---
title: "Homelab wiki — index"
slug: index
category: glossary
last_reviewed: 2026-04-27
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
  - _(seeds added in E4-S02)_
- **runbooks/** — step-by-step operator procedures (deploy, rebuild, rotate)
  - _(seeds added in E4-S02)_
- **decisions/** — distilled prior decisions (Graphiti-overlap is acceptable)
  - _(seeds added in E4-S02)_
- **glossary/** — term definitions
  - [Wiki page schema](_schema)
- **projects/** — per-project pointers (cross-link only; do NOT duplicate `_bmad-output/`)
  - _(seeds added in E4-S02)_

## Recently updated

- `_schema.md` — 2026-04-27 (E4-S01 bootstrap)
- `index.md` — 2026-04-27 (E4-S01 bootstrap)

_(Section will be auto-populated by `scripts/wiki-lint.sh --regen` once the
lint script ships per the deferred-items note in [Wiki page schema](_schema).)_

## Bootstrap status

This is the E4-S01 bootstrap landing. Currently shipped:

- `index.md` (this file)
- `_schema.md` (frontmatter + body conventions per ADR-006)

Deferred to follow-up (per the Sprint 4 kickoff scope decision):

- Five category subdirectories (`architecture/`, `runbooks/`, `decisions/`,
  `glossary/`, `projects/`) with `.gitkeep` placeholders.
- `scripts/wiki-lint.sh` link checker.
- Pre-commit hook wiring.

Seed entries land in E4-S02 (operator picks content).
