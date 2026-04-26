---
type: sprint-plan
product: context-stack
version: 1.0.0
status: draft
date: 2026-04-25
duration: 5 sprints (10 calendar weeks)
sprint_length_weeks: 2
brief_ref: product-brief.md
prd_ref: prd.md
arch_ref: architecture.md
epics_ref: epics.md
acceptance_ref: tests/acceptance.md
e2e_ref: tests/e2e-deployment.md
readiness_ref: readiness-check.md
---

# Context Stack — Sprint Plan

## 1. Overview

This plan converts the four epics and 38 INVEST stories from `epics.md` into a concrete **5-sprint** execution schedule. The original phase plan committed each phase to a single sprint; honest math against single-operator capacity says **Epic 4 (Production Hardening) does not fit one 2-week sprint** at this rate. The honest answer is to split E4 into two sprints rather than compress, descope MUSTs, or pretend.

**Inputs digested:**

- `epics.md` — 4 epics, 38 stories, ~37 ideal-days total (E1 ~7d, E2 ~7d, E3 ~9.5d, E4 ~13.5d).
- `architecture.md` §11 + ADR-014 — 8 architectural risks; recalibrated 44 MUST / 26 SHOULD / 3 COULD MoSCoW.
- `tests/acceptance.md` — 325 ACs across 38 stories; vague-AC tightening list (E2 PASS-WITH-NOTES).
- `tests/e2e-deployment.md` — Phase-1 + Phase-2 deploy + 3 disaster drills (D1, D2, D3).
- `readiness-check.md` — verdict PASS-WITH-NOTES, Sprint 1 GO, two Mandatory Fixes queued.

**Capacity model (single-operator, side-project):**

- ~3 effective dev-hours per working day (homelab is not a day job — ops work + meetings + life happen).
- 2-week sprints = 10 calendar days × 5 working days × 3 hrs ≈ 30 raw hours, but realistic ≈ 18 effective hrs/sprint after kickoff (0.5d) + retro (0.5d).
- **Effort multiplier:** ~1.7× from "ideal days" to "real-time wall-clock days". A 1d ideal story is roughly 1.7 real days at 3 hrs/day.
- Within-epic parallelism is limited (single operator). Some interleaving is possible (e.g., docs while a backup cron runs), but dual-context coding is not.

**Top-level honest assessment:**

| Epic | Ideal days | Real wall-clock days | Sprint capacity (10 cal days) | Verdict |
|---|---|---|---|---|
| E1 Decommission | ~7 | ~12 | 10 | **Tight; fits Sprint 1 with disciplined scope** |
| E2 GitNexus Pilot | ~7 | ~12 | 10 | **Tight; fits Sprint 2 with one buffer day** |
| E3 Graphiti Pilot | ~9.5 | ~16 | 10 | **Overflows; ~1-2 days slip into Sprint 4 OR descope COULDs** |
| E4 Production Hardening | ~13.5 | ~23 | 10 | **Does NOT fit one sprint. Must split into S4 + S5.** |

The original brief §4.3 committed each phase to one sprint. That implicit estimate assumed a tighter ideal-day:wall-clock ratio than is realistic for a side-project homelab operator. **Recommendation: 5 sprints (10 weeks), not 4.** The product is still 4 phases; only the schedule changes. The PRD's FR-LLM-007 deferral path remains the safety valve — if Sprint 5 starts and `hybrid_gemma_serving` is not ready, defer LiteLLM to a follow-up backlog and use Sprint 5 to consolidate.

**Total wall-clock duration:** **10 weeks (5 sprints × 2 weeks)** from S1 kickoff to product-level KPI scorecard at end of S5. The week-4 KPI scorecard from the brief becomes a **week-10 product-level KPI scorecard** — operator should adjust §6 KPI cadence in the brief retro accordingly (or run the scorecard at the original week-4 mark on E2/E3 outputs and a second one at week-10 on the integrated stack). E4-S11 anchors the binding gate.

---

## 2. Sprint Calendar

Dates are TBD-relative. Operator picks `S1-D1` calendar date at Sprint 1 kickoff; all subsequent dates derive from that anchor.

| Sprint | Window | Goal | Stories (count) | Ideal effort | Real wall-clock | Kickoff/Retro overhead | Decision Gate |
|---|---|---|---|---|---|---|---|
| **S1** | D1-D10 | Decommission MemPalace + OMEGA cleanly via single PR with 8 sequenced commits + tagged release | E1-S01..S09 (9) | ~7d | ~12d | 0.5d kickoff + 0.5d retro | E1 Exit Gate (epics §3.5): 9-AC checklist + zero-grep + Hermes verify + tag |
| **S2** | D11-D20 | GitNexus pilot installed + parent-folder topology + 5 smoke tests + week-1 KPI scorecard | E2-S01..S08 (8) + S3-prep (cypher-replay.sh, 0.5d) | ~7d + 0.5d | ~12.5d | 0.5d kickoff + 0.5d retro | E2 Exit Gate (epics §4.5): 4-of-5 KPI green at week-1 (K1, K2, K3, K4, K6); footprint < 500 MB; export wrapper exists |
| **S3** | D21-D30 | Graphiti pilot deployed on ct-ai-01 + backup cadence + restore drill + week-2 KPI scorecard | E3-S01..S09 (9) + S4-prep (down -v guards spec, 0.5d) | ~9.5d + 0.5d | ~16d + 1d | 0.5d kickoff + 0.5d retro | E3 Exit Gate (epics §5.5): 4-of-6 KPI green at week-2; FalkorDB < 200 MB; backup + restore drill done; tom-personal namespace verified. **Likely 1-2 day slip into S4** (see §5.4). |
| **S4** | D31-D40 | Production Hardening Part A: wiki tier + $1 cap + Ansible role + ct-dev-homelab deploy + rollback drill | E4-S01, S02, S03, S04, S07, S08 (6) | ~8.5d | ~14d | 0.5d kickoff + 0.5d retro | S4 mid-gate: wiki tier shipped + Ansible deploy succeeded + rollback drill exercised. (Not a product-level gate — that's S5.) |
| **S5** | D41-D50 | Production Hardening Part B: LiteLLM bridge + 50-fact validation + observability digest + exit ramps + product-level KPI gate + retro | E4-S05, S06, S09, S10, S11, S12 (6) | ~5d | ~8.5d | 0.5d kickoff + 0.5d retro | **Product-level Decision Gate (PRD §11):** 4-of-6 KPI green + G-Latency clean + G-Rollback validated. If LiteLLM defers (FR-LLM-007), S5 still ships everything else. |

**Sprint cadence:** 2 weeks per sprint. Total = 10 weeks. Actual elapsed time (with 2-3 day operator gap between sprints to reset context, write the retro, and brief the next sprint) is realistically **11-12 weeks calendar time** — but inside-sprint capacity is what's planned.

**Cumulative effort burndown:** 9 + 8 + 9 + 6 + 6 = 38 stories (matches epics.md). Adding the 2 mandatory-fix items (S3-prep, S4-prep) = 40 work items.

---

## 3. Sprint 1 — Decommission (E1)

### 3.1 Sprint Goal

> Cleanly remove MemPalace + OMEGA from workstation, repo, dev_hosts container, and Hermes config in **one merge-commit PR with 8 sequenced commits**, tagged `phase-1-decommission-complete`, with `grep -r -i 'mempalace\|omega' homelab/` returning zero on a clean clone.

### 3.2 Sprint Backlog

| Story ID | Title | Size (ideal d) | Real est (wc-d) | Dependencies | Owner | Notes |
|---|---|---|---|---|---|---|
| E1-S01 | Disable OMEGA hooks in `~/.claude/settings.json` | 0.5 | 1 | — | tomamourette | Disable-only; run one full Claude Code session to verify silence (FR-DEC-007 first half). Commit 1. |
| E1-S02 | Remove OMEGA hook entries from settings.json | 0.5 | 1 | E1-S01 | tomamourette | Full removal after disable session passes silent. Commit 2. |
| E1-S03 | Uninstall omega-memory + remove role + group_vars | 1.0 | 1.7 | E1-S02 | tomamourette | `pip uninstall`, delete `ai-dev-omega-memory` role, drop OMEGA group_vars from dev_hosts container playbook (FR-DEC-008, FR-DEP-009). Commit 3. |
| E1-S04 | Remove MemPalace store + role + skills | 1.0 | 1.7 | E1-S03 | tomamourette | Delete `~/.mempalace/`, `ai-dev-mempalace` role, three Hermes skills. Commit 4. |
| E1-S05 | Remove MemPalace wiring + knowledge-query orchestrator | 0.5 | 1 | E1-S04 | tomamourette | Delete `wire-mempalace.yml` + degenerated `knowledge-query` skill. Commit 5. |
| E1-S06 | Remove mempalace conditionals from Hermes Jinja | 1.5 | 2.5 | E1-S05 | tomamourette | **Riskiest commit.** Edit `config.yaml.j2`, `defaults/main.yml`, `verify.yml`. Commit 6. |
| E1-S07 | Author Phase-1 decommission doc | 0.5 | 1 | E1-S06 | tomamourette | Capture every action + FR-DEC-012 no-data-migration record. Commit 7. |
| E1-S08 | Hermes verify run on ct-dev-homelab + grep/process gates | 1.0 | 1.7 | E1-S07 | tomamourette | Execute `verify.yml` on `ct-dev-homelab`; commit verify-output as evidence. Commit 8. |
| E1-S09 | Forward-protection pre-push hook + tag release | 0.5 | 1 | E1-S08 (post-merge) | tomamourette | Pre-push hook + tag `phase-1-decommission-complete`. Post-merge work. |

**Sprint total:** 7 ideal days / ~12.6 wall-clock days. **Buffer:** ~3.4 wall-clock days (after kickoff/retro overhead) — adequate for the riskiest commit (E1-S06 Hermes Jinja).

### 3.3 Sprint Plan (week-by-week)

**Week 1 (D1-D5):**

- **D1 (kickoff, 0.5d):** Verify pre-conditions: `ct-dev-homelab` reachable, current Hermes `verify.yml` works pre-decommission (baseline run captured), branch `decommission/context-stack-phase-1` created, working tree clean. Read ADR-010 + `e2e-deployment.md` §3.1 (decommission path).
- **D1 (PM) - D2:** E1-S01 + E1-S02 (commit 1 + 2). Run a full Claude Code session between them to verify hooks fire silent — this is the safety net per ADR-010.
- **D3-D4:** E1-S03 (commit 3). Uninstall omega-memory pip package; remove role; remove group_vars; idempotent re-run check.
- **D5:** E1-S04 (commit 4). Delete MemPalace surface.

**Week 2 (D6-D10):**

- **D6:** E1-S05 (commit 5). Delete wiring + orchestrator.
- **D7-D8:** E1-S06 (commit 6, **risky**). Hermes Jinja edits. Run Hermes verify on ct-dev-homelab between commits 6 and 7 (sanity check before doc).
- **D9 (AM):** E1-S07 (commit 7). Decommission doc.
- **D9 (PM):** E1-S08 (commit 8). Final Hermes verify run; grep/pgrep gates; commit verify-output evidence.
- **D9 (PM)** — Open PR with merge-commit instruction in PR body (NOT squash). Self-review.
- **D10 (AM):** Merge PR. E1-S09: install pre-push hook + `git tag phase-1-decommission-complete && git push --tags`.
- **D10 (PM):** Sprint retro (0.5d). Document actual vs estimated. **During retro: spawn S3-prep backlog item: author `cypher-replay.sh` (≤ 0.5d). Schedule for early S2.**

### 3.4 Risks

| Risk | Mitigation in this sprint |
|---|---|
| AR7 — Single-PR wide surface ships dead code | E1-S08 grep + pgrep gates are hard checks; per-commit revertability per ADR-010 (merge-commit not squash) |
| R7 — Hermes Jinja edits break unrelated paths | E1-S06 isolated; Hermes verify run after commit 6 AND after commit 8 |
| Operator-irreversibility — accidentally squash-merging | PR description carries explicit "MUST be merge-commit, NOT squash" line; self-review checklist |
| MEMORY.md auto-memory continuity break | E1 acceptance criterion #8 — verify auto-memory loads at next session start |
| ct-dev-homelab unreachable mid-sprint | D1 kickoff verifies reachability; if down, contingency = run Hermes verify locally first, defer ct-dev-homelab run to D9-D10 |

### 3.5 Sprint Definition of Done

S1 is "done" when **all** of:

1. PR merged to `main` with merge-commit (not squash); 8 commits visible on `main` history.
2. Tag `phase-1-decommission-complete` pushed.
3. `grep -r -i 'mempalace\|omega' homelab/` (excluding `_bmad-output/`, decommission doc, git history) returns 0.
4. `pgrep -f 'mempalace\|omega'` on workstation AND on `ct-dev-homelab` returns 0.
5. Hermes `verify.yml` exits 0 on `ct-dev-homelab`.
6. `~/.claude/settings.json` shows zero OMEGA hook entries.
7. Decommission doc exists with FR-DEC-012 no-data-migration record.
8. Auto-memory `MEMORY.md` loads end-to-end at next session start.
9. Pre-push hook installed; CI lint pending (downgrade from week 1).
10. Sprint retro authored; lessons stored in OMEGA-equivalent (or new project memory file `project_context_stack_sprint_log.md`).

### 3.6 Sprint Decision Gate (proceed to S2?)

**Gate criteria (epics §3.5):**

- All 9 acceptance criteria above pass → **GO** to S2.
- If any criterion fails: hold S2 start; `git revert` offending commit pre-merge, OR exercise FR-DEP-007 rollback (re-install OMEGA + MemPalace from prior commit) if regression surfaces post-merge.

### 3.7 Demo / Review Artifacts

- The merge-commit PR (link in retro).
- Pre/post `grep` output captured in decommission doc.
- Pre/post Hermes `verify.yml` output captured in decommission doc.
- Tag URL: `git show phase-1-decommission-complete`.
- Retro entry in project memory.

---

## 4. Sprint 2 — GitNexus Pilot (E2)

> **Sprint 2 Pivot Note (2026-04-26).** Mid-sprint, E2-S01 npm install passed but the daemon failed at runtime: LadybugDB native binding (`lbugjs.node`) requires `GLIBCXX_3.4.32`; Debian 12 bookworm workstation maxes at `_3.4.30`. Operator chose **Option B: containerise** via the official `ghcr.io/abhigyanpatwari/gitnexus:1.6.3` Docker image (Debian 13 trixie base). Captured in **ADR-015**; ADR-005 amended for transport variance (HTTP/4747 instead of stdio). Inserted as **E2-S01.5** between S01 and S02; npm binary uninstalled. ½-day slip absorbed by Sprint 2's existing slack budget (~3.3 wall-clock days; see §4.2 Sprint total). E2-S02 footprint test now retries against the containerised daemon; E2-S03 MCP wiring uses `claude mcp add --transport http`. No backlog descope.

### 4.1 Sprint Goal

> Install **GitNexus v1.6.3** on the workstation as MCP-native code-graph; wire PreToolUse + PostToolUse-on-commit hooks; verify parent-folder topology over `~/workspace/homelab/` (all 3 sibling repos); pass 5 smoke tests; ship `scripts/gitnexus-export.sh`; reach the **week-1 KPI gate** (4-of-5 green: K1, K2, K3, K4, K6).

### 4.2 Sprint Backlog

| Story ID | Title | Size (ideal d) | Real est (wc-d) | Dependencies | Owner | Notes |
|---|---|---|---|---|---|---|
| **S3-prep** | Author `cypher-replay.sh` (Mandatory Fix #1) | 0.5 | 1 | E1 merged | tomamourette | **Parallel work — does not block E2 critical path.** Authored under `homelab-playbook/roles/ai-dev-graphiti/files/cypher-replay.sh` so it's ready when E3-S07 lands in S3. Amend E3-S07 AC11 in same PR. |
| E2-S01 | Install GitNexus 1.6.3 + supply-chain verification | 1.0 | 1.7 | E1 merged | tomamourette | `npm install -g gitnexus@1.6.3`; verify maintainer + checksum + ≥3mo activity (NFR-SUPP-001); capture in workstation Ansible role/installer. |
| E2-S02 | Verify footprint < 500 MB | 0.5 | 1 | E2-S01 | tomamourette | Sample daemon RSS over 24h; closes AR1. |
| E2-S03 | Wire MCP registration to Claude Code | 0.5 | 1 | E2-S01 | tomamourette | `npx gitnexus setup`; verify `claude mcp list` shows healthy. |
| E2-S04 | Configure PreToolUse + PostToolUse-on-commit hooks | 1.0 | 1.7 | E2-S03 | tomamourette | Edit `~/.claude/settings.json`; PostToolUse fires on Bash containing `git commit`. |
| E2-S05 | Configure parent-folder topology + privacy audit | 1.0 | 1.7 | E2-S03 | tomamourette | Index `~/workspace/homelab/`; tcpdump audit during full reindex (no outbound LLM). |
| E2-S06 | Implement 5 smoke-test scenarios | 1.5 | 2.5 | E2-S04, E2-S05 | tomamourette | Cross-repo query, impact analysis, context retrieval, incremental + full reindex timing, graceful-degradation drill. |
| E2-S07 | Implement export wrapper `scripts/gitnexus-export.sh` | 1.0 | 1.7 | E2-S03 | tomamourette | NDJSON per ADR-012; closes Q8 + FR-CG-010; documents exit ramp. |
| E2-S08 | Week-1 decision-gate scorecard | 0.5 | 1 | E2-S06, E2-S07 | tomamourette | K1 token-reduction sample on 3 cross-repo questions; K2 reindex timings; K3 spend (=0); K4 non-blank artifact; K6 subjective uplift. Gate decision recorded. |

**Sprint total:** 7d ideal + 0.5d S3-prep = 7.5 ideal-days / ~12.7 wall-clock days. **Buffer:** ~3.3 wall-clock days.

### 4.3 Sprint Plan (week-by-week)

**Week 1 (D11-D15):**

- **D11 (kickoff, 0.5d):** Pre-flight: GitNexus 1.6.3 still on npm? (Outstanding question #3 from readiness-check.) Anthropic Claude Code CLI working? `claude mcp list` baseline captured.
- **D11 (PM)-D12:** E2-S01 install + supply-chain verification.
- **D13:** E2-S03 MCP registration + E2-S02 footprint baseline (start the 24h sample).
- **D14:** E2-S07 export wrapper (parallel to footprint sample running) + start S3-prep `cypher-replay.sh` authoring (interleave with passive work).
- **D15:** E2-S04 hook configuration (PreToolUse + PostToolUse-on-commit).

**Week 2 (D16-D20):**

- **D16:** E2-S05 parent-folder topology + privacy audit (`tcpdump` during a full reindex).
- **D17-D18:** E2-S06 5 smoke tests (cross-repo query, impact, context, incremental reindex < 30 s, full reindex < 60 s, graceful-degradation drill).
- **D19 (AM):** E2-S02 24h footprint check finalised; E2-S08 week-1 KPI scorecard authored.
- **D19 (PM):** Sprint retro. **During retro: spawn S4-prep backlog item: author `down -v` guard spec for E4-S07 rollback playbook (≤ 0.5d).**
- **D20:** Slack day for any week-1 KPI failure investigation OR start of S3-prep `cypher-replay.sh` if not already done (paired with E3-S01 prep notes for kickoff).

### 4.4 Risks

| Risk | Mitigation in this sprint |
|---|---|
| AR1 — GitNexus footprint > 500 MB | E2-S02 measures over 24h; if > 500 MB, file follow-up story OR exit-ramp to CodeGraphContext (ADR-004 alt) |
| AR4 / R1 — GitNexus single-maintainer abandonment | E2-S01 verifies ≥3mo upstream activity at install; E2-S07 export wrapper exists day 1 |
| Supply-chain — npm typosquat | E2-S01 verifies `gitnexus` package name + maintainer + checksum (graphify vs graphifyy lesson) |
| G-Latency — new hooks regress session-start | E2-S08 measures NFR-PERF-001; if > 1 s overhead, hooks tuned |
| GitNexus 1.6.3 yanked from npm (Outstanding Q #3) | D11 pre-flight checks npm registry; if yanked, version-bump revision before starting E2-S01 |

### 4.5 Sprint Definition of Done

S2 is "done" when **all** of:

1. `claude mcp list` shows `gitnexus` healthy.
2. `~/.claude/settings.json` has PreToolUse + PostToolUse hooks present and firing on `git commit`.
3. Parent-folder topology covers all 3 sibling repos; verified by Cypher query returning nodes from each.
4. Daemon RSS < 500 MB measured over 24h.
5. Incremental reindex < 30s; full reindex < 60s.
6. 5 smoke tests pass (E2-S06).
7. `scripts/gitnexus-export.sh` produces NDJSON; exit-ramp doc references it.
8. Week-1 KPI scorecard: ≥ 4-of-5 green.
9. `cypher-replay.sh` authored and committed (S3-prep done).
10. Sprint retro authored.

### 4.6 Sprint Decision Gate (proceed to S3?)

**Gate criteria (epics §4.5):**

- Per epics §4.5, **proceed to S3 regardless of E2 KPI outcome** — pilots are independent.
- However: if E2 fails week-1 gate or AR1 fires, log regression and either (a) exercise GitNexus rollback (`npm uninstall -g gitnexus` + `claude mcp remove`), or (b) accept regression with documented gap and continue to S3. The product-level gate at S5 is binding.

### 4.7 Demo / Review Artifacts

- `claude mcp list` output (gitnexus healthy).
- 24h RSS sample chart/log.
- Reindex timings from PostToolUse log.
- Smoke-test session transcripts.
- Week-1 KPI scorecard markdown.
- `cypher-replay.sh` committed.

---

## 5. Sprint 3 — Graphiti Pilot (E3)

### 5.1 Sprint Goal

> Stand up **Graphiti + FalkorDB Docker Compose stack** on `ct-ai-01` per the 488-line install runbook; configure `gpt-4o-mini` + embeddings + `SEMAPHORE_LIMIT=5` + `tom-personal` namespace; ship three-layer backup (AOF + RDB + Cypher monthly); execute restore drill; pass 5 functional smoke tests; reach the **week-2 KPI gate** (4-of-6 green including K5 first-shot recall).

### 5.2 Sprint Backlog

| Story ID | Title | Size (ideal d) | Real est (wc-d) | Dependencies | Owner | Notes |
|---|---|---|---|---|---|---|
| **S4-prep** | Spec `down -v` guards for E4-S07 rollback playbook (Mandatory Fix #2) | 0.5 | 1 | — | tomamourette | Drafts the AC text + the `cp -a` pre-step OR `--force-data-loss` guard for E4-S07; not implemented yet (that's S4) but spec lands here. |
| E3-S01 | Stand up Docker Compose stack on ct-ai-01 | 1.5 | 2.5 | E1 merged | tomamourette | Compose at `/srv/graphiti/docker-compose.yml`; `.env` mode 600; pinned tags. Runbook §6 steps 1-7. **Pre-flight: verify cron daemon installed on ct-ai-01 (Outstanding Q #2).** |
| E3-S02 | Configure MCP HTTP transport + Tailscale reach | 1.0 | 1.7 | E3-S01 | tomamourette | Bind 127.0.0.1:8000; verify Tailscale reach; `claude mcp add --transport http`. Runbook §6 steps 8-10. |
| E3-S03 | Update CLAUDE.md Memory (Graphiti) section | 0.5 | 1 | E3-S02 | tomamourette | Document read/write semantics; replaces deleted OMEGA section. |
| E3-S04 | Configure gpt-4o-mini + embeddings + SEMAPHORE + telemetry-off | 1.0 | 1.7 | E3-S01 | tomamourette | `.env` settings; INFO logs + monthly rotation. |
| E3-S05 | Smoke-test add_episode + search + verify tom-personal namespace | 1.0 | 1.7 | E3-S02, E3-S04 | tomamourette | Probe write returns UUID; verify default group_id (closes AR8). Runbook §7 tests 1-2. |
| E3-S06 | Implement 5 functional scenarios | 1.5 | 2.5 | E3-S05 | tomamourette | Bi-temporal + graceful-degradation drill (stop FalkorDB, < 3s timeout) + multi-episode supersession. |
| E3-S07 | Implement Graphiti backup (AOF + RDB + monthly Cypher export) **+ amend AC11: cypher-replay.sh** | 1.5 | 2.5 | E3-S01 | tomamourette | Per ADR-007. **Mandatory Fix #1 lands here:** AC11 commits `cypher-replay.sh` (already authored in S2 prep) into role and exercises a round-trip in AC12. |
| E3-S08 | Restore drill | 1.0 | 1.7 | E3-S07 | tomamourette | Stop containers; restore from AOF + RDB + Cypher; verify probe data returns; document. |
| E3-S09 | Week-2 decision-gate scorecard | 0.5 | 1 | E3-S05, E3-S06, E3-S07 | tomamourette | Full 6-KPI scorecard incl. K5 first-shot recall on 8 operator-tagged retro queries; FalkorDB RAM check. |

**Sprint total:** 9.5d ideal + 0.5d S4-prep = 10 ideal-days / ~17 wall-clock days. **Buffer:** ~-1 wall-clock day (i.e., **~1-2 day overflow likely**). See §5.4 risk; mitigations below.

### 5.3 Sprint Plan (week-by-week)

**Week 1 (D21-D25):**

- **D21 (kickoff, 0.5d):** Pre-flight: cron installed on ct-ai-01? OpenAI API key in `/srv/graphiti/.env` mode 600? Tailscale reachable from workstation? Read runbook §6 fully.
- **D21 (PM)-D23:** E3-S01 Compose stack stand-up (runbook §6 steps 1-7). This is the heaviest setup story.
- **D24:** E3-S02 MCP HTTP transport + Tailscale reach + S4-prep `down -v` guard spec (parallel light work).
- **D25:** E3-S04 model + SEMAPHORE + telemetry config + start E3-S03 CLAUDE.md edit.

**Week 2 (D26-D30):**

- **D26:** E3-S03 finalize + E3-S05 namespace verification + first probe write.
- **D27-D28:** E3-S06 5 functional scenarios (bi-temporal + graceful-degradation drill).
- **D28-D29:** E3-S07 backup cron + AC11 cypher-replay round-trip.
- **D29-D30:** E3-S08 restore drill + E3-S09 week-2 KPI scorecard.
- **D30:** Sprint retro. Decision: did we slip? If E3-S08 or E3-S09 overflowed, **explicitly carry the slipped story into S4 backlog at S4 kickoff** — do not pretend it landed.

### 5.4 Risks

| Risk | Severity | Mitigation in this sprint |
|---|---|---|
| **Sprint overflow (~1-2d) — E3 has the highest ideal-day count** | **HIGH** | Mitigation 1: S3-S03 (CLAUDE.md doc) is interleavable with other stories — actually 0.5d typing time. Mitigation 2: E3-S06 graceful-degradation drill could be deferred to S4 day 1 if time-constrained (it's a SHOULD per ADR-014 / FR-MEM-013). Mitigation 3: K5 first-shot recall measurement requires 1 week of operator-tagged queries — start tagging on D22 (immediately after Compose is up) so by D29 there's a week of data. |
| AR8 — default group_id discipline (writes land in `main` not `tom-personal`) | MEDIUM | E3-S05 explicit AC; codified in CLAUDE.md (E3-S03) |
| AR3 — OpenAI Usage API eventual consistency overshoot | LOW (cap is in S4) | Manual daily billing watch this sprint; auto-throttle in S4 |
| R6 — spend creep if Graphiti chatty | LOW | `SEMAPHORE_LIMIT=5` baseline (E3-S04); manual check |
| R2 — Bi-temporal value premature judgment | LOW | Week-2 gate is intermediate; binding gate is S5; brief §6 prohibits promote/demote before week 4 (here: end of S5) |
| Outstanding Q #2 — cron may be absent on ct-ai-01 LXC | MEDIUM | D21 kickoff verifies; if absent, add Ansible task to E3-S01 to install `cron` package |
| Graphiti 1.0.2 image yanked from registry | LOW | D21 pre-flight `docker pull zepai/graphiti-mcp:v1.0.2` — fail fast |

### 5.5 Sprint Definition of Done

S3 is "done" when **all** of:

1. `docker compose ps` on ct-ai-01: graphiti-mcp + graphiti-falkordb both `Up`.
2. `claude mcp list` shows `graphiti` over HTTP, healthy.
3. Probe `add_episode` returns UUID; `search_facts` retrieves it.
4. Bi-temporal `valid_at` query passes (smoke test 3).
5. All writes land in `tom-personal` (default group verified).
6. FalkorDB resident memory < 200 MB at end of sprint.
7. AOF rewrite cron daily; RDB cron weekly; first monthly Cypher export executed.
8. `cypher-replay.sh` committed AND restore drill round-trip exercised it (AC11+12 of E3-S07).
9. Restore drill (E3-S08) executed: data fully restored from backups; documented.
10. Week-2 KPI scorecard: ≥ 4-of-6 green.
11. Sprint retro authored. **Carry-over list explicit if any story slipped.**

### 5.6 Sprint Decision Gate (proceed to S4?)

**Gate criteria (epics §5.5):**

- All 9 acceptance criteria above pass → **GO** to S4.
- Combined daily spend (E2 + E3) under $1/day informal cap.
- No blocking-tool-call hangs > 3s (NFR-AVAIL-002).
- If E3 KPI gate fails: per brief §4.3 Phase 2 gate — migrate-or-revert. Exit ramp: `docker compose down` + `claude mcp remove graphiti` + monthly Cypher export retained.

### 5.7 Demo / Review Artifacts

- `docker compose ps` output.
- Probe `add_episode` UUID + `search_facts` round-trip.
- Bi-temporal query result.
- Backup files listing under `/srv/graphiti/data/`.
- Restore drill log.
- Week-2 KPI scorecard markdown.
- `cypher-replay.sh` round-trip evidence.

---

## 6. Sprint 4 — Production Hardening Part A (E4 partial)

### 6.1 Sprint Goal

> Ship the **wiki tier** (schema + 3-5 seeds + `wiki-query` skill); enforce the **daily $1 hard-cap auto-throttle** (ADR-008); wrap the stack in the **`ai-dev-context-stack` Ansible role**; deploy to **`ct-dev-homelab`** and exercise **rollback drill** (G-Rollback gate). Defer LiteLLM bridge + observability digest + product KPI scorecard to S5.

### 6.2 Scope Decision (E4 split rationale)

E4 has 12 stories totalling ~13.5 ideal days / ~23 wall-clock days. A 2-week sprint at ~10 wall-clock days cannot fit it without descoping MUSTs. The two available levers are:

1. **Descope COULDs and aggressive SHOULD trim** — saves ~2.5d (FR-OBS-002 cap is COULD per ADR-014; FR-LLM-005..008 are MUSTs but FR-LLM-007 deferral path explicit). Net: ~11d ideal / ~18.5d wall-clock. Still doesn't fit.
2. **Split E4 into S4 (Part A) + S5 (Part B)** — preserves all MUSTs and SHOULDs; clean decision-gate at end of S5.

**Recommendation: split (lever 2).** The FR-LLM-007 deferral path is the safety valve for S5 if `hybrid_gemma_serving` slips. Lever 1 alone is not enough.

**S4 Part A scope (6 stories, ~8.5 ideal days):** wiki tier (S01-S03), $1 cap (S04), Ansible role (S07), ct-dev-homelab deploy + rollback (S08).

**S5 Part B scope (6 stories, ~5 ideal days):** LiteLLM bridge (S05-S06), observability digest (S09), query hierarchy + exit ramps (S10), product KPI scorecard (S11), retro (S12).

### 6.3 Sprint Backlog

| Story ID | Title | Size (ideal d) | Real est (wc-d) | Dependencies | Owner | Notes |
|---|---|---|---|---|---|---|
| E4-S01 | Define wiki page schema + bootstrap index.md + _schema.md | 1.0 | 1.7 | E1 merged | tomamourette | Frontmatter spec per ADR-006; directory layout. |
| E4-S02 | Bootstrap initial 3-5 wiki seed entries | 1.5 | 2.5 | E4-S01 | tomamourette | Tailscale policy, PVE cluster, decommission runbook, Graphiti install ref, GitNexus topology. Track ≥3 sessions/seed. |
| E4-S03 | Author wiki-query skill (read-on-demand) | 1.0 | 1.7 | E4-S01 | tomamourette | `~/.claude/skills/wiki-query/SKILL.md`; allowed-tools=Read; smoke-test on seeds. |
| E4-S04 | Implement daily $1 hard-cap auto-throttle | 1.5 | 2.5 | E3 complete | tomamourette | `cost-cap.sh` cron on ct-ai-01; ntfy via CT101; manual breach test. |
| E4-S07 | Author `ai-dev-context-stack` Ansible role **+ down -v guard (Mandatory Fix #2)** | 1.5 | 2.5 | E2, E3 complete | tomamourette | Wraps workstation + ct-ai-01 install. **AC adds: rollback playbook MUST refuse `down -v` without `--force-data-loss` flag OR auto `cp -a /srv/graphiti/data /srv/graphiti/data.bak.<TS>` first (Mandatory Fix #2 from S3-prep spec).** |
| E4-S08 | Deploy to ct-dev-homelab + E2E suite + rollback drill | 1.5 | 2.5 | E4-S07 | tomamourette | Run role; 5 smoke tests; rollback drill (G-Rollback gate). E2E plan §4 + §5. |

**Sprint total:** 8.5 ideal-days / ~14.4 wall-clock days. **Overflow: ~4.4 wall-clock days.** Mitigation: see §6.4. The buffer is genuinely tight here — operator should be honest about Sprint 4 actuals at retro.

### 6.4 Sprint Plan (week-by-week)

**Week 1 (D31-D35):**

- **D31 (kickoff, 0.5d):** Pre-flight: ct-dev-homelab reachable? S2 + S3 outputs (GitNexus install role + Graphiti compose unit) under version control? Re-read S4-prep `down -v` guard spec. Verify `hybrid_gemma_serving` status check (informational — affects S5 not S4).
- **D31 (PM)-D32:** E4-S01 wiki schema + bootstrap.
- **D33-D34:** E4-S02 seed entries (3-5 pages from highest-leverage memory notes).
- **D34-D35:** E4-S03 wiki-query skill (interleaves with E4-S02 since seeds reference each other).

**Week 2 (D36-D40):**

- **D36-D37:** E4-S04 $1 cap auto-throttle (cron + ntfy + manual breach test).
- **D37-D38:** E4-S07 Ansible role authoring with **down -v guard AC enforced**.
- **D39:** E4-S08 ct-dev-homelab deploy + 5 smoke tests + **rollback drill (G-Rollback)**.
- **D40 (AM):** Slack day for any deploy-flake recovery OR overflow from D39.
- **D40 (PM):** Sprint retro. Decision: are we ready for S5 LiteLLM work? Has `hybrid_gemma_serving` shipped? If NOT, S5 plan reshapes to defer LiteLLM (FR-LLM-007 path).

**Honest disclosure:** This sprint has the tightest buffer of all 5. If E4-S07 (Ansible role) takes 3 wall-clock days instead of 2.5 (likely — it's wrapping two non-trivial deliverables), E4-S08 may slip 1 day into early S5. That's acceptable; flag at retro.

### 6.5 Risks

| Risk | Severity | Mitigation in this sprint |
|---|---|---|
| **Sprint buffer near zero** | **HIGH** | E4-S02 seed count: aim for 3 (the SHOULD-bar minimum), not 5; defer 4-5 to backlog. E4-S07 reuses ct-ai-01 Compose unit verbatim (do NOT refactor). |
| AR6 — wiki content drift, last_reviewed > 6mo | LOW | Schema enforces `last_reviewed`; `wiki-lint.sh` warns; quarterly review backlog ticket created at retro |
| Mandatory Fix #2 — `down -v` data-loss footgun | MEDIUM | E4-S07 AC enforces; verified during E4-S08 rollback drill |
| ct-dev-homelab in flux during deploy | MEDIUM | D31 pre-flight; if down, defer E4-S08 deploy to S5 D41 |
| AR3 — OpenAI Usage API eventual consistency | LOW | E4-S04 cron at 30 min cadence; documented overshoot acceptable |
| Operator-irreversibility — accidentally `docker compose down -v` on ct-ai-01 directly (not via playbook) | MEDIUM | E4-S07 also adds operator-facing `cp -a` aliasing in the runbook; E4-S08 rollback drill rehearses the safe path |

### 6.6 Sprint Definition of Done

S4 is "done" when **all** of:

1. Wiki tree exists at `homelab-playbook/wiki/` with `index.md`, `_schema.md`, ≥3 seed entries.
2. Each seed entry referenced by ≥1 Claude Code session (3×3 target relaxed to 3×1 if running tight; full 3×3 verified at S5 retro per FR-WIKI-006 SHOULD).
3. `wiki-query` skill installed; reads files in ≤200 ms.
4. `scripts/wiki-lint.sh` runs in pre-commit and exits 0.
5. `cost-cap.sh` cron firing every 30 min; manual breach test confirms `SEMAPHORE_LIMIT=5→1` + ntfy alert; auto-restore at UTC day rollover.
6. `ai-dev-context-stack` Ansible role exists; deploys end-to-end on ct-dev-homelab; `verify.yml` exits 0.
7. **Mandatory Fix #2 verified:** rollback playbook refuses `down -v` without explicit flag OR auto-`cp -a` first.
8. 5 smoke tests on ct-dev-homelab pass (3-of-5 hard-pass + 2-of-5 quality lenient per ADR-014 SHOULD).
9. Rollback drill exercised once on ct-dev-homelab; returns to pre-deploy state in ≤1 day operator-wall-time.
10. Sprint retro authored. `hybrid_gemma_serving` status confirmed for S5 planning.

### 6.7 Sprint Decision Gate (proceed to S5?)

**Gate criteria:**

- All 10 acceptance criteria above pass → **GO** to S5.
- If E4-S08 G-Rollback drill fails: **stack does NOT promote off ct-dev-homelab**; S5 becomes a stabilization sprint to fix the rollback path (LiteLLM defers automatically).
- If `hybrid_gemma_serving` not in beta by S4 retro: S5 LiteLLM stories defer per FR-LLM-007; S5 reshapes to product-finalisation only.

### 6.8 Demo / Review Artifacts

- Wiki tree screenshot/listing.
- `wiki-query` skill demo on a seed entry.
- $1 cap manual breach test log + ntfy alert screenshot.
- Ansible role play-by-play log on ct-dev-homelab.
- Rollback drill timing + before/after diff.

---

## 7. Sprint 5 — Production Hardening Part B + LiteLLM (E4 remainder)

### 7.1 Sprint Goal

> Ship the **LiteLLM bridge** (Graphiti's LLM call → `hybrid_gemma_serving` via `OPENAI_BASE_URL` override) behind the **95%-well-formed-JSON validation gate** (FR-LLM-005); ship the **weekly observability digest**; document **unified query hierarchy + exit ramps**; run the **product-level KPI scorecard at week 4-equivalent** (G-Latency clean + G-Rollback validated); author **Phase-4 retro** and close the product.
>
> **OR:** if `hybrid_gemma_serving` is not ready, exercise FR-LLM-007 deferral and use the LiteLLM time to consolidate documentation, additional wiki seeds, and tighten the 6 vague ACs from acceptance.md §5.1.

### 7.2 Scope (two paths)

**Path A — LiteLLM ships:**

| Story ID | Title | Size (ideal d) | Real est (wc-d) |
|---|---|---|---|
| E4-S05 | Build LiteLLM bridge config (OPENAI_BASE_URL override) | 1.0 | 1.7 |
| E4-S06 | Validate LiteLLM extraction-JSON quality on 50-fact set | 1.5 | 2.5 |
| E4-S09 | Implement weekly observability digest | 0.5 | 1 |
| E4-S10 | Document unified query hierarchy + exit ramps | 1.0 | 1.7 |
| E4-S11 | Run product-level 4-of-6 KPI scorecard + G-Latency + G-Rollback | 0.5 | 1 |
| E4-S12 | Phase-4 retro + epic close | 0.5 | 1 |

**Path A total:** 5 ideal-days / ~8.9 wall-clock days. **Buffer:** ~1 wall-clock day. Tight but feasible.

**Path B — LiteLLM defers (FR-LLM-007 invoked):**

- E4-S05 + E4-S06 → backlog (saved ~4.2 wall-clock days).
- Replace with: (i) inline-tighten the 6 vague ACs from acceptance.md §5.1 (~0.5d); (ii) author 2-3 additional wiki seeds (~1d); (iii) consolidate the weekly observability digests collected during S4-S5 into a 4-week trend report (~0.5d); (iv) optionally start `hybrid_gemma_serving` pre-integration spike if the gateway is partially ready (~1.5d).
- E4-S09, S10, S11, S12 still ship.
- **Path B total:** ~5 ideal-days / ~8.5 wall-clock days. **Buffer:** ~1.5 wall-clock days.

**Decision point:** End of S4 retro (D40). Path A or Path B chosen explicitly; backlog ticket recorded for deferred work.

### 7.3 Sprint Plan (Path A; week-by-week)

**Week 1 (D41-D45):**

- **D41 (kickoff, 0.5d):** Confirm Path A decision; `hybrid_gemma_serving` LiteLLM gateway reachable from ct-ai-01? `OPENAI_BASE_URL` value documented? 50-fact validation set source decided (EQ5 from epics.md — handcrafted operator set vs Graphiti corpus extract).
- **D41 (PM)-D42:** E4-S05 LiteLLM bridge config (env var override).
- **D43-D45:** E4-S06 50-fact validation harness + run + gate (≥95% well-formed JSON). **If fails: auto-fallback (revert env vars) per FR-LLM-006; defer Phase 4 with backlog ticket; continue with rest of S5.**

**Week 2 (D46-D50):**

- **D46:** E4-S09 weekly observability digest template + first authored digest.
- **D47-D48:** E4-S10 query hierarchy doc + exit ramps (GitNexus + Graphiti).
- **D49 (AM):** E4-S11 product-level KPI scorecard (K1-K6 from 4-week digest aggregate; G-Latency vs pre-deploy baseline; G-Rollback evidence from S4-S08).
- **D49 (PM):** E4-S12 Phase-4 retro + epic close.
- **D50:** Slack day; final cross-check; product handoff (`product-readme.md`?). Sprint retro.

### 7.4 Risks

| Risk | Severity | Mitigation in this sprint |
|---|---|---|
| AR2 — LiteLLM Responses API quirks may break < 95% gate | HIGH (Path A) | E4-S06 validation gate is the trigger; ADR-011 fallback = side-by-side proxy OR revert env vars (FR-LLM-008); Path B is the meta-fallback |
| AR5 — Graphiti `OpenAIGenericClient` selection bugs | MEDIUM | E4-S05 spike runs first; if no-fork path fails, side-by-side proxy alt; worst case Path B |
| `hybrid_gemma_serving` not ready by S5 kickoff | HIGH | D40 decision (Path A vs B); FR-LLM-007 deferral path explicit |
| Product-level KPI gate fails at E4-S11 | MEDIUM | Per brief §6 hard gates — if 4-of-6 not green or G-Latency regressed, stack does NOT promote off ct-dev-homelab; documented in retro; remediation backlog item |
| Operator fatigue at Sprint 5 (10-week marathon) | MEDIUM | Slack day D50; allow product retro to spill 1-2 days post-D50 calendar without penalty |

### 7.5 Sprint Definition of Done (Path A)

S5 is "done" when **all** of:

1. (Path A) LiteLLM bridge configured on graphiti-mcp container; embeddings stay on OpenAI.
2. (Path A) 50-fact validation set executed; ≥95% well-formed JSON OR auto-fallback exercised.
3. (Path A) FR-LLM-008 reversibility: revert env vars round-trip < 1 day.
4. Weekly observability digest template exists; ≥1 digest authored.
5. Unified query hierarchy doc published at `homelab-playbook/wiki/architecture/query-hierarchy.md`.
6. GitNexus + Graphiti exit-ramp docs both published.
7. Product-level KPI scorecard: ≥4-of-6 KPIs green AND G-Latency clean AND G-Rollback validated (E4-S08 evidence carried).
8. Phase-4 retro authored; ADR-014 SHOULD/MUST split validated retrospectively; backlog tickets for deferred work + quarterly wiki review.
9. (Path B alternative) FR-LLM-007 invoked; backlog ticket for LiteLLM bridge documented; non-LiteLLM stories all complete.

### 7.6 Sprint Decision Gate (product-level RELEASE)

**This is the binding gate per PRD §11 + brief §6.**

- 4-of-6 KPIs green AND G-Latency clean AND G-Rollback validated → **PRODUCT RELEASE.**
- If 4-of-6 KPI fails → migrate-or-revert decision per brief §4.3; FR-DEP-007 rollback exercised on failing tier.
- If G-Latency regressed → investigate; if irreducible, stack does NOT promote off ct-dev-homelab.
- If G-Rollback not validated → stack does NOT promote off ct-dev-homelab (brief §6 hard gate).

### 7.7 Demo / Review Artifacts

- LiteLLM bridge config diff (env vars before/after) + 50-fact validation result table.
- Observability digest markdown.
- Query hierarchy doc.
- Exit-ramp docs.
- Product-level KPI scorecard.
- Phase-4 retro markdown.

---

## 8. Sprint Velocity Tracking Plan

The single biggest unknown is the **ideal-day:wall-clock multiplier**. The plan assumes ~1.7×. Sprint 1 is the calibration sprint.

**Calibration procedure:**

1. **At end of S1:** Record actual wall-clock days per story (D1=actual hours/3) vs ideal-day estimates from epics.md §3.8.
2. **Compute:** `actual_multiplier = sum(actual_wc_days) / sum(ideal_days)`. E1's ideal sum is 7d.
3. **If `actual_multiplier > 2.0`:** sprints S2-S5 must descope. Targets: defer COULDs first, then SHOULDs per ADR-014. The `cypher-replay.sh` and `down -v` Mandatory Fixes are the only items that cannot defer.
4. **If `actual_multiplier ≤ 1.5`:** sprints can absorb additional work; consider pulling forward 1-2 deferred items per sprint.
5. **If `1.5 < actual_multiplier ≤ 2.0`:** plan holds; track per-sprint and re-calibrate at end of S2 + S3.

**Tracking artifact:** at end of each sprint, append a one-row entry to `homelab-playbook/_bmad-output/planning-artifacts/products/context-stack/velocity-log.md`:

```
| Sprint | Ideal-days planned | Wall-clock-days actual | Multiplier | Notes |
|---|---|---|---|---|
| S1 | 7.0 | TBD | TBD | E1-S06 Hermes Jinja was the slowest |
```

Five rows total at product close. Drives the next product's capacity model (compounding learning per ADR-014 spirit).

---

## 9. Cross-Sprint Risks

Carried from `architecture.md` §11, ADR-014, and `e2e-deployment.md` §3:

| ID | Risk | Affects sprints | Mitigation owner |
|---|---|---|---|
| AR1 | GitNexus footprint > 500 MB | S2 | E2-S02 24h sample; exit-ramp to CodeGraphContext if breached |
| AR2 | LiteLLM Responses API breakage | S5 | E4-S06 validation gate; FR-LLM-007 defer |
| AR3 | OpenAI Usage API consistency lag | S3-S5 | 30-min cron cadence; documented overshoot acceptable |
| AR4 / R1 | GitNexus / FalkorDB / Graphiti single-maintainer abandonment | S2-S5 (continuous) | NFR-SUPP-001 ≥3mo activity check at adoption; export wrappers from day 1 (E2-S07, E3-S07) |
| AR5 | Graphiti OpenAIGenericClient bugs | S5 | E4-S05 spike runs first; side-by-side proxy alt |
| AR6 | Wiki content drift | S4-S5 + post-product | `wiki-lint.sh` warn; quarterly review backlog ticket |
| AR7 | Single-PR decommission wide surface | S1 | Grep + Hermes verify gates (E1-S08); per-commit revertability |
| AR8 | Default group_id discipline | S3 (continuous after) | E3-S05 explicit verify; CLAUDE.md doc (E3-S03) |
| **Sprint overflow** | **E3 + E4 estimated tight; operator under-estimates side-project life-friction** | **S3, S4** | **Velocity calibration at end of S1 + S2 (§8); aggressive SHOULD trim if multiplier > 2.0** |
| Operator burnout | 10-week marathon at 3 hrs/day | S4-S5 | Slack day in each sprint plan; permission to spill 1-2 days at S5 retro |

---

## 10. Mandatory Fixes Schedule (from readiness-check.md §Mandatory Fixes)

| Fix | Source | Affects | Lands in | Story |
|---|---|---|---|---|
| **#1** Author `cypher-replay.sh` companion to `cypher-export.sh` | readiness-check.md F2 | E3-S07 / D1 disaster drill | **S2 (prep)** + **S3 (commit + AC11/12)** | S2: S3-prep authoring; S3: amend E3-S07 |
| **#2** Guard `docker compose down -v` in rollback procedures | readiness-check.md §3.1 + §5.3 of e2e-deployment.md | E4-S07 rollback playbook + E4-S08 drill | **S3 (prep)** + **S4 (commit + AC enforce)** | S3: S4-prep spec; S4: amend E4-S07 |

Both small (≤0.5d each); both queued in the sprint *before* they're needed. Neither blocks Sprint 1.

---

## 11. Recommended Improvements Schedule (from readiness-check.md §Recommended Improvements, non-blocking)

| # | Improvement | Best sprint | Cost |
|---|---|---|---|
| 1 | Inline rubric tightening for the 6 vague ACs (E3-S09, E4-S02, S08, S09, S11, S12) | **S2 retro authors a small "rubric pin" PR**; lands before S3 | ~0.25d |
| 2 | Add explicit AC for NFR-PERF-006 (`add_episode` < 5s) + NFR-PRIV-002 (embeddings boundary doc + tcpdump audit) | **S2** (covers NFR-PRIV-002 in E2-S05) + **S3** (covers NFR-PERF-006 at E3-S06) | ~0.25d (incremental) |
| 3 | Master "wiki integrity gate" AC at E4-S11 (lint once across all 4 weeks of contributions) | **S5** (E4-S11 amendment) | ~0.1d |
| 4 | Promote `last_reviewed: ≤6mo` enforcement to lint-fail | **Post-product backlog** (seeds aren't 6mo old until ~2027) | Future |
| 5 | Document FR-LLM-007 deferral path explicitly in epics §6.4 | **S4 (during prep for S5)** | ~0.1d |

Total recommended-improvements work: ~0.6 days, distributed across 3 sprints. Each fits within sprint slack.

---

## 12. Capacity Buffer / Slack Time

Honest accounting — buffer = (10 wall-clock days) − (planned story wc-days) − (1d kickoff+retro overhead):

| Sprint | Planned wc-days | Overhead | Available buffer | Risk level |
|---|---|---|---|---|
| **S1** | 12.6 | 1 | -3.6 (negative — relies on parallelism / quick stories landing same day) | MEDIUM (E1-S06 risky) |
| **S2** | 12.7 | 1 | -3.7 | MEDIUM (E2-S06 5 smoke tests heavy) |
| **S3** | 17 | 1 | **-8** (overflow) | **HIGH** — likely 1-2d slip into S4 |
| **S4** | 14.4 | 1 | -5.4 | **HIGH** — deploy + rollback drill is unforgiving |
| **S5** | 8.9 (Path A) / 8.5 (Path B) | 1 | +0.1 / +0.5 | LOW |

**Honest read:** the buffer is fragile across the board (S5 is the only comfortable one). The 1.7× multiplier assumes ~3 hrs/day; if a week has a lot of life-friction (a long ops day, a sick kid, a holiday), the multiplier blows out. **Operator is encouraged to:**

1. **Treat the wc-day estimates as 60th-percentile, not median.** When budgeting calendar time, add 20%.
2. **Take buffer seriously.** Do NOT pull forward backlog work into the buffer days — they exist for slip absorption.
3. **Re-baseline at S1 retro.** If S1's actual multiplier is > 1.85, immediately replan S2-S5 with reduced scope.

If the operator needs more compression (e.g., wants 4 sprints not 5), the only safe lever is:

- **Defer LiteLLM entirely (FR-LLM-007).** S5 collapses into the back half of an extended S4. ~5 days saved. Result: 4-sprint product with explicit "Phase 4 deferred to backlog" close-out.

This is the lever the PRD already permits.

---

## 13. Communications and Cadence

**Daily (within sprint):**

- Maintain task list via TodoWrite in the active Claude Code session.
- Commits land on `feat/context-stack-sprint-N-<slug>` branches; one PR per story or per epic-commit-group.

**Weekly:**

- 1-page progress note authored at `homelab-playbook/_bmad-output/planning-artifacts/products/context-stack/sprint-N/week-M-progress.md` (or in-line in the sprint retro draft). Captures: planned vs done, KPI samples, blockers, scope changes.

**Sprint boundary:**

- **Mini-retro** authored as a markdown file at `homelab-playbook/_bmad-output/planning-artifacts/products/context-stack/sprint-N/retro.md`.
- One-line summary committed to project memory (auto-memory or OMEGA-equivalent — there is no OMEGA after Sprint 1, so use `~/.claude/projects/.../memory/project_context_stack_sprint_log.md` as the per-product memory file).
- Velocity row appended to `velocity-log.md` (§8).

**Product retro (S5 D49-D50):**

- Phase-4 retro from E4-S12 doubles as the product close-out.
- Lessons feed forward to `feedback_*.md` auto-memory entries and the next product's brief.

**No daily standups, no async-team rituals — single-operator product.** Communication is operator-to-future-operator (memory) and operator-to-PR-self (review discipline).

---

## 14. Sprint 1 Kickoff Checklist

Day 1 of Sprint 1, ensure all of the following are true *before* writing any code:

1. ☐ Working tree clean: `git -C ~/workspace/homelab status` reports nothing to commit on each of the three sibling repos.
2. ☐ Branch created: `git -C ~/workspace/homelab/homelab-playbook checkout -b decommission/context-stack-phase-1` (or equivalent on the relevant repo for each commit).
3. ☐ Pre-decommission baseline captured: run `ansible-playbook` against `ct-dev-homelab` with the current Hermes role and `verify.yml` exits 0. **Save the output as evidence** under `homelab-playbook/docs/decommission/baseline-pre-decommission.txt`.
4. ☐ ct-dev-homelab reachable: `ansible -i inventory ct-dev-homelab -m ping` succeeds.
5. ☐ `~/.claude/settings.json` backed up to `~/.claude/settings.json.bak.<TS>` (rollback insurance).
6. ☐ `~/.mempalace/` listed in case it has unexpected files (FR-DEC-012 evidence pre-deletion).
7. ☐ `pip list | grep omega-memory` confirms current install version (rollback target).
8. ☐ Hermes Jinja templates identified: `config.yaml.j2`, `defaults/main.yml`, `verify.yml` paths confirmed.
9. ☐ ADR-010 re-read: 8-commit sequence and **merge-commit-not-squash** rule fresh in mind.
10. ☐ Sprint backlog (this document §3.2) opened in TodoWrite or equivalent task tracker; first task = E1-S01.
11. ☐ Operator life-context calibration: realistic estimate of how many of the next 10 working days will hit the 3-hr target. Adjust expectations now, not at retro.

Sprint 1 GO criterion (from readiness-check.md §Sprint 1 Go/No-Go) is unchanged: **GO** if all 11 above tick.

---

**End of sprint-plan.md — handoff to Phase 7 (product README + handoff to user).**
