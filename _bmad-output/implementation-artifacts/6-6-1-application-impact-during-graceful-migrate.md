---
status: backlog
epic: 6
story: 6.6.1
title: Application-impact measurement during graceful HA migrate (TCP / cache / PID with optional replication-lag injection)
created: 2026-04-25
author: BMad SM
depends-on: 6-6
---

# Story 6.6.1: Application-impact measurement during graceful HA migrate

Status: backlog

## Story

As an operator,
I want empirical, inside-CT measurements of what live applications experience during a graceful `ha-manager crm-command migrate` (TCP socket survival, reconnect time, in-memory cache loss, daemon PID changes), with an OPTIONAL replication-lag injection variant to test migrate-back under stale-source conditions,
so that the operator's mental model of "11 s outage" (Story 6.6) is replaced by an honest description of what real applications running inside ct:162 see during the same migration window — and Story 6.7's pull-plug drill inherits a calibrated baseline rather than an HA-LRM-only number.

## Business value

Story 6.6 proved the V4 graceful-migrate mechanism works at the **HA layer**: total HA-LRM transition was 11 s (CRM `request_start` → `started` on pve2), heartbeat byte-identity confirmed filesystem replication, replicated snapshot lineage flipped cleanly, no operator intervention. PASS GREEN.

But 6.6's adversarial review (R2 MED + R4 LOW) flagged a measurement gap: **11 s is the HA-LRM number, not the application-level number.**

What 6.6 did NOT measure:
- TCP connections live-at-migration-start: did they survive (unlikely — migrate stops the CT, restarts on the new node), or were they reset? If reset, how long until applications reconnected?
- In-memory state inside the running processes (caches, session tokens, websockets, prepared statements): the CT's filesystem is byte-identical post-migrate, but every process restarts from scratch.
- Process PIDs: did `systemd`-supervised daemons restart cleanly? Were any zombied? Did any fail to come back?
- Daemon health post-migrate: did `systemctl is-active` for every expected unit return `active` within N seconds?

What 6.6 did NOT simulate (R4):
- Replication-lag conditions. 6.6 ran with replication healthy and `LastSync` fresh (≤60 s). A real failover situation often has 3+ minutes of accumulated lag on the source node when the migrate-back fires. PVE's behaviour under "source filesystem is stale" is unverified — does it re-replicate before allowing migrate-back? Does it refuse? Does it succeed silently with stale data?

Without 6.6.1, the operator carries a wrong mental model into Story 6.7's pull-plug drill: they expect "11 s outage" and will be surprised when applications inside the CT report TCP resets, cache rebuild stalls, and websocket reconnect storms. With 6.6.1, the runbook section "What graceful HA migration does/does not preserve" gets replaced with empirical numbers — and the operator knows in advance which application patterns (e.g. websockets-without-auto-reconnect) need a sidecar reconnect strategy before relying on HA failover.

ct:162 is the canonical target because it is HA-managed, lives on pve3, and is the workload Epic 6's RPO/RTO promises are calibrated against (`project_quant_trading.md`). The drill window must respect market-hours sensitivity (refer to Story 6.9.1's `drill-safety-check.sh` once that lands; pre-6.9.1, manual operator discipline applies).

## Absorbed finding

This story **absorbs** Story 6.6's adversarial-review findings:

- **R2 (MED)** — "11 s outage measures HA-LRM transitions only, not application-level impact. TCP connections die, in-memory state is lost, processes restart. Heartbeat byte-identity proves filesystem replication, not application continuity. Future drills should measure inside-CT socket survival."
- **R4 (LOW, related)** — "Replication-lag injection not simulated. Real failover may have 3+ min stale state on the source when migrate-back fires; PVE behaviour under that condition is unverified."

R2 is the load-bearing finding (AC-2 / AC-3 cover it). R4 is folded in as **AC-4 OPTIONAL** — good-to-have but not gating. If the operator runs only AC-1 through AC-3 + AC-5 + AC-7, the story can ship; AC-4 is a strict superset that converts a remaining unknown into evidence.

R3 (label-mutation in `changes()` rules) and code-review L2 (Prometheus container clean-exit) are absorbed by Story 6.10.3 — explicitly out-of-scope here.

## Acceptance Criteria

### AC-1: Pre-flight — drill window open, ct:162 healthy, instrumentation prerequisites met

**Given** the cluster is 3/3 quorate (`pvecm status` on pve1: `Quorate: Yes`, `Total votes: 3`)
**And** Story 6.6 is `done` (V4 baseline established; 11 s HA-LRM number is the calibration anchor)
**And** the drill is scheduled outside the market-hours window per `project_quant_trading.md` (weekend morning canonical, OR weekday after 22:00 CEST). If Story 6.9.1 is `done`, run `sudo /usr/local/bin/drill-safety-check.sh --drill-name 6-6-1-app-impact` — gate must exit 0 before proceeding.
**And** ct:162 is HA-tagged with `state: started` per Story 6.3 (`ha-manager status` shows `ct:162` started on `pve3`)
**And** all 8 replication jobs are `OK` with `fail_count=0` (`pvesh get /cluster/replication --output-format json | jq '.[] | .fail_count'` → all 0)
**When** I capture the pre-flight artifact bundle
**Then** the bundle exists at `_bmad-output/drill-evidence/v4-1-app-impact-<date>-pre/`:
- `ha-manager-status.txt`
- `pvesh-replication-pre.json`
- `ct162-pid-snapshot-pre.txt` — `pct exec 162 -- ps -eo pid,ppid,cmd --no-headers | sort -k1,1n`
- `ct162-systemctl-units-pre.txt` — `pct exec 162 -- systemctl list-units --type=service --state=active --no-legend`
- `instrumentation-readiness.txt` — confirms the AC-2 instrumentation script is staged in ct:162 and the external counterpart endpoint is reachable

### AC-2: Inside-CT instrumentation — long-lived TCP socket + heartbeat counter + in-memory state file

**Given** AC-1 holds
**When** I deploy the instrumentation harness inside ct:162
**Then** the following three measurement primitives are running and producing evidence before any migration:

1. **Long-lived TCP socket to an external endpoint** — a process inside ct:162 holds an open TCP connection to a peer outside the CT (recommended: a `nc -kl` listener on pve1 at a high port, OR a real already-running service like the Prometheus scrape endpoint on ct-docker-01:9090). The script logs every read/write with a monotonically increasing sequence number and millisecond-resolution timestamp. Output: `/root/v4-1-tcp-socket.log` inside ct:162.
2. **Heartbeat counter** — a tight loop (`while true; do echo "$(date +%s%3N) $((COUNTER++))" >> /root/v4-1-heartbeat.log; sleep 0.5; done &`) writing 2 ticks/second to a file. The counter is **kept in-memory** in the shell variable `$COUNTER`; if the process restarts, the counter resets to 0 (this is exactly the in-memory-state-loss signal we want to capture). File path: `/root/v4-1-heartbeat.log`.
3. **PID watcher** — every 5 s, dump `ps -eo pid,ppid,cmd --no-headers | sort -k1,1n` to `/root/v4-1-pid-watch.log`. After migration, the PID set should be entirely new (the CT was stopped + restarted on the new node); we want to see how clean the restart was, what came up, and whether anything is missing vs the pre-flight `systemctl` snapshot.

**And** the instrumentation script is committed to `homelab-infra/scripts/drills/v4-1-app-impact-instrumentation.sh` (idempotent — running it twice doesn't double-spawn the loops; uses `pidof` guards or pid-files in `/var/run/`).
**And** the external TCP peer is documented in the script header (which host, which port, why) so a future operator can re-run the drill against the same endpoint.
**And** the instrumentation has been running ≥120 s before AC-3 fires the migration — long enough for the pre-migrate baseline counter and PID snapshots to stabilise.

### AC-3: Graceful migrate pve3 → pve2 + per-primitive measurement capture

**Given** AC-2 holds (instrumentation has been running ≥120 s)
**When** I trigger the V4 graceful migration:
```
ssh pve3 "ha-manager crm-command migrate ct:162 pve2"
```
**Then** the migration completes per the Story 6.6 pattern (HA-LRM transitions on pve2: `request_start` → `started`)
**And** the following per-primitive measurements are captured to `_bmad-output/drill-evidence/v4-1-app-impact-<date>-during/`:

1. **TCP socket measurement**:
   - **Time of last successful read/write before disruption**: T_last (epoch ms from socket log)
   - **Time of first successful read/write after disruption**: T_reconnect (epoch ms)
   - **TCP socket survival outcome**: one of `{survived, reset+auto-reconnect, reset+manual-reconnect, reset+no-reconnect}`
   - **Reconnect duration**: `T_reconnect - T_last` (ms)
   - **Sequence-number gap**: how many ticks were lost between last successful write and first post-reconnect write
2. **Heartbeat counter measurement**:
   - **Last counter value before disruption**: C_last (from file, NOT from in-memory variable)
   - **First counter value after disruption**: C_post (should be 0 — proves in-memory state was lost; if it isn't 0, the process didn't actually restart and we have a different question)
   - **Heartbeat gap**: time between last `echo` and first post-resume `echo` (ms) — this is the closest proxy to "what would a tight-loop application see?"
3. **PID watcher measurement**:
   - **Last pre-migrate PID set**: from pid-watch log
   - **First post-migrate PID set**: PIDs should all be new (likely 1, 2, 3, ... starting fresh — confirms full restart)
   - **Daemon parity**: diff `pct exec 162 -- systemctl list-units --type=service --state=active --no-legend` post-migrate vs the AC-1 pre snapshot. Any missing units? Any new failed units?

**And** the post-migrate `pct exec 162 -- date +%s` matches the pve2-side wall clock (no clock skew introduced by the move).
**And** ct:162 is fully operational on pve2 within the bound established by Story 6.6 (≤60 s CT-down-to-CT-up).

### AC-4 OPTIONAL: Replication-lag injection — migrate-back under stale-source conditions

**Given** AC-3 holds and ct:162 is now running on pve2
**And** the operator explicitly opts into the lag-injection variant (this AC is OPTIONAL — flagged for skip if the drill window is tight or the operator wants to keep the drill conservative)
**When** I inject replication lag and then trigger migrate-back:
1. **Disable replication for ct:162's jobs from pve2 outward**:
   ```
   ssh pve2 "pvesr disable 162-0"   # 162→pve1
   ssh pve2 "pvesr disable 162-1"   # 162→pve3
   ```
2. **Generate inside-CT activity to accumulate lag** — re-run the AC-2 instrumentation under load (e.g. write 1 MB/min of synthetic data to `/root/v4-1-load-data.bin`) for **≥5 minutes**. The pve3 source is now ≥5 min stale relative to pve2's current state.
3. **Verify lag is observable**:
   ```
   ssh pve3 "zfs list -t snapshot -r rpool/data | grep 162 | awk '{print $1}'"
   # Newest __replicate_162-*__ snapshot on pve3 should be ≥5 min old
   ```
4. **Re-enable replication and trigger migrate-back**:
   ```
   ssh pve2 "pvesr enable 162-0; pvesr enable 162-1"
   ssh pve2 "ha-manager crm-command migrate ct:162 pve3"
   ```
5. **Measure**:
   - **Did PVE auto-replicate before migrate?** Watch `pvesr status` on pve2 — does the rate spike during the migrate trigger?
   - **Migrate-back outage duration** (total CT-down-to-CT-up time, from pve3-side perspective)
   - **Were any seconds of inside-CT data lost?** Diff `/root/v4-1-load-data.bin` byte-for-byte pre-migrate vs post-migrate-back. The `bin` file is the canary: if PVE migrate-back uses stale-source data, the file content reverts ≥5 min.

**Then** the measurements are captured to `_bmad-output/drill-evidence/v4-1-app-impact-<date>-replication-lag/`
**And** the outcome is documented as one of:
- **Outcome A (clean)**: PVE auto-replicates before migrate-back; `bin` file is byte-identical pre-migrate vs post-migrate-back. Lag was absorbed, RPO promise held under stress.
- **Outcome B (data loss)**: `bin` file reverts to pre-load state; PVE migrated stale source data. RPO promise has a hidden caveat — operator needs to know about this.
- **Outcome C (refusal)**: PVE refuses to migrate while replication is mid-catch-up. Outage is longer than AC-3 (operator waits for replication, then migrates). Acceptable but document the wait time.

### AC-5: Measurement results documented in runbook

**Given** AC-3 holds (and AC-4 if it ran)
**When** I update `homelab-infra/docs/ha-replication-runbook.md`
**Then** the existing section "What graceful HA migration does/does not preserve" (added by Story 6.6's fix-apply F2) is **extended** with empirical numbers from AC-3:
- **TCP connections**: do not survive — observed reset + reconnect within `<measured ms>`.
- **In-memory state**: lost — heartbeat counter resets to 0 every migrate.
- **Process PIDs**: replaced — all daemons restart from PID 1 lineage.
- **Daemon parity**: `<X/X units restored>` — list any discrepancies observed.
- **HA-LRM outage** (Story 6.6 number): 11 s.
- **Application-level outage** (this story's number): `<measured ms>`. The delta between these two numbers is the operator's "applications-on-this-CT need a reconnect strategy" budget.
**And** if AC-4 ran, a new subsection "Replication-lag-injected migrate-back" documents the Outcome (A/B/C) with numbers.
**And** the runbook calls out which application patterns are observed to be problematic (e.g. "websockets without auto-reconnect lose a tick on every migrate; HTTP connections with retry survive cleanly").

### AC-6: Rollback procedure documented (only relevant if AC-4 was run)

**Given** AC-4 was executed
**When** I document rollback in the story Dev Notes + runbook
**Then** the rollback procedure for a stuck migrate-back is captured:
1. If migrate-back succeeded but daemons didn't come up cleanly on pve3: standard error-state recovery sequence per `feedback_pve9_ha_error_recovery.md`:
   ```
   ssh pve3 "ha-manager set ct:162 --state disabled"
   # diagnose root cause
   ssh pve3 "ha-manager set ct:162 --state started"
   ```
2. If replication failed to catch up before migrate-back: `pvesr run --id 162-0 --verbose` and `pvesr run --id 162-1 --verbose` to force a sync; if that fails, see `homelab-infra/docs/ha-replication-runbook.md §Troubleshooting` and `project_pve3_storage_redesign.md`.
3. If the lag injection left orphan replication snapshots on pve2 or pve1, identify them:
   ```
   for n in pve1 pve2 pve3; do ssh $n "zfs list -t snapshot -r rpool/data | grep '__replicate_162'"; done
   ```
   Compare against the AC-1 pre-flight snapshot baseline; remove orphans only if confidently identified.

### AC-7: Final disposition — application patterns that fail under graceful migrate are identified

**Given** AC-3 (and AC-4 if it ran) hold and the runbook is updated
**When** I review the measurements with the application patterns running inside ct:162
**Then** a final-disposition note is appended to the runbook (or a new follow-up backlog story is created) listing each application pattern observed during the drill and its survival classification:
- **Pattern survived cleanly** (auto-reconnect, no user-visible impact): list services
- **Pattern survived with degradation** (reconnect storm, cache rebuild stall): list services + describe degradation
- **Pattern did NOT survive** (manual restart needed): list services + flag as a follow-up backlog item

**And** if any pattern in the third category exists, a new backlog story is filed (e.g. "Add auto-reconnect sidecar for `<service>` to survive HA migrations") and cross-referenced from the runbook.

## Tasks

- [ ] **Task 0: Pre-flight + drill-window confirmation** (AC-1)
  - Confirm Story 6.6 done, cluster quorate, replication healthy, drill window open.
  - If Story 6.9.1 done, run `drill-safety-check.sh --drill-name 6-6-1-app-impact` — gate must pass.
  - Capture AC-1 evidence bundle to `_bmad-output/drill-evidence/v4-1-app-impact-<date>-pre/`.

- [ ] **Task 1: Author + stage instrumentation harness** (AC-2)
  - Write `homelab-infra/scripts/drills/v4-1-app-impact-instrumentation.sh` (idempotent; pid-files; documented external TCP peer).
  - `pct push 162 v4-1-app-impact-instrumentation.sh /root/v4-1-app-impact-instrumentation.sh` (or equivalent).
  - Start the harness inside ct:162; wait ≥120 s for stable baseline.
  - Verify all three primitives are emitting (TCP socket log, heartbeat log, pid-watch log).

- [ ] **Task 2: Trigger graceful migrate + capture evidence** (AC-3)
  - `ssh pve3 "ha-manager crm-command migrate ct:162 pve2"`.
  - Wait for HA-LRM to reach `started` on pve2 (≤60 s per Story 6.6).
  - `pct pull 162 /root/v4-1-tcp-socket.log /root/v4-1-heartbeat.log /root/v4-1-pid-watch.log` to host.
  - Compute the measurements (T_last, T_reconnect, gap, counter reset, PID parity, daemon parity).
  - Capture to `_bmad-output/drill-evidence/v4-1-app-impact-<date>-during/`.

- [ ] **Task 3: OPTIONAL — replication-lag injection + migrate-back** (AC-4)
  - Operator decision point: skip OR proceed.
  - If proceed: disable 162-0/162-1, generate ≥5 min of inside-CT load, verify lag observable, re-enable + migrate back.
  - Measure migrate-back outage, byte-diff the load `bin` file, classify outcome (A/B/C).
  - Capture to `_bmad-output/drill-evidence/v4-1-app-impact-<date>-replication-lag/`.

- [ ] **Task 4: Update runbook with empirical numbers** (AC-5)
  - Extend §"What graceful HA migration does/does not preserve" with measured numbers.
  - If AC-4 ran, add §"Replication-lag-injected migrate-back" with Outcome.

- [ ] **Task 5: Document rollback procedure** (AC-6)
  - Folded into runbook + story Dev Notes; only relevant if AC-4 ran.

- [ ] **Task 6: Final-disposition + follow-up backlog** (AC-7)
  - Review per-pattern survival; classify; file follow-up backlog stories for any "did not survive" patterns.

- [ ] **Task 7: Final-state evidence + status flip**
  - Verify ct:162 returned to its canonical home node (pve3 if AC-4 ran; pve2 if only AC-3 ran — operator's call whether to migrate-back as a separate clean step).
  - Verify replication healthy (all 8 jobs OK, fail_count=0).
  - Append Dev Agent Record per Story 6.10 pattern.
  - Frontmatter `backlog → review`.

## Dev Notes

### Instrumentation script pattern

Skeleton for `homelab-infra/scripts/drills/v4-1-app-impact-instrumentation.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

# External TCP peer — adjust per drill setup
EXTERNAL_HOST="${EXTERNAL_HOST:-192.168.50.20}"  # pve1
EXTERNAL_PORT="${EXTERNAL_PORT:-9999}"            # nc -kl on pve1

LOG_DIR="/root"
TCP_LOG="$LOG_DIR/v4-1-tcp-socket.log"
HB_LOG="$LOG_DIR/v4-1-heartbeat.log"
PID_LOG="$LOG_DIR/v4-1-pid-watch.log"

# Idempotency: refuse if already running
if [ -f /var/run/v4-1-instrumentation.pid ] && kill -0 "$(cat /var/run/v4-1-instrumentation.pid)" 2>/dev/null; then
    echo "instrumentation already running (pid $(cat /var/run/v4-1-instrumentation.pid))" >&2
    exit 0
fi
echo $$ > /var/run/v4-1-instrumentation.pid
trap 'rm -f /var/run/v4-1-instrumentation.pid' EXIT

# Primitive 1: long-lived TCP socket
(
    exec 3<>"/dev/tcp/$EXTERNAL_HOST/$EXTERNAL_PORT"
    SEQ=0
    while true; do
        printf '%s %d\n' "$(date +%s%3N)" "$SEQ" >&3
        printf '%s tx %d\n' "$(date +%s%3N)" "$SEQ" >> "$TCP_LOG"
        SEQ=$((SEQ + 1))
        sleep 1
    done
) &

# Primitive 2: heartbeat counter (in-memory; resets on process restart)
(
    COUNTER=0
    while true; do
        printf '%s %d\n' "$(date +%s%3N)" "$COUNTER" >> "$HB_LOG"
        COUNTER=$((COUNTER + 1))
        sleep 0.5
    done
) &

# Primitive 3: PID watcher
(
    while true; do
        {
            printf '=== %s ===\n' "$(date -Iseconds)"
            ps -eo pid,ppid,cmd --no-headers | sort -k1,1n
        } >> "$PID_LOG"
        sleep 5
    done
) &

wait
```

External TCP peer — recommended setup on pve1: `screen -dmS v4-1-listener nc -kl 9999 > /tmp/v4-1-listener.log`. Documented in the script header so a future operator runs the same setup.

### Replication-lag-injection method

Two safe primitives:
- `pvesr disable <jobid>` — stops scheduled replication for a job; existing snapshots remain intact, no destructive operation.
- `pvesr enable <jobid>` — re-enables scheduled replication.

After `enable`, the next scheduled cycle catches up; force-immediate via `pvesr run --id <jobid> --verbose`.

Lag accumulation method — write a known-byte-count pattern to a file inside ct:162 (`/root/v4-1-load-data.bin`) using `dd if=/dev/urandom of=/root/v4-1-load-data.bin bs=1M count=5` repeated every minute for 5 minutes. The file content is the canary: byte-diff before vs after the lag-injected migrate-back tells the operator whether the migrate used stale source data (Outcome B) or correctly waited for catch-up (Outcome A).

### Why "OPTIONAL" on AC-4

AC-4 is a deliberately bigger commitment than AC-2/AC-3:
- It deliberately accumulates ≥5 min of replication lag, which means the cluster spends that window outside the Epic 6 RPO promise. Acceptable for a drill window; not acceptable for production.
- It tests an unverified PVE behaviour (migrate-back under stale source). The blast radius if PVE handles it badly (Outcome B with data loss) is a corrupted ct:162.
- Mitigation: ct:162 is HA-managed so the worst case is a partial restore from the freshest replica. The drill is designed to make this mitigation observable, not invisible.

If the operator wants the conservative path: run AC-1, AC-2, AC-3, AC-5, AC-7. Ship 6.6.1 with the AC-3 numbers in the runbook and explicitly note "AC-4 deferred — replication-lag-under-migrate-back behaviour remains unverified". A future story can revisit when the operator is comfortable with the blast radius.

### Risk / failure modes

1. **Instrumentation harness leaks processes after a drill abort** — pid-file + EXIT trap cleans up, but a SIGKILL (`kill -9`) leaves loops running. Manual cleanup: `pkill -f v4-1-instrumentation` inside ct:162.
2. **External TCP peer (`nc -kl`) wedges on a half-closed connection** — well-known nc behaviour; operator restarts the listener as needed. Documented in script header.
3. **Heartbeat counter ambiguity** — if the inside-CT shell that runs the counter doesn't actually restart on migrate (e.g. systemd-supervised with PID-1 stable), the counter would NOT reset to 0, and the test gives a false-positive "in-memory survived" signal. Mitigation: run the counter as a **direct shell** (not under systemd), exactly so it dies with the CT shutdown. Confirm pre-drill that `pidof bash | grep -F "$COUNTER_PID"` matches the loop's process tree.
4. **TCP socket reconnect logic dependency** — bash's `/dev/tcp` does NOT auto-reconnect on EOF. The instrumentation will see the socket close and exit. That is by design — we want to measure "how long until a fresh connect succeeds", and a separate respawn loop wraps the socket primitive (the AC-2 script's outer `while true` re-execs the inner socket block on connection close). Documented.
5. **AC-4 stale-source migrate-back race** — between `pvesr enable` and `ha-manager crm-command migrate`, PVE may schedule a replication run that completes before the migrate fires; this would defeat the lag injection. Mitigation: enable + migrate within 1 second of each other (use `;` to chain, not `&&` or two separate ssh calls).

### File layout

**homelab-infra/** (create):
- `scripts/drills/v4-1-app-impact-instrumentation.sh` (~80-120 lines, mode 0755)

**homelab-infra/** (modify):
- `docs/ha-replication-runbook.md` — extend §"What graceful HA migration does/does not preserve" with empirical numbers; add §"Replication-lag-injected migrate-back" if AC-4 ran.

**homelab-playbook/** (modify):
- `_bmad-output/drill-evidence/v4-1-app-impact-<date>-pre/` (new dir, multi-file evidence bundle)
- `_bmad-output/drill-evidence/v4-1-app-impact-<date>-during/` (new dir)
- `_bmad-output/drill-evidence/v4-1-app-impact-<date>-replication-lag/` (new dir; only if AC-4 ran)

### Prior art references

- **Story 6.6 (V4 baseline drill)** — established the 11-s HA-LRM outage number; this story extends with application-level numbers.
- **Story 6.5 (V3 RPO drill)** — established the heartbeat-file pattern; AC-2's heartbeat-counter primitive is the in-memory variant of that pattern.
- **Story 6.9.1 (drill safety preconditions)** — gate dependency for the drill window check.
- **Memory: feedback_pve9_ha_error_recovery.md** — operator preference: error-state recovery sequence is `disabled → diagnose → started`. Relevant for AC-6 rollback.
- **Memory: project_quant_trading.md** — ct:162 market-hours sensitivity (drill window discipline).
- **Memory: project_pve3_storage_redesign.md** — replication-snapshot semantics; informs AC-4 lag-injection method.

## Test strategy

**Phase 1 (Task 0):** observation-only; pre-flight bundle.

**Phase 2 (Task 1):** instrumentation deployment inside ct:162 — 120 s baseline. No cluster state change.

**Phase 3 (Task 2):** the load-bearing migration. ct:162 is briefly offline (≤60 s per Story 6.6). Side-effect: HA state changes, replication direction flips. Same blast radius as Story 6.6, by design.

**Phase 4 (Task 3, OPTIONAL):** higher-blast-radius lag injection. ct:162 spends ~5 min outside RPO promise. Cleanup is automatic via re-enable + first-cycle catch-up; operator monitors `pvesr status` post-drill to confirm fail_count=0 before declaring done.

**Phase 5 (Tasks 4-7):** runbook updates + final-disposition review + status flip.

**Test acceptance:** evidence bundles exist; runbook updated with empirical numbers; if AC-4 ran, Outcome (A/B/C) classified and documented; ct:162 healthy on its target node post-drill; all 8 replication jobs OK with fail_count=0.

## Security considerations

No impact, all internal:
- Instrumentation harness runs inside ct:162 — same trust boundary as the existing CT.
- External TCP peer (`nc -kl` on pve1) listens on a high port, internal-only; not exposed beyond the LAN.
- No secrets, no credentials, no new network-facing services beyond the temporary `nc` listener (removed after the drill).
- `pvesr` and `ha-manager` invocations are root-API operations that already exist in the operator's trust model.
- AC-4's lag-injection writes random data to a file inside ct:162; cleanup is `rm /root/v4-1-load-data.bin` post-drill.

## Rollback procedure

1. **Stop the instrumentation harness** inside ct:162: `pct exec 162 -- pkill -f v4-1-instrumentation`. Remove pid-file: `pct exec 162 -- rm -f /var/run/v4-1-instrumentation.pid`.
2. **Stop the external TCP peer** on pve1: `ssh pve1 "screen -X -S v4-1-listener quit"`.
3. **If AC-4 ran**: re-enable replication on any disabled jobs, force a sync, verify fail_count=0:
   ```
   ssh pve2 "pvesr enable 162-0; pvesr enable 162-1"
   ssh pve2 "pvesr run --id 162-0 --verbose; pvesr run --id 162-1 --verbose"
   ssh pve2 "pvesr status"   # confirm OK + fail_count=0
   ```
4. **If migrate-back left ct:162 in error state**: standard error-state recovery sequence:
   ```
   ssh <home-node> "ha-manager set ct:162 --state disabled"
   # diagnose root cause via journal / pvesr status / zfs list
   ssh <home-node> "ha-manager set ct:162 --state started"
   ```
5. **Verify cluster health**: `pvecm status` 3/3 quorate, all replication jobs OK, ct:162 `started` on its target node.
6. **Optional**: clean up evidence bundle directories if they need to be discarded — usually kept as drill history.

Rollback restores the pre-6.6.1 state. The runbook updates are the only persistent artifacts; if 6.6.1 is rolled back entirely, `git checkout homelab-infra/docs/ha-replication-runbook.md` reverts those.

## References

- **Story 6.6 (V4 baseline)**: `homelab-playbook/_bmad-output/implementation-artifacts/6-6-validation-drill-v4-simulated-failover-via-migrate.md` — adversarial review R2 and R4 are absorbed by this story
- **Story 6.10 (HA exporter)**: `homelab-playbook/_bmad-output/implementation-artifacts/6-10-ha-state-prometheus-exporter.md` — runbook precedent
- **Story 6.5 (V3 RPO drill)**: `homelab-playbook/_bmad-output/implementation-artifacts/6-5-validation-drill-v3-replication-rpo-for-ct162.md` — heartbeat-file pattern
- **Story 6.9.1 (drill safety)**: `homelab-playbook/_bmad-output/implementation-artifacts/6-9-1-drill-safety-preconditions.md` — drill-window gate dependency
- **Memory: project_quant_trading.md**: `/home/developer/.claude/projects/-home-developer-workspace-homelab/memory/project_quant_trading.md` — ct:162 sensitivity; informs drill window
- **Memory: feedback_pve9_ha_error_recovery.md**: `/home/developer/.claude/projects/-home-developer-workspace-homelab/memory/feedback_pve9_ha_error_recovery.md` — error-state recovery sequence
- **Memory: project_pve3_storage_redesign.md**: `/home/developer/.claude/projects/-home-developer-workspace-homelab/memory/project_pve3_storage_redesign.md` — replication-snapshot semantics
- **PVE HA API**: <https://pve.proxmox.com/pve-docs/ha-manager.1.html>, `ha-manager crm-command migrate`
- **PVE replication API**: <https://pve.proxmox.com/pve-docs/pvesr.1.html>, `pvesr disable`, `pvesr enable`, `pvesr run`
