---
type: story
epic: FE3
id: FE3-S01
title: "forge-platform branch: local image build plus four real variables for sizing defaults and maxima"
size: M
priority: MUST
owner: dev
blocking: false
fr_refs: [FR-WS-001, FR-WS-002, FR-WS-009]
nfr_refs: [NFR-CAP-002]
adr_refs: []
risk_refs: [R4]
gate_refs: [h]
status: done
date: 2026-09-09
---

# FE3-S01: forge-platform branch: local image build plus four real variables for sizing defaults and maxima

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
>    **any** browser-trusted certificate — the homelab has no inbound :80/:443, so HTTP-01 is
>    impossible, not merely inconvenient. Wildcard scope is optional; the token is not.
>    **REVERSED 2026-09-09 — a wildcard IS required.** The token sentence still holds and the
>    token needs no re-scoping; only the "wildcard scope is optional" clause is dead. See the
>    amendment at the top of [ADR-005](../adrs/ADR-005-dns-01-wildcard-over-public-ingress.md).

> **CARRIES THE UNRESOLVED R4 SIZING DECISION.** This story is **one of the two candidate
> resolutions** to the sizing conflict recorded against FE1-S01, not a resolution in itself. The
> workspace template's `coder_parameter` defaults are **12288 MB RAM** (`main.tf:62`) and
> **20480 MB swap** (`main.tf:77`). They are `coder_parameter`, **not** `variable`, so a
> `--variables-file` **cannot** lower them; `min = 2048` and `mutable = true` mean an operator
> *can* choose smaller at create time, but only by remembering to, every time. Swap has no answer
> inside an unprivileged LXC — `swap_mb` defaults to **512 MB** in `modules/ct-debian`. The two
> candidate resolutions, **neither chosen by the proposal's approval**: (a) **this story** — four
> real `variable`s driving both the `coder_parameter` defaults and their validation maxima, paired
> with an explicit `swap_mb = 8192` set at FE1-S01; or (b) size CT 167 at **4C/12GB** instead. This
> is an operator capacity call against pve3 that approval of the proposal explicitly did **not**
> settle. **Do not treat authoring this story as resolving R4** — the values this story's new
> `variable`s should actually be set to depend on that still-open operator decision, and the ACs
> below default the values conservatively (matching the current template) rather than presuming
> an answer.

## User Story

As **tomamourette**, I want **the forge-platform PoC branch building its workspace image from a local `docker build` instead of Azure Container Registry, and four real Terraform `variable`s added that drive both the four `coder_parameter` defaults and their validation maxima**, so that **the workspace template needs no registry credentials to run on CT 167, and once the R1/R4 sizing decision is finally made, changing the defaults is a one-line `--variables-file` edit instead of a hand-edit of `main.tf` every time**.

## Background and Context

Two independent changes are bundled in this story because both touch the same `coder_parameter`/`locals` region of `coder/templates/forge/main.tf` and both are needed before `terraform apply` can succeed on a Proxmox host with no ACR reachable.

**Image source (uncontested, not part of R4):** `local.image` is currently `"saplyforgedevacr.azurecr.io/forge-workspace:latest"` (`main.tf:107`), and `resource "docker_image" "main"` already sets `keep_locally = true` (`main.tf:548-551`) — meaning the template was already designed to tolerate an image that isn't freshly pulled from a registry every time. Per evidence **E5**, this is the cheapest of the substitutions: change `local.image` to reference an image built locally on `ct-forge-01` via `docker build` (FE3-S06 does the actual build; this story only changes what `local.image` points at and what parameter/variable controls it, if any). No registry is needed at all — this part of the story is uncontested and does not touch R4.

**Sizing variables (the R4-adjacent part):** `main.tf:42-99` defines four `coder_parameter` blocks — `workspace_cpu_shares` (default 1024, min 256, max 4096), `workspace_memory_mb` (default 12288, min 2048, max 15360), `workspace_memory_swap_mb` (default 20480, min 2048, max 32768), `workspace_memory_reservation_mb` (default 2048, min 512, max 8192). Because these are `coder_parameter` (mutable, operator-facing form fields at workspace-create time) rather than `variable` (template-author-facing, settable via `-var`/`--variables-file`), there is currently **no way** for whoever runs `coder templates push` to change the *defaults* a new workspace starts with, short of editing `main.tf` directly — which HARD RULE / FR-WS-009 forbids (no forking `main.tf`; additive variables only). FR-WS-002 requires four real `variable`s that feed **both** the `default` **and** the `validation.max` of each corresponding `coder_parameter`, so a `--variables-file` becomes the single point of control the R4 decision needs, whichever way it resolves.

## Acceptance Criteria

**AC1 — `local.image` sources from a local build, no registry reference remains as the default.**
- **Given** the forge-platform PoC branch,
- **When** the operator runs `grep -n 'azurecr.io' coder/templates/forge/main.tf`,
- **Then** the count is `0` — `local.image` (or a new `variable` controlling it) resolves to a locally-tagged image name (e.g. `forge-workspace:local`) with no ACR hostname anywhere in the template.

**AC2 — Four new `variable` blocks exist, each feeding one `coder_parameter`'s default and max.**
- **Given** `main.tf` on the PoC branch,
- **When** the operator runs `terraform validate` in `coder/templates/forge/`,
- **Then** it passes, and four `variable` blocks exist — `workspace_cpu_shares_default`/`_max` (or an equivalent single-variable-with-both-fields shape, see Implementation Notes), and likewise for `workspace_memory_mb`, `workspace_memory_swap_mb`, `workspace_memory_reservation_mb` — each referenced by the corresponding `coder_parameter`'s `default` and `validation.max` fields (no hardcoded literals left in those two fields for these four parameters).

**AC3 — Defaults left conservative, not pre-resolving R4.**
- **Given** AC2 has passed,
- **When** the operator diffs the new `variable` defaults against the current `coder_parameter` defaults,
- **Then** the new variables' defaults **match the existing values exactly** (1024 / 12288 / 20480 / 2048, maxima 4096 / 15360 / 32768 / 8192) — this story does not change runtime behavior by itself; it only makes the values changeable. Actually lowering them (option (a) of R4) is a separate, explicit operator-approved follow-up, not silently bundled here.

**AC4 — `main.tf` not forked.**
- **Given** FR-WS-009,
- **When** the operator runs `git diff --stat` between the PoC branch and the upstream `forge-platform` default branch for `coder/templates/forge/main.tf`,
- **Then** the diff is additive (`variable` blocks added, `local.image` value changed, `coder_parameter.*.default`/`.validation.max` fields repointed to the new variables) — no unrelated restructuring, no renamed resources, no deleted blocks other than the literal values now sourced from variables.

**AC5 — `terraform plan` in the template directory is clean.**
- **Given** AC1–AC4 have passed,
- **When** the operator runs `terraform plan` in `coder/templates/forge/` with no `--variables-file` supplied (i.e., relying purely on the new variables' defaults),
- **Then** the plan shows the same resource shape as before this story (no unexpected diffs), confirming the refactor is behavior-preserving until someone deliberately overrides a variable.

## Implementation Notes

Reference §2.3 (sizing conflict), FR-WS-001, FR-WS-002, FR-WS-009, R4, the FE1-S01 second banner (same underlying decision). Two structurally simple options for AC2's variable shape — either is acceptable, pick whichever matches forge-platform's existing Terraform style once inspected:

```hcl
# Option A — one variable per (parameter, bound) pair
variable "workspace_memory_mb_default" {
  type    = number
  default = 12288
}
variable "workspace_memory_mb_max" {
  type    = number
  default = 15360
}
# ... repeated for cpu_shares, memory_swap_mb, memory_reservation_mb (8 variables total)

data "coder_parameter" "workspace_memory_mb" {
  # ...
  default = tostring(var.workspace_memory_mb_default)
  validation {
    min = 2048
    max = var.workspace_memory_mb_max
  }
}
```

```hcl
# Option B — one object variable per parameter (4 variables total, matching "four new variables" literally)
variable "workspace_memory_mb" {
  type = object({ default = number, min = number, max = number })
  default = { default = 12288, min = 2048, max = 15360 }
}

data "coder_parameter" "workspace_memory_mb" {
  # ...
  default = tostring(var.workspace_memory_mb.default)
  validation {
    min = var.workspace_memory_mb.min
    max = var.workspace_memory_mb.max
  }
}
```

FR-WS-002 says "four real `variable`s" — **Option B satisfies that literally** (one variable per sizing knob, each carrying default+max, optionally min); prefer it unless the existing codebase's Terraform style strongly favors flat scalars.

```bash
# AC verification
grep -n 'azurecr.io' coder/templates/forge/main.tf   # expect 0 hits
terraform validate coder/templates/forge/
terraform plan coder/templates/forge/                # no --variables-file; expect a clean, unsurprising plan
git diff --stat upstream/main -- coder/templates/forge/main.tf
```

## Test Plan

**Pre-state:** `local.image` points at `saplyforgedevacr.azurecr.io/...`; all four sizing knobs are `coder_parameter` with hardcoded default/validation literals; no `variable` blocks exist for them.

**Action sequence:**
1. Change `local.image` (or introduce a variable for it) to a local image reference (AC1).
2. Add the four `variable` blocks and repoint the `coder_parameter` default/max fields (AC2).
3. Diff the new variable defaults against the pre-existing literals to confirm no value changed (AC3).
4. `terraform validate` and `terraform plan` with no overrides (AC4, AC5).
5. As a smoke test only (not this story's job to decide values), try `terraform plan -var='workspace_memory_mb={default=4096,min=2048,max=15360}'` and confirm the plan reflects a lowered default — proving the mechanism works, without adopting the lowered value as this story's outcome.

**Post-state checks:**
- Zero `azurecr.io` references.
- `terraform validate` passes.
- `terraform plan` with defaults matches pre-change resource shape.
- A `-var` override demonstrably changes the resulting `coder_parameter` default in a plan.

**Rollback:** `git checkout` the pre-story `main.tf` on the PoC branch; no infrastructure has been applied by this story (this is a template-source change, exercised at `coder templates push` time in FE3-S06).

## Dependencies

- **Blocked by:** FE1-S05 (privileged-Docker-in-LXC measurement, informative context for what CT 167 can actually sustain — not a hard technical dependency for this Terraform edit, but the R4 decision this story exists to serve depends on knowing FE1-S05's result).
- **Blocks:** FE3-S06 (image build + template push uses this branch's `main.tf`), FE4-S02 gate (h) (sizing measured against whatever this story's variables and the R4 decision produce).
- **Operator decision still open:** the actual values to set once this mechanism exists (R4 option (a) vs. option (b), 4C/12GB) — not resolved by this story or any other in FE1–FE4.

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Authoring this story is mistaken for *resolving* R4 | Medium — the two are easy to conflate since they touch the same lines | Medium — a false sense that the sizing question is closed | AC3 explicitly keeps defaults unchanged; the banner above states this in the story itself |
| `coder_parameter.validation.max` becomes a computed expression Terraform can't validate at plan time for a `data` block (some `coder_parameter` validation fields may require literal-like values) | Low | Medium — `terraform validate` could reject a variable-sourced max | AC2's own `terraform validate` gate catches this immediately; if it fails, fall back to a `locals` intermediate that resolves the variable before assignment |
| Local image build (AC1) and FE3-S06's actual build/push are done out of order, leaving `local.image` pointing at an image that doesn't exist yet | Low | Low — `terraform plan`/`apply` simply fails until FE3-S06 runs | Sequence documented in Dependencies; this story only changes the *reference*, not the image's existence |

## Definition of Done

- [ ] AC1–AC5 all green and evidenced.
- [ ] `local.image` (or its replacement) references no ACR hostname.
- [ ] Four `variable` blocks exist, feeding both defaults and maxima, with unchanged default values.
- [ ] `terraform validate` and a no-override `terraform plan` both clean.
- [ ] R4 explicitly recorded as still open in this story's own text (not resolved by authoring it).
- [ ] Story status updated from `draft` to `done` in this file's frontmatter.
