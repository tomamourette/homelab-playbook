---
status: backlog
epic: 6
story: 6.5.2
title: 7-day */1 soak telemetry — long-tail observability for ct:162 replication
created: 2026-04-25
author: BMad SM
depends-on: 6-5
---

# Story 6.5.2: 7-day */1 soak telemetry — long-tail observability for ct:162 replication

Status: backlog

## Story

As an operator,
I want Prometheus recording rules and Grafana panels capturing the long-tail behaviour of ct:162 at `*/1` cadence over a 7-day soak window — covering snapshot-count growth, ARC/txg/metadata pressure, send-stream byte volume, and a synthetic small-write workload — and a day-7 runbook check that applies the explicit rollback criterion from Story 6.5,
so that the "KEEP at `*/1`" decision shipped in Story 6.5 stops being a 16-minute snapshot and becomes a measured 7-day commitment with an unambiguous rollback path.

## Business value

Story 6.5's drill ran for ~16 minutes against ct:162 at `*/1`. That is enough to prove a per-cycle p95 ≤ 60 s **at one moment in time**, but it does not characterize:

1. **Snapshot accumulation on `rpool/data/subvol-162-disk-0`** — `*/1` produces ~1440 `__replicate_*` snapshots per day vs. ~96 at `*/15`. Even though `pvesr` prunes older snapshots after each successful cycle, snapshot-count growth in the rootfs subvol is the metric that warns of a stalled-prune failure mode (e.g. one cycle fails silently, the next cycle re-uses the previous snapshot, and the count climbs).
2. **ARC / txg / metadata pressure** — `*/1` cadence increases ZFS metadata churn (snapshot create / destroy / list) by ~15× compared to `*/15`. ARC hit-ratio drift and txg sync p95 are the leading indicators of a memory or IO-pressure failure that the per-cycle Duration metric does not see until the cycle itself misses.
3. **Real quant-trading workload pattern** — Story 6.5's AC-3 wrote 100 MB of `/dev/urandom` in one bulk `dd`. The actual quant-trading workload is small frequent writes (DB transactions, log appends), which exercise a fundamentally different ZFS write path (small txg flushes vs. one big bulk write). The 100 MB `dd` test does not falsify the small-write path.
4. **Day-7 verdict against an explicit rollback criterion** — Story 6.5's Dev Agent Record committed to "KEEP at `*/1`" without naming the conditions under which that decision should be revisited. Without a written threshold, "the cluster feels OK" becomes the default decision rule, which is the same vibes-not-numbers posture Epic 6 was chartered to end.

This story turns a 16-minute proof into a 7-day commitment, with telemetry that any future operator can re-run on demand:

1. **Prometheus recording rules** capture daily snapshot count, ARC delta, txg sync p95, and send-stream byte volume.
2. **Grafana panels** surface the four metrics over the 7-day window so the soak is observable, not just stored.
3. **Day-7 verdict** applies a written rollback criterion (defined below in AC-5) — KEEP at `*/1` if all green, ROLL BACK to `*/15` if any threshold breached.
4. **Synthetic small-write workload** test on day 4-5 falsifies the small-write-path assumption.

Without 6.5.2, the next operator who sees a ct:162 alert at 04:00 has no baseline distribution to compare against and no rollback procedure that does not require re-running 6.5 from scratch.

## Absorbed finding

This story **absorbs** Story 6.5 adversarial-review findings:

- **R4 (MED) — long-tail untested**: 16-min sample doesn't reveal snapshot-count growth on rootfs subvol over 30/60/90 days; ARC/txg/metadata pressure under sustained `*/1` cadence is unobserved.
- **R5 (MED) — workload pattern untested**: real quant-trading workload (small frequent writes) vs. the 100 MB bulk `dd` test that 6.5 actually performed.

Story 6.5 Dev Agent Record §"Gotchas surfaced during this run" implicitly acknowledged R4/R5 by deferring "long-term cycle stability" to follow-up; this story closes that deferral.

R4/R5-adjacent context **not** absorbed here:

- **Aliasing disambiguation** — owned by Story 6.5.1 (1s-cadence falsification run). 6.5.2 starts after 6.5.1 has either confirmed aliasing or surfaced cycle-Duration variance; if the latter, AC-2 recording rules are tuned accordingly.
- **30/60/90-day soak** — out of scope. R4 mentioned 30/60/90 days; the SM-and-operator pragmatic window is 7 days, which is enough to characterize daily/hourly long-tail without staking the epic on a 90-day commitment. If the 7-day soak surfaces a slow trend (e.g. snapshot count creeping +5%/day), file a follow-up note for a longer soak under explicit instrumentation.
- **Cross-workload fairness comparison (CT250 at `*/30`)** — out of scope; that is general monitoring cleanup, not a 6.5-cluster blocker.
- **HA-manager fault-injection during soak** — out of scope; that is Story 6.6/6.7's drill.

## Acceptance Criteria

### AC-1: Pre-flight — cluster healthy, 6.10 alerts working, soak start time recorded

**Given** Stories 6.5 (`done`) and 6.10 (`done`) are live; ct:162 is at `*/1` cadence; Story 6.5.1 has either confirmed aliasing or filed its CYCLE-DURATION-VARIANCE follow-up
**When** I run pre-flight checks:
- `ssh pve1 "pvecm status"` → `Quorate: Yes`, `Total votes: 3`
- `ssh pve3 "pvesr status"` → `162-0` and `162-1` both `Schedule=*/1`, `State=OK`, `FailCount=0`
- Grafana HA Replication dashboard all-green
- `curl -s 'https://prometheus.bi-services.be/api/v1/rules' | jq '.data.groups[].rules[] | select(.name | startswith("PVEHA"))'` returns the 6.10 rule set, all `inactive`
- ntfy push channel verified working (send a test push via `curl -d "soak start" https://ntfy.bi-services.be/homelab-test` and confirm receipt on operator phone)

**Then** all five checks pass
**And** soak-window start time `T_start = $(date -u +%FT%TZ)` is captured to `_bmad-output/soak-evidence/soak-meta.txt`
**And** the pre-flight output is archived to `_bmad-output/soak-evidence/day-0-preflight.txt`
**And** if any pre-flight check fails, the soak does NOT start — fix the upstream issue first

### AC-2: Prometheus recording rules added (snapshot count, ARC, txg, send-stream)

**Given** AC-1 holds
**When** I add a new recording-rules file `homelab-apps/stacks/observability/config/recording/replication-soak.yml` with the following rules **and** install the ZFS textfile collector script `homelab-infra/proxmox/replication/zfs-soak-exporter.sh` on pve3 (the home node for ct:162)
**Then** the following metrics are emitted and queryable in Prometheus within 5 minutes of rule reload:

- **`pve_zfs_snapshot_count{dataset="rpool/data/subvol-162-disk-0"}`** — gauge, count of all snapshots on the dataset (emitted by `zfs-soak-exporter.sh` via textfile collector, refreshed every 5 min)
- **`pve_zfs_arc_hit_ratio_5m`** — recording rule (`zfs_arc_hits_total - on() group_left() (zfs_arc_misses_total) over 5m`) computing the 5-minute ARC hit-ratio delta from existing `node_zfs_*` metrics already emitted by `prometheus-node-exporter`'s ZFS collector
- **`pve_zfs_txg_sync_p95_5m`** — recording rule, 5-minute p95 of `zfs_txg_sync_time` (or whichever node-exporter ZFS metric exposes txg sync timing — see Dev Notes §"What's in node-exporter today")
- **`pve_replication_send_bytes_total{jobid=~"162-.*"}`** — counter (added to `pve-replication-exporter.sh` from Story 6.2) — running total of bytes sent per cycle, derived from `pvesh` / `pvesr` log output

**And** the recording rules are validated with `docker exec prometheus promtool check rules /etc/prometheus/recording/replication-soak.yml` → SUCCESS
**And** the textfile collector script is installed via cron (`*/5 * * * * root /usr/local/bin/zfs-soak-exporter.sh`) on pve3, written atomically, with a `flock`-serialized + `timeout`-wrapped invocation matching the Story 6.2 R6/R7 hardening pattern
**And** Prometheus is hot-reloaded via `docker kill --signal=HUP prometheus` on ct-docker-01 — no Prometheus restart required

### AC-3: Grafana dashboard panels added

**Given** AC-2 holds
**When** I add four panels to the existing `HA Replication` dashboard (`homelab-apps/stacks/observability/dashboards/ha-replication.json`) — OR create a new dashboard `Replication Soak` (UID `replication-soak-6-5-2`) if the existing dashboard is layout-saturated
**Then** the four panels render live data within 5 minutes of dashboard provisioning:

- **Panel A — Snapshot count over time** (time series, 7-day window, dataset filter `rpool/data/subvol-162-disk-0`). Threshold annotation at `+10%` of T_start baseline (visual line).
- **Panel B — ARC hit-ratio delta** (time series, 7-day window). Threshold annotation at `-5%` from T_start baseline.
- **Panel C — txg sync p95** (time series, 7-day window, host filter `pve3`). Threshold annotation at `2× T_start baseline`.
- **Panel D — Send-stream bytes per cycle** (time series, 7-day window, jobid filter `162-.*`). No threshold (informational only — characterizes the actual delta size distribution).

**And** the dashboard JSON is committed
**And** baseline values from `T_start` are captured to `_bmad-output/soak-evidence/day-0-baseline.txt` (queried via `curl https://prometheus.bi-services.be/api/v1/query?query=...`) so day-7 verdict has explicit numbers to compare against

### AC-4: 7-day soak window starts; daily auto-summary cronjob captures metrics

**Given** AC-2 and AC-3 are in place; T_start is recorded
**When** I install a daily cron job on ct-docker-01 (where Prometheus + Grafana run) that captures the previous 24h's metric snapshots
**Then** at 09:00 CEST each day for 7 days, the cron job:
- Queries Prometheus for the four soak metrics (24h windows, min/median/p95/max for time-series; raw value for snapshot count)
- Queries Alertmanager for any `PVEReplication*` or `PVEHA*` alerts that fired in the 24h window
- Writes a daily summary to `_bmad-output/soak-evidence/day-N.md` (where N=1..7) containing:
  - Day number + date
  - Snapshot count at start-of-day, end-of-day, delta
  - ARC hit-ratio delta range
  - txg sync p95 range
  - Send-stream bytes (sum, mean per cycle, p99 single cycle)
  - Alert events (if any) with start/end timestamps
  - Cluster sanity check (`pvesr status` snapshot)

**And** day-N.md files are written by the cron job, NOT manually — operator effort over the soak is "read the dashboard once a day, escalate if anything looks off"
**And** the cron job is idempotent: re-running it for the same day overwrites the file rather than appending duplicates
**And** if the cron job itself fails (e.g. Prometheus unreachable) it sends a single ntfy push and writes a `day-N-FAILED.md` placeholder so the gap is visible

### AC-5: Day-7 verdict applies the rollback criterion (KEEP or ROLL BACK)

**Given** AC-4 has produced 7 daily summaries
**When** I run the day-7 verdict procedure documented in this story's Dev Notes §"Rollback criterion thresholds"
**Then** one of two verdicts is recorded in `_bmad-output/soak-evidence/day-7-verdict.md` and appended to `homelab-infra/docs/ha-replication-runbook.md §"V3 Drill Results"`:

- **Verdict KEEP** — all four thresholds were respected across all 7 days:
  - Snapshot count on `rpool/data/subvol-162-disk-0` did NOT grow more than **+10% above T_start baseline** at any point
  - ARC hit-ratio delta stayed within **−5% of T_start baseline** (i.e. ARC efficiency did not collapse under the increased metadata churn)
  - txg sync p95 stayed below **2× T_start baseline** (i.e. metadata flushes did not start backing up)
  - Zero `PVEReplication*` alerts fired during soak (false-positive rate = 0)

- **Verdict ROLL BACK** — at least one threshold breached. The verdict file names the breached threshold(s), the day(s) it occurred on, and the suspected cause. Cadence is reverted to `*/15` per AC-8.

**And** the verdict is annotated with the underlying soak-evidence pointer (e.g. "see `day-3.md` for ARC delta breach at 14:30 CEST")
**And** the runbook §"V3 Drill Results" is updated with the soak verdict above the existing Story 6.5 KEEP decision (the new verdict supersedes the 16-min finding)

### AC-6: Small-write workload pattern test on day 4-5

**Given** the soak is in-progress and the cluster is healthy on day 4 (no breaches in days 1-3)
**When** on day 4 or day 5 I run the small-write workload pattern test described in Dev Notes §"Small-write test", which simulates 100 small DB transactions/min for 30 min inside ct:162 (each transaction ~4 KB write + fsync, total ~30 MB written across the test)
**Then** during the 30-min test window:
- ct:162 replication legs `162-0` and `162-1` continue to report `State=OK`, `FailCount=0` — verified via `pvesr status` snapshot every 5 min during the test
- The per-cycle `pve_replication_last_duration_seconds` for both legs stays below **2× the soak-baseline median** (small frequent writes should still snap inside ≤30 s — anything else suggests txg flush queueing)
- Send-stream bytes per cycle (`pve_replication_send_bytes_total` rate over 5 min) shows the small-write delta replicating per cycle (not coalescing into one big cycle), validating the small-write path
- No `PVEReplication*` or `PVEHA*` alert fires during the test window
- Test transcript + measured numbers archived to `_bmad-output/soak-evidence/day-N-small-write-test.log`

### AC-7: Final report appended to runbook with measured numbers

**Given** AC-5 and AC-6 are complete
**When** I append a `### V3 Soak Results (<T_start> → <T_start + 7d>)` section to `homelab-infra/docs/ha-replication-runbook.md` immediately under §"V3 Drill Results (2026-04-25)"
**Then** the section contains:
- Soak window (T_start, T_end, duration)
- Per-day summary table (7 rows × 5 columns: day, snapshot count delta, ARC delta range, txg p95 range, alerts fired)
- Small-write test outcome (pass/fail with measured numbers)
- Day-7 verdict (KEEP or ROLL BACK) with rationale
- Pointer to evidence directory `_bmad-output/soak-evidence/`
- Observed long-tail patterns (e.g. "snapshot count peaks at 23:30 CEST coincident with `pvesr` prune lag — within tolerance")
**And** the existing "Measured RPO" table in the runbook is **left unchanged** — soak telemetry is about long-tail, not per-cycle p95 (which 6.5 already captured)

### AC-8: If ROLL BACK — cadence reverted, runbook updated, post-mortem captured

**Given** AC-5 returned **Verdict ROLL BACK**
**When** I revert the cadence:
```bash
ssh pve3 "pvesr update 162-0 --schedule '*/15'"
ssh pve3 "pvesr update 162-1 --schedule '*/15'"
```
**Then** within 2 cycles, `pvesr status` on pve3 shows both jobs back to `Schedule=*/15`, `State=OK`
**And** the runbook §"Measured RPO" table for `162-0`/`162-1` is reverted to its pre-6.5 schedule + thresholds (or amended to "`*/15`, p95 reverted to <pre-6.5 baseline> after 7-day */1 soak surfaced <breach>")
**And** a post-mortem note is written to `_bmad-output/soak-evidence/post-mortem.md` containing:
- Which threshold breached and on which day
- Suspected root cause (with evidence pointer)
- Whether `*/5` (intermediate cadence) is a candidate to retest, or `*/15` is the conservative final
- Whether a follow-up Story (e.g. "investigate ZFS metadata-flush behaviour under */1 cadence") should be opened
**And** the operator-checklist in the runbook is updated to flip the "ct:162 at `*/1`" assumption back to "`*/15` until further notice"

**Note**: if AC-5 returned **Verdict KEEP**, AC-8 is `N/A — soak passed`.

## Tasks / Subtasks

- [ ] **Task 1: Pre-flight sanity** (AC-1)
  - [ ] Run the five pre-flight checks; archive output to `day-0-preflight.txt`
  - [ ] Capture `T_start`, baselines for each of the four soak metrics, ntfy test push
  - [ ] Abort if any check fails

- [ ] **Task 2: Implement `zfs-soak-exporter.sh` on pve3** (AC-2)
  - [ ] Write the exporter script at `homelab-infra/proxmox/replication/zfs-soak-exporter.sh` — emits `pve_zfs_snapshot_count{dataset="..."}` for the ct:162 rootfs subvol
  - [ ] Apply Story 6.2 R6/R7 hardening: `flock -n -E 0 /var/lock/zfs-soak-exporter.lock`, `timeout 30 zfs list -t snapshot ...`, atomic write via `mktemp` + `mv`
  - [ ] Install via cron (`/etc/cron.d/zfs-soak-exporter`) on pve3 (only — pve1/pve2 are replication targets, source-side metric only needed on home node)
  - [ ] Verify the metric appears in Prometheus within 5 min: `curl -s 'https://prometheus.bi-services.be/api/v1/query?query=pve_zfs_snapshot_count'`

- [ ] **Task 3: Add recording rules + reload Prometheus** (AC-2)
  - [ ] Create `homelab-apps/stacks/observability/config/recording/replication-soak.yml` with the three recording rules (ARC delta, txg p95, send-stream — snapshot count is gauge-only, no recording rule needed)
  - [ ] **NEEDS OPERATOR CONFIRMATION** — verify which `node_zfs_*` metric names actually exist in your `prometheus-node-exporter` build before authoring the recording-rule expressions; metric names vary across node-exporter versions (e.g. `node_zfs_arcstats_hits` vs `zfs_arc_hits_total`). Run `curl -s http://192.168.50.203:9100/metrics | grep -E '^(node_zfs|zfs_)' | head -50` on pve3 first
  - [ ] `promtool check rules` validates the file
  - [ ] Reload Prometheus via SIGHUP; verify the recorded metrics appear in `/api/v1/rules`

- [ ] **Task 4: Extend `pve-replication-exporter.sh` with send-stream bytes counter** (AC-2)
  - [ ] **NEEDS OPERATOR CONFIRMATION** — verify whether `pve_replication_send_bytes_total` is already emitted by Story 6.2's exporter; if it is, this sub-task is a no-op and AC-2's recording rule simply uses it. If not, parse `/var/log/pve/replicate/<jobid>` for the per-cycle send-stream byte count and emit as a counter.
  - [ ] If extending the exporter: re-deploy to pve1, pve2, pve3 per Story 6.2's deploy pattern; verify metric appears in Prometheus

- [ ] **Task 5: Build Grafana dashboard panels** (AC-3)
  - [ ] Decide: extend existing `HA Replication` dashboard OR create new `Replication Soak` dashboard — operator preference
  - [ ] Add the four panels (snapshot count, ARC delta, txg p95, send-stream)
  - [ ] Capture day-0 baselines via Prometheus query API; archive to `day-0-baseline.txt`
  - [ ] Commit dashboard JSON

- [ ] **Task 6: Implement daily-summary cron job** (AC-4)
  - [ ] Write `homelab-apps/stacks/observability/scripts/soak-daily-summary.sh` (runs on ct-docker-01) — queries Prometheus + Alertmanager + writes `day-N.md`
  - [ ] Install cron entry: `0 9 * * * developer /opt/homelab-apps/stacks/observability/scripts/soak-daily-summary.sh` (CEST)
  - [ ] Idempotent + ntfy-on-failure (re-running for same day overwrites; Prometheus-unreachable triggers ntfy push)
  - [ ] **NEEDS OPERATOR CONFIRMATION** — confirm the cron job runs as the right user on ct-docker-01 (ct-docker-01 is the observability host; user is likely `developer` or a service account)

- [ ] **Task 7: Soak window — daily monitoring** (AC-4 ongoing)
  - [ ] Day 1-7: operator visits the dashboard once daily, eyeballs the four panels against the threshold annotations
  - [ ] If any threshold trips during soak: do NOT roll back immediately — confirm via PromQL the breach is sustained (≥30 min), check for confounders (e.g. concurrent backup), then escalate
  - [ ] All 7 day-N.md files exist and are not `*-FAILED.md` placeholders

- [ ] **Task 8: Day 4 or day 5 — small-write workload test** (AC-6)
  - [ ] Run `homelab-playbook/_bmad-output/soak-evidence/small-write-test.sh` (see Dev Notes §"Small-write test")
  - [ ] Capture transcript + measured numbers to `day-N-small-write-test.log`
  - [ ] Verify all five AC-6 conditions hold; if not, do NOT continue soak — escalate per AC-8 rollback path

- [ ] **Task 9: Day 7 — verdict + final report** (AC-5, AC-7)
  - [ ] Apply rollback criterion (Dev Notes §"Rollback criterion thresholds") to the 7-day data
  - [ ] Write `day-7-verdict.md` with KEEP or ROLL BACK + rationale
  - [ ] Append `### V3 Soak Results` section to runbook
  - [ ] Update operator-checklist in runbook with final cadence

- [ ] **Task 10: If ROLL BACK — execute revert** (AC-8)
  - [ ] `pvesr update --schedule '*/15'` on both legs
  - [ ] Update runbook "Measured RPO" table back to `*/15` baselines
  - [ ] Write `post-mortem.md` with breach + root cause + follow-up recommendation
  - [ ] If KEEP: skip this task

- [ ] **Task 11: Commit + status flip**
  - [ ] Commit `homelab-infra` changes (zfs-soak-exporter, runbook updates) as one logical unit
  - [ ] Commit `homelab-apps` changes (recording rules, dashboard, daily-summary script) as one logical unit
  - [ ] Commit `_bmad-output/soak-evidence/` as a third unit (`docs(soak-evidence): 7-day */1 soak measurements + day-7 verdict`)
  - [ ] Flip story frontmatter `backlog` → `review`
  - [ ] **NEEDS OPERATOR CONFIRMATION** — sprint-status YAML flip via the sprint-status skill

## Dev Notes

### Rollback criterion thresholds

These thresholds are the explicit definition of "KEEP" vs "ROLL BACK" referenced in AC-5. They are baseline-relative (T_start), not absolute, because absolute thresholds depend on cluster hardware and current workload.

| Metric | KEEP threshold | ROLL BACK trigger |
|---|---|---|
| Snapshot count on `rpool/data/subvol-162-disk-0` | ≤ T_start × 1.10 (sustained) | > T_start × 1.10 sustained for ≥ 30 min |
| ARC hit-ratio delta (vs T_start baseline) | within −5% | < T_start − 5% sustained for ≥ 30 min |
| txg sync p95 | ≤ T_start × 2.0 | > T_start × 2.0 sustained for ≥ 30 min |
| `PVEReplication*` alert fired (false positive count) | 0 | ≥ 1 false-positive firing |

"Sustained for ≥ 30 min" means the breach is observed in the daily summary AND a 30-min PromQL query around the breach window confirms it (filters out transient blips). A single 5-min spike during a `pvesr` prune cycle is NOT a rollback trigger.

ANY single ROLL BACK trigger fires the verdict — thresholds are joined by OR, not AND. The conservative posture is intentional: we are not committing to `*/1` long-term unless every metric stays inside its budget.

### What's in node-exporter today vs. what needs adding

`prometheus-node-exporter` (Debian package, installed on pve1/pve2/pve3 by Story 6.2) ships a ZFS collector that emits `node_zfs_*` metrics. **NEEDS OPERATOR CONFIRMATION** of exact metric names before authoring recording rules. Likely candidates from upstream node-exporter:

- ARC hit/miss: `node_zfs_arcstats_hits`, `node_zfs_arcstats_misses` (cumulative counters)
- txg sync time: `node_zfs_txg_sync_time_ms` or similar — exact name version-dependent
- Pool I/O: `node_zfs_zpool_iostat_*`

What's NOT in node-exporter and needs adding via textfile collector:

- **Snapshot count per dataset** — node-exporter does not enumerate snapshots. The new `zfs-soak-exporter.sh` script handles this via `zfs list -t snapshot -H -o name | grep "^rpool/data/subvol-162-disk-0@" | wc -l`.
- **Per-replication-job send-stream bytes** — node-exporter has nothing for this. Either extend Story 6.2's `pve-replication-exporter.sh` (preferred, AC-2 path) or parse `/var/log/pve/replicate/<jobid>` standalone.

### Recording rules syntax (template)

```yaml
# homelab-apps/stacks/observability/config/recording/replication-soak.yml
groups:
  - name: replication-soak.recording
    interval: 30s
    rules:
      - record: pve_zfs_arc_hit_ratio_5m
        expr: |
          rate(node_zfs_arcstats_hits[5m])
            / (rate(node_zfs_arcstats_hits[5m]) + rate(node_zfs_arcstats_misses[5m]))
      - record: pve_zfs_txg_sync_p95_5m
        expr: |
          quantile_over_time(0.95, node_zfs_txg_sync_time_ms[5m])
      # send-stream is a counter from pve-replication-exporter; rate() at panel-time, not recording rule
```

Adjust metric names per the AC-2 verification step.

### ZFS textfile collector path

Per Story 6.2 Completion Note 2: Debian's `prometheus-node-exporter` uses `/var/lib/prometheus/node-exporter/` as the textfile collector directory (NOT `/var/lib/node_exporter/textfile_collector/`). The new `zfs-soak-exporter.sh` writes to `/var/lib/prometheus/node-exporter/zfs_soak.prom` to match the existing convention.

### Small-write test

```bash
# small-write-test.sh — run inside ct:162 on day 4 or day 5
# Simulates 100 small DB transactions/min for 30 min
# Total: 3000 writes × 4 KB = ~12 MB across 30 min (real workload pattern, not bulk)

DURATION_MIN=30
TX_PER_MIN=100
LOG=/var/log/v3-soak-small-write.log

for minute in $(seq 1 $DURATION_MIN); do
  for tx in $(seq 1 $TX_PER_MIN); do
    # Simulate a small DB transaction: 4 KB write + fsync
    dd if=/dev/urandom of=/var/lib/v3-soak-tx.$$.$tx bs=4K count=1 conv=fsync 2>>"$LOG"
    rm -f /var/lib/v3-soak-tx.$$.$tx
  done
  sleep 60
done

echo "small-write test done at $(date -u +%FT%TZ)" >> "$LOG"
```

The `conv=fsync` forces a synchronous write per transaction — this is the path that exercises ZFS's small-write txg flush behaviour. Bulk `dd` (Story 6.5 AC-3) does not.

### Why 7 days (not 30, not 90)

7 days captures all weekly cron-driven artefacts (weekly ZFS scrub from Story 7.6, weekly PBS verify, weekly apt updates) plus weekday-vs-weekend workload variation. 30/60/90 days would catch slower trends (e.g. a +0.5%/day snapshot-count creep that 7 days misses) but stakes the epic on a 1-3 month commitment. Pragmatic posture: 7 days as the gate; if KEEP verdict, file a follow-up note for a passive 30-day "no alerts fired" check that happens automatically (no operator effort) via existing 6.10 alerting.

### What "healthy" looks like post-soak (KEEP path)

- Snapshot count grew predictably during business hours (write spikes), pruned overnight, day-over-day delta near zero
- ARC hit-ratio stayed within ±2% of T_start (5% threshold not approached)
- txg sync p95 stayed within ±20% of T_start (2× threshold not approached)
- Zero `PVEReplication*` alerts; the alert noise floor is the 4 unrelated ServiceDown alerts already documented in Story 6.5 AC-7 evidence
- Small-write test on day 4-5 passed all five AC-6 conditions

### What "needs rollback" looks like (ROLL BACK path)

Most likely failure modes (in order of probability per the SM's read of the cluster):
1. Snapshot count climbs because `pvesr` prune is failing silently — surfaced by the snapshot-count panel breaching +10% within 24h
2. txg sync p95 climbs under sustained metadata churn — surfaced by the txg panel
3. ARC drops because metadata working-set exceeds ARC budget — surfaced by ARC delta panel
4. False-positive `PVEReplicationStale` firing because cycle Duration occasionally exceeds threshold — surfaced by alert log

### File layout

Files to create:
- `homelab-infra/proxmox/replication/zfs-soak-exporter.sh` (new, ~50 lines)
- `homelab-apps/stacks/observability/config/recording/replication-soak.yml` (new, ~30 lines)
- `homelab-apps/stacks/observability/scripts/soak-daily-summary.sh` (new, ~80 lines)
- `_bmad-output/soak-evidence/day-N.md` × 7 (cron-generated)
- `_bmad-output/soak-evidence/day-7-verdict.md`
- `_bmad-output/soak-evidence/small-write-test.sh`
- `_bmad-output/soak-evidence/day-N-small-write-test.log`
- `_bmad-output/soak-evidence/day-0-preflight.txt`
- `_bmad-output/soak-evidence/day-0-baseline.txt`
- `_bmad-output/soak-evidence/post-mortem.md` (only if ROLL BACK)

Files to modify:
- `homelab-infra/proxmox/replication/pve-replication-exporter.sh` (only if AC-2 send-bytes counter needs adding — pending operator confirmation)
- `homelab-apps/stacks/observability/dashboards/ha-replication.json` OR new `replication-soak.json`
- `homelab-infra/docs/ha-replication-runbook.md` — append `### V3 Soak Results` section + update Measured RPO table if ROLL BACK
- `/etc/cron.d/zfs-soak-exporter` on pve3 (deployed, not committed — operator-managed live state per Story 6.2 pattern)
- `/etc/cron.d/soak-daily-summary` on ct-docker-01 (deployed, not committed)

### Prior art references

- **Story 6.2** (`6-2-verify-replication-state-and-deltas.md`) — established the textfile-collector + Debian-node-exporter pattern; provides the `flock`/`timeout`/atomic-write hardening template; established the 5-min cron cadence
- **Story 6.5** (`6-5-validation-drill-v3-replication-rpo-for-ct162.md`) — the 16-min sample this story extends to 7 days; the cadence-tightening + KEEP decision being soak-validated
- **Story 6.10** (`6-10-ha-state-prometheus-exporter.md`) + 6.10.1 (alert tuning post-soak) — concurrent-running tuning of the HA alert chain over the same calendar window; this story does NOT depend on 6.10.1 but they share the same calendar
- **Story 7.6** (`7-6-enable-weekly-zfs-scrub-automation.md`) — weekly ZFS scrub the 7-day soak will see at least once; expected to NOT trigger any soak threshold

## Test strategy

**Phase 1 (Tasks 1-6):** instrumentation. Recording rules + dashboard + daily summary cron — additive only, no cluster mutation. Outcome: telemetry pipeline producing day-N.md files reliably.

**Phase 2 (Task 7):** passive 7-day soak. Operator effort is "look at dashboard once daily, escalate if anomaly". No cluster mutation in this phase. Outcome: 7 day-N.md files + dashboard history.

**Phase 3 (Task 8):** active small-write test on day 4-5. Bounded 30-min workload-generating test inside ct:162 — minimal cluster impact (~12 MB written, all cleaned up). Outcome: small-write path validation.

**Phase 4 (Task 9):** verdict + runbook update. Documentation only.

**Phase 5 (Task 10):** rollback (only if Verdict ROLL BACK). Two `pvesr update` commands to revert cadence; runbook updates; post-mortem capture. Outcome: cluster back to `*/15` baseline.

**Evidence that the story passed:**

- Recording rules + textfile collector emit all four soak metrics for ≥7 days
- Grafana dashboard has the four panels with threshold annotations
- 7 day-N.md files exist (none `-FAILED`)
- Day-4-or-5 small-write test log shows all five AC-6 conditions met
- `day-7-verdict.md` records KEEP or ROLL BACK with rationale
- Runbook §"V3 Soak Results" section is present with measured numbers
- (If ROLL BACK) Cadence reverted to `*/15` and post-mortem captured

## Security considerations

- `zfs-soak-exporter.sh` runs as root on pve3 — invokes `zfs list` (read-only) and writes to `/var/lib/prometheus/node-exporter/`. No new credentials, no network exposure beyond node-exporter's existing `:9100`.
- `soak-daily-summary.sh` runs on ct-docker-01 as a non-root user — invokes `curl` against Prometheus + Alertmanager (already-trusted internal endpoints) and writes to `_bmad-output/soak-evidence/`. No secrets handled.
- Small-write test runs inside ct:162 — generates `/dev/urandom` writes to `/var/lib/v3-soak-tx.*` and cleans up. No persistent change to ct:162 state.
- Soak evidence files contain operational metadata (snapshot counts, RPO numbers) — not credential material. Safe to commit.

## Rollback procedure

**The soak itself is non-mutating** — only Task 10 (cadence revert, conditional on Verdict ROLL BACK) changes cluster state. If the soak instrumentation needs to be backed out:

```bash
# Remove daily-summary cron + script
ssh ct-docker-01 "rm -f /etc/cron.d/soak-daily-summary /opt/homelab-apps/stacks/observability/scripts/soak-daily-summary.sh"

# Remove zfs-soak-exporter cron + script on pve3
ssh pve3 "rm -f /etc/cron.d/zfs-soak-exporter /usr/local/bin/zfs-soak-exporter.sh /var/lib/prometheus/node-exporter/zfs_soak.prom"

# Remove recording rules + dashboard
# (git revert the homelab-apps commits; reload Prometheus via SIGHUP)
```

**Cadence rollback (AC-8) is straightforward**:

```bash
ssh pve3 "pvesr update 162-0 --schedule '*/15'"
ssh pve3 "pvesr update 162-1 --schedule '*/15'"
# Verify within 2 cycles via pvesr status
```

No other state changes. Replication state machine is unaffected (existing `__replicate_*` snapshots remain valid; the next `*/15` cycle picks up where the previous `*/1` cycle left off).

## References

- **Parent story**: `homelab-playbook/_bmad-output/implementation-artifacts/6-5-validation-drill-v3-replication-rpo-for-ct162.md` — Source of the rollback criterion and the KEEP decision being soak-validated
- **Cousin story (sequential)**: `6-5-1-rpo-aliasing-disambiguation.md` — must complete before this soak starts so the 1s falsification result feeds AC-1 expectations
- **Cousin story (concurrent)**: `6-10-1-ha-alert-tuning-post-soak.md` — runs over the same calendar; tunes 6.10 alerts post-soak data; does NOT block this story
- **Sibling story (instrumentation parent)**: `6-2-verify-replication-state-and-deltas.md` — provides the exporter hardening pattern (`flock`/`timeout`/atomic-write) used here
- **Runbook**: `homelab-infra/docs/ha-replication-runbook.md §"V3 Drill Results"` and §"Measured RPO"
- **Workload context**: OMEGA memory `project_quant_trading` — small-write profile of the actual workload, RPO sensitivity rationale
- **Related infra story**: `7-6-enable-weekly-zfs-scrub-automation.md` — the 7-day soak window will see one weekly scrub; expected to NOT breach any soak threshold (informational reference)
- **Prometheus node-exporter ZFS collector docs**: <https://github.com/prometheus/node_exporter#zfs>
- **Prometheus recording rules docs**: <https://prometheus.io/docs/prometheus/latest/configuration/recording_rules/>
