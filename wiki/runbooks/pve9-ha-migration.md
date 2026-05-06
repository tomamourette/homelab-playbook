---
title: "PVE 9 HA: groups → rules migration runbook"
slug: pve9-ha-migration
category: runbooks
last_reviewed: 2026-04-27
owner: tomamourette
related_pages: [tailscale-policy]
related_frs: []
related_adrs: []
status: draft
supersedes: []
superseded_by: null
tags: [proxmox, pve9, ha, runbook]
---

# PVE 9 HA: groups → rules migration runbook

## Summary

`ha-manager groupadd` is dead in PVE 9.1+. Use
`ha-manager rules add node-affinity <name> --nodes <csv> --resources <csv>`
with **resources required at creation** (no empty rules). Per-CT `--state`
matches the current run-state for project containers; always-on infra is
unconditionally `started`. **Always cross-check `ha-manager rules config`
against `/etc/pve/replication.cfg` before any pull-plug drill** — HA
without replication = `zfs error: dataset does not exist` and a fenced
resource. Error-state recovery is `disabled → diagnose → started`, never
`--state stopped` directly.

## Context

Proxmox VE 9.1.1 (verified 2026-04-24 on this cluster, kernel 6.17.2-1-pve)
has migrated the legacy HA-group abstraction to a new rules system. All
references to "HA groups" in older docs and pre-9.x story drafts are
obsolete:

- `ha-manager groupadd <name> --nodes ... --restricted 0 --nofailback 0`
  returns `cannot create group: ha groups have been migrated to rules`
  (exit 2)
- The pre-9.x split of "create groups (metadata-only) → assign CTs to
  groups (state-changing)" is no longer expressible. The new model
  couples rule and resource lifecycle.
- Source on a 9.x node:
  `/usr/share/perl5/PVE/HA/Rules.pm` and
  `/usr/share/perl5/PVE/HA/Rules/NodeAffinity.pm`. The PVE Manager source
  carries the marker
  `# TODO PVE 10: Remove group migration when HA groups have been fully migrated to rules`.

## Procedure

### 1. API translation table

| Pre-9.x (HA groups) | PVE 9.1+ (rules) |
|---|---|
| `ha-manager groupadd <name> --nodes ...` | `ha-manager rules add node-affinity <name> --nodes <csv> --resources <csv>` |
| `--restricted 0\|1` | `--strict 0\|1` (semantic equivalent) |
| `--nofailback 0\|1` on the group | per-resource: `ha-manager set <sid> --failback <0\|1>` |
| group with no members | not expressible — `--resources` is required at creation |

This cluster's four named rules:

| Name | strict | nodes | resources |
|---|---|---|---|
| `critical` | 0 | pve1,pve2,pve3 | ct:162 |
| `standard` | 0 | pve1,pve2,pve3 | ct:101, ct:151, ct:163, ct:250 (and others as designed) |
| `pinned-pve1` | 1 | pve1 | vm:100 |
| `pinned-pve3` | 1 | pve3 | ct:160 |

### 2. Per-CT state policy

Set `--state` at `ha-manager add` time per the operator's policy:

> "If running, fail over and start on peer. If stopped, migrate the
>  storage but stay stopped on peer."

| Resource class | `--state` at registration |
|---|---|
| Always-on infra (ct:162, ct:101, ct:160, ct:163, vm:100) | `started` unconditionally |
| Project containers (ct:151 sparkle-cps, ct:250 dev-homelab) | matches `pct status` at registration time |

After registration, state is operator-controlled day-to-day via
`ha-manager set <sid> --state stopped|started`. The Ansible role
[`pve-ha-rules`](git:homelab-infra/ansible/roles/pve-ha-rules/) asserts
**presence** of resources, rule definitions, and per-resource `failback`
— not `state`. Operator flips survive role runs.

### 3. Replication-vs-HA pre-flight (REQUIRED before any pull-plug drill)

```bash
ssh pve1 "cat /etc/pve/replication.cfg"   # source of truth for jobs
ssh pve1 "ha-manager rules config"        # source of truth for HA placement
```

For every resource in a rule with `nodes pve1,pve2,pve3` (failover-eligible),
the resource MUST have replication jobs to **both peer nodes**, or HA
failover hits `zfs error: dataset does not exist` and fences the resource
into `error` state.

Drill scripts gate on this — see
[`homelab-infra/ansible/roles/drill-safety/files/drill-safety-preflight.sh`](git:homelab-infra/ansible/roles/drill-safety/files/drill-safety-preflight.sh)
and the Python CI guard
[`homelab-infra/scripts/ci/check-ha-storage-placement.py`](git:homelab-infra/scripts/ci/check-ha-storage-placement.py).

Reference query:

```bash
for sid in $(ssh pve1 "ha-manager status" | awk '/^service/ {print $2}'); do
  vmid="${sid#*:}"
  repl_count=$(ssh pve1 "grep -cE \"^local: $vmid-\" /etc/pve/replication.cfg")
  # For non-pinned resources, expect repl_count >= 2 (one per peer node).
  # For strict-pinned, repl_count can be 0 (won't fail over).
  echo "$sid replication-jobs=$repl_count"
done
```

### 4. Error-state recovery sequence

PVE 9.x **rejects** `ha-manager set <sid> --state stopped` when the
resource is in `error` state with
`service '<sid>' in error state, must be disabled and fixed first`.

Correct sequence:

```bash
ssh pve1 "ha-manager set <sid> --state disabled"   # CRM stands down
sleep 15
# diagnose + fix the underlying cause (storage, lock, replication, etc.)
ssh pve1 "ha-manager set <sid> --state started"    # CRM resumes (~10s tick)
```

Worked example (ct:162 V4 drill rollback, 2026-04-25):

```bash
ssh pve1 "ha-manager set ct:162 --state stopped"
# → service 'ct:162' in error state, must be disabled and fixed first   FAIL

ssh pve1 "ha-manager set ct:162 --state disabled"
sleep 15
ssh pve3 "zfs rename rpool/data/subvol-162-disk-0-DRILL rpool/data/subvol-162-disk-0"
ssh pve1 "ha-manager set ct:162 --state started"
```

### 5. Stranded-config recovery (replication gap)

If HA placed the resource config on a node that does NOT have a working
dataset (Story 6-7 V5 drill on ct:151, 2026-04-25):

```bash
mv /etc/pve/nodes/<wrong-node>/lxc/<vmid>.conf \
   /etc/pve/nodes/<right-node>/lxc/<vmid>.conf
```

Combine with the disabled→diagnose→started sequence above.

## Pitfalls

- **Empty rules are impossible.** `ha-manager rules add node-affinity`
  rejects creation without `--resources`. List resources must already be
  HA-managed (`ha-manager add` first).
- **`nofailback` moved.** It is not a rule property; it lives per-resource
  as `failback` (semantic flip). Set with `ha-manager set <sid> --failback <0|1>`.
- **State drift is intentional.** The `pve-ha-rules` Ansible role does NOT
  re-assert `state:` after first registration. Editing the YAML default
  has no effect on already-registered resources; force re-registration with
  `ha-manager remove <sid>` first.
- **Pre-PVE-9 stories need rewriting, not patching.** The "create groups
  metadata-only → assign CTs" pattern doesn't translate. Collapse into a
  single story that creates rules with resources pre-populated; set
  per-resource `nofailback` separately.

## Common error-state triggers

- File-system errors on the resource's storage
- Missing storage mount on the home node (NFS gone, ZFS pool UNAVAIL)
- Network split during failover
- `max_restart` exhaustion (3 retries × ~30 s — PVE 9 default)
- Stale lock at `/var/lock/pve-manager/lock-<vmid>.lck`
- Snapshot corruption from interrupted `zfs send|recv`
- **Replication gap** (resource in failover-eligible rule but no replication
  job to the failover target — see §3)

## Cross-references

- [`homelab-infra/ansible/roles/pve-ha-rules/README.md`](git:homelab-infra/ansible/roles/pve-ha-rules/README.md)
  — single source of truth for rule + resource registration
- [`homelab-infra/ansible/roles/pve-ha-rules/defaults/main.yml`](git:homelab-infra/ansible/roles/pve-ha-rules/defaults/main.yml)
  — declared `ha_resources` + `ha_rules`
- [`homelab-infra/docs/ha-replication-runbook.md`](git:homelab-infra/docs/ha-replication-runbook.md)
  — full operator runbook including "Recovering an HA resource stuck in
  `error` state"
- [`homelab-infra/ansible/roles/drill-safety/files/drill-safety-preflight.sh`](git:homelab-infra/ansible/roles/drill-safety/files/drill-safety-preflight.sh)
- [`homelab-infra/scripts/ci/check-ha-storage-placement.py`](git:homelab-infra/scripts/ci/check-ha-storage-placement.py)
- `~/.claude/.../memory/project_pve9_ha_rules_migration.md`
- `~/.claude/.../memory/feedback_pve9_ha_error_recovery.md`
- `~/.claude/.../memory/feedback_ha_replication_audit_first.md`
- `~/.claude/.../memory/project_project_container_ha_policy.md`
- Story 6.3 (HA rule definitions + per-CT state policy)
- Story 6.10 (HA-state Prometheus exporter; alert `PVEHAResourceUnhealthy`
  deep-links to this runbook)
