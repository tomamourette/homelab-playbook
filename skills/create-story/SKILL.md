# Create Story

**Phase:** 4 — Implementation | **Agent:** Scrum Master (Bob) | **Model:** Gemini Pro (local) | **Cost:** $0
**Frequency:** Per user story

## When to Use

Create or refine a detailed user story for implementation. This adds implementation details beyond what create-epics-and-stories provides.

## Prerequisites

- Epic and high-level story should exist

## Execution

Handle locally on Gemini Pro.

1. Read the high-level story and the architecture document
2. Expand the story with implementation detail:
   - **Acceptance criteria:** Detailed, testable conditions
   - **Technical approach:** Specific files to create/modify, patterns to follow
   - **Dependencies:** Other stories or external services needed
   - **Test plan:** What tests to write (unit, integration, e2e)
   - **Definition of done:** Specific checklist
3. Write the detailed story to `docs/stories/story-NNN-name.md`

## Output

A detailed story file ready for dev-story (Claude CLI delegation). The more detail here, the better Claude CLI performs.
