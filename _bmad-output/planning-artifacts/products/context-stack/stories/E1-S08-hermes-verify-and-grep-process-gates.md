---
type: story
epic: E1
id: E1-S08
title: "Hermes verify run on ct-dev-homelab + grep/process gates"
size: 1d
priority: MUST
fr_refs: [FR-DEC-009, FR-DEC-010, FR-DEC-011, FR-DEP-006]
adr_refs: [ADR-010]
status: draft
date: 2026-04-25
---

# E1-S08: Hermes verify run on ct-dev-homelab + grep/process gates

## User Story

As **tomamourette** (homelab operator), I want **the Hermes `verify.yml` run end-to-end on `ct-dev-homelab` exiting 0, the repo-wide grep for `mempalace|omega` returning 0, and `pgrep` on workstation + container returning 0**, so that **the Phase-1 cleanup is empirically verified before tagging the merge commit (FR-DEC-009, FR-DEC-010, FR-DEC-011)**.

## Background and Context

ADR-010 §Validation makes this story the binding empirical gate for the Phase-1 PR — a passing Hermes verify run on `ct-dev-homelab` is what lets the operator merge with confidence. PRD §10 R7 names this run as the mitigation for the Hermes-Jinja-edit risk (E1-S06). This is **commit 8 of 8** and produces the verify-run evidence that gets appended to the E1-S07 doc.

## Acceptance Criteria

### AC1: Hermes verify.yml exits 0 on ct-dev-homelab

- **Given** commits 1–7 of the decommission branch are in place
- **When** I run `ansible-playbook -i homelab-infra/ansible/inventories/homelab homelab-infra/ansible/playbooks/deploy-hermes.yml --limit ct-dev-homelab --tags verify` (or the equivalent verify-only invocation per the role's existing pattern)
- **Then** the playbook exits 0 AND no task references `mempalace` or `omega` AND no `failed=` count > 0 AND no Jinja `UndefinedError` is raised

### AC2: Repo-wide grep gate returns 0 (FR-DEC-009)

- **Given** AC1 passes
- **When** I run the FR-DEC-009 grep gate from the workspace root:
  ```bash
  grep -r -i 'mempalace\|omega' homelab/ \
    --exclude-dir=.git \
    --exclude-dir=_bmad-output \
    --exclude-dir=docs/decommission \
    | grep -v '^Binary file'
  ```
- **Then** the result is 0 matches (the decommission doc, `_bmad-output/` planning artifacts, and `.git/` history are sanctioned exceptions per FR-DEC-009)

### AC3: Workstation pgrep returns 0 (FR-DEC-010 part 1)

- **Given** AC1 passes
- **When** I run `pgrep -fa 'mempalace\|omega' && echo NONZERO || echo ZERO` on the workstation
- **Then** output is `ZERO` (no MemPalace or OMEGA processes running on the workstation)

### AC4: ct-dev-homelab pgrep returns 0 (FR-DEC-010 part 2)

- **Given** AC1 passes
- **When** I exec `pgrep -fa 'mempalace\|omega'` inside the `ct-dev-homelab` container (over Tailscale or pct exec)
- **Then** output is empty (0 matches; FR-DEC-010 satisfied for the container side)

### AC5: Verify-run output is appended to the decommission doc

- **Given** AC1 passes and the doc from E1-S07 has the stub section "Hermes verify run output (appended in commit 8)"
- **When** I capture the verify-run stdout to `/tmp/e1-s08-hermes-verify.log` and append a summary (last 40 lines, recap-PLAY-RECAP-style) to the decommission doc
- **Then** `homelab-playbook/docs/decommission/phase-1-context-stack.md` contains the `PLAY RECAP` block from the verify run AND the AC2 grep-gate command + result AND the AC3/AC4 pgrep results

### AC6: MEMORY.md auto-memory continuity verified

- **Given** ACs 1–5 pass
- **When** I open one fresh Claude Code session post-verify-run and observe the auto-memory load
- **Then** `MEMORY.md` loads end-to-end without errors AND no "OMEGA" or "MemPalace" references appear in the session-start transcript

### AC7: Commit conforms to ADR-010

- **When** committed
- **Then** commit message reads `decommission: run Hermes verify on ct-dev-homelab; commit verify-output as evidence` and the diff is restricted to `homelab-playbook/docs/decommission/phase-1-context-stack.md` (the appended evidence)

## Implementation Notes

- ADR-010 commit 8 of 8.
- This story does NOT yet tag the merge commit — tagging happens in E1-S09 after the PR merges. This commit is the *evidence-collection* commit on the branch.
- The grep-gate command (AC2) is the canonical incantation from FR-DEC-009. Codify it as a snippet in the doc itself so E1-S09's pre-push hook can reuse the same logic.
- For the pgrep on `ct-dev-homelab` (AC4), use whatever access path is current (per memory note `project_phone_notifications_tailscale.md`, Tailscale tailnet is the default). Equivalent: `pct exec <CT-id> -- pgrep -fa 'mempalace\|omega'` from a PVE node.
- If `verify.yml` was edited in E1-S06 (line 125 task name + lines 137–174 block), the run here is the binding test that those edits work. If verify.yml fails, **do not amend** — `git revert` E1-S06 and re-author per ADR-010.
- The PR description should include a checklist for the reviewer-of-one acknowledging:
  - "I am merging with **merge commit, not squash**" (per ADR-010 §Consequences)
  - "All 8 commits' tests pass"
  - "Tag will be applied in E1-S09 after merge"

## Test Plan

**Pre-test state check:**
```bash
git log --oneline phase-1-decommission ^main | wc -l    # expect ≥ 7 (commits 1-7 in place)
test -f homelab-playbook/docs/decommission/phase-1-context-stack.md && echo OK
ssh ct-dev-homelab "echo connectivity OK" || pct exec <id> -- echo OK
```

**Action — run verify, capture evidence:**
```bash
# AC1: Hermes verify
ansible-playbook -i homelab-infra/ansible/inventories/homelab \
  homelab-infra/ansible/playbooks/deploy-hermes.yml \
  --limit ct-dev-homelab --tags verify \
  | tee /tmp/e1-s08-hermes-verify.log
echo "Exit: $?"   # expect 0

# AC2: grep gate
grep -r -i 'mempalace\|omega' homelab/ \
  --exclude-dir=.git \
  --exclude-dir=_bmad-output \
  --exclude-dir=docs/decommission \
  | tee /tmp/e1-s08-grep-gate.log
wc -l /tmp/e1-s08-grep-gate.log   # expect 0

# AC3: workstation pgrep
pgrep -fa 'mempalace\|omega' | tee /tmp/e1-s08-pgrep-workstation.log
wc -l /tmp/e1-s08-pgrep-workstation.log   # expect 0

# AC4: container pgrep
ssh ct-dev-homelab "pgrep -fa 'mempalace\|omega'" | tee /tmp/e1-s08-pgrep-container.log
wc -l /tmp/e1-s08-pgrep-container.log     # expect 0
```

**Append evidence to doc:**
```bash
{
  echo ""
  echo "## Hermes verify run output (E1-S08)"
  echo ""
  echo '### `verify.yml` PLAY RECAP'
  echo '```'
  tail -40 /tmp/e1-s08-hermes-verify.log
  echo '```'
  echo ""
  echo "### Grep gate (FR-DEC-009)"
  echo '```'
  echo '$ grep -r -i mempalace\|omega homelab/ --exclude-dir=.git --exclude-dir=_bmad-output --exclude-dir=docs/decommission'
  echo "(0 matches — gate green)"
  echo '```'
  echo ""
  echo "### pgrep gate (FR-DEC-010)"
  echo '```'
  echo "workstation: $(wc -l < /tmp/e1-s08-pgrep-workstation.log) matches"
  echo "ct-dev-homelab: $(wc -l < /tmp/e1-s08-pgrep-container.log) matches"
  echo '```'
} >> homelab-playbook/docs/decommission/phase-1-context-stack.md
git add homelab-playbook/docs/decommission/phase-1-context-stack.md
```

**Post-test state check:**
```bash
grep -c "Hermes verify run output" homelab-playbook/docs/decommission/phase-1-context-stack.md   # expect 1
grep -c "PLAY RECAP" homelab-playbook/docs/decommission/phase-1-context-stack.md                  # expect 1
```

**Rollback procedure (per ADR-010):**
```bash
# If verify.yml fails:
git revert <sha-of-E1-S06>   # most likely culprit is the Jinja edit
# Re-prepare E1-S06 as a NEW commit; re-run E1-S08 verify
# DO NOT amend E1-S06 (per CLAUDE.md "create a NEW commit rather than amending")
```

## Dependencies

- **Blocks:** E1-S09 (forward-protection + tag); merge of the PR
- **Blocked by:** E1-S01 through E1-S07 (all prior commits must be on the branch)

## Risks and Mitigations

| Risk | Source | Mitigation |
|---|---|---|
| `verify.yml` fails because E1-S06 missed a Jinja conditional | ADR-010 risk R7 / AR7 | `git revert E1-S06`; re-author per ADR-010 (NEW commit, not amend) |
| ct-dev-homelab unreachable at verify time | Operator environment | Pre-test connectivity check; if container down, postpone S08 (don't fake the evidence) |
| Grep gate flags doc itself or planning artifacts | Doc / `_bmad-output/` contain references by design | Exclusions in the AC2 incantation are the contract; codify in E1-S09's pre-push hook so the rule is consistent |
| Operator squash-merges the PR, collapsing per-commit revertability | ADR-010 §Consequences | PR description checklist names "merge commit, not squash"; reviewer-of-one acknowledges in PR body |

## Definition of Done

- [ ] All ACs pass
- [ ] PR commit created with the ADR-010-conformant message
- [ ] All four evidence files (`/tmp/e1-s08-*.log`) archived; key excerpts appended to the decommission doc
- [ ] Verify tasks added to `tests/acceptance.md` as `AT-FR-DEC-009`, `AT-FR-DEC-010`, `AT-FR-DEC-011`, `AT-FR-DEP-006a`
- [ ] PR description includes "merge with merge commit, not squash" acknowledgement
- [ ] PR is ready to merge
