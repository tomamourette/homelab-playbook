---
stepsCompleted: ['step-01-init', 'step-02-technical-overview', 'step-03-integration-patterns', 'step-04-architectural-patterns', 'step-05-implementation-research', 'step-06-research-synthesis']
inputDocuments:
  - 'pve3:/etc/pve/storage.cfg'
  - 'pve3:zpool status'
  - 'pve3:lsblk / smartctl / dmidecode'
workflowType: 'research'
lastStep: 6
research_type: 'technical'
research_topic: 'PVE3 (MinisForum N5 Pro) storage architecture for a 3-node Proxmox cluster with HA requirements'
research_goals: 'Design a clean-slate storage layout across 3×1TB NVMe + 5×20TB HDD that (a) preserves bulk capacity, (b) eliminates the single-point-of-failure we previously hit where a container on pve3 shared NFS died when pve3 died, and (c) lets HA-critical containers live-migrate and fail over when any one node goes down.'
user_name: 'tomamourette'
date: '2026-04-20'
web_research_enabled: true
source_verification: true
---

# Research Report: PVE3 Storage Architecture

**Date:** 2026-04-20
**Author:** tomamourette
**Research Type:** technical (deep-dive)
**Node:** pve3 (MinisForum N5 Pro, 192.168.50.203)
**Cluster:** home-cluster (pve1, pve2, pve3)

---

## Executive Summary

**Recommended architecture on pve3:** three ZFS pools — a **2-way mirror `rpool`** (nvme0 + nvme1) for OS and HA-critical CT roots, a **single-disk `fast-pool`** (nvme2) for ephemeral/scratch, and a **RAIDZ1 `hdd-pool`** with a **mirrored metadata special vdev** (partitions on nvme0 + nvme1) for PBS, bulk NFS, and large read-mostly data. HA for containers is provided by **Proxmox Storage Replication + HA Manager**, *not* by keeping data on a single-node NFS share.

**What this fixes:** today, `shared-nfs` is a single-disk ZFS pool on pve3 exported as the *only* copy of ct-media-01's 354 GB media library. When pve3 goes down, that share disappears and every consumer breaks — the failure mode you described. The new design keeps HA-critical CT roots on locally-replicated `rpool` (independent copy on each node) and explicitly marks bulk NFS as non-HA.

**Hidden blocker uncovered during investigation:** pve1 and pve2 currently use **LVM-thin (`local-lvm`), not ZFS**. Replication requires ZFS on both sides. Fixing HA is therefore not only a pve3 rebuild — it also requires converting pve1 and pve2 to ZFS. The migration plan now addresses this.

**Headline numbers:**

| Pool | Node | Redundancy | Usable capacity | Role |
|------|------|------------|-----------------|------|
| `rpool` on pve3 | pve3 | 2-way NVMe mirror (survives 1 drive) | ~828 GB | OS + HA-critical CT roots |
| `hdd-pool` on pve3 | pve3 | RAIDZ1 + mirrored special vdev | ~72 TiB | PBS, bulk NFS, models, media |
| `fast-pool` on pve3 | pve3 | Single drive (no redundancy, by design) | ~928 GB | Ephemeral scratch only |
| `rpool` on pve1 | pve1 | Single NVMe (target of replication) | ~450 GB | Replication target for HA CTs |
| `rpool` on pve2 | pve2 | Single NVMe (target of replication) | ~900 GB | Replication target for HA CTs |

---

## 1. Research Overview & Methodology

**Approach:**
1. Inspect actual hardware on pve3 and surrounding cluster via SSH (block devices, ZFS pools, storage.cfg, network links, HA state, memory, cluster quorum).
2. Identify the root cause of the prior failure ("CT on pve3 shared storage died when pve3 went down").
3. Survey current (April 2026) best-practice guidance for Proxmox storage in three categories: ZFS replication+HA, Ceph, and NFS-HA (LINSTOR / pacemaker).
4. Evaluate each against the **real** topology (asymmetric nodes, 1 GbE, non-ECC DDR5, 3-node cluster).
5. Produce a concrete layout, implementation sequence, and risk register.

**Sources verified:** Proxmox VE docs, Proxmox support forum threads, Saturn ME architecture guides, TrueNAS ZFS references, practical ZFS community. See "Citations" at the end.

---

## 2. Verified Current State

### 2.1 pve3 hardware (ground truth, not spec-sheet)

| Component | Detail |
|-----------|--------|
| System | MinisForum N5 PRO, DDR5 **non-ECC**, 32 GB installed (~23 GB usable after iGPU reservation) |
| NVMe 0 | Samsung SSD 990 PRO 1 TB, `S6Z1NF0L202025D`, 0% used, 34 °C |
| NVMe 1 | Samsung SSD 990 PRO 1 TB, `S7HDNL0L322630L`, 0% used, 33 °C |
| NVMe 2 | Samsung SSD 990 PRO 1 TB, `S7HDNL0L323003J`, 0% used, 35 °C |
| HDD ×5 | WDC WD221PURP-85CJRY0 (Western Digital **Purple Pro** 22 TB / 20 TiB nominal), 7200 RPM, 3.5" SATA, surveillance/NVR-rated |
| NICs | `eno1` = Aquantia AQC113 10GBase-T (linked at **1 Gbps** because partner switch port is 1 G), `enp197s0` = Realtek RTL8126 5 GbE (DOWN), `enxa0c...` USB-Ethernet (DOWN) |
| pve1/pve2 NICs (peers) | 4× Intel I226-V each (CWWK CW-AD4L-N V1) — **2.5 GbE max natively, no 10 GbE without hardware additions** |

**⚠ Observations:**
- **Consumer NVMe without PLP** (power-loss protection). This limits SLOG value — see §4.3.
- **Non-ECC RAM.** Not a show-stopper for ZFS, but scrub alone cannot detect in-memory bit-flips. Mitigation: regular scrubs + off-node backups (which we have: PBS).
- **The 10 GbE port is bottlenecked by the switch.** eno1 negotiates 1 Gbps. This caps throughput to ~120 MB/s, which is fine for HA correctness and steady-state operations but slows initial full-sync and DR-restore scenarios. **Not a prerequisite** for the migration; upgrade whenever convenient. See §5 Phase 1 for details.

### 2.2 Current ZFS layout on pve3

```
rpool        (mirror: nvme0p3, nvme2p3)   928 GB, 38 GB used → / + CT160 (30 GB LLM) + CT162 (4 GB quant)
shared-pool  (single: nvme1)               928 GB, 353 GB used → /shared-pool/nfs (exported as shared-nfs)
```

Exported to cluster in `/etc/pve/storage.cfg` as:
- `local` — dir on `/var/lib/vz` (ISO/templates)
- `local-lvm` — orphan thin pool (unused; there is no LVM layout, safe to remove post-migration)
- `local-zfs` — `rpool/data` (currently hosts CT160, CT162)
- `shared-nfs` — NFS from `192.168.50.203:/shared-pool/nfs` (the SPOF)

### 2.3 Cluster topology & the HA problem

```
pve1 (192.168.50.201)  pve2 (192.168.50.202)  pve3 (192.168.50.203)
  500 GB Samsung 970     1 TB WD Black-ish      3×1 TB NVMe + 5×20 TB HDD
  local-lvm ONLY         local-lvm ONLY         rpool + shared-pool (ZFS)
  (NOT ZFS)              (NOT ZFS)                │
                                                  └── NFS export
                                                        │
                                                        └── mounted on pve1 as shared-nfs (media)
```

**Quorum:** 3/3 votes, quorate. HA manager is in watchdog-standby (armed). Cluster network is 1 GbE on all three nodes.

**Failure we hit:** a container's root disk lived on `shared-nfs`. When pve3 went down, the NFS export disappeared → the container could not start anywhere else in the cluster (pve2 or pve1), even though its *config* would have been picked up by the HA manager. The container's data only existed on pve3.

**The fundamental issues (two of them):**
1. `shared-nfs` is not *shared* in the HA sense — it is **single-sourced** from pve3. A shared-storage path for HA must tolerate the loss of the node that serves it.
2. pve1 and pve2 use **LVM-thin**, not ZFS. Proxmox's Storage Replication (the documented HA mechanism for asymmetric clusters) **requires ZFS on both source and target**. Today's cluster cannot do replication-based HA even in principle.

This means the HA story today is effectively: nothing. PBS backups are the only protection. Fixing HA requires solving both problems.

### 2.4 Complete running workload inventory (verified from `pct list` / `qm list` / configs)

**pve1 (Samsung 970 EVO Plus 500 GB, local-lvm):**

| ID | Type | Name | Root | Extra mounts | Managed by | HA need |
|----|------|------|------|--------------|------------|---------|
| 101 | LXC | ct-docker-01 | local-lvm 20G | — | Terraform | **High** — Docker host = homelab bootstrap |
| 102 | LXC | ct-media-01 | local-lvm 240G | mp0 → `shared-nfs/media` (354 GB) | Terraform | Med — downtime tolerable, data must survive |
| 104 | LXC | ct-zeroclaw-01 | local-lvm 4G | — | Manual | Low |
| 150 | LXC | ct-dev-homelab | local-lvm 50G (14 GB used) | — | Terraform | **Critical during migration** — this is the operator workbench (Claude Code / SSH sessions / local git checkout of homelab repo). Must not live on pve1 during Phase 6. |
| 100 | VM | smarthome | local-lvm 32G | **USB 10c4:ea60 (Zigbee)** | Manual | Pinned to pve1 by USB |
| 103 | VM | vm-haos-01 | local-lvm (iso-based) | — | Terraform | Med — Home Assistant |
| 999 | VM | ubuntu-dev-template | local-lvm 50G | — | Template | N/A |
| 9000 | VM | ubuntu-22.04-cloudimg | local-lvm 2G | — | Template | N/A |

**pve2 (WD SN770 ~1 TB, local-lvm):**

| ID | Type | Name | Root | Extra mounts | Managed by | HA need |
|----|------|------|------|--------------|------------|---------|
| 151 | LXC | ct-sparkle-cps | local-lvm 20G | — | Manual | Med — client project CPS-Fabric |
| 152 | LXC | ct-dev-test | local-lvm 15G | — | Terraform | Low — deliberately disposable |
| 153 | LXC | ct-isabelle | local-lvm 20G | — | Terraform | Med — project work |

**pve3 (3× NVMe + 5× HDD raw, ZFS):**

| ID | Type | Name | Root | Extra mounts | Managed by | HA need |
|----|------|------|------|--------------|------------|---------|
| 160 | LXC | ct-ai-01 | local-zfs 50G (30G used) | iGPU passthrough `/dev/dri` | Manual | Low-Med — LLM serving, **pinned to pve3 by GPU** |
| 162 | LXC | ct-quant-trading | local-zfs 50G (4G used) | — | Terraform | **High** — market hours uptime |

**Key pinning constraints (cannot freely migrate):**
- **VM 100 (smarthome)** — USB passthrough for Silicon Labs Zigbee (`10c4:ea60`). Lives where the USB stick lives (pve1).
- **CT 160 (ct-ai-01)** — iGPU passthrough (`/dev/dri`) for Ollama. Lives where the iGPU lives (pve3).
- Everything else is movable.

**Data inventory on pve3's `shared-pool/nfs` (must be preserved):**

```
/shared-pool/nfs/media/downloads   198 GB
/shared-pool/nfs/media/movies       47 GB
/shared-pool/nfs/media/tv          109 GB
/shared-pool/nfs/media/books         <1 MB (empty)
/shared-pool/nfs/media/music         <1 MB (empty)
/shared-pool/nfs/dump              empty
/shared-pool/nfs/images            empty
/shared-pool/nfs/private           empty
─────────────────────────────────────────
Total:                             ~354 GB   (all in media/)
```

**Consumer:** only ct-media-01 (pve1) mounts this. No VMs/CTs have root disks on shared-nfs. That simplifies the migration — we only need to preserve data, not virtualize live CT storage off the single-disk pool.

---

## 3. Options Considered (and why they were rejected)

The research goal is "best HA-compatible layout for 3 NVMe + 5 HDD on pve3 within a 3-node cluster." We evaluated every mainstream pattern, not just the obvious ones, because the HA failure mode is what hurt us before.

### 3.1 Ceph (hyper-converged RBD)

**Would it solve the HA problem?** Yes — true distributed block storage.

**Rejected because:**
1. **Massive storage asymmetry.** Ceph wants roughly equal capacity per node. We have 500 GB / 1 TB / ~100 TB — that is a ~200× imbalance. CRUSH maps would be pathological; any pool containing the HDDs would bottleneck on pve1/pve2 having nowhere to place the third replica. [Proxmox forum: "ensure that the total capacity presented per node is more or less the same"]
2. **3-OSD-per-node minimum.** pve1 and pve2 each have a single NVMe — partitioning them to reach 3 OSDs is a known anti-pattern (correlated failure = 1 disk).
3. **Network floor of 10 GbE for acceptable performance.** We are at 1 Gbps. Ceph's write path needs ACK from `replica_count` OSDs over the network — 1 GbE puts latency and throughput in unusable territory for VM workloads. [Saturn ME, Proxmox docs: "2.5 Gb is not recommended for Ceph in production"]
4. **3-node cluster is Ceph's *minimum*, not its sweet spot.** Community guidance from 2026 puts the break-even for Ceph over ZFS-replication at **5+ symmetric nodes**.
5. **Scrub/recovery on spinning disks** at this scale is brutal — a failed 20 TB OSD would rebuild for days, during which the cluster runs degraded.

**Verdict:** architecturally wrong fit, not just "pricey." Do not deploy Ceph on this topology.

### 3.2 TrueNAS VM as shared storage

**Would it solve HA?** No — same SPOF pattern. If the TrueNAS VM lives on pve3, losing pve3 kills the NAS. Running TrueNAS on a separate physical box would work but is outside the scope of this refactor (and introduces a new failure domain).

**Verdict:** does not address the problem. Skip.

### 3.3 LINSTOR + DRBD (block-level replicated shared storage)

**Would it solve HA?** Yes — DRBD replicates block devices synchronously between nodes; LINSTOR Gateway can float an NFS/iSCSI virtual IP across nodes.

**Rejected because:**
1. Operational complexity spike — pacemaker + DRBD + LINSTOR introduces three new moving parts to a homelab stack.
2. The HA-critical workload is small (CT162 = 4 GB, CT160 could be). Proxmox's built-in ZFS replication achieves ~the same RTO for a small LXC with ~1/10th of the config burden.
3. Synchronous DRBD over 1 GbE = latency-bound writes, same problem as Ceph.

**Verdict:** technically valid, overkill for the workload. Revisit only if the HA-critical footprint grows to dozens of VMs.

### 3.4 ZFS replication + PVE HA Manager ⭐ recommended

**Would it solve HA?** Yes, with a bounded RPO. Local ZFS pool on each node; Proxmox's built-in replication (`pvesr`) pushes incremental snapshots to peers; HA manager restarts the VM/CT on a peer if the primary is lost.

**How it handles our failure mode:** if pve3 dies, HA manager sees the `ha-group`-eligible CT on pve3, finds the latest replica on (e.g.) pve2, and starts the CT there from the replicated disk. No shared-storage dependency.

**Caveats — important for CT vs. VM:**
- For **VMs (KVM)**, replication + HA flips direction automatically — documented and supported.
- For **containers (LXC)**, the picture is nuanced. [Proxmox forum, 2025-26] The container will start on the replica node after failover, but the replication *direction* does not flip automatically back; a manual re-sync is needed after the original node returns. Newer PVE 8/9 versions have improved this, but it still requires a check. Plan for a post-failover manual step.
- **RPO = replication interval.** Default 15 min. Minimum supported is 1 min. At 1 min + our 1 GbE link, a 4 GB CT like quant-trading replicates its snapshot delta in a few seconds.
- **Storage must be named identically on all nodes** for replication to work. This is our first migration prerequisite.

**Verdict: primary recommendation.** Simple, documented, integrated in the GUI, zero extra software, plays nicely with our asymmetry (you replicate the *small* HA-critical CTs, not the HDD pool).

### 3.5 mdraid / LVM for HDDs

**Rejected because** we lose ZFS checksumming, snapshots, send/receive, compression, and special-vdev acceleration. No meaningful upside on modern Proxmox where ZFS is first-class. [Proxmox wiki: "ZFS is the recommended storage technology for Proxmox VE"]

### 3.6 RAIDZ1 vs striped mirrors for the 5×HDD pool

This is where your original question ("RAID 1 on the 5th disk"?) really sits. Let's work the numbers on the two defensible layouts for five disks:

| Layout | Usable | IOPS (write) | IOPS (read) | Redundancy | Resilver time @ 20 TB | Expansion |
|--------|--------|--------------|-------------|------------|------------------------|-----------|
| RAIDZ1 (1 vdev of 5) | ~72 TiB | ~1× single HDD (~150) | ~1× | Any 1 disk | Long (~1–2 days per disk) | Hard (add another full vdev) |
| Striped mirrors (2+2) + 1 hot spare | ~36 TiB | ~2× (~300) | ~4× (~600) | 1 from each mirror; 2 disks from the same mirror kills pool | Fast (~6–10 h) | Easy (add another mirror pair) |
| RAIDZ2 (1 vdev of 5) | ~54 TiB | ~1× | ~1× | Any 2 disks | Long | Hard |

**Matching the decision to the role.** The HDD pool in this design is **not** VM-hot storage — it's PBS + bulk NFS + LLM model library + quant historical data. Those are sequential-heavy workloads where RAIDZ1's IOPS ceiling barely matters. For sequential I/O, RAIDZ1 delivers 4× a single disk's throughput (4 data disks + 1 parity). The community consensus — *striped mirrors for VM/DB, RAIDZ for bulk* — aligns cleanly with what you want.

**On your "RAID 1 for the 5th disk" idea:** what you're intuiting is "don't leave the 5th disk unprotected." The correct expression of that intuition inside ZFS is either (a) **include the 5th disk as a hot spare** on the RAIDZ1 pool, or (b) accept it as part of RAIDZ1 where it contributes capacity *and* is covered by the single-parity guarantee. Having a hot spare costs you 20 TB of capacity but buys automatic replacement start-time when a disk drops. With only 5 disks, the usability math:

- **RAIDZ1 of all 5** → 72 TiB usable, 1-disk fault tolerance, no automatic replacement start
- **RAIDZ1 of 4 + 1 hot spare** → 54 TiB usable, 1-disk fault tolerance + automatic resilver kick-off, one-disk "budget" for a second failure during resilver if you're quick to notice
- **Striped mirrors 2+2 + 1 hot spare** → 36 TiB usable but survives two simultaneous failures *iff* they're in different mirrors

**Recommendation: RAIDZ1 across all 5 disks, monitor aggressively.** At 20 TB per disk you're near the edge of where RAIDZ1 is still a safe choice — URE math on large drives is not great. Mitigations:
1. Weekly scrubs (cron via `zfs-zed`).
2. Full SMART + email alerting.
3. PBS snapshot pruning policy that keeps off-pool copies (so a second failure during resilver is merely painful, not catastrophic).
4. Keep one 20 TB drive as a **cold spare** on the shelf (Purple Pros are readily available; having a physical unit ready beats waiting on Amazon mid-incident).

### 3.7 NVMe allocation (revised after review)

Three NVMe and two pools (rpool + HDD-pool helpers) means somewhere we have to compromise on either capacity, redundancy, or simplicity. The defensible patterns:

| Option | nvme0 | nvme1 | nvme2 | rpool usable | HDD metadata accel? | Redundancy |
|--------|-------|-------|-------|--------------|---------------------|-------------|
| A: 3-way mirror rpool | rpool | rpool | rpool | 928 GB | No | rpool: any 2 can fail |
| B: 2-way rpool + idle drive | rpool | rpool | (unused or single fast-pool) | 928 GB | No | rpool: 1 drive |
| C: 2-way rpool + L2ARC on nvme2 | rpool | rpool | L2ARC only | 928 GB | Read cache only (modest for sequential workload) | rpool: 1 drive; L2ARC loss is harmless |
| **D: Partitioned — rpool mirror + special mirror on nvme0+nvme1; fast-pool on nvme2** | rpool + special | rpool + special | fast-pool single | 828 GB | **Yes — mirrored metadata** | rpool: 1 drive; special: 1 drive; fast-pool: 0 (by design) |

**Recommendation after review: Option D.** The reasoning evolved from the initial "3-way mirror" recommendation for these reasons:

1. **The HDD pool's single biggest performance weakness is metadata latency.** PBS chunk GC, `ls` on million-file directories, `find` on bulk NFS — all metadata-heavy, all painful on pure HDD. Special vdev turns these from minutes into seconds. [Community consensus for PBS + HDD.](https://forum.proxmox.com/threads/pbs-and-zfs-special-allocation-class-vdev-aka-fusion-drive.148953/)
2. **Single-disk special vdev is a catastrophic SPOF** ("if the special vdev dies, the pool is gone"). Mirrored special vdev is mandatory. Partitioning nvme0+nvme1 to contribute 100 GB each to a special-mirror costs only 100 GB of rpool per drive.
3. **rpool's 2-way mirror is sufficient because replication protects it at the cluster level.** Losing both nvme0 and nvme1 on pve3 means reinstalling pve3 — but the HA-critical CTs are already replicated to pve1 and pve2 and will be running there. This is precisely the scenario replication exists for.
4. **nvme2 as a single-disk `fast-pool` gives real operational value** — see §4.5 for per-CT usage. It's opt-in: ephemeral workloads get fast NVMe; nothing that matters goes there.
5. **SLOG/L2ARC on nvme2 both rejected:** SLOG wants PLP (Samsung 990 Pro has none), and modern guidance is that the risk rarely pays off for consumer drives ([NVMe SLOG without PLP](https://www.truenas.com/community/threads/nvme-slog-without-plp-power-loss-protection-mitigation.87708/)). L2ARC for sequential-heavy bulk workload is a weak win and costs ~1.6 GB ARC RAM per 1 TB cache — on a 23 GB-usable box we keep ARC for ARC.

### 3.8 The "special vdev is a SPOF" rule (must-understand)

| Vdev type | What it does | If it dies |
|-----------|--------------|-----------|
| L2ARC (cache) | Read cache beyond ARC | ✅ ZFS forgets cache. No data loss. |
| SLOG (log) | Accelerates sync writes | ⚠️ Up to ~5 sec sync writes can be lost. Pool continues. |
| Special (metadata) | Stores metadata + small files | 🔥 **Entire pool is dead.** Must mirror. |

Option D uses `special` in a mirrored configuration (nvme0p3 + nvme1p3), so any single-drive failure leaves the pool intact.

---

## 4. Recommended Architecture (Clean-Slate Rebuild)

### 4.1 pve3 storage layout (Option D — partitioned hybrid)

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                   pve3                                         ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║                                                                                ║
║   Per-NVMe partition table:                                                   ║
║     nvme0n1:  [1 GB EFI] [828 GB rpool-part]  [100 GB special-part]           ║
║     nvme1n1:  [1 GB EFI] [828 GB rpool-part]  [100 GB special-part]           ║
║     nvme2n1:  [whole disk: fast-pool, ~928 GB, NO redundancy]                 ║
║                                                                                ║
║   ┌──────────────────────────────────────────────────────────┐                ║
║   │ rpool (2-way mirror)                    usable: ~828 GB  │                ║
║   │  └── mirror-0: nvme0n1p2 + nvme1n1p2                     │                ║
║   │  Datasets:                                               │                ║
║   │    rpool/ROOT/pve-1      — Proxmox OS                    │                ║
║   │    rpool/data/subvol-162-disk-0   — ct-quant-trading     │                ║
║   │    rpool/data/subvol-160-disk-0   — ct-ai-01 (root only) │                ║
║   └──────────────────────────────────────────────────────────┘                ║
║                                                                                ║
║   ┌──────────────────────────────────────────────────────────┐                ║
║   │ hdd-pool (RAIDZ1 + mirrored special)  usable: ~72 TiB    │                ║
║   │  ├── raidz1-0: sda + sdb + sdc + sdd + sde (22 TB each)  │                ║
║   │  └── special:  mirror(nvme0n1p3, nvme1n1p3) — 100 GB     │                ║
║   │  Datasets:                                               │                ║
║   │    hdd-pool/pbs          — PBS datastore                 │                ║
║   │    hdd-pool/bulk         — NFS root (shared-nfs-bulk)    │                ║
║   │      hdd-pool/bulk/media     — the 354 GB media library  │                ║
║   │      hdd-pool/bulk/downloads                             │                ║
║   │      hdd-pool/bulk/movies, tv, books, music              │                ║
║   │      hdd-pool/bulk/dump, images, private                 │                ║
║   │    hdd-pool/models       — LLM model cache (ct-ai-01)    │                ║
║   │    hdd-pool/quant-history — cold quant data              │                ║
║   └──────────────────────────────────────────────────────────┘                ║
║                                                                                ║
║   ┌──────────────────────────────────────────────────────────┐                ║
║   │ fast-pool (single disk)                 usable: ~928 GB  │                ║
║   │  └── nvme2n1 (whole disk)                                │                ║
║   │  NO redundancy. Contents MUST be rebuildable.            │                ║
║   │  Datasets (created on-demand per CT):                    │                ║
║   │    fast-pool/scratch      — shared scratch               │                ║
║   │    fast-pool/<ct-name>    — per-CT ephemeral mount point │                ║
║   └──────────────────────────────────────────────────────────┘                ║
║                                                                                ║
║   Cold spare (shelf): 1× WD Purple Pro 22 TB (order before rebuild)           ║
╚════════════════════════════════════════════════════════════════════════════════╝
```

**Key design property — fault tolerance matrix:**

| Failure | rpool | hdd-pool | fast-pool | Cluster impact |
|---------|-------|----------|-----------|----------------|
| nvme0 or nvme1 dies | Degraded (1 mirror leg) | Degraded (1 special leg) | Unaffected | Replace drive, resilver |
| nvme2 dies | Unaffected | Unaffected | **Lost** | Ephemeral workloads restart; rebuildable |
| 1 HDD dies | Unaffected | Degraded (RAIDZ1 tolerates 1) | Unaffected | Replace drive, resilver |
| nvme0 + nvme1 both die | **Dead** — reinstall pve3 | **Dead** — pool lost | Unaffected | HA CTs continue on pve1/pve2 (replicated) |
| 2 HDDs die simultaneously | Unaffected | **Dead — data loss** | Unaffected | Restore from PBS (off-pool) |

The bottom row (2 HDDs dying at once during resilver) is the headline residual risk — see §7. Mitigations: weekly scrubs, cold spare, PBS off-node backup chain.

### 4.2 ZFS properties (defaults we're overriding)

**rpool** (OS + HA CT roots — prioritise safety and lz4 compression):
```
compression=lz4                  # fast, always-on, saves ~30% on CT roots
atime=off                        # reduce metadata writes
xattr=sa                         # efficient xattrs for Proxmox
recordsize=128K  (default)       # fine for mixed CT/VM
redundant_metadata=most (default)
```

**hdd-pool** (bulk — prioritise throughput and capacity):
```
compression=zstd-3               # better ratio than lz4, CPU budget is ample
atime=off
xattr=sa
recordsize=1M                    # big blocks for media/models/PBS chunks
redundant_metadata=most
autotrim=off                     # HDDs don't TRIM
```

**hdd-pool/pbs** (PBS datastore specifically):
```
recordsize=128K                  # PBS chunks are ~4 MiB but access is random-ish
compression=off                  # PBS chunks are already compressed
```

**hdd-pool/bulk** (NFS export):
```
sync=standard                    # keep correctness; accept the write penalty
                                 # (we rejected SLOG for reasons in §3.7)
```

### 4.3 Non-HA vs HA storage classification (the critical distinction)

| Storage | Reachable when pve3 is down? | Used for |
|---------|------------------------------|----------|
| rpool on pve3 | No (but **data is replicated** to pve1/pve2 rpools → HA-manager restarts on peer) | HA-critical CTs/VMs |
| hdd-pool on pve3 via `shared-nfs-bulk` | **No.** Explicitly non-HA. | Bulk data, backups, media, models. If pve3 is down, backups pause — this is **acceptable** and documented. |

**This is the design principle that fixes the original incident:** never place an HA-critical CT's root disk on a single-node NFS export. The NFS export is for data that can tolerate pve3's absence.

### 4.4 Cluster-wide HA strategy

1. **Convert pve1 and pve2 from LVM-thin to ZFS.** This is the gated prerequisite; without it, replication is impossible.
   - pve1: single NVMe (500 GB) → `rpool` single-disk ZFS (no mirror possible with one drive). Acceptable as replication target since data also exists on pve3 + pve2.
   - pve2: single NVMe (1 TB) → same pattern.
   - **Storage IDs must match exactly on all 3 nodes.** All three expose `local-zfs` → `rpool/data`.
2. **Enable Proxmox Storage Replication** (GUI: Datacenter → Replication).
   - See per-CT matrix in §4.5 below for which workloads get replicated and at what interval.
3. **Define HA groups and policies.**
   - `ha-group: critical` → members [pve2, pve1, pve3] → for CT162 (quant-trading).
   - `ha-group: pinned-pve1` → restricted:1, nodes [pve1] → for VM100 (USB Zigbee).
   - `ha-group: pinned-pve3` → restricted:1, nodes [pve3] → for CT160 (iGPU).
   - `ha-group: standard` → members [pve1, pve2, pve3] → default for movable work.
4. **Arm HA manager + fencing.** Current state: `fencing standby (CRM watchdog standby)`. Keep watchdog fencing — Proxmox default, works on this hardware.
5. **Verify by deliberate pull-the-plug tests** (§6 validation plan).

### 4.5 Per-CT storage placement & HA plan (the full matrix)

This is the canonical answer to "what should every workload do in the new world." Produced by walking every CT/VM in the cluster and applying the §3 decision rubric.

**Legend:**
- **Root placement:** where the rootfs/bootdisk disk should live
- **Replicate to:** nodes that receive ZFS replicated snapshots (for HA)
- **HA group:** Proxmox HA manager group assignment
- **Extra mounts:** additional mount points and their placement

| ID | Name | Root placement | Extra mounts | HA group | Replicate to | Notes |
|----|------|----------------|--------------|----------|--------------|-------|
| **pve1 workloads** |
| 101 | ct-docker-01 | pve1:`local-zfs` | — | `standard` (prefers pve1) | pve2, pve3 @ 5 min | Bootstrap container; replicating both ways insures against pve1 loss |
| 102 | ct-media-01 | pve1:`local-zfs` 240G | mp0 → `shared-nfs-bulk/media` (NFS, from pve3 hdd-pool) | `standard` (prefers pve1) | pve2 @ 15 min | Root replicates cheap (240 GB over 15 min) but **media data does NOT** — it lives on hdd-pool; if pve3 is down, media is unreachable. Acceptable: the *library* is non-HA. |
| 104 | ct-zeroclaw-01 | pve1:`fast-pool-local`* | — | none | none | Tiny and disposable; see note below about pve1's lack of a fast-pool |
| 150 | ct-dev-homelab | **pve3 during migration**; pve1 after | — | `standard` (prefers pve3 or pve1) | pve1 + pve2 @ 15 min | **Operator workbench.** Holds the live git checkout of the homelab repo, SSH keys, Terraform state, and any in-progress work. Must be on a node that is NOT currently being reinstalled. Post-migration, it can live on either pve1 or pve3 with replication to the other. |
| 100 | VM smarthome | pve1:`local-zfs` | USB passthrough (Silicon Labs Zigbee) | `pinned-pve1` | none (can't — USB pins it) | **Pinned**: can only run on pve1. PBS backups are the sole protection. |
| 103 | VM vm-haos-01 | pve1:`local-zfs` | — | `standard` | pve2 @ 15 min | Home Assistant. Replicate to pve2 for HA. |
| 999 | ubuntu-dev-template | pve1:`local-zfs` (template) | — | N/A | N/A | Stopped template |
| 9000 | ubuntu-22.04-cloudimg | pve1:`local-zfs` (template) | — | N/A | N/A | Stopped template |
| **pve2 workloads** |
| 151 | ct-sparkle-cps | pve2:`local-zfs` | — | `standard` | pve1, pve3 @ 5 min | Client project — deserves multi-target replication |
| 152 | ct-dev-test | pve2:`local-zfs` | — | none | none | Deliberately disposable per feedback memory ("Deploy to ct-dev-test before ct-dev-homelab") |
| 153 | ct-isabelle | pve2:`local-zfs` | — | `standard` | pve1 @ 5 min | Project work |
| **pve3 workloads** |
| 160 | ct-ai-01 | pve3:`local-zfs` (rpool) 50G | mp0 → `hdd-pool/models` (Ollama model files) | `pinned-pve3` | pve2 @ 30 min (root only) | **Pinned by iGPU**. Model files live on hdd-pool (bulk, ~tens of GB, not worth replicating). Root replication preserves config. |
| 162 | ct-quant-trading | pve3:`local-zfs` (rpool) 50G | — | `critical` | pve1, pve2 @ 1 min | Highest-priority HA target. 1-min RPO over 10 GbE is seconds. |

*Note on `fast-pool-local` on pve1/pve2:* neither of those nodes has a spare NVMe to dedicate as fast-pool. Only pve3 has a true scratch tier. Entries marked `fast-pool-local` for pve1/pve2 should be read as "on local-zfs, with the operator understanding it's treated as disposable" — the storage *role* maps to concept-of-scratch rather than a separate physical pool. If pve1 or pve2 ever gets a second NVMe, they can get real fast-pools; until then, rpool is the only choice.

**Replication totals (back-of-envelope network cost):**
- CT101, CT102 (root), CT151, CT153 → ~300 GB combined, replicated with cadences 5–15 min. At 1 Gbps this is easy (delta snapshots are ~MBs).
- CT162 @ 1 min → tiny deltas (4 GB rootfs, idle → ~KBs per cycle).
- CT160 @ 30 min → 50 GB rootfs, delta mostly small.
- VM103 (HAOS) @ 15 min → similar.

Total cluster replication traffic: manageable on 1 Gbps; becomes instant on 10 GbE.

### 4.6 NFS export migration (preserving the 354 GB media data)

**Goal:** transform `192.168.50.203:/shared-pool/nfs` (from single-disk ZFS on nvme1) into `192.168.50.203:/hdd-pool/bulk` (from the new RAIDZ1 + special-mirror) **without downloading 354 GB again**.

**Data map (source → target):**

| Source (pve3 nvme1 — current) | Target (pve3 hdd-pool — new) | Size |
|-------------------------------|------------------------------|------|
| `/shared-pool/nfs/media/movies` | `/hdd-pool/bulk/media/movies` | 47 GB |
| `/shared-pool/nfs/media/tv` | `/hdd-pool/bulk/media/tv` | 109 GB |
| `/shared-pool/nfs/media/downloads` | `/hdd-pool/bulk/media/downloads` | 198 GB |
| `/shared-pool/nfs/media/books` | `/hdd-pool/bulk/media/books` | <1 MB |
| `/shared-pool/nfs/media/music` | `/hdd-pool/bulk/media/music` | <1 MB |
| `/shared-pool/nfs/dump` | `/hdd-pool/bulk/dump` | empty |
| `/shared-pool/nfs/images` | `/hdd-pool/bulk/images` | empty |
| `/shared-pool/nfs/private` | `/hdd-pool/bulk/private` | empty |

**Preservation mechanic:** the key insight is that **the HDDs are brand new and empty**. We can create `hdd-pool` *first*, copy data from `shared-pool` to `hdd-pool`, **then** rebuild the NVMe layout. At no point does the 354 GB leave pve3 or need to be re-downloaded.

**Copy method:** `zfs send | zfs recv` for correctness and speed, not `rsync`. This preserves snapshots and is much faster than file-level copy:

```bash
# On pve3, snapshot the existing single-disk pool
zfs snapshot -r shared-pool@pre-migration

# Replicate into the new hdd-pool (bulk dataset as recv target)
zfs send -R shared-pool@pre-migration \
  | zfs recv -F hdd-pool/bulk-staging

# Rename into place (after validation)
zfs rename hdd-pool/bulk-staging/nfs hdd-pool/bulk
```

Estimated transfer time: 354 GB / (HDD RAIDZ1 sequential write ~400 MB/s, but bottlenecked by source being single NVMe at ~1.5 GB/s read) = **~15–20 minutes**.

**NFS cutover:**
1. Stop ct-media-01 (pve1) to release the NFS mount cleanly.
2. In pve3 `/etc/pve/storage.cfg`: remove `shared-nfs` entry; add `shared-nfs-bulk` pointing to the new export path.
3. Export `/hdd-pool/bulk` via NFS (update `/etc/exports`).
4. Update ct-media-01's `mp0` line: `mp0: /mnt/pve/shared-nfs-bulk/media,mp=/media,replicate=0,shared=1`.
5. Start ct-media-01; verify `ls /media` shows the movies/tv/downloads tree intact.
6. After 48 h of clean operation, destroy `shared-pool` (the original single-disk pool on nvme1). nvme1 is now free for its new role as part of the 2-way rpool mirror + special mirror.

**Rollback:** if the cutover fails, `shared-pool` is not destroyed until step 6. Revert ct-media-01's mp0 line to the old path and restart.

---

## 5. Implementation Plan (Migration Sequence)

**Goal:** zero-data-loss transition from today (LVM-thin on pve1/pve2, SPOF NFS on pve3) to the target architecture (ZFS on all 3 nodes, replicated HA, new pve3 layout with preserved media).

**Guiding principles:**
- The cluster maintains quorum at all times (2/3 nodes always up).
- The 354 GB media never leaves pve3 and is never re-downloaded.
- Every CT/VM has a known-good PBS backup before its node is touched.
- Each phase is individually revertible.

### Phase 0 — Preparation (no changes to cluster; do first)

| # | Action |
|---|--------|
| 0.1 | **Order 1× cold-spare WD Purple Pro 22 TB** — put on shelf, label with date |
| 0.2 | **Commit current state snapshot** to `homelab-playbook/_bmad-output/pre-migration-snapshot-2026-04-20/` (all `/etc/pve/*`, `zpool status`, `lsblk`, `pct list`, `qm list`) |
| 0.3 | **Set up a dedicated PBS datastore** — if not already present, create one (even temporarily on pve1's local-lvm or an external disk) for migration backups. Critical: do **not** rely only on the current PBS if it lives on pve3 since pve3 is being rebuilt. |
| 0.4 | **Full PBS backup of every CT and VM**, in the priority order: CT162, CT160, CT102, VM100, VM103, CT101, CT151, CT153, CT104, **CT150 (operator workbench)**, CT152. Verify one restore (CT152, the disposable one) end-to-end. |
| 0.5 | **Document the 354 GB media checksum inventory:** `cd /shared-pool/nfs/media && find . -type f -exec sha256sum {} + > /tmp/media-manifest-pre.txt` on pve3. Copy off-node. You'll verify against this after migration. |
| 0.6 | **Confirm switch upgrade path for Phase 1** — check which switch ports are 2.5/10 GbE. |
| 0.7 | **Protect the operator workbench (CT150 ct-dev-homelab).** From inside CT150: commit and push ALL work in `/home/developer/workspace/homelab` to origin. Confirm no unpushed commits: `git status` clean, `git log origin/main..HEAD` empty. Run PBS backup of CT150 as final step. This ensures that if the workbench is lost mid-migration, nothing in-flight is gone. |
| 0.8 | **Set up a fallback management path.** Ensure SSH-from-laptop works directly to pve1/pve2/pve3 (not just through CT150). If SSH keys live only in CT150, export them somewhere else first. This is your escape hatch if the workbench migration fails. |

### Phase 1 — Network upgrade (OPTIONAL — can be deferred)

**Hardware reality check (verified 2026-04-20):**
- **pve1 & pve2** — CWWK CW-AD4L-N V1 mini-PCs with 4× Intel I226-V NICs. **Max 2.5 GbE natively.** 10 GbE would require M.2-to-PCIe expansion or hardware replacement.
- **pve3** — MinisForum N5 Pro with 1× Aquantia AQC113 (10 GbE) + 1× Realtek RTL8126 (5 GbE). Currently negotiating 1 Gbps due to switch.

**The cluster is therefore a 2.5 GbE-capable cluster at the bottleneck (pve1/pve2).** Any pve3↔pve1/2 replication is capped at 2.5 GbE regardless of pve3's 10 GbE.

**Reclassification:** 1 GbE is sufficient for correctness, HA mechanics, and steady-state replication. The 10 GbE NIC on pve3 auto-negotiates with whatever switch port it's plugged into, so a later switch upgrade requires **zero Proxmox reconfiguration**. Skipping this phase does not block any later phase.

**Three-tier network roadmap:**

| Tier | What's needed | Cluster link speed | Effort |
|------|---------------|--------------------|--------|
| Tier 0 (now) | No change | 1 GbE | — |
| Tier 1 (low effort, recommended soon) | 2.5 GbE-capable switch (~$80-150 home-grade, ~$300 managed) | 2.5 GbE cluster-wide | Just plug in the new switch; auto-negotiation handles the rest |
| Tier 2 (only if justified) | M.2 → PCIe 10 GbE adapter on pve2 (and maybe pve1), 10 GbE switch/direct cable | 10 GbE on selected links | Hardware mod + cable routing |

**What 1 GbE is fine for:**
- Corosync / quorum (tiny bandwidth, low-latency on LAN switches = ✅)
- HA failover at the moment of node loss (uses already-replicated data; no transfer needed)
- Steady-state ZFS replication (delta snapshots are KB-to-MB sized for your workloads)
- NFS media streaming (1 GbE handles ~12 parallel 4K streams)
- Routine PBS incremental backups

**What 1 GbE makes slower (but does not break):**
- Initial full-sync of replication jobs (one-time ~50 min instead of ~5 min across the whole cluster)
- Live migration of large (100 GB+) CTs during planned maintenance
- Full-disk PBS restore (DR-RTO scenario: ~2 h instead of ~12 min per TB)

**Decision: Defer network upgrade.** Proceed through Phases 2–9 at 1 GbE. Schedule the initial replication sync (Phase 8.1) during an off-peak window.

**If/when you do upgrade later:**
| # | Action |
|---|--------|
| 1.1 | Move pve3's eno1 cable to a 10 GbE (or 2.5 GbE) switch port; auto-negotiation handles the rest |
| 1.2 | Verify: `ethtool eno1 \| grep Speed` returns ≥2500 Mb/s |
| 1.3 | If pve1/pve2 have spare 2.5 GbE NICs, move their cluster uplinks onto faster switch ports |
| 1.4 | Consider enabling `enp197s0` (pve3's 5 GbE port) as a dedicated corosync ring for quorum resilience (optional, cheap, improves HA robustness under network saturation) |

### Phase 2 — pve3 HDD pool first (unlocks the media move)

The HDDs are currently empty. We can build `hdd-pool` without touching any existing data.

| # | Action |
|---|--------|
| 2.1 | Identify all 5 HDDs by `/dev/disk/by-id/…` (not `/dev/sda` — letters can shuffle): `ls -l /dev/disk/by-id/ \| grep WD221PURP` |
| 2.2 | Create `hdd-pool` with RAIDZ1, **without** special vdev yet (NVMe is still busy): `zpool create -o ashift=12 -O compression=zstd-3 -O atime=off -O xattr=sa hdd-pool raidz1 <by-id-1> ... <by-id-5>` |
| 2.3 | Create datasets: `zfs create hdd-pool/pbs`, `zfs create hdd-pool/bulk`, `zfs create hdd-pool/models`, `zfs create hdd-pool/quant-history` |
| 2.4 | Set recordsize for bulk media: `zfs set recordsize=1M hdd-pool/bulk` |

### Phase 3 — Media data migration (pve3, using `zfs send | recv`)

| # | Action |
|---|--------|
| 3.1 | `zfs snapshot -r shared-pool@pre-migration` |
| 3.2 | `zfs send -R shared-pool@pre-migration \| pv \| zfs recv -F hdd-pool/bulk-staging` (estimate 15–20 min; `pv` gives a progress bar) |
| 3.3 | Verify byte-for-byte: `cd /hdd-pool/bulk-staging/nfs/media && find . -type f -exec sha256sum {} + > /tmp/media-manifest-post.txt && diff /tmp/media-manifest-pre.txt /tmp/media-manifest-post.txt` → must be empty |
| 3.4 | Promote the staging dataset into final position: `zfs rename hdd-pool/bulk-staging/nfs hdd-pool/bulk` (after destroying the empty `hdd-pool/bulk` placeholder created in Phase 2) |
| 3.5 | Set recordsize on `hdd-pool/bulk` = 1M (if not already inherited) |

### Phase 4 — NFS cutover (swap from old path to new, ct-media-01 downtime ~2 min)

| # | Action |
|---|--------|
| 4.1 | On pve1: stop ct-media-01 (`pct stop 102`) |
| 4.2 | On pve3: update `/etc/exports` — remove old path, add `/hdd-pool/bulk 192.168.50.0/24(rw,no_subtree_check,no_root_squash)`; `exportfs -ra` |
| 4.3 | On pve3 Proxmox: edit `/etc/pve/storage.cfg` — add new storage `shared-nfs-bulk` pointing to `192.168.50.203:/hdd-pool/bulk`. Keep `shared-nfs` entry temporarily for rollback. |
| 4.4 | On pve1: update `/etc/pve/lxc/102.conf` `mp0:` line to reference `/mnt/pve/shared-nfs-bulk/media` |
| 4.5 | `pct start 102`; verify `pct exec 102 -- ls -la /media/movies \| head` shows the expected titles |
| 4.6 | Exercise via the actual consumers — Jellyfin/Plex/whatever ct-media-01 runs — play back a video to confirm read path works |
| 4.7 | **Wait 48 h** under real-world usage before Phase 5 |

### Phase 5 — pve3 NVMe rebuild (the hard phase)

Now `shared-pool` (on nvme1) can be destroyed and the NVMe layout rebuilt.

**Pre-flight:**
- CT160 and CT162 must be temporarily evacuated since rpool will be destroyed
- Live-migrate CT162 to pve2 *(pve2 still on LVM at this point — use offline migration; CT162 rootfs = 4 GB used, fast)*
- CT160 cannot migrate (iGPU-pinned to pve3) — stop it; accept the downtime for the duration of Phase 5

| # | Action |
|---|--------|
| 5.1 | `pct migrate 162 pve2` (offline; will use local-lvm on pve2 temporarily) |
| 5.2 | `pct stop 160`; verify PBS backup from Phase 0.4 exists and is recent |
| 5.3 | Reboot pve3 off a Proxmox 9 install USB |
| 5.4 | In installer: manual partition — all 3 NVMes — per §4.1 layout. Use "ZFS (RAID1 / mirror)" for rpool across nvme0p2+nvme1p2. EFI mirrored on all three drives. |
| 5.5 | First boot: verify `zpool status rpool` = ONLINE, mirror-0 of two partitions |
| 5.6 | Re-add pve3 to the cluster (`pvecm add <pve1-ip>`) |
| 5.7 | Destroy the old `shared-pool` (it no longer exists after reinstall, but verify nvme1 is clean) |
| 5.8 | Add the mirrored special vdev to `hdd-pool`: `zpool add hdd-pool special mirror /dev/disk/by-id/nvme-...-part3 /dev/disk/by-id/nvme-...-part3` (the p3 partitions on nvme0 and nvme1) |
| 5.9 | Configure `special_small_blocks` on `hdd-pool/pbs` to route small files to special: `zfs set special_small_blocks=128K hdd-pool/pbs` (only for the datasets that benefit — PBS and metadata-heavy; leave bulk at 0) |
| 5.10 | Create `fast-pool`: `zpool create -o ashift=12 -O compression=lz4 -O atime=off fast-pool /dev/disk/by-id/nvme-...-nvme2n1` |
| 5.11 | Restore NFS export (same `/etc/exports` as before); Proxmox storage config (same `storage.cfg` additions). Media is back online. |
| 5.12 | Restore CT160 from PBS to new `local-zfs` on pve3 |
| 5.13 | Add `hdd-pool/models` mount point to CT160 config; copy Ollama models from old location (if they were on rpool) to `hdd-pool/models`, update Ollama config to point there |
| 5.14 | Live-migrate CT162 back to pve3 (target storage `local-zfs`) |
| 5.15 | Validate §6 items V1, V2, V7 at this point |

### Phase 5.5 — Evacuate the operator workbench (CT150) to pve3

**Why this is its own phase:** CT150 ct-dev-homelab is where the operator (you, right now) runs this migration from. It holds the live git checkout, SSH sessions, any terminal state, and Claude Code context. If it vanishes during Phase 6's pve1 reinstall, the migration is blind-piloted from that moment on.

| # | Action |
|---|--------|
| 5.5.1 | From inside CT150: final commit + push of any in-flight work. `git status` must be clean. |
| 5.5.2 | Take a fresh PBS backup of CT150 (supersedes the one from Phase 0.4 with any late work). |
| 5.5.3 | Restore CT150 from PBS to pve3 (`pct restore 150 <backup> --storage local-zfs --target pve3`). **Do not delete the original on pve1 yet** — it stays as a fallback. Use a different VMID (e.g. 250) for the restore if PVE balks at duplicates, then rename later. |
| 5.5.4 | Reconnect your SSH / Claude Code session to the CT150 instance now running on pve3. Confirm the working directory (`/home/developer/workspace/homelab`), git state, and SSH keys are all intact. |
| 5.5.5 | Verify you can still SSH to all 3 pve nodes from the pve3-resident CT150. |
| 5.5.6 | Only after the pve3-resident CT150 is confirmed functional, proceed to Phase 6. |

### Phase 6 — pve1 LVM-to-ZFS conversion

pve1 has a single 500 GB NVMe. Its CTs must move off first. **CT150 must already be on pve3 per Phase 5.5 before starting this phase.**

| # | Action |
|---|--------|
| 6.1 | **Evacuate pve1 CTs temporarily to pve2 and pve3 via PBS restore:** |
|     | • VM100 (smarthome, USB-pinned) → **cannot move**; accept downtime for the duration of Phase 6 |
|     | • VM103 (HAOS) → restore from PBS to pve2 |
|     | • CT101 (docker-host) → restore from PBS to pve3 (on the new rpool) |
|     | • CT102 (media) → restore from PBS to pve3 (the media NFS mount still works cross-node; **update its `mp0` to reference `shared-nfs-bulk` not `shared-nfs`**) |
|     | • CT104 → restore to pve2 |
|     | • CT150 — **already on pve3 from Phase 5.5**; nothing to do here |
| 6.2 | Stop VM100; note its config |
| 6.3 | Reboot pve1 off Proxmox install USB |
| 6.4 | Install with "ZFS (RAID0 / single-disk)" on the 500 GB NVMe. Re-join cluster. |
| 6.5 | Verify `zpool status rpool` ONLINE; storage ID `local-zfs` present in `storage.cfg` |
| 6.6 | Restore VM100 to pve1 from PBS |
| 6.7 | Move other CTs/VMs back to pve1 as needed (per §4.5 matrix) via live migration or PBS restore — this time target `local-zfs` |
| 6.8 | **Decide where CT150 lives long-term:** either migrate it back to pve1 and set up replication to pve3 (pve1 primary, pve3 replica) OR keep it on pve3 long-term with replication to pve1 (pve3 primary, pve1 replica). The latter is slightly safer given pve3's more resilient storage. |
| 6.9 | Update Terraform: `terraform.tfvars` for pve1 CTs change `storage` from `local-lvm` to `local-zfs` |

### Phase 7 — pve2 LVM-to-ZFS conversion

Same pattern as Phase 6, on the 1 TB NVMe.

| # | Action |
|---|--------|
| 7.1 | Evacuate CT151, CT152, CT153 to pve1 or pve3 |
| 7.2 | Reinstall pve2 with ZFS (RAID0 / single-disk) |
| 7.3 | Re-join cluster; restore CTs |
| 7.4 | Update Terraform |

### Phase 8 — Replication + HA wiring

| # | Action |
|---|--------|
| 8.1 | Datacenter → Replication: create replication jobs per §4.5 matrix (CT162 @ 1 min to pve1+pve2; CT160 root @ 30 min to pve2; CT101 → pve2+pve3; CT102 root → pve2; etc) |
| 8.2 | Wait for first replication cycle of each job; verify `pvesr status` shows `OK` with recent timestamp |
| 8.3 | Create HA groups per §4.4 (`critical`, `standard`, `pinned-pve1`, `pinned-pve3`) |
| 8.4 | Assign CTs/VMs to HA groups |
| 8.5 | Run §6 validation items V3–V6 |

### Phase 9 — Decommission + Terraform/Ansible codification

| # | Action |
|---|--------|
| 9.1 | Remove old `shared-nfs` storage entry from `storage.cfg` on all nodes (after 1 week of `shared-nfs-bulk` working cleanly) |
| 9.2 | Update `homelab-infra/terraform/modules/ct-debian/variables.tf` default storage from `local-lvm` to `local-zfs` |
| 9.3 | Update `homelab-infra/terraform/envs/homelab/terraform.tfvars` — the commented-out `vm_storage = "local-lvm"` line should become `vm_storage = "local-zfs"` |
| 9.4 | Add Ansible role for pve3's `hdd-pool` / NFS export configuration under `homelab-infra/ansible/roles/pve-host-pve3/` (node-specific because only pve3 has HDDs) |
| 9.5 | Update `docs/architecture-homelab-infra.md` to reflect the new storage topology (you already have uncommitted changes staged there) |
| 9.6 | Add the §4.5 per-CT placement matrix as canonical documentation in `homelab-infra/docs/` or `docs/storage-placement-rules.md` |
| 9.7 | Add the Ansible guardrail that fails CI when an HA CT targets non-replicable storage (see §8.3) |

---

## 6. Validation Plan (the cluster is not "done" until these pass)

| # | Test | Expected result |
|---|------|-----------------|
| V1 | `zpool status rpool` on pve3 | `state: ONLINE`, 3-way mirror, 0 errors |
| V2 | `zpool status hdd-pool` on pve3 | `state: ONLINE`, raidz1-0 of 5 disks, 0 errors |
| V3 | `pvesr status` shows CT162 replicated to pve1 and pve2 within last 1 min | Last sync < 60 s old |
| V4 | **Failover drill:** `qm/pct set` CT162 to migrated state, then `qm/pct stop pve3` via IPMI-pull. HA manager should restart CT162 on pve2. | CT162 online on pve2 within ~2 min; `pct exec 162 -- uptime` < 2 min elapsed |
| V5 | Pull-plug drill (pve3 hard reset): pve3 absent, CT162 running on pve2, `shared-nfs-bulk` unreachable (expected), HA-critical services OK. | pve2/pve1 operational, non-HA NFS gracefully degraded, no stale mounts |
| V6 | Post-recovery: pve3 boots → replication direction re-establishes → CT162 live-migrates back to pve3 if HA group prefers it. | `pvesr status` clean within 5 min |
| V7 | Scrub: `zpool scrub hdd-pool` completes | 0 errors |
| V8 | PBS backup of CT162 succeeds and restore works end-to-end | Restore within RTO target |

---

## 7. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| HDD URE during RAIDZ1 resilver (2nd-disk failure scenario) | Low-Med (20 TB drives) | High (pool loss) | Weekly scrubs, SMART alerts, cold spare on shelf, PBS off-node backup chain |
| Special vdev mirror: both legs fail simultaneously | Very low (independent NVMe) | **Catastrophic — hdd-pool is dead** | 2-way mirror is the mitigation; monitor `Percentage Used` on nvme0 & nvme1; consider upgrading one to enterprise PLP NVMe when budget allows |
| Operator puts important data on `fast-pool` by mistake | Med (easy human error) | Med-High (data loss on nvme2 failure) | Clear naming; §4.5 matrix is canonical; proposed Ansible guardrail (§9.7) |
| ZFS replication drift for LXC (direction-flip edge cases) | Med | Low-Med (manual re-sync post-failover) | Document post-failover runbook step; monitor `pvesr status` |
| Non-ECC memory corrupts data | Very Low | High | Regular scrubs, PBS backups, accept as known residual |
| Consumer NVMe wearout on shared special/rpool drives | Low (0% used today) | Med | Monitor SMART `Percentage Used`; 990 Pro has ~1200 TBW endurance; expect ~5-year lifespan at homelab write rates |
| I/O contention on nvme0/nvme1 (rpool + special on same physical device) | Med | Low (minor latency spikes) | Monitor; acceptable at homelab load; if it becomes a real issue, upgrade one NVMe to PLP-equipped enterprise |
| Network bottleneck at 1 GbE on pve3 uplink | High (present today) | **Low** during normal operation; Med during initial migration/DR | Not blocking — HA mechanics and steady-state replication are fine at 1 GbE. Upgrade whenever budget allows (Phase 1 is optional). |
| Mixed-use of `shared-nfs-bulk` accidentally hosting HA workload | Med (bad operator habit) | High (repeats the original incident) | Rename to make non-HA nature explicit; Ansible pre-commit check (§9.7) |
| Cluster quorum loss during Phase 5/6/7 (node reinstall) | Low | High (2-node quorum required) | Only one node down at a time; verify `pvecm status` Quorate before each phase; don't schedule during any other maintenance |
| PBS datastore location during migration | **Operational gotcha** | High if ignored | PBS datastore **cannot live on pve3** during pve3 reinstall; set up a temporary datastore on pve1 or an external drive for the migration window |
| Media verification drift (checksum diff post-migration) | Low | Med (would indicate real corruption) | Phase 3.3 diff must be empty before declaring phase complete; if it isn't, rollback and investigate |
| VM100 (smarthome) downtime during pve1 rebuild | Certain | Low (home automation pause) | Communicate planned downtime to household; keep rebuild window short |
| CT160 (ct-ai-01) downtime during pve3 rebuild | Certain | Low (LLM offline) | Schedule pve3 rebuild window; LLM is not mission-critical |
| **CT150 (operator workbench) lost during pve1 reinstall** | Med (if Phase 5.5 skipped) | **High — migration becomes blind** | Phase 5.5 is the mitigation: evacuate CT150 to pve3 BEFORE starting Phase 6. Phase 0.7 pre-commit requirement is a secondary mitigation. Fallback SSH path (Phase 0.8) is the tertiary mitigation. |
| Uncommitted work on CT150 lost if the fallback PBS restore is needed | Low (if Phase 0.7 done) | Med (lost work, recovery effort) | Phase 0.7 pre-flight: commit + push everything before touching pve1 |

---

## 8. Open Questions (for follow-up)

1. **Is the switch port for pve3 upgradable to 10 GbE today?** If not, what's the plan? (Enterprise switch with SFP+? MikroTik CRS? Direct peer-to-peer on the 5 GbE ports as cluster private network?)
2. **Should we add a dedicated cluster-network on `enp197s0` (5 GbE)** as Corosync's redundant ring? Would harden quorum against vmbr0 outages.
3. **Do we want to keep ct-quant-trading on pve3** (stated role: HA, close to LLM/GPU path?), or does its HA-criticality warrant pve2 as primary with replication to pve3?
4. **PBS instance placement** — keep inside pve3, or run PBS in its own LXC replicated across nodes? Current gist is "PBS datastore on hdd-pool/pbs" — PBS the service itself can be local to pve3.

---

## 9. Decision Summary (for the runbook)

| Question | Answer |
|----------|--------|
| pve3 NVMe layout | **2-way mirror `rpool` (nvme0 + nvme1 partitioned), single-disk `fast-pool` (nvme2)** |
| pve3 HDD layout | **RAIDZ1 across all 5 × 20 TB + mirrored metadata special vdev** (100 GB partitions on nvme0 + nvme1) |
| Why not 3-way mirror? | Replication already protects HA-critical data at the cluster level; freeing a drive for fast-pool gives real scratch value, and partitioning nvme0/nvme1 gives hdd-pool its metadata accelerator |
| Why not SLOG/L2ARC? | Consumer 990 Pro has no PLP (SLOG risky); workload is sequential-heavy (L2ARC weak); RAM better spent on ARC |
| pve1 & pve2 storage? | **Reinstall with ZFS (single-disk)** — LVM-thin is a hard blocker for replication |
| Ceph? | **No** — asymmetric + 1 GbE + 3 nodes = wrong fit |
| How is HA provided? | **ZFS replication + PVE HA Manager** across all 3 nodes with matching `local-zfs` storage IDs |
| What lives on NFS? | **Only non-HA bulk data** (media, downloads, dump, images); renamed to `shared-nfs-bulk` to signal intent |
| How is the 354 GB media preserved? | `zfs send \| zfs recv` from `shared-pool` → `hdd-pool/bulk` before destroying the old pool; never leaves pve3 |
| Cold spare? | **Yes, one 22 TB Purple Pro** on the shelf |
| Network prerequisite? | **None — 1 GbE is sufficient for correctness and HA.** Upgrade to ≥2.5 GbE is a nice-to-have for faster initial syncs and DR; can be deferred indefinitely. |
| Where does each CT live? | See §4.5 per-CT placement matrix — canonical |
| Full migration order | Prep → (optional Network) → HDD pool → Media migration → NFS cutover → pve3 rebuild → **Evacuate CT150 workbench to pve3** → pve1 rebuild → pve2 rebuild → Replication/HA → Terraform codification (Phases 0–9 in §5) |
| Operator workbench protection | CT150 ct-dev-homelab must be on pve3 before Phase 6 starts (Phase 5.5). All work must be committed + pushed before Phase 6. Fallback SSH from laptop must be verified working (Phase 0.8). |
| Guardrail to prevent the original incident again | CI check: any CT with `ha=1` using `fast-pool` or `shared-nfs-bulk` must fail (§9.7) |

---

## 10. Citations

### Proxmox (official)
- [ZFS on Linux — Proxmox VE Wiki](https://pve.proxmox.com/wiki/ZFS_on_Linux)
- [Storage Replication — Proxmox VE Wiki](https://pve.proxmox.com/wiki/Storage_Replication)
- [Deploy Hyper-Converged Ceph Cluster — Proxmox VE Wiki](https://pve.proxmox.com/wiki/Deploy_Hyper-Converged_Ceph_Cluster)
- [Proxmox Backup Server — Storage](https://pbs.proxmox.com/docs/storage.html)

### Architecture / decision guides (2025–26)
- [Best Storage Setup for 3-Node and 4-Node Proxmox Clusters (Ceph, ZFS, TrueNAS) — Saturn ME](https://www.saturnme.com/best-storage-setup-for-3-node-and-4-node-proxmox-ve-clusters-ceph-zfs-and-truenas-compared/)
- [Choosing Between Ceph and ZFS for Storage in Proxmox — Saturn ME](https://www.saturnme.com/choosing-between-ceph-and-zfs-for-storage-in-proxmox/)
- [ZFS RAID Options in Proxmox VE 9 — Saturn ME](https://www.saturnme.com/understanding-zfs-raid-levels-in-proxmox-ve/)
- [Proxmox Storage Architecture on Bare Metal: Ceph vs. ZFS Decision Guide — OpenMetal](https://openmetal.io/resources/blog/proxmox-storage-architecture-on-bare-metal-ceph-vs-zfs-decision-guide/)
- [Proxmox VE Storage Options: ZFS, LVM-Thin, Ceph, NFS Compared — SelfHostWise](https://selfhostwise.com/posts/proxmox-ve-storage-options-zfs-lvm-thin-ceph-and-nfs-compared/)

### Forum threads (community evidence)
- [For Best Performance — Proxmox Cluster with CEPH or ZFS? — Level1Techs](https://forum.level1techs.com/t/for-best-performance-proxmox-cluster-with-ceph-or-zfs/198627)
- [HA Best Practice — Proxmox Forum](https://forum.proxmox.com/threads/ha-best-practice.157253/)
- [High Availability with local ZFS storage — Proxmox Forum](https://forum.proxmox.com/threads/high-availability-with-local-zfs-storage.122922/)
- [Considering a 3-node cluster with ZFS replication — Proxmox Forum](https://forum.proxmox.com/threads/considering-building-a-proxmox-3-node-cluster-with-zfs-replication.173274/)
- [Understanding CEPH in a 3 Node Cluster with 12 OSDs — Proxmox Forum](https://forum.proxmox.com/threads/understanding-ceph-in-a-3-node-cluster-with-12-osds.161734/)
- [FabU: Can I use ZFS RaidZ for my VMs? — Proxmox Forum](https://forum.proxmox.com/threads/fabu-can-i-use-zfs-raidz-for-my-vms.159923/)
- [ZFS Special VDEV — Proxmox Forum](https://forum.proxmox.com/threads/zfs-special-vdev.159907/)
- [Minisforum N5 Pro on Proxmox — Proxmox Forum](https://forum.proxmox.com/threads/minisforums-nas-n5-pro.166323/)

### ZFS deep reference
- [ZFS sync/async + ZIL/SLOG, explained — JRS Systems](https://jrs-s.net/2019/05/02/zfs-sync-async-zil-slog/)
- [ZFS ZIL and SLOG — TrueNAS Documentation](https://www.truenas.com/docs/references/zilandslog/)
- [ZFS using SATA SSD as SLOG: The Cheap Upgrade That Often Fails — cr0x.net](https://cr0x.net/en/zfs-sata-ssd-slog-fails/)
- [Three-site Proxmox + ZFS layout sanity check — Practical ZFS](https://discourse.practicalzfs.com/t/three-site-proxmox-zfs-15x16-tb-site-special-vdev-pbs-encrypted-off-site-layout-sanity-check-best-practice-questions/2727)

### ZFS + non-ECC RAM
- [Proxmox, non-ECC memory, ZFS or not? — Proxmox Forum](https://forum.proxmox.com/threads/proxmox-non-ecc-memory-zfs-or-not.132892/)
- [ZFS, Non-ECC RAM, and Kernel Panics: Can Your Homelab Survive? — Medium](https://medium.com/@PlanB./zfs-non-ecc-ram-and-kernel-panics-can-your-homelab-survive-b4b585717a0a)

### N5 Pro hardware reference
- [Minisforum N5 Pro AI NAS — product](https://store.minisforum.com/products/minisforum-n5-pro-ai-nas)
- [Minisforum N5 Pro Review — ServeTheHome](https://www.servethehome.com/minisforum-n5-pro-review-an-awesome-nas-platform/3/)
- [Minisforum N5 Pro Small NAS in Hand — Level1Techs](https://forum.level1techs.com/t/minisforum-n5-pro-small-nas-in-hand/237601)

### HA NFS alternatives
- [Highly Available NFS for Proxmox With LINSTOR Gateway — LINBIT](https://linbit.com/blog/highly-available-nfs-for-proxmox-with-linstor-gateway/)
- [HA NFS service for KVM VMs on a Proxmox Cluster with Ceph — Proxmox Forum](https://forum.proxmox.com/threads/ha-nfs-service-for-kvm-vms-on-a-proxmox-cluster-with-ceph.80967/)

---

*Research conducted 2026-04-20 by direct inspection of pve3 + cluster state and web-sourced 2025/26 best-practice guidance. Ready for review.*
