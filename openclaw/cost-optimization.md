# OpenClaw Cost Optimization Guide

**Last Updated:** 2026-02-06
**Status:** Active Reference

## Purpose

Minimize OpenClaw API costs while maintaining quality for critical tasks. OpenClaw itself is free (MIT licensed) — all costs come from LLM provider APIs.

---

## Cost Baseline: Three Tiers

This setup uses a three-tier cost strategy:

| Tier | Models | Cost | Use Case |
|---|---|---|---|
| **Free** | Gemini Flash OAuth, Groq free tier, `instant`, `fast` | $0 | Supervision, heartbeats, simple tasks |
| **Cheap** | Groq `quality` ($0.59/$0.79/1M), `reason` ($0.70/$1.20/1M) | ~$0.01-0.05/task | QA, drift detection, structured reasoning |
| **Premium** | Claude Sonnet 4.5 ($3.00/$15.00/1M) | ~$0.10-0.50/task | Code generation, architecture, debugging |

**Key insight:** Context accumulation is the biggest cost driver. Every message in history gets resent with each request. Long sessions with Claude can spiral fast.

---

## 1. Free Tier Maximization

### Gemini Flash OAuth (Primary Model)
- **Model:** `google-gemini-cli/gemini-3-flash-preview` ($0.10/$0.40 per 1M tokens, free via OAuth)
- **Limits:** 60 RPM, 1,000 requests/day
- **Current usage:** Telegram interactions + BMAD planning (heartbeats are on Groq `instant`, not Gemini)
- **Headroom:** ~950+ requests/day available for interactive work
- **Assessment:** Cheapest Gemini model, well-sized for supervisor role. Flash is faster and cheaper than Pro while sufficient for coordination tasks.

### Groq Free Tier
- **Available models:** All four Groq models have free tier access
- **Limits:** Rate-limited by requests/tokens per minute and per day (varies by model)
- **Best free-tier model:** `instant` (llama-3.1-8b-instant) — lightest rate limits
- **Check current limits:** console.groq.com/settings/billing/plans

### Google Gemini CLI OAuth vs API Key
- **OAuth (current):** 60 RPM, 1,000/day — generous for personal use
- **API key:** Different rate limits, may require billing setup
- **Recommendation:** Stay on OAuth. It's free and sufficient.

---

## 2. Prompt Caching — Biggest Single Savings Lever

### The Problem
When using Claude Sonnet 4.5, every request sends the full system prompt + workspace context + conversation history. Without caching, you pay full input price ($3.00/1M tokens) every turn.

### Current Config (Applied)
```json5
"cacheRetention": "long"  // 1-hour TTL (changed from "short")
```

### Dollar Math

Assume a typical coding session: 15K tokens of cached content (system prompt + workspace files), 10 turns over 45 minutes.

**With `short` (5-min cache):**
If turns are spaced >5 minutes apart (common during code review/testing):
- 10 cache writes: 10 x 15K x $3.75/1M = **$0.56**
- 0 cache reads (expired between turns)
- Plus regular input/output costs

**With `long` (1-hr cache):**
- 1 cache write: 1 x 15K x $6.00/1M = **$0.09**
- 9 cache reads: 9 x 15K x $0.30/1M = **$0.04**
- Total: **$0.13**

**Savings: 77% on cached content costs.**

For sessions with more turns or longer system prompts, savings reach 90%+.

### Why This Works
The `contextPruning.ttl` is already set to `"1h"`. Changing `cacheRetention` to `"long"` (also 1 hour) aligns the two — cached content stays warm for the same duration the pruner considers it "recent."

---

## 3. Heartbeat Optimization

### Current Config (Applied)
```json5
"heartbeat": {
  "every": "30m",
  "model": "groq/llama-3.1-8b-instant"
}
```
48 heartbeats/day on Groq `instant` (free tier). Heartbeats are completely off the Gemini quota, leaving more Gemini requests available for interactive work.

### Cache Warming Note
If using Claude with 1-hour cache retention, set heartbeat to `"55m"` to keep the cache warm. Not applicable in current setup since heartbeats use Groq, not Anthropic.

---

## 4. Compaction & Memory Flush

### Current Config (Already Optimal)
```json5
"compaction": {
  "mode": "safeguard",
  "memoryFlush": { "enabled": true }
}
```

### Why This Is Good
- **Safeguard mode:** Only compacts when hitting context token limit (no premature compaction)
- **Memory flush:** Before compaction, writes durable notes to `memory/YYYY-MM-DD.md`
- **Cost:** Compaction uses the session's current model. Since primary is Gemini Flash (free), compaction is free for the main agent

### Watch Out For
When the coder agent runs long Claude sessions, compaction triggers on Claude = paid compaction turn. Mitigations:
- Start fresh sessions for new tasks instead of extending old ones
- Use `/compact` manually at a natural breakpoint while still on Gemini before switching to Claude

---

## 5. Sub-agent Cost Control

### Principle
Not every sub-task needs the most expensive model. Configure sub-agents to use cost-effective models.

### Current Config
```json5
"subagents": { "maxConcurrent": 8 }
```
Sub-agents inherit the session's model. If a Claude session spawns 8 sub-agents, that's 8 parallel Claude API calls.

### Recommendations
- **Research/data gathering:** Run on `quality` or `reason` (Groq, ~$0.01/task)
- **Classification/routing:** Run on `instant` ($0, free tier)
- **Code generation sub-tasks:** Claude is justified here
- **Scope tasks tightly:** Fewer iterations = fewer API calls = lower costs

---

## 6. Session Management

### Start Fresh Sessions for New Tasks
Every message in the conversation history gets resent with each API call. A 50-turn session sends all 50 turns every time. Cost grows linearly with session length.

**Practice:**
- End sessions after completing a logical unit of work
- Start new sessions for new BMAD phases or task types
- Don't use a coding session for unrelated Q&A

### Separate Sessions for Large Outputs
Commands that produce large outputs (e.g., `git diff`, `docker inspect`) inflate context. Run these in separate diagnostic sessions or use the coder agent specifically for them.

---

## 7. Monthly Cost Breakdown

All Claude CLI development work runs on **Opus 4.6 via Claude Max subscription** (fixed monthly cost). OpenClaw supervision runs on free/cheap models. No per-token Claude charges.

| Item | Cost | Notes |
|---|---|---|
| Claude Max subscription | $100-200/mo | All Claude CLI delegated work (Opus 4.6) — architecture, dev stories, code review, debugging |
| Gemini Flash/Pro (OpenClaw supervisor) | $0 | Free via OAuth — BMAD planning, coordination, heartbeats |
| Groq (QA, validation, reasoning) | ~$0.50-5/mo | Minimal — validation tasks, correct-course |
| **Monthly total** | **~$100-200/mo fixed** | Predictable, no variable Claude API charges |

### For Comparison: Unoptimized Baseline
All tasks on Claude via API, no caching, no model routing:
- **Monthly total:** $800-1,500+ variable

**Current setup savings:** Fixed $100-200/mo vs $800-1,500+ variable. Plus, Opus 4.6 for everything instead of rationing between Sonnet/Opus.

---

## 8. Quick Wins Checklist

| # | Action | Status | Impact | Est. Savings |
|---|---|---|---|---|
| 1 | `cacheRetention` set to `"long"` | Applied | High | 77-92% on Claude cache costs |
| 2 | `model.fallbacks` chain configured | Applied | Medium | Prevents failures when Gemini rate-limited |
| 3 | Heartbeat on Groq `instant` | Applied | Medium | Heartbeats off Gemini quota entirely |
| 4 | API keys in `~/.openclaw/.env` | Applied | Security | Prevents accidental key exposure |
| 5 | Gemini Flash as primary (was Pro) | Applied | Low | Cheaper per-token if OAuth quota exceeded |
| 6 | Start fresh sessions per task | Workflow habit | Medium | Prevents context bloat |
| 7 | Delegate dev work to Claude CLI (Opus 4.6 via Max) | Workflow habit | High | Fixed cost subscription instead of per-token |
| 8 | Scope sub-agent tasks tightly | Workflow habit | Medium | Fewer iterations per sub-agent |

**Remaining workflow habits (#6-8):** These are the biggest ongoing optimization levers. The config changes are done.

---

## Tools & Resources

- **OpenClaw Cost Calculator:** https://calculator.vlvt.sh/
- **Groq Console (check rate limits):** https://console.groq.com/settings/billing/plans
- **Anthropic Console (set spending limits):** https://console.anthropic.com/settings/billing
- **OpenClaw Docs — Compaction:** https://docs.openclaw.ai/concepts/compaction
- **OpenClaw Docs — Model Providers:** https://docs.openclaw.ai/concepts/model-providers

---

## Related Documents

- [model-routing-strategy.md](./model-routing-strategy.md) — Which model to use for each task type
- [openclaw-config-reference.md](./openclaw-config-reference.md) — Full config reference with recommended changes
- [claude-cli-delegation.md](./claude-cli-delegation.md) — Delegating dev work to Claude CLI (Opus 4.6 via Max subscription)
