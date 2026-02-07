# OpenClaw Model Routing Strategy

**Last Updated:** 2026-02-06
**Status:** Active Reference

## Purpose

Define which AI model to use for each task type in the homelab OpenClaw setup. The goal: maximize quality where it matters, minimize cost everywhere else.

---

## Model Inventory & Cost Matrix

| Model | Alias | Input $/1M | Output $/1M | Free Tier | Best For |
|---|---|---|---|---|---|
| google-gemini-cli/gemini-3-flash-preview | *(primary)* | $0.10 | $0.40 | Yes (OAuth) | General tasks, supervision, planning |
| google-gemini-cli/gemini-3-pro-preview | `pro` | $2.00 | $12.00 | Yes (OAuth) | BMAD workflows, complex planning (free via OAuth) |
| anthropic/claude-sonnet-4-5-20250929 | `claude` | $3.00 | $15.00 | No | Code generation, architecture, debugging |
| groq/openai/gpt-oss-20b | `fast` | ~free | ~free | Yes | Quick responses, formatting |
| groq/llama-3.3-70b-versatile | `quality` | $0.59 | $0.79 | Partial | Reasoning, QA, documentation |
| groq/deepseek-r1-distill-llama-70b | `reason` | $0.70 | $1.20 | Partial | Deep reasoning, analysis |
| groq/llama-3.1-8b-instant | `instant` | ~$0.05 | ~$0.08 | Yes | Classification, status checks, routing |

**Note:** Gemini OAuth free tier provides 60 RPM and 1,000 requests/day. Groq free tier has rate limits that vary by model — check console.groq.com for current quotas.

**Cache pricing for Claude (when using `cacheRetention: "long"`):**
- Cache write: $6.00/1M tokens (1-hour TTL)
- Cache read: $0.30/1M tokens (90% savings vs full input)

---

## Task-to-Model Routing Matrix

| Task Type | Model | Alias | Rationale | Est. Cost/Task |
|---|---|---|---|---|
| Telegram supervision | Gemini 3 Flash | *(primary)* | Free, fast, good for coordination | $0 |
| Heartbeat checks | Llama 3.1 8B | `instant` | Dedicated cheap model via heartbeat override | $0 |
| Status checks / quick lookups | Llama 3.1 8B | `instant` | Fastest, trivial, free tier | $0 |
| Documentation writing | Gemini 3 Flash | *(primary)* | Writing quality fine, free | $0 |
| BMAD: Product Brief | Gemini 3 Pro | `/model pro` | Better reasoning for planning artifacts, free via OAuth | $0 |
| BMAD: PRD generation | Gemini 3 Pro | `/model pro` | Structured output quality, free via OAuth | $0 |
| BMAD: Architecture decisions | Claude CLI Opus 4.6 | `exec` → Claude CLI | Delegated to CLI, Max subscription | Subscription |
| BMAD: Story creation | Gemini 3 Pro | `/model pro` | Structured but not critical, free via OAuth | $0 |
| Code generation (Terraform/Ansible/Compose) | Claude CLI Opus 4.6 | `exec` → Claude CLI | Delegated to CLI, Max subscription | Subscription |
| Code review | Claude CLI Opus 4.6 | `exec` → Claude CLI | Delegated to CLI, Max subscription | Subscription |
| QA / test writing | Llama 3.3 70B | `quality` | Structured, pattern-based | ~$0.01 |
| Drift detection analysis | DeepSeek R1 70B | `reason` | Needs reasoning about config diffs | ~$0.02-0.05 |
| Complex debugging | Claude CLI Opus 4.6 | `exec` → Claude CLI | Delegated to CLI, Max subscription | Subscription |
| Simple Q&A / formatting | GPT-OSS 20B | `fast` | Quick, low stakes | $0 |

---

## BMAD Pipeline Model Map

Map each BMAD workflow phase to its optimal model:

```
Phase 1: /product-brief       -> Gemini Pro (free)   -- planning, structured output
Phase 2: /create-prd          -> Gemini Pro (free)   -- structured output, templates
Phase 3: /create-architecture  -> Claude CLI Opus 4.6  -- delegated, Max subscription
Phase 4: /create-epics-stories -> Gemini Pro (free)   -- structured, repetitive
Phase 5: /create-story         -> Gemini Pro (free)   -- individual story detail, templated
Phase 6: /dev-story            -> Claude CLI Opus 4.6  -- delegated, Max subscription
Phase 7: /code-review          -> Claude CLI Opus 4.6  -- delegated, Max subscription
Phase 8: /qa-automation        -> quality (cheap)     -- test patterns, structured
```

**Cost per full BMAD cycle:** $0 variable (delegated sessions covered by Max subscription, rest is free/cheap)

**Savings:** 75-90% by routing non-critical phases to free/cheap models.

See [bmad-pipeline.md](./bmad-pipeline.md) for the full 31-workflow breakdown with per-epic vs per-story frequency.

---

## Groq Model Selection Guide

### `fast` (groq/openai/gpt-oss-20b)
- **Speed:** Fastest
- **Quality:** Lowest
- **Use for:** Chat acknowledgments, simple Q&A, text formatting, message routing
- **Avoid for:** Code generation, architecture decisions, anything requiring nuance

### `quality` (groq/llama-3.3-70b-versatile)
- **Speed:** Fast
- **Quality:** Good general-purpose reasoning
- **Use for:** BMAD artifacts, documentation, QA test generation, code review triage, structured outputs
- **Avoid for:** Complex multi-file code generation, subtle debugging

### `reason` (groq/deepseek-r1-distill-llama-70b)
- **Speed:** Moderate (chain-of-thought reasoning adds latency)
- **Quality:** Best reasoning on Groq
- **Use for:** Drift detection analysis, architecture decisions (budget alternative to Claude), debugging analysis, config diff evaluation
- **Avoid for:** Simple tasks (overkill), latency-sensitive interactions

### `instant` (groq/llama-3.1-8b-instant)
- **Speed:** Near-instant
- **Quality:** Basic
- **Use for:** Classification, routing decisions, simple summaries, status checks, pre-processing
- **Avoid for:** Anything requiring real reasoning or code quality

---

## Fallback Strategy

When the primary model hits rate limits, the configured fallback chain degrades gracefully:

```
Gemini 3 Flash (free, primary)
    ↓ rate limit hit
Gemini 3 Pro (free, same OAuth quota but different model endpoint)
    ↓ rate limit hit
Groq llama-3.3-70b-versatile (cheap: $0.59/$0.79 per 1M)
    ↓ rate limit hit
Claude Sonnet 4.5 (expensive fallback: $3.00/$15.00 per 1M — rarely reached)
```

**Current config (applied):**
```json5
"model": {
  "primary": "google-gemini-cli/gemini-3-flash-preview",
  "fallbacks": ["google-gemini-cli/gemini-3-pro-preview", "groq/llama-3.3-70b-versatile", "anthropic/claude-sonnet-4-5-20250929"]
}
```

OpenClaw handles failover with exponential backoff: 1min -> 5min -> 25min -> 1hr cap. Auth profiles are pinned per session and rotate on cooldown.

---

## How to Switch Models

### In Chat (Telegram / Web)
```
/model pro         # Switch to Gemini 3 Pro for BMAD sessions
/model claude      # Switch to Claude Sonnet 4.5 (OpenClaw fallback only — dev work uses Claude CLI)
/model fast        # Switch to GPT-OSS 20B for quick tasks
/model quality     # Switch to Llama 3.3 70B for quality work
/model reason      # Switch to DeepSeek R1 for deep reasoning
/model instant     # Switch to Llama 3.1 8B for fast lookups
/model default     # Reset to primary (Gemini Flash)
```

### Per-Agent (in openclaw.json)
Set `model.primary` in the agent definition within `agents.list[]`.

### Per-Heartbeat Override (Active)
```json5
"heartbeat": {
  "every": "30m",
  "model": "groq/llama-3.1-8b-instant"  // dedicated cheap model for heartbeats
}
```
Heartbeats use `instant` via Groq free tier, keeping them off the Gemini quota entirely.

### Workflow Recommendation
1. Switch to `/model pro` at the start of any BMAD session
2. For architecture, impl. readiness, dev story, and code review — OpenClaw delegates to Claude CLI (Opus 4.6 via Max subscription). No `/model` switch needed
3. Stay on Pro for sprint mgmt, story creation, and retrospective
4. Switch back to `/model default` (Flash) when BMAD work is done
5. Use `/model reason` for drift detection, analysis, and correct-course tasks

---

## Cost Comparison: Current vs Unoptimized

| Scenario | Monthly Cost |
|---|---|
| All Claude via API (unoptimized) | $800-1,500+ variable |
| All Gemini (free tier only) | $0 |
| Current setup (Max + free models) | ~$100-200/mo fixed (Max subscription) + $0 (Gemini/Groq) |

The current setup uses Claude CLI (Opus 4.6 via Max subscription) for all development work and free models (Gemini Pro, Groq) for everything else. Total cost is the fixed Max subscription — no variable API charges for Claude.

See [claude-cli-delegation.md](./claude-cli-delegation.md) for Claude CLI invocation patterns and auth setup.
