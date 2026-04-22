---
status: done
epic: 2
story: 2.2
title: Create hdd-pool RAIDZ1 (without special vdev yet)
---

# Story 2.2: Create `hdd-pool` RAIDZ1 (without special vdev yet)

## User Story

As an operator, I want a RAIDZ1 ZFS pool across all 5 HDDs, so that bulk data has redundancy and a canonical home.

## Acceptance Criteria

**Given** all 5 HDDs are identified by `by-id` (Story 2.1)
**When** I run `zpool create -o ashift=12 -O compression=zstd-3 -O atime=off -O xattr=sa hdd-pool raidz1 <by-id-1> <by-id-2> <by-id-3> <by-id-4> <by-id-5>`
**Then** `zpool status hdd-pool` shows `state: ONLINE`, a single `raidz1-0` vdev of 5 disks, 0 errors
**And** `zpool list hdd-pool` shows ~100 TB raw / ~72 TiB usable
**And** the pool is visible in Proxmox UI under Datacenter → Storage → (pending addition)

## Tasks

- [x] Run `zpool create` on pve3 with all 5 HDDs via by-id paths from Story 2.1
- [x] Verify `zpool status` ONLINE, 0 errors
- [x] Verify usable capacity matches expectations

## Dev Notes

- Pool created on pve3 2026-04-20 using the exact command form in AC above (by-id paths only, no `/dev/sdX`).
- No special vdev attached at this stage — that's deferred to Story 3.4 (after pve3's NVMe layout is ready in Epic 3). The pool runs metadata on HDDs for now; small-block performance will be lifted once the mirrored metadata special vdev is added.
- `ashift=12` chosen for 4K native sector alignment; `compression=zstd-3` balances bulk-media compressibility vs CPU; `atime=off` + `xattr=sa` standard ZFS-on-Linux hygiene.

## Implementation Report

```
$ ssh pve3 "zpool status hdd-pool"
  pool: hdd-pool
 state: ONLINE
config:
        NAME                                      STATE     READ WRITE CKSUM
        hdd-pool                                  ONLINE       0     0     0
          raidz1-0                                ONLINE       0     0     0
            ata-WDC_WD221PURP-85CJRY0_6LJ7HEUT    ONLINE       0     0     0
            ata-WDC_WD221PURP-85CJRY0_6LHYV64U    ONLINE       0     0     0
            ata-WDC_WD221PURP-85CJRY0_69G94MNE    ONLINE       0     0     0
            ata-WDC_WD221PURP-85CJRY0_6LJ59RET    ONLINE       0     0     0
            ata-WDC_WD221PURP-85CJRY0_68G2NL9H    ONLINE       0     0     0
errors: No known data errors
```

Raw capacity ~100 TB; usable ~72 TiB after RAIDZ1 parity overhead. Ready for Story 2.3 dataset creation.
