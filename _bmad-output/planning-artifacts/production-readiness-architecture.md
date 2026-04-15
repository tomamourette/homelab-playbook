---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
lastStep: 8
status: 'complete'
completedAt: '2026-04-01'
inputDocuments:
  - homelab-playbook/_bmad-output/planning-artifacts/prd.md
  - homelab-playbook/_bmad-output/planning-artifacts/research/technical-ephemeral-cloud-containers-research-2026-03-31.md
  - docs/index.md
  - docs/project-overview.md
  - docs/architecture-homelab-infra.md
  - docs/architecture-homelab-apps.md
  - docs/architecture-homelab-playbook.md
  - docs/integration-architecture.md
  - docs/development-guide.md
  - docs/deployment-guide.md
workflowType: 'architecture'
project_name: 'homelab'
user_name: 'tomamourette'
date: '2026-04-01'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**

31 functional requirements across 6 capability domains:

| Domain | FRs | Architectural Impact |
|--------|-----|---------------------|
| Backup & Recovery (FR1-FR6) | 6 | Host-level Restic agents on both hosts, Ansible-managed cron, configurable retention, backend-agnostic restore |
| Monitoring & Alerting (FR7-FR13) | 7 | Extends existing Prometheus/Grafana stack, adds alert rules + email notification channel, backup status dashboard |
| Centralized Logging (FR14-FR18) | 5 | Loki + Promtail added to observability stack, Promtail on both hosts via Docker socket, auto-discovery of new containers |
| Authentication & Access (FR19-FR23) | 5 | Authelia as Traefik forward-auth middleware, session-based SSO, auto-protects new Traefik-routed services |
| Update Awareness (FR24-FR28) | 5 | Diun for container images, cron scripts for apt + tool versions, daily digest aggregation |
| Email Notifications (FR29-FR31) | 3 | SMTP relay (prerequisite for all notification-capable services), outbound-only |

**Non-Functional Requirements:**

| Category | Key Constraints |
|----------|----------------|
| Performance | Grafana < 3s load, Loki queries < 5s for 30 days, backups < 2h nightly, no service degradation during backup I/O |
| Security | HTTPS-only SSO cookies, Restic AES-256 encryption at rest, secrets in env files not git, no unauthenticated access |
| Reliability | No silent backup failures, auto-restart policies, SMTP retry (3x), Promtail reconnects on container restart, Loki handles ingestion spikes |
| Integration | Traefik forward-auth (Authelia), Grafana datasource (Loki), Docker socket (Promtail + Diun), host filesystem (Restic) |

**Scale & Complexity:**

- Primary domain: Infrastructure/DevOps (IaC + container orchestration + observability)
- Complexity level: Medium — multiple integrating systems across 2 nodes, single-user, no HA/compliance requirements
- Estimated architectural components: 6 new stacks/services (SMTP relay, Authelia, Loki, Promtail x2, Diun, Restic x2) plus extensions to existing observability and infra-core stacks

### Technical Constraints & Dependencies

| Constraint | Source | Impact |
|-----------|--------|--------|
| Existing Traefik v3 label system | homelab-apps conventions | Authelia must integrate via forward-auth middleware labels, not standalone config |
| Docker Compose v2 standard | homelab-apps conventions | All new stacks follow existing patterns: pinned tags, health checks, resource limits, proxy network |
| Ansible role-based deployment | homelab-infra conventions | Host-level agents (Restic, Promtail, apt checks) managed as Ansible roles, not ad-hoc scripts |
| LXC containers, not VMs | Proxmox topology | Promtail Docker socket access may need LXC configuration; privileged mode only on ct-media-01 |
| `.env.sample` + `.env` pattern | homelab-apps security model | Every new stack needs sample env committed, real env gitignored |
| 2-node topology (pve1/pve2) | Physical infrastructure | Services targeting "both hosts" need deployment to ct-docker-01 (pve1) and ct-media-01 (pve1) — both on same node currently |
| No existing SMTP relay | PRD gap analysis | Must be provisioned before any alerting/notification capability can function |
| PUID/PGID=1000, TZ=Europe/Brussels | homelab-apps conventions | All new containers inherit these defaults |

### Cross-Cutting Concerns Identified

| Concern | Affected Components | Architectural Approach Needed |
|---------|-------------------|-------------------------------|
| Secret management | SMTP creds, Authelia secrets, Restic password, Grafana SMTP config | Consistent `.env` pattern; Ansible may template some secrets |
| Multi-host deployment | Promtail, Restic, Diun, apt checks | Ansible roles that target both hosts; Docker stacks vs host-level agents distinction |
| Disk space pressure | Loki logs, Restic snapshots, Prometheus TSDB | Retention policies per service + Prometheus alerting at 80% disk threshold |
| Service discovery | Promtail (log collection), Diun (image checks), Authelia (SSO protection) | Docker socket access + Traefik label conventions — new services auto-detected |
| Ansible template expansion | New IPs, new stack configs, new cron jobs | Existing 9 Jinja2 templates will grow; new templates needed for backup schedules, SMTP config |
| Deployment ordering | SMTP → Observability → Logging → SSO → Backup → Updates | Each capability independent except SMTP prerequisite; architecture must document deploy sequence |
| Monitoring of monitoring | Backup jobs, Promtail health, Loki ingestion, SMTP delivery | Meta-monitoring: Prometheus must scrape the new observability components themselves |

## Starter Template Evaluation

### Primary Technology Domain

Infrastructure/DevOps — IaC provisioning + container orchestration + observability. This is a brownfield project extending an operational platform, not a greenfield application.

### Starter Template Decision: Not Applicable

**Rationale:** This project adds capabilities to an existing, fully operational infrastructure stack. The "starter" is the existing codebase across three repositories:

- **homelab-infra** — Terraform modules, Ansible roles/playbooks, deployment scripts
- **homelab-apps** — 16 Docker Compose stacks with established conventions
- **homelab-playbook** — BMAD orchestration and planning artifacts

New capabilities (SMTP, Authelia, Loki, Promtail, Restic, Diun) will be implemented as new Docker Compose stacks and Ansible roles following existing patterns, not generated from a starter template.

### Established Technical Stack

| Layer | Technology | Version | Convention |
|-------|-----------|---------|------------|
| Provisioning | Terraform | >= 1.6 | Module-based, telmate/proxmox provider |
| Config Management | Ansible | >= 2.15 | Role-based, Jinja2 templates |
| Container Runtime | Docker + Compose | 24.0+ / v2 | Pinned tags, health checks, resource limits |
| Reverse Proxy | Traefik | v3.0.2 | Docker label-based routing, ACME via Cloudflare |
| Monitoring | Prometheus + Grafana | Latest | Scrape configs, dashboard-as-code |
| Deployment | Portainer CE | Latest | GitOps webhooks, stack-targets.yml mapping |
| Secrets | `.env` files | N/A | `.env.sample` committed, `.env` gitignored |
| Defaults | All containers | N/A | PUID/PGID=1000, TZ=Europe/Brussels, proxy network |

### New Stack Convention Template

All new Docker Compose stacks will follow this established pattern:

```yaml
# Pattern: Docker Compose v2, pinned tags, health checks, resource limits
services:
  service-name:
    image: vendor/image:x.y.z          # Pinned version, never :latest
    container_name: service-name
    restart: unless-stopped
    environment:
      - PUID=1000
      - PGID=1000
      - TZ=Europe/Brussels
    volumes:
      - /opt/appdata/stack-name/service:/config
    networks:
      - proxy                           # For Traefik-routed services
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.service.rule=Host(`service.bi-services.be`)"
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 512M
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:port/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL

networks:
  proxy:
    external: true
```

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
- SMTP relay approach — prerequisite for all notification capabilities
- Authelia integration model — affects all Traefik-routed service access
- Loki storage mode — determines observability stack extension pattern

**Important Decisions (Shape Architecture):**
- Restic backup target and migration path
- Promtail deployment model across hosts
- Update check aggregation strategy

**Deferred Decisions (Post-MVP):**
- Native OIDC integration for Grafana/n8n/Portainer (Phase 2)
- Self-healing via n8n automation (Phase 3)
- Renovate/Dependabot for container image version PRs (Phase 3)
- One-click disaster recovery playbook (Phase 3)

### Email & Notifications

| Decision | Choice | Rationale |
|----------|--------|-----------|
| SMTP relay | Docker container (lightweight relay image) | Follows containerization convention, single config point, all services reference relay hostname on Docker network |
| Relay placement | ct-docker-01, on proxy network | Central to most notification consumers (Grafana, Diun, backup scripts) |
| Upstream SMTP | Gmail/Outlook app password as relay target | Simplest outbound delivery, no MX record management needed |
| Failure handling | Log failed deliveries, Prometheus metrics if relay exposes them | FR31: failed deliveries visible to operator |

**Cascading:** All services needing email (Grafana, Diun, Restic report scripts, apt check scripts) will use `smtp-relay:25` as their SMTP host on the Docker network.

### Authentication & Security

| Decision | Choice | Rationale |
|----------|--------|-----------|
| SSO provider | Authelia (single binary, YAML config) | PRD-specified; lightweight for single-user homelab, no PostgreSQL dependency |
| Session storage | File-based (default) | Single-user, no HA requirement; persisted via `/opt/appdata/authelia/` volume |
| Traefik integration | Forward-auth middleware via Docker labels | Standard pattern; new services auto-protected by inheriting middleware labels |
| 2FA | Optional TOTP, not enforced | FR23: operator can enable; not required for homelab |
| Session duration | Configurable, default 7 days | Minimize re-authentication for daily use while maintaining security |

**Cascading:** Traefik infra-core stack needs a new `authelia` forward-auth middleware definition. All existing and new Traefik-routed services add the middleware label to be protected.

### Observability & Logging

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Log aggregation | Loki (single-binary, filesystem mode) | Homelab scale (32 containers), no external dependencies, native Grafana integration |
| Log collection | Promtail as Docker container on each host | Docker socket bind-mount for auto-discovery, follows containerization convention |
| Loki retention | 30 days (configurable) | PRD starting point; tune based on disk usage via Prometheus alerts |
| Loki placement | ct-docker-01, in observability stack | Co-located with Grafana for minimal network latency on queries |
| Promtail placement | Both ct-docker-01 and ct-media-01 | FR14: collect from all containers on both hosts |
| Alerting channel | Grafana → SMTP relay → email | FR10-FR11: email notifications for service failures and unexpected restarts |

**Cascading:** Observability stack Docker Compose gets Loki + Promtail services added. Promtail on ct-media-01 needs its own deployment (either separate stack or Ansible-managed). Grafana gets Loki as additional datasource.

### Backup & Recovery

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Backup tool | Restic (encrypted, deduplicated, incremental) | PRD-specified; supports backend migration without job reconfiguration |
| Backup target (MVP) | Local path on Proxmox host (`/mnt/backups/restic/`) | Fastest MVP, PRD-specified starting point |
| Backup target (future) | NAS when third node added | Restic's `--repo` flag makes migration a config change, not an architecture change |
| Backup execution | Ansible-managed systemd timer or cron on each container host | Host-level operation (not containerized) — backs up `/opt/appdata/` filesystem paths |
| Schedule | 02:00 nightly | Off-peak to minimize I/O impact on running services |
| Retention | 7 daily, 4 weekly, 3 monthly | PRD-specified; `restic forget --keep-daily 7 --keep-weekly 4 --keep-monthly 3` |
| Failure notification | Script sends email via SMTP relay on failure | FR: no silent failures |
| Repo password | Stored in `.env` file on each host, Ansible-templated | Consistent with existing secrets management |

**Cascading:** Restic is a host-level agent, NOT a Docker container — it needs filesystem access to `/opt/appdata/`. Ansible role manages installation, cron/timer, and config. Backup status exported to Prometheus via textfile collector or custom exporter for Grafana dashboard.

### Update Awareness

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Container image checks | Diun (Docker Image Update Notifier) | PRD-specified; Docker socket read-only access |
| System package checks | Ansible-managed cron script (`apt update && apt list --upgradable`) | Runs on containers + Proxmox nodes |
| Tool version checks | Cron script checking Terraform, Ansible, Node.js, Docker versions | Compare installed vs latest release |
| Notification aggregation | Separate emails per tool | Simplest MVP; each tool independently testable and debuggable |
| Diun placement | Docker container on each host | Needs Docker socket access to detect running images |
| Digest schedule | Daily (matching PRD) | All checks run overnight, emails arrive by morning |

**Cascading:** Diun needs Docker socket read-only mount. Apt/tool check scripts managed by Ansible cron role. All notification scripts use SMTP relay.

### Infrastructure & Deployment

| Decision | Choice | Rationale |
|----------|--------|-----------|
| New stack placement | Authelia + SMTP relay + Diun on ct-docker-01; Promtail on both hosts; Restic on both hosts | Centralize coordination services, distribute collection agents |
| Stack organization | New stacks: `authelia/`, `smtp-relay/`, `update-checks/` in homelab-apps; Loki + Promtail extend `observability/` | Follows existing stack-per-concern pattern |
| Ansible roles | New roles: `restic-backup`, `apt-check`, `tool-version-check` | Host-level agents managed as Ansible roles |
| Deployment order | 1. SMTP relay → 2. Observability → 3. Loki + Promtail → 4. Authelia → 5. Restic → 6. Diun + update checks | Each step delivers standalone value; SMTP first as prerequisite |
| CI/CD | Extend existing `validate.yml` GitHub Action for new stacks | New stacks get compose syntax + YAML lint + secret scan validation |

### Decision Impact Analysis

**Implementation Sequence:**
```
1. SMTP Relay        → Enables email for everything downstream
2. Observability     → Deploy Prometheus + Grafana (existing stack)
3. Logging           → Add Loki + Promtail to observability stack
4. SSO               → Authelia + Traefik forward-auth middleware
5. Backup            → Restic agents + Ansible roles on both hosts
6. Update Checks     → Diun + cron scripts + email digests
```

**Cross-Component Dependencies:**
```
SMTP Relay ←── Grafana alerting
           ←── Restic failure notifications
           ←── Diun notifications
           ←── Apt check notifications
           ←── Tool version check notifications

Traefik    ←── Authelia forward-auth middleware (modifies infra-core)

Docker Socket ←── Promtail (log discovery)
              ←── Diun (image version detection)

Prometheus ←── New scrape targets (Loki, Authelia, SMTP relay if metrics exposed)

Grafana    ←── Loki datasource (new)
           ←── Alert rules + email notification channel (new)
           ←── Backup status dashboard (new)
           ←── Update status dashboard (new)
```

## Implementation Patterns & Consistency Rules

### Critical Conflict Points Identified

7 areas where AI agents could make different choices, resolved below.

### Docker Compose Patterns

**All AI agents MUST follow these conventions for new stacks:**

| Pattern | Rule | Example |
|---------|------|---------|
| Service names | kebab-case | `smtp-relay`, `promtail` |
| Container names | Match service name | `container_name: smtp-relay` |
| Image tags | Pinned semver, never `:latest` | `image: authelia/authelia:4.38.0` |
| Environment | PUID/PGID/TZ on all containers | `PUID=1000`, `PGID=1000`, `TZ=Europe/Brussels` |
| Restart policy | `unless-stopped` | All long-running services |
| Networks | Join `proxy` (external) for Traefik-routed; internal network for inter-service | `networks: [proxy]` |
| Volumes | Bind mount to `/opt/appdata/{stack-name}/{service}/` | `/opt/appdata/authelia/config:/config` |
| Security | `no-new-privileges:true` + `cap_drop: ALL` on all containers | Selective `cap_add` only when required |
| Resource limits | Always set `deploy.resources.limits` for CPU + memory | Match estimates from resource planning |
| Health checks | Required on all services, 30s interval | curl, wget, or native health endpoint |
| Labels | Traefik v3 labels for routed services | `traefik.http.routers.{service}.rule=Host(...)` |

**Anti-patterns:**
- Never use `:latest` tags
- Never publish host ports directly (Traefik handles routing)
- Never use `privileged: true` unless explicitly required (only ct-media-01 GPU)
- Never hardcode IPs in Compose files (use Docker DNS hostnames)

### Ansible Role Patterns

**Role structure (mandatory for new roles):**

```
roles/
  {role-name}/
    tasks/main.yml        # Required: task definitions
    handlers/main.yml     # Required if services need restart triggers
    templates/*.j2        # Jinja2 templates for dynamic config
    defaults/main.yml     # Default variables (overridable)
    files/                # Static files (scripts, configs)
```

| Pattern | Rule | Example |
|---------|------|---------|
| Role naming | kebab-case | `restic-backup`, `apt-check` |
| Variable prefix | Role name as prefix | `restic_backup_schedule`, `apt_check_recipients` |
| Idempotency | All tasks must be idempotent | Use `creates:`, `when:`, `stat` checks |
| Tags | Tag all tasks with role name | `tags: [restic-backup]` |
| Handlers | Use handlers for service restarts, not inline `command` | `notify: restart restic-timer` |

### Environment Variable Patterns

**`.env.sample` conventions:**

| Pattern | Rule | Example |
|---------|------|---------|
| Naming | UPPER_SNAKE_CASE, prefixed by stack context when ambiguous | `SMTP_HOST`, `SMTP_PORT`, `AUTHELIA_JWT_SECRET` |
| Shared vars | Generic name within stack (no prefix needed when unambiguous) | `DB_PASSWORD` in a stack with one database |
| Cross-stack vars | Prefix with service name | `GRAFANA_SMTP_HOST` vs `DIUN_SMTP_HOST` — but both point to `smtp-relay` |
| Secrets | Placeholder value indicating generation method | `AUTHELIA_JWT_SECRET=generate-with-openssl-rand-base64-32` |
| Comments | Document each variable | `# SMTP relay hostname (Docker service name on proxy network)` |

**Rule:** Every new stack commits `.env.sample` with all variables documented. `.env` is always gitignored.

### Scheduled Task Patterns

**Decision: systemd timers** for all new scheduled tasks (Restic backup, apt checks, tool version checks).

| Pattern | Rule | Rationale |
|---------|------|-----------|
| Timer type | systemd timer + service unit | Journald logging, dependency management, status introspection via `systemctl` |
| Timer naming | `{task-name}.timer` + `{task-name}.service` | `restic-backup.timer`, `apt-check.timer` |
| Deployment | Ansible-templated unit files in `/etc/systemd/system/` | Consistent with IaC approach |
| Failure notification | `OnFailure=` directive pointing to email notification service | Systemd-native failure handling, no wrapper scripts needed |
| Logging | Stdout/stderr to journald (default) | Promtail can collect from journald if configured; `journalctl -u restic-backup` for debugging |

**Anti-pattern:** Do not use raw crontab entries. Systemd timers provide better observability, dependency ordering, and failure handling.

### Script Output Patterns

**Decision: plain text with structured prefix.**

```
[2026-04-01T02:15:00Z] [OK] restic-backup: /opt/appdata/infra-core backed up (1.2GB, 45s)
[2026-04-01T02:15:45Z] [OK] restic-backup: /opt/appdata/observability backed up (890MB, 32s)
[2026-04-01T02:16:00Z] [FAIL] restic-backup: /opt/appdata/organizr - permission denied
```

| Pattern | Rule |
|---------|------|
| Timestamp | ISO 8601 with timezone (`[2026-04-01T02:15:00Z]`) |
| Severity | `[OK]`, `[WARN]`, `[FAIL]` |
| Source | Script name after severity |
| Message | Human-readable description with context |

### Traefik Middleware Patterns

**Authelia forward-auth integration:**

```yaml
# Define the middleware ONCE in infra-core:
- "traefik.http.middlewares.authelia.forwardAuth.address=http://authelia:9091/api/authz/forward-auth"
- "traefik.http.middlewares.authelia.forwardAuth.trustForwardHeader=true"
- "traefik.http.middlewares.authelia.forwardAuth.authResponseHeaders=Remote-User,Remote-Groups,Remote-Email"

# Every protected service adds:
- "traefik.http.routers.{service}.middlewares=authelia@docker"
```

| Pattern | Rule |
|---------|------|
| Middleware name | `authelia` (consistent across all stacks) |
| Protected by default | All Traefik-routed services add the middleware label |
| Exceptions | Health check endpoints, Prometheus scrape endpoints — explicitly exclude from auth |

### Prometheus Integration Patterns

| Pattern | Rule |
|---------|------|
| Scrape config | Add new targets to `prometheus.yml` in observability stack |
| Metrics port | Services expose `/metrics` on default port; add Traefik labels only if web UI needed |
| Alert rules | One rule file per capability domain: `backup-alerts.yml`, `service-alerts.yml` |
| Alert naming | `{Domain}{Condition}` — `BackupFailed`, `ServiceDown`, `DiskSpaceWarning` |
| Dashboard naming | `{Domain} Overview` — "Backup Overview", "Service Health Overview" |

### Enforcement Guidelines

**All AI agents MUST:**
1. Read the existing stack in the same category before creating a new one
2. Follow the Docker Compose convention template from the Starter Template section exactly
3. Use systemd timers for all scheduled tasks, never crontab
4. Commit `.env.sample` with documented variables for every new stack
5. Add Authelia middleware label to all new Traefik-routed services
6. Add Prometheus scrape targets for all new services that expose metrics
7. Pin all image versions to specific semver tags

**Pattern Verification:**
- `docker compose config` validates Compose syntax
- `ansible-lint` validates role structure
- `detect-secrets scan` validates no hardcoded secrets
- Existing GitHub Actions CI extends to cover new stacks automatically

## Project Structure & Boundaries

### Requirements to Repository Mapping

| FR Category | Target Repo | New Files/Directories |
|------------|-------------|----------------------|
| Email Notifications (FR29-31) | homelab-apps | `stacks/smtp-relay/` |
| Monitoring & Alerting (FR7-13) | homelab-apps | Extend `stacks/observability/`, new alert rules + dashboards |
| Centralized Logging (FR14-18) | homelab-apps + homelab-infra | Extend `stacks/observability/` (Loki), new Promtail on ct-media-01; Ansible role for Promtail config |
| Authentication (FR19-23) | homelab-apps | `stacks/authelia/`, modify `stacks/infra-core/` |
| Backup & Recovery (FR1-6) | homelab-infra | New Ansible role `restic-backup`, systemd units |
| Update Awareness (FR24-28) | homelab-apps + homelab-infra | `stacks/update-checks/` (Diun), Ansible roles `apt-check`, `tool-version-check` |

### homelab-apps — New & Modified Stacks

```
homelab-apps/
├── stacks/
│   ├── smtp-relay/                          # NEW STACK
│   │   ├── docker-compose.yml
│   │   ├── .env.sample
│   │   └── .gitignore
│   │
│   ├── authelia/                            # NEW STACK
│   │   ├── docker-compose.yml
│   │   ├── config/
│   │   │   └── configuration.yml.sample
│   │   ├── .env.sample
│   │   └── .gitignore
│   │
│   ├── update-checks/                       # NEW STACK
│   │   ├── docker-compose.yml
│   │   ├── config/
│   │   │   └── diun.yml.sample
│   │   ├── .env.sample
│   │   └── .gitignore
│   │
│   ├── observability/                       # MODIFIED STACK
│   │   ├── docker-compose.yml               # ADD: loki, promtail services
│   │   ├── config/
│   │   │   ├── prometheus.yml               # MODIFY: add new scrape targets
│   │   │   ├── loki-config.yml              # NEW
│   │   │   ├── promtail-config.yml          # NEW
│   │   │   └── alerting/                    # NEW DIRECTORY
│   │   │       ├── service-alerts.yml
│   │   │       ├── backup-alerts.yml
│   │   │       ├── disk-alerts.yml
│   │   │       └── notification-channel.yml
│   │   ├── dashboards/                      # NEW DIRECTORY
│   │   │   ├── service-health.json
│   │   │   ├── backup-status.json
│   │   │   └── update-status.json
│   │   └── .env.sample                      # MODIFY: add LOKI_*, GRAFANA_SMTP_* vars
│   │
│   ├── infra-core/                          # MODIFIED STACK
│   │   ├── docker-compose.yml               # MODIFY: add authelia middleware labels
│   │   └── config/
│   │       └── dynamic/
│   │           └── authelia-middleware.yml   # NEW
│   │
│   └── [all existing stacks]               # MODIFY: add authelia middleware label
│
├── .github/
│   └── workflows/
│       └── validate.yml                     # MODIFY: add new stacks to validation
│
└── stack-targets.yml                        # MODIFY: add new stacks to endpoint mapping
```

### homelab-infra — New Ansible Roles

```
homelab-infra/
├── ansible/
│   ├── roles/
│   │   ├── restic-backup/                   # NEW ROLE
│   │   │   ├── tasks/main.yml
│   │   │   ├── handlers/main.yml
│   │   │   ├── templates/
│   │   │   │   ├── restic-backup.service.j2
│   │   │   │   ├── restic-backup.timer.j2
│   │   │   │   ├── restic-backup.sh.j2
│   │   │   │   └── restic-notify-failure.sh.j2
│   │   │   ├── defaults/main.yml
│   │   │   └── files/
│   │   │       └── restic-check.sh
│   │   │
│   │   ├── apt-check/                       # NEW ROLE
│   │   │   ├── tasks/main.yml
│   │   │   ├── templates/
│   │   │   │   ├── apt-check.service.j2
│   │   │   │   ├── apt-check.timer.j2
│   │   │   │   └── apt-check.sh.j2
│   │   │   └── defaults/main.yml
│   │   │
│   │   ├── tool-version-check/              # NEW ROLE
│   │   │   ├── tasks/main.yml
│   │   │   ├── templates/
│   │   │   │   ├── tool-check.service.j2
│   │   │   │   ├── tool-check.timer.j2
│   │   │   │   └── tool-check.sh.j2
│   │   │   └── defaults/main.yml
│   │   │
│   │   ├── promtail-media/                  # NEW ROLE
│   │   │   ├── tasks/main.yml
│   │   │   ├── templates/
│   │   │   │   ├── docker-compose.yml.j2
│   │   │   │   └── promtail-config.yml.j2
│   │   │   └── defaults/main.yml
│   │   │
│   │   └── [existing roles unchanged]
│   │
│   ├── playbooks/
│   │   └── deploy-production-readiness.yml  # NEW
│   │
│   └── inventory/
│       └── group_vars/
│           └── all.yml                      # MODIFY: add smtp, restic vars
│
└── terraform/                               # NO CHANGES
```

### Architectural Boundaries

**Repository Boundaries:**

| Boundary | Rule | Violation Example |
|----------|------|-------------------|
| homelab-apps owns Docker stacks | All Docker Compose files live here | Never put docker-compose.yml in homelab-infra |
| homelab-infra owns host config | Ansible roles, systemd units, host-level tools | Never SSH and manually configure |
| homelab-playbook owns planning | PRDs, architecture, stories, sprint tracking | Never put implementation code here |

**Network Boundaries:**

```
External (Internet)
    │ HTTPS :443
    ▼
Traefik (ct-docker-01, proxy network)
    │
    ├── authelia (forward-auth, proxy network)
    │
    ├── proxy network services (ct-docker-01)
    │   ├── smtp-relay :25 (internal only, NOT Traefik-routed)
    │   ├── loki :3100 (internal only, Grafana datasource)
    │   ├── promtail → loki (internal)
    │   └── diun (no network exposure, Docker socket only)
    │
    └── HTTP proxy → ct-media-01 services
        └── promtail-media → loki on ct-docker-01 (cross-host)
```

**Data Boundaries:**

| Data Type | Location | Backup Scope |
|-----------|----------|-------------|
| Application data | `/opt/appdata/{stack}/` per host | YES — Restic nightly |
| Media files | `/media/` on ct-media-01 | NO — re-downloadable |
| Loki logs | `/opt/appdata/observability/loki/` | YES — included in appdata backup |
| Prometheus TSDB | `/opt/appdata/observability/prometheus/` | YES — included in appdata backup |
| Authelia sessions | `/opt/appdata/authelia/` | YES — included in appdata backup |
| Restic repo | `/mnt/backups/restic/` on Proxmox host | NO — this IS the backup |

### Integration Points

**Internal (Docker network):**
- All services → `smtp-relay:25` for outbound email
- Promtail → `loki:3100` for log ingestion (HTTP push)
- Grafana → `loki:3100` as datasource (LogQL queries)
- Prometheus → all services with `/metrics` endpoints (HTTP scrape)
- All Traefik routers → `authelia:9091` for forward-auth

**Cross-host (ct-docker-01 ↔ ct-media-01):**
- Promtail on ct-media-01 → Loki on ct-docker-01 (HTTP, needs IP or DNS)
- Diun on ct-docker-01 watches local Docker; separate Diun on ct-media-01 watches its Docker
- Restic runs independently on each host, backing up local `/opt/appdata/`

**External:**
- SMTP relay → upstream provider (Gmail/Outlook, port 587 TLS)
- Diun → Docker Hub / GHCR registries (HTTPS, checking image digests)
- Tool version check → GitHub API (HTTPS, comparing release versions)

## Architecture Validation Results

### Coherence Validation

**Decision Compatibility:**
- All technology choices are compatible and well-established in the Docker/homelab ecosystem
- One conflict identified and resolved: host-level scripts (Restic, apt-check) need SMTP access → solved by binding relay port to `127.0.0.1:25` on the host

**Correction to Email & Notifications decision:**
- SMTP relay publishes `127.0.0.1:25:25` on the host
- Docker services use `smtp-relay:25` (Docker DNS)
- Host scripts (systemd units) use `localhost:25`
- No external exposure (bound to loopback only)

**Pattern Consistency:** All implementation patterns align with existing codebase conventions. No contradictions between Docker Compose, Ansible role, and naming patterns.

**Structure Alignment:** Project structure directly supports all architectural decisions. Every component has a defined home across the three repositories.

### Requirements Coverage

**Functional Requirements: 31/31 covered**

| Category | FRs | Architectural Support |
|----------|-----|----------------------|
| Backup & Recovery | FR1-FR6 | Restic Ansible role, systemd timers, configurable retention, CLI restore |
| Monitoring & Alerting | FR7-FR13 | Prometheus scrape, Grafana dashboards, email alerts via SMTP relay |
| Centralized Logging | FR14-FR18 | Loki + Promtail, Docker socket auto-discovery, LogQL via Grafana |
| Authentication | FR19-FR23 | Authelia forward-auth, persistent sessions, optional TOTP |
| Update Awareness | FR24-FR28 | Diun + apt-check + tool-check, daily emails |
| Email | FR29-FR31 | SMTP relay container, localhost bind, delivery logging |

**Non-Functional Requirements: All addressed**

| NFR | Architectural Support |
|-----|----------------------|
| Grafana < 3s load | Resource limits, local Loki filesystem, Prometheus on same host |
| Loki queries < 5s (30 days) | Filesystem storage mode, 30-day retention with auto-cleanup |
| Backups < 2h nightly | Restic incremental/deduplicated, scheduled at 02:00 off-peak |
| No backup I/O degradation | Off-peak scheduling + Prometheus disk I/O monitoring |
| HTTPS-only SSO | Authelia secure cookies, Traefik TLS termination |
| Encrypted backups | Restic AES-256 at rest |
| No silent failures | systemd `OnFailure=` + SMTP notification |
| Auto-restart services | Docker `restart: unless-stopped` |
| SMTP retry | Relay handles retry logic |

### Gap Analysis Results

| # | Gap | Priority | Resolution |
|---|-----|----------|------------|
| 1 | Host scripts can't reach Docker-only SMTP relay | Critical | **Resolved:** bind `127.0.0.1:25:25`; updated in decisions |
| 2 | Cross-host Promtail → Loki needs IP | Important | Ansible renders Loki URL from Terraform outputs (existing pattern) |
| 3 | Grafana dashboard provisioning not specified | Minor | Use provisioning directory with bind-mount + provisioning config |
| 4 | Restic backup metrics for Prometheus | Minor | Textfile collector: backup script writes `.prom` file, node-exporter scrapes |

### Architecture Completeness Checklist

**Requirements Analysis**
- [x] Project context thoroughly analyzed (31 FRs, 6 domains)
- [x] Scale and complexity assessed (medium, 2-node, single-user)
- [x] Technical constraints identified (8 constraints)
- [x] Cross-cutting concerns mapped (7 concerns)

**Architectural Decisions**
- [x] Critical decisions documented (SMTP, Authelia, Loki, Restic, Promtail, Diun)
- [x] Technology stack fully specified with rationale
- [x] Integration patterns defined (Docker network, cross-host, external)
- [x] Deployment sequence documented (6-step ordered)

**Implementation Patterns**
- [x] Docker Compose conventions (11 rules + anti-patterns)
- [x] Ansible role structure defined
- [x] Environment variable conventions
- [x] Scheduled task patterns (systemd timers)
- [x] Script output format
- [x] Traefik middleware patterns
- [x] Prometheus integration patterns
- [x] Enforcement guidelines (7 mandatory rules)

**Project Structure**
- [x] Complete directory structure for homelab-apps changes
- [x] Complete directory structure for homelab-infra changes
- [x] Repository boundaries defined
- [x] Network boundaries mapped
- [x] Data boundaries with backup scope
- [x] All integration points documented

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION

**Confidence Level:** High — brownfield project with established conventions, clear boundaries, and well-understood technology choices.

**Key Strengths:**
- Builds on proven, operational infrastructure with established patterns
- Every new component follows existing conventions — no new paradigms
- Clear separation: Docker stacks in homelab-apps, host agents in homelab-infra
- Each capability delivers standalone value with documented deployment order
- All 31 functional requirements mapped to specific components and locations

**Areas for Future Enhancement:**
- Native OIDC for Grafana/n8n/Portainer (Phase 2)
- n8n aggregation of update digests
- Automated restore testing
- Self-healing via n8n

### Implementation Handoff

**AI Agent Guidelines:**
- Follow all architectural decisions exactly as documented
- Use implementation patterns consistently across all components
- Respect repository boundaries (Docker stacks → homelab-apps, host config → homelab-infra)
- Refer to this document for all architectural questions
- Read existing stacks before creating new ones

**First Implementation Priority:**
Deploy SMTP relay stack — prerequisite for all downstream notification capabilities.
