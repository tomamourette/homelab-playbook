# Sprint 4 Kickoff — Production Hardening Part A (Epic E4 partial)

**Date:** 2026-04-27
**Sprint:** 4 of 5 (Production Hardening Part A, Week 7-8 of 10)
**Sprint Goal:** Ship wiki tier (3 stories) + $1/day hard-cap auto-throttle (1 story) + Ansible role + ct-dev-homelab deploy with rollback drill (2 stories). 6 stories, ~8.5 ideal days, ~14.4 wall-clock days. **Buffer is tight (~-5.4 days nominal); aggressive SHOULD-trim discipline applies.**
**Branch:** `feature/context-stack-e3-graphiti` (continues from Sprint 3 close; rebase/branch decision deferred to operator)
**Sprint plan source:** `_bmad-output/planning-artifacts/products/context-stack/sprint-plan.md` §6

---

## 1. Pre-flight checklist

### 1.1 Mandatory checks

| # | Check | Status | Notes |
|---|---|---|---|
| 1 | E1 (Decommission) closed | PASS | Tagged `phase-1-decommission-complete` 2026-04-26. **Not merged to `main` yet** — FR-DEC-009 forward-protection hook flagged this when pushing E3 work. Acceptable for E4-S01 because the wiki tier lives entirely under `homelab-playbook/wiki/` with no dependency on the decommissioned `ai-dev-omega-memory` / MemPalace roles. |
| 2 | E2 (GitNexus Pilot) closed | DEFERRED | Sprint 2 was never executed; GitNexus MCP is `Connected` per E3-S03 evidence but no week-1 KPI scorecard exists. Carry-forward addressed in §3 below. Does not block E4-S01. |
| 3 | E3 (Graphiti Pilot) closed | PASS (CONDITIONAL) | Sprint 3 closed 2026-04-27 with `e3-retro` (commit `03ad119`). Exit Gate verdict CONDITIONAL-PASS: 5/9 clean PASS, 2 PARTIAL, 2 operator-pending, 1 substantively-met. Zero FAIL. |
| 4 | `down -v` guard spec re-read (S3-prep / Mandatory Fix #2) | NOT SHIPPED | Per E3-retro §3 and §8 (S3-prep #2): the spec for E4-S07's rollback playbook did not ship visibly in Sprint 3. **Action: re-draft the AC text + the `cp -a` pre-step OR `--force-data-loss` guard before E4-S07 starts (week 2 of this sprint).** Spec lands inline in E4-S07 PR; no separate prep commit. |

### 1.2 Informational checks (state recorded; not blocking E4-S01)

| Check | Status | Notes |
|---|---|---|
| `ct-dev-homelab` reachable | TBD | Not required until E4-S07/S08 (week 2). Verify by D36 latest. |
| `hybrid_gemma_serving` status | TBD | Sprint 5 (LiteLLM bridge) dependency, not Sprint 4. Re-check at S4 retro to decide S5 Path A vs Path B per sprint-plan.md §7.2. |
| Restic source-set wiring | OPEN | Operator follow-up #1 from E3 KPI scorecard: point restic at `~/.local/state/graphiti-backup/`. Sprint 4 GO condition (operator action), not E4-S01-specific. |
| `~/.graphiti-data.preserved-by-e3-s08` cleanup | OPEN | E3 retro operator follow-up #2: safe to delete on/after 2026-04-28. |
| AR8 — `tom-personal` namespace verification | OPEN | E3-S06 used per-test alphanumeric groups; tom-personal default-group AR was deferred. One-off probe at S4 D31 per E3 retro §7 carry-forward #4. |

---

## 2. Sprint backlog

Per `sprint-plan.md` §6.3:

| Story ID | Title | Ideal d | Real wc-d | Dependencies | This-sprint priority |
|---|---|---|---|---|---|
| **E4-S01** | Wiki schema + bootstrap (`index.md`, `_schema.md`) | 1.0 | 1.7 | E1 merged (de-facto via tag) | **NEXT — in flight** |
| E4-S02 | Bootstrap initial 3-5 wiki seed entries | 1.5 | 2.5 | E4-S01 | **STOP after S01 — operator picks seed content** |
| E4-S03 | `wiki-query` skill (read-on-demand) | 1.0 | 1.7 | E4-S01 | parallelizable with S02 (week 1) |
| E4-S04 | Daily $1 hard-cap auto-throttle | 1.5 | 2.5 | E3 complete | week 2 |
| E4-S07 | `ai-dev-context-stack` Ansible role + `down -v` guard | 1.5 | 2.5 | E2 + E3 complete | week 2 |
| E4-S08 | Deploy to ct-dev-homelab + E2E + rollback drill | 1.5 | 2.5 | E4-S07 | week 2 endgame |

**Total:** 8.5 ideal-d / ~14.4 wc-d. Sprint capacity (10 wc-d minus 1d kickoff/retro overhead) = 9 wc-d. **Nominal buffer: -5.4 wc-d.** Per sprint-plan.md §6.5, mitigations are: aim for 3 seeds (not 5) in E4-S02; do NOT refactor the ct-ai-01 Compose unit when wrapping it in the Ansible role (E4-S07).

**Note:** 6 stories vs 12 in original Epic E4. The other 6 (E4-S05 LiteLLM bridge, E4-S06 50-fact validation, E4-S09 observability digest, E4-S10 query hierarchy + exit ramps, E4-S11 product KPI scorecard, E4-S12 phase-4 retro) belong to Sprint 5 (Part B) per the §6.2 split rationale. The E4 Decision Gate is the **Sprint 5** gate, not this sprint's.

---

## 3. Carry-forward from Sprint 3 retro and KPI scorecard

Operator action items (informational here; tracked in retro §7):

1. **Restic source set:** point at `~/.local/state/graphiti-backup/` before S4 closes. Single config change; severity HIGH if not done (workstation-loss event loses every backup).
2. **Preserved data dir:** `sudo rm -rf ~/.graphiti-data.preserved-by-e3-s08` on/after 2026-04-28 (24h post-drill safety window expires).
3. **Gemini API key rotation:** security hygiene; key string is in Sprint 3 transcript on disk per operator-side workflow.
4. **GitNexus KPI backfill (K1, K2, K4-GitNexus):** 3 INSUFFICIENT-DATA scores in the E3 scorecard reflect Sprint 2 deferral. Carry to S5 E4-S09 (weekly observability digest), ~0.25d. Does NOT carry to E4-S01.
5. **AR8 `tom-personal` probe:** one-off at S4 kickoff per retro §7 carry-forward #4.
6. **FalkorDB RSS snapshot:** Epic AC6 needs `docker stats` evidence at end of S4 per retro §7 carry-forward #5.
7. **SEMAPHORE_LIMIT and telemetry-off re-confirmation:** Epic AC8 components not cited explicitly in S3 evidence per retro §7 carry-forward #6.
8. **`cypher-replay.sh` decision (S3-prep #1):** either land in S4 or downgrade to docs-only with RDB-restore as the operative recovery procedure. Decision owner: operator at first available checkpoint.
9. **Daily "did this save a re-derivation?" prompt:** add to operator daily retro template starting D31 so K6 has 4 weeks of operator-tagged data before S5 product gate.

None of items 1-9 block E4-S01.

---

## 4. Sprint discipline (E3 retro lesson applied)

Per E3-retro §5, lesson 2: **substory expansion needs a formal trigger.** E3-S04 grew from 1 story to 7 substories (E3-S04a..g) without a sprint-change-proposal cycle; the velocity-tracking discipline in `sprint-plan.md` §8 was not exercised.

**Sprint 4 rule of record:**

- At the moment any story emits its **second** substory, file a one-paragraph **sprint-change-proposal** note at `homelab-playbook/docs/context-stack/sprint-4/change-proposal-<storyID>.md` capturing: (a) the unplanned divergence, (b) the new ideal-day estimate, (c) the carry-forward decision (does this push another story out of S4, or is it absorbed in buffer?).
- The note lands BEFORE the second substory's evidence commit.
- No more silent E3-S04a..g style growth.

This applies to **every** story in this sprint, including E4-S01.

---

## 5. Decision gate (proceed to Sprint 5?)

10 acceptance criteria per `sprint-plan.md` §6.6. Re-read at S4 retro (D40). Headline gates:

- All 10 ACs pass → **GO** to Sprint 5.
- If E4-S08 G-Rollback drill fails: stack does NOT promote off `ct-dev-homelab`; S5 becomes a stabilization sprint and LiteLLM defers automatically.
- If `hybrid_gemma_serving` not in beta by S4 retro: S5 reshapes to Path B per `sprint-plan.md` §7.2; backlog ticket for LiteLLM.

This is **not** the product-level gate. The binding product release gate is S5 E4-S11.

---

## 6. Velocity tracking

Per `sprint-plan.md` §8, append a row to `velocity-log.md` at S4 retro. S1-S3 multipliers should be back-computed from commit timestamps if the log was not maintained — but the multiplier baseline informs S4-D40 honesty about whether the 1.7× assumption held.

---

**End of Sprint 4 kickoff. First action: E4-S01 implementation (separate commit).**
