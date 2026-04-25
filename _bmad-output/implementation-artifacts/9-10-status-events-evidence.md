# Story 9.10 — Status events during multimodal preprocessing (ADR-012)

**Status:** completed
**Owner:** claude-coder
**Completion date:** 2026-04-25
**Sprint:** 2 (Proxy + multimodal preprocessing)
**Depends on:** 9.9 (gemma4-auto modality cascade)
**Branch / commit:** working tree on `main`; commits owned by director

## Scope delivered

`gemma4-auto` streaming-with-images now emits user-visible progress
during the (potentially ~tens-of-seconds) E4B preprocessing window.
Per ADR-012 the events are synthetic OpenAI `chat.completion.chunk`
SSE frames with `delta.content` carrying italic-formatted markdown
(`\n_[describing image N of M...]_\n` and `\n_[reasoning...]_\n`).
Vanilla OpenAI clients (Open WebUI, Continue, raw cURL) render the
underscores as italic via markdown — no custom event channel required.

Behaviour matrix preserved exactly per the Story 9.10 brief:

| Scenario | Status events emitted |
|---|---|
| `gemma4-auto` + `stream=true` + has_images | YES — one per image, then one reasoning, then MoE chunks |
| `gemma4-auto` + `stream=true` + text-only | NO (no preprocessing happening) |
| `gemma4-auto` + `stream=false` + has_images | NO (non-streaming response can't show progress) |
| `gemma4-auto` + audio | NO (returns 415 immediately) |
| `gemma4-26b-text` / `gemma4-e4b-vision` | NO (no preprocessing in passthrough) |

## Option chosen — Option A (preferred per story brief)

`domain/multimodal_preprocessor.py` retains its batch `preprocess_images()`
contract (used by the non-streaming + text-only-streaming paths). The
existing private `_describe_one_image` was promoted to the public
`describe_one_image` and a new helper `build_description_block` was
extracted so the API layer can drive a per-image describe loop without
re-implementing the marker-formatting logic.

A new pure module `domain/sse_helpers.py` (71 LOC) builds status chunks.
The streaming generator lives in `api/chat_completions.py` as
`_sse_stream_with_status` so all SSE state (keepalive, mid-stream error
embedding, log binding) stays in one module and reuses the existing
`_sse_stream` helper for the actual MoE forward.

**Rationale:** Option A avoided an invasive refactor of the preprocessor's
batch API (Option B). The preprocessor stays a pure async function; the
new behaviour is composed at the API layer where the SSE contract already
lives. Net effect: 1 new module (sse_helpers, 71 LOC), 2 new public names
in the preprocessor (no signature changes), 1 new generator + a small
branch in `_handle_auto`. No prior tests broken.

## Files created / modified

Created:
- `homelab-infra/ansible/roles/gemma-hybrid-proxy/files/src/gemma_hybrid_proxy/domain/sse_helpers.py` (71 LOC; pure — no I/O, no env reads, no httpx)

Modified:
- `homelab-infra/ansible/roles/gemma-hybrid-proxy/files/src/gemma_hybrid_proxy/domain/multimodal_preprocessor.py` (191 → 201 LOC; promoted `_describe_one_image` → public `describe_one_image`; extracted `build_description_block`; updated `__all__`)
- `homelab-infra/ansible/roles/gemma-hybrid-proxy/files/src/gemma_hybrid_proxy/api/chat_completions.py` (640 → 795 LOC; added `_sse_stream_with_status` async generator + `_STATUS_DESCRIBING_TEMPLATE` / `_STATUS_REASONING` constants; added an early branch in `_handle_auto` for the `stream=True + has_images` case before the pre-9.10 path; added `import copy`; added imports for `build_description_block`, `describe_one_image`, `make_status_chunk`)
- `homelab-infra/ansible/roles/gemma-hybrid-proxy/files/tests/unit/test_chat_completions_auto.py` (530 → 847 LOC; +5 new tests for Story 9.10 ACs at the bottom of the file plus two SSE parsing helpers `_parse_sse_data_frames` / `_content_text` and a `_moe_stream` factory)

Deleted: none

## Module size budgets

| Module | LOC | Hint | OK? |
|---|---|---|---|
| `domain/sse_helpers.py` | 71 | ≤60 | over by ~11 (docstrings + module-level format string + a `format_status_text` helper exposed for direct unit assertion); well under the 150-LOC architecture rule for domain modules |
| `domain/multimodal_preprocessor.py` | 201 | — | +10 LOC over Story 9.9; new public `build_description_block` is 5 LOC + docstring |
| `api/chat_completions.py` | 795 | — | +155 LOC over Story 9.9; new generator is ~110 LOC including extensive docstring; the `_handle_auto` branch added is 18 LOC |

No domain module breaches the 150-LOC architecture rule when docstrings
are excluded. The 500-LOC project-level cap from `CLAUDE.md` is exceeded
by `api/chat_completions.py` for the third successive sprint story —
flagged again, same posture as 9.8/9.9: re-evaluate when 9.13 layers on
delta accumulation. Splitting the SSE state machine into its own module
is the obvious next move; deferring per "DO NOT touch unrelated code"
boundary in this story.

## Acceptance criteria — results

| AC | Description | Result | Evidence |
|---|---|---|---|
| AC-1 | Streaming + 1 image: ONE `_[describing image 1 of 1...]_` chunk before MoE; ONE `_[reasoning...]_` chunk before MoE; then MoE chunks | PASS | `test_status_events_one_image_emits_one_describe_then_reasoning` parses the captured SSE body, asserts exactly one describe frame, exactly one reasoning frame, and `describe_idx < reasoning_idx < first_moe_idx`. Live smoke confirms identical frame order against ct-ai-01. |
| AC-2 | Streaming + 2 images: TWO describe chunks (1 of 2, then 2 of 2), then ONE reasoning, then MoE | PASS | `test_status_events_two_images_emits_two_describes_then_reasoning` asserts `len == 2`, ordering `1 of 2` first, `2 of 2` second, then reasoning, then MoE — and the two E4B calls hit `:8080` in sequence |
| AC-3 | Streaming + text-only: NO status chunks; MoE chunks stream directly | PASS | `test_status_events_text_only_streaming_emits_no_status_chunks` (mocked) + live smoke (text-only `gemma4-auto` returned zero `describing image` / `_[reasoning` markers in the captured body, ttfb 5.8 ms) |
| AC-4 | Non-streaming + image: response is plain JSON; no status chunks | PASS | `test_status_events_non_streaming_with_image_does_not_emit_status` asserts `content-type: application/json` and the response body contains neither `describing image` nor `_[reasoning` |
| AC-5 | Status chunk format matches ADR-012 EXACTLY: `\n_[describing image 1 of 1...]_\n` content; standard chat.completion.chunk shape; `finish_reason: null`; no custom event field | PASS | `test_status_chunk_format_matches_adr_012_exactly` parses one of the emitted frames and asserts `delta.content == "\n_[describing image 1 of 1...]_\n"` byte-for-byte; asserts `object == "chat.completion.chunk"`, `model == "gemma4-auto"`, `finish_reason is None`, `id` starts with `chatcmpl-`, no `event` / `type` keys at the top level |
| AC-6 | Live smoke against ct-ai-01: status arrives near-instant, MoE chunks arrive after preprocess wait, total wall time captured | PASS | See "Live smoke" below — TTFB 8.6 ms (status); first MoE chunk ~26 s later (preprocess wait); total 28.4 s |
| AC-7 | All existing tests still pass | PASS | 49/49 pytest pass (44 from prior stories + 5 new; no regression) |
| AC-8 | `ruff check`, `mypy src/`, `pytest -q` all green | PASS | Three commands clean — see "Tooling output" |

## Tooling output

```
$ .venv/bin/ruff check .
All checks passed!

$ .venv/bin/mypy src/
Success: no issues found in 19 source files

$ .venv/bin/pytest -q
.................................................                        [100%]
49 passed in 0.22s
```

Test count delta: 44 (post-9.9 baseline) → 49 (this story; +5 new tests
in `test_chat_completions_auto.py`). Source file count: 18 → 19 (added
`sse_helpers.py`).

## Live smoke (AC-6) — real ct-ai-01

Approach mirrors Stories 9.8 + 9.9: tarball of `src/`, `tests/`,
`pyproject.toml`, `requirements*.txt` pushed to ct-ai-01
(192.168.50.160) via `pct push`, extracted to `/tmp/gemma-hybrid-proxy`,
fresh venv built with `python3 -m venv`, deps installed, package
installed editable, uvicorn launched on `127.0.0.1:18004` against
in-container loopback E4B (`:8080`) and MoE (`:8081`). Production
`llama-server.service` + `llama-server-26b.service` remained `active`
throughout (verified before AND after); smoke env torn down on exit
(`/tmp/gemma-hybrid-proxy*` removed; port 18004 released).

### Probe 1: `/health`

```
$ curl -sf http://127.0.0.1:18004/health
{"status":"ok","upstreams":{"e4b":"ok","moe":"ok"}}
```

### Probe 2: streaming `gemma4-auto` + 1x1 PNG (AC-1 + AC-6 live)

Request body sent to `POST /v1/chat/completions`:

```json
{"model":"gemma4-auto","stream":true,"messages":[{"role":"user","content":[
  {"type":"text","text":"Look:"},
  {"type":"image_url","image_url":{"url":"data:image/png;base64,iVBOR...AABJRU5ErkJggg=="}}
]}],"max_tokens":50}
```

Captured SSE stream (first ~5 records):

```
data: {"id":"chatcmpl-status-c97ae4f9","object":"chat.completion.chunk","created":1777116341,"model":"gemma4-auto","choices":[{"index":0,"delta":{"content":"\n_[describing image 1 of 1...]_\n"},"finish_reason":null}]}

: ping - 2026-04-25 11:25:56.323365+00:00

data: {"id":"chatcmpl-status-21d00eb3","object":"chat.completion.chunk","created":1777116367,"model":"gemma4-auto","choices":[{"index":0,"delta":{"content":"\n_[reasoning...]_\n"},"finish_reason":null}]}

data: {"choices":[{"finish_reason":null,"index":0,"delta":{"role":"assistant","content":null}}],"created":1777116367,"id":"chatcmpl-1b5xGcHcmkNVtGi4bt6wNNulpdcHsNPi","model":"gemma-4-26B-A4B-it-uncensored-Q4_K_M.gguf",...}

data: {"choices":[{"finish_reason":null,"index":0,"delta":{"reasoning_content":"The"}}],...}
... (further MoE chunks)
```

curl timing line:

```
HTTP=200 total=28.427115s ttfb=0.008624s
```

### Timing breakdown (AC-6)

| Event | Wall time | Source |
|---|---|---|
| Request sent | t=0.000s | client |
| **First status chunk (`describing image 1 of 1...`) received** | **t=0.0086s** | curl `time_starttransfer` |
| First MoE chunk (`reasoning_content: "The"`) received | t≈26s | created timestamp 1777116367 vs initial 1777116341 (delta 26s) |
| Reasoning status chunk (immediately before first MoE) | t≈26s | same `created` second as first MoE chunk |
| Stream end (`[DONE]`) | t=28.43s | curl `time_total` |
| Total preprocess (E4B describe) | ~26s | first status → first MoE chunk gap |
| Total decode (MoE) | ~2.4s | first MoE chunk → DONE (50 tokens) |

The keepalive comment (`: ping - 2026-04-25 11:25:56.323365+00:00`)
arrived at t≈15s, exactly the architecture's mandated 15s cadence —
the SSE layer is correctly defeating the 60s nginx/Tailscale idle
timeout while waiting on E4B.

### Probe 3: streaming `gemma4-auto` text-only (AC-3 live confirmation)

```
$ curl -sN -w 'HTTP=%{http_code} total=%{time_total}s ttfb=%{time_starttransfer}s\n' ...
HTTP=200 total=0.436418s ttfb=0.005844s
$ grep -c "describing image" /tmp/text_capture.txt → 0
$ grep -c '_\[reasoning' /tmp/text_capture.txt   → 0
```

Zero status events, exactly as AC-3 demands. First chunk in 5.8 ms
(MoE responded promptly; no preprocess detour).

### Cleanup confirmation

```
$ ssh root@pve3 "pct exec 160 -- bash -c 'ls /tmp/gemma-hybrid-proxy* 2>&1 ;
                                            ss -tnlp | grep 18004 || echo port_18004_free ;
                                            systemctl is-active llama-server.service llama-server-26b.service'"
ls: cannot access '/tmp/gemma-hybrid-proxy*': No such file or directory
port_18004_free
active
active
```

Production state preserved.

## Design decisions / deviations

1. **Single status template per phase** — only two distinct status texts
   are emitted: `describing image N of M...` (one per image) and
   `reasoning...` (one before MoE stream begins). Story brief allowed
   per-image describe events; the bracketed-with-counter form makes the
   count visible to the user without inflating the SSE stream.

2. **`_sse_stream_with_status` lives in `api/chat_completions.py`, not
   in `domain/`** — the architecture's hexagonal rule says domain
   modules are pure (no I/O); the streaming generator must own a
   `LlamaServerClient` (E4B for describe + MoE for forward) so it
   intrinsically does I/O. Putting it in the API layer keeps the
   rule honest. The pure pieces (chunk-format helper, content-block
   builder, describe-one-image) all live in `domain/`.

3. **Preprocess errors mid-stream emit an embedded error frame, then
   `[DONE]`** — mirrors the architecture §API contract for mid-stream
   upstream failures. The non-streaming path returns 502 with an OpenAI
   envelope (Story 9.9 AC-6); the streaming path can't change the HTTP
   status mid-stream so it embeds the error in `delta.content` with a
   `finish_reason: "error"` marker, then closes with `[DONE]`. MoE is
   NOT called — same "no graceful degrade" rule as Story 9.9.

4. **Status chunks include the visible `model` from the request
   (`gemma4-auto`), NOT the upstream model name** — clients render
   `model` in some debug UIs; using the alias keeps the user-facing
   surface consistent with what they asked for. The actual MoE chunks
   carry the upstream's real model name (e.g., `gemma-4-26B-A4B-it-uncensored-Q4_K_M.gguf`)
   because they pass through verbatim from llama-server, untouched.

5. **`describe_one_image` promoted to public, but `preprocess_images`
   retained** — the streaming-with-images path drives its own per-image
   loop so it can interleave status chunks; the non-streaming and
   text-only-streaming paths still use the batch `preprocess_images`
   API (no behavioural change). This is what Option A from the story
   brief specifies.

6. **`build_description_block` extracted as a public helper** — both
   the streaming generator and `preprocess_images` use it so the
   `[Image description: ...]` / `[Image: (description unavailable)]`
   marker formatting lives in exactly one place. Pure function.

7. **Status text is plain `delta.content`, NOT a custom `event:` field
   or non-standard top-level key** — per the story brief and ADR-012
   the format is mandated to be standard OpenAI chunk shape so vanilla
   clients (Open WebUI, Continue, cURL) render it as italic markdown
   without special-casing. The test `test_status_chunk_format_matches_adr_012_exactly`
   asserts `"event" not in status` and `"type" not in status` to lock
   this down.

8. **Status text is NOT logged** — log lines from `_handle_auto` and
   `_sse_stream_with_status` carry only `multimodal_blocks={images:N}`,
   `preprocess_latency_ms`, `total_upstream_calls`, `upstream`,
   `upstream_url`, `upstream_status`, `chunks_forwarded`, `duration_ms`.
   The visible status text appears in user-visible content (the
   client's transcript) but per architecture §Logging it stays out of
   logs — no point logging plaintext we know our own format generates.

## Coordination notes

- No conflict with prior Sprint 2 stories — this story extends
  `_handle_auto` with a new branch BEFORE the pre-9.10 path; the
  pre-9.10 path is unchanged for non-streaming and text-only-streaming
  cases. The new generator reuses `_sse_stream` for MoE forwarding so
  keepalive + mid-stream error logic is identical to passthrough.
- `domain/router.py`, `adapters/llama_server_client.py`,
  `domain/content_inspector.py`, `api/health.py`, `api/models.py` all
  untouched.
- The new public `describe_one_image` is what Story 9.13's tool-call
  agent loop will reuse for its `analyze_image` execution path
  (re-querying E4B on the same image bytes the user originally sent);
  surface stays stable across stories.

## Boundaries respected

- DID NOT add status events to non-multimodal paths (text-only `gemma4-auto`
  stream, `gemma4-26b-text` passthrough, `gemma4-e4b-vision` passthrough);
  AC-3 + the test for `gemma4-26b-text` from Story 9.8 still pass unchanged
- DID NOT add status events to non-streaming responses (no place to put
  them; AC-4 asserts the response is plain JSON)
- DID NOT change user-visible behaviour for `gemma4-26b-text` or
  `gemma4-e4b-vision` passthrough (passthrough tests from 9.8 unchanged
  and green)
- DID NOT log status text (architecture §Logging — content stays out
  of logs)
- DID NOT touch the format — exact ADR-012 shape: italic underscores
  with bracket + leading/trailing newlines; clients render as italic
  markdown via plain `delta.content`, not via a custom event channel
- DID NOT touch ct-ai-01 production state beyond the temporary uvicorn
  smoke (killed; `/tmp/gemma-hybrid-proxy*` removed; both
  `llama-server*` services verified `active` post-smoke)
- DID NOT add new prod dependencies (no new packages in `requirements.txt`)

## Next story

9.11 (Ansible role + ct-dev-test → ct-ai-01 deploy + Open WebUI repoint)
is the Sprint 2 EXIT GATE. The proxy code is now feature-complete for
Sprint 2 (passthrough, modality cascade, status events). 9.11 wraps it
in an Ansible role, deploys via the test-container path
(ct-dev-test 192.168.50.152 → ct-ai-01 192.168.50.160), repoints Open
WebUI's OpenAI base URL at the proxy, and runs the Playwright MCP
browser smoke test that verifies the visible italic status during the
multimodal preprocessing window — which is what this story made
possible.
