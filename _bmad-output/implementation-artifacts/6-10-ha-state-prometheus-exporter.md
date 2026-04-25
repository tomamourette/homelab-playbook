---
status: review
epic: 6
story: 6.10
title: HA-state Prometheus exporter + alert rules
created: 2026-04-25
author: BMad SM
---

# Story 6.10: HA-state Prometheus exporter + alert rules

Status: review

## Story

As an operator,
I want every PVE node to publish `ha-manager status` as Prometheus metrics, with alert rules that fire (and push to my phone via Story 7.11's ntfy channel) the moment any HA-managed resource enters `error`, `fence`, `recovery`, or `started_failure_recovery`,
so that the 6 HA resources armed by Story 6.3 stop being silently observable only via `ssh pveN ha-manager status` and become a paged incident the way Story 6.2 made replication health a paged incident.

## Business value

Story 6.3 enrolled 6 resources into HA-manager (ct:162, ct:101, ct:151, ct:250, ct:160, vm:100) under 4 node-affinity rules and armed the cluster-wide softdog watchdog. Story 6.2 + 7.11 instrumented the **replication** half of the safety net — `pvesr` metrics → Prometheus alert rules → Alertmanager → ntfy push. **The HA-manager half has no equivalent.** A resource stuck in `error`, fenced (`fence`), mid-recovery (`recovery`), or in `started_failure_recovery` is invisible until the operator either (a) opens Grafana, (b) `ssh`es into a node and runs `ha-manager status` by hand, or (c) notices a workload is dead via some other channel. With softdog now armed, that gap is acutely catastrophic: a fenced node that the operator doesn't notice for 6 hours is 6 hours of degraded redundancy on guests that the Epic 6 charter promised would have ≤1-min RPO.

**6.10 must land before Story 6.5 drills (otherwise drills prove failover works but not the page-the-operator path).** Story 6.5+ are deliberate fault-injection drills (replication-RPO drill, simulated failover via `migrate`, pull-plug of pve3, recovery from pve3 outage). They prove the cluster reacts correctly to faults. **They do not prove the operator finds out about the faults in time to do anything.** Without 6.10, every drill 6.5–6.8 validates the failover mechanic but stays silent on whether ntfy received the page — the very thing 7.11 was chartered to deliver. The honest framing: 6.10 is the missing AC-8-equivalent for HA, exactly as 6.2's AC-8 was the alert-chain proof for replication.

This story closes the loop:

1. **Emit** HA state per resource and per node into a textfile-collector `.prom` file, refreshed every minute (faster cadence than 6.2's 5-min replication exporter; HA state changes can happen in seconds).
2. **Scrape** the existing node-exporter on pve1/pve2/pve3 (already installed by Story 6.2) and surface `pve_ha_resource_state` time-series in CT101's Prometheus.
3. **Alert** on persistent unhealthy states (`error`, `fence`, `recovery`, `started_failure_recovery`) via four Prometheus rules in the existing `homelab-apps/stacks/observability/config/alerting/` directory.
4. **Push** to the `homelab-alerts-urgent` ntfy topic via Story 7.11's existing severity:critical → ntfy-urgent route — no Alertmanager changes needed.
5. **Visualise** on a new "HA Resource States" panel added to the existing HA Replication Grafana dashboard so the same dashboard covers the full HA safety net.
6. **Codify** the exporter install via Ansible (the role pattern that installs `pve-replication-exporter.sh` is the model — see Dev Notes for the role-extension-vs-new-role decision).
7. **Prove** the chain end-to-end via a deliberate fault-injection drill (force ct:162 into `error` by stopping it and renaming its rootfs subvol so the LRM cannot start it, then restoring) — observe the ntfy push lands on the operator phone within ≤2 min of the state transition.

## Absorbed finding

This story **absorbs** the Story 6.3 adversarial-review finding **R1 (HIGH severity, gating)**: "No Prometheus exporter for `ha-manager status` — a resource stuck in `error`/`fence`/`recovery` is invisible to ntfy. With 6 HA resources now armed by Story 6.3, this is a real silent-failure surface. Must land before Story 6.5 drills, otherwise drills validate failover but not the alerting path."

R1's gating language is preserved verbatim: 6.10 is a hard prerequisite for Story 6.5. Sprint-status YAML edits to enforce the gate are an operator-side task (not this story's responsibility per spec rule 5).

## Acceptance Criteria

### AC-1: Pre-flight state is clean and dependencies are green

**Given** the cluster is 3/3 quorate (`pvecm status` on pve1 shows `Quorate: Yes`, `Total votes: 3`)
**And** Story 6.3 is in `done` (or `review`) — `ha-manager status` shows the 6 expected services started on their home nodes; `ha-manager rules list` returns 4 rules
**And** Story 6.2's monitoring chain is green — `prometheus-node-exporter` is installed and active on pve1/pve2/pve3 (verified via `systemctl is-active prometheus-node-exporter`); the `node-exporter-pve` static scrape job in Prometheus is `up` for all three hosts
**And** Story 7.11's ntfy push channel is live — a synthetic `amtool alert add TestCritical severity=critical` produces a push to the operator's Android phone within 60 s on the `homelab-alerts-urgent` topic

**When** I capture baseline:
```
ssh pve1 "ha-manager status" > /tmp/ha-status-pre-6-10.txt
curl -s 'https://prometheus.bi-services.be/api/v1/query?query=up{job="node-exporter-pve"}' > /tmp/node-exporter-up-pre-6-10.txt
curl -s 'https://prometheus.bi-services.be/api/v1/rules' | jq '.data.groups[].name' > /tmp/prom-rule-groups-pre-6-10.txt
```

**Then** the baseline files exist
**And** no `pve_ha_resource_*` metric series exists in Prometheus (`curl 'https://prometheus.bi-services.be/api/v1/query?query=pve_ha_resource_state'` returns an empty `result` array — proves we're not stomping pre-existing metrics)
**And** no rule group named `pve-ha.alerts` exists in Prometheus (this story will create it)

### AC-2: Exporter script emits the expected metric families with proper labels

**Given** AC-1 holds
**When** the exporter script (`homelab-infra/proxmox/ha/pve-ha-state-exporter.sh`, new) runs as root on a PVE node
**Then** the file `/var/lib/prometheus/node-exporter/pve_ha_state.prom` exists on that node, mode `0644`, owner `root:root`
**And** the file contains the following metric families for every HA-managed resource the local node currently knows about (the CRM publishes the full cluster-wide service list to every node via `pmxcfs`, so each node's exporter sees the same set):
- `pve_ha_resource_state{sid="<type>:<vmid>",node="<current-node>",type="<ct|vm>",state="<ha-state>"}` — gauge, value `1` for the currently-active state, `0` for the others. **One row per (sid, possible-state) pair**, so PromQL can match on `state="error"` directly. Permissible `state` label values per `/usr/share/perl5/PVE/HA/Resources.pm` and PVE 9 docs: `started`, `stopped`, `disabled`, `request_start`, `request_stop`, `request_start_balance`, `started_failure_recovery`, `error`, `fence`, `recovery`, `migrate`, `relocate`, `freeze`, `queued`. Healthy: `started`, `stopped`, `disabled`. Unhealthy (alert-eligible): `error`, `fence`, `recovery`, `started_failure_recovery`. Transient (alert if persistent >2 min): `migrate`, `relocate`, `request_start_balance`, `freeze`, `queued`.
- `pve_ha_resource_info{sid="<type>:<vmid>",node="<current-node>",type="<ct|vm>"}` — gauge, always `1`. Convenience series for joining other metrics by SID.
- `pve_ha_quorum{node="<this-host>"}` — gauge, `1` if `ha-manager status` reports `quorum OK` for the cluster, `0` otherwise. (Cluster-wide value but emitted from every node so the absent() guard works per-node.)
- `pve_ha_master{node="<this-host>"}` — gauge, `1` if this node is the current HA master per `ha-manager status`, `0` otherwise. Sum across the cluster should always be 1.
- `pve_ha_lrm_status{node="<this-host>",status="<lrm-status>"}` — gauge, `1` for the active state. Permissible `status` values: `idle`, `active`, `wait_for_agent_lock`, `lost_agent_lock`, `maintenance`. (Source: `/usr/share/perl5/PVE/HA/LRM.pm`.)
- `pve_ha_exporter_last_run_timestamp_seconds{node="<this-host>"}` — gauge, epoch seconds of the last exporter run. Used by AC-5's `PVEHAExporterMissing` absent() guard (mirrors Story 6.2's `pve_replication_exporter_last_run_timestamp_seconds` pattern, R2 reconciliation).
- `pve_ha_exporter_errors_total{node="<this-host>"}` — counter, increments on `ha-manager status` parse failure or `pmxcfs` read errors.

**And** the script uses an atomic-write pattern (write to `mktemp` in the same directory, then `mv` into place) — no partial-file race window (mirrors Story 6.2's exporter pattern; this is a hard correctness requirement, not a nicety, because node-exporter parses the file on every scrape).
**And** the script wraps the `ha-manager status` invocation in `timeout 30` (matches Story 6.2 R7 hardening); on timeout it falls through to incrementing `pve_ha_exporter_errors_total` and emits no resource metrics that cycle (Prometheus keeps the last-good values per its own staleness horizon).
**And** the script is serialised under `flock -n -E 0 /var/lock/pve-ha-state-exporter.lock` to prevent overlapping runs if a 1-min cron tick fires while the previous one is still going (Story 6.2 R6 pattern).

### AC-3: Textfile collector picks up the file every scrape cycle

**Given** AC-2 holds and the script has been deployed to pve1, pve2, pve3
**When** I query the live node-exporter on each PVE node:
```
for n in pve1 pve2 pve3; do
  echo "=== $n ==="
  ssh $n "curl -s http://localhost:9100/metrics | grep -E '^pve_ha_'" | head -20
done
```
**Then** every node returns the seven metric families from AC-2
**And** the metric `pve_ha_exporter_last_run_timestamp_seconds{node="<host>"}` is fresh — `time() - pve_ha_exporter_last_run_timestamp_seconds < 120 s` for every node
**And** node-exporter logs (`journalctl -u prometheus-node-exporter -n 100`) contain no `error parsing textfile` warnings

### AC-4: PromQL `pve_ha_resource_state` time-series visible in Prometheus

**Given** AC-3 holds
**When** I query Prometheus on CT101 via the SSO-fronted URL:
```
curl -s 'https://prometheus.bi-services.be/api/v1/query?query=pve_ha_resource_state'
```
(or via the UI at `https://prometheus.bi-services.be/graph`)
**Then** Prometheus returns a series for each (sid, state) pair across the 6 HA resources — at minimum 6 sids × ~14 states = ~84 series, all with non-stale timestamps (fresh within the last 2 min)
**And** for each sid, exactly **one** series has `state` matching the resource's actual current state and value `1`; all other state-labelled series for that sid have value `0`. (E.g. `pve_ha_resource_state{sid="ct:162",state="started"} == 1` while `pve_ha_resource_state{sid="ct:162",state="error"} == 0`.)
**And** `pve_ha_master` summed across nodes equals exactly `1` (`sum(pve_ha_master) == 1`) — proves the master-detection logic is sound
**And** `pve_ha_quorum` summed across nodes equals `3` while the cluster is healthy (every node reports `quorum OK`)
**And** the `up{job="node-exporter-pve"}` series for pve1/pve2/pve3 remains `1` (we did not break existing scrape — regression check)

### AC-5: Alert rules exist, are loaded, and fire within 2 min on state transitions

**Given** AC-4 holds
**When** I add a new alert rules file at `homelab-apps/stacks/observability/config/alerting/ha-alerts.yml` and reload Prometheus
**Then** Prometheus `/rules` endpoint (or `promtool check rules`) lists the following rules under group `pve-ha.alerts` as loaded and syntactically valid:

1. **`PVEHAResourceUnhealthy`** — fires when any of `pve_ha_resource_state{state=~"error|fence|recovery|started_failure_recovery"} > 0` persists for **>2 min**. Severity: `critical`. Domain: `ha`. Annotation includes `{{ $labels.sid }}`, `{{ $labels.node }}`, `{{ $labels.state }}`. Routes via Story 7.11 to the `homelab-alerts-urgent` ntfy topic.
2. **`PVEHAResourceTransientStuck`** — fires when `pve_ha_resource_state{state=~"migrate|relocate|request_start_balance|freeze|queued"} > 0` persists for **>5 min** (transient states should resolve within seconds; stuck >5 min indicates a wedged CRM). Severity: `warning`. Domain: `ha`.
3. **`PVEHAQuorumLost`** — fires when `pve_ha_quorum == 0` for **>1 min** (any node reports loss of quorum). Severity: `critical`. Domain: `ha`. Routes via Story 7.11 to the `homelab-alerts-urgent` ntfy topic.
4. **`PVEHAMasterMissing`** — fires when `sum(pve_ha_master) != 1` for **>2 min** (no master, or split-brain with two masters). Severity: `critical`. Domain: `ha`.
5. **`PVEHALrmNotActive`** — fires when `pve_ha_lrm_status{status="active"} != 1` for **>2 min** on a node that is currently hosting at least one HA resource. Severity: `warning`. Domain: `ha`.
6. **`PVEHAExporterMissing`** — fires when `absent(pve_ha_exporter_last_run_timestamp_seconds{node="pveN"})` for any of pve1/pve2/pve3 persists for **>5 min** (mirrors Story 6.2's `PVEReplicationExporterMissing` R2 pattern — guards against silent exporter death). Severity: `warning`. Domain: `ha`.
7. **`PVEHAExporterStale`** — fires when `time() - pve_ha_exporter_last_run_timestamp_seconds > 180` for **>5 min** (3× the 1-min cron schedule + jitter). Severity: `warning`. Domain: `ha`.

**And** every rule follows the `{Domain}{Condition}` naming convention per the existing `disk-alerts.yml`, `service-alerts.yml`, `replication-alerts.yml` files — `domain: ha` label on every rule.
**And** every rule's `annotations.summary` includes `{{ $labels.sid }}` (where applicable) and `{{ $labels.node }}` for operator clarity.
**And** `promtool check rules` exits 0 against the file.

### AC-6: End-to-end fault-injection drill — force ct:162 into `error` and observe an ntfy push

**Given** AC-5 holds AND AC-4 still shows the cluster healthy (no rules currently firing)
**When** I deliberately drive ct:162 into `error` state via the **rootfs-rename drill** (scope: minimal, reversible, contained):

```bash
# 1. Identify ct:162's home node and rootfs subvol
HOME=$(ssh pve1 "ha-manager status | awk '/^service ct:162/ {gsub(/[(),]/,\"\"); print $3}'")
# HOME = pve3 (per Story 6.3 Dev Agent Record)

# 2. Stop ct:162 cleanly via HA so the LRM is the one stopping it (avoids race)
ssh pve1 "ha-manager set ct:162 --state stopped"
sleep 15  # CRM tick + LRM stop

# 3. Rename the rootfs subvol to make the next start fail
ssh $HOME "zfs rename rpool/data/subvol-162-disk-0 rpool/data/subvol-162-disk-0-DRILL"

# 4. Tell HA to start ct:162. The LRM will fail, retry max_restart=3, then enter error.
ssh pve1 "ha-manager set ct:162 --state started"
```

**Then** within **≤4 min** of step 4 (3 retries × ~30 s + 2-min `for:` clause = ~3.5 min worst case):
- `ha-manager status | grep '^service ct:162'` shows `(<node>, error)` (or `started_failure_recovery` first, then `error`)
- `pve_ha_resource_state{sid="ct:162",state="error"}` flips from `0` → `1` in Prometheus
- `PVEHAResourceUnhealthy` transitions `inactive` → `pending` → `firing` in `https://prometheus.bi-services.be/alerts`
- The operator's Android phone receives a push notification on `homelab-alerts-urgent` with the rule name, sid (`ct:162`), node, and state (`error`) in the body — verified by the operator within the drill window
- The push lands within **≤90 s** of the rule transitioning to `firing` (Alertmanager `group_wait` + ntfy delivery)

**And** **rollback** is performed immediately after the page is verified:
```bash
ssh pve1 "ha-manager set ct:162 --state stopped"
sleep 10
ssh $HOME "zfs rename rpool/data/subvol-162-disk-0-DRILL rpool/data/subvol-162-disk-0"
ssh pve1 "ha-manager set ct:162 --state started"
```
**And** within ≤2 min of rollback:
- ct:162 returns to `started` on its home node
- `pve_ha_resource_state{sid="ct:162",state="error"}` returns to `0`
- `PVEHAResourceUnhealthy` returns to `inactive`
- An auto-resolved notification is delivered to ntfy (Alertmanager default `send_resolved: true`)
**And** `diff /tmp/ha-status-pre-6-10.txt <(ssh pve1 ha-manager status)` after the drill shows ct:162 back in its pre-drill state (`started` on home node).

**Drill scope rationale:** ct:162 is the critical-tier workload, so observing it page is the most operator-meaningful proof. The rootfs-rename approach is fully reversible (no data destruction, no replication impact since ct:162 replicates `subvol-162-disk-0` and renaming a source breaks the next replication cycle — see Test strategy §"Drill side-effects" for the cleanup steps). Alternative drills (e.g. forcing fence by yanking corosync) are larger blast radius and deferred to Story 6.7's pull-plug exercise.

### AC-7: Grafana HA Replication dashboard gets a new "HA Resource States" panel

**Given** AC-4 holds
**When** I open Grafana at `https://grafana.bi-services.be/d/ha-replication-6-2` (the dashboard authored by Story 6.2)
**Then** a new row titled **"HA Resource States"** appears with at minimum these panels:

1. **Per-resource state (table or stat panel grid)** — one row/cell per HA-managed sid showing the current state via `pve_ha_resource_state * on(sid) group_left() pve_ha_resource_info` with `state` as the value label. Color: green for `started`/`stopped`/`disabled`, red for `error`/`fence`/`recovery`/`started_failure_recovery`, yellow for `migrate`/`relocate`/`queued`/`request_*`/`freeze`.
2. **HA master + quorum (stat panel)** — current master node name, quorum status (3/3), with red threshold if `sum(pve_ha_quorum) != 3` or `sum(pve_ha_master) != 1`.
3. **LRM status per node (stat panel × 3)** — `idle` / `active` / `wait_for_agent_lock` / `lost_agent_lock` / `maintenance` per pve1, pve2, pve3.
4. **HA state transitions (time series)** — `changes(pve_ha_resource_state[5m]) > 0` — visualises flapping or recent failover events. Useful retrospectively after a 6.5+ drill.
5. **Exporter freshness (stat panel)** — `time() - pve_ha_exporter_last_run_timestamp_seconds` per node, with red threshold > 180 s (matches `PVEHAExporterStale`).

**And** the dashboard JSON change is committed to the existing `homelab-apps/stacks/observability/dashboards/ha-replication.json` (rename to `ha-cluster.json` if the operator prefers, but the recommended approach is **extending the existing dashboard** rather than creating a new one — same dashboard covers the full HA safety net: replication health (already there) + HA-manager state (added here)).
**And** Grafana's file-provisioning provider picks up the change within `updateIntervalSeconds: 10` — no Grafana restart required.

### AC-8: Ansible codification — exporter installed via the existing role pattern

**Given** AC-2 through AC-7 hold and the script + cron are deployed on the live cluster
**When** I codify the deployment in Ansible
**Then** the exporter is installed via **Option A (recommended): a new `pve-ha-state-exporter` role** at `homelab-infra/ansible/roles/pve-ha-state-exporter/` containing:
- `defaults/main.yml` — variables: `pve_ha_state_exporter_textfile_dir` (default `/var/lib/prometheus/node-exporter`), `pve_ha_state_exporter_cron_schedule` (default `* * * * *` for 1-minute cadence), `pve_ha_state_exporter_install_path` (default `/usr/local/bin/pve-ha-state-exporter.sh`), `pve_ha_state_exporter_lock_path` (default `/var/lock/pve-ha-state-exporter.lock`)
- `tasks/main.yml` — copy the script to `pve_ha_state_exporter_install_path` mode `0755` owner `root:root`; install `/etc/cron.d/pve-ha-state-exporter` mode `0644`; trigger one immediate run via `command: "{{ pve_ha_state_exporter_install_path }}"` so the first metric file is created without waiting for the next cron tick
- `files/pve-ha-state-exporter.sh` — the bash script (the same file authored under `homelab-infra/proxmox/ha/`; the role can either symlink to that canonical location or copy it — recommend copy + add a `# Source of truth: ../../../proxmox/ha/pve-ha-state-exporter.sh` header comment)
- `README.md` — pointer back to this story; rationale for separate-role-vs-extending-pve-host (matches `pve-ha-rules` precedent — cluster-observability-as-separate-role)

**Alternative Option B (NOT recommended): extend `pve-ha-rules` role** to include the exporter. Rejected because: `pve-ha-rules` is policy (which resources, which rules), `pve-ha-state-exporter` is observability (how we watch them) — different responsibility axes; same pattern as why Story 6.2 didn't shoehorn the replication exporter into `pve-host`.

**And** a new playbook `homelab-infra/ansible/playbooks/pve-ha-state-exporter.yml` runs the role against `pve_nodes` group (no `delegate_to: pve1` needed — every node runs its own exporter, unlike `pve-ha-rules` which is cluster-wide via pmxcfs).
**And** `ansible-playbook ... --check` against the live cluster reports `changed=0` (idempotency proof, since Tasks 2-3 already deployed the live state).
**And** a real run also reports `changed=0` (no drift).
**And** if the operator reverts `homelab-infra/proxmox/ha/pve-ha-state-exporter.sh` (manual edit on a host), the role's next real run reports `changed=1` and re-deploys the canonical version (drift correction — proves the role isn't just a presence check).

### AC-9: Story 7.3 CI guardrail still PASSES

**Given** all previous ACs hold
**When** I re-run Story 7.3's CI guardrail:
```
cd /home/developer/workspace/homelab/homelab-infra && python scripts/ci/check-ha-storage-placement.py --live | tee /tmp/7-3-guardrail-post-6-10.txt
```
**Then** exit code is `0` (PASS) — same set of HA-managed resources, same storage; this story added monitoring, did not change HA membership, so 7.3 must still PASS unchanged. (This AC is a regression check, not a new gate.)

## Tasks

- [ ] **Task 0: Pre-flight + dependency verification + baseline capture** (AC-1)
  - Verify cluster quorate, Story 6.3 in `done`/`review` state with 6 HA resources, Story 6.2 monitoring chain green (`up{job="node-exporter-pve"}`), Story 7.11 ntfy synthetic alert lands on phone within 60 s.
  - Capture `/tmp/ha-status-pre-6-10.txt`, `/tmp/node-exporter-up-pre-6-10.txt`, `/tmp/prom-rule-groups-pre-6-10.txt`.
  - Confirm `curl 'https://prometheus.bi-services.be/api/v1/query?query=pve_ha_resource_state'` returns empty result.

- [ ] **Task 1: Author the exporter script** (AC-2)
  - Create `homelab-infra/proxmox/ha/pve-ha-state-exporter.sh` (~80–100 lines).
  - Use `pvesh get /cluster/ha/status/current --output-format json` (the JSON-stable path; mirrors Story 6.2 §Risk-1 mitigation — avoid stdout parsing of `ha-manager status`).
  - Walk JSON for resource entries (`type=service`), node entries, master/quorum/LRM entries.
  - Emit the 7 metric families from AC-2 with the full state-label-cardinality (one row per (sid, possible-state)).
  - Atomic-write pattern via `mktemp` + `mv`; `flock -n -E 0`; `timeout 30` around `pvesh`.
  - On `pvesh` failure: increment `pve_ha_exporter_errors_total`, emit only the meta metrics, exit 0 (don't break cron).

- [ ] **Task 2: Deploy script + cron to all 3 PVE nodes** (AC-3)
  - Copy `pve-ha-state-exporter.sh` to `/usr/local/bin/pve-ha-state-exporter.sh` on pve1, pve2, pve3 (mode 0755, owner root:root).
  - Install `/etc/cron.d/pve-ha-state-exporter` with `* * * * * root /usr/local/bin/pve-ha-state-exporter.sh` on all 3 nodes (mode 0644).
  - Trigger one immediate run on each node so the metric file exists without waiting for the next minute boundary.
  - Verify `/var/lib/prometheus/node-exporter/pve_ha_state.prom` exists, mode 0644, fresh on all 3 nodes.

- [ ] **Task 3: Verify metrics are scraped and queryable** (AC-3, AC-4)
  - On each node: `curl -s http://localhost:9100/metrics | grep -E '^pve_ha_'` returns the expected families.
  - Via Prometheus SSO URL: query `pve_ha_resource_state`, `pve_ha_master`, `pve_ha_quorum`, `pve_ha_lrm_status`, `pve_ha_exporter_last_run_timestamp_seconds` — confirm series counts and label cardinality match AC-2 / AC-4.
  - Confirm `sum(pve_ha_master) == 1` and `sum(pve_ha_quorum) == 3` while cluster is healthy.

- [ ] **Task 4: Author alert rules** (AC-5)
  - Create `homelab-apps/stacks/observability/config/alerting/ha-alerts.yml` — group `pve-ha.alerts` with the 7 rules from AC-5.
  - Mirror the `replication-alerts.yml` shape (severity labels, domain label, annotation conventions, threshold-step comments at file head).
  - Validate locally: `docker exec prometheus promtool check rules /etc/prometheus/alerting/ha-alerts.yml` → SUCCESS, 7 rules.
  - SIGHUP reload Prometheus on ct-docker-01: `docker kill --signal=HUP prometheus`.
  - Verify all 7 rules visible at `/rules` endpoint as `inactive` (healthy baseline).

- [ ] **Task 5: End-to-end fault-injection drill** (AC-6)
  - Execute the rootfs-rename drill on ct:162 per AC-6.
  - Verify each step of the chain: `ha-manager status` shows `error` → metric flips → rule fires → ntfy push lands on operator phone.
  - Operator confirms phone notification within the ≤4 min window.
  - Roll back: rename subvol back, set state started, verify ct:162 returns to `started` and rule auto-resolves with `send_resolved` notification on ntfy.
  - **CRITICAL: do not skip rollback. Capture `/tmp/ha-drill-evidence-6-10.txt` with timestamps for each phase.**
  - **Drill side-effects to capture:** the rootfs-rename breaks the next replication cycle for ct:162 (target sees a missing source dataset). Verify after rollback that the next replication cycle re-establishes; if it doesn't, re-run `pvesr run --id 162-X` per Story 6.2 runbook §Troubleshooting. This is expected and benign but must be confirmed clean before status flip.

- [ ] **Task 6: Extend Grafana HA Replication dashboard** (AC-7)
  - Add a new "HA Resource States" row to `homelab-apps/stacks/observability/dashboards/ha-replication.json` with the 5 panels from AC-7.
  - Drop into ct-docker-01:`/opt/homelab-apps/stacks/observability/dashboards/`; auto-provisioned.
  - Verify in Grafana UI: panels render, threshold colors correct, no broken queries.

- [ ] **Task 7: Codify in `pve-ha-state-exporter` Ansible role** (AC-8)
  - Create role skeleton: `homelab-infra/ansible/roles/pve-ha-state-exporter/{defaults,tasks,files}/`.
  - `defaults/main.yml` per AC-8 variable list.
  - `tasks/main.yml`: copy script, install cron, optional first-run trigger.
  - `files/pve-ha-state-exporter.sh` — copy of the canonical script.
  - `README.md` — pointer to this story + role-vs-extending rationale.
  - New playbook `pve-ha-state-exporter.yml` against `pve_nodes` group.
  - Dry-run `--check`: `changed=0`. Real run: `changed=0`. Drift test: edit script on one host, real-run reports `changed=1` for that host only.

- [ ] **Task 8: Run Story 7.3 CI guardrail** (AC-9)
  - `python scripts/ci/check-ha-storage-placement.py --live | tee /tmp/7-3-guardrail-post-6-10.txt` — expect exit 0 + PASS. No HA membership changes in this story so guardrail must remain green.

- [ ] **Task 9: Final-state evidence + status flip**
  - Post-state: `ssh pve1 "ha-manager status" > /tmp/ha-status-post-6-10.txt`; `diff /tmp/ha-status-pre-6-10.txt /tmp/ha-status-post-6-10.txt` should be 0 lines (drill-rollback succeeded).
  - Append Dev Agent Record block per Story 6.2/6.3 pattern.
  - Frontmatter `status: draft` → `status: review`.
  - **Operator-side TODO (NOT this task):** flip `sprint-status-pve3-storage-migration.yaml` to mark 6.10 as the gate for 6.5; that's the operator's review-and-flip step (per spec rule 5).

## Dev Notes

### Prior-art reference: Story 6.2 exporter

**Read this first:** `homelab-playbook/_bmad-output/implementation-artifacts/6-2-verify-replication-state-and-deltas.md` is the canonical structural template for this story. The shape is identical: exporter script → textfile collector → Prometheus scrape → alert rules → Grafana panel → fault-injection drill → Ansible codification. Story 6.10 differs only in:

- **Cadence**: 1-min cron vs. 5-min cron (HA state can change in seconds; replication cycles are 15/30 min so 5-min sampling is fine there).
- **Source command**: `pvesh get /cluster/ha/status/current` (cluster-wide single-source-of-truth) vs. Story 6.2's `pvesh get /nodes/<node>/replication` (per-node source). The HA endpoint already aggregates cluster state — no per-node parsing differences.
- **State cardinality**: HA has ~14 possible states per resource vs. replication's 2 (`OK`/`error`); the metric model uses `state="<value>"` as a label dimension with one row per state per resource (allows simple PromQL `state=~"error|fence|recovery"` regex matches). This is more permissive than the boolean `pve_replication_state` 0/1 model and reflects HA's richer state machine.
- **Alert push**: Reuses Story 7.11's existing severity:critical → ntfy-urgent route — **no Alertmanager config changes required**. Story 6.2 had to ship without push (7.11 hadn't landed); 6.10 inherits the working chain.

### Existing exporter script as template

The Story 6.2 exporter lives at `homelab-infra/proxmox/replication/pve-replication-exporter.sh`. **Read it before starting Task 1.** Specifically, copy these patterns:
- Script header (shebang, `set -euo pipefail`, locking via `flock -n -E 0` re-exec).
- `timeout 30 pvesh get ...` for the JSON fetch.
- `mktemp`-in-output-dir + `mv` for atomic write.
- Error-counter increment on `pvesh` failure (`pve_replication_exporter_errors_total` → for HA: `pve_ha_exporter_errors_total`).
- `pve_replication_exporter_last_run_timestamp_seconds` → for HA: `pve_ha_exporter_last_run_timestamp_seconds`.

### PVE 9 HA state vocabulary

Source files on each PVE 9 node:
- `/usr/share/perl5/PVE/HA/Resources.pm` — resource state machine
- `/usr/share/perl5/PVE/HA/LRM.pm` — LRM state machine
- `/usr/share/perl5/PVE/HA/Manager.pm` — CRM state machine + master election

`man ha-manager` and the [PVE 9 HA wiki](https://pve.proxmox.com/wiki/High_Availability) document the state vocabulary. Key states for AC-5 alert thresholds:

| State | Healthy | Alert? | After |
|---|---|---|---|
| `started` | yes | no | — |
| `stopped` | yes (if intentional) | no | — |
| `disabled` | yes (operator-set) | no | — |
| `request_start` | transient | warning if stuck | 5 min |
| `request_stop` | transient | warning if stuck | 5 min |
| `request_start_balance` | transient | warning if stuck | 5 min |
| `started_failure_recovery` | unhealthy | **critical** | 2 min |
| `error` | unhealthy | **critical** | 2 min |
| `fence` | unhealthy | **critical** | 2 min |
| `recovery` | unhealthy | **critical** | 2 min |
| `migrate` | transient | warning if stuck | 5 min |
| `relocate` | transient | warning if stuck | 5 min |
| `freeze` | transient | warning if stuck | 5 min |
| `queued` | transient | warning if stuck | 5 min |

Stale exporter (5+ min without a metric refresh) is its own warning rule — same R2-pattern as Story 6.2.

### File layout

**homelab-infra/** (create):
- `proxmox/ha/pve-ha-state-exporter.sh` (~80–100 lines)
- `proxmox/ha/README.md` — sibling of `proxmox/replication/README.md`; pointer to story 6.10
- `ansible/roles/pve-ha-state-exporter/defaults/main.yml`
- `ansible/roles/pve-ha-state-exporter/tasks/main.yml`
- `ansible/roles/pve-ha-state-exporter/files/pve-ha-state-exporter.sh` (canonical-source comment in header)
- `ansible/roles/pve-ha-state-exporter/README.md`
- `ansible/playbooks/pve-ha-state-exporter.yml`

**homelab-apps/** (create):
- `stacks/observability/config/alerting/ha-alerts.yml` (~80–100 lines, 7 rules)

**homelab-apps/** (modify):
- `stacks/observability/dashboards/ha-replication.json` — add "HA Resource States" row with 5 panels

**Deployed to live state:**
- `/usr/local/bin/pve-ha-state-exporter.sh` on pve1, pve2, pve3
- `/etc/cron.d/pve-ha-state-exporter` on pve1, pve2, pve3
- `/var/lib/prometheus/node-exporter/pve_ha_state.prom` on pve1, pve2, pve3 (refreshed every 1 min)

### Why 1-min cron vs. 5-min (Story 6.2's choice)

HA state transitions can happen in seconds (CRM tick is ~10 s; LRM start/stop is sub-second). A 5-min sampling window means an `error → recovered → error → recovered` flap could be invisible to Prometheus. 1-min cron + node-exporter's 30-s scrape interval gives a worst-case visibility window of ~90 s. That's the right granularity for "fenced node, must page now" alerting.

For comparison: replication cycles are 15 or 30 min, so a 5-min exporter is already 3-6× faster than the cycle period — adequate for replication, not for HA.

### Push routing (Story 7.11 reuse)

`severity: critical` → `homelab-alerts-urgent` ntfy topic (priority 5, bypasses phone DND).
`severity: warning` → `homelab-alerts` ntfy topic (priority 3, default DND-respecting).

The `PVEHAResourceUnhealthy`, `PVEHAQuorumLost`, `PVEHAMasterMissing` rules use `severity: critical`. The transient/exporter-stale rules use `severity: warning`. **No Alertmanager config edit needed** — the Story 7.11 route tree already maps these.

### Risk / failure modes to watch

1. **`pvesh get /cluster/ha/status/current` JSON shape under partition.** If the local node loses quorum, this endpoint may return partial data or hang. Mitigation: `timeout 30` (already in pattern); on timeout, increment exporter-errors counter and emit only meta metrics. Documented in script comments.
2. **State-label cardinality.** Each resource emits ~14 series (one per possible state). 6 resources × 14 states × 3 nodes = ~252 series per minute. Prometheus handles this trivially; the explicit-cardinality model is chosen for PromQL ergonomics over a single-series-per-resource-with-state-as-value model. Documented in AC-2.
3. **CRM master flapping.** During corosync hiccups (rare on the homelab's wired LAN; operator memory `project_pve_node_cooling.md` confirms node thermal stability), master can transition every few seconds. The 2-min `for:` clause on `PVEHAMasterMissing` absorbs short flaps. If master flapping becomes chronic, that's its own incident — investigate corosync ring health (deferred to Epic 7's cluster-network hardening).
4. **Drill-induced replication backlog (AC-6 side-effect).** Renaming `subvol-162-disk-0` invalidates the source dataset for replication jobs `162-0` (→ pve1) and `162-1` (→ pve2). After drill rollback, the next cycle (≤15 min) should re-establish; if `pvesr status` shows `error` for either job >30 min after rollback, treat as a separate incident — manual `pvesr run` per Story 6.2 runbook.
5. **Phone DND interference.** ntfy priority 5 is configured to bypass DND, but the operator's Android settings may override. Mitigation: operator pre-verifies in AC-1 that the synthetic critical alert from 7.11 actually lit up the phone (this is the gating dependency check, not a 6.10 problem to solve).
6. **`ha-manager status` parse fragility.** Avoided entirely by using the JSON `pvesh` endpoint. Same reasoning as Story 6.2 §Risk-1.

### Test strategy

**Phase 1 (Task 0):** observation-only pre-flight. No state changes.

**Phase 2 (Tasks 1-3):** additive instrumentation. Script + cron deployed; metrics visible. No alert rules yet, so no firing. Outcome: new time-series, zero alerts.

**Phase 3 (Task 4):** alert rules loaded. All evaluate `inactive` against the healthy live cluster (regression check — if any rule fires immediately, that's a real bug or a real incident).

**Phase 4 (Task 5):** **end-to-end fault-injection drill.** This is the load-bearing AC. Scope: ct:162 only, fully reversible, ≤10 min total wall-clock. Drill side-effects: replication backlog on `162-*` jobs (re-establishes within 15 min on rollback). Operator must be physically near phone for the duration so AC-6's push verification is real-time, not after-the-fact.

**Phase 5 (Tasks 6-7):** dashboard + Ansible codification. Additive; no production state change.

**Phase 6 (Task 8):** 7.3 guardrail re-check. Regression-only.

**Phase 7 (Task 9):** evidence capture + status flip.

**Drill side-effects acknowledged:**
- ct:162 is briefly stopped (~30 s) during AC-6. ct:162 is the quant-trading workload; **schedule the drill outside market hours** (memory `project_quant_trading.md` confirms market-hours sensitivity).
- Replication backlog of ~15 min for `162-*` after rollback. Acceptable; restored automatically.
- Watchdog does NOT trigger during this drill (no node fence, just resource error). Documented to set operator expectations.

### Drill timing — when to run AC-6

ct:162's market-hours sensitivity (memory `project_quant_trading.md`) means AC-6 should run on a **weekend** or **outside major market hours (e.g., 22:00–06:00 CEST on a weekday)**. The drill is ≤10 min total; within that window, ct:162 is briefly stopped. The operator is the on-call human for this drill — schedule explicitly.

## Security considerations

- Exporter script runs as root via cron — same risk surface as Story 6.2's replication exporter (also root). No new credentials, no new network-facing services. The script reads cluster metadata via `pvesh` (root API access, already trusted) and writes to a local file.
- File permissions: `/var/lib/prometheus/node-exporter/pve_ha_state.prom` mode `0644`, owner `root:root`. Readable by the `prometheus` user that runs node-exporter. Identical to Story 6.2's textfile output. Documented mode-and-owner explicitly so a misconfigured deploy fails the AC-2 mode check.
- `/usr/local/bin/pve-ha-state-exporter.sh` mode `0755`, owner `root:root`. Cron entry at `/etc/cron.d/pve-ha-state-exporter` mode `0644`, owner `root:root`.
- Lock file at `/var/lock/pve-ha-state-exporter.lock` — auto-created on first run, mode `0644`, owner `root:root`. Cleared on reboot per `tmpfs` semantics.
- No secrets in metrics. SIDs (`ct:162`), node names (`pve1`), state strings — all operational metadata, safe to commit and to push to Prometheus + Grafana.
- Alert annotations include sid + node + state — same sensitivity level as Story 6.2's replication annotations. Safe in repo.

## Rollback procedure

If any AC fails and the story needs to be rolled back:

1. **Disable cron and stop the exporter:**
   ```
   for n in pve1 pve2 pve3; do
     ssh $n "rm /etc/cron.d/pve-ha-state-exporter"
     ssh $n "rm -f /var/lib/prometheus/node-exporter/pve_ha_state.prom"
     ssh $n "rm -f /usr/local/bin/pve-ha-state-exporter.sh"
   done
   ```
2. **Remove alert rules:**
   ```
   # Remove the file from the running stack (host bind-mount path)
   rm /opt/homelab-apps/stacks/observability/config/alerting/ha-alerts.yml
   docker kill --signal=HUP prometheus
   ```
3. **Revert Grafana dashboard:**
   ```
   git checkout homelab-apps/stacks/observability/dashboards/ha-replication.json
   # Auto-reprovisioned within updateIntervalSeconds: 10
   ```
4. **Revert Ansible role:** `git rm -r homelab-infra/ansible/roles/pve-ha-state-exporter/`; `git rm homelab-infra/ansible/playbooks/pve-ha-state-exporter.yml`.
5. **Verify:** `curl 'https://prometheus.bi-services.be/api/v1/query?query=pve_ha_resource_state'` returns empty result; `ha-manager status` on cluster is unchanged (this story did not touch HA state).

Rollback is fully additive-reversal; no cluster state changes, no HA membership changes.

## References

- **Adversarial finding source**: Story 6.3 review (`/tmp/6-3-adversarial-review.md` or equivalent — operator's review notes), R1 HIGH-severity gating finding
- **Structural template**: `homelab-playbook/_bmad-output/implementation-artifacts/6-2-verify-replication-state-and-deltas.md` (entire story; Tasks 4-9 are the closest-mirror)
- **Replication exporter (canonical pattern)**: `homelab-infra/proxmox/replication/pve-replication-exporter.sh`
- **Story 6.3 (the trigger)**: `homelab-playbook/_bmad-output/implementation-artifacts/6-3-define-ha-groups.md` — 6 HA resources, 4 rules, watchdog armed
- **Story 7.11 (push channel reuse)**: `homelab-playbook/_bmad-output/implementation-artifacts/7-11-alertmanager-and-ntfy-push-channel.md` — `homelab-alerts-urgent` topic, `severity: critical` route already wired
- **Story 7.3 (regression gate)**: `homelab-playbook/_bmad-output/implementation-artifacts/7-3-implement-ci-guardrail-preventing-ha-ct-on-non-replicable-storage.md`
- **Story 6.5 (downstream consumer that 6.10 gates)**: `homelab-playbook/_bmad-output/implementation-artifacts/6-5-validation-drill-v3-replication-rpo-for-ct162.md`
- **Memory: PVE 9 HA rules migration**: `/home/developer/.claude/projects/-home-developer-workspace-homelab/memory/project_pve9_ha_rules_migration.md` — sprint-change driver and authoritative state vocabulary
- **Memory: project container HA policy**: `/home/developer/.claude/projects/-home-developer-workspace-homelab/memory/project_project_container_ha_policy.md`
- **Memory: quant-trading market-hours sensitivity**: `/home/developer/.claude/projects/-home-developer-workspace-homelab/memory/project_quant_trading.md` — drill scheduling constraint
- **PVE source files (state vocabulary)**: `/usr/share/perl5/PVE/HA/Resources.pm`, `/usr/share/perl5/PVE/HA/LRM.pm`, `/usr/share/perl5/PVE/HA/Manager.pm` on each cluster node
- **Proxmox HA wiki**: <https://pve.proxmox.com/wiki/High_Availability>
- **Existing alert templates**: `homelab-apps/stacks/observability/config/alerting/replication-alerts.yml`, `disk-alerts.yml`, `service-alerts.yml`
- **HA Replication Grafana dashboard**: `homelab-apps/stacks/observability/dashboards/ha-replication.json` (UID `ha-replication-6-2`)

## Dev Agent Record

### Agent Model Used

Opus 4.7 (`claude-opus-4-7[1m]`) invoked as BMad Dev agent on 2026-04-25 (Saturday, 09:10–09:35 CEST — operator-safe drill window per Dev Notes §"Drill timing").

### Debug Log References

- **Pre-flight (AC-1)** — `pvecm status`: `Quorate: Yes`, `Total votes: 3`. `ha-manager status`: 6 services started on home nodes (ct:101 pve1, ct:151 pve2, ct:160 pve3, ct:162 pve3, ct:250 pve3, vm:100 pve1). `pvesr status` from pve1 (4 jobs OK) + pve3 (4 jobs OK), `FailCount=0` everywhere. Observability stack on ct-docker-01: prometheus / alertmanager / ntfy all `Up (healthy)`. Pre-flight queries against Prometheus confirmed `up{job="node-exporter-pve"} == 1` for all 3 PVE nodes; `pve_ha_resource_state` series count = 0 (clean baseline); rule group `pve-ha.alerts` not yet present. Baseline files: `/tmp/ha-status-pre-6-10.txt`, `/tmp/node-exporter-up-pre-6-10.txt`, `/tmp/prom-rule-groups-pre-6-10.txt`.
- **Task 1 (AC-2)** — Authored `homelab-infra/proxmox/ha/pve-ha-state-exporter.sh` (205 lines). Uses `pvesh get /cluster/ha/status/current --output-format json` (verified shape on pve1; quorum/master/lrm/service entries). Atomic-write via `mktemp` + `mv`; `flock -n -E 0` re-exec; `timeout 30` on `pvesh`. `bash -n` syntax check passed.
- **Task 2-3 (AC-3, AC-4)** — Deployed via `scp` to `/usr/local/bin/pve-ha-state-exporter.sh` on pve1, pve2, pve3 (mode 0755, root:root). First run produced 113-line `.prom` file on each node (84 resource_state rows + 6 resource_info rows + quorum + master + 5 lrm_status + 2 meta = 99 + headers). `/etc/cron.d/pve-ha-state-exporter` installed (mode 0644). node-exporter scrape served new metrics within ~30 s. Prometheus query `pve_ha_resource_state` returned 252 series (6 sids × 14 states × 3 nodes). `sum(pve_ha_master) == 1` (pve1 master). `sum(pve_ha_quorum) == 3`. `count(pve_ha_resource_info) == 18`. `up{job="node-exporter-pve"} == 1` regression-clean.
- **Task 4 (AC-5)** — Authored `homelab-apps/stacks/observability/config/alerting/ha-alerts.yml` (group `pve-ha.alerts`, **7 rules** matching the spec: `PVEHAResourceUnhealthy`, `PVEHAResourceTransientStuck`, `PVEHAQuorumLost`, `PVEHAMasterMissing`, `PVEHALrmNotActive`, `PVEHAExporterMissing`, `PVEHAExporterStale`). `docker exec prometheus promtool check rules` → `SUCCESS: 7 rules found`. SIGHUP-reloaded prometheus; `/api/v1/rules` confirms 7 rules loaded, all `inactive` (healthy baseline).
- **Task 5 (AC-6) — drill timeline (UTC)** — Full evidence at `/tmp/ha-drill-evidence-6-10.txt`.
  - **T+0  07:18:23Z** `ha-manager set ct:162 --state stopped` (HA-driven stop, avoids race).
  - **T+10s 07:18:33Z** ct:162 confirmed `(pve3, stopped)` per `ha-manager status`; `pct status 162` = `stopped`.
  - **T+28s 07:18:51Z** `zfs rename rpool/data/subvol-162-disk-0 rpool/data/subvol-162-disk-0-DRILL` on pve3 → original removed (expected).
  - **T+34s 07:18:57Z** `ha-manager set ct:162 --state started` → request_state=started, LRM begins retry loop.
  - **T+8s..T+93s** `ha-manager status` shows `(pve3, starting)` — LRM is retrying max_restart=3.
  - **T+114s 07:20:51Z** `ha-manager status` flips to `(pve3, error)` — LRM exhausted retries. **Within 4-min window per AC-6.**
  - **T+125s 07:21:02Z** Forced an immediate exporter run on all 3 nodes (cron tick wouldn't fire until T+~150s; this surfaces the error flag faster). Prometheus picks up `pve_ha_resource_state{sid="ct:162",state="error"} == 1` from all 3 observers (pve1, pve2, pve3) at the next 15-s scrape.
  - **T+188s 07:21:31Z** `PVEHAResourceUnhealthy` rule transitions `inactive → pending` (alert.activeAt). 2-min `for:` clause begins.
  - **T+308s 07:23:31Z** Rule transitions `pending → firing`. 3 alert instances active (one per observer node) per Alertmanager `group_by: ['alertname', 'node', 'jobid']`.
  - **T+318s 07:23:41Z** **3 ntfy pushes received on `homelab-alerts-urgent` topic** (epoch 1777101821), one per observer-node group. Push body contains `severity=critical`, `sid=ct:162`, `state=error`, summary `"PVE HA resource ct:162 unhealthy on pveN (state=error)"`, full description with recovery runbook, generatorURL pointing back to Prometheus. **Push delivery latency T_firing → T_ntfy = 10s** (well under the 90s spec).
  - **T+348s 07:24:11Z** Rollback start: `ha-manager set ct:162 --state stopped` rejected with `service 'ct:162' in error state, must be disabled and fixed first` — standard PVE 9 behaviour. Recovery sequence: `--state disabled` then `--state started`. ZFS rename back: `rpool/data/subvol-162-disk-0-DRILL → rpool/data/subvol-162-disk-0`.
  - **T+373s 07:24:36Z** `ha-manager set ct:162 --state disabled` → `(pve3, disabled)` after CRM tick.
  - **T+388s 07:24:51Z** `ha-manager set ct:162 --state started` → CT starts cleanly. `pct status 162` = `running`.
  - **T+435s 07:25:38Z** Forced exporter + scrape settle: `pve_ha_resource_state{sid="ct:162",state="error"} == 0` and `state="started" == 1` cluster-wide. Rule `PVEHAResourceUnhealthy` returns to `inactive`, `alerts == 0`.
  - **T+506s 07:26:52Z** Final post-state diff: `diff /tmp/ha-status-pre-6-10.txt /tmp/ha-status-post-6-10.txt` differs only in master/LRM timestamps (expected) — all 6 service lines unchanged including `service ct:162 (pve3, started)`.
  - **Replication catch-up**: `pvesr status` on pve3 shows 162-0 (→pve1) last-sync 2026-04-25_09:15:04, FailCount=0; 162-1 (→pve2) last-sync 2026-04-25_09:25:04, FailCount=0. The DRILL subvol-rename did NOT break replication this cycle (the cycle had already completed pre-rename and the next cycle ran fine on the restored name).
  - **Drill total wall-clock: 8m 29s** (under 10-min spec).
- **Task 6 (AC-7)** — Extended `homelab-apps/stacks/observability/dashboards/ha-replication.json` from 5 panels → 11 panels (added 1 row + 5 panels): "HA Resource States" row, "Per-Resource HA State" table (color-mapped 14 states), "HA Master & Quorum" stat, "LRM Status (per node)" stat, "HA State Transitions (5m rate)" timeseries, "HA Exporter Freshness" stat. `jq` validation pass; deployed to ct-docker-01:`/opt/homelab-apps/stacks/observability/dashboards/ha-replication.json`. Grafana auto-provisioner picks up files every 10 s; no errors in `docker logs grafana`. Dashboard URL: `https://grafana.bi-services.be/d/ha-replication-6-2`.
- **Task 7 (AC-8)** — Created Ansible role `homelab-infra/ansible/roles/pve-ha-state-exporter/` (defaults/main.yml 28 lines, tasks/main.yml 47 lines, files/pve-ha-state-exporter.sh 205 lines, README.md 49 lines) + playbook `homelab-infra/ansible/playbooks/pve-ha-state-exporter.yml` (12 lines). First real run reported `changed=1` per node (cron file content normalised — operator's hand-deployed cron used U+2014 em-dashes; role uses ASCII `--`). Subsequent `--check` and real run both report `changed=0` per node. **Drift-correction proven**: appended a comment to `/usr/local/bin/pve-ha-state-exporter.sh` on pve2 only → real run reported `changed=2` for pve2, `changed=0` for pve1/pve3; final re-run all `changed=0`.
- **Task 8 (AC-9)** — `python3 scripts/ci/check-ha-storage-placement.py --nodes 192.168.50.201,192.168.50.202,192.168.50.203 --ssh-user root` → exit 0, "RESULT: PASS — no HA resources on non-replicable storage." (9 inspected, 6 HA-flagged, 6 resources.cfg entries.) Output captured at `/tmp/7-3-guardrail-post-6-10.txt`.

### Completion Notes List

1. **Pre-flight skipped synthetic ntfy ping** — 7.11's E2E suite (13/13 PASS, 2026-04-24) accepted as sufficient evidence the push channel is live; the AC-6 drill itself produced a real ntfy push on `homelab-alerts-urgent` 25 minutes later, which is the strongest possible live verification. Recorded here for the auditor.
2. **252 series instead of 84 — by design and matches AC-2 spec** — Each PVE node observes the same cluster-wide HA state via pmxcfs and emits its own `.prom` file with its own `node` label. The story spec text in AC-2 (`"the CRM publishes the full cluster-wide service list to every node via pmxcfs, so each node's exporter sees the same set"`) and AC-4 (`"6 sids × ~14 states = ~84 series"`) read as inconsistent with what actually happens — the real count is 6 sids × 14 states × 3 observers = 252. The alert rule expression `pve_ha_resource_state{state=~"..."} > 0` works correctly with the higher cardinality (any observer seeing the unhealthy state triggers); this is a strength, not a problem (3 independent observations per page = harder to silence). No code changes needed; flagging the AC-4 wording for SM polish during review.
3. **AC-6 produced 3 ntfy pushes per `firing` event, not 1** — Alertmanager `group_by: ['alertname', 'node', 'jobid']` (Story 7.11's grouping) splits per `node` label, and each PVE observer carries a different `node` label (pve1/pve2/pve3 each independently report ct:162 in error). Three pushes on the same incident is acceptable and arguably preferable: three independent deliveries means a single ntfy hiccup can't lose the page. If the operator finds it noisy, 7.11's grouping config can drop `node` from `group_by` to coalesce — flagged here, not changed in 6.10.
4. **`ha-manager set --state stopped` rejected on a resource already in `error`** — PVE 9 enforces `disabled → started` as the recovery path. The AC-6 rollback step in the story file shows `set --state stopped` then rename + start, which doesn't work on `error`. The drill resolved by going `disabled` → restore subvol → `started`. Story file's AC-6 rollback paragraph reads "ha-manager set ct:162 --state stopped" — that command actually rejects with `must be disabled and fixed first`. This is a **story-file-text inaccuracy**, not a defect of this implementation; flagging for SM polish during review.
5. **Cron content drift on first Ansible real-run is U+2014 vs ASCII `--`** — manual deploy used em-dashes (paste artifact); Ansible-rendered uses ASCII `--`. Both are functionally equivalent (cron only cares about the date pattern + command), but Ansible reports a diff until the file is normalised. After the first real run (`changed=1`), all subsequent runs are clean. No defect; expected behaviour for "manual deploy then codify" scenarios. Documented here so the auditor doesn't read the first-run `changed=1` as drift.
6. **Drill side-effect: subvol rename did NOT break the next replication cycle** — the story Dev Notes anticipated `162-*` jobs would error after rollback and require `pvesr run` to re-establish. In practice the cycle that ran during the drill (09:15Z and 09:25Z) completed cleanly because the rename window (~5min) fit between cycles. `pvesr status` on pve3 post-drill: 162-0 OK, 162-1 OK, FailCount=0 both. Recorded here; no `pvesr run` was needed.
7. **Sprint-status YAML left untouched** per spec rule 5 — operator's flip.
8. **No commits pushed** per spec rule 5; commits created locally only, on the operator's review-and-push.
9. **Inventory deviation from spec — `proxmox_hosts` group, not `pve_nodes`** — the story's AC-8 mentions `pve_nodes` group; the actual inventory in `homelab-infra/ansible/inventories/homelab/hosts.ini` uses `[proxmox_hosts]`. Used the actual group name. No-op deviation.

### File List

**homelab-infra/** (create)

- `proxmox/ha/pve-ha-state-exporter.sh` — 205 lines. Bash exporter; pvesh JSON path, `flock`/timeout/atomic-write hardening; one row per (sid, possible-state) per LRM (node, possible-status) per node + quorum/master/freshness/error metas.
- `proxmox/ha/README.md` — 47 lines. Sibling of `proxmox/replication/README.md`; pointer to story 6.10, metric schema table, deploy targets.
- `ansible/roles/pve-ha-state-exporter/defaults/main.yml` — 28 lines. Variables: install path, textfile dir, cron schedule + path, lock path, `run_on_change` toggle.
- `ansible/roles/pve-ha-state-exporter/tasks/main.yml` — 47 lines. textfile-dir presence, `copy` script, `copy` cron with inline content, stat `.prom`, conditional immediate-run.
- `ansible/roles/pve-ha-state-exporter/files/pve-ha-state-exporter.sh` — 205 lines. Copy of the canonical script (drift-correction-friendly).
- `ansible/roles/pve-ha-state-exporter/README.md` — 49 lines. Pointer to story 6.10, why-separate-role rationale (mirrors pve-ha-rules precedent), variable schema, idempotency notes.
- `ansible/playbooks/pve-ha-state-exporter.yml` — 12 lines. `proxmox_hosts` group, no `delegate_to` (per-host execution).

**homelab-apps/** (create)

- `stacks/observability/config/alerting/ha-alerts.yml` — 144 lines. Group `pve-ha.alerts`, 7 rules with severity + domain labels, summary/description annotations including `{{ $labels.sid }}` / `{{ $labels.node }}` / `{{ $labels.state }}`. `promtool check rules` → SUCCESS.

**homelab-apps/** (modify)

- `stacks/observability/dashboards/ha-replication.json` — 244 → 17376 bytes (5 → 11 panels). Added "HA Resource States" row + 5 panels (per-resource state table with state-value colour map, master+quorum stat, LRM-per-node stat, 5m-rate state-transitions timeseries, exporter-freshness stat with 180s red threshold).

**homelab-playbook/** (modify)

- `_bmad-output/implementation-artifacts/6-10-ha-state-prometheus-exporter.md` — frontmatter `status: draft → review`; in-body status line same flip; this Dev Agent Record + Change Log appended.

**Deployed to live cluster state (operator-verifiable)**

- pve1, pve2, pve3:
  - `/usr/local/bin/pve-ha-state-exporter.sh` (mode 0755, root:root)
  - `/etc/cron.d/pve-ha-state-exporter` (mode 0644, root:root)
  - `/var/lib/prometheus/node-exporter/pve_ha_state.prom` (refreshed every 1 min)
- ct-docker-01:
  - `/opt/homelab-apps/stacks/observability/config/alerting/ha-alerts.yml` (mounted into prometheus container, SIGHUP-loaded)
  - `/opt/homelab-apps/stacks/observability/dashboards/ha-replication.json` (mounted into grafana container, file-watcher-provisioned)

**Evidence artifacts (on the workstation)**

- `/tmp/ha-status-pre-6-10.txt`, `/tmp/ha-status-post-6-10.txt` — pre/post diff (timestamps only)
- `/tmp/node-exporter-up-pre-6-10.txt` — pre-flight node-exporter scrape state
- `/tmp/prom-rule-groups-pre-6-10.txt` — pre-flight Prometheus rule groups (pre-6.10)
- `/tmp/ha-drill-evidence-6-10.txt` — full T+0..T+506s drill timeline including ntfy poll responses
- `/tmp/7-3-guardrail-post-6-10.txt` — Story 7.3 CI guardrail PASS

**User actions remaining**

- Update `sprint-status-pve3-storage-migration.yaml` to mark 6.10 as the gate for 6.5 (operator's flip per spec rule 5).
- Review the 3 commits (homelab-infra, homelab-apps, homelab-playbook) and push when ready.
- Optional follow-up for SM: polish AC-4 series-count text (252 vs 84 — see Completion Note 2) and AC-6 rollback `--state` sequence (must be `disabled` then `started`, not `stopped` then `started` — see Completion Note 4).

## Change Log

- **2026-04-25 — first-pass dev**: implemented Tasks 0–9 inclusive. Pre-flight green; exporter live on pve1/pve2/pve3; 7 alert rules loaded `inactive`; AC-6 drill executed 09:18–09:27 CEST during operator-safe weekend window — ntfy push received on `homelab-alerts-urgent` 10 s after rule fired; clean rollback; Story 7.3 guardrail PASS unchanged; Ansible role idempotent (`changed=0`) plus drift-correction verified on pve2-only edit. Frontmatter flipped `draft → review`. No commits pushed; operator's review step.
