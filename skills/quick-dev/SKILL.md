# Quick Dev

Delegate quick development tasks to Claude CLI (Opus 4.6 via Max subscription).

## When to Use

For small, well-understood tasks that don't need the full BMAD ceremony. Bug fixes, small features, config changes, refactoring. This is the Quick Flow parallel track.

## Execution

Formulate the user's request as a clear, specific prompt and delegate:

```
exec command="claude -p 'TASK_DESCRIPTION' --output-format json --model opus --allowedTools 'Read,Write,Edit,Bash,Glob,Grep,WebSearch' --append-system-prompt 'Read CLAUDE.md for project conventions. This is a quick task — implement it directly, write tests if appropriate, and run them.' --max-turns 15" workdir="/root/.openclaw/workspace/homelab-playbook"
```

Replace `TASK_DESCRIPTION` with a clear, specific description of what the user wants. Include:
- What to change
- Which files are involved (if known)
- Any constraints or preferences

## Examples

**Bug fix:**
```
"Fix the Docker healthcheck in docker-compose.yml for the traefik service. It's returning unhealthy because the endpoint changed to /ping."
```

**Config change:**
```
"Add a new environment variable REDIS_URL to the docker-compose.yml for the api service. Default to redis://redis:6379/0."
```

**Small feature:**
```
"Add a backup script that dumps the PostgreSQL database and uploads to S3. Put it in scripts/backup-db.sh. Add a cron entry."
```

## Output

Report to the user:
- What was changed
- Files modified
- Test results (if tests were run)
- Session ID for follow-ups
