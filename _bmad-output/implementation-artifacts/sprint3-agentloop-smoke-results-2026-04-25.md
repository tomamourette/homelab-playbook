# Sprint 3 Agent-Loop Smoke Test Results — Story 9.15

- **Date:** 2026-04-25
- **Owner:** claude-coder
- **Target:** Production proxy at `http://127.0.0.1:8000` on ct-ai-01 (CT 160), model `gemma4-auto`
- **Harness:** `homelab-infra/tests/sprint3_agentloop_smoke.py` (25 prompts, stdlib-only, SSE streaming)
- **Results JSON:** `sprint3-agentloop-smoke-results-2026-04-25.json` (in this directory)

---

## Headline result

**12/25 PASS (48.0%)**, wall time **837.6s (14.0 min)**, **0 HTTP 5xx** errors, all 4 production services preserved.

| Category          | Result | Pass criterion (per AC) |
|-------------------|--------|-------------------------|
| no_image          | **5/5 (100%)** | AC-3 ≥80% — PASS |
| passive_image     | **5/5 (100%)** | AC-4 ≥80% — PASS |
| tool_triggering   | **0/10 (0%)**  | AC-5 ≥50% — **FAIL** |
| multi_iteration   | **0/3 (0%)**   | AC-6 at least one with 2+ — **FAIL** |
| iteration_cap     | **2/2 (100%)** | AC-7 both terminate — PASS |

---

## Per-prompt results

| # | id | category | flags | result | wall (s) | tool_calls | finish_reason | notes |
|---|----|----------|-------|--------|---------:|-----------:|---------------|-------|
| 1 | noimg-01 | no_image | C5BS | PASS | 3.52 | 0 | length | — |
| 2 | noimg-02 | no_image | C5BS | PASS | 5.14 | 0 | length | — |
| 3 | noimg-03 | no_image | C5BS | PASS | 1.97 | 0 | length | — |
| 4 | noimg-04 | no_image | C5BS | PASS | 2.70 | 0 | length | — |
| 5 | noimg-05 | no_image | C5BS | PASS | 4.22 | 0 | length | — |
| 6 | passive-01 | passive_image | C5BS | PASS | 31.98 | 0 | length | describe event fired |
| 7 | passive-02 | passive_image | C5BS | PASS | 31.26 | 0 | length | describe event fired |
| 8 | passive-03 | passive_image | C5BS | PASS | 30.65 | 0 | length | describe event fired |
| 9 | passive-04 | passive_image | C5BS | PASS | 30.80 | 0 | length | describe event fired |
| 10 | passive-05 | passive_image | C5BS | PASS | 29.35 | 0 | length | describe event fired |
| 11 | tool-01 | tool_triggering | C5-S | FAIL | 34.15 | 0 | stop | model emitted `<\|tool_call>` text instead of structured tool_call |
| 12 | tool-02 | tool_triggering | C5-S | FAIL | 43.64 | 0 | length | ran out of tokens in reasoning |
| 13 | tool-03 | tool_triggering | C5-S | FAIL | 43.59 | 0 | length | ran out of tokens in reasoning |
| 14 | tool-04 | tool_triggering | C5-S | FAIL | 38.03 | 0 | stop | model emitted `<\|tool_call>` text instead of structured tool_call |
| 15 | tool-05 | tool_triggering | C5-S | FAIL | 43.57 | 0 | length | ran out of tokens in reasoning |
| 16 | tool-06 | tool_triggering | C5-S | FAIL | 40.75 | 0 | stop | model emitted `<\|tool_call>` text instead of structured tool_call |
| 17 | tool-07 | tool_triggering | C5-S | FAIL | 34.50 | 0 | stop | model emitted `<\|tool_call>` text instead of structured tool_call |
| 18 | tool-08 | tool_triggering | C5-S | FAIL | 45.11 | 0 | length | ran out of tokens in reasoning |
| 19 | tool-09 | tool_triggering | C5-S | FAIL | 32.90 | 0 | stop | model emitted `<\|tool_call>` text instead of structured tool_call |
| 20 | tool-10 | tool_triggering | C5-S | FAIL | 42.44 | 0 | length | ran out of tokens in reasoning |
| 21 | multi-01 | multi_iteration | C5-S | FAIL | 51.36 | 0 | length | ran out of tokens, no structured tool_call |
| 22 | multi-02 | multi_iteration | C5-S | FAIL | 51.23 | 0 | length | ran out of tokens, no structured tool_call |
| 23 | multi-03 | multi_iteration | C5-S | FAIL | 51.16 | 0 | length | ran out of tokens, no structured tool_call |
| 24 | cap-01 | iteration_cap | C5BS | PASS | 54.22 | 0 | stop | model emitted SIX `<\|tool_call>` tokens in plain text — proper structured emission would have triggered loop |
| 25 | cap-02 | iteration_cap | C5BS | PASS | 59.40 | 0 | stop | terminated cleanly |

**Flags legend:** `C` completed (saw `[DONE]`), `5` no 5xx, `B` behavior_ok per category, `S` status_events_ok.

---

## Acceptance criteria results

| AC | Description | Result | Value |
|----|-------------|--------|-------|
| AC-1 | Harness runs end-to-end against production `:8000` without error | **PASS** | 25/25 got HTTP responses |
| AC-2 | 25 prompts executed; per-prompt scores recorded | **PASS** | 25/25 prompts |
| AC-3 | NO-IMAGE pass rate ≥ 80% | **PASS** | 5/5 (100%) |
| AC-4 | PASSIVE-IMAGE pass rate ≥ 80% | **PASS** | 5/5 (100%) |
| AC-5 | TOOL-TRIGGERING pass rate ≥ 50% | **FAIL** | 0/10 (0%) — see "Critical finding" below |
| AC-6 | MULTI-ITERATION: at least one prompt triggers 2+ tool calls | **FAIL** | 0 multi prompts triggered structured tool_calls |
| AC-7 | ITERATION-CAP: both prompts terminate without hanging | **PASS** | 2/2 completed cleanly |
| AC-8 | Status events visible: every multimodal prompt shows `_[describing image...]_` | **PASS** | 20/20 multimodal prompts had describe events |
| AC-9 | No 5xx errors observed | **PASS** | 0 5xx errors |
| AC-10 | Production state preserved | **PASS** | gemma-hybrid-proxy.service `active`; llama-server.service `active`; llama-server-26b.service `active`; open-webui (docker) `Up healthy` |

**Overall: 8/10 ACs PASS, 2/10 FAIL (AC-5, AC-6).**

---

## Critical finding: model emits unstructured tool-call tokens

**6/15** multimodal-tool prompts produced plain-text content like:

```text
<|tool_call>call:google:analyze_image{queries:['What is the exact RGB color value of the center pixel of this image?']}<tool_call|>
<|tool_call>call:analyze_image{question: 'what is written in the top-left corner of the image?'}<tool_call|>
<|tool_call>call:analyze_image(prompt="What are the dominant colors in this image?")<tool_call|>
```

These were emitted in `delta.content`, not in `delta.tool_calls`. Because the proxy's
agent loop only fires when `finish_reason == "tool_calls"`, the loop never executed —
even though the model clearly *wanted* to call `analyze_image`. Notable cases:

- **cap-01** emitted SIX consecutive `<|tool_call>` tokens in plain text — exactly the kind of multi-call sequence Story 9.14's iteration cap was designed to handle.
- **tool-04** emitted a perfectly-formed call with the right tool name and a sensible question, but as text.

**Likely root cause:** llama.cpp's `--jinja` mode + `gemma4-asf0.jinja` chat template
isn't transforming the TrevorJS abliterated Gemma 4 26B-A4B's tool-call output format
into structured `tool_calls` SSE deltas. The Sprint 1 gate (Story 9.5) *did* show
this model produces structured tool_calls when called directly on `:8081` with raw
tools (98% pass rate). The difference: Sprint 1 hit `:8081` directly with the
harness's `tools` field; this story hits `:8000` where the proxy injects
`analyze_image` into the messages flow with image preprocessing intervening.

**Independent confirmation:** I re-ran the EXACT prompt that produced a structured
`tool_calls` finish_reason in Story 9.14's live smoke (~2h ago) and got
`finish_reason=stop` with no tool_calls — confirming this is current production
behavior, not a harness parser bug. (Probe script: `/tmp/probe_tool_call.py`.)

This is a real Story 9.18+ candidate (template / parser fix) — but is OUT OF SCOPE
for Story 9.15, which only validates the agent loop end-to-end. The agent-loop
INFRASTRUCTURE (Story 9.14) is correct: status events fire (20/20 describe events),
preprocessing works (every multimodal prompt got `_[describing image...]_`), the
proxy stays up under load (no 5xx in 837s), and the iteration cap behavior is sound
(both cap prompts terminated cleanly). What's missing is the upstream signal that
WOULD trigger the loop.

---

## Other anomalies

- **9/15 tool-triggering and multi-iteration prompts hit `finish_reason=length`** before they had a chance to emit a tool call — token budget (`max_tokens=400-600`) was insufficient to cover the model's verbose `reasoning_content` AND a final tool call. Recommend bumping `max_tokens` to ≥1024 in any retry suite, or reducing the model's reasoning verbosity via system-prompt nudge.
- **All 5 no_image prompts hit `finish_reason=length` despite tight `max_tokens` (40-120)** — the model's `reasoning_content` consumes the budget before producing the answer. Expected per ADR-003 (reasoning_content sequestered) — the visible answers were still coherent, so behavior_ok=True.
- **0 `_[calling analyze_image...]_` status events** across the entire run — directly downstream of the structured-tool-call gap above. The Story 9.14 status event for tool-call detection only fires when `finish_reason="tool_calls"` lands, which never happened.
- **0 `_[Maximum tool-call iterations reached.]_` events** — the iteration cap never fired (because no iterations ever ran). `MAX_TOOL_ITERATIONS=5` is unproven against real production traffic; this story can't validate it.
- **Wall-time per multimodal prompt: ~30-55s**, dominated by E4B preprocess (~26s) + 1 MoE iteration (~5-30s depending on token budget). Consistent with Story 9.14's ~26s preprocess and ~25-50s MoE expectations.

---

## Five example failures (with brief reasons)

1. **tool-01** — Model emitted `<|tool_call>call:google:analyze_image{queries:['What is the exact RGB color value...']}<tool_call|>` as plain text. Should have been a structured `delta.tool_calls`. (Template/parser gap.)

2. **tool-02** — Model spent 400 tokens deliberating in `reasoning_content` and never produced a tool call or a visible answer (`finish_reason=length`). Token budget too tight given the 26B's reasoning verbosity.

3. **tool-04** — Same as tool-01: emitted `<|tool_call>call:analyze_image{question: 'what is written in the top-left corner...'}<tool_call|>` as text. Tool name + arg name were correct.

4. **multi-01** — Multi-step prompt asking for 3 separate analyze_image calls; model spent all 600 tokens reasoning, never produced any tool call. `finish_reason=length`.

5. **cap-01** — IRONIC PASS. The harness scored this PASS (terminated cleanly, AC-7 satisfied) but the model attempted SIX sequential `<|tool_call>` text emissions — exactly the multi-iteration sequence that Story 9.14's iteration cap was built for. If the structured-tool-call emission worked, this would have been the most interesting prompt in the suite.

---

## Production state preservation (AC-10)

```
$ ssh pve3 "pct exec 160 -- bash -c 'systemctl is-active gemma-hybrid-proxy.service llama-server.service llama-server-26b.service ; docker ps --format \"{{.Names}} {{.Status}}\" | grep -i webui'"
active
active
active
open-webui   Up 57 minutes (healthy)
```

All four production services preserved before, during, and after the test. The
proxy handled 25 sequential streaming requests with no degradation.

LiteLLM gateway (Story 9.16, parallel) was deployed mid-test on `:4000` — no impact
on `:8000` reachability or test results (disjoint ports per coordinator note).

---

## Pre-flight + execution summary

```
$ ssh pve3 "pct exec 160 -- curl -fsS http://127.0.0.1:8000/health"
{"status":"ok","upstreams":{"e4b":"ok","moe":"ok"}}

$ ssh pve3 "pct push 160 /tmp/sprint3_agentloop_smoke.py /tmp/sprint3_agentloop_smoke.py"
PUSHED

$ ssh pve3 "pct exec 160 -- bash -c 'TIMEOUT=240 RESULTS_JSON=/tmp/sprint3-agentloop-smoke-results-2026-04-25.json python3 /tmp/sprint3_agentloop_smoke.py'"
... (25 prompts × ~33s avg = 837.6s wall time) ...
TOTAL: 12/25 PASS (48.0%)
Wall time: 837.6s (14.0 min)

$ scp pve3:/tmp/sprint3-agentloop-smoke-results-2026-04-25.json _bmad-output/implementation-artifacts/
(via pct pull then scp — JSON in repo)
```

Exit code 1 from the harness is **expected** (it gates at <50% pass rate, and this
run was 48%). The non-zero exit reflects the under-target tool-call rate, not a
harness bug.

---

## Conclusion

Story 9.15 is **partially complete**:

- **PASS:** AC-1, AC-2, AC-3, AC-4, AC-7, AC-8, AC-9, AC-10 (8/10)
- **FAIL:** AC-5 (0/10 vs ≥50% target), AC-6 (no multi-iteration prompt produced 2+ structured tool calls)

The harness itself is correct and the agent-loop INFRASTRUCTURE works — preprocess
fires, status events emit, the loop is reachable, the iteration cap doesn't hang.
The gap is upstream: the deployed TrevorJS Gemma 4 26B-A4B Q4_K_M + `gemma4-asf0.jinja`
chat template is emitting `<|tool_call>...<tool_call|>` as plain text rather than
as structured `delta.tool_calls` SSE chunks under the proxy's compose flow (image
preprocess + augmented tools + bigger context). Sprint 1's 98% pass rate showed the
model CAN produce structured tool_calls when called directly on `:8081` with simple
text prompts — the regression appears in the proxy's compose path.

**Recommendation:** This finding is the right kind to surface NOW, before Story 9.18
goes deeper into agent loop correctness. Either:

1. (lightweight) tighten the `gemma4-auto` system prompt to remind the model to use
   structured tool calls, then re-run this harness; or
2. (medium) audit the `gemma4-asf0.jinja` template against TrevorJS's documented
   tool-call format and check whether `--jinja` is actually parsing it correctly
   under the proxy's request shape; or
3. (heavy) bump to Unsloth UD-Q5_K_M (Sprint 1 fallback) for the agent-loop path
   and gate the decision on a re-run.

The harness is reusable for any of these — set `TARGET_URL` and re-run. JSON +
Markdown reports diff cleanly across runs.
