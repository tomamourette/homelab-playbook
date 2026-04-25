---
type: story
epic: E1
id: E1-S05
title: "Remove MemPalace wiring (wire-mempalace.yml + knowledge-query orchestrator)"
size: 0.5d
priority: MUST
fr_refs: [FR-DEC-004, FR-DEC-006, FR-DEP-001]
adr_refs: [ADR-010, ADR-005]
status: draft
date: 2026-04-25
---

# E1-S05: Remove MemPalace wiring (wire-mempalace.yml + knowledge-query orchestrator)

## User Story

As **tomamourette** (homelab operator), I want **the `wire-mempalace.yml` Hermes task and the degenerated `knowledge-query` orchestrator skill removed**, so that **the wiring layer that pretended to glue MemPalace to Hermes (and the orphaned orchestrator that has no backend left) stops misleading future-me (FR-DEC-004, FR-DEC-006)**.

## Background and Context

`wire-mempalace.yml` is the Hermes role task that wired the three (now-deleted) `mempalace-*` skills into Hermes' config. The `knowledge-query` skill was the original orchestrator on top of mempalace — per ADR-005, it degenerated into a thin shell when the MemPalace MCP path didn't deliver, and is the spiritual ancestor of the future Phase-3 `wiki-query` skill (FR-WIKI-001 explicitly recreates the read-on-demand skill against the new wiki tier). ADR-010 §Decision commit 5 isolates this commit from E1-S04 because the wiring edits are conceptually distinct from store/role deletion. This is **commit 5 of 8**.

## Acceptance Criteria

### AC1: wire-mempalace.yml task file deleted

- **Given** the file `homelab-infra/ansible/roles/ai-dev-hermes/tasks/wire-mempalace.yml` exists
- **When** I `git rm` it
- **Then** `test -f homelab-infra/ansible/roles/ai-dev-hermes/tasks/wire-mempalace.yml` exits 1

### AC2: knowledge-query orchestrator skill directory removed

- **Given** `homelab-infra/ansible/roles/ai-dev-hermes/files/skills/knowledge-query/` exists (degenerated orchestrator)
- **When** I `git rm -r` it
- **Then** the directory is gone AND `find homelab-infra/ -type d -name knowledge-query` returns no matches

### AC3: Hermes tasks/main.yml does not include wire-mempalace.yml

- **Given** `homelab-infra/ansible/roles/ai-dev-hermes/tasks/main.yml` lines 14–15 currently `- include_tasks: wire-mempalace.yml` (or equivalent)
- **When** I edit lines 14–15 out (see Implementation Notes)
- **Then** `grep -ni wire-mempalace homelab-infra/ansible/roles/ai-dev-hermes/tasks/main.yml` returns 0 AND `ansible-lint homelab-infra/ansible/roles/ai-dev-hermes/` reports no syntax errors

### AC4: No surviving references in repo (scoped grep)

- **Given** ACs 1–3 are complete
- **When** I run `grep -rni 'wire-mempalace\|knowledge-query' homelab-infra/`
- **Then** the result is 0 matches

### AC5: Idempotent re-run of Hermes role on ct-dev-homelab in check mode does not error

- **Given** ACs 1–4 are complete
- **When** I run `ansible-playbook --check --diff -i homelab-infra/ansible/inventories/homelab homelab-infra/ansible/playbooks/deploy-hermes.yml --limit ct-dev-homelab` (or the operator's local equivalent)
- **Then** the dry run finishes without referencing `wire-mempalace` or `knowledge-query`. (Note: full `verify.yml` is run in E1-S08 against the real container; this is a dry-run sanity check only)

### AC6: Commit conforms to ADR-010

- **When** committed
- **Then** commit message reads `decommission: remove MemPalace wiring (wire-mempalace.yml + knowledge-query)`

## Implementation Notes

- ADR-010 commit 5 of 8.
- Verified earlier targets:
  - `homelab-infra/ansible/roles/ai-dev-hermes/tasks/wire-mempalace.yml` (full file delete)
  - `homelab-infra/ansible/roles/ai-dev-hermes/files/skills/knowledge-query/` (degenerated orchestrator dir)
  - **Surgical edit**: `homelab-infra/ansible/roles/ai-dev-hermes/tasks/main.yml` lines 14–15 — remove the `include_tasks: wire-mempalace.yml` lines.
- Do **not** touch `defaults/main.yml`, `templates/config.yaml.j2`, or `tasks/verify.yml` here — those are E1-S06 (the riskiest commit, isolated for review per ADR-010 §Consequences).
- The `knowledge-query` skill is **not** the same as the future `wiki-query` skill — `wiki-query` is delivered later in E4-S03 against `homelab-playbook/wiki/`. Do not preserve any of the orchestrator's logic.
- Recommend running `ansible-lint` over the Hermes role after the surgical edit to catch dangling include references early.

## Test Plan

**Pre-test state check:**
```bash
test -f homelab-infra/ansible/roles/ai-dev-hermes/tasks/wire-mempalace.yml && echo present
test -d homelab-infra/ansible/roles/ai-dev-hermes/files/skills/knowledge-query/ && echo present
grep -n wire-mempalace homelab-infra/ansible/roles/ai-dev-hermes/tasks/main.yml   # expect lines 14-15
```

**Action:**
```bash
git rm homelab-infra/ansible/roles/ai-dev-hermes/tasks/wire-mempalace.yml
git rm -r homelab-infra/ansible/roles/ai-dev-hermes/files/skills/knowledge-query/
# Surgical edit main.yml: remove the include_tasks line(s) referencing wire-mempalace
$EDITOR homelab-infra/ansible/roles/ai-dev-hermes/tasks/main.yml
git add homelab-infra/ansible/roles/ai-dev-hermes/tasks/main.yml
```

**Post-test state check:**
```bash
grep -rni 'wire-mempalace\|knowledge-query' homelab-infra/   # expect 0
ansible-lint homelab-infra/ansible/roles/ai-dev-hermes/      # expect clean
```

**Sanity dry-run (AC5):**
```bash
ansible-playbook --check --diff \
  -i homelab-infra/ansible/inventories/homelab \
  homelab-infra/ansible/playbooks/deploy-hermes.yml --limit ct-dev-homelab
# Expect: no tasks reference wire-mempalace or knowledge-query
```

**Rollback procedure (per ADR-010):**
```bash
git revert <sha-of-this-commit>   # restores task file, skill dir, and the include line in main.yml
```

## Dependencies

- **Blocks:** E1-S06 (Jinja edits assume wiring is gone), E1-S08 (Hermes verify run)
- **Blocked by:** E1-S04 (skill dirs already deleted; wiring referenced them)

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Removing `include_tasks` line shifts other line numbers, making future ADR-010 references stale | Document line edit explicitly here; E1-S06's line references are independently re-verified before that commit |
| Hermes role becomes inconsistent between commit 4 and commit 6 (Jinja still references mempalace) | Expected and accepted per ADR-010 — only `main` after merge needs to be consistent; E1-S08 verify run is the final gate |
| `ansible-lint` not installed on workstation | Optional check; AC5 dry-run is the binding sanity check |

## Definition of Done

- [ ] All ACs pass
- [ ] PR commit created with the ADR-010-conformant message
- [ ] Verify tasks added to `tests/acceptance.md` as `AT-FR-DEC-004`, `AT-FR-DEC-006`
