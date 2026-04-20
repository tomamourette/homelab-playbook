# Story 5.1: Create LLM Wiki Directory Structure and SCHEMA.md

Status: done

## Story

As a homelab operator,
I want a structured LLM Wiki directory layout with a SCHEMA.md convention, index page, and operation log per project,
So that Hermes and Claude Code have a consistent, compounding knowledge base to write to and query from.

## Acceptance Criteria

1. **Given** the homelab project on ct-dev-homelab (192.168.50.150)
   **When** I create the LLM Wiki directory structure
   **Then** a `wiki/` directory exists at `~/workspace/homelab/wiki/` with subdirectories: `raw/`, `wiki/entities/`, `wiki/concepts/`, `wiki/decisions/`, `wiki/meetings/`, `outputs/`, `.drafts/`, and `_meta/`

2. **Given** the wiki directory structure exists
   **When** I create the SCHEMA.md file
   **Then** `wiki/SCHEMA.md` defines: naming conventions (kebab-case filenames), page types (entity, concept, decision, meeting summary), required YAML frontmatter fields (title, confidence, last_ingested, sources, content_hash, stale, provenance, tags), cross-referencing rules (Obsidian `[[wikilinks]]`), and the three LLM Wiki operations (ingest, query, lint)

3. **Given** the SCHEMA.md defines navigation files
   **When** I create the index and log files
   **Then** `wiki/_index.md` exists as an empty catalogue with section headers for entities, concepts, decisions, and meetings
   **And** `wiki/log.md` exists as an empty append-only operation log with a header documenting the log format (timestamp, operation type, pages affected)

4. **Given** the wiki directory needs tag governance
   **When** I create the taxonomy file
   **Then** `wiki/_meta/taxonomy.md` exists with a controlled tag vocabulary organized by domain (infrastructure, observability, security, networking, ai-dev, knowledge-management) and instructions for adding new tags

5. **Given** the wiki will be synced via git
   **When** I initialize the wiki as a git repository
   **Then** `wiki/.gitignore` excludes `.obsidian/workspace.json`, `.obsidian/workspace-mobile.json`, and `.obsidian/plugins/*/data.json`
   **And** the wiki directory is initialized as a standalone git repository (not a subdirectory of the homelab repo)
   **And** an initial commit captures the directory structure, SCHEMA.md, _index.md, log.md, taxonomy.md, and .gitignore

6. **Given** the wiki is a standalone git repo
   **When** I configure the Obsidian vault basics
   **Then** `wiki/.obsidian/` directory exists with a minimal `app.json` config (no workspace state files committed)
   **And** the vault is recognizable by Obsidian when opened on the laptop

## Edge Cases & Error Scenarios

1. **Side effects:**
   - New directory tree created at `~/workspace/homelab/wiki/` (10+ directories, 6+ files)
   - A new standalone git repository initialized (separate from homelab repo)
   - `.obsidian/` directory created with vault config -- adds Obsidian recognition
   - Initial git commit created capturing all scaffolding files

2. **Dependency failure:**
   - If `~/workspace/homelab/` does not exist: `mkdir -p` will create it, but this would be unusual -- halt and verify container state
   - If git is not installed: story cannot complete Task 5 -- dev-host role guarantees git, so this indicates a broken baseline
   - If the `wiki/` directory already exists (e.g., from a previous failed attempt): check for existing content before overwriting -- prefer idempotent creation (mkdir -p, don't clobber existing files)

3. **Assumptions:**
   - ct-dev-homelab is accessible and the developer user has write access to `~/workspace/homelab/`
   - git is available (installed by dev-host role)
   - No existing `wiki/` directory at the target path (first-time creation)
   - The wiki repo will get a remote origin configured in a later story (5.5 or 5.8) -- this story only does `git init` with no remote
   - SCHEMA.md content is stable enough that Stories 5.2-5.4 can build on it without breaking changes

## Eval Assertions

<!-- Binary test assertions derived from acceptance criteria. Used by /autoresearch:fix for post-code-review iteration loops. -->

| # | Assertion | Command/Check | Pass Criteria |
|---|-----------|---------------|---------------|
| AC-1 | Wiki directory structure exists | `test -d ~/workspace/homelab/wiki/raw && test -d ~/workspace/homelab/wiki/wiki/entities && test -d ~/workspace/homelab/wiki/wiki/concepts && test -d ~/workspace/homelab/wiki/wiki/decisions && test -d ~/workspace/homelab/wiki/wiki/meetings && test -d ~/workspace/homelab/wiki/outputs && test -d ~/workspace/homelab/wiki/.drafts && test -d ~/workspace/homelab/wiki/_meta` | Exits with code 0 |
| AC-2 | SCHEMA.md exists with required content | `test -f ~/workspace/homelab/wiki/SCHEMA.md && grep -q 'kebab-case' ~/workspace/homelab/wiki/SCHEMA.md && grep -q 'frontmatter' ~/workspace/homelab/wiki/SCHEMA.md && grep -q 'ingest' ~/workspace/homelab/wiki/SCHEMA.md && grep -q 'wikilinks' ~/workspace/homelab/wiki/SCHEMA.md` | Exits with code 0 |
| AC-3 | _index.md and log.md exist with structure | `test -f ~/workspace/homelab/wiki/_index.md && grep -q '## Entities' ~/workspace/homelab/wiki/_index.md && test -f ~/workspace/homelab/wiki/log.md && grep -q 'Operation' ~/workspace/homelab/wiki/log.md` | Exits with code 0 |
| AC-4 | taxonomy.md exists with tag domains | `test -f ~/workspace/homelab/wiki/_meta/taxonomy.md && grep -q 'infrastructure' ~/workspace/homelab/wiki/_meta/taxonomy.md && grep -q 'knowledge-management' ~/workspace/homelab/wiki/_meta/taxonomy.md` | Exits with code 0 |
| AC-5 | Standalone git repo with .gitignore | `cd ~/workspace/homelab/wiki && git rev-parse --git-dir > /dev/null 2>&1 && grep -q 'workspace.json' .gitignore && git log --oneline -1` | Exits with code 0, shows initial commit |
| AC-6 | Obsidian vault config exists | `test -f ~/workspace/homelab/wiki/.obsidian/app.json` | Exits with code 0 |

## Tasks / Subtasks

- [x] Task 1: Create wiki directory structure (AC: 1)
  - [x] Create `~/workspace/homelab/wiki/` and all subdirectories: `raw/`, `wiki/entities/`, `wiki/concepts/`, `wiki/decisions/`, `wiki/meetings/`, `outputs/`, `.drafts/`, `_meta/`
  - [x] Add `.gitkeep` files in empty directories to ensure git tracks them

- [x] Task 2: Write SCHEMA.md (AC: 2)
  - [x] Define page type specifications (entity, concept, decision, meeting) with required fields
  - [x] Define YAML frontmatter template with all required fields: title, confidence (0.0-1.0), last_ingested (ISO date), sources (list), content_hash (sha256 prefix), stale (boolean), provenance (extracted|inferred|ambiguous), tags (from taxonomy)
  - [x] Document naming conventions: kebab-case filenames, no spaces, lowercase
  - [x] Document cross-referencing rules: use Obsidian `[[wikilinks]]` for internal links, run cross-linker pass after each ingest
  - [x] Document the three LLM Wiki operations (ingest, query, lint) with expected inputs/outputs
  - [x] Document the three-layer architecture: Raw Sources (human, immutable) / The Wiki (LLM, generated) / The Schema (human, config)
  - [x] Reference the Karpathy LLM Wiki pattern as the design foundation

- [x] Task 3: Create _index.md and log.md (AC: 3)
  - [x] Write `_index.md` with section headers: `## Entities`, `## Concepts`, `## Decisions`, `## Meetings`, each with a placeholder comment explaining the format (one-line summary per page, linked)
  - [x] Write `log.md` with header documenting format: `| Timestamp | Operation | Pages Affected | Source | Notes |`
  - [x] Add an initial log entry recording wiki creation

- [x] Task 4: Create taxonomy.md (AC: 4)
  - [x] Define tag domains: infrastructure, observability, security, networking, ai-dev, knowledge-management, automation, storage, proxmox, ansible, docker, homelab-ops
  - [x] Document process for adding new tags (add to taxonomy, use in frontmatter, cross-linker picks up automatically)

- [x] Task 5: Initialize git repo and configure .gitignore (AC: 5)
  - [x] Create `.gitignore` with Obsidian exclusions
  - [x] Run `git init` inside `~/workspace/homelab/wiki/`
  - [x] Stage all files and create initial commit: `wiki: initialize LLM Wiki structure and schema`

- [x] Task 6: Create minimal Obsidian vault config (AC: 6)
  - [x] Create `wiki/.obsidian/app.json` with minimal settings (e.g., `{"showLineNumber": true, "strictLineBreaks": true}`)
  - [x] Ensure `.obsidian/` is committed but workspace state files are gitignored

## Dev Notes

### Architecture Context

This story implements the **LLM Wiki pattern** from Karpathy's gist, adapted for the homelab project. The wiki is the first component of the Phase 2b Knowledge Management stack (Epic 5 > Epic 6 > Epic 7).

**Three-layer architecture:**
- **Raw Sources** (`raw/`) -- human-owned, immutable source documents
- **The Wiki** (`wiki/`) -- LLM-generated pages: entities, concepts, decisions, cross-references
- **The Schema** (`SCHEMA.md`) -- human-owned configuration telling the LLM how the wiki is structured

**Key design decisions from architecture.md:**
- Wiki is a standalone git repo, NOT a subdirectory of the homelab monorepo (per research Part 9: "One repo per vault is strongly recommended")
- Uses Obsidian `[[wikilinks]]` for cross-references (powers Obsidian graph view and backlinks panel)
- YAML frontmatter on every page for Dataview queries on the laptop
- No vector DB needed at this scale (~100 articles / 400K words) -- LLM navigates via `_index.md`
- `.drafts/` staging area exists for future human-review-before-promotion workflow (not wired in this story)

**Directory structure from research report Part 8:**
```
project-wiki/                    <- Obsidian vault root
├── .obsidian/                   <- Obsidian config (gitignored selectively)
├── raw/                         <- Immutable source documents
├── wiki/                        <- LLM-owned pages
│   ├── entities/                <- Person, tool, service pages
│   ├── concepts/                <- Architectural patterns, methodologies
│   ├── decisions/               <- ADRs, retro learnings
│   └── meetings/                <- Meeting note summaries
├── outputs/                     <- Query results, generated reports
├── .drafts/                     <- Staging area for human review
├── _index.md                    <- Self-maintained page catalogue
├── _meta/
│   └── taxonomy.md              <- Controlled tag vocabulary
├── log.md                       <- Append-only operation log
└── SCHEMA.md                    <- LLM instructions
```

### What This Story Does NOT Do

- Does NOT create Hermes skills (Stories 5.2-5.4)
- Does NOT configure Obsidian Git plugin for auto-pull (Story 5.5)
- Does NOT set up the laptop meta-vault (Story 5.6)
- Does NOT wire git auto-push cron (Story 5.8)
- Does NOT ingest any content -- the wiki starts empty (structure only)

### YAML Frontmatter Reference

Every wiki page MUST include this frontmatter (from research Part 8):
```yaml
---
title: Page Title
confidence: 0.85
last_ingested: 2026-04-16
sources:
  - source-document.md
content_hash: abc123
stale: false
provenance: extracted    # extracted | inferred | ambiguous
tags:
  - infrastructure
  - proxmox
---
```

### File Naming Convention

- Kebab-case: `proxmox-clustering.md`, `traefik-routing.md`
- No spaces, no uppercase in filenames
- Directories use lowercase: `entities/`, `concepts/`, `decisions/`, `meetings/`

### Project Structure Notes

- Wiki lives at `~/workspace/homelab/wiki/` on ct-dev-homelab -- a new standalone git repo
- This is separate from the three existing repos (homelab-infra, homelab-apps, homelab-playbook)
- The wiki directory root IS the Obsidian vault root
- On the laptop, this will be cloned as `homelab-wiki/` (Story 5.6)

### References

- [Source: planning-artifacts/research/technical-llm-knowledge-management-research-2026-04-11.md#Part 8] -- Canonical directory structure, YAML frontmatter, naming conventions
- [Source: planning-artifacts/research/technical-llm-knowledge-management-research-2026-04-11.md#Part 9] -- Multi-vault architecture, git sync pattern, .gitignore
- [Source: planning-artifacts/research/technical-llm-knowledge-management-research-2026-04-11.md#Part 1] -- LLM Wiki pattern: three-layer architecture, operations (ingest, query, lint), navigation files
- [Source: planning-artifacts/architecture.md#Planned Decisions] -- "LLM Wiki directory structure and SCHEMA.md convention per project"
- [Source: planning-artifacts/epics.md#Epic 5] -- Story 5.1 scope and acceptance criteria
- [Source: planning-artifacts/prd.md#FR53] -- "Hermes can maintain a structured LLM Wiki per project"

## Dev Agent Record

### Agent Model Used

claude-opus-4-6 (1M context)

### Debug Log References

None -- clean implementation, all 6 eval assertions passed on first run.

### Completion Notes List

- Created full wiki directory tree at `~/workspace/homelab/wiki/` following the Karpathy LLM Wiki three-layer architecture
- SCHEMA.md covers all required sections: three-layer architecture, naming conventions, page types (entity/concept/decision/meeting), YAML frontmatter spec (all 8 fields), cross-referencing rules with Obsidian wikilinks, and all three operations (ingest/query/lint) with inputs/outputs
- _index.md has section headers for Entities, Concepts, Decisions, Meetings with format comments
- log.md has the operation log table format and an initial creation entry
- taxonomy.md has 7 tag domains (infrastructure, observability, security, networking, ai-dev, knowledge-management, automation) covering all 12+ required tags
- Standalone git repo initialized with initial commit (e62e022), separate from homelab monorepo
- Obsidian vault recognizable via .obsidian/app.json; workspace state files gitignored
- All 6 acceptance criteria verified via eval assertions

### File List

- wiki/SCHEMA.md (new) -- LLM Wiki configuration and operation definitions
- wiki/_index.md (new) -- Page catalogue with section headers
- wiki/log.md (new) -- Append-only operation log with initial entry
- wiki/_meta/taxonomy.md (new) -- Controlled tag vocabulary
- wiki/.gitignore (new) -- Obsidian workspace exclusions
- wiki/.obsidian/app.json (new) -- Minimal Obsidian vault config
- wiki/raw/.gitkeep (new) -- Directory placeholder
- wiki/wiki/entities/.gitkeep (new) -- Directory placeholder
- wiki/wiki/concepts/.gitkeep (new) -- Directory placeholder
- wiki/wiki/decisions/.gitkeep (new) -- Directory placeholder
- wiki/wiki/meetings/.gitkeep (new) -- Directory placeholder
- wiki/outputs/.gitkeep (new) -- Directory placeholder
- wiki/.drafts/.gitkeep (new) -- Directory placeholder
- wiki/_meta/.gitkeep (new) -- Directory placeholder
- homelab-playbook/_bmad-output/implementation-artifacts/sprint-status.yaml (modified) -- Status updated
- homelab-playbook/_bmad-output/implementation-artifacts/5-1-create-llm-wiki-structure-and-schema.md (modified) -- Story file updated

## Change Log

- 2026-04-16: Implemented Story 5.1 -- Created LLM Wiki directory structure, SCHEMA.md, _index.md, log.md, taxonomy.md, .gitignore, .obsidian/app.json. Initialized standalone git repo with initial commit.
- 2026-04-16: Deployed to ct-dev-test (192.168.50.152) -- All 7 eval assertions passed (6 AC + .trash/ gitignore). Committed .gitignore fix (e999679). Status moved to done.
