---
title: "Wiki page schema"
slug: _schema
category: glossary
last_reviewed: 2026-04-27
owner: tomamourette
related_pages: []
related_frs: [FR-WIKI-002, FR-WIKI-003, FR-WIKI-004, FR-WIKI-008]
related_adrs: [ADR-006, ADR-009, ADR-013]
status: stable
supersedes: []
superseded_by: null
---

# Wiki page schema

The normative spec for every page under `homelab-playbook/wiki/`. This file is itself
a wiki page and conforms to the schema it documents. Source of truth: ADR-006
(`_bmad-output/planning-artifacts/products/context-stack/adrs/ADR-006-wiki-as-file-tree.md`).
If this file and ADR-006 disagree, ADR-006 wins; reconcile here.

## Summary

Wiki pages are plain markdown with YAML frontmatter, organised in a fixed five-category
file tree, cross-linked by slug (not relative path), and validated by a (pending)
`scripts/wiki-lint.sh` link checker. Zero MCP, zero database, zero LLM at retrieval
time per FR-WIKI-003 / FR-WIKI-005.

## Context

Per ADR-013, the wiki tier holds **current state** authoritative knowledge — distinct
from Graphiti (dated decision trail), auto-memory (one-line pointers), and GitNexus
(code structure). The schema must surface enough metadata (`last_reviewed`,
`related_pages`, `related_frs`, `related_adrs`, `supersedes` / `superseded_by`) to
keep that division enforceable as the tree grows.

`index.md` is the only file Claude Code is *expected* to read at session start
(FR-WIKI-004 + ADR-009). Per-page reads happen on-demand via the `wiki-query` skill
(E4-S03; not yet shipped).

## Procedure / Decision / Definition

### Frontmatter (required, YAML, every page)

Every wiki page MUST start with the following block. Order is recommended for
readability; only the keys are normative.

```yaml
---
title: "Human-readable page title"            # required, string
slug: kebab-case-slug                          # required, unique across the tree
                                               # matches filename without .md
category: architecture                         # required, one of:
                                               # architecture | runbooks | decisions
                                               # | glossary | projects
last_reviewed: 2026-04-27                      # required, ISO date (YYYY-MM-DD)
                                               # WARN if > 6 months stale (not fail)
owner: tomamourette                            # required, single string
related_pages:                                 # required, list of slugs (may be empty)
  - architecture/pve-cluster-topology
  - runbooks/ct-deploy
related_frs:                                   # required, list of FR-IDs (may be empty)
  - FR-MEM-003
  - NFR-PRIV-003
related_adrs:                                  # required, list of ADR-IDs (may be empty)
  - ADR-001
status: stable                                 # required, one of: draft | stable | superseded
supersedes: []                                 # required, list of slugs (may be empty)
superseded_by: null                            # required, slug or null
---
```

### Body section conventions (recommended, in order, where applicable)

```markdown
## Summary
One paragraph, < 80 words. The TL;DR a Claude Code session needs.

## Context
Why this exists / what problem it solves.

## Procedure / Decision / Definition
Body — depends on category:
- runbooks/ → numbered step procedure
- architecture/ → decision rationale + diagram (if any)
- decisions/ → distilled decision text + supersession history
- glossary/ → term definitions, alphabetical within page
- projects/ → cross-link summary; do NOT duplicate _bmad-output content

## Cross-references
Links to related wiki pages, git artifacts, external sources.
```

### Cross-reference syntax

| Target | Syntax | Example |
|---|---|---|
| Wiki-internal (slug-based) | `[text](slug)` | `[PVE cluster topology](pve-cluster-topology)` |
| Repo-internal (git tree) | `[text](git:path/from/repo/root)` | `[Hermes verify](git:homelab-playbook/playbooks/verify.yml)` |
| External web | `[text](https://...)` | standard markdown |

Slugs are preferred over relative paths so that file renames do not break links.
The (pending) `wiki-lint.sh` resolves `slug → file` at lint time.

### Filename convention

- Lowercase kebab-case: `network-tailscale-policy.md`, not `Network_Tailscale_Policy.md`.
- Filename (without `.md`) MUST equal the `slug` frontmatter value.
- Files live under their `category` subdirectory.

### Lint rules (per ADR-006 §Decision; enforced by `wiki-lint.sh` once shipped)

1. Every page parses as YAML-frontmatter + markdown.
2. Every `slug` is unique in the tree.
3. Every `related_pages` entry resolves to an existing slug.
4. Every `related_frs` entry exists in the latest PRD.
5. Every `related_adrs` entry exists in `_bmad-output/.../adrs/`.
6. `last_reviewed` ≤ 6 months old (warn-level, not fail).

Rules 1-5 fail the lint (exit 1). Rule 6 emits `WARN:` and exits 0.

### New-page template (copy-paste)

```markdown
---
title: "New page title"
slug: new-page-slug
category: architecture
last_reviewed: 2026-04-27
owner: tomamourette
related_pages: []
related_frs: []
related_adrs: []
status: draft
supersedes: []
superseded_by: null
---

# New page title

## Summary

One-paragraph TL;DR.

## Context

Why this page exists.

## Procedure / Decision / Definition

Body content.

## Cross-references

- ...
```

### How to add a new wiki page (3-step recipe)

1. Copy the template above to `homelab-playbook/wiki/<category>/<slug>.md`.
2. Fill in `title`, `slug`, `category`, `last_reviewed`, body sections.
3. Run `bash scripts/wiki-lint.sh` (once that script ships in a follow-up).
   Until then, manually verify: slug uniqueness, related_pages resolvable,
   related_frs / related_adrs present in PRD / adrs/.

## Cross-references

- ADR-006: wiki-as-file-tree decision and full schema rationale
  (`_bmad-output/planning-artifacts/products/context-stack/adrs/ADR-006-wiki-as-file-tree.md`)
- ADR-009: wiki-query skill design (read-side companion; consumes this schema)
- ADR-013: tier-of-truth division (why the wiki is distinct from Graphiti / auto-memory)
- FR-WIKI-002 / FR-WIKI-003 / FR-WIKI-004 / FR-WIKI-008: PRD requirements driving this schema

## Deferred from E4-S01 bootstrap

The story spec (`E4-S01-wiki-schema-and-bootstrap.md`) AC5/AC6/AC9 and DoD include:

- `scripts/wiki-lint.sh` — bash + yq link checker enforcing rules 1-6 above.
- Pre-commit hook wiring (`scripts/install-git-hooks.sh`).
- Five category subdirectories with `.gitkeep` (`architecture/`, `runbooks/`,
  `decisions/`, `glossary/`, `projects/`).

These were intentionally deferred from this commit per the kickoff scope decision
(markdown-only substrate). Until they ship:

- Lint rules 1-6 are enforced by operator discipline at commit time.
- Category subdirectories are documented in this schema and will materialise
  when the first seed page in each category lands (E4-S02 + later).

Track these as an explicit follow-up under E4-S01 OR a small carrier story
before E4-S02 starts (operator decision).
