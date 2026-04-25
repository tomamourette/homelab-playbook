---
type: story
epic: E1
id: E1-S07
title: "Author Phase-1 decommission doc"
size: 0.5d
priority: MUST
fr_refs: [FR-DEC-012]
adr_refs: [ADR-010]
status: draft
date: 2026-04-25
---

# E1-S07: Author Phase-1 decommission doc

## User Story

As **tomamourette** (homelab operator), I want **a single authoritative decommission doc that records every action taken in Phase 1 and the FR-DEC-012 "no data was migrated, both stores were empty" record**, so that **future-me (and the rollback path in FR-DEP-007) has a single page that explains what was removed, when, and why no data is recoverable from MemPalace or OMEGA stores (FR-DEC-012)**.

## Background and Context

PRD §14 glossary defines the "Decommission doc" as a markdown deliverable produced as part of Phase 1 recording every action taken. ADR-010 §Decision commit 7 places this commit *before* the Hermes verify run (commit 8) so the verify-run output can be appended to a doc that already exists. This is **commit 7 of 8**. The doc also serves as the FR-DEC-012 contract that no data migration was performed (both MemPalace SQLite and OMEGA store were empty/near-empty at decommission time).

## Acceptance Criteria

### AC1: Decommission doc exists at the canonical path

- **Given** ACs in E1-S01 through E1-S06 have completed
- **When** I author `homelab-playbook/docs/decommission/phase-1-context-stack.md`
- **Then** `test -f homelab-playbook/docs/decommission/phase-1-context-stack.md` exits 0 AND `wc -l` reports ≥ 100 lines

### AC2: Doc enumerates every action taken across commits 1–6

- **Given** the doc is open
- **When** I read its "Actions taken" section
- **Then** the section contains at minimum one bullet per commit (1–6) with: commit message, paths touched, and FR refs covered. Specifically:
  - Commit 1: disable OMEGA hooks → settings.json (FR-DEC-007a)
  - Commit 2: remove OMEGA hooks → settings.json (FR-DEC-007b)
  - Commit 3: uninstall omega-memory + role + group_vars (FR-DEC-008, FR-DEP-009)
  - Commit 4: MemPalace store + role + skills (FR-DEC-001..003)
  - Commit 5: wire-mempalace + knowledge-query (FR-DEC-004, FR-DEC-006)
  - Commit 6: Hermes Jinja conditionals (FR-DEC-005)

### AC3: FR-DEC-012 no-data-migration record is captured

- **Given** the empty-evidence file from E1-S04 exists at `/tmp/e1-s04-mempalace-empty-evidence.txt`
- **When** I copy / inline its content into the doc under a "Data migration record (FR-DEC-012)" section
- **Then** the section explicitly states (a) MemPalace SQLite tables were 0 rows at deletion (with table list), (b) OMEGA store was 9 captured memories with broken vector search (per ADR-005 context), and (c) **no data was migrated; both stores were destroyed in place**

### AC4: Rollback path is documented inline

- **Given** the doc is being authored
- **When** I add a "Rollback (FR-DEP-007)" section
- **Then** the section captures: (a) tag name `phase-1-decommission-complete`, (b) `git revert` of the merge commit as the unwind, (c) `pipx install omega-memory==1.4.3` re-install command, (d) Ansible role re-pin path (cherry-pick from the prior commit), (e) note that workstation `~/.mempalace/` and `~/.omega/` are gone — restoration restores the *Ansible role* but the data was empty at decommission so there is nothing to recover

### AC5: MEMORY.md auto-memory continuity statement

- **Given** the doc is being authored
- **When** I add a "Auto-memory continuity (MEMORY.md)" section
- **Then** the section confirms (a) `/home/developer/.claude/projects/-home-developer-workspace-homelab/memory/MEMORY.md` was unaffected by Phase 1, (b) auto-memory is the only memory tier post-decommission until E3 (Graphiti) lands, (c) the next session-start should load `MEMORY.md` cleanly

### AC6: Cross-references to FRs and ADRs

- **Given** the doc is being authored
- **When** I add a "References" section
- **Then** it lists: FR-DEC-001 through FR-DEC-012, FR-DEP-001, FR-DEP-007, FR-DEP-009, ADR-005, ADR-010, brief §7, and PRD §14 glossary "Decommission doc"

### AC7: Commit conforms to ADR-010

- **When** committed
- **Then** commit message reads `decommission: write Phase-1 decommission doc` and the diff is restricted to `homelab-playbook/docs/decommission/phase-1-context-stack.md`

## Implementation Notes

- ADR-010 commit 7 of 8.
- Doc lives at `homelab-playbook/docs/decommission/phase-1-context-stack.md` per PRD §14 glossary and project rule "Use `/docs` for documentation and markdown files" (CLAUDE.md). Create the `docs/decommission/` subdirectory if it doesn't exist.
- The Hermes verify-run output (E1-S08) is **appended to this doc** as evidence — leave a stub section "Hermes verify run output (appended in commit 8)" that E1-S08 will fill.
- The grep gate evidence (`grep -r -i 'mempalace\|omega' homelab/` returning 0) is also appended in E1-S08.
- Pull the empty-store evidence directly from `/tmp/e1-s04-mempalace-empty-evidence.txt`; do not duplicate work.
- Follow project rule: the doc itself **will** contain the words `mempalace` and `omega` (it's literally a doc about decommissioning them) — the FR-DEC-009 grep gate explicitly excludes the decommission doc + git history + `_bmad-output/`.

## Test Plan

**Pre-test state check:**
```bash
test -f /tmp/e1-s04-mempalace-empty-evidence.txt && echo OK
ls homelab-playbook/docs/decommission/ 2>/dev/null   # may not exist yet
```

**Action:**
```bash
mkdir -p homelab-playbook/docs/decommission/
$EDITOR homelab-playbook/docs/decommission/phase-1-context-stack.md
# Author per AC1-AC6 sections; reference inline the empty-evidence file content
git add homelab-playbook/docs/decommission/phase-1-context-stack.md
```

**Post-test state check:**
```bash
test -f homelab-playbook/docs/decommission/phase-1-context-stack.md && echo OK
wc -l homelab-playbook/docs/decommission/phase-1-context-stack.md   # expect ≥ 100
grep -c "FR-DEC-012" homelab-playbook/docs/decommission/phase-1-context-stack.md   # expect ≥ 1
grep -c "MEMORY.md" homelab-playbook/docs/decommission/phase-1-context-stack.md   # expect ≥ 1
grep -c "phase-1-decommission-complete" homelab-playbook/docs/decommission/phase-1-context-stack.md   # expect ≥ 1
```

**Rollback procedure (per ADR-010):**
```bash
git revert <sha-of-this-commit>   # removes the doc; harmless because next commit (E1-S08) edits it
```

## Dependencies

- **Blocks:** E1-S08 (the verify-run evidence is appended to this doc), E1-S09 (forward-protection step references the doc as a sanctioned exception to the grep gate)
- **Blocked by:** E1-S04 (empty-evidence file), E1-S06 (Hermes edits referenced in the actions log)

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Doc itself contains `mempalace`/`omega` strings and a future grep gate (E1-S08, E1-S09) flags them as residue | FR-DEC-009 explicitly excludes the decommission doc; E1-S08 grep gate passes the same exclusion; E1-S09 pre-push hook excludes `homelab-playbook/docs/decommission/` and `_bmad-output/` |
| Operator skips writing the FR-DEC-012 record because both stores were "obviously empty" | AC3 is a hard gate; doc must enumerate the empty-evidence content |
| Doc drifts from reality as later phases modify the decommission scope | Doc captures Phase-1 state at merge; future phases' updates land in their own doc, not this one |

## Definition of Done

- [ ] All ACs pass
- [ ] PR commit created with `decommission: write Phase-1 decommission doc`
- [ ] Doc has stub section "Hermes verify run output (appended in commit 8)" awaiting E1-S08 evidence
- [ ] Verify task added to `tests/acceptance.md` as `AT-FR-DEC-012`
