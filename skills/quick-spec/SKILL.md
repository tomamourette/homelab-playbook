# Quick Spec

**Quick Flow** | **Agent:** Solo Dev (Barry) | **Model:** Gemini Pro or `/model quality` | **Cost:** $0-0.02

## When to Use

Fast, lightweight spec for small tasks that don't need full BMAD ceremony. Skip phases 1-3 and go straight to a quick spec + quick dev.

## Execution

Handle locally on Gemini Pro. Escalate to `/model quality` if more complex than expected.

1. Discuss the task with the user conversationally
2. Create a lightweight spec:
   - **What:** One-sentence description
   - **Why:** What problem it solves
   - **How:** Brief technical approach
   - **Acceptance criteria:** 2-5 testable conditions
   - **Files affected:** List of files to create/modify
3. Confirm with user before proceeding to quick-dev

## Output

A lightweight spec — just enough to guide implementation. If the task turns out to be bigger than expected, suggest switching to the full BMAD flow.
