# Story 5.7: Build Article-Ingest Skill

Status: done

## Story

As a homelab operator,
I want a Hermes skill that takes a URL, delegates to the BMAD technical-research skill for content extraction, and feeds the result into wiki-ingest,
So that I can grow my LLM Wiki from web articles without manually copying content into `raw/`.

## Acceptance Criteria

1. **Given** the article-ingest skill is deployed to `homelab-infra/ansible/roles/ai-dev-hermes/files/skills/article-ingest/SKILL.md`
   **When** I inspect the skill file
   **Then** the SKILL.md has YAML frontmatter with `name`, `description`, `version`, `author`, `license`, and `metadata.hermes.tags` fields matching the pattern used by wiki-ingest, wiki-query, and wiki-lint
   **And** `metadata.hermes.related_skills` includes `[wiki-ingest, wiki-query, wiki-lint]`

2. **Given** the article-ingest skill is invoked with a valid URL (e.g., a technical blog post or documentation page)
   **When** the skill executes its extraction step
   **Then** the skill delegates content extraction to the BMAD technical-research workflow (or an equivalent web-fetch + summarization step that Hermes can perform)
   **And** the extracted content is saved as a markdown file in `wiki/raw/` with a descriptive kebab-case filename derived from the article title or URL slug
   **And** the raw file includes a YAML frontmatter block with `source_url`, `fetched_date`, and `title` fields

3. **Given** a raw markdown file has been created from the extracted article content
   **When** the skill executes its ingest step
   **Then** the skill delegates to the wiki-ingest skill (or directly follows the wiki-ingest workflow steps) to transform the raw file into structured wiki pages
   **And** the resulting wiki pages conform to SCHEMA.md (correct frontmatter fields: title, confidence, last_ingested, sources, content_hash, stale, provenance, tags)
   **And** the `sources` field in generated wiki pages references the raw file deposited in step 2
   **And** `_index.md` is updated with new page entries
   **And** `log.md` has a new row recording the ingest operation

4. **Given** the article-ingest skill is invoked with an invalid or unreachable URL
   **When** the skill attempts extraction
   **Then** the skill reports a clear error message identifying the URL and the failure reason (e.g., 404, timeout, DNS failure)
   **And** no files are written to `wiki/raw/` or `wiki/`
   **And** a log entry is appended to `log.md` recording the failed attempt

5. **Given** the article-ingest skill is invoked with a URL whose content has already been ingested (duplicate detection)
   **When** the skill computes the content_hash of the fetched article
   **Then** if an existing raw file in `wiki/raw/` has the same content_hash, the skill reports "already ingested" and skips processing
   **And** if the content has changed (different hash, same source URL), the skill updates the existing raw file and re-runs ingest (update path)

6. **Given** all implementation is complete
   **When** I check for BMAD update-safety
   **Then** no files in `.claude/skills/bmad-*/` have been modified

## Edge Cases & Error Scenarios

1. **Side effects:** This story creates a single new file: `homelab-infra/ansible/roles/ai-dev-hermes/files/skills/article-ingest/SKILL.md`. No wiki content is created or modified -- the skill is a definition file only. The ai-dev-hermes Ansible role's existing skill deployment task will pick up the new directory on next playbook run. No services are restarted, no state is advanced.
2. **Dependency failure:** If Hermes's web-fetch tool cannot reach the target URL (network down, URL 404, DNS failure, paywall, bot-blocking), the skill must fail cleanly with a log entry and no partial files. If wiki-ingest delegation fails mid-way (e.g., SCHEMA.md missing, taxonomy.md missing, disk full), partial wiki pages may be written -- the skill should document this as a known limitation and recommend running wiki-lint after any failed ingest. If `wiki/raw/` does not exist, the skill should instruct Hermes to create it (it was established in Story 5-1).
3. **Assumptions:** The wiki directory structure exists at `~/workspace/homelab/wiki/` with `raw/`, `wiki/`, `_index.md`, `_meta/taxonomy.md`, `log.md`, and `SCHEMA.md` (all created by Story 5-1). Hermes has web-fetch capability (file tools + web access configured in Story 3-1/3-2). The wiki-ingest skill exists and is functional (Story 5-2). The git remote is configured and auto-push is active (Story 5-5). SCHEMA.md frontmatter contract is stable and will not change during this story's implementation.

## Eval Assertions

<!-- Binary test assertions derived from acceptance criteria. Used by /autoresearch:fix for post-code-review iteration loops. -->

| # | Assertion | Command/Check | Pass Criteria |
|---|-----------|---------------|---------------|
| AC-1 | Skill directory exists | `test -d homelab-infra/ansible/roles/ai-dev-hermes/files/skills/article-ingest/` | Exits with code 0 |
| AC-1b | SKILL.md has correct frontmatter | `head -10 homelab-infra/ansible/roles/ai-dev-hermes/files/skills/article-ingest/SKILL.md \| grep -q 'name: article-ingest'` | Exits with code 0 |
| AC-1c | Frontmatter has related_skills | `grep -q 'related_skills:.*wiki-ingest' homelab-infra/ansible/roles/ai-dev-hermes/files/skills/article-ingest/SKILL.md` | Exits with code 0 |
| AC-2 | Extraction workflow documented | `grep -q 'Fetch Article\|web-fetch\|fetch.*URL' homelab-infra/ansible/roles/ai-dev-hermes/files/skills/article-ingest/SKILL.md` | Exits with code 0 |
| AC-2b | Raw file deposit documented | `grep -q 'wiki/raw/' homelab-infra/ansible/roles/ai-dev-hermes/files/skills/article-ingest/SKILL.md` | Exits with code 0 |
| AC-2c | Raw frontmatter includes source_url | `grep -q 'source_url' homelab-infra/ansible/roles/ai-dev-hermes/files/skills/article-ingest/SKILL.md` | Exits with code 0 |
| AC-3 | Wiki-ingest delegation documented | `grep -q 'wiki-ingest' homelab-infra/ansible/roles/ai-dev-hermes/files/skills/article-ingest/SKILL.md` | Exits with code 0 |
| AC-3b | SCHEMA.md conformance referenced | `grep -q 'SCHEMA.md' homelab-infra/ansible/roles/ai-dev-hermes/files/skills/article-ingest/SKILL.md` | Exits with code 0 |
| AC-3c | Index and log updates documented | `grep -q '_index.md' homelab-infra/ansible/roles/ai-dev-hermes/files/skills/article-ingest/SKILL.md && grep -q 'log.md' homelab-infra/ansible/roles/ai-dev-hermes/files/skills/article-ingest/SKILL.md` | Exits with code 0 |
| AC-4 | Error handling for invalid URL documented | `grep -q '404\|timeout\|unreachable\|DNS' homelab-infra/ansible/roles/ai-dev-hermes/files/skills/article-ingest/SKILL.md` | Exits with code 0 |
| AC-5 | Duplicate detection documented | `grep -q 'content_hash\|duplicate\|already ingested' homelab-infra/ansible/roles/ai-dev-hermes/files/skills/article-ingest/SKILL.md` | Exits with code 0 |
| AC-6 | No BMAD files modified | `cd ~/workspace/homelab && git diff .claude/skills/bmad-*/` | Empty output (no changes) |
| AC-6b | SKILL.md under 500 lines | `wc -l < homelab-infra/ansible/roles/ai-dev-hermes/files/skills/article-ingest/SKILL.md` | Output is less than 500 |

## Tasks / Subtasks

- [x] Task 1: Create article-ingest SKILL.md with frontmatter and workflow (AC: 1, 2, 3, 4, 5)
  - [x] Create directory `homelab-infra/ansible/roles/ai-dev-hermes/files/skills/article-ingest/`
  - [x] Create `SKILL.md` with YAML frontmatter matching wiki-ingest pattern: `name: article-ingest`, `version: 0.1.0`, `author: homelab`, `license: MIT`, `metadata.hermes.tags: [wiki, ingest, article, knowledge-management, llm-wiki]`, `metadata.hermes.related_skills: [wiki-ingest, wiki-query, wiki-lint]`
  - [x] Write the Overview section explaining: URL input -> fetch -> extract -> deposit to raw/ -> delegate to wiki-ingest
  - [x] Write the "When to Use" section: user sends a URL (via CLI or Slack gateway in future), scheduled batch ingestion, operator pastes article link
  - [x] Write the Input section: a single URL string (required), optional `--title` override, optional `--tags` to pre-assign taxonomy tags
  - [x] Write the Output section: raw file in `wiki/raw/`, wiki pages in `wiki/entities/`, `wiki/concepts/`, `wiki/decisions/`, updated `_index.md`, log entry
  - [x] Write the Error Handling section covering: unreachable URL, empty content, missing SCHEMA.md, missing taxonomy.md, duplicate detection

- [x] Task 2: Implement the extraction workflow in SKILL.md (AC: 2)
  - [x] Define Step 1 (Read Configuration): read `wiki/SCHEMA.md`, `wiki/_meta/taxonomy.md`, `wiki/_index.md` (same as wiki-ingest Step 1)
  - [x] Define Step 2 (Fetch Article): use Hermes web-fetch tool (or equivalent) to retrieve the URL content; extract article title, body text, publication date if available; strip navigation, ads, boilerplate (focus on article body)
  - [x] Define Step 3 (Generate Raw File): compute content_hash (sha256, first 8 chars) of fetched content; check for duplicate in `wiki/raw/` by scanning existing files for matching `source_url` in frontmatter; generate kebab-case filename from article title (e.g., `proxmox-gpu-passthrough-guide.md`); write raw file with frontmatter (`source_url`, `fetched_date`, `title`, `content_hash`) and extracted markdown body

- [x] Task 3: Implement the ingest delegation in SKILL.md (AC: 3)
  - [x] Define Step 4 (Delegate to Wiki-Ingest): invoke the wiki-ingest skill with the newly created raw file path as input; if wiki-ingest is not available as a callable skill, inline the wiki-ingest workflow steps (Steps 3-7 from wiki-ingest SKILL.md: extract structured content, generate pages, cross-linker pass, update _index.md, append to log.md)
  - [x] Ensure the `sources` field in generated wiki pages references the raw filename (not the original URL -- the URL is in the raw file's frontmatter)

- [x] Task 4: Implement error handling and duplicate detection (AC: 4, 5)
  - [x] Define error handling for URL fetch failures: report error with URL and reason, append failure to `log.md`, exit cleanly
  - [x] Define duplicate detection logic: after fetching, compute content_hash; scan `wiki/raw/` for files with matching `source_url` in frontmatter; if same hash -> skip ("already ingested"); if different hash -> update raw file and re-ingest
  - [x] Define handling for empty or non-extractable content: log attempt, report to operator, do not create wiki pages

- [x] Task 5: Verify skill structure and BMAD update-safety (AC: 1, 6)
  - [x] Verify SKILL.md is under 500 lines (Claude Code skill convention from architecture)
  - [x] Verify frontmatter fields match the pattern from wiki-ingest/wiki-query/wiki-lint
  - [x] Verify no files in `.claude/skills/bmad-*/` have been modified
  - [x] Verify the skill file is self-contained (Hermes skills are single SKILL.md files, no subdirectories with templates/references)

## Dev Notes

### Architecture Context

This story implements **FR55** from the PRD: "Hermes can ingest web articles into LLM Wiki via BMAD technical-research skill, triggered by user sending a URL via Slack or CLI."

The architecture defines the query hierarchy concern as: "Wiki (fast, pre-synthesized) -> MemPalace (deep, raw verbatim) -> OMEGA (cross-project memory)." Article-ingest feeds the wiki layer, enriching the pre-synthesized knowledge base that Hermes queries first.

### Hermes Skill File Pattern

All Hermes skills follow the same structure established by wiki-ingest, wiki-query, and wiki-lint:

- **Location:** `homelab-infra/ansible/roles/ai-dev-hermes/files/skills/<skill-name>/SKILL.md`
- **Structure:** Single `SKILL.md` file per skill directory (no subdirectories, no templates, no references)
- **Frontmatter:** YAML block with `name`, `description`, `version` (0.1.0), `author` (homelab), `license` (MIT), `metadata.hermes.tags`, `metadata.hermes.related_skills`
- **Sections:** Overview, When to Use, Input, Output, Error Handling, Workflow Steps, Requirements, Notes

### BMAD Technical-Research Delegation

The BMAD technical-research skill (`/.claude/skills/bmad-technical-research/`) is a **Claude Code skill** (interactive, web-search-dependent, multi-step wizard). It is NOT a Hermes skill. Hermes cannot directly invoke Claude Code skills.

**Design decision:** The article-ingest Hermes skill should NOT depend on the BMAD technical-research skill. Instead, it should:
1. Use Hermes's own web-fetch capability (file tools + web access) to retrieve the URL content
2. Use Hermes's LLM capabilities to extract and summarize the article content into structured markdown
3. Deposit the result in `wiki/raw/` following the same format that manual deposits would use
4. Delegate to wiki-ingest for the actual page generation

This keeps the skill self-contained within Hermes's execution context. The BMAD technical-research skill remains available for deep, interactive research sessions initiated by the operator via Claude Code.

### Wiki SCHEMA.md Contract

All wiki pages must conform to `wiki/SCHEMA.md`. Key frontmatter fields:
- `title` (string), `confidence` (float 0.0-1.0), `last_ingested` (ISO date), `sources` (list of strings referencing raw files), `content_hash` (first 8 chars of sha256), `stale` (boolean), `provenance` (extracted | inferred | ambiguous), `tags` (from `_meta/taxonomy.md`)

Page types: Entity (`wiki/entities/`), Concept (`wiki/concepts/`), Decision (`wiki/decisions/`), Meeting (`wiki/meetings/`).

Raw file naming: kebab-case, lowercase, `.md` extension. Article raw files should use the article title slug (e.g., `proxmox-gpu-passthrough-guide.md`).

### Raw File Frontmatter for Articles

Raw files deposited by article-ingest should include additional frontmatter beyond what manual deposits have:

```yaml
---
title: Article Title Extracted from Page
source_url: https://example.com/article
fetched_date: 2026-04-16
content_hash: a1b2c3d4
---
```

This enables duplicate detection (by `source_url` + `content_hash`) and provenance tracking.

### Duplicate Detection Strategy

1. After fetching URL content, compute sha256 hash (first 8 chars)
2. Scan all files in `wiki/raw/` for YAML frontmatter containing `source_url` matching the input URL
3. If found with same `content_hash` -> skip ("Content unchanged, already ingested")
4. If found with different `content_hash` -> update the raw file content and re-run ingest (content changed)
5. If not found -> create new raw file and run ingest

### Previous Story Intelligence (5-6)

Story 5-6 (Set Up Laptop Meta-Vault with Dataview) is in `review` status. Key learnings:
- Adapted Dataview queries to match actual SCHEMA.md frontmatter fields (`confidence`, `stale`, `last_ingested`, `provenance`) -- the article-ingest skill must use these same fields, NOT `type`/`status`/`last_updated`
- Story 5-5 blocker (GitHub remote repo) was resolved -- wiki git push now works
- Dashboard files live in `wiki/wiki/dashboards/` and are synced via git

### What This Story Does NOT Do

- Does NOT modify the wiki-ingest SKILL.md -- article-ingest delegates to wiki-ingest as-is
- Does NOT implement Slack gateway URL ingestion (that is Epic 7, Story 7-7)
- Does NOT implement cron-scheduled batch ingestion (Story 5-8 wires cron)
- Does NOT create an Ansible role -- the skill file is deployed by the existing ai-dev-hermes role's skill deployment mechanism
- Does NOT modify any files in `.claude/skills/bmad-*/` (BMAD update-safety constraint)
- Does NOT interact with MemPalace (Epic 6) or OMEGA

### References

- [Source: planning-artifacts/prd.md#FR55] -- "Hermes can ingest web articles into LLM Wiki via BMAD technical-research skill, triggered by user sending a URL via Slack or CLI"
- [Source: planning-artifacts/architecture.md#Stack] -- "Knowledge Wiki: LLM Wiki (markdown), Per-container Obsidian vault, git-synced, Hermes-maintained"
- [Source: planning-artifacts/architecture.md#Cross-Cutting Concerns] -- "Query hierarchy: LLM Wiki -> MemPalace -> OMEGA"
- [Source: planning-artifacts/sprint-change-proposal-knowledge-mgmt-2026-04-11.md] -- Story 5.7 definition: "Build article-ingest skill (URL -> BMAD research -> wiki)"
- [Source: wiki/SCHEMA.md] -- Three-layer architecture, frontmatter spec, ingest operation definition
- [Source: homelab-infra/ansible/roles/ai-dev-hermes/files/skills/wiki-ingest/SKILL.md] -- Ingest workflow steps, page type detection, cross-linker pass, index update
- [Source: homelab-infra/ansible/roles/ai-dev-hermes/files/skills/wiki-query/SKILL.md] -- Skill frontmatter pattern reference
- [Source: homelab-infra/ansible/roles/ai-dev-hermes/files/skills/wiki-lint/SKILL.md] -- Skill frontmatter pattern reference
- [Source: implementation-artifacts/5-6-setup-laptop-meta-vault-with-dataview.md] -- Previous story: SCHEMA.md field corrections, git push resolution

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

N/A -- single-file skill definition, no runtime debugging required.

### Completion Notes List

- All 13 eval assertions pass (AC-1 through AC-6b)
- SKILL.md is 250 lines (well under 500 limit)
- Frontmatter matches wiki-ingest/wiki-query/wiki-lint pattern exactly
- No BMAD files modified (git diff .claude/skills/bmad-*/ is empty)
- Skill is self-contained: single SKILL.md file, no subdirectories

### Change Log

- 2026-04-16: Created article-ingest SKILL.md with full workflow (Tasks 1-5)

### File List

- `homelab-infra/ansible/roles/ai-dev-hermes/files/skills/article-ingest/SKILL.md` (created)
