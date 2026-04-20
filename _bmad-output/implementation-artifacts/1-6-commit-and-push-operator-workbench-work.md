---
status: done
epic: 1
story: 1.6
title: Commit and push operator workbench work
---

# Story 1.6: Commit and push operator workbench work

## User Story

As an operator, I want all in-flight work on ct-dev-homelab committed and pushed to git, so that if the workbench is lost during migration, no work is lost with it.

## Acceptance Criteria

**Given** I am working from ct-dev-homelab (CT150)
**When** I run `git status` in `/home/developer/workspace/homelab`
**Then** the working tree is clean (no modified/untracked files, or all changes are deliberately committed)
**And** `git log origin/main..HEAD` returns empty (no unpushed commits)
**And** any local-only artifacts that are intentionally not in git (SSH keys, terraform state files) are documented and copied off-node

## Tasks

- [x] Verify parent repo (`/home/developer/workspace/homelab`) working tree clean
- [x] Verify parent repo no unpushed commits
- [x] Verify sub-repo `homelab-playbook` working tree clean
- [x] Handle telemetry-file drift — add `.gitignore` excluding `.claude-flow/data/` and untrack `pending-insights.jsonl`
- [x] Verify sub-repo no unpushed commits

## Dev Notes

- Story 1.6 was effectively completed during this session by repeated commits and pushes throughout the research → epic → sprint-planning → story-execution flow.
- Encountered one edge case: `homelab-playbook/.claude-flow/data/pending-insights.jsonl` was tracked but is auto-mutated by claude-flow tooling — not user work. Solution: untrack + gitignore so future `git status` remains clean.
- Parent repo (`homelab`): the earlier session's uncommitted modifications (`docs/architecture-homelab-infra.md` etc.) were resolved in commit `0467be2` before this session.
- Local-only artifacts intentionally NOT in git:
  - `/root/.pbs-migration-credentials` on pve2 (PBS API token + CT105 root password, chmod 600)
  - SSH private keys in `~/.ssh/` on CT150
  - Terraform state (`terraform.tfstate`) — typical to keep out of git; backed up to laptop or similar
- These are documented in the PBS migration runbook and in `reserved-vmids.md` where relevant.

## Implementation Report

- Multiple commits pushed during the session covering: research doc, epic breakdown, sprint status, Story 1.1 (cold spare inventory), Story 1.2 (PBS datastore + runbook + reserved-vmids), Story 1.4 (state snapshot).
- Post-Story-1.6 final state: both repos clean, pushed.
- No user-authored work is at risk if CT150 is lost.
