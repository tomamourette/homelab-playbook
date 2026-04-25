---
type: story
epic: E2
id: E2-S06
title: "Implement 5 smoke-test scenarios (call-graph, cross-repo, dependency, reindex timing, sustained-load + degradation)"
size: 1.5d
priority: MUST
fr_refs: [FR-CG-006, FR-CG-007, FR-CG-009, FR-CG-011]
nfr_refs: [NFR-PERF-002, NFR-PERF-004, NFR-PERF-005, NFR-AVAIL-001, NFR-FOOTPRINT-002]
adr_refs: [ADR-004, ADR-005, ADR-014]
status: draft
date: 2026-04-25
---

# E2-S06: Implement 5 smoke-test scenarios (call-graph, cross-repo, dependency, reindex timing, sustained-load + degradation)

## User Story

As **tomamourette**, I want **a five-scenario smoke-test suite that exercises GitNexus's key value claims (call-graph traversal, cross-repo edges, dependency walks, auto-reindex responsiveness, and sustained-load + graceful-degradation behaviour) — committed as a runbook with reproducible commands**, so that **the week-1 KPI gate (E2-S08) and any future regression-detection have an objective, repeatable basis for "GitNexus is working correctly" instead of subjective "feels right" judgement**.

## Background and Context

The 5 scenarios in this story map to the value claims that justified ADR-004's adoption decision and to the FRs that require functional + performance + availability evidence: FR-CG-006 (incremental reindex ≤ 30 s), FR-CG-007 (full reindex ≤ 60 s — SHOULD per ADR-014), FR-CG-009 (non-blank GRAPH_REPORT-style artifact — SHOULD per ADR-014), FR-CG-011 (graceful degradation — SHOULD per ADR-014). NFR-PERF-002 (p95 query latency < 500 ms), NFR-AVAIL-001 (no tool-call hang > 3 s), and NFR-FOOTPRINT-002 (< 500 MB sustained over 1 h active session) are also exercised here. The scenarios are committed as a runbook so they can be re-run by E2-S08 (week-1 gate) and at every Sprint retro thereafter.

## Acceptance Criteria

**AC1 — Smoke-test runbook committed.**
- **Given** E2-S05 done (parent-folder topology live + cross-repo edges proven),
- **When** the operator authors `homelab-playbook/docs/runbooks/gitnexus-smoke-tests.md` containing all 5 scenarios with: pre-conditions, exact commands, expected outputs, pass thresholds, and an "evidence captured to" path for each,
- **Then** the runbook is committed AND each scenario can be re-run from the runbook alone (no tribal knowledge / no missing prep steps).

**AC2 — Scenario 1: Call-graph traversal ("find all callers of function X").**
- **Given** the operator picks a real function from `~/workspace/homelab/` with known callers (e.g., a Python helper in `homelab-bootstrap/`),
- **When** the operator runs `npx gitnexus cypher 'MATCH (caller)-[:CALLS]->(callee {name:"<X>"}) RETURN caller.path, caller.line LIMIT 50'` (or via the MCP `cypher` tool in a Claude Code session, OR via the `impact` tool),
- **Then** the result contains at minimum the callers the operator can manually verify via `grep` (≥ 1 expected caller; zero false positives at the top 5 by line number); query latency < 500 ms p95 over 5 repeated runs (NFR-PERF-002); evidence captured to the runbook.

**AC3 — Scenario 2: Cross-repo dependency edge ("show me dependencies between repo A and repo B").**
- **Given** the cross-repo cypher query saved in E2-S05 AC4 evidence note,
- **When** the operator runs that query (or a refined version) AND a Claude Code session asks the model in natural language "find any reference from `homelab-playbook/` Ansible roles to services defined in `homelab/`",
- **Then** the cypher query returns ≥ 1 cross-repo row AND the natural-language session answer cites at minimum one of those rows by file path AND total tokens consumed by the session is recorded (used as a K1 sample in E2-S08); evidence captured.

**AC4 — Scenario 3: Dependency walk ("what does this function depend on?").**
- **Given** the operator picks a representative function/file,
- **When** the operator invokes the GitNexus `context(file_or_symbol)` tool (architecture §7.1) via MCP — e.g., a Claude Code session prompt "use gitnexus context to summarise dependencies of `<symbol or file>`",
- **Then** the response enumerates at least its imports / called functions / referenced symbols AND a non-blank artifact (FR-CG-009) is produced AND the response time end-to-end is < 5 s (per NFR-PERF-002 ceiling for tool-call queries); evidence captured (sample artifact pasted into runbook).

**AC5 — Scenario 4: Auto-reindex responsiveness ("PostToolUse fires within N seconds of commit").**
- **Given** E2-S04 hooks live + AC2/AC3/AC4 prove the daemon is queryable,
- **When** the operator (a) makes a one-line edit in `homelab-playbook/`, (b) `git commit`s via the Claude Code Bash tool so PostToolUse fires, (c) immediately queries GitNexus for the new line via cypher, AND (d) repeats steps a–c 10 times across the 3 sibling repos,
- **Then** in ≥ 9 of 10 trials the change is reflected in the graph within 30 s of commit (FR-CG-006 / NFR-PERF-004); for 1 cold-start case (`npx gitnexus reindex --full` from clean), full reindex completes in ≤ 60 s on `~/workspace/homelab/` (FR-CG-007 / NFR-PERF-005); both results recorded with raw timings in the runbook (used by E2-S08 as the K2 sample).

**AC6 — Scenario 5a: Sustained-load footprint test (1 h active session).**
- **Given** AC5 has passed,
- **When** the operator drives a 1-hour Claude Code working session that includes ≥ 10 commits, ≥ 20 tool calls into GitNexus, AND continuous PreToolUse hook firing,
- **Then** GitNexus daemon RSS (sampled every 5 minutes) stays < 500 MB throughout (NFR-FOOTPRINT-002 sustained-load reaffirmation; complements E2-S02's 24 h passive baseline) AND no tool-call exceeds the 3 s timeout budget (NFR-AVAIL-001 stress-side); evidence captured.

**AC7 — Scenario 5b: Graceful-degradation drill (FR-CG-011).**
- **Given** AC2–AC6 have passed,
- **When** the operator stops the gitnexus daemon (`pkill -f gitnexus`) AND immediately drives a representative Claude Code session that includes (i) a code-related question and (ii) a Bash tool call that triggers the now-orphaned PostToolUse hook,
- **Then** the session completes successfully AND no tool-call hangs > 3 s waiting for gitnexus AND `claude mcp list` reports `gitnexus` as unhealthy AND auto-memory + (if E4 lands first) wiki paths continue to function (per FR-CG-011, NFR-AVAIL-001); the session transcript is saved as evidence; daemon restarted at end of test.

**AC8 — Runbook is the source of truth for E2-S08.**
- **Given** AC1–AC7 are green,
- **When** E2-S08 runs the week-1 KPI scorecard,
- **Then** every metric collected for the gate (K1 token-reduction sample, K2 reindex timings, K4 non-blank artifact check, K6 subjective uplift) traces to a scenario or evidence file from this runbook (no separate ad-hoc collection in E2-S08).

## Implementation Notes

**Reference architecture sections:** §7.1 MCP servers — tool inventory (GitNexus tools used: cypher, impact, context, reindex), §11 G-Latency + AR1 (sustained-load test addresses both), §5.2 Observability (hook log is the K2 source).

**Reference ADRs:** ADR-004 (the value claims being verified), ADR-005 (MCP-first means model must invoke tools — AC4 + AC3 prove this), ADR-014 (FR-CG-007, FR-CG-009, FR-CG-011 are SHOULDs — runbook must distinguish hard-pass from quality-pass on these).

**Concrete commands (selected — full set in runbook):**

```bash
# AC2 — call-graph traversal
TIMEFORMAT='%R'
for i in 1 2 3 4 5; do
  time npx gitnexus cypher 'MATCH (caller)-[:CALLS]->(callee {name:"<symbol>"}) RETURN caller.path LIMIT 50' > /tmp/q$i.txt 2>&1
done
# manual cross-check:
grep -rn '<symbol>(' ~/workspace/homelab/ | head -10

# AC5 — auto-reindex timing (10 trials)
for i in $(seq 1 10); do
  echo "# trial $i $(date -Iseconds)" >> homelab-playbook/_bmad-output/.smoke-test
  cd ~/workspace/homelab/homelab-playbook && git add . && git commit -m "smoke: trial $i"
  T0=$(date +%s)
  while ! npx gitnexus cypher "MATCH (f:File) WHERE f.path CONTAINS '.smoke-test' AND f.indexed_at > timestamp() - 60000 RETURN f LIMIT 1" 2>/dev/null | grep -q .smoke-test; do
    sleep 2
    T1=$(date +%s)
    if [ $((T1 - T0)) -gt 60 ]; then echo "TIMEOUT trial $i"; break; fi
  done
  echo "trial $i: $((T1 - T0))s"
done

# Cold-start full reindex
rm -rf ~/.gitnexus/cache 2>/dev/null
time npx gitnexus reindex --full

# AC6 — sustained-load sampler (run during 1 h session)
while true; do
  ps -o pid,rss,cmd -p $(pgrep -f gitnexus | head -1) | tail -1 >> /tmp/gitnexus-1h-rss.csv
  sleep 300
done &

# AC7 — degradation drill
pkill -f gitnexus
# in fresh Claude Code session: ask "what is 2+2"; ask "read README.md"; do `git status`
# expect: no hang > 3s; mcp list shows unhealthy
claude mcp list | grep gitnexus
```

**Runbook file path:** `homelab-playbook/docs/runbooks/gitnexus-smoke-tests.md`. Each scenario gets its own H2 section with: Goal, Preconditions, Commands, Expected output, Pass threshold, Evidence path.

**Evidence captures:** raw timings → `~/workspace/homelab/_export/gitnexus-smoke-week1.csv`; sample artifacts → embedded in the runbook itself; degradation transcript → committed under `homelab-playbook/docs/decisions/gitnexus-degradation-evidence.md`.

## Test Plan

**Pre-state:**
- E2-S05 done; cross-repo Cypher query saved.
- E2-S04 hooks live.
- E2-S02 footprint baseline.
- 1 h block reserved on operator's calendar for AC6.

**Action sequence:**
1. Author runbook skeleton (AC1).
2. Execute Scenario 1 (AC2); record evidence.
3. Execute Scenario 2 (AC3); record token usage from a real Claude Code session.
4. Execute Scenario 3 (AC4); paste sample artifact into runbook.
5. Execute Scenario 4 (AC5) — 10 incremental + 1 cold-start full.
6. Execute Scenario 5a (AC6) — 1 h sustained session with sampler.
7. Execute Scenario 5b (AC7) — degradation drill.
8. Verify runbook covers all evidence sources for E2-S08 (AC8).
9. Commit runbook + evidence files.

**Post-state checks:**
- Runbook committed and self-contained.
- All 5 scenarios PASS at their stated thresholds.
- Evidence files referenced from runbook.
- Degradation drill transcript shows session-continuity.

**Rollback:**
- Smoke tests have no persistent side effects beyond the test commits in the homelab repos. If a tester wants to clean up, `git revert` each `smoke: trial $i` commit (or accept them as harmless empties).
- Degradation drill restarts daemon at end; no rollback needed.

## Dependencies

- **Blocked by:** E2-S05 (parent-folder topology + cross-repo edges live).
- **Blocks:** E2-S08 (week-1 KPI gate sources its evidence from this runbook).

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| AC2 result has false positives or missing callers — call-graph quality below expectations. | Med | High — would undermine ADR-004's value claim. | Document precision/recall delta in runbook; if recall < 80% on the operator's spot-check, file an architecture review (the assumption was AST-first parsers handle Python + Ansible-Jinja + bash adequately). |
| Cold-start reindex > 60 s (FR-CG-007 SHOULD breached). | Med | Low — SHOULD per ADR-014. | Document the actual time; if 60–120 s, accept as quality-pass; if > 120 s, file a performance investigation backlog ticket. |
| 1 h sustained-load test reveals memory growth pattern (RSS rising linearly). | Low | Med — AR1 reopens. | If RSS at T+1h is > 1.5× T+0, escalate to architecture review of GitNexus daemon memory model; AR1 reopens with a leak hypothesis. |
| Degradation drill fails because PostToolUse hook hangs > 3 s when daemon is gone. | Med | Med — FR-CG-011 SHOULD breached. | Document the hang time; if > 3 s, propose a hook-side timeout wrapper (`timeout 3 npx gitnexus ...`) as a Sprint 2 follow-up; recheck after E2-S08. |
| 1 h session block conflicts with operator's calendar. | Med | Low — schedule slip. | Schedule via /loop or a calendar block; AC6 sampler runs in the background, so the operator can do real work during the hour. |

## Definition of Done

- [ ] AC1–AC8 all green.
- [ ] `homelab-playbook/docs/runbooks/gitnexus-smoke-tests.md` committed.
- [ ] All 5 scenario evidence files exist (paths referenced from runbook).
- [ ] Degradation drill transcript committed.
- [ ] Sustained-load CSV captured.
- [ ] Story status updated to `done`; OMEGA `omega_store(...)` records "smoke runbook = source of truth for KPI gate".
