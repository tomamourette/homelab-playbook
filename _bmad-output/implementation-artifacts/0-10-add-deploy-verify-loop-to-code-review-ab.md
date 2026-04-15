# Story 0.10: Add Deploy-and-Verify Loop to code-review-ab

Status: done

## Story

As a developer,
I want the `/code-review-ab` skill to include a deploy-and-verify step after fix comparison that runs the story's eval assertions against the real target, and loops with autoresearch:fix until all assertions pass,
so that no story is marked done until the implementation is verified end-to-end on the actual infrastructure.

## Acceptance Criteria

1. **Given** the code-review-ab skill completes its review and fix phases
   **When** there are eval assertions in the story file
   **Then** a new "Deploy and Verify" step runs after fixes are applied
   **And** it prompts the user for the deployment command (e.g., `ansible-playbook ...`, `npm test`, etc.)

2. **Given** the deployment command completes
   **When** eval assertions are run on the target
   **Then** each assertion result is displayed as PASS or FAIL with the command output

3. **Given** one or more eval assertions fail after deployment
   **When** the user confirms to iterate
   **Then** autoresearch:fix runs targeting the failing assertions
   **And** after fixes, the deployment and verification loop repeats
   **And** the loop continues until all assertions pass or max iterations (default 3) reached

4. **Given** all eval assertions pass
   **When** the loop exits
   **Then** the story status is updated to done
   **And** sprint-status.yaml is updated

5. **Given** the user cannot deploy (no infrastructure access)
   **When** prompted for the deployment command
   **Then** they can skip with "skip" — the skill falls back to the current behavior (mark done without deployment verification)
   **And** a note is added to the story: "Deployment verification skipped — manual testing required"

6. **Given** the BMAD installation at `.claude/skills/bmad-*/`
   **When** this story is implemented
   **Then** zero files in `.claude/skills/bmad-*/` are modified (NFR-INT-5)

## Eval Assertions

<!-- Binary test assertions derived from acceptance criteria. Used by /autoresearch:fix for post-code-review iteration loops. -->

| # | Assertion | Command/Check | Pass Criteria |
|---|-----------|---------------|---------------|
| AC-1 | Deploy-verify step exists in workflow | Read workflow.md Step 3 section | Contains "Deploy and Verify" step referencing deploy-verify.md |
| AC-2 | deploy-verify.md protocol file exists | Read deploy-verify.md | Contains deployment prompt, assertion runner, fix loop, and skip path |
| AC-3 | Fix loop is bounded | Read deploy-verify.md loop section | max_iterations = 3, loop exits when limit reached |
| AC-4 | Skip path preserves existing behavior | Read deploy-verify.md skip section | "skip" triggers note addition and falls through to normal completion |
| AC-5 | Eval assertion parsing documented | Read deploy-verify.md | Instructions to parse `## Eval Assertions` table from story file |
| AC-6 | No BMAD files modified | `git diff .claude/skills/bmad-*/` | Empty output |

## Edge Cases & Error Scenarios

1. **No eval assertions in story file:** Step 3 is skipped entirely — existing behavior preserved
2. **Deployment command fails (non-zero exit):** Display error output, ask user to fix command or skip — do NOT run assertions against a failed deploy
3. **Assertion command fails to execute (not PASS/FAIL, but error):** Mark as FAIL with error output, include in failing set
4. **All assertions pass on first try:** No fix loop needed — proceed directly to mark done
5. **Max iterations exhausted with remaining failures:** Log remaining failures as known issues in story, still mark done but with caveat note
6. **User declines autoresearch:fix mid-loop:** Break loop, log remaining failures, proceed to completion
7. **Story file has Eval Assertions table but no Command/Check column entries:** Treat as no assertions — skip deploy-verify

## Tasks / Subtasks

- [x] Task 0: Verify code-review-ab skill files exist and current workflow works
- [x] Task 1: Read current workflow.md and fix-compare.md to understand integration points
- [x] Task 2: Create deploy-verify.md protocol file with full deploy-and-verify logic
  - [x] 2a: Eval assertion parser (reads story file, extracts assertion table)
  - [x] 2b: Deployment command prompt (user-provided, with skip option)
  - [x] 2c: Assertion runner (executes each check, displays PASS/FAIL)
  - [x] 2d: Fix loop (autoresearch:fix on failures, re-deploy, re-verify, max 3 iterations)
  - [x] 2e: Skip path (adds note, falls through to normal completion)
  - [x] 2f: Completion handler (updates story with verification results)
- [x] Task 3: Modify workflow.md to add Step 3 referencing deploy-verify.md
- [x] Task 4: Verify skip path preserves all existing behavior
- [x] Task 5: Verify BMAD update-safety (`git diff .claude/skills/bmad-*/`)

## Dev Notes

### What This Story Modifies

- `.claude/skills/code-review-ab/workflow.md` — adds Step 3 (Deploy and Verify) after Step 2
- `.claude/skills/code-review-ab/deploy-verify.md` — new file, detailed deploy-and-verify protocol

### What This Story Does NOT Modify

- `.claude/skills/bmad-*/` — zero BMAD skill files touched (NFR-INT-5)
- `.claude/skills/code-review-ab/SKILL.md` — no changes to skill metadata
- `.claude/skills/code-review-ab/fix-compare.md` — no changes to A/B comparison logic

### Design Decisions

- **User-provided deployment command:** Keeps the skill infrastructure-agnostic (works for Ansible, npm, Terraform, etc.)
- **"skip" option:** Preserves backward compatibility — no forced deployment
- **Max 3 iterations:** Prevents infinite loops; matches autoresearch:fix's own bounded iteration philosophy
- **Re-deploy AND re-verify each iteration:** Ensures fixes actually work on the target, not just locally
- **Eval assertions as pass/fail criteria:** Same assertions used by autoresearch:fix — single source of truth

### Source

- Epic 0 planning: autoresearch integration — code quality loop (near-ready track)
- Story 0.7 (two-strike deferral) and 0.8/0.9 patterns inform the non-destructive extension approach

## Dev Agent Record

**Agent Model Used:** claude-opus-4-6 (Opus 4.6, 1M context)

### Completion Notes

- Read all three code-review-ab skill files before making changes
- Created deploy-verify.md as a standalone protocol (mirrors fix-compare.md pattern)
- Added Step 3 to workflow.md between Step 2 and the implicit completion
- Step 3 is a conditional — only fires when eval assertions exist in the story
- Skip path adds a note to the story and proceeds to normal completion
- Fix loop bounded at 3 iterations with user confirmation each round
- Deployment command failure (non-zero exit) handled separately from assertion failure

### File List

- `.claude/skills/code-review-ab/workflow.md` — added Step 3 (Deploy and Verify)
- `.claude/skills/code-review-ab/deploy-verify.md` — new file, deploy-and-verify protocol
- `homelab-playbook/_bmad-output/implementation-artifacts/0-10-add-deploy-verify-loop-to-code-review-ab.md` — story file created, status updated to done
- `homelab-playbook/_bmad-output/implementation-artifacts/sprint-status.yaml` — story status updated to done
