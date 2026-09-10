---
type: story
epic: FE1
id: FE1-S02
title: "Narrowly-targeted terraform plan and apply for CT 167"
size: S
priority: MUST
owner: dev
blocking: false
fr_refs: [FR-SUB-004]
nfr_refs: [NFR-IAC-002]
adr_refs: []
risk_refs: []
gate_refs: [j]
status: done
date: 2026-09-09
---

# FE1-S02: Narrowly-targeted terraform plan and apply for CT 167

> **~~BLOCKED — do not start.~~ BLOCKER LIFTED 2026-09-09 — banner retained for the record.**
> Both §5.4 prerequisites now exist and were verified on the facts, not waived:
> `vault_forge_github_client_id` (20 chars) and `vault_forge_github_client_secret` (40) satisfy
> FE0-S01, and `vault_cloudflare_api_token` (53) + `vault_cloudflare_zone_id` satisfy FE0-S02 —
> all four present in `ansible/inventories/homelab/group_vars/vault.yml`. Lengths are of the
> **unquoted** values; no secret value was read or printed. See FE2-S06's banner for the full
> verification note. The original banner text follows unchanged:
>
> **BLOCKED — do not start.** Per §5.4 of the approved proposal, nothing in FE1–FE4 begins
> before **both** operator prerequisites exist:
> 1. **GitHub OAuth App** → `CODER_EXTERNAL_AUTH_0_ID/TYPE/CLIENT_ID/CLIENT_SECRET` (FE0-S01).
>    The only non-optional external credential in the whole PoC. Without it the workspace build
>    **fails** — `data "coder_external_auth" "github"` (`coder/templates/forge/main.tf:25-27`) has
>    no `optional = true` — and even if it did not, `forge-sync.sh` sources its token from
>    `coder external-auth access-token github` and **silently skips its entire clone block**, so
>    agentic-ai never lands and gates (b)–(e) are untestable.
> 2. **Cloudflare API token**, DNS-edit scope, zone `bi-services.be` (FE0-S02). Required for
>    **any** browser-trusted certificate — the homelab has no inbound `:80`/`:443`, so HTTP-01 is
>    impossible, not merely inconvenient. Wildcard scope is optional; the token is not.
>    **REVERSED 2026-09-09 — a wildcard IS required.** The token sentence still holds and the
>    token needs no re-scoping; only the "wildcard scope is optional" clause is dead. See the
>    amendment at the top of [ADR-005](../adrs/ADR-005-dns-01-wildcard-over-public-ingress.md).

## User Story

As **tomamourette**, I want **a narrowly `-target`ed `terraform plan` for `module.ct_forge_01` and its three generated/DNS resources, reviewed and applied**, so that **CT 167 is created without a bare plan dragging in unrelated pre-existing DNS drift, and I can see exactly what will change before committing to it**.

## Background and Context

This story is FE1-S01's necessary follow-on, deliberately kept separate so the sizing decision (R4) and the module block itself (FE1-S01) can be reviewed on their own before any state-changing Terraform command runs. Evidence **E7** and the runbook's **Pitfall §1** are explicit: "a bare `terraform plan` against this state often includes pre-existing config drift (e.g. `gemma.bi-services.be → 192.168.50.194` from `ai_service_ip_map`) that has nothing to do with the new container" — an untargeted plan for `ct-forge-01` would show unrelated changes and make the actual diff for CT 167 hard to verify at a glance. NFR-IAC-002 restates this as a standing rule: **every** `terraform plan` against the homelab root is narrowly `-target`ed, not just this one.

Gate (j) (§5.3) — "`terraform plan` on the homelab root is clean apart from the intended CT; the `ct_sparkle_vlabel` phantom has not been recreated" — is exercised at acceptance time in FE4-S02, but this story is where the discipline that makes that gate passable is first established.

## Acceptance Criteria

**AC1 — Plan targets exactly the expected resources.**
- **Given** FE1-S01's `module "ct_forge_01"` block and `outputs.tf` edits are in place,
- **When** the dev runs `terraform plan -target=module.ct_forge_01 -target=local_file.prometheus_targets -target=local_file.pihole_custom_list -target='cloudflare_record.homelab["ct-forge-01"]' -out=tfplan-forge-01` from `homelab-infra/terraform/envs/homelab`,
- **Then** the plan succeeds and `terraform show -no-color tfplan-forge-01 | grep -E "(will be|^Plan:)"` shows exactly the module's resources being created plus the two `local_file` regenerations (2 replaces) — matching the runbook's expected shape of "4 creates + 2 replaces."

**AC2 — No unrelated drift in the plan.**
- **Given** AC1's plan output,
- **When** the dev inspects the full plan for any resource address not related to `ct_forge_01`, its DNS record, or the two generated files,
- **Then** none appears — specifically, no `ct_sparkle_vlabel` resource and no unrelated `ai_service_ip_map` drift.

**AC3 — Pre-apply verification of Debian 13 template caching on pve3.**
- **Given** the runbook's Pitfall §6 (template caching is per-node),
- **When** the dev runs `ssh root@pve3 "ls /var/lib/vz/template/cache/ | grep debian-13"` before applying,
- **Then** `debian-13-standard_13.1-2_amd64.tar.zst` is present — if absent, the dev runs `pveam download` first (per the runbook) rather than letting the apply fail mid-flight with a stale LXC ID allocated.

**AC4 — Apply succeeds and CT 167 is reachable.**
- **Given** AC1–AC3 have passed and the operator has reviewed the plan,
- **When** the dev runs `terraform apply tfplan-forge-01`,
- **Then** the apply completes with 0 errors, and `ssh root@pve3 "pct exec 167 -- ip -4 addr show eth0 | grep inet"` shows `192.168.50.167`.

**AC5 — Config sanity check post-create.**
- **Given** AC4's apply,
- **When** the dev runs `ssh root@pve3 "pct config 167 | grep -E '^(nameserver|searchdomain|net0|features)'"`,
- **Then** `features` shows `nesting=1,keyctl=1`, and `nameserver`/`searchdomain`/`net0` are populated (the runbook notes the Proxmox API token does not always inject these correctly on create — this AC catches that before Ansible work in FE1-S04 depends on it).

## Implementation Notes

Reference runbook `homelab-playbook/wiki/runbooks/create-project-container.md` §3 (terraform init/plan/apply) and §4's opening verification commands (`pct config`, `ip addr show`), Pitfall §1 (untargeted plan drift) and Pitfall §6 (per-node template caching). NFR-IAC-002 is the standing rule this story instantiates.

```bash
cd homelab-infra/terraform/envs/homelab
terraform init -upgrade=false

# Pre-apply: confirm template cached on pve3
ssh root@pve3 "ls /var/lib/vz/template/cache/ | grep debian-13"
# If missing: ssh root@pve3 "pveam download local debian-13-standard_13.1-2_amd64.tar.zst"

terraform plan \
  -target=module.ct_forge_01 \
  -target=local_file.prometheus_targets \
  -target=local_file.pihole_custom_list \
  -target='cloudflare_record.homelab["ct-forge-01"]' \
  -out=tfplan-forge-01

terraform show -no-color tfplan-forge-01 | grep -E "(will be|^Plan:)"
# Expected: 4 creates + 2 replaces. Plan: 6 to add, 0 to change, 2 to destroy.

terraform apply tfplan-forge-01

# Post-apply verification
ssh root@pve3 "pct config 167 | grep -E '^(nameserver|searchdomain|net0|features)'"
ssh root@pve3 "pct exec 167 -- ip -4 addr show eth0 | grep inet"
```

## Test Plan

**Pre-state:** `module "ct_forge_01"` and its `outputs.tf` entries exist (FE1-S01 done); CT 167 does not yet exist on pve3.

**Action sequence:**
1. `terraform init` (idempotent if already initialized).
2. Verify Debian 13 template cached on pve3 (AC3).
3. Run the narrowly-targeted plan (AC1), inspect for drift (AC2).
4. Operator/dev reviews the plan output.
5. Apply (AC4).
6. Verify config and network reachability (AC5).

**Post-state checks:**
- `pct list` on pve3 shows VMID 167, `ct-forge-01`, running.
- `ip -4 addr show eth0` inside the CT returns `192.168.50.167`.
- `pct config 167` shows the expected `features` string.

**Rollback:** `terraform destroy -target=module.ct_forge_01 -target=local_file.prometheus_targets -target=local_file.pihole_custom_list -target='cloudflare_record.homelab["ct-forge-01"]'` — reverses the apply cleanly since nothing else depends on CT 167 yet at this point in the sequence (HA, Ansible, and the Coder host all come later).

## Dependencies

- **Blocked by:** FE1-S01 (module block must exist), FE0-S01, FE0-S02 (§5.4).
- **Blocks:** FE1-S03 (HA needs the CT to exist), FE1-S04 (Ansible needs the CT reachable), FE4-S02 gate (j).

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Debian 13 template not cached on pve3 (cached elsewhere), apply fails mid-flight leaving a stale LXC ID | Medium (runbook explicitly flags this as a known pitfall) | Medium — requires manual cleanup of the partially-allocated ID before retrying | AC3 checks the cache explicitly before apply, per Pitfall §6 |
| SSH key fingerprint mismatch between `terraform.tfvars` and the operator's workstation key, discovered only at FE1-S04/FE1-S08 verification | Medium (has hit 3 prior project CTs per the runbook) | Low — password prompt, not a failure of this story's ACs | Out of this story's scope; flagged here for awareness, handled at FE1-S04/verification steps per runbook §5/§8 |
| Bare plan re-introduced by habit (someone runs `terraform plan` without `-target` later) | Low | Medium — pulls in unrelated drift, obscures the real diff | NFR-IAC-002 is a standing rule, not a one-time fix; gate (j) in FE4-S02 re-checks this at acceptance time |

## Definition of Done

- [ ] AC1–AC5 all green and evidenced.
- [ ] `terraform apply` completed with 0 errors against the narrowly-targeted plan.
- [ ] CT 167 reachable at `192.168.50.167` with `features=nesting=1,keyctl=1` confirmed.
- [ ] Story status updated from `draft` to `done` in this file's frontmatter.
