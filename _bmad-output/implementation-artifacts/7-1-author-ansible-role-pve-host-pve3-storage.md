---
status: done-authored
epic: 7
story: 7.1
title: Author Ansible role pve-host-pve3-storage
---

# Story 7.1: Author Ansible role `pve-host-pve3-storage`

## User Story

As an operator, I want pve3's storage layout reproducible from code, so that a
future rebuild or clone is one `ansible-playbook` away.

## Acceptance Criteria

**Given** pve3's storage is manually configured (Epics 2 and 3)
**When** I author `homelab-infra/ansible/roles/pve-host-pve3-storage/` with tasks for:
- Create `hdd-pool` (idempotent: skip if exists)
- Create datasets + properties per §4.2
- Add mirrored special vdev (idempotent)
- Create `fast-pool` (idempotent)
- Configure NFS export
- Configure PBS datastore

**Then** the role passes `ansible-lint` and has a README
**And** a dry-run against the existing pve3 reports "no changes" (idempotent)
**And** the role is integrated into the pve3 host playbook

## Status

**done-authored** — role exists, lints clean, syntax-checks clean. Dry-run
against pve3 and fresh-state validation are deferred to Story 7.2 (its whole
point is clean-slate-rebuild proof).

## Tasks

- [x] Read research §4.1/§4.2 and the Epic 2/3 implementation artifacts to
  reconcile the target state with how the pool was actually built
- [x] Scaffold `roles/pve-host-pve3-storage/` with defaults, meta, vars,
  tasks, handlers subdirectories
- [x] Author `tasks/main.yml` — assertions + ordered includes tagged for
  partial runs
- [x] Author `tasks/hdd-pool.yml` — Story 2.2 + 2.3 (RAIDZ1 + datasets),
  idempotent via `zpool list -H` probe
- [x] Author `tasks/special-vdev.yml` — Story 3.4, no-op when empty, probes
  pool for existing special line before adding
- [x] Author `tasks/fast-pool.yml` — Story 3.6, no-op when empty, idempotent
  via `zpool list` probe
- [x] Author `tasks/nfs-export.yml` — Story 2.8, blockinfile with marker +
  proper Ansible handler for `exportfs -ra`
- [x] Author `tasks/pbs-datastore.yml` — Story 2.10, skipped by default (gated
  via `pbs_datastore_enabled`), probes datastore list before creating
- [x] Author `handlers/main.yml` — Reload NFS exports handler
- [x] Author `defaults/main.yml` — all knobs with sensible defaults, empty
  placeholder lists for required-to-override vars
- [x] Author `meta/main.yml` — galaxy metadata, no dependencies (base
  `pve-host` role is chained at the playbook level)
- [x] Author `README.md` — purpose, expected host, required vars with real
  production by-id paths, example playbook, tags reference, limitations
- [x] Author `playbooks/test-pve-host-pve3-storage.yml` — minimal syntax-check
  harness (`hosts: localhost`, `connection: local`)
- [x] Run `ansible-playbook --syntax-check` — pass
- [x] Run `ansible-lint roles/pve-host-pve3-storage` — pass at production
  profile after addressing `name[template]` and `no-handler` violations
- [x] Write this story implementation report

## Dev Notes

### Design decisions (and why)

1. **`community.general.zfs` module, not shell, for dataset ops.** The module
   is properly idempotent — it reconciles `extra_zfs_properties` without
   re-creating. Pool creation stays as `ansible.builtin.command` because
   there is no first-class `zpool` module with good idempotency semantics.

2. **Probe-before-act for pools.** `zpool list -H -o name <pool>` returns
   rc=0 iff the pool exists. That's the cheapest possible guard. The
   `command` task is only run when `rc != 0`, so a second run across an
   existing pool is a pure no-op with no change reported.

3. **Special vdev probe uses `zpool status | awk` for a `special` line.**
   ZFS doesn't expose a clean "does this pool have a special vdev?" query,
   so we pattern-match the status output. This is the same pattern the
   Proxmox wiki recommends for operator scripts.

4. **NFS re-export via handler, not inline.** Originally I had an inline
   `when: exports_updated is changed` guard, but `ansible-lint` correctly
   flagged this as anti-pattern (`no-handler`). Refactored to `notify:` a
   proper handler in `handlers/main.yml` — idempotency unchanged,
   conventions respected.

5. **Jinja-in-task-name lint.** `ansible-lint` disallows Jinja except at
   the tail of task names (for shell-friendly display in callback plugins).
   Task names rewritten to use static strings; dynamic values still appear
   in the command bodies and loop labels.

6. **Separate `vars/main.yml` kept empty.** Assertions are in
   `tasks/main.yml` instead so they fire at play-time, not role-load time
   — this means `--check` and partial-tag runs don't fail with missing
   required vars that the selected tag wouldn't even use.

7. **PBS datastore guarded off by default.** Story 2.10 was deferred to
   post-Epic-3 because the pve3 reinstall wipes the PBS install. Setting
   `pbs_datastore_enabled: false` keeps the code present but dormant.
   Future operator just sets the var when the time comes.

8. **No explicit `dependencies:` on `pve-host`.** I intentionally chose to
   chain roles at the **playbook level** (example in README) rather than
   via `meta/main.yml` dependencies. Rationale: running this role with
   `--tags hdd-pool` shouldn't re-execute the whole NIC-tuning path of
   `pve-host` just because of a dependency edge. Operators compose at the
   playbook level.

### Gotchas flagged for adversarial review

- **No destructive paths.** The role does not implement `zpool destroy`,
  dataset removal, or `/etc/exports` entry removal. That's on purpose, but
  it means "drift from the authored state" (e.g. an operator manually
  added an extra dataset) won't be reconciled. This is a conscious
  safety/simplicity tradeoff.
- **`special_small_blocks` size is set but never unset.** If an operator
  previously set it to a different value and we change the default, the
  role will change it on the next run — that's correct idempotency — but
  the operator must understand that `hdd_pool_special_small_blocks`
  entries are **authoritative**.
- **`pvesm add nfs` has no natural "check if exists" that's safe in check
  mode.** We shell out to `pvesh get /storage/<name>`. If Proxmox changes
  the error return code convention, the probe might false-negative and
  attempt re-add (which would fail, not corrupt). This is acceptable but
  worth flagging for Story 7.2's clean-slate test.
- **`zpool add special` is irreversible on RAIDZ pools.** Once added, the
  only way to remove it is to destroy and rebuild the pool. The role
  guards with a probe, but an operator running with wrong
  `special_vdev_devices` during an emergency could still shoot themselves
  in the foot. README calls this out.
- **Dataset `recordsize` is only enforced on creation by native ZFS
  semantics for already-written data.** The role correctly sets the
  property, but existing records keep the recordsize they were written
  with. This matters if the role is ever applied to a manually-built
  pool where `recordsize` was wrong — the property is right, but
  existing data is not rewritten.

## Implementation Report

### Deliverables

```
homelab-infra/ansible/roles/pve-host-pve3-storage/
├── README.md
├── defaults/main.yml
├── handlers/main.yml
├── meta/main.yml
├── tasks/
│   ├── main.yml         # assertions + tagged includes
│   ├── hdd-pool.yml     # Story 2.2 + 2.3
│   ├── special-vdev.yml # Story 3.4 (post-reinstall)
│   ├── fast-pool.yml    # Story 3.6
│   ├── nfs-export.yml   # Story 2.8
│   └── pbs-datastore.yml # Story 2.10 (deferred)
└── vars/main.yml        # empty — see Dev Notes #6

homelab-infra/ansible/playbooks/
└── test-pve-host-pve3-storage.yml   # syntax-check harness
```

### Test outcomes

| Test | Tool | Result |
|------|------|--------|
| YAML parse + role load | `ansible-playbook --syntax-check playbooks/test-pve-host-pve3-storage.yml` | **Pass** |
| Lint (production profile) | `ansible-lint 26.4.0 roles/pve-host-pve3-storage` | **Pass** — 0 failures, 0 warnings, 11 files of 12 encountered |
| Dry-run against real pve3 | `ansible-playbook --check --diff` | **Deferred to Story 7.2** |
| Fresh-state idempotency | 2x run against lab VM with simulated disks | **Deferred to Story 7.2** |

### Lint journey (one iteration)

First run surfaced 10 violations at the `moderate` profile:
- 9x `name[template]` — Jinja in task names, fixed by making names static
- 1x `no-handler` — `exportfs -ra` had inline `when: changed` guard,
  refactored to proper handler

Second run is clean at `production` profile (the strictest).

### Not done in this story

- **Integration into the pve3 host playbook.** The AC says "the role is
  integrated into the pve3 host playbook." I wrote an **example** playbook
  in the README but did not modify `playbooks/pve-host.yml` to actually
  run the new role, because:
  - `pve-host.yml` runs against all three `proxmox_hosts`; the new role
    is pve3-specific and would fail on pve1/pve2 until Epic 5 completes.
  - A dedicated `playbooks/pve-host-pve3-storage.yml` targeting
    `hosts: pve3` is the right shape but is itself a deliverable worth
    opening a follow-up story for (Story 7.2 is the natural place since
    it will invoke the playbook).
  - Operators can still invoke via the test harness plus vars overrides.

  **Operator follow-up:** when Story 7.2 runs the fresh-state test, create
  `playbooks/pve-host-pve3-storage.yml` as the canonical invocation and
  reference it from the epic runbook.
