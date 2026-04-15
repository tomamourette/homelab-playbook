# Story 8.2: Integrate PVE3 into Infrastructure Automation

Status: ready-for-dev

## Story

As a homelab operator,
I want pve3 integrated into Ansible, SSH config, DNS, and documentation,
So that pve3 is managed consistently with pve1 and pve2.

## Acceptance Criteria

1. **Given** pve3 is joined to the cluster (Story 8.1)
   **When** I check the Ansible inventory
   **Then** `ansible/inventories/homelab/hosts.ini` has pve3 in `[proxmox_hosts]` with `ansible_host=192.168.50.203 ansible_user=root ansible_ssh_private_key_file=~/.ssh/homelab_ed25519`

2. **Given** pve3 is in the Ansible inventory
   **When** I run `ansible-playbook pve-host.yml --limit pve3`
   **Then** the playbook succeeds and NIC ring buffer tuning is applied to pve3's physical NIC

3. **Given** pve3 needs SSH access from the control machine
   **When** I check the SSH config
   **Then** `~/.ssh/config` on ct-dev-homelab has a `pve3` alias pointing to `192.168.50.203` with `User root` and `IdentityFile ~/.ssh/homelab_ed25519`

4. **Given** pve3 needs DNS resolution
   **When** I check Pi-hole custom DNS
   **Then** `192.168.50.203 pve3` is resolvable (either via Pi-hole custom list or `/etc/hosts` entries already deployed in Story 8.1)

5. **Given** pve3 is operational
   **When** I check the infra documentation
   **Then** `docs/architecture-homelab-infra.md` is updated with pve3 in the network diagram, node table, SSH access table, and network tuning section

6. **Given** all integration is complete
   **When** I run `ansible all -m ping`
   **Then** all hosts respond successfully including pve3

## Edge Cases & Error Scenarios

1. **Side effects:**
   - `hosts.ini` modified (pve3 line added to `[proxmox_hosts]`)
   - `~/.ssh/config` modified (pve3 block added)
   - `docs/architecture-homelab-infra.md` modified (network diagram, tables updated)
   - `pve-host.yml` applies NIC ring buffer tuning to pve3 (ethtool + systemd service)

2. **Dependency failure:**
   - If SSH key not on pve3: already deployed in Story 8.1 (homelab_ed25519)
   - If `pve-host.yml` fails on pve3: check NIC name (N5 Pro uses 10GbE, different chipset from pve1/pve2 Realtek 2.5GbE) — the role auto-detects but verify
   - If `ansible all -m ping` fails for pve3: check SSH config, key, and network connectivity

3. **Assumptions:**
   - Story 8.1 is complete (pve3 in cluster, SSH key deployed)
   - homelab-infra repo is accessible from ct-dev-homelab
   - Pi-hole runs on ct-docker-01 (192.168.50.194)
   - The `pve-host` role auto-detects the physical NIC via bridge member detection

## Eval Assertions

<!-- Binary test assertions derived from acceptance criteria. Used by /autoresearch:fix for post-code-review iteration loops. -->

| # | Assertion | Command/Check | Pass Criteria |
|---|-----------|---------------|---------------|
| AC-1 | pve3 in Ansible inventory | `grep -q 'pve3.*192.168.50.203' homelab-infra/ansible/inventories/homelab/hosts.ini` | Exits with code 0 |
| AC-2 | pve-host playbook succeeds | `cd homelab-infra && ansible-playbook -i ansible/inventories/homelab/hosts.ini ansible/playbooks/pve-host.yml --limit pve3` | Exits with code 0 |
| AC-3 | SSH config has pve3 | `grep -A2 'Host pve3' ~/.ssh/config` | Shows HostName 192.168.50.203 |
| AC-4 | DNS resolution works | `ssh pve3 'hostname'` | Returns pve3 (SSH alias resolves) |
| AC-5 | Docs updated with pve3 | `grep -q 'pve3' docs/architecture-homelab-infra.md` | Exits with code 0 |
| AC-6 | Ansible ping all hosts | `cd homelab-infra && ansible all -i ansible/inventories/homelab/hosts.ini -m ping` | All hosts return SUCCESS including pve3 |

## Tasks / Subtasks

- [ ] Task 0: Verify Story 8.1 completion (AC: all)
  - [ ] Run `ssh pve3 'pvecm status'` to confirm pve3 is in the cluster
  - [ ] Run `ssh pve3 'hostname'` to confirm SSH access works
- [ ] Task 1: Add pve3 to Ansible inventory (AC: 1)
  - [ ] Edit `homelab-infra/ansible/inventories/homelab/hosts.ini`
  - [ ] Add `pve3 ansible_host=192.168.50.203 ansible_user=root ansible_ssh_private_key_file=~/.ssh/homelab_ed25519` under `[proxmox_hosts]`
- [ ] Task 2: Add pve3 SSH config (AC: 3)
  - [ ] Add pve3 block to `~/.ssh/config` matching the pattern of pve1/pve2 entries
- [ ] Task 3: Run pve-host playbook on pve3 (AC: 2)
  - [ ] Run `cd homelab-infra && ansible-playbook -i ansible/inventories/homelab/hosts.ini ansible/playbooks/pve-host.yml --limit pve3`
  - [ ] Verify NIC ring buffer tuning was applied (check ethtool output on pve3)
- [ ] Task 4: Update infrastructure documentation (AC: 5)
  - [ ] Update network diagram in `docs/architecture-homelab-infra.md` to include pve3 (.203) as third node
  - [ ] Add pve3 to the Infrastructure Resources node comparison (Ryzen AI 9 HX PRO 370, 12C/24T, 28GB DDR5, 3x 1TB NVMe, 10GbE+5GbE, OCULink)
  - [ ] Add pve3 to the SSH Access table
  - [ ] Add pve3 NIC to the Network Tuning table (NIC name TBD — auto-detected by pve-host role)
- [ ] Task 5: Verify full integration (AC: 4, 6)
  - [ ] Run `ssh pve3 'hostname'` via SSH alias (tests SSH config)
  - [ ] Run `cd homelab-infra && ansible all -i ansible/inventories/homelab/hosts.ini -m ping`
  - [ ] Verify all hosts respond SUCCESS

## Dev Notes

This story modifies files in **two repos**: `homelab-infra` (Ansible inventory) and `homelab-playbook` (docs). All edits are in `homelab-infra/` for IaC and `docs/` for documentation.

### Previous Story Learnings (8.1)

- SSH key (`homelab_ed25519`) already deployed on pve3 via web UI shell
- pve3 hostname is `pve3` (domain `home-cluster` from installer, vs `home.io` on pve1/pve2)
- pve3 uses ZFS mirror root (not ext4/LVM like pve1/pve2) — no impact on Ansible
- NIC chipset on N5 Pro is different from pve1/pve2 (10GbE, not Realtek 2.5GbE) — `pve-host` role auto-detects
- pve3 has 28GB RAM currently (2x 16GB), upgrade to 96GB planned

### Existing Patterns to Follow

**Ansible inventory** (`hosts.ini`):
```ini
pve1 ansible_host=192.168.50.201 ansible_user=root ansible_ssh_private_key_file=~/.ssh/homelab_ed25519
pve2 ansible_host=192.168.50.202 ansible_user=root ansible_ssh_private_key_file=~/.ssh/homelab_ed25519
```

**SSH config** (`~/.ssh/config`):
```
Host pve2
    HostName 192.168.50.202
    User root
    IdentityFile ~/.ssh/homelab_ed25519
    StrictHostKeyChecking accept-new
```

**pve-host role** (`ansible/playbooks/pve-host.yml`):
- Targets `[proxmox_hosts]` group
- Auto-detects physical NIC (bridge member of vmbr0)
- Applies `ethtool -G <nic> rx 4096 tx 4096`
- Deploys systemd oneshot service for boot persistence

### Pi-hole DNS Note

The Pi-hole custom list template (`pihole-custom.list.j2`) manages service DNS (traefik, grafana, etc.), not node DNS. Node resolution for pve3 is already handled by `/etc/hosts` entries deployed in Story 8.1. Adding a Pi-hole local DNS record for `pve3` is optional but nice-to-have for any client on the network.

### Project Structure Notes

- `homelab-infra/ansible/inventories/homelab/hosts.ini` — Ansible inventory
- `homelab-infra/ansible/playbooks/pve-host.yml` — targets `[proxmox_hosts]`
- `homelab-infra/ansible/roles/pve-host/` — NIC ring buffer tuning role
- `~/.ssh/config` — SSH aliases (on ct-dev-homelab)
- `docs/architecture-homelab-infra.md` — infra documentation

### References

- [Source: homelab-infra/ansible/inventories/homelab/hosts.ini]
- [Source: homelab-infra/ansible/playbooks/pve-host.yml]
- [Source: docs/architecture-homelab-infra.md#Network Architecture]
- [Source: docs/architecture-homelab-infra.md#SSH Access]
- [Source: planning-artifacts/epics.md#Story 8.2]

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
