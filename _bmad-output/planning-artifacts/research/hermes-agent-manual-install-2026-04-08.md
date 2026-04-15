# Hermes Agent Manual Install Record — ct-dev-test

**Date:** 2026-04-08
**Target:** ct-dev-test (192.168.50.152)
**Installer:** `curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash`
**Source:** NousResearch/hermes-agent (GitHub, MIT license)

---

## Install Command

```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
```

Installer handles Python 3.11, Node.js, uv automatically.

## Binary Location

- Installed to: `~/.local/bin/hermes`
- Also at: `~/.hermes/hermes-agent/venv/bin/hermes`
- `~/.hermes/bin/tirith` (helper binary)
- **PATH issue:** `~/.local/bin` not in PATH by default — must add to `.bashrc`

## Setup Wizard (`hermes setup`)

### Authentication

| Prompt | Options | Chosen | Notes |
|--------|---------|--------|-------|
| Authentication method | 1. Claude Pro/Max subscription (OAuth), 2. Anthropic API key, 3. Cancel | 1 (OAuth) | **IMPORTANT:** Anthropic banned subscription OAuth for third-party agents as of April 4, 2026. OAuth tokens fail with HTTP 401. |

**Working auth method:** Clear stale OAuth tokens, let Hermes auto-discover Claude Code credentials:
```bash
hermes config set ANTHROPIC_API_KEY ""
hermes config set ANTHROPIC_TOKEN ""
```
Hermes then uses Claude Code's credential store directly.

### TTS Provider

| Prompt | Options | Chosen | Notes |
|--------|---------|--------|-------|
| Select TTS provider | Edge TTS (free), ElevenLabs, OpenAI TTS, MiniMax TTS, NeuTTS | Edge TTS (default) | Not needed for director use case |

### Terminal Backend

| Prompt | Options | Chosen | Notes |
|--------|---------|--------|-------|
| Select terminal backend | Local, Docker, Modal, SSH, Daytona, Singularity | Local (default) | Container is the execution environment |

### Working Directory

| Prompt | Default | Chosen | Notes |
|--------|---------|--------|-------|
| Messaging working directory | `.` | `/home/developer/workspace/homelab` | Project root for cron/messaging sessions |

### Sudo

| Prompt | Default | Chosen | Notes |
|--------|---------|--------|-------|
| Enable sudo support? | N | N | Architecture: FR39 — Director doesn't install packages. Developer has passwordless sudo anyway. |

### Agent Settings

| Prompt | Default | Chosen | Notes |
|--------|---------|--------|-------|
| Max iterations | 60 | 90 | Architecture assumes 90 max turns |
| Tool progress mode | all | all | Good visibility during testing |
| Compression threshold | 0.5 | 0.7 | Keep more context for BMAD workflows |
| Session reset mode | Inactivity + daily | Inactivity + daily (default) | Good for always-on director |

### Tools Enabled

| Tool | Enabled | API Key Needed | Notes |
|------|---------|---------------|-------|
| Web Search & Scraping | Yes | No | Built-in |
| Browser Automation | Yes | No | Built-in |
| Terminal & Processes | Yes | No | Core functionality |
| File Operations | Yes | No | Core functionality |
| Code Execution | Yes | No | Core functionality |
| Vision / Image Analysis | Yes | No | Built-in |
| Image Generation | Yes | No (FAL.ai key optional) | Skipped API key |
| Mixture of Agents | No | Yes (OpenRouter) | Needs multiple LLM providers |
| Text-to-Speech | Yes | No | Edge TTS |
| Skills | Yes | No | Core — BMAD skills will load here |
| Task Planning | Yes | No | Core — todo management |
| Memory | Yes | No | Hermes built-in memory |
| Session Search | Yes | No | FTS5 session history |
| Clarifying Questions | Yes | No | Built-in |
| Task Delegation | Yes | No | Core — subagent spawning |
| Cron Jobs | Yes | No | Core — scheduled tasks |
| RL Training | Yes | Yes (Tinker API key) | Enabled with free Tinker key — Phase 2 feature |
| Home Assistant | Yes | Yes (HA token) | Tom has HA at ha.bi-services.be |

### Additional Config

| Prompt | Value | Notes |
|--------|-------|-------|
| Home Assistant URL | `https://ha.bi-services.be` | Via reverse proxy |
| FAL API key | Skipped | Not needed |
| WandB API key | Skipped | Not needed now |

## Config File Locations

```
~/.hermes/
├── config.yaml          # Model, terminal, memory, tools, display
├── .env                 # API keys (cleared for Claude Code auto-discovery)
├── SOUL.md              # Agent identity/personality
├── memories/
│   ├── MEMORY.md        # Agent notes (2,200 char limit)
│   └── USER.md          # User profile (1,375 char limit)
├── skills/              # Agent-created + installed skills
├── cron/                # Scheduled jobs
├── sessions/            # Conversation history (SQLite FTS5)
└── hermes-agent/        # Installed package + venv
    └── venv/bin/hermes  # Actual binary
```

## Critical Discoveries

1. **OAuth banned for third-party agents** — Anthropic blocked subscription OAuth tokens for Hermes/OpenClaw as of April 4, 2026. Must clear stale tokens and use Claude Code credential auto-discovery instead.

2. **PATH not set** — `~/.local/bin` not in PATH after install. Must add manually or via Ansible.

3. **Claude Code auto-discovery works** — After clearing `ANTHROPIC_API_KEY` and `ANTHROPIC_TOKEN` from `.env`, Hermes finds Claude Code's credentials automatically. No separate API key needed.

4. **No Ansible vault needed for API keys** — Hermes uses Claude Code's auth. Epic 3 retro action item #5 (vault setup for API credentials) is no longer a prerequisite.

5. **Default model:** `anthropic/claude-sonnet-4-6` — set automatically after OAuth flow.

## Implications for Epic 3 Ansible Role

- Install: `curl` installer + PATH setup
- Config: Template `config.yaml` from wizard answers (Jinja2)
- Auth: Clear `.env` tokens, rely on Claude Code auto-discovery
- No vault-encrypted API key needed
- `hermes setup` is interactive — Ansible role must template config directly, not run the wizard
- SOUL.md: Template from Jinja2
- Skills: Deploy BMAD skill stubs to `~/.hermes/skills/`
