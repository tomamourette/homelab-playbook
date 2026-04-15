# Story 2.3: Configure Grafana Alert Rules and Email Notification Channel

**Epic:** 2 - Observability and Alerting
**Status:** done
**Implements:** FR10, FR11, FR12
**Target repo:** homelab-apps

---

## User Story

**As a** homelab operator,
**I want** email notifications when a service goes down or a container restarts unexpectedly,
**So that** I am proactively alerted to issues instead of discovering them manually.

---

## Acceptance Criteria

### AC1: Service down email notification
**Given** the Grafana SMTP notification channel is configured to use `smtp-relay:25`
**When** a service fails health checks for longer than 5 minutes (configurable threshold)
**Then** Grafana sends an email notification with the service name and host

### AC2: Unexpected container restart notification
**Given** a container restarts unexpectedly
**When** the restart is detected by Prometheus (container start time changes > 1 in 15m window)
**Then** an email notification is sent with the container name and instance details
**And** expected restarts (operator-initiated) are suppressed by the 15m windowed change detection

### AC3: Configurable alert suppression
**Given** the operator wants to suppress alerts for a specific service
**When** the alert rule configuration is edited (adding container name to `name!~"..."` regex)
**Then** that service is excluded without affecting other alert rules

### AC4: Disk usage threshold notification
**Given** a disk usage threshold of 80% is configured
**When** any monitored volume exceeds 80%
**Then** an email notification is sent with the volume path and current usage

---

## Technical Context

### Prometheus Alert Rules
- Alert rules loaded from `config/alerting/*.yml` (new) alongside `config/rules/*.yml` (legacy, now emptied)
- Naming convention: `{Domain}{Condition}` per architecture decision
- Evaluation interval: 15s (global setting)

### Grafana Unified Alerting
- Grafana 10+ unified alerting enabled (`GF_UNIFIED_ALERTING_ENABLED=true`)
- Legacy alerting disabled (`GF_ALERTING_ENABLED=false`)
- SMTP configured via `GF_SMTP_*` environment variables pointing to `smtp-relay:25`
- Contact points and notification policies provisioned via YAML files

### SMTP Integration
- Grafana connects to `smtp-relay:25` on the Docker proxy network
- No TLS required (internal network, `GF_SMTP_STARTTLS_POLICY=NoStartTLS`)
- Skip certificate verify enabled (`GF_SMTP_SKIP_VERIFY=true`)

---

## Implementation Plan

### Files Created
1. `stacks/observability/config/alerting/service-alerts.yml` -- Prometheus alert rules: ServiceDown, UnexpectedRestart, ContainerHighMemory, ContainerHighCPU
2. `stacks/observability/config/alerting/disk-alerts.yml` -- Prometheus alert rules: DiskSpaceWarning (>80%), DiskSpaceCritical (>90%)
3. `stacks/observability/config/grafana/provisioning/alerting/contactpoints.yml` -- Grafana email contact point via smtp-relay
4. `stacks/observability/config/grafana/provisioning/alerting/policies.yml` -- Grafana notification policy routing all alerts to email

### Files Modified
1. `stacks/observability/config/prometheus.yml` -- Added `alerting/*.yml` to rule_files glob
2. `stacks/observability/docker-compose.yml` -- Added alerting volume mount to Prometheus, GF_SMTP_* and unified alerting env vars to Grafana
3. `stacks/observability/.env.sample` -- Added GRAFANA_SMTP_HOST, GRAFANA_SMTP_FROM, GRAFANA_SMTP_FROM_NAME, GRAFANA_ALERT_EMAIL_TO variables
4. `stacks/observability/config/rules/homelab-alerts.yml` -- Emptied (replaced by structured alerting/ rules)

### Alert Rules Summary

| Alert | Domain | Threshold | Severity | FR |
|-------|--------|-----------|----------|----|
| ServiceDown | service | `up == 0` for 5m | critical | FR10 |
| UnexpectedRestart | service | `changes(start_time) > 1` in 15m | warning | FR11 |
| ContainerHighMemory | service | >90% of memory limit for 5m | warning | FR10 |
| ContainerHighCPU | service | >80% CPU for 10m | warning | FR10 |
| DiskSpaceWarning | disk | <20% free for 5m | warning | FR10 |
| DiskSpaceCritical | disk | <10% free for 2m | critical | FR10 |

### Suppression Mechanism (FR12)
- **Per-container suppression:** Add container name to `name!~"container1|container2"` regex in alert rule expressions
- **Per-domain suppression:** Add Grafana notification policy sub-routes matching `domain` label with different receiver or mute timing
- **Global suppression:** Grafana mute timings can silence all alerts during maintenance windows

---

## Dev Checklist

- [x] Read existing prometheus.yml, docker-compose.yml, rules/homelab-alerts.yml
- [x] Read architecture for alert naming convention ({Domain}{Condition})
- [x] Read epics for Story 2.3 acceptance criteria and file targets
- [x] Create config/alerting/service-alerts.yml with ServiceDown, UnexpectedRestart, ContainerHighMemory, ContainerHighCPU
- [x] Create config/alerting/disk-alerts.yml with DiskSpaceWarning, DiskSpaceCritical
- [x] Create Grafana provisioning alerting/contactpoints.yml for email contact point
- [x] Create Grafana provisioning alerting/policies.yml for notification routing
- [x] Update prometheus.yml to load alerting/*.yml rule files
- [x] Update docker-compose.yml: add alerting volume mount and GF_SMTP_* env vars
- [x] Update .env.sample with GRAFANA_SMTP_* variables
- [x] Deprecate legacy rules/homelab-alerts.yml to prevent duplicate alerts
- [x] Code review: verify against FR10, FR11, FR12, architecture naming, AC1-AC4
- [x] Apply review fixes (R-206 through R-209)
