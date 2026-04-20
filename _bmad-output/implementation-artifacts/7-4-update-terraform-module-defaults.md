---
status: done
epic: 7
story: 7.4
title: Update Terraform module defaults
---

# Story 7.4: Update Terraform module defaults

## User Story

As an operator, I want newly-created CTs to default to `local-zfs`, so that no one accidentally creates a new workload on a storage that doesn't exist (or on a pre-migration `local-lvm` that will be torn down).

## Acceptance Criteria

**Given** `homelab-infra/terraform/modules/ct-debian/variables.tf` currently defaults `storage_id`
**When** I update the default value from `local-lvm` to `local-zfs`
**And** I update `terraform.tfvars.example` to match
**Then** a new CT created via the module with no explicit `storage_id` lands on `local-zfs`
**And** existing CTs are unaffected (their state is already set)

## Tasks

- [x] Change default in `homelab-infra/terraform/modules/ct-debian/variables.tf` line 45 from `"local-lvm"` to `"local-zfs"`
- [x] Enrich the `description` field with guardrail guidance (don't pick `fast-zfs`/`shared-nfs-bulk` for HA resources)
- [x] Update `homelab-infra/terraform/envs/homelab/terraform.tfvars.example` comment from `# vm_storage = "local-lvm"` to `# vm_storage = "local-zfs"` with a note that `local-lvm` was the pre-Epic-5 value

## Deliberately NOT done in this story

**Hardcoded overrides in `envs/homelab/main.tf`** — there are 9 explicit `storage_id = "local-lvm"` lines (for CT101, CT102, CT104, CT150, CT151, CT152, CT153, VM103, and the template 999). These are intentionally left alone because the underlying CTs/VMs STILL LIVE on `local-lvm` today. Changing them now would cause `terraform apply` to see drift and attempt to migrate storage — an operation that belongs in Epic 5.

Those explicit overrides get flipped to `local-zfs` in:
- Story 5.6 (pve1-hosted resources, post-pve1-reinstall): CT101, CT102, CT104, CT150, VM103, 999 template
- Story 5.11 (pve2-hosted resources, post-pve2-reinstall): CT151, CT152, CT153

Story 7.4 only affects the **default** applied to NEW CTs that don't specify `storage_id` explicitly. This is purely forward-looking — existing CTs are untouched until Epic 5 migrates their storage.

## Dev Notes

- Single-value change; zero risk of breaking existing state (defaults are only used when no override is provided).
- Description field now documents the three-tier storage policy (`local-zfs` for HA-safe, `fast-zfs` for ephemeral, avoid `shared-nfs-bulk` for HA) so future devs don't re-discover the rule.
- The CI guardrail in Story 7.3 will mechanically catch violations of the policy even if someone ignores the description.

## Implementation Report

```diff
-  default     = "local-lvm"
+  default     = "local-zfs"
```

with expanded description. `terraform.tfvars.example` comment updated in line with the new default. No other changes.
