---
adr: 016
title: "NFR-FOOTPRINT-002 active-state baseline — re-baseline GitNexus daemon RSS from idle 500 MB to active 2 GB"
status: accepted
date: 2026-04-26
authors: tomamourette (via BMAD director Claude)
context_question: null
supersedes: null
amends: prd.md NFR-FOOTPRINT-002
---

# ADR-016: NFR-FOOTPRINT-002 active-state baseline — re-baseline GitNexus daemon RSS from idle 500 MB to active 2 GB

## Context

NFR-FOOTPRINT-002 in the Context Stack PRD originally read:

> **NFR-FOOTPRINT-002**: GitNexus daemon resident memory: < 500 MB. Measurement: process RSS sample over 24 h on workstation.

That threshold was set during PRD authoring (Phase 2) without any empirical measurement of the GitNexus daemon. Sprint 2 produced two such measurements:

- **E2-S02 retry (idle baseline, 2026-04-26)**: 12 samples × 5 s = 60 s window with the daemon running but **zero repos indexed**. PEAK 80 MB / MEAN 80 MB / P95 80 MB. Flat line. Comfortably under the 500 MB threshold.
- **E2-S06 Scenario 5 (active baseline, 2026-04-26)**: 30 samples × 30 s = 900 s window with **3 repos indexed** (homelab-apps + homelab-infra + homelab-playbook = 883 files / 11 944 nodes / 12 756 edges) and an MCP load loop hitting `list_repos` every 10 s. PEAK 1482 MB / MEAN 1315 MB / P95 1480 MB. Working-set trend −212 MB across the window — **no memory leak**. Three times over the original 500 MB threshold.

The original threshold was correct for the daemon-with-zero-repos case it was implicitly written against, and incorrect for the active-state operating profile that Sprint 2 onwards depends on. The PRD author did not have empirical data and treated 500 MB as a generous-feeling cap; the cap is an artifact of estimation, not an architectural constraint.

The relevant architectural constraint per the brief and ADR-015 is that the stack must fit comfortably on a homelab workstation (16+ GB RAM) with room to share with Claude Code, the user's other tooling, and a future Graphiti container. **2 GB sustained RSS is well within that envelope** (~12.5 % of a 16 GB host) and matches the measured reality of GitNexus indexing the user's 3-repo corpus.

## Decision

Re-baseline NFR-FOOTPRINT-002:

- **Active threshold**: GitNexus daemon resident memory < **2 GB sustained RSS** when ≥ 1 repo is indexed.
- **Idle expectation (informational, not a gate)**: < 500 MB when zero repos are indexed.
- **Scaling expectation**: roughly 1 GB per 1 000 indexed files. If Sprint 4's `ct-dev-homelab` deploy crosses ~3 000 files (e.g., adds Graphiti's Python library or a 10-repo merge), revisit this NFR.

Measurement: process RSS sampled at 30 s intervals over a ≥ 15 min sustained-load window with the daemon serving an MCP request every ≤ 10 s.

Trend behaviour required: working set must NOT grow monotonically across the window (leak detector). If trend is positive, this NFR is breached even if peak stays under 2 GB.

## Alternatives considered

1. **Investigate why 1.5 GB on 883 files** — could be inefficient indexing, retainer leak in LadybugDB, large internal caches, or simply by-design memory–for–query-speed trade-off. Estimated effort ~½ day. **Rejected**: the daemon shows no leak (working-set trend −212 MB), the operator decision (1A) chose to proceed, and the investigation can land as a Sprint 2 retro action item without blocking Sprint 2 close.
2. **Defer to E2-S08 decision gate (Option C of escalation)** — let the 4-of-6 KPI scorecard drive the verdict. **Rejected**: the answer was foreordained (re-baseline) since the daemon is healthy and the 500 MB number was unfounded; punting wastes a gate exchange.
3. **Reverse ADR-004 to a lighter tool** (e.g., CodeGraphContext) — would lower footprint at the cost of restarting the Sprint 2 stories. **Rejected**: 2 GB is well within homelab budget; tool selection is sound.
4. **Keep the 500 MB threshold and mark NFR-FOOTPRINT-002 as failed in the Sprint 2 KPI scorecard** — preserves the original number but turns the scorecard verdict into a misleading "FAIL" on a healthy daemon. **Rejected**: dishonest measurement; scorecard purpose is decision support not box-ticking.

## Consequences

### Positive
- NFR matches measured reality. Sprint 2 KPI scorecard at E2-S08 becomes meaningful.
- E2-S06 Scenario 5 verdict flips from FAIL to PASS under the new threshold (1482 MB measured vs 2000 MB threshold).
- Future deploys (Sprint 4 ct-dev-homelab) inherit a realistic baseline rather than chasing an unattainable 500 MB.
- Captures the active-vs-idle distinction architecturally — useful framing for any future runtime NFR.

### Negative
- 4× higher footprint allowance. If Sprint 4 scales to 10+ repos in `ct-dev-homelab` deploy, the 2 GB ceiling may be reached and this NFR will need re-baselining again. The 1 GB-per-1000-files scaling expectation surfaces this risk early.
- Loses some forcing function for upstream optimization. If a future GitNexus version regresses memory, the wider threshold absorbs more of the regression silently. Mitigation: the leak-detector clause (no monotonic growth) catches growth-style regressions.

### Neutral / known trade-offs
- ADR-015 (Docker delivery) image is 944 MB on registry / 504 MB on disk; the daemon's 1.5 GB sustained RSS is on top of that storage cost. Combined storage + memory ~2 GB total — still acceptable for homelab.
- Idle expectation kept as informational sub-criterion. Useful for canary checks (a daemon idling at 1 GB before any repo is indexed would indicate a regression), but not gating.

## Validation / Exit ramp

- **Sprint 2 close**: re-run the same 15-min sustained-load test against `gitnexus` container; confirm the daemon's measured behavior matches the new NFR.
- **Sprint 4 ct-dev-homelab deploy**: re-run sustained-load test in the container deployment; if PEAK > 2 GB AND the corpus is < 1 000 files / 1500 nodes more than the workstation pilot, that's evidence of an environmental regression and this NFR re-evaluates.
- **Sprint 4 retro**: as a planned re-evaluation point, validate the 1 GB-per-1000-files scaling expectation against actual observed behavior. Update the NFR's scaling rule if the empirical scaling differs materially.
- **Exit ramp if NFR cannot hold**: the FR-CG-010 GitNexus exit ramp (graphify, CodeGraphContext) remains available. If a Sprint 4 measurement breaches a 4 GB ceiling, escalate to a tool-replacement ADR.

## References

- ADR-004 (GitNexus over alternatives — tool selection unchanged by this ADR)
- ADR-015 (GitNexus Docker delivery — captures the libstdc++ pivot that preceded these measurements)
- E2-S02 retry evidence: `homelab-playbook/docs/context-stack/sprint-2/e2-s02-footprint-evidence-retry.md` (idle baseline)
- E2-S06 evidence: commit `a1eeb64` on `feature/context-stack-e2-gitnexus`; `homelab-playbook/docs/context-stack/sprint-2/e2-s06-smoke-tests-evidence.md` Scenario 5 (active baseline)
- prd.md NFR-FOOTPRINT-002 (amended in this commit)
