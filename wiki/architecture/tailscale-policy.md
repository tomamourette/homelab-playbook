---
title: "Tailscale access policy"
slug: tailscale-policy
category: architecture
last_reviewed: 2026-07-28
owner: tomamourette
related_pages: [remote-access-recovery, remote-access-topology, create-project-container]
related_frs: []
related_adrs: [ADR-001]
status: stable
supersedes: []
superseded_by: null
tags: [tailscale, networking, security, ssh, remote-access]
---

# Tailscale access policy

## Summary

The tailnet (`taildf9e93.ts.net`) is the homelab's default off-LAN access
path for **two** distinct needs: phone-facing services (the original scope
of this page) and, as of the 2026-07-28 keyless remote-access design,
**operator shell access via Tailscale SSH** — no SSH keys at all. Do not
reflexively reach for Cloudflare-proxy public exposure or hand-distributed
SSH keys; the tailnet already gives both the phone and the operator's
devices a stable encrypted path on home wifi *and* mobile data / off-LAN.
Public DNS / port-forward and SSH-key distribution both stay
fallback-or-disabled unless Tailscale is genuinely insufficient. See
[Remote access recovery](remote-access-recovery) for the operator runbook
and [Remote access topology](remote-access-topology) for how this fits
alongside Cloudflare Tunnel, VS Code tunnels, and the Proxmox console.

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

A third, later fact widened the scope from phone-only to operator shell
access: the operator's workstation died 2026-07-28 and took the only copy
of the `homelab-infra` SSH private key with it. Every container trusted
that one key and nothing else, so a new PC had no way in — even though the
containers were never truly unreachable (`pct enter` from a PVE host needs
no password). The fix activated **Tailscale SSH**, which authenticates by
tailnet identity instead of a distributed `authorized_keys` entry, as the
primary operator access path. See
[Remote access recovery](remote-access-recovery) for the full runbook and
[ADR-001](../../_bmad-output/planning-artifacts/products/remote-access/adrs/ADR-001-tailscale-primary-keys-fallback.md)
for the decision record.

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

### Tailscale SSH (operator shell access)

Two containers are onboarded to keyless remote access today:
`ct-dev-homelab` (tagged `tag:control`, 100.104.114.63) and
`ct-sparkle-cps` (tagged `tag:container`, 100.127.130.70). `tag:control`
is deliberately the only tag permitted to SSH *to* the others — it is
the Ansible/Terraform control node. Onboarding a new container is an
explicit step, not automatic; see
[Remote access recovery](remote-access-recovery#onboard-a-new-container-to-keyless-remote-access).

Implemented by the `remote-access` Ansible role
(`homelab-infra/ansible/roles/remote-access/`, commit `54d7f3a`) and
applied via `playbooks/remote-access.yml`. SSH keys remain a fallback
path only, distributed by `playbooks/ssh-authorized-keys.yml` — see
[Remote access topology](remote-access-topology) for how this sits
alongside Cloudflare Tunnel, VS Code tunnels, and the Proxmox console.

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

## Out-of-repo configuration

**The tailnet ACL lives only in the Tailscale admin console. It is
UNVERSIONED infrastructure — a change there is invisible to git**, unlike
almost everything else this wiki documents. Treat this section as a
snapshot, not a live source; re-verify against the admin console before
relying on it for an incident.

As recorded 2026-07-28 (verified against the running tailnet at that
time):

```json
"tagOwners": {
  "tag:container": ["autogroup:admin"],
  "tag:control":   ["autogroup:admin"]
},
"ssh": [
  {
    "action": "accept",
    "src":    ["autogroup:member", "tag:control"],
    "dst":    ["tag:container", "tag:control"],
    "users":  ["autogroup:nonroot", "root"]
  }
]
```

`tag:control` appears in **both** `src` and `dst`: as a source so
`ct-dev-homelab` can SSH to the others (it is the only container
permitted to), and as a destination so the operator's own devices
(`autogroup:member`) can still reach it.

### Known discrepancy — not resolved from here

`homelab-infra/ansible/inventories/homelab/group_vars/all/remote-access.yml`
(~line 20, a comment documenting the expected ACL shape) shows:

```json
"ssh": [{ "action": "accept", "src": ["autogroup:member"],
          "dst": ["tag:container"], "users": ["autogroup:nonroot","root"] }]
```

— i.e. `src` limited to `autogroup:member`, with no `tag:control` and no
`tag:control` in `dst`. That disagrees with the ACL block recorded above
from the 2026-07-28 handoff, which includes `tag:control` in both `src`
and `dst` (required for `ct-dev-homelab` to reach the other containers at
all).

**The admin console is authoritative.** Neither in-repo copy — the
comment above, nor this wiki page — could be cross-checked against the
live console from here. Until someone confirms the console's actual
`ssh` rule directly, treat the in-repo comment as possibly stale
documentation rather than as proof of what's enforced. If `ct-dev-homelab`
is observed failing to SSH to `ct-sparkle-cps` over Tailscale, check the
console's `ssh` rule for `tag:control` in `src` first.

## Cross-references

- `~/.claude/.../memory/project_phone_notifications_tailscale.md` —
  origin-of-rule (Tom on Android, validated 2026-04-24)
- `~/.claude/.../memory/feedback_tailscale_auth_recovery.md` —
  90-day key-rotation gotcha
- [`homelab-apps/stacks/networking-tailscale/docker-compose.yml`](git:homelab-apps/stacks/networking-tailscale/docker-compose.yml)
- [`homelab-infra/ansible/roles/litellm-gateway/defaults/main.yml`](git:homelab-infra/ansible/roles/litellm-gateway/defaults/main.yml)
  (see `litellm_listen_host` comment on Tailscale-only public access)
- Story 7.11 — push-notification chain that proved this path
- [Remote access recovery](remote-access-recovery) — new-PC setup,
  break-glass, health check, onboarding a container
- [Remote access topology](remote-access-topology) — all four
  off-LAN/local access mechanisms together
- [`homelab-infra/ansible/roles/remote-access/`](git:homelab-infra/ansible/roles/remote-access/)
  (commit `54d7f3a`) — the Tailscale SSH + VS Code tunnel role
- [`homelab-infra/ansible/inventories/homelab/group_vars/all/remote-access.yml`](git:homelab-infra/ansible/inventories/homelab/group_vars/all/remote-access.yml)
  — SSH-key fallback declaration; see the discrepancy noted above
- `REMOTE-ACCESS-HANDOFF.md` (workspace root) — source handoff for the
  2026-07-28 keyless remote-access work
