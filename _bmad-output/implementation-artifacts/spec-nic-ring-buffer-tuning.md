---
title: 'NIC ring buffer tuning on Proxmox hosts'
type: 'bugfix'
created: '2026-04-07'
status: 'done'
baseline_commit: '151d535'
context:
  - homelab-infra/ansible/inventories/homelab/hosts.ini
---

<frozen-after-approval reason="human-owned intent -- do not modify unless human renegotiates">

## Intent

**Problem:** Both Proxmox hosts (pve1/pve2) have Intel i225 NICs (`igc` driver) with RX/TX ring buffers at the 256 default while max is 4096. This causes ~30 dropped packets/sec, 156k+ cumulative RX drops, and degraded real-time traffic (Teams calls dropping, general lag).

**Approach:** Create a new `pve-host` Ansible role that tunes NIC ring buffers to 4096 via `ethtool`, persisted through a systemd oneshot service. Add pve2 to the inventory. Apply immediately to both hosts.

## Boundaries & Constraints

**Always:**
- Use `ethtool -G <iface> rx 4096 tx 4096` for the tuning command
- Make the setting persist across reboots via a systemd oneshot (not `/etc/network/interfaces` post-up, which Proxmox can overwrite during upgrades)
- Auto-detect the active physical NIC name (it differs: `enp2s0` on pve1, `enp1s0` on pve2)
- Keep the role minimal and extensible for future host-level tuning

**Ask First:**
- Adding additional kernel/sysctl tuning beyond ring buffers
- Changing any existing network configuration

**Never:**
- Modify `/etc/network/interfaces` directly (Proxmox owns this file)
- Restart networking or reboot hosts
- Touch bridge (vmbr0) settings

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path | NIC supports ring size 4096 | Ring buffers set to 4096, persist on reboot | N/A |
| Already tuned | Ring buffers already at 4096 | No change, idempotent | N/A |
| NIC doesn't support 4096 | Max < 4096 | Set to NIC's reported max | Warn but don't fail |

</frozen-after-approval>

## Code Map

- `homelab-infra/ansible/roles/pve-host/tasks/main.yml` -- New role: NIC ring buffer tuning via ethtool
- `homelab-infra/ansible/roles/pve-host/templates/nic-ring-buffer.service.j2` -- Systemd oneshot unit to apply settings at boot
- `homelab-infra/ansible/roles/pve-host/defaults/main.yml` -- Default variables (ring buffer sizes)
- `homelab-infra/ansible/inventories/homelab/hosts.ini` -- Add pve2 to `[proxmox_hosts]` group
- `homelab-infra/ansible/playbooks/pve-host.yml` -- Playbook to run the role against proxmox_hosts

## Tasks & Acceptance

**Execution:**
- [x] `homelab-infra/ansible/inventories/homelab/hosts.ini` -- Add pve2 to `[proxmox_hosts]` group
- [x] `homelab-infra/ansible/roles/pve-host/defaults/main.yml` -- Define `nic_ring_rx: 4096` and `nic_ring_tx: 4096`
- [x] `homelab-infra/ansible/roles/pve-host/templates/nic-ring-buffer.service.j2` -- Systemd oneshot that runs ethtool on the detected NIC at boot
- [x] `homelab-infra/ansible/roles/pve-host/tasks/main.yml` -- Detect active NIC, apply ethtool, deploy systemd unit, enable service
- [x] `homelab-infra/ansible/playbooks/pve-host.yml` -- Playbook targeting `proxmox_hosts` with role `pve-host`

**Acceptance Criteria:**
- Given both PVE hosts, when the playbook runs, then `ethtool -g <nic>` shows RX/TX ring buffers at 4096
- Given a PVE host reboots, when it comes back up, then ring buffers are automatically set to 4096 by the systemd service
- Given a NIC already at 4096, when the playbook runs again, then no changes are made (idempotent)
- Given pve2, when `ansible-inventory --list` is run, then pve2 appears in the `proxmox_hosts` group

## Verification

**Commands:**
- `ssh pve1 "ethtool -g enp2s0 | grep -A4 'Current'"` -- expected: RX 4096, TX 4096
- `ssh pve2 "ethtool -g enp1s0 | grep -A4 'Current'"` -- expected: RX 4096, TX 4096
- `ssh pve1 "systemctl is-enabled nic-ring-buffer.service"` -- expected: enabled
- `ssh pve2 "systemctl is-enabled nic-ring-buffer.service"` -- expected: enabled

## Spec Change Log

## Suggested Review Order

- Entry point: NIC detection, idempotency check, and live apply logic
  [`main.yml:7`](../../homelab-infra/ansible/roles/pve-host/tasks/main.yml#L7)

- Boot persistence: systemd oneshot unit template with detected NIC name
  [`nic-ring-buffer.service.j2:1`](../../homelab-infra/ansible/roles/pve-host/templates/nic-ring-buffer.service.j2#L1)

- Tunable defaults: ring buffer sizes as overridable variables
  [`defaults/main.yml:1`](../../homelab-infra/ansible/roles/pve-host/defaults/main.yml#L1)

- Inventory: pve2 added to proxmox_hosts group
  [`hosts.ini:3`](../../homelab-infra/ansible/inventories/homelab/hosts.ini#L3)

- Playbook: role wiring for proxmox_hosts
  [`pve-host.yml:1`](../../homelab-infra/ansible/playbooks/pve-host.yml#L1)
