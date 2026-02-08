# Party Mode (Multi-Agent Discussion)

**Core Utility** | **Model:** Gemini Pro (local) | **Cost:** $0

## When to Use

Simulate a multi-agent discussion where different BMAD personas debate a topic. Useful for exploring trade-offs from different perspectives.

## Execution

Handle locally on Gemini Pro.

1. Identify the topic from the user
2. Simulate perspectives from multiple BMAD agents:
   - **Architect (Winston):** Technical feasibility, system design
   - **PM (John):** User needs, requirements, scope
   - **Developer (Amelia):** Implementation complexity, tech debt
   - **QA (Quinn):** Testability, edge cases, reliability
   - **Scrum Master (Bob):** Timeline, dependencies, risk
3. Each perspective should challenge the others
4. Synthesize into a recommendation

## Output

A structured discussion with multiple viewpoints and a synthesized recommendation. Helps surface issues that a single perspective might miss.
