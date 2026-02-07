# OpenClaw Configuration Reference & Best Practices

**Last Updated:** 2026-02-06
**Status:** Active Reference

## Purpose

Document the `openclaw.json` configuration structure, explain each section, and provide best-practice recommendations specific to this homelab setup.

---

## Config File Basics

- **Location:** `~/.openclaw/openclaw.json`
- **Format:** JSON5 (supports comments, trailing commas)
- **Validation:** Strict — unknown keys, malformed types, or invalid values prevent Gateway startup
- **Splitting:** Use `$include` to break large configs into multiple files as the setup grows
- **Backups:** OpenClaw auto-creates `.bak` files on changes (currently 4 backups retained)

---

## Configuration Sections Explained

### `meta` — Auto-Managed Metadata
```json5
"meta": {
  "lastTouchedVersion": "2026.2.3-1",
  "lastTouchedAt": "2026-02-05T17:30:43.797Z"
}
```
Do not edit manually. Updated automatically by OpenClaw on every config change.

### `env` — Environment Variables
Empty block. API keys have been moved to `~/.openclaw/.env` (chmod 600) for security.

### `wizard` — Setup Wizard State
Tracks the last onboard/doctor command execution. Informational only.

### `auth.profiles` — Authentication Profiles
```json5
"auth": {
  "profiles": {
    "google-gemini-cli:tom.amourette@gmail.com": {
      "provider": "google-gemini-cli",
      "mode": "oauth"
    }
  }
}
```
Google Gemini CLI uses OAuth (free tier: 60 RPM, 1,000 requests/day). OpenClaw manages token refresh automatically.

### `agents.defaults` — Default Agent Configuration

#### `model` — Primary Model Selection
```json5
"model": {
  "primary": "google-gemini-cli/gemini-3-flash-preview",
  "fallbacks": ["google-gemini-cli/gemini-3-pro-preview", "groq/llama-3.3-70b-versatile", "anthropic/claude-sonnet-4-5-20250929"]
}
```
- **Primary:** Gemini 3 Flash — cheapest Gemini model ($0.10/$0.40 per 1M tokens), free via OAuth
- **Fallback chain:** Flash -> Pro -> Groq quality -> Claude Sonnet. Degrades gracefully through increasingly capable (and expensive) models when rate limits are hit.

#### `models` — Model Registry with Aliases
```json5
"models": {
  "anthropic/claude-sonnet-4-5-20250929": {
    "alias": "claude",
    "params": { "cacheRetention": "long" }
  },
  "google-gemini-cli/gemini-3-flash-preview": {},
  "google-gemini-cli/gemini-3-pro-preview": { "alias": "pro" },
  "groq/openai/gpt-oss-20b": { "alias": "fast" },
  "groq/llama-3.3-70b-versatile": { "alias": "quality" },
  "groq/deepseek-r1-distill-llama-70b": { "alias": "reason" },
  "groq/llama-3.1-8b-instant": { "alias": "instant" }
}
```
Aliases enable quick switching via `/model <alias>` in chat.

**`cacheRetention` options:**
| Value | TTL | Cache Write Cost | Cache Read Cost | Best For |
|---|---|---|---|---|
| `"none"` | No caching | N/A | N/A | One-off queries |
| `"short"` | 5 minutes | $3.75/1M tokens | $0.30/1M tokens | Quick exchanges |
| `"long"` | 1 hour | $6.00/1M tokens | $0.30/1M tokens | Sustained coding sessions |

**Current setting:** `"long"` (1-hour TTL). Aligned with `contextPruning.ttl: "1h"` for optimal cache hit rates. See cost-optimization.md for the dollar math.

#### `memorySearch` — Memory System
```json5
"memorySearch": {
  "experimental": { "sessionMemory": true }
}
```
Enables cross-session memory search. The `experimental.sessionMemory` flag allows the agent to recall context from previous sessions.

#### `contextPruning` — Context Window Management
```json5
"contextPruning": {
  "mode": "cache-ttl",
  "ttl": "1h"
}
```
- **`cache-ttl` mode:** Trims old tool results (in-memory only, full transcript preserved on disk) when they exceed the TTL
- **`ttl: "1h"`:** Content older than 1 hour gets soft-trimmed, then hard-cleared if needed
- **Protection:** Last 3 assistant turns are always protected from pruning

This TTL should match `cacheRetention` for optimal cost alignment.

#### `compaction` — Session Compaction
```json5
"compaction": {
  "mode": "safeguard",
  "memoryFlush": { "enabled": true }
}
```
- **`safeguard` mode:** Only compacts when approaching context token limit
- **`memoryFlush`:** Before compaction, the agent writes durable memory to `memory/YYYY-MM-DD.md`, preventing information loss
- **Manual trigger:** `/compact` command forces a compaction pass

This is the optimal configuration. No changes needed.

#### `heartbeat` — Periodic Agent Turns
```json5
"heartbeat": {
  "every": "30m",
  "model": "groq/llama-3.1-8b-instant"
}
```
Runs a periodic agent turn every 30 minutes using the `instant` model via Groq free tier. This keeps heartbeats off the Gemini quota entirely, using the cheapest available model for these lightweight check-in turns.

**Current:** 48 heartbeats/day on Groq `instant` (free).

**Available heartbeat options:**
| Option | Description |
|---|---|
| `every` | Interval between heartbeats (e.g., `"30m"`, `"1h"`) |
| `activeHours` | `{ start, end }` — skip heartbeats outside these hours |
| `model` | Override model for heartbeats (e.g., use cheap model) |
| `target` | Target agent ID for heartbeat |
| `prompt` | Custom heartbeat prompt |
| `ackMaxChars` | Max characters in heartbeat acknowledgment |

#### `maxConcurrent` and `subagents`
```json5
"maxConcurrent": 4,
"subagents": { "maxConcurrent": 8 }
```
- **4 concurrent agent turns:** Appropriate for WSL2 homelab — balances responsiveness vs resource usage
- **8 concurrent subagents:** Generous but fine for parallelized research/generation tasks

### `agents.list` — Named Agent Definitions

#### Coder Agent
```json5
{
  "id": "coder",
  "name": "Homelab Coder",
  "workspace": "/root/.openclaw/workspace",
  "model": { "primary": "google-gemini-cli/gemini-3-flash-preview" },
  "memorySearch": {
    "enabled": true,
    "sources": ["memory", "sessions"]
  },
  "tools": {
    "profile": "coding",
    "alsoAllow": ["exec", "read", "write", "edit"]
  }
}
```
- Uses `coding` tool profile with exec/read/write/edit permissions
- Memory search across both workspace memory and session history
- Uses Gemini Flash as primary (free). Switch to Claude via `/model claude` for IaC code generation sessions

### `channels.telegram` — Telegram Bot
```json5
"channels": {
  "telegram": {
    "enabled": true,
    "dmPolicy": "pairing",
    "replyToMode": "first",
    "groupPolicy": "allowlist",
    "streamMode": "partial"
  }
}
```
- **`dmPolicy: "pairing"`:** Requires device pairing before accepting DMs
- **`groupPolicy: "allowlist"`:** Only responds in explicitly allowed groups
- **`streamMode: "partial"`:** Streams partial responses (better UX than waiting for full response)
- **`replyToMode: "first"`:** Replies to the first message in a thread

### `gateway` — Local Gateway Server
```json5
"gateway": {
  "port": 18790,
  "mode": "local",
  "auth": { "token": "..." },
  "remote": { "token": "..." }
}
```
- Runs on port 18790 (default is 18789)
- Local mode — not exposed to internet
- Auth tokens protect the gateway API

**Security:** Keep tokens secret. Restrict port to private network only. Use Tailscale/VPN for remote access.

### `plugins` — Enabled Plugins
```json5
"plugins": {
  "entries": {
    "telegram": { "enabled": true },
    "google-gemini-cli-auth": { "enabled": true }
  }
}
```
Minimal plugin set. Only enable what you actively use.

---

## Security: API Keys in .env

API keys are stored in `~/.openclaw/.env` (chmod 600), not in `openclaw.json`. The `env` block in `openclaw.json` is empty. OpenClaw reads `~/.openclaw/.env` automatically.

**If adding new API keys:** Always add them to `~/.openclaw/.env`, never to `openclaw.json`.

---

## Applied Config Changes (2026-02-06)

All changes below have been applied to the live `openclaw.json`.

### Change 1: Gemini Flash as Primary with Fallback Chain
```json5
"model": {
  "primary": "google-gemini-cli/gemini-3-flash-preview",
  "fallbacks": ["google-gemini-cli/gemini-3-pro-preview", "groq/llama-3.3-70b-versatile", "anthropic/claude-sonnet-4-5-20250929"]
}
```

### Change 2: Upgraded Cache Retention to Long
```json5
"params": {
  "cacheRetention": "long"  // was "short" — 77-92% savings on Claude cache costs
}
```

### Change 3: Heartbeat on Groq Instant
```json5
"heartbeat": {
  "every": "30m",
  "model": "groq/llama-3.1-8b-instant"  // dedicated cheap model, off Gemini quota
}
```

### Change 4: API Keys Moved to .env
`ANTHROPIC_API_KEY` and `GROQ_API_KEY` moved from `env` block to `~/.openclaw/.env` (chmod 600).
