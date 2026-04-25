---
type: story
epic: E3
id: E3-S01
title: "Stand up Docker Compose stack on ct-ai-01 (FalkorDB + Graphiti MCP)"
size: 1.5d
priority: MUST
fr_refs: [FR-MEM-001, FR-DEP-002, FR-DEP-010]
adr_refs: [ADR-001, ADR-007]
status: draft
date: 2026-04-25
---

# E3-S01: Stand up Docker Compose stack on ct-ai-01 (FalkorDB + Graphiti MCP)

## User Story

As **tomamourette** (homelab operator), I want **a pinned Docker Compose stack at `/srv/graphiti/docker-compose.yml` on `ct-ai-01` that brings up `graphiti-falkordb` and `graphiti-mcp` containers with a mode-600 `.env`, persistent `/srv/graphiti/data` volume, and a working FalkorDB healthcheck**, so that **I have a reproducible, supply-chain-pinned base layer for the Graphiti pilot before any MCP wiring or LLM config (FR-MEM-001, FR-DEP-002, FR-DEP-010 covered)**.

## Background and Context

ADR-001 selects FalkorDB as the Graphiti backend (sub-200 MB RAM, ~1 ms cold-start, vendor-supported compose recipe). The 488-line install runbook at `_bmad-output/planning-artifacts/research/graphiti-claude-code-install-plan-2026-04-25.md` §6 steps 1–7 is the operative procedure; this story executes those steps with two architecture-level deltas (per architecture §8.2): pinned image tags (`zepai/graphiti-mcp:v1.0.2` + a pinned `falkordb/falkordb` tag — FR-DEP-010), and `.env` mode 600 (FR-DEP-002). The `127.0.0.1` bind on `8000`/`6379`/`3000` follows the existing `phone-notifications-tailscale` pattern; the bind change to `0.0.0.0` and Claude Code MCP registration are deferred to E3-S02.

This story is the foundation for E3 — every subsequent E3 story depends on the stack being healthy and the `.env` being writable.

## Acceptance Criteria

### AC1: `/srv/graphiti/` directory layout exists with correct ownership

- **Given** a fresh `ct-ai-01` LXC with Docker + docker-compose installed and Tailscale up
- **When** I run the runbook §6 Step 2 directory bootstrap (`sudo mkdir -p /srv/graphiti/data && sudo chown $USER:$USER /srv/graphiti`)
- **Then** `ls -ld /srv/graphiti /srv/graphiti/data` shows owner = current user (or `$USER:$USER`); `stat -c '%a' /srv/graphiti` shows `755` or stricter.

### AC2: `docker-compose.yml` is committed to `homelab-playbook/roles/ai-dev-graphiti/templates/docker-compose.yml.j2` (or equivalent) with pinned tags

- **Given** the FalkorDB recipe in runbook §2 + architecture §8.2 deltas
- **When** I author `/srv/graphiti/docker-compose.yml` (rendered from the role template) and commit the template to `homelab-playbook`
- **Then** `grep -E "^\s+image:" /srv/graphiti/docker-compose.yml` shows **exactly** these two lines (no `latest`):
  - `image: zepai/graphiti-mcp:v1.0.2`
  - `image: falkordb/falkordb:<pinned-version-or-sha>` (operator picks the latest stable tag at install time and pins by tag, NOT `:latest`)
- **And** `docker compose config` exits 0 (compose file parses).

### AC3: `.env` exists at `/srv/graphiti/.env` with mode 600 and the required variables

- **Given** AC2
- **When** I create `/srv/graphiti/.env` per runbook §6 Step 4 (excluding LLM/embedding tuning, which lives in E3-S04)
- **Then** `stat -c '%a' /srv/graphiti/.env` returns `600`
- **And** `grep -E '^(OPENAI_API_KEY|FALKORDB_PASSWORD)=' /srv/graphiti/.env | wc -l` returns 2 (both populated; `FALKORDB_PASSWORD` generated via `openssl rand -hex 24`)
- **And** `.env` is **not** tracked by git (`git check-ignore /srv/graphiti/.env || echo "outside repo"` — the file lives outside the repo on the host; the repo holds only the template/example).

### AC4: Both containers come up healthy

- **Given** AC2 + AC3
- **When** I run `cd /srv/graphiti && docker compose --env-file .env up -d` (runbook §6 Step 5)
- **Then** `docker compose ps --format json | jq -r '.[].State'` returns `running` for both `graphiti-falkordb` and `graphiti-mcp`
- **And** `docker compose ps --format json | jq -r '.[].Health'` returns `healthy` (or empty for `graphiti-mcp` which has no compose-level healthcheck) for `graphiti-falkordb` within 60 s of `up -d`.

### AC5: FalkorDB responds to `PING`

- **Given** AC4
- **When** I run `docker compose exec falkordb redis-cli -a "$FALKORDB_PASSWORD" PING` (runbook §6 Step 6)
- **Then** the response is exactly `PONG`.

### AC6: Persistent volume survives container recreate

- **Given** AC4
- **When** I run `docker compose down && docker compose --env-file .env up -d` and re-execute AC5
- **Then** `PONG` is returned again **and** `ls -la /srv/graphiti/data` shows `appendonly.aof` (or AOF directory in newer Redis) plus `dump.rdb` (if a snapshot has been taken).

### AC7: Pinned tags surfaced in the runbook

- **Given** ACs 2–6 pass
- **When** I update the install runbook reference card in `homelab-playbook/docs/runbooks/graphiti-install.md` (or seed wiki entry per E4-S02)
- **Then** the recorded tags match exactly what `docker compose images` reports; no `:latest` references remain in any committed playbook artefact.

## Implementation Notes

- **Source of truth for compose layout:** runbook §2.3 (FalkorDB recipe) — copy verbatim, then apply the two deltas in AC2 (image pins) and ADR-007 (which adds `cron.d/graphiti-backup` — that file is created in E3-S07, not here).
- **Image pin verification (closes runbook open-verification step #1):** before `docker compose up -d`, run `docker pull zepai/graphiti-mcp:v1.0.2`. If `manifest unknown`, fall back to runbook §6 Step 4a (local build from `https://github.com/getzep/graphiti.git mcp_server/`). Either path is acceptable for AC2; record the path taken in the install runbook.
- **`falkordb/falkordb` pinning:** check `docker search falkordb/falkordb` and the FalkorDB GitHub releases page; pick the latest tagged release (e.g. `falkordb/falkordb:v4.x.y`) — never `:latest`. Document the chosen tag.
- **Volume mount:** `/srv/graphiti/data:/data` (host:container). Do **not** use a Docker named volume — host bind mount makes ZFS snapshots and ADR-007 backups straightforward.
- **Memory limits:** keep `mem_limit: 1g` on `falkordb` and `mem_limit: 512m` on `graphiti-mcp` per runbook §2.3. NFR-FOOTPRINT-001 (< 200 MB FalkorDB RSS) is verified in E3-S09; the 1 GB compose limit is the ceiling, not the budget.
- **Tailscale plumbing is NOT in scope for this story.** Bind stays at `127.0.0.1` here; E3-S02 flips to `0.0.0.0` after the stack is proven local-healthy.
- **Ansible role `ai-dev-graphiti`:** per architecture §8.3, the long-term home for this compose unit is the `ai-dev-graphiti` role under `homelab-playbook/roles/`. For Sprint 3, hand-rolling the file on `ct-ai-01` is acceptable (the role template is the formal commit); the full role wrap-up lives in E4-S07.

## Test Plan

**Pre-flight on workstation:**
```bash
ssh ct-ai-01 'docker --version && docker compose version'   # expect both
ssh ct-ai-01 'tailscale status | grep -i ct-ai-01'           # expect ts node up
```

**Step-by-step on ct-ai-01:**
```bash
# AC1
sudo mkdir -p /srv/graphiti/data && sudo chown $USER:$USER /srv/graphiti
ls -ld /srv/graphiti /srv/graphiti/data

# AC2 (after committing template + rendering)
cd /srv/graphiti
docker compose config                                        # exit 0
grep -E "^\s+image:" docker-compose.yml                      # exact lines per AC2

# AC3
chmod 600 .env && stat -c '%a' .env                          # 600
grep -cE '^(OPENAI_API_KEY|FALKORDB_PASSWORD)=' .env         # 2

# AC4
docker compose --env-file .env up -d
sleep 30 && docker compose ps --format json | jq -r '.[] | "\(.Name) \(.State) \(.Health)"'

# AC5
docker compose exec falkordb redis-cli -a "$FALKORDB_PASSWORD" PING

# AC6
docker compose down && docker compose --env-file .env up -d
docker compose exec falkordb redis-cli -a "$FALKORDB_PASSWORD" PING
ls -la /srv/graphiti/data | head
```

**Failure-mode probes:**
- If `docker pull zepai/graphiti-mcp:v1.0.2` returns `manifest unknown`: execute runbook §6 Step 4a local-build path; rerun AC2 with the local tag (e.g. `graphiti-mcp:local`); record in story evidence.
- If `PING` fails: `docker compose logs falkordb | tail -50` and check the `REDIS_ARGS=--requirepass` interpolation.

## Dependencies

- **Blocks:** E3-S02 (MCP HTTP transport requires this stack up), E3-S03, E3-S04, E3-S05, E3-S06, E3-S07, E3-S08, E3-S09 — every subsequent E3 story depends on a healthy compose stack.
- **Blocked by:** E1-S02 (settings.json must be free of OMEGA hook entries before any new MCP wiring lands; this story doesn't wire MCP but the next does, and E1 must be merged before E3 begins per epics §5.3).
- **External:** OpenAI API key provisioned (operator); Docker + docker-compose installed on `ct-ai-01` (pre-existing); Tailscale up.

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| `zepai/graphiti-mcp:v1.0.2` not on Docker Hub (closes runbook open-verification #1) | Step 4a local-build fallback documented above; story evidence records the path taken |
| FalkorDB pinned tag drifts (operator picks a tag that gets retracted) | Record SHA digest in install runbook (`docker images --digests falkordb/falkordb`); ADR-007 monthly Cypher export is the disaster-recovery insurance |
| `.env` accidentally committed (FR-DEP-008 violation) | `.env` lives at `/srv/graphiti/.env` on the host; the repo carries only an `env.example` template; pre-push hook from E1-S09 catches `OPENAI_API_KEY=sk-` strings |
| Volume permissions wrong (container UID 999 can't write) | Bind mount + `chown` on the host; if Redis logs `Permission denied`, `sudo chown -R 999:999 /srv/graphiti/data` and document |
| pve3 storage redesign (per memory) moves the LXC; data dir path changes | `/srv/graphiti/data` is intentionally host-side; ZFS snapshot + send pattern (per project memory) carries the data with the container |

## Definition of Done

- [ ] All ACs (AC1–AC7) pass on `ct-ai-01`
- [ ] `docker-compose.yml.j2` template committed to `homelab-playbook/roles/ai-dev-graphiti/templates/` (or interim location) with pinned tags
- [ ] `env.example` committed (no real secrets) showing the required variable set
- [ ] `.env` exists on host with mode 600; **NOT** committed
- [ ] Install evidence (terminal capture of AC4–AC6) archived in story comments or `_bmad-output/evidence/E3-S01.txt`
- [ ] Acceptance test stub `AT-FR-MEM-001a` referenced in `tests/acceptance.md` (populated in P5a)
- [ ] No `:latest` references in any committed compose template or playbook artefact
- [ ] Story status flipped to `done`; `git tag` not required (E3 has no per-story tag like E1's `phase-1-decommission-complete`)
