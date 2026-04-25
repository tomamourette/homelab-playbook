---
status: backlog
epic: 6
story: 6.10.1
title: HA alert tuning post-soak (de-dupe + quorum-match transient states)
created: 2026-04-25
author: BMad SM
depends-on: 6-10
---

# Story 6.10.1: HA alert tuning post-soak

Status: backlog

## Story

As an operator,
I want the HA alert chain (Story 6.10) tuned against ≥2 weeks of real-world soak data so that genuine incidents produce **one** legible push per logical event rather than per-observer fan-out, and transient states (`recovery`, `relocate`, `migrate`) require quorum-of-observers before paging,
so that operator alert fatigue does not erode the value of the Story 6.10 + 7.11 push chain that the rest of Epic 6 now relies on.

## Business value

Story 6.10 shipped with a deliberately verbose alert posture: every observer (pve1, pve2, pve3) emits its own `pve_ha_resource_state` series, and Alertmanager's `group_by: ['alertname', 'node', 'jobid']` (Story 7.11) splits per `node` label. Story 6.10's AC-6 drill produced **3 ntfy pushes for a single ct:162-error event** (one per observer node, T+318s evidence in the drill log). The code-review accepted this as redundancy worth keeping until a soak proved its noise cost; the adversarial review flagged it as a HIGH-severity alert-fatigue risk that warrants tuning.

Worst-case math: a real incident touching 5 simultaneous resources would produce **5 alerts × 3 observers = 15 ntfy pushes/min**. An operator who silences ntfy to escape that flood loses the next critical alert. That is the textbook alert-fatigue failure mode and Epic 6's whole charter (paged-not-audited HA) collapses if the operator silences the channel.

The same review (R8 MED) noted that observer-node consensus uses ANY-match (`{state="error"} > 0`) — a single observer flapping during a pmxcfs partition is enough to fire. For hard-fail states (`error`, `fence`, `started_failure_recovery`) ANY-match is correct; for transient states (`recovery`, `relocate`, `migrate`, `request_*`) it is over-eager. Quorum-match (`>=2` observers reporting the same unhealthy state) dampens partition-induced false positives without sacrificing real-incident detection.

This story closes both gaps after a 2-week soak so the tuning is data-driven, not guess-driven:

1. **Coalesce per-event multi-observer pushes** by dropping `node` from `group_by` for `pve-ha.*` alerts (group by `['alertname', 'sid']` instead) — one logical event ⇒ one push.
2. **Quorum-match for transient states** (`>=2` observers) — keep ANY-match for hard-fail states (`error`, `fence`).
3. **`for:` duration tuning** based on observed false-positive rate — extend `for:` on any rule that flapped during the soak.
4. **Document new noise patterns** discovered during soak so the runbook captures them for future operators.

## Absorbed finding

This story **absorbs** Story 6.10's adversarial-review findings:

- **R1 (HIGH per adversarial; MED per code-review)** — 3 ntfy pushes per event because Alertmanager `group_by` includes the `node` label. Code-review accepted it as redundancy (3 independent deliveries means a single ntfy hiccup can't lose the page); adversarial flagged it as alert-fatigue risk after a real multi-resource incident. SM resolution: keep redundancy through soak window, then re-evaluate.
- **R8 (MED)** — observer-node consensus uses ANY-match (`{state="error"} > 0`); during a pmxcfs partition this could false-fire. Quorum-match (`>=2`) for transient states would dampen this without weakening hard-fail detection.

R1's "3-pushes" behaviour is documented in Story 6.10 Completion Note 3 and the AC-6 drill evidence at `/tmp/ha-drill-evidence-6-10.txt` T+318s.

R3 (cron-daemon-death meta-monitoring) and R7 (drill safety preconditions) are deliberately **not** absorbed here — they are in scope for Stories 6.11 and 6.9.1 respectively.

## Acceptance Criteria

### AC-1: Pre-flight — cluster healthy, 6.10 in production for ≥2 weeks, soak data captured

**Given** Story 6.10 has been live in production for **≥14 days** (frontmatter `status: done`)
**And** the cluster is 3/3 quorate (`pvecm status` on pve1: `Quorate: Yes`, `Total votes: 3`)
**And** Story 6.11 (node systemd unit health) and Story 6.9.1 (drill safety preconditions) are either `done` or explicitly out-of-scope for this tuning pass (so we are not tuning while the alert surface is still being added to)
**When** I capture baseline:
```
ssh pve1 "ha-manager status" > /tmp/ha-status-pre-6-10-1.txt
curl -s 'https://prometheus.bi-services.be/api/v1/rules' | jq '.data.groups[] | select(.name=="pve-ha.alerts")' > /tmp/ha-rules-pre-6-10-1.json
curl -s 'https://alertmanager.bi-services.be/api/v2/alerts/groups' > /tmp/am-groups-pre-6-10-1.json
```
**Then** the baseline files exist and capture the pre-tuning state for diff after AC-3/AC-4
**And** no `PVEHA*` rule is currently `firing` (we are not tuning during a real incident).

### AC-2: Soak-period alert metrics are captured and reviewed

**Given** AC-1 holds
**When** I extract the 14-day soak window's alert history from Prometheus + Alertmanager + ntfy logs
**Then** a Markdown table is added to `homelab-infra/docs/ha-replication-runbook.md` (new section "HA alert soak review — <YYYY-MM-DD>") that captures, **per rule** (`PVEHAResourceUnhealthy`, `PVEHAResourceTransientStuck`, `PVEHAQuorumLost`, `PVEHAMasterMissing`, `PVEHALrmNotActive`, `PVEHAExporterMissing`, `PVEHAExporterStale`):
- Total times fired in the soak window
- Total ntfy pushes delivered (should equal `firing_count × 3` pre-tuning per the R1 fan-out)
- Dedupe ratio (pushes / unique-incident-count) — target post-tuning is ≤1.0 for `PVEHAResource*` rules
- False-positive count (rule fired but no real incident, e.g. transient pmxcfs blip resolved within 30 s)
- Time-to-acknowledge (median elapsed between `firing` and operator-side ntfy-tap; only for real incidents)
**And** the soak-review section calls out any patterns (e.g. "every Tuesday at 03:15 CEST `PVEHAExporterStale` flaps for 30 s — root cause: cron + timekeeping jitter") that need rule-level tuning beyond the R1/R8 changes.

**Note for the dev**: if the soak window had **zero** real or false-positive firings (cluster was rock-stable), document that and proceed — the de-duplication tuning (AC-3) and quorum-match (AC-4) are still worth applying as defensive posture; we just won't have observed evidence for `for:` tuning (AC-5).

### AC-3: Alertmanager `group_by` change applied + validated synthetically

**Given** AC-2 holds
**When** I edit `homelab-apps/stacks/observability/config/alertmanager/alertmanager.yml`:
- Add a new sub-route under the existing severity-tree that matches `domain="ha"` and overrides `group_by` to `['alertname', 'sid']` — drops `node` from grouping for HA alerts only (replication and other-domain alerts retain the existing grouping).
- The `domain` label is already emitted by every Story 6.10 rule per AC-5 conventions (`domain: ha`), so the matcher is `domain = "ha"` (exact match).
- Reload Alertmanager via `docker kill --signal=HUP alertmanager` (or `docker restart alertmanager` if the running version doesn't honour HUP — verify in advance).
**Then** `amtool config show` reflects the new `group_by` for the HA route
**And** I inject a synthetic multi-observer event for verification:
```
# Force the exporter to emit error state for ct:162 from all 3 nodes simultaneously
# (NOT a real HA fault — manipulate only the .prom file content for 2 minutes, restore after)
for n in pve1 pve2 pve3; do
  ssh $n "echo 'pve_ha_resource_state{sid=\"ct:162\",node=\"$n\",type=\"ct\",state=\"error\"} 1' >> /var/lib/prometheus/node-exporter/pve_ha_state.prom"
done
sleep 180  # 2-min for: + 30s scrape settle
# Restore — re-run the exporter on all 3 nodes
for n in pve1 pve2 pve3; do ssh $n "/usr/local/bin/pve-ha-state-exporter.sh"; done
```
**And** the operator's phone receives **exactly 1 ntfy push** (not 3) for the synthetic event — verified by checking the ntfy server log:
```
docker logs ntfy --since 5m | grep -c 'sid=ct:162.*state=error'
# Expected: 1
```
**And** the push body contains all 3 `node` labels (Alertmanager aggregates them into the single notification body when `node` is dropped from `group_by`) — operator can still see which observers reported the state from a single push.

### AC-4: Quorum-match expression updates for transient states + validated synthetically

**Given** AC-3 holds
**When** I edit `homelab-apps/stacks/observability/config/alerting/ha-alerts.yml`:
- **`PVEHAResourceUnhealthy`** (hard-fail states `error`, `fence`, `started_failure_recovery`) — keep ANY-match; expression unchanged. Hard-fail is unambiguous; ANY observer is enough.
- **`PVEHAResourceTransientStuck`** (transient states `recovery`, `relocate`, `migrate`, `request_start_balance`, `freeze`, `queued`) — change to **quorum-match (`>=2`)**:
  ```promql
  count by (sid, state) (pve_ha_resource_state{state=~"recovery|relocate|migrate|request_start_balance|freeze|queued"} > 0) >= 2
  ```
  This requires ≥2 of the 3 observers to report the same transient state for the same sid before firing — pmxcfs partition affecting one node alone won't fire.
- Update annotations to document the quorum requirement so operator runbook stays in sync.
- `promtool check rules` against the file → SUCCESS, 7 rules.
- SIGHUP-reload Prometheus.
**Then** `/api/v1/rules` shows the updated expression for `PVEHAResourceTransientStuck`
**And** I inject a synthetic single-observer transient event (only pve2 emits `state="recovery"=1` for ct:162; pve1 + pve3 unchanged) — verify the rule does **NOT** fire (1 < 2). Restore.
**And** I inject a synthetic two-observer transient event (pve2 + pve3 emit `state="recovery"=1`) — verify the rule **does** fire after `for: 5m`. Restore.
**And** the synthetic tests are documented in the soak-review section of the runbook with the exact commands used so future tuning rounds can replay them.

### AC-5: `for:` duration tuning for any rule observed to false-fire

**Given** AC-4 holds and AC-2's soak-review surfaced ≥1 rule that false-fired
**When** I tune `for:` durations:
- For each rule that false-fired during soak with a transient that resolved within X seconds, extend `for:` to `2 × X` (rounded up to the nearest 30 s).
- Cap `for:` extensions at `15m` for hard-fail states (`error`, `fence`) — beyond that we are tolerating real incidents too long.
- Cap `for:` extensions at `30m` for `PVEHAExporterStale` / `PVEHAExporterMissing` — beyond that the meta-monitoring promise of Story 6.10 erodes.
- Document each `for:` change in the soak-review section: rule name, old value, new value, rationale (cite the false-fire evidence).
**Then** `promtool check rules` passes after the tuning
**And** the soak-review section ends with a "Tuning applied" subsection listing the per-rule changes.

**Special case — no false-fires observed during soak**: skip this AC's edits and document "No `for:` tuning applied — soak window observed zero false-fire incidents on any HA rule." Re-evaluate at the next soak window. This is a legitimate AC outcome, not a defect.

### AC-6: New alert documentation in runbook

**Given** AC-3 through AC-5 hold
**When** I update `homelab-infra/docs/ha-replication-runbook.md` Monitoring section
**Then** the runbook now states explicitly:
- The HA alert deduplication policy (one logical event ⇒ one push, regardless of observer count) and where it is enforced (`alertmanager.yml` `group_by` sub-route for `domain="ha"`).
- The quorum-match policy for transient states (≥2 observers required) and the rationale (pmxcfs partition tolerance).
- Any new `for:` tuning applied in AC-5, and the soak-review evidence that motivated each change.
- A pointer to the synthetic-test commands in AC-3 and AC-4 so a future tuning round can repro them.

### AC-7: Story 7.11 E2E suite still PASSES

**Given** all previous ACs hold
**When** I re-run Story 7.11's end-to-end alert-chain test suite
**Then** all assertions still PASS — same severity routing (critical → ntfy-urgent, warning → ntfy-default, info → ntfy-low), same fail-loud default, same case-insensitive severity matchers; this story added a sub-route under the severity tree, did not change the severity tree itself.

### AC-8: Optional `PVEClusterCTMigrated` info-severity alert (post-soak decision; absorbs Story 6.6 R1 Outcome B)

After 2-week soak, decide if a low-priority `info`-severity alert should fire on graceful HA migrations (`ha-manager crm-command migrate`). Argument FOR: audit trail of all CT migrations during weekly maintenance, useful for post-incident reconstruction. Argument AGAINST: noise, especially during planned maintenance windows. Decision goes into runbook + alertmanager routing tree. Routes to `homelab-alerts-low` ntfy topic if implemented.

**Given** AC-2's soak review captured how often graceful migrations occurred during the soak window (Story 6.6 / 6.6.1 / 6.7 / 6.8 drills + any incident-driven migrations)
**When** I weigh the audit-trail value vs the noise cost
**Then** I document a decision (one of three outcomes) in the runbook's "HA alert soak review — <YYYY-MM-DD>" section under a new subsection "PVEClusterCTMigrated decision":
- **Decision A — IMPLEMENT**: add a new alert rule to `ha-alerts.yml`:
  ```yaml
  - alert: PVEClusterCTMigrated
    expr: |
      changes(pve_ha_resource_state_by_sid{state="started"}[2m]) > 0
      and on(sid) (count by (sid) (pve_ha_resource_state{state="started"}) > 0)
    for: 0s
    labels:
      severity: info
      domain: ha
    annotations:
      summary: 'CT {{ $labels.sid }} migrated (graceful HA migrate)'
      description: |
        A graceful HA migration completed for {{ $labels.sid }}.
        Source: <previous_node>; Target: {{ $labels.exported_node }}.
        This is an audit-trail event, not an incident.
  ```
  Routes via existing severity tree to `homelab-alerts-low` ntfy topic (per Story 7.11; if low-topic not implemented, fall through to `homelab-alerts-default` AND document the gap as a follow-up). Note: this rule is itself susceptible to label-mutation blindness (R3); use the `pve_ha_resource_state_by_sid` recording rule from Story 6.10.3 if that story is `done` first — otherwise document the dependency.
- **Decision B — DEFER**: soak window did not produce enough migration events to justify the rule (e.g. <2 migrations in 14 days); revisit at the next soak. Document the count + threshold in the runbook.
- **Decision C — REJECT**: noise concern outweighs audit-trail value (e.g. weekly maintenance windows generate predictable migrations that operators don't want paged on, even at info-severity). Document rationale.
**And** if Decision A: the rule is added, validated via `promtool check rules` SUCCESS, prometheus is hot-reloaded, and a synthetic test (manually flip an `exported_node` label in `pve_ha_state.prom` for ct:162) verifies the alert fires AND routes to ntfy-low.
**And** the decision is captured in the alertmanager routing tree comments + ha-replication-runbook.md.

## Tasks

- [ ] **Task 0: Pre-flight + soak-window confirmation** (AC-1)
  - Confirm Story 6.10 has been `done` for ≥14 days. Check git log for the merge of `homelab-apps/stacks/observability/config/alerting/ha-alerts.yml`.
  - Cluster quorate, no `PVEHA*` rule firing.
  - Capture baselines `/tmp/ha-status-pre-6-10-1.txt`, `/tmp/ha-rules-pre-6-10-1.json`, `/tmp/am-groups-pre-6-10-1.json`.

- [ ] **Task 1: Extract + summarise soak-period alert metrics** (AC-2)
  - Query Prometheus `ALERTS{alertstate="firing"}` over the 14-day window for each `PVEHA*` rule.
  - Cross-check Alertmanager `/api/v2/alerts` history.
  - Cross-check ntfy server log (`docker logs ntfy --since 14d | grep prometheus-bot`).
  - Author the "HA alert soak review — <YYYY-MM-DD>" Markdown table in the runbook.

- [ ] **Task 2: Apply `group_by` change and verify with synthetic event** (AC-3)
  - Edit `alertmanager.yml`: add `domain="ha"` sub-route with `group_by: ['alertname', 'sid']`.
  - Reload (HUP or restart, whichever the running Alertmanager honours).
  - Inject synthetic 3-observer error-state event for ct:162; verify exactly 1 ntfy push.
  - Capture push log evidence to `/tmp/6-10-1-am-dedupe-evidence.txt`.

- [ ] **Task 3: Apply quorum-match for transient states and verify** (AC-4)
  - Edit `ha-alerts.yml`: rewrite `PVEHAResourceTransientStuck` to `count by (sid, state) (...) >= 2`.
  - `promtool check rules` → SUCCESS.
  - SIGHUP-reload Prometheus.
  - Inject 1-observer synthetic recovery event → verify rule does NOT fire. Restore.
  - Inject 2-observer synthetic recovery event → verify rule fires after `for: 5m`. Restore.
  - Capture evidence to `/tmp/6-10-1-quorum-match-evidence.txt`.

- [ ] **Task 4: `for:` duration tuning** (AC-5)
  - For each rule that false-fired during soak: extend `for:` per AC-5 ratios; cap per AC-5 thresholds.
  - If zero false-fires: document and skip.
  - Append "Tuning applied" subsection to runbook soak-review.

- [ ] **Task 5: Runbook documentation refresh** (AC-6)
  - Update Monitoring section with dedupe policy, quorum-match policy, `for:` tuning trail.

- [ ] **Task 6: Story 7.11 regression check** (AC-7)
  - Re-run 7.11's E2E suite; capture output to `/tmp/7-11-suite-post-6-10-1.txt`.

- [ ] **Task 7: Final-state evidence + status flip**
  - Diff `/tmp/ha-status-pre-6-10-1.txt` vs post-state — should be 0 lines (no HA membership change).
  - Append Dev Agent Record per Story 6.10 pattern.
  - Frontmatter `backlog → review`.

## Dev Notes

### Current Alertmanager `group_by` (the line being changed)

`homelab-apps/stacks/observability/config/alertmanager/alertmanager.yml` line 36:

```yaml
route:
  receiver: ntfy-urgent
  group_by: ['alertname', 'node', 'jobid']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 12h
```

The `node` element is the source of the 3-pushes-per-event behaviour for HA alerts. For replication alerts (Story 6.2) the `node` label is the home-node-of-job, which is correctly per-job-unique, so dropping `node` from the global default is **not** safe — that is why this story adds a sub-route scoped to `domain="ha"` rather than editing the top-level `group_by`.

### Sub-route shape (recommended — verify against running Alertmanager version)

```yaml
route:
  receiver: ntfy-urgent
  group_by: ['alertname', 'node', 'jobid']  # unchanged default
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 12h
  routes:
    # NEW: HA-specific grouping — coalesce per-observer fan-out into one push per logical event
    - matchers:
        - domain = "ha"
      group_by: ['alertname', 'sid']
      continue: true   # let the severity routes below still apply
    # ... existing severity routes (unchanged) ...
    - matchers:
        - severity =~ "^[Cc]ritical$|^CRITICAL$"
      receiver: ntfy-urgent
      ...
```

**Important — `continue: true` semantics**: the `domain="ha"` sub-route only sets `group_by`; it does not select a receiver. Without `continue: true`, Alertmanager would drop the alert before reaching the severity routes. Verify with `amtool config routes test --tree` against a synthetic `severity=critical, domain=ha` alert.

### Reference patterns from Story 6.10 drill evidence

- T+318s: 3 ntfy pushes received on `homelab-alerts-urgent` topic (epoch 1777101821), one per observer-node group. Push body contains `severity=critical`, `sid=ct:162`, `state=error`. Source: Story 6.10 Dev Agent Record / `/tmp/ha-drill-evidence-6-10.txt`.
- Push delivery latency `T_firing → T_ntfy = 10s`. The dedupe change should not affect latency (still bounded by Alertmanager `group_wait: 30s`).

### Memory references

- `feedback_pve9_ha_error_recovery.md` — operator preference: per-resource state changes should produce one notification (not per-observer).
- `project_quant_trading.md` — ct:162 sensitivity informs why a stale alert that fires during a market-hours window is high-cost; tuning is partly about not training the operator to ignore the channel.

### Soak-review extraction commands

```bash
# Prometheus: which alerts fired and how often during the soak window
curl -s 'https://prometheus.bi-services.be/api/v1/query_range' \
  --data-urlencode 'query=ALERTS{alertname=~"PVEHA.*",alertstate="firing"}' \
  --data-urlencode 'start=2026-04-25T00:00:00Z' \
  --data-urlencode 'end=2026-05-09T23:59:59Z' \
  --data-urlencode 'step=60s' | jq

# Alertmanager: notification log
curl -s 'https://alertmanager.bi-services.be/api/v2/alerts' | jq '.[] | select(.labels.domain=="ha")'

# ntfy: actual delivered pushes
docker exec ntfy ntfy access | grep prometheus-bot   # auth events
docker logs ntfy --since 14d | grep -E 'sid=(ct|vm):' | wc -l   # delivered count
```

### Threshold caps for `for:` tuning

The caps in AC-5 prevent runaway tuning that would erode the meta-monitoring promise:

- Hard-fail states cap at `15m` — beyond that we tolerate real ct:162 outage too long.
- Exporter-staleness caps at `30m` — beyond that the exporter could die for half an hour and we wouldn't know.

If soak data justifies exceeding these caps, that is a separate conversation (operator decision); document it as an open question, do not exceed silently.

## Test strategy

**Phase 1 (Task 0):** observation-only baseline.

**Phase 2 (Task 1):** soak-data extraction + Markdown table authoring. No production state change.

**Phase 3 (Task 2):** Alertmanager config edit + reload + 3-observer synthetic injection. Side-effects: 1 real ntfy push to operator phone (synthetic but lands on real channel — keep operator informed). The injection is restore-clean: the exporter overwrites the manipulated `.prom` file on its next 1-minute tick.

**Phase 4 (Task 3):** Prometheus rules edit + reload + 1-observer + 2-observer synthetic injections. Same restore-clean pattern.

**Phase 5 (Tasks 4-7):** documentation + regression check + status flip. No production state change.

**Synthetic-injection cleanup**: the `/var/lib/prometheus/node-exporter/pve_ha_state.prom` file is regenerated by cron on every 1-minute tick, so any manual edit is automatically reverted within 60 seconds. The forced exporter run in the AC-3 / AC-4 cleanup steps just accelerates that.

## Security considerations

- No new credentials, no new network-facing services. Edits are confined to existing config files (`alertmanager.yml`, `ha-alerts.yml`) and the runbook.
- Synthetic-injection in AC-3 / AC-4 writes to `/var/lib/prometheus/node-exporter/` which already requires root; no privilege escalation. The temporary metrics never leave the local node.
- `amtool` and `promtool` invocations are read-only validations against existing config — no risk surface.
- No secrets in the runbook updates. SIDs (`ct:162`), node names, state strings — operational metadata only.

## Rollback procedure

If AC-3, AC-4, or AC-5 produces unexpected behaviour:

1. **Revert Alertmanager config**:
   ```
   git checkout homelab-apps/stacks/observability/config/alertmanager/alertmanager.yml
   docker kill --signal=HUP alertmanager
   ```
2. **Revert Prometheus rules**:
   ```
   git checkout homelab-apps/stacks/observability/config/alerting/ha-alerts.yml
   docker kill --signal=HUP prometheus
   ```
3. **Revert runbook**:
   ```
   git checkout homelab-infra/docs/ha-replication-runbook.md
   ```
4. **Verify**: synthetic 3-observer event again produces 3 ntfy pushes (the pre-tuning behaviour); single-observer transient still fires `PVEHAResourceTransientStuck` (the pre-tuning ANY-match behaviour); 7.11 E2E suite still PASSES.

Rollback is fully additive-reversal; no cluster state changes.

## References

- **Story 6.10 (the trigger)**: `homelab-playbook/_bmad-output/implementation-artifacts/6-10-ha-state-prometheus-exporter.md` — Completion Note 3 (3-pushes), AC-6 drill evidence, R1/R8 deferred from review
- **Story 7.11 (push channel)**: `homelab-playbook/_bmad-output/implementation-artifacts/7-11-alertmanager-and-ntfy-push-channel.md` — severity routing, fail-loud default
- **Story 6.2 (replication exporter precedent)**: `homelab-playbook/_bmad-output/implementation-artifacts/6-2-verify-replication-state-and-deltas.md` — alert tuning patterns
- **Memory: quant-trading sensitivity**: `/home/developer/.claude/projects/-home-developer-workspace-homelab/memory/project_quant_trading.md` — informs cost-of-fatigue
- **Memory: PVE 9 HA error recovery**: `/home/developer/.claude/projects/-home-developer-workspace-homelab/memory/feedback_pve9_ha_error_recovery.md` — operator UX preference
- **Alertmanager grouping docs**: <https://prometheus.io/docs/alerting/latest/configuration/#route>
- **Alertmanager sub-routes + `continue` semantics**: <https://prometheus.io/docs/alerting/latest/configuration/#route> (note on `continue` matching)
- **Drill evidence**: `/tmp/ha-drill-evidence-6-10.txt` (Story 6.10 Dev Agent Record), T+318s timeline

## Change Log

- **2026-04-25**: Scope expanded by Story 6-6 adversarial review (R1 Outcome B) — optional `PVEClusterCTMigrated` info-severity alert decision added to AC list (post-soak).
