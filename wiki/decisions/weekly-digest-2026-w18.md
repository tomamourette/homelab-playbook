---
title: "Weekly observability digest — 2026-W18"
slug: weekly-digest-2026-w18
category: decisions
last_reviewed: 2026-04-27
owner: tomamourette
related_pages: [weekly-observability-digest]
related_frs: [FR-OBS-001, FR-OBS-004, FR-OBS-006]
related_adrs: [ADR-008, ADR-013]
status: stable
supersedes: []
superseded_by: null
---

## Summary

[1-2 sentences from operator: how the week went; standout signals.]

## Context

Pilot 2026-W18. Stack state: GitNexus on workstation, Graphiti on ct-dev-homelab
(production target), wiki tier active, LiteLLM bridge: DEFERRED (FR-LLM-007
gate operator-pending). Source data window: 2026-04-20 to 2026-04-27.

## Decision (KPI scorecard)

| KPI | Value | Threshold | Status |
|---|---|---|---|
| K1 token reduction | [TBD; 3 cross-repo Q&A samples this week] | >= 5x | [G/A/R] |
| K2 reindex time (incr.) | [TBD; from PostToolUse hook log] | <= 30 s | [G/A/R] |
| K2 reindex time (full) | [TBD] | <= 60 s | [G/A/R] |
| K3 spend (week) | $0.000254 (lifetime: $0.0002538; cap-breaches in window: 2) | <= $5/wk | R |
| K4 facts/week (tom-personal) | 0 | >= 25 | [G/A/R] |
| K5 good-catch tally | [TBD; manual operator-tag count] | >= 3 over 4 weeks | [G/A/R] |
| K6 subjective uplift | [TBD; 1-paragraph operator note] | "noticeable" by week 4 | [G/A/R] |
| FalkorDB RSS (ct-dev-homelab) | 16.6MiB | < 200 MB | G |
| GitNexus daemon RSS (workstation) | 58.85MiB | < 500 MB | G |
| GitNexus tool-hit-rate (week) | 43 calls | > 0/wk | G |

## GitNexus reindex recency (registry.json)

| Repo | Last indexed | Files | Nodes |
|---|---|---|---|
| homelab-apps | 2026-04-27T06:52:15.810Z | 96 | 343 |
| homelab-infra | 2026-04-27T11:36:05.056Z | 362 | 3850 |
| homelab-playbook | 2026-04-27T12:09:24.244Z | 492 | 8113 |

## Recent commits (window: 2026-04-20 -> 2026-04-27)

- homelab-apps: 27 commits this week
- homelab-infra: 37 commits this week
- homelab-playbook: 82 commits this week

## Cross-references

- [Weekly digest template](weekly-observability-digest)
- [Cost cap (ADR-008)](git:_bmad-output/planning-artifacts/products/context-stack/adrs/ADR-008-daily-1-dollar-cap-implementation.md)
- [Tier of truth (ADR-013)](_schema)

## Notes

[Operator paragraph: lessons from the week; retro candidates for ADR-013
promotion to wiki proper or Graphiti add_episode.]
