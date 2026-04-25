---
type: story
epic: E1
id: E1-S03
title: "Uninstall omega-memory package + remove ai-dev-omega-memory role + group_vars"
size: 1d
priority: MUST
fr_refs: [FR-DEC-008, FR-DEP-001, FR-DEP-009]
adr_refs: [ADR-010]
status: draft
date: 2026-04-25
---

# E1-S03: Uninstall omega-memory package + remove ai-dev-omega-memory role + group_vars

## User Story

As **tomamourette** (homelab operator), I want **the `omega-memory` Python package uninstalled from the workstation, the `ai-dev-omega-memory` Ansible role removed from `homelab-infra`, and the OMEGA group_vars dropped from the dev_hosts container playbook**, so that **OMEGA is gone from both the workstation runtime and the deploy automation in one coherent commit (FR-DEC-008, FR-DEP-009)**.

## Background and Context

After E1-S02 the OMEGA hooks are de-registered from Claude Code, but `omega-memory 1.4.3` is still installed via pipx and the `ai-dev-omega-memory` Ansible role + `dev_hosts/ai-dev-omega.yml` group_vars still ship the role to dev_hosts containers. ADR-010 §Decision commit 3 bundles the package uninstall and the repo-side role/group_vars removal into one logical commit because they form a single conceptual unit: "OMEGA is no longer deployed anywhere." This is **commit 3 of 8**.

## Acceptance Criteria

### AC1: omega-memory Python package uninstalled

- **Given** `pipx list | grep omega-memory` shows `omega-memory 1.4.3` (or `pip show omega-memory` returns metadata)
- **When** I run `pipx uninstall omega-memory` (or `pip uninstall -y omega-memory` in the environment that owns it)
- **Then** `pipx list | grep -c omega` returns `0` AND `python3 -c "import omega_memory" 2>&1 | grep -c "ModuleNotFoundError"` returns `1`

### AC2: OMEGA daemon process is not running

- **Given** AC1 is done
- **When** I run `pgrep -f "omega serve" && pgrep -f omega-memory`
- **Then** `pgrep -f "omega serve" | xargs -r kill` is invoked once (idempotent — succeeds if already empty); subsequent `pgrep -fa omega` returns `0` matches

### AC3: ai-dev-omega-memory Ansible role removed

- **Given** the role exists at `homelab-infra/ansible/roles/ai-dev-omega-memory/`
- **When** I run `git rm -r homelab-infra/ansible/roles/ai-dev-omega-memory/` and commit
- **Then** `test -d homelab-infra/ansible/roles/ai-dev-omega-memory` returns false (exit 1) AND the deletion is reflected in `git status` for the decommission branch

### AC4: dev_hosts group_vars file removed

- **Given** the file `homelab-infra/ansible/inventories/homelab/group_vars/dev_hosts/ai-dev-omega.yml` exists
- **When** I `git rm` it
- **Then** `test -f homelab-infra/ansible/inventories/homelab/group_vars/dev_hosts/ai-dev-omega.yml` returns false

### AC5: deploy-ai-dev-container.yml drops the role and tag references

- **Given** `homelab-infra/ansible/playbooks/deploy-ai-dev-container.yml` references `ai-dev-omega-memory` (role include, tag, composition comment, and possibly an example `--limit ... --tags` line)
- **When** I edit it to drop every reference
- **Then** `grep -i omega homelab-infra/ansible/playbooks/deploy-ai-dev-container.yml` returns 0 matches AND `ansible-playbook --syntax-check homelab-infra/ansible/playbooks/deploy-ai-dev-container.yml` exits 0

### AC6: Idempotent re-run safety (FR-DEP-001)

- **Given** ACs 1–5 are complete
- **When** I run the deploy playbook in check mode against a non-prod target (`ansible-playbook --check --diff -i inventories/homelab playbooks/deploy-ai-dev-container.yml --limit ct-dev-test`)
- **Then** the dry run completes without referencing `ai-dev-omega-memory` and reports zero changes attributable to OMEGA

### AC7: Commit conforms to ADR-010 message format

- **When** committed
- **Then** commit message reads: `decommission: uninstall omega-memory + remove ai-dev-omega-memory role + group_vars`

## Implementation Notes

- ADR-010 commit 3 of 8.
- Verified earlier targets (CONCRETE FILESYSTEM REFERENCES):
  - Workstation: `pipx uninstall omega-memory` (current version `omega-memory 1.4.3`).
  - Workstation: `pgrep -f "omega serve" | xargs -r kill` (kills daemon if alive).
  - Repo: `homelab-infra/ansible/roles/ai-dev-omega-memory/` (full directory).
  - Repo: `homelab-infra/ansible/inventories/homelab/group_vars/dev_hosts/ai-dev-omega.yml`.
  - Repo: drop role and tag from `homelab-infra/ansible/playbooks/deploy-ai-dev-container.yml`.
- The `~/.omega/` directory and `~/.claude/scripts/omega-*.py` hook scripts are **not** removed here — those land in E1-S06 to keep the workstation FS cleanup paired with the MemPalace workstation cleanup story. This story is package + repo automation only.
- `pgrep` cleanup is idempotent: `pgrep -f "omega serve" | xargs -r kill` exits cleanly when no process matches.

## Test Plan

**Pre-test state check:**
```bash
pipx list | grep omega                              # expect "omega-memory 1.4.3"
pgrep -fa "omega serve"                              # snapshot
ls homelab-infra/ansible/roles/ai-dev-omega-memory/ # expect role files
ls homelab-infra/ansible/inventories/homelab/group_vars/dev_hosts/ai-dev-omega.yml
grep -ci omega homelab-infra/ansible/playbooks/deploy-ai-dev-container.yml
```

**Action:**
```bash
pipx uninstall omega-memory
pgrep -f "omega serve" | xargs -r kill
git rm -r homelab-infra/ansible/roles/ai-dev-omega-memory/
git rm homelab-infra/ansible/inventories/homelab/group_vars/dev_hosts/ai-dev-omega.yml
# Edit playbooks/deploy-ai-dev-container.yml — drop role include, tag, composition comment, --limit example
git add homelab-infra/ansible/playbooks/deploy-ai-dev-container.yml
```

**Post-test state check:**
```bash
pipx list | grep -c omega                                # expect 0
pgrep -fa omega                                          # expect 0 lines
test -d homelab-infra/ansible/roles/ai-dev-omega-memory/ && echo BAD || echo OK
grep -ci omega homelab-infra/ansible/playbooks/deploy-ai-dev-container.yml  # expect 0
ansible-playbook --syntax-check homelab-infra/ansible/playbooks/deploy-ai-dev-container.yml
```

**Idempotency check (AC6):**
```bash
ansible-playbook --check --diff -i homelab-infra/ansible/inventories/homelab \
  homelab-infra/ansible/playbooks/deploy-ai-dev-container.yml --limit ct-dev-test
# Expect: no tasks reference ai-dev-omega-memory; clean diff
```

**Rollback procedure (per ADR-010):**
```bash
git revert <sha-of-this-commit>   # restores role + group_vars + playbook references
pipx install omega-memory==1.4.3   # reinstalls package on workstation if needed
```

## Dependencies

- **Blocks:** E1-S04 (MemPalace removal) — sequencing per ADR-010
- **Blocked by:** E1-S02 (settings.json registration must already be gone)

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| pipx uninstall leaves orphan binaries in PATH | `which omega 2>/dev/null` post-check; `rm` orphan symlinks if found (FR-DEC-009 grep gate at S08 will catch any remaining reference) |
| dev_hosts playbook syntax breaks after edit | AC5 syntax check + AC6 dry run guard |
| Role removal breaks an unrelated playbook that imports it transitively | `grep -rni "ai-dev-omega-memory\|ai_dev_omega_memory" homelab-infra/` post-edit; expect only the playbook entry being removed |

## Definition of Done

- [ ] All ACs pass
- [ ] PR commit created with the ADR-010-conformant message
- [ ] Verify tasks added to `tests/acceptance.md` as `AT-FR-DEC-008`, `AT-FR-DEP-001a`, `AT-FR-DEP-009`
- [ ] No new `omega` references introduced anywhere in the diff
