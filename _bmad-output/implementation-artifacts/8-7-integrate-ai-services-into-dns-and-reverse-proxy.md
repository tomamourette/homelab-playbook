# Story 8.7: Integrate AI Services into DNS and Reverse Proxy

Status: done

## Story

As a homelab operator,
I want Open WebUI and Ollama accessible via proper DNS names with HTTPS and SSO protection,
So that the AI services are consistent with the rest of my homelab infrastructure.

## Acceptance Criteria

1. **Given** Open WebUI is running on ct-ai-01 at 192.168.50.160:3000 (Story 8.4)
   **When** I add DNS entries to the Pi-hole custom list template
   **Then** `chat.bi-services.be` and `ollama.bi-services.be` resolve to 192.168.50.160

2. **Given** DNS entries exist
   **When** I add a Traefik cross-host routing config for AI services
   **Then** `ai-services.yml` exists in `stacks/infra-core/config/` with service+router definitions for chat and ollama

3. **Given** Traefik routing is configured
   **When** I access `https://chat.bi-services.be`
   **Then** Traefik routes to Open WebUI on 192.168.50.160:3000 with TLS via Let's Encrypt

4. **Given** Authelia middleware is available
   **When** I access `https://chat.bi-services.be`
   **Then** the route is protected by Authelia SSO (`authelia@file` middleware)

5. **Given** Ollama API needs programmatic access
   **When** I access `https://ollama.bi-services.be`
   **Then** the route reaches Ollama API on 192.168.50.160:11434 **without** Authelia (API route, no SSO)

## Edge Cases & Error Scenarios

1. **Side effects:**
   - `pihole-custom.list.j2` modified (2 new DNS entries added)
   - `ai-services.yml` created in Traefik dynamic config directory
   - Pi-hole needs restart/reload to pick up DNS changes
   - Traefik hot-reloads dynamic config automatically (no restart needed)

2. **Dependency failure:**
   - If Let's Encrypt cert fails: DNS must resolve publicly via Cloudflare (not just Pi-hole internal)
   - If Authelia blocks Open WebUI websockets: may need to add headers or bypass path
   - If Ollama API needs auth later: add API key middleware instead of Authelia

3. **Assumptions:**
   - Traefik runs on ct-docker-01 (192.168.50.194) and can reach ct-ai-01 (192.168.50.160)
   - Cloudflare DNS has a wildcard or specific A record for *.bi-services.be
   - Authelia middleware is defined in `stacks/infra-core/config/dynamic/authelia-middleware.yml`
   - Traefik file provider watches `stacks/infra-core/config/` directory

## Eval Assertions

| # | Assertion | Command/Check | Pass Criteria |
|---|-----------|---------------|---------------|
| AC-1 | DNS entries in template | `grep -q 'chat.bi-services.be' homelab-infra/ansible/templates/pihole-custom.list.j2` | Exits with code 0 |
| AC-2 | Traefik config exists | `test -f homelab-apps/stacks/infra-core/config/ai-services.yml` | Exits with code 0 |
| AC-3 | HTTPS route works | `curl -sk -o /dev/null -w '%{http_code}' https://chat.bi-services.be` | Returns 200 or 302 (Authelia redirect) |
| AC-4 | Authelia protects chat | `curl -sk -o /dev/null -w '%{http_code}' https://chat.bi-services.be` | Returns 302 (redirect to Authelia) when not authenticated |
| AC-5 | Ollama API no SSO | `curl -sk https://ollama.bi-services.be/api/tags` | Returns JSON (no auth redirect) |

## Tasks / Subtasks

- [x] Task 1: Add DNS entries to Pi-hole template (AC: 1)
  - [x] Edited `homelab-infra/ansible/templates/pihole-custom.list.j2` — added chat + ollama entries pointing to docker_ip (Traefik)
  - [x] Added entries directly to Pi-hole on ct-docker-01 and restarted DNS
  - [x] DNS resolves: `chat.bi-services.be` → 192.168.50.194, `ollama.bi-services.be` → 192.168.50.194
  - [x] Cloudflare DNS not needed — Let's Encrypt uses DNS challenge via Cloudflare API (already configured)
- [x] Task 2: Create Traefik cross-host routing config (AC: 2, 3, 4, 5)
  - [x] Created `homelab-apps/stacks/infra-core/config/ai-services.yml` following media-indexers.yml pattern
  - [x] Services: chat → 192.168.50.160:3000, ollama → 192.168.50.160:11434
  - [x] chat-secure: Authelia middleware (`authelia@file`), ollama-secure: no middleware
  - [x] Updated `docker-compose.yml` to add bind mount for ai-services.yml
  - [x] Deployed to ct-docker-01, Traefik container recreated
- [x] Task 3: Deploy DNS changes (AC: 1)
  - [x] Pi-hole custom.list updated on ct-docker-01 directly
  - [x] Pi-hole container restarted to pick up changes
- [x] Task 4: Verify routing (AC: 3, 4, 5)
  - [x] `https://chat.bi-services.be` → 302 redirect to Authelia (SSO working)
  - [x] `https://ollama.bi-services.be/api/tags` → JSON response with models (no auth, direct API)

## Dev Notes

### Cross-Host Routing Pattern

Following `media-indexers.yml` pattern exactly. Traefik on ct-docker-01 proxies requests to ct-ai-01 via internal network:

```yaml
http:
  services:
    chat:
      loadBalancer:
        servers:
          - url: "http://192.168.50.160:3000"
    ollama:
      loadBalancer:
        servers:
          - url: "http://192.168.50.160:11434"
  routers:
    chat-secure:
      entryPoints: ["websecure"]
      rule: "Host(`chat.bi-services.be`)"
      service: "chat"
      middlewares: ["authelia@file"]
      tls:
        certResolver: letsencrypt
    ollama-secure:
      entryPoints: ["websecure"]
      rule: "Host(`ollama.bi-services.be`)"
      service: "ollama"
      tls:
        certResolver: letsencrypt
```

### Authelia Integration

- Middleware defined in `stacks/infra-core/config/dynamic/authelia-middleware.yml`
- Chat route uses `authelia@file` middleware (SSO protection)
- Ollama API route has NO middleware (programmatic access)

### DNS Flow

- Pi-hole (`pihole-custom.list.j2`) resolves `chat.bi-services.be` → ct-docker-01 (192.168.50.194, where Traefik runs)
- Traefik then proxies to ct-ai-01 (192.168.50.160)
- Cloudflare needs matching A records for Let's Encrypt cert validation

### Files to Modify

- `homelab-infra/ansible/templates/pihole-custom.list.j2` — add AI service DNS entries
- `homelab-apps/stacks/infra-core/config/ai-services.yml` — new file, Traefik dynamic config

### References

- [Source: homelab-apps/stacks/infra-core/config/media-indexers.yml — cross-host pattern]
- [Source: homelab-apps/stacks/infra-core/config/dynamic/authelia-middleware.yml — SSO middleware]
- [Source: docs/integration-architecture.md#Cross-Host Routing]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6[1m])

### Debug Log References

- Traefik file provider `directory: /etc/traefik` does NOT recurse into subdirectories — `dynamic/` files weren't loaded
- Fixed by adding individual bind mount in docker-compose.yml (matches existing pattern for media-indexers.yml)
- Let's Encrypt cert uses Cloudflare DNS challenge — no public A records needed, but cert issuance takes a few minutes
- Pi-hole custom.list is bind-mounted from `/opt/homelab-apps/stacks/dns-pihole/config/custom.list`, not `/etc/pihole/`
- Pi-hole restartdns requires container restart (kill permission issue inside container)

### Deployment Verification

Result: 5/5 assertions passed.

| # | Assertion | Result |
|---|-----------|--------|
| AC-1 | DNS entries in template | PASS — pihole-custom.list.j2 updated |
| AC-2 | Traefik config exists | PASS — ai-services.yml created + mounted |
| AC-3 | HTTPS route works | PASS — HTTP 302 (Authelia redirect) |
| AC-4 | Authelia protects chat | PASS — redirects to auth.bi-services.be |
| AC-5 | Ollama API no SSO | PASS — returns JSON directly |

### Completion Notes List

- `chat.bi-services.be` → Authelia SSO → Open WebUI
- `ollama.bi-services.be` → Ollama API (no auth, programmatic access)
- Traefik cross-host routing from ct-docker-01 to ct-ai-01 (192.168.50.160)
- Let's Encrypt cert pending DNS challenge completion (using default cert temporarily)
- Pi-hole template + docker-compose.yml both updated in repos

### Change Log

- 2026-04-15: Story implemented — DNS + Traefik + Authelia for AI services

### File List

- `homelab-infra/ansible/templates/pihole-custom.list.j2` — added AI service DNS entries
- `homelab-apps/stacks/infra-core/config/ai-services.yml` — new Traefik cross-host config
- `homelab-apps/stacks/infra-core/docker-compose.yml` — added ai-services.yml bind mount
