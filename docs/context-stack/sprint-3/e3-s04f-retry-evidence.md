# E3-S04f-retry — Cloud-LLM Smoke PASS (Gemini 2.5 Flash-Lite)

- **Date:** 2026-04-27
- **Story:** E3-S04f-retry (re-run of E3-S04f-test with hyphen-free `group_id`)
- **Branch:** `decommission/context-stack-phase-1`
- **Status:** **PASS** — all 6 smoke substeps green; cloud-LLM extraction + dedup + persistence + retrieval all verified end-to-end.
- **Predecessor:** [`e3-s04f-test-evidence.md`](./e3-s04f-test-evidence.md) (uncommitted) — that run proved the cloud-LLM extraction path works but failed at FalkorDB-driver dedup because the group_id `e3-s05-flash-lite-test` contained hyphens that broke RediSearch query escaping. This retry uses `e3s05flashlite` to sidestep that orthogonal bug; the underlying `falkordb_driver.py` hyphen-quoting issue is filed for E3-S04h.

## What changed since the previous run

Identical methodology and config diff as E3-S04f-test. Only behavioural delta:

| Aspect | E3-S04f-test (previous) | E3-S04f-retry (this) |
|---|---|---|
| `group_id` | `e3-s05-flash-lite-test` | `e3s05flashlite` (no hyphens) |
| Episode name | "E3-S04f Flash-Lite test" | "E3-S04f retry — Flash-Lite end-to-end" |
| Smoke outcome | extraction OK, persistence FAILED at RediSearch syntax error | full PASS, 10 entities + 10 edges persisted |

All four upstream workarounds remain in place and untouched (factories.py bind-mount, gemma4-26b-json LiteLLM alias, OPENAI_BASE_URL env, gemma-hybrid-proxy).

## Configuration delta (committed in homelab-apps)

`stacks/graphiti/config-graphiti-mcp.yaml`:

```diff
 llm:
-  provider: "openai"          # LiteLLM gateway is OpenAI-API-compatible
-  model: ${MODEL_NAME:gemma4-26b-text}
+  # E3-S04f-retry: provider: gemini for Graphiti's LLM extraction.
+  # Workarounds (factories.py mount, gemma4-26b-json alias, OPENAI_BASE_URL) stay
+  # in place. Cleanup deferred to E3-S04g after this verification pass.
+  provider: "gemini"
+  model: ${LLM_MODEL:gemini-2.5-flash-lite}
   max_tokens: ${LLM_MAX_TOKENS:1500}
   providers:
+    gemini:
+      api_key: ${GEMINI_API_KEY}
     openai:
       api_key: ${LITELLM_MASTER_KEY}
       api_url: ${LITELLM_BASE_URL:http://192.168.50.160:4000/v1}
```

Embedder block UNCHANGED (`provider: openai` → `gemini-embedding-2` via LiteLLM gateway).

`stacks/graphiti/.env` (gitignored): added `GEMINI_API_KEY=…` (39 chars, sourced from `/opt/litellm-gateway/.env` on ct-ai-01). File mode 600. Three keys total (`LITELLM_MASTER_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`).

## Container state

Identical missing-`google-genai` issue as the previous run — the `zepai/knowledge-graph-mcp:standalone` image's venv lacks the SDK. Workaround (transient, not committed): `docker exec graphiti-mcp uv pip install --python /app/mcp/.venv/bin/python 'google-genai>=1.62.0'` then `docker compose restart graphiti-mcp` (NOT `--force-recreate`, which would wipe the install).

Persistent fix (custom Dockerfile or entrypoint init script) is the responsibility of **E3-S04g** — out of scope for this retry.

Init logs after restart:

```
2026-04-27 05:23:40 - graphiti_mcp_server - INFO -   - LLM: gemini / gemini-2.5-flash-lite
2026-04-27 05:23:40 - graphiti_mcp_server - INFO -   - Embedder: openai / gemini-embedding-2
2026-04-27 05:23:40 - services.factories - INFO - Creating Gemini client
2026-04-27 05:23:40 - graphiti_mcp_server - INFO - Using LLM provider: gemini / gemini-2.5-flash-lite
2026-04-27 05:23:40 - graphiti_mcp_server - INFO - Using Embedder provider: openai
```

`docker ps`: `graphiti-mcp Up 12 seconds (healthy)`. Health endpoint: 200.

## Smoke test results — group_id `e3s05flashlite`

| Step | Action | HTTP | Result | Latency |
|------|--------|------|--------|---------|
| 5a | `initialize` | 200 | session_id `96d015a78...` (32 chars) | <1s |
| 5b | `notifications/initialized` | 202 | accepted | <1s |
| 5c | `add_memory` (queued) | 200 | `Episode '…' queued for processing in group 'e3s05flashlite'` | 0.006s submit |
| 5d | Queue worker outcome | — | **`Successfully processed episode None for group e3s05flashlite`**, `Completed add_episode in 7528 ms` | 7.5s end-to-end |
| 5e | `search_nodes` | 200 | **10 nodes** retrieved with rich summaries | 0.46s |
| 5f | `get_episodes` | 200 | **1 episode** with full content + correct group_id | 0.005s |

**ALL 6 substeps PASS.** Acceptance threshold (≥4 sensible entities + edges + temporal facts) exceeded.

### Brief vs. server schema deviation (non-fatal)

The brief's `get_episodes` payload used `group_id` (singular) and `last_n` — the actual MCP server schema (graphiti-mcp v1.26.0) accepts `group_ids: array[string]` and `max_episodes: integer`. First call with the brief's arg names returned `episodes: []` because the singular `group_id` was silently ignored as an extra arg. Second call with the schema-correct payload returned the episode immediately. This is a brief-text bug, not a smoke-test failure — the server itself behaved correctly in both calls (returned 200 + a structured response in both cases). Documenting here per the rule "if you hit something that contradicts prior evidence, surface it as deviation, don't silently re-discover."

## Entity list (Gemini 2.5 Flash-Lite extracted, persisted to FalkorDB)

| # | Name | Labels | Summary (excerpt) |
|---|------|--------|-------------------|
| 1 | `homelab Context Stack Sprint 3` | Entity, Event | reached an end-to-end Graphiti memory write; used Gemini 2.5 Flash-Lite for entity extraction |
| 2 | `Context Stack` | Entity, Document | launched to decommission MemPalace and OMEGA; in favor of GitNexus, Graphiti, LLM Wiki |
| 3 | `Graphiti` | Entity | end-to-end Graphiti memory write; launched in favor of Graphiti |
| 4 | `entity extraction` | Entity, Topic | performed entity extraction using Gemini 2.5 Flash-Lite |
| 5 | `MemPalace` | Entity, Organization | Context Stack launched to decommission MemPalace |
| 6 | `LLM Wiki` | Entity, Document | Context Stack launched in favor of an LLM Wiki |
| 7 | `Gemini 2.5 Flash-Lite` | Entity | used for entity extraction |
| 8 | `OMEGA` | Entity, Organization | Context Stack launched to decommission OMEGA |
| 9 | `GitNexus` | Entity, Organization | Context Stack launched in favor of GitNexus |
| 10 | `graph` | Entity, Topic | FalkorDB persists the graph |

**Quality:** 10/10 sensible English noun-phrases or proper-nouns. All six product/system names from the episode are present. Both technology versions captured. Backend (`FalkorDB` was implicitly captured via the `PERSISTS` edge to `graph`). One mild gap: `Tom Amourette` did not promote to a discrete Person entity — the operator surfaces in the launched-by fact, but Flash-Lite chose to encode it as a relation rather than a node. That gap is responsible for the single dropped edge (see below).

## Edge list (10 facts persisted with temporal metadata)

| # | Relation | Fact | valid_at |
|---|----------|------|----------|
| 1 | REPLACED_BY | The Context Stack product was launched in favor of an LLM Wiki | 2026-04-25 |
| 2 | PERFORMED_ACTION | Sprint 3 reached an end-to-end Graphiti memory write | 2026-04-26 |
| 3 | REPLACED_BY | Context Stack launched in favor of GitNexus | 2026-04-25 |
| 4 | PERFORMED_ACTION | Sprint 3 performed entity extraction using Gemini 2.5 Flash-Lite | 2026-04-26 |
| 5 | USED_ENTITY | Sprint 3 used Gemini 2.5 Flash-Lite for entity extraction | 2026-04-26 |
| 6 | REPLACED_BY | Context Stack launched in favor of Graphiti | 2026-04-25 |
| 7 | DECOMMISSIONED_IN_FAVOR_OF | Context Stack launched to decommission OMEGA | 2026-04-25 |
| 8 | DECOMMISSIONED_IN_FAVOR_OF | Context Stack launched to decommission MemPalace | 2026-04-25 |
| 9 | PERSISTS | FalkorDB persists the graph | 2026-04-27 |
| 10 | HANDLES | Gemini Embedding 2 handles vector encoding | 2026-04-27 |

**Quality:** all 10 edges have plausible relation labels. Temporal `valid_at` metadata is correctly aligned with the episode's narrative dates (launch=2026-04-25, sprint work=2026-04-26, ambient state=now). One edge was dropped during processing: `LAUNCHED_BY` — its target node (presumably "Tom Amourette") was not in the entity set, so graphiti emitted `Target entity not found in nodes for edge relation: LAUNCHED_BY` and skipped it. Non-fatal; the rest of the graph completed cleanly.

## End-to-end latency

| Phase | Latency |
|---|---|
| add_memory submit (HTTP roundtrip) | 6 ms |
| Queue worker pick-up to completion | 7.5 s |
| Total submit → search-visible | ~7.5 s |

Massive improvement over the 30-300s local-Gemma cycles documented in S04c-S04e. One Gemini API call, HTTP 200, no retries, no Pydantic validation errors, no schema mismatch — same clean path the previous test demonstrated, now followed through to durable graph state.

## Why this run succeeded where the previous one failed

The only effective change between the two runs was the `group_id` value:

- Previous: `e3-s05-flash-lite-test` (hyphens + leading-digit segments) → `RediSearch: Syntax error at offset 14 near e3` during dedup
- This run: `e3s05flashlite` (alphanumeric, no separators) → all RediSearch fulltext queries parsed cleanly

This confirms the previous run's hypothesis verbatim: **the hyphen escaping defect in `graphiti_core/driver/falkordb_driver.py` is provider-agnostic** — it would have triggered identically under the local-Gemma path. The cloud-LLM swap and the FalkorDB driver bug are orthogonal concerns; this retry isolates them by sidestepping the latter.

## Decision: COMMIT

Per the brief's hard rules:

- All 5a–5f passed → no rollback
- Quality gate (≥4 sensible entities + edges + temporal facts) exceeded → no rollback
- Zero workaround removed, zero workaround modified → safe
- `.env` confirmed in `.gitignore` (`**/.env` rule at line 13) → safe to commit config without secret leakage

Two commits made:

- **homelab-apps** — `stacks/graphiti/config-graphiti-mcp.yaml` config swap to `provider: gemini` / `gemini-2.5-flash-lite`.
- **homelab-playbook** — this evidence file (under `docs/context-stack/sprint-3/`).

## Workarounds still active (deliberately, deferred to E3-S04g)

| Workaround | Status | Removal target |
|---|---|---|
| `factories.py.patched` bind-mount on graphiti-mcp | ACTIVE | E3-S04g (no longer needed under gemini provider — was a Pydantic schema patch for openai/Gemma path) |
| `gemma4-26b-json` LiteLLM alias usage in graphiti config | INACTIVE for graphiti, ACTIVE for other consumers | Keep alias; only graphiti's reference removed (already done by this commit) |
| `OPENAI_BASE_URL=…/v1` env on graphiti-mcp container | ACTIVE | E3-S04g (graphiti-core's gemini path doesn't read OPENAI_BASE_URL; safe to drop) |
| `gemma-hybrid-proxy` upstream reasoner | ACTIVE | Keep — used by Hermes / OWUI / other consumers; nothing to do for graphiti |
| Transient `google-genai` install in container venv | ACTIVE-but-fragile (wipes on `--force-recreate`) | E3-S04g (custom Dockerfile or entrypoint init script) |

## Next stories

- **E3-S04g** (now unblocked) — workaround cleanup: remove factories.py mount, drop OPENAI_BASE_URL env from graphiti-mcp, ship a custom Dockerfile (or entrypoint pip-install hook) so `google-genai` survives `--force-recreate` and image refreshes. Target: green smoke-test reproducible from a clean `docker compose up -d` with no manual `docker exec` step.
- **E3-S04h** (separate, low-priority) — patch `graphiti_core/driver/falkordb_driver.py` hyphen-quoting in RediSearch query builder so realistic group_ids like `proj-foo` work natively. Workaround in the meantime: sanitize/strip hyphens at the MCP layer before persisting.
- **E3-S05** (full) — wider functional smoke: multi-episode ingestion, cross-group fact retrieval, Tom-as-Person edge promotion sanity-check, latency budget characterization under sustained load.

## Files

- Test branch: `decommission/context-stack-phase-1`
- Modified: `homelab-apps/stacks/graphiti/config-graphiti-mcp.yaml`
- Modified (gitignored): `homelab-apps/stacks/graphiti/.env` (added `GEMINI_API_KEY`)
- Evidence (this file, committed): `homelab-playbook/docs/context-stack/sprint-3/e3-s04f-retry-evidence.md`
- Evidence (predecessor, uncommitted): `homelab-playbook/docs/context-stack/sprint-3/e3-s04f-test-evidence.md`
