---
type: story
epic: E4
id: E4-S01
title: "Define wiki page schema + bootstrap index.md and _schema.md"
size: 1d
priority: MUST
fr_refs: [FR-WIKI-002, FR-WIKI-003, FR-WIKI-004, FR-WIKI-008, FR-DEP-005]
adr_refs: [ADR-006, ADR-013]
status: draft
date: 2026-04-25
---

# E4-S01: Define wiki page schema + bootstrap index.md and _schema.md

## User Story

As **tomamourette** (homelab operator), I want **the Tier-1 wiki tree bootstrapped at `homelab-playbook/wiki/` with a normative frontmatter schema (`_schema.md`), an entry-point index (`index.md`), the five canonical category subdirectories, and a working `scripts/wiki-lint.sh` link checker**, so that **all subsequent wiki seeds (E4-S02), the `wiki-query` skill (E4-S03), and the unified query-hierarchy doc (E4-S10) have a stable, machine-parseable substrate to land on per ADR-006**.

## Background and Context

Per ADR-006 (director-resolved Q3), the wiki is a file-based markdown tree under `homelab-playbook/wiki/`, version-controlled via the existing git workflow (FR-WIKI-008), with zero MCP / DB / LLM at retrieval time (FR-WIKI-003). The schema (frontmatter + body sections + slug-based cross-references) is normative — every wiki page MUST conform. ADR-013 establishes the tier-of-truth division (wiki = current state, Graphiti = trail, auto-memory = pointers, GitNexus = code structure); the wiki schema must surface enough metadata (`related_pages`, `related_frs`, `related_adrs`, `last_reviewed`, `supersedes`/`superseded_by`) to keep that division enforceable. This story is the **substrate** — it ships no content seeds (those are E4-S02), it ships the **mechanism**.

`index.md` is what Claude Code reads at session start (FR-WIKI-004) and what the `wiki-query` skill reads first (ADR-009); it must be small (< 5 KB target), human-grep-able, and auto-rebuildable by `wiki-lint.sh`.

## Acceptance Criteria

### AC1: Wiki tree skeleton exists at `homelab-playbook/wiki/` with five category subdirectories

- **Given** the homelab-playbook repo on the `phase-3-wiki-tier` branch
- **When** I run `tree -L 2 homelab-playbook/wiki/`
- **Then** output shows directories `architecture/`, `runbooks/`, `decisions/`, `glossary/`, `projects/` AND files `index.md` + `_schema.md` at the root

### AC2: `_schema.md` documents the ADR-006 frontmatter spec verbatim

- **Given** `homelab-playbook/wiki/_schema.md` exists
- **When** I read it
- **Then** it contains: (a) the YAML frontmatter block from ADR-006 §Decision (all required keys: `title`, `slug`, `category`, `last_reviewed`, `owner`, `related_pages`, `related_frs`, `related_adrs`, `status`, `supersedes`, `superseded_by`); (b) the H2 section convention (`## Summary`, `## Context`, `## Procedure / Decision / Definition`, `## Cross-references`); (c) the slug-based cross-reference syntax (`[text](slug)`, `[text](git:path)`, standard URL); (d) a copy-pasteable "new-page template" block

### AC3: `index.md` exists with the three required sections

- **Given** `homelab-playbook/wiki/index.md` exists
- **When** I read it
- **Then** it contains: (a) one-paragraph "what's in this wiki" summary (≤ 80 words), (b) bulleted index by category with each bullet linking to a slug + one-line description (placeholder: only `_schema` listed at this point — content comes in E4-S02), (c) a "Recently updated" stub auto-populated by `wiki-lint.sh`

### AC4: `index.md` total size is < 5 KB at this bootstrap stage

- **Given** AC3 passes
- **When** I run `wc -c homelab-playbook/wiki/index.md`
- **Then** the byte count is < 5120 (< 5 KB) — confirms ADR-009 size projection holds at bootstrap

### AC5: `scripts/wiki-lint.sh` is committed and exits 0 on the bootstrap tree

- **Given** the script exists at `homelab-playbook/scripts/wiki-lint.sh` with mode 755
- **When** I run `bash homelab-playbook/scripts/wiki-lint.sh`
- **Then** exit code is 0 AND stdout reports: `pages: 1 (_schema.md only); slugs unique: yes; broken related_pages: 0; broken related_frs: 0; broken related_adrs: 0; stale (>6mo): 0`

### AC6: `wiki-lint.sh` enforces all six ADR-006 rules

- **Given** AC5 passes
- **When** I introduce a synthetic violation (one at a time): (a) duplicate slug; (b) `related_pages: [does-not-exist]`; (c) `related_frs: [FR-FAKE-999]`; (d) `related_adrs: [ADR-999]`; (e) `last_reviewed: 2024-01-01` (>6 months stale); (f) malformed YAML frontmatter
- **Then** for each: cases (a)–(d) and (f) cause exit code 1 with a descriptive message; case (e) emits a `WARN:` line but exit code stays 0 (per ADR-006: stale is warn-level, not fail)

### AC7: `_schema.md` itself passes wiki-lint

- **Given** AC2 and AC5
- **When** wiki-lint runs
- **Then** `_schema.md` (which is itself a wiki page about the schema) carries valid frontmatter (title="Wiki page schema", slug="_schema", category="glossary" or "architecture", last_reviewed=today, related_adrs=[ADR-006]) and lints clean

### AC8: `homelab-playbook/.gitignore` does NOT exclude any wiki path

- **Given** the wiki tree is intended to ride the existing git workflow (FR-WIKI-008)
- **When** I run `git check-ignore homelab-playbook/wiki/index.md homelab-playbook/wiki/_schema.md`
- **Then** both files are NOT ignored (no output) — they will be committed

### AC9: Pre-commit hook wires `wiki-lint.sh` for the homelab-playbook repo

- **Given** the existing repo conventions
- **When** I commit a change touching `homelab-playbook/wiki/**`
- **Then** the pre-commit hook (or equivalent `git config core.hooksPath`-managed hook) runs `wiki-lint.sh` and blocks the commit on exit code 1; this is captured in `homelab-playbook/scripts/install-git-hooks.sh` (or via existing pattern) and documented in the story DoD

## Implementation Notes

### Directory layout (per ADR-006 §Decision)

```
homelab-playbook/wiki/
├── index.md              # Entry point (FR-WIKI-004)
├── _schema.md            # Schema spec (this story)
├── architecture/         # Cross-product architectural decisions
├── runbooks/             # Step-by-step procedures
├── decisions/            # Distilled prior decisions (Graphiti-overlap is OK)
├── glossary/             # Term definitions
└── projects/             # Per-project pointers (cross-link only)
```

Create empty `.gitkeep` in each subdirectory so the structure ships even before E4-S02 lands content.

### `wiki-lint.sh` reference implementation skeleton

```bash
#!/usr/bin/env bash
# homelab-playbook/scripts/wiki-lint.sh
# Enforces ADR-006 wiki schema rules.
set -euo pipefail
WIKI_DIR="$(git rev-parse --show-toplevel)/homelab-playbook/wiki"
[ -d "$WIKI_DIR" ] || { echo "FAIL: wiki dir missing"; exit 1; }

ERRS=0; WARNS=0
SLUGS=()
PAGES=$(find "$WIKI_DIR" -type f -name '*.md' | sort)

for f in $PAGES; do
  # Extract frontmatter; parse with yq (apt: yq, or pip: yq)
  FM=$(awk '/^---$/{c++; next} c==1' "$f" | head -n -0 | sed -n '/^---$/q;p')
  TITLE=$(echo "$FM" | yq '.title // ""' -)
  SLUG=$(echo "$FM" | yq '.slug // ""' -)
  CAT=$(echo "$FM" | yq '.category // ""' -)
  LR=$(echo "$FM" | yq '.last_reviewed // ""' -)
  # validations: title nonblank, slug nonblank+unique, category in allowlist,
  # last_reviewed parseable; related_pages slugs resolvable; related_frs in PRD;
  # related_adrs in adrs/. Stale >6mo emits WARN (not ERR).
  ...
done

# Optional regen: if --regen passed, rebuild index.md "Recently updated" section.
echo "pages: ${#PAGES[@]}; slugs unique: $(...); broken: $ERRS; stale: $WARNS"
[ "$ERRS" -eq 0 ]
```

Concrete language choice: bash + `yq` (Go binary, already widely deployable) — not python-frontmatter, to keep the workstation install footprint minimal. If `yq` is not installed, the script emits an actionable error pointing to `apt install yq` or the binary release page.

### `_schema.md` content (sketch)

Header frontmatter (this page IS itself a wiki page):
```yaml
---
title: "Wiki page schema"
slug: _schema
category: glossary
last_reviewed: 2026-04-25
owner: tomamourette
related_pages: []
related_frs: [FR-WIKI-002, FR-WIKI-003]
related_adrs: [ADR-006, ADR-013]
status: stable
supersedes: []
superseded_by: null
---
```

Body must be the verbatim ADR-006 §Decision schema block plus a "How to add a new wiki page" runbook subsection (3-step recipe: copy template → fill frontmatter → run wiki-lint).

### `index.md` content (bootstrap; E4-S02 fills it)

```markdown
---
title: "Homelab wiki — index"
slug: index
category: glossary
last_reviewed: 2026-04-25
owner: tomamourette
related_pages: []
related_frs: [FR-WIKI-004]
related_adrs: [ADR-006, ADR-009]
status: stable
supersedes: []
superseded_by: null
---

# Homelab wiki

Curated, file-based, zero-MCP knowledge base. The single source of truth for
*current state* (architectural decisions, runbooks, conventions). Distinct from
Graphiti (which holds dated decisions and supersession trails) and auto-memory
(which holds one-line pointers). See ADR-013 for the tier-of-truth division.

## By category

- **architecture/** — _(seeds added in E4-S02)_
- **runbooks/** — _(seeds added in E4-S02)_
- **decisions/** — _(seeds added in E4-S02)_
- **glossary/** — [Wiki page schema](_schema)
- **projects/** — _(seeds added in E4-S02)_

## Recently updated

_(Auto-populated by `scripts/wiki-lint.sh --regen`)_
```

### Git hook integration

Use the existing `homelab-playbook/scripts/install-git-hooks.sh` pattern (or create one matching the repo's existing pre-push hook for `mempalace|omega` reference creep, per E1-S09). Keep the hook fast (< 2 s on a typical wiki commit) — the slow paths in wiki-lint are the FR-existence and ADR-existence checks; cache them per-run.

## Test Plan

**Pre-flight (parallel; one Bash block):**
```bash
git rev-parse --show-toplevel                                    # confirm we're in homelab repo
ls -la homelab-playbook/wiki/ 2>&1 || echo "wiki dir absent (expected pre-story)"
which yq                                                          # confirm yq available
```

**Author the bootstrap (Edit/Write):**
1. Create five category subdirectories with `.gitkeep`.
2. Write `homelab-playbook/wiki/_schema.md` per Implementation Notes.
3. Write `homelab-playbook/wiki/index.md` per Implementation Notes.
4. Write `homelab-playbook/scripts/wiki-lint.sh` per skeleton; `chmod +x`.
5. Update `homelab-playbook/scripts/install-git-hooks.sh` (or equivalent) to register the pre-commit hook.

**AC verification:**
```bash
# AC1
tree -L 2 homelab-playbook/wiki/
# AC4
wc -c homelab-playbook/wiki/index.md     # expect < 5120
# AC5
bash homelab-playbook/scripts/wiki-lint.sh && echo PASS
# AC6 (synthetic violation drill — for each, create a tmp page in wiki/architecture/, run lint, expect failure mode, restore)
echo '---
title: dup
slug: _schema
category: architecture
last_reviewed: 2026-04-25
owner: tomamourette
related_pages: []
related_frs: []
related_adrs: []
status: draft
supersedes: []
superseded_by: null
---' > homelab-playbook/wiki/architecture/dup.md
bash homelab-playbook/scripts/wiki-lint.sh; echo "exit=$? (expect 1)"
rm homelab-playbook/wiki/architecture/dup.md
# Repeat for the other 5 violation cases.

# AC7
bash homelab-playbook/scripts/wiki-lint.sh
# AC8
git check-ignore homelab-playbook/wiki/index.md homelab-playbook/wiki/_schema.md
# AC9
git add homelab-playbook/wiki/_schema.md && git commit -m "test: lint hook"
# Expect either commit success (clean) or block (introduce a violation first to verify).
```

**Rollback:**
```bash
git checkout HEAD~1 -- homelab-playbook/wiki/ homelab-playbook/scripts/wiki-lint.sh
```

## Dependencies

- **Blocks:** E4-S02 (seed entries need schema), E4-S03 (skill needs index.md), E4-S10 (query-hierarchy doc is a wiki page)
- **Blocked by:** none (E4 first story; can start as soon as E1 is merged so the repo doesn't carry mempalace cruft)

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| `yq` not installed on workstation; lint fails opaquely | Lint script emits actionable error pointing to `apt install yq`; document in `_schema.md` as a prerequisite |
| Schema rules drift between `_schema.md` and `wiki-lint.sh` | Both regenerable from ADR-006 source; AC6 synthetic-violation drill catches drift at story-test time and pre-commit time |
| `index.md` exceeds 5 KB once E4-S02 seeds land | Explicit AC4 budget at bootstrap; ADR-009 §Negative covers "if it grows past 20 KB switch to preload" — that's the reversal trigger, not a Sprint 4 worry |
| Pre-commit hook slows commits noticeably | AC9 plus a non-AC budget: `time wiki-lint.sh` ≤ 2s on the bootstrap tree; revisit if E4-S02 makes it slower |

## Definition of Done

- [ ] All ACs pass (AC1–AC9)
- [ ] PR commit messages: `wiki: bootstrap tree, schema, lint script` (one commit, since these are coupled)
- [ ] `homelab-playbook/wiki/{index.md,_schema.md}` and the five category dirs are committed
- [ ] `homelab-playbook/scripts/wiki-lint.sh` is committed and executable
- [ ] Pre-commit hook is registered for the repo
- [ ] No regression in `MEMORY.md` auto-memory loading
- [ ] `git log --oneline | head -3` shows the bootstrap commit immediately after the E1 `phase-1-decommission-complete` tag
- [ ] Cross-reference task added: `AT-FR-WIKI-002a`, `AT-FR-WIKI-004a` (Phase 5a will populate)
