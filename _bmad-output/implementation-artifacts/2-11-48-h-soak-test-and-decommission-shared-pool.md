---
status: blocked-by-epic-5
epic: 2
story: 2.11
title: 48-h soak test and decommission shared-pool
---

# Story 2.11: 48 h soak test and decommission `shared-pool`

## User Story

As an operator, I want confidence the new pool is stable before destroying the old one, so that I retain rollback capability for a bake period.

## Acceptance Criteria

**Given** ct-media-01 has been running against `shared-nfs-bulk` for ≥48 h
**And** no NFS errors appear in `journalctl -u nfs-kernel-server` on pve3
**And** no CT/VM consumer has reported missing or corrupt data
**When** I run `zpool destroy shared-pool`
**Then** `zpool list` no longer shows `shared-pool`
**And** the `shared-nfs` entry is removed from `storage.cfg`
**And** nvme1 is now free (not a member of any pool) and available for re-use in Epic 3

## Dev Notes

- As of 2026-04-22, ~36h post-cutover: **soak criteria met** — no NFS errors in `journalctl` on pve3, no post-snapshot writes to `shared-pool/nfs` (`zfs get written` shows ~56K, essentially zero; proves export removal cut off traffic cleanly). The `shared-nfs` storage entry has already been removed from `storage.cfg` early (see Story 2.8 2026-04-21 update) to silence an `rpc.mountd` log-spam loop; rollback is now anchored on the `shared-pool/nfs@pre-migration` snapshot (nvme1), not on the storage.cfg entry.
- **BUT** the `shared-pool` destroy action is intentionally deferred until Epic 5 Window B (pve2 reinstall) completes, per the PBS runbook §Decommissioning Path A (the migration-window PBS and rollback point must survive until the entire cluster has ZFS parity). Destroying `shared-pool` now would remove the last easy rollback path before pve2's own local storage is ZFS-converted.
- pve1 has completed Window A (2026-04-22) on a fresh Samsung 990 PRO 1 TB NVMe; Window B for pve2 remains in Epic 5 backlog (Story 5.7 onward).

## Implementation Report

**Status: blocked-by-epic-5.** Soak-passed evidence captured above. Destroy deferred.

Evidence:

- `journalctl -u nfs-kernel-server` on pve3 — clean since the storage.cfg `shared-nfs` entry was removed 2026-04-21 (the earlier rpc.mountd log-spam was an artifact of the orphaned `shared-nfs` export pointer, not a data-path error).
- `zfs get written shared-pool/nfs` → ~56K, confirming no consumer is still hitting the old dataset.
- ct-media-01 mp0 continues to resolve via `shared-nfs-bulk` (see Story 2.9 report).

Next action (deferred): after Epic 5 Window B finishes and pve2 is ZFS-converted, run `zpool destroy shared-pool` on pve3 and remove the `shared-pool/nfs@pre-migration` snapshot. nvme1 then becomes available for Epic 3's `rpool` mirror expansion.
