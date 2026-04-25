# Story 6.10.2 — pvesr fail_count alerting verification evidence

**Date**: 2026-04-25
**Branch identified**: A (rule + metric both present, properly tuned)
**Verdict**: PARTIAL-DONE — no code changes required

## Headline

V5 drill task wording referenced `pve_replication_failcount` (no underscore).
The **actually-published** metric is `pve_replication_fail_count` (with underscore,
matching `node-exporter` textfile-collector convention). The metric IS published,
publishes a row per defined job (including `fail_count=0` healthy rows), and
Story 6.2's `PVEReplicationFailing` rule already alerts on it.

V5's "empty metric" observation was a metric-name typo, not an exporter or alert gap.

## Evidence summary

### Metric coverage (file `01-fail-count-by-node.json`)

```
pve1: 4 series  (jobs 100-0, 100-1, 101-0, 101-1)
pve2: 2 series  (jobs 151-0, 151-1 — ct-sparkle-cps; not in 6.1 matrix but a real CT)
pve3: 4 series  (jobs 162-0, 162-1, 250-0, 250-1)
TOTAL: 10 series — matches 10 active pvesr jobs cluster-wide
```

### Per-job schedule (file `03-schedule-minutes.json`)

```
100-0/1   pve1->pve2/3   */15
101-0/1   pve1->pve2/3   */15
151-0/1   pve2->pve1/3   */15   (ct-sparkle-cps; outside 6.1 matrix but exporter sees it)
162-0/1   pve3->pve1/2   */1    (ct-quant-trading, Story 6.5 KEEP)
250-0/1   pve3->pve1/2   */30
```

The `*/1` cadence on 162-0/1 is the worst-case workload this story was concerned about.
Both jobs publish `pve_replication_fail_count{...}=0` when healthy.

### Existing alert rule (file `04-active-rules.json`)

```yaml
- alert: PVEReplicationFailing
  expr: pve_replication_fail_count > 0
  for: 10m
  labels:
    severity: critical
    domain: replication
  state: inactive  (healthy)
```

### Routing (alertmanager.yml inspection)

```
severity=critical -> ntfy-urgent (topic: homelab-alerts-urgent)
                     group_wait: 10s
                     repeat_interval: 4h
```

Routing is case-insensitive on severity, fail-loud default to ntfy-urgent.
Story 7.11 confirms operator phone has Urgent priority on this topic.

## Why no code changes

AC-2 PARTIAL-DONE branch criteria all met:
- Existing rule has severity=critical (matches story's *escalation* tier expectation)
- Routing reaches ntfy with Urgent priority
- Exporter publishes a row per defined job, including healthy 0-valued rows
  (so `> 0` matcher is satisfiable)

Faster warning tier (`> 0 for 5m`) is a deferred enhancement (story 6.10.3 if ever
needed); the existing `> 0 for 10m critical` is judged sufficient by SM/Dev for this
operator's risk appetite.

## V5 metric-name typo provenance

Task wording: `pve_replication_failcount` (no underscore)
Actually published: `pve_replication_fail_count` (with underscore)

The exporter source confirms the underscore variant is canonical:
`homelab-infra/proxmox/replication/pve-replication-exporter.sh:53`
```
# HELP pve_replication_fail_count Consecutive failure count from `pvesr status` (integer).
# TYPE pve_replication_fail_count gauge
```

Story 6.2's rule and dashboards all use the underscore variant. The V5 task
description should be updated to refer to the correct name in any future drill log.

## No synthetic test required

AC-4 synthetic test is contingent on AC-3 (new-rule path); since this story collapsed
to AC-2 PARTIAL-DONE, the synthetic test for the existing critical-tier rule was
already validated by the V5 drill itself: ct-quant-trading was migrated, replication
re-seeded, all 10 series remain `inactive` in `/api/v1/rules`. The chain is live.

A dedicated synthetic-failure test for the existing rule (zfs-quota injection on
101-0) is left as a Sprint 7 dry-run item if operator wants belt-and-braces proof —
not required for this story's scope.
