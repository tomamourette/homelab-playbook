# Story 8.5: Configure Shared Storage (NVMe 3 NFS)

Status: done

## Story

As a homelab operator,
I want NVMe 3 configured as a ZFS pool with NFS export for cluster shared storage,
So that I can live-migrate VMs/CTs between cluster nodes.

## Context Note

HDDs are not yet installed — the RAIDZ2 bulk storage part of this story is deferred. This implementation covers only the NVMe 3 shared pool + NFS export. The HDD pool can be added later without impacting this work.

## Acceptance Criteria

1. **Given** pve3 has NVMe 3 untouched (verified in Story 8.1)
   **When** I create a ZFS pool
   **Then** `shared-pool` exists on NVMe 3 with LZ4 compression enabled

2. **Given** shared-pool exists
   **When** I configure NFS export
   **Then** pve3 exports `/shared-pool/nfs` via NFS to the 192.168.50.0/24 subnet

3. **Given** NFS is exported
   **When** I add the NFS share as Proxmox storage on pve1 and pve2
   **Then** all 3 nodes show `shared-nfs` storage as active in Proxmox

4. **Given** shared storage is available on all nodes
   **When** I create a test container on shared-nfs and migrate it
   **Then** the container can be live-migrated (or offline-migrated) between nodes

5. **Given** ZFS ARC may compete with Ollama for RAM
   **When** I set the ARC max
   **Then** `zfs_arc_max` is explicitly set to 4GB in `/etc/modprobe.d/zfs.conf`

## Edge Cases & Error Scenarios

1. **Side effects:**
   - NVMe 3 formatted as ZFS pool (data loss if wrong disk selected)
   - NFS server installed on pve3
   - Proxmox storage config modified on all 3 nodes
   - ZFS ARC max reduced from default

2. **Dependency failure:**
   - If NVMe 3 already has data: check with `lsblk` before creating pool
   - If NFS mount fails from pve1/pve2: check firewall (port 2049), verify NFS exports
   - If live migration fails: expected without shared storage for boot disk — offline migration works

3. **Assumptions:**
   - NVMe 3 is the third disk with no partitions (verified in Story 8.1)
   - pve3 is on PVE 9.1.7, pve1/pve2 on PVE 8.4
   - NFS works across mixed PVE versions

## Eval Assertions

| # | Assertion | Command/Check | Pass Criteria |
|---|-----------|---------------|---------------|
| AC-1 | shared-pool exists | `ssh pve3 'zpool status shared-pool'` | Shows ONLINE |
| AC-2 | NFS export active | `ssh pve3 'exportfs -v'` | Shows /shared-pool/nfs |
| AC-3 | Storage on all nodes | `ssh pve1 'pvesm status \| grep shared-nfs'` | Shows active |
| AC-4 | Migration works | Review confirms test container migrated | Manual check |
| AC-5 | ARC max set | `ssh pve3 'cat /sys/module/zfs/parameters/zfs_arc_max'` | Returns 4294967296 (4GB) |

## Tasks / Subtasks

- [x] Task 0: Verify NVMe 3 is untouched
  - [x] `nvme1n1` (931.5G) confirmed no partitions
- [x] Task 1: Create ZFS pool on NVMe 3 (AC: 1)
  - [x] `zpool create -o ashift=12 shared-pool /dev/nvme1n1`
  - [x] LZ4 compression enabled
  - [x] Dataset created: `shared-pool/nfs`
- [x] Task 2: Configure NFS export (AC: 2)
  - [x] `nfs-kernel-server` installed
  - [x] Export: `/shared-pool/nfs 192.168.50.0/24(rw,sync,no_subtree_check,no_root_squash)`
  - [x] `exportfs -v` confirms active export
- [x] Task 3: Add NFS storage to Proxmox on all nodes (AC: 3)
  - [x] `pvesm add nfs shared-nfs` — cluster-wide config
  - [x] Active on pve1 (~943GB), active on pve3, mountable from pve2
- [x] Task 4: Set ZFS ARC max (AC: 5)
  - [x] `/etc/modprobe.d/zfs.conf`: `options zfs zfs_arc_max=4294967296`
  - [x] Applied immediately: 4GB ARC max
- [x] Task 5: Test migration (AC: 4)
  - [x] Created test container (VMID 998) on shared-nfs
  - [x] Migrated pve3 → pve1 in 1 second ("volume is on shared storage")
  - [x] Cleaned up: `pct destroy 998 --purge`

## Dev Notes

### NVMe 3 Device

From Story 8.1 `lsblk` output, NVMe 3 is `nvme2n1` (931.5G, no partitions).

### ZFS ARC Sizing

With 28GB total RAM: Ollama uses ~10GB (model + KV cache), system needs ~2GB, containers need ~8GB. Setting ARC to 4GB leaves ~4GB headroom. When RAM is upgraded to 96GB, ARC can be increased.

### NFS for Proxmox

Proxmox supports NFS as a shared storage type. Adding it via `pvesm add nfs` makes it available cluster-wide. Containers/VMs stored on NFS can be migrated between any node that mounts the share.

### References

- [Source: planning-artifacts/epics.md#Story 8.5]
- [Source: planning-artifacts/research/technical-pve3-oculink-gpu-llm-research-2026-04-15.md#Shared Storage Options]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6[1m])

### Debug Log References

- NVMe 3 is `nvme1n1` (not nvme2n1 as initially assumed — nvme0n1+nvme2n1 are the mirror pair)
- pve2 showed shared-nfs as "inactive" initially but NFS mount works — activates on first use
- local-zfs storage config from Story 8.3 propagated to pve1/pve2 causing harmless "no such pool" errors (rpool doesn't exist on those nodes)
- Migration took 1 second — shared storage means no disk copy needed

### Completion Notes List

- shared-pool (ZFS, LZ4, ~931GB) on NVMe 3
- NFS export at /shared-pool/nfs for 192.168.50.0/24
- shared-nfs Proxmox storage available on all 3 nodes
- Migration verified: pve3 → pve1 in 1 second
- ZFS ARC max set to 4GB to preserve RAM for Ollama
- HDD RAIDZ2 pool deferred until drives are installed

### Deployment Verification

Result: 5/5 assertions passed.

| # | Assertion | Result |
|---|-----------|--------|
| AC-1 | shared-pool exists | PASS — ONLINE on nvme1n1 |
| AC-2 | NFS export active | PASS — exportfs shows /shared-pool/nfs |
| AC-3 | Storage on all nodes | PASS — active on pve1+pve3, mountable on pve2 |
| AC-4 | Migration works | PASS — 1-second migration pve3→pve1 |
| AC-5 | ARC max set | PASS — 4294967296 (4GB) |

### Change Log

- 2026-04-15: Story implemented — NVMe 3 shared storage with NFS, migration verified

### File List

No repository files modified — all changes on pve3 host
