# Story 4.2: Integrate Authelia Forward-Auth Middleware with Traefik

**Epic:** 4 - SSO Gateway
**Status:** done
**Implements:** FR19, FR20, FR22
**Target repo:** homelab-apps

---

## User Story

**As a** homelab operator,
**I want** Traefik to use Authelia as a forward-auth middleware for all routed services,
**So that** every service is protected by SSO without per-service configuration.

---

## Acceptance Criteria

### AC1: Unauthenticated redirect
**Given** the Authelia forward-auth middleware is defined in infra-core
**When** an unauthenticated user accesses any Traefik-routed service
**Then** the request is intercepted and redirected to the Authelia login portal

### AC2: Single sign-on
**Given** the operator has authenticated via Authelia
**When** they navigate to any other Traefik-routed service
**Then** they pass through without a second login (single session cookie)

### AC3: Auto-protection of new services
**Given** a new service is added to Traefik with the `authelia@file` middleware label
**When** it is accessed
**Then** it is automatically protected by SSO without any Authelia-side configuration

### AC4: Middleware configuration
**Given** the middleware is defined
**When** inspected
**Then** the forward-auth address is `http://authelia:9091/api/authz/forward-auth`
**And** `trustForwardHeader` is true
**And** response headers include `Remote-User`, `Remote-Groups`, `Remote-Email`

---

## Tasks

- [x] Create `stacks/infra-core/config/dynamic/authelia-middleware.yml`
  - [x] Traefik file provider dynamic config format (http.middlewares)
  - [x] Middleware name: `authelia`
  - [x] forwardAuth address: `http://authelia:9091/api/authz/forward-auth`
  - [x] trustForwardHeader: true
  - [x] authResponseHeaders: Remote-User, Remote-Groups, Remote-Email
- [x] Modify `stacks/infra-core/docker-compose.yml`
  - [x] Add volume mount for `./config/dynamic:/etc/traefik/dynamic:ro`
  - [x] Traefik file provider already watches `/etc/traefik` recursively (no static config change needed)

---

## Architecture References

- **Middleware pattern:** Architecture "Traefik Middleware Patterns" section
- **Provider type:** Traefik file provider (not Docker labels) -- middleware defined in `authelia-middleware.yml`
- **Middleware reference:** `authelia@file` (since defined via file provider, not Docker labels)
- **Auth endpoint:** `http://authelia:9091/api/authz/forward-auth` (Authelia v4.38+ authz endpoint)
- **Network:** Authelia on `proxy` network, reachable by Traefik via container name
- **Integration:** Story 4.3 will add `authelia@file` middleware label to all existing service routers

---

## Implementation Notes

### Why file provider instead of Docker labels

The architecture file map explicitly specifies `infra-core/config/dynamic/authelia-middleware.yml` as a NEW file. Using the file provider to define the middleware has advantages:

1. **Decoupled from container lifecycle** -- middleware persists even if Authelia container restarts
2. **Single definition** -- not attached to any specific container's labels
3. **Consistent with existing pattern** -- security-headers middleware already uses file provider

### Middleware reference convention

Since the middleware is defined via file provider, services must reference it as `authelia@file` (not `authelia@docker`). This differs from the architecture's label example which shows `authelia@docker`. Decision D-406 documents this.

### Traefik file provider recursive scan

Traefik v3 file provider with `directory: /etc/traefik` and `watch: true` recursively scans all subdirectories. The new `dynamic/` subdirectory is automatically discovered without changes to `traefik.yml`.

---

## Dependencies

- **Story 4.1:** Authelia container must be deployed and accessible on `proxy` network at `authelia:9091`

---

## Out of Scope

- Rolling out middleware labels to existing services (Story 4.3)
- End-to-end SSO validation (Story 4.4)
- Health check endpoint exclusions (Story 4.3/4.4 scope)
