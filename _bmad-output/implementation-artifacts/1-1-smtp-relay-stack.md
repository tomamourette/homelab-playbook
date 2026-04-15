# Story 1.1: Create SMTP Relay Docker Compose Stack

**Epic:** 1 - SMTP Relay
**Status:** ready-for-dev
**Implements:** FR29, FR30
**Target repo:** homelab-apps

---

## User Story

**As a** homelab operator,
**I want** an SMTP relay container running on ct-docker-01,
**So that** all services on the Docker network can send outbound email via a single relay.

---

## Acceptance Criteria

### AC1: Docker network email relay
**Given** the smtp-relay stack is deployed on ct-docker-01
**When** a service sends an email to `smtp-relay:25` on the Docker network
**Then** the relay forwards it to the configured upstream SMTP provider (Gmail/Outlook)
**And** the relay is accessible from host scripts via `localhost:25` (bound to `127.0.0.1:25:25`)

### AC2: Configurable upstream SMTP credentials
**Given** the `.env.sample` file exists in the stack directory
**When** the operator copies it to `.env` and fills in credentials
**Then** the relay authenticates to the upstream provider using those credentials
**And** the sender address, upstream host, port, and credentials are all configurable via environment variables

### AC3: Architecture compliance
**Given** the docker-compose.yml is created
**When** inspected for compliance
**Then** it uses a pinned semver image tag (not `:latest`)
**And** sets `restart: unless-stopped`, `no-new-privileges:true`, `cap_drop: ALL`
**And** sets resource limits (CPU + memory)
**And** includes a health check
**And** does NOT expose the relay via Traefik (internal-only service)

---

## Tasks

- [x] Research lightweight SMTP relay Docker images (boky/postfix or similar)
- [x] Create `stacks/smtp-relay/docker-compose.yml`
  - [x] Pinned image version tag
  - [x] container_name: smtp-relay
  - [x] restart: unless-stopped
  - [x] Environment variables from .env (upstream host, port, user, password, from address, allowed networks)
  - [x] Port binding: 127.0.0.1:25:25 for host script access
  - [x] Join proxy network (Docker services use smtp-relay:25)
  - [x] Health check for SMTP service
  - [x] Resource limits (cpu + memory)
  - [x] security_opt: no-new-privileges:true
  - [x] cap_drop: ALL, cap_add only what is required
  - [x] PUID/PGID/TZ environment variables
  - [x] Logging driver configuration (json-file with rotation)
  - [x] No Traefik labels (internal-only service)
- [x] Create `stacks/smtp-relay/.env.sample`
  - [x] SMTP_RELAY_HOST with comment
  - [x] SMTP_RELAY_PORT with comment
  - [x] SMTP_RELAY_USERNAME with comment
  - [x] SMTP_RELAY_PASSWORD with comment
  - [x] SMTP_RELAY_FROM with comment
  - [x] SMTP_ALLOWED_NETWORKS with comment
  - [x] TZ with comment
- [x] Create `stacks/smtp-relay/.gitignore`

---

## Dev Notes

### Architecture Compliance Requirements

All 11 Docker Compose conventions must be followed:

| # | Convention | Application |
|---|-----------|-------------|
| 1 | Service names: kebab-case | `smtp-relay` |
| 2 | Container names: match service | `container_name: smtp-relay` |
| 3 | Image tags: pinned semver | e.g., `boky/postfix:v4.3.0` |
| 4 | Environment: PUID/PGID/TZ | All set, TZ from .env |
| 5 | Restart policy: unless-stopped | Set |
| 6 | Networks: proxy (external) | Joins proxy for Docker DNS access |
| 7 | Volumes: /opt/appdata/{stack}/{service}/ | Postfix spool/config if needed |
| 8 | Security: no-new-privileges + cap_drop ALL | Set; cap_add NET_BIND_SERVICE if binding port 25 inside container |
| 9 | Resource limits: deploy.resources.limits | CPU + memory set |
| 10 | Health checks: required, 30s interval | SMTP port check |
| 11 | Labels: Traefik v3 for routed services | NOT applicable - internal only |

### SMTP Relay Specifics

- **Port binding:** `127.0.0.1:25:25` on the host, so host-level scripts (Restic failure notifications, apt-check, tool-check) can use `localhost:25`
- **Docker DNS:** Other containers on the proxy network use `smtp-relay:25`
- **No Traefik routing:** This is NOT a web service; no Traefik labels needed
- **Outbound-only:** No inbound email, relay to upstream provider only

### .env.sample Pattern

- UPPER_SNAKE_CASE variable names
- Comment above each variable explaining its purpose
- Placeholder values indicating what to fill in
- `.env` is gitignored, `.env.sample` is committed

### Image Decision

Using `boky/postfix` - a lightweight Postfix-based SMTP relay container designed specifically for relaying mail through an upstream provider. Well-maintained, Alpine-based, small footprint.

---

## Testing Strategy

### Manual Verification (Story 1.2 covers full validation)

1. `docker compose config` - verify compose file is valid
2. `docker compose up -d` - verify container starts
3. `docker compose ps` - verify health check passes
4. `docker inspect smtp-relay` - verify security options, resource limits, network
5. Check port binding: `ss -tlnp | grep :25` should show 127.0.0.1:25

### Compose File Linting

- YAML syntax validation
- Docker Compose v2 schema compliance
- No `:latest` tags
- Resource limits present
- Health check present

---

## File List

| File | Action | Path |
|------|--------|------|
| docker-compose.yml | Created | `stacks/smtp-relay/docker-compose.yml` |
| .env.sample | Created | `stacks/smtp-relay/.env.sample` |
| .gitignore | Created | `stacks/smtp-relay/.gitignore` |

---

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2026-04-01 | Story created (Phase 1: CREATE-STORY) | Claude |
| 2026-04-01 | Implementation complete (Phase 2: DEV-STORY) | Claude |
| 2026-04-01 | Code review and fixes applied (Phase 3: CODE-REVIEW) | Claude |

---

## Review Findings

| # | Severity | Finding | Resolution |
|---|----------|---------|------------|
| R1 | High | `cap_drop: ALL` with no `cap_add` would prevent Postfix from starting. Postfix requires NET_BIND_SERVICE (port 25), SETGID/SETUID (privilege dropping), SYS_CHROOT (Postfix chroot jails), DAC_READ_SEARCH (mail queue access), KILL (process management). | Added targeted `cap_add` for exactly the 6 capabilities Postfix requires. |
| R2 | Medium | Health check used `postfix status` which requires process inspection and may fail under restricted capabilities. | Changed to TCP-based health check: `printf 'EHLO healthcheck\n' | nc 127.0.0.1 25 | grep -q '220'` which directly tests SMTP responsiveness. |
| R3 | Medium | No `hostname` set on the container. Postfix uses hostname for HELO/EHLO greeting. Without it, the container ID is used, which upstream providers may reject as suspicious. | Added `hostname: smtp-relay` to the service definition. |
| R4 | Low | `start_period: 15s` was too short for Postfix initialization under resource-constrained environments. | Increased to `start_period: 30s` to allow adequate warm-up time. |

### Review Compliance Checklist

- [x] Architecture patterns: All 11 Docker Compose conventions followed
- [x] PRD FR29: Outbound email capability from any service -- satisfied via proxy network + 127.0.0.1:25 binding
- [x] PRD FR30: Configurable SMTP target -- all credentials/host/port via .env variables
- [x] Security: No hardcoded secrets (all via .env), cap_drop ALL with minimal cap_add, no-new-privileges
- [x] Health check: Effective TCP-based SMTP check, not dependent on Postfix internals
- [x] .env.sample: Complete with all variables documented
- [x] Resource limits: 0.5 CPU, 128M memory -- reasonable for a lightweight relay
