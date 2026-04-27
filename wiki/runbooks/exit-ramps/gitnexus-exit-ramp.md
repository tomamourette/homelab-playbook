---
title: "GitNexus tier — exit ramp"
slug: gitnexus-exit-ramp
category: runbooks
last_reviewed: 2026-04-27
owner: tomamourette
related_pages:
  - index
  - query-hierarchy
related_frs:
  - FR-CG-010
  - NFR-PORT-001
related_adrs:
  - ADR-004
  - ADR-012
  - ADR-013
status: stable
supersedes: []
superseded_by: null
---

# GitNexus tier — exit ramp

## Summary

GitNexus's exit ramp is the NDJSON dump from `scripts/gitnexus-export.sh`
(per ADR-012). The export uses GitNexus's documented `cypher` tool surface
to produce a Context-Stack-controlled JSON schema that any successor
graph store can ingest. Recovery from a corrupt graph is `gitnexus
group_sync` against the source repos. **Operator note:** there is a
known `${HOME}` path-resolution divergence between the container and
the workstation CLI (Section "Container vs CLI registry divergence"
below) — surface to address at next deploy, not a runtime blocker.

## Context

ADR-012 ships the export as a wrapper script (not an upstream feature)
because GitNexus does not document a stable export format. The wrapper
queries Cypher (`MATCH (n)-[r]->(m) RETURN n, labels(n), r, type(r), m,
labels(m)`) and emits NDJSON the operator controls — Context Stack owns
the schema, GitNexus owns only the underlying storage.

GitNexus is rated R1 abandonment risk (Brief §10.1, single-maintainer
project), so the exit ramp is non-optional per ADR-004.

## Procedure

### 1. Export the graph (NDJSON dump per ADR-012)

```bash
# From the workstation, with GitNexus daemon running:
bash homelab-playbook/scripts/gitnexus-export.sh
# Output: ~/workspace/homelab/_export/gitnexus/$(date +%Y-%m-%d).ndjson
```

The schema (Context-Stack-controlled, NOT GitNexus-controlled — see
ADR-012 §Decision):

```jsonl
{"type":"node","id":"<id>","labels":["Function","Definition"],"props":{"name":"add_episode","file":"...","line":234}}
{"type":"node","id":"<id>","labels":["File"],"props":{"path":"src/foo.py"}}
{"type":"edge","id":"<id>","src":"<node-id>","dst":"<node-id>","kind":"REFERENCES","props":{"line":56}}
```

Three field shapes — `node`, `edge`, optional version-header line.
Validate the dump:

```bash
EXPORT=~/workspace/homelab/_export/gitnexus/$(date +%Y-%m-%d).ndjson
jq -c . < "$EXPORT" | wc -l            # parses, line count > 0
jq -r '.type' "$EXPORT" | sort -u      # expect: edge, node
ls -lh "$EXPORT"                       # expect: < 50 MB at homelab scale
```

### 2. Replay into a successor (CodeGraphContext / graphify / Neo4j)

The replay script `scripts/gitnexus-to-cgc.sh` is **not shipped** —
ADR-012 explicitly defers this until the exit ramp is exercised. The
sketch (per ADR-012 §Replay path):

```bash
# Sketch — only built on exit-ramp activation
cat $EXPORT \
  | jq -r 'select(.type=="node") | "MERGE (n:" + (.labels | join(":")) +
           " {id:\"" + .id + "\"}) SET n += " + (.props|tojson)' \
  | cypher-shell -u neo4j -p $NEO4J_PASS
```

Building the replay is a Sprint 5+ event triggered by the exit-ramp
activation; capture the runbook at `runbooks/gitnexus-to-codegraphcontext.md`
when it ships.

### 3. Recovery from corruption — re-analyze, don't restore

GitNexus's underlying LadybugDB store is not a portable backup target
(ADR-012 §Alternatives Considered, item 2). Recovery is **re-analysis
from source repos**, which is fast (the operator's `~/workspace/homelab/`
re-indexes in seconds — sub-30 s per FR-CG-002 / K2 target):

```bash
# 1. Wipe the corrupt data dir on the host
docker compose -f homelab-apps/stacks/gitnexus/docker-compose.yml down

# 2. Remove the data volume (or mv it aside as a safety net)
sudo mv /root/.gitnexus-data /root/.gitnexus-data.bak.$(date +%s)

# 3. Bring the stack back up; daemon recreates an empty registry
docker compose -f homelab-apps/stacks/gitnexus/docker-compose.yml up -d

# 4. Re-register and analyze each repo
docker exec gitnexus-mcp gitnexus group_sync --repo /workspace/homelab-playbook
docker exec gitnexus-mcp gitnexus group_sync --repo /workspace/homelab-infra
docker exec gitnexus-mcp gitnexus group_sync --repo /workspace/homelab-apps

# 5. Verify
docker exec gitnexus-mcp gitnexus list_repos
# expect: 3 repos with healthy graphs
```

The source-of-truth for the *graph* is the source-of-truth for the *code*
— there is nothing to restore that the source repos don't already encode.

### 4. Container vs CLI registry divergence (operator note from E4-S09)

**Problem surfaced during E4-S09 KPI backfill (2026-04-27):** the GitNexus
container resolves `${HOME}` to `/root/`, so its data lives at
`/root/.gitnexus-data` per `docker inspect`. The operator's CLI on the
workstation writes to `/home/developer/.gitnexus-data`. **Two registries
diverge.** The MCP daemon's `list_repos` returns `[]` (its own registry);
the operator's CLI registry has 3 repos with healthy graphs.

**Why this is not a Sprint-5 blocker:** the E4-S09 backfill measured
on-disk graph artefacts directly, sidestepping the registry mismatch.
K1 / K2 / K4 numbers in the weekly digest are valid.

**Why this matters for the exit ramp:** future K1 token-reduction
round-trip measurements (which compare Claude Code MCP-tool answers vs
operator-CLI answers) and operator-recovery procedures both need the
two registries to agree. Specifically:

- Step 1 (export) above runs against whichever side the operator
  invokes — workstation CLI hits `/home/developer/.gitnexus-data`,
  `docker exec` against the container hits `/root/.gitnexus-data`.
- Step 3 (recovery) above uses `docker exec ... gitnexus group_sync` —
  this writes to the container's registry. The workstation CLI's
  registry is unaffected and stays out of sync.

**Recommended canonical resolution (operator decision at next deploy,
not in this story):**

- **Option A (preferred): use `docker exec` for all `gitnexus` CLI
  invocations going forward.** Aliases on the workstation:
  ```bash
  alias gitnexus='docker exec gitnexus-mcp gitnexus'
  ```
  This makes the container the single source of truth.
- **Option B: at next re-baseline, force the bind-mount path to align.**
  Edit `homelab-apps/stacks/gitnexus/docker-compose.yml` to bind-mount
  `/home/developer/.gitnexus-data:/root/.gitnexus-data`, so both sides
  see the same on-disk state regardless of who writes.

**Do not change the running stack today.** The divergence is documented;
operator picks A or B at the next intentional GitNexus deploy. Until
then, prefer the container side (Option A pattern, ad-hoc) for any
operation that must round-trip via the daemon.

### 5. Cadence

Per ADR-012 §Cadence:

- **On-demand:** operator runs the export when a snapshot is wanted.
- **Phase 2 exit:** export run once, committed to `_export/gitnexus/`
  as evidence for FR-CG-010 / NFR-PORT-001.
- **No automatic schedule** — the exit ramp is insurance, not a backup.
  The wiki + git workflow is the operator's primary capture mechanism.

## Cross-references

- [Query hierarchy](query-hierarchy) — when to consult Tier 2 (GitNexus).
- ADR-004 — GitNexus adoption + exit-ramp commitment.
- ADR-012 — graph export wrapper (NDJSON schema + replay sketch).
- ADR-013 — tier-of-truth division.
- E4-S09 backfill (`docs/context-stack/sprint-2/kpi-backfill.md`) —
  source of the container vs CLI registry divergence note above.
