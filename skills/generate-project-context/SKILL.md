# Generate Project Context

**Context Management** | **Agent:** Analyst (Mary) | **Model:** Gemini Pro (local) | **Cost:** $0

## When to Use

Generate a context document that can be used to prime new BMAD sessions. Captures the current state of the project for efficient context loading.

## Execution

Handle locally on Gemini Pro.

1. Gather project context:
   - Current architecture and design decisions
   - Active sprint and story status
   - Known issues and technical debt
   - Recent changes and their rationale
   - Key patterns and conventions
2. Compile into a context document at `docs/project-context.md`
3. This document can be referenced by `--append-system-prompt` in Claude CLI delegations

## Output

A context document that helps any BMAD session (or Claude CLI delegation) start with full project awareness.
