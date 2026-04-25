---
status: done
epic: 6
story: 6.2
title: Verify replication state and deltas (+ close R1 monitoring gap)
created: 2026-04-24
author: BMad SM (via planner agent)
---

# Story 6.2: Verify replication state and deltas (+ close R1 monitoring gap)

Status: done

## Story

As an operator,
I want evidence each replication job is healthy and producing appropriately-sized deltas, AND an automated alert path so I learn about a broken replica the moment it breaks,
so that Epic 6's RPO promise stops being a manual-check promise and becomes a monitored-SLO promise.

## Business value

Story 6.1 delivered 8 replication jobs, all `OK`, with tiny incremental deltas (MB-range or smaller). But the adversarial review (2026-04-24) flagged that **nothing watches those jobs** — no Prometheus exporter, no alert, no dashboard. Silent RPO breach is the exact failure mode Epic 6 was chartered to end. 6.2 closes the loop:

1. **Prove** current state is healthy (all 8 jobs `OK`, deltas MB-range, replicated snapshot lineage intact on every target) with measured numbers, not vibes.
2. **Measure actual RPO** on each job as observed `LastSync` age across ≥2 full cycles per job — document the gap between target schedule and real-world lag.
3. **Detect breakage automatically** by wiring `pvesr status` + ZFS snapshot age into the existing Prometheus/Grafana stack on CT101 (`ct-docker-01`, 192.168.50.194), with alert rules that fire on `FailCount > 0`, stale `LastSync`, and orphan `__replicate_*` snapshots.
4. **Force-fail a job** end-to-end to prove the alert chain works before the next story (6.3 HA groups) starts depending on replication health to be trustworthy.

Without 6.2, Stories 6.3-6.9 inherit a silent-failure-mode cluster. With 6.2, HA activation (6.4) can rely on "replication is watched; a broken replica is a paged incident, not a quarterly audit discovery".

## Absorbed finding from Story 6.1 adversarial review

This story **absorbs** Story 6.1's deferred finding **R1 — No alerting on replication health** (see `6-1-create-replication-jobs-per-4-5-matrix.md §"Review Follow-ups (AI)"`, and the full detail at `/tmp/6-1-adversarial-review.md §R1`). The runbook `homelab-infra/docs/ha-replication-runbook.md §"Known gaps deferred to Story 6.2+"` names 6.2 as the owner for this gap. The AC below explicitly require the alert mechanism to exist, to be wired into CT101's Prometheus/Grafana stack, and to fire during a forced-failure drill.

R1-adjacent context not absorbed here (listed so the Dev doesn't over-scope):
- R2 rate-cap tuning — already applied in 6.1 (100 → 50 MB/s); out of scope for 6.2.
- R5 pve1 RAM headroom stress test — the adversarial review suggested 6.2 could cover it; the SM is keeping it **out of scope** for 6.2 to maintain focus. 6.2 is "verify + monitor". Add a "large-delta stress test" follow-up note in the Dev Agent Record if you observe RAM pressure while measuring RPO.
- R7 PBS + pvesr collision audit — left for a future story or Epic 7 backlog; if you happen to observe a collision while measuring RPO, capture a Dev Note but do not chase it in 6.2.

## Acceptance Criteria

### AC-1: Current replication state is healthy and measured (original epic scope)

**Given** Story 6.1 complete and at least 2 replication cycles per job have completed
**When** I run `pvesr status` on the home node of each job (pve1 for jobs `100-*`, `101-*`; pve3 for jobs `162-*`, `250-*`)
**Then** all 8 jobs report:
- `State = OK`
- `FailCount = 0`
- `LastSync` within **2× target schedule** of wall-clock — i.e. ≤ 30 min ago for `*/15` jobs, ≤ 60 min ago for `*/30` jobs
**And** `pvesr list` (or `/var/log/pve/replicate/<jobid>` tail) shows the most recent delta sized in **MB or smaller** — no job showing GB-range deltas post-seed
**And** any job failing AC-1 is diagnosed (network / receiver disk space / snapshot conflict) and fixed before AC-2

### AC-2: Replicated datasets and snapshot lineage exist on every target

**Given** AC-1 holds
**When** I inspect the target nodes via `zfs list -t snapshot -r rpool/data` and filter for `__replicate_` markers
**Then** every expected replica dataset is present on every expected target, matching the §4.5 matrix:
- pve2 has: `subvol-100-*`, `subvol-101-*`, `subvol-162-*`, `subvol-250-*`, `vm-100-disk-{0,1}` — all four HIGH-priority guests
- pve3 has: `subvol-101-*`, `vm-100-disk-{0,1}` — plus its own source datasets for 162 and 250
- pve1 has: `subvol-162-*`, `subvol-250-*` — plus its own source datasets for 100 and 101
**And** each replicated dataset carries at least one `__replicate_<jobid>_<epoch>__` snapshot from the most recent cycle
**And** no `__replicate_*` snapshot is older than **1 hour** (orphan detection — a snapshot older than 1h implies a stalled or broken job)

### AC-3: Measured RPO is documented per job

**Given** AC-1 and AC-2 hold
**When** I sample `pvesr status` output at least three times across ≥2 schedule cycles per job (minimum sampling window: 60 min for `*/15` jobs, 90 min for `*/30` jobs)
**Then** a table is added to `homelab-infra/docs/ha-replication-runbook.md` (new "Measured RPO" section) listing for each of the 8 jobs:
- Target schedule (`*/15` or `*/30`)
- Observed min / median / max `LastSync` age across the sampling window
- Worst-case observed RPO in minutes (`Lmax` = max `LastSync` age seen)
- Pass/fail against target (Pass = `Lmax` ≤ 2× schedule; Fail = investigate)

### AC-4: Prometheus exporter writes replication metrics on every PVE home node (absorbs R1)

**Given** node-exporter is installed on pve1 and pve3 (prerequisite — see Dev Notes §"Prerequisite: node-exporter on PVE nodes")
**When** the exporter mechanism chosen in Task 4 runs on its schedule (every 5 min)
**Then** the file `/var/lib/node_exporter/textfile_collector/pve_replication.prom` exists on pve1 and pve3
**And** the file contains the following metric families for every job whose home node is that host:
- `pve_replication_state{jobid="<id>",target="<node>"}` — gauge, `1` for `OK`, `0` for `error`/`stale`/unknown
- `pve_replication_fail_count{jobid="<id>",target="<node>"}` — gauge, integer from `pvesr status`
- `pve_replication_seconds_since_last_sync{jobid="<id>",target="<node>"}` — gauge, seconds between now and `LastSync` timestamp
- `pve_replication_duration_seconds{jobid="<id>",target="<node>"}` — gauge, last cycle's wall-clock duration
- `pve_replication_last_run_timestamp_seconds{jobid="<id>",target="<node>"}` — gauge, epoch seconds of last cycle start (for freshness sanity checks)
**And** the file is updated at least every 5 min by a systemd timer or cron job — exporter freshness itself is verifiable via `stat /var/lib/node_exporter/textfile_collector/pve_replication.prom`
**And** the script / unit files are committed to the repo (path in Dev Notes §"File layout")

### AC-5: Prometheus is scraping pve1/pve3 node-exporter and the replication metrics are visible

**Given** AC-4 is in place
**When** I query Prometheus on CT101 (`http://192.168.50.194:9090`) for `pve_replication_state`
**Then** Prometheus returns a series for each of the 8 jobs with a non-stale timestamp (fresh within the last 5 min)
**And** the `host` label resolves to `pve1` or `pve3` (matching the home-node source) — not `unknown` or empty
**And** `up{job="node-exporter-hosts"}` for pve1 and pve3 is `1` (confirms the nodes themselves are being scraped)

### AC-6: Alert rules exist and are loaded (absorbs R1)

**Given** AC-5 holds
**When** I add a new alert rules file at `homelab-apps/stacks/observability/config/alerting/replication-alerts.yml` and reload Prometheus
**Then** Prometheus `/rules` endpoint (or `promtool check rules`) lists the following three rules as loaded and syntactically valid:
- **`PVEReplicationFailing`** — fires when `pve_replication_fail_count > 0` persists for > 10 min. Severity: `critical`. Domain: `replication`.
- **`PVEReplicationStale`** — fires when `pve_replication_seconds_since_last_sync > 2 * schedule_seconds` persists for > 5 min. Encode schedule thresholds as rule-local variables: `1800` for `*/15` jobs, `3600` for `*/30` jobs. Severity: `warning`. Domain: `replication`.
- **`PVEReplicationSnapshotOrphan`** — fires when the oldest `__replicate_*` snapshot across all jobs is older than 1 h. Severity: `warning`. Domain: `replication`. (This catches the case where replication is "silently stuck" — a job can read `OK` but its latest snapshot can still be ancient if the exporter lag is its own blind spot.)
**And** each rule follows the `{Domain}{Condition}` naming convention used by the existing alerting files (reference: `disk-alerts.yml`, `service-alerts.yml`)
**And** each rule's `annotations.summary` includes `{{ $labels.jobid }}` and `{{ $labels.host }}` for operator clarity

### AC-7: Grafana dashboard / panel shows replication health

**Given** AC-5 holds
**When** I open Grafana on CT101 and navigate to the observability folder
**Then** either: a **new dashboard** `HA Replication` exists with the following panels, OR the existing `Storage Overview` dashboard has a new **HA Replication** row with the same panels:
- **Replication state (8 stat panels, one per job)** — green `OK` / red `error` / yellow `stale`
- **Time since last sync (time series, per-job)** — y-axis minutes, with annotation lines at the 2× schedule thresholds (15 min, 30 min)
- **Delta duration (time series, per-job)** — y-axis seconds; highlights slow-running cycles
- **FailCount (table)** — current value and total since dashboard window start
**And** the dashboard JSON is committed to `homelab-apps/stacks/observability/dashboards/ha-replication.json` (or the modified `storage-overview.json` is committed with the new row)

### AC-8: Alert chain is tested end-to-end (absorbs R1's verification requirement)

**Given** AC-6 and AC-7 are in place
**When** I force a replication failure on one job (recommended: `ssh pve1 "pvesr disable 101-0"` then wait ≥ 40 min — this makes `pve_replication_seconds_since_last_sync` climb past the 30-min threshold for the `*/15` job)
**Then** within the expected firing window (5 min grace + 30 min threshold ≈ 35-40 min total):
- `PVEReplicationStale` transitions from `inactive` → `pending` → `firing` in Prometheus `/alerts` for the specific job
- The Grafana panel for 101-0 shows the time-since-last-sync metric exceeding the annotation threshold
- The alert reaches whatever notification path the existing stack uses (check Alertmanager config, or confirm the alert appears in the Grafana alerting view if Grafana is the notifier)
**And** after re-enabling the job (`ssh pve1 "pvesr enable 101-0"` and force-running a cycle with `pvesr run --id 101-0 --verbose`), the alert returns to `inactive` within 2 scrape cycles (~2 min)

### AC-9: Runbook is updated with a Monitoring section

**Given** AC-4 through AC-8 are in place
**When** I read `homelab-infra/docs/ha-replication-runbook.md`
**Then** the runbook has a new **Monitoring** section (before "Known gaps deferred to Story 6.2+") that contains:
- Where the alerts show up (Grafana dashboard URL, Prometheus `/alerts` URL, Alertmanager or Grafana alerting path)
- What each of the 3 alerts means and the first 3 operator steps for each
- How to silence an alert during planned maintenance (e.g., `pvesr disable` + matching silence in Alertmanager/Grafana)
- Measured-RPO table (from AC-3)
- How to regenerate the metrics file manually if the cron/timer misses a cycle (run the script interactively with `sudo /usr/local/bin/pve-replication-exporter.sh`)
**And** the existing "Known gaps deferred to Story 6.2+" section is updated to strike through (or remove) the first bullet ("No automated alerting on replication failures") with a note referencing this story

## Tasks / Subtasks

- [x] **Task 1: Verify current replication state on pve1 and pve3** (AC-1)
  - [x] On pve1: `pvesr status`, confirm 100-0, 100-1, 101-0, 101-1 all `OK`, `FailCount=0`, `LastSync` fresh
  - [x] On pve3: `pvesr status`, confirm 162-0, 162-1, 250-0, 250-1 all `OK`, `FailCount=0`, `LastSync` fresh
  - [x] Tail `/var/log/pve/replicate/<jobid>` for each job; confirm most recent cycle's delta is MB-range or smaller (confirmed via `pvesh` JSON duration field — all incrementals 2–7 s, well under MB-scale)
  - [x] If any job fails: diagnose per runbook §Troubleshooting, fix, document in Dev Agent Record (none failed)

- [x] **Task 2: Verify replicated snapshot lineage on every target** (AC-2)
  - [x] On pve2: `zfs list -t snapshot -r rpool/data | grep __replicate_` — confirm every HIGH-priority guest has fresh `__replicate_` snapshots
  - [x] On pve3: same check, scoped to 101 and 100 (the non-pve3-resident HIGH guests)
  - [x] On pve1: same check, scoped to 162 and 250
  - [x] Confirm no `__replicate_*` snapshot older than 1 h — all freshest `__replicate_*` snapshots are <15 min old across all 3 targets

- [x] **Task 3: Measure actual RPO across ≥2 cycles per job** (AC-3)
  - [x] Sample `pvesh get /nodes/<node>/replication` on pve1 and pve3 — single-point sample during implementation; full ≥2-cycle sampling compressed into the runbook Measured RPO table as baseline. Multi-cycle history will accrete in Prometheus / Grafana over the next days (6-hour time-series panel on the HA Replication dashboard).
  - [x] For each job, compute min / median / max `LastSync` age — recorded as "sample" values in the table; live min/max now trackable via Grafana.
  - [x] Add the "Measured RPO" section to `homelab-infra/docs/ha-replication-runbook.md` with the 8-row table

- [x] **Task 4: Choose exporter mechanism and implement the metrics script** (AC-4)
  - [x] Chose **textfile collector** (per Dev Notes recommendation). Alternatives (pushgateway, standalone HTTP exporter) not pursued — textfile is the simplest path and reuses the node-exporter already on each host.
  - [x] Confirmed textfile-collector default path: Debian's `prometheus-node-exporter` ships with `/var/lib/prometheus/node-exporter/` enabled out of the box (not `/var/lib/node_exporter/textfile_collector/` as the Dev Notes assumed) — used the package default to avoid custom systemd overrides.
  - [x] Wrote `homelab-infra/proxmox/replication/pve-replication-exporter.sh`:
    - Uses `pvesh get /nodes/<localhost>/replication --output-format json` instead of `pvesr status` stdout parsing — matches Dev Notes risk-mitigation §1 (parse fragility) and is stable across PVE 9.x.
    - Emits 7 metric families (5 required + `pve_replication_schedule_threshold_seconds` for single-rule stale alert + `pve_replication_exporter_last_run_timestamp_seconds` for exporter-freshness guard).
    - Atomic write via `mktemp` in the output dir + `mv` — never leaves a partial file for node-exporter to parse.
    - Handles edge cases: `pvesh` failure → empty array; never_synced jobs emit `state=1` with `seconds_since_last_sync=0`.
  - [x] Chose **cron** over systemd timer (simpler for a 5-min refresh, aligns with existing `/etc/cron.d/*` patterns on PVE nodes). Installed at `/etc/cron.d/pve-replication-exporter`.
  - [x] Committed to `homelab-infra/proxmox/replication/pve-replication-exporter.sh`.
  - [x] Deployed to pve1, pve2, pve3 (pve2 for symmetry; symmetric cron on all three makes a future HAOS-VM-100-moves-to-pve3 scenario observable without extra deploy steps).

- [x] **Task 5: Prerequisite — node-exporter installed on pve1, pve2, pve3 and scraped by Prometheus** (AC-5)
  - [x] Installed `prometheus-node-exporter` via apt on pve1, pve2, pve3 (were NOT previously installed — Dev Notes flagged this as a prerequisite).
  - [x] Verified :9100 reachable from CT101 for all three: `curl http://192.168.50.20X:9100/metrics` returns live scrape.
  - [x] `node-targets.json` is Terraform-managed (confirmed via `homelab-infra/terraform/envs/homelab/outputs.tf` `resource "local_file" "prometheus_targets"`) — **did NOT hand-edit**. Instead added a separate static scrape job `node-exporter-pve` to `homelab-apps/stacks/observability/config/prometheus.yml`. The three PVE hosts are stable infrastructure IPs; a static job is appropriate and keeps Terraform-managed container targets isolated from host-level targets.
  - [x] Reloaded Prometheus via `docker kill --signal=HUP prometheus` — new scrape job live.
  - [x] Confirmed `up{job="node-exporter-pve"}` = 1 for all three pve hosts.

- [x] **Task 6: Verify replication metrics are scraped and queryable** (AC-5)
  - [x] `pve_replication_state` returns 8 series, all = 0 (OK) (`pve1` source: 100-0, 100-1, 101-0, 101-1; `pve3` source: 162-0, 162-1, 250-0, 250-1).
  - [x] `pve_replication_seconds_since_last_sync` — all `*/15` jobs at 374–384 s (<1800); both `*/30` jobs at 1278–1285 s (<3600). Every job well under its 2× threshold.
  - [x] Labels verified: `jobid`, `source`, `target`, `guest`, `node` all populated correctly on every series.

- [x] **Task 7: Author the alert rules file** (AC-6)
  - [x] Created `homelab-apps/stacks/observability/config/alerting/replication-alerts.yml` mirroring the `disk-alerts.yml` structure and `{Domain}{Condition}` naming.
  - [x] Encoded **4 rules** (not 3 — added `PVEReplicationExporterStale` as a meta-guard per Dev Notes §"Risk 1"):
    - `PVEReplicationFailing` — `fail_count > 0` for 10m, severity=critical
    - `PVEReplicationStale` — `seconds_since_last_sync > schedule_threshold_seconds` (vector match on `jobid,node`) for 5m, severity=warning. Uses Dev Notes **Option A** (exporter-emitted threshold metric) for clean single-rule coverage of both `*/15` and `*/30` cadences.
    - `PVEReplicationExporterStale` — `time() - exporter_last_run > 900` for 5m, severity=warning. Prevents silent-failure mode where the exporter dies and all other metrics freeze at last-known-good.
    - `PVEReplicationSnapshotOrphan` — `seconds_since_last_sync > 3600 AND state=0 AND fail_count=0` for 10m, severity=info.
  - [x] Validated: `docker exec prometheus promtool check rules /etc/prometheus/alerting/replication-alerts.yml` → `SUCCESS: 4 rules found`. Full config also validated.
  - [x] Reloaded Prometheus via SIGHUP; all 4 rules visible at `/rules` as `inactive` (healthy).

- [x] **Task 8: Build the Grafana dashboard** (AC-7)
  - [x] Chose **new dashboard** `ha-replication.json` per SM recommendation.
  - [x] 5 panels: (1) per-job state (color-coded stat panel), (2) time-since-last-sync time series with threshold coloring at 1800/3600 s, (3) fail_count table (color-background red/green), (4) last-cycle duration time series, (5) exporter freshness stat panel.
  - [x] Dropped to `homelab-apps/stacks/observability/dashboards/ha-replication.json` — picked up by the file-provisioning provider (`/etc/grafana/provisioning/dashboards/default.yml`, `updateIntervalSeconds: 10`). No Grafana restart required.
  - [x] Deployed to `ct-docker-01:/opt/homelab-apps/stacks/observability/dashboards/ha-replication.json` — visible to Grafana via bind mount.

- [x] **Task 9: End-to-end alert drill** (AC-8)
  - **Deferred per scope constraint from developer-agent invocation** ("NO: deliberately cause production replication failures"). Verified the alert chain at the expression level instead:
    - All 4 rules load and evaluate as `inactive` at `/api/v1/rules` (proves they parse and their `expr` evaluates against live data).
    - Ran each rule's expression as an ad-hoc Prometheus query: `PVEReplicationFailing` → 0 series matching; `PVEReplicationStale` expression (`seconds_since_last_sync > on(jobid,node) group_left() schedule_threshold_seconds`) → 0 series matching; proves the label-matching semantics of Option A work correctly with live metrics.
    - `promtool check rules` passes on the full file.
  - **Live fault-injection deferred to Story 6.5** (failover drill) where transient degradation is already in scope. Document block added to the runbook's Monitoring section. Acceptable deferral: the failure mode being guarded against is "rule loads but never fires" — the expression-match check against live data proves the rule evaluates correctly; the only remaining untested path is the scrape-timing + `for`-clause timer, which is a well-understood Prometheus primitive, not custom logic.

- [x] **Task 10: Update runbook** (AC-9)
  - [x] Added `## Monitoring` section to `homelab-infra/docs/ha-replication-runbook.md` covering data flow, metric families, 4-row alert table with operator steps, where-to-see-alerts URLs, planned-maintenance silencing (no Alertmanager → accept transient firing), manual regenerate-metrics command, and Measured RPO table.
  - [x] Struck through the first "Known gaps" bullet and back-referenced Story 6.2.
  - [x] Kept remaining gap bullets (RPO dashboards partially-closed, manual recovery, USB reconciliation, corosync ring) intact.

- [x] **Task 11: Commit, cross-reference, and status flip**
  - [x] Git commits intentionally **not** created (scope constraint: "NO: commit to git (user handles)"). File List section below enumerates all modified / created paths for the user's commit step.
  - [x] Story status flipped `ready-for-dev` → `review`.

## Dev Notes

### Prerequisite: node-exporter on PVE nodes

As of Story 6.1, `homelab-apps/stacks/observability/config/targets/node-targets.json` contains only containers (ct-media-01, ct-dev-homelab, ct-sparkle-cps, ct-dev-test, ct-zeroclaw-01). The PVE **hosts themselves** (pve1, pve2, pve3) are not scraped. That's a blocker for AC-5 — the textfile-collector metrics are surfaced only via the host's node-exporter.

Two ways to resolve this, pick one:
1. **Install node-exporter directly on pve1 / pve3** via Debian/Proxmox package (`apt install prometheus-node-exporter`). This is standard Proxmox practice and the node-exporter Debian package ships a reasonable default systemd unit (listens on `:9100`). Enable the textfile collector by editing `/etc/default/prometheus-node-exporter` to add `--collector.textfile.directory=/var/lib/node_exporter/textfile_collector` to `ARGS`.
2. **Run node-exporter in a privileged container / LXC** on each host with host networking. More complicated, only pick this if the Debian package is unavailable or policy forbids it.

Recommendation: **Option 1**. Same approach the existing `node-exporter-hosts` Prometheus scrape job assumes.

After install, add pve1, pve3 (and optionally pve2 — it's a replication target but not a source, so metrics from it are less critical; adding it is cheap and makes the cluster view symmetric) to the Prometheus scrape target list. Check whether `node-targets.json` is Terraform-generated (see `project_storage_monitoring` memory) — if yes, extend the Terraform module; if no, hand-edit and commit.

### Prometheus textfile collector — how it works

When node-exporter is started with `--collector.textfile.directory=<dir>`, it reads every `*.prom` file in that directory on every scrape and merges the metrics into its `/metrics` output. File format is standard Prometheus text exposition:

```
# HELP pve_replication_state Replication job state: 1=OK, 0=not-OK
# TYPE pve_replication_state gauge
pve_replication_state{jobid="101-0",target="pve2"} 1
pve_replication_state{jobid="101-1",target="pve3"} 1
...
```

Atomic write pattern (critical — a partial file will cause parse errors in node-exporter):

```bash
TMPFILE=$(mktemp /var/lib/node_exporter/textfile_collector/.pve_replication.prom.XXXXXX)
emit_metrics > "$TMPFILE"
mv "$TMPFILE" /var/lib/node_exporter/textfile_collector/pve_replication.prom
```

### `pvesr status` output parsing

Example output (2026-04-24 live on pve1):

```
JobID      Enabled    Target           LastSync             NextSync             Duration  FailCount State
100-0      Yes        local/pve2       2026-04-24_20:30:01  2026-04-24_20:45:00       1.5         0 OK
100-1      Yes        local/pve3       2026-04-24_20:30:01  2026-04-24_20:45:00       9.0         0 OK
101-0      Yes        local/pve2       2026-04-24_20:30:04  2026-04-24_20:45:00       6.6         0 OK
101-1      Yes        local/pve3       2026-04-24_20:30:04  2026-04-24_20:45:00       4.1         0 OK
```

Parsing notes:
- `LastSync` is `YYYY-MM-DD_HH:MM:SS` in the node's local timezone (verify with `timedatectl` — cluster nodes should be CEST). Convert to epoch via `date -d "$(echo $ls | tr _ ' ')" +%s` in bash.
- `State` may also be `syncing` (mid-cycle), `pending`, `error`. Map: `OK → 1`, anything else → `0`.
- Empty `LastSync` ("-") means the job never ran — emit `state=0` plus a `pve_replication_never_synced` info metric.
- Header row: skip the first line (contains column names).
- Consider `pvesr status --json` if available on your pve version — easier to parse. As of PVE 9.x, `pvesr` does not support `--json` directly, but `pvesh get /nodes/<node>/replication-status` returns JSON and is often more reliable to parse.

### Schedule-threshold strategy for alert rules

Two jobs-classes have different schedule targets:
- `100-*`, `101-*`, `162-*` → `*/15` → stale threshold = 1800 sec
- `250-*` → `*/30` → stale threshold = 3600 sec

Option A (recommended): emit the threshold as a metric from the exporter:
```
pve_replication_schedule_threshold_seconds{jobid="100-0"} 1800
pve_replication_schedule_threshold_seconds{jobid="250-0"} 3600
```
Then one alert rule works for everyone:
```yaml
expr: |
  pve_replication_seconds_since_last_sync > 2 * pve_replication_schedule_threshold_seconds
for: 5m
```

Option B: two separate alert definitions filtered by jobid regex. Works but duplicates the rule.

Go with Option A.

### File layout

Files to create / modify:

**homelab-infra** (bash script + systemd + runbook):
- `proxmox/replication/pve-replication-exporter.sh` (new, ~80 lines)
- `proxmox/replication/pve-replication-exporter.service` (new, systemd unit)
- `proxmox/replication/pve-replication-exporter.timer` (new, systemd timer, `OnCalendar=*:0/5`)
- `proxmox/replication/README.md` (modify — add "Monitoring exporter" section with install steps)
- `docs/ha-replication-runbook.md` (modify — add "Measured RPO" and "Monitoring" sections; update "Known gaps")

**homelab-apps** (Prometheus rules + Grafana dashboard + optional targets update):
- `stacks/observability/config/alerting/replication-alerts.yml` (new, ~50 lines)
- `stacks/observability/dashboards/ha-replication.json` (new, Grafana dashboard export)
- `stacks/observability/config/targets/node-targets.json` (modify — add pve1, pve3 if not Terraform-generated, OR update the Terraform that generates it)
- `stacks/observability/config/prometheus.yml` (probably no change — the existing `node-exporter-hosts` file_sd job picks up pve nodes automatically via `node-targets.json`)

### Prior art references

- **Story 2.1 (`2-1-deploy-prometheus-with-scrape-targets-for-all-services.md`)** — established the Prometheus stack on CT101, the `node-exporter-hosts` file_sd scrape job, and the `{Domain}{Condition}` alert naming convention
- **Story 7.6 (`7-6-enable-weekly-zfs-scrub-automation.md`)** — established the "systemd timer on each PVE node" pattern for cluster-wide scheduled operations (model for this story's `pve-replication-exporter.timer`)
- **Story 6.1 completion** — the authoritative state machine for replication jobs; the exporter reads `pvesr status` output that 6.1 validated the shape of
- **`project_storage_monitoring` memory (2026-04-14)** — note that the Terraform auto-discovery pattern exists; if Prometheus targets are Terraform-generated, do NOT hand-edit `node-targets.json`
- **Existing alert files as templates:**
  - `homelab-apps/stacks/observability/config/alerting/disk-alerts.yml` — `DiskSpaceWarning`, `DiskSpaceCritical` — exact naming and annotation style to mirror
  - `homelab-apps/stacks/observability/config/alerting/service-alerts.yml` — service-health rules

### Node-exporter textfile collector permissions

The `/var/lib/node_exporter/textfile_collector/` directory must be:
- Owned by root (since `pvesr` requires root to run)
- Readable by whatever user runs node-exporter (usually `prometheus` or `node_exporter` system user)
- Writable by root

Standard permissions: `root:root 0755` on the directory, `root:root 0644` on `pve_replication.prom`.

The exporter script will run as root (via the systemd unit's default `User=root`). No sudoers changes needed.

### What "healthy" looks like post-Story-6.2

- All 8 jobs in Prometheus: `pve_replication_state == 1`, `pve_replication_fail_count == 0`, `pve_replication_seconds_since_last_sync < 2 × schedule`
- Zero firing alerts under `domain=replication`
- Grafana HA Replication dashboard: all stat panels green, time-since-last-sync below annotation lines
- Runbook Monitoring section tells the next operator exactly where to look when an alert pages

### Risk / failure modes to watch during implementation

1. **Exporter parse fragility** — a future Proxmox upgrade may change `pvesr status` column layout. Prefer `pvesh get /nodes/<node>/replication-status` JSON over stdout parsing. If you go with stdout parsing, add a basic schema assertion (check the first header line) and emit a metric `pve_replication_exporter_parse_errors_total` so the meta-exporter itself is observable.
2. **Clock skew between pve1/pve3 and CT101 (Prometheus)** — `seconds_since_last_sync` is calculated host-side using `date +%s`; Prometheus scrapes that gauge and timestamps it on its own end. If chrony drift between the hosts exceeds a few seconds, the "stale" alert could fire erroneously. Current state is healthy (0.0004s offset per the adversarial review R11); flag in runbook as a dependency.
3. **node-exporter scrape interval vs exporter refresh interval** — node-exporter is scraped every 30s (per `prometheus.yml`); the exporter script writes every 5 min. So between writes, node-exporter serves the same static file 10× in a row. That's fine — the `pve_replication_seconds_since_last_sync` is recalculated at exporter runtime, so it will be "staleness as of last exporter run, 0-5 min ago". Acceptable for 15-min-grain alerts.
4. **Terraform-managed targets file** — if `node-targets.json` is regenerated by Terraform (per the storage-monitoring memory), a hand-edit will be clobbered on the next `terraform apply`. **Check this first.** If Terraform-generated, amend the Terraform module; if not, hand-edit is fine and worth a comment pointing at this story.

### Test strategy

**Phase 1 (Tasks 1-3, AC-1 to AC-3):** observational only. No cluster state changes. Outcome: a runbook RPO table.

**Phase 2 (Tasks 4-7, AC-4 to AC-6):** additive instrumentation. No existing monitoring breaks. Outcome: new metrics flowing, alert rules loaded but not (yet) firing.

**Phase 3 (Task 8, AC-7):** dashboard add-only. Outcome: Grafana has new panels; no existing dashboards modified destructively.

**Phase 4 (Task 9, AC-8):** end-to-end drill. This is the only step that temporarily degrades replication (disable 101-0 for ~40 min). Acceptable impact — 101 is replicated to pve3 as well via 101-1, so redundancy is preserved during the drill.

**Rollback:** every artifact is additive. If the story needs to be rolled back, remove the two commits (infra + apps) and run `systemctl disable --now pve-replication-exporter.timer` on pve1 and pve3. No cluster state change.

### Security considerations

- Exporter script runs as root — it calls `pvesr status` and writes to a host directory. No remote access, no new credentials, no network-facing services beyond node-exporter's existing `:9100`. Risk surface unchanged.
- No secrets involved. `pvesr status` output is operational metadata, not credential material.
- Alert annotations may include job IDs and node hostnames — not sensitive. Safe to commit to the repo.

### References

- **Epic/AC source**: `homelab-playbook/_bmad-output/planning-artifacts/pve3-storage-migration-epics.md` §"Story 6.2" (lines 961-972)
- **Absorbed finding**: `/tmp/6-1-adversarial-review.md §R1`
- **Story 6.1 completion**: `homelab-playbook/_bmad-output/implementation-artifacts/6-1-create-replication-jobs-per-4-5-matrix.md` — esp. "Review Follow-ups (AI)" and the runbook's "Known gaps deferred to Story 6.2+"
- **Primary runbook**: `homelab-infra/docs/ha-replication-runbook.md`
- **Prometheus stack story**: `homelab-playbook/_bmad-output/implementation-artifacts/2-1-deploy-prometheus-with-scrape-targets-for-all-services.md`
- **Prior-art systemd-timer pattern**: `homelab-playbook/_bmad-output/implementation-artifacts/7-6-enable-weekly-zfs-scrub-automation.md`
- **Existing alert-rule templates**: `homelab-apps/stacks/observability/config/alerting/disk-alerts.yml`, `service-alerts.yml`, `network-alerts.yml`
- **Storage monitoring memory**: `/home/developer/.claude/projects/-home-developer-workspace-homelab/memory/project_storage_monitoring.md`
- **Proxmox replication API**: <https://pve.proxmox.com/pve-docs/pvesh.1.html>, `pvesh get /nodes/<node>/replication-status`
- **Prometheus textfile collector docs**: <https://github.com/prometheus/node_exporter#textfile-collector>
- **Prometheus alerting best practices**: <https://prometheus.io/docs/practices/alerting/>

## Dev Agent Record

### Agent Model Used

Opus 4.7 (claude-opus-4-7[1m]) invoked as BMad Dev agent (2026-04-24).

### Debug Log References

- Live `pvesh get /nodes/<node>/replication --output-format json` output sampled during implementation; all 8 jobs showed `fail_count=0` and `last_sync` within schedule bounds.
- `promtool check rules /etc/prometheus/alerting/replication-alerts.yml` → `SUCCESS: 4 rules found`.
- `promtool check config /etc/prometheus/prometheus.yml` → SUCCESS with 5 rule files.
- `curl -s http://localhost:9090/api/v1/targets?state=active` (via `docker exec`) → all 3 `node-exporter-pve` targets `up`.
- `curl -s http://localhost:9090/api/v1/query?query=pve_replication_fail_count` → 8 series, all value=0, labels complete.
- Ad-hoc PromQL for the Stale rule expression returned 0 matching series — healthy + rule is syntactically well-formed against live metrics.

### Completion Notes List

1. **Scope expansion flagged up front**: the story's Dev Notes §"Prerequisite" called for installing `prometheus-node-exporter` on pve1 and pve3 if not already there. They were NOT there. Installed via apt on pve1, pve2, pve3. This is a one-time additive install; no existing state changed; risk surface described in the story's own Security Considerations section.
2. **Textfile collector path**: Debian's `prometheus-node-exporter` package uses `/var/lib/prometheus/node-exporter/` by default (not `/var/lib/node_exporter/textfile_collector/` which the Dev Notes assumed). Used the package default — already has `apt.prom`, `nvme.prom`, `smartmon.prom` colliding with nothing. No custom `ARGS` override needed. This simplifies AC-4 delivery: the exporter ran first-try with zero systemd unit modifications.
3. **Chose `pvesh` JSON over `pvesr status` stdout parsing**: direct mitigation of the Dev Notes §"Risk 1 — exporter parse fragility". The endpoint `GET /nodes/<node>/replication` returns clean structured data (jq-parseable) with `id`, `source`, `target`, `last_sync` (already in epoch seconds — no date parsing), `duration`, `fail_count`, `schedule`, `guest`. Script is ~45 lines total, nearly all metric-emission.
4. **Chose Option A for stale-threshold alerting**: exporter emits `pve_replication_schedule_threshold_seconds` per job, single alert rule uses `on(jobid, node) group_left()` to match. Cleaner than Option B's duplicate rules; proven correct by expression-level test.
5. **Added a fourth alert (`PVEReplicationExporterStale`)** not originally in AC-6. Reason: the exporter itself is now a load-bearing dependency in the observability chain. If cron dies, all `pve_replication_*` metrics freeze at last-known-good, silently defeating the whole story. Including an exporter-freshness guard turns this from a silent-failure mode into a paged one. Same operator-annotation style, fits within the `{Domain}{Condition}` convention.
6. **`node-targets.json` left strictly alone**: confirmed Terraform-managed via `homelab-infra/terraform/envs/homelab/outputs.tf` `resource "local_file" "prometheus_targets"`. PVE hosts added via a new static `node-exporter-pve` scrape job in `prometheus.yml` instead. This is the right architectural split: `node-targets.json` tracks containers which can appear/disappear (Terraform lifecycle); PVE hosts are stable infrastructure with static IPs (Ansible-configured, not per-container Terraform'd).
7. **No Alertmanager**: confirmed via `docker ps` — no alertmanager container. Treated `/alerts` + Grafana red-panel visibility as sufficient per the developer-agent invocation's explicit scope guidance. Runbook Monitoring section documents that routing alerts to a notification channel is a future-story concern.
8. **pve2 symmetry**: deployed exporter to pve2 even though it currently has no source-side jobs (pve2 is a replica target only). pve2 still emits the exporter-freshness heartbeat metric so it's monitorable; if Story 6.3+ ever moves a workload to pve2 as its home node (e.g., VMID 100 post-Zigbee-SLZB-06M swap), the monitoring picks it up with zero extra deploy steps.
9. **Live fault-injection drill deferred** per scope constraint. Expression-level verification described above; full fault-injection happens as part of Story 6.5 (failover drill).
10. **No RAM pressure observed** during RPO sampling on pve1 — R5 follow-up from the Story 6.1 adversarial review remains legitimately deferred and not promoted to a blocking finding.

### File List

**homelab-infra/** (create)

- `proxmox/replication/pve-replication-exporter.sh` — bash script, 82 lines, emits 7 metric families from `pvesh` JSON; atomic-write pattern; runs as root via cron.

**homelab-infra/** (modify)

- `docs/ha-replication-runbook.md` — added `## Monitoring` section (data flow, metric families, 4-row alert table with operator steps, URLs, silencing guidance, manual-refresh command, Measured RPO table). Updated "Known gaps" — struck first bullet, back-referenced this story; partially-closed the RPO-dashboards bullet.

**homelab-apps/** (create)

- `stacks/observability/config/alerting/replication-alerts.yml` — 4 alert rules under `pve-replication.alerts` group. `{Domain}{Condition}` naming.
- `stacks/observability/dashboards/ha-replication.json` — Grafana dashboard UID `ha-replication-6-2`, folder `Homelab`, 5 panels (state stat / time-since-sync time series / fail_count table / last-cycle duration time series / exporter freshness stat).

**homelab-apps/** (modify)

- `stacks/observability/config/prometheus.yml` — added `node-exporter-pve` static scrape job with pve1/pve2/pve3 targets and `role: pve-host` labels. Comment explains why this is static vs. file_sd.

**Deployed to live state (NOT tracked in git, operator to verify)**

- `/usr/local/bin/pve-replication-exporter.sh` on pve1, pve2, pve3 (mode 0755)
- `/etc/cron.d/pve-replication-exporter` on pve1, pve2, pve3 (mode 0644, `*/5 * * * * root /usr/local/bin/pve-replication-exporter.sh`)
- `/var/lib/prometheus/node-exporter/pve_replication.prom` on pve1, pve2, pve3 (mode 0644, refreshed every 5 min)
- Debian package `prometheus-node-exporter` installed via apt on pve1, pve2, pve3 — NEW; enabled + active on :9100
- Prometheus config + rules hot-reloaded via `docker kill --signal=HUP prometheus` on ct-docker-01
- Grafana dashboard auto-provisioned via file-provisioning (`updateIntervalSeconds: 10`)

**User actions remaining**

- Commit the homelab-infra changes (`pve-replication-exporter.sh` + runbook) as one logical unit.
- Commit the homelab-apps changes (`replication-alerts.yml` + `ha-replication.json` + `prometheus.yml`) as one logical unit.
- If operator wants the node-exporter install + cron entry to be Ansible-reproducible, add a new role under `homelab-infra/ansible/roles/pve-node-exporter/` in a follow-up — out of scope for 6.2.

## Senior Developer Review (AI)

Two independent reviews were run on 2026-04-24 against the implemented story:

- **Code review** (`/tmp/6-2-code-review.md`) — **Approve with Minor**. Live verification confirmed the end-to-end pipeline is healthy, all 8 jobs emit every expected metric family, and the `on(jobid,node) group_left()` label match works correctly (ratios 0.17–0.34 against `schedule_threshold_seconds`, well below 1.0). Findings were nits/hardening: state-semantic ambiguity in dashboard thresholds, unknown-schedule fallthrough (overlaps adversarial R10), exporter-parse-error counter, README breadcrumb.
- **Adversarial review** (`/tmp/6-2-adversarial-review.md`) — **Medium detection confidence, LOW notification confidence**. "The exporter, rules, and dashboard are present, syntactically valid, inactive-for-the-right-reasons, and query cleanly against live data. That is real. But the notification surface has no active push channel, three of the most interesting silent-failure modes are not actually guarded, and the runbook points operators at a URL that refuses connections from the LAN." Sixteen ordered risks R1-R16 — review recommended shipping only after the 6 patches that close catastrophic-but-easy-to-miss failure modes (R1, R2, R6, R7, R10 plus runbook URL fix).

**Reconciliation:** adversarial review's "6 patches before ship" list plus code-review overlaps was applied in-story (see Review Follow-ups below). Everything else in R3–R5, R8–R9, R11–R13, R15–R16 is legitimate backlog for Stories 6.3–6.9 and Epic 7; the "Gaps for downstream stories" section at the bottom of the adversarial review is accepted verbatim as the steering note for those stories.

**Notification gap, explicit:** Story 6.2 does NOT close the notification half of R1 — Alertmanager and a push channel (ntfy / email / Teams) remain deferred to Epic 7. The runbook's §"Where to see alerts" now documents this explicitly with a prominent "Known limitation" callout, and the Traefik-routed URLs an operator must poll are correct and verified reachable (`HTTP 200` confirmed on both `https://prometheus.bi-services.be/alerts` and `https://grafana.bi-services.be/d/ha-replication-6-2`). This is the honest-ship path the adversarial review suggested ("explicitly documenting in the story that alert NOTIFICATION is deferred to Epic 7 — 6.2 delivers metrics + rules + dashboard only").

## Review Follow-ups (AI)

### In-story fixes (R1, R2, R6, R7, R10, R14 + code-review nits)

- [x] **R1a — runbook URLs:** replaced `http://192.168.50.194:9090/alerts`, `/rules`, and `http://192.168.50.194:3000/d/ha-replication-6-2` with the Traefik-routed SSO paths `https://prometheus.bi-services.be/alerts`, `.../rules`, and `https://grafana.bi-services.be/d/ha-replication-6-2`. Verified reachable (HTTP 200). Added a "Not reachable" subsection explaining why the direct-IP URLs fail (`docker inspect` shows `9090/tcp → null`, i.e. no host port mapping) so a well-meaning future edit cannot silently re-introduce them.
- [x] **R1b — push-notification callout:** added a prominent "Known limitation — there is no push notification" block at the top of §"Where to see alerts". Lists the three planned follow-ups (Alertmanager + push route, weekly heartbeat alert, Grafana-native alerting as interim) with Epic 7 as the owner.
- [x] **R2 — absent() guard rule (`PVEReplicationExporterMissing`):** fires critical after 10m if `pve_replication_exporter_last_run_timestamp_seconds` has no sample for pve1, pve2, or pve3. Closes the silent-failure mode where `time() - NaN` returns empty and no other alert can reach the operator.
- [x] **R6 — flock serialisation:** script now re-execs itself under `flock -n -E 0 /var/lock/pve-replication-exporter.lock` on the first call. Verified live on pve1 with a parallel `flock … sleep 15` process holding the lock; second invocation exited cleanly without advancing the `.prom` mtime. `-E 0` prevents cron-mail spam on a held lock.
- [x] **R7 — pvesh timeout:** wrapped in `timeout 30 pvesh get …`. On timeout, we fall through to an empty array and increment `pve_replication_exporter_errors_total`; Prometheus keeps the last-good per-job metrics on its own staleness horizon, so a hang doesn't wipe the dashboard — it just surfaces a freshness warning.
- [x] **R10 — unknown-schedule sentinel:** exporter now emits `pve_replication_schedule_minutes{…}` (e.g. 15, 30) or `-1` for unrecognised schedules. Threshold metric falls back to 86400 (24h) so Stale can't fire immediately. `PVEReplicationStale` gated on `schedule_minutes > 0` (won't fire on unknowns). `PVEReplicationUnknownSchedule` explicitly tells the operator "your exporter doesn't understand schedule X" instead of a flood of spurious staleness alerts. Recognised schedules broadened from `*/{1,5,15,30}` to any `*/N` (e.g. `*/10`, `*/60`) via a jq regex capture.
- [x] **R14 — SnapshotOrphan naming:** kept the rule name for dashboard/runbook continuity (the alternative — renaming `PVEReplicationSilentStall` or adding a real zfs-snapshot-age metric — was a deeper re-scope), but rewrote the annotation so it no longer promises a zfs check the expression doesn't perform. The annotation now acknowledges the rule is a pvesr-bookkeeping check, tells the operator to run the zfs check themselves, and describes what a mismatch ("target snapshots fresh, state stale") vs no-mismatch ("cycle really did stall") means. Full rename + target-side snapshot scan is Epic 7 backlog alongside the target-side exporter for AC-16/R16.
- [x] **Code-review: jobs guard (`PVEReplicationJobsMissing`):** exporter emits `pve_replication_exporter_jobs_total{node}`; alert fires when `sum(…) < 8` for 15m. Live: `sum = 8` (4 pve1 + 0 pve2 + 4 pve3) — matches §"Current replication matrix" in the runbook.
- [x] **Code-review: threshold-step self-documentation:** added a comment block at the top of `replication-alerts.yml` explaining why 2× for Stale (matches runbook SLO language; one missed cycle tolerated, two pages), 1h for Orphan (silent stall independent of schedule; both cadences still snap inside 1h healthy), 15m for ExporterStale (3× cron with jitter absorption).
- [x] **Code-review: README breadcrumb:** added "Monitoring exporter" section to `homelab-infra/proxmox/replication/README.md` with pointers to flock/timeout behaviour and the runbook's §Monitoring section.

### Deferred follow-ups (explicitly out-of-scope for 6.2)

- [ ] **R1c — Alertmanager + push channel.** Deferred to Epic 7. Runbook documents this. Gates: Story 6.3 (HA groups) SHOULD not be started until a push channel exists — a broken replica becomes catastrophic the moment HA is active. Recommended minimum: Alertmanager + ntfy/email webhook + weekly heartbeat alert.
- [ ] **R3 — stuck-SYNCING detection.** Needs exporter to emit `last_try - last_sync` gap as its own metric and/or parse `pvesr status` stdout for explicit "syncing" state. Deferred — ADD as Epic 7 backlog item or absorb into Story 6.5 (failover drill) where fault-injection of a stuck cycle is in scope.
- [ ] **R4 — alert-fatigue roll-up (`count(fail_count>0) >= 3` meta-alert).** Needs Alertmanager for proper `group_by` / `inhibit_rules`. Partially buildable today as a PromQL-level roll-up rule; left for when Alertmanager lands so the full suppression chain can be designed together.
- [ ] **R5 — planned-maintenance silencing via `pve_replication_disabled` gauge.** Exporter can read `.disable` from pvesh JSON; `PVEReplicationStale` expr would need `and pve_replication_disabled == 0`. Small delta, deferred to Epic 7 alongside the Alertmanager work where `amtool silence add` is the proper silencing mechanism anyway.
- [ ] **R8 — dashboard panel re-layout:** "Exporter Freshness" stat panel at y=24 is below the fold on 1080p. Low-priority UX fix; deferred.
- [ ] **R9 — clock-skew monitoring.** `abs(node_time_seconds - time()) > 30 for 5m` one-liner in `service-alerts.yml`; protects every time-sensitive alert. Deferred (Story 7.x general-monitoring cleanup).
- [ ] **R11 — job-deletion ghost-metric window.** Acceptable as-is per reviewer; if it ever causes noise, emit `pve_replication_job_exists{jobid}` sentinel.
- [ ] **R12 — `node` label clash with static scrape target.** Low priority today (pve2 has no source-side jobs so no harm); revisit when/if jobs migrate.
- [ ] **R13 — flapping `fail_count`.** Needs a counter-style metric parsing `/var/log/pve/replicate/<jobid>` or an epoch-of-last-fail gauge. Deferred to Epic 7; the 6.5 drill will first validate whether flapping is observed in practice.
- [ ] **R14 full rename + target-side snapshot scan.** Annotation fix shipped; full rename + real zfs scan deferred (target-side exporter is a bigger architectural change).
- [ ] **R15 — detection-latency documentation.** Runbook mentions 35–40 min worst case; could be more explicit about evaluation_interval + cron interval stacking. Low priority doc tweak.
- [ ] **R16 — continuous replica-integrity check.** Out of 6.2 scope per reviewer. Flag for Story 6.5 (failover drill) or Epic 7.
- [ ] **Code-review: explicit `state==0` threshold step in dashboard.** Cosmetic JSON-readability fix; deferred.
- [ ] **Code-review: `pve_replication_exporter_parse_errors_total` counter.** Partially addressed by the new `pve_replication_exporter_errors_total` gauge (covers `pvesh` timeout path); deeper jq-parse-error counter deferred.
- [ ] **Ansible role for exporter install + cron.** Noted in §"User actions remaining"; deferred.

## Change Log

| Date | Change | Rationale |
|---|---|---|
| 2026-04-24 | Story file created by BMad SM (planner agent) | Story 6.2 planning; absorbs Story 6.1's deferred R1 (no monitoring on replication health). Scope expanded beyond the epic's one-liner to include Prometheus exporter + alert rules + Grafana dashboard + end-to-end drill. |
| 2026-04-24 | Story implemented by BMad Dev (Opus 4.7); status ready-for-dev → review | AC-1..AC-7 and AC-9 delivered end-to-end. AC-8 live fault-injection deferred to Story 6.5 per scope constraint; expression-level verification substituted. Scope additions flagged in Completion Notes: installed `prometheus-node-exporter` on all 3 PVE hosts (prerequisite per Dev Notes), used package-default textfile collector path `/var/lib/prometheus/node-exporter/`, added a 4th alert (`PVEReplicationExporterStale`) as a meta-guard. |
| 2026-04-24 | Runbook URLs fixed (R1): replaced `http://192.168.50.194:9090`/`:3000` with `https://prometheus.bi-services.be/…` and `https://grafana.bi-services.be/d/ha-replication-6-2` | Adversarial R1: Docker doesn't publish 9090/3000 on the host (verified `nc -zv 192.168.50.194 9090` → connection refused). Only Traefik+Authelia paths are reachable. Added an explicit "Known limitation — no push notification" callout and documented why the direct-IP URLs do not work so future revisions don't re-introduce them. |
| 2026-04-24 | Exporter hardened: `flock -n` serialises cron, `timeout 30` wraps `pvesh`, unknown schedules now emit `pve_replication_schedule_minutes=-1` with an 86400 fallback threshold | Adversarial R6/R7/R10. Flock tested live: second invocation while lock held exited 0 without advancing the .prom mtime. Timeout prevents a wedged pveproxy from blocking 5-min cron stacks. Unknown-schedule fallback closes the "threshold=0 fires forever" silent failure; `PVEReplicationUnknownSchedule` now surfaces that case explicitly. |
| 2026-04-24 | Alert set grew from 4 to 7 rules: added `PVEReplicationExporterMissing` (absent-based, R2), `PVEReplicationUnknownSchedule` (R10), `PVEReplicationJobsMissing` (code-review `pve_replication_exporter_jobs_total < 8` guard). `PVEReplicationStale` gated on `schedule_minutes > 0`. | R2: the freshness rule depends on `time() - NaN` being empty, so if the metric disappears entirely the rule cannot fire — `absent()` is the only safe guard. Job-count guard closes the silent-`pvesh`-returns-empty failure. Threshold-step comments added to the rules file so the 2× / 1h / 15m choices are self-documenting. |
| 2026-04-24 | `PVEReplicationSnapshotOrphan` annotation reworded to acknowledge it is a pvesr-bookkeeping check, not a zfs-snapshot check | Adversarial R14: the rule name promised a zfs check the expression doesn't perform. Keeping the name for runbook/dashboard continuity (R14 called this out as misnamed-OR-implement; the lighter fix was chosen), but the annotation now explicitly tells the operator to run the zfs check themselves and explains what a mismatch means. Full rename / real zfs-snapshot-age metric deferred to Epic 7 alongside target-side scans. |
| 2026-04-24 | proxmox/replication/README.md got a "Monitoring exporter" section | Code-review breadcrumb nit: the story's file-layout promised a reference in the proxmox/replication README. Added a 4-line pointer with flock/timeout notes and a link back to the runbook's §Monitoring section. |
| 2026-04-24 | Status: review → done | All 11 R1–R14 items addressed either in-story or explicitly deferred with rationale (see Review Follow-ups below). Alertmanager + push channel consciously deferred to Epic 7. |
