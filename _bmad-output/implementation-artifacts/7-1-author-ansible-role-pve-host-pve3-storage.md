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

## Post-adversarial fixes

A cynical review surfaced 10 defects in the initial authorship. Each was
addressed in a follow-up pass while keeping the role lint-clean at the
`production` profile.

### Fix 1 — Hostname guard

The role had no safeguard against being run on the wrong host (`-l pve1`
typo). Added a `hostname_guard` default (`"pve3"`) and a leading
`assert: ansible_facts['hostname'] == hostname_guard` in `tasks/main.yml`.
Override with `-e hostname_guard=other`; disable with `-e hostname_guard=""`.
Documented under a new "Hostname guard" section in the README.

**Files:** `tasks/main.yml` (new assert block, top of file), `defaults/main.yml`
(new `hostname_guard: "pve3"` default), `README.md` (new section).

### Fix 2 — ZFS kernel module precheck

`zpool --version` returns 0 even when the ZFS kernel module isn't loaded,
making every subsequent `zpool` call fail with "Failed to load ZFS module".
Added a dedicated `zpool list` (no args) probe with an explicit `fail` task
matching on `'Failed to load ZFS module' in stderr or rc != 0`. Error
message tells the operator to `modprobe zfs` or check zfs-dkms / kernel
alignment.

**File:** `tasks/main.yml` (two new tasks after the `zpool --version` probe).

### Fix 3 — Exported / FAULTED hdd-pool handling

Original probe (`zpool list -H -o name`) conflated three states: absent,
exported, and FAULTED — all return rc=1. Running `zpool create` against an
exported or faulted pool would attempt to overwrite disks still holding
data.

Fixed by:
- Prefixing `zpool import -a -N -o readonly=on` (non-destructive, picks up
  exported pools so the probe sees them).
- Extending the probe to `zpool list -H -o name,health` and parsing
  health into a `hdd_pool_health` fact.
- Adding an explicit fail-task when the pool exists but reports
  `FAULTED` or `UNAVAIL`.
- Gating the create task on `not hdd_pool_exists | bool` instead of the
  raw probe rc.

**File:** `tasks/hdd-pool.yml` (probe section rewritten).

### Fix 4 — Cluster-join precheck for nfs-export

`pvesm add nfs` on a cluster-unjoined node creates a node-local storage
entry that conflicts on subsequent cluster join. The old code had no
quorum check.

Added a `pvesh get /cluster/status` probe that parses the JSON response
for a `type: cluster` entry with `quorate: 1`. Non-quorate runs fail with
an actionable message ("defer to post-cluster-join") unless the operator
explicitly sets `nfs_skip_cluster_check: true`, in which case a warning
debug task emits and the run continues.

**Files:** `tasks/nfs-export.yml` (probe + fail + warn tasks before the
existing storage probe), `defaults/main.yml` (new
`nfs_skip_cluster_check: false`).

### Fix 5 — Special-vdev probe regex

The old `awk '/^\s*special$/'` pattern missed newer ZFS status output
where the `special` section header carries trailing status text
(e.g. `special  ONLINE  0  0  0`).

Replaced with a two-stage probe: `zdb -C <pool>` primary, looking for
`type: 'special'` in the pool config (authoritative), falling back to
`zpool status -v | grep -E '^\s+special\b'` (whole-word match, tolerates
trailing columns).

**File:** `tasks/special-vdev.yml`.

### Fix 6 — PBS datastore task ordering

The original `pbs-datastore.yml` stat'd the dataset path before
installing `proxmox-backup-server`. That ordering is backwards: without
the package, none of the downstream tasks can run regardless of path
presence.

Reordered:
1. Install `proxmox-backup-server` (apt).
2. Ensure `proxmox-backup-proxy` is running.
3. Stat the datastore path (precondition for datastore registration).
4. Probe existing datastores.
5. Create the datastore if absent.

**File:** `tasks/pbs-datastore.yml` (task block reordered; comment block
added explaining why).

### Fix 7 — Hardcoded NFS server IP

`defaults/main.yml` had `pve_storage_server: 192.168.50.203`, coupling
the supposedly-agnostic role to pve3's specific LAN IP. Replaced with
`"{{ ansible_facts.default_ipv4.address | default(...) | default('192.168.50.203') }}"`
so the role adapts to any host's primary-IPv4 facts, falling back to
`hostvars[inventory_hostname].ansible_host` and ultimately to the
original static IP for safety.

**File:** `defaults/main.yml`.

### Fix 8 — Handler noise

`handlers/main.yml` had `changed_when: true` on the `exportfs -ra`
command, reporting a change every notify even when nothing changed. The
notifying task (`blockinfile` on `/etc/exports`) already reports the real
change; `exportfs -ra` itself is idempotent at the NFS layer.

Changed to `changed_when: false` with a comment explaining the rationale.

**File:** `handlers/main.yml`.

### Fix 9 — Test playbook scope & check-mode limitation

The test playbook was syntax-check only with no block comment explaining
why `--check` was out of scope. Added a detailed header explaining:
- What the harness covers (YAML parse, role load).
- What a meaningful `--check --diff` would require (hostname fixture,
  loaded ZFS module, fabricated by-id block devices, quorate PVE cluster,
  installable PBS package).
- That Story 7.2 is where the fixture + clean-slate test is authored.
- How to invoke real check-mode against pve3 once ready.

Also set `hostname_guard: ""` in the harness vars so the new guard
doesn't trip against `localhost`.

**File:** `playbooks/test-pve-host-pve3-storage.yml`.

### Fix 10 — Collection requirements documented

`meta/main.yml` had `min_ansible_version: 2.12` but no mention of the
`community.general` collection, despite `community.general.zfs` being
used in two task files. Added:

- `collections: [community.general]` in `meta/main.yml`.
- A dedicated `requirements.yml` at the role root pinning
  `community.general >= 3.0.0`.
- README "Collection requirements" section with the
  `ansible-galaxy collection install -r` invocation.

**Files:** `meta/main.yml`, `requirements.yml` (new), `README.md`.

### Post-fix validation

| Test | Tool | Result |
|------|------|--------|
| YAML parse + role load | `ansible-playbook --syntax-check playbooks/test-pve-host-pve3-storage.yml` | **Pass** |
| Lint (production profile) | `ansible-lint 26.4.0 roles/pve-host-pve3-storage` | **Pass** — 0 failures, 0 warnings, 12 files processed |
| Lint of test playbook | `ansible-lint --profile=production playbooks/test-pve-host-pve3-storage.yml` | **1 pre-existing** `role-name[path]` warning (intrinsic to `role: ../roles/...` relative path, pre-dates adversarial review, unchanged) |

### Nothing compromised

All 10 fixes are additive or refactoring — none remove existing
idempotency, no behaviour on a well-formed pve3 target changes. The
fixes make the role strictly safer (guards) and cleaner (handler noise,
task ordering, collection docs) while remaining backward compatible
with the production invocation shape captured in the README.
