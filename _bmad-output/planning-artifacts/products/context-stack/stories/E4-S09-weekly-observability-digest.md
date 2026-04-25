---
type: story
epic: E4
id: E4-S09
title: "Implement weekly observability digest (cost / hit-rate / footprint / KPI)"
size: 0.5d
priority: SHOULD
fr_refs: [FR-OBS-001, FR-OBS-004, FR-OBS-006]
adr_refs: [ADR-008, ADR-013]
status: draft
date: 2026-04-25
---

# E4-S09: Implement weekly observability digest (cost / hit-rate / footprint / KPI)

## User Story

As **tomamourette** (homelab operator), I want **a weekly digest template at `homelab-playbook/wiki/runbooks/weekly-observability-digest.md` plus a single executable digest at `homelab-playbook/wiki/decisions/weekly-digest-<ISO-WEEK>.md` that aggregates K1 token-reduction sample, K2 reindex timings, K3 Anthropic+OpenAI spend, K4 facts/week, K5 good-catch tally, K6 subjective uplift, FalkorDB RSS, GitNexus daemon RSS, and GitNexus tool-hit-rate**, so that **the 4-week pilot has a structured weekly artifact for E4-S11's product-level KPI scorecard, FR-OBS-001 / FR-OBS-004 / FR-OBS-006 close, and the operator's retro discipline is captured in a wiki-tier-resident artifact (per ADR-013 promotion rule for crystallised patterns)**.

## Background and Context

FR-OBS-001 (weekly cost-check), FR-OBS-004 (weekly retro note), FR-OBS-006 (GitNexus tool-hit-rate) are SHOULDs per ADR-014. They land in this story bundled because they are all read once per week from the same observability fabric (architecture §5.2 Observability table). Brief §6 names K1-K6 as the success-metric scorecard.

EQ7 (epics.md §9) asks where the digest lives. **Resolution:** the **template** lives at `wiki/runbooks/weekly-observability-digest.md` (operator process); **each week's filled instance** lives at `wiki/decisions/weekly-digest-<ISO-WEEK>.md` (the historical record — ADR-013 says "decisions / distilled prior decisions" is the right home for retro artifacts that crystallise into the wiki). Both are wiki-lint-clean, slug-resolvable, and tracked in `index.md`.

The operator chooses delivery: ntfy push at week-end OR daily-email — whichever lands. Default is "manual creation per week + commit" (low ceremony, fits operator-of-one workflow). An optional cron-driven email-out is an extension flagged at retro.

## Acceptance Criteria

### AC1: Template wiki page exists and conforms to ADR-006 schema

- **Given** the wiki tree from E4-S01/S02
- **When** I look at `homelab-playbook/wiki/runbooks/weekly-observability-digest.md`
- **Then** it exists with valid frontmatter (title="Weekly observability digest — template", slug="weekly-observability-digest", category="runbooks", last_reviewed=today, related_frs=[FR-OBS-001, FR-OBS-004, FR-OBS-006], related_adrs=[ADR-008, ADR-013]); body has the 4-section ADR-006 layout; passes `wiki-lint.sh`

### AC2: Template specifies how to fill each KPI row

- **Given** AC1 holds
- **When** I read the template body
- **Then** the Procedure section enumerates per-KPI: (a) the data source (K1: 3 representative cross-repo questions journaled by operator; K2: PostToolUse hook log lines; K3: OpenAI billing dashboard + Anthropic Usage export; K4: `mcp__graphiti__get_episodes(group_id="tom-personal", last_n=200)` count; K5: operator-tagged retro entries per FR-OBS-005; K6: weekly subjective rating with "noticeable" baseline established at week 1); (b) the green/amber/red threshold per K (sourcing PRD §7); (c) which command(s) to run to capture footprint (FalkorDB RSS via `docker stats --no-stream`, GitNexus RSS via `ps -o rss= -p $(pgrep gitnexus)`); (d) GitNexus tool-hit-rate via `grep -c gitnexus ~/.claude/projects/*/sessions/*.jsonl | sort | uniq -c` (or whatever the actual hook log location turns out to be)

### AC3: Template includes copy-paste commands for the operator

- **Given** AC2 holds
- **When** I look at the template's "Procedure" section
- **Then** it has a code block with executable commands the operator can paste into a terminal to gather all signals (with sane comments noting which produces what KPI input); the script equivalent at `homelab-playbook/scripts/weekly-digest.sh` exists and runs the same commands writing to stdout

### AC4: First weekly digest instance is authored at the end of Sprint 4 week 1

- **Given** the deploy from E4-S08 has been live for ~7 days
- **When** I run `bash homelab-playbook/scripts/weekly-digest.sh > /tmp/digest-week1.md` then refine into prose at `homelab-playbook/wiki/decisions/weekly-digest-2026-W17.md` (or whatever the ISO week is)
- **Then** the file exists with valid frontmatter (title="Weekly observability digest — week 1 (Sprint 4)", slug=`weekly-digest-2026-W17`, category="decisions", related_pages=[`weekly-observability-digest`], status="stable"); body has all 6 KPI values + 3 footprint values + 1 hit-rate value + 1 subjective paragraph + 1 "next week's hypothesis" paragraph; passes `wiki-lint.sh`

### AC5: Digest captures the KPI green/amber/red status per row

- **Given** AC4 holds
- **When** I read the digest's body
- **Then** each KPI row shows: KPI name | Value | Threshold | Status (Green/Amber/Red) — using the table from the template; `index.md` regen picks up the new digest

### AC6: GitNexus tool-hit-rate includes the FR-OBS-006 zero-week trigger

- **Given** AC4 holds
- **When** I read the digest's "GitNexus tool-hit-rate" section
- **Then** it reports a number AND a flag — if the rate is 0 calls per session over the 7-day window (FR-OBS-006 trigger), the digest body adds a "CLAUDE.md review needed" callout with a link to the GitNexus section of the operator's `~/.claude/CLAUDE.md`

### AC7: Cost rollup includes both providers

- **Given** AC4 holds
- **When** I read the digest's K3 row
- **Then** it reports Anthropic spend (from operator's manual export of Anthropic Usage), OpenAI spend (from `cost-cap.sh` log aggregate via `awk` on `/var/log/graphiti-cost-cap.log`), and the sum; the threshold for K3 is "monthly run-rate < $20" (i.e., weekly < $5); status = green if weekly ≤ $5, amber if $5-7, red if > $7 OR if any single day hit the $1 cap (recorded in `journalctl -t graphiti-cost-cap`)

### AC8: NFR-COST-003 cost-neutrality check is included if E4-S05/S06 active path

- **Given** E4-S05 + S06 ran the active path (bridge live)
- **When** AC4 runs
- **Then** the digest includes a section "Cost-neutrality (NFR-COST-003)" comparing 7-day pre-bridge spend (from `tests/litellm-50-fact-summary-*.md` start-of-window) vs post-bridge 7-day spend; status = green if equal-or-cheaper, red if more expensive (per NFR-COST-003)

### AC9: Digest is committed as part of weekly retro discipline

- **Given** AC4 created `wiki/decisions/weekly-digest-2026-W17.md`
- **When** I run `git add homelab-playbook/wiki/decisions/weekly-digest-2026-W17.md && git commit -m "wiki: weekly digest 2026-W17"`
- **Then** the commit succeeds; `wiki-lint.sh` passes; `index.md` is regenerated to reference the new digest under `decisions/`

### AC10: Template lifecycle: subsequent weeks reuse the same template, re-fill once per week

- **Given** AC1 + AC4 hold
- **When** week 2 of Sprint 4 ends
- **Then** a new file `wiki/decisions/weekly-digest-2026-W18.md` is created from the template, filled, committed; the **template** is unchanged (it's a template); the **per-week files** accumulate (one per ISO week)

### AC11: Operator decides delivery channel; default is in-repo only

- **Given** the digest is committed to the wiki
- **When** the operator chooses delivery
- **Then** **default**: nothing automatic — operator references the wiki digest at end-of-week retro. **Optional add-on (post-this-story; backlog)**: a cron entry on `ct-ai-01` (or workstation) runs `bash homelab-playbook/scripts/weekly-digest.sh` Sundays at 18:00 local and ntfy-pushes the summary; this is documented in the template but NOT shipped in this story (FR-OBS-001 is SHOULD; the script + manual-recipe is the deliverable; automation is gravy)

## Implementation Notes

### Template content (sketch)

`homelab-playbook/wiki/runbooks/weekly-observability-digest.md`:

```markdown
---
title: "Weekly observability digest — template"
slug: weekly-observability-digest
category: runbooks
last_reviewed: 2026-04-25
owner: tomamourette
related_pages: []
related_frs: [FR-OBS-001, FR-OBS-004, FR-OBS-006]
related_adrs: [ADR-008, ADR-013]
status: stable
supersedes: []
superseded_by: null
---

## Summary

Weekly retro template for Context Stack. Aggregates K1-K6 KPIs, footprints,
hit-rates, and a subjective paragraph. Published to `wiki/decisions/` as
`weekly-digest-<ISO-WEEK>.md` once per week through the 4-week pilot and
beyond.

## Context

The product-level KPI scorecard (E4-S11) at week 4 reads these digests as
input. FR-OBS-001 / FR-OBS-004 / FR-OBS-006 each land here. Per ADR-013,
crystallised retro patterns belong in the wiki tier (decisions/), not in
Graphiti (which holds dated decisions, not retros).

## Procedure

### 1. Run the gather script

    bash homelab-playbook/scripts/weekly-digest.sh

This prints a draft digest to stdout. Pipe to a new file under
`wiki/decisions/`:

    bash homelab-playbook/scripts/weekly-digest.sh > \
      homelab-playbook/wiki/decisions/weekly-digest-$(date -u +%Y-W%V).md

### 2. Refine prose: replace stub paragraphs with actual observations

Sections to fill:

| Section | Source | Threshold (PRD §7) |
|---|---|---|
| K1 token reduction | Manual journal of 3 cross-repo Q&A this week | ≥ 5× input-token reduction → green |
| K2 reindex time | `grep "PostToolUse" ~/.claude/projects/*/sessions/*.jsonl \| awk '{...duration...}'` | ≤ 30 s incremental, ≤ 60 s full → green |
| K3 spend | Anthropic export + OpenAI billing + `awk` over /var/log/graphiti-cost-cap.log | weekly ≤ $5 → green; ≤ $7 → amber; > $7 OR any $1/day cap hit → red |
| K4 facts/week | `claude -p 'use mcp__graphiti__get_episodes group_id=tom-personal last_n=200' \| jq '[.[] \| select(.created_at \| ...)] \| length'` | ≥ 25 facts → green |
| K5 good-catch tally | This week's manual operator-tag of "Graphiti returned a useful prior decision" moments | ≥ 3 tags over 4 weeks; weekly accumulates to that target |
| K6 subjective uplift | One-paragraph operator note | "noticeable" by week 4 retro |
| FalkorDB RSS | `ssh ct-ai-01 'docker stats --no-stream graphiti-falkordb'` | < 200 MB → green |
| GitNexus daemon RSS | `ps -o rss= -p $(pgrep -f gitnexus) \| awk '{print $1/1024 "MB"}'` | < 500 MB → green |
| GitNexus tool-hit-rate | `grep -c '"server":"gitnexus"' ~/.claude/projects/*/sessions/this-week*.jsonl \| awk ...` | > 0 over the week → green; 0 → CLAUDE.md review trigger |
| Cost-neutrality (if Phase 4 bridge active) | 7-day pre-bridge vs 7-day post-bridge K3 | post ≤ pre → green |

### 3. Status row

For each KPI, mark Green / Amber / Red against thresholds. Add to a summary
table at the top of the digest. This table is what E4-S11 reads.

### 4. Commit

    git add homelab-playbook/wiki/decisions/weekly-digest-$(date -u +%Y-W%V).md
    git commit -m "wiki: weekly digest $(date -u +%Y-W%V)"

## Cross-references

- [Weekly digest archive](decisions/) — list of past weeks
- [Cost-cap implementation](weekly-cost-cap-runbook) — if it exists; else link to ADR-008
- [Tier of truth](_schema) — where retros live (wiki vs Graphiti)
```

### `homelab-playbook/scripts/weekly-digest.sh` (sketch)

```bash
#!/usr/bin/env bash
set -euo pipefail
WEEK=$(date -u +%Y-W%V)
TODAY=$(date -u +%Y-%m-%d)
WEEK_AGO=$(date -u -d '7 days ago' +%Y-%m-%d)

cat <<EOF
---
title: "Weekly observability digest — $WEEK"
slug: weekly-digest-$WEEK
category: decisions
last_reviewed: $TODAY
owner: tomamourette
related_pages: [weekly-observability-digest]
related_frs: [FR-OBS-001, FR-OBS-004, FR-OBS-006]
related_adrs: [ADR-008, ADR-013]
status: stable
supersedes: []
superseded_by: null
---

## Summary

[1-2 sentences from operator: how the week went; any standout signals.]

## Context

Pilot week N of 4 (Sprint 4). Stack state: GitNexus on workstation, Graphiti
on ct-ai-01, wiki tier active, [LiteLLM bridge: ACTIVE / DEFERRED]. Source
data window: $WEEK_AGO to $TODAY.

## Decision (KPI scorecard)

| KPI | Value | Threshold | Status |
|---|---|---|---|
| K1 token reduction | [TBD; 3 Q&A samples this week] | ≥ 5× | [G/A/R] |
| K2 reindex time (incr.) | [TBD; from hook log] | ≤ 30 s | [G/A/R] |
| K2 reindex time (full) | [TBD] | ≤ 60 s | [G/A/R] |
| K3 spend (week) | \$$(awk '/throttled|restored/ {sum+=$NF} END {print sum+0}' /var/log/graphiti-cost-cap.log 2>/dev/null || echo "TBD") | ≤ \$5/wk | [G/A/R] |
| K4 facts/week | [TBD; via get_episodes] | ≥ 25 | [G/A/R] |
| K5 good-catch tally | [TBD; manual tag count] | ≥ 3 over 4 wks | [G/A/R] |
| K6 subjective uplift | [TBD; 1-paragraph] | "noticeable" | [G/A/R] |
| FalkorDB RSS | $(ssh -o ConnectTimeout=5 ct-ai-01.tail-scale.ts.net "docker stats --no-stream --format '{{.MemUsage}}' graphiti-falkordb" 2>/dev/null || echo "TBD") | < 200 MB | [G/A/R] |
| GitNexus daemon RSS | $(ps -o rss= -p $(pgrep -f 'gitnexus' | head -1) 2>/dev/null | awk '{printf "%.1f MB", $1/1024}' || echo "TBD") | < 500 MB | [G/A/R] |
| GitNexus tool-hit-rate (week) | [TBD; grep over session jsonl] | > 0/wk | [G/A/R] |
EOF

# Optional cost-neutrality block (if Phase 4 active)
if ssh -o ConnectTimeout=5 ct-ai-01.tail-scale.ts.net "grep -q '^OPENAI_BASE_URL=http://hybrid-gemma' /srv/graphiti/.env" 2>/dev/null; then
cat <<EOF

| NFR-COST-003 cost-neutrality | [pre=\$X / post=\$Y] | post ≤ pre | [G/A/R] |
EOF
fi

cat <<EOF

## Cross-references

- [Weekly digest template](weekly-observability-digest)
- [Cost cap (ADR-008)](git:_bmad-output/planning-artifacts/products/context-stack/adrs/ADR-008-daily-1-dollar-cap-implementation.md)

## Notes

[Operator paragraph: lessons from the week; any retro candidates for ADR-013
promotion to wiki proper or Graphiti add_episode.]
EOF
```

### Why digest lives in `decisions/` not `runbooks/`

Per ADR-013, retros are the operator's distilled record of what was decided / what was learned. The **template** is procedural (runbook); the **per-week digest** is a decision artifact (which KPIs were green and what we did about reds). Both are wiki-tier (current state + retrospective record), neither is Graphiti (Graphiti holds dated decisions about the *system under management*, not retros about the *process of managing it*).

### NOT in scope

- Does NOT auto-publish to email/ntfy (AC11 says it's a backlog item).
- Does NOT make the digest into a dashboard or web UI (NG9 — CLI + MCP only).
- Does NOT auto-promote weekly digests into Graphiti episodes (manual process per ADR-013).
- Does NOT cover monthly rollup (separate, E4-S11 owns the 4-week aggregate).

## Test Plan

**Pre-flight:**
```bash
ls homelab-playbook/wiki/{runbooks,decisions}/   # confirm dirs exist (E4-S01)
test -f /var/log/graphiti-cost-cap.log || echo "(cost-cap log absent — E4-S04 not yet run on ct-ai-01)"
ssh ct-ai-01.tail-scale.ts.net 'docker stats --no-stream graphiti-falkordb' 2>&1 | head -2
```

**Author template (Edit/Write):**
- `homelab-playbook/wiki/runbooks/weekly-observability-digest.md` per AC1-AC3
- `homelab-playbook/scripts/weekly-digest.sh` per Implementation Notes; chmod +x

**AC verification:**
```bash
# AC1
yq '.title, .slug, .category, .related_frs, .related_adrs' homelab-playbook/wiki/runbooks/weekly-observability-digest.md
bash homelab-playbook/scripts/wiki-lint.sh
# AC2 (manual review of body)
grep -E '^### \d\.' homelab-playbook/wiki/runbooks/weekly-observability-digest.md
# AC3
test -x homelab-playbook/scripts/weekly-digest.sh && bash homelab-playbook/scripts/weekly-digest.sh | head -50
# AC4 (run at end of week 1 of Sprint 4)
bash homelab-playbook/scripts/weekly-digest.sh > homelab-playbook/wiki/decisions/weekly-digest-$(date -u +%Y-W%V).md
# Operator fills [TBD] sections
# AC5 (verify status column populated)
grep -E '\| \[G\|A\|R\] \|' homelab-playbook/wiki/decisions/weekly-digest-*.md | wc -l   # ≥ 6 KPIs
# AC6
grep -i 'CLAUDE.md review' homelab-playbook/wiki/decisions/weekly-digest-*.md   # only if K6 = 0
# AC7
grep -E 'Anthropic.+OpenAI|K3 spend' homelab-playbook/wiki/decisions/weekly-digest-*.md
# AC9
bash homelab-playbook/scripts/wiki-lint.sh && git add homelab-playbook/wiki/decisions/weekly-digest-*.md
git commit -m "wiki: weekly digest $(date -u +%Y-W%V)"
# AC10 (deferred — confirms at week 2 of Sprint 4)
```

**Rollback:**
```bash
git rm homelab-playbook/wiki/runbooks/weekly-observability-digest.md
git rm homelab-playbook/scripts/weekly-digest.sh
git rm homelab-playbook/wiki/decisions/weekly-digest-*.md
```

## Dependencies

- **Blocks:** E4-S11 (KPI scorecard reads from the per-week digests)
- **Blocked by:** E4-S01 (wiki schema/lint), E4-S04 (cost-cap.log is a data source), E4-S08 (deploy active so K2/K4 measurable)

## Risks and Mitigations

| Risk | Source | Mitigation |
|---|---|---|
| Operator doesn't fill the digest weekly → no data for E4-S11 | Discipline | AC4 + AC10 establish the cadence; if missed, E4-S11 falls back to summed signals from raw logs (less rich, still data); retro captures the gap |
| `weekly-digest.sh` SSH/jq commands fail in unexpected env (e.g., shell quoting) | Script reliability | Script uses `2>/dev/null \|\| echo "TBD"` fallbacks; operator manually fills any TBDs; doesn't gate the digest |
| K6 (subjective) is harder to fill than K1-K5 | Subjectivity | Template has explicit "noticeable baseline established at week 1" instruction; operator anchors at week 1 and grades subsequent weeks against that baseline |
| Cost-neutrality block lies dormant if Phase 4 deferred | Conditional logic | AC8 only fires if bridge active; the wiki page footer notes "Phase 4 deferred" if S05/S06 closed deferred |
| Digest gets too long over 4 weeks (4 separate files) → noise in the wiki | Naming | One file per week is the right cadence (small, focused); E4-S11 produces a separate "4-week scorecard" rollup as its own digestible artifact, not a 4-file concat |

## Definition of Done

- [ ] All ACs pass (AC1–AC11), with AC4 representing one filled digest by end of Sprint 4 week 1
- [ ] `homelab-playbook/wiki/runbooks/weekly-observability-digest.md` (template) committed and lint-clean
- [ ] `homelab-playbook/scripts/weekly-digest.sh` committed and executable
- [ ] At least one filled digest at `homelab-playbook/wiki/decisions/weekly-digest-<ISO>.md` committed
- [ ] `index.md` regenerated to reference both the template and the first digest
- [ ] AC11 backlog ticket (if operator decides to automate ntfy/email): `weekly-digest-automation` filed under `_bmad-output/planning-artifacts/products/context-stack/backlog/`
- [ ] Cross-reference task added: `AT-FR-OBS-001a`, `AT-FR-OBS-004a`, `AT-FR-OBS-006a` (Phase 5a will populate)
