---
adr: 010
title: "Decommission MemPalace + OMEGA in a single PR with sequenced commits"
status: accepted
date: 2026-04-25
authors: tomamourette (via BMAD director Claude)
context_question: null
---

# ADR-010: Decommission MemPalace + OMEGA in a single PR with sequenced commits

## Context

Phase 1 of Context Stack is the decommission of two dormant tools:

- **OMEGA**: 4 Claude Code hook entries in `~/.claude/settings.json`, the `ai-dev-omega-memory` Ansible role, `omega-memory` Python package, group_vars in dev_hosts container playbook.
- **MemPalace**: `~/.mempalace/` workstation store, `ai-dev-mempalace` Ansible role, three Hermes skills, `wire-mempalace.yml`, conditional blocks in three Hermes Jinja files, the degenerated `knowledge-query` orchestrator.

Three structural choices exist for sequencing:

A. **Single big-bang PR** — all of FR-DEC-* in one commit. Lowest review fragmentation but highest blast radius.
B. **Two PRs (OMEGA first, then MemPalace)** — staggered; lets the operator catch surprises before doing the second.
C. **Single PR, multiple commits** — one branch, one review, but commits sequenced so partial revert is possible.

The decommission is wide-surface (FR-DEC-005 edits three Hermes Jinja files; risk R7 in PRD §10). It also does not need to be reversible-mid-flight — the rollback path (FR-DEP-007) is "reinstall from prior commit" not "selectively unwind". The operator is single-reviewer, so PR-count is not a coordination issue.

## Decision

**Single PR, with the work split into sequenced commits in this order:**

1. `decommission: disable OMEGA hooks (settings.json)` — disable only, do not remove. Verifies one Claude Code session runs clean (FR-DEC-007 first half).
2. `decommission: remove OMEGA hook entries from settings.json` — full removal. (FR-DEC-007 second half).
3. `decommission: uninstall omega-memory Python package + remove ai-dev-omega-memory role + group_vars` — workstation + dev_hosts. (FR-DEC-008).
4. `decommission: remove MemPalace store + role + skills` — `~/.mempalace/`, `ai-dev-mempalace`, three Hermes skills. (FR-DEC-001 through FR-DEC-003).
5. `decommission: remove MemPalace wiring (wire-mempalace.yml + knowledge-query)` — the orchestrator wiring. (FR-DEC-004, FR-DEC-006).
6. `decommission: remove mempalace conditionals from Hermes Jinja templates` — `config.yaml.j2`, `defaults/main.yml`, `verify.yml`. (FR-DEC-005). **The riskiest commit; isolated for review.**
7. `decommission: write Phase-1 decommission doc` — captures every action taken + the FR-DEC-012 "no-data-migration" record (PRD §14 glossary "Decommission doc").
8. `decommission: run Hermes verify on ct-dev-homelab; commit verify-output as evidence` — FR-DEC-011 + FR-DEP-006 first half.

Each commit is independently revertable via `git revert <sha>` if a regression surfaces in the workflow window between the commit and the PR merge. After merge, FR-DEP-007 rollback is the contract.

Tag the merged commit `phase-1-decommission-complete` so the rollback target is grep-able.

## Consequences

**Positive.**
- Single PR = single review surface for the operator (the only reviewer); no context-switching between PRs that touch overlapping config.
- Sequenced commits give a granular `git revert` capability during the review window; the riskiest commit (Hermes Jinja edits) is isolated.
- The disable-then-remove split for OMEGA hooks (FR-DEC-007) is captured as two commits, giving a one-session "is anything broken?" gate before the irreversible step.
- Tagged final commit makes the rollback target explicit.

**Negative.**
- Big-PR review tax — ~10 file deletions, ~3 file edits, plus the decommission doc. Mitigated by the commit-level granularity.
- A mid-PR mistake that's discovered post-merge requires `git revert` of the *PR-merge commit* (which reverts everything), not of an individual commit (because squash-merge collapses the sequence). Recommendation: **merge with merge commit, not squash**, so the per-commit revertability is preserved on `main`.

**Neutral.**
- The decommission doc itself (commit 7) is the record FR-DEC-012 mandates.

## Alternatives Considered

1. **Two PRs (OMEGA, then MemPalace)** — rejected. The Hermes Jinja edits (FR-DEC-005) reference *both* tools' conditionals; splitting them into two PRs creates an awkward intermediate state where one half of the conditionals is removed and the other isn't. Single-PR avoids the half-state.
2. **Big-bang single commit** — rejected. Loses the disable-first-then-remove safety net for OMEGA hooks; no granular revert for the Hermes Jinja commit.
3. **Phased over multiple sprints** — rejected. The decommission is the gate to Phase 2; delaying it delays adoption signal. Brief §4.3 makes Phase 1 a single sprint (Sprint 1 in the 4-sprint plan).

## Validation / Exit Ramp

- **Validation:**
  - After each commit in the sequence, `npx claude-flow doctor` (or local equivalent — direct `claude mcp list` + `pgrep` checks) verifies nothing broke.
  - After commit 8, the Hermes verify run on `ct-dev-homelab` exits 0 (FR-DEC-011 + FR-DEP-006).
  - After the PR merges, `grep -r -i 'mempalace\|omega' homelab/` (excluding decommission doc + git history + `_bmad-output/`) returns zero matches (FR-DEC-009).
- **Exit ramp:** if any commit-level regression survives the immediate `git revert` window, the merged-PR rollback per FR-DEP-007 (re-install OMEGA + MemPalace from prior commit on the tagged release) is the documented escape.
- **Reversal trigger:** if `git revert` on the merge commit is exercised, file an incident note in the wiki under `runbooks/decommission-revert.md` and reopen the Phase 1 epic.

## References

- PRD FR-DEC-001 through FR-DEC-012, FR-DEP-007
- Brief §7 (decommission targets), §10.1 R7 (decommission breakage risk)
- Project rule (CLAUDE.md): "create a NEW commit rather than amending"
