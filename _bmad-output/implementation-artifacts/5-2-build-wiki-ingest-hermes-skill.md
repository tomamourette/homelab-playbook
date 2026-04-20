# Story 5.2: Build Wiki-Ingest Hermes Skill

Status: done

## Story

As a homelab operator,
I want a Hermes skill that ingests raw source documents into structured LLM Wiki pages with YAML frontmatter, cross-references, index updates, and operation logging,
So that Hermes can autonomously build and maintain the project knowledge base following the Karpathy LLM Wiki ingest operation defined in SCHEMA.md.

## Acceptance Criteria

1. **Given** the wiki structure from Story 5-1 exists at `~/workspace/homelab/wiki/`
   **When** I deploy the wiki-ingest skill
   **Then** `~/.hermes/skills/wiki-ingest/SKILL.md` exists with valid YAML frontmatter (name, description, version, author, metadata.hermes.tags)
   **And** the skill source file exists at `homelab-infra/ansible/roles/ai-dev-hermes/files/skills/wiki-ingest/SKILL.md`

2. **Given** a raw source document exists in `wiki/raw/` (e.g., a meeting note or design doc)
   **When** Hermes invokes the wiki-ingest skill with the source file path
   **Then** the skill extracts entities, concepts, decisions, and/or meeting notes from the source
   **And** creates or updates wiki pages in the correct subdirectory (`wiki/entities/`, `wiki/concepts/`, `wiki/decisions/`, `wiki/meetings/`) using kebab-case filenames

3. **Given** the wiki-ingest skill creates or updates a page
   **When** the page is written to disk
   **Then** the page has valid YAML frontmatter with all 8 required fields: title, confidence (0.0-1.0), last_ingested (ISO date), sources (list), content_hash (sha256 prefix, first 8 chars of source content hash), stale (false), provenance (extracted|inferred|ambiguous), tags (from `_meta/taxonomy.md`)

4. **Given** the wiki-ingest skill creates or updates pages
   **When** the ingest operation completes
   **Then** the skill runs a cross-linker pass that scans new/updated pages for entity and concept mentions and inserts Obsidian `[[wikilinks]]` where references are found
   **And** uses `[[wikilinks]]` (not standard Markdown links) for all internal wiki references

5. **Given** the wiki-ingest skill creates or updates pages
   **When** the ingest operation completes
   **Then** `wiki/_index.md` is updated with new page entries under the correct section (Entities, Concepts, Decisions, Meetings)
   **And** each entry includes a one-line summary and a wikilink to the page

6. **Given** the wiki-ingest skill completes an ingest operation
   **When** the operation log is updated
   **Then** `wiki/log.md` has a new row appended with: timestamp (ISO), operation type ("ingest"), pages affected (comma-separated list), source document, and notes
   **And** the log entry format matches the table format defined in log.md

7. **Given** the wiki-ingest skill processes a source document that overlaps with an existing wiki page
   **When** the page already exists in `wiki/`
   **Then** the skill updates the existing page (merging new information) rather than creating a duplicate
   **And** updates `content_hash` to reflect the new source content
   **And** sets `last_ingested` to the current date

8. **Given** the wiki-ingest Ansible deployment
   **When** the `ai-dev-hermes` role deploys skills
   **Then** `wiki-ingest/SKILL.md` is deployed from `homelab-infra/ansible/roles/ai-dev-hermes/files/skills/wiki-ingest/` to `~/.hermes/skills/wiki-ingest/` alongside existing skills (bmad-quick-dev, bmad-sprint-director)

## Tasks / Subtasks

- [x] Task 1: Create wiki-ingest SKILL.md with Hermes frontmatter and ingest workflow (AC: 1, 2)
  - [x] Create directory `homelab-infra/ansible/roles/ai-dev-hermes/files/skills/wiki-ingest/`
  - [x] Write `SKILL.md` with YAML frontmatter matching the pattern from existing Hermes skills (name, description, version, author, metadata.hermes.tags, related_skills)
  - [x] Define the ingest workflow: accept source file path, read SCHEMA.md for rules, read taxonomy.md for valid tags, extract structured content by page type, write pages to correct subdirectories
  - [x] Document input format (file path to raw source document), output format (wiki pages + index + log updates), and error handling

- [x] Task 2: Implement page creation with YAML frontmatter (AC: 3)
  - [x] Define frontmatter generation: compute `content_hash` as first 8 chars of sha256 of source content, set `confidence` based on provenance, set `last_ingested` to current ISO date, populate `sources` with the source file path, set `stale: false`, determine `provenance` (extracted for direct quotes, inferred for synthesized content, ambiguous for uncertain), select `tags` from taxonomy.md vocabulary
  - [x] Document the page type detection heuristic: how the skill decides if extracted content is an entity, concept, decision, or meeting summary
  - [x] Specify kebab-case filename generation from the page title

- [x] Task 3: Implement cross-linker pass (AC: 4)
  - [x] Define cross-linking algorithm: after writing pages, scan each new/updated page body for mentions of existing wiki page titles
  - [x] Insert `[[wikilinks]]` for recognized entity and concept references (matching against `_index.md` entries and filenames without extension)
  - [x] Ensure no duplicate wikilinks are inserted on re-ingest of the same content
  - [x] Use Obsidian `[[wikilinks]]` only — never standard Markdown `[text](url)` for internal references

- [x] Task 4: Implement _index.md and log.md updates (AC: 5, 6)
  - [x] Define _index.md update logic: read current index, find correct section header (Entities/Concepts/Decisions/Meetings), insert new entry with wikilink and one-line summary, maintain alphabetical order within sections
  - [x] Define log.md append logic: add row with `| ISO-timestamp | ingest | pages-affected | source-file | notes |`
  - [x] Handle idempotent index updates (don't add duplicate entries on re-ingest)

- [x] Task 5: Implement update-vs-create logic for existing pages (AC: 7)
  - [x] Define page existence check: look up page by title (kebab-case filename) in the target subdirectory
  - [x] If page exists: merge new information into existing content, update `content_hash`, `last_ingested`, and `sources` list (append new source), preserve existing `tags` and add new ones
  - [x] If page does not exist: create new page with full frontmatter and content

- [x] Task 6: Add Ansible deployment wiring (AC: 8)
  - [x] Verify the `ai-dev-hermes` role's skill deployment task copies from `files/skills/` to `~/.hermes/skills/`
  - [x] Ensure `wiki-ingest/` directory is included in the skill copy task (should work automatically if the role uses a directory copy pattern)
  - [x] Test that the skill appears alongside `bmad-quick-dev` and `bmad-sprint-director` after role execution

## Dev Notes

### Architecture Context

This story implements the **ingest** operation from the Karpathy LLM Wiki three-layer architecture. The ingest operation is the primary way knowledge enters the wiki — it transforms raw source documents (Layer 1: `raw/`) into structured wiki pages (Layer 2: `wiki/`) following the rules defined in SCHEMA.md (Layer 3).

**The skill is a Hermes SKILL.md file** — a markdown document that Hermes reads and follows as instructions. It is NOT executable code. Hermes uses its file tools (read, write, list) to interact with the wiki directory. The SKILL.md tells Hermes *what to do* and *how to do it* when the ingest operation is invoked.

**Three-layer architecture (from Story 5-1):**
- **Raw Sources** (`raw/`) — human-owned, immutable source documents
- **The Wiki** (`wiki/`) — LLM-generated pages: entities, concepts, decisions, cross-references
- **The Schema** (`SCHEMA.md`) — human-owned configuration telling the LLM how the wiki is structured

**Ingest operation flow (from SCHEMA.md):**
1. Read the source document(s) from `raw/`
2. Read SCHEMA.md for structure rules
3. Read `_meta/taxonomy.md` for valid tags
4. Extract entities, concepts, decisions, and meeting notes
5. For each extracted item: check if page exists (update if so, create if not), generate YAML frontmatter, write structured content, compute `content_hash`
6. Run cross-linker pass to insert `[[wikilinks]]`
7. Update `_index.md` with new/updated entries
8. Append operation to `log.md`

### Hermes Skill File Pattern

Follow the existing Hermes skill pattern from `homelab-infra/ansible/roles/ai-dev-hermes/files/skills/`. Reference skills:
- `bmad-quick-dev/SKILL.md` — stub skill with YAML frontmatter, overview, when-to-use, capabilities, requirements
- `bmad-sprint-director/SKILL.md` — stub skill with tags, related_skills

**Key difference:** wiki-ingest is a FULL skill, not a stub. It must contain the complete ingest workflow as instructions Hermes can follow, including all the rules from SCHEMA.md distilled into actionable steps.

**YAML frontmatter format:**
```yaml
---
name: wiki-ingest
description: Ingest raw source documents into structured LLM Wiki pages with YAML frontmatter, cross-references, and index updates.
version: 0.1.0
author: homelab
license: MIT
metadata:
  hermes:
    tags: [wiki, ingest, knowledge-management, llm-wiki]
    related_skills: [wiki-query, wiki-lint]
---
```

### YAML Frontmatter Spec (from SCHEMA.md)

Every wiki page MUST include:
```yaml
---
title: Page Title
confidence: 0.85
last_ingested: 2026-04-16
sources:
  - source-document.md
content_hash: abc123def
stale: false
provenance: extracted    # extracted | inferred | ambiguous
tags:
  - infrastructure
  - proxmox
---
```

- `content_hash`: First 8 chars of sha256 of the source content at ingest time
- `confidence`: 0.9+ for extracted (direct from source), 0.7-0.9 for inferred, 0.5-0.7 for ambiguous
- `provenance`: `extracted` (direct from source), `inferred` (LLM reasoning), `ambiguous` (uncertain)
- `tags`: MUST come from `_meta/taxonomy.md` controlled vocabulary

### Tag Domains (from taxonomy.md created in Story 5-1)

infrastructure, observability, security, networking, ai-dev, knowledge-management, automation, storage, proxmox, ansible, docker, homelab-ops

### Cross-Referencing Rules (from SCHEMA.md)

- Use Obsidian `[[wikilinks]]` for all internal references
- After each ingest, run cross-linker pass: scan new/updated pages for entity and concept mentions, insert `[[wikilinks]]` where references are found
- Do NOT use standard Markdown links for internal wiki references
- External links use standard Markdown link syntax

### Wiki Directory Structure (created in Story 5-1)

```
wiki/                            <- Obsidian vault root (standalone git repo)
├── raw/                         <- Layer 1: immutable source documents
├── wiki/
│   ├── entities/                <- Person, tool, service pages
│   ├── concepts/                <- Architectural patterns, methodologies
│   ├── decisions/               <- ADRs, retro learnings
│   └── meetings/                <- Meeting note summaries
├── outputs/                     <- Query results
├── .drafts/                     <- Staging area (not used by ingest)
├── _index.md                    <- Page catalogue (updated by ingest)
├── _meta/
│   └── taxonomy.md              <- Controlled tag vocabulary (read by ingest)
├── log.md                       <- Operation log (appended by ingest)
└── SCHEMA.md                    <- LLM instructions (read by ingest)
```

### File Naming Convention

- Kebab-case: `proxmox-clustering.md`, `traefik-routing.md`
- No spaces, no uppercase in filenames
- Directories use lowercase

### Deployment Path

- **Source:** `homelab-infra/ansible/roles/ai-dev-hermes/files/skills/wiki-ingest/SKILL.md`
- **Target:** `~/.hermes/skills/wiki-ingest/SKILL.md` (deployed by ai-dev-hermes role)
- **Existing skills at target:** `bmad-quick-dev/`, `bmad-sprint-director/`
- The ai-dev-hermes role uses a directory copy pattern from `files/skills/` to `~/.hermes/skills/`

### What This Story Does NOT Do

- Does NOT implement the query operation (Story 5.3)
- Does NOT implement the lint operation (Story 5.4)
- Does NOT configure Obsidian (Story 5.5)
- Does NOT set up git auto-push (Story 5.8)
- Does NOT implement article ingest from URLs (Story 5.7) — this story handles local `raw/` files only
- Does NOT interact with MemPalace (Epic 6) or OMEGA — wiki is file-based

### Previous Story Intelligence (Story 5-1)

Story 5-1 created the wiki directory structure and all scaffolding files:
- `wiki/SCHEMA.md` — defines all three operations including the ingest workflow
- `wiki/_index.md` — empty catalogue with section headers (Entities, Concepts, Decisions, Meetings)
- `wiki/log.md` — operation log with table format header and initial creation entry
- `wiki/_meta/taxonomy.md` — controlled tag vocabulary with 7 domains
- `wiki/.gitignore` — Obsidian exclusions
- `wiki/.obsidian/app.json` — minimal vault config
- Standalone git repo initialized (separate from homelab monorepo)

All 6 eval assertions passed on first run. No issues or corrections needed.

### Project Structure Notes

- Wiki lives at `~/workspace/homelab/wiki/` on ct-dev-homelab (192.168.50.150)
- Wiki is a standalone git repo, NOT a subdirectory of the homelab monorepo
- Hermes skills are in the homelab-infra repo under `ansible/roles/ai-dev-hermes/files/skills/`
- The ai-dev-hermes role deploys skills from the role's `files/skills/` to `~/.hermes/skills/`

### References

- [Source: wiki/SCHEMA.md] — Complete ingest operation definition, frontmatter spec, cross-referencing rules, naming conventions
- [Source: wiki/_meta/taxonomy.md] — Controlled tag vocabulary for the `tags` frontmatter field
- [Source: wiki/_index.md] — Current index structure with section headers
- [Source: wiki/log.md] — Operation log format
- [Source: planning-artifacts/research/technical-llm-knowledge-management-research-2026-04-11.md#Part 1] — LLM Wiki pattern: three operations, navigation files, token budget considerations
- [Source: planning-artifacts/research/technical-llm-knowledge-management-research-2026-04-11.md#Part 8] — Obsidian + LLM Wiki best practices, canonical directory structure, YAML frontmatter
- [Source: planning-artifacts/prd.md#FR53] — "Hermes can maintain a structured LLM Wiki per project"
- [Source: planning-artifacts/architecture.md#Stack] — "Knowledge Wiki: LLM Wiki (markdown), per-container Obsidian vault, git-synced, Hermes-maintained"
- [Source: planning-artifacts/epics.md] — Epic 5 story list in sprint-status.yaml
- [Source: homelab-infra/ansible/roles/ai-dev-hermes/files/skills/bmad-quick-dev/SKILL.md] — Reference Hermes skill file pattern
- [Source: implementation-artifacts/5-1-create-llm-wiki-structure-and-schema.md] — Previous story context and learnings

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

No debug issues encountered. Clean implementation.

### Completion Notes List

- Created full wiki-ingest SKILL.md (316 lines) with complete 7-step ingest workflow as Hermes-readable instructions
- YAML frontmatter validated: name, description, version, author, license, metadata.hermes.tags, metadata.hermes.related_skills
- All 8 required wiki page frontmatter fields documented with generation rules (title, confidence, last_ingested, sources, content_hash, stale, provenance, tags)
- Page type detection heuristic table covers entity, concept, decision, and meeting types with signal descriptions
- Content templates provided for all four page types following SCHEMA.md structure
- Cross-linker pass algorithm defined: builds reference list from filenames and _index.md, scans page bodies, inserts [[wikilinks]], prevents duplicates and self-references
- _index.md update logic: alphabetical ordering, correct section placement, idempotent (no duplicates on re-ingest)
- log.md append logic: ISO timestamp, operation type, pages affected, source, notes
- Update-vs-create logic: existing pages get merged content, updated content_hash/last_ingested/sources, preserved tags
- Ansible deployment: wiki-ingest/ directory auto-deployed by existing configure-skills.yml copy task; updated verify.yml to expect 3 skills (was 2)
- Kebab-case filename generation documented with examples including meeting date prefix convention

### File List

- homelab-infra/ansible/roles/ai-dev-hermes/files/skills/wiki-ingest/SKILL.md (NEW)
- homelab-infra/ansible/roles/ai-dev-hermes/tasks/verify.yml (MODIFIED - updated skill count from 2 to 3)
- homelab-playbook/_bmad-output/implementation-artifacts/sprint-status.yaml (MODIFIED - status updates)
- homelab-playbook/_bmad-output/implementation-artifacts/5-2-build-wiki-ingest-hermes-skill.md (MODIFIED - task completion, dev record)

### Review Findings

- [x] [Review][Patch] Empty source document edge case not handled in error section -- FIXED (approach: inline)
- [x] [Review][Patch] Meeting date fallback not documented for date-less meeting sources -- FIXED (approach: inline)
- [ ] [Review][Note] content_hash example inconsistency across repo files (SCHEMA.md shows 6 chars, story devnotes 9, SKILL.md instructions correct at 8) -- no action, informational
- [ ] [Review][Note] AC 1/8 reference ~/.hermes/skills/wiki-ingest/ but actual deploy path is ~/.hermes/skills/bmad/wiki-ingest/ (follows existing pattern) -- no action, informational

## Change Log

- 2026-04-16: Story created with comprehensive context for wiki-ingest Hermes skill implementation
- 2026-04-16: Implemented all 6 tasks -- created wiki-ingest SKILL.md with full ingest workflow, updated Ansible verify task
- 2026-04-16: Code review complete -- 2 patch findings fixed (inline), 2 notes logged, A/B comparison run (tie at 50, inline wins)
- 2026-04-16: Deployed to ct-dev-test (192.168.50.152) -- all 5 eval assertions PASS, idempotent second run confirmed, status moved to done
