---
type: story
epic: FE0
id: FE0-S05
title: "Stash or exclude the uncommitted ct_sparkle_vlabel (VMID 166) block and decide its fate"
size: XS
priority: MUST
owner: operator
blocking: false
fr_refs: [FR-PRE-006]
nfr_refs: []
adr_refs: []
risk_refs: []
gate_refs: [j]
status: done
date: 2026-09-09
---

# FE0-S05: Stash or exclude the uncommitted ct_sparkle_vlabel (VMID 166) block and decide its fate

## User Story

As **tomamourette**, I want **the uncommitted `module "ct_sparkle_vlabel"` block removed from the working tree (or otherwise excluded from any plan/apply) before CT 167 is provisioned**, so that **a bare `terraform plan` or `apply` cannot accidentally recreate a container I already destroyed, and VMID 167 is unambiguously the next free slot**.

## Background and Context

Per the canon's verified fact table and evidence **E7**: `homelab-infra/terraform/envs/homelab/main.tf:280-304` contains an **uncommitted working-tree** `module "ct_sparkle_vlabel"` block (VMID 166), re-verified this pass via `git diff` as **+27 unstaged lines**, for a container that was **destroyed on 2026-07-28** and deliberately left uncommitted (per the operator's own auto-memory: `project_sparkle_vlabel.md` — "was created 2026-06-15 but NO LONGER EXISTS as of 2026-07-28; its Terraform block is a phantom, deliberately left uncommitted"). This is not new information; it is a known, standing piece of drift that this PoC's FE1-S01/FE1-S02 work would otherwise walk straight into. If FE1-S01 appends `module "ct_forge_01"` to the same file without first dealing with the phantom block, a subsequent `terraform apply` risks recreating `ct-sparkle-vlabel` as an unintended side effect — exactly the failure mode gate (j) exists to catch ("the `ct_sparkle_vlabel` phantom has not been recreated").

**The fate decision is explicitly an operator call and this story does not make it.** Two outcomes are possible — delete the block entirely (if `ct-sparkle-vlabel` will never return), or commit it in a disabled/commented state (if it might be recreated later under a different plan) — and this proposal takes no position on which. What this story **does** require is that, whichever fate is chosen, the block cannot silently participate in the narrowly-`-target`ed plan that FE1-S02 will run for CT 167, and that **167 is confirmed as the correct next free VMID** in the 162–169 project block once the phantom is out of the way.

## Acceptance Criteria

**AC1 — Phantom block re-confirmed via `git diff`.**
- **Given** the canon's claim that `main.tf:280-304` is uncommitted,
- **When** the operator runs `git diff -- homelab-infra/terraform/envs/homelab/main.tf | grep -A2 "module \"ct_sparkle_vlabel\""`,
- **Then** the block appears in the diff as unstaged, confirming it has not drifted into a committed state since the canon was written.

**AC2 — Fate decided and recorded (operator call, recorded as open until decided).**
- **Given** AC1 confirms the phantom is still present,
- **When** the operator chooses one of: (a) `git checkout -- homelab-infra/terraform/envs/homelab/main.tf` to discard the block entirely, or (b) commit the block with an explicit `count = 0` / disabled marker and a comment explaining why it is retained but inert,
- **Then** the choice and its rationale are recorded in this story's Definition of Done — **this AC is satisfied by an explicit recorded decision, not by a default action taken without operator sign-off.**

**AC3 — VMID 167 confirmed as next free slot post-resolution.**
- **Given** AC2's decision has been applied,
- **When** the operator runs `pct list` on each of pve1, pve2, and pve3, and cross-checks against `terraform state list | grep ct_`,
- **Then** no CT with VMID 166 exists anywhere in the cluster or in Terraform state, and 167 is confirmed free for FE1-S01.

**AC4 — `terraform plan` on the homelab root does not touch `ct_sparkle_vlabel` (gate j precondition).**
- **Given** AC2's decision has been applied,
- **When** the operator runs a scoped `terraform plan` against `homelab-infra/terraform/envs/homelab` (even before FE1-S01's `module "ct_forge_01"` exists, as a baseline check),
- **Then** the plan output contains no reference to `ct_sparkle_vlabel` creating, destroying, or modifying anything — laying the groundwork for gate (j)'s later, stricter check.

## Implementation Notes

Reference evidence **E7**, canon fact row "VMID 166 is a phantom," and the operator's own memory file `~/.claude/projects/-home-developer-workspace-homelab/memory/project_sparkle_vlabel.md`. This story is **documents-and-git-state only** with respect to a decision — the actual `git checkout` or commit action is a small, low-risk operation the operator or a dev under operator instruction can perform, but the **decision itself is not delegable**.

```bash
# AC1 — reconfirm the phantom
git diff -- homelab-infra/terraform/envs/homelab/main.tf | grep -A2 'module "ct_sparkle_vlabel"'

# AC2(a) — discard entirely
git checkout -- homelab-infra/terraform/envs/homelab/main.tf

# AC2(b) — alternative: commit disabled, e.g. wrap in a `count = 0` guard with a comment,
# then `git add` and commit with a message referencing this story and FR-PRE-006.

# AC3 — confirm no live CT 166 anywhere
for node in pve1 pve2 pve3; do ssh root@$node "pct list | grep -w 166"; done
terraform state list | grep ct_sparkle_vlabel

# AC4 — baseline plan, no phantom involvement
cd homelab-infra/terraform/envs/homelab && terraform plan | grep -i sparkle_vlabel
# Expected: no output
```

## Test Plan

**Pre-state:** `git diff` shows the uncommitted `ct_sparkle_vlabel` block at `main.tf:280-304`; VMID 166 does not exist on any node.

**Action sequence:**
1. Reconfirm the phantom via `git diff` (AC1).
2. Operator decides and records the fate (AC2).
3. Apply the decision (discard or commit-disabled).
4. Confirm VMID 166 absence cluster-wide (AC3).
5. Run a baseline `terraform plan` and confirm no `ct_sparkle_vlabel` reference (AC4).

**Post-state checks:**
- `git status` on `homelab-infra` shows no uncommitted `ct_sparkle_vlabel` changes (either discarded or committed).
- `pct list` on all three nodes shows no VMID 166.
- `terraform plan` baseline is silent on `ct_sparkle_vlabel`.

**Rollback:** If the block was discarded (AC2a) and the operator later wants it back, it is only recoverable from the working-tree diff captured in AC1's evidence or from operator memory of its prior shape — there is no other copy, since it was never committed. If committed disabled (AC2b), `git revert` restores the pre-story state.

## Dependencies

- **Blocked by:** Nothing.
- **Blocks:** FE1-S01 (must not append `module "ct_forge_01"` to a file still carrying the live uncommitted phantom without this resolution happening first) and gate (j) in FE4-S02.

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Operator discards the block, but later wants `ct-sparkle-vlabel` recreated under a new plan and has to redesign it from scratch (nothing was ever committed to reconstruct from) | Low | Low — a redesign is not necessarily worse than reusing the phantom's shape | AC2 requires the decision and rationale be recorded, so at minimum the *reasoning* survives even if the Terraform block does not |
| The block is committed disabled (AC2b) but a future bulk edit or `count` refactor accidentally re-enables it | Low | Medium — would recreate a destroyed container unexpectedly | Gate (j) in FE4-S02 exists precisely to catch this regression before any apply lands |

## Definition of Done

- [ ] AC1–AC4 all green and evidenced.
- [ ] Fate decision recorded here: _______________ (filled in by operator at execution time — discard or commit-disabled, with rationale).
- [ ] VMID 166 confirmed absent from all three Proxmox nodes and from Terraform state.
- [ ] Baseline `terraform plan` on the homelab root shows no `ct_sparkle_vlabel` activity.
- [ ] Story status updated from `draft` to `done` in this file's frontmatter.
