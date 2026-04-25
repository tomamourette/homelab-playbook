---
type: story
epic: E4
id: E4-S04
title: "Implement daily $1 hard-cap auto-throttle (cron + OpenAI Usage API + ntfy)"
size: 1.5d
priority: COULD
fr_refs: [FR-OBS-002]
adr_refs: [ADR-008]
status: draft
date: 2026-04-25
---

# E4-S04: Implement daily $1 hard-cap auto-throttle (cron + OpenAI Usage API + ntfy)

## User Story

As **tomamourette** (homelab operator), I want **a 30-minute cron loop on `ct-ai-01` that polls the OpenAI Usage API for today's combined LLM + embedding spend, drops Graphiti's `SEMAPHORE_LIMIT` from 5 to 1 when daily aggregate exceeds $1, fires an ntfy alert to my phone via CT101 over Tailscale, and auto-restores `SEMAPHORE_LIMIT=5` at the next UTC day rollover**, so that **chatty Graphiti ingestion bursts cannot silently blow the < $20/month NFR-COST-001 budget, and I get a phone-pushable warning the moment the cap is hit (NFR-COST-002 / FR-OBS-002 / ADR-008)**.

## Background and Context

ADR-008 (closes Q6) is the architectural blueprint: a cron job on `ct-ai-01` polls OpenAI's `/v1/organization/usage/completions` and `/v1/organization/usage/embeddings` endpoints every 30 minutes. If aggregated daily spend > $1, the script edits `/srv/graphiti/.env` to drop `SEMAPHORE_LIMIT=5 → SEMAPHORE_LIMIT=1` and runs `docker compose up -d --no-deps graphiti-mcp` to recreate just the MCP container with the new limit. Restore happens once per UTC day in the post-midnight window. Alerts route via the operator's existing CT101 ntfy at `http://ct101.tail-scale.ts.net/graphiti-alerts` (Tailscale-only, per `project_phone_notifications_tailscale.md`).

Per ADR-014, FR-OBS-002 is downgraded to **COULD** (architecturally specified in ADR-008 but not blocking for product release). Per ADR-008 §Validation, the synthetic-test drill (temporarily set `DAILY_CAP=0.01` to force throttle) is the gate that proves the wiring.

## Acceptance Criteria

### AC1: `cost-cap.sh` is installed at `/srv/graphiti/scripts/cost-cap.sh` mode 755

- **Given** ct-ai-01 has Graphiti deployed (E3-S01) and the directory `/srv/graphiti/scripts/` exists
- **When** I SSH to `ct-ai-01` and run `ls -l /srv/graphiti/scripts/cost-cap.sh`
- **Then** the file exists, mode is `-rwxr-xr-x`, owner is `root` (or the deploy user), and the script header `#!/usr/bin/env bash` is present

### AC2: Script implements the ADR-008 reference behavior verbatim

- **Given** AC1 holds
- **When** I read `/srv/graphiti/scripts/cost-cap.sh`
- **Then** it: (a) reads `DAILY_CAP` (default `1.00`), `COMPOSE_DIR` (`/srv/graphiti`), `NTFY_URL` (default `http://ct101.tail-scale.ts.net/graphiti-alerts`); (b) curls `/v1/organization/usage/completions?start_time=<TODAY>T00:00:00Z` and `/v1/organization/usage/embeddings?start_time=<TODAY>T00:00:00Z` with `Authorization: Bearer $OPENAI_ADMIN_KEY`; (c) sums the `amount.value` fields via `jq`; (d) edits `SEMAPHORE_LIMIT=` in `.env` and runs `docker compose up -d --no-deps graphiti-mcp` when threshold breached; (e) only restores once per UTC day (post-midnight window check `HOUR_UTC -lt 01`); (f) calls ntfy with `Title: Graphiti cost cap` and `Priority: high` on throttle, normal on restore; (g) writes a `logger -t graphiti-cost-cap` line for both transitions

### AC3: `OPENAI_ADMIN_KEY` is in `/srv/graphiti/.env` mode 600 and not committed

- **Given** the deploy user ran the install
- **When** I SSH to ct-ai-01 and run `stat -c '%a %U' /srv/graphiti/.env`
- **Then** mode is `600`, owner is the deploy user; AND `git -C /srv/graphiti log --oneline -- .env 2>&1 | head -1` returns nothing (no commit history — `.env` is never tracked); AND `git -C $REPO_ROOT grep -nF 'OPENAI_ADMIN_KEY=sk-' -- :!**/*.md.j2 :!docs/**` returns 0 matches

### AC4: Cron entry `*/30 * * * *` is registered and visible in `crontab -l`

- **Given** AC1 holds
- **When** I SSH to ct-ai-01 and run `sudo crontab -l -u root` (or the deploy user)
- **Then** the output contains exactly the line:
  ```
  */30 * * * * /srv/graphiti/scripts/cost-cap.sh >> /var/log/graphiti-cost-cap.log 2>&1
  ```
- **And** `ls -l /var/log/graphiti-cost-cap.log` shows the file exists (created on first run) with sane permissions

### AC5: Smoke run — script executes cleanly under cap

- **Given** AC1–AC4 hold and current daily OpenAI spend is < $1
- **When** I run `sudo bash /srv/graphiti/scripts/cost-cap.sh` once manually on ct-ai-01
- **Then** exit code is 0; `/var/log/graphiti-cost-cap.log` shows a parsed total in dollars; `grep SEMAPHORE_LIMIT /srv/graphiti/.env` still shows `=5` (no throttle); no ntfy fired

### AC6: Synthetic breach test — throttle fires when DAILY_CAP=0.01

- **Given** AC5 holds
- **When** I run `sudo DAILY_CAP=0.01 bash /srv/graphiti/scripts/cost-cap.sh` on ct-ai-01
- **Then** within 60 s: (a) `grep SEMAPHORE_LIMIT /srv/graphiti/.env` shows `=1`; (b) `docker compose ps graphiti-mcp` on `/srv/graphiti` shows the container restarted (Created column < 60 s old); (c) `journalctl -t graphiti-cost-cap | tail -1` shows `throttled: $<total>`; (d) `/var/log/graphiti-cost-cap.log` last block shows the throttle path; (e) operator's phone receives an ntfy push titled "Graphiti cost cap" with priority high

### AC7: Auto-restore fires at next UTC day rollover

- **Given** AC6 left `SEMAPHORE_LIMIT=1` in place
- **When** I wait for the next UTC midnight + 30 min (or, for test, manually invoke with `TZ=UTC date` mocked to 00:30Z) and the cron runs the script
- **Then** `grep SEMAPHORE_LIMIT /srv/graphiti/.env` shows `=5`; `docker compose ps graphiti-mcp` shows another restart; `journalctl -t graphiti-cost-cap | tail -1` shows `restored: $<total>`; ntfy push fires with `Title: Graphiti cost cap` and normal priority and body containing "Graphiti restored to SEMAPHORE_LIMIT=5"

### AC8: Script is idempotent — repeated invocations under cap are no-ops

- **Given** AC5 holds and `SEMAPHORE_LIMIT=5`
- **When** I run the script 5 times back-to-back via `for i in 1 2 3 4 5; do sudo bash /srv/graphiti/scripts/cost-cap.sh; done`
- **Then** `.env` and the running container are unchanged across runs; no ntfy storms (i.e., zero ntfy pushes for the 5 invocations under cap)

### AC9: ntfy URL is overridable via env, not hardcoded path

- **Given** AC1 holds
- **When** I run `sudo NTFY_URL=http://ct101.tail-scale.ts.net/test-channel DAILY_CAP=0.01 bash /srv/graphiti/scripts/cost-cap.sh`
- **Then** the ntfy push targets the override URL (the operator can subscribe to the test channel to verify); restore the production URL afterwards

### AC10: Script handles OpenAI Usage API failure gracefully

- **Given** AC1 holds
- **When** I temporarily corrupt the `OPENAI_ADMIN_KEY` (e.g., set to `sk-bad`) in `.env` and run the script
- **Then** the script exits non-zero (because of `set -euo pipefail`), the cron-redirected log captures the curl failure with the HTTP status, NO `.env` mutation occurs, NO ntfy is fired (don't alert-storm on auth failures); a separate `logger -t graphiti-cost-cap-error` line captures the failure

## Implementation Notes

### Script content (verbatim from ADR-008 §Implementation surface, with AC10 robustness add-ons)

```bash
#!/usr/bin/env bash
# /srv/graphiti/scripts/cost-cap.sh
# ADR-008: daily $1 hard-cap autothrottle for Graphiti
set -euo pipefail

# Config (env-overridable for tests)
DAILY_CAP="${DAILY_CAP:-1.00}"
COMPOSE_DIR="${COMPOSE_DIR:-/srv/graphiti}"
NTFY_URL="${NTFY_URL:-http://ct101.tail-scale.ts.net/graphiti-alerts}"
TODAY=$(date -u +%Y-%m-%d)

# Sanity
if [ ! -f "$COMPOSE_DIR/.env" ]; then
  logger -t graphiti-cost-cap-error "missing $COMPOSE_DIR/.env"; exit 2
fi
# Source the admin key without leaking other vars
OPENAI_ADMIN_KEY=$(grep -E '^OPENAI_ADMIN_KEY=' "$COMPOSE_DIR/.env" | cut -d= -f2-)
if [ -z "$OPENAI_ADMIN_KEY" ]; then
  logger -t graphiti-cost-cap-error "OPENAI_ADMIN_KEY missing in .env"; exit 3
fi

# Query usage with timeout + retry-once (eventual-consistency tolerance)
fetch() {
  curl -fsSL --max-time 15 \
    -H "Authorization: Bearer $OPENAI_ADMIN_KEY" \
    "$1" | jq '[.data[] | .results[].amount.value // 0] | add // 0'
}
USAGE_JSON=$(fetch "https://api.openai.com/v1/organization/usage/completions?start_time=${TODAY}T00:00:00Z") || {
  logger -t graphiti-cost-cap-error "completions usage fetch failed"; exit 4
}
EMBED_JSON=$(fetch "https://api.openai.com/v1/organization/usage/embeddings?start_time=${TODAY}T00:00:00Z") || {
  logger -t graphiti-cost-cap-error "embeddings usage fetch failed"; exit 5
}

TOTAL=$(echo "$USAGE_JSON + $EMBED_JSON" | bc -l)
OVER=$(echo "$TOTAL > $DAILY_CAP" | bc -l)
CURRENT_LIMIT=$(grep -E '^SEMAPHORE_LIMIT=' "$COMPOSE_DIR/.env" | cut -d= -f2)

if [ "$OVER" = "1" ] && [ "$CURRENT_LIMIT" != "1" ]; then
  sed -i "s/^SEMAPHORE_LIMIT=.*/SEMAPHORE_LIMIT=1/" "$COMPOSE_DIR/.env"
  ( cd "$COMPOSE_DIR" && docker compose up -d --no-deps graphiti-mcp )
  curl -fsSL -m 10 \
    -d "Graphiti spend cap hit: $TOTAL USD today (>$DAILY_CAP). SEMAPHORE_LIMIT=1." \
    -H "Title: Graphiti cost cap" -H "Priority: high" "$NTFY_URL" || true
  logger -t graphiti-cost-cap "throttled: \$$TOTAL today"
elif [ "$OVER" != "1" ] && [ "$CURRENT_LIMIT" = "1" ]; then
  HOUR_UTC=$(date -u +%H)
  if [ "$HOUR_UTC" -lt "01" ]; then
    sed -i "s/^SEMAPHORE_LIMIT=.*/SEMAPHORE_LIMIT=5/" "$COMPOSE_DIR/.env"
    ( cd "$COMPOSE_DIR" && docker compose up -d --no-deps graphiti-mcp )
    curl -fsSL -m 10 \
      -d "New day, Graphiti restored to SEMAPHORE_LIMIT=5." \
      -H "Title: Graphiti cost cap" "$NTFY_URL" || true
    logger -t graphiti-cost-cap "restored: $TOTAL today"
  fi
fi
```

### Cron registration

Two ways, pick one — the **Ansible role (E4-S07) is canonical**:

1. Manual (for first install / testing): `sudo crontab -e -u root` → add line per AC4.
2. Ansible-managed via `cron` module — implemented in E4-S07's role; this story leaves the manual path documented and tested.

### `OPENAI_ADMIN_KEY` provisioning

The operator generates an **organization admin API key** from the OpenAI dashboard (separate from the regular `OPENAI_API_KEY` Graphiti uses). Scope = `usage` only, no model access. Stored in `/srv/graphiti/.env`:

```
# /srv/graphiti/.env  (mode 600, never committed)
OPENAI_API_KEY=sk-...                # existing — Graphiti's runtime key
OPENAI_ADMIN_KEY=sk-admin-...        # NEW — for cost-cap.sh, usage scope
SEMAPHORE_LIMIT=5
GRAPHITI_TELEMETRY_ENABLED=false
```

For Ansible-driven deploy (E4-S07), the admin key is sourced from the same Sparkle-style ansible-vault pattern.

### ntfy subscription on operator phone

The operator must already be subscribed to `http://ct101.tail-scale.ts.net/graphiti-alerts` in their Android ntfy app — this is the same Tailscale-only path documented in `project_phone_notifications_tailscale.md`. AC6 verifies end-to-end delivery; if missing, operator subscribes once via app QR-code-paste-URL.

### Why post-midnight window for restore

Per ADR-008 §Consequences/Neutral, the restore window (`HOUR_UTC < 01`) is checked once per UTC day to avoid flapping. If the operator throttles at 23:55 UTC and again at 00:05 UTC the next day, the restore sees `OVER=0` and `HOUR_UTC=0` and fires once — clean transition.

### NOT in scope

- Anthropic Usage API polling (Anthropic spend is K3, separate; the operator manually checks per FR-OBS-001 weekly retro). The cap targets OpenAI only because that's where Graphiti spend lives.
- Per-episode cost simulation (rejected per ADR-008 §Alternatives).
- LiteLLM gateway budget guard (Phase 4; FR-LLM-007 conditional; if LiteLLM lands and proves more reliable, ADR-008 §Exit-ramp says retire the cron — this is *not* this story).

## Test Plan

**Pre-flight (parallel; one Bash block on ct-ai-01):**
```bash
ssh ct-ai-01.tail-scale.ts.net 'docker compose -f /srv/graphiti/docker-compose.yml ps'   # graphiti-mcp Up
ssh ct-ai-01.tail-scale.ts.net 'ls -l /srv/graphiti/.env'                                  # mode 600
ssh ct-ai-01.tail-scale.ts.net 'curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $(grep OPENAI_ADMIN_KEY /srv/graphiti/.env | cut -d= -f2)" https://api.openai.com/v1/organization/usage/completions?start_time=$(date -u +%Y-%m-%d)T00:00:00Z'   # 200
ssh ct101.tail-scale.ts.net 'systemctl is-active ntfy'                                     # active (or whatever runs ntfy on CT101)
```

**Install the script (Edit/Write or scp):**
```bash
scp scripts/cost-cap.sh ct-ai-01.tail-scale.ts.net:/srv/graphiti/scripts/cost-cap.sh
ssh ct-ai-01.tail-scale.ts.net 'sudo chmod 755 /srv/graphiti/scripts/cost-cap.sh && sudo chown root:root /srv/graphiti/scripts/cost-cap.sh'
ssh ct-ai-01.tail-scale.ts.net "sudo bash -c 'echo \"*/30 * * * * /srv/graphiti/scripts/cost-cap.sh >> /var/log/graphiti-cost-cap.log 2>&1\" | crontab -u root -'"
ssh ct-ai-01.tail-scale.ts.net 'sudo touch /var/log/graphiti-cost-cap.log && sudo chmod 644 /var/log/graphiti-cost-cap.log'
```

**AC verification (run on ct-ai-01):**
```bash
# AC1
ls -l /srv/graphiti/scripts/cost-cap.sh
# AC2 (review: confirm script body matches Implementation Notes)
diff <(cat /srv/graphiti/scripts/cost-cap.sh) <(cat /path/to/expected.sh)
# AC3
stat -c '%a %U' /srv/graphiti/.env
git -C ~/workspace/homelab/homelab-playbook grep -nF 'OPENAI_ADMIN_KEY=sk-' || echo "0 matches OK"
# AC4
sudo crontab -l -u root | grep cost-cap.sh
# AC5
sudo bash /srv/graphiti/scripts/cost-cap.sh
tail -5 /var/log/graphiti-cost-cap.log
grep SEMAPHORE_LIMIT /srv/graphiti/.env   # =5
# AC6
sudo DAILY_CAP=0.01 bash /srv/graphiti/scripts/cost-cap.sh
sleep 30
grep SEMAPHORE_LIMIT /srv/graphiti/.env   # =1
docker compose -f /srv/graphiti/docker-compose.yml ps graphiti-mcp   # restarted
journalctl -t graphiti-cost-cap | tail -1
# AC6e: confirm phone received ntfy push (manual verification with operator)
# AC7
# Either wait until 00:30 UTC and tail logs, OR mock by manual edit:
sudo sed -i 's/HOUR_UTC=\$(date -u +%H)/HOUR_UTC=0/' /srv/graphiti/scripts/cost-cap.sh
sudo bash /srv/graphiti/scripts/cost-cap.sh
sudo sed -i 's/HOUR_UTC=0/HOUR_UTC=$(date -u +%H)/' /srv/graphiti/scripts/cost-cap.sh   # restore
grep SEMAPHORE_LIMIT /srv/graphiti/.env   # =5
# AC8
for i in 1 2 3 4 5; do sudo bash /srv/graphiti/scripts/cost-cap.sh; done
# Verify no .env churn, no ntfy storm
# AC9
sudo NTFY_URL=http://ct101.tail-scale.ts.net/test-channel DAILY_CAP=0.01 bash /srv/graphiti/scripts/cost-cap.sh
# Restore default cap manually
# AC10
sudo sed -i 's/^OPENAI_ADMIN_KEY=.*/OPENAI_ADMIN_KEY=sk-bad/' /srv/graphiti/.env
sudo bash /srv/graphiti/scripts/cost-cap.sh; echo "exit=$?"
# Restore real key from vault; verify journalctl shows error tag
sudo sed -i 's/^OPENAI_ADMIN_KEY=sk-bad/OPENAI_ADMIN_KEY=<real key from vault>/' /srv/graphiti/.env
journalctl -t graphiti-cost-cap-error | tail -3
```

**Rollback:**
```bash
sudo crontab -u root -l | grep -v 'cost-cap.sh' | sudo crontab -u root -
sudo rm /srv/graphiti/scripts/cost-cap.sh /var/log/graphiti-cost-cap.log
# Revert any .env edits (SEMAPHORE_LIMIT=5)
sudo sed -i 's/^SEMAPHORE_LIMIT=.*/SEMAPHORE_LIMIT=5/' /srv/graphiti/.env
( cd /srv/graphiti && docker compose up -d --no-deps graphiti-mcp )
```

## Dependencies

- **Blocks:** E4-S07 (Ansible role idempotently installs cron + script + admin-key from vault); E4-S11 (KPI K3 measurement validates the cap held during pilot)
- **Blocked by:** E3-S01 (Graphiti deployed and `.env` exists), E3-S04 (`SEMAPHORE_LIMIT=5` baseline set)

## Risks and Mitigations

| Risk | Source | Mitigation |
|---|---|---|
| OpenAI Usage API eventual consistency overshoots cap by cents (AR3 from arch §11) | ADR-008 §Negative | 30-min cadence accepts ~5–15 min lag; documented overshoot is acceptable at $20/mo budget |
| ntfy push lost (phone offline / Tailscale disconnected) | Network | `journalctl -t graphiti-cost-cap` + `/var/log/graphiti-cost-cap.log` are the durable record; AC6 includes weekly retro check that ntfy delivery worked |
| Admin key compromise via .env leak | Security | mode 600, never committed (AC3); separate from runtime API key — admin key is `usage`-scope only, no model/billing-edit |
| `docker compose up -d --no-deps` causes a Graphiti session-mid-flight episode to lose its in-flight LLM call | Restart-during-write | `SEMAPHORE_LIMIT=1` means at most one in-flight call; transient failure is acceptable; episode retry is the operator's responsibility |
| False positive: another OpenAI workload on the same org key triggers throttle | ADR-008 §Reversal trigger | If observed: separate the Graphiti API key onto a child key with its own quota; documented in `_session-log` if it bites |
| Cron timezone mismatch (cron runs in container TZ vs script uses UTC) | OS config | Script uses `date -u +%Y-%m-%d` explicitly; cron's wall-clock cadence (every 30 min) is timezone-independent |

## Definition of Done

- [ ] All ACs pass (AC1–AC10), including AC6 phone-confirmed ntfy delivery
- [ ] `/srv/graphiti/scripts/cost-cap.sh` deployed and executable on ct-ai-01
- [ ] Cron entry registered (visible via `sudo crontab -l`)
- [ ] `OPENAI_ADMIN_KEY` provisioned and stored in `.env` mode 600
- [ ] No regression in Graphiti's normal operation (E3 smoke tests still pass)
- [ ] Repo backup of script committed at `homelab-playbook/scripts/cost-cap.sh` (for E4-S07 Ansible source)
- [ ] Synthetic-breach drill (AC6) recorded in `homelab-playbook/wiki/_session-log.md` with timestamp + ntfy delivery confirmation
- [ ] Cross-reference task added: `AT-FR-OBS-002a` (Phase 5a will populate)
