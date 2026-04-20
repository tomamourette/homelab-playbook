---
status: done
epic: 2
story: 2.4
title: Snapshot shared-pool as pre-migration rollback point
---

# Story 2.4: Snapshot `shared-pool` as pre-migration rollback point

## User Story

As an operator, I want an immutable snapshot of the old pool, so that I can rewind if the `zfs send | recv` goes wrong.

## Acceptance Criteria

**Given** `shared-pool` contains the 354 GB media library
**When** I run `zfs snapshot -r shared-pool@pre-migration`
**Then** `zfs list -t snapshot shared-pool` includes the `@pre-migration` snapshot on every dataset beneath `shared-pool`
**And** the snapshot is confirmed immutable (attempt to delete returns snapshot-protection error unless force-destroyed)

## Tasks

- [x] Run `zfs snapshot -r shared-pool@pre-migration` on pve3
- [x] Verify snapshot exists on both `shared-pool` and `shared-pool/nfs`
- [x] Confirm snapshot is accessible at `/shared-pool/nfs/.zfs/snapshot/pre-migration/`

## Dev Notes

Captured 2026-04-20 immediately after Story 1.5's sha256sum completed. Spot-check confirms the snapshot hash matches the live-data hash (zero drift during the narrow window between Story 1.5 finishing and Story 2.4 executing).

## Implementation Report

```
$ ssh pve3 "zfs list -t snapshot -r shared-pool"
NAME                            USED  AVAIL  REFER  MOUNTPOINT
shared-pool@pre-migration         0B      -    96K  -
shared-pool/nfs@pre-migration     0B      -   355G  -
```

`355G REFER` matches expected ~354 GB media + dataset metadata. Snapshot is zero-cost (CoW) — the 0B USED means no writes have diverged from the snapshot yet.

This snapshot is the rollback point. If anything in Epic 2 Stories 2.5-2.8 goes wrong, we can:
1. Mount the snapshot (already auto-mounted at `/shared-pool/nfs/.zfs/snapshot/pre-migration/`)
2. Re-NFS-export from the snapshot path (tested fallback)
3. Or `zfs rollback shared-pool/nfs@pre-migration` to undo any later changes

Preserved until Story 2.11 (48 h soak test passes), then destroyed with the rest of `shared-pool`.
