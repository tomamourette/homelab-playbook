---
status: done
epic: 6
story: 6.6
title: Validation drill V4 — simulated failover via ha-manager migrate
created: 2026-04-24
author: BMad SM (via planner agent)
---

# Story 6.6: Validation drill V4 — simulated failover via ha-manager migrate

Status: done

> **PVE 9.1+ note:** uses HA rules (node-affinity), not legacy HA groups — see Story 6.3 sprint-change note and `/home/developer/.claude/projects/-home-developer-workspace-homelab/memory/project_pve9_ha_rules_migration.md`. The `migrate` subcommand has moved to `ha-manager crm-command migrate <sid> <node>` (verified live on this cluster 2026-04-25 via `ha-manager help migrate`). The legacy form `ha-manager migrate <sid> <node>` may still work via a compatibility shim; the canonical form is the `crm-command` namespace. `nofailback` is now per-resource `failback` (inverted boolean). Terminology updated below where it appears.

## Story

As an operator,
I want to exercise an end-to-end HA-managed failover of CT162 from pve3 to pve2 (and back) via `ha-manager migrate`, measuring total outage time, snapshot-lineage reversal, and the notification path,
so that before Story 6.7's destructive pull-plug drill, I have observed proof that the CRM watchdog, replication state machine, and ntfy push channel all participate correctly in a graceful failover — eliminating the "did the mechanism work, or did luck spare us" ambiguity that would otherwise contaminate any interpretation of 6.7.

## Business value

Story 6.5 (V3 drill) proves replication meets 1-min RPO. But 1-min RPO is only useful if failover actually exercises it. 6.6 is the **graceful rehearsal** of the mechanism that 6.7 will then test under adversarial conditions (real node death). It converts three unmeasured assumptions into documented facts:

1. **HA-manager migration actually moves a CT** and the CRM picks up the directive in finite time — `ha-manager migrate 162 pve2` is the documented API call (NOT `pct migrate`, which bypasses HA and would invalidate the drill). This story sees the CRM's behaviour end-to-end.
2. **Total outage time is bounded** (target: ≤60 s CT-down-to-CT-up). This is the concrete number that feeds into Epic 6's "HA with ≤1-min RPO" promise — RPO alone is insufficient; RTO also needs a measured ceiling.
3. **Replication direction flips automatically** after migration. `pvesr status` post-migrate should show CT162 now owned by pve2 (new home), replicating back toward pve3 and forward to pve1. A failure here means the replicated peer cannot retake the primary role without manual intervention — a silent HA-is-one-way failure mode that 6.7 would then crash into.
4. **The ntfy push channel fires on HA state changes** (Story 7.11 integration). If it doesn't fire for a graceful migration, the operator learns a real node-death event would also go unnoticed — and that gap gets fixed before 6.7, not during.

6.6 is workload-impacting (CT162 is briefly offline). It is run during a **low-traffic window**, or "accepted as a drill" — CT162 is quant-trading; weekend/after-hours is the natural slot. The in-CT heartbeat file is how the drill measures application-side continuity vs. host-side migration completion.

Without 6.6, Story 6.7 inherits two unmeasured assumptions (HA migrate works; replication flips) while simultaneously running under the pressure of a simulated node loss. With 6.6, 6.7 can isolate "did HA detect node-down fast enough?" — the one adversarial question 6.7 is actually for.

## Acceptance Criteria

### AC-1: Pre-flight baseline captured with no active failures

**Given** the cluster is 3/3 quorate (`pvecm status`) and Story 6.5 has completed with CT162 at its finalised schedule (either `*/1` or the documented fallback)
**And** CT162 is HA-tagged per Story 6.3 (rewritten — supersedes original 6.4) (`ha-manager config | awk '/^ct: 162/,/^$/'` shows `state: started`; `ha-manager rules config --resource ct:162` shows membership in the `critical` node-affinity rule — **NEEDS OPERATOR CONFIRMATION** that rewritten 6.3 is done before 6.6 starts; if 6.3 is not done, 6.6 blocks)
**When** I capture pre-state snapshots
**Then** the following artifacts exist in `_bmad-output/drill-evidence/v4-ct162-failover-<date>-pre/`:
- `ha-manager-status.txt` — full output of `ha-manager status --verbose`, confirming CT162 state = `started` on `pve3`
- `pvesr-status-pve3.txt` — `162-0`, `162-1` both `OK`, fresh `LastSync`
- `ct162-uptime.txt` — `pct exec 162 -- uptime` output and `pct exec 162 -- date +%s` epoch
- `heartbeat-pre.txt` — contents of `/root/v4-heartbeat.txt` written inside CT162 with a known timestamp (Task 1 creates this)
- `alertmanager-alerts-pre.json` — `curl https://alertmanager.bi-services.be/api/v2/alerts` output, should be empty for `PVEReplication*` and any `PVECluster*`
**And** the Grafana HA Replication dashboard is all-green (optional screenshot → `dashboard-pre.png`)

### AC-2: `ha-manager migrate` moves CT162 from pve3 to pve2 within the CRM timing window

**Given** AC-1 holds
**When** I issue `ha-manager crm-command migrate ct:162 pve2` from any cluster node (PVE 9.1+ canonical form; `<sid>` = `ct:162`)
**Then** the following sequence is observed in `ha-manager status --verbose` output over the next 60 s, with each state captured to an evidence timeline:
1. CRM receives the directive: `ct:162 (pve3, requested_state=migrate, target=pve2)`
2. CT162 stops on pve3: `ct:162 (pve3, stopped)`
3. CT162 starts on pve2: `ct:162 (pve2, started)`
**And** wall-clock elapsed from `ha-manager crm-command migrate` command issue to `pct status 162` returning `status: running` on pve2 is **≤ 60 s** (green), with 60–180 s tracked as yellow and > 180 s as red (see Dev Notes §"Timing expectations")
**And** `pct list` on pve2 shows VMID 162 in state `running`; on pve3 it is absent

### AC-3: In-CT heartbeat + outage measurement quantifies RTO from the application's perspective

**Given** the pre-state heartbeat file (`/root/v4-heartbeat.txt`) contains a known epoch written at T_pre
**When** CT162 has come back up on pve2 (AC-2 complete) and I re-read the heartbeat file
**Then** `pct exec 162 -- cat /root/v4-heartbeat.txt` on pve2 returns the same content written at T_pre (proves filesystem continuity — replication delivered the file, not lost during stop/start)
**And** `pct exec 162 -- uptime` shows the CT's own `up` counter restarted at ≤ T_migrate + outage_seconds (proves the container actually stopped + started, not hibernated)
**And** the computed `outage_seconds = T_ct_up_on_pve2 - T_ct_stop_on_pve3` is recorded and categorised:
- ≤ 60 s: green (matches RTO target)
- 61–180 s: yellow (acceptable for a drill; document the slow step — CRM poll jitter, container fsck, networking race, etc.)
- > 180 s: red; **root-cause before closing this story** — do not mark 6.6 as done with an unexplained > 3-min outage

### AC-4: Replication state machine flips direction post-migration

**Given** AC-2 is complete and CT162 has been on pve2 for at least 2 minutes (one full `*/1` or `*/15` cycle on the new home)
**When** I run `pvesr status` on **pve2** (the new home) and on **pve3** (the old home)
**Then** on pve2: two new replication jobs exist with CT162 as source: one targeting pve1 (the other surviving critical target), one targeting pve3 (the now-old home). They show `State = OK` and `LastSync` within one cycle.
**Or** (acceptable alternative Proxmox behaviour): the original `162-0` and `162-1` jobs have been rewritten by the HA manager with their source changed from pve3 to pve2, targets updated, and `State = OK` within two cycles.
**And** on pve3: either the original `162-0`/`162-1` job entries are gone, OR they show as foreign / owned by pve2
**And** target-side snapshots on the new targets (pve1 and pve3) have a `__replicate_*` marker with an epoch ≥ T_ha_migrate_complete — proves the post-migrate replication cycles are actually running, not a stale view of pre-migrate data
**And** **NEEDS OPERATOR CONFIRMATION** — Proxmox's exact post-migrate replication.cfg behaviour ("rewrite in place" vs. "create new source-pve2 jobs and deprecate old") is version-specific; the drill records whichever of the two is observed and documents it in the runbook for 6.7's benefit

### AC-5: ntfy push channel fires for the migration event (Story 7.11 integration)

**Given** Alertmanager is running on ct-docker-01 and the ntfy topics are subscribed on the operator's Android phone (per `ha-replication-runbook.md §"Subscribing the Android phone to push alerts"`)
**When** AC-2's migration sequence executes
**Then** one of two documented outcomes occurs:
- **Outcome A (alert fires):** a `PVEClusterHAMigration` (or equivalent HA-state-change) alert fires, routes via Alertmanager, and delivers a ntfy push to the operator's phone within **≤ 90 s** of `ha-manager migrate` being issued. Evidence: screenshot or notification log from the ntfy app; also `curl https://alertmanager.bi-services.be/api/v2/alerts` captures the alert while active.
- **Outcome B (no such alert exists):** the Prometheus rules set does NOT include an `HAMigration`-type alert. No push fires. This is a **gap finding**, recorded verbatim in the drill output; a follow-up story / backlog note is opened under Epic 7 to add one (e.g. `PVEClusterCTMigrated` rule on `changes(pve_ha_ct_node_id[5m]) > 0` or similar, built atop a new exporter metric).
**And** whichever outcome is observed is recorded in the V4 Drill Results section of the runbook
**And** if Outcome B: the drill does NOT fail 6.6 on that basis — notification gap is a known Epic 7 scope boundary. It does flag the gap explicitly so 6.7's interpretation is calibrated.

### AC-6: CT162 returned to home node and state re-verified

**Given** AC-2 through AC-5 are complete
**When** I issue `ha-manager crm-command migrate ct:162 pve3` (return to home) — **NEEDS OPERATOR CONFIRMATION** on whether per-resource `failback=1` on ct:162 (PVE 9.1+ replacement for legacy group-level `nofailback=0`) will auto-return CT162 without an explicit migrate command; the rewritten 6.3 sets `failback=1` per resource, but the observed behaviour may be "do nothing until next scheduler tick"
**Then** within 60 s, CT162 is back on pve3 with `ha-manager status` showing `ct:162 (pve3, started)`
**And** `pvesr status` on pve3 shows `162-*` jobs (or their recreated/flipped equivalents) back to source=pve3, target=pve1/pve2
**And** the heartbeat file is still present and intact (`pct exec 162 -- cat /root/v4-heartbeat.txt`)
**And** the Grafana HA Replication dashboard returns to all-green
**And** Alertmanager shows no firing `PVEReplication*` / `PVECluster*` alerts (confirm at Task 9 — if any are firing, root-cause before closing)

### AC-7: V4 Drill Results section added to runbook with measured numbers and gap findings

**Given** AC-1 through AC-6 are complete
**When** I append a `## V4 Drill Results (<date>)` section to `homelab-infra/docs/ha-replication-runbook.md` **above** the existing "End-to-end drill status" subsection (sibling to V3 Drill Results from Story 6.5)
**Then** the section contains:
- **Timing table**: `T_migrate_issued`, `T_ct_stopped_on_pve3`, `T_ct_started_on_pve2`, `T_ct_back_on_pve3`; computed outage_seconds and round-trip_seconds
- **Replication flip observation**: which of the two AC-4 alternatives was observed (rewrite-in-place vs. new-source-jobs); full `pvesr status` transcript before + after
- **Notification outcome**: Outcome A (alert fired, latency recorded) OR Outcome B (no such alert exists, follow-up backlog reference)
- **Planned outage window**: actual window duration (wall-clock from drill start to drill end) vs. the planned ≤5-min window
- **Evidence paths**: `_bmad-output/drill-evidence/v4-ct162-failover-<date>-{pre,during,post}/`
- **Decision gate for Story 6.7**: if AC-2 (≤60 s) passed green, 6.7 can start; if yellow, run one retry pass to confirm repeatability; if red, block 6.7 until root cause documented

### AC-8: Story 6.10 alert chain validated end-to-end during drill

**Given** Story 6.10 is `done` and `pve_ha_resource_state` is being scraped by Prometheus
**When** the drill triggers a state change in ct:162 (running→stopped→migrating→started, or per the drill's intent)
**Then** Prometheus captures the transition (`changes(pve_ha_resource_state{sid="ct:162"}[5m]) > 0`)
**And** any abnormal state (error/fence/recovery >2m) fires `PVEHAResourceUnhealthy` within ≤60s
**And** the operator's phone receives an `Urgent`-priority ntfy push within ≤60s of the alert firing
**And** drill evidence captures both: the Prometheus query result AND the ntfy push payload (or a screenshot equivalent)

## Tasks

- [ ] **Task 0: Pre-flight sanity** (AC-1 prerequisites; blocks the drill if any fail)
  - [ ] `ssh pve1 "pvecm status"` — confirm `Quorate: Yes`, `Total votes: 3`; abort if not 3/3
  - [ ] Confirm Story 6.3 (rewritten — supersedes original 6.4) is complete: `ssh pve1 "ha-manager config | grep '^ct: 162'"` shows the resource registered with state `started`; `ssh pve1 "ha-manager rules config --resource ct:162"` shows membership in the `critical` node-affinity rule — **NEEDS OPERATOR CONFIRMATION** if either is missing (rewritten 6.3 expected ahead of 6.6)
  - [ ] `ssh pve3 "pvesr status"` — confirm `162-*` jobs `OK`, fresh `LastSync`
  - [ ] Grafana HA Replication dashboard all-green — optional screenshot → `dashboard-pre.png`
  - [ ] Alertmanager: zero active `PVEReplication*` / `PVECluster*` alerts — no hidden failure baseline
  - [ ] `ntfy` app on operator phone: subscribed + smoke-tested within the last 7 days (re-run `homelab-infra/tests/e2e-alertmanager-ntfy.sh` if unsure)
  - [ ] **Planned outage window announced**: the drill window is ≤ 5 minutes total wall-clock (CT162 will be actively offline for ~1–2 minutes of that; the rest is observation + migrate-back). Run outside market hours / during weekends or document "drill-acceptable window" in the log.
  - [ ] `mkdir -p _bmad-output/drill-evidence/v4-ct162-failover-<date>-pre` + `during` + `post` subdirs

- [ ] **Task 1: Pre-state capture + heartbeat write** (AC-1)
  - [ ] `ha-manager status --verbose > _bmad-output/drill-evidence/v4-ct162-failover-<date>-pre/ha-manager-status.txt`
  - [ ] `ssh pve3 "pvesr status" > _bmad-output/drill-evidence/.../pvesr-status-pve3.txt`
  - [ ] `ssh pve3 "pct exec 162 -- uptime" > _bmad-output/drill-evidence/.../ct162-uptime.txt`
  - [ ] Write heartbeat inside CT162: `ssh pve3 "pct exec 162 -- sh -c 'echo \"v4-drill T_pre=$(date -u +%Y-%m-%dT%H:%M:%SZ) epoch=$(date +%s)\" > /root/v4-heartbeat.txt'"`
  - [ ] Snapshot the heartbeat content into evidence: `pct exec 162 -- cat /root/v4-heartbeat.txt` → `heartbeat-pre.txt`
  - [ ] Alertmanager baseline: `curl -s https://alertmanager.bi-services.be/api/v2/alerts | jq '[.[] | select(.labels.alertname | test("PVE"))]' > alertmanager-alerts-pre.json`

- [ ] **Task 2: Issue HA-managed migration** (AC-2)
  - [ ] Record wall-clock: `T_migrate_issued=$(date -u +%Y-%m-%dT%H:%M:%SZ)` + epoch form
  - [ ] `ssh pve1 "ha-manager crm-command migrate ct:162 pve2"` (PVE 9.1+ canonical form; or from any node; pve1 is a convenient neutral party — NOT pve3 in case of a network partition mid-drill)
  - [ ] Immediately begin polling `ha-manager status` every 2 s for 120 s; tee each sample with timestamp into `_bmad-output/drill-evidence/.../during/ha-manager-timeline.txt`
  - [ ] Capture the first timestamp where `ct:162` appears as `(pve2, started)` → `T_ct_started_on_pve2`
  - [ ] Verify on pve2: `ssh pve2 "pct status 162"` → `status: running`
  - [ ] Compute outage_seconds = T_ct_started_on_pve2 - T_ct_stopped_on_pve3 (both from the polling timeline)

- [ ] **Task 3: Verify CT162 is live on pve2 and heartbeat intact** (AC-3)
  - [ ] `ssh pve2 "pct exec 162 -- uptime"` — record uptime (should be a few seconds, proving a real restart)
  - [ ] `ssh pve2 "pct exec 162 -- cat /root/v4-heartbeat.txt"` — must match the pre-drill content exactly
  - [ ] `ssh pve2 "pct exec 162 -- ip addr show eth0"` — confirm IP `192.168.50.162` is up (LXC network retained)
  - [ ] Smoke test one application-level endpoint if CT162 exposes one (e.g. SSH to `192.168.50.162` succeeds with the usual key); skip if no service is exposed at rest
  - [ ] Categorise outage_seconds against the green/yellow/red scale (Dev Notes §"Timing expectations"); record the verdict inline in the timeline file

- [ ] **Task 4: Wait for replication to settle on the new home + verify direction flip** (AC-4)
  - [ ] Wait 2 minutes (one full `*/1` cycle × 2 for safety; if CT162 stayed at `*/15`, wait 3 minutes)
  - [ ] `ssh pve2 "pvesr status"` — capture the new source-side job state
  - [ ] `ssh pve3 "pvesr status"` — capture the old home's view
  - [ ] `ssh pve1 "zfs list -t snapshot -r rpool/data/subvol-162-disk-0 | tail -5"` — confirm a fresh `__replicate_*` snapshot exists post-migrate
  - [ ] Same on pve3 for the new target leg
  - [ ] Document whichever AC-4 alternative was observed (rewrite-in-place vs. new-source-jobs) in a dedicated evidence file `replication-flip-<date>.txt`

- [ ] **Task 5: Notification check** (AC-5, Story 7.11 integration)
  - [ ] Check phone ntfy app for any alert that fired between T_migrate_issued and T_migrate_issued + 120 s
  - [ ] `curl -s https://alertmanager.bi-services.be/api/v2/alerts` during the migration window + 90 s; save to `alertmanager-alerts-during.json`
  - [ ] `curl -s https://prometheus.bi-services.be/api/v1/query?query=ALERTS` — look for any `PVECluster*` or HA-related alert
  - [ ] Record Outcome A (alert fired, with name + latency) or Outcome B (no such alert exists) in `notification-outcome-<date>.txt`
  - [ ] If Outcome B: open a backlog note in the runbook's "Known gaps deferred to Epic 7" section — "No HA-migration alert rule exists; operator must notice the Grafana panel or subscribe to `ha-manager` syslog entries out of band"

- [ ] **Task 6: Migrate CT162 back to pve3** (AC-6)
  - [ ] `ha-manager crm-command migrate ct:162 pve3` from pve1
  - [ ] Poll `ha-manager status` every 2 s for 90 s; record `T_ct_back_on_pve3`
  - [ ] Verify on pve3: `pct status 162` → running; `pct exec 162 -- cat /root/v4-heartbeat.txt` → unchanged content
  - [ ] `ssh pve3 "pvesr status"` — confirm `162-*` jobs back to source=pve3 (or new equivalents, per AC-4 observation)
  - [ ] **NEEDS OPERATOR CONFIRMATION** — if per-resource `failback=1` (PVE 9.1+ replacement for legacy group-level `nofailback=0`) + Proxmox behaviour meant CT162 returned automatically without the explicit migrate command, document that instead (no manual migrate needed); the `ha-manager crm-command migrate` command becomes confirmatory

- [ ] **Task 7: Post-state capture + dashboard verification** (AC-6)
  - [ ] Repeat Task 1's evidence capture into the `/post/` subdir: `ha-manager-status.txt`, `pvesr-status-pve3.txt`, `ct162-uptime.txt`, `heartbeat-post.txt`, `alertmanager-alerts-post.json`
  - [ ] Grafana HA Replication dashboard all-green → `dashboard-post.png`
  - [ ] `curl -s https://alertmanager.bi-services.be/api/v2/alerts | jq '[.[] | select(.labels.alertname | test("PVE"))]'` → expected: same shape as pre (empty or non-firing)

- [ ] **Task 8: Replication catch-up check + snapshot sanity** (AC-6)
  - [ ] If replication is stale (`seconds_since_last_sync` > schedule on the dashboard): `ssh pve3 "pvesr run --id 162-0 --verbose"` and same for `162-1` to force a catch-up
  - [ ] Confirm both legs `OK` after catch-up
  - [ ] Target snapshot sanity: `ssh pve1 "zfs list -t snapshot -r rpool/data/subvol-162-disk-0 | tail -3"` and same on pve2 — confirm freshest `__replicate_*` epochs are both post-T_ct_back_on_pve3

- [ ] **Task 9: Write V4 Drill Results section** (AC-7)
  - [ ] Append `## V4 Drill Results (<date>)` to `homelab-infra/docs/ha-replication-runbook.md` (sibling of the V3 section from Story 6.5)
  - [ ] Include the timing table (migrate → stop → start → back), replication flip observation, notification outcome, planned-vs-actual window duration, evidence paths, decision gate for Story 6.7
  - [ ] Cross-reference this story file from the runbook

- [ ] **Task 10: Commit runbook updates + status-YAML flip**
  - [ ] Commit `homelab-infra/docs/ha-replication-runbook.md` (V4 drill section + any "Known gaps" update for notification outcome) as one logical unit (`feat(drill): V4 simulated failover via ha-manager migrate`)
  - [ ] Commit `_bmad-output/drill-evidence/v4-ct162-failover-<date>-{pre,during,post}/*` as evidence companion (`docs(drill-evidence): V4 failover measurements`)
  - [ ] Flip status YAML in this story file from `draft` → `review`
  - [ ] **NEEDS OPERATOR CONFIRMATION** — sprint-status YAML flip for Story 6.6 is outside SM scope per project rules; Dev to flip via the sprint-status skill

## Dev Notes

### Measurement commands

**Issuing the migration** (AC-2, Task 2). Note the `ct:` prefix — `ha-manager` takes SIDs (`<type>:<id>`), not bare VMIDs. PVE 9.1+: `migrate` lives under `crm-command` (verified live 2026-04-25 via `ha-manager help migrate`):

```bash
T_MIGRATE_EPOCH=$(date +%s)
T_MIGRATE_ISO=$(date -u +%Y-%m-%dT%H:%M:%SZ)
echo "T_migrate_issued: $T_MIGRATE_ISO ($T_MIGRATE_EPOCH)" \
  | tee -a _bmad-output/drill-evidence/v4-ct162-failover-$(date +%F)/during/timeline.txt
ssh pve1 "ha-manager crm-command migrate ct:162 pve2"
```

**Polling `ha-manager status` with timestamps** (AC-2, Task 2):

```bash
EVIDENCE=_bmad-output/drill-evidence/v4-ct162-failover-$(date +%F)/during
for i in $(seq 1 60); do
  echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) (epoch=$(date +%s)) ===" >> $EVIDENCE/ha-manager-timeline.txt
  ssh pve1 "ha-manager status --verbose" >> $EVIDENCE/ha-manager-timeline.txt
  sleep 2
done
```

**Parsing the timeline for key epochs** (AC-3):

```bash
grep -B1 "ct:162" ha-manager-timeline.txt | awk '
  /^=== / { ts=$2 }
  /ct:162.*stopped/ && !stop_ts { stop_ts=ts; print "T_stop_on_pve3:", stop_ts }
  /ct:162.*pve2.*started/ && !start_ts { start_ts=ts; print "T_started_on_pve2:", start_ts }'
```

**Replication direction check** (AC-4, Task 4):

```bash
# Pre-migrate: pve3 sources 162-*
# Post-migrate: pve2 should source them (or equivalent)
ssh pve2 "pvesh get /nodes/pve2/replication --output-format json | jq '.[] | select(.id | startswith(\"162-\"))'"
ssh pve3 "pvesh get /nodes/pve3/replication --output-format json | jq '.[] | select(.id | startswith(\"162-\"))'"
```

### Timing expectations

| Metric | Green | Yellow | Red |
|---|---|---|---|
| **Outage time** (T_ct_stopped_on_pve3 → T_ct_started_on_pve2) (AC-3) | ≤ 60 s | 61–180 s | > 180 s (**root-cause before closing**) |
| ha-manager migrate total wall-clock (AC-2) | ≤ 60 s | 61–180 s | > 180 s |
| Replication flip settle (AC-4) | ≤ 2 cycles (~2 min on `*/1`) | 2–5 cycles | > 5 cycles or never (indicates CRM + replication are not reconciling — will burn 6.7) |
| ntfy push delivery latency (AC-5, Outcome A) | ≤ 90 s from T_migrate_issued | 90–180 s | > 180 s (phone FCM path degraded) |
| Round-trip total (migrate out + back) (AC-6) | ≤ 3 min wall-clock | 3–8 min | > 8 min (re-run with root cause documented) |
| **Planned outage window for CT162** | ~1–2 min active offline within a ≤5-min total drill window | — | If outage exceeds 5 min, abort drill and investigate before retry |

### Evidence artifacts

All under `homelab-playbook/_bmad-output/drill-evidence/v4-ct162-failover-<YYYY-MM-DD>/`:

- `pre/ha-manager-status.txt`, `pre/pvesr-status-pve3.txt`, `pre/ct162-uptime.txt`, `pre/heartbeat-pre.txt`, `pre/alertmanager-alerts-pre.json`, `pre/dashboard-pre.png` (optional)
- `during/timeline.txt` (key epochs), `during/ha-manager-timeline.txt` (full poll output), `during/alertmanager-alerts-during.json`, `during/notification-outcome-<date>.txt`
- `post/ha-manager-status.txt`, `post/pvesr-status-pve2+pve3.txt`, `post/replication-flip-<date>.txt`, `post/heartbeat-post.txt`, `post/ct162-uptime.txt`, `post/alertmanager-alerts-post.json`, `post/dashboard-post.png` (optional)

### Rollback-during-drill scenarios

**Scenario A — CT162 fails to start on pve2** (stuck in `starting` or errors out pre-flight). Possible causes: pve2 not quorate (re-check `pvecm status`), pve2's replica dataset stale/missing (check `zfs list` on pve2), HA manager stuck (`systemctl status pve-ha-crm pve-ha-lrm` on pve2).
- Fallback 1: `ha-manager crm-command migrate ct:162 pve3` to force CT162 back to its original home. CT162 returns, drill aborts, incident note filed.
- Fallback 2 (if AC-2's migrate directive itself hung): `ha-manager set ct:162 --state started` to re-arm HA state machine, then retry `ha-manager crm-command migrate`.
- Fallback 3 (if HA path is entirely broken mid-drill): `pct start 162` manually on pve3 (the original home) — NOT HA-managed, but restores service. Then `ha-manager set ct:162 --state started` to re-register. 6.7 should NOT proceed until the HA stack is demonstrably healthy again.
- Capture all stderr and state logs to `during/failure-<date>.log`. A failed AC-2 is not a failed Story 6.6 — it is a found-bug in the HA stack; file a blocker story before 6.7.

**Scenario B — Replication direction does not flip (AC-4 fails)**. Symptom: after CT162 is live on pve2, `pvesr status` on pve2 does not show 162-* as source; the old pve3-sourced jobs are stuck or stale.
- First check: was CT162 actually writing while on pve2? Write a new marker (`pct exec 162 -- sh -c "date > /root/v4-while-on-pve2"`) to force delta.
- If replication is still stale: `pvesr run --id 162-0 --verbose` on whichever node is the source per the current config. If `pvesr` refuses with "source is not this node", manually recreate the jobs: `pvesr delete 162-0 && pvesr create-local-job 162-0 pve1 --schedule '*/1' --rate 50` on pve2.
- This scenario is a significant finding — Proxmox versions differ on auto-flip behaviour. Record verbatim in AC-4 evidence; this is exactly what 6.6 exists to surface before 6.7.

**Scenario C — ha-manager `crm-command migrate`-back fails or per-resource `failback=1` auto-migrate doesn't trigger** (AC-6). The CT should come back on its own if ct:162 has `failback=1` (PVE 9.1+ replacement for legacy group-level `nofailback=0`) and pve3 is the preferred node; if it doesn't, and the explicit migrate also fails, follow Scenario A Fallback 1-3. Accepting CT162 staying on pve2 temporarily is fine — the drill already validated AC-2 through AC-5; schedule a non-drill migrate-back later.

**Scenario D — Alertmanager reports unrelated firing alert during the drill window**. Do not confuse it with drill output. Filter alerts strictly on `PVECluster*` or HA-lifecycle names when assessing AC-5.

### Why `ha-manager crm-command migrate`, NOT `pct migrate`

`pct migrate <vmid> <target>` performs a straight-line container migration through pveproxy/SSH. It bypasses the HA manager entirely — the CRM does not see the move as an HA state transition; the LRM on both nodes is uninvolved. Using `pct migrate` here would test the `pct migrate` code path, not the HA failover path. The 6.7 pull-plug drill will rely on exactly the CRM+LRM handshake that `ha-manager crm-command migrate` exercises. Rehearsing the wrong path produces a false sense of readiness.

`ha-manager crm-command migrate <sid> <target>` (PVE 9.1+ canonical form; verified live 2026-04-25 via `ha-manager help migrate`) puts the SID into `requested_state=migrate` with a target node. The CRM picks it up on its next scheduling tick (default every 10 s), the current LRM stops the CT, the target LRM starts it. This is the same state machine the CRM will use after a pull-plug — the only difference is the `requested_state` transition source (operator directive vs. dead-node detection). The legacy form `ha-manager migrate ...` may still work via a compatibility shim but the `crm-command` namespace is the documented form.

### Planned outage window

Target total drill wall-clock: **≤ 5 minutes** end-to-end (Task 2 start to Task 8 end). Of that:

- CT162 actively offline: ~1–2 minutes (the `stopped` window on pve3, before it starts on pve2 — then again briefly during migrate-back)
- Observation / evidence capture: ~3 minutes

Recommended schedule slot:

- **Preferred:** weekend daytime or any after-hours window when quant-trading signals are quiet
- **Acceptable:** any low-traffic workday window with the operator actively watching
- **Avoid:** market-open hours (CT162 is quant-trading — this is a drill, not a production outage, but treat it like an operational change)

Announce the drill in the drill log with start/end timestamps so post-hoc incident correlation (if any trading signal is anomalous during the window) can rule the drill in or out.

### Why the notification check can return Outcome B

Story 7.11 closed the notification gap for **replication alerts** (`PVEReplication*` family). It did NOT add an alert rule for HA lifecycle events — `ha-manager migrate` is expected operator action, not a fault. There is no `PVEClusterHAMigration` alert in `replication-alerts.yml` today (confirmed by grep). If the cluster emits any HA-related metric that Prometheus scrapes, a rule could be written; otherwise, a new exporter is needed. 6.6 surfacing Outcome B is a **feature of the drill** — it's how we find out. The fix lives in Epic 7 (backlog), not in 6.6.

Note: this gap does NOT block Story 6.7 (pull-plug drill) — the pull-plug event will fire `PVEReplicationStale` / `PVEReplicationFailing` alerts via the replication-health path once pve3 goes away, which Story 7.11 DOES cover. The missing rule is specifically the "graceful migration occurred" event, and graceful migrations are, by nature, not an incident.

### Prior art references

- **Story 6.1** — the 8 replication jobs this drill flips mid-flight
- **Story 6.2** — the Prometheus/Grafana monitoring that stays silent (except for Outcome A) during the drill; also contributes the `seconds_since_last_sync` metric the replication-flip check uses
- **Story 6.3** (rewritten — supersedes original 6.4) — defines the `critical` HA node-affinity rule that ct:162 belongs to AND HA-registers the resource (per-resource `failback=1` is what enables AC-6's auto-return scenario; PVE 9.1+ replacement for legacy group-level `nofailback=0`)
- **Story 6.4** — superseded; absorbed into rewritten Story 6.3
- **Story 6.5** (sibling drill) — finalised CT162 schedule and provides the baseline RPO numbers this drill's replication-flip check implicitly relies on; also cleared VMID 100 USB risk (relevant if operator confuses a VMID 100 migration with CT162 failover)
- **Story 6.7** (next drill) — consumes 6.6's decision gate (AC-7)
- **Story 7.11** — Alertmanager + ntfy push channel; this drill is its first real HA-lifecycle exercise
- **`pve3-storage-migration-epics.md` §"Story 6.6"** — baseline AC (lines 1022–1035) is narrower; expansion to absorb timing categorisation + replication-flip check + notification gap surface was SM judgement to bring Story 6.6 in line with the Epic 6 "observed-not-assumed" quality bar

### File layout

Files to create:

- `homelab-playbook/_bmad-output/drill-evidence/v4-ct162-failover-<date>-{pre,during,post}/*.{txt,json,log,png}`

Files to modify:

- `homelab-infra/docs/ha-replication-runbook.md` — add `## V4 Drill Results` section; update "Known gaps" if Outcome B (notification); update the "Related stories" list to reference 6.6 retrospectively if not already present

## Test strategy

**Phase 1 (Tasks 0-1):** pre-flight + evidence baseline. No cluster state changes. Outcome: captured pre-state or aborted drill.

**Phase 2 (Tasks 2-3):** the active drill — ha-manager migrate, outage measurement, heartbeat verification. CT162 is offline during this phase. Outcome: measured outage_seconds, green/yellow/red classification.

**Phase 3 (Task 4):** replication direction flip verification. Passive observation + `pvesr status` polling. Outcome: documented alternative behaviour (AC-4).

**Phase 4 (Task 5):** notification path check. Passive observation of Alertmanager / phone. Outcome: Outcome A or Outcome B, both documented verbatim.

**Phase 5 (Tasks 6-7):** migrate back + post-state capture. Second short outage. Outcome: CT162 back on pve3, evidence captured.

**Phase 6 (Task 8):** replication catch-up + snapshot sanity. Catches any stale state left by the flip.

**Phase 7 (Tasks 9-10):** documentation + commits. No cluster mutation.

**Evidence that the drill passed:**

- `during/timeline.txt` records green outage_seconds (≤ 60 s) — or yellow with an explanation — for AC-3
- `post/replication-flip-<date>.txt` shows one of the two AC-4 alternatives; both `162-*` legs `OK` within 2 cycles
- `during/notification-outcome-<date>.txt` records Outcome A (with delivery latency) or Outcome B (with backlog note referenced)
- `post/heartbeat-post.txt` contents match `pre/heartbeat-pre.txt` (filesystem continuity)
- `post/ha-manager-status.txt` shows CT162 back on pve3 with `state: started`
- Runbook `## V4 Drill Results` section written with all required rows
- Grafana dashboard all-green post-drill; no residual firing `PVEReplication*` alerts
- **NEEDS OPERATOR CONFIRMATION**: the ntfy phone notification is checked visually by the operator at the time of the drill; there is no automated way to assert the phone buzzed short of tailing the ntfy server logs (which is also captured via Alertmanager API, but the final "phone actually buzzed" assertion is manual)

## Security considerations

- `ha-manager migrate` uses existing cluster-internal SSH + corosync. No new credentials or network exposure.
- Heartbeat file `/root/v4-heartbeat.txt` is non-sensitive (a timestamp string). Deleted at drill end is not required — acceptable to leave as a historical marker; the next drill (V5) can refresh it.
- Evidence files include internal IPs and job IDs — operational metadata, safe to commit.
- VMID 100 is NOT touched by 6.6. USB caveats from 6.5 do not apply.
- Alertmanager API calls go through `https://alertmanager.bi-services.be` via Traefik+Authelia — operator must be SSO-authenticated for the `curl` calls. Alternative: `docker exec alertmanager amtool` on ct-docker-01 (no SSO).

## Rollback procedure

**Drill abort mid-flight (before Task 6):**

```bash
# If CT162 is live on pve2 and drill is aborted for any reason, migrate back immediately
ssh pve1 "ha-manager crm-command migrate ct:162 pve3"
# Wait for ha-manager status to show ct:162 (pve3, started)
for i in $(seq 1 45); do
  ssh pve1 "ha-manager status | grep ct:162"
  sleep 2
done
ssh pve3 "pct status 162"    # must be running
```

**Replication stale on migrate-back:**

```bash
# If pvesr status shows 162-* with old LastSync, force catch-up before closing
ssh pve3 "pvesr run --id 162-0 --verbose"
ssh pve3 "pvesr run --id 162-1 --verbose"
# Verify
ssh pve3 "pvesr status"
```

**HA migrate hangs on migrate-back:**

- Try `pct start 162` on pve3 directly if the CT is already stopped on pve2 — recovers service non-HA-managed. File an incident Dev Note.
- `ha-manager set ct:162 --state started` to re-register HA state after manual start.
- Do NOT proceed to Story 6.7 — a hanging HA migrate is a blocker, not a nuance.

**Heartbeat file lost or mutated** (AC-3 fails): strong signal that replication did NOT deliver the filesystem intact. Do NOT proceed to Story 6.7. File a blocking story; re-run Story 6.5 to re-verify replication correctness.

**Evidence files partial / drill didn't run to completion:** delete the `_bmad-output/drill-evidence/v4-ct162-failover-<date>-*` dirs; do not commit partial evidence. Story 6.6 remains in `draft` / `ready-for-dev`; the next attempt creates a fresh evidence dir.

## References

- **Epic/AC source**: `homelab-playbook/_bmad-output/planning-artifacts/pve3-storage-migration-epics.md` §"Story 6.6" (lines 1022–1035)
- **Sibling 6.x stories**:
  - `6-1-create-replication-jobs-per-4-5-matrix.md` — creates the replication jobs that must flip
  - `6-2-verify-replication-state-and-deltas.md` — the monitoring/alert chain this drill piggybacks on
  - Story 6.3 (HA node-affinity rules + resource registration; PVE 9.1+ rules model — supersedes original 6.4) — defines the rule ct:162 belongs to AND HA-registers ct:162; must be done before 6.6 starts
  - Story 6.4 — superseded; absorbed into rewritten Story 6.3
  - `6-5-validation-drill-v3-replication-rpo-for-ct162.md` — sibling drill; finalises the replication cadence 6.6 operates against
  - Story 6.7 (pull-plug) — downstream, gated on 6.6's green-light decision
- **Notification chain**: `7-11-alertmanager-and-ntfy-push-channel.md` — the ntfy push path tested in AC-5
- **Guardrail**: `7-3-implement-ci-guardrail-preventing-ha-ct-on-non-replicable-storage.md` — verifies CT162 remains on replicable storage; passive cross-check during the drill
- **Primary runbook**: `homelab-infra/docs/ha-replication-runbook.md` — receives the `## V4 Drill Results` section
- **OMEGA memory**: `project_quant_trading` — CT162 home node, resources, application context
- **Proxmox docs**:
  - HA Manager: <https://pve.proxmox.com/wiki/High_Availability>
  - `ha-manager` man page: <https://pve.proxmox.com/pve-docs/ha-manager.1.html>
  - CRM + LRM architecture: <https://pve.proxmox.com/pve-docs/chapter-ha-manager.html>
- **Sprint change authority**: `homelab-playbook/_bmad-output/planning-artifacts/sprint-change-proposal-2026-04-24.md` §2 (HA priority matrix — CT162 critical)

## Dev Agent Record (2026-04-25)

**Operator:** BMad Dev (claude-opus-4-7) via Claude Agent SDK
**Drill window:** 09:28 → 09:34 UTC (≈6 min wall-clock; CT162 active offline ~23 s total across both legs)
**Outcome:** **PASS — GREEN on every measured threshold.** Story 6.7 decision gate: green-light.

### Timeline (UTC, all epochs from polling output and LRM journals)

| Phase | T (UTC) | Epoch | Event |
|---|---|---|---|
| Pre-flight | 09:28:39 | 1777109319 | `pvecm status` 3/3 quorate; 6 HA services started; 162-* OK; 0 PVE alerts |
| Pre-flight | 09:28:59 | 1777109339 | Heartbeat written inside ct:162 on pve3: `v4-drill T_pre=2026-04-25T09:28:59Z epoch=1777109339` |
| Pre-flight | ~09:30:00 | — | Detected `prometheus` container exited at 09:24:30Z (clean compaction, exit 255 no error). Restarted before AC-8 capture; healthy throughout drill. |
| Forward | 09:30:34 | 1777109434 | `ha-manager crm-command migrate ct:162 pve2` issued from pve1 |
| Forward | 09:30:38 | 1777109438 | LRM pve3: `vzshutdown:162` task ended OK |
| Forward | 09:30:46 | 1777109446 | First poll: HA `(pve2, starting)`, pct status running on pve2 |
| Forward | 09:30:49 | 1777109449 | LRM pve2: `service status ct:162 started` |
| Forward | 09:30:56 | 1777109456 | CRM acknowledged `(pve2, started)` |
| Verify | 09:31:14 | — | Heartbeat readable on pve2 (byte-identical), uptime 0 min, IP 192.168.50.162 up |
| Replication | 09:31:01–09:31:06 | — | First post-fwd cycle: `162-0`/`162-1` re-sourced from pve2 automatically (auto-flip) |
| Backward | 09:31:59 | 1777109519 | `ha-manager crm-command migrate ct:162 pve3` issued from pve1 |
| Backward | 09:32:07 | 1777109527 | LRM pve2: `vzshutdown:162` task ended OK |
| Backward | 09:32:15 | — | Polling sees HA `(pve3, starting)`, pct status running on pve3 |
| Backward | 09:32:19 | 1777109539 | LRM pve3: `service status ct:162 started` |
| Backward | 09:32:25 | 1777109545 | CRM acknowledged `(pve3, started)` |
| Verify | 09:32:35 | — | Heartbeat readable on pve3 (byte-identical), uptime 0 min, IP up |
| Replication | 09:32:01–09:32:08 | — | Post-back cycle: `162-0`/`162-1` re-sourced from pve3, target pve1/pve2 |
| Post-state | 09:33:55 | — | Final `ha-manager status`: 6/6 services started, ct:162 (pve3, started) |

### AC verdict table

| AC | Verdict | Evidence | Notes |
|---|---|---|---|
| AC-1 Pre-flight baseline | PASS | `pre/preflight.txt`, `pre/heartbeat-pre.txt`, `pre/alertmanager-alerts-pre.json`, `pre/pve_ha_resource_state-ct162-pre.json` | Cluster 3/3, replication OK, no PVE alerts. Prometheus container had exited 4 min pre-drill; restarted before AC-8 evidence capture. |
| AC-2 Forward migrate timing | PASS (GREEN) | `during/timeline.txt`, `during/ha-manager-fwd-poll.txt`, `during/lrm-journal-fwd.txt` | Wall-clock cmd → CRM started: 22 s. Outage (LRM-bounded): 11 s. Both ≤60 s green. |
| AC-3 Outage + heartbeat RTO | PASS (GREEN) | `during/heartbeat-postfwd.txt`, `post/heartbeat-post.txt` | Outage 11 s fwd / 12 s back. Heartbeat byte-identical both legs. CT uptime 0 min on both targets (real restart). |
| AC-4 Replication direction flip | PASS (Outcome: auto-flip in-place) | `during/pvesr-postfwd.txt`, `post/pvesr-post.txt` | Proxmox rewrote `source` field within one cycle. `162-0`/`162-1` source pve3 → pve2 → pve3. FailCount=0. Cosmetic stale comment on `162-1`. |
| AC-5 ntfy notification | PASS (Outcome B documented) | `during/alertmanager-alerts-during.json`, `post/alertmanager-alerts-post.json` | Only `AlertmanagerDeadManSwitch` (info heartbeat) firing. No HA-migration alert exists; backlog note captured. Expected gap, does not block 6.7. |
| AC-6 Migrate-back | PASS (GREEN) | `during/ha-manager-back-poll.txt`, `post/lrm-journal-back.txt` | Outage 12 s, wall-clock 26 s, round-trip 111 s — all GREEN. Heartbeat survived. |
| AC-7 Runbook V4 section | PASS | `homelab-infra/docs/ha-replication-runbook.md` | New `### V4 Drill Results (2026-04-25)` section inserted above `### End-to-end drill status`, ~53 lines (verified via `git show 59396ee --stat`). |
| AC-8 Story 6.10 alert chain | PASS | `post/ac8-prometheus.txt` | `pve_ha_resource_state` captured both transitions via `exported_node` label mutation. Honest query: `count by (exported_node) (count_over_time(...[20m]))` returns 3 distinct samples each for pve2 and pve3. `error/fence/recovery` always 0; `PVEHAResourceUnhealthy` correctly silent. |

### Files touched

**Modified:**

- `homelab-infra/docs/ha-replication-runbook.md` — added V4 Drill Results section (~53 lines (verified via `git show 59396ee --stat`), between V3 Drill Results and End-to-end drill status)
- `homelab-playbook/_bmad-output/implementation-artifacts/6-6-validation-drill-v4-simulated-failover-via-migrate.md` — frontmatter `status: draft → review`; this Dev Agent Record appended

**Created:**

- `homelab-playbook/_bmad-output/drill-evidence/v4-ct162-failover-2026-04-25/pre/preflight.txt`
- `homelab-playbook/_bmad-output/drill-evidence/v4-ct162-failover-2026-04-25/pre/heartbeat-pre.txt`
- `homelab-playbook/_bmad-output/drill-evidence/v4-ct162-failover-2026-04-25/pre/ct162-uptime.txt`
- `homelab-playbook/_bmad-output/drill-evidence/v4-ct162-failover-2026-04-25/pre/alertmanager-alerts-pre.json`
- `homelab-playbook/_bmad-output/drill-evidence/v4-ct162-failover-2026-04-25/pre/pve_ha_resource_state-ct162-pre.json`
- `homelab-playbook/_bmad-output/drill-evidence/v4-ct162-failover-2026-04-25/during/timeline.txt`
- `homelab-playbook/_bmad-output/drill-evidence/v4-ct162-failover-2026-04-25/during/ha-manager-fwd-poll.txt`
- `homelab-playbook/_bmad-output/drill-evidence/v4-ct162-failover-2026-04-25/during/ha-manager-back-poll.txt`
- `homelab-playbook/_bmad-output/drill-evidence/v4-ct162-failover-2026-04-25/during/lrm-journal-fwd.txt`
- `homelab-playbook/_bmad-output/drill-evidence/v4-ct162-failover-2026-04-25/during/heartbeat-postfwd.txt`
- `homelab-playbook/_bmad-output/drill-evidence/v4-ct162-failover-2026-04-25/during/pvesr-postfwd.txt`
- `homelab-playbook/_bmad-output/drill-evidence/v4-ct162-failover-2026-04-25/during/alertmanager-alerts-during.json`
- `homelab-playbook/_bmad-output/drill-evidence/v4-ct162-failover-2026-04-25/post/heartbeat-post.txt`
- `homelab-playbook/_bmad-output/drill-evidence/v4-ct162-failover-2026-04-25/post/lrm-journal-back.txt`
- `homelab-playbook/_bmad-output/drill-evidence/v4-ct162-failover-2026-04-25/post/pvesr-post.txt`
- `homelab-playbook/_bmad-output/drill-evidence/v4-ct162-failover-2026-04-25/post/ha-manager-status.txt`
- `homelab-playbook/_bmad-output/drill-evidence/v4-ct162-failover-2026-04-25/post/ac8-prometheus.txt`
- `homelab-playbook/_bmad-output/drill-evidence/v4-ct162-failover-2026-04-25/post/alertmanager-alerts-post.json`
- `homelab-playbook/_bmad-output/drill-evidence/v4-ct162-failover-2026-04-25/v4-summary-2026-04-25.md`

### Deviations from story plan

1. **Prometheus container was in `Exited (255)` state at start of drill** (last log entry 09:00:01Z TSDB compaction; container actually exited 09:24:30Z with no error). Detected during AC-1 pre-flight; restarted with `docker start prometheus` and verified `/-/healthy` before proceeding. Did not abort because the cause was clearly clean shutdown (no error stack, no OOM, exit during compaction window) and the drill window allowed recovery. Logged as a separate observation; this is unrelated to the V4 drill itself but worth noting as a flap of unknown origin in the alerting infrastructure — recommend a follow-up to set `restart: always` on prometheus container or investigate compose file (currently `unless-stopped`, which means a manual stop would persist; a clean shutdown then-no-restart could indicate something stopped it manually or a watchdog issue).

2. **`ha-manager status --verbose` poll cadence**: story plan specified 2 s polling for 120 s. Used the same 2 s cadence but with a bounded 60-iteration loop and 8 s per-SSH timeout (exit-on-state-match). Forward leg matched at iteration 12 (T+22 s); backward at iteration 14 (T+26 s). No timeouts.

3. **`changes()` query for AC-8 returned 0**: this is a known semantic of Prometheus `changes()` — it works on values within a single time series, but the home-node transition surfaces as new series creation / old series removal (the `exported_node` label changes). The honest verification is `count by (exported_node) (count_over_time(...[20m]))` and a range query showing `exported_node=pve2` series existed for ~105 s during the migration window. Documented in the runbook section. Not a defect in Story 6.10; just a subtlety of the metric model (state IS captured; `changes()` is the wrong function for a label-mutation transition).

4. **No abort scenarios encountered.** All 8 ACs verified PASS. No HA `error`/`fence` state; replication FailCount=0 throughout; cluster stayed quorate; no unexpected alerts; heartbeat survived.

### Next actions for operator

- Flip sprint-status YAML for Story 6.6 from in-progress → review (outside Dev scope; per project rules).
- Story 6.7 (pull-plug drill) decision gate is GREEN — can be scheduled.
- Optional Epic 7 backlog: add a `PVEClusterCTMigrated` alert rule (would close Outcome B notification gap); not blocking.
- Optional infra follow-up: investigate the `prometheus` container clean-exit at 09:24:30Z — likely a one-off but worth confirming no recurring pattern.

## Change Log

- **2026-04-25 — fix-apply pass**: Applied F1 (runbook alert filter scope + graceful-vs-fence distinction), F2 (what migration does/does not preserve section), F3 (line-count discrepancy), F4 (changes()-vs-label-mutation discoverability — moved from V4 inline to runbook §Monitoring/Alert Verification), F5 (operational guardrails: migrate spacing, flip latency, AC-8 evidence chain caveat), F6 (cosmetic 162-1 comment fix). Adversarial R2+R4 → Story 6-6-1 (drafted in parallel); R3 + code L2 → Story 6-10-3 (drafted in parallel); R7+R8 → fold into existing 6-9-1; R1 outcome-B → fold into existing 6-10-1.
