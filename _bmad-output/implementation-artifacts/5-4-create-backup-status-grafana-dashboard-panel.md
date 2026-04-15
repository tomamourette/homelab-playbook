# Story 5.4: Create Backup Status Grafana Dashboard Panel

**Epic:** 5 - Backup and Recovery
**Status:** done
**Implements:** FR13
**Target repos:** homelab-apps, homelab-infra

---

## User Story

**As a** homelab operator,
**I want** to see backup job status (last run, success/failure, size) in Grafana,
**So that** backup health is visible during my daily health check.

---

## Acceptance Criteria

### AC1: Prometheus textfile metrics (ARCH-7)
**Given** the Restic backup script writes metrics to a Prometheus textfile collector `.prom` file
**When** Prometheus scrapes the node-exporter textfile directory
**Then** backup metrics (last run timestamp, success/failure, snapshot size, duration) are available as Prometheus metrics

### AC2: Grafana dashboard
**Given** the backup-status Grafana dashboard is provisioned
**When** the operator views it
**Then** it displays last backup time, success/failure status, and snapshot size for each host
**And** failed backups are visually highlighted

---

## Implementation Summary

### homelab-infra changes

**Modified:** `ansible/roles/restic-backup/templates/restic-backup.sh.j2`
- Added `write_textfile_metrics()` function called after backup completion (both success and failure)
- Writes 5 Prometheus gauge metrics to `.prom` file:
  - `restic_backup_last_status` (0=success, 1=failure)
  - `restic_backup_last_success_timestamp` (unix epoch; preserved on failure)
  - `restic_backup_last_duration_seconds`
  - `restic_backup_last_size_bytes` (from `restic stats latest --json`)
  - `restic_backup_snapshots_total` (retention snapshot count)
- Atomic write via temp file + `mv` to prevent partial reads

**Modified:** `ansible/roles/restic-backup/defaults/main.yml`
- Added `restic_backup_textfile_dir` (default: `/opt/appdata/observability/node-exporter/textfile`)
- Added `restic_backup_textfile_file` (default: `restic_backup.prom`)

**Modified:** `ansible/roles/restic-backup/tasks/main.yml`
- Added task to create the textfile collector directory with correct permissions

### homelab-apps changes

**Created:** `stacks/observability/dashboards/backup-status.json`
- Title: "Backup Overview" (architecture naming convention)
- UID: `homelab-backup-overview`
- Panels:
  - **Summary row:** Hosts Backup OK (stat), Hosts Backup Failed (stat), Total Snapshots (stat)
  - **Detail row:** Backup Status by Host (table with status/last-success/duration/size/snapshots, color-coded)
  - **Trends row:** Time Since Last Successful Backup (stat with orange/red thresholds), Backup Size per Host (stat), Backup Duration Over Time (timeseries), Retention Snapshot Count (timeseries)
- Links to Service Health Overview dashboard
- Refresh: 5m (appropriate for nightly metrics)
- Default time range: 24h

**Modified:** `stacks/observability/docker-compose.yml`
- Added `--collector.textfile.directory=/textfile` to node-exporter command
- Added volume mount `/opt/appdata/observability/node-exporter/textfile:/textfile:ro`

---

## Decisions

| ID | Decision | Confidence |
|----|----------|------------|
| D-512 | Enable node-exporter textfile collector via command flag and volume mount | 95% |
| D-513 | Write 5 Prometheus metrics covering all FR13 requirements | 95% |
| D-514 | Configurable textfile path via role defaults | 95% |
| D-515 | Atomic .prom file write via temp file + mv | 95% |
| D-516 | Dashboard title "Backup Overview" per naming convention | 95% |
| D-517 | 5m refresh interval (vs 30s for service-health) | 95% |
| D-518 | Ansible task to create textfile directory | 95% |

## Review Findings

| ID | Finding | Severity | Resolution |
|----|---------|----------|------------|
| R-508 | Inline command substitution for last_success_timestamp in heredoc was fragile | Medium | Pre-computed into variable before heredoc |
| R-509 | `restic stats latest --json` output format may vary | Low | Accepted -- graceful fallback to 0 bytes |
