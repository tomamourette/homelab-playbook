---
# Sprint 1 Tool-Call Accuracy Gate Results
# Story: 9.5 (Sprint 1 EXIT GATE)
# Date: 2026-04-25
# Owner: claude-coder
# Status: completed
---

## Summary

| Field | Value |
|---|---|
| **Target** | `http://127.0.0.1:8081` (llama-server inside ct-ai-01 / CT 160 on pve3) |
| **Model** | `gemma-4-26B-A4B-it-uncensored-Q4_K_M.gguf` (TrevorJS) with asf0 chat template |
| **Total prompts** | 50 |
| **Passed (all 3 checks)** | **49** |
| **Pass rate** | **98.0%** |
| **Tier** | **PASS** (≥90% threshold) |
| **Wall-clock time** | 374.3 s (~6 min 14 s) |
| **Mean per-prompt latency** | 7.49 s |
| **Reasoning_content present** | 50/50 — informational, sequestered field per ADR-003; **not** an R1 leakage indicator |

**Recommendation to director: Tier = PASS. Keep TrevorJS Q4_K_M as the sole reasoner. No fallback deploy required. Proceed to Sprint 2 unmodified. Record outcome as ADR-002 addendum.**

## How to re-run

The harness is re-runnable as a single command (with stdlib `urllib.request` only — no third-party dependencies needed inside the container):

```bash
# From the homelab controller
scp /home/developer/workspace/homelab/homelab-infra/tests/sprint1_toolcall_gate.py pve3:/tmp/
ssh pve3 "pct push 160 /tmp/sprint1_toolcall_gate.py /root/sprint1-gate/sprint1_toolcall_gate.py"
ssh pve3 "pct exec 160 -- bash -c 'cd /root/sprint1-gate && \
  TARGET_URL=http://127.0.0.1:8081 \
  RESULTS_JSON=/root/sprint1-gate/full-results.json \
  python3 sprint1_toolcall_gate.py'"
```

Optional: `LIMIT=5` env var for a fast plumbing check.

## Per-category breakdown

| Category | Total | Passed | Pass rate |
|---|---|---|---|
| single-tool-call | 20 | 20 | 100.0% |
| multi-tool-call (score first call) | 15 | 15 | 100.0% |
| parallel-call (score first call) | 5 | 5 | 100.0% (caveat below) |
| error-recovery | 5 | 5 | 100.0% |
| negative (no tool call expected) | 5 | 4 | 80.0% |
| **Total** | **50** | **49** | **98.0%** |

## Scoring rubric (recap)

Each prompt is scored on three binary checks; **all three must pass** for the prompt to count toward pass rate:

- **Schema-valid (S):** the emitted `tool_call` has parseable JSON arguments AND references a tool that's in the registered tool set. For negative/error-recovery prompts where no call is expected, S = True if no calls were emitted (or any emitted calls were structurally clean).
- **Correct-intent (I):** the chosen tool name matches the expected tool. For negative prompts, I = True if no call was emitted. For error-recovery, I = True if no call was emitted OR the call was emitted with empty/missing args (signaling the gap).
- **Correct-args (A):** for positive prompts, the actual arguments contain the expected subset (case-insensitive, with int↔str tolerance). For negative/error-recovery, A is trivially True (the gate hinges on S+I in that case).

Multi-call and parallel-call prompts are scored on the **FIRST** emitted call's intent and args, with a secondary informational check on whether the expected number of parallel calls were emitted (does NOT affect pass/fail).

## Failed prompts (1)

### `negative-02` — negative — FAIL
- **Prompt:** `"What is 2 plus 2?"`
- **Expected behavior:** answer directly with text ("4"), do not invoke a tool.
- **Actual:** model emitted `calculate(expression="2 + 2")` — chose to delegate trivial arithmetic to the registered tool rather than answering inline.
- **Failure reason:** correct-intent failed (negative prompt but tool was called). Schema-valid PASS (call structure was clean and references a registered tool).
- **Severity:** very low. The model is being conservative and using the tool that's literally named for arithmetic. In production this would just round-trip a `4` from the calculate tool. Not a chat-template failure (R1) and not a tool-call schema failure. Could be debated whether the rubric should mark this as PASS, but per the harness's "honest scoring" principle it's marked FAIL because the operator's intent was clearly "respond directly without using a tool."

## Clean PASS examples (representative)

| ID | Category | Prompt | Tool chosen | Args |
|---|---|---|---|---|
| single-01 | single | "What's the current weather in Tokyo? Use get_weather." | `get_weather` | `{"city":"Tokyo"}` |
| single-09 | single | "Weather in Paris in fahrenheit?" | `get_weather` | `{"city":"Paris","units":"fahrenheit"}` |
| single-08 | single | "Send email to alice@example.com, subject 'Test', body 'Hello Alice'" | `send_email` | `{"to":"alice@example.com","subject":"Test","body":"Hello Alice"}` |
| multi-01 | multi | "Find user 42's email, then look up the weather where they live." | `get_user_email` (first) | `{"user_id":42}` |
| multi-03 | multi | "Read /etc/hostname, then send its contents to ops@example.com" | `get_file_contents` (first) | `{"path":"/etc/hostname"}` |
| parallel-01 | parallel | "Tell me the weather in NYC, London, and Tokyo simultaneously." | `get_weather` (first) | `{"city":"New York"}` |
| error-01 | error_recovery | "What's the weather?" (no city) | (no call — text response) | n/a |
| negative-01 | negative | "Hello, how are you today?" | (no call — text response) | n/a |
| negative-04 | negative | "What is the capital of France?" | (no call — text response) | n/a |

## Anomalies and observations

### 1. Parallel-call prompts only emit ONE call (informational, not failure)

For all 5 `parallel-*` prompts the model emitted exactly **one** tool call (correct tool, sensible args), not the requested 2-3 parallel calls. The harness still scores them PASS because the first-call rubric for the locked Sprint 1 gate only checks intent + args, not call count. **However, this is a real Sprint-2/3 implication:** the proxy's `delta_accumulator` (Story 9.13) and tool-call orchestration loop (Story 9.12) should NOT assume the model will batch parallel calls — it currently chains them sequentially via re-prompting (typical for reasoner-style templates). Worth flagging in the Sprint 2 architecture review and possibly the ADR-002 addendum.

### 2. Two error-recovery prompts ran ~44s (~6× median)

`error-02` ("Look up that user's email") and `error-05` ("Read the file") each took ~44 s instead of the ~4-7 s median. Both correctly emitted no tool call, but the model produced long chain-of-thought (visible in `reasoning_content`) deliberating over the ambiguity. This is benign for a gate test but worth noting for Sprint 3 latency budgets — ambiguous prompts can have a 5-10× latency penalty under the asf0 reasoner template. Mitigation could be a max-CoT-tokens cap if it becomes a UX issue.

### 3. `reasoning_content` present in 50/50 responses

Every response carried a non-empty `reasoning_content` field. This is **expected and correct** under the asf0/gemma4_jinja chat template — chain-of-thought is sequestered there per ADR-003 — and is NOT an R1 indicator. The R1 risk (chat-template fix incomplete → CoT leaks into `content`) would have manifested as `content` containing CoT prose; that did not happen in any of the 50 prompts. **R1 is now considered closed.**

### 4. No JSON parse failures, no schema violations

All 50 responses had cleanly-parseable `arguments` strings; all chosen tool names were in the registered set. The chat template's tool-call grammar enforcement is solid.

### 5. Multi-tool prompts are slower than single-tool (~7.4 s mean vs. ~4.2 s)

The harness only sends a single turn (no actual tool-result feedback loop). Multi-tool prompts elicit more pre-call deliberation in `reasoning_content` and therefore higher latency, even though only the first call is scored. Expected; informational.

## Decision

**Tier: PASS** (98.0% ≥ 90% threshold)

**Action:** Keep TrevorJS Q4_K_M as sole reasoner. No Unsloth UD-Q5_K_M deploy. `gemma4-26b-text` and `gemma4-auto` both route to TrevorJS in Sprint 2.

**Required follow-up:** Append ADR-002 addendum in `homelab-playbook/_bmad-output/planning-artifacts/hybrid-gemma-serving-architecture.md` recording the 98% pass rate, the tier verdict, and the date — this is a **director-owned action** per the Sprint 1 exit gate spec (the harness only measures; the ADR appendage is the architectural record).

## Files

- Test harness: `homelab-infra/tests/sprint1_toolcall_gate.py` (~600 LOC, stdlib-only)
- Per-prompt JSON results: `homelab-playbook/_bmad-output/implementation-artifacts/sprint1-toolcall-gate-results-2026-04-25.json`
- This report: `homelab-playbook/_bmad-output/implementation-artifacts/sprint1-toolcall-gate-results-2026-04-25.md`
- Evidence summary: `homelab-playbook/_bmad-output/implementation-artifacts/9-5-toolcall-gate-evidence.md`
