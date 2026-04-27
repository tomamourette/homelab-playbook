---
adr: 008
title: "Daily $1 hard-cap implementation via OpenAI Usage API + ct-ai-01 cron throttle"
status: accepted
date: 2026-04-25
authors: tomamourette (via BMAD director Claude)
context_question: Q6
---

# ADR-008: Daily $1 hard-cap implementation via OpenAI Usage API + ct-ai-01 cron throttle

## Amendment 2026-04-27 (E4-S04 — cost source: OpenAI Usage API → LiteLLM /metrics, throttle: docker SEMAPHORE_LIMIT → LiteLLM model_list deactivation)

**Decision change.** Replace "OpenAI Usage API" as the cost source with the
**LiteLLM gateway's Prometheus `/metrics` endpoint** — specifically the
`litellm_spend_metric_total` counter, filtered by `api_provider="gemini"`.
Replace the `SEMAPHORE_LIMIT 5→1 + docker compose up -d --no-deps graphiti-mcp`
throttle with **YAML comment-out (`#@COSTCAP-OFF# `) of the listed Gemini
aliases inside sentinel-marked blocks in `/opt/litellm-gateway/config.yaml`**,
followed by a `systemctl reload-or-restart litellm-gateway`. Calls to
throttled aliases return HTTP 400 ("Invalid model name") which is the
effective rejection. Restore strips the prefix and restarts.

**Why.**
1. **Gemini, not OpenAI.** ADR-002 was amended in E3-S04g to use Gemini
   2.5 Flash-Lite for Graphiti's LLM extraction (instead of gpt-4o-mini);
   ADR-003 v2 already moved embeddings to Gemini Embedding 2 in E3-S04b.
   No OpenAI traffic flows on the Graphiti hot path anymore. The cost
   source must follow.
2. **LiteLLM is stateless (Story 9.16).** `/spend/*`, `/global/spend/*`,
   `/spend/calculate`, and `/model/update` all return 500 "No db connected"
   in stateless mode. Enabling the database adds a Prisma+SQLite migration
   to the role for one feature, with cascading complexity (schema migrations,
   per-key budget enforcement, virtual-key persistence). Out of proportion
   for a $1/day cap. The Prometheus counter is exposed unconditionally and
   has the labels we need (`api_provider`, `model`).
3. **Per-model `rpm`/`tpm`/`max_parallel_requests` are router hints, NOT
   request rejecters.** Verified empirically by reading
   `litellm/proxy/hooks/parallel_request_limiter.py`: enforcement only fires
   when a virtual-key/team budget is in play (which requires a DB). A live
   throttle test with `rpm: 1` on `gemini-embedding-2` allowed three
   back-to-back embeddings to all return 200. Comment-out is the most
   reliable knob without a DB.
4. **No Graphiti container restart (vs ADR-008 v1).** The throttle now
   targets LiteLLM (~3 s downtime, only the Gemini path) rather than
   Graphiti-MCP. Other LiteLLM consumers (Hermes, OWUI, Continue) keep
   working unchanged. `gemma4-*` aliases (local Gemma, $0 cost) are
   explicitly left alone — `cost-cap.sh` filters by `api_provider="gemini"`
   for the spend signal AND only edits the `COST-CAP-START gemini-throttle-target`
   sentinel blocks, not the Gemma blocks.

**Implementation surface.**
- Script: `/usr/local/bin/cost-cap.sh` (deployed by the `litellm-gateway`
  Ansible role, `homelab-infra/ansible/roles/litellm-gateway/files/cost-cap.sh`).
- Cron: `/etc/cron.d/cost-cap` running every 30 min (template
  `templates/cost-cap.cron.j2`).
- Env file: `/etc/cost-cap.env` mode 600, holding budget, alias list,
  ntfy URLs, and base64'd ntfy basic auth (vault-encrypted as
  `vault_cost_cap_ntfy_basic_auth` in `host_vars/ct-ai-01/vault.yml`).
- State: `/var/lib/cost-cap/state.json` — daily baseline + throttled flag.
- Log: `/var/log/cost-cap.log` (mode 0640).
- Sentinel markers in `templates/litellm-config.yaml.j2` around each
  throttleable alias, with the `gemini-2.5-flash-lite` block as a forward-
  compat placeholder for when ADR-002's Flash-Lite extraction lands.

**Spend computation.** `litellm_spend_metric_total` is a lifetime
cumulative counter that resets when the gateway process restarts. The
script snapshots it at the first cron tick of each UTC day and stores
the value as `baseline_spend`; `today_spend = current_total - baseline_spend`.
Counter regression (gateway restart mid-day) triggers a re-baseline so
`today_spend` is never negative. The 30-min cadence accepts ~0.5 USD of
"miss-window" exposure on the worst-case burst — acceptable at $20/mo budget
(NFR-COST-001).

**Throttle mechanism (verified breach test 2026-04-27):**
- BREACH: ntfy "Cost-cap BREACH" → `homelab-alerts-urgent` (urgent priority,
  DND-bypass on phone), 200 OK delivery.
- Throttled alias `/v1/models` → no longer listed; direct call → HTTP 400
  `Invalid model name passed in model=gemini-embedding-2`.
- Control alias `gemma4-26b-text` chat completion → HTTP 200 (no regression).
- RESTORE: ntfy "Cost-cap RESTORED" → `homelab-alerts-default` (warning
  tier), 200 OK. Alias re-listed and HTTP 200 on subsequent embedding
  request.
- Idempotence: 5x back-to-back invocations under budget → 5 logged
  no-op lines, zero gateway restarts, zero ntfy POSTs.

**ntfy delivery channel.** ADR-008 v1 named `http://ct101.tail-scale.ts.net/graphiti-alerts`
as a Tailscale-only path. The actual homelab ntfy server is on
ct-docker-01 (192.168.50.194) per Story 7.11, with a public-DNS HTTPS
endpoint at `https://ntfy.bi-services.be/`. The amendment uses the
existing `homelab-alerts-urgent` (breach) and `homelab-alerts-default`
(restore) topics with the `prometheus-bot` write-credential (basic auth,
60 chars base64) reused from the Alertmanager → ntfy path. No new ntfy
topics or auth surface added.

**Reversal trigger.** If Graphiti ever moves back to OpenAI (unlikely
post-ADR-002 amendment), revisit the cost source — `litellm_spend_metric_total`
will continue to track the new provider tag. If LiteLLM Story 9.18+
enables a database, switch to `/global/spend/keys` for per-virtual-key
spend (cleaner than the Prometheus delta). Either way, the throttle
mechanism (sentinel block comment-out) stays — it's provider-independent.



## Context

PRD FR-OBS-002 / NFR-COST-002 mandate a daily hard-cap: if combined Graphiti-induced spend exceeds $1 in any 24-hour window, ingestion auto-throttles (drop `SEMAPHORE_LIMIT` to 1) and the operator is alerted. PRD Q6 asks the architecture phase to choose between three implementation surfaces:

(a) **Workstation wrapper** polling Anthropic Usage API and killing the daemon — wrong layer; the spend is OpenAI's, not Anthropic's.
(b) **LiteLLM gateway budget guard** — only available in Phase 4 (when `hybrid_gemma_serving` LiteLLM is on the Graphiti path); FR-OBS-002 must work in Phase 1 without LiteLLM.
(c) **Container-side cgroup throttle** — wrong abstraction; cgroups limit CPU/memory, not API spend.

A fourth option emerges from the constraints: **a cron job on `ct-ai-01` that polls the OpenAI Usage API directly and re-deploys the Graphiti container with a lower `SEMAPHORE_LIMIT` when spend crosses the threshold**.

Spend signal source: OpenAI's Usage API (`/v1/organization/usage/completions` and `/v1/organization/usage/embeddings`) returns daily-aggregated cost in dollars; the `start_time` query parameter accepts a date and the response is structured. (Confirmed via OpenAI billing dashboard and platform.openai.com docs.)

Alert channel: the operator's existing Tailscale-reachable ntfy at CT101 (per memory `project_phone_notifications_tailscale.md`) is the natural fit — phone-pushable, no new infrastructure.

## Decision

Implement the $1 daily cap as a **30-minute cron loop on `ct-ai-01` that polls the OpenAI Usage API and updates the Graphiti container's `SEMAPHORE_LIMIT` via docker-compose if the daily spend exceeds threshold**, plus an ntfy push to the operator's phone.

### Implementation surface

`/srv/graphiti/scripts/cost-cap.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

DAILY_CAP="${DAILY_CAP:-1.00}"             # USD
COMPOSE_DIR=/srv/graphiti
NTFY_URL="${NTFY_URL:-http://ct101.tail-scale.ts.net/graphiti-alerts}"
TODAY=$(date -u +%Y-%m-%d)

# Query OpenAI Usage API for today's combined cost
USAGE_JSON=$(curl -fsSL \
  -H "Authorization: Bearer $OPENAI_ADMIN_KEY" \
  "https://api.openai.com/v1/organization/usage/completions?start_time=${TODAY}T00:00:00Z" \
  | jq '[.data[] | .results[].amount.value] | add // 0')

EMBED_JSON=$(curl -fsSL \
  -H "Authorization: Bearer $OPENAI_ADMIN_KEY" \
  "https://api.openai.com/v1/organization/usage/embeddings?start_time=${TODAY}T00:00:00Z" \
  | jq '[.data[] | .results[].amount.value] | add // 0')

TOTAL=$(echo "$USAGE_JSON + $EMBED_JSON" | bc -l)

# Compare; throttle if over
OVER=$(echo "$TOTAL > $DAILY_CAP" | bc -l)
CURRENT_LIMIT=$(grep "SEMAPHORE_LIMIT=" "$COMPOSE_DIR/.env" | cut -d= -f2)

if [ "$OVER" = "1" ] && [ "$CURRENT_LIMIT" != "1" ]; then
  # Throttle: edit .env, recreate Graphiti container only
  sed -i "s/^SEMAPHORE_LIMIT=.*/SEMAPHORE_LIMIT=1/" "$COMPOSE_DIR/.env"
  cd "$COMPOSE_DIR" && docker compose up -d --no-deps graphiti-mcp
  curl -fsSL -d "Graphiti spend cap hit: $TOTAL USD today (>$DAILY_CAP). SEMAPHORE_LIMIT=1." \
    -H "Title: Graphiti cost cap" -H "Priority: high" "$NTFY_URL"
  logger -t graphiti-cost-cap "throttled: \$$TOTAL today"
elif [ "$OVER" != "1" ] && [ "$CURRENT_LIMIT" = "1" ]; then
  # New UTC day → restore default limit
  HOUR_UTC=$(date -u +%H)
  if [ "$HOUR_UTC" -lt "01" ]; then
    sed -i "s/^SEMAPHORE_LIMIT=.*/SEMAPHORE_LIMIT=5/" "$COMPOSE_DIR/.env"
    cd "$COMPOSE_DIR" && docker compose up -d --no-deps graphiti-mcp
    curl -fsSL -d "New day, Graphiti restored to SEMAPHORE_LIMIT=5." \
      -H "Title: Graphiti cost cap" "$NTFY_URL"
    logger -t graphiti-cost-cap "restored: $TOTAL today"
  fi
fi
```

Cron entry:
```
*/30 * * * * /srv/graphiti/scripts/cost-cap.sh >> /var/log/graphiti-cost-cap.log 2>&1
```

`OPENAI_ADMIN_KEY` is a separate **organization admin API key** (not the regular `OPENAI_API_KEY` used by Graphiti) with the `usage` scope. Stored in `/srv/graphiti/.env` mode 600 alongside other secrets; never committed (FR-DEP-008).

### Alerting

Push to the operator's existing CT101 ntfy (Tailscale-reachable). Title: "Graphiti cost cap"; priority: high on throttle, normal on restore.

## Consequences

**Positive.**
- Runs in Phase 1 (no LiteLLM dependency); the same script works through Phase 4.
- Polling every 30 min gives effective resolution — at $1/day, the cap is reached in extreme cases when ~1500 episodes are ingested in a day; the throttle window is fast enough.
- Reuses existing infrastructure: `cron`, `docker compose up -d --no-deps`, ntfy on CT101 — zero new components.
- The "what did it cost yesterday" report is also derivable from the same script — operator-friendly observability.

**Negative.**
- OpenAI Usage API has eventual consistency (~5-15 min lag); the cap may overshoot by a few cents during chatty bursts. Acceptable at $1 granularity.
- Requires an organization admin API key with usage scope — separate from the regular Graphiti `OPENAI_API_KEY`. New secret to manage; mitigated by keeping it in `.env` mode 600.
- 30-min poll cadence is a trade-off: tighter (every 5 min) hammers the OpenAI API; looser (hourly) lets bursts overshoot.

**Neutral.**
- The daily cap is a soft engineering bound; the monthly cap (NFR-COST-001 < $20) remains the primary product-level KPI (K3).
- Restore-default-limit logic only fires once per UTC day to avoid flapping.

## Alternatives Considered

1. **Wrapper script polling Anthropic Usage API and killing the daemon** — rejected. Wrong API; Graphiti spend is OpenAI's. Anthropic Usage API is for Claude Code's own conversation tokens (separate and tracked by K3 directly).
2. **LiteLLM gateway budget guard** — rejected for Phase 1 (no LiteLLM in Phase 1). Worth re-evaluating when Phase 4 lands; if LiteLLM's budget guard is more reliable, swap the cron-polling layer for the gateway-side guard and keep the ntfy alert.
3. **cgroup-based throttle** — rejected. Wrong abstraction; doesn't constrain external API calls.
4. **Hard-stop the container at threshold (vs throttle to LIMIT=1)** — rejected. Throttle keeps Graphiti available for *reads* (which are nearly free, dominated by embedding queries at < $0.01/month) while suppressing chatty *writes*. Hard-stop loses observability of "is Graphiti up" without distinguishing the failure mode.
5. **Pre-spend simulation (block writes that would exceed cap)** — rejected. Requires intercepting Graphiti's prompt-template token counts before sending; intrusive code change in MCP server. Reactive throttling on observed spend is sufficient at single-operator scale.

## Validation / Exit Ramp

- **Validation:**
  - Week 1: cron entry installed; `tail /var/log/graphiti-cost-cap.log` shows successful daily polls.
  - Synthetic test: temporarily set `DAILY_CAP=0.01` in the env for 30 min; verify `SEMAPHORE_LIMIT` drops to 1 and ntfy fires; restore to 1.00.
- **Exit ramp:** if Phase 4 LiteLLM bridge lands and its budget guard is reliable, retire the cron polling and keep only the ntfy alert (still useful for monthly K3 visibility).
- **Reversal trigger:** if the cron throttling causes false positives (e.g., due to other OpenAI usage on the same org key), separate the Graphiti API key from the operator's other workloads onto a child key with its own quota.

## References

- PRD FR-OBS-002, NFR-COST-002
- OpenAI Usage API: <https://platform.openai.com/docs/api-reference/usage>
- Project memory `project_phone_notifications_tailscale.md` (CT101 ntfy)
- `graphiti-claude-code-install-plan-2026-04-25.md` §3 (`SEMAPHORE_LIMIT`), §4 (cost model)
