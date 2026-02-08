# Check Implementation Readiness

Delegate implementation readiness review to Claude CLI (Opus 4.6 via Max subscription).

## When to Use

When the user wants to validate that the architecture, PRD, and stories are aligned and ready for implementation. This is a Phase 3 (Solutioning) BMAD workflow — the gate before Phase 4.

## Prerequisites

- Architecture document must exist
- PRD must exist
- Epics and stories should exist

## Execution

1. Identify the architecture doc, PRD, and stories in the workspace
2. Delegate to Claude CLI using exec:

```
exec command="claude -p 'Perform an implementation readiness check. Review: 1) The architecture doc for completeness and feasibility. 2) The PRD for clarity of requirements. 3) The stories for alignment with architecture. 4) Identify any gaps, contradictions, or missing decisions that would block implementation. Be adversarial — find problems before they become bugs.' --output-format json --model opus --allowedTools 'Read,Glob,Grep' --append-system-prompt 'You are a BMAD Architect (Winston) performing adversarial review. Read CLAUDE.md for project conventions. This is a READ-ONLY review — do not modify any files. Output a structured readiness report with: PASS/FAIL verdict, issues found, recommended fixes.' --max-turns 10" workdir="/root/.openclaw/workspace/homelab-playbook"
```

3. Parse the JSON response
4. Report the readiness verdict (PASS/FAIL) and any issues to the user
5. If FAIL: list the issues that need fixing before implementation can start
6. Store `session_id` for follow-up discussion

## Output

Report to the user:
- PASS or FAIL verdict
- List of issues found (if any)
- Recommended fixes
- Whether to proceed to Phase 4 or fix issues first
