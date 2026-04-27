# E3-S04c — Bridge fix attempt (option A): evidence

**Date**: 2026-04-26
**Story**: E3-S04c (LiteLLM `/v1/responses` → `/v1/chat/completions` bridge for Graphiti LLM extraction)
**Branch**: `feature/context-stack-e3-graphiti`
**Status**: **FAIL at Step 3 (gateway-layer bridge probe)** — option A (`openai/chat_completions/<model>` prefix) does NOT activate the bridge in LiteLLM 1.83.13. Step 4 (E3-S05 MCP smoke test) NOT attempted, per spike's hard-rule "no retries on smoke-test failure".

---

## 1. Change applied

Single-line change to `homelab-infra/ansible/roles/litellm-gateway/templates/litellm-config.yaml.j2`, scoped to the `gemma4-26b-json` alias only (`gemma4-auto`, `gemma4-26b-text`, `gemma4-e4b-vision`, and `gemini-embedding-2` left untouched):

```diff
   - model_name: gemma4-26b-json
     litellm_params:
-      model: openai/gemma4-26b-text
+      # ADR-017 v3 + E3-S04c: bridge /v1/responses → /v1/chat/completions
+      # so graphiti-core 0.28.2's responses.parse() reaches our chat-completions-only
+      # llama.cpp backend. LiteLLM 1.83.13 ships this bridge natively (docs/response_api).
+      model: openai/chat_completions/gemma4-26b-text
       api_base: {{ litellm_upstream_url }}
       api_key: {{ litellm_upstream_api_key }}
       extra_body:
```

---

## 2. Ansible deploy — PASS

Run: `ansible-playbook playbooks/deploy-ollama-models.yml --tags litellm-gateway --limit ct-ai-01 --vault-password-file /dev/shm/vp` (locale `C.UTF-8`).

PLAY RECAP:

```
ct-ai-01                   : ok=16   changed=2    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
```

- Render LiteLLM config: **changed**
- Restart litellm-gateway handler: **changed**
- `/health/liveliness` probe: **ok** (passed after 2 retries while service warmed)

External liveness re-probe post-deploy: `HTTP 200` against `http://192.168.50.160:4000/health/liveliness`.

---

## 3. Bridge sanity probe — **FAIL**

Payload sent to `POST http://192.168.50.160:4000/v1/responses` with master-key auth:

```json
{"model": "gemma4-26b-json", "input": "Reply with a JSON object containing a single key 'ok' set to true.", "max_output_tokens": 200}
```

Response:

```
HTTP 404 time=0.036513s
{"error":{"message":"litellm.NotFoundError: NotFoundError: OpenAIException - {\"detail\":\"Not Found\"}. Received Model Group=gemma4-26b-json\nAvailable Model Group Fallbacks=None","type":null,"param":null,"code":"404"}}
```

**Wall-clock 36 ms** — gateway routed and got a synchronous 404 from upstream (no LLM call took place).

### Why the bridge didn't fire (LiteLLM logs from `journalctl -u litellm-gateway`)

```
litellm.llms.custom_httpx.http_handler.MaskedHTTPStatusError:
  Client error '404 Not Found' for url 'http://127.0.0.1:8000/v1/responses'
INFO:     192.168.50.156:51182 - "POST /v1/responses HTTP/1.1" 404 Not Found
```

LiteLLM 1.83.13's `aresponses` → `async_response_api_handler` (`litellm/llms/custom_httpx/llm_http_handler.py:2432`) **POSTed `/v1/responses` directly to the upstream `api_base` (`http://127.0.0.1:8000`)** instead of bridging to `/v1/chat/completions`. The upstream `gemma-hybrid-proxy` only exposes `/v1/chat/completions`, so it returned 404. The `openai/chat_completions/` model-name prefix that the LiteLLM docs describe (`docs/response_api`) did **not** activate the chat-completions translation path on this code path / version.

Net: option A as a single-line model-prefix change is non-functional in LiteLLM 1.83.13 against an OpenAI-compatible custom upstream. The investigation's "Deal-breaker watch" callout (e3-s04c-investigation.md §Verdict, last paragraph) is the operative outcome — but the failure mode is one level earlier than predicted: the bridge prefix doesn't translate the route at all (404), rather than translating the route but failing on Responses-API-only fields (400). Either way, option A is dead for this version.

Per spike hard-rule "no retries on smoke-test failure", I stopped here. **Did NOT** proceed to Step 4 (E3-S05 MCP smoke test). graphiti-mcp container untouched.

---

## 4. E3-S05 acceptance — NOT EXECUTED

| Substep | Status |
|---|---|
| 4a — `initialize` MCP session | NOT ATTEMPTED (Step 3 failed) |
| 4b — `notifications/initialized` | NOT ATTEMPTED |
| 4c — `add_memory` | NOT ATTEMPTED |
| 4d — queue-worker monitor | NOT ATTEMPTED |
| 4e — `search_nodes` | NOT ATTEMPTED |
| 4f — `get_episodes` | NOT ATTEMPTED |

E3-S05 remains **BLOCKED** on resolution of the LLM-extraction path.

---

## 5. Surprises / deviations

- **Locale tweak required for Ansible**: had to set `LC_ALL=C.UTF-8 LANG=C.UTF-8` to avoid `unsupported locale setting` on the controller. Not new — pre-existing controller-environment thing — but worth noting for future runs.
- **SSH hostname alias**: `ssh ct-ai-01` did not resolve via DNS / system `~/.ssh/config`; had to use `root@192.168.50.160` directly to pull the master key. Inventory uses `ansible_host=192.168.50.160`, which is fine for Ansible. If we want a working short-name alias for one-off ssh, that's a separate `~/.ssh/config` change.
- **Failure mode is "earlier than expected"**: the investigation flagged the deal-breaker as "the bridge translates the route but Responses-API-only fields trip a 400". Reality: the prefix didn't translate at all (404 with the upstream URL still containing `/v1/responses`). This may mean the prefix syntax `openai/chat_completions/<model>` either (a) isn't recognized in 1.83.13, (b) requires a different config knob (e.g. `use_chat_completions_api: true` as a litellm_param — option B in the investigation), or (c) is recognized only when `api_base` doesn't already end in a path. None of these were probed because hard-rule #2 stopped further iteration.

---

## 6. Recommended next move

Open a **new** spike or follow-up story to evaluate (in order of likely lowest pain):

1. **Option B — `use_chat_completions_api: true` litellm_param** on the `gemma4-26b-json` alias. Same blast radius as option A (one alias only). 5–10 min trial deploy.
2. **Option D — bind-mount patched `factories.py`** in graphiti-mcp to flip its LLM client to `OpenAIGenericClient` (which uses `chat.completions.parse` natively). ~30 min, owns a small in-tree patch until upstream PR #1437 lands.
3. If both A and B are non-functional in 1.83.13, escalate option D to the default fallback for E3-S04c.

Do **NOT** retry within this spike — three repos are clean (one-line template change + this evidence doc + investigation), the LiteLLM container is healthy, and graphiti-mcp is untouched. Picking up from option B requires zero rollback.

---

## 7. Commits

- homelab-infra: `<sha-1>` — `e3-s04c: enable LiteLLM /v1/responses → /v1/chat/completions bridge on gemma4-26b-json — unblocks graphiti-core 0.28.2 LLM extraction`
- homelab-playbook: `<sha-2>` — `e3-s04c: investigation + bridge fix attempt evidence — option A non-functional on LiteLLM 1.83.13`

(SHAs filled in on commit; placeholder until then.)

---

## 8. Status

**NOT READY for E3-S06.** E3-S05 still blocked. Recommendation: schedule an E3-S04d (option B trial) or escalate directly to option D. graphiti-mcp container and Graphiti config files untouched — no rollback needed regardless of which path is chosen next.
