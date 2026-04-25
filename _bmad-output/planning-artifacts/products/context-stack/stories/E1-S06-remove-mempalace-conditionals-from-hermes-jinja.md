---
type: story
epic: E1
id: E1-S06
title: "Remove mempalace conditionals from Hermes Jinja templates"
size: 1.5d
priority: MUST
fr_refs: [FR-DEC-005]
adr_refs: [ADR-010]
status: draft
date: 2026-04-25
---

# E1-S06: Remove mempalace conditionals from Hermes Jinja templates

## User Story

As **tomamourette** (homelab operator), I want **every `mempalace` conditional, variable, and template block excised from `config.yaml.j2`, `defaults/main.yml`, and `verify.yml` of the Hermes Ansible role**, so that **the Hermes role renders no MemPalace state and the verify task no longer probes for the deleted skills (FR-DEC-005)**.

## Background and Context

This is the **riskiest commit** in the entire Phase-1 PR — wide-surface edits across three Hermes role files where a misplaced bracket or stale variable can break unrelated paths (PRD §10 R7, epics.md §3.7). ADR-010 §Decision commit 6 isolates this work into one commit so the diff has a single clear review surface and can be reverted with one `git revert` if Hermes-side regressions surface during the verify run (E1-S08). This is **commit 6 of 8**.

## Acceptance Criteria

### AC1: config.yaml.j2 mempalace MCP block removed

- **Given** `homelab-infra/ansible/roles/ai-dev-hermes/templates/config.yaml.j2` lines 283–288 contain a `mempalace` MCP block (and line 273 contains a related conditional)
- **When** I edit out lines 283–288 (the MCP block) AND clean up the conditional on line 273 (which gates the block)
- **Then** `grep -ni mempalace homelab-infra/ansible/roles/ai-dev-hermes/templates/config.yaml.j2` returns 0

### AC2: defaults/main.yml mempalace variables removed

- **Given** `homelab-infra/ansible/roles/ai-dev-hermes/defaults/main.yml` lines 34–36 define `ai_dev_hermes_mempalace_*` variables
- **When** I delete those three lines
- **Then** `grep -ni mempalace homelab-infra/ansible/roles/ai-dev-hermes/defaults/main.yml` returns 0

### AC3: verify.yml Story-6.4 verify block removed and task name updated

- **Given** `homelab-infra/ansible/roles/ai-dev-hermes/tasks/verify.yml` lines 137–174 contain the Story-6.4 mempalace verification block AND line 125 has a task name that mentions mempalace
- **When** I delete lines 137–174 AND update line 125's task name to no longer mention mempalace
- **Then** `grep -ni mempalace homelab-infra/ansible/roles/ai-dev-hermes/tasks/verify.yml` returns 0

### AC4: Whole Hermes role is mempalace-free

- **Given** ACs 1–3 are complete
- **When** I run `grep -rni mempalace homelab-infra/ansible/roles/ai-dev-hermes/`
- **Then** the result is 0 matches

### AC5: Templates render successfully against current vars

- **Given** AC4 passes
- **When** I run `ansible-playbook --check --diff -i homelab-infra/ansible/inventories/homelab homelab-infra/ansible/playbooks/deploy-hermes.yml --limit ct-dev-homelab`
- **Then** the dry run reports 0 errors AND the rendered `config.yaml` (visible in `--diff`) contains no `mempalace` strings AND no Jinja `UndefinedError` is raised for removed variables

### AC6: Hermes role unit-syntax checks pass

- **Given** AC4 passes
- **When** I run `ansible-playbook --syntax-check homelab-infra/ansible/playbooks/deploy-hermes.yml` and `ansible-lint homelab-infra/ansible/roles/ai-dev-hermes/`
- **Then** both exit 0 (or print only pre-existing warnings — capture baseline before edit for diff)

### AC7: Commit conforms to ADR-010

- **When** committed
- **Then** commit message reads `decommission: remove mempalace conditionals from Hermes Jinja templates` and the diff is restricted to the three files (`templates/config.yaml.j2`, `defaults/main.yml`, `tasks/verify.yml`)

## Implementation Notes

- **ADR-010 commit 6 of 8 — the riskiest commit.** Per ADR-010 §Consequences, this commit is isolated specifically to make `git revert <sha>` a clean unwind path if E1-S08's Hermes verify run on `ct-dev-homelab` surfaces breakage.
- Verified line ranges (CONCRETE FILESYSTEM REFERENCES; re-verify before edit because S05 may have shifted nothing in these three files but the line numbers were captured pre-S05):
  - `templates/config.yaml.j2`: drop **lines 283–288** (mempalace MCP block); clean up **line 273** conditional that gates the block.
  - `defaults/main.yml`: drop **lines 34–36** (`ai_dev_hermes_mempalace_*` defaults).
  - `tasks/verify.yml`: drop **lines 137–174** (Story-6.4 verify block); update **line 125** task name (it mentions mempalace).
- Always re-grep with `grep -n mempalace <file>` before editing to confirm current line numbers — the line refs above are pre-S05 snapshots.
- Use **inline double-quoted strings** for any regex value that might be touched (memory note YAML block-scalar regex trap — `>-` / `|-` keep `\s` literal and break regex silently). This story does not introduce regex but the warning applies if the conditional cleanup involves any.
- After editing, render the template manually if possible to confirm Jinja2 happiness:
  ```bash
  ansible-playbook --check --diff ... | grep -A 30 "config.yaml"
  ```
- **Do not** make any other "drive-by" edits in these three files. The ADR-010 review-surface discipline depends on the diff being narrowly scoped.

## Test Plan

**Pre-test state check (capture baseline lint/syntax noise):**
```bash
ansible-playbook --syntax-check homelab-infra/ansible/playbooks/deploy-hermes.yml \
  > /tmp/e1-s06-syntax-pre.txt 2>&1
ansible-lint homelab-infra/ansible/roles/ai-dev-hermes/ \
  > /tmp/e1-s06-lint-pre.txt 2>&1 || true

grep -n mempalace homelab-infra/ansible/roles/ai-dev-hermes/templates/config.yaml.j2
grep -n mempalace homelab-infra/ansible/roles/ai-dev-hermes/defaults/main.yml
grep -n mempalace homelab-infra/ansible/roles/ai-dev-hermes/tasks/verify.yml
```

**Action — surgical edits to three files:**
```bash
$EDITOR homelab-infra/ansible/roles/ai-dev-hermes/templates/config.yaml.j2   # drop lines 283-288 + clean line 273
$EDITOR homelab-infra/ansible/roles/ai-dev-hermes/defaults/main.yml          # drop lines 34-36
$EDITOR homelab-infra/ansible/roles/ai-dev-hermes/tasks/verify.yml           # drop lines 137-174 + update line 125 task name
git add homelab-infra/ansible/roles/ai-dev-hermes/templates/config.yaml.j2 \
        homelab-infra/ansible/roles/ai-dev-hermes/defaults/main.yml \
        homelab-infra/ansible/roles/ai-dev-hermes/tasks/verify.yml
```

**Post-test state check:**
```bash
grep -rni mempalace homelab-infra/ansible/roles/ai-dev-hermes/   # expect 0

ansible-playbook --syntax-check homelab-infra/ansible/playbooks/deploy-hermes.yml \
  > /tmp/e1-s06-syntax-post.txt 2>&1
diff /tmp/e1-s06-syntax-pre.txt /tmp/e1-s06-syntax-post.txt    # expect identical

ansible-lint homelab-infra/ansible/roles/ai-dev-hermes/ \
  > /tmp/e1-s06-lint-post.txt 2>&1 || true
diff /tmp/e1-s06-lint-pre.txt /tmp/e1-s06-lint-post.txt        # expect no NEW errors

ansible-playbook --check --diff \
  -i homelab-infra/ansible/inventories/homelab \
  homelab-infra/ansible/playbooks/deploy-hermes.yml --limit ct-dev-homelab \
  | tee /tmp/e1-s06-dry-run.txt
grep -i mempalace /tmp/e1-s06-dry-run.txt   # expect 0
grep -i UndefinedError /tmp/e1-s06-dry-run.txt   # expect 0
```

**Rollback procedure (per ADR-010 — this is the SOP unwind for the riskiest commit):**
```bash
# If E1-S08 verify run on ct-dev-homelab fails because of this commit:
git revert <sha-of-this-commit>
# This restores all three Jinja files to their pre-edit state.
# Investigate and re-prepare the edit; re-commit as a NEW commit (do NOT amend).
```

## Dependencies

- **Blocks:** E1-S08 (Hermes verify run on ct-dev-homelab is the binding test for this commit)
- **Blocked by:** E1-S04 (skills dirs gone), E1-S05 (wiring gone) — commits 4 and 5 must be in place so the Jinja edits don't fight surviving references

## Risks and Mitigations

| Risk | Source | Mitigation |
|---|---|---|
| Wrong line range deletion takes out adjacent unrelated config | ADR-010 risk register; this is the named "riskiest" commit | Pre/post `grep -n mempalace`; baseline syntax/lint diff before vs after; isolated to one commit so `git revert` is clean |
| Removing a default leaves a downstream `{{ ai_dev_hermes_mempalace_* }}` reference undefined | YAML/Jinja silent failure mode | AC5 `--check --diff` exposes `UndefinedError`; AC4 grep gate confirms no surviving references in the role |
| Line numbers shifted by E1-S05 main.yml edit (different file but operator confuses files) | Editing fatigue across 6 sequential commits | Pre-test step re-greps current line numbers; do not trust the snapshot ranges blindly |
| Operator drive-by-edits unrelated content in the three files | ADR-010 review-surface discipline | AC7 restricts diff scope; reviewer-of-one acknowledges in PR body |

## Definition of Done

- [ ] All ACs pass
- [ ] PR commit created with `decommission: remove mempalace conditionals from Hermes Jinja templates`
- [ ] Pre/post syntax + lint diffs archived in `/tmp/e1-s06-*.txt` for reference during E1-S08 verify run
- [ ] Verify task added to `tests/acceptance.md` as `AT-FR-DEC-005`
- [ ] PR body acknowledges this is the high-risk commit per ADR-010
