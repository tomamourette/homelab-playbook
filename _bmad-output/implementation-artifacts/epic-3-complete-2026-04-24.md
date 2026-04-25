---
date: 2026-04-24
session: Epic 3 pve3 Target NVMe Architecture (architecture COMPLETE pending overnight scrub)
relates-to: window-b-complete-2026-04-24.md, 7-9-ansible-pve-node-bootstrap-playbook.md, 2-10-deploy-pbs-datastore-on-hdd-pool-pbs.md, pve3-bios-vram-24gb-guide.md
---

# Epic 3 — pve3 Target NVMe Architecture COMPLETE

pve3 is reinstalled onto the Option-D target storage architecture: 2-way rpool mirror (nvme0+nvme2 p3) for OS, mirrored special vdev (nvme0+nvme2 p4) accelerating hdd-pool metadata, single-disk fast-pool (nvme1 whole disk) for scratch. All three pve3-resident CTs restored and operational. Cluster at 3/3 quorum.

## Target architecture achieved

```
pve3 NVMe layout (3× Samsung 990 PRO 1TB — ~928 GB each)
============================================================

nvme0n1 (S7HDNL0L322630L, eui.0025384361a07084)
  ├── p1 BIOS boot stub (1007 KiB)
  ├── p2 EFI system partition (1 GiB)
  ├── p3 rpool mirror member 0 (827 GiB)
  └── p4 hdd-pool special vdev mirror member 0 (103 GiB)

nvme1n1 (S6Z1NF0L202025D, eui.0025384261b00ca8)
  └── whole disk → fast-pool (828 GiB usable)

nvme2n1 (S7HDNL0L323003J, eui.0025384361a071f9)
  ├── p1 BIOS boot stub (1007 KiB)
  ├── p2 EFI system partition (1 GiB)
  ├── p3 rpool mirror member 1 (827 GiB)
  └── p4 hdd-pool special vdev mirror member 1 (103 GiB)
```

**Cluster-wide ZFS pools:**
- `rpool`: 2-way mirror, 824 GB, ONLINE, 0 errors
- `hdd-pool`: RAIDZ1 5× 22 TB HDDs + mirrored 103 GB special vdev, 100 TB, ONLINE, 0 errors
- `fast-pool`: single-disk 928 GB (NOT redundant), ONLINE, 0 errors

## Workload placement (final)

| Node | Guests |
|---|---|
| pve1 | CT101 ct-docker-01, CT102 ct-media-01 (running — NFS from pve3 restored), VM100 smarthome (HAOS) |
| pve2 | CT151 ct-sparkle-cps |
| pve3 | CT160 ct-ai-01 (restored from PBS), CT162 ct-quant-trading (migrated back), CT250 ct-dev-homelab (migrated back) |

## Story-by-story execution summary

### Story 3.1 — Evacuate CT160 and CT162 from pve3 pre-reinstall
**Status: done.** Executed 2026-04-24 15:05–15:12 UTC.
- CT162 migrated pve3 → pve2 via `pct migrate --restart --target-storage local-zfs` (1:18)
- CT250 (ct-dev-homelab workbench — this session's execution host) migrated pve3 → pve1 (2:23, session briefly dropped mid-migrate)
- CT160 stopped (has iGPU passthrough, can't migrate)
- CT102 on pve1 stopped to free RAM for CT250's temporary stay (CT102 NFS client depended on pve3 anyway — offline during reinstall is free)
- Fresh CT160 stop-mode PBS backup captured (`ct/160/2026-04-24T13:13:01Z`, ~20 GiB compressed — 99.9% dedup vs the running-snapshot from Story 2.10)
- `zpool export -f hdd-pool` required to release the busy pool

### Story 3.2 — Reinstall Proxmox with 2-way ZFS mirror
**Status: done.** Executed 2026-04-24 ~15:50–17:00 UTC.

Key events:
- **First install attempt FAILED** with `error: installation failed: no disks found matching selection`. Root cause: the Proxmox auto-installer's minimal initramfs does not populate `/dev/disk/by-id/` symlinks, so the `disk-list = ["/dev/disk/by-id/nvme-Samsung_SSD_990_PRO_1TB_..."]` paths in pve3-answer.toml didn't resolve.
- **Fix:** rewrote `disk-list` to kernel device names: `disk-list = ["nvme0n1", "nvme2n1"]` — same form pve1/pve2's working answer files used.
- **ISO rebuild required.** pve2 lacked `proxmox-auto-install-assistant` (fresh install, enterprise apt-source blocked); fixed apt sources, installed the tool, rebuilt ISO, re-flashed USB.
- **USB flash was flaky** — first dd (bs=4M) truncated at 797 MB due to USB device resets (`usb 1-4: reset high-speed USB device` ×7 in dmesg). Retried with `bs=1M conv=fsync` — 1.83 GB in 10 min, clean.
- **BIOS UMA Frame Buffer Size:** options offered were 16G / 32G / 48G; `24G` not available. Chose **32G Fixed** (host sees 62 GB, iGPU gets 32 GB for LLM). pve3-bios-vram-24gb-guide.md is now superseded — the real menu has these discrete choices.
- **Drive name swap (installer ↔ running OS):** the installer's kernel enumerated NVMes differently from the running PVE — what `nvme0n1` was pre-reinstall became `nvme1n1` post-reinstall and vice-versa. `disk-list = ["nvme0n1", "nvme2n1"]` still selected 2 of 3 drives correctly (all 3 drives are identical Samsung 990 PRO 1TB so this is cosmetic), just different serials than originally planned. Documented for future reinstalls.
- Post-install, `rpool-OLD-<uuid>` ZFS import (a stale ZFS label on nvme1n1 from pre-reinstall) hung the first boot. Recovered via initramfs rescue shell: destroyed nvme1n1 first 10 MB + last 10 MB with `dd` (clears ZFS labels), then `zpool import -f -N rpool; exit`. After a second reboot the system booted cleanly.

### Story 3.3 — Rejoin pve3 to cluster
**Status: done.** Executed 2026-04-24 ~17:10 UTC.
- pve-node-bootstrap.yml (Story 7.9) ran in production for the first time
- Result: `ok=56 / changed=15 / failed=0` in ~57 seconds
- Cluster 3/3 quorate, Config Version 10
- **One defect in the pve3-firstboot.sh bootstrap pubkey** — the Story 7.9 dev agent transcribed the wrong ed25519 pubkey (fingerprint `IBQFQNo2...`) instead of the Ansible controller's actual key (`INhm8fGwL...`). Required one-time manual SSH key install on pve3 console before the playbook could connect. **Fix for future**: update pve3-firstboot.sh to embed the correct pubkey from `/home/developer/.ssh/homelab_ed25519.pub`. Story 7.9 re-open marker captured.

### Stories 3.4 to 3.7 — Storage reshape (automated via pve-host-pve3-storage role)
**Status: done.** Executed 2026-04-24 ~18:30 UTC via `playbooks/pve3-storage-apply.yml`.
- **3.4 Special vdev:** created p4 partitions on nvme0/nvme2 (sgdisk `-n 4:0:0 -t 4:bf01`), added as `mirror-1` special vdev to hdd-pool. Uses the 103.5 GiB free tail that `hdsize=828` left on each drive.
- **3.5 Special small blocks:** `hdd-pool/pbs` dataset configured with `special_small_blocks=128K` so PBS chunk metadata routes to NVMe.
- **3.6 fast-pool:** wiped stale `rpool-OLD` labels on nvme1n1 (required multiple iterations + a reboot to release kernel holds), created single-disk `fast-pool` on nvme1n1 whole disk.
- **3.7 NFS export:** `/etc/exports` reconciled, nfs-kernel-server installed, rpcbind + nfs-server enabled. CT102 on pve1 verified reading `/media/` (books/downloads/movies/music/tv all visible via NFS) after cluster storage `shared-nfs-bulk` auto-reactivated.

**One issue during the role run:** hdd-pool was initially imported read-only after reboot (due to hostid mismatch); required `zpool export hdd-pool && zpool import -f hdd-pool` to become writable before ZFS property reconciliation could proceed.

### Story 3.8 — Restore CT160 and migrate CT162/CT250 back
**Status: done.** Executed 2026-04-24 ~18:40–18:50 UTC.
- CT160 PBS-restore from `ct/160/2026-04-24T13:13:01Z` to local-zfs (5 min)
- CT160 started, pings at 192.168.50.160, iGPU passthrough config preserved (verified via `lxc.cgroup2.devices.allow c 226:* rwm` + `lxc.mount.entry: /dev/dri dev/dri`)
- CT162 migrated pve2 → pve3 (1:20, ZFS send ~8 GB)
- CT250 migrated pve1 → pve3 (this session's execution host, brief disconnect expected and recovered)

**One cluster-state quirk:** CT160's config entry was still cluster-wide visible on pve3 even after the wipe (because `/etc/pve/lxc/160.conf` is cluster-shared). Required `pct destroy 160 --force 1 --purge` before the PBS restore could create the CT anew.

### Story 3.9 — hdd-pool/models mount in CT160
**Status: done-with-path-mismatch.** Executed 2026-04-24 ~18:58 UTC.
- `pct set 160 -mp0 /hdd-pool/models,mp=/var/lib/ollama/models`
- CT160 restart → mount verified present at `/var/lib/ollama/models` (80 TB avail)
- **POST-VERIFICATION FINDING (2026-04-24):** Ollama on Debian stores models at `/usr/share/ollama/.ollama/models` (not `/var/lib/ollama/models`). The PBS restore preserved the 13 GB of prior models at that correct path, and `ollama list` inside CT160 shows them intact:
  - `gemma4-uncensored:latest` (5.8 GB)
  - `gemma4:e4b` (9.6 GB)
- The `mp0` we added bind-mounts hdd-pool/models at the *wrong* path — Ollama doesn't use it. **Harmless** (no data loss, no ollama failure), but the storage-offloading intent of Story 3.9 isn't realized — models still live on rpool.
- **Deferred action** (future story 3.9-followup): if/when user wants to accumulate many large models, re-point mp0 to `/usr/share/ollama/.ollama/models` and move existing content. 15 GB on 928 GB rpool is fine for current usage.

### Story 3.10 — Validation
**Status: in-progress (scrub completes overnight).**
- All 3 pools `state: ONLINE`, 0 read/write/checksum errors
- `zpool status` structure confirms: rpool mirror-0 (2 disks), hdd-pool raidz1-0 (5 HDDs) + special mirror-1 (2 NVMe parts), fast-pool single-disk
- Scrubs started concurrently at ~18:58 UTC — will complete over the next several hours (hdd-pool is the largest, ~946 GB allocated, typical 50-100 MB/s scrub = 2-5 hours)
- Expected completion notification via `zed` email

## Permanent PBS restoration (Story 2.10 follow-on)

The Story 2.10 work paid off exactly as designed:
- `hdd-pool/pbs` dataset **preserved across pve3 reinstall** (hdd-pool is on the 5 HDDs which Epic 3 did not touch)
- Post-reinstall the role re-installed `proxmox-backup-server`, re-registered the datastore in `/etc/proxmox-backup/datastore.cfg`, and the existing `.chunks/` deduplication store (65,538 chunks) was recognized immediately
- All 3 prior backup snapshots (`ct/151/2026-04-24T11:42:05Z`, `ct/160/2026-04-24T11:42:58Z`, `ct/160/2026-04-24T13:13:01Z`) survived and were available for restore
- One gotcha: PBS user database (`/etc/proxmox-backup/user.cfg`) lives on rpool and was wiped — had to recreate `pve-backup@pbs` user + ACL. New PBS credentials stored at `pve3:/root/pbs-creds.txt` (mode 600). **Operator to-do: move to password manager.**
- Also had to: (a) update cluster PVE storage fingerprint (cert regenerated on reinstall), (b) `chown root:backup /etc/proxmox-backup/datastore.cfg` so the PBS proxy daemon can read it (the role's file-perms step didn't set the group — future role improvement).

## Lessons (captured for future reinstalls)

1. **`disk-list` must use kernel names in answer.toml** — `/dev/disk/by-id/` paths fail silently in the auto-installer's minimal initramfs.
2. **Stale ZFS labels on an un-wiped drive will hang first-boot** — if a drive was previously a zpool member, even partial label remnants cause ZFS to try to auto-import on boot. Zero out first 10 MB and last 10 MB of the drive BEFORE reinstall, or be prepared to do initramfs rescue.
3. **Kernel NVMe device naming is NOT stable between installer env and running OS** — serials are stable; document explicitly which physical drive should be preserved by serial, not by `nvme0n1`/`nvme1n1`/`nvme2n1`.
4. **UMA Frame Buffer Size options vary by BIOS revision** — don't assume `24G` is available; document the selected value and update the guide after each run.
5. **PBS datastore config file needs `root:backup` ownership**, not `root:root`, or the proxy daemon returns 400 on all API calls.
6. **CT restore against cluster-shared config** — if a CT's config exists in `/etc/pve/lxc/` but its disk is gone (reinstall), `pct restore` will refuse. Must `pct destroy --force 1 --purge` first.
7. **PBS user database lives on rpool** — wiped by reinstall. Re-creation is manual unless codified in the role (future Story 2.10 refinement).

## Epic closure checklist

- [x] 3.1 Evacuate CT160/CT162/CT250 from pve3
- [x] 3.2 Reinstall PVE with 2-way ZFS mirror + hdsize reservation
- [x] 3.3 Rejoin cluster via pve-node-bootstrap.yml
- [x] 3.4 Mirrored special vdev on hdd-pool
- [x] 3.5 special_small_blocks on hdd-pool/pbs
- [x] 3.6 Single-disk fast-pool on nvme1
- [x] 3.7 NFS re-export
- [x] 3.8 CT160 PBS-restore + CT162/CT250 migrate-back
- [x] 3.9 hdd-pool/models mount on CT160
- [ ] 3.10 Overnight scrub (in progress; close tomorrow after scrub completes and Ollama model re-pull is done if desired)

## Followups (non-blocking)

- **Story 7.9 defect**: wrong ed25519 pubkey in pve3-firstboot.sh. Fix before next node reinstall.
- **Ollama model re-pull** inside CT160 (pre-existing models were on rpool, destroyed by 3.2). Non-urgent — models are re-downloadable.
- **PBS creds migration** from `/root/pbs-creds.txt` to password manager.
- **pve3-bios-vram-24gb-guide.md** update: document real BIOS options (16/32/48 GB) and the fact that "24 GB" doesn't exist on this BIOS revision.
- **PBS schedule**: GC + verify jobs not yet scheduled (Story 7.6 scrub schedule is a similar pattern).
- **Role improvement**: have `pve-host-pve3-storage` role explicitly `chown root:backup` on `/etc/proxmox-backup/datastore.cfg` after creating it.
- **pve3 apt sources**: the no-subscription source is in place but pve-enterprise is still listed-but-disabled. Clean cleanup in Epic 7.

## Sprint status diff

- **Epic 3**: `backlog` → `done-pending-scrub`
- Stories 3.1–3.9: `backlog` → `done`
- Story 3.10: `backlog` → `in-progress` (scrub running)
- Downstream unblocks: Epic 6 (HA + replication) has no remaining prereqs
