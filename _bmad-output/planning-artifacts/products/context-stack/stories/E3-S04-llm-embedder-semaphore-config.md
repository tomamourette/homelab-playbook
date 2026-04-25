---
type: story
epic: E3
id: E3-S04
title: "Configure gpt-4o-mini + text-embedding-3-small + SEMAPHORE_LIMIT + telemetry-off + INFO logging"
size: 1d
priority: MUST
fr_refs: [FR-MEM-004, FR-MEM-006, FR-MEM-011, FR-OBS-003]
adr_refs: [ADR-002, ADR-003, ADR-008, ADR-011]
status: draft
date: 2026-04-25
---

# E3-S04: Configure gpt-4o-mini + text-embedding-3-small + SEMAPHORE_LIMIT + telemetry-off + INFO logging

## User Story

As **tomamourette** (homelab operator), I want **the Graphiti MCP container configured with `MODEL_NAME=gpt-4o-mini`, `EMBEDDER_MODEL_NAME=text-embedding-3-small`, `SEMAPHORE_LIMIT=5`, `GRAPHITI_TELEMETRY_ENABLED=false`, INFO-level logging with monthly rotation, and `OPENAI_BASE_URL` left explicit (Phase-1 default = OpenAI; Phase-4-ready)**, so that **Phase 1 cost stays under $1/month at my profile, the cloud privacy line is documented, ingest is throttled below the rate-limit cliff, and the Phase 4 LiteLLM bridge (E4-S05) is a one-env-var flip away (FR-MEM-004, FR-MEM-006, FR-MEM-011, FR-OBS-003 covered)**.

## Background and Context

ADR-002 pins `gpt-4o-mini` as the Phase-1 extraction LLM (~$0.30/month at profile, documented Graphiti default). ADR-003 keeps embeddings on OpenAI `text-embedding-3-small` in **all phases** — small local embedders produce drifted vectors that degrade Graphiti's recall (per maintainer caveat, runbook §4). `SEMAPHORE_LIMIT=5` is the brief §10.1 R6 mitigation against rate-limit chains and runaway spend. Telemetry off is FR-MEM-011 (privacy hygiene). INFO-level logging is the FR-OBS-003 insurance policy for the exit ramp (replay episodes from the log).

This story also pre-stages Phase 4 readiness: the `.env` carries `OPENAI_BASE_URL=https://api.openai.com/v1` explicitly (rather than relying on the SDK default). E4-S05 will flip that single line to point at LiteLLM behind the validation gate; nothing in Phase 1–3 cares about the explicit value.

## Acceptance Criteria

### AC1: `.env` carries the four required model/throttle/telemetry variables

- **Given** the `.env` from E3-S01 (currently has `OPENAI_API_KEY` + `FALKORDB_PASSWORD` only)
- **When** I extend `/srv/graphiti/.env` to include the variables in Implementation Notes
- **Then** these greps all return 1 against the file:
  - `grep -c '^MODEL_NAME=gpt-4o-mini$' /srv/graphiti/.env`
  - `grep -c '^SMALL_MODEL_NAME=gpt-4o-mini$' /srv/graphiti/.env`
  - `grep -c '^EMBEDDER_MODEL_NAME=text-embedding-3-small$' /srv/graphiti/.env`
  - `grep -c '^SEMAPHORE_LIMIT=5$' /srv/graphiti/.env`
  - `grep -c '^GRAPHITI_TELEMETRY_ENABLED=false$' /srv/graphiti/.env`
  - `grep -c '^OPENAI_BASE_URL=https://api.openai.com/v1$' /srv/graphiti/.env`
  - `grep -c '^GRAPHITI_GROUP_ID=tom-personal$' /srv/graphiti/.env`

### AC2: `.env` mode is still 600 after edit

- **Given** AC1
- **When** I run `stat -c '%a' /srv/graphiti/.env`
- **Then** the result is `600`.

### AC3: Container picks up the new env on recreate

- **Given** AC1 + AC2
- **When** I run `cd /srv/graphiti && docker compose --env-file .env up -d`
- **Then** `docker compose exec graphiti-mcp env | grep -E '^(MODEL_NAME|SMALL_MODEL_NAME|EMBEDDER_MODEL_NAME|SEMAPHORE_LIMIT|GRAPHITI_TELEMETRY_ENABLED|OPENAI_BASE_URL|GRAPHITI_GROUP_ID)='` returns the seven expected lines.

### AC4: First add_episode round-trip uses gpt-4o-mini

- **Given** AC3 and Graphiti MCP registered with Claude Code (E3-S02)
- **When** I drive `add_episode(name="phase1-llm-probe", episode_body="LLM-config probe at $(date -Iseconds)", source="text", group_id="tom-personal")` from Claude Code
- **Then** the call returns a UUID **and** OpenAI usage dashboard (or the soon-to-exist `cost-cap.sh` from E4-S04 — for this story, manual check is fine) shows tokens against `gpt-4o-mini` and `text-embedding-3-small` (no `gpt-4o`, no `text-embedding-3-large`).

### AC5: Telemetry endpoint not reached

- **Given** AC3
- **When** I run `docker compose logs graphiti-mcp 2>&1 | head -200` after one ingest
- **Then** no log line references `posthog`, `telemetry.getzep`, or any analytics endpoint (FR-MEM-011 verification).

### AC6: INFO-level logging captured to host

- **Given** AC3 (and a Compose logging-driver section configured per Implementation Notes)
- **When** I run `docker compose logs graphiti-mcp --tail 50` after one ingest
- **Then** at least one INFO-level line per request is present (e.g. `INFO ... POST /mcp/ ... 200`); the log driver is `json-file` with size cap (per Implementation Notes) so monthly rotation is achievable via `docker logrotate` or host-side `logrotate`.

### AC7: Monthly rotation policy documented + cron entry stubbed

- **Given** AC6
- **When** I commit `homelab-playbook/roles/ai-dev-graphiti/files/logrotate-graphiti` with a monthly rotate config and add a stub line to `cron.d/graphiti-backup` (the file E3-S07 will populate with backup crons)
- **Then** the rotate config, when run via `logrotate -d /etc/logrotate.d/graphiti`, dry-runs successfully (debug mode prints intended actions, no errors); cron entry is commented `# (rotate is a SHOULD per ADR-014 / FR-OBS-003)`.

### AC8: Rate-limit headroom verified (informational)

- **Given** AC3 (`SEMAPHORE_LIMIT=5`)
- **When** I drive 10 `add_episode` calls in quick succession from Claude Code (or a `curl` loop hitting the MCP tool endpoint)
- **Then** zero 429 responses appear in `docker compose logs graphiti-mcp` for that window; if 429s appear, drop `SEMAPHORE_LIMIT` to 3 and document.

## Implementation Notes

**`.env` extension (append to E3-S01's `.env`):**

```env
# LLM (ADR-002 — Phase 1 default, swappable in E4-S05 via OPENAI_BASE_URL flip)
MODEL_NAME=gpt-4o-mini
SMALL_MODEL_NAME=gpt-4o-mini

# Embeddings (ADR-003 — stay on OpenAI in ALL phases)
EMBEDDER_MODEL_NAME=text-embedding-3-small

# Throttle (FR-MEM-006, brief §10.1 R6)
SEMAPHORE_LIMIT=5

# Privacy hygiene (FR-MEM-011)
GRAPHITI_TELEMETRY_ENABLED=false

# Phase-4 readiness — explicit, even though it's the SDK default in Phase 1
# E4-S05 flips this single line to the LiteLLM gateway URL behind the
# 95%-well-formed-JSON validation gate.
OPENAI_BASE_URL=https://api.openai.com/v1

# Namespacing (FR-MEM-005 — verified separately in E3-S05)
GRAPHITI_GROUP_ID=tom-personal
```

**Compose logging-driver patch (add under `graphiti-mcp` service in `docker-compose.yml`):**

```yaml
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "5"
        labels: "service=graphiti-mcp"
```

This caps log size at 50 MB per container and gives `logrotate` (or the host's existing rotation pattern) something to grab. INFO-level is the Graphiti MCP server default; no extra env is needed unless the container exposes a log-level override (verify in `docker compose run graphiti-mcp --help`).

**`logrotate` snippet (`homelab-playbook/roles/ai-dev-graphiti/files/logrotate-graphiti`):**

```
/var/lib/docker/containers/*/*-json.log {
    monthly
    rotate 6
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
```

(Operator may already have a global Docker logrotate — if so, this story's contribution is the monthly cadence note in the ai-dev-graphiti role README, not a new file.)

**Why the explicit `OPENAI_BASE_URL` matters in Phase 1:**
- Documented (audit trail makes the Phase-4 flip a one-line diff).
- Some Graphiti versions read the env at startup; setting it explicitly avoids "is the SDK default really still `api.openai.com`?" archaeology in Sprint 4.
- Per ADR-011 fallback path: if Phase 4 fails the validation gate, **reverting is exactly this line** flipping back to `https://api.openai.com/v1`.

## Test Plan

**Pre-flight:**
```bash
ssh ct-ai-01 'cat /srv/graphiti/.env | wc -l'    # baseline line count
ssh ct-ai-01 'docker compose -f /srv/graphiti/docker-compose.yml ps'    # both Up
```

**Apply edits:**
```bash
ssh ct-ai-01 'cd /srv/graphiti && \
  cat >> .env <<EOF
MODEL_NAME=gpt-4o-mini
SMALL_MODEL_NAME=gpt-4o-mini
EMBEDDER_MODEL_NAME=text-embedding-3-small
SEMAPHORE_LIMIT=5
GRAPHITI_TELEMETRY_ENABLED=false
OPENAI_BASE_URL=https://api.openai.com/v1
GRAPHITI_GROUP_ID=tom-personal
EOF
chmod 600 .env'

# AC1
ssh ct-ai-01 'for v in MODEL_NAME=gpt-4o-mini SMALL_MODEL_NAME=gpt-4o-mini \
  EMBEDDER_MODEL_NAME=text-embedding-3-small SEMAPHORE_LIMIT=5 \
  GRAPHITI_TELEMETRY_ENABLED=false OPENAI_BASE_URL=https://api.openai.com/v1 \
  GRAPHITI_GROUP_ID=tom-personal; do
    grep -c "^$v$" /srv/graphiti/.env
done'    # expect: 1 1 1 1 1 1 1

# AC2
ssh ct-ai-01 'stat -c %a /srv/graphiti/.env'    # 600

# AC3 — recreate to pick up env
ssh ct-ai-01 'cd /srv/graphiti && docker compose --env-file .env up -d'
ssh ct-ai-01 'docker compose -f /srv/graphiti/docker-compose.yml exec graphiti-mcp env | \
  grep -E "^(MODEL_NAME|SMALL_MODEL_NAME|EMBEDDER_MODEL_NAME|SEMAPHORE_LIMIT|GRAPHITI_TELEMETRY_ENABLED|OPENAI_BASE_URL|GRAPHITI_GROUP_ID)="'

# AC4 — drive a probe ingest from Claude Code, then check OpenAI usage page
# (manual; see https://platform.openai.com/usage)

# AC5
ssh ct-ai-01 'docker compose -f /srv/graphiti/docker-compose.yml logs graphiti-mcp 2>&1 | \
  grep -iE "posthog|telemetry|getzep.*analytics" | wc -l'    # expect 0

# AC6
ssh ct-ai-01 'docker compose -f /srv/graphiti/docker-compose.yml logs graphiti-mcp --tail 50 | \
  grep -c "INFO"'    # expect >= 1

# AC7
ssh ct-ai-01 'logrotate -d /etc/logrotate.d/graphiti 2>&1 | grep -i error'    # expect empty

# AC8 — burst test
for i in {1..10}; do
  # Drive add_episode from a Claude Code session or a curl loop
  echo "burst $i"
done
ssh ct-ai-01 'docker compose -f /srv/graphiti/docker-compose.yml logs graphiti-mcp 2>&1 | \
  grep -c "429"'    # expect 0 (or < 2)
```

## Dependencies

- **Blocks:** E3-S05 (smoke-tests need a properly-configured ingest path); E3-S07 (backup cron sits in the same `cron.d/` file as the logrotate stub); E3-S09 (K3 spend KPI assumes the Phase-1 cost model holds).
- **Blocked by:** E3-S01 (`.env` exists), E3-S02 (MCP registered so AC4 ingestion path works).

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| `gpt-4o-mini` deprecated mid-pilot (per ADR-002 reversal trigger) | Single env var change to next OpenAI cheap-tier; documented in ADR-002 exit ramp |
| Embedder produces unusable recall (recall-quality regression) | ADR-003 reversal trigger: swap to `text-embedding-3-large` for one-week controlled experiment |
| `SEMAPHORE_LIMIT=5` too aggressive on first day with high-volume seed ingest | AC8 catches 429s; drop to 3 if observed; long-term cap is E4-S04's daily-$1 cost cap (not this story's concern) |
| Telemetry env var doesn't actually disable telemetry (upstream regression) | AC5 verifies log-line absence; if telemetry still fires, file an issue against `getzep/graphiti` and document |
| Compose recreate restarts mid-write (lost in-flight episode) | The MCP server is idempotent on `add_episode` retries; FalkorDB AOF replay covers any pre-fsync writes |
| `OPENAI_BASE_URL` explicit value masks an SDK default change in a future Graphiti version | Acceptable trade-off — explicit is auditable; record the value in the install runbook |

## Definition of Done

- [ ] All ACs (AC1–AC8) pass
- [ ] `.env` extended with seven new lines; mode 600 preserved
- [ ] Compose logging-driver section committed to template
- [ ] `logrotate-graphiti` file committed (or rotation note added to role README)
- [ ] Acceptance test stubs `AT-FR-MEM-004a`, `AT-FR-MEM-006a`, `AT-FR-MEM-011a`, `AT-FR-OBS-003a` referenced in `tests/acceptance.md`
- [ ] One probe `add_episode` reflected on OpenAI usage dashboard against `gpt-4o-mini` (screenshot or dashboard URL recorded)
- [ ] Phase-4 readiness note added to install runbook: "to swap LLM, edit `OPENAI_BASE_URL` in `/srv/graphiti/.env` and `docker compose up -d`"
