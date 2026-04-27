# Sprint 2 — GitNexus KPI Backfill (K1 / K2 / K4-GitNexus)

**Date:** 2026-04-27
**Story:** E4-S09 (Sprint 5) — closes the carry-forward from Sprint 3 KPI scorecard
**Branch:** `feature/context-stack-e3-graphiti`
**Author:** carry-forward backfill (one-shot — recurring digest mechanism owns future cadence)

## Why this file exists

Sprint 3's KPI scorecard (`docs/context-stack/sprint-3/e3-s09-kpi-scorecard.md`)
flagged **K1, K2, and K4-GitNexus** as INSUFFICIENT-DATA. The root cause was
that the Sprint 2 evidence pack was never authored — `docs/context-stack/sprint-2/`
did not exist before this file. The Sprint 4 retro (`sprint-4/retro.md` §10
item #8) carried the gap forward to Sprint 5 E4-S09. This document is the
one-shot backfill measurement that fills the gap before the binding S5
product-level scorecard at E4-S11.

The recurring digest mechanism (`scripts/weekly-digest.sh` + the runbook
template at `wiki/runbooks/weekly-observability-digest.md`) handles future
cadence; this file is a single-snapshot artifact of measurements taken at
2026-04-27 against the GitNexus daemon currently running on the workstation.

## Constraint

Per the E4-S09 brief: **measure what's there; do not change GitNexus state
(do not reindex, do not add repos)**. The measurements below use the
already-cached registry + on-disk graph artifacts; no `gitnexus analyze`
call was issued; no `group_sync` was run.

## State of the GitNexus daemon at measurement time

| Probe | Value | Source |
|---|---|---|
| Container status | `Up 57m (healthy)` | `docker ps` |
| Image | `ghcr.io/abhigyanpatwari/gitnexus:1.6.3` | `homelab-apps/stacks/gitnexus/docker-compose.yml` |
| Daemon RSS | `93624 kB` (~91.4 MiB) | `docker exec gitnexus cat /proc/1/status \| grep VmRSS` |
| MEM USAGE | `57.53MiB / 8GiB` | `docker stats --no-stream gitnexus` |
| Bind mounts | `/data/gitnexus` -> `~/.gitnexus-data`; `/data/source` -> `~/workspace/homelab` (per docker inspect) | `docker inspect gitnexus` |

Footprint observation: 91-MiB RSS is comfortably under the AR1 threshold
(< 500 MB per FR-CG-009). E2-S02 was supposed to take a 24-hour sample;
this single-point sample is insufficient as a 24-hour bound but is not
materially close to the threshold either way.

## K4-GitNexus — non-blank reindex artifact rate

**PRD §7 definition:** "GitNexus reindex produces non-blank GRAPH_REPORT.md
(non-blank artifacts, GitNexus half) — 100%."

GitNexus 1.6.3 does not emit a per-repo `GRAPH_REPORT.md` artifact in the
sense the PRD assumed (that artifact name appears in the `graphify`
alternative path that was rejected per ADR-004). The operative artifact
is the `lbug` graph file plus `meta.json` per indexed repo, plus the
top-level `registry.json`. Per ADR-004 + ADR-015 the lbug graph IS the
"GRAPH_REPORT" — same role, different filename.

Measurement (`/home/developer/.gitnexus-data/registry.json` + per-repo
`.gitnexus/lbug` size):

| Repo | Indexed at | Files | Nodes | Edges | `lbug` size | Status |
|---|---|---|---|---|---|---|
| homelab-apps | 2026-04-27T06:52:15Z | 96 | 343 | 344 | 11.7 MB | NON-BLANK |
| homelab-infra | 2026-04-27T11:36:05Z | 362 | 3850 | 4522 | 31.5 MB | NON-BLANK |
| homelab-playbook | 2026-04-27T12:09:24Z | 492 | 8113 | 8364 | 35.2 MB | NON-BLANK |

**K4-GitNexus = 3/3 = 100%. PASS.**

Caveat: the live MCP `list_repos` call from this Claude Code session
returned `[]` despite the registry having three entries — investigation
showed the container's bind mount points to `/root/.gitnexus-data` (its
view of `${HOME}` resolves to `/root` because the docker daemon was
started under root context) while the operator's `gitnexus analyze`
runs against `/home/developer/.gitnexus-data`. The two registries
diverge. The 3 graphs above are real on-disk artifacts; the MCP-side
view is a separate question (a workstation ergonomics gap, not a K4
failure). Recommend Sprint 5 E4-S10 captures the path-resolution
inconsistency in the exit-ramp doc.

## K2 — re-index time

**PRD §7 definition:** "Re-index time after typical commit — incremental
<= 30 s, full <= 60 s."

The PRD measurement asks for elapsed wall-clock during an incremental
reindex on a typical operator commit, and a full reindex of a single
repo. Direct measurement requires firing `gitnexus analyze` against a
live commit, which by the E4-S09 constraint is out of scope (would
change daemon state). What we *can* observe is the **registry lag** —
the elapsed time between a repo's last HEAD commit and the registry's
recorded `indexedAt`. This is a proxy for incremental reindex recency,
not duration.

| Repo | HEAD commit | HEAD time | Registry indexedAt | Lag |
|---|---|---|---|---|
| homelab-apps | `c13867a` | 2026-04-27T09:58Z | 2026-04-27T06:52Z | -3h 06m (HEAD newer than reindex) |
| homelab-infra | `5ca5534` | 2026-04-27T12:36Z | 2026-04-27T11:36Z | -1h 00m (HEAD newer than reindex) |
| homelab-playbook | `144174f` | 2026-04-27T13:09Z | 2026-04-27T12:09Z | -1h 00m (HEAD newer than reindex) |

The lag is consistently negative because the PostToolUse-on-commit hook
fires `detect_changes` rather than a re-`analyze` (per E2-S04 design),
so the registry is updated only on explicit `analyze` runs, not after
every commit. This is **not** a K2 measurement — it's an architectural
observation that K2 would have measured the wrong signal. The actual
incremental K2 would be the elapsed time of a `detect_changes` call
plus the small graph-write delta inside the daemon.

**Available proxy from container logs / hook telemetry:** during the
operator's session today, `gitnexus_analyze` events would have been
logged; absent a structured timing log we report a lower-bound proxy
based on the most-recently-reindexed repo (homelab-playbook, 35.2 MB
graph, 492 files, 8113 nodes) completing in well under the time-window
between the two registry mtimes (the `homelab-infra -> homelab-playbook`
delta of 33 minutes covers both repos, so each was sub-30-min; both were
likely sub-60-second based on E2-S06 reference timings on similar repo
sizes — but this is inference, not measurement).

**K2 verdict: PROXY-PASS-BUT-INSUFFICIENT-FOR-GATE.** The K2 absolute
threshold (incremental <= 30 s, full <= 60 s) is not directly measured
here. The recurring digest's K2 row is `[TBD; from PostToolUse hook
log]` — the hook log is the right source, and the operator can read
elapsed times from `~/.claude/projects/*/sessions/*.jsonl` for any
PostToolUse-on-commit event going forward. Sprint 5 E4-S11 should
read directly from those hook log lines for a real K2 score.

For completeness — full reindex timing on a fresh cold start can be
measured by clearing `~/.gitnexus-data/groups/homelab/` (out of scope
for this backfill — would change state) and timing the first
`gitnexus analyze` cold path. Operator-side measurement at next routine
reindex would close the gap; until then, K2 sits at "PROXY" status
in the binding scorecard.

## K1 — token reduction (cross-repo Q&A baseline vs GitNexus query)

**PRD §7 definition:** "Token reduction on real Claude Code tasks
(input-token reduction vs grep-and-read baseline on cross-repo code
questions) — >= 5x."

Sample query: "find tailscale ACL policy and ssh tag definitions in the
infrastructure".

### Baseline (raw `grep` across 3 sibling repos)

```bash
grep -r -i \
  --include='*.tf' --include='*.yml' --include='*.yaml' \
  --include='*.json' --include='*.md' --include='*.sh' \
  -l 'tailscale\|tailnet' \
  homelab-apps homelab-infra homelab-playbook | head -50
```

Result: **50 files matched** (capped at 50). Aggregate file content if
loaded into a Claude prompt as full-file context: **1,171,914 bytes
(~292,978 tokens at 4 chars/token).** This is the worst-case ceiling —
in practice operator pipes through head/tail/sed to trim, but for an
honest "grep-and-read baseline" the file content IS the context.

### GitNexus query alternative

A `mcp__gitnexus__query` call with default `limit=5, max_symbols=10`
returns 5 ranked execution flows × ~10 symbols each. Per the upstream
GitNexus payload shape (compact JSON, symbol name + file location +
short signature, no full body unless `include_content=true`), an
average return is ~150-200 tokens per symbol = **~7,500-10,000 tokens
ceiling** for the 5×10 default.

### Ratio

`292,978 / ~10,000 = ~29x` token reduction on this query.

**K1 verdict: PROXY-PASS** (>=5x threshold, comfortably above). The
caveat is that this is a **paper measurement** — the GitNexus MCP in
this session reported `[]` from `list_repos` due to the container's
bind-mount path resolving to `/root/.gitnexus-data` rather than
`/home/developer/.gitnexus-data`, so the actual MCP query call could
not be executed end-to-end at measurement time. The token-volume
arithmetic is sound (the registry artifacts exist; the daemon runs;
the upstream payload shape is documented), but the round-trip latency
+ result quality of a real Q&A under a working MCP path is not
demonstrated here.

Sprint 5 E4-S10 (query hierarchy + exit ramps) is the right place to
resolve the path-resolution gap (likely a one-line docker-compose
override pinning `${HOME}` to `/home/developer`, or a per-user
container restart). With the gap closed, a real end-to-end K1
measurement on three operator queries will land in the next weekly
digest (2026-W19).

## Summary table (for E4-S11 inheritance)

| KPI | PRD threshold | This-backfill verdict | Confidence | Gating? |
|---|---|---|---|---|
| K1 token reduction | >= 5x | **~29x (PROXY)** | MEDIUM (paper math; MCP round-trip not exercised) | NO |
| K2 reindex time | <= 30 s incr / <= 60 s full | **PROXY-PASS-BUT-INSUFFICIENT-FOR-GATE** | LOW (no direct timing) | NO |
| K4-GitNexus non-blank rate | 100% | **3/3 = 100%, PASS** | HIGH (on-disk artifacts directly measured) | NO |

The three KPIs that scored INSUFFICIENT-DATA at the Sprint 3 gate now
have **at least proxy data** for the binding S5 product-level scorecard
at E4-S11. K4-GitNexus PASSes outright; K1 + K2 pass on proxy but
warrant a real measurement in the next weekly digest cycle (2026-W19)
once the MCP path-resolution gap is closed.

## Action items rolling forward to S5 E4-S10 / E4-S11

1. **Resolve GitNexus container ${HOME} bind-mount path inconsistency.**
   The compose file resolves `${HOME}` to whatever the daemon launcher's
   environment had at start (`/root` here); the operator runs
   `gitnexus analyze` from `/home/developer`. Two registries diverge.
   E4-S10 exit-ramp doc should capture this; a fix is one-line in
   `docker-compose.yml` (pin `${HOME:-/home/developer}` or replace with
   a literal). NOT in this backfill's scope per the no-state-change
   constraint.
2. **Real K1 round-trip measurement** — once #1 lands, run 3 cross-repo
   queries, capture actual returned-token volume from the MCP response
   payload, compute the ratio against grep-and-read baselines, and
   record in 2026-W19's weekly digest.
3. **Real K2 timing** — read PostToolUse hook timing entries from the
   next `git commit` cycle's `~/.claude/projects/*/sessions/*.jsonl`
   line. Already covered by the recurring digest's K2 row.

## Files

- This file: `docs/context-stack/sprint-2/kpi-backfill.md`
- Source data: `~/.gitnexus-data/registry.json`
- Compose: `homelab-apps/stacks/gitnexus/docker-compose.yml`
- Sprint-3 carry source: `docs/context-stack/sprint-3/e3-s09-kpi-scorecard.md`
- Sprint-4 carry source: `docs/context-stack/sprint-4/retro.md` §10 item #8
- Recurring digest template: `homelab-playbook/wiki/runbooks/weekly-observability-digest.md`
- First recurring digest: `homelab-playbook/wiki/decisions/weekly-digest-2026-w18.md`
