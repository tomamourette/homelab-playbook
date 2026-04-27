# E3-S08.5 — `search_nodes` regression investigation

**Date:** 2026-04-27
**Author:** autonomous agent (Claude Opus 4.7), under tomamourette
**Branch:** `decommission/context-stack-phase-1`
**Bug:** MCP `search_nodes` returns `"No relevant nodes found"` against `e3s06test1` despite 260 indexed Entity nodes with populated 3072-dim `name_embedding`. The same query returned 4/5 strong top-1 hits during E3-S06 Test 2 earlier today.

**TL;DR:** Not an embedder bug, not a vector-index bug, not data corruption. graphiti-mcp's `search_nodes` MCP tool calls `client.search_(group_ids=[<one>])`, which (for FalkorDB only) **skips the per-group driver clone unless `len(group_ids) > 1`**. With a single `group_id`, the driver stays pointed at whichever FalkorDB graph was last selected — at boot, that is `default_db` (per `FALKORDB_DATABASE` env), which is empty. E3-S06's search worked only because the immediately-preceding `add_episode("...", group_id="e3s06test1")` mutated `self.driver._database` to `e3s06test1` as a side-effect; every container restart since (06:47Z, 09:32Z, 09:34Z) reset it to `default_db`. **Investigation only — no code or container state was changed.**

---

## Reproduction

### Verbatim MCP request and response

Submitted via the MCP HTTP transport from inside the container against
`http://127.0.0.1:8000/mcp`, after a clean `initialize` + `notifications/initialized`:

```json
{"jsonrpc":"2.0","id":2,"method":"tools/call",
 "params":{"name":"search_nodes",
           "arguments":{"query":"FalkorDB","group_ids":["e3s06test1"],"max_nodes":5}}}
```

Response:

```json
{"jsonrpc":"2.0","id":2,
 "result":{"content":[{"type":"text",
                       "text":"{\n  \"message\": \"No relevant nodes found\",\n  \"nodes\": []\n}"}],
           "structuredContent":{"result":{"message":"No relevant nodes found","nodes":[]}},
           "isError":false}}
```

### graphiti-mcp log lines emitted during the call

```
INFO:     127.0.0.1:44862 - "POST /mcp HTTP/1.1" 200 OK
2026-04-27 09:42:14 - mcp.server.lowlevel.server - INFO - Processing request of type CallToolRequest
2026-04-27 09:42:15 - httpx - INFO - HTTP Request: POST http://192.168.50.160:4000/v1/embeddings "HTTP/1.1 200 OK"
```

Embedder returns 200 OK. No exception. No retry. No warning. The request completes "successfully" with zero results — the failure mode the user observed.

---

## Hypotheses tested

### H1 — Embedder request failing silently

**Test:** call LiteLLM gateway directly from the graphiti-mcp container with the master key:

```bash
docker exec graphiti-mcp curl -sS http://192.168.50.160:4000/v1/embeddings \
  -H "Authorization: Bearer ${OPENAI_API_KEY}" -H "Content-Type: application/json" \
  -d '{"model":"gemini-embedding-2","input":"FalkorDB"}'
```

Returns a 3072-dim vector, first 5 floats `[-0.0020271805, 0.026372025, 0.0027829702, -0.010040411, -0.024237368]`. Norm-squared ≈ 1.0 (unit-normalised, as expected for cosine).

The same first 5 floats are **byte-identical** to the embedding stored on the `FalkorDB` Entity node in the graph. The embedder is healthy and produces the expected vector.

`docker exec graphiti-mcp curl ... /health/liveliness` returns 200. Network path is clean.

**Verdict: ruled out.** Embedder works.

### H2 — Vector index missing or stale

**Test:** `CALL db.indexes()` on `e3s06test1`:

```
Entity   [uuid, group_id, name, created_at, summary]   {uuid:[RANGE], group_id:[RANGE,FULLTEXT], name:[RANGE,FULLTEXT], summary:[FULLTEXT]}
```

There is **no vector index on `name_embedding`**, but FalkorDB's `vec.cosineDistance()` does not require one — it is a function evaluated per-row, not an indexed lookup. Confirmed by running the exact graphiti-core search Cypher manually with a self-supplied vector:

```cypher
MATCH (n:Entity {name: "FalkorDB"}), (m:Entity)
WITH n, m, (2 - vec.cosineDistance(m.name_embedding, n.name_embedding))/2 AS score
WHERE score > 0.6 RETURN m.name, score ORDER BY score DESC LIMIT 10
```

Returns 10 rows in 2.4 ms: `FalkorDB (1.0) → FalkorDB v4.18.1 (0.943) → FalkorDB AOF (0.929) → FalkorDB AUTH (0.919) → Neo4j (0.859) → Redis (0.815) → ...`. Vector math is healthy on the live data.

The fulltext side is also healthy: `CALL db.idx.fulltext.queryNodes("Entity", "FalkorDB")` returns the expected names. Both halves of the hybrid search work in isolation.

**Verdict: ruled out.** Indexes are fine.

### H3 — `group_ids` parameter encoding changed

**Test:** call MCP `search_nodes` with TWO `group_ids` instead of one:

```json
{"name":"search_nodes",
 "arguments":{"query":"FalkorDB","group_ids":["e3s06test1","default_db"],"max_nodes":5}}
```

Response (truncated):

```
"message": "Nodes retrieved successfully",
"nodes": [
  {"name":"FalkorDB AUTH",   "group_id":"e3s06test1", ...},
  {"name":"FalkorDB",        "group_id":"e3s06test1", ...},
  {"name":"FalkorDB AOF",    "group_id":"e3s06test1", ...},
  {"name":"FalkorDB v4.18.1","group_id":"e3s06test1", ...},
  {"name":"Redis",           "group_id":"e3s06test1", ...}
]
```

**Five strong hits** — exactly the same shape as E3-S06's Test 2 Q1. The only difference between this call and the failing one is `group_ids` length (2 vs 1). That is the smoking gun for the actual root cause (see below).

**Verdict: ruled in — but as a symptom of the deeper bug, not the cause.** The MCP tool wrapper passes `group_ids` through unchanged; the parameter shape is correct.

### H4 — graphiti-mcp version drift

```
mcp 1.26.0
graphiti-core 0.28.2
google-genai 1.73.1
Image graphiti-mcp-genai-bundled:e3-s04g built 2026-04-27 05:47:59 UTC (id ce41bd511e04)
```

Image timestamp is **before** E3-S06 (which started at 06:29Z). Same image has been running across E3-S06, E3-S07, and E3-S08. No drift. The Dockerfile's `:standalone` tag would only matter if the image were rebuilt, which it has not been.

**Verdict: ruled out.**

### H5 — Asyncio / connection pool regression

The single search call completes cleanly in ~1 s with no retries, no timeouts, no warnings. Independent direct-driver tests (below) show full functionality — just against the wrong target graph.

**Verdict: ruled out.**

---

## Root cause

### What's actually happening

graphiti-mcp's `search_nodes` MCP tool wraps `client.search_(query, config, group_ids=effective_group_ids, ...)` (graphiti_mcp_server.py:447). `client.search_` is decorated with `@handle_multiple_group_ids` (graphiti_core/decorators.py:29).

That decorator's body (decorators.py:48-54):

```python
if (
    hasattr(self, 'clients')
    and hasattr(self.clients, 'driver')
    and self.clients.driver.provider == GraphProvider.FALKORDB
    and group_ids
    and len(group_ids) > 1     # ← THIS GATE
):
    # fan out: one driver clone per group_id, run search, merge
    ...
```

For FalkorDB, **the per-group-id driver clone only runs when `len(group_ids) > 1`**. With a single group_id, the search runs against `self.clients.driver` as-is — whatever database that driver is pointed at.

graphiti-mcp constructs the driver **once at startup** (graphiti_mcp_server.py:218):

```python
falkor_driver = FalkorDriver(
    host=db_config['host'], port=db_config['port'],
    password=db_config['password'],
    database=db_config['database'],   # 'default_db' (from FALKORDB_DATABASE env / config.yaml)
)
```

`default_db` is empty (verified: `MATCH (n) RETURN count(n)` → 0). All real data lives in per-group-id graphs (`e3s06test1`, `e3s05flashlite`, `e3s06test3bitemp`, etc.).

When `search_nodes(group_ids=["e3s06test1"])` is called:
1. Decorator sees `len(group_ids) == 1` → skips the clone fan-out.
2. `node_similarity_search` runs `MATCH (n:Entity) WHERE n.group_id IN ["e3s06test1"] WITH n, vec.cosineDistance(n.name_embedding, vecf32($search_vector)) AS score WHERE score > 0.6 ...` against the driver's current graph (`default_db`).
3. `default_db` has zero nodes → zero matches → zero results.
4. graphiti-mcp returns `"No relevant nodes found"`.

No exception is raised because an empty graph produces an empty result set, not an error.

### Why E3-S06 Test 2 worked

graphiti-core's `add_episode` mutates the driver in place (graphiti.py:889):

```python
if group_id != self.driver._database:
    self.driver = self.driver.clone(database=group_id)
    self.clients.driver = self.driver
```

E3-S06 Test 2 ran search **immediately after** Test 1's 50-episode ingest into group `e3s06test1`. The last ingested episode left `self.driver._database = "e3s06test1"`. The search then ran against the right graph **as a side-effect of the prior write**, not as designed behavior.

Container restarts since E3-S06 (06:47Z for Test 5a, 09:32Z post-restore, 09:34Z, etc.) reconstruct the driver from compose env (`FALKORDB_DATABASE=default_db`) and the side-effect is gone. Hence the regression appears now.

### Direct driver-state proof

Same code path graphiti-mcp uses, run from inside the container:

```
factory db_cfg: {'host': 'falkordb', 'port': 6379, 'database': 'default_db'}
driver _database: default_db
--- 1 group_id (current MCP path) ---
count: 0
--- 2 group_ids (forces clone fan-out) ---
count: 10 (top: ['FalkorDB AUTH', 'FalkorDB', 'FalkorDB AOF'])
```

This is the same Graphiti(...) construction, the same search_() call, the same group_ids — only the count of group_ids differs. With one: 0 results. With two: 10 results.

### Sanity: dimensional truncation is NOT the cause

`graphiti_core.embedder.client.EMBEDDING_DIM = int(os.getenv('EMBEDDING_DIM', 1024))` is a module-level **default** (1024). The `OpenAIEmbedderConfig` is constructed with `embedding_dim=config.dimensions` (factories.py:275), which reads `dimensions: 3072` from `config-graphiti-mcp.yaml`. Live introspection confirms `embedder.config.embedding_dim == 3072` and `await embedder.create(["FalkorDB"])` returns 3072 floats. The `[: self.config.embedding_dim]` slice in `OpenAIEmbedder.create` (openai.py:60) is a no-op when len ≤ embedding_dim.

I tested deliberate 1024-dim truncation against the live graph: FalkorDB raises `ResponseError: Vector dimension mismatch, expected 3072 but got 1024`. The actual MCP search returns 0 results with **no error** — different failure signature. So truncation is not happening. (This was a useful intermediate finding worth recording in case `dimensions: 3072` ever drifts to 1024 in config — the symptom would be a logged ResponseError, not silent zero hits.)

---

## Proposed fix

### Recommended (E3-S08.6)

**Option A — fix the call site (smallest blast radius, ~10 lines):**

In `homelab-apps/stacks/graphiti/...` we can't change graphiti-core's decorator, but we can change graphiti-mcp's tool wrapper. Either:

A1. **Wrap the driver before each search.** In `graphiti_mcp_server.py:447`, before `client.search_(...)`, when `effective_group_ids` has exactly one element, set the driver explicitly:

```python
if len(effective_group_ids) == 1 and config.database.provider.lower() == 'falkordb':
    # Work around graphiti-core/decorators.py:54 which only fans out for >1 group_ids.
    # FalkorDB stores per-group_id graphs as separate databases; with 1 group_id the
    # decorator skips the clone, leaving the driver pointed at the boot-time database
    # (FALKORDB_DATABASE, default 'default_db'). We force it here.
    client.driver = client.driver.clone(database=effective_group_ids[0])
    client.clients.driver = client.driver
```

This matches what `add_episode` already does. Same pattern applies to `search_nodes`, `search_facts`, `search_memory_nodes`, `search_memory_facts`, `get_episodes` — anywhere a `group_ids` filter is passed.

A2. **Always pass at least two group_ids.** Append a sentinel like `"__noop_force_fanout__"` whenever `len(group_ids) == 1`. Crude but very small. Loses the fact that single-group is the common case and forces an extra concurrent task that returns nothing.

A1 is cleaner. Estimated effort: ~30 minutes including writing/running smoke against `e3s06test1`. Bind-mount the patched `graphiti_mcp_server.py` into the existing image (no rebuild needed), or roll a new local image tag.

**Option B — fix graphiti-core's decorator (correct but larger blast radius):**

In `graphiti_core/decorators.py`, change `len(group_ids) > 1` to `len(group_ids) >= 1` for FalkorDB. Or keep the >1 check for the fan-out merge logic but add a single-group fast path that still calls `driver.clone(database=group_ids[0])` before the function call. Either form is a one-line patch in upstream.

Risk: this is a vendored dependency in the upstream image. Patching it requires a bind-mount or a Dockerfile `RUN sed -i ...` step, which means E3-S04g-style patch maintenance across upstream rolls. Not preferred.

**Option C — accept and document.** Standardize on always passing 2+ group_ids in any agent that calls search. Brittle (any future caller will hit the same trap) and not what the MCP tool's docstring promises (`group_ids: list of group identifiers...`).

### Recommendation

**Option A1.** It's surgical, the bug is in graphiti-mcp's tool layer (where the contract `group_ids[]` should mean "scope the search to these graphs"), and the fix matches the in-class pattern that `add_episode` already uses. The same wrapper logic should apply to all search-family MCP tools (`search_nodes`, `search_facts`, `search_memory_nodes`, `search_memory_facts`).

Estimated effort: **30-45 minutes** including the patch, smoke test against `e3s06test1`, and a minimal regression smoke that exercises both the 1-group and 2-group paths.

### Side-quest to consider in the same fix

`add_episode`'s mutate-in-place behavior (`self.driver = self.driver.clone(...)`) means each ingest has a side effect that persists across calls. After A1 lands, search_nodes's behavior becomes deterministic (no longer depends on prior `add_episode` order), but `add_episode` itself is still order-dependent. That's an upstream design choice; not blocking E3-S08.6.

---

## Risks

1. **Wrapping `client.driver` in the MCP tool changes shared state for any concurrent request.** The MCP server uses a single `Graphiti` instance (graphiti-mcp's `graphiti_service.get_client()`). Two simultaneous `search_nodes` calls with different group_ids would race on `client.driver = client.driver.clone(...)`. Need to either (a) clone-and-pass-through-`driver=` kwarg to `search_()` (which `search_` accepts, line 1416) instead of mutating `self.client.driver`, or (b) add a per-call lock. Option (a) is preferred and is what graphiti-core's decorator does internally for the fan-out path:

   ```python
   results = await client.search_(
       query=query,
       config=NODE_HYBRID_SEARCH_RRF,
       group_ids=effective_group_ids,
       search_filter=search_filters,
       driver=client.driver.clone(database=effective_group_ids[0])
                if len(effective_group_ids) == 1 else None,
   )
   ```

   But: `search_` only forwards `driver=` to the inner `search()` helper; the decorator wraps `search_` itself and does NOT receive that kwarg. Need to verify `search_(driver=...)` is honored when the decorator skips the clone (probably yes — `search()` uses the `driver` argument if not None — but verify in the fix story).

2. **Other MCP tools (`add_memory`, `get_episodes`, `delete_episode`) already work correctly via `add_episode`'s in-place clone.** A1 must not perturb that path. Smoke each tool family in E3-S08.6.

3. **`get_episodes(group_ids=[...])`** has the **same bug** (it uses the same single-driver state). The first call after a restart may return no episodes for a non-default group. Confirmed at the architectural level (uses the same driver, same `_database` field); not yet reproduced. Worth re-running E3-S08 Phase 6 after the fix to confirm episode counts are reachable from the MCP layer (the post-restore count check used direct FalkorDB Cypher, so it didn't catch this).

4. **The E3-S06 PASS verdict** for Test 2 is reframed but not invalidated — the search results were correct, the underlying mechanism that produced them was incidental. The data quality findings (96% extraction, 4/5 top-1 hits, etc.) all stand. But "MCP `search_nodes` works" should be re-asserted in E3-S08.6 after the fix, **without** an ingest immediately preceding the search.

5. **No risk to data integrity.** This is a query-layer routing bug. No data has been written to the wrong graph. All 13 graphs are intact (per E3-S08 Phase 6 verification). The 91-second restore-drill RTO finding is unaffected.

---

## Files referenced

- `/home/developer/workspace/homelab/homelab-apps/stacks/graphiti/docker-compose.yml` — `FALKORDB_DATABASE=default_db` env at line ~158
- `/home/developer/workspace/homelab/homelab-apps/stacks/graphiti/config-graphiti-mcp.yaml` — `dimensions: 3072` at line 58 (verified correct, NOT the cause)
- Inside the running container:
  - `/app/mcp/src/graphiti_mcp_server.py:218` — driver construction with `database=db_config['database']`
  - `/app/mcp/src/graphiti_mcp_server.py:447` — `client.search_(group_ids=effective_group_ids, ...)`
  - `/app/mcp/.venv/lib/python3.11/site-packages/graphiti_core/decorators.py:29-54` — `handle_multiple_group_ids` decorator with the `len(group_ids) > 1` gate
  - `/app/mcp/.venv/lib/python3.11/site-packages/graphiti_core/graphiti.py:889` — `add_episode`'s `self.driver = self.driver.clone(database=group_id)` (the side-effect that hid the bug during E3-S06)
  - `/app/mcp/.venv/lib/python3.11/site-packages/graphiti_core/driver/falkordb_driver.py:307` — `FalkorDriver.clone(database=...)` implementation
- E3-S06 evidence: `homelab-playbook/docs/context-stack/sprint-3/e3-s06-evidence.md`
- E3-S08 evidence: `homelab-playbook/docs/context-stack/sprint-3/e3-s08-evidence.md` (caveat in Phase 6 documents the same observation against the preserved data dir)

No code or config was modified during this investigation. All changes are deferred to E3-S08.6.
