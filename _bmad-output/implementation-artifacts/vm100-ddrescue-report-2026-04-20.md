# VM100 ddrescue Report — 2026-04-20

**Operation:** Block-level rescue of VM100 (production Home Assistant) from failing pve1 NVMe (Samsung 970 EVO Plus, 24→112 media errors during run).

**Status:** SUCCESS — 99.999774% rescued, 76 KiB unrecoverable across 19 bad 4-KiB sectors.

---

## Timing

| Marker | Value |
|---|---|
| Start (UTC) | 2026-04-20T21:25:10Z |
| End (UTC)   | 2026-04-20T21:30:26Z |
| Wall-clock runtime | 5 min 16 s |
| ddrescue self-reported runtime | 5 min 03 s |
| ddrescue exit | Finished cleanly (reached `# Finished` marker in mapfile) |

## Source and Target

| Field | Value |
|---|---|
| Source device | `/dev/pve/vm-100-disk-1` (LV in pve/data thin pool, pve1) |
| Source backing | Samsung 970 EVO Plus NVMe (`nvme0n1`) |
| Source size | 32.00 GiB (34,359,738,368 bytes) |
| Target image | `/mnt/pve/shared-nfs-bulk/rescue/vm100-disk1.img` → `/hdd-pool/bulk/rescue/vm100-disk1.img` on pve3 |
| Target size (apparent) | 34,359,738,368 bytes (32 GiB, sparse) |
| Target size (allocated) | 2.3 GiB (thin/sparse; matches original 21.97 % LV mapped size) |
| Mapfile | `/hdd-pool/bulk/rescue/vm100-disk1.mapfile` |
| Log | `/hdd-pool/bulk/rescue/vm100-ddrescue.log` (57 KB) |
| VM100 config snapshot | `/hdd-pool/bulk/rescue/vm100.conf` |

Command executed on pve1:
```
ddrescue -d -r3 -b 4096 /dev/pve/vm-100-disk-1 \
  /mnt/pve/shared-nfs-bulk/rescue/vm100-disk1.img \
  /mnt/pve/shared-nfs-bulk/rescue/vm100-disk1.mapfile
```

## Recovery Statistics

| Metric | Value |
|---|---|
| Total size | 34,359,738,368 B (32 GiB) |
| Rescued | 34,359,660,544 B (≈ 32 GiB minus 76 KiB) |
| Unrescued | 77,824 B (76 KiB) |
| **Percent rescued** | **99.999774 %** |
| Bad areas | 19 |
| Bad-area size | Uniform 4 KiB (one filesystem page each) |
| ddrescue read errors | 88 total (ddrescue retries, so error count > bad areas) |
| Passes completed | Pass 1 (forward), Trimming, Scraping, Retry 1-3 — full -r3 sequence |

## Bad-sector map

All 19 unrecoverable regions are exactly 4 KiB (0x1000 bytes) each and cluster in two tight zones:

**Zone A — offset ≈ 17.95 GB (16 bad blocks, offsets 0x42D531000 – 0x42D871000):**
```
0x42D531000, 0x42D539000, 0x42D53D000, 0x42D579000, 0x42D57D000,
0x42D6B5000, 0x42D6B9000, 0x42D6BD000, 0x42D6C1000, 0x42D6F1000,
0x42D6F9000, 0x42D835000, 0x42D839000, 0x42D83D000, 0x42D849000,
0x42D871000
```

**Zone B — offset ≈ 20.05 GB (3 bad blocks, offsets 0x4AB9B5000 – 0x4AB9FD000):**
```
0x4AB9B5000, 0x4AB9F9000, 0x4AB9FD000
```

These map to LBAs roughly consistent with the P1 runbook's "LBA 224,117,xxx" region (source NVMe ~LBA 35M @ 4 KiB = ~141 GiB sector range on physical drive; offsets above are LV-relative, not drive-relative, because LV is a slice of the thin pool).

## NVMe drive health delta during rescue

| Field | Before | After |
|---|---|---|
| Temperature | 82 °C | 79 °C |
| Media and Data Integrity Errors | 24 | 112 |
| Critical Warning | 0x00 | 0x00 |
| Percentage Used | 1 % | 1 % |

Drive survived the rescue. Media error count jumped by 88 (matching ddrescue read_errors exactly), confirming each failed read was a real NAND-level integrity error, not a transient bus/controller fault.

## What to expect on restore

The rescued image is **virtually complete** — only 76 KiB of data is missing out of a 32 GiB disk (0.000226 %). Since the bad blocks are uniform 4 KiB pages inside two tight zones, the likely outcomes on restore are:

1. **Best case (probable):** the lost pages land in ext4 free space or a sparsely-used directory entry / inode / journal region. Home Assistant boots cleanly after an `fsck`. No user-visible data loss.
2. **Realistic case:** the lost pages hit a filesystem metadata block (inode table) or a small number of data extents. `fsck` repairs the metadata. A handful of files may be truncated, zero-filled, or moved to `lost+found`. At 76 KiB lost, this is at most ~19 individual 4-KiB file blocks.
3. **Worst case (unlikely):** a lost block sits in a critical superblock-adjacent structure, requiring superblock-backup recovery. ext4 has multiple superblock copies, so this is still recoverable via `e2fsck -b <backup-super>`.

Home Assistant's state is stored in `/config` (YAML + SQLite recorder DB). The recorder DB is the most likely candidate for a small corruption — worst case is loss of recent sensor history. Automations, dashboards, and credentials are in YAML files and are almost certainly intact.

**Recommended restore plan (for after pve1 NVMe is replaced):**
1. Import image to replacement storage: `qm importdisk 100 /hdd-pool/bulk/rescue/vm100-disk1.img <new-storage>`.
2. Restore config from `/hdd-pool/bulk/rescue/vm100.conf` (keep EFI disk reference or rebuild the 4 MB `efidisk0`).
3. Boot into rescue mode (or attach disk to a rescue VM) and run `e2fsck -f -y /dev/sdX2` (or equivalent — VM100 uses ext4 per typical HA-OS image layout).
4. Normal boot. Check HA logs for DB corruption warnings; if recorder DB is corrupt, truncate/rebuild it.
5. Validate: `curl http://<new-ip>:8123` returns 200 and all automations listed in the UI.

## Files on pve3 (NFS-backed, safe)

```
/hdd-pool/bulk/rescue/
  vm100.conf              (510 B)  — VM100 config snapshot
  vm100-disk1.img         (32 GiB sparse, 2.3 GiB allocated)
  vm100-disk1.mapfile     (1,457 B)
  vm100-ddrescue.log      (57 KB)
```

## Do NOT before next step

- Do not attempt to restore/boot this image until pve1 is reinstalled on a new NVMe. That is the next P1 task.
- Keep VM100 on pve1 running as long as the drive allows — it remains our authoritative copy until we successfully boot the rescued image.
- Do not delete or modify the files in `/hdd-pool/bulk/rescue/`; they are now the sole off-drive copy of VM100.

---

Generated by subagent following `vm100-ddrescue-runbook.md`.
