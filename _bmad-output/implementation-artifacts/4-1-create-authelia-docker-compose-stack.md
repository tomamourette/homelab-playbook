# Story 4.1: Create Authelia Docker Compose Stack

**Epic:** 4 - SSO Gateway
**Status:** ready-for-dev
**Implements:** FR19, FR20, FR21, FR23
**Target repo:** homelab-apps

---

## User Story

**As a** homelab operator,
**I want** Authelia deployed as a Docker container with YAML-based configuration,
**So that** I have a lightweight SSO provider running on ct-docker-01.

---

## Acceptance Criteria

### AC1: Authelia portal accessible
**Given** the authelia stack is deployed on ct-docker-01
**When** the operator accesses `auth.bi-services.be`
**Then** the Authelia login portal is displayed

### AC2: Configurable session and 2FA
**Given** the Authelia configuration file is set up
**When** inspected
**Then** session duration is configurable (default 7 days)
**And** TOTP 2FA is available as an optional feature the operator can enable
**And** session storage is file-based in `/opt/appdata/authelia/`
**And** cookies use HTTPS-only with secure and httpOnly flags (NFR-SEC-1)
**And** the configuration sample (`configuration.yml.sample`) is committed; real config with secrets is gitignored

### AC3: Architecture compliance
**Given** the docker-compose.yml follows conventions
**When** inspected
**Then** it uses a pinned semver image tag (e.g., `authelia/authelia:4.38.0`)
**And** sets resource limits, health check, `restart: unless-stopped`, `no-new-privileges:true`, `cap_drop: ALL`
**And** Authelia joins the `proxy` network for Traefik routing
**And** includes json-file logging driver with rotation

---

## Tasks

- [x] Create `stacks/authelia/docker-compose.yml`
  - [x] Pinned image version tag: `authelia/authelia:4.38.18`
  - [x] container_name: authelia
  - [x] restart: unless-stopped
  - [x] Environment variables from .env (JWT_SECRET, SESSION_SECRET, SMTP settings)
  - [x] Join proxy network (Traefik routes to authelia:9091)
  - [x] Traefik labels for `auth.bi-services.be` HTTPS routing
  - [x] Health check using Authelia native health endpoint
  - [x] Resource limits (0.5 CPU, 256M memory)
  - [x] security_opt: no-new-privileges:true
  - [x] cap_drop: ALL
  - [x] TZ environment variable
  - [x] Logging driver configuration (json-file with rotation)
  - [x] Volume mounts for config and data at `/opt/appdata/authelia/`
- [x] Create `stacks/authelia/config/configuration.yml.sample`
  - [x] Server listening on 0.0.0.0:9091
  - [x] Log level: info
  - [x] TOTP issuer set to homelab domain
  - [x] Session domain with configurable 7-day default expiration
  - [x] Session cookies with HTTPS-only, secure, httpOnly flags
  - [x] File-based session provider
  - [x] File-based user database reference
  - [x] SMTP notifier for password reset emails
  - [x] Access control: default deny, single policy allowing the operator
  - [x] Storage: local SQLite at /config/db.sqlite3
- [x] Create `stacks/authelia/.env.sample`
  - [x] AUTHELIA_JWT_SECRET placeholder
  - [x] AUTHELIA_SESSION_SECRET placeholder
  - [x] AUTHELIA_STORAGE_ENCRYPTION_KEY placeholder
  - [x] SMTP settings for notifier (host, port, sender)
  - [x] TZ variable
  - [x] AUTHELIA_HOST variable for Traefik
  - [x] DOMAIN variable for session cookie domain
- [x] Create `stacks/authelia/.gitignore`
  - [x] .env
  - [x] configuration.yml (real config with secrets)
  - [x] users_database.yml (password hashes)
  - [x] db.sqlite3 (session/storage state)

---

## Architecture References

- **Auth decisions:** File-based sessions, forward-auth, TOTP optional, 7-day session default
- **Conventions:** Pinned semver, health check, resource limits, cap_drop ALL, no-new-privileges, proxy network
- **Volume path:** `/opt/appdata/authelia/` for config, session data, SQLite DB
- **Integration:** Traefik forward-auth middleware (Story 4.2 scope, not this story)
- **SMTP:** Uses `smtp-relay:25` on Docker network for password reset notifications

---

## Dependencies

- **Story 1.1/1.2:** SMTP relay must be deployed (for password reset emails via notifier)

---

## Out of Scope

- Traefik forward-auth middleware integration (Story 4.2)
- Rolling out middleware labels to existing services (Story 4.3)
- End-to-end SSO validation (Story 4.4)
