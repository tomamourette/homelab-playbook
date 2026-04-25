---
status: backlog
epic: 6
story: 6.9.4
title: NTP sync precondition for drill-safety preflight (Gate 0 soft warning)
created: 2026-04-25
author: BMad SM
depends-on: 6-9-1
---

# Story 6.9.4: NTP sync precondition for drill-safety preflight (Gate 0 soft warning)

Status: backlog

## Story

As an operator running drill-safety preflight,
I want a Gate 0 NTP-sync precondition that loudly warns (but does NOT refuse) when the operator workbench OR any cluster node has unsynced NTP,
so that a skewed clock — which would silently make Gate 2's time-window check return the wrong day-of-week or hour and either let an unsafe drill proceed or block a safe one — is visible to the operator before the rest of the gate sequence relies on `date +%u`.

## Business value

Story 6.9.1's Gate 2 (time-window) trusts `TZ=Europe/Brussels date +%u` and `+%H` to derive day-of-week and hour. The implementation correctly handles DST transitions and non-Europe/Brussels host clocks via `TZ=`. **What it does not handle is a host clock that is wrong by hours**.

The adversarial-review finding R5 from 6.9.1 named the case: "if `chrony.service` is failed (Story 6.11 alert), the time check could be wrong." A skewed clock produces two failure modes that matter:

1. **False time-window failure (false positive)**: a healthy off-hours operator runs preflight at 03:00 Saturday CEST, but the host clock is stuck on 14:30 Tuesday CEST from a chrony failure 4 days ago. Gate 2 refuses with "weekday market-hours window" — the operator is blocked from a legitimate weekend drill until they realise the clock is wrong. High-friction, but safe: false-positive refusals don't damage anything.

2. **False time-window pass (false negative — the dangerous case)**: a clock skew in the **opposite** direction makes a Tuesday-14:00 invocation look like Saturday-03:00 to the script. Gate 2 passes; the drill proceeds during ct:162's market-hours window; the missed-fill events accumulate. This is exactly the scenario 6.9.1 was chartered to prevent.

The 6.9.1 Dev Notes acknowledge this gap as a "known limitation" deferred to Story 6.11's chrony health alert. But the chrony alert is a **monitoring** signal — it pages the operator at 14:30 Tuesday when chrony breaks. It does NOT enforce anything at drill-execution time. An operator who ignores or hasn't seen the chrony page can still run preflight and get a false-pass.

The fix is a Gate 0 (numbered explicitly to indicate it runs **before** all other gates) that checks `timedatectl show -p NTPSynchronized --value` on:
- The local host running the script (operator workbench)
- Each PVE node (pve1, pve2, pve3)

If any returns `no` (or `false` on older systemd; the spec is ambiguous — Task 0 confirms), Gate 0 emits a **loud warning** but does **not** refuse the drill. The rationale for soft-warn (not fail-closed):

- **Most clock skews are minor and harmless**. Chrony briefly losing its upstream NTP servers leaves the local clock as the previous-good — drift is bounded by chrony's last sync (typically <1ms even after hours of upstream loss). Gate 2's hour-granularity check tolerates seconds-to-minutes of drift comfortably.

- **The dangerous case (hours-of-skew) is rare**. It requires either chrony to have been off long enough for clock-source-drift to accumulate, or a deliberate `date set` operation. The warning surfaces both — operator decides if the drill proceeds.

- **Hard-refuse on NTP would block legitimate drills during transient NTP unavailability**. NTP server churn (upstream pool member rotation, DNS resolution flap) can leave `NTPSynchronized=no` for minutes at a time on a clock that's actually fine. A fail-closed gate would block drills during these windows for no real safety gain.

- **The gate's value is the WARNING — operator awareness — not the refusal**. Once the operator knows clock state is uncertain, they can verify with `chronyc tracking` or `ntpstat` before proceeding.

The pattern is: **soft-warning gates raise visibility without imposing friction; the operator decides**. This is the **opposite** of 6.9.1's fail-closed gates (which refuse non-overridably for cluster-state catastrophes). NTP skew is a precondition that makes other gates' checks unreliable, not a catastrophe in its own right.

## Absorbed finding

This story **absorbs** Story 6.9.1's adversarial-review finding **R5 — NTP sync precondition**: "Gate 2 trusts `TZ=Europe/Brussels date +%u`. Skewed clock → wrong gate result. NTP sync is a precondition the script doesn't check today."

R5b (the false-negative variant — clock skew that causes a market-hours drill to pass Gate 2) is the dangerous failure mode; this story addresses both R5 and R5b under one gate.

R1, R2, R4, R10 from the same review are out of scope here (they are addressed by Stories 6.9.2 and 6.9.3).

Per spec rule 5, sprint-status YAML edits are an operator-side step.

## Acceptance Criteria

### AC-1: Pre-flight verification

**Given** Story 6.9.1 is in `done` state
**And** the canonical script `homelab-infra/scripts/drill-safety-preflight.sh` exists with the 8 gates and lifecycle modes from 6.9.1
**And** the `drill-safety` Ansible role is deployed to pve1, pve2, pve3, and the operator workbench
**When** I run `drill-safety-preflight.sh --check-all` on the operator workbench (or `--check` if 6.9.2 is not yet shipped)
**Then** the existing 8 gates report PASS (or whatever cluster state warrants); this story will add Gate 0 ahead of them

### AC-2: Add `gate_ntp` (numbered 0 — runs before all other gates)

**Given** the script is invoked (with or without `--force`, with or without `--check-all`)
**When** the script enters the gate-runner
**Then** the **first gate that runs** is `gate_ntp` (named "Gate 0" in the per-gate output table to indicate explicitly that it runs before Gate 1):
```bash
gate_ntp() {
    local result=PASS
    local detail=""
    local checked_hosts=()
    
    # Local host (operator workbench)
    local local_sync
    local_sync=$(timedatectl show -p NTPSynchronized --value 2>/dev/null || echo "unknown")
    checked_hosts+=("local:$local_sync")
    if [[ "$local_sync" != "yes" ]]; then
        result=WARN
        detail="$detail local=$local_sync"
    fi
    
    # PVE nodes
    for node in pve1 pve2 pve3; do
        local node_sync
        node_sync=$(timeout 10 ssh -o BatchMode=yes "$node" \
            "timedatectl show -p NTPSynchronized --value" 2>/dev/null || echo "ssh-failed")
        checked_hosts+=("$node:$node_sync")
        if [[ "$node_sync" != "yes" ]]; then
            result=WARN
            detail="$detail $node=$node_sync"
        fi
    done
    
    if [[ "$result" == "WARN" ]]; then
        emit_warning "Gate 0 NTP" "$detail (hosts: ${checked_hosts[*]})"
    else
        emit_pass "Gate 0 NTP" "all 4 hosts NTPSynchronized=yes"
    fi
    return 0   # Soft-warn — never returns non-zero
}
```
**And** the gate is invoked **before** all existing gates (Lockfile, Time-window, Cluster, Replication, HA, Coverage, Evidence-stack, Loop-window) — its output is the first row of the `--check-all` table
**And** the gate handles edge cases:
- `timedatectl` not installed (older systems pre-systemd) → result UNKNOWN with message; soft-warn
- SSH timeout to a node → result `ssh-failed` for that node; warn that the node's NTP state is indeterminate
- `NTPSynchronized=no` (modern systemd default) → warn
- `NTPSynchronized=false` (older systemd output format) → warn (treat any non-`yes` as warn)
- `NTPSynchronized=unknown` (rare) → warn
- A node's `timedatectl` output format unexpected → warn with the raw value captured for forensics

### AC-3: Soft-warning behaviour — does NOT exit non-zero

**Given** Gate 0 detects unsynced NTP on one or more hosts
**When** the script continues through subsequent gates
**Then** the script:
- Emits a **loud warning** to stderr — formatted to stand out in terminal output (color if `--no-color` not passed; ALL-CAPS leader; multi-line):
```
================================================================================
WARNING — Gate 0: NTP NOT SYNCED
  Hosts with non-synchronized clocks:
    local (ct-dev-homelab):    no
    pve3:                       ssh-failed (ssh timeout)
  
  Subsequent time-based gates (Gate 2 time-window) MAY return incorrect
  results if clock skew exceeds gate granularity (1 hour for time-window).
  
  Verify with:
    chronyc tracking           # operator workbench
    ssh pve1 chronyc tracking  # each PVE node
  
  This gate does NOT refuse the drill. Operator: decide whether to proceed.
================================================================================
```
- Continues to Gate 1 and subsequent gates normally
- The Gate 0 row in `--check-all`'s consolidated table shows `WARN` (a new third state distinct from `PASS` and `FAIL`) — does NOT contribute to the overall exit code
- The audit log records the warning with explicit warn-level marker:
```
2026-04-25T03:14:22Z  user=tom  gate=0_ntp  result=WARN  detail="local=no pve3=ssh-failed"
```
- The `--check-all` table's "Overall: ..." line counts WARN separately:
```
Overall: 7 PASS, 1 WARN, 0 FAIL, 0 BLOCKED, 0 SKIP. Drill would PROCEED with operator awareness.
```
**And** the soft-warning behaviour is intentional — opposite of the fail-closed Gates 1, 3, 4, 5, 6, 7. Documented in the inline comments and the Dev Notes.
**And** there is **no `--force` override needed** for Gate 0 because there's nothing to override — the gate never refuses

### AC-4: README + runbook update with NTP precondition documentation

**Given** AC-2 and AC-3 are in place
**When** I update `homelab-infra/ansible/roles/drill-safety/README.md` and the `homelab-infra/docs/ha-replication-runbook.md` runbook
**Then** the README has a new "Gate 0 — NTP sync precondition" section that documents:
- What the gate checks (local + 3 PVE nodes via `timedatectl`)
- Why it's soft-warn (rationale per the Business Value section above — minor skew is harmless, hard-refuse blocks legitimate drills, the value is operator awareness)
- The two failure modes the gate guards against (false-positive refusal during clock skew; false-negative pass during opposite-direction clock skew)
- The chronyc / systemd-timesyncd troubleshooting reference (next sub-AC)
**And** the runbook has a new "NTP precondition" subsection (sibling to the existing 6.9.1 §"Drill safety preconditions") that documents:
- The chrony / systemd-timesyncd troubleshooting flow:
  ```
  # On any host with NTPSynchronized=no:
  
  # Which NTP service is running?
  systemctl status chrony chronyd systemd-timesyncd
  
  # Chrony tracking + sources (most informative):
  chronyc tracking
  chronyc sources -v
  
  # systemd-timesyncd status (alternative):
  timedatectl status
  
  # Force a sync:
  sudo chronyc -a 'burst 4/4'        # chrony
  sudo systemctl restart systemd-timesyncd
  
  # Verify:
  timedatectl show -p NTPSynchronized --value   # should print "yes"
  ```
- The known-PVE-default: PVE 9.x ships with `chrony` enabled by default; the operator workbench (ct-dev-homelab, Debian 13) ships with `systemd-timesyncd` by default. Both are checked uniformly via `timedatectl`.
- Cross-reference to Story 6.11 (chrony health alert) — the prometheus-side monitoring complement to this preflight-side warning.
- A worked example: simulated unsynced clock → Gate 0 warning → operator runs `chronyc tracking` → finds upstream pool flap → waits 60s → re-runs preflight → Gate 0 PASSes.

### AC-5: Self-test — simulate NTP unsynced and verify warning fires; restore and verify warning clears

**Given** AC-2 through AC-4 are in place
**When** the implementer runs the self-test on the operator workbench:
```bash
# 1. Capture baseline (NTP synced)
sudo timedatectl set-ntp false   # disables NTP sync
sleep 2
timedatectl show -p NTPSynchronized --value   # should print "no"

# 2. Run preflight; expect Gate 0 to WARN, other gates to proceed
sudo /usr/local/bin/drill-safety-preflight.sh --check-all 2>&1 | tee /tmp/6-9-4-warn-test.txt

# 3. Verify the Gate 0 warning is in the output
grep -i "WARNING.*Gate 0.*NTP" /tmp/6-9-4-warn-test.txt   # expect non-empty match
grep -E "Overall:.*1 WARN" /tmp/6-9-4-warn-test.txt        # expect non-empty match

# 4. Verify exit code is 0 (or whatever the other gates would naturally produce — Gate 0 itself doesn't change it)
echo "exit: $?"

# 5. Restore NTP and verify warning clears
sudo timedatectl set-ntp true
sleep 5   # let chrony/timesyncd resync
timedatectl show -p NTPSynchronized --value   # should print "yes"
sudo /usr/local/bin/drill-safety-preflight.sh --check-all 2>&1 | tee /tmp/6-9-4-clear-test.txt
grep -E "Overall:.*0 WARN" /tmp/6-9-4-clear-test.txt   # expect non-empty match
```
**Then** step 3 confirms the warning fires when NTP is unsynced (Gate 0 row shows WARN; loud warning emitted to stderr)
**And** step 4 confirms the script exits per the OTHER gates' results — Gate 0 itself never returns non-zero (verified by the WARN counter being separate from the FAIL counter)
**And** step 5 confirms the warning clears once NTP resyncs (Gate 0 row shows PASS; no warning emitted)
**And** the test transcript is captured at `_bmad-output/drill-evidence/6-9-4-self-test-<date>.txt`
**And** a parallel test simulates SSH-failed-to-pve3 (e.g. `--add-known-hosts` with a wrong key for pve3 transiently) to verify the `ssh-failed` branch produces the same WARN result without crashing the gate

## Tasks

- [ ] **Task 0: Pre-flight + dependency verification + `timedatectl` output format check**
  - Cluster quorate; Story 6.9.1 in `done`; canonical preflight script + Ansible role both present.
  - Confirm `timedatectl show -p NTPSynchronized --value` works on:
    - Operator workbench (ct-dev-homelab, Debian 13)
    - pve1, pve2, pve3 (PVE 9.x)
  - Capture exact output strings (`yes`, `no`, `false`, `unknown`?) per host. The gate logic in AC-2 treats anything other than `yes` as warn — confirm there are no surprise output formats.
  - Confirm SSH from operator workbench → pve1/pve2/pve3 works in `BatchMode=yes` (no password prompt) for all three nodes. If not, document the gap; the gate will report `ssh-failed` for any unreachable node.

- [ ] **Task 1: Implement `gate_ntp` (Gate 0)** (AC-2, AC-3)
  - Add `gate_ntp()` function to `drill-safety-preflight.sh`.
  - Insert into the `GATES=()` array at index 0 — runs before all existing gates.
  - Helper `check_ntp_local()` — wraps `timedatectl show -p NTPSynchronized --value`.
  - Helper `check_ntp_remote(node)` — wraps `timeout 10 ssh -o BatchMode=yes "$node" "timedatectl show -p NTPSynchronized --value"`.
  - Result aggregation: any host non-`yes` → result=WARN; all `yes` → result=PASS; `timedatectl` missing → result=UNKNOWN (treat as WARN per AC-2).
  - Implement `emit_warning()` formatter for the multi-line stderr block (AC-3 specifies the exact format).
  - Audit-log entry includes `gate=0_ntp` marker so logs can be filtered.
  - Update `--check-all` table formatter to recognize a third state `WARN` (alongside `PASS` / `FAIL` / `BLOCKED` / `SKIP`).
  - Update the table's "Overall: ..." footer to include `WARN` count.
  - `bash -n` + `shellcheck` clean.

- [ ] **Task 2: README + runbook update** (AC-4)
  - Add "Gate 0 — NTP sync precondition" section to `homelab-infra/ansible/roles/drill-safety/README.md`.
  - Add "NTP precondition" subsection to `homelab-infra/docs/ha-replication-runbook.md` (sibling of the existing §"Drill safety preconditions").
  - Include the chrony / timesyncd troubleshooting block verbatim from AC-4.
  - Cross-reference Story 6.11 (chrony health alert) — note the prometheus-side complement.
  - Cross-reference 6.9.1 (parent) — note that Gate 0 was deferred from 6.9.1's R5 finding.

- [ ] **Task 3: Self-test** (AC-5)
  - Run the AC-5 test sequence on the operator workbench.
  - Capture transcript at `_bmad-output/drill-evidence/6-9-4-self-test-<date>.txt`.
  - Verify the WARN-fire / WARN-clear paths.
  - Verify the SSH-failed branch (transient unreachable node) produces WARN without crashing.
  - Restore the workbench's NTP-sync state to `true` at end of test (cleanup).

- [ ] **Task 4: Final-state evidence + status flip**
  - Verify `/var/log/homelab-drill-safety.log` shows Gate 0 audit entries from Task 3.
  - Verify the workbench's `timedatectl show -p NTPSynchronized --value` returns `yes` (cleanup confirmed).
  - Append Dev Agent Record per 6.9.1 pattern.
  - Frontmatter `backlog → review`.

## Dev Notes

### `timedatectl show -p NTPSynchronized --value` output format

Modern systemd (≥ v239) emits one of:
- `yes` — NTP is synced
- `no` — NTP is not synced (or NTP is disabled via `set-ntp false`)
- empty string — `NTPSynchronized` property not exposed (very old systemd)

Older systemd may emit `true` / `false` instead of `yes` / `no`. The gate logic treats anything other than `yes` as warn — no need to enumerate all variants, just the positive case.

PVE 9.x ships systemd v254+ (`yes`/`no` format). Debian 13 ships systemd v257 (same format). Task 0 confirms.

### `chrony` vs `systemd-timesyncd`

Both NTP services expose state through `timedatectl` — the gate doesn't care which is running. Default per platform:
- **PVE 9.x**: `chrony.service` (chronyd daemon)
- **Debian 13 cloud-init / minimal**: `systemd-timesyncd.service`
- **Debian 13 + ntpsec installed**: `ntpsec.service` (less common)

The runbook's troubleshooting section (AC-4) covers all three. Operator runs whichever applies on the affected host.

### Why Gate 0 (not Gate 1)?

The 6.9.1 gate-priority list (Dev Notes §"Gate priority and fail-fast") puts Lockfile at position 1 because it's the cheapest local check. Gate 0 (NTP) is even cheaper (one `timedatectl` invocation) AND it modifies the trustworthiness of subsequent time-based gates (Gate 2 in particular). Numbering it `0` rather than re-renumbering all other gates:
- Preserves the historical numbering from 6.9.1 (operators have memorised "Gate 2 = time window")
- Signals "this runs before everything else, including the cheap local checks" — it's a *meta-check* on the host's clock, not a state check
- Matches the prefix `0_` used in shell-script ordering conventions (e.g. `00-preflight`, `0_init`)

### Why soft-warn (not fail-closed)?

The 6.9.1 design philosophy is **fail-closed for cluster-state catastrophes** (broken quorum, broken replication, broken HA). NTP unsynced is **not** a cluster-state catastrophe — it's a precondition that makes ONE other gate's check unreliable. Hard-refusing on NTP unsynced would:
- Block legitimate drills during transient NTP unavailability (NTP server churn happens regularly)
- Block drills on a freshly-rebooted host before NTP has had time to sync (chrony's first sync after boot is typically 30s-2min)
- Block drills on an operator workbench that uses systemd-timesyncd's "best-effort" mode where `NTPSynchronized=no` for several hours after boot is normal

Soft-warn is the right design: surface the uncertainty, let the operator decide. This is the same pattern the existing 6.9.1 gates use for transient HA states (`migrate`, `relocate`, `request_*`, `freeze` — tolerated as transient, not refused).

### Clock-skew tolerance: when does NTP sync actually matter?

Gate 2 checks day-of-week + hour. The granularity is **1 hour**. For Gate 2 to return the wrong day-of-week, clock skew would need to exceed:
- Day-of-week wrong: skew > 24 hours (very rare)
- Hour wrong: skew > 1 hour (possible after long NTP outage)

A clock with `NTPSynchronized=no` due to chrony losing upstream reach for 30 minutes typically has drift << 1 second (chrony's internal stability is sub-millisecond after a long sync history). The dangerous case is `NTPSynchronized=no` for **days** with no internal stability — e.g. a fresh VM with no chrony history that has never synced. Gate 0 catches both: the warn fires regardless of how bad the skew actually is, the operator does the verification.

### File layout

**homelab-infra/** (modify):
- `scripts/drill-safety-preflight.sh` — add `gate_ntp()`, add to GATES array at index 0, update `--check-all` table to recognize WARN state, add `emit_warning()` helper
- `ansible/roles/drill-safety/files/drill-safety-preflight.sh` — mirror update
- `ansible/roles/drill-safety/README.md` — add "Gate 0 — NTP sync precondition" section
- `docs/ha-replication-runbook.md` — add "NTP precondition" subsection with chrony/timesyncd troubleshooting

### Prior art references

- **Story 6.9.1** — the parent. Gate-runner architecture, audit-log format, `--check-all` table formatter all inherit.
- **Story 6.11** — chrony health alert (prometheus-side complement; this story is the preflight-side complement).
- **`timedatectl` man page**: <https://man7.org/linux/man-pages/man1/timedatectl.1.html>
- **`chronyc tracking` reference**: <https://chrony.tuxfamily.org/doc/4.0/chronyc.html#tracking>
- **systemd-timesyncd reference**: <https://www.freedesktop.org/software/systemd/man/systemd-timesyncd.service.html>

## Test strategy

**Phase 1 (Task 0):** observation + `timedatectl` output format verification. Captures any platform variance.

**Phase 2 (Task 1):** script edits; `bash -n` and `shellcheck` are correctness checks. No live cluster state changes (gate is read-only on each host).

**Phase 3 (Task 3):** **load-bearing AC**. `sudo timedatectl set-ntp false` on the operator workbench is a 2-line revert (`set-ntp true`) and zero-risk — does not affect cluster state. The simulated SSH-failed test uses transient SSH config manipulation, also zero-risk.

**Phase 4 (Tasks 2, 4):** documentation + status flip. No production state change.

**Test acceptance**: `_bmad-output/drill-evidence/6-9-4-self-test-<date>.txt` shows the WARN-fire path, the WARN-clear path, and the SSH-failed-to-node branch — all without affecting other gates' exit semantics.

## Security considerations

- **Local-host clock tampering as bypass**: a root-equivalent attacker who can `date set` the host clock to off-hours can bypass Gate 2 (time-window). Gate 0 surfaces the bypass (the manual `date set` typically leaves NTP unsynced — `timedatectl` reports `NTPSynchronized=no`). This is **defense in depth, not a complete defense**: an attacker who also enables NTP after their `date set` can re-sync the clock to a bogus value if they control an upstream NTP server. The trust model assumes the operator does not collude with their own host clock; Gate 0 raises the bar for accidental skew, not deliberate skew.
- **No new credentials, no new network surface**. The gate uses existing operator-workbench → PVE-node SSH (already required for 6.9.1's other gates).
- **SSH key compromise**: same trust model as 6.9.1 — operator's SSH key gates all PVE-node access; Gate 0 inherits that trust boundary.
- **`timedatectl` invocation safety**: read-only command; cannot modify system state. Even SSH'd to a remote PVE node, the gate cannot change anything.

## Rollback procedure

The script changes are additive (new gate, new helper, no existing-behaviour changes). If unexpected behaviour:
1. **Revert script files**: `git checkout homelab-infra/scripts/drill-safety-preflight.sh` and `git checkout homelab-infra/ansible/roles/drill-safety/files/drill-safety-preflight.sh`.
2. **Re-run Ansible role** to push reverted script to PVE nodes + workbench.
3. **No cluster state change** — Gate 0 is read-only; nothing to undo.

Rollback restores the pre-6.9.4 state where NTP sync is a known limitation deferred to Story 6.11's monitoring alert. The R5 finding re-opens.

## References

- **Adversarial finding source**: Story 6.9.1 review, R5 (NTP sync precondition)
- **Parent story**: `homelab-playbook/_bmad-output/implementation-artifacts/6-9-1-drill-safety-preconditions.md`
- **Sibling story** (chrony health alert; prometheus-side complement): Story 6.11 — referenced in 6.9.1 Dev Notes §"Risk / failure modes" item 1
- **Structural template**: `6-2-verify-replication-state-and-deltas.md`
- **Canonical preflight script (post-6.9.1)**: `homelab-infra/scripts/drill-safety-preflight.sh`
- **`timedatectl` man page**: <https://man7.org/linux/man-pages/man1/timedatectl.1.html>
- **`chrony` reference**: <https://chrony.tuxfamily.org/doc/4.0/>
- **`systemd-timesyncd` reference**: <https://www.freedesktop.org/software/systemd/man/systemd-timesyncd.service.html>

## Change Log

- **2026-04-25**: Story created by BMad SM as Story 6.9.1's adversarial-review follow-up (absorbs R5 — NTP sync precondition).
