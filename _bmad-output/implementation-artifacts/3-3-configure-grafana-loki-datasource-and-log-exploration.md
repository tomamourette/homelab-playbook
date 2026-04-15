# Story 3.3: Configure Grafana Loki Datasource and Log Exploration

**Status:** Done
**Date Completed:** 2026-04-01
**Implements:** FR15, FR16

## Summary

Created a Grafana provisioned datasource configuration for Loki, enabling log search and exploration directly from Grafana's Explore panel. The datasource points to `http://loki:3100` on the same Docker `monitoring` network. Grafana auto-provisions this datasource on startup alongside the existing Prometheus datasource, requiring zero manual configuration.

Operators can now use Grafana Explore with LogQL to:
- Search logs by container name (`{container_name="plex"}`)
- Filter by time range using Grafana's time picker
- Search by keyword (`{container_name="plex"} |= "error"`)
- Correlate logs across multiple containers (`{compose_project=~"observability|infra-core"} |= "timeout"`)

## Files Created

| File | Description |
|------|-------------|
| `stacks/observability/config/grafana/provisioning/datasources/loki.yml` | Grafana provisioned datasource for Loki: proxy access mode, http://loki:3100, maxLines 1000, 60s timeout, derived field for container name correlation |

## Files Modified

None. The Grafana service in `docker-compose.yml` already mounts `./config/grafana/provisioning:/etc/grafana/provisioning:ro` (configured in Story 2.1), which includes the `datasources/` directory. No Compose changes needed -- Grafana automatically picks up all YAML files in the provisioning directory on startup.

## Architecture Compliance

| Convention | Status |
|------------|--------|
| Loki as native Grafana datasource (ARCH-INT-4) | Yes -- provisioned via standard Grafana provisioning API |
| LogQL query support (NFR-INT-2) | Yes -- Loki datasource natively supports LogQL in Explore panel |
| Loki internal only (no Traefik exposure) | Yes -- datasource URL uses Docker service name `loki:3100` on internal monitoring network |
| Prometheus remains default datasource | Yes -- `isDefault: false` on Loki; Prometheus retains `isDefault: true` |
| Provisioning directory pattern | Yes -- follows same structure as `prometheus.yml` in same directory |

## Acceptance Criteria Verification

1. **Loki configured as provisioned Grafana datasource** -- Yes, `config/grafana/provisioning/datasources/loki.yml` with `type: loki`, `url: http://loki:3100`
2. **Operator can search logs by container name label** -- Yes, LogQL label selector `{container_name="..."}` works via Grafana Explore; Promtail relabel config (Story 3.1) maps Docker container names to the `container_name` label
3. **Operator can filter by time range and keyword using LogQL** -- Yes, Grafana Explore provides time range picker + LogQL supports `|=` (contains), `|~` (regex), `!=` (not contains) filter expressions
4. **Queries return results within 5 seconds for 30-day ranges (NFR-PERF-2)** -- Supported by Loki filesystem storage mode with TSDB schema and embedded query cache (configured in Story 3.1 loki-config.yml)
5. **Correlated logs across multiple containers in a time window** -- Yes, LogQL supports multi-value label matchers (`{container_name=~"plex|sonarr|radarr"}`) and Grafana Explore displays results in chronological order

## FR Traceability

| FR | How Satisfied |
|----|---------------|
| FR15: Search logs by container name, time range, and keyword from single interface | Loki datasource in Grafana Explore provides container label filtering, time range picker, and LogQL keyword search (`\|=`, `\|~`) |
| FR16: Filter and correlate logs across multiple containers for a specific time window | LogQL regex matchers (`=~`) select multiple containers; Grafana time range restricts window; results displayed chronologically |

## LogQL Quick Reference

For operator convenience, common queries supported by this datasource:

| Use Case | LogQL Query |
|----------|-------------|
| All logs from one container | `{container_name="plex"}` |
| Error logs from one container | `{container_name="plex"} \|= "error"` |
| Logs from a compose project | `{compose_project="observability"}` |
| Logs from multiple containers | `{container_name=~"plex\|sonarr\|radarr"}` |
| Exclude health checks | `{container_name="traefik"} != "healthcheck"` |
| Regex filter | `{host="ct-docker-01"} \|~ "timeout\|connection refused"` |
| Rate of errors (metric) | `rate({container_name="plex"} \|= "error" [5m])` |

## Decisions

| ID | Decision | Confidence | Rationale |
|----|----------|------------|-----------|
| D-315 | Use `isDefault: false` for Loki datasource | 95% | Prometheus is the primary datasource for dashboards and alerts; Loki is secondary for log exploration. Operator selects Loki explicitly in Explore panel. |
| D-316 | Set maxLines to 1000 (not default 5000) | 93% | Balances query performance with result completeness; 1000 lines is sufficient for most debugging sessions; operator can override per-query in Explore UI. |
| D-317 | Set timeout to 60 seconds | 95% | NFR-PERF-2 targets 5s for 30-day queries, but complex regex filters may take longer; 60s provides headroom without leaving connections hanging indefinitely. |
| D-318 | Add derivedFields for container_name correlation | 92% | Enables click-through from log lines to related container context; matches the container_name label set by Promtail relabel config in Story 3.1. |
| D-319 | No custom log exploration dashboard created | 95% | Grafana Explore panel is purpose-built for ad-hoc log exploration with LogQL; a static dashboard would duplicate Explore functionality without adding value. Architecture and PRD both reference "Grafana Explore panel using LogQL" -- not a custom dashboard. |

## Review Findings

| ID | Finding | Severity | Resolution |
|----|---------|----------|------------|
| R-310 | Grafana provisioning directory already mounted read-only in docker-compose.yml (Story 2.1) -- no Compose modifications needed | N/A | Confirmed; new YAML file in datasources/ directory is automatically discovered on Grafana restart |
| R-311 | Prometheus datasource has `editable: true` -- Loki should match for consistency | Low | Set `editable: true` on Loki datasource to match existing Prometheus pattern; allows operator to tweak settings via UI if needed |
| R-312 | Loki datasource URL uses Docker service name `loki` -- requires both services on same Docker network | N/A | Confirmed; both Grafana and Loki are on the `monitoring` network per docker-compose.yml |
