---
status: backlog
epic: 6
story: 6.11
title: Node-level systemd unit health alerts (cron, chrony, sshd, pve-cluster, corosync, pvedaemon, pveproxy, pve-firewall)
created: 2026-04-25
author: BMad SM
depends-on: 6-2
---

# Story 6.11: Node-level systemd unit health alerts

Status: backlog

## Story

As an operator,
I want a cross-cutting alert pack that fires the moment any critical systemd unit on pve1, pve2, or pve3 enters `failed` or stops being `active` (cron, chrony, sshd, pve-cluster, corosync, pvedaemon, pveproxy, pve-firewall),
so that the "exporter-is-alive-but-cron-is-dead" silent-failure surface — which Story 6.10's `PVEHAExporterStale` only catches indirectly with a 3-min delay — becomes a paged incident with explicit per-unit clarity.

## Business value

Story 6.10 added `PVEHAExporterStale` and `PVEHAExporterMissing` as meta-monitoring guards on the HA exporter. They work, but they catch cron-daemon death **indirectly**: only after the textfile-collector file has not been rewritten for ≥3 minutes does Prometheus notice the exporter is stale. By that point the operator has lost the "what actually died" signal — `cron.service` is just one of dozens of units that could explain the staleness.

The same blind spot covers **every other cluster-critical systemd unit** on the PVE hosts. A failed `pve-cluster.service` (pmxcfs) would surface as cluster-wide weirdness 60+ seconds after the fact; a failed `corosync.service` would surface as quorum loss in `pvecm status` and (eventually) `PVEHAQuorumLost`, but only after the cluster has already decohered. A failed `chrony.service` would surface as alert-rule false-positives once clock drift exceeds tens of seconds — by which time multiple time-sensitive Story 6.10 / 6.2 rules are firing for the wrong reasons.

`prometheus-node-exporter` (already installed on all 3 PVE hosts by Story 6.2) **already exposes** `node_systemd_unit_state{name="<unit>",state="<state>"}` for every active unit — we just need the alert rules to consume it. This is therefore a low-implementation-cost, high-coverage gap closure: zero new exporters, zero new infrastructure, just a new rules file and a Grafana panel.

This story closes the gap:

1. **Define alert rules** per critical unit (cron, chrony, sshd, pve-cluster, corosync, pvedaemon, pveproxy, pve-firewall) using `node_systemd_unit_state{name="<unit>",state="active"} != 1`.
2. **Severity-tier the alerts** — `critical` for HA-critical units (`pve-cluster.service`, `corosync.service`); `warning` for ops-critical units (`cron.service`, `chronyd.service` or `chrony.service`, `ssh.service` or `sshd.service`, `pvedaemon.service`, `pveproxy.service`, `pve-firewall.service`).
3. **Reuse the Story 7.11 push chain** — no Alertmanager edits required; the existing severity tree routes critical → ntfy-urgent and warning → ntfy-default.
4. **Add a Grafana panel** "Node Systemd Health" so the operator can see at a glance whether all units are green across all 3 nodes.
5. **Synthetic-test the chain** by stopping `cron.service` on pve2 and observing the ntfy push within ≤2 minutes.

After 6.11 lands, `PVEHAExporterStale` becomes the **secondary** indicator for cron death (still fires after 3 min); the new `NodeSystemdUnitFailed{name="cron.service"}` is the **primary** indicator (fires after 2 min with explicit unit name in the push body). Same pattern for every other critical unit.

## Absorbed finding

This story **absorbs** Story 6.10's adversarial-review finding **R3 (MED severity)**: "Cron-daemon death is unobserved at the meta level. `PVEHAExporterStale` catches it indirectly but there's no `node_systemd_unit_state{name="cron.service"}` alert. A cron-daemon failure on any PVE node would silently freeze the HA-state metrics until the 3-min stale alert fires; the operator would have no per-unit diagnosis from the page."

R3 is one of three meta-monitoring gaps the 6.10 review surfaced; the others (R7 drill-window enforcement, R1/R8 alert-fan-out and quorum-match) are absorbed by Stories 6.9.1 and 6.10.1 respectively. Per spec rule 5, sprint-status YAML edits are an operator-side step.

## Acceptance Criteria

### AC-1: Pre-flight — observability stack live, node-exporter exposing `node_systemd_unit_state`

**Given** the cluster is 3/3 quorate (`pvecm status` on pve1: `Quorate: Yes`, `Total votes: 3`)
**And** Story 6.2's monitoring chain is green — `prometheus-node-exporter` active on pve1, pve2, pve3 (`systemctl is-active prometheus-node-exporter` returns `active` on each); `up{job="node-exporter-pve"} == 1` for all three hosts in Prometheus
**And** Story 7.11's push chain is live — `severity=critical` routes to `ntfy-urgent`, `severity=warning` routes to `ntfy-default`
**When** I capture baseline:
```
for n in pve1 pve2 pve3; do
  echo "=== $n ===" >> /tmp/systemd-units-pre-6-11.txt
  ssh $n "curl -s http://localhost:9100/metrics | grep -E '^node_systemd_unit_state' | head -20" >> /tmp/systemd-units-pre-6-11.txt
done
curl -s 'https://prometheus.bi-services.be/api/v1/rules' | jq '.data.groups[].name' > /tmp/prom-rule-groups-pre-6-11.txt
```
**Then** the baseline files exist
**And** `node_systemd_unit_state{name="cron.service",state="active"}` returns a value (`1` if active) for each of pve1/pve2/pve3 — proves the systemd collector is enabled (it is, by default in the Debian package; this is the AC that catches the unhappy case where someone disabled it).
**And** no rule group named `node-systemd.alerts` exists yet (this story creates it).

### AC-2: Verify node-exporter exposes `node_systemd_unit_state` for every target unit

**Given** AC-1 holds
**When** I query each target unit on each PVE node:
```
TARGET_UNITS=(cron.service chrony.service chronyd.service ssh.service sshd.service \
              pve-cluster.service corosync.service pvedaemon.service pveproxy.service pve-firewall.service)
for n in pve1 pve2 pve3; do
  for u in "${TARGET_UNITS[@]}"; do
    val=$(ssh $n "curl -s http://localhost:9100/metrics | grep -E '^node_systemd_unit_state{name=\"$u\".*state=\"active\"' | awk '{print \$2}'")
    echo "$n $u $val"
  done
done | tee /tmp/6-11-unit-coverage.txt
```
**Then** the output captures, for every (node, unit) pair, either:
- A value of `1` (unit is active and node-exporter sees it), OR
- An empty value with an explicit "not present" annotation in the dev notes (some units are conditional — e.g. on Debian `chrony` is the unit name, on others it is `chronyd`; `ssh.service` vs `sshd.service` similarly. Pick whichever name node-exporter actually emits per node).

**And** the dev surfaces an "actual unit names per node" mapping table in the Dev Agent Record so the alert rules in AC-3 use the correct unit names per the live environment, not assumed names. **Critical caveat**: Debian 12/13 PVE installs default to `chrony.service` and `ssh.service`; the rule expressions must match the actual emitted name. If the operator has remapped (e.g. via `systemctl alias`), the rule expression must reflect that.

**And** any unit that is genuinely absent (not just renamed) — e.g. if `pve-firewall.service` is masked because the operator does not run the PVE firewall — is documented in the runbook with rationale, and **its rule is omitted from AC-3 rather than firing perpetually**.

### AC-3: Add Prometheus rules per critical unit

**Given** AC-2 holds and the per-node unit name mapping is locked
**When** I create `homelab-apps/stacks/observability/config/alerting/node-systemd-alerts.yml` with the following rules under group `node-systemd.alerts`:

| Rule name | Unit | Severity | `for:` |
|---|---|---|---|
| `NodeSystemdPVEClusterFailed` | `pve-cluster.service` | `critical` | `2m` |
| `NodeSystemdCorosyncFailed` | `corosync.service` | `critical` | `2m` |
| `NodeSystemdCronFailed` | `cron.service` | `warning` | `2m` |
| `NodeSystemdChronyFailed` | (live name from AC-2) | `warning` | `2m` |
| `NodeSystemdSshFailed` | (live name from AC-2) | `warning` | `2m` |
| `NodeSystemdPvedaemonFailed` | `pvedaemon.service` | `warning` | `2m` |
| `NodeSystemdPveproxyFailed` | `pveproxy.service` | `warning` | `2m` |
| `NodeSystemdPveFirewallFailed` | `pve-firewall.service` (omit if masked) | `warning` | `2m` |

**Then** every rule expression is the form:
```promql
node_systemd_unit_state{name="<unit>",state="active"} != 1
```
**And** every rule has labels: `severity: <tier>`, `domain: node-systemd`
**And** every rule's `annotations.summary` includes `{{ $labels.instance }}` and `{{ $labels.name }}` so the operator sees both "which node" and "which unit" in the push body
**And** `promtool check rules` against the new file → SUCCESS (rule count = 7 or 8 depending on `pve-firewall` inclusion)
**And** SIGHUP-reload Prometheus on ct-docker-01: `docker kill --signal=HUP prometheus`
**And** `/api/v1/rules` shows all rules in group `node-systemd.alerts` as `inactive` (healthy baseline)

### AC-4: Severity allocation — HA-critical = critical, ops-critical = warning

**Given** AC-3 holds
**When** I review the severity allocation
**Then** the allocation maps cleanly to the cost-of-failure tiers:
- **`severity: critical`** (routes to `ntfy-urgent`, DND-bypass on phone): `pve-cluster.service`, `corosync.service`. Both directly threaten cluster quorum + HA. A failure here is a 3am-wake-the-operator event.
- **`severity: warning`** (routes to `ntfy-default`, respects DND): `cron.service`, `chrony.service` (or `chronyd.service`), `ssh.service` (or `sshd.service`), `pvedaemon.service`, `pveproxy.service`, `pve-firewall.service`. Important — without these the cluster's monitoring/management surface degrades — but a multi-hour delay before fixing is survivable; not a 3am event.

**And** the severity tiers are documented in the runbook so the operator can verify the routing intent matches the alert.

### AC-5: Synthetic test — stop cron.service on pve2 and observe the ntfy push within ≤2 min

**Given** AC-3 holds AND the cluster is healthy (no `node-systemd.alerts` rule currently firing)
**When** I deliberately stop `cron.service` on pve2 (the least-busy PVE node — picked to minimise blast radius for the synthetic test):
```
ssh pve2 "systemctl stop cron"
SYNTH_T0=$(date -u +%s)
echo "T+0: stopped cron.service on pve2 at epoch $SYNTH_T0" | tee /tmp/6-11-synth-evidence.txt
```
**Then** within **≤4 min** of `SYNTH_T0` (15s scrape + 2-min `for:` + 30s Alertmanager `group_wait` + ~30s ntfy delivery + buffer):
- `node_systemd_unit_state{name="cron.service",state="active",instance="pve2:9100"}` flips to `0`
- `NodeSystemdCronFailed` transitions `inactive` → `pending` → `firing` in `https://prometheus.bi-services.be/alerts`
- The operator's Android phone receives a push notification on the `homelab-alerts-default` topic (warning severity → ntfy-default, NOT urgent — confirms severity routing is correct) — push body contains `name=cron.service`, `instance=pve2:9100`
- The push lands within **≤90 s** of the rule transitioning to `firing`

**And** **rollback is performed immediately after the page is verified**:
```
ssh pve2 "systemctl start cron"
ssh pve2 "systemctl is-active cron"   # expect "active"
```
**And** within ≤2 min of rollback:
- `node_systemd_unit_state{name="cron.service",state="active",instance="pve2:9100"}` returns to `1`
- `NodeSystemdCronFailed` returns to `inactive`
- An auto-resolved notification is delivered to ntfy (`send_resolved: true` from Alertmanager default)

**And** evidence is captured at `/tmp/6-11-synth-evidence.txt` with timestamps for: `SYNTH_T0`, scrape-flip-detected, rule-pending, rule-firing, ntfy-push-received-on-phone, rollback-issued, scrape-flip-back, rule-inactive.

**Why pve2**: pve2 was the least-loaded PVE node at the time of Story 6.10's drill (no source-side replication jobs; only target). Stopping cron there for ~4 minutes has the smallest blast radius. If pve2 has gained source-side workloads since 6.10, pick the least-busy node at execution time and document the choice in the Dev Agent Record.

### AC-6: Rollback procedure documented

**Given** AC-3 through AC-5 hold
**When** I update the runbook
**Then** `homelab-infra/docs/ha-replication-runbook.md` (or a new sibling `node-systemd-runbook.md` if the runbook is getting unwieldy — Dev's call) contains:
- A "Node systemd unit alerts" section listing all rules, target units, and severities.
- The synthetic-test command from AC-5 (so the operator can re-run it themselves).
- The rollback command (revert the file + SIGHUP-reload Prometheus).
- A "Known limitations" subsection: e.g. if a unit transitions through `failed → reloading → active` in <2 min, the rule does not fire (correct behaviour — `for: 2m` absorbs flap; documented so the operator does not wonder why a brief stop did not page).

### AC-7: Grafana dashboard updated with "Node Systemd Health" panel

**Given** AC-3 holds
**When** I extend either the existing `ha-replication.json` dashboard (now broader than just replication) or add a new `node-health.json` dashboard — Dev's choice; recommendation is **new dashboard** to avoid bloating ha-replication
**Then** the dashboard contains at minimum:
- **"Node Systemd Health" stat-grid panel** — one stat per (node, unit) pair (3 nodes × 7-8 units = ~21-24 stats). Green if `state="active" == 1`, red otherwise. Use `node_systemd_unit_state{name=~"cron|chrony|chronyd|ssh|sshd|pve-cluster|corosync|pvedaemon|pveproxy|pve-firewall|.service",state="active"}` with regex match.
- **"Recent failures (last 24h)" table** — `changes(node_systemd_unit_state{state="failed"}[24h]) > 0` listing (node, unit, count).
**And** the dashboard JSON change is committed
**And** Grafana auto-provisioner picks up the change within `updateIntervalSeconds: 10` — no Grafana restart required

## Tasks

- [ ] **Task 0: Pre-flight + dependency verification** (AC-1)
  - Cluster quorate; node-exporter active on all 3 PVE nodes; Story 7.11 push chain green.
  - Capture `/tmp/systemd-units-pre-6-11.txt`, `/tmp/prom-rule-groups-pre-6-11.txt`.

- [ ] **Task 1: Discover live unit names on each PVE node** (AC-2)
  - For each of the 8 target units, query node-exporter on pve1/pve2/pve3 and capture which unit names are actually emitted.
  - Build the per-node mapping table in the Dev Agent Record.
  - Identify any genuinely-absent units (e.g. `pve-firewall.service` if masked) — note for AC-3 omission.

- [ ] **Task 2: Author `node-systemd-alerts.yml`** (AC-3, AC-4)
  - Create `homelab-apps/stacks/observability/config/alerting/node-systemd-alerts.yml`.
  - 7-8 rules in group `node-systemd.alerts` per the AC-3 table.
  - Severity allocation per AC-4.
  - `promtool check rules` → SUCCESS.
  - SIGHUP-reload Prometheus.
  - Verify all rules `inactive` at `/api/v1/rules`.

- [ ] **Task 3: Synthetic test — stop cron on pve2** (AC-5)
  - Stop `cron.service` on pve2; record `SYNTH_T0`.
  - Watch Prometheus + Alertmanager + phone.
  - Capture evidence at `/tmp/6-11-synth-evidence.txt` with all timestamps.
  - **CRITICAL: rollback within 4 min so cron can resume processing scheduled jobs.**
  - Verify rule auto-resolves and `send_resolved` notification lands.

- [ ] **Task 4: Update runbook** (AC-6)
  - Add "Node systemd unit alerts" section to `ha-replication-runbook.md` (or sibling).
  - Include synthetic-test command, rollback procedure, known limitations.

- [ ] **Task 5: Grafana dashboard** (AC-7)
  - Choose: extend ha-replication or new node-health dashboard. Document the choice.
  - Add the 2 panels per AC-7.
  - Deploy to ct-docker-01 dashboards directory; auto-provisioned.
  - Verify panels render correctly.

- [ ] **Task 6: Final-state evidence + status flip**
  - Diff `/tmp/systemd-units-pre-6-11.txt` vs post — should differ only in timestamps + the deliberately-paused-then-restored cron entry on pve2.
  - Append Dev Agent Record per Story 6.10 pattern.
  - Frontmatter `backlog → review`.

## Dev Notes

### `node_systemd_unit_state` metric shape

```
node_systemd_unit_state{name="cron.service",state="active"} 1
node_systemd_unit_state{name="cron.service",state="failed"} 0
node_systemd_unit_state{name="cron.service",state="activating"} 0
node_systemd_unit_state{name="cron.service",state="deactivating"} 0
node_systemd_unit_state{name="cron.service",state="inactive"} 0
```

For each (node, unit) pair, exactly one `state` row has value `1`. The rule expression `state="active" != 1` therefore catches every non-active state without having to enumerate them.

### Critical-unit rationale (severity tiers)

- **`pve-cluster.service`** (pmxcfs) — **critical**. The cluster filesystem; if it stops, all cluster operations stall (config writes, HA decisions, replication state, even `pveproxy` partially). Direct threat to HA. Story 6.10's `PVEHAExporterStale` would catch this within 3 min; this rule catches it within 2 min with explicit unit name.
- **`corosync.service`** — **critical**. Cluster-wide messaging + quorum. If it stops on a node, that node becomes non-quorate; HA fences it (softdog armed by Story 6.3). Story 6.10's `PVEHAQuorumLost` would catch this; this rule provides the per-node "why" diagnosis.
- **`cron.service`** — **warning**. Drives the textfile-collector exporters (Story 6.2's `pve-replication-exporter`, Story 6.10's `pve-ha-state-exporter`). Without cron, both exporters freeze; observability degrades. Survivable for hours; not a 3am event.
- **`chrony.service`** (or `chronyd.service` on some distributions) — **warning**. Time sync. Without it, clock drift accumulates; time-based PromQL evaluations (`time() - timestamp_seconds > N`) drift; `pve_replication_seconds_since_last_sync` and `pve_ha_exporter_last_run_timestamp_seconds` produce false positives. Story 6.2 R9 noted clock-skew alerting was deferred; this rule partially closes that gap (catches the unit-failure cause; doesn't catch slow drift while unit is "active" — that is still future work).
- **`ssh.service`** (or `sshd.service`) — **warning**. Operator access. Without it, the operator cannot remediate via SSH; must use the PVE web UI / IPMI. Survivable but degraded.
- **`pvedaemon.service`** — **warning**. The PVE API daemon (handles `pvesh` calls, including the ones the exporters use). If it stops, exporters fall through to the timeout/error path (Story 6.10 §Risk-1 mitigation). Indirect threat to monitoring.
- **`pveproxy.service`** — **warning**. The PVE web UI / external API surface. If it stops, the operator can still SSH and use `pvesh` locally; the web UI is gone. Survivable.
- **`pve-firewall.service`** — **warning**. The PVE firewall daemon. If it stops AND the firewall was enforcing rules, network policy degrades. Many homelab installs have it masked; if masked, omit the rule entirely (the rule would fire perpetually on a deliberately-masked unit, which is alert spam).

### Why no `severity: info` tier

The Story 7.11 routing has 3 tiers (critical, warning, info). All units in this story map cleanly to critical or warning per the cost-of-failure analysis above. Adding info-tier units (e.g. `unattended-upgrades.service`) would add noise without operator value at this stage; a future story can extend the unit set if a real noise/value tradeoff emerges.

### Alert rule template (for Task 2)

```yaml
groups:
  - name: node-systemd.alerts
    rules:
      - alert: NodeSystemdPVEClusterFailed
        expr: node_systemd_unit_state{name="pve-cluster.service",state="active"} != 1
        for: 2m
        labels:
          severity: critical
          domain: node-systemd
        annotations:
          summary: "pve-cluster.service is not active on {{ $labels.instance }}"
          description: |
            The Proxmox cluster filesystem (pmxcfs) is not in 'active' state on {{ $labels.instance }}.
            This threatens cluster quorum, HA decisions, and replication state.
            Operator steps:
              1. ssh {{ $labels.instance }} 'systemctl status pve-cluster.service'
              2. journalctl -u pve-cluster.service -n 100
              3. Check pmxcfs mount: mount | grep /etc/pve
              4. If safe: systemctl restart pve-cluster.service (note: this briefly
                 unmounts /etc/pve cluster-wide on this node).
      # ... 6-7 more rules following the same shape ...
```

### Live unit-name discovery

Run on each PVE node before authoring rules:

```
for u in cron chrony chronyd ssh sshd pve-cluster corosync pvedaemon pveproxy pve-firewall; do
  systemctl status "${u}.service" 2>/dev/null | head -1 && echo "  → present"
done
```

Or via node-exporter (matches what Prometheus actually sees):

```
curl -s http://localhost:9100/metrics | \
  grep -E '^node_systemd_unit_state\{name="(cron|chrony|chronyd|ssh|sshd|pve-cluster|corosync|pvedaemon|pveproxy|pve-firewall).service"' | \
  awk -F'"' '{print $2}' | sort -u
```

### Why this is a low-cost story

No new exporters, no new processes, no new package installs, no new network paths. Just:
1. One new rules file (`node-systemd-alerts.yml`).
2. One reload of Prometheus (SIGHUP — no downtime).
3. One Grafana panel addition.
4. Documentation updates.

The synthetic test is the only step that touches live state, and it is a 4-minute window of stopped cron on a single node — survivable and self-healing on rollback.

### Risk / failure modes

1. **`node_systemd_unit_state` metric absent for a target unit on a particular node** — e.g. operator masked `pve-firewall.service` deliberately. Mitigation: AC-2's discovery step + AC-3's omit-if-absent rule. Document the omission in the runbook.
2. **Unit name drift across distributions** — `chrony.service` on Debian 12+; `chronyd.service` on Red Hat-family. PVE 9 is Debian-based, so `chrony.service` is correct, but Task 1's discovery step is the safety net.
3. **Severity over-tuning** — a `chrony` failure at 3am is annoying but survivable; we deliberately route it to warning (DND-respecting), not critical (DND-bypass). If operator preferences change, edit the rule file. Documented.
4. **Synthetic-test blast radius** — stopping `cron.service` for 4 min means any cron job scheduled during that window does not run. On pve2 the only known cron jobs at the time of writing are the Story 6.2 replication exporter and the Story 6.10 HA-state exporter (both 1-5 min cadence). A missed exporter cycle is recovered on the next tick; no permanent state lost. **If a future cron job has tighter timing requirements (e.g. backup window), revisit Task 3's choice of pve2 + cron**.

### File layout

**homelab-apps/** (create):
- `stacks/observability/config/alerting/node-systemd-alerts.yml` (~80-100 lines, 7-8 rules)

**homelab-apps/** (modify or create):
- Either modify `stacks/observability/dashboards/ha-replication.json` (add Node Systemd Health row), or create `stacks/observability/dashboards/node-health.json` (recommended). Dev's call; document the choice.

**homelab-infra/** (modify):
- `docs/ha-replication-runbook.md` — add "Node systemd unit alerts" section (or create `node-systemd-runbook.md` sibling).

### Prior art references

- **Story 6.2** — `replication-alerts.yml` (the structural template for `node-systemd-alerts.yml`)
- **Story 6.10** — `ha-alerts.yml` (severity allocation pattern, dashboard extension pattern)
- **Story 7.11** — severity routing (no Alertmanager edits needed — this story consumes the existing tree)
- **Memory: pve9_ha_rules_migration** — informs which units PVE 9 cares about
- **Memory: pve_node_cooling** — informs that the homelab has been thermally stable; thus systemd-unit failures we observe will be operator-induced or genuine bugs, not thermal stress

## Test strategy

**Phase 1 (Task 0):** observation-only baseline.

**Phase 2 (Task 1):** read-only discovery — query node-exporter on all 3 nodes, build the unit-name mapping. No state change.

**Phase 3 (Task 2):** rule-file authoring + SIGHUP reload. Additive; if `promtool check rules` passes and reload is clean, no risk.

**Phase 4 (Task 3):** **the load-bearing AC.** Stop cron on pve2 for ≤4 min. The exporters will miss one tick (1-min cadence) — acceptable. Operator must be physically near phone for the duration so the AC-5 push verification is real-time. Roll back immediately on push receipt.

**Phase 5 (Tasks 4-6):** documentation + dashboard + status flip. No production state change.

## Security considerations

- No new credentials; no new network-facing services. The rule file is config-only.
- `node_systemd_unit_state` is read-only metadata about systemd state. No secrets, no PII.
- Annotations include unit names and node hostnames — operational metadata, safe to commit.
- Synthetic test stops `cron.service` for 4 min; cron jobs scheduled during that window don't run. If the operator has time-critical cron jobs (e.g. an unattended backup), reschedule the synthetic test or pick a different unit/node.

## Rollback procedure

If AC-3 produces unexpected behaviour (e.g. a rule fires immediately because a unit is genuinely failed and the operator forgot):
1. **Revert the rules file**: `git checkout homelab-apps/stacks/observability/config/alerting/node-systemd-alerts.yml`. SIGHUP-reload Prometheus.
2. **Revert dashboard**: `git checkout homelab-apps/stacks/observability/dashboards/node-health.json` (or the modified `ha-replication.json`). Auto-reprovisioned.
3. **Verify**: `/api/v1/rules` no longer lists `node-systemd.alerts` group; existing alert groups (`pve-ha.alerts`, `pve-replication.alerts`, etc.) still PASS.

Rollback is fully additive-reversal; no cluster state change, no HA membership change, no exporter change.

## References

- **Adversarial finding source**: Story 6.10 review, R3 MED finding (cron-daemon-death unobserved at meta level)
- **Structural template**: `homelab-playbook/_bmad-output/implementation-artifacts/6-2-verify-replication-state-and-deltas.md` and `6-10-ha-state-prometheus-exporter.md`
- **Push chain**: `homelab-playbook/_bmad-output/implementation-artifacts/7-11-alertmanager-and-ntfy-push-channel.md` — severity routing (no edits needed)
- **node-exporter installed**: Story 6.2 (textfile-collector + systemd collector default-on for the Debian package)
- **Existing alert templates**: `homelab-apps/stacks/observability/config/alerting/replication-alerts.yml`, `ha-alerts.yml`, `disk-alerts.yml`, `service-alerts.yml`
- **Existing Grafana dashboards**: `homelab-apps/stacks/observability/dashboards/ha-replication.json` (UID `ha-replication-6-2`)
- **node-exporter systemd collector docs**: <https://github.com/prometheus/node_exporter#enabled-by-default>
- **`node_systemd_unit_state` reference**: <https://github.com/prometheus/node_exporter/blob/master/collector/systemd_linux.go>
- **Memory: PVE 9 HA rules migration**: `/home/developer/.claude/projects/-home-developer-workspace-homelab/memory/project_pve9_ha_rules_migration.md`
- **Memory: PVE node cooling (thermal stability)**: `/home/developer/.claude/projects/-home-developer-workspace-homelab/memory/project_pve_node_cooling.md`
