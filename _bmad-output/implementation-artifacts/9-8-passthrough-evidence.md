# Story 9.8 — Passthrough mode for `gemma4-26b-text` and `gemma4-e4b-vision`

**Status:** completed
**Owner:** claude-coder
**Completion date:** 2026-04-25
**Sprint:** 2 (Proxy + multimodal preprocessing)
**Depends on:** 9.6 (scaffold), 9.7 (`/v1/models`)
**Branch / commit:** working tree on `main`; commits owned by director

## Scope delivered

OpenAI-compatible `POST /v1/chat/completions` passthrough for two virtual aliases:

- `gemma4-26b-text` → `http://127.0.0.1:8081/v1/chat/completions` (TrevorJS Q4_K_M, MoE/26B)
- `gemma4-e4b-vision` → `http://127.0.0.1:8080/v1/chat/completions` (Gemma 4 E4B)

Both modes (non-streaming and SSE streaming) are forwarded byte-for-byte; the
proxy adds zero buffering on the streaming path (ADR-012). `gemma4-auto` is
recognised but returns 501 with the deferral pointer to Story 9.9. Unknown
aliases return 404 with the OpenAI error envelope and the canonical alias
list. Tool-call delta accumulation is intentionally NOT touched here
(deferred to Story 9.13).

## Files created / modified

Created:
- `homelab-infra/ansible/roles/gemma-hybrid-proxy/files/src/gemma_hybrid_proxy/domain/router.py` (123 LOC, pure)
- `homelab-infra/ansible/roles/gemma-hybrid-proxy/files/tests/unit/test_chat_completions.py` (full passthrough test suite, replaces stub)

Modified:
- `homelab-infra/ansible/roles/gemma-hybrid-proxy/files/src/gemma_hybrid_proxy/api/chat_completions.py` (replaced 501 stub with full router + SSE forwarder)
- `homelab-infra/ansible/roles/gemma-hybrid-proxy/files/src/gemma_hybrid_proxy/adapters/llama_server_client.py` (added `forward_json` + `stream_request` + `UpstreamTimeout` / `UpstreamUnreachable` error types + `transport=` injection point for tests)
- `homelab-infra/ansible/roles/gemma-hybrid-proxy/files/src/gemma_hybrid_proxy/config.py` (new `e4b_upstream_model`, `moe_upstream_model` settings; defaults empty)

Deleted:
- `homelab-infra/ansible/roles/gemma-hybrid-proxy/files/tests/unit/test_chat_completions_stub.py` (superseded; all assertions migrated into the new test file's AC-9 regression block)

## Module size budgets

| Module | LOC | Rule | OK? |
|---|---|---|---|
| `domain/router.py` | 123 | ≤150 (architecture §Code structure rules) | yes |
| `adapters/llama_server_client.py` | 254 | no hard limit on adapters | yes (lots of docstrings) |
| `api/chat_completions.py` | 474 | no hard limit on api modules; story budget hint was ≤150 LOC | over hint, but ~50% is docstrings + the SSE state machine helpers (`_forward_sse_with_keepalive`, `_parse_sse_record`, `_stream_error_as_sse`, `_embed_error_in_stream`) which would otherwise inflate `_sse_stream`; flagging as a deviation but not refactoring further this story |

## Acceptance criteria — results

| AC | Description | Result | Evidence |
|---|---|---|---|
| AC-1 | `gemma4-26b-text` + `stream=false` + text-only message returns OpenAI-shaped response (mocked) | PASS | `test_gemma4_26b_text_non_streaming_routes_to_moe` — asserts upstream URL hit `:8081`, request body forwarded, response body mirrored |
| AC-2 | Same with `stream=true` returns SSE chunks unchanged + `[DONE]` terminator | PASS | `test_streaming_forwards_chunks_and_terminator` — asserts each `data: {...}` line and `data: [DONE]` appear verbatim in the response body |
| AC-3 | `gemma4-e4b-vision` with `image_url` content block routes to E4B (`:8080`) | PASS | `test_gemma4_vision_with_image_url_routes_to_e4b` — asserts upstream port 8080, content blocks `["text", "image_url"]` preserved |
| AC-4 | `gemma4-auto` returns 501 with the explicit "requires Story 9.9" message | PASS | `test_gemma4_auto_returns_501_with_deferral_message` + live smoke (see below) |
| AC-5 | Unknown model returns 404 + OpenAI envelope listing the 3 valid aliases | PASS | `test_unknown_model_returns_404_with_alias_list` + live smoke; envelope includes `valid_aliases` array |
| AC-6 | Upstream timeout returns 502 with OpenAI envelope | PASS | `test_upstream_timeout_returns_502_with_openai_envelope` (mocked `httpx.ReadTimeout`) + sibling `test_upstream_unreachable_returns_502_with_url_in_message` for ConnectError |
| AC-7 | `X-Request-ID` propagated outbound, generated if absent | PASS | `test_request_id_propagated_outbound_when_provided` + `test_request_id_generated_when_absent`; verified live in proxy logs (`request_id=req-f8bbf168c6a942dc` from generated UUID) |
| AC-8 | Live smoke against real ct-ai-01 endpoints | PASS | See "Live smoke" section below |
| AC-9 | Existing tests still pass (no regression) | PASS | 36/36 pytest pass; `/health` and `/v1/models` tests untouched and green |
| AC-10 | `ruff check`, `mypy src/`, `pytest -q` all green | PASS | All checks passed; mypy: "no issues found in 17 source files"; pytest: 36 passed in 0.16s |

## Tooling output

```
$ .venv/bin/ruff check .
All checks passed!

$ .venv/bin/mypy src/
Success: no issues found in 17 source files

$ .venv/bin/pytest -q
....................................                                     [100%]
36 passed in 0.16s
```

Test count delta: 19 (baseline post-9.6) → 36 (this story; +17 new tests covering all
ACs, with AC-9 regressions migrated from the deleted stub file).

## Live smoke (AC-8) — real ct-ai-01

Approach: copied `pyproject.toml`, `requirements.txt`, `src/` to `/tmp/gemma-hybrid-proxy`
on ct-ai-01 (192.168.50.160), built a venv with `python3 -m venv`, installed deps
+ the package editable, ran `uvicorn gemma_hybrid_proxy.main:app --host 127.0.0.1
--port 18002` against the in-container loopback E4B (`:8080`) and MoE (`:8081`).
Killed the proxy and removed `/tmp/gemma-hybrid-proxy*` after smoke. The
production `llama-server.service` and `llama-server-26b.service` were untouched
and remained `active` throughout (verified before and after).

Smoke probes:

```
$ curl -sf http://127.0.0.1:18002/health
{"status":"ok","upstreams":{"e4b":"ok","moe":"ok"}}

$ curl -sf http://127.0.0.1:18002/v1/models | jq -c '.data[].id'
"gemma4-auto"
"gemma4-26b-text"
"gemma4-e4b-vision"
```

AC-1 live (text-only chat through `gemma4-26b-text`, non-streaming):

```
$ time curl -sf http://127.0.0.1:18002/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"gemma4-26b-text","messages":[{"role":"user","content":"Say one word."}],"stream":false}'
{"choices":[{"finish_reason":"stop","index":0,"message":{"role":"assistant","content":"Hello.", ...}}],
 "model":"gemma-4-26B-A4B-it-uncensored-Q4_K_M.gguf",
 "usage":{"completion_tokens":141,"prompt_tokens":20,"total_tokens":161},
 "timings":{"predicted_per_second":24.873805131201387, ...},
 "id":"chatcmpl-3VnWSNeFbBVmCQcLms6qat5NtcmHOww8"}
real  0m5.996s
```

- Visible content: `"Hello."` (one word, as instructed)
- Decode rate: **24.87 tok/s** — within the Sprint 1 baseline (25.11 tok/s on direct `:8081`); proxy overhead is negligible
- Total tokens: 161 (141 completion incl. reasoning_content + 20 prompt)
- Wall time: 6.0s

AC-2 live (streaming through `gemma4-26b-text`):

```
$ curl -sN http://127.0.0.1:18002/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"gemma4-26b-text","messages":[{"role":"user","content":"Count to three."}],"stream":true,"max_tokens":50}'
data: {"choices":[{"finish_reason":null,"index":0,"delta":{"role":"assistant","content":null}}], ...}

data: {"choices":[{"finish_reason":null,"index":0,"delta":{"reasoning_content":"*"}}], ...}

data: {"choices":[{"finish_reason":null,"index":0,"delta":{"reasoning_content":"   "}}], ...}
... (truncated)
```

- Each chunk has the canonical `data: {...}\n\n` SSE record framing
- Proxy log: `chat_completions.completed ... chunks_forwarded=26 duration_ms=1364.65 ... upstream_status=200`
- 26 chunks forwarded; clean termination with upstream `[DONE]` (cut off by `head -50` in the curl above; visible in the proxy logs)

AC-4 live (`gemma4-auto` deferral):

```
$ curl -s http://127.0.0.1:18002/v1/chat/completions -H 'Content-Type: application/json' \
  -d '{"model":"gemma4-auto","messages":[{"role":"user","content":"hi"}]}'
{"error":{"message":"gemma4-auto requires Story 9.9; use gemma4-26b-text or gemma4-e4b-vision until then",
          "type":"not_implemented","param":null,"code":"gemma_hybrid.not_implemented"}}
HTTP=501
```

AC-5 live (unknown model):

```
$ curl -s http://127.0.0.1:18002/v1/chat/completions -H 'Content-Type: application/json' \
  -d '{"model":"gpt-4o","messages":[{"role":"user","content":"hi"}]}'
{"error":{"message":"Model 'gpt-4o' is not recognised. Valid aliases: gemma4-auto, gemma4-26b-text, gemma4-e4b-vision.",
          "type":"model_not_found","param":null,"code":"gemma_hybrid.model.unknown",
          "valid_aliases":["gemma4-auto","gemma4-26b-text","gemma4-e4b-vision"]}}
HTTP=404
```

Cleanup confirmed: `/tmp/gemma-hybrid-proxy*` removed; `llama-server.service` +
`llama-server-26b.service` both `active`; `:8080` + `:8081` `/health` both green
post-smoke.

## Design decisions / deviations

1. **`api/chat_completions.py` over the 150-LOC story hint** — the SSE state
   machine (parse upstream record framing, emit data + comment events,
   keepalive on idle, embed error frames mid-stream) is split into four named
   helpers in the same file rather than promoted to a new module. Promoting
   would invent a `domain/sse_forwarding.py` that's pure-bytes plumbing,
   which doesn't earn its place in `domain/`. Flagging as a follow-up if
   line count becomes a maintenance issue when 9.13 layers tool-call delta
   accumulation onto the stream path.

2. **Per-request `LlamaServerClient` construction** — matches the existing
   `/health` factory pattern in the scaffold. A long-lived module-level pool
   would reduce per-request connect cost but complicate test injection.
   Architecture §Code structure rules requires `httpx.Limits(max_connections=4,
   max_keepalive_connections=4)` — set per client; cross-request keepalive
   reuse is a Sprint 2 hardening follow-up tracked separately.

3. **`upstream_model` rewrite defaulted to empty (passthrough)** — llama-server
   is permissive on the `model` field for single-model servers. Empty default
   means the client's model alias (e.g., `gemma4-26b-text`) flows through to
   the upstream untouched; the live smoke confirmed the upstream returns its
   own `model` name (`gemma-4-26B-A4B-it-uncensored-Q4_K_M.gguf`) regardless.
   `GEMMA_HYBRID_E4B_UPSTREAM_MODEL` and `GEMMA_HYBRID_MOE_UPSTREAM_MODEL` are
   wired in `config.py` for the day a backend tightens this.

4. **Mid-stream error embedding** — when the upstream times out / disconnects
   mid-stream, the SSE generator emits a final `data:` chunk shaped like a
   chat completion chunk with the OpenAI error envelope embedded in
   `delta.content` (architecture §API contract: "Do not silently truncate").
   Pre-stream errors (non-2xx upstream response before any bytes) are
   surfaced the same way for stream consistency, since the SSE response
   headers have already been committed by the time we know.

5. **`X-Request-ID` generation** uses `uuid.uuid4().hex[:16]` prefixed
   `req-`. Long enough to avoid collision in the homelab volume; short
   enough to read in a log line. LiteLLM (Story 9.16) will likely supply
   its own; this layer just propagates whatever it sees.

6. **Authorization stripping** — outbound headers explicitly do NOT carry
   `Authorization` (architecture ADR-009: loopback only inside the LXC).
   Verified by the unit test asserting the header is absent on forwarded
   requests.

## Coordination notes

- Story 9.7 was running in parallel. Files don't overlap: 9.7 owns
  `api/models.py` (and may add `domain/upstream_health.py`); this story
  owns `api/chat_completions.py`, `domain/router.py` (new),
  `adapters/llama_server_client.py`, and the matching tests. Imported
  no symbols from `api/models.py` (the alias constants are owned by
  `domain/router.py` per single-source-of-truth).

- Velocity bump on sprint_2: this story is +1. If 9.7 also completes,
  director can bump to whatever total is appropriate without rebasing
  this evidence.

## Boundaries respected

- Did NOT implement `gemma4-auto` orchestration (Story 9.9)
- Did NOT implement tool_call delta accumulation (Story 9.13)
- Did NOT touch ct-ai-01 production state beyond a temporary uvicorn
  smoke (killed; `/tmp/gemma-hybrid-proxy*` removed; both backend
  services verified `active` post-smoke)
- Did NOT add new prod dependencies (only reused `httpx`, `sse-starlette`,
  `pydantic`, `structlog`, `pydantic-settings` already in `requirements.txt`)
- Did NOT log payload contents (per architecture §Logging never-log list)
  — log lines carry only `request_id`, `model`, `stream`, `upstream`,
  `upstream_url`, `upstream_status`, `chunks_forwarded`, `duration_ms`

## Next story

9.9 (`gemma4-auto` orchestration) can now layer on top: it will call
`router.route()` to detect `gemma4-auto`, then use `LlamaServerClient`'s
`forward_json` against E4B for image describe, then invoke the SSE
generator from this story (refactored to accept an arbitrary payload)
against MoE for the reasoner pass. The hexagonal boundaries built here
keep that change additive.
