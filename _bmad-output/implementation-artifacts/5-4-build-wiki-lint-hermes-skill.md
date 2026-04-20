# Story 5.4: Build Wiki-Lint Hermes Skill

Status: done

## Story

As a homelab operator,
I want a Hermes skill that validates wiki health by detecting contradictions, orphaned pages, stale claims, and missing cross-references,
So that the LLM Wiki stays structurally sound and factually consistent as pages accumulate, following the lint operation defined in SCHEMA.md.

## Acceptance Criteria

1. **Given** the wiki structure from Story 5-1 exists at `~/workspace/homelab/wiki/`
   **When** I deploy the wiki-lint skill
   **Then** `~/.hermes/skills/bmad/wiki-lint/SKILL.md` exists with valid YAML frontmatter (name, description, version, author, license, metadata.hermes.tags, metadata.hermes.related_skills)
   **And** the skill source file exists at `homelab-infra/ansible/roles/ai-dev-hermes/files/skills/wiki-lint/SKILL.md`

2. **Given** a wiki with pages that have valid YAML frontmatter
   **When** Hermes invokes the wiki-lint skill
   **Then** the skill checks every page in `wiki/entities/`, `wiki/concepts/`, `wiki/decisions/`, and `wiki/meetings/` for:
   - Valid YAML frontmatter with all 8 required fields (title, confidence, last_ingested, sources, content_hash, stale, provenance, tags)
   - Tags that exist in `_meta/taxonomy.md`
   - Non-broken `[[wikilinks]]` (target page exists in the wiki)
   - `stale` flag accuracy (compare `content_hash` against current source in `raw/`)

3. **Given** the wiki-lint skill has completed its checks
   **When** it detects issues
   **Then** it produces a structured lint report listing each issue with: page name, issue type (missing-frontmatter, invalid-tag, broken-wikilink, stale-page, orphaned-page, missing-from-index), severity (error/warning), and a human-readable description

4. **Given** the wiki-lint skill detects auto-fixable issues
   **When** the operator has not passed a `--dry-run` flag (or equivalent)
   **Then** the skill auto-fixes:
   - Missing frontmatter fields by adding defaults (confidence: 0.5, stale: true, provenance: ambiguous)
   - Stale pages by setting `stale: true` when `content_hash` does not match current source
   - Unlisted pages by adding them to `_index.md` in the correct section and alphabetical order
   **And** broken wikilinks are flagged for review but NOT auto-removed

5. **Given** the wiki-lint skill completes a lint operation
   **When** the operation log is updated
   **Then** `wiki/log.md` has a new row appended with: timestamp (ISO), operation type ("lint"), pages checked count, issues found count, auto-fixes applied count, and notes

6. **Given** the wiki has zero pages (empty `_index.md`, no files in `wiki/` subdirectories)
   **When** Hermes invokes the wiki-lint skill
   **Then** the skill returns a clear message: "No wiki pages to lint. Run wiki-ingest first to populate the wiki."
   **And** no log entry is appended

7. **Given** the wiki-lint skill detects contradictions between pages
   **When** two or more pages make conflicting claims about the same entity or concept
   **Then** the lint report includes a "contradiction" issue type listing the conflicting pages, the conflicting claims, and which page has higher confidence or more recent `last_ingested` date

8. **Given** the wiki-lint Ansible deployment
   **When** the `ai-dev-hermes` role deploys skills
   **Then** `wiki-lint/SKILL.md` is deployed from `homelab-infra/ansible/roles/ai-dev-hermes/files/skills/wiki-lint/` to `~/.hermes/skills/bmad/wiki-lint/` alongside existing skills (bmad-quick-dev, bmad-sprint-director, wiki-ingest, wiki-query)
   **And** `verify.yml` expects 5 skills (updated from 4)

## Edge Cases & Error Scenarios

1. **Side effects:** This story creates one new file (`wiki-lint/SKILL.md` in the Ansible role's `files/skills/` directory) and modifies one existing file (`verify.yml` skill count 4 -> 5). At runtime, the lint skill may modify wiki page frontmatter (auto-fix mode) and append to `_index.md` and `log.md`. Sprint-status.yaml is updated to `ready-for-dev`.
2. **Dependency failure:** If `SCHEMA.md`, `_meta/taxonomy.md`, or `_index.md` is missing, the skill must halt with a clear error (not silently skip checks). If a source file referenced in `sources` frontmatter does not exist in `raw/`, the stale check should flag a warning (source may have been removed) rather than erroring. If Hermes file tools fail mid-lint (e.g., permission error writing a fix), the skill should report the failure for that page and continue with remaining pages.
3. **Assumptions:** Wiki directory structure exists at `~/workspace/homelab/wiki/` (created by Story 5-1). The `ai-dev-hermes` role's `configure-skills.yml` uses a directory copy from `files/skills/` (validated in Stories 5-2 and 5-3). `content_hash` is always 8 hex characters of SHA-256. The operator has run at least one ingest before lint is useful (empty-wiki guard handles this). Tags in `_meta/taxonomy.md` are the single source of truth -- if a page has a tag not in taxonomy, it is flagged even if the tag "looks valid."

## Eval Assertions

<!-- Binary test assertions derived from acceptance criteria. Used by /autoresearch:fix for post-code-review iteration loops. -->

| # | Assertion | Command/Check | Pass Criteria |
|---|-----------|---------------|---------------|
| AC-1 | SKILL.md exists with valid frontmatter | `test -f homelab-infra/ansible/roles/ai-dev-hermes/files/skills/wiki-lint/SKILL.md && head -10 homelab-infra/ansible/roles/ai-dev-hermes/files/skills/wiki-lint/SKILL.md \| grep -q "name: wiki-lint"` | Exits with code 0 |
| AC-2 | Lint workflow covers all 4 check categories | `grep -c "frontmatter\|taxonomy\|wikilink\|stale\|content_hash" homelab-infra/ansible/roles/ai-dev-hermes/files/skills/wiki-lint/SKILL.md` | Count >= 5 (each category mentioned at least once) |
| AC-3 | Lint report format documented in SKILL.md | `grep -q "issue type\|severity\|error.*warning" homelab-infra/ansible/roles/ai-dev-hermes/files/skills/wiki-lint/SKILL.md` | Exits with code 0 |
| AC-4 | Auto-fix logic and dry-run documented | `grep -q "dry-run\|auto-fix\|Missing frontmatter.*defaults" homelab-infra/ansible/roles/ai-dev-hermes/files/skills/wiki-lint/SKILL.md` | Exits with code 0 |
| AC-5 | Log.md append format documented | `grep -q "log.md\|lint.*pages checked\|issues found" homelab-infra/ansible/roles/ai-dev-hermes/files/skills/wiki-lint/SKILL.md` | Exits with code 0 |
| AC-6 | Empty-wiki guard documented | `grep -q "No wiki pages to lint" homelab-infra/ansible/roles/ai-dev-hermes/files/skills/wiki-lint/SKILL.md` | Exits with code 0 |
| AC-7 | Contradiction detection documented | `grep -q "contradiction" homelab-infra/ansible/roles/ai-dev-hermes/files/skills/wiki-lint/SKILL.md` | Exits with code 0 |
| AC-8 | verify.yml updated to expect 5 skills | `grep -q "< 5" homelab-infra/ansible/roles/ai-dev-hermes/tasks/verify.yml` | Exits with code 0 |

## Tasks / Subtasks

- [x] Task 0: Verify previous story's skill invocation (AC: prerequisite)
  - [x] Invoke the wiki-query skill created in Story 5-3 with a trivial question (e.g., "What tools are documented in the wiki?") and confirm it produces expected output (synthesized answer or "No wiki pages available" message). If it fails, halt and raise a blocker.

- [x] Task 1: Create wiki-lint SKILL.md with Hermes frontmatter and lint workflow (AC: 1, 2, 3)
  - [x] Create directory `homelab-infra/ansible/roles/ai-dev-hermes/files/skills/wiki-lint/`
  - [x] Write `SKILL.md` with YAML frontmatter matching the sibling skill pattern (name: wiki-lint, description, version: 0.1.0, author: homelab, license: MIT, metadata.hermes.tags: [wiki, lint, knowledge-management, llm-wiki], related_skills: [wiki-ingest, wiki-query])
  - [x] Define the lint workflow Step 1: Read configuration (SCHEMA.md, _meta/taxonomy.md, _index.md)
  - [x] Define Step 2: Empty-wiki guard (same pattern as wiki-query)
  - [x] Define Step 3: Enumerate all wiki pages across all 4 subdirectories
  - [x] Define Step 4: Validate each page (frontmatter completeness, tag validity, wikilink integrity, stale flag accuracy)
  - [x] Define Step 5: Check _index.md completeness (every wiki page listed)
  - [x] Define Step 6: Detect orphaned pages (pages not referenced by any other page via wikilinks)

- [x] Task 2: Implement contradiction detection logic (AC: 7)
  - [x] Define contradiction detection: for pages about the same entity/concept (matching by title or overlapping tags), compare key claims and facts
  - [x] Document how to identify contradictions: conflicting facts in the same section type (e.g., two entity pages claiming different versions for the same tool)
  - [x] Include confidence and recency comparison to suggest which page is more authoritative

- [x] Task 3: Implement auto-fix logic and dry-run mode (AC: 4)
  - [x] Define auto-fixable issue types: missing frontmatter fields (add defaults), stale flag (set to true), unlisted pages (add to _index.md)
  - [x] Define non-auto-fixable issue types: broken wikilinks (flag only), contradictions (flag only), orphaned pages (flag only)
  - [x] Document dry-run mode: when invoked with `--dry-run`, report all issues but apply zero fixes
  - [x] Define default values for missing frontmatter: confidence: 0.5, stale: true, provenance: ambiguous, tags: [], sources: [], content_hash: "00000000", last_ingested: current date

- [x] Task 4: Implement lint report format and log.md append (AC: 3, 5)
  - [x] Define structured lint report format: grouped by issue type, each issue with page name, type, severity, description
  - [x] Define severity levels: error (missing required frontmatter, broken wikilinks) vs warning (stale pages, orphaned pages, missing from index)
  - [x] Define log.md append: `| ISO-timestamp | lint | N pages checked | M issues found, K auto-fixed | notes |`

- [x] Task 5: Add Ansible deployment wiring (AC: 8)
  - [x] Verify the `ai-dev-hermes` role's skill deployment task copies wiki-lint from `files/skills/` to `~/.hermes/skills/bmad/`
  - [x] Update `verify.yml` skill count threshold from `< 4` to `< 5` and update task name to include wiki-lint

## Dev Notes

### Architecture Context

This story implements the **lint** operation from the Karpathy LLM Wiki three-layer architecture (SCHEMA.md, Section "LLM Wiki Operations", Operation 3). The lint operation validates wiki health and fixes structural issues. It is the quality gate that keeps the wiki clean as pages accumulate from ingest operations.

**The skill is a Hermes SKILL.md file** -- a markdown document that Hermes reads and follows as instructions. It is NOT executable code. Hermes uses its file tools (read, write, list) to interact with the wiki directory. The SKILL.md tells Hermes *what to do* and *how to do it* when the lint operation is invoked.

**Lint operation flow (from SCHEMA.md):**
1. Check every page in `wiki/` for: valid YAML frontmatter, valid tags, non-broken wikilinks, stale flag accuracy
2. Check `_index.md` completeness
3. Report issues and optionally auto-fix

### Hermes Skill File Pattern

Follow the existing Hermes skill pattern from sibling skills. Reference skills:
- `homelab-infra/ansible/roles/ai-dev-hermes/files/skills/wiki-ingest/SKILL.md` -- 316 lines, full 7-step workflow
- `homelab-infra/ansible/roles/ai-dev-hermes/files/skills/wiki-query/SKILL.md` -- 228 lines, full 7-step workflow

**YAML frontmatter format:**
```yaml
---
name: wiki-lint
description: Validate wiki health — detect contradictions, orphaned pages, stale claims, broken wikilinks, and missing cross-references.
version: 0.1.0
author: homelab
license: MIT
metadata:
  hermes:
    tags: [wiki, lint, knowledge-management, llm-wiki]
    related_skills: [wiki-ingest, wiki-query]
---
```

**Key difference from sibling skills:** wiki-lint reads AND writes to `wiki/` pages (auto-fix mode). It may modify frontmatter fields and `_index.md`. In dry-run mode, it only reads.

### Lint Check Categories

Based on SCHEMA.md Section "3. Lint", the skill must check:

| Check | Source of Truth | Auto-fixable? | Severity |
|-------|----------------|---------------|----------|
| Frontmatter has all 8 required fields | SCHEMA.md "YAML Frontmatter" | Yes (add defaults) | Error |
| Tags exist in taxonomy.md | `_meta/taxonomy.md` | No (flag) | Error |
| Wikilinks point to existing pages | `wiki/` subdirectories | No (flag) | Error |
| `stale` flag matches source hash | `raw/` directory, `content_hash` field | Yes (set stale: true) | Warning |
| Every page listed in `_index.md` | `_index.md` vs directory listing | Yes (add entry) | Warning |
| Orphaned pages (no inbound wikilinks) | Cross-page wikilink scan | No (flag) | Warning |
| Contradictions between pages | Cross-page fact comparison | No (flag) | Warning |

### YAML Frontmatter Required Fields (from SCHEMA.md)

All 8 fields that must be present on every wiki page:
- `title` (string)
- `confidence` (float 0.0-1.0)
- `last_ingested` (ISO date)
- `sources` (list of strings)
- `content_hash` (string, sha256 prefix, 8 chars)
- `stale` (boolean)
- `provenance` (enum: extracted | inferred | ambiguous)
- `tags` (list of strings)

### Stale Detection Algorithm

1. For each wiki page, read `sources` from frontmatter
2. For each source file, check if it exists in `raw/`
3. If source exists: compute sha256 of source content, take first 8 chars, compare against `content_hash`
4. If hashes differ: the page is stale (source changed since last ingest)
5. If source does not exist in `raw/`: flag as warning (source may have been removed or renamed)

### Contradiction Detection Approach

Since there is no vector DB, contradiction detection relies on Hermes's LLM reasoning:
1. Group pages by overlapping topics (matching tags or similar titles)
2. For pages in the same group, compare key facts in corresponding sections
3. Flag when the same entity/concept has conflicting attributes across pages
4. Include both pages' `confidence` and `last_ingested` to help the operator decide which is correct

This is the most LLM-intensive check -- it requires reading and comparing multiple pages. Limit comparison to pages that share at least one tag or reference the same entity via wikilinks.

### Wiki Directory Structure (created in Story 5-1)

```
wiki/                            <- Obsidian vault root (standalone git repo)
├── raw/                         <- Layer 1: immutable source documents
├── wiki/
│   ├── entities/                <- Person, tool, service pages
│   ├── concepts/                <- Architectural patterns, methodologies
│   ├── decisions/               <- ADRs, retro learnings
│   └── meetings/                <- Meeting note summaries
├── outputs/                     <- Query results (not checked by lint)
├── .drafts/                     <- Staging area (not checked by lint)
├── _index.md                    <- Page catalogue (checked for completeness)
├── _meta/
│   └── taxonomy.md              <- Controlled tag vocabulary (source of truth for tags)
├── log.md                       <- Operation log (appended by lint)
└── SCHEMA.md                    <- LLM instructions (read by lint)
```

### Deployment Path

- **Source:** `homelab-infra/ansible/roles/ai-dev-hermes/files/skills/wiki-lint/SKILL.md`
- **Target:** `~/.hermes/skills/bmad/wiki-lint/SKILL.md` (deployed by ai-dev-hermes role)
- **Existing skills at target:** `bmad-quick-dev/`, `bmad-sprint-director/`, `wiki-ingest/`, `wiki-query/`
- The ai-dev-hermes role uses a directory copy pattern from `files/skills/` to `~/.hermes/skills/bmad/`
- `verify.yml` currently checks for `< 4` skills; must update to `< 5`

### What This Story Does NOT Do

- Does NOT implement the ingest operation (Story 5.2 -- done)
- Does NOT implement the query operation (Story 5.3 -- done)
- Does NOT configure Obsidian (Story 5.5)
- Does NOT set up git auto-push or cron scheduling for lint (Story 5.8)
- Does NOT implement article ingest from URLs (Story 5.7)
- Does NOT interact with MemPalace (Epic 6) or OMEGA -- wiki is file-based

### Previous Story Intelligence (Story 5-3)

Story 5-3 created the wiki-query SKILL.md (228 lines) with:
- Full 7-step query workflow as Hermes-readable instructions
- YAML frontmatter validated: name, description, version, author, license, metadata.hermes.tags, metadata.hermes.related_skills
- Empty-wiki guard returning exact message and skipping output/log
- Provenance-aware synthesis with [[wikilink]] citations
- Optional output persistence to `outputs/`
- Log.md append with truncation for large page lists

**Key patterns established by 5-2 and 5-3:**
- SKILL.md structure: frontmatter, Overview, When to Use, Input, Output, Error Handling, multi-step workflow, Requirements, Notes
- Error handling section covers every failure mode explicitly
- Empty-wiki guard is a reusable pattern (check _index.md entries + directory listing)
- Deploy path is `~/.hermes/skills/bmad/` (not directly under `~/.hermes/skills/`)
- `configure-skills.yml` uses `src: "skills/"` directory copy -- new skill directories are picked up automatically
- `verify.yml` skill count must be incremented (was 3 -> 4 for query, now 4 -> 5 for lint)

**Review findings from 5-2 (still relevant):**
- content_hash is 8 chars of sha256 (first 8 hex digits) -- be consistent
- Deploy path follows `bmad/` subdirectory pattern

### Ansible Verify Update

`verify.yml` currently checks for `< 4` skills (line ~132). After adding wiki-lint, update to `< 5` and update task name to include wiki-lint.

### Tag Domains (from taxonomy.md created in Story 5-1)

Available tags for validation: infrastructure, proxmox, storage, homelab-ops, observability, prometheus, grafana, logging, security, vault, certificates, networking, dns, traefik, tailscale, ai-dev, hermes, claude, omega, ollama, llm, knowledge-management, wiki, obsidian, mempalace, ingestion, automation, ansible, terraform, docker

### Project Structure Notes

- SKILL.md lives in `homelab-infra/ansible/roles/ai-dev-hermes/files/skills/wiki-lint/SKILL.md`
- Wiki data lives in `~/workspace/homelab/wiki/` (separate standalone git repo)
- No files in `.claude/skills/bmad-*/` are modified (BMAD update-safety constraint)

### References

- [Source: wiki/SCHEMA.md#Lint] -- Complete lint operation definition (3 steps, 4 check categories)
- [Source: wiki/SCHEMA.md#YAML Frontmatter] -- All 8 required fields with types and descriptions
- [Source: wiki/SCHEMA.md#Cross-Referencing Rules] -- Wikilink format rules
- [Source: wiki/_meta/taxonomy.md] -- Controlled tag vocabulary for tag validation
- [Source: planning-artifacts/sprint-change-proposal-knowledge-mgmt-2026-04-11.md] -- Epic 5 story 5.4 definition, FR56
- [Source: planning-artifacts/prd.md#FR56] -- "Hermes can perform periodic wiki lint"
- [Source: planning-artifacts/architecture.md#Stack] -- "Knowledge Wiki: LLM Wiki (markdown), per-container Obsidian vault, git-synced, Hermes-maintained"
- [Source: implementation-artifacts/5-3-build-wiki-query-hermes-skill.md] -- Previous story context, deploy patterns, verify.yml updates
- [Source: homelab-infra/ansible/roles/ai-dev-hermes/files/skills/wiki-ingest/SKILL.md] -- Reference Hermes skill file (316 lines, full workflow)
- [Source: homelab-infra/ansible/roles/ai-dev-hermes/files/skills/wiki-query/SKILL.md] -- Reference Hermes skill file (228 lines, full workflow)
- [Source: homelab-infra/ansible/roles/ai-dev-hermes/tasks/verify.yml] -- Current verify task with skill count check (< 4)

## Dev Agent Record

### Agent Model Used

claude-opus-4-6

### Debug Log References

None -- clean implementation, all 8 eval assertions passed on first attempt.

### Completion Notes List

- Task 0: Verified wiki-query SKILL.md from Story 5-3 exists with valid frontmatter, 7 workflow steps, and empty-wiki guard.
- Task 1: Created wiki-lint/SKILL.md (357 lines) with full 7-step lint workflow following sibling skill patterns. YAML frontmatter matches spec exactly.
- Task 2: Contradiction detection implemented in Step 6b -- groups pages by overlapping tags/wikilinks, compares key facts, includes confidence/recency comparison for authority ranking.
- Task 3: Auto-fix logic in Steps 4a (missing frontmatter defaults), 4d (stale flag), and 5 (unlisted pages in _index.md). Dry-run mode documented throughout. Non-fixable issues (broken wikilinks, invalid tags, orphaned pages, contradictions) are flagged only.
- Task 4: Structured lint report format in Step 7a with tables grouped by issue type and severity (error vs warning). Log.md append format in Step 7b.
- Task 5: Updated verify.yml skill count from < 4 to < 5 and task name to include wiki-lint. Deployment wiring confirmed -- configure-skills.yml uses directory copy from files/skills/ so wiki-lint is picked up automatically.

### File List

- homelab-infra/ansible/roles/ai-dev-hermes/files/skills/wiki-lint/SKILL.md (new)
- homelab-infra/ansible/roles/ai-dev-hermes/tasks/verify.yml (modified -- skill count 4 -> 5, task name updated)
- homelab-playbook/_bmad-output/implementation-artifacts/sprint-status.yaml (modified -- story status)
- homelab-playbook/_bmad-output/implementation-artifacts/5-4-build-wiki-lint-hermes-skill.md (modified -- task checkboxes, dev record)
