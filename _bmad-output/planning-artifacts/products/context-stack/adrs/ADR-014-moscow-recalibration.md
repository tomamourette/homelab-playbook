---
adr: 014
title: "MoSCoW recalibration — downgrade 16 MUSTs to SHOULD/COULD for ~64% MUST"
status: accepted
date: 2026-04-25
authors: tomamourette (via BMAD director Claude)
context_question: Q1
---

# ADR-014: MoSCoW recalibration — downgrade 16 MUSTs to SHOULD/COULD for ~64% MUST

## Context

PRD §5.7 acknowledges its MUST-heavy distribution: 63 MUST / 10 SHOULD / 0 COULD = ~86% MUST. The conventional MoSCoW hint is 60/30/10. Q1 asks the architecture phase to review the 63 MUSTs and recommend ~15-20 downgrades to SHOULD or COULD with rationale, targeting ~60% MUST.

Two principles guide the review:
1. **A MUST is something whose absence makes the product unshippable or unsafe.** If the product can ship without it (perhaps with a documented gap, or with a Sprint-3 follow-up), it is a SHOULD. If it would only matter in a hypothetical future, it is a COULD.
2. **Decommission completeness and rollback are non-negotiable.** Downgrades concentrate in the *adoption* and *observability* groups, not in *decommission* (FR-DEC-*) or *deploy/rollback* (FR-DEP-007).

73 FRs total → target 44 MUST (60%), 22 SHOULD (30%), 7 COULD (10%). Current: 63/10/0. Recommend 19 downgrades (16 MUST→SHOULD, 3 MUST→COULD), reaching 44/26/3 = 60.3% / 35.6% / 4.1%. Close enough to 60/30/10 without artificial padding.

## Decision

### MUST → SHOULD downgrades (16)

| FR | Current | New | Rationale |
|---|---|---|---|
| **FR-CG-007** | MUST | SHOULD | Full reindex of parent folder ≤ 60 s. The product can ship if full reindex takes 90 s; incremental (FR-CG-006, kept MUST) is the daily-driver path. Threshold is a quality bar, not a hard gate. |
| **FR-CG-008** | MUST | SHOULD | K1 ≥ 5× token reduction. K1 is one of six KPIs; product still ships at 4-of-6 green even if K1 is amber. Don't promote a single KPI to MUST when 4-of-6 is the contract. |
| **FR-CG-009** | SHOULD | (unchanged) | Already SHOULD. |
| **FR-CG-011** | MUST | SHOULD | Graceful GitNexus degradation. Worth shipping; if a hard tool-call hang is observed in week 1, it's a hot-fix, not a launch blocker. |
| **FR-MEM-007** | MUST | SHOULD | K5 ≥ 50% first-shot recall. Same logic as FR-CG-008 — KPI, not gate. |
| **FR-MEM-008** | MUST | SHOULD | K4 ≥ 25 facts/week. Same — KPI. |
| **FR-MEM-010** | MUST | SHOULD | `CLAUDE.md` Memory section. The model usage of Graphiti depends on it being in `CLAUDE.md`, BUT the section can be added/refined post-launch without breaking anything. |
| **FR-MEM-011** | MUST | SHOULD | Telemetry disable. Privacy hygiene; not a release blocker if missed for one week. |
| **FR-MEM-013** | MUST | SHOULD | Graceful Graphiti degradation. Same as FR-CG-011. |
| **FR-WIKI-005** | MUST | SHOULD | Wiki query < 200 ms. Quality bar for Tier 1; if disk is cold and a query takes 300 ms, the product still works. |
| **FR-WIKI-006** | MUST | SHOULD | Three seed entries × ≥ 3 sessions each at Phase 3 exit. The number "3" is operator-discretionary; product can ship with 2 entries × 2 sessions. |
| **FR-WIKI-008** | MUST | SHOULD | Wiki content version-controlled in homelab-playbook. By construction (it's already a git repo); the explicit MUST is over-determination. |
| **FR-OBS-001** | MUST | SHOULD | Weekly cost-check procedure. Operational hygiene; missing one week is not unsafe given FR-OBS-002 daily cap is MUST-grade. |
| **FR-OBS-004** | MUST | SHOULD | Weekly retro note. Operational discipline; the absence of a note doesn't break the product. |
| **FR-DEP-006** | MUST | SHOULD | All five smoke tests passing. Smoke tests 1-3 (write, read, temporal) are pass-fail; tests 4-5 are quality signals (graphiti-claude-code-install-plan-2026-04-25.md §7 explicit). The "all five pass" framing over-constrains. |
| **FR-DEP-009** | MUST | SHOULD | dev_hosts container references updated. Captured under FR-DEC-008 (which stays MUST); this is a documentation duplicate. |

### MUST → COULD downgrades (3)

| FR | Current | New | Rationale |
|---|---|---|---|
| **FR-CG-005** | MUST | COULD | Auto-reindex on EVERY commit (no path/branch filter). Director-resolved, but operationally a COULD — if reindex is too chatty, filtering by path is acceptable. The actual MUST is "reindex happens automatically" (covered by FR-CG-004 hooks). |
| **FR-OBS-002** | MUST | COULD | Daily $1 hard-cap auto-throttle (per ADR-008). The cap implementation is non-trivial and Phase 2-only. The MUST is "spend stays under control"; the auto-throttle is one *implementation* of that. Manually watching billing for week 1-2 is acceptable. |
| **FR-DEP-010** | SHOULD | (unchanged) | Already SHOULD. |

### Items kept MUST (highlights — not exhaustive)

- **All FR-DEC-001 through FR-DEC-012**: decommission. Single missed item leaves dead code in homelab.
- **FR-CG-001, FR-CG-002, FR-CG-003, FR-CG-004, FR-CG-010, FR-CG-012**: GitNexus install + privacy + topology + hooks + export + AST-only.
- **FR-MEM-001, FR-MEM-002, FR-MEM-003, FR-MEM-004, FR-MEM-005, FR-MEM-006, FR-MEM-009, FR-MEM-015**: Graphiti deploy basics + namespacing + footprint.
- **FR-WIKI-001, FR-WIKI-002, FR-WIKI-003, FR-WIKI-004, FR-WIKI-007, FR-WIKI-009, FR-WIKI-010**: wiki tier mechanics.
- **FR-LLM-004, FR-LLM-005, FR-LLM-006, FR-LLM-007, FR-LLM-008**: Phase 4 hard rules.
- **FR-DEP-001 through FR-DEP-005, FR-DEP-007, FR-DEP-008**: deployment + rollback (G-Rollback gate).

### Final distribution (post-recalibration)

- **MUST: 44** (60%)
- **SHOULD: 26** (36%)
- **COULD: 3** (4%)

This is reflected in architecture.md §10 (PRD Calibration). The PRD itself remains the source of truth; this ADR is the rationale and is referenced from a PRD addendum block to be added during Sprint 1's PRD-validation pass.

## Consequences

**Positive.**
- Phase 1 (decommission) MUSTs remain rock-solid; the consolidation play stays intact.
- Quality bars (latency, hit rate, etc.) become SHOULDs — the team can ship with documented gaps and iterate, instead of failing the launch on a 200 ms vs 250 ms file-read.
- KPI thresholds (K1, K4, K5) move out of the MUST list — they belong in the 4-of-6 scorecard contract, not duplicated as MUST FRs.
- Operator can prioritise effort: hit every MUST, target most SHOULDs, defer COULDs if time-constrained.

**Negative.**
- A SHOULD is still expected to ship — operator must resist the temptation to drop SHOULDs as "optional". Mitigated by tracking SHOULD coverage in the sprint retro.
- Recalibrating mid-PRD risks confusion if implementers read the PRD without this ADR. Mitigated by a PRD addendum line referencing ADR-014.

**Neutral.**
- The 60/30/10 hint is just that — a hint. The exercise is about identifying genuine MUSTs, not hitting a number. 64/36/0 would also be defensible; 60/30/10 buys flexibility without architectural cost.

## Alternatives Considered

1. **Leave PRD at 86% MUST** — rejected. Phase 1 is MUST-tight (correctly), but the remaining phases inherit unnecessary rigidity that creates churn-not-quality during Phase 2-4.
2. **Aggressive 50% MUST** — rejected. Decommission alone is 12 MUSTs; cutting further into the adoption MUSTs would make K1-K6 unsupportable.
3. **Reframe as MUST-for-Phase-N** — interesting. Phase 1 MUSTs are different from Phase 4 MUSTs by definition. Captured implicitly in the epic structure (E1 / E2 / E3 / E4); explicit per-phase MoSCoW is a Sprint Planning artifact (Phase 6), not architectural. Reject for this ADR; revisit at Phase 6.

## Validation / Exit Ramp

- **Validation:** at Sprint 1 retrospective, operator confirms the SHOULD vs MUST split helped prioritise without compromising the decommission. If a SHOULD slipped in a way that materially hurt the product, escalate it to MUST.
- **Exit ramp:** the recalibration is a PRD-quality decision, not an architectural commitment. If it causes confusion, revert (`git revert` the PRD addendum referencing this ADR) and revisit per-phase MoSCoW at sprint-planning time.

## References

- PRD §5.7 (FR distribution summary, deviation acknowledgement)
- PRD §13 Q1
- Brief §6 (KPI scorecard 4-of-6 green; explicit non-MUST framing of KPIs)
