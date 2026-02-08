# Retrospective

**Phase:** 4 — Implementation | **Agent:** Scrum Master (Bob) | **Model:** Gemini Pro (local) | **Cost:** $0
**Frequency:** Per epic

## When to Use

After completing a sprint/epic, reflect on what worked, what didn't, and what to improve.

## Prerequisites

- Sprint should be complete (all stories done or explicitly deferred)

## Execution

Handle locally on Gemini Pro.

1. Review the sprint:
   - Which stories were completed?
   - Were there any blockers or course corrections?
   - How did the architecture hold up during implementation?
   - Were estimates accurate?
2. Generate a retrospective covering:
   - **What went well:** Successes, smooth implementations
   - **What didn't go well:** Blockers, surprises, underestimates
   - **Lessons learned:** Patterns to repeat or avoid
   - **Action items:** Concrete improvements for next sprint
   - **Architecture feedback:** Any patterns that need updating in CLAUDE.md or architecture docs
3. Write to `docs/sprints/sprint-NNN-retro.md`

## Output

A retrospective document with actionable improvements. Update CLAUDE.md if there are new conventions to capture.
