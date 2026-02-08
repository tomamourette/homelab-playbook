# Edit PRD

**Phase:** 2 — Planning | **Agent:** PM (John) | **Model:** Gemini Pro (local) | **Cost:** $0

## When to Use

Iterative refinement of the PRD based on validation feedback or user input.

## Prerequisites

- PRD must exist
- Usually triggered after validate-prd returns issues

## Execution

Handle locally on Gemini Pro.

1. Read the current PRD
2. Apply the user's requested changes or fix validation issues
3. Maintain document structure and numbering consistency
4. Update the "Last Updated" timestamp
5. After edits, suggest running validate-prd again

## Output

Updated PRD document. Suggest re-validation if changes were substantial.
