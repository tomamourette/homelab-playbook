# E3-S04e — option-A residue revert + E3-S05 smoke retry: evidence

**Date**: 2026-04-26
**Story**: E3-S04e (one-line revert of the failed option-A bridge prefix on the `gemma4-26b-json` LiteLLM alias) + E3-S05 MCP smoke-test retry
**Branch**: `feature/context-stack-e3-graphiti`
**Status**: **REVERT PASS, SMOKE FAIL on a new failure mode (schema-shape mismatch, not gateway).** The gateway revert is correct and verified working at the HTTP layer (200 OK with valid JSON body in 0.95s). The MCP smoke test now fails downstream of the gateway, inside graphiti-core's `OpenAIGenericClient` extraction path, on a Pydantic `ExtractedEntities` validation error: Gemma is returning `{"entities": [...]}` but the schema demands `{"extracted_entities": [...]}`. **No retries per the spike hard-rule.** The revert itself is a clean win and should ship; smoke-test failure is independent and needs a new story (E3-S04f or similar).

---

## 1. The revert

Pure single-line code change inside the `gemma4-26b-json` alias block of `homelab-infra/ansible/roles/litellm-gateway/templates/litellm-config.yaml.j2`. Comment block updated to explain WHY the prefix is gone, so the next person doesn't re-add it.

```diff
   - model_name: gemma4-26b-json
     litellm_params:
-      # ADR-017 v3 + E3-S04c: bridge /v1/responses → /v1/chat/completions
-      # so graphiti-core 0.28.2's responses.parse() reaches our chat-completions-only
-      # llama.cpp backend. LiteLLM 1.83.13 ships this bridge natively (docs/response_api).
-      model: openai/chat_completions/gemma4-26b-text
+      # E3-S04a/d: graphiti-core uses chat.completions.parse() via the OpenAIGenericClient
+      # patch (homelab-apps/stacks/graphiti/factories.py.patched), so no /v1/responses
+      # bridge is needed here. The earlier option-A bridge prefix (E3-S04c) was reverted
+      # in E3-S04d/e — the bridge prefix wasn't engaging on LiteLLM 1.83.13 and broke the
+      # alias against the upstream llama.cpp anyway.
+      model: openai/gemma4-26b-text
       api_base: {{ litellm_upstream_url }}
       api_key: {{ litellm_upstream_api_key }}
       extra_body:
```

Other aliases (`gemma4-auto`, `gemma4-26b-text`, `gemma4-e4b-vision`, `gemini-embedding-2`) untouched. `extra_body.response_format.type=json_object` and `chat_template_kwargs.enable_thinking=false` preserved on `gemma4-26b-json`.

---

## 2. Ansible deploy

```bash
cd homelab-infra/ansible
LC_ALL=C.UTF-8 LANG=C.UTF-8 ansible-playbook \
  playbooks/deploy-ollama-models.yml \
  --tags litellm-gateway \
  --limit ct-ai-01 \
  --vault-password-file /dev/shm/vp
```

Recap (extract):

```
TASK [litellm-gateway : Render LiteLLM config (model_list + general_settings)] *** changed: [ct-ai-01]
RUNNING HANDLER [litellm-gateway : Restart litellm-gateway] *** changed: [ct-ai-01]
TASK [litellm-gateway : Wait for LiteLLM /health/liveliness to return 200] *** ok: [ct-ai-01]

PLAY RECAP **********************************************************
ct-ai-01 : ok=16 changed=2 unreachable=0 failed=0 skipped=0 rescued=0 ignored=0
```

`failed=0`, render config `changed`, restart handler ran, post-restart liveliness probe returned 200 after one retry (~5s warm-up). Note: `ansible-playbook` must be invoked with `cwd=homelab-infra/ansible` so `ansible.cfg`'s `roles_path = roles` resolves; running from repo root with an explicit `-i` fails with "role 'ollama-models' not found".

Independent post-deploy probe:

```bash
curl -sS -o /dev/null -w 'HTTP %{http_code}\n' http://192.168.50.160:4000/health/liveliness
# HTTP 200
```

---

## 3. Direct gateway probe — `gemma4-26b-json` alias

Goal: prove the alias now correctly forwards `/v1/chat/completions` to the upstream gemma-hybrid-proxy → llama.cpp without the broken `chat_completions/` prefix.

```bash
LITELLM_KEY=$(ssh root@192.168.50.160 "grep '^LITELLM_MASTER_KEY=' /opt/litellm-gateway/.env | cut -d= -f2-")
curl -sS -m 60 -H "Authorization: Bearer $LITELLM_KEY" \
  -H "Content-Type: application/json" \
  --data-binary @/tmp/e3-s04e-probe.json \
  http://192.168.50.160:4000/v1/chat/completions
```

Payload:

```json
{
  "model": "gemma4-26b-json",
  "messages": [
    {"role":"system","content":"Return JSON only."},
    {"role":"user","content":"Reply with {\"ok\": true}."}
  ],
  "max_tokens": 100,
  "temperature": 0
}
```

Response (verbatim):

```
HTTP 200 time=0.954627s

{"id":"chatcmpl-2ziluWZqdCX41nuyXxHnAxtuMlm4UEe6","created":1777235806,
 "model":"gemma4-26b-json","object":"chat.completion",
 "system_fingerprint":"b1-4fbdabd",
 "choices":[{"finish_reason":"stop","index":0,
   "message":{"content":"{\"ok\": true}\n","role":"assistant",
              "provider_specific_fields":{"refusal":null}},
   "provider_specific_fields":{}}],
 "usage":{"completion_tokens":15,"prompt_tokens":25,"total_tokens":40,
          "prompt_tokens_details":{"cached_tokens":0}},
 "timings":{...,"prompt_per_second":81.83,"predicted_per_second":26.98}}
```

- HTTP 200, wall-clock 0.95 s
- `choices[0].message.content == "{\"ok\": true}\n"` — valid JSON, content matches the prompt
- `finish_reason: stop`
- 25 prompt tokens, 15 completion tokens (the JSON-mode + `enable_thinking=false` constraints are still honoured — no `<think>` blocks, model emitted JSON only)
- llama.cpp build `b1-4fbdabd` — the same upstream that was returning 404 with the broken prefix in E3-S04d

**Verdict: revert successful at the gateway layer.** This is the precondition that E3-S04d called out as missing. Nothing else on the gateway side blocks E3-S05 now.

---

## 4. E3-S05 MCP smoke retry

Group: `e3-s05-smoke-retry` (separate namespace from any partial state in the previous attempt).

| Step | Action | Result | Status |
|------|--------|--------|--------|
| 4a | `initialize` (JSON-RPC) | HTTP 200, session `a4c397a4ebce…`, server `Graphiti Agent Memory v1.26.0` | PASS |
| 4b | `notifications/initialized` | HTTP 202 Accepted | PASS |
| 4c | `tools/call add_memory` (group=`e3-s05-smoke-retry`) | HTTP 200 in 7 ms — `Episode 'E3-S05 smoke test (retry)' queued for processing` | PASS (submit) |
| 4d | Queue worker → extraction complete | **FAIL at t≈15 s** — Pydantic `ExtractedEntities` validation error, missing required field `extracted_entities`. Worker raised, episode dropped. Subsequent monitor passes (t=20–180 s) showed no recovery. | **FAIL** |
| 4e | `search_nodes` | **NOT EXECUTED** — extraction never produced graph nodes; `search_nodes` would return empty by definition. Per hard-rule "no retries on smoke-test failure", stopped here. | SKIP |
| 4f | `get_episodes` | **NOT EXECUTED** — same reason. | SKIP |

### 4d failure-mode capture (full)

graphiti-mcp container logs, `--since 5m`, filtered for the failing window:

```
2026-04-26 20:37:13 - mcp.server.lowlevel.server - INFO - Processing request of type CallToolRequest
2026-04-26 20:37:13 - services.queue_service - INFO - Starting episode queue worker for group_id: e3-s05-smoke-retry
2026-04-26 20:37:13 - services.queue_service - INFO - Processing episode None for group e3-s05-smoke-retry
2026-04-26 20:37:28 - httpx - INFO - HTTP Request: POST http://192.168.50.160:4000/v1/chat/completions "HTTP/1.1 200 OK"
2026-04-26 20:37:28 - services.queue_service - ERROR - Failed to process episode None for group e3-s05-smoke-retry:
  1 validation error for ExtractedEntities
  extracted_entities
    Field required [type=missing,
      input_value={'entities': [{'name': 'C..., 'entity_type_id': 4}]},
      input_type=dict]
    For further information visit https://errors.pydantic.dev/2.12/v/missing
```

**Critical observations:**

1. The HTTP call to the gateway returned **200 OK** at 20:37:28 (15 s after worker start). The gateway and the upstream Gemma model are both healthy and responding within budget.
2. Graphiti-core received a well-formed `chat.completions` response from Gemma containing valid JSON.
3. The JSON Gemma produced has top-level key **`entities`**, but graphiti-core's `ExtractedEntities` Pydantic schema (graphiti-core 0.28.2, `prompts/extract_nodes.py`) demands the top-level key be **`extracted_entities`**. Pydantic rejects the response, the worker raises, the episode is dropped before any graph write.
4. The model's content is otherwise sane — Gemma did extract entity-shaped objects with `name` and `entity_type_id` fields. Only the wrapping key is wrong.

### Independent of the gateway revert

This failure mode did NOT exist in E3-S04d's evidence — the previous failure was an upstream HTTP 404 from llama.cpp because of the bad model prefix at the gateway, which short-circuited well before any extraction. With the prefix correctly reverted, extraction now reaches the schema-validation step and exposes a separate problem: the `OpenAIGenericClient` path in graphiti-core doesn't pin the JSON-schema response shape tightly enough for Gemma to honour the exact field name. `OpenAIGenericClient` (E3-S04d's chosen client class) uses `response_format={'type':'json_schema',...}`; if the upstream provider doesn't enforce the JSON-Schema constraint server-side (as our llama.cpp build with `response_format: json_object` doesn't), the model is free to alias the field name.

The gateway-side `extra_body.response_format: {type: json_object}` is the loose JSON-mode (any valid JSON), not the strict JSON-schema mode. The strict mode would have to be passed via `response_format: {type: json_schema, json_schema: {...}}` — but that requires either (a) llama.cpp builds with `--grammar` derived from the schema, or (b) graphiti-core sending the full schema in the request, which it does, but the upstream doesn't enforce.

**This is a new story, not a regression.** Likely fixes (out of scope for E3-S04e):

- Patch `OpenAIGenericClient` to validate-and-rename `entities` → `extracted_entities` on receive (cheap, hacky)
- Add a llama.cpp grammar hook so `response_format: json_schema` becomes enforceable upstream (clean, more work)
- Tighten the system prompt graphiti-core uses to emphasize the exact field name (medium, brittle)
- Consider llama-cpp-server's native `response_format: {type: json_schema, schema: {...}}` support (build dependency)

The hard-rule `no retries on smoke-test failure` was followed: I stopped at 4d, did not modify graphiti-core or the LiteLLM config to chase this. Capture only.

---

## 5. Wall-clock summary

- `add_memory` HTTP submit: 7 ms
- Worker pulled from queue and called Gemma: t≈0–13 s
- Gemma returned 200 OK to graphiti-core: t=15 s
- Graphiti-core raised Pydantic ValidationError: t=15 s
- Subsequent 165 s of monitoring: no further activity (worker drained, episode lost)

The 15 s Gemma round-trip is in-budget for a 26B-A4B local model on CPU+iGPU (matches E3-S04d's `gemma-hybrid-proxy` benchmarks of 12–18 s for 100-token completions on this prompt size).

---

## 6. Entities + edges Gemma extracted

**Cannot fully report.** The Pydantic ValidationError fires before graphiti-core logs the full parsed response. The truncated `input_value` repr in the traceback shows:

```python
{'entities': [{'name': 'C..., 'entity_type_id': 4}]}
```

Only enough to confirm that Gemma produced at least one entity object with a name starting with `C` (likely "Context Stack", "Claude Code", or "Code-Quality" given the episode body) and an `entity_type_id` of 4. No edges were extracted because edge extraction is a downstream pass that depends on entity extraction succeeding. The episode body mentioned Gemini Embedding 2, Gemma 4 26B-MoE, FalkorDB, OpenAIGenericClient, and Sprint 3 — Gemma had clear named entities to draw from, so the extraction quality is plausibly fine; only the wrapping key is broken.

---

## 7. Anything unexpected

1. **The new failure mode is at a different layer than E3-S04d's failure.** Previous failure was upstream HTTP 404 (gateway-routing); this one is downstream Pydantic schema (graphiti-core ↔ Gemma contract). The revert moved the failure forward, which is the expected direction of progress.
2. **Ansible playbook path discovery.** The story brief suggested `ansible/site.yml`; the actual playbook is `ansible/playbooks/deploy-ollama-models.yml`, and `ansible-playbook` must be invoked with `cwd=homelab-infra/ansible` for `ansible.cfg`'s `roles_path = roles` to resolve. Documented above for the next agent.
3. **Gateway probe is fast and clean.** 0.95 s end-to-end with a 26B-MoE local model is a decent confirmation that the gateway, the proxy, and llama.cpp are all healthy — the smoke-test failure is genuinely a graphiti↔Gemma schema-name mismatch and not a transport-layer issue.
4. **`OpenAIGenericClient` does not appear to log the raw `chat.completions` response** before parsing, which makes diagnosing this kind of schema mismatch harder. Logging the JSON payload on validation error would be a nice graphiti-core upstream contribution.

---

## 8. Status

- **E3-S04e itself**: PASS — single-line revert is correct, deployed, and gateway-verified.
- **E3-S05 MCP smoke retry**: FAIL on a new failure mode (schema-name mismatch in graphiti↔Gemma), independent of E3-S04e's revert.
- **NOT READY for E3-S06.** A new story (suggest E3-S04f or E3-S05.1) is needed to fix the `entities` vs `extracted_entities` mismatch in the `OpenAIGenericClient` extraction path before the full functional smoke-test suite can run.

---

## 9. Hand-off notes

The next-story author should investigate, in this order:

1. Confirm whether graphiti-core 0.28.2's `OpenAIGenericClient` uses `chat.completions.create` with `response_format: {type: 'json_object'}` (loose) or `{type: 'json_schema', json_schema: {schema, strict: true}}` (strict). If loose, that's the root cause; the strict mode would force Gemma's output through the schema's exact field names.
2. Check llama.cpp's `b1-4fbdabd` build for `response_format: json_schema` support — if absent, we cannot fix this purely server-side and the patch must live in graphiti-core or in a wrapper.
3. Consider a minimal post-process fix: wrap `OpenAIGenericClient._generate_response` to detect `{'entities': [...]}` and rewrite to `{'extracted_entities': [...]}` before Pydantic. Hacky but unblocks E3-S05 in a single bind-mounted file change, mirroring the E3-S04d pattern.
4. Whatever the fix, do NOT touch the LiteLLM gateway config or `factories.py.patched` — those are correct and stay.

The `homelab-infra` revert is independently shippable and is committed in this story; the smoke-test failure is reported but no fix is attempted, per spike rules.
