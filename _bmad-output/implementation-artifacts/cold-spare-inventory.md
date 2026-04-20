# PVE3 hdd-pool Cold Spare Inventory

## Purpose

The pve3 `hdd-pool` is a RAIDZ1 vdev of 5x 22 TB WD Purple Pro drives — single-parity, so it tolerates exactly one drive failure. During a resilver (which at 22 TB scale runs many hours to several days), a second-drive failure is catastrophic: the entire pool and the 354 GB media library it holds are lost. The risk this cold spare mitigates is not drive failure itself (inevitable) but **time-to-replace**: having a sealed drive already on the shelf turns a 3-7 day shipping window into a 15-minute physical swap, collapsing the exposure window where the pool is running degraded and a second failure would be fatal.

## Target drive spec

| Field         | Value                                                                              |
|---------------|------------------------------------------------------------------------------------|
| Model family  | Western Digital Purple (Pro)                                                       |
| Device model  | WDC WD221PURP-85CJRY0                                                              |
| Part number   | WD221PURP                                                                          |
| Capacity      | 22 TB (22,000,969,973,760 bytes)                                                   |
| Form factor   | 3.5"                                                                               |
| Interface     | SATA 6 Gb/s                                                                        |
| Rationale     | Exact match to the 5 production drives below — identical firmware family, identical capacity, identical acoustic/vibration profile, identical warranty terms. Avoids RAIDZ member-size truncation and minimizes behavioural surprises during resilver. |

## Production HDD inventory (pve3, captured 2026-04-20)

| Slot | Device | Model                 | Serial    | Capacity |
|------|--------|-----------------------|-----------|----------|
| 1    | sda    | WDC WD221PURP-85CJRY0 | 6LJ7HEUT  | 22 TB    |
| 2    | sdb    | WDC WD221PURP-85CJRY0 | 6LHYV64U  | 22 TB    |
| 3    | sdc    | WDC WD221PURP-85CJRY0 | 69G94MNE  | 22 TB    |
| 4    | sdd    | WDC WD221PURP-85CJRY0 | 6LJ59RET  | 22 TB    |
| 5    | sde    | WDC WD221PURP-85CJRY0 | 68G2NL9H  | 22 TB    |

Source command: `for d in sda sdb sdc sdd sde; do smartctl -i /dev/$d | grep -E 'Device Model|Serial'; done` on pve3.

## Procurement ownership & gating

- **Owner:** tomamourette (Tom)
- **Target order-by date:** within 7 days of Epic 1 start (i.e. before Story 1.2 completes)
- **Target on-shelf date:** within 14 days of order placement (regional supplier lead times)
- **Gate rule:** Epic 2 (bulk storage foundation — pve3 HDD pool creation) **MUST NOT** start until this record shows `Status: on shelf`. This is a hard gate; violating it reintroduces the "drive fails during initial RAIDZ1 resilver with no replacement available" risk the cold spare exists to mitigate.
- **Alternative coverage:** if procurement is delayed beyond 21 days, consider converting to RAIDZ2 (§4 research doc alternatives) — 1 disk of capacity for permanent 2-failure tolerance, no physical-spare dependency.

## Cold spare record

| Status    | Order date | Supplier | Serial | Delivery date | Physical location | Notes |
|-----------|------------|----------|--------|---------------|-------------------|-------|
| to order  | TBD        | TBD      | TBD    | TBD           | TBD               | TBD   |

Fields to fill in post-procurement:

- **Status**: `to order` → `ordered` → `received` → `on shelf` → (eventually) `consumed <date>` (update as state changes)
- **Order date**: ISO date (YYYY-MM-DD) the order was placed
- **Supplier**: vendor + order reference (e.g. "Amazon DE #123-456", "Mindfactory invoice 789"). Record the supplier's region — warranty/RMA channels differ between WD EU, WD US, and WD APAC.
- **Serial**: record from the drive label (or from `smartctl -i` once powered in an external dock during on-arrival verification below)
- **Delivery date**: ISO date received — this starts the warranty clock (5 years for WD Purple Pro in most regions; confirm at receipt, attach warranty PDF to repo)
- **Physical location**: e.g. "homelab shelf, anti-static bag, top of rack"
- **Notes**: firmware revision from label, any visible damage, shipping condition

## On-arrival verification (before shelving)

Do NOT just drop the new drive into storage — the 30-day return window lapses fast, and DOA drives are common enough to warrant a 10-minute sanity check:

1. Connect the drive via an external SATA/USB dock to a Linux machine (or pve3 itself in a spare bay if convenient).
2. Run `smartctl -a /dev/sdX` — check `Reallocated_Sector_Ct = 0`, `Current_Pending_Sector = 0`, zero power-on hours (or a few from factory test), temperature sane.
3. Run `smartctl -t short /dev/sdX` and wait ~2 minutes; verify `Self-test execution status: completed without error` via `smartctl -l selftest /dev/sdX`.
4. Record the serial + firmware revision into the cold spare record above, then seal in anti-static bag and shelve.

Skipping this step has bitten every homelab operator at least once. Don't be the outlier.

## Shelf-aging health checks (while the spare is on the shelf)

A sealed drive is not a healthy drive. Capacitor aging, stiction, and firmware clock bugs can cause a spare to be DOA after 12-24 months of shelf time — exactly when you need it.

- **Cadence:** every 6 months (set a calendar reminder at procurement)
- **Procedure:** power the spare in an external dock, run `smartctl -t short /dev/sdX`, verify clean self-test, record the date + `Power_On_Hours` delta in the cold spare record's Notes field. Takes 5 minutes wall-clock.
- **Failure action:** if the shelf drive fails a self-test, immediately treat the cold-spare inventory as empty — order a replacement and RMA the failed one before the warranty window closes.

## Rotation procedure (when a production drive fails)

**Chassis capability (pve3-specific, verified 2026-04-20):** the 5 HDD bays are behind a JMicron JMB58x AHCI controller (PCI `c1:00.0`). AHCI CAP register reports hot-plug-relevant bits set (`ahci_host_caps = 0xef33ff84`). AHCI hot-plug on JMB58x is reported supported but has a mixed reputation in the community — **not yet test-verified on this specific N5 Pro**. Treat as "probably works, but don't trust it blindly at 3am."

**Safe default: cold-swap with pve3 powered down.** Use hot-swap only after you have verified it with a test pull on a scratch pool at a non-critical time. Cold-swap adds ~5 minutes of downtime for the node and is vastly safer.

### 0. Diagnose BEFORE pulling anything

The entire premise of this rotation is "a disk failed." Verify that first — a flaky SATA cable, a failing backplane, or a controller PHY fault presents identically to disk failure and will burn the cold spare for nothing:

- `zpool status -v hdd-pool` — note exactly which drive(s) are reported failed, the specific error counts, and whether the failure is single-drive or pattern-across-multiple-drives (the latter strongly implies controller/cable, not disk).
- `dmesg -T | tail -200 | grep -iE 'ata|link|reset|error'` — look for link-reset storms, SATA PHY errors, command-timeout patterns. A healthy drive with a bad cable will log dozens of `exception Emask 0x10 SAct 0x0 SErr 0x40d0000` lines.
- Physically pull the reported-failed drive, connect it via external SATA dock on a separate machine, run `smartctl -a` and `smartctl -t short`. If SMART is clean and the self-test passes, the drive is fine and the failure is in the pve3 chassis (cable, backplane, or controller). **Do not insert the cold spare into a bad slot** — fix the chassis issue first, or move the pool's operation to a different slot.

If and only if the drive genuinely failed SMART checks in an external dock, proceed:

### 1. Physically swap
Power pve3 down (safe default), pull the failed drive, insert the cold spare in the same bay. Power back up. (Hot-swap alternative: pull and insert while running, only if you've previously verified JMB58x hot-plug works on this system.)

### 2. Find the new drive's by-id path
`ls -l /dev/disk/by-id/ | grep <new-drive-serial>` — gives the exact `ata-WDC_WD221PURP-85CJRY0_<serial>` string to use. Do NOT use `/dev/sdX` — device letters can shuffle after reinsert.

### 3. Trigger resilver
`zpool replace hdd-pool <failed-by-id> <new-by-id>`. Watch progress with `zpool status hdd-pool` — expect hours to days depending on pool fill.

### 4. Record the new serial
Update this file — move the cold spare's serial into the production inventory table at the failed slot, update the cold spare record status to `consumed <YYYY-MM-DD>`, and commit the change so the cluster state stays authoritative in git.

### 5. Re-order replacement
Immediately order a new WD221PURP cold spare (same model, same supplier channel if pricing is comparable). The pool runs fully-redundant once resilver completes, but we are back to zero cold spares until the new one arrives — minimize that window.

### Fallback SKU (if WD221PURP becomes EOL)

WD Purple Pro line may be rotated out; if WD221PURP is unavailable:
1. First preference: next-gen WD Purple Pro at same capacity (e.g. future `WD225PURP` style part)
2. Second preference: WD Red Pro 22 TB (different SKU family but same reliability class)
3. Third preference: Seagate IronWolf Pro 22 TB
Mixing SKUs in a RAIDZ1 vdev is fine for ZFS; match capacity exactly (or the RAIDZ member size is truncated to the smallest).
