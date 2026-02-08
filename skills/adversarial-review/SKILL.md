# Adversarial Review (General)

**Core Utility** | **Model:** `/model reason` (DeepSeek R1) | **Cost:** ~$0.02-0.05

## When to Use

Devil's advocate review of any document or decision. Actively tries to find problems, weaknesses, and flawed assumptions.

## Execution

Handle locally. Switch to `/model reason` (DeepSeek R1) for deeper reasoning.

1. Read the document or decision the user wants reviewed
2. Adopt an adversarial stance — assume something is wrong and find it:
   - **Assumptions:** What's taken for granted that might not hold?
   - **Edge cases:** What scenarios break this?
   - **Security:** What attack vectors exist?
   - **Scale:** Does this work at 2x, 10x the expected load?
   - **Dependencies:** What single points of failure exist?
   - **Alternatives:** Is there a simpler or better approach?
3. Categorize findings:
   - **CRITICAL:** Must address before proceeding
   - **WARNING:** Should address, but not blocking
   - **INFO:** Worth considering, low risk

## Output

An adversarial review with categorized findings. This is intentionally harsh — better to find problems here than in production.
