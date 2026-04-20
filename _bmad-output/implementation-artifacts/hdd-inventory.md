# PVE3 HDD Inventory (hdd-pool RAIDZ1 members)

Captured: 2026-04-20
Source: `ssh pve3 'ls -l /dev/disk/by-id/ | grep WD221PURP'`

## Mapping (slot → serial → by-id)

| Slot | Linux device | Serial   | Model                 | `by-id` path                                                |
|------|--------------|----------|-----------------------|-------------------------------------------------------------|
| 1    | sda          | 6LJ7HEUT | WDC WD221PURP-85CJRY0 | `/dev/disk/by-id/ata-WDC_WD221PURP-85CJRY0_6LJ7HEUT`        |
| 2    | sdb          | 6LHYV64U | WDC WD221PURP-85CJRY0 | `/dev/disk/by-id/ata-WDC_WD221PURP-85CJRY0_6LHYV64U`        |
| 3    | sdc          | 69G94MNE | WDC WD221PURP-85CJRY0 | `/dev/disk/by-id/ata-WDC_WD221PURP-85CJRY0_69G94MNE`        |
| 4    | sdd          | 6LJ59RET | WDC WD221PURP-85CJRY0 | `/dev/disk/by-id/ata-WDC_WD221PURP-85CJRY0_6LJ59RET`        |
| 5    | sde          | 68G2NL9H | WDC WD221PURP-85CJRY0 | `/dev/disk/by-id/ata-WDC_WD221PURP-85CJRY0_68G2NL9H`        |

## Intended pool membership

Single RAIDZ1 vdev across all 5 drives — `hdd-pool` per research doc §4.1. All 5 drives contribute to capacity + parity; any 1-drive loss is survivable, 2-drive simultaneous loss is catastrophic (mitigated by Story 1.1 cold spare).

## `zpool create` command (ready for Story 2.2)

```bash
zpool create -o ashift=12 \
  -O compression=zstd-3 -O atime=off -O xattr=sa \
  hdd-pool raidz1 \
    /dev/disk/by-id/ata-WDC_WD221PURP-85CJRY0_6LJ7HEUT \
    /dev/disk/by-id/ata-WDC_WD221PURP-85CJRY0_6LHYV64U \
    /dev/disk/by-id/ata-WDC_WD221PURP-85CJRY0_69G94MNE \
    /dev/disk/by-id/ata-WDC_WD221PURP-85CJRY0_6LJ59RET \
    /dev/disk/by-id/ata-WDC_WD221PURP-85CJRY0_68G2NL9H
```

## Why `by-id` not `/dev/sdX`

Linux block-device letters are assigned in detection order at boot. On a hot-plug event (cable reseat, drive replacement, controller rescan) the letters can reorder — `sda` yesterday might be `sdc` today. If `zpool create` was given `sda`, the pool may fail to import or, worse, import with the wrong drive mapping. The `by-id` path is derived from the drive's own serial + model, so it tracks the physical drive no matter which SATA port or slot it ends up on.

Source of truth for serial → by-id mapping in an emergency:
```bash
ls -l /dev/disk/by-id/ | grep WD221PURP
```
