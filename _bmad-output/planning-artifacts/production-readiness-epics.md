---
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
  - step-03-create-stories
  - step-04-final-validation
inputDocuments:
  - homelab-playbook/_bmad-output/planning-artifacts/prd.md
  - homelab-playbook/_bmad-output/planning-artifacts/architecture.md
workflowType: 'epics-and-stories'
project_name: 'homelab'
user_name: 'tomamourette'
date: '2026-04-01'
---

# Homelab Production Readiness - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for the Homelab Production Readiness initiative, decomposing the 31 functional requirements from the PRD and the architectural decisions into implementable stories across 6 epics. Each epic delivers standalone user value and follows the deployment order specified in the architecture document.

## Requirements Inventory

### Functional Requirements

- **FR1:** Operator can configure automated nightly backups of all `/opt/appdata/` paths on both container hosts
- **FR2:** Operator can define backup retention policies (daily, weekly, monthly snapshot counts)
- **FR3:** Operator can list available backup snapshots with timestamps and sizes
- **FR4:** Operator can restore any stack's data from a specific backup snapshot to its original or an alternate path
- **FR5:** Operator can verify backup integrity without performing a full restore
- **FR6:** Operator can change the backup target (local -> NAS -> S3) without reconfiguring individual backup jobs
- **FR7:** System collects metrics from all running containers and host nodes at regular intervals
- **FR8:** Operator can view service health status for all 32 services from a single dashboard
- **FR9:** Operator can view resource utilization (CPU, memory, disk, network) per container and per host
- **FR10:** System sends email notification when a service fails health checks for longer than a configurable threshold
- **FR11:** System sends email notification when an unexpected container restart occurs (with container name, exit code, timestamp)
- **FR12:** Operator can configure which events trigger notifications and which are suppressed
- **FR13:** Operator can view backup job status (last run, success/failure, size) from the monitoring dashboard
- **FR14:** System collects stdout/stderr from all Docker containers on both hosts automatically
- **FR15:** Operator can search logs by container name, time range, and keyword from a single interface
- **FR16:** Operator can filter and correlate logs across multiple containers for a specific time window
- **FR17:** System retains logs for a configurable duration with automatic cleanup
- **FR18:** New containers are automatically discovered and their logs collected without manual configuration
- **FR19:** Operator can access all Traefik-routed services with a single login session
- **FR20:** System intercepts unauthenticated requests to any protected service and redirects to login
- **FR21:** Operator can configure session duration (how long before re-authentication is required)
- **FR22:** New services added to Traefik are automatically protected by SSO without per-service configuration
- **FR23:** Operator can optionally enable two-factor authentication (TOTP)
- **FR24:** System checks all running container images against their upstream registries for newer versions
- **FR25:** System checks apt package status on all containers and Proxmox nodes for available updates
- **FR26:** System checks installed tool versions (Terraform, Ansible, Node.js, Docker) against latest releases
- **FR27:** Operator receives a daily digest email summarizing all available updates across the homelab
- **FR28:** Operator can view current vs. available versions from the monitoring dashboard
- **FR29:** System can send outbound email notifications from any service (alerting, update checks, backup reports)
- **FR30:** Operator can configure the SMTP relay target (provider, credentials, sender address)
- **FR31:** Failed email delivery attempts are logged and visible to the operator

### Non-Functional Requirements

- **NFR-PERF-1:** Grafana dashboard loads within 3 seconds with all panels populated
- **NFR-PERF-2:** Loki log queries return results within 5 seconds for 30-day time ranges
- **NFR-PERF-3:** Backup jobs complete within 2 hours for full nightly run (both hosts combined)
- **NFR-PERF-4:** Backup I/O must not degrade running service performance during scheduled runs
- **NFR-PERF-5:** Promtail log collection adds no measurable latency to container operations
- **NFR-SEC-1:** All SSO sessions use HTTPS-only cookies with secure and httpOnly flags
- **NFR-SEC-2:** Backup data encrypted at rest (Restic AES-256)
- **NFR-SEC-3:** SMTP credentials stored in environment files, never committed to Git
- **NFR-SEC-4:** Authelia configuration (password hash, secrets) stored outside of Git
- **NFR-SEC-5:** No service accessible without authentication when SSO is enabled (except health check endpoints)
- **NFR-SEC-6:** Backup repository password stored securely, separate from backup data
- **NFR-REL-1:** Backup jobs must complete successfully or send a failure notification -- no silent failures
- **NFR-REL-2:** Monitoring stack auto-restarts on failure (Docker restart policy: unless-stopped)
- **NFR-REL-3:** Email notifications retry on transient SMTP failures (at least 3 attempts)
- **NFR-REL-4:** Promtail tolerates container restarts and reconnects automatically
- **NFR-REL-5:** Alert rules persist across Prometheus restarts (configuration-based, not runtime state)
- **NFR-REL-6:** Loki handles log ingestion spikes without dropping entries during normal operations
- **NFR-INT-1:** Authelia integrates with Traefik via standard forward-auth middleware
- **NFR-INT-2:** Loki integrates as a native Grafana datasource (LogQL query support)
- **NFR-INT-3:** Promtail discovers containers via Docker socket (standard Docker provider)
- **NFR-INT-4:** Diun accesses Docker socket read-only for image version detection
- **NFR-INT-5:** Restic operates independently of Docker (backs up host filesystem paths)
- **NFR-INT-6:** All new components follow existing homelab-apps conventions: Docker Compose v2, pinned tags, health checks, resource limits, proxy network

### Additional Requirements (from Architecture)

- **ARCH-1:** All new Docker Compose stacks use pinned semver image tags, never `:latest`
- **ARCH-2:** All containers set `no-new-privileges:true` and `cap_drop: ALL`
- **ARCH-3:** All scheduled tasks use systemd timers, not crontab
- **ARCH-4:** Every new stack commits `.env.sample` with documented variables
- **ARCH-5:** SMTP relay publishes `127.0.0.1:25:25` on host for systemd script access
- **ARCH-6:** Promtail on ct-media-01 deployed via Ansible role (`promtail-media`)
- **ARCH-7:** Restic backup metrics exported via textfile collector for Prometheus
- **ARCH-8:** Grafana dashboards provisioned via bind-mount provisioning directory
- **ARCH-9:** Script output follows structured prefix format: `[timestamp] [severity] source: message`
- **ARCH-10:** Authelia middleware defined once in infra-core, referenced by all protected services

### UX Design Requirements

Not applicable -- infrastructure project with no user-facing UI beyond Grafana dashboards.

### FR Coverage Map

| FR | Epic | Story | Description |
|----|------|-------|-------------|
| FR1 | 5 | 5.1, 5.2 | Restic backup role + systemd timer |
| FR2 | 5 | 5.1, 5.2 | Retention policy in Ansible defaults |
| FR3 | 5 | 5.3 | Restic snapshot listing |
| FR4 | 5 | 5.3 | Restic restore capability |
| FR5 | 5 | 5.3 | Restic check command |
| FR6 | 5 | 5.1 | Backend-agnostic repo config |
| FR7 | 2 | 2.1 | Prometheus scrape targets |
| FR8 | 2 | 2.2 | Grafana service health dashboard |
| FR9 | 2 | 2.2 | Grafana resource utilization panels |
| FR10 | 2 | 2.3 | Grafana email alert rules |
| FR11 | 2 | 2.3 | Container restart alert rule |
| FR12 | 2 | 2.3 | Configurable alert suppression |
| FR13 | 5 | 5.4 | Backup status dashboard panel |
| FR14 | 3 | 3.1, 3.2 | Promtail on both hosts |
| FR15 | 3 | 3.3 | Grafana Loki datasource + Explore |
| FR16 | 3 | 3.3 | LogQL cross-container queries |
| FR17 | 3 | 3.1 | Loki retention config |
| FR18 | 3 | 3.1, 3.2 | Promtail Docker socket auto-discovery |
| FR19 | 4 | 4.1, 4.2 | Authelia SSO + Traefik middleware |
| FR20 | 4 | 4.1, 4.2, 4.3 | Forward-auth redirect |
| FR21 | 4 | 4.1 | Session duration config |
| FR22 | 4 | 4.2, 4.3 | Middleware auto-protects new services |
| FR23 | 4 | 4.1 | Optional TOTP 2FA |
| FR24 | 6 | 6.1, 6.2 | Diun container image checks (both hosts) |
| FR25 | 6 | 6.3 | Ansible apt-check role |
| FR26 | 6 | 6.4 | Ansible tool-version-check role |
| FR27 | 6 | 6.1, 6.2, 6.3, 6.4 | Per-tool email notifications (see FR27 note in Epic 6) |
| FR28 | 6 | 6.5 | Update status Grafana dashboard |
| FR29 | 1 | 1.1 | SMTP relay container |
| FR30 | 1 | 1.1 | Configurable relay target |
| FR31 | 1 | 1.2 | Delivery logging and visibility |

## Epic List

| Epic | Title | FRs Covered | Stories | Target Repos |
|------|-------|-------------|---------|-------------|
| 1 | SMTP Relay | FR29-FR31 | 2 | homelab-apps |
| 2 | Observability and Alerting | FR7-FR13 | 4 | homelab-apps |
| 3 | Centralized Logging | FR14-FR18 | 4 | homelab-apps, homelab-infra |
| 4 | SSO Gateway | FR19-FR23 | 4 | homelab-apps |
| 5 | Backup and Recovery | FR1-FR6, FR13 | 4 | homelab-infra, homelab-apps |
| 6 | Update Checks | FR24-FR28 | 6 | homelab-apps, homelab-infra |

**Total: 6 epics, 24 stories**

---

## Epic 1: SMTP Relay

**Goal:** Provide a centralized outbound email relay so that all downstream services (Grafana alerts, backup reports, update digests) can send notifications without individual SMTP configuration.

**Prerequisite for:** All other epics that send email notifications (Epics 2, 3, 5, 6).

### Story 1.1: Create SMTP Relay Docker Compose Stack

As a homelab operator,
I want an SMTP relay container running on ct-docker-01,
So that all services on the Docker network can send outbound email via a single relay.

**Target repo:** homelab-apps
**Files created:**
- `stacks/smtp-relay/docker-compose.yml`
- `stacks/smtp-relay/.env.sample`
- `stacks/smtp-relay/.gitignore`

**Implements:** FR29, FR30

**Acceptance Criteria:**

**Given** the smtp-relay stack is deployed on ct-docker-01
**When** a service sends an email to `smtp-relay:25` on the Docker network
**Then** the relay forwards it to the configured upstream SMTP provider (Gmail/Outlook)
**And** the relay is accessible from host scripts via `localhost:25` (bound to `127.0.0.1:25:25`)

**Given** the `.env.sample` file exists in the stack directory
**When** the operator copies it to `.env` and fills in credentials
**Then** the relay authenticates to the upstream provider using those credentials
**And** the sender address, upstream host, port, and credentials are all configurable via environment variables

**Given** the docker-compose.yml is created
**When** inspected for compliance
**Then** it uses a pinned semver image tag (not `:latest`)
**And** sets `restart: unless-stopped`, `no-new-privileges:true`, `cap_drop: ALL`
**And** sets resource limits (CPU + memory)
**And** includes a health check
**And** does NOT expose the relay via Traefik (internal-only service)

### Story 1.2: Validate SMTP Relay and Add Delivery Logging

As a homelab operator,
I want to verify the SMTP relay sends email successfully and logs failed deliveries,
So that I have confidence notifications will work before deploying downstream services.

**Target repo:** homelab-apps
**Files modified:**
- `stack-targets.yml` (add smtp-relay entry)

**Implements:** FR31

**Acceptance Criteria:**

**Given** the smtp-relay container is running
**When** a test email is sent via `swaks` or `sendmail` from the host using `localhost:25`
**Then** the email arrives at the configured recipient address

**Given** the relay encounters a delivery failure (invalid credentials, upstream down)
**When** the relay attempts to send
**Then** the failure is logged to the container's stdout/stderr
**And** the operator can view the failure via `docker logs smtp-relay`

**Given** the smtp-relay stack is deployed
**When** `stack-targets.yml` is checked
**Then** it includes the smtp-relay stack with its target host (ct-docker-01)

---

## Epic 2: Observability and Alerting

**Goal:** Deploy the Prometheus + Grafana monitoring stack with email-based alerting so that the operator has a single dashboard showing all service health, resource utilization, and receives proactive notifications for outages and unexpected restarts.

### Story 2.1: Deploy Prometheus with Scrape Targets for All Services

As a homelab operator,
I want Prometheus collecting metrics from all running containers and host nodes,
So that I have the raw data foundation for dashboards and alerting.

**Target repo:** homelab-apps
**Files created/modified:**
- `stacks/observability/docker-compose.yml` (ensure Prometheus service exists with current config)
- `stacks/observability/config/prometheus.yml` (add scrape targets for all 32 services + host metrics)
- `stacks/observability/.env.sample` (update if needed)

**Implements:** FR7

**Acceptance Criteria:**

**Given** the observability stack is deployed on ct-docker-01
**When** Prometheus starts up
**Then** it scrapes metrics from all running containers that expose `/metrics` endpoints
**And** it scrapes host-level metrics (node-exporter or cAdvisor) on both ct-docker-01 and ct-media-01
**And** scrape targets are defined in configuration files (not runtime state)

**Given** a new service is deployed that exposes `/metrics`
**When** its scrape target is added to `prometheus.yml`
**Then** Prometheus discovers and scrapes it within one scrape interval

### Story 2.2: Create Grafana Service Health and Resource Dashboard

As a homelab operator,
I want a single Grafana dashboard showing all service health status and resource utilization,
So that I can perform my daily health check in under 90 seconds.

**Target repo:** homelab-apps
**Files created:**
- `stacks/observability/dashboards/service-health.json`
- `stacks/observability/config/provisioning/dashboards/dashboards.yml` (provisioning config)

**Implements:** FR8, FR9

**Acceptance Criteria:**

**Given** Grafana is running with the Prometheus datasource
**When** the operator opens the Service Health dashboard
**Then** it displays health status (up/down) for all services across both nodes
**And** shows CPU, memory, disk, and network utilization per container and per host
**And** the dashboard loads within 3 seconds (NFR-PERF-1)

**Given** the dashboard JSON is stored in the provisioning directory
**When** Grafana restarts
**Then** the dashboard is automatically re-provisioned (not lost)

### Story 2.3: Configure Grafana Alert Rules and Email Notification Channel

As a homelab operator,
I want email notifications when a service goes down or a container restarts unexpectedly,
So that I am proactively alerted to issues instead of discovering them manually.

**Target repo:** homelab-apps
**Files created:**
- `stacks/observability/config/alerting/service-alerts.yml`
- `stacks/observability/config/alerting/disk-alerts.yml`
- `stacks/observability/config/provisioning/alerting/notification-channel.yml`
- `stacks/observability/.env.sample` (add `GRAFANA_SMTP_HOST`, `GRAFANA_SMTP_FROM`, etc.)

**Implements:** FR10, FR11, FR12

**Acceptance Criteria:**

**Given** the Grafana SMTP notification channel is configured to use `smtp-relay:25`
**When** a service fails health checks for longer than 5 minutes (configurable threshold)
**Then** Grafana sends an email notification with the service name and host

**Given** a container restarts unexpectedly
**When** the restart is detected by Prometheus (container exit code, restart count delta)
**Then** an email notification is sent with the container name, exit code, and timestamp
**And** expected restarts (operator-initiated via `docker compose up -d`) are suppressed

**Given** the operator wants to suppress alerts for a specific service
**When** the alert rule configuration is edited
**Then** that service can be excluded without affecting other alert rules

**Given** a disk usage threshold of 80% is configured
**When** any monitored volume exceeds 80%
**Then** an email notification is sent with the volume path and current usage

### Story 2.4: Validate Observability Stack End-to-End

As a homelab operator,
I want to verify that monitoring and alerting work together end-to-end,
So that I trust the system before deploying further capabilities.

**Target repo:** homelab-apps (no new files -- validation only)

**Implements:** Validates FR7-FR12

**Acceptance Criteria:**

**Given** the observability stack is fully deployed with alert rules and notification channel
**When** the operator stops a monitored container (simulated outage)
**Then** Prometheus detects the outage within one scrape interval
**And** Grafana fires the alert within the configured threshold
**And** an email notification is received at the configured address

**Given** all Prometheus scrape targets are configured
**When** the operator checks the Prometheus targets page (`/targets`)
**Then** all targets show status "UP" (or documented as expected-down if not yet deployed)

---

## Epic 3: Centralized Logging

**Goal:** Deploy Loki and Promtail so that all container logs from both hosts are collected, searchable, and queryable from Grafana, enabling the "debug in 5 minutes" incident response journey.

### Story 3.1: Add Loki and Promtail to Observability Stack on ct-docker-01

As a homelab operator,
I want Loki receiving logs and Promtail collecting container logs on ct-docker-01,
So that all container stdout/stderr from the primary host is centrally stored and queryable.

**Target repo:** homelab-apps
**Files created/modified:**
- `stacks/observability/docker-compose.yml` (add `loki` and `promtail` services)
- `stacks/observability/config/loki-config.yml`
- `stacks/observability/config/promtail-config.yml`
- `stacks/observability/.env.sample` (add Loki retention, storage path vars)

**Implements:** FR14, FR17, FR18

**Acceptance Criteria:**

**Given** Loki and Promtail are added to the observability stack on ct-docker-01
**When** the stack is deployed
**Then** Promtail discovers all running containers via the Docker socket
**And** Promtail pushes container stdout/stderr to Loki at `loki:3100`
**And** Loki stores logs in `/opt/appdata/observability/loki/` with a configurable retention period (default 30 days)

**Given** a new container is started on ct-docker-01
**When** it produces log output
**Then** Promtail automatically discovers and collects its logs without manual configuration

**Given** the Loki and Promtail services are configured
**When** inspected for compliance
**Then** they use pinned semver image tags
**And** Promtail has read-only Docker socket access (`/var/run/docker.sock:/var/run/docker.sock:ro`)
**And** both services have resource limits, health checks, and `restart: unless-stopped`

### Story 3.2: Deploy Promtail on ct-media-01 via Ansible Role

As a homelab operator,
I want Promtail running on ct-media-01 pushing logs to Loki on ct-docker-01,
So that container logs from both hosts are centrally collected.

**Target repo:** homelab-infra
**Files created:**
- `ansible/roles/promtail-media/tasks/main.yml`
- `ansible/roles/promtail-media/templates/docker-compose.yml.j2`
- `ansible/roles/promtail-media/templates/promtail-config.yml.j2`
- `ansible/roles/promtail-media/defaults/main.yml`

**Implements:** FR14, FR18

**Acceptance Criteria:**

**Given** the `promtail-media` Ansible role is applied to ct-media-01
**When** the role runs
**Then** a Promtail container is deployed on ct-media-01 via Docker Compose
**And** it pushes logs to the Loki instance on ct-docker-01 (URL rendered from Ansible variables)
**And** it discovers all running containers on ct-media-01 via Docker socket

**Given** the Ansible role follows homelab-infra conventions
**When** inspected
**Then** it uses the standard role structure (tasks, templates, defaults)
**And** variables are prefixed with `promtail_media_`
**And** all tasks are tagged with `promtail-media`
**And** the role is idempotent (re-running produces no changes if already applied)

### Story 3.3: Configure Grafana Loki Datasource and Log Exploration

As a homelab operator,
I want Loki available as a Grafana datasource so I can search and filter logs,
So that I can identify root cause of service issues within 5 minutes.

**Target repo:** homelab-apps
**Files created:**
- `stacks/observability/config/provisioning/datasources/loki.yml`

**Implements:** FR15, FR16

**Acceptance Criteria:**

**Given** Loki is configured as a provisioned Grafana datasource
**When** the operator opens Grafana Explore and selects the Loki datasource
**Then** they can search logs by container name label
**And** they can filter by time range and keyword using LogQL
**And** queries return results within 5 seconds for 30-day ranges (NFR-PERF-2)

**Given** the operator is investigating an incident
**When** they filter logs for a specific 5-minute window across multiple containers
**Then** correlated log entries from all matching containers are displayed in chronological order

### Story 3.4: Validate Centralized Logging End-to-End

As a homelab operator,
I want to verify logs flow from both hosts through to Grafana queries,
So that I trust the logging pipeline before relying on it for incident response.

**Target repo:** No new files -- validation only

**Implements:** Validates FR14-FR18

**Acceptance Criteria:**

**Given** Promtail is running on both ct-docker-01 and ct-media-01
**When** a container on ct-media-01 produces log output
**Then** the log entry is queryable in Grafana via Loki within 30 seconds

**Given** a container is restarted on ct-docker-01
**When** Promtail reconnects to the container's new log stream
**Then** no log gap is observed (NFR-REL-4)

**Given** Promtail is running on both hosts
**When** the operator checks the Promtail targets page
**Then** all active containers on both hosts show as discovered targets

---

## Epic 4: SSO Gateway

**Goal:** Deploy Authelia as a forward-auth middleware in Traefik so that the operator authenticates once and accesses all services, eliminating per-service credential management.

### Story 4.1: Create Authelia Docker Compose Stack

As a homelab operator,
I want Authelia deployed as a Docker container with YAML-based configuration,
So that I have a lightweight SSO provider running on ct-docker-01.

**Target repo:** homelab-apps
**Files created:**
- `stacks/authelia/docker-compose.yml`
- `stacks/authelia/config/configuration.yml.sample`
- `stacks/authelia/.env.sample`
- `stacks/authelia/.gitignore`

**Implements:** FR19, FR20, FR21, FR23

**Acceptance Criteria:**

**Given** the authelia stack is deployed on ct-docker-01
**When** the operator accesses `auth.bi-services.be`
**Then** the Authelia login portal is displayed

**Given** the Authelia configuration file is set up
**When** inspected
**Then** session duration is configurable (default 7 days)
**And** TOTP 2FA is available as an optional feature the operator can enable
**And** session storage is file-based in `/opt/appdata/authelia/`
**And** cookies use HTTPS-only with secure and httpOnly flags (NFR-SEC-1)
**And** the configuration sample (`configuration.yml.sample`) is committed; real config with secrets is gitignored

**Given** the docker-compose.yml follows conventions
**When** inspected
**Then** it uses a pinned semver image tag (e.g., `authelia/authelia:4.38.0`)
**And** sets resource limits, health check, `restart: unless-stopped`, `no-new-privileges:true`, `cap_drop: ALL`
**And** Authelia joins the `proxy` network for Traefik routing

### Story 4.2: Integrate Authelia Forward-Auth Middleware with Traefik

As a homelab operator,
I want Traefik to use Authelia as a forward-auth middleware for all routed services,
So that every service is protected by SSO without per-service configuration.

**Target repo:** homelab-apps
**Files created/modified:**
- `stacks/infra-core/config/dynamic/authelia-middleware.yml` (new)
- `stacks/infra-core/docker-compose.yml` (add Authelia middleware labels on Traefik)

**Implements:** FR19, FR20, FR22

**Acceptance Criteria:**

**Given** the Authelia forward-auth middleware is defined in infra-core
**When** an unauthenticated user accesses any Traefik-routed service
**Then** the request is intercepted and redirected to the Authelia login portal

**Given** the operator has authenticated via Authelia
**When** they navigate to any other Traefik-routed service
**Then** they pass through without a second login (single session cookie)

**Given** a new service is added to Traefik with the `authelia@docker` middleware label
**When** it is accessed
**Then** it is automatically protected by SSO without any Authelia-side configuration

**Given** the middleware is defined
**When** inspected
**Then** the forward-auth address is `http://authelia:9091/api/authz/forward-auth`
**And** `trustForwardHeader` is true
**And** response headers include `Remote-User`, `Remote-Groups`, `Remote-Email`

### Story 4.3: Roll Out Authelia Middleware Labels to All Existing Services

As a homelab operator,
I want all existing Traefik-routed service compose files updated with the `authelia@docker` middleware label,
So that every service is protected by SSO immediately after Authelia and its middleware are deployed.

**Target repo:** homelab-apps
**Files modified:**
- All 17+ existing `docker-compose.yml` files under `stacks/` that have Traefik router labels

**Implements:** FR20, FR22

**Acceptance Criteria:**

**Given** the Authelia middleware is defined in infra-core (Story 4.2 complete)
**When** the operator inspects any existing Traefik-routed service's `docker-compose.yml`
**Then** the service's Traefik labels include `traefik.http.routers.<service>.middlewares=authelia@docker`

**Given** all 17+ existing compose files have been updated with the Authelia middleware label
**When** an unauthenticated user accesses any of those services
**Then** they are redirected to the Authelia login portal

**Given** some services may need to be excluded from SSO (e.g., health check endpoints)
**When** the operator reviews the list of modified files
**Then** any intentional exclusions are documented in a comment within the compose file

**Given** all compose files are updated
**When** each stack is redeployed (`docker compose up -d`)
**Then** existing service behavior is unchanged for authenticated users
**And** unauthenticated requests are intercepted and redirected to Authelia

### Story 4.4: Validate SSO Gateway End-to-End

As a homelab operator,
I want to verify SSO protects all services and the login flow works correctly,
So that I trust the authentication layer before Phase 1 go-live.

**Target repo:** No new files -- validation only

**Implements:** Validates FR19-FR23

**Acceptance Criteria:**

**Given** Authelia and the forward-auth middleware are deployed
**When** the operator accesses a Traefik-routed service without a session
**Then** they are redirected to the Authelia login page

**Given** the operator logs in via Authelia
**When** they navigate to a different Traefik-routed service
**Then** they are not prompted to log in again (session persists)

**Given** the operator enables TOTP 2FA in Authelia
**When** they log in
**Then** they are prompted for a TOTP code after entering their password

**Given** a health check endpoint exists on a service
**When** it is accessed without authentication
**Then** it responds normally (health endpoints excluded from forward-auth)

---

## Epic 5: Backup and Recovery

**Goal:** Deploy Restic-based nightly backups of all `/opt/appdata/` paths on both hosts with configurable retention, so that the operator can recover from any data loss within 1 hour.

### Story 5.1: Create Restic Backup Ansible Role

As a homelab operator,
I want an Ansible role that installs and configures Restic with systemd timers on both hosts,
So that nightly encrypted backups run automatically without manual intervention.

**Target repo:** homelab-infra
**Files created:**
- `ansible/roles/restic-backup/tasks/main.yml`
- `ansible/roles/restic-backup/handlers/main.yml`
- `ansible/roles/restic-backup/templates/restic-backup.service.j2`
- `ansible/roles/restic-backup/templates/restic-backup.timer.j2`
- `ansible/roles/restic-backup/templates/restic-backup.sh.j2`
- `ansible/roles/restic-backup/defaults/main.yml`

**Implements:** FR1, FR2, FR6

**Acceptance Criteria:**

**Given** the `restic-backup` Ansible role is applied to ct-docker-01 and ct-media-01
**When** the role completes
**Then** Restic is installed on both hosts
**And** a systemd timer runs the backup at 02:00 nightly (ARCH-3)
**And** the backup covers all `/opt/appdata/` paths on the target host
**And** retention is configured as 7 daily, 4 weekly, 3 monthly snapshots (default, overridable)
**And** backup data is encrypted at rest with AES-256 (NFR-SEC-2)

**Given** the role defaults define the backup target
**When** the operator changes the target from local to NAS to S3
**Then** only the `restic_backup_repo` variable changes; no backup job reconfiguration needed

**Given** the role follows homelab-infra conventions
**When** inspected
**Then** variables are prefixed with `restic_backup_`
**And** all tasks are tagged with `restic-backup`
**And** tasks are idempotent
**And** the repo password is stored in an Ansible-templated env file (NFR-SEC-6)

### Story 5.2: Create Restic Failure Notification Service

As a homelab operator,
I want a systemd service that sends an email when a backup fails,
So that I am never surprised by silent backup failures.

**Target repo:** homelab-infra
**Files created:**
- `ansible/roles/restic-backup/templates/restic-notify-failure.sh.j2`
- `ansible/roles/restic-backup/templates/restic-notify-failure.service.j2`

**Implements:** FR1 (reliability aspect), NFR-REL-1

**Acceptance Criteria:**

**Given** the `restic-backup.service` systemd unit is configured
**When** the backup job fails (non-zero exit code)
**Then** the `OnFailure=restic-notify-failure.service` directive triggers
**And** the failure notification service sends an email via `localhost:25` (SMTP relay)
**And** the email includes the hostname, timestamp, and failure reason

**Given** the backup completes successfully
**When** the timer fires
**Then** no failure email is sent

**Given** the notification script follows Architecture patterns
**When** inspected
**Then** output uses structured prefix format: `[timestamp] [severity] source: message` (ARCH-9)

### Story 5.3: Create Restic Restore and Verification Procedures

As a homelab operator,
I want documented and tested procedures for listing snapshots, verifying integrity, and restoring data,
So that I can confidently recover from any failure within 1 hour.

**Target repo:** homelab-infra
**Files created:**
- `ansible/roles/restic-backup/files/restic-check.sh`

**Implements:** FR3, FR4, FR5

**Acceptance Criteria:**

**Given** the operator wants to list available snapshots
**When** they run `restic snapshots` with the configured repo
**Then** they see a list of snapshots with timestamps, paths, and sizes

**Given** the operator wants to restore a specific stack's data
**When** they run `restic restore <snapshot-id> --target /opt/appdata/` (or alternate path)
**Then** the data is restored to the specified location

**Given** the operator wants to verify backup integrity
**When** they run the `restic-check.sh` script
**Then** it executes `restic check` against the repository
**And** reports integrity status without performing a full restore
**And** a full restore of any single stack's data completes within 1 hour

### Story 5.4: Create Backup Status Grafana Dashboard Panel

As a homelab operator,
I want to see backup job status (last run, success/failure, size) in Grafana,
So that backup health is visible during my daily health check.

**Target repo:** homelab-apps + homelab-infra
**Files created:**
- `stacks/observability/dashboards/backup-status.json` (homelab-apps)
- `ansible/roles/restic-backup/templates/restic-backup.sh.j2` (modify to write `.prom` textfile)

**Implements:** FR13

**Acceptance Criteria:**

**Given** the Restic backup script writes metrics to a Prometheus textfile collector `.prom` file (ARCH-7)
**When** Prometheus scrapes the node-exporter textfile directory
**Then** backup metrics (last run timestamp, success/failure, snapshot size, duration) are available as Prometheus metrics

**Given** the backup-status Grafana dashboard is provisioned
**When** the operator views it
**Then** it displays last backup time, success/failure status, and snapshot size for each host
**And** failed backups are visually highlighted

---

## Epic 6: Update Checks

**Goal:** Deploy container image update detection (Diun) and system/tool version checking so that the operator receives email notifications summarizing all available updates across the homelab.

> **Note (FR27 divergence):** FR27 specifies a "daily digest email," but the confirmed architecture decision chose separate per-tool emails for MVP simplicity (Diun sends its own notifications, apt-check and tool-version-check each send their own). A unified daily digest may be added in a future iteration.

### Story 6.1: Create Diun Docker Compose Stack for Container Image Checks

As a homelab operator,
I want Diun monitoring all running containers for newer image versions,
So that I am aware of available updates without manually checking registries.

**Target repo:** homelab-apps
**Files created:**
- `stacks/update-checks/docker-compose.yml`
- `stacks/update-checks/config/diun.yml.sample`
- `stacks/update-checks/.env.sample`
- `stacks/update-checks/.gitignore`

**Implements:** FR24, FR27

**Acceptance Criteria:**

**Given** the update-checks stack is deployed on ct-docker-01
**When** Diun runs its scheduled check
**Then** it compares all running container images against their upstream registries
**And** sends an email notification for images with newer versions available
**And** uses `smtp-relay:25` for email delivery

**Given** the docker-compose.yml follows conventions
**When** inspected
**Then** Diun has read-only Docker socket access (`/var/run/docker.sock:/var/run/docker.sock:ro`)
**And** uses a pinned semver image tag
**And** sets resource limits, health check, `restart: unless-stopped`, `no-new-privileges:true`, `cap_drop: ALL`

**Given** a new container is deployed
**When** Diun next runs
**Then** the new container's image is automatically included in the check (Docker socket auto-discovery)

### Story 6.2: Deploy Diun on ct-media-01 for Media Container Image Checks

As a homelab operator,
I want Diun monitoring container images on ct-media-01 (Plex, Sonarr, Radarr, etc.),
So that image update detection covers BOTH container hosts, not just ct-docker-01.

**Target repo:** homelab-infra
**Files created:**
- `ansible/roles/diun-media/tasks/main.yml`
- `ansible/roles/diun-media/templates/docker-compose.yml.j2`
- `ansible/roles/diun-media/templates/diun.yml.j2`
- `ansible/roles/diun-media/defaults/main.yml`

**Implements:** FR24, FR27

**Acceptance Criteria:**

**Given** the `diun-media` Ansible role is applied to ct-media-01
**When** the role runs
**Then** a Diun container is deployed on ct-media-01 via Docker Compose
**And** it monitors all running container images on ct-media-01 via Docker socket (read-only)
**And** it sends email notifications for images with newer versions via `smtp-relay` on ct-docker-01

**Given** a media container (Plex, Sonarr, Radarr, etc.) has a newer image available
**When** Diun runs its scheduled check on ct-media-01
**Then** it detects the update and sends an email notification listing the image and available version

**Given** the Ansible role follows homelab-infra conventions
**When** inspected
**Then** it uses the standard role structure (tasks, templates, defaults)
**And** variables are prefixed with `diun_media_`
**And** all tasks are tagged with `diun-media`
**And** the role is idempotent (re-running produces no changes if already applied)
**And** the Diun container uses a pinned semver image tag, resource limits, health check, `restart: unless-stopped`, `no-new-privileges:true`, `cap_drop: ALL`

### Story 6.3: Create Ansible Role for APT Package Update Checks

As a homelab operator,
I want automated checks for available apt package updates on all containers and Proxmox nodes,
So that I know about pending system-level updates.

**Target repo:** homelab-infra
**Files created:**
- `ansible/roles/apt-check/tasks/main.yml`
- `ansible/roles/apt-check/templates/apt-check.service.j2`
- `ansible/roles/apt-check/templates/apt-check.timer.j2`
- `ansible/roles/apt-check/templates/apt-check.sh.j2`
- `ansible/roles/apt-check/defaults/main.yml`

**Implements:** FR25, FR27

**Acceptance Criteria:**

**Given** the `apt-check` Ansible role is applied to all containers and Proxmox nodes
**When** the systemd timer fires daily
**Then** the script runs `apt update && apt list --upgradable`
**And** sends an email via `localhost:25` listing available package updates
**And** produces no email if there are no updates (no noise)

**Given** the role follows homelab-infra conventions
**When** inspected
**Then** it uses systemd timers (not crontab) per ARCH-3
**And** variables are prefixed with `apt_check_`
**And** all tasks are tagged with `apt-check`
**And** script output uses structured prefix format (ARCH-9)

### Story 6.4: Create Ansible Role for Tool Version Checks

As a homelab operator,
I want automated checks comparing installed tool versions (Terraform, Ansible, Node.js, Docker) against latest releases,
So that I know when critical infrastructure tools are outdated.

**Target repo:** homelab-infra
**Files created:**
- `ansible/roles/tool-version-check/tasks/main.yml`
- `ansible/roles/tool-version-check/templates/tool-check.service.j2`
- `ansible/roles/tool-version-check/templates/tool-check.timer.j2`
- `ansible/roles/tool-version-check/templates/tool-check.sh.j2`
- `ansible/roles/tool-version-check/defaults/main.yml`

**Implements:** FR26, FR27

**Acceptance Criteria:**

**Given** the `tool-version-check` Ansible role is applied to the appropriate hosts
**When** the systemd timer fires daily
**Then** the script checks installed versions of Terraform, Ansible, Node.js, and Docker
**And** compares them against latest releases (GitHub API or version endpoints)
**And** sends an email via `localhost:25` listing tools with newer versions available
**And** produces no email if all tools are current

**Given** the role follows homelab-infra conventions
**When** inspected
**Then** it uses systemd timers (not crontab) per ARCH-3
**And** variables are prefixed with `tool_version_check_`
**And** all tasks are tagged with `tool-version-check`
**And** script output uses structured prefix format (ARCH-9)

### Story 6.5: Create Update Status Grafana Dashboard

As a homelab operator,
I want to see current vs. available versions for containers, packages, and tools in Grafana,
So that update status is visible during my daily health check.

**Target repo:** homelab-apps
**Files created:**
- `stacks/observability/dashboards/update-status.json`

**Implements:** FR28

**Acceptance Criteria:**

**Given** Diun and the apt/tool check scripts export update status as Prometheus metrics (via textfile collector)
**When** the operator views the Update Status Grafana dashboard
**Then** it shows current vs. available versions for container images
**And** shows pending apt package updates per host
**And** shows installed vs. latest versions for tracked tools (Terraform, Ansible, Node.js, Docker)

**Given** the dashboard is stored in the provisioning directory
**When** Grafana restarts
**Then** the dashboard is automatically re-provisioned

### Story 6.6: Validate Update Checks End-to-End

As a homelab operator,
I want to verify that all update check mechanisms work and produce notifications,
So that I trust the system provides complete update awareness.

**Target repo:** No new files -- validation only

**Implements:** Validates FR24-FR28

**Acceptance Criteria:**

**Given** Diun is running and monitoring container images
**When** a container image has a newer version available
**Then** Diun detects it and sends an email notification

**Given** the apt-check timer has fired
**When** packages are available for update
**Then** an email is sent listing the upgradable packages

**Given** the tool-version-check timer has fired
**When** a tool has a newer version available
**Then** an email is sent listing the outdated tool and its latest version

**Given** the Update Status Grafana dashboard is deployed
**When** the operator views it
**Then** all update data is displayed and matches the email notifications

---

## Final Validation

### FR Coverage Verification

All 31 functional requirements (FR1-FR31) are covered by at least one story:

| FR Range | Epic | Stories | Status |
|----------|------|---------|--------|
| FR1-FR6 | Epic 5 | 5.1, 5.2, 5.3 | Covered |
| FR7-FR9 | Epic 2 | 2.1, 2.2 | Covered |
| FR10-FR12 | Epic 2 | 2.3 | Covered |
| FR13 | Epic 5 | 5.4 | Covered |
| FR14-FR18 | Epic 3 | 3.1, 3.2, 3.3 | Covered |
| FR19-FR23 | Epic 4 | 4.1, 4.2, 4.3 | Covered |
| FR24-FR28 | Epic 6 | 6.1, 6.2, 6.3, 6.4, 6.5 | Covered |
| FR29-FR31 | Epic 1 | 1.1, 1.2 | Covered |

### Dependency Verification

- **No forward dependencies between stories within an epic:** Each story builds on the previous one sequentially.
- **No circular dependencies between epics:** Epic 1 (SMTP) is a prerequisite for Epics 2, 5, and 6 (email notifications). All other epics are independent.
- **Deployment order is respected:** SMTP -> Observability -> Logging -> SSO -> Backup -> Update Checks.

### Epic Independence Verification

Each epic delivers complete, standalone functionality:
- **Epic 1:** SMTP relay works and sends email independently.
- **Epic 2:** Full monitoring + alerting stack with dashboards and notifications.
- **Epic 3:** Complete logging pipeline from both hosts to Grafana.
- **Epic 4:** Full SSO covering all Traefik-routed services.
- **Epic 5:** Complete backup + restore + monitoring of backup health.
- **Epic 6:** Complete update awareness for containers, packages, and tools.

### Architecture Compliance Verification

- All Docker stacks use pinned semver tags (ARCH-1)
- All containers use `no-new-privileges:true` + `cap_drop: ALL` (ARCH-2)
- All scheduled tasks use systemd timers (ARCH-3)
- All stacks include `.env.sample` (ARCH-4)
- SMTP relay bound to `127.0.0.1:25:25` for host script access (ARCH-5)
- Promtail on ct-media-01 deployed via Ansible role (ARCH-6)
- Backup metrics via textfile collector (ARCH-7)
- Grafana dashboards provisioned via bind-mount (ARCH-8)
- Script output uses structured prefix format (ARCH-9)
- Authelia middleware defined once in infra-core (ARCH-10)
- Cross-repo stories clearly identify target repo (homelab-apps vs homelab-infra)
