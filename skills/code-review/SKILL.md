# Code Review

Delegate code review to Claude CLI (Opus 4.6 via Max subscription).

## When to Use

When the user asks to review code changes, a PR, or a branch diff. This is a Phase 4 (Implementation) BMAD workflow.

## Execution

### Option A: Review a branch diff

```
exec command="bash -c 'cd /root/.openclaw/workspace/homelab-playbook && git diff main...BRANCH_NAME | claude -p \"Review this diff. Check for: 1) Code quality and best practices. 2) Security vulnerabilities. 3) Test coverage gaps. 4) Alignment with architecture docs. 5) IaC-specific issues (Terraform state, Ansible idempotency, Docker security).\" --output-format json --model opus --allowedTools \"Read,Glob,Grep,Bash(git log *),Bash(git show *)\" --append-system-prompt \"You are a BMAD Code Reviewer. Read CLAUDE.md for project conventions. Be thorough but constructive. Categorize findings as: CRITICAL (must fix), WARNING (should fix), INFO (suggestion).\" --max-turns 10'" workdir="/root/.openclaw/workspace/homelab-playbook"
```

### Option B: Review recent changes (no branch)

```
exec command="bash -c 'cd /root/.openclaw/workspace/homelab-playbook && git diff HEAD~3 | claude -p \"Review these recent changes.\" --output-format json --model opus --allowedTools \"Read,Glob,Grep,Bash(git log *),Bash(git show *)\" --append-system-prompt \"You are a BMAD Code Reviewer. Read CLAUDE.md. Be thorough but constructive.\" --max-turns 10'" workdir="/root/.openclaw/workspace/homelab-playbook"
```

### Option C: Review specific files

```
exec command="claude -p 'Review the following files for code quality, security, and alignment with architecture: FILE_PATHS' --output-format json --model opus --allowedTools 'Read,Glob,Grep' --append-system-prompt 'You are a BMAD Code Reviewer. Read CLAUDE.md. This is a READ-ONLY review.' --max-turns 10" workdir="/root/.openclaw/workspace/homelab-playbook"
```

## Output

Report to the user:
- Review verdict (APPROVE / REQUEST CHANGES)
- CRITICAL issues (must fix before merge)
- WARNING issues (should fix)
- INFO suggestions (nice to have)
- Overall code quality assessment
