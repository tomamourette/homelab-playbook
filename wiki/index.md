---
title: "Homelab wiki — index"
slug: index
category: meta
last_reviewed: 2026-07-28
owner: tomamourette
related_pages: []
related_frs: [FR-WIKI-002, FR-WIKI-003, FR-WIKI-004, FR-WIKI-007, FR-WIKI-008]
related_adrs: [ADR-006, ADR-009, ADR-013]
status: stable
supersedes: []
superseded_by: null
---

# Homelab wiki

Curated, file-based, zero-MCP knowledge base. Single source of truth for
*current state* — architectural decisions, runbooks, conventions. Distinct
from Graphiti (dated decision trail), auto-memory (one-line pointers), and
GitNexus (code structure). See ADR-013 for the full tier-of-truth division
and ADR-006 for the file-tree decision.

## How to add a page

See [Wiki page schema](_schema) for the frontmatter spec, body conventions,
filename rules, and a copy-pasteable new-page template.

## By category

- **architecture/** — cross-product architectural decisions (network, cluster, storage)
  - [Tailscale access policy](tailscale-policy) (E4-S02; widened 2026-07-28
    to cover Tailscale SSH)
  - [Remote access topology](remote-access-topology) (2026-07-28)
  - [Hybrid Gemma serving](hybrid-gemma-serving) (E4-S02)
- **runbooks/** — step-by-step operator procedures (deploy, rebuild, rotate)
  - [Create a new project container](create-project-container) (2026-05-09;
    step 8 updated 2026-07-28)
  - [Remote access recovery](remote-access-recovery) (2026-07-28)
  - [Test the Context Stack — operator verification runbook](test-the-stack) (post-Sprint-4)
  - [Weekly observability digest — template](weekly-observability-digest) (E4-S09)
  - [wiki-query skill](wiki-query-skill) (E4-S03)
  - [PVE 9 HA migration](pve9-ha-migration) (E4-S02)
  - **runbooks/exit-ramps/** — per-tier portability runbooks (E4-S10)
    - [Wiki tier — exit ramp](wiki-exit-ramp)
    - [GitNexus tier — exit ramp](gitnexus-exit-ramp)
    - [Graphiti tier — exit ramp](graphiti-exit-ramp)
    - [Auto-memory tier — exit ramp](auto-memory-exit-ramp)
- **decisions/** — distilled prior decisions (Graphiti-overlap is acceptable)
  - [Context Stack query hierarchy](query-hierarchy) (E4-S10, canonical
    routing table per ADR-013)
  - [Weekly digest — 2026-W18](weekly-digest-2026-w18) (E4-S09 first instance)
- **glossary/** — term definitions
  - _(seeds added in E4-S02; none yet)_
- **projects/** — per-project pointers (cross-link only; do NOT duplicate `_bmad-output/`)
  - _(seeds added in E4-S02; none yet)_
- **meta** (root-level) — wiki self-description
  - [Wiki page schema](_schema)

## Recently updated

- `runbooks/remote-access-recovery.md` — 2026-07-28 (new; keyless
  remote-access design)
- `architecture/remote-access-topology.md` — 2026-07-28 (new)
- `architecture/tailscale-policy.md` — 2026-07-28 (widened to cover
  Tailscale SSH; added out-of-repo ACL section)
- `runbooks/create-project-container.md` — 2026-07-28 (step 8 rewritten
  to stop redistributing SSH private keys; previously 2026-05-09 post
  ct-saply-ai create)
- `decisions/query-hierarchy.md` — 2026-04-27 (E4-S10)
- `runbooks/exit-ramps/*.md` — 2026-04-27 (E4-S10, four pages)
- `decisions/weekly-digest-2026-w18.md` — 2026-04-27 (E4-S09)
- `runbooks/weekly-observability-digest.md` — 2026-04-27 (E4-S09)
- `runbooks/wiki-query-skill.md` — 2026-04-27 (E4-S03)
- `architecture/{tailscale-policy,hybrid-gemma-serving}.md` — 2026-04-27 (E4-S02)
- `runbooks/pve9-ha-migration.md` — 2026-04-27 (E4-S02)
- `_schema.md` — 2026-04-27 (E4-S01 bootstrap)

_(Section will be auto-populated by `scripts/wiki-lint.sh --regen` once the
regen mode ships; until then it is hand-maintained per story.)_

## Bootstrap status

E4-S01/S02/S03/S09/S10 have shipped. Currently populated:

- `_schema.md` + `index.md` (E4-S01).
- `architecture/` — 2 seeds (E4-S02).
- `runbooks/` — 3 seeds (E4-S02 + S03 + S09).
- `runbooks/exit-ramps/` — 4 per-tier exit-ramp runbooks (E4-S10).
- `decisions/` — query-hierarchy canonical routing table (E4-S10) +
  weekly digest 2026-W18 (E4-S09).
- `scripts/wiki-lint.sh` — shipped and passing.

Still empty (seeds welcomed when content emerges):

- `glossary/` — term definitions.
- `projects/` — per-project pointer pages.
