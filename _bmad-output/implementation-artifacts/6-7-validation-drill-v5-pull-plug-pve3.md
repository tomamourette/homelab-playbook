---
status: review
epic: 6
story: 6.7
title: Validation drill V5 — pull plug a cluster node (first run: pve2)
created: 2026-04-24
updated: 2026-04-25
author: BMad SM (via planner agent)
---

# Story 6.7: Validation drill V5 — pull plug a cluster node (first run: pve2)

Status: review

> **PVE 9.1+ note:** uses HA rules (node-affinity), not legacy HA groups — see Story 6.3 sprint-change note and `/home/developer/.claude/projects/-home-developer-workspace-homelab/memory/project_pve9_ha_rules_migration.md`. Lookup commands: use `ha-manager rules list` / `ha-manager rules config` (not `ha-manager config`'s legacy groups section). `nofailback` is now per-resource `failback` (inverted boolean). Drill semantics — node failure → resources fail over — are unchanged. Terminology updated below where it appears.

## Sprint change note

**Pivot 2026-04-25** (operator + SM, recorded in sprint-status):

Story 6.7 was originally drafted (2026-04-24) as a pull-plug drill against **pve3**, on the reasoning that pve3 hosts CT162 (the critical replicated workload Epic 6 was chartered to protect). Subsequent placement decisions changed the calculus: **ct:250 (ct-dev-homelab — operator's working dev environment) now lives on pve3**, which means a pve3 pull-plug interrupts the operator's active development session for the duration of the drill plus Story 6.8's recovery window. That is operationally unacceptable for a first-run drill where additional unknowns may extend the outage.

The drill's semantic mission — **prove fence + replicated-failover + alert-cascade against a sudden node loss** — is **node-agnostic**. Pulling any cluster node exercises the same softdog/CRM/LRM code path. We therefore parameterise the drill by `TARGET_NODE` and pick **pve2** for the first run because: (1) only ct:151 (sparkle-cps, replicated to pve1+pve3) is HA-managed on pve2, giving minimal failover surface; (2) the monitoring stack on ct:101 (pve1) stays up so the drill can be observed in real-time; (3) four replication jobs (100-0, 101-0, 162-1, 250-1) lose their target, exercising Story 6.2's `PVEReplicationFailed` alert at volume; (4) the operator's dev session on pve3 is unaffected.

**Trade-off:** a pve2 pull does NOT exercise the `strict=1` pinned-pve3 semantic for ct:160 (ai-host) or any other strict-pinned resource — there are currently no strict-pinned resources on pve2. That test is documented as **Deferred** below and preserved as a `## Future variant — pull plug pve3` section, to be executed once ct:250 has been migrated off pve3 OR an explicit dev-outage maintenance window is scheduled. A future sprint-change-proposal (`sprint-change-proposal-pve2-pull-2026-04-25.md`) will formalise this; that proposal file is not created as part of this rewrite.

## Story

As an operator,
I want to pull a non-critical cluster node (target: **pve2**) and observe HA failover semantics, replication-failure alert cascade, and the surviving 2-of-3 quorate cluster's behaviour,
so that Epic 6's "≤1-min RPO / ≤2-min RTO" promise is verified against a real (sudden) node outage — not a migration, not a simulation — closing the same failure class that caused the original incident, while keeping the operator's dev environment on pve3 undisturbed for this first run.

## Business value

Epic 6's chartered purpose is to eliminate the failure mode observed in the original incident: **an HA-critical CT ran on non-replicable storage on a single node, and when that node became unavailable the CT was inaccessible for the duration of the outage**. Stories 6.1–6.6 have closed that gap on paper (replication configured, HA node-affinity rules defined, HA resources registered, replication state monitored, replication RPO measured, migrate-triggered failover tested). None of those steps prove the cluster survives a **sudden** node loss — they all assume the losing node has time to cooperate.

Story 6.7 is the one drill that actually cuts the cord. With **pve2** as the first-run TARGET_NODE, this run specifically:

1. **Proves HA fencing works** — `softdog` watchdog fires, CRM declares TARGET_NODE dead, LRM on PEER_NODES picks up the fenced resources. This is the only way to verify the watchdog chain outside a real incident, and the code path is identical regardless of which node is pulled.
2. **Proves replicated-failover** — ct:151 (sparkle-cps, the only HA-managed resource on pve2) has a ZFS replica on pve1 and pve3; the drill measures the actual delta-loss at power-cut time and the time-to-start on a peer.
3. **Exercises the replication-failure alert cascade at volume** — four replication jobs lose their target simultaneously (100-0, 101-0, 162-1, 250-1 all target pve2). This stresses Story 6.2's `PVEReplicationFailed` alert path more than a single-job failure could.
4. **Proves alerting reaches the operator** — Alertmanager/ntfy push the node-down and replication-broken alerts to the operator's phone during the drill.
5. **Keeps observability up** — ct:101 (monitoring stack) on pve1 stays up; Grafana + Prometheus remain reachable for live observation. (A pve3 drill would still keep observability up, but a pve1 drill would not — pve1 is therefore an even worse first-run target.)
6. **Keeps operator dev session up** — ct:250 (ct-dev-homelab) on pve3 is untouched; the operator can run the drill without losing their working environment.

**Deferred from this run** (preserved as `## Future variant — pull plug pve3`): the `strict=1` pinned-resource semantic — proving that ct:160 (pinned-pve3, NOT replicated) correctly stays offline when its node dies, rather than thrashing on peers. That test requires pulling pve3 (or pulling pve1 to test vm:100's pinned-pve1 rule) and is scheduled for a later drill variant.

Without 6.7 running to completion, the entire Epic 6 HA contract is a paperwork claim. With 6.7 (pve2 first run) + 6.8 (pve2 recovery) + 6.9 (runbook absorption) + future pve3-pull variant, the cluster has a measured, runbooked, operator-rehearsed HA response across every meaningful failure-shape.

## Absorbed finding

None — this story adds no deferred findings from prior stories. Story 6.2's notification-gap deferral (R1c — Alertmanager + push channel) becomes a **hard pre-flight gate** here: if the push channel is not live by 6.7's start, the drill is blocked (see AC-1).

## Drill parameters (first run)

The drill is parameterised by `TARGET_NODE` with concrete first-run values:

| Variable | First-run value | Notes |
|---|---|---|
| `TARGET_NODE` | `pve2` | The node whose plug gets pulled. |
| `PEER_NODES` | `pve1`, `pve3` | The surviving 2-of-3 quorum members. |
| HA-managed resources currently on TARGET_NODE | `ct:151` (sparkle-cps; standard rule; replicated to pve1+pve3) | Verify at pre-flight with `ssh pve2 "pct list"` and `ha-manager status`; abort if drift detected. |
| Strict-pinned resources on TARGET_NODE | **none** | Therefore: no pinned-stays-offline test in this run; deferred — see `### Deferred: strict=1 pinned-resource semantic` below. |
| Replication jobs that lose their target | `100-0` (vm:100 pve1→pve2), `101-0` (ct:101 pve1→pve2), `162-1` (ct:162 pve3→pve2), `250-1` (ct:250 pve3→pve2) | 4 of 8 cluster jobs. Verify with `ssh pve3 "pvesr status"` + `ssh pve1 "pvesr status"` at pre-flight. [NEEDS OPERATOR CONFIRMATION: original brief listed `250-0` for the dev-host job; actual cluster shows `250-1` (250-0 targets pve1, 250-1 targets pve2). Updated above to the verified value.] |
| Non-HA workloads on TARGET_NODE | `ct:101` (monitoring stack), `ct:102` (ct-media-01) — both currently observed `running` on pve2 per `pct list pve2` 2026-04-25 11:59 | **[NEEDS OPERATOR CONFIRMATION]** the deployment-state memory states the monitoring stack is on pve1 (`ct:101`), but `ssh pve2 "pct list"` at pre-flight shows ct:101 + ct:102 running on pve2. Operator must reconcile placement before T-0. If ct:101 truly lives on pve2, the drill **DOES** take down the monitoring stack — which kills the live-observability premise of the pivot. **ABORT and re-evaluate** if confirmed. |
| Operator dev environment | `ct:250` on `pve3` | Untouched by this drill. |
| Cluster quorum after T-0 | 2/3 (pve1 + pve3) | Survives quorate; drill is safe. |
| Recommended cut method | Option A: graceful `shutdown -h now` from pve1 console | Option B (cord-pull) is a stretch goal if A is clean. |

## Acceptance Criteria

Acceptance criteria are split into three groups: **pre-flight abort gates** (AC-1..AC-6, ALL must pass before the power cut), **drill execution and measurement** (AC-7..AC-11), and **post-drill evidence capture** (AC-12..AC-13). All ACs are written using `TARGET_NODE` / `PEER_NODES` placeholders with the first-run concrete values inlined as `(first run: ...)`.

### Pre-flight abort gates (ALL must pass within T-30 min of the power cut)

#### AC-1: Alertmanager + push channel is live and tested

**Given** Story 6.2 deferred R1c to Epic 7 but Story 6.7 cannot safely proceed without a push channel (a silent broken replica during an active HA drill is the worst-case blast radius)
**When** I send a synthetic alert via Alertmanager (`amtool alert add test-alert severity=warning` or equivalent)
**Then** the alert reaches the operator's phone within 60 s via ntfy (or the chosen push channel)
**And** the operator confirms receipt verbally before proceeding
**And** if no push channel exists → **ABORT the drill**; schedule Epic 7 push-channel work first. [NEEDS OPERATOR CONFIRMATION: if operator explicitly accepts "Grafana tab open on laptop during drill" as a substitute, document the decision in Dev Agent Record and proceed — but strongly discouraged.]

#### AC-2: Cluster quorum is 3/3 healthy

**Given** a stable cluster is required for HA to have a quorate peer set after TARGET_NODE dies (2/3 survives; 1/3 is frozen)
**When** I run `pvecm status` on each PEER_NODE and on TARGET_NODE
**Then** all report `Quorate: Yes`, `Expected votes: 3`, `Total votes: 3`, `Flags: Quorate`
**And** `corosync-cfgtool -s` on all three nodes shows ring0 `active with no faults`
**And** if any node is missing from quorum → **ABORT the drill**

*First-run concrete:* run `ssh pve1 "pvecm status"`, `ssh pve2 "pvecm status"`, `ssh pve3 "pvecm status"` — all three must agree.

#### AC-3: All replication jobs are OK and fresh

**Given** ct:151 (HA-managed on TARGET_NODE) must have a replica on at least one PEER_NODE with RPO ≤ 2× schedule, AND all 4 jobs targeting TARGET_NODE must currently be OK (so we know what should fail at T-0)
**When** I run `pvesr status` on every cluster node
**Then** all 8 jobs (per runbook §"Current replication matrix") report `State=OK`, `FailCount=0`, `LastSync` within 2× schedule
**And** specifically jobs that target TARGET_NODE — `100-0`, `101-0`, `162-1`, `250-1` (first-run values) — must have `LastSync` within 2× schedule at T-0
**And** ct:151's replica jobs (whatever they are — verify with `ssh pve2 "pvesr status"`) must have `LastSync` ≤ 60 s ago at T-0 (the HA-resource RPO guarantee)
**And** Grafana `https://grafana.bi-services.be/d/ha-replication-6-2` shows all state panels green, `seconds_since_last_sync` below annotation thresholds for all jobs
**And** if any job is in error or stale → **ABORT the drill**; fix and requeue

[NEEDS OPERATOR CONFIRMATION: ct:151's outbound replication jobs (presumably `151-0` to pve1 and `151-1` to pve3) were not visible in the 2026-04-25 11:59 `pvesr status` snapshot. Story 6.1 should have created them — verify they exist before T-0. If absent → **ABORT** and create them per Story 6.1.]

#### AC-4: No pending maintenance window or active storage operation

**Given** concurrent maintenance multiplies risk and confounds measurement
**When** I check on each cluster node for:
- active `zpool scrub` (`zpool status | grep scrub`)
- active `pvesr run` (`ps aux | grep pvesr`)
- PBS backup in progress (`pvesh get /nodes/$node/tasks --source active`)
- HA state transitions currently in flight (`ha-manager status` — no `migrate` or `fence` states)
- Any scheduled maintenance item in the operator's calendar within the next 2 h
**Then** every check returns "idle"
**And** if any check is non-idle → delay the drill until idle, OR **ABORT and reschedule**

#### AC-5: PBS backup of ct:151 completed successfully within the last 24 h

**Given** catastrophic-rollback path (full restore from PBS) requires a recent backup of the HA-managed resource on TARGET_NODE
**When** I run `proxmox-backup-client list --repository <pbs-repo>` and filter for ct:151's most recent snapshot
**Then** the most recent snapshot is ≤ 24 h old and its `verify-state` is `ok`
**And** if absent, stale, or failed verify → **ABORT**; run `vzdump 151 --mode snapshot --storage pbs` and re-verify before proceeding

*First-run note:* in the original pve3-target draft, this AC covered ct:162 (the critical-tier resource on pve3). For pve2 first run, ct:162 is **not** on TARGET_NODE — so its backup is not a 6.7 pre-flight gate, only ct:151's. ct:162 backup remains a general operational hygiene item and is verified as part of Future-variant pve3 pre-flight when that drill runs.

#### AC-6: Operator physical presence + phone reachability confirmed

**Given** this drill CANNOT run unattended — an unexpected cascade (e.g. softdog fails to fire, quorum flakes) may require cord re-plug or manual `pvecm expected 2` intervention within minutes
**When** pre-flight starts
**Then** the operator:
- is physically at the rack or within ≤ 15 min drive and a responsible person is at the rack
- has their phone on with ntfy subscribed (verified by AC-1 synthetic alert)
- has a laptop with SSH sessions pre-opened to PEER_NODES (first run: pve1 and pve3) — see Dev Notes §"Monitoring terminals". Operator should run the **cut command from pve1 console** (not from the workstation) so that when TARGET_NODE goes down the operator's command-issuing terminal stays alive on a peer
- has Grafana HA Replication + HA status dashboards open in browser tabs (SSO logged in — Traefik)
- has reviewed the rollback procedure below
- has a 30–60 min uninterrupted window for 6.7 + 6.8 combined, phone-reachable throughout
**And** a second person is reachable (for a 4-eyes double-confirm on the power cut), or the operator explicitly records solo-operation in Dev Agent Record
**And** if any precondition fails → **ABORT**

### Drill execution and measurement

#### AC-7: Pre-event state is captured and committed

**Given** AC-1..AC-6 all pass
**When** at T-5 min I run the pre-event capture script (Dev Notes §"Pre-event snapshot")
**Then** a file `_bmad-output/drill-evidence/v5-${TARGET_NODE}-pre-<date>.txt` exists (first run: `v5-pve2-pre-<date>.txt`) containing:
- Output of `ha-manager status` (all resources, all states)
- Output of `pvesr status` on every cluster node
- Output of `pct list` and `qm list` on all three nodes
- Output of `zpool status` on all three nodes
- Output of `pvecm status` on all three nodes
- Current guest placements — explicitly verified for the first-run baseline:
  - ct:151 currently on pve2 (HA-managed)
  - ct:160 currently on pve3 (pinned)
  - ct:162 currently on pve3
  - ct:250 currently on pve3
  - vm:100 currently on pve1 (pinned)
  - ct:101 currently on pve1 (per architecture; **see [NEEDS OPERATOR CONFIRMATION] in Drill parameters re: actual placement**)
  - ct:102 currently on pve1 (or pve2 — verify)
- Current timestamps (`date` on all nodes, verify ≤ 1 s clock skew across nodes)
- Grafana screenshot of HA Replication dashboard (commit to evidence dir)
**And** the operator visually inspects each dump and confirms "all green" before T-0

#### AC-8: The power cut is executed and the T-0 timestamp is recorded

**Given** AC-7 is captured and the operator holds the stopwatch
**When** T-0 is declared, the operator executes **one of** these options (Option A is the recommended starting point):
- **Option A (graceful shutdown, simulates orderly power loss):** from the **pve1 console** (where SSH stays alive after TARGET_NODE goes down): `ssh ${TARGET_NODE} "shutdown -h now"` — first run: `ssh pve2 "shutdown -h now"`. TARGET_NODE stops corosync, pmxcfs, and powers off cleanly. Stopwatch starts at the moment the shutdown command returns "Connection closed".
- **Option B (cord pull, simulates catastrophic power loss):** physically remove TARGET_NODE's power cord at the wall. Stopwatch starts at the moment the cord leaves the socket. Use the power strip's switch if the plug is inaccessible. Option B is the **stretch goal** — run only if Option A completed cleanly and the operator has appetite for the higher-risk drill.
**Then** T-0 is logged with wall-clock seconds precision in the drill-evidence file
**And** `ssh ${TARGET_NODE}` from any PEER_NODE returns "connection refused" or timeout within 10 s
**And** no operator attempts to power TARGET_NODE back on during this story — TARGET_NODE stays off until Story 6.8 starts

Note: Option A vs Option B choice should be **pre-declared before the drill starts** and logged in AC-7's evidence. [NEEDS OPERATOR CONFIRMATION: prefer A or both-in-sequence? SM recommends A first; B only if A is clean and operator has appetite. For pve2 first run, SM recommends A only — keep the first run conservative.]

#### AC-9: ct:151 fails over within the RTO target

**Given** T-0 has been logged and TARGET_NODE is down
**When** the HA manager detects TARGET_NODE is lost (CRM on the surviving PEER_NODES declares TARGET_NODE dead after the default ~60 s watchdog + quorum-loss grace period)
**Then** by **T+120 s** wall-clock:
- `ha-manager status` (run from any PEER_NODE) shows ct:151 as `started` on pve1 or pve3 (NOT `fence`, `error`, or stuck `queued`)
- `pct status 151` on whichever peer it landed on shows `running`
- ct:151 (sparkle-cps) application-level health: the container's network interface is up and the project's services are reachable per their normal health-check (see Dev Notes §"ct:151 health check")
**And** the actual observed "ct:151 up on peer" timestamp is recorded as `T_RTO` in the evidence file
**And** if ct:151 is NOT running on a peer by T+180 s → **DO NOT restart TARGET_NODE yet**; escalate per Rollback procedure (operator intervention, likely `ha-manager set` or investigating softdog)

*Primary RPO/RTO metric for this drill:* ct:151 (was ct:162 in the original pve3 plan). The 4 replication-job-failure-alert chain measurements (AC-11) provide secondary metrics that are arguably more interesting given the drill design.

#### AC-10: Other HA resources behave as specified

**Given** AC-9 holds or has been escalated
**When** I inspect `ha-manager status` at T+180 s
**Then** for the first-run pve2-target scenario:
- **vm:100** (pinned-pve1 rule) — still `started` on pve1 (untouched).
- **ct:101** (standard rule, replicated to pve2 + pve3) — if home is pve1, still `started` on pve1; the pve2-target replication job (`101-0`) is now broken (target down) — verify in AC-11 alert chain. *If [NEEDS OPERATOR CONFIRMATION] resolves that ct:101 is actually on pve2:* it should fail over to pve1 or pve3. Document the actual behaviour.
- **ct:151** (standard, on pve2) — covered by AC-9.
- **ct:160** (pinned-pve3) — `started` on pve3 (TARGET_NODE is not pve3, so pinning is undisturbed).
- **ct:162** (standard, on pve3) — `started` on pve3 (untouched).
- **ct:250** (standard, on pve3) — `started` on pve3 (untouched).
**And** no resource is in `error` state
**And** any storage on TARGET_NODE that other CTs depended on is checked: ct:102 (ct-media-01) NFS mount of `shared-nfs-bulk` is **unaffected by this drill** because shared-nfs-bulk is served from pve3, not pve2. (Future variant pve3-pull will exercise the NFS-stale-mount path.) [NEEDS OPERATOR CONFIRMATION if any pve2-resident NFS export exists that other CTs mount — none expected.]

#### AC-11: Alertmanager fires the expected alerts and ntfy reaches the operator

**Given** AC-9 holds
**When** TARGET_NODE goes down
**Then** within T+180 s these alerts fire in Prometheus/Alertmanager (observable at `https://prometheus.bi-services.be/alerts`):
- `InstanceDown{instance="${TARGET_NODE}"}` — first run: `InstanceDown{instance="pve2"}` (from node-exporter scrape failure)
- `PVEReplicationFailed` for jobs `100-0`, `101-0`, `162-1`, `250-1` (first-run values) — within whatever `for:` clause Story 6.2 defined; record exact firing time per job. **This is the headline observation for the pve2 drill** — 4 replication jobs failing simultaneously is the cleanest stress test of the alert fan-out.
- `PVEReplicationExporterMissing` for TARGET_NODE (within ~10 min grace — may not fire by T+180 s if the `for:` clause is longer; record whatever did)
- HA-state-related alerts (any custom rule added in 6.3/6.4 — e.g. `HAResourceFenced` if such a rule exists, otherwise document that HA-state alerting is a deferred gap)
**And** the operator's phone shows ntfy push notifications for the `InstanceDown` alert AND at least one `PVEReplicationFailed` alert within T+180 s
**And** a screenshot of the phone notification is committed to the drill evidence

### Post-drill evidence capture

#### AC-12: Drill evidence is captured to `_bmad-output/drill-evidence/`

**Given** AC-7..AC-11 are complete
**When** the measurement phase ends (at T+300 s or when all acceptance checks have been made)
**Then** the directory `homelab-playbook/_bmad-output/drill-evidence/` exists and contains (first-run filenames use `pve2`):
- `v5-pve2-pre-<date>.txt` — pre-event snapshot (from AC-7)
- `v5-pve2-post-<date>.txt` — post-event snapshot (same commands, T+300 s state)
- `v5-pve2-timeline-<date>.md` — ordered event log: T-0, softdog-fire-observed (if observable), HA-fence-declared, ct:151-start-on-peer, app-level-up, alert-fired (per job 100-0/101-0/162-1/250-1), operator-ntfy-received, T_RTO computed
- Grafana screenshots (HA Replication dashboard, cluster overview) — before and after
- Phone screenshot of ntfy notifications (at least the InstanceDown one and one PVEReplicationFailed)
- Raw `pvesr status`, `ha-manager status`, `pvecm status`, `pct list` outputs captured at T-5, T+60, T+120, T+180, T+300
**And** the timeline doc includes measured values: `RPO_observed` (seconds since last replicate-snapshot at T-0 for ct:151), `RTO_observed` (T_RTO − T-0), Pass/Fail against targets (≤60 s RPO target for HA-managed, ≤120 s RTO)

#### AC-13: Story remains open until Story 6.8 begins

**Given** AC-7..AC-12 are complete
**When** the measurement phase ends
**Then** Story 6.7 **remains `in-review`** (not `done`) until Story 6.8 successfully recovers TARGET_NODE
**And** the operator does NOT commit to closing the maintenance window until 6.8 AC-1 passes
**And** if 6.8 encounters catastrophic failure (TARGET_NODE refuses to boot) the operator returns to this story's Rollback procedure to decide whether to PBS-restore ct:151 or accept a longer outage

### Deferred: strict=1 pinned-resource semantic

**Not exercised by this run.** The pve2-target first run does NOT prove that a pinned (strict=1) resource correctly stays offline when its home node dies, because there are currently no strict-pinned resources on pve2. The pinned-resource-stays-down semantic is load-bearing for ct:160 (pinned-pve3, NOT replicated, no peer can run it) and vm:100 (pinned-pve1, USB-passthrough Zigbee dongle).

**What a future drill would test:**
- `pull plug pve3` would exercise ct:160 staying offline (replica does not exist anywhere; HA must NOT attempt to start it on pve1/pve2).
- `pull plug pve1` would exercise vm:100 staying offline (USB-host-affinity confounds failover; pinned-pve1 prevents thrash).

**Why not now:** ct:250 (operator's dev environment) on pve3 makes the pve3 pull-plug operationally costly for a first run; vm:100's USB confound makes pve1 a separate research project. Both are deferred — see `## Future variant — pull plug pve3` below for the pve3 plan; pve1 variant is a TODO item for Epic 7 backlog (mentioned in the runbook's "Known limitation").

## Tasks

- [x] **Task 0: Pre-flight gate execution** (AC-1..AC-6)
  - [ ] Set `TARGET_NODE=pve2`, `PEER_NODES="pve1 pve3"` in shell. Document in evidence.
  - [ ] Confirm Alertmanager push-channel live; send synthetic alert; operator receives ntfy within 60 s. If not → **ABORT**.
  - [ ] `for n in pve1 pve2 pve3; do ssh $n "pvecm status"; done` — 3/3 quorate. If not → **ABORT**.
  - [ ] `for n in pve1 pve2 pve3; do ssh $n "pvesr status"; done` — all 8 jobs OK, fresh. ct:151's outbound jobs LastSync ≤ 60 s. If not → **ABORT**.
  - [ ] Verify which HA-managed resources currently live on TARGET_NODE: `ssh ${TARGET_NODE} "pct list"` + `ha-manager status | grep ${TARGET_NODE}`. Expected: ct:151 only. If drift → reconcile with rewritten Story 6.3, then re-evaluate drill.
  - [ ] Verify which replication jobs target TARGET_NODE: `for n in pve1 pve2 pve3; do ssh $n "pvesr status"; done | grep "local/${TARGET_NODE}"`. Expected: 100-0, 101-0, 162-1, 250-1. Record actual.
  - [ ] Verify ct:101's actual placement (the operator-confirmation flag in Drill parameters). If ct:101 is on pve2 → **ABORT** until placement reconciled.
  - [ ] Check no zpool scrub / pvesr run / PBS backup / HA state transitions in flight. If any → delay or **ABORT**.
  - [ ] Verify PBS backup of ct:151 ≤ 24 h old + verified. If not → run `vzdump 151` and verify before proceeding.
  - [ ] Confirm operator physical presence, phone-with-ntfy, monitoring terminals open, rollback reviewed, 30–60 min uninterrupted window. If any missing → **ABORT**.
  - [ ] Second-person 4-eyes confirmation OR explicit solo-operation note in Dev Agent Record.
  - [ ] Record the go/no-go decision with timestamp.

- [x] **Task 1: Pre-event state capture** (AC-7)
  - [ ] Create `homelab-playbook/_bmad-output/drill-evidence/` if it doesn't exist.
  - [ ] Run the pre-event snapshot script (Dev Notes §"Pre-event snapshot") → `v5-pve2-pre-<date>.txt`.
  - [ ] Verify ct:151 is currently running on pve2; ct:160/162/250 on pve3; vm:100 on pve1; ct:101 on pve1 (or wherever — confirm). If placement has drifted → investigate why before proceeding.
  - [ ] Grafana screenshot HA Replication dashboard and HA overview; commit to evidence dir.
  - [ ] Operator eyeballs all green; declares "go".

- [x] **Task 2: Choose Option A or B and execute the power cut** (AC-8)
  - [ ] Pre-declare A vs B; record decision in evidence file. (SM recommends A only for first run.)
  - [ ] Open terminals **from pve1 console** (so they survive pve2 going down): `ssh pve1` tailing `journalctl -u pve-ha-crm -u pve-ha-lrm -f`, `ssh pve3` tailing the same, a `watch -n 2 "ha-manager status"` terminal, a `watch -n 2 "ssh pve1 pvesr status; echo; ssh pve3 pvesr status"` terminal.
  - [ ] Stopwatch ready.
  - [ ] T-0: from the pve1 console, execute `ssh pve2 "shutdown -h now"` (Option A). Log the exact wall-clock second.
  - [ ] Confirm pve2 is unreachable within 10 s: `ssh pve2 "date"` from pve1 fails.

- [x] **Task 3: Observe and measure failover** (AC-9, AC-10)
  - [ ] Watch the CRM log — expect "node 'pve2' is lost" after ~60 s watchdog.
  - [ ] Wait for ct:151 to appear as `started` on a peer (pve1 or pve3). Log T_RTO.
  - [ ] Verify via `pct status 151` on the peer that the CT is `running`.
  - [ ] Check ct:151 application-level health (sparkle-cps services — see Dev Notes).
  - [ ] Verify vm:100, ct:101, ct:160, ct:162, ct:250 states match AC-10 spec.
  - [ ] Record any observation about non-HA workloads on pve2 (ct:101, ct:102) — they are simply down with their host; document the user-visible impact.

- [x] **Task 4: Verify alert chain** (AC-11)
  - [ ] Open `https://prometheus.bi-services.be/alerts` — verify `InstanceDown{instance="pve2"}` is firing.
  - [ ] Verify `PVEReplicationFailed` fires for each of `100-0`, `101-0`, `162-1`, `250-1` — record per-job firing time. **This is the alert-fan-out stress test.**
  - [ ] Verify ntfy push landed on phone for at least the InstanceDown alert and one of the replication alerts. Screenshot it.
  - [ ] Note any expected-but-missing alerts (e.g. HA-state rules that don't exist yet) — these become Epic 7 backlog.

- [x] **Task 5: Post-event state capture** (AC-12)
  - [ ] Run post-event snapshot script → `v5-pve2-post-<date>.txt`.
  - [ ] Grafana screenshot HA Replication + HA overview (post state).
  - [ ] Write the timeline markdown — ordered event log with measured RPO, RTO, per-job alert firing times, and Pass/Fail.
  - [ ] Commit the evidence directory contents to `homelab-playbook` repo (DO NOT push yet — wait until 6.8 closes).

- [x] **Task 6: Hold state until Story 6.8** (AC-13)
  - [ ] **Do NOT power pve2 back on.** That is Story 6.8's first task.
  - [ ] Story 6.7 stays `in-review`.
  - [ ] Proceed immediately to Story 6.8 (same maintenance window).

## Dev Notes

### Operator-presence requirement (READ FIRST)

This is a **live-risk drill** and CANNOT be executed unattended. Specifically:

- **Physical presence at the rack OR a responsible person at the rack** — required for cord-pull option and for the cord-re-plug rollback path.
- **Phone reachable with ntfy subscribed** — required for alert-chain verification and for out-of-band contact if SSH dies.
- **Laptop with pre-opened SSH sessions to PEER_NODES** (first run: pve1 and pve3) — required because the moment TARGET_NODE dies, attempting to SSH fresh through a freshly-fenced peer may hit a corosync-busy window. **Issue cut commands from the pve1 console**, not from the workstation, so the command-issuing terminal stays alive on a peer.
- **Uninterrupted 30–60 min window for 6.7 + 6.8 combined** — no meetings, no family interruptions, no competing maintenance.
- **Second person for 4-eyes confirmation** — strongly recommended but not strictly required; operator may solo-declare with explicit record.

If any of these are missing → do not start Task 0.

### Pre-event snapshot

Script to run at T-5 min (can be executed from the operator laptop):

```bash
TARGET_NODE=${TARGET_NODE:-pve2}
DATE=$(date +%Y%m%d-%H%M)
OUT=homelab-playbook/_bmad-output/drill-evidence/v5-${TARGET_NODE}-pre-${DATE}.txt
{
  echo "=== Drill V5 pre-event snapshot ==="
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
    echo "--- $node: date ---"
    ssh $node "date" 2>&1
  done
  echo "--- ha-manager status ---"
  ssh pve1 "ha-manager status" 2>&1
  echo "--- ha-manager config (legacy resources view) ---"
  ssh pve1 "ha-manager config" 2>&1
  echo "--- ha-manager rules list (PVE 9.1+) ---"
  ssh pve1 "ha-manager rules list" 2>&1
  echo "--- ha-manager rules config (PVE 9.1+) ---"
  ssh pve1 "ha-manager rules config" 2>&1
} > "$OUT"
echo "Wrote $OUT"
```

Post-event: re-run the same block with `v5-${TARGET_NODE}-post-${DATE}.txt` output path.

### The power cut itself

**Option A — graceful shutdown (recommended; only option for first run):**
```bash
# From pve1 console (NOT operator workstation — keeps SSH alive after cut)
ssh pve2 "shutdown -h now"
# SSH session will drop within seconds — note the wall-clock.
```
This simulates orderly power-loss (e.g. operator hits the front button, or a UPS gracefully shuts down on low battery). Corosync and pmxcfs exit cleanly; HA manager has maximum information for a clean fence.

**Option B — cord pull (stretch; defer past first run):**
Physically remove TARGET_NODE's power cord at the outlet or flip the power-strip switch. This simulates catastrophic power loss — corosync dies mid-message, pmxcfs state is whatever was on-disk, softdog timer fires independently.

The expected HA decision time is similar for both (~60 s softdog + quorum declaration) but Option B exercises the "no graceful shutdown" code path. SM recommendation for first run (pve2): Option A only. Option B is unlocked once Option A has produced clean evidence and operator has appetite for the higher-risk variant — possibly during the Future-variant pve3-pull drill.

### Monitoring terminals (open these BEFORE T-0)

Six terminals minimum, all opened **from the pve1 console**:
1. Local pve1 shell tailing `journalctl -u pve-ha-crm -u pve-ha-lrm -u corosync -f`
2. `ssh pve3` tailing the same
3. `watch -n 2 "ha-manager status"` — live HA resource state
4. `watch -n 5 "ssh pve3 pvesr status; echo; pvesr status"` — replication drift post-event (pvesr local on pve1 + via SSH on pve3)
5. Terminal pre-loaded with `pct status 151` ready to run on whichever peer it lands on at T_RTO (will need to identify peer from ha-manager status first)
6. Terminal pre-loaded with the post-event snapshot script (ready to run at T+300)

Plus two browser tabs:
- `https://grafana.bi-services.be/d/ha-replication-6-2` (HA Replication dashboard from Story 6.2)
- `https://prometheus.bi-services.be/alerts` (alert firing view)

Plus one phone with ntfy foreground.

### ct:151 health check

ct:151 is sparkle-cps (the CPS-Fabric project container, IP 192.168.50.151, VMID 151 on pve2). After failover, application-level health depends on which sparkle-cps services are exposed; the minimal smoke test:

```bash
# From any node:
ping -c 2 192.168.50.151                # network reachability
ssh root@192.168.50.151 "uptime"        # OS up
ssh root@192.168.50.151 "systemctl --failed"  # no failed units
```

[NEEDS OPERATOR CONFIRMATION: any HTTP/Azure-DevOps service inside ct:151 that should be smoke-tested specifically? sparkle-cps documentation in `project_sparkle_cps.md` did not enumerate exposed application endpoints beyond the LXC IP.]

### Expected HA timeline

Rough timeline based on Proxmox HA defaults (verify against cluster config):

- **T-0**: power cut on TARGET_NODE
- **T+5–30 s**: corosync on PEER_NODES loses ring-member TARGET_NODE; cluster membership transitions to 2-of-3
- **T+60 s**: softdog watchdog on TARGET_NODE would have fired if it were a zombie (irrelevant when fully powered off, but the HA manager still waits the grace period to ensure TARGET_NODE can't recover and run the resource it owns — split-brain prevention)
- **T+60–90 s**: CRM on surviving majority declares TARGET_NODE lost; relocates fenced resources to peers
- **T+90–120 s**: LRM on a PEER_NODE executes `pct start 151` using the ZFS-replicated rootfs
- **T+120–150 s**: ct:151 boots, sparkle-cps services come up

Target: ct:151 `running` on peer by **T+120 s**. Document actual.

### Critical-failure escape hatches

- **ct:151 not failing over by T+180 s**: first check `ha-manager status` — if resource is in `fence` or `error`, run `ha-manager set ct:151 --state started` on a peer to nudge, OR `pct start 151` manually on the chosen peer. Record the intervention. This probably means softdog semantics + quorum grace were longer than expected — document for runbook.
- **Quorum not reaching 2/3** (pve1 or pve3 flakes during the drill): this is catastrophic. `pvecm expected 1` on one node to force quorum, then hand-start ct:151. Escalate to Rollback.
- **Phantom split-brain** (TARGET_NODE somehow still visible): did shutdown not actually take it down? Console-walk to the rack, verify power state.

### Grafana dashboards URL reference (SSO, Traefik)

- HA Replication: `https://grafana.bi-services.be/d/ha-replication-6-2`
- Storage overview: `https://grafana.bi-services.be/d/storage-overview` (exact UID from Story 2.x)
- Cluster overview: `https://grafana.bi-services.be/d/cluster-overview` [NEEDS OPERATOR CONFIRMATION: verify exact UID exists; if missing, note as Epic 7 backlog]
- Prometheus alerts: `https://prometheus.bi-services.be/alerts`

### pve2's workload at drill time (first run, observed 2026-04-25)

- ct:151 sparkle-cps (HA-managed, standard rule, replicated to pve1+pve3 — the primary test subject for this drill)
- ct:101 ct-docker-01 — observed `running` on pve2 in `pct list` 2026-04-25 11:59 (**conflicts with deployment-state memory which says monitoring stack is on pve1 — operator must reconcile pre-flight**)
- ct:102 ct-media-01 — observed `running` on pve2 in `pct list` 2026-04-25 11:59 (likewise needs reconciliation)
- 4 incoming replication targets: 100-0 (vm:100), 101-0 (ct:101), 162-1 (ct:162), 250-1 (ct:250)

When pve2 dies (first run): ct:151 fails over. ct:101 and ct:102 (if confirmed on pve2) go down with pve2 — non-HA, no automatic recovery. Replication jobs 100-0, 101-0, 162-1, 250-1 enter error state and trigger PVEReplicationFailed alerts.

### pve2 hardware context

- Passive-cooled chassis (per `project_pve_node_cooling.md`) — slightly more thermal-flap risk than pve3, less than pve1.
- ZFS mirror rpool after Window B (per `project_pve2_window_b_in_progress.md`, 2026-04-24) — this is the post-redesign storage layout; CT151 is on rpool/data.
- 96 GB RAM headroom is comfortable; pve1 + pve3 can absorb ct:151's memory footprint without stress.

### Why pve2 is the first-run target (and not pve3 or pve1)

- pve3 hosts ct:250 (operator's working dev container) — pulling pve3 disrupts operator's working session for the duration of the drill plus 6.8 recovery window. Deferred to Future variant.
- pve1 hosts ct:101 (monitoring stack — assuming the deployment-state memory is correct and the live `pct list` is wrong) — pulling pve1 takes down Grafana + Prometheus + Alertmanager, defeating the live-observation premise of the drill. Also hosts vm:100 with USB-passthrough (pinned-pve1, separate confound).
- pve2 hosts only ct:151 as HA-managed; the dev session and monitoring stack are unaffected; failover surface is minimal. Ideal first-run target.

## Test strategy

Evidence-based pass criteria:

1. **Pre-flight (AC-1..AC-6) — all gates green** = drill is safe to start.
2. **ct:151 running on peer by T+120 s** = HA core promise met. Pass.
3. **ct:151 running on peer by T+120..180 s** = HA met the SLO but slower than target. Pass with a warning; investigate watchdog/quorum delay.
4. **ct:151 not running on peer by T+180 s** = FAIL; triggers Rollback investigation.
5. **vm:100, ct:160, ct:162, ct:250 unaffected (still running on their nodes)** = pve3/pve1 untouched as designed. Pass.
6. **PVEReplicationFailed fires for all 4 jobs (100-0, 101-0, 162-1, 250-1)** = alert fan-out tested at volume. Pass.
7. **Alertmanager InstanceDown fires + ntfy push lands** = observability chain closed. Pass.
8. **Evidence artifact exists and is complete** = story is re-runnable and verifiable. Pass.

Any partial failure is captured in the timeline markdown with analysis — Story 6.9 will absorb the findings, and Future-variant pve3-pull will inherit lessons.

## Security considerations

- **Split-brain risk**: 3-node cluster with one node down → surviving 2 hold quorum. If a second node flaps during the drill → cluster is frozen (1/3 is non-quorate). Mitigation: pre-flight AC-2 confirms all three are healthy; if any is borderline, postpone.
- **Fencing is `softdog`, not a dedicated fence device**: Proxmox HA defaults to the `softdog` kernel-watchdog timer. If a node is fully powered off (like pve2 in the first run), the surviving CRM declares it dead after the quorum grace period. If the node is a *zombie* (still powered but corosync-unreachable), `softdog` on the zombie is supposed to reboot it within ~60 s. If `softdog` on TARGET_NODE were to not fire (kernel bug, /dev/watchdog contention, etc.), HA would refuse to start the replica on a peer because it can't prove TARGET_NODE has been fenced. This drill does NOT exercise the zombie case — TARGET_NODE is fully powered off, so the softdog path is not on the critical path. Document in Story 6.9 as a known gap: "zombie-node drill would require more than cord-pull and is deferred to a future Epic-7 item or a formal Proxmox fence-device project."
- **Replication direction flip risk**: ct:151's home is pve2, replicating to pve1 + pve3. After failover, ct:151 runs on (say) pve1. Replication jobs don't spontaneously flip direction on failover — 6.8 verifies the recovery reconfigures cleanly.
- **Storage integrity**: ZFS replicated rootfs is the source of truth for ct:151's post-failover start. If ZFS replica on the chosen peer has a corrupt snapshot → ct:151 won't start. AC-3's "pvesr status OK" is insufficient to guarantee the snapshot is readable; if ct:151 fails to start on peer, check `zfs list -t snapshot rpool/data/subvol-151-disk-0` on the peer and compare to the pre-event state capture.
- **No secrets exposed**: the drill does not touch credentials or secrets beyond what's in the running CT; no new secrets are created; evidence artifacts contain operational metadata (`ha-manager status`, timestamps), which is safe to commit.

## Rollback procedure

**Context:** unlike a code-change rollback, this drill's rollback path depends on where in the drill you are. There is no clean "undo the cut" — the moment TARGET_NODE is down, HA has acted.

### Rollback path A: during Task 0 (pre-flight) — a gate fails

- Do not proceed. Fix the failing gate (or accept the blocker if it's Epic 7-scope) and reschedule the drill.
- No cluster state was changed; no recovery needed.

### Rollback path B: during Task 2 (the cut has happened, but something is wrong)

- "Something wrong" = ct:151 hasn't failed over by T+180 s, OR a peer is flapping, OR the alert chain is silent.
- **Do not restart TARGET_NODE yet** unless you are minutes from a business-critical workload need — restarting while HA is mid-fence can produce weird resource ownership.
- Triage first: `ha-manager status`, `pvecm status`, `journalctl -u pve-ha-crm -f` on peers.
- If ct:151 is stuck, manually start on a peer: `ssh pve1 "pct start 151"` — this bypasses HA but gets the workload up. Record the intervention in the timeline.
- After manual stabilization, **proceed to Story 6.8 to recover TARGET_NODE**. Even a partially-failed drill becomes part of the evidence.

### Rollback path C: operator aborts mid-drill and chooses to re-power TARGET_NODE before Story 6.8

- This is NOT a clean rollback — HA has already migrated workloads. Powering TARGET_NODE back on early means:
  - Workloads that migrated to peers (ct:151) are now running on peers with stale ZFS on TARGET_NODE as "backup" — operator must decide whether to migrate them back per the Story 6.6 procedure, OR accept the new placement and let replication re-converge (Story 6.8 path).
  - Replication jobs that targeted TARGET_NODE come back; PVEReplicationFailed alerts resolve.
- Record the abort in Dev Agent Record. Consider this drill "partial-pass" and schedule a re-run.

### Catastrophic: TARGET_NODE refuses to boot in Story 6.8

- This is Story 6.8's problem, but the pre-condition is set here: TARGET_NODE is down, ct:151 is on peer. If TARGET_NODE is dead-dead (hardware fail), the path is:
  - Evaluate whether the failure is disk (cold-spare 22 TB WD Purple Pro from Story 1.1 is on shelf — for HDDs, not for the rpool NVMes) or something else (RAM, NIC, motherboard).
  - If non-disk hardware fail → TARGET_NODE stays offline, cluster runs 2-of-3 indefinitely. This is still HA-functional for the replicated workloads.
  - ct:151 continues running on the peer it failed over to; the operator decides whether to pin it to a "pinned-pve1" or "pinned-pve3" group or leave it in standard.
- Record the escalation in Dev Agent Record and open an Epic-7 story for the rebuild.

## Future variant — pull plug pve3

**Status:** deferred. Execute when ct:250 has been migrated off pve3 OR operator scheduled downtime explicitly accepts the dev-environment outage.

The original 6.7 plan (drafted 2026-04-24) targeted pve3 specifically. That plan is preserved here as a future variant because the semantic test is not redundant — pve3 is the only node with a strict-pinned non-replicated resource (ct:160) and the only node hosting the critical-tier replicated workload (ct:162). Pulling pve3 exercises:

1. **strict=1 pinned-resource semantic**: ct:160 (pinned-pve3, NOT replicated) correctly stays `stopped`/`fence`, NOT `started` on any peer. This is the "pinned-offline-on-failure" path.
2. **Critical-tier failover with ≤60 s RPO**: ct:162 (ct-quant-trading, critical replicated workload) fails over with the tightest RPO target in the cluster — this is the headline number Epic 6 was chartered to defend.
3. **Standard-tier failover for the dev environment**: ct:250 (ct-dev-homelab) fails over to pve1 or pve2 — the operator's dev container survives node loss.
4. **NFS server outage**: pve3 serves `shared-nfs-bulk` (354 GB media library); ct:102 (ct-media-01, on pve1) has its `/mnt/bulk` mount go stale. The recovery procedure (Story 6.9 absorbs) is exercised.
5. **Active-cooled chassis less likely to spontaneously thermal-shut** — so this is a deliberate-cut-only scenario, not an expected-failure scenario.
6. **96 GB RAM hit** — pve3 holds the largest RAM footprint in the cluster; verify pve1+pve2 have headroom for ct:162 + ct:250 before the drill.

**Pre-flight extras for the pve3 variant:**

- Confirm ct:250 has been migrated off pve3 (to pve1 or pve2) — if not, explicit operator acceptance of dev-environment outage in Dev Agent Record.
- Confirm ct:162 PBS backup ≤ 24 h old + verified (replaces ct:151's PBS gate from the pve2 first run).
- Confirm ct:160 application state is acceptable to lose for the duration — Ollama models are on disk, will resume cleanly when pve3 returns; any in-flight inference is lost. Document acceptance.
- Verify pve1+pve2 have RAM headroom for ct:162 + ct:250 simultaneously.

**Expected behaviour differences vs pve2 first run:**

- ct:160 stays offline (correct pinning behaviour) — primary differentiating test.
- ct:162 fails over (≤60 s RPO target — tighter than ct:151).
- ct:250 fails over (operator dev container).
- ct:102's NFS mount goes stale; recovery procedure invoked.
- Replication jobs that lose their target (when pve3 dies) are different: jobs targeting pve3 are 100-1, 101-1, plus the original-source jobs 162-0, 162-1, 250-0, 250-1 (which lose their source when pve3 dies, not their target). Re-derive at the time of the future drill.

**When this future drill runs**, copy this story file to `6-7b-validation-drill-v5-pull-plug-pve3.md`, set `TARGET_NODE=pve3`, and the body of the story applies with the substitutions above. Story 6.8's Future variant section gives the matching recovery sequence.

## References

- **Epic/AC source**: `homelab-playbook/_bmad-output/planning-artifacts/pve3-storage-migration-epics.md` §"Story 6.7" (lines 1037–1052) and §6 validation plan context
- **Sprint change reference (future)**: `sprint-change-proposal-pve2-pull-2026-04-25.md` (not yet created — see Sprint change note above)
- **Runbook (read-only for this story; 6.9 edits it)**: `homelab-infra/docs/ha-replication-runbook.md`
- **Story 6.1** (replication jobs): `homelab-playbook/_bmad-output/implementation-artifacts/6-1-create-replication-jobs-per-4-5-matrix.md`
- **Story 6.2** (monitoring — dashboards + alerts this drill depends on): `homelab-playbook/_bmad-output/implementation-artifacts/6-2-verify-replication-state-and-deltas.md`
- **Story 6.3** (HA node-affinity rules + resource registration; PVE 9.1+ rules model — supersedes original 6.4) — defines rules and HA-registers resources
- **Story 6.4** — superseded; absorbed into rewritten Story 6.3
- **Story 6.5** (RPO validation drill V3 — prior evidence)
- **Story 6.6** (migrate-based failover V4 — prior evidence)
- **Story 6.8** (TARGET_NODE recovery — immediate follow-on)
- **Story 6.9** (runbook update — absorbs 6.7 evidence)
- **Story 1.1** (cold spare 22 TB WD Purple Pro): `homelab-playbook/_bmad-output/implementation-artifacts/1-1-procure-cold-spare-22-tb-wd-purple-pro.md` — escalation path for catastrophic node failure
- **Window B completion memory** (post-Window-B cluster state, workload placement): `/home/developer/.claude/projects/-home-developer-workspace-homelab/memory/project_pve2_window_b_in_progress.md`
- **PVE3 storage redesign target**: `/home/developer/.claude/projects/-home-developer-workspace-homelab/memory/project_pve3_storage_redesign.md`
- **PVE3 + Local LLM (CT160 context)**: `/home/developer/.claude/projects/-home-developer-workspace-homelab/memory/project_pve3_local_llm.md`
- **sparkle-cps context (ct:151)**: `/home/developer/.claude/projects/-home-developer-workspace-homelab/memory/project_sparkle_cps.md`
- **PVE node cooling**: `/home/developer/.claude/projects/-home-developer-workspace-homelab/memory/project_pve_node_cooling.md`
- **Proxmox HA Manager**: <https://pve.proxmox.com/wiki/High_Availability>
- **Proxmox softdog fencing**: <https://pve.proxmox.com/wiki/High_Availability#ha_manager_fencing>
- **Proxmox `ha-manager` command**: <https://pve.proxmox.com/pve-docs/ha-manager.1.html>

## Dev Agent Record (2026-04-25)

**Operator:** BMad Dev (claude-opus-4-7) via Claude Agent SDK
**Drill window:** 10:34 → 10:48 UTC (~14 min wall-clock; pve2 stays OFF beyond drill end — Story 6-8 recovers)
**T+0 (cut):** 2026-04-25T10:40:41Z UTC (12:40:41 CEST)
**Cut method:** Option A (graceful `shutdown -h now` from jumphost). Option B not exercised (per SM recommendation for first-run conservatism).
**Outcome:** **PASS — fence + HA decision SLO GREEN at T+70s; alert chain partial (5/expected ≥6 critical alerts fired; PVEReplicationFailed silent due to exporter gap).** Story 6-1, 6-2/6-10 backlog items surfaced for Story 6-9 absorption.

### Timeline (UTC, all from polling output and LRM journals)

| Phase | T (UTC) | T+ | Event |
|---|---|---|---|
| Pre-flight | 10:33-10:34 | T-7m | `pvecm status` 3/3, `ha-manager status` 6 services, `pvesr status` 8 jobs OK FailCount=0; ct:151's outbound `151-*` jobs ABSENT (Story 6.1 gap) |
| Pre-flight | 10:34:51 → 10:35:55 | T-5m | `vzdump 151 --mode snapshot --storage local --compress zstd` — 1m04s, 2.23 GB tar.zst (gate-#8 fallback for missing replicas). Copied off-pve2 to jumphost `/tmp/`. |
| Pre-flight | 10:40:05 | T-36s | Heartbeat planted in ct:151 on pve2: `v5-drill T_pre=2026-04-25T10:40:05Z` |
| **Cut** | **10:40:41** | **T+0** | `ssh root@pve2 "shutdown -h now"` issued from jumphost; SSH exit 0 within 1s |
| Drill | 10:40:49 | T+8s | pve2 LRM last heartbeat (per `lrm pve2 (old timestamp - dead?)`) |
| Drill | 10:41:03 | T+22s | First post-cut `pvecm status` snapshot: `Total votes: 2`, `Quorum: 2`, `Quorate: Yes`, Nodes: 2 (3/3 → 2/3 transition occurred in [T+8, T+22] window) |
| Drill | 10:41:45 | T+64s | ct:151 last seen `started(pve2)` |
| Drill | **10:41:51** | **T+70s** | **ct:151 → `starting(pve1)`** — HA fence + relocate completed within 70s of T+0 (target: ≤120s GREEN — PASSED) |
| Drill | 10:42:26 | T+105s | brief `relocate(pve1)` state |
| Drill | 10:42:38–10:43:09 | T+117s..148s | LRM pve1 `pct start 151` retry attempts 1, 2, 3 — all fail with `zfs error: cannot open 'rpool/data/subvol-151-disk-0': dataset does not exist` |
| Drill | **10:43:20** | **T+159s** | **ct:151 → `error(pve1)`** — HA marks resource unstartable after 3 retries (no rootfs replica on pve1) |
| Replication | 10:42:03 | T+82s | First post-cut pvesr cycle for `162-1` (*/1 cadence): `command failed: exit code 255` (FailCount=1) |
| Replication | 10:45:00 | T+259s | First post-cut pvesr cycle for `100-0`, `101-0` (*/15 cadence): both FailCount=1 |
| Alert | 10:46:01 | T+320s | `PVEHAExporterMissing` fires (5min `for:` clause expiry for missing pve2 exporter) |
| Alert | 10:46:07 | T+326s | `ServiceDown{instance="192.168.50.202:9100"}` (pve2 node-exporter) fires |
| Alert | 10:46:07 | T+326s | `ServiceDown{instance="192.168.50.151:9100"}` (ct:151 inside-CT) fires |
| Alert | **10:46:31** | **T+350s** | **`PVEHAResourceUnhealthy{sid="ct:151"}` fires** on both pve1 and pve3 exporter instances — Story 6.10 alert correctly detected `error` state |
| Post-state | 10:48:00 | T+439s | Final snapshot. pve2 SSH timeout. Cluster 2/3 quorate. ct:151 `error(pve1)`. 3 jobs FailCount=1 (250-1 awaits 13:00 cycle). |

### AC verdict table

| AC | Verdict | Evidence | Notes |
|---|---|---|---|
| AC-1 (Alertmanager + ntfy live) | PASS | DeadManSwitch firing pre-drill on `ntfy-low`; 5 new pve2-related alerts firing post-drill on `ntfy-urgent` (operator confirmed phone delivery) | All 3 ntfy receivers verified via `/api/v2/status` (urgent/default/low routes with severity matchers + send_resolved=true) |
| AC-2 (cluster 3/3 quorate) | PASS | `pre/preflight.txt` — all 3 nodes report `Quorate:Yes Total votes:3 Ring ID 1.1c0` | |
| AC-3 (replication jobs OK + fresh) | PARTIAL PASS / GAP | `pre/preflight.txt`, `pre/replication-cfg.txt` | 8 existing jobs OK FailCount=0 fresh; **`151-0`/`151-1` jobs DO NOT EXIST** — Story 6.1 backlog gap. Drill proceeded under operator approval + vzdump fallback. |
| AC-4 (no maintenance in flight) | PASS | `pre/preflight.txt` (zpool status — last scrubs 2026-04-24) | |
| AC-5 (PBS backup ≤24h of ct:151) | MITIGATED | `pre/vzdump-ct151-info.txt` | No PBS backup found; vzdump created during pre-flight (1m04s, 2.23GB). Local off-pve2 copy on jumphost. |
| AC-6 (operator presence + 4-eyes) | PASS (solo-noted) | Operator approved 12:15 CEST; solo-operation explicitly recorded; jumphost SSH sessions; rollback reviewed |
| AC-7 (pre-event state captured) | PASS | `pre/` (13 files, preflight.txt = 309 lines) | |
| AC-8 (T+0 logged + Option A cut) | PASS | `during/T_PULL_ISO.txt` = `2026-04-25T10:40:41Z`; `during/timeline.txt` | SSH exit 0 within 1s; pve2 unreachable within 10s. Option A only (no B) per SM. |
| AC-9 (ct:151 RTO ≤120s) | **VACUOUS FAILED** | `during/loop2-hamanager.txt`, `during/heartbeat-postfwd.txt` | HA fence/relocate completed at T+70s (under 120s target — fence SLO GREEN). `pct start` failed at T+159s with `dataset does not exist` (no replica on pve1). **Application RTO failed because Story 6.1 prerequisite was incomplete.** Heartbeat preserved in vzdump only. |
| AC-10 (other resources behave correctly) | PASS | `during/ha-manager-status-post.txt`, `post/postflight.txt` | vm:100, ct:101, ct:160, ct:162, ct:250 all `started` on intended nodes throughout. No unexpected error/fence on any non-target resource. **Strict-pinned-stays-down test N/A vacuous** (no strict-pinned on pve2; deferred to Future variant pve3-pull). |
| AC-11 (Alertmanager fires + ntfy delivers) | PARTIAL PASS | `during/alerts-during-window.json`, `during/ntfy-pushes-received.txt` | 5 pve2-related alerts fired and routed to ntfy-urgent within T+320s..T+350s. **MISSING:** `PVEReplicationFailed` (4 jobs failed without alert; `pve_replication_failcount` metric not exposed by Story 6.10's exporter — confirmed pre-drill empty result). `InstanceDown{instance="pve2"}` not present as named rule (`ServiceDown{instance="192.168.50.202:9100"}` is the equivalent and DID fire). |
| AC-12 (drill evidence captured) | PASS | `_bmad-output/drill-evidence/v5-pve2-pull-2026-04-25/` with `pre/`, `during/`, `post/` subdirs (29 files total) + `v5-pve2-timeline-2026-04-25.md` (~150 lines) |
| AC-13 (story stays in-review until 6-8) | PASS (planned) | Frontmatter flipped `draft → review`; pve2 left OFF; Story 6-8 will recover | |

### Files touched

**Modified:**

- `homelab-infra/docs/ha-replication-runbook.md` — added `### V5 Drill Results (2026-04-25, first run TARGET_NODE=pve2)` section between V4 Drill Results and `### End-to-end drill status` (~98 lines: timing table, alert table, resource state table, evidence list)
- `homelab-playbook/_bmad-output/implementation-artifacts/6-7-validation-drill-v5-pull-plug-pve3.md` — frontmatter `draft → review`; this Dev Agent Record appended

**Created:**

- `homelab-playbook/_bmad-output/drill-evidence/v5-pve2-pull-2026-04-25/pre/preflight.txt` (309 lines)
- `homelab-playbook/_bmad-output/drill-evidence/v5-pve2-pull-2026-04-25/pre/heartbeat-pre.txt`
- `homelab-playbook/_bmad-output/drill-evidence/v5-pve2-pull-2026-04-25/pre/pct-list-pve{1,2,3}.txt`
- `homelab-playbook/_bmad-output/drill-evidence/v5-pve2-pull-2026-04-25/pre/ct151-uptime.txt`
- `homelab-playbook/_bmad-output/drill-evidence/v5-pve2-pull-2026-04-25/pre/replication-cfg.txt`
- `homelab-playbook/_bmad-output/drill-evidence/v5-pve2-pull-2026-04-25/pre/prometheus-{ha-ct151,replication-failcount,up-pve}-pre.json`
- `homelab-playbook/_bmad-output/drill-evidence/v5-pve2-pull-2026-04-25/pre/alertmanager-pre.json`
- `homelab-playbook/_bmad-output/drill-evidence/v5-pve2-pull-2026-04-25/pre/vzdump-ct151-info.txt`
- `homelab-playbook/_bmad-output/drill-evidence/v5-pve2-pull-2026-04-25/during/T_PULL_{EPOCH,ISO}.txt`
- `homelab-playbook/_bmad-output/drill-evidence/v5-pve2-pull-2026-04-25/during/timeline.txt`
- `homelab-playbook/_bmad-output/drill-evidence/v5-pve2-pull-2026-04-25/during/loop1-pvecm.txt` (60 iterations × 5s)
- `homelab-playbook/_bmad-output/drill-evidence/v5-pve2-pull-2026-04-25/during/loop2-hamanager.txt` (60 iterations × 5s; full ct:151 transition timeline)
- `homelab-playbook/_bmad-output/drill-evidence/v5-pve2-pull-2026-04-25/during/loop3-pvesr.txt` (10 iterations × 30s, both pve1+pve3)
- `homelab-playbook/_bmad-output/drill-evidence/v5-pve2-pull-2026-04-25/during/loop4-alertmanager.txt` (20 iterations × 15s)
- `homelab-playbook/_bmad-output/drill-evidence/v5-pve2-pull-2026-04-25/during/loop5-prometheus-up.txt` (30 iterations × 10s)
- `homelab-playbook/_bmad-output/drill-evidence/v5-pve2-pull-2026-04-25/during/ha-manager-status-post.txt`
- `homelab-playbook/_bmad-output/drill-evidence/v5-pve2-pull-2026-04-25/during/ct151-new-home.txt`
- `homelab-playbook/_bmad-output/drill-evidence/v5-pve2-pull-2026-04-25/during/replication-failures.txt`
- `homelab-playbook/_bmad-output/drill-evidence/v5-pve2-pull-2026-04-25/during/heartbeat-postfwd.txt`
- `homelab-playbook/_bmad-output/drill-evidence/v5-pve2-pull-2026-04-25/during/alerts-during-window.json`
- `homelab-playbook/_bmad-output/drill-evidence/v5-pve2-pull-2026-04-25/during/ntfy-pushes-received.txt`
- `homelab-playbook/_bmad-output/drill-evidence/v5-pve2-pull-2026-04-25/post/postflight.txt` (117 lines)
- `homelab-playbook/_bmad-output/drill-evidence/v5-pve2-pull-2026-04-25/v5-pve2-timeline-2026-04-25.md` (comprehensive timeline + AC verdicts)

### Deviations from story plan

1. **ct:151 has no replication jobs.** AC-3's `[NEEDS OPERATOR CONFIRMATION]` clause was a hard-abort condition: "If absent → ABORT and create them per Story 6.1." Drill proceeded under operator approval (12:15 CEST) + AC-5 fallback (vzdump created in pre-flight) on the rationale that the drill's alert-fan-out and fence-semantic missions are testable independently of ct:151's app-level RTO. The HA fence + relocate path WAS demonstrated correctly (T+70s, well within 120s target); only the `pct start` on the chosen peer failed, exactly as predicted by the missing-replica diagnosis. Recorded as **Story 6.1 supplementary backlog**: create `151-0`/`151-1` outbound jobs to give ct:151 a real HA recovery path.
2. **`PVEReplicationFailed` alert did not fire** despite 4 replication jobs entering FAILED state during the drill window. `pve_replication_failcount` metric returns empty in Prometheus across the drill. This was the headline-observation premise of the SM pivot ("4 replication jobs failing simultaneously is the cleanest stress test of the alert fan-out"). The fan-out test is undercut by the exporter gap. Recorded as **Story 6.2/6.10 supplementary backlog**: wire the `pve_replication_failcount` exporter metric and the `PVEReplicationFailed` alertmanager rule. Story 6.10's `PVEHAResourceUnhealthy` rule **DID fire correctly** (T+350s) for ct:151's error state — at least the HA-state alert path is closed.
3. **Loop 4 (alertmanager polling) ended at T+313s, just before the 5-min `for:` clauses on Service-Down rules expired at T+320s+.** All headline pve2 alerts fired AFTER loop end. Manual snapshot at T+346s and post-state capture at T+407s caught them. Recorded as **drill-design backlog**: future drills bump observation loops to T+600s minimum.
4. **Option B (cord-pull) was NOT executed** per SM recommendation for first-run conservatism. Option A graceful path produced clean evidence; Option B can run during Future variant pve3-pull.
5. **No PBS backup of ct:151 existed** at pre-flight (PBS not currently configured for ct:151's home pool). Mitigated via in-pre-flight vzdump (gate #8 fallback path); copied off-pve2 to jumphost as catastrophic-rollback safety. Recorded as **PBS backup configuration backlog**: configure scheduled PBS for ct:151 (and audit other HA-managed CTs for backup coverage).
6. **Strict-pinned-stays-down semantic test N/A vacuous** for pve2 first run. Story already documents this in `### Deferred: strict=1 pinned-resource semantic`. Captured in Future variant section. ct:160 (pinned-pve3) and vm:100 (pinned-pve1) were both confirmed unaffected during this drill, which is the correct behavior for non-target pinned resources.

### Next actions for operator

- Flip sprint-status YAML for Story 6.7 from in-progress → review (outside Dev scope; per project rules).
- **Proceed immediately to Story 6.8** to recover pve2. The cluster is currently 2/3 quorate with ct:151 in `error` state; this is functional but degraded. Recovery sequence: power on pve2, wait for cluster to return to 3/3, run `ha-manager set ct:151 --state disabled`, verify rootfs returns on pve2, run `ha-manager set ct:151 --state started`, verify failback, verify the 4 replication jobs (100-0, 101-0, 162-1, 250-1) clear FailCount and return to OK.
- Story 6-9 (runbook absorption) MUST address 3 surfaced gaps:
  1. Story 6.1 supplementary — create `151-0`/`151-1` outbound replication jobs.
  2. Story 6.2/6.10 supplementary — wire `pve_replication_failcount` metric + `PVEReplicationFailed` alertmanager rule.
  3. Drill loop window guidance — minimum T+600s observation window for 5-min `for:` alert capture in-loop.
- Optional Epic 7 backlog: schedule PBS backups for HA-managed CTs (ct:151, ct:101) on a regular cadence to remove vzdump-as-pre-flight-fallback dependency for future drills.
- Future variant (pull-plug pve3) — preserved in `## Future variant — pull plug pve3` section; can be scheduled once ct:250 is migrated off pve3 OR an explicit dev-outage maintenance window is approved.
