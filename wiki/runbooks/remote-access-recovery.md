---
title: "Remote access recovery — new PC / locked out"
slug: remote-access-recovery
category: runbooks
last_reviewed: 2026-07-28
owner: tomamourette
related_pages: [tailscale-policy, remote-access-topology, create-project-container]
related_frs: []
related_adrs: [ADR-001]
status: stable
supersedes: []
superseded_by: null
tags: [tailscale, ssh, vscode-tunnel, remote-access, runbook, disaster-recovery]
---

# Remote access recovery — new PC / locked out

## Summary

As of 2026-07-28 the homelab uses a **keyless** remote-access design:
Tailscale SSH is primary (no SSH keys at all), VS Code tunnels cover
browser-only access, and SSH keys are a fallback distributed by
`ssh-authorized-keys.yml`. A new PC needs three installs and zero file
copies. If every path is somehow down, `pct enter` from any PVE host
needs no password and always works. This runbook is the "I have a new
PC" / "I am locked out" procedure.

## Context

The previous workstation (`tom-notebook-1`) died and took the only copy
of the `homelab-infra` SSH private key with it. Every container trusted
that one key and nothing else, so a new PC had no way in. The
containers were never truly unreachable — `pct enter` from a PVE host
needs no password — but the *credential* was gone. Three separate
keyless mechanisms already existed and were all dormant; this work
activated them. Root cause worth remembering: **one credential, on one
device, with no second path.** See [ADR-001](../../_bmad-output/planning-artifacts/products/remote-access/adrs/ADR-001-tailscale-primary-keys-fallback.md)
for the full decision record.

Only two containers are keyless-reachable today: `ct-dev-homelab`
(`tag:control`, the only container permitted to SSH to the others) and
`ct-sparkle-cps` (`tag:container`). Onboarding a new container to this
design is a separate, explicit step — see
[Onboard a new container](#onboard-a-new-container-to-keyless-remote-access)
below.

## Procedure

### New-PC setup (3 steps, no files copied)

1. **Install Tailscale.** Sign in as `tom.amourette@...`. Tailnet:
   `taildf9e93.ts.net`.
2. **Install VS Code.** Sign in with **Microsoft** (not GitHub — the
   GitHub OAuth authorisation for VS Code tunnels was deliberately
   revoked). Both `ct-dev-homelab` and `ct-sparkle-cps` appear in the
   Remote Explorer's tunnel list automatically.
3. **Optional: install the Tailscale VS Code extension.** It shows a
   clickable list of tailnet-reachable machines and is the intended
   replacement for a hand-maintained `~/.ssh/config` — do not maintain
   one.

No SSH keys, no `~/.ssh/config`, no repo clone.

Once on the tailnet, shell in with Tailscale SSH (no keys):

```bash
ssh ct-dev-homelab.taildf9e93.ts.net
ssh ct-sparkle-cps.taildf9e93.ts.net
```

Browser-only access (needed for both containers because the Tailscale
extension requires desktop VS Code and vscode.dev cannot do
Remote-SSH):

```
https://vscode.dev/tunnel/ct-dev-homelab
https://vscode.dev/tunnel/ct-sparkle-cps
```

### Break-glass path

`pct enter <vmid>` from **any** PVE host (pve1 `192.168.50.201`, pve2
`192.168.50.202`, pve3 `192.168.50.203`) needs no password and always
works, independent of Tailscale, VS Code tunnels, or SSH keys. This is
the path of last resort — e.g. Tailscale itself is misconfigured on the
target container. It requires being on the PVE host itself (physical
access, or Proxmox web console).

### Read-only health check

Safe to run at any time; changes nothing:

```bash
cd ~/workspace/homelab/homelab-infra/ansible
ansible-playbook playbooks/remote-access-verify.yml
```

Reports, per host: Tailscale backend state, declared vs. actual tags,
auth key id, key shape/scope, tunnel state, VS Code CLI version. Narrow
with `--limit <host>` for a single container.

### Onboard a new container to keyless remote access

Not automatic for new project containers created via
[Create a new project container](create-project-container). To add one:

1. Add the container to `[remote_access_hosts]` in
   `homelab-infra/ansible/inventories/homelab/hosts.ini`.
2. Add its CTID to `lxc_tun_ctids` in
   `homelab-infra/ansible/playbooks/lxc-enable-tun.yml` — unprivileged
   LXC has no `/dev/net/tun` by default, and Tailscale SSH cannot serve
   without it. This is a PVE-host-side operation (the device is granted
   in the container's config), so it lives in its own playbook rather
   than the `remote-access` role.
3. Declare a tag in the tailnet ACL if the container needs one beyond
   the shared `tag:container` scope (see
   [Remote access topology](remote-access-topology) for the ACL and why
   it is unversioned).
4. Ensure a scoped auth key exists in the vault. `tag:container` uses
   `vault_tailscale_authkey`; a distinct tag (like `tag:control`) needs
   its own key — a Tailscale auth key carries its own tags and cannot
   grant one it is not scoped to. Helper on `ct-dev-homelab`:
   `~developer/add-tailscale-key.sh [variable_name]` — stores a key into
   the vault with hidden input, shape validation, and a character count.
5. Run, in order:

   ```bash
   cd homelab-infra/ansible
   ansible-playbook playbooks/lxc-enable-tun.yml -e '{"lxc_tun_ctids":[<vmid>]}'
   ansible-playbook playbooks/remote-access.yml --limit ct-<name>
   ansible-playbook playbooks/remote-access-verify.yml --limit ct-<name>
   ```

## Gotchas — each of these caused a real outage

1. **Never set `--accept-routes` on a node inside an advertised
   subnet.** The tailnet's subnet router advertises `192.168.50.0/24`,
   which is the LAN these containers are on. Accepting it installs that
   route via `tailscale0`, outranking `eth0`, and blackholes all LAN
   traffic including inbound SSH. The container stays alive but is
   reachable only via `pct exec`. `remote_access_tailscale_accept_routes`
   defaults to `false` for this reason — only set `true` for a node
   *outside* `192.168.50.0/24` that needs to reach the LAN.

2. **One auth key per tag.** A Tailscale auth key carries its own tags
   and cannot grant a tag it is not scoped to. A `tag:container` key
   silently rejoins a `tag:control` host on the wrong tag, losing its
   SSH-source privilege — and only on rebuild, which is the worst time
   to find out.

3. **Tagging alone breaks Tailscale SSH.** A tagged node is owned by
   the tailnet, so a stock ACL rule targeting `autogroup:self` stops
   matching it. The `ssh` rule must target the tag explicitly.

4. **A stale `code` CLI breaks browser tunnels only.** vscode.dev
   always serves the current workbench and refuses a server it does not
   match, failing with *"The workbench failed to connect to the server
   (Error: Network Error)"*. Desktop VS Code negotiates its own server
   and keeps working, so the browser path breaks silently and alone.
   The `remote-access` role compares the installed CLI against current
   stable every run. The symptom can also survive as a cached service
   worker — clear site data for vscode.dev, or test in a private
   window.

5. **Unprivileged LXC has no `/dev/net/tun`.** Tailscale SSH cannot
   serve without it. Granted by `playbooks/lxc-enable-tun.yml`, which
   needs a container restart and only restarts containers whose config
   it actually changed.

6. **`tailscale up --reset` with a rejected tag leaves the node logged
   out.** The reset clears prefs before the tag is validated. The
   `remote-access` role catches this, rejoins without tags, and warns
   rather than leaving the host off the tailnet.

7. **Hidden password prompts invite duplicate pastes.** `read -rsp`
   echoes nothing, which reads as "the paste failed", so a key can get
   pasted several times and concatenated. It stores happily and only
   fails at the moment it's depended on — during a rebuild, the worst
   time to discover it. `add-tailscale-key.sh` prints a character count
   and validates the key shape to catch this before it's stored.

## Cross-references

- [Tailscale-only access policy](tailscale-policy) — tailnet-first
  access rule, now widened to cover SSH; the ACL lives only in the
  Tailscale admin console (unversioned)
- [Remote access topology](remote-access-topology) — the four
  overlapping access mechanisms and when to use which
- [Create a new project container](create-project-container) — step 8
  now points here for operator access verification
- `homelab-infra/ansible/roles/remote-access/` — the role (Tailscale +
  VS Code tunnel)
- `homelab-infra/ansible/playbooks/remote-access.yml` — apply
- `homelab-infra/ansible/playbooks/remote-access-verify.yml` — read-only
  health check
- `homelab-infra/ansible/playbooks/ssh-authorized-keys.yml` — SSH-key
  fallback distribution
- `homelab-infra/ansible/playbooks/lxc-enable-tun.yml` — PVE-host-side
  `/dev/net/tun` grant
- commit `54d7f3a` in `homelab-infra` — `feat(remote-access): keyless
  remote access via Tailscale + VS Code tunnels`
