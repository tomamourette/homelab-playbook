# Story 0.6: Add Edge Cases Section and Task 0 Convention to Story Template

Status: done

## Story

As a developer,
I want the `/create-story-with-evals` wrapper to prompt for edge cases, error scenarios, and include a Task 0 verification handoff when applicable,
so that error handling gaps are caught at story design time (not code review) and cross-session skill verification is formalized.

## Context (from Epic 0 Retrospective)

This addresses two patterns identified in the Epic 0 retrospective:
- **Pattern 1:** Error handling gaps flagged in 4/5 stories — story template didn't prompt for error scenarios
- **Pattern 5:** Cross-session testing limitation — skills can't be tested in the session that creates them

## Acceptance Criteria

1. **Given** the `/create-story-with-evals` workflow
   **When** a story is created
   **Then** the generated story includes an "Edge Cases & Error Scenarios" section between Acceptance Criteria and Eval Assertions
   **And** the section prompts for three questions: (a) What side effects does this story produce? (b) What happens when a dependency fails? (c) What assumptions does this story make?

2. **Given** a story whose predecessor created or modified a skill/role
   **When** the story is created via `/create-story-with-evals`
   **Then** Task 0 is included as the first task: "Verify previous story's skill/role invocation"

3. **Given** the BMAD installation at `.claude/skills/bmad-*/`
   **When** this story is implemented
   **Then** zero files in `.claude/skills/bmad-*/` are modified (NFR-INT-5)

4. **Given** the existing story creation workflow
   **When** the edge cases section is added
   **Then** the workflow still produces all original sections (Story, AC, Eval Assertions, Tasks, Dev Notes) unchanged

## Eval Assertions

<!-- Binary test assertions derived from acceptance criteria. Used by /autoresearch:fix for post-code-review iteration loops. -->

| # | Assertion | Command/Check | Pass Criteria |
|---|-----------|---------------|---------------|
| AC-1 | Edge Cases section in template | Read `create-story-with-evals/templates/eval-assertions.md` | Contains "Edge Cases & Error Scenarios" with three prompting questions |
| AC-2 | Task 0 convention in workflow | Read `create-story-with-evals/workflow.md` | Contains Task 0 guidance for predecessor verification |
| AC-3 | No BMAD files modified | `git diff .claude/skills/bmad-*/` | Empty output |
| AC-4 | Original sections preserved | Compare workflow output structure before/after | All original sections present and unchanged |

## Edge Cases & Error Scenarios

1. **Side effects:** Modifies template and workflow files in `/create-story-with-evals/` — no other files affected
2. **Dependency failure:** If create-story-with-evals skill is missing, this story cannot proceed — prerequisite check
3. **Assumptions:** The current template structure has a clear insertion point for the new section; the workflow has a step where Task 0 logic can be added

## Tasks / Subtasks

- [x] Task 1: Read current template and workflow files to understand insertion points
- [x] Task 2: Add "Edge Cases & Error Scenarios" section to `templates/eval-assertions.md` with three prompting questions
- [x] Task 3: Add Task 0 convention guidance to `workflow.md` — when predecessor story created a skill/role, include Task 0
- [x] Task 4: Verify BMAD update-safety (`git diff .claude/skills/bmad-*/`)
- [x] Task 5: Test by reviewing the template output — confirm all sections present

## Dev Notes

### What This Story Modifies

- `.claude/skills/create-story-with-evals/templates/eval-assertions.md` — add edge cases section
- `.claude/skills/create-story-with-evals/workflow.md` — add Task 0 logic

### Source

- Epic 0 Retrospective (2026-04-04): Pattern 1 (error handling gaps), Pattern 5 (cross-session testing)
- Action Items 1 and 3 from retro

### Previous Story Learnings

- Template modifications in create-story-with-evals are immediately effective (no session restart needed)
- The eval assertions template guides the LLM during story generation — prompting questions work well for this

## Dev Agent Record

- **Agent Model Used:** claude-opus-4-6 (Opus 4.6 with 1M context)
- **Completion Notes:**
  - Task 1: Read all three files (story, eval-assertions template, workflow) to understand structure and insertion points
  - Task 2: Added "Edge Cases & Error Scenarios Section" to eval-assertions.md template with section format, three prompting questions (side effects, dependency failure, assumptions), and detailed guidance for each question
  - Task 3: Added Step 4b (Generate Edge Cases & Error Scenarios), Step 4c (Generate Task 0 when applicable), and updated Step 5 to handle insertion of both new sections plus Task 0 prepending in workflow.md
  - Task 4: Verified zero BMAD files modified via find command against timestamp marker — empty output confirmed
  - Task 5: Read back both modified files to confirm all original sections preserved and new sections correctly placed
- **Files Modified:**
  - .claude/skills/create-story-with-evals/templates/eval-assertions.md — added Edge Cases & Error Scenarios section with format template and guidance
  - .claude/skills/create-story-with-evals/workflow.md — added Steps 4b, 4c; updated Step 5 for edge cases + Task 0 insertion
  - homelab-playbook/_bmad-output/implementation-artifacts/0-6-add-edge-cases-and-task0-to-story-template.md — marked done with Dev Agent Record
- **Review Findings:**
  - No issues found. All four acceptance criteria satisfied: (1) edge cases section with three questions in template, (2) Task 0 convention in workflow, (3) zero BMAD files touched, (4) all original sections preserved in both files.
  - The workflow step numbering (4, 4b, 4c, 5, 6) maintains backward compatibility — no existing step numbers changed.
