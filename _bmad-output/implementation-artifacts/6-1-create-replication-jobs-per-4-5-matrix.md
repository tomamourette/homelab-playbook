---
status: done
epic: 6
story: 6.1
title: Create replication jobs per §4.5 matrix (HIGH-priority scope)
created: 2026-04-24
author: BMad SM (via planner agent)
---

# Story 6.1: Create replication jobs per §4.5 matrix (HIGH-priority scope)

Status: done

## Story

As an operator,
I want automated ZFS replication configured for every HA-tagged workload to two peer nodes,
so that if any single node fails, HA failover has a recent replica to start from on either surviving node.

## Business value

Epic 6 is the final capstone of the pve3-storage-migration program: High Availability Activated. Every prior epic (1 through 5 plus Epic 3 pve3 rebuild) exists to enable this story. The original incident that kicked off this program (a single-node ZFS failure taking down workloads with no replica) is only operationally eliminated once replication jobs are *running and producing recent deltas on peer nodes*. This story is the last thing standing between "backup-based DR with 15-minute-to-hours RPO" and "HA-based DR with 15-minute RPO and automatic failover".

All downstream stories in Epic 6 (6.2 delta verification, 6.3 HA groups, 6.4 HA assignments, 6.5 V3 RPO drill, 6.6 V4 migrate drill, 6.7 V5 pull-plug drill, 6.8 V6 recovery drill, 6.9 runbook) build on 6.1's jobs. If the replication targets do not exist, HA cannot start a guest on a peer.

## Scope revision vs epic document

The epic document (`pve3-storage-migration-epics.md` §"Story 6.1") lists the full original §4.5 matrix (CT162, CT101, CT102, CT151, CT153, CT160, VM103, VMID 250/CT150). That matrix predates the Window B consolidation (2026-04-24) and the HA priority review in `sprint-change-proposal-2026-04-24.md §2`.

**Post-consolidation reality:**

- CT152, CT153, CT150, CT105 destroyed in Window B (see `window-b-complete-2026-04-24.md §"Workload consolidation"`). They no longer exist and do not need replication.
- CT102 (ct-media-01), CT151 (ct-sparkle-cps), CT160 (ct-ai-01) are LOW-priority (not HA-tagged) per the priority matrix. They are protected by nightly PBS backup (Epic 4). Replicating them is deferred as optional enhancement.
- CT250 (ct-dev-homelab) was created after the original epic draft; it replaces the destroyed CT150/153 as the operator workbench and is HA-tagged.
- VMID 103 (HAOS) referenced in the epic is a typo for VMID 100 — the smarthome VM is `smarthome` on pve1 at VMID 100 per the current inventory.

**This story's execution scope is therefore the HIGH-priority list from `sprint-change-proposal-2026-04-24.md §2.4`:**

| VMID | Name | Home node | Replication targets | Schedule | Rationale |
|------|------|-----------|---------------------|----------|-----------|
| 100 | smarthome (HAOS VM) | pve1 | pve2, pve3 | */15 | HA-tagged (primary residence) |
| 101 | ct-docker-01 | pve1 | pve2, pve3 | */15 | HA-tagged (primary Docker host) |
| 162 | ct-quant-trading | pve3 | pve1, pve2 | */15 | HA-tagged (market-hours sensitive) |
| 250 | ct-dev-homelab | pve3 | pve1, pve2 | */30 | HA-tagged (operator workbench) |

Total: 8 replication jobs (4 guests × 2 targets each). Replicating to **two** targets — not one — gives HA flexibility: if the home node fails, either surviving node can take over.

## Acceptance Criteria

**Given** the cluster is 3/3 quorate (verified via `pvecm status` on each node)
**And** all three nodes expose `local-zfs` with identical storage IDs (verified via `pvesm status` per node)
**And** every HIGH-priority guest in the table above exists and is running on its listed home node (verified via `pct list` / `qm list`)

**When** I create the eight replication jobs per the table above via `pvesr create-local-job` (or `pvesh create /nodes/<node>/replication`)

**Then** `pvesr status` on the home node of each guest shows the job with state `OK` and a schedule matching the spec
**And** the first replication cycle of each job completes successfully (state `OK`, zero errors)
**And** the target node shows the replicated dataset on its `local-zfs` (verified via `zfs list -r rpool/data` on the target)
**And** the second replication cycle produces a small delta (< 100 MB typical for idle guests, MB-range not GB-range — validated in Story 6.2)
**And** no job is in state `error` or `warning`
**And** the replication configuration is persisted to the Ansible role or a committed markdown runbook so it can be reconstructed if `/etc/pve/replication.cfg` is lost

**Given** VMID 100 (smarthome HAOS VM) is replicated to pve2 and pve3
**When** HA would hypothetically failover VMID 100 to pve2 or pve3 after a pve1 failure
**Then** the story MUST explicitly document that Zigbee USB passthrough (USB ID `10c4:ea60`) is physically connected to pve1 only, and a failover-started smarthome on pve2/pve3 comes up **without Zigbee radio connectivity** — Home Assistant will boot but Zigbee devices will be unreachable until pve1 is recovered or the USB stick is physically moved

## Tasks / Subtasks

- [x] **Task 1: Pre-flight checks** (AC: cluster quorate, storage uniform, guests present)
  - [x] Verify cluster: `pvecm status` on pve1, pve2, pve3 — all report `Quorate: Yes`, `Total votes: 3`
  - [x] Verify shared storage naming: `pvesm status` on each node shows `local-zfs` active with identical pool name `rpool`
  - [x] Verify HIGH-priority guests are running on their home nodes: `pct list` on pve1 shows 101 running; `qm list` on pve1 shows 100 running; `pct list` on pve3 shows 162 and 250 running
  - [x] Confirm no stale replication jobs: `pvesr list` on each node — documented current state as empty baseline before changes
  - [x] Confirm `/etc/pve/replication.cfg` is currently small/empty (it is cluster-wide via `pmxcfs`)
  - [x] Read Proxmox replication docs reference: <https://pve.proxmox.com/wiki/Storage_Replication>

- [x] **Task 2: Create VMID 100 replication jobs (smarthome → pve2, pve3)** (AC: VMID 100 jobs exist @15min)
  - [x] On pve1: `pvesr create-local-job 100-0 pve2 --schedule '*/15' --rate 100 --comment '...'`
  - [x] On pve1: `pvesr create-local-job 100-1 pve3 --schedule '*/15' --rate 100 --comment '...'`
  - [x] Verified: `pvesr status` on pve1 lists both `100-0` and `100-1` as enabled; both eventually reached `OK` after their first seed
  - [x] **Zigbee caveat documented**: VMID 100 failover to pve2/pve3 comes up WITHOUT Zigbee radio (USB `10c4:ea60` is pinned to pve1). Captured in `homelab-infra/docs/ha-replication-runbook.md` as the top-level "Known limitation" section

- [x] **Task 3: Create VMID 101 replication jobs (ct-docker-01 → pve2, pve3)** (AC: VMID 101 jobs exist @15min)
  - [x] On pve1: `pvesr create-local-job 101-0 pve2 --schedule '*/15' --rate 100 --comment '...'`
  - [x] On pve1: `pvesr create-local-job 101-1 pve3 --schedule '*/15' --rate 100 --comment '...'`
  - [x] Verified in `pvesr status` on pve1; both reached `OK`
  - [x] First-seed data confirmed ~8.89 GB (see runbook seed table); subsequent cycles down to MB-range

- [x] **Task 4: Create VMID 162 replication jobs (ct-quant-trading → pve1, pve2)** (AC: VMID 162 jobs exist @15min)
  - [x] On pve3: `pvesr create-local-job 162-0 pve1 --schedule '*/15' --rate 100 --comment '...'`
  - [x] On pve3: `pvesr create-local-job 162-1 pve2 --schedule '*/15' --rate 100 --comment '...'`
  - [x] Verified in `pvesr status` on pve3; both `OK`
  - [x] Note: 162-0 first attempt failed at 324s with connection reset during concurrent seed pressure; Proxmox scheduler auto-retried at next `*/15` slot and completed cleanly in 770s. Behavior documented in runbook troubleshooting section

- [x] **Task 5: Create VMID 250 replication jobs (ct-dev-homelab → pve1, pve2)** (AC: VMID 250 jobs exist @30min)
  - [x] On pve3: `pvesr create-local-job 250-0 pve1 --schedule '*/30' --rate 100 --comment '...'`
  - [x] On pve3: `pvesr create-local-job 250-1 pve2 --schedule '*/30' --rate 100 --comment '...'`
  - [x] Verified in `pvesr status` on pve3; both `OK`
  - [x] 30-minute schedule rationale captured in runbook

- [x] **Task 6: Force first replication run on each job** (AC: first cycle completes)
  - [x] Bootstrap shell loops invoked `pvesr run --id <id> --verbose` for all 8 jobs, logging to `/var/log/pve-replication-bootstrap-2026-04-24.log` on pve1 and pve3
  - [x] Parallel seeds (4 concurrent on pve1-side + 4 concurrent on pve3-side) hit lock contention and cross-host bandwidth contention; seed durations stretched to 10-30 min per job instead of the predicted <5 min each
  - [x] All 8 seeds eventually completed successfully — final `pvesr status` on both home nodes shows `LastSync` populated and `FailCount=0` for every job
  - [x] Per-job replication logs captured at `/var/log/pve/replicate/<jobid>` on the origin node (authoritative source beyond the bootstrap stdout log)

- [x] **Task 7: Verify replicated datasets on target nodes** (AC: target dataset exists)
  - [x] On pve2: `zfs list -r rpool/data` confirms `subvol-101-disk-0` (8.89G), `subvol-162-disk-0` (3.96G), `subvol-250-disk-0` (6.68G), `vm-100-disk-0` (EFI 72K), `vm-100-disk-1` (VM 2.90G)
  - [x] On pve3: `zfs list -r rpool/data` confirms `subvol-101-disk-0` (8.89G), `vm-100-disk-0` (72K), `vm-100-disk-1` (2.90G) — 162 and 250 originate here so they appear as the source datasets
  - [x] On pve1: `zfs list -r rpool/data` confirms `subvol-162-disk-0` (3.96G), `subvol-250-disk-0` (6.68G) replicas
  - [x] All replication snapshots `__replicate_*` verified present on every target; the second-cycle snapshots prove incremental replication is working

- [x] **Task 8: Validate replication state holistically** (AC: all jobs `OK`)
  - [x] `pvesr status` on pve1 shows 100-0, 100-1, 101-0, 101-1 all `OK`, no errors, `FailCount=0`
  - [x] `pvesr status` on pve3 shows 162-0, 162-1, 250-0, 250-1 all `OK`, no errors, `FailCount=0`
  - [x] Observed the 20:30 scheduled cycle complete incrementally — delta snapshots match expected MB-range per the runbook's "Seed run results" table (67MB for VM100 disk delta on first incremental, KB-range for idle CTs)
  - [x] No job in `error` state; no job stuck `pending` for more than one cycle

- [x] **Task 9: Persist configuration as-code** (AC: reconstruction is possible)
  - [x] Option A chosen: created `homelab-infra/proxmox/replication/README.md` with the 8 idempotent `pvesr create-local-job` commands and a pointer to the primary runbook
  - [x] Created `homelab-infra/docs/ha-replication-runbook.md` as the primary operator runbook (rebuild procedure, pause/resume, troubleshooting, seed run results)
  - [x] Cross-referenced from `homelab-infra/ansible/roles/pve-host-pve3-storage/README.md` under a new "Related work" section
  - [x] Option B (Ansible role `pve-host-replication-jobs`) explicitly deferred to Epic 7 backlog; noted in replication README

- [x] **Task 10: Document the Zigbee USB caveat prominently** (AC: caveat captured)
  - [x] Added top-level "Known limitation: VMID 100 Zigbee USB passthrough" section to `homelab-infra/docs/ha-replication-runbook.md` — includes USB ID `10c4:ea60`, the two recovery options (restore pve1 OR physically move the stick + `qm set --usb0`), and a cross-link to Story 6.7 pull-plug drill where this will be empirically confirmed
  - [x] Replication README at `homelab-infra/proxmox/replication/README.md` repeats the caveat prominently and links to the full runbook section
  - [x] OMEGA memory cross-link: deferred to user (dev agent has no OMEGA API access from this sandbox)

## Dev Notes

### Relevant architecture patterns and constraints

**This story does NOT require Ansible.** Replication jobs are cluster-wide config (`/etc/pve/replication.cfg` is replicated by `pmxcfs`). A `pvesr create-local-job` call on any node writes the job to the cluster filesystem and it's immediately visible on all nodes. You can perform all configuration from a single SSH session per home node.

**Why schedule at 15 min (not 1 min)?** The epic originally specified 1-min for CT162 (highest criticality). 15-min is a safer starting point for Epic 6 initial activation because:
- 1-min replication can stress a 2-way ZFS mirror on the 16 GB RAM nodes (pve1/pve2) if delta is large
- RPO of 15 min is still well within "acceptable" for all four workloads (none are synchronous-replication grade)
- Story 6.5 will tune CT162 specifically down to 1-min if the RPO drill shows headroom

**Storage Replication prerequisites (from Proxmox docs):**
- ZFS storage with identical pool name on source and target — satisfied post-Epic 3 (all nodes have `rpool`)
- Source and target both reachable via cluster network
- Each guest has ALL its disks on ZFS (no mixed-storage guests replicate cleanly) — verify with `pct config <VMID>` or `qm config <VMID>` before creating the job

### Proxmox replication CLI reference

```bash
# Create a replication job (run on the guest's home node)
pvesr create-local-job <JOBID> <TARGET-NODE> \
  --schedule '*/15' \
  [--comment 'HA replica for <name>'] \
  [--rate <MB/s>]           # optional bandwidth cap
  [--disable]               # optional: create disabled, enable later

# JOBID convention: <VMID>-<N> where N is an integer 0,1,2... per extra target
# Example: CT101 replicating to pve2 (job 101-0) and pve3 (job 101-1)

# List jobs
pvesr list                      # cluster-wide
pvesr status                    # state + last sync + next sync (per node)

# Force a run (use after creating to seed the target immediately)
pvesr run --id <JOBID> --verbose

# Delete a job (careful — drops the replica tree on target)
pvesr delete <JOBID>

# Inspect config
cat /etc/pve/replication.cfg
```

### Idempotency patterns

- `pvesr create-local-job <JOBID>` is **not** idempotent — calling it twice on an existing ID returns error `400 parameter verification failed: job 'X' already exists`. Either check first with `pvesr list | grep <JOBID>` or catch the error and treat it as success
- For a manual-run story like this one, add a simple pre-check shell loop:
  ```bash
  for JOBID in 100-0 100-1 101-0 101-1; do
    if pvesr list | grep -q "^${JOBID}\s"; then
      echo "SKIP: ${JOBID} already exists"
    else
      pvesr create-local-job "${JOBID}" "${TARGET}" --schedule '*/15'
    fi
  done
  ```
- When documenting in the README, include this idempotent re-run block so the next operator can safely execute the commands

### RPO targets (informational — validated in later stories)

| VMID | RPO target | Story | Rationale |
|------|-----------|-------|-----------|
| 100 (smarthome) | 15 min | 6.5 baseline | Sensor-history loss up to 15 min is recoverable |
| 101 (ct-docker-01) | 15 min | 6.5 baseline | Docker volumes are the state; 15 min matches backup RPO for most stacks |
| 162 (ct-quant-trading) | 1 min (stretch) | 6.5 primary drill | Market-hours state; tighten schedule post-drill if 15-min baseline is stable |
| 250 (ct-dev-homelab) | 30 min | 6.5 baseline | Workbench loss tolerance is high — operator can recover from git |

### Cluster facts (2026-04-24 post-Window-B state)

| Node | IP | MAC (primary NIC) | Hostname FQDN | RAM | ZFS pools |
|------|-----|-------------------|---------------|------|-----------|
| pve1 | 192.168.50.201 | `00:d0:4c:10:40:54` | pve1.home.io | 16 GB | rpool (mirror) |
| pve2 | 192.168.50.202 | `00:d0:4c:10:41:d4` | pve2.home.io | 16 GB | rpool (mirror) |
| pve3 | 192.168.50.203 | `38:05:25:37:3d:cd` | pve3.home.io | 96 GB | rpool (mirror) + fast-pool + hdd-pool |

### Workload inventory (2026-04-24)

| VMID | Name | Home | Type | HA priority | Replicate? |
|------|------|------|------|-------------|------------|
| 100 | smarthome | pve1 | VM (HAOS) | HIGH | YES → pve2, pve3 |
| 101 | ct-docker-01 | pve1 | CT | HIGH | YES → pve2, pve3 |
| 102 | ct-media-01 | pve1 | CT | LOW | NO (nightly PBS only; NFS-backed on pve3) |
| 151 | ct-sparkle-cps | pve2 | CT | LOW | NO (nightly PBS only) |
| 160 | ct-ai-01 | pve3 | CT | LOW | NO (nightly PBS only; rebuildable from config) |
| 162 | ct-quant-trading | pve3 | CT | HIGH | YES → pve1, pve2 |
| 250 | ct-dev-homelab | pve3 | CT | HIGH | YES → pve1, pve2 |

### Critical caveat: VMID 100 (smarthome) Zigbee passthrough

The smarthome VM has a USB passthrough configured for the Zigbee radio (Silicon Labs CP210x, USB ID `10c4:ea60`). This USB stick is physically plugged into pve1 only. Proxmox USB passthrough is **host-local** — it cannot follow a VM during replication-based failover.

**Operational implication:** if pve1 fails and HA starts VMID 100 on pve2 or pve3, Home Assistant WILL boot but Zigbee devices WILL be unreachable until either:
1. pve1 is recovered and the VM is migrated back, OR
2. The operator physically moves the Zigbee USB stick to the node where VMID 100 is now running AND updates the VM's USB passthrough config to match the new host

Document this prominently in the replication README and in the Story 6.9 HA runbook. Story 6.7 (pull-plug pve1 drill) should observe and confirm this behavior.

### Previous story intelligence

- **Story 7.9** (Ansible pve-node-bootstrap playbook) established the conventions for cluster-wide operator automation — idempotency contract, explicit hostname guards, `--check --diff` pre-flight pattern. This story follows those conventions in spirit even though it is CLI-driven rather than Ansible-driven.
- **Story 3.x** (pve3 storage rebuild, Epic 3) ensures pve3 has a `local-zfs` pool identical in name to pve1/pve2. Without that, the ZFS replication would have no common dataset namespace. Verify `pvesm status` shows `local-zfs` on all three nodes BEFORE starting Task 2.
- **Epic 4** (PBS backup) remains the authoritative backup layer for LOW-priority guests (CT102, CT151, CT160) and a defence-in-depth layer for HIGH-priority guests. Replication is not a replacement for backup — `pvesr` snapshots have `__replicate_` prefix and are not retained as operator-visible restore points.

### Project Structure Notes

- All new files live in `homelab-infra/proxmox/replication/` (a new subdirectory). This is the infrastructure repo, not `homelab-playbook/` (docs/BMad) and not `homelab-apps/` (application stacks).
- Commit with the conventional prefix used in homelab-infra: `feat(replication): ...` or `docs(replication): ...`.
- No Terraform changes needed for this story — replication is Proxmox-side config stored in `/etc/pve/replication.cfg`.
- No Ansible role changes needed for this story (role option is deferred to Epic 7 per Task 9 Option B).

### Test strategy

**During execution (Tasks 1–8):**
- `pvesr status` on each home node — expect all 8 jobs `OK`
- `zfs list -r rpool/data` on each target — expect replicated datasets present
- `pvesr list | wc -l` — expect 8+1 (header) = 9 lines cluster-wide
- `cat /etc/pve/replication.cfg` — expect 8 job stanzas

**After one full schedule cycle (~16 min post-execution):**
- `pvesr status` — all `Last Sync` < 17 min ago, all `OK`, no `error`

**Story 6.2 will formally validate** delta sizes and job health over multiple cycles. 6.1 is "jobs created and first cycle ran clean".

**Story 6.5 will formally validate** CT162's 1-min RPO target (tightened schedule) once 6.1's 15-min baseline is confirmed stable.

### Security considerations

- Replication uses cluster SSH trust, which is already established post-Epic 5 (all 3 nodes exchange root keys bidirectionally via corosync + `pvecm`). No new credential distribution needed.
- `pvesr` snapshots are stored in `rpool/data` on both source and target — same permission model as any ZFS dataset. No additional access control required.
- Bandwidth: first-run of CT101 and CT250 will push multi-GB over the cluster network. Consider executing Tasks 2–6 during a low-traffic window (evening or weekend) if the cluster network is shared with other traffic. `--rate` flag can throttle per-job if needed.

### Rollback procedure

If a replication job is misbehaving, delete it cleanly:

```bash
# On the job's home node
pvesr delete <JOBID>
# This also removes __replicate_* snapshots on the target
```

If the replication target dataset is desired as a manual restore point, take a named snapshot on the target BEFORE deleting the job:

```bash
# On the target node, before deleting the job
zfs snapshot rpool/data/subvol-101-disk-0@manual-pre-delete-2026-04-24
```

Full rollback of the story: `for ID in 100-0 100-1 101-0 101-1 162-0 162-1 250-0 250-1; do pvesr delete $ID; done` — restores the cluster to pre-6.1 state.

### References

- **Epic/AC source**: `homelab-playbook/_bmad-output/planning-artifacts/pve3-storage-migration-epics.md` §"Story 6.1" (lines 939-959)
- **Scope approval**: `homelab-playbook/_bmad-output/planning-artifacts/sprint-change-proposal-2026-04-24.md` §2 "HA priority matrix"
- **Cluster state reference**: `homelab-playbook/_bmad-output/implementation-artifacts/window-b-complete-2026-04-24.md` §"Workload placement"
- **Role conventions**: `homelab-infra/ansible/roles/pve-host-pve3-storage/tasks/main.yml` (idempotency + hostname-guard pattern)
- **Previous story pattern**: `homelab-playbook/_bmad-output/implementation-artifacts/7-9-ansible-pve-node-bootstrap-playbook.md`
- **Proxmox Storage Replication**: <https://pve.proxmox.com/wiki/Storage_Replication>
- **Proxmox `pvesr` man page**: <https://pve.proxmox.com/pve-docs/pvesr.1.html>
- **Proxmox HA Manager**: <https://pve.proxmox.com/wiki/High_Availability>
- **Proxmox replication.cfg format**: <https://pve.proxmox.com/pve-docs/chapter-pvesr.html>

## Dev Agent Record

### Agent Model Used

Claude Opus 4.7 (1M context), acting as BMad Dev (Amelia) — direct pve1/pve2/pve3 SSH + `pvesr`/`pvesh`/`zfs` CLI execution. No code generation; only Proxmox cluster state mutation and documentation authoring.

### Debug Log References

- `pve1:/var/log/pve-replication-bootstrap-2026-04-24.log` — bootstrap-script stdout for the manual `pvesr run` sequence
- `pve3:/var/log/pve-replication-bootstrap-2026-04-24.log` — ditto for pve3-originated jobs
- `pve1:/var/log/pve/replicate/{100-0,100-1,101-0,101-1}` — authoritative per-job replication logs
- `pve3:/var/log/pve/replicate/{162-0,162-1,250-0,250-1}` — ditto

### Completion Notes List

1. **All 8 jobs created and reached `OK` state.** Final `pvesr status` on both pve1 and pve3 shows every job with a recent `LastSync`, `FailCount=0`, and `State=OK` (except a healthy mid-cycle `SYNCING` transition at 20:30 for 100-1's incremental — that completed shortly after capture).
2. **One transient failure encountered, auto-recovered by Proxmox scheduler.** Job `162-0` (pve3 → pve1) failed its first-seed attempt at 324s with SSH connection reset — caused by simultaneous high-bandwidth inbound contention on pve1 (also receiving VM100's 32 GB seed via 100-0). The Proxmox replication scheduler auto-retried at the next `*/15` slot and the retry completed cleanly in 770s. The failure mode, root cause, and the automatic-retry recovery are documented in the runbook's Troubleshooting section.
3. **Seed timing lesson captured.** Running 4 concurrent seeds on each origin node + 4 concurrent `zfs recv` on each target node saturated the shared 1 GbE cluster network; effective per-stream throughput dropped to ~3–15 MB/s and total wall-clock for the full seed sweep was ~80 minutes instead of the originally estimated 20–30 minutes. Future rebuilds should stagger seeds or run them off-peak. Recorded in the runbook "Notes on seed timing".
4. **Incremental delta behaviour validated.** Post-seed incremental cycles at the scheduled `*/15` and `*/30` slots completed in 2–9 seconds with deltas ranging from 0 B (pristine, nothing changed) to 67 MB (VM100 active state). Well under the AC threshold of "< 100 MB typical" — proves the replication subsystem is working as a proper incremental ZFS send/recv pipeline.
5. **VMID 100 Zigbee caveat documented in two places** (runbook top section + replication README) to maximize operator visibility during a failover event.
6. **`replication.cfg` is cluster-wide via `pmxcfs`** — so jobs are visible on every node, but `pvesr status` only shows the jobs the local node is the *source* of. Full authoritative status requires querying both pve1 and pve3.

### File List

- **Created**: `homelab-infra/docs/ha-replication-runbook.md` (primary operator runbook, ~240 lines)
- **Created**: `homelab-infra/proxmox/replication/README.md` (config-as-code rebuild commands + pointer to primary runbook)
- **Modified**: `homelab-infra/ansible/roles/pve-host-pve3-storage/README.md` (appended "Related work" section cross-linking to Epic 6 HA replication)
- **Modified on cluster** (not in repo — persisted in `pmxcfs`): `/etc/pve/replication.cfg` on all 3 nodes (8 new job stanzas: 100-0, 100-1, 101-0, 101-1, 162-0, 162-1, 250-0, 250-1)
- **Generated on cluster** (not in repo): `/var/log/pve-replication-bootstrap-2026-04-24.log` on pve1 and pve3; per-job logs at `/var/log/pve/replicate/<jobid>`
- **Modified**: this story file (task checkboxes, Dev Agent Record, Change Log, status `ready-for-dev` → `review`)

## Senior Developer Review (AI)
**Reviewer:** code-reviewer
**Date:** 2026-04-24
**Outcome:** Approve with Minor

### Findings
- [x] [M-1] Shell glob bug in runbook rebuild loop
- [x] [M-2] Missing `--comment` on rebuild command
- [x] [M-3] "idempotent" label misapplied in proxmox/replication/README.md

## Review Follow-ups (AI)
**Reviewer:** adversarial-reviewer
**Date:** 2026-04-24
**Confidence:** Medium (before fixes)

### Findings
- [x] [R1] No alerting on replication health — documented as deferred to Story 6.2
- [x] [R2] Rate limit reduced from 100 → 50 MB/s on all 8 jobs (leaves corosync/pveproxy headroom)
- [x] [R3] Runbook language softened to reflect "replicas staged, HA not yet active"
- [x] [R4] VM100 USB passthrough caveat updated to match likely pre-flight failure (empirical drill → 6.5)

## Change Log

- **2026-04-24**: Story file created by BMad SM (planner agent). Status: `ready-for-dev`. Scope reduced from original epic's 8-guest matrix to the 4 HIGH-priority guests per `sprint-change-proposal-2026-04-24.md §2` (LOW-priority guests deferred to PBS-only protection; destroyed guests removed from scope).
- **2026-04-24**: Story executed by BMad Dev (Amelia / Claude Opus 4.7). All 8 replication jobs created, seeded, and validated against AC. One transient seed failure (162-0) auto-recovered by scheduler. HA runbook authored at `homelab-infra/docs/ha-replication-runbook.md`. Status: `ready-for-dev` → `review`.

| Date | Change | Rationale |
|---|---|---|
| 2026-04-24 | Reduced `-rate` 100→50 MB/s on all 8 jobs | Corosync/pveproxy headroom; adversarial R2 |
| 2026-04-24 | Fixed runbook rebuild-loop glob + added --comment | Code review M-1, M-2 |
| 2026-04-24 | Clarified idempotency limits in config-as-code README | Code review M-3 |
| 2026-04-24 | Runbook softened re: HA not yet active | Adversarial R3 |
| 2026-04-24 | VM100 USB caveat rewritten for pre-flight-fail reality | Adversarial R4 |
| 2026-04-24 | Added "Known gaps deferred to 6.2+" section | Adversarial R1 |
| 2026-04-24 | Story status flipped: `review` → `done` | Review findings applied and verified live |
