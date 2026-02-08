# Create Architecture

Delegate architecture creation to Claude CLI (Opus 4.6 via Max subscription).

## When to Use

When the user asks to create, design, or draft an architecture document for a feature or system component. This is a Phase 3 (Solutioning) BMAD workflow.

## Prerequisites

- PRD must exist (Phase 2 output)
- Epics & stories should ideally exist, but architecture can come first for novel work

## Execution

1. Identify the relevant PRD and any existing architecture docs in the workspace
2. Delegate to Claude CLI using exec:

```
exec command="claude -p 'Create an architecture document for the feature described in the PRD. Read the PRD at docs/prd.md (or the path the user specifies). Follow BMAD methodology: identify components, data flow, technology choices, deployment strategy, and security considerations. Ask clarifying questions at the end if anything is ambiguous.' --output-format json --model opus --allowedTools 'Read,Write,Edit,Bash,Glob,Grep,WebSearch' --append-system-prompt 'You are a BMAD Architect (Winston). Read CLAUDE.md for project conventions. Create the architecture document in docs/architecture.md. Be thorough but practical for a homelab context.' --max-turns 15" workdir="/root/.openclaw/workspace/homelab-playbook"
```

3. Parse the JSON response
4. If `is_error` is true, report the error to the user
5. Store `session_id` for follow-up questions (use `--resume`)
6. Report the architecture summary and any questions Claude asked to the user
7. If the user answers questions, resume the session:

```
exec command="claude -p 'USER_ANSWERS_HERE' --resume 'SESSION_ID' --output-format json --model opus --allowedTools 'Read,Write,Edit,Bash,Glob,Grep' --max-turns 10" workdir="/root/.openclaw/workspace/homelab-playbook"
```

## Output

The architecture document will be written to the workspace by Claude CLI. Report to the user:
- Summary of the architecture decisions
- File path where the doc was written
- Any open questions from Claude
- The session ID for follow-ups
