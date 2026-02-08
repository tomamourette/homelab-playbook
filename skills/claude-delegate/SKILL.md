# Claude CLI Delegation (Generic)

Generic skill for delegating any development task to Claude CLI (Opus 4.6 via Max subscription).

Use this skill when no specific BMAD workflow skill matches, but the task requires Claude CLI's capabilities (file editing, code generation, testing, debugging).

## When to Use

- User asks for something that requires code changes but isn't a specific BMAD workflow
- Complex debugging that needs codebase access
- Multi-file refactoring
- Research + implementation combined
- Any task where Claude CLI's built-in tools (file access, git, bash) are needed

## Execution

1. Analyze the user's request
2. Choose the appropriate tool whitelist:
   - **Read-only tasks** (review, analysis): `Read,Glob,Grep`
   - **Write tasks** (implementation, fixes): `Read,Write,Edit,Bash,Glob,Grep`
   - **Full access** (with web search, git): `Read,Write,Edit,Bash,Glob,Grep,WebSearch`
3. Choose max-turns based on complexity:
   - Simple (review, small fix): `--max-turns 10`
   - Medium (feature, refactor): `--max-turns 20`
   - Complex (multi-file, TDD cycle): `--max-turns 30`
4. Delegate to Claude CLI:

```
exec command="claude -p 'TASK_PROMPT' --output-format json --model opus --allowedTools 'TOOL_LIST' --append-system-prompt 'Read CLAUDE.md for project conventions.' --max-turns MAX_TURNS" workdir="/root/.openclaw/workspace/homelab-playbook"
```

5. Parse the JSON response:
   - `result`: text summary to report to user
   - `session_id`: store for follow-ups
   - `is_error`: check for failures
   - `num_turns`: how many turns it took
6. Report the result summary to the user
7. For follow-ups, use `--resume SESSION_ID`

## Session Management

- Store every `session_id` returned — users often want to continue
- For follow-ups: `--resume SESSION_ID` continues the conversation
- For branching: `--resume SESSION_ID --fork-session` creates a new branch without modifying the original
- Session history persists in `~/.claude/projects/` — Claude CLI remembers past context

## Error Handling

- If `is_error: true` with subtype `error_max_turns`: the task needs more turns, resume with a higher limit
- If `is_error: true` with subtype `error_during_execution`: report the error, ask user how to proceed
- If exec times out (>1800s): the task is too large, break it down
