---
status: review
epic: 7
story: 7.14
title: Fix ct-dev-homelab inventory drift (.150 → .156)
created: 2026-04-25
author: BMad SM
---

# Story 7.14: Fix ct-dev-homelab inventory drift

Status: review

## Story

As an operator,
I want the Ansible inventory's `ct-dev-homelab` entry to reflect the container's actual IP (`192.168.50.156`, CT 250 on pve3) instead of its stale pre-migration IP (`192.168.50.150`),
so that any role or playbook targeting `ct-dev-homelab` resolves to the live host instead of failing connection or — worse — connecting to whatever might later occupy `.150`.

## Business value

Trivial bookkeeping fix. The drift was surfaced by the Story 6-9-1 `fix-apply` F5 deviation: when verification ran against `ct-dev-homelab`, the inventory pointed at `.150` while the live container had been migrated to pve3 as CT 250 with IP `.156`. Cost of leaving it: every operator who runs an Ansible task against this host hits a connection failure (best case, immediate signal) or — once `.150` is reassigned to a different container — silently runs against the wrong host (worst case, undetected blast radius). Cost to fix: a 5-line `s/150/156/` and a ping check. The asymmetry is overwhelming; ship it.

## Acceptance Criteria

### AC-1: Ansible can ping ct-dev-homelab via inventory

**Given** the inventory has been updated
**When** I run `LC_ALL=C.UTF-8 LANG=C.UTF-8 ansible -i inventories/homelab/hosts.ini ct-dev-homelab -m ping`
**Then** the host responds `SUCCESS` with `"ping": "pong"`
**And** `--list-hosts ct-dev-homelab` resolves to exactly one host: `ct-dev-homelab`.

### AC-2: No `.150` references remain in the homelab inventory

**Given** the edit is complete
**When** I `grep -rn "192.168.50.150\|VMID 150" ansible/inventories/homelab/`
**Then** zero matches are returned.

## Files modified

`homelab-infra`:

- `ansible/inventories/homelab/hosts.ini` — `ct-dev-homelab ansible_host=192.168.50.150` → `192.168.50.156`
- `ansible/inventories/homelab/host_vars/ct-dev-homelab/vars.yml` — header comment `VMID 150, pve2, 192.168.50.150` → `VMID 250, pve3, 192.168.50.156`
- `ansible/inventories/homelab/host_vars/ct-dev-homelab/vault.yml` — header comment same as above
- `ansible/inventories/homelab/group_vars/all.yml` — `dev_homelab_ip: 192.168.50.150` → `192.168.50.156`

## Commit

- `homelab-infra@cc78909` — `fix(inventory): ct-dev-homelab IP .150 → .156 (Story 7.14)`

## Dev Agent Record

**Agent:** Code Implementation Agent (Opus 4.7)
**Date:** 2026-04-25

**Pre-flight verification:**

```
$ ssh root@192.168.50.156 "hostname"
ct-dev-homelab
```

Hostname matches expectation — proceeded with edits.

**Post-edit verification (AC-1):**

```
$ cd ansible && LC_ALL=C.UTF-8 LANG=C.UTF-8 \
    ansible -i inventories/homelab/hosts.ini ct-dev-homelab -m ping
ct-dev-homelab | SUCCESS => {
    "changed": false,
    "ping": "pong"
}

$ LC_ALL=C.UTF-8 LANG=C.UTF-8 \
    ansible -i inventories/homelab/hosts.ini --list-hosts ct-dev-homelab
  hosts (1):
    ct-dev-homelab
```

**Post-edit verification (AC-2):**

```
$ grep -rn "192.168.50.150\|VMID 150" ansible/inventories/homelab/
(no output — zero matches)
```

Both ACs pass. Status flipped to `review`.

**Notes:**

- The `homelab-infra` working tree had unrelated in-flight changes (Cloudflare token plumbing for Story 7.11, plus other docs/terraform edits). The 7.14 commit `cc78909` is scoped to the 4 inventory files only — the cloudflare block in `group_vars/all.yml` was preserved separately and is not part of this commit.
- Commits not pushed per instruction.
