---
status: done
epic: 2
story: 2.7
title: Promote staging to final location and rename datasets
---

# Story 2.7: Promote staging to final location and rename datasets

## User Story

As an operator, I want the staging dataset renamed into its final position, so that the path structure matches the intended `hdd-pool/bulk/media` layout.

## Acceptance Criteria

**Given** staging-area media is verified byte-for-byte (Story 2.6)
**When** I destroy the empty placeholder `hdd-pool/bulk` (created in Story 2.3) and run `zfs rename hdd-pool/bulk-staging/nfs hdd-pool/bulk`
**Then** `zfs list | grep hdd-pool/bulk` shows the correct dataset at the expected path
**And** `ls /hdd-pool/bulk/media/` shows the media contents
**And** `recordsize=1M` is inherited/set on the renamed dataset

## Tasks

- [x] `zfs destroy hdd-pool/bulk` (empty placeholder from Story 2.3)
- [x] `zfs rename hdd-pool/bulk-staging/nfs hdd-pool/bulk`
- [x] `zfs destroy -r hdd-pool/bulk-staging` (needed `-r` because `@pre-migration` snapshot came over from Story 2.5's `zfs send -R`)
- [x] Re-apply `recordsize=1M` on the renamed dataset (properties survive rename but worth re-asserting)
- [x] Verify final tree

## Dev Notes

- `zfs destroy` required `-r` to include the `@pre-migration` snapshot under `bulk-staging`. This is expected behavior: the snapshot was replicated across by `zfs send -R`.
- After destroy, the original `shared-pool@pre-migration` on nvme1 remains untouched — still there as rollback option until Story 2.11.

## Implementation Report

```
$ zfs list -r hdd-pool
NAME                     USED  AVAIL  REFER  MOUNTPOINT
hdd-pool                 355G  79.4T   217K  /hdd-pool
hdd-pool/bulk            355G  79.4T   355G  /hdd-pool/bulk
hdd-pool/models          153K  79.4T   153K  /hdd-pool/models
hdd-pool/pbs             153K  79.4T   153K  /hdd-pool/pbs
hdd-pool/quant-history   153K  79.4T   153K  /hdd-pool/quant-history

$ ls /hdd-pool/bulk/media/
books  downloads  movies  music  tv

$ du -sh /hdd-pool/bulk/media/*
512	books      (empty)
200G	downloads
47G	movies
512	music      (empty)
110G	tv
```

All content present at the target path. Ready for Story 2.8 NFS cutover.
