---
date: 2026-04-24
session: Epic 5 Window B pve2 NVMe swap + reinstall + return-migration (COMPLETE)
relates-to: pve1-swap-complete-2026-04-22.md, pve2-solo-nvme-replacement-runbook.md (draft), media-recordsize-rewrite-2026-04-22.md
---

# pve2 Window B — COMPLETE

pve2's WD_BLACK SN850X has been replaced with 2× Samsung 990 PRO 1TB in a ZFS RAID1 mirror. Proxmox VE 9.1.1 reinstalled, node rejoined cluster, CT151 migrated back. In parallel: RAM redistributed across cluster, heat pads installed on pve1 + pve3 existing NVMes, Story 5.13 (pve1 2-way rpool mirror) completed.

## Final cluster state (2026-04-24 post-migration)

**pve1** (single-chassis NVMe mirror, 16 GB RAM):
- 2× Samsung 990 PRO 1TB in rpool ZFS mirror (added Story 5.13)
- 1× 16 GB DDR5 (single-channel — accepted trade-off)
- CT101 ct-docker-01 — running
- CT102 ct-media-01 — running (`/media` bind-mounted from `shared-nfs-bulk` on pve3)
- VM100 smarthome — running (HAOS with Zigbee USB passthrough)
- Templates 999, 9000 — stopped

**pve2** (fresh install, 16 GB RAM):
- 2× Samsung 990 PRO 1TB in rpool ZFS mirror (auto-installer RAID1)
- 1× 16 GB DDR5 (single-channel)
- CT151 ct-sparkle-cps — running, migrated back in 61 s

**pve3** (storage focus, 96 GB RAM):
- 3× Samsung 990 PRO 1TB + 5× 22 TB WD Purple Pro RAIDZ1 (unchanged)
- 2× 48 GB DDR5 (dual-channel — optimized for LLM workload)
- Heat pads applied to all 3 existing NVMes
- CT160 ct-ai-01, CT162 ct-quant-trading, CT250 ct-dev-homelab (renamed from `-pve3`) — running

**Cluster**: 3/3 quorate, all nodes on ZFS (no more LVM anywhere).

## RAM redistribution

| Node | Before | After | Rationale |
|---|---|---|---|
| pve1 | 1× 48 GB | 1× 16 GB | Single-channel; sufficient for current workloads (~11 GB used of 15 GB available) |
| pve2 | 1× 48 GB | 1× 16 GB | Single-channel; fresh install, minimal use |
| pve3 | 2× 16 GB | **2× 48 GB dual-channel = 96 GB** | Maximum iGPU VRAM headroom (up to 24 GB) + large LLM context + VM headroom |

Total cluster RAM unchanged at 128 GB; rebalanced to concentrate on pve3 where the Radeon 890M iGPU and LLM workload benefit most.

## Workload consolidation (same session)

Destroyed during Window B prep:
- CT104 ct-zeroclaw-01 (pve1, stopped tombstone, user-initiated destroy)
- CT150 ct-dev-homelab (pve1, stopped tombstone, user-initiated destroy)
- CT152 ct-dev-test (pve2, throwaway, user-initiated destroy)
- CT153 ct-isabelle (pve2, user-initiated destroy)
- CT105 ct-pbs-migration (pve2, pre-Window-A rollback archive no longer load-bearing)
- VM103 vm-haos-01 (pve1, abandoned HAOS installer, Terraform module was commented out)

Migrated:
- CT151 sparkle-cps → pve3 (via pbs-migration vzdump + pct restore) → back to pve2 (via `pct migrate --restart`)

Renamed:
- CT250 hostname: `ct-docker-01-pve3` → `ct-dev-homelab` (VMID 250 retained)
- CT250 `onboot: 0 → 1` (now production workbench)

Removed from cluster:
- `pbs-migration` PBS storage config

## Cluster-wide storage IDs now consistent

| Node | local-lvm | local-zfs |
|---|---|---|
| pve1 | inactive | active |
| pve2 | inactive | active ← flipped by Window B |
| pve3 | inactive | active |

Meets Story 5-12 AC without requiring explicit story execution.

## Gotchas encountered + learnings (for Epic 3 automation)

### 1. `/etc/hosts` stale IP causes `pvecm add` split-brain

The auto-installer wrote `/etc/hosts` with the IP it received from DHCP at install time (`192.168.50.26` — DHCP fallback IP because no reservation for pve2's new-install MAC existed in the router yet). When `pvecm add` ran, it resolved `pve2` hostname to `.26` instead of `.202` and registered the node in corosync at the wrong IP. Result: pve2 joined a "cluster of one" (itself at .26) instead of the existing cluster at .201/.203.

**Fix:** edit `/etc/hosts` to `192.168.50.202 pve2.home.io pve2` BEFORE running `pvecm add`. Then reset cluster state (`rm /etc/corosync/*`, stop/restart pve-cluster) and retry.

**Prevention for Epic 3:** DHCP reservation for pve3 MAC → .203 (Epic 7.8, now done). `/etc/hosts` fix in pve-node-bootstrap playbook (Epic 7.9).

### 2. Auto-installer `source = "from-dhcp"` pins vmbr0 to the wrong NIC

Auto-installer picks whichever NIC had a DHCP lease at install time (enp5s0 this session). After install, vmbr0 is hardcoded to enp5s0. If the cable is moved to ETH0 port (= enp2s0), vmbr0 silently fails to come up because enp5s0 has no link. All four NIC link LEDs go dark after boot, making diagnosis feel like "the node is completely broken."

**Fix:** edit `/etc/network/interfaces`, change `bridge-ports enp5s0` → `bridge-ports enp2s0`, then `systemctl restart networking`.

**Prevention for Epic 3:** pve-node-bootstrap playbook (Epic 7.9) + DHCP reservations + answer.toml with MAC-pinned NIC.

### 3. `/root/.ssh/authorized_keys` is a symlink to `/etc/pve/priv/authorized_keys` on fresh PVE

Proxmox cluster-ssh uses `/etc/pve/priv/authorized_keys` as the shared cluster key file, symlinked into root's homedir. On a fresh standalone node, the symlink target doesn't exist yet, so `>> authorized_keys` fails with "No such file or directory."

**Fix:** `rm /root/.ssh/authorized_keys` (removes the broken symlink), then create a real file with cluster SSH keys.

**Prevention for Epic 3:** answer.toml `[first-boot]` script installs a bootstrap pubkey into a real authorized_keys file.

### 4. NIC interface naming shifts after hardware change

Before Window B, pve2 NICs were named `enp1s0`–`enp4s0`. After the drive+RAM swap, PCI enumeration shifted and NICs were named `enp2s0`–`enp5s0`. This broke the mental model of "ETH0 = enp1s0" and confused initial diagnosis.

**Prevention:** pve-node-bootstrap playbook detects the active NIC at runtime rather than hardcoding names.

### 5. pvecm's `--use_ssh` still hangs if SSH trust isn't already bidirectional

Even with `--use_ssh --force`, pvecm add tries multiple SSH operations and will hang waiting for interactive auth if either direction of trust isn't already established. Install one direction manually first, then add is fast.

**Prevention:** pve-node-bootstrap playbook distributes SSH keys in both directions before calling pvecm add.

### 6. MinisForum N5 Pro ETH0 port = WAN on Asus router (initial confusion)

Unrelated to pve2 but caught during diagnosis: Asus router's physically-labeled `ETH0` is the WAN port (not in `br0` bridge). Devices plugged into it get link LED but no LAN connectivity. Always use labeled `LAN 1/2/3/4` ports.

## Performance notes

- **Resilver for Story 5.13 (pve1 2nd NVMe attach):** 25.6 GB in 35 seconds, 0 errors
- **CT151 migration back to pve2:** 61 seconds for ~5.6 GB CT via ZFS send/recv
- **pve2 auto-install:** ~10 minutes end-to-end (USB boot → ZFS install → reboot → SSH available)

## Terraform drift to reconcile (deferred)

- `main.tf` line 164–187 `ct_dev_homelab` module references vmid=150 / node=pve2 / local-lvm — no longer exists on cluster. Needs full removal from module + `terraform apply -refresh-only` to reconcile state.
- VM103 module (lines 47–62) commented-out, can be deleted entirely.

Tracked in Story 5.11 (scope revised — see `sprint-change-proposal-2026-04-24.md`).

## Sprint status impact

Closed stories:
- **5-7** Evacuate pve2 CTs: done
- **5-8** Reinstall Proxmox pve2 with ZFS: done (actually 2-way mirror, better than planned single-disk)
- **5-9** Rejoin pve2 to cluster: done
- **5-12** Validate cluster-wide storage ID consistency: done
- **5-13** Add 2nd NVMe to pve1 rpool mirror: done
- **Epic 5**: DONE (all stories complete)

Revised stories (scope changes):
- **5-10** Restore pve2 CTs: scope reduced — 105/152/153 destroyed per operator decision; only CT151 restored
- **5-11** Update Terraform for pve2 CTs: scope revised — `ct_dev_homelab` module needs removal, not flip

New stories (added in Epic 7):
- **7-8** DHCP reservations for all PVE MACs (done in this session)
- **7-9** Ansible pve-node-bootstrap playbook (for Epic 3 prep)
- **7-10** pve3 fixed VRAM BIOS configuration runbook (for Epic 3 execution)
