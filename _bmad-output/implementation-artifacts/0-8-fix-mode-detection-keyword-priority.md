# Story 0.8: Fix Mode Detection Keyword Priority in update-project-docs

Status: done

## Story

As a developer,
I want the `/update-project-docs` skill to have explicit keyword priority when multiple mode keywords appear in the user's input,
so that ambiguous commands produce predictable results instead of undefined behavior.

## Context (from Epic 0 Retrospective)

This addresses Pattern 2: mode detection keyword ambiguity was deferred 3 times across stories 0.3 (W3), 0.4 (W3), and 0.5 (W1). Per the new Two-Strike Deferral rule, this must be resolved.

## Acceptance Criteria

1. **Given** a user input containing multiple mode keywords (e.g., "check and update my docs")
   **When** the skill detects the mode
   **Then** it applies explicit priority: `check` > `full` > `update` (default)

2. **Given** a user input with no mode keyword
   **When** the skill detects the mode
   **Then** it defaults to `update` mode (existing behavior preserved)

3. **Given** a user input with exactly one mode keyword
   **When** the skill detects the mode
   **Then** it selects that mode (existing behavior preserved)

4. **Given** the BMAD installation at `.claude/skills/bmad-*/`
   **When** this story is implemented
   **Then** zero files in `.claude/skills/bmad-*/` are modified (NFR-INT-5)

## Eval Assertions

<!-- Binary test assertions derived from acceptance criteria. Used by /autoresearch:fix for post-code-review iteration loops. -->

| # | Assertion | Command/Check | Pass Criteria |
|---|-----------|---------------|---------------|
| AC-1 | Priority order implemented | Read workflow.md mode detection section | Contains explicit priority logic: check > full > update |
| AC-2 | Default preserved | Read workflow.md | Default mode is still `update` when no keyword matches |
| AC-3 | Single keyword works | Read workflow.md | Single keyword detection logic unchanged |
| AC-4 | No BMAD files modified | `git diff .claude/skills/bmad-*/` | Empty output |

## Edge Cases & Error Scenarios

1. **Side effects:** Modifies mode detection logic in workflow.md — affects which mode is selected
2. **Dependency failure:** N/A — self-contained change
3. **Assumptions:** Current mode detection uses keyword matching that can match multiple keywords simultaneously; priority logic can be inserted before the routing step

## Tasks / Subtasks

- [x] Task 0: Verify `/update-project-docs` skill files exist and are unchanged from Story 0.5
- [x] Task 1: Read current workflow.md mode detection logic
- [x] Task 2: Add explicit priority order: check keywords checked first, then full, then update as default
- [x] Task 3: Verify default behavior (no keyword → update) is preserved
- [x] Task 4: Verify BMAD update-safety (`git diff .claude/skills/bmad-*/`)

## Dev Notes

### What This Story Modifies

- `.claude/skills/bmad-update-project-docs/workflow.md` — mode detection section only

### Source

- Epic 0 Retrospective (2026-04-04): Pattern 2 (repeated deferrals), Deferred Debt D1
- Three-time deferral: Story 0.3 W3, Story 0.4 W3, Story 0.5 W1

### Previous Story Learnings (Story 0.5)

- workflow.md routes to instructions.md with mode parameter
- Mode detection currently uses keyword matching without priority
- Priority should be: check (read-only, safest) > full (explicit request) > update (default, most common)

## Dev Agent Record

- **Agent Model Used:** claude-opus-4-6 (Opus 4.6, 1M context)
- **Completion Notes:**
  - Read existing workflow.md (67 lines) and confirmed flat bullet-list mode detection with no priority logic
  - Replaced the MODE DETECTION section with explicit priority-ordered if/else-if/else structure: check (Priority 1) > full (Priority 2) > update (Priority 3, default)
  - All same keywords preserved: check/health/status/"are my docs current" for check; full/regenerate/rescan for full; default fallback for update
  - Added explanatory sentence clarifying ambiguous-input behavior (e.g., "check and update my docs" resolves to check)
  - EXECUTION section (routing to instructions.md with mode parameter) left completely unchanged
  - INITIALIZATION section left completely unchanged
  - Verified BMAD safety: all `.claude/skills/bmad-*/` directories have unchanged timestamps (Mar 30 20:41); only `bmad-update-project-docs` modified (Apr 4 19:19)
- **File List:**
  - `/home/developer/workspace/homelab/.claude/skills/bmad-update-project-docs/workflow.md` (modified)
- **Review Findings:**
  - No issues found. The change is minimal and surgical -- only the MODE DETECTION section was rewritten. All keywords, all mode names, all routing logic, and the default behavior are preserved. The only semantic change is that when multiple keywords appear simultaneously, check now wins over full, and full wins over update, instead of undefined behavior.
