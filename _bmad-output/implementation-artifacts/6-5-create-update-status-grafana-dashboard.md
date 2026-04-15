# Story 6.5: Create Update Status Grafana Dashboard

**Epic:** 6 - Update Checks
**Status:** done
**Implements:** FR28
**Target repos:** homelab-apps, homelab-infra

---

## User Story

**As a** homelab operator,
**I want** to see current vs. available versions for containers, packages, and tools in Grafana,
**So that** update status is visible during my daily health check.

---

## Acceptance Criteria

### AC1: Prometheus textfile metrics for apt-check (ARCH-7)
**Given** the apt-check script writes metrics to a Prometheus textfile collector `.prom` file
**When** Prometheus scrapes the node-exporter textfile directory
**Then** apt update metrics (upgradable count, last run timestamp, status) are available as Prometheus metrics

### AC2: Prometheus textfile metrics for tool-check (ARCH-7)
**Given** the tool-check script writes metrics to a Prometheus textfile collector `.prom` file
**When** Prometheus scrapes the node-exporter textfile directory
**Then** tool version metrics (outdated count, checked count, last run timestamp, status) are available as Prometheus metrics

### AC3: Grafana dashboard
**Given** the update-status Grafana dashboard is provisioned
**When** the operator views it
**Then** it shows pending apt package updates per host
**And** shows outdated tool counts per host (Terraform, Ansible, Node.js, Docker)
**And** shows container image update notifications from Diun via Loki log panel
**And** shows last check timestamps for apt-check and tool-check
**And** shows summary stats (total upgradable packages, total outdated tools)
**And** shows trend graphs for update counts over time

---

## Implementation Summary

### homelab-infra changes

**Modified:** `ansible/roles/apt-check/templates/apt-check.sh.j2`
- Added `write_textfile_metrics()` function called after successful package count determination
- Added `write_textfile_metrics_failure()` function called on apt-get update failure
- Writes 3 Prometheus gauge metrics to `.prom` file:
  - `apt_check_upgradable_packages` (number of upgradable packages)
  - `apt_check_last_run_timestamp` (unix epoch of last run)
  - `apt_check_last_status` (0=success, 1=failure)
- Atomic write via temp file + `mv` to prevent partial reads
- On failure, preserves previous upgrade count from existing `.prom` file

**Modified:** `ansible/roles/apt-check/defaults/main.yml`
- Added `apt_check_textfile_dir` (default: `/opt/appdata/observability/node-exporter/textfile`)
- Added `apt_check_textfile_file` (default: `apt_check.prom`)

**Modified:** `ansible/roles/apt-check/tasks/main.yml`
- Added task to create the textfile collector directory with correct permissions

**Modified:** `ansible/roles/tool-version-check/templates/tool-check.sh.j2`
- Added `write_textfile_metrics()` function called after tool version comparison
- Writes 4 Prometheus gauge metrics to `.prom` file:
  - `tool_check_outdated_total` (number of outdated tools)
  - `tool_check_checked_total` (number of tools successfully checked)
  - `tool_check_last_run_timestamp` (unix epoch of last run)
  - `tool_check_last_status` (0=success, 1=failure)
- Atomic write via temp file + `mv` to prevent partial reads

**Modified:** `ansible/roles/tool-version-check/defaults/main.yml`
- Added `tool_version_check_textfile_dir` (default: `/opt/appdata/observability/node-exporter/textfile`)
- Added `tool_version_check_textfile_file` (default: `tool_check.prom`)

**Modified:** `ansible/roles/tool-version-check/tasks/main.yml`
- Added task to create the textfile collector directory with correct permissions

### homelab-apps changes

**Created:** `stacks/observability/dashboards/update-status.json`
- Title: "Update Overview" (architecture naming convention: `{Domain} Overview`)
- UID: `homelab-update-overview`
- Datasources: Prometheus (textfile metrics) + Loki (Diun container logs)
- Panels:
  - **Summary row:** APT Packages Upgradable (stat), Tools Outdated (stat), Hosts Reporting OK (stat), Check Failures (stat), Last APT Check (stat, time-since), Last Tool Check (stat, time-since)
  - **Container Image Updates row:** Diun Image Update Notifications (Loki logs panel, queries `container_name=~"diun|diun-media"`)
  - **APT Package Updates row:** Upgradable Packages per Host (stat), APT Check Status by Host (table with upgradable/last-check/status, color-coded)
  - **Tool Version Status row:** Outdated Tools per Host (stat), Tool Check Status by Host (table with outdated/checked/last-check/status, color-coded)
  - **Update Trends row:** APT Upgradable Packages Over Time (timeseries), Outdated Tools Over Time (timeseries)
- Cross-links to Service Health Overview and Backup Overview dashboards
- Refresh: 5m (appropriate for daily metrics)
- Default time range: 24h
- Tags: homelab, updates, diun, apt, tools, overview, fr28

---

## Metrics Approach Decision

**APT packages and tool versions:** Prometheus textfile collector (ARCH-7 pattern, same as restic-backup from Story 5.4). The apt-check and tool-check scripts already run on systemd timers; adding textfile metrics output requires minimal changes and produces structured, queryable Prometheus gauges.

**Diun container image updates:** Loki log panel (hybrid approach). Diun does not expose Prometheus metrics natively, and its state is stored in BoltDB (binary, not scriptable from bash). Since Promtail already collects Diun container logs, the dashboard uses a LogQL query to show recent update notifications. This avoids creating additional infrastructure (scripts, timers, exec commands) solely for metrics extraction. The trade-off is that Diun data is less structured than Prometheus metrics, but it provides the actual update notification content (image names, tags) which is more useful than a bare count.

---

## Decisions

| ID | Decision | Confidence |
|----|----------|------------|
| D-622 | Use Prometheus textfile collector (ARCH-7) for apt-check and tool-check metrics, matching restic-backup pattern from Story 5.4 | 95% |
| D-623 | Use Loki LogQL panel for Diun container image updates instead of creating a separate metrics-extraction script | 92% |
| D-624 | Hybrid datasource dashboard (Prometheus + Loki) — Prometheus for structured apt/tool metrics, Loki for Diun logs | 93% |
| D-625 | Write textfile metrics before email send attempts — metrics should reflect check results regardless of notification delivery | 95% |
| D-626 | apt-check failure handler preserves previous upgrade count from existing .prom file (same pattern as restic-backup preserving last_success_timestamp on failure) | 95% |
| D-627 | Dashboard UID `homelab-update-overview` follows existing pattern (`homelab-backup-overview`, `homelab-service-health`) | 95% |
