---
type: story
epic: E3
id: E3-S09
title: "Week-2 decision gate — KPI scorecard, RAM check, decide proceed/migrate"
size: 0.5d
priority: MUST
fr_refs: [FR-MEM-007, FR-MEM-008, FR-MEM-015, FR-OBS-005]
adr_refs: [ADR-014, ADR-001, ADR-002]
status: draft
date: 2026-04-25
---

# E3-S09: Week-2 decision gate — KPI scorecard, RAM check, decide proceed/migrate

## User Story

As **tomamourette** (homelab operator), I want **a one-page week-2 decision-gate scorecard that records K1–K6, FalkorDB resident memory, OpenAI spend, and operator-tagged "good catches" against the green/amber/red rubric, ending with a binary proceed-to-E4 / migrate-or-revert decision recorded in the sprint retro**, so that **E3 can close cleanly with a documented gate per brief §6 / PRD §7 / epics §5.4 — not on subjective vibes (FR-MEM-007, FR-MEM-008, FR-MEM-015, FR-OBS-005 covered)**.

## Background and Context

The week-2 decision gate is the binding step before E4 starts. Per epics §5.4 AC9, the threshold is "≥ 4-of-6 KPIs green" with K5 (first-shot recall) measured on operator-tagged retro queries from one full week of usage. Per epics §9 EQ2, this story is where the green/amber/red rubric per KPI gets fixed — until now, K6 ("subjective uplift") has been ungrounded.

The scorecard format is operator-facing one-pager — not a spreadsheet, not a dashboard. The operator answers each row in 2–3 sentences with evidence pointers; the final decision is binary and recorded in the Sprint 3 retro.

## Acceptance Criteria

### AC1: K1 (token reduction) measured on 3 representative cross-repo questions

- **Given** Graphiti has been live for 2 weeks (or as much as Sprint 3 allows; even 1 week is acceptable since GitNexus is the dominant K1 driver — see PRD §7)
- **When** I select 3 representative cross-repo questions from the past week's actual sessions and compute input-token count for (a) Graphiti+GitNexus-mediated answer vs (b) grep-and-read baseline
- **Then** the recorded ratio is ≥ 5× on average across the 3 questions (FR-CG-008 K1 green threshold), or amber 3–5×, or red < 3×. **Note:** K1 is primarily a GitNexus story (E2 owned), not Graphiti's; the E3 gate records what's measurable but doesn't gate solely on K1.

### AC2: K2 (re-index timing) — informational only (GitNexus territory)

- **Given** PostToolUse-on-commit hooks are firing from E2
- **When** I sample timing for 5 typical commits in the week-2 window
- **Then** record values; this gate doesn't fail E3 on K2 (E2's domain).

### AC3: K3 (spend) — sum OpenAI + Anthropic, threshold $20/month run-rate

- **Given** ADR-002 cost model predicts ~$0.30/month from Graphiti at operator's profile
- **When** I check OpenAI usage dashboard for the 2-week window and Anthropic usage export
- **Then** the recorded combined run-rate (extrapolated to 30 days) is < $20/month (green), $20–$30/month (amber), > $30/month (red).
- **And** within OpenAI: `gpt-4o-mini` line is < $5/month run-rate (NFR-COST-001 sub-cap); `text-embedding-3-small` line is < $0.10/month.
- **And** zero days in the window exceeded $1/day (NFR-COST-002 — manual check this week; E4-S04 automates).

### AC4: K4 (facts/week) ≥ 25 distinct facts captured

- **Given** Graphiti has been writing for 2 weeks
- **When** I count: `docker compose exec falkordb redis-cli -a "$FALKORDB_PASSWORD" GRAPH.QUERY default_db "MATCH (n)-[r]->(m) WHERE n.group_id='tom-personal' AND r.created_at > '2026-04-11' RETURN count(r)"` (date adjusted to 2 weeks ago)
- **Then** count is ≥ 50 (green: 2 × 25/week threshold), 25–49 (amber: meeting baseline), < 25 (red: ingest is failing — model isn't being prompted to write per CLAUDE.md).

### AC5: K5 (first-shot recall) ≥ 50% on operator-tagged retro queries

- **Given** the operator has tagged 8 retro queries during the week-2 window where Graphiti *should* have a useful prior decision
- **When** I run each query against `search_facts` and judge "useful match returned in top-3 results" (binary per query)
- **Then** ≥ 4-of-8 = 50% (green per FR-MEM-007), 3-of-8 (amber), ≤ 2-of-8 (red — recall machinery broken).
- **And** the tagged-query method is recorded: each tag is an entry in a operator-kept list at `homelab-playbook/docs/runbooks/graphiti-retro-tags.md` with timestamp, query, expected-fact-pointer, observed-result.

### AC6: K6 (subjective uplift) ≥ "noticeable" on week-2 retro

- **Given** the operator has logged subjective notes per session over the 2-week window (FR-OBS-004)
- **When** I review the notes and rate uplift on a green/amber/red rubric:
  - **Green:** ≥ 60% of sessions where Graphiti was queried produced a "yes, useful" tag; subjective overall = "noticeable" or stronger
  - **Amber:** 40–60% useful tag rate; mixed subjective
  - **Red:** < 40% useful tag rate; subjective = "I don't notice it" or "OMEGA-redux"
- **Then** record the rating with 2–3 sentences of qualitative evidence (closes EQ2 — "noticeable" is now operator-defined as ≥ 60% useful-tag rate).

### AC7: FalkorDB RAM < 200 MB at week-2 sample

- **Given** the stack has been up for ≥ 2 weeks
- **When** I run `ssh ct-ai-01 'docker stats graphiti-falkordb --no-stream --format "{{.MemUsage}}"'` (sample over 24 h via 6 spaced samples for noise control)
- **Then** mean RSS < 200 MB (FR-MEM-015 / NFR-FOOTPRINT-001 green); 200–400 MB amber; > 400 MB red (architectural premise of ADR-001 in question).

### AC8: GitNexus daemon RSS < 500 MB (cross-pilot check, AR1 closure)

- **Given** GitNexus from E2 has been live for ≥ 2 weeks
- **When** I sample workstation `ps -p $(pgrep -f gitnexus | head -1) -o rss=` over 24 h
- **Then** mean RSS < 500 MB (NFR-FOOTPRINT-002 green); informational on this gate but recorded.

### AC9: Good-catch tally ≥ 3 over the 2-week window (closes FR-OBS-005)

- **Given** the operator has been recording "good catches" — moments where Graphiti returned a useful prior decision the operator would have otherwise re-derived
- **When** I count tagged entries in `homelab-playbook/docs/runbooks/graphiti-retro-tags.md` flagged `good-catch`
- **Then** count ≥ 3 (green), 1–2 (amber), 0 (red — Graphiti isn't earning rent).

### AC10: Decision recorded in Sprint 3 retro

- **Given** ACs 1–9 produce a populated scorecard
- **When** I count "green" rows across K1–K6 (six possible)
- **Then** record the decision per the rubric:
  - **≥ 4-of-6 green:** **PROCEED to E4** — record in `_bmad-output/evidence/E3-S09-decision-gate-2026-05-09.md` (date adjusted to actual gate day)
  - **3-of-6 green:** **AMBER — proceed with documented gap and a Sprint-4 review story**; gap items become E4 backlog
  - **≤ 2-of-6 green:** **MIGRATE OR REVERT** — exercise FR-DEP-007 Phase-2 portion: `docker compose down`, `claude mcp remove graphiti`, retain monthly Cypher export at `/srv/graphiti/exports/` for replay
- **And** the decision is signed off by the operator (one-line note); the next sprint plan reflects it.

### AC11: One-pager committed to repo

- **Given** AC10 decision is made
- **When** I write `_bmad-output/evidence/E3-S09-decision-gate-2026-05-09.md` per the template in Implementation Notes
- **Then** the file contains: KPI table (K1–K6 green/amber/red + values), RAM checks, good-catch tally, qualitative summary (≤ 200 words), final decision, action items (if any), reference to retro session.

## Implementation Notes

**Scorecard one-pager template (`_bmad-output/evidence/E3-S09-decision-gate-2026-05-09.md`):**

```markdown
# E3-S09 Week-2 Decision Gate — 2026-05-09

**Operator:** tomamourette
**Window:** 2026-04-25 → 2026-05-09 (15 days)
**Stack:** FalkorDB v<X> + zepai/graphiti-mcp:v1.0.2 on ct-ai-01

## KPI scorecard

| KPI | Green threshold | Observed | Status | Evidence |
|---|---|---|---|---|
| K1 | ≥ 5× token reduction (3 q's avg) | <X.X×> | Green/Amber/Red | <link to question samples> |
| K2 | ≤ 30 s incremental reindex | <Xs avg over 5 commits> | (E2 territory) | <link> |
| K3 | < $20/month run-rate | <$X.XX> | <status> | OpenAI dashboard screenshot |
| K4 | ≥ 25 facts/week | <X facts in 2 weeks> | <status> | Cypher count |
| K5 | ≥ 50% first-shot recall (8 tagged) | <X-of-8> | <status> | retro-tags.md link |
| K6 | "noticeable" / ≥ 60% useful | <subjective>; <X% of sessions> | <status> | retro notes |

## Footprint checks

- FalkorDB RSS (mean over 24 h): <X MB> — target < 200 MB. Status: <green/amber/red>
- GitNexus daemon RSS (mean over 24 h): <X MB> — target < 500 MB. Status: <informational>

## Good-catch tally
<N> good catches in window. Top 1–2 examples (one-line each):
1. <example>
2. <example>

## Qualitative summary (≤ 200 words)
<operator narrative — what worked, what didn't, what surprised>

## Decision
**Greens: <N>-of-6.**

[ ] PROCEED to E4 (≥ 4-of-6 green)
[ ] AMBER — proceed with gap (3-of-6 green; backlog: <items>)
[ ] MIGRATE / REVERT (≤ 2-of-6 green)

**Action items:**
- <one item per amber/red row>

**Sign-off:** tomamourette  / 2026-05-09
**Retro reference:** <link to Sprint 3 retro doc>
```

**Where the data comes from:**
- K1: 3 sample sessions from the week-2 window, hand-tagged by operator at session-end. Use `wc -w` on the relevant grep-and-read baseline transcript vs the GitNexus/Graphiti-mediated transcript.
- K2: GitNexus PostToolUse hook log (`~/.claude/hooks.log` or wherever E2-S04 routed it).
- K3: <https://platform.openai.com/usage> (manual screenshot/CSV) + Anthropic usage export.
- K4: direct Cypher query to FalkorDB (per AC4).
- K5: `homelab-playbook/docs/runbooks/graphiti-retro-tags.md` — operator-maintained.
- K6: weekly retro notes — also operator-maintained.

**Retro tags doc structure (`graphiti-retro-tags.md`):**

```markdown
# Graphiti retro tags — operator-curated

| Date | Query | Expected fact | Observed result | Tag |
|---|---|---|---|---|
| 2026-04-26 | "what did we decide about pve2 storage" | pve2 → ZFS mirror migration | <result snippet> | useful / noise / good-catch |
| ... | ... | ... | ... | ... |
```

Tags: `useful` (returned within top-3, matches expected), `partial` (returned but ranked low), `noise` (returned wrong fact), `miss` (returned nothing), `good-catch` (returned a fact the operator would not have remembered themselves).

**Why this is a 0.5d story, not a full day:** the *gate* itself is operator judgment + a one-pager. The hard work is the 2-week observation that precedes it — which has been happening in parallel with E3-S05/06/07/08 deliverables. This story is the *consolidation*.

**EQ2 closure:** by adopting the rubric above (green/amber/red per KPI with explicit thresholds), epics §9 EQ2 is closed. Update epics §9 to reflect.

## Test Plan

```bash
# AC1 — token reduction sample (manual, per question)
# Q1: "which roles in any sibling repo reference mempalace?"
#   Baseline: grep -ri 'mempalace' ~/workspace/homelab/ | wc -w  → BX
#   GitNexus: claude --print "use gitnexus impact for mempalace symbol" | wc -w → GX
#   Ratio: BX/GX
# Repeat for Q2, Q3; record in scorecard

# AC3 — spend
# Manual: open https://platform.openai.com/usage
# Manual: anthropic usage export
# Sum to scorecard

# AC4 — facts count
DATE_2W_AGO=$(date -d '14 days ago' -Iseconds)
ssh ct-ai-01 "docker exec graphiti-falkordb redis-cli -a \"$(grep ^FALKORDB_PASSWORD= /srv/graphiti/.env | cut -d= -f2)\" GRAPH.QUERY default_db \"MATCH (n)-[r]->(m) WHERE n.group_id='tom-personal' AND r.created_at > '$DATE_2W_AGO' RETURN count(r)\""

# AC5 — first-shot recall
# Manual: open homelab-playbook/docs/runbooks/graphiti-retro-tags.md
# Filter rows in the 2-week window; count tag=useful/(useful+partial+noise+miss)

# AC7 — RAM sample
for i in $(seq 1 6); do
  ssh ct-ai-01 'docker stats graphiti-falkordb --no-stream --format "{{.MemUsage}}"'
  sleep $((4*3600))   # 6 samples × 4 h = 24 h coverage; or run async on schedule
done | tee /tmp/e3-s09-falkor-ram.log

# AC8 — GitNexus RAM
for i in $(seq 1 6); do
  ps -p $(pgrep -f gitnexus | head -1) -o rss=
  sleep $((4*3600))
done | tee /tmp/e3-s09-gitnexus-ram.log

# AC9 — good-catch tally
grep -c "good-catch" homelab-playbook/docs/runbooks/graphiti-retro-tags.md

# AC10–AC11 — manual scorecard write-up
$EDITOR _bmad-output/evidence/E3-S09-decision-gate-$(date -I).md
```

## Dependencies

- **Blocks:** E4 epic start. The decision in AC10 directly determines whether Sprint 4 begins as planned (PROCEED), starts with a documented gap (AMBER), or pivots to migrate-or-revert (RED).
- **Blocked by:** E3-S05, S06, S07, S08 — all evidence sources. **Crucially also blocked by 2 weeks of observation time** — this story can only run at the end of week 2 of E3 deployment, not on day 1.

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Operator skips retro tagging mid-week → K5/K6/K9 thin | Calendar nudge at end of each session: "tag Graphiti queries"; ntfy reminder Friday afternoons |
| K5 < 50% — recall is broken | Diagnose: AR8 (group_id mishandled — re-verify E3-S05 outcome); ADR-003 (embedder choice — try `text-embedding-3-large` controlled experiment); CLAUDE.md prompt tuning |
| K3 > $30/month — runaway ingest | E4-S04 hard-cap is the long-term answer; for now drop SEMAPHORE_LIMIT to 2 and audit what's chatty (`get_episodes` + manual review) |
| K6 "I don't notice it" — same OMEGA failure mode reprised | The architectural premise of the product is in question; AMBER decision with explicit Sprint 4 review story to either tune or initiate migrate path |
| RAM > 200 MB (AC7 red) — ADR-001 premise broken | Document; pursue Neo4j-evaluation backlog story; not blocking E4 unless > 1 GB sustained (would breach mem_limit) |
| Operator over-weights one bad week (single-event bias) | Decision rubric is mechanical (count greens); operator narrative goes in qualitative summary, not the decision count |
| Decision deferral — operator can't decide proceed/migrate | Decision rubric forces binary; AMBER is the explicit "with-gap" choice; no "I'll think about it" path |

## Definition of Done

- [ ] All ACs (AC1–AC11) addressed (some AC values may be amber/red — that's a recorded outcome, not a story failure)
- [ ] `_bmad-output/evidence/E3-S09-decision-gate-<date>.md` committed, signed off by operator
- [ ] `homelab-playbook/docs/runbooks/graphiti-retro-tags.md` populated with ≥ 8 entries from the window
- [ ] AC7/AC8 RAM logs archived
- [ ] Decision recorded in Sprint 3 retro: PROCEED / AMBER / MIGRATE-REVERT
- [ ] If PROCEED: E4 sprint plan starts; no further E3 stories
- [ ] If AMBER: explicit backlog tickets filed for the gap items; E4 starts with the documented caveat
- [ ] If MIGRATE-REVERT: FR-DEP-007 Phase-2 rollback executed (`docker compose down`, `claude mcp remove graphiti`); monthly Cypher export retained; epic closes with epic-level retrospective
- [ ] EQ2 closed in epics §9 (rubric defined)
- [ ] Acceptance test stubs `AT-FR-MEM-007a`, `AT-FR-MEM-008a`, `AT-FR-MEM-015a`, `AT-FR-OBS-005a` referenced in `tests/acceptance.md`
- [ ] FR-MEM-014 final sign-off (full backup-mechanism-exercised closure across E3-S07 + E3-S08 + this gate)
