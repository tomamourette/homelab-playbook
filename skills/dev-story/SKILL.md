# Dev Story

Delegate story implementation to Claude CLI (Opus 4.6 via Max subscription).

## When to Use

When the user asks to implement a specific user story. This is a Phase 4 (Implementation) BMAD workflow — the core development step.

## Prerequisites

- Story file must exist (created by create-story workflow)
- Architecture document must exist
- Sprint should be active (sprint-planning done)

## Execution

1. Identify the story file the user wants to implement
2. Delegate to Claude CLI using exec:

```
exec command="claude -p 'Implement the user story at STORY_PATH. Read the story acceptance criteria carefully. Follow the architecture at docs/architecture.md. Write the implementation code, write tests, run them, and fix any failures. Commit when tests pass.' --output-format json --model opus --allowedTools 'Read,Write,Edit,Bash,Glob,Grep,WebSearch' --append-system-prompt 'You are a BMAD Developer (Amelia). Read CLAUDE.md for project conventions. Follow TDD where practical. Run tests after implementation. Create atomic commits with conventional commit messages.' --max-turns 30" workdir="/root/.openclaw/workspace/homelab-playbook"
```

3. Replace `STORY_PATH` with the actual path to the story file
4. Parse the JSON response
5. Store `session_id` — dev stories often need follow-ups
6. Report to the user:
   - What was implemented
   - Test results (pass/fail)
   - Files created/modified
   - Any issues or questions
   - The session ID for follow-ups

## Follow-ups

If the user wants changes or Claude has questions:

```
exec command="claude -p 'USER_FEEDBACK_HERE' --resume 'SESSION_ID' --output-format json --model opus --allowedTools 'Read,Write,Edit,Bash,Glob,Grep' --max-turns 20" workdir="/root/.openclaw/workspace/homelab-playbook"
```

## Output

Code changes are made directly in the workspace by Claude CLI. Report:
- Implementation summary
- Test results
- Files changed (with paths)
- Commits made
- Open questions or issues
