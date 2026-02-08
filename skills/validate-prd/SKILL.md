# Validate PRD

**Phase:** 2 — Planning | **Agent:** PM (John) | **Model:** Gemini Pro or `/model quality` | **Cost:** $0-0.03

## When to Use

Adversarial review of the PRD to catch gaps, contradictions, and missing requirements before architecture begins.

## Prerequisites

- PRD must exist

## Execution

Handle locally. Use Gemini Pro (free) or switch to `/model quality` (Groq) for a second-opinion perspective.

1. Read the PRD at `docs/prd.md`
2. Validate against these criteria:
   - **Completeness:** Are all functional requirements testable? Any vague language?
   - **Consistency:** Do requirements contradict each other?
   - **Feasibility:** Can this be built with the homelab stack?
   - **Scope:** Is scope realistic for a solo developer?
   - **Dependencies:** Are all external dependencies identified?
   - **Acceptance criteria:** Are they specific and measurable?
3. Report findings as: PASS (ready for Phase 3) or NEEDS REVISION (with specific issues)

## Output

A validation verdict with specific issues to fix. If PASS, proceed to Phase 3.
