# E3-S04d — factories.py bind-mount patch + E3-S05 smoke: evidence

**Date**: 2026-04-26
**Story**: E3-S04d (graphiti-mcp factories.py override — `OpenAIClient` → `OpenAIGenericClient` so the LLM client uses `chat.completions.create` instead of `responses.parse`), bundled with the E3-S05 MCP smoke test.
**Branch**: `feature/context-stack-e3-graphiti`
**Status**: **PARTIAL PASS** — option D bind-mount patch is correct and in effect; graphiti-mcp now hits `/v1/chat/completions` against the LiteLLM gateway as designed. **E3-S05 smoke FAILS at extraction step (5d)** due to a separate, gateway-side LiteLLM routing bug on the `gemma4-26b-json` alias (the underlying `model:` value carries a stale `chat_completions/` prefix from the option-A attempt that never got fully reverted, or a parallel config drift; see §6). Per spike hard-rule "no retries on smoke-test failure", we stopped at the failure and captured. **READY for E3-S04e** (gateway-config fix on `gemma4-26b-json`), then re-run smoke.

---

## 1. Why option D

Option A (E3-S04c — single-line model-prefix change `model: openai/chat_completions/gemma4-26b-text` to activate LiteLLM's `/v1/responses` → `/v1/chat/completions` bridge) **failed at the gateway layer**: LiteLLM 1.83.13 did not activate the bridge for our OpenAI-compatible custom upstream. See `e3-s04c-evidence.md` §3.

Option B (LiteLLM upgrade) was rejected because the same code path is suspected to fail the same way on newer versions, and we did not want to take an upgrade risk on a centralized gateway used by Hermes / OWUI / others.

Option C (proxy-shim a `/v1/responses` endpoint) was rejected as additional moving parts.

Option D — the documented fallback in `e3-s04c-investigation.md` §Verdict's "Why not option D" rationale, which we are now executing because option A's failure is verified — is the cleanest fix: bind-mount a patched `factories.py` into graphiti-mcp so the `openai` provider case dispatches to `OpenAIGenericClient` (which uses `chat.completions.create` with `response_format={'type':'json_schema',...}`) instead of `OpenAIClient` (which uses `responses.parse`). The gateway path stays purely on `/v1/chat/completions`, which LiteLLM bridges natively for any OpenAI-protocol upstream.

---

## 2. The patch — diff vs. upstream factories.py

Two chunks. Source extracted from inside the live container (`docker exec graphiti-mcp cat /app/mcp/src/services/factories.py`, 435 lines, mcp-server v1.0.2 / graphiti-core 0.28.2). Patched copy at `homelab-apps/stacks/graphiti/factories.py.patched` (442 lines).

```diff
--- /tmp/factories.py.orig
+++ homelab-apps/stacks/graphiti/factories.py.patched
@@ -19 +19,25 @@
-from graphiti_core.llm_client import LLMClient, OpenAIClient
+from graphiti_core.llm_client import LLMClient, OpenAIClient  # noqa: F401
+# E3-S04d patch: import OpenAIGenericClient for the openai-provider case.
+# OpenAIClient uses responses.parse() which LiteLLM 1.83.13 does not bridge for
+# openai-prefixed model_list aliases against a custom api_base (see e3-s04c-evidence.md).
+# OpenAIGenericClient uses chat.completions.create with response_format=json_schema,
+# which is fully bridged. Reverts when upstream PR #1437 lands.
+from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient
@@ -134,6 +140,7 @@
-                # Only pass reasoning/verbosity parameters for reasoning models (gpt-5 family)
-                if is_reasoning_model:
-                    return OpenAIClient(config=llm_config, reasoning='minimal', verbosity='low')
-                else:
-                    # For non-reasoning models, explicitly pass None to disable these parameters
-                    return OpenAIClient(config=llm_config, reasoning=None, verbosity=None)
+                # E3-S04d: route through OpenAIGenericClient (chat.completions +
+                # response_format=json_schema) instead of OpenAIClient (responses.parse,
+                # not bridged in LiteLLM 1.83.13 against custom api_base).
+                # OpenAIGenericClient does not accept reasoning/verbosity kwargs;
+                # the is_reasoning_model branch above is preserved but inert here.
+                _ = is_reasoning_model  # kept for upstream-merge clarity
+                return OpenAIGenericClient(config=llm_config)
```

Net change: +13 added lines / -7 removed lines, no semantic effect on the other 4 provider arms (`azure_openai`, `anthropic`, `gemini`, `groq`) — those still construct `OpenAIClient` / vendor-native clients exactly as upstream. **Config stays `provider: openai`** in `config-graphiti-mcp.yaml`; only the client class behind the `openai` arm changes.

`OpenAIGenericClient.__init__` signature (`graphiti_core/llm_client/openai_generic_client.py:61`) is `(config, cache=False, client=None, max_tokens=16384)`. We pass `config=llm_config` only and let `max_tokens` default — graphiti-core's per-call `max_tokens` override (the YAML `llm.max_tokens: 1500`) flows through the `_generate_response` path regardless. The `reasoning=` / `verbosity=` kwargs that the original passes are not accepted by `OpenAIGenericClient` and are inert for non-reasoning models anyway, so dropping them is safe.

`base_url` is not explicitly set in the factory's `CoreLLMConfig` (upstream bug — same one the existing `OPENAI_BASE_URL` env workaround in `docker-compose.yml` lines 167-168 papers over). `OpenAIGenericClient` calls `AsyncOpenAI(api_key=config.api_key, base_url=config.base_url)` at line 91 — with `config.base_url=None` the SDK falls back to the `OPENAI_BASE_URL` env var, which is set to `http://192.168.50.160:4000/v1`. So routing to the LiteLLM gateway works identically before and after the patch.

---

## 3. Compose volume mount

Single addition to the `graphiti-mcp` service's `volumes:` block in `homelab-apps/stacks/graphiti/docker-compose.yml`:

```diff
     volumes:
       # Override the in-image /app/mcp/config/config.yaml with our split
       # llm/embedder provider config (ADR-017 v3). Read-only mount.
       - ./config-graphiti-mcp.yaml:/app/mcp/config/config.yaml:ro
+      # E3-S04d (2026-04-26): bind-mount factories.py override so the openai
+      # LLM provider case dispatches to OpenAIGenericClient (chat.completions
+      # + response_format=json_schema) instead of OpenAIClient (responses.parse).
+      # LiteLLM 1.83.13 does not bridge /v1/responses for openai-prefixed
+      # model_list aliases against a custom api_base — option A failure mode
+      # documented in homelab-playbook/docs/context-stack/sprint-3/e3-s04c-evidence.md.
+      # Revert this mount when upstream PR #1437 lands or LiteLLM ships the
+      # bridge in a way that works against custom api_base. See e3-s04d-evidence.md.
+      - ./factories.py.patched:/app/mcp/src/services/factories.py:ro
```

---

## 4. Container restart + verification — PASS

```
$ docker compose up -d
 Container falkordb Running
 Container graphiti-mcp Recreate
 Container graphiti-mcp Recreated
 Container graphiti-mcp Started

$ docker ps --filter name=graphiti-mcp --format 'table {{.Names}}\t{{.Status}}'
NAMES          STATUS
graphiti-mcp   Up 15 seconds (healthy)

$ docker logs graphiti-mcp --since 60s 2>&1 | tail -8
2026-04-26 20:28:57 - graphiti_mcp_server - INFO - Successfully initialized Graphiti client
2026-04-26 20:28:57 - graphiti_mcp_server - INFO - Using LLM provider: openai / gemma4-26b-json
2026-04-26 20:28:57 - graphiti_mcp_server - INFO - Using Embedder provider: openai
2026-04-26 20:28:57 - graphiti_mcp_server - INFO - Using database: falkordb
2026-04-26 20:28:57 - graphiti_mcp_server - INFO - Using group_id: main
2026-04-26 20:28:57 - graphiti_mcp_server - INFO - Starting MCP server with transport: http

$ curl -sS -o /dev/null -w 'health=%{http_code}\n' http://127.0.0.1:8000/health
health=200
```

No `ImportError`, no `AttributeError`, no Python traceback. Init clean.

### Patch-in-effect check

```
$ docker exec graphiti-mcp grep -n "OpenAIGenericClient" /app/mcp/src/services/factories.py | head -5
20:# E3-S04d patch: import OpenAIGenericClient for the openai-provider case.
23:# OpenAIGenericClient uses chat.completions.create with response_format=json_schema,
25:from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient
140:                # E3-S04d: route through OpenAIGenericClient (chat.completions +
143:                # OpenAIGenericClient does not accept reasoning/verbosity kwargs;
```

Override visible inside the container at the expected path. ✅

---

## 5. E3-S05 smoke test — FAIL at step 5d (extraction)

| Step | Acceptance | Observed | Verdict |
|------|------------|----------|---------|
| 5a — `initialize` | HTTP 200 + session id header | HTTP 200, `mcp-session-id: 939a4248096d…` | **PASS** |
| 5b — `notifications/initialized` | HTTP 200/202, no error | HTTP 202 | **PASS** |
| 5c — `add_memory` (queue submit) | HTTP 200, body says queued | HTTP 200 (5.6 ms), body: `Episode 'E3-S05 smoke test' queued for processing in group 'e3-s05-smoke'` | **PASS** |
| 5d — extraction completion within 12 × 10 s polls | log shows `Episode added` / `Entities extracted` | extraction worker hit `404 Not Found` from gateway in 0.5 s; failed both retries; queue marked the episode as failed | **FAIL** |
| 5e — `search_nodes` returns ≥1 node | empty response (graph never written) | HTTP 200 (366 ms): `{"message":"No relevant nodes found","nodes":[]}` | **FAIL (caused by 5d)** |
| 5f — `get_episodes` returns ≥1 episode | empty response | HTTP 200 (5.5 ms): `{"message":"No episodes found","episodes":[]}` | **FAIL (caused by 5d)** |

### 5c — add_memory verbatim response

```
HTTP 200 time=0.005597s
event: message
data: {"jsonrpc":"2.0","id":2,"result":{"content":[{"type":"text","text":"{\n  \"message\": \"Episode 'E3-S05 smoke test' queued for processing in group 'e3-s05-smoke'\"\n}"}],"structuredContent":{"result":{"message":"Episode 'E3-S05 smoke test' queued for processing in group 'e3-s05-smoke'"}},"isError":false}}
```

### 5d — extraction failure log dump (from `docker logs graphiti-mcp --since 5m`)

```
2026-04-26 20:29:36 - services.queue_service - INFO - Starting episode queue worker for group_id: e3-s05-smoke
2026-04-26 20:29:36 - services.queue_service - INFO - Processing episode None for group e3-s05-smoke
2026-04-26 20:29:36 - httpx - INFO - HTTP Request: POST http://192.168.50.160:4000/v1/chat/completions "HTTP/1.1 404 Not Found"
2026-04-26 20:29:36 - graphiti_core.llm_client.openai_generic_client - ERROR - Error in generating LLM response: Error code: 404 - {'error': {'message': "litellm.NotFoundError: NotFoundError: OpenAIException - Model 'chat_completions/gemma4-26b-text' is not recognised. Valid aliases: gemma4-auto, gemma4-26b-text, gemma4-e4b-vision.. Received Model Group=gemma4-26b-json\nAvailable Model Group Fallbacks=None", 'type': None, 'param': None, 'code': '404'}}
2026-04-26 20:29:36 - graphiti_core.llm_client.openai_generic_client - WARNING - Retrying after application error (attempt 1/2): …
2026-04-26 20:29:38 - services.queue_service - ERROR - Failed to process episode None for group e3-s05-smoke: Rate limit exceeded.
```

Wall-clock from `add_memory` queue submit (20:29:30) to first extraction failure (20:29:36): ~6 s. Wall-clock to terminal queue failure (20:29:38): ~8 s. (No useful "wall-clock to first search hit" — extraction never reached graph-write.)

### Entity / summary extraction quality

**N/A** — extraction never ran. The 404 came back from the gateway before the LLM was prompted, so no Gemma-extracted entities or summaries exist to validate.

---

## 6. Root-cause of the smoke failure — gateway-side, not factories patch

**The factories patch did exactly what it was supposed to.** Three pieces of evidence:

1. The httpx log line — `POST http://192.168.50.160:4000/v1/chat/completions` — confirms graphiti is now hitting `/v1/chat/completions`, not `/v1/responses`. Before the patch, the same code path hit `/v1/responses` (per `e3-s04c-evidence.md` §3 logs from the gateway side: `POST /v1/responses HTTP/1.1 404`). After the patch: `POST /v1/chat/completions`. ✅
2. The error originates from `graphiti_core.llm_client.openai_generic_client` (the new client class), not `graphiti_core.llm_client.openai_client` (the old one). ✅
3. Container init logged `Using LLM provider: openai / gemma4-26b-json` cleanly, no signature mismatch on the swapped client class. ✅

**The actual failure mode** is a LiteLLM gateway routing bug on the `gemma4-26b-json` model alias. Reproduced directly against the gateway (graphiti-mcp out of the loop):

```
$ curl -sS -X POST http://192.168.50.160:4000/v1/chat/completions \
    -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
    -H "Content-Type: application/json" \
    -d '{"model":"gemma4-26b-text","messages":[{"role":"user","content":"hi"}],"max_tokens":10}'
{"id":"chatcmpl-…","model":"gemma4-26b-text",…}   ← 200 OK

$ curl -sS -X POST http://192.168.50.160:4000/v1/chat/completions \
    -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
    -H "Content-Type: application/json" \
    -d '{"model":"gemma4-26b-json","messages":[{"role":"user","content":"hi"}],"max_tokens":10}'
{"error":{"message":"litellm.NotFoundError: NotFoundError: OpenAIException - Model 'chat_completions/gemma4-26b-text' is not recognised. Valid aliases: gemma4-auto, gemma4-26b-text, gemma4-e4b-vision.. Received Model Group=gemma4-26b-json …","code":"404"}}
```

`gemma4-26b-text` works; `gemma4-26b-json` does not. The error message `Model 'chat_completions/gemma4-26b-text' is not recognised` reveals that the `gemma4-26b-json` alias's `litellm_params.model` value still carries the **`openai/chat_completions/gemma4-26b-text`** prefix from the E3-S04c option-A experiment. The `chat_completions/` segment was meant to activate LiteLLM's response-API bridge (which we now know was non-functional in 1.83.13 — `e3-s04c-evidence.md`), but it was apparently not reverted to plain `openai/gemma4-26b-text` after that story closed. LiteLLM is now passing `chat_completions/gemma4-26b-text` through to the upstream llama.cpp server, which rejects it because the upstream doesn't know about the `chat_completions/` prefix and only has alias `gemma4-26b-text`.

This is a config-drift issue in `homelab-infra/ansible/roles/litellm-gateway/templates/litellm-config.yaml.j2` on the `gemma4-26b-json` alias. It is **not** the factories.py patch's responsibility, but it does block the E3-S05 smoke from passing here.

---

## 7. E3-S05 acceptance status

| Acceptance criterion | Status |
|----------------------|--------|
| graphiti-mcp container survives restart with patched factories.py | **PASS** |
| Container logs `Successfully initialized Graphiti client` with the new client class behind it | **PASS** |
| MCP `initialize` + `notifications/initialized` round-trip | **PASS** |
| `add_memory` accepts the episode and returns "queued" within <1 s | **PASS** |
| Extraction worker reaches the LLM via `/v1/chat/completions` (not `/v1/responses`) | **PASS** — see §6 |
| Extraction worker completes (entities + edges written to FalkorDB) | **FAIL** — gateway 404 on `gemma4-26b-json` alias (config drift) |
| `search_nodes` returns ≥1 node from `e3-s05-smoke` group | **FAIL** (caused by extraction failure) |
| `get_episodes` returns ≥1 episode from `e3-s05-smoke` group | **FAIL** (caused by extraction failure) |

**Net**: option D is the right fix at the graphiti-mcp layer. The remaining work is a one-line revert on the LiteLLM gateway template (`gemma4-26b-json` alias's `litellm_params.model` from `openai/chat_completions/gemma4-26b-text` back to `openai/gemma4-26b-text`), then re-run the E3-S05 smoke. Per spike hard-rule "no retries on smoke-test failure", we did not attempt that fix here — it should land as **E3-S04e**.

---

## 8. Anything unexpected

- **The factories.py patch caught a config-drift bug** that would have hit us regardless of which fix-attempt we were on. Even if option A had worked at the LiteLLM bridge layer, the `gemma4-26b-json` alias on the gateway would still have been broken (the `chat_completions/` prefix in the upstream `model:` value sends the upstream a name it doesn't recognize). So we'd have hit a 404 from llama.cpp instead of from LiteLLM, but it would still have been a 404. This drift originated in `e3-s04c` and persisted even though `e3-s04c-evidence.md` doesn't note an explicit revert. Future stories should add a "revert if smoke fails" step to gateway-template changes.
- The `OpenAIGenericClient` retry loop emits two retries before giving up (visible in the log: `attempt 1/2`). That's fine for genuine transient failures, but for a deterministic 404 it just doubles the gateway pressure. Not worth fixing — graphiti-core upstream behavior.
- The `graphiti_mcp_server` queue worker's terminal log line says `Rate limit exceeded` — that is the message string `OpenAIGenericClient` emits after exhausting retries on any error type, **not** an actual rate-limit response. The underlying error in this case is the 404. Misleading but cosmetic.

---

## 9. Status

**READY for E3-S04e** — gateway-config fix on the `gemma4-26b-json` LiteLLM alias (single-line: revert `litellm_params.model` to `openai/gemma4-26b-text`), then re-run the E3-S05 MCP smoke test (steps 5a–5f). On smoke pass, proceed to E3-S06 (full functional smoke-test suite — extraction quality, similarity, bi-temporal, multi-hop, failure-injection).

NOT ready for E3-S06 yet (E3-S05 itself has not yet passed end-to-end).

---

## 10. Reproduction

```bash
# Inspect patch in container
docker exec graphiti-mcp grep -n "OpenAIGenericClient" /app/mcp/src/services/factories.py

# Reproduce gateway-side failure (no graphiti involvement)
curl -sS -X POST http://192.168.50.160:4000/v1/chat/completions \
  -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"gemma4-26b-json","messages":[{"role":"user","content":"hi"}],"max_tokens":10}'
# expect: 404 with "Model 'chat_completions/gemma4-26b-text' is not recognised"

# Confirm sibling alias works (proves the upstream + LiteLLM are both fine in general)
curl -sS -X POST http://192.168.50.160:4000/v1/chat/completions \
  -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"gemma4-26b-text","messages":[{"role":"user","content":"hi"}],"max_tokens":10}'
# expect: 200
```
