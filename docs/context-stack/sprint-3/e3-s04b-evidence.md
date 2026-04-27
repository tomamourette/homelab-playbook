# E3-S04 part (b) — `gemini-embedding-2` via LiteLLM gateway evidence

**Sprint 3 / Epic E3 / story 4 of 9 (part b — embedder cutover, ADR-003 v2)**
**Date:** 2026-04-26
**Branch:** `feature/context-stack-e3-graphiti` (homelab-infra + homelab-apps + homelab-playbook)
**Status:** part (b) primary deliverable DONE — `gemini-embedding-2` is wired
through the LiteLLM gateway and verified end-to-end at the Graphiti-core
`OpenAIEmbedder` client layer (3072-dim vectors round-trip cleanly). The
opportunistic E3-S05 smoke test (`add_memory` MCP call) surfaced a separate,
**pre-existing, independent** blocker on the LLM-extraction path that is out of
scope for this story; flagged below for a follow-up story.

## 1. Why v2, not v1

ADR-003 v1 (2026-04-25) selected OpenAI `text-embedding-3-small`. The E3-S04b
research pass (`docs/context-stack/sprint-3/e3-s04b-embedder-research.md`,
Addendum starting line 124) found three load-bearing facts that flipped the
verdict to **`gemini-embedding-2`**:

1. v2 went GA 2026-04-22 — "preview only" framing in the main body of the
   research report was stale by four days.
2. The MTEB scores attributed to `gemini-embedding-001` in the main body were
   actually v2's numbers (68.32 MMTEB, 73.30 English-v2, 74.66 Code — three
   tracks #1 simultaneously). v1 standalone scores were not separately
   reported in v2-era recaps. Picking v1 would mean paying for a worse model
   under a misattributed benchmark.
3. Graphiti's `GeminiEmbedder` (and the OpenAI-protocol `OpenAIEmbedder` we
   actually use through the gateway) accepts the model name as plain config
   — zero code change to switch.

## 2. Vault changes (host-scoped per existing pattern)

The brief specified `inventories/group_vars/all/vault.yml` (file-encrypted),
but the existing convention for ct-ai-01-only secrets is inline-`!vault`
scalars in `host_vars/ct-ai-01/vault.yml` (already used for
`vault_litellm_master_key`). I followed the existing convention.

```
homelab-infra/ansible/inventories/homelab/host_vars/ct-ai-01/vault.yml
  + vault_gemini_api_key: !vault | … 39-char Google API key …
```

Verification (from a Python loader using `ansible.parsing.vault.VaultLib`,
key value never echoed):

- `vault_litellm_master_key` length: 67 chars (unchanged)
- `vault_gemini_api_key` length: 39 chars (matches the source `.gemini-key-e3-s04`
  byte-count and Google's documented `AIza…` prefix length)

## 3. LiteLLM gateway changes

Three template files in
`homelab-infra/ansible/roles/litellm-gateway/`:

**`defaults/main.yml`** — add the Jinja-resolved variable that maps the vault
secret onto the role's namespace:

```yaml
litellm_gemini_api_key: "{{ vault_gemini_api_key | default('REPLACE_ME_VIA_VAULT') }}"
```

**`templates/env.j2`** — add `GEMINI_API_KEY` to the systemd EnvironmentFile so
LiteLLM can resolve `os.environ/GEMINI_API_KEY` at request time:

```
GEMINI_API_KEY={{ litellm_gemini_api_key }}
```

**`templates/litellm-config.yaml.j2`** — new alias entry under `model_list`
(after the chat-completion aliases):

```yaml
  # ── Embedder aliases (E3-S04b, ADR-003 v2 amendment 2026-04-26) ─────
  - model_name: gemini-embedding-2
    litellm_params:
      model: gemini/gemini-embedding-2
      api_key: os.environ/GEMINI_API_KEY
```

Plus a global `drop_params: true` under `litellm_settings` (E3-S04b discovery
— see §6 for the failure that surfaced this requirement):

```yaml
litellm_settings:
  drop_params: true
  callbacks: ["prometheus"]   # only when litellm_enable_prometheus
```

## 4. Ansible deploy outcome

```
PLAY RECAP
ct-ai-01                   : ok=16   changed=3    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
```

(First deploy.) Tasks `Render LiteLLM config`, `Render LiteLLM environment file`,
and the `Restart litellm-gateway` handler all `changed`. Health probe
(`/health/liveliness`) returned 200 after the standard uvicorn warm-up retry
window. Confirmed from workstation:

```
$ curl -sS -o /dev/null -w 'liveliness HTTP %{http_code} time=%{time_total}s\n' \
    http://192.168.50.160:4000/health/liveliness
liveliness HTTP 200 time=0.001639s
```

A second deploy (after the `drop_params` fix) was identical except `changed=2`
(config + handler restart only).

## 5. Embedder probe — gateway side (HTTP)

```bash
curl -sS -m 60 -o /tmp/e3-s04b-resp.json -w 'HTTP %{http_code} time=%{time_total}s' \
  -H "Authorization: Bearer $LITELLM_KEY" -H "Content-Type: application/json" \
  --data-binary @/tmp/e3-s04b-probe.json \
  http://192.168.50.160:4000/v1/embeddings
```

Payload was `{"model":"gemini-embedding-2","input":["FalkorDB is a Redis-derived graph database used as Graphiti's storage backend."]}`.

| Check                   | Value                                                 |
|-------------------------|-------------------------------------------------------|
| HTTP status             | 200                                                   |
| Wall time               | 0.413 s                                               |
| Response object         | `list`                                                |
| `model` in response     | `gemini-embedding-2`                                  |
| Vector dimension        | 3072                                                  |
| First 3 floats          | `[-0.004932652, 0.027712563, -0.0125886025]`          |
| Last 3 floats           | `[-0.008048, 0.005654521, -0.0014484071]`             |
| Token usage             | `prompt=18, total=18`                                 |

`/v1/models` listing post-deploy confirms the alias appears alongside the four
chat-completion aliases:

```
gemma4-auto, gemma4-26b-text, gemma4-e4b-vision, gemma4-26b-json, gemini-embedding-2
```

## 6. Embedder probe — Graphiti embedder client (in-container)

To prove the embedder works through Graphiti's actual code path (not just at
the gateway HTTP layer), I exec'd into the `graphiti-mcp` container and called
`graphiti_core.embedder.openai.OpenAIEmbedder.create()` directly using the
same env vars Graphiti reads at startup:

```python
cfg = OpenAIEmbedderConfig(
    api_key=os.environ['OPENAI_API_KEY'],            # litellm master key
    embedding_model='gemini-embedding-2',
    embedding_dim=3072,
    base_url=os.environ['EMBEDDER_BASE_URL'],        # http://192.168.50.160:4000/v1
)
e = OpenAIEmbedder(config=cfg)
vec = await e.create('FalkorDB is a graph DB used as Graphiti backend.')
```

First attempt **failed** with:

```
openai.BadRequestError: Error code: 400 - {'error': {'message':
"litellm.UnsupportedParamsError: gemini does not support parameters:
{'encoding_format': 'base64'}, for model=gemini-embedding-2."}}
```

Root cause: openai-python ≥1.45 sends `encoding_format=base64` by default on
`embeddings.create()`. The Gemini provider rejects it. Fix is **on the gateway
side**: add `litellm_settings.drop_params: true`. After re-deploy:

```
embedding ok: dim=3072, first3=[0.0039779525, 0.021969197, -0.0039228033],
              last3=[-0.0069680465, -9.603066e-05, -0.007700739]
```

End-to-end embedder path verified at the Graphiti library level. **This is the
load-bearing E3-S04b acceptance** — every layer between Graphiti's embedder
call and Google's API now works through the LiteLLM gateway transparently.

## 7. Graphiti compose & config diff

`homelab-apps/stacks/graphiti/docker-compose.yml`:

```diff
       # ---- LLM (LiteLLM gateway on ct-ai-01 — Tailscale-routable LAN IP) ----
+      # E3-S04b workaround for upstream graphiti-mcp v1.0.2 bug:
+      # services/factories.py constructs CoreLLMConfig WITHOUT passing
+      # base_url for the openai LLM provider. Workaround: set OPENAI_BASE_URL
+      # env-var; AsyncOpenAI reads it via the SDK's standard env fallback
+      # when base_url is None.
+      - OPENAI_BASE_URL=http://192.168.50.160:4000/v1
       - LITELLM_BASE_URL=http://192.168.50.160:4000/v1
       …
-      # ---- Embedder (cloud OpenAI per ADR-003) ----
-      - EMBEDDER_BASE_URL=https://api.openai.com/v1
-      - EMBEDDER_MODEL=text-embedding-3-small
+      # ---- Embedder (LiteLLM gateway → Gemini, ADR-003 v2 2026-04-26) ----
+      - EMBEDDER_BASE_URL=http://192.168.50.160:4000/v1
+      - EMBEDDER_MODEL=gemini-embedding-2
```

`homelab-apps/stacks/graphiti/config-graphiti-mcp.yaml`:

```diff
 embedder:
+  # E3-S04b / ADR-003 v2 (2026-04-26): switched from cloud OpenAI
+  # text-embedding-3-small (1536-dim) to Google gemini-embedding-2 (3072-dim)
   provider: "openai"
-  model: ${EMBEDDER_MODEL:text-embedding-3-small}
-  dimensions: 1536
+  model: ${EMBEDDER_MODEL:gemini-embedding-2}
+  dimensions: 3072
   providers:
     openai:
-      api_key: ${OPENAI_API_KEY}                    # cloud OpenAI key (placeholder until E3-S04)
-      api_url: ${EMBEDDER_BASE_URL:https://api.openai.com/v1}
+      api_key: ${OPENAI_API_KEY}                    # LiteLLM master key
+      api_url: ${EMBEDDER_BASE_URL:http://192.168.50.160:4000/v1}
```

`homelab-apps/stacks/graphiti/.env` (gitignored): `OPENAI_API_KEY` flipped from
`PLACEHOLDER_FILL_IN_E3_S04` to the LiteLLM master key (same value as
`LITELLM_MASTER_KEY` in the same file). `.env.sample` updated to document the
new shape.

## 8. Graphiti restart and post-restart health

```
$ docker compose up -d
 Container falkordb Healthy
 Container graphiti-mcp Recreated
 Container graphiti-mcp Started

$ docker ps --filter name=graphiti-mcp --format 'table {{.Names}}\t{{.Status}}'
NAMES          STATUS
graphiti-mcp   Up 12 seconds (healthy)

$ docker logs graphiti-mcp --since 30s | grep -E "(LLM provider|Embedder|Successfully)"
graphiti_mcp_server - INFO - Successfully initialized Graphiti client
graphiti_mcp_server - INFO - Using LLM provider: openai / gemma4-26b-json
graphiti_mcp_server - INFO - Using Embedder provider: openai
graphiti_mcp_server - INFO -   - Embedder: openai / gemini-embedding-2

$ curl -sS -w 'health %{http_code}\n' http://127.0.0.1:8000/health
{"status":"healthy","service":"graphiti-mcp"} health 200
```

`Using Embedder provider: openai / gemini-embedding-2` — the model name
propagates correctly into Graphiti's runtime.

## 9. MCP smoke test (opportunistic E3-S05 attempt)

The brief asked to land an opportunistic E3-S05 smoke test (`add_memory` →
queue worker → `search_nodes`). Result: **the embedder side works, but
`add_memory` cannot complete because the LLM-extraction step hits an
independent, pre-existing blocker.**

### 9.1 What worked

- `initialize` (HTTP 200) — session-id `191e1cc5...` returned in headers.
- `notifications/initialized` (HTTP 202).
- `tools/call add_memory` (HTTP 200, 11 ms) — episode queued for processing
  in group `e3-s04b-smoke`.
- Queue worker started: `services.queue_service - INFO - Starting episode
  queue worker for group_id: e3-s04b-smoke`.

### 9.2 What failed (and why it's not E3-S04b's problem)

The queue worker calls `graphiti_core.llm_client.openai_client.OpenAIClient`
to do entity/edge extraction from the episode body. That client uses the new
**OpenAI Responses API path** (`/v1/responses`, via
`self.client.responses.parse(...)` — verified in
`graphiti_core/llm_client/openai_client.py:99`). Two distinct issues
surfaced:

**Issue A — graphiti-mcp factory bug.** The first attempt sent the
extraction request to `https://api.openai.com/v1/responses` instead of the
LiteLLM gateway. Root cause: the upstream graphiti-mcp v1.0.2 server's
`services/factories.py` (lines 122-130) constructs `CoreLLMConfig` for the
`openai` provider **without passing `base_url`**, so AsyncOpenAI falls back
to the SDK default. The `azure_openai` and `groq` provider branches in the
same factory *do* pass `base_url`. This is a latent bug in upstream that
has been masked since E3-S02 because no one had run `add_memory` end-to-end
(E3-S02 only checked `/health`, E3-S03 checked MCP `initialize`/`tools/list`,
E3-S04a verified the gateway alias via direct curl). I worked around it by
setting `OPENAI_BASE_URL` at the container env level — `AsyncOpenAI` reads
it as a fallback when `base_url=None` is passed.

**Issue B — `/v1/responses` not routable through LiteLLM 1.83.13.** With
the env workaround in place, the request now reaches the gateway, but
LiteLLM returns 404:

```
litellm.NotFoundError: NotFoundError: OpenAIException - {"detail":"Not Found"}.
Received Model Group=gemma4-26b-json
Available Model Group Fallbacks=None
```

LiteLLM 1.83.13's proxy exposes `/v1/chat/completions` and `/v1/embeddings`
for `model_list` aliases but **does not route `/v1/responses`** to them. This
is an upstream mismatch between graphiti-core 0.28.2's choice of the new
Responses API and LiteLLM's proxy surface. Resolution paths (none in scope
for E3-S04b):

1. Patch upstream graphiti-mcp to accept an `openai_generic` provider
   (which uses `chat.completions.create` — see
   `graphiti_core/llm_client/openai_generic_client.py:123`) and switch
   `config-graphiti-mcp.yaml` to that provider.
2. Wait for / contribute LiteLLM Responses-API proxy support.
3. Send a real cloud-OpenAI key as `OPENAI_API_KEY` and unset `OPENAI_BASE_URL`
   so the LLM extraction goes directly to api.openai.com (abandons ADR-017 v3
   ADOPT-LOCAL Gemma; defeats the gateway-egress goal).

These are architecture-level decisions for a follow-up story. Recommended
path: option 1 (one-file patch in graphiti-mcp factory + provider switch in
the YAML; preserves the gateway egress goal and stays on local Gemma).

### 9.3 Smoke test acceptance status

| Step                                | Outcome                                                  |
|-------------------------------------|----------------------------------------------------------|
| MCP `initialize`                    | OK (HTTP 200, session id returned)                       |
| MCP `notifications/initialized`     | OK (HTTP 202)                                            |
| `tools/call add_memory`             | OK (HTTP 200, 11 ms — episode queued)                    |
| Queue worker triggers extraction    | OK (worker logs entry visible)                           |
| LLM extraction completes            | **FAILED** — Issue B above                               |
| Embedding step (would follow)       | not reached                                              |
| `tools/call search_nodes` returns ≥1 | not reached                                              |
| `tools/call get_episodes` returns ≥1 | not reached                                              |

Embedder-only verification (§6 above) is the load-bearing acceptance for
this story.

## 10. Commit summary

Three commits, one per repo, branch `feature/context-stack-e3-graphiti`:

- `homelab-infra` — vault key, role defaults, env template, config template
  (gateway alias + drop_params).
- `homelab-apps` — compose env (OPENAI_BASE_URL, EMBEDDER_*), config-yaml
  (embedder.dimensions=3072, default URLs).
- `homelab-playbook` — ADR-003 v2 amendment + this evidence doc.

(SHAs added at commit time — see git log on the branch.)

## 11. Anything unexpected

Three unexpected findings, ordered by impact:

1. **graphiti-mcp v1.0.2 factory ignores `llm.providers.openai.api_url`.**
   The YAML schema accepts the field, the schema does parse it, but
   `services/factories.py` lines 122-130 don't pass it through to
   `CoreLLMConfig`. The `azure_openai` and `groq` cases do. Worked around
   here via `OPENAI_BASE_URL` env-var fallback; would benefit from an
   upstream PR.

2. **graphiti-core 0.28.2's `OpenAIClient` uses the Responses API
   (`/v1/responses`)** which LiteLLM 1.83.13 does not proxy to its
   `model_list` aliases. Discovered when the workaround in (1) routed the
   request to the gateway and got a 404. This is a graphiti-core / LiteLLM
   version mismatch, not anything in E3-S04b's lane.

3. **openai-python ≥1.45 sends `encoding_format=base64` by default on
   `embeddings.create()`** which the Gemini provider rejects through
   LiteLLM. Resolved cleanly by adding `litellm_settings.drop_params: true`
   to the gateway config.

The vault was structured differently from the brief's expectation
(host_vars/ct-ai-01 inline-`!vault` scalars vs. group_vars/all
file-encrypted) — I matched the existing pattern (`vault_litellm_master_key`
already lives there for this exact same role/host combination).

## 12. Next-step status

**E3-S04b primary deliverable: DONE.** `gemini-embedding-2` is wired through
the LiteLLM gateway, vault-secured, ansible-managed, and verified at the
Graphiti-core embedder client layer (3072-dim vectors round-trip).

**E3-S05 (full functional smoke tests) is BLOCKED on a follow-up story to
either patch graphiti-mcp's openai-provider factory or switch to the
`openai_generic` provider class.** The embedder portion of any future smoke
test will work; the LLM extraction will not until the
`/v1/responses`-vs-LiteLLM mismatch is resolved.

**Recommendation:** open a new story (E3-S04c?) — "Patch graphiti-mcp v1.0.2
LLM provider to use chat.completions via openai_generic" — before E3-S05.
Estimated 1-2 hours: fork graphiti-mcp, change one file in factories.py,
either rebuild the image or contribute upstream. This is the smaller of the
two resolution paths and keeps ADR-017 v3 ADOPT-LOCAL intact.

NOT-READY for E3-S06 (full functional smoke-test suite) — the LLM-side
blocker must clear first.
