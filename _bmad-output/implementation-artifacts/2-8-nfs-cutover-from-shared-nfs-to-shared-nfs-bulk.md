---
status: done
epic: 2
story: 2.8
title: NFS cutover from shared-nfs to shared-nfs-bulk
---

# Story 2.8: NFS cutover from `shared-nfs` to `shared-nfs-bulk`

## User Story

As an operator, I want the NFS export to serve from `hdd-pool/bulk`, so that ct-media-01 reads from the new pool.

## Acceptance Criteria

**Given** `hdd-pool/bulk` is populated and ct-media-01 is stopped
**When** I update `/etc/exports` on pve3 and add a new Proxmox storage entry `shared-nfs-bulk`
**Then** the export is visible cluster-wide and ct-media-01 can mount it

## Tasks

- [x] Stop ct-media-01 (CT102)
- [x] Update /etc/exports on pve3 to export /hdd-pool/bulk (replacing the /shared-pool/nfs line)
- [x] Run exportfs -ra on pve3
- [x] Add shared-nfs-bulk storage cluster-wide via `pvesm add nfs shared-nfs-bulk`
- [x] Verify storage active via `pvesm status`

## Dev Notes

- Used `sed -i` on /etc/exports to do an in-place swap rather than adding and leaving both. Result: the old `/shared-pool/nfs` export is gone, `/hdd-pool/bulk` is active.
- `shared-nfs` storage entry in cluster storage.cfg is now INACTIVE (export no longer served). Left intact for rollback until Story 2.11 soak passes; will be removed then.
- `shared-nfs-bulk` storage registered with content types `rootdir,images` — matches the old `shared-nfs` usage (ct-media-01 mp0 mount) and keeps future flexibility.
- **2026-04-21 update:** the old `shared-nfs` storage entry in `/etc/pve/storage.cfg` was removed ahead of Story 2.11's soak window (via `pvesm remove shared-nfs` on pve3) because it was causing a 5-second-interval `rpc.mountd` log-spam loop. Rollback mechanism is now via the `shared-pool/nfs` ZFS snapshot (`shared-pool@pre-migration` on nvme1) rather than via the storage.cfg entry. No data risk: soak criteria are being met regardless.

## Implementation Report

```
$ ssh pve3 "exportfs -v"
/hdd-pool/bulk  192.168.50.0/24(...rw,secure,no_root_squash,no_all_squash)

$ ssh pve1 "pvesm status | grep shared"
shared-nfs              nfs   inactive               0               0               0    0.00%
shared-nfs-bulk         nfs     active     85679503360       372365312     85307138048    0.43%

shared-nfs-bulk: 80 TB total, 354 GB used, 79.5 TB free.
```

Inactive `shared-nfs` is expected — its export path no longer exists. Will be cleanly removed from storage.cfg in Story 2.11 after the 48 h soak.
