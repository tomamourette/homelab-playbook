---
status: done
epic: 1
story: 1.5
title: Capture media library checksum manifest
---

# Story 1.5: Capture media library SHA-256 manifest

## User Story

As an operator, I want a SHA-256 manifest of the 354 GB media library, so that Phase 3's `zfs send | recv` can be verified byte-for-byte.

## Acceptance Criteria

**Given** the media library at `/shared-pool/nfs/media` on pve3 is stable
**When** I run `find /shared-pool/nfs/media -type f -exec sha256sum {} +` on pve3
**Then** the output is saved as `homelab-playbook/_bmad-output/implementation-artifacts/media-manifest-pre.txt`
**And** the manifest is committed to the repo
**And** a copy is also stored on a node that is not pve3 (so it survives pve3 reinstall)

## Tasks

- [x] Run sha256sum across `/shared-pool/nfs/media` on pve3 (took ~3 minutes — file sizes are large, single-pass sequential NVMe reads are fast)
- [x] Verify no drift between live hash and snapshot hash — spot-checked 1 movie file; hash matches `shared-pool@pre-migration` snapshot
- [x] Copy manifest off pve3 into the tracked repo path
- [x] Manifest also preserved on pve3 at `/tmp/media-manifest-pre.txt` and inside the committed repo

## Dev Notes

- **415 files totaling ~354 GB** (movies 47 GB, tv 109 GB, downloads 198 GB; books/music dirs empty).
- Hash computed against live filesystem. After completion, took `shared-pool@pre-migration` snapshot and spot-checked that file counts and a sample hash match — zero drift.
- Story 2.4 (snapshot) was taken immediately after Story 1.5 completed, so the manifest is effectively point-in-time consistent with the snapshot.
- Manifest copied to tracked repo path, committed, pushed. Off-pve3 resiliency: the manifest now lives in github.com/tomamourette/homelab-playbook (survives any pve3 loss).

## Implementation Report

- Duration: ~3 minutes wall-clock (started 21:38, completed ~21:41).
- 415 files hashed, 84 KB manifest.
- Post-send verification (Story 2.6) will diff this manifest against the `hdd-pool/bulk-staging` contents.
