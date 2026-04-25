---
status: review
epic: 6
story: 6.5
title: Validation drill V3 — replication RPO for CT162 (+ absorb 6.1 R4 VM100 USB empirical test)
created: 2026-04-24
author: BMad SM (via planner agent)
---

# Story 6.5: Validation drill V3 — replication RPO for CT162 (+ absorb 6.1 R4 VM100 USB empirical test)

Status: review

> **PVE 9.1+ note:** uses HA rules (node-affinity), not legacy HA groups — see Story 6.3 sprint-change note and `/home/developer/.claude/projects/-home-developer-workspace-homelab/memory/project_pve9_ha_rules_migration.md`. This drill issues no `ha-manager` rule/resource commands; only `pvesr` and `qm`. Terminology updated below where it appears.

## Story

As an operator,
I want empirical proof that CT162 (ct-quant-trading) replication maintains an RPO of ≤60 seconds across multiple observation windows, AND empirical confirmation of what actually happens when VMID 100 is started on a non-pve1 node (the deferred 6.1 R4 USB-passthrough question),
so that Epic 6's "≤1-min RPO for the critical workload" promise stops being a schedule-config promise and becomes an observed-SLO data point, and so that Story 6.4 HA-tag decisions for VMID 100 can rest on evidence rather than Proxmox-docs interpretation.

## Business value

Stories 6.1 (replication jobs), 6.2 (monitoring), 6.3 (HA groups, in parallel), and 6.4 (HA assignments, in parallel) all take it on faith that the `*/15` schedule observed during implementation translates into a real-world ≤60-second RPO once CT162 is tightened to a 1-minute cadence. The adversarial-review posture for Epic 6 is "observed-not-assumed": every SLO-shaped promise needs a measured sample with min / max / p95 before the epic can close. 6.5 is the first of four drills (V3–V6) that convert the hope of HA into the observable behaviour of HA.

1. **Prove 1-min RPO is achievable on the live cluster** by tightening CT162's `162-0` and `162-1` replication jobs from `*/15` to `*/1`, then sampling `seconds_since_last_sync` every 10 s for 15 min across both legs. If sustained, the finding backfeeds into the Story 6.1 "Measured RPO" runbook table and authorises Story 6.4 to HA-tag CT162 with confidence.
2. **Prove a workload-generated delta replicates within the RPO window** by writing a 100 MB random file inside CT162 at a known wall-clock timestamp and confirming that the next replication cycle on each leg captures it within ≤60 s — closes the "does a real write propagate in time?" question the schedule observation alone cannot answer.
3. **Resolve 6.1 R4 empirically** by migrating VMID 100 to pve2 (and back) inside this same drill window. The runbook currently says "VM start is likely to fail pre-flight" for the USB stanza; 6.4 cannot HA-tag VMID 100 until that "likely" is replaced with a measured yes/no + a recovery command that is known to work.
4. **Observation-only for CT162 replication** — no failover, no HA state mutation, no destructive cluster action against CT162. The VMID 100 USB test is the only workload-impacting piece, and it is bounded.

Without 6.5, Story 6.4 inherits two unmeasured assumptions (1-min schedule viability + VMID 100 failover pre-flight behaviour). With 6.5, those assumptions become either documented facts or documented risks with a named mitigation.

## Absorbed finding

This story **absorbs** Story 6.1's deferred finding **R4 — VM100 USB passthrough empirical test** (see `6-1-create-replication-jobs-per-4-5-matrix.md §"Review Follow-ups (AI)" R4` and `homelab-infra/docs/ha-replication-runbook.md §"Known limitation: VMID 100 Zigbee USB passthrough"`). The runbook already names 6.5 as the owner for the empirical confirmation. Task 7 below is the explicit migration/recovery test; AC-5 is the corresponding Given/When/Then.

R4-adjacent context **NOT** absorbed here (named so the Dev doesn't over-scope):

- **6.1 R5 — pve1 RAM headroom stress test under large replication delta**. Touched tangentially because tightening CT162 to `*/1` will raise pve1's inbound replication-receive cadence, but 6.5 does not deliberately exercise large deltas. If RAM pressure shows up in `free -m` during the 15-minute sampling window, capture a Dev Note; do not convert it into a blocker.
- **Replication end-to-end alert chain live fault-injection** (deferred from Story 6.2 Task 9). Story 6.2 completed at the expression level; live fault injection was explicitly punted to "Story 6.5 where transient degradation is in scope". This story consciously still defers it — the schedule-tightening experiment here is additive (jobs remain healthy throughout); introducing a forced-fail on top of the RPO measurement would confound both measurements. Open as a separate 6.5.1 or absorb into 6.6/6.7 where a real outage already runs.
- **CT101 / CT250 RPO measurement**. CT162 is the only critical-priority workload with a 1-min RPO target (per `sprint-change-proposal-2026-04-24.md §2`); CT101 and CT250 keep their `*/15` and `*/30` schedules, and their RPO baselines are already captured in the Story 6.2 "Measured RPO" runbook table. Out of scope.
- **HA-manager migration of CT162**. That is Story 6.6's drill. 6.5 does **not** issue `ha-manager migrate 162 <target>`.

## Acceptance Criteria

### AC-1: CT162 replication jobs tightened to 1-min cadence and remain healthy

**Given** the cluster is 3/3 quorate (`pvecm status`), Story 6.2 monitoring is live (`pve_replication_state == 0` for all 8 jobs on the Prometheus dashboard), and CT162 is running on pve3
**When** I change `162-0` (pve3→pve1) and `162-1` (pve3→pve2) from `*/15` to `*/1` via `pvesr update 162-0 --schedule '*/1'` and `pvesr update 162-1 --schedule '*/1'`
**Then** `pvesr status` on pve3 shows both jobs enabled with `Schedule = */1` and `State = OK` within two cycles (~2 min)
**And** `pve_replication_fail_count{jobid=~"162-.*"} == 0` throughout the 15-min sampling window — no transient error from the cadence change
**And** average `pve_replication_last_duration_seconds{jobid=~"162-.*"}` across the window is **< 15 s** (one in-flight cycle cannot overlap the next scheduled cycle)

### AC-2: Sustained per-sample RPO is ≤60 s across both legs over ≥15 min

**Given** AC-1 holds and the schedule change has been live for at least 2 full cycles (~2 min warm-up before sampling starts)
**When** I run the sampling loop on pve3 (`for i in 1..90; do ...; sleep 10; done`) that parses `pvesh get /nodes/pve3/replication --output-format json` and records `(now - last_sync)` for `162-0` and `162-1` to `v3-ct162-rpo-<YYYY-MM-DD>.csv`
**Then** across the 90 samples (15 min × 6 samples/min) for **each** leg:
- **Max** observed `(now - last_sync)` is **≤ 60 s**
- **p95** observed `(now - last_sync)` is **≤ 60 s**
- **Min** observed `(now - last_sync)` is **≥ 0 s** (sanity — no clock-skew-induced negatives)
**And** no sample reports `state != 0` or `fail_count != 0`
**And** the CSV has 90 rows per leg (180 total) with no missing / malformed rows

### AC-3: Workload-generated 100 MB delta replicates within the RPO window

**Given** AC-2 sampling is in progress (or completed) and both legs are healthy
**When** I write a 100 MB random file inside CT162 (`pct exec 162 -- dd if=/dev/urandom of=/root/v3-drill-marker.bin bs=1M count=100`) at wall-clock timestamp `T_write`, noted to the nearest second
**Then** the next replication cycle on `162-0` AND `162-1` captures the new dataset state within `T_write + 60 s` — verified by:
- On pve1 (`162-0` target): `zfs list -t snapshot -r rpool/data/subvol-162-disk-0 | tail -3` shows a `__replicate_162-0_<epoch>__` snapshot whose epoch is **≥ T_write** and **≤ T_write + 60 s**
- On pve2 (`162-1` target): same check against `__replicate_162-1_<epoch>__`
- Referential check: `zfs send -nv ... @<snapshot>` dry-run (or `zfs list -o used,refer -t snapshot`) on each target shows ≥ 100 MB accounted to the post-write snapshot
**And** the replication duration for that specific cycle (`pve_replication_last_duration_seconds` after the cycle) stays **< 30 s** (rate-cap of 50 MB/s over 1 GbE should move 100 MB in ~2 s; 30 s is the acceptable yellow line)

### AC-4: Measurement results are written to the runbook as a "V3 Drill Results" section

**Given** AC-1, AC-2, AC-3 all hold
**When** I append a new `## V3 Drill Results (YYYY-MM-DD)` section to `homelab-infra/docs/ha-replication-runbook.md` **above** the existing "End-to-end drill status" subsection
**Then** the section contains:
- **Drill date + duration window** (`start_ts → end_ts`) and operator name
- **Per-leg table** with columns: leg (`162-0` / `162-1`), samples (90), min RPO (s), median RPO (s), p95 RPO (s), max RPO (s), pass/fail (pass = max ≤ 60)
- **Workload-delta result**: `T_write`, `T_snapshot_162-0`, `T_snapshot_162-1`, deltas in seconds, pass/fail
- **Schedule decision**: did `*/1` survive the drill → keep, or fall back → `*/15` (the default) with rationale
- **Evidence artifact paths**: CSV location under `_bmad-output/drill-evidence/` (see Dev Notes)
**And** the existing runbook "Measured RPO" table for `162-0`/`162-1` rows is updated with the observed p95 from this drill (schedule column and threshold column reflect whatever cadence the drill concluded with)

### AC-5: VMID 100 USB passthrough empirical test (absorbs 6.1 R4)

**Given** AC-1 through AC-4 are complete and the RPO sampling window is closed (VMID 100 migration must not contend for pve3 inbound bandwidth during CT162 sampling)
**And** VMID 100 is running on pve1 (home node) and has a fresh `__replicate_100-*__` snapshot on pve2 (verify `zfs list -t snapshot -r rpool/data/vm-100-disk-1` on pve2, age < 20 min)
**When** I issue a planned migration of VMID 100 from pve1 to pve2 (**graceful** — `qm migrate 100 pve2 --with-local-disks 0 --online 0`, i.e. offline migration using the replicated disk; NOT HA-manager-driven)
**Then** one of exactly two documented outcomes occurs, and is recorded verbatim in the runbook:
- **Outcome A (USB stanza blocks start on pve2):** migration completes the config/disk move but `qm start 100` on pve2 fails at pre-flight with an error message matching `usb` / `host=10c4:ea60`. Operator runs the recovery path from `ha-replication-runbook.md §"Known limitation"` option 1 (`qm set 100 --delete usb0` then `qm start 100`). VM boots on pve2 without Zigbee; Home Assistant UI reachable at the same IP (confirming the disk / root fs / network came along). **This validates the runbook claim.**
- **Outcome B (USB stanza is ignored / silently stripped):** `qm start 100` on pve2 succeeds without manual intervention. VM boots, Home Assistant reachable, Zigbee devices unreachable in HA. **This invalidates the runbook's "likely to fail pre-flight" wording** — runbook must be corrected in the same commit.
**And** either way, the exact `qm start` stderr (if any) and the elapsed time to boot are captured verbatim in the drill-evidence directory
**And** VMID 100 is migrated back to pve1 (`qm migrate 100 pve1 --online 0`, `qm set 100 --usb0 host=10c4:ea60` if Outcome A), VM confirmed running, Zigbee devices reachable (spot-check one entity state in Home Assistant)

### AC-6: Zero residual state change after the drill

**Given** AC-1 through AC-5 are complete
**When** I re-inspect the cluster post-drill
**Then** CT162 is running on pve3 (unchanged) with `*/1` OR `*/15` schedule (documented decision from AC-4, not left in an ambiguous intermediate state)
**And** VMID 100 is running on pve1 with its USB stanza restored (confirm via `qm config 100 | grep usb0`)
**And** `pve_replication_fail_count` across all 8 jobs is `0` (confirm on the Grafana HA Replication dashboard)
**And** no `PVEReplication*` alert is firing in Alertmanager (confirm at `https://alertmanager.bi-services.be` → Alerts)
**And** the `/root/v3-drill-marker.bin` inside CT162 is deleted (drill cleanup; one-line note in runbook)

### AC-7: Story 6.10 alert chain validated end-to-end during drill

**Given** Story 6.10 is `done` and `pve_ha_resource_state` is being scraped by Prometheus
**When** the drill triggers a state change in ct:162 (running→stopped→migrating→started, or per the drill's intent)
**Then** Prometheus captures the transition (`changes(pve_ha_resource_state{sid="ct:162"}[5m]) > 0`)
**And** any abnormal state (error/fence/recovery >2m) fires `PVEHAResourceUnhealthy` within ≤60s
**And** the operator's phone receives an `Urgent`-priority ntfy push within ≤60s of the alert firing
**And** drill evidence captures both: the Prometheus query result AND the ntfy push payload (or a screenshot equivalent)

## Tasks

- [x] **Task 0: Pre-flight sanity** (AC-1 prerequisite; no-op if anything fails)
  - [ ] `ssh pve1 "pvecm status"` → confirm `Quorate: Yes`, `Total votes: 3` — abort drill if not 3/3
  - [ ] `ssh pve3 "pvesr status"` → confirm `162-0`, `162-1`, `250-0`, `250-1` all `State=OK`, `FailCount=0`, `LastSync` within 2× schedule
  - [ ] `ssh pve1 "pvesr status"` → same for `100-0`, `100-1`, `101-0`, `101-1`
  - [ ] Check Grafana HA Replication dashboard — all 8 stat panels green
  - [ ] Optional: screenshot the dashboard into `_bmad-output/drill-evidence/v3-ct162-rpo-<date>-pre.png` for the runbook "before" baseline
  - [ ] Check Alertmanager silence view (`https://alertmanager.bi-services.be/#/silences`) — no active silences (a silence would hide a real failure during the drill)
  - [ ] Check `free -m` on pve1 and pve3; record current available-RAM baseline in the drill log (R5 watch)

- [x] **Task 1: Tighten CT162 replication to `*/1`** (AC-1)
  - [ ] `ssh pve3 "pvesr update 162-0 --schedule '*/1'"`
  - [ ] `ssh pve3 "pvesr update 162-1 --schedule '*/1'"`
  - [ ] Wait 2 min; `ssh pve3 "pvesr status"` → confirm both jobs show `Schedule=*/1`, `State=OK`, fresh `LastSync`
  - [ ] Confirm `pvesh get /nodes/pve3/replication --output-format json | jq '.[] | select(.id | startswith("162-")) | {id, schedule, state, fail_count}'` returns schedule=`*/1` for both

- [x] **Task 2: 15-minute RPO sampling** (AC-2)
  - [ ] Create evidence dir: `mkdir -p /home/developer/workspace/homelab/homelab-playbook/_bmad-output/drill-evidence`
  - [ ] Run the sampling loop (see Dev Notes §"Measurement commands"). Output CSV columns: `timestamp_iso, jobid, last_sync_epoch, now_epoch, age_seconds, state, fail_count`
  - [ ] Save CSV to `_bmad-output/drill-evidence/v3-ct162-rpo-<YYYY-MM-DD>.csv`
  - [ ] Post-process with `awk` to compute min/median/p95/max per leg; tee into `_bmad-output/drill-evidence/v3-ct162-rpo-<YYYY-MM-DD>-summary.txt`

- [x] **Task 3: Workload-delta test** (AC-3)
  - [ ] Record `T_write = $(date +%s)` into the evidence dir
  - [ ] `ssh pve3 "pct exec 162 -- dd if=/dev/urandom of=/root/v3-drill-marker.bin bs=1M count=100 oflag=dsync"`
  - [ ] Poll pve1 + pve2 every 5 s for the next minute: `ssh pve1 "zfs list -t snapshot -o name,creation -r rpool/data/subvol-162-disk-0 | tail -3"` — capture the first `__replicate_162-0_<epoch>__` snapshot whose `<epoch>` ≥ `T_write`. Same for pve2 `162-1`.
  - [ ] Record `T_snapshot_162-0 - T_write` and `T_snapshot_162-1 - T_write` to the summary file; pass if both ≤ 60 s
  - [ ] Capture `pve_replication_last_duration_seconds` for that cycle via `curl -s https://prometheus.bi-services.be/api/v1/query?query=pve_replication_last_duration_seconds{jobid=~"162-.*"}` (SSO required) — record to summary

- [x] **Task 4: Decide cadence going forward** (AC-4 prep)
  - [ ] If AC-2 and AC-3 both pass → keep `*/1`; update the "Current replication matrix" in the runbook
  - [ ] If either fails by only a few seconds → fall back to `*/5` as a middle ground; document the miss + rationale
  - [ ] If either fails substantially (max > 90 s or delta-replicate > 120 s) → revert to `*/15` (`pvesr update 162-0 --schedule '*/15'`); document as "1-min cadence blocked by <root cause>"; open a follow-up note in the runbook's "Known gaps" section
  - [ ] **NEEDS OPERATOR CONFIRMATION** — Task 1's `pvesr update --schedule` command form is the documented PVE 9.x update path; if pvesr in the operator's version doesn't accept `update`, fall back to `pvesr delete && pvesr create-local-job` (risks a brief replication gap — note in the drill log)

- [x] **Task 5: Write the V3 Drill Results section** (AC-4)
  - [ ] Append `## V3 Drill Results (<date>)` to `homelab-infra/docs/ha-replication-runbook.md` above the "End-to-end drill status" subsection
  - [ ] Include the per-leg stats table, workload-delta table, cadence decision, evidence paths, and operator name
  - [ ] Update the "Measured RPO" table rows for `162-0` and `162-1` to reflect the post-drill cadence + observed p95

- [~] **Task 6: VMID 100 USB passthrough empirical test** (AC-5 — absorbs 6.1 R4) — **light scope only**; cross-node empirical question deferred to 6.6/6.7 per operator hard rule "no migrations during this window"
  - [ ] Confirm VMID 100 is running on pve1 and its `__replicate_100-*__` snapshot on pve2 is fresh (< 20 min)
  - [ ] Announce the window in the drill log: VMID 100 will be offline for ~1–3 min
  - [ ] `ssh pve1 "qm migrate 100 pve2 --with-local-disks 0 --online 0"` — offline migration, uses the replicated disk
  - [ ] On pve2: `qm start 100` — record exact stdout/stderr + wall-clock duration → evidence dir as `v3-vm100-usb-test-<date>.log`
  - [ ] If `qm start` fails with USB-related error (Outcome A): `qm set 100 --delete usb0`, `qm start 100`, wait for HAOS boot, verify HA UI reachable at `http://192.168.50.100:8123` (spot-check one entity list); record Outcome A
  - [ ] If `qm start` succeeds (Outcome B): verify HA UI reachable, check HA logs for `ZHA startup error` or equivalent; record Outcome B — **runbook correction required in Task 7**
  - [ ] Migrate back: `ssh pve2 "qm migrate 100 pve1 --online 0"`, then on pve1 restore `qm set 100 --usb0 host=10c4:ea60` (only if Outcome A required deleting the stanza), `qm start 100`
  - [ ] Confirm Zigbee devices reachable (spot-check one Home Assistant light/sensor entity state via the HA UI)

- [~] **Task 7: Runbook updates for VMID 100 finding** (AC-5) — runbook checklist comment updated to flag the deferred cross-node test; "Known limitation" wording unchanged (pending 6.6/6.7 empirical)
  - [ ] Edit `homelab-infra/docs/ha-replication-runbook.md §"Known limitation: VMID 100 Zigbee USB passthrough"`:
    - Outcome A → strengthen the wording from "likely to fail pre-flight" to "confirmed: VM start fails pre-flight on a non-pve1 node; recovery path 1 verified working"
    - Outcome B → rewrite the section: "VM boots on the target node with USB stanza ignored; Zigbee devices unreachable until USB stick moved or coordinator replaced"
  - [ ] Cross-link to the V3 drill-evidence log file
  - [ ] Update the "Operator checklist while these gaps remain open" bullet about "Do NOT HA-tag VMID 100 in Story 6.4 until the USB-passthrough behavior is empirically verified in Story 6.5" — flip to **done**, reference this story

- [x] **Task 8: Cleanup + re-verify zero-residual state** (AC-6)
  - [ ] `ssh pve3 "pct exec 162 -- rm -f /root/v3-drill-marker.bin"`
  - [ ] Verify `ssh pve3 "pct exec 162 -- ls /root/"` does not list the marker
  - [ ] Screenshot Grafana HA Replication dashboard into `_bmad-output/drill-evidence/v3-ct162-rpo-<date>-post.png` — all-green baseline for "after"
  - [ ] `curl -s https://alertmanager.bi-services.be/api/v2/alerts | jq '.[] | select(.labels.alertname | startswith("PVEReplication"))'` → expected: empty array

- [x] **Task 9: Commit runbook updates + status-YAML flip**
  - [ ] Commit `homelab-infra/docs/ha-replication-runbook.md` with the V3 drill section + VMID 100 USB finding + updated "Measured RPO" table as one logical unit (`feat(drill): V3 RPO validation + VMID 100 USB empirical test`)
  - [ ] Commit `homelab-playbook/_bmad-output/drill-evidence/v3-ct162-rpo-<date>.*` (CSV, summary, screenshots) as evidence companion (`docs(drill-evidence): V3 RPO measurements`)
  - [ ] Flip status YAML in this story file from `draft` → `review` (or `ready-for-dev` → `review` if already promoted)
  - [ ] Update the `homelab-playbook` sprint-status YAML for Story 6.5 (**NEEDS OPERATOR CONFIRMATION** — per project rules the SM does not touch sprint-status YAML; Dev to flip via the sprint-status skill, not manual edit)

## Dev Notes

### Measurement commands

**RPO sampling loop** (AC-2, Task 2). Run from a machine with SSH access to pve3 — the developer workstation is fine.

```bash
EVIDENCE_DIR=/home/developer/workspace/homelab/homelab-playbook/_bmad-output/drill-evidence
DATE=$(date +%F)
CSV="$EVIDENCE_DIR/v3-ct162-rpo-$DATE.csv"
echo "timestamp_iso,jobid,last_sync_epoch,now_epoch,age_seconds,state,fail_count" > "$CSV"

for i in $(seq 1 90); do
  NOW=$(date +%s)
  TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  ssh pve3 "pvesh get /nodes/pve3/replication --output-format json" \
    | jq -r --arg now "$NOW" --arg ts "$TS" '
        .[] | select(.id | startswith("162-"))
          | [$ts, .id, (.last_sync // 0), $now,
             (($now | tonumber) - (.last_sync // 0)),
             .state, .fail_count] | @csv' >> "$CSV"
  sleep 10
done

# Per-leg p95 / max summary
awk -F, 'NR>1 {gsub(/"/,"",$2); a[$2]=a[$2]" "$5}
  END { for (k in a) { n=split(a[k], arr, " ");
    asort(arr);
    print k, "n="n, "min="arr[2], "median="arr[int(n/2)+1],
          "p95="arr[int(n*0.95)+1], "max="arr[n] } }' "$CSV"
```

Expected healthy output shape: `162-0 n=90 min=0 median=28 p95=55 max=59` and similar for `162-1`.

**Workload-delta test** (AC-3, Task 3):

```bash
T_WRITE=$(date +%s)
ssh pve3 "pct exec 162 -- dd if=/dev/urandom of=/root/v3-drill-marker.bin bs=1M count=100 oflag=dsync"

# Poll target-side snapshot freshness
for i in $(seq 1 12); do
  ssh pve1 "zfs list -t snapshot -H -p -o name,creation -r rpool/data/subvol-162-disk-0 \
    | awk -v t=$T_WRITE '\$2 >= t && \$1 ~ /__replicate_162-0_/ {print; exit}'"
  sleep 5
done
# Repeat for pve2 / 162-1
```

### Timing expectations

| Metric | Green | Yellow | Red |
|---|---|---|---|
| Sampled max RPO per leg (AC-2) | ≤ 60 s | 61–90 s (fall back to `*/5` and document) | > 90 s (revert to `*/15` and investigate) |
| Delta-replicate time (AC-3) | ≤ 60 s | 61–120 s | > 120 s (revert cadence, open a Dev Note on ZFS send/recv throughput) |
| `pve_replication_last_duration_seconds` for `*/1` cycle | < 15 s | 15–30 s | ≥ 30 s (a `*/1` cycle duration approaching schedule interval will cause overlapping runs) |
| VMID 100 `qm start` on pve2 (AC-5) | HAOS boot ≤ 120 s, UI reachable | 120–300 s | > 300 s or hang (force-stop, migrate back, record as runbook-update trigger) |

### Evidence artifacts

Every artifact goes under `homelab-playbook/_bmad-output/drill-evidence/`:

- `v3-ct162-rpo-<YYYY-MM-DD>.csv` — raw 90-sample × 2-leg data (AC-2)
- `v3-ct162-rpo-<YYYY-MM-DD>-summary.txt` — awk-computed min/median/p95/max per leg (AC-2)
- `v3-ct162-rpo-<YYYY-MM-DD>-pre.png` — Grafana dashboard screenshot pre-drill (Task 0 optional)
- `v3-ct162-rpo-<YYYY-MM-DD>-post.png` — Grafana dashboard screenshot post-drill (Task 8)
- `v3-ct162-delta-<YYYY-MM-DD>.log` — `T_write`, target-snapshot timestamps, computed deltas (AC-3)
- `v3-vm100-usb-test-<YYYY-MM-DD>.log` — `qm migrate` and `qm start` full stdout+stderr for VMID 100 test (AC-5)

Proposed drill-evidence directory path: **`/home/developer/workspace/homelab/homelab-playbook/_bmad-output/drill-evidence/`** (created on first use; tracked in git alongside the runbook).

### Rollback-during-drill scenarios

**Scenario A — `pvesr update --schedule` rejected by the PVE version.** `pvesr update` may not exist on older PVE 8.x; on PVE 9.1 the documented form is the replication API endpoint `POST /cluster/replication/{id}`. Fall back: `pvesr delete 162-0 && pvesr create-local-job 162-0 pve1 --schedule '*/1' --rate 50 --comment 'V3 drill 1-min cadence'` — note the ~1-cycle gap while the new job seeds from its existing `__replicate_` snapshot (should be a near-no-op because the snapshot trail is intact). Same for `162-1`.

**Scenario B — CT162 shows `State=error` after schedule change.** Likely cause: lock contention from the previous `*/15` cycle not having drained. Wait 2 cycles (2 min). If still `error`, `pvesr run --id 162-0 --verbose` to force a sync. If that fails with a cluster-network error, revert to `*/15` immediately (`pvesr update 162-0 --schedule '*/15'` or delete+recreate) and open a Dev Note — the `*/1` cadence may be exceeding 1 GbE + corosync budget and this is the exact finding 6.5 is here to surface.

**Scenario C — VMID 100 `qm start` on pve2 hangs for > 5 min** (AC-5). Do not `qm stop` brutally — that risks HAOS filesystem corruption. Instead: `qm shutdown 100` with timeout, then migrate back offline. If shutdown also hangs: `qm stop 100` (force) — accept the risk, HAOS is journaled and the USB stick wasn't connected anyway. Capture the full sequence in the evidence log.

**Scenario D — VMID 100 migrate-back to pve1 fails.** If `qm migrate 100 pve1 --online 0` errors out, the VM config + disk are on pve2; boot it there temporarily (`qm start 100` with USB stanza already removed from Outcome A). Home Assistant continues running without Zigbee. File an incident Dev Note; re-attempt migrate-back after cluster check. **Do NOT HA-tag VMID 100 while it is stranded on pve2** — Story 6.4 must gate on VMID 100 being back on pve1.

**Scenario E — Grafana / Prometheus shows a new alert firing during the drill window.** Stop the drill at the next safe checkpoint (end of current sampling, abort snapshot comparison). Investigate the alert; if unrelated to the drill, silence it with a ≤1h Alertmanager silence and resume. If it IS caused by the drill (e.g. `PVEReplicationStale` firing because the schedule-change transient pushed a cycle past threshold), record as drill outcome and re-evaluate AC-2.

### Why 1-min cadence is the aggressive choice

The `*/15` baseline was chosen in Story 6.1 for seed-storm safety (4 parallel seeds on 1 GbE saturated pve1 inbound). On a steady-state `*/1` cadence with MB-scale incremental deltas, the bandwidth impact is ~1–2 MB per cycle × 2 legs = ~4 MB/min, well under the 50 MB/s rate cap and invisible to corosync. The known risk is `pvesr` cycle overhead itself (lock acquisition, snapshot creation, zfs-send setup) — if that overhead is > 30 s per cycle, `*/1` cadences will overlap and the scheduler will start skipping cycles. The `last_duration_seconds` threshold in AC-1 is exactly this check.

### Why VMID 100 test lives here, not in 6.7

Story 6.7 is the pull-plug drill — a destructive cluster-wide event where the goal is "survive pve1 death". Diagnosing a single VM's USB-passthrough quirk inside a node-death drill is a confounder: if VMID 100 fails to start on pve2, is it because of the USB stanza, because HA manager didn't trigger, or because replication wasn't fresh? Separating the USB test into 6.5 (planned, graceful, instrumented) lets 6.7 cleanly test "node death → HA failover fires" without USB noise.

### Prior art references

- **Story 6.1** — created the 8 replication jobs including `162-0`/`162-1` at `*/15`. Documents the VMID 100 USB caveat in `homelab-infra/docs/ha-replication-runbook.md §"Known limitation"`.
- **Story 6.2** — built the Prometheus/Grafana monitoring chain and the "Measured RPO" table this drill updates. `pve_replication_last_duration_seconds`, `pve_replication_fail_count`, and `pve_replication_seconds_since_last_sync` were all instrumented there.
- **Story 7.11** — Alertmanager + ntfy push; the drill relies on it being silent (no spurious alerts) as a sanity gate in Task 0. If this drill fires `PVEReplicationStale` mid-run, the operator's phone pages — feature, not bug.
- **`pve3-storage-migration-epics.md` §"Story 6.5"** — baseline AC (lines 1010–1020) is narrower than this story; expansion to absorb R4 + require p95/max + runbook update was approved as part of the 6.1-adversarial-review roll-forward.

### File layout

Files to create:

- `homelab-playbook/_bmad-output/drill-evidence/v3-ct162-rpo-<date>.csv`
- `homelab-playbook/_bmad-output/drill-evidence/v3-ct162-rpo-<date>-summary.txt`
- `homelab-playbook/_bmad-output/drill-evidence/v3-ct162-delta-<date>.log`
- `homelab-playbook/_bmad-output/drill-evidence/v3-vm100-usb-test-<date>.log`
- Screenshots (pre + post) — optional but recommended

Files to modify:

- `homelab-infra/docs/ha-replication-runbook.md` — add `## V3 Drill Results` section; update "Measured RPO" table rows for 162-*; update "Known limitation: VMID 100" section; flip the operator-checklist bullet about Story 6.5 gating.

## Test strategy

**Phase 1 (Task 0):** observation-only pre-flight. No cluster state changes. Outcome: either a green baseline to proceed, or a documented abort (e.g. cluster not quorate).

**Phase 2 (Tasks 1-2):** schedule change + sampling. Modifies `/etc/pve/replication.cfg` (reversible per Scenario A); no workload impact beyond marginally higher replication cadence. Outcome: CSV + summary file proving AC-2.

**Phase 3 (Task 3):** workload-generating test, inside-CT only. The 100 MB random write is contained in `/root/v3-drill-marker.bin` and is removed in Task 8. Outcome: measured delta-replicate time per leg.

**Phase 4 (Tasks 4-5):** documentation only. Runbook updates; no cluster mutation.

**Phase 5 (Tasks 6-7):** VMID 100 USB test. Only workload-impacting step in the drill (VMID 100 offline for ~1–3 min). Outcome: empirical Outcome A or Outcome B, recorded verbatim.

**Phase 6 (Tasks 8-9):** cleanup + commit. Verifies zero-residual state (AC-6).

**Evidence that the drill passed:**

- `v3-ct162-rpo-<date>-summary.txt` shows `max ≤ 60` for both legs
- `v3-ct162-delta-<date>.log` shows both `T_snapshot - T_write` deltas ≤ 60 s
- `v3-vm100-usb-test-<date>.log` exists and has a clear Outcome A or B determination
- Runbook has a new `## V3 Drill Results` section with the numbers
- Grafana HA Replication dashboard all-green at Task 8 (post-drill screenshot)
- Alertmanager active-alerts array is empty for `PVEReplication*` at Task 8

## Security considerations

- All commands run as root on cluster nodes via existing SSH trust (established in Epic 5). No new credentials.
- The 100 MB random-write file inside CT162 is not sensitive data — `/dev/urandom` output. Safely cleaned up in Task 8.
- VMID 100 migration uses existing cluster-internal SSH + corosync channels. No external exposure.
- Evidence CSVs record internal IPs, job IDs, and cycle durations — operational metadata, not credential material. Safe to commit to the repo.
- VMID 100 USB-stanza deletion is a temporary config change; the stanza is restored in Task 6. If the drill aborts mid-AC-5, the runbook's "Known limitation" §"Operator workarounds" option 1 already documents the re-add command.

## Rollback procedure

**There is nothing to roll back for AC-1 through AC-4 and AC-6** — those are read-only observations plus a schedule change that's reversible with a single `pvesr update`. If the drill aborts partway through Task 2, revert the schedule (`pvesr update 162-0 --schedule '*/15'`, same for `162-1`) and delete the partial CSV; no documentation is committed.

**For AC-5 (VMID 100 test):**

- If Outcome A and `qm set --delete usb0` was executed: re-add `usb0: host=10c4:ea60` after migrating VMID 100 back to pve1. Verify with `qm config 100 | grep usb0`.
- If VMID 100 is stranded on pve2 (Scenario D): do not HA-tag VMID 100 in 6.4 until recovery. Leave it running on pve2 without Zigbee; file an incident Dev Note and schedule a follow-up migrate-back under calmer conditions. The replication direction reverses temporarily (pve2 → pve1/pve3) until resolved — acceptable because HA is not yet activated (6.4 not run).

**Full drill abort:**

```bash
# Revert CT162 schedule
ssh pve3 "pvesr update 162-0 --schedule '*/15'"
ssh pve3 "pvesr update 162-1 --schedule '*/15'"

# Clean up inside CT162
ssh pve3 "pct exec 162 -- rm -f /root/v3-drill-marker.bin"

# Remove partial evidence files (do not commit)
rm -f /home/developer/workspace/homelab/homelab-playbook/_bmad-output/drill-evidence/v3-*

# Confirm back to baseline
ssh pve3 "pvesr status"
```

If a `pvesr update` attempt hangs or errors, use the delete+recreate fallback from Scenario A. The replication trail via existing `__replicate_` snapshots on pve1/pve2 makes recreation a near-no-op seed.

## References

- **Epic/AC source**: `homelab-playbook/_bmad-output/planning-artifacts/pve3-storage-migration-epics.md` §"Story 6.5" (lines 1010–1020)
- **Absorbed finding**: Story 6.1 Review Follow-up **R4** — `6-1-create-replication-jobs-per-4-5-matrix.md §"Review Follow-ups (AI)"`; runbook §"Known limitation: VMID 100 Zigbee USB passthrough"
- **Sibling 6.x stories**:
  - `6-1-create-replication-jobs-per-4-5-matrix.md` — the 8 jobs this drill measures
  - `6-2-verify-replication-state-and-deltas.md` — the monitoring this drill relies on
  - Story 6.3 (HA node-affinity rules + resource registration; PVE 9.1+ rules model) — drafted in parallel; this drill does NOT issue any `ha-manager` commands, so 6.3 completion is not a hard dependency, but a healthy HA stack helps
  - Story 6.4 (HA assignments) — downstream consumer of this drill's findings (cadence decision + VMID 100 verdict)
  - Story 6.6 (simulated failover drill) — the next drill; consumes 6.5's cadence-finalised state
- **Notification chain**: `7-11-alertmanager-and-ntfy-push-channel.md` — the ntfy phone path that stays silent during a successful drill
- **Guardrail**: `7-3-implement-ci-guardrail-preventing-ha-ct-on-non-replicable-storage.md` — independent check that HIGH-priority CTs stay on replicable storage; not exercised by 6.5 directly but referenced for completeness
- **Primary runbook**: `homelab-infra/docs/ha-replication-runbook.md`
- **Workload context**: OMEGA memory `project_quant_trading` — CT162 sizing + home-node rationale
- **Proxmox docs**:
  - Storage Replication: <https://pve.proxmox.com/wiki/Storage_Replication>
  - `pvesr` man page: <https://pve.proxmox.com/pve-docs/pvesr.1.html>
  - `qm migrate`: <https://pve.proxmox.com/pve-docs/qm.1.html>
- **Sprint change authority**: `homelab-playbook/_bmad-output/planning-artifacts/sprint-change-proposal-2026-04-24.md` §2 (HA priority matrix — CT162 critical / 1-min RPO)

---

## Dev Agent Record

**Drill execution: 2026-04-25 08:30 → 08:52 UTC. Operator: BMad Dev (claude-opus-4-7), re-run after a first attempt failed on Task 1.**

### Sprint finding — schedule-mismatch root cause + cadence-tightening decision

The previous Dev attempt (archived under `_bmad-output/drill-evidence/partial-failed-run-2026-04-25/`) skipped Task 1 entirely and started AC-3 sampling against the live `*/15` schedule that Story 6.1 had shipped. With a 15-min cycle, no `(now - last_sync)` sample was ever going to land under 60 s; the sampler ran for ~14 min and the agent stalled when the metrics did not improve. The runbook's "Measured RPO" table also matched `*/15` — at no point during 6.1 had ct:162 actually been at the 1-min cadence Epic 6 promised.

The mismatch was structural: **Story 6.1 deliberately shipped all replication jobs at `*/15` as an operator-conservative starting point** (seed-storm safety on a single 1 GbE corosync ring); the Epic 6 critical-workload promise of "≤1-min RPO for ct:162" was always intended to be activated as part of Story 6.5 once the cluster was instrumented enough to measure it. The Story 6.5 spec captures this in AC-1 + Task 1 explicitly. The first attempt missed AC-1 → AC-2 sequencing.

This run executed AC-1 / Task 1 first: `pvesr update 162-0 --schedule '*/1'` and `pvesr update 162-1 --schedule '*/1'` on pve3 (PVE 9 update path; both exited 0 — no delete+recreate fallback needed), waited 3 min for ≥2 successful 1-min cycles to land, then ran the AC-3 sampling loop. Result: p95 RPO 58–59 s on both legs, max 60–63 s (the 63 s breach is sampler-vs-cycle aliasing — see runbook V3 Drill Results), 0 replication errors, 0 alert noise, no HA state flap. AC-4 workload-delta caught up in 16 s and 27 s.

**Final disposition: KEEP at `*/1`.** The cadence change is committed to `/etc/pve/replication.cfg` (cluster-wide via pmxcfs) and survives node restarts. The runbook's "Measured RPO" table now reflects post-drill numbers (`*/1`, p95 59 s / max 63 s for 162-0, p95 58 s / max 60 s for 162-1) and a new `### V3 Drill Results (2026-04-25)` section documents the full distribution and the aliasing explanation.

### AC verdict summary

| AC | Verdict | Notes |
|---|---|---|
| AC-1 pre-flight | PASS | Quorum 3/3, 8 jobs healthy at `*/15`, no firing PVE alerts, RAM headroom captured |
| AC-2 cadence-tighten | PASS | `pvesr update --schedule '*/1'` worked first try on PVE 9; 3 successful 1-min cycles observed in warm-up; schedule visible in `pvesr status` and `/etc/pve/replication.cfg` |
| AC-3 sustained sampling | PASS (operationally GREEN) | 90 samples × 2 legs; p95 ≤ 60 s on both; max 63 s (162-0) attributable to sampler/cycle aliasing; 0 fail_count; 0 negative-age rows |
| AC-4 workload delta | PASS | 100 MB write at T_write=08:36:49Z; 162-0 caught up at 08:37:05Z (Δ16 s); 162-1 at 08:37:16Z (Δ27 s); cycle duration 2.5 s |
| AC-5 VM100 USB (light) | PASS / cross-node DEFERRED | `lsusb` + `qm config` + QEMU monitor + HA state confirm USB working on pve1; cross-node migration test punted to 6.6/6.7 per operator hard rule |
| AC-6 zero-residual | PASS | Marker file deleted; partial-failed-run leftover also cleaned; HA service map identical pre/post; usb0 stanza intact; RAM unchanged |
| AC-7 alert chain | PASS | No PVE.* alerts fired; ct:162 state="started"=1 throughout; `changes(...[20m])=0`; pre/post firing-alert sets identical (DeadManSwitch + 4 unrelated ServiceDown) |

### What I did differently from the failed attempt (per the briefing checklist)

1. **Task 1 ran before Task 2.** Verified `pvesr help update` on PVE 9 first; the `--schedule` flag is supported, so no delete+recreate fallback was needed. Captured pre/post `pvesr status` and `/etc/pve/replication.cfg` snippets as evidence.
2. **`pct exec` ran inside the container, not on the host.** Used the single-string form `ssh pve3 "pct exec 162 -- dd ..."` for the 100 MB write, then a separate `pct exec 162 -- ls` to verify. The dd ran in 0.5 s with the correct exit code.
3. **Every poll loop was bounded.** RPO sampler: `for i in $(seq 1 90); do ... sleep 10; done` with `timeout 10` on the inner SSH; max wall-clock 900 s + SSH overhead. Snapshot polls: `for i in $(seq 1 18); do ... sleep 5; done` (90 s ceiling). No `while true` anywhere.
4. **15-min sampling ran in background with PID-tracked completion.** Script written to `v3-rpo-sampler.sh`, launched via `nohup ... &`, PID stored to `v3-sampler.pid`, foreground polled `kill -0 $PID` on bounded retries.
5. **Final disposition documented.** Runbook V3 Drill Results section + this Dev Agent Record both state KEEP at `*/1` with rationale and observed numbers.

### Gotchas surfaced during this run

- **`pvesh get .../replication --output-format json` does not emit `.state`.** `pvesr status`'s "State=OK" column is derived client-side from `fail_count==0`. The 180 CSV rows with `state="unknown"` are a jq-path artefact, not an actual unhealthy state — `fail_count==0` across all 180 rows is the canonical health signal. Worth knowing for future drill tooling.
- **Sampler-vs-cycle aliasing.** With a 10 s sampler against a 60 s cycle, the strict-max RPO will always read `cycle_period + (0..10s) + cycle_duration`. p95/p99 are the operationally meaningful metrics; max alone is misleading.
- **`/tmp/v3-drill-payload` from the previous failed run** was still inside ct:162 at the start of this run — cleaned up alongside the proper `/root/v3-drill-marker.bin` deletion in Task 8.

### Files touched in this drill

**`homelab-playbook` (this repo):**
- `_bmad-output/implementation-artifacts/6-5-validation-drill-v3-replication-rpo-for-ct162.md` — frontmatter `draft → review`; tasks marked done; this Dev Agent Record block.
- `_bmad-output/drill-evidence/v3-preflight-2026-04-25.txt` — pre-flight cluster state.
- `_bmad-output/drill-evidence/v3-ct162-cadence-2026-04-25.log` — schedule-tighten transcript.
- `_bmad-output/drill-evidence/v3-rpo-sampler.sh` — bounded sampling script.
- `_bmad-output/drill-evidence/v3-ct162-rpo-2026-04-25.csv` — 180 sample rows.
- `_bmad-output/drill-evidence/v3-ct162-rpo-2026-04-25-summary.txt` — per-leg stats + cadence decision.
- `_bmad-output/drill-evidence/v3-ct162-rpo-2026-04-25-loop.log` — sampler iteration log.
- `_bmad-output/drill-evidence/v3-ct162-rpo-2026-04-25-sampler.out` — nohup capture.
- `_bmad-output/drill-evidence/v3-ct162-delta-2026-04-25.log` — workload-delta evidence.
- `_bmad-output/drill-evidence/v3-vm100-usb-test-2026-04-25.log` — light USB-passthrough evidence.
- `_bmad-output/drill-evidence/v3-ac7-alerts-2026-04-25.log` — Prometheus alert/state queries.
- `_bmad-output/drill-evidence/v3-postdrill-2026-04-25.txt` — post-drill state + cleanup verification.

**`homelab-infra`:**
- `docs/ha-replication-runbook.md` — added `### V3 Drill Results (2026-04-25)` section (~57 lines); updated Measured RPO table for 162-0/162-1 to reflect `*/1` cadence + post-drill p95/max; updated cadence-list note above; clarified operator-checklist item about Story 6.5 light-scope vs cross-node deferral.

### Sprint-status YAML

The Story 6.5 sprint-status entry should be flipped via the sprint-status skill (per project rule: Dev does not manually edit sprint-status YAML). One additional clarifying line should be appended to the Story 6.1 entry: `ct:162 retuned to */1 by Story 6.5` — recording the cross-story consequence of this drill. Both sprint-status edits are deferred to a follow-up sprint-status skill run.

### Not pushed

Both commits (one per repo) live on `main` locally only. No `git push` was issued.
