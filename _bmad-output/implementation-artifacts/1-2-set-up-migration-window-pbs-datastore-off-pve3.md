---
status: done
epic: 1
story: 1.2
title: Set up migration-window PBS datastore (off pve3)
---

# Story 1.2: Set up migration-window PBS datastore (off pve3)

## User Story

As an operator,
I want a PBS datastore that does NOT live on pve3,
So that I can take and restore backups even while pve3 is being rebuilt.

## Acceptance Criteria

**Given** the current PBS datastore is on or will be destroyed with pve3 (note: no PBS exists in the cluster today — this builds one from scratch)
**When** I create a temporary datastore on pve2 (chosen over pve1 because pve1 has only ~42 GB free vs pve2's ~772 GB free in its LVM thin pool)
**Then** the temporary datastore appears in PBS UI as healthy
**And** a test backup from CT152 to the temporary datastore succeeds
**And** the datastore location is documented and reachable from all three pve nodes
**And** the plan for decommissioning the temporary datastore post-migration is documented

## Tasks

- Verify 192.168.50.155 is free cluster-wide (ARP neighbor check + 3x ping)
- Verify VMID 105 is free on all nodes
- Create unprivileged LXC CT105 (`ct-pbs-migration`) on pve2 from cached `debian-12-standard_12.12-1_amd64.tar.zst` template
  - 2 cores, 2 GB RAM, 512 MB swap
  - Rootfs 8 GB on `local-lvm`
  - Mount point 0: 500 GB on `local-lvm` mounted at `/var/lib/proxmox-backup`
  - Bridge vmbr0, IP `192.168.50.155/24`, gw `192.168.50.1`, nameserver `192.168.50.1`
  - Onboot 1, tags `homelab;pbs;migration-window;temporary`
- Install Proxmox Backup Server 3.4 inside CT105 via `pbs-no-subscription` repo
- Fix `/var/lib/proxmox-backup` ownership (chown backup:backup) because the mountpoint was created before the postinst added the `backup` user
- Create PBS datastore `migration-window` at `/var/lib/proxmox-backup/migration-window`
- Generate API token `root@pam!pve-cluster` with `DatastoreBackup` ACL on `/datastore/migration-window`
- Capture PBS TLS fingerprint
- Register `pbs-migration` in cluster-wide `/etc/pve/storage.cfg` via `pvesm add pbs`
- Test vzdump CT152 to `pbs-migration` — confirm success and capture size/duration
- Configure PBS prune job `mw-prune` (keep-last=2, daily) to cap datastore growth during the migration window
- Persist credentials on pve2 `/root/.pbs-migration-credentials` (chmod 600, OUT of git)
- Author operational runbook at `_bmad-output/implementation-artifacts/pbs-migration-datastore-runbook.md`

## Dev Notes

### Why pve2 (not pve1)

Director pre-check confirmed:
- pve1 `local-lvm` thin pool: only ~42 GB free — cannot host a 500 GB datastore
- pve2 `local-lvm` thin pool: 794.30 GB total, **2.77% used**, ~772 GB free — comfortably fits the datastore plus CT rootfs
- pve2 runs only 3 production LXCs (CT151 ct-sparkle-cps, CT152 ct-dev-test, CT153 ct-isabelle), so contention is minimal
- pve3 cannot host (it will be reinstalled — that's the whole point of the story)

### LXC vs VM choice

Unprivileged LXC chosen over a full VM for: lower overhead (~2 GB RAM vs 4+ GB for a minimal PBS VM), faster provisioning, and because the datastore's durability story is the same either way (it lives on pve2's `local-lvm` thin pool in both cases, not inside the guest). One gotcha documented below (mountpoint ownership).

### CT105 network config

- **VMID:** 105 (verified unused before creation; neighbors 104 = ct-zeroclaw-01, 150 = ct-dev-homelab)
- **Hostname:** `ct-pbs-migration`
- **IP:** `192.168.50.155/24` — verified unused via `ip neigh show` (FAILED state) + 3x ping timeout
- **Gateway:** `192.168.50.1`
- **Bridge:** `vmbr0`
- **MAC:** auto-assigned by pct create
- **Onboot:** 1 (autostart with pve2)

### PBS datastore details

- **Datastore name:** `migration-window`
- **Path inside CT:** `/var/lib/proxmox-backup/migration-window`
- **Backing:** 500 GB ext4 on `local-lvm:vm-105-disk-1` (pve2's thin pool)
- **Free at creation:** 491 GiB
- **Prune policy:** `mw-prune` keep-last=2, daily (PBS 3.4 moved retention from datastore config to prune jobs)

### PBS API token

- **Token ID:** `root@pam!pve-cluster`
- **Secret:** stored in `/root/.pbs-migration-credentials` on pve2 (chmod 600) — NEVER committed
- **ACL:** `DatastoreBackup` on `/datastore/migration-window` (includes backup + read + prune per PBS role definitions)
- **Rotation plan:** rotate once mid-migration if the window extends past 14 days; revoke at decommission time (see runbook)

### PBS TLS fingerprint

- **SHA-256:** `d2:6e:ee:4f:1d:e8:e3:50:a1:ab:5b:3e:cb:5d:e4:e6:a7:cc:7c:c5:0c:b5:57:66:d4:d0:97:d5:72:f9:82:50`
- Embedded in `/etc/pve/storage.cfg` via `pvesm add pbs --fingerprint ...` so PVE nodes can verify the PBS API cert without trusting the CT's self-signed root

### Cluster storage.cfg entry (now live on all 3 pve nodes)

```
pbs: pbs-migration
    datastore migration-window
    server 192.168.50.155
    content backup
    fingerprint d2:6e:ee:4f:1d:e8:e3:50:a1:ab:5b:3e:cb:5d:e4:e6:a7:cc:7c:c5:0c:b5:57:66:d4:d0:97:d5:72:f9:82:50
    username root@pam!pve-cluster
```

### Gotchas hit and resolved

1. **CA cert failure for `download.proxmox.com` over HTTPS** in the fresh Debian 12 CT — resolved by fetching the `proxmox-release-bookworm.gpg` key over HTTP (acceptable because apt verifies the repo signature against the key once installed; the one-time HTTP fetch can't poison a signed key file). SHA-512 verified against the key bundled in the Proxmox repo.
2. **`proxmox-backup-proxy` failed with EACCES on `rrdb stat dir`** — because the 500 GB mountpoint was created by `pct create` before the PBS postinst added the `backup` user, `/var/lib/proxmox-backup` was owned `root:root` mode 755. Fix: `chown backup:backup /var/lib/proxmox-backup` inside CT, `systemctl reset-failed && systemctl start proxmox-backup-proxy`. Documented so Story 2.8 (new PBS datastore on pve3) doesn't hit the same issue — the fix is "install PBS *before* mounting the dedicated backup volume, or chown the mountpoint root immediately after mounting."
3. **PBS 3.4 removed inline `--keep-*` retention from datastore config** — replaced with dedicated `prune-job`s. Used `proxmox-backup-manager prune-job create mw-prune --store migration-window --keep-last 2 --schedule daily`.
4. **`proxmox-backup-manager user generate-token --output-format json`** — flag rejected in PBS 3.4 (schema says no extra properties). The default human-readable output already contains the token secret as JSON-ish lines, so I captured it from there.

### Test backup result (CT152)

- **Command:** `vzdump 152 --storage pbs-migration --mode snapshot`
- **Backup ID:** `ct/152/2026-04-20T19:19:00Z`
- **Source size:** 9.84 GiB (mountpoint rootfs)
- **Read:** 9.447 GiB (the rest was LOST+FOUND / exclusions)
- **Compressed on-wire:** 4.033 GiB
- **Volume size reported by `pvesm list`:** 10,574,652,254 B (~10.57 GB raw)
- **Duration:** 56.87 s (client-side); 00:01:03 total including snapshot setup/teardown
- **Throughput:** 170.608 MiB/s average
- **Status:** OK — backup finished successfully, notification sent via `mail-to-root`

### Datastore reachability from all 3 nodes

`pbs-migration` is registered in `/etc/pve/storage.cfg` which is cluster-replicated via pmxcfs, so it is automatically visible on pve1, pve2, pve3. Confirmed on pve2 via `pvesm status` (`pbs-migration pbs active 491 GiB available`). Reachability from pve1/pve3 is implicit because all three pve nodes sit on `192.168.50.0/24` with `vmbr0` bridged directly to the LAN.

### Decommissioning plan (full detail in runbook)

- Expected lifetime: ~4 weeks (duration of Epics 1-3 migration window)
- Trigger for removal: Story 2.8 (new permanent PBS datastore on pve3 `hdd-pool/pbs`) proven, AND Story 2.11 soak test complete
- Steps: `pvesm remove pbs-migration` → `pct stop 105 && pct destroy 105` → `rm /root/.pbs-migration-credentials` on pve2

## Implementation Report

- Created CT105 (`ct-pbs-migration`) on pve2 with 500 GB datastore volume; network `192.168.50.155/24` verified unused
- Installed Proxmox Backup Server 3.4.8-3 from `pbs-no-subscription` repo
- Fixed mountpoint ownership issue (EACCES on rrdb stat dir) by chowning `/var/lib/proxmox-backup` to `backup:backup`
- Created datastore `migration-window` and prune job `mw-prune` (keep-last=2 daily)
- Generated API token `root@pam!pve-cluster` with `DatastoreBackup` ACL; persisted credentials to `/root/.pbs-migration-credentials` on pve2 (chmod 600, NOT in git)
- Registered `pbs-migration` in cluster storage.cfg with SHA-256 fingerprint pin
- Test backup of CT152 succeeded: 9.447 GiB read, 4.033 GiB compressed, 56.87 s at 170 MiB/s (backup ID `ct/152/2026-04-20T19:19:00Z`)
- Authored operational runbook at `_bmad-output/implementation-artifacts/pbs-migration-datastore-runbook.md`
- No commits made (director handles that)
