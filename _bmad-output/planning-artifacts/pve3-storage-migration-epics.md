---
stepsCompleted: ['step-01-validate-prerequisites', 'step-02-design-epics', 'step-03-create-stories', 'step-04-final-validation']
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

NFR12: The cluster SHALL NOT deploy Ceph — asymmetric node capacity (1 TB / 1 TB / ~100 TB post-Epic-5-Window-A; post-Epic-5-Window-B: 1 TB / 1 TB / ~100 TB homogeneous) and 1 GbE network make it architecturally wrong.

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

| FR | Epic | Brief |
|----|------|-------|
| FR1 | Epic 6 | HA failover for designated CTs |
| FR2 | Epic 6 | Storage Replication configured cluster-wide |
| FR3 | Epics 2 + 3 | Hdd-pool RAIDZ1 (Epic 2) + mirrored special vdev added on NVMe rebuild (Epic 3) |
| FR4 | Epic 3 | Rpool 2-way mirror on pve3 |
| FR5 | Epic 3 | Fast-pool on pve3 |
| FR6 | Epic 5 | pve1/pve2 LVM→ZFS conversion |
| FR7 | Epic 2 | Media preservation via `zfs send \| zfs recv` |
| FR8 | Epic 2 | NFS export renamed to `shared-nfs-bulk` |
| FR9 | Epic 4 | CT150 evacuation to pve3 |
| FR10 | Epics 3 + 6 | Per-CT storage placement applied |
| FR11 | Epic 6 | HA groups defined (critical/standard/pinned-pve1/pinned-pve3) |
| FR12 | Epic 6 | Failover drills per §6 validation plan |
| FR13 | Epic 2 | PBS datastore on `hdd-pool/pbs` |
| FR14 | Epic 7 | Ansible role for pve3 storage (bonus: option c) |
| FR15 | Epic 7 | CI guardrail preventing HA CT on non-replicable storage (bonus: option d) |
| FR16 | Epic 7 | Terraform default storage updated `local-lvm` → `local-zfs` |

## Epic List

### Epic 1: Migration Readiness

All preparation that can be done without altering any running workload — backups verified, spare drive on shelf, fallback paths tested, operator workbench work committed/pushed, temporary PBS datastore in place. Exit state: ready to start destructive work with full revertibility.

**FRs covered:** — (no FRs directly; NFR-driven)
**NFRs covered:** NFR6 (PBS verified restore), NFR11 (network decision), NFR14 (cold spare on shelf)
**Maps to research §5 phases:** Phase 0, Phase 1 (optional)

### Epic 2: Bulk Storage Foundation with Preserved Media

A production-grade 72 TiB ZFS RAIDZ1 pool on pve3's five HDDs holding the byte-for-byte preserved 354 GB media library. Consumers (ct-media-01) switched to the new `shared-nfs-bulk` storage, which is explicitly scoped as non-HA. The old single-disk `shared-pool` retained for 48 h as rollback, then destroyed.

**FRs covered:** FR3 (RAIDZ1 creation — special vdev deferred to Epic 3), FR7 (media preservation), FR8 (NFS rename), FR13 (PBS datastore)
**NFRs covered:** NFR1 (zero-data-loss + sha256 verify), NFR7 (ct-media-01 downtime ≤10 min), NFR15 (by-id paths)
**Maps to research §5 phases:** Phase 2, 3, 4

### Epic 3: pve3 Target NVMe Architecture

pve3 reinstalled onto the target three-pool layout: 2-way mirrored `rpool` (nvme0 + nvme1 partitions) for OS and HA-critical CT roots, single-disk `fast-pool` (nvme2) for ephemeral scratch, mirrored metadata special vdev added to `hdd-pool` (nvme0 + nvme1 partitions). CT160 and CT162 restored and operational.

**FRs covered:** FR3 (special vdev added), FR4 (rpool mirror), FR5 (fast-pool), FR10 (pve3-side placement)
**NFRs covered:** NFR5 (fault tolerance matrix fully realized for pve3), NFR8 (CT160 downtime acceptable)
**Maps to research §5 phases:** Phase 5

### Epic 4: Operator Workbench Safe Harbor

ct-dev-homelab (CT150) safely evacuated to pve3 with a verified operator session on it before any destructive work touches pve1. Fallback SSH-from-laptop path documented and proven.

**FRs covered:** FR9 (CT150 evacuation)
**NFRs covered:** NFR10 (workbench operational throughout migration)
**Maps to research §5 phases:** Phase 5.5

### Epic 5: Cluster-wide ZFS Parity (pve1 + pve2)

pve1 and pve2 reinstalled with ZFS single-disk `rpool` in place of LVM-thin. All three nodes now expose matching `local-zfs` storage IDs, unblocking Proxmox Storage Replication. Quorum maintained throughout (only one node down at a time).

**FRs covered:** FR6 (LVM→ZFS conversion on pve1 and pve2)
**NFRs covered:** NFR2 (quorum ≥2/3 maintained), NFR9 (VM100 planned downtime)
**Maps to research §5 phases:** Phase 6, 7

### Epic 6: High Availability Activated

Replication jobs configured per §4.5 per-CT matrix, HA groups defined, workloads assigned, and the end-to-end HA contract validated by deliberate pull-the-plug drills. CT162 demonstrably survives a pve3 outage with ≤1 min RPO. The original failure mode (HA CT on single-node NFS) is operationally eliminated.

**FRs covered:** FR1 (HA failover), FR2 (replication), FR10 (cluster-wide placement), FR11 (HA groups), FR12 (validation drills)
**NFRs covered:** NFR4 (RPO ≤1 min)
**Maps to research §5 phases:** Phase 8, plus §6 validation V3–V6

### Epic 7: Reproducibility & Guardrails

Storage and HA architecture codified in Ansible + Terraform. CI guardrail rejects any configuration that places an HA-flagged CT on non-replicable storage (the original incident pattern). Architecture docs updated to reflect the new topology. Weekly ZFS scrubs automated.

**FRs covered:** FR14 (Ansible role for pve3 storage), FR15 (CI guardrail), FR16 (Terraform defaults)
**NFRs covered:** NFR13 (weekly scrubs)
**Maps to research §5 phases:** Phase 9

### Dependency Chain

```
Epic 1 ──> Epic 2 ──> Epic 3 ──> Epic 4 ──> Epic 5 ──> Epic 6 ──> Epic 7
```

Epic 7 work (Ansible role authoring, CI guardrail) can be developed in parallel with earlier epics; its delivery is gated on all prior epics being complete so the codified artifacts reflect reality.

---

## Epic 1: Migration Readiness

Complete all preparation that can be done without altering any running workload — backups verified, spare drive on shelf, fallback paths tested, operator workbench work pushed, temporary PBS datastore in place. Exit state: ready to start destructive work with full revertibility.

### Story 1.1: Procure cold-spare 22 TB WD Purple Pro

As an operator,
I want a 22 TB WD Purple Pro on the shelf,
So that a failed HDD during RAIDZ1 resilver can be replaced immediately without waiting on shipping.

**Acceptance Criteria:**

**Given** Phase 0 of the migration plan
**When** I place and receive the order
**Then** one sealed WD Purple Pro (matching part `WD221PURP`) is physically on the homelab shelf
**And** its serial number is documented in `homelab-playbook/_bmad-output/implementation-artifacts/cold-spare-inventory.md`
**And** the delivery date is recorded (for warranty tracking)

### Story 1.2: Set up migration-window PBS datastore (off pve3)

As an operator,
I want a PBS datastore that does NOT live on pve3,
So that I can take and restore backups even while pve3 is being rebuilt.

**Acceptance Criteria:**

**Given** the current PBS datastore is on or will be destroyed with pve3
**When** I create a temporary datastore on pve1 (or external USB/NFS disk)
**Then** the temporary datastore appears in PBS UI as healthy
**And** a test backup from CT152 to the temporary datastore succeeds
**And** the datastore location is documented and reachable from all three pve nodes
**And** the plan for decommissioning the temporary datastore post-migration is documented

### Story 1.3: Full cluster PBS backup with verified restore test

As an operator,
I want a fresh PBS backup of every CT and VM with at least one end-to-end restore validated,
So that I have a known-good recovery point before any node is touched.

**Acceptance Criteria:**

**Given** the temporary PBS datastore from Story 1.2 is operational
**When** I run PBS backup of all CTs/VMs in priority order (CT162, CT160, CT102, VM100, VM103, CT101, CT151, CT153, CT104, CT150, CT152)
**Then** every backup shows `OK` status in PBS UI
**And** each backup's size and timestamp are captured in `homelab-playbook/_bmad-output/implementation-artifacts/pre-migration-backup-manifest.md`
**When** I perform a test restore of CT152 to a temporary VMID on pve2
**Then** the test CT starts successfully and its application layer (Debian boot) is reachable
**And** the test CT is destroyed after verification

### Story 1.4: Capture pre-migration state snapshot

As an operator,
I want the current cluster state documented as a versioned snapshot in git,
So that I have an authoritative reference for rollback and diffing post-migration.

**Acceptance Criteria:**

**Given** the cluster is in its current pre-migration state
**When** I collect `zpool status`, `zfs list -t all`, `pct list`, `qm list`, `/etc/pve/storage.cfg`, `/etc/pve/lxc/*.conf`, `/etc/pve/qemu-server/*.conf`, `ip link`, `ethtool <iface>`, `pvecm status` from all three nodes
**Then** the outputs are written into `homelab-playbook/_bmad-output/implementation-artifacts/pre-migration-snapshot-2026-04-20/` under per-node subdirectories
**And** the snapshot is committed to the `homelab` repo
**And** the commit is pushed to origin

### Story 1.5: Capture media library checksum manifest

As an operator,
I want a SHA-256 manifest of the 354 GB media library,
So that Phase 3's `zfs send | recv` can be verified byte-for-byte.

**Acceptance Criteria:**

**Given** the media library at `/shared-pool/nfs/media` on pve3 is stable (ct-media-01 idle)
**When** I run `find /shared-pool/nfs/media -type f -exec sha256sum {} +` on pve3
**Then** the output is saved as `homelab-playbook/_bmad-output/implementation-artifacts/media-manifest-pre.txt`
**And** the manifest is committed to the repo
**And** a copy is also stored on a node that is not pve3 (so it survives pve3 reinstall)

### Story 1.6: Commit and push operator workbench work

As an operator,
I want all in-flight work on ct-dev-homelab committed and pushed to git,
So that if the workbench is lost during migration, no work is lost with it.

**Acceptance Criteria:**

**Given** I am working from ct-dev-homelab (CT150)
**When** I run `git status` in `/home/developer/workspace/homelab`
**Then** the working tree is clean (no modified/untracked files, or all changes are deliberately committed)
**And** `git log origin/main..HEAD` returns empty (no unpushed commits)
**And** any local-only artifacts that are intentionally not in git (SSH keys, terraform state files) are documented and copied off-node

### Story 1.7: Verify fallback SSH-from-laptop path

As an operator,
I want direct SSH access from my laptop to each pve node,
So that I can manage the migration even if ct-dev-homelab is unreachable.

**Acceptance Criteria:**

**Given** my laptop has SSH keys authorized on pve1, pve2, pve3
**When** I run `ssh pve1 hostname`, `ssh pve2 hostname`, `ssh pve3 hostname` from my laptop
**Then** all three commands succeed without password prompt
**And** the laptop-based SSH config is documented (host aliases, key paths)
**And** an `scp` test of a small file from laptop to pve3 succeeds

### Story 1.8: Network upgrade decision and optional switch swap

As an operator,
I want a documented decision on the network upgrade tier,
So that Phase 2 can start on the chosen network baseline.

**Acceptance Criteria:**

**Given** the three-tier network roadmap in research doc §5 Phase 1 (1 GbE / 2.5 GbE / 10 GbE)
**When** I decide which tier to migrate on
**Then** the decision and rationale are recorded in `homelab-playbook/_bmad-output/implementation-artifacts/network-tier-decision.md`
**And** if Tier 1 (2.5 GbE switch) is chosen, a 2.5 GbE-capable switch is installed and all three pve uplinks negotiate ≥2500 Mb/s (`ethtool` output attached)
**And** if Tier 0 (stay at 1 GbE) is chosen, the risk and expected initial-sync duration are explicitly acknowledged in the decision doc

---

## Epic 2: Bulk Storage Foundation with Preserved Media

A production-grade 72 TiB ZFS RAIDZ1 pool on pve3's five HDDs holding the byte-for-byte preserved 354 GB media library. Consumers (ct-media-01) switched to the new `shared-nfs-bulk` storage, which is explicitly scoped as non-HA. The old single-disk `shared-pool` retained for 48 h as rollback, then destroyed.

### Story 2.1: Identify and document all 5 HDDs by `/dev/disk/by-id`

As an operator,
I want every HDD referenced by its stable `by-id` path,
So that `zpool create` is not vulnerable to `/dev/sdX` letter reshuffling on reboot.

**Acceptance Criteria:**

**Given** the 5 HDDs are installed on pve3
**When** I run `ls -l /dev/disk/by-id/ | grep WD221PURP`
**Then** 5 distinct `ata-WDC_WD221PURP-…` paths are listed (one per physical drive)
**And** each `by-id` path is mapped to its serial number and captured in `homelab-playbook/_bmad-output/implementation-artifacts/hdd-inventory.md`
**And** the planned pool membership (all 5 in one RAIDZ1 vdev) is documented alongside

### Story 2.2: Create `hdd-pool` RAIDZ1 (without special vdev yet)

As an operator,
I want a RAIDZ1 ZFS pool across all 5 HDDs,
So that bulk data has redundancy and a canonical home.

**Acceptance Criteria:**

**Given** all 5 HDDs are identified by `by-id` (Story 2.1)
**When** I run `zpool create -o ashift=12 -O compression=zstd-3 -O atime=off -O xattr=sa hdd-pool raidz1 <by-id-1> <by-id-2> <by-id-3> <by-id-4> <by-id-5>`
**Then** `zpool status hdd-pool` shows `state: ONLINE`, a single `raidz1-0` vdev of 5 disks, 0 errors
**And** `zpool list hdd-pool` shows ~100 TB raw / ~72 TiB usable
**And** the pool is visible in Proxmox UI under Datacenter → Storage → (pending addition)

### Story 2.3: Create `hdd-pool` datasets and tune properties

As an operator,
I want purpose-specific datasets on `hdd-pool`,
So that each workload (PBS, bulk, models, quant-history) can have appropriate recordsize and sync settings.

**Acceptance Criteria:**

**Given** `hdd-pool` exists (Story 2.2)
**When** I run `zfs create` for `hdd-pool/pbs`, `hdd-pool/bulk`, `hdd-pool/models`, `hdd-pool/quant-history`
**Then** `zfs list hdd-pool` shows all four child datasets
**And** `hdd-pool/bulk` has `recordsize=1M` (verified with `zfs get recordsize`)
**And** `hdd-pool/pbs` has `recordsize=128K` and `compression=off` (PBS chunks are pre-compressed)
**And** `hdd-pool/bulk` has `sync=standard`
**And** all dataset properties are documented in `homelab-playbook/_bmad-output/implementation-artifacts/zfs-datasets.md`

### Story 2.4: Snapshot `shared-pool` as pre-migration rollback point

As an operator,
I want an immutable snapshot of the old pool,
So that I can rewind if the `zfs send | recv` goes wrong.

**Acceptance Criteria:**

**Given** `shared-pool` contains the 354 GB media library
**When** I run `zfs snapshot -r shared-pool@pre-migration`
**Then** `zfs list -t snapshot shared-pool` includes the `@pre-migration` snapshot on every dataset beneath `shared-pool`
**And** the snapshot is confirmed immutable (attempt to delete returns snapshot-protection error unless force-destroyed)

### Story 2.5: Migrate 354 GB media via `zfs send | zfs recv`

As an operator,
I want the media library copied to `hdd-pool` via native ZFS replication,
So that the transfer is fast, preserves structure, and never leaves pve3.

**Acceptance Criteria:**

**Given** `hdd-pool` exists and `shared-pool@pre-migration` snapshot exists
**When** I run `zfs send -R shared-pool@pre-migration | pv | zfs recv -F hdd-pool/bulk-staging`
**Then** the command completes successfully (estimated ~15–20 min)
**And** `zfs list hdd-pool/bulk-staging` shows approximately 354 GB used
**And** `ls /hdd-pool/bulk-staging/nfs/media/` shows `movies`, `tv`, `downloads`, `books`, `music`

### Story 2.6: Verify media via SHA-256 manifest diff

As an operator,
I want cryptographic proof that every byte of media transferred correctly,
So that I can declare Phase 3 complete with confidence.

**Acceptance Criteria:**

**Given** the media is on `hdd-pool/bulk-staging` (Story 2.5) and `media-manifest-pre.txt` exists (Story 1.5)
**When** I run `cd /hdd-pool/bulk-staging/nfs/media && find . -type f -exec sha256sum {} + > /tmp/media-manifest-post.txt`
**And** I run `diff /path/to/media-manifest-pre.txt /tmp/media-manifest-post.txt`
**Then** the diff returns empty (no output)
**And** if the diff is non-empty, the migration is considered FAILED and rolled back (destroy `hdd-pool/bulk-staging`, investigate)

### Story 2.7: Promote staging to final location and rename datasets

As an operator,
I want the staging dataset renamed into its final position,
So that the path structure matches the intended `hdd-pool/bulk/media` layout.

**Acceptance Criteria:**

**Given** staging-area media is verified byte-for-byte (Story 2.6)
**When** I destroy the empty placeholder `hdd-pool/bulk` (created in Story 2.3) and run `zfs rename hdd-pool/bulk-staging/nfs hdd-pool/bulk`
**Then** `zfs list | grep hdd-pool/bulk` shows the correct dataset at the expected path
**And** `ls /hdd-pool/bulk/media/` shows the media contents
**And** `recordsize=1M` is inherited/set on the renamed dataset

### Story 2.8: NFS cutover from `shared-nfs` to `shared-nfs-bulk`

As an operator,
I want the NFS export to serve from `hdd-pool/bulk`,
So that ct-media-01 reads from the new pool.

**Acceptance Criteria:**

**Given** `hdd-pool/bulk` is populated and ct-media-01 is stopped
**When** I update `/etc/exports` on pve3 to export `/hdd-pool/bulk 192.168.50.0/24(rw,no_subtree_check,no_root_squash)` and run `exportfs -ra`
**And** I add a new Proxmox storage entry `shared-nfs-bulk` in `/etc/pve/storage.cfg` pointing to `192.168.50.203:/hdd-pool/bulk`
**Then** `showmount -e 192.168.50.203` from pve1 shows the new export
**And** pve1 can mount `192.168.50.203:/hdd-pool/bulk` manually (test mount)
**And** the old `shared-nfs` entry is kept in `storage.cfg` as rollback

### Story 2.9: Update ct-media-01 config to use `shared-nfs-bulk` and validate

As an operator,
I want ct-media-01 reading media from the new pool,
So that the consumer flow is fully cut over.

**Acceptance Criteria:**

**Given** `shared-nfs-bulk` is available (Story 2.8)
**When** I edit `/etc/pve/lxc/102.conf` to change `mp0:` from `/mnt/pve/shared-nfs/media,mp=/media,...` to `/mnt/pve/shared-nfs-bulk/media,mp=/media,...`
**And** I start ct-media-01 (`pct start 102`)
**Then** `pct exec 102 -- ls /media/movies | head` returns the expected titles
**And** Jellyfin/Plex (or whichever consumer) plays back a test video successfully
**And** ct-media-01 downtime from stop→start→verified-playback is ≤10 min (NFR7)

### Story 2.10: Deploy PBS datastore on `hdd-pool/pbs`

As an operator,
I want PBS using the new HDD pool for backups,
So that cluster-wide backups have 72 TiB of redundant space.

**Acceptance Criteria:**

**Given** `hdd-pool/pbs` dataset exists (Story 2.3)
**When** I configure a new PBS datastore pointing to `/hdd-pool/pbs`
**Then** the datastore shows healthy in PBS UI
**And** a test backup (from any small CT) to this datastore succeeds
**And** the datastore is added as a backup target in Proxmox VE
**And** the temporary datastore from Story 1.2 is kept until Phase 5 completes

### Story 2.11: 48 h soak test and decommission `shared-pool`

As an operator,
I want confidence the new pool is stable before destroying the old one,
So that I retain rollback capability for a bake period.

**Acceptance Criteria:**

**Given** ct-media-01 has been running against `shared-nfs-bulk` for ≥48 h
**And** no NFS errors appear in `journalctl -u nfs-kernel-server` on pve3
**And** no CT/VM consumer has reported missing or corrupt data
**When** I run `zpool destroy shared-pool`
**Then** `zpool list` no longer shows `shared-pool`
**And** the `shared-nfs` entry is removed from `storage.cfg`
**And** nvme1 is now free (not a member of any pool) and available for re-use in Epic 3

---

## Epic 3: pve3 Target NVMe Architecture

pve3 reinstalled onto the target three-pool layout: 2-way mirrored `rpool` (nvme0 + nvme1 partitions) for OS and HA-critical CT roots, single-disk `fast-pool` (nvme2) for ephemeral scratch, mirrored metadata special vdev added to `hdd-pool` (nvme0 + nvme1 partitions). CT160 and CT162 restored and operational.

### Story 3.1: Evacuate CT160 and CT162 from pve3 pre-reinstall

As an operator,
I want CT160 and CT162 moved off pve3 before reinstall,
So that neither container is lost when pve3 is wiped.

**Acceptance Criteria:**

**Given** CT162 (quant-trading) is running on pve3 with rootfs on `local-zfs`
**When** I run `pct migrate 162 pve2` (offline migration — target storage `local-lvm` on pve2, since pve2 hasn't been ZFS-converted yet)
**Then** CT162 appears in `pct list` on pve2 and starts successfully
**Given** CT160 (ct-ai-01) is running on pve3 with iGPU passthrough
**When** I stop CT160 (`pct stop 160`)
**Then** the most recent PBS backup of CT160 (from Story 1.3) is verified by a test restore to a throwaway VMID
**And** CT160 is marked as "offline for Phase 5" in the migration log

### Story 3.2: Reinstall Proxmox on pve3 with 2-way ZFS mirror

As an operator,
I want pve3 running Proxmox 9 with the target rpool layout,
So that the new architecture is in place.

**Acceptance Criteria:**

**Given** Proxmox 9 installer USB is prepared
**When** I boot pve3 from USB and use the installer's manual-partitioning flow
**Then** nvme0 and nvme1 each have three partitions: 1 GB EFI, ~828 GB rpool-mirror, ~100 GB special-mirror
**And** nvme2 is left unpartitioned (target for Story 3.6)
**And** rpool is created as 2-way mirror of nvme0 partition 2 + nvme1 partition 2
**And** EFI is mirrored across all three NVMe so the node can boot from any single surviving drive
**And** after first boot, `zpool status rpool` shows ONLINE mirror of the two NVMe partitions

### Story 3.3: Rejoin pve3 to the cluster

As an operator,
I want pve3 back in the home-cluster with working quorum,
So that cluster operations can resume.

**Acceptance Criteria:**

**Given** pve3 boots on fresh Proxmox with rpool (Story 3.2)
**When** I run `pvecm add 192.168.50.201` (or via GUI join)
**Then** `pvecm status` on pve3 shows Quorate, 3 votes, all three node IPs in the ring
**And** `pvecm status` on pve1 and pve2 also shows 3 votes
**And** `/etc/pve/storage.cfg` is present and synchronized from the cluster

### Story 3.4: Add mirrored special vdev to `hdd-pool`

As an operator,
I want `hdd-pool` accelerated with mirrored metadata on NVMe,
So that PBS/bulk metadata operations become orders of magnitude faster.

**Acceptance Criteria:**

**Given** pve3 is back in the cluster (Story 3.3) and `hdd-pool` is importable
**When** I run `zpool import hdd-pool` (if not auto-imported)
**And** I run `zpool add hdd-pool special mirror /dev/disk/by-id/nvme-...-part3 /dev/disk/by-id/nvme-...-part3` (the p3 partitions on nvme0 and nvme1)
**Then** `zpool status hdd-pool` shows both the `raidz1-0` vdev and a `special` mirror of 2 NVMe partitions
**And** `zpool list hdd-pool` reports the special vdev capacity (~100 GB) as part of the pool
**And** the special vdev is ONLINE with 0 errors

### Story 3.5: Configure `special_small_blocks` for metadata-heavy datasets

As an operator,
I want small-file blocks routed to the special vdev for PBS-like workloads,
So that the HDD pool's random-IO characteristics improve for the right datasets.

**Acceptance Criteria:**

**Given** special vdev exists on `hdd-pool` (Story 3.4)
**When** I run `zfs set special_small_blocks=128K hdd-pool/pbs`
**Then** `zfs get special_small_blocks hdd-pool/pbs` returns `128K local`
**And** `hdd-pool/bulk` remains at default (0) so bulk media stays on HDDs
**And** the configuration is documented

### Story 3.6: Create single-disk `fast-pool` on nvme2

As an operator,
I want a dedicated scratch/ephemeral NVMe pool,
So that rebuildable workloads get NVMe speed without polluting rpool.

**Acceptance Criteria:**

**Given** nvme2 is untouched after Story 3.2
**When** I run `zpool create -o ashift=12 -O compression=lz4 -O atime=off fast-pool /dev/disk/by-id/nvme-...-nvme2n1`
**Then** `zpool status fast-pool` shows ONLINE single-disk pool
**And** `zpool list fast-pool` shows ~928 GB usable
**And** the Proxmox storage ID `fast-zfs` (or similar) is added in `storage.cfg` with `content: rootdir,images`
**And** warning banner/note in the storage description explicitly says "NOT REDUNDANT — ephemeral use only"

### Story 3.7: Re-establish NFS export for `hdd-pool/bulk`

As an operator,
I want the NFS export working again on fresh pve3,
So that ct-media-01 (now on pve3 after Epic 5 or still on pve1) can mount the media library.

**Acceptance Criteria:**

**Given** pve3 is reinstalled and `hdd-pool` is imported with all datasets
**When** I recreate `/etc/exports` with `/hdd-pool/bulk 192.168.50.0/24(rw,no_subtree_check,no_root_squash)` and run `exportfs -ra`
**And** I add `shared-nfs-bulk` entry back into `storage.cfg` pointing to `192.168.50.203:/hdd-pool/bulk`
**Then** `showmount -e 192.168.50.203` from any other node shows the export
**And** ct-media-01 continues to read media successfully (no data loss across the reinstall)

### Story 3.8: Restore CT160 and migrate CT162 back to pve3

As an operator,
I want both pve3-resident CTs back where they belong,
So that LLM serving and quant-trading resume on their natural node.

**Acceptance Criteria:**

**Given** pve3's rpool exists and `local-zfs` storage ID is present
**When** I restore CT160 from PBS to pve3 targeting `local-zfs`
**Then** CT160 starts successfully and Ollama/Open-WebUI are reachable
**When** I migrate CT162 from pve2 back to pve3 (`pct migrate 162 pve3 --target-storage local-zfs`)
**Then** CT162 runs on pve3 and its quant-trading logic resumes
**And** both CTs appear in `pct list` on pve3

### Story 3.9: Add `hdd-pool/models` mount to CT160 and relocate Ollama models

As an operator,
I want Ollama models living on the bulk HDD pool,
So that rpool isn't bloated by tens of GB of model files.

**Acceptance Criteria:**

**Given** CT160 is running on pve3 and `hdd-pool/models` dataset exists
**When** I add a mount point to CT160 config: `mp0: /hdd-pool/models,mp=/var/lib/ollama/models`
**And** I copy existing Ollama models into `/hdd-pool/models` (or re-pull if corrupted)
**And** I restart Ollama inside CT160
**Then** `ollama list` returns the expected models
**And** a test inference query succeeds
**And** `du -sh /var/lib/ollama/models` inside the CT shows it's mounted from `hdd-pool/models`

### Story 3.10: Validate pve3 storage state (V1, V2, V7)

As an operator,
I want automated verification that the pve3 target architecture is correct,
So that Epic 3 can be declared complete.

**Acceptance Criteria:**

**Given** pve3 rebuild is complete
**When** I run `zpool status rpool`, `zpool status hdd-pool`, `zpool status fast-pool`
**Then** all three pools report `state: ONLINE`, 0 read/write/checksum errors
**And** `hdd-pool` explicitly shows raidz1-0 of 5 HDDs + special mirror of 2 NVMe partitions
**When** I run `zpool scrub hdd-pool`
**Then** the scrub completes with 0 errors (may take hours; can run overnight)

---

## Epic 4: Operator Workbench Safe Harbor

ct-dev-homelab (CT150) safely evacuated to pve3 with a verified operator session on it before any destructive work touches pve1. Fallback SSH-from-laptop path proven.

### Story 4.1: Final commit + push of any trailing workbench work

As an operator,
I want one last clean-tree checkpoint before moving CT150,
So that any work done since Story 1.6 is preserved.

**Acceptance Criteria:**

**Given** Epic 3 is complete and we are about to start Epic 4
**When** I run `git status` in `/home/developer/workspace/homelab` inside CT150
**Then** working tree is clean
**And** `git log origin/main..HEAD` is empty
**And** a final commit summary is written to `homelab-playbook/_bmad-output/implementation-artifacts/workbench-checkpoint-phase-5.5.md`

### Story 4.2: Fresh PBS backup of CT150 post-checkpoint

As an operator,
I want the most-recent possible PBS backup of CT150,
So that the restore-to-pve3 step uses a clean state.

**Acceptance Criteria:**

**Given** CT150 working tree is clean (Story 4.1)
**When** I run PBS backup of CT150 (VMID 150) to the temporary datastore
**Then** the backup completes with `OK` status
**And** the backup timestamp is within the last 15 minutes
**And** the size matches expectations (~14 GB used on rootfs)

### Story 4.3: Restore CT150 to pve3 as parallel instance

As an operator,
I want CT150 running on pve3 without deleting the pve1 copy yet,
So that the pve1 instance remains as a fallback.

**Acceptance Criteria:**

**Given** the fresh PBS backup of CT150 exists (Story 4.2)
**When** I run `pct restore 250 <backup-path> --storage local-zfs --target pve3` (using VMID 250 to avoid collision with original CT150)
**Then** VMID 250 appears in `pct list` on pve3 with all CT150's content
**And** the pve1 CT150 (VMID 150) is still running but can be cleanly stopped for Phase 6

### Story 4.4: Verify pve3-resident CT150 operational

As an operator,
I want end-to-end confirmation the pve3-resident CT150 works,
So that I'm not trusting a silent restore.

**Acceptance Criteria:**

**Given** VMID 250 is restored on pve3
**When** I start VMID 250 (`pct start 250`) and `pct enter 250`
**Then** `git status` in `/home/developer/workspace/homelab` matches the clean state from Story 4.1
**And** SSH to pve1, pve2, pve3 from inside VMID 250 all succeed
**And** SSH keys in `~/.ssh/` are present
**And** Terraform can `terraform plan` against the homelab-infra state without errors
**And** Claude Code / dev tools reconnect cleanly

### Story 4.5: Cut operator session over to pve3-resident CT150

As an operator,
I want my active working session pointed at pve3-hosted CT150,
So that pve1 reinstall (Epic 5) cannot disrupt me.

**Acceptance Criteria:**

**Given** VMID 250 is validated (Story 4.4)
**When** I disconnect my current SSH/Claude session from the pve1-hosted CT150
**And** I reconnect to the pve3-hosted VMID 250 (using `ssh ct-dev-homelab-pve3` or equivalent alias)
**Then** my working directory is `/home/developer/workspace/homelab`
**And** `hostname` / IP confirm I am on the pve3 instance
**And** the pve1 CT150 (VMID 150) is stopped (`pct stop 150`) but not yet destroyed

### Story 4.6: Retain pve1 CT150 as tombstone until Epic 5 completes

As an operator,
I want the original CT150 preserved as a bail-out option,
So that if VMID 250 has hidden corruption, I can fall back.

**Acceptance Criteria:**

**Given** VMID 250 is the active workbench (Story 4.5)
**When** Epic 5 Phase 6 begins (pve1 reinstall)
**Then** the pve1 CT150 rootfs is already doomed (pve1 gets wiped) — no action needed
**But until** pve1 reinstall starts, VMID 150 (stopped) remains on pve1 as a fallback
**And** after Epic 5 completes, VMID 250 is renamed/renumbered back to 150 on pve3 for operational consistency

---

## Epic 5: Cluster-wide ZFS Parity (pve1 + pve2)

pve1 and pve2 reinstalled with ZFS single-disk `rpool` in place of LVM-thin. All three nodes now expose matching `local-zfs` storage IDs. Quorum maintained throughout (only one node down at a time).

### Story 5.1: Evacuate pve1 CTs/VMs before reinstall

As an operator,
I want every pve1 workload safely running elsewhere or safely backed up,
So that pve1 can be wiped without losing work.

**Acceptance Criteria:**

**Given** Epic 4 complete (CT150 already on pve3 as VMID 250)
**When** I restore/migrate pve1 workloads per §4.5 matrix:
- VM103 (HAOS) → restore from PBS to pve2
- CT101 (docker-host) → restore from PBS to pve3 (`local-zfs`)
- CT102 (media) → restore from PBS to pve3 (`local-zfs`), update mp0 to `shared-nfs-bulk`
- CT104 → restore from PBS to pve2
- VM100 (smarthome) → cannot move; stop and ensure fresh PBS backup exists
**Then** `pct list` / `qm list` on pve1 shows only the stopped VM100 and any templates
**And** all evacuated workloads are verified running on their new nodes
**And** VM100's USB Zigbee device (10c4:ea60) is noted for re-passthrough after reinstall

### Story 5.2: Reinstall Proxmox on pve1 with ZFS single-disk rpool

As an operator,
I want pve1 on ZFS matching pve3's storage ID convention,
So that replication becomes possible.

**Acceptance Criteria:**

**Given** pve1 is evacuated (Story 5.1)
**When** I boot pve1 from Proxmox 9 install USB
**And** I install with "ZFS (RAID0)" option on the single 1 TB Samsung 990 PRO NVMe (upgraded from failing 500 GB 970 EVO Plus during Epic 5 Window A), pool name `rpool`
**Then** pve1 boots with `zpool status rpool` ONLINE single-disk
**And** `/etc/pve/storage.cfg` (once rejoined) shows `local-zfs` ID pointing to `rpool/data`

### Story 5.3: Rejoin pve1 to the cluster

As an operator,
I want pve1 back in cluster quorum,
So that HA/replication configuration can include it.

**Acceptance Criteria:**

**Given** pve1 is freshly installed (Story 5.2)
**When** I run `pvecm add 192.168.50.203` (join via pve3)
**Then** `pvecm status` shows 3 Quorate votes from all nodes
**And** pve1 is listed in `/etc/pve/nodes/`
**And** pve1 sees the cluster-wide `storage.cfg` including `local-zfs` across all three nodes

### Story 5.4: Restore VM100 smarthome to pve1 with USB passthrough

As an operator,
I want the Zigbee coordinator VM back on pve1,
So that home automation resumes.

**Acceptance Criteria:**

**Given** pve1 is in the cluster (Story 5.3)
**When** I restore VM100 from PBS to pve1 targeting `local-zfs`
**And** I re-add the USB passthrough for device `10c4:ea60` in the VM config
**Then** VM100 starts successfully
**And** Home Assistant (VM103 on pve2 for now, or wherever moved in Story 5.1) sees the Zigbee coordinator online
**And** household automation recovers (test: trigger a Zigbee device event)

### Story 5.5: Move selected CTs back to pve1 per §4.5 matrix

As an operator,
I want workloads whose "home node" is pve1 running there,
So that the cluster matches the target per-CT placement plan.

**Acceptance Criteria:**

**Given** pve1 has `local-zfs` storage (Story 5.3)
**When** I live-migrate (or restore from PBS) the following to pve1 targeting `local-zfs`:
- CT101 (docker-host)
- VM103 (HAOS)
- CT102 (media) — still mounts `shared-nfs-bulk` for media
- CT104
**Then** all listed workloads are running on pve1
**And** CT102's mp0 still references `/mnt/pve/shared-nfs-bulk/media`
**And** `pct list` / `qm list` on pve1 matches the §4.5 matrix

### Story 5.6: Update Terraform tfvars for pve1 CTs

As an operator,
I want Terraform state reflecting the new storage,
So that `terraform plan` is clean and future CT creations target `local-zfs`.

**Acceptance Criteria:**

**Given** pve1 CTs are managed by Terraform (CT101, CT102, CT150, VM103 per tags)
**When** I update `homelab-infra/terraform/envs/homelab/terraform.tfvars` — replace `local-lvm` references with `local-zfs` for pve1-targeted resources
**And** I run `terraform plan`
**Then** the plan shows zero changes (Terraform recognizes state already matches)
**And** if any drift exists, it is reconciled with `terraform apply` or `terraform state` commands
**And** the tfvars change is committed + pushed

### Story 5.7: Evacuate pve2 CTs before reinstall

As an operator,
I want pve2 workloads safely relocated,
So that pve2 can be wiped without losing work.

**Acceptance Criteria:**

**Given** pve1 is ZFS and in-cluster (Story 5.3); VMID 250 (operator workbench) is on pve3
**When** I migrate/restore pve2 workloads:
- CT151 (ct-sparkle-cps) → migrate or restore to pve1 (`local-zfs`)
- CT153 (ct-isabelle) → migrate or restore to pve1 (`local-zfs`)
- CT152 (ct-dev-test) → destroy (Terraform will recreate on pve2 post-install)
- Any VMs that ended up on pve2 during Story 5.1 (VM103, CT104) → migrate back to pve1 or pve3
**Then** `pct list` / `qm list` on pve2 is empty (or only stopped templates)

**Evacuation matrix (including migration-window PBS):**

| Guest | Source storage (pve2) | Target (during pve2 window) | Method | Post-window home | Notes |
|-------|------------------------|----------------------------|--------|------------------|-------|
| CT151 ct-sparkle-cps | pve2 local-lvm | pve1 local-zfs | migrate or PBS restore | pve1 or pve2 per §4.5 | Standard evacuation |
| CT153 ct-isabelle    | pve2 local-lvm | pve1 local-zfs | migrate or PBS restore | pve1 or pve2 per §4.5 | Standard evacuation |
| CT152 ct-dev-test    | pve2 local-lvm | destroyed      | Terraform recreate after Story 5.10 | pve2 local-zfs | Ephemeral; no data to preserve |
| VM103 / CT104 (if on pve2 post-5.1) | pve2 local-lvm | pve1 or pve3 | migrate | per §4.5 | Temporary relocation only |
| CT105 ct-pbs-migration | pve2 local-lvm | pve3 local-zfs temporarily OR external (fallback) | PBS restore | back to pve2 local-zfs | **Critical**: this is the migration-window PBS (Story 1.2). Moving pve2 → pve3 during the pve2 window breaks Path A. Alternative: copy migration-window datastore to `hdd-pool/pbs` on pve3 first, import there, then destroy original. |

**Dev Note:** VM105 requires special handling — it's the cluster's only backup destination during the window. Moving the PBS while it is the sole backup target breaks the PBS-runbook "Decommissioning Path A" (the migration-window PBS must remain reachable and immutable until pve2 is back and rollback is no longer needed). Consider standing up the permanent PBS on `hdd-pool/pbs` (Story 2.10 deferred) **before** starting Epic 5 Window B, so the migration-window datastore can be decommissioned cleanly instead of relocated mid-window.

### Story 5.8: Reinstall Proxmox on pve2 with ZFS single-disk rpool

As an operator,
I want pve2 on ZFS matching the cluster-wide convention.

**Acceptance Criteria:**

**Given** pve2 is evacuated (Story 5.7)
**When** I boot pve2 from Proxmox 9 installer and install with "ZFS (RAID0)" on the 1 TB NVMe, pool name `rpool`
**Then** pve2 boots with `zpool status rpool` ONLINE single-disk
**And** `local-zfs` storage ID is present in cluster-wide `storage.cfg`

### Story 5.9: Rejoin pve2 to the cluster

**Acceptance Criteria:**

**Given** pve2 is reinstalled (Story 5.8)
**When** I run `pvecm add 192.168.50.203`
**Then** `pvecm status` shows 3 Quorate votes across pve1, pve2, pve3
**And** pve2 is listed in `/etc/pve/nodes/`

### Story 5.10: Restore pve2 CTs and let Terraform recreate CT152

As an operator,
I want pve2 back in full operation.

**Acceptance Criteria:**

**Given** pve2 is in cluster (Story 5.9)
**When** I restore CT151 and CT153 from PBS to pve2 (`local-zfs`)
**And** I run `terraform apply` on the homelab-infra state
**Then** CT152 is recreated on pve2 via Terraform targeting `local-zfs`
**And** all three pve2-intended CTs (151, 152, 153) are running on pve2
**And** any workloads temporarily on pve1 that belong on pve2 per §4.5 are migrated back

### Story 5.11: Update Terraform tfvars for pve2 CTs

**Acceptance Criteria:**

**Given** pve2 CTs are managed by Terraform
**When** I update `terraform.tfvars` for pve2-targeted resources (remove `local-lvm`, use `local-zfs`)
**Then** `terraform plan` shows zero changes
**And** the tfvars change is committed + pushed

### Story 5.13: Add second NVMe to pve1 as ZFS mirror (optional; hardware permitting)

As an operator,
I want pve1's `rpool` to be a 2-way ZFS mirror instead of a single-disk pool,
So that pve1 survives a single NVMe failure without requiring cluster-replication-driven recovery.

**Acceptance Criteria:**

**Given** pve1 has a spare NVMe slot and a second 1 TB (or larger) NVMe is procured
**When** I attach the second NVMe to the existing `rpool` via `zpool attach rpool <existing-by-id> <new-by-id>`
**Then** `zpool status rpool` shows a `mirror-0` vdev of two devices, resilver completes cleanly
**And** pve1 now tolerates a single-drive failure without needing PBS restore

**Rationale:** Enables real-time protection against pve1 single-drive failure (complementary to cluster replication, which handles node-level failure but not bare-metal single-drive hot-swap without downtime). Deferred to backlog — not required for Epic 6 HA correctness, which relies on cluster replication across nodes, not intra-node redundancy.

### Story 5.12: Validate cluster-wide storage ID consistency

As an operator,
I want proof all three nodes expose identical storage configurations,
So that Epic 6 replication will work without surprise errors.

**Acceptance Criteria:**

**Given** pve1 and pve2 are both ZFS-converted
**When** I run `cat /etc/pve/storage.cfg` on any node
**Then** `local-zfs` entry exists referring to `rpool/data`, `content` matches (`images,rootdir`)
**And** `local` (dir) entry exists on all three nodes
**And** `shared-nfs-bulk` (NFS from pve3) is visible cluster-wide
**And** `hdd-zfs` (or similar for hdd-pool/models etc.) is visible on pve3
**And** `fast-zfs` is visible on pve3 only (with the "non-redundant" description)
**And** no `local-lvm` references remain anywhere

---

## Epic 6: High Availability Activated

Replication jobs configured per §4.5 per-CT matrix, HA groups defined, workloads assigned, and end-to-end HA contract validated by deliberate pull-the-plug drills. The original failure mode is operationally eliminated.

### Story 6.1: Create replication jobs per §4.5 matrix

As an operator,
I want automated ZFS replication for designated workloads,
So that failover has a recent copy of each CT on peer nodes.

**Acceptance Criteria:**

**Given** all three nodes expose `local-zfs` with matching IDs
**When** I create replication jobs in Datacenter → Replication per §4.5:
- CT162 → pve1 and pve2 at 1-minute interval
- CT101 (docker) → pve2 and pve3 at 5-minute
- CT102 (media root only) → pve2 at 15-minute
- CT151 → pve1 and pve3 at 5-minute
- CT153 → pve1 at 5-minute
- CT160 (root only) → pve2 at 30-minute
- VM103 (HAOS) → pve2 at 15-minute
- VMID 250 / CT150 (workbench) → pve1 and pve2 at 15-minute
**Then** all jobs appear in `pvesr status` with status `OK`
**And** the first replication cycle of each job completes successfully
**And** subsequent cycles show recent timestamps (< interval + 1 min)

### Story 6.2: Verify replication state and deltas

As an operator,
I want evidence each replication job is healthy and producing appropriately-sized deltas.

**Acceptance Criteria:**

**Given** Story 6.1 complete and at least 2 replication cycles per job have run
**When** I run `pvesr status` and inspect each job
**Then** all jobs show `OK` with last-run timestamp < interval
**And** `pvesr list` shows delta sizes in MB (not GB), indicating deltas are small as expected
**And** any failing/slow job is diagnosed (network, receiver disk space, etc.) and fixed

### Story 6.3: Define HA groups

As an operator,
I want named HA groups matching the placement policy,
So that HA manager moves CTs to the right subset of nodes.

**Acceptance Criteria:**

**Given** cluster quorum and fencing are active
**When** I create groups in Datacenter → HA → Groups:
- `critical`: members = pve1, pve2, pve3 (no restriction); nofailback=0
- `standard`: members = pve1, pve2, pve3; nofailback=0
- `pinned-pve1`: members = pve1 only; restricted=1
- `pinned-pve3`: members = pve3 only; restricted=1
**Then** all four groups appear in `ha-manager config` output
**And** each group's node list is verified correct

### Story 6.4: Assign CTs and VMs to HA groups

As an operator,
I want each workload assigned to its intended HA group,
So that failover behavior matches design.

**Acceptance Criteria:**

**Given** HA groups exist (Story 6.3)
**When** I assign per §4.4/§4.5:
- CT162 → `critical`
- VM100 → `pinned-pve1`
- CT160 → `pinned-pve3`
- CT101, CT102, CT151, CT153, VM103, VMID 250/CT150 → `standard`
- CT104, CT152 (disposable) → none (no HA)
**Then** `ha-manager config` shows each assignment
**And** `ha-manager status` shows them as `started` (or appropriate state)
**And** the CRM watchdog is armed (`ha-manager status` output)

### Story 6.5: Validation drill V3 — replication RPO for CT162

As an operator,
I want proof CT162's replication RPO meets the ≤1-min target.

**Acceptance Criteria:**

**Given** CT162 is replicating to pve1 and pve2 at 1-min interval
**When** I observe `pvesr status` over 10 minutes
**Then** every successful sync is ≤60 sec older than wall-clock at observation time
**And** no job has entered an error state

### Story 6.6: Validation drill V4 — simulated failover via migrate

As an operator,
I want to exercise the HA-style failover without a destructive node crash first,
So that baseline mechanics work.

**Acceptance Criteria:**

**Given** CT162 is running on pve3 with replication to pve1 and pve2
**When** I run `ha-manager migrate ct:162 pve2` (triggers HA-managed migration)
**Then** CT162 stops on pve3 and starts on pve2 within ~1 min
**And** `pct status 162` on pve2 shows `running`
**And** the quant-trading application logs indicate clean restart (no transaction loss beyond RPO)
**And** I migrate it back to pve3 for subsequent tests

### Story 6.7: Validation drill V5 — pull-plug pve3

As an operator,
I want ultimate proof the cluster survives sudden node loss,
So that the original incident cannot recur.

**Acceptance Criteria:**

**Given** CT162 is on pve3 with fresh replicas on pve1 and pve2
**When** I hard-power-cycle pve3 (IPMI reset, or physical power cable pull — NOT a graceful shutdown)
**Then** within ~2 min, HA manager declares pve3 dead and starts CT162 on a peer (pve2 preferred due to lower latency)
**And** `pct status 162` on pve2 shows `running`
**And** the quant-trading app resumes (market hours permitting)
**And** `shared-nfs-bulk` shows as unreachable (expected — pve3 is down) and ct-media-01 shows the mount as stale
**And** no other HA-group CT is unexpectedly down

### Story 6.8: Validation drill V6 — pve3 recovery

As an operator,
I want pve3 rejoining to re-establish replication cleanly,
So that recovery from a node outage is routine.

**Acceptance Criteria:**

**Given** pve3 is currently offline after Story 6.7 and CT162 is running on pve2
**When** I power pve3 back on
**Then** pve3 rejoins the cluster within ~3 min (quorum returns to 3)
**And** `pvesr status` shows CT162's replication re-established with pve3 as the new target
**And** after the first post-recovery replication cycle, CT162 can be HA-manager-migrated back to pve3
**And** `shared-nfs-bulk` becomes reachable again; ct-media-01 stale-mount recovers (may require `pct reboot`)

### Story 6.9: Document validated HA behavior in runbook

As an operator,
I want a durable operational runbook,
So that a future incident is routine, not research.

**Acceptance Criteria:**

**Given** drills V3–V6 are passing (Stories 6.5–6.8)
**When** I write `homelab-playbook/_bmad-output/implementation-artifacts/ha-runbook.md` covering:
- How to verify replication state
- How to trigger planned failover
- How to respond to unplanned failover
- How to recover a failed node
- How to handle the `shared-nfs-bulk` stale-mount case after pve3 reboot
**Then** the runbook is committed to the repo
**And** it references the specific pvesr/ha-manager/pct commands observed in drills

---

## Epic 7: Reproducibility & Guardrails

Storage and HA architecture codified in Ansible + Terraform. CI guardrail rejects any configuration that places an HA-flagged CT on non-replicable storage. Architecture docs updated.

### Story 7.1: Author Ansible role `pve-host-pve3-storage`

As an operator,
I want pve3's storage layout reproducible from code,
So that a future rebuild or clone is one `ansible-playbook` away.

**Acceptance Criteria:**

**Given** pve3's storage is manually configured (Epics 2 and 3)
**When** I author `homelab-infra/ansible/roles/pve-host-pve3-storage/` with tasks for:
- Create `hdd-pool` (idempotent: skip if exists)
- Create datasets + properties per §4.2
- Add mirrored special vdev (idempotent)
- Create `fast-pool` (idempotent)
- Configure NFS export
- Configure PBS datastore
**Then** the role passes `ansible-lint` and has a README
**And** a dry-run against the existing pve3 reports "no changes" (idempotent)
**And** the role is integrated into the pve3 host playbook

### Story 7.2: Idempotency test of Ansible role against fresh state

As an operator,
I want proof the role works from a clean slate,
So that disaster recovery is proven, not assumed.

**Acceptance Criteria:**

**Given** the Ansible role from Story 7.1
**When** I run it against a lab VM with 5 simulated HDDs and 3 NVMe partitions (or via --check mode against pve3)
**Then** the role creates all expected pools, datasets, and exports
**And** a second run reports zero changes
**And** the test outcome is documented in the role's README

### Story 7.3: Implement CI guardrail preventing HA CT on non-replicable storage

As an operator,
I want automated rejection of the original-incident configuration,
So that I cannot accidentally repeat it.

**Acceptance Criteria:**

**Given** the repo has a pre-commit / CI pipeline
**When** I add a check (Ansible playbook, shell script, or Terraform validation) that:
- Reads all CT/VM configs (via Proxmox API or Terraform state)
- For each resource with `ha.state == started` (or tag `ha=true`), verifies storage is NOT `fast-zfs`, `fast-pool`, or `shared-nfs-bulk`
- Fails CI with a clear error if a violation is found
**Then** a deliberate test commit that puts an HA CT on `fast-zfs` fails CI with the expected message
**And** a commit with the correct placement passes CI
**And** the check runs on every PR / pre-commit

### Story 7.4: Update Terraform module defaults

As an operator,
I want newly-created CTs to default to `local-zfs`,
So that no one accidentally creates a new workload on a storage that doesn't exist.

**Acceptance Criteria:**

**Given** `homelab-infra/terraform/modules/ct-debian/variables.tf` currently defaults `storage_id`
**When** I update the default value from any `local-lvm` reference to `local-zfs`
**And** I update `terraform.tfvars.example` to match
**Then** a new CT created via the module with no explicit `storage_id` lands on `local-zfs`
**And** existing CTs are unaffected (their state is already set)

### Story 7.5: Update architecture docs to reflect target state

As an operator,
I want `docs/architecture-homelab-infra.md` reflecting reality,
So that any future human or agent reading the doc sees the correct topology.

**Acceptance Criteria:**

**Given** the migration is complete (Epics 1–6 done)
**When** I update `docs/architecture-homelab-infra.md` with:
- The three pools on pve3 with their vdev structure
- The per-CT placement matrix from research §4.5
- The HA groups and their members
- The `shared-nfs-bulk` non-HA scoping
- The prohibition on HA CTs using non-replicable storage
**Then** the doc is committed + pushed
**And** stale references to `shared-nfs`, single-disk ZFS on pve3, or `local-lvm` on pve1/pve2 are removed

### Story 7.6: Enable weekly ZFS scrub automation

As an operator,
I want scheduled scrubs on every ZFS pool,
So that silent corruption is detected early (especially given non-ECC RAM).

**Acceptance Criteria:**

**Given** all ZFS pools exist across the cluster
**When** I enable the Debian-packaged `zfs-zed` scheduled scrub (default `/etc/cron.d/zfsutils-linux` runs on the second Sunday of each month)
**OR** I create systemd timers in Ansible for weekly scrubs on each node
**Then** `systemctl list-timers` (or `cron` inspection) shows the scheduled scrub
**And** email/log notification on scrub completion is configured
**And** the first manual scrub of each pool has been executed + passed

### Story 7.7: Retrospective and memory updates

As an operator,
I want the lessons from this migration captured in durable memory,
So that future related work benefits from the learnings.

**Acceptance Criteria:**

**Given** all prior stories are complete
**When** I write a retrospective covering:
- What went smoother than expected
- What took longer / had surprises
- What I'd do differently next time (e.g., order of operations, tooling gaps)
**Then** the retrospective is committed to `docs/retrospectives/pve3-storage-migration-2026-04-Q2.md`
**And** durable memories are updated via `omega_store` or the memory file system:
- Target architecture (already done)
- Any new feedback memories (e.g., "always evacuate operator workbench first during node reinstalls")
- Project memory for the post-migration state

### Story 7.8: DHCP reservations for all PVE MACs on Asus router

As an operator,
I want pve1/pve2/pve3 MAC addresses bound to 192.168.50.201/202/203 respectively in the Asus router's DHCP reservation list,
So that any future reinstall automatically receives the correct IP regardless of which port or driver order the installer chose.

**Acceptance Criteria:**

**Given** the Asus router at 192.168.50.1 is the authoritative DHCP server
**When** I set `dhcp_staticlist` via nvram with the 3 PVE MACs bound to their canonical IPs:
- pve1: `00:d0:4c:10:40:54` → 192.168.50.201
- pve2: `00:d0:4c:10:41:d4` → 192.168.50.202
- pve3: `38:05:25:37:3d:cd` → 192.168.50.203
**Then** `/etc/dnsmasq.conf` on the router contains `dhcp-host=<MAC>,<IP>` lines for all 3
**And** future DHCP requests from each MAC receive the reserved IP
**And** the failure mode observed during Window B (install got 192.168.50.26 instead of .202 because no reservation existed) is prevented for future reinstalls

**Status:** done (2026-04-24). See `implementation-artifacts/window-b-complete-2026-04-24.md` §"Prevention for Epic 3".

### Story 7.9: Ansible pve-node-bootstrap playbook

As an operator,
I want a single Ansible playbook that takes a freshly-auto-installed PVE node and joins it to the existing cluster with correct /etc/hosts, SSH trust, and pvecm membership,
So that Epic 3 (pve3 rebuild) does not repeat Window B's 2 hours of manual recovery steps.

**Acceptance Criteria:**

**Given** a freshly auto-installed PVE node is reachable via its DHCP-reserved IP using the Ansible controller's bootstrap SSH key (installed via answer.toml `[first-boot]`)
**When** I run `ansible-playbook playbooks/pve-node-bootstrap.yml -l <node>`
**Then** `/etc/hosts` on the target contains entries for all cluster nodes at their canonical IPs
**And** `/etc/network/interfaces` has `bridge-ports` bound to the NIC with active link (auto-detected at runtime, not hardcoded)
**And** bidirectional SSH root-key trust is established between the new node and all existing cluster members
**And** `pvecm add --use_ssh --force <cluster-ip>` has executed and succeeded
**And** `pvecm status` on all 3 nodes reports 3/3 quorate
**And** the playbook is idempotent — re-running produces zero changes
**And** the playbook is documented in `homelab-infra/ansible/playbooks/README.md`
**And** a pve3-specific answer.toml (`pve3-answer.toml`) exists in `homelab-infra/proxmox/answer-files/` with:
- `disk-list` referencing NVMe drives by-id (serial-based), explicitly excluding the 5 HDDs
- `zfs.raid = "raid1"` + `zfs.hdsize = 828` to leave ~100 GB per drive for special-vdev partitions (per Story 3.2 AC)
- `[first-boot]` section installing the Ansible controller's bootstrap pubkey
**And** integration test: running the playbook against a test node (e.g., VM in dry-run) produces expected changes

**Status:** backlog. PREREQUISITE for Epic 3 Story 3.3. Estimated effort: 2–4 hours.

### Story 7.10: pve3 fixed VRAM BIOS configuration runbook

As an operator,
I want a documented runbook for configuring pve3's BIOS to allocate 24 GB fixed VRAM to the Radeon 890M iGPU,
So that when pve3 reboots (during Epic 3 reinstall or a planned maintenance window) I can correctly apply the fixed-VRAM setting and Ollama can reliably detect the iGPU.

**Acceptance Criteria:**

**Given** pve3 is the MinisForum N5 Pro with AMD Ryzen AI 9 HX PRO 370 and Radeon 890M iGPU
**When** I follow `implementation-artifacts/pve3-bios-vram-24gb-guide.md`
**Then** BIOS UMA Frame Buffer Size is set to 24 GB Fixed (not Dynamic/Auto)
**And** after boot, `dmesg | grep -i amdgpu` shows 24 GB allocated to the iGPU
**And** `cat /sys/class/drm/card0/device/mem_info_vram_total` reports ~25 769 803 776 bytes (24 GB)
**And** `free -h` reports host total ≈ 72 GB (96 minus 24 reserved)
**And** Ollama inside ct-ai-01 detects the iGPU (relevant to known Ollama issue #11451 with gfx1150 Dynamic VRAM)
**And** the guide covers: pre-boot checklist, BIOS key to press, exact menu path, setting name, verification commands, rollback procedure, troubleshooting
**And** the guide is referenced from Story 3.2 (reinstall runbook) and can be executed during the same reboot

**Status:** done (guide authored 2026-04-24). Execution pending — will be applied during Epic 3 Story 3.2 or a dedicated pve3 reboot window.

### Story 7.11: Alertmanager + self-hosted ntfy push channel

As an operator,
I want Prometheus alerts to push to my Android phone via self-hosted ntfy (routed through Alertmanager),
So that replication failures, zpool degradation, and other cluster incidents are seen within minutes rather than whenever I next open the Grafana dashboard.

**Context:** Story 6.2 delivered monitoring (metrics + alert rules + dashboard) but the adversarial review flagged that the notification chain is polling-only — operator must manually look at the dashboard to see alerts. For Epic 6 HA activation (Story 6.3+), a broken replica becomes catastrophic rather than merely a warning; push alerts are therefore a **gate** before 6.3.

**Acceptance Criteria:**

**Given** the existing observability stack on ct-docker-01 (192.168.50.194) running Prometheus + Grafana via docker-compose, and Traefik reverse-proxy in place
**When** I deploy Alertmanager + self-hosted ntfy to the observability stack
**Then** Alertmanager is reachable at `https://alertmanager.bi-services.be` (Authelia SSO-gated, same pattern as Grafana/Prometheus)
**And** ntfy is reachable at `https://ntfy.bi-services.be` (with an operator-auth protected topic `homelab-alerts`)
**And** Prometheus is configured to forward alerts to Alertmanager (via `alerting.alertmanagers` in prometheus.yml)
**And** Alertmanager has a `webhook_config` routing to ntfy with priority mapping:
- Prometheus `severity: critical` → ntfy priority `urgent` (bypasses phone's Do Not Disturb)
- Prometheus `severity: warning` → ntfy priority `default`
- Prometheus `severity: info` → ntfy priority `low`
**And** the 7 Prometheus alert rules from Story 6.2 are re-verified to emit the correct severity label (adjust if needed)
**And** the Android ntfy app (F-Droid or Play Store) is installed on operator's phone and subscribed to the `homelab-alerts` topic
**And** an end-to-end test fires a synthetic alert via `amtool alert add` or `curl http://alertmanager:9093/...`, phone receives the push within 60 seconds
**And** a "silence" workflow is documented — operator can mute alerts from Alertmanager UI during planned maintenance windows
**And** the `ha-replication-runbook.md` Monitoring section is updated: replace the "no push channel — must poll Grafana" note with "push alerts delivered via ntfy Android app on topic `homelab-alerts`"

**Out of scope / deferred:**
- Multi-device push (adding more phones/users) — future as-needed
- Slack/email/Teams routing — ntfy-only for now
- Alert grouping/inhibition rules beyond Alertmanager defaults — tune after first week of operation
- Silence integration with Ansible (e.g., automatic silence during role runs) — future story if repetitive

**Status:** backlog (blocks Story 6.3 HA group activation per adversarial review of Story 6.2)

**Effort estimate:** ~2 hours (ntfy + Alertmanager both small deployments; Traefik labels + DNS are already-established patterns; Prometheus/Alertmanager integration is well-documented)


### Story 7.12: Ansible-Vault secrets rendering for .env + Terraform

As an operator,
I want all cluster secrets stored once in the Ansible Vault (`group_vars/vault.yml`) and rendered into `.env` files + Terraform variables at deploy time,
So that secret rotation (Cloudflare token, ntfy password, PBS creds, etc.) is a single-file edit + `ansible-playbook` run, not an error-prone hunt across 3+ hand-edited files.

**Context:** Story 7.11 adversarial review (R4) surfaced that the Cloudflare token + ntfy password are scattered across 3 locations (infra-core/.env on CT101, terraform.tfvars, ntfy-password secret file) with no rotation playbook. When the Cloudflare token expired 2026-04-24, each consumer had to be found and updated individually. Ansible Vault already exists in the repo (`homelab-infra/ansible/inventories/homelab/group_vars/vault.yml`) but is under-used.

**Acceptance Criteria:**

**Given** the cluster's secrets live in multiple places (`.env` on various CTs, `terraform.tfvars`, password files)
**When** I store all secrets in `homelab-infra/ansible/inventories/homelab/group_vars/vault.yml` (encrypted) and write an Ansible playbook `playbooks/render-secrets.yml`
**Then** running `ansible-playbook playbooks/render-secrets.yml` (re)generates:
- `/opt/homelab-apps/stacks/infra-core/.env` on ct-docker-01 (with `CF_DNS_API_TOKEN` from vault)
- `/opt/homelab-apps/stacks/observability/.env` on ct-docker-01 (with ntfy password + any future secrets)
- `/opt/homelab-apps/stacks/observability/config/alertmanager/ntfy-password` on ct-docker-01 (600 perms)
- Optionally: `homelab-infra/terraform/envs/homelab/terraform.auto.tfvars.json` (git-ignored) with `cloudflare_api_token` from vault

**And** `terraform.tfvars` is removed from git (replaced by `.tfvars.example` template) — `.gitignore` covers `*.auto.tfvars.json`
**And** `.gitignore` also covers `**/.env`, `**/ntfy-password`, any other secret files
**And** rotation workflow documented: (1) edit `vault.yml`, (2) run `ansible-playbook playbooks/render-secrets.yml`, (3) restart affected containers, (4) test end-to-end
**And** an onboarding step is added to the top-level README: "To start from a fresh clone, you need the `vault_password` file (shared out-of-band) and run `render-secrets.yml` before `terraform apply`"
**And** a CI guardrail (Story 7.3 pattern) checks PRs don't commit secrets — a `pre-commit` hook or basic grep for known token prefixes (`cfut`, `sk-`, `AKIA`, etc.)

**Out of scope / deferred:**
- Migration to SOPS (alternative to Ansible Vault) — future consideration if Ansible Vault friction mounts
- HashiCorp Vault or other dedicated secret services — overkill for homelab scale
- Automatic secret rotation (auto-generate + push new CF token nightly) — manual rotation with this pattern is already good
- Secrets-at-rest encryption on the container filesystem beyond what docker-compose already does

**Status:** backlog. Not blocking Story 6.3. Nice-to-have cleanup after Epic 6 closes.

**Effort estimate:** ~2-3 hours — straightforward Ansible work, no new infrastructure.
