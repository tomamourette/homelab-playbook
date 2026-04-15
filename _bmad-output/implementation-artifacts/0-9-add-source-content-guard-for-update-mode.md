# Story 0.9: Add Source Content Guard for Update Mode

Status: done

## Story

As a developer,
I want the `/update-project-docs` update mode to detect and handle when source file content exceeds a safe threshold for LLM context,
so that the section update prompt doesn't silently truncate or fail when many files have changed.

## Context (from Epic 0 Retrospective)

This addresses Pattern 4: Story 0.4 deferred W2 — "Unbounded source file contents can overflow LLM context." The section-update prompt stuffs all changed source files into LLM context. With many changes (e.g., after a large epic), this could be hundreds of KB. Per the retro, this must be resolved before heavy use of update mode.

## Acceptance Criteria

1. **Given** source files that exceed a configurable size threshold (e.g., 50KB combined)
   **When** update mode prepares the section-update prompt
   **Then** it warns the user about the content size before proceeding

2. **Given** source files exceeding the threshold
   **When** the user confirms to proceed
   **Then** the skill processes one doc at a time with only its relevant source files (not all source files at once)

3. **Given** source files under the threshold
   **When** update mode runs normally
   **Then** existing behavior is unchanged — no warning, no chunking

4. **Given** the BMAD installation at `.claude/skills/bmad-*/`
   **When** this story is implemented
   **Then** zero files in `.claude/skills/bmad-*/` are modified (NFR-INT-5)

## Eval Assertions

<!-- Binary test assertions derived from acceptance criteria. Used by /autoresearch:fix for post-code-review iteration loops. -->

| # | Assertion | Command/Check | Pass Criteria |
|---|-----------|---------------|---------------|
| AC-1 | Size threshold check exists | Read instructions.md update mode section | Contains source content size calculation and threshold comparison |
| AC-2 | Warning displayed for large content | Read instructions.md | Warning message shown when threshold exceeded, with user confirmation |
| AC-3 | Normal flow unchanged | Read instructions.md | Below-threshold path matches existing update mode logic |
| AC-4 | No BMAD files modified | `git diff .claude/skills/bmad-*/` | Empty output |

## Edge Cases & Error Scenarios

1. **Side effects:** Modifies update mode logic in instructions.md — adds a size check before section regeneration
2. **Dependency failure:** If source files can't be read (deleted between detection and update), skip with warning
3. **Assumptions:** LLM context has a practical limit; 50KB of source content is a reasonable default threshold; the threshold should be configurable via a variable in the instructions

## Tasks / Subtasks

- [x] Task 0: Verify `/update-project-docs` skill files exist and update mode works (from Story 0.4/0.5)
- [x] Task 1: Read current instructions.md update mode (Phase U4) to understand how source files are loaded
- [x] Task 2: Add source content size calculation before Phase U4 section regeneration
- [x] Task 3: Add threshold comparison with configurable limit (default 50KB)
- [x] Task 4: Add warning message and user confirmation when threshold exceeded
- [x] Task 5: Add per-doc processing path for large content (only relevant source files per doc, not all at once)
- [x] Task 6: Verify below-threshold path is unchanged
- [x] Task 7: Verify BMAD update-safety (`git diff .claude/skills/bmad-*/`)

## Dev Notes

### What This Story Modifies

- `.claude/skills/bmad-update-project-docs/instructions.md` — update mode Phase U4, add size guard

### Source

- Epic 0 Retrospective (2026-04-04): Pattern 4 (unbounded input), Deferred Debt D2
- Story 0.4 Review Finding W2: "Unbounded {source_file_contents} can overflow LLM context"

### Previous Story Learnings (Story 0.4)

- Update mode Phase U4 reads changed source files and passes them to section-update-prompt.md
- The `{source_file_contents}` template variable receives all source content
- For small changes this works fine, but large epics touching many files would overflow
- Section-update-prompt.md already scopes to "the changed source files that affect this doc" — the guard ensures total size stays manageable

### Design Decision

Three options were considered in the retro:
(a) Cap source files at N KB and summarize the rest
(b) Process one doc at a time with only its relevant source files
(c) Add a warning when input exceeds threshold

This story implements (c) warning + (b) per-doc processing as the mitigation path. Option (a) summarization is more complex and deferred.

## Dev Agent Record

**Agent Model Used:** claude-opus-4-6 (Opus 4.6, 1M context)

### Completion Notes

- Read story file, instructions.md, and section-update-prompt.md before making changes
- Inserted new step **c3 (Source Content Size Guard)** into Phase U4, between step 15c2 (gather implementation context) and step 15d (load section update prompt)
- Guard calculates combined character count of all source file contents across confirmed docs
- Default threshold set to 50,000 characters (~50KB) as specified
- Below-threshold path is a no-op pass-through — zero changes to existing behavior
- Above-threshold path presents warning with total size, threshold, file count, and doc count
- User gets three choices: [C] continue anyway, [P] per-doc processing, [X] cancel
- Per-doc processing mode executes steps 15b-15g individually per doc with only that doc's source files
- No files under `.claude/skills/bmad-*/` were modified

### File List

- `.claude/skills/bmad-update-project-docs/instructions.md` — added step c3 (source content size guard) to Phase U4
- `homelab-playbook/_bmad-output/implementation-artifacts/0-9-add-source-content-guard-for-update-mode.md` — status updated to done

### Review Findings

- **No issues found.** The guard is purely additive — inserted as a new numbered step between c2 and d. The below-threshold path explicitly says "proceed normally to step 15d" which preserves identical behavior. The above-threshold path's per-doc mode references existing steps (15b-15g) without modifying them.
