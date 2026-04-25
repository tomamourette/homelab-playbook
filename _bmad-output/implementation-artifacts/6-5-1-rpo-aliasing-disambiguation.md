---
status: backlog
epic: 6
story: 6.5.1
title: RPO aliasing disambiguation — 1s-cadence sampler verification for ct:162
created: 2026-04-25
author: BMad SM
depends-on: 6-5
---

# Story 6.5.1: RPO aliasing disambiguation — 1s-cadence sampler verification

Status: backlog

## Story

As an operator,
I want a 1-second-cadence sampler run against ct:162 replication that empirically falsifies (or confirms) the sampler-vs-cycle aliasing claim from Story 6.5,
so that the next time a future operator sees a `max > 60s` outlier on ct:162 they know whether the aliasing precedent applies (and the cluster is healthy) or whether the cycle Duration itself is drifting (and something must be investigated).

## Business value

Story 6.5's drill recorded `max=63s` on leg `162-0` against a 60-second budget. The Dev Agent Record attributes this to **sampler-vs-cycle aliasing**: with a 10 s sampler against a 60 s cycle, the strict-max RPO will always read `cycle_period + (0..10s) + cycle_duration`, so a 63 s reading is consistent with a healthy 60 s cycle plus measurement quantization. That explanation is plausible and arithmetically sound — but it was **not falsified** during 6.5 because no 1 s-cadence verification run was performed.

Without disambiguation, the aliasing argument becomes a self-serving precedent: any future drift in actual cycle Duration will be dismissed as "more aliasing" and the empirical proof of `≤60s RPO` quietly erodes. A 10-minute 1-second-cadence run resolves this:

- If `max ≤ 61s` (i.e. true cycle never exceeds the 60s budget by more than 1s of measurement quantization), the aliasing claim is **falsified-into-confirmation**: the 6.5 drill's `max=63s` was measurement noise, the cycle itself is healthy, and the runbook can stamp "aliasing confirmed real artifact" against the observed numbers.
- If `max > 61s`, the aliasing claim is **falsified-into-rejection**: the cycle Duration itself is exceeding 60s under some condition the 6.5 drill did not stress, and a sub-investigation is required (out of scope for this story; opened as a follow-up issue per AC-5).

Either way, the runbook gets a defensible answer and the falsification step itself becomes a permanent fixture of the V3-class drill template.

## Absorbed finding

This story **absorbs** Story 6.5 adversarial review finding **R2** (HIGH severity per the review's classification, but procedurally a process gap rather than a code/config defect):

> "Aliasing claim is unfalsified. The sampler-period-vs-cycle-period (10s vs 60s) collision argument explains the 63s outlier on 162-0, but a 1s-cadence verification run wasn't done. Without disambiguation, future operators may dismiss real cycle-duration drift as 'more aliasing'."

The R2 finding is referenced in Story 6.5 Dev Agent Record §"Gotchas surfaced during this run" (sampler-vs-cycle aliasing bullet) and `_bmad-output/drill-evidence/v3-ct162-rpo-2026-04-25-summary.txt` line `cadence_decision=KEEP at */1`.

R2-adjacent context **not** absorbed here:

- **Continuous monitoring of cycle Duration** at the recording-rule level. Out of scope for this story; that long-tail telemetry is the job of Story 6.5.2 (7-day soak telemetry).
- **Re-running the full V3 drill at 1s cadence**. Out of scope — this story runs only the AC-2 sampling loop equivalent, not Tasks 1/3/5 from 6.5.
- **`pvesr` cycle Duration histogram metric**. If the falsification fails (max > 61s), the follow-up investigation may require this; out of scope for the current story to avoid scope creep into instrumentation.

## Acceptance Criteria

### AC-1: Pre-flight — cluster healthy, ct:162 still at `*/1` cadence

**Given** Story 6.5 is `done` (or `review` with the KEEP-at-`*/1` decision committed to `/etc/pve/replication.cfg`)
**When** I run pre-flight checks:
- `ssh pve1 "pvecm status"` → `Quorate: Yes`, `Total votes: 3`
- `ssh pve3 "pvesr status"` → `162-0` and `162-1` both show `Schedule=*/1`, `State=OK`, `FailCount=0`, `LastSync` within 2 minutes of wall-clock
- Grafana HA Replication dashboard shows all 8 stat panels green
- No `PVEReplication*` alert firing in Alertmanager (`https://alertmanager.bi-services.be`)

**Then** all four checks pass before the sampler is launched
**And** the pre-flight output is captured to `_bmad-output/drill-evidence/v3-1s-aliasing-<YYYY-MM-DD>-pre.txt`
**And** if any check fails the drill aborts (do not run the sampler against an unhealthy cluster — the result would be unattributable)

### AC-2: 1-second-cadence sampler runs for 10 minutes

**Given** AC-1 holds
**When** I launch the 1s-cadence sampler script (Dev Notes §"Sampler script") that records `(now - last_sync)` for `162-0` and `162-1` every 1 second for 600 iterations (10 minutes)
**Then** the run produces a CSV at `_bmad-output/drill-evidence/v3-1s-aliasing-<YYYY-MM-DD>.csv` with **600 rows per leg = 1200 total rows**
**And** the CSV has the same column schema as `v3-ct162-rpo-2026-04-25.csv` from Story 6.5 (`timestamp_iso, jobid, last_sync_epoch, now_epoch, age_seconds, state, fail_count`)
**And** no row has `state="error"` or `fail_count>0` (i.e. the sampler did not coincide with a real replication failure that would confound the result)
**And** the sampler is **bounded**: a `for $(seq 1 600); do ... sleep 1; done` loop with `timeout 5` on the inner `pvesh` call — no `while true`, no unbounded retry

### AC-3: Verdict — `max ≤ 61s` confirms aliasing, `max > 61s` reveals real variance

**Given** AC-2 holds and the 1200 CSV rows are present
**When** I post-process the CSV with `awk` (or equivalent) to compute per-leg min / median / p95 / p99 / **max** of `age_seconds`
**Then** one of exactly two verdicts is recorded in `v3-1s-aliasing-<YYYY-MM-DD>-summary.txt`:

- **Verdict ALIASING-CONFIRMED**: `max ≤ 61s` on **both** legs. The 1s sampler resolves the cycle period to within 1s of measurement quantization; the 6.5 drill's `max=63s` is therefore explained by 10s-sampler aliasing, the aliasing claim is empirically defensible, and the RPO budget of `≤60s` is upheld.
- **Verdict CYCLE-DURATION-VARIANCE**: `max > 61s` on **either** leg. The aliasing claim is rejected — the cycle itself drifted past 60s during the sampling window. The exact `max`, the timestamp it occurred at, and the surrounding 10 samples are recorded for the follow-up investigation.

**And** the verdict line, the per-leg stats, and the raw CSV path are appended to `homelab-infra/docs/ha-replication-runbook.md §"V3 Drill Results (2026-04-25)"` as a new sub-section `#### Aliasing disambiguation (1s sampler — <date>)`.

### AC-4: Falsification step codified into drill runbook + sampler.sh

**Given** AC-3 records a verdict (either outcome)
**When** I update `homelab-playbook/_bmad-output/drill-evidence/v3-rpo-sampler.sh` with a new `--cadence 1` flag (or equivalent inline branch) **and** append a "Falsification step" sub-section to `homelab-infra/docs/ha-replication-runbook.md §"V3 Drill Results"` (or to a new "RPO drill template" section if the runbook structure makes that cleaner)
**Then** the sampler script supports `bash v3-rpo-sampler.sh --cadence 1 --duration 600` as a documented mode that writes to a `*-1s-aliasing-*.csv` file — same schema, same output dir, same bounded-loop guarantees
**And** the runbook section explicitly states: "Every future cadence-tightening drill (V3-class: tightening any replication job below `*/15`) MUST include a 1s-cadence aliasing-disambiguation run alongside the standard 10s sampler. The 10s sampler measures distribution; the 1s sampler falsifies aliasing claims about the max."
**And** the runbook section names the verdict thresholds explicitly (`≤61s` confirms / `>61s` rejects) so a future operator does not have to re-derive them

### AC-5: If `max > 61s`, open a sub-investigation issue (not in scope here)

**Given** AC-3 returned **Verdict CYCLE-DURATION-VARIANCE**
**When** I file a follow-up note in `homelab-infra/docs/ha-replication-runbook.md §"Known gaps deferred to <future stories>"` with:
- The observed `max`, the timestamp, the 10 surrounding samples
- A suggested next step (e.g., "instrument `pve_replication_last_duration_seconds` recording rule + 30-min p99 alert" — see Story 6.5.2 for the recording-rule infrastructure)
- A pointer to either: (a) cadence rollback to `*/5` if variance is sustained, or (b) wait for 6.5.2 soak telemetry to characterize the long-tail before deciding

**Then** the follow-up is captured but **not executed in this story** — Story 6.5.1 ends at the disambiguation verdict and the runbook update
**And** if AC-3 returned **Verdict ALIASING-CONFIRMED**, AC-5 is a no-op and is marked `N/A — aliasing confirmed`.

## Tasks / Subtasks

- [ ] **Task 1: Pre-flight sanity** (AC-1)
  - [ ] Run the four pre-flight checks; capture combined output to `_bmad-output/drill-evidence/v3-1s-aliasing-<date>-pre.txt`
  - [ ] Abort if any check fails — do not proceed to Task 2

- [ ] **Task 2: Implement 1s-cadence mode in `v3-rpo-sampler.sh`** (AC-2 prep, AC-4 partial)
  - [ ] Add `--cadence <N>` and `--duration <seconds>` flags (default `--cadence 10 --duration 900` for 6.5 backwards-compat); 1s mode is `--cadence 1 --duration 600`
  - [ ] Output filename derives from the cadence (`v3-ct162-rpo-<date>-<cadence>s.csv`) so the 6.5 baseline file is not overwritten
  - [ ] Keep all existing 6.5 invariants: `timeout 5` on inner SSH, atomic CSV write, bounded loop with explicit iteration count, error trap

- [ ] **Task 3: Run the 1s sampler for 10 minutes** (AC-2)
  - [ ] `nohup bash v3-rpo-sampler.sh --cadence 1 --duration 600 > v3-1s-aliasing-<date>-sampler.out &` — record PID
  - [ ] Foreground-poll `kill -0 $PID` on bounded retries (~620 iterations of 1s sleep cap) — do NOT use `while true` to wait
  - [ ] On completion: confirm CSV has 1200 rows, no `error` rows, no malformed rows

- [ ] **Task 4: Post-process and write verdict** (AC-3)
  - [ ] `awk`-compute per-leg min / median / p95 / p99 / max of `age_seconds`
  - [ ] Emit verdict ALIASING-CONFIRMED if both legs `max ≤ 61`, else CYCLE-DURATION-VARIANCE
  - [ ] Write `v3-1s-aliasing-<date>-summary.txt` with the verdict, the per-leg stats, and the raw CSV path

- [ ] **Task 5: Update runbook** (AC-3, AC-4)
  - [ ] Append `#### Aliasing disambiguation (1s sampler — <date>)` sub-section under §"V3 Drill Results (2026-04-25)" with the verdict + stats
  - [ ] Append "Falsification step" sub-section to the runbook §"V3 Drill Results" (or new §"RPO drill template") describing the mandatory 1s-cadence run for any future V3-class drill
  - [ ] Cross-link to the updated sampler script and the verdict thresholds

- [ ] **Task 6: If CYCLE-DURATION-VARIANCE — file follow-up note** (AC-5)
  - [ ] Append entry to runbook §"Known gaps deferred to <future stories>" with observed `max`, timestamp, suggested next step
  - [ ] Cross-link Story 6.5.2 (soak telemetry) as the candidate consumer of this finding

- [ ] **Task 7: Commit + status flip**
  - [ ] Commit `_bmad-output/drill-evidence/v3-1s-aliasing-<date>.*` and the updated `v3-rpo-sampler.sh` as one logical unit (`feat(drill-tooling): add 1s aliasing-disambiguation sampler mode + V3.1 verdict`)
  - [ ] Commit the runbook update separately if it lives in `homelab-infra` (`docs(runbook): codify 1s falsification step for V3-class RPO drills + V3.1 verdict`)
  - [ ] Flip story frontmatter `backlog` → `review`
  - [ ] **NEEDS OPERATOR CONFIRMATION** — sprint-status YAML flip handled via the sprint-status skill (per project rule: SM/Dev does not hand-edit sprint-status YAML)

## Dev Notes

### Sampler script

`v3-rpo-sampler.sh` already exists at `_bmad-output/drill-evidence/v3-rpo-sampler.sh` with hard-coded 10s cadence and 90 iterations (Story 6.5). Extend with two flags:

```bash
CADENCE_S="${CADENCE_S:-10}"   # --cadence
DURATION_S="${DURATION_S:-900}"  # --duration
ITERATIONS=$(( DURATION_S / CADENCE_S ))
# usage: --cadence 1 --duration 600 → 600 iterations × 1s = 600s
```

Output filename:
```bash
CSV="$EVIDENCE_DIR/v3-ct162-rpo-${DATE}-${CADENCE_S}s.csv"
# Story 6.5 produced v3-ct162-rpo-2026-04-25.csv (no cadence suffix);
# new mode produces v3-1s-aliasing-<date>.csv (per AC-2 evidence path).
# Choose either convention; see AC-2 — "v3-1s-aliasing-*.csv" is what the AC names.
```

### Why 10 minutes (not 15 or 30)

A 10-minute window at 1s cadence captures **10 full cycle periods** at the `*/1` schedule (60s each). That is enough to observe the per-cycle wall-clock duration as the `age_seconds` metric crosses zero on each cycle boundary — i.e. the sampler will see the `last_sync_epoch` increment ~10 times. With 1s resolution, the `max age` measurement quantization is ±1s, so any reading > 61s strictly implies the cycle itself ran longer than 60s plus 1s of sampler skew.

15 or 30 minutes would give more confidence in the tail but at proportional cost to operator time. 10 minutes is the smallest window that gives ≥10 cycle observations per leg with a defensible p99.

### Why `≤61s` and not `≤60s`

Sampler quantization. The 1s sampler reads `now = $(date +%s)` and `last_sync` from `pvesh`; both are integer-second epochs. Even a perfectly punctual 60s cycle can read as `61s` if the sampler tick lands 1s after the cycle boundary. `≤61s` accepts that 1s of measurement noise; `>61s` is the strict signal of cycle Duration variance.

### Sampler load on pve3

Running `pvesh get /nodes/pve3/replication --output-format json` 600 times in 10 minutes is one call/sec to pveproxy on pve3. `pveproxy` handles this routinely — the existing 5-min cron-driven `pve-replication-exporter.sh` is already invoking equivalent calls and Story 6.2's R7 hardening wrapped it in `timeout 30`. No new load concerns.

### Exit conditions

- Normal exit: 600 iterations completed, CSV has 1200 rows, verdict written.
- Early exit (sampler aborted): partial CSV exists, summary records `INCOMPLETE` verdict, partial CSV is **not** committed (do not pollute the evidence directory with partial runs — see Story 6.5 Dev Agent Record cleanup of `partial-failed-run-2026-04-25/`).
- Cluster-failure exit (pre-flight passed but a real replication failure occurred mid-run): commit the partial CSV to a `partial-failed-run-<date>/` sub-directory for forensics; verdict is `ABORTED — cluster event during run, see <evidence path>`.

### File layout

Files to create:
- `_bmad-output/drill-evidence/v3-1s-aliasing-<date>-pre.txt`
- `_bmad-output/drill-evidence/v3-1s-aliasing-<date>.csv` (1200 rows)
- `_bmad-output/drill-evidence/v3-1s-aliasing-<date>-summary.txt`
- `_bmad-output/drill-evidence/v3-1s-aliasing-<date>-sampler.out`

Files to modify:
- `_bmad-output/drill-evidence/v3-rpo-sampler.sh` — add `--cadence` / `--duration` flags
- `homelab-infra/docs/ha-replication-runbook.md` — append aliasing-disambiguation sub-section + falsification-step template

### Prior art references

- **Story 6.5** (`6-5-validation-drill-v3-replication-rpo-for-ct162.md`) — the parent drill that surfaced R2; established the sampler-script + evidence-dir pattern
- **`v3-rpo-sampler.sh`** — existing bounded-loop sampler with `timeout 5` on inner SSH, error trap, atomic CSV append; baseline for the 1s-mode extension

## Test strategy

**Phase 1 (Task 1):** observation-only pre-flight. No cluster state changes. Outcome: green baseline OR documented abort.

**Phase 2 (Tasks 2-3):** add 1s mode to sampler script + run for 10 min. No cluster mutation; only adds a new evidence file. Sampler load on pve3 is 1 call/sec for 10 min — sustained-low-and-bounded.

**Phase 3 (Task 4-5):** post-process + runbook update. Documentation only.

**Phase 4 (Task 6):** conditional follow-up note (only if CYCLE-DURATION-VARIANCE).

**Evidence that the story passed:**

- `v3-1s-aliasing-<date>.csv` has exactly 1200 rows
- `v3-1s-aliasing-<date>-summary.txt` has a clear verdict line
- Runbook has the new `#### Aliasing disambiguation` sub-section with stats
- Runbook has the new "Falsification step" template language
- `v3-rpo-sampler.sh` accepts `--cadence 1 --duration 600` and produces the expected output

## Security considerations

- Sampler runs as the developer's user via existing SSH trust (homelab_ed25519); no new credentials.
- 600 SSH calls in 10 minutes against pveproxy on pve3 — within normal operational load. No firewall changes, no new network exposure.
- CSV records internal IPs, job IDs, and replication timestamps — operational metadata, not credential material. Safe to commit.
- No workload mutation, no cluster state change, no `pvesr` or `qm` write commands. Read-only drill end-to-end.

## Rollback procedure

**No rollback required** — this story is read-only. The only artifacts are evidence files (committed) and a script extension (additive flags with backwards-compatible defaults). If the sampler errors mid-run:

```bash
# Kill the sampler if it was launched via nohup
kill $(cat _bmad-output/drill-evidence/v3-1s-aliasing-<date>-sampler.pid)

# Optionally remove the partial CSV
rm -f _bmad-output/drill-evidence/v3-1s-aliasing-<date>.csv
```

The cluster state is unchanged. The script extension can be reverted with a single `git revert` if it ever needs to be backed out.

## References

- **Parent story**: `homelab-playbook/_bmad-output/implementation-artifacts/6-5-validation-drill-v3-replication-rpo-for-ct162.md` — surfaces R2; provides the sampler-script + evidence-dir baseline
- **Story 6.5 Dev Agent Record** — §"Gotchas surfaced during this run" (sampler-vs-cycle aliasing); §"Files touched in this drill"
- **Story 6.5 evidence**: `_bmad-output/drill-evidence/v3-ct162-rpo-2026-04-25.csv`, `-summary.txt`
- **Sampler**: `_bmad-output/drill-evidence/v3-rpo-sampler.sh`
- **Runbook**: `homelab-infra/docs/ha-replication-runbook.md §"V3 Drill Results (2026-04-25)"`
- **Workload context**: OMEGA memory `project_quant_trading` (`/home/developer/.claude/projects/-home-developer-workspace-homelab/memory/project_quant_trading.md`) — ct:162 sizing, home-node rationale, why a 1-min RPO matters for this workload
- **Cousin story (concurrent)**: `6-5-2-soak-telemetry-1min-replication.md` — long-tail telemetry that consumes any CYCLE-DURATION-VARIANCE finding from this story
