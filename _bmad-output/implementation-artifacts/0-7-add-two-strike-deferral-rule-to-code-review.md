# Story 0.7: Add Two-Strike Deferral Rule to Code Review

Status: done

## Story

As a developer,
I want the `/code-review-ab` skill to enforce a Two-Strike Deferral rule — if a deferred item appeared in the previous story's review, it must be reclassified as `[Review][Backlog]` with a story key,
so that technical debt doesn't accumulate invisibly through repeated deferrals.

## Context (from Epic 0 Retrospective)

This addresses Pattern 2: the mode detection keyword ambiguity was deferred 3 times across stories 0.3, 0.4, 0.5. Each review re-discussed the same item. The Two-Strike rule prevents this.

## Acceptance Criteria

1. **Given** the `/code-review-ab` skill (or its underlying workflow)
   **When** a reviewer encounters a `[Review][Defer]` item
   **Then** the review guidance instructs: check if this deferral matches one from the previous story's review findings

2. **Given** a deferral that appeared in the previous story's review
   **When** the reviewer identifies it
   **Then** it MUST be reclassified as `[Review][Backlog]` with a suggested story key (e.g., `0-X-fix-description`)
   **And** the reviewer notes it for the SM to add to sprint-status.yaml

3. **Given** the BMAD installation at `.claude/skills/bmad-*/`
   **When** this story is implemented
   **Then** zero files in `.claude/skills/bmad-*/` are modified (NFR-INT-5)

4. **Given** the existing code-review-ab workflow
   **When** the two-strike rule is added
   **Then** the existing A/B comparison and standard review flows are unchanged

## Eval Assertions

<!-- Binary test assertions derived from acceptance criteria. Used by /autoresearch:fix for post-code-review iteration loops. -->

| # | Assertion | Command/Check | Pass Criteria |
|---|-----------|---------------|---------------|
| AC-1 | Two-strike instruction in review | Read code-review-ab workflow/fix-compare files | Contains two-strike deferral rule guidance |
| AC-2 | Backlog reclassification format | Review the guidance text | Shows `[Review][Backlog]` format with story key example |
| AC-3 | No BMAD files modified | `git diff .claude/skills/bmad-*/` | Empty output (no changes) |
| AC-4 | Existing flows unchanged | Compare A/B comparison logic before/after | Standard review and A/B flows preserved |

## Edge Cases & Error Scenarios

1. **Side effects:** Modifies guidance text in code-review-ab skill files — no functional code changes
2. **Dependency failure:** If code-review-ab skill doesn't exist, cannot proceed — but we verified it exists in the retro
3. **Assumptions:** The code-review-ab workflow has a section where review classification guidance can be added or extended

## Tasks / Subtasks

- [x] Task 1: Read all code-review-ab skill files to find the right insertion point for review classification guidance
- [x] Task 2: Add Two-Strike Deferral rule instruction to the appropriate file
- [x] Task 3: Include example showing `[Review][Defer]` → `[Review][Backlog]` reclassification with story key
- [x] Task 4: Verify BMAD update-safety (`git diff .claude/skills/bmad-*/`)
- [x] Task 5: Verify existing A/B flow and standard review flow are unchanged

## Dev Notes

### What This Story Modifies

- `.claude/skills/code-review-ab/workflow.md` or `fix-compare.md` — add two-strike guidance

### Source

- Epic 0 Retrospective (2026-04-04): Pattern 2 (repeated deferrals)
- Action Item 2 from retro

### Design

The rule is simple: "If a `[Review][Defer]` item matches a deferral from the previous story's review findings, it MUST be reclassified as `[Review][Backlog]` with a story key." This is review guidance, not automation — the reviewer enforces it.

## Dev Agent Record

- **Agent Model Used:** claude-opus-4-6 (Opus 4.6, 1M context)
- **Completion Notes:**
  - Read all three code-review-ab skill files (SKILL.md, workflow.md, fix-compare.md) and the story file
  - Identified workflow.md Step 1 (triage phase) as the correct insertion point -- between finding classification and fix option presentation
  - Added "Step 1.5: Two-Strike Deferral Rule" section to workflow.md with full rule description, lookup procedure, reclassification instructions, and before/after example
  - Preserved all existing content: Step 1 (standard review + A/B option menu), Step 2 (post-review), initialization block, and critical notes are unchanged
  - fix-compare.md was not modified -- the deferral rule belongs in the triage phase (workflow.md), not the fix comparison phase
  - SKILL.md was not modified -- no changes needed to skill metadata
  - Zero files under .claude/skills/bmad-*/ were touched
- **File List:**
  - `.claude/skills/code-review-ab/workflow.md` — added Step 1.5 (Two-Strike Deferral Rule)
- **Review Findings:**
  - No issues found. The insertion is purely additive guidance text. Existing A/B comparison logic and standard review flow options 0-3 are fully preserved. The new step 1.5 sits logically between triage classification and fix option presentation.
