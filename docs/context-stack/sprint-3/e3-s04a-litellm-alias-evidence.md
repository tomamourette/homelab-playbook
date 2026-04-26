# E3-S04 part (a) — LiteLLM `gemma4-26b-json` alias evidence

**Sprint 3 / Epic E3 / story 4 of 9 (part a — LLM gateway config)**
**Date**: 2026-04-26
**Branch**: `feature/context-stack-e3-graphiti` (homelab-infra + homelab-apps + homelab-playbook)
**Status**: part (a) DONE — gateway alias live, Graphiti MCP cut over and healthy. Part (b) BLOCKED on operator-supplied `OPENAI_API_KEY` for the embedder client (text-embedding-3-small per ADR-003).

## 1. Why a NEW alias (not edit the existing `gemma4-26b-text`)

ADR-017 v3 (clean ADOPT-LOCAL, commit `74ef3aa`) mandates that every Graphiti MCP request to the LLM include three params:

- `response_format: {"type": "json_object"}`
- `chat_template_kwargs: {"enable_thinking": false}`
- `max_tokens: 1500`

E3-S02 verified that the upstream Graphiti MCP server (zepai/knowledge-graph-mcp v1.0.2, graphiti-core 0.28.2) does NOT expose `response_format` or `chat_template_kwargs` as first-class client config knobs. They must therefore be forced at the gateway layer (LiteLLM `extra_body`).

But the existing `gemma4-26b-text` alias is also consumed by Hermes and (likely) OWUI, neither of which want JSON-mode forced. Modifying the existing alias would break those consumers.

**Resolution**: add a new alias `gemma4-26b-json` that points at the same upstream model (`openai/gemma4-26b-text` → gemma-hybrid-proxy) but with the two mandatory params merged into every outbound request via `litellm_params.extra_body`. Hermes/OWUI continue to use `gemma4-26b-text` unchanged.

## 2. New alias entry (verbatim from `homelab-infra/ansible/roles/litellm-gateway/templates/litellm-config.yaml.j2`)

```yaml
  # ADR-017 v3: Graphiti-specific alias that forces JSON-mode + disables
  # Gemma's thinking blocks at the gateway layer. Required because the
  # upstream Graphiti MCP server (v1.0.2) doesn't expose these as first-
  # class client config knobs. Other consumers (Hermes, OWUI) keep using
  # gemma4-26b-text unchanged. extra_body is merged into the upstream
  # request body by LiteLLM's OpenAI-compatible client (see litellm/main.py
  # kwargs.get("extra_body", {}) merge at request time).
  - model_name: gemma4-26b-json
    litellm_params:
      model: openai/gemma4-26b-text
      api_base: {{ litellm_upstream_url }}
      api_key: {{ litellm_upstream_api_key }}
      extra_body:
        chat_template_kwargs:
          enable_thinking: false
        response_format:
          type: json_object
```

## 3. LiteLLM version + `extra_body` syntax provenance

- LiteLLM version on ct-ai-01: `1.83.13` (from `/opt/litellm-gateway/.venv/bin/pip show litellm`)
- Documented syntax: `litellm_params.extra_body` (top-level key under `litellm_params` for each `model_list` entry). This is the standard LiteLLM proxy config pattern. Reference docs: <https://docs.litellm.ai/docs/completion/provider_specific_params> ("Use 'extra_body' parameter in litellm_params to pass extra parameters to the model provider").
- Code-side verification on this exact version: `litellm/main.py` line 4300 merges `kwargs.get("extra_body", {})` into the upstream request body for the OpenAI-compatible client. The OpenRouter precedent (lines 3305–3310) uses the same pattern with the comment "we use openai 'extra_body' to pass openrouter specific params".
- No alternate syntax (`model_info.extra_body`, etc.) was needed. The Pydantic config validation at gateway startup did not reject the entry — gateway came up clean and the new alias appeared in `/v1/models`.

## 4. Ansible deploy outcome

```
PLAY RECAP
ct-ai-01                   : ok=16   changed=2    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
```

- `Render LiteLLM config` task: changed (template re-rendered with new entry).
- `Restart litellm-gateway` handler: changed (systemd unit restarted; service active immediately, /health/liveliness 200 after ~7s of retries — expected uvicorn startup window).
- No template syntax errors, no Pydantic validation errors, no role failures.

## 5. End-to-end probe (1st episode of E3-S01.5 spike corpus)

Probe payload deliberately omitted both `response_format` and `chat_template_kwargs` from the client body — they MUST come from the gateway alias's `extra_body` to count as proof.

```bash
KEY=$(cat /home/developer/.litellm-key-e3-s04 | tr -d '\n')
curl -sS -m 180 -o /tmp/e3-s04-resp.json -w 'HTTP %{http_code} time=%{time_total}s' \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  --data-binary @/tmp/e3-s04-probe.json \
  http://192.168.50.160:4000/v1/chat/completions
```

Result:

| Check | Value | Verdict |
| --- | --- | --- |
| HTTP status | 200 | OK |
| Wall time | 33s (curl `time_total=32.27s`) | reasonable for 26B at 1500 max_tokens; gemma-hybrid-proxy cold-ish path |
| `finish_reason` | `stop` | clean termination, not `length`/`tool_calls` |
| `content` parses as JSON | YES — keys: `['entities', 'edges', 'valid_at', 'invalid_at']` | response_format=json_object was injected |
| `reasoning_content` field | absent (False) | enable_thinking=false was injected |
| Token usage | prompt=785, completion=667, total=1452 | within max_tokens=1500 budget |

All three acceptance conditions met (parseable JSON, no reasoning_content, finish_reason=stop). The gateway alias is correctly auto-injecting both ADR-017 v3 params on every request.

## 6. Graphiti compose env diff

`homelab-apps/stacks/graphiti/docker-compose.yml`:

```diff
       - LITELLM_BASE_URL=http://192.168.50.160:4000/v1
-      - MODEL_NAME=gemma4-26b-text
+      # ADR-017 v3: use the gemma4-26b-json gateway alias which auto-injects
+      # response_format=json_object + chat_template_kwargs.enable_thinking=false
+      # via LiteLLM extra_body. The Graphiti MCP server v1.0.2 doesn't expose
+      # those params as first-class client config, so we force them at the
+      # gateway layer (homelab-infra litellm-gateway role). Other consumers
+      # (Hermes, OWUI) keep using gemma4-26b-text unchanged.
+      - MODEL_NAME=gemma4-26b-json
       - LLM_MAX_TOKENS=1500
```

`LLM_RESPONSE_FORMAT` and `LLM_ENABLE_THINKING` were not present in the file — no removal needed.

## 7. Graphiti container restart + post-restart health

```
$ docker compose up -d
 Container graphiti-mcp Recreated
 Container graphiti-mcp Started

$ docker ps --filter name=graphiti-mcp
NAMES          STATUS
graphiti-mcp   Up 9 seconds (healthy)

$ docker logs graphiti-mcp --since 30s | grep "LLM provider"
graphiti_mcp_server - INFO - Using LLM provider: openai / gemma4-26b-json

$ curl -sS -o /dev/null -w 'HTTP %{http_code}\n' http://127.0.0.1:8000/health
HTTP 200
```

Container healthy on the new alias; falkordb depends_on healthcheck passed; healthcheck cycle stable.

## 8. E3-S04 status summary

| Part | Description | Status |
| --- | --- | --- |
| (a) | LLM gateway alias `gemma4-26b-json` with `extra_body` injection; Graphiti MCP cut over | DONE (this doc) |
| (b) | Real `OPENAI_API_KEY` in `stacks/graphiti/.env` for the cloud-OpenAI embedder client (text-embedding-3-small per ADR-003) | BLOCKED on operator |

Until part (b) lands, Graphiti MCP `/health` reports OK (LLM client + DB connect), but any `add_memory` MCP call that triggers an embedding request will fail with an OpenAI auth error. E3-S05 (first real episode ingest) cannot complete without it.

## 9. Anything unexpected

- Nothing. `extra_body` syntax matched the documented pattern exactly; gateway accepted the config on first try; `/v1/models` listed the new alias; the probe confirmed both `response_format` and `chat_template_kwargs.enable_thinking=false` are being merged into the upstream request body.
- Wall-time of the probe (33s) is within the expected envelope for the gemma-hybrid-proxy path on a non-warm GPU; no cause for concern relative to E3-S01.5 spike numbers.
