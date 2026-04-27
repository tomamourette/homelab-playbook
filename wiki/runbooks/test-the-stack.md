---
title: "Test the Context Stack — operator verification runbook"
slug: test-the-stack
category: runbooks
last_reviewed: 2026-04-27
owner: tomamourette
related_pages:
  - index
  - query-hierarchy
  - weekly-observability-digest
  - graphiti-exit-ramp
  - gitnexus-exit-ramp
  - wiki-exit-ramp
  - auto-memory-exit-ramp
related_frs:
  - FR-MEM-009
  - FR-MEM-013
  - FR-MEM-014
  - FR-OBS-001
  - FR-OBS-004
  - NFR-FOOTPRINT-001
related_adrs:
  - ADR-007
  - ADR-008
  - ADR-013
status: stable
supersedes: []
superseded_by: null
---

# Test the Context Stack — operator verification runbook

## Summary

How to verify your Context Stack is healthy and how to exercise each feature
for confidence. Five things to test: **add_memory + search round-trip**,
**similarity search**, **backup**, **rollback**, and **cost-cap**. Use the
60-second health check first; reach for feature tests when something feels
off or before a quarterly drill.

## Context

The stack is deployed in two places:

- **Workstation** — `~/workspace/homelab/homelab-apps/stacks/graphiti/`,
  data dir `~/.graphiti-data`, backups under `~/.local/state/graphiti-backup/`.
- **ct-dev-homelab** (192.168.50.156) — `/srv/graphiti/`, deployed via the
  Ansible `compose-app` role + `deploy-context-stack.yml` playbook.

The cost-cap lives on **ct-ai-01** (192.168.50.160), runs every 30 min via
cron, and watches the LiteLLM gateway's Prometheus counter. The ntfy
delivery channel is `https://ntfy.bi-services.be/` (ct-docker-01 backs it).

Per ADR-013 query-hierarchy, the stack is one of four tiers; this runbook
covers verifying Tier 2 (GitNexus) and Tier 3 (Graphiti) plus their cost-cap
and backup safety nets. Tier 1 (wiki) and Tier 4 (auto-memory) are
file-based and exit-ramp-tested via [wiki-exit-ramp](wiki-exit-ramp) and
[auto-memory-exit-ramp](auto-memory-exit-ramp).

## Procedure

### Prerequisites

- Stack already deployed (workstation OR ct-dev-homelab — see file map below).
- Graphiti MCP server reachable on `127.0.0.1:8000` (workstation) or
  `192.168.50.156:8000` over Tailscale (ct-dev-homelab).
- LiteLLM gateway reachable on `192.168.50.160:4000` (ct-ai-01).
- Vault password handy if you may need to redeploy via Ansible.
- For destructive tests (rollback drill, cost-cap manual breach): SSH into
  the relevant host and a willingness to take a snapshot first.

### 1. Quick-look health check (the 60-second check)

Before drilling into any single feature, confirm everything is up. The
canonical "is the stack healthy?" answer is the [weekly-observability-digest](weekly-observability-digest)
script — run that and read the FalkorDB / GitNexus rows. For an immediate
check without producing a digest, the four commands below are enough:

```bash
# Container status (run on the host where the stack is deployed)
docker ps --filter name=graphiti-mcp --filter name=falkordb \
          --filter name=gitnexus \
          --format 'table {{.Names}}\t{{.Status}}'
# Expect: all three Up (healthy).

# Graphiti health endpoint
curl -sS -o /dev/null -w 'graphiti /health=%{http_code}\n' \
     http://127.0.0.1:8000/health
# Expect: 200.

# LiteLLM gateway liveness (from ANY host on the tailnet)
curl -sS -o /dev/null -w 'litellm /health/liveliness=%{http_code}\n' \
     http://192.168.50.160:4000/health/liveliness
# Expect: 200.

# Last RDB backup timestamp (workstation; ct-dev-homelab paths differ)
ls -la ~/.local/state/graphiti-backup/rdb/latest.rdb
# Expect: symlink to a falkordb-<TS>.rdb dated within the past 7 days.
```

If all four pass, the stack is healthy. If any fails, jump to **§7. What to
do if something's off**.

### 2. Feature tests

Run the test that maps to the question you're trying to answer. Each
section is independent.

#### 2.1 Test add_memory + search round-trip (FR-MEM-009)

Verifies LLM extraction + embedding + FalkorDB persistence + retrieval.

**Pattern** (validated in `docs/context-stack/sprint-3/e3-s04f-retry-evidence.md`):

1. MCP `initialize` → `notifications/initialized` → `tools/call add_memory`.
2. Use an **alphanumeric** `group_id` (e.g., `e4s08test`). Hyphens trigger
   the E3-S04h FalkorDB driver bug — see pitfall below.
3. Wait 30 s for the queue worker to extract + persist (typical 7-15 s end
   to end; ≤ 30 s on first call after a cold restart).
4. `tools/call search_nodes` for a term you placed in the episode body.
5. Expect ≥ 1 node returned with `name` + `uuid` populated.

**Concrete invocation** (the easiest path is the Claude Code MCP tools —
`mcp__graphiti__add_memory` then `mcp__graphiti__search_nodes` — which
handle the JSON-RPC framing for you). For raw curl over the HTTP MCP
endpoint, build the JSON-RPC payload via `python3 -c` to a `/tmp/` file
then `curl -X POST -d @/tmp/payload.json http://127.0.0.1:8000/mcp`.
[adapt for your environment — the exact MCP transport headers (session-id
cookie, accept type) depend on the graphiti-mcp version; the Claude Code
tool wrappers are the load-bearing path.]

**Expected latencies** (from E3-S04f-retry single-episode happy path):

| Phase | Latency |
|---|---|
| `add_memory` HTTP submit | < 1 s |
| Queue worker extract + persist | 7-15 s typical, up to 30 s under load |
| `search_nodes` retrieval | 0.5-1.5 s |

**Pitfall — group_id MUST be alphanumeric.** Values containing hyphens
(`my-test`, `proj-foo`) trigger the E3-S04h FalkorDB driver hyphen-escape
bug at dedup time, returning `RediSearch: Syntax error at offset N near
<frag>`. Workaround: strip separators (`mytest`, `projfoo`). The bug is
provider-agnostic and will bite identically under local-Gemma or
cloud-Gemini extraction. Tracked in the Sprint 3 backlog.

#### 2.2 Test similarity search

Verifies the embedder + retrieval path. Run `search_nodes` with queries
that should hit specific content in your data. Pattern from
`docs/context-stack/sprint-3/e3-s06-evidence.md` Test 2 — adapt the
queries to your corpus:

- **Verbatim factual term** — e.g. "FalkorDB backup retention" → expect
  top-1 to be a FalkorDB-related entity.
- **Multi-word concept** — e.g. "Tailscale phone notifications" → expect
  top-1 to surface the matching entity with full context.
- **Specific entity name** — e.g. "ct-quant-trading container" → expect
  top-1 perfect match.
- **Cross-domain query** — e.g. "cloud disaster recovery vendor selection"
  → expect coherent multi-hop chain.
- **Negative test** — e.g. "canine pets" (no related content) → expect
  weakly-matched fillers, NOT high-confidence garbage.

Acceptance signal: ≥ 4 of 5 queries return a top-1 result that is
defensibly relevant; negative test returns weak fillers only. The
E3-S06 baseline was 4/5 strong top-1 + clean negative test PASS.

#### 2.3 Test backup (ADR-007 amended, FR-MEM-014)

Verifies the three backup layers. Run each manually and inspect artifacts.

```bash
# Layer 2 — daily AOF rewrite (compaction; no on-disk artifact, but verifies
# BGREWRITEAOF returns OK against the live container)
~/workspace/homelab/homelab-apps/stacks/graphiti/scripts/backup-aof-rewrite.sh

# Layer 2 — weekly RDB snapshot (writes to ~/.local/state/graphiti-backup/rdb/)
~/workspace/homelab/homelab-apps/stacks/graphiti/scripts/backup-rdb-snapshot.sh

# Layer 3 — monthly per-graph Cypher export (writes to .../cypher/)
~/workspace/homelab/homelab-apps/stacks/graphiti/scripts/backup-cypher-export.sh

# Verify artifacts
ls -la ~/.local/state/graphiti-backup/rdb/ ~/.local/state/graphiti-backup/cypher/
ls -la ~/.local/state/graphiti-backup/rdb/latest.rdb \
       ~/.local/state/graphiti-backup/cypher/latest.tar.gz
# Expect: symlinks resolve to dated artifacts. RDB ≈ 10 MB; Cypher tarball ≈ 18 MB
# at current data scale. Size grows with corpus.

# Verify the Cypher tarball is well-formed (one nodes file + one edges file
# per graph, plus a MANIFEST.txt)
tar -tzf ~/.local/state/graphiti-backup/cypher/latest.tar.gz | head -20
```

The cron schedule that runs these unattended is documented in
[graphiti-exit-ramp](graphiti-exit-ramp) §5 (cadence) — daily 02:00, weekly
Sunday 03:00, monthly 1st 04:00 — don't restate; just verify cron is
running with `systemctl is-active cron`.

#### 2.4 Test rollback — DESTRUCTIVE — use a test environment

This wipes graph data. **Never run on workstation without a snapshot.**
Reference the [graphiti-exit-ramp](graphiti-exit-ramp) and the validated
restore drill at `docs/context-stack/sprint-3/e3-s08-restore-runbook.md`.
That runbook is already operator-facing — follow it directly.

Two options for safe execution:

1. **ct-dev-homelab** — the Ansible `compose-app` role's `down -v` guard
   enforces two opt-in flags (`down_destructive=true` AND
   `compose_app_force_data_loss=true`) and takes a `cp -a` snapshot before
   destroying volumes. Validated in
   `docs/context-stack/sprint-4/e4-s08-evidence.md` Phase 4. Safest place
   to drill the full restore loop.
2. **Workstation** — take a manual snapshot first:
   `mv ~/.graphiti-data ~/.graphiti-data.preserved-$(date -u +%Y%m%dT%H%M%SZ)`
   then follow the restore runbook. The runbook's Phase 3 covers this same
   step explicitly. Keep the preserved dir for 24 h before deleting.

Acceptance: post-restore, `GRAPH.LIST` returns the expected graphs, the
load-bearing graph has its expected node count, `health=200`, and a fresh
add_memory + search_nodes round-trip succeeds.

#### 2.5 Test cost-cap (manual breach, ADR-008 v2)

Verifies the daily $1 hard-cap detects overrun, throttles the Gemini
aliases, fires ntfy, and restores at UTC day rollover. Pattern from
`docs/context-stack/sprint-4/e4-s04-evidence.md` Phase 7.

**Important — this affects only the `gemini-*` aliases**
(`gemini-embedding-2`, future `gemini-2.5-flash-lite`). The `gemma4-*`
aliases are sentinel-untouched and remain HTTP 200 throughout. Hermes /
OWUI / other Gemma-only consumers see no impact.

```bash
# 1. SSH to ct-ai-01
ssh tomamourette@192.168.50.160

# 2. Sanity — confirm current state is unthrottled
sudo cat /var/lib/cost-cap/state.json
# Expect: { "baseline_date": "<today>", "throttled": false, ... }

# 3. Trigger breach with an absurdly low budget. The script reads
#    DAILY_BUDGET_USD from env, so override for one run only.
sudo bash -c '. /etc/cost-cap.env && DAILY_BUDGET_USD=0.0000005 \
              /usr/local/bin/cost-cap.sh'

# 4. Verify breach logged + ntfy fired + aliases removed from /v1/models
sudo tail -n 20 /var/log/cost-cap.log
# Expect: "BREACH: today_spend=… > budget=…", "alias=gemini-embedding-2 throttled",
#         "ntfy POST … -> 200".

curl -sS -H "Authorization: Bearer <your-master-key>" \
     http://192.168.50.160:4000/v1/models | jq -r '.data[].id'
# Expect: gemini-embedding-2 ABSENT; gemma4-* present.

# 5. Restore — simulate UTC day rollover by tampering state.json
sudo jq '.baseline_date = "2026-04-26"' /var/lib/cost-cap/state.json \
     | sudo tee /var/lib/cost-cap/state.json.new \
     && sudo mv /var/lib/cost-cap/state.json.new /var/lib/cost-cap/state.json
sudo /usr/local/bin/cost-cap.sh
# Expect: log shows "rebaseline: new UTC day", "alias=… restored", "ntfy POST
# .../homelab-alerts-default -> 200". Aliases visible in /v1/models again.

# 6. Confirm
curl -sS -H "Authorization: Bearer <your-master-key>" \
     http://192.168.50.160:4000/v1/models | jq -r '.data[].id'
# Expect: gemini-embedding-2 PRESENT again.
```

Phone should receive two ntfy alerts: one urgent (BREACH on
`homelab-alerts-urgent`) and one default (RESTORED on
`homelab-alerts-default`). Body text is templated from the script — see
the E4-S04 evidence for the exact text. **Never echo the master key in
logs or screenshots.**

### 3. What "healthy" looks like at steady state

Quick reference — what each component should report when nothing is wrong.

| Component | Expected | Where to check |
|---|---|---|
| `graphiti-mcp` container | Up (healthy), `/health=200` | `docker ps`, curl |
| `falkordb` container | Up (healthy) | `docker ps` |
| `gitnexus` container | Up (healthy), MCP responsive | `docker ps`, MCP probe |
| LiteLLM gateway (ct-ai-01) | `/health/liveliness=200` | curl |
| `gemma4-*` aliases | Listed in `/v1/models` | curl `/v1/models` |
| `gemini-embedding-2` alias | Listed in `/v1/models` (UNLESS throttled) | curl `/v1/models` |
| Cron entries on ct-ai-01 | `cost-cap` every 30 min in `/etc/cron.d/cost-cap` | `cat /etc/cron.d/cost-cap` |
| Cron entries on workstation | daily AOF, weekly RDB, monthly Cypher in `crontab -l` | `crontab -l` |
| Backup dir | RDB symlink fresh (≤ 7 days) | `ls -la ~/.local/state/graphiti-backup/rdb/latest.rdb` |
| Cost-cap state | `/var/lib/cost-cap/state.json` shows `"throttled": false` | `sudo cat …` on ct-ai-01 |
| FalkorDB resident memory | < 200 MB (NFR-FOOTPRINT-001) | `docker stats falkordb` |

### 4. What to do if something's off

Prose flowchart — match the symptom on the left, run the fix on the right.

- **`graphiti-mcp` container down or unhealthy**
  Inspect: `docker logs graphiti-mcp --tail 100`. Look for `Successfully
  initialized Graphiti client`, `Using LLM provider: gemini /
  gemini-2.5-flash-lite`, and **no** tracebacks. To bring it back:
  `cd ~/workspace/homelab/homelab-apps/stacks/graphiti/ && docker compose up -d`.
  If the image was rebuilt and lost the `graphiti_mcp_server.py.patched`
  bind-mount, see next bullet.

- **`search_nodes` returns empty for known-good queries**
  Most likely cause (E3-S08.6): `graphiti_mcp_server.py.patched` is no
  longer bind-mounted into the container. Check
  `docker inspect graphiti-mcp | grep -A 5 Mounts` for the patched file.
  If absent, redeploy from a fresh `docker compose up -d` against the
  current `docker-compose.yml` (which mounts the patched server). On
  ct-dev-homelab, re-run `deploy-context-stack.yml` against the host.

- **Cost-cap not firing despite known overrun**
  Check `/var/log/cost-cap.log` on ct-ai-01 for the most recent run
  (cron is `*/30 * * * *`). Confirm the LiteLLM Prometheus counter is
  reachable: `curl http://192.168.50.160:4000/metrics | grep
  litellm_spend_metric_total | head -3`. If the counter is missing or
  zero, the gateway either restarted (counter resets — script
  re-baselines on next run) or is in stateless mode without the
  Prometheus exporter (re-run the `litellm-gateway` Ansible role).

- **Backup directory empty or stale**
  Check `~/.local/state/graphiti-backup/logs/{aof,rdb,cypher}.log` for
  the last cron run. Verify cron is active: `systemctl is-active cron`.
  Run each backup script manually (§2.3) and confirm exit code 0. If
  `BGSAVE` hangs, FalkorDB may be at memory pressure — `docker stats
  falkordb` and consult [graphiti-exit-ramp](graphiti-exit-ramp).

- **Embedder errors in graphiti-mcp logs**
  Symptom: `Connection error` or HTTP 401 on `/embeddings`. Check
  `curl http://192.168.50.160:4000/v1/models` from the graphiti host —
  `gemini-embedding-2` must be in the list. If absent, either the
  cost-cap throttled it (check `/var/lib/cost-cap/state.json`) or the
  alias is missing from the gateway config — run
  `ansible-playbook -i inventories/homelab playbooks/deploy-litellm-gateway.yml
  --tags litellm-gateway` to re-template.

- **`get_episodes` returns `[]` despite known data**
  Known graphiti-mcp v1.26.0 quirk — `get_episodes` filters by
  `episode_id_prefix` which is rarely set. Use `search_nodes` or direct
  Cypher (`docker exec falkordb redis-cli GRAPH.QUERY <group_id>
  "MATCH (n:Episodic) RETURN n LIMIT 10"`) to verify persistence.
  Documented in E4-S08 evidence Phase 3.

### 5. References

Cross-links — no duplication; click through for the full procedure:

- [Query hierarchy](query-hierarchy) — when to ask which tier.
- [Weekly observability digest](weekly-observability-digest) — canonical
  health digest; replaces the §1 quick-look check at retro time.
- [Graphiti tier — exit ramp](graphiti-exit-ramp) — backup cadence,
  recovery, Cypher-export-as-audit-only caveat.
- [GitNexus tier — exit ramp](gitnexus-exit-ramp) — Tier 2 export and
  recovery.
- [Wiki tier — exit ramp](wiki-exit-ramp) — Tier 1 portability.
- [Auto-memory tier — exit ramp](auto-memory-exit-ramp) — Tier 4 portability.
- E3-S08 restore runbook —
  [git:docs/context-stack/sprint-3/e3-s08-restore-runbook.md](git:docs/context-stack/sprint-3/e3-s08-restore-runbook.md).
- E3-S06 functional smoke evidence —
  [git:docs/context-stack/sprint-3/e3-s06-evidence.md](git:docs/context-stack/sprint-3/e3-s06-evidence.md).
- E3-S04f-retry single-episode evidence —
  [git:docs/context-stack/sprint-3/e3-s04f-retry-evidence.md](git:docs/context-stack/sprint-3/e3-s04f-retry-evidence.md).
- E4-S04 cost-cap evidence —
  [git:docs/context-stack/sprint-4/e4-s04-evidence.md](git:docs/context-stack/sprint-4/e4-s04-evidence.md).
- E4-S08 ct-dev-homelab deploy + drill —
  [git:docs/context-stack/sprint-4/e4-s08-evidence.md](git:docs/context-stack/sprint-4/e4-s08-evidence.md).
- ADR-007 (Graphiti backup, amended 2026-04-27 + 2026-04-27b).
- ADR-008 (daily $1 cost cap, amended 2026-04-27 v2).
- ADR-013 (tier-of-truth division).
