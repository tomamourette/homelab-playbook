# Sprint Planning

**Phase:** 4 — Implementation | **Agent:** Scrum Master (Bob) | **Model:** Gemini Pro (local) | **Cost:** $0
**Frequency:** Per epic

## When to Use

Plan a sprint by selecting stories from an epic and ordering them for implementation.

## Prerequisites

- Epics and stories must exist (Phase 3 output)
- Implementation readiness should be PASS

## Execution

Handle locally on Gemini Pro.

1. Read the epic and its stories
2. Assess story dependencies — which must come first?
3. Create a sprint plan:
   - **Sprint goal:** What this sprint delivers
   - **Selected stories:** Ordered by dependency and priority
   - **Blocked stories:** Stories that can't start yet and why
   - **Definition of done:** What "sprint complete" means
4. Write the sprint plan to `docs/sprints/sprint-NNN.md`

## Output

A sprint plan document with ordered stories. Implementation proceeds story-by-story using dev-story skill.
