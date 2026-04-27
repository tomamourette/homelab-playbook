---
title: "Graphiti tier — exit ramp"
slug: graphiti-exit-ramp
category: runbooks
last_reviewed: 2026-04-27
owner: tomamourette
related_pages:
  - index
  - query-hierarchy
related_frs:
  - FR-MEM-014
  - NFR-PORT-002
related_adrs:
  - ADR-007
  - ADR-013
status: stable
supersedes: []
superseded_by: null
---

# Graphiti tier — exit ramp

## Summary

Graphiti's exit ramp is two-pronged per ADR-007 (amended 2026-04-27):
the **RDB snapshot** is the recovery path (point-in-time restore of the
FalkorDB binary state); the **per-graph Cypher export** is audit/portability
insurance (not round-trippable as-shipped). Recovery drill is captured in
the E3-S08 restore runbook. Migration to a different graph store requires
building a Cypher-replay tool against the response-format dump (deferred,
see `Backlog` below).

## Context

Graphiti runs FalkorDB (Redis-module graph store) with `appendonly yes` +
periodic `BGSAVE`. ADR-007's three-layer backup design (in-process AOF,
weekly RDB, monthly Cypher export) is unchanged in intent; the
2026-04-27 amendment clarified two implementation realities:

1. **Per-graph reality:** Graphiti creates one FalkorDB graph per
   `group_id` lazily. The Cypher export must enumerate `GRAPH.LIST`
   dynamically and emit one export per graph.
2. **Cypher export is audit-only.** FalkorDB's `GRAPH.QUERY` output is the
   canonical query response format, NOT Cypher-import compatible. Round-
   tripping requires a replay tool we have not yet built.

The RDB snapshot is therefore the actual recovery mechanism; the Cypher
export is the cross-database escape hatch.

## Procedure

### 1. Recovery (RDB-restore drill, E3-S08 runbook)

Use the E3-S08 runbook at
`docs/context-stack/sprint-3/e3-s08-restore-runbook.md`. Summary:

```bash
# 1. Stop the stack
cd /srv/graphiti && docker compose down

# 2. Wipe the data dir (or mv it aside as a safety net)
sudo mv /srv/graphiti/data /srv/graphiti/data.bak.$(date +%s)
sudo mkdir -p /srv/graphiti/data

# 3. Restore the AOF + RDB from the backup snapshot
cp /backup/$DATE/appendonly.aof /srv/graphiti/data/
cp /backup/$DATE/dump.rdb       /srv/graphiti/data/

# 4. Start the stack — FalkorDB replays AOF, loads RDB
docker compose up -d

# 5. Verify (per ADR-007 step 5)
docker compose exec falkordb redis-cli -a "$FALKORDB_PASSWORD" \
    GRAPH.QUERY default_db "MATCH (n) RETURN count(n)"
# Expected: count matches the count from before the restore.

# 6. Smoke test (install-plan §7 smoke tests 1-3)
# write, read, temporal-validity probes against MCP at port 8000
```

The drill is mandatory before Phase 2 promotion (gates G-Rollback) and
repeats quarterly. Operator journals the result in the weekly retro
([Weekly observability digest](weekly-observability-digest)).

### 2. Cross-database migration (audit export → manual replay)

The Cypher export is the cross-database escape hatch. Per ADR-007
amendment, the exporter enumerates `GRAPH.LIST` and writes one file per
graph:

```bash
# Layer 3 of ADR-007's three-layer backup
bash homelab-apps/stacks/graphiti/scripts/backup-cypher-export.sh
# Output: ~/.local/state/graphiti-backup/cypher/<YYYY-MM>/<group_id>.raw
```

The `.raw` file is the FalkorDB query response, NOT Cypher source. To
migrate to Neo4j / Kuzu / another graph store, you need to:

1. **Parse the response format** — line-by-line, each line is a
   `redis-cli` row. The shape is documented in
   `homelab-apps/stacks/graphiti/scripts/backup-cypher-export.sh`
   (the script that produces it).
2. **Build a Cypher-replay tool** — read the parsed nodes/edges,
   emit `CREATE` / `MERGE` Cypher against the target store. This tool
   does not exist yet (see Backlog).
3. **Replay against the target.**
4. **Validate** — count nodes, count edges, sample-query parity.

For a same-version FalkorDB restore (the common case), use the RDB
path in §1 above. The Cypher export path is only for "we want to leave
FalkorDB" — at which point investing one day to build the replay tool
is the cost of admission.

### 3. Migration to a different FalkorDB instance (same version)

If the target is just a different FalkorDB host (e.g. moving Graphiti
from `ct-dev-homelab` to a new container), the RDB file is portable:

```bash
# 1. Export from source — last weekly RDB snapshot
SRC=$(ls -t ~/.local/state/graphiti-backup/rdb/*.rdb | head -1)

# 2. Stop the destination FalkorDB (per Amendment 2026-04-27b — DO NOT
#    use `docker compose down -v`; use `down` and the named volume
#    persists. The compose-app role's down-guard enforces this.)
ssh <dest-host> "cd /srv/graphiti && docker compose down"

# 3. Copy the RDB into the destination's data dir
scp "$SRC" <dest-host>:/srv/graphiti/data/dump.rdb

# 4. Bring the stack up; FalkorDB loads the RDB on start
ssh <dest-host> "cd /srv/graphiti && docker compose up -d"

# 5. Verify per §1 step 5/6
```

This path is faster than re-ingesting from Cypher and is what the
quarterly restore drill exercises.

### 4. Backlog — Cypher-replay tool (E3-S04h)

The Cypher export's hyphen-escape edge case (`group_id` values
containing hyphens like `e4-s09` need quoting in the replay) and the
response-format-to-Cypher translator are tracked as **E3-S04h** in the
Sprint 3 backlog. Until that ships, the Cypher export is genuinely
**audit-only**: it answers "did graph G exist on date D with these
nodes" but does not let you reconstitute G in another store without
hand-rolling the replay.

If a real cross-database migration becomes urgent, promote E3-S04h to
the next sprint and budget ~1 day for the replay tool + validation.

### 5. Cadence (per ADR-007 §Decision)

- **In-process:** AOF default-on, every write fsyncs.
- **Daily 03:00:** `BGREWRITEAOF` (compacts AOF, bounds replay time).
- **Weekly Sun 03:30:** `BGSAVE` (forces RDB snapshot).
- **Monthly 1st 04:00:** Cypher export per graph in `GRAPH.LIST`.
- **Retention:** 14 daily / 8 weekly / 3 monthly RDB snapshots; 12
  monthly Cypher exports.
- **Drill cadence:** before Phase 2 promotion, then quarterly.

### 6. Pre-restore deletion safety (Amendment 2026-04-27b)

The Ansible `compose-app` role at
`homelab-infra/ansible/roles/compose-app/` refuses `docker compose
down -v` unless TWO opt-in flags are set explicitly: per-call
`down_destructive=true` AND per-stack `compose_app_force_data_loss=true`.
When both are set, the role first takes a `cp -a` snapshot of the data
dir before destroying volumes. Honour this contract — bypassing it on
the Graphiti host risks losing both the live state and the on-host
backup artefacts that share the data-dir tree.

## Cross-references

- [Query hierarchy](query-hierarchy) — when to consult Tier 3 (Graphiti).
- ADR-007 (amended 2026-04-27 + 2026-04-27b) — backup strategy +
  per-group reality + down-guard.
- ADR-013 — tier-of-truth division.
- E3-S08 restore runbook
  (`docs/context-stack/sprint-3/e3-s08-restore-runbook.md`).
- Backup scripts:
  - `homelab-apps/stacks/graphiti/scripts/backup-aof-rewrite.sh`
  - `homelab-apps/stacks/graphiti/scripts/backup-rdb-snapshot.sh`
  - `homelab-apps/stacks/graphiti/scripts/backup-cypher-export.sh`
