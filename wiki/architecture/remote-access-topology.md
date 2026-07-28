---
title: "Remote access topology"
slug: remote-access-topology
category: architecture
last_reviewed: 2026-07-28
owner: tomamourette
related_pages: [tailscale-policy, remote-access-recovery, create-project-container]
related_frs: []
related_adrs: [ADR-001]
status: stable
supersedes: []
superseded_by: null
tags: [tailscale, cloudflare, vscode-tunnel, proxmox, remote-access, networking]
---

# Remote access topology

## Summary

Four overlapping mechanisms provide off-LAN or emergency access to the
homelab estate, each covering a different need: **Cloudflare Tunnel**
(public web apps), the **Tailscale subnet router** (operator's own LAN
access from anywhere), **VS Code tunnels** (browser-only dev access to
two specific containers), and the **Proxmox console / `pct enter`**
(break-glass, always works). No single page previously described them
together, which made it easy to reach for the wrong one. This page also
records a real concentration risk: both keyless-reachable containers sit
on the same physical node.

## Context

Each mechanism was built for a distinct need at a different time and
none of them supersedes the others:

- The web-app stack (Cloudflare Tunnel + Traefik + Authelia) predates
  the 2026-07-28 keyless remote-access work and was deliberately left
  alone by it — it solves "a third party, or a browser with no
  Tailscale, needs to reach a specific public service," which Tailscale
  SSH does not address.
- The Tailscale subnet router solves "the operator's own devices need
  the whole LAN, not just one container."
- VS Code tunnels solve "browser-only access, no desktop VS Code, to a
  specific dev container" — see [Tailscale-only access policy](tailscale-policy)
  and [Remote access recovery](remote-access-recovery) for why this
  exists alongside Tailscale SSH rather than instead of it.
- The Proxmox console is the fallback of last resort, independent of
  every network-layer mechanism above it.

## Procedure / Decision

### The four mechanisms

| # | Mechanism | Covers | Where it runs | Auth |
|---|---|---|---|---|
| a | Cloudflare Tunnel + Traefik + Authelia | ~19 public services on `*.bi-services.be` | `ct-docker-01` (CT 101, pve1) | Authelia (+ per-service auth where configured) |
| b | Tailscale subnet router (`homelab-gateway-1`) | Operator's own devices reaching the full `192.168.50.0/24` LAN from anywhere | Docker container inside CT 101 (pve1), userspace-networking mode, advertises `192.168.50.0/24` | Tailscale ACL (tailnet membership) |
| c | VS Code tunnels | Browser-only (vscode.dev) dev access to `ct-dev-homelab` and `ct-sparkle-cps` specifically | `remote-access` role, `/opt/remote-access/vscode-cli/` on each container | Microsoft account sign-in |
| d | Proxmox console / `pct enter` | Break-glass shell to any container, any time | Any PVE host (pve1/pve2/pve3) | Proxmox host root (physical/console access); `pct enter` itself needs no password |

Tailscale SSH (keyless operator shell access to `ct-dev-homelab` and
`ct-sparkle-cps` specifically) is documented as part of mechanism (b)'s
tailnet — see [Tailscale-only access policy](tailscale-policy) — rather
than as a separate row, since it rides the same tailnet membership and
ACL.

### Which to use when

| Need | Use |
|---|---|
| A third party (not the operator) needs to reach a specific service | (a) Cloudflare Tunnel |
| Operator's phone or PC needs any LAN service (Grafana, Pi-hole, Proxmox UI, `bi-services.be` hostnames) from off-LAN | (b) Tailscale subnet router, or Tailscale SSH directly to a keyless-onboarded container |
| Operator needs a shell on `ct-dev-homelab` or `ct-sparkle-cps` | Tailscale SSH (primary) → VS Code tunnel browser terminal (fallback) → SSH key (fallback) |
| Operator needs a shell on any other container, off-LAN, no other mechanism onboarded | Not currently possible without VPN into the LAN via (b) first, then a fallback SSH key or `pct enter` from console access |
| Operator needs a shell and everything above is broken | (d) `pct enter <vmid>` from a PVE host — see [Remote access recovery](remote-access-recovery#break-glass-path) |
| Browser only, no desktop VS Code, dev work on `ct-dev-homelab`/`ct-sparkle-cps` | (c) VS Code tunnel at `https://vscode.dev/tunnel/<name>` |

### Concentration risk

**Both keyless-reachable containers — `ct-dev-homelab` and
`ct-sparkle-cps` — sit on `pve3`.** A `pve3` outage removes Tailscale
SSH access to both simultaneously, along with both VS Code tunnels
(their credential directories are on the same node). Mechanism (b), the
subnet router, is unaffected (it runs in CT 101 on `pve1`), so the
operator's own tailnet-based LAN access survives a `pve3` outage — but
recovering a *shell inside* either affected container during that
outage falls back to (d), the Proxmox console, on `pve3` itself once it
recovers, or a cold rebuild on a different node.

This is a known, accepted gap as of 2026-07-28 (see the handoff's "Open
items" — a second subnet router on a different node was suggested but
not built). It is not unique to `pve3`: mechanism (a) and (b) both
depend on a single container, `ct-docker-01` on `pve1` — if `pve1` goes
down, all off-LAN access (public and tailnet-LAN) is lost until someone
is physically on the LAN. The estate currently has **two** single points
of node failure, on two different nodes, for two different halves of
remote access.

## Cross-references

- [Tailscale-only access policy](tailscale-policy) — SSH ACL, tailnet
  name, out-of-repo ACL configuration
- [Remote access recovery](remote-access-recovery) — new-PC setup,
  break-glass, health check, container onboarding
- [Create a new project container](create-project-container) — step 8,
  operator access verification for new containers
- [`homelab-apps/stacks/networking-tailscale/docker-compose.yml`](git:homelab-apps/stacks/networking-tailscale/docker-compose.yml)
  — subnet router deployment
- [`homelab-infra/ansible/roles/remote-access/`](git:homelab-infra/ansible/roles/remote-access/)
  — Tailscale SSH + VS Code tunnel role (commit `54d7f3a`)
- `REMOTE-ACCESS-HANDOFF.md` (workspace root) — "Consider" section,
  source for the concentration-risk framing
- `~/.claude/.../memory/project_pve_node_cooling.md` — pve3 is the
  active-cooled node, relevant context for why dev/AI containers default
  there
