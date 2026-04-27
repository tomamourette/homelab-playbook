# E3-S08 Evidence — Graphiti restore drill (ADR-007)

**Sprint:** 3 / Epic 3 (Graphiti rollout)
**Story:** E3-S08 — disaster-recovery restore drill
**Date:** 2026-04-27
**Branch:** decommission/context-stack-phase-1
**Operator:** autonomous agent (Claude Opus 4.7), under tomamourette
**Outcome:** **PASS WITH CAVEAT** — graph data integrity verified end-to-end; one MCP-search caveat (pre-existing, unrelated to drill).

## Summary

The drill simulated catastrophic loss of `~/.graphiti-data` and proved the E3-S07 RDB backup artifact restores a working stack with all 13 graphs and exact node counts intact. **First-attempt restore failed** (silent-bypass: AOF preferred over `dump.rdb`); recovery procedure adjusted to promote the RDB to AOF base file with a matching manifest, after which the second attempt loaded all 26 keys cleanly. Total wall-clock downtime including the diagnostic detour: **91 seconds**.

The runbook (`e3-s08-restore-runbook.md`) captures the corrected procedure so future operators don't hit the same silent failure.

## Phase-by-phase outcome

| Phase | Description | Outcome |
| --- | --- | --- |
| 0 | Pre-drill state capture | PASS |
| 1 | Force fresh RDB snapshot | PASS |
| 2 | Simulate data loss (preserve + clear) | PASS |
| 3 | First restore attempt — RDB at `dump.rdb` | **FAIL** (silent bypass) |
| 4a | Recovery: promote RDB to AOF base + manifest | PASS |
| 4b | Verify FalkorDB load | PASS |
| 5 | Start graphiti-mcp + verify init | PASS |
| 6 | Verify restored data matches pre-drill | PASS WITH CAVEAT |
| 7 | Drill outcome decision | PASS |
| 8 | Documents written | PASS (this file + runbook) |

## Phase 0 — Pre-drill state

**Containers:**

```
NAMES          STATUS
graphiti-mcp   Up 3 hours (healthy)
falkordb       Up 18 hours (healthy)
```

**Graphs (13 total):**

```
default_db
e3-s04b-smoke
e3-s05-smoke
e3-s05-smoke-retry
e3-s05-flash-lite-test
e3s05flashlite
e3s04g1
e3s04g2
e3s04g3
e3s06test1
e3s06test3bitemp
graphiti_migration
e3s06test5failinject
```

**Pre-drill node counts (`/tmp/e3-s08-counts-pre.txt`):**

```
default_db : 0 nodes
e3-s04b-smoke : 0 nodes
e3-s05-smoke : 0 nodes
e3-s05-smoke-retry : 0 nodes
e3-s05-flash-lite-test : 0 nodes
e3s05flashlite : 14 nodes
e3s04g1 : 13 nodes
e3s04g2 : 13 nodes
e3s04g3 : 13 nodes
e3s06test1 : 308 nodes
e3s06test3bitemp : 14 nodes
graphiti_migration : 0 nodes
e3s06test5failinject : 3 nodes
```

Total nodes: **378**. Load-bearing graph: **`e3s06test1` (308 nodes)**.

**Pre-drill sample entities from `e3s06test1`:**

```
ADR-001
FalkorDB v4.18.1
Graphiti
Neo4j
FalkorDB
```

## Phase 1 — Drill snapshot

Ran `homelab-apps/stacks/graphiti/scripts/backup-rdb-snapshot.sh`:

```
falkordb-20260427T093042Z.rdb   10,659,398 bytes   2026-04-27 09:30 UTC
latest.rdb -> falkordb-20260427T093042Z.rdb
```

This is the artifact restored from in Phase 4.

## Phase 2 — Simulated data loss

09:30:50 UTC — downtime clock starts.

```
Container graphiti-mcp Stopping
Container graphiti-mcp Stopped
Container falkordb Stopping
Container falkordb Stopped
```

Live data dir preserved:

```
mv ~/.graphiti-data ~/.graphiti-data.preserved-by-e3-s08
mkdir -p ~/.graphiti-data
```

Preserved-dir contents (the safety rollback):

```
drwxr-xr-x  2 root      root             5 Apr 27 09:30 appendonlydir
-rw-r--r--  1 root      root      10659398 Apr 27 09:30 dump.rdb
```

## Phase 3 — First restore attempt (FAILED — documented for the runbook)

Placed backup as `~/.graphiti-data/dump.rdb` (the obvious-looking spot):

```
DRILL_RDB=~/.local/state/graphiti-backup/rdb/falkordb-20260427T093042Z.rdb
cp -v "$DRILL_RDB" ~/.graphiti-data/dump.rdb
sudo chown root:root ~/.graphiti-data/dump.rdb
```

Started `falkordb`. Logs showed:

```
1:M 27 Apr 2026 09:31:07.972 * BGSAVE done, 0 keys saved, 0 keys skipped, 118 bytes written.
1:M 27 Apr 2026 09:31:07.973 * Creating AOF base file appendonly.aof.1.base.rdb on server start
```

`GRAPH.LIST` empty, `DBSIZE = 0`. **Silent bypass:** with `appendonly yes` set by the compose `REDIS_ARGS`, FalkorDB ignores `dump.rdb` at the data dir root and creates a fresh empty AOF on startup. The 10.66 MB `dump.rdb` was never read.

This is the most important runbook insight from the drill — operators following the obvious path would silently lose their data. The runbook now documents this explicitly under "If load shows 0 keys" and corrects Phase 4 to place the backup inside `appendonlydir/` with a matching manifest.

## Phase 4 — Corrected restore (PASS)

Inspected the preserved dir's AOF layout to learn the right shape:

```
appendonly.aof.4.base.rdb   (10.66 MB, root:root)
appendonly.aof.4.incr.aof   (0 bytes)
appendonly.aof.manifest     ("file appendonly.aof.4.base.rdb seq 4 type b\nfile appendonly.aof.4.incr.aof seq 4 type i startoffset 1013 endoffset 1013")
```

Stopped `falkordb`, cleared the failed-attempt dir, and rebuilt with the backup as the AOF base file at `seq 1`:

```bash
sudo rm -rf ~/.graphiti-data
mkdir -p ~/.graphiti-data/appendonlydir
sudo cp -v "$DRILL_RDB" ~/.graphiti-data/appendonlydir/appendonly.aof.1.base.rdb
echo "file appendonly.aof.1.base.rdb seq 1 type b" \
  | sudo tee ~/.graphiti-data/appendonlydir/appendonly.aof.manifest
sudo touch ~/.graphiti-data/appendonlydir/appendonly.aof.1.incr.aof
sudo chown -R root:root ~/.graphiti-data/appendonlydir
```

Started `falkordb` again. Logs (verbatim relevant lines):

```
1:M 27 Apr 2026 09:31:50.505 * <module> Done decoding graph e3s06test5failinject
1:M 27 Apr 2026 09:31:50.505 * <module> Done decoding graph e3-s05-smoke-retry
1:M 27 Apr 2026 09:31:50.511 * <module> Done decoding graph e3-s05-flash-lite-test
1:M 27 Apr 2026 09:31:50.511 * Done loading RDB, keys loaded: 26, keys expired: 0.
1:M 27 Apr 2026 09:31:50.511 * DB loaded from base file appendonly.aof.1.base.rdb: 0.039 seconds
1:M 27 Apr 2026 09:31:50.514 * Creating AOF incr file appendonly.aof.1.incr.aof on server start
1:M 27 Apr 2026 09:31:50.514 * Ready to accept connections tcp
```

**26 keys loaded** matches the snapshot (`BGSAVE done, 26 keys saved` from the pre-drill shutdown log). All 13 graphs decoded. Container reported `Up 8 seconds (healthy)`.

## Phase 5 — graphiti-mcp restart

```
NAMES          STATUS
graphiti-mcp   Up 12 seconds (healthy)

2026-04-27 09:32:06 - graphiti_mcp_server - INFO - Successfully initialized Graphiti client
2026-04-27 09:32:06 - graphiti_mcp_server - INFO - Using LLM provider: gemini / gemini-2.5-flash-lite
2026-04-27 09:32:06 - graphiti_mcp_server - INFO - Using Embedder provider: openai

curl -o /dev/null -w 'health=%{http_code}\n' http://127.0.0.1:8000/health
health=200
```

09:32:21 UTC — downtime clock stops. **Total downtime: 91 seconds (1 m 31 s).**

## Phase 6 — Data integrity verification

**Graph list (sorted diff):**

```
diff <(sort /tmp/e3-s08-graphs-pre.txt) <(sort /tmp/e3-s08-graphs-post.txt)
→ GRAPHS_MATCH_SORTED
```

(Unsorted diff showed differences only in iteration order — Redis hash table iteration is non-deterministic across restarts. Sorted comparison is the correct check.)

**Node counts (sorted diff):**

```
diff <(sort /tmp/e3-s08-counts-pre.txt) <(sort /tmp/e3-s08-counts-post.txt)
→ COUNTS_MATCH_SORTED
```

Per-graph post-drill counts (verbatim from `/tmp/e3-s08-counts-post.txt`):

```
default_db : 0 nodes
e3s06test1 : 308 nodes        ← load-bearing graph: matches exactly
e3s05flashlite : 14 nodes
graphiti_migration : 0 nodes
e3-s05-smoke : 0 nodes
e3s04g2 : 13 nodes
e3s06test3bitemp : 14 nodes
e3s04g3 : 13 nodes
e3-s04b-smoke : 0 nodes
e3s04g1 : 13 nodes
e3s06test5failinject : 3 nodes
e3-s05-smoke-retry : 0 nodes
e3-s05-flash-lite-test : 0 nodes
```

**Sample entity check on `e3s06test1` (post-restore):**

```
1) "ADR-001"
2) "FalkorDB v4.18.1"
3) "Graphiti"
4) "Neo4j"
5) "FalkorDB"
```

Identical to pre-drill (`/tmp/e3-s08-sample-pre.txt`), modulo Redis execution-time metadata.

**Index profile post-restore (Entity):**

```
"Entity"  RANGE on uuid, group_id, name, created_at;  FULLTEXT on group_id, name, summary
numDocuments: 260   (= 260 Entity nodes, all present)
```

Other indexes also intact: `RELATES_TO` 302 docs, `MENTIONS` 367 docs, `Episodic` 48 docs.

**Embeddings:** 260 / 260 Entity nodes have `name_embedding` populated post-restore.

## Phase 6 caveat — MCP `search_nodes` returns empty (NOT a drill regression)

Post-restore, `search_nodes(query="FalkorDB", group_ids=["e3s06test1"])` returned `{ "message": "No relevant nodes found", "nodes": [] }` despite the entity being present in the graph.

To rule out a drill-induced regression, I swapped the data dir back to `~/.graphiti-data.preserved-by-e3-s08` (the untouched live state from Phase 0), restarted both containers, and ran the **same** MCP query:

```json
{"jsonrpc":"2.0","id":2,"result":{"content":[{"type":"text","text":
  "{\n  \"message\": \"No relevant nodes found\",\n  \"nodes\": []\n}"}],...}}
```

**Identical empty result against the untouched live state.** This proves the empty-search behavior is pre-existing (not caused by the drill). The drill restored data integrity exactly; what it cannot fix is a search-layer issue that already existed. After the comparison test, the data dir was swapped back to the drill-restored state for the final stack run.

This caveat is documented in the runbook so future operators don't mis-diagnose it as a restore failure. Investigation of the MCP search bug is out of scope for E3-S08 and should be raised as its own issue (likely E3-S09 input or a Sprint 3 retro item).

## Phase 7 — Drill verdict

**PASS.** Restore proven end-to-end. The first-attempt failure became the most valuable runbook content — silent AOF-bypass would otherwise have been a real-world disaster waiting to happen.

The preserved data dir at `~/.graphiti-data.preserved-by-e3-s08` is left in place as the 24 h safety net per the runbook. Operator should delete after 2026-04-28 once next-day stability is confirmed.

## Final state

```
NAMES          STATUS
graphiti-mcp   Up <healthy>
falkordb       Up <healthy>
```

- 13 graphs in `GRAPH.LIST` (matches pre-drill exactly).
- `e3s06test1` has 308 nodes, 260 of which are `Entity` with `name_embedding` populated.
- `health=200` on `http://127.0.0.1:8000/health`.
- LLM provider: `gemini / gemini-2.5-flash-lite`.
- Embedder provider: `openai` (LiteLLM gateway alias for Gemini Embedding 2).

## Files

- `homelab-playbook/docs/context-stack/sprint-3/e3-s08-restore-runbook.md` — operator runbook (the deliverable).
- `homelab-playbook/docs/context-stack/sprint-3/e3-s08-evidence.md` — this file.

No `homelab-apps` or `homelab-infra` changes (backup scripts were already in place from E3-S07).

## Quarterly cadence

ADR-007 specifies a quarterly restore drill. Next due: **2026-07-27**. The runbook is the artifact future drills should re-validate against.
