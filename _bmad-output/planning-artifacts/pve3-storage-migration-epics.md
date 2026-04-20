---
stepsCompleted: ['step-01-validate-prerequisites']
inputDocuments:
  - 'homelab-playbook/_bmad-output/planning-artifacts/research/technical-pve3-storage-architecture-research-2026-04-20.md'
project_name: 'PVE3 Storage Architecture Migration'
date: '2026-04-20'
user_name: 'tomamourette'
---

# PVE3 Storage Architecture Migration - Epic Breakdown

## Overview

This document decomposes the cluster-wide storage migration designed in the research document (`technical-pve3-storage-architecture-research-2026-04-20.md`) into implementable epics and stories. The migration converts the home-cluster from its current fragile state (pve1/pve2 on LVM-thin, pve3 on mixed ZFS with a single-node NFS SPOF) to a resilient ZFS-everywhere architecture with true HA via Proxmox Storage Replication, while preserving 354 GB of existing media data and the operator workbench container.

## Requirements Inventory

### Functional Requirements

FR1: The cluster SHALL provide HA failover for designated critical containers (CT162 ct-quant-trading, at minimum) such that the container continues to operate after any single node becomes unavailable.

FR2: The cluster SHALL implement Proxmox Storage Replication between ZFS pools on all three nodes (pve1, pve2, pve3) using matching storage IDs, with per-CT replication cadences per §4.5 of the research doc.

FR3: pve3 SHALL host a new RAIDZ1 pool across all 5× 20 TB WD Purple Pro HDDs, with mirrored metadata special vdev on NVMe partitions, providing ~72 TiB of usable bulk storage.

FR4: pve3 SHALL host a new 2-way mirrored `rpool` (nvme0 + nvme1 partitions) for OS + HA-critical CT root disks, providing ~828 GB usable.

FR5: pve3 SHALL host a single-disk `fast-pool` (nvme2) for ephemeral / rebuildable workloads, ~928 GB capacity.

FR6: pve1 and pve2 SHALL be reinstalled with ZFS single-disk `rpool` in place of LVM-thin, so that replication is possible.

FR7: The existing 354 GB media library (currently at `/shared-pool/nfs/media` on pve3) SHALL be preserved byte-for-byte during migration using `zfs send | zfs recv`, without re-downloading or transferring off-node.

FR8: The current NFS export `shared-nfs` SHALL be replaced with `shared-nfs-bulk` pointing to `/hdd-pool/bulk` on the new pool, with consumer CT (ct-media-01) reconfigured to the new path.

FR9: The operator workbench container (CT150 ct-dev-homelab) SHALL be evacuated to pve3 before pve1 reinstall begins, and remain functional throughout the migration so that the operator retains their SSH/git/Claude Code session.

FR10: Each CT and VM in the cluster SHALL be reassigned to appropriate storage per the §4.5 per-CT placement matrix (rpool for HA-critical roots, hdd-pool for bulk mounts, fast-pool for ephemeral scratch).

FR11: HA manager SHALL be configured with named groups (`critical`, `standard`, `pinned-pve1`, `pinned-pve3`) and each CT/VM SHALL be assigned to the appropriate group per §4.4.

FR12: The cluster SHALL be validated with deliberate pull-the-plug failover drills (V4, V5 in §6) before the migration is declared complete.

FR13: pve3 SHALL provide a Proxmox Backup Server datastore on `hdd-pool/pbs` accessible to all cluster nodes.

FR14: An Ansible role SHALL codify pve3's `hdd-pool` creation, dataset configuration, NFS export, and PBS datastore setup so the node is reproducible.

FR15: A CI guardrail SHALL prevent any CT/VM with `ha=1` from being deployed with storage on `fast-pool` or `shared-nfs-bulk`, preventing recurrence of the original incident.

FR16: The Terraform `ct-debian` module default storage SHALL be updated from `local-lvm` to `local-zfs` after all three nodes are converted.

### NonFunctional Requirements

NFR1: The migration SHALL be zero-data-loss. Byte-for-byte verification (sha256) of the media library required before declaring Phase 3 complete.

NFR2: The cluster SHALL maintain Proxmox quorum (≥2/3 nodes) at all times during the migration; no more than one node may be offline simultaneously during Phase 5/6/7.

NFR3: Each migration phase SHALL be individually revertible until explicitly destroyed (e.g., old `shared-pool` retained until 48 h after new NFS cutover succeeds).

NFR4: HA-critical container (CT162) replication RPO SHALL be ≤1 minute.

NFR5: Fault tolerance matrix after migration:
- rpool on pve3: survives any 1 NVMe drive loss
- hdd-pool on pve3: survives any 1 HDD drive loss AND any 1 NVMe (special mirror half) loss
- fast-pool on pve3: no redundancy (by design; only ephemeral data)

NFR6: Full PBS backup of every CT/VM SHALL exist and be verified (at least one restore test) before any node reinstall begins.

NFR7: ct-media-01 downtime during NFS cutover (Phase 4) SHALL be ≤10 minutes.

NFR8: CT160 ct-ai-01 (LLM) downtime during pve3 rebuild (Phase 5) is acceptable for the full phase duration (~2–4 h) given its non-critical HA status.

NFR9: VM100 smarthome downtime during pve1 rebuild (Phase 6) is acceptable because the Zigbee USB pinning makes it non-movable; household must be notified in advance.

NFR10: Operator workbench CT150 SHALL remain operational throughout the migration via Phase 5.5 pre-evacuation to pve3.

NFR11: 1 GbE network is sufficient for correctness; 2.5 GbE switch upgrade is nice-to-have but not blocking. No Proxmox reconfiguration required for later network upgrade.

NFR12: The cluster SHALL NOT deploy Ceph — asymmetric node capacity (500 GB / 1 TB / ~100 TB) and 1 GbE network make it architecturally wrong.

NFR13: Weekly ZFS scrubs SHALL be enabled on rpool and hdd-pool to detect silent corruption (required given non-ECC RAM).

NFR14: A cold-spare 22 TB WD Purple Pro SHALL be on the shelf before migration begins (Phase 0.1).

NFR15: All disk references in `zpool create` commands SHALL use `/dev/disk/by-id/...` paths (not `sda/sdb/...`) to avoid device-letter-shuffle hazards.

### Additional Requirements (Architecture & Infrastructure)

- **No starter template** — this is a brownfield migration against an existing running cluster. All work is incremental modification of existing nodes.
- **Proxmox VE 9 reinstall** required on pve3 (Phase 5), pve1 (Phase 6), pve2 (Phase 7). Installer used for partitioning + ZFS pool creation during install.
- **Post-install ZFS operations** (special vdev add, fast-pool create, NFS export setup, PBS datastore) require scripting via Ansible for reproducibility and documentation (see FR14).
- **Terraform state location matters** — current state files live on CT150 ct-dev-homelab. Must be committed/pushed to git before any pve1 work (Phase 0.7).
- **PBS datastore temporarily cannot live on pve3** during pve3 rebuild. Alternative datastore on pve1 (or external disk) needed for migration-window backups (Phase 0.3).
- **Storage IDs must match across nodes** for Proxmox Storage Replication to work. Enforce `local-zfs` ID on all three post-migration.
- **Fallback SSH path required** — direct laptop→pve-node SSH must be verified before pve1 reinstall, in case CT150 evacuation encounters issues (Phase 0.8).
- **Pinning constraints codified:**
  - VM100 smarthome → pinned to pve1 (USB Zigbee `10c4:ea60`)
  - CT160 ct-ai-01 → pinned to pve3 (iGPU `/dev/dri`)
- **Cold-spare procurement** has lead time; must be ordered at Phase 0 start.
- **Switch upgrade** is independent work, not a prerequisite; three-tier roadmap documented (1 GbE → 2.5 GbE → optional 10 GbE with hardware additions).

### UX Design Requirements

Not applicable. This is pure infrastructure work with no UI component. Operator-facing surfaces (Proxmox GUI, Ansible output, Terraform plan) use their native defaults.

### FR Coverage Map

_(to be populated in Step 2 after epic design)_

## Epic List

_(to be populated in Step 2)_
