---
type: story
epic: E4
id: E4-S11
title: "Run product-level 4-of-6 KPI scorecard at week 4 + G-Latency + G-Rollback gates"
size: 0.5d
priority: MUST
fr_refs: [FR-OBS-004, FR-DEP-006, FR-DEP-007]
adr_refs: [ADR-013, ADR-014]
status: draft
date: 2026-04-25
---

# E4-S11: Run product-level 4-of-6 KPI scorecard at week 4 + G-Latency + G-Rollback gates

## User Story

As **tomamourette** (homelab operator), I want **the product-level KPI scorecard computed by aggregating the four weekly digests from E4-S09 (covering Sprint 4 weeks 1-4 of the pilot), the G-Latency hard-gate measured against the pre-deploy 5-session baseline (NFR-PERF-001), and the G-Rollback hard-gate confirmed via E4-S08 evidence**, so that **I have an evidence-backed accept/migrate/revert decision per PRD §11 / brief §6: ≥ 4-of-6 KPIs green AND G-Latency clean AND G-Rollback validated → product accept; otherwise → migrate per the failing tier's exit ramp (E4-S10) or revert per FR-DEP-007**.

## Background and Context

PRD §7 + §11 + brief §6 set the bar: **4-of-6 KPI scorecard green at week 4** is the product accept condition; **G-Latency** (NFR-PERF-001) and **G-Rollback** (FR-DEP-007) are independent hard gates outside the scorecard. Per ADR-014, the recalibrated MoSCoW means this scorecard inherits the SHOULD/COULD bars (e.g., FR-MEM-007/K5 is SHOULD; if it falls just short, K5 still counts as amber-not-red and contributes to the 4-of-6 in nuanced ways).

This story does NOT generate new data — it **reads from**:
- The four E4-S09 weekly digests (Sprint 4 weeks 1-4)
- The E4-S08 G-Latency CSV (pre-deploy + post-deploy session-start times)
- The E4-S08 rollback wall-time evidence
- The E4-S06 LiteLLM gate result (if Phase 4 active)
- `wiki/_session-log.md` cumulative facts read across E4-S02 seeds (FR-WIKI-006)

It produces ONE artifact: `homelab-playbook/wiki/decisions/product-scorecard-2026-week4.md` — the operator's go/no-go decision record.

## Acceptance Criteria

### AC1: Four weekly digests exist for Sprint 4 weeks 1-4

- **Given** E4-S09 has been run weekly through Sprint 4
- **When** I run `ls homelab-playbook/wiki/decisions/weekly-digest-*.md | wc -l`
- **Then** there are at least 4 weekly digest files covering the 4-week pilot window; each has a status row table populated (no `[TBD]` cells); each passes wiki-lint

### AC2: KPI scorecard aggregates K1-K6 over the 4-week window

- **Given** AC1 holds
- **When** I author `homelab-playbook/wiki/decisions/product-scorecard-2026-week4.md` with valid frontmatter (slug=`product-scorecard-2026-week4`, category=`decisions`, related_frs=[FR-OBS-004], related_adrs=[ADR-014])
- **Then** the body contains one master table with 6 rows (K1-K6), each row showing: 4-week aggregate value (or trend), threshold, final-status (Green / Amber / Red), and a 1-line "evidence pointer" (e.g., "see weekly-digest-2026-W17 §K3, weekly-digest-2026-W18 §K3, ...")

### AC3: 4-of-6 green threshold is computed and the gate decision is explicit

- **Given** AC2 holds
- **When** I read the scorecard
- **Then** a "Gate decision" section reports: `green_count=<N>`; `gate=PASS` if `N ≥ 4`, else `gate=FAIL`; if FAIL, names exactly which KPIs failed and references the relevant exit-ramp page (E4-S10 `exit-ramps`) for the affected tier

### AC4: G-Latency gate measured against pre-deploy baseline

- **Given** E4-S08 captured `tests/glatency-pre-deploy-<TS>.csv` and `tests/glatency-post-deploy-<TS>.csv`
- **When** I compute mean delta (`avg(post) - avg(pre)`)
- **Then** the scorecard reports the delta in seconds; status = `Green` if delta ≤ 1.0 s (NFR-PERF-001 bound), `Red` if > 1.0 s; if RED, this is a **gate-blocking** failure regardless of K1-K6 outcome (per brief §6 hard gate)

### AC5: G-Rollback gate confirmed via E4-S08 evidence

- **Given** E4-S08 ran the rollback drill (AC6-AC10) with wall-time recorded
- **When** I look at E4-S08's deliverables
- **Then** the scorecard captures: rollback validated = YES, wall-time = X minutes, AC8 diff = clean, AC9 re-deploy = succeeded; status = `Green` if all four hold, `Red` if any fail; gate-blocking failure if Red (brief §6)

### AC6: Phase 4 LiteLLM bridge state is reported in scorecard

- **Given** E4-S05 + E4-S06 ran one of three paths (active+passed / active+failed-and-reverted / deferred)
- **When** I read the scorecard
- **Then** a "Phase 4 status" section explicitly reports: `bridge_active=YES/NO`, `validation_pass_rate=<PCT>%/N\A`, `cost_neutrality=Green/Amber/Red/N\A`; if `bridge_active=YES`, NFR-COST-003 is computed from E4-S09 weekly digests; if `bridge_active=NO` and Phase 4 deferred, that's documented and DOES NOT count against the gate (FR-LLM-007 explicit)

### AC7: FR-WIKI-006 (3 seeds × 3 sessions) is computed and reported

- **Given** E4-S02's `_session-log.md` accumulates session-tagged seed reads
- **When** I tally per-seed read counts at week 4
- **Then** the scorecard reports: number of seeds with ≥ 3 distinct sessions reading them; status = `Green` if ≥ 3 seeds hit, `Amber` if 2 seeds hit (per ADR-014 SHOULD relaxation), `Red` if < 2

### AC8: Resource footprint thresholds checked

- **Given** weekly digests have FalkorDB RSS and GitNexus daemon RSS columns (E4-S09 AC2)
- **When** I read the 4-week max values
- **Then** scorecard reports: FalkorDB peak RSS over 4 weeks (Green if < 200 MB / NFR-FOOTPRINT-001); GitNexus daemon peak RSS over 4 weeks (Green if < 500 MB / NFR-FOOTPRINT-002)

### AC9: Decision record is explicit and machine-readable

- **Given** AC2-AC8 are populated
- **When** I read the scorecard's terminal section "Decision"
- **Then** it states one of: `accept` (all gates green; product done; promote off ct-dev-homelab), `accept_with_gaps` (4-of-6 green BUT some Ambers; promote with backlog tickets for follow-up), `migrate` (≥ 1 KPI Red AND not gate-blocking; trigger the failing tier's exit ramp), `revert` (G-Latency or G-Rollback Red; do NOT promote; revert via FR-DEP-007); the decision is the input to E4-S12 retro

### AC10: ntfy push delivered to operator on scorecard completion

- **Given** the scorecard is committed
- **When** I run `bash homelab-playbook/scripts/notify-scorecard.sh homelab-playbook/wiki/decisions/product-scorecard-2026-week4.md`
- **Then** an ntfy push is sent to `http://ct101.tail-scale.ts.net/graphiti-alerts` with title `Context Stack — week 4 scorecard` and body containing the green-count + decision; this is the explicit operator-acknowledgment moment

### AC11: Scorecard cross-links the per-week digests, exit ramps, and the query hierarchy

- **Given** AC2 holds
- **When** I read the body
- **Then** the Cross-references section contains slug links to: each weekly-digest, `exit-ramps`, `context-stack-query-hierarchy`, `ai-dev-context-stack`, `hybrid-gemma-serving`; all resolve via wiki-lint

### AC12: ADR-014 SHOULD-bar validation: was the recalibration correct?

- **Given** the 4-week pilot ran with ADR-014's MoSCoW redistribution
- **When** I write the scorecard's "Notes" section
- **Then** it reports operator's verdict on whether the SHOULD/MUST split worked: did any SHOULD that ought to have been MUST cause a regression? did any MUST that ought to have been SHOULD over-rigid the sprint? (this is direct input to E4-S12 retro per ADR-014's own §Validation criterion)

## Implementation Notes

### Scorecard content (sketch)

`homelab-playbook/wiki/decisions/product-scorecard-2026-week4.md`:

```markdown
---
title: "Context Stack — product KPI scorecard week 4"
slug: product-scorecard-2026-week4
category: decisions
last_reviewed: 2026-04-25
owner: tomamourette
related_pages:
  - weekly-digest-2026-W17
  - weekly-digest-2026-W18
  - weekly-digest-2026-W19
  - weekly-digest-2026-W20
  - exit-ramps
  - context-stack-query-hierarchy
  - hybrid-gemma-serving
  - ai-dev-context-stack
related_frs: [FR-OBS-004, FR-DEP-006, FR-DEP-007]
related_adrs: [ADR-014, ADR-013]
status: stable
supersedes: []
superseded_by: null
---

## Summary

4-week pilot of Context Stack on ct-dev-homelab and ct-ai-01. KPI scorecard:
[N]/6 green. G-Latency: [Green/Red]. G-Rollback: [Green/Red]. Decision:
**[accept / accept_with_gaps / migrate / revert]**.

## Context

Per PRD §7 + §11 + brief §6: 4-of-6 KPI green at week 4 = product accept;
G-Latency + G-Rollback are independent hard gates. ADR-014 recalibrated
MoSCoW; this scorecard validates that recalibration as part of FR-OBS-004
weekly retro discipline.

## Decision (KPI scorecard — 4-week aggregate)

| KPI | 4-week value | Threshold | Status | Evidence |
|---|---|---|---|---|
| K1 token reduction | [aggregate from 12 Q&A across 4 weekly digests] | ≥ 5× | [G/A/R] | weekly-digest-{W17..W20} §K1 |
| K2 reindex time (incr.) | [worst case] | ≤ 30 s | [G/A/R] | weekly-digest-{W17..W20} §K2 |
| K3 spend (monthly run-rate) | [4-week sum × 13/12] | < $20/mo | [G/A/R] | weekly-digest-{W17..W20} §K3, /var/log/graphiti-cost-cap.log |
| K4 facts/week | [avg of weeks 2-4] | ≥ 25 | [G/A/R] | weekly-digest-{W17..W20} §K4 |
| K5 good-catch tally | [sum over 4 weeks] | ≥ 3 | [G/A/R] | weekly-digest-{W17..W20} §K5 |
| K6 subjective uplift | [final week verdict] | "noticeable" | [G/A/R] | weekly-digest-2026-W20 §K6 |
| **green count** | **[N] / 6** | **≥ 4** | **[gate=PASS/FAIL]** | this row |

## Hard gates

| Gate | Value | Threshold | Status |
|---|---|---|---|
| G-Latency (session-start delta) | [seconds] | ≤ 1.0 s | [Green/Red] |
| G-Rollback (E4-S08 evidence) | YES/NO + wall-time | YES + ≤ 1 day | [Green/Red] |

## Phase 4 status

| Item | Value |
|---|---|
| LiteLLM bridge active? | [YES/NO] |
| Validation pass rate | [PCT% / N/A] |
| Cost-neutrality (NFR-COST-003) | [Green/Amber/Red/N/A] |

## Coverage signals

| Signal | Value | Threshold | Status |
|---|---|---|---|
| FR-WIKI-006 (3×3 seeds) | [seeds with ≥ 3 sessions] | ≥ 3 of 5 | [G/A/R] |
| FalkorDB peak RSS | [MB] | < 200 MB | [G/A/R] |
| GitNexus peak RSS | [MB] | < 500 MB | [G/A/R] |

## Decision

**[accept | accept_with_gaps | migrate | revert]**

[1-paragraph rationale citing the specific KPI/gate values that drove the
choice. If `migrate` or `revert`, names the next step from E4-S10 exit
ramps.]

## Cross-references

- [Weekly digest W17](weekly-digest-2026-W17)
- [Weekly digest W18](weekly-digest-2026-W18)
- [Weekly digest W19](weekly-digest-2026-W19)
- [Weekly digest W20](weekly-digest-2026-W20)
- [Exit ramps](exit-ramps)
- [Query hierarchy](context-stack-query-hierarchy)
- [Hybrid Gemma serving](hybrid-gemma-serving)
- [ai-dev-context-stack](ai-dev-context-stack)

## Notes (ADR-014 validation)

Was the SHOULD/MUST recalibration correct?
- [verdict per category from ADR-014's downgrades]

Backlog from this scorecard:
- [list of items that need attention regardless of decision]
```

### `homelab-playbook/scripts/notify-scorecard.sh` (sketch)

```bash
#!/usr/bin/env bash
set -euo pipefail
SC_PATH="${1:?path-to-scorecard.md}"
[ -f "$SC_PATH" ] || { echo "FAIL: $SC_PATH not found"; exit 1; }
DECISION=$(grep -E '^\*\*\[' "$SC_PATH" | head -1 | sed 's/\*//g; s/^\[//; s/\]$//')
GREEN=$(grep -E '^\| \*\*green count\*\*' "$SC_PATH" | grep -oE '[0-9]+ / 6' | head -1)
GATE=$(grep -E '^\| \*\*green count\*\*' "$SC_PATH" | grep -oE 'PASS|FAIL' | head -1)
GLATENCY=$(grep -E '^\| G-Latency' "$SC_PATH" | awk -F'\\| ' '{print $5}' | tr -d '][')
GROLLBACK=$(grep -E '^\| G-Rollback' "$SC_PATH" | awk -F'\\| ' '{print $5}' | tr -d '][')

curl -fsSL -m 10 \
  -d "Scorecard: ${GREEN} green; gate=${GATE}; G-Latency=${GLATENCY}; G-Rollback=${GROLLBACK}; decision=${DECISION}" \
  -H "Title: Context Stack — week 4 scorecard" \
  -H "Priority: high" \
  http://ct101.tail-scale.ts.net/graphiti-alerts
```

### Computing 4-week aggregates

For each KPI, the aggregation rule:
- **K1**: median of 4 weekly values (operator picks 3 cross-repo Qs/week × 4 weeks = 12 sample points)
- **K2**: worst-case (P95 across the 4 weeks)
- **K3**: weekly run-rate × 13/12 ≈ monthly rate; or actual monthly billing if billing cycle aligned
- **K4**: average of weeks 2-4 (week 1 is ramp-up; aligns with FR-MEM-008 "≥ 25 facts/week after week 2")
- **K5**: cumulative count over 4 weeks (FR-OBS-005 target = ≥ 3)
- **K6**: terminal (week 4) verdict, with "trend" annotation if the operator's subjective rating changed mid-pilot

These rules go in the scorecard's Notes section as the "How aggregates were computed" sub-paragraph.

### NOT in scope

- Does NOT run any new measurements (consumes the 4 weekly digests + E4-S08 evidence).
- Does NOT change the deploy state (the deploy stays as-is per E4-S08 final state).
- Does NOT decide whether to promote to other containers — only whether the product is "accept" / "migrate" / "revert" against the spec.
- Does NOT do retro analysis (E4-S12).

## Test Plan

**Pre-flight:**
```bash
ls homelab-playbook/wiki/decisions/weekly-digest-*.md | wc -l   # ≥ 4
test -f tests/glatency-pre-deploy-*.csv && test -f tests/glatency-post-deploy-*.csv
grep -c "ROLLBACK_END" /tmp/e4-s08-rollback-*.log   # ≥ 1 (rollback ran)
```

**Author scorecard (Edit/Write):**
- `homelab-playbook/wiki/decisions/product-scorecard-2026-week4.md` per AC2-AC9
- `homelab-playbook/scripts/notify-scorecard.sh` per Implementation Notes

**Compute aggregates:**
```bash
# K1 — manual aggregation from weekly digests
grep "K1 token" homelab-playbook/wiki/decisions/weekly-digest-*.md
# K2 — worst-case incremental reindex
grep "K2 reindex" homelab-playbook/wiki/decisions/weekly-digest-*.md
# K3 — sum spend; estimate monthly rate
awk '/K3 spend/ {print $0}' homelab-playbook/wiki/decisions/weekly-digest-*.md
# K4 — average for weeks 2-4
grep "K4 facts/week" homelab-playbook/wiki/decisions/weekly-digest-{W18,W19,W20}.md
# K5 — cumulative
grep "K5 good-catch" homelab-playbook/wiki/decisions/weekly-digest-*.md
# K6 — week 4 terminal
grep "K6 subjective" homelab-playbook/wiki/decisions/weekly-digest-W20.md

# G-Latency
awk -F, 'BEGIN { pre=0; post=0; pn=0; ptn=0 }
         FILENAME~/pre/  { pre+=$1; pn++ }
         FILENAME~/post/ { post+=$1; ptn++ }
         END { print "delta:", (post/ptn) - (pre/pn) }' tests/glatency-*.csv

# FR-WIKI-006
for slug in network-tailscale-policy pve-cluster-topology decommission-context-stack-phase-1 hybrid-gemma-serving ai-dev-context-stack; do
  c=$(grep -c "| $slug |" homelab-playbook/wiki/_session-log.md)
  echo "$slug: $c"
done | tee /tmp/wiki006-tally.txt
```

**AC verification:**
```bash
bash homelab-playbook/scripts/wiki-lint.sh   # AC2
yq '.related_pages, .related_frs, .related_adrs' homelab-playbook/wiki/decisions/product-scorecard-2026-week4.md
grep -E '^\| K[1-6]' homelab-playbook/wiki/decisions/product-scorecard-2026-week4.md   # 6 KPI rows
grep -E '^green_count|^gate=' homelab-playbook/wiki/decisions/product-scorecard-2026-week4.md   # AC3
grep -E '^\| G-Latency' homelab-playbook/wiki/decisions/product-scorecard-2026-week4.md   # AC4
grep -E '^\| G-Rollback' homelab-playbook/wiki/decisions/product-scorecard-2026-week4.md   # AC5
grep -E '^Phase 4' homelab-playbook/wiki/decisions/product-scorecard-2026-week4.md          # AC6
grep -E '^FR-WIKI-006' homelab-playbook/wiki/decisions/product-scorecard-2026-week4.md      # AC7
grep -E '^\*\*\[(accept|accept_with_gaps|migrate|revert)\]\*\*' homelab-playbook/wiki/decisions/product-scorecard-2026-week4.md   # AC9

# AC10 — fire ntfy
bash homelab-playbook/scripts/notify-scorecard.sh homelab-playbook/wiki/decisions/product-scorecard-2026-week4.md
# Operator confirms phone receives the push

# AC11
bash homelab-playbook/scripts/wiki-lint.sh   # all cross-refs resolve
# AC12
grep -A 5 'ADR-014 validation' homelab-playbook/wiki/decisions/product-scorecard-2026-week4.md
```

**Rollback (story-level — undo the scorecard authoring):**
```bash
git rm homelab-playbook/wiki/decisions/product-scorecard-2026-week4.md
git rm homelab-playbook/scripts/notify-scorecard.sh
```

## Dependencies

- **Blocks:** E4-S12 (retro consumes the decision); product release/promotion (whichever it is)
- **Blocked by:** 4 × E4-S09 weekly digests (one per week of Sprint 4); E4-S08 G-Latency CSVs + rollback evidence; E4-S06 LiteLLM gate result; E4-S10 (cross-link target)

## Risks and Mitigations

| Risk | Source | Mitigation |
|---|---|---|
| Operator misses one of the 4 weekly digests; aggregation has missing data | Discipline (FR-OBS-004 SHOULD bar) | AC1 hard requires ≥ 4; if missed, the scorecard reports "incomplete" status with explicit note; gate decision falls back to whichever data exists |
| K6 (subjective) is hard to grade objectively in the scorecard | Subjectivity | Scorecard reports operator's terminal verdict + a 1-paragraph rationale; the gate-counter treats it like K1-K5 |
| 3-of-6 green: "close-but-not-passing" temptation to override the gate | Discipline | The gate threshold is encoded as `≥ 4`; if green=3 the scorecard says `gate=FAIL` and triggers `migrate` decision per AC9; operator can override only by amending the scorecard with explicit override note (visible in commit) |
| ntfy push fails (CT101 down, Tailscale flaky) | Infra | The wiki commit is the durable record; ntfy is best-effort; AC10 says "delivered" but allows a one-line retry note if push initially failed |
| ADR-014 §Validation criterion (AC12) is left as a stub | Process | AC12 explicit; reviewer-of-one acknowledges in PR body that the SHOULD/MUST verdict was filled |
| Scorecard ships before all 4 weeks complete (e.g., Sprint 4 wraps early) | Schedule | Hard requirement: 4 digests must exist (AC1); if Sprint 4 only has 3 weeks, scorecard runs at end-of-week-3 with explicit "3-week pilot" note and migrates to a 4-week extension if any KPI is borderline |

## Definition of Done

- [ ] All ACs pass (AC1–AC12)
- [ ] `homelab-playbook/wiki/decisions/product-scorecard-2026-week4.md` committed and lint-clean
- [ ] `homelab-playbook/scripts/notify-scorecard.sh` committed and executable
- [ ] AC9 decision is explicit, one of {accept, accept_with_gaps, migrate, revert}
- [ ] AC10 ntfy push delivered (operator phone-confirmed); body matches the scorecard summary
- [ ] `index.md` regenerated to reference the scorecard
- [ ] Cross-reference task added: `AT-FR-OBS-004b`, `AT-FR-DEP-006b`, `AT-FR-DEP-007b` (Phase 5a will populate)
- [ ] Scorecard outcome handed to E4-S12 retro for consumption
