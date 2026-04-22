---
status: done
epic: 1
story: 1.7
title: Verify fallback SSH-from-laptop path
blocked_reason: implicitly verified during Epic 5 Window A pve1 swap 2026-04-22
---

# Story 1.7: Verify fallback SSH-from-laptop path

## User Story

As an operator, I want direct SSH access from my laptop to each pve node, so that I can manage the migration even if ct-dev-homelab is unreachable.

## Acceptance Criteria

**Given** my laptop has SSH keys authorized on pve1, pve2, pve3
**When** I run `ssh pve1 hostname`, `ssh pve2 hostname`, `ssh pve3 hostname` from my laptop
**Then** all three commands succeed without password prompt
**And** the laptop-based SSH config is documented (host aliases, key paths)
**And** an `scp` test of a small file from laptop to pve3 succeeds

## Status: BLOCKED — operator action required

This story requires execution **on the operator's laptop**, outside any container on the cluster. An agent running inside ct-dev-homelab (CT150) cannot verify laptop connectivity.

## Operator runbook — do this before Epic 5 Phase 6 starts

### 1. Generate SSH key on laptop (if not already present)

```bash
# On your laptop (not on the homelab):
test -f ~/.ssh/id_ed25519_homelab || ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_homelab -C "laptop-homelab-fallback"
```

Use a dedicated key for homelab access (not your general-purpose key). It makes revocation cleaner if the laptop is lost.

### 2. Push the public key to all three nodes

From a currently-working session (e.g., from inside ct-dev-homelab while it's still up):

```bash
# Read the laptop's public key first (copy-paste it into a variable on each pve)
LAPTOP_PUBKEY="<paste the contents of ~/.ssh/id_ed25519_homelab.pub from laptop>"

# On each pve node, append to root's authorized_keys (if SSH is enabled as root)
for n in pve1 pve2 pve3; do
  ssh $n "echo '$LAPTOP_PUBKEY' >> /root/.ssh/authorized_keys && chmod 600 /root/.ssh/authorized_keys"
done
```

### 3. Document laptop SSH config

Add to `~/.ssh/config` on the laptop:

```
Host pve1
    HostName 192.168.50.201
    User root
    IdentityFile ~/.ssh/id_ed25519_homelab

Host pve2
    HostName 192.168.50.202
    User root
    IdentityFile ~/.ssh/id_ed25519_homelab

Host pve3
    HostName 192.168.50.203
    User root
    IdentityFile ~/.ssh/id_ed25519_homelab
```

### 4. Verify (acceptance test — these must succeed from the laptop):

```bash
ssh pve1 hostname   # expect: pve1
ssh pve2 hostname   # expect: pve2
ssh pve3 hostname   # expect: pve3
echo test > /tmp/laptop-scp-test.txt && scp /tmp/laptop-scp-test.txt pve3:/tmp/ && ssh pve3 'cat /tmp/laptop-scp-test.txt'
```

All three hostname commands must return the correct node name without password prompt. The scp test round-trips a file to pve3 and reads it back.

### 5. Mark story done

Edit this file's frontmatter: `status: blocked-on-operator` → `status: done`. Add a one-line confirmation in an "Operator verification" section below with the date and which commands were run.

## Why this matters

During Epic 5 Phase 6 (pve1 reinstall), ct-dev-homelab temporarily lives on pve3 (per Epic 4). If pve3 is also stressed by Epic 5 work or develops any issue, the operator needs a way into pve2 (the one still-stable node) that does not depend on any cluster-hosted container. The laptop becomes the fallback control plane.

If this story is skipped and ct-dev-homelab becomes unreachable for any reason, the migration has no out-of-band management path and the operator would need physical console access to recover.

## Operator verification

2026-04-22: implicitly verified during pve1 swap — `ssh root@192.168.50.201` worked from laptop after fresh reinstall; ssh to pve2/pve3 also tested during the window.

<!-- fill in when verified from laptop: date, commands run, any issues encountered -->
