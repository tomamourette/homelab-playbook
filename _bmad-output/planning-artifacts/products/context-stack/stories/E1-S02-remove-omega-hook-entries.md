---
type: story
epic: E1
id: E1-S02
title: "Remove OMEGA hook entries from settings.json"
size: 0.5d
priority: MUST
fr_refs: [FR-DEC-007]
adr_refs: [ADR-010]
status: draft
date: 2026-04-25
---

# E1-S02: Remove OMEGA hook entries from settings.json

## User Story

As **tomamourette** (homelab operator), I want **the four OMEGA hook entries fully removed from `~/.claude/settings.json` after the disable-only session has demonstrated zero regression**, so that **the workstation no longer references `omega/hooks/fast_hook.py` at all (FR-DEC-007 second half)**.

## Background and Context

E1-S01 disabled the four OMEGA hook entries and ran one safety-net Claude Code session to confirm nothing depends on them. ADR-010 §Decision commit 2 mandates the irreversible removal as a separate commit so the disable-then-remove split is preserved on the branch history. This story is **commit 2 of 8**.

## Acceptance Criteria

### AC1: All four OMEGA entries removed from settings.json

- **Given** E1-S01 has merged (or its commit exists on the branch) and the safety-net log at `/tmp/e1-s01-disable-session.log` shows no OMEGA-related errors
- **When** I delete the `_disabled_omega_hooks` block (or the in-place disabled entries) from `~/.claude/settings.json`
- **Then** `grep -c "fast_hook" ~/.claude/settings.json` returns `0` AND `grep -ci "omega" ~/.claude/settings.json` returns `0`

### AC2: settings.json remains valid JSON and Claude Code starts cleanly

- **Given** AC1 is complete
- **When** I run `python3 -c "import json; json.load(open('/home/developer/.claude/settings.json'))"` and start a fresh Claude Code session
- **Then** the JSON parse exits 0 AND the new session starts without referencing OMEGA in its boot transcript

### AC3: Hook scripts on disk are still present (deletion deferred to E1-S06)

- **Given** AC1 + AC2 pass
- **When** I check `~/.claude/scripts/omega-*.py`
- **Then** the four hook scripts may still exist on disk; this is correct — they are removed in E1-S06 (workstation cleanup) along with `~/.omega/`. This story removes only the *registration* in settings.json.

### AC4: Commit conforms to ADR-010 message format

- **Given** ACs 1–3 pass
- **When** I commit on the decommission branch
- **Then** commit message is exactly `decommission: remove OMEGA hook entries from settings.json` and the diff is restricted to `~/.claude/settings.json`

## Implementation Notes

- ADR-010 commit 2 of 8. This is the irreversible step that the E1-S01 safety net protects.
- Preserve a backup at `~/.claude/settings.json.pre-decommission.bak` for ≤ 7 days as a personal safety net (not committed).
- The disable→remove split exists specifically because the OMEGA entries imposed a session-start cost (per ADR-005 lesson) and the operator wanted one full session to confirm silence.
- After this commit, the *registration* is gone; the *scripts and pipx package* still exist and are handled in E1-S03 (uninstall package + role) and E1-S06 (workstation cleanup hooks scripts dir + `~/.omega/`).

## Test Plan

**Pre-test state check (require E1-S01 evidence):**
```bash
test -f /tmp/e1-s01-disable-session.log && echo "S01 evidence present"
grep -c "fast_hook" ~/.claude/settings.json   # expect 4 (still under _disabled_omega_hooks)
jq '._disabled_omega_hooks // empty' ~/.claude/settings.json   # not empty
```

**Action:** delete the disabled block from `~/.claude/settings.json`.

**Post-test state check:**
```bash
grep -c "fast_hook" ~/.claude/settings.json   # expect 0
grep -ci "omega" ~/.claude/settings.json      # expect 0
python3 -c "import json; json.load(open('/home/developer/.claude/settings.json'))" && echo OK
claude --help > /dev/null 2>&1 && echo "claude CLI OK"
```

**Optional confirmatory session:**
```bash
script -q /tmp/e1-s02-post-removal-session.log claude
# do one task; exit; verify no omega in log
grep -i omega /tmp/e1-s02-post-removal-session.log  # expect 0
```

**Rollback procedure (per ADR-010):**
```bash
git revert <sha-of-this-commit>   # restores the _disabled_omega_hooks block
# OR fall back to the .bak: cp ~/.claude/settings.json.pre-decommission.bak ~/.claude/settings.json
```

## Dependencies

- **Blocks:** E1-S03 (package uninstall makes more sense after the registration is gone)
- **Blocked by:** E1-S01 (must have safety-net session evidence)

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Removal breaks an unrelated session-start expectation that wasn't visible in the S01 safety net | Local `.bak` backup; `git revert` restores |
| Operator skips the S01 safety-net evidence | This story's pre-test check requires the S01 log file to exist |

## Definition of Done

- [ ] All ACs pass
- [ ] PR commit created with message `decommission: remove OMEGA hook entries from settings.json`
- [ ] Local `.bak` retained for 7 days (uncommitted)
- [ ] Verify task added to `tests/acceptance.md` as `AT-FR-DEC-007b`
