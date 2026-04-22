# CT150 Evacuation — Operator Cutover Runbook

> **2026-04-22 update:** operator is permanently on CT250 at 192.168.50.156 (soft cutover — Option B). Option A (hard IP swap to .150) is no longer urgent since pve1 was rebuilt on healthy hardware and the original CT150 tombstone is gone. This runbook is retained as a reference in case a future emergency cutover is needed.

**Current state (as of 2026-04-20 20:45 UTC):** two workbenches running in parallel.

| Instance | Node | VMID | IP | Hostname | Role |
|----------|------|------|----|----------|------|
| Original | pve1 | **150** | 192.168.50.150 | ct-dev-homelab | live session (this one) |
| Evacuated | pve3 | **250** | 192.168.50.156 | ct-dev-homelab-pve3 | standby, fully functional |

**Why both are running:** so you can decide when to cut over. Nothing is destroyed; you can keep both indefinitely, or stop either, or promote 250 → 150.

## Option A — Cut over now (recommended if pve1 NVMe feels risky)

Run these commands from **your laptop** (not from inside CT150, because stopping 150 would kill your session):

```bash
# 1. Verify the new workbench works (sanity check)
ssh root@192.168.50.156 'hostname && cd /home/developer/workspace/homelab/homelab-playbook && git log --oneline -1'
# Expected: ct-dev-homelab-pve3 + the latest commit hash

# 2. Stop the old CT150 on pve1
ssh root@192.168.50.201 'pct stop 150'

# 3. Change VMID 250's IP from .156 → .150
ssh root@192.168.50.203 'pct set 250 --net0 name=eth0,bridge=vmbr0,gw=192.168.50.1,ip=192.168.50.150/24,type=veth'

# 4. Reboot VMID 250 to apply IP change
ssh root@192.168.50.203 'pct reboot 250'

# 5. Wait ~15 sec, then reconnect via the original IP
ssh root@192.168.50.150 'hostname'
# Expected: ct-dev-homelab-pve3 (hostname is from restore, can rename later)
```

**After cutover:** resume Claude Code / your dev workflow by SSHing to `192.168.50.150` as before. The hostname inside the container is now `ct-dev-homelab-pve3` but that's cosmetic — can be fixed by editing `/etc/hostname` + `/etc/hosts` inside the CT if desired.

**Post-cutover cleanup (optional, when you're confident):**
```bash
# Rename VMID 250 → 150 on pve3 to match (only if you want VMID consistency)
# This requires destroying old VMID 150 first, which was already stopped above
ssh root@192.168.50.201 'pct destroy 150'   # removes dead CT150 from pve1 config
# Then optionally on pve3:
# pct cleanup — VMID 250 stays as 250; or rename via backup+restore if you really want 150
```

## Option B — Keep both running, use 250 as the new primary

Just start using `192.168.50.156` for new work. Old CT150 at `.150` becomes read-only / idle.

Advantage: zero disruption, both available.
Disadvantage: two CTs consuming resources on pve1 and pve3.

## Option C — Rollback (if CT250 has a problem)

```bash
ssh root@192.168.50.203 'pct stop 250'
# Continue using CT150 at 192.168.50.150 as normal. Nothing has changed from your perspective.
# The PBS backup from Story 4.2 is still available if needed later.
```

## Option D — Rename VMID 250 → 150 (cosmetic consistency)

Only do this if you want the VMID to match the hostname after cutover. Adds complexity.

```bash
# After Option A is complete and old CT150 destroyed:
# Take a backup of 250, destroy 250, restore as 150
ssh root@192.168.50.203 'vzdump 250 --storage pbs-migration --mode snapshot'
# Find the backup
BACKUP=$(ssh root@192.168.50.203 'pvesm list pbs-migration | grep "ct/250" | tail -1 | awk "{print \$1}"')
ssh root@192.168.50.203 "pct stop 250; pct destroy 250 --purge; pct restore 150 $BACKUP --storage local-zfs --rootfs local-zfs:50 --hostname ct-dev-homelab --net0 name=eth0,bridge=vmbr0,gw=192.168.50.1,ip=192.168.50.150/24,type=veth --unprivileged 1"
ssh root@192.168.50.203 'pct start 150'
```

## How to get back online if everything breaks

### Scenario: can't reach either CT150 or CT250
Your laptop still has SSH to pve1/pve2/pve3 directly (Story 1.7 setup). From your laptop:
```bash
ssh root@192.168.50.201  # pve1 host
ssh root@192.168.50.202  # pve2 host
ssh root@192.168.50.203  # pve3 host
```
On any pve host you can `pct list` and `pct start <VMID>` to recover a stopped CT.

### Scenario: pve3 went down (unlikely but possible)
Old CT150 on pve1 still works. Just `ssh root@192.168.50.201 'pct start 150'` if needed.

### Scenario: pve1 died for real (NVMe finally gave up)
CT250 on pve3 is untouched — `ssh root@192.168.50.156` continues to work. Everything on pve1 (CT101, CT102, CT104, CT150, VM100, VM103) is offline until the new NVMe arrives. Epic 5 then reinstalls pve1 from scratch and restores from PBS.

### Scenario: new PBS restore is needed
The migration-window PBS datastore (CT105 on pve2, 192.168.50.155) holds backups of all cluster guests from Story 1.3. It's independent of pve1 and pve3. Access the PBS UI at https://192.168.50.155:8007 or use `pct restore <new-vmid> pbs-migration:backup/ct/<id>/<timestamp> --storage <target>`.

## Timeline expectations

- Cutover Option A: ~30 seconds of CT150 downtime, then new workbench is live at the original IP
- Option B: zero downtime, two instances
- Rollback Option C: ~5 seconds (stop CT250), no impact to your current session

## Quick verification after cutover

```bash
# Confirm you're talking to the new workbench on pve3
ssh root@192.168.50.150 'grep -E "pve3|pve1" /etc/hostname /proc/version 2>/dev/null; ip -4 addr show eth0 | grep inet'
# Should show eth0 IP .150/24 and "pve3" somewhere in kernel/hostname context

# Confirm git state is what you expect
ssh root@192.168.50.150 'cd /home/developer/workspace/homelab/homelab-playbook && git log --oneline -5'
# Should show the most recent commits from this migration session
```

## My recommendation

**Do Option A tonight or tomorrow morning** — every hour on the failing pve1 NVMe is another roll of the dice. The cutover takes 30 seconds and is fully reversible by reversing the three `pct` commands.

Keep the old CT150 in PBS backups (it's already there from Story 4.2). If you ever need to recover state from "how it was before cutover," restore that backup to a fresh VMID.
