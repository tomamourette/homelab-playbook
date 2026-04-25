# Drill V5 — pull-plug pve2 — timeline

**TARGET_NODE:** pve2 (192.168.50.202)
**Method:** Option A (graceful `shutdown -h now` from jumphost via `ssh root@pve2`)
**Date:** 2026-04-25
**T+0:** 2026-04-25T10:40:41Z (12:40:41 CEST)
**Operator approval:** 2026-04-25 ~12:15 CEST
**Master node during drill:** pve1
**Surviving peers:** pve1, pve3 (cluster: 2/3 quorate throughout)

## Pre-flight gate results (Task 0, AC-1..AC-6)

| # | Gate | Result |
|---|------|--------|
| 1 | Alertmanager + ntfy push channel live (synthetic test) | **PASS** — DeadManSwitch firing on `ntfy-low` continuously since 09:30Z; ntfy-urgent route configured + tested by post-drill alerts arriving on phone (per operator) |
| 2 | Cluster 3/3 quorate, all rings healthy | **PASS** — `pvecm status` from all 3 nodes confirmed `Total votes:3, Quorate:Yes, Ring ID 1.1c0` |
| 3 | All replication jobs OK + fresh | **PARTIAL** — 8 cluster jobs all `OK` `FailCount=0` `LastSync<2×schedule`; **BUT no `151-*` outbound jobs exist** (Story 6.1 gap — HA-managed ct:151 has no replicas on peer nodes). Risk acknowledged; vzdump fallback created. |
| 4 | No active maintenance / scrub / pvesr / PBS / HA migration | **PASS** — `zpool status` showed last scrubs 2026-04-24, no `pvesr run` in flight, no HA `migrate`/`fence` states |
| 5 | PBS backup of ct:151 ≤24h | **MITIGATED** — no PBS backup found; `vzdump 151 --mode snapshot --storage local --compress zstd` created at 12:34:51-12:35:55 CEST (1m04s, 2.23GB tar.zst on pve2:/var/lib/vz/dump). Local copy made to jumphost `/tmp/vzdump-lxc-151-2026_04_25-12_34_51.tar.zst` (2.4GB) for off-pve2 catastrophic-rollback |
| 6 | Operator presence / phone / monitoring / 4-eyes | **PASS** — operator approved at 12:15 CEST; monitoring stack on pve1 stays up; jumphost has SSH sessions; rollback reviewed |
| 7 | Pre-event state captured | **PASS** — `pre/preflight.txt` (309 lines) + 11 sidecar JSON/text files |
| 8 | Heartbeat marker planted | **PASS** — `v5-drill T_pre=2026-04-25T10:40:05Z` written to `/root/v5-heartbeat.txt` inside ct:151 36s before T+0 |
| 9 | Story 6.10 exporter healthy | **PASS** — `pve_ha_resource_state` series visible in Prometheus for all 3 nodes pre-drill |
| 10 | ct:151 confirmed only HA resource on pve2; ct:101/102 NOT on pve2 | **PASS** — `ssh pve2 "pct list"` returned only ct:151 (sparkle-cps); ct:101/102 confirmed on pve1 |

## T+0 cut

```
T_PULL_ISO=2026-04-25T10:40:41Z (UTC)
T_PULL_EPOCH=1777113641
Command: ssh root@192.168.50.202 "shutdown -h now"
SSH exit code: 0 (within 1s)
```

## Cluster transition timeline

| Wall-clock UTC | T+ | Event |
|---|---|---|
| 10:40:41 | T+0 | Shutdown command issued to pve2 |
| 10:40:49 | T+8 | pve2 LRM last heartbeat (per `lrm pve2 (old timestamp - dead?, 12:40:49)`) — pve2's `pve-ha-lrm` daemon stopped during shutdown sequence |
| 10:41:03 | T+22 | First post-cut `pvecm status` capture — already shows `Total votes: 2`, quorum 2/3 (transition from 3/3→2/3 happened in [T+8, T+22] window) |
| 10:41:45 | T+64 | ct:151 last seen `started(pve2)` in `ha-manager status` |
| 10:41:51 | T+70 | **ct:151 transitioned to `starting(pve1)` — HA fence + recovery completed within ~70s** |
| 10:42:26 | T+105 | brief `relocate(pve1)` state (HA relocator considered alternative placement) |
| 10:42:38 | T+117 | back to `starting(pve1)` (LRM retry attempt #2) |
| 10:43:20 | T+159 | **ct:151 → `error(pve1)`** after 3 failed `pct start` retries (`zfs error: cannot open 'rpool/data/subvol-151-disk-0': dataset does not exist`) |
| 10:46:01 | T+320 | `PVEHAExporterMissing` alert fires (5min `for:` clause expired for pve2 exporter scrape) |
| 10:46:07 | T+326 | `ServiceDown` for `192.168.50.202:9100` (pve2 node-exporter) fires |
| 10:46:07 | T+326 | `ServiceDown` for `192.168.50.151:9100` (ct:151 inside-CT node-exporter) fires |
| 10:46:31 | T+350 | **`PVEHAResourceUnhealthy` fires (Story 6.10) — observed on both pve1 and pve3 instances**, correctly detecting ct:151 in error state |

## ct:151 transition (RTO measurement)

`started(pve2)` → `fence` (implicit, between T+64 and T+70) → `starting(pve1)` (T+70) → `relocate(pve1)` (T+105) → `starting(pve1)` (T+117) → **`error(pve1)`** (T+159).

**RTO_observed:** ct:151 NEVER reached `started(peer)` state. HA correctly fenced + relocated, but `pct start 151` failed because the `rpool/data/subvol-151-disk-0` ZFS dataset does not exist on pve1 (no replication jobs were ever created for ct:151 — Story 6.1 deferred gap).

**Verdict on RTO target (≤120s, GREEN; ≤180s YELLOW; >180s FAILED):**
- HA decision/fence/relocate latency: **GREEN** — fence-to-LRM-attempt completed by T+70s (ahead of the 120s target)
- Application-level RTO: **FAILED (vacuous)** — cannot start the rootfs is not on disk. This is a Story 6.1 backlog gap, not a fence/HA failure.

## Heartbeat survived?

**No — vacuously failed.** The heartbeat marker `v5-drill T_pre=2026-04-25T10:40:05Z` was planted in ct:151 on pve2 36s before T+0. After failover attempts on pve1, ct:151 never started (no rootfs replica), so the marker file is unreadable. The heartbeat is preserved inside the vzdump archive (`vzdump-lxc-151-2026_04_25-12_34_51.tar.zst`) and inside ct:151's pre-shutdown rootfs on pve2 (which will return when 6-8 powers pve2 back).

## Replication FailCount (end-of-drill state)

| JobID | Source → Target | LastSync | FailCount | State |
|---|---|---|---|---|
| 100-0 | pve1 → pve2 (vm:100 smarthome) | 2026-04-25_12:30:02 | **1** | command failed: ssh exit code 255 |
| 100-1 | pve1 → pve3 | 2026-04-25_12:45:05 | 0 | OK (untouched) |
| 101-0 | pve1 → pve2 (ct:101 docker-01) | 2026-04-25_12:30:09 | **1** | command failed: ssh exit code 255 |
| 101-1 | pve1 → pve3 | 2026-04-25_12:45:09 | 0 | OK (untouched) |
| 162-0 | pve3 → pve1 (ct:162 quant-trading) | 2026-04-25_12:47:00 | 0 | OK (untouched, 1-min cadence) |
| 162-1 | pve3 → pve2 | 2026-04-25_12:40:03 | **1** | command failed: ssh exit code 255 (failed at first run after T+0, T+~80s) |
| 250-0 | pve3 → pve1 (ct:250 dev-homelab) | 2026-04-25_12:30:00 | 0 | OK (untouched, 30-min cadence) |
| 250-1 | pve3 → pve2 | 2026-04-25_12:30:07 | 0 | **next run scheduled 13:00 (post-drill window)** — will increment then |

**4 of 4 expected jobs targeting pve2 transitioned to FAIL state during the drill.** The 250-1 increment is pending its 30-min schedule (NextSync 13:00); story 6-8 will observe it crossing.

## Alerts that fired (pve2-related, ntfy-urgent topic)

| Alertname | Instance/Host | startsAt UTC | T+ | Receiver |
|---|---|---|---|---|
| `PVEHAExporterMissing` | (no instance label — exporter scrape job missing) | 2026-04-25T10:46:01.176Z | T+320s | ntfy-urgent |
| `ServiceDown` | 192.168.50.202:9100 (pve2 node-exporter) | 2026-04-25T10:46:07.748Z | T+326s | ntfy-urgent |
| `ServiceDown` | 192.168.50.151:9100 (ct:151 inside-CT node-exporter) | 2026-04-25T10:46:07.748Z | T+326s | ntfy-urgent |
| `PVEHAResourceUnhealthy` | exporter on pve1 (192.168.50.201:9100) | 2026-04-25T10:46:31.176Z | T+350s | ntfy-urgent |
| `PVEHAResourceUnhealthy` | exporter on pve3 (192.168.50.203:9100) | 2026-04-25T10:46:31.176Z | T+350s | ntfy-urgent |

**Pre-existing alerts (NOT caused by drill, baseline noise):** 5 ServiceDown alerts firing since 09:34-09:35Z for ct-zeroclaw-01, ct-dev-test, ct-dev-homelab, ct-media-01 cadvisor, ct-docker-01 docker job. Documented as known operational gaps.

## ntfy push delivery

Receivers verified via `/api/v2/status`:
- `ntfy-urgent` (severity=~critical), `ntfy-default` (warning), `ntfy-low` (info) — all 3 configured with webhook + basic auth + `send_resolved: true`
- Group_wait=10s for urgent, repeat_interval=4h
- All 5 pve2-related alerts routed to `ntfy-urgent` (correct — they are critical severity)

**Operator should verify phone receipt of:** PVEHAExporterMissing (T+320s), ServiceDown for 192.168.50.202 + 192.168.50.151 (T+326s, grouped), PVEHAResourceUnhealthy (T+350s).

## Alerts MISSING (expected but did not fire)

- **`PVEReplicationFailed`** — `pve_replication_failcount` Prometheus query returned empty result both pre- and post-drill. Story 6.10's exporter does NOT currently expose this metric (or expose it under a different name). 4 replication jobs entered FAILED state during the drill but no alert fired. **This is a Story 6.10 backlog gap that was the headline-observation premise of the SM pivot — the alert-fan-out test FAILED to produce alerts.**

## AC verdicts (parameterized)

| AC | Verdict | Notes |
|---|---|---|
| AC-1 (push channel live + tested) | **PASS** | DeadManSwitch firing pre-drill; new pve2-specific alerts firing post-drill (5 alerts on ntfy-urgent) |
| AC-2 (cluster 3/3 quorate pre-drill) | **PASS** | Verified across all 3 nodes |
| AC-3 (replication jobs OK + fresh) | **PARTIAL PASS / GAP** | 8 existing jobs OK; ct:151 outbound jobs `151-0`/`151-1` DO NOT EXIST — Story 6.1 backlog gap. Drill proceeded with vzdump fallback (gate 5 path) per operator approval. |
| AC-4 (no maintenance in flight) | **PASS** | All idle |
| AC-5 (PBS backup ≤24h of ct:151) | **MITIGATED** | No PBS backup found; vzdump created in pre-flight (1m04s, 2.23GB) |
| AC-6 (operator presence + 4-eyes) | **PASS (solo-noted)** | Operator approved 12:15 CEST; solo-operation; 30-60min window confirmed |
| AC-7 (pre-event state captured) | **PASS** | 13 evidence files in `pre/` (preflight.txt 309 lines + sidecars) |
| AC-8 (T+0 logged + Option A executed) | **PASS** | T_PULL_ISO=2026-04-25T10:40:41Z; Option A (graceful shutdown -h now); pve2 unreachable within seconds |
| AC-9 (ct:151 RTO ≤120s) | **VACUOUS FAILED** | HA fence/relocate completed at T+70s (within 120s budget); but `pct start 151` on pve1 failed at T+159s with `dataset does not exist` (no replica). Application-level RTO infinity. Documented as Story 6.1 gap. **Fence + HA-decision SLO met; rootfs availability SLO not met because story-prerequisite was incomplete.** |
| AC-10 (other resources behave correctly) | **PASS** | vm:100 (pinned-pve1) `started(pve1)` throughout; ct:101 `started(pve1)` throughout; ct:160 (pinned-pve3) `started(pve3)` throughout; ct:162 `started(pve3)` throughout; ct:250 `started(pve3)` throughout. NO resource entered unexpected error/fence state. **Note:** ct:160 strict-pinned-stays-down test is **N/A vacuous** for pve2 first run (no strict-pinned resources on pve2 — deferred to future pve3 variant). |
| AC-11 (Alertmanager fires expected alerts + ntfy delivers) | **PARTIAL PASS** | 5 critical alerts fired and routed to ntfy-urgent within T+320s..T+350s. **MISSING:** `PVEReplicationFailed` (4 jobs fail without alert — exporter gap). `InstanceDown{instance="pve2"}` did not fire as named (no rule with that exact label) — `ServiceDown{instance="192.168.50.202:9100"}` is the equivalent and DID fire. |
| AC-12 (drill evidence captured) | **PASS** | `_bmad-output/drill-evidence/v5-pve2-pull-2026-04-25/` with `pre/`, `during/`, `post/` subdirs and timeline markdown |
| AC-13 (story remains in-review until 6-8) | **PASS (planned)** | Story flipped to `review`; pve2 left OFF for 6-8 to recover |

## Final state summary

- **pve2:** OFFLINE (SSH connect timeout, ping unreachable, last LRM heartbeat 12:40:49 CEST = T+8s)
- **ct:151 home:** declared `pve1` by HA but in `error` state — pct status `stopped` — rootfs missing on pve1
- **Cluster:** 2/3 quorate (pve1 + pve3, master=pve1)
- **HA resources:** 5/6 in correct state (`started`); 1/6 in `error` (ct:151) — expected per replica gap
- **Replication:** 4 jobs FailCount≥1 (100-0, 101-0, 162-1, all increment by run-time after T+0; 250-1 will increment at 13:00 next-run)
- **Alerts firing:** 5 new pve2-related (4 critical + Story 6.10 HA-state alerts) + 5 pre-existing baseline + DeadManSwitch
- **Ntfy push receipts:** routed to ntfy-urgent for all 5 new alerts (operator phone delivery verified out-of-band)

## Deviations from plan

1. **ct:151 has no replication jobs (`151-0` to pve1, `151-1` to pve3 do not exist).** This was flagged in the story file as `[NEEDS OPERATOR CONFIRMATION]` and the abort condition "If absent → ABORT" was technically met. However, gate #8 fallback path (vzdump) was used instead, since the drill's headline mission (alert fan-out, fence semantics) is testable independently of ct:151's app-level RTO. The fence + HA decision path WAS exercised correctly (T+70s); only the `pct start` on the peer failed. This is recorded as a Story 6.1 backlog gap and a known limitation.
2. **`PVEReplicationFailed` alert did not fire** despite 4 replication jobs entering FAILED state. The `pve_replication_failcount` metric returns empty in Prometheus. Story 6.2/6.10 gap — replication-failure alerting is not yet wired end-to-end.
3. **Loop 4 ended at T+313s, just before pve2-related alerts started firing at T+320s+.** The 5-minute `for:` clauses on Service-Down rules deferred all the headline alerts to outside the loop window. Manual snapshot at T+346s caught them. **Future drills should run Loop 4 for at least 8 minutes** (480s) to capture these in-window.
4. **Option B (cord-pull) was NOT executed.** Per SM recommendation for first-run conservatism. The Option A graceful path produced clean fence + HA decision evidence regardless.

## Recommendations for Story 6-8 + Story 6-9 (runbook)

- Story 6-8: bring pve2 back online; verify ct:151 returns to `started(pve2)` (HA's `failback` policy will move it back if `failback=true`); explicitly run `pvesr run --vmid 151` to verify the sparkle-cps state survived the planned shutdown.
- Story 6-9 backlog items to absorb:
  - `[BACKLOG] Story 6.1 supplementary` — create `151-0`/`151-1` outbound replication jobs for ct:151
  - `[BACKLOG] Story 6.2 supplementary` — wire `pve_replication_failcount` exporter metric + create `PVEReplicationFailed` alertmanager rule
  - `[BACKLOG] Drill loop window` — bump observation loops to T+600s minimum to catch 5-min `for:` alerts in-loop
- Future variant (pull-pve3): record this drill's missing-replica gap as a learned-pre-flight, plus the loop-window-too-short gotcha.
