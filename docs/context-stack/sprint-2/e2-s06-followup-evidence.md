# E2-S06 Follow-up Evidence

**Date:** 2026-04-26
**Closes:** Operator escalation items 1A (NFR re-baseline) + 2i (post.sh hook fix)
**Branch:** feature/context-stack-e2-gitnexus
**Companion to:** E2-S06 evidence (commit `a1eeb64`)

## ADR-016 — NFR-FOOTPRINT-002 re-baseline

- Path: `../../_bmad-output/planning-artifacts/products/context-stack/adrs/ADR-016-nfr-footprint-active-baseline.md`
- Old threshold: < 500 MB sustained RSS (idle-baseline, no empirical data behind it)
- New threshold: **< 2 GB sustained RSS in active state (≥1 indexed repo)** with no monotonic growth
- Idle expectation retained: < 500 MB (informational sub-criterion only)
- Scaling expectation: roughly 1 GB per 1 000 indexed files
- Rationale: original threshold was estimation artifact; measured idle 80 MB and measured active 1482 MB peak (no leak) across 30 samples × 30 s

## PRD amendment

`prd.md` §6.4 NFR-FOOTPRINT-002 row updated. Trace now includes ADR-016. Diff shape:

```
- < 500 MB. Process RSS sample over 24 h on workstation.
+ < 2 GB sustained RSS in active state (≥1 repo indexed) with no monotonic growth trend across a ≥15 min window.
+ Idle (zero repos) expectation: < 500 MB (informational, not gating).
+ Scaling: ~1 GB per 1 000 indexed files.
+ Measurement: RSS sampled at 30 s intervals over ≥15 min sustained-load window with MCP request every ≤10 s.
+ Re-baselined per ADR-016 (2026-04-26) after E2-S02 idle + E2-S06 active measurements showed the original cap was an estimation artifact.
```

## post.sh hook fix

The original hook (E2-S04) called MCP `detect_changes` on git-commit Bash payloads, which per Sprint 2 spike is **read-only** (maps git diff hunks against the existing graph but does NOT trigger reindex). The CLI subcommand `gitnexus analyze <path> --skip-agents-md` is the actual reindex primitive.

The agent fix (live on workstation at `/home/developer/.claude/hooks/gitnexus/post.sh`):
- Replaces the MCP `detect_changes` call with `timeout 3 docker exec gitnexus node /app/gitnexus/dist/cli/index.js analyze "$CONTAINER_PATH" --skip-agents-md` backgrounded with `&`+`disown`
- Adds payload `cwd` parsing → host→container path mapping (`/home/developer/workspace/homelab/<repo>` → `/data/source/<repo>`)
- Preserves all original design properties: fail-silent on connection error, 3 s wall-clock cap, git-commit-only filter, `--skip-agents-md` to honor E2-S05 carry-over
- Graceful skip if `cwd` is missing or outside the mounted root

### Hook test results (3/3 PASS)

| Test | Input | Result |
|---|---|---|
| Commit-style Bash with valid cwd | `{"tool":"Bash","args":{"command":"git commit -m test"}}` | exit 0 in 77 ms; background `analyze` ran successfully (homelab-playbook now in registry: 331 files, 4131 symbols, 4350 edges) |
| Non-commit Bash | `{"tool":"Bash","args":{"command":"ls -la"}}` | exit 0 in 4 ms; silent no-op as designed |
| Daemon-down resilience | container stopped, then commit payload | exit 0 in 79 ms; container restarted clean afterwards |

## Scenario 5 verdict update (under new threshold)

Original E2-S06 Scenario 5 verdict was FAIL on threshold. With ADR-016 re-baseline:

| | Measured (E2-S06) | Old threshold | New threshold | Verdict |
|---|---|---|---|---|
| PEAK RSS | 1482 MB | < 500 MB | < 2 GB | **PASS** |
| MEAN RSS | 1315 MB | (n/a) | (n/a) | informational |
| P95 RSS | 1480 MB | (n/a) | (n/a) | informational |
| Working-set trend | −212 MB across window | (no leak detector) | no monotonic growth | **PASS** |

Sprint 2 KPI scorecard at E2-S08 will reflect the corrected verdict.

## Sprint 2 carry-overs that this commit closes

- ✅ Item 1A (escalated from E2-S06): NFR re-baseline via ADR-016 + PRD amendment
- ✅ Item 2i (escalated from E2-S06): post.sh hook calls correct reindex primitive

## Sprint 2 carry-overs that remain

- E2-S07 (graph export wrapper for FR-CG-010 exit ramp) — pending
- E2-S08 (Week-1 decision gate / KPI scorecard) — pending
- Investigation of GitNexus 1.5 GB-on-883-files efficiency — Sprint 2 retro action item per ADR-016 §Alternatives §1
- E2-S04 carry-over: `--skip-agents-md` is honored by `analyze`, but the `gitnexus analyze` CLI still regenerates `.claude/skills/gitnexus/` SKILL.md files (separate from AGENTS.md/CLAUDE.md). Consider extending the .gitignore policy or filing an upstream issue for `--skip-skills` parity.
