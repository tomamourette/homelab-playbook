# Market Research

**Phase:** 1 — Analysis | **Agent:** Analyst (Mary) | **Model:** Gemini Pro (local) | **Cost:** $0

## When to Use

Research existing solutions, alternatives, and competitive landscape. For homelab context: what tools/projects already solve this problem?

## Execution

Handle locally on Gemini Pro. Use web search if available.

1. Research existing solutions for the problem described in the product brief
2. For each alternative found, document:
   - Name and URL
   - What it does well
   - What it lacks
   - Self-hosting feasibility
   - Community/maintenance status
3. Provide a recommendation: build vs adopt vs fork
4. Write findings to `docs/research/market-research.md`

## Output

A market research document comparing alternatives. Helps inform the build-vs-buy decision before committing to architecture.
