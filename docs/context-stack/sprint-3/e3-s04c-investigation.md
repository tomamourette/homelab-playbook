# E3-S04c — Investigation: graphiti-core /v1/responses ↔ LiteLLM mismatch

**Date:** 2026-04-26
**Story:** E3-S04c (follow-up to E3-S04b)
**Recommended unblock:** **LiteLLM-gateway-side bridge** — change the `gemma4-26b-json` alias's model id from `openai/gemma4-26b-text` to `openai/chat_completions/gemma4-26b-text` in the litellm-gateway role template. Pre-existing LiteLLM feature; no version bump required; no graphiti container changes.
**Estimated effort:** **5–10 minutes** (1-line edit in `litellm-config.yaml.j2`, run the litellm-gateway Ansible play, smoke-test `add_memory` once).

---

## Q1 findings — `openai_generic_client`

### A1.1 Does `openai_generic_client.py` exist? Does it use `chat.completions.create()`?

**Yes to both, verified inside the live container** `graphiti-mcp` (image `zepai/knowledge-graph-mcp:standalone`, container id `460bafb39439`, status healthy):

- File present: `/app/mcp/.venv/lib/python3.11/site-packages/graphiti_core/llm_client/openai_generic_client.py`
- Class: `class OpenAIGenericClient(LLMClient):` (line 37)
- API call site: line 123 — `response = await self.client.chat.completions.create(...)` (NOT `responses.parse`)
- Default model: `gpt-4.1-mini` (overridable via `LLMConfig.model`)
- Default `max_tokens`: `16384` — comment in source: *"Defaults to 16384 (16K) for better compatibility with local models"*
- Response handling: requests `response_format = {"type":"json_object"}` (or json_schema if `response_model` provided) and parses `response.choices[0].message.content` with `json.loads()`. Exactly the path our LiteLLM `gemma4-26b-json` alias is built for.

Contrast with `openai_client.py` (the default the factory hands out):
- Class `OpenAIClient(BaseOpenAIClient)`
- `_create_structured_completion()` calls `self.client.responses.parse(**request_kwargs)` at line 99 — this is the **/v1/responses** call that's failing.
- `_create_completion()` does fall back to `chat.completions.create()` at line 119, but the *structured-output* path (which graphiti uses for entity/edge extraction) goes through the responses API.

### A1.2 Does graphiti-mcp's `services/factories.py` recognise `openai_generic`?

**No.** Path: `/app/mcp/src/services/factories.py`. The `LLMClientFactory.create()` `match provider:` block (line 100+) accepts exactly five strings:

```
'openai' | 'azure_openai' | 'anthropic' | 'gemini' | 'groq'
```

Default arm: `case _: raise ValueError(f'Unsupported LLM provider: {provider}')`.

`OpenAIGenericClient` is **not imported** in `factories.py` — it's not even an option behind a `try/except` like `AnthropicClient`, `GeminiClient`, `GroqClient` are. The graphiti-core library `__init__.py` (`/app/mcp/.venv/lib/python3.11/site-packages/graphiti_core/llm_client/__init__.py`) only re-exports `OpenAIClient`, not `OpenAIGenericClient`, so even an `import` shim would have to dig into the submodule directly.

### A1.3 Is the unblock a one-line config edit `provider: openai → openai_generic`?

**No** — that would raise `ValueError: Unsupported LLM provider: openai_generic` at startup. A code patch (bind-mounted `factories.py`) is required to get graphiti-mcp v1.0.2 to use the existing `OpenAIGenericClient` class.

There's also no env-var override for `provider` in the running image: `grep -rn "GRAPHITI_LLM_PROVIDER\|provider.*env" /app/mcp/src/` returns nothing. The schema does support `${VAR}` substitution inside YAML values (so `provider: ${LLM_PROVIDER:openai}` is *technically* possible), but the factory's allow-list still blocks `openai_generic` regardless.

**Translation:** The previous coder agent's claim is half-right — the class exists and uses `chat.completions.create()` — but **wrong on the unblock effort**. graphiti-mcp v1.0.2 cannot reach `OpenAIGenericClient` through configuration alone. A code patch (or a fork, or PR #1437 / PR #1227 / PR #1339 from upstream) is needed to make `provider: openai_generic` resolve.

---

## Q2 findings — LiteLLM Responses-API roadmap

### A2.1 Current latest LiteLLM version (2026-04-26)

Latest published nightly: **v1.83.13-nightly** (Apr 24, 2026). Latest *stable*: **v1.83.7-stable** (Apr 19, 2026). Our gateway on `192.168.50.160:4000` is already running `litellm_version: 1.83.13` — confirmed via `/health/readiness`, which also reports the `ResponsesIDSecurity` callback loaded (i.e., Responses-API plumbing is active in our running gateway).

Note: Python 3.10 is now the minimum (v1.83.10-nightly breaking change, Apr 19).

### A2.2 Has LiteLLM proxy added /v1/responses → /chat/completions bridging for `model_list` aliases?

**Yes — and the feature is already shipped in the version we're running.** Two independent mechanisms exist:

1. **`use_chat_completions_api: true`** flag inside `litellm_params` of a `model_list` entry. Makes it explicit that LiteLLM should call the provider's `/chat/completions` for `/v1/responses` requests.
2. **`openai/chat_completions/<model>` model-id prefix** — same effect, just encoded in the model id instead of a separate flag.

Verbatim from `https://docs.litellm.ai/docs/response_api`:

> *"Requests to /chat/completions may be bridged here automatically when the provider lacks support for that endpoint."*
> *"If the provider only supports /chat/completions, the request will fail. Use either of these to force the /responses → /chat/completions bridge: `use_chat_completions_api: true` — makes it explicit that LiteLLM will call the provider's chat-completions API."*

### A2.3 Issues / PRs / version history

- **Issue #15342** — *"`litellm_proxy` provider lacks native Responses API support, causing unnecessary transformations and errors"* — opened Oct 8 2025, **closed** by PR #15347.
- **PR #15347** — *"Add native Responses API support for litellm_proxy provider"* — **merged Oct 9 2025**. Adds `LiteLLMProxyResponsesAPIConfig` in `litellm/llms/litellm_proxy/responses/transformation.py`. Note this PR is for `litellm_proxy/...` model ids (gateway-to-gateway), **not** the `openai/...` prefix; the `openai/chat_completions/` bridge prefix was *already* in main when #15347 landed.
- **Issue #13130** — *"support enabling /responses to /chat/completions Bridge on openai (llama.cpp) models"* — **closed**. Exact match for our use case (llama.cpp backend, `/chat/completions`-only). Resolution was the bridge prefix that's now documented.
- **v1.83.8-nightly** (Apr 15 2026) — *"fix(responses-ws): append ?model= to backend WebSocket URL"* and *"fix(responses): map refusal stop_reason to incomplete status in streaming"* — proves Responses-API code path is being actively maintained.
- Other open items (not blockers for us): #26554 (Anthropic translation), #26250 (`aclose()` cleanup), #26241 (drop_params on Anthropic→Responses adapter), #26240 (Claude Code 2.1.104 validation), #26212 (mcp_semantic_tool_filter).

**Verdict on Q2:** the bridge has been production-shipped well before our gateway version. Nothing to wait for.

---

## Q3 findings — graphiti-mcp v1.0.2 patch surface

### A3.1 Is `provider` in `config-graphiti-mcp.yaml` env-var overridable?

The host file `/home/developer/workspace/homelab/homelab-apps/stacks/graphiti/config-graphiti-mcp.yaml` is mounted read-only into the container at `/app/mcp/config/config.yaml`. The schema supports `${VAR}` and `${VAR:default}` substitution inside scalar values (verified at `/app/mcp/src/config/schema.py:_expand_env_vars`). So `provider: ${LLM_PROVIDER:openai}` *would* be substituted at load time — but the resulting value still has to clear the factory's hard-coded match block, which only knows `openai|azure_openai|anthropic|gemini|groq`. Env-var-only is not a path forward.

### A3.2 Does graphiti-mcp v1.0.2 source recognize `openai_generic`?

**Not on `main`, but multiple in-flight upstream PRs add it:**

| PR | Author | Date | What it does |
|----|--------|------|--------------|
| #1227 | contextablemark | 2026-02-13 | Add local model support with `openai_generic` provider + reranker config |
| #1339 | Ker102 | 2026-03-21 | Use `OpenAIGenericClient` for non-OpenAI endpoints (Gemini, Ollama, vLLM) |
| #1341 | wignerStan | 2026-03-21 | Ollama and Kuzu/LadybugDB compatibility |
| #1362 | theskipper007 | 2026-03-31 | Validate LLM responses in `OpenAIGenericClient` to prevent Pydantic errors |
| **#1437** | srirsiva | **2026-04-25** | Forward OpenAI `api_url` + add chat-completions LLM path via a new `use_chat_completions: bool` flag; in `factories.py` returns `OpenAIGenericClient` when set. Open. Reviewer @xkonjin flagged 3 concerns + missing tests. |
| #1226 | contextablemark | 2026-02-13 | Feature Request: fully support local model deployments in MCP |
| #1116 | (older) | — | OpenAI provider ignores `api_base` config and falls back to api.openai.com |

None merged as of 2026-04-26. PR #1437 is the closest spiritual match to what we'd need to bind-mount: a `use_chat_completions` knob that makes the factory return `OpenAIGenericClient` instead of `OpenAIClient`. But it's open, has reviewer concerns, and no test coverage.

### A3.3 Smallest-change inventory

Ranked from smallest to largest:

| Option | Where | Effort | Risk |
|--------|-------|--------|------|
| **A. LiteLLM bridge prefix** (RECOMMENDED) | One line in `litellm-config.yaml.j2` — change `model: openai/gemma4-26b-text` to `model: openai/chat_completions/gemma4-26b-text` on the `gemma4-26b-json` alias only | **5–10 min** | Very low — pre-existing LiteLLM feature, doesn't touch graphiti-mcp at all, scoped to one alias so other consumers (Hermes, OWUI) are unaffected |
| B. `use_chat_completions_api: true` flag | Same file, add one line under `litellm_params` of `gemma4-26b-json` | 5–10 min | Same as A — equivalent semantically; pick one or the other |
| C. Env var alone | Set `LLM_PROVIDER=openai_generic` and update YAML to `provider: ${LLM_PROVIDER:openai}` | N/A | **Won't work** — factory's match block rejects the value |
| D. Bind-mount patched `factories.py` | Patch the match block to add `openai_generic` arm + import `OpenAIGenericClient` from `graphiti_core.llm_client.openai_generic_client`, mount via `docker compose volumes:` | ~30 min + test cycle | Medium — bind-mount must survive container upgrades; we own the patch until upstream merges PR #1437 or similar |
| E. Fork graphiti-mcp / pin to a custom build | Fork repo, apply PR #1437 or #1339, push image to a private registry, swap docker image tag | ~2–4 hours + ongoing maintenance | High — we now own a fork; security-update cadence becomes our problem |

---

## Verdict

**Do option A.** Edit `homelab-infra/ansible/roles/litellm-gateway/templates/litellm-config.yaml.j2`, change line 33 from:

```yaml
      model: openai/gemma4-26b-text
```

to:

```yaml
      model: openai/chat_completions/gemma4-26b-text
```

…on the `gemma4-26b-json` alias only (lines 31–40). Leave `gemma4-26b-text`, `gemma4-auto`, and `gemma4-e4b-vision` unchanged so existing consumers are untouched. Run the `litellm-gateway` Ansible play to roll the new config to `192.168.50.160:4000`, then re-trigger an `add_memory` call against graphiti-mcp; the queued worker should now succeed because `client.responses.parse()` will land on LiteLLM, get bridged internally to `/chat/completions`, and hit the same `gemma-hybrid-proxy` upstream that already returned clean JSON in the 32s wall-clock smoke test.

**Why not option D (factories.py patch)?** It's a graphiti-container patch we'd own indefinitely, would need re-application on every image upgrade, and gains nothing over option A — both ultimately route entity-extraction through `/chat/completions` to the same llama.cpp backend with the same JSON-mode response_format and the same `enable_thinking: false`. Option A is upstream-agnostic and uses a documented LiteLLM feature.

**Deal-breaker watch:** if graphiti-core's `responses.parse()` payload includes Responses-API-only fields (e.g. `instructions`, `previous_response_id`, `tools` with the new schema, `reasoning_effort`) that LiteLLM's bridge can't translate to `chat.completions` parameters, the bridge will return a 400. Mitigation: the `_create_structured_completion()` path in `openai_base_client.py` builds `request_kwargs` from a Pydantic schema name + json_schema body, which is structurally close to chat.completions' `response_format = {"type":"json_schema",...}` — LiteLLM's bridge is documented to handle this case. If a 400 surfaces in practice, fall back to option D (bind-mount patched `factories.py` flipping the factory to `OpenAIGenericClient`).

---

## Sources

- Live container inspection: `docker exec graphiti-mcp ...` against image `zepai/knowledge-graph-mcp:standalone` (container `460bafb39439`, healthy 8min uptime at investigation time)
- `/app/mcp/.venv/lib/python3.11/site-packages/graphiti_core/llm_client/openai_generic_client.py` (lines 37, 95, 123, 138)
- `/app/mcp/.venv/lib/python3.11/site-packages/graphiti_core/llm_client/openai_client.py` (lines 27, 65, 99, 103, 119) — confirms `responses.parse` at line 99
- `/app/mcp/.venv/lib/python3.11/site-packages/graphiti_core/llm_client/__init__.py` — confirms `OpenAIGenericClient` not exported
- `/app/mcp/src/services/factories.py` (the live image bundle, lines 100+) — confirms 5-provider match block, no `openai_generic`
- `/app/mcp/src/config/schema.py` lines 19–61 — confirms `${VAR:default}` substitution available in YAML values
- LiteLLM `/health/readiness` on `http://192.168.50.160:4000` — confirms `litellm_version: 1.83.13` and `ResponsesIDSecurity` callback loaded
- https://docs.litellm.ai/docs/response_api — `use_chat_completions_api` and `openai/chat_completions/` prefix documentation
- https://github.com/BerriAI/litellm/issues/15342 — `litellm_proxy` Responses API bug (closed)
- https://github.com/BerriAI/litellm/pull/15347 — merged Oct 9 2025, native litellm_proxy Responses-API support
- https://github.com/BerriAI/litellm/issues/13130 — bridge for llama.cpp models (closed, exact match for our case)
- https://github.com/BerriAI/litellm/releases — v1.83.13-nightly (Apr 24 2026), v1.83.7-stable (Apr 19 2026)
- https://github.com/getzep/graphiti/pull/1437 — open, adds `use_chat_completions` flag + `OpenAIGenericClient` factory branch
- https://github.com/getzep/graphiti/pull/1227 — open, adds `openai_generic` provider name
- https://github.com/getzep/graphiti/pull/1339 — open, uses `OpenAIGenericClient` for non-OpenAI endpoints
- https://github.com/getzep/graphiti/issues/1116 — older known bug: api_base ignored, fixed by placing under `providers.openai.api_url` (which our config already does)
- https://github.com/getzep/graphiti/issues/1226 — feature request: full local-model support
- Local artifact: `homelab-infra/ansible/roles/litellm-gateway/templates/litellm-config.yaml.j2` line 33 (the one-line target)
