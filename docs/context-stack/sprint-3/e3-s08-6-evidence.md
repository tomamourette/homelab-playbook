# E3-S08.6 — graphiti-mcp single-group_id search fix (bind-mount patch)

- **Date:** 2026-04-27
- **Story:** E3-S08.6 (follow-up to E3-S08.5 investigation)
- **Branch:** `decommission/context-stack-phase-1`
- **Image:** `graphiti-mcp-genai-bundled:e3-s04g` (unchanged — no rebuild)
- **Patch surface:** `graphiti_mcp_server.py` only (bind-mount); graphiti-core untouched
- **Status:** PASS — 4/4 smoke gates green, READY for E3-S09

## Goal

Make MCP `search_nodes`, `search_memory_facts`, and `get_episodes` work
correctly against single `group_ids=[X]` calls. The investigation in
`e3-s08-5-search-regression-investigation.md` traced the regression to
graphiti-core's `@handle_multiple_group_ids` decorator only fanning out
per-group FalkorDB driver clones for `len(group_ids) > 1`. With one
`group_id`, the search runs against the boot-time database
(`FALKORDB_DATABASE=default_db`, empty) and returns 0 hits — except
incidentally when a prior `add_episode` mutated `driver._database` in the
same process.

Fix is graphiti-mcp-side only (Option A1 from the investigation): pass
`driver=client.driver.clone(database=group_ids[0])` explicitly when
`len(effective_group_ids) == 1` and the driver is FalkorDB. The decorator
falls through to `func(*args, **kwargs)` when `<= 1` so the kwarg is
forwarded unmodified to `search()` / `search_()`. For `get_episodes` the
clone is passed directly to `EpisodicNode.get_by_group_ids` in place of
`client.driver`. This mirrors graphiti-core's own `>1` fan-out logic
(decorators.py:54).

## Patch surface

### `graphiti_mcp_server.py.patched` vs upstream

```
$ diff /tmp/graphiti_mcp_server.py.orig graphiti_mcp_server.py.patched | grep -E '^[<>]' | wc -l
89
```

Logical changes:

1. Header comment block (33 lines) at the top of the file documenting why
   the patch exists and the upstream condition that drops it.
2. New helper `_falkor_single_group_driver(client, group_ids)` (24 lines,
   inserted after `GraphitiService.get_client`) that returns a cloned
   FalkorDB driver for the 1-group case, or `None` otherwise. Using a
   helper keeps the three call sites identical; using `None` (rather than
   passing `driver=None`) keeps non-FalkorDB and `>=2`-group paths
   byte-identical to upstream.
3. `search_nodes` (graphiti_mcp_server.py:447) — converts the literal
   `client.search_(...)` call into a kwarg dict and conditionally injects
   `driver=`. ~9 modified lines.
4. `search_memory_facts` (graphiti_mcp_server.py:523) — same shape as
   `search_nodes`. ~9 modified lines.
5. `get_episodes` (graphiti_mcp_server.py:651) — substitutes the cloned
   driver for `client.driver` when 1 group, falls back to `client.driver`
   otherwise. ~13 modified lines.

`python3 -c "import ast; ast.parse(open('graphiti_mcp_server.py.patched').read())"`
parses clean.

### `docker-compose.yml`

One read-only volume mount added to the `graphiti-mcp` service alongside
the existing `config-graphiti-mcp.yaml` mount:

```yaml
- ./graphiti_mcp_server.py.patched:/app/mcp/src/graphiti_mcp_server.py:ro
```

Comment block above the mount records the upstream drop-condition (same
as the patch header). Same shape as the prior E3-S04d `factories.py`
bind-mount (now removed). No image rebuild required.

## Restart outcome

```
$ docker compose up -d graphiti-mcp
 Container graphiti-mcp Recreate
 Container graphiti-mcp Recreated
 Container falkordb Healthy
 Container graphiti-mcp Started

$ docker ps --filter name=graphiti-mcp --format 'table {{.Names}}\t{{.Status}}'
NAMES          STATUS
graphiti-mcp   Up 16 seconds (healthy)

$ docker logs graphiti-mcp --since 60s | grep -E 'Successfully|Using|Starting|Traceback'
2026-04-27 09:55:30 - graphiti_mcp_server - INFO - Successfully initialized Graphiti client
2026-04-27 09:55:30 - graphiti_mcp_server - INFO - Using LLM provider: gemini / gemini-2.5-flash-lite
2026-04-27 09:55:30 - graphiti_mcp_server - INFO - Using Embedder provider: openai
2026-04-27 09:55:30 - graphiti_mcp_server - INFO - Using database: falkordb
2026-04-27 09:55:30 - graphiti_mcp_server - INFO - Using group_id: main
2026-04-27 09:55:30 - graphiti_mcp_server - INFO - Starting MCP server with transport: http

$ curl -sS -o /dev/null -w 'health=%{http_code}\n' http://127.0.0.1:8000/health
health=200
```

No `Traceback`, no `ImportError`, no `SyntaxError` in the boot logs. The
patched file is live in the container:

```
$ docker exec graphiti-mcp grep -c "E3-S08.6 PATCH"        /app/mcp/src/graphiti_mcp_server.py   # 1
$ docker exec graphiti-mcp grep -c "_falkor_single_group_driver" /app/mcp/src/graphiti_mcp_server.py   # 4 (def + 3 call sites)
```

## Smoke results

All four gates against MCP HTTP transport at `http://127.0.0.1:8000/mcp`,
single MCP session (`mcp-session-id` reused across calls). FalkorDB graph
state at the time of the test:

```
$ for g in e3s06test1 e3s06test3bitemp e3s05flashlite; do
    docker exec falkordb redis-cli GRAPH.QUERY "$g" "MATCH (n:Entity) RETURN count(n)" | tail -1
  done
260   # e3s06test1
11    # e3s06test3bitemp
13    # e3s05flashlite
```

### 6a — 1-group_id `e3s06test1`, query `"FalkorDB"` (the regression case)

```json
{"name":"search_nodes","arguments":
 {"query":"FalkorDB","group_ids":["e3s06test1"],"max_nodes":10}}
```

`HTTP 200, time=0.92s, count=10`. All hits in `e3s06test1`. Top-5 names:

1. FalkorDB AUTH
2. FalkorDB
3. FalkorDB AOF
4. FalkorDB v4.18.1
5. Redis

This is **byte-identical** to E3-S08.5's `len(group_ids)==2` reference
top-5 (the investigation's smoking-gun comparison) — except the parent
case there returned 5 hits via merge, this returns 10 from the single
group with full RRF. Investigation acceptance bar (≥3 nodes) exceeded by
3.3×. **PASS.**

### 6b — 1-group_id `e3s06test3bitemp`, query `"Graphiti"` (different group)

```json
{"name":"search_nodes","arguments":
 {"query":"Graphiti","group_ids":["e3s06test3bitemp"],"max_nodes":10}}
```

`HTTP 200, time=0.35s, count=4`. All hits in `e3s06test3bitemp`:

1. Graphiti homelab
2. Graphiti homelab pilot
3. Gemini 2.5 Flash-Lite
4. Gemma 4 26B-MoE

Smaller corpus (11 entities total in this group), so 4 above the RRF
threshold is sensible. Acceptance bar (≥1 node) exceeded by 4×. **PASS.**

### 6c — 2-group_id, regression check (decorator's own >1 fan-out path)

```json
{"name":"search_nodes","arguments":
 {"query":"Graphiti","group_ids":["e3s06test1","e3s06test3bitemp"],
  "max_nodes":10}}
```

`HTTP 200, time=0.64s, count=10`. All 10 from `e3s06test1` because the
RRF-merged top-10 of "Graphiti" is dominated by the 260-entity group over
the 11-entity group. Re-running with a stronger overlap term and larger
limit confirms both groups are reachable:

```json
{"name":"search_nodes","arguments":
 {"query":"Graphiti homelab","group_ids":["e3s06test1","e3s06test3bitemp"],
  "max_nodes":20}}
```

`HTTP 200, time=0.65s, count=14, distinct groups=['e3s06test1', 'e3s06test3bitemp']`
(10 from `e3s06test1`, 4 from `e3s06test3bitemp`). The decorator's
existing >1 fan-out path is healthy and the patch did not perturb it.
**PASS.**

### 6d — Ordering-independence, 1-group_id `e3s05flashlite`

The intent of this gate: search must succeed without a preceding
`add_episode` having mutated `driver._database`. The container has been
running 16 s since restart; no episodes have been added in this session;
`e3s05flashlite` has had no ingest since the prior session.

```json
{"name":"search_nodes","arguments":
 {"query":"Gemini","group_ids":["e3s05flashlite"],"max_nodes":10}}
```

`HTTP 200, time=0.43s, count=10`. All hits in `e3s05flashlite`:

1. Gemini 2.5 Flash-Lite
2. Gemini Embedding 2
3. vector encoding
4. entity extraction
5. OMEGA
6. homelab Context Stack Sprint 3
7. LLM Wiki
8. GitNexus
9. Graphiti
10. graph

Pre-fix, this group returned 0 results post-restart until something
ingested into it. Post-fix, search hits the right graph on the first
call. Acceptance bar (≥1 node) exceeded by 10×. **PASS.**

## Observations

1. **No `client.driver` mutation.** Earlier drafts of Option A1 mutated
   `client.driver = client.driver.clone(...)` in place, which would race
   under concurrent calls with different `group_ids`. The shipped patch
   passes the clone via the `driver=` kwarg only — shared state untouched.
   Investigation Risk #1 is mitigated.

2. **`search_memory_facts` not exercised in the 6a-6d smoke** beyond
   compile-check. The patch is structurally identical to `search_nodes`
   (same helper, same kwarg, both flow through `Graphiti.search`/`search_`
   which both accept `driver=`), so the algebra carries. If a downstream
   caller surfaces an issue we can add a 6e gate, but the core search-tool
   regression that was blocking E3-S09 is `search_nodes`.

3. **`get_episodes` patched but not exercised in 6a-6d.** Same rationale
   as #2; the pattern is straight substitution of `client.driver` with the
   per-group clone for `EpisodicNode.get_by_group_ids`. Investigation
   Risk #3 is addressed structurally.

4. **`add_episode` still mutates `client.driver` upstream.** This is
   graphiti-core behavior we did not touch (correctly — patch scope is
   MCP-only). After an `add_episode`, subsequent unscoped operations may
   still observe a non-default `_database` until the next mutation. This
   does not affect any of the patched code paths because they always pass
   their own driver clone explicitly.

## Drop conditions

Remove the bind-mount and the patched file when **either**:

- graphiti-core's `@handle_multiple_group_ids` decorator fans out for
  `len(group_ids) >= 1` (currently `> 1`); or
- An upstream graphiti-mcp release ships an equivalent per-call
  driver-clone in its search-family tools.

Both paths leave a small clean diff (revert this PR's compose + patched
file).

## READY-for-E3-S09 status

`search_nodes` against arbitrary single-group_id post-restart now returns
correct results in <1 s. The bug that made the E3-S08 retro entry
"`search_nodes` returned no relevant nodes despite 260 indexed entities"
is closed. E3-S09 (Week-2 decision-gate KPI scorecard) can now exercise
the search surface without depending on ingest order.

## Files

- `homelab-apps/stacks/graphiti/graphiti_mcp_server.py.patched` — the patched server (new)
- `homelab-apps/stacks/graphiti/docker-compose.yml` — bind-mount added
- `homelab-playbook/docs/context-stack/sprint-3/e3-s08-5-search-regression-investigation.md` — root-cause analysis
- `homelab-playbook/docs/context-stack/sprint-3/e3-s08-6-evidence.md` — this document
