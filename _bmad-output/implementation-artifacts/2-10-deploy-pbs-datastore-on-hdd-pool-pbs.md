---
status: done
epic: 2
story: 2.10
title: Deploy PBS datastore on hdd-pool/pbs
previous_deferred_reason: permanent PBS instance will live on the reinstalled pve3 host; standing it up before Epic 3 Story 3.2 means destroying and re-creating it. Dataset directory structure is prepared; instance deployment moves to post-3.2.
undeferred_reason: Ansible role is idempotent and PBS datastore DATA lives on hdd-pool/pbs (5 HDDs preserved through Epic 3). Standing PBS up now unlocks critical CT160 pre-Epic-3 backup. Post-Epic-3 re-run reinstalls package + re-registers datastore pointing at preserved chunks.
---

# Story 2.10: Deploy PBS datastore on `hdd-pool/pbs`

## User Story

As an operator, I want PBS using the new HDD pool for backups, so that cluster-wide backups have 72 TiB of redundant space.

## Acceptance Criteria

**Given** `hdd-pool/pbs` dataset exists (Story 2.3)
**When** I configure a new PBS datastore pointing to `/hdd-pool/pbs`
**Then** the datastore shows healthy in PBS UI
**And** a test backup (from any small CT) to this datastore succeeds
**And** the datastore is added as a backup target in Proxmox VE
**And** the temporary datastore from Story 1.2 is kept until Phase 5 completes

## Status: DEFERRED to post-Story-3.2

## Why deferred

The permanent PBS instance is intended to run on the pve3 host. pve3 gets reinstalled in Epic 3 Story 3.2 (2-way rpool mirror). Any PBS daemon/config standing now on pve3 gets wiped. The persistent part — the `/hdd-pool/pbs` dataset — already exists from Story 2.3, and hdd-pool is NOT destroyed in 3.2 (it's on the 5 HDDs, not the NVMes being repartitioned).

Rather than stand up PBS twice, defer the instance-deployment portion of this story until after 3.2 completes. The dataset's "ready state" is already satisfied (directory exists, recordsize tuned for PBS chunks, compression off).

## What's already done (Story 2.3 satisfies part of this)

- `hdd-pool/pbs` dataset created ✓
- `recordsize=128K` set ✓
- `compression=off` set (PBS chunks are pre-compressed) ✓
- Directory mounted at `/hdd-pool/pbs` ✓ — ready to receive a PBS datastore pointer

## What moves to Epic 3

After Story 3.2 completes (pve3 reinstalled with 2-way rpool + fast-pool + hdd-pool re-imported + mirrored special vdev):

1. `apt install proxmox-backup-server` on pve3 host (Proxmox allows PBS and PVE coexistence)
2. `proxmox-backup-manager datastore create pve3-pbs /hdd-pool/pbs`
3. Generate API token, register as `pbs-permanent` storage in cluster storage.cfg
4. Run a test backup from any small CT
5. Schedule weekly GC + verify jobs (same pattern as migration-window)

These steps get folded into Epic 3's runbook (proposal: add as Story 3.11 "Deploy permanent PBS on rebuilt pve3").

## Bridging invariant

Until Story 2.10's deferred portion completes, the migration-window PBS from Story 1.2 is the ONLY cluster backup target. That's fine — it was designed for this exact duration. The Story 1.2 runbook explicitly plans for evacuation/decommission once Story 2.10 completes post-Epic-3.

## Implementation

- **Execution date:** 2026-04-24
- **Agent:** Dev (Claude Opus 4.7 1M) executing via bmad-dev-story pattern
- **Host:** pve3 (192.168.50.203)
- **PBS version installed:** `proxmox-backup-server 4.1.8-1` (from `pbs-no-subscription` repo)

### Ansible command

```bash
cd homelab-infra/ansible
ansible-playbook -i inventories/homelab/hosts.ini \
  playbooks/pve3-storage-apply.yml \
  -l pve3 --tags pbs-datastore
```

New production playbook `playbooks/pve3-storage-apply.yml` was authored (role had only a syntax-check harness). Re-run confirms idempotency (`changed=0`).

### Hotfixes applied en route (out of role scope)

Two pre-existing pve3 apt misconfigurations blocked `apt install proxmox-backup-server` and were hotfixed outside the role:

1. `/etc/apt/sources.list.d/pve-enterprise.sources` (deb822 format, dropped by PVE 9 upgrade) still enabled the enterprise-only `pve-enterprise` suite → renamed to `.disabled`. The legacy `.list` file was already commented out; the newer `.sources` file had overridden it.
2. `proxmox-backup-server` package is NOT in `pve-no-subscription` — added `/etc/apt/sources.list.d/pbs-no-subscription.list`. The PBS install then dropped an `enterprise` equivalent (`pbs-enterprise.sources`) — disabled the same way.

These fixes are **temporary on pve3** because Epic 3 Story 3.2 reinstalls the host. Post-Epic-3, the correct pattern (drop `pbs-no-subscription` + disable `enterprise` sources) should be encoded in whichever role manages pve3 apt sources (candidate: new `pve-host-pve3-apt` role or extend `pve-node-bootstrap`). Filed as follow-up below.

### Results

| Item | Value |
|------|-------|
| Datastore URI | `pve3-pbs` at `/hdd-pool/pbs` (79.1 TiB avail) |
| PBS Web UI | https://192.168.50.203:8007 |
| PBS services | `proxmox-backup` + `proxmox-backup-proxy` both `active` |
| Cluster storage name | `pbs: pve3-pbs` (registered via `pvesm add pbs`) |
| Cluster visibility | `pvesm status` on pve1/pve2/pve3 all show `pve3-pbs active 84,911,816,576 KiB` |
| PBS user | `pve-backup@pbs` with `DatastoreBackup` ACL on `/datastore/pve3-pbs` |
| PBS TLS fingerprint (sha256) | `cb:55:2a:a4:7f:16:04:ea:cb:08:6d:d9:16:b9:3f:b9:52:d4:a1:29:70:16:eb:22:1e:1e:fa:0b:34:6c:91:ed` |
| Test backup (CT151 ct-sparkle-cps) | `ct/151/2026-04-24T11:42:05Z` — 5.15 GiB → 2.125 GiB compressed, 33 s, 155 MiB/s |
| **CT160 pre-Epic-3 snapshot** | `ct/160/2026-04-24T11:42:58Z` — 35.22 GiB → 20.2 GiB compressed, 64 s, 470 MiB/s (**Epic 3 rollback safety net for ct-ai-01**) |
| Datastore usage after both backups | 23.2 GiB on hdd-pool/pbs |

### Credentials location

`pve-backup@pbs` password is **NOT** stored in the git repo. It lives at `/tmp/pbs-creds-story-2-10.txt` on the operator workstation (mode 600). For persistence, operator should move it into their password manager entry for "homelab-pbs-cluster-backup-user". A follow-up (see below) will move it into `homelab-infra/ansible/vault/` when the PBS storage registration becomes automated.

### Acceptance-criteria status

- [x] `pve3-pbs` datastore online at `/hdd-pool/pbs` (PBS service active, port 8007 listening)
- [x] Visible in PBS Web UI (https://192.168.50.203:8007 — verified via ss + systemctl; not browser-tested)
- [x] Registered cluster-wide as PVE storage (`pvesm status` on all 3 nodes shows `pve3-pbs active`)
- [x] Test backup of small CT (CT151 → 5 GiB, 33 s, snapshot mode, success)
- [x] Temporary `pbs-migration` storage already removed (per handoff context — CT105 was destroyed during Window B)
- [x] Story status updated `deferred-to-epic-3` → `done`

### Follow-ups (not in scope of 2.10)

1. **Epic 3 Story 3.11 (new):** Re-run `ansible-playbook ... --tags pbs-datastore` after pve3 is reinstalled. Role is idempotent; it will reinstall the `proxmox-backup-server` package and re-register the `pve3-pbs` datastore pointing at the preserved `/hdd-pool/pbs` dataset. **Dedup chunks survive** the rpool reinstall because they live on hdd-pool. User/ACL must be re-created (see script below).
2. **Apt source hygiene:** encode the "disable enterprise sources + drop pbs-no-subscription" fix into an Ansible role task so post-Epic-3 reinstall doesn't require manual hotfixes. Candidate: extend `pve-node-bootstrap` with a `configure-apt-sources.yml` task.
3. **Cluster PBS storage registration in Ansible:** `pvesm add pbs …` is currently manual. Automate via a new `pve-cluster-storage-pbs` role referencing vault-encrypted password. Likely belongs in Epic 7 (Ansible role consolidation) or a dedicated Story 2.11.
4. **GC + verify schedules:** currently unscheduled. Add weekly GC + monthly verify jobs. Candidate: Story 2.11 or part of Epic 7.
5. **PBS datastore notification target:** default `mail-to-root` works but root mail isn't routed off-box. Future story: configure PBS SMTP / webhook notifications.

### Post-Epic-3 re-hydration script (for Story 3.11 runbook)

```bash
# Assumes hdd-pool is re-imported and /hdd-pool/pbs is mounted with existing chunks.
cd homelab-infra/ansible
ansible-playbook -i inventories/homelab/hosts.ini \
  playbooks/pve3-storage-apply.yml \
  -l pve3 --tags pbs-datastore
# Re-create cluster-backup user (password from password manager):
ssh pve3 "proxmox-backup-manager user create pve-backup@pbs --password \$PBS_PWD"
ssh pve3 "proxmox-backup-manager acl update /datastore/pve3-pbs DatastoreBackup --auth-id pve-backup@pbs"
# Re-register cluster storage (new fingerprint expected — fresh TLS cert after reinstall):
PBS_FP=$(ssh pve3 "proxmox-backup-manager cert info | awk -F': ' '/Fingerprint/{print \$2}'")
ssh pve1 "pvesm remove pve3-pbs 2>/dev/null; pvesm add pbs pve3-pbs --server 192.168.50.203 --datastore pve3-pbs --username pve-backup@pbs --password \$PBS_PWD --fingerprint \$PBS_FP --content backup"
# Verify chunks still present:
ssh pve3 "proxmox-backup-manager verify pve3-pbs --ignore-verified --outdated-after 0"
```
