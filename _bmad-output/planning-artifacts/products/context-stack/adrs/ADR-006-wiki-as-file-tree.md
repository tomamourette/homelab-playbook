---
adr: 006
title: "Wiki tier as a file-based markdown tree under homelab-playbook/wiki/"
status: accepted
date: 2026-04-25
authors: tomamourette (via BMAD director Claude)
context_question: Q3
---

# ADR-006: Wiki tier as a file-based markdown tree under homelab-playbook/wiki/

## Context

The director-resolved decision is: LLM Wiki at `homelab-playbook/wiki/`, file-based, zero-MCP. PRD FR-WIKI-001 through FR-WIKI-010 and Q3 ask the architecture phase to define:
- Directory structure under `homelab-playbook/wiki/`
- Page-frontmatter schema (YAML)
- Section conventions
- Cross-reference syntax
- Required metadata: last-reviewed-date, owner, related-pages, related-FRs

Design objective: human-writeable, machine-parseable, link-checkable, and consumable by Claude Code without a daemon, DB, or LLM extraction at retrieval time (FR-WIKI-005 < 200 ms file-read).

## Decision

### Directory structure

```
homelab-playbook/wiki/
├── index.md                          # Entry point; loaded at session start (FR-WIKI-004)
├── _schema.md                        # This page schema (machine-readable spec)
├── architecture/                     # Architectural decisions (cross-product)
│   ├── network-tailscale-policy.md
│   ├── pve-cluster-topology.md
│   └── storage-zfs-conventions.md
├── runbooks/                         # Step-by-step operator procedures
│   ├── ct-deploy.md
│   ├── pve-node-rebuild.md
│   └── secrets-rotation.md
├── decisions/                        # Distilled prior decisions (Graphiti-overlap is acceptable)
│   ├── pve9-ha-rules-migration.md
│   └── pve3-storage-redesign.md
├── glossary/                         # Term definitions, single-page, alphabetical
│   └── homelab-glossary.md
└── projects/                         # Per-project pointers (NOT full content; cross-link)
    ├── context-stack.md
    ├── hybrid-gemma-serving.md
    └── sparkle-cps.md
```

### Page frontmatter schema (YAML)

Every wiki page MUST start with:

```yaml
---
title: "Tailscale-only network policy for phone-facing services"
slug: network-tailscale-policy             # URL/anchor-safe; matches filename without .md
category: architecture                      # architecture | runbooks | decisions | glossary | projects
last_reviewed: 2026-04-25                   # ISO date; review SHOULD be ≤ 6 months old
owner: tomamourette                         # Single-operator product, but explicit for forward-compat
related_pages:                              # Wiki-internal links (relative path or slug)
  - architecture/pve-cluster-topology
  - runbooks/ct-deploy
related_frs:                                # PRD requirements traced
  - FR-MEM-003                              # Tailscale-bind for Graphiti
  - NFR-PRIV-003                            # Tailscale-only phone-facing
related_adrs:                               # ADRs that touch this page
  - ADR-001
status: stable                              # draft | stable | superseded
supersedes: []                              # list of slugs (or empty list)
superseded_by: null                         # slug, or null
---
```

### Section conventions (body)

Pages use the following H2 sections in order, where applicable:

```markdown
## Summary
One paragraph, < 80 words. The TL;DR a Claude Code session needs.

## Context
Why this exists / what problem it solves.

## Procedure / Decision / Definition
Body — depends on category.

## Cross-references
Inline links use `[text](slug)` form (slug-based, not relative path) so renames don't break.
```

### Cross-reference syntax

- **Wiki-internal:** `[text](slug)` — e.g., `[PVE cluster topology](pve-cluster-topology)`. A link checker (the same one in `_schema.md`) resolves slug → file.
- **External (homelab-playbook git tree):** `[text](git:path/from/repo/root)` — e.g., `[Hermes verify](git:homelab-playbook/playbooks/verify.yml)`.
- **External (web):** standard markdown URL.

### Link-checker rules (lightweight; lives as a `scripts/wiki-lint.sh` in homelab-playbook)

1. Every page parses as YAML-frontmatter + markdown.
2. Every `slug` is unique in the tree.
3. Every `related_pages` entry resolves to an existing slug.
4. Every `related_frs` entry exists in the latest PRD.
5. Every `related_adrs` entry exists in `adrs/`.
6. `last_reviewed` is ≤ 6 months old (warn-level, not fail).

### `index.md`

`index.md` is the only page Claude Code is *expected* to read at session start (FR-WIKI-004). It contains:
- A one-paragraph "what's in this wiki" summary.
- A bulleted index by category, with each bullet linking to a slug + a one-line description.
- A "recently updated" section auto-populated by `wiki-lint.sh`.

This keeps session-start cost to one file-read of a small index, not a full tree scan.

## Consequences

**Positive.**
- Plain markdown + git → zero new infrastructure. Backups are inherent (NFR-PORT-003).
- YAML frontmatter is parseable by any tool (`yq`, `python-frontmatter`, `awk`); link-checker is shell-scriptable.
- Slug-based cross-references survive file renames.
- `last_reviewed` hygiene catches stale content before it causes wrong answers.
- `related_frs` / `related_adrs` create a bidirectional trace between PRD and wiki; doc rot becomes detectable.

**Negative.**
- No semantic search at the wiki tier (intentional — that's Graphiti's job).
- Schema enforcement requires the operator to actually run `wiki-lint.sh` before committing; CI integration is a follow-up if needed.
- Slug-based linking has a learning curve vs relative paths; mitigated by `_schema.md` page.

**Neutral.**
- `projects/` subtree intentionally cross-links rather than duplicating content — single source of truth lives in `_bmad-output/planning-artifacts/products/<name>/`.

## Alternatives Considered

1. **SQLite database for the wiki** — rejected. Defeats zero-MCP goal; loses git-native version control; loses grep-ability.
2. **MDX or rich frontmatter (TOML, JSON)** — rejected. YAML matches the existing BMAD artifact convention (every PRD/ADR/brief uses YAML frontmatter). Consistency wins.
3. **Freeform markdown, no schema** — rejected. Loses link-checking, last-reviewed hygiene, and the FR / ADR backtrace.
4. **Hosted wiki (Outline, BookStack)** — rejected. New deploy surface, monthly cost, no git integration. Out-of-scope per brief NG9.

## Validation / Exit Ramp

- **Validation:** Phase 3 exit (FR-WIKI-006) — three seed entries authored, each consumed by ≥ 3 distinct Claude Code sessions; `wiki-lint.sh` exits 0 against the tree.
- **Exit ramp:** wiki content is plain markdown in git — inherently portable to any other markdown-based system (GitBook, Outline, MkDocs, Sphinx). No data conversion needed.
- **Reversal trigger:** if the operator finds themselves writing the same fact in three places (auto-memory + wiki + Graphiti), schema or scope is wrong — revisit the tier-of-truth lines in ADR-013.

## References

- Director-resolved decision: wiki location is `homelab-playbook/wiki/`
- PRD FR-WIKI-001 through FR-WIKI-010, NFR-PERF-003, NFR-PORT-003
- ADR-009 (wiki-query skill design, the read-side companion)
- ADR-013 (tier-of-truth division — wiki vs Graphiti vs auto-memory)
