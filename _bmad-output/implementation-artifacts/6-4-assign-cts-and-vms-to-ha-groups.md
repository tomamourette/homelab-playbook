---
status: superseded
epic: 6
story: 6.4
title: Assign CTs and VMs to HA groups
created: 2026-04-24
superseded_at: 2026-04-25
superseded_by: 6-3-define-ha-rules-and-assign-resources
author: BMad SM
---

# Story 6.4: Assign CTs and VMs to HA groups

Status: superseded

## Superseded

This story is **superseded by the rewritten Story 6.3** (`6-3-define-ha-groups.md`, retitled "Define HA node-affinity rules and assign resources").

**Reason:** Proxmox VE 9.1.1 (live on this cluster, kernel 6.17.2-1-pve, verified 2026-04-24) deprecated the legacy HA-groups abstraction in favour of node-affinity rules. The new schema **requires `--resources` at rule creation** — there is no longer a "create empty group, fill it later" step. That makes the original 6.3 / 6.4 split (groups first, then assignments) unexpressible: rule existence and resource membership are coupled by design in the rules model.

The rewritten Story 6.3 absorbs this story's scope into a single sequence:
1. Register each resource with `ha-manager add` (the PVE 9 step that makes a CT/VM HA-managed)
2. Create the four node-affinity rules with `--resources` populated at creation
3. Set per-resource `failback` (the PVE 9 replacement for the legacy group-level `nofailback` flag)

**Date superseded:** 2026-04-25
**Superseded by:** `homelab-playbook/_bmad-output/implementation-artifacts/6-3-define-ha-groups.md` (file path unchanged for git-history reasons; title and content rewritten)
**Memory file with full PVE 9 mapping:** `/home/developer/.claude/projects/-home-developer-workspace-homelab/memory/project_pve9_ha_rules_migration.md`

The §4.5 placement matrix preserved below remains the authoritative resource→rule map (the rule names `critical` / `standard` / `pinned-pve1` / `pinned-pve3` carry forward unchanged into the rewritten 6.3). Only the CLI commands and the lifecycle coupling changed.

## Original AC archive (for historical reference)

The original ACs from this story are preserved in git history at the prior commit. Key invariants that carry forward into the rewritten 6.3:

- **CT162 → `critical`** (replicated, ≤1-min RPO target)
- **VM100 → `pinned-pve1`** (Zigbee USB `10c4:ea60` on pve1 only)
- **CT160 → `pinned-pve3`** (iGPU `/dev/dri/renderD128` on pve3 only)
- **CT101 → `standard`** (ct-docker-01)
- **CT250 → `standard`** (ct-dev-homelab)
- **Disposable / non-HA**: ct:104, ct:152, ct:153 (none currently exist in cluster — verified 2026-04-25); ct:102 (ct-media-01, mounts non-replicable `shared-nfs-bulk`); ct:151 (ct-sparkle-cps, LOW-priority, PBS-protected — operator-confirmation gate in rewritten 6.3 to decide inclusion in `standard`)
- **Story 7.3 CI guardrail** — mandatory post-task check; carries forward as AC-8 in rewritten 6.3
- **CRM watchdog activation** — armed automatically on first `ha-manager add`; carries forward as a dev-note in rewritten 6.3

For the full original AC text and the per-task command sequences, see the git log entry for this file prior to the 2026-04-25 supersession commit.
