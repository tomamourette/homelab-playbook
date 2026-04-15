# Story 3.2: Deploy Promtail on ct-media-01 via Ansible Role

**Status:** Done
**Date Completed:** 2026-04-01
**Implements:** FR14, FR18

## Summary

Created the `promtail-media` Ansible role to deploy Promtail as a standalone Docker Compose service on ct-media-01. The role auto-discovers all running containers via Docker socket and pushes stdout/stderr to Loki on ct-docker-01 over cross-host HTTP. Also added a host port binding (3101) to Loki on ct-docker-01 to enable this cross-host communication.

## Files Created

| File | Description |
|------|-------------|
| `ansible/roles/promtail-media/defaults/main.yml` | Role defaults: Promtail image version (3.4.2), Loki URL (192.168.50.194:3101), resource limits (128M/0.5 CPU), host label, paths |
| `ansible/roles/promtail-media/tasks/main.yml` | Role tasks: create directories, template config + compose, ensure Docker, pull image, compose up, health check |
| `ansible/roles/promtail-media/handlers/main.yml` | Restart handler: `docker compose up -d --force-recreate` on config/compose changes |
| `ansible/roles/promtail-media/templates/docker-compose.yml.j2` | Docker Compose template: Promtail container with Docker socket (ro), positions volume, security hardening, health check |
| `ansible/roles/promtail-media/templates/promtail-config.yml.j2` | Promtail config template: Docker SD with 5s refresh, relabel configs matching 3.1, cross-host Loki push URL, host=ct-media-01 label |

## Files Modified

| File | Changes |
|------|---------|
| `stacks/observability/docker-compose.yml` (homelab-apps) | Added `ports:` binding to Loki service: `${LOKI_BIND_ADDRESS:-0.0.0.0}:${LOKI_EXTERNAL_PORT:-3101}:3100` for cross-host Promtail access |

## Files Requiring Manual Update

| File | Required Changes |
|------|-----------------|
| `stacks/observability/.env` (homelab-apps) | Add `LOKI_BIND_ADDRESS=192.168.50.194` (optional, tightens binding to ct-docker-01 IP) and `LOKI_EXTERNAL_PORT=3101` (optional, 3101 is default) |

## Architecture Compliance

| Convention | Status |
|------------|--------|
| Pinned semver image tags (ARCH-1) | Yes -- `grafana/promtail:3.4.2` |
| no-new-privileges + cap_drop ALL (ARCH-2) | Yes -- plus cap_add DAC_READ_SEARCH for Docker socket |
| Ansible role deployed (ARCH-6) | Yes -- `promtail-media` role |
| Standard role structure | Yes -- defaults, tasks, handlers, templates |
| Variables prefixed `promtail_media_` | Yes -- all defaults |
| All tasks tagged `promtail-media` | Yes |
| restart: unless-stopped (NFR-REL-2) | Yes |
| Docker socket read-only (NFR-INT-3) | Yes -- `/var/run/docker.sock:/var/run/docker.sock:ro` |
| Resource limits | Yes -- 128M memory, 0.5 CPU (matching 3.1 Promtail) |
| Health check | Yes -- wget to `/ready` on :9080 |
| json-file log driver with rotation | Yes -- 50m max-size, 3 files |
| Idempotent | Yes -- all tasks are idempotent; re-run produces no changes |

## Acceptance Criteria Verification

1. **Promtail container deployed on ct-media-01 via Docker Compose** -- Yes, `docker compose up -d` in tasks/main.yml
2. **Pushes logs to Loki on ct-docker-01** -- Yes, `promtail_media_loki_url: http://192.168.50.194:3101/loki/api/v1/push`
3. **Discovers all running containers via Docker socket** -- Yes, `docker_sd_configs` with `host: unix:///var/run/docker.sock`, 5s refresh
4. **Standard role structure (tasks, templates, defaults)** -- Yes, plus handlers
5. **Variables prefixed with `promtail_media_`** -- Yes
6. **All tasks tagged with `promtail-media`** -- Yes
7. **Idempotent** -- Yes, all Ansible tasks use declarative modules or `changed_when` guards

## Decisions Made

- D-309 through D-314 (see decision-log.md)

## Review Findings

- R-304: Loki had no host port binding for cross-host access (High, resolved by adding port 3101 binding)
- R-305: No .env file template needed for Promtail (Low, by design -- YAML config, not env vars)
- R-306: No proxy network in compose (Low, by design -- cross-host via host IP, not Docker DNS)

## Dependencies Unlocked

- Story 3.4 (Validate Centralized Logging End-to-End) -- Promtail now running on both hosts
