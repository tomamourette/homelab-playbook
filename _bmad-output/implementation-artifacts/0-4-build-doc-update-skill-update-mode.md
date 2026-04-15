# Story 0.4: Build Doc Update Skill — Update Mode

Status: done

## Story

As a developer,
I want to run `/update-project-docs` to incrementally update only the affected documentation sections after an epic,
so that my project docs stay current without full regeneration.

## Acceptance Criteria

1. **Given** a project with stale docs (as identified by check mode)
   **When** I run `/update-project-docs`
   **Then** the skill presents a change plan showing which docs and sections will be updated (FR45, AT-6.3)

2. **Given** a presented change plan
   **When** the user confirms
   **Then** the skill updates only the affected sections while preserving unchanged sections exactly (FR46)

3. **Given** the update is complete
   **When** the state file is checked
   **Then** `project-scan-report.json` is updated with new git ref and section timestamps (FR50, AT-6.5)

4. **Given** the user does not confirm the change plan
   **When** they decline or modify
   **Then** no documentation files are modified (same as check mode)

5. **Given** the BMAD installation at `.claude/skills/bmad-*/`
   **When** this update is applied
   **Then** zero files in `.claude/skills/bmad-*/` are modified (NFR-INT-5)

## Eval Assertions

<!-- Binary test assertions derived from acceptance criteria. Used by /autoresearch:fix for post-code-review iteration loops. -->

| # | Assertion | Command/Check | Pass Criteria |
|---|-----------|---------------|---------------|
| AC-1 | Change plan presented | Run `/update-project-docs` on project with stale docs | Plan lists affected docs, sections, and changed source files |
| AC-2 | Section-level update | After confirmed update, diff the doc file | Only the affected H2/H3 section content changed; all other sections identical |
| AC-3 | State file updated | Read `project-scan-report.json` after update | `git_ref_at_last_update` matches current HEAD; section timestamps updated |
| AC-4 | Decline preserves docs | Decline the plan, check `git diff docs/` | Empty output (no docs modified) |
| AC-5 | No BMAD files modified | `git diff .claude/skills/bmad-*/` | Empty output |

## Tasks / Subtasks

- [x] Task 1: Add update mode to workflow.md (AC: #1)
  - [x] Read the existing `.claude/skills/bmad-update-project-docs/workflow.md`
  - [x] Replace the update mode stub ("Not yet implemented") with routing to `./instructions.md` with `mode=update`
  - [x] Keep check and full mode logic unchanged

- [x] Task 2: Add update mode logic to instructions.md (AC: #1, #2, #3, #4)
  - [x] Read the existing `.claude/skills/bmad-update-project-docs/instructions.md`
  - [x] Add `## Update Mode` section after the existing check mode section
  - [x] Reuse Phase 0 (git check) and Phase 1 (detect changes) from check mode — same logic
  - [x] Reuse Phase 2 (map changes to doc sections) from check mode — same logic
  - [x] Add Phase 3 — PRESENT CHANGE PLAN:
    - Show each doc file, affected sections, and the changed source files that triggered it
    - Ask user: "Apply these updates? [Y] Yes / [N] No / [S] Select specific docs"
    - If N: exit without changes (AC #4)
    - If S: let user select which docs to update
  - [x] Add Phase 4 — EXECUTE SECTION UPDATES:
    - For each confirmed doc:
      a. Read current doc file completely
      b. Read the changed source files that affect this doc
      c. Load `./templates/section-update-prompt.md` for the regeneration prompt
      d. Identify the target H2/H3 section(s) by heading match
      e. Regenerate ONLY the affected section content
      f. Replace the section in the doc file, preserving everything before and after
      g. Write the updated doc file
    - For docs marked `_full_regenerate` (e.g., source-tree-analysis.md): regenerate entire file
  - [x] Add Phase 5 — UPDATE STATE:
    - Update `project-scan-report.json` with:
      - `git_ref_at_last_update` = current HEAD
      - `last_incremental_update` = current date
      - `section_timestamps` updated for each modified doc/section
      - `stale_docs` = [] (cleared after successful update)

- [x] Task 3: Enhance section-update-prompt.md template (AC: #2)
  - [x] Read the existing `.claude/skills/bmad-update-project-docs/templates/section-update-prompt.md`
  - [x] Replace the placeholder content with the production prompt:
    - Include current section content as context
    - Include changed source files as input
    - Instruct to match existing writing style and detail level
    - Instruct to output ONLY the section (heading + body)
    - Add examples of good vs bad section updates

- [x] Task 4: Test update mode (AC: #1, #2, #3, #4, #5)
  - [x] Run `/update-project-docs` on the homelab project (should detect stale docs from recent changes)
  - [x] Verify change plan is presented correctly
  - [x] Confirm the plan and verify section-level update works
  - [x] Check that unchanged sections are preserved exactly
  - [x] Verify `project-scan-report.json` is updated correctly
  - [x] Run `git diff .claude/skills/bmad-*/` and verify zero changes

## Dev Notes

### What This Story Adds

This story extends the existing `bmad-update-project-docs` skill (created in Story 0.3) with the update mode — the core capability that actually modifies documentation sections.

### Architecture Reference

From the research document, the update mode algorithm:

```
Phase 1-2: Same as check mode (detect changes, map to docs)
Phase 3: Present change plan, get user confirmation
Phase 4: For each confirmed doc:
   a. Read current doc
   b. Read changed sources
   c. Regenerate ONLY affected sections
   d. Replace in-place, preserve everything else
Phase 5: Update state file
```

### Section-Level Update Strategy

**Key principle:** Read the full doc, find the target section by H2/H3 heading, regenerate only that section's content from the changed source files, and write back the full doc with only that section changed.

For `_full_regenerate` docs (like `source-tree-analysis.md`), regenerate the entire file — section-level doesn't apply when the whole tree needs refreshing.

### Previous Story Learnings (Story 0.3)

- Skill structure works: 5 files, visible in Claude Code immediately
- Git prerequisite check (Phase 0) catches non-git repos early
- Catch-all mapping exclusion logic: `docs: []` patterns skip catch-all
- State file path = `{project_knowledge}/project-scan-report.json` (same as bmad-document-project)

### Files to Modify (not create)

- `.claude/skills/bmad-update-project-docs/workflow.md` — replace update mode stub
- `.claude/skills/bmad-update-project-docs/instructions.md` — add update mode section
- `.claude/skills/bmad-update-project-docs/templates/section-update-prompt.md` — replace placeholder

### References

- [Source: architecture.md — Incremental Documentation Skill]
- [Source: prd.md — FR43, FR45, FR46, FR50]
- [Source: research/technical-incremental-docs-autoresearch-2026-04-03.md — Update Mode Core Algorithm]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

None — clean implementation.

### Completion Notes List

- Added update mode to workflow.md (replaced stub with routing to instructions.md)
- Added update mode logic to instructions.md (Phases 3-5: change plan, section updates, state update)
- Enhanced section-update-prompt.md with production prompt, good/bad examples, and full-regenerate guidance
- Reuses Phases 0-2 from check mode (no duplication)
- User confirmation required before any doc writes (Y/N/S options)
- Section-level update: find heading → extract section → regenerate → replace in-place
- Full regeneration path for `_full_regenerate` docs
- Zero BMAD files modified

### File List

- `.claude/skills/bmad-update-project-docs/workflow.md` (modified — update mode stub replaced)
- `.claude/skills/bmad-update-project-docs/instructions.md` (modified — update mode section added)
- `.claude/skills/bmad-update-project-docs/templates/section-update-prompt.md` (modified — placeholder replaced with production content)

### Review Findings

- [x] [Review][Patch] D1: Check mode must stop writing `git_ref_at_last_update` — only update mode should advance the baseline [`instructions.md` Phase 4, step 11] -- FIXED
- [x] [Review][Patch] D2: Partial select `[S]` must keep unselected docs in `stale_docs` instead of clearing to `[]` [`instructions.md` Phase U5, step 17] -- FIXED
- [x] [Review][Patch] D3: Add defensive path guard in Phase 4 — skip and warn if target path is under `.claude/skills/bmad-*/` [`instructions.md` Phase U4, step 15a] -- FIXED
- [x] [Review][Patch] P1: Add fallback for invalid/unreachable git ref in state file [`instructions.md` Phase 1, step 1] -- FIXED
- [x] [Review][Patch] P2: Add error handling when heading not found in doc — skip, warn, list as unresolved [`instructions.md` Phase U4, step 15e] -- FIXED
- [x] [Review][Patch] P3: Add cancel/back path from `[S]` select mode [`instructions.md` Phase U3, step 14] -- FIXED
- [x] [Review][Patch] P4: Section update prompt should instruct LLM to preserve items from unchanged source files [`templates/section-update-prompt.md`] -- FIXED
- [x] [Review][Patch] P5: Strip blank lines from git output and filter deleted files before Phase 2 [`instructions.md` Phase 1, step 3] -- FIXED
- [x] [Review][Patch] P6: Renumber update mode steps to avoid collision with check mode numbering [`instructions.md`] -- FIXED
- [x] [Review][Defer] W1: Date fallback baseline unreliable (mtime varies across clones/CI) [`instructions.md` Phase 1] — deferred, pre-existing from Story 0-3
- [x] [Review][Defer] W2: Unbounded `{source_file_contents}` can overflow LLM context [`templates/section-update-prompt.md`] — deferred, requires architectural chunking decision
- [x] [Review][Defer] W3: Mode detection has no priority when multiple keywords match [`workflow.md`] — deferred, pre-existing
- [x] [Review][Defer] W4: Multi-repo git detection limitation [`instructions.md` Phase 1] — deferred, architectural constraint
