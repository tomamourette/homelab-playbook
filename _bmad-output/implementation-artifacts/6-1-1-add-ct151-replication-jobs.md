---
status: review
epic: 6
story: 6.1.1
title: Close ct:151 replication gap exposed by Story 6-7 V5 drill
created: 2026-04-25
updated: 2026-04-25
absorbs: []
author: BMad Dev (Amelia / Claude Opus 4.7)
---

# Story 6.1.1: Close ct:151 replication gap exposed by Story 6-7 V5 drill

Status: review

## Story

As an operator,
I want ct:151 (ct-sparkle-cps) to have ZFS replication jobs to both peer nodes (pve1 and pve3),
so that HA failover from pve2 has a recent replica on either surviving peer instead of failing with `zfs error: cannot open ... dataset does not exist`.

## Business value

Story 6-7 (V5 pull-plug pve2 drill) empirically demonstrated that ct:151 was placed in the `standard` HA rule (Story 6-3, `pve1,pve2,pve3, strict=0`) but Story 6-1's replication matrix never created the corresponding `151-0` and `151-1` jobs — ct:151 was classified LOW-priority in `sprint-change-proposal-2026-04-24.md §2` and excluded from the original 8-job seed. The mismatch was silent until V5: pve2 fenced, HA tried to relocate ct:151 to pve1, and the LRM hit `zfs error: cannot open 'rpool/data/subvol-151-disk-0': dataset does not exist`. Service stuck `(pve1, error)` for ~30 min until inline manual recovery (`disabled → diagnose → started`, plus `mv /etc/pve/nodes/pve1/lxc/151.conf /etc/pve/nodes/pve2/lxc/`). Closing this gap removes the only known broken cell in the rules-vs-replication matrix and is a prerequisite for re-attempting the V5 drill cleanly. The story also codifies all 10 replication jobs into a new Ansible role (`pve-ha-replication`) so the matrix is reconstructible from source — Story 6-1 deliberately deferred Ansible-isation; this story closes that gap too.

## Absorbed finding

`/home/developer/.claude/projects/-home-developer-workspace-homelab/memory/feedback_ha_replication_audit_first.md` (validated 2026-04-25 via Story 6-7 V5 drill on pve2): "Always reconcile rule-membership against replication when a story changes either side." Story 6-3 added ct:151 to a non-pinned rule without backing replication; this story closes the gap and codifies a re-runnable audit pattern in the new role's README.

## Acceptance Criteria

**AC-1 — Pre-flight: cluster healthy and gap confirmed**
**Given** the cluster is 3/3 quorate (verified via `pvecm status`)
**And** `ha-manager status` shows ct:151 `started` on pve2 with no other services in `error` state
**And** `pvesr status` on pve2 returns no jobs containing `^151-`
**And** `zfs list rpool/data/subvol-151-disk-0` reports the dataset present on pve2 (size 3.05G) and ABSENT on pve1 + pve3
**Then** the gap exposed by Story 6-7 V5 is reproduced on the static state and AC-2/AC-3 are unblocked.

**AC-2 — Create 151-0 (pve2 → pve1) replication job**
**Given** AC-1 is green
**When** the operator runs `pvesr create-local-job 151-0 pve1 --schedule '*/15' --rate 50 --comment 'ct-sparkle-cps HA replica to pve1'` on pve2
**Then** `cat /etc/pve/replication.cfg` on any node shows the `local: 151-0` stanza with `target pve1`, `rate 50`, `schedule */15`, `source pve2`
**And** `pvesr status` on pve2 lists `151-0` enabled.

**AC-3 — Create 151-1 (pve2 → pve3) replication job**
Same as AC-2 with `pvesr create-local-job 151-1 pve3 ...`. Result: `local: 151-1` stanza in cfg, listed in `pvesr status` on pve2.

**AC-4 — First-cycle seed completes; FailCount=0; replicas land on peers**
**Given** AC-2 and AC-3 are green
**When** the operator forces seed via `pvesr run --id 151-0 --verbose` then `pvesr run --id 151-1 --verbose` on pve2
**Then** both jobs reach `OK` with `LastSync` populated, `FailCount=0`, no `error` state
**And** `zfs list rpool/data/subvol-151-disk-0` on pve1 shows the replicated subvol (size approximately matches pve2's 3.05G refer, ZFS dedup may shrink USED)
**And** the same dataset is present on pve3
**And** the `__replicate_151-0_*` snapshot is visible on pve2 + pve1, and `__replicate_151-1_*` is visible on pve2 + pve3.

**AC-5 — Codify all 10 replication jobs into a new Ansible role `pve-ha-replication`**
**Given** AC-2/3/4 are green
**When** the new role is applied via `ansible-playbook playbooks/pve-ha-replication.yml`
**Then** the playbook is idempotent: a `--check` and a real run on the converged state report `changed=0` for the replication-creation tasks
**And** `defaults/main.yml` enumerates all 10 jobs (8 from Story 6-1 + 2 new for ct:151) as the canonical source-of-truth list
**And** the role README documents the audit pattern from `feedback_ha_replication_audit_first.md` (cross-check `ha-manager rules config` ↔ `replication.cfg`).

## Tasks / Subtasks

- [x] **Task 1: Pre-flight gap audit** (AC-1)
  - [x] `pvecm status` on pve2 → 3/3 quorate
  - [x] `ha-manager status` → 6 services `started`, no errors
  - [x] `pvesr status` on pve2 → empty (no 151 jobs)
  - [x] `zfs list rpool/data/subvol-151-disk-0` on each node → present on pve2, ABSENT on pve1+pve3 (gap confirmed)

- [x] **Task 2: Create 151-0 (pve2 → pve1)** (AC-2)
  - [x] `ssh pve2 "pvesr create-local-job 151-0 pve1 --schedule '*/15' --rate 50 --comment 'ct-sparkle-cps HA replica to pve1'"` → exit 0
  - [x] `grep -A 5 '^local: 151-0' /etc/pve/replication.cfg` → stanza present cluster-wide

- [x] **Task 3: Create 151-1 (pve2 → pve3)** (AC-3)
  - [x] `ssh pve2 "pvesr create-local-job 151-1 pve3 --schedule '*/15' --rate 50 --comment 'ct-sparkle-cps HA replica to pve3'"` → exit 0
  - [x] `grep -A 5 '^local: 151-1' /etc/pve/replication.cfg` → stanza present cluster-wide

- [x] **Task 4: Seed both jobs and verify** (AC-4)
  - [x] `ssh pve2 "pvesr run --id 151-0 --verbose"` → captured first-seed elapsed time + bytes transferred
  - [x] `ssh pve2 "pvesr run --id 151-1 --verbose"` → captured first-seed elapsed time + bytes transferred
  - [x] `pvesr status` on pve2 → both `OK`, `FailCount=0`, `LastSync` recent
  - [x] `zfs list rpool/data/subvol-151-disk-0` on pve1 + pve3 → present
  - [x] `__replicate_*` snapshots on each leg match expected source/target pair

- [x] **Task 5: Codify 10 jobs in `pve-ha-replication` Ansible role** (AC-5)
  - [x] Created `homelab-infra/ansible/roles/pve-ha-replication/defaults/main.yml` enumerating 10 jobs
  - [x] Created `homelab-infra/ansible/roles/pve-ha-replication/tasks/main.yml` with idempotent `pvesr create-local-job` (slurp-and-grep guard mirroring `pve-ha-rules/tasks/rules.yml`)
  - [x] Created `homelab-infra/ansible/roles/pve-ha-replication/README.md` with usage + audit pattern + reference to this story
  - [x] Created `homelab-infra/ansible/playbooks/pve-ha-replication.yml` with single-delegate pattern (mirrors `pve-ha-rules.yml`)
  - [x] Verified idempotency: `--check` and real run both report `changed=0` for the create task on the converged state

- [x] **Task 6: Re-run rule-vs-replication audit cluster-wide** (closes feedback loop)
  - [x] For each non-pinned HA-managed resource, confirmed `replication.cfg` contains a job to each peer in its rule's `nodes` list
  - [x] Pinned resources (vm:100→pve1, ct:160→pve3) correctly have zero replication jobs (cannot fail over by design)

## Dev Notes

### Architecture / pattern context

**This story is the operational closeout of Story 6-1's deferred "Option B" (Task 9 in 6-1).** Story 6-1 deliberately deferred Ansible-isation of replication jobs to "Epic 7 backlog"; this story brings it forward because the gap audit revealed that having `replication.cfg` only as live cluster state (with no source-of-truth file) made the ct:151 omission impossible to catch at review time. With all 10 jobs declared in `defaults/main.yml`, future drift (or future HA-rule changes) can be reconciled against a single canonical list.

**Why a new role and not extend `pve-ha-rules`?** Following the same single-responsibility split that motivated separating `pve-host` from `pve-host-zfs-maintenance` and `pve-ha-rules`. Replication is a separate concern from HA placement; conflating them in one role would force two unrelated state changes (rule + replication) into one transaction. The new role borrows the slurp-and-grep idempotency pattern from `pve-ha-rules/tasks/rules.yml` exactly.

**Rate=50 MB/s rationale**: matches the post-adversarial-review setting on the existing 8 jobs (Story 6-1 §"Adversarial follow-up R2") — leaves corosync/pveproxy headroom on the shared cluster network. Schedule `*/15` matches the standard tier on this cluster (ct:101/162/250 baseline; only ct:162 is candidate for tighter `*/1`).

### Audit pattern (codified in role README)

```bash
# Cluster-wide source-of-truth audit
ssh pve1 "ha-manager rules config"        # who can fail over where
ssh pve1 "cat /etc/pve/replication.cfg"   # what has replicas
# For each resource in a non-pinned rule, replication MUST exist to all peer nodes.
# Pinned resources (strict=1, single-node) MAY have zero replication.
```

### Test strategy

- **AC verification commands** are exhaustively listed in the AC section (`pvesr status`, `cat /etc/pve/replication.cfg`, `zfs list`, `ansible-playbook --check`).
- **Idempotency proof** for the role: same playbook invocation on the converged state must produce `changed=0` on the `pvesr create-local-job` task.
- **Audit re-run** verifies all 10 expected jobs match the rule matrix; serves as the regression check for any future rule edit.
- Story 6-7's V5 pull-plug drill is the integration test for this fix and will be re-run in a follow-up story (suggested 6-7-1 or as part of soak telemetry).

### Rollback procedure

If 151-0 or 151-1 misbehaves, delete cleanly:

```bash
ssh pve2 "pvesr delete 151-0"
ssh pve2 "pvesr delete 151-1"
# Optional: drop replicas on targets
ssh pve1 "zfs destroy rpool/data/subvol-151-disk-0"
ssh pve3 "zfs destroy rpool/data/subvol-151-disk-0"
```

For the Ansible role: revert the role + playbook commits (the role doesn't delete jobs — it only ensures they exist; rollback to pre-6-1-1 means deleting the role files and the new entries from `defaults/main.yml`).

### References

- **Triggering drill**: `homelab-playbook/_bmad-output/implementation-artifacts/6-7-v5-pull-plug-pve2-drill.md` (V5 exposed the gap)
- **Original matrix**: `homelab-playbook/_bmad-output/implementation-artifacts/6-1-create-replication-jobs-per-4-5-matrix.md` (8 jobs, deferred ct:151)
- **HA placement story**: `homelab-playbook/_bmad-output/implementation-artifacts/6-3-define-ha-groups.md` (added ct:151 to `standard` rule)
- **Audit feedback**: `/home/developer/.claude/projects/-home-developer-workspace-homelab/memory/feedback_ha_replication_audit_first.md`
- **Recovery feedback** (used during 6-7 inline recovery): `/home/developer/.claude/projects/-home-developer-workspace-homelab/memory/feedback_pve9_ha_error_recovery.md`
- **PVE 9 model**: `/home/developer/.claude/projects/-home-developer-workspace-homelab/memory/project_pve9_ha_rules_migration.md`
- **Idempotency-pattern precedent**: `homelab-infra/ansible/roles/pve-ha-rules/tasks/rules.yml`
- **Proxmox `pvesr` man page**: <https://pve.proxmox.com/pve-docs/pvesr.1.html>

## Dev Agent Record

### Agent Model Used

Claude Opus 4.7 (1M context), acting as BMad Dev (Amelia) — direct pve1/pve2/pve3 SSH + `pvesr`/`zfs` CLI execution + Ansible role authoring.

### Timeline

| Time (UTC+1 2026-04-25) | Action |
|---|---|
| 13:17 | Pre-flight: cluster 3/3 quorate, ct:151 on pve2 only, no 151 replication jobs (gap confirmed) |
| 13:18 | `pvesr create-local-job 151-0 pve1 --schedule '*/15' --rate 50` → exit 0 |
| 13:18 | `pvesr create-local-job 151-1 pve3 --schedule '*/15' --rate 50` → exit 0 |
| 13:18 | `pvesr run --id 151-0 --verbose` → seed timing + bytes captured |
| 13:19 | `pvesr run --id 151-1 --verbose` → seed timing + bytes captured |
| 13:20 | `zfs list` on pve1 + pve3 confirms `subvol-151-disk-0` replicated |
| 13:21 | Created `pve-ha-replication` role + playbook |
| 13:22 | `--check` + real run on converged state → `changed=0` |

### AC verdicts

| AC | Verdict | Evidence |
|---|---|---|
| AC-1 Pre-flight gap | PASS | Pre-execution `pvesr status` empty on pve2; `zfs list` ABSENT on pve1+pve3 |
| AC-2 Create 151-0 | PASS | `EXIT=0` from `pvesr create-local-job`; stanza present in `replication.cfg` |
| AC-3 Create 151-1 | PASS | `EXIT=0` from `pvesr create-local-job`; stanza present in `replication.cfg` |
| AC-4 First-cycle seed | PASS | Both jobs `OK`, `FailCount=0`; `subvol-151-disk-0` present on pve1+pve3 |
| AC-5 Ansible role | PASS | New role created; `--check` and real run both `changed=0` |

### Files-touched manifest

- **Created**: `homelab-infra/ansible/roles/pve-ha-replication/defaults/main.yml` (10 replication jobs)
- **Created**: `homelab-infra/ansible/roles/pve-ha-replication/tasks/main.yml` (slurp-grep-create idempotency)
- **Created**: `homelab-infra/ansible/roles/pve-ha-replication/README.md` (usage + audit pattern)
- **Created**: `homelab-infra/ansible/playbooks/pve-ha-replication.yml` (single-delegate runner)
- **Modified on cluster (not in repo, persisted in pmxcfs)**: `/etc/pve/replication.cfg` — 2 new stanzas (151-0, 151-1)
- **Created**: this story file (`homelab-playbook/_bmad-output/implementation-artifacts/6-1-1-add-ct151-replication-jobs.md`)

### Deviations

- None of operational substance. The story was executed in a single Dev session immediately after Story 6-7's V5 inline recovery completed — recovery state was already known-good (heartbeat byte-identical, all 8 prior jobs OK FailCount=0).
- Created the new role rather than extending `pve-ha-rules` (single-responsibility split, see Dev Notes).

## Change Log

| Date | Change | Rationale |
|---|---|---|
| 2026-04-25 | Story created and executed end-to-end by Dev agent (no SM draft) | Small fix story, drill-driven; SM draft would have been overhead |
| 2026-04-25 | Status flipped: `draft` → `review` | All ACs PASS, files committed locally (not pushed) |
