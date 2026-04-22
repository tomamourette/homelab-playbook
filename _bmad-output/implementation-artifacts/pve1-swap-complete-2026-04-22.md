---
date: 2026-04-22
session: Epic 5 Phase 1 pve1 NVMe swap + reinstall + return-migration (COMPLETE)
relates-to: pve1-solo-nvme-replacement-runbook.md, pve1-preflight-report-2026-04-21.md, vm100-ddrescue-report-2026-04-20.md, session-recovery-2026-04-21.md
---

# pve1 NVMe replacement — complete

The failing 500 GB Samsung 970 EVO Plus has been replaced with a 1 TB Samsung 990 PRO, Proxmox VE 9.1.1 reinstalled, all workloads returned, HA back online.

## Final state (2026-04-22 post-migration)

**pve1** (new 990 PRO, ZFS single-disk rpool ~928 GB):
- CT101 ct-docker-01 — running (19 docker stacks: pihole, traefik, prometheus, grafana, etc.)
- CT102 ct-media-01 — running (20 docker containers: plex, jellyfin, sonarr, radarr, etc.); `/media` bind-mounted from `shared-nfs-bulk` on pve3
- CT104 ct-zeroclaw-01 — running
- CT150 ct-dev-homelab — **stopped tombstone** (operator workbench lives on pve3 CT250 per Epic 4)
- VM100 smarthome — running (HAOS booted from ddrescue image; HA at http://192.168.50.86:8123 returning 200; Zigbee USB 10c4:ea60 passthrough working)
- VM103 vm-haos-01 — running (iso-boot only; cosmetic)
- Templates 999, 9000 — stopped

**pve2, pve3** — unchanged from prior state.

**Cluster** — 3/3 quorate.

## Gotchas encountered + learnings (for pve2's future swap)

### 1. `proxmox-auto-install-assistant` filter syntax is brittle
- `filter.ID_NET_NAME_MAC = "enp*/MAC"` — this is NOT valid; `ID_NET_NAME_MAC` refers to the udev MAC-based interface NAME (like `enx00d04c104054`), not a pattern combining NIC-name and MAC
- `filter.ID_BUS = "nvme"` — NVMe devices don't reliably expose `ID_BUS`, so this match failed silently

**Fix applied (works):**
```toml
[network]
source = "from-dhcp"         # simpler; installer picks whichever NIC has a lease

[disk-setup]
filesystem = "zfs"
zfs.raid = "raid0"
zfs.ashift = 12
zfs.compress = "zstd"
disk-list = ["nvme0n1"]       # explicit over filter
```

### 2. Auto-installer halts silently at TUI when a filter fails
Failed filter doesn't emit a clear network-visible error. Symptom: pve1 got a DHCP lease and responded to ping, but SSH/pveproxy/all TCP ports stayed closed forever (installer TUI sitting idle waiting for operator input). Only a monitor + keyboard reveals the issue.

### 3. Without a monitor you cannot pull the USB at the "install complete" moment
After successful install, auto-installer reboots. If BIOS boot order has USB first, it re-enters the installer indefinitely. **The clean fix is to set BIOS boot order: internal NVMe priority #1, USB fallback.** Must be done with a monitor attached the first time.

Once BIOS boot order is right, future auto-installs are truly headless:
- Plug USB, power on → boots USB → installs → reboots → BIOS picks NVMe → PVE boots. No operator action required.

### 4. OVMF Secure Boot with empty efidisk traps HAOS booting (100% CPU black screen)
The old VM100's `efidisk0` was not in the ddrescue (it was a separate 4 MB LV). When we created a fresh empty efidisk, the default PVE config generated OVMF config with Secure Boot code but unenrolled keys → HAOS refused to boot silently (no VGA output, 100% CPU).

**Fix applied (works):**
```bash
qm set 100 --delete efidisk0
qm set 100 --efidisk0 local-zfs:4,efitype=4m,pre-enrolled-keys=0
```

The explicit `pre-enrolled-keys=0` puts Secure Boot in Setup Mode, allowing HAOS to boot normally.

### 5. `pvecm add` prompts for target's root password via API (non-interactive can't answer)
Even with SSH keys pre-trusted, `pvecm add 192.168.50.203` fails with "EOF while reading password".

**Fix: `pvecm add --use_ssh`** bypasses the API auth path and uses the SSH trust we set up. Add `--force` if the stale node directory (`/etc/pve/nodes/pve1/`) exists from a pre-reinstall cluster state.

### 6. After reinstall, old SSH host keys cause `Host key verification failed`
The reinstalled node has fresh SSH host keys. Cluster nodes + CT250 workbench cached the old fingerprint.

**Fix:**
```bash
ssh-keygen -R 192.168.50.201   # on each client node (CT250, pve2, pve3)
ssh-keygen -R pve1
# Then reconnect — new host key auto-accepted (StrictHostKeyChecking=accept-new)
```

### 7. `qm migrate` for VMs refuses local CDROM ISOs
`qm migrate 103 pve1 --with-local-disks` errors: "can't migrate local disk … local cdrom image". Workaround: detach ISO via `qm set --delete ide2`, migrate, reattach on target.

### 8. `pct migrate --restart` works cleanly for offline LXC migrations
All 4 LXC migrations (CT104, CT101, CT102, plus CT150 which stayed as tombstone) completed with a brief stop-ship-start cycle. No live/CRIU migration needed. Duration roughly proportional to rootfs used size at ~100 MB/s over 1 GbE.

## VM100 recovery quality — outstanding

The 99.9998% ddrescue rescue image booted cleanly with the `pre-enrolled-keys=0` fix:
- Home Assistant frontend responds HTTP 200 within ~60 sec of VM start
- Zigbee device pairings (the critical `zigbee.db`) preserved — no re-pairing needed
- Recorder DB intact (history preserved)
- All automations/scripts/scenes intact
- Household automation should resume without intervention

## Terraform main.tf updated (partial)

`homelab-infra/terraform/envs/homelab/main.tf` storage_id flipped `local-lvm` → `local-zfs` for the three migrated pve1 CTs (ct-docker-01, ct-media-01, ct-zeroclaw-01).

**Known drift** — Terraform state (`terraform.tfstate`) still references old `local-lvm:vm-NNN-disk-0` volumes. When the operator runs `terraform plan` next, they'll see drift. **Resolution path:**

```bash
# Run this at the next convenient time — read-only, no changes applied:
cd homelab-infra/terraform/envs/homelab
terraform apply -refresh-only    # syncs state to live cluster reality
# Then a subsequent `terraform plan` should show no diff (or only intended drift).
```

Explicitly **NOT** updated:
- `ct-dev-homelab` (line 173) — tombstone on pve1, not migrated
- `ct-dev-test`, `ct-sparkle-cps`, `ct-isabelle` (lines 199, 225, 251) — on pve2 (still LVM)
- `ct-dev-01` VM module (line 311) — not currently deployed in cluster

These flip to `local-zfs` when pve2 gets its own swap + reinstall.

## BIOS boot order reminder

If operator hasn't yet: boot pve1 once with the monitor, enter BIOS (Del/F2), set the internal NVMe as boot priority #1. This makes future auto-installs truly unattended (works for pve2 too).

## Next in the sprint

- **Story 5.12**: Validate cluster-wide storage ID consistency (pve2 not done yet — pending drive 2)
- **Story 5.4**: formally mark VM100 smarthome restoration done (artifact = this doc)
- **Story 2.11**: 48 h soak period on shared-nfs-bulk — now ~36 h in, can likely close now (verify media playback one more time, then destroy shared-pool on pve3)
- **Story 7.2**: idempotency test of `pve-host-pve3-storage` Ansible role — deferred until after Epic 3 (pve3 rebuild still pending drive 2)
- **Epic 5 Window B**: pve2 swap when second 990 PRO arrives
- **Story 5.13 (proposed)**: add a second 990 PRO to pve1 as ZFS mirror (hardware permitting; future)
