---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments: []
workflowType: 'research'
lastStep: 6
research_type: 'technical'
research_topic: 'Nous Research Hermes Agent — multi-provider rate-limit avoidance, smart-switching, and cost/perf tuning across Claude + Gemini + ChatGPT subscriptions (with local fallback)'
research_goals: 'Define a setup pattern for Hermes Agent that (a) never trips a single-provider rate limit, (b) smart-switches between Claude/Gemini/ChatGPT subscription seats first then API fallback, (c) optionally falls through to local Ollama, (d) keeps overall $ spend low while maintaining good performance — sub-first, API-fallback routing.'
user_name: 'tomamourette'
date: '2026-05-15'
web_research_enabled: true
source_verification: true
---

# Research Report: technical

**Date:** 2026-05-15
**Author:** tomamourette
**Research Type:** technical

---

## Research Overview

**Topic:** How to set up Nous Research **Hermes Agent** to (a) avoid hitting single-provider rate limits, (b) smart-switch between Claude / Gemini / ChatGPT subscription seats first, then API keys, then local Ollama, and (c) keep total $ low while maintaining strong performance.

**Operator context:** Tom (homelab operator) holds active subscriptions for Anthropic Claude (Pro/Max), Google Gemini (Pro/Ultra), and OpenAI ChatGPT (Plus/Pro). A local Ollama stack runs on `pve3` (Gemma reasoner per the Hybrid-Gemma-Serving project memory) and is available as a free-tier fallback.

**Methodology:** Director-coordinated parallel sub-agent web research, each sub-agent assigned a bounded subdomain, results cross-checked against primary sources (vendor docs, OSS repos, pricing pages) and merged by the director.

---

## Technical Research Scope Confirmation

**Research Topic:** Nous Research Hermes Agent — multi-provider rate-limit avoidance, smart-switching, cost/perf tuning
**Research Goals:** sub-first / API-fallback routing, balance cost + performance, never trip rate limits

**Technical Research Scope:**
- Architecture Analysis — Hermes Agent runtime, where the provider/routing seam lives
- Implementation Approaches — Subscription-seat routing vs API-key routing, OAuth-token rotation
- Technology Stack — Hermes Agent + LiteLLM / OpenRouter / Portkey / RouteLLM / Helicone / claude-code-router
- Integration Patterns — OpenAI-compatible proxy front-end, fallback chains, retry/backoff, rate-limit-header handling
- Performance Considerations — Tier-by-difficulty routing, prompt cache reuse, spillover thresholds

**Research Methodology:**
- Current web data with rigorous source verification
- Multi-source validation for critical technical claims
- Confidence levels flagged where the public record is thin
- Director + parallel sub-agent decomposition

**Scope Confirmed:** 2026-05-15

---

<!-- Content will be appended sequentially through research workflow steps -->

## Executive Summary (TL;DR)

The original premise — *"smart-switch between Claude/Gemini/ChatGPT subscriptions to dodge rate limits and save money"* — **only partially holds in May 2026**. Vendor crackdowns since Feb 2026 changed the landscape:

| Subscription | Sub-OAuth for third-party agents? | Verdict |
|---|---|---|
| **Anthropic Claude Pro/Max** | Officially **banned** in Feb 2026, then "reinstated" May 2026 via a separate **Agent SDK credit pool that bills at API rates** | **Skip sub-routing** — pay API directly. No real savings remain. |
| **Google Gemini Pro/Ultra** | OAuth via `gemini-cli` works; grey-zone but tolerated | **Use it.** 1,500–2,000 req/day for bulk/cheap tier. |
| **OpenAI ChatGPT Plus/Pro** | OAuth via Codex CLI exists but highest enforcement risk; OpenAI history of bricking proxies | **Best-effort overlay** — don't depend on it. |

**Recommended architecture (homelab, May 2026):**

1. **Hermes Agent native config** (Nous Research, MIT, already self-hostable on ct-hermes-hub) handles routing — its built-in `fallback_model:` chains, `auxiliary:` slots, and credential pools cover ~80% of the requirement without an external proxy.
2. **Tier ladder** baked into Hermes config: Gemini 3 Flash-Lite → Haiku 4.5 → Sonnet 4.6 → Opus 4.7 / GPT-5.5 → Ollama Gemma 3 on pve3.
3. **LiteLLM** in front of Hermes only if you need cross-provider 429 cooldown / quota tracking / Postgres-backed observability — *and* you pin a version past the #26015 CPU-hang bug. Otherwise skip; Hermes's own fallback is simpler.
4. **Sub-seat OAuth limited to Gemini** (Code Assist) for bulk tier. Treat Claude Max OAuth as dead for agent use. Don't wire Codex OAuth into a production loop.
5. **Prompt caching is the real cost lever** — Anthropic's 90% cache-read discount + 1.25× write premium pays for itself after one hit; Claude Code-style agent loops report 60–90% input savings. This dwarfs any routing-layer gain.

---

## Technical Overview — Hermes Agent (Nous Research)

**Product:** [hermes-agent.nousresearch.com](https://hermes-agent.nousresearch.com/) — MIT-licensed, self-hosted autonomous agent (Python ~88% / TypeScript ~8.8%), v0.13.0 as of research date. Distinct from coding-IDE assistants — it's a chat-interface + tools agent across Telegram/Discord/Slack/WhatsApp/Signal/Email/CLI with persistent memory, scheduled tasks, and skill system.

**Runtime model:** Self-hosted, no telemetry, all state stays local. Install via `curl … install.sh | bash`, then `hermes setup`. Configured via `~/.hermes/config.yaml` + `~/.hermes/.env`. Sandboxing backends: local / Docker / SSH / Singularity / Modal.

**Provider abstraction:** First-class multi-provider. Documented providers (May 2026): OpenAI, Anthropic, Gemini, Groq, OpenRouter, Nous Portal, DeepSeek, MiniMax, Qwen, xAI, Alibaba, HuggingFace, NovitaAI, NVIDIA NIM, Ollama, AWS Bedrock, Azure Foundry, plus any OpenAI-compatible custom endpoint.

**Config schema (per slot):**
```yaml
model:
  provider: openrouter
  model: "anthropic/claude-sonnet-4.6"
  base_url: ""
fallback_model:
  provider: anthropic
  model: "claude-haiku-4.5"
auxiliary:
  compression:
    provider: gemini
    model: "gemini-3-flash"
```

**Built-in resilience:**
- `fallback_model:` triggers on primary error (native failover, no proxy needed).
- `agent.api_max_retries` (default 3) for transient errors.
- **Credential pools** rotate across multiple API keys for the same provider on 429/failure — biggest single rate-limit-avoidance feature.
- Per-provider `request_timeout_seconds` / `stale_timeout_seconds`.
- No global queue or cross-provider quota tracker — that's where an external proxy adds value, if at all.

**Cost-aware routing — gaps:** No built-in task-difficulty router. Only cost knob is `provider_routing.sort: "price"` and only when traffic goes via OpenRouter. Workaround: assign cheaper models to `auxiliary.*` slots manually.

**OAuth status (verified 2026-05-15):**
- ChatGPT/Codex device-code OAuth: ✅
- gemini-cli OAuth (Google Cloud Code Assist backend): ✅
- GitHub Copilot OAuth: ✅
- Anthropic OAuth (Claude Max): ⚠️ Supported in code but routes to Anthropic's `extra_usage` billing pool which is empty by default — open issues #15080, #10575, #6475, #12905 document HTTP 400 "out of extra usage" for Max subscribers. **Operationally unusable for sub-savings.**

---

## Integration Patterns — Routing/Proxy Layers Compared

When Hermes's native fallback is not enough (e.g., you want cross-provider 429 cooldown, persistent quota tracking, or shared routing across other tools), insert a proxy.

| Tool | Self-host | License | OpenAI-compat | Failover | RL tracking | Cost-tier | Sub-OAuth | Ollama |
|---|---|---|---|---|---|---|---|---|
| **LiteLLM** | ✅ (needs Postgres for full proxy) | MIT + commercial | ✅ | ✅ ordered | ✅ `cooldown_time` (with bug caveats) | Manual | ✅ Claude Code header passthrough | ✅ |
| **OpenRouter** | ❌ hosted | Proprietary | ✅ | ✅ `models: [...]` | ✅ managed | Implicit (price-sorted) | ❌ | ❌ |
| **Portkey** | ✅ (MIT gateway) | MIT/proprietary | ✅ | ✅ | ✅ | ✅ Configs | ❌ | ✅ |
| **RouteLLM** | ✅ Python | Apache-2.0 | ✅ server mode | ❌ (not its job) | ❌ | ✅ (its whole purpose) | ✅ via downstream | n/a |
| **Helicone AI Gateway** | ✅ Rust, ~30 MB | Apache-2.0* | ✅ | ✅ weighted | ✅ | ✅ | ❌ | ⚠️ unclear |
| **claude-code-router** | ✅ Node/Bun | MIT | Anthropic-shaped | ❌ no explicit failover | ❌ | Route-by-slot only | Inherits CC env (fragile) | ✅ first-class |
| **Cloudflare AI Gateway** | ❌ edge | Proprietary | ✅ | ✅ | ✅ sliding | Via Workers code | ❌ | ❌ |
| **Kong AI Gateway** | ✅ heavy | Apache-2.0 + EE | ✅ | ✅ cross-format (3.10+) | ✅ `failover_criteria` | Load-balanced | ❌ | ✅ |

*Helicone license labels inconsistent — verify before commit.

**Per-tool key notes:**

- **LiteLLM** — most feature-complete OSS option; the *only* one supporting Anthropic OAuth header passthrough (`forward_client_headers_to_llm_api: true`). Multiple open bugs around 429 (#24366 cooldown bypass, #3274 slow Groq fallback, #22296 streaming 429 fallback broken). **#26015** — 100% CPU hang on mid-stream 429 *when fallbacks are empty* — defensive config required.
- **OpenRouter** — simplest fallback (`"models": [...]` array), pays only for successful model. Free tier 50 req/day / 20 RPM. No Ollama. No sub-OAuth.
- **Portkey OSS gateway** — sub-1ms claimed overhead, MIT; no documented Claude Pro/Max OAuth forwarding. Cloud Enterprise from $250/mo (overkill).
- **RouteLLM** — academic project, binary classifier picking strong-vs-weak. Use *upstream* of LiteLLM as a cost-tier router, not a replacement for failover.
- **Helicone AI Gateway** — newest, lightweight Rust binary. License inconsistency is a yellow flag.
- **claude-code-router** — task-slot router (background/think/long-context) shaped for Claude Code, *no automatic failover*. Anthropic OAuth dependency makes it fragile under the Feb 2026 enforcement regime.
- **Cloudflare AI Gateway** — edge-only; doesn't talk to Ollama; good for free-tier rate-limit shaping but not for our homelab needs.
- **Kong AI Gateway** — heavyweight (full Kong stack); overkill unless you already run Kong.

**Verdict for sub-first / API-fallback / Ollama-fallback:**

1. **First choice = Hermes Agent's native config alone.** Three slots in one YAML:
   ```yaml
   model: { provider: anthropic, model: "claude-sonnet-4.6" }
   fallback_model: { provider: gemini, model: "gemini-3.1-pro" }
   auxiliary:
     compression: { provider: gemini, model: "gemini-3-flash-lite" }
   ```
   Plus credential pools for per-provider key rotation. Simplest, no extra service.

2. **Add LiteLLM only if** you need cross-provider 429 cooldown, shared quota tracking with other tools (Hermes + ct-dev-homelab + Cursor/Claude Code), or Postgres-backed audit logging. Pin to a version past #26015 fix; always set non-empty `fallbacks` to dodge the CPU hang.

3. **Don't bother with claude-code-router** — no fallback, and its main value (Claude OAuth) is the exact thing Anthropic just clamped.

---

## Architectural Patterns — Sub-Seat OAuth (Reality Check, May 2026)

### Anthropic Claude Pro/Max — DEAD FOR AGENT USE
- Claude Code CLI OAuth works (`~/.claude/`), but **Feb 2026 Anthropic explicitly banned third-party tools/agents from using subscription tokens** (ToS clarification, *The Register* 2026-02-20; Hacker News #47069299).
- **May 2026 partial reversal:** Anthropic reinstated third-party use *only* via a separate "**Agent SDK credit pool**" billed at standard API rates with a monthly non-rollover allotment roughly equal to your plan tier ($20–$200). Arbitrage is dead by design.
- Community proxies (`horselock/claude-code-proxy`, `AmazingAng/auth2api`, `router-for-me/CLIProxyAPI`) still work technically — they violate ToS. Anthropic has shown they will brick these flows (Jan 2026 OpenClaw shutdown).
- **Recommendation:** Use Anthropic **API key** for Hermes. Reserve your Claude Code Max subscription for interactive use in Claude Code itself, where the May 2026 5h cap doubling + 50% weekly bump (through 2026-07-13) gives you ~225–900 msg/5h on Max.

### Google Gemini Pro/Ultra — USE IT
- `gemini-cli` OAuth grants Gemini Code Assist quota: **free tier = 1,000 req/day Flash-only**, **AI Pro = 1,500 req/day**, **AI Ultra = 2,000 req/day**, all including Gemini 3.x Pro via CLI router.
- Free tier became Flash-only on 2026-03-25 — Pro models require paid sub.
- Google has *not* publicly cracked down on OAuth reuse proxies (Brioch/gemini-openai-proxy, ubaltaci/gemini-cli-proxy, KashifKhn/gemini-proxy, gzzhongqi/geminicli2api).
- **Most usable subscription for agent routing.** Wire it as the bulk/cheap tier.

### ChatGPT Plus/Pro — HIGHEST RISK
- Codex CLI OAuth stores tokens at `~/.codex/auth.json`. OpenAI docs explicitly say "not for external use".
- Rate limits (April 2026 token-based rework): Plus ~40 min reasoning time on GPT-5.4 / 5h; Pro 5× Plus (10× through 2026-05-31 promo); $200 Pro 20×. `codex /status` shows live remaining.
- OpenAI has the worst track record for tolerating proxies — PandoraNext, chatgpt-to-api, revChatGPT all hit C&D or model bans. Current survivors (`numman-ali/opencode-openai-codex-auth`, `router-for-me/CLIProxyAPI`, `ben-vargas/ai-cli-proxy-api`) work today, **assume short half-life**.
- **Recommendation:** Treat ChatGPT as **API-only** for the agent. Keep your ChatGPT Plus/Pro for interactive Codex use.

### Rate-limit exhaustion signals (use these in retry logic)
| Provider | 429 header to read | Reset signal |
|---|---|---|
| Anthropic | `anthropic-ratelimit-*-remaining` / `*-reset` (Unix epoch) | `retry-after` on hard cap; **529 = global overload, fail over immediately** |
| Gemini | `RESOURCE_EXHAUSTED` + `retry-after` seconds | Quota field names the limit (e.g., `GenerateRequestsPerDayPerProjectPerModel`) |
| OpenAI | `x-ratelimit-remaining-{requests,tokens}` / `*-reset-{requests,tokens}` | Codex CLI surfaces sub-pool as `usage_limit_reached` |

---

## Implementation Research — Cost/Perf Tier Ladder

### Pricing benchmark, $/1M tokens (verified 2026-05-15)

| Model | Input | Output | Cached input | Notes |
|---|---|---|---|---|
| Claude Opus 4.7 | $5.00 | $25.00 | $0.50 | New tokenizer ≈ +35% tokens vs older Claude; 1M context std price |
| Claude Sonnet 4.6 | $3.00 | $15.00 | $0.30 | 1M context std; 79.6% SWE-bench Verified |
| **Claude Haiku 4.5** | **$1.00** | **$5.00** | **$0.10** | **Workhorse for agent loops** |
| Gemini 3.1 Pro Preview | $2.00 (≤200k) / $4.00 (>200k) | $12 / $18 | $0.20 / $0.40 | 80.6% SWE-bench, cheaper than GPT-5.5 |
| Gemini 3 Flash Preview | $0.50 | $3.00 | $0.05 | |
| **Gemini 3.1 Flash-Lite** | **$0.25** | **$1.50** | **$0.025** | **Cheapest frontier-vendor tier** |
| GPT-5.5 | $5.00 | $30.00 | $0.50 | 2× input / 1.5× output above 272k tokens |
| GPT-5.4 | $2.50 | $15.00 | $0.25 | Current "default Sonnet-class" from OpenAI |
| GPT-5.4-mini | $0.75 | $4.50 | $0.075 | Haiku-class competitor |
| GPT-5.4-nano | $0.20 | $1.25 | $0.02 | OpenAI cheapest |
| DeepSeek V3.2 | $0.28 | $0.42 | $0.028 | Cache cut 90% on 2026-04-26 |
| Groq Llama-4 Scout | $0.11 | $0.34 | n/a | 594 tok/s |
| Local Gemma 3 / Qwen 3 (Ollama on pve3) | $0 | $0 | n/a | Electricity only |

⚠️ GPT-5, 5-mini, 5-nano are deprecated — use 5.5 / 5.4-mini / 5.4-nano. Gemini 3.x is still "Preview" — may shift to GA pricing soon. DeepSeek cache prices changed <90 days ago.

### Prompt-cache economics (the real cost lever)
- Anthropic and OpenAI both: **90% cache-read discount** (10% of input price).
- Anthropic write premium: **1.25× for 5-min TTL** (breaks even after 1 hit), **2× for 1-hour TTL** (breaks even after 2 hits).
- Coding-agent loops with stable system prompt + repeated file context: **60–90% input-token savings** documented (Anthropic RCA case study, Claude Code internal telemetry).
- Combine with Batch API (50% off) for non-interactive work → ~95% effective input discount.
- **Don't bother caching:** one-shot calls, prompts <1024 tokens (Anthropic minimum cacheable block), or agent loops with rotating context.
- Gemini context caching: separate storage fee ($1/Mtok/hour Flash, $4.50/hr Pro) — only worth it for high-frequency reads, not bursty agent traffic.

### Task-difficulty routing — when worth it
- Layered approach beats single technique: **rule-then-classifier** is 80% of the value in ~50 LOC (regex on intent keywords, token-count thresholds, presence of code blocks); embedding classifier (BERT-class, ~50–200 ms) only on ambiguous queries; reserve LLM-as-judge for offline eval, not per-request (500–2000 ms latency).
- **Cascade pattern**: cheap model first, escalate only if verifier (logprob threshold, JSON-schema-validation, or unit-test failure) trips. RouteLLM's 2024 paper claimed ~85% savings; with 2026 frontier models the realistic save is 40–60% because Haiku/Flash are already very capable.
- **Confidence-gated escalation**: read token-level logprobs from cheap tier, escalate if mean logprob < threshold.

### Spillover / retry best practice
1. Read `retry-after` header → sleep exactly that long. Server is truth.
2. Else read `anthropic-ratelimit-*-reset` → sleep to reset.
3. Else **exponential backoff with full jitter**: `sleep = random(0, base × 2^attempt)`. Jitter is mandatory; without it, fleet retries lockstep-amplify the 429.
4. **Failover after 2 retries**, not 5. By retry 5, user latency is unacceptable.
5. **Circuit breaker**: trip after N failures in window; route 100% to sibling for cooldown period.
6. Distinguish **429 (your quota)** from **529 (provider-wide overload)** — the latter fails over immediately, queueing is pointless.

Anthropic concurrency caps (homelab is realistically Tier 1–2): Tier 1 = 50 RPM / 30k ITPM (Opus); Tier 2 = 1000 RPM / 450k ITPM. Tier 2 Sonnet is plenty for solo-dev.

---

## Research Synthesis — Recommended Architecture for Tom

### Stack
```
                ┌──────────────────────────┐
                │  Hermes Agent v0.13.x    │  (ct-hermes-hub, pve3, 192.168.50.163)
                │  ~/.hermes/config.yaml   │
                └─────────────┬────────────┘
                              │ (native fallback + credential pools)
        ┌──────────────────────┼──────────────────────┐
        ▼                      ▼                      ▼
  ┌──────────┐          ┌──────────┐          ┌──────────────────┐
  │ Tier 0/1 │          │ Tier 2/3 │          │   Tier 4 (local) │
  │ cheap    │          │ premium  │          │   Ollama / pve3  │
  │ bulk     │          │ reason   │          │  (Gemma 3 / Qwen)│
  └──────────┘          └──────────┘          └──────────────────┘
  Gemini Flash-Lite     Sonnet 4.6 / Opus 4.7
  (sub OAuth via        Gemini 3.1 Pro
   gemini-cli) OR       GPT-5.5
   API key              (all API key)
```

### `~/.hermes/config.yaml` skeleton (paste-and-adapt)

```yaml
# Primary slot: standard reasoning, agent tool calls
model:
  provider: anthropic
  model: "claude-sonnet-4.6"
  cache_control: ephemeral   # turn on Anthropic prompt cache
  request_timeout_seconds: 60
  stale_timeout_seconds: 120

# Fallback when Anthropic 429s or returns 529 overload
fallback_model:
  provider: gemini
  model: "gemini-3.1-pro"

# Cheap auxiliary slots — compression, summarization, sub-agent dispatch
auxiliary:
  compression:
    provider: gemini
    model: "gemini-3-flash-lite"
  summarization:
    provider: anthropic
    model: "claude-haiku-4.5"
    cache_control: ephemeral

agent:
  api_max_retries: 3        # transient errors
  # Add jittered exponential backoff at the wrapper layer if not built in

# Credential pools — rotate keys on 429
credentials:
  anthropic:
    keys:
      - "${ANTHROPIC_API_KEY_1}"
      - "${ANTHROPIC_API_KEY_2}"   # optional second key for higher RPM ceiling
  gemini:
    # gemini-cli OAuth (the sanctioned-grey-zone sub path)
    auth_type: oauth
    # falls back to GEMINI_API_KEY if OAuth dies
  openai:
    keys:
      - "${OPENAI_API_KEY}"

# Local fallback for full-vendor-outage scenario (Tailscale-only mode)
custom_providers:
  ollama_local:
    base_url: "http://ct-media-01.bi-services.be:11434"   # or wherever your Ollama lives on pve3
    model: "gemma-3-12b-it-unsloth-Q5_K_M"
```

### When to add LiteLLM
**Add it if** you want cross-tool quota tracking (Hermes + ct-dev-homelab + Cursor + Claude Code all sharing rate-limit budget) or audit logging in Postgres. Wire it as:
```yaml
# In Hermes config — point at LiteLLM proxy
custom_providers:
  litellm_proxy:
    base_url: "http://ct-litellm.bi-services.be:4000"
    api_key: "${LITELLM_MASTER_KEY}"
model:
  provider: litellm_proxy
  model: "claude-sonnet-4.6"     # LiteLLM resolves to real upstream
```
In LiteLLM's `config.yaml`, define:
```yaml
model_list:
  - model_name: claude-sonnet-4.6
    litellm_params:
      model: anthropic/claude-sonnet-4-6-20251001
      api_key: os.environ/ANTHROPIC_API_KEY_1
  - model_name: claude-sonnet-4.6   # second deployment, same logical name
    litellm_params:
      model: anthropic/claude-sonnet-4-6-20251001
      api_key: os.environ/ANTHROPIC_API_KEY_2
router_settings:
  fallbacks:
    - claude-sonnet-4.6: [gemini-3.1-pro, gpt-5.4, ollama_local]
litellm_settings:
  allowed_fails: 3
  cooldown_time: 30          # critical: makes 429s rotate keys
  num_retries: 2
general_settings:
  master_key: ${LITELLM_MASTER_KEY}
```
**Pin LiteLLM to a version past PR fixing #26015** (CPU hang on empty fallback). Always populate `fallbacks` — never empty.

### Tier ladder (set in Hermes `auxiliary` slots + agent routing logic)
| Tier | Use for | Primary | Spillover | Cost (cached) |
|---|---|---|---|---|
| 0 | Trivial: var rename, syntax | **Gemini 3.1 Flash-Lite** or local Ollama | Haiku 4.5 | $0.025/$1.50 input/output |
| 1 | Default: most coding, refactor, docs, agent loop | **Claude Haiku 4.5** (cached) | GPT-5.4-mini, Gemini 3 Flash | $0.10/$5 |
| 2 | Standard reasoning: multi-file, review, planning | **Claude Sonnet 4.6** (cached) | Gemini 3.1 Pro, GPT-5.4 | $0.30/$15 |
| 3 | Heavy: architecture, security, deep research | **Claude Opus 4.7** | GPT-5.5, Gemini 3.1 Pro >200k | $0.50/$25 |
| 4 | Offline: full cloud outage / privacy-sensitive | **Ollama Gemma 3 / Qwen 3** (pve3, your existing hybrid-Gemma stack) | — | $0 |

### Cost-control checklist
- ✅ **Turn on prompt caching globally** (Anthropic ephemeral, OpenAI cached input, Gemini context cache only for high-frequency repeats). This is the single biggest lever (60–90% savings).
- ✅ **Default to Haiku 4.5** for the agent loop, not Sonnet/Opus. Only escalate on confidence threshold or explicit tool-call type.
- ✅ **Use Gemini Code Assist OAuth** for bulk Tier 0/1 — only sanctioned-tolerated sub-routing left.
- ❌ **Don't wire Claude Max OAuth or Codex OAuth into Hermes.** Both are TOS-fragile, may break overnight. Use API keys.
- ✅ **Batch API for non-interactive work** (overnight summarization, ingestion) — 50% additional discount.
- ✅ **Set jittered exponential backoff + circuit breakers** at the Hermes wrapper layer; don't rely on naive retry.
- ✅ **Distinguish 429 from 529** — 529 means fail over now, don't queue.
- ✅ **Wire Ollama on pve3 as the final fallback** — your `project_hybrid_gemma_serving.md` stack already has UD-Q5_K_M + LiteLLM gateway; expose it as Hermes `custom_providers.ollama_local`.

### What NOT to do
- Don't deploy `claude-code-router` as the front-end router — no failover; Anthropic OAuth dependency is dead weight in May 2026.
- Don't rely on `auth2api` / `CLIProxyAPI` / `horselock/claude-code-proxy` to convert your Claude Max sub into agent quota. These violate Anthropic ToS and may stop working overnight.
- Don't pick OpenRouter as the sole proxy — pure pay-as-you-go, no Ollama, no sub-OAuth. Useful as one spillover destination, not as the routing layer.
- Don't add Kong AI Gateway or Cloudflare AI Gateway — heavyweight / edge-only respectively; wrong shape for a Proxmox homelab.

### Open questions to validate before production
1. Does Hermes Agent's `credential_pools` rotate on `429`+`anthropic-ratelimit-*-reset` correctly, or only on hard failures? (Docs ambiguous; test with synthetic 429.)
2. Does `auxiliary.compression: gemini-3-flash-lite` actually route compression traffic separately, or is it a hint the planner ignores? (Trace the actual API calls in `~/.hermes/logs/`.)
3. Gemini 3.x pricing is "Preview" — verify GA prices before annualizing the budget.
4. How does Hermes handle Anthropic prompt cache headers? Does it set `cache_control: ephemeral` blocks automatically on system prompt + tool definitions, or does it need explicit config? (Open an issue or read source.)

---

## Sources (consolidated, accessed 2026-05-15 unless noted)

### Hermes Agent (Nous Research)
- https://hermes-agent.nousresearch.com/
- https://github.com/NousResearch/hermes-agent
- https://hermes-agent.nousresearch.com/docs/user-guide/configuration
- https://hermes-agent.nousresearch.com/docs/user-guide/features/overview/
- https://hermes-agent.nousresearch.com/docs/integrations/providers
- https://hermes-agent.nousresearch.com/docs/user-guide/features/credential-pools
- GitHub Issues #15080, #10575, #6475, #12905 (Anthropic OAuth extra_usage bugs)

### Routing/Proxy Layers
- https://docs.litellm.ai/docs/proxy/reliability
- https://docs.litellm.ai/docs/tutorials/claude_code_max_subscription
- LiteLLM Issues #13380, #24366, #26015, #3274, #22296 (OAuth passthrough & 429 bugs)
- https://openrouter.ai/docs/guides/routing/model-fallbacks
- https://openrouter.ai/docs/api/reference/limits
- https://github.com/Portkey-ai/gateway
- https://github.com/lm-sys/RouteLLM
- https://github.com/Helicone/ai-gateway
- https://github.com/musistudio/claude-code-router
- https://developers.cloudflare.com/ai-gateway/features/rate-limiting/
- https://developer.konghq.com/plugins/ai-proxy-advanced/

### Subscription-Seat OAuth
- https://support.claude.com/en/articles/11145838-use-claude-code-with-your-pro-or-max-plan
- https://www.theregister.com/2026/02/20/anthropic_clarifies_ban_third_party_claude_access/
- https://venturebeat.com/technology/anthropic-reinstates-openclaw-and-third-party-agent-usage-on-claude-subscriptions-with-a-catch (2026-05-13)
- https://news.ycombinator.com/item?id=47069299
- https://apidog.com/blog/claude-code-weekly-limits-50-percent-increase-july-2026/
- https://github.com/horselock/claude-code-proxy
- https://github.com/AmazingAng/auth2api
- https://geminicli.com/docs/resources/quota-and-pricing/
- https://github.com/google-gemini/gemini-cli/discussions/22970
- https://github.com/router-for-me/CLIProxyAPI
- https://developers.openai.com/codex/auth
- https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan
- https://community.openai.com/t/understanding-the-new-codex-limit-system-after-the-april-9-update/1378768

### Pricing & Cost/Perf
- https://platform.claude.com/docs/en/about-claude/pricing
- https://platform.claude.com/docs/en/api/rate-limits
- https://developers.openai.com/api/docs/pricing
- https://ai.google.dev/gemini-api/docs/pricing
- https://groq.com/pricing
- https://api-docs.deepseek.com/quick_start/pricing/
- https://www.lmsys.org/blog/2024-07-01-routellm/
- https://arxiv.org/abs/2410.10347 (Cascade Routing)
- https://dev.to/stella_lin_82914c71e25769/anthropic-prompt-caching-cut-our-rca-cost-by-90-5gmb
- https://blog.logrocket.com/llm-routing-right-model-for-requests/
- https://www.aifreeapi.com/en/posts/claude-api-429-error-fix
- https://tokenmix.ai/blog/claude-api-error-529-overload-strategy-2026
- https://www.morphllm.com/best-ai-model-for-coding

### Related homelab project memories cross-referenced
- `project_hermes_hub.md` — ct-hermes-hub container layout (VMID 163, pve3)
- `project_ai_dev_container.md` — Hermes Agent in the AI Dev Container PRD
- `project_hybrid_gemma_serving.md` — Local Ollama Gemma 3 stack for Tier 4 fallback
- `project_pve3_local_llm.md` — pve3 local-LLM topology

