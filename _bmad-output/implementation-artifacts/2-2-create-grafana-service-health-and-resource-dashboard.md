# Story 2.2: Create Grafana Service Health and Resource Dashboard

**Epic:** 2 - Observability and Alerting
**Status:** done
**Implements:** FR8, FR9
**Target repo:** homelab-apps

---

## User Story

**As a** homelab operator,
**I want** a single Grafana dashboard showing all service health status and resource utilization,
**So that** I can perform my daily health check in under 90 seconds.

---

## Acceptance Criteria

### AC1: Service health status for all services
**Given** Grafana is running with the Prometheus datasource
**When** the operator opens the Service Health dashboard
**Then** it displays health status (up/down) for all services across both nodes
**And** shows CPU, memory, disk, and network utilization per container and per host
**And** the dashboard loads within 3 seconds (NFR-PERF-1)

### AC2: Dashboard survives restart
**Given** the dashboard JSON is stored in the provisioning directory
**When** Grafana restarts
**Then** the dashboard is automatically re-provisioned (not lost)

---

## Technical Context

### Data Sources
- **cAdvisor** (jobs `cadvisor` and `cadvisor-media`): Per-container CPU, memory, network, disk I/O for ALL containers on both hosts. Primary source for FR8 and FR9 container metrics.
- **node-exporter** (jobs `node-exporter` and `node-exporter-media`): Per-host CPU, memory, disk, network. Provides FR9 host metrics.
- **Prometheus `up` metric**: Scrape target status (up/down) for services with /metrics endpoints.

### Key PromQL Patterns
- Container running status: `container_last_seen{name!=""}` (cAdvisor)
- Container CPU: `rate(container_cpu_usage_seconds_total{name!=""}[5m]) * 100`
- Container memory: `container_memory_usage_bytes{name!=""}`
- Container network: `rate(container_network_receive_bytes_total{name!=""}[5m])`
- Container disk I/O: `rate(container_fs_reads_bytes_total{name!=""}[5m])`
- Host CPU: `100 - (avg by (host) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)`
- Host memory: `100 * (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes))`
- Host disk: `100 - (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"} * 100)`
- Host network: `sum by (host) (rate(node_network_receive_bytes_total{device!~"lo|veth.*|docker.*|br-.*"}[5m]))`

---

## Implementation Plan

### Files Created
1. `stacks/observability/dashboards/service-health.json` — Grafana dashboard JSON (provisioned via bind-mount)

### Files Modified
1. `stacks/observability/docker-compose.yml` — Added `./dashboards:/var/lib/grafana/dashboards:ro` volume mount to Grafana service
2. `stacks/observability/config/grafana/provisioning/dashboards/default.yml` — Updated provisioning path to `/var/lib/grafana/dashboards`

### Dashboard Layout

**Row 1: Service Health Overview**
- Running Containers (total) — stat panel
- ct-docker-01 Containers — stat panel
- ct-media-01 Containers — stat panel
- Scrape Targets Up — stat panel
- Scrape Targets Down — stat panel (red when > 0)
- Restarts (24h) — stat panel (yellow/red thresholds)

**Row 2: All Services Health Table**
- Table showing every container with: Name, Host, Status (UP/DOWN color-coded), CPU %, Memory, Net In, Net Out
- Sorted by status (DOWN first for immediate visibility)

**Row 3: Scrape Target Status + Container Uptime**
- Scrape target table (job, instance, host, UP/DOWN)
- Container uptime table (shortest uptime first — recent restarts visible)

**Row 4: Host Resource Utilization**
- 4 gauge panels: Host CPU, Host Memory, Host Disk (/), Host Network
- 2 time series: Host CPU Over Time, Host Memory Over Time

**Row 5: Container Resource Utilization**
- CPU per container (top 15, time series)
- Memory per container (top 15, time series)
- Network Rx per container (top 10, time series)
- Network Tx per container (top 10, time series)
- Disk Read per container (top 10, time series)
- Disk Write per container (top 10, time series)

**Row 6: Host Disk and Network Detail**
- Host Disk Usage Over Time (with 85% threshold line)
- Host Network Throughput Over Time (Rx + Tx per host)

### Provisioning Strategy
- Dashboard JSON stored in `stacks/observability/dashboards/` (ARCH-8)
- Grafana bind-mounts this directory as `/var/lib/grafana/dashboards`
- Provisioning config `default.yml` points to this path
- Dashboard auto-provisions on Grafana startup/restart
- `allowUiUpdates: true` allows temporary UI edits without losing provisioned version

---

## Dev Checklist

- [x] Read existing docker-compose.yml, provisioning config, prometheus.yml
- [x] Identify all metrics sources (cAdvisor, node-exporter, up metric)
- [x] Design dashboard layout with FR8 (health status) and FR9 (resource utilization) panels
- [x] Create service-health.json with PromQL queries for all panels
- [x] Add dashboards volume mount to Grafana service in docker-compose.yml
- [x] Update provisioning config path to match new mount
- [x] Validate JSON is well-formed
- [x] Code review: verify against FR8, FR9, ARCH-8, NFR-PERF-1
- [x] Apply review fixes
