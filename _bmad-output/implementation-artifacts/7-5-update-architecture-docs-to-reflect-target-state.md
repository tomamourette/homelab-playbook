---
status: review
epic: 7
story: 7.5
title: Update architecture docs to reflect current target state
---

# Story 7.5: Update architecture docs to reflect current target state

## User Story

As an operator returning to the homelab after an absence (or onboarding a new collaborator), I want `docs/architecture-homelab-infra.md` to reflect the **current target state** of the cluster — all-ZFS on PVE 9.1, pve3 Option D storage layout, Epic 6.1/6.2 replication + monitoring landed, HA explicitly deferred — so that the architecture doc is a usable ground truth rather than a lagging artifact.

## Acceptance Criteria

**Given** the cluster as of 2026-04-24 has landed:
- Epic 5 (all 3 nodes reinstalled onto ZFS mirrors / ZFS pools, no LVM anywhere)
- Epic 3 (pve3 Option D: rpool + fast-pool + hdd-pool w/ mirrored special vdev)
- Epic 2 Story 2.10 (PBS on pve3 at `/hdd-pool/pbs`)
- Story 6.1 (8 replication jobs) + Story 6.2 (textfile exporter + alerts + dashboard)
- Stories 7.1, 7.3, 7.4, 7.8, 7.9 (automation hardening)

**When** an operator reads `docs/architecture-homelab-infra.md`,

**Then** the document must:
1. State PVE version as 9.1 and root FS as ZFS on all 3 nodes.
2. Show the correct per-node hardware (CWWK pve1/2 with 16 GB + ZFS mirror; N5 Pro pve3 with 96 GB, 3× NVMe, 5× 22 TB HDD).
3. Document the full pve3 Option D pool layout (rpool, fast-pool, hdd-pool + special vdev + special_small_blocks).
4. Show the real workload placement (CT101/102 + VM100 on pve1; CT151 on pve2; CT160/162/250 on pve3).
5. Document `shared-nfs-bulk` NFS export + CT102 bind-mount.
6. Document the cluster-wide `pve3-pbs` datastore + CT160 safety-net backup.
7. Document Story 6.1 replication jobs table + Story 6.2 alerts + Grafana dashboard name.
8. Include an HA section that is **explicitly a placeholder** — naming what is pending (6.3/6.4/6.5-6.8/6.9) and deferring canonical HA docs to Story 6.9. No HA group names or RTO/RPO numbers may be stated.
9. Document the known gaps: Alertmanager pending, 2nd corosync ring pending, VM100 Zigbee failover untested, CT160 ollama model path cosmetic.
10. Document the Epic 7 automation story outputs (pve-host-pve3-storage role, pve-node-bootstrap playbook, CI guardrail, Terraform default flip, DHCP MAC pinning).

**And** the document must NOT commit to git (human review first — status `review`).

## Tasks

- [x] Read current `docs/architecture-homelab-infra.md` (342 lines, dated 2026-04-22) to understand baseline structure.
- [x] Update header: bump `Last updated:` to 2026-04-24 with provenance note (Epic 5 + Epic 3 + Story 6.1/6.2).
- [x] Rewrite **Executive Summary** to reflect PVE 9.1 + all-ZFS + 6 production CTs + 1 HAOS VM + 1 conditional dev VM.
- [x] Bump **Technology Stack** table: Proxmox VE 9.1, add ZFS-on-root row, add PBS row.
- [x] Add new **Cluster Hardware** section with per-node hardware table (CWWK vs N5 Pro).
- [x] Add new **pve3 Storage Architecture (Option D)** subsection with pool table and iGPU UMA allocation note.
- [x] Add new **Workload Placement** subsection listing current CT/VM → node mapping.
- [x] Rewrite the **Containers** canonical table (drop deprecated entries like CT104/CT150/CT152/CT153, add CT250, correct CT150 → CT250).
- [x] Rewrite **Virtual Machines** table: VM100 (smarthome, live) + VM200 (dev_vm, conditional). Drop the "CT103 vm-haos-01 disabled" framing.
- [x] Add new **Shared Storage (NFS)** section documenting pve3 export + CT102 bind-mount.
- [x] Add new **Backups (PBS)** section documenting pve3-pbs datastore + special vdev rationale + CT160 safety-net backup.
- [x] Add new **Replication & Monitoring (Story 6.1 + 6.2)** section with full 8-job replication table + 4 alert names + Grafana dashboard name + Alertmanager-pending note.
- [x] Add new **HA — Section Pending Epic 6 Closure** placeholder section with explicit cross-link to Story 6.9 and enumeration of what is deferred.
- [x] Add new **Known Gaps & Followups** section: Alertmanager, 2nd corosync ring, Ollama path cosmetic, VM100 Zigbee failover untested, vm-haos Terraform resource disabled, local TF state.
- [x] Add new **Automation & Reproducibility (Epic 7)** section naming Stories 7.1, 7.3, 7.4, 7.8, 7.9 and what each codifies.
- [x] Update **ct-debian module** section: note `local-zfs` as new default (Story 7.4).
- [x] Update **Host-Level Tuning** targets to include pve3 (not just pve1, pve2).
- [x] Add `pve-host-pve3-storage` to the Ansible roles table.
- [x] Update **Network Architecture** ASCII diagram to show current per-node CT/VM placement + DHCP-pinned IPs note + pending 2nd corosync ring.
- [x] Update **CI/CD Patterns** section to include the Story 7.3 HA-storage guardrail.
- [x] Update **SSH Access** table: correct pve3 RAM (96 GB, not 28 GB) + note `ha` is VM100.
- [x] Update **AI Services** section: mention the 32 GB UMA Frame Buffer allocation.
- [x] Rewrite **Known Limitations** section to reflect current state (vm-haos resource disabled, not CT; HA not yet live with cross-reference).
- [x] Create this story file with `status: review`.
- [x] Do NOT git-commit.

## Dev Notes

Facts added to the document (delta from the 2026-04-22 version):

**Cluster-wide:**
- PVE version bumped 8.4 → 9.1.
- All 3 nodes on ZFS (no LVM anywhere) called out explicitly and repeatedly.
- DHCP reservations pin PVE MACs → canonical IPs (Story 7.8).

**Per-node hardware:**
- pve1: CWWK CW-AD4L-N V1, 1× 16 GB DDR5, 2× Samsung 990 PRO 1TB ZFS mirror rpool (Story 5.13).
- pve2: CWWK equivalent, 1× 16 GB DDR5, 2× Samsung 990 PRO 1TB ZFS mirror rpool (Window B).
- pve3: MinisForum N5 Pro, 2× 48 GB DDR5 = 96 GB dual-channel (previously stated as 28 GB), 3× Samsung 990 PRO 1TB + 5× 22 TB WD Purple Pro, active-cooled.

**pve3 Option D storage:**
- rpool 2-way mirror on nvme0p3 + nvme2p3 (824 GB usable).
- fast-pool single-disk on nvme1n1 (928 GB, ephemeral).
- hdd-pool RAIDZ1 on 5× 22 TB WD Purple Pro + mirrored special vdev on nvme0p4 + nvme2p4 (103 GB each).
- special_small_blocks=128K on hdd-pool/pbs.
- 32 GB UMA Frame Buffer to Radeon 890M iGPU (BIOS Fixed mode).

**Workloads:**
- pve1: CT101 ct-docker-01, CT102 ct-media-01, VM100 smarthome (HAOS + Zigbee USB passthrough).
- pve2: CT151 ct-sparkle-cps.
- pve3: CT160 ct-ai-01 (iGPU-pinned), CT162 ct-quant-trading, CT250 ct-dev-homelab.

**Shared storage / backup:**
- pve3 exports /hdd-pool/bulk as `shared-nfs-bulk`.
- CT102 bind-mounts /mnt/pve/shared-nfs-bulk/media → /media.
- PBS on pve3 at /hdd-pool/pbs, registered as `pve3-pbs` storage cluster-wide.
- CT160 pre-Epic-3 safety-net backup preserved.

**Epic 6 (landed portion):**
- 8 replication jobs (VM100, CT101, CT162, CT250 × 2 targets each), `*/15` or `*/30`, `-rate 50` MB/s.
- Textfile exporter + 4 alerts (`PVEReplicationFailing`, `PVEReplicationStale`, `PVEReplicationExporterStale`, `PVEReplicationSnapshotOrphan`).
- Grafana dashboard `ha-replication-6-2`.

**HA explicitly deferred (placeholder section):**
- HA groups + members → Story 6.3.
- Guest tagging → Story 6.4.
- 2nd corosync ring → prereq of Story 6.3.
- RTO/RPO drill results → Stories 6.5–6.8.
- Canonical failover runbook → Story 6.9.

**Known gaps:**
- Alertmanager not yet stood up (alerts fire to Prometheus `/alerts` only).
- Ollama models path on CT160 is cosmetic non-issue.
- VM100 Zigbee USB failover untested — Story 6.5.

**Automation (Epic 7):**
- `pve-host-pve3-storage` role (Story 7.1).
- `pve-node-bootstrap.yml` playbook (Story 7.9).
- CI guardrail blocks HA CTs on non-replicable storage (Story 7.3).
- Terraform module default flipped to `local-zfs` (Story 7.4).
- DHCP MAC pinning (Story 7.8).

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2026-04-24 | 0.1 | Full rewrite of `docs/architecture-homelab-infra.md` to reflect cluster target state post-Epic-5 + post-Epic-3 + Story 6.1/6.2. HA section intentionally left as placeholder pending Story 6.9. | SM+Dev (Claude) |
