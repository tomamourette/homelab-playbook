---
status: done
epic: 2
story: 2.6
title: Verify media via SHA-256 manifest diff
---

# Story 2.6: Verify media via SHA-256 manifest diff

## User Story

As an operator, I want cryptographic proof that every byte of media transferred correctly, so that I can declare Phase 3 complete with confidence.

## Acceptance Criteria

**Given** the media is on `hdd-pool/bulk-staging` (Story 2.5) and `media-manifest-pre.txt` exists (Story 1.5)
**When** I run `cd /hdd-pool/bulk-staging/nfs/media && find . -type f -exec sha256sum {} + > /tmp/media-manifest-post.txt`
**And** I run `diff /path/to/media-manifest-pre.txt /tmp/media-manifest-post.txt`
**Then** the diff returns empty (no output)
**And** if the diff is non-empty, the migration is considered FAILED and rolled back

## Tasks

- [x] Run sha256sum across the staging copy
- [x] Diff against the pre-migration manifest
- [x] Confirm zero-byte diff

## Dev Notes

All 415 files verified. Zero diff. The `zfs send | zfs recv` transfer was byte-perfect.

This is the cryptographic proof point: we can now say with high confidence that not a single bit of the 354 GB media library was corrupted, dropped, or modified during the migration.

## Implementation Report

```
$ diff /tmp/media-manifest-pre.txt /tmp/media-manifest-post.txt
(empty — zero output, exit 0)

$ wc -l /tmp/media-manifest-pre.txt /tmp/media-manifest-post.txt
   415 /tmp/media-manifest-pre.txt
   415 /tmp/media-manifest-post.txt
   830 total
```

Verification gate PASSED. Story 2.7 (promote to final location) is safe to proceed.
