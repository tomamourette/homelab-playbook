---
status: deferred-to-epic-3
epic: 2
story: 2.10
title: Deploy PBS datastore on hdd-pool/pbs
deferred_reason: permanent PBS instance will live on the reinstalled pve3 host; standing it up before Epic 3 Story 3.2 means destroying and re-creating it. Dataset directory structure is prepared; instance deployment moves to post-3.2.
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
