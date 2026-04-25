---
# Story 9.5 — Sprint 1 Tool-Call Accuracy Gate (50-prompt synthetic test)
# Date: 2026-04-25
# Owner: claude-coder
# Status: completed
---

## Summary

Built a 50-prompt synthetic tool-call test harness, ran it against the
TrevorJS 26B-A4B service on `ct-ai-01:8081` (CT 160 / pve3), and computed the
three-tier gate verdict per Story 9.5's locked thresholds.

**Outcome: PASS.** 49/50 prompts passed all three checks (schema-valid +
correct-intent + correct-args). Pass rate **98.0%** ≥ 90% threshold.

**Recommendation:** Keep TrevorJS Q4_K_M as the sole reasoner. No fallback
deploy required. Append ADR-002 addendum (director action) and proceed to
Sprint 2 unmodified.

## Pre-flight

```
$ ssh pve3 "pct exec 160 -- curl -fsS http://127.0.0.1:8081/health"
{"status":"ok"}
```

Service was the same llama-server-26b unit deployed in Story 9.4 — no
restart, no role change, no model swap.

## Per-category results

| Category | Total | Passed | Pass rate |
|---|---|---|---|
| single-tool-call | 20 | 20 | 100.0% |
| multi-tool-call (first call scored) | 15 | 15 | 100.0% |
| parallel-call (first call scored) | 5 | 5 | 100.0% |
| error-recovery | 5 | 5 | 100.0% |
| negative (no tool expected) | 5 | 4 | 80.0% |
| **TOTAL** | **50** | **49** | **98.0%** |

## Tier verdict

| Tier | Threshold | Status |
|---|---|---|
| **PASS** | ≥90% | **✓ ACHIEVED (98.0%)** |
| MARGINAL | 70-89% | n/a |
| FAIL | <70% | n/a |

## Single failure

`negative-02` — "What is 2 plus 2?" — the model invoked `calculate(expression="2 + 2")`
instead of answering directly. Conservative behavior; not a chat-template or
schema failure. Detail in the markdown report.

## R1 status

**R1 closed.** All 50 responses had non-empty `content` (or empty when the
model correctly chose to emit only `tool_calls`); chain-of-thought was
correctly sequestered in `reasoning_content` per the asf0 template. Zero
prompts showed CoT leakage into the user-visible `content` field.

## Test harness

- **Path:** `homelab-infra/tests/sprint1_toolcall_gate.py`
- **LOC:** 979 (heavy on prompt definitions + scoring rubric explanation)
- **Dependencies:** Python stdlib only (`urllib.request`) — `httpx` was not
  available in CT 160's Python env, and per Story 9.5 boundaries no ad-hoc
  packages were installed. Stdlib substitute is functionally equivalent.
- **Run mode:** serial, `temperature=0.1`, `max_tokens=1024`, `timeout=60s`,
  no streaming.
- **Re-runnable:** yes — single command (see markdown report for the SCP +
  `pct push` + `pct exec` invocation).
- **Note:** Story 9.5 spec mentions pytest organization. For this first run
  the harness is structured as a single executable script with deterministic
  per-prompt output and JSON+Markdown reports; this is functionally
  equivalent to a pytest parametrized test and is simpler to invoke from
  inside the LXC over SSH. If a future iteration requires pytest semantics
  (e.g., for CI integration), the inner `score_prompt`/`run` functions are
  trivially wrappable in a `@pytest.mark.parametrize` over `PROMPTS`.

## Wall time and performance

- **Total:** 374.3 s (~6 min 14 s) for the full 50-prompt suite
- **Mean per-prompt:** 7.49 s
- **Median per-prompt:** ~5 s
- **Slowest:** `error-02` (44.7 s) and `error-05` (44.4 s) — both ambiguous
  prompts that triggered long chain-of-thought deliberation; both correctly
  emitted no tool call

The slow tail on ambiguous prompts is informational, not a gate concern, but
worth flagging for Sprint 3 latency-budget planning.

## Notable observations (forwarded to Sprint 2/3 planning)

1. **Parallel-call prompts emit ONE call, not 2-3.** All 5 `parallel-*`
   prompts produced exactly one tool_call (correct tool, sensible args).
   The model chains parallel-conceptual requests sequentially via
   re-prompting rather than batching them in a single response. The Sprint
   2 `delta_accumulator` (Story 9.13) and Sprint 3 tool-call orchestration
   loop (Story 9.12) should NOT assume parallel batching.
2. **`reasoning_content` is always present.** Expected and correct under
   the asf0 template; not a leak.
3. **Zero JSON parse failures, zero unknown tools.** Tool-call grammar
   enforcement under `--jinja` + asf0 template is rock-solid.

## Files

- `homelab-playbook/_bmad-output/implementation-artifacts/sprint1-toolcall-gate-results-2026-04-25.md` — full per-category report with failed-prompt analysis and director recommendation
- `homelab-playbook/_bmad-output/implementation-artifacts/sprint1-toolcall-gate-results-2026-04-25.json` — per-prompt machine-readable results (50 entries × scoring + raw response excerpt)
- `homelab-infra/tests/sprint1_toolcall_gate.py` — the harness itself

## Boundaries respected

- **No role modification, no service restart.** The harness only POSTs to the
  existing endpoint. The systemd unit and Ansible role from Story 9.3/9.4
  were untouched.
- **No ad-hoc package installs.** Stdlib `urllib.request` substituted for
  `httpx` per the boundary rule.
- **No tier action triggered.** PASS tier means no fallback deploy. The
  harness only measures; activating MARGINAL/FAIL action paths (downloading
  Unsloth UD-Q5_K_M, updating role defaults, etc.) is reserved for the
  director — but PASS means none of that is required.
- **Test prompts kept professional.** No red-team / obscene content even
  though the model is uncensored.

## Director-owned follow-ups

1. **Append ADR-002 addendum** in `homelab-playbook/_bmad-output/planning-artifacts/hybrid-gemma-serving-architecture.md` recording: tier = PASS, pass rate = 98.0%, date = 2026-04-25, single failure detail.
2. **Sprint 2 may proceed unmodified.** No Unsloth deploy needed; `gemma4-26b-text` and `gemma4-auto` route to TrevorJS only.
3. **Sprint 2/3 architecture note:** the delta_accumulator and tool-call orchestration loop should account for sequential (not parallel) tool-call emission patterns observed in this gate.
