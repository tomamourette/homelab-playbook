# VM100 (smarthome) — ddrescue Salvage Runbook

**Why:** pve1 NVMe has bad sectors that caused VM100's PBS backup to fail at 52% / 16.8 GiB three times in a row (Story 1.3). VM100 is Zigbee-coordinator-pinned to pve1 and has no pre-migration backup. Before pve1 reinstall, attempt to salvage as much of the 32 GB disk as possible using `ddrescue`, which handles read errors gracefully.

**Best case:** 99% recovery, only the ~1 GB bad-sector region is lost, VM100 restores cleanly, Zigbee pairings preserved.
**Worst case:** bad region sits on top of the Zigbee DB, a few tens of devices need to be re-paired manually.

## When to run this

**Run BEFORE the pve1 reinstall, AFTER the operator workbench is cut over to pve3 (Epic 4 Option A).**

Reasoning: ddrescue will stress-read the failing drive for up to an hour. That could accelerate the drive's failure. If CT150 is still on pve1 when that happens, you lose your session. If CT150 is already on pve3 (CT250), you're insulated.

## Safety check before starting

```bash
# From pve3 or your laptop — NOT from anywhere on pve1
ssh root@192.168.50.156 'hostname'   # confirm pve3-hosted workbench is up
ssh root@192.168.50.201 'pct status 150 2>/dev/null; echo done'
# If you see pct 150 still running, cut over first.
```

## Prerequisites

- Fresh NFS export to pve3's hdd-pool (shared-nfs-bulk, already mounted on pve1 as /mnt/pve/shared-nfs-bulk) — this is where the image lands.
- Free space on hdd-pool: at least 40 GB (image up to 32 GB + map file + snapshots if needed). `hdd-pool/bulk` has ~79 TiB free, plenty.
- `ddrescue` (package: `gddrescue`) installed on pve1.

## Step-by-step

### 1. Install ddrescue on pve1

```bash
ssh root@192.168.50.201 'apt update && apt install -y gddrescue'
# If apt update fails (pve1 NVMe might be in trouble), try:
# apt -o Acquire::AllowInsecureRepositories=true install -y gddrescue
# Or copy the .deb from pve3 and dpkg -i
```

### 2. Create a dedicated folder for the rescue images

```bash
ssh root@192.168.50.203 'mkdir -p /hdd-pool/bulk/rescue && chmod 755 /hdd-pool/bulk/rescue'
# Verify from pve1 that the NFS mount sees it:
ssh root@192.168.50.201 'ls -la /mnt/pve/shared-nfs-bulk/rescue/'
```

### 3. Stop VM100 and deactivate the LV

```bash
ssh root@192.168.50.201 'qm stop 100'
# Wait a few seconds for clean shutdown, then:
ssh root@192.168.50.201 'qm status 100'   # should show 'stopped'

# Deactivate the LV so ddrescue has exclusive access
ssh root@192.168.50.201 'lvchange -an pve/vm-100-disk-1'
# -an = deactivate (opposite of -ay). If it says "in use", check for dangling qemu processes first.
```

### 4. First ddrescue pass (fast, non-destructive read)

This pass reads only good sectors and skips bad regions quickly. Gives you the bulk of the data in 10-15 min.

```bash
ssh root@192.168.50.201 'ddrescue \
  --force \
  --no-scrape \
  /dev/pve/vm-100-disk-1 \
  /mnt/pve/shared-nfs-bulk/rescue/vm100-disk1.img \
  /mnt/pve/shared-nfs-bulk/rescue/vm100-disk1.mapfile'
```

Flags:
- `--force`: overwrite existing image if rerun
- `--no-scrape`: skip intensive rereads of bad regions on pass 1
- The mapfile records what was read successfully — reruns pick up where they left off

**Expected output during run:**
```
rescued:       15.0 GiB,  tried:         0 B,  errsize:      0 B,  errors:         0
```

After ~15 min you should see ~31 GB rescued, ~1 GB errored. The exact numbers depend on how many sectors are affected.

### 5. Second pass (attempt to recover bad regions)

```bash
ssh root@192.168.50.201 'ddrescue \
  --force \
  --retry-passes=3 \
  /dev/pve/vm-100-disk-1 \
  /mnt/pve/shared-nfs-bulk/rescue/vm100-disk1.img \
  /mnt/pve/shared-nfs-bulk/rescue/vm100-disk1.mapfile'
```

`--retry-passes=3`: try each bad region up to 3 more times (drive might return good data on retry as heads reseat). Might recover 10-50% of the originally-bad region.

**If this makes pve1 unresponsive or temperature spikes, STOP:** ddrescue is stressing the drive. You have the pass-1 image which captures the bulk of the data. Use what you have.

### 6. (Optional) Try reverse-read pass

```bash
ssh root@192.168.50.201 'ddrescue \
  --force \
  --reverse \
  --retry-passes=1 \
  /dev/pve/vm-100-disk-1 \
  /mnt/pve/shared-nfs-bulk/rescue/vm100-disk1.img \
  /mnt/pve/shared-nfs-bulk/rescue/vm100-disk1.mapfile'
```

Reverse pass can sometimes recover sectors that forward-read refused. Optional — skip if drive is already stressed.

### 7. Verify the image

```bash
ssh root@192.168.50.203 'ls -la /hdd-pool/bulk/rescue/'
# Expect ~32 GB vm100-disk1.img plus a ~kB mapfile

# Check the mapfile for error rate:
ssh root@192.168.50.203 'tail -20 /hdd-pool/bulk/rescue/vm100-disk1.mapfile'
# Lines ending in '+' = good, '-' = failed. Count how many are '-' to estimate data loss.

# Optional: try to mount the image read-only and see what's recoverable:
ssh root@192.168.50.203 'modprobe nbd && qemu-nbd -c /dev/nbd0 -r /hdd-pool/bulk/rescue/vm100-disk1.img && \
  mkdir -p /mnt/vm100-salvage && \
  mount -o ro /dev/nbd0p1 /mnt/vm100-salvage && \
  ls /mnt/vm100-salvage'
# Unmount after inspection:
# umount /mnt/vm100-salvage && qemu-nbd -d /dev/nbd0
```

## Post-pve1-reinstall: restore VM100 from the rescue image

After the new NVMe is in and Proxmox reinstalled on pve1:

```bash
# Create a fresh VM 100 config matching the original
ssh root@192.168.50.201 'qm create 100 \
  --name smarthome \
  --memory 2048 \
  --cores 2 \
  --bios ovmf \
  --machine q35 \
  --cpu x86-64-v2-AES \
  --ostype l26 \
  --net0 virtio=06:15:27:AF:EB:5D,bridge=vmbr0 \
  --scsihw virtio-scsi-single \
  --efidisk0 local-zfs:1,efitype=4m'

# Import the rescue image as the VM's scsi0 disk
ssh root@192.168.50.201 'qm importdisk 100 /mnt/pve/shared-nfs-bulk/rescue/vm100-disk1.img local-zfs'
# Attach the imported disk
ssh root@192.168.50.201 'qm set 100 --scsi0 local-zfs:vm-100-disk-0,discard=on,iothread=1'
ssh root@192.168.50.201 'qm set 100 --boot order=scsi0'

# Re-attach USB Zigbee passthrough
ssh root@192.168.50.201 'qm set 100 --usb0 host=10c4:ea60'

# Start it
ssh root@192.168.50.201 'qm start 100'

# Watch console during boot:
ssh root@192.168.50.201 'qm terminal 100'
# Look for: filesystem errors (expected in the bad region), fsck offers, boot completion
```

## What to expect inside VM100 after restore

- **Filesystem check (fsck) will run** at first boot — the bad region likely intersects metadata or files, so fsck fixes or deletes corrupted entries
- **Home Assistant may lose some state:** device history, some automation state, sensor buffers
- **Zigbee2MQTT / ZHA pairing DB:** this is the important one — if the DB is intact, all 50+ devices re-pair automatically. If the DB corruption is severe, you'll need to re-pair devices (5-10 min each).
- **Bottom line:** likely 95%+ of VM100 boots and works, but be prepared to re-pair Zigbee devices.

## If ddrescue fails completely

If pve1 crashes or ddrescue returns with minimal recovery:

1. VM100 is functionally lost. Accept the data loss.
2. After pve1 reinstall, recreate VM100 from a fresh Debian + Home Assistant install.
3. Re-pair Zigbee devices manually.
4. You have VM100's .conf file in the pre-migration snapshot (Story 1.4) — gives you the exact CPU/memory/network settings to replicate.

## Cleanup after successful restore

Once VM100 is verified running post-reinstall and you've kept it up for a few days:

```bash
ssh root@192.168.50.203 'rm -rf /hdd-pool/bulk/rescue/'
# Reclaim ~32 GB. Don't rush — keep the image for at least a week in case you need to re-salvage anything.
```
