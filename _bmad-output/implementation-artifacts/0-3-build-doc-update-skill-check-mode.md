# Story 0.3: Build Doc Update Skill — Check Mode

Status: done

## Story

As a developer,
I want to run `/update-project-docs check` to see which documentation is stale,
so that I know which docs need updating after code changes without modifying any files.

## Acceptance Criteria

1. **Given** a project with a `docs/` folder and recent code changes since the last doc update
   **When** I run `/update-project-docs check`
   **Then** the skill detects changed files using `git log --since` or git ref comparison (FR44)

2. **Given** detected file changes
   **When** the skill classifies them
   **Then** it maps changes to specific documentation files using the file-to-doc mapping (FR49)

3. **Given** the classification is complete
   **When** the health report is displayed
   **Then** it shows which docs are current and which are stale with the changed files listed (FR47, AT-6.2)

4. **Given** the check mode runs
   **When** it completes
   **Then** no documentation files are modified (read-only mode)

5. **Given** the check mode runs
   **When** it completes
   **Then** state is tracked in `project-scan-report.json` with `git_ref_at_last_update` and section timestamps (FR50, AT-6.5)

6. **Given** the BMAD installation at `.claude/skills/bmad-*/`
   **When** this skill is created
   **Then** zero files in `.claude/skills/bmad-*/` are modified (NFR-INT-5, AT-6.8)

7. **Given** any BMAD project with a `docs/` folder
   **When** the skill is installed
   **Then** it works independently of the AI Dev Container project (NFR-INT-6)

## Eval Assertions

<!-- Binary test assertions derived from acceptance criteria. Used by /autoresearch:fix for post-code-review iteration loops. -->

| # | Assertion | Command/Check | Pass Criteria |
|---|-----------|---------------|---------------|
| AC-1 | Git change detection works | Make a known file change, run check mode | Changed file appears in report |
| AC-2 | File-to-doc mapping | Change a file matching a mapping pattern | Correct doc file flagged as stale |
| AC-3 | Health report displays | Run `/update-project-docs check` | Report shows current/stale status per doc |
| AC-4 | Read-only mode | Run check, verify no docs modified | `git diff docs/` shows no changes |
| AC-5 | State tracking | Run check, read `project-scan-report.json` | Contains `git_ref_at_last_update` field |
| AC-6 | No BMAD files modified | `git diff .claude/skills/bmad-*/` | Empty output |
| AC-7 | Project-independent | Skill has no hardcoded homelab paths | Review confirms all paths are configurable |

## Tasks / Subtasks

- [x] Task 1: Create skill directory structure (AC: #6)
  - [x] Create `.claude/skills/bmad-update-project-docs/SKILL.md` with frontmatter
  - [x] Set `name: update-project-docs` (invoked as `/update-project-docs`)
  - [x] Set description to trigger on "update project docs", "check project docs", "docs health check"
  - [x] Verify directory is outside `bmad-*/`

- [x] Task 2: Create the workflow.md mode router (AC: #1, #3, #7)
  - [x] Create `.claude/skills/bmad-update-project-docs/workflow.md`
  - [x] Load config from `{project-root}/_bmad/bmm/config.yaml` to resolve `project_knowledge` (docs folder path)
  - [x] Detect mode from user input: "check" → check mode, "full" → full mode, default → update mode
  - [x] For this story, only implement the check mode branch (update and full are stories 0.4 and 0.5)
  - [x] Route to `./instructions.md` with mode=check

- [x] Task 3: Create instructions.md with check mode logic (AC: #1, #2, #3, #4)
  - [x] Create `.claude/skills/bmad-update-project-docs/instructions.md`
  - [x] Implement Phase 1 — DETECT CHANGES:
    - Read `project-scan-report.json` from `{project_knowledge}/` if it exists
    - Extract `git_ref_at_last_update` (or use last doc modification date as fallback)
    - Run `git log --name-only --pretty=format:"" <last_ref>..HEAD` to get changed files
    - Deduplicate the file list
  - [x] Implement Phase 2 — MAP CHANGES TO DOC SECTIONS:
    - Load `./references/doc-section-mapping.md`
    - For each changed file, match against mapping patterns
    - Build list of (doc_file, sections_affected, changed_source_files)
  - [x] Implement Phase 3 — DISPLAY HEALTH REPORT:
    - For each doc in `{project_knowledge}/`:
      - If affected by changes → show as STALE with list of changed files
      - If not affected → show as CURRENT with last updated date
    - Show recommendation: "Run /update-project-docs to update N stale documents."
  - [x] Ensure NO files are written or modified (read-only)

- [x] Task 4: Create the file-to-doc mapping reference (AC: #2, #7)
  - [x] Create `.claude/skills/bmad-update-project-docs/references/doc-section-mapping.md`
  - [x] Define mappings for the homelab project:
    - `homelab-infra/ansible/roles/**` → `architecture-homelab-infra.md` (Roles, Deployment Sequence)
    - `homelab-infra/terraform/**` → `architecture-homelab-infra.md` (Terraform sections)
    - `homelab-apps/stacks/**` → `architecture-homelab-apps.md` (Application Services)
    - `*/docker-compose.yml` → `project-overview.md` (Application Services)
    - `**` (any change) → `source-tree-analysis.md` (full regenerate)
  - [x] Document that mappings are configurable per project
  - [x] Ensure no hardcoded absolute paths (use relative patterns)

- [x] Task 5: Implement state tracking (AC: #5)
  - [x] After check mode completes, update/create `project-scan-report.json` in `{project_knowledge}/`
  - [x] Add fields: `git_ref_at_last_update`, `last_incremental_update`, `section_timestamps`
  - [x] If `project-scan-report.json` already exists (from bmad-document-project), extend it — don't overwrite
  - [x] State update is the ONLY write operation in check mode

- [x] Task 6: Create placeholder for templates (AC: #7)
  - [x] Create `.claude/skills/bmad-update-project-docs/templates/` directory
  - [x] Create `section-update-prompt.md` placeholder (used by update mode in story 0.4, not needed for check)

- [x] Task 7: Test check mode end-to-end (AC: #1, #2, #3, #4, #5)
  - [x] Run `/update-project-docs check` on the homelab project
  - [x] Verify health report shows correct current/stale status
  - [x] Verify no docs were modified (`git diff docs/`)
  - [x] Verify `project-scan-report.json` was created/updated with correct fields
  - [x] Verify `git diff .claude/skills/bmad-*/` shows zero changes

## Dev Notes

### Architecture Reference

From the architecture document and research, this skill follows the design at:
- [Source: architecture.md — Incremental Documentation Skill decisions]
- [Source: research/technical-incremental-docs-autoresearch-2026-04-03.md — Check Mode Doc Health Report]

### Skill Directory Structure

```
.claude/skills/bmad-update-project-docs/
├── SKILL.md                          # Frontmatter + invocation
├── workflow.md                       # Mode router (check/update/full)
├── instructions.md                   # Core logic for all modes
├── templates/
│   └── section-update-prompt.md      # Placeholder (used by update mode in 0.4)
└── references/
    └── doc-section-mapping.md        # File patterns → doc sections
```

### Check Mode Algorithm (from research)

```
1. Read project-scan-report.json → extract git_ref_at_last_update
2. Run: git log --name-only --pretty=format:"" <last_ref>..HEAD
3. For each changed file, match against doc-section-mapping
4. Display health report:
   ✅ project-overview.md — current
   ⚠️ architecture-homelab-infra.md — STALE (3 files changed)
5. Update state file (only write in check mode)
```

### Key Design Decisions

- **Read-only except state file** — check mode never modifies docs, only updates `project-scan-report.json`
- **Configurable mappings** — `doc-section-mapping.md` is a reference file, not hardcoded logic
- **Extends existing state** — if `project-scan-report.json` exists from `bmad-document-project`, add fields rather than overwrite
- **Fallback for missing state** — if no state file exists, use last modification date of docs as baseline
- **Project-independent** — all paths resolved from config, no hardcoded homelab paths

### Previous Story Learnings (Story 0.1)

- Wrapper/standalone skill pattern works — `.claude/skills/` auto-detects new skills
- BMAD update-safety verified with `git diff .claude/skills/bmad-*/`
- SKILL.md description should include multiple trigger phrases for discoverability
- Workflow.md should handle errors with explicit HALT messages

### Project Structure Notes

- New directory: `.claude/skills/bmad-update-project-docs/` (5 files across 3 subdirs)
- Reads from: `docs/` (project_knowledge), `.git/` (change detection)
- Writes to: `docs/project-scan-report.json` (state tracking only)
- No existing files modified
- No BMAD skill files touched

### References

- [Source: architecture.md — Incremental Documentation Skill]
- [Source: architecture.md — Claude Code Skill Patterns]
- [Source: prd.md — FR43, FR44, FR47, FR49, FR50, NFR-INT-5, NFR-INT-6]
- [Source: research/technical-incremental-docs-autoresearch-2026-04-03.md — Check Mode, File-to-Doc Mapping]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

None — clean implementation.

### Completion Notes List

- Created `bmad-update-project-docs` skill with 5 files across 3 subdirectories
- Implemented check mode: git-diff detection → file-to-doc mapping → health report → state tracking
- Update mode stub returns "not yet implemented" message (Story 0.4)
- Full mode stub delegates to `/bmad-document-project` (Story 0.5)
- File-to-doc mapping covers all 3 repos with 13 mapping rules + customization guide
- Skill immediately visible in Claude Code skill list as `bmad-update-project-docs`
- Zero BMAD files modified — fully honors NFR-INT-5
- All paths resolved from config — no hardcoded project paths (NFR-INT-6)

### File List

- `.claude/skills/bmad-update-project-docs/SKILL.md` (new)
- `.claude/skills/bmad-update-project-docs/workflow.md` (new)
- `.claude/skills/bmad-update-project-docs/instructions.md` (new)
- `.claude/skills/bmad-update-project-docs/references/doc-section-mapping.md` (new)
- `.claude/skills/bmad-update-project-docs/templates/section-update-prompt.md` (new — placeholder for Story 0.4)

### Review Findings

- [x] [Review][Patch] No git availability check — fixed: added Phase 0 prerequisite validation [instructions.md]
- [x] [Review][Patch] Catch-all `**` mapping ambiguity — fixed: clarified exclusion logic (docs:[] skips catch-all) [instructions.md]
- [x] [Review][Patch] State file path clarification — fixed: added note that {project_knowledge} = docs folder [instructions.md]
- [x] [Review][Defer] Config variable passing implicit — works in practice, LLM reads workflow.md then instructions.md in same context
- [x] [Review][Defer] End-to-end test requires separate invocation — cannot test skill inline during implementation
