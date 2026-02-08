# QA Automation

**Phase:** 4 — Implementation | **Agent:** QA (Quinn) | **Model:** `/model quality` (Groq) | **Cost:** ~$0.01-0.03
**Frequency:** Per user story

## When to Use

Generate test cases and automation scripts after a story is implemented. Validates the implementation against acceptance criteria.

## Execution

Handle locally. Switch to `/model quality` (Groq) — pattern-based test generation doesn't need expensive models.

1. Read the story file (acceptance criteria) and the implementation (code changes)
2. Generate:
   - **Test cases:** Based on acceptance criteria
   - **Edge cases:** Boundary conditions, error scenarios
   - **Integration tests:** If the story involves multiple components
   - **Smoke tests:** Quick validation that the basic flow works
3. Write test files alongside the implementation
4. Report what tests were generated and suggest running them

## Note

If test generation requires reading/writing code files, consider delegating to Claude CLI via the claude-delegate skill instead — it has native file access.

## Output

Test files written to the workspace. Suggest running `make test` or the project's test command.
