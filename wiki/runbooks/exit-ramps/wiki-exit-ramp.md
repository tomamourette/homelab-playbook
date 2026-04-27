---
title: "Wiki tier — exit ramp"
slug: wiki-exit-ramp
category: runbooks
last_reviewed: 2026-04-27
owner: tomamourette
related_pages:
  - _schema
  - index
  - query-hierarchy
  - wiki-query-skill
related_frs:
  - FR-WIKI-002
  - FR-WIKI-008
  - NFR-PORT-001
related_adrs:
  - ADR-006
  - ADR-009
  - ADR-013
status: stable
supersedes: []
superseded_by: null
---

# Wiki tier — exit ramp

## Summary

The wiki is plain markdown + YAML frontmatter in a git repo. The exit ramp
is `git clone homelab-playbook` — you already have the data. This page
documents the schema downstream consumers must respect, the lint contract
that guarantees it, and how to wire the wiki into a search engine, static
site generator, or successor knowledge base without losing fidelity.

## Context

ADR-006 chose markdown-in-git as the wiki substrate specifically because
it has the trivial exit ramp: there is no proprietary binary, no embedding
store, no MCP server, no daemon. Migration cost is approximately zero as
long as the consumer respects the YAML frontmatter contract.

The non-trivial work is in the **schema contract**: any successor tool
must parse the same frontmatter the lint script enforces, or cross-link
integrity breaks (slugs unresolved, ADR/FR references dangling). This
runbook surfaces what the contract is and how to verify migration.

## Procedure

### 1. Capture the data

```bash
# Already done if you have the repo cloned
git clone <homelab-playbook-remote> /path/to/destination
cd /path/to/destination/wiki
ls
# expect: _schema.md  index.md  architecture/  decisions/  glossary/
#         projects/   runbooks/
```

The `wiki/` directory tree is portable as-is. Copy it anywhere — another
repo, an S3 bucket, a flat tarball — and the data survives intact.

### 2. Honour the schema contract

Every page must conform to [Wiki page schema](_schema). The required
frontmatter keys (per `_schema.md` §Frontmatter):

```yaml
title:           # required, string
slug:            # required, kebab-case, unique across tree, matches filename
category:        # required, one of: architecture | runbooks | decisions
                 #                   | glossary | projects | meta
last_reviewed:   # required, ISO YYYY-MM-DD
owner:           # required, single string
related_pages:   # required list (may be empty), slugs
related_frs:     # required list (may be empty), FR-IDs
related_adrs:    # required list (may be empty), ADR-IDs
status:          # required, one of: draft | stable | superseded
supersedes:      # required list (may be empty)
superseded_by:   # required, slug or null
```

Cross-reference syntax inside markdown bodies uses **slug-based** links
(`[text](slug)`), not relative paths — slugs survive file renames.

### 3. Run the lint to verify integrity

```bash
bash homelab-playbook/scripts/wiki-lint.sh
# expect: wiki-lint: pages=N failed=0 warnings=0
```

The lint enforces (rules per `_schema.md` §Lint rules):

1. YAML frontmatter parses cleanly.
2. Slug matches filename (without `.md`).
3. Slug is unique across the tree.
4. Category in allow-list.
5. `last_reviewed` is ISO YYYY-MM-DD.
6. `status` in `{draft, stable, superseded}`.

Soft warning (exit 0): `last_reviewed` older than 6 months.

A clean lint is the migration smoke test — if a successor tool ingests
the tree and reports unresolvable slugs or missing required keys, the
ingest failed; do not promote the migration until lint is clean on both
sides.

### 4. Ingest into a downstream consumer (3 patterns)

**Pattern A — Static site generator (Hugo, MkDocs, Docusaurus).** All
three accept markdown + YAML frontmatter natively. Map the wiki tree
into the SSG's content directory; configure the SSG to honour the
`category` field as section, `slug` as URL path. Frontmatter keys not
recognised by the SSG are passed through untouched (Hugo: `Params.X`;
MkDocs: ignored; Docusaurus: ignored). No data loss.

**Pattern B — Search engine (ripgrep, ugrep, simple Lucene index).**
Treat each `.md` file as a document. The frontmatter `tags`, `category`,
and `related_*` fields are the natural facet filters. ripgrep is
already the operator's day-zero search engine — no migration needed for
the read path.

**Pattern C — Successor knowledge base (Notion, Obsidian, BookStack).**
Each tool has a markdown import path. The frontmatter generally needs
to be flattened into native metadata fields; the slug→file mapping
must be preserved or all internal links break. Validate by spot-checking
five pages with cross-references after import; if any link 404s, the
import lost slug integrity and should be redone.

### 5. Recovery from corruption

Wiki corruption is a `git` problem, not a wiki problem:

```bash
# History is in git; recover any prior version
cd homelab-playbook
git log -- wiki/architecture/<slug>.md
git checkout <SHA> -- wiki/architecture/<slug>.md
```

If the entire `wiki/` tree is lost on the working copy, `git checkout`
restores it. If the git remote is also lost, restore from the operator's
existing repo backup pattern (zfs send / GitHub mirror / etc.).

## Cross-references

- [Wiki page schema](_schema) — the frontmatter contract.
- [Query hierarchy](query-hierarchy) — when to consult Tier 1 (wiki) vs
  other tiers.
- [wiki-query skill](wiki-query-skill) — the Tier 1 retrieval mechanism.
- ADR-006 — wiki-as-file-tree decision (full rationale for the trivial
  exit ramp).
- ADR-009 — wiki-query skill design.
