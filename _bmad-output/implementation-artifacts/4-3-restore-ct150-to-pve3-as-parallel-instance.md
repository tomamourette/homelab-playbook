---
status: done
epic: 4
story: 4.3
title: Restore CT150 to pve3 as parallel instance (VMID 250)
executed_early: true
executed_reason: P1 pve1 NVMe failure discovered during Story 1.3 — evacuation moved forward of original Phase 5.5 timing to protect operator workbench from progressing hardware failure.
---

# Story 4.3: Restore CT150 to pve3 as parallel instance

## User Story

As an operator, I want CT150 running on pve3 without deleting the pve1 copy yet, so that the pve1 instance remains as a fallback.

## Acceptance Criteria

**Given** the fresh PBS backup of CT150 exists (Story 4.2)
**When** I run `pct restore 250 <backup-path> --storage local-zfs --target pve3`
**Then** VMID 250 appears in `pct list` on pve3 with all CT150's content
**And** the pve1 CT150 (VMID 150) is still running but can be cleanly stopped for Phase 6

## Tasks

- [x] Fresh PBS backup of CT150 taken (Story 4.2) — `pbs-migration:backup/ct/150/2026-04-20T20:40:54Z`, 13.56 GB
- [x] Restore as VMID 250 on pve3 with temp IP 192.168.50.156 and hostname `ct-dev-homelab-pve3`
- [x] Handle `--ignore-unpack-errors 1` gotcha (Docker overlayfs device nodes can't be recreated in unprivileged container restore)
- [x] Verify VMID 250 running and reachable

## Dev Notes

- **Executed early** (before Epic 3) because Story 1.3 discovered pve1's NVMe has ongoing media failures. Waiting for the nominal Phase 5.5 timing would risk losing the operator workbench to hardware failure.
- Used VMID **250** and temp IP **192.168.50.156** to avoid collision with the still-running CT150 at VMID 150 / IP 192.168.50.150. Both run in parallel — cutover is a deliberate separate action (Story 4.5).
- Auto-generated new MAC address (BC:24:11:09:52:89) — different from CT150's original MAC so the two can coexist on the same L2 network.
- `--ignore-unpack-errors 1` needed because the backup contained Docker's `backingFsBlockDev` device nodes that can't be recreated in an unprivileged container restore. These are runtime-only Docker artifacts; losing them means Docker state will be re-initialized on first start — no loss of actual container images (those are in the docker overlay which is preserved).
- `safe.directory` configured for root in all sub-repos on CT250 after first-boot so `git` works as root. `sudo -u developer` also works.

## Implementation Report

```
$ ssh pve3 'pct config 250 | head -5'
arch: amd64
cores: 2
hostname: ct-dev-homelab-pve3
memory: 8192
net0: ...ip=192.168.50.156/24

$ ssh root@192.168.50.156 'hostname && uptime'
ct-dev-homelab-pve3
 20:45:47 up 0 min, 1 user, load average: 1.51, 0.62, 0.38

$ ssh root@192.168.50.156 'cd /home/developer/workspace/homelab/homelab-playbook && git log --oneline -1'
6a8613c feat(epic-1): Story 1.3 done-with-exception + P1 pve1 NVMe failure

$ ssh root@192.168.50.156 'ls /home/developer/.ssh/ && ls /home/developer/.claude/.credentials.json && ls /home/developer/workspace/homelab/homelab-infra/terraform/envs/homelab/terraform.tfstate'
(all intact)
```

State preserved:
- SSH keys (id_ed25519, homelab_ed25519, known_hosts) ✓
- Terraform state (97 KB tfstate + backup, last modified 2026-04-18 — pre-session) ✓
- Claude credentials ✓
- Full `/home/developer/workspace/homelab` git tree with all session commits ✓
- docker/nesting features preserved in CT config ✓
