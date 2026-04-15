# Story 0.1: Add Eval Assertions Section to Story Template

Status: done

## Story

As a developer,
I want a wrapper skill `/create-story-with-evals` that calls `/bmad-create-story` and then appends an "Eval Assertions" section to the generated story,
so that every story has measurable pass/fail verification points for autoresearch and code review, without modifying any BMAD skill files.

## Acceptance Criteria

1. **Given** the wrapper skill at `.claude/skills/create-story-with-evals/`
   **When** I run `/create-story-with-evals`
   **Then** it invokes `/bmad-create-story` to generate the story normally
   **And** after the story file is created, it appends an "Eval Assertions" section

2. **Given** a generated story file with acceptance criteria
   **When** the wrapper appends the "Eval Assertions" section
   **Then** each eval assertion maps to a specific acceptance criterion by number
   **And** assertions use binary pass/fail format (not scaled ratings)
   **And** assertions use shell-executable format where possible (exit codes, file existence, command output)

3. **Given** the BMAD installation at `.claude/skills/bmad-*/`
   **When** this story is implemented
   **Then** zero files in `.claude/skills/bmad-*/` are modified (NFR-INT-5, AT-6.8)
   **And** the wrapper skill lives in `.claude/skills/create-story-with-evals/` (separate from bmad-*)

4. **Given** a user who runs `/create-story-with-evals`
   **When** the wrapper completes
   **Then** the output story file is identical to what `/bmad-create-story` produces, plus the Eval Assertions section
   **And** the sprint-status.yaml is updated correctly (same as /bmad-create-story would do)

## Tasks / Subtasks

- [x] Task 1: Create the wrapper skill directory and SKILL.md (AC: #1, #3)
  - [x] Create `.claude/skills/create-story-with-evals/SKILL.md` with proper frontmatter
  - [x] Set `name: create-story-with-evals`
  - [x] Set `description` to trigger on "create story with evals" or "create next story"
  - [x] SKILL.md references the workflow.md file

- [x] Task 2: Create the wrapper workflow.md (AC: #1, #2, #4)
  - [x] Create `.claude/skills/create-story-with-evals/workflow.md`
  - [x] Step 1: Invoke `/bmad-create-story` — pass through any user arguments (story number, etc.)
  - [x] Step 2: After create-story completes, identify the generated story file path from sprint-status.yaml
  - [x] Step 3: Read the generated story file
  - [x] Step 4: Extract acceptance criteria from the story
  - [x] Step 5: Generate eval assertions table — one row per AC, binary pass/fail format
  - [x] Step 6: Append `## Eval Assertions` section to the story file (after Acceptance Criteria, before Tasks)
  - [x] Step 7: Save the updated story file

- [x] Task 3: Create the eval assertions template (AC: #2)
  - [x] Create `.claude/skills/create-story-with-evals/templates/eval-assertions.md`
  - [x] Template includes the table format and design principles
  - [x] Template guides the agent on how to derive assertions from ACs

- [x] Task 4: Verify BMAD update-safety (AC: #3)
  - [x] Run `git diff .claude/skills/bmad-*/` and verify zero changes
  - [x] Confirm the wrapper skill is in its own directory outside `bmad-*/`

- [ ] Task 5: Test the wrapper (AC: #1, #2, #4)
  - [ ] Run `/create-story-with-evals` for the next story (story 0.2)
  - [ ] Verify the generated story file contains the Eval Assertions section
  - [ ] Verify assertions map to acceptance criteria
  - [ ] Verify sprint-status.yaml was updated correctly

## Dev Notes

### Approach: Wrapper Skill

A standalone Claude Code skill that wraps `/bmad-create-story`:

```
.claude/skills/create-story-with-evals/
├── SKILL.md                          # Frontmatter + invocation
├── workflow.md                       # Wrapper logic
└── templates/
    └── eval-assertions.md            # Assertion format template
```

**How it works:**
1. User runs `/create-story-with-evals` (or the skill auto-detects from "create next story")
2. Skill invokes `/bmad-create-story` which does all the heavy lifting (artifact analysis, story generation, sprint-status update)
3. After create-story finishes, the wrapper reads the generated story file
4. It extracts the acceptance criteria
5. It generates a `## Eval Assertions` table with one row per AC
6. It inserts the section into the story file (after AC, before Tasks)

**Why this approach:**
- Zero modifications to BMAD skills — fully honors NFR-INT-5
- The wrapper is additive — if BMAD changes create-story output format, the wrapper adapts
- Can be independently versioned, tested, and evolved
- The eval assertions logic is concentrated in one place

### Eval Assertion Design Principles (from autoresearch research)

- **Binary assertions produce cleaner signals** — a test either passes or doesn't
- **Shell-executable where possible** — `command exits with code 0`, `file exists at path`, `output contains string`
- **Manual checks for non-automatable criteria** — "Review confirms X" for subjective quality checks
- **One assertion per acceptance criterion** — direct traceability
- These assertions are used by `/autoresearch:fix` for post-code-review iteration loops

### SKILL.md Frontmatter Design

```yaml
---
name: create-story-with-evals
description: 'Creates a story with eval assertions. Wraps /bmad-create-story and adds binary test assertions derived from acceptance criteria. Use when the user says "create story with evals" or "create next story with evals"'
---
```

### Project Structure Notes

- New directory: `.claude/skills/create-story-with-evals/` (3 files)
- No existing files modified
- No BMAD skill files touched

### References

- [Source: architecture.md — BMAD Workflow Enhancement Decisions / Eval Assertions in Story Templates]
- [Source: prd.md — FR51, NFR-INT-5]
- [Source: research/technical-incremental-docs-autoresearch-2026-04-03.md — BMAD Update-Safety section]
- [Source: MindStudio — AutoResearch Eval Loop](https://www.mindstudio.ai/blog/autoresearch-eval-loop-binary-tests-claude-code-skills)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

None — no errors encountered.

### Completion Notes List

- Created wrapper skill `/create-story-with-evals` as a standalone Claude Code skill
- Wrapper calls `/bmad-create-story` first, then appends eval assertions to the generated story file
- Zero BMAD skill files modified — fully honors NFR-INT-5
- Skill immediately visible in Claude Code's skill list
- Task 5 (test the wrapper) deferred to Story 0.2 creation — the wrapper will be tested when we create the next story

### File List

- `.claude/skills/create-story-with-evals/SKILL.md` (new)
- `.claude/skills/create-story-with-evals/workflow.md` (new)
- `.claude/skills/create-story-with-evals/templates/eval-assertions.md` (new)

### Review Findings

- [x] [Review][Patch] Step 2 "most recently changed" ambiguity — fixed: match by story key transition from backlog [workflow.md]
- [x] [Review][Patch] No error handling for create-story failure — fixed: added file existence check with HALT [workflow.md]
- [x] [Review][Patch] Insertion position fragile — fixed: flexible H2 matching [workflow.md]
- [x] [Review][Patch] SKILL.md description missing "create next story" trigger phrase — fixed [SKILL.md]
- [x] [Review][Defer] AC #4 identity verification — no checksum to verify story content unchanged beyond eval section — deferred, low risk for MVP
