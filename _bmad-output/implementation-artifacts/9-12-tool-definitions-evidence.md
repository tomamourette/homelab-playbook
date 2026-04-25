# Story 9.12 — `analyze_image` tool schema + registry plumbing

**Owner:** claude-coder
**Completed:** 2026-04-25
**Sprint:** 3 (Tool-call agent loop + LiteLLM gateway)
**Depends on:** 9.11 (proxy deployed on ct-ai-01)
**Unblocks:** 9.13 (delta accumulator), 9.14 (orchestrator agent loop), 9.15 (synthetic-prompt smoke)

## Scope

Lock the OpenAI function-calling schema for `analyze_image` and add the
registry plumbing the orchestrator (Story 9.14) will use to inject the
tool, validate emitted arguments, and label images with stable IDs the
26B reasoner can reference. Pure domain module — zero I/O, zero `httpx`.

## Files

| File | Change |
|---|---|
| `homelab-infra/ansible/roles/gemma-hybrid-proxy/files/src/gemma_hybrid_proxy/domain/tool_definitions.py` | Replaced 45-LOC Story 9.6 skeleton with 117-LOC implementation (excludes docstrings/blanks). |
| `homelab-infra/ansible/roles/gemma-hybrid-proxy/files/tests/unit/test_tool_definitions.py` | NEW — 16 unit tests. |

## Public surface (`__all__`)

* `ANALYZE_IMAGE_TOOL` — OpenAI tool definition dict (`type=function`,
  `function.name="analyze_image"`, `image_id` + `question` required,
  `additionalProperties: false`).
* `AVAILABLE_TOOLS` — `[ANALYZE_IMAGE_TOOL]`. `transcribe_audio` is
  intentionally absent (ADR-008 defers audio to Sprint 4).
* `MAX_TOOL_ITERATIONS = 5` — architecture §Error handling rules cap;
  Story 9.14 reads it (overridable via
  `gemma_hybrid_proxy_max_tool_iterations`).
* `get_tool_by_name(name) -> dict | None` — registry lookup for the
  Story 9.14 executor.
* `augment_request_with_tools(request_body, available_tools) -> dict`
  — pure deep-copy merge. Injects our tools when the client supplied
  none, dedup-by-name appends when the client supplied some (client's
  copy wins on overlap), defaults `tool_choice` to `"auto"` only when
  unset. **Caller (Story 9.14) gates this on `model == "gemma4-auto"`;
  passthrough aliases stay pure passthrough.**
* `assign_image_ids(messages) -> list[dict]` — deep-copy walk that
  inserts `{"type":"text","text":"[Image image-N:]"}` immediately
  before each `image_url` block. Numbering is **global across all
  messages** (image-1 in message 0, image-2 in message 2, etc.).
  Designed to compose with `multimodal_preprocessor.preprocess_images`:
  Story 9.14 will wire `assign_image_ids` BEFORE `preprocess_images` so
  the final shape is `[Image image-N:] [Image description: ...]`.
* `AnalyzeImageArgs` — Pydantic v2 model, `strict=True, extra="forbid"`,
  used by the executor to validate emitted tool-call arguments before
  dispatch.

## Acceptance criteria

| AC | Status | Evidence |
|---|---|---|
| AC-1 — 6 functions/constants per spec | PASS | All defined; see `__all__`. |
| AC-2 — ~12 unit tests pass | PASS — 16 tests | `pytest tests/unit/test_tool_definitions.py -q` → `16 passed`. |
| AC-3 — `ruff` + `mypy` + `pytest` green | PASS | `ruff check` → `All checks passed!`; `mypy src/` → `Success: no issues found in 19 source files`; `pytest -q` → `65 passed`. |
| AC-4 — No regressions in prior 49 tests | PASS | Full suite: `49 → 65`, +16 new, 0 broken. |
| AC-5 — Module ≤120 LOC excluding docstrings | PASS — 117 LOC | AST-based count (non-blank, non-docstring). |

Also covers the epic-level ACs from `hybrid-gemma-serving-epics.md`:

* **Schema shape** — `name="analyze_image"`, plain-English description,
  required `image_id` + `question` strings → matches architecture
  §Tool-call schema rules verbatim (architecture lines 426-445).
* **Schema validates against OpenAI function-calling spec** —
  `test_analyze_image_tool_validates_as_openai_tool_definition` parses
  it through the `ToolDefinition` Pydantic model (strict,
  `extra="forbid"`).
* **Unit tests cover** schema loads / validates synthetic well-formed
  call (`AnalyzeImageArgs`) / rejects missing required / rejects extras
  (`additionalProperties: false` + Pydantic strict).
* **Registered for orchestrator import** —
  `from gemma_hybrid_proxy.domain.tool_definitions import AVAILABLE_TOOLS, augment_request_with_tools`
  is the contract Story 9.14 consumes.

## Test breakdown (16 tests)

* Tool shape (3) — Pydantic-validates as `ToolDefinition`,
  `MAX_TOOL_ITERATIONS == 5`, registry holds only `analyze_image`.
* `get_tool_by_name` (2) — hit returns canonical dict identity, miss
  returns `None`.
* `augment_request_with_tools` (5) — empty client tools → injects +
  sets `tool_choice: "auto"`; distinct client tools → merges both;
  overlapping name → client wins, no duplication; existing
  `tool_choice` preserved; input dict unmodified after call.
* `assign_image_ids` (3) — text-only no-op + non-mutation; single
  image gets `[Image image-1:]` sibling; two images across messages
  get `image-1` then `image-2` (global numbering).
* `AnalyzeImageArgs` strict mode (3) — canonical accepted, extras
  rejected, missing required rejected.

## Lint / type / test commands

```bash
cd homelab-infra/ansible/roles/gemma-hybrid-proxy/files
.venv/bin/ruff check src/gemma_hybrid_proxy/domain/tool_definitions.py tests/unit/test_tool_definitions.py
# All checks passed!

.venv/bin/mypy src/
# Success: no issues found in 19 source files

.venv/bin/pytest -q
# ................................................................. [100%]
# 65 passed in 0.23s
```

## Coordination notes

* Disjoint with Story 9.13 (delta accumulator). 9.13 owns
  `domain/delta_accumulator.py` + its tests; 9.12 owns
  `domain/tool_definitions.py` + its tests. Both can land in any order.
* `domain/multimodal_preprocessor.py` was NOT modified — Story 9.14
  composes the two pure functions (`assign_image_ids` then
  `preprocess_images`) at the call site.
* `api/chat_completions.py` was NOT modified — Story 9.14 adds the
  tool-loop branch.
* No live test against ct-ai-01 — Story 9.15 owns the integration smoke.
* No new dependencies. `pydantic` and `copy` already in tree.

## Deviations

None.
