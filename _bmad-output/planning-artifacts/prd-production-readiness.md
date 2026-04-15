---
stepsCompleted:
  - step-01-init
  - step-02-discovery
  - step-02b-vision
  - step-02c-executive-summary
  - step-03-success
  - step-04-journeys
  - step-05-domain-skipped
  - step-06-innovation-skipped
  - step-07-project-type
  - step-08-scoping
  - step-09-functional
  - step-10-nonfunctional
  - step-11-polish
  - step-12-complete
inputDocuments:
  - docs/index.md
  - docs/project-overview.md
  - docs/architecture-homelab-infra.md
  - docs/architecture-homelab-apps.md
  - docs/architecture-homelab-playbook.md
  - docs/source-tree-analysis.md
  - docs/integration-architecture.md
  - docs/development-guide.md
  - docs/deployment-guide.md
documentCounts:
  briefs: 0
  research: 0
  brainstorming: 0
  projectDocs: 9
workflowType: 'prd'
projectType: 'brownfield'
classification:
  projectType: infrastructure_devops
  domain: general
  complexity: medium
  projectContext: brownfield
  initiative: "Homelab Production Readiness"
  features:
    - disaster_recovery_backup
    - health_dashboard_alerting
    - sso_gateway
    - log_aggregation
    - container_update_checks
---

# Product Requirements Document - Homelab Production Readiness

**Author:** tomamourette
**Date:** 2026-03-30

## Executive Summary

This PRD defines the **Homelab Production Readiness** initiative — five infrastructure capabilities to be deployed *before* Phase 1 application go-live. The homelab currently operates a 2-node Proxmox cluster with 4 containers, 16 Docker Compose stacks defined, and a full IaC pipeline (Terraform + Ansible). The infrastructure is code-complete but lacks the operational foundation needed to run 32 services reliably: no backup for stateful data, no proactive monitoring, no centralized authentication, no unified logging, and no visibility into stale container images.

The goal is a **simpler way of working** — fewer manual checks, fewer login prompts, faster debugging, and confidence that data survives failures. Five capabilities eliminate entire categories of operational risk before they become incidents:

1. **Disaster Recovery & Backup** — Restic backing up all `/opt/appdata/` stateful data nightly with encryption, deduplication, and configurable retention.
2. **Health Dashboard & Alerting** — Prometheus + Grafana observability stack with email notifications for service outages and unexpected container restarts.
3. **SSO Gateway** — Authelia as a single authentication layer in front of all Traefik-routed services, replacing per-service credentials with one login.
4. **Centralized Log Aggregation** — Loki + Promtail integrated with Grafana, providing searchable container logs across all hosts from one dashboard.
5. **Update Checks** — Diun for container image updates plus cron-based system package and tool version checks, with daily digest email.

### What Makes This Special

This isn't about adding complexity — it's about reducing operational burden. Each feature eliminates a class of manual work: backup removes recovery anxiety, monitoring removes "is it still running?" checks, SSO removes credential friction, logging removes cross-container detective work, and update checks remove version staleness. The net result is a homelab that's *simpler to operate* with more services running than it was with fewer.

The core insight: do it right before go-live, not after the first incident.

## Project Classification

- **Project Type:** Infrastructure/DevOps platform (IaC + container orchestration)
- **Domain:** General (self-hosted homelab infrastructure)
- **Complexity:** Medium — multiple integrating systems across 2 nodes, no regulatory requirements, significant operational scope (32 services, 16 stacks)
- **Project Context:** Brownfield — adding production-readiness capabilities to an operational homelab before Phase 1 application deployment
- **Target Repositories:** homelab-infra (Ansible roles/playbooks), homelab-apps (new Docker Compose stacks)

## Success Criteria

### User Success

- **Recovery confidence:** Full restore of any stack's `/opt/appdata/` data completes in under 1 hour from backup, verified by at least one successful test restore before Phase 1 go-live
- **Proactive awareness:** Service outages trigger email notification within 5 minutes of detection
- **Unexpected restart visibility:** Unexpected container restarts generate a notification with context (container name, exit code, timestamp); expected restarts are suppressed
- **Single login:** One authentication to access all Traefik-routed services — no per-service credentials
- **Fast debugging:** Root cause of any service issue identifiable within 5 minutes by searching centralized logs in Grafana
- **Update awareness:** Daily digest email summarizing outdated container images, system packages, and tool versions

### Business Success

- **Operational time reduction:** Daily health check drops from manual spot-checking to glancing at one Grafana dashboard
- **Incident recovery:** First real incident after go-live resolved using backup + logs + monitoring without data loss
- **3-month target:** All 16 stacks running in production with zero undetected outages and zero unrecoverable data events

### Technical Success

- **Backup coverage:** All `/opt/appdata/` paths on both ct-docker-01 and ct-media-01 backed up nightly with configurable retention
- **Monitoring coverage:** Prometheus scraping all 32 services + host metrics on both nodes
- **Log coverage:** All container stdout/stderr collected by Promtail and queryable in Loki via Grafana
- **SSO coverage:** Authelia protecting all Traefik-routed endpoints (20+ services)
- **Update coverage:** Container images, apt packages on containers/nodes, and tool versions checked daily

### Measurable Outcomes

| Metric | Target | Measurement |
|--------|--------|-------------|
| Backup RTO | < 1 hour per stack | Timed test restore |
| Alert latency | < 5 minutes | Simulated service kill → email received |
| Login count per session | 1 (SSO) | Manual verification |
| Log search to root cause | < 5 minutes | Simulated failure scenario |
| Update visibility lag | < 24 hours | Check notification freshness |

## User Journeys

### Journey 1: Daily Health Check — "Is everything still running?"

Tom, weekday morning, coffee in hand. He opens Grafana — already authenticated via SSO from an earlier session. The overview dashboard shows all 32 services across both nodes: green dots, resource utilization normal, no alerts fired overnight.

He glances at the backup panel — last night's run completed at 02:15, all `/opt/appdata/` paths backed up, retention policy holding 7 daily + 4 weekly snapshots. The update digest widget shows 2 container images have newer versions and 1 apt package update pending. Nothing critical.

Total time: **90 seconds**. Tab closed, on with the day.

**Capabilities revealed:** Grafana dashboard with service status overview, backup status panel, update digest integration, SSO session persistence.

### Journey 2: Incident Response — "Plex is down, what happened?"

Saturday evening. Tom gets an email: "Service Down: media-plex on ct-media-01". The alert fired 3 minutes after Plex stopped responding to health checks.

He opens Grafana (already logged in via SSO), clicks to the Plex panel — container exited with code 137 (OOM killed). Switches to Loki, filters `container=plex` in the last 30 minutes — memory spiking during a 4K hardware transcode.

He SSHs to ct-media-01, bumps the Plex memory limit from 4GB to 6GB, runs `docker compose up -d`. Service returns green in Grafana within 60 seconds.

Total time from alert to resolution: **under 5 minutes**.

**Capabilities revealed:** Email alerting with service/host context, Loki log search by container, Grafana resource panels, SSO removing login friction during incidents.

### Journey 3: Disaster Recovery — "ct-docker-01 disk failed"

Tuesday. ct-docker-01 is unreachable after a disk failure on pve1.

Tom provisions a fresh ct-docker-01 using Terraform + Ansible (10 minutes). Docker running but no application data. He lists Restic snapshots — most recent from 02:15 last night. Restores `/opt/appdata/` from the snapshot.

Traefik certificates, Portainer data, Prometheus history, Grafana dashboards, Pi-hole config, n8n workflows, Organizr settings, CouchDB data — all restored. He runs `docker compose up -d` per stack. Services return online with yesterday's state.

Total time from fresh container to full service restoration: **under 1 hour**.

**Capabilities revealed:** Restic nightly snapshots, full `/opt/appdata/` restore, integration with IaC rebuild workflow, retention policy for recent recovery points.

### Journey 4: New Stack Onboarding — "I just added Immich for photos"

Weekend project. Tom creates the Docker Compose file following existing conventions, adds Traefik labels, deploys. On first access to `immich.bi-services.be`, SSO intercepts — he's already logged in from Grafana, passes straight through. No new password.

Promtail auto-discovers the new container's logs. Prometheus scrapes it if `/metrics` is exposed. The update check tool detects the new image for tomorrow's digest. Tom adds one line for the backup path.

The only manual step: adding the backup path. SSO, logging, monitoring, update checks — all automatic for any new Traefik-routed container.

**Capabilities revealed:** SSO auto-protecting new services, Promtail auto-discovering containers, update check auto-detecting images, backup requiring explicit path addition for new stacks.

### Journey Requirements Summary

| Journey | Primary Capabilities | Key Requirement |
|---------|---------------------|-----------------|
| Daily Health Check | Grafana dashboard, backup status, update digest, SSO | Single-pane overview of all services, backups, and updates |
| Incident Response | Email alerts, Loki log search, Grafana panels, SSO | < 5 min alert-to-root-cause with container-level filtering |
| Disaster Recovery | Restic backup, IaC rebuild, snapshot restore | < 1 hour full stack restore from nightly snapshot |
| New Stack Onboarding | SSO auto-protect, Promtail auto-discover, update auto-detect | Zero-config for logging/SSO/updates; one-line for backup |

## Infrastructure-Specific Requirements

### Backup Architecture

- **Tool:** Restic (encrypted, deduplicated, incremental backups)
- **MVP Target:** Local disk on Proxmox host (LVM-thin storage pool)
- **Scope:** All `/opt/appdata/` paths on ct-docker-01 and ct-media-01
- **Schedule:** Nightly (02:00), configurable via cron or systemd timer
- **Retention:** 7 daily, 4 weekly, 3 monthly snapshots
- **Restore:** CLI-based restore to original or alternate path
- **Validation:** At least one test restore before Phase 1 go-live
- **Future Migration:** Restic supports switching backend (local → NAS → S3) without reconfiguring backup jobs
- **Deployment:** Ansible-managed cron job on each host

### Email / SMTP Relay

- **New requirement:** No existing SMTP relay — must be provisioned as part of this initiative
- **Options:** Lightweight relay container or Ansible-configured `msmtp` on hosts
- **Scope:** Outbound-only relay for alert emails from Grafana, n8n, Diun, and backup reports
- **No inbound email needed** — notification delivery only
- **Alternative:** Direct SMTP via Gmail/Outlook app password (simplest MVP)

### SSO Gateway

- **Tool:** Authelia (lightweight, single binary, YAML config)
- **Rationale:** Single-user homelab — Authentik's PostgreSQL dependency is overkill
- **Integration:** Traefik forward-auth middleware — every Traefik-routed service protected automatically
- **Authentication:** Username/password with optional TOTP 2FA
- **Session:** Persistent cookie — one login covers all services
- **Configuration:** YAML-based, stored in `/opt/appdata/authelia/`
- **Deployment:** New stack on ct-docker-01, integrated with existing infra-core Traefik config

### Logging Stack

- **Extend existing:** Add Loki + Promtail to `stacks/observability/` Docker Compose file
- **Loki:** Log storage and query engine, integrated as Grafana datasource
- **Promtail:** Docker log discovery — auto-collects stdout/stderr from all containers
- **Deployment:** Promtail on both ct-docker-01 and ct-media-01
- **Retention:** Configurable (start with 30 days, tune based on disk usage)
- **Query:** Via Grafana Explore panel using LogQL

### Update Check System

- **Tool:** Diun (Docker Image Update Notifier)
- **Container images:** All running containers on both hosts
- **System packages:** `apt` update check via cron script on all containers + both Proxmox nodes
- **Tool versions:** Terraform, Ansible, Node.js, Docker checked against latest releases
- **Notification:** Daily digest email (aggregated)
- **Deployment:** Diun container on each host + Ansible-managed cron for apt/tool checks

### Implementation Considerations

- **Stack placement:** Authelia, SMTP relay, and Diun on ct-docker-01; Promtail on both hosts; Restic on both hosts
- **Ansible automation:** Backup cron jobs, Promtail agents, apt check scripts, and msmtp config managed via Ansible roles
- **Existing stack modifications:** observability stack gains Loki + Promtail; infra-core gains Authelia forward-auth middleware
- **New stacks:** authelia, smtp-relay (if containerized), update-checks (Diun)
- **Config management:** All new `.env.sample` files following existing homelab-apps conventions

## Project Scoping & Phased Development

### MVP Strategy

**Approach:** Incremental problem-solving — deploy each capability independently, validate, move to the next. No big-bang deployment.

**Resource Requirements:** Single operator (Tom) + Claude Code CLI for IaC generation.

### MVP Deployment Order

Each step delivers standalone value:

1. **SMTP Relay** — Prerequisite for all notifications. Smallest scope, fastest win.
2. **Observability + Alerting** — Deploy existing Prometheus/Grafana stack with email alert rules. Immediate visibility.
3. **Logging (Loki + Promtail)** — Extend observability stack. Enables "debug in 5 minutes" journey.
4. **Authelia SSO** — Forward-auth middleware in Traefik. One login for everything.
5. **Backup (Restic)** — Nightly backup of all `/opt/appdata/`. Test restore validates disaster recovery.
6. **Update Checks (Diun)** — Container image + system package notifications. Daily digest email.

### Post-MVP Features

**Phase 2 (Growth):**
- Migrate backup target from local disk to NAS (when new node added)
- Per-service Grafana dashboards with tuned thresholds
- Native OIDC for Grafana, n8n, Portainer
- Log retention policies and pattern-based alerting
- Automated apt upgrade reports with diff

**Phase 3 (Expansion):**
- One-click disaster recovery playbook (Ansible-based full restore)
- Self-healing via n8n workflows (auto-restart, auto-scale)
- Renovate/Dependabot for Docker image version PRs in homelab-apps
- Drift detection integration (Stories 1.2-1.4)

### Risk Mitigation

**Technical Risks:**
- *Promtail on LXC containers:* Docker socket access may need configuration → test early, fall back to syslog driver
- *Authelia + Traefik:* Forward-auth middleware requires precise label config → validate with one service before rollout
- *Restic on shared storage:* Backup I/O impact → schedule at 02:00, monitor with Prometheus

**Resource Risks:**
- *Disk space:* Monitor consumption via Prometheus alerts at 80% threshold
- *Single operator:* No self-healing yet → Phase 3 addresses with n8n automation

**Contingency:** No capability depends on another (except SMTP relay). Any feature can be deferred without blocking the rest.

## Functional Requirements

### Backup & Recovery

- **FR1:** Operator can configure automated nightly backups of all `/opt/appdata/` paths on both container hosts
- **FR2:** Operator can define backup retention policies (daily, weekly, monthly snapshot counts)
- **FR3:** Operator can list available backup snapshots with timestamps and sizes
- **FR4:** Operator can restore any stack's data from a specific backup snapshot to its original or an alternate path
- **FR5:** Operator can verify backup integrity without performing a full restore
- **FR6:** Operator can change the backup target (local → NAS → S3) without reconfiguring individual backup jobs

### Monitoring & Alerting

- **FR7:** System collects metrics from all running containers and host nodes at regular intervals
- **FR8:** Operator can view service health status for all 32 services from a single dashboard
- **FR9:** Operator can view resource utilization (CPU, memory, disk, network) per container and per host
- **FR10:** System sends email notification when a service fails health checks for longer than a configurable threshold
- **FR11:** System sends email notification when an unexpected container restart occurs (with container name, exit code, timestamp)
- **FR12:** Operator can configure which events trigger notifications and which are suppressed
- **FR13:** Operator can view backup job status (last run, success/failure, size) from the monitoring dashboard

### Centralized Logging

- **FR14:** System collects stdout/stderr from all Docker containers on both hosts automatically
- **FR15:** Operator can search logs by container name, time range, and keyword from a single interface
- **FR16:** Operator can filter and correlate logs across multiple containers for a specific time window
- **FR17:** System retains logs for a configurable duration with automatic cleanup
- **FR18:** New containers are automatically discovered and their logs collected without manual configuration

### Authentication & Access Control

- **FR19:** Operator can access all Traefik-routed services with a single login session
- **FR20:** System intercepts unauthenticated requests to any protected service and redirects to login
- **FR21:** Operator can configure session duration (how long before re-authentication is required)
- **FR22:** New services added to Traefik are automatically protected by SSO without per-service configuration
- **FR23:** Operator can optionally enable two-factor authentication (TOTP)

### Update Awareness

- **FR24:** System checks all running container images against their upstream registries for newer versions
- **FR25:** System checks apt package status on all containers and Proxmox nodes for available updates
- **FR26:** System checks installed tool versions (Terraform, Ansible, Node.js, Docker) against latest releases
- **FR27:** Operator receives a daily digest email summarizing all available updates across the homelab
- **FR28:** Operator can view current vs. available versions from the monitoring dashboard

### Email Notifications

- **FR29:** System can send outbound email notifications from any service (alerting, update checks, backup reports)
- **FR30:** Operator can configure the SMTP relay target (provider, credentials, sender address)
- **FR31:** Failed email delivery attempts are logged and visible to the operator

## Non-Functional Requirements

### Performance

- Grafana dashboard loads within 3 seconds with all panels populated
- Loki log queries return results within 5 seconds for 30-day time ranges
- Backup jobs complete within 2 hours for full nightly run (both hosts combined)
- Backup I/O must not degrade running service performance during scheduled runs
- Promtail log collection adds no measurable latency to container operations

### Security

- All SSO sessions use HTTPS-only cookies with secure and httpOnly flags
- Backup data encrypted at rest (Restic AES-256)
- SMTP credentials stored in environment files, never committed to Git
- Authelia configuration (password hash, secrets) stored outside of Git
- No service accessible without authentication when SSO is enabled (except health check endpoints)
- Backup repository password stored securely, separate from backup data

### Reliability

- Backup jobs must complete successfully or send a failure notification — no silent failures
- Monitoring stack auto-restarts on failure (Docker restart policy: unless-stopped)
- Email notifications retry on transient SMTP failures (at least 3 attempts)
- Promtail tolerates container restarts and reconnects automatically
- Alert rules persist across Prometheus restarts (configuration-based, not runtime state)
- Loki handles log ingestion spikes without dropping entries during normal operations

### Integration

- Authelia integrates with Traefik via standard forward-auth middleware
- Loki integrates as a native Grafana datasource (LogQL query support)
- Promtail discovers containers via Docker socket (standard Docker provider)
- Diun accesses Docker socket read-only for image version detection
- Restic operates independently of Docker (backs up host filesystem paths)
- All new components follow existing homelab-apps conventions: Docker Compose v2, pinned tags, health checks, resource limits, proxy network
