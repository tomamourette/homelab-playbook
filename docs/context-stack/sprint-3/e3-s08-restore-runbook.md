# Graphiti Restore Runbook (per ADR-007)

**Audience:** Homelab operator facing FalkorDB data corruption / volume loss in the Graphiti context-stack.
**Recovery path:** RDB snapshot from `~/.local/state/graphiti-backup/rdb/latest.rdb`, promoted to AOF base file.
**Validated:** 2026-04-27 via E3-S08 drill (see `e3-s08-evidence.md`). Achieved 91 s actual downtime on first execution; runbook target 5–15 min.

## Why this is the recovery path

ADR-007 (amended 2026-04-27) names the RDB snapshot under `~/.local/state/graphiti-backup/rdb/` as the actual recovery artifact. The Cypher-shaped tarballs under `~/.local/state/graphiti-backup/cypher/` are an audit / portability / exit-ramp artifact only — they cannot be directly imported back into FalkorDB-Graphiti. Don't try.

## Prerequisites

- Backup artifact present: `~/.local/state/graphiti-backup/rdb/latest.rdb` (a symlink to a dated `falkordb-<TS>.rdb`).
- Tools: `docker compose`, `sudo` (needed to write into the bind-mount data dir as `root:root`), shell on the developer workstation.
- Confidence the backup is recent: `ls -la ~/.local/state/graphiti-backup/rdb/latest.rdb`. If older than ~1 week, the in-container AOF state may still be richer than the snapshot — try a plain restart first (Phase 1 below) before proceeding to a full RDB restore.

## Critical concept: AOF takes priority over `dump.rdb`

FalkorDB has `appendonly yes` (set by the compose `REDIS_ARGS`). On startup, when AOF is on, the server **ignores `dump.rdb` in the data dir root** and instead reads `appendonlydir/appendonly.aof.<seq>.base.rdb` as named by `appendonlydir/appendonly.aof.manifest`. If you only place `dump.rdb`, the server starts empty, creates a new (empty) AOF base, and the snapshot is silently bypassed. The drill discovered this on the first attempt; the recovery procedure below corrects for it.

## Steps

### Phase 1 — Try a plain restart first (no-cost sanity check)

If the loss looks transient (volume mounted but graphs missing, or after a host crash), the in-place AOF may still recover the data:

```bash
cd ~/workspace/homelab/homelab-apps/stacks/graphiti
docker compose restart falkordb graphiti-mcp
sleep 10
docker exec falkordb redis-cli GRAPH.LIST
```

If `GRAPH.LIST` returns the expected graphs, you are done. Otherwise continue.

### Phase 2 — Stop the stack

Stop the consumer first, then the data layer. This avoids graphiti-mcp seeing an empty graph and writing an empty marker.

```bash
cd ~/workspace/homelab/homelab-apps/stacks/graphiti
docker compose stop graphiti-mcp
docker compose stop falkordb
docker ps -a --filter name=graphiti-mcp --filter name=falkordb \
  --format 'table {{.Names}}\t{{.Status}}'
```

**Verify:** both containers `Exited`.

### Phase 3 — Preserve any remaining state, prepare a clean data dir

Before destroying anything, save what's there. This is the rollback path if the restore fails.

```bash
mv ~/.graphiti-data ~/.graphiti-data.preserved-$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p ~/.graphiti-data/appendonlydir
```

**Verify:** the preserved dir still has its `dump.rdb` and `appendonlydir/`. The new dir is empty but has the `appendonlydir/` subdir.

### Phase 4 — Promote the backup RDB into the AOF base position

```bash
DRILL_RDB=~/.local/state/graphiti-backup/rdb/$(readlink ~/.local/state/graphiti-backup/rdb/latest.rdb)
echo "Restoring from: $DRILL_RDB"

# Place backup RDB as AOF base file (sequence number 1, type b = base).
sudo cp -v "$DRILL_RDB" ~/.graphiti-data/appendonlydir/appendonly.aof.1.base.rdb

# Write a matching manifest. The 'seq 1' must agree with the filename.
echo "file appendonly.aof.1.base.rdb seq 1 type b" \
  | sudo tee ~/.graphiti-data/appendonlydir/appendonly.aof.manifest

# Empty incremental file so the server has something to append to.
sudo touch ~/.graphiti-data/appendonlydir/appendonly.aof.1.incr.aof

# Match ownership to what FalkorDB writes from inside the container.
sudo chown -R root:root ~/.graphiti-data/appendonlydir
ls -la ~/.graphiti-data/appendonlydir/
```

**Verify:** three files in `appendonlydir/`, all owned `root:root`, manifest contents `file appendonly.aof.1.base.rdb seq 1 type b`.

### Phase 5 — Start FalkorDB, verify it loaded the snapshot

```bash
cd ~/workspace/homelab/homelab-apps/stacks/graphiti
docker compose start falkordb
sleep 8
docker ps --filter name=falkordb --format 'table {{.Names}}\t{{.Status}}'
docker logs falkordb --since 30s 2>&1 | grep -E "Loading RDB|Done loading|Done decoding|Ready to accept|Error" | tail -20
```

**Acceptance — all of these MUST appear in the logs:**

- `Loading RDB produced by version <X>`
- `Done decoding graph <name>` (one per graph, e.g. 13 lines for the current stack)
- `Done loading RDB, keys loaded: <N>` with N matching the expected graph count's worth of keys (current production: 26)
- `DB loaded from base file appendonly.aof.1.base.rdb`
- `Ready to accept connections tcp`

**MUST NOT appear:**

- `Bad file format`
- `Permission denied`
- `Could not open`
- `keys loaded: 0` (this is the silent-bypass failure mode — see "If load shows 0 keys" below)

### Phase 6 — Start graphiti-mcp

```bash
docker compose start graphiti-mcp
sleep 12
docker ps --filter name=graphiti-mcp --format 'table {{.Names}}\t{{.Status}}'
docker logs graphiti-mcp --since 60s 2>&1 | grep -iE "Successfully initialized|Using LLM|Using Embedder|error|traceback" | tail -10
curl -sS -o /dev/null -w 'health=%{http_code}\n' http://127.0.0.1:8000/health
```

**Acceptance:**

- graphiti-mcp shows `Up <N> seconds (healthy)`.
- Logs include `Successfully initialized Graphiti client`, `Using LLM provider: gemini / gemini-2.5-flash-lite`, `Using Embedder provider: openai`.
- `health=200`.
- No traceback.

### Phase 7 — Verify restored data

```bash
# All graphs present
docker exec falkordb redis-cli GRAPH.LIST

# Heavy-graph node count (current load-bearing test graph: e3s06test1 ~ 308 nodes)
docker exec falkordb redis-cli --no-raw GRAPH.QUERY e3s06test1 \
  "MATCH (n) RETURN count(n)" | grep -A1 integer

# Sample entity names (sanity check that the restore actually has the data, not just empty graphs)
docker exec falkordb redis-cli --no-raw GRAPH.QUERY e3s06test1 \
  "MATCH (n:Entity) RETURN n.name LIMIT 5"
```

## Verification checklist

- [ ] `GRAPH.LIST` matches the operator's expectations (or known subset).
- [ ] The current load-bearing graph has its expected node count (current: `e3s06test1` = 308 nodes).
- [ ] No errors in `docker logs falkordb --since 5m`.
- [ ] No errors in `docker logs graphiti-mcp --since 5m`.
- [ ] `health=200` from `http://127.0.0.1:8000/health`.

## Rollback (if restore fails)

If any verification step fails, revert before debugging:

```bash
cd ~/workspace/homelab/homelab-apps/stacks/graphiti
docker compose stop graphiti-mcp falkordb
sudo rm -rf ~/.graphiti-data
# Use whichever preserved-* dir you created in Phase 3
sudo mv ~/.graphiti-data.preserved-<TS> ~/.graphiti-data
docker compose start falkordb
sleep 8
docker compose start graphiti-mcp
sleep 12
docker exec falkordb redis-cli GRAPH.LIST
```

If the preserved dir was already corrupt (i.e., the original loss event), there is no in-stack rollback — the snapshot was the only recovery path. Investigate offline before trying again with a different (older) snapshot from `~/.local/state/graphiti-backup/rdb/`.

## If load shows 0 keys

The most common silent-failure mode: you placed the backup as `~/.graphiti-data/dump.rdb` (root) instead of `~/.graphiti-data/appendonlydir/appendonly.aof.1.base.rdb` (with manifest). The server has AOF on, so it ignores root-level `dump.rdb` and starts empty.

Fix: stop the stack, redo Phase 4 (place inside `appendonlydir/` with a matching manifest), and restart. The drill's first attempt hit this exact failure; phase logs will confirm.

## Caveats

- **Cypher tarballs are not a recovery path.** The `~/.local/state/graphiti-backup/cypher/cypher-<TS>.tar.gz` files are response-format dumps for audit / portability per the ADR-007 amendment. They cannot be directly imported back into FalkorDB-Graphiti. Don't try. Use the RDB snapshot.
- **Embedding model lock-in.** Gemini Embedding 2 vectors stored in FalkorDB graphs are tied to that embedder model. If Google ever deprecates `gemini-embedding-2`, restore is fine but new queries against the restored data will need to re-embed. Out of scope for this runbook.
- **AOF base sequence numbering.** The drill used `seq 1` as a fresh start. If you want to preserve historical AOF sequence (e.g. roll forward from a richer pre-loss state), match the original manifest's seq number instead. The drill chose `1` for simplicity.
- **No password.** FalkorDB has no `requirepass`, so `redis-cli` works without `-a`. If a password is added later, every `redis-cli` invocation in this runbook needs `-a "$FALKORDB_PASSWORD"` (read from a vault, never echoed).
- **MCP `search_nodes` is currently broken on this stack** (returns empty for known-good queries pre- AND post-drill). Restore preserves data integrity but does not fix this pre-existing search defect — track separately. Use direct `GRAPH.QUERY` for verification, not MCP search.

## Cleanup (after 24 h of green)

The preserved dir from Phase 3 is your safety net. Once the restored stack has run cleanly for 24 h (no falkordb crashes, no graphiti-mcp errors, queries returning expected results), delete it:

```bash
sudo rm -rf ~/.graphiti-data.preserved-<TS>
```

Don't delete it earlier — if the restore had a subtle issue (missing recent writes, etc.) you want a clean rollback target.

## Operator log template

When you run this runbook in anger, fill this in and append it to the next quarterly drill evidence file:

```
Date / time (UTC):
Reason for restore (event):
Snapshot used (path + mtime):
Pre-restore graph count (if known):
Post-restore graph count:
Post-restore heavy-graph node count:
Total downtime:
Anything unexpected:
Outcome (PASS / PARTIAL / FAIL):
```
