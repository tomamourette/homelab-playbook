# Story 4.3: Roll Out Authelia Middleware Labels to All Existing Services

**Epic:** 4 - SSO Gateway
**Status:** done
**Implements:** FR20, FR22
**Target repo:** homelab-apps

---

## User Story

**As a** homelab operator,
**I want** all existing Traefik-routed services protected by the Authelia forward-auth middleware,
**So that** unauthenticated requests to any service are redirected to the SSO login portal.

---

## Acceptance Criteria

### AC1: All existing Traefik-routed services protected
**Given** the Authelia middleware is defined via file provider (Story 4.2)
**When** all existing docker-compose.yml files with Traefik router labels are inspected
**Then** each router includes `authelia@file` in its middlewares label

### AC2: Authelia portal excluded
**Given** the Authelia stack's own router
**When** inspected
**Then** it does NOT have the `authelia@file` middleware (would cause infinite redirect loop)

### AC3: Non-Traefik services unaffected
**Given** services without Traefik router labels (threadfin, tuliprox, tailscale, portainer-agent, node-exporter, cadvisor)
**When** inspected
**Then** they are unchanged

### AC4: Existing middlewares preserved
**Given** services with existing middleware labels (traefik-auth, security-headers@file, obsidian-cors)
**When** `authelia@file` is added
**Then** existing middlewares are preserved in the comma-separated list

---

## Tasks

- [x] Audit all 20 stacks in `homelab-apps/stacks/` for Traefik router labels
- [x] Add `authelia@file` middleware to all Traefik-routed services (21 routers across 14 stacks)
- [x] Preserve existing middleware chains (traefik dashboard, obsidian CORS)
- [x] Verify authelia stack excluded (infinite redirect loop prevention)
- [x] Verify sprint-created stacks without Traefik labels skipped (smtp-relay, update-checks)

---

## Files Modified (14 docker-compose.yml files, 21 routers)

| Stack | File | Router(s) | Notes |
|-------|------|-----------|-------|
| automations-n8n | `stacks/automations-n8n/docker-compose.yml` | n8n-secure | Added `authelia@file` |
| dns-pihole | `stacks/dns-pihole/docker-compose.yml` | pihole-secure | Added `authelia@file` |
| infra-core | `stacks/infra-core/docker-compose.yml` | traefik-secure | Prepended `authelia@file` to existing `traefik-auth,security-headers@file` |
| infra-core | `stacks/infra-core/docker-compose.yml` | portainer-secure | Added `authelia@file` |
| infra-homepage | `stacks/infra-homepage/docker-compose.yml` | homepage-secure | Added `authelia@file` |
| media-downloads | `stacks/media-downloads/docker-compose.yml` | qbittorrent-secure | Added `authelia@file` |
| media-downloads | `stacks/media-downloads/docker-compose.yml` | sabnzbd-secure | Added `authelia@file` |
| media-indexers | `stacks/media-indexers/docker-compose.yml` | sonarr-secure | Added `authelia@file` |
| media-indexers | `stacks/media-indexers/docker-compose.yml` | radarr-secure | Added `authelia@file` |
| media-indexers | `stacks/media-indexers/docker-compose.yml` | prowlarr-secure | Added `authelia@file` |
| media-indexers | `stacks/media-indexers/docker-compose.yml` | bazarr-secure | Added `authelia@file` |
| media-jellyfin | `stacks/media-jellyfin/docker-compose.yml` | jellyfin-secure | Added `authelia@file` |
| media-jellyseerr | `stacks/media-jellyseerr/docker-compose.yml` | jellyseerr-secure | Added `authelia@file` |
| media-overseerr | `stacks/media-overseerr/docker-compose.yml` | overseerr-secure | Added `authelia@file` |
| media-plex | `stacks/media-plex/docker-compose.yml` | plex-secure | Added `authelia@file` |
| media-plex | `stacks/media-plex/docker-compose.yml` | tautulli-secure | Added `authelia@file` |
| observability | `stacks/observability/docker-compose.yml` | prometheus-secure | Added `authelia@file` |
| observability | `stacks/observability/docker-compose.yml` | grafana-secure | Added `authelia@file` |
| organizr | `stacks/organizr/docker-compose.yml` | organizr-secure | Added `authelia@file` |
| productivity-obsidian | `stacks/productivity-obsidian/docker-compose.yml` | obsidian-secure | Prepended `authelia@file` to existing `obsidian-cors` |

## Stacks NOT Modified (6 stacks, with reasons)

| Stack | Reason |
|-------|--------|
| authelia | Excluded: would cause infinite redirect loop (R-402) |
| smtp-relay | No Traefik router labels; internal SMTP service |
| update-checks | No Traefik router labels; background scheduler |
| media-iptv (threadfin) | No Traefik router labels; media network only |
| media-tuliprox | No Traefik router labels; media network only |
| networking-tailscale | No Traefik router labels; host networking |
| portainer-agent | No Traefik router labels; agent network only |

---

## Architecture References

- **Middleware reference:** `authelia@file` (file provider, per D-406/R-405)
- **Middleware definition:** `stacks/infra-core/config/dynamic/authelia-middleware.yml` (Story 4.2)
- **Auth endpoint:** `http://authelia:9091/api/authz/forward-auth`
- **Middleware order:** `authelia@file` placed first in chain so auth check runs before other middleware

---

## Dependencies

- **Story 4.1:** Authelia container deployed
- **Story 4.2:** Authelia forward-auth middleware defined in Traefik file provider

---

## Out of Scope

- End-to-end SSO validation (Story 4.4)
- Per-service access control policies (configurable in Authelia's access_control rules)
- API endpoint bypass rules (future enhancement if needed)
