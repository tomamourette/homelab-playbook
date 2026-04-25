---
status: backlog
epic: 6
story: 6.12
title: PBS topology redundancy — close the dead-PBS-on-dead-node circular dependency
created: 2026-04-25
author: BMad SM (via planner agent)
depends-on: [2.10, 6.9]
---

# Story 6.12: PBS topology redundancy — close the dead-PBS-on-dead-node circular dependency

Status: backlog

## Story

As an operator,
I want a second Proxmox Backup Server datastore (internal replica on pve1, or offsite, or both) that holds a synchronised copy of every backup group currently stored on the pve3 PBS instance,
so that when pve3 itself is the dead node, ct:160 / ct:102 (and every other guest backed up to PBS) can still be restored to a surviving cluster member without waiting for pve3 hardware recovery.

## Business value

Story 6.9's adversarial review (R2) surfaced a **circular dependency in the recovery path**:

> The current PBS topology has the only PBS datastore on `hdd-pool/pbs` on **pve3** (Story 2.10). If pve3 dies permanently (mainboard failure, not just reboot), the PBS instance is gone with the host. Story 6.9's Scenario C documents "PBS restore" as the recovery path for ct:160 — but that path is **unreachable when pve3 itself is the dead node**. Same issue for ct:102 if pve1 dies and PBS-on-pve3 is somehow unreachable (network partition, simultaneous failure, ransomware encrypting the cluster, etc.).

This is a real architectural gap. ct:160 (`ct-ai-01`) is the catastrophic case: it's pinned to pve3 via iGPU passthrough (per `6-9-document-validated-ha-behavior-in-runbook.md` AC-3 Subsection 3c — *"CT160: stays offline until pve3 returns; no operator action"*) and Story 6.9 Scenario C names PBS restore as the only path to bring it up on a different node. With PBS-on-dead-pve3, that path doesn't exist.

Closing this gap means:

1. **ct:160 becomes recoverable to pve1 / pve2** when pve3 is permanently dead — restore from the replica PBS, then re-attach to a working iGPU (operator's choice; pve1 has an iGPU per `project_pve3_local_llm` memory) or run headless on a temporary basis.
2. **ct:102 (and any PBS-only-protected guest)** becomes recoverable when its home node dies and the pve3 PBS is also unreachable.
3. **The Story 6.9 §"Known non-recoverable / constrained cases"** can lose its "PBS-on-pve3 single-point-of-failure" caveat, replaced by a documented recovery procedure.
4. **HA promise becomes coherent**: Epic 6 promised RPO via pvesr replication AND backup retention via PBS. Single-PBS-on-pve3 means the second leg of the promise (long-window restore) collapses to zero when its own host dies. A second instance restores the promise.

Without this story, every future "pve3 dies permanently" tabletop ends with "ct:160 stays offline until we buy and rebuild a pve3 replacement". With it, the same tabletop ends in "restore ct:160 from pve1 PBS in <30 min".

## Absorbed finding from Story 6.9 adversarial review

This story **absorbs** Story 6.9's deferred adversarial finding **R2 — Circular recovery dependency: PBS lives on pve3, pve3-dies recovery path requires PBS** (see `6-9-document-validated-ha-behavior-in-runbook.md` Senior Developer Review section and the adversarial review artifact referenced therein).

The Story 6.9 runbook update intentionally documented Scenario C with the circular-dep caveat ("PBS restore from pve3" is named but not annotated as unreachable when pve3 is dead) because the fix is architecturally larger than a docs change — it requires standing up a second PBS instance. Story 6.9 was kept docs-only per its scope; the SM accepted the finding into the backlog as this story.

R2-adjacent context not absorbed here (listed so the Dev doesn't over-scope):
- **Live drill of pve3-permanent-death** — out of scope for 6.12. This story delivers the mitigation; validating it under live conditions is a future drill story (likely Epic 6.5-style or a 6.13).
- **Geographic / offsite redundancy** — Option B in the decision matrix below covers this. SM recommendation is to do Option A first (internal replica) and treat offsite as a separate Epic 7 story for true disaster recovery. If the operator picks Option C (both) up front, AC structure expands.
- **Encryption-key co-management** — addressed as a single AC + a Security Considerations note, not a full key-rotation story. PBS does not auto-share keys cross-instance; the operator must decide single-key (simpler restore) vs independent-key (defense-in-depth) at deploy time.

## Decision matrix — operator picks before Dev starts

This story has three viable architectures. The Dev cannot start until the operator picks one. Default AC structure below assumes **Option A**; if operator picks B or C, the Dev re-scopes the AC list using the same skeleton (deploy + datastore + sync + first-sync verify + drill + docs).

### Option A — Internal PBS replica on pve1 (or pve2)

Deploy a second PBS instance on pve1 as a sync target for the existing pve3 PBS. PVE PBS supports remote-sync (pull all groups every N minutes via the built-in Sync Job mechanism). Storage cost: ~150 GB on pve1 rpool/fast-pool (matches current pve3 PBS usage). Setup time: ~4-6 hours including drill.

**Pros:**
- Internal to cluster — no offsite contracts, no third-party trust, fully under operator control.
- Bandwidth is LAN-local — no upload caps, no metered links, sync interval can be tight (e.g. every 15 min).
- Restore latency from pve1 PBS to a pve1/pve2 guest is LAN-fast.
- Symmetric to existing pvesr replication mental model — "every load-bearing pve3 thing has a pve1 mirror".
- Setup uses the same `apt install proxmox-backup-server` + datastore-create dance from Story 2.10; minimal new operational surface.

**Cons:**
- If both pve1 + pve3 die simultaneously (fire, theft, lightning surge taking out a whole rack, ransomware encrypting all rpool drives), both PBS instances are gone. Doesn't protect against site-level disaster.
- pve1 storage headroom check needed — story 6.4-era rpool sizing may be tight after Epic 3 storage redesign.
- Adds a daemon and a port on pve1 (default 8007); minor attack-surface increase.

**Cost estimate:**
- Storage: ~150 GB on pve1 (current pve3 PBS datastore size as of 2026-04-25; **NEEDS OPERATOR CONFIRMATION** — run `proxmox-backup-manager datastore show pve3-pbs` on pve3 for live size before story start).
- Hardware: $0 (uses existing pve1).
- Bandwidth: LAN-local, negligible.
- Setup time: ~4-6 hours (1h deploy + 1h sync config + ~2h first sync + 1h drill + docs).

### Option B — Offsite PBS

Deploy PBS on a separate machine outside the homelab cluster — Raspberry Pi 5 / mini-PC at a parents' house, hosted VPS (e.g. Hetzner / OVH), or a NAS at a friend's home. Sync from pve3 via PBS's built-in remote-sync over SSH/HTTPS.

**Pros:**
- Geographic redundancy — true disaster recovery. Survives fire, theft, lightning, whole-cluster ransomware.
- Decouples backup retention from cluster health — even a "pve1+pve3 both dead" scenario is recoverable.
- Lower-trust radius from a recovery-of-recovery perspective: if the cluster is compromised, an offsite instance with key-isolated credentials is harder to also compromise.

**Cons:**
- Bandwidth cost — initial seed of ~150 GB over a residential uplink takes hours or days; ongoing incremental sync needs ~10-50 MB/day depending on backup churn.
- Latency for restore — pulling 150 GB back over the WAN to recover ct:160 could take 4-12 h depending on the link. RTO degrades from "minutes" to "many hours".
- Third-party / external dependency — VPS provider terms, parents' router uptime, SSH key management across a NAT boundary, dynamic DNS or VPN for routing.
- More operational surface: Tailscale / WireGuard / SSH tunnel to maintain, cert / fingerprint management for cross-site PBS sync.

**Cost estimate:**
- Hardware: $80-150 for a Raspberry Pi 5 + 256 GB SSD + case; OR $5-15/month for a hosted VPS with 250 GB storage.
- Bandwidth: ~150 GB initial seed (one-time); ongoing ~300 MB-1.5 GB/month incremental.
- Setup time: ~12-20 hours (hardware procurement + OS install + PBS install + WAN routing + sync config + first seed wait + drill + docs).

### Option C — Both (internal replica + offsite)

Do Option A first for fast recovery, then layer Option B on top for disaster scenarios.

**Pros:**
- Best of both: LAN-fast restore for the common "one node died" case + WAN-survivable for the rare "site disaster" case.
- Defense-in-depth — a compromise that takes out internal replicas still leaves the offsite copy.
- Aligns with industry-standard 3-2-1 backup rule (3 copies, 2 media, 1 offsite): primary on pve3 + replica on pve1 + offsite = compliant.

**Cons:**
- 3× the operational surface (three PBS instances to maintain, monitor, key-manage).
- Sequential sync chain (pve3 → pve1 → offsite, or pve3 → offsite directly with pve1 as a separate target) needs careful design to avoid sync-loop or duplicate-cost.
- Higher total cost (Option A + Option B combined).

**Cost estimate:**
- Sum of A + B: ~$80-150 hardware OR $5-15/month VPS + ~150 GB pve1 storage + ~16-26 hours setup.

### SM recommendation

**Pick Option A first.** It closes the immediate Story 6.9 R2 gap with the lowest cost, fastest setup, and minimal new operational surface. It directly enables ct:160 / ct:102 recovery to a surviving cluster member, which is the headline use case from the adversarial finding. Offsite (Option B) addresses a larger threat model (site disaster, ransomware) that is real but distinct from R2's "pve3 hardware died" scenario, and warrants its own dedicated story under Epic 7 (Reproducibility & Guardrails) where the operational pattern (cross-site sync, WAN routing, key isolation) gets first-class treatment. Operator can revisit Option C as a follow-up once Option A is operational.

The AC list below is structured for **Option A**. If the operator picks B or C up front, the AC list re-skeletons (same task shape: deploy + datastore + sync + first-sync verify + drill + docs) but specifics change (offsite hardware procurement adds 2-3 ACs; dual-target adds a second sync-config AC). Flag the choice in the operator's pre-Dev decision and the Dev re-scopes during Task 0.

## Acceptance Criteria

*(AC structure assumes Option A. Re-scope if operator picks B or C.)*

### AC-1: Pre-flight checks pass

**Given** Story 2.10 is `done` (existing pve3 PBS instance is healthy) and the operator has picked Option A
**When** I run pre-flight checks
**Then** the following are confirmed:
- `proxmox-backup-manager datastore show pve3-pbs` on pve3 returns a healthy datastore with `<measured>` GB used (record the live size in Dev Agent Record)
- pve1 `zpool list rpool` shows ≥150 GB free (or ≥ `<measured>` × 1.2, whichever is larger) — **NEEDS OPERATOR CONFIRMATION** of target dataset (rpool/data/pbs vs fast-pool/pbs vs a new dedicated dataset)
- pve1 cluster status `pvecm status` shows `Quorate: Yes` (don't deploy onto a degraded cluster)
- No conflicting service on pve1 port 8007 (`ss -lntp | grep 8007` returns empty)
- Backup of pve1's current state captured before any new package install (`apt list --installed > /root/pre-pbs-install-pkgs.txt` and a snapshot of `/etc`)

### AC-2: Second PBS instance deployed on pve1

**Given** AC-1 passes
**When** I install PBS on pve1 (via the same `apt install proxmox-backup-server` pattern Story 2.10 used on pve3, OR via a dedicated CT — see Dev Notes for the CT-vs-host trade-off)
**Then** `proxmox-backup-manager versions` on pve1 returns a clean install matching the pve3 PBS version
**And** the PBS web UI is reachable at `https://pve1:8007` (or the CT's IP if CT-based)
**And** PBS systemd units (`proxmox-backup-proxy`, `proxmox-backup`) are `active (running)` and `enabled`
**And** the install path (CT vs host) is documented in the Dev Agent Record with the rationale

### AC-3: PBS datastore configured on pve1

**Given** AC-2 holds
**When** I create a new datastore `pve1-pbs` pointing at the chosen path (`/rpool/data/pbs` OR `/fast-pool/pbs` OR equivalent — operator-chosen during AC-1)
**Then** `proxmox-backup-manager datastore show pve1-pbs` returns a healthy datastore
**And** retention policy matches pve3's (`proxmox-backup-manager prune-job list` and the matching keep-last/keep-daily/keep-weekly/keep-monthly settings copied verbatim from pve3)
**And** the datastore is registered as a backup target in the PVE cluster via `pvesm add pbs pve1-pbs --server pve1 --datastore pve1-pbs --fingerprint <fp> --username <user@pbs>` so manual backups can target it directly if needed
**And** PBS user `pve-backup@pbs` is created on the new instance with `DatastoreBackup` ACL on `/datastore/pve1-pbs` (matches Story 2.10 pattern)

### AC-4: Sync job from pve3 PBS → pve1 PBS configured

**Given** AC-2 and AC-3 hold
**When** I configure a PBS Sync Job on **pve1 PBS** that pulls from pve3 PBS as the remote source (PBS sync is pull-based — the target initiates)
**Then** `proxmox-backup-manager sync-job list` on pve1 shows the new job with:
- Remote: pve3 PBS (configured via `proxmox-backup-manager remote add pve3 --host pve3 --auth-id sync@pbs --fingerprint <fp>`)
- Remote store: `pve3-pbs`
- Local store: `pve1-pbs`
- Schedule: every 15 min (or operator-chosen interval — match the dominant pvesr cadence from Story 6.1)
- `remove-vanished: false` initially (safety: don't propagate deletions until first manual prune review)
**And** the sync user `sync@pbs` on pve3 PBS has `DatastoreReader` ACL on `/datastore/pve3-pbs` (read-only, least-privilege)
**And** the job's authentication uses an API token (not a password) stored on pve1 — token value committed only via the operator's secret manager, never to git

### AC-5: First sync completes successfully and pve1 PBS mirrors pve3 PBS

**Given** AC-4 holds
**When** I trigger the first sync manually with `proxmox-backup-manager sync-job run <jobid>` on pve1 PBS and wait for it to complete (estimated 30-90 min for ~150 GB on a LAN)
**Then** the sync job status shows `OK` with no errors
**And** `proxmox-backup-manager backup-group list pve1-pbs` returns the same group set as `proxmox-backup-manager backup-group list pve3-pbs` (group counts and group names match)
**And** for at least 3 spot-checked groups (recommended: ct/160, ct/102, ct/250), the snapshot count and most-recent snapshot timestamp on pve1 match pve3 within tolerance (snapshots since the sync started may differ by one cycle)
**And** datastore size on pve1 PBS is within ±5% of pve3 PBS (slack for PBS chunk-deduplication differences during sync)

### AC-6: Ongoing sync test — fresh backup propagates

**Given** AC-5 holds
**When** I trigger a fresh backup of a small CT (e.g. ct/250 or any low-churn CT) to pve3 PBS via PVE's normal backup mechanism (`vzdump <vmid> --storage pve3-pbs ...`)
**And** I wait for the next sync cycle (≤ 15 min, or the configured interval)
**Then** `proxmox-backup-manager snapshot list pve1-pbs <group>` shows the new snapshot on pve1 PBS within 2× the sync interval (≤ 30 min for a 15-min cadence)
**And** the snapshot on pve1 PBS verifies cleanly: `proxmox-backup-manager verify pve1-pbs <group>/<snapshot>` returns `OK` (chunk integrity check on the replica)

### AC-7: Disaster simulation — restore ct:160 (or stand-in) from pve1 PBS while pve3 PBS is offline

**Given** AC-5 and AC-6 hold and pve3 PBS has at least one ct:160 backup snapshot
**When** I simulate "pve3 PBS unavailable" by stopping the proxmox-backup-proxy service on pve3 (`ssh pve3 'systemctl stop proxmox-backup-proxy proxmox-backup'`) — and I do NOT touch pve3's PVE services, only PBS
**And** I attempt to restore ct:160 to pve1 (or pve2) using only the pve1 PBS instance: `pvesm set` to point ct:160 restore at `pve1-pbs`, then `pct restore <new_vmid> /var/lib/vz/dump/<dump>.vma --storage local-lvm` or equivalent PBS-restore path
**Then** the restore completes successfully without any read attempt to pve3 PBS (verifiable via no new connections to `pve3:8007` during the restore window)
**And** the restored CT boots on pve1/pve2 (note: ct:160 iGPU passthrough won't work on a different node — that's expected and out-of-scope; AC-7 validates **data recovery**, not GPU re-binding. Test passes if the CT boots far enough to mount its rootfs — driver/passthrough errors at GPU-init are acceptable.)
**And** after the test, pve3 PBS is restarted and a final sync runs cleanly (no split-brain, no data loss on either side)
**Note:** if the operator prefers not to test with ct:160 (production AI workload), use a stand-in test CT created for the drill. Document the choice in Dev Agent Record.

### AC-8: Documentation updated — runbook + arch docs + Story 6.9 caveat removed

**Given** AC-1 through AC-7 hold
**When** I update the docs
**Then** `homelab-infra/docs/ha-replication-runbook.md` has a new **PBS topology** section that:
- Diagrams the two-PBS topology (pve3 primary, pve1 replica)
- Documents the sync schedule + retention alignment
- Adds a "Restore when pve3 is dead" procedure (the operator-runnable version of AC-7)
- References this story as the closure of Story 6.9 R2
**And** `homelab/docs/architecture-homelab-infra.md` PBS section is updated to reflect two instances (not just one on pve3)
**And** Story 6.9's runbook update gets a follow-up note: the §"Known non-recoverable / constrained cases" caveat about PBS-on-pve3 single-point-of-failure is replaced with a reference to the new restore procedure
**And** `project_pve3_storage_redesign` memory file gets a note that Epic 6 closed the PBS-on-pve3 single-point-of-failure gap

## Tasks / Subtasks

- [ ] **Task 0: Operator picks Option A / B / C; Dev confirms scope** (pre-AC)
  - [ ] Capture operator decision in Dev Agent Record.
  - [ ] If Option B or C: re-scope AC list with offsite-specific ACs (hardware procurement, WAN routing, dynamic DNS / VPN, key-isolation). Coordinate with SM before starting.

- [ ] **Task 1: Pre-flight checks** (AC-1)
  - [ ] Measure live pve3 PBS datastore size — record in Dev Agent Record.
  - [ ] Verify pve1 storage headroom on the chosen target dataset.
  - [ ] Confirm cluster quorate, no port conflicts.
  - [ ] Snapshot pve1's pre-install state (apt list, /etc).

- [ ] **Task 2: Deploy PBS on pve1** (AC-2)
  - [ ] Decide CT vs host install (see Dev Notes — recommendation: CT for upgrade isolation, host if rpool storage path is preferred).
  - [ ] If CT: provision LXC with PBS (sizing: 4 GB RAM, 4 CPU, ~10 GB rootfs; bind-mount host dataset for the datastore).
  - [ ] If host: `apt install proxmox-backup-server` directly, mirroring Story 2.10's pve3 install.
  - [ ] Verify PBS daemon healthy, web UI reachable.

- [ ] **Task 3: Configure PBS datastore on pve1** (AC-3)
  - [ ] Create the datastore at the chosen path.
  - [ ] Set retention policy = pve3's policy (verbatim copy from `proxmox-backup-manager prune-job list`).
  - [ ] Register in PVE cluster as a backup target (`pvesm add pbs pve1-pbs ...`).
  - [ ] Create `pve-backup@pbs` user + ACL.

- [ ] **Task 4: Configure sync job pve3 → pve1** (AC-4)
  - [ ] Create `sync@pbs` API token on pve3 PBS (least-privilege: `DatastoreReader` on pve3-pbs only).
  - [ ] Add pve3 as a remote on pve1 PBS via `proxmox-backup-manager remote add`.
  - [ ] Configure sync-job with `remove-vanished: false` (safety) on a 15-min schedule.
  - [ ] Document API token storage location (operator's secret manager).

- [ ] **Task 5: Trigger first sync + spot-check** (AC-5)
  - [ ] `proxmox-backup-manager sync-job run` and monitor progress.
  - [ ] Compare group counts, snapshot timestamps, datastore sizes between pve3-pbs and pve1-pbs.
  - [ ] Document observed first-sync duration (informs long-term sync-window planning).

- [ ] **Task 6: Ongoing-sync drill** (AC-6)
  - [ ] Trigger a fresh backup of a low-churn CT to pve3 PBS.
  - [ ] Wait ≤ 30 min and verify the snapshot lands on pve1 PBS.
  - [ ] Run `proxmox-backup-manager verify` on the replicated snapshot.

- [ ] **Task 7: Disaster simulation** (AC-7)
  - [ ] Stop pve3 PBS (services only — NOT the host).
  - [ ] Restore ct:160 (or stand-in CT) from pve1-pbs to pve1 or pve2.
  - [ ] Verify CT boots far enough to confirm data integrity.
  - [ ] Restart pve3 PBS; confirm clean re-sync.
  - [ ] Capture timing numbers (restore-from-replica RTO).

- [ ] **Task 8: Documentation** (AC-8)
  - [ ] Add §"PBS topology" to `homelab-infra/docs/ha-replication-runbook.md`.
  - [ ] Add "Restore when pve3 is dead" procedure (operator-grade, copy-pasteable).
  - [ ] Update `homelab/docs/architecture-homelab-infra.md` PBS section.
  - [ ] Annotate Story 6.9 runbook caveat.
  - [ ] Update `project_pve3_storage_redesign` memory file.

- [ ] **Task 9: Commit, cross-reference, status flip**
  - [ ] Commit homelab-infra changes (PBS sync config + runbook) as one logical unit.
  - [ ] Commit homelab changes (arch doc) as one logical unit.
  - [ ] Flip story status `ready-for-dev` → `review`.

## Dev Notes

### CT-vs-host install for the pve1 PBS instance

Two reasonable patterns:

1. **PBS in an LXC on pve1** — cleaner upgrade isolation (PBS package upgrades don't touch the host), easier rollback (snapshot the CT), portable (CT can be migrated to pve2 if pve1 ever becomes the dead node — flips the story's recovery topology again). Bind-mount the chosen host dataset (e.g. `/rpool/data/pbs`) into the CT for the datastore. Sizing: 4 GB RAM / 4 vCPU / 10 GB rootfs is plenty for PBS itself; the datastore lives on the bind-mount.
2. **PBS on pve1 host directly** — same pattern as Story 2.10 used for pve3. Less abstraction. Coexists with PVE per Proxmox's documented support (already validated on pve3). Storage path is direct, no bind-mount layer.

**Recommendation: CT.** Reasons: (a) pve1 has more long-term workloads than pve3 had pre-PBS; isolating PBS in a CT keeps host upgrades simpler. (b) If pve1 ever becomes the dead node and we need to rotate which-host-runs-PBS, a CT migrates in minutes; a host-install requires re-bootstrapping. (c) Story 2.10's pve3 install was constrained by it being the post-Epic-3 fresh host — that constraint doesn't apply to pve1.

Document the choice + rationale in Dev Agent Record so the next operator (or future-Story-6.13) can reason about the topology.

### PBS sync-job mechanics

PBS sync jobs are **pull-based** — the target instance pulls from a remote source. Documentation: <https://pbs.proxmox.com/docs/managing-remotes.html>. Key syntax:

```bash
# On pve3 PBS: create a least-privileged token for the sync user
proxmox-backup-manager user create sync@pbs
proxmox-backup-manager user generate-token sync@pbs sync-token-pve1
proxmox-backup-manager acl update /datastore/pve3-pbs DatastoreReader --auth-id 'sync@pbs!sync-token-pve1'

# On pve1 PBS: register pve3 as a remote
proxmox-backup-manager remote add pve3 \
  --host pve3 \
  --auth-id 'sync@pbs!sync-token-pve1' \
  --password '<token-secret>' \
  --fingerprint '<pve3-pbs-fingerprint>'

# On pve1 PBS: create the sync job
proxmox-backup-manager sync-job create pve3-to-pve1 \
  --remote pve3 \
  --remote-store pve3-pbs \
  --store pve1-pbs \
  --schedule '*/15' \
  --remove-vanished false \
  --comment 'Story 6.12 — pve3 → pve1 PBS replica'
```

The `--fingerprint` value comes from `proxmox-backup-manager cert info` on pve3 PBS. The sync user (`sync@pbs!sync-token-pve1`) is least-privilege: read-only ACL on the source datastore, no write or admin rights anywhere.

### Encryption key handling — single-key vs independent-key

PBS does not auto-share encryption keys cross-instance. Two patterns:

**Pattern A — single shared encryption key (recommended for Option A internal replica):**
- Copy the existing pve3 PBS `master.key` (or whatever encryption key the cluster uses for backups) to pve1 PBS.
- Sync replicates the encrypted chunks as-is — pve1 PBS doesn't need to decrypt to sync.
- Restore from pve1 PBS uses the same key; operator's restore procedure is identical regardless of source instance.

**Pattern B — independent keys per instance (defense-in-depth):**
- pve1 PBS gets its own encryption key.
- Sync still replicates encrypted chunks (PBS sync doesn't care about your encryption); but if the operator wanted to decrypt and re-encrypt with the new key, that's a manual reseed (basically a fresh full backup).
- Restore from pve1 PBS would require operator to know which key was active at backup time. Operationally fragile.

**Recommendation: Pattern A.** Single shared key. The Story 6.9 R2 mitigation is about availability, not key-isolation. Independent keys is an Option B / Epic 7 concern (where the offsite instance has stronger threat-model requirements).

Document in Security Considerations + the runbook §"PBS topology".

### Storage path on pve1

**NEEDS OPERATOR CONFIRMATION** — pick one before Dev starts:

- `/rpool/data/pbs` — uses pve1's rpool. Default Proxmox mounted dataset. Headroom depends on Epic 3 storage redesign outcome on pve1 (see `project_pve3_storage_redesign` memory).
- `/fast-pool/pbs` — uses pve1's fast-pool (NVMe). Faster sync-write but PBS workload is sequential-heavy so the speed delta is small; uses up NVMe wear cycles unnecessarily.
- New dedicated dataset `/rpool/data/pbs-replica` — clean separation, easy to track usage independently.

SM leans toward a dedicated dataset on rpool. Operator decides during Task 1.

### Retention policy alignment

pve3 PBS retention (per Story 2.10 commit): copy verbatim. Don't drift the two retention policies — divergence creates restore-time surprises ("the snapshot exists on pve3 but pve1 already pruned it"). Single source of truth is pve3's prune-job; pve1 mirrors. If the operator ever wants to extend retention on the replica (longer-window backup), do it as a separate story with explicit reasoning.

### Ansible automation candidates

Out of scope for 6.12 itself (story is one-shot deploy + drill), but flag for follow-up:

- New role `homelab-infra/ansible/roles/pbs-replica/` that codifies install + datastore + sync-job for the pve1 instance.
- Existing role `pbs-server` (used by Story 2.10) might be parameterizable to handle both primary-pve3 and replica-pve1 patterns; alternatively split into `pbs-primary` + `pbs-replica`.
- Deferred to Epic 7 reproducibility work or a dedicated 6.12.1 if the operator wants the deploy to be re-runnable.

### Risk / failure modes during implementation

1. **Sync job credential leak** — API token on pve1 PBS must not land in git. Use the operator's secret manager (Vault / pass / env file in `/etc/pve` excluded from version control).
2. **`remove-vanished: true` too early** — if set at job creation and the operator later prunes pve3-pbs (legitimate retention), pve1-pbs follows the prune. Default `false` for the first sync cycle; promote to `true` only after confirming retention policy alignment + at least 7 days of healthy syncs.
3. **First sync collides with regular backup window** — 150 GB seed sync can saturate the pve3 → pve1 link for 30-90 min. Schedule first sync in a low-backup-window (e.g. early morning), not during the regular vzdump cron. Coordinate with `vzdump.cron` on the cluster.
4. **Encryption key mismatch on restore** — if operator accidentally creates a new key on pve1 PBS instead of copying pve3's, sync will succeed (encrypted chunks replicate fine) but restore will fail decryption. Verify key match at AC-2 / AC-3 boundary, before the first sync.
5. **PBS version drift** — pve1 PBS package version must be ≥ pve3 PBS (same or newer). PBS sync supports newer→older only with caveats; safer to keep matched. Document the version pin in Dev Agent Record.

### Test strategy

**Phase 1 (Tasks 1-3):** install + datastore — additive, no impact on existing pve3 PBS. Outcome: a healthy idle pve1 PBS instance.

**Phase 2 (Tasks 4-6):** sync configured + tested — first-time data flow from pve3 to pve1. No impact on pve3 PBS read/write capacity (sync uses a low-priority read path). Outcome: pve1 PBS mirrors pve3 PBS, ongoing-sync proven.

**Phase 3 (Task 7):** disaster simulation — the headline test. Stop pve3 PBS only (not the host). Restore from pve1 PBS to confirm the recovery path actually works without any pve3 PBS dependency. The "GPU passthrough won't work" caveat for ct:160 is expected; this AC validates data recovery, not full functionality. Acceptable impact: pve3 PBS unavailable for ~15-30 min during the drill (no scheduled backups during the window).

**Phase 4 (Task 8):** docs + architecture updates. Outcome: future operator reading the runbook can execute the recovery procedure without re-deriving it.

**Rollback:** every artifact is additive. To roll back, stop sync job + remove pve1 PBS datastore + remove the PBS package (or destroy the CT). pve3 PBS untouched throughout. No cluster state change.

### What "healthy" looks like post-Story-6.12

- Two PBS instances (pve3-pbs primary, pve1-pbs replica) both report healthy in their respective UIs
- Sync job runs every 15 min, success rate ≥ 99% over a 7-day window
- pve1 PBS group count + snapshot count matches pve3 PBS within one sync cycle
- Documented restore procedure (AC-8) executed once successfully (Task 7) — RTO timing recorded
- Story 6.9 runbook caveat about PBS-on-pve3 single-point-of-failure replaced with a positive recovery procedure
- No firing alerts under `domain=pbs` (alert wiring for the PBS sync itself is **deferred to Epic 7** — out of scope for 6.12; flag as a known gap in the runbook §"Known limitations")

### Prior art references

- **Story 2.10 (`2-10-deploy-pbs-datastore-on-hdd-pool-pbs.md`)** — established the PBS deploy pattern on pve3, the `proxmox-backup-server` package install on a PVE host, datastore creation, ACL setup, `pvesm add pbs` registration. The pve1 deploy mirrors this.
- **Story 6.9 (`6-9-document-validated-ha-behavior-in-runbook.md`)** — source of the R2 finding being absorbed; Scenario C (pve3 dies) names PBS restore but doesn't qualify "from where".
- **Story 6.2 (`6-2-verify-replication-state-and-deltas.md`)** — replication-monitoring pattern. The PBS sync job alerting (deferred to Epic 7) follows the same pattern (textfile collector → Prometheus → alert rule).
- **`feedback_ha_replication_audit_first.md`** memory — emphasises the audit-first stance for HA recovery work; this story aligns by validating recovery works (AC-7 drill) before declaring done.
- **`project_pve3_storage_redesign.md`** memory — context on Epic 3 storage redesign; consult for pve1 rpool / fast-pool sizing before AC-1.

## Security considerations

- **API token for sync user** — stored on pve1 PBS only, in `/etc/proxmox-backup/remote.cfg` or equivalent. Never committed to git. Operator's secret manager owns the canonical copy.
- **`sync@pbs` user is least-privileged** — `DatastoreReader` ACL on pve3-pbs only. Cannot prune, cannot write, cannot create users. Compromise of the token leaks read-access to encrypted backup chunks (still encrypted at rest); does not enable destructive operations on either instance.
- **Encryption key handling** — single shared key (Pattern A above) means a key compromise affects both instances. Acceptable for Option A internal replica because they're in the same trust radius (same cluster, same operator). Option B / offsite would warrant independent keys.
- **Network exposure** — PBS on pve1 listens on :8007 the same way as pve3. No new external exposure (LAN-only). PBS API is TLS-terminated by default.
- **`remove-vanished: false` initial setting** — protects against malicious or accidental prune on pve3 propagating to pve1. Promotion to `true` is an operational decision after the topology is proven stable.
- **Not in scope** — full audit-log replication between instances (PBS doesn't auto-share audit logs; if forensic alignment is needed, that's Epic 7 work).

## Rollback procedure

If Story 6.12 needs to be rolled back (e.g. pve1 storage pressure, sync causing cluster issues, operator decides to pivot to Option B):

1. Stop the sync job: `proxmox-backup-manager sync-job remove pve3-to-pve1` on pve1 PBS.
2. Remove the remote: `proxmox-backup-manager remote remove pve3` on pve1 PBS.
3. Remove the PBS storage from PVE: `pvesm remove pve1-pbs` on any cluster node.
4. Remove the datastore on pve1 PBS: `proxmox-backup-manager datastore remove pve1-pbs --keep-job-configs false --destroy-data <bool>` (operator decides whether to destroy the replica chunks or keep them on disk).
5. If host-install: `apt remove proxmox-backup-server` on pve1; if CT-install: stop and destroy the CT.
6. Free the dataset: `zfs destroy <chosen-dataset>`.
7. Revert sync user / token on pve3 PBS: `proxmox-backup-manager user delete sync@pbs`.
8. Revert docs (runbook + arch doc + memory file).

No impact on pve3 PBS — primary instance untouched throughout. Cluster state unchanged.

## References

- **Story 2.10 (PBS deploy)**: `homelab-playbook/_bmad-output/implementation-artifacts/2-10-deploy-pbs-datastore-on-hdd-pool-pbs.md`
- **Story 6.9 (Scenario C + R2 source)**: `homelab-playbook/_bmad-output/implementation-artifacts/6-9-document-validated-ha-behavior-in-runbook.md`
- **Story 6.2 (replication-monitoring pattern, prior art)**: `homelab-playbook/_bmad-output/implementation-artifacts/6-2-verify-replication-state-and-deltas.md`
- **HA replication runbook (target for AC-8 update)**: `homelab-infra/docs/ha-replication-runbook.md`
- **Architecture doc (target for AC-8 update)**: `homelab/docs/architecture-homelab-infra.md`
- **Memory: `feedback_ha_replication_audit_first.md`**: `/home/developer/.claude/projects/-home-developer-workspace-homelab/memory/feedback_ha_replication_audit_first.md`
- **Memory: `project_pve3_storage_redesign.md`**: `/home/developer/.claude/projects/-home-developer-workspace-homelab/memory/project_pve3_storage_redesign.md`
- **PBS sync docs**: <https://pbs.proxmox.com/docs/managing-remotes.html>
- **PBS user/ACL docs**: <https://pbs.proxmox.com/docs/user-management.html>
- **Proxmox 3-2-1 backup guidance**: <https://pbs.proxmox.com/docs/maintenance.html>

## Change Log

| Date | Change | Rationale |
|---|---|---|
| 2026-04-25 | Story file created by BMad SM (planner agent) | Absorbs Story 6.9 adversarial R2 (PBS-on-pve3 single-point-of-failure for ct:160 / ct:102 recovery). Decision matrix (Option A/B/C) frames operator pick; default AC structure assumes Option A (internal replica on pve1) per SM recommendation. |
