---
status: backlog
epic: 6
story: 6.9.2
title: Drill-safety lockfile resilience + --check-all UX
created: 2026-04-25
author: BMad SM
depends-on: 6-9-1
---

# Story 6.9.2: Drill-safety lockfile resilience + --check-all UX

Status: backlog

## Story

As an operator running drill-safety preflight at 03:00 after an incident,
I want the lockfile mechanism to recover gracefully from stranded locks (Ctrl-C, crash, kill -9, reboot-on-non-tmpfs `/var/lock`) and a `--check-all` mode that reports every gate's status in one pass instead of fail-fasting on the first refusal,
so that a stranded lockfile does not require `sudo rm` archaeology and a 3am operator can see the full failure surface in a single invocation rather than fix-and-rerun seven times.

## Business value

Story 6.9.1 shipped a 749-line `drill-safety-preflight.sh` with 8 fail-fast gates plus three lifecycle modes (`--lockfile-create`, `--lockfile-release`, `--post-drill-check`). It works correctly on the happy path. The adversarial review surfaced two related UX gaps that compound under pressure:

1. **Stranded lockfiles are high-friction recovery** (R1+R2). The current trap-based cleanup fires on `EXIT`, `SIGINT`, `SIGTERM` — but **not** on `SIGKILL` (`kill -9`), and not on a crash mid-drill. When that happens, the lockfile content is the operator's PID at lock creation time. There is no liveness check: subsequent drill invocations refuse with exit 14 ("another drill is in progress, PID=12345") even though PID 12345 has been dead for hours. The published recovery is `sudo rm /var/lock/homelab-drill-in-progress`, which works but is exactly the kind of error-prone workaround that gets cargo-culted into runbooks. A 3am operator who doesn't know whether the lockfile is real or stale will either wait pointlessly or `rm` it without checking — and `rm` without checking is the path that lets two real drills run concurrently.

2. **Fail-fast is wrong for diagnostic mode** (R10). The current `--check` flag claims diagnostic intent but inherits fail-fast semantics from the main loop in 6.9.1's gate runner. (The spec called for `--check` to print a per-gate table; the implementation kept fail-fast because the gates are sequenced cheap-to-expensive.) For an operator who runs preflight at 03:00 after pages and finds Gate 3 (cluster) failing, fixing that gate and re-running only to discover Gate 5 (HA state) was also failing is a 5-minute round-trip per gate. With six gates that can fail, that is a 30-minute pessimistic cycle. A non-fail-fast `--check-all` mode collapses that to one invocation: every gate runs, every failure surfaces, the operator fixes them all in parallel.

The pattern is: **6.9.1 made drills hard to run accidentally; 6.9.2 makes drill-safety hard to use wrong**. Both are operator-ergonomics stories; together they make the preflight script trustworthy enough that a future operator does not work around it.

## Absorbed finding

This story **absorbs** Story 6.9.1's adversarial-review findings **R1, R2 (lockfile resilience)** and **R10 (`--check-all` UX)**. R1+R2 were bundled because both are lockfile-state-machine concerns; R10 is bundled with them because all three are observably in the same code path (the gate runner that owns lockfile state and the gate-iteration loop). Splitting into three separate stories would cost more in cross-story coordination than the bundle costs in scope.

R3-R9 from the same review are out of scope here (they are story-spec gaps, not script-runtime gaps).

Per spec rule 5, sprint-status YAML edits are an operator-side step.

## Acceptance Criteria

### AC-1: Pre-flight verification

**Given** Story 6.9.1 is in `done` state
**And** the canonical script `homelab-infra/scripts/drill-safety-preflight.sh` exists at 749 lines (or the post-6.9.1 line count) with the 8 gates and three lifecycle modes
**And** the `drill-safety` Ansible role is deployed to pve1, pve2, pve3, and the operator workbench (`/usr/local/bin/drill-safety-preflight.sh` mode 0755 owner root:root)
**When** I run `drill-safety-preflight.sh --help` on each PVE node and the workbench
**Then** the script exists, is executable, and emits a usage banner that lists the post-6.9.1 flag set as the baseline this story extends

### AC-2: Stale-lockfile age check refuses new --lockfile-create

**Given** a lockfile exists at `/var/lock/homelab-drill-in-progress` with `STARTED=<epoch>` older than **4 hours wall-clock** AND the `PID=<n>` recorded in the lockfile is dead (per `kill -0 $PID` returning non-zero)
**When** I invoke `drill-safety-preflight.sh --lockfile-create --drill-name 6-X-foo`
**Then** the script auto-clears the stale lockfile, writes a new lockfile with the current PID/start/user/reason, and proceeds
**And** the auto-clear emits an audit-log line:
```
2026-04-25T03:14:22Z  user=tom  action=auto_clear_stale  prior_pid=12345  prior_started=2026-04-24T22:01:11Z  prior_age_hours=5.2  liveness=dead  result=cleared
```
**And** if the recorded PID **is alive** (`kill -0 $PID` returns zero) — regardless of lockfile age — the script REFUSES with exit 14 and a clear message that the drill is genuinely in progress (not auto-cleared, even at age >4h)
**And** if the lockfile age is **<4h** AND the PID is dead, the script REFUSES with exit 14 and instructs the operator to use `--lockfile-force-release --reason "..."` (the dead-PID-but-young-lock case is the ambiguous one — could be a crash 30 minutes ago that the operator is still investigating; auto-clear would discard live forensic state)
**And** the 4-hour threshold is configurable via env var `DRILL_LOCKFILE_STALE_AFTER_SECONDS` (default 14400) — sets the floor for "definitely abandoned"

### AC-3: PID-liveness probe in --lockfile-create

**Given** I invoke `drill-safety-preflight.sh --lockfile-create --drill-name 6-X-foo`
**And** a lockfile exists at `/var/lock/homelab-drill-in-progress`
**When** the script reads `PID=<n>` from the lockfile content
**Then** the script probes liveness via `kill -0 "$PID" 2>/dev/null`:
- **PID alive** → REFUSE with exit 14 + the existing 6.9.1 message (genuine in-progress drill)
- **PID dead AND age >= DRILL_LOCKFILE_STALE_AFTER_SECONDS** → auto-clear per AC-2 + proceed
- **PID dead AND age < DRILL_LOCKFILE_STALE_AFTER_SECONDS** → REFUSE with exit 14 + new message indicating the dead-PID + young-age ambiguity and pointing at `--lockfile-force-release`
**And** the liveness probe handles edge cases:
- Lockfile content malformed (no `PID=` line, or `PID=` value not an integer) → treat as stale and auto-clear (with audit entry `action=auto_clear_malformed`)
- `kill -0` permission-denied (would happen if the lockfile-creator was a different user than the script-runner; not expected since both run as root) → treat as alive (conservative — if we can't probe, assume live)
- Lockfile exists but is empty (touched, never written) → treat as malformed → auto-clear

### AC-4: --check-all mode runs every gate without fail-fast

**Given** the script is invoked with `--check-all` (a NEW flag)
**When** the script runs
**Then** the script:
1. Runs **all 8 gates** regardless of any individual gate's pass/fail outcome (no fail-fast)
2. Captures each gate's exit status, gate name, and one-line summary
3. Prints a consolidated table at the end of execution:
```
Gate                              Status    Detail
--------------------------------- --------- ----------------------------------------
1. Lockfile                       PASS      no in-progress drill
2. Time-window                    PASS      Saturday 03:14 CEST (off-hours)
3. Cluster quorate                FAIL      Quorate: No, Total votes: 2 (need 3)
4. Replication health             PASS      10/10 jobs OK, max fail_count=0
5. HA state                       FAIL      ct:162 (pve3) state=recovery
6. Replication coverage           PASS      4/4 non-pinned resources at 2+ peers
7. Evidence-stack health          PASS      prometheus 4d uptime, exporters fresh
8. Loop window                    SKIP      no --drill-script provided

Overall: 6 PASS, 2 FAIL, 0 BLOCKED, 1 SKIP. Drill would be REFUSED.
Exit code: 11 (first non-overridable failure: cluster quorate)
```
4. Exits with the **most-significant** non-zero exit code from any gate (priority ordering: 14 > 11 > 12 > 13 > 16 > 15 > 10 > 17 — non-overridable cluster-state gates rank above overridable ones)
5. The `--check` flag from 6.9.1 is preserved verbatim (always exits 0; for legacy callers); `--check-all` is the new diagnostic mode
**And** the consolidated table is also written to a structured file at `/var/log/homelab-drill-safety-check-all.json` (overwritten each invocation; not append-only — diagnostic snapshot, not audit) so an operator can `jq` the results into a dashboard or remediation script
**And** if BOTH `--check` and `--check-all` are passed simultaneously, `--check-all` wins (and the script prints a one-line warning that `--check` was overridden)

### AC-5: --lockfile-force-release flag with mandatory --reason

**Given** the operator has determined a lockfile is genuinely stale (e.g. via the dead-PID-but-young-age refusal in AC-3)
**When** I invoke `drill-safety-preflight.sh --lockfile-force-release --reason "post-incident cleanup; verified PID 12345 dead via ps"`
**Then** the script:
1. Refuses if `--reason` is missing (exit 2, same usage-error pattern as `--force`)
2. Reads the existing lockfile content (if any) to capture forensic state for the audit log
3. Removes `/var/lock/homelab-drill-in-progress` regardless of PID-liveness or age
4. Logs an audit entry:
```
2026-04-25T03:14:22Z  user=tom  action=force_release  prior_pid=12345  prior_started=2026-04-25T01:20:11Z  prior_age_hours=1.9  prior_liveness=dead  reason="post-incident cleanup; verified PID 12345 dead via ps"  result=cleared
```
5. Exits 0 on success
**And** if no lockfile exists at invocation time, exits 0 with a notice (`no lockfile to release`) and audit entry `action=force_release_noop` — idempotent for cron / Ansible callers
**And** the operator can chain a force-release into a fresh `--lockfile-create` in the same invocation by also passing `--lockfile-create --drill-name <name>` after the force-release; lifecycle order: force-release first, then create
**And** the audit-log entry is **always written** even if `/var/log/homelab-drill-safety.log` is non-writable, the script falls back to syslog (`logger -t drill-safety -p user.info`) so the force-release event is never silently lost

### AC-6: Self-test exercises the auto-clear path on a synthetic stranded lockfile

**Given** the script is in place per AC-1 through AC-5
**When** the implementer runs the self-test:
```
# 1. Create a stranded lockfile (orphan PID, old age)
ORPHAN_PID=99999  # confirmed not running via kill -0
echo "PID=$ORPHAN_PID
STARTED=$(date -d '-5 hours' +%s)
HOSTNAME=$(hostname)
USER=tom
REASON=synthetic-stale-test
DRILL_NAME=6-9-2-self-test" | sudo tee /var/lock/homelab-drill-in-progress

# 2. Run lockfile-create — should auto-clear and proceed
sudo /usr/local/bin/drill-safety-preflight.sh --lockfile-create --drill-name 6-9-2-recovery
echo "exit: $?"  # expect 0

# 3. Verify the audit log has the auto-clear entry
sudo grep auto_clear_stale /var/log/homelab-drill-safety.log | tail -1
```
**Then** the script auto-clears the synthetic stale lockfile (audit entry shows `prior_pid=99999  liveness=dead  prior_age_hours≈5.0`)
**And** the new lockfile contains the live invocation's PID and current epoch
**And** the test sequence (steps 1-3) is captured at `_bmad-output/drill-evidence/6-9-2-self-test-<date>.txt`
**And** the same self-test is repeated with a **live** PID (`ORPHAN_PID=$$` of a running shell) — script REFUSES with exit 14 (real-conflict path; verifies AC-3 alive-PID branch)
**And** the same self-test is repeated with a **dead PID + young age** (`STARTED=$(date -d '-1 hour' +%s)`) — script REFUSES with exit 14 + the `--lockfile-force-release` instruction (verifies AC-3 ambiguous-young-dead path)

### AC-7: README and runbook updated with stale-lockfile recovery procedure

**Given** AC-2 through AC-6 are in place
**When** I read `homelab-infra/ansible/roles/drill-safety/README.md` and the parent runbook
**Then** the README has a new "Stale lockfile recovery" section that documents:
- The 3-state decision tree (alive PID → wait; dead PID + age >= 4h → auto-clear on next `--lockfile-create`; dead PID + age < 4h → operator decides via `--lockfile-force-release`)
- How to verify a PID is dead before forcing (`ps -p <pid>` shows nothing)
- The `--lockfile-force-release --reason "..."` usage with an example reason
- The `DRILL_LOCKFILE_STALE_AFTER_SECONDS` env-var override (when an operator wants a tighter or looser threshold for a specific situation)
- The audit-log location and how to grep for force-release events
**And** the existing 6.9.1-era guidance to `sudo rm /var/lock/homelab-drill-in-progress` is **explicitly deprecated** in the README (callout: "Do NOT use plain `rm` — use `--lockfile-force-release --reason` so the action is audit-logged. Plain `rm` works but breaks the audit trail.")
**And** the `--check-all` mode is documented in the README's Usage section with a sample output (the table from AC-4)

## Tasks

- [ ] **Task 0: Pre-flight + dependency verification**
  - Cluster quorate; Story 6.9.1 in `done`; canonical script + Ansible role both present.
  - Confirm `/var/lock/homelab-drill-in-progress` is **absent** (no leaked lock from prior testing).
  - Confirm `/var/log/homelab-drill-safety.log` exists (or the script will create it on first invocation).

- [ ] **Task 1: Add PID-liveness + age check to `--lockfile-create`** (AC-2, AC-3)
  - Refactor the existing `lockfile_create()` function in `drill-safety-preflight.sh` to a 3-state decision tree (live / dead+old / dead+young / malformed).
  - Add helper `lockfile_parse()` that reads `/var/lock/homelab-drill-in-progress` and emits a struct (assoc array) of PID/STARTED/HOSTNAME/USER/REASON/DRILL_NAME, with `MALFORMED=1` on parse failure.
  - Add helper `lockfile_age_seconds()` that returns `$(( $(date +%s) - STARTED ))`, or `-1` if STARTED is unparseable.
  - Add helper `pid_alive()` that wraps `kill -0 "$PID" 2>/dev/null`.
  - Wire the decision tree into `lockfile_create()`.
  - Audit-log every state transition (`auto_clear_stale`, `auto_clear_malformed`, `refuse_alive`, `refuse_young_dead`).
  - `bash -n` + `shellcheck` clean.

- [ ] **Task 2: Implement `--check-all` mode** (AC-4)
  - Add `--check-all` to the argument-parse switch; mutually-exclusive-with-warning vs `--check`.
  - Refactor `run_gates()` to take a `FAIL_FAST=0|1` parameter; existing default behaviour preserved (FAIL_FAST=1).
  - In `--check-all` mode, run with `FAIL_FAST=0`; capture each gate's status into an associative-array results table.
  - Implement `print_gate_table()` that formats the AC-4 table.
  - Implement `gate_priority_exit()` that returns the most-significant non-zero exit code per the AC-4 priority list.
  - Write the structured results to `/var/log/homelab-drill-safety-check-all.json` (overwritten each invocation).

- [ ] **Task 3: Implement `--lockfile-force-release`** (AC-5)
  - Add `--lockfile-force-release` to the argument-parse switch.
  - Refuse if `--reason` is missing (exit 2).
  - Read existing lockfile (if any) for forensic-state capture.
  - Remove the lockfile.
  - Audit-log entry includes `prior_pid`, `prior_started`, `prior_age_hours`, `prior_liveness` (probed before removal), `reason`, `result`.
  - Fall back to syslog (`logger`) if the audit-log file is non-writable.
  - Idempotent: no-op exit 0 if no lockfile present.
  - Support chained invocation (`--lockfile-force-release --reason "..." --lockfile-create --drill-name "..."`) by sequencing release-then-create in the main flow.

- [ ] **Task 4: Self-test** (AC-6)
  - Synthetic stale lockfile (orphan PID 99999, started -5h) → expect auto-clear + new lock created → PASS.
  - Synthetic live lockfile (PID = `$$` of running shell, age irrelevant) → expect REFUSE exit 14.
  - Synthetic young-dead lockfile (orphan PID, age 1h) → expect REFUSE exit 14 + `--lockfile-force-release` instruction.
  - Synthetic malformed lockfile (random text, no `PID=` line) → expect auto-clear (malformed branch).
  - `--check-all` against the live healthy cluster → expect 8 PASS rows with overall exit 0.
  - `--check-all` with synthetic-failed Gate 1 (touch the lockfile first) → expect 7 PASS + 1 FAIL with overall exit 14.
  - Capture all transcripts at `_bmad-output/drill-evidence/6-9-2-self-test-<date>.txt`.

- [ ] **Task 5: README + runbook update** (AC-7)
  - Add "Stale lockfile recovery" section to `homelab-infra/ansible/roles/drill-safety/README.md`.
  - Add a small section on `--check-all` to the same README.
  - Deprecate the 6.9.1-era `sudo rm` guidance with an explicit callout.
  - Cross-reference 6.9.1 (parent) and 6.9.2 (this story).

- [ ] **Task 6: Final-state evidence + status flip**
  - Verify `/var/log/homelab-drill-safety.log` shows the audit entries from Task 4.
  - Verify `/var/log/homelab-drill-safety-check-all.json` exists and is parseable JSON.
  - Verify `/var/lock/homelab-drill-in-progress` is absent at end-of-test.
  - Append Dev Agent Record per Story 6.9.1 pattern.
  - Frontmatter `backlog → review`.

## Dev Notes

### PID-liveness via `kill -0`

`kill -0 "$PID"` sends signal 0 — a no-op signal that just returns 0 if the process exists and the caller has permission to signal it, non-zero otherwise. As root, the permission check is always satisfied; the only return-non-zero path is "no such PID". This is the canonical UNIX liveness check; no `/proc/<pid>` parsing required.

Edge case: PID reuse. After a reboot, PID counters restart at low numbers; a recorded PID of 12345 from before reboot might be reused by a different process post-reboot. `/var/lock` is tmpfs on Debian so reboot clears the lockfile naturally — but on non-tmpfs `/var/lock`, the recorded PID could collide with an unrelated post-reboot process. The 4-hour age threshold catches this in practice (any reboot followed by 4h of uptime gives the auto-clear path), but for paranoid correctness the script can also compare `STARTED` against `/proc/<pid>/stat` field 22 (`starttime` in clock ticks since boot) — if the lockfile claims STARTED=epoch_X but the running PID has a `starttime` corresponding to an epoch later than X, it's a different process. Optional hardening, not required for AC.

### `flock` + auto-clear interaction

The 6.9.1 script uses `(set -o noclobber; > "$LOCK") 2>/dev/null` for atomic claim. Auto-clear changes that pattern to:
```bash
if [[ -e "$LOCK" ]]; then
    parse_lockfile "$LOCK"
    if pid_alive "$PID"; then
        refuse_with_exit 14
    elif [[ "$(lockfile_age_seconds)" -ge "$STALE_AFTER" ]]; then
        audit_log "auto_clear_stale" "..."
        rm -f "$LOCK"
    elif [[ "$MALFORMED" == "1" ]]; then
        audit_log "auto_clear_malformed" "..."
        rm -f "$LOCK"
    else
        refuse_with_exit 14 "young-dead"
    fi
fi
# Now atomic claim:
( set -o noclobber; printf '%s\n' "PID=$$ STARTED=$(date +%s) ..." > "$LOCK" ) 2>/dev/null
```

The atomic-claim still races against another invocation that also passes the auto-clear branch — but in practice the only two callers are the operator's own shell and the Ansible role, and neither runs concurrently in a healthy operations model. Adding `flock -n` around the claim is belt-and-braces if needed; the 6.9.1 script already uses `flock` patterns elsewhere.

### Non-fail-fast gate runner

The 6.9.1 `run_gates()` function (single-call iteration with early return on first non-zero) needs minimal refactor:
```bash
run_gates() {
    local fail_fast="${1:-1}"
    declare -gA GATE_RESULTS=()
    local first_fail_exit=0
    for gate in "${GATES[@]}"; do
        local exit_code
        "$gate"; exit_code=$?
        GATE_RESULTS["$gate"]="$exit_code"
        if [[ "$exit_code" -ne 0 ]]; then
            [[ "$first_fail_exit" -eq 0 ]] && first_fail_exit="$exit_code"
            [[ "$fail_fast" -eq 1 ]] && return "$exit_code"
        fi
    done
    return "$first_fail_exit"  # 0 if all passed, else most-significant via gate_priority_exit
}
```
The structured-results emission to JSON is a 5-line `printf` formatter against the `GATE_RESULTS` array.

### Exit-code priority ordering

| Code | Gate | Overridable? | Severity |
|---|---|---|---|
| 14 | Lockfile | No | High (concurrent-drill class) |
| 11 | Cluster quorum | No | High (data-loss class) |
| 12 | Replication health | No | High |
| 13 | HA state | No | High |
| 16 | Replication coverage | No | High |
| 15 | Evidence stack | No | Medium (observability gap) |
| 10 | Time window | Yes (`--force`) | Medium (operator-discipline) |
| 17 | Loop window | Yes (`--force`) | Medium (alert-coverage UX) |

Priority for `--check-all` exit code: **non-overridable High first, then Medium, then overridable**. The list above is in priority order. If multiple gates fail, the most-significant becomes the overall exit code.

### File layout

**homelab-infra/** (modify):
- `scripts/drill-safety-preflight.sh` — refactor `lockfile_create()`, add `--check-all`, add `--lockfile-force-release`, add helpers (`lockfile_parse`, `pid_alive`, `gate_priority_exit`, `print_gate_table`)
- `ansible/roles/drill-safety/files/drill-safety-preflight.sh` — mirror update (the 6.9.1 sibling-role precedent)
- `ansible/roles/drill-safety/README.md` — add "Stale lockfile recovery" section + `--check-all` usage

### Prior art references

- **Story 6.9.1** — the script this story extends. All semantics and audit-log format inherit from it.
- **Story 6.10** — exporter pattern for `flock` + `timeout` + atomic-write; same defensive coding standards apply here.
- **Bash `kill -0` reference**: <https://man7.org/linux/man-pages/man1/kill.1.html> (BSD/POSIX `kill -0`)
- **flock atomic-claim (`set -o noclobber`)**: <https://mywiki.wooledge.org/BashFAQ/045>

## Test strategy

**Phase 1 (Task 0):** observation only.

**Phase 2 (Tasks 1-3):** script edits; `bash -n` and `shellcheck` are the correctness checks. No live cluster state changes.

**Phase 3 (Task 4):** **load-bearing AC**. Synthetic lockfile manipulation is zero-risk (just `tee` and `rm` to `/var/lock`). All four lockfile decision-tree paths exercised + `--check-all` exercised against live + synthetic-failed cluster state.

**Phase 4 (Tasks 5-6):** documentation + status flip. No production state change.

**Test acceptance**: `_bmad-output/drill-evidence/6-9-2-self-test-<date>.txt` shows all four lockfile decision-tree branches + both `--check-all` paths exercised correctly.

## Security considerations

- The audit-log integrity for `--lockfile-force-release` is the security-relevant property of this story. The append-only log + syslog fallback makes it hard for a force-release event to be silently lost. Tampering with `/var/log/homelab-drill-safety.log` is a root-only operation (mode 0644 owner root); operator-trust model assumes the operator does not erase their own audit trail. Routing to syslog → centralised aggregation is a hardening follow-up (out of scope).
- No new credentials, no new network-facing services. The `--lockfile-force-release` reason string is logged verbatim, never interpreted as a command (no injection surface).
- The malformed-lockfile auto-clear branch (AC-3) is the smallest expansion of the auto-clear surface — it removes a lockfile whose content is unparseable. An attacker who can write to `/var/lock` already has root-equivalent access; the malformed branch does not increase their attack surface.
- `kill -0` against unrelated PIDs reveals "this PID exists" to the script — already common-knowledge from `/proc` scanning; not a privilege expansion.

## Rollback procedure

The script changes are additive (new flags, new code paths, refactored helpers). If the new behaviour causes unexpected refusals or auto-clears:
1. **Revert the script file**: `git checkout homelab-infra/scripts/drill-safety-preflight.sh` and `git checkout homelab-infra/ansible/roles/drill-safety/files/drill-safety-preflight.sh`.
2. **Re-run the Ansible role** to push the reverted script to all PVE nodes + workbench.
3. **Lockfile state**: any in-flight lockfile from the new code is bit-compatible with the 6.9.1 format (same fields), so no lockfile cleanup needed on rollback.
4. **Audit log**: leave intact (append-only forensic trail).

The pre-6.9.2 state is the 6.9.1 published baseline — fully functional, just with the high-friction recovery path. Rollback restores that baseline without data loss.

## References

- **Adversarial finding source**: Story 6.9.1 review, R1+R2 (lockfile resilience) and R10 (`--check-all` UX)
- **Parent story**: `homelab-playbook/_bmad-output/implementation-artifacts/6-9-1-drill-safety-preconditions.md`
- **Structural template**: `6-2-verify-replication-state-and-deltas.md`
- **Canonical script (post-6.9.1)**: `homelab-infra/scripts/drill-safety-preflight.sh`
- **Ansible role**: `homelab-infra/ansible/roles/drill-safety/`
- **Bash `kill -0`**: <https://man7.org/linux/man-pages/man1/kill.1.html>
- **flock atomic-claim**: <https://mywiki.wooledge.org/BashFAQ/045>
- **Tmpfs `/var/lock` on Debian**: <https://wiki.debian.org/var/lock> (relevant to lockfile-survives-reboot edge case)

## Change Log

- **2026-04-25**: Story created by BMad SM as Story 6.9.1's adversarial-review follow-up (absorbs R1+R2+R10).
