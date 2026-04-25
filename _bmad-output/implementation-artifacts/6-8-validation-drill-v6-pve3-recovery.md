---
status: draft
epic: 6
story: 6.8
title: Validation drill V6 — node recovery (first run: pve2)
created: 2026-04-24
updated: 2026-04-25
author: BMad SM (via planner agent)
---

# Story 6.8: Validation drill V6 — node recovery (first run: pve2)

Status: draft

> **PVE 9.1+ note:** uses HA rules (node-affinity), not legacy HA groups — see Story 6.3 sprint-change note and `/home/developer/.claude/projects/-home-developer-workspace-homelab/memory/project_pve9_ha_rules_migration.md`. Lookup commands: use `ha-manager rules list` / `ha-manager rules config` (not legacy groups). `nofailback=0` (legacy group flag) is now per-resource `failback=1` (inverted boolean, set via `ha-manager set <sid> --failback 1`); `nofailback=1` ↔ `failback=0`. Drill semantics — recovery + reconvergence + failback policy — are unchanged. Terminology updated below where it appears.

## Sprint change note

**Pivot 2026-04-25** (operator + SM, paired with Story 6.7's pivot, recorded in sprint-status):

Story 6.8 was originally drafted (2026-04-24) as the recovery follow-on to a **pve3** pull-plug. Following the 6.7 pivot to use pve2 as the first-run TARGET_NODE (because ct:250 — the operator's dev environment — lives on pve3 and a pve3 drill disrupts the operator's working session), 6.8 is parameterised to recover whichever node 6.7 pulled. **First-run target: pve2.**

The recovery semantic — **prove quorum-return + ZFS-import + replication-reconvergence + per-resource `failback` policy + alert-resolution** — is **node-agnostic**. Recovering any node exercises the same code path. The first-run pve2 recovery has a smaller scope than a pve3 recovery would (only ct:151 to fail back, no pinned-resource auto-start to verify, no NFS-server-recovery to check), but the core recovery contract is identical.

**Trade-off:** the pve2 first run does NOT exercise: (1) ct:160 (pinned-pve3, NOT replicated) auto-starting on pve3's return — that is the only proof that pinned-offline-resources come back cleanly; (2) ct:162 / ct:250 failback semantics (the resources currently on pve3); (3) `shared-nfs-bulk` recovery and ct:102 stale-mount fix. All three are documented as **Deferred** below and preserved in the `## Future variant — pve3 recovery` section. The pve3-recovery drill runs after 6.7's Future variant (pve3 pull-plug) executes.

A future sprint-change-proposal (`sprint-change-proposal-pve2-pull-2026-04-25.md`) will formalise this pivot; that proposal file is not created as part of this rewrite.

## Story

As an operator,
I want the recovered cluster node (target: **pve2**) to rejoin cleanly, replication to reconverge in the correct direction, ct:151 to end up in a defensible final placement (per per-resource `failback` policy), and the four lost replication targets (100-0, 101-0, 162-1, 250-1) to come back to OK,
so that recovery from a node outage is a routine operational sequence — not a research project — and the cluster ends the maintenance window healthier than it started.

## Business value

Story 6.7 proves the cluster *survives* node loss. Story 6.8 proves the cluster *recovers* from it. A recovery path that requires ad-hoc diagnostic work every time is not an HA recovery — it's a dressed-up outage. The specific value for the first-run pve2 recovery:

1. **Cluster quorum returns to 3/3** — confirms corosync, pmxcfs, and the cluster trust relationship are intact after an unclean shutdown.
2. **Four replication jobs reconverge to TARGET_NODE** — jobs `100-0`, `101-0`, `162-1`, `250-1` (which target pve2) come back to `State=OK` after pve2 is up and reachable. This is the recovery side of 6.7's alert-fan-out stress test.
3. **ct:151 final placement reflects per-resource `failback` policy** — either auto-fails-back to pve2 (failback=1) or stays on the peer it landed on (failback=0). The drill pins which behaviour holds.
4. **Replication-direction-flip semantics are documented** — ct:151's home was pve2, replicating to pve1+pve3. After failover to (say) pve1, jobs `151-0` (pve2→pve1) and `151-1` (pve2→pve3) are nominally invalid until ct:151 returns to pve2 OR the operator reconfigures. 6.8 captures the observed Proxmox behaviour for the runbook.
5. **No surprise behaviours** — any CT in an unexpected state after recovery is a discovery that upgrades into a ticket.

**Deferred from this run** (preserved as `## Future variant — pve3 recovery`): pinned-pve3 CT (ct:160) auto-start on pve3's return; ct:162 failback per `failback=1`; ct:250 failback; `shared-nfs-bulk` recovery and ct:102 stale-mount fix. All four are exercised when the pve3 Future variant runs.

Without 6.8 completing cleanly, Epic 6's "HA is validated" claim is only half true — the cluster can take a hit but has never been shown to come back.

## Absorbed finding

None. 6.8 is a direct follow-on to 6.7 within the same maintenance window.

## Drill parameters (first run, paired with 6.7)

| Variable | First-run value | Notes |
|---|---|---|
| `TARGET_NODE` | `pve2` | Same as 6.7's TARGET_NODE. |
| `PEER_NODES` | `pve1`, `pve3` | The 2-of-3 quorum that survived during 6.7. |
| HA-managed resource that needs final placement | `ct:151` (sparkle-cps) | The only HA-managed resource that fled TARGET_NODE in 6.7. |
| Replication jobs that should auto-recover | `100-0`, `101-0`, `162-1`, `250-1` | All four target pve2; should return to State=OK after pve2 boots. |
| Pinned resources to verify auto-start | **none** | No strict-pinned resources on pve2 → no auto-start verification needed. Deferred to Future variant. |
| NFS server to recover | **none on pve2** | shared-nfs-bulk is served from pve3, untouched by this drill. Deferred to Future variant. |
| Recommended power-on method | Match 6.7's cut method | First run: Option A graceful → power on via front button OR `pvecm` from peer if remote IPMI exists. |

## Acceptance Criteria

Acceptance criteria are split into: **pre-condition gates** (AC-1), **recovery sequence** (AC-2..AC-6), **verification of expected behavior** (AC-7..AC-9), and **evidence capture + story closure** (AC-10..AC-11). All ACs use `TARGET_NODE` / `PEER_NODES` placeholders with the first-run concrete values inlined as `(first run: ...)`.

### Pre-condition gates

#### AC-1: Story 6.7 completed (pass or partial-pass) with TARGET_NODE currently offline

**Given** Story 6.8 cannot meaningfully run if TARGET_NODE is still up
**When** at the start of Task 0 I run `pvecm status` on each PEER_NODE
**Then** both report cluster membership = 2 (PEER_NODES only), TARGET_NODE marked offline / unreachable
**And** `ssh ${TARGET_NODE}` returns timeout or connection refused
**And** Story 6.7's evidence directory contains `v5-${TARGET_NODE}-pre-<date>.txt` + `v5-${TARGET_NODE}-post-<date>.txt` (first run: `v5-pve2-pre-<date>.txt` + `v5-pve2-post-<date>.txt`)
**And** ct:151 is currently running on a PEER_NODE — pve1 or pve3 (per 6.7 AC-9)
**And** if any of these is not true → **ABORT 6.8**; escalate to SM to correct 6.7 first

### Recovery sequence (ordered)

#### AC-2: TARGET_NODE boots cleanly and rejoins the cluster within 5 min

**Given** AC-1 holds and the operator is physically at the rack (or has remote power-on access)
**When** the operator powers TARGET_NODE back on (front button or re-plugs the cord — match the 6.7 cut method)
**Then** within **T+5 min** from power-on:
- TARGET_NODE BIOS + boot completes (expected: ~60 s to GRUB, ~60 s kernel+rpool import, ~30 s pve-services)
- `ssh ${TARGET_NODE} "date"` succeeds from the operator laptop (first run: `ssh pve2 "date"`)
- `ssh ${TARGET_NODE} "pvecm status"` shows `Quorate: Yes`, `Expected votes: 3`, `Total votes: 3`, `Flags: Quorate`
- `pvecm status` on each PEER_NODE agrees: 3 members, quorate
- `corosync-cfgtool -s` on all three nodes reports ring0 `active with no faults`
**And** if TARGET_NODE does not quorate by T+5 min → investigate per Rollback Path B; do NOT proceed to AC-3

#### AC-3: ZFS pools import cleanly on TARGET_NODE

**Given** AC-2 holds
**When** I run `ssh ${TARGET_NODE} "zpool status"` and `ssh ${TARGET_NODE} "zpool list"`
**Then**:
- `rpool` shows `state: ONLINE`, no degraded or faulted devices, no errors. *First-run pve2 specific:* rpool is the post-Window-B ZFS mirror (per `project_pve2_window_b_in_progress.md`); both vdev members must show ONLINE.
- Any additional pools on TARGET_NODE (verify with `zpool list`) show `state: ONLINE`. *First-run pve2:* expect only `rpool`. (pve3 has rpool + hdd-pool + fast-pool per the Future variant; pve1 currently has rpool only.)
- Every dataset is mounted (`zfs list` returns all expected datasets with mountpoints, no `-` in MOUNTPOINT column for datasets that should be mounted)
**And** if any pool is degraded / any dataset unmounted → investigate before AC-4; degraded pool likely means a disk needs resilvering; unmounted dataset may block HA restart of TARGET_NODE-resident CTs

#### AC-4: Replication jobs targeting TARGET_NODE resume and catch up

**Given** AC-3 holds
**When** I wait one full schedule interval (up to 15 min for `*/15` jobs, up to 30 min for `*/30`) after TARGET_NODE is back
**Then** `pvesr status` on each cluster node shows:
- For jobs that target TARGET_NODE — first run: `100-0` (vm:100 pve1→pve2), `101-0` (ct:101 pve1→pve2), `162-1` (ct:162 pve3→pve2), `250-1` (ct:250 pve3→pve2) — every one returns to `State=OK`, `FailCount=0` (or fail-counter reset on first successful sync), `LastSync` ≤ 2× schedule
- For jobs originating from TARGET_NODE — first run: ct:151's outbound jobs (presumably `151-0` to pve1, `151-1` to pve3) — depending on where ct:151 currently runs (see AC-7), these may be invalid/error until ct:151 migrates back, OR Proxmox has auto-adjusted the source. Document observed behaviour. [NEEDS OPERATOR CONFIRMATION: if Proxmox does NOT auto-flip, the jobs error until ct:151 is migrated back — AC-7 fixes it.]
- No replication job is running unboundedly (i.e. no single job locked at 100% CPU in a runaway state — `ps aux | grep pve-zsync` returns idle on all nodes)
**And** if any job is stuck in a partial state (`syncing` for > 10 min, `error` without a clear cause) → run the force-restart procedure (Dev Notes §"Force-restart a stuck replication job")
**And** Alertmanager `PVEReplicationFailed` for jobs `100-0`, `101-0`, `162-1`, `250-1` resolves within 2× schedule of TARGET_NODE coming up; resolution-push lands on operator phone

#### AC-5: Pinned-TARGET_NODE CTs auto-start within 5 min of quorum return — N/A first run

**Given** TARGET_NODE has rejoined the cluster for ≥ 5 min
**When** I check pinned resources on TARGET_NODE
**Then** for the **first-run pve2** scenario: there are no strict-pinned resources on pve2, so this AC is **vacuously satisfied** — there is nothing to auto-start.
**And** the evidence file records "no pinned resources on pve2; AC-5 N/A for first run; Future-variant pve3 recovery exercises ct:160 auto-start"
**And** for the Future variant pve3 recovery: this AC re-activates with `ct:160` as the resource; `pct status 160` on pve3 shows `running`; ha-manager status shows ct:160 `started` on pve3; Ollama API + Open WebUI HTTP smoke tests pass — see `## Future variant` section.

#### AC-6: TARGET_NODE-served NFS recovers and dependent CT mounts are restored — N/A first run

**Given** AC-2 holds
**When** I check for NFS exports served by TARGET_NODE
**Then** for the **first-run pve2** scenario: pve2 does not serve `shared-nfs-bulk` (that's pve3) and is not known to serve any other cluster-mounted NFS export. This AC is **vacuously satisfied** — there is no NFS recovery to perform. [NEEDS OPERATOR CONFIRMATION: if any pve2-resident NFS export was added since the architecture docs were last updated, list and recover it here.]
**And** the evidence file records "no pve2-served NFS exports; AC-6 N/A for first run; Future-variant pve3 recovery exercises shared-nfs-bulk + ct:102 stale-mount recovery"
**And** for the Future variant pve3 recovery: this AC re-activates — `pvesm status` shows shared-nfs-bulk `active`; ct:102 NFS mount is recovered per Dev Notes §"ct-media-01 NFS stale-mount recovery"; media library contents intact.

### Verification of expected behavior

#### AC-7: ct:151 final placement reflects per-resource `failback` policy

**Given** AC-4 holds (replication is re-established or the direction question is understood)
**When** I observe ct:151's placement after TARGET_NODE has been quorate for ≥ 15 min (one full replication cycle)
**Then** one of two outcomes is acceptable, and the acceptable one is the one that matches the per-resource `failback` setting from rewritten Story 6.3:
- **If `failback=1`** (PVE 9.1+ default; equivalent to legacy `nofailback=0`; failback to preferred node): `ha-manager status` should show ct:151 `started` back on pve2 (auto-migrated when pve2 returned and replication confirmed fresh).
- **If `failback=0`** (equivalent to legacy `nofailback=1`; stay on failover node): `ha-manager status` should show ct:151 still `started` on whichever PEER_NODE 6.7 failed over to; pve2 is a replica target again.
**And** the final placement is documented in the evidence file with the observed `failback` value for ct:151 (per-resource; `ha-manager config | awk '/^ct: 151/,/^$/'` output)
**And** if the observed placement does NOT match the configured policy → this is a bug; escalate. Likely cause: replication not yet fresh enough on pve2 for HA to consider failback safe, OR a latent bug in the pinning/failback logic — investigate and document.

[NEEDS OPERATOR CONFIRMATION: rewritten 6.3 sets `failback=1` per-resource for ct:151 (and standard members generally). Confirm the final decision and lock it in this story's evidence. SM-recommended default is `failback=1` for `standard` members where the originating node is known good (auto-failback reduces long-term ops load). Note: in PVE 9 this is set per resource via `ha-manager set <sid> --failback 0|1`, not at rule level.]

#### AC-8: No HA resource is in `error`, `fence`, or `queued` unexpectedly

**Given** AC-2..AC-7 hold
**When** I run `ha-manager status` from any node 30 min after TARGET_NODE has rejoined
**Then** every HA resource shows `started` on its expected node — first-run expected end state:
- vm:100 `started` on pve1 (pinned-pve1 rule, never moved)
- ct:101 `started` on its home (pve1 per architecture; or wherever the [NEEDS OPERATOR CONFIRMATION] resolves)
- ct:151 `started` per AC-7 `failback` policy (pve2 if failback=1; PEER_NODE if failback=0)
- ct:160 `started` on pve3 (pinned-pve3, never moved during pve2 drill)
- ct:162 `started` on pve3 (standard rule, never moved during pve2 drill)
- ct:250 `started` on pve3 (standard rule, never moved during pve2 drill)
**And** no resource is `error` / `fence` / `queued` / `disabled` without a documented reason
**And** any surprise state is recorded in the evidence file as a ticket for follow-up

#### AC-9: Cluster-wide health metrics are back to green

**Given** AC-8 holds
**When** I open Grafana HA Replication dashboard (`https://grafana.bi-services.be/d/ha-replication-6-2`) and the cluster overview (if it exists)
**Then**:
- All 8 replication-job state panels green (`pve_replication_state == 1`)
- `seconds_since_last_sync` metric for all jobs below 2× schedule
- Exporter-freshness panel green on pve1/pve2/pve3
- Prometheus `up{job="node-exporter-pve"}` = 1 for all three nodes
- Alertmanager firing-alerts count for `domain=replication` and `domain=cluster` returns to zero
**And** the `InstanceDown{instance="${TARGET_NODE}"}` alert that fired during 6.7 resolves within 5 min of AC-2 pass — first run: `InstanceDown{instance="pve2"}` resolves
**And** `PVEReplicationFailed` alerts for the four jobs (100-0, 101-0, 162-1, 250-1) resolve within 2× schedule of AC-2 pass
**And** the ntfy "resolved" pushes land on the operator phone

### Evidence capture + story closure

#### AC-10: Combined V5+V6 drill evidence artifact is committed

**Given** Stories 6.7 and 6.8 are both complete
**When** evidence capture ends
**Then** `homelab-playbook/_bmad-output/drill-evidence/v5-v6-${TARGET_NODE}-<date>.md` exists (first run: `v5-v6-pve2-<date>.md`) containing:
- Timeline merging 6.7 (cut) + 6.8 (recovery) — with T-0 and T_RTO from 6.7 and T_quorum-returned, T_replication-caught-up (per job), T_all-green from 6.8
- Measured RPO (from 6.7) and measured RTO (from 6.7) — for ct:151 in the first run
- Per-job replication-recovery times for the 4 jobs (100-0, 101-0, 162-1, 250-1)
- Per-resource `failback` observed behavior + final placement for ct:151 (from AC-7; PVE 9.1+ replacement for legacy `nofailback`)
- Grafana screenshots: before 6.7, just-after-cut (6.7), just-after-quorum-return (6.8), final green (6.8)
- ntfy notification log: every push received during the window (firing + resolved)
- Any operator interventions (force-restart replication, `ha-manager set`, manual migrate-back) with timestamps and rationale
- Raw dumps referenced from 6.7's `v5-pve2-pre-*.txt` and `v5-pve2-post-*.txt`, plus new `v6-pve2-recovered-<date>.txt` capturing final state
- Known follow-ups flagged inline (e.g. "HA-state-change alerting is a deferred gap — Epic 7"; "ct:160 pinned-auto-start untested in this run — Future-variant pve3 recovery")

#### AC-11: Maintenance window is closed and stories flipped

**Given** AC-1..AC-10 pass
**When** evidence is committed
**Then**:
- Story 6.7 status flips from `in-review` to `review` (awaiting QA signoff) — this was held open by 6.7 AC-13
- Story 6.8 status flips from `in-progress` to `review`
- The maintenance window log (or operator calendar) is closed
- The operator has ≥ 15 min of post-window observation with no new alerts before walking away
- The inputs for Story 6.9 are enumerated (Dev Notes §"Handoff to Story 6.9") — timeline + measured numbers + recovery steps + first-run-vs-future-variant notes

## Tasks

- [ ] **Task 0: Pre-condition gate** (AC-1)
  - [ ] **Task 0 prerequisite (6.9.1)**: run `sudo /usr/local/bin/drill-safety-preflight.sh --check --drill-name 6-8-pve-recovery` and verify exit 0 before proceeding to other Task 0 steps.
  - [ ] Set `TARGET_NODE=pve2`, `PEER_NODES="pve1 pve3"` in shell. Document in evidence.
  - [ ] Confirm 6.7 completed and TARGET_NODE is offline; 6.7 evidence exists on disk.
  - [ ] Confirm ct:151 is currently running on a PEER_NODE (pve1 or pve3).
  - [ ] Confirm operator is still in the maintenance window (phone-reachable, ≥ 30 min remaining in the combined 6.7+6.8 budget).
  - [ ] If any gate fails → **ABORT**.

- [ ] **Task 1: Power on TARGET_NODE and wait for quorum return** (AC-2)
  - [ ] Operator re-plugs the cord OR presses the front power button (matches the 6.7 cut option).
  - [ ] Start stopwatch at power-on.
  - [ ] From a PEER_NODE: `watch -n 5 pvecm status` for the membership change (2 → 3).
  - [ ] Log T_quorum-returned when TARGET_NODE shows in quorum.
  - [ ] If > 5 min → investigate. Likely causes: rpool slow-import, corosync trust issue, NIC didn't come up. Dev Notes §"Slow quorum return".

- [ ] **Task 2: Verify ZFS pool health and dataset mounts** (AC-3)
  - [ ] `ssh ${TARGET_NODE} "zpool status"` — all pools ONLINE, no errors.
  - [ ] `ssh ${TARGET_NODE} "zfs list"` — all datasets mounted.
  - [ ] `ssh ${TARGET_NODE} "zpool events -v | head -50"` — check for recent ZFS events (import, read errors).
  - [ ] If any pool is degraded → `zpool clear <pool>` MAY be safe; investigate event log first.

- [ ] **Task 3: Verify replication reconverges** (AC-4)
  - [ ] Watch `ssh ${TARGET_NODE} "pvesr status"` for one full cycle.
  - [ ] Cross-verify on PEER_NODES: `for n in pve1 pve3; do ssh $n "pvesr status"; done` (first run).
  - [ ] Specifically watch the 4 jobs that were broken: `100-0`, `101-0`, `162-1`, `250-1` — log per-job time-to-OK.
  - [ ] If any job shows persistent `error` → Dev Notes §"Force-restart a stuck replication job".
  - [ ] Document observed direction for ct:151's outbound jobs (TARGET_NODE→peer, peer→TARGET_NODE, or bidirectional).
  - [ ] Verify Alertmanager `PVEReplicationFailed` alerts resolve; ntfy resolved-pushes land.

- [ ] **Task 4: Verify pinned-TARGET_NODE CTs auto-start** (AC-5) — **N/A first run**
  - [ ] First run (pve2): no strict-pinned resources on pve2; record AC-5 as N/A in evidence.
  - [ ] Future variant (pve3): re-activate this task; check ct:160 auto-start; Ollama API + Open WebUI HTTP.

- [ ] **Task 5: Recover NFS server and dependent mounts** (AC-6) — **N/A first run**
  - [ ] First run (pve2): no pve2-served NFS exports; record AC-6 as N/A in evidence.
  - [ ] Future variant (pve3): re-activate; `pvesm status` shared-nfs-bulk active; ct:102 mount recovery.

- [ ] **Task 6: Verify ct:151 final placement per per-resource `failback` policy (PVE 9.1+; legacy `nofailback`)** (AC-7)
  - [ ] Read per-resource `failback` value: `ha-manager config | awk '/^ct: 151/,/^$/'` (PVE 9.1+ — `failback` is per resource, not per rule).
  - [ ] Observe ct:151's placement after 15+ min of stability.
  - [ ] Document observed placement vs configured policy. Any mismatch → investigate.
  - [ ] If operator WANTS to migrate ct:151 back manually (regardless of `failback`): `ha-manager crm-command migrate ct:151 pve2` — but only after AC-4 replication is confirmed caught up in both directions. Record the manual intervention.

- [ ] **Task 7: Final green-check** (AC-8, AC-9)
  - [ ] `ha-manager status` — every resource `started` on the expected node.
  - [ ] Grafana dashboards green; no firing alerts.
  - [ ] Prometheus `InstanceDown{instance="pve2"}` resolved.
  - [ ] PVEReplicationFailed alerts for 4 jobs resolved.
  - [ ] Phone ntfy shows the `resolved` notifications.
  - [ ] Record any surprise states as follow-up tickets.

- [ ] **Task 8: Capture combined V5+V6 evidence** (AC-10)
  - [ ] Write `v5-v6-pve2-<date>.md` combining 6.7 + 6.8 timelines with measured values and operator interventions.
  - [ ] Run the post-recovery snapshot script → `v6-pve2-recovered-<date>.txt`.
  - [ ] Grafana screenshots: at cut, at quorum-return, at final-green.
  - [ ] Commit the evidence directory to homelab-playbook (DO NOT push until 6.7 is also flipped to `review` — same commit is fine).
  - [ ] Explicitly note in the evidence: "AC-5 (pinned-auto-start) and AC-6 (NFS recovery) N/A for pve2 first run; deferred to Future-variant pve3 recovery."

- [ ] **Task 9: Close the maintenance window + hand off to 6.9** (AC-11)
  - [ ] Observe the cluster for ≥ 15 min post-green with no new alerts.
  - [ ] Flip Story 6.7 status → `review`.
  - [ ] Flip Story 6.8 status → `review`.
  - [ ] Close the maintenance window in the operator calendar.
  - [ ] Enumerate 6.9's inputs: the evidence file, the observed RPO/RTO, the observed per-resource `failback` behavior, any surprise states, AND the explicit list of "what was NOT tested in this first run" so 6.9's runbook clearly distinguishes verified-by-pve2-drill from deferred-to-pve3-drill.

## Dev Notes

### Recovery checklist (ordered commands)

```bash
TARGET_NODE=${TARGET_NODE:-pve2}
PEER_NODES=${PEER_NODES:-"pve1 pve3"}

# Task 1: Quorum return
for n in $PEER_NODES; do ssh $n "watch -n 5 pvecm status"; done   # wait for 3 members
ssh ${TARGET_NODE} "pvecm status"                                   # once SSH works

# Task 2: ZFS health
ssh ${TARGET_NODE} "zpool status"
ssh ${TARGET_NODE} "zpool list"
ssh ${TARGET_NODE} "zfs list"
ssh ${TARGET_NODE} "zpool events -v | head -50"

# Task 3: Replication
ssh ${TARGET_NODE} "pvesr status"
for n in $PEER_NODES; do ssh $n "pvesr status"; done

# Task 6: Final placement (PVE 9.1+: rules listed via `ha-manager rules`; failback is per-resource)
ssh pve1 "ha-manager rules config --resource ct:151"
ssh pve1 "ha-manager config | awk '/^ct: 151/,/^$/'"   # shows per-resource failback value
ssh pve1 "ha-manager status | grep ct:151"
# If operator wants manual migrate-back (after replication confirmed caught up):
ssh pve1 "ha-manager crm-command migrate ct:151 pve2"

# Task 7: Overall health
ssh pve1 "ha-manager status"
ssh pve1 "pvesr status"
# Grafana: https://grafana.bi-services.be/d/ha-replication-6-2
# Prometheus alerts: https://prometheus.bi-services.be/alerts
```

### Force-restart a stuck replication job

If `pvesr status` shows a job stuck in `error` or syncing forever:

```bash
# On the job's home node (the source side):
ssh <source-node> "pvesr disable <job-id>"
ssh <source-node> "pvesr enable <job-id>"
# Force-run one cycle:
ssh <source-node> "pvesr run --id <job-id> --verbose"
# Inspect the log:
ssh <source-node> "tail -50 /var/log/pve/replicate/<job-id>"
```

For the first-run pve2 recovery, the four jobs to watch are 100-0 (source pve1), 101-0 (source pve1), 162-1 (source pve3), 250-1 (source pve3). All four have a PEER_NODE as source — TARGET_NODE was the lost target. As soon as TARGET_NODE returns, the next scheduled run should rehydrate the target and clear the alert.

If the job error is "snapshot does not exist on target", the target lost its `__replicate_*` snapshot lineage (possible after an unclean shutdown — more likely on the source side, but worth checking on TARGET_NODE for the four incoming jobs). Recovery:

```bash
# Nuke the orphaned target dataset on TARGET_NODE (careful — this costs a full re-seed):
ssh ${TARGET_NODE} "zfs list -t snapshot rpool/data/subvol-<vmid>-disk-0 | grep __replicate_"
# If snapshots are missing, destroy the target dataset and let pvesr re-seed:
ssh ${TARGET_NODE} "zfs destroy -r rpool/data/subvol-<vmid>-disk-0"
ssh <source-node> "pvesr run --id <job-id> --verbose"  # will re-seed full
```

Full re-seed is MB-to-GB scale and takes minutes; schedule during quiet hours if possible.

### Slow quorum return

If TARGET_NODE doesn't rejoin quorum within 5 min:

- SSH fails: check from the console — is TARGET_NODE up? is the NIC up (`ip a`)? Is `/etc/hosts` correct (Window B lesson — installer may have set wrong IP)?
- SSH works but no quorum: `ssh ${TARGET_NODE} "systemctl status corosync"` — is it up? `ssh ${TARGET_NODE} "journalctl -u corosync -n 100"` — look for ring errors, auth failures, multicast issues. The Window B lessons flagged that bidirectional SSH trust and correct `/etc/hosts` are pre-conditions; if TARGET_NODE was recently reinstalled (NOT the case in the drill, but noted for completeness), these would be the first checks.
- `pvecm status` stuck: `systemctl restart corosync` on TARGET_NODE; then `systemctl restart pve-cluster`. If still stuck → escalate to Rollback Path B.

### Expected vs observed replication direction

Proxmox replication is **asymmetric** by design — a job has a fixed source (the home node) and a fixed target. When ct:151 fails over from pve2 to a PEER_NODE:

- ct:151's outbound jobs (presumably `151-0` pve2→pve1 and `151-1` pve2→pve3) have pve2 as source, but ct:151's LXC is now on a peer — so these jobs are **invalid** until either (a) the CT migrates back to pve2 or (b) the operator reconfigures with the peer as source.

Expected behavior based on Proxmox docs + community reports:
- Jobs will enter error state ("source dataset not found" or similar) until the CT's home changes.
- Per-resource `failback=1` (PVE 9.1+; equivalent to legacy group-level `nofailback=0`) should trigger an automatic failback migrate to pve2 once replication confirms pve2 is caught up — chicken-and-egg if replication is broken because the CT isn't on pve2 yet.
- In practice, the failback flow is: HA manager detects pve2 healthy → initiates migrate-back → Proxmox replication re-seeds from peer as source (may be a full-seed if the ZFS lineage diverged) → CT lands on pve2 → jobs `151-0` / `151-1` resume with pve2 as source, normal operation.

[NEEDS OPERATOR CONFIRMATION: the exact mechanism is what 6.8 measures. If observed behavior differs materially, 6.9's runbook needs the observed flow, not the predicted one.]

### Handoff to Story 6.9

Explicit enumeration of what 6.9 consumes from 6.7 + 6.8 (first-run pve2 edition):

1. `homelab-playbook/_bmad-output/drill-evidence/v5-v6-pve2-<date>.md` — the combined timeline + measurements
2. **Measured RPO for ct:151** (from 6.7 AC-12) — the only HA-managed resource that fled in this drill
3. **Measured RTO for ct:151** (from 6.7 AC-9) — target ≤120 s
4. **Per-job replication-recovery times** for jobs 100-0, 101-0, 162-1, 250-1 (from AC-4)
5. **Observed replication direction behavior on failover + failback** for ct:151 (from AC-4, Dev Notes)
6. **Observed per-resource `failback` policy behavior** for ct:151 (from AC-7; PVE 9.1+ replacement for legacy group-level `nofailback`)
7. **Any operator interventions** (from 6.7 + 6.8 timeline)
8. **Surprise states / tickets** — inputs to Epic 7 backlog
9. **Explicit list of what was NOT tested**: pinned-resource auto-start (ct:160 on pve3), critical-tier failback (ct:162), dev-tier failback (ct:250), shared-nfs-bulk recovery, ct:102 stale-mount fix. All deferred to Future-variant pve3 recovery — 6.9's runbook should clearly distinguish verified-by-pve2-drill from awaiting-pve3-drill.

### Grafana dashboards URL reference

- HA Replication: `https://grafana.bi-services.be/d/ha-replication-6-2`
- Prometheus alerts: `https://prometheus.bi-services.be/alerts`
- Cluster overview: `https://grafana.bi-services.be/d/cluster-overview` [NEEDS OPERATOR CONFIRMATION: verify UID]

### Post-recovery snapshot script

```bash
TARGET_NODE=${TARGET_NODE:-pve2}
DATE=$(date +%Y%m%d-%H%M)
OUT=homelab-playbook/_bmad-output/drill-evidence/v6-${TARGET_NODE}-recovered-${DATE}.txt
{
  echo "=== Drill V6 post-recovery snapshot ==="
  echo "TARGET_NODE: ${TARGET_NODE}"
  echo "Captured at: $(date -u)"
  for node in pve1 pve2 pve3; do
    echo "--- $node: pvecm status ---"
    ssh $node "pvecm status" 2>&1
    echo "--- $node: pvesr status ---"
    ssh $node "pvesr status" 2>&1
    echo "--- $node: zpool status ---"
    ssh $node "zpool status" 2>&1
    echo "--- $node: pct list ---"
    ssh $node "pct list" 2>&1
    echo "--- $node: qm list ---"
    ssh $node "qm list" 2>&1
  done
  echo "--- ha-manager status ---"
  ssh pve1 "ha-manager status"
  echo "--- ha-manager config (per-resource view, includes failback) ---"
  ssh pve1 "ha-manager config"
  echo "--- ha-manager rules list (PVE 9.1+) ---"
  ssh pve1 "ha-manager rules list"
  echo "--- ha-manager rules config (PVE 9.1+) ---"
  ssh pve1 "ha-manager rules config"
} > "$OUT"
echo "Wrote $OUT"
```

## Test strategy

Evidence-based pass criteria (first run, pve2):

1. **AC-2 (quorum by T+5 min)** = cluster is back. If slow → investigate; if fails → Rollback Path B.
2. **AC-3 (ZFS healthy)** = no data-path risk. Any degraded pool is a major escalation.
3. **AC-4 (replication caught up — 4 jobs to OK)** = RPO commitment re-established. Partial pass acceptable if operator understood the failover-direction semantics for ct:151's outbound jobs.
4. **AC-5 (pinned auto-start)** = N/A first run; satisfied vacuously.
5. **AC-6 (NFS recovery)** = N/A first run; satisfied vacuously.
6. **AC-7 (per-resource `failback` observed; legacy `nofailback`)** for ct:151 = documented, not surprise.
7. **AC-8 (no surprise HA states)** = clean ending.
8. **AC-9 (Grafana green + alerts resolved)** = observability closes the loop.
9. **AC-10 + AC-11 (evidence + story closure)** = story is reproducible.

Any partial failure becomes a captured finding for 6.9 or Epic 7.

## Security considerations

- **Replication direction after failover** is the subtlest security/integrity concern. If ct:151 ran on a PEER_NODE for 30 min and made state changes, then migrates back to pve2, the source of truth is the peer's copy — NOT the pre-cut pve2 copy. Proxmox replication handles this by sending the peer's current state back to pve2 as the new "canonical" replica; if this step fails silently (e.g. snapshot lineage diverged), a naïve failback could overwrite fresh state with stale state. Mitigation: AC-4 explicitly waits for replication to catch up in the correct direction before any manual migrate-back.
- **Split-brain during recovery**: while TARGET_NODE is booting but before it joins corosync, there is a brief window where 2-of-3 is quorate and 1-of-3 (TARGET_NODE) is not. If TARGET_NODE's HA LRM were to (erroneously) start ct:151 from its stale pre-cut replica during this window, we'd have ct:151 running on two nodes simultaneously → corruption. Mitigation: Proxmox HA is designed to prevent this — a non-quorate node cannot start HA resources. The `softdog` watchdog on TARGET_NODE would fire to reboot it if it attempted to hold a resource without quorum. Verification: AC-8's `ha-manager status` snapshot would catch a duplicate `started` state.
- **Fencing on recovery**: when TARGET_NODE rejoins, the CRM on the quorum majority has already fenced TARGET_NODE's resources. Rejoining does NOT undo the fence; resources stay on their new home until per-resource `failback` (PVE 9.1+; legacy `nofailback`) or manual migrate-back triggers re-balance. This is safe by design.
- **No new credentials, no new network surface**: this story changes no config, opens no new ports. All actions are operator-initiated via existing SSH trust.

## Rollback procedure

### Rollback path A: TARGET_NODE refuses to boot

- Power-cycle once (full cold reboot) — may clear a stuck NVMe firmware state.
- Check on-console for POST errors, ZFS import failures, kernel panic.
- If rpool won't import: `zpool import -f rpool` on the recovery shell (bootable USB recovery ISO may be needed).
- If one NVMe in the rpool mirror is dead: the mirror still imports degraded; operator can boot with one drive and replace-resilver the other. *First-run pve2 specific:* the post-Window-B mirror has both members in rpool; if one is dead, boot degraded and replace via `project_pve2_window_b_in_progress.md` lessons.
- Escalation: **cluster continues running 2-of-3 indefinitely**. ct:151 stays on its post-failover peer. Schedule an Epic-7 story for the rebuild; cluster is still HA for the replicated workloads.

### Rollback path B: TARGET_NODE boots but corosync won't quorate

- Check `/etc/hosts` on TARGET_NODE — must have the expected entry (Window B lesson: installer may have put the DHCP IP instead). First run: `192.168.50.202 pve2`.
- Check ring0 NIC is up: `ip a` should show vmbr0 with the expected IP. If not, network config drifted.
- Check time sync: `timedatectl status` — large clock skew can cause corosync auth failures.
- Restart corosync + pve-cluster: `systemctl restart corosync pve-cluster`.
- Nuclear option: `pvecm updatecerts --force` (refreshes cluster TLS); reboot TARGET_NODE.
- If quorum still fails → cluster is effectively 2-of-3 permanently; treat as Rollback Path A.

### Rollback path C: replication permanently broken for ct:151

- If replication cannot be re-established in either direction, ct:151's HA commitment is degraded.
- Options: (1) destroy target datasets and re-seed full (minutes of CT downtime on the source side) per Dev Notes §"Force-restart"; (2) accept temporarily-degraded RPO and open a ticket for a deeper investigation.
- Do NOT leave ct:151 running without a working replica — that's the exact pre-Epic-6 failure mode.

### Rollback path D: replication-job-target dataset on TARGET_NODE permanently broken

- If any of the 4 incoming jobs (100-0, 101-0, 162-1, 250-1) can't reseed cleanly to TARGET_NODE, destroy the target dataset and re-seed full (Dev Notes §"Force-restart"). Each is a minutes-long full sync; impact is non-zero on the source's IO but no service outage.
- Document the re-seed in the evidence file.

### Rollback path E: docs-only correction

- If 6.8 completes but the evidence file has errors / missed measurements → amend the evidence file and re-commit. No cluster state change. Standard docs rollback: `git revert <hash>` if a commit needs full undo.

## Future variant — pve3 recovery

**Status:** deferred. Execute after 6.7's Future-variant pve3 pull-plug runs — i.e. once ct:250 has been migrated off pve3 OR operator scheduled downtime explicitly accepts the dev-environment outage.

The original 6.8 plan (drafted 2026-04-24) recovered pve3 specifically. That plan is preserved here as a future variant because the recovery semantic is not redundant — pve3 is the only node that hosts a strict-pinned non-replicated resource (ct:160), the critical-tier replicated workload (ct:162), the dev-tier resource (ct:250 currently), and the `shared-nfs-bulk` NFS server. Recovering pve3 exercises:

1. **ct:160 (pinned-pve3) auto-starts on pve3's return** — `pct status 160` = running; ha-manager status shows ct:160 `started` on pve3 (NOT on any other node — it's pinned). This activates AC-5 (which is N/A for the pve2 first run). Application-level checks: `curl http://192.168.50.160:3000/` returns 200 (Open WebUI); `curl http://192.168.50.160:11434/api/tags` returns Ollama JSON. If ct:160 does NOT start within T+5 min of quorum return → check `ha-manager status` for `error` state; may need `ha-manager set ct:160 --state started`.

2. **ct:162 final placement per per-resource `failback`** — the critical-tier failback path. Identical to AC-7 but for ct:162. SM recommendation: `failback=1` for ct:162 (auto-failback reduces long-term ops load for the critical workload).

3. **ct:250 final placement per per-resource `failback`** — the dev-container failback path. Identical to AC-7 but for ct:250. Operator may consider `failback=0` for the dev container if post-failover thrashing risk outweighs the benefit; record decision.

4. **shared-nfs-bulk + ct:102 NFS stale-mount recovery** — activates AC-6 (which is N/A for the pve2 first run):
   - `pvesm status` on any node — shared-nfs-bulk reports `active`.
   - `showmount -e pve3` lists expected NFS exports.
   - ct:102 NFS mount may need manual recovery via `pct enter 102 -- stat /mnt/bulk` (if hangs → stale); recovery options:
     - **Full CT reboot** (simplest, ~30 s downtime): `pct reboot 102`
     - **In-container unmount + remount** (zero-downtime for non-media services): `pct enter 102 -- bash -c 'umount -l /mnt/bulk; mount -a'`
     - **Cluster-level storage reactivate**: `pvesm set shared-nfs-bulk --disable 1; sleep 5; pvesm set shared-nfs-bulk --disable 0` then re-trigger CT mount.
   - Operator should try option 1 first. Record which procedure worked — load-bearing input for 6.9.
   - Verify media library contents intact (random sample `ls`).

5. **ZFS pool layout differs**: pve3 has `rpool` + `hdd-pool` (5×22 TB RAIDZ1 + mirrored special vdev) + `fast-pool` per `project_pve3_storage_redesign.md`. AC-3 expands accordingly — verify all three pools ONLINE, no degraded devices, all datasets mounted. A degraded `hdd-pool` may indicate a disk needs resilvering — cold spare from Story 1.1 is on shelf for this case.

6. **Replication-recovery jobs differ**: when pve3 dies (in the Future-variant 6.7), the jobs that lose their target are different from the pve2 first run. Re-derive at the time of the future drill:
   - Jobs targeting pve3: presumably `100-1` (vm:100 pve1→pve3), `101-1` (ct:101 pve1→pve3), `151-1` (ct:151 pve2→pve3), and any others. Verify with `pvesr status` filtered for `local/pve3`.
   - Jobs originating from pve3: `162-0`, `162-1`, `250-0`, `250-1` (and `160-*` if ct:160 is replicated, which currently it isn't). These jobs lose their **source** when pve3 dies — they should not produce PVEReplicationFailed, they just stop firing until pve3 returns.

7. **Failback semantics for multiple resources simultaneously** — pve3 recovery exercises ct:160 (auto-start, no failback question) + ct:162 (failback) + ct:250 (failback) at once. Order of operations and any contention is documented for the runbook.

**Pre-flight extras for the pve3 variant:**
- Confirm ct:250 has been migrated off pve3 OR explicit acceptance of dev-outage.
- Confirm operator has reviewed the pinned-resource-auto-start escape hatch (`ha-manager set ct:160 --state started` if it doesn't auto-start).
- Confirm ct:102 (ct-media-01) is healthy pre-drill so any post-recovery stale-mount can be attributed to the drill, not pre-existing state.

**When this future drill runs**, copy this story file to `6-8b-validation-drill-v6-pve3-recovery.md`, set `TARGET_NODE=pve3`, and the body of the story applies — with AC-5 and AC-6 re-activated (no longer N/A), and the 6 additional concerns above expanded inline.

## References

- **Epic/AC source**: `homelab-playbook/_bmad-output/planning-artifacts/pve3-storage-migration-epics.md` §"Story 6.8" (lines 1053–1066)
- **Sprint change reference (future)**: `sprint-change-proposal-pve2-pull-2026-04-25.md` (not yet created — see Sprint change note above)
- **Story 6.7** (prerequisite): `homelab-playbook/_bmad-output/implementation-artifacts/6-7-validation-drill-v5-pull-plug-pve3.md` (filename retained for git history; first run pivots to pve2 — see 6.7 sprint change note)
- **Story 6.9** (consumes 6.8's evidence): `homelab-playbook/_bmad-output/implementation-artifacts/6-9-document-validated-ha-behavior-in-runbook.md`
- **Story 6.3** (HA node-affinity rules + resource registration; PVE 9.1+ rules model — supersedes original 6.4) — defines per-resource `failback` policy and rule membership observed here
- **Story 6.4** — superseded; absorbed into rewritten Story 6.3
- **Story 6.1** (replication jobs): `homelab-playbook/_bmad-output/implementation-artifacts/6-1-create-replication-jobs-per-4-5-matrix.md`
- **Story 6.2** (monitoring + dashboards): `homelab-playbook/_bmad-output/implementation-artifacts/6-2-verify-replication-state-and-deltas.md`
- **Story 1.1** (cold spare 22 TB WD Purple Pro): `homelab-playbook/_bmad-output/implementation-artifacts/1-1-procure-cold-spare-22-tb-wd-purple-pro.md` — escalation path
- **Story 1.5** (media library checksum manifest): `homelab-playbook/_bmad-output/implementation-artifacts/1-5-capture-media-library-checksum-manifest.md` — optional deep-verify path for ct-media-01 recovery (Future variant pve3)
- **Window B completion memory**: `/home/developer/.claude/projects/-home-developer-workspace-homelab/memory/project_pve2_window_b_in_progress.md` — the 5 lessons (esp. /etc/hosts + bidirectional SSH trust + NIC naming); ZFS mirror layout
- **PVE3 storage redesign target**: `/home/developer/.claude/projects/-home-developer-workspace-homelab/memory/project_pve3_storage_redesign.md` — rpool/hdd-pool/fast-pool layout reference for Future-variant AC-3
- **PVE3 + Local LLM (CT160 context)**: `/home/developer/.claude/projects/-home-developer-workspace-homelab/memory/project_pve3_local_llm.md` — Ollama + Open WebUI endpoints for Future-variant AC-5
- **sparkle-cps context (ct:151)**: `/home/developer/.claude/projects/-home-developer-workspace-homelab/memory/project_sparkle_cps.md`
- **Proxmox HA Manager**: <https://pve.proxmox.com/wiki/High_Availability>
- **Proxmox replication**: <https://pve.proxmox.com/wiki/Storage_Replication>
- **ZFS `zpool events`**: <https://openzfs.github.io/openzfs-docs/man/master/8/zpool-events.8.html>
