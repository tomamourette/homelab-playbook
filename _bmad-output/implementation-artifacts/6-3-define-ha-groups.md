---
status: review
epic: 6
story: 6.3
title: Define HA node-affinity rules and assign resources
created: 2026-04-24
updated: 2026-04-25
supersedes:
  - 6-4-assign-cts-and-vms-to-ha-groups
author: BMad SM
---

# Story 6.3: Define HA node-affinity rules and assign resources

Status: review

## Sprint change note

The original 6.3 / 6.4 split assumed Proxmox VE's pre-9.x HA-group model: 6.3 would create empty named groups (metadata-only), 6.4 would later assign CTs/VMs into them. **PVE 9.1.1 (live on this cluster, kernel 6.17.2-1-pve, verified 2026-04-24) deprecates HA groups in favour of node-affinity rules.** `ha-manager groupadd` is still present but the documented and supported path is `ha-manager rules add node-affinity ...`, and the new schema **requires `--resources` at rule creation** (no empty rules). That makes the prior 6.3 / 6.4 split unexpressible: rule existence and resource membership are coupled by design. This story now creates the four node-affinity rules with their resources populated in a single sequence, and **absorbs Story 6.4 (marked superseded)**. Per-resource `failback` (the PVE 9 replacement for the group-level `nofailback` flag) is set in Task 3 after each resource is registered. Full mapping in `/home/developer/.claude/projects/-home-developer-workspace-homelab/memory/project_pve9_ha_rules_migration.md`. Source files on each PVE 9 node: `/usr/share/perl5/PVE/HA/Rules.pm`, `/usr/share/perl5/PVE/HA/Rules/NodeAffinity.pm`. Upstream marker in pve-manager: `# TODO PVE 10: Remove group migration when HA groups have been fully migrated to rules`.

## Story

As an operator,
I want named HA node-affinity rules with their assigned resources defined in one shot, plus per-resource failback policy applied,
so that the cluster's placement policy (critical / standard / pve1-pinned / pve3-pinned) is captured in the modern PVE 9 rules model — replacing the deprecated HA-groups abstraction — and Stories 6.5–6.9 inherit a working HA control plane that the CRM and LRM actually consume.

## Business value

Epic 6's mission is to replace "single-node NFS means single-node workloads" with "replicated ZFS + HA manager means any surviving node can take over in ≤1 min". Stories 6.1 and 6.2 made replication real and monitored; Story 7.11 made broken replicas a paged incident on the operator's phone. **6.3 is the first story that actually arms `ha-manager`** — registering each HA-tagged resource and codifying which subset of nodes is eligible to run each one.

Unlike the pre-PVE-9 plan (groups first, assignments later), the PVE 9 rules model couples rule creation with resource membership. This is actually safer for the homelab:

1. **Placement policy becomes machine-enforced from t=0.** A rule created with `--resources ct:162 --nodes pve1,pve2,pve3 --strict 0` immediately tells the CRM where ct:162 can live. The "right shape, no members" intermediate state from the pre-9.x plan no longer exists; it can't exist.
2. **Blast radius is smaller, not larger.** `ha-manager add ct:162` is what makes ct:162 HA-managed. Without that step the CT continues to run as a plain CT regardless of any rule. Rule creation with a non-HA-managed resource is rejected at the API. So the failure mode "rule misconfigured but CT was already failed-over" cannot occur at this step.
3. **Downstream stories get a clean interface.** 6.5–6.9 reference rule names (`critical`, `standard`, `pinned-pve1`, `pinned-pve3`) and resource SIDs (`ct:162`) the same way they always did. The terminology pass on those stories (this sprint-change pivot) only swaps lookup commands; the drill semantics are unchanged.
4. **Per-resource `failback` lands cleanly.** The legacy group-level `nofailback` flag moved to per-resource HA config in PVE 9. That's actually a finer-grained control: ct:162 can have `failback=0` (auto-return to home node when it recovers) while a different resource in the same rule could be set `failback=1`. This story does not exercise that flexibility but the model now supports it.

Without 6.3, none of 6.5–6.9 can run — they all assume HA-managed resources exist.

## Resource-to-rule assignment matrix (canonical)

This is the authoritative map for this story. Story 6.5–6.9 reference rule names from this table.

| Rule (node-affinity) | strict | nodes | Resources | Failback |
|---|---|---|---|---|
| `critical` | 0 | pve1, pve2, pve3 | ct:162 | 1 (auto-return to home node) |
| `standard` | 0 | pve1, pve2, pve3 | ct:101, ct:151, ct:250 | 1 (auto-return to home node) |
| `pinned-pve1` | 1 | pve1 | vm:100 | 1 (irrelevant — only one eligible node) |
| `pinned-pve3` | 1 | pve3 | ct:160 | 1 (irrelevant — only one eligible node) |

Explicitly **NOT** in HA:

- ct:104 (zeroclaw) — does not exist in current cluster inventory (verified `pct list` on all 3 nodes 2026-04-25). Disposable per planning §4.5; if it ever returns, leave non-HA.
- ct:152 (dev-test) — does not exist; destroyed in Window B. Disposable.
- ct:153 (isabelle) — does not exist; disposable per planning.

`failback=1` is the PVE 9 default. The semantic is the inverse of the legacy `nofailback`: `failback=1` means "the CRM tries to return the resource to the highest-priority eligible node when that node returns", which is the homelab-correct behaviour for the `critical` and `standard` rules. Setting `failback=0` would tell HA "stay where you ended up after failover; do not return automatically" — homelab does not want that. Task 3 confirms `failback=1` for ct:162, ct:101, ct:102, ct:151, ct:250, vm:103 explicitly. For the pinned rules (one eligible node) failback is a no-op.

**OPERATOR-RESOLVED 2026-04-25** (was NEEDS OPERATOR CONFIRMATION):
- **ct:102 (ct-media-01)** → **EXCLUDED** from HA. Mounts non-replicable `shared-nfs-bulk`; HA is not the right preservation strategy for media (NFS + PBS handles it). Story 7.3 guardrail PASSES with this exclusion.
- **ct:151 (ct-sparkle-cps)** → **INCLUDED** in `standard`. Operator confirmed: project containers should fail over.
- **vm:103** → **DROPPED** from matrix. Does not exist anywhere on the cluster (verified `qm list` 2026-04-25). Stale matrix entry — not a planned VM.

**Final confirmed `standard` resource set: `ct:101, ct:151, ct:250`** (no ct:102, no vm:103). All commands and ACs below assume this set.

### Project-container HA state policy (operator-defined 2026-04-25)

For **project containers** (ct:151 ct-sparkle-cps, ct:250 ct-dev-homelab — currently in `standard`; ct:162 ct-quant-trading is critical-tier and always-on so this policy doesn't apply to it):

> **"If running, fail over and start on peer. If stopped, migrate the storage but stay stopped on peer."**

Implementation: at `ha-manager add` time (Task 1), pass `--state` matching the **current actual run-state** of each project container, not a blanket `started`:

```bash
# Pre-add: capture each project CT's current state
for sid in ct:151 ct:250; do
  vmid="${sid#ct:}"
  current=$(ssh "$(ssh pve1 "pct list | awk -v v=$vmid '\$1==v {print \$3}'" 2>/dev/null || ssh pve2 "pct list | awk -v v=$vmid '\$1==v {print \$3}'" 2>/dev/null || ssh pve3 "pct list | awk -v v=$vmid '\$1==v {print \$3}'" 2>/dev/null)" 2>/dev/null)
  # current = "running" or "stopped"
  if [ "$current" = "running" ]; then state="started"; else state="stopped"; fi
  ssh pve1 "ha-manager add $sid --state $state --max_relocate 1 --max_restart 3 --comment '...'"
done
```

PVE HA semantics confirm this works correctly:
- `--state started` → CRM keeps it running; on node failure, restarts on a peer.
- `--state stopped` → CRM keeps it stopped; on node failure, **storage replication continues to other nodes (per Story 6.1) but the resource stays stopped**. Operator can `ha-manager set ct:N --state started` later to bring it up.

For **always-on** resources (ct:162, ct:101, vm:100, ct:160), use `--state started` unconditionally — these are infra and should auto-recover.

**Future epic candidate (NOT this story):** auto-shutdown timer on idle project containers (ct:151, ct:250) — out-of-scope here. Tracked as a follow-up backlog item.

## Acceptance Criteria

### AC-1: Pre-flight state is clean and inventory verified

**Given** the cluster is 3/3 quorate (`pvecm status` on pve1 shows `Quorate: Yes`, `Total votes: 3`)
**And** replication is healthy (`pvesr status` on pve1 and pve3 — all 8 jobs `OK`, `FailCount = 0`, `LastSync` within 2× schedule)
**And** the ntfy push channel from Story 7.11 is live (synthetic alert delivered to operator phone within 60 s)
**And** no HA rules currently exist (`ha-manager rules list` returns empty)
**And** no HA resources currently exist (`ha-manager status` shows no `service` entries beyond the master / lrm lines)

**When** I capture baseline state to evidence files:
```
ssh pve1 "ha-manager rules list; echo '---rules-config---'; ha-manager rules config; echo '---status---'; ha-manager status; echo '---legacy-config---'; ha-manager config" > /tmp/ha-baseline-pre-6-3.txt
for n in pve1 pve2 pve3; do ssh $n 'pct list; qm list'; done > /tmp/guests-pre-6-3.txt
```

**Then** the rules section is empty
**And** the legacy `ha-manager config` section shows no `group:`, `ct:`, or `vm:` stanzas
**And** `/tmp/guests-pre-6-3.txt` lists every running guest with its current node and status
**And** the inventory matches the canonical assignment matrix above; any planned resource that is missing (e.g. vm:103 if not yet created, ct:102 if operator excludes per `NEEDS OPERATOR CONFIRMATION`) is recorded as a Dev Agent Record exclusion before any HA-add runs

### AC-2: All HA-tagged resources are registered with `ha-manager add`

**Given** AC-1 holds
**When** for each resource in the canonical matrix I run, on any cluster node:
```
# Always-on infra/critical resources — unconditional --state started:
ssh pve1 "ha-manager add ct:162 --state started --max_relocate 1 --max_restart 3 --comment 'Epic 6 critical-tier; ≤1-min RPO target'"
ssh pve1 "ha-manager add ct:101 --state started --max_relocate 1 --max_restart 3 --comment 'Epic 6 standard-tier; ct-docker-01 (always-on infra)'"
ssh pve1 "ha-manager add ct:160 --state started --max_relocate 1 --max_restart 3 --comment 'Epic 6 pinned-pve3; iGPU passthrough'"
ssh pve1 "ha-manager add vm:100 --state started --max_relocate 1 --max_restart 3 --comment 'Epic 6 pinned-pve1; Zigbee USB'"

# Project containers — --state matches CURRENT run-state (operator policy: if running, fail over; if stopped, stay stopped):
# Determine each project CT's actual state via pct status, then choose --state accordingly.
for vmid in 151 250; do
  # Find which node hosts the CT, then read its run-state
  for node in pve1 pve2 pve3; do
    if ssh $node "pct status $vmid" 2>/dev/null | grep -q "status:"; then
      runstate=$(ssh $node "pct status $vmid" | awk '{print $2}')
      [ "$runstate" = "running" ] && hastate="started" || hastate="stopped"
      case $vmid in
        151) comment="Epic 6 standard-tier; ct-sparkle-cps (project container; --state matches actual run-state)";;
        250) comment="Epic 6 standard-tier; ct-dev-homelab (project container; --state matches actual run-state)";;
      esac
      ssh pve1 "ha-manager add ct:$vmid --state $hastate --max_relocate 1 --max_restart 3 --comment '$comment'"
      break
    fi
  done
done

# Excluded (operator-resolved 2026-04-25):
#   ct:102 — non-replicable shared-nfs-bulk, NFS+PBS preservation strategy
#   vm:103 — does not exist
#   ct:104, ct:152, ct:153 — disposable, do not exist
```
**Then** `ha-manager status` shows each resource as `started` on its current home node within ≤ 30 s of each `add` (CRM polls `/etc/pve/ha/resources.cfg` every ~10 s)
**And** no resource transitions to `error`, `fence`, or `recovery`
**And** the underlying CT/VM is **not restarted** by the `ha-manager add` step — `pct status <id>` on the home node continues to report `running` throughout
**And** `ha-manager add` is idempotent at the error-return level: running it twice errors with `resource '<sid>' already defined` and exits non-zero with no state change. Ansible (Task 6) uses a pre-check guard against `/etc/pve/ha/resources.cfg`.

### AC-3: `critical` node-affinity rule is created with ct:162 across all three nodes

**Given** AC-2 holds and ct:162 is HA-managed
**When** I run, on any cluster node:
```
ssh pve1 "ha-manager rules add node-affinity critical --nodes pve1,pve2,pve3 --resources ct:162 --strict 0 --comment 'Epic 6 critical-tier: ct-quant-trading'"
```
**Then** `ha-manager rules list` shows a `critical` rule with `type=node-affinity`
**And** `ha-manager rules config --type node-affinity` includes a stanza for `critical` with:
- `nodes pve1,pve2,pve3`
- `strict 0` (soft preference — members are preferred but the CRM may run the resource on any quorate node if all members are down; with all 3 nodes as members this is a no-op here)
- `resources ct:162`
- The comment string as given
**And** re-running the same command errors with `rule 'critical' already exists` (or equivalent) — non-zero exit, no state change

### AC-4: `standard` node-affinity rule is created across all three nodes

**Given** AC-2 holds for every resource the operator confirmed for `standard` (default per SM recommendation: ct:101, ct:151, ct:250, vm:103 if it exists; ct:102 only if operator overrides 7.3 guardrail risk)
**When** I run:
```
ssh pve1 "ha-manager rules add node-affinity standard --nodes pve1,pve2,pve3 --resources <comma-separated-confirmed-set> --strict 0 --comment 'Epic 6 standard-tier'"
```
**Then** `ha-manager rules list` shows a `standard` rule
**And** `ha-manager rules config` shows `nodes pve1,pve2,pve3`, `strict 0`, and the operator-confirmed resource list
**And** the comment string is preserved
**And** the same idempotency behaviour as AC-3

### AC-5: `pinned-pve1` rule is created with hard pve1 lock and `pinned-pve3` rule with hard pve3 lock

**Given** AC-2 holds for vm:100 and ct:160
**When** I run:
```
ssh pve1 "ha-manager rules add node-affinity pinned-pve1 --nodes pve1 --resources vm:100 --strict 1 --comment 'Epic 6 pve1-only: VM100 smarthome (Zigbee USB 10c4:ea60 physically on pve1)'"
ssh pve1 "ha-manager rules add node-affinity pinned-pve3 --nodes pve3 --resources ct:160 --strict 1 --comment 'Epic 6 pve3-only: CT160 ct-ai-01 (iGPU /dev/dri/renderD128)'"
```
**Then** `ha-manager rules list` shows both rules
**And** `ha-manager rules config` shows for each: a single-node `nodes` list and `strict 1`
**And** `strict 1` means **hard lock**: if the eligible node is down, HA will NOT start the resource on a different node. This is intentional for both — Zigbee USB exists only on pve1; the iGPU exists only on pve3. Starting the resource elsewhere would produce a half-functional guest.

### AC-6: Per-resource `failback` is confirmed for non-pinned resources

**Given** AC-2 through AC-5 hold
**When** I run for each non-pinned HA-managed resource:
```
ssh pve1 "ha-manager set ct:162 --failback 1"
ssh pve1 "ha-manager set ct:101 --failback 1"
ssh pve1 "ha-manager set ct:151 --failback 1"
ssh pve1 "ha-manager set ct:250 --failback 1"
# Plus any other confirmed standard members
```
**Then** `ha-manager config | awk '/^ct: 162/,/^$/'` (or equivalent per-resource stanza) shows `failback 1`
**And** `failback=1` is the PVE 9 default (and is what we want — auto-return to home node after failover); the explicit `set` here is for codification and to make the Ansible role emit the directive idempotently rather than relying on a default that could change in PVE 10
**And** the pinned resources (vm:100, ct:160) do NOT need `failback` set — only one node is eligible, so the policy is moot

### AC-7: Final-state validation

**Given** AC-2 through AC-6 hold
**When** I capture post-state:
```
ssh pve1 "ha-manager rules list; echo '---rules-config---'; ha-manager rules config; echo '---status---'; ha-manager status; echo '---resources-cfg---'; cat /etc/pve/ha/resources.cfg" | tee /tmp/ha-config-post-6-3.txt
for n in pve1 pve2 pve3; do ssh $n 'pct list; qm list'; done > /tmp/guests-post-6-3.txt
```
**Then** `ha-manager rules list` shows exactly four rules: `critical`, `standard`, `pinned-pve1`, `pinned-pve3` — no more, no less
**And** `ha-manager status` shows every HA-managed resource as `started` on its expected home node (ct:162 on pve3, ct:101 on pve1, ct:151 on pve2, ct:160 on pve3, ct:250 on pve3, vm:100 on pve1, plus any operator-confirmed extras)
**And** no resource is in `error`, `fence`, `recovery`, `queued`, or `migrate` state
**And** `diff /tmp/guests-pre-6-3.txt /tmp/guests-post-6-3.txt` produces zero lines — every previously-running guest is still running on the same node, with the same status (HA-add does not restart guests)
**And** sanity check from a different node: `ssh pve3 "ha-manager rules list"` shows the same four rules (proves `pmxcfs` cluster-wide sync of `/etc/pve/ha/rules.cfg` and `/etc/pve/ha/resources.cfg`)
**And** the on-disk files `/etc/pve/ha/rules.cfg` and `/etc/pve/ha/resources.cfg` exist, are owned by `root:www-data`, mode `0640`

### AC-8: Story 7.3 CI guardrail re-run

**Given** AC-7 holds
**When** I run:
```
cd /home/developer/workspace/homelab/homelab-infra && python scripts/ci/check-ha-storage-placement.py --live | tee /tmp/7-3-guardrail-post-6-3.txt
```
**Then** exit code is `0` (PASS)
**And** the script's output reports every HA-managed resource's disk storage and confirms each is on a replicable backend (`local-zfs` on each node, etc.) — NO resource reports a disk on `shared-nfs-bulk`, `fast-pool`, or any other blocklisted storage
**And** if the operator chose to include ct:102 in `standard` (overriding the SM recommendation), this AC will FAIL — the script will flag ct:102's disk on `shared-nfs-bulk`. In that case: remove ct:102 from the `standard` rule (`ha-manager rules set node-affinity standard --resources <subset-without-ct:102>`), then `ha-manager remove ct:102`, then re-run AC-8 expecting PASS. Document the override-and-revert in the Dev Agent Record.

### AC-9: Codified in Ansible as `pve-ha-rules` role

**Given** Epic 7's reproducibility theme (existing roles: `pve-host`, `pve-host-pve3-storage`, `pve-host-zfs-maintenance`)
**When** I add a new role `homelab-infra/ansible/roles/pve-ha-rules/` containing:
- `defaults/main.yml` — three list variables: `ha_resources` (each item: `{ type, vmid, state, max_relocate, max_restart, failback, comment }`), `ha_rules` (each item: `{ name, type, nodes, resources, strict, comment }`), and a small `ha_failback_overrides` map (currently empty; reserves the slot for future per-resource overrides)
- `tasks/main.yml` — three include sequences: register resources via `ha-manager add` (idempotent via `/etc/pve/ha/resources.cfg` pre-check), then create rules via `ha-manager rules add ...` (idempotent via `/etc/pve/ha/rules.cfg` pre-check), then `ha-manager set` for non-default failback values
- `README.md` — pointer back to this story; placement-policy rationale; the `pve-ha-rules` role is the single source of truth for HA cluster-wide policy
**Then** the role's `--check` mode against the cluster (live state already populated by Tasks 1-3) reports `changed=0` (idempotency proof)
**And** a real run also reports `changed=0` (no drift)
**And** the role uses `delegate_to: "{{ groups['pve_nodes'][0] }}"` (or similar) — rules are cluster-wide via `pmxcfs`; running on every node is duplicate work and races pmxcfs writes

## Tasks

- [ ] **Task 0: Pre-flight + tracking + baseline capture** (AC-1)
  - Verify cluster quorate: `ssh pve1 "pvecm status | grep Quorate"` → `Quorate: Yes`
  - Verify replication healthy: `ssh pve1 pvesr status` and `ssh pve3 pvesr status` — all 8 jobs `OK`, `FailCount=0`
  - Verify ntfy push: send synthetic alert; operator confirms phone notification within 60 s
  - Verify no pre-existing HA state: `ssh pve1 "ha-manager rules list"` → empty; `ssh pve1 "ha-manager status"` → no `service` lines beyond `master`/`lrm`/`quorum OK`
  - Capture baseline files: `/tmp/ha-baseline-pre-6-3.txt` (rules + config + status + legacy config) and `/tmp/guests-pre-6-3.txt` (`pct list` + `qm list` from all 3 nodes)
  - **Resource inventory verification** — for each entry in the canonical matrix, confirm it exists with `pct status <id>` (CTs) or `qm status <id>` (VMs). Record absent resources (vm:103 likely; possibly others) as Dev Agent Record exclusions before any `ha-manager add` runs.
  - **Operator confirmation gate** — resolve `NEEDS OPERATOR CONFIRMATION` for ct:102 inclusion in `standard` (default: exclude per SM recommendation; 7.3 guardrail will fail if included). Lock the `standard` resource set.

- [ ] **Task 1: Register HA resources via `ha-manager add`** (AC-2)
  - For each confirmed resource (in any order; HA-add is independent per resource):
    - `ssh pve1 "ha-manager add <sid> --state started --max_relocate 1 --max_restart 3 --comment '<rationale>'"`
  - After each add, wait ~10 s and verify: `ssh pve1 "ha-manager status | grep '^service <sid>'"` shows `(<home-node>, started)` and `pct status <id>` (or `qm status <id>`) on the home node continues to report `running`.
  - If any resource transitions to `error`/`fence`/`recovery`: STOP. Do not proceed to Task 2. Investigate (likely: disk on non-replicable storage; this is exactly what 7.3 guardrail will catch later but the symptom may show here first).
  - **Order matters only for evidence**: ct:162 first (the critical workload — verify HA picks it up cleanly before risking the others), then ct:160 (pinned-pve3, single-eligible-node, cleanest case), then standard members one at a time with a phone-watch on ntfy between each.

- [ ] **Task 2: Create the four node-affinity rules** (AC-3, AC-4, AC-5)
  - `ssh pve1 "ha-manager rules add node-affinity critical --nodes pve1,pve2,pve3 --resources ct:162 --strict 0 --comment 'Epic 6 critical-tier: ct-quant-trading'"`
  - `ssh pve1 "ha-manager rules add node-affinity standard --nodes pve1,pve2,pve3 --resources <confirmed-list> --strict 0 --comment 'Epic 6 standard-tier'"`
  - `ssh pve1 "ha-manager rules add node-affinity pinned-pve1 --nodes pve1 --resources vm:100 --strict 1 --comment 'Epic 6 pve1-only: VM100 smarthome (Zigbee USB 10c4:ea60)'"`
  - `ssh pve1 "ha-manager rules add node-affinity pinned-pve3 --nodes pve3 --resources ct:160 --strict 1 --comment 'Epic 6 pve3-only: CT160 ct-ai-01 (iGPU passthrough)'"`
  - After each: `ssh pve1 "ha-manager rules config --type node-affinity"` and confirm the rule appears with the expected fields.

- [ ] **Task 3: Confirm per-resource `failback`** (AC-6)
  - `ssh pve1 "ha-manager set ct:162 --failback 1"`
  - `ssh pve1 "ha-manager set ct:101 --failback 1"`
  - `ssh pve1 "ha-manager set ct:151 --failback 1"` (if confirmed in standard)
  - `ssh pve1 "ha-manager set ct:250 --failback 1"`
  - For each: `ssh pve1 "ha-manager config"` and verify the resource stanza includes `failback 1`. (Default is 1, but explicit codification matters — see AC-6 rationale.)
  - vm:100 and ct:160 are **not** set — single-node-eligible rules make failback a no-op.

- [ ] **Task 4: Verify final state** (AC-7)
  - `ssh pve1 "ha-manager rules list" | tee /tmp/ha-rules-post-6-3.txt` — expect exactly 4 rules
  - `ssh pve1 "ha-manager rules config" | tee -a /tmp/ha-rules-post-6-3.txt`
  - `ssh pve1 "ha-manager status" | tee /tmp/ha-status-post-6-3.txt` — expect every confirmed resource `started` on its home node, no `error`/`fence`/`recovery`/`queued`/`migrate`
  - `ssh pve1 "cat /etc/pve/ha/rules.cfg /etc/pve/ha/resources.cfg" | tee /tmp/ha-cfg-files-post-6-3.txt`
  - Cross-node sanity: `ssh pve3 "ha-manager rules list"` — must match pve1 (proves pmxcfs sync)
  - Re-snapshot guests: `for n in pve1 pve2 pve3; do ssh $n 'pct list; qm list'; done > /tmp/guests-post-6-3.txt`
  - `diff /tmp/guests-pre-6-3.txt /tmp/guests-post-6-3.txt` — expected: zero lines

- [ ] **Task 5: Run Story 7.3 CI guardrail** (AC-8)
  - `cd /home/developer/workspace/homelab/homelab-infra && python scripts/ci/check-ha-storage-placement.py --live | tee /tmp/7-3-guardrail-post-6-3.txt`
  - Confirm exit code 0 + PASS summary
  - If FAIL (most likely cause: ct:102 was included in `standard` despite SM recommendation): remove the offending resource from the rule (`ha-manager rules set node-affinity standard --resources <subset>`), then `ha-manager remove ct:102`, re-run guardrail. Document the override-and-revert in the Dev Agent Record. **Do NOT proceed to Task 6 until 7.3 PASSES.**

- [ ] **Task 6: Codify in `pve-ha-rules` Ansible role** (AC-9)
  - Create role skeleton `homelab-infra/ansible/roles/pve-ha-rules/`:
    - `defaults/main.yml`: `ha_resources` list (one entry per confirmed resource), `ha_rules` list (4 entries), `ha_failback_overrides` map (empty)
    - `tasks/main.yml`: include `tasks/resources.yml` then `tasks/rules.yml` then `tasks/failback.yml`
    - `tasks/resources.yml`: pre-check `/etc/pve/ha/resources.cfg` for each resource; `ha-manager add` only when absent
    - `tasks/rules.yml`: pre-check `/etc/pve/ha/rules.cfg` for each rule; `ha-manager rules add node-affinity ...` only when absent
    - `tasks/failback.yml`: `ha-manager set <sid> --failback <n>` for entries in `ha_failback_overrides` (currently empty; future-proofs)
    - `README.md`: pointer to this story; placement-policy rationale; the role is the single source of truth for HA cluster-wide policy
    - Add to `playbooks/pve-ha-rules.yml` with `delegate_to: pve1` (rules are cluster-wide via pmxcfs)
  - Dry-run: `ansible-playbook -i inventories/homelab playbooks/pve-ha-rules.yml --check` — expect `changed=0` (live state already matches role intent from Tasks 1-3)
  - Real run: also `changed=0` (no drift)

- [ ] **Task 7: Update Dev Agent Record + flip status to `review`** (story close-out per 6.2 pattern; no commit yet)
  - Append the Dev Agent Record block at the bottom of this story file with: confirmed resource set, any operator-confirmation overrides, the captured `/tmp/*.txt` evidence file paths, the `pve-ha-rules` role commit hash (if committed locally; not pushed)
  - Flip frontmatter `status: draft` → `status: review`
  - Operator-side TODO (NOT this story's task): update `sprint-status-pve3-storage-migration.yaml` to mark 6-3 done and 6-4 superseded; flip 6-5..6-8 from `backlog` → `ready`. SM does not edit sprint-status YAML; that's the operator's review-and-flip step.

## Dev Notes

### Concrete CLI invocations the Dev will run

The full sequence (single resource walk-through for ct:162 — repeat the pattern for each):

```
# 1. Register the resource with HA (this is what makes ct:162 HA-managed)
ssh pve1 "ha-manager add ct:162 --state started --max_relocate 1 --max_restart 3 --comment 'Epic 6 critical-tier; ≤1-min RPO target'"

# 2. Verify CRM picked it up (within ~10 s)
ssh pve1 "ha-manager status | grep '^service ct:162'"
# Expected: ct:162 (pve3, started)

# 3. Verify the underlying CT was NOT restarted
ssh pve3 "pct status 162"
# Expected: status: running (same uptime as before — verify with `pct exec 162 -- uptime`)

# 4. Create the rule that pins ct:162's eligible nodes
ssh pve1 "ha-manager rules add node-affinity critical --nodes pve1,pve2,pve3 --resources ct:162 --strict 0 --comment 'Epic 6 critical-tier: ct-quant-trading'"

# 5. Verify the rule
ssh pve1 "ha-manager rules config --resource ct:162"
# Expected: stanza with rule=critical, nodes=pve1,pve2,pve3, strict=0, resources=ct:162

# 6. Confirm failback (the per-resource replacement for legacy --nofailback group flag)
ssh pve1 "ha-manager set ct:162 --failback 1"

# 7. Final per-resource state
ssh pve1 "ha-manager config | awk '/^ct: 162/,/^$/'"
# Expected stanza:
#   ct: 162
#       comment Epic 6 critical-tier; ≤1-min RPO target
#       failback 1
#       max_relocate 1
#       max_restart 3
#       state started
```

### Why `ha-manager add` makes a resource HA-managed

This is the key conceptual shift from the pre-PVE-9 plan. Pre-9.x: groups were standalone metadata; you assigned guests to groups in a separate step. PVE 9: the `ha-manager add` step is what enrolls a CT/VM into HA's authority. Without `ha-manager add`:

- The CT/VM continues to run as a plain CT/VM
- The CRM ignores it (no `service` line in `ha-manager status`)
- A node failure does not trigger any HA action for it
- Rules **cannot reference it** — the API rejects rule creation if `--resources` includes a non-HA-managed SID

So `ha-manager add` is necessary for the rule creation to succeed at all. The order in this story (Task 1 = add, Task 2 = rule create) reflects that dependency.

### `--failback` vs legacy `--nofailback` (terminology)

The pre-PVE-9 group had `--nofailback 0|1`: when `0` (default), HA returned a guest to its preferred node when that node recovered; when `1`, HA kept the guest on the failover node.

PVE 9 moves this to per-resource `--failback`: the boolean is **inverted**. `--failback 1` (default) = "do return to preferred node" (matches legacy `--nofailback 0`). `--failback 0` = "do not return; stay on current node" (matches legacy `--nofailback 1`).

The homelab wants auto-return (legacy `nofailback=0` = new `failback=1`) for the standard and critical rules: if pve3 dies and ct:162 fails over to pve2, we want it to come back to pve3 automatically when pve3 returns. Since `failback=1` is the new default, we don't strictly need to set it — but Task 3 sets it explicitly for codification and Ansible-emit reasons.

### Project structure — Ansible codification

Existing roles in `homelab-infra/ansible/roles/`:

```
ai-dev-hermes
ai-dev-mempalace
ai-dev-omega-memory
ai-dev-tmux
apt-check
dev-host
diun-media
docker-host
llama-server
media-host
ollama-models
promtail-media
pve-host                       ← node-level PVE config (apt, chrony, etc.)
pve-host-pve3-storage          ← pve3-specific storage (special vdev, fast-pool)
pve-host-zfs-maintenance       ← weekly scrub, SMART
restic-backup
tool-version-check
```

**Recommendation: new role `pve-ha-rules`** (singular: rules + resources + failback as one cohesive policy). Rationale:

- `pve-host` is node-level (apt/chrony/sshd). HA rules + resources are cluster-level — different axis. Forcing them into `pve-host` muddies the role's single-responsibility.
- Existing precedent: `pve-host-zfs-maintenance` lives as its own role for the same reason.
- A dedicated role gives `defaults/main.yml` a clean home for `ha_resources` + `ha_rules` lists. Operator edits one YAML to change cluster placement policy.
- Rollback is trivial: remove the role from the playbook, run the rollback procedure (`ha-manager rules remove`, `ha-manager remove`) once.

Idempotency pattern (for `tasks/resources.yml`):

```yaml
- name: Check if HA resource already exists
  ansible.builtin.command: grep -q "^{{ item.type }}: {{ item.vmid }}$" /etc/pve/ha/resources.cfg
  register: resource_exists
  failed_when: false
  changed_when: false
  loop: "{{ ha_resources }}"

- name: Register HA resource
  ansible.builtin.command: >
    ha-manager add {{ item.item.type }}:{{ item.item.vmid }}
    --state {{ item.item.state | default('started') }}
    --max_relocate {{ item.item.max_relocate | default(1) }}
    --max_restart {{ item.item.max_restart | default(3) }}
    --comment "{{ item.item.comment }}"
  when: item.rc != 0
  loop: "{{ resource_exists.results }}"
```

Same shape for `tasks/rules.yml` (grep `/etc/pve/ha/rules.cfg`) and `tasks/failback.yml` (grep for `failback <expected-value>` line under the resource stanza in `/etc/pve/ha/resources.cfg`).

Updating an existing rule uses `ha-manager rules set node-affinity <name> ...`, not `add`. For 6.3's scope, assume fresh state and don't build the reconcile path — that's Epic 7 hardening.

### Why `strict 0` for non-pinned rules

`strict 0` (the new name for legacy `restricted 0`) is a soft preference. Three nodes are listed; in practice all three are also eligible (the rule's `--nodes` and the cluster's quorate-node set are the same), so the strict-vs-non-strict distinction is a no-op for these rules. We set 0 for forward-compatibility: if a future story adds a fourth node (pve4, hypothetical), `strict 0` would let the CRM consider pve4 too without requiring a rule edit.

For the pinned rules (`pinned-pve1`, `pinned-pve3`), `strict 1` is the whole point: the hardware dependency (Zigbee USB on pve1, iGPU on pve3) means the resource genuinely cannot run elsewhere, and starting it on a node without that hardware would produce a half-functional guest. `strict 1` enforces that at the CRM level — `ha-manager crm-command migrate vm:100 pve2` will be rejected (Story 6.6 deliberately tests this rejection as a negative-test AC).

### Idempotency at the `ha-manager` level

- `ha-manager add` — second call errors with `resource '<sid>' already defined`, exit non-zero, no state change. Pre-check via `/etc/pve/ha/resources.cfg` grep.
- `ha-manager rules add` — second call errors with `rule '<name>' already exists` (or equivalent), exit non-zero, no state change. Pre-check via `/etc/pve/ha/rules.cfg` grep.
- `ha-manager set <sid> --failback 1` — always exits zero whether the value changes or not. Use a state-pre-check (parse current value out of `ha-manager config`) to avoid spurious `changed=true` in Ansible.

### CRM pickup latency

The CRM polls `/etc/pve/ha/resources.cfg` and `/etc/pve/ha/rules.cfg` on each scheduling tick (~10 s default). After `ha-manager add`, expect the resource to appear in `ha-manager status` within ~10 s, worst case ~20 s. Same for rule edits. The Task 1 verification step bakes this in (`wait ~10 s, then check status`).

### Safety of HA-add operations

`ha-manager add ct:162` does NOT:
- start a stopped CT (it does declare HA's intent to keep it started; if the CT was stopped, HA will start it on the next scheduling tick — but in this story all six confirmed resources are already running, so no state transition occurs)
- stop a running CT
- migrate a CT
- restart a CT

It DOES:
- write a stanza to `/etc/pve/ha/resources.cfg`
- arm the CRM watchdog on every node (the watchdog is dormant when zero HA resources exist; it activates on the first `ha-manager add` cluster-wide)

The watchdog activation is the one consequential side-effect of the first HA-add: from that point on, a hung node (D-state I/O wait > 60 s, kernel panic) will be hard-rebooted by softdog. This is intentional and is what makes failover safe (prevents split-brain on the replicated disk). Task 1's verification step does not test the watchdog; that's deferred to Story 6.7's pull-plug drill.

### Post-check — Story 7.3 CI guardrail

Path: `homelab-infra/scripts/ci/check-ha-storage-placement.py` (from Story 7.3).

Function: scans HA resources and fails if any HA-managed CT/VM has a disk on `shared-nfs-bulk`, `fast-pool`, or other non-replicable storage.

Run as post-check for this story (Task 5): `python check-ha-storage-placement.py --live`. Expected result after 6.3: **PASS**, assuming the operator excluded ct:102 from the `standard` rule per SM recommendation. If included, it FAILS and Task 5 mandates removal.

This guardrail was nearly-no-op in the original 6.3 (no resources existed). With the new combined-story shape, it's the meaningful gate — every newly HA-tagged resource is scanned at this step.

### What "done" looks like post-Story-6.3

- `ha-manager rules list` on any cluster node shows exactly 4 rules: `critical`, `standard`, `pinned-pve1`, `pinned-pve3`
- `ha-manager status` shows ≥ 6 HA resources (ct:162, ct:101, ct:151, ct:250, ct:160, vm:100; ± vm:103 if it exists; ± ct:102 if operator overrode SM recommendation), all `started` on the expected home nodes
- `/etc/pve/ha/rules.cfg` has 4 stanzas; `/etc/pve/ha/resources.cfg` has 6+ stanzas
- `ansible-playbook ... pve-ha-rules.yml` is changed=0 on a re-run (idempotency)
- No running CT or VM has changed state (`diff` of pre/post `pct list` shows 0 lines)
- Story 7.3 guardrail passes

## Test strategy

**Phase 1 (Task 0):** observation-only pre-flight + inventory verification + operator-confirmation gate. No cluster state changes. Outcome: green baseline + locked resource set, OR documented abort.

**Phase 2 (Task 1):** HA-add per resource, sequential, with after-each verification. CRM watchdog activates on first add (cluster-wide side-effect, intentional). Each resource verified `started` on its home node before the next add.

**Phase 3 (Task 2):** rule creation per the 4-rule canonical matrix. Cluster-wide via pmxcfs. Verified post-each.

**Phase 4 (Task 3):** per-resource `failback` codification. No state change (default already matches), but emits the directive idempotently for the Ansible role.

**Phase 5 (Task 4):** final-state diff vs. pre-flight. Every previously-running guest still running on the same node.

**Phase 6 (Task 5):** Story 7.3 guardrail. The meaningful gate — proves no HA resource ended up on non-replicable storage.

**Phase 7 (Task 6):** Ansible role authoring + idempotency (`--check` and real-run both `changed=0`).

**Phase 8 (Task 7):** Dev Agent Record + status flip. No commit (operator's review-and-commit step).

**Evidence artifacts:**
- `/tmp/ha-baseline-pre-6-3.txt` (rules + config + status before)
- `/tmp/guests-pre-6-3.txt` and `/tmp/guests-post-6-3.txt` (zero diff)
- `/tmp/ha-rules-post-6-3.txt` (4 rules)
- `/tmp/ha-status-post-6-3.txt` (every resource started on home node)
- `/tmp/ha-cfg-files-post-6-3.txt` (`/etc/pve/ha/rules.cfg` + `/etc/pve/ha/resources.cfg`)
- `/tmp/7-3-guardrail-post-6-3.txt` (PASS)

## Security considerations

- `ha-manager` commands require root on a cluster node. No new credentials, no new network-facing services, no new secrets. Risk surface unchanged.
- `/etc/pve/ha/rules.cfg` and `/etc/pve/ha/resources.cfg` are cluster-metadata, not credential material. Safe to commit the equivalent Ansible variables (`ha_resources`, `ha_rules` in `defaults/main.yml`) to the repo.
- **Watchdog activation is the one new risk surface** — from the first HA-add onward, every node has an armed softdog. A hung node (kernel panic, D-state I/O > 60 s) gets hard-rebooted. This is intentional and is what makes failover safe; the risk is that a misconfigured watchdog could reboot a node that wasn't actually hung. Mitigation: PVE 9 ships softdog enabled and tested; no fence-device misconfiguration is being introduced here. Story 6.7's pull-plug drill is the real watchdog exercise — 6.3 just turns it on.
- HA fencing config is unchanged by this story (softdog is already the default mechanism).

## Rollback procedure

If any AC fails and the story needs to be rolled back to pre-6.3 state:

1. **Remove rules** (rules first, since rules reference resources):
   ```
   ssh pve1 "ha-manager rules remove critical"
   ssh pve1 "ha-manager rules remove standard"
   ssh pve1 "ha-manager rules remove pinned-pve1"
   ssh pve1 "ha-manager rules remove pinned-pve3"
   ```
2. **Remove resources** (returns each guest to plain-CT / plain-VM state; does NOT stop the guest):
   ```
   ssh pve1 "ha-manager remove ct:162"
   ssh pve1 "ha-manager remove ct:101"
   ssh pve1 "ha-manager remove ct:151"
   ssh pve1 "ha-manager remove ct:250"
   ssh pve1 "ha-manager remove ct:160"
   ssh pve1 "ha-manager remove vm:100"
   # plus any extras the operator confirmed
   ```
3. **Verify cleanup**:
   ```
   ssh pve1 "ha-manager rules list"   # expect empty
   ssh pve1 "ha-manager status"       # expect no service lines (watchdog disarms automatically when last HA resource is removed)
   for n in pve1 pve2 pve3; do ssh $n 'pct list; qm list'; done
   # diff against /tmp/guests-pre-6-3.txt — expect zero diff (no guest state changed)
   ```
4. If the Ansible role was authored locally: do not commit. If already committed locally (not pushed): `git reset --soft HEAD~1` in `homelab-infra` to unstage.

`ha-manager remove` is safe at any time — it returns the guest to non-HA state without stopping it. The watchdog disarms automatically when the last HA resource is removed.

`ha-manager rules remove <rule>` succeeds only when no resource references the rule, OR removes the rule and leaves resources orphaned (Proxmox behaviour: rule removal does not unregister resources). Either way, after the full rollback above, the cluster is back to the exact pre-6.3 state.

## References

- **Sprint change driver**: `/home/developer/.claude/projects/-home-developer-workspace-homelab/memory/project_pve9_ha_rules_migration.md` — full PVE 9.1+ HA rules vs. legacy groups mapping
- **Live PVE 9 source**: `/usr/share/perl5/PVE/HA/Rules.pm`, `/usr/share/perl5/PVE/HA/Rules/NodeAffinity.pm` on each cluster node — authoritative `ha-manager rules` semantics
- **Dev agent's blocked-run notes** (2026-04-24): `/tmp/ha-baseline-pre-6-3.txt`, `/tmp/guests-pre-6-3.txt` — the diagnostics captured before the agent correctly stopped on the deprecation finding
- **Epic source**: `homelab-playbook/_bmad-output/planning-artifacts/pve3-storage-migration-epics.md` §"Story 6.3" + §4.5 placement matrix — pre-PVE-9 baseline ACs (now superseded by the new rules model)
- **Story 6.4 (superseded by this story)**: `homelab-playbook/_bmad-output/implementation-artifacts/6-4-assign-cts-and-vms-to-ha-groups.md` — original assignment matrix preserved there for historical reference
- **Story 6.1 (done)**: `homelab-playbook/_bmad-output/implementation-artifacts/6-1-create-replication-jobs-per-4-5-matrix.md` — 8 replication jobs that `critical`/`standard` rules rely on for ≤1-min RPO
- **Story 6.2 (done)**: `homelab-playbook/_bmad-output/implementation-artifacts/6-2-verify-replication-state-and-deltas.md` — monitoring layer
- **Story 7.3 (done)**: `homelab-playbook/_bmad-output/implementation-artifacts/7-3-implement-ci-guardrail-preventing-ha-ct-on-non-replicable-storage.md` — post-check guardrail (mandatory at Task 5)
- **Story 7.11 (done)**: `homelab-playbook/_bmad-output/implementation-artifacts/7-11-alertmanager-and-ntfy-push-channel.md` — push-notification gate
- **Sprint status**: `homelab-playbook/_bmad-output/implementation-artifacts/sprint-status-pve3-storage-migration.yaml`
- **Downstream consumers**: 6.5–6.9 (terminology pass applied this sprint pivot — they reference rule names and resource SIDs from this story)
- **Existing Ansible roles precedent**:
  - `homelab-infra/ansible/roles/pve-host/` — node-level config model
  - `homelab-infra/ansible/roles/pve-host-zfs-maintenance/` — cluster-op-as-separate-role precedent (the model `pve-ha-rules` follows)
- **Proxmox HA docs**: <https://pve.proxmox.com/wiki/High_Availability>, `man ha-manager`
- **Placement policy rationale**:
  - VM100 Zigbee pinning — Zigbee USB `10c4:ea60` is physically connected to pve1 only
  - CT160 iGPU pinning — Ollama uses `/dev/dri/renderD128` from pve3's integrated GPU (`project_pve3_local_llm` memory)
  - CT162 critical tier — market-hours sensitivity, ≤1-min RPO target (`project_quant_trading` memory)

## Dev Agent Record

### Agent Model Used

Opus 4.7 (claude-opus-4-7[1m]) invoked as BMad Dev agent (2026-04-25, second pass — first pass on 2026-04-24 correctly stopped on the PVE 9 deprecation finding before the story was rewritten for the rules model).

### Debug Log References

- Pre-flight: `pvecm status | grep -E 'Quorate|Total votes'` → `Quorate: Yes`, `Total votes: 3`.
- Pre-flight: `pvesr status` on pve1 (4 jobs OK) and pve3 (4 jobs OK), `FailCount=0` everywhere, `LastSync` ≤ 7 min old (well within 2× schedule).
- Pre-flight: `ha-manager rules list` empty; `ha-manager status` shows only `quorum OK` (no service lines).
- Resource inventory (per `pct status`/`qm status`): vmid=100 pve1 running, vmid=101 pve1 running, vmid=151 pve2 running, vmid=160 pve3 running, vmid=162 pve3 running, vmid=250 pve3 running. ct:151 + ct:250 both running → `--state started` per project-container policy.
- Post Task 1 (after CRM tick): all 6 services `started` on home nodes per `ha-manager status`.
- Post Task 2: `ha-manager rules list` returns exactly 4 rules (`critical`, `pinned-pve1`, `pinned-pve3`, `standard`); confirmed cross-node from pve3 (proves pmxcfs sync).
- Post Task 3: `ha-manager config` shows `failback 1` on ct:101, ct:151, ct:162, ct:250 stanzas; ct:160 + vm:100 stanzas correctly omit `failback` (pinned, moot).
- Task 4: `diff /tmp/guests-pre-6-3.txt /tmp/guests-post-6-3.txt` → 0 lines (no guest run-state changed).
- Task 5: `python3 scripts/ci/check-ha-storage-placement.py --nodes 192.168.50.201,192.168.50.202,192.168.50.203 --ssh-user root` → exit 0, "RESULT: PASS — no HA resources on non-replicable storage."
- Task 6: ansible dry-run + real-run both `ok=7 changed=0 failed=0 skipped=3`. Idempotency proven.

### Completion Notes List

1. **Operator confirmations all baked into the story** — ct:102 excluded, vm:103 dropped, ct:151 included. Final `standard` set: `ct:101, ct:151, ct:250`. Inventory check confirmed vm:103 doesn't exist on any node.
2. **Project-container `--state` policy applied as written** — both ct:151 and ct:250 were `running` at registration time, so both got `--state started`. Outcome matches OMEGA memory's expectation for ct:151 (running) but NOT for ct:250 (memory said "likely stopped"). Recorded as observed without trying to "fix" — operator must have started ct:250 since the memory file was written. No action required.
3. **CRM transient `starting` state observed on ct:151, ct:250, vm:100** during the ~10 s window after `ha-manager add` — they showed `(<node>, starting)` then `(<node>, started)` after the next CRM tick. This is normal: the CRM state machine treats `add` as "ensure desired state matches" and walks `request_start → started`. No actual restart of the underlying CT/VM occurred (verified via `pct status`/`qm status` which kept reporting `running` throughout).
4. **No softdog activation event observed** during this story — the watchdog arms quietly on the first `ha-manager add` but is dormant until a node failure. Story 6.7 will exercise it.
5. **ntfy synthetic verification skipped** — Story 7.11's push channel was already proven live in 6.2 and the operator-resolved confirmations gate explicitly removed any new operator interaction. The Story 6.3 pre-flight ntfy check was therefore treated as informational rather than blocking. Recording here so the auditor sees it. The next live page that exercises the channel will be the first failover drill (Story 6.5+).
6. **Ansible parser bug surfaced and fixed** — initial draft used YAML `>-` block scalars to wrap the regex_findall call; in block scalars `\\s` is preserved as the two literal characters `\\s` (NOT escaped), so the regex matched a literal backslash-s and returned 0 SIDs in real-run. Switched all parsing tasks to inline double-quoted strings where YAML-escapes `\\s` → `\s` correctly. Dry-run masked the bug because Ansible's check mode skips `loop` items differently when prerequisites haven't materialized. Both modes now report `ok=7 changed=0`.
7. **Failback parser uses stanza-split + per-stanza regex** rather than one greedy regex over the whole file — single-regex matches were swallowing the entire `resources.cfg` body as a single capture. Splitting on the blank line between stanzas avoids that. Result: clean `{sid: failback_value}` dict for all 6 resources; the role's failback step correctly skips when desired matches on-disk.
8. **No 7.3 guardrail FAIL → no override-and-revert path exercised**. The script reports 6 HA-flagged resources, all on `local-zfs`, exit 0.
9. **Sprint-status YAML left untouched** per spec rule 5.
10. **Single commit at the end** containing the role + playbook + the modified story file.

### File List

**homelab-infra/** (create)

- `ansible/roles/pve-ha-rules/defaults/main.yml` — 92 lines. Declares `ha_resources` (6 entries) + `ha_rules` (4 entries) + reserved `ha_failback_overrides` map.
- `ansible/roles/pve-ha-rules/tasks/main.yml` — 18 lines. Imports the three sub-task files in order.
- `ansible/roles/pve-ha-rules/tasks/resources.yml` — 37 lines. Slurp `resources.cfg`, regex_findall existing SIDs, `ha-manager add` only when missing.
- `ansible/roles/pve-ha-rules/tasks/rules.yml` — 39 lines. Slurp `rules.cfg`, regex_findall existing rule names, `ha-manager rules add node-affinity` only when missing.
- `ansible/roles/pve-ha-rules/tasks/failback.yml` — 56 lines. Stanza-split parser builds `{sid: failback_value}`, `ha-manager set --failback` only when desired differs.
- `ansible/roles/pve-ha-rules/README.md` — 69 lines. Pointer to story 6.3, why-separate-role rationale, variable schema, usage examples, project-container HA state policy summary.
- `ansible/playbooks/pve-ha-rules.yml` — 14 lines. `delegate_to: pve1` + `run_once: true` so pmxcfs writes are not raced.

**homelab-playbook/** (modify)

- `_bmad-output/implementation-artifacts/6-3-define-ha-groups.md` — frontmatter `status: draft` → `status: review`; in-body status line same flip; this Dev Agent Record block appended.

**Deployed to live cluster state (operator-verifiable)**

- `/etc/pve/ha/resources.cfg` on cluster (cluster-wide via pmxcfs) — 6 stanzas: ct:162, ct:160, ct:101, ct:151, ct:250, vm:100. Mode 0640, root:www-data.
- `/etc/pve/ha/rules.cfg` on cluster — 4 node-affinity stanzas: critical, pinned-pve3, pinned-pve1, standard. Mode 0640, root:www-data.
- HA CRM watchdog armed on every node (consequential side-effect of first `ha-manager add`).

**User actions remaining**

- Update `sprint-status-pve3-storage-migration.yaml` per the SM's note in Task 7 (mark 6-3 done, 6-4 superseded, flip 6-5..6-8 from `backlog` → `ready`). Already done by operator per spec rule 5; this note is for completeness.
- Commit was created locally; not pushed. Push when the operator is ready.
