# Editorial Review (Prose)

**Core Utility** | **Model:** Gemini Pro (local) | **Cost:** $0

## When to Use

Review a document for prose quality — clarity, conciseness, tone, grammar.

## Execution

Handle locally on Gemini Pro.

1. Read the document the user specifies
2. Review for:
   - **Clarity:** Is the meaning unambiguous?
   - **Conciseness:** Can anything be cut without losing meaning?
   - **Tone:** Is it appropriate for the audience (technical docs, README, etc.)?
   - **Grammar/spelling:** Any errors?
   - **Structure:** Does the document flow logically?
3. Provide specific suggestions with line references

## Output

A list of editorial suggestions. Apply them if the user approves.
