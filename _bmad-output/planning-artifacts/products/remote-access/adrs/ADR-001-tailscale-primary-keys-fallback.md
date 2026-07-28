---
adr: 001
title: "Tailscale SSH primary, SSH keys fallback-only"
status: accepted
date: 2026-07-28
authors: tomamourette (via Claude Code session on pve3, continued from ct-dev-homelab)
context_question: null
---

# ADR-001: Tailscale SSH primary, SSH keys fallback-only

## Context

The operator's workstation (`tom-notebook-1`) died and took with it the
only copy of the `homelab-infra` SSH private key. Every container
trusted that one key and nothing else, so a replacement PC had no way
in. The containers were never truly unreachable — `pct enter` from a
PVE host needs no password — but the *credential* was gone, and nothing
in the estate replaced it automatically.

Root cause: one credential, on one device, with no second path. Three
separate keyless mechanisms already existed in the ecosystem
(Tailscale's own SSH feature, Tailscale ACL tagging for unattended
rejoin, and VS Code's tunnel/device-login model) and were all dormant —
none had been wired into the homelab.

The goal became: **a replacement PC must need no files copied.** No SSH
config, no key restore, no repo clone. Whatever replaced the dead
workstation's key needed to survive the *next* dead workstation too.

## Decision

**Tailscale SSH is the primary operator access path. SSH keys become a
fallback only, kept for hosts or moments where Tailscale is
unavailable.**

Concretely:

- Containers that need operator shell access join the tailnet
  (`taildf9e93.ts.net`) with Tailscale SSH enabled (`--ssh`), authenticating
  by tailnet identity rather than an `authorized_keys` entry. Implemented
  by the `remote-access` Ansible role
  (`homelab-infra/ansible/roles/remote-access/`, commit `54d7f3a`).
- Nodes are tagged (`tag:container` / `tag:control`) rather than joined
  as personal devices, so they don't inherit a personal device's key
  expiry — the exact failure mode that started this. `tag:control`
  (currently only `ct-dev-homelab`) is the sole tag permitted to SSH
  *to* the others, expressed as a distinct ACL entry rather than
  granting every container equal reach.
- **VS Code tunnels** cover the one gap Tailscale SSH cannot: browser-only
  access (vscode.dev), needed because the Tailscale VS Code extension
  requires desktop VS Code and vscode.dev cannot do Remote-SSH. The
  tunnel provider is **Microsoft**, not GitHub — deliberately, to keep
  GitHub org/repo OAuth scopes off a credential that sits on a
  container; the GitHub authorisation was revoked.
- **SSH keys are the fallback only**, distributed by
  `playbooks/ssh-authorized-keys.yml`, additive (`exclusive: false`) so
  the playbook can never lock out a key still in use. This path stays
  because Tailscale itself can be down, or a host may not (yet) be
  onboarded to the tailnet.
- **`pct enter` from any PVE host remains the break-glass path**,
  independent of every network-layer mechanism above — it needs no
  password and was true before this work and remains true after it.

What a new PC needs: install Tailscale, sign in; install VS Code, sign
in with Microsoft. No files copied, no keys, no repo clone.

## Alternatives Considered

1. **Recover / regenerate the lost SSH key and keep key-based SSH as
   primary.** Rejected — this repairs the immediate symptom but not the
   root cause. The next dead workstation reproduces the exact same
   outage. A regenerated key is still one credential on one device.

2. **Centralize SSH keys in a password manager / vault, distributed on
   demand.** Considered as a partial mitigation (and left as an open
   item — `.vault_pass` currently exists only on `ct-dev-homelab`). Not
   sufficient alone: it still requires *some* working access path to
   fetch the key from the vault onto a fresh device, and still leaves
   `authorized_keys` as the thing being managed rather than removed as
   a dependency.

3. **VPN-only access (no SSH exposed at all).** Rejected as
   disproportionate: the estate already has functioning per-container
   SSH for Ansible, and Tailscale SSH achieves the "no keys" goal
   without removing the SSH protocol operators and tooling already
   understand.

4. **GitHub OAuth for VS Code tunnels (instead of Microsoft).**
   Rejected — GitHub org/repo scopes are broader than a container-side
   dev-tunnel credential needs, and the workstation was already signed
   into Microsoft. Deliberately revoked the GitHub authorisation to
   remove it as a live credential.

## Consequences

**Positive.**
- A replacement workstation is reachable with zero file transfer —
  verified by the 2026-07-28 disaster-recovery test: both containers
  were logged out of the tailnet, then recovered by the `remote-access`
  role with no human input, `rescued=0`, correct tag re-applied on both.
- Tagged nodes don't silently drop off the tailnet on a personal
  device's 90-day key-expiry clock — see also
  [Tailscale-only access policy](../../../../wiki/architecture/tailscale-policy.md).
- SSH-key fallback is still additive and still works, so this is a
  strict widening of access paths, not a narrowing.

**Negative.**
- Onboarding a new container to keyless access is now a distinct,
  explicit multi-step operation (inventory group, `/dev/net/tun` grant,
  ACL tag, scoped auth key) rather than automatic — documented in
  [Remote access recovery](../../../../wiki/runbooks/remote-access-recovery.md).
  A project container created via the
  [create-project-container](../../../../wiki/runbooks/create-project-container.md)
  runbook is **not** onboarded by default.
- New concentration risk: both keyless-reachable containers
  (`ct-dev-homelab`, `ct-sparkle-cps`) currently sit on `pve3` — a
  `pve3` outage removes both Tailscale SSH targets and both VS Code
  tunnels at once. Documented, not yet mitigated — see
  [Remote access topology](../../../../wiki/architecture/remote-access-topology.md#concentration-risk).
- The tailnet ACL (tag ownership + the `ssh` rule) lives only in the
  Tailscale admin console — genuinely unversioned infrastructure that
  git cannot show a diff for. A found discrepancy between the
  in-repo comment in `group_vars/all/remote-access.yml` and the
  2026-07-28 handoff's recorded ACL could not be resolved from a
  read-only wiki-authoring session; the console is authoritative and
  must be checked directly.

**Neutral.**
- `.vault_pass` still exists only on `ct-dev-homelab` — every vault
  secret (Cloudflare tokens, restic password, both Tailscale auth keys)
  would still die with that one container. Belongs in the password
  manager; tracked as an open item, not resolved by this ADR.
- Console root passwords remain unset; `pct enter` needs none, but the
  Proxmox web console login does. Tracked as a separate open item.

## References

- `REMOTE-ACCESS-HANDOFF.md` (workspace root) — full handoff this ADR
  and the associated wiki pages are drawn from
- `homelab-infra` commit `54d7f3a` — `feat(remote-access): keyless
  remote access via Tailscale + VS Code tunnels`
- [Tailscale access policy](../../../../wiki/architecture/tailscale-policy.md)
- [Remote access recovery](../../../../wiki/runbooks/remote-access-recovery.md)
- [Remote access topology](../../../../wiki/architecture/remote-access-topology.md)
