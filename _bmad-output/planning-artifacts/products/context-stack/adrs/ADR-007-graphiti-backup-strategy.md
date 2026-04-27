---
adr: 007
title: "Graphiti backup cadence — daily AOF rewrite + weekly RDB snapshot + monthly export"
status: accepted
date: 2026-04-25
authors: tomamourette (via BMAD director Claude)
context_question: Q2
---

# ADR-007: Graphiti backup cadence — daily AOF rewrite + weekly RDB snapshot + monthly export

## Amendment 2026-04-27 (per-group graph reality)

**Discovery during E3-S06 functional smoke tests:** Graphiti creates one FalkorDB graph per `group_id` lazily. As of E3-S07 implementation there are 13 such graphs in `GRAPH.LIST` (`default_db`, plus per-test/per-feature namespaces); the count grows whenever a new `group_id` is used. The original ADR-007 design implicitly assumed a single canonical graph (`default_db`).

**What changed:**

- **Layer 1 (in-process AOF):** unchanged. AOF is FalkorDB-server-level and captures writes to every graph in the instance.
- **Layer 2 (daily AOF rewrite + weekly RDB snapshot):** unchanged in intent. AOF rewrite (`BGREWRITEAOF`) and RDB snapshot (`BGSAVE`) are both server-level — they cover all graphs in one operation. Implementation in `homelab-apps/stacks/graphiti/scripts/backup-aof-rewrite.sh` and `backup-rdb-snapshot.sh`.
- **Layer 3 (monthly Cypher export):** must enumerate `GRAPH.LIST` dynamically and emit one export per graph, not one global export against a hardcoded `default_db`. Implementation in `homelab-apps/stacks/graphiti/scripts/backup-cypher-export.sh`.

**Caveat surfaced during implementation:** FalkorDB's `GRAPH.QUERY` output is the canonical query response format, NOT directly Cypher-import compatible. The Cypher export is best understood as a per-graph audit/portability/exit-ramp artifact, not the primary recovery path. The RDB snapshot (Layer 2) remains the actual point-in-time-restoration mechanism. Building a Cypher-replay tool that round-trips through the response format is deferred to E3-S08 (restore drill); for the drill, restore from the RDB snapshot, validate via Graphiti search queries, treat the Cypher export as a parallel audit signal.

**Operational paths:** logs at `~/.local/state/graphiti-backup/logs/{aof,rdb,cypher}.log`; artifacts at `~/.local/state/graphiti-backup/{rdb,cypher}/`. `/var/log` and `/var/backups` were rejected because the cron-running user (`developer`) is unprivileged on the workstation; XDG state-dir convention sidesteps the sudo requirement and keeps artifacts in a directory the operator's existing host-level backup sweep can capture.

**Reversal trigger:** if FalkorDB ever ships a native `GRAPH.EXPORT` / `GRAPH.IMPORT` Cypher round-trip, replace the script's `.raw` capture with that and demote the response-format dump.

The original Decision text below stands; this amendment supersedes the assumption of a single `default_db` graph.

## Context

PRD FR-MEM-014 and brief Q5 ask the architecture phase to recommend a Graphiti backup cadence and retention. FalkorDB is a Redis module; its persistence model is the standard Redis dual mechanism:

- **AOF** (append-only file): every write appended to disk; on restart, replay rebuilds state. Durable to the last `fsync`.
- **RDB** (snapshot): periodic full-state dump to a single binary file. Fast restore but loses writes since the last snapshot.

Both can run together (`appendonly yes` + `save ...` rules), which is the FalkorDB default per `graphiti-claude-code-install-plan-2026-04-25.md` §10 ("RDB+AOF defaults are durable").

Constraints:
- Single-operator product; no DR-class RPO/RTO target (a few hours of lost facts is annoying, not catastrophic).
- `/srv/graphiti/data` is on `ct-ai-01` (currently on pve3 storage; per project memory, this container moves between nodes).
- The operator already has a `zfs send` / rsnapshot pattern for backups (per install-plan §2.3 "Add /srv/graphiti/data to whatever you back up").
- Storage is cheap; ops burden is the binding constraint.

## Decision

Three layers of backup, all automated:

### Layer 1 — In-process durability (AOF, default-on)

`appendonly yes` is on by default in FalkorDB. The MCP server crash → restart cycle replays the AOF, losing only writes since the last `fsync`. No operator action required.

### Layer 2 — Daily AOF rewrite + weekly RDB snapshot (cron on `ct-ai-01`)

Add to `/srv/graphiti/cron.d/graphiti-backup`:

```bash
# Daily at 03:00 — rewrite AOF (compacts, reduces replay time)
0 3 * * * docker exec graphiti-falkordb redis-cli -a "$FALKORDB_PASSWORD" BGREWRITEAOF >> /var/log/graphiti-backup.log 2>&1

# Weekly Sunday at 03:30 — force RDB snapshot
30 3 * * 0 docker exec graphiti-falkordb redis-cli -a "$FALKORDB_PASSWORD" BGSAVE >> /var/log/graphiti-backup.log 2>&1
```

`/srv/graphiti/data` (containing `appendonly.aof` + `dump.rdb`) is then captured by the operator's existing nightly `zfs send` / rsnapshot pattern.

**Retention:** 14 daily snapshots + 8 weekly snapshots + 3 monthly snapshots. Total disk footprint at this data scale: < 5 GB combined (well within NFR-FOOTPRINT-003).

### Layer 3 — Monthly Cypher export (the exit-ramp insurance)

A monthly cron exports the entire graph as portable JSON:

```bash
# 1st of month at 04:00 — Cypher dump
0 4 1 * * /srv/graphiti/scripts/cypher-export.sh > /srv/graphiti/exports/graphiti-$(date +%Y-%m).json 2>> /var/log/graphiti-backup.log
```

Where `cypher-export.sh` runs:

```bash
#!/usr/bin/env bash
docker exec graphiti-falkordb redis-cli -a "$FALKORDB_PASSWORD" GRAPH.QUERY default_db \
  "MATCH (n)-[r]->(m) RETURN n, r, m" --no-auth-warning
```

Exports retained for 12 months (12 files; tiny — a populated Graphiti at this scale produces < 50 MB JSON).

### Restore drill protocol (exercised at Phase 2 promotion + quarterly)

```
1. Stop the stack:   cd /srv/graphiti && docker compose down
2. Wipe the data:    sudo rm -rf /srv/graphiti/data && sudo mkdir -p /srv/graphiti/data
3. Restore the AOF:  cp /backup/$DATE/appendonly.aof /srv/graphiti/data/
4. Start the stack:  docker compose up -d
5. Verify:           docker compose exec falkordb redis-cli -a "$FALKORDB_PASSWORD" \
                       GRAPH.QUERY default_db "MATCH (n) RETURN count(n)"
   Expected: count matches the count from before the restore.
6. Smoke test:       Run install-plan §7 smoke tests 1-3 (write, read, temporal validity).
```

The restore drill is mandatory before Phase 2 promotion off `ct-dev-homelab` (gates G-Rollback) and is repeated quarterly thereafter — operator journals the result in the weekly retro (FR-OBS-004).

## Consequences

**Positive.**
- AOF + cron-driven `BGREWRITEAOF` gives near-zero RPO at no manual cost.
- RDB snapshots + ZFS-snapshot of `/srv/graphiti/data` gives point-in-time recovery for arbitrary days in the retention window.
- Monthly Cypher export decouples backup from FalkorDB binary format — exit ramp from FalkorDB is one-replay away (see ADR-001 exit ramp).
- All commands run inside existing `docker exec` + `cron` patterns; no new ops surface.

**Negative.**
- Three layers means three things can break (AOF rewrite hang, ZFS snapshot failure, JSON export script error). Mitigated by `>> /var/log/graphiti-backup.log` and a weekly `journalctl | grep graphiti-backup` glance.
- Quarterly restore drill is operator-time (~30 min). Without it, "documented" backup is unverified backup — the value is the drill, not the drill spec.

**Neutral.**
- AOF + RDB defaults are documented Redis behaviour; the only change is enforcing `BGREWRITEAOF` cadence to keep replay time bounded.

## Alternatives Considered

1. **AOF-only (no RDB)** — rejected. AOF replay time grows with history; without periodic compaction (BGREWRITEAOF), restore latency drifts up.
2. **RDB-only (no AOF)** — rejected. Up to a week of lost writes between snapshots; meaningful for fact archive even at single-operator scale.
3. **`zfs send` of the data dir without explicit AOF rewrite** — rejected. Captures whatever is on disk at snapshot time; without forcing AOF rewrite, replay cost grows unboundedly.
4. **Cypher export as the *only* backup** — rejected. Cypher JSON is replay-shaped, not state-shaped; recovering from it requires a full re-ingest run, not a binary restore. Slow and lossy on relation timestamps.
5. **Continuous replication to a second FalkorDB** — rejected. Over-engineered for single-operator product.

## Validation / Exit Ramp

- **Validation:**
  - Week 1: `cron.d/graphiti-backup` installed; `journalctl --since 1.day.ago | grep graphiti-backup` shows successful AOF rewrite.
  - Phase 2 promotion: restore drill exercised once on `ct-dev-homelab`; smoke-tests 1-3 pass against restored data.
  - Quarterly: drill repeated; operator journal note recorded.
- **Exit ramp:** monthly Cypher export is the cross-database escape hatch. If FalkorDB becomes unmaintained, replay any monthly export into Neo4j or Kuzu via a one-off importer script.
- **Reversal trigger:** if a real recovery scenario (e.g., disk-corruption event) reveals the AOF is unrecoverable, escalate AOF rewrite cadence to twice-daily and add Cypher export to weekly.

## References

- `graphiti-claude-code-install-plan-2026-04-25.md` §10 (RDB+AOF durable; nightly backup pattern)
- PRD FR-MEM-014, NFR-PORT-002, FR-DEP-007 (rollback)
- ADR-001 (FalkorDB choice), ADR-012 (graph export tooling)
- Brief Q5
