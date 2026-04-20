---
status: done
epic: 1
story: 1.4
title: Capture pre-migration state snapshot
---

# Story 1.4: Capture pre-migration state snapshot

## User Story

As an operator,
I want a dated, read-only snapshot of every cluster/node/guest configuration,
So that I have an authoritative reference to diff against after pve3 is rebuilt,
and can detect unexpected drift at a glance.

## Acceptance Criteria

**Given** Epic 1 is about to run (pve3 will be destructively reinstalled in Epic 3)
**When** I capture the current state of the cluster
**Then** the snapshot contains:
- Per-node `zpool status`, `zfs list -t all`, `pct list`, `qm list` from all three nodes
- Per-node `/etc/pve/lxc/*.conf` and `/etc/pve/qemu-server/*.conf` dumps
- Per-node `ip link` + `ethtool <iface>` for each ethernet interface
- Per-node LVM layout (`lvs`, `vgs`, `pvs`) and PVE version
- Cluster-wide `/etc/pve/storage.cfg`, `pvecm status/nodes`, `/etc/pve/corosync.conf`, `ha-manager status`
**And** the snapshot is written to `homelab-playbook/_bmad-output/implementation-artifacts/pre-migration-snapshot-2026-04-20/` under per-node subdirectories
**And** a README explains what the snapshot is, how to diff against a future state, and what is NOT captured

## Tasks

- [x] Create target directory tree (`cluster/`, `pve1/`, `pve2/`, `pve3/`) with per-node `lxc/`, `qemu-server/` subdirs
- [x] Verify SSH connectivity to pve1, pve2, pve3 from the workbench
- [x] Collect per-node snapshot for pve1 (23 files)
- [x] Collect per-node snapshot for pve2 (23 files)
- [x] Collect per-node snapshot for pve3 (22 files — only 3 ethtool ifaces vs 4 on pve1 and 4 on pve2)
- [x] Collect cluster-wide configs from pve3 (storage.cfg, pvecm status/nodes, corosync.conf, ha-manager status)
- [x] Author README inside snapshot dir (≤30 lines) explaining purpose, scope, what's NOT captured, and how to diff
- [x] Author story spec artifact at `_bmad-output/implementation-artifacts/1-4-capture-pre-migration-state-snapshot.md`
- [ ] Commit to git (deferred — director handles commits after review)
- [ ] Push to origin (deferred — director handles pushes after review)

## Dev Notes

### Why a snapshot (and not just "rely on backups")

PBS backups (Story 1.3) capture guest *contents*. They do NOT capture
host-level cluster topology: network interface names and speeds,
LVM thin-pool layout on pve1/pve2, cluster-wide `storage.cfg` entries,
corosync ring config, or the per-node `pveversion`. If pve3 comes up with
subtly different interface names, a different `rpool` feature flag set,
or a missing storage.cfg entry, PBS restore alone would not catch it.
This snapshot is the ground-truth reference for `diff -r` post-migration.

### What the snapshot shows (facts captured 2026-04-20)

- **Cluster:** PVE 9.1.7 / kernel 6.17.13-2-pve on all three nodes. Corosync
  cluster `home-cluster`, config version 5, quorate with 3 nodes.
- **pve1:** 4 ethernet ifaces (enp2s0–enp5s0, enp2s0 active at 1 Gbps).
  LVM-only (no ZFS). Hosts CT101 (docker), CT102 (media), CT104 (zeroclaw),
  CT150 (dev-homelab).
- **pve2:** 4 ethernet ifaces (enp1s0–enp4s0). LVM-only. Hosts CT105
  (pbs-migration from Story 1.2), CT151 (sparkle-cps, currently mid-backup),
  CT152 (dev-test), CT153 (isabelle).
- **pve3:** 3 ethernet ifaces (eno1, enp197s0, enxa0cec87fcb8b — USB
  eth adapter). ZFS-only (`rpool` ONLINE, `shared-pool` for NFS export).
  Hosts CT160 (ai-01 with iGPU passthrough), CT162 (quant-trading, currently
  mid-backup).
- **Storage.cfg (cluster-wide):** `local` (dir), `local-lvm` (lvmthin on
  pve1/pve2), `local-zfs` (zfspool on pve3), `shared-nfs` (nfs server
  192.168.50.203), `pbs-migration` (from Story 1.2).

### Minor collection notes

- **pve3 ethtool enp197s0** — emits "netlink error: No such device" lines
  at top because the interface is present but unplugged. Captured anyway
  (`Link detected: no`) — useful baseline.
- **pve3 lvs.txt is empty** — pve3 has no LVM volume groups (ZFS-only).
  Empty file is the correct captured state.
- **pve1 & pve2 zpool-status.txt** contain the literal string
  `no pools available` — expected; both nodes are LVM-only. Kept as
  explicit evidence rather than absent files, so diffs can detect
  "wait, why does pve1 have a zpool now?" unambiguously.
- **CT151 and CT162 show `backup` lock state** in `pct list` — they were
  mid-backup when the snapshot ran (Story 1.3 full-cluster PBS job
  running concurrently). This is noise in the `Lock` column only; the
  rest of the config is stable because PBS uses ZFS/LVM snapshots.

### Scope boundaries (also in README)

Not captured: live guest data (PBS covers that), secrets
(`/root/.pbs-migration-credentials` on pve2 stays out of git),
`authorized_keys` / SSH host keys (out of scope — would force a re-trust
workflow on restore which is the wrong pattern).

## Implementation Report

- **Target directory:** `/home/developer/workspace/homelab/homelab-playbook/_bmad-output/implementation-artifacts/pre-migration-snapshot-2026-04-20/`
- **Total files captured:** 68 (including README.md)
- **Total size:** 78,974 bytes (~77 KiB, 280 KiB disk usage)
- **Per-node breakdown:** pve1 = 23 files, pve2 = 23 files, pve3 = 22 files (one fewer ethtool iface), cluster = 5 files, root = 1 (README)
- **Collection errors:** zero fatal errors. Two cosmetic notes: (1) pve3 ethtool on unplugged USB adapter emits netlink errors in stderr (captured in the file, non-blocking), (2) pve3 has an empty `lvs.txt` because it's ZFS-only (correct captured state).
- **Collection method:** SSH from operator workbench to each node, read-only commands only (`hostname`, `uname`, `zpool status`, `zfs list`, `pct list`, `qm list`, `cat /etc/pve/{lxc,qemu-server}/*.conf`, `ip -br link/addr`, `ethtool`, `lvs/vgs/pvs`, `pveversion`, `pvesm status`). Cluster configs pulled from pve3 (any node works — pmxcfs replicates).
- **README authored** at snapshot-dir root (28 lines) — explains purpose, scope, not-captured, and how to diff.
- **No commits made** (director handles git commit + push after review per Story 1.2/1.3 pattern).
