---
status: backlog
epic: 6
story: 6.9.3
title: Drill-script evidence manifest + post-drill enforcement
created: 2026-04-25
author: BMad SM
depends-on: 6-9-1
---

# Story 6.9.3: Drill-script evidence manifest + post-drill enforcement

Status: backlog

## Story

As an operator running a drill,
I want the drill script itself to emit an authoritative evidence manifest at execution start (loop duration, gate versions, script SHA, start epoch) and a `--post-drill-check` that validates the manifest's claims against actual wall-clock observations,
so that Story 6.9.1's Gate 8 (loop-window validation) cannot be silently defeated by a drill that **claims** `LOOP_DURATION_S=600` but reassigns the variable mid-script — the static grep pre-check stays as a soft warning, but real enforcement happens against observed reality.

## Business value

Story 6.9.1's Gate 8 (AC-11) enforces a 10-minute minimum drill-loop window so that `for: 5m` Prometheus alerts have time to evaluate. The enforcement mechanism is a **static grep** of the drill script for the literal string `LOOP_DURATION_S=600` (or higher). This is brittle in a way that matters:

```bash
# Drill script that PASSES Gate 8's static grep but actually runs for 60s:
LOOP_DURATION_S=600    # passes the grep check
# ... 200 lines of drill setup ...
LOOP_DURATION_S=60     # silently overrides — dev was iterating and forgot to change back
T_INJECT=$(date +%s)
while [[ $(($(date +%s) - T_INJECT)) -lt $LOOP_DURATION_S ]]; do ...; done
```

The adversarial review (R4 from 6.9.1) named exactly this failure mode: "the drill claims a 600s loop but actually runs for 60s — Gate 8 cannot tell the difference, and three of six expected `for: 5m` alerts never get observed." This is a **false NEGATIVE on alert-chain validation** — the operator believes the drill validated alert delivery; in reality the drill ended before the alerts could fire. The V5 pull-plug-pve2 drill (2026-04-25, the very drill that surfaced AC-11 in 6.9.1) ended at T+313s for exactly this category of reason; only a wall-clock observation of actual elapsed time can catch it.

The fix is a two-layer enforcement:

1. **Static grep (existing Gate 8)** — kept, demoted to soft warning. Catches the obvious case (someone forgot to set the variable at all) but acknowledges its blind spot (variable reassignment).

2. **Drill-emitted evidence manifest (NEW)** — every drill script writes `_bmad-output/drill-evidence/<drill-name>/manifest.json` at execution start with declared `loop_duration_s`, `start_epoch`, `gate_versions`, `script_sha256`, and the actual values used at runtime. The manifest is **the drill's own self-report** — it cannot lie about what value the loop ACTUALLY ran with because the manifest is generated from the same `$LOOP_DURATION_S` variable the loop reads. A drill that reassigns the variable mid-flight is now detectable: the manifest captures the final value at exit time, and the post-drill check compares manifest claim to observed wall-clock duration.

3. **`--post-drill-check` gate (NEW Gate 9)** — reads the manifest after the drill completes and verifies: (a) manifest exists, (b) claimed `loop_duration_s >= 600`, (c) actual elapsed wall-clock time matches claim within 10% tolerance, (d) script SHA matches the script that the manifest claims to be from (tamper detection). Mismatch → exit non-zero, drill verdict reported as INVALID rather than PASS.

The pattern is: **6.9.1 Gate 8 protects against forgetfulness; 6.9.3 manifest+Gate 9 protects against deception (whether accidental or malicious)**. Together they make drill-loop-duration claims trustworthy enough that Stories 6.5/6.6/6.7/6.8/6.6.1 retroactive evidence can be re-validated.

## Absorbed finding

This story **absorbs** Story 6.9.1's adversarial-review finding **R4 (Gate 8 evidence-manifest enforcement)**: "The static grep can be lied to. A drill that defines `LOOP_DURATION_S=600` and reassigns to 60 mid-script passes Gate 8 trivially — false NEGATIVE on alert-chain validation."

R3 (stuck-SYNCING detection) and R5 (NTP sync precondition) from the same review are out of scope here. R5 is its own follow-up (Story 6.9.4).

Per spec rule 5, sprint-status YAML edits are an operator-side step.

## Acceptance Criteria

### AC-1: Pre-flight verification

**Given** Story 6.9.1 is in `done` state and Gate 8 (AC-11 static-grep enforcement) is deployed in `drill-safety-preflight.sh`
**And** the existing drill scripts (V3 / V4 / V5 / V6 — Stories 6.5 / 6.6 / 6.7 / 6.8) are present at the canonical path (operator-workbench-resident or `homelab-infra/scripts/drills/` — confirm location during Task 0)
**When** I run `drill-safety-preflight.sh --check-all` on the operator workbench
**Then** the existing 8 gates report PASS (or whatever the current cluster state warrants); Gate 8 is the gate this story will refactor
**And** the manifest spec in this story is consistent with the existing Gate 8 contract (i.e. the manifest carries `loop_duration_s` ≥ 600 if the drill is intended to validate `for: 5m` alerts)

### AC-2: Manifest format spec — drill scripts emit a JSON manifest at execution start

**Given** a drill script under `homelab-infra/scripts/drills/` (or `_bmad-output/drill-runners/`, depending on operator preference — confirmed in Task 0)
**When** the drill script begins execution
**Then** the script emits a manifest at:
```
_bmad-output/drill-evidence/<drill-name>/manifest.json
```
where `<drill-name>` is the operator-passed name (e.g. `6-7-pull-plug-pve3-2026-04-25`).
**And** the manifest contains the following fields:
```json
{
  "schema_version": "1",
  "drill_name": "6-7-pull-plug-pve3-2026-04-25",
  "drill_script_path": "/home/developer/workspace/homelab/homelab-infra/scripts/drills/pull-plug-pve3.sh",
  "script_sha256": "a1b2c3...",
  "start_epoch": 1745492062,
  "start_iso8601": "2026-04-25T03:14:22Z",
  "operator": "tom",
  "operator_workbench_hostname": "ct-dev-homelab",
  "loop_duration_s": 600,
  "loop_duration_source": "literal",
  "gate_versions": {
    "preflight_script_sha256": "<sha of drill-safety-preflight.sh>",
    "manifest_schema_version": "1"
  },
  "drill_intent": {
    "watches_for_5m_alerts": true,
    "watches_for_1m_alerts": true,
    "expected_firing_alerts": ["PVEReplicationStale", "PVEHAStarted", "..."]
  },
  "end_epoch": null,
  "end_iso8601": null,
  "elapsed_wall_clock_s": null,
  "exit_code": null,
  "verdict": "in_progress"
}
```
**And** at drill exit (success or failure), the script appends `end_epoch`, `end_iso8601`, `elapsed_wall_clock_s`, `exit_code`, and `verdict` (one of `success` / `failure` / `aborted`) — the file is rewritten with the completed manifest
**And** the `script_sha256` is `sha256sum "$0" | awk '{print $1}'` computed at script-start time — captures the script-as-executed (post-edit drift won't re-rewrite the manifest's recorded SHA)
**And** the `loop_duration_source` field is one of `literal` (`LOOP_DURATION_S=600` was the only assignment), `env` (`LOOP_DURATION_S` came from environment), `runtime_reassigned` (the variable was reassigned after first reference; this is the case Gate 8's static grep cannot catch — the drill reports it honestly)
**And** the manifest write is **atomic**: write to `manifest.json.tmp`, `mv` to `manifest.json` — never a half-written file
**And** the manifest emission is implemented via a small bash helper `homelab-infra/scripts/drills/lib/emit-manifest.sh` that drill scripts source: `source "$(dirname "$0")/lib/emit-manifest.sh"`; `manifest_init "<drill-name>"`; `manifest_finalise <exit-code>` — keeps the per-drill code minimal

### AC-3: Existing Gate 8 demoted to soft warning; real enforcement via Gate 9

**Given** the static-grep Gate 8 from Story 6.9.1 (AC-11) is in place
**When** I run `drill-safety-preflight.sh --drill-script <path>` on a drill script
**Then** the existing Gate 8 static-grep check still runs but is **demoted to a soft warning**:
- If the script lacks `LOOP_DURATION_S=600` (or higher) literal AND the script lacks a `tail-phase` marker → emit a yellow warning on stderr, do NOT exit non-zero
- The warning text references this story (6.9.3) and explains that real enforcement now happens via `--post-drill-check` after the drill completes
- The script's exit code is NOT affected by the soft warning (preserves behaviour for any drill that intentionally bypasses, e.g. `--force --reason`)
**And** a NEW Gate 9 (AC-5) is the load-bearing enforcement — its non-zero exit IS the refusal
**And** the existing 6.9.1 self-test (which deliberately tests Gate 8's hard-refusal exit 17) is updated: the new exit semantics are "warn at preflight, refuse at post-drill"
**And** the runbook clarifies: a drill that runs without invoking `--post-drill-check` is **structurally untrusted** — its claim of having validated `for: 5m` alerts cannot be substantiated. Recommended: every drill ends with `drill-safety-preflight.sh --post-drill-check --drill-name <name>` as its final task.

### AC-4: Existing drill scripts (V3/V4/V5/V6) retroactively emit the manifest

**Given** the drill scripts for Stories 6.5 / 6.6 / 6.7 / 6.8 already exist (and have already been executed in the V3/V4/V5/V6 drill-rehearsal series)
**When** I update each drill script to source `lib/emit-manifest.sh` and call `manifest_init` + `manifest_finalise`
**Then** the script lifecycle becomes:
```bash
#!/usr/bin/env bash
set -euo pipefail
# ... existing setup ...
source "$(dirname "$0")/lib/emit-manifest.sh"
manifest_init "6-7-pull-plug-pve3-$(date +%F)"
trap 'manifest_finalise "$?"' EXIT
# ... drill body ...
```
**And** the retroactive update applies to:
- `homelab-infra/scripts/drills/replication-rpo-ct162.sh` (Story 6.5 V3)
- `homelab-infra/scripts/drills/simulated-failover-migrate.sh` (Story 6.6 V4)
- `homelab-infra/scripts/drills/pull-plug-pve3.sh` (Story 6.7 V5; if the script's canonical path differs, confirm during Task 0)
- `homelab-infra/scripts/drills/pve3-recovery.sh` (Story 6.8 V6)
- Any future drill script in the same directory follows the same pattern
**And** if a drill script does NOT exist as a committed file (operator ran it ad-hoc with shell snippets), this AC notes the gap and Task 4 captures a NEEDS-OPERATOR-CONFIRMATION on the script's canonical location
**And** the retroactive update is non-functional (does not change drill behaviour) — only adds manifest emission
**And** each updated script is exercised against `--post-drill-check` in a dry-run (manifest produced, post-check validates) before being committed

> **NEEDS OPERATOR CONFIRMATION**: the canonical filesystem path of each existing drill script (V3/V4/V5/V6) — the AC names paths under `homelab-infra/scripts/drills/`, but the V5 evidence in Story 6.9.1's Dev Agent Record references the operator workbench rather than a committed script. Confirm whether each drill is a committed script, an Ansible playbook, or operator shell history before Task 4 begins.

### AC-5: NEW Gate 9 — `--post-drill-check` validates manifest claims against wall-clock reality

**Given** a drill has completed and emitted a manifest at `_bmad-output/drill-evidence/<drill-name>/manifest.json`
**When** I invoke `drill-safety-preflight.sh --post-drill-check --drill-name <drill-name>`
**Then** the script runs Gate 9 with the following sub-checks:
1. **Manifest exists** at the expected path. If missing → exit 18, message names the expected path and asks "did the drill emit a manifest?"
2. **Manifest is parseable JSON** with all required fields populated. If parse fails → exit 18 with the jq parse error.
3. **`loop_duration_s >= 600`** (the same threshold the existing Gate 8 enforces). If the manifest claims a value below threshold AND the drill's `drill_intent.watches_for_5m_alerts` is `true` → exit 19 with a clear "drill claimed N seconds, threshold 600s for `for: 5m` alert validation" message.
4. **Wall-clock match within 10% tolerance**: compute `actual = end_epoch - start_epoch`; verify `abs(actual - loop_duration_s) / loop_duration_s <= 0.10`. If outside tolerance → exit 20 with the deception-detection message:
   ```
   Drill INVALID: manifest claims loop_duration_s=600 but wall-clock elapsed=63s.
   Tolerance band: 540s-660s. Observed: 63s.
   Possible causes:
     - Drill script reassigned LOOP_DURATION_S after the manifest was written
     - Drill script exited early (errored mid-loop)
     - Manifest was forged (script_sha256 mismatch — see next check)
   This drill cannot be trusted to have validated `for: 5m` alerts. Re-run.
   ```
5. **Script SHA tamper-detect**: recompute `sha256sum "$drill_script_path"`; compare to manifest's `script_sha256`. If different → exit 21 with "drill script was modified post-execution; manifest cannot be trusted." This is a known false-positive path (operator legitimately edits the script after the drill) — emit as a yellow warning, not exit non-zero, when `--post-drill-check --tolerate-script-edit` is passed.
6. **`drill_intent` sanity**: if the manifest claims `watches_for_5m_alerts: true` but `expected_firing_alerts` is an empty list → emit yellow warning ("drill claims to watch for 5m alerts but lists no expected alerts; consider whether the drill is actually validating anything").
**And** Gate 9 exits 0 only if all checks pass; otherwise the most-significant non-zero exit code (priority: 20 > 21 > 19 > 18) becomes the final exit
**And** the post-drill check writes a verdict to `_bmad-output/drill-evidence/<drill-name>/post-drill-verdict.txt`:
```
VERDICT: VALID | INVALID
Manifest: _bmad-output/drill-evidence/<drill-name>/manifest.json
Claimed loop: 600s
Observed loop: 612s (within 10% tolerance: PASS)
Script SHA at run: a1b2c3...  (current SHA: a1b2c3...  match: PASS)
Alerts watched: PVEReplicationStale, PVEHAStarted (firing during drill: 2/2)
Verdict generated: 2026-04-25T03:24:22Z
Generated by: drill-safety-preflight.sh v6.9.3
```
**And** the verdict file is **the canonical artefact** that an operator attaches to the drill story's Dev Agent Record (closes the drill's evidence loop)

### AC-6: Synthetic deception test — drill that lies about its loop duration

**Given** the manifest spec (AC-2), the demoted Gate 8 (AC-3), and the new Gate 9 (AC-5) are in place
**When** I author a synthetic test drill at `homelab-infra/scripts/drills/synthetic-lying-drill.sh` that:
```bash
#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/lib/emit-manifest.sh"
LOOP_DURATION_S=600
manifest_init "synthetic-lying-2026-04-25"
trap 'manifest_finalise "$?"' EXIT

# The lie: silently shorten the loop after manifest was written
LOOP_DURATION_S=60

T_INJECT=$(date +%s)
while [[ $(($(date +%s) - T_INJECT)) -lt $LOOP_DURATION_S ]]; do
    sleep 5
done
```
**And** I run the drill, then run `drill-safety-preflight.sh --post-drill-check --drill-name synthetic-lying-2026-04-25`
**Then** Gate 9 detects the deception:
- Manifest claim: `loop_duration_s=600`
- Wall-clock observed: ~60s
- Verdict: **INVALID** (exit 20, AC-5 sub-check 4)
- The post-drill-verdict.txt explicitly names "wall-clock mismatch — drill ran for 60s but claimed 600s"
**And** the synthetic test transcript is captured at `_bmad-output/drill-evidence/6-9-3-synthetic-lying-test-<date>.txt`
**And** an **honest** synthetic drill (loop actually runs 600s) is also tested → Gate 9 exits 0, verdict VALID — proves the gate doesn't false-positive on legitimate drills

### AC-7: Runbook + drill-author guide

**Given** AC-2 through AC-6 are in place
**When** I update `homelab-infra/docs/ha-replication-runbook.md` (or a new drill-author guide file under the same directory)
**Then** the runbook gains a "Drill author guide" section that documents:
- The 5-line boilerplate every new drill script must include (source the lib, `manifest_init`, `trap manifest_finalise`)
- The required manifest fields and what each is used for in Gate 9
- The `--post-drill-check --drill-name <name>` invocation as a drill's final canonical task
- How to interpret the post-drill verdict (VALID vs INVALID, the script SHA tamper case, the operator-edit-after-drill case)
- The `--tolerate-script-edit` escape hatch and when to use it
- Examples: clean drill (verdict VALID), lying drill (verdict INVALID), aborted drill (manifest has `verdict: aborted`, post-check still meaningful)
**And** the existing 6.9.1 §"Drill safety preconditions" section is amended to reference 6.9.3 and the manifest mechanism — Gate 8's static grep is documented as soft-warning-only
**And** the drill-author guide is cross-linked from each existing drill story (Stories 6.5 / 6.6 / 6.7 / 6.8 References sections gain a pointer to it on next review pass)

## Tasks

- [ ] **Task 0: Pre-flight + dependency verification + drill-script audit**
  - Cluster quorate; Story 6.9.1 in `done`; canonical preflight script + Ansible role both present.
  - **Audit**: confirm the filesystem path of every existing drill script (V3/V4/V5/V6). Capture in Dev Notes; flag NEEDS-OPERATOR-CONFIRMATION items if any drill is non-committed (operator shell history vs committed script).
  - Confirm `_bmad-output/drill-evidence/` exists; if not, create.

- [ ] **Task 1: Manifest emission library** (AC-2)
  - Author `homelab-infra/scripts/drills/lib/emit-manifest.sh`:
    - `manifest_init(drill_name)` — writes initial manifest with start_epoch, script_sha256, gate_versions, drill_intent (sourced from drill-script env vars `DRILL_WATCHES_5M_ALERTS`, `DRILL_EXPECTED_ALERTS`, etc.)
    - `manifest_finalise(exit_code)` — appends end_epoch, elapsed_wall_clock_s, exit_code, verdict; atomic-write via `mktemp` + `mv`
    - `manifest_path(drill_name)` — pure-string helper for path resolution (used by --post-drill-check too)
  - JSON construction via `jq -n --argjson ... '{...}'` (avoids hand-stringification of JSON, no escape-hell)
  - Helper script `bash -n` + `shellcheck` clean.
  - Self-test: source the lib in a one-liner, call `manifest_init`/`finalise`, verify the manifest is valid JSON via `jq .`.

- [ ] **Task 2: Demote existing Gate 8 to soft warning** (AC-3)
  - In `drill-safety-preflight.sh`, refactor `gate_8_loop_window()`:
    - Existing static-grep code path retained
    - On grep miss: emit warning to stderr, **return 0** (was: exit 17)
    - Update inline comments to reference 6.9.3 and the new Gate 9
  - Add `--strict-gate-8` flag for callers who want the old hard-refusal behaviour (CI guardrail use case)
  - Update the existing 6.9.1 self-test transcript reference: Gate 8 is now soft-warn at preflight; hard-refuse moved to post-drill.

- [ ] **Task 3: Implement `--post-drill-check` Gate 9** (AC-5)
  - Add `--post-drill-check` flag with required `--drill-name <name>` arg
  - Implement `gate_9_post_drill()`:
    1. Resolve manifest path; verify exists
    2. Parse via jq; emit clear error on parse failure
    3. Validate `loop_duration_s >= 600` (when `drill_intent.watches_for_5m_alerts == true`)
    4. Validate wall-clock match: `abs(actual - claim) / claim <= 0.10`
    5. Validate `script_sha256` (with `--tolerate-script-edit` escape hatch)
    6. Sanity-check `drill_intent` (warning-only)
  - Write verdict to `_bmad-output/drill-evidence/<drill-name>/post-drill-verdict.txt`
  - Exit-code priority: 20 > 21 > 19 > 18 (most-egregious deception first)
  - `bash -n` + `shellcheck` clean.

- [ ] **Task 4: Retroactively update existing drill scripts** (AC-4)
  - For each existing committed drill script: add `source` + `manifest_init` + `trap manifest_finalise`.
  - Set `DRILL_WATCHES_5M_ALERTS`, `DRILL_EXPECTED_ALERTS` env-vars at script top per drill's actual intent.
  - For non-committed drills (NEEDS-OPERATOR-CONFIRMATION items from Task 0): document the gap; a future story (or operator-side script-formalisation pass) commits these as proper scripts.
  - Verify each updated script still passes `bash -n` + `shellcheck`.

- [ ] **Task 5: Synthetic deception test** (AC-6)
  - Author `homelab-infra/scripts/drills/synthetic-lying-drill.sh` per AC-6.
  - Author `homelab-infra/scripts/drills/synthetic-honest-drill.sh` (mirror, but with no reassignment).
  - Run both; capture transcripts at `_bmad-output/drill-evidence/6-9-3-synthetic-lying-test-<date>.txt`.
  - Verify the lying drill produces verdict INVALID (exit 20); the honest drill produces verdict VALID (exit 0).
  - Verify the manifest's `loop_duration_source` is `runtime_reassigned` for the lying drill (the manifest IS honest about the lie, by design).

- [ ] **Task 6: Runbook + drill-author guide** (AC-7)
  - Add "Drill author guide" section to `homelab-infra/docs/ha-replication-runbook.md` (or new file, depending on size).
  - Update existing 6.9.1 §"Drill safety preconditions" to reference 6.9.3 and the manifest mechanism.
  - Cross-reference Stories 6.5/6.6/6.7/6.8 (References-section pointer added on next review pass — out of scope for 6.9.3 itself).

- [ ] **Task 7: Final-state evidence + status flip**
  - All synthetic tests + retroactive script updates verified.
  - Append Dev Agent Record per 6.9.1 pattern.
  - Frontmatter `backlog → review`.

## Dev Notes

### Manifest schema versioning

The `schema_version: "1"` field is intentional — future evolutions (adding alert-trace data, GPU/temperature snapshots, multi-drill correlation) will bump to `"2"` and the post-drill check will branch on the version. Forward-compatible: a v2-aware post-drill-check can read v1 manifests as a strict subset; a v1-aware post-drill-check refuses on a v2 manifest with "schema version mismatch — upgrade your preflight script".

### `script_sha256` semantics

`script_sha256` is the hash of the drill script **as executed**. Computed at `manifest_init` time via `sha256sum "$0"`. If the operator edits the script after the drill (e.g. fixes a typo, commits the changes), the on-disk SHA changes but the manifest's recorded SHA does not — the post-drill check detects the mismatch.

Why this matters: post-hoc script edits could otherwise rewrite history. An operator who runs a drill that fails, then edits the script to "fix" the failure, then claims the original drill validated the fixed version — the manifest's recorded SHA forensically pins the drill to the script-as-executed.

The `--tolerate-script-edit` escape hatch exists for the legitimate case (operator edits comments, formatting, non-functional whitespace). The post-drill check still emits a yellow warning even with the tolerance flag, so the edit is logged.

### Atomic manifest writes

Every manifest update (init + finalise) writes to `manifest.json.tmp` and `mv`s into place. Two reasons:
1. A `--post-drill-check` racing against an in-progress drill (operator running both in parallel by accident) sees either the pre-init absence, the in-progress manifest, or the finalised manifest — never a half-written file.
2. Filesystem crash during write leaves the previous manifest intact; only the `.tmp` file is corrupted, and `manifest_init` removes any leftover `.tmp` on next run.

### Wall-clock tolerance: 10%

Why 10%? The 600s target absorbs:
- Cron scheduling jitter (~30s — Gate 7 evidence-stack tolerance)
- Bash `sleep 30` granularity in the loop (1-2s drift per iteration over 20 iterations = ~30s)
- Operator-initiated abort right at the threshold (drill ends at T+595s — within tolerance)

10% of 600s = 60s — comfortably wider than expected drift, narrower than the deception case (60s vs 600s = 90% mismatch — far outside any tolerance).

For non-600s drills (e.g. a drill that intentionally claims `loop_duration_s=900`), 10% of 900 = 90s — still narrow enough to catch deception. The percentage stays constant, the absolute tolerance scales.

### `drill_intent.watches_for_5m_alerts`

A drill that doesn't watch for `for: 5m` alerts (e.g. a 1-minute migration drill, a snapshot-only drill) doesn't need a 600s loop. The `watches_for_5m_alerts: false` path in the manifest tells Gate 9 to skip the AC-5 sub-check 3 (the 600s threshold). Gate 9 still validates wall-clock match against whatever the drill claimed — it just doesn't impose the 600s floor.

This is the `--force --reason` escape hatch from 6.9.1 AC-11 expressed in manifest form: instead of the operator overriding at preflight, the drill self-reports its intent at execution. The operator-trust model is unchanged (the operator authors the drill); the audit trail is improved.

### File layout

**homelab-infra/** (create):
- `scripts/drills/lib/emit-manifest.sh` (~80 lines, sourced by drill scripts)
- `scripts/drills/synthetic-lying-drill.sh` (~30 lines, AC-6 test)
- `scripts/drills/synthetic-honest-drill.sh` (~25 lines, AC-6 control)

**homelab-infra/** (modify):
- `scripts/drill-safety-preflight.sh` — demote Gate 8 to soft warning; add Gate 9 (`--post-drill-check`); add `--strict-gate-8` flag; add `--tolerate-script-edit` flag
- `ansible/roles/drill-safety/files/drill-safety-preflight.sh` — mirror update
- `scripts/drills/replication-rpo-ct162.sh` (V3) — retroactive manifest emission
- `scripts/drills/simulated-failover-migrate.sh` (V4) — retroactive manifest emission
- `scripts/drills/pull-plug-pve3.sh` (V5) — retroactive manifest emission (subject to Task 0 path confirmation)
- `scripts/drills/pve3-recovery.sh` (V6) — retroactive manifest emission
- `docs/ha-replication-runbook.md` — drill-author guide section + 6.9.1 cross-reference

> **NEEDS OPERATOR CONFIRMATION**: the canonical filesystem location of the V5 pull-plug-pve2 / pve3 drill scripts. Story 6.9.1's evidence references operator workbench shell snippets, not committed files — confirm whether each V-N drill is a committed script (in which case Task 4 updates it) or an Ansible playbook (in which case the manifest-emission pattern applies in YAML form, slightly different from the bash boilerplate).

### Prior art references

- **Story 6.9.1** — the parent. Gate 8 (AC-11) is the gate this story refactors; Gate 9 is the new addition.
- **Story 6.10** — exporter SHA-tamper-detect pattern; same `sha256sum` mechanic.
- **Story 6.2** — exporter atomic-write pattern; same `mktemp` + `mv` for manifest writes.
- **JSON-LD / schema versioning best practice**: <https://json-schema.org/understanding-json-schema/structuring.html>
- **Bash `trap ... EXIT` for finalise pattern**: <https://www.gnu.org/software/bash/manual/bash.html#Bourne-Shell-Builtins>

## Test strategy

**Phase 1 (Task 0):** observation + drill-script audit. Capture NEEDS-OPERATOR-CONFIRMATION items.

**Phase 2 (Tasks 1-3):** library + script changes; `bash -n` and `shellcheck` clean. No live cluster state changes.

**Phase 3 (Task 4):** retroactive script updates. Each updated script exercised in a `--post-drill-check` dry-run (synthetic short-loop to verify manifest+verdict produce correctly) before commit.

**Phase 4 (Task 5):** **load-bearing AC**. Synthetic lying drill + synthetic honest drill. Both exercised end-to-end. Lying drill MUST produce verdict INVALID; honest drill MUST produce verdict VALID. Either failure invalidates this story.

**Phase 5 (Tasks 6-7):** documentation + status flip. No production state change.

**Test acceptance**: `_bmad-output/drill-evidence/6-9-3-synthetic-lying-test-<date>.txt` shows the lying-drill verdict INVALID with the wall-clock-mismatch reason; the same file (or a sibling) shows the honest-drill verdict VALID. Each retroactive drill-script update verified by a dry-run `--post-drill-check` against a synthetic short-loop run.

## Security considerations

- **Manifest tamper-resistance**: `script_sha256` is the only meaningful tamper-detect. An operator (root) who can edit the drill script can also edit the manifest; the SHA mismatch in the manifest's recorded value vs the on-disk script catches the case where the script changed AFTER manifest emission. It does NOT catch the case where the manifest itself is rewritten by an attacker post-hoc — same trust model as the audit log (operator-trust).
- **Drill manifest as forensic artefact**: post-drill the manifest + verdict are the canonical evidence the operator attaches to the drill story's Dev Agent Record. If the story's verdict claims VALID but the manifest verdict says INVALID, the manifest wins (objective wall-clock data over subjective claim).
- **No new credentials, no new network surface**. Manifest is local-filesystem only; `--post-drill-check` reads from local files only.
- **`jq` injection**: drill names and operator names go into the manifest as JSON-string-escaped values via `jq --arg`; no risk of breaking out of the JSON context.
- **Symlink attack on `_bmad-output/drill-evidence/`**: an attacker who can create symlinks in that directory could redirect manifest writes elsewhere. Mitigation: the manifest-init helper checks `realpath` resolution and refuses if the resolved path is outside `_bmad-output/drill-evidence/`. Additive defense; out of scope for first delivery if the trust model is "operator-only writes to this dir".

## Rollback procedure

The library + script changes are additive (new files, new flags, new gate). If unexpected behaviour:
1. **Revert all script + library files**: `git checkout` each modified file from this story.
2. **Re-run Ansible role** to push reverted preflight script to PVE nodes + workbench.
3. **Manifest files in `_bmad-output/drill-evidence/`**: leave intact (forensic record); future `--post-drill-check` invocations against pre-rollback manifests still work because the manifest schema is independent of the script version.
4. **`drill-safety-preflight.sh` reverts to 6.9.1 state**: Gate 8 returns to hard-refusal mode (exit 17 on grep miss); Gate 9 disappears.
5. **No cluster state change** — manifests live in the workbench/repo, not on PVE hosts.

Rollback restores the pre-6.9.3 state where Gate 8 is hard-refuse and there is no manifest mechanism. The deception failure mode (R4) re-opens, but the rest of 6.9.1 is unaffected.

## References

- **Adversarial finding source**: Story 6.9.1 review, R4 (Gate 8 evidence-manifest enforcement)
- **Parent story**: `homelab-playbook/_bmad-output/implementation-artifacts/6-9-1-drill-safety-preconditions.md`
- **Drill stories the manifest applies to**:
  - `6-5-validation-drill-v3-replication-rpo-for-ct162.md`
  - `6-6-validation-drill-v4-simulated-failover-via-migrate.md`
  - `6-7-validation-drill-v5-pull-plug-pve3.md`
  - `6-8-validation-drill-v6-pve3-recovery.md`
- **Structural template**: `6-2-verify-replication-state-and-deltas.md`
- **Canonical preflight script (post-6.9.1)**: `homelab-infra/scripts/drill-safety-preflight.sh`
- **Ansible role**: `homelab-infra/ansible/roles/drill-safety/`
- **`jq` JSON construction**: <https://stedolan.github.io/jq/manual/#Invokingjq>
- **`sha256sum` man page**: <https://man7.org/linux/man-pages/man1/sha256sum.1.html>
- **Bash `trap ... EXIT` finalise pattern**: <https://www.gnu.org/software/bash/manual/bash.html#Bourne-Shell-Builtins>

## Change Log

- **2026-04-25**: Story created by BMad SM as Story 6.9.1's adversarial-review follow-up (absorbs R4 — Gate 8 evidence-manifest enforcement).
