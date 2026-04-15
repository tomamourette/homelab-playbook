# Story 0.5: Build Doc Update Skill — Full Mode and Mapping Config

Status: done

## Story

As a developer,
I want `/update-project-docs full` to delegate to the existing `bmad-document-project` skill for complete regeneration,
so that I have a single entry point for both incremental and full documentation workflows.

## Acceptance Criteria

1. **Given** the doc update skill is installed
   **When** I run `/update-project-docs full`
   **Then** the skill delegates to `bmad-document-project` for a full rescan — no errors, no partial execution (FR48, AT-6.4)

2. **Given** the `references/doc-section-mapping.md` file
   **When** a different project uses this skill
   **Then** the mapping is configurable per project — patterns and doc targets can be edited without modifying skill code (FR49)

3. **Given** any BMAD project with a `docs/` folder and `_bmad/bmm/config.yaml`
   **When** the skill is installed
   **Then** all three modes (check, update, full) work correctly without homelab-specific assumptions (NFR-INT-6)

4. **Given** the BMAD installation at `.claude/skills/bmad-*/`
   **When** this update is applied
   **Then** zero files in `.claude/skills/bmad-*/` are modified (NFR-INT-5)

## Eval Assertions

<!-- Binary test assertions derived from acceptance criteria. Used by /autoresearch:fix for post-code-review iteration loops. -->

| # | Assertion | Command/Check | Pass Criteria |
|---|-----------|---------------|---------------|
| AC-1 | Full mode delegates to bmad-document-project | Run `/update-project-docs full` | Skill displays delegation message and invokes `/bmad-document-project` without errors |
| AC-2 | Mapping file is configurable | Review `references/doc-section-mapping.md` for project-independence notes | File contains customization instructions; no hardcoded absolute paths; patterns are clearly examples |
| AC-3 | Skill is project-independent | `grep -r "homelab" .claude/skills/bmad-update-project-docs/instructions.md .claude/skills/bmad-update-project-docs/workflow.md` | Empty output (no homelab-specific references in core skill logic) |
| AC-4 | No BMAD files modified | `git diff .claude/skills/bmad-*/` | Empty output (zero changes to BMAD skill files) |

## Tasks / Subtasks

- [x] Task 1: Implement full mode in instructions.md (AC: #1)
  - [x] Read the existing `.claude/skills/bmad-update-project-docs/instructions.md`
  - [x] Replace the one-line stub `*Delegates to /bmad-document-project — Story 0.5*` with a proper `## Full Mode` section
  - [x] Full mode logic: display delegation message, then invoke `/bmad-document-project` skill
  - [x] Add error handling: if `/bmad-document-project` skill is not available, HALT with clear message
  - [x] After delegation completes, update `project-scan-report.json`: set `git_ref_at_last_update` to HEAD, set `last_full_rescan` to current date, clear `stale_docs`

- [x] Task 2: Verify workflow.md routing is correct (AC: #1)
  - [x] Read `.claude/skills/bmad-update-project-docs/workflow.md`
  - [x] Verify the full mode section routes to `./instructions.md` with `mode=full` (not just displaying a message and invoking directly)
  - [x] If workflow.md currently invokes `/bmad-document-project` inline, change it to route to instructions.md like the other modes

- [x] Task 3: Ensure doc-section-mapping.md is project-independent (AC: #2, #3)
  - [x] Read `.claude/skills/bmad-update-project-docs/references/doc-section-mapping.md`
  - [x] Add a header comment or note explaining that these patterns are project-specific examples and should be customized per project
  - [x] Ensure the customization section explains how a new project would create their own mapping from scratch
  - [x] Verify no hardcoded absolute paths exist — all patterns must be relative

- [x] Task 4: Ensure instructions.md is project-independent (AC: #3)
  - [x] Audit instructions.md for any homelab-specific references
  - [x] Verify all paths resolve from `{project_knowledge}` config variable, not hardcoded
  - [x] Verify Phase 0 git check works generically (not container-specific)
  - [x] Verify state file path uses `{project_knowledge}/project-scan-report.json` consistently

- [x] Task 5: Test all three modes (AC: #1, #2, #3, #4)
  - [x] Run `/update-project-docs full` — verify it delegates to `bmad-document-project`
  - [x] Run `/update-project-docs check` — verify check mode still works
  - [x] Run `/update-project-docs` (default) — verify update mode still works
  - [x] Verify zero files modified under `.claude/skills/bmad-*/`

## Dev Notes

### What This Story Adds

This is the final story in the doc update skill trilogy (0-3: check, 0-4: update, 0-5: full+mapping). It completes the skill by:
1. Implementing the full mode delegation to `bmad-document-project`
2. Ensuring the mapping file is clearly documented as configurable
3. Ensuring the entire skill is project-independent

### Architecture Reference

Full mode is a **thin wrapper** — it does NOT duplicate bmad-document-project's logic. The relationship:

```
bmad-document-project          bmad-update-project-docs
├── initial_scan          <---- /update-project-docs full (delegates)
├── full_rescan           <---- /update-project-docs full (delegates)
│
│   SHARED:
├── docs/ output folder
├── project-scan-report.json (extended with incremental fields)
```

Full mode delegates, then updates the shared state file so check/update modes know the baseline has been refreshed.

### Current Skill Structure (do NOT create new files)

```
.claude/skills/bmad-update-project-docs/
├── SKILL.md                              (DO NOT MODIFY)
├── workflow.md                           (MODIFY — fix routing if needed)
├── instructions.md                       (MODIFY — add full mode section)
├── templates/
│   └── section-update-prompt.md          (DO NOT MODIFY)
└── references/
    └── doc-section-mapping.md            (MODIFY — add project-independence notes)
```

### Previous Story Learnings (Story 0-3 and 0-4)

- Skill structure: 5 files across 3 subdirectories — all already exist, do NOT create new files
- Phase numbering: check mode uses steps 0-11, update mode uses steps 12-17 (prefixed U3-U5). Full mode should use steps 18+ or prefix F1
- State file at `{project_knowledge}/project-scan-report.json` — shared with `bmad-document-project`
- `git_ref_at_last_update` should only be advanced when docs are actually updated (learned from code review D1)
- Defensive path guard exists in Phase U4 — skip writes to `.claude/skills/bmad-*/`
- Config resolution: `project_knowledge` comes from `_bmad/bmm/config.yaml`

### Files to Modify (not create)

- `.claude/skills/bmad-update-project-docs/workflow.md` — fix full mode routing if needed
- `.claude/skills/bmad-update-project-docs/instructions.md` — add full mode section
- `.claude/skills/bmad-update-project-docs/references/doc-section-mapping.md` — add project-independence documentation

### What NOT to Do

- Do NOT duplicate any bmad-document-project logic — delegate only
- Do NOT create new files — all skill files already exist
- Do NOT modify any `.claude/skills/bmad-*/` files
- Do NOT hardcode paths — resolve everything from config
- Do NOT change check mode or update mode behavior — they are done and reviewed

### References

- [Source: architecture.md — Incremental Documentation Skill decisions table]
- [Source: prd.md — FR48, FR49, NFR-INT-5, NFR-INT-6, AT-6.4]
- [Source: epics.md — Epic 0, Story 0-5]
- [Source: research/technical-incremental-docs-autoresearch-2026-04-03.md — Full mode design, relationship diagram]
- [Source: 0-4-build-doc-update-skill-update-mode.md — Prior story learnings and review findings]
- [Source: 0-3-build-doc-update-skill-check-mode.md — Foundational skill structure and patterns]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

None — clean implementation.

### Completion Notes List

- Replaced full mode stub in instructions.md with Phases F1-F2 (steps 18-22): skill availability check, delegation message, invoke bmad-document-project, post-delegation state update
- Fixed workflow.md full mode routing — changed from inline invocation to `./instructions.md` with `mode=full` (consistent with check and update modes)
- Added project-independence header to doc-section-mapping.md noting patterns are project-specific examples
- Expanded customization section with "starting from scratch" guide and minimal starter mapping template
- Audited instructions.md and workflow.md — homelab references only in example output blocks, all logic uses `{project_knowledge}` and `{project_name}` config variables
- Zero pre-existing BMAD skill files modified

### File List

- `.claude/skills/bmad-update-project-docs/workflow.md` (modified — full mode routing changed to instructions.md)
- `.claude/skills/bmad-update-project-docs/instructions.md` (modified — full mode section added, Phases F1-F2)
- `.claude/skills/bmad-update-project-docs/references/doc-section-mapping.md` (modified — project-independence notes and starter mapping added)

### Review Findings

- [x] [Review][Patch] D1: Add failure/cancellation handling for delegated bmad-document-project [`instructions.md` step 20] -- FIXED
- [x] [Review][Patch] P1: Replace homelab-specific filenames in example blocks with generic names [`instructions.md`] -- FIXED
- [x] [Review][Patch] P2: Align `last_full_scan` to `last_full_rescan` in check mode preserve list [`instructions.md` step 11] -- FIXED
- [x] [Review][Patch] P3: Full mode must update `section_timestamps` for all docs [`instructions.md` step 21] -- FIXED
- [x] [Review][Patch] P4: Remove `last_incremental_update` from full mode state update [`instructions.md` step 21] -- FIXED
- [x] [Review][Patch] P5: Clarify mapping rules — both specific and catch-all apply simultaneously [`doc-section-mapping.md`] -- FIXED
- [x] [Review][Defer] W1: Mode detection keyword ambiguity/priority — deferred, pre-existing
- [x] [Review][Defer] W2: project_knowledge path never validated for existence — deferred, pre-existing
- [x] [Review][Defer] W3: No schema definition for project-scan-report.json — deferred, architectural
- [x] [Review][Defer] W4: Concurrency across modes — deferred, unrealistic for single-user skill
