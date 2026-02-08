# Create PRD

**Phase:** 2 — Planning | **Agent:** PM (John) | **Model:** Gemini Pro (local) | **Cost:** $0

## When to Use

Create a Product Requirements Document from the product brief. This is the central planning artifact that drives architecture and stories.

## Prerequisites

- Product brief should exist (Phase 1 output)

## Execution

Handle locally on Gemini Pro.

1. Read the product brief at `docs/product-brief.md` (or user-specified path)
2. Create a PRD covering:
   - **Overview:** What we're building and why
   - **User personas:** Who uses this (even if just yourself)
   - **Functional requirements:** What it must do (numbered, testable)
   - **Non-functional requirements:** Performance, security, reliability targets
   - **Technical constraints:** Must work with existing stack (Docker, Terraform, etc.)
   - **Out of scope:** Explicitly excluded features
   - **Dependencies:** External services, APIs, hardware requirements
   - **Acceptance criteria:** How we know the feature is done
3. Write the PRD to `docs/prd.md` (or a named variant)
4. Ask the user to review before proceeding to Phase 3

## Output

A structured PRD document. This feeds directly into architecture (Phase 3) and story creation.
