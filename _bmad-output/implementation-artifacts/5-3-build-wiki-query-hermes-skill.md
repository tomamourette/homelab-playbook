# Story 5.3: Build Wiki-Query Hermes Skill

Status: done

## Story

As a homelab operator,
I want a Hermes skill that searches wiki pages by keyword and semantic match and synthesizes answers with citations,
So that Hermes can answer natural language questions using the project knowledge base following the Karpathy LLM Wiki query operation defined in SCHEMA.md.

## Acceptance Criteria

1. **Given** the wiki structure from Story 5-1 exists at `~/workspace/homelab/wiki/`
   **When** I deploy the wiki-query skill
   **Then** `~/.hermes/skills/wiki-query/SKILL.md` exists with valid YAML frontmatter (name, description, version, author, metadata.hermes.tags)
   **And** the skill source file exists at `homelab-infra/ansible/roles/ai-dev-hermes/files/skills/wiki-query/SKILL.md`

2. **Given** a natural language question (e.g., "How is Traefik configured for HTTPS?")
   **When** Hermes invokes the wiki-query skill with the question
   **Then** the skill reads `_index.md` to identify candidate pages relevant to the query
   **And** reads the candidate wiki pages from `wiki/entities/`, `wiki/concepts/`, `wiki/decisions/`, and/or `wiki/meetings/`

3. **Given** the wiki-query skill has identified relevant pages
   **When** the skill synthesizes an answer
   **Then** the answer includes Obsidian `[[wikilinks]]` citing the source wiki pages (not standard Markdown links)
   **And** the answer distinguishes between high-confidence facts (from `extracted` provenance pages) and lower-confidence inferences (from `inferred` or `ambiguous` provenance pages)

4. **Given** the wiki-query skill synthesizes an answer
   **When** the answer is returned to the caller
   **Then** the skill optionally writes the answer to `wiki/outputs/` as a timestamped markdown file (e.g., `outputs/2026-04-16-traefik-https-query.md`) when the caller requests persistence
   **And** the output file uses kebab-case filename with ISO date prefix

5. **Given** the wiki-query skill completes a query operation
   **When** the operation log is updated
   **Then** `wiki/log.md` has a new row appended with: timestamp (ISO), operation type ("query"), pages consulted (comma-separated list), question asked, and notes
   **And** the log entry format matches the table format defined in log.md

6. **Given** the wiki has zero pages (empty `_index.md`, no files in `wiki/` subdirectories)
   **When** Hermes invokes the wiki-query skill with any question
   **Then** the skill returns a clear message: "No wiki pages available. Run wiki-ingest first to populate the wiki."
   **And** no output file is created and no log entry is appended

7. **Given** the wiki-query Ansible deployment
   **When** the `ai-dev-hermes` role deploys skills
   **Then** `wiki-query/SKILL.md` is deployed from `homelab-infra/ansible/roles/ai-dev-hermes/files/skills/wiki-query/` to `~/.hermes/skills/wiki-query/` alongside existing skills (bmad-quick-dev, bmad-sprint-director, wiki-ingest)

## Tasks / Subtasks

- [x] Task 1: Create wiki-query SKILL.md with Hermes frontmatter and query workflow (AC: 1, 2, 3)
  - [x] Create directory `homelab-infra/ansible/roles/ai-dev-hermes/files/skills/wiki-query/`
  - [x] Write `SKILL.md` with YAML frontmatter matching the wiki-ingest pattern (name: wiki-query, description, version: 0.1.0, author: homelab, metadata.hermes.tags: [wiki, query, knowledge-management, llm-wiki], related_skills: [wiki-ingest, wiki-lint])
  - [x] Define the query workflow: accept natural language question, read _index.md for page discovery, read relevant pages, synthesize answer with [[wikilink]] citations
  - [x] Document page relevance scoring: match question keywords against page titles, tags, and frontmatter fields; read pages with highest relevance first
  - [x] Document provenance-aware synthesis: flag facts from `inferred` or `ambiguous` provenance pages with lower confidence

- [x] Task 2: Implement answer synthesis with citation format (AC: 3, 4)
  - [x] Define answer format: structured response with inline `[[wikilinks]]` to source pages
  - [x] Define confidence annotation: when citing a page with `provenance: inferred` or `confidence < 0.7`, prefix the claim with a qualifier (e.g., "Based on inferred context from [[page]]...")
  - [x] Define optional output persistence: when caller requests, write answer to `wiki/outputs/` with kebab-case ISO-date-prefixed filename
  - [x] Document output file format: markdown with the question as H1, answer body, and a "Sources" section listing all consulted pages

- [x] Task 3: Implement log.md append for query operations (AC: 5)
  - [x] Define log.md append logic: add row with `| ISO-timestamp | query | pages-consulted | question | notes |`
  - [x] Handle the case where many pages are consulted: truncate the pages list if it exceeds a reasonable length (e.g., list first 5 pages then "... and N more")

- [x] Task 4: Implement empty-wiki guard (AC: 6)
  - [x] Define empty-wiki detection: read `_index.md` and check if any page entries exist (non-comment, non-header lines with `[[wikilinks]]`); also check if `wiki/` subdirectories contain any `.md` files
  - [x] If wiki is empty: return the "no pages available" message, skip output file creation, skip log.md append

- [x] Task 5: Add Ansible deployment wiring (AC: 7)
  - [x] Verify the `ai-dev-hermes` role's skill deployment task copies from `files/skills/` to `~/.hermes/skills/`
  - [x] Ensure `wiki-query/` directory is included in the skill copy task (should work automatically if the role uses a directory copy pattern)
  - [x] Update `verify.yml` to expect 4 skills (currently expects 3: bmad-quick-dev, bmad-sprint-director, wiki-ingest)

## Dev Notes

### Architecture Context

This story implements the **query** operation from the Karpathy LLM Wiki three-layer architecture. The query operation is how knowledge exits the wiki -- it answers natural language questions by searching structured wiki pages (Layer 2: `wiki/`) and synthesizing answers with citations.

**The skill is a Hermes SKILL.md file** -- a markdown document that Hermes reads and follows as instructions. It is NOT executable code. Hermes uses its file tools (read, write, list) to interact with the wiki directory. The SKILL.md tells Hermes *what to do* and *how to do it* when the query operation is invoked.

**Query operation flow (from SCHEMA.md):**
1. Read `_index.md` to identify relevant pages
2. Read relevant wiki pages
3. Synthesize an answer with citations (`[[wikilinks]]`)
4. Optionally write the answer to `outputs/`

### Hermes Skill File Pattern

Follow the existing Hermes skill pattern from `homelab-infra/ansible/roles/ai-dev-hermes/files/skills/`. Reference skill:
- `wiki-ingest/SKILL.md` -- full skill with YAML frontmatter, overview, when-to-use, input/output, error handling, multi-step workflow

**Key difference from wiki-ingest:** wiki-query reads the wiki (does not write to `wiki/` pages). It only writes to `outputs/` (optional) and appends to `log.md`.

**YAML frontmatter format:**
```yaml
---
name: wiki-query
description: Search wiki pages by keyword and semantic match, synthesize answers with citations.
version: 0.1.0
author: homelab
license: MIT
metadata:
  hermes:
    tags: [wiki, query, knowledge-management, llm-wiki]
    related_skills: [wiki-ingest, wiki-lint]
---
```

### Page Relevance Strategy

Since this is a file-based wiki (no vector DB, no embeddings), the query skill relies on Hermes's own LLM reasoning to determine relevance:

1. **Index scan:** Read `_index.md` and match question keywords against page names and one-line summaries
2. **Tag matching:** Cross-reference question topic against page `tags` in frontmatter (tags from `_meta/taxonomy.md`)
3. **Page reading:** Read the top N most relevant pages (recommend 3-5 to stay within token budget)
4. **Synthesis:** Compose an answer drawing from all consulted pages, citing each with `[[wikilinks]]`

There is NO embedding search or vector similarity -- Hermes uses its LLM understanding of the question to decide which pages to read. This is intentional per the Karpathy pattern: the wiki is small enough for the LLM to navigate by reading the index.

### YAML Frontmatter Fields Used by Query

The query skill reads (but does not write) these frontmatter fields from wiki pages:
- `title`: displayed in citations
- `confidence`: used to weight facts in synthesis (higher confidence = more authoritative)
- `provenance`: `extracted` facts are stated directly; `inferred`/`ambiguous` facts get a qualifier
- `stale`: if `true`, the skill should note that the source may be outdated
- `tags`: used for topic matching during page relevance scoring

### Cross-Referencing Rules (from SCHEMA.md)

- Use Obsidian `[[wikilinks]]` for all citations in the answer
- Do NOT use standard Markdown links for wiki page references
- External links (URLs outside the wiki) use standard Markdown link syntax

### Wiki Directory Structure (created in Story 5-1)

```
wiki/                            <- Obsidian vault root (standalone git repo)
├── raw/                         <- Layer 1: immutable source documents
├── wiki/
│   ├── entities/                <- Person, tool, service pages
│   ├── concepts/                <- Architectural patterns, methodologies
│   ├── decisions/               <- ADRs, retro learnings
│   └── meetings/                <- Meeting note summaries
├── outputs/                     <- Query results (written by wiki-query)
├── .drafts/                     <- Staging area (not used by query)
├── _index.md                    <- Page catalogue (read by query)
├── _meta/
│   └── taxonomy.md              <- Controlled tag vocabulary (read by query)
├── log.md                       <- Operation log (appended by query)
└── SCHEMA.md                    <- LLM instructions (read by query)
```

### File Naming Convention

- Output files: kebab-case with ISO date prefix: `2026-04-16-traefik-https-query.md`
- No spaces, no uppercase in filenames
- Derive the slug from the question (first few meaningful words)

### Deployment Path

- **Source:** `homelab-infra/ansible/roles/ai-dev-hermes/files/skills/wiki-query/SKILL.md`
- **Target:** `~/.hermes/skills/wiki-query/SKILL.md` (deployed by ai-dev-hermes role)
- **Existing skills at target:** `bmad-quick-dev/`, `bmad-sprint-director/`, `wiki-ingest/`
- The ai-dev-hermes role uses a directory copy pattern from `files/skills/` to `~/.hermes/skills/`
- **Note from Story 5-2 review:** actual deploy path is `~/.hermes/skills/bmad/wiki-query/` (follows existing pattern under `bmad/` subdirectory)

### What This Story Does NOT Do

- Does NOT implement the ingest operation (Story 5.2 -- done)
- Does NOT implement the lint operation (Story 5.4)
- Does NOT configure Obsidian (Story 5.5)
- Does NOT set up git auto-push (Story 5.8)
- Does NOT implement query hierarchy (Epic 6, Story 6.5) -- this is wiki-only search, no MemPalace or OMEGA fallback
- Does NOT implement article ingest from URLs (Story 5.7)
- Does NOT interact with MemPalace (Epic 6) or OMEGA -- wiki is file-based

### Previous Story Intelligence (Story 5-2)

Story 5-2 created the wiki-ingest SKILL.md (316 lines) with:
- Full 7-step ingest workflow as Hermes-readable instructions
- YAML frontmatter validated: name, description, version, author, license, metadata.hermes.tags, metadata.hermes.related_skills
- All 8 required wiki page frontmatter fields documented with generation rules
- Page type detection heuristic covering entity, concept, decision, meeting types
- Cross-linker pass algorithm
- _index.md and log.md update logic
- Update-vs-create logic for existing pages

**Review findings from 5-2:**
- Empty source document edge case was not initially handled -- fixed inline
- Meeting date fallback was not documented for date-less meeting sources -- fixed inline
- content_hash example inconsistency across repo files (SCHEMA.md shows 6 chars, story devnotes 9, SKILL.md correct at 8) -- informational, no action
- AC 1/8 reference `~/.hermes/skills/wiki-ingest/` but actual deploy path is `~/.hermes/skills/bmad/wiki-ingest/` (follows existing pattern) -- informational

**Key takeaway for 5-3:** Follow the same SKILL.md structure and level of detail as wiki-ingest. Ensure error handling covers all edge cases (empty wiki, missing SCHEMA.md, missing _index.md). Use the `bmad/` subdirectory deploy path.

### Ansible Verify Update

`verify.yml` currently checks for `3` skills (line 132: `verify_skill_stubs.matched < 3`). After adding wiki-query, update to `< 4`.

### Tag Domains (from taxonomy.md created in Story 5-1)

Available tags for topic matching: infrastructure, proxmox, storage, homelab-ops, observability, prometheus, grafana, logging, security, vault, certificates, networking, dns, traefik, tailscale, ai-dev, hermes, claude, omega, ollama, llm, knowledge-management, wiki, obsidian, mempalace, ingestion, automation, ansible, terraform, docker

### References

- [Source: wiki/SCHEMA.md#Query] -- Complete query operation definition (4 steps)
- [Source: wiki/_index.md] -- Current index structure with section headers
- [Source: wiki/_meta/taxonomy.md] -- Controlled tag vocabulary for topic matching
- [Source: wiki/log.md] -- Operation log format
- [Source: planning-artifacts/research/technical-llm-knowledge-management-research-2026-04-11.md#Part 1] -- LLM Wiki pattern: three operations, navigation files
- [Source: planning-artifacts/sprint-change-proposal-knowledge-mgmt-2026-04-11.md] -- Epic 5 story breakdown, FR53 coverage
- [Source: planning-artifacts/prd.md#FR53] -- "Hermes can maintain a structured LLM Wiki per project"
- [Source: planning-artifacts/architecture.md#Stack] -- "Knowledge Wiki: LLM Wiki (markdown), per-container Obsidian vault, git-synced, Hermes-maintained"
- [Source: implementation-artifacts/5-2-build-wiki-ingest-hermes-skill.md] -- Previous story context, review findings, deployment patterns
- [Source: homelab-infra/ansible/roles/ai-dev-hermes/files/skills/wiki-ingest/SKILL.md] -- Reference Hermes skill file (full skill pattern)
- [Source: homelab-infra/ansible/roles/ai-dev-hermes/tasks/verify.yml] -- Current verify task with skill count check

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

None -- clean implementation, no issues encountered.

### Completion Notes List

- Created wiki-query SKILL.md (228 lines) following the wiki-ingest pattern: YAML frontmatter, overview, when-to-use, input/output, error handling, 7-step query workflow
- SKILL.md covers all 7 ACs: valid frontmatter (AC1), index-based page discovery and page reading (AC2), provenance-aware synthesis with [[wikilink]] citations (AC3), optional output persistence to outputs/ (AC4), log.md append with truncation for large page lists (AC5), empty-wiki guard returning exact message and skipping output/log (AC6), Ansible deployment via existing directory copy pattern (AC7)
- Verified configure-skills.yml uses `src: "skills/"` directory copy -- wiki-query/ is picked up automatically, no task changes needed
- Updated verify.yml skill count threshold from `< 3` to `< 4` and updated task name to include wiki-query
- YAML frontmatter validated: name, description, version, author, license, metadata.hermes.tags, metadata.hermes.related_skills all correct
- Sprint status updated: ready-for-dev -> in-progress -> review

### Change Log

- 2026-04-16: Created wiki-query SKILL.md, updated verify.yml skill count to 4, story status set to review

### File List

- homelab-infra/ansible/roles/ai-dev-hermes/files/skills/wiki-query/SKILL.md (new)
- homelab-infra/ansible/roles/ai-dev-hermes/tasks/verify.yml (modified -- skill count 3->4, task name updated)
- homelab-playbook/_bmad-output/implementation-artifacts/sprint-status.yaml (modified -- 5-3 status)
- homelab-playbook/_bmad-output/implementation-artifacts/5-3-build-wiki-query-hermes-skill.md (modified -- task checkboxes, status, dev agent record)
