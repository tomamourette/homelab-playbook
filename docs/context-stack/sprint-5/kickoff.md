# Sprint 5 Kickoff — Production Hardening Part B (Epic E4 remainder)

**Date:** 2026-04-27
**Sprint Goal:** Close out E4 — observability digest + query hierarchy + product KPI scorecard + retro. LiteLLM bridge stories (E4-S05 / E4-S06) are FR-LLM-007 gate-pending and start on operator signal.
**Branch:** `feature/context-stack-e3-graphiti` (continues from Sprint 4 close)
**Sprint plan:** `_bmad-output/planning-artifacts/products/context-stack/sprint-plan.md` §7
**Predecessor:** Sprint 4 retro `144174f` (2026-04-27) — Exit Gate PASS

## Pre-flight checklist

| # | Check | Status | Notes |
|---|---|---|---|
| 1 | Sprint 4 closed | PASS | Retro `144174f` 2026-04-27 — all 10 Exit Gate ACs PASS or substantively-met PASS |
| 2 | E4-S08 stack live on ct-dev-homelab | PASS | `graphiti-mcp Up (healthy) 49m`, `falkordb Up (healthy) 49m`, `gitnexus Up (healthy) ~1h` per `docker ps` against 192.168.50.156 |
| 3 | Cost-cap log present on ct-ai-01 | PASS | `/var/log/cost-cap.log` last 30-min cron tick at 13:00:01 UTC; `today_spend_usd=0.0002538` well under budget |
| 4 | GitNexus daemon running on workstation | PASS | container `gitnexus Up 57m (healthy)`, RSS ~93 MiB (well under K-footprint < 500 MB) |
| 5 | Graphiti backup logs present | PASS | `~/.local/state/graphiti-backup/logs/{aof,cypher,rdb}.log` populated (most recent: rdb.log 09:30 UTC) |
| 6 | FR-LLM-007 gate verdict | OPERATOR-PENDING | Determines whether E4-S05/S06 (LiteLLM bridge) run this sprint or defer to backlog. Default = pending until operator resolves at S5 D41. |
| 7 | Sprint 4 GO conditions partially open | PARTIAL | Restic source set + key rotations + preserved-data-dir cleanups remain operator-side; not blocking S09 / S10 / S11 |

## Sprint backlog (per sprint-plan.md §7)

| Story ID | Title | Gate-dependent? | This-sprint priority |
|---|---|---|---|
| **E4-S09** | Weekly observability digest + KPI backfill | NO | **NEXT (in flight via this story)** |
| E4-S10 | Query hierarchy + exit ramps (tier-of-truth ADR-013) | NO | after S09 |
| E4-S11 | Product-level KPI scorecard | depends on S09 digests | week 2 |
| E4-S12 | Sprint 5 retro + product retro | final | week 2 endgame |
| E4-S05 | LiteLLM bridge — wire path | YES (FR-LLM-007) | DEFERRED until gate resolved |
| E4-S06 | LiteLLM bridge — verification | YES (FR-LLM-007) | DEFERRED |

Gate-independent path (S09 → S10 → S11 → S12) ships regardless of FR-LLM-007 verdict. If operator selects Path A (LiteLLM proceeds), S05/S06 slot in before S11. If Path B (defer), S05/S06 to backlog and the saved time absorbs into vague-AC tightening / extra wiki seeds per sprint-plan §7.2.

## Carried-forward from Sprint 4 retro / E3 KPI scorecard

Operator action items still open (most-urgent first, full list in `sprint-4/retro.md` §10):

1. **URGENT — Rotate `LITELLM_MASTER_KEY`** (leaked in E4-S08 agent transcript — length=67 shape exposed; full value visible in earlier debugging step).
2. **URGENT — Rotate `GEMINI_API_KEY`** (transcript exposure 2026-04-27 — Sprint 3 carry-forward + continued S4 exposure during env-template fix).
3. Point restic source set at `~/.local/state/graphiti-backup/` (Sprint 3 carry-forward #1; without it, workstation-loss event also loses every backup).
4. Preserved data dir cleanup:
   - `~/.graphiti-data.preserved-by-e3-s08` — `sudo rm -rf` on/after 2026-04-28 (24h post-drill window).
   - `/srv/graphiti/data.bak.20260427T123352` on ct-dev-homelab — clean up after 24h if stack stable (E4-S08 Phase 4 drill artefact).
5. E4-S02 wiki seed promotion (`tailscale-policy`, `pve9-ha-migration`, `hybrid-gemma-serving` — operator review `status: draft` → `status: stable`).
6. **FR-LLM-007 gate decision** — Path A vs Path B vs operator-input-pending → blocks E4-S05 / E4-S06 only.
7. **GitNexus K1 / K2 / K4-GitNexus KPI backfill — closed by THIS story's E4-S09 deliverable.** See `e4-s09-evidence.md` and `sprint-2/kpi-backfill.md`.
8. `cypher-replay.sh` final disposition (one-line ADR-007 sub-amendment to memorialise "RDB-restore is operative; Cypher export is docs-only" — closes Mandatory Fix #1).
9. AR8 `tom-personal` namespace one-off probe (deferred again in S4).
10. Daily "did this save a re-derivation?" prompt for K6 retro tagging (start at S5 D41 latest so K6 has 4 weeks of operator-tagged data before the binding S5 product gate at E4-S11).

## Decision Gate (proceed to Sprint-5 close)

10 acceptance criteria per sprint-plan.md §7.5 (Path A) — re-read at S5 retro. Path B (LiteLLM-deferred) collapses to 6 ACs (S09 + S10 + S11 + S12 deliverables only).

## Honest disclosure for S5 buffer

Sprint-plan §12 lists S5 as the only sprint with positive buffer (+0.1 wc-d Path A, +0.5 wc-d Path B). Sprint 4's actual velocity (~2h 14min wall-clock for the entire sprint per retro §12) is dramatically tighter than the 1.7× plan multiplier; S5 is unlikely to be buffer-constrained. The constraint is the FR-LLM-007 decision and operator concentration availability, not arithmetic.
