# Story 3.1: Add Loki and Promtail to Observability Stack on ct-docker-01

**Status:** Done
**Date Completed:** 2026-04-01
**Implements:** FR14, FR17, FR18

## Summary

Added Loki (log aggregation) and Promtail (log collection) services to the existing observability Docker Compose stack on ct-docker-01. Promtail auto-discovers all running containers via Docker socket and pushes stdout/stderr to Loki. Loki stores logs with filesystem backend and 30-day configurable retention.

## Files Created

| File | Description |
|------|-------------|
| `stacks/observability/config/loki-config.yml` | Loki server configuration: single-binary mode, filesystem storage, TSDB schema v13, compactor-based 30-day retention, embedded query cache |
| `stacks/observability/config/promtail-config.yml` | Promtail configuration: Docker service discovery via socket, relabel configs for container/compose labels, host identification label, pipeline stages for JSON log parsing |

## Files Modified

| File | Changes |
|------|---------|
| `stacks/observability/docker-compose.yml` | Added `loki` and `promtail` services with pinned versions, health checks, resource limits, security hardening, monitoring network |

## Files Requiring Manual Update

| File | Required Changes |
|------|-----------------|
| `stacks/observability/.env.sample` | Add variables: `LOKI_VERSION=3.4.2`, `PROMTAIL_VERSION=3.4.2`, `LOKI_DATA=/opt/appdata/observability/loki`, `PROMTAIL_POSITIONS=/opt/appdata/observability/promtail`, `LOKI_MEMORY_LIMIT=512M` (optional), `PROMTAIL_MEMORY_LIMIT=128M` (optional) |

## Architecture Compliance

| Convention | Status |
|------------|--------|
| Pinned semver image tags (ARCH-1) | Yes -- `grafana/loki:${LOKI_VERSION}`, `grafana/promtail:${PROMTAIL_VERSION}` |
| no-new-privileges + cap_drop ALL (ARCH-2) | Yes -- both services |
| Health checks | Yes -- Loki `/ready` on :3100, Promtail `/ready` on :9080 |
| Resource limits | Yes -- Loki 512M/1.0 CPU, Promtail 128M/0.5 CPU (configurable via env) |
| restart: unless-stopped (NFR-REL-2) | Yes -- both services |
| Docker socket read-only (NFR-INT-3) | Yes -- `/var/run/docker.sock:/var/run/docker.sock:ro` |
| Monitoring network | Yes -- both on internal `monitoring` network |
| Loki internal only | Yes -- no Traefik labels, no proxy network |
| json-file log driver with rotation | Yes -- 50m max-size, 3 files |
| Filesystem storage mode | Yes -- per architecture decision |
| 30-day retention (configurable) | Yes -- `retention_period: 720h` in loki-config.yml |

## Acceptance Criteria Verification

1. **Promtail discovers all running containers via Docker socket** -- Yes, `docker_sd_configs` with `host: unix:///var/run/docker.sock`
2. **Promtail pushes stdout/stderr to Loki at loki:3100** -- Yes, `clients.url: http://loki:3100/loki/api/v1/push`
3. **Loki stores logs in /opt/appdata/observability/loki/** -- Yes, `${LOKI_DATA}:/loki:rw` volume mount
4. **Configurable retention (default 30 days)** -- Yes, `retention_period: 720h` with compactor retention enabled
5. **New containers auto-discovered without manual config** -- Yes, Docker SD refreshes every 5s; `promtail_ignore=true` label for opt-out
6. **Pinned semver image tags** -- Yes, via `${LOKI_VERSION}` and `${PROMTAIL_VERSION}` env vars
7. **Read-only Docker socket** -- Yes, `:ro` suffix on socket mount
8. **Resource limits, health checks, restart policy** -- Yes, all three present on both services

## Decisions Made

- D-300 through D-308 (see decision-log.md)

## Review Findings

- R-300: Promtail cap_add DAC_READ_SEARCH (Medium, resolved)
- R-301: Loki volume ownership requirement (Low, documented)
- R-302: Promtail no user directive by design (Low, accepted)
- R-303: .env.sample permission-restricted (Medium, documented manual step)

## Dependencies Unlocked

- Story 3.2 (Deploy Promtail on ct-media-01) -- can now proceed
- Story 3.3 (Configure Grafana Loki Datasource) -- can now proceed
