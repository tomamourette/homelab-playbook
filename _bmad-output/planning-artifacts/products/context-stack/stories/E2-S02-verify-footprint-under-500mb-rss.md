---
type: story
epic: E2
id: E2-S02
title: "Verify GitNexus daemon footprint < 500 MB RSS over 24 h (close architecture AR1)"
size: 0.5d
priority: MUST
fr_refs: [FR-CG-002, FR-CG-012]
nfr_refs: [NFR-FOOTPRINT-002, NFR-FOOTPRINT-003]
adr_refs: [ADR-004]
status: draft
date: 2026-04-25
---

# E2-S02: Verify GitNexus daemon footprint < 500 MB RSS over 24 h (close architecture AR1)

## User Story

As **tomamourette**, I want **the GitNexus daemon's resident memory measured under representative use over a 24-hour window and recorded as a baseline note**, so that **architecture risk AR1 (npm + Node.js footprint may exceed 500 MB) is closed with hard evidence before I commit to MCP wiring and hook registration in E2-S03 and E2-S04 — and so a future regression has a documented week-0 anchor to compare against**.

## Background and Context

Architecture §11 AR1 explicitly lists the GitNexus footprint as an open architectural risk: the brief assumed a Python daemon (~500 MB ceiling) but the actual implementation is Node.js + tree-sitter + LadybugDB; the ceiling is held but the verification is required. NFR-FOOTPRINT-002 sets the hard limit (`< 500 MB resident memory, sampled over 24 h`). NFR-FOOTPRINT-003 also constrains combined disk footprint (FalkorDB data + GitNexus indexes + wiki tree < 5 GB) — GitNexus's contribution is captured here. This story runs at week 0 of the pilot, before hook noise complicates the measurement; it is intentionally short (0.5 d) but blocks E2-S03 because if AR1 fires, ADR-004 must be re-opened (revisit GitNexus or adopt CodeGraphContext exit ramp early).

## Acceptance Criteria

**AC1 — Daemon starts and is identifiable in `ps`.**
- **Given** E2-S01 has installed `gitnexus@1.6.3`,
- **When** the operator starts the daemon via `npx gitnexus daemon` (or whichever upstream-documented start command applies; checked in E2-S01 AC4) AND runs `pgrep -af gitnexus`,
- **Then** at least one process matches AND its command line includes `gitnexus`; the operator records the PID for AC2.

**AC2 — Initial RSS sample < 500 MB.**
- **Given** the daemon has been running ≥ 60 s (settle time) AND a full reindex of `~/workspace/homelab/` has completed once,
- **When** the operator runs `ps -o pid,rss,vsz,cmd -p <PID>`,
- **Then** the RSS value (in KB) divided by 1024 is < 500 (i.e., < 500 MB) AND the value is recorded in `homelab-playbook/docs/decisions/gitnexus-footprint-baseline.md`.

**AC3 — Sustained 24 h RSS sample < 500 MB.**
- **Given** AC1 has passed,
- **When** a sampling cron / loop captures `ps -o pid,rss,cmd -p <PID>` every 15 minutes for 24 h into a CSV at `~/workspace/homelab/_export/gitnexus-rss-week0.csv` AND the operator drives at least 10 representative `git commit` events during the window,
- **Then** the maximum RSS in the CSV is < 500 MB AND the 95th-percentile RSS is < 400 MB (headroom for hook noise added in E2-S04) AND the CSV is committed (or referenced) from the baseline note.

**AC4 — Disk footprint sample (NFR-FOOTPRINT-003 contribution).**
- **Given** the daemon has indexed `~/workspace/homelab/`,
- **When** the operator runs `du -sh ~/.gitnexus 2>/dev/null || du -sh "$(npx gitnexus config get index-path 2>/dev/null || echo ~/.gitnexus)"`,
- **Then** the index directory size is < 1 GB AND the value is recorded in the baseline note (so the combined NFR-FOOTPRINT-003 budget can be tallied in E4).

**AC5 — Privacy / network audit during reindex (FR-CG-002, FR-CG-012).**
- **Given** the daemon is running and a full reindex is in progress,
- **When** the operator captures `tcpdump -i any -n 'tcp and not (host 127.0.0.1 or host ::1)' -w /tmp/gitnexus-net.pcap` for the duration of one full reindex AND inspects the pcap with `tcpdump -r /tmp/gitnexus-net.pcap | grep -vE 'localhost|127\.0\.0\.1' | wc -l`,
- **Then** the count of non-loopback TCP packets attributable to the gitnexus PID is **0** during the reindex (closes FR-CG-002 "no source code over the wire" and FR-CG-012 "no LLM API call for parsing"); the evidence line is appended to the baseline note. (E2-S05 repeats this audit during the parent-folder topology verification — this AC seeds the technique.)

**AC6 — AR1 closure decision recorded.**
- **Given** AC2 + AC3 + AC4 + AC5 all green,
- **When** the operator updates `homelab-playbook/docs/decisions/gitnexus-footprint-baseline.md`,
- **Then** the file ends with one of two explicit verdicts: `AR1: CLOSED — 24h max RSS = <X> MB, 95p = <Y> MB, disk = <Z> MB; proceed to E2-S03.` OR `AR1: BLOCKED — <metric> exceeded; halt E2; revisit ADR-004.`; in the BLOCKED case, the story does NOT pass and an architecture-team escalation is opened.

## Implementation Notes

**Reference architecture sections:** §11 AR1 (the risk this story closes), §4.1 Code-graph layer (daemon shape), §5.4 Backup and recovery (GitNexus index is rebuildable from source, not separately backed up — sets context for AC4).

**Reference ADRs:** ADR-004 (the decision to adopt GitNexus on the < 500 MB premise — this story is the verification leg).

**Sampling cron snippet for AC3** (cron-on-workstation, lives only for the 24 h window):

```bash
# In a one-off systemd-timer or `at`-job — NOT committed long-term.
*/15 * * * * /usr/bin/ps -o pid,rss,cmd -C node,gitnexus | grep gitnexus | awk -v ts="$(date -Iminutes)" '{print ts","$0}' >> ~/workspace/homelab/_export/gitnexus-rss-week0.csv
```

**Network audit shape for AC5:**

```bash
# In one terminal (sudo): tcpdump for 60 s while reindex runs
sudo tcpdump -i any -n -w /tmp/gitnexus-net.pcap 'tcp and not (host 127.0.0.1 or host ::1)' &
# In another: trigger full reindex
npx gitnexus reindex --full
# Stop tcpdump, inspect:
sudo tcpdump -r /tmp/gitnexus-net.pcap | wc -l   # expect 0 (modulo unrelated workstation chatter — filter by PID with iptables/owner-match if noisy)
```

**Baseline note path:** `homelab-playbook/docs/decisions/gitnexus-footprint-baseline.md`. Contents: PID, all sampled RSS values (max + p95 + median), disk footprint, network-audit summary, AR1 verdict, links to the CSV and pcap.

## Test Plan

**Pre-state:**
- E2-S01 AC1–AC6 all green.
- `gitnexus --version` returns `1.6.3`.
- No prior `~/.gitnexus/` index present (or baseline note acknowledges existing index size).

**Action sequence:**
1. Start daemon (AC1); record PID.
2. Trigger full reindex on `~/workspace/homelab/`; wait for completion.
3. Take initial RSS sample (AC2) at T+60s after reindex completes.
4. Start 24 h sampling cron / loop (AC3); during the window, drive ≥ 10 commits.
5. After 24 h: stop sampler; compute max + p95 + median; check < 500 MB max.
6. Capture disk footprint (AC4).
7. During step 2 OR a fresh reindex, run tcpdump audit (AC5).
8. Update baseline note with the AR1 CLOSED / BLOCKED verdict (AC6).

**Post-state checks:**
- `gitnexus-footprint-baseline.md` exists, ends with `AR1: CLOSED ...`.
- `gitnexus-rss-week0.csv` exists with ≥ 96 sample rows.
- pcap inspection summary recorded.

**Rollback:**
- If AR1: BLOCKED, halt E2 immediately; open architecture review per ADR-004 reversal trigger; consider browser-side mode (per architecture §11 AR1) or jump to CodeGraphContext exit ramp.
- Sampler has no persistent side effects — disabling the cron / loop is the only cleanup.

## Dependencies

- **Blocked by:** E2-S01 (binary must be installed).
- **Blocks:** E2-S03 (no point registering MCP if footprint blocks adoption); transitively all of E2-S04..S08.

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| 24 h sampling window slips past sprint cadence. | Low | Low — sample window can run as a background task during E2-S03/S04 prep. | Start the sampler ASAP; do AC2 + AC4 + AC5 immediately for fast partial closure; AC3 finalises 24 h later. |
| RSS spikes during full reindex briefly exceed 500 MB. | Med | Med — would still BLOCK AR1. | Sampler granularity is 15 min, so it captures spikes; if a one-off spike is observed during reindex but steady-state is well under, baseline note must record both numbers and explicitly explain — escalate if spike > 500 MB sustained ≥ 2 samples (30 min). |
| tcpdump permission / noise — unrelated workstation traffic clutters the pcap. | Med | Low — needs filtering. | Filter by destination (LLM-API hosts: `api.openai.com`, `api.anthropic.com`); if zero, claim is supported. Optionally use `iptables --owner` rule to scope to gitnexus's UID. |
| LadybugDB index path not at `~/.gitnexus/` on this version. | Low | Low — du target wrong. | AC4 falls back to `npx gitnexus config get index-path`; if that command doesn't exist on v1.6.3, locate via `lsof -p <PID> | grep ladybug`. |

## Definition of Done

- [ ] AC1–AC6 all green and evidenced.
- [ ] `homelab-playbook/docs/decisions/gitnexus-footprint-baseline.md` committed with `AR1: CLOSED` verdict.
- [ ] `~/workspace/homelab/_export/gitnexus-rss-week0.csv` captured (referenced from the note; may or may not be committed depending on size).
- [ ] Architecture §11 AR1 entry updated to "Closed by E2-S02 (see baseline note)" via PR.
- [ ] Story status updated to `done`; OMEGA `omega_store(...)` records the verdict.
