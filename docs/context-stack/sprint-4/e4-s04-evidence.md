# E4-S04 — Daily $1 hard-cap autothrottle (cost-cap.sh + cron + ntfy)

**Sprint 4 / Epic E4 / story 4 — daily Gemini hard-cap implementation per ADR-008 v2**
**Date**: 2026-04-27
**Branch**: `feature/context-stack-e3-graphiti` (homelab-infra + homelab-playbook)
**Status**: DONE — script deployed, cron registered, breach + restore proven end-to-end without burning real Gemini spend.

---

## 1. Why ADR-008 needed amending before code

ADR-008 v1 (2026-04-25) was written when the planned LLM stack still ran Graphiti against OpenAI (`gpt-4o-mini` extraction + `text-embedding-3-small` embeddings). Two follow-on amendments shifted that stack to Gemini:

- E3-S04b (2026-04-26): embeddings moved from `text-embedding-3-small` → `gemini-embedding-2` (per ADR-003 v2).
- E3-S04g (2026-04-26): extraction moved (in plan) from `gpt-4o-mini` → `gemini-2.5-flash-lite` (per ADR-002 amendment, not yet wired as a LiteLLM alias as of this story).

Net effect: **there is no OpenAI traffic on the LiteLLM gateway anymore for Graphiti's hot path**. ADR-008's "OpenAI Usage API" cost source is stale. The story brief explicitly called this out, and the ADR amendment captures the change in §"Amendment 2026-04-27".

## 2. Spend-source endpoint chosen — and why two others didn't work

Investigated three LiteLLM endpoints + two fallbacks:

| Endpoint | Status | Why |
|---|---|---|
| `GET /spend/calculate` | **405 Method Not Allowed** | wrong verb; takes POST per docs but POST hits next row |
| `GET /global/spend?start_date=…` | **500 "No db connected"** | LiteLLM is in stateless mode (no Prisma/SQLite), Story 9.16 deliberately runs without a DB |
| `GET /global/spend/keys` | **500 "No db connected"** | same |
| `GET /global/spend/models` | **500 "No db connected"** | same |
| `GET /spend/logs` | **500 "Database not connected"** | same |
| journald + log parsing | not pursued | LiteLLM logs don't carry per-request cost; only Prometheus does |
| **`GET /metrics` Prometheus counter** | **CHOSEN** | `litellm_spend_metric_total{api_provider="gemini",model=…}` exposed unconditionally with the labels we need |

Sample response (from breach drill, gateway uptime ~5 min, 5 test embeddings):

```
litellm_spend_metric_total{api_key_alias="None",api_provider="gemini",client_ip="127.0.0.1",end_user="None",hashed_api_key="ab32a86b1c7e66eb2bc2a7ab52f1784d00b2455aba9930b65017c315f30feac1",model="gemini-embedding-2",model_id="ed2d53425893783309eef4635265105eccd41ae79083a99aacd3481b818e6b97",org_alias="None",org_id="None",team="None",team_alias="None",user="default_user_id",user_agent="curl/8.14.1",user_email="None"} 0.0000100000
```

Filter: `awk` over `/^litellm_spend_metric_total\{/ && api_provider="gemini"`. Sums across all matching rows. Auto-captures any future `gemini-*` aliases (e.g., `gemini-2.5-flash-lite` when ADR-002 lands) without script edits.

**Caveat captured in script comments**: this is a lifetime cumulative counter that resets on gateway restart. Daily window is computed via a per-day baseline snapshot in `/var/lib/cost-cap/state.json`; counter regression triggers a re-baseline so `today_spend` is never negative.

## 3. Throttle mechanism chosen — and why `rpm: 1` didn't work

Initial design (and brief's own sketch) used per-model `rpm: 1` to throttle. Empirical test on LiteLLM 1.83.13:

```
=== test 3 quick embeddings (rpm=1 should rate-limit some) ===
embed 1: HTTP 200
embed 2: HTTP 200
embed 3: HTTP 200
```

Reading `litellm/proxy/hooks/parallel_request_limiter.py` confirms: per-model `rpm`/`tpm`/`max_parallel_requests` are enforced **only** when a virtual key/team/org budget is in scope (which requires a DB). In stateless mode they're router load-balancing hints, not request rejecters.

The `model/update` admin endpoint (the brief's other suggestion) also requires a DB:

```
POST /model/update -> 500 "No DB Connected. Here's how to do it - https://docs.litellm.ai/docs/proxy/virtual_keys"
```

Pivoted to **YAML comment-out via sentinel markers**: each throttleable Gemini alias lives between `# COST-CAP-START gemini-throttle-target <alias>` / `# COST-CAP-END …` markers in the role-templated `config.yaml`. On breach, every YAML payload line in the block is prefixed with `#@COSTCAP-OFF# `; on restore the prefix is stripped. The alias disappears from `model_list`; calls to it return HTTP 400 "Invalid model name". This is provider-independent, requires no DB, and leaves `gemma4-*` blocks untouched.

Verified directly:

- Throttled `gemini-embedding-2` direct call: **HTTP 400** with body `{"error":{"message":"/embeddings: Invalid model name passed in model=gemini-embedding-2…"}}`.
- Untouched `gemma4-26b-text` chat call: **HTTP 200** (regression test passes).
- `/v1/models` after breach: `['gemma4-auto', 'gemma4-26b-text', 'gemma4-e4b-vision', 'gemma4-26b-json']` — `gemini-embedding-2` correctly absent.
- `/v1/models` after restore: includes `gemini-embedding-2` again.

## 4. ntfy delivery channel — corrected to actual homelab path

Story brief named `192.168.50.101 (CT101)` based on the Phone-Notifications memory. The actual homelab ntfy server runs on **ct-docker-01 (192.168.50.194)** per Story 7.11, with public-DNS HTTPS at `https://ntfy.bi-services.be/`. The `192.168.50.101` IP is unreachable (no route, no host).

Reachability verified from ct-ai-01:

```
curl -sS -m 5 -o /dev/null -w "ntfy.bi-services.be: %{http_code}\n" https://ntfy.bi-services.be/homelab-alerts-low
ntfy.bi-services.be: 200
```

Topics + creds reused from existing Alertmanager → ntfy path:

- `homelab-alerts-urgent` (urgent priority, DND-bypass) for breach.
- `homelab-alerts-default` (warning tier) for restore.
- Auth: `prometheus-bot:<password>` base64-encoded, vault-encrypted as `vault_cost_cap_ntfy_basic_auth` in `host_vars/ct-ai-01/vault.yml` (60 chars when decoded — sanity-checked via `length` filter, content not echoed). Override knobs `vault_cost_cap_ntfy_url_breach` / `…_restore` exist if a dedicated topic is preferred later.

## 5. Ansible role changes (homelab-infra)

Files added/changed in `ansible/roles/litellm-gateway/`:

- `files/cost-cap.sh` — NEW. 12.3 KB executable bash, mode 0750 on host. Polls metrics, computes daily delta, edits config between sentinels, restarts gateway, fires ntfy.
- `templates/litellm-config.yaml.j2` — sentinel markers added around `gemini-embedding-2` block; placeholder block reserved for `gemini-2.5-flash-lite`.
- `templates/cost-cap.cron.j2` — NEW. `/etc/cron.d/cost-cap`, `*/30 * * * *` invoking the script with env file sourced.
- `templates/cost-cap.env.j2` — NEW. `/etc/cost-cap.env` mode 0600. Exports `DAILY_BUDGET_USD`, `THROTTLED_ALIASES`, `NTFY_URL_BREACH/RESTORE`, `NTFY_BASIC_AUTH`, plus knob overrides.
- `tasks/main.yml` — 6 new tasks under tag `litellm-gateway-cost-cap` (also covered by `litellm-gateway`): apt jq+bc, state dir, log file, script copy, env template, cron template.
- `defaults/main.yml` — `cost_cap_*` variables with sane defaults; ntfy URL + basic auth pull from vault.
- `inventories/homelab/host_vars/ct-ai-01/vault.yml` — added `vault_cost_cap_ntfy_basic_auth` (per-key vault-encrypted).

## 6. Ansible deploy outcome

Two play runs:

**Run 1 (cost-cap-only tag):**
```
PLAY RECAP
ct-ai-01                   : ok=7    changed=6    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
```

**Run 2 (full litellm-gateway tag — re-templates config + restarts gateway with new sentinels):**
```
PLAY RECAP
ct-ai-01                   : ok=22   changed=3    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
```

Cron file verbatim from ct-ai-01:

```
# Managed by Ansible — litellm-gateway role / E4-S04 cost-cap (ADR-008 v2)
# Polls every 30 min; reads env from /etc/cost-cap.env.
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
*/30 * * * * root . /etc/cost-cap.env && /usr/local/bin/cost-cap.sh >> /var/log/cost-cap.log 2>&1
```

Permissions verified on ct-ai-01:

```
-rw-------  /etc/cost-cap.env       (mode 600, root-only — holds vault-decoded auth)
-rw-r--r--  /etc/cron.d/cost-cap    (mode 644, world-readable — cron daemon needs)
-rwxr-x---  /usr/local/bin/cost-cap.sh  (mode 750)
-rw-r-----  /var/log/cost-cap.log
drwxr-x---  /var/lib/cost-cap/      (state dir, mode 750)
```

## 7. Breach test outcomes (no real spend burned)

**Trigger method**: option A from the brief — set `DAILY_BUDGET_USD=0.0000005` (5e-7 USD) at script invocation. Today's actual Gemini spend on the gateway after 5 test embeddings was 1.0e-5 USD, well above the simulated cap. No production traffic was diverted; no real-world $1 budget was touched.

### 7.1 Breach script output (verbatim from `/var/log/cost-cap.log`)

```
[2026-04-27T11:31:29+00:00] today_utc=2026-04-27 gemini_total_lifetime_usd=0.0000100000
[2026-04-27T11:31:29+00:00] today_spend_usd=.0000100000 budget_usd=0.0000005 throttled=false
[2026-04-27T11:31:29+00:00] BREACH: today_spend=.0000100000 > budget=0.0000005 — throttling
[2026-04-27T11:31:29+00:00] alias=gemini-embedding-2 throttled (alias removed from model_list)
[2026-04-27T11:31:29+00:00] alias=gemini-2.5-flash-lite throttled (alias removed from model_list)
[2026-04-27T11:31:33+00:00] gateway up (metrics responsive)
[2026-04-27T11:31:33+00:00] ntfy POST https://ntfy.bi-services.be/homelab-alerts-urgent -> 200
```

### 7.2 ntfy alert delivery — confirmed

ntfy POST returned **HTTP 200**. The message body sent (verbatim from script):

> Title: `Cost-cap BREACH`
> Priority: `urgent`
> Body: `Daily Gemini spend $.0000100000 > cap $0.0000005 on ct-ai-01. Throttled aliases (removed from model_list): gemini-2.5-flash-lite gemini-embedding-2. Auto-restore at UTC day rollover.`

### 7.3 Throttle state — Gemini blocked, Gemma untouched

```
--- gemini-embedding-2 block (throttled state) ---
  # COST-CAP-START gemini-throttle-target gemini-embedding-2
#@COSTCAP-OFF#   - model_name: gemini-embedding-2
#@COSTCAP-OFF#     litellm_params:
#@COSTCAP-OFF#       model: gemini/gemini-embedding-2
#@COSTCAP-OFF#       api_key: os.environ/GEMINI_API_KEY
  # COST-CAP-END gemini-throttle-target gemini-embedding-2

--- gemma4-26b-text block (CONTROL — must be unchanged) ---
  - model_name: gemma4-26b-text
    litellm_params:
      model: openai/gemma4-26b-text
      api_base: http://127.0.0.1:8000/v1
      api_key: noop
```

`/v1/models` enumeration **excludes** `gemini-embedding-2`:
```
['gemma4-auto', 'gemma4-26b-text', 'gemma4-e4b-vision', 'gemma4-26b-json']
```

Direct embedding call to throttled alias:
```
gemini-embedding-2 HTTP 400
{"error":{"message":"/embeddings: Invalid model name passed in model=gemini-embedding-2. Call `/v1/models` to view available models for your key.","type":"None","param":"None","code":"400","provider_s…
```

Direct chat call to control alias (Gemma path):
```
gemma4-26b-text HTTP 200
```

### 7.4 Restore path — UTC day rollover simulation

Simulated by tampering `/var/lib/cost-cap/state.json` to set `baseline_date` to yesterday (`2026-04-26`):

```
[2026-04-27T11:31:49+00:00] today_utc=2026-04-27 gemini_total_lifetime_usd=0.0000000000
[2026-04-27T11:31:49+00:00] rebaseline: new UTC day (was=2026-04-26 now=2026-04-27)
[2026-04-27T11:31:49+00:00] day rollover with throttle active — restoring normal limits
[2026-04-27T11:31:49+00:00] alias=gemini-embedding-2 restored (alias re-enabled in model_list)
[2026-04-27T11:31:49+00:00] alias=gemini-2.5-flash-lite restored (alias re-enabled in model_list)
[2026-04-27T11:31:52+00:00] gateway up (metrics responsive)
[2026-04-27T11:31:52+00:00] ntfy POST https://ntfy.bi-services.be/homelab-alerts-default -> 200
[2026-04-27T11:31:52+00:00] baselined: date=2026-04-27 spend=0.0000000000
[2026-04-27T11:31:52+00:00] today_spend_usd=0 budget_usd=1.00 throttled=false
[2026-04-27T11:31:52+00:00] OK: under budget, no action
```

ntfy "RESTORED" delivery: **HTTP 200** to `homelab-alerts-default`. Body:

> Title: `Cost-cap RESTORED`
> Priority: `default`
> Body: `UTC day rollover (2026-04-27). Gemini aliases [gemini-2.5-flash-lite gemini-embedding-2] re-enabled in model_list. Yesterday's lifetime baseline at start of today was $0E-10.`

`/v1/models` after restore lists `gemini-embedding-2` again, and a follow-up embedding call returns **HTTP 200**.

### 7.5 Idempotence — no churn under steady-state budget

5 back-to-back invocations on a stable under-budget state:

```
=== 5x idempotence under budget ===
[2026-04-27T11:32:02+00:00] today_utc=2026-04-27 gemini_total_lifetime_usd=0.0000004000
[2026-04-27T11:32:02+00:00] today_spend_usd=.0000004000 budget_usd=1.00 throttled=false
[2026-04-27T11:32:02+00:00] OK: under budget, no action
… (5 identical no-op log entries)
=== systemd status === active
=== state === { "baseline_date": "2026-04-27", "baseline_spend": 0E-10, "throttled": false }
```

Zero gateway restarts, zero ntfy POSTs, zero state mutations across the 5 runs.

## 8. ADR-008 amendment summary

Single new section appended near the top of ADR-008 (preserves the v1 OpenAI history below for traceability). Captures:

1. Cost source: OpenAI Usage API → LiteLLM `/metrics` Prometheus counter.
2. Throttle: Graphiti SEMAPHORE_LIMIT 5→1 + docker-compose recreate → LiteLLM YAML alias comment-out + `systemctl reload-or-restart litellm-gateway`.
3. Why per-model `rpm` was tried and abandoned (router-only knob in stateless mode).
4. ntfy channel: `ct101.tail-scale.ts.net/graphiti-alerts` → `https://ntfy.bi-services.be/homelab-alerts-{urgent,default}` (correcting an outdated ADR-008 v1 assumption — actual ntfy server is on ct-docker-01).
5. Reversal trigger preserved.

Per ADR amendment policy, the v1 body remains intact below the amendment for traceability; the v1 §Implementation surface bash sketch is no longer the source of truth — the role at `homelab-infra/ansible/roles/litellm-gateway/files/cost-cap.sh` is.

## 9. Anything unexpected

1. **Per-model `rpm: 1` is a no-op without a DB.** Empirically verified — three back-to-back embeddings all returned 200 even with `rpm: 1` set. Pivoted to comment-out (HTTP 400 path) which is unconditional. Documented in the script header and ADR amendment.
2. **`bc` mishandles jq's scientific-notation output.** jq emits `0E-10` for tiny floats; `bc` parses it as a strictly-positive number, breaking the "counter went backward" guard with false positives. Fixed by piping `baseline_spend` through `awk '{printf "%.10f", $0+0}'` before any `bc` comparison.
3. **The story's brief named `192.168.50.101` (CT101) for ntfy.** That host is unreachable from ct-ai-01 (no ICMP response, no HTTP). The actual ntfy server has been on ct-docker-01 (192.168.50.194 / `ntfy.bi-services.be`) since Story 7.11. Wiring the cost-cap to the real homelab ntfy was straightforward; called out in the ADR amendment so the next operator doesn't chase the stale IP.
4. **LiteLLM's `gemini-2.5-flash-lite` alias does NOT yet exist.** ADR-002 has been amended in plan but the alias hasn't been wired into `litellm-config.yaml.j2`. The cost-cap script and config template both treat it as a forward-compat placeholder (sentinel block reserved, name in `THROTTLED_ALIASES` default). When E4-S05 (LiteLLM bridge) or a future E3-S04h adds the alias, the throttle path will Just Work — no code change needed in cost-cap.sh.
5. **State dir + log file naming.** Brief mentioned `/srv/graphiti/scripts/cost-cap.sh` from ADR-008 v1. That path doesn't make sense post-amendment — the script is a LiteLLM-level concern, not a Graphiti-container-level one. Path moved to `/usr/local/bin/cost-cap.sh` (system-managed, role-deployed). State + log under `/var/lib/cost-cap/` and `/var/log/cost-cap.log` — standard FHS locations.

## 10. READY status

- Cron registered, runs `*/30 * * * *` on ct-ai-01.
- `$1/day` cap is the deployed default (override via `cost_cap_daily_budget_usd` host_var or `DAILY_BUDGET_USD` env).
- Throttle target list is parameterized: change `cost_cap_throttled_aliases` host_var and re-template; add a sentinel block in `litellm-config.yaml.j2` for any new alias.
- Breach + restore + ntfy proven end-to-end without burning any meaningful real spend (~$1e-5 used on 5 test embeddings, well inside the daily budget).

**READY for E4-S02** (operator seed picks — independent track) **and E4-S07** (Ansible role for ct-dev-homelab deploy — will reuse this role).
