# Story 9.13 — `delta_accumulator` for streaming tool_calls — Evidence

- **Sprint:** 3
- **Owner:** claude-coder
- **Date:** 2026-04-25
- **Depends on:** 9.12 (analyze_image tool definitions — running in parallel; disjoint files)
- **Source spec:** `_bmad-output/planning-artifacts/hybrid-gemma-serving-epics.md` §Story 9.13; architecture §Integration Patterns (Tool-Call Orchestration Pattern); ADR-012; research doc §Integration Patterns (delta-accumulation pattern, OpenAI cookbook reference)

---

## Implementation summary

Fleshed out the Story 9.6 skeleton at
`homelab-infra/ansible/roles/gemma-hybrid-proxy/files/src/gemma_hybrid_proxy/domain/delta_accumulator.py`
into a pure-domain reassembler for OpenAI streaming `tool_calls` deltas.

**Public surface (per Story 9.13 spec):**

| Symbol | Kind | Purpose |
|---|---|---|
| `ToolCallAccumulator` | class | Per-request state machine; `dict[int, _PartialCall]` keyed by `tool_calls[*].index` |
| `ToolCallAccumulator.consume_chunk(chunk)` | method | Merge one `chat.completion.chunk` dict; collects pre-tool-call `delta.content` text and any `delta.tool_calls[*]` fragments |
| `ToolCallAccumulator.is_complete(chunk)` | method | True when `choices[0].finish_reason ∈ {tool_calls, stop, length}` |
| `ToolCallAccumulator.finalize()` | method | Returns `list[ToolCall]` (validated Pydantic) ordered by index, with concatenated `function.arguments` left as the original JSON string per OpenAI spec |
| `ToolCallAccumulator.accumulated_text()` | method | Returns the concatenated pre-tool-call assistant text (preserves "Let me check…"-style preambles) |
| `ToolCallAccumulator.finish_reason` | property | Last-seen terminal `finish_reason` (`None` until terminated) |
| `ToolCallAccumulator.reset()` | method | Clears all state for reuse on a subsequent turn |
| `parse_arguments(arguments_str)` | helper | Safe JSON-decode → `dict[str, Any]`; returns `{}` and emits a `structlog.warning` on parse failure or non-object payload (does not raise — Story 9.14 surfaces a clean tool-execution error to the client) |
| `accumulate_stream(chunks)` | helper | Async helper for Story 9.14: drains an `AsyncIterator[dict]`, returns `(tool_calls, text, finish_reason)` and stops at the first terminal chunk |

**Edge cases handled (all under unit test):**

- Single tool call across 3 chunks (id+name in one, args split across two)
- Two parallel tool calls (different `index` values) interleaved across chunks → finalised in index order
- Pre-tool-call assistant text content captured separately from tool calls
- Arguments arriving BEFORE name (some servers emit out of order) → still assembles
- Malformed JSON in args → `parse_arguments` returns `{}` + emits `delta_accumulator.parse_arguments_failed` warning
- Valid JSON but non-object payload (e.g. `"foo"`) → `{}` + `delta_accumulator.parse_arguments_non_object` warning
- `parse_arguments(None)` and `parse_arguments("")` → `{}` (no log)
- `finish_reason: "stop"` with no tool calls → empty list, just text
- `finish_reason: "length"` (truncated) → returns whatever was accumulated; caller can detect the truncation via the `finish_reason` field and the empty `parse_arguments` result on the partial JSON
- Chunk without `choices` (or empty choices) → no-op (defensive)
- Fragment without explicit `index` → falls into next free slot

**Design decisions / deviations from the brief:**

1. **Class renamed from `DeltaAccumulator` → `ToolCallAccumulator`.** The Story 9.13 spec (in this turn's brief) explicitly names `ToolCallAccumulator` even though the 9.6 skeleton stub used `DeltaAccumulator`. The skeleton was unreachable from any caller (`grep` confirmed zero call sites), so the rename is safe and matches the brief verbatim.
2. **`finish_reason` exposed as a `@property`, not a method**, because the brief asks `accumulate_stream` to return it as a tuple element — a property is more pythonic than `get_finish_reason()`. Tests assert against `accumulator.finish_reason`.
3. **`finalize()` leaves `function.arguments` as the original JSON-encoded string**, matching the OpenAI spec for `ToolCall.function.arguments`. Callers (Story 9.14) call `parse_arguments(call.function.arguments)` to get a `dict`. This keeps the `ToolCall` Pydantic model roundtrippable through `model_validate(model_dump())`.
4. **`type` propagation is defensive**: only set on the output `ToolCall` if upstream sent the literal string `"function"`. The Pydantic model is `Literal["function"] | None` so any other value would fail validation; this way a quirky upstream that omits `type` cleanly yields `None` instead of crashing.
5. **No log capture via `caplog`** — the project doesn't configure structlog through stdlib `logging`, so structlog uses its default-to-stdout printer. Tests assert via `capsys.readouterr().out` instead, which matches structlog's default behaviour and avoids forcing a global structlog config in tests.
6. **Module is 217 lines raw / 116 code lines (excluding docstrings)** — under the architecture's ≤150-LOC ceiling for `domain/` modules.
7. **No `httpx`, no env reads, no I/O.** Pure domain per architecture §Code structure rules; the async helper takes an `AsyncIterator[dict]` so the orchestrator (Story 9.14) feeds it whatever it likes (httpx SSE, fixture, list, generator).

---

## Acceptance criteria results

| AC | Result | Evidence |
|---|---|---|
| AC-1: 4 methods + 2 helpers (per spec) | PASS | `ToolCallAccumulator.{consume_chunk,is_complete,finalize,accumulated_text,reset}` + `parse_arguments` + `accumulate_stream`. `finish_reason` exposed as a property (deviation #2 above). |
| AC-2: ≥10 unit tests, all pass | PASS | 15 tests in `tests/unit/test_delta_accumulator.py`, all green. |
| AC-3: ruff + mypy + pytest all green | PASS | See command transcript below. |
| AC-4: No regressions in prior 49 tests | PASS | 80 tests collected total (49 prior + 16 from Story 9.12 landed in parallel + 15 new for 9.13); 80/80 pass. |
| AC-5: Module ≤150 LOC (excl. docstrings) | PASS | 116 code lines (AST-counted: 171 non-blank − 55 docstring lines). |
| AC-6: `accumulate_stream` works with mock async iterator | PASS | `test_accumulate_stream_end_to_end` and `test_accumulate_stream_plain_text_only` verify both branches (tool-call termination and plain `stop`) and that trailing chunks after termination are ignored. |

Spec-doc AC restatement (epic §9.13):

- **Single tool call across multiple chunks** — `test_single_tool_call_across_three_chunks` ✅
- **Multiple parallel `tool_calls` (different `index`)** — `test_two_parallel_tool_calls_interleaved` ✅
- **Interleaved text + tool_call deltas** — `test_pretext_content_captured_separately` ✅
- **Single-chunk completion** — `test_finalised_calls_are_validated_pydantic_tool_calls` (1-chunk happy path) ✅
- **JSON validation rejects malformed args + surfaces error** — `test_parse_arguments_malformed_returns_empty_and_warns` + `test_parse_arguments_non_object_returns_empty_and_warns` ✅
- **R4 / Open WebUI #23066 — clean delta emission**: This module accumulates deltas; emission of clean tool-call deltas to the downstream client is Story 9.14's orchestrator's job. The accumulator returns validated `ToolCall` objects that round-trip through Pydantic (`test_finalised_calls_are_validated_pydantic_tool_calls`), giving the orchestrator a known-clean payload to re-encode. The byte-level fixture comparison called out in the spec belongs to 9.14.

---

## Test count + lint/mypy/pytest transcript

```text
$ .venv/bin/ruff check src/gemma_hybrid_proxy/domain/delta_accumulator.py tests/unit/test_delta_accumulator.py
All checks passed!

$ .venv/bin/mypy src/
Success: no issues found in 19 source files

$ .venv/bin/pytest -q tests/
................................................................................ [100%]
80 passed in 0.23s
```

- **New tests (Story 9.13):** 15 in `tests/unit/test_delta_accumulator.py`
- **Total tests now:** 80 (49 prior baseline + 16 from Story 9.12 landed in parallel + 15 new)
- **Regressions:** 0

---

## Files touched

- **EDITED:** `homelab-infra/ansible/roles/gemma-hybrid-proxy/files/src/gemma_hybrid_proxy/domain/delta_accumulator.py` — fleshed out the 41-LOC skeleton from Story 9.6 to the 217-line implementation (116 code lines).
- **NEW:** `homelab-infra/ansible/roles/gemma-hybrid-proxy/files/tests/unit/test_delta_accumulator.py` — 15 unit tests (477 lines incl. helpers + docstrings).

No production state touched; no external services contacted; no Ansible / systemd / network changes; no new dependencies. Story 9.12 (`tool_definitions.py`) ran in parallel on disjoint files — no conflicts, both file trees coexist cleanly under `domain/` and `tests/unit/`.

---

## Boundaries respected

- Did NOT touch `chat_completions.py` (Story 9.14 wires this in).
- Did NOT touch `tool_definitions.py` (Story 9.12 owns it).
- Did NOT touch `multimodal_preprocessor.py`.
- Did NOT introduce `httpx` or any other adapter import in the domain module.
- Did NOT introduce a new prod dependency (uses stdlib `json` + already-pinned `structlog` for logging + the existing `openai_models.ToolCall` Pydantic type).

---

## Sprint status update

- 9.13 status: `pending` → `completed`
- owner: `unassigned` → `claude-coder`
- completion_date: `2026-04-25`
- evidence: this file (`9-13-delta-accumulator-evidence.md`)
- sprint_3 stories_completed: `0` → `1`
- sprint_3 notes: brief Story 9.13 summary appended

Sprint 3 may proceed to Story 9.14 (orchestrator agent loop) once Story 9.12 (parallel) also lands.
