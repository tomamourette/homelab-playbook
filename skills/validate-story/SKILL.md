# Validate Story

**Phase:** 4 — Implementation | **Agent:** Scrum Master (Bob) | **Model:** `/model quality` (Groq) | **Cost:** ~$0.01
**Frequency:** Per user story

## When to Use

Quick validation of a story before sending it to dev-story. Catches gaps in acceptance criteria or technical approach.

## Execution

Handle locally. Switch to `/model quality` (Groq) for a second perspective.

1. Read the story file
2. Validate:
   - Are acceptance criteria specific and testable?
   - Does the technical approach align with the architecture?
   - Are dependencies identified?
   - Is the scope reasonable for a single story?
   - Is the test plan adequate?
3. Report: READY (proceed to dev-story) or NEEDS WORK (with specific issues)

## Output

A quick READY/NEEDS WORK verdict. If NEEDS WORK, list the specific issues to fix before implementing.
