---
status: backlog
epic: 6
story: 6.10.3
title: Audit alert rules for label-mutation semantics + harden Prometheus container restart policy
created: 2026-04-25
author: BMad SM
depends-on: 6-10
---

# Story 6.10.3: Audit alert rules for label-mutation semantics + Prometheus container restart-policy hardening

Status: backlog

## Story

As an operator,
I want every alert / recording rule that uses `changes()`, `rate()`, or `increase()` over a series with mutating labels to be audited and rewritten with label-stable patterns AND the Prometheus container's restart policy hardened so that a clean-exit (such as the one observed at 09:24:30Z 2026-04-25) cannot leave the alerting chain dark for 4+ minutes,
so that the Story 6.10 HA-state observability we just deployed never fails silently — neither at the rule-semantics layer (a `changes()` rule that never increments because label-mutation creates a *new* series) nor at the container-availability layer (Prometheus exited cleanly under `unless-stopped` and no auto-restart triggered).

## Business value

The Story 6.6 V4 drill surfaced two coupled silent-failure modes in the freshly-deployed Story 6.10 observability stack:

1. **Label-mutation blindness in `changes()` rules** (adversarial R3 MED): A rule written as `changes(pve_ha_resource_state[5m]) > 3` looks like it should fire on a flapping ct:162. It does not — `pve_ha_resource_state` carries an `exported_node` label that flips on migrate. When the migrate happens, Prometheus does not see "the same series changed value"; it sees "the old series went stale and a new series with a different label-set appeared". `changes()` returns 0 because the old series has no further samples. The rule is silently blind to the exact event it was written to detect. The same pattern can affect `rate()` (counter resets at series boundary) and `increase()` (same). Story 6.10 deployed N rules without auditing for this — there could be more blind rules we haven't found yet.

2. **Prometheus container clean-exit under `unless-stopped`** (code-review L2 LOW): At 09:24:30Z 2026-04-25 (4 min before the V4 drill), the prometheus container exited cleanly (`exited (0)` per `docker compose ps`). The compose file declares `restart: unless-stopped`, which by Docker semantics auto-restarts on failure but **NOT on clean exit by an operator action**. There was no operator action at that timestamp. The most likely culprits are: (a) a `docker compose pull` collateral, (b) a memory-limit hit during compaction triggering OOM, (c) a SIGTERM from the host's docker daemon during a maintenance task. Whatever the cause, `unless-stopped` did not protect the alert chain — and neither did any meta-monitor (`PrometheusContainerDown` does not exist as a rule). The drill happened to fire 4 min later when prometheus was healthy again, but a 4-min dark window is a 4-min window during which an unrelated incident could have gone unalerted.

Both gaps reduce the value of Story 6.10's investment. This story closes them in a single coupled hardening pass:

1. **Audit-and-rewrite** all rules using `changes()`/`rate()`/`increase()` over `pve_ha_*` (and any other series with mutating labels) — replace with label-stable patterns (recording rules that strip mutating labels, OR `count by (sid)` of `count_over_time`).
2. **Investigate-and-harden** the prometheus container restart policy — determine why clean-exit happened, switch to `restart: always` (or healthcheck + force-restart-on-fail), AND add a `PrometheusContainerDown` alert routed to ntfy so a future dark window pages immediately.

Without 6.10.3, the operator's mental model of "Story 6.10 observability is complete" carries two hidden dependencies (no rule blind-spots, prometheus stays up). With 6.10.3, both are converted from assumptions to enforced invariants with synthetic tests proving each path.

## Absorbed finding

This story **absorbs** Story 6.6's adversarial-review and code-review findings:

- **R3 (MED, adversarial)** — "`changes()=0` on `pve_ha_resource_state` was a Prometheus label-mutation semantic. Story 6.10 alert rules may have similar blindness on label-mutating series." 6.6's V4 drill found that the rule did not fire because `exported_node` mutated; the AC-2 audit below systematically sweeps for the same pattern across all rules.
- **L2 (LOW, code-review)** — "prometheus container clean-exit at 09:24:30Z (4 min pre-drill); `unless-stopped` policy shouldn't exit cleanly without operator action; worth a restart-policy hardening pass." AC-4 through AC-7 close this.

R2 (application-impact during graceful migrate) and R4 (replication-lag injection) are absorbed by Story 6.6.1 — explicitly out-of-scope here.

R7+R8 (drill pre-flight + post-flight checks) are absorbed by Story 6.9.1 — out-of-scope here.

R1 outcome-B (`PVEClusterCTMigrated` info-severity alert) is folded into Story 6.10.1 — out-of-scope here.

## Acceptance Criteria

### AC-1: Pre-flight — cluster healthy, observability stack up, rule baseline captured

**Given** the cluster is 3/3 quorate (`pvecm status` on pve1: `Quorate: Yes`, `Total votes: 3`)
**And** Story 6.10 is `done` (HA exporter live; `ha-alerts.yml` deployed)
**And** the observability stack is up (`docker compose ps` on ct-docker-01 shows prometheus, alertmanager, grafana, ntfy all `running` AND `healthy` if a healthcheck is defined)
**When** I capture the baseline
**Then** the following baseline files exist:
- `/tmp/6-10-3-rules-pre.json` — `curl -s 'https://prometheus.bi-services.be/api/v1/rules' | jq` (full rule list snapshot)
- `/tmp/6-10-3-prometheus-inspect-pre.json` — `docker inspect prometheus | jq '.[0].HostConfig.RestartPolicy, .[0].State'`
- `/tmp/6-10-3-prometheus-logs-pre.txt` — `docker logs prometheus --since 24h --tail 5000` (captures the 09:24:30Z exit context for forensic analysis)
- `/tmp/6-10-3-compose-pre.txt` — `docker compose -f /opt/homelab-apps/stacks/observability/docker-compose.yml config` (resolved compose state)
**And** no `PVEHA*` rule is currently firing (we are not auditing during a real incident).

### AC-2: Grep audit — identify all alert/recording rules using `changes()` / `rate()` / `increase()` over label-mutating series

**Given** AC-1 holds
**When** I sweep the alerting + recording rule files for the three problematic functions:
```
cd homelab-apps/stacks/observability/config/alerting
grep -nE 'changes\s*\(|rate\s*\(|increase\s*\(' *.yml > /tmp/6-10-3-grep-changes.txt
```
**And** I cross-reference each match against the **list of known label-mutating series**:
- `pve_ha_resource_state` — has `exported_node` (flips on migrate), `state` (flips on transition; itself a label of interest, not a mutation in the PromQL sense — but counts as a label that is **expected to change**)
- `pve_ha_lrm_status` — has `node`, `status` (status flips on LRM state changes)
- `pve_ha_crm_master` — has `node` (flips on master election)
- Any `pve_*` series with `node` / `target` / `exported_node` labels that flip during HA / migration / replication events
- Any `up{...}` series whose `instance` label can change (rare; flag for completeness)
**Then** a Markdown table is produced at `/tmp/6-10-3-audit-table.md` with one row per identified rule:
| Rule name | File | Function | Series | Mutating label(s) | Risk classification |
|---|---|---|---|---|---|
| ExampleAlertName | ha-alerts.yml | `changes()` | `pve_ha_resource_state` | `exported_node`, `state` | HIGH — silent blind during migrate |
**And** the audit table is reviewed and each rule is classified as one of:
- **HIGH** — rule is silently blind during the exact event it was meant to detect (must rewrite)
- **MEDIUM** — rule may produce double-counts or miss-counts during label transitions (should rewrite)
- **LOW** — rule's PromQL math is unaffected by label mutation in practice (e.g. `rate()` over a counter with stable labels) — no change needed
**And** the audit covers all files under `homelab-apps/stacks/observability/config/alerting/` (not just `ha-alerts.yml`) — `replication-alerts.yml`, `disk-alerts.yml`, `service-alerts.yml`, `network-alerts.yml`, and any others present.

### AC-3: For each HIGH/MEDIUM rule, rewrite with label-stable pattern + validate via `promtool`

**Given** AC-2 holds and at least one rule is classified HIGH or MEDIUM
**When** I rewrite each affected rule using one of the documented label-stable patterns:

**Pattern A — recording rule that strips mutating labels first**:
```yaml
# In recording-rules.yml
groups:
  - name: pve-ha.recording
    rules:
      - record: pve_ha_resource_state_by_sid
        expr: max by (sid, state) (pve_ha_resource_state)
# Then the alert uses the stripped series:
- alert: PVEHAResourceFlapping
  expr: changes(pve_ha_resource_state_by_sid[10m]) > 4
```

**Pattern B — `count by (sid) (count_over_time(...))`**:
```yaml
- alert: PVEHAResourceFlapping
  expr: |
    count by (sid) (
      count_over_time(pve_ha_resource_state{state="error"}[10m])
    ) > 4
```
This counts unique `(sid, error-sample)` tuples regardless of `exported_node` mutation — every unique (sid, error) appearance increments by 1.

**Pattern C — `quantile_over_time` / `last_over_time` with explicit `by` clause**:
For state-tracking, prefer `last_over_time(...)` and `by (sid)` aggregation rather than `changes()`.

**Then** each rewritten rule is validated:
```
docker exec prometheus promtool check rules /etc/prometheus/alerting/<file>.yml
# Expected: SUCCESS, <N> rules found
docker exec prometheus promtool check config /etc/prometheus/prometheus.yml
# Expected: SUCCESS
```
**And** Prometheus is hot-reloaded via `docker kill --signal=HUP prometheus`
**And** `/api/v1/rules` shows the rewritten rules as `inactive` (or with the same firing state they had pre-rewrite, if applicable)
**And** for each rewritten rule, a synthetic test is run that **proves the rewrite catches the previously-blind event**:
- For each HIGH-classified rule, inject the exact event the rule is meant to detect (e.g. for an HA-flapping rule, manipulate the `pve_ha_state.prom` file across multiple node values to simulate label mutation)
- Verify the rewritten expression evaluates non-zero against the synthetic event
- Capture the synthetic-test evidence to `/tmp/6-10-3-synthetic-rule-tests.txt`

### AC-4: Prometheus container restart-policy investigation

**Given** AC-1's baseline captured the 09:24:30Z exit context
**When** I investigate the clean-exit cause:
```
# 1. What is the current restart policy?
docker inspect prometheus --format '{{json .HostConfig.RestartPolicy}}'
# Expected: {"Name":"unless-stopped","MaximumRetryCount":0}

# 2. What does the exit log show?
docker logs prometheus --since 48h --tail 10000 | grep -B 3 -A 10 -E 'shutting down|received SIGTERM|received SIGINT|context canceled|out of memory|killed' > /tmp/6-10-3-exit-context.txt

# 3. Was there compose activity (pull / up / restart) around that timestamp?
journalctl -u docker --since '2026-04-25 09:00:00' --until '2026-04-25 09:30:00' | grep -E 'compose|prometheus' > /tmp/6-10-3-docker-journal.txt

# 4. Was there a memory-limit hit?
docker inspect prometheus --format '{{.HostConfig.Memory}} {{.HostConfig.MemorySwap}}'
journalctl -k --since '2026-04-25 09:00:00' --until '2026-04-25 09:30:00' | grep -E 'oom|out of memory|killed process' > /tmp/6-10-3-oom-journal.txt

# 5. What was the kernel doing?
journalctl -k --since '2026-04-25 09:00:00' --until '2026-04-25 09:30:00' > /tmp/6-10-3-kernel-journal.txt
```
**Then** the root cause is identified and documented as one of:
- **Cause A — operator-initiated**: a `docker compose` command was issued (pull / restart / down). Verify against operator's shell history if available.
- **Cause B — OOM / memory-limit**: kernel killed the process. Confirmed by `oom_killer` entries in dmesg.
- **Cause C — SIGTERM from docker daemon**: docker maintenance event (image cleanup, daemon reload).
- **Cause D — application-internal clean exit**: prometheus's own shutdown logic triggered (e.g. corrupt TSDB block detected; uncommon).
- **Cause E — UNDETERMINED** — flagged for follow-up; harden anyway per AC-5 because `restart: unless-stopped` already failed once, regardless of cause. **NEEDS OPERATOR CONFIRMATION** that proceeding with hardening on Cause E is acceptable (i.e. fix-the-symptom-while-Cause-E-investigation-continues vs block-on-root-cause).
**And** the cause is captured in the runbook under a new "2026-04-25 prometheus dark window — root cause analysis" section.

### AC-5: Harden compose restart policy + validate

**Given** AC-4 holds
**When** I edit `homelab-apps/stacks/observability/docker-compose.yml`:
- **Choice 1 (recommended)**: change `restart: unless-stopped` to `restart: always`. Difference: `always` restarts on **any** exit (clean OR non-zero) regardless of operator stop history. Trade-off: a deliberately-stopped container will be restarted unless the operator uses `docker compose down` (which removes the container entirely). For a load-bearing observability container, this is the right default.
- **Choice 2 (alternative)**: keep `restart: unless-stopped` AND add a `healthcheck` + autoheal sidecar. More complex; only pursue if Choice 1 breaks an operator workflow (e.g. local-dev where `docker stop prometheus` is used routinely). Healthcheck example:
  ```yaml
  prometheus:
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:9090/-/healthy"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 30s
  ```
- Document the choice in the compose file as a comment + in the runbook.
**Then** apply the change:
```
cd /opt/homelab-apps/stacks/observability
docker compose up -d prometheus
docker inspect prometheus --format '{{json .HostConfig.RestartPolicy}}'
# Expected: {"Name":"always","MaximumRetryCount":0}  (for Choice 1)
```
**And** verify the change is committed to the homelab-apps repo, not just on the running host.

### AC-6: Add `PrometheusContainerDown` alert

**Given** AC-3 and AC-5 hold
**When** I add a new rule to `homelab-apps/stacks/observability/config/alerting/service-alerts.yml`:
```yaml
- alert: PrometheusContainerDown
  expr: up{job="prometheus"} == 0
  for: 2m
  labels:
    severity: warning
    domain: observability
  annotations:
    summary: 'Prometheus self-monitoring: prometheus container is down for {{ $value }}m'
    description: |
      The prometheus container on ct-docker-01 has been unreachable from its own
      scrape target (up{job="prometheus"} == 0) for >2 min. The alert chain may
      be partially or fully dark — investigate via:
        ssh ct-docker-01 "docker compose -f /opt/homelab-apps/stacks/observability/docker-compose.yml ps prometheus"
        ssh ct-docker-01 "docker logs prometheus --tail 100"
      Restart policy is restart: always per Story 6.10.3; if container is missing
      entirely, the host docker daemon may be unhealthy.
    runbook: 'https://github.com/.../homelab-infra/docs/observability-runbook.md#prometheus-container-down'
```
**Then** the rule is validated and loaded:
```
docker exec prometheus promtool check rules /etc/prometheus/alerting/service-alerts.yml
# Expected: SUCCESS, <N+1> rules found
docker kill --signal=HUP prometheus
curl -s 'https://prometheus.bi-services.be/api/v1/rules' | jq '.data.groups[] | .rules[] | select(.name=="PrometheusContainerDown")'
# Expected: rule visible, state=inactive
```
**And** the alert is routed to `homelab-alerts-default` ntfy topic via the existing severity-tree in `alertmanager.yml` (Story 7.11) — `severity=warning` maps to ntfy-default per the established routing. No new alertmanager route needed.
**And** the runbook documents the alert: what it means, first 3 operator steps, manual recovery (`docker compose up -d prometheus`), and known dark-window-bound (`for: 2m` + scrape interval + group_wait = ~3 min worst-case time-to-page).

### AC-7: Synthetic test — stop prometheus, verify alert fires AND auto-restart kicks in

**Given** AC-5 and AC-6 hold
**When** I run the synthetic test:
```
# Mark T_0 — the moment we issue the stop
T0=$(date +%s)
ssh ct-docker-01 "docker compose -f /opt/homelab-apps/stacks/observability/docker-compose.yml stop prometheus"

# Wait 3 min — long enough for the alert (2m for: + scrape + group_wait) to fire
sleep 180

# Check alert state
curl -s 'https://prometheus.bi-services.be/api/v1/alerts' | jq '.data.alerts[] | select(.labels.alertname=="PrometheusContainerDown")'
# Expected: BUT — prometheus is stopped, this URL won't respond. Use alertmanager instead:
curl -s 'https://alertmanager.bi-services.be/api/v2/alerts' | jq '.[] | select(.labels.alertname=="PrometheusContainerDown")'
# Expected: 1 alert, state=active

# Verify ntfy push received
docker logs ntfy --since 5m | grep -i 'PrometheusContainerDown'
# Expected: 1 push delivered to homelab-alerts-default topic
```
**Then** within 3 min of T_0, the operator's phone receives a `homelab-alerts-default` ntfy push for `PrometheusContainerDown`
**And** I now restart and verify auto-recovery:
```
# If Choice 1 (restart: always) was chosen: stopping the container with docker compose stop should NOT trigger auto-restart (compose stop sets a manual-stop flag)
# So we manually start it back:
ssh ct-docker-01 "docker compose -f /opt/homelab-apps/stacks/observability/docker-compose.yml up -d prometheus"

# OR — to fully test auto-restart, kill (not stop) the prometheus process inside the container:
ssh ct-docker-01 "docker kill prometheus"
# This simulates a process crash; restart: always SHOULD auto-restart within seconds
```
**And** verify recovery:
```
sleep 30
curl -s 'https://prometheus.bi-services.be/-/healthy'
# Expected: 200 Prometheus Server is Healthy
curl -s 'https://alertmanager.bi-services.be/api/v2/alerts' | jq '.[] | select(.labels.alertname=="PrometheusContainerDown")'
# Expected: alert resolved (or no longer present)
docker logs ntfy --since 2m | grep -i 'PrometheusContainerDown'
# Expected: resolved/RESOLVED push delivered
```
**And** the synthetic test evidence is captured to `/tmp/6-10-3-prometheus-down-test.txt`.

**Note**: there is a real but bounded operator-impact risk during this test — for ~3 min, the alerting chain is dark (prometheus is what evaluates rules). Mitigations:
- Run during a quiet window (no other drills in flight; ideally same window as Story 6.9.1's drill safety gates).
- Other independent monitoring (e.g. uptimerobot, external pings) is out-of-scope but worth a follow-up.

### AC-8: Changes documented in observability docs + runbook

**Given** AC-1 through AC-7 hold
**When** I update documentation
**Then**:
- `homelab-infra/docs/ha-replication-runbook.md` Monitoring section has a new "Label-mutation audit (Story 6.10.3)" subsection listing the audited rules, classification table, and the rewrite patterns (A/B/C) used.
- A new file or section `homelab-infra/docs/observability-runbook.md` (or extension thereof if it already exists) documents:
  - The prometheus container restart-policy choice (Choice 1 or Choice 2) + rationale.
  - The 2026-04-25 dark-window root-cause analysis (per AC-4 outcome).
  - The `PrometheusContainerDown` alert + first 3 operator steps + manual recovery.
- Cross-references from Story 6.10's runbook section to 6.10.3's additions.
- The `/tmp/6-10-3-audit-table.md` produced in AC-2 is committed (or its content folded into the runbook).

## Tasks

- [ ] **Task 0: Pre-flight + baseline capture** (AC-1)
  - Cluster quorate; observability stack up; no PVEHA* firing.
  - Capture rule list, prometheus inspect, prometheus logs, compose state.

- [ ] **Task 1: Grep audit + classification** (AC-2)
  - `grep -nE 'changes\s*\(|rate\s*\(|increase\s*\('` across `alerting/*.yml` + `recording/*.yml` (if present).
  - Cross-reference each match against the known-mutating-series list.
  - Author `/tmp/6-10-3-audit-table.md` with HIGH / MEDIUM / LOW classification.

- [ ] **Task 2: Rewrite HIGH and MEDIUM rules** (AC-3)
  - For each affected rule, choose Pattern A / B / C; rewrite.
  - Add recording rules where Pattern A is chosen (`recording-rules.yml`; create file if absent).
  - `promtool check rules` and `promtool check config` after each edit.
  - Hot-reload prometheus.
  - Synthetic-event test for each HIGH-classified rule; capture evidence.

- [ ] **Task 3: Investigate prometheus dark-window root cause** (AC-4)
  - Pull exit logs, docker journal, kernel journal around 09:24:30Z.
  - Determine cause (A/B/C/D/E); document in runbook.

- [ ] **Task 4: Harden compose restart policy** (AC-5)
  - Pick Choice 1 (`restart: always`) or Choice 2 (healthcheck + autoheal).
  - Edit compose file with comment documenting choice + rationale.
  - `docker compose up -d prometheus`; verify `RestartPolicy.Name = always` (or equivalent).
  - Commit change.

- [ ] **Task 5: Add `PrometheusContainerDown` alert** (AC-6)
  - Append rule to `service-alerts.yml`.
  - `promtool check rules` SUCCESS.
  - SIGHUP-reload prometheus.
  - Verify rule visible at `/api/v1/rules` as `inactive`.
  - Verify alertmanager severity-tree routes warning → ntfy-default (no new route needed).

- [ ] **Task 6: Synthetic test — stop prometheus** (AC-7)
  - `docker compose stop prometheus` at T_0.
  - Wait ≤3 min; verify ntfy push received.
  - Restart container; verify alert resolves; verify auto-recovery on `docker kill prometheus` (Choice 1 only).
  - Capture evidence to `/tmp/6-10-3-prometheus-down-test.txt`.

- [ ] **Task 7: Documentation refresh** (AC-8)
  - Update `ha-replication-runbook.md` Monitoring section + `observability-runbook.md` (new or existing).
  - Cross-reference Story 6.10 + 6.10.1 + 7.11.

- [ ] **Task 8: Final-state evidence + status flip**
  - Verify all rewritten rules `inactive` post-reload.
  - Verify prometheus container `up` with new restart policy.
  - Verify `PrometheusContainerDown` `inactive`.
  - Append Dev Agent Record per Story 6.10 pattern.
  - Frontmatter `backlog → review`.

## Dev Notes

### `promtool` invocation paths

The prometheus container ships `promtool` at `/bin/promtool`. Validate rules from outside the container:
```
docker exec prometheus promtool check rules /etc/prometheus/alerting/<file>.yml
docker exec prometheus promtool check config /etc/prometheus/prometheus.yml
```
The `/etc/prometheus/alerting/` path inside the container maps to `homelab-apps/stacks/observability/config/alerting/` on the host (via bind mount in compose). Editing the host file + SIGHUP-reload prometheus is the canonical update path.

### Docker compose locations

- Compose file: `/opt/homelab-apps/stacks/observability/docker-compose.yml` on ct-docker-01
- Repo source: `homelab-apps/stacks/observability/docker-compose.yml`
- Reload: `cd /opt/homelab-apps/stacks/observability && docker compose up -d prometheus` (recreates container with new config; brief downtime ~5 s during the swap; alert chain may not catch this since it's <2 min `for:`)

### Alertmanager routing tree (Story 7.11 reference)

The severity-tree in `alertmanager.yml` (Story 7.11) routes:
- `severity=critical` → `ntfy-urgent` (homelab-alerts-urgent topic)
- `severity=warning` → `ntfy-default` (homelab-alerts-default topic)
- `severity=info` → `ntfy-low` (homelab-alerts-low topic, if implemented; otherwise default)

`PrometheusContainerDown` uses `severity=warning` → routes to `ntfy-default` automatically. No new route needed.

### Healthcheck examples (Choice 2 alternative)

If Choice 2 is selected (less invasive than `restart: always`):
```yaml
prometheus:
  healthcheck:
    test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:9090/-/healthy"]
    interval: 30s
    timeout: 5s
    retries: 3
    start_period: 30s
```

Plus an autoheal sidecar (e.g. `willfarrell/autoheal`):
```yaml
autoheal:
  image: willfarrell/autoheal
  restart: always
  environment:
    - AUTOHEAL_CONTAINER_LABEL=autoheal
  volumes:
    - /var/run/docker.sock:/var/run/docker.sock
```

Then label `prometheus`:
```yaml
prometheus:
  labels:
    - autoheal=true
```

Choice 2 trade-offs: more moving parts; autoheal sidecar itself becomes load-bearing. Recommendation: Choice 1 unless operator's local-dev workflow specifically needs `docker stop prometheus` to NOT auto-restart.

### Recording-rules.yml file pattern

If no `recording-rules.yml` exists yet (Story 6.10 didn't create one), this story creates it under `homelab-apps/stacks/observability/config/alerting/` (same directory; loaded by `prometheus.yml`'s `rule_files:` glob). Skeleton:

```yaml
groups:
  - name: pve-ha.recording
    interval: 30s
    rules:
      - record: pve_ha_resource_state_by_sid
        expr: max by (sid, state) (pve_ha_resource_state)
      # ... other label-stripping recordings ...
```

The recording rules pre-aggregate the mutating labels away, so downstream alert rules can use the stable `_by_sid` series without paying the per-evaluation cost.

### Risk / failure modes

1. **Rewritten rule changes firing semantics in unintended ways** — a rule that previously fired on label-mutation events now only fires on stable-series transitions. Mitigation: synthetic-event test for each HIGH rule (AC-3 final clause); operator reviews the audit table before applying.
2. **`restart: always` interferes with operator's local-dev workflow** — if operator routinely stops prometheus for testing, `restart: always` undoes it. Mitigation: documented in compose comment; Choice 2 is the alternative.
3. **AC-7 synthetic test creates a real ~3-min dark window** — alerting chain blind during the test. Mitigation: schedule in a quiet window; document; Story 6.9.1's drill-safety gate would normally cover this if we treated AC-7 as a drill (consider adding `--drill-name 6-10-3-synthetic-stop` invocation if 6.9.1 done).
4. **Cause E (undetermined root cause) for the 09:24:30Z exit** — hardening proceeds but the root cause is unresolved; if it recurs, the `PrometheusContainerDown` alert will fire and forensic data will accumulate. Acceptable; flagged in runbook.
5. **Recording-rules.yml file collision** — if Story 6.10.1 or 6.10.2 also creates a recording-rules file, naming collision possible. Mitigation: search for existing `recording-rules*.yml` before creating; reuse if present.

### File layout

**homelab-apps/** (modify):
- `stacks/observability/config/alerting/<varies>.yml` — rewritten rules
- `stacks/observability/config/alerting/service-alerts.yml` — append `PrometheusContainerDown`
- `stacks/observability/config/alerting/recording-rules.yml` — new file, contains label-stripping recording rules (only if Pattern A used)
- `stacks/observability/docker-compose.yml` — restart-policy hardening (Choice 1 or 2)

**homelab-infra/** (modify):
- `docs/ha-replication-runbook.md` — new "Label-mutation audit (Story 6.10.3)" subsection
- `docs/observability-runbook.md` (new file or existing) — restart-policy choice rationale, dark-window RCA, `PrometheusContainerDown` operator steps

### Prior art references

- **Story 6.10 (HA exporter)**: `homelab-playbook/_bmad-output/implementation-artifacts/6-10-ha-state-prometheus-exporter.md` — the rules being audited
- **Story 6.10.1 (HA alert tuning post-soak)**: `homelab-playbook/_bmad-output/implementation-artifacts/6-10-1-ha-alert-tuning-post-soak.md` — co-tuning context; coordinate to avoid double-edits on `ha-alerts.yml`
- **Story 6.10.2 (pvesr fail_count alerting)**: `homelab-playbook/_bmad-output/implementation-artifacts/6-10-2-pvesr-fail-count-alerting.md` — same observability stack
- **Story 6.6 (V4 drill — adversarial review surfaced these findings)**: `homelab-playbook/_bmad-output/implementation-artifacts/6-6-validation-drill-v4-simulated-failover-via-migrate.md`
- **Story 6.2 (replication exporter precedent)**: `homelab-playbook/_bmad-output/implementation-artifacts/6-2-verify-replication-state-and-deltas.md` — prometheus rule-file deployment pattern
- **Story 7.11 (push channel)**: `homelab-playbook/_bmad-output/implementation-artifacts/7-11-alertmanager-and-ntfy-push-channel.md` — severity routing tree
- **Prometheus `changes()` semantics**: <https://prometheus.io/docs/prometheus/latest/querying/functions/#changes>
- **Prometheus label-matching docs**: <https://prometheus.io/docs/prometheus/latest/querying/basics/#instant-vector-selectors>
- **Docker compose restart policies**: <https://docs.docker.com/compose/compose-file/05-services/#restart>
- **Memory: project_storage_monitoring.md** — observability conventions

## Test strategy

**Phase 1 (Task 0):** observation-only; baseline capture.

**Phase 2 (Task 1):** static-analysis only (grep + classification). No state change.

**Phase 3 (Task 2):** rule rewrites. Each rewrite is validated by `promtool` before reload; reload is hot (SIGHUP, no downtime). Synthetic-event tests against each HIGH rule.

**Phase 4 (Task 3):** investigation only; reads logs, no state change.

**Phase 5 (Tasks 4-5):** restart-policy + new alert deployment. Container recreate (~5 s downtime); accepted.

**Phase 6 (Task 6):** load-bearing AC-7 synthetic test. Real ~3-min dark window. Side-effect: 1 real ntfy push (alert) + 1 real ntfy push (resolution) to operator phone. Manual restart restores normal state.

**Phase 7 (Tasks 7-8):** documentation + status flip. No state change.

**Test acceptance**: rule rewrites pass `promtool` + synthetic-event tests catch the previously-blind events; prometheus container has new restart policy; `PrometheusContainerDown` rule loaded and tested end-to-end with real ntfy push delivery; runbook updated.

## Security considerations

- All edits confined to existing config files (`*.yml`, `docker-compose.yml`) and new alert/recording-rule files.
- No new credentials, no new network-facing services.
- The new `PrometheusContainerDown` alert exposes ct-docker-01's hostname in its annotation — operational metadata, not credential material.
- `docker inspect` and `docker logs` invocations are read-only; existing root-equivalent privilege on ct-docker-01 already exists for the operator.
- Restart-policy change does not expand attack surface; it only changes when docker auto-restarts the container.
- Synthetic test (AC-7) does not introduce any data exposure — it stops/starts a local container.

## Rollback procedure

1. **Revert rule rewrites**:
   ```
   git checkout homelab-apps/stacks/observability/config/alerting/<each-modified-file>.yml
   git rm homelab-apps/stacks/observability/config/alerting/recording-rules.yml   # if newly created
   docker kill --signal=HUP prometheus
   ```
2. **Revert restart-policy hardening**:
   ```
   git checkout homelab-apps/stacks/observability/docker-compose.yml
   cd /opt/homelab-apps/stacks/observability
   docker compose up -d prometheus
   docker inspect prometheus --format '{{json .HostConfig.RestartPolicy}}'
   # Expected: back to {"Name":"unless-stopped",...}
   ```
3. **Revert `PrometheusContainerDown` alert** — covered by step 1's `service-alerts.yml` revert.
4. **Revert runbook**:
   ```
   git checkout homelab-infra/docs/ha-replication-runbook.md
   git checkout homelab-infra/docs/observability-runbook.md   # if was modified, not newly created
   git rm homelab-infra/docs/observability-runbook.md         # if newly created
   ```
5. **Verify**: `promtool check config` SUCCESS post-rollback; `up{job="prometheus"}` returns 1; `pvesh get /cluster/ha/status/current` is unaffected.

Rollback restores the pre-6.10.3 state — including the two known-failure modes the story was meant to close. Roll back only if the rewritten rules genuinely produce wrong results that operator can't tune in-place.

## References

- **Adversarial finding source — R3 (label-mutation)**: Story 6.6 V4 drill review
- **Code-review finding source — L2 (clean-exit at 09:24:30Z)**: Story 6.6 code review
- **Story 6.10 (HA exporter — the rules being audited)**: `homelab-playbook/_bmad-output/implementation-artifacts/6-10-ha-state-prometheus-exporter.md`
- **Story 6.10.1 (alert tuning, parallel work)**: `homelab-playbook/_bmad-output/implementation-artifacts/6-10-1-ha-alert-tuning-post-soak.md`
- **Story 6.10.2 (pvesr alerting, parallel work)**: `homelab-playbook/_bmad-output/implementation-artifacts/6-10-2-pvesr-fail-count-alerting.md`
- **Story 6.6 (V4 drill, finding source)**: `homelab-playbook/_bmad-output/implementation-artifacts/6-6-validation-drill-v4-simulated-failover-via-migrate.md`
- **Story 7.11 (push channel — alertmanager severity routing)**: `homelab-playbook/_bmad-output/implementation-artifacts/7-11-alertmanager-and-ntfy-push-channel.md`
- **Story 6.2 (replication exporter — prior art for promtool + rule-file conventions)**: `homelab-playbook/_bmad-output/implementation-artifacts/6-2-verify-replication-state-and-deltas.md`
- **Memory: project_storage_monitoring.md** — observability conventions
- **Prometheus `changes()` reference**: <https://prometheus.io/docs/prometheus/latest/querying/functions/#changes>
- **Prometheus recording-rules best practices**: <https://prometheus.io/docs/practices/rules/>
- **Docker compose restart policy reference**: <https://docs.docker.com/compose/compose-file/05-services/#restart>
- **Docker healthcheck reference**: <https://docs.docker.com/reference/dockerfile/#healthcheck>
