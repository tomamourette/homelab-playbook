---
type: story
epic: E4
id: E4-S02
title: "Bootstrap initial 3-5 wiki seed entries from existing project memories"
size: 1.5d
priority: SHOULD
fr_refs: [FR-WIKI-006, FR-WIKI-010, FR-DEP-005]
adr_refs: [ADR-006, ADR-013]
status: draft
date: 2026-04-25
---

# E4-S02: Bootstrap initial 3-5 wiki seed entries from existing project memories

## User Story

As **tomamourette** (homelab operator), I want **3-5 high-leverage wiki entries authored by hand-distilling existing project memory notes (Tailscale-only network policy, PVE 9.x cluster topology, decommission runbook, hybrid_gemma_serving target, ai-dev-context-stack deploy procedure)**, so that **the wiki tier has actual *content* the operator and Claude Code will use in the 4-week pilot, satisfying FR-WIKI-006 (≥ 3 seeds × ≥ 3 sessions each) and giving E4-S03's wiki-query skill something to retrieve at smoke-test time**.

## Background and Context

ADR-006 ships the schema (E4-S01); ADR-009 ships the read-on-demand pattern (E4-S03). This story ships the **content seeds** that close FR-WIKI-006. Per ADR-014, FR-WIKI-006 is now SHOULD (3×3 sessions; accept 2×2 with documented gap as ship-able). FR-WIKI-010 is the explicit scope guard — bulk authorship is out of scope; the operator curates over time, the Phase 3 deliverable is the *tier mechanism* with a small set of hand-distilled seeds.

The seed list is pinned here (closes EQ4 from epics.md §9). Each seed is distilled from an existing memory note in `/home/developer/.claude/projects/-home-developer-workspace-homelab/memory/` (Tier-4 source) and refactored to ADR-006 schema. Per ADR-013, these are *current-state* artifacts (architecture / runbook / pointer) — not dated decisions (those stay in Graphiti).

## Acceptance Criteria

### AC1: Five seed entries are authored, each conforming to ADR-006 schema

- **Given** the wiki tree from E4-S01 is bootstrapped
- **When** I list the wiki tree
- **Then** the following five files exist and pass `wiki-lint.sh`:

| File | Slug | Category | Source memory note |
|---|---|---|---|
| `architecture/network-tailscale-policy.md` | `network-tailscale-policy` | architecture | `project_phone_notifications_tailscale.md` |
| `architecture/pve-cluster-topology.md` | `pve-cluster-topology` | architecture | `project_pve3_storage_redesign.md` + `project_pve_node_cooling.md` + `project_pve9_ha_rules_migration.md` |
| `runbooks/decommission-context-stack-phase-1.md` | `decommission-context-stack-phase-1` | runbooks | E1 deliverable + decommission doc from E1-S07 |
| `projects/hybrid-gemma-serving.md` | `hybrid-gemma-serving` | projects | `project_hybrid_gemma_serving.md` |
| `projects/ai-dev-context-stack.md` | `ai-dev-context-stack` | projects | This product's brief + architecture (cross-link only, NOT duplication) |

(Five seeds, exceeding the FR-WIKI-006 minimum of 3, gives slack for a 2-of-5 fall-through under ADR-014's relaxed bar.)

### AC2: Each seed has all required ADR-006 frontmatter fields

- **Given** AC1 holds
- **When** I run `bash homelab-playbook/scripts/wiki-lint.sh`
- **Then** exit code is 0; reports `pages: 7` (5 seeds + `_schema` + `index`); no broken slugs, no broken FR refs, no broken ADR refs

### AC3: Each seed has body sections in the prescribed order

- **Given** AC1 holds
- **When** I grep each seed for H2 headers
- **Then** each contains, in order: `## Summary` (≤ 80 words), `## Context`, `## Procedure / Decision / Definition` (whichever fits the category), `## Cross-references`

### AC4: `index.md` is regenerated to list the five seeds

- **Given** AC1 and AC2 hold
- **When** I run `bash homelab-playbook/scripts/wiki-lint.sh --regen`
- **Then** `homelab-playbook/wiki/index.md` is updated: each category's bullet list now contains the new slugs with one-line summaries; "Recently updated" section lists the 5 seeds with their `last_reviewed` dates; total file size still < 5 KB

### AC5: `projects/ai-dev-context-stack.md` is a cross-link, not a duplicate

- **Given** the project deliverable lives at `_bmad-output/planning-artifacts/products/context-stack/`
- **When** I read `projects/ai-dev-context-stack.md`
- **Then** the body Procedure section is ≤ 200 words and consists of a one-paragraph summary plus a `git:` link list pointing to `brief.md`, `prd.md`, `architecture.md`, and `epics.md` — the wiki page does NOT inline the brief/PRD/arch content (FR-WIKI-010 scope guard)

### AC6: Each seed carries accurate `related_frs` / `related_adrs` traceability

- **Given** AC1 holds
- **When** I inspect each seed's frontmatter
- **Then** `related_frs` and `related_adrs` lists name only IDs that exist in the PRD and `adrs/` respectively; for example: network-tailscale-policy has `related_frs: [FR-MEM-003, NFR-PRIV-003]` and `related_adrs: [ADR-001]`; pve-cluster-topology has `related_frs: [FR-MEM-001]` and `related_adrs: []`; decommission-context-stack-phase-1 has `related_frs: [FR-DEC-009, FR-DEC-010, FR-DEC-011]` and `related_adrs: [ADR-010]`; hybrid-gemma-serving has `related_frs: [FR-LLM-001, FR-LLM-005]` and `related_adrs: [ADR-011]`; ai-dev-context-stack has all the FRs implicit and `related_adrs: [ADR-006, ADR-013]`

### AC7: Operator log captures ≥ 3 distinct Claude Code sessions reading each seed (FR-WIKI-006 SHOULD)

- **Given** the seeds are committed
- **When** I run 3 distinct Claude Code sessions during Sprint 4 in `~/workspace/homelab/homelab-playbook/`, each prompted with one of: "what's our tailscale policy?", "describe the PVE cluster topology", "how did we decommission the prior memory tools?", "what's the hybrid-gemma-serving plan?", "what is the context-stack project?"
- **Then** the operator log at `homelab-playbook/wiki/_session-log.md` (or equivalent — see Implementation Notes) records ≥ 3 distinct session IDs/timestamps per seed, totalling ≥ 15 reads across the 5 seeds; per ADR-014 the SHOULD bar is met if ≥ 3 of 5 seeds hit ≥ 3 sessions (rest documented as gap)

### AC8: No seed exceeds 4 KB body size

- **Given** the seeds are committed
- **When** I run `wc -c homelab-playbook/wiki/{architecture,runbooks,decisions,glossary,projects}/*.md | sort -n`
- **Then** every file is < 4096 bytes — keeps reads fast (FR-WIKI-005), forces operator to distil rather than dump

### AC9: Each seed page passes the slug-based cross-reference rule

- **Given** the seeds are committed
- **When** wiki-lint runs
- **Then** every `[text](slug)` link in the body resolves to an existing wiki slug; every `[text](git:path)` link resolves to a path that exists in the homelab repo at `git rev-parse HEAD`

## Implementation Notes

### Seed authoring approach

Each seed is **hand-distilled**, not auto-extracted. The operator (or director-Claude) reads the source memory note(s), restates the *current-state* facts (per ADR-013) in ≤ 4 KB, drops temporal/historical detail (that stays in Graphiti), and adds traceability links to FRs/ADRs.

Concrete distillation template per seed:

```markdown
---
title: "<concise title, e.g., Tailscale-only network policy for phone-facing services>"
slug: <kebab-case slug matching filename>
category: <architecture | runbooks | decisions | glossary | projects>
last_reviewed: 2026-04-25
owner: tomamourette
related_pages: [<other slugs>]
related_frs: [<FR-IDs>]
related_adrs: [<ADR-IDs>]
status: stable
supersedes: []
superseded_by: null
---

## Summary
<≤ 80 words; the TL;DR a Claude Code session needs>

## Context
<why this exists / what problem it solves>

## Procedure | Decision | Definition
<body — depends on category>

## Cross-references
- [related wiki page](slug)
- [git artifact](git:path/from/repo/root)
```

### Per-seed distillation specs (operator-pinned, closes EQ4)

1. **`network-tailscale-policy`** — From `project_phone_notifications_tailscale.md`. Summary: phone-facing (and increasingly all service-facing-from-untrusted-network) services default to Tailscale-only access; Pi-hole local-override + Traefik covers home-wifi-without-Tailscale separately. Cross-ref ADR-001 (FalkorDB-on-ct-ai-01-via-Tailscale follows the same pattern); cross-ref `pve-cluster-topology`.

2. **`pve-cluster-topology`** — From the three PVE memory notes. Summary: 3-node PVE 9.x cluster (pve1/pve2/pve3); pve1+pve2 passive-cooled, pve3 has active fans; ZFS-mirror rpool on pve2 (LVM→ZFS migrated 2026-04-24); pve3 has the OCULink dGPU slot for the local LLM stack. Procedure section: HA-rules migration note (PVE 9.1+ uses `ha-manager rules add node-affinity`, not the deprecated groups). Cross-ref ADR-001 (Graphiti runs on ct-ai-01 inside this cluster).

3. **`decommission-context-stack-phase-1`** — From E1's decommission doc (E1-S07). Summary: how Phase 1 removed MemPalace + OMEGA in a single PR, 8 sequenced commits, tagged `phase-1-decommission-complete`; how to re-execute the process (or use it as a template) for any future tier removal. Procedure: link to ADR-010, link to E1-S08 grep/process gates, link to the actual decommission doc in `homelab-playbook/docs/decommission/`.

4. **`hybrid-gemma-serving`** — From `project_hybrid_gemma_serving.md`. Summary: separate epic delivering Unsloth UD-Q5_K_M reasoner + FastAPI proxy + LiteLLM gateway on pve3 with Vulkan; Context Stack's Phase 4 LiteLLM bridge (E4-S05 + E4-S06) is *consumer*, not provider. Cross-ref ADR-011 (Phase 4 implementation), `project:context-stack` (this product).

5. **`ai-dev-context-stack`** — From this product's planning artifacts. Summary: ≤ 80-word "this is what Context Stack is" — tiered context substrate (wiki + GitNexus + Graphiti + auto-memory). Body is **just cross-links** to the brief, PRD, architecture, epics in `_bmad-output/planning-artifacts/products/context-stack/`. NO duplication (FR-WIKI-010).

### Operator session log

Add `homelab-playbook/wiki/_session-log.md` (also wiki-page-formatted, slug `_session-log`, category `glossary`) — a tiny operator-tracked file where each row is one session × one seed read:

```
| ISO timestamp | Session label | Seed slug | Note |
|---|---|---|---|
| 2026-04-26T10:00Z | s4-day1 | network-tailscale-policy | Asked re: ntfy access, wiki-query returned page |
| 2026-04-26T14:00Z | s4-day1 | pve-cluster-topology | Asked re: ct-ai-01 location, page consulted |
```

This is what AC7 measures. Lightweight; the operator updates it as part of weekly retro (E4-S09 cross-references it).

### Authoring order

To avoid wide-surface review: author seeds in five sequential commits on the `phase-3-wiki-tier` branch, each named `wiki: seed <slug>`. Run `wiki-lint.sh --regen` after the fifth seed commits, in a sixth commit `wiki: regen index.md`.

## Test Plan

**Pre-flight:**
```bash
bash homelab-playbook/scripts/wiki-lint.sh   # baseline: only _schema + index after E4-S01
ls homelab-playbook/wiki/{architecture,runbooks,projects}/   # expect: empty (.gitkeep only)
```

**Author seeds (Edit/Write — one per file):** see Implementation Notes for the five distillation specs.

**Regenerate index:**
```bash
bash homelab-playbook/scripts/wiki-lint.sh --regen
```

**AC verification:**
```bash
# AC1
ls -1 homelab-playbook/wiki/architecture/
ls -1 homelab-playbook/wiki/runbooks/
ls -1 homelab-playbook/wiki/projects/
# AC2
bash homelab-playbook/scripts/wiki-lint.sh
# AC3 (one per seed)
for f in homelab-playbook/wiki/{architecture,runbooks,projects}/*.md; do
  echo "=== $f ==="
  grep -E '^## (Summary|Context|Procedure|Decision|Definition|Cross-references)' "$f"
done
# AC4
wc -c homelab-playbook/wiki/index.md   # < 5120
grep -c "^- " homelab-playbook/wiki/index.md   # entries listed
# AC5
wc -w homelab-playbook/wiki/projects/ai-dev-context-stack.md   # body words ≤ ~250 to leave buffer for frontmatter
grep -c "git:" homelab-playbook/wiki/projects/ai-dev-context-stack.md   # ≥ 4 git: links
# AC6 (manual inspection)
for f in homelab-playbook/wiki/{architecture,runbooks,projects}/*.md; do
  yq '.related_frs, .related_adrs' "$f"
done
# AC8
find homelab-playbook/wiki/ -type f -name '*.md' -size +4k   # expect: empty
# AC9
bash homelab-playbook/scripts/wiki-lint.sh   # already enforces it
```

**AC7 (post-commit, runs over Sprint 4 calendar week):**
```bash
# After 3 distinct sessions × 5 seeds, count rows in _session-log.md per seed:
for slug in network-tailscale-policy pve-cluster-topology decommission-context-stack-phase-1 hybrid-gemma-serving ai-dev-context-stack; do
  echo -n "$slug: "
  grep -c "| $slug |" homelab-playbook/wiki/_session-log.md
done
# Expect ≥ 3 for at least 3 seeds (SHOULD bar per ADR-014)
```

**Rollback:**
```bash
git checkout HEAD~6 -- homelab-playbook/wiki/   # discards the five seed commits + regen
```

## Dependencies

- **Blocks:** E4-S03 (skill needs index.md and at least one seed for smoke-tests), E4-S10 (query-hierarchy doc lives alongside seeds), E4-S11 (FR-WIKI-006 is part of the week-4 acceptance suite)
- **Blocked by:** E4-S01 (schema + lint must exist)

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Operator over-distils and seed has insufficient content for Claude Code to actually use | AC8 caps page size but no AC enforces minimum; the AC7 session-log drill exposes uselessness within Sprint 4 |
| AC7 (3 sessions × 3 seeds) doesn't hit by Sprint 4 retro | ADR-014 SHOULD bar accepts 2 sessions × 2 seeds; gap is documented in E4-S12 retro and a "wiki content review" backlog ticket is created |
| `projects/ai-dev-context-stack.md` invites duplication of brief/PRD/arch | AC5 hard-caps body length and demands `git:` cross-links; reviewer-of-one acknowledges in PR body that NO duplication is the rule |
| Seed `related_frs` drift if PRD changes mid-sprint | wiki-lint AC2 catches it; operator runs lint on every seed-edit; PRD-change story would naturally include a wiki-lint sweep |
| EQ4 mid-sprint scope drift (operator wants to add a 6th seed) | This story pins the list at 5; new seeds are post-E4 backlog work, captured in retro (E4-S12) |

## Definition of Done

- [ ] All ACs pass (AC1–AC9, with AC7 measured at end of Sprint 4)
- [ ] Five seed PR commits + one `wiki: regen index.md` commit on `phase-3-wiki-tier` branch
- [ ] `homelab-playbook/wiki/_session-log.md` exists and is being updated (running) by the operator
- [ ] No regression in `MEMORY.md` auto-memory loading observed during seed-authoring sessions
- [ ] Cross-reference task added: `AT-FR-WIKI-006a` (Phase 5a will populate)
- [ ] If AC7 falls short of 3×3 by Sprint 4 retro, a `wiki-content-review-Q3-2026` backlog ticket is created
