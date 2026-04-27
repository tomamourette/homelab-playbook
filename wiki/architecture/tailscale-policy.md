---
title: "Tailscale-only access policy for phone-facing services"
slug: tailscale-policy
category: architecture
last_reviewed: 2026-04-27
owner: tomamourette
related_pages: []
related_frs: []
related_adrs: []
status: draft
supersedes: []
superseded_by: null
tags: [tailscale, networking, security]
---

# Tailscale-only access policy for phone-facing services

## Summary

Phone-facing homelab services (push notifications, dashboards, anything the
operator's Android device needs to reach off-LAN) default to **Tailscale-only
access**. Do not reflexively reach for Cloudflare-proxy public exposure; the
tailnet already gives the phone a stable encrypted path on home wifi *and*
mobile data. Public DNS / port-forward stays disabled unless Tailscale is
genuinely insufficient.

## Context

Two facts make Tailscale the natural default rather than a fallback:

1. **Internal DNS is RFC1918.** `ntfy.bi-services.be` (and other
   `*.bi-services.be` LAN-only names) resolves only on home wifi via
   Pi-hole local-override → `192.168.50.194`. Public DNS has no A-record,
   and even if it did, the target is not internet-routable.
2. **The operator's Android phone is joined to the same tailnet as
   `ct-docker-01`.** It reaches services via the Tailscale MagicDNS hostname
   or the `100.x.y.z` IP, not via public DNS.

Validated 2026-04-24 with end-to-end push delivery (Story 7.11 chain:
Alertmanager → ntfy → operator's phone) on both home wifi and mobile data.

## Procedure / Decision

### Default rule

For any **new phone-facing service**, choose Tailscale-only access. The
candidate must justify why Tailscale is insufficient before public exposure
is considered.

| Need | Default path | Public-exposure trigger |
|---|---|---|
| Operator phone reaches a homelab service off-LAN | Tailscale | None — Tailscale covers it |
| Service must be reachable by a third party | Cloudflare proxy + auth | Required (operator can't share tailnet) |
| Service must be reachable from a non-Tailscale device the operator owns | Add device to tailnet first | Only if device cannot run Tailscale |

### On-LAN access without Tailscale

When the operator is on home wifi and not running Tailscale, Pi-hole
local-override + Traefik already provide hostname-based access to internal
services. No additional configuration required. The Tailscale-only rule
applies to **off-LAN** access.

### Concrete deployment pattern

The reference implementation lives in
[`homelab-apps/stacks/networking-tailscale/docker-compose.yml`](git:homelab-apps/stacks/networking-tailscale/docker-compose.yml):

- Tailscale container runs on `ct-docker-01` in `network_mode: host`, with
  `--advertise-routes=192.168.50.0/24` and `--accept-routes`.
- LiteLLM gateway on `ct-ai-01` widened to `0.0.0.0:4000` specifically to
  allow Tailscale clients (Continue.dev, Cursor, phone apps) to reach the
  gateway, with bearer-auth as the only security boundary
  (see [`homelab-infra/ansible/roles/litellm-gateway/defaults/main.yml`](git:homelab-infra/ansible/roles/litellm-gateway/defaults/main.yml)
  comments on `litellm_listen_host`).
- No port-forward at the home router. No Cloudflare tunnel for these
  services. Bearer keys + Tailscale ACLs are the access control.

### Troubleshooting checklist

When the phone reports "hostname won't resolve" for a tailnet service:

1. Tailscale toggle on in the phone's Tailscale app.
2. Android Private DNS = Off or Automatic (custom DoH bypasses MagicDNS).
3. Confirm the service is actually bound to a tailnet-reachable interface
   (e.g. `0.0.0.0:port`, not `127.0.0.1:port`).
4. If on home wifi only and Tailscale is off, fall back to the Pi-hole +
   Traefik LAN path — confirm `bi-services.be` resolution.
5. Auth-key expiry: Tailscale auth keys expire every 90 days; the
   container can report healthy while logged out. Regenerate the key and
   recreate the compose stack if the node is silently disconnected.

### Anti-patterns to avoid

- Reaching for a public Cloudflare proxy "just in case" the phone might be
  off-LAN — Tailscale is already there.
- Punching a hole in the home router (UPnP / port-forward) for a phone-only
  service. The tailnet supersedes this.
- Binding a service to `127.0.0.1` on the host and then needing a public
  reverse proxy to expose it. Bind to the Tailscale interface (or
  `0.0.0.0` with bearer auth) and let the tailnet ACL be the boundary.

## Cross-references

- `~/.claude/.../memory/project_phone_notifications_tailscale.md` —
  origin-of-rule (Tom on Android, validated 2026-04-24)
- `~/.claude/.../memory/feedback_tailscale_auth_recovery.md` —
  90-day key-rotation gotcha
- [`homelab-apps/stacks/networking-tailscale/docker-compose.yml`](git:homelab-apps/stacks/networking-tailscale/docker-compose.yml)
- [`homelab-infra/ansible/roles/litellm-gateway/defaults/main.yml`](git:homelab-infra/ansible/roles/litellm-gateway/defaults/main.yml)
  (see `litellm_listen_host` comment on Tailscale-only public access)
- Story 7.11 — push-notification chain that proved this path
