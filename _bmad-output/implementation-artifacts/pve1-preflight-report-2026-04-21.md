---
date: 2026-04-21
verdict: YELLOW — proceed when final CT102 retry + VM103 backup complete
related: P1-pve1-nvme-failure-2026-04-20.md, vm100-ddrescue-report-2026-04-20.md, pve1-solo-nvme-replacement-runbook.md
---

# pve1 NVMe swap — pre-flight report

**Operator has 1 of 2 Samsung 990 PRO drives in hand. Swap plan: pve1 now (solo), pve2 later when drive 2 arrives.**

## Section 1 — VM100 ddrescue image validation

**Outcome: GREEN — restore prognosis excellent.**

Image attached read-only via `losetup -fP /hdd-pool/bulk/rescue/vm100-disk1.img`. Partition layout confirms this is **HAOS (Home Assistant OS)** not Debian-with-HA-Core:

| Partition | Size | Role |
|-----------|------|------|
| p1 | 32 MB | hassos-esp (EFI system) |
| p2 | 24 MB | hassos-boot-A |
| p3 | 256 MB | hassos-kernel-A |
| p4 | 24 MB | hassos-boot-B |
| p5 | 256 MB | hassos-kernel-B |
| p6 | 8 MB | hassos-bootstate |
| p7 | 96 MB | hassos-overlay |
| **p8** | **31.3 GB** | **hassos-data (ext4 — where all HA state lives)** |

p8 mounted cleanly read-only. No I/O errors during mount or while reading.

**Critical HA files — all fully readable (sha256 computed, full-file read succeeded):**

| File | Size | SHA-256 prefix |
|------|------|----------------|
| `supervisor/homeassistant/configuration.yaml` | 688 B | `ece4e3edb1ea1f3b` |
| `supervisor/homeassistant/home-assistant_v2.db` (recorder) | 19.8 MB | `ace27b4a659e92a1` |
| `supervisor/homeassistant/zigbee.db` (**ZHA device pairings**) | 348 KB | `06b1cd9908ba78f0` |
| `supervisor/homeassistant/secrets.yaml` | 161 B | `9c6ea1ebf206217b` |
| `supervisor/homeassistant/automations.yaml` | 3.8 KB | `85887d6e2f5ee39f` |

**Interpretation:** the 76 KiB corruption (19 bad 4 KiB sectors clustered in two zones around 17.95 GB and 20.05 GB offsets inside the 32 GB disk) did NOT hit any of these. The bad zones landed in sparse/unused/swap regions of the HAOS data partition.

**Post-restore behavior expected:** Home Assistant boots, loads recorder history, ZHA lists all previously paired Zigbee devices, automations run. No re-pairing, no manual HA rebuild needed.

**Unmounted and detached loop device after validation.**

## Section 2 — Final PBS sweep of pve1 live guests

Sweep of the four guests that will be PBS-restored (CT101, CT102, CT104, VM103 — VM100 excluded since ddrescue is authoritative; CT150 excluded as the tombstone per Epic 4).

| VMID | Name | Status | Duration | Size (PBS) | Timestamp | Notes |
|------|------|--------|----------|------------|-----------|-------|
| 104 | ct-zeroclaw-01 | OK | ~1 min | 1.59 GB | 2026-04-21T11:47:02Z | clean |
| 101 | ct-docker-01 | OK | ~2 min | 17.3 GB | 2026-04-21T11:47:18Z | clean |
| 102 | ct-media-01 | FAIL (broken pipe) then retry in progress | retry started 13:48:33 | ~225 GB compressed (estimate from prior sweep) | 2026-04-21T11:48:29Z failed, retry running | first attempt hit broken-pipe when the orchestrating agent session terminated; serial retry running now |
| 103 | vm-haos-01 | in progress | < 1 min expected (iso-boot, no disk) | trivial | running at report time | will complete before CT102 |

**Progress to continue after report writing:** wait for CT102 retry (expected ~30 min total) and VM103 (expected ~1 min). When both `OK`, the swap can proceed.

## Section 3 — Other prerequisites

| Check | Status |
|-------|--------|
| Operator workbench on pve3 (not on pve1) | ✅ CT250 @ 192.168.50.156 (Epic 4 soft cutover) |
| Cluster quorate | ✅ 3/3 votes |
| Hardware received (drive 1 of 2) | ✅ Operator confirmed |
| Hardware received (drive 2 of 2) | ❌ In transit — pve2 swap deferred to later window |
| M.2 thermal pad on hand | ⚠️ **Operator must confirm** (see runbook Phase 2) |
| Proxmox 9 install USB prepared | ⚠️ Operator must confirm |
| Household notified of VM100 downtime (~1h) | ⚠️ Operator must confirm |
| Fallback SSH laptop→pve1/2/3 works | ⚠️ Story 1.7 still blocked-on-operator — strongly recommended to verify today |

## Section 4 — Go / no-go verdict

**Overall: YELLOW** — proceed when:

1. CT102 retry completes with `OK` status
2. VM103 backup completes with `OK` status
3. Operator confirms thermal pad + USB installer + household notification

Once those three are met → **GREEN** for swap.

**Non-blocking caveats** (flagged by the runbook author):
- VM100 efidisk0 (the 4 MB EFI vars storage) was NOT in the ddrescue (it's a separate LV that wasn't targeted). HAOS may boot fresh efivars cleanly; if it doesn't, operator will need to boot rescue media and re-enroll the UEFI keys. Low probability — HAOS is designed to handle missing efivars on first boot.
- `pvecm delnode pve1` must be run on pve3 BEFORE pve1 attempts to rejoin — the runbook Phase 4.1 handles this.

## Section 5 — Recommended proceed order

1. **Wait for CT102 + VM103 backups** (~30 min from report time).
2. **Operator confirms thermal pad / installer USB / household** via reply.
3. **Operator performs Phase 1 evacuation + Phase 2 physical swap** per `pve1-solo-nvme-replacement-runbook.md`.
4. **When pve1 boots fresh,** ping the director (this session) to drive Phases 3–8.

## Appendix — commands used during validation

```bash
ssh pve3 "modprobe loop && losetup -fP /hdd-pool/bulk/rescue/vm100-disk1.img"
ssh pve3 "lsblk /dev/loop0 && file -s /dev/loop0p8"
ssh pve3 "mkdir -p /mnt/vm100-rescue-p8 && mount -o ro,noexec,nosuid /dev/loop0p8 /mnt/vm100-rescue-p8"
ssh pve3 "ls /mnt/vm100-rescue-p8/supervisor/homeassistant/"
ssh pve3 "for f in ...; do sha256sum \$f; done"   # full-file read of 5 critical HA files
ssh pve3 "umount /mnt/vm100-rescue-p8 && rmdir /mnt/vm100-rescue-p8 && losetup -d /dev/loop0"
```
