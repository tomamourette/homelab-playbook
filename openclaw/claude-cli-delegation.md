# OpenClaw → Claude CLI Delegation Strategy

**Last Updated:** 2026-02-06
**Status:** Active Reference

## Purpose

Use OpenClaw as the supervisor/coordinator (cheap/free models) and delegate development work to Claude CLI, which has native access to optimized file tools, MCP servers, prompt caching, persistent memory, subagent spawning, and auto-compaction — capabilities that generic LLM API calls can't replicate.

---

## Why Delegate to Claude CLI?

| Capability | OpenClaw Direct API | Claude CLI |
|---|---|---|
| File tools (read, write, edit, glob, grep) | Must implement via `exec` | Built-in, optimized |
| Prompt caching | Manual (`cacheRetention` param) | Automatic, aggressive (90% savings on reads) |
| Context management | Manual pruning/compaction | Auto-compaction with memory flush |
| MCP servers | Requires adapter plugin | Native, 100+ servers, auto tool search |
| Web search | Via tool config | Built-in `WebSearch` tool |
| Subagent spawning | Via `subagents` config | Native `Task` tool with model routing |
| Session memory | `memorySearch` config | `CLAUDE.md` + persistent memory files |
| Git integration | Via `exec` tool | Native, understands repos |
| Turn control | No built-in limit | `--max-turns` flag (keeps sessions focused) |
| Structured output | Model-dependent | `--json-schema` enforcement |

**Bottom line:** Claude CLI is a full development environment. OpenClaw calling the Anthropic API directly gets you a chat response. Claude CLI gets you an agent that reads your code, edits files, runs tests, and commits — all in one invocation.

---

## Architecture

```
User (Telegram / Web)
  │
  ▼
OpenClaw Supervisor (Gemini Flash / Pro — free)
  │
  ├─ BMAD Planning (Phase 1-2): handled by OpenClaw on Gemini Pro
  ├─ Sprint management: handled by OpenClaw on Gemini Pro
  ├─ Heartbeats: handled by OpenClaw on Groq instant
  │
  ├─ Architecture (Phase 3): delegate to Claude CLI (Opus 4.6)
  ├─ Dev Story (Phase 4): delegate to Claude CLI (Opus 4.6)
  ├─ Code Review (Phase 4): delegate to Claude CLI (Opus 4.6)
  ├─ Quick Dev: delegate to Claude CLI (Opus 4.6)
  │
  ▼
Claude CLI (headless, -p mode)
  ├─ Reads CLAUDE.md for project conventions
  ├─ Uses built-in tools: Read, Write, Edit, Bash, Glob, Grep
  ├─ Connects to MCP servers (GitHub, databases, etc.)
  ├─ Spawns subagents for parallel work
  ├─ Auto-manages context window (compaction)
  ├─ Returns JSON result with cost tracking
  │
  ▼
OpenClaw Supervisor
  ├─ Parses result, stores session ID
  ├─ Reports summary to user via Telegram
  └─ Tracks cumulative cost
```

---

## Claude CLI Headless Mode — Key Flags

### Essential Flags for Automation

| Flag | Description | Example |
|---|---|---|
| `-p` | Non-interactive mode (required) | `claude -p "Fix the bug"` |
| `--output-format json` | Machine-readable output with cost/session data | `claude -p --output-format json "task"` |
| `--allowedTools` | Auto-approve tools (no prompting) | `--allowedTools "Read,Write,Edit,Bash,Glob,Grep"` |
| `--max-budget-usd` | Hard budget cap per invocation (API key billing only) | Not needed with Max subscription |
| `--max-turns` | Limit agentic turns | `--max-turns 20` |
| `--model` | Model selection | `--model opus` (default for Max subscription) |
| `--append-system-prompt` | Add to default prompt (preserves Claude Code behavior) | `--append-system-prompt "Follow BMAD methodology"` |
| `--resume` | Continue a previous session | `--resume "session-uuid"` |
| `--fork-session` | Branch from a session without modifying it | `--resume "id" --fork-session` |
| `--dangerously-skip-permissions` | Skip all tool approval prompts (use with caution) | See security section below |

**On `--dangerously-skip-permissions`:** This flag is required for fully autonomous execution — without it, Claude CLI hangs waiting for user approval on file edits and shell commands. However, it grants unrestricted filesystem and shell access. **Prefer `--allowedTools`** to whitelist specific tools instead, which provides autonomy with guardrails. Only use `--dangerously-skip-permissions` in sandboxed/containerized environments.

### JSON Output Structure

```json
{
  "type": "result",
  "subtype": "success",
  "session_id": "uuid",
  "result": "Claude's text response...",
  "is_error": false,
  "num_turns": 5,
  "duration_ms": 45000,
  "total_cost_usd": 0.42,
  "usage": {
    "input_tokens": 15000,
    "output_tokens": 3200,
    "cache_read_input_tokens": 12000
  }
}
```

Error subtypes: `error_max_turns`, `error_max_budget_usd`, `error_during_execution`.

### Piping Context

```bash
# Pipe file content
cat architecture.md | claude -p "Review this architecture"

# Pipe a git diff for review
git diff HEAD~3 | claude -p "Review these changes" --output-format json

# Pipe PR diff
gh pr diff 42 | claude -p --append-system-prompt "You are a security reviewer" --output-format json
```

---

## OpenClaw Exec Tool Configuration

### Required Config in `openclaw.json`

Add to `agents.defaults`:

```json5
"tools": {
  "exec": {
    "host": "gateway",         // Run on host (Claude CLI needs filesystem access)
    "timeoutSec": 1800,        // 30 min for long dev tasks
    "backgroundMs": 30000,     // Background after 30s (dev tasks take time)
    "notifyOnExit": true       // Notify when Claude CLI finishes
  },
  "elevated": {
    "enabled": true,
    "allowFrom": {
      "telegram": ["YOUR_TELEGRAM_USER_ID"]
    }
  }
}
```

### Coder Agent Config

Update the coder agent to explicitly allow exec:

```json5
{
  "id": "coder",
  "name": "Homelab Coder",
  "workspace": "/root/.openclaw/workspace",
  "model": { "primary": "google-gemini-cli/gemini-3-flash-preview" },
  "tools": {
    "profile": "coding",
    "alsoAllow": ["exec", "read", "write", "edit"]
  }
}
```

---

## Invocation Patterns

### Pattern 1: Simple Task Delegation

OpenClaw receives a task via Telegram, delegates to Claude CLI:

```bash
claude -p "Fix the authentication bug in src/auth.py. Run tests after." \
  --output-format json \
  --model opus \
  --allowedTools "Read,Write,Edit,Bash,Glob,Grep" \
  --append-system-prompt "Read CLAUDE.md for project conventions. Follow TDD." \
  --max-turns 20
```

### Pattern 2: BMAD Dev Story

```bash
claude -p "Implement the dev story in docs/stories/story-003-jwt-auth.md. \
Follow the architecture in docs/architecture.md. \
Write tests. Run them. Fix failures." \
  --output-format json \
  --model opus \
  --allowedTools "Read,Write,Edit,Bash,Glob,Grep,WebSearch" \
  --append-system-prompt "You are a BMAD Developer (Amelia). Follow the story acceptance criteria exactly." \
  --max-turns 30
```

### Pattern 3: Architecture Review (Read-Only)

```bash
claude -p "Review the architecture document at docs/architecture-jwt.md. \
Identify security concerns, scalability issues, and missing components. \
Check alignment with the PRD at docs/prd.md." \
  --output-format json \
  --model opus \
  --allowedTools "Read,Glob,Grep" \
  --append-system-prompt "You are a BMAD Architect (Winston). Be thorough but constructive." \
  --max-turns 10
```

### Pattern 4: Code Review

```bash
git diff main...feature-branch | claude -p \
  "Review this diff. Check for: code quality, security vulnerabilities, \
test coverage, alignment with architecture docs." \
  --output-format json \
  --model opus \
  --allowedTools "Read,Glob,Grep,Bash(git log *),Bash(git show *)" \
  --append-system-prompt "You are a BMAD Code Reviewer. Be thorough." \
  --max-turns 10
```

### Pattern 5: Session Continuity (Multi-Step)

```bash
# Step 1: Architecture session
ARCH_SESSION=$(claude -p "Analyze codebase and propose architecture for JWT auth" \
  --output-format json \
  --model opus \
  --allowedTools "Read,Glob,Grep" \
  --max-turns 15 | jq -r '.session_id')

# Step 2: Implementation (forked from arch context)
IMPL_SESSION=$(claude -p "Implement the JWT architecture from our discussion" \
  --resume "$ARCH_SESSION" --fork-session \
  --output-format json \
  --model opus \
  --allowedTools "Read,Write,Edit,Bash,Glob,Grep" \
  --max-turns 30 | jq -r '.session_id')

# Step 3: Review (forked, has full context)
claude -p "Review the implementation against the architecture" \
  --resume "$IMPL_SESSION" --fork-session \
  --output-format json \
  --model opus \
  --allowedTools "Read,Glob,Grep,Bash(git diff *)" \
  --max-turns 10
```

---

## BMAD Pipeline with Claude CLI Delegation

Updated model routing — Claude CLI replaces direct API calls for implementation:

```
Phase 1: Analysis        -> OpenClaw on Gemini Pro (free)
Phase 2: Planning        -> OpenClaw on Gemini Pro (free)
Phase 3: Architecture    -> Claude CLI (--model opus)  ← DELEGATED
Phase 3: Impl. Readiness -> Claude CLI (--model opus)  ← DELEGATED
Phase 4: Sprint Planning -> OpenClaw on Gemini Pro (free)
Phase 4: Create Story    -> OpenClaw on Gemini Pro (free)
Phase 4: Dev Story       -> Claude CLI (--model opus)  ← DELEGATED
Phase 4: Code Review     -> Claude CLI (--model opus)  ← DELEGATED
Phase 4: QA Automate     -> OpenClaw on Groq quality (cheap)
Phase 4: Retrospective   -> OpenClaw on Gemini Pro (free)
Quick Dev                -> Claude CLI (--model opus)  ← DELEGATED
```

### Advantages Over Direct API

1. **Claude CLI reads CLAUDE.md** automatically — project conventions, coding standards, and memory are loaded without stuffing them into every API request
2. **Auto-compaction** — long dev sessions don't blow up context costs
3. **Built-in tools** — no need to configure OpenClaw's exec for every file operation
4. **Session forking** — architecture context flows into implementation without re-sending
5. **Opus 4.6 everywhere** — Max subscription means the best model for every task, no cost tradeoffs

---

## Authentication — Subscription (OAuth)

Claude CLI uses your **Claude Max subscription** via OAuth — NOT API key billing. This is a hard requirement: Max provides Opus 4.6 access with higher rate limits, at a fixed monthly cost.

### How It Works

| Auth Method | How It Works | Cost | Used By |
|---|---|---|---|
| **OAuth (Max subscription)** | Claude Max, OAuth token in `~/.claude/credentials.json` | $100-200/mo (Max) | Claude CLI (Opus 4.6) |
| API Key (`ANTHROPIC_API_KEY`) | Pay-per-token via Anthropic Console | Variable | OpenClaw (not used for Claude CLI) |

**Key distinction:** OpenClaw uses free/cheap models (Gemini, Groq) for supervision. Claude CLI uses the Max subscription for all development work on Opus 4.6. These are separate billing paths — OpenClaw never touches the Anthropic subscription, and Claude CLI never uses the API key.

### OAuth Token Handoff (Headless Environments)

OAuth requires a browser for initial login. In headless environments (WSL2, VPS, Docker), use a "token handoff":

1. **Local authentication:** Run `claude login` on a machine with a browser
2. **Token extraction:** Credentials are stored in `~/.claude/credentials.json`
3. **Transfer:** Copy `~/.claude/` to the headless environment (or mount as Docker volume)
4. **Verification:** Claude CLI finds the existing credentials and authenticates without a browser

```bash
# On local machine (has browser)
claude login

# Copy to headless server
scp -r ~/.claude/ user@server:~/.claude/

# Or for Docker, mount the volume (see Docker section below)
```

**Token refresh:** OAuth tokens expire and auto-refresh. If the token expires while the headless environment is offline, re-run `claude login` locally and re-copy. For long-running setups, the token typically stays valid as long as Claude CLI uses it periodically.

**Important:** Do NOT export `ANTHROPIC_API_KEY` to the shell environment (e.g., in `.bashrc`, `.zshrc`, or Docker `environment:`). If Claude CLI inherits this variable, it overrides OAuth and switches to pay-per-token API billing. Keeping the key only in `~/.openclaw/.env` (which OpenClaw reads internally) is safe — it won't leak to subprocesses spawned via `exec`.

---

## Docker Deployment

When running OpenClaw in Docker, Claude CLI's credential and session directories must be volume-mounted for persistence.

### Critical Volume Mounts

```yaml
services:
  openclaw-gateway:
    image: openclaw/gateway:latest
    volumes:
      - ~/.openclaw:/root/.openclaw          # OpenClaw config, memory, skills
      - ~/projects:/root/workspace            # Development workspace
      - ~/.claude:/root/.claude               # ESSENTIAL: Claude CLI credentials + sessions
    network_mode: host                        # For local network discovery
```

The `~/.claude` mount is the most critical and often overlooked. Without it:
- Claude CLI prompts for authentication on every spawn (breaks automation)
- Session history is lost between container restarts (breaks `--resume`)
- Persistent memory files are not preserved

### What `~/.claude` Contains

| Path | Purpose |
|---|---|
| `credentials.json` | OAuth token for subscription auth |
| `projects/` | Per-project session history and memory |
| `settings.json` | User preferences, MCP server config |
| `statsig/` | Usage analytics (optional) |

---

## Cost Implications

### Subscription vs API — Cost Comparison

With subscription auth, Claude CLI development work is covered by your fixed monthly plan:

| Scenario | OpenClaw (Free/Cheap) | Claude CLI (Max Subscription) | Total |
|---|---|---|---|
| Any usage level | $0 | Included in Max ($100-200/mo) | **$100-200/mo fixed** |

With Max, there's no tiering concern — Opus 4.6 is available for every delegation. The fixed cost covers all usage within Max's rate limits.

**Rate limits:** Max provides the highest rate limits of any subscription tier. The `--max-turns` flag is still useful to keep individual sessions focused, not to save cost but to prevent runaway sessions.

### Cost Per Delegation (Subscription Context)

With subscription, these are not billed per-token — they consume from your plan's included usage:

| Task Type | Model | Est. Turns | `--max-turns` | Notes |
|---|---|---|---|---|
| Architecture review (read-only) | Opus 4.6 | 5-10 | `10` | Read-only, low turn count |
| Dev story implementation | Opus 4.6 | 10-30 | `30` | Longest sessions, most turns |
| Code review | Opus 4.6 | 5-10 | `10` | Moderate |
| Quick dev (small fix) | Opus 4.6 | 3-10 | `10` | Light |
| Impl. readiness check | Opus 4.6 | 5-10 | `10` | Moderate |

### Claude CLI Cost Optimizations (Automatic)

These optimizations reduce token usage (extends your subscription's daily allowance):

- **Prompt caching**: System prompt, CLAUDE.md, tool definitions cached automatically. Fewer tokens counted against limits.
- **Auto-compaction**: When approaching 200K context limit, Claude CLI summarizes history automatically. Keeps sessions efficient.
- **Subagent delegation**: Verbose tasks (test running, log analysis) run in lightweight subagents, keeping main context small.

---

## CLAUDE.md for BMAD Projects

Claude CLI automatically reads `CLAUDE.md` from the project root. Create one with BMAD conventions:

```markdown
# CLAUDE.md

## Project
Homelab infrastructure-as-code. Terraform, Ansible, Docker Compose.

## Conventions
- Follow BMAD methodology for all development work
- Read the relevant story file before starting implementation
- Check architecture docs for design decisions
- Write tests before implementation (TDD)
- Run tests after changes: `make test`
- Lint before committing: `make lint`

## Architecture
- See docs/architecture.md for current system design
- See docs/prd.md for product requirements

## Git
- Conventional commits: feat:, fix:, refactor:, docs:, test:
- One logical change per commit
- Always run tests before committing
```

---

## OpenClaw Skills for Claude CLI Delegation

Skills are installed at `skills/` in the BMAD agent's workspace (`/root/.openclaw/workspace/homelab-playbook/`). Each skill is a directory with a `SKILL.md` file — OpenClaw discovers them automatically.

### Installed Skills (33 total)

```
skills/
  │
  ├── Phase 1 — Analysis (local, Gemini Pro)
  │   ├── create-product-brief/SKILL.md
  │   ├── market-research/SKILL.md
  │   ├── domain-research/SKILL.md
  │   ├── technical-research/SKILL.md        (escalates to /model reason)
  │   └── brainstorming/SKILL.md
  │
  ├── Phase 2 — Planning (local, Gemini Pro)
  │   ├── create-prd/SKILL.md
  │   ├── validate-prd/SKILL.md              (can use /model quality)
  │   ├── edit-prd/SKILL.md
  │   └── create-ux-design/SKILL.md
  │
  ├── Phase 3 — Solutioning
  │   ├── create-architecture/SKILL.md       ← DELEGATED (Opus 4.6)
  │   ├── create-epics-and-stories/SKILL.md  (local, Gemini Pro)
  │   └── check-implementation-readiness/SKILL.md ← DELEGATED (read-only)
  │
  ├── Phase 4 — Implementation
  │   ├── sprint-planning/SKILL.md           (local, Gemini Pro — per epic)
  │   ├── sprint-status/SKILL.md             (local, Gemini Pro — on demand)
  │   ├── create-story/SKILL.md              (local, Gemini Pro — per story)
  │   ├── validate-story/SKILL.md            (local, /model quality — per story)
  │   ├── dev-story/SKILL.md                 ← DELEGATED (Opus 4.6, per story)
  │   ├── code-review/SKILL.md               ← DELEGATED (Opus 4.6, per story)
  │   ├── qa-automate/SKILL.md               (local, /model quality — per story)
  │   ├── correct-course/SKILL.md            (local, /model reason — exception)
  │   └── retrospective/SKILL.md             (local, Gemini Pro — per epic)
  │
  ├── Quick Flow
  │   ├── quick-spec/SKILL.md                (local, Gemini Pro)
  │   └── quick-dev/SKILL.md                 ← DELEGATED (Opus 4.6)
  │
  ├── Context Management (local, Gemini Pro)
  │   ├── document-project/SKILL.md
  │   └── generate-project-context/SKILL.md
  │
  ├── Core Utilities
  │   ├── help/SKILL.md                      (/model instant)
  │   ├── party-mode/SKILL.md                (Gemini Pro)
  │   ├── index-docs/SKILL.md                (/model instant)
  │   ├── shard-doc/SKILL.md                 (/model instant)
  │   ├── editorial-review-prose/SKILL.md    (Gemini Pro)
  │   ├── editorial-review-structure/SKILL.md (/model quality)
  │   └── adversarial-review/SKILL.md        (/model reason)
  │
  └── Generic
      └── claude-delegate/SKILL.md           ← DELEGATED (fallback)
```

**6 skills delegate to Claude CLI** (Opus 4.6 via Max), **27 run locally** on free/cheap models.

### BMAD Agent Config (in openclaw.json)

```json5
{
  "id": "bmad",
  "name": "BMAD Orchestrator",
  "workspace": "/root/.openclaw/workspace/homelab-playbook",
  "model": { "primary": "google-gemini-cli/gemini-3-pro-preview" },
  "tools": {
    "profile": "coding",
    "alsoAllow": ["exec", "read", "write", "edit"],
    "exec": {
      "host": "gateway",
      "timeoutSec": 1800,
      "backgroundMs": 30000,
      "notifyOnExit": true
    }
  }
}
```

The BMAD agent runs on Gemini Pro (free) for orchestration and uses `exec` to invoke Claude CLI for delegated workflows. Each skill's SKILL.md tells the agent exactly which `claude -p` command to run, with the right `--allowedTools` and `--max-turns` for that workflow.

---

## Environment Setup

### Prerequisites

```bash
# Install Claude CLI
npm install -g @anthropic-ai/claude-code

# Verify installation
claude --version
```

### Authenticate with Subscription (OAuth)

```bash
# On a machine with a browser — authenticate via OAuth
claude login
# This opens a browser for Claude Pro/Max subscription auth
# Credentials saved to ~/.claude/credentials.json

# For headless environments (WSL2, VPS, Docker):
# Copy ~/.claude/ from your local machine (see "OAuth Token Handoff" above)

# IMPORTANT: Do NOT export ANTHROPIC_API_KEY to the shell
# (e.g., in .bashrc, .zshrc, or Docker environment:)
# If Claude CLI inherits it, it overrides OAuth → per-token billing
# Keys in ~/.openclaw/.env are safe (OpenClaw reads internally, not exported)
# Verify the shell doesn't have it:
echo $ANTHROPIC_API_KEY  # Should be empty
```

**Note:** OpenClaw's `ANTHROPIC_API_KEY` (in `~/.openclaw/.env`) is for OpenClaw's own API calls to Claude as a fallback model. Claude CLI should NOT use this key — it uses the subscription via OAuth. Keep these auth paths separate.

### Configure MCP Servers for Claude CLI

```bash
# Add GitHub MCP (available in all Claude CLI sessions)
claude mcp add --transport http -s user github https://api.githubcopilot.com/mcp/

# List configured servers
claude mcp list
```

### Test the Integration

```bash
# Quick test — should return JSON with result
claude -p "Say hello" --output-format json --max-turns 1

# Verify subscription auth (not API key)
# The output JSON should NOT show total_cost_usd charges if on subscription
claude -p "What auth method am I using?" --output-format json --max-turns 1

# Test with file access
cd /root/.openclaw/workspace/homelab-playbook
claude -p "List the files in the openclaw/ directory" \
  --output-format json \
  --allowedTools "Bash(ls *),Glob" \
  --max-turns 3
```

---

## Security Considerations

### Attack Surface

The OpenClaw + Claude CLI integration grants significant system access. Claude CLI can read/write files, execute shell commands, and access the network. OpenClaw adds remote triggering (Telegram/Discord) and scheduled execution (cron). Together, this is essentially "God-mode" access to the host system.

### ClawHub Supply Chain Risk

The OpenClaw skill ecosystem (ClawHub) has documented supply-chain vulnerabilities:

- **Malicious skills** can embed harmful commands in SKILL.md files (Markdown parsed as executable instructions)
- **Known payloads** include info-stealers (AMOS Stealer), SSH key injection, and data exfiltration via `curl | bash` patterns
- **Mitigation:** Never install unverified skills from ClawHub. Audit every SKILL.md before use. Use `openclaw-skills-security-checker` for automated scanning.

### Defensive Architecture

1. **Containerization:** Run the entire stack in Docker with limited volume mounts. Use rootless Docker mode for additional isolation.
2. **Egress filtering:** Firewall rules should allow traffic only to trusted API endpoints (`api.anthropic.com`, `api.openai.com`, `github.com`). Block all other outbound connections.
3. **Tool whitelisting:** Prefer `--allowedTools "Read,Write,Edit,Bash,Glob,Grep"` over `--dangerously-skip-permissions`. This provides autonomy while restricting the tool surface.
4. **Elevated command review:** Configure OpenClaw's `elevated` tool policy to require explicit user approval for `exec` commands, especially those invoking Claude CLI with write permissions.
5. **Workspace isolation:** Mount only the specific project directory as workspace, not the entire home directory. Claude CLI only needs access to the code it's working on.

---

## Related Documents

- [bmad-pipeline.md](./bmad-pipeline.md) — BMAD workflow phases and model routing
- [model-routing-strategy.md](./model-routing-strategy.md) — Model inventory and task-to-model matrix
- [cost-optimization.md](./cost-optimization.md) — Cost optimization techniques and budget scenarios
- [openclaw-config-reference.md](./openclaw-config-reference.md) — Full openclaw.json configuration reference
- [openclaw claude cli.md](./openclaw%20claude%20cli.md) — Deep research analysis of OpenClaw + Claude CLI integration (academic reference)
