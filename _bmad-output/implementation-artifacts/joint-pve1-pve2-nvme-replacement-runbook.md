# Joint pve1 + pve2 NVMe Replacement — Runbook

**Context:** Two Samsung 990 PRO 1 TB NVMes ordered to replace pve1 (failing 970 EVO Plus) and pve2 (WD SN770). ETA: 2026-04-21. Migration plan originally did pve1 and pve2 reinstalls in separate windows (Epic 5 Phase 6 then Phase 7); with hardware arriving together, we can combine but must handle cluster quorum carefully.

## The quorum problem (read this first)

Proxmox cluster needs **2 of 3 votes quorate** to operate (cluster transactions, HA decisions, storage.cfg edits). Today: all 3 nodes up = 3 votes quorate.

| Scenario | pve1 | pve2 | pve3 | Votes | Quorate? | Impact |
|----------|------|------|------|-------|----------|--------|
| Normal | ✅ | ✅ | ✅ | 3 | Yes | All ops work |
| pve1 down only | ❌ | ✅ | ✅ | 2 | Yes | Quorum OK; CTs on pve2/pve3 fine |
| pve2 down only | ✅ | ❌ | ✅ | 2 | Yes | Quorum OK; CTs on pve1/pve3 fine |
| **pve1 AND pve2 down** | ❌ | ❌ | ✅ | 1 | **NO** | **pve3 read-only, can't start/stop/migrate** |

**The danger:** if you reinstall pve1 and pve2 at the same time, pve3 goes into "no quorum" mode. **Running CTs/VMs keep running** but you can't:
- Start or stop any guest
- Edit storage.cfg or any /etc/pve/ file
- Use HA manager (doesn't matter — nothing HA yet)
- Add new nodes back (needs quorum to accept them!)

**If you push it too far and pve3 also has a problem while pve1+pve2 are down**, the cluster can wedge. Recovery involves `pvecm expected 1` overrides, which is doable but stressful.

## Two paths to choose from

### Path A — Sequential (recommended: safer)

Reinstall one node at a time, let it rejoin, verify quorum, then do the next.

**Timeline (per node: ~60–90 min each):**
```
T+0:00   Evacuate pve1 → reinstall pve1 → rejoin cluster → restore CTs
T+1:30   Verify quorum 3/3
T+1:30   Evacuate pve2 → reinstall pve2 → rejoin cluster → restore CTs
T+3:00   Verify quorum 3/3
T+3:00   Proceed to Epic 6 replication
```

**Pro:** quorum never drops below 2. Zero risk of cluster-level wedge.
**Con:** 2× the wall-clock time.

### Path B — Parallel (faster, medium-risk)

Reinstall both nodes simultaneously. Accept a ~60–90 min window where pve3 has no quorum. Verify pve3 CTs are all running BEFORE starting.

**Timeline:**
```
T+0:00   Pre-check: pve3 quorate alone via 'pvecm expected 1' standby-ready.
         Verify no pve3 operations are pending (no running vzdump, no replications).
T+0:05   Stop pve1; swap NVMe; boot installer
T+0:10   Stop pve2; swap NVMe; boot installer
T+0:40   Both install + first boot complete
T+1:00   pve1 rejoins, quorum restored (2/3)
T+1:20   pve2 rejoins, quorum 3/3
T+1:30   Restore pve1 CTs from PBS
T+2:30   Restore pve2 CTs from PBS
T+3:00   Done
```

**Pro:** saves ~90 min. Both nodes done in one focused session.
**Con:** pve3 read-only for ~60 min. If pve3 hits an issue during that window, recovery requires manual quorum-override.

**Emergency override if pve3 needs a transaction while pve1+pve2 are down:**
```bash
ssh pve3 'pvecm expected 1'   # temporarily allow pve3 to operate alone
# do what you need
# when pve1 or pve2 comes back, normal quorum resumes automatically
```

### My recommendation

**Go sequential (Path A)** the first time. You've never done a dual-node reinstall on this cluster; picking the safer path means if something weird happens with one node, the other is still healthy to diagnose from. The 90 min savings of parallel isn't worth the quorum-recovery skill tax.

If you ever do this again (second hardware refresh cycle 3-5 years out), go parallel — you'll know the pattern.

## Prerequisites (before you start EITHER path)

- [ ] Drives in hand: 2× Samsung 990 PRO 1 TB, unboxed
- [ ] M.2 thermal pads on hand (1 mm, ≥5 W/m·K) — 2 strips for the 2 new drives
- [ ] Proxmox VE 9 installer USB (same ISO as pve3's install)
- [ ] Laptop with SSH access to pve1/pve2/pve3 verified (Story 1.7 — if not done, DO IT before starting)
- [ ] Physical access to both CWWK CW-AD4L-N mini-PCs
- [ ] Small phillips screwdriver for M.2 slot screws
- [ ] **Operator workbench already evacuated to pve3 (CT250 / 192.168.50.156)** — do Option A in `ct150-evacuation-cutover-runbook.md` first
- [ ] ddrescue VM100 image captured (see `vm100-ddrescue-runbook.md`) — optional but recommended if you want any chance of preserving Zigbee pairings

## Path A — Sequential reinstall, step-by-step

### Phase 1: pve1 reinstall (~90 min)

```bash
# === PRE-CHECK (from your laptop) ===
ssh root@192.168.50.201 'pvecm status'           # should say Quorate, 3 votes
ssh root@192.168.50.201 'pct list && qm list'     # inventory of pve1 guests

# === STEP 1.1: EVACUATE pve1 ===
# PBS backups already exist for all pve1 guests (Story 1.3) except VM100
# which we'll handle via ddrescue. Stop everything on pve1:
ssh root@192.168.50.201 'for id in 101 102 104; do pct stop $id; done'
ssh root@192.168.50.201 'for id in 100 103; do qm shutdown $id --timeout 60; done'
# CT150 is already stopped if you completed the Epic 4 cutover; if not, stop it now too:
ssh root@192.168.50.201 'pct stop 150 2>/dev/null || true'

# === STEP 1.2: FINAL SANITY CHECK ===
ssh root@192.168.50.201 'pct list ; qm list'     # all should show "stopped"
# Verify PBS is reachable from pve2 and pve3 (where we'll restore):
ssh root@192.168.50.202 'pvesm status | grep pbs-migration'   # should be active

# === STEP 1.3: PHYSICAL SWAP ===
# Shutdown pve1
ssh root@192.168.50.201 'shutdown -h now'
# Wait for it to fully power off (~30s). Physically:
# 1. Disconnect power
# 2. Open the CWWK case
# 3. Remove old NVMe from M.2 slot
# 4. Check thermal pad on heatsink — if pad is pitted/dried, replace with fresh 1mm pad
# 5. Insert new Samsung 990 PRO
# 6. Secure with screw, close case, reconnect power

# === STEP 1.4: INSTALL PROXMOX ===
# Boot from Proxmox 9 installer USB
# Filesystem: ZFS (RAID0) on the single new NVMe
# Pool name: rpool (MUST match pve3 naming for future replication)
# Compression: default (on)
# Hostname: pve1
# IP: 192.168.50.201/24, gw 192.168.50.1, DNS 192.168.50.1
# Root password: (use your standard homelab password)
# Storage: select the new Samsung 990 PRO, use full disk, ashift=12 (default for NVMe)

# === STEP 1.5: FIRST BOOT + CLUSTER REJOIN ===
ssh root@192.168.50.201 'hostname && zpool status rpool'   # verify ZFS healthy
# Join cluster from pve1:
ssh root@192.168.50.201 'pvecm add 192.168.50.203 --use_ssh 1'
# (uses pve3 as the join target — pve3 has ZFS and is the most stable)

# Verify from another node:
ssh root@192.168.50.203 'pvecm status'   # should show 3 nodes, 3 votes, Quorate

# === STEP 1.6: RESTORE pve1 CTs/VMs FROM PBS ===
# (on pve1 now — after SSH sees pve1 back up)
ssh root@192.168.50.201 'for ID in 101 102 103 104; do
  BACKUP=$(pvesm list pbs-migration | grep "ct/$ID/\|vm/$ID/" | tail -1 | awk "{print \$1}")
  if [ -z "$BACKUP" ]; then echo "no backup for $ID — skipping"; continue; fi
  echo "restoring $ID from $BACKUP"
  case $ID in
    101|102|104) pct restore $ID $BACKUP --storage local-zfs --rootfs local-zfs:20 ;;
    103)         qmrestore $BACKUP $ID --storage local-zfs ;;
  esac
done'

# VM100 (smarthome) special case — restore from ddrescue image, not PBS
# (see vm100-ddrescue-runbook.md for the restore part)

# === STEP 1.7: UPDATE CT102 shared-nfs-bulk MOUNT ===
# After restore, ct-media-01's mp0 should still reference shared-nfs-bulk
# but verify:
ssh root@192.168.50.201 'grep mp0 /etc/pve/lxc/102.conf'
# Should show: mp0: /mnt/pve/shared-nfs-bulk/media,...
# If it reverted to /mnt/pve/shared-nfs/media, fix:
ssh root@192.168.50.201 'sed -i "s|/mnt/pve/shared-nfs/media|/mnt/pve/shared-nfs-bulk/media|" /etc/pve/lxc/102.conf'

# === STEP 1.8: START pve1 CTs/VMs ===
ssh root@192.168.50.201 'for id in 101 102 104; do pct start $id; done'
ssh root@192.168.50.201 'for id in 103; do qm start $id; done'
# VM100 after its ddrescue restore
```

Verify quorum before proceeding:
```bash
ssh root@192.168.50.203 'pvecm status | grep -E "Expected|Votes|Quorate"'
# Expected votes: 3, Quorate: Yes
```

### Phase 2: pve2 reinstall (~90 min)

Identical pattern:

```bash
# === PRE-CHECK ===
# Verify pve1 is fully healthy:
ssh root@192.168.50.201 'pct list ; qm list'
ssh root@192.168.50.201 'pvecm status'

# === STEP 2.1: EVACUATE pve2 ===
# IMPORTANT: CT105 (pbs-migration) is on pve2 and currently holds all our backups.
# Before stopping it, decide:
#   Option 2A: leave PBS running on pve2 during reinstall — NOT POSSIBLE, pve2 goes offline
#   Option 2B: migrate CT105 to pve3 first (its mountpoint is on pve2 local-lvm — won't move easily)
#   Option 2C: accept PBS unavailable during pve2 reinstall (~90 min). If you need to restore
#              a pve2 guest that just got reinstalled, you CAN'T while pve2 is being rebuilt
#              — but that's a non-issue because pve2 has no HA-critical workload now.

# Go with Option 2C — simplest:
ssh root@192.168.50.202 'pct stop 105 151 152 153'

# === STEP 2.2: PHYSICAL SWAP (same as 1.3) ===
ssh root@192.168.50.202 'shutdown -h now'
# ... swap NVMe with fresh thermal pad ...

# === STEP 2.3: INSTALL PROXMOX (same as 1.4) ===
# Filesystem: ZFS (RAID0), pool name rpool, hostname pve2, IP 192.168.50.202

# === STEP 2.4: REJOIN CLUSTER ===
ssh root@192.168.50.202 'pvecm add 192.168.50.203 --use_ssh 1'
ssh root@192.168.50.203 'pvecm status'   # 3 nodes, 3 votes

# === STEP 2.5: RESTORE pve2 GUESTS FROM PBS ===
# CT105 migration-window PBS: restore it so backups work again
# CT151, CT153: restore (CT152 can be recreated via Terraform)
ssh root@192.168.50.202 'for ID in 151 153; do
  BACKUP=$(pvesm list pbs-migration | grep "ct/$ID/" | tail -1 | awk "{print \$1}")
  pct restore $ID $BACKUP --storage local-zfs --rootfs local-zfs:20
done'

# Wait — pbs-migration won't be available because CT105 is gone with pve2 reinstall.
# ALTERNATIVE: restore CT105 from its pre-reinstall config BEFORE restoring others.
# This needs: pre-reinstall PBS-of-PBS backup (take this BEFORE stopping pve2!)

# === SIMPLER: take a dump of all pve2 CTs to a file on pve3 BEFORE pve2 stop ===
# See prep section below.

# === STEP 2.6: RECREATE CT105 PBS FROM pve2 PRE-BACKUP DUMP ===
# (See "Pre-reinstall prep" section below for the dump strategy.)

# === STEP 2.7: TERRAFORM RECREATE CT152 ===
ssh root@192.168.50.150 'cd /home/developer/workspace/homelab/homelab-infra/terraform/envs/homelab && terraform apply'
```

### Phase 3: Post-reinstall cluster validation

```bash
ssh root@192.168.50.203 'pvecm status'   # 3/3 quorate
ssh root@192.168.50.203 'pct list ; qm list'   # on each node, verify guests
for n in pve1 pve2 pve3; do
  ssh root@$n 'zpool status rpool | head -5'
done
# All should show ONLINE, 0 errors
```

## Pre-reinstall prep — avoiding the PBS-on-pve2 bootstrap problem

The migration-window PBS (CT105) lives on pve2. If we reinstall pve2 and lose PBS, we can't restore pve2's own guests.

**The fix: before stopping pve2 for reinstall, dump its CTs to pve3 as vzdump files (not PBS).**

```bash
# Create a target dir on pve3 (outside NFS, just local)
ssh root@192.168.50.203 'mkdir -p /hdd-pool/pve2-reinstall-dumps'

# Dump each pve2 guest to that dir (plain vzdump, not PBS)
ssh root@192.168.50.202 'for id in 105 151 152 153; do
  vzdump $id --storage local --dumpdir /mnt/pve3-dumps --mode snapshot --compress zstd
done'

# If "local" storage is not cross-node-reachable, use an intermediate:
# Mount pve3 via SSHFS or use scp after dumping locally:
ssh root@192.168.50.202 'for id in 105 151 152 153; do
  vzdump $id --storage local --mode snapshot --compress zstd
done'
# Then copy the dumps to pve3:
ssh root@192.168.50.202 'ls /var/lib/vz/dump/*.tar.zst' | \
  xargs -I{} scp pve2:{} pve3:/hdd-pool/pve2-reinstall-dumps/
```

**Restore order after pve2 reinstall:**
```bash
# 1. Pull CT105 dump from pve3 and restore on pve2 first
scp pve3:/hdd-pool/pve2-reinstall-dumps/vzdump-lxc-105-*.tar.zst pve2:/var/lib/vz/dump/
ssh pve2 'pct restore 105 /var/lib/vz/dump/vzdump-lxc-105-*.tar.zst --storage local-zfs --rootfs local-zfs:8 --mp0 local-zfs:500,mp=/var/lib/proxmox-backup'
ssh pve2 'pct start 105'
# Wait for PBS to come up. Verify datastore imports cleanly.

# 2. Now pbs-migration is back — restore CT151, CT153 from PBS as in Step 2.5.
```

## What the operator needs to do

In order:

1. [ ] **Confirm Story 1.7** (SSH from laptop to pve1/2/3) works — without this, recovery from a midnight failure is very painful
2. [ ] **Cut over operator workbench** (Epic 4 / ct150-evacuation-cutover-runbook.md Option A) — 30 sec
3. [ ] **Replace M.2 thermal pads** on both pve1 and pve2 during the physical swap
4. [ ] **Pre-reinstall dump** of pve2 CTs to pve3 (see section above) — prevents PBS bootstrap chicken-and-egg
5. [ ] **ddrescue VM100** before starting pve1 reinstall (see vm100-ddrescue-runbook.md)
6. [ ] **Run Path A sequentially** — pve1 first, verify, then pve2
7. [ ] **Start Epic 6** (replication + HA) once both nodes are on ZFS

## If something goes wrong

- **One node reinstall fails halfway, cluster has 2/3 votes but one is broken:** stop, don't reinstall the second node. Recover the broken one first. Quorum is fine with 2 healthy.
- **Both nodes die mid-reinstall:** pve3 goes read-only. Use `pvecm expected 1` on pve3 to allow it to operate alone while you fix pve1 or pve2.
- **New NVMe DOA:** rare but happens. You have the failing-but-still-reading original pve1 NVMe — pop it back in, boot, you're back where you started. For pve2: you haven't stopped anything yet, just don't.
- **PBS datastore can't be restored on pve2:** use the vzdump files on `/hdd-pool/pve2-reinstall-dumps/` — they're cluster-agnostic.

## When all is done

Commit this runbook's "executed" state:
- Update `sprint-status-pve3-storage-migration.yaml`: epic-5 stories 5.1–5.12 → `done`
- Take a fresh post-reinstall state snapshot (Story 1.4 pattern, as `post-migration-snapshot-YYYY-MM-DD/`)
- Proceed to Epic 6 (replication + HA).
