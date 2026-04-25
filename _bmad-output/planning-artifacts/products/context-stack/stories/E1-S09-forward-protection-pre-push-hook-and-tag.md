---
type: story
epic: E1
id: E1-S09
title: "Forward-protection pre-push hook + tag phase-1-decommission-complete"
size: 0.5d
priority: MUST
fr_refs: [FR-DEC-009, FR-DEP-007]
adr_refs: [ADR-010]
status: draft
date: 2026-04-25
---

# E1-S09: Forward-protection pre-push hook + tag phase-1-decommission-complete

## User Story

As **tomamourette** (homelab operator), I want **a repo-local `pre-push` git hook that blocks any push reintroducing `mempalace` or `omega` references AND a `phase-1-decommission-complete` tag on the merged commit**, so that **regression of decommissioned tools is impossible without an explicit override and the rollback target for the rest of Context Stack is grep-able (FR-DEC-009 forward-protection, ADR-010 §Validation)**.

## Background and Context

ADR-010 §Validation specifies that the merged commit must be tagged `phase-1-decommission-complete` to make the rollback target grep-able. Epic E1 §3.4 acceptance criterion 9 mandates a forward-protection pre-push hook that fails on `mempalace|omega` reference creep (downgrades to a CI lint after week 1 per the same epic AC). This story is **after the PR merges** — it's the wrap-up that locks the decommission state in. Effort: 0.5d.

## Acceptance Criteria

### AC1: Merge commit is tagged phase-1-decommission-complete

- **Given** the Phase-1 PR has merged to `main` with a merge commit (not squash) per ADR-010
- **When** I run `git tag -a phase-1-decommission-complete <merge-commit-sha> -m "Phase 1 decommission complete (Context Stack)"` and `git push origin phase-1-decommission-complete`
- **Then** `git tag -l phase-1-decommission-complete` returns the tag AND `git rev-parse phase-1-decommission-complete^{commit}` returns the merge-commit SHA AND the tag is visible on the remote (`git ls-remote --tags origin | grep phase-1-decommission-complete` returns the tag)

### AC2: pre-push hook script exists and is executable

- **Given** the repo has no current `pre-push` hook (or has a benign existing one to extend)
- **When** I create `homelab/.githooks/pre-push` (or `.git/hooks/pre-push` linked from a tracked path) and set it executable
- **Then** `test -x homelab/.githooks/pre-push` exits 0 AND `git config core.hooksPath` reports `.githooks` (the tracked location)

### AC3: pre-push hook blocks pushes that reintroduce mempalace/omega references

- **Given** the hook from AC2 is installed
- **When** I run a synthetic push attempt that adds a file containing the literal string `mempalace` outside the sanctioned exclusion list
- **Then** the hook exits non-zero AND prints a clear error message naming the offending file/line AND the push is aborted

### AC4: pre-push hook respects the same exclusions as FR-DEC-009

- **Given** the hook is installed
- **When** the diff being pushed only changes files under `homelab-playbook/docs/decommission/`, `_bmad-output/planning-artifacts/`, or git history (`.git/`)
- **Then** the hook exits 0 (these are sanctioned exceptions per FR-DEC-009 — historical record and the doc itself)

### AC5: Hook logic uses the canonical FR-DEC-009 incantation

- **Given** the hook source
- **When** I read its grep command
- **Then** the command matches the FR-DEC-009 / E1-S08 grep gate exactly:
  ```bash
  grep -r -i 'mempalace\|omega' <staged-paths> \
    --exclude-dir=.git \
    --exclude-dir=_bmad-output \
    --exclude-dir=docs/decommission \
    --exclude-dir=stories  # _bmad-output story files reference these names by design
  ```

### AC6: Override path is documented (escape hatch)

- **Given** there is a legitimate need to reference `mempalace` or `omega` in future commits (e.g., writing a retro doc that names them as cautionary tales)
- **When** the operator runs `git push --no-verify`
- **Then** the hook is bypassed AND a comment in the hook source explicitly documents this escape hatch with a warning ("only use for retro / decommission-archive commits")

### AC7: Hook downgrade-to-CI plan documented

- **Given** epic AC9 specifies the hook "downgrades to a CI lint after week 1"
- **When** I author `homelab-playbook/docs/decommission/phase-1-context-stack.md` (extend the existing doc from E1-S07)
- **Then** the doc gains a "Forward protection (week 1+)" section noting: (a) the pre-push hook is the immediate guard, (b) at week 2, replace with a CI lint step in the homelab-infra GitHub Actions / pre-merge check, (c) reference the canonical grep incantation

### AC8: Tag is reachable as the rollback target per ADR-010

- **Given** AC1 is complete
- **When** I simulate the FR-DEP-007 rollback dry-run: `git checkout phase-1-decommission-complete -- <some-decommissioned-path>` (e.g., `homelab-infra/ansible/roles/ai-dev-mempalace`)
- **Then** the path returns at the post-decommission state (i.e., empty / not-present), confirming the tag is the correct rollback target — the *prior* commit before merge is the pre-decommission anchor

### AC9: Commit (this story is post-merge, so commit lives on a follow-up small PR or directly on main per repo policy)

- **When** the hook + doc edit is committed
- **Then** commit message reads `decommission: add pre-push forward-protection hook + tag phase-1-decommission-complete`

## Implementation Notes

- This story runs **after the Phase-1 PR merges** — it is not commit 9 of the same PR (the PR is 8 commits per ADR-010). It's a follow-up commit that depends on the merge having happened so that the merge-commit SHA exists to tag.
- Tag command:
  ```bash
  git tag -a phase-1-decommission-complete -m "Phase 1 decommission complete (Context Stack); rollback target per FR-DEP-007"
  git push origin phase-1-decommission-complete
  ```
- Hook location: prefer `homelab-playbook/.githooks/pre-push` tracked in git, with `git config core.hooksPath .githooks` set in repo (or documented as an operator install step). This avoids the `.git/hooks/` non-tracked-by-default trap.
- Hook logic (sketch):
  ```bash
  #!/usr/bin/env bash
  set -euo pipefail
  FORBIDDEN_PATTERN='mempalace\|omega'
  EXCLUDES=(--exclude-dir=.git --exclude-dir=_bmad-output --exclude-dir=docs/decommission --exclude-dir=stories)
  HITS=$(git diff --cached --name-only origin/main...HEAD 2>/dev/null \
         | xargs -r grep -l -i "$FORBIDDEN_PATTERN" "${EXCLUDES[@]}" 2>/dev/null || true)
  if [[ -n "$HITS" ]]; then
    echo "FORWARD-PROTECTION: push blocked — these files reintroduce mempalace/omega references:"
    echo "$HITS"
    echo "Override with: git push --no-verify (only for retro/archive commits per E1-S09)"
    exit 1
  fi
  ```
- Update the E1-S07 decommission doc with the AC7 section; this is a small append to an existing file.
- Per ADR-014's MoSCoW recalibration the FR for forward-protection isn't explicit; this story executes the spirit of FR-DEC-009 (zero references) extended *forward* in time, which is epic-level AC9.

## Test Plan

**Pre-test state check:**
```bash
git log --oneline | head -3   # confirm merge commit present
git tag -l phase-1-decommission-complete   # expect empty
ls -la .git/hooks/ homelab-playbook/.githooks/ 2>/dev/null
```

**Action — tag the merge commit:**
```bash
MERGE_SHA=$(git log --merges -1 --format=%H)
git tag -a phase-1-decommission-complete "$MERGE_SHA" \
  -m "Phase 1 decommission complete (Context Stack); rollback target per FR-DEP-007"
git push origin phase-1-decommission-complete
```

**Action — install hook:**
```bash
mkdir -p homelab-playbook/.githooks
$EDITOR homelab-playbook/.githooks/pre-push    # author per Implementation Notes sketch
chmod +x homelab-playbook/.githooks/pre-push
git config core.hooksPath homelab-playbook/.githooks
git add homelab-playbook/.githooks/pre-push
```

**Action — append AC7 doc section:**
```bash
$EDITOR homelab-playbook/docs/decommission/phase-1-context-stack.md   # add Forward Protection section
git add homelab-playbook/docs/decommission/phase-1-context-stack.md
```

**Test the hook negatively (AC3):**
```bash
git checkout -b test-forward-protection
echo "this references mempalace deliberately" > /tmp/test-forward.txt
git add /tmp/test-forward.txt   # would fail; instead create in repo:
echo "mempalace test" > homelab-playbook/test-forward.txt
git add homelab-playbook/test-forward.txt
git commit -m "test: forward-protection negative test"
git push origin test-forward-protection 2>&1 | grep -i "FORWARD-PROTECTION" && echo OK
# Cleanup
git reset --hard HEAD~1
git branch -D test-forward-protection
rm -f homelab-playbook/test-forward.txt
```

**Test the hook positively (AC4):**
```bash
# Add a benign change and confirm push succeeds
echo "# Phase-1 retrospective notes" >> homelab-playbook/docs/decommission/phase-1-context-stack.md
git add homelab-playbook/docs/decommission/phase-1-context-stack.md
git commit -m "docs(decommission): retro append"
git push   # expect: hook permits (mempalace/omega in this file is sanctioned; AC4 exclusion)
```

**Post-test state check:**
```bash
git tag -l phase-1-decommission-complete   # expect: phase-1-decommission-complete
test -x homelab-playbook/.githooks/pre-push && echo OK
git config core.hooksPath   # expect: homelab-playbook/.githooks
grep -c "Forward protection" homelab-playbook/docs/decommission/phase-1-context-stack.md   # expect ≥ 1
```

**Rollback procedure (per ADR-010):**
```bash
git tag -d phase-1-decommission-complete
git push origin :refs/tags/phase-1-decommission-complete
git rm homelab-playbook/.githooks/pre-push
git config --unset core.hooksPath
git revert <sha-of-this-commit>
```

## Dependencies

- **Blocks:** E2 (clean baseline confirmed; rollback target tagged → safe to start GitNexus install)
- **Blocked by:** E1-S08 (PR merge must have happened so merge-commit SHA exists); requires `main` branch to be at the merge commit

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Pre-push hook overreaches (blocks legitimate retro commits) | AC4 exclusions + AC6 `--no-verify` escape hatch; documented in the hook source |
| Operator forgets to set `core.hooksPath` on a fresh clone | Document the one-line install in `homelab-playbook/docs/decommission/phase-1-context-stack.md` (AC7 section); also note in the homelab-infra README setup steps |
| Tag accidentally placed on wrong SHA | AC1 verifies the tag → merge-commit SHA pairing via `git rev-parse`; `git tag -d` + re-tag on correction |
| Week-2 CI lint downgrade is forgotten, leaving the hook in place forever | AC7 documents the downgrade plan; track as a backlog item linked to E2 retro |

## Definition of Done

- [ ] All ACs pass
- [ ] Tag `phase-1-decommission-complete` exists locally and on origin
- [ ] `homelab-playbook/.githooks/pre-push` is executable and tracked in git
- [ ] Negative test (AC3) and positive test (AC4) both observed
- [ ] AC7 doc section appended to the decommission doc
- [ ] Backlog ticket filed for "week-2: replace pre-push with CI lint"
- [ ] Verify task added to `tests/acceptance.md` as `AT-EPIC-E1-AC9` (forward protection)
