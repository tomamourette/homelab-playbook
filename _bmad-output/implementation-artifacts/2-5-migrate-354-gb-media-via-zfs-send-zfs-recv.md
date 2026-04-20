---
status: done
epic: 2
story: 2.5
title: Migrate 354 GB media via zfs send | zfs recv
---

# Story 2.5: Migrate 354 GB media via `zfs send | zfs recv`

## User Story

As an operator, I want the media library copied to `hdd-pool` via native ZFS replication, so that the transfer is fast, preserves structure, and never leaves pve3.

## Acceptance Criteria

**Given** `hdd-pool` exists and `shared-pool@pre-migration` snapshot exists
**When** I run `zfs send -R shared-pool@pre-migration | zfs recv -F hdd-pool/bulk-staging`
**Then** the command completes successfully
**And** `zfs list hdd-pool/bulk-staging` shows approximately 354 GB used
**And** `ls /hdd-pool/bulk-staging/nfs/media/` shows `movies`, `tv`, `downloads`, `books`, `music`

## Tasks

- [x] Run `zfs send -R shared-pool@pre-migration | zfs recv -F hdd-pool/bulk-staging`
- [x] Verify transferred size
- [x] Verify content tree

## Dev Notes

- `pv` was not installed on pve3 (would have given progress bar) — fell back to running without, which worked on first try.
- Transfer time ~5–10 minutes (not precisely measured, executed as single SSH call with no progress instrumentation).
- The `-R` flag does recursive/replication including the snapshot itself, so `hdd-pool/bulk-staging@pre-migration` exists on the receive side.
- Used `-F` on recv to replace any existing dataset (there wasn't one) — safe because we just created `hdd-pool`.

## Implementation Report

```
$ zfs list -r hdd-pool/bulk-staging
NAME                        USED  AVAIL  REFER  MOUNTPOINT
hdd-pool/bulk-staging       355G  79.4T   153K  /hdd-pool/bulk-staging
hdd-pool/bulk-staging/nfs   355G  79.4T   355G  /hdd-pool/bulk-staging/nfs
```

355G total matches expected ~354 GB source with minor accounting variance. Content tree verified (dump, images, media, private). Story 2.6 then ran full SHA-256 manifest diff against this and confirmed zero-byte drift.
