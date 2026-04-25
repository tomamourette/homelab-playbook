---
type: story
epic: E1
id: E1-S04
title: "Remove MemPalace store + ai-dev-mempalace role + Hermes mempalace-* skills"
size: 1d
priority: MUST
fr_refs: [FR-DEC-001, FR-DEC-002, FR-DEC-003]
adr_refs: [ADR-010]
status: draft
date: 2026-04-25
---

# E1-S04: Remove MemPalace store + ai-dev-mempalace role + Hermes mempalace-* skills

## User Story

As **tomamourette** (homelab operator), I want **the workstation `~/.mempalace/` SQLite store deleted, the `ai-dev-mempalace` Ansible role removed in full, the dev_hosts MemPalace group_vars dropped, and the three Hermes `mempalace-*` skill directories deleted**, so that **the bulk of MemPalace's surface — store, role, group_vars, skills — disappears from the workstation and the repo in one revertable commit (FR-DEC-001, FR-DEC-002, FR-DEC-003)**.

## Background and Context

MemPalace's SQLite is empty (0 rows across all tables; 4.5 KB on disk; no data migration is required per FR-DEC-012). The Ansible role is dead infrastructure since `ct-dev-test` was retired, and the three Hermes mempalace skills (`mempalace-kg-query`, `mempalace-diary`, `mempalace-search`) are unused. ADR-010 §Decision commit 4 batches these because they're a single conceptual delete: "MemPalace stops existing as a deployable artifact." This is **commit 4 of 8**.

## Acceptance Criteria

### AC1: Workstation MemPalace store deleted

- **Given** `~/.mempalace/` exists (currently 4.5KB, empty SQLite tables)
- **When** I run `rm -rf ~/.mempalace/` after confirming it is empty
- **Then** `test -d /home/developer/.mempalace` exits 1 AND `pgrep -f mempalace` returns 0

### AC2: Empty-store confirmation captured (feeds FR-DEC-012 record)

- **Given** the store still exists
- **When** I run a row-count probe before deletion: `sqlite3 ~/.mempalace/*.db "SELECT name FROM sqlite_master WHERE type='table';" 2>/dev/null` and a per-table `SELECT count(*)` on each
- **Then** all tables show 0 rows; the output is captured to `/tmp/e1-s04-mempalace-empty-evidence.txt` and referenced in the E1-S07 decommission doc

### AC3: ai-dev-mempalace Ansible role removed in full

- **Given** `homelab-infra/ansible/roles/ai-dev-mempalace/` contains 9 task files plus role metadata
- **When** I run `git rm -r homelab-infra/ansible/roles/ai-dev-mempalace/`
- **Then** `test -d homelab-infra/ansible/roles/ai-dev-mempalace/` exits 1 AND no other role's `meta/main.yml` lists it as a dependency (`grep -rni 'ai-dev-mempalace\|ai_dev_mempalace' homelab-infra/ansible/roles/*/meta/` returns 0)

### AC4: dev_hosts MemPalace group_vars file removed

- **Given** `homelab-infra/ansible/inventories/homelab/group_vars/dev_hosts/ai-dev-mempalace.yml` exists
- **When** I `git rm` it
- **Then** the file is gone AND `grep -rni mempalace homelab-infra/ansible/inventories/homelab/group_vars/` returns 0

### AC5: Three Hermes mempalace-* skill directories removed

- **Given** the three directories exist:
  - `homelab-infra/ansible/roles/ai-dev-hermes/files/skills/mempalace-kg-query/`
  - `homelab-infra/ansible/roles/ai-dev-hermes/files/skills/mempalace-diary/`
  - `homelab-infra/ansible/roles/ai-dev-hermes/files/skills/mempalace-search/`
- **When** I `git rm -r` all three
- **Then** `ls homelab-infra/ansible/roles/ai-dev-hermes/files/skills/ | grep -c mempalace` returns 0

### AC6: deploy-ai-dev-container.yml drops the ai-dev-mempalace role include

- **Given** `homelab-infra/ansible/playbooks/deploy-ai-dev-container.yml` references `ai-dev-mempalace` (role include, tag block, composition comment, and the `--limit ct-dev-test --tags ai-dev-mempalace` example line)
- **When** I edit out every reference
- **Then** `grep -i mempalace homelab-infra/ansible/playbooks/deploy-ai-dev-container.yml` returns 0 AND `ansible-playbook --syntax-check ...` exits 0

### AC7: Commit conforms to ADR-010

- **When** committed
- **Then** commit message reads `decommission: remove MemPalace store + role + skills`

## Implementation Notes

- ADR-010 commit 4 of 8.
- Hermes role internals (`tasks/main.yml` include, `defaults/main.yml` mempalace vars, `templates/config.yaml.j2` mempalace MCP block, `tasks/verify.yml` story-6.4 block) are **NOT** edited here — those are surgical Jinja edits that land in **E1-S06** because they require careful diff review per ADR-010 risk R7.
- `wire-mempalace.yml` and the `knowledge-query` orchestrator skill land in **E1-S05** (next commit).
- Capture the empty-table evidence (AC2) before the `rm -rf` so the FR-DEC-012 "no data was migrated, store was empty" record in the E1-S07 doc has receipts.
- Use `git rm` (not `rm`) for repo files so deletions are part of the commit object, not unstaged changes.

## Test Plan

**Pre-test state check:**
```bash
ls -la ~/.mempalace/                                      # snapshot size + db file
sqlite3 ~/.mempalace/*.db ".tables" 2>/dev/null            # capture table list
ls homelab-infra/ansible/roles/ai-dev-mempalace/ | wc -l   # expect ≥ 1
ls homelab-infra/ansible/roles/ai-dev-hermes/files/skills/ | grep mempalace
grep -c mempalace homelab-infra/ansible/playbooks/deploy-ai-dev-container.yml
```

**Action — capture evidence then delete:**
```bash
# AC2 evidence first
{ echo "## ~/.mempalace/ table contents at $(date -u +%FT%TZ)"; \
  sqlite3 ~/.mempalace/*.db ".tables"; \
  for t in $(sqlite3 ~/.mempalace/*.db ".tables"); do \
    echo "$t: $(sqlite3 ~/.mempalace/*.db "SELECT count(*) FROM $t;")"; done; \
} > /tmp/e1-s04-mempalace-empty-evidence.txt

# Workstation deletion
rm -rf ~/.mempalace/

# Repo deletions
git rm -r homelab-infra/ansible/roles/ai-dev-mempalace/
git rm homelab-infra/ansible/inventories/homelab/group_vars/dev_hosts/ai-dev-mempalace.yml
git rm -r homelab-infra/ansible/roles/ai-dev-hermes/files/skills/mempalace-kg-query/
git rm -r homelab-infra/ansible/roles/ai-dev-hermes/files/skills/mempalace-diary/
git rm -r homelab-infra/ansible/roles/ai-dev-hermes/files/skills/mempalace-search/

# Edit playbook (manual): drop role include + tag + composition comment + example --limit line
$EDITOR homelab-infra/ansible/playbooks/deploy-ai-dev-container.yml
git add homelab-infra/ansible/playbooks/deploy-ai-dev-container.yml
```

**Post-test state check:**
```bash
test -d ~/.mempalace && echo BAD || echo OK
test -d homelab-infra/ansible/roles/ai-dev-mempalace/ && echo BAD || echo OK
ls homelab-infra/ansible/roles/ai-dev-hermes/files/skills/ | grep -c mempalace   # expect 0
grep -ci mempalace homelab-infra/ansible/playbooks/deploy-ai-dev-container.yml   # expect 0
ansible-playbook --syntax-check homelab-infra/ansible/playbooks/deploy-ai-dev-container.yml
test -f /tmp/e1-s04-mempalace-empty-evidence.txt && echo OK
```

**Rollback procedure (per ADR-010):**
```bash
git revert <sha-of-this-commit>     # restores role, group_vars, three skill dirs, playbook references
# Workstation ~/.mempalace was empty; restoration is `mkdir ~/.mempalace` (no data to recover)
```

## Dependencies

- **Blocks:** E1-S05 (wiring removal), E1-S06 (Hermes Jinja edits assume the skill dirs are gone), E1-S07 (decommission doc references the empty-evidence file)
- **Blocked by:** E1-S03 (OMEGA path cleared first, per ADR-010 ordering)

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Deleting `~/.mempalace/` loses data | AC2 captures the row-count evidence (zero rows) before deletion; FR-DEC-012 explicitly mandates no data migration |
| Hermes role still references the deleted skills via Jinja conditionals → role becomes inconsistent at this commit | This is **expected and acceptable** at this commit — the Jinja edits are E1-S06; the branch is reviewed end-to-end before merge. Ansible would fail the role between commits 4–6 but not on `main` |
| Playbook edit leaves an `--limit ct-dev-test --tags ai-dev-mempalace` example in the operator-facing comment block | AC6 grep gate catches comment text too |

## Definition of Done

- [ ] All ACs pass
- [ ] PR commit created with `decommission: remove MemPalace store + role + skills`
- [ ] `/tmp/e1-s04-mempalace-empty-evidence.txt` exists and is referenced in the E1-S07 doc TODO list
- [ ] Verify tasks added to `tests/acceptance.md` as `AT-FR-DEC-001`, `AT-FR-DEC-002`, `AT-FR-DEC-003`
