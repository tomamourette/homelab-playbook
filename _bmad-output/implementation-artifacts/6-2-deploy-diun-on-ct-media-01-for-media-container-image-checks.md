# Story 6.2: Deploy Diun on ct-media-01 for Media Container Image Checks

**Epic:** 6 - Update Checks
**Status:** done
**Implements:** FR24, FR27
**Target repo:** homelab-infra

---

## User Story

**As a** homelab operator,
**I want** Diun monitoring container images on ct-media-01 (Plex, Sonarr, Radarr, etc.),
**So that** image update detection covers BOTH container hosts, not just ct-docker-01.

---

## Acceptance Criteria

### AC1: Diun deployed on ct-media-01 via Ansible role
**Given** the `diun-media` Ansible role is applied to ct-media-01
**When** the role runs
**Then** a Diun container is deployed on ct-media-01 via Docker Compose
**And** it monitors all running container images on ct-media-01 via Docker socket (read-only)
**And** it sends email notifications for images with newer versions via smtp-relay on ct-docker-01

### AC2: Media container update detection
**Given** a media container (Plex, Sonarr, Radarr, etc.) has a newer image available
**When** Diun runs its scheduled check on ct-media-01
**Then** it detects the update and sends an email notification listing the image and available version

### AC3: Architecture compliance
**Given** the Ansible role follows homelab-infra conventions
**When** inspected
**Then** it uses the standard role structure (tasks, templates, defaults, handlers)
**And** variables are prefixed with `diun_media_`
**And** all tasks are tagged with `diun-media`
**And** the role is idempotent (re-running produces no changes if already applied)
**And** the Diun container uses a pinned semver image tag, resource limits, health check, `restart: unless-stopped`, `no-new-privileges:true`, `cap_drop: ALL`

---

## Tasks

- [x] Create `ansible/roles/diun-media/defaults/main.yml`
  - [x] All variables prefixed with `diun_media_`
  - [x] Configurable: image version, schedule, SMTP host/port/from/to, resource limits
  - [x] Default SMTP host: ct-docker-01 IP (192.168.50.194)
  - [x] Default schedule: 06:30 daily (staggered from ct-docker-01 at 06:00)
- [x] Create `ansible/roles/diun-media/tasks/main.yml`
  - [x] Validate SMTP from/to are configured (assert)
  - [x] Create data directory for BoltDB state persistence
  - [x] Deploy environment file (mode 0600)
  - [x] Deploy Docker Compose file
  - [x] Ensure Docker is running
  - [x] Pull Diun image
  - [x] Deploy via docker compose up
  - [x] Wait for container to be running
  - [x] All tasks tagged with `diun-media`
- [x] Create `ansible/roles/diun-media/templates/docker-compose.yml.j2`
  - [x] Pinned semver image (variable)
  - [x] container_name: diun-media
  - [x] restart: unless-stopped
  - [x] Docker socket read-only mount
  - [x] Data volume for BoltDB persistence
  - [x] Environment from .env file
  - [x] security_opt: no-new-privileges:true
  - [x] cap_drop: ALL
  - [x] Resource limits (CPU + memory)
  - [x] Health check (file-based with version fallback)
  - [x] json-file logging with rotation
  - [x] No proxy network (uses host IP for cross-host SMTP)
  - [x] No Traefik labels (internal-only service)
- [x] Create `ansible/roles/diun-media/templates/diun-media.env.j2`
  - [x] All Diun configuration via environment variables (matching 6.1 pattern D-602)
  - [x] Docker provider with watchByDefault=true (FR24)
  - [x] SMTP notification pointing to ct-docker-01
- [x] Create `ansible/roles/diun-media/handlers/main.yml`
  - [x] Handler for restarting Diun container on config changes

---

## Dev Notes

### Architecture Compliance

| # | Convention | Application |
|---|-----------|-------------|
| 1 | Pinned semver image tag (ARCH-1) | `crazymax/diun:4.28.0` (variable) |
| 2 | no-new-privileges + cap_drop ALL (ARCH-2) | Yes, no cap_add needed (D-603) |
| 3 | Role structure (tasks, templates, defaults, handlers) | Yes |
| 4 | Variable prefix: role name | `diun_media_*` |
| 5 | All tasks tagged | `diun-media` |
| 6 | Idempotent | Yes — docker compose up is idempotent, template changes trigger handler |
| 7 | Resource limits | 0.5 CPU, 256M memory |
| 8 | Health check | File-based (diun.db) with version fallback |
| 9 | Logging | json-file, 10m, 3 files |

### Cross-Host SMTP Access

ct-media-01 cannot reach smtp-relay via Docker DNS (smtp-relay is on ct-docker-01's proxy network). Instead, Diun-media uses the ct-docker-01 host IP (192.168.50.194) directly.

**Prerequisite:** The smtp-relay port binding on ct-docker-01 must be changed from `127.0.0.1:25:25` to `192.168.50.194:25:25` (or `0.0.0.0:25:25` with appropriate firewall rules) to allow cross-host access. This is documented as decision D-605.

### Differences from Story 6.1 (ct-docker-01 Diun)

| Aspect | 6.1 (ct-docker-01) | 6.2 (ct-media-01) |
|--------|--------------------|--------------------|
| Deployment | Docker Compose in homelab-apps | Ansible role in homelab-infra |
| SMTP access | Docker DNS (`smtp-relay:25`) | Host IP (`192.168.50.194:25`) |
| Network | proxy (external) | Default bridge (no proxy needed) |
| Container name | `diun` | `diun-media` |
| Schedule | 06:00 | 06:30 (staggered) |
| Data dir | `/opt/appdata/update-checks/diun` | `/opt/appdata/diun-media/data` |

### Reference Files

- **Pattern reference:** `ansible/roles/restic-backup/` (Ansible role conventions)
- **Diun reference:** `homelab-apps/stacks/update-checks/docker-compose.yml` (Story 6.1)
- **Architecture:** `_bmad-output/planning-artifacts/architecture.md` (Ansible Role Patterns, Update Awareness)
- **PRD:** FR24 (container image checks on both hosts), FR27 (daily notification emails)
