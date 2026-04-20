---
status: done
epic: 2
story: 2.1
title: Identify and document all 5 HDDs by /dev/disk/by-id
---

# Story 2.1: Identify and document all 5 HDDs by `/dev/disk/by-id`

## User Story

As an operator, I want every HDD referenced by its stable `by-id` path, so that `zpool create` is not vulnerable to `/dev/sdX` letter reshuffling on reboot.

## Acceptance Criteria

**Given** the 5 HDDs are installed on pve3
**When** I run `ls -l /dev/disk/by-id/ | grep WD221PURP`
**Then** 5 distinct `ata-WDC_WD221PURP-…` paths are listed (one per physical drive)
**And** each `by-id` path is mapped to its serial number and captured in `hdd-inventory.md`
**And** the planned pool membership (all 5 in one RAIDZ1 vdev) is documented alongside

## Tasks

- [x] Run `ls -l /dev/disk/by-id/ | grep WD221PURP` on pve3 and capture output
- [x] Create `hdd-inventory.md` with slot/serial/by-id mapping table
- [x] Record the exact `zpool create` command ready for Story 2.2
- [x] Add "why by-id" rationale for operational defense

## Dev Notes

- All 5 drives confirmed as identical model (WDC WD221PURP-85CJRY0), no mixed firmware families.
- Serials match the production-HDD-inventory table in `cold-spare-inventory.md` (Story 1.1).
- `hdd-inventory.md` serves as both the current-state truth and the pool-construction command reference for Story 2.2.

## Implementation Report

Artifact: `hdd-inventory.md`. Captured mapping for all 5 drives; pre-built the `zpool create` command ready to copy into Story 2.2.
