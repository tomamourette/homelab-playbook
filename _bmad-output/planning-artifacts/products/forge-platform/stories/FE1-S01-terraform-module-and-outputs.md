---
type: story
epic: FE1
id: FE1-S01
title: "Terraform module block for CT 167 ct-forge-01 plus outputs.tf registration"
size: S
priority: MUST
owner: dev
blocking: false
fr_refs: [FR-SUB-001, FR-SUB-002, FR-SUB-003]
nfr_refs: [NFR-CAP-002]
adr_refs: [ADR-001]
risk_refs: [R4]
gate_refs: [j]
status: done
date: 2026-09-09
---

# FE1-S01: Terraform module block for CT 167 ct-forge-01 plus outputs.tf registration

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

> **ALSO BLOCKED ON AN UNRESOLVED SIZING DECISION (R4).** The workspace template's
> `coder_parameter` defaults are **12288 MB RAM** (`coder/templates/forge/main.tf:62`) and
> **20480 MB swap** (`main.tf:77`). These are `coder_parameter`, **not** `variable`, so a
> `--variables-file` **cannot** lower them; `min = 2048` and `mutable = true` mean an operator
> *can* choose smaller, but only by remembering to, every time. Swap has no answer inside an
> unprivileged LXC — you cannot create a swapfile, and the CT gets whatever `swap_mb` Terraform
> set, which `modules/ct-debian` defaults to **512 MB**
> (`homelab-infra/terraform/modules/ct-debian/variables.tf:30-33`). Two candidate resolutions,
> **neither chosen**: (a) four real `variable`s driving both the defaults and the validation
> maxima (FE3-S01) **plus** `swap_mb = 8192`; or (b) size CT 167 at **4C/12GB**. This is an
> operator capacity call against pve3 and **must be resolved before this story starts**.
> Approval of the proposal did not settle it.

## User Story

As **tomamourette**, I want **a `module "ct_forge_01"` Terraform block for CT 167 mirroring `ct_saply_ai`, plus its two `outputs.tf` registrations**, so that **`ct-forge-01` exists as declared infrastructure on the established pattern, with monitoring and DNS auto-derived rather than hand-edited, and with an explicit swap allocation that does not silently inherit the module's undersized 512 MB default**.

## Background and Context

This is the first story of FE1 (Substrate) and follows evidence **E7**: the established homelab CT pattern (`homelab-playbook/wiki/runbooks/create-project-container.md`) is the correct implementation vehicle, not a bespoke VM (E4 rejects `modules/vm-dev` — never applied, legacy telmate disk blocks, no default `ci_password`, no qemu-guest-agent so no IP ever returned, and its base template lives on the wrong node for a pve3 clone). CT 167, `ct-forge-01`, is sized 4C/8GB/50GB, Debian 13, `features=nesting=1,keyctl=1`, at `192.168.50.167`, per the frozen scope in the canon and §1 of the proposal.

**Two things must be true before this story can proceed**, beyond the standard FE1–FE4 blockers: FE0-S05 must have resolved the `ct_sparkle_vlabel` (VMID 166) phantom block, so this story's edit to `main.tf` does not land next to live uncommitted drift that a later apply could recreate; and the R4 sizing conflict (banner above) must be resolved by the operator, because this story's `swap_mb` value (FR-SUB-002) and CT memory size depend directly on which resolution — (a) template variables + `swap_mb = 8192`, or (b) a larger 4C/12GB CT — the operator chooses.

The runbook's template block (§1 of `create-project-container.md`) does **not** set `swap_mb` explicitly, relying on the module default of 512 MB. FR-SUB-002 requires this story to set it explicitly regardless of which R4 resolution the operator picks, because leaving it at the module default is the specific failure mode R4 describes.

## Acceptance Criteria

**AC1 — `module "ct_forge_01"` block matches the runbook pattern.**
- **Given** FE0-S05 has resolved the `ct_sparkle_vlabel` phantom and the operator has resolved R4,
- **When** the dev appends a `module "ct_forge_01"` block to `homelab-infra/terraform/envs/homelab/main.tf`, mirroring `module "ct_saply_ai"`'s shape and sourcing `../../modules/ct-debian`,
- **Then** the block sets: `name = "ct-forge-01"`, `vmid = 167`, `node = "pve3"`, `unprivileged = true`, `features = ["nesting=1", "keyctl=1"]`, `network_ip = "192.168.50.167/24"`, `storage_id = "local-zfs"`, `ostemplate` pointing at the cached Debian 13 template, and `cores`/`memory_mb`/`disk_gb` matching whichever R4 resolution the operator chose (4/8192/50 for resolution (a), or 4/12288/50 for resolution (b)).

**AC2 — `swap_mb` set explicitly (FR-SUB-002).**
- **Given** AC1's block,
- **When** the dev reviews the module arguments,
- **Then** `swap_mb` is present as an explicit argument (not omitted to inherit the module's 512 MB default) — `8192` under R4 resolution (a), or an operator-specified value under resolution (b) — and `grep -A20 'module "ct_forge_01"' main.tf | grep swap_mb` returns a match.

**AC3 — `outputs.tf` registrations (FR-SUB-003).**
- **Given** AC1's block exists,
- **When** the dev appends `ct_forge_01`'s entry to `locals.all_containers` (for Prometheus `file_sd_configs`) and `"ct-forge-01" = module.ct_forge_01.ip_address` to `locals.project_container_host_map` in `homelab-infra/terraform/envs/homelab/outputs.tf`,
- **Then** both appends are present and `terraform validate` (not yet `plan` — that is FE1-S02) succeeds against the edited files.

**AC4 — No wildcard entry introduced.**
- **Given** the canon's explicit prohibition,
- **When** the dev reviews the `outputs.tf` edit,
- **Then** no wildcard hostname (`*.forge.bi-services.be` or similar) appears in `fqdn_dns_records` or `project_container_host_map` — only the single `ct-forge-01` host entry.

**AC5 — `terraform fmt` and `terraform validate` clean.**
- **Given** AC1–AC4's edits,
- **When** the dev runs `terraform fmt -check` and `terraform validate` in `homelab-infra/terraform/envs/homelab`,
- **Then** both commands exit 0 with no diff and no validation errors.

## Implementation Notes

Reference the runbook `homelab-playbook/wiki/runbooks/create-project-container.md` §0 (pre-flight table) and §1–§2 (module + outputs steps) verbatim — this story is that runbook's steps 0–2 applied to `ct-forge-01`. Reference ADR-001 (lxc-over-vm-for-forge-poc) for why this is an LXC and not the rejected VM path. This story does **not** run `terraform plan` or `apply` — that is FE1-S02, deliberately separated so the R4-driven sizing choice is locked in and reviewed before any state-changing command runs.

```hcl
# homelab-infra/terraform/envs/homelab/main.tf — append after the most recent project container
# ct-forge-01 project container on pve3 — Forge developer platform PoC (self-hosted).
module "ct_forge_01" {
  source = "../../modules/ct-debian"

  name         = "ct-forge-01"
  vmid         = 167
  node         = "pve3"
  cores        = 4
  memory_mb    = 8192          # or 12288 per R4 resolution (b) — operator decision, see banner
  disk_gb      = 50
  storage_id   = "local-zfs"
  ostemplate   = "local:vztmpl/debian-13-standard_13.1-2_amd64.tar.zst"
  unprivileged = true
  features     = ["nesting=1", "keyctl=1"]
  swap_mb      = 8192           # explicit — FR-SUB-002; module default of 512 is the R4 failure mode

  network_bridge  = "vmbr0"
  network_ip      = "192.168.50.167/24"
  network_gateway = "192.168.50.1"
  nameserver      = "192.168.50.194"
  searchdomain    = var.domain

  ssh_keys = var.ssh_keys
  mounts   = []

  tags = ["forge", "project", "ai-dev", "homelab"]
}
```

```hcl
# outputs.tf — locals.all_containers append:
{
  name       = module.ct_forge_01.name
  node       = module.ct_forge_01.node
  vmid       = module.ct_forge_01.ctid
  monitoring = module.ct_forge_01.monitoring
},

# outputs.tf — locals.project_container_host_map append:
"ct-forge-01" = module.ct_forge_01.ip_address
```

## Test Plan

**Pre-state:** No `module "ct_forge_01"` block exists; `ct_sparkle_vlabel` phantom resolved (FE0-S05 done); R4 sizing decision recorded.

**Action sequence:**
1. Confirm FE0-S05 and the R4 decision are both closed (pre-flight check, not an AC but a hard gate on starting).
2. Append the `module "ct_forge_01"` block (AC1, AC2).
3. Append the two `outputs.tf` entries (AC3, AC4).
4. Run `terraform fmt -check` and `terraform validate` (AC5).

**Post-state checks:**
- `grep -A25 'module "ct_forge_01"' main.tf` shows all required arguments including explicit `swap_mb`.
- `grep -A5 'ct-forge-01' outputs.tf` shows both the `all_containers` entry and the host-map entry.
- `terraform validate` exits 0.

**Rollback:** `git checkout -- homelab-infra/terraform/envs/homelab/main.tf homelab-infra/terraform/envs/homelab/outputs.tf`. No `apply` has run yet at this story's boundary, so rollback is a pure working-tree revert with zero infrastructure impact.

## Dependencies

- **Blocked by:** FE0-S01, FE0-S02 (§5.4), FE0-S05 (phantom block must be resolved first), and the operator's R4 sizing decision (not a story — an out-of-band operator call recorded wherever the operator tracks it).
- **Blocks:** FE1-S02 (plan/apply consumes this story's block).

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| R4 is not actually resolved before this story starts, and a dev picks a sizing value unilaterally | Medium | High — reintroduces the exact OOM/undersized-swap failure R4 warns about | The banner is placed directly under the H1 per the template's "never buried in prose" rule; AC1/AC2 both require the operator's chosen values, not a default |
| `ct_sparkle_vlabel` phantom still present when this story's edit lands, causing an apply to recreate it later | Low (if FE1-S01 correctly gates on FE0-S05) | High — recreates a destroyed container | Explicit dependency on FE0-S05 in this story's Dependencies section and pre-flight check |
| Module argument mismatch vs. `ct_saply_ai` (e.g. wrong `ostemplate` string) causes a later `plan` to fail | Low | Low — caught by `terraform validate` in AC5 before any plan/apply | AC5 requires `validate` to pass as part of this story, not deferred to FE1-S02 |

## Definition of Done

- [ ] AC1–AC5 all green and evidenced.
- [ ] `module "ct_forge_01"` block present in `main.tf`, sized per the operator's R4 decision, with `swap_mb` explicit.
- [ ] Both `outputs.tf` registrations present, no wildcard entries.
- [ ] `terraform fmt -check` and `terraform validate` both pass.
- [ ] Story status updated from `draft` to `done` in this file's frontmatter.
