# Pre-Migration Backup Manifest

**Purpose:** Captures the pre-migration PBS backup sweep for the pve3 storage migration (Epic 1, Story 1.3). Serves as the authoritative restore reference for every cluster guest.

**Datastore:** `pbs-migration` → CT105 `ct-pbs-migration` (pve2, 192.168.50.155) → datastore `migration-window`
**Sweep date:** 2026-04-20
**Operator:** Story 1.3 (SM + Dev subagent)
**Cluster inventory at sweep time:** 11 guests across pve1/pve2/pve3 (verified via `pct list` and `qm list` on each node).

---

## Backup Sweep Results

| VMID | Name               | Node | Start (UTC)          | Duration | Size on wire (compressed) | Size on disk in PBS (deduped) | Status                  |
|------|--------------------|------|----------------------|----------|---------------------------|-------------------------------|-------------------------|
| 162  | ct-quant-trading   | pve3 | 2026-04-20T19:32:47Z | 00:00:50 | 2.51 GiB                  | 6.13 GiB raw (dedup applied)  | OK                      |
| 160  | ct-ai-01           | pve3 | 2026-04-20T19:33:38Z | 00:06:29 | 20.20 GiB                 | 35.22 GiB raw (dedup applied) | OK                      |
| 102  | ct-media-01        | pve1 | 2026-04-20T19:32:45Z | 00:31:17 | ~211 GiB                  | 212.1 GiB raw                 | OK                      |
| 100  | smarthome (VM)     | pve1 | 2026-04-20T20:04:03Z | 00:00:26 | — (partial)               | — (no backup written)         | **FAILED** (see notes)  |
| 103  | vm-haos-01 (VM)    | pve1 | 2026-04-20T20:04:30Z | 00:00:00 | 778 bytes (config-only)   | 778 bytes                     | OK (diskless VM)        |
| 101  | ct-docker-01       | pve1 | 2026-04-20T20:04:32Z | 00:03:10 | 6.85 GiB                  | 15.98 GiB raw (dedup applied) | OK                      |
| 151  | ct-sparkle-cps     | pve2 | 2026-04-20T19:32:46Z | 00:00:37 | 1.67 GiB                  | 3.97 GiB raw (dedup applied)  | OK                      |
| 153  | ct-isabelle        | pve2 | 2026-04-20T19:33:24Z | 00:00:37 | 1.64 GiB                  | 4.16 GiB raw (dedup applied)  | OK                      |
| 104  | ct-zeroclaw-01     | pve1 | 2026-04-20T20:08:32Z | 00:00:41 | 548 MiB                   | 1.47 GiB raw (dedup applied)  | OK                      |
| 150  | ct-dev-homelab     | pve1 | 2026-04-20T20:09:14Z | 00:03:03 | 4.26 GiB                  | 12.62 GiB raw (dedup applied) | OK                      |
| 152  | ct-dev-test        | pve2 | 2026-04-20T19:34:02Z | 00:01:00 | 6.42 MiB (incremental)    | 9.84 GiB raw (99.4% reused)   | OK                      |
| **Totals (successes)** | | | Sweep start: 2026-04-20T19:32:45Z, end: 2026-04-20T20:12:17Z (~40 min wall clock, 3 nodes in parallel) | | **~249 GiB wire** | **~191 GiB on PBS (pvesm: 37.11% of 491 GiB)** | **10 of 11 successful** |

### Notes column details

- **CT102 / ct-media-01 size:** reported as "processed 210.9 GiB in 31m" with no explicit "compressed" summary line because the final pxar summary was truncated in the log before "had to backup" — the full 210 GiB uploaded is both the raw and the near-wire footprint (highly varied media content compresses poorly). On-disk in PBS reflected as the 212 GiB raw after chunking.
- **VM103 / vm-haos-01:** VM config has no disks attached (`backup contains no disks`). Diskless config backup succeeded; disks for Home Assistant OS presumably live on external storage or are mounted at runtime.
- **CT152 / ct-dev-test:** this was a re-run of the Story 1.2 test. Second snapshot benefited from chunk dedup (99.4% reused), so wire was only 6.4 MiB even though the raw on-disk is still ~9.8 GiB.

## Failures

### VM100 / smarthome (pve1) — HARDWARE-RELATED

- **First attempt (snapshot mode):** failed at 52% of scsi0 with `ERROR: job failed with err -61 - No data available`
- **Retry (stop mode, VM cold-stopped):** failed at exact same offset (52%, ~16.9 GiB into 32 GiB scsi0)
- **Root cause identified:** `dmesg` on pve1 during retry shows:
  ```
  nvme0n1: I/O Cmd(0x2) @ LBA 224110720, 256 blocks, I/O Error (sct 0x2 / sc 0x81)
  critical medium error, dev nvme0n1, sector 224110720 op 0x0:(READ)
  ```
  Multiple critical medium errors on pve1's nvme0n1 starting at LBA 224110720, clustered. This is a developing NVMe hardware failure, not a snapshot/USB quirk. The VM100 scsi0 LV happens to have dirty-mapped regions intersecting those bad sectors.
- **Impact:** VM100 (smarthome / Home Assistant infra host with USB Zigbee dongle `usb0: host=10c4:ea60`) has NO pre-migration backup. Cannot safely destroy this VM pre-migration.
- **Risk escalation:** pve1's NVMe has physical bad sectors. This is a separate incident that must be handled before or alongside pve3 migration. Recommend raising a risk flag with the director.
- **Mitigation options for pve3 migration:**
  1. Migrate pve3 without VM100 touched; leave VM100 on pve1 as-is.
  2. Live-migrate VM100 to pve2 (which has 484 GiB free on pbs-migration-adjacent thin pool) by `qm migrate 100 pve2 --online --with-local-disks`, then back up the new location.
  3. Stop VM100, copy disk via `dd conv=noerror,sync` to capture non-bad regions, accept known-bad data in the 16.8 GiB region.

## Test Restore (CT152 → VMID 199)

- **Backup source:** `pbs-migration:backup/ct/152/2026-04-20T19:34:02Z` (the re-run from sweep, not the Story 1.2 original)
- **Restore command:**
  ```
  pct restore 199 pbs-migration:backup/ct/152/2026-04-20T19:34:02Z \
    --storage local-lvm --rootfs local-lvm:15 --hostname ct-restore-test
  ```
- **Restore start:** 2026-04-20T20:13:43Z
- **Restore end:** 2026-04-20T20:14:49Z
- **Restore duration:** 1 min 6 s (covers 9.84 GiB raw into a 15 GB local-lvm volume)
- **Start command:** `pct start 199`
- **Start timestamp:** 2026-04-20T20:14:55Z (approx., prior to verification poll)
- **Verification:**
  - `pct status 199` → `status: running`
  - `pct exec 199 -- uptime` → ` 20:15:05 up 0 min, 1 user, load average: 1.15, 0.83, 1.01` (confirms fresh boot, uptime < 1 min)
  - `pct exec 199 -- cat /etc/os-release` → `PRETTY_NAME="Debian GNU/Linux 12 (bookworm)"` (matches original CT152)
- **Destroy command:** `pct stop 199; pct destroy 199 --purge`
- **Destroy start:** 2026-04-20T20:15:10Z
- **Destroy end:** 2026-04-20T20:15:17Z
- **Destroy duration:** 7 s
- **Post-destroy check:** `pct list | grep 199` → no matches → VMID 199 cleanly removed
- **Result:** Restore verified end-to-end (PBS → pct restore → CT boots Debian → CT destroyed cleanly).

## Commands Used (for reproducibility)

```bash
# 1. Verify VMID 199 free
for n in pve1 pve2 pve3; do ssh $n "pct list | grep '^199\\b' || true; qm list | grep ' 199 ' || true"; done

# 2. Parallel per-node sweep (one script per node, three running concurrently)
# pve1 (in priority order for pve1 guests):
for id in 102 100 103 101 104 150; do
  ssh pve1 "vzdump $id --storage pbs-migration --mode snapshot \
    --notes-template 'pre-migration sweep {{node}} {{guestname}}'"
done
# pve2:
for id in 151 153 152; do
  ssh pve2 "vzdump $id --storage pbs-migration --mode snapshot \
    --notes-template 'pre-migration sweep {{node}} {{guestname}}'"
done
# pve3:
for id in 162 160; do
  ssh pve3 "vzdump $id --storage pbs-migration --mode snapshot \
    --notes-template 'pre-migration sweep {{node}} {{guestname}}'"
done

# 3. Verify backups exist
ssh pve2 "pvesm list pbs-migration"

# 4. Restore test
ssh pve2 "pct restore 199 pbs-migration:backup/ct/152/2026-04-20T19:34:02Z \
  --storage local-lvm --rootfs local-lvm:15 --hostname ct-restore-test"
ssh pve2 "pct start 199; sleep 10; pct status 199; pct exec 199 -- uptime"

# 5. Cleanup
ssh pve2 "pct stop 199; pct destroy 199 --purge"
```

## PBS Datastore Utilization (post-sweep)

- Total:    491 GiB (514,937,088 KiB)
- Used:     182.3 GiB (191,100,584 KiB) — 37.11%
- Free:     283.8 GiB (297,605,720 KiB)
- Change from pre-sweep (~4.5 GiB used, 0.87%) → +177.8 GiB net for 10 successful backups.

## Operator Log Files

- `/tmp/backup-sweep-1.3/pve1.log` — per-guest vzdump output for pve1 sweep (102, 100-fail, 103, 101, 104, 150)
- `/tmp/backup-sweep-1.3/pve2.log` — per-guest vzdump output for pve2 sweep (151, 153, 152)
- `/tmp/backup-sweep-1.3/pve3.log` — per-guest vzdump output for pve3 sweep (162, 160)
- `/tmp/backup-sweep-1.3/vm100-retry.log` — retry attempt for VM100 in stop mode (also failed; triggered dmesg inspection that revealed the NVMe medium errors)
- `/tmp/backup-sweep-1.3/restore.log` — pct restore transcript for CT152 → 199
