---
severity: P1
discovered: 2026-04-20
discovered_during: Story 1.3 (pre-migration PBS backup sweep)
status: OPEN — requires operator decision before migration continues
---

# P1 — pve1 NVMe hardware failure

## TL;DR

**pve1's NVMe (`nvme0n1`, Samsung 970 EVO Plus 500 GB) is developing hardware failures.** SMART shows 24 Media and Data Integrity Errors, 359 error log entries, and temperature 82°C / 93°C (critical threshold 85°C). dmesg shows repeated `critical medium error` events on sector ~224,110,720. Three attempts to back up VM100 (smarthome) all failed at exactly the 52% mark — the backup read ran into the bad sectors.

**Migration plan must pause here.** 10 of 11 cluster guests are safely backed up; VM100 is not.

## Evidence

### SMART summary (`smartctl -a /dev/nvme0n1` on pve1)

| Attribute | Value |
|-----------|-------|
| Percentage Used (wear) | 1% (so not a wear issue) |
| Media and Data Integrity Errors | **24** (non-zero = physical media failure) |
| Error Information Log Entries | **359** |
| Temperature | **82°C** (current), **93°C** (secondary sensor) — critical threshold is 85°C |
| Warning | Critical Warning: 0x00 (still "healthy" flag per NVMe spec, but error log tells the real story) |

### Error log (first 3 entries)

```
0   359  4  0xf223  0xc502  0x000  224117514  1  -  Unrecovered Read Error
1   358  4  0x8222  0xc502  0x000  224117194  1  -  Unrecovered Read Error
2   357  4  0xd221  0xc502  0x000  224117034  1  -  Unrecovered Read Error
```

All three errors are Unrecovered Read Errors in the same LBA neighborhood (~224,117,xxx). Not a single transient glitch — this is a sustained bad region.

### dmesg (`dmesg -T | grep critical`)

```
critical medium error, dev nvme0n1, sector 224110720 op 0x0:(READ) …
critical medium error, dev nvme0n1, sector 224111232 …
critical medium error, dev nvme0n1, sector 224113792 …
critical medium error, dev nvme0n1, sector 224114048 …
critical medium error, dev nvme0n1, sector 224114304 …
critical medium error, dev nvme0n1, sector 224116864 …
critical medium error, dev nvme0n1, sector 224117120 …
critical medium error, dev nvme0n1, sector 224117376 …
```

Multiple contiguous sector clusters affected. This is either bad flash cells or a failing controller region.

### VM100 backup reproducibility

Three attempts — all failed at ~52% / 16.8 GiB:
1. 19:32 vzdump snapshot mode → `err -61 No data available`
2. 22:03 vzdump snapshot mode → same
3. 22:11 vzdump **stop mode** → same

Stop-mode failing too means the error is NOT a snapshot issue, NOT a USB-passthrough fsfreeze issue — it is hardware.

## Impact on the migration plan

### Immediate impact

1. **VM100 has no pre-migration backup.** Without a backup, if pve1 is reinstalled (Epic 5 Story 5.2), VM100's data is lost. Home automation (Zigbee coordinator) goes down permanently with whatever state was on the failing sectors.
2. **All other pve1 CTs/VMs are at risk.** The NVMe is failing. CT101 (docker), CT102 (media rootfs), CT104, CT150 (operator workbench!), VM103 — all live on the same failing drive. Further bad sectors could corrupt any of them.
3. **Operator workbench CT150 itself is on the failing drive.** If nvme0n1 fully dies, the live SSH/git session we're running in vanishes.

### Medium-term impact

- **Epic 5 (pve1 reinstall) assumes the NVMe is fine and will reformat-and-restore.** With a failing NVMe, reformat will remap or refuse to remap bad blocks; either way, the new install is on a dying drive.
- **Epic 4 (workbench evacuation) just became more urgent** — CT150 should move to pve3 ASAP, not wait for the nominal Phase 5.5.

## Recommended operator actions (pick one)

### Option A — Replace pve1 NVMe first, then continue migration (recommended)

1. Order a new NVMe for pve1 immediately. Same-capacity or larger (500 GB→1 TB) is fine. 2.5" NVMe is not a thing; it's M.2. Candidates: Samsung 990 PRO 1 TB (matches pve3's trio), WD Black SN850X, or similar.
2. **Move the operator workbench (CT150) to pve3 NOW** using the Story 1.2 PBS backup. This is Story 4 executed early.
3. Attempt VM100 rescue using `ddrescue` (writes a copy with bad-block handling — best-effort, might save 99% of the data):
   ```bash
   ssh pve1 'apt install -y gddrescue && \
     lvchange -ay pve/vm-100-disk-1 && \
     ddrescue /dev/pve/vm-100-disk-1 /mnt/pve/shared-nfs-bulk/rescue/vm100-disk1.img /mnt/pve/shared-nfs-bulk/rescue/vm100-disk1.mapfile -r3'
   ```
   The resulting image will have zeros where bad sectors live; restore into a fresh VM and re-onboard the Zigbee coordinator (re-pair ~50 devices if its DB is corrupt).
4. When the new NVMe arrives: replace, reinstall Proxmox on it with ZFS (Epic 5 as originally planned), restore CTs from PBS. Old NVMe goes to e-waste.

### Option B — Continue migration, replace pve1 NVMe later

Viable only if you're willing to lose VM100's data.
- Proceed with Epic 3 (pve3 reinstall) — no dependency on pve1 NVMe health.
- Skip Epic 4 evacuation to pve3 (keeps CT150 on failing drive = additional risk).
- Epic 5 Phase 6 attempts pve1 reinstall on the failing NVMe. Probably works for a while but lives on a ticking clock.

**Not recommended.** Known failing hardware + high-temperature + VM100 data loss = avoidable outage.

### Option C — Accept VM100 loss, order NVMe in background

- Continue migration path.
- Accept VM100 smarthome is lost; rebuild household automation from scratch on a new VM after pve1 reinstall.
- Order new NVMe in parallel for when Epic 5 lands.

**Intermediate risk profile.** Loses automation state but doesn't drag the entire migration.

## Why the NVMe might be running at 82°C

The N5 Pro platform for pve1 is the CWWK CW-AD4L-N. Community reports indicate several of these units ship with under-spec thermal pads on the M.2 slot. At 82°C idle the drive is permanently throttling and likely accelerating its own failure.

Before installing the replacement NVMe, **inspect/replace the thermal pad on the M.2 slot.** Cheap fix, prevents a recurrence.

## What's already captured (so we can plan around this)

Per Story 1.4's pre-migration state snapshot: we have exact current VM100 config (`100.conf`), disk size (32 GB scsi0), USB passthrough IDs (10c4:ea60 — Silicon Labs Zigbee). If VM100 rescue fails entirely, the VM can be recreated with same config; only application-layer state (Zigbee pairings, HA automations state) is lost.

## Migration sprint-status implications

- **Story 1.3:** marked `done` for the 10 guests that succeeded. VM100 noted as hardware-blocked with pointer to this P1 doc.
- **Epic 2:** completed through Story 2.9. Story 2.10 was already deferred. Story 2.11 (48 h soak on the new NFS) can proceed.
- **Epic 3:** safe to proceed when operator is ready (doesn't touch pve1).
- **Epic 4 (workbench evacuation):** should be executed early — before further reads on pve1 risk CT150.
- **Epic 5:** hold until new pve1 NVMe is on hand.
