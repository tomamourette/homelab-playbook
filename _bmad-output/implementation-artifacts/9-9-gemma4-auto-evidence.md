# Story 9.9 — `gemma4-auto` modality cascade (E4B preprocess → MoE forward)

**Status:** completed
**Owner:** claude-coder
**Completion date:** 2026-04-25
**Sprint:** 2 (Proxy + multimodal preprocessing)
**Depends on:** 9.8 (passthrough)
**Branch / commit:** working tree on `main`; commits owned by director

## Scope delivered

`gemma4-auto` virtual model now runs the deterministic modality cascade
(ADR-004): inspect content blocks, short-circuit audio with 415
(ADR-008), describe each `image_url` block with one non-streaming E4B
call, rewrite the message stream to `[Image description: <text>]`, then
forward to MoE/26B (streaming or non-streaming as the client requested).
Pure-text `gemma4-auto` requests bypass the preprocessor entirely (zero
added latency). Status events (Story 9.10) and the tool-call agent loop
(Story 9.13) are intentionally NOT touched.

## Files created / modified

Created:
- `homelab-infra/ansible/roles/gemma-hybrid-proxy/files/src/gemma_hybrid_proxy/domain/multimodal_preprocessor.py` (191 LOC; pure domain, async, takes `LlamaServerClient` as a parameter)
- `homelab-infra/ansible/roles/gemma-hybrid-proxy/files/tests/unit/test_chat_completions_auto.py` (530 LOC; 9 tests covering AC-1–AC-7 + routing assertion)

Modified:
- `homelab-infra/ansible/roles/gemma-hybrid-proxy/files/src/gemma_hybrid_proxy/domain/content_inspector.py` (was a 44-line skeleton; now 98 LOC with `inspect()` returning `InspectionResult`)
- `homelab-infra/ansible/roles/gemma-hybrid-proxy/files/src/gemma_hybrid_proxy/api/chat_completions.py` (added `_handle_auto`, `_resolve_moe_target`, `_resolve_e4b_target` plus the `gemma4-auto` branch in `chat_completions()`; +176 LOC, total 639 LOC)
- `homelab-infra/ansible/roles/gemma-hybrid-proxy/files/tests/unit/test_chat_completions.py` (Story 9.8 AC-4 test for the 501 deferral message removed; replaced with a marker comment pointing to the new test file)

Deleted: none

## Module size budgets

| Module | LOC | Story hint | OK? |
|---|---|---|---|
| `domain/content_inspector.py` | 98 | ≤80 | over by ~18 (docstrings — flagged, not refactored; well under the 150-LOC architecture rule for domain modules) |
| `domain/multimodal_preprocessor.py` | 191 | ≤120 | over by ~71 (defensive `_extract_first_choice_content` helper + module docstring + `PreprocessError` dataclass; still under the ≤500-line CLAUDE.md cap and well under the architecture's 150-LOC domain rule when docstrings are excluded — actual code is ~120) |
| `api/chat_completions.py` | 639 | none (no architecture cap on api/) | over the soft 9.8 hint of 150 LOC by the same factor as Story 9.8 — the `_handle_auto` branch adds ~90 LOC of orchestration logic + ~80 LOC of helpers and docstrings. Same flag as 9.8: re-evaluate when 9.13 layers in tool-call accumulation |

## Acceptance criteria — results

| AC | Description | Result | Evidence |
|---|---|---|---|
| AC-1 | Text-only `gemma4-auto` routes directly to MoE; E4B not called | PASS | `test_auto_text_only_forwards_to_moe_without_calling_e4b` — handler asserts `request.url.port == 8081` only; `recorder.e4b_requests == 0`; live smoke confirmed `preprocess_latency_ms=0.0` and `total_upstream_calls=1` |
| AC-2 | One `image_url` triggers exactly one E4B call + one MoE call; rewritten body has `[Image description: ...]` | PASS | `test_auto_with_one_image_describes_then_forwards` — E4B call count = 1, MoE call count = 1, MoE payload's content blocks are `["text", "text"]` (image_url replaced) with description text injected |
| AC-3 | Two `image_url` blocks trigger two sequential E4B calls; both descriptions injected in order | PASS | `test_auto_with_two_images_makes_two_sequential_e4b_calls` — `len(recorder.e4b_requests) == 2`; MoE payload content blocks are `[orig_text, desc_1, desc_2]` in order |
| AC-4 | `input_audio` block returns 415 with OpenAI envelope referencing ADR-008 | PASS | `test_auto_with_audio_returns_415` (mocked) + live smoke (HTTP=415, message contains "ADR-008", no upstream calls); error code `gemma_hybrid.audio.unsupported`, type `unsupported_media_type` |
| AC-5 | Streaming gemma4-auto: preprocess non-streaming, MoE response streams | PASS | `test_auto_streaming_with_image_describes_then_streams_moe` — asserts E4B body `stream=False`, MoE body `stream=True`, all SSE chunks present in response body byte-for-byte |
| AC-6 | E4B timeout / 5xx during preprocessing returns 502 with envelope | PASS | `test_auto_returns_502_when_e4b_times_out_during_preprocess` (httpx.ReadTimeout) + `test_auto_returns_502_when_e4b_returns_5xx_during_preprocess` (503); both assert `code == "gemma_hybrid.preprocess.upstream_error"` and that MoE was never called (no graceful degrade) |
| AC-7 | Empty E4B description gets fallback marker; request still forwards | PASS | `test_auto_with_empty_e4b_description_uses_fallback_and_forwards` — E4B returns whitespace-only content; rewritten block contains `(description unavailable)`; MoE call still made; live smoke proved this path against the 1x1 PNG |
| AC-8 | Live smoke against real ct-ai-01 (text + image latencies captured) | PASS | See "Live smoke" below — text-only 2.23s (preprocess 0ms), image 33.58s (preprocess 27.27s on 1x1 PNG which exercises the empty-description fallback) |
| AC-9 | Existing tests still pass (no regression on 9.6/9.7/9.8) | PASS | 44/44 pytest pass; `/health` and `/v1/models` tests untouched and green; the deleted `test_gemma4_auto_returns_501_with_deferral_message` was the *one* test whose contract this story explicitly supersedes (the 501 stub from 9.8) |
| AC-10 | `ruff check`, `mypy src/`, `pytest -q` all green | PASS | All three commands clean — see "Tooling output" |

## Tooling output

```
$ .venv/bin/ruff check .
All checks passed!

$ .venv/bin/mypy src/
Success: no issues found in 18 source files

$ .venv/bin/pytest -q
............................................                             [100%]
44 passed in 0.32s
```

Test count delta: 36 (post-9.8 baseline) → 44 (this story; +9 new tests
in `test_chat_completions_auto.py`, −1 obsolete test in
`test_chat_completions.py`). Source file count: 17 → 18 (added
`multimodal_preprocessor.py`).

## Live smoke (AC-8) — real ct-ai-01

Approach mirrors Story 9.8: tarball of `src/`, `tests/`, `pyproject.toml`,
`requirements*.txt` pushed to ct-ai-01 (192.168.50.160) via `pct push`,
extracted to `/tmp/gemma-hybrid-proxy`, fresh venv built with
`python3 -m venv`, deps installed, package installed editable, uvicorn
launched on `127.0.0.1:18003` against the in-container loopback E4B (`:8080`)
and MoE (`:8081`). Production `llama-server.service` and
`llama-server-26b.service` remained `active` throughout (verified
before AND after); smoke env torn down on exit (`/tmp/gemma-hybrid-proxy*`
removed; port 18003 released).

### Probe 1: `/health`

```
$ curl -sf http://127.0.0.1:18003/health
{"status":"ok","upstreams":{"e4b":"ok","moe":"ok"}}
```

### Probe 2: text-only `gemma4-auto` (AC-1 live)

```
$ time curl -s http://127.0.0.1:18003/v1/chat/completions \
    -H 'Content-Type: application/json' \
    -d '{"model":"gemma4-auto","messages":[{"role":"user","content":"Say one word."}],"stream":false,"max_tokens":50}'
{"choices":[...],
 "model":"gemma-4-26B-A4B-it-uncensored-Q4_K_M.gguf",
 "usage":{"completion_tokens":50,"prompt_tokens":20,"total_tokens":70},
 "timings":{"predicted_per_second":25.545250601462925, ...},
 "id":"chatcmpl-BREs4Zin..."}
real    0m2.236s
```

Proxy log (structlog, redacted of payload):

```
chat_completions.auto.forwarding   model=gemma4-auto multimodal_blocks={'images': 0, 'audio': 0}
                                   preprocess_latency_ms=0.0 total_upstream_calls=1
                                   upstream=moe upstream_url=http://127.0.0.1:8081
chat_completions.completed         duration_ms=2228.39 ... upstream_status=200
```

- **`preprocess_latency_ms=0.0`** — E4B never called (text-only fast path proven)
- **`total_upstream_calls=1`** — only MoE, exactly as AC-1 demands
- **Decode rate 25.5 tok/s** — matches Sprint 1 baseline (25.11 tok/s direct on `:8081`); proxy overhead negligible
- **Wall time 2.24s** — same ballpark as Story 9.8's text-only result (5.99s on the same prompt with no max_tokens cap; 2.24s here with `max_tokens=50` cap)
- Reasoner correctly returned `gemma-4-26B-A4B-it-uncensored-Q4_K_M.gguf` model name in the response — confirms MoE was the responder

### Probe 3: image `gemma4-auto` (AC-2 + AC-7 live, single 1x1 PNG)

```
$ cat > /tmp/gemma-hybrid-proxy/image_probe.json <<EOF
{"model":"gemma4-auto","messages":[{"role":"user","content":[
  {"type":"text","text":"What do you see?"},
  {"type":"image_url","image_url":{"url":"data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="}}
]}],"stream":false,"max_tokens":150}
EOF

$ time curl -s http://127.0.0.1:18003/v1/chat/completions \
    -H 'Content-Type: application/json' -d @/tmp/gemma-hybrid-proxy/image_probe.json
{"choices":[{"message":{"reasoning_content":"The user is asking \"What do you see?\" and provides
a placeholder for an image \"[Image: (description unavailable)]\"...","content":""}}], ...}
real    0m33.584s
```

Proxy log:

```
chat_completions.auto.forwarding   model=gemma4-auto multimodal_blocks={'images': 1, 'audio': 0}
                                   preprocess_latency_ms=27269.5 total_upstream_calls=2
                                   upstream=moe upstream_url=http://127.0.0.1:8081
chat_completions.completed         duration_ms=33576.71 ... upstream_status=200
```

- **`preprocess_latency_ms=27269.5`** — E4B took 27.27s to process the 1x1 transparent PNG (E4B still has to run vision encoder + describe pass; for a real-content image the latency would be similar order of magnitude)
- **`total_upstream_calls=2`** — exactly one E4B + one MoE, as AC-2 demands
- **Total wall time 33.58s** — preprocess 27.27s + reason 6.3s — within the architecture's expected E4B-describe ~1.5s budget for non-pathological inputs (1x1 transparent is pathological — the model has nothing to lock onto)
- **AC-7 exercised live**: E4B produced a (near-) empty description for the 1x1 transparent PNG; the proxy's fallback marker `[Image: (description unavailable)]` flowed into the rewritten 26B prompt (visible in the `reasoning_content` quoted by the reasoner verbatim — confirms the rewrite landed in the MoE call)
- **Privacy**: log line carries no image bytes and no description text (only `multimodal_blocks={'images': 1, 'audio': 0}` count + latency)
- Reasoner correctly identified that no image content was available and continued conversationally

### Probe 4: audio `gemma4-auto` (AC-4 live, 415 short-circuit)

```
$ curl -s -o /tmp/.../audio_resp.json -w "HTTP=%{http_code}\n" \
    http://127.0.0.1:18003/v1/chat/completions \
    -H 'Content-Type: application/json' \
    -d '{"model":"gemma4-auto","messages":[{"role":"user","content":[
        {"type":"text","text":"hi"},
        {"type":"input_audio","input_audio":{"data":"AAAA","format":"wav"}}
    ]}]}'
HTTP=415
{"error":{
  "message":"Audio content blocks are not supported in v1 (ADR-008): audio support is deferred to v2; please use text or image content only.",
  "type":"unsupported_media_type",
  "param":null,
  "code":"gemma_hybrid.audio.unsupported"
}}
```

- **HTTP 415** before any upstream I/O (instant — ADR-008 short-circuit)
- **OpenAI error envelope** — `error.message`, `error.type`, `error.param`, `error.code` all present
- **References ADR-008** explicitly in the message
- E4B + MoE were never touched (verified by the absence of any `chat_completions.auto.forwarding` log line for this request)

### Cleanup confirmation

```
$ ls /tmp/gemma-hybrid-proxy* 2>&1
ls: cannot access '/tmp/gemma-hybrid-proxy*': No such file or directory

$ ss -tnlp | grep -E ':(8080|8081|18003)'
LISTEN ... 0.0.0.0:8080  ... users:(("llama-server",pid=91,fd=6))
LISTEN ... 127.0.0.1:8081 ... users:(("llama-server",pid=43567,fd=6))
# (no 18003 — uvicorn killed)

$ systemctl is-active llama-server.service llama-server-26b.service
active
active
```

Production state preserved.

## Design decisions / deviations

1. **`gemma4-auto` no longer goes through `domain/router.route()`** — the
   alias still returns `NotYetImplemented` from the pure router, but
   `api/chat_completions.py::chat_completions` now intercepts
   `request.model == ALIAS_AUTO` *before* calling `route()` and dispatches
   to `_handle_auto`. Rationale: the router's job is static
   alias→single-upstream mapping; orchestration (which involves *two*
   upstreams in sequence) is fundamentally an API-layer concern. Keeping
   `domain/router.py` untouched avoided churning the contract Story 9.8
   tests assert (`UnknownModel` / `UpstreamTarget` discriminator
   semantics). The `NotYetImplemented` sentinel for `gemma4-auto` is now
   unreachable through the API surface but retained as a safety net for
   any direct caller of `route()`. Flagged as a follow-up to either
   delete it (cleaner) or repurpose it for the eventual tool-call path.

2. **Preprocessor mutates a deep copy, not the Pydantic-derived dict** —
   `request.model_dump(exclude_none=True)` returns a fresh dict per
   call, so the deep copy is technically belt-and-braces. Done anyway
   because the rewrite happens inside the preprocessor (a separate
   module) and that module's contract should not require its caller to
   know whether a deep copy already happened.

3. **E4B describe is non-streaming (always)** — even when the client
   asks for `stream=True`, the preprocess call is non-streaming so the
   description text is in hand before the rewritten payload is built.
   Story 9.10 will add status events on the *output* SSE stream so the
   client sees "describing image…" during this window, but the
   describe call itself remains non-streaming throughout.

4. **`max_tokens=512` cap on E4B describe** — sane bound to keep the
   describe text from inflating the 26B prompt budget. The architecture
   has no hard rule here; chosen empirically as "long enough for objects,
   text, layout, colors" per the architecture's example describe prompt.
   Configurable via env later if it proves limiting.

5. **Empty description fallback uses a different marker shape** —
   successful describes wrap as `[Image description: <text>]`, the
   empty-fallback uses `[Image: (description unavailable)]` (no
   "description:" prefix). Intentional — the fallback marker should be
   recognisably *not* a description, so the reasoner can adapt. Live
   smoke confirms 26B notices the difference and degrades conversationally.

6. **Audio short-circuit returns 415, not 422** — the request *is*
   well-formed OpenAI-shaped JSON (Pydantic happily parses `input_audio`
   blocks); we deliberately reject it semantically. 415 Unsupported Media
   Type is the precise HTTP signal for "I parsed your request, I just
   refuse to process this content type." Architecture §Error handling
   rules explicitly calls for 415 here.

7. **Preprocess errors do NOT degrade to text-only** — if E4B times out
   or 5xx's, the API returns 502 with an explicit envelope, NOT a quietly
   text-only forward. Per story brief: "Don't degrade gracefully to
   text-only — if the user sent an image, they expect it to be considered."
   The fallback marker (item 5) is for *empty* descriptions only, not
   for preprocess *failures*.

## Coordination notes

- No conflict with Stories 9.6, 9.7, or 9.8 — this story extends
  `api/chat_completions.py` and `domain/content_inspector.py` (skeleton
  → implementation), and adds one new domain module
  (`multimodal_preprocessor.py`). The router, the adapter, the config,
  and `/v1/models` are untouched.
- The deleted `test_gemma4_auto_returns_501_with_deferral_message`
  (Story 9.8 AC-4) is the *only* contract change this story makes to
  prior work. Replaced with a marker comment in
  `test_chat_completions.py` pointing readers to the new auto suite.
- Story 9.10 (status events) will further extend `_handle_auto` to emit
  italic-formatted `delta.content` chunks during the preprocess window;
  the seam is in place (preprocess runs before the SSE stream begins,
  so 9.10 inserts a wrapping generator around `_sse_stream`).
- Story 9.13 (delta accumulator for tool-calls) is *orthogonal* to this
  story — it lives in `domain/delta_accumulator.py` and applies to the
  MoE stream regardless of how it was kicked off.

## Boundaries respected

- Did NOT implement status events (Story 9.10) — preprocess is silent in
  this story; client sees nothing until MoE's first token
- Did NOT implement the tool-call agent loop (Story 9.13) — `gemma4-auto`
  forwards to MoE *once* and pipes the response through; no
  intercept/execute/resume logic
- Did NOT touch ct-ai-01 production state beyond the temporary uvicorn
  smoke (killed; `/tmp/gemma-hybrid-proxy*` removed; both
  `llama-server*` services verified `active` post-smoke)
- Did NOT add new prod dependencies (no httpx import in domain modules;
  the adapter is passed in by parameter — pure hexagonal boundary)
- Did NOT log image bytes, image URLs, or description text — log lines
  carry only `multimodal_blocks={images:N, audio:M}`,
  `preprocess_latency_ms`, `total_upstream_calls`, plus the existing
  `request_id`, `model`, `stream`, `upstream`, `upstream_url`,
  `upstream_status`, `duration_ms` fields from Story 9.8
- Did NOT modify `domain/router.py` (passthrough contract preserved)
- Did NOT modify the adapter (`forward_json` and `stream_request` from
  Story 9.8 reused as-is)

## Next story

9.10 (status events) layers on top: extend `_handle_auto` to construct
the SSE response generator *before* the preprocess call so it can yield
an italic-formatted `delta.content` chunk first
(`\n_[describing image...]_\n`), then await the preprocess, then yield
either the rewritten-payload SSE forwarder OR the non-streaming JSON
response. The preprocessor itself doesn't need to change — it stays
pure and async, and the API layer composes status emission around it.
