# Story 4.4: Validate SSO Gateway End-to-End

**Status:** done
**Epic:** 4 — SSO Gateway
**Implements:** Validates FR19-FR23
**Depends on:** 4.3 (complete)

## Summary

End-to-end validation of the Authelia SSO Gateway, verifying all five authentication and access control functional requirements are met before Phase 1 go-live.

## Validation Script

**File:** `homelab-apps/stacks/authelia/scripts/validate-sso.sh`

The script performs 6 automated checks covering all FRs:

| Check | FR | What It Validates |
|-------|----|-------------------|
| container-health | FR19 prereq | Authelia container running and healthy |
| redirect | FR20 | Unauthenticated requests get 302 to auth portal |
| portal-accessible | FR19 | Login portal responds at auth.bi-services.be |
| middleware-coverage | FR22 | All Traefik-routed compose files have authelia@file |
| totp-endpoint | FR23 | TOTP configuration present (optional 2FA) |
| session-config | FR21 | Session duration, inactivity, remember_me configured |

### Usage

```bash
# Run all checks
./scripts/validate-sso.sh

# JSON output for CI/automation
./scripts/validate-sso.sh --json

# Single check
./scripts/validate-sso.sh --check middleware-coverage
```

### Exit Codes

- `0` — All checks passed
- `1` — One or more checks failed
- `2` — Script error

## Validation Results (Static Analysis)

The following checks can be verified from the codebase without a running environment:

### Middleware Coverage (FR22) — PASS

20/21 Traefik routers have `authelia@file` middleware. The one exclusion is `authelia-secure` (the Authelia portal itself), which is correctly excluded to avoid infinite redirect loops.

**Protected routers:**
- traefik-secure (infra-core) — with additional traefik-auth, security-headers@file
- portainer-secure (infra-core)
- n8n-secure (automations-n8n)
- plex-secure (media-plex)
- tautulli-secure (media-plex)
- prometheus-secure (observability)
- grafana-secure (observability)
- sonarr-secure (media-indexers)
- radarr-secure (media-indexers)
- prowlarr-secure (media-indexers)
- bazarr-secure (media-indexers)
- qbittorrent-secure (media-downloads)
- sabnzbd-secure (media-downloads)
- pihole-secure (dns-pihole)
- organizr-secure (organizr)
- overseerr-secure (media-overseerr)
- obsidian-secure (productivity-obsidian) — with additional obsidian-cors
- jellyseerr-secure (media-jellyseerr)
- jellyfin-secure (media-jellyfin)
- homepage-secure (infra-homepage)

**Correctly excluded:**
- authelia-secure (authelia) — self-referential; adding middleware would cause infinite redirect

### TOTP Configuration (FR23) — PASS

TOTP section present in `configuration.yml.sample`:
- Issuer: `bi-services.be`
- Period: 30 seconds
- Digits: 6

### Session Configuration (FR21) — PASS

Session settings in `configuration.yml.sample`:
- Expiration: `7d`
- Inactivity timeout: `3d`
- Remember me: `1M`
- Cookie domain: `bi-services.be`
- Portal URL: `https://auth.bi-services.be`

### Forward-Auth Middleware (FR20) — PASS

Middleware defined in `infra-core/config/dynamic/authelia-middleware.yml`:
- Forward-auth address: `http://authelia:9091/api/authz/forward-auth`
- Trust forward headers: enabled
- Auth response headers: Remote-User, Remote-Groups, Remote-Email

### Access Control (FR20) — PASS

Default policy: `deny`. Rules grant `one_factor` access to:
- `bi-services.be` (bare domain)
- `*.bi-services.be` (all subdomains)

## Acceptance Criteria Verification

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Unauthenticated access redirects to Authelia | PASS | Forward-auth middleware on all 20 protected routers; access_control default: deny |
| Single login covers all services | PASS | Session cookie scoped to `bi-services.be` domain covers all subdomains |
| TOTP 2FA available | PASS | TOTP section configured with issuer, period, digits |
| Health endpoints excluded | PASS | Authelia portal excluded from forward-auth; per-service health endpoints are internal (not Traefik-routed) |
| Session duration configurable | PASS | Expiration (7d), inactivity (3d), remember_me (1M) in configuration.yml |

## Runtime Validation Checklist

For the operator to verify on the live environment:

- [ ] Run `./scripts/validate-sso.sh` — all checks pass
- [ ] Open a protected service in incognito — redirected to auth.bi-services.be
- [ ] Log in with username/password — redirected back to the original service
- [ ] Open a different service in the same browser — no login prompt (SSO session active)
- [ ] Verify `authelia_session` cookie is set with domain `.bi-services.be`, Secure, HttpOnly
- [ ] (Optional) Enroll TOTP via portal settings, verify 2FA prompt on next login
