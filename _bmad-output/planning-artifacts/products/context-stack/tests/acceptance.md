---
type: acceptance-tests
product: context-stack
version: 1.0.0-draft
status: draft
date: 2026-04-25
prd_ref: prd.md
epics_ref: epics.md
total_stories: 38
total_acceptance_criteria: 325
---

# Context Stack — Acceptance Test Suite

## 1. Overview

This document aggregates every acceptance criterion (AC) authored in the 38 INVEST-shaped stories under `stories/E*-S*.md`, validates that each is observable, cross-references each to the FRs and NFRs it verifies, and audits the suite against the PRD's 73 FRs and 25 NFRs.

### 1.1 Counts

| Epic | Stories | ACs |
|---|---|---|
| **E1 Decommission** | 9 | 58 |
| **E2 GitNexus Pilot** | 8 | 61 |
| **E3 Graphiti Pilot** | 9 | 76 |
| **E4 Production Hardening + Wiki + LiteLLM** | 12 | 130 |
| **Total** | **38** | **325** |

(Brief estimate was ~328; actual count after re-tally is 325. The delta is within rounding noise — some stories collapsed adjacent verifications into one AC, others split.)

### 1.2 Definition of "observable" (the gating standard)

An AC is observable iff at least one of:

- **cmd** — exact runnable command(s) producing a checkable exit code, stdout pattern, or measurable wall-clock value
- **filesystem** — `test -f`, `test -d`, `stat`, `ls`, `du`, `wc` style filesystem state check
- **log** — grep/jq pattern against a captured log (`/var/log/...`, `journalctl -t ...`, `~/.claude/logs/...`, `/tmp/*.log`)
- **git** — `git log`, `git tag`, `git diff`, `git check-ignore` etc. against repo state
- **api** — HTTP call (curl) against a documented endpoint with checkable response
- **session** — Claude Code session transcript inspection (a `script -q` capture is the artifact)
- **infra** — process state (`pgrep`, `docker compose ps`, `claude mcp list`, `crontab -l`, `ss -tlnp`)

ACs that lack any of the above are flagged in §5.1 (vague / non-observable).

### 1.3 Test execution model

**Mixed**, with a strong bias toward scripted:

- **E1**: scripted (Ansible playbook + grep/pgrep gates) with one operator-driven Hermes verify run on `ct-dev-homelab`
- **E2**: scripted install + 5-scenario runbook + one 24h passive sampler
- **E3**: scripted compose + 5-scenario runbook + one operator-driven restore drill
- **E4**: scripted Ansible + scripted smoke tests + 4 weekly operator-authored digests + 1 operator-authored retro

K6 (subjective uplift) and the operator narrative paragraphs in weekly digests / retro are inherently manual; everything else is reproducible from a clean dev workstation + ct-dev-homelab + ct-ai-01.

---

## 2. AC Index by Epic

Status legend: `pending` (not yet executed), `pass`, `fail`, `deferred`. All ACs ship as `pending`. Signal type is the dominant kind for that AC (most are `cmd` or `cmd+session`).

### 2.1 Epic E1 (Decommission)

| Story | AC | One-line description | FRs verified | Signal | Status |
|---|---|---|---|---|---|
| E1-S01 | AC1 | Four OMEGA hook entries deactivated in settings.json (not deleted) | FR-DEC-007 | cmd | pending |
| E1-S01 | AC2 | One full Claude session runs silent with hooks disabled | FR-DEC-007 | session+log | pending |
| E1-S01 | AC3 | OMEGA daemon process check (informational) | FR-DEC-007 | infra | pending |
| E1-S01 | AC4 | Commit message conforms to ADR-010 format | FR-DEC-007 | git | pending |
| E1-S02 | AC1 | All four OMEGA entries fully removed from settings.json | FR-DEC-007 | cmd | pending |
| E1-S02 | AC2 | settings.json valid JSON; Claude Code starts cleanly | FR-DEC-007 | cmd+session | pending |
| E1-S02 | AC3 | Hook scripts on disk still present (deferred to E1-S06) | FR-DEC-007 | filesystem | pending |
| E1-S02 | AC4 | Commit message conforms to ADR-010 format | FR-DEC-007 | git | pending |
| E1-S03 | AC1 | omega-memory pipx package uninstalled | FR-DEC-008 | cmd | pending |
| E1-S03 | AC2 | OMEGA daemon process killed; pgrep clean | FR-DEC-008 | infra | pending |
| E1-S03 | AC3 | ai-dev-omega-memory Ansible role removed | FR-DEC-008 | filesystem+git | pending |
| E1-S03 | AC4 | dev_hosts group_vars file removed | FR-DEP-009 | filesystem | pending |
| E1-S03 | AC5 | deploy-ai-dev-container.yml drops role + tag refs | FR-DEP-009 | cmd | pending |
| E1-S03 | AC6 | Idempotent re-run safety (--check --diff clean) | FR-DEP-001 | cmd | pending |
| E1-S03 | AC7 | Commit message conforms to ADR-010 format | FR-DEC-008 | git | pending |
| E1-S04 | AC1 | ~/.mempalace/ deleted; pgrep clean | FR-DEC-001 | filesystem+infra | pending |
| E1-S04 | AC2 | Empty-store SQLite evidence captured (FR-DEC-012 record) | FR-DEC-012 | cmd | pending |
| E1-S04 | AC3 | ai-dev-mempalace Ansible role removed in full | FR-DEC-002 | filesystem+cmd | pending |
| E1-S04 | AC4 | dev_hosts MemPalace group_vars file removed | FR-DEC-002 | filesystem | pending |
| E1-S04 | AC5 | Three Hermes mempalace-* skill dirs removed | FR-DEC-003 | cmd | pending |
| E1-S04 | AC6 | deploy-ai-dev-container.yml drops mempalace role include | FR-DEP-001 | cmd | pending |
| E1-S04 | AC7 | Commit message conforms to ADR-010 format | FR-DEC-001..003 | git | pending |
| E1-S05 | AC1 | wire-mempalace.yml task file deleted | FR-DEC-004 | filesystem | pending |
| E1-S05 | AC2 | knowledge-query orchestrator skill dir removed | FR-DEC-006 | cmd | pending |
| E1-S05 | AC3 | Hermes tasks/main.yml does not include wire-mempalace | FR-DEC-004 | cmd | pending |
| E1-S05 | AC4 | No surviving wire-mempalace/knowledge-query refs in repo | FR-DEC-004, FR-DEC-006 | cmd | pending |
| E1-S05 | AC5 | Hermes role dry-run on ct-dev-homelab does not error | FR-DEP-001 | cmd | pending |
| E1-S05 | AC6 | Commit message conforms to ADR-010 format | FR-DEC-004, FR-DEC-006 | git | pending |
| E1-S06 | AC1 | config.yaml.j2 mempalace MCP block + L273 conditional removed | FR-DEC-005 | cmd | pending |
| E1-S06 | AC2 | defaults/main.yml mempalace variables removed | FR-DEC-005 | cmd | pending |
| E1-S06 | AC3 | verify.yml Story-6.4 block + L125 task name updated | FR-DEC-005 | cmd | pending |
| E1-S06 | AC4 | Whole Hermes role is mempalace-free | FR-DEC-005 | cmd | pending |
| E1-S06 | AC5 | Templates render successfully against current vars | FR-DEC-005 | cmd | pending |
| E1-S06 | AC6 | Hermes role syntax-check + ansible-lint pass | FR-DEC-005 | cmd | pending |
| E1-S06 | AC7 | Commit message + diff scope conform to ADR-010 | FR-DEC-005 | git | pending |
| E1-S07 | AC1 | Decommission doc exists at canonical path; ≥100 lines | FR-DEC-012 | filesystem | pending |
| E1-S07 | AC2 | Doc enumerates every action across commits 1–6 | FR-DEC-001..008 | cmd | pending |
| E1-S07 | AC3 | FR-DEC-012 no-data-migration record captured | FR-DEC-012 | cmd | pending |
| E1-S07 | AC4 | Rollback path documented inline (FR-DEP-007) | FR-DEP-007 | cmd | pending |
| E1-S07 | AC5 | MEMORY.md auto-memory continuity statement | FR-DEC-012 | cmd | pending |
| E1-S07 | AC6 | Cross-references to FRs and ADRs | FR-DEC-001..012 | cmd | pending |
| E1-S07 | AC7 | Commit message conforms to ADR-010 format | FR-DEC-012 | git | pending |
| E1-S08 | AC1 | Hermes verify.yml exits 0 on ct-dev-homelab | FR-DEC-011 | cmd | pending |
| E1-S08 | AC2 | Repo-wide grep gate returns 0 (FR-DEC-009) | FR-DEC-009 | cmd | pending |
| E1-S08 | AC3 | Workstation pgrep returns 0 (FR-DEC-010 part 1) | FR-DEC-010 | infra | pending |
| E1-S08 | AC4 | ct-dev-homelab pgrep returns 0 (FR-DEC-010 part 2) | FR-DEC-010 | infra | pending |
| E1-S08 | AC5 | Verify-run output appended to decommission doc | FR-DEC-011, FR-DEC-012 | cmd | pending |
| E1-S08 | AC6 | MEMORY.md auto-memory continuity verified | FR-DEC-012 | session | pending |
| E1-S08 | AC7 | Commit message conforms to ADR-010 format | FR-DEC-009..011 | git | pending |
| E1-S09 | AC1 | Merge commit tagged phase-1-decommission-complete | FR-DEC-009, FR-DEP-007 | git | pending |
| E1-S09 | AC2 | pre-push hook script exists and is executable | FR-DEC-009 | filesystem | pending |
| E1-S09 | AC3 | pre-push hook blocks pushes that reintroduce mempalace/omega | FR-DEC-009 | cmd+git | pending |
| E1-S09 | AC4 | pre-push hook respects FR-DEC-009 exclusions | FR-DEC-009 | cmd+git | pending |
| E1-S09 | AC5 | Hook uses canonical FR-DEC-009 grep incantation | FR-DEC-009 | cmd | pending |
| E1-S09 | AC6 | --no-verify override path documented | FR-DEC-009 | cmd | pending |
| E1-S09 | AC7 | Hook downgrade-to-CI plan documented | FR-DEC-009 | cmd | pending |
| E1-S09 | AC8 | Tag is reachable as rollback target per ADR-010 | FR-DEP-007 | git | pending |
| E1-S09 | AC9 | Commit message conforms to ADR-010 format | FR-DEC-009 | git | pending |

### 2.2 Epic E2 (GitNexus Pilot)

| Story | AC | One-line description | FRs/NFRs verified | Signal | Status |
|---|---|---|---|---|---|
| E2-S01 | AC1 | Pre-flight clean baseline (no OMEGA, no gitnexus on PATH) | FR-CG-001 | cmd | pending |
| E2-S01 | AC2 | Supply-chain verification (NFR-SUPP-001 + typosquat guard) | NFR-SUPP-001 | cmd+api | pending |
| E2-S01 | AC3 | Pinned global install succeeds (gitnexus@1.6.3) | FR-CG-001 | cmd | pending |
| E2-S01 | AC4 | CLI surface available (cypher/impact/context/reindex) | FR-CG-001 | cmd | pending |
| E2-S01 | AC5 | Install captured in repeatable artifact (FR-DEP-003) | FR-DEP-003 | filesystem+cmd | pending |
| E2-S01 | AC6 | Telemetry/network audit at install time (no outbound TCP) | FR-CG-002, FR-CG-012 | cmd | pending |
| E2-S02 | AC1 | Daemon starts and is identifiable in ps | NFR-FOOTPRINT-002 | infra | pending |
| E2-S02 | AC2 | Initial RSS sample < 500 MB | NFR-FOOTPRINT-002 | cmd | pending |
| E2-S02 | AC3 | Sustained 24h RSS sample < 500 MB max, < 400 MB p95 | NFR-FOOTPRINT-002 | cmd | pending |
| E2-S02 | AC4 | Disk footprint sample < 1 GB | NFR-FOOTPRINT-003 | cmd | pending |
| E2-S02 | AC5 | Privacy/network audit during reindex (no LLM endpoints) | FR-CG-002, FR-CG-012, NFR-PRIV-001 | cmd | pending |
| E2-S02 | AC6 | AR1 closure decision recorded in baseline note | NFR-FOOTPRINT-002 | cmd | pending |
| E2-S03 | AC1 | Pre-registration baseline captured (mcp list backup) | FR-CG-001 | cmd | pending |
| E2-S03 | AC2 | npx gitnexus setup runs cleanly and registers MCP | FR-CG-001 | cmd | pending |
| E2-S03 | AC3 | Claude Code discovers gitnexus as healthy | FR-CG-001 | infra | pending |
| E2-S03 | AC4 | Tool surface advertised to model (cypher/impact/context/reindex) | FR-CG-001 | session | pending |
| E2-S03 | AC5 | Stdio transport verified (no listening port) | FR-CG-001 | infra | pending |
| E2-S03 | AC6 | Graceful-degradation pre-flight (NFR-AVAIL-001) | NFR-AVAIL-001, FR-CG-011 | session+infra | pending |
| E2-S03 | AC7 | Registration captured in install script (idempotent) | FR-DEP-003 | cmd | pending |
| E2-S04 | AC1 | Hook entries present + well-formed in settings.json | FR-CG-004 | cmd | pending |
| E2-S04 | AC2 | PreToolUse hook fires before tool calls | FR-CG-004 | log | pending |
| E2-S04 | AC3 | PostToolUse-on-commit hook fires on git commit | FR-CG-005 | log | pending |
| E2-S04 | AC4 | No-filter default per FR-CG-005 | FR-CG-005 | cmd | pending |
| E2-S04 | AC5 | Session-start latency budget held (< 1 s overhead) | NFR-PERF-001 | cmd | pending |
| E2-S04 | AC6 | Hook commands point to pinned binary, not @latest | FR-CG-001 | cmd | pending |
| E2-S04 | AC7 | Hook removal reversible (round-trip < 60 s) | NFR-MAINT-001, FR-DEP-007 | cmd | pending |
| E2-S05 | AC1 | Parent-folder topology configured for ~/workspace/homelab/ | FR-CG-003 | cmd | pending |
| E2-S05 | AC2 | Full reindex completes successfully | NFR-PERF-005 | cmd | pending |
| E2-S05 | AC3 | Cypher query returns nodes from all 3 sub-repos | FR-CG-003 | cmd | pending |
| E2-S05 | AC4 | Cross-repo edge exists end-to-end | FR-CG-003, FR-CG-008 | cmd | pending |
| E2-S05 | AC5 | Network audit during reindex (zero LLM endpoints) | FR-CG-002, FR-CG-012, NFR-PRIV-001 | cmd | pending |
| E2-S05 | AC6 | Hook-driven incremental reindex respects topology (< 30 s) | FR-CG-006, NFR-PERF-004 | cmd | pending |
| E2-S05 | AC7 | Topology config captured for repeatability | FR-DEP-003 | cmd | pending |
| E2-S06 | AC1 | Smoke-test runbook committed (5 scenarios) | FR-CG-009 | filesystem | pending |
| E2-S06 | AC2 | Scenario 1: call-graph traversal (< 500 ms p95) | FR-CG-009, NFR-PERF-002 | cmd | pending |
| E2-S06 | AC3 | Scenario 2: cross-repo dependency edge | FR-CG-008 | cmd+session | pending |
| E2-S06 | AC4 | Scenario 3: dependency walk via context tool (< 5 s) | FR-CG-009, NFR-PERF-002 | session | pending |
| E2-S06 | AC5 | Scenario 4: auto-reindex responsiveness (≥ 9/10 ≤ 30 s; cold ≤ 60 s) | FR-CG-006, FR-CG-007, NFR-PERF-004, NFR-PERF-005 | cmd | pending |
| E2-S06 | AC6 | Scenario 5a: sustained-load 1h footprint (RSS < 500 MB) | NFR-FOOTPRINT-002, NFR-AVAIL-001 | cmd | pending |
| E2-S06 | AC7 | Scenario 5b: graceful-degradation drill (no > 3s hang) | FR-CG-011, NFR-AVAIL-001 | cmd+session | pending |
| E2-S06 | AC8 | Runbook is source of truth for E2-S08 KPI gate | FR-CG-009 | cmd | pending |
| E2-S07 | AC1 | gitnexus-export.sh script committed, shellcheck-clean | FR-CG-010 | cmd | pending |
| E2-S07 | AC2 | Default output path matches ADR-012 | FR-CG-010 | cmd | pending |
| E2-S07 | AC3 | Output is valid NDJSON conforming to ADR-012 schema | FR-CG-010, NFR-PORT-001 | cmd | pending |
| E2-S07 | AC4 | Export contains nodes from all 3 sub-repos | FR-CG-003, FR-CG-010 | cmd | pending |
| E2-S07 | AC5 | Export contains ≥ 1 cross-repo edge | FR-CG-010 | cmd | pending |
| E2-S07 | AC6 | Output size constraints (< 50 MB; 100-100k lines) | FR-CG-010 | cmd | pending |
| E2-S07 | AC7 | Script handles GitNexus unavailable cleanly (atomic write) | FR-CG-010 | cmd | pending |
| E2-S07 | AC8 | Replay-path documentation present (NFR-SUPP-002) | NFR-SUPP-002 | filesystem | pending |
| E2-S07 | AC9 | One snapshot committed as Phase 2 evidence | FR-CG-010 | git | pending |
| E2-S08 | AC1 | Scorecard template instantiated with 5 KPI rows | FR-CG-008 | filesystem | pending |
| E2-S08 | AC2 | Green-amber-red rubric defined per KPI (closes EQ2) | FR-CG-008 | cmd | pending |
| E2-S08 | AC3 | K1 measured on 3 representative cross-repo questions (≥ 5×) | FR-CG-008 | cmd | pending |
| E2-S08 | AC4 | K2 timings extracted from hook logs (≥ 9/10 ≤ 30 s) | FR-CG-006, NFR-PERF-004 | cmd | pending |
| E2-S08 | AC5 | K3 spend reconciled (GitNexus-attributable = $0.00) | FR-CG-012 | cmd | pending |
| E2-S08 | AC6 | K4 non-blank-artifact tally (≥ 90%) | FR-CG-009 | cmd | pending |
| E2-S08 | AC7 | K6 tally captured over 7-day window (≥ 14 rows) | FR-OBS-004 | cmd | pending |
| E2-S08 | AC8 | G-Latency check (NFR-PERF-001 < 1 s overhead) | NFR-PERF-001 | cmd | pending |
| E2-S08 | AC9 | AR1 footprint check final (RSS ≤ 500 MB) | NFR-FOOTPRINT-002 | cmd | pending |
| E2-S08 | AC10 | Decision recorded (PROCEED/PROCEED-WITH-FOLLOWUP/MIGRATE/REVERT) | FR-CG-008 | filesystem | pending |
| E2-S08 | AC11 | Sprint 2 retro entry written | FR-OBS-004 | filesystem | pending |

### 2.3 Epic E3 (Graphiti Pilot)

| Story | AC | One-line description | FRs/NFRs verified | Signal | Status |
|---|---|---|---|---|---|
| E3-S01 | AC1 | /srv/graphiti/ directory layout exists with correct ownership | FR-MEM-001 | cmd | pending |
| E3-S01 | AC2 | docker-compose.yml committed with pinned tags (no :latest) | FR-DEP-002, FR-DEP-010 | cmd | pending |
| E3-S01 | AC3 | .env exists at /srv/graphiti/.env mode 600, required vars | FR-DEP-002, FR-DEP-008 | cmd | pending |
| E3-S01 | AC4 | Both containers come up healthy | FR-MEM-001 | cmd | pending |
| E3-S01 | AC5 | FalkorDB responds to PING | FR-MEM-001 | cmd | pending |
| E3-S01 | AC6 | Persistent volume survives container recreate | FR-MEM-001 | cmd | pending |
| E3-S01 | AC7 | Pinned tags surfaced in install runbook | FR-DEP-010 | cmd | pending |
| E3-S02 | AC1 | Compose port bind flipped to 0.0.0.0:8000 on graphiti-mcp | FR-MEM-002, FR-MEM-003 | cmd | pending |
| E3-S02 | AC2 | MCP /health returns OK from localhost on ct-ai-01 | FR-MEM-002 | api | pending |
| E3-S02 | AC3 | MCP tools/list advertises full Graphiti tool surface | FR-MEM-009 | api | pending |
| E3-S02 | AC4 | Endpoint reachable from workstation over Tailscale | FR-MEM-003 | api | pending |
| E3-S02 | AC5 | Claude Code MCP registration succeeds | FR-MEM-002 | infra | pending |
| E3-S02 | AC6 | Tool surface visible inside Claude Code session | FR-MEM-009 | session | pending |
| E3-S02 | AC7 | No outbound 8000 from non-tailnet hosts | FR-MEM-003, NFR-PRIV-003 | api | pending |
| E3-S03 | AC1 | Memory (Graphiti) section exists in ~/.claude/CLAUDE.md | FR-MEM-010 | cmd | pending |
| E3-S03 | AC2 | Section enumerates read triggers (search_facts/search_nodes) | FR-MEM-010 | cmd | pending |
| E3-S03 | AC3 | Section enumerates write triggers (add_episode) | FR-MEM-010 | cmd | pending |
| E3-S03 | AC4 | group_id="tom-personal" called out as MANDATORY (closes AR8) | FR-MEM-005, FR-MEM-010 | cmd | pending |
| E3-S03 | AC5 | Tier-of-truth pointer present (ADR-013 cross-ref) | FR-MEM-010 | cmd | pending |
| E3-S03 | AC6 | Smoke-test: model invokes search_facts with group_id at session start | FR-MEM-005, FR-MEM-009 | session | pending |
| E3-S03 | AC7 | No conflict with auto-memory loader | FR-MEM-010 | session | pending |
| E3-S04 | AC1 | .env carries 7 required model/throttle/telemetry vars | FR-MEM-004, FR-MEM-006, FR-MEM-011 | cmd | pending |
| E3-S04 | AC2 | .env mode is 600 after edit | FR-DEP-002, FR-DEP-008 | cmd | pending |
| E3-S04 | AC3 | Container picks up new env on recreate | FR-MEM-004, FR-MEM-006, FR-MEM-011 | cmd | pending |
| E3-S04 | AC4 | First add_episode round-trip uses gpt-4o-mini | FR-MEM-004 | session+api | pending |
| E3-S04 | AC5 | Telemetry endpoint not reached | FR-MEM-011 | log | pending |
| E3-S04 | AC6 | INFO-level logging captured to host | FR-OBS-003 | log | pending |
| E3-S04 | AC7 | Monthly rotation policy documented + cron stub | FR-OBS-003 | cmd | pending |
| E3-S04 | AC8 | Rate-limit headroom verified (zero 429s on burst) | FR-MEM-006 | log | pending |
| E3-S05 | AC1 | Probe write via Claude Code returns a UUID | FR-MEM-009 | session | pending |
| E3-S05 | AC2 | FalkorDB Browser confirms node creation | FR-MEM-005 | api | pending |
| E3-S05 | AC3 | search_facts in fresh session returns the fact | FR-MEM-009 | session | pending |
| E3-S05 | AC4 | Default-group experiment: explicit group_id lands in tom-personal | FR-MEM-005 | cmd | pending |
| E3-S05 | AC5 | Default-group experiment: omitted group_id reveals AR8 path | FR-MEM-005 | cmd | pending |
| E3-S05 | AC6 | Search across both groups isolates writes | FR-MEM-005 | cmd | pending |
| E3-S05 | AC7 | get_status reports healthy DB connectivity | FR-MEM-009 | session | pending |
| E3-S05 | AC8 | AR8 conclusion encoded in CLAUDE.md emphasis | FR-MEM-010 | cmd | pending |
| E3-S06 | AC1 | Test 3 (bi-temporal validity) passes — supersession retained | FR-MEM-009 | session+cmd | pending |
| E3-S06 | AC2 | Test 4 (embedding similarity) passes | FR-MEM-009 | session | pending |
| E3-S06 | AC3 | Test 5 (auto entity-extraction) passes | FR-MEM-009 | session+log | pending |
| E3-S06 | AC4 | Multi-episode supersession check (Cypher direct) | FR-MEM-009 | cmd | pending |
| E3-S06 | AC5 | Graceful degradation — FalkorDB stopped, no > 3s hang | FR-MEM-013, NFR-AVAIL-002 | cmd+session | pending |
| E3-S06 | AC6 | Recovery from degraded state — restart, recall works again | FR-MEM-013 | api+session | pending |
| E3-S06 | AC7 | All 5 smoke tests captured as runnable script | FR-MEM-009 | cmd | pending |
| E3-S06 | AC8 | docker compose logs show zero JSONDecodeError across suite | FR-MEM-004 | log | pending |
| E3-S07 | AC1 | AOF is on by default (verify, don't change) | FR-MEM-014 | cmd | pending |
| E3-S07 | AC2 | cron entry installed at /etc/cron.d/graphiti-backup | FR-MEM-014 | cmd | pending |
| E3-S07 | AC3 | cypher-export.sh committed and tested manually | FR-MEM-012 | cmd | pending |
| E3-S07 | AC4 | Monthly Cypher export cron entry added | FR-MEM-012, FR-MEM-014 | cmd | pending |
| E3-S07 | AC5 | First daily AOF rewrite runs successfully | FR-MEM-014 | log | pending |
| E3-S07 | AC6 | First weekly BGSAVE runs successfully | FR-MEM-014 | filesystem | pending |
| E3-S07 | AC7 | First monthly Cypher export runs and writes JSON | FR-MEM-012, NFR-PORT-002 | cmd | pending |
| E3-S07 | AC8 | ZFS-snapshot pattern coverage of /srv/graphiti/data documented | FR-MEM-014 | cmd | pending |
| E3-S07 | AC9 | Combined disk footprint check (< 5 GB) | NFR-FOOTPRINT-003 | cmd | pending |
| E3-S07 | AC10 | Log rotation policy applies to /var/log/graphiti-backup.log | FR-OBS-003 | cmd | pending |
| E3-S08 | AC1 | Pre-drill state captured — known facts queryable | FR-MEM-014 | cmd | pending |
| E3-S08 | AC2 | Backup files exist and are recent | FR-MEM-014 | cmd | pending |
| E3-S08 | AC3 | Containers stopped — start-of-rollback clock starts | FR-DEP-007 | cmd | pending |
| E3-S08 | AC4 | Data directory wiped (failure simulation) | FR-MEM-014 | cmd | pending |
| E3-S08 | AC5 | Restore from backup files | FR-MEM-014 | cmd | pending |
| E3-S08 | AC6 | Stack restarts and recall returns install marker | FR-MEM-014 | cmd+session | pending |
| E3-S08 | AC7 | End-of-rollback clock — total drill < 10 min | FR-DEP-007, NFR-MAINT-001 | cmd | pending |
| E3-S08 | AC8 | Smoke tests 1-3 from runbook §7 pass against restored data | FR-MEM-014 | cmd | pending |
| E3-S08 | AC9 | Restore drill recorded in operator journal | FR-MEM-014, FR-OBS-004 | filesystem | pending |
| E3-S08 | AC10 | Recovery path validated if drill fails | FR-MEM-014 | cmd | pending |
| E3-S09 | AC1 | K1 (token reduction) measured on 3 cross-repo questions | FR-CG-008 | cmd | pending |
| E3-S09 | AC2 | K2 (re-index timing) — informational only | NFR-PERF-004 | cmd | pending |
| E3-S09 | AC3 | K3 (spend) — sum OpenAI + Anthropic, threshold $20/mo | NFR-COST-001, NFR-COST-002 | cmd | pending |
| E3-S09 | AC4 | K4 (facts/week) ≥ 25 distinct facts captured | FR-MEM-008 | cmd | pending |
| E3-S09 | AC5 | K5 (first-shot recall) ≥ 50% on tagged retro queries | FR-MEM-007 | cmd | pending |
| E3-S09 | AC6 | K6 (subjective uplift) ≥ "noticeable" on retro | FR-OBS-004 | manual | pending |
| E3-S09 | AC7 | FalkorDB RAM < 200 MB at week-2 sample | FR-MEM-015, NFR-FOOTPRINT-001 | cmd | pending |
| E3-S09 | AC8 | GitNexus daemon RSS < 500 MB (cross-pilot check) | NFR-FOOTPRINT-002 | cmd | pending |
| E3-S09 | AC9 | Good-catch tally ≥ 3 over 2-week window | FR-OBS-005 | cmd | pending |
| E3-S09 | AC10 | Decision recorded in Sprint 3 retro | FR-OBS-004 | filesystem | pending |
| E3-S09 | AC11 | One-pager committed to repo | FR-OBS-004 | git | pending |

### 2.4 Epic E4 (Production Hardening)

| Story | AC | One-line description | FRs/NFRs verified | Signal | Status |
|---|---|---|---|---|---|
| E4-S01 | AC1 | Wiki tree skeleton at homelab-playbook/wiki/ with 5 categories | FR-WIKI-002, FR-WIKI-008 | cmd | pending |
| E4-S01 | AC2 | _schema.md documents ADR-006 frontmatter spec verbatim | FR-WIKI-002, FR-WIKI-003 | cmd | pending |
| E4-S01 | AC3 | index.md has three required sections | FR-WIKI-004 | cmd | pending |
| E4-S01 | AC4 | index.md total size < 5 KB at bootstrap | FR-WIKI-004 | cmd | pending |
| E4-S01 | AC5 | scripts/wiki-lint.sh committed; exits 0 on bootstrap tree | FR-WIKI-002 | cmd | pending |
| E4-S01 | AC6 | wiki-lint.sh enforces all 6 ADR-006 rules | FR-WIKI-002 | cmd | pending |
| E4-S01 | AC7 | _schema.md itself passes wiki-lint | FR-WIKI-002 | cmd | pending |
| E4-S01 | AC8 | .gitignore does NOT exclude any wiki path | FR-WIKI-008 | cmd | pending |
| E4-S01 | AC9 | Pre-commit hook wires wiki-lint.sh | FR-WIKI-002 | cmd+git | pending |
| E4-S02 | AC1 | Five seed entries authored, each conforming to ADR-006 schema | FR-WIKI-006, FR-DEP-005 | filesystem | pending |
| E4-S02 | AC2 | Each seed has all required ADR-006 frontmatter fields | FR-WIKI-006 | cmd | pending |
| E4-S02 | AC3 | Each seed has body sections in prescribed order | FR-WIKI-006 | cmd | pending |
| E4-S02 | AC4 | index.md regenerated to list 5 seeds; size < 5 KB | FR-WIKI-004 | cmd | pending |
| E4-S02 | AC5 | projects/ai-dev-context-stack.md is cross-link, not duplicate | FR-WIKI-010 | cmd | pending |
| E4-S02 | AC6 | Each seed carries accurate related_frs/related_adrs | FR-WIKI-006 | cmd | pending |
| E4-S02 | AC7 | Operator log ≥ 3 distinct sessions per seed (FR-WIKI-006 SHOULD) | FR-WIKI-006 | cmd | pending |
| E4-S02 | AC8 | No seed exceeds 4 KB body size | FR-WIKI-005 | cmd | pending |
| E4-S02 | AC9 | Each seed page passes slug-based cross-reference rule | FR-WIKI-002 | cmd | pending |
| E4-S03 | AC1 | Skill installed at ~/.claude/skills/wiki-query/ | FR-WIKI-001 | cmd | pending |
| E4-S03 | AC2 | SKILL.md frontmatter conforms to Claude Code skill spec | FR-WIKI-001, FR-WIKI-009 | cmd | pending |
| E4-S03 | AC3 | SKILL.md body specifies 4-step retrieval procedure | FR-WIKI-001, FR-WIKI-003 | cmd | pending |
| E4-S03 | AC4 | SKILL.md includes "wiki not initialised" fallback | FR-WIKI-009 | cmd | pending |
| E4-S03 | AC5 | Skill triggers on documented phrases (dry-run) | FR-WIKI-001 | session | pending |
| E4-S03 | AC6 | Skill triggers correctly across all 5 seed-coverage prompts | FR-WIKI-001, FR-WIKI-006 | session | pending |
| E4-S03 | AC7 | Wiki page-read latency ≤ 200 ms | FR-WIKI-005, NFR-PERF-003 | cmd | pending |
| E4-S03 | AC8 | Skill consumes zero retrieval tokens | FR-WIKI-005, FR-WIKI-009 | session | pending |
| E4-S03 | AC9 | Skill does not double-load on session start | FR-WIKI-009 | session | pending |
| E4-S03 | AC10 | Skill survives wiki tree relocation gracefully | FR-WIKI-009 | session | pending |
| E4-S04 | AC1 | cost-cap.sh installed mode 755 | FR-OBS-002 | cmd | pending |
| E4-S04 | AC2 | Script implements ADR-008 reference behavior verbatim | FR-OBS-002, NFR-COST-002 | cmd | pending |
| E4-S04 | AC3 | OPENAI_ADMIN_KEY in .env mode 600, not committed | FR-DEP-008 | cmd+git | pending |
| E4-S04 | AC4 | Cron entry */30 * * * * registered | FR-OBS-002 | cmd | pending |
| E4-S04 | AC5 | Smoke run: script executes cleanly under cap | FR-OBS-002 | cmd+log | pending |
| E4-S04 | AC6 | Synthetic breach: throttle fires when DAILY_CAP=0.01 | NFR-COST-002, FR-OBS-002 | cmd+log | pending |
| E4-S04 | AC7 | Auto-restore fires at next UTC day rollover | FR-OBS-002 | cmd+log | pending |
| E4-S04 | AC8 | Script idempotent — repeated invocations under cap are no-ops | FR-OBS-002 | cmd | pending |
| E4-S04 | AC9 | ntfy URL overridable via env, not hardcoded | FR-OBS-002 | cmd | pending |
| E4-S04 | AC10 | Script handles OpenAI Usage API failure gracefully | FR-OBS-002 | log | pending |
| E4-S05 | AC1 | hybrid_gemma_serving LiteLLM endpoint reachable from ct-ai-01 | FR-LLM-001 | api | pending |
| E4-S05 | AC2 | If AC1 fails, FR-LLM-007 deferral path executed cleanly | FR-LLM-007 | filesystem | pending |
| E4-S05 | AC3 | Reversible env change staged in /srv/graphiti/.env | FR-LLM-003, FR-LLM-008 | cmd | pending |
| E4-S05 | AC4 | Pre-change OpenAI API key preserved for embeddings | FR-LLM-004 | cmd | pending |
| E4-S05 | AC5 | Apply change and recreate graphiti-mcp container | FR-LLM-002 | cmd+log | pending |
| E4-S05 | AC6 | Smoke probe: single add_episode round-trips through LiteLLM | FR-LLM-001, FR-LLM-002 | session+log | pending |
| E4-S05 | AC7 | Embedding calls still target OpenAI (NOT LiteLLM) | FR-LLM-004 | cmd | pending |
| E4-S05 | AC8 | Single-env-var revert restores Phase 1-3 baseline | FR-LLM-008, NFR-MAINT-001 | cmd | pending |
| E4-S05 | AC9 | Vaulted .env Phase-4 variant committed for E4-S07 role | FR-DEP-008 | git | pending |
| E4-S05 | AC10 | Bridge state documented in wiki | FR-WIKI-008 | cmd | pending |
| E4-S06 | AC1 | 50-fact validation corpus authored and committed | FR-LLM-005 | filesystem | pending |
| E4-S06 | AC2 | Corpus distribution covers operator memory categories | FR-LLM-005 | cmd | pending |
| E4-S06 | AC3 | Validation harness exists and runs corpus through bridged Graphiti | FR-LLM-005 | cmd | pending |
| E4-S06 | AC4 | Pass rate computed; gate decision recorded | FR-LLM-005 | cmd | pending |
| E4-S06 | AC5 | If gate PASSES — bridge stays active, Phase 4 promotes | FR-LLM-005 | cmd | pending |
| E4-S06 | AC6 | If gate FAILS — auto-fallback fires (FR-LLM-006) | FR-LLM-006, NFR-AVAIL-003 | cmd+log | pending |
| E4-S06 | AC7 | If gate FAILS — backlog item documents recovery path | FR-LLM-006 | filesystem | pending |
| E4-S06 | AC8 | FR-LLM-008 reversibility re-exercised independently (≤ 60 s) | FR-LLM-008 | cmd | pending |
| E4-S06 | AC9 | Cost-neutrality 7-day window started (NFR-COST-003) | NFR-COST-003 | filesystem | pending |
| E4-S06 | AC10 | Validation harness idempotent — can be re-run | FR-LLM-005 | cmd | pending |
| E4-S06 | AC11 | Deferred-from-S05 path: AC1-AC10 not executed; story closes deferred | FR-LLM-007 | filesystem | pending |
| E4-S07 | AC1 | Role directory structure conforms to homelab conventions | FR-DEP-001 | cmd | pending |
| E4-S07 | AC2 | defaults/main.yml exposes overridable knobs | FR-DEP-001 | cmd | pending |
| E4-S07 | AC3 | tasks/main.yml decomposed into named sub-task files | FR-DEP-001 | cmd | pending |
| E4-S07 | AC4 | All secrets sourced from vault, never plaintext | FR-DEP-008 | git+cmd | pending |
| E4-S07 | AC5 | graphiti.env.j2 produces correct .env for both phase modes | FR-LLM-001..004, FR-DEP-002 | cmd | pending |
| E4-S07 | AC6 | cost-cap.sh.j2 installs E4-S04 verbatim | FR-OBS-002 | cmd | pending |
| E4-S07 | AC7 | install-wiki-skill.yml deploys wiki-query skill | FR-WIKI-001, FR-DEP-005 | cmd | pending |
| E4-S07 | AC8 | register-mcp.yml registers Graphiti MCP on target | FR-MEM-002, FR-DEP-005 | cmd | pending |
| E4-S07 | AC9 | tasks/verify.yml exits 0 on healthy deploy | FR-DEP-006 | cmd | pending |
| E4-S07 | AC10 | Playbook follows deploy-ai-dev-container.yml pattern | FR-DEP-001 | cmd | pending |
| E4-S07 | AC11 | Idempotency — second run is a no-op | FR-DEP-001 | cmd | pending |
| E4-S07 | AC12 | Role README documents deploy + rollback procedure | FR-DEP-007 | filesystem | pending |
| E4-S08 | AC1 | Pre-deploy snapshot of ct-dev-homelab captured | FR-DEP-007 | cmd | pending |
| E4-S08 | AC2 | First deploy succeeds via E4-S07 role (≤ 15 min) | FR-DEP-004, FR-DEP-006 | cmd+log | pending |
| E4-S08 | AC3 | Five smoke tests from runbook §7 pass on ct-dev-homelab | FR-DEP-006 | cmd | pending |
| E4-S08 | AC4 | At minimum 3-of-5 hard-pass + 2-of-5 quality | FR-DEP-006 | cmd | pending |
| E4-S08 | AC5 | Cleanup smoke-test pollution from Graphiti | FR-MEM-009 | session | pending |
| E4-S08 | AC6 | Rollback drill — IN ANGER mid-flight kill (≤ 1 day) | FR-DEP-007, NFR-MAINT-001 | cmd | pending |
| E4-S08 | AC7 | Mid-flight-kill leaves system in recoverable state | FR-DEP-007 | cmd | pending |
| E4-S08 | AC8 | Post-rollback state matches AC1 pre-deploy snapshot | FR-DEP-007 | cmd | pending |
| E4-S08 | AC9 | Re-deploy after rollback succeeds (round-trip integrity) | FR-DEP-007 | cmd | pending |
| E4-S08 | AC10 | Rollback wall-time recorded for FR-DEP-007 evidence | FR-DEP-007 | filesystem | pending |
| E4-S08 | AC11 | All 5 tests + deploy + rollback committed as scripts | FR-DEP-006 | git | pending |
| E4-S08 | AC12 | G-Latency baseline measured against pre-deploy reference | NFR-PERF-001 | cmd | pending |
| E4-S09 | AC1 | Template wiki page exists and conforms to ADR-006 schema | FR-OBS-001, FR-OBS-004, FR-OBS-006 | cmd | pending |
| E4-S09 | AC2 | Template specifies how to fill each KPI row | FR-OBS-004 | cmd | pending |
| E4-S09 | AC3 | Template includes copy-paste commands | FR-OBS-001 | filesystem | pending |
| E4-S09 | AC4 | First weekly digest authored at end of Sprint 4 week 1 | FR-OBS-004 | cmd | pending |
| E4-S09 | AC5 | Digest captures KPI green/amber/red status per row | FR-OBS-004 | cmd | pending |
| E4-S09 | AC6 | GitNexus tool-hit-rate includes FR-OBS-006 zero-week trigger | FR-OBS-006 | cmd | pending |
| E4-S09 | AC7 | Cost rollup includes both providers | FR-OBS-001, NFR-COST-001 | cmd | pending |
| E4-S09 | AC8 | NFR-COST-003 cost-neutrality check (if Phase 4 active) | NFR-COST-003 | cmd | pending |
| E4-S09 | AC9 | Digest committed as part of weekly retro discipline | FR-OBS-004 | git | pending |
| E4-S09 | AC10 | Template lifecycle: subsequent weeks reuse template | FR-OBS-004 | filesystem | pending |
| E4-S09 | AC11 | Operator decides delivery channel; default in-repo only | FR-OBS-001 | filesystem | pending |
| E4-S10 | AC1 | Query-hierarchy wiki page authored and lint-clean | FR-WIKI-007 | cmd | pending |
| E4-S10 | AC2 | Page documents read order with rationale and cost reasoning | FR-WIKI-007 | cmd | pending |
| E4-S10 | AC3 | Page documents WRITE hierarchy (ADR-013 addition) | FR-WIKI-007 | cmd | pending |
| E4-S10 | AC4 | Page documents bidirectional promotion rules | FR-WIKI-007 | cmd | pending |
| E4-S10 | AC5 | GitNexus exit ramp dry-run-validated via export wrapper | FR-CG-010, NFR-PORT-001, NFR-SUPP-002 | cmd | pending |
| E4-S10 | AC6 | GitNexus export round-trip dry-run into CGC-equivalent target | FR-CG-010, NFR-SUPP-002 | cmd | pending |
| E4-S10 | AC7 | Graphiti exit ramp — Cypher export validated round-trippable | FR-MEM-012, NFR-PORT-002, NFR-SUPP-002 | cmd | pending |
| E4-S10 | AC8 | Graphiti exit ramp — episode-replay log validated extractable | FR-OBS-003, NFR-SUPP-002 | log | pending |
| E4-S10 | AC9 | Exit-ramp documentation page authored at wiki/runbooks/exit-ramps.md | NFR-SUPP-002 | cmd | pending |
| E4-S10 | AC10 | Both ramps measure ≤ 1 day operator-wall-time | NFR-MAINT-001 | cmd | pending |
| E4-S10 | AC11 | index.md regenerated to reference new pages | FR-WIKI-004 | cmd | pending |
| E4-S10 | AC12 | Both pages cross-reference each other and FRs/ADRs | FR-WIKI-002 | cmd | pending |
| E4-S11 | AC1 | Four weekly digests exist for Sprint 4 weeks 1-4 | FR-OBS-004 | cmd | pending |
| E4-S11 | AC2 | KPI scorecard aggregates K1-K6 over 4-week window | FR-OBS-004 | cmd | pending |
| E4-S11 | AC3 | 4-of-6 green threshold computed; gate decision explicit | FR-OBS-004 | cmd | pending |
| E4-S11 | AC4 | G-Latency gate measured against pre-deploy baseline | NFR-PERF-001 | cmd | pending |
| E4-S11 | AC5 | G-Rollback gate confirmed via E4-S08 evidence | FR-DEP-007 | cmd | pending |
| E4-S11 | AC6 | Phase 4 LiteLLM bridge state reported in scorecard | FR-LLM-005, FR-LLM-007 | cmd | pending |
| E4-S11 | AC7 | FR-WIKI-006 (3 seeds × 3 sessions) computed and reported | FR-WIKI-006 | cmd | pending |
| E4-S11 | AC8 | Resource footprint thresholds checked | NFR-FOOTPRINT-001, NFR-FOOTPRINT-002 | cmd | pending |
| E4-S11 | AC9 | Decision record explicit and machine-readable | FR-OBS-004 | cmd | pending |
| E4-S11 | AC10 | ntfy push delivered to operator on scorecard completion | FR-OBS-002 | cmd+manual | pending |
| E4-S11 | AC11 | Scorecard cross-links per-week digests, exit ramps, hierarchy | FR-WIKI-002, FR-WIKI-007 | cmd | pending |
| E4-S11 | AC12 | ADR-014 SHOULD-bar validation: was the recalibration correct? | FR-OBS-004 | cmd | pending |
| E4-S12 | AC1 | Retro page authored and lint-clean | FR-OBS-004 | cmd | pending |
| E4-S12 | AC2 | Sprint-plan-vs-actuals table covers all 4 epics × all stories | FR-OBS-004 | cmd | pending |
| E4-S12 | AC3 | Per-epic retro paragraphs identify what worked and what didn't | FR-OBS-004 | cmd | pending |
| E4-S12 | AC4 | ADR-014 verdict explicit (was recalibration correct?) | FR-OBS-004 | cmd | pending |
| E4-S12 | AC5 | LiteLLM bridge outcome documented | FR-LLM-005, FR-LLM-007 | cmd | pending |
| E4-S12 | AC6 | Lessons-learned section captures ≥ 3 distinct lessons | FR-OBS-004 | cmd | pending |
| E4-S12 | AC7 | Backlog tickets enumerated for deferred work | FR-OBS-004 | filesystem | pending |
| E4-S12 | AC8 | Quarterly wiki review backlog ticket created | FR-OBS-004 | filesystem | pending |
| E4-S12 | AC9 | Annual exit-ramp drill backlog ticket created | NFR-SUPP-002 | filesystem | pending |
| E4-S12 | AC10 | Final close-out paragraph links retro to PRD §11 sign-off | FR-OBS-004 | cmd | pending |
| E4-S12 | AC11 | Retro committed and ntfy-pushed for closure | FR-OBS-004 | git+cmd | pending |
| E4-S12 | AC12 | Epic close updates epic frontmatter status (backlog) | FR-OBS-004 | filesystem | pending |

---

## 3. Full AC Detail (organized by epic)

For brevity, the canonical Given/When/Then prose lives inside each story file (one line per AC under §2). This section captures, per AC, the **Test command(s)**, **Expected output / pass condition**, and **Failure mode(s)** distilled from the story bodies. ACs marked with the same wording as §2 are not duplicated here unless the test command requires expansion.

### 3.1 Epic E1 — Decommission

```
### E1-S01-AC1: All four OMEGA hook entries deactivated
Story: E1-S01 — Disable OMEGA hooks in ~/.claude/settings.json
FRs verified: [FR-DEC-007]
Given: ~/.claude/settings.json contains four entries calling omega/hooks/fast_hook.py
When: Edit settings.json to disable them (move to _disabled_omega_hooks block)
Then: grep -c "fast_hook.py" ~/.claude/settings.json returns 4 (still present, relocated);
      jq '.hooks | tostring | contains("fast_hook")' returns false
Test command(s):
    python3 -c "import json; json.load(open('/home/developer/.claude/settings.json'))" && echo OK
    grep -c "fast_hook" ~/.claude/settings.json
    jq '.hooks // {} | tostring | contains("fast_hook")' ~/.claude/settings.json
Expected: count=4; jq returns false; JSON parses
Failure mode(s): JSON parse error → settings.json malformed (rollback via .bak)
                 jq returns true → entries still under .hooks (rerun edit)

### E1-S01-AC2: One full Claude session runs silent with hooks disabled
Story: E1-S01
FRs verified: [FR-DEC-007]
Test command(s):
    script -q /tmp/e1-s01-disable-session.log claude --session-name=e1-s01-safety-net
    grep -iE "omega|fast_hook|session.?start.*fail" /tmp/e1-s01-disable-session.log
Expected: zero matches in transcript
Failure mode(s): omega refs in transcript → safety-net failed; do not proceed to E1-S02

### E1-S01-AC3: OMEGA daemon process check (informational)
Story: E1-S01 — FR-DEC-007 — informational; daemon may still run (deferred to E1-S05/S06)
Test command(s): pgrep -fa "omega serve"
Expected: empty (or recorded if running)
Failure mode(s): n/a (informational)

### E1-S01-AC4: Commit message conforms to ADR-010
Test: git log -1 --format=%s | grep -F "decommission: disable OMEGA hooks (settings.json)"
Failure mode: wrong message → reword commit (do NOT amend; reset and recommit)
```

(Acceptance test detail for the remaining ACs in E1 follows the same pattern. To keep this artifact under the index-table-with-test-pointer model rather than repeating Given/When/Then for 325 ACs, the Test commands and Expected outputs for every AC are inlined verbatim in the source story files under the **Test Plan** section. Each story is the canonical detail. This section is therefore an aggregator with the per-story test-plan reference.)

**Per-story test-plan pointers (for §3.1 E1):**

- E1-S01 Test Plan → `stories/E1-S01-disable-omega-hooks.md` §Test Plan
- E1-S02 Test Plan → `stories/E1-S02-remove-omega-hook-entries.md` §Test Plan
- E1-S03 Test Plan → `stories/E1-S03-uninstall-omega-memory-and-role.md` §Test Plan
- E1-S04 Test Plan → `stories/E1-S04-remove-mempalace-store-role-skills.md` §Test Plan
- E1-S05 Test Plan → `stories/E1-S05-remove-mempalace-wiring-and-knowledge-query.md` §Test Plan
- E1-S06 Test Plan → `stories/E1-S06-remove-mempalace-conditionals-from-hermes-jinja.md` §Test Plan
- E1-S07 Test Plan → `stories/E1-S07-author-phase-1-decommission-doc.md` §Test Plan
- E1-S08 Test Plan → `stories/E1-S08-hermes-verify-and-grep-process-gates.md` §Test Plan
- E1-S09 Test Plan → `stories/E1-S09-forward-protection-pre-push-hook-and-tag.md` §Test Plan

### 3.2 Epic E2 — GitNexus Pilot

**Per-story test-plan pointers:**

- E2-S01 Test Plan → `stories/E2-S01-install-gitnexus-and-supply-chain-verification.md` §Test Plan
- E2-S02 Test Plan → `stories/E2-S02-verify-footprint-under-500mb-rss.md` §Test Plan
- E2-S03 Test Plan → `stories/E2-S03-wire-mcp-registration-to-claude-code.md` §Test Plan
- E2-S04 Test Plan → `stories/E2-S04-configure-pretooluse-and-posttooluse-hooks.md` §Test Plan
- E2-S05 Test Plan → `stories/E2-S05-configure-parent-folder-topology-and-privacy-audit.md` §Test Plan
- E2-S06 Test Plan → `stories/E2-S06-implement-five-smoke-test-scenarios.md` §Test Plan
- E2-S07 Test Plan → `stories/E2-S07-implement-graph-export-wrapper-ndjson.md` §Test Plan
- E2-S08 Test Plan → `stories/E2-S08-week-1-decision-gate-kpi-scorecard.md` §Test Plan

### 3.3 Epic E3 — Graphiti Pilot

**Per-story test-plan pointers:**

- E3-S01 Test Plan → `stories/E3-S01-falkordb-compose-stack.md` §Test Plan
- E3-S02 Test Plan → `stories/E3-S02-mcp-http-tailscale.md` §Test Plan
- E3-S03 Test Plan → `stories/E3-S03-claude-md-memory-section.md` §Test Plan
- E3-S04 Test Plan → `stories/E3-S04-llm-embedder-semaphore-config.md` §Test Plan
- E3-S05 Test Plan → `stories/E3-S05-smoke-test-write-read-namespace.md` §Test Plan
- E3-S06 Test Plan → `stories/E3-S06-five-functional-smoke-tests.md` §Test Plan
- E3-S07 Test Plan → `stories/E3-S07-backup-cron-aof-rdb-cypher.md` §Test Plan
- E3-S08 Test Plan → `stories/E3-S08-restore-drill.md` §Test Plan
- E3-S09 Test Plan → `stories/E3-S09-week2-decision-gate.md` §Test Plan

### 3.4 Epic E4 — Production Hardening

**Per-story test-plan pointers:**

- E4-S01 Test Plan → `stories/E4-S01-wiki-schema-and-bootstrap.md` §Test Plan
- E4-S02 Test Plan → `stories/E4-S02-bootstrap-wiki-seeds.md` §Test Plan
- E4-S03 Test Plan → `stories/E4-S03-wiki-query-skill.md` §Test Plan
- E4-S04 Test Plan → `stories/E4-S04-daily-1dollar-cap-autothrottle.md` §Test Plan
- E4-S05 Test Plan → `stories/E4-S05-litellm-bridge-config.md` §Test Plan
- E4-S06 Test Plan → `stories/E4-S06-validate-litellm-50fact-gate.md` §Test Plan
- E4-S07 Test Plan → `stories/E4-S07-ansible-role-context-stack.md` §Test Plan
- E4-S08 Test Plan → `stories/E4-S08-deploy-ct-dev-homelab-and-rollback.md` §Test Plan
- E4-S09 Test Plan → `stories/E4-S09-weekly-observability-digest.md` §Test Plan
- E4-S10 Test Plan → `stories/E4-S10-query-hierarchy-and-exit-ramps.md` §Test Plan
- E4-S11 Test Plan → `stories/E4-S11-week4-kpi-scorecard.md` §Test Plan
- E4-S12 Test Plan → `stories/E4-S12-phase4-retro-and-close.md` §Test Plan

**Why §3 points back to story files rather than re-pasting:** every story already carries a `## Test Plan` block with verbatim runnable commands. Duplicating ~325 Test Plan blocks here would inflate the file by ~3000 lines without adding information; the §2 index lets a tester walk every AC by ID, and the per-story file is the canonical detail. This is the same principle as PRD §12 ("if Phase 5 finds an untested observable signal, that is a PRD bug to be fixed by addendum") — the tests live where they're maintained.

**Dependency annotations** (where AC depends on hidden state from another AC, beyond the obvious story-blocks-story chain):

- E1-S08-AC1 depends on E1-S06-AC1..AC7 having all landed on the branch (not just merged). If E1-S06 is reverted mid-PR, E1-S08-AC1's verify run fails.
- E2-S08-AC3 depends on E2-S06-AC3 having produced the cross-repo Cypher query — the K1 sample reuses the question.
- E3-S05-AC8 depends on E3-S05-AC5's outcome (Path A vs Path B) — the CLAUDE.md edit is conditional.
- E3-S09-AC4 / AC5 / AC9 depend on **2 weeks of operator observation time** — they are not runnable on day 1 of E3.
- E4-S02-AC7 depends on **operator running ≥ 3 distinct sessions per seed during Sprint 4** — runnable only at end of week 4.
- E4-S06-AC11 depends on E4-S05-AC2 deferral having fired — deferral cascades.
- E4-S08-AC4's "3-of-5 hard-pass + 2-of-5 quality" rule is a per-ADR-014 SHOULD relaxation; tests 1, 2, 5 are non-negotiable.
- E4-S11-AC1 depends on **4 separate weekly digests existing**, which means E4-S09 must have been run weekly — not just authored once.
- E4-S12-AC2 depends on **all 38 stories having reached DONE or DEFERRED** — it is the synthesis story.

---

## 4. Cross-Cutting Test Categories (matrix view)

### 4.1 FR-DEC-* zero-references after E1 (regression suite for decommission)

| FR | Verifier ACs |
|---|---|
| FR-DEC-001 | E1-S04-AC1 |
| FR-DEC-002 | E1-S04-AC3, AC4 |
| FR-DEC-003 | E1-S04-AC5 |
| FR-DEC-004 | E1-S05-AC1, AC3, AC4 |
| FR-DEC-005 | E1-S06-AC1..AC7 |
| FR-DEC-006 | E1-S05-AC2, AC4 |
| FR-DEC-007 | E1-S01-AC1..AC4, E1-S02-AC1..AC4 |
| FR-DEC-008 | E1-S03-AC1..AC3 |
| FR-DEC-009 | E1-S08-AC2, E1-S09-AC1..AC9 (forward) |
| FR-DEC-010 | E1-S08-AC3, AC4 |
| FR-DEC-011 | E1-S08-AC1, AC5 |
| FR-DEC-012 | E1-S04-AC2, E1-S07-AC3 |

The regression-suite incantation that closes all FR-DEC-* together (E1-S08-AC2):
```bash
grep -r -i 'mempalace\|omega' homelab/ \
  --exclude-dir=.git \
  --exclude-dir=_bmad-output \
  --exclude-dir=docs/decommission
```

### 4.2 FR-CG-* graph correctness

| FR | Verifier ACs |
|---|---|
| FR-CG-001 | E2-S01-AC3, AC4; E2-S03-AC2, AC3, AC5 |
| FR-CG-002 | E2-S01-AC6, E2-S02-AC5, E2-S05-AC5 |
| FR-CG-003 | E2-S05-AC1, AC3, AC4 |
| FR-CG-004 | E2-S04-AC1, AC2 |
| FR-CG-005 | E2-S04-AC3, AC4 |
| FR-CG-006 | E2-S06-AC5, E2-S08-AC4 |
| FR-CG-007 | E2-S06-AC5 (cold-start full reindex) |
| FR-CG-008 | E2-S05-AC4, E2-S08-AC3, E3-S09-AC1 |
| FR-CG-009 | E2-S06-AC1..AC4, E2-S08-AC6 |
| FR-CG-010 | E2-S07-AC1..AC9, E4-S10-AC5, AC6 |
| FR-CG-011 | E2-S03-AC6, E2-S06-AC7 |
| FR-CG-012 | E2-S01-AC6, E2-S02-AC5, E2-S05-AC5, E2-S08-AC5 |

### 4.3 FR-MEM-* extract-and-recall

| FR | Verifier ACs |
|---|---|
| FR-MEM-001 | E3-S01-AC1..AC7 |
| FR-MEM-002 | E3-S02-AC1..AC3, AC5 |
| FR-MEM-003 | E3-S02-AC1, AC4, AC7 |
| FR-MEM-004 | E3-S04-AC1, AC3, AC4 |
| FR-MEM-005 | E3-S03-AC4; E3-S05-AC2, AC4..AC6 |
| FR-MEM-006 | E3-S04-AC1, AC3, AC8 |
| FR-MEM-007 | E3-S09-AC5 |
| FR-MEM-008 | E3-S09-AC4 |
| FR-MEM-009 | E3-S02-AC3, AC6; E3-S05-AC1, AC3, AC7; E3-S06-AC1..AC4, AC7 |
| FR-MEM-010 | E3-S03-AC1..AC7 |
| FR-MEM-011 | E3-S04-AC1, AC3, AC5 |
| FR-MEM-012 | E3-S07-AC3, AC4, AC7; E4-S10-AC7 |
| FR-MEM-013 | E3-S06-AC5, AC6 |
| FR-MEM-014 | E3-S07-AC1..AC10; E3-S08-AC1..AC10 |
| FR-MEM-015 | E3-S09-AC7 |

### 4.4 NFR-PERF-* latency

| NFR | Verifier ACs | Target |
|---|---|---|
| NFR-PERF-001 | E2-S04-AC5; E2-S08-AC8; E4-S08-AC12; E4-S11-AC4 | < 1 s session-start overhead |
| NFR-PERF-002 | E2-S06-AC2, AC4 | < 500 ms p95 query |
| NFR-PERF-003 | E4-S03-AC7 | < 200 ms wiki file read |
| NFR-PERF-004 | E2-S05-AC6, E2-S06-AC5, E2-S08-AC4 | ≤ 30 s incremental reindex |
| NFR-PERF-005 | E2-S05-AC2, E2-S06-AC5 | ≤ 60 s full reindex |
| NFR-PERF-006 | (no AC binds it directly — see §5.4) | < 5 s `add_episode` |

### 4.5 NFR-COST-* spend-cap

| NFR | Verifier ACs | Target |
|---|---|---|
| NFR-COST-001 | E3-S09-AC3, E4-S09-AC7 | < $20/mo all-in |
| NFR-COST-002 | E4-S04-AC2, AC6, E3-S09-AC3 | < $1/day with auto-throttle |
| NFR-COST-003 | E4-S06-AC9, E4-S09-AC8 | bridge ≤ Phase 1 baseline |

### 4.6 NFR-PRIV-* code-stays-local

| NFR | Verifier ACs | Target |
|---|---|---|
| NFR-PRIV-001 | E2-S02-AC5, E2-S05-AC5 | source code never leaves workstation |
| NFR-PRIV-002 | (FR-LLM-004 + E4-S05-AC7 documents the boundary) | embeddings → OpenAI is acknowledged |
| NFR-PRIV-003 | E3-S02-AC7 | phone-facing surfaces Tailscale-only |

### 4.7 Other NFR cross-cuts

| NFR | Verifier ACs |
|---|---|
| NFR-FOOTPRINT-001 | E3-S09-AC7, E4-S11-AC8 |
| NFR-FOOTPRINT-002 | E2-S02-AC2, AC3; E2-S06-AC6; E3-S09-AC8; E4-S11-AC8 |
| NFR-FOOTPRINT-003 | E2-S02-AC4, E3-S07-AC9 |
| NFR-AVAIL-001 | E2-S03-AC6, E2-S06-AC6, AC7 |
| NFR-AVAIL-002 | E3-S06-AC5, AC6 |
| NFR-AVAIL-003 | E4-S06-AC6 |
| NFR-MAINT-001 | E2-S04-AC7, E3-S08-AC7, E4-S05-AC8, E4-S08-AC6, E4-S10-AC10 |
| NFR-MAINT-002 | (FR-DEP-007 partial; E1-S07-AC4 documents the rollback) |
| NFR-SUPP-001 | E2-S01-AC2 |
| NFR-SUPP-002 | E2-S07-AC8; E4-S10-AC5..AC9; E4-S12-AC9 |
| NFR-PORT-001 | E2-S07-AC3, E4-S10-AC5 |
| NFR-PORT-002 | E3-S07-AC7, E4-S10-AC7 |
| NFR-PORT-003 | (markdown-by-construction; no AC needed) |

---

## 5. Quality Audit

### 5.1 Vague / non-observable ACs

The suite uses observable verbs throughout — most ACs check exit codes, grep counts, file existence, jq-parsed JSON, or HTTP status. The audit found **6** ACs that bend the observable bar; all are operator-judgment items where automation is structurally inappropriate, but each could be tightened.

| AC | Issue | Recommendation |
|---|---|---|
| **E3-S09-AC6 (K6 subjective uplift)** | "≥ 'noticeable' on retro" — `noticeable` is operator-defined; rubric in story says "≥ 60% useful-tag rate". | Already mitigated in E2-S08-AC2 (rubric pinned). E3-S09-AC6 should re-state the rubric inline rather than referring to retro narrative. Reword: "K6 = green if ≥ 60% of sessions tagged useful in graphiti-retro-tags.md over 14-day window." |
| **E4-S02-AC7 (3 sessions × 3 seeds)** | "operator log records ≥ 3 distinct session IDs/timestamps per seed" depends on operator manually filling `_session-log.md`. The `session_id_or_topic` column is operator-curated free-text; a forgotten entry produces a false negative. | Either (a) automate session-log injection from Claude Code transcript metadata, or (b) accept this as inherently manual and document the operator-discipline dependency in §5.1 of acceptance.md (this list). |
| **E4-S08-AC4 (3-of-5 hard-pass + 2-of-5 quality)** | "operator may judge cite quality leniently" on smoke test 3; "may slip if Graphiti's clock is off by minutes" on smoke test 4. The leniency criteria are not observable. | Reword: test 3 passes if `wiki-query` skill log shows the slug was read (binary); test 4 passes if `valid_at` is within ±60 s of `reference_time` (numeric). |
| **E4-S09-AC5 (KPI green/amber/red status per row)** | "using the table from the template" — template is defined elsewhere; this AC depends on the template being correct. | Reword: "each KPI row in the digest has a status cell with literal value `Green`, `Amber`, or `Red`; no other strings; verifiable via grep -E '\\| \\[GAR\\]'". |
| **E4-S11-AC12 (ADR-014 SHOULD-bar validation)** | Asks "did any SHOULD that ought to have been MUST cause a regression?" — this is a yes/no with operator narrative; the AC is structurally a fill-in-the-blank rather than a runnable check. | Accept as inherently retrospective. Tighten only by requiring the answer be one of {`yes-FRname`, `none observed`} via grep — already specified in E4-S12-AC4 and inherited here. |
| **E4-S12-AC6 (≥ 3 distinct lessons)** | Each lesson = "1 line problem + 1 line cause + 1 line mitigation". The triplet-shape is observable; the *quality* of the lessons is not. | Accept as inherently retrospective; the triplet-shape grep gate is sufficient. |

**Summary:** the 3 worst (most operator-narrative-dependent) are E4-S02-AC7, E4-S08-AC4, and E3-S09-AC6. The first is a Sprint-4-discipline gate; the second can be tightened with concrete pass criteria; the third should restate its rubric inline rather than deferring to the retro narrative.

### 5.2 Duplicate / overlapping ACs across stories

The suite has natural overlap on cross-cut signals (footprint, latency, privacy, rollback) by design — different epics test the same NFR at different points in the lifecycle. Found **5** sets of materially overlapping ACs; in each case the redundancy is justified or the consolidation is recommended:

| Duplicate set | Overlap | Recommendation |
|---|---|---|
| **GitNexus footprint** — E2-S02-AC2, AC3 (24h passive) vs E2-S06-AC6 (1h sustained-load) vs E3-S09-AC8 (week-2 sample) vs E4-S11-AC8 (4-week peak) | All measure GitNexus daemon RSS at increasing time scales. | Justified — different windows surface different failure modes (leak vs spike vs steady-state). Keep all four. |
| **G-Latency NFR-PERF-001** — E2-S04-AC5 (single hook install) vs E2-S08-AC8 (week-1) vs E4-S08-AC12 (post-deploy) vs E4-S11-AC4 (week-4 final) | Same metric, four time points. | Justified — G-Latency is a hard gate; checking at four points along the deploy timeline catches regressions early. |
| **Graceful-degradation drills** — E2-S03-AC6 (GitNexus pre-flight, < 3s), E2-S06-AC7 (GitNexus full drill), E3-S06-AC5 (Graphiti drill, < 3s) | Both tools tested for the same NFR-AVAIL-* / FR-CG-011 / FR-MEM-013 contract. | Justified — two distinct tools, two distinct failure paths. E2-S03-AC6 is the pre-flight, E2-S06-AC7 is the deep drill; no consolidation. |
| **Rollback wall-time** — E3-S08-AC7 (FalkorDB-only, < 10 min) vs E4-S08-AC6, AC10 (full-stack, ≤ 1 day) vs E4-S05-AC8 (LiteLLM bridge, ≤ 60 s) | Three rollback scopes. | Justified — different blast radii. E3-S08 is a tier-specific drill; E4-S08 is the product-level G-Rollback gate; E4-S05-AC8 is the LiteLLM micro-revert. |
| **Wiki-lint** — E4-S01-AC5..AC7, E4-S02-AC2, AC9, AC4, E4-S10-AC1, AC11, AC12, E4-S11 et al. | Every wiki page authored re-runs `wiki-lint.sh`. | Slight redundancy. Recommend a "wiki integrity gate" master AC at E4-S11 that runs lint once across all 4 weeks of contributions and asserts zero new violations. (Currently each story's commit hook covers this already.) |

**Count of materially redundant ACs: 0.** All overlaps surface different signals or different time windows. No consolidation is recommended; one optional tightening (consolidated wiki-lint gate at E4-S11) was noted.

### 5.3 FRs without coverage

Cross-checked the 73 FRs from PRD §5 against the §2 AC index:

**Result: 0 FR-MUST gaps; 0 FR-SHOULD gaps.** All 73 FRs are covered by at least one AC in §2.

Verification of high-traffic FRs:

- **FR-DEC-001 through FR-DEC-012**: covered (E1).
- **FR-CG-001 through FR-CG-012**: covered (E2).
- **FR-MEM-001 through FR-MEM-015**: covered (E3 + E4-S07/E4-S08 register-mcp).
- **FR-WIKI-001 through FR-WIKI-010**: covered (E4-S01..S03, S10, S11).
- **FR-LLM-001 through FR-LLM-008**: covered (E4-S05, S06; deferral path covers FR-LLM-007).
- **FR-OBS-001 through FR-OBS-006**: covered (E2-S08, E3-S04, E3-S09, E4-S04, E4-S09, E4-S11, E4-S12).
- **FR-DEP-001 through FR-DEP-010**: covered (E1-S03/S05, E2-S01/S03, E3-S01, E4-S07/S08).

The coverage is dense — most FRs have ≥ 3 ACs verifying them across the lifecycle.

### 5.4 NFRs without acceptance test

Checked the 25 NFRs from PRD §6 against the §2 AC index:

**Found 2 NFRs with weak / no per-story AC coverage:**

| NFR | Threshold | Status | Recommendation |
|---|---|---|---|
| **NFR-PERF-006** | `add_episode` ingestion ≤ 5 s/typical episode | **Weak coverage** — implicit in E3-S05-AC1 (UUID returns within session expectation) and E4-S08-AC3 test 1 (returns within 10 s) but no AC explicitly times it against the 5 s threshold across 30 episodes. | Add as E2E plan item: time `add_episode` over 30 episodes during E3-S06; assert mean < 5 s, p95 < 10 s. Alternatively, file a SHOULD-tier addendum AC against E3-S06 Test Plan. |
| **NFR-PRIV-002** | Embeddings of conversational fact semantics MAY go to OpenAI; documented and accepted | **No AC** — explicitly noted as "documented" in PRD; no story has an AC that asserts the documentation exists or that the embedding-call payload audit was done. | Add as E2E plan item: confirm `~/.claude/CLAUDE.md` Memory section + wiki page on tier-of-truth document the cloud-embedding boundary; sample one embedding-call payload via tcpdump and confirm it carries fact text (not source code). |
| **NFR-MAINT-002** | Decommission rollback documented and exercisable | **Document-only coverage** — E1-S07-AC4 documents the rollback path; no AC exercises the dry-run. | Acceptable as `documented`-tier per PRD §10 R8 acknowledgement. E2E plan should include an annual decommission rollback drill if the operator wants belt-and-suspenders. |
| **NFR-PORT-003** | Wiki content portable (markdown by construction) | **No AC needed** — by construction. | None. |

**E2E-plan-only NFRs (legitimately without per-story AC):** NFR-PERF-006, NFR-PRIV-002 (per-NFR audit), NFR-MAINT-002 (annual drill option), NFR-PORT-003 (by-construction). These belong in the E2E plan (Phase 5b) under "cross-cutting NFR validation."

---

## 6. Test Execution Order

Recommended order, with smoke-tests before exit-gates within each epic.

### Sprint 1 (Epic E1)

1. E1-S01 ACs (disable hooks, safety-net session)
2. E1-S02 ACs (full removal)
3. E1-S03 ACs (omega package + role)
4. E1-S04 ACs (mempalace store + role + skills)
5. E1-S05 ACs (wiring removal)
6. E1-S06 ACs (Hermes Jinja — riskiest commit)
7. E1-S07 ACs (decommission doc)
8. **E1-S08 ACs** (Hermes verify + grep + pgrep gates) — **EXIT GATE**
9. E1-S09 ACs (forward-protection hook + tag) — **post-merge**

### Sprint 2 (Epic E2)

10. E2-S01 ACs (install + supply chain)
11. E2-S02 ACs (footprint baseline) — runs over 24h in parallel
12. E2-S03 ACs (MCP registration)
13. E2-S04 ACs (hooks)
14. E2-S05 ACs (topology + privacy audit)
15. E2-S06 ACs (5 smoke scenarios)
16. E2-S07 ACs (export wrapper)
17. **E2-S08 ACs** (week-1 KPI gate) — **DECISION GATE** (proceed/migrate/revert)

### Sprint 3 (Epic E3)

18. E3-S01 ACs (compose stack)
19. E3-S02 ACs (MCP HTTP transport)
20. E3-S03 ACs (CLAUDE.md memory section)
21. E3-S04 ACs (LLM/embedder/throttle/telemetry)
22. E3-S05 ACs (smoke + AR8 closure)
23. E3-S06 ACs (5 functional scenarios)
24. E3-S07 ACs (backup cron)
25. E3-S08 ACs (restore drill — destructive)
26. **E3-S09 ACs** (week-2 KPI gate) — **DECISION GATE** — requires 2 weeks of observation before runnable

### Sprint 4 (Epic E4)

27. E4-S01 ACs (wiki schema + bootstrap)
28. E4-S02 ACs (wiki seeds) — AC7 measured at end of week 4
29. E4-S03 ACs (wiki-query skill)
30. E4-S04 ACs (daily $1 cap + synthetic breach drill)
31. E4-S05 ACs (LiteLLM bridge config) — may execute deferral path
32. E4-S06 ACs (50-fact validation gate) — may execute deferral path
33. E4-S07 ACs (Ansible role authoring)
34. **E4-S08 ACs** (ct-dev-homelab deploy + rollback IN ANGER) — **G-Rollback gate**
35. E4-S09 ACs — runs **weekly** through Sprint 4 (4 instances)
36. E4-S10 ACs (query hierarchy + exit ramps dry-run)
37. **E4-S11 ACs** (week-4 product KPI scorecard) — **PRODUCT DECISION GATE**
38. **E4-S12 ACs** (Phase 4 retro + epic close) — **PRD §11 SIGN-OFF**

---

## 7. Test Tooling

For 100% reproducibility from a clean dev workstation + ct-dev-homelab + ct-ai-01.

### 7.1 Workstation prerequisites

- **bash 5+** (for `set -euo pipefail`, associative arrays)
- **jq** (JSON parsing in every Test Plan)
- **yq** (YAML frontmatter parsing for wiki-lint)
- **curl** (MCP HTTP probes, ntfy pushes, OpenAI Usage API)
- **bc** (cost arithmetic)
- **shellcheck** (script lint)
- **git** (incl. `git config core.hooksPath`)
- **ansible-playbook ≥ 2.14** (decommission, deploy)
- **ansible-lint, yamllint, ansible-vault** (E1, E4-S07)
- **npm + Node.js** (GitNexus install — E2)
- **claude-code CLI** (the SUT)
- **gh** (GitHub API for E2-S01 supply-chain check)
- **tcpdump + sudo** (E2 privacy audits)
- **strace** (E2-S01-AC6 install-time network audit)
- **script** (transcript capture for session-based ACs)
- **time** (latency measurement)
- **awk, sed, grep, find** (ubiquitous)
- **tree** (E4-S01-AC1; non-essential but cleaner than `find -L 2`)

### 7.2 ct-ai-01 prerequisites (server side)

- **docker + docker-compose v2** (E3 stack)
- **redis-cli** (inside falkordb container; comes with image)
- **logger** (cost-cap.sh logging)
- **systemd-journald** (`journalctl -t graphiti-cost-cap`)
- **cron** (E3-S07, E4-S04)
- **logrotate** (E3-S04, E3-S07)
- **Tailscale** (already installed; networking only)

### 7.3 ct-dev-homelab prerequisites (deploy target)

- **Tailscale-reachable** at canonical hostname
- **claude-code CLI installed** (E4-S07-AC7 skips with friendly message if absent — but full E4-S08 acceptance requires it)
- **dpkg-based system** (E4-S08-AC1 snapshot uses dpkg)
- **bash + the workstation toolchain subset** (for receiving rsync'd wiki tree, running smoke tests)

### 7.4 External services

- **OpenAI API access** (gpt-4o-mini, text-embedding-3-small, organization admin key for Usage API)
- **Anthropic API access** (Claude Code's substrate; usage export accessible)
- **CT101 ntfy server** (via Tailscale; for E4-S04, E4-S06, E4-S11 phone notifications)
- **`hybrid_gemma_serving` LiteLLM gateway** — only required if E4-S05 active path is taken; deferral path skips this dep

### 7.5 Optional / belt-and-braces

- **password-store** (operator vault password for ansible-vault)
- **systemd-timer or `at`** (E2-S02-AC3 24h sampler — alternative to `cron`)

All of the above should already be present on the operator's workstation per project memory; the install-script artifacts in E2-S01-AC5, E3-S01-AC2, E4-S07-AC1 capture any deltas needed for a fresh-rebuild walkthrough.

---

## 8. Open Issues for the E2E plan (Phase 5b)

The per-story AC suite is comprehensive at the unit-of-deploy level but cannot, by construction, cover certain cross-cutting integration scenarios. The E2E plan (Phase 5b) MUST cover:

### 8.1 Cross-tier integration scenarios

1. **Full 4-tier query walk-through.** A single Claude Code session that demonstrates Tier 1 (wiki-query) → Tier 2 (GitNexus cypher) → Tier 3 (Graphiti search_facts) → Tier 4 (auto-memory MEMORY.md) all firing in sequence on a realistic question. No per-story AC tests this — each tier's ACs are tier-isolated. The E2E plan should script one canonical "real session" that exercises all four.

2. **Hooks + MCP coordination.** PreToolUse + PostToolUse + Graphiti MCP + GitNexus MCP + wiki-query skill all loaded simultaneously. Per-story ACs test each pair; no AC asserts they coexist without fighting (e.g., a PostToolUse-on-commit-induced GitNexus reindex that races a Graphiti `add_episode` write).

### 8.2 Full deploy + rollback E2E

3. **Cold-start install on a fresh ct-dev-homelab.** Per-story ACs deploy *to* ct-dev-homelab (E4-S08-AC2) but assume the workstation is already in steady state. The E2E plan should walk a fresh-VM-style end-to-end install starting from a clean homelab repo clone + clean workstation.

4. **Rollback from product-level failure modes.** E4-S08 exercises mid-flight kill rollback; the E2E plan should also cover (a) "K3 spend ran away — daily cap fired but I want to revert anyway" path; (b) "G-Latency regressed at week 3 — revert E2 hooks while keeping E3 Graphiti"; (c) "Phase 4 LiteLLM gate fails after 7-day run — fall back to gpt-4o-mini, replay episodes" path.

### 8.3 NFR cross-cutting coverage (per §5.4)

5. **NFR-PERF-006**: time `add_episode` over 30 episodes; assert mean < 5 s, p95 < 10 s.
6. **NFR-PRIV-002**: tcpdump-based audit of one embedding-call payload, confirming fact text (NOT source code) is what crosses the boundary.
7. **NFR-MAINT-002**: optional annual decommission rollback drill (re-install OMEGA + MemPalace from prior commit, verify Hermes runs).

### 8.4 End-to-end Claude Code session that exercises all 4 tiers

8. **Canonical "operator workflow" session.** A scripted ~30-minute Claude Code session running through: open project, ask cross-repo code question (Tier 2), ask architecture question (Tier 1), ask "what did we decide" (Tier 3), session-start auto-memory load (Tier 4), commit a change (PostToolUse fires Tier 2 reindex). Capture transcript; assert each tier was queried; assert total tokens consumed < operator's K1 baseline × ratio.

### 8.5 Long-horizon items

9. **Quarterly wiki review** (E4-S12-AC8 backlog).
10. **Annual exit-ramp drill** (E4-S12-AC9 backlog).
11. **Quarterly Graphiti restore drill** (E3-S08 next-quarterly-drill calendar entry).

These belong in the long-horizon E2E plan / operations runbook, not in Phase 5b's first-release acceptance test sweep.

---

**End of acceptance.md — handoff to E2E test plan (Phase 5b) and readiness check (Phase 5c).**
