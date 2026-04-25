# Story 9.14 — Orchestrator agent loop (intercept → execute → resume → stream) — Evidence

- **Sprint:** 3
- **Owner:** claude-coder
- **Date:** 2026-04-25
- **Depends on:** 9.12 (analyze_image schema + augment_request_with_tools), 9.13 (ToolCallAccumulator)
- **Source spec:** `_bmad-output/planning-artifacts/hybrid-gemma-serving-epics.md` §Story 9.14; architecture ADR-004 (single-threaded master loop), ADR-012 (stream-only, status events), §Implementation Patterns → Error handling rules (max iterations = 5; tool execution failure injects tool message, never crashes the request)

---

## Implementation summary

New pure-async orchestration module
`homelab-infra/ansible/roles/gemma-hybrid-proxy/files/src/gemma_hybrid_proxy/domain/agent_loop.py`
(351 lines raw / 259 code lines — see "Deviations" §1) plus a wire-up
in `api/chat_completions.py` that:

1. Builds an `image_registry: dict[str, dict]` from the inspection's
   image blocks BEFORE the multimodal preprocessor replaces them with
   text descriptions (so `analyze_image` calls can re-fetch the
   original payload).
2. Calls `assign_image_ids` to label each image block with a stable
   `[Image image-N:]` text marker.
3. Calls the existing `preprocess_images` to swap the labelled
   `image_url` blocks for `[Image description: ...]` text blocks.
4. Calls `augment_request_with_tools` to inject the `analyze_image`
   tool definition into the outgoing MoE request (client tools win
   on overlap; `tool_choice` defaults to `"auto"`).
5. Hands the augmented request to `AgentLoopRunner` for the iteration
   loop (streaming or non-streaming per the client's `stream` flag).

**`AgentLoopRunner` public surface:**

| Symbol | Purpose |
|---|---|
| `AgentLoopRunner` (dataclass) | Per-request driver; takes injected MoE+E4B clients, image registry, request body, request id, model label, optional `e4b_upstream_model`, and `max_iterations` (default `MAX_TOOL_ITERATIONS = 5`). |
| `AgentLoopRunner.run_streaming() -> AsyncIterator[dict[str, str]]` | Drives the loop, yielding `{"data": <json>}` chunks for `EventSourceResponse`. Plain `delta.content` chunks pass straight through; `delta.tool_calls` chunks are buffered through `ToolCallAccumulator` until `finish_reason` lands. On `tool_calls`: emit a status, execute against E4B, append tool messages, re-issue MoE. On natural finish: emit `[DONE]`. On iteration cap: emit synthetic content + final-stop chunk + `[DONE]`. |
| `AgentLoopRunner.run_non_streaming() -> dict` | Same loop in non-streaming mode; returns the final OpenAI completion dict (with the max-iter notice spliced into `choices[0].message.content` if the cap fires). |
| `build_image_registry(inspection_image_blocks, *, starting_index=1)` | Pure helper — maps each `image-N` handle (matching `assign_image_ids` global numbering) to its ORIGINAL `image_url` payload. |

**Status events emitted between iterations (ADR-012 form):**

| Event text | When |
|---|---|
| `\n_[calling analyze_image: <question[:60]>...]_\n` | Before each tool execution (per tool call within an iteration). |
| `\n_[continuing reasoning...]_\n` | After all tool calls in an iteration finish, before the next MoE stream opens. |
| `\n\n_[Maximum tool-call iterations reached. Returning current best answer.]_\n\n` | Once the iteration cap fires (only emitted on the cap-hit path). |

The pre-existing Story 9.10 status events (`\n_[describing image N of M...]_\n`, `\n_[reasoning...]_\n`) continue to fire in the streaming-with-status branch; the new 9.14 events compose cleanly between them.

**Error handling per architecture §Implementation Patterns:**

- **Pydantic args validation failure** (e.g., model emits `analyze_image` with missing `question` field) → tool message body becomes `error: invalid arguments: <pydantic_errors>`; loop continues; model gets to retry or summarise. Logged at `warning` level under `agent_loop.tool_args_invalid`.
- **E4B failure during tool execution** (timeout, 5xx, connection refused) → tool message body becomes `error: image analysis failed: <reason>`; loop continues. Logged under `agent_loop.tool_exec_failed`.
- **Unknown image_id** (model hallucinates `image-99` when only `image-1` exists) → tool message body becomes `error: unknown image_id 'image-99'`; loop continues. No log (model error, not infra error).
- **Unknown tool name** (e.g., `transcribe_audio`, deferred per ADR-008) → tool message body becomes `error: unknown tool 'transcribe_audio'`; loop continues. No log.
- **Catch-all `Exception`** → `error: image analysis failed: <repr>`. Logged under `agent_loop.tool_exec_unexpected`. Defends the loop against bugs in `describe_one_image` we haven't anticipated.
- **Iteration cap (5)** → Once the 6th attempt would otherwise begin, the runner emits a synthetic content chunk + `finish_reason: "stop"` chunk + `[DONE]`, logged at `warning` level under `agent_loop.max_iterations_reached`.

---

## Files touched

- **NEW:** `src/gemma_hybrid_proxy/domain/agent_loop.py` (351 raw / 259 code lines)
- **MODIFIED:** `src/gemma_hybrid_proxy/api/chat_completions.py` (added `AgentLoopRunner` + `build_image_registry` + `augment_request_with_tools` + `assign_image_ids` imports; rewired `_handle_auto` to: build registry → assign image ids → preprocess → augment → run loop; rewired `_sse_stream_with_status` similarly with the runner driving the post-preprocess MoE phase)
- **NEW:** `tests/unit/test_agent_loop.py` (21 unit tests)
- **MODIFIED:** `tests/unit/test_chat_completions_auto.py` (3 pre-existing tests updated for the new image-id label shape: rewritten messages now contain `[Image image-N:]` text blocks before each `[Image description: ...]` block — this is intended Story 9.14 behaviour, not a regression)

No production state touched (live smoke ran on a temporary uvicorn on
`127.0.0.1:18005`, torn down after capture). No Ansible role / systemd
unit / dependency changes. No new prod dependencies.

---

## Acceptance criteria results

| AC | Result | Evidence |
|---|---|---|
| AC-1: text-only `gemma4-auto` does NOT trigger a tool loop iteration | PASS | `test_auto_text_only_no_tool_loop_iteration_regression` (FastAPI surface) + `test_runner_streaming_passes_through_text_chunks_when_no_tool_call` (runner direct). Live smoke (probe 1 below): 1 MoE call, 1.26s, no E4B touched, response carries `analyze_image` tool registration but model didn't use it. |
| AC-2: image preprocess + augmented request to MoE; if no tool call, response streams (1 iteration) | PASS | `test_auto_streaming_with_image_no_tool_call_passes_through` — exactly 1 E4B (preprocess) + 1 MoE (no tool loop); status events for describe + reasoning fire but NOT calling/continuing. |
| AC-3: MoE emits one `analyze_image` tool call → executed against E4B → result injected → MoE re-queried → final response streams | PASS | `test_runner_streaming_executes_tool_call_and_resumes` (runner) + `test_auto_streaming_with_image_then_tool_call_full_loop` (full FastAPI surface, 2 MoE calls + 2 E4B calls). **Live smoke (probe 2): real ct-ai-01 model emitted `tool_calls` finish_reason; tool was executed; second iteration ran to completion; total wall 85.97s.** |
| AC-4: Iteration cap — synthetic loop bounded at MAX_TOOL_ITERATIONS with synthetic close | PASS | `test_runner_streaming_iteration_cap_emits_synthetic_close` — set `max_iterations=3`, model keeps emitting tool_calls; loop exits at 3 with `_[Maximum tool-call iterations reached. Returning current best answer.]_` content + `finish_reason: "stop"` + `[DONE]`. |
| AC-5: Tool args validation failure → tool error injected; no crash; loop continues | PASS | `test_runner_tool_args_validation_failure_injects_error_message` — model emits `analyze_image({"image_id": "image-1"})` (missing `question`); tool message body is `error: invalid arguments: ...`; second MoE iteration receives the error and emits a graceful summary; E4B never touched. |
| AC-6: E4B raises during tool execution → tool error injected; no crash; loop continues | PASS | `test_runner_e4b_failure_during_tool_exec_injects_error_message` (E4B returns 503) + `test_runner_handles_upstream_error_subclass` (raw httpx.ConnectError raised mid-describe). Both surface as `error: image analysis failed: ...` tool messages; second MoE iteration runs cleanly. |
| AC-7: Status events visible between iterations | PASS | `test_runner_streaming_executes_tool_call_and_resumes` parses the SSE body and asserts both `calling analyze_image` and `continuing reasoning` status frames are present. Live smoke (probe 2): all 4 status events captured (`describing image 1 of 1...` → `reasoning...` → `calling analyze_image: what color is the pixel?...` → `continuing reasoning...`). |
| AC-8: All existing tests still pass | PASS | 80 prior + 21 new = 101 pytest pass; 0 regressions. (3 pre-existing tests in `test_chat_completions_auto.py` had to be updated to reflect the new message shape — see "Files touched" — but this is intended 9.14 behaviour, not a regression.) |
| AC-9: ruff / mypy / pytest all green | PASS | See command transcript below. |
| AC-10: Live smoke against ct-ai-01 on port 18005 (no production disturbance) | PASS | See "Live smoke" §below — agent loop fired with real MoE emitting `tool_calls`, real E4B executing the analyze_image follow-up, second MoE iteration consuming the tool result and producing further content; production `gemma-hybrid-proxy.service` on `:8000` untouched. |

---

## Test count + lint/mypy/pytest transcript

```text
$ .venv/bin/ruff check .
All checks passed!

$ .venv/bin/mypy src/
Success: no issues found in 20 source files

$ .venv/bin/pytest -q tests/
........................................................................ [ 71%]
.............................                                            [100%]
101 passed in 0.30s
```

- **New tests (Story 9.14):** 21 in `tests/unit/test_agent_loop.py`
- **Modified tests:** 3 in `tests/unit/test_chat_completions_auto.py` (image-id label shape)
- **Total tests now:** 101 (80 prior baseline + 21 new)
- **Regressions:** 0

---

## Live smoke (AC-10) — real ct-ai-01

Approach mirrors Stories 9.8–9.11: tarball of `src/`, `tests/`,
`pyproject.toml`, `requirements*.txt` pushed to ct-ai-01 (CT 160) via
`pct push`, extracted to `/tmp/ghp-9.14`, fresh venv built with
`python3 -m venv`, package installed editable, uvicorn launched on
`127.0.0.1:18005` against in-container loopback E4B (`:8080`) and MoE
(`:8081`). Production `gemma-hybrid-proxy.service` (`:8000`),
`llama-server.service` (`:8080`), `llama-server-26b.service`
(`:8081`) all remained `active` throughout (verified before AND
after); smoke env torn down on exit (`/tmp/ghp-9.14*` removed; port
18005 released).

### Probe 0: `/health`

```
$ curl -sf http://127.0.0.1:18005/health
{"status":"ok","upstreams":{"e4b":"ok","moe":"ok"}}
```

### Probe 1: text-only `gemma4-auto`, non-streaming (AC-1 regression)

```json
{
  "model": "gemma4-auto",
  "stream": false,
  "messages": [{"role": "user", "content": "Reply with only the word: pong"}],
  "max_tokens": 10
}
```

Result: `HTTP=200 total=1.263407s ttfb=1.263355s`. Response body shows
1 MoE call only; no E4B contact; model deliberated in
`reasoning_content` then hit `finish_reason: length`. Importantly the
proxy's structured log shows `agent_loop=True total_upstream_calls=1`
— the runner ran but did NOT do a tool-call iteration.

### Probe 2: streaming `gemma4-auto` + 1×1 PNG + tool-call-provoking prompt (AC-3 + AC-7 live)

```json
{
  "model": "gemma4-auto",
  "stream": true,
  "messages": [{"role": "user", "content": [
    {"type": "text", "text": "You MUST call the analyze_image tool to inspect this image with the question: what color is the pixel? Do not answer directly; use the tool."},
    {"type": "image_url", "image_url": {"url": "data:image/png;base64,iVBOR...AABJRU5ErkJggg=="}}
  ]}],
  "max_tokens": 600
}
```

Result: `HTTP=200 total=85.972221s ttfb=0.006377s`.

Captured status events (in order, with their `created` Unix timestamps from the SSE frames):

| t (relative) | Event | Source frame timestamp |
|---|---|---|
| 0.006s | `\n_[describing image 1 of 1...]_\n` (Story 9.10 — preprocess) | `created: 1777120426` |
| 26s | `\n_[reasoning...]_\n` (Story 9.10 — handoff to MoE) | `created: 1777120452` |
| 34s | `\n_[calling analyze_image: what color is the pixel?...]_\n` (**Story 9.14 — first tool call detected**) | `created: 1777120460` |
| 60s | `\n_[continuing reasoning...]_\n` (**Story 9.14 — tool exec done, next iteration starting**) | `created: 1777120486` |
| 86s | `data: [DONE]` | end of second MoE iteration |

Captured `finish_reason` values: `tool_calls` (first MoE iteration — this is the agent loop firing) AND `length` (second MoE iteration — model ran out of token budget while writing the final answer).

Captured proxy log lines (filtered for the request):

```
12:34:12 [info] chat_completions.auto.forwarding agent_loop=True ... preprocess_latency_ms=25882.4 stream=True total_upstream_calls=2
12:34:46 [info] agent_loop.tool_iteration agent_loop=True iteration=0 tool_calls=1 ...
12:35:12 [info] agent_loop.iteration_done agent_loop=True finish_reason=length iteration=1 ...
12:35:12 [info] chat_completions.auto.completed agent_loop=True duration_ms=85970.12 stream=True
```

### Timing breakdown (AC-10)

| Event | Wall time | Source |
|---|---|---|
| Request sent | t=0.000s | client |
| **First status chunk (`describing image 1 of 1...`) received** | **t=0.006s** | curl `time_starttransfer` |
| Preprocess (E4B describe) finished, reasoning status emitted | t≈26s | created delta 1777120426 → 1777120452 |
| **First MoE iteration completed with `finish_reason: "tool_calls"`** | **t≈34s** | calling status emitted at created 1777120460 |
| **Tool execution (E4B re-queried with `analyze_image`)** | **t≈60s** | continuing status emitted at created 1777120486 (delta 26s) |
| **Second MoE iteration ran 600 predicted tokens** | t≈60s → 86s | predicted_per_second 23.75 tok/s × 600 ≈ 25.3s |
| Stream end (`[DONE]`) | t=85.97s | curl `time_total` |

Total upstream call breakdown:

- **E4B**: 2 calls (1 preprocess describe + 1 tool exec re-describe, both ~26s)
- **MoE**: 2 calls (1 reasoning that emitted `tool_calls`, 1 follow-up that consumed the tool result)
- **Iterations**: 1 tool-call iteration + 1 natural close iteration (total 2 cycles through the agent loop)

### Cleanup confirmation

```
$ ssh root@pve3 "pct exec 160 -- bash -c '
    ss -tnlp | grep 18005 || echo port_18005_free ;
    systemctl is-active gemma-hybrid-proxy.service llama-server.service llama-server-26b.service ;
    ls /tmp/ghp* 2>&1 || echo cleanup_ok'"
port_18005_free
active
active
active
cleanup_ok
```

Production state preserved: `gemma-hybrid-proxy.service` on `:8000`,
`llama-server.service` on `:8080`, `llama-server-26b.service` on `:8081`
all `active` before and after the smoke. Smoke env removed.

---

## Design decisions / deviations

1. **`agent_loop.py` is 259 code lines, over the brief's "≤180 LOC" target (and over the architecture's 150 LOC `domain/` ceiling).** The streaming generator + non-streaming path + tool execution + 4 module-level helpers (`_safe_parse_chunk`, `_should_forward_chunk`, `_extract_data_payloads`, `_inject_max_iter`) + 2 message-shape helpers (`_assistant_tool_call_msg`, `_tool_msg`, `_call_summary`) pushed past 180. Pulled non-essential helpers out of the class to module level to bring the class itself down; further compression would either inline the streaming/non-streaming paths into `chat_completions.py` (breaks the hexagonal boundary — the runner needs to be testable without FastAPI) or drop the non-streaming path (brief explicitly requires both). Trade-off: code stays clear and testable, file is over the soft target. Same situation as `delta_accumulator.py` (Story 9.13: 217 raw / 116 code) and `multimodal_preprocessor.py` (Story 9.9: 191 LOC vs 120 hint) — pattern matched.

2. **`AgentLoopRunner` is a `@dataclass`, not a hand-rolled `__init__`.** Eight injected dependencies + sane defaults read more clearly as fields than as constructor parameters. Mypy strict on `domain/*` accepts the dataclass form. `field(default_factory=lambda: _log.bind(...))` lets each instance get its own bound logger without sharing one across requests.

3. **Image registry is built BEFORE preprocessing in BOTH `_handle_auto` branches** (streaming-with-status and the non-streaming/text-only path). The brief asked for "per-request, no global state" — the registry is a local `dict` in the API surface, passed once into the runner constructor, and dies with the request. No singleton, no module-level mutation.

4. **`assign_image_ids` is called BEFORE the existing `preprocess_images`.** The architecture's intended composition (per `assign_image_ids` docstring): walk the messages, insert `[Image image-N:]` text blocks before each `image_url`, then let the preprocessor swap each `image_url` for `[Image description: ...]`. The final shape is `[Image image-N:] [Image description: <E4B output>]`. To make the preprocessor's coordinates correct after the insertion, `_handle_auto` re-runs `inspect()` on the labelled messages before calling `preprocess_images`. The streaming-with-status branch does the same (using `relabelled_inspection` instead of the original `inspection`).

5. **Tool calls are buffered through `ToolCallAccumulator` even when only one fragment arrives.** The accumulator handles the multi-chunk case correctly and the single-chunk case as a no-op; the runner doesn't need a fast-path. A delta chunk that ONLY carries `tool_calls` (no `delta.content`) is suppressed from the client-facing stream — only the assistant's accumulated text content (any pre-tool-call preamble like "Let me check…") is forwarded. Once `finish_reason == "tool_calls"` lands, the runner re-emits a synthetic assistant message containing the reassembled `tool_calls` array as the next-iteration's history entry; the client never sees the raw fragment chunks. This matches the architecture's "clean delta emission" goal (R4 mitigation, Open WebUI #23066).

6. **Existing 3 tests in `test_chat_completions_auto.py` updated, not deleted.** They asserted the pre-9.14 message shape (text + description). Story 9.14 changes the shape to (text + image-N label + description) — a deliberate and architecture-mandated change. The updated assertions still verify the same underlying behaviour (correct image-handling, description injected, fallback on empty E4B, 2 sequential E4B calls for 2 images) but now also check the image-N label landed and the `analyze_image` tool was registered on the MoE call. This is the same pattern Story 9.10 used when it added status events (which changed the SSE frame stream shape).

7. **Iteration cap fires AFTER the 5th tool-call iteration completes**, not before the 6th starts. Because `for iteration in range(self.max_iterations)` runs `iteration ∈ {0, 1, 2, 3, 4}`, the loop body runs 5 times max. If the 5th iteration's `finish_reason` is still `tool_calls`, control falls through to the synthetic-close block. Architecture says "on 6th iteration, force `finish_reason: stop`" — this implementation forces it after the 5th iteration and BEFORE the 6th would start, which is functionally equivalent.

8. **Non-streaming path is tested via the runner directly, not via FastAPI surface.** The FastAPI integration tests cover the streaming path end-to-end (`test_auto_streaming_with_image_then_tool_call_full_loop`). For the non-streaming path, a dedicated runner-level test (`test_runner_non_streaming_executes_tool_and_returns_assembled_response`) verifies the loop behaviour. The `_run_agent_loop` API-layer wrapper for non-streaming is exercised by `test_auto_text_only_no_tool_loop_iteration_regression` and `test_auto_request_body_includes_analyze_image_tool` (both non-streaming, both fall through to `run_non_streaming` with finish_reason=stop on the first iteration).

---

## Boundaries respected

- Did NOT modify `domain/tool_definitions.py` (Story 9.12 territory).
- Did NOT modify `domain/delta_accumulator.py` (Story 9.13 territory).
- Did NOT add LiteLLM (that's Story 9.16).
- Did NOT add `transcribe_audio` (ADR-008 deferred to Sprint 4).
- Did NOT touch the production `gemma-hybrid-proxy.service` on `:8000`. The live smoke ran on `:18005` and was torn down.
- Did NOT introduce new prod dependencies (uses existing httpx, pydantic, structlog, sse-starlette).
- Image registry is per-request — built in `_handle_auto`, lives only in the runner constructor, dies with the request. No global state.
- `agent_loop.py` is pure async — no `httpx` import, no env reads, no file I/O. The `LlamaServerClient` instances are passed in by `chat_completions.py`, which owns settings and lifecycle.

---

## Sprint status update

- 9.14 status: `pending` → `completed`
- owner: `unassigned` → `claude-coder`
- completion_date: `2026-04-25`
- evidence: this file (`9-14-agent-loop-evidence.md`)
- sprint_3 stories_completed: `2` → `3`
- sprint_3 notes: brief Story 9.14 summary appended

Sprint 3 may proceed to Story 9.15 (synthetic prompt test suite that
should provoke `analyze_image` invocations against the live `:8000`
proxy on ct-dev-test).
