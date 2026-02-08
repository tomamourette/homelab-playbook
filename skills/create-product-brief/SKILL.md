# Create Product Brief

**Phase:** 1 — Analysis | **Agent:** Analyst (Mary) | **Model:** Gemini Pro (local) | **Cost:** $0

## When to Use

Starting point for a new feature or project. Captures the problem, target users, and high-level solution direction before committing to detailed planning.

## Execution

Handle this locally on the current model (Gemini Pro). No delegation needed.

1. Ask the user to describe the feature/project they want to build
2. Create a product brief document covering:
   - **Problem statement:** What pain point or need does this address?
   - **Target users:** Who benefits from this? (For homelab: yourself, household, etc.)
   - **Proposed solution:** High-level approach
   - **Success criteria:** How do we know this works?
   - **Scope boundaries:** What is explicitly NOT included?
   - **Risks & open questions:** What could go wrong? What needs research?
3. Write the brief to `docs/product-brief.md` (or a named variant)
4. Ask the user to review and confirm before moving to Phase 2

## Output

A product brief document in the workspace. Ask the user:
- Does this capture the problem correctly?
- Any scope changes?
- Ready to move to Phase 2 (PRD creation)?
