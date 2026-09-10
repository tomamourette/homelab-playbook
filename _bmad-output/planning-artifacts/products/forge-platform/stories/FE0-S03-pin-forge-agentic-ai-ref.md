---
type: story
epic: FE0
id: FE0-S03
title: "Pin FORGE_AGENTIC_AI_REF to a tag in coder_agent.main.env"
size: XS
priority: MUST
owner: dev
blocking: false
fr_refs: [FR-PRE-004]
nfr_refs: []
adr_refs: []
risk_refs: []
status: done
date: 2026-09-09
---

# FE0-S03: Pin FORGE_AGENTIC_AI_REF to a tag in coder_agent.main.env

## User Story

As **tomamourette**, I want **`FORGE_AGENTIC_AI_REF` pinned to a specific tag rather than left floating on a branch**, so that **a merge to `agentic-ai`'s `main` branch during the PoC cannot silently change what the workspace clones mid-flight, corrupting the PORTS/DOES-NOT-PORT verdict**.

## Background and Context

`FORGE_AGENTIC_AI_REF` lives in `coder_agent.main.env` at `coder/templates/forge/main.tf:160-162` (verified fact, canon). This proposal (§3.4 "Agreements, adopted unchanged") explicitly carries forward the prior findings document's recommendation to pin this ref, unchanged. The reasoning is narrow but important: the PoC's entire purpose is to produce a **dated, falsifiable verdict** (§1 of the sprint-change-proposal). If `agentic-ai`'s default branch moves between FE3-S06 (image build + template push) and FE4-S02 (acceptance gates), the workspace created in FE4-S01 could clone a different tree than the one the acceptance gates were designed against, and the eventual verdict would be undated in substance even if dated on the calendar.

This is a small, isolated, single-line change and carries no operator dependency — it can proceed as soon as a decision is made about which `agentic-ai` tag to pin to (the current tip commit `87ec24a`, per canon, is a reasonable candidate if no tag exists yet at that commit).

## Acceptance Criteria

**AC1 — Ref pinned to an immutable tag, not a branch.**
- **Given** `agentic-ai @ 87ec24a` is the repo HEAD verified for this pass,
- **When** the dev either finds an existing git tag at or near that commit, or creates one (e.g. `git tag forge-poc-2026-09-09 87ec24a && git push origin forge-poc-2026-09-09` in `agentic-ai`, with the operator's approval since it is a git-state-changing action against an external repo),
- **Then** `coder/templates/forge/main.tf:160-162`'s `FORGE_AGENTIC_AI_REF` value is set to that tag name (not `main`, not a floating branch name).

**AC2 — `terraform validate` still passes.**
- **Given** AC1's edit is made on the forge-platform PoC branch,
- **When** the dev runs `terraform validate` inside `coder/templates/forge/`,
- **Then** the command exits 0 with no new errors introduced by this change.

**AC3 — Value is a plain string literal, not a `coder_parameter`.**
- **Given** the intent is to remove operator discretion over this value during the PoC (not add a knob),
- **When** the dev inspects the edited line,
- **Then** `FORGE_AGENTIC_AI_REF` remains a fixed environment-variable value in `coder_agent.main.env`, not converted into a mutable `coder_parameter` (that would reintroduce the exact drift this story exists to prevent).

## Implementation Notes

Reference proposal §3.4 (agreements adopted unchanged), canon fact table row `FORGE_AGENTIC_AI_REF lives in coder_agent.main.env` (`main.tf:160-162`). No runbook applies — this is a forge-platform repo edit, not a homelab-infra/Ansible change.

```bash
# Inspect current value
grep -n "FORGE_AGENTIC_AI_REF" repos/forge-platform/coder/templates/forge/main.tf

# If no tag exists yet at the verified HEAD, operator approves creating one:
cd repos/agentic-ai
git tag forge-poc-2026-09-09 87ec24a
git push origin forge-poc-2026-09-09

# Edit main.tf:160-162 to reference the tag instead of `main` (or whatever it currently tracks)
```

## Test Plan

**Pre-state:** `FORGE_AGENTIC_AI_REF` tracks a floating branch (verify current value before editing).

**Action sequence:**
1. Confirm or create an immutable tag in `agentic-ai` at the verified commit (AC1).
2. Edit `main.tf:160-162` to reference the tag (AC1).
3. Run `terraform validate` (AC2).
4. Confirm the value remains a plain env-var string, not a `coder_parameter` (AC3).

**Post-state checks:**
- `grep FORGE_AGENTIC_AI_REF main.tf` shows a tag name, not `main` or another branch.
- `terraform validate` exits 0.

**Rollback:** `git checkout -- coder/templates/forge/main.tf` on the forge-platform branch; delete the pushed tag with `git push origin :refs/tags/<tag>` if it was newly created and no longer wanted.

## Dependencies

- **Blocked by:** FE0-S01 and FE0-S02 per §5.4 (this story is FE0, not FE1+, but the canon's blocking language is scoped to FE1–FE4; this story may proceed in parallel with FE0-S01/S02 since it touches neither credential).
- **Blocks:** FE3-S06 (image build + template push) benefits from this being resolved first, so the build that gets pushed is against a known-fixed ref, but does not hard-block it.

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| No existing tag near `87ec24a`; creating one requires push access and operator sign-off on an external repo | Low | Low | AC1 explicitly calls for operator approval before pushing a new tag |
| Pinning to a stale ref means bug fixes in `agentic-ai` main are not picked up during the PoC | Medium | Low — acceptable per PoC's scope; a re-pin is a one-line change if needed | Document the pinned tag in the story's Definition of Done so a re-pin is a deliberate, visible act |

## Definition of Done

- [ ] AC1–AC3 all green and evidenced.
- [ ] `FORGE_AGENTIC_AI_REF` set to an immutable tag in `coder/templates/forge/main.tf:160-162`.
- [ ] `terraform validate` passes in `coder/templates/forge/`.
- [ ] The pinned tag name recorded in this file's Definition of Done for future reference.
- [ ] Story status updated from `draft` to `done` in this file's frontmatter.
