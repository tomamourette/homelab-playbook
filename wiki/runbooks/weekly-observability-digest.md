---
title: "Weekly observability digest — template"
slug: weekly-observability-digest
category: runbooks
last_reviewed: 2026-04-27
owner: tomamourette
related_pages: []
related_frs: [FR-OBS-001, FR-OBS-004, FR-OBS-006]
related_adrs: [ADR-008, ADR-013]
status: stable
supersedes: []
superseded_by: null
---

## Summary

Weekly retro template for the Context Stack pilot. Aggregates the K1-K6 KPIs
plus FalkorDB / GitNexus footprint and GitNexus tool-hit-rate into a single
markdown digest committed to `wiki/decisions/weekly-digest-<ISO-WEEK>.md`.
Drives the product-level KPI scorecard at E4-S11. Cadence: once per week
through the 4-week pilot and beyond.

## Context

Per ADR-013 the wiki tier holds *current state* authoritative knowledge,
including crystallised retro patterns. Weekly digests are decisions ("here is
what was green / amber / red and what we did about it") and live under
`wiki/decisions/`; this *template* is procedural and lives under
`wiki/runbooks/`. Neither belongs in Graphiti — Graphiti holds dated
decisions about the system under management, not retros about the process of
managing it.

The digest closes three FRs in one fabric: FR-OBS-001 (weekly cost-check),
FR-OBS-004 (weekly retro note), and FR-OBS-006 (GitNexus tool-hit-rate trip
to "CLAUDE.md review needed" when the rate is zero over a 7-day window).

## Procedure

### 1. Run the gather script

```bash
bash homelab-playbook/scripts/weekly-digest.sh
```

This prints a draft digest body to stdout. Pipe to a per-week file under
`wiki/decisions/`:

```bash
SLUG=$(date -u +%Y-w%V)   # lowercase 'w' is required by wiki-lint kebab-case rule
bash homelab-playbook/scripts/weekly-digest.sh > \
  homelab-playbook/wiki/decisions/weekly-digest-${SLUG}.md
```

### 2. Refine prose

Replace stub `[TBD]` paragraphs with actual observations. Sections to fill:

| Section | Source | Threshold (PRD §7) |
|---|---|---|
| K1 token reduction | Manual journal of 3 cross-repo Q&A this week | >= 5x input-token reduction -> green |
| K2 reindex time | `grep PostToolUse ~/.claude/projects/*/sessions/*.jsonl` (or registry indexedAt deltas) | <= 30 s incremental, <= 60 s full -> green |
| K3 spend | Anthropic Usage export + `cost-cap.log` aggregate via `awk` (script auto-fills the gemini half) | weekly <= $5 green; <= $7 amber; > $7 OR any cap-breach in window -> red |
| K4 facts/week | `mcp__graphiti__get_episodes(group_id="tom-personal", last_n=200)` count (script auto-fills via redis-cli on ct-dev-homelab) | >= 25 facts -> green |
| K5 good-catch tally | Operator-tagged retro entries per FR-OBS-005 | >= 3 tags over 4 weeks |
| K6 subjective uplift | One-paragraph operator note | "noticeable" by week-4 retro |
| FalkorDB RSS | `docker stats falkordb` on ct-dev-homelab (script auto-fills) | < 200 MB -> green |
| GitNexus daemon RSS | `docker stats gitnexus` on workstation (script auto-fills) | < 500 MB -> green |
| GitNexus tool-hit-rate | grep over `~/.claude/projects/*/sessions/*.jsonl` (script auto-fills) | > 0 over the week -> green; 0 -> CLAUDE.md review trigger |
| Cost-neutrality (Phase 4 only) | 7-day pre-bridge vs 7-day post-bridge K3 | post <= pre -> green |

### 3. Status row

For each KPI, mark Green / Amber / Red against thresholds. The summary
table at the top of the digest is what E4-S11 reads at the product-level
gate. Auto-populated rows ship with G/A/R already filled by the script;
manual rows ship with `[G/A/R]` placeholder for the operator to set.

### 4. Commit

```bash
SLUG=$(date -u +%Y-w%V)
bash homelab-playbook/scripts/wiki-lint.sh \
  homelab-playbook/wiki/decisions/weekly-digest-${SLUG}.md
git add homelab-playbook/wiki/decisions/weekly-digest-${SLUG}.md
git commit -m "wiki: weekly digest ${SLUG}"
```

### Idempotency

The script is idempotent — running it twice within the same UTC minute
produces the same output (no time-jitter randomness). Re-running after a
new sample (e.g., a fresh cron tick of `cost-cap.log`) updates the values
deterministically.

### Delivery channel (default = in-repo only)

Per AC11, the **default** delivery is in-repo only — operator references
the wiki digest at end-of-week retro. Optional add-on (post-this-story
backlog item `weekly-digest-automation`): a cron entry on the workstation
runs `bash homelab-playbook/scripts/weekly-digest.sh` Sunday 18:00 UTC
and ntfy-pushes the summary line. The infra-side cron stub is shipped in
`homelab-infra/ansible/roles/weekly-digest/` (status: not-yet-enabled —
opt-in via inventory variable; ships now to avoid carrying it as a
deferred backlog item).

## Cross-references

- [Weekly digest archive](decisions/) — list of past weeks
- [Tier of truth (ADR-013)](_schema) — where retros live (wiki vs Graphiti)
- [Cost cap (ADR-008)](git:_bmad-output/planning-artifacts/products/context-stack/adrs/ADR-008-daily-1-dollar-cap-implementation.md) — feeds K3 row

## Notes

The Sprint-3 KPI scorecard (`docs/context-stack/sprint-3/e3-s09-kpi-scorecard.md`)
flagged K1, K2, and K4-GitNexus as INSUFFICIENT-DATA because the Sprint-2
GitNexus evidence pack was never authored. The Sprint-2 backfill was closed
in this story (E4-S09) — see `docs/context-stack/sprint-2/kpi-backfill.md`
for the one-shot measurements that fill the gap before the binding S5
product-level scorecard at E4-S11.
