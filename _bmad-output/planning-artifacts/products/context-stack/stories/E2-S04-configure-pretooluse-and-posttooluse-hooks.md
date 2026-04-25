---
type: story
epic: E2
id: E2-S04
title: "Configure PreToolUse + PostToolUse-on-commit hooks for auto-reindex"
size: 1d
priority: MUST
fr_refs: [FR-CG-004, FR-CG-005]
nfr_refs: [NFR-PERF-001, NFR-PERF-004]
adr_refs: [ADR-004, ADR-005, ADR-014]
status: draft
date: 2026-04-25
---

# E2-S04: Configure PreToolUse + PostToolUse-on-commit hooks for auto-reindex

## User Story

As **tomamourette**, I want **PreToolUse and PostToolUse-on-Bash-`git commit` hooks wired into `~/.claude/settings.json` so GitNexus auto-injects code-graph context before tool calls and auto-reindexes after every commit**, so that **the graph is always fresh without manual intervention (closing graphify's biggest operational gap per ADR-004) and Claude Code consistently has the freshest possible structural context every session**.

## Background and Context

FR-CG-004 mandates PreToolUse and PostToolUse hooks; FR-CG-005 (downgraded to COULD per ADR-014 but architecturally specified in §4.1 + §7.3 with default no-filter behaviour) specifies auto-reindex on every commit, no path or branch filter. `npx gitnexus setup` (run in E2-S03) likely already wrote the hook entries; this story validates they are present, fire on the right events, and meet the latency budgets in NFR-PERF-001 (overall session-start overhead < 1 s) and NFR-PERF-004 (incremental reindex < 30 s — measured for real in E2-S06 smoke test 4 but pre-flighted here). Architecture §7.3 is the spec; hook entries live in `~/.claude/settings.json` per architecture §7.3.

## Acceptance Criteria

**AC1 — Hook entries present and well-formed in settings.json.**
- **Given** E2-S03 ran `npx gitnexus setup` AND captured the post-state settings.json,
- **When** the operator runs `jq '.hooks // .Hooks // {}' ~/.claude/settings.json` (key name varies by Claude Code version),
- **Then** the output contains BOTH a `PreToolUse` entry referencing `gitnexus` AND a `PostToolUse` entry whose matcher targets `Bash` calls containing `git commit` (per architecture §7.3 row 2); both entries are valid JSON; both are syntactically aligned with the operator's known-good hook schema (cross-checked against the user's CLAUDE.md hook examples).

**AC2 — PreToolUse hook fires before tool calls (observability).**
- **Given** AC1 has passed,
- **When** the operator opens a fresh Claude Code session, asks a code-related question that triggers any tool (e.g., `Read /tmp/foo.txt` after creating that file), AND inspects the operator's hook log path (`~/.claude/logs/hooks/` or whichever path the harness emits — discoverable via `cat ~/.claude/settings.json | jq '.hooks.PreToolUse'`),
- **Then** at least one PreToolUse log entry exists for the session AND it references the gitnexus hook by name AND the entry timestamp is within 5 s of the session start.

**AC3 — PostToolUse-on-commit hook fires on `git commit`.**
- **Given** AC1 has passed AND the `~/workspace/homelab/` repo is the active working tree,
- **When** the operator (in a Claude Code Bash tool call) runs `git commit --allow-empty -m "test: E2-S04 hook smoke"` AND inspects the hook log,
- **Then** a PostToolUse log entry appears within 30 s of the commit AND it indicates a reindex was triggered AND `gitnexus` daemon RSS sample taken 30 s after commit shows expected post-reindex behaviour (RSS may rise transiently but settle within bounds set in E2-S02 baseline).

**AC4 — No-filter default per FR-CG-005.**
- **Given** AC3 has passed,
- **When** the operator inspects the PostToolUse hook configuration in settings.json AND the `gitnexus setup`-generated hook command,
- **Then** there is no path-filter or branch-filter constraint applied (no `--paths`, no `--branch`, no `--include`-style restrictor); the comment block in settings.json (or in the install script that re-applies it) explicitly notes "FR-CG-005 default no-filter; ADR-014 downgrade to COULD if filter needed in Sprint 2 follow-up".

**AC5 — Session-start latency budget held (NFR-PERF-001).**
- **Given** AC1 has passed,
- **When** the operator measures session-start time on 5 consecutive fresh sessions (`time claude --print "echo done" 2>&1` or equivalent timing harness) AND compares the median to a pre-hook baseline measured pre-AC1 (or against the post-E1 baseline if available),
- **Then** the additional latency contributed by the gitnexus hooks is < 1 s on the median session (per NFR-PERF-001) AND the value is recorded in `homelab-playbook/docs/decisions/gitnexus-hook-latency.md`.

**AC6 — Hook commands point to the pinned binary, not `latest`.**
- **Given** AC1 has passed,
- **When** the operator inspects every gitnexus-related command in settings.json (PreToolUse, PostToolUse, any matchers),
- **Then** every command invokes either `gitnexus@1.6.3` explicitly OR resolves to the global-install binary `which gitnexus` already pinned to 1.6.3 (no `npx gitnexus@latest` slips through); evidence: a one-line audit `grep -E 'gitnexus' ~/.claude/settings.json` showing zero `@latest` matches.

**AC7 — Hook removal is reversible (FR-DEP-007 spirit).**
- **Given** AC1–AC6 are green,
- **When** the operator demonstrates `cp ~/.claude/settings.json ~/.claude/settings.json.with-hooks.bak` AND running `jq 'del(.hooks.PreToolUse[] | select(.name | contains("gitnexus")))' ~/.claude/settings.json` (or the `claude mcp remove gitnexus` route if that also strips hooks) AND a post-removal grep `grep gitnexus ~/.claude/settings.json` returns zero matches AND the file restored from backup re-enables hooks,
- **Then** the round-trip works AND the time-to-disable hooks is < 60 s (per NFR-MAINT-001 reversibility).

## Implementation Notes

**Reference architecture sections:** §7.3 Hooks — what fires when (the spec table), §4.1 Code-graph layer (PreToolUse + PostToolUse listed), §11 G-Latency risk note, §5.4 Backup and recovery (gitnexus index is rebuildable, so hook misbehaviour is recoverable by stop-daemon + reindex-on-restart).

**Reference ADRs:** ADR-004 (PostToolUse-on-commit auto-reindex is the "biggest operational gap closure"), ADR-005 (MCP-first, no skill scaffolding), ADR-014 (FR-CG-005 downgrade to COULD — if reindex is too chatty, filtering becomes a Sprint 2 follow-up not a launch story).

**Concrete commands:**

```bash
# AC1 — inspect hooks
jq '.hooks // .Hooks // {}' ~/.claude/settings.json
jq '.hooks.PreToolUse, .hooks.PostToolUse' ~/.claude/settings.json | grep -i gitnexus

# AC2 — trigger PreToolUse
echo "test" > /tmp/foo.txt
# in a Claude Code session: prompt "read /tmp/foo.txt"
ls -la ~/.claude/logs/hooks/  # discover hook log location
tail -50 ~/.claude/logs/hooks/*.log | grep -i 'PreToolUse.*gitnexus'

# AC3 — trigger PostToolUse-on-commit
cd ~/workspace/homelab/
git commit --allow-empty -m "test: E2-S04 hook smoke"
sleep 5
tail -50 ~/.claude/logs/hooks/*.log | grep -iE 'PostToolUse.*gitnexus|reindex'

# AC4 — confirm no filter
jq '.hooks.PostToolUse[] | select(.command? | tostring | contains("gitnexus"))' ~/.claude/settings.json
# expect no --paths / --branch / --include args

# AC5 — latency baseline (run 5x, take median)
for i in 1 2 3 4 5; do
  time claude --print "echo done" 2>&1 | tail -3
done

# AC6 — pin audit
grep -E 'gitnexus.*@latest' ~/.claude/settings.json && echo "FAIL: latest tag found" || echo "PASS"

# AC7 — reversibility round-trip
cp ~/.claude/settings.json ~/.claude/settings.json.with-hooks.bak
jq 'del(.hooks.PreToolUse[]? | select((.command? // "") | contains("gitnexus")))
    | del(.hooks.PostToolUse[]? | select((.command? // "") | contains("gitnexus")))' \
   ~/.claude/settings.json > /tmp/settings-no-gitnexus.json
mv /tmp/settings-no-gitnexus.json ~/.claude/settings.json
grep gitnexus ~/.claude/settings.json   # expect empty
mv ~/.claude/settings.json.with-hooks.bak ~/.claude/settings.json   # restore
```

**Evidence note path:** `homelab-playbook/docs/decisions/gitnexus-hook-latency.md`. Contents: hook entries (verbatim JSON), PreToolUse log line evidence, PostToolUse-on-commit log line evidence, 5-sample session-start latency table with median, no-filter audit, removal round-trip wall-time.

## Test Plan

**Pre-state:**
- E2-S03 done; `claude mcp list` shows `gitnexus healthy`.
- E2-S02 baseline RSS captured.
- `~/workspace/homelab/` is the active working tree.

**Action sequence:**
1. Inspect hooks in settings.json (AC1).
2. Trigger PreToolUse via a `Read` tool call (AC2).
3. Trigger PostToolUse via empty `git commit` (AC3); confirm reindex log line.
4. Audit hook command for path/branch filters (AC4).
5. Time 5 fresh sessions; compute median; confirm < 1 s overhead (AC5).
6. Audit for `@latest` (AC6).
7. Round-trip reversibility test (AC7); restore.
8. Update evidence note.

**Post-state checks:**
- Hook entries present and well-formed.
- Hook log shows PreToolUse + PostToolUse-on-commit firing.
- No `@latest` references.
- Median session-start overhead < 1 s.
- Round-trip successful in < 60 s.

**Rollback:**
- Restore from `~/.claude/settings.json.with-hooks.bak` (or, if pre-hook backup exists from E2-S03, restore that).
- Wall-time: < 1 minute.
- Combined with E2-S03 rollback: workstation back to post-E1 state.

## Dependencies

- **Blocked by:** E2-S03 (MCP must be registered for hook commands to make sense).
- **Blocks:** E2-S05 (topology test relies on hooks firing on real commits in `~/workspace/homelab/`), E2-S06 (smoke test 4 measures incremental reindex timing — needs hooks live), E2-S08 (week-1 KPI gate measures K2 reindex timings from hook logs).

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| `npx gitnexus setup` wrote hooks in a non-standard schema (mismatch with operator's CLAUDE.md hook conventions). | Med | Med — hooks may not fire under Claude Code's matcher rules. | AC1 cross-checks schema against operator's known-good examples; if mismatched, operator hand-rewrites the entries to match Claude Code's PreToolUse/PostToolUse spec while preserving the gitnexus command. |
| PreToolUse hook adds > 1 s session-start latency (G-Latency risk per architecture §11). | Med | High — fails NFR-PERF-001; story must reduce hook scope. | AC5 measures; if > 1 s, scope down PreToolUse to fire only on specific tool matchers (e.g., `Read`, `Bash` only) and re-measure. Document any scoping in the evidence note. |
| PostToolUse-on-commit fires too eagerly (every Bash, not just `git commit`). | Low | Med — reindex storm. | AC3 + AC4 explicitly inspect the matcher; if too broad, edit matcher regex to `^git commit\b`. |
| Hook log path differs by Claude Code version. | Low | Low — discoverability friction. | AC2 includes `ls -la ~/.claude/logs/hooks/` discovery step; document the path used in the evidence note. |
| Reindex on every commit becomes too chatty in operator's daily workflow. | Med | Low — quality-of-life issue. | ADR-014 explicitly downgraded FR-CG-005 to COULD; if reindex storm bothers operator post-Sprint 2, file a backlog ticket for path/branch filter — DO NOT widen this story. |

## Definition of Done

- [ ] AC1–AC7 all green and evidenced.
- [ ] `homelab-playbook/docs/decisions/gitnexus-hook-latency.md` committed.
- [ ] `~/.claude/settings.json` has PreToolUse + PostToolUse-on-commit gitnexus entries; pinned to v1.6.3.
- [ ] Hook log captures evidence of both hooks firing on real triggers.
- [ ] Median session-start overhead < 1 s.
- [ ] Story status updated to `done`; OMEGA `omega_store(...)` records hook latency baseline.
