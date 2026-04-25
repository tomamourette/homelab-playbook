---
type: story
epic: E1
id: E1-S01
title: "Disable OMEGA hooks in ~/.claude/settings.json"
size: 0.5d
priority: MUST
fr_refs: [FR-DEC-007]
adr_refs: [ADR-010, ADR-005]
status: draft
date: 2026-04-25
---

# E1-S01: Disable OMEGA hooks in ~/.claude/settings.json

## User Story

As **tomamourette** (homelab operator), I want **the four OMEGA hook entries in `~/.claude/settings.json` disabled (commented or moved to a `_disabled` block) for one full Claude Code session before they are removed**, so that **I can prove the workstation runs clean without the OMEGA session-start contract before I take the irreversible step of deletion (FR-DEC-007 first half)**.

## Background and Context

OMEGA registered four Claude Code hook entries (SessionStart, Stop ×2, UserPromptSubmit, PostToolUse — all calling `omega/hooks/fast_hook.py`). Per ADR-005, OMEGA is being decommissioned because the MCP-first ecosystem won the bet against skill-first session-start contracts. ADR-010 §Decision commit 1 mandates a disable-then-remove split as the OMEGA safety net so the operator catches breakage before deletion. This story is **commit 1 of 8** in the single ADR-010 PR.

## Acceptance Criteria

### AC1: All four OMEGA hook entries are deactivated (not yet deleted)

- **Given** `~/.claude/settings.json` currently contains four entries that call `omega/hooks/fast_hook.py` (SessionStart, Stop, UserPromptSubmit, PostToolUse)
- **When** I edit settings.json to disable them (rename keys to `_disabled_<original>` or comment via JSON-with-comments if supported, or move to a `disabled_hooks` sibling block)
- **Then** `python3 -c "import json; d=json.load(open('/home/developer/.claude/settings.json'))" && grep -c "fast_hook.py" /home/developer/.claude/settings.json` returns 4 (entries still physically present) AND `jq '.hooks | tostring | contains("fast_hook")' /home/developer/.claude/settings.json` returns `false` (no longer mounted under `.hooks.*`)

### AC2: One full Claude Code session runs with hooks disabled and shows no regression

- **Given** the disable edit from AC1 is saved
- **When** I open one full Claude Code session in `~/workspace/homelab/homelab-playbook` and perform one representative task (e.g., read 2 files, run one Bash command, exit cleanly)
- **Then** no error messages reference `omega`, `fast_hook`, or session-start hook failures; transcript captured to `/tmp/e1-s01-disable-session.log` for evidence

### AC3: OMEGA daemon process check (informational; daemon may still run, that's S05/S06)

- **Given** AC1 + AC2 pass
- **When** I run `pgrep -fa "omega serve"` on the workstation
- **Then** if the daemon is running, that's expected (it is removed in E1-S05/E1-S06, not here); the disable touches hooks only

### AC4: Commit conforms to ADR-010 message format

- **Given** ACs 1–3 pass
- **When** I commit the change on the decommission branch
- **Then** commit message is exactly `decommission: disable OMEGA hooks (settings.json)` and the diff is restricted to `~/.claude/settings.json` (or a repo-managed copy of it)

## Implementation Notes

- ADR-010 commit 1 of 8. Do **not** delete the entries here — only deactivate.
- The four targets (verified earlier) are SessionStart, Stop ×2, UserPromptSubmit, PostToolUse, all referencing `omega/hooks/fast_hook.py`.
- Preferred deactivation: move under a top-level sibling key `_disabled_omega_hooks: { ... }` to keep the JSON valid and grep-able. Do NOT use comments — `settings.json` is strict JSON.
- The disable-only session in AC2 is the **safety net**: ADR-010 §Consequences explicitly calls this "a one-session 'is anything broken?' gate before the irreversible step."
- Branch convention from ADR-010: branch name `phase-1-decommission`; merge with **merge commit, not squash** (preserves per-commit revertability).

## Test Plan

**Pre-test state check:**
```bash
grep -c "fast_hook" ~/.claude/settings.json    # expect 4
jq -r '.hooks | keys[]' ~/.claude/settings.json | sort
pgrep -fa "fast_hook"                            # snapshot
```

**Action:** edit `~/.claude/settings.json` per Implementation Notes; save.

**Post-test state check:**
```bash
python3 -c "import json,sys; json.load(open('/home/developer/.claude/settings.json'))" && echo OK
grep -c "fast_hook" ~/.claude/settings.json    # still 4 (still present, just relocated)
jq '.hooks // {} | tostring | contains("fast_hook")' ~/.claude/settings.json   # false
```

**Run the safety-net session for AC2:**
```bash
script -q /tmp/e1-s01-disable-session.log claude --session-name=e1-s01-safety-net
# inside session: do one representative task (read README, run "ls", exit)
grep -iE "omega|fast_hook|session.?start.*fail" /tmp/e1-s01-disable-session.log    # expect 0 matches
```

**Rollback procedure (per ADR-010):**
```bash
git revert <sha-of-this-commit>   # restores fast_hook entries under .hooks
```
Per-commit revertability is preserved because the PR uses merge-commit, not squash.

## Dependencies

- **Blocks:** E1-S02 (cannot remove until disable-only session passes silent)
- **Blocked by:** none (this is commit 1 of 8)

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Disable changes JSON structure such that Claude Code refuses to start | Validate JSON before saving (`python3 -c "import json; json.load(open(...))"`); keep a `~/.claude/settings.json.pre-decommission.bak` for ≤ 24h |
| Operator forgets to actually run the safety-net session before commit 2 | AC2 is a hard gate; commit 2 (E1-S02) explicitly references the `/tmp/e1-s01-disable-session.log` evidence file |

## Definition of Done

- [ ] All ACs pass (AC1, AC2, AC3, AC4)
- [ ] PR commit created with message `decommission: disable OMEGA hooks (settings.json)`
- [ ] Safety-net session log archived at `/tmp/e1-s01-disable-session.log` (referenced by E1-S02)
- [ ] Verify task added to `tests/acceptance.md` (Phase 5a will populate; cross-reference here as `AT-FR-DEC-007a`)
- [ ] No regression in `MEMORY.md` auto-memory loading observed during the safety-net session
