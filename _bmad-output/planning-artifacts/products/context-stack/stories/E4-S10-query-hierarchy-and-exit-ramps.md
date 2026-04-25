---
type: story
epic: E4
id: E4-S10
title: "Document unified query hierarchy + validate exit ramps (GitNexus and Graphiti)"
size: 1d
priority: MUST
fr_refs: [FR-WIKI-007, FR-CG-010]
adr_refs: [ADR-013, ADR-006, ADR-012, ADR-007]
status: draft
date: 2026-04-25
---

# E4-S10: Document unified query hierarchy + validate exit ramps (GitNexus and Graphiti)

## User Story

As **tomamourette** (homelab operator), I want **(a) the unified query-hierarchy doc authored at `homelab-playbook/wiki/architecture/context-stack-query-hierarchy.md` (Tier 1 wiki → Tier 2 GitNexus → Tier 3 Graphiti → Tier 4 auto-memory) per ADR-013, and (b) both adopted-component exit ramps dry-run-validated end-to-end: GitNexus → CodeGraphContext / graphify (via the `scripts/gitnexus-export.sh` NDJSON wrapper from E2-S07) AND Graphiti → Mem0/OMEGA-revival via the Cypher dump + episode-replay log from E3-S07**, so that **NFR-SUPP-002 closes (every adopted component has a documented + exercised exit ramp), FR-WIKI-007 closes, and the operator has confidence that supply-chain risk on either tier (R1, AR4 GitNexus abandonment) is materially reversible**.

## Background and Context

ADR-013 establishes the tier-of-truth division. FR-WIKI-007 mandates a "unified query hierarchy" document. NFR-SUPP-002 mandates documented exit ramps for each adopted component. ADR-012 (Q8) ships GitNexus's NDJSON export schema; ADR-007 (Q2) ships Graphiti's three-layer backup. This story consolidates both into **dry-run validations** — actually running the export, actually running an episode-replay round-trip — so the exit ramps are **exercised**, not theoretical.

The risk this story addresses (R1 GitNexus abandonment, R5 OpenAI dependency, AR4): if either upstream becomes unmaintained or unworkable, the operator can re-target the data to the named alternative (CodeGraphContext for code-graph; Mem0 / OMEGA-revival / Cypher-on-fresh-Graphiti for memory) within ≤ 1 day operator-wall-time (NFR-MAINT-001).

## Acceptance Criteria

### AC1: Query-hierarchy wiki page authored and lint-clean

- **Given** the wiki tree (E4-S01/S02)
- **When** I look at `homelab-playbook/wiki/architecture/context-stack-query-hierarchy.md`
- **Then** it exists with valid ADR-006 frontmatter (title="Context Stack — unified query hierarchy", slug=`context-stack-query-hierarchy`, category="architecture", related_frs=[FR-WIKI-007], related_adrs=[ADR-013, ADR-006, ADR-009]); body has all 4 sections; passes `wiki-lint.sh`

### AC2: Page documents the read order with rationale and cost reasoning

- **Given** AC1 holds
- **When** I read the body
- **Then** the Procedure section enumerates the 4 tiers in cost-order: Tier 1 wiki (< 200 ms file-read, zero retrieval tokens, "current state"), Tier 2 GitNexus (sub-second AST query, "code structure"), Tier 3 Graphiti (~100-500 ms MCP, "dated decisions / supersession"), Tier 4 auto-memory (passive, "session-start ground truth / one-line pointers"); each tier has a 1-2 sentence "when to query this tier" and a "what NOT to query this tier for" — verbatim aligned with ADR-013's decision card

### AC3: Page documents the WRITE hierarchy (the half ADR-013 added beyond PRD §14)

- **Given** AC1 holds
- **When** I read the body
- **Then** the Procedure section's second half states: where each kind of fact goes when the operator captures it — one-line pointer → `MEMORY.md`; durable artifact → wiki; dated decision / supersession → Graphiti; code structure → GitNexus (automatic, no operator write). This is the "Don't double-write" rule from `graphiti-claude-code-install-plan-2026-04-25.md` §9 (which ADR-013 formalised) — verbatim cited

### AC4: Page documents bidirectional promotion rules

- **Given** AC1 holds
- **When** I read the body
- **Then** the Procedure section also documents (per ADR-013 §Bidirectional rule): wiki → Graphiti supersession (set `superseded_by:` AND write a Graphiti episode); Graphiti → wiki promotion (3+ session crystallization → distil to wiki, leave Graphiti episode for trail); auto-memory → wiki promotion (entries growing past one line are wiki candidates)

### AC5: GitNexus exit ramp is dry-run-validated via export wrapper

- **Given** GitNexus from E2 is running on the workstation with the parent-folder topology
- **When** I run `bash homelab-playbook/scripts/gitnexus-export.sh > /tmp/e4-s10-gitnexus-export.ndjson`
- **Then** the file exists with > 0 lines; each line is valid JSON parseable as `{type: "node"|"edge", id, ...}` per ADR-012; `head -1 /tmp/e4-s10-gitnexus-export.ndjson | jq .type` returns `"node"`; `wc -l /tmp/e4-s10-gitnexus-export.ndjson` reports a non-trivial count (≥ 100 lines for the homelab parent-folder graph)

### AC6: GitNexus export round-trip dry-run into a CodeGraphContext-equivalent target (file-only verification)

- **Given** AC5 produced the NDJSON
- **When** I run a parsing/replay sketch script `homelab-playbook/scripts/gitnexus-export-replay-dryrun.sh /tmp/e4-s10-gitnexus-export.ndjson` that reads the NDJSON, validates schema conformance for every line, and outputs a count of nodes/edges by label/kind
- **Then** the script exits 0; output reports counts that look reasonable (e.g., `Function: 200 nodes, REFERENCES: 1500 edges`); zero schema violations. **Note:** this story does NOT install or actually run CodeGraphContext — that would be a separate epic if the operator ever needs to migrate. The dry-run validates that the NDJSON IS in the schema CodeGraphContext or any successor would expect, per ADR-012

### AC7: Graphiti exit ramp — Cypher export validated round-trippable

- **Given** Graphiti from E3 is running on `ct-ai-01` and E3-S07 implemented the monthly `scripts/cypher-export.sh`
- **When** I SSH to ct-ai-01 and run `sudo bash /srv/graphiti/scripts/cypher-export.sh > /tmp/e4-s10-graphiti-cypher.json`
- **Then** the file exists with valid JSON output of `MATCH (n)-[r]->(m) RETURN n,r,m`; size > 0; `jq '.results | length' /tmp/e4-s10-graphiti-cypher.json` returns the node count; this is the FR-MEM-012 / NFR-PORT-002 acceptance signal

### AC8: Graphiti exit ramp — episode-replay log validated extractable

- **Given** Graphiti running with INFO logs captured (FR-OBS-003 from E3-S04)
- **When** I run `ssh ct-ai-01.tail-scale.ts.net 'sudo journalctl -u docker -t graphiti-mcp --since "30 days ago" | grep -E "add_episode|episode_body" > /tmp/e4-s10-replay.log'` (or `docker compose logs --since 720h graphiti-mcp | grep ...`)
- **Then** the log file is non-empty; each line corresponds to an `add_episode` call with the prompt body extractable (so a future "replay these episodes against a fresh Graphiti / Mem0 / new tool" path is feasible); the count roughly matches K4 weekly facts × pilot weeks

### AC9: Exit-ramp documentation page authored at `wiki/runbooks/exit-ramps.md`

- **Given** AC5-AC8 produced evidence
- **When** I look at the wiki
- **Then** `homelab-playbook/wiki/runbooks/exit-ramps.md` exists with valid frontmatter (slug=`exit-ramps`, category=`runbooks`, related_frs=[FR-CG-010, FR-MEM-012, FR-MEM-014], related_adrs=[ADR-007, ADR-012]); body has two parallel sections "GitNexus → alternative" and "Graphiti → alternative"; each section has: command sequence, expected output sample, target tools (GitNexus → CodeGraphContext / graphify, Graphiti → Mem0 / OMEGA-revival via Cypher / fresh-Graphiti); each command sequence has been ACTUALLY RUN per AC5/AC7/AC8 with /tmp output paths cited as evidence

### AC10: Both ramps measure ≤ 1 day operator-wall-time per NFR-MAINT-001

- **Given** AC5-AC8 ran
- **When** I record wall-time of each export
- **Then** the AC9 wiki page reports actual measured wall-time (typically < 5 minutes for a homelab-sized graph); ≤ 1 day envelope is trivially met; if either ramp wall-time exceeds 30 min, the page calls out the size as a risk

### AC11: `index.md` regenerated to reference the new pages

- **Given** AC1 + AC9 hold
- **When** I run `bash homelab-playbook/scripts/wiki-lint.sh --regen`
- **Then** `index.md` lists `context-stack-query-hierarchy` under architecture/ and `exit-ramps` under runbooks/; `wiki-lint.sh` exits 0

### AC12: Both pages cross-reference each other AND the relevant FRs/ADRs

- **Given** AC1 + AC9 hold
- **When** I inspect frontmatter and body cross-refs
- **Then** `context-stack-query-hierarchy.md` lists `exit-ramps` in `related_pages` and vice versa; both pages have `[Tier 1 wiki](_schema)`, `[GitNexus exit ramp](exit-ramps#gitnexus)` etc. as inline cross-refs; all resolve via wiki-lint

## Implementation Notes

### `wiki/architecture/context-stack-query-hierarchy.md` content (sketch)

```markdown
---
title: "Context Stack — unified query hierarchy"
slug: context-stack-query-hierarchy
category: architecture
last_reviewed: 2026-04-25
owner: tomamourette
related_pages: [_schema, exit-ramps, ai-dev-context-stack]
related_frs: [FR-WIKI-007, FR-MEM-005, FR-CG-003]
related_adrs: [ADR-013, ADR-006, ADR-009, ADR-005]
status: stable
supersedes: []
superseded_by: null
---

## Summary

Four tiers, in cost-order, for a Claude Code session: wiki (file-read) →
GitNexus (AST) → Graphiti (bi-temporal facts) → auto-memory (passive
session-start markdown). Cheapest first; never write the same fact in two
tiers; promotion rules below.

## Context

ADR-013 formalises the tier-of-truth division. The four tiers exist because
each has a comparative advantage — collapsing them loses K1-K6 differentiation.
Knowing the rules avoids the OMEGA + MemPalace decay pattern.

## Procedure / Decision

### Read order (queries)

1. **Tier 1 — Wiki** (`homelab-playbook/wiki/`, via `wiki-query` skill)
   - When: "what's our convention for X", "tailscale policy", "PVE topology"
   - Latency: < 200 ms file-read; zero retrieval tokens
   - NOT for: dated decisions, code structure
2. **Tier 2 — GitNexus** (workstation MCP, AST)
   - When: "what calls X", "where is Y defined", "impact of changing Z"
   - Latency: sub-second
   - NOT for: human-language conventions, dated decisions
3. **Tier 3 — Graphiti** (ct-ai-01 MCP, bi-temporal)
   - When: "what did we decide about X", "when did Y change", "supersession trail"
   - Latency: 100-500 ms
   - NOT for: code structure, current static state
4. **Tier 4 — auto-memory** (`MEMORY.md`, passive)
   - When: session-start; never queried explicitly
   - Latency: passive load
   - NOT for: anything queried; pointers and one-line facts only

### Write order (capture)

| Kind of fact | Tier |
|---|---|
| One-line pointer / preference / static stable fact | Tier 4 (`MEMORY.md`) |
| Synthesised durable artifact (architecture, runbook, policy) | Tier 1 (wiki) |
| Dated decision / lesson / supersession (validity matters) | Tier 3 (Graphiti `add_episode`, `group_id=tom-personal`) |
| Source-code structure | Tier 2 (GitNexus, automatic; no operator write) |

### Promotion rules

- **Wiki → Graphiti supersession**: when a wiki page is superseded, set
  `superseded_by: <slug>` AND write a Graphiti episode capturing the date
  and reason. Wiki = current state; Graphiti = the trail.
- **Graphiti → Wiki**: if a Graphiti episode crystallises into a stable
  pattern referenced in 3+ sessions, distil into wiki. Graphiti episode
  remains (history); wiki page is the new front door.
- **Auto-memory → Wiki**: an auto-memory entry that grows past one line
  (sub-bullets, code snippets) is a wiki candidate. Migrate; leave a
  one-line pointer in `MEMORY.md`.

## Cross-references

- [Tier-of-truth ADR](git:_bmad-output/planning-artifacts/products/context-stack/adrs/ADR-013-tier-of-truth-division.md)
- [Wiki schema](_schema)
- [Exit ramps](exit-ramps)
- [Context Stack project](ai-dev-context-stack)
```

### `wiki/runbooks/exit-ramps.md` content (sketch)

```markdown
---
title: "Context Stack — exit ramps for adopted components"
slug: exit-ramps
category: runbooks
last_reviewed: 2026-04-25
owner: tomamourette
related_pages: [context-stack-query-hierarchy]
related_frs: [FR-CG-010, FR-MEM-012, FR-MEM-014]
related_adrs: [ADR-007, ADR-012]
status: stable
supersedes: []
superseded_by: null
---

## Summary

Documented + dry-run-validated escape paths for both GitNexus (Tier 2) and
Graphiti (Tier 3). Both ramps complete in ≤ 1 day operator-wall-time
(NFR-MAINT-001) and were measured during E4-S10 at < 5 minutes wall-time
each.

## Context

NFR-SUPP-002 mandates a documented exit ramp per adopted component. R1
GitNexus abandonment risk and R5 cloud dependency for Graphiti motivate
this. Per ADR-012 (GitNexus) and ADR-007 (Graphiti).

## Procedure

### GitNexus → CodeGraphContext or graphify

GitNexus stores its graph in LadybugDB internally. Our wrapper exports it
to NDJSON in the schema documented in ADR-012:

    bash homelab-playbook/scripts/gitnexus-export.sh > graphexport.ndjson

NDJSON shape:
    {"type":"node","id":"...","labels":["Function"],"props":{...}}
    {"type":"edge","id":"...","src":"...","dst":"...","kind":"REFERENCES","props":{...}}

To replay into CodeGraphContext (Neo4j-MCP) or graphify, use their respective
ingestion runbooks. The NDJSON IS the migration artifact.

**Last validated:** [DATE-OF-AC5-AC6 run]; export size [LINE-COUNT]; wall-time [SECONDS].

### Graphiti → Mem0 / OMEGA-revival / fresh-Graphiti

Two layers of insurance per ADR-007:

**Cypher dump (snapshot):**

    ssh ct-ai-01.tail-scale.ts.net 'sudo bash /srv/graphiti/scripts/cypher-export.sh' > graphiti-cypher.json

This produces the full graph as JSON. To restore into a fresh FalkorDB or
Neo4j: standard `LOAD JSON` Cypher invocation in the new instance.

**Episode-replay log (forward-replay):**

    ssh ct-ai-01.tail-scale.ts.net 'sudo journalctl -u docker -t graphiti-mcp --since "X days ago" | grep -E "add_episode|episode_body"' > replay.log

To replay: parse each `add_episode` call from the log and re-issue against
the new memory tool's API. This works for Mem0, OMEGA, or any system that
accepts add-episode-like writes.

**Last validated:** [DATE-OF-AC7-AC8 run]; Cypher export size [SIZE]; replay
log line count [COUNT]; wall-time [SECONDS].

## Cross-references

- [Query hierarchy](context-stack-query-hierarchy)
- [Graphiti backup ADR](git:_bmad-output/planning-artifacts/products/context-stack/adrs/ADR-007-graphiti-backup-strategy.md)
- [GitNexus export ADR](git:_bmad-output/planning-artifacts/products/context-stack/adrs/ADR-012-gitnexus-graph-export-wrapper.md)
```

### Why dry-run is enough (not a full migration)

NFR-SUPP-002 says "documented exit ramp." It does NOT mandate a full migration to a successor tool — that's premature. The dry-run (export → schema-validate → replay-format-check) proves: (a) the export works, (b) the format matches the documented spec, (c) the operator could perform the migration in finite time if they had to. Going further (actually deploying CodeGraphContext or Mem0 for the round-trip) is wasted effort if neither is needed today.

### NOT in scope

- Does NOT install CodeGraphContext, Mem0, or any successor tool.
- Does NOT migrate live data (the operator migrates only IF triggered by R1/R5; this story makes that future migration cheap).
- Does NOT update `index.md`'s "Recently updated" beyond what `wiki-lint.sh --regen` does.

## Test Plan

**Pre-flight:**
```bash
# Confirm prior outputs exist
test -x homelab-playbook/scripts/gitnexus-export.sh        # E2-S07
ssh ct-ai-01.tail-scale.ts.net 'test -x /srv/graphiti/scripts/cypher-export.sh'   # E3-S07
ssh ct-ai-01.tail-scale.ts.net 'docker compose -f /srv/graphiti/docker-compose.yml ps'   # graphiti-mcp Up
ls homelab-playbook/wiki/architecture/   # E4-S01/S02 substrate exists
```

**Run exit-ramp dry-runs:**
```bash
# GitNexus export (AC5)
START=$(date +%s); bash homelab-playbook/scripts/gitnexus-export.sh > /tmp/e4-s10-gitnexus-export.ndjson; END=$(date +%s)
echo "wall-time: $((END-START))s"
wc -l /tmp/e4-s10-gitnexus-export.ndjson
head -1 /tmp/e4-s10-gitnexus-export.ndjson | jq .

# Schema-replay dry-run (AC6)
bash homelab-playbook/scripts/gitnexus-export-replay-dryrun.sh /tmp/e4-s10-gitnexus-export.ndjson

# Graphiti Cypher export (AC7)
START=$(date +%s); ssh ct-ai-01.tail-scale.ts.net 'sudo bash /srv/graphiti/scripts/cypher-export.sh' > /tmp/e4-s10-graphiti-cypher.json; END=$(date +%s)
echo "wall-time: $((END-START))s"
jq '.results | length' /tmp/e4-s10-graphiti-cypher.json

# Graphiti episode replay log (AC8)
ssh ct-ai-01.tail-scale.ts.net 'sudo journalctl -CONTAINER_NAME=graphiti-mcp --since "30 days ago" 2>/dev/null || sudo docker compose -f /srv/graphiti/docker-compose.yml logs --since 720h graphiti-mcp' \
  | grep -E "add_episode|episode_body" > /tmp/e4-s10-replay.log
wc -l /tmp/e4-s10-replay.log
```

**Author wiki pages (Edit/Write):**
- `wiki/architecture/context-stack-query-hierarchy.md` per AC1-AC4
- `wiki/runbooks/exit-ramps.md` per AC9, with measured wall-times from above

**AC verification:**
```bash
bash homelab-playbook/scripts/wiki-lint.sh                    # AC1, AC9, AC11
yq '.related_pages' homelab-playbook/wiki/architecture/context-stack-query-hierarchy.md
yq '.related_pages' homelab-playbook/wiki/runbooks/exit-ramps.md   # AC12 cross-refs
grep -E '## (Read order|Write order|Promotion rules)' homelab-playbook/wiki/architecture/context-stack-query-hierarchy.md   # AC2-AC4
grep -E 'GitNexus → |Graphiti → ' homelab-playbook/wiki/runbooks/exit-ramps.md   # AC9
grep -E '\[DATE|\[LINE-COUNT|\[SECONDS' homelab-playbook/wiki/runbooks/exit-ramps.md && echo "FAIL: stub left" || echo "PASS"
```

**Rollback:**
```bash
git rm homelab-playbook/wiki/architecture/context-stack-query-hierarchy.md
git rm homelab-playbook/wiki/runbooks/exit-ramps.md
git rm homelab-playbook/scripts/gitnexus-export-replay-dryrun.sh
```

## Dependencies

- **Blocks:** E4-S11 (KPI scorecard references both pages); E4-S12 (retro references the dry-run results)
- **Blocked by:** E4-S01 + E4-S02 (wiki tree exists), E2-S07 (`scripts/gitnexus-export.sh` exists), E3-S07 (`/srv/graphiti/scripts/cypher-export.sh` exists)

## Risks and Mitigations

| Risk | Source | Mitigation |
|---|---|---|
| GitNexus export schema drifts from ADR-012 spec | Upstream change | AC6 schema-validation script catches; if drift, update ADR-012 + the wrapper in a follow-up commit |
| Graphiti monthly Cypher export hasn't run yet by Sprint 4 (cron cadence) | Cadence | AC7 manually invokes the script ON-DEMAND, not waiting for cron; first export wall-time captures |
| Cypher dump > 100 MB at end-of-month (large graph) | Data volume | Page reports actual size; if > 100 MB, document as a forward concern (no action this sprint); FalkorDB at < 200 MB RSS makes this unlikely |
| Episode-replay log lookup fails (logs rotated) | Log retention | E3-S04 set monthly rotation; AC8 uses `--since 30 days ago` matching the rotation; if logs are missing, document the gap as a forward concern (the AOF + RDB paths are still intact) |
| The page becomes stale (`last_reviewed > 6 months`) | Wiki hygiene | `wiki-lint.sh` warn-level on stale; quarterly wiki-review backlog ticket per arch §11 AR6 |
| Operator never runs the dry-run again post-this-story → ramp untested when actually needed | Discipline | E4-S12 retro creates a follow-up annual-drill backlog ticket; this story's first run is the proof, not a one-off |

## Definition of Done

- [ ] All ACs pass (AC1–AC12)
- [ ] `homelab-playbook/wiki/architecture/context-stack-query-hierarchy.md` committed and lint-clean
- [ ] `homelab-playbook/wiki/runbooks/exit-ramps.md` committed and lint-clean (with measured wall-times filled in, NOT stub `[DATE]` placeholders)
- [ ] `homelab-playbook/scripts/gitnexus-export-replay-dryrun.sh` committed and executable
- [ ] Evidence artifacts preserved at `tests/e4-s10-{gitnexus-export.ndjson,graphiti-cypher.json,replay.log}` for the retro
- [ ] `index.md` regenerated to list both new pages
- [ ] No regression in E2/E3 functionality from running the export scripts
- [ ] Cross-reference task added: `AT-FR-WIKI-007a`, `AT-FR-CG-010a`, `AT-FR-MEM-012a` (Phase 5a will populate)
