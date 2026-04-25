# Sprint Change Proposal: Window B scope deltas + Epic 7 new stories

**Date:** 2026-04-24
**Author:** tomamourette (with BMad analyst assist)
**Change Type:** Scope revision on existing stories + New stories (additive) in Epic 7
**Scope Classification:** Minor

---

## Section 1: Issue Summary

### Problem Statement

Window B (Epic 5 pve2 reinstall) completed 2026-04-24 with three scope deltas vs. the original epic definition:

1. **Story 5-10** (Restore pve2 CTs): the operator chose to destroy 3 of the 4 pve2 CTs (105, 152, 153) during Window B prep rather than restore them. Only CT151 was preserved and migrated back.
2. **Story 5-11** (Update Terraform for pve2 CTs): the `ct_dev_homelab` module in `main.tf` now references a CT (VMID 150) that has been destroyed. Story's scope changes from "flip storage_id LVM→ZFS" to "remove the module entirely."
3. **Additional unplanned work in the same session:** DHCP reservations on the Asus router + authoring the pve-node-bootstrap Ansible playbook + documenting pve3's fixed-VRAM BIOS procedure. None fit cleanly in Epics 1–6; three new Epic 7 stories are added to capture them as reproducibility/guardrail work.

### Context

- Window B session produced artifact `implementation-artifacts/window-b-complete-2026-04-24.md` documenting the state
- Multiple manual recovery steps during pve2 cluster-join (fix `/etc/hosts`, fix `/etc/network/interfaces`, bidirectional SSH trust, etc.) took ~2 hours. Epic 3 (pve3 rebuild) is the next epic and is more complex — automating these steps before Epic 3 is high-ROI
- User decision to consolidate pve2's CT inventory during the same maintenance window simplified the state but diverges from the original "restore everything" plan

### Evidence

- `window-b-complete-2026-04-24.md` (full completion artifact)
- `sprint-status-pve3-storage-migration.yaml` (pre-update state showed all of this as `backlog`)
- Live cluster state at 2026-04-24: 3/3 quorate, all ZFS, RAM rebalanced, consolidated CT inventory

---

## Section 2: Approved Changes

### 2.1 Story 5-10 scope revision

**Original AC:** Restore CT105, CT151, CT152, CT153 from PBS to pve2's new ZFS storage.

**Revised AC:** Restore CT151 (ct-sparkle-cps) via PBS dump → restore → migrate-back. CT105/CT152/CT153 destroyed per operator decision during Window B prep (documented in window-b-complete-2026-04-24.md §"Workload consolidation"). Story status: `done-with-scope-change`.

**Rationale:** CT105 (pbs-migration) archive was rollback insurance for Window A which is now stable; CT152 (dev-test) was throwaway; CT153 (isabelle) no longer needed by operator. Reducing CT count on pve2 simplifies future HA planning and frees storage.

### 2.2 Story 5-11 scope revision

**Original AC:** Update Terraform `main.tf` storage_id from `local-lvm` → `local-zfs` for pve2 CT modules (ct_dev_homelab, ct_dev_test, ct_sparkle_cps, ct_isabelle).

**Revised AC:**
- `ct_dev_test` module: delete entirely (CT152 destroyed)
- `ct_isabelle` module: delete entirely (CT153 destroyed)
- `ct_dev_homelab` module: delete entirely (CT150 destroyed; the surviving workbench is CT250 on pve3, created outside Terraform)
- `ct_sparkle_cps` module: flip storage_id `local-lvm` → `local-zfs` (CT151 survives on pve2's new ZFS rpool)
- Run `terraform apply -refresh-only` to reconcile state with cluster reality

Story status: `revised-backlog` (scope known, execution pending).

**Rationale:** The destroys in 5-10 make the original flip-storage-id plan incorrect for 3 of the 4 modules. Deletion is the correct action.

### 2.3 New Story 7-8: DHCP reservations for all PVE MACs

**Story:**
> As an operator,
> I want pve1/pve2/pve3 MAC addresses to be bound to 192.168.50.201/202/203 respectively in the Asus router's DHCP reservation list,
> So that any future reinstall automatically receives the correct IP regardless of which port or driver order the installer chose.

**Acceptance Criteria:**
- **Given** the Asus router at 192.168.50.1 is the authoritative DHCP server
- **When** I set `dhcp_staticlist` via nvram with the 3 PVE MACs bound to their canonical IPs
- **Then** `/etc/dnsmasq.conf` on the router contains `dhcp-host=<MAC>,<IP>` lines for all 3
- **And** future DHCP requests from each MAC receive the reserved IP
- **And** the prior failure mode ("Window B install got 192.168.50.26 instead of .202") is impossible

**Status:** `done` (2026-04-24)

**Artifact:** Recorded in window-b-complete-2026-04-24.md §"Prevention for Epic 3". MACs: pve1 `00:d0:4c:10:40:54`, pve2 `00:d0:4c:10:41:d4`, pve3 `38:05:25:37:3d:cd`.

### 2.4 New Story 7-9: Ansible pve-node-bootstrap playbook

**Story:**
> As an operator,
> I want a single Ansible playbook that takes a freshly-auto-installed PVE node and joins it to the existing cluster with correct /etc/hosts, SSH trust, and pvecm membership,
> So that Epic 3 (pve3 rebuild) does not repeat Window B's 2 hours of manual recovery steps.

**Acceptance Criteria:**
- **Given** a freshly auto-installed PVE node is reachable via its DHCP-reserved IP using the Ansible controller's bootstrap SSH key (installed by answer.toml `[first-boot]`)
- **When** I run `ansible-playbook playbooks/pve-node-bootstrap.yml -l <node>`
- **Then** `/etc/hosts` on the target contains entries for all cluster nodes at their canonical IPs
- **And** `/etc/network/interfaces` has `bridge-ports` bound to the NIC with active link (auto-detected, not hardcoded)
- **And** bidirectional SSH root-key trust is established between the new node and all existing cluster members
- **And** `pvecm add --use_ssh --force <cluster-ip>` has executed and succeeded
- **And** `pvecm status` on all 3 nodes reports 3/3 quorate
- **And** the playbook is idempotent — re-running produces zero changes
- **And** the playbook is documented in `homelab-infra/ansible/playbooks/README.md`
- **And** a pve3-specific answer.toml (`pve3-answer.toml`) exists in `homelab-infra/proxmox/answer-files/` with serial-based disk filters and `zfs.hdsize=828` to match Story 3.2 partition layout

**Status:** `backlog` (prerequisite for Epic 3 — blocks Story 3.3)

### 2.5 New Story 7-10: pve3 fixed VRAM BIOS configuration runbook

**Story:**
> As an operator,
> I want a documented runbook for configuring pve3's BIOS to allocate 24 GB fixed VRAM to the Radeon 890M iGPU,
> So that when pve3 reboots (during Epic 3 reinstall or a planned maintenance window), I can correctly apply the fixed-VRAM setting and Ollama can reliably detect the iGPU.

**Acceptance Criteria:**
- **Given** pve3 is the MinisForum N5 Pro with AMD Ryzen AI 9 HX PRO 370 and Radeon 890M iGPU
- **When** I follow `implementation-artifacts/pve3-bios-vram-24gb-guide.md`
- **Then** BIOS UMA Frame Buffer Size is set to 24 GB Fixed (not Dynamic/Auto)
- **And** after boot, `dmesg | grep -i amdgpu` shows 24 GB allocated to the iGPU
- **And** `rocm-smi --showmeminfo vram` or equivalent reports ~24 GB available
- **And** Ollama inside ct-ai-01 detects the iGPU (relevant to known Ollama issue #11451 with gfx1150 Dynamic VRAM)
- **And** the guide covers: pre-boot checklist, BIOS key to press, exact menu path, setting name, verification commands, rollback procedure

**Status:** `backlog` (will be referenced during Epic 3 Story 3.2 or a dedicated pve3 reboot maintenance window)

---

## Section 3: Impact on Other Work

- **Epic 3 timeline:** Story 7-9 (pve-node-bootstrap playbook) becomes a prerequisite. Estimated 2–4 hours to author + test. Recommend executing before Epic 3 kickoff.
- **Epic 5 closure:** With 5-7 through 5-13 all done or revised-done, Epic 5 can be marked `done-with-exceptions` (exceptions = 5-10, 5-11 scope revisions captured in this proposal).
- **Epic 7 scope:** Grows from 7 stories to 10 stories. Still completable in parallel/desk-work mode; not a critical path blocker beyond 7-9.

## Section 4: Changes to sprint-status-pve3-storage-migration.yaml

See updated YAML. Summary of diffs vs 2026-04-20 baseline:
- Epic 5: `in-progress` → `done-with-exceptions`
- Stories 5-7, 5-8, 5-9, 5-12, 5-13: `backlog` → `done`
- Story 5-10: `backlog` → `done-with-scope-change`
- Story 5-11: `backlog` → `revised-backlog`
- Story 2-11: `backlog` → `ready-to-execute` (soak window expired)
- Epic 7: added 7-8 (done), 7-9 (backlog), 7-10 (backlog)

---

## Approval

Operator: tomamourette — approved inline 2026-04-24
Implementation: immediate (documentation refresh, no code deploy required for the scope changes themselves)
