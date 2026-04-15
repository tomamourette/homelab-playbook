# Story 6.1: Create Diun Docker Compose Stack for Container Image Checks

**Epic:** 6 - Update Checks
**Status:** ready-for-dev
**Implements:** FR24, FR27
**Target repo:** homelab-apps

---

## User Story

**As a** homelab operator,
**I want** Diun monitoring all running containers for newer image versions,
**So that** I am aware of available updates without manually checking registries.

---

## Acceptance Criteria

### AC1: Container image update detection
**Given** the update-checks stack is deployed on ct-docker-01
**When** Diun runs its scheduled check
**Then** it compares all running container images against their upstream registries
**And** sends an email notification for images with newer versions available
**And** uses `smtp-relay:25` for email delivery

### AC2: Docker socket auto-discovery
**Given** a new container is deployed on ct-docker-01
**When** Diun next runs
**Then** the new container's image is automatically included in the check (Docker socket auto-discovery)

### AC3: Architecture compliance
**Given** the docker-compose.yml is created
**When** inspected for compliance
**Then** Diun has read-only Docker socket access (`/var/run/docker.sock:/var/run/docker.sock:ro`)
**And** uses a pinned semver image tag (not `:latest`)
**And** sets `restart: unless-stopped`, `no-new-privileges:true`, `cap_drop: ALL`
**And** sets resource limits (CPU + memory)
**And** includes a health check
**And** joins the proxy network (for smtp-relay access)
**And** does NOT expose any ports via Traefik (no network exposure, Docker socket only)
**And** uses json-file logging driver with rotation

---

## Tasks

- [x] Create `stacks/update-checks/docker-compose.yml`
  - [x] Pinned Diun image version tag
  - [x] container_name: diun
  - [x] restart: unless-stopped
  - [x] Environment variables from .env (SMTP config, schedule, timezone)
  - [x] Volume: Docker socket read-only mount
  - [x] Volume: Diun config directory
  - [x] Volume: Diun data directory (for state persistence)
  - [x] Join proxy network (for smtp-relay:25 access)
  - [x] Health check
  - [x] Resource limits (cpu + memory)
  - [x] security_opt: no-new-privileges:true
  - [x] cap_drop: ALL
  - [x] Logging driver configuration (json-file with rotation)
  - [x] No Traefik labels (internal-only service)
- [x] Create `stacks/update-checks/config/diun.yml.sample`
  - [x] Watch configuration for Docker provider
  - [x] Schedule: daily (cron expression)
  - [x] Mail notification provider pointing to smtp-relay:25
- [x] Create `stacks/update-checks/.env.sample`
  - [x] TZ with comment
  - [x] DIUN_NOTIF_MAIL_HOST with comment
  - [x] DIUN_NOTIF_MAIL_PORT with comment
  - [x] DIUN_NOTIF_MAIL_FROM with comment
  - [x] DIUN_NOTIF_MAIL_TO with comment
  - [x] DIUN_WATCH_SCHEDULE with comment
- [x] Create `stacks/update-checks/.gitignore`

---

## Dev Notes

### Architecture Compliance Requirements

All Docker Compose conventions must be followed:

| # | Convention | Application |
|---|-----------|-------------|
| 1 | Service names: kebab-case | `diun` |
| 2 | Pinned semver image tag | `crazymax/diun:4.28.0` |
| 3 | container_name set | `diun` |
| 4 | restart: unless-stopped | Yes |
| 5 | Resource limits (CPU + memory) | 0.5 CPU, 256M memory |
| 6 | Health check | Diun built-in or file-based |
| 7 | security_opt: no-new-privileges | Yes |
| 8 | cap_drop: ALL | Yes |
| 9 | Logging: json-file with rotation | 10m, 3 files |
| 10 | proxy network | External, for smtp-relay access |
| 11 | No Traefik labels | Internal-only, no web exposure |

### Docker Socket Security

Diun requires Docker socket access to enumerate running containers and check their image digests against upstream registries. The socket is mounted **read-only** (`:ro`) as Diun only reads container metadata - it never starts, stops, or modifies containers.

### SMTP Notification

Diun sends email notifications via the internal SMTP relay (`smtp-relay:25` on the proxy network). Per architecture decision D-005, Diun sends its own email per update found (separate emails, not a unified digest for MVP).

### Diun Configuration

Diun uses a YAML configuration file (`diun.yml`) for:
- **Watch providers:** Docker socket provider for auto-discovering running containers
- **Notification providers:** Mail via SMTP relay
- **Schedule:** Daily cron expression (default: `0 6 * * *` - 06:00 daily)

### Reference Files

- **Convention reference:** `stacks/smtp-relay/docker-compose.yml` (Story 1.1)
- **Architecture:** `_bmad-output/planning-artifacts/architecture.md` (Update Awareness section)
- **PRD:** FR24 (container image checks), FR27 (daily notification emails)
