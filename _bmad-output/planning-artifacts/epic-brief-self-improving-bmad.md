# Epic Brief: Self-Improving BMAD Workflow

**Status:** Exploratory — not yet scheduled
**Source:** Technical research (2026-04-04)
**Research doc:** `research/technical-autoresearch-bmad-integration-2026-04-04.md`

## Vision

Use accumulated session data (code review findings, deferred work patterns, dev agent confusion signals) to improve the BMAD skills themselves — create-story, dev-story, code-review, and others — through autonomous iteration.

## Two Tracks

### Track A: Code Quality Loop (Near-Ready)

Decouple "finding" from "fixing" in the code-review workflow. Code-review writes findings to the story file; `/autoresearch:fix` reads them and auto-resolves patch findings autonomously.

**Gaps to close:**
- G1: eval-runner script (run all eval assertions from a story file, output N/M passed)
- G2: review-to-fix-queue parser (parse `[Review][Patch]` lines into autoresearch:fix format)
- G3: story path resolver (auto-detect current story from sprint-status.yaml)
- G4: guard command per story type (homelab has no npm test — needs story-type-aware guards)
- G5: post-fix story update (auto-mark review findings [x] after resolution)

### Track B: Skill Evolution (Research Project)

Use `/autoresearch:reason` (adversarial debate) to propose improvements to BMAD skill files based on cross-story metrics. Requires substantial eval infrastructure.

**Gaps to close:**
- G6: cross-story metrics collector
- G7: skill snapshot + rollback mechanism
- G8: human approval gate for skill changes
- G9: baseline metric storage
- G10: prompt eval infrastructure (the big one — essentially an LLM eval framework)

## Suggested Sequencing

1. **Immediate (within current epics):** Build G1 + G2 as a small story. Enables Track A.
2. **Near-term epic:** Build G3-G5 to close the full code-review → autoresearch:fix loop.
3. **Future epic:** Build G6-G10 for Track B. G10 is a research project in itself.

## Evidence from Current Work

- Story 0-4 code review: 3 decisions + 6 patches applied manually. Autoresearch:fix would have handled the 6 patches autonomously.
- Story 0-5 code review: 1 decision + 5 patches applied manually. Same.
- Deferred work shows recurring patterns (W1: date fallback, W3: mode detection ambiguity) across both stories — exactly the signal Track B would detect and act on.

## Built: `/code-review-ab` Wrapper Skill (2026-04-04)

A wrapper skill has been created at `.claude/skills/code-review-ab/` that:
- Wraps `/bmad-code-review` without modifying any `bmad-*` files (safe from BMAD updates)
- Adds option 4 ("Compare fixes A/B") to the fix-handling step
- Checks git availability — falls back to inline fix if files aren't in a repo
- Runs both inline fix and autoresearch:fix sequentially on the same findings
- LLM auto-selects the winner based on weighted scoring (fix rate 40%, evals 30%, guard 20%, blocked 10%)
- Logs detailed comparison to `{implementation_artifacts}/fix-approach-log.tsv`
- After 10+ comparisons, the log enables data-driven decision on which approach to default to

**Files:**
- `.claude/skills/code-review-ab/SKILL.md` — trigger definitions
- `.claude/skills/code-review-ab/workflow.md` — wrapper logic
- `.claude/skills/code-review-ab/fix-compare.md` — A/B comparison, scoring, logging

**Usage:** Run `/code-review-ab` instead of `/bmad-code-review`. All standard code review behavior is identical — only the fix step adds option 4.

**Limitation:** Option 4 only works on files in git repositories. Non-git files fall back to inline fix automatically.

## Proposed: Smart Full-Mode Doc Regeneration with Diff-Merge

**Problem:** The current full mode (`/update-project-docs full`) delegates to `bmad-document-project`, which regenerates all docs from scratch, overwriting everything. This loses manual edits, custom sections, and human-added context.

**Proposed approach:** Regenerate to a staging folder, diff against existing docs, validate each difference, then merge.

1. Generate fresh docs to `{project_knowledge}/.staging/`
2. For each doc file, diff `.staging/doc.md` vs existing `doc.md`
3. Classify each diff hunk:
   - New content in staging → valid addition (source code changed) → merge in
   - Content missing from staging → could be stale OR could be manual addition → flag for review
   - Content differs → regeneration updated it → validate against source files
4. Auto-merge clear cases, flag ambiguous cases in a merge report
5. Write final docs, remove staging folder
6. Log what was merged, what was flagged, what was preserved

**Why it fits here:** The doc-section-mapping infrastructure from Epic 0 stories 0-3/0-4/0-5 already maps source files to doc sections. The diff validation logic can use this mapping to determine whether a missing section is "removed because source was deleted" vs. "manually added by a human."

**Prerequisite: The `docs/` folder is NOT yet a git repository.** This needs to be set up first — either as a standalone repo (`git init` in docs/) or as a git submodule of the parent project. This is a prerequisite task for this story.

**Preferred approach: Git on docs folder.** If the docs folder is a git repo (or submodule), the staging folder is unnecessary — git IS the diff/merge tool. The flow becomes: full regen overwrites docs → `git diff` shows changes → LLM reviews each hunk against the mapping (source changed → keep new, manual addition removed → restore, stale removed → keep deletion) → `git commit` the merged state. This also enables check/update modes to track doc-level changes independently.

**Fallback: Staging folder.** For non-git projects, generate to `{project_knowledge}/.staging/`, diff against existing, validate, merge, cleanup.

**Implementation:** Would be a wrapper around the full mode delegation in `instructions.md`, similar to how `code-review-ab` wraps `bmad-code-review`. Does not modify `bmad-document-project` itself.

## Proposed: BMAD Wrapper Skills for Versioned Planning Artifacts

**Idea:** Create wrapper skills around `/bmad-create-prd` and `/bmad-create-architecture` that:
- Output files with a shortened version suffix (e.g., `prd-v2.md`, `architecture-v3.md`) rather than overwriting the original
- This allows tracking how the PRD and architecture evolve across epics
- The `/update-project-docs` context sources already point to `prd.md` and `architecture.md` — versioned files would need the config to point to the latest version, or use a symlink/alias pattern

**Why:** Currently, PRD and architecture files get overwritten when re-run. Versioning them enables:
- Comparing what changed between planning iterations
- Using older versions as context for understanding design evolution
- Rollback if a planning change proves wrong

**Implementation:** Same wrapper pattern as `create-story-with-evals` and `code-review-ab` — wraps the BMAD skill without modifying it.

## Key Constraint

**Skill evolution requires a mandatory human approval gate.** Unlike code fixes (which are verified by tests), skill changes affect all future sessions. The autoresearch pattern's "keep/discard" decision must be replaced with "propose to human / human accepts or rejects."
