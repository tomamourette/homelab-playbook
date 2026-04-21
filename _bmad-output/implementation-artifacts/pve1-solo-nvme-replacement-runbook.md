# pve1-solo NVMe Replacement — Runbook

**Status:** Draft, 2026-04-21. Supersedes Path A (sequential) of `joint-pve1-pve2-nvme-replacement-runbook.md` for pve1; the pve2 half of the joint runbook will be executed separately once drive 2 arrives.

**Scope:** Replace pve1's failing Samsung 970 EVO Plus 500 GB NVMe with a Samsung 990 PRO 1 TB; reinstall Proxmox VE 9 onto a ZFS single-disk `rpool` matching the cluster-wide convention; evacuate → swap → rejoin → restore → validate.

---

## Preamble — why solo instead of joint

- **Hardware reality:** only **one** Samsung 990 PRO is on hand. pve2's replacement drive is still in transit (ETA TBD). Waiting is not acceptable because pve1's 970 EVO Plus is actively failing: 24 media errors (112 after the VM100 rescue), 82 °C, bad sectors clustered near LBA 224M. Each day of delay increases the risk of a hard failure that forces emergency recovery instead of a planned window.
- **Quorum advantage over joint execution:** running pve1 solo keeps pve2 AND pve3 up throughout. Quorum stays at 2/3 even while pve1 is powered down. There is never a window where pve3 is alone and read-only. The joint runbook's Path B parallel timing risk and its `pvecm expected 1` emergency-override procedure are not needed here.
- **Tradeoff:** two smaller windows (this one, plus a future pve2 window) instead of one ~3 h joint window. Operator wall-clock cost is higher; operational risk is lower. Given the cluster has never done a dual-node reinstall, the solo path is preferred regardless of whether drive 2 had arrived.
- **Research doc alignment:** this splits Epic 5 Window A (pve1) from Window B (pve2) per §4.5 per-CT placement matrix and NFR2 (quorum ≥2/3 at all times).

---

## Pre-flight checklist — must all pass before powering down pve1

- [ ] **pve1-preflight-report** shows go/no-go **green** (SMART delta captured, no new critical warning since ddrescue)
- [ ] **Final PBS sweep complete** — CT101, CT102, CT104, VM103 each have a fresh backup (timestamp within 2 h of start); verify with `proxmox-backup-client list --repository pbs-migration` or PBS UI
- [ ] **VM100 ddrescue image + mapfile + vm100.conf** present at `pve3:/hdd-pool/bulk/rescue/` (see `vm100-ddrescue-report-2026-04-20.md`)
- [ ] **CT150 evacuation to CT250 on pve3 is DONE** (Epic 4 soft cutover). Confirm: `ssh root@192.168.50.203 'pct status 250'` returns `running`; `ssh root@192.168.50.201 'pct status 150'` returns `stopped`. **Operator's active Claude/SSH session must be on CT250 (192.168.50.156), NOT on pve1 and NOT on the old CT150.**
- [ ] **Laptop SSH independent of CT150/CT250** verified: `ssh pve2 hostname` and `ssh pve3 hostname` from laptop succeed without going through any CT (Story 1.7 runbook). This is the escape hatch if CT250 is unreachable mid-swap.
- [ ] **Drive physically received and inspected** — Samsung 990 PRO 1 TB in hand, unopened box verified, serial number recorded in `homelab-playbook/_bmad-output/implementation-artifacts/cold-spare-inventory.md` (append row: date received, serial, model, assigned-to pve1)
- [ ] **M.2 thermal pad on hand** — 1 mm, ≥5 W/m·K, silicone or putty type. **NOT OPTIONAL.** The 970 EVO's 82 °C was the root cause of NAND wear; reusing the old, dried-out pad guarantees the new drive overheats too.
- [ ] **Proxmox VE 9 install USB prepared and tested** — same ISO used for pve3's rebuild (matches cluster version). Test-boot on a spare machine or confirm it boots to installer menu on pve1 by tapping F11 briefly before committing to the swap.
- [ ] **Small phillips screwdriver** for the CWWK case + M.2 retaining screw
- [ ] **~2 h clear of market hours** (US market closed) and **household Zigbee lull** (no one running automations that need HA right now; announce ~1 h Home Assistant outage)
- [ ] **Laptop charged / on power**, stable internet, this runbook visible in a second window

---

## Phase 1 — Evacuate pve1 guests (no physical work yet)

**Goal:** every pve1 guest is either already on pve2/pve3, or (for VM100) has its ddrescue image safely off pve1. At end of phase, `pct list` / `qm list` on pve1 shows only stopped templates.

### Placement matrix

| VMID | Guest | Current state | Target node | Mechanism | Post-swap destination | Notes |
|------|-------|---------------|-------------|-----------|------------------------|-------|
| 101 | ct-docker-01 | pve1 local-lvm, running | **pve3 local-zfs** | PBS restore | back to pve1 local-zfs | HA-candidate; restore fresh avoids any LVM-thin residue |
| 102 | ct-media-01 | pve1 local-lvm 240G, running | **pve3 local-zfs** | PBS restore | back to pve1 local-zfs | Keep mp0 → `shared-nfs-bulk` |
| 104 | ct-zeroclaw-01 | pve1 local-lvm 4G, running | **pve2 local-lvm** | PBS restore | back to pve1 local-zfs | Tiny, disposable |
| 103 | vm-haos-01 | pve1 local-lvm, running | **pve2 local-lvm** | PBS restore | back to pve1 local-zfs | ISO-only, trivial |
| 100 | VM smarthome (HA) | pve1 local-lvm **BAD NVMe** | **stays down** | ddrescue image (complete) | pve1 local-zfs (restore from image) | Zigbee USB `10c4:ea60` pins it to pve1 — cannot move |
| 150 | ct-dev-homelab | already on pve3 as CT250 | — (Epic 4 complete) | — | CT150 tombstone stays on pve1 until wipe | Operator uses CT250 throughout |
| 999, 9000 | templates | stopped | — | destroyed by pve1 wipe | recreated from terraform after rejoin | Templates, not data |

### Commands (copy-paste from laptop)

```bash
# === Pre-check from laptop ===
ssh root@192.168.50.201 'pvecm status | grep -E "Expected|Votes|Quorate"'   # 3, 3, Yes
ssh root@192.168.50.201 'pct list ; qm list'                                # inventory

# === 1.1 Stop all pve1 workloads (VM100 last — release USB cleanly) ===
ssh root@192.168.50.201 'for id in 101 102 104; do pct stop $id; done'
ssh root@192.168.50.201 'qm shutdown 103 --timeout 60'
ssh root@192.168.50.201 'qm shutdown 100 --timeout 120'                     # HA graceful stop
ssh root@192.168.50.201 'pct status 150 2>/dev/null || true'                # already stopped from Epic 4

# === 1.2 Final PBS sweep of the movable guests (skip VM100 — ddrescue is its backup) ===
ssh root@192.168.50.201 'for id in 101 102 104; do
  vzdump $id --storage pbs-migration --mode stop --notes-template "pre-pve1-swap-$(date +%F)"
done'
ssh root@192.168.50.201 'vzdump 103 --storage pbs-migration --mode stop --notes-template "pre-pve1-swap-$(date +%F)"'

# === 1.3 Restore CT101 to pve3 (local-zfs, HA-candidate) ===
# Find latest backup id
BACKUP_101=$(ssh root@192.168.50.203 'pvesm list pbs-migration' | awk '/ct\/101\//{print $1}' | tail -1)
ssh root@192.168.50.203 "pct restore 101 $BACKUP_101 --storage local-zfs --rootfs local-zfs:20"
ssh root@192.168.50.203 'pct start 101'
ssh root@192.168.50.203 'pct exec 101 -- hostname'                          # sanity

# === 1.4 Restore CT102 to pve3 and reattach shared-nfs-bulk ===
BACKUP_102=$(ssh root@192.168.50.203 'pvesm list pbs-migration' | awk '/ct\/102\//{print $1}' | tail -1)
ssh root@192.168.50.203 "pct restore 102 $BACKUP_102 --storage local-zfs --rootfs local-zfs:20"
# Verify mp0 points at shared-nfs-bulk; if not, fix:
ssh root@192.168.50.203 'grep mp0 /etc/pve/lxc/102.conf'
ssh root@192.168.50.203 'sed -i "s|/mnt/pve/shared-nfs/media|/mnt/pve/shared-nfs-bulk/media|" /etc/pve/lxc/102.conf'
ssh root@192.168.50.203 'pct start 102'
ssh root@192.168.50.203 'pct exec 102 -- ls /media/movies | head'           # media reachable

# === 1.5 Restore CT104 to pve2 (tiny) ===
BACKUP_104=$(ssh root@192.168.50.202 'pvesm list pbs-migration' | awk '/ct\/104\//{print $1}' | tail -1)
ssh root@192.168.50.202 "pct restore 104 $BACKUP_104 --storage local-lvm --rootfs local-lvm:4"
ssh root@192.168.50.202 'pct start 104'

# === 1.6 Restore VM103 to pve2 (trivial, iso-only) ===
BACKUP_103=$(ssh root@192.168.50.202 'pvesm list pbs-migration' | awk '/vm\/103\//{print $1}' | tail -1)
ssh root@192.168.50.202 "qmrestore $BACKUP_103 103 --storage local-lvm"
ssh root@192.168.50.202 'qm start 103'

# === 1.7 Verify VM100 ddrescue artifacts are safe on pve3 ===
ssh root@192.168.50.203 'ls -la /hdd-pool/bulk/rescue/'
# Must show: vm100-disk1.img (~32 GiB sparse), vm100-disk1.mapfile, vm100.conf, vm100-ddrescue.log

# === 1.8 Final sanity: pve1 has nothing running ===
ssh root@192.168.50.201 'pct list ; qm list'   # all stopped; CT150 stopped; templates stopped
```

**Exit criteria for Phase 1:**
- CT101, CT102 running on pve3 with `local-zfs` rootfs, CT102 serving media from `shared-nfs-bulk`
- CT104, VM103 running on pve2
- VM100 stopped on pve1 (drive is still readable); ddrescue image triple-confirmed on pve3
- `pvecm status` still shows 3/3 quorate
- Announce to household: "Home Assistant going down for ~1 h in 5 min"

---

## Phase 2 — Physical swap (operator at the rack, ~20 min)

```bash
# Final warning-window action: tell the household, silence the alerts
ssh root@192.168.50.201 'shutdown -h now'
# Wait ~30 sec for full power-off (fans stop, LED dark)
```

**Physical steps (at the CWWK CW-AD4L-N):**

1. Unplug power cable. Wait 10 sec.
2. Unscrew the CWWK case lid (4× small phillips, usually on the bottom).
3. Locate the M.2 slot holding the Samsung 970 EVO Plus. Note slot orientation and which side the heatsink pad is on.
4. Unscrew the M.2 retaining screw. Drive pops up at ~30°. Slide it out.
5. **Bag the old drive immediately in the anti-static bag.** Label it: `pve1-970EVO-500GB-FAILED-2026-04-21-RMA`. Record its serial next to the entry in cold-spare-inventory.md (it becomes the outgoing RMA item).
6. **Thermal pad swap:**
   - Peel the old pad off the heatsink (usually gummy; use plastic spudger or fingernail, NOT a screwdriver — don't scratch the heatsink).
   - Clean residue with 90%+ isopropyl alcohol on a lint-free cloth. Let dry.
   - Cut new 1 mm pad to match the heatsink footprint. Peel both release liners.
   - Apply to heatsink. Press lightly — do NOT compress fully yet, the NVMe does that.
7. Unbox the new Samsung 990 PRO. Inspect: no bent pins, serial matches the number already recorded.
8. Slide 990 PRO into the M.2 slot at ~30°, seat fully. Press flat. Re-install retaining screw (snug, not torqued — M.2 screws strip easily).
9. Confirm heatsink sits flush on the drive (pad compresses slightly).
10. Close case. Reinstall lid screws.
11. Reconnect power. Insert Proxmox 9 USB into a USB-A port.
12. Power on. Immediately tap F11 (or F7 depending on BIOS) for boot menu. Select the USB.

---

## Phase 3 — Proxmox 9 install (operator at console, ~15 min)

Installer walk-through, exact choices:

| Screen | Choice |
|--------|--------|
| Welcome | "Install Proxmox VE (Graphical)" |
| EULA | Accept |
| Target Harddisk | Click **Options** → **Filesystem: `zfs (RAID0)`**, **ashift: 12**, **compress: zstd**, **checksum: on**. Select only `nvme0n1` (the new 990 PRO, ~931 GiB). Pool name: **`rpool`** (default). |
| Location & Timezone | Country: Australia (or current), Timezone: `Australia/Melbourne` (same as pve2/pve3) |
| Root password | Same as pve2/pve3 (check password manager). Email: the same address used for pve2/pve3 root notifications. |
| Management Network | Interface: **`enp1s0`** (confirm with MAC — the one on the expected switch port). Hostname FQDN: **`pve1.home.arpa`** (match pve2/pve3 domain). IP: **`192.168.50.201/24`**, Gateway: **`192.168.50.1`**, DNS: **`192.168.50.1`**. |
| Summary | Verify all above. **DO NOT enable "Automatic reboot"** — leave it off so you can remove the USB. |
| Install | Runs ~5 min. Remove USB at "Install finished". Reboot. |

**Critical don'ts:**
- **DO NOT** create any additional pools, datasets, or storage at this stage. The install must be minimal — Proxmox defaults only. `fast-pool` concepts, special vdevs, etc. are all pve3 concerns; pve1 is single-disk ZFS only.
- **DO NOT** click "advanced networking" options. Plain DHCP-off static IP is what the cluster expects.
- **DO NOT** set a hostname other than `pve1` — `/etc/pve/` paths include the hostname and a mismatch will cause cluster rejoin grief.

After first boot, from laptop:

```bash
ssh root@192.168.50.201 'hostname && zpool status rpool && ip -4 addr show enp1s0'
# Expect:
#   pve1
#   rpool ONLINE, single-disk nvme0n1, 0 errors
#   192.168.50.201/24
```

---

## Phase 4 — Cluster rejoin (~10 min)

**Sequence matters here.** pve1's fresh install has no cluster knowledge, but pve3 still has an old `/etc/pve/nodes/pve1/` directory. Remove that stale entry BEFORE pve1 tries to join, or the join will fail with a config-clash error.

```bash
# === 4.1 From pve3 (healthiest node): remove the old pve1 entry ===
ssh root@192.168.50.203 'pvecm nodes'                                       # pve1 appears as offline
ssh root@192.168.50.203 'pvecm delnode pve1'                                # removes from cluster config
ssh root@192.168.50.203 'ls /etc/pve/nodes/'                                # should no longer list pve1
# If /etc/pve/nodes/pve1 still exists (stale), remove:
ssh root@192.168.50.203 'rm -rf /etc/pve/nodes/pve1 2>/dev/null || true'

# === 4.2 From pve1 (fresh install): join the cluster via pve3 ===
# Generate/accept SSH keys first so --use_ssh works cleanly:
ssh root@192.168.50.201 'ssh-keyscan -H 192.168.50.203 >> ~/.ssh/known_hosts 2>/dev/null'
ssh root@192.168.50.201 'pvecm add 192.168.50.203 --use_ssh'
# Prompts for pve3 root password. Join takes ~30 sec. Corosync restarts.

# === 4.3 Verify quorum from all three nodes ===
for n in 201 202 203; do
  echo "=== pve@192.168.50.$n ==="
  ssh root@192.168.50.$n 'pvecm status | grep -E "Expected|Votes|Quorate"'
done
# Expect all three to report: Expected votes 3, Total votes 3, Quorate Yes

# === 4.4 Verify storage.cfg synced down to pve1 ===
ssh root@192.168.50.201 'cat /etc/pve/storage.cfg'
# Must include: local-zfs (pointing to rpool/data), local (dir), pbs-migration, shared-nfs-bulk
```

**If pve1 fails to join:**
- Check `ssh root@192.168.50.203 'journalctl -u corosync -n 50'` for error hints
- Common cause: stale `/etc/pve/nodes/pve1` on pve2. Run `ssh root@192.168.50.202 'rm -rf /etc/pve/nodes/pve1'` then retry.
- If really stuck, `pvecm add` with `--force` on pve1 is last-resort.

---

## Phase 5 — Restore VM100 from ddrescue image (the special case)

VM100 is the only guest NOT restored from PBS — its disk is the 99.999774% rescued raw image. Home Assistant's Zigbee pairings and recorder DB are in that image; a PBS restore would revert to an older HA state and lose pairings.

```bash
# === 5.1 Mount shared-nfs-bulk on pve1 (storage.cfg should have synced this already) ===
ssh root@192.168.50.201 'pvesm status | grep shared-nfs-bulk'               # active
ssh root@192.168.50.201 'ls /mnt/pve/shared-nfs-bulk/rescue/'               # vm100-disk1.img visible

# === 5.2 Inspect the captured VM100 config ===
ssh root@192.168.50.201 'cat /mnt/pve/shared-nfs-bulk/rescue/vm100.conf'
# Note: storage reference is `local-lvm:vm-100-disk-1` in the old file;
#       we'll recreate on local-zfs as `local-zfs:vm-100-disk-0`.
# Also note: boot=order, efidisk0 reference, USB passthrough line (10c4:ea60).

# === 5.3 Create target zvol on rpool/data ===
ssh root@192.168.50.201 'zfs create -V 32G rpool/data/vm-100-disk-0'
ssh root@192.168.50.201 'ls -l /dev/zvol/rpool/data/vm-100-disk-0'           # block device exists

# === 5.4 Convert raw ddrescue image → zvol (writes byte-for-byte) ===
# Run from pve1 so the read comes over NFS once:
ssh root@192.168.50.201 'qemu-img convert -p -f raw -O raw \
  /mnt/pve/shared-nfs-bulk/rescue/vm100-disk1.img \
  /dev/zvol/rpool/data/vm-100-disk-0'
# Progress bar. ~5-10 min at 1 GbE. NO output = still running; don't interrupt.

# === 5.5 Create VM100 config ===
# Start from the captured vm100.conf, replace the disk storage reference, copy to /etc/pve/qemu-server/100.conf.
# Key substitutions:
#   scsi0: local-lvm:vm-100-disk-1,size=32G  →  scsi0: local-zfs:vm-100-disk-0,size=32G
#   efidisk0: local-lvm:vm-100-disk-0,...     →  efidisk0: local-zfs:vm-100-disk-1,size=4M,efitype=4m,pre-enrolled-keys=1
# (create the efidisk zvol too: zfs create -V 4M rpool/data/vm-100-disk-1)
ssh root@192.168.50.201 'zfs create -V 4M rpool/data/vm-100-disk-1'
ssh root@192.168.50.201 'cp /mnt/pve/shared-nfs-bulk/rescue/vm100.conf /etc/pve/qemu-server/100.conf'
ssh root@192.168.50.201 "sed -i 's|local-lvm:vm-100-disk-1,size=32G|local-zfs:vm-100-disk-0,size=32G|' /etc/pve/qemu-server/100.conf"
ssh root@192.168.50.201 "sed -i 's|local-lvm:vm-100-disk-0|local-zfs:vm-100-disk-1|' /etc/pve/qemu-server/100.conf"
ssh root@192.168.50.201 'cat /etc/pve/qemu-server/100.conf'                 # eyeball check

# === 5.6 Re-attach USB passthrough for Zigbee ===
# Verify USB device still visible on pve1:
ssh root@192.168.50.201 'lsusb | grep 10c4:ea60'                             # Silicon Labs CP210x
# If config doesn't have usb0 line, add it:
ssh root@192.168.50.201 'grep -q "^usb0:" /etc/pve/qemu-server/100.conf || echo "usb0: host=10c4:ea60,usb3=0" >> /etc/pve/qemu-server/100.conf'

# === 5.7 Start VM100 ===
ssh root@192.168.50.201 'qm start 100'
ssh root@192.168.50.201 'qm status 100'                                      # running
# VM console (noVNC via Proxmox GUI) or watch `qm terminal 100` if HAOS has serial.
# Expect first boot to fsck ext4 (fixes any metadata hits from the 76 KiB lost zones).

# === 5.8 Validate Home Assistant ===
# Give HA 2-3 min to start recorder + zigbee2mqtt/ZHA:
sleep 180
curl -sS -o /dev/null -w "%{http_code}\n" http://192.168.50.86:8123           # expect 200
# Browser check: dashboard loads; check Settings → Devices → Zigbee coordinator status
# HA logs: ssh/console into VM100, `journalctl -u home-assistant -f` — watch for
#   "recorder: database integrity ok" (good) or
#   "recorder: CRITICAL: database is corrupt" (bad — triage with sqlite3 .recover)
```

**If the recorder DB is corrupt** (realistic given 76 KiB of lost bytes):
- Worst case: lose last ~days of sensor history. Automations + credentials unaffected.
- Fix: stop HA, `sqlite3 home-assistant_v2.db ".recover" > recovered.sql`, rebuild DB, restart HA.
- If Zigbee coordinator won't pair: worst case is re-pair 30 devices by hand over ~1 h. Still cheaper than losing everything.

---

## Phase 6 — Restore the other guests to pve1

Now that pve1 is a full cluster member with `local-zfs`, pull the evacuated guests home.

```bash
# === 6.1 Live-migrate CT101 pve3 → pve1 ===
ssh root@192.168.50.203 'pct migrate 101 pve1 --target-storage local-zfs --online'
# With both nodes on ZFS, `pct migrate --online` uses zfs send for the disk delta; fast.

# === 6.2 Live-migrate CT102 pve3 → pve1 ===
ssh root@192.168.50.203 'pct migrate 102 pve1 --target-storage local-zfs --online'
# Verify mp0 still points at shared-nfs-bulk after migrate:
ssh root@192.168.50.201 'grep mp0 /etc/pve/lxc/102.conf'
ssh root@192.168.50.201 'pct exec 102 -- ls /media/movies | head'

# === 6.3 Migrate CT104 pve2 → pve1 ===
# pve2 is still local-lvm (awaiting its own swap). Offline migration required.
ssh root@192.168.50.202 'pct stop 104 && pct migrate 104 pve1 --target-storage local-zfs'
ssh root@192.168.50.201 'pct start 104'

# === 6.4 Migrate VM103 pve2 → pve1 ===
ssh root@192.168.50.202 'qm stop 103 && qm migrate 103 pve1 --targetstorage local-zfs'
ssh root@192.168.50.201 'qm start 103'

# === 6.5 CT150 stays on pve3 as CT250 ===
# Operator decides later whether to renumber/relocate (Epic 4 follow-up).
# CT150 tombstone on old pve1 is gone (wiped with the drive). No action needed.
```

---

## Phase 7 — Terraform tfvars update (Story 5.6 equivalent)

Reflect the new storage topology so future `terraform apply` doesn't try to recreate guests on the now-nonexistent `local-lvm`.

```bash
# On CT250 (operator workbench on pve3), where the terraform state lives
ssh developer@192.168.50.156
cd /home/developer/workspace/homelab/homelab-infra/terraform/envs/homelab

# Edit main.tf (or terraform.tfvars, depending on where storage_id lives) —
# for every resource targeting pve1, change:
#   storage_id = "local-lvm"   →   storage_id = "local-zfs"
# Affected resources (per §4.5 matrix): CT101, CT102, CT104, CT150 (if still defined), VM103, VMID 999 template.

# Plan should show zero changes (state already matches post-restore reality):
terraform plan
# Expected: "No changes. Your infrastructure matches the configuration."

# If drift exists (e.g. terraform thinks a CT is on local-lvm but it's actually on local-zfs now),
# use `terraform state rm` + `terraform import` for the affected resource, OR
# accept a targeted `terraform apply -target=... -refresh-only` to reconcile.

# Commit + push the tfvars/main.tf change
git add envs/homelab/main.tf
git commit -m "chore(tf): pve1 storage_id local-lvm → local-zfs post-NVMe-swap"
git push origin main
```

**DO NOT commit:** any `.tfstate` file, any `.env`, or the VM100 conf snapshot (too close to a credential-bearing file — archive it separately).

---

## Phase 8 — Validation

All must pass before declaring the window closed.

```bash
# === 8.1 ZFS health on pve1 ===
ssh root@192.168.50.201 'zpool status rpool'
# Expect: state ONLINE, scan: none requested, 0 errors across read/write/cksum

# === 8.2 Cluster quorum ===
ssh root@192.168.50.203 'pvecm status | grep -E "Expected|Votes|Quorate"'
# Expected votes 3, Total votes 3, Quorate Yes

# === 8.3 All pve1-resident guests running ===
ssh root@192.168.50.201 'pct list'     # 101, 102, 104 running
ssh root@192.168.50.201 'qm list'      # 100, 103 running

# === 8.4 Service reachability ===
curl -sS -o /dev/null -w "HA:%{http_code}\n" http://192.168.50.86:8123                 # 200
ssh root@192.168.50.201 'pct exec 101 -- systemctl is-active docker'                    # active
ssh root@192.168.50.201 'pct exec 102 -- ls /media/movies | head -3'                    # titles
ssh root@192.168.50.201 'pct exec 104 -- hostname'                                       # ct-zeroclaw-01

# === 8.5 Zigbee DB survived (proves ddrescue preserved device pairings) ===
# In HA UI: Settings → Devices & Services → Zigbee coordinator → Devices list
# Expect: ~30 previously-paired devices listed with "last_seen" timestamps from today
# If list is empty, the 76 KiB hit the Zigbee network table — re-pair manually.

# === 8.6 PBS still reachable from pve1 ===
ssh root@192.168.50.201 'pvesm status | grep pbs-migration'                              # active

# === 8.7 Record post-swap snapshot ===
ssh root@192.168.50.201 'mkdir -p /tmp/post-swap-$(date +%F) && cd /tmp/post-swap-$(date +%F) && \
  zpool status > zpool.txt && zfs list > zfs.txt && pct list > pct.txt && qm list > qm.txt && \
  cp /etc/pve/storage.cfg storage.cfg && pvecm status > pvecm.txt'
# Copy to operator workbench for commit alongside this runbook:
scp -r root@192.168.50.201:/tmp/post-swap-$(date +%F) developer@192.168.50.156:/home/developer/workspace/homelab/homelab-playbook/_bmad-output/implementation-artifacts/
```

---

## Post-swap follow-ups

- [ ] **RMA the old NVMe via Samsung warranty.** Include: failure date (2026-04-21), media-error count (112), SMART log snippet, photo of the bad-sector pattern. Pack in the anti-static bag + original 990 PRO box. Record RMA case number back in `cold-spare-inventory.md`.
- [ ] **Log the session** in `docs/retrospectives/pve1-nvme-swap-2026-04-21.md` (what took longer than planned, what went cleanly, any surprises). Do this within 24 h while memory is fresh.
- [ ] **Defer pve2 swap until drive 2 arrives.** Split Epic 5 Window B (pve2 reinstall) off into its own runbook when ETA is known. This runbook's patterns are directly reusable; mostly swap hostnames and IPs, and revise evacuation mechanics (no VM100 equivalent).
- [ ] **Epic 6 (replication + HA) remains blocked** until pve2 is also on ZFS. That is the next hard gate.

---

## Rollback

| If failure hits in... | Rollback path |
|------------------------|---------------|
| **Phase 1** (evacuation) | Revert: no physical damage yet. Abort; re-enable pve1 guests from PBS if they were mid-restore; re-plan once pve1 stabilizes. The old drive is still reading. |
| **Phase 2** (physical swap) | If the new 990 PRO won't detect: re-seat pad + drive. If still broken and old drive still functions, reinstall old drive, power on, cluster resumes with pve1 guests on their evacuation targets. Contact Samsung for RMA on the new drive. |
| **Phase 3** (Proxmox install) | Installer failure is easy: re-boot, re-run installer. No data loss. If the drive itself seems sick, swap back to old drive (still readable) — temporary reprieve — and plan a replacement drive. |
| **Phase 4** (cluster rejoin) | Rejoin errors are config-level, not hardware. Worst case: `pvecm delnode pve1` on pve2 AND pve3, then retry with `--force` on pve1. If truly wedged, leave pve1 out — the cluster runs fine at 2/3 with pve2+pve3. Guests stay on their evacuation nodes. |
| **Phase 5** (VM100 restore) | If HA refuses to boot or Zigbee table is lost: last resort = restore VM100 from PBS (older state but functional), then re-pair ~30 Zigbee devices by hand over ~1 h. Not ideal but tractable. HA config templates are in `/home/developer/workspace/homelab/` — not on the failing drive. |
| **Phase 6** (guest restores to pve1) | Non-destructive: if a migration fails, the guest remains running on its evacuation node. Try offline migration. Last resort: PBS restore fresh to pve1. |
| **Phase 7** (Terraform) | Zero-impact on running guests. If `terraform plan` shows unexpected drift, commit nothing; investigate with `terraform state list` and `terraform import`. |
| **Phase 8** (validation) | If a check fails, triage the specific item. None of these are rollback-triggering; they are operational issues to fix in-place. |

---

## Variable / parameter reference

### Nodes & IPs

| Node | IP | Role during window | Post-swap storage |
|------|----|--------------------|-------------------|
| pve1 | 192.168.50.201 | **subject of swap** | rpool (ZFS single-disk, new 990 PRO 1 TB) |
| pve2 | 192.168.50.202 | evacuation host (CT104, VM103) | local-lvm (unchanged; own swap pending) |
| pve3 | 192.168.50.203 | evacuation host (CT101, CT102), cluster pivot | rpool + hdd-pool + fast-pool (Epic 3 complete) |

### Storage IDs

| ID | Type | Node(s) | Purpose |
|----|------|---------|---------|
| `local-lvm` | LVM-thin | pve2 (still) | legacy; pve1's old local-lvm is wiped by reinstall |
| `local-zfs` | ZFS pool rpool/data | pve1 (new), pve3 | HA-replicable root disks |
| `local` | dir | all three | templates, ISOs |
| `pbs-migration` | pbs | all three | migration-window backups (CT on pve2) |
| `shared-nfs-bulk` | nfs | exported by pve3 | media library; CT102 consumer |
| `hdd-pool` | zfs | pve3 only | bulk storage (not pve1-relevant) |
| `fast-pool` | zfs | pve3 only | ephemeral (not pve1-relevant) |

### VMID placement (pre-swap → post-swap)

| VMID | Name | Pre-swap node | During swap | Post-swap node |
|------|------|---------------|-------------|-----------------|
| 100 | VM smarthome (HA) | pve1 (bad NVMe) | **down** (ddrescue on pve3) | pve1 (restored from image) |
| 101 | ct-docker-01 | pve1 | pve3 (local-zfs) | pve1 (local-zfs) |
| 102 | ct-media-01 | pve1 | pve3 (local-zfs, mp0→shared-nfs-bulk) | pve1 (local-zfs, mp0→shared-nfs-bulk) |
| 103 | vm-haos-01 | pve1 | pve2 (local-lvm) | pve1 (local-zfs) |
| 104 | ct-zeroclaw-01 | pve1 | pve2 (local-lvm) | pve1 (local-zfs) |
| 150 | ct-dev-homelab | pve1 (tombstone) | pve1 stopped; CT250 on pve3 runs | wiped with pve1; CT250 stays on pve3 |
| 250 | ct-dev-homelab (relocated) | pve3 (operator session) | pve3 (operator session) | pve3 |
| 999 | ubuntu-dev-template | pve1 | wiped | recreated via Terraform if needed |
| 9000 | ubuntu-22.04-cloudimg | pve1 | wiped | recreated via Terraform if needed |

### Hardware identifiers

| Item | Value |
|------|-------|
| Old NVMe model | Samsung 970 EVO Plus 500 GB |
| Old NVMe status | 24→112 media errors, 82°C peak, bad sectors near LBA 224M — RMA candidate |
| New NVMe model | Samsung 990 PRO 1 TB |
| New NVMe serial | _(record on receipt; paste into cold-spare-inventory.md)_ |
| USB Zigbee (VM100) | `10c4:ea60` (Silicon Labs CP210x UART bridge) |
| M.2 thermal pad spec | 1 mm thickness, ≥5 W/m·K, silicone or putty type |
| Proxmox VE version | 9.x (matches pve2, pve3) |

### Key files & paths

| Path | What |
|------|------|
| `pve3:/hdd-pool/bulk/rescue/vm100-disk1.img` | ddrescue image (sole VM100 source) |
| `pve3:/hdd-pool/bulk/rescue/vm100-disk1.mapfile` | ddrescue mapfile (for any retry) |
| `pve3:/hdd-pool/bulk/rescue/vm100.conf` | captured VM100 config pre-swap |
| `pve3:/hdd-pool/bulk/rescue/vm100-ddrescue.log` | rescue log |
| `pve1:/etc/pve/qemu-server/100.conf` | rebuilt VM100 config (post-Phase 5) |
| `pve1:/dev/zvol/rpool/data/vm-100-disk-0` | VM100 rootfs zvol (32 GiB) |
| `pve1:/dev/zvol/rpool/data/vm-100-disk-1` | VM100 EFI zvol (4 MiB) |
| `homelab-infra/terraform/envs/homelab/main.tf` | tfvars to update in Phase 7 |
| `homelab-playbook/_bmad-output/implementation-artifacts/cold-spare-inventory.md` | drive serials log |

---

*Generated 2026-04-21 as the pve1-only split of `joint-pve1-pve2-nvme-replacement-runbook.md`. Do not commit until Director review.*
