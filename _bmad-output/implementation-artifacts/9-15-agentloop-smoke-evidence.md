# Story 9.15 — Agent-loop smoke test (synthetic prompts → live :8000 proxy) — Evidence

- **Sprint:** 3
- **Owner:** claude-coder
- **Date:** 2026-04-25
- **Depends on:** 9.14 (orchestrator agent loop on production proxy at `:8000`)
- **Source spec:** `_bmad-output/planning-artifacts/hybrid-gemma-serving-epics.md` §Story 9.15; harness pattern from `homelab-infra/tests/sprint1_toolcall_gate.py` (Story 9.5)

---

## Implementation summary

New stdlib-only smoke harness `homelab-infra/tests/sprint3_agentloop_smoke.py`
(606 raw lines) modelled on Sprint 1's pattern but targeting the production
`gemma-hybrid-proxy` on `:8000` (model `gemma4-auto`, where the proxy
auto-injects `analyze_image`) rather than `:8081` directly. SSE-streaming
client; per-prompt scoring across 4 binary checks (`completed`, `no_5xx`,
`behavior_ok` per category, `status_events_ok`); per-category aggregation;
AC-level pass/fail evaluation; JSON + Markdown outputs.

**25-prompt suite** distributed:

| Category | Count | Behavior expected | Pass threshold (AC) |
|---|---|---|---|
| `no_image` | 5 | No tool calls (regression check) | AC-3: ≥80% |
| `passive_image` | 5 | Preprocess describe; no tool call | AC-4: ≥80% |
| `tool_triggering` | 10 | ≥1 `analyze_image` tool call | AC-5: ≥50% |
| `multi_iteration` | 3 | ≥2 `analyze_image` tool calls | AC-6: ≥1 prompt with 2+ |
| `iteration_cap` | 2 | Terminates cleanly (cap may or may not fire) | AC-7: both terminate |

Synthetic image: 1x1 red PNG (model will hallucinate details — fine, we score
agent-loop BEHAVIOR not visual accuracy).

Configurable via env vars: `TARGET_URL` (default `http://127.0.0.1:8000`),
`LIMIT`, `TIMEOUT` (default 180s). Exits non-zero if pass rate < 50% (smoke
gate).

---

## Files touched

- **NEW:** `homelab-infra/tests/sprint3_agentloop_smoke.py` (606 LOC, stdlib-only)
- **NEW:** `_bmad-output/implementation-artifacts/sprint3-agentloop-smoke-results-2026-04-25.json` (raw per-prompt + aggregate)
- **NEW:** `_bmad-output/implementation-artifacts/sprint3-agentloop-smoke-results-2026-04-25.md` (analysis + per-prompt table + critical-finding writeup)
- **NEW:** `_bmad-output/implementation-artifacts/9-15-agentloop-smoke-evidence.md` (this file)
- **MODIFIED:** `_bmad-output/implementation-artifacts/hybrid-gemma-serving-sprint-status.md` (9.15 status pending → completed; sprint_3 stories_completed 4 → 5)

No production state touched. Harness ran inside CT 160 against in-container
loopback `:8000`. No ad-hoc package installs. No proxy or role changes.

---

## Acceptance criteria results

| AC | Result | Evidence |
|---|---|---|
| AC-1: Harness runs end-to-end against production `:8000` without error | **PASS** | 25/25 prompts got HTTP responses (all 200); harness completed; reports written |
| AC-2: 25 prompts executed; per-prompt scores recorded | **PASS** | 25/25 in JSON results, all categories represented |
| AC-3: NO-IMAGE pass rate ≥ 80% | **PASS** | 5/5 (100%) — model never tool-called on text-only prompts (correct regression) |
| AC-4: PASSIVE-IMAGE pass rate ≥ 80% | **PASS** | 5/5 (100%) — describe events fired, no tool calls (description sufficed) |
| AC-5: TOOL-TRIGGERING pass rate ≥ 50% | **FAIL** | 0/10 — see "Critical finding" §below |
| AC-6: MULTI-ITERATION: at least one prompt triggers 2+ tool calls | **FAIL** | 0/3 — same root cause as AC-5 |
| AC-7: ITERATION-CAP: both prompts terminate without hanging | **PASS** | 2/2 completed cleanly with `[DONE]`; neither hit the synthetic max-iter close |
| AC-8: Status events visible: every multimodal prompt shows `_[describing image...]_` | **PASS** | 20/20 multimodal prompts had ≥1 describe event (matches Story 9.10 status-event behavior) |
| AC-9: No 5xx errors observed | **PASS** | 0 5xx across all 25 prompts (837s wall) |
| AC-10: Production state preserved | **PASS** | All 4 services `active` before+after — `gemma-hybrid-proxy.service`, `llama-server.service`, `llama-server-26b.service`, `open-webui` (docker container `Up healthy`) |

**8/10 ACs PASS, 2/10 FAIL (AC-5, AC-6).**

---

## Critical finding (root cause of AC-5 / AC-6 failure)

**6/15 multimodal-tool prompts emitted unstructured `<|tool_call>...<tool_call|>`
tokens in `delta.content` rather than as structured `delta.tool_calls` SSE
chunks.** Examples captured from JSON results:

```text
tool-01: <|tool_call>call:google:analyze_image{queries:['What is the exact RGB color value of the center pixel of this image?']}<tool_call|>
tool-04: <|tool_call>call:analyze_image{question: 'what is written in the top-left corner of the image?'}<tool_call|>
tool-06: <|tool_call>call:google:analyze_image{prompt='Is there any text or writing in this image?...'}<tool_call|>
tool-07: <|tool_call>call:analyze_image{question: 'is there a human face visible in this image, and if so where?'}<tool_call|>
tool-09: <|tool_call>call:analyze_image{question: 'count any geometric shapes (circles, squares, triangles) visible in this image'}<tool_call|>
cap-01: <|tool_call>call:analyze_image(prompt="What are the dominant colors in this image?")<tool_call|><|tool_call>call:analyze_image(prompt="What are the main shapes present in this image?")<tool_call|>... (six total)
```

The remaining 9 multimodal-tool prompts hit `finish_reason=length` before
producing any tool call (token budget exhausted by the 26B's `reasoning_content`).

The proxy's agent loop only fires when `finish_reason == "tool_calls"`, which
NEVER happened across all 25 prompts. So the loop never executed iteration ≥1,
and the iteration cap (`MAX_TOOL_ITERATIONS=5`) was never tested against
production traffic.

**Independent confirmation that this is current production behavior, not a
harness parser bug:** I re-ran the EXACT prompt that produced a structured
`tool_calls` finish_reason in Story 9.14's live smoke (~2h prior, against
`:18005`):

```text
$ ssh pve3 "pct exec 160 -- python3 /tmp/probe_tool_call.py"
FINISH_REASON=stop
[DONE]
```

No tool_calls delta. Model now declines the call against the same prompt it
accepted 2 hours ago against the temporary `:18005` smoke server. The Sprint 1
gate (Story 9.5) ALSO showed this model produces structured tool_calls when
called directly on `:8081` with simple text prompts (98% pass rate). The
delta: `:8000` proxy adds image preprocess + tool injection + larger
context — and somewhere in that compose path, the model's tool-call output
isn't being parsed structurally.

**Likely cause:** llama.cpp's `--jinja` mode + `gemma4-asf0.jinja` template
isn't transforming the model's `<|tool_call>...<tool_call|>` text tokens into
structured `tool_calls` for the OpenAI-API surface under the proxy's compose
flow. This is a Story 9.18+ candidate (template / parser fix) but is OUT OF
SCOPE for Story 9.15.

**The agent-loop INFRASTRUCTURE (Story 9.14) is correct:**
- Status events fire (20/20 multimodal prompts had describe events)
- Preprocess works (every multimodal prompt got `_[describing image 1 of 1...]_`)
- Proxy stays up under sequential load (no 5xx in 837s)
- Iteration cap doesn't hang (both cap prompts terminated cleanly)

What's missing is the upstream signal that WOULD trigger the loop.

---

## Live execution transcript

```text
$ ssh pve3 "pct exec 160 -- curl -fsS http://127.0.0.1:8000/health"
{"status":"ok","upstreams":{"e4b":"ok","moe":"ok"}}

$ scp tests/sprint3_agentloop_smoke.py pve3:/tmp/sprint3_agentloop_smoke.py
$ ssh pve3 "pct push 160 /tmp/sprint3_agentloop_smoke.py /tmp/sprint3_agentloop_smoke.py"
$ ssh pve3 "pct exec 160 -- ls -la /tmp/sprint3_agentloop_smoke.py"
-rw-r--r-- 1 root root 32317 Apr 25 12:44 /tmp/sprint3_agentloop_smoke.py

$ ssh pve3 "pct exec 160 -- bash -c 'TIMEOUT=240 RESULTS_JSON=/tmp/sprint3-agentloop-smoke-results-2026-04-25.json python3 /tmp/sprint3_agentloop_smoke.py'"
Target: http://127.0.0.1:8000
Prompts: 25 (FULL 25)
Per-prompt timeout: 240s
... (25 prompts, ~33s avg) ...
[24/25] cap-01       iteration_cap    C5BS PASS  54.22s tc=0 ev=d1r1c0n0m0
[25/25] cap-02       iteration_cap    C5BS PASS  59.40s tc=0 ev=d1r1c0n0m0
TOTAL: 12/25 PASS (48.0%)
Wall time: 837.6s (14.0 min)
By category:
  no_image           5/5   tool_calls_sum=0   describe=0   calling=0   max_iter=0
  passive_image      5/5   tool_calls_sum=0   describe=5   calling=0   max_iter=0
  tool_triggering    0/10  tool_calls_sum=0   describe=10  calling=0   max_iter=0
  multi_iteration    0/3   tool_calls_sum=0   describe=3   calling=0   max_iter=0
  iteration_cap      2/2   tool_calls_sum=0   describe=2   calling=0   max_iter=0
AC results:
  [PASS] AC-3_no_image_>=80pct: 5/5
  [PASS] AC-4_passive_image_>=80pct: 5/5
  [FAIL] AC-5_tool_triggering_>=50pct: 0/10
  [FAIL] AC-6_multi_iter_at_least_one_2plus: no
  [PASS] AC-7_iter_cap_terminates: 2/2
  [PASS] AC-8_status_events_visible: multimodal_describe=20/20; tool_call_calling_event_ok=True
  [PASS] AC-9_no_5xx_errors: 0 5xx error(s) observed
  [PASS] AC-2_25_prompts_executed: 25 prompts (limit=None)
  [PASS] AC-1_harness_end_to_end: 25/25 got HTTP responses
Wrote results JSON to /tmp/sprint3-agentloop-smoke-results-2026-04-25.json

$ ssh pve3 "pct pull 160 /tmp/sprint3-agentloop-smoke-results-2026-04-25.json /tmp/sprint3-agentloop-smoke-results-2026-04-25.json"
$ scp pve3:/tmp/sprint3-agentloop-smoke-results-2026-04-25.json _bmad-output/implementation-artifacts/

$ ssh pve3 "pct exec 160 -- bash -c 'systemctl is-active gemma-hybrid-proxy.service llama-server.service llama-server-26b.service ; docker ps --format \"{{.Names}} {{.Status}}\" | grep -i webui'"
active
active
active
open-webui   Up 57 minutes (healthy)
```

Exit code 1 from the harness is **expected** (it gates non-zero at <50% pass
rate, this run was 48.0%). The non-zero exit reflects the under-target
tool-call rate, not a harness bug.

---

## Proxy log corroboration

Sample agent-loop log lines from `journalctl -u gemma-hybrid-proxy.service`
during the test (formatted for clarity):

```text
chat_completions.auto.streaming_with_status model=gemma4-auto multimodal_blocks={'images': 1, 'audio': 0} ...
chat_completions.auto.forwarding model=gemma4-auto preprocess_latency_ms=26146.13 stream=True total_upstream_calls=2 ...
chat_completions.completed chunks_forwarded=347 duration_ms=40750.66 ... total_upstream_calls=2 ...
```

Every multimodal request showed `total_upstream_calls=2` (1 E4B preprocess +
1 MoE iteration), and there were ZERO `agent_loop.tool_iteration` log lines
across the full 837s run. This corroborates the harness's observation that no
structured tool-call iteration ever fired against production.

---

## Anomalies / edge observations

- **9/15 tool-triggering and multi-iteration prompts hit `finish_reason=length`**
  before they had a chance to emit a tool call. Token budget (`max_tokens=400-600`)
  was insufficient to cover the 26B's `reasoning_content` AND a final tool call.
  Future retry suite should bump `max_tokens` to ≥1024.
- **All 5 no_image prompts hit `finish_reason=length` despite tight `max_tokens`
  (40-120)** — the model's `reasoning_content` consumes the budget before producing
  the answer. Expected per ADR-003 (reasoning_content sequestered) — visible
  answers were still coherent, so behavior_ok=True.
- **0 `_[calling analyze_image...]_` status events** across the entire run —
  directly downstream of the structured-tool-call gap. Story 9.14's status event
  for tool-call detection only fires when `finish_reason="tool_calls"` lands.
- **0 `_[Maximum tool-call iterations reached.]_` events** — the iteration cap
  never fired because no iterations ran. `MAX_TOOL_ITERATIONS=5` is unproven
  against real production traffic; this story can't validate it.
- **Wall-time per multimodal prompt: ~30-55s**, dominated by E4B preprocess
  (~26s) + 1 MoE iteration (~5-30s depending on token budget). Consistent with
  Story 9.14's ~26s preprocess and ~25-50s MoE expectations.
- **Coordination with Story 9.16 (parallel)**: LiteLLM gateway came up on
  `:4000` mid-test. Disjoint port, no impact on `:8000` reachability or test
  results. Confirmed via `ss -tnlp | grep -E ":4000|:8000"` mid-run.

---

## Boundaries respected

- Did NOT modify the deployed proxy or any role.
- Did NOT install ad-hoc packages in CT 160 (stdlib-only urllib/json/socket/re).
- Did NOT touch ct-ai-01 services beyond curl reads of `/health` and HTTP POSTs
  to `/v1/chat/completions`.
- Did NOT score on visual accuracy (1x1 PNG hallucination is expected).
- Did NOT exceed the 30-min wall-time soft limit (14.0 min actual).
- Did NOT spin up a temporary proxy on a different port (this story validates
  the REAL deployed proxy at `:8000`).

---

## Sprint status update

- 9.15 status: `pending` → `completed`
- owner: `unassigned` → `claude-coder`
- completion_date: `2026-04-25`
- evidence: this file (`9-15-agentloop-smoke-evidence.md`)
- ac_coverage: `["AC-1", "AC-2", "AC-3", "AC-4", "AC-7", "AC-8", "AC-9", "AC-10"]`
  (8/10 ACs satisfied; AC-5 and AC-6 documented as failures with root cause)
- sprint_3 stories_completed: `4` → `5`
- sprint_3 notes: 9.15 summary appended

Sprint 3 may proceed to Story 9.17 (EXIT GATE — clients + Prometheus + Grafana
dashboard). The AC-5 / AC-6 failures should be carried into the Story 9.17
exit-gate review and the Sprint 3 retrospective; depending on operator
decision, a follow-up story (Sprint 4 candidate) to either tighten the
`gemma4-auto` system prompt, audit the `gemma4-asf0.jinja` template parsing,
or fall back to Unsloth UD-Q5_K_M for the agent-loop path may be warranted
before declaring agent-loop production-ready.
