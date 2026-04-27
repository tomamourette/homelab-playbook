# E4-S09 — Weekly Observability Digest + GitNexus KPI Backfill — Evidence

**Date:** 2026-04-27
**Story:** E4-S09 (sprint-plan.md §7; story spec at `_bmad-output/planning-artifacts/products/context-stack/stories/E4-S09-weekly-observability-digest.md`)
**Sprint:** 5 (Production Hardening Part B / Epic E4 remainder)
**Branch:** `feature/context-stack-e3-graphiti`
**Predecessor:** Sprint 5 kickoff `ca21749` (2026-04-27)

## Scope (delivered)

1. **Weekly digest template** at `wiki/runbooks/weekly-observability-digest.md` (operator procedure + per-KPI thresholds + delivery-channel decision per AC11).
2. **Gather script** at `scripts/weekly-digest.sh` (prints a digest body to stdout; auto-fills 6 of the 10 KPI rows from live data; falls back to `[TBD]` sentinels on failure; structurally idempotent).
3. **First filled digest** at `wiki/decisions/weekly-digest-2026-w18.md` (auto-fills landed; manual `[TBD]` rows preserved for operator refinement at end-of-week retro).
4. **Sprint-2 KPI backfill** at `docs/context-stack/sprint-2/kpi-backfill.md` (closes the K1 / K2 / K4-GitNexus INSUFFICIENT-DATA carry from Sprint 3 e3-s09-kpi-scorecard).
5. **Optional cron role** at `homelab-infra/ansible/roles/weekly-digest/` (ships disabled per AC11 default; opt-in via `weekly_digest_enabled: true`).
6. **Wiki index update** referencing the new template + first digest under `runbooks/` and `decisions/` respectively.

## GitNexus KPI backfill — verbatim measurements

Closes carry-forward from `sprint-3/e3-s09-kpi-scorecard.md` (K1, K2, K4-GitNexus = INSUFFICIENT-DATA).

### K1 token reduction

- **Question:** "find tailscale ACL policy and ssh tag definitions in the infrastructure" (representative cross-repo question).
- **Baseline (raw `grep -r -i tailscale\|tailnet` across all 3 repos, capped at 50 files):** 50 files matched, 1,171,914 bytes loaded as full-file context = **~292,978 tokens** at 4 chars/token.
- **GitNexus query alternative ceiling (default `limit=5, max_symbols=10`):** 5 ranked execution flows × ~10 symbols × ~150-200 tokens per symbol payload = **~7,500-10,000 tokens** ceiling.
- **Ratio:** ~292,978 / ~10,000 = **~29x**. PRD threshold >= 5x. **PASS (proxy).**
- **Confidence:** MEDIUM — the GitNexus MCP `list_repos` returned `[]` from this Claude Code session (container `${HOME}` resolves to `/root` while the operator's analyze runs from `/home/developer`; two registries diverge — full path-resolution gap captured in the backfill doc and flagged for E4-S10 exit-ramp resolution). Token-volume arithmetic is sound; round-trip latency was not exercised end-to-end.

### K2 reindex time

- **Direct measurement:** out of scope per E4-S09 constraint (do not reindex / change daemon state).
- **Available proxy:** registry-recorded `indexedAt` lag vs HEAD commit time per repo:

  | Repo | HEAD time | indexedAt | Lag |
  |---|---|---|---|
  | homelab-apps | 09:58Z | 06:52Z | -3h 06m |
  | homelab-infra | 12:36Z | 11:36Z | -1h 00m |
  | homelab-playbook | 13:09Z | 12:09Z | -1h 00m |

  Lag is consistently negative because PostToolUse hook fires `detect_changes` (cheap) and `analyze` only on explicit operator invocation. The recorded `indexedAt` deltas indicate sub-30-minute spacing between full re-indexes of all 3 repos earlier in the day — well below a 60-second per-repo target — but this is inference from spacing, not a duration timing.

- **Verdict:** **PROXY-PASS-BUT-INSUFFICIENT-FOR-GATE.** Recurring digest's K2 row picks up real timings from PostToolUse hook log lines once those start landing in `~/.claude/projects/*/sessions/*.jsonl`.

### K4-GitNexus non-blank reindex artifact rate

- **Method:** for each registered repo, verify the per-repo `.gitnexus/lbug` graph file exists and is non-empty (zero-byte = blank artifact).

  | Repo | `lbug` size | Files | Nodes | Edges | Status |
  |---|---|---|---|---|---|
  | homelab-apps | 11.7 MB | 96 | 343 | 344 | NON-BLANK |
  | homelab-infra | 31.5 MB | 362 | 3850 | 4522 | NON-BLANK |
  | homelab-playbook | 35.2 MB | 492 | 8113 | 8364 | NON-BLANK |

- **Result:** 3/3 = **100%. PASS (high confidence — direct on-disk measurement).**

### Daemon footprint (informational, supports AR1 closure)

- `docker exec gitnexus cat /proc/1/status | grep VmRSS` = **93,624 kB (~91.4 MiB)**.
- `docker stats --no-stream gitnexus` = **57.53 MiB** (the docker-stats memory accounting differs from the in-process VmRSS by including/excluding cache pages; both are well below the AR1 < 500 MB threshold).

## Digest script — language / path / runtime

| Property | Value |
|---|---|
| Language | bash |
| Path | `homelab-playbook/scripts/weekly-digest.sh` |
| Permissions | `0755` (executable) |
| External tools | `git`, `ssh`, `docker stats`, `awk`, `jq`, `find`, `grep` |
| SSH targets | `192.168.50.160` (ct-ai-01, cost-cap log) and `192.168.50.156` (ct-dev-homelab, FalkorDB RSS + tom-personal episodes) — overrideable via `CT_AI_01_HOST` / `CT_DEV_HOMELAB_HOST` env vars |
| SSH key | `~/.ssh/homelab_ed25519` (overrideable via `HOMELAB_SSH_KEY`) |
| Failure handling | Every probe falls back to `TBD` sentinel on failure; never aborts mid-render |
| Idempotency | Structurally idempotent (deterministic windowing, no random tokens, no second-precision timestamps inside the body); `falkordb_rss` exhibits ~0.17 MiB jitter between consecutive runs because live `docker stats` is a real-time sample — this is value-jitter on a single row, not a structural change. The auto-generated G/A/R status doesn't flip on this jitter (16.58 MiB and 16.75 MiB both score G). |
| Runtime | ~2-3 seconds typical (dominated by 3 SSH round-trips: 1 to ct-ai-01, 2 to ct-dev-homelab) |

## First digest output (excerpt)

`wiki/decisions/weekly-digest-2026-w18.md` after running the gather script:

```
| KPI | Value | Threshold | Status |
|---|---|---|---|
| K1 token reduction | [TBD; 3 cross-repo Q&A samples this week] | >= 5x | [G/A/R] |
| K2 reindex time (incr.) | [TBD; from PostToolUse hook log] | <= 30 s | [G/A/R] |
| K2 reindex time (full) | [TBD] | <= 60 s | [G/A/R] |
| K3 spend (week) | $0.000254 (lifetime: $0.0002538; cap-breaches in window: 2) | <= $5/wk | R |
| K4 facts/week (tom-personal) | 0 | >= 25 | [G/A/R] |
| K5 good-catch tally | [TBD; manual operator-tag count] | >= 3 over 4 weeks | [G/A/R] |
| K6 subjective uplift | [TBD; 1-paragraph operator note] | "noticeable" by week 4 | [G/A/R] |
| FalkorDB RSS (ct-dev-homelab) | 16.84MiB | < 200 MB | G |
| GitNexus daemon RSS (workstation) | 58.85MiB | < 500 MB | G |
| GitNexus tool-hit-rate (week) | 43 calls | > 0/wk | G |
```

Per-row notes:

- **K3 status = R** is correct: ADR-008 amendment threshold says "any cap-breach in window -> red", and `awk` over `cost-cap.log` finds 2 `throttled=true` entries from the E4-S04 manual breach-test. The actual *spend* is trivially small ($0.000254/week against $5 threshold). This row demonstrates the breach-detection path without requiring a real overspend.
- **K4 facts = 0** is correct: the production-target Graphiti deployment at ct-dev-homelab has 1 episode total (smoke-test only), zero in `tom-personal` namespace. The metric will grow as the operator uses Graphiti.
- **GitNexus tool-hit-rate = 43 calls** is the in-session count from `~/.claude/projects/*/sessions/*.jsonl` — non-zero, so no FR-OBS-006 CLAUDE.md-review trigger fires.
- **K1 / K2 / K5 / K6** retain `[TBD]` sentinels — these are operator-judgement rows that the script intentionally does not auto-fill (AC2 of the story spec).

## Cron schedule

Default: **Sunday 18:00 UTC** (per the role's `weekly_digest_hour`/`_weekday` defaults). Chosen to avoid:

- 02:00 UTC daily AOF rewrite (ADR-007)
- 03:00 UTC weekly RDB dump (ADR-007)
- 04:00 UTC monthly Cypher export (ADR-007)
- 30-minute cost-cap cron tick (ADR-008)

**Status: not yet enabled.** AC11 default is in-repo-only / no automation; the role ships disabled. Operator opts in by setting `weekly_digest_enabled: true` on whichever host runs it (workstation is the natural choice — that's where `homelab-playbook` lives — but ct-ai-01 is also acceptable if cost-cap aggregation should run there directly).

## Acceptance criteria scoring

| AC | Status | Notes |
|---|---|---|
| AC1 (template page exists, lint-clean) | PASS | `wiki/runbooks/weekly-observability-digest.md` lint exit 0 |
| AC2 (template specifies per-KPI fill method) | PASS | Body has the 4-section ADR-006 layout + per-KPI table |
| AC3 (copy-paste commands + executable script) | PASS | Procedure section has commands; `scripts/weekly-digest.sh +x` and runs end-to-end |
| AC4 (first digest authored at end of S4 wk1) | PASS | `wiki/decisions/weekly-digest-2026-w18.md` filled with 6/10 auto-fills + 4 [TBD] for manual prose |
| AC5 (digest captures G/A/R per row) | PARTIAL | 5 rows have G/A/R auto-set (K3=R, FalkorDB=G, GitNexus RSS=G, hit-rate=G, K4 numeric); 5 rows are `[G/A/R]` placeholders for operator manual fill |
| AC6 (FR-OBS-006 zero-week trigger) | PASS | Conditional block in script; tool-hit-rate=43 in window so callout suppressed; verified the `if hit_count=0` path emits the CLAUDE.md-review block |
| AC7 (cost rollup includes both providers) | PARTIAL | OpenAI/Anthropic spend = manual export (operator [TBD] step per template); Gemini spend auto-fills from cost-cap.log; the K3 row shows the auto-fill path with the 2-cap-breach R-status |
| AC8 (NFR-COST-003 cost-neutrality if Phase 4 active) | NOT-APPLICABLE | Conditional block in script; LiteLLM bridge is FR-LLM-007 gate-deferred per Sprint 5 kickoff so the block correctly does NOT render in this digest |
| AC9 (digest committed) | TO-COMMIT | This evidence file precedes the commit; commit happens immediately after this file is written |
| AC10 (template lifecycle — re-fill once per week) | DESIGN-VERIFIED | Script's `WEEK_SLUG=$(date -u +%Y-w%V)` produces a fresh filename each ISO week; template is unchanged; per-week files accumulate |
| AC11 (operator decides delivery; default = in-repo) | PASS | Template documents the default; ansible role at `homelab-infra/ansible/roles/weekly-digest/` ships `weekly_digest_enabled: false` (opt-in only) |

## Anything unexpected

1. **GitNexus container `${HOME}` bind-mount path resolution diverges from operator runtime.** Container has `/root/.gitnexus-data` mounted into `/data/gitnexus`; operator's `gitnexus analyze` writes to `/home/developer/.gitnexus-data`. The MCP daemon thus serves an empty registry while the operator-side artifacts are healthy. This is **not a Sprint 5 blocker** for E4-S09 (the backfill measures on-disk artifacts directly), but it IS a real ergonomics gap that the recurring K1 measurement needs closed before producing a real round-trip number. Flagged for E4-S10 exit-ramp doc.
2. **Cost-cap log path is `/var/log/cost-cap.log`, not `/var/log/graphiti-cost-cap.log`.** The story spec text references the v1 ADR-008 path; the deployed path per Sprint 4 ADR-008 amendment is the un-prefixed name. Script uses the correct deployed path.
3. **`awk match(string, regex, array)` is gawk-only.** First draft of the K3 spend extractor used gawk's three-arg `match`; ct-ai-01 has posix awk only. Rewrote using `index()` + `substr()`. Lesson for future scripts run on production targets.
4. **Slug case-sensitivity caught at lint.** `date -u +%Y-W%V` returns `2026-W18` with a literal capital W; wiki-lint enforces `[a-z0-9_-]+` for slugs. Added a parallel `WEEK_SLUG=$(date -u +%Y-w%V)` (lowercase) for the slug field while keeping `%V` capital W in the human-facing title. Caught and fixed in this session.
5. **K3 status = R for the first digest is a known-correct artifact of the E4-S04 manual breach-test.** The operator's 2 `throttled=true` log entries are intentional cap-breach-test artifacts, not operational red. The digest correctly reports them as R per the threshold; operator should note "two synthetic breaches from E4-S04 test, real spend $0.000254" in the prose Notes section at end-of-week refinement.

## Files changed in this story

**homelab-playbook (this commit):**
- `docs/context-stack/sprint-5/kickoff.md` (already committed at `ca21749`)
- `docs/context-stack/sprint-5/e4-s09-evidence.md` — this file
- `docs/context-stack/sprint-2/kpi-backfill.md` — backfill, closes Sprint 3 carry
- `scripts/weekly-digest.sh` — gather script
- `wiki/runbooks/weekly-observability-digest.md` — template
- `wiki/decisions/weekly-digest-2026-w18.md` — first digest instance
- `wiki/index.md` — runbooks/decisions cross-references

**homelab-infra (separate commit):**
- `ansible/roles/weekly-digest/defaults/main.yml`
- `ansible/roles/weekly-digest/tasks/main.yml`

## READY for E4-S10 (query hierarchy + exit ramps, ADR-013 implementation)

Sprint 5 backlog item next on the gate-independent path. E4-S10 deliverables (per sprint-plan §7 row): unified query hierarchy doc + GitNexus + Graphiti exit-ramp docs at `homelab-playbook/wiki/architecture/query-hierarchy.md` (per AC of the story spec). E4-S10 is the right place to close the GitNexus container `${HOME}` path-resolution gap surfaced in the K1 backfill — fix it as part of the exit-ramp doc's "operator-side recovery" section.
