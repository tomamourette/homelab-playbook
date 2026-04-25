---
type: story
epic: E2
id: E2-S08
title: "Week-1 decision-gate KPI scorecard (proceed / migrate / revert)"
size: 0.5d
priority: MUST
fr_refs: [FR-CG-008]
nfr_refs: [NFR-PERF-001, NFR-FOOTPRINT-002]
adr_refs: [ADR-004, ADR-014]
status: draft
date: 2026-04-25
---

# E2-S08: Week-1 decision-gate KPI scorecard (proceed / migrate / revert)

## User Story

As **tomamourette**, I want **a one-page scorecard scoring 4-of-6 KPIs (K1, K2, K3, K4, K6 — K5 is Graphiti-only) with green-amber-red verdicts derived from the E2-S06 smoke-test runbook + week-1 hook logs**, so that **at the end of Sprint 2 I have an objective gate decision (proceed-to-E3, migrate-to-CodeGraphContext, or revert-to-no-code-graph) that closes Epic E2 and resolves the epic-level acceptance criterion #8 in epics.md §4.4**.

## Background and Context

Brief §6 / PRD §7 / epics.md §4.4 AC8 collectively define the 4-of-6 KPI gate at week 1. The KPIs are:
- **K1** Token-reduction on cross-repo questions ≥ 5× (FR-CG-008).
- **K2** Reindex timing — incremental ≤ 30 s, full ≤ 60 s (NFR-PERF-004/005, FR-CG-006/007).
- **K3** Spend — should be 0 (GitNexus is local-only, no LLM calls; FR-CG-012).
- **K4** Non-blank artifact — every reindex produces a non-blank GRAPH_REPORT-style summary (FR-CG-009 — SHOULD per ADR-014).
- **K6** Subjective uplift — operator-tagged "did GitNexus save me a re-read" on ≥ 60% of in-window sessions.

**K5 (Graphiti first-shot recall) is excluded from the E2 gate** — Graphiti isn't deployed until E3. EQ2 in epics.md §9 explicitly tasks Phase 4b with fixing the green-amber-red rubric and the K6 "noticeable" definition; this story does that.

## Acceptance Criteria

**AC1 — Scorecard template instantiated.**
- **Given** E2-S06 runbook + evidence files exist AND E2-S07 export wrapper proves FR-CG-010,
- **When** the operator opens `homelab-playbook/docs/decisions/gitnexus-week1-scorecard.md` (new file),
- **Then** the file contains the 5 KPI rows (K1, K2, K3, K4, K6), each with: definition, measurement source (pointer to E2-S06 runbook section or hook log path), pass threshold, green-amber-red rubric, and the actual measured value.

**AC2 — Green-amber-red rubric defined per KPI (closes EQ2).**
- **Given** AC1 has begun,
- **When** the operator commits the rubric block in the scorecard,
- **Then** each KPI has explicit thresholds:
  - **K1 token-reduction:** GREEN ≥ 5× / AMBER 3×–5× / RED < 3× (median over 3 cross-repo questions).
  - **K2 reindex timing:** GREEN ≤ 30 s incremental + ≤ 60 s full / AMBER ≤ 45 s + ≤ 90 s / RED beyond AMBER.
  - **K3 spend:** GREEN = $0.00 (architectural promise) / AMBER any unexpected charge < $0.10 / RED any pattern of charges (would indicate FR-CG-012 violation, escalates immediately).
  - **K4 non-blank artifact:** GREEN 100% non-blank / AMBER ≥ 90% / RED < 90%.
  - **K6 subjective uplift:** GREEN ≥ 60% sessions tagged "yes, saved me a re-read" / AMBER 40–60% / RED < 40%; the operator-facing definition "yes" = "GitNexus tool result eliminated at least one grep + Read cycle that I would otherwise have done"; "no" = "I would have answered as fast or faster without it"; tracked in `~/workspace/homelab/_export/gitnexus-k6-tally.csv` (one row per session over the 7-day window, columns `date`, `session_id_or_topic`, `verdict`, `note`).

**AC3 — K1 sample measured on 3 representative cross-repo questions.**
- **Given** E2-S06 AC3 produced one cross-repo Cypher query result + Claude Code session token-usage data,
- **When** the operator picks 2 additional representative cross-repo questions (e.g., "list every Ansible role in homelab-playbook that targets a service defined in homelab/", "find every CI script that references a path under homelab-bootstrap/") AND runs each (a) WITH GitNexus and (b) baseline grep+Read — capturing input tokens for each via Claude Code's session metadata,
- **Then** for each of the 3 questions, `tokens_baseline / tokens_gitnexus` ≥ 5 (median over 3 = K1 GREEN); raw counts pasted into the scorecard.

**AC4 — K2 timings extracted from hook logs.**
- **Given** E2-S06 AC5 ran 10 incremental + 1 cold-start trial,
- **When** the operator extracts wall-clock per trial from `~/workspace/homelab/_export/gitnexus-smoke-week1.csv` (or runbook timings),
- **Then** at least 9 of 10 incremental trials are ≤ 30 s AND the cold-start full reindex is ≤ 60 s; values pasted into the scorecard.

**AC5 — K3 spend reconciled.**
- **Given** GitNexus is local-only with zero LLM calls,
- **When** the operator pulls the operator's OpenAI + Anthropic billing summaries for the 7-day pilot window AND attributes costs (most should be Graphiti-attributable in E3, NOT GitNexus),
- **Then** GitNexus-attributable spend is exactly $0.00 (no LLM usage tied to GitNexus daemon activity); recorded as K3 GREEN. Any non-zero figure triggers FR-CG-012 root-cause investigation (which is itself an architectural-violation-class incident, not a scorecard amber).

**AC6 — K4 non-blank-artifact tally.**
- **Given** every PostToolUse-on-commit hook fired during the 7-day window writes a log line / artifact (per FR-CG-009),
- **When** the operator runs a one-liner counting non-blank entries — e.g., `grep -c 'reindex.*ok' ~/.claude/logs/hooks/*.log` and divides by total commit-trigger count,
- **Then** the percentage non-blank is recorded; if ≥ 90% the K4 rubric awards at minimum AMBER (SHOULD per ADR-014); if 100% it's GREEN.

**AC7 — K6 tally captured over the full 7-day window.**
- **Given** the operator has been working in Claude Code daily during Sprint 2,
- **When** the operator reviews the K6 tally CSV — one row per Claude Code session in the 7-day window with verdict yes/no and a one-line note,
- **Then** the CSV has ≥ 14 rows (~2 sessions/day × 7 days) AND the GREEN/AMBER/RED verdict is computed from the percent of "yes" rows.

**AC8 — G-Latency check (NFR-PERF-001).**
- **Given** E2-S04 AC5 measured pre-hook vs post-hook session-start latency,
- **When** the operator re-measures the 5-sample median at end of week 1 (after a week of real workload), AND compares to the post-E1 baseline,
- **Then** the additional latency is < 1 s on the median (NFR-PERF-001) — recorded as a G-Latency check pass / fail. (G-Latency is a brief §6 hard gate.)

**AC9 — AR1 footprint check final.**
- **Given** E2-S02 captured the 24 h baseline AND E2-S06 AC6 captured the 1 h sustained-load shape,
- **When** the operator runs `ps -o pid,rss,cmd -C node,gitnexus | grep gitnexus` at end of week 1 AND samples the 7-day max from any continuous logs available,
- **Then** GitNexus daemon RSS at end of week ≤ 500 MB AND 7-day max ≤ 500 MB; recorded in scorecard. (AR1 stays closed.)

**AC10 — Decision recorded.**
- **Given** AC1–AC9 are green-or-amber-or-red as measured,
- **When** the operator writes the scorecard's verdict block,
- **Then** the verdict is one of:
  - **PROCEED** (≥ 4 of 5 KPIs GREEN AND G-Latency clean AND AR1 closed) → continue to E3 / E4 with no GitNexus changes;
  - **PROCEED-WITH-FOLLOWUP** (≥ 4 of 5 KPIs GREEN-or-AMBER AND no RED) → continue but file a backlog ticket per amber finding;
  - **MIGRATE** (any RED AND issue is not resolvable in 2 days) → exercise the GitNexus exit ramp (E2-S07's runbook); halt further GitNexus stories;
  - **REVERT** (G-Latency RED OR AR1 reopens) → `npm uninstall -g gitnexus` + `claude mcp remove gitnexus` + restore settings.json from backup; document in retro.

**AC11 — Sprint 2 retro entry written.**
- **Given** AC10 has produced a verdict,
- **When** the operator authors a 1-paragraph entry in `homelab-playbook/docs/decisions/sprint-2-retro.md` (or appends to an existing retro),
- **Then** the entry summarises the verdict + key amber/red findings + next-sprint follow-ups.

## Implementation Notes

**Reference architecture sections:** §11 AR1 (footprint final check), §11 G-Latency note, §5.2 Observability table (KPI sources).

**Reference ADRs:** ADR-004 (the gate decides whether the adoption holds), ADR-014 (clarifies which KPIs are MUST vs SHOULD; ADR-014 already adjusted FR-CG-005, FR-CG-007, FR-CG-009, FR-CG-011 to SHOULD/COULD — the rubric reflects this).

**Reference epics.md / EQs:** epics.md §4.4 AC8 + §9 EQ2 (this story closes both — AC8 is the gate rubric definition; EQ2 demands the green-amber-red and K6 definition be fixed before the gate evaluates).

**Concrete scorecard template** (paste into the new file):

```markdown
# GitNexus Week-1 Scorecard

Date: <YYYY-MM-DD>
Window: <start-date> → <end-date> (7 days post-E2-S03 deploy)

## Verdict: <PROCEED | PROCEED-WITH-FOLLOWUP | MIGRATE | REVERT>

## KPI table

| KPI | Definition | Source | Threshold | Measured | Verdict |
|---|---|---|---|---|---|
| K1 token-reduction | tokens_baseline / tokens_gitnexus on cross-repo Q | E2-S06 §AC3 + 2 additional | ≥ 5× GREEN / 3-5× AMBER / < 3× RED | <X×> | <G/A/R> |
| K2 reindex timing | incremental p95 + full cold | E2-S06 §AC5 + smoke CSV | ≤ 30s + ≤ 60s GREEN | <Xs/Ys> | <G/A/R> |
| K3 spend | GitNexus-attributable LLM spend | OpenAI + Anthropic billing | $0.00 GREEN | <$X> | <G/A/R> |
| K4 non-blank artifact | % of PostToolUse runs producing non-blank | hook log grep | 100% GREEN / ≥ 90% AMBER | <X%> | <G/A/R> |
| K6 subjective uplift | "yes saved me a re-read" tally | k6-tally.csv | ≥ 60% GREEN | <X% over Y rows> | <G/A/R> |

## Hard gates

- G-Latency (< 1 s session-start overhead): <PASS / FAIL> — measured <Xs>
- AR1 footprint (< 500 MB sustained): <CLOSED / REOPENED> — 7-day max <Y MB>

## Amber/red findings + follow-up tickets

- ...
```

**K6 tally CSV path:** `~/workspace/homelab/_export/gitnexus-k6-tally.csv`. Columns: `date,session_id_or_topic,verdict,note`. Operator fills daily during Sprint 2.

**Scorecard file path:** `homelab-playbook/docs/decisions/gitnexus-week1-scorecard.md`.

## Test Plan

**Pre-state:**
- E2-S01..E2-S07 all done.
- E2-S06 runbook executed and evidence files captured.
- 7-day pilot window has elapsed since E2-S03 deploy (the latency baseline reference).

**Action sequence:**
1. Instantiate scorecard with rubric block (AC1, AC2).
2. Run K1 sample on 3 cross-repo questions (AC3); paste numbers.
3. Extract K2 timings (AC4) from E2-S06 evidence.
4. Reconcile K3 spend (AC5).
5. Tally K4 (AC6).
6. Compile K6 tally (AC7).
7. Re-measure G-Latency (AC8).
8. Final AR1 footprint check (AC9).
9. Write verdict (AC10).
10. Append retro entry (AC11).

**Post-state checks:**
- Scorecard file committed.
- Verdict is one of the four documented outcomes.
- K6 tally CSV has ≥ 14 rows.
- Retro entry references scorecard.

**Rollback:**
- If verdict = REVERT: execute the rollback chain — `npm uninstall -g gitnexus` + `claude mcp remove gitnexus` + restore `~/.claude/settings.json` from `*.pre-gitnexus.bak` + `git revert` the install-script + scripts/gitnexus-export.sh commits. Wall-time: ≤ 30 minutes.
- If verdict = MIGRATE: do not roll back GitNexus immediately; run the export wrapper (E2-S07) one final time, then schedule the migration in Sprint 3+.

## Dependencies

- **Blocked by:** E2-S01 through E2-S07 (every previous story produces evidence consumed here).
- **Blocks:** Sprint 2 close; E3 is unaffected by E2 verdict per epics.md §4.5 (pilots are independent), but a REVERT verdict is a strong signal to revisit ADR-004 before E4's product-level gate.

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| K6 tally undercounted (operator forgot to log sessions). | Med | Med — verdict is unreliable. | Set a daily reminder during Sprint 2 (calendar block or /loop schedule); in retro, document any day where tally < 1 row. |
| K1 questions cherry-picked to favour GitNexus. | Med | High — invalid gate. | Author the 3 questions in advance (commit them at start of Sprint 2 in the scorecard skeleton), don't pick after seeing GitNexus's behaviour. |
| Anthropic-side token usage attribution conflated with non-Context-Stack work. | High | Low — K3 noise. | K3 is GitNexus-only, which has zero LLM calls — so the answer is structurally $0. Any non-zero figure is an architectural violation, not a measurement artefact. |
| AR1 reopens at end of week 1 despite passing E2-S02 baseline. | Low | High — REVERT verdict. | The decision tree explicitly handles this via REVERT; ADR-004 reversal is invoked. |
| Verdict = MIGRATE but E2-S07 export wrapper isn't fully functional yet. | Low | High — exit ramp gap. | E2-S07 is a hard predecessor; without it, story HALTS until export wrapper exists. |

## Definition of Done

- [ ] AC1–AC11 all green or, where measurement returns AMBER/RED, the verdict (AC10) explicitly captures the finding and follow-up tickets are filed.
- [ ] `homelab-playbook/docs/decisions/gitnexus-week1-scorecard.md` committed with verdict.
- [ ] `homelab-playbook/docs/decisions/sprint-2-retro.md` (new or appended) references the scorecard.
- [ ] If verdict = REVERT or MIGRATE: rollback / migration is scheduled (or executed) per AC10.
- [ ] EQ2 (epics.md §9) marked closed in the EQ tracker.
- [ ] Story status updated to `done`; OMEGA `omega_store(...)` records the verdict + which KPIs were RED if any.
