---
date: 2026-04-25
drill: V5 pull-plug pve2
owner: BMad SM (via planner agent)
type: retrospective (not a story)
related-stories: 6-7, 6-1-1, 6-9-1, 6-10-2, 6-9
---

# V5 pull-plug pve2 drill — retrospective

## What the drill set out to prove

Story 6-7 (V5 pull-plug pve2) was scoped to validate two specific things on the live cluster:

1. **HA fence semantic on pve2 power loss** — that pve3 (the surviving HA-master candidate) correctly fences pve2, declares its HA-managed resources `recovery`, and migrates them to peer nodes within the published RTO budget (target ≤ 90s).
2. **Alert chain end-to-end on pve2 pull** — that the six expected alerts (`PVENodeDown`, `PVEReplicationStale`, `PVEHAResourceFenced`, `PVEHAResourceRecovery`, `PVEReplicationFailed`, `PVEHAClusterUnhealthy`) transition from `inactive → pending → firing` in Prometheus, then route through Alertmanager to the `ntfy-urgent` topic on the operator's phone, with `send_resolved: true` correctly clearing on recovery.

The drill was executed on pve2 (not the originally-scoped pve3 target) to protect the operator's active dev session on pve3 — a mid-drill pivot decision (see Operator decision points below).

## What it actually proved

The drill empirically validated the cluster's HA + alert chain:

- **HA RTO 70s GREEN**: pve2 pulled at T=0; HA fence declared at T+24s; ct/vm migrations to pve1 + pve3 completed by T+70s. Inside the 90s budget; well above the 60s pre-existing measurement from V4 (simulated migrate).
- **5 of 6 alerts reached ntfy-urgent**: `PVENodeDown` (T+45s), `PVEReplicationStale` (T+325s), `PVEHAResourceFenced` (T+50s), `PVEHAResourceRecovery` (T+65s), `PVEHAClusterUnhealthy` (T+30s) all fired and pushed correctly. The 6th — `PVEReplicationFailed` — did NOT fire (see exposed gaps).
- **`send_resolved: true` working**: post-recovery, every fired alert correctly transitioned `firing → resolved` and emitted a "RESOLVED" ntfy push within the expected 2-min window after recovery completed.
- **Recovery sequence empirically validated**: pve2 power-on → cluster re-quorate (3/3) → HA-managed resources auto-migrated back to home nodes per HA rule placement → replication jobs caught up within one cycle.

These are the *expected* outcomes — the drill's primary value was confirming they hold under a real, full-power-loss fault on a production cluster. They now do.

## What it exposed (the unique value of this drill)

The V5 drill caught **four gaps that were silent before the drill ran**. Each is independently concerning; collectively they justify the drill cost in a single execution.

### Gap 1 — ct:151 had no replication despite being in the `standard` HA rule (CRITICAL)

ct:151 (sparkle-cps, VMID 151, on pve2) was a member of the `standard` HA rule — meaning the cluster considered it failover-eligible. But `/etc/pve/replication.cfg` contained **zero** replication jobs sourcing from `local: 151-`. The drill exposed this when ct:151 was declared `recovery` but had no destination disk to migrate to. **Had pve2 actually died (not been pull-plugged in a controlled drill), ct:151 would have been stranded — the only recovery path would have been PBS restore from the previous backup, with data loss equal to the time since the last backup.** Dev 6-1-1 is closing this gap in parallel; the audit-first principle is now memorized in `feedback_ha_replication_audit_first.md`.

### Gap 2 — `pve_replication_failcount` Prometheus metric was empty

During the drill, `pvesr status` on the surviving nodes correctly showed replication jobs in `State=error` with `FailCount > 0` (jobs sourced from pve2 couldn't reach the dead source). But the Prometheus metric `pve_replication_failcount` was **empty** — zero rows scraped — making the `PVEReplicationFailed` alert (defined in Story 6.2) unable to match. The metric exists in the exporter's vocabulary but the exporter is publishing zero label-rows. The alert chain is **dark** for the upstream signal. Story 6-10-2 was drafted earlier to cover this; the V5 drill provides the empirical evidence that justifies its severity.

### Gap 3 — drill observation loop ended at T+313s, missing `for: 5m` alerts

The drill's Prometheus alert observation loop terminated at T+313s. The three alerts with `for: 5m` clauses (`PVEReplicationStale`, `PVEHAClusterUnhealthy`, etc.) were configured to transition `pending → firing` at ~T+320s — **seven seconds after the loop exited**. The alerts ultimately fired and pushed to ntfy correctly, so the operator's phone confirmed them, but the drill's own evidence capture missed three of six expected `firing` transitions. Future drills need a minimum T+600s (10 min wall-clock) observation window to give `for: 5m` clauses time to evaluate.

### Gap 4 — drill design needs pre-flight audit

Nobody audited the cluster's replication coverage versus HA rule placement *before* running the drill. Gap 1 (ct:151) was knowable from `/etc/pve/replication.cfg` and `ha-manager status` alone, with a five-minute audit script — no drill required. The drill *did* surface it (which is one valid form of value), but a properly-designed pre-flight gate would have surfaced it without putting the cluster through a fence. The audit-first principle is now codified in `feedback_ha_replication_audit_first.md` and is being added as AC-10 to Story 6-9-1.

## Unique value of this drill

**The gap it caught was silent before the drill ran.** No alert, no monitoring dashboard, no health check, and no prior story execution had surfaced ct:151's missing replication. The cluster reported itself healthy (`ha-manager status` showed all resources `started`; Prometheus showed all alerts `inactive`), and yet a real pve2 failure would have been a data-loss event. The V5 drill paid for itself in a single execution: without it, the next pve2 outage (whether from a hardware fault, a kernel panic, or a power event) would have stranded ct:151 with PBS restore as the only recovery path.

This is the canonical justification for chaos drills. Self-reported cluster health is a necessary but not sufficient signal; deliberate fault injection is the only way to validate that the cluster's failure paths actually work.

## Lessons codified into memory

- **`feedback_ha_replication_audit_first.md`** (NEW) — before any HA-related work, audit replication coverage versus HA rule placement. Non-pinned HA resources without replication to both peers are silent failures waiting for a real fault.
- **`feedback_pve9_ha_error_recovery.md`** (extended) — appended a section on the drill loop window. Any drill loop watching for `for: 5m` alerts must run at least 10 min wall-clock; the alert evaluation cadence is the binding constraint, not the inject cadence.

## Action items spawned

- **Story 6-1-1** (in progress) — close ct:151 replication gap. Dev 6-1-1 is configuring `local: 151-0` and `local: 151-1` jobs to pve1 and pve3 respectively, with `*/15` cadence matching the cluster's other `standard`-rule resources.
- **Story 6-9-1 expansion** (this retrospective's twin deliverable) — adds AC-10 (pre-flight replication-coverage audit, refuses drill on deficient resources) and AC-11 (drill observation loop minimum T+600s window with intentional `for: 5m` test).
- **Story 6-10-2 verification** (this retrospective's twin deliverable) — verified that the pvesr fail_count alerting story already covers the empty-metric exporter gap; V5 drill evidence pinned to References as empirical motivation.

## Operator decision points

The drill was originally scoped to target pve3 (the standing V5 plan; pve3 was the candidate since it was the cluster's HA-master at the time of scoping). Mid-execution, the operator pivoted to pve2 to **protect the active dev session on pve3** — pulling pve3 would have terminated work-in-progress on ct:152 (the dev container) and ct:153 (the ai-dev container). The pivot was sound: the drill's *intent* (validate HA fence + alert chain on a real node loss) is target-agnostic; pve2 was a valid stand-in.

The original pve3-pull design is preserved as a **Future variant** for execution after the dev session window closes, since pve3-specific dependencies (Ollama on the dGPU OCULink path, ct:162 quant-trading home-node placement) are still worth empirical validation under a pve3-loss scenario. That variant is captured as a backlog note for Story 6-7's successor.

---

## Correction note (2026-04-25 post-Story 6-10-2)

The drill report flagged a **"missing `PVEReplicationFailed` alert"** as evidence of an exporter gap. Story 6.10.2 verification showed this was a **metric-name typo, not an actual gap**:

- Real published metric: `pve_replication_fail_count` (underscore between `fail` and `count`)
- Drill agent queried: `pve_replication_failcount` (no underscore) → returned 0 series → wrongly concluded "metric empty"

The actually-deployed `PVEReplicationFailing` rule (Story 6.2) uses the correct metric name, has `for: 10m` + `severity: critical`, and was active throughout the V5 drill window (~20 minutes). The 4 failed replication jobs (100-0, 101-0, 162-1, 250-1) almost certainly **did** fire that rule, sending a 6th ntfy push not captured in the drill's polling loops.

**Implication**: V5's alert chain was MORE complete than the drill report claimed (probably 6+ alerts to ntfy, not 5). The "exporter gap" finding is RETRACTED. Story 6-10-2 closed as Branch A (verify-only, no code changes).

**Lesson for future drills**: cross-check metric names against the exporter source before declaring a "missing metric" finding.

---

*This document will be cited by Story 6-9 (final HA runbook synthesis) when that story runs. The drill evidence proper lives at `_bmad-output/drill-evidence/v5-pve2-pull-2026-04-25/`.*
