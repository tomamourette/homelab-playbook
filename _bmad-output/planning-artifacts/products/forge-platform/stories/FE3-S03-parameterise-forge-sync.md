---
type: story
epic: FE3
id: FE3-S03
title: "Parameterise forge-sync.sh (org, repo list, ADO block) preserving flags and failure messages"
size: M
priority: MUST
owner: dev
blocking: false
fr_refs: [FR-WS-005]
nfr_refs: []
adr_refs: []
risk_refs: []
status: done
date: 2026-09-09
---

# FE3-S03: Parameterise forge-sync.sh (org, repo list, ADO block) preserving flags and failure messages

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

## User Story

As **tomamourette**, I want **`forge-sync.sh` parameterised so its GitHub org, ADO org, and repo deny list are already externally overridable (not hardcoded), while every per-repo behavior — the distinct `warn_private_clone_failed` message per repo, the `--recurse-submodules` flag on `agentic-ai`/GitHub-org clones but not on `knowledge-base`, the `--ff-only` pull semantics — is preserved exactly**, so that **the script that clones `agentic-ai` into every Forge workspace continues to behave identically for this PoC while being genuinely reusable by a future company that isn't Saply**.

## Background and Context

Reading `forge-sync.sh` closely, most of the parameterisation FR-WS-005 asks for **already exists**: `DENY="${FORGE_SYNC_DENY:-agentic-ai knowledge-base company-overlay}"` (line 8), `GITHUB_ORG="${FORGE_GITHUB_ORG:-Saply-ai}"` (line 9), and `ADO_ORG="${FORGE_ADO_ORG:-saplyai}"` (line 10) are all already environment-variable-overridable with a Saply-shaped default, and `main.tf:302` already passes `FORGE_SYNC_DENY`, `FORGE_GITHUB_ORG`, `FORGE_ADO_ORG` into the script's environment at boot. This story's real scope, once that's confirmed, is narrower than "parameterise from scratch": verify each of these three already-parameterised values is actually wired end-to-end from the template (not just present as a script-level default that nothing overrides), and parameterise anything still hardcoded that FR-WS-005 requires — specifically the **ADO block**, which is not currently config-driven the same way.

The ADO block (`forge-sync.sh:81-108`) is more deeply Saply-specific than the org name alone: it authenticates via `coder external-auth access-token azure-devops`, falling back to `az account get-access-token --resource 499b84ac-1321-427f-aa17-267ca6975798` (a fixed Azure DevOps resource GUID, correct for any ADO tenant, not Saply-specific) if the Coder token is absent, then walks **all** ADO projects in the org via the REST API. This part is left functionally intact by this story — ADO is explicitly out of PoC scope for *exercising*, but the script must not be stripped of ADO support entirely, since a future company might use it; the story's job is to confirm the ADO org name is override-driven the same way the GitHub org already is (it is: `ADO_ORG`), and that no Saply-only literal (a hardcoded project name, a hardcoded ADO org string inside the loop body itself rather than in the `ADO_ORG` variable) remains buried in the walk logic.

The non-negotiable constraint (per the task brief and canon HARD RULE) is preserving **per-repo flags and distinct failure messages exactly**: `agentic-ai` and `knowledge-base` each get their own tailored `warn_private_clone_failed` call (`forge-sync.sh:58-59, 66-67`) with repo-specific human-readable descriptions ("the Agentic AI dev environment (skills, plugins, hooks)" vs. "the Knowledge Base (company-wide docs and research)"), and the generic per-org loop (`:46-54`) uses no such message at all — clone failures there are silent (`|| true`), which is itself intentional behavior (a private repo in the org that this GitHub user simply can't see should not spam every workspace boot log). None of this differentiated behavior should collapse into one generic function during parameterisation.

## Acceptance Criteria

**AC1 — Confirm existing parameterisation is genuinely wired, not just present.**
- **Given** `main.tf:302` (`FORGE_SYNC_DENY="${join(" ", local.repo_deny)}" FORGE_GITHUB_ORG="${local.github_org}" FORGE_ADO_ORG="${local.ado_org}" "$HOME/.local/bin/forge-sync"`),
- **When** the operator sets `local.github_org = "test-org"` in a scratch Terraform plan (not applied) and inspects the rendered `startup_script`,
- **Then** the rendered `FORGE_GITHUB_ORG=test-org` appears verbatim in the script invocation — confirming the override path from `locals` through to the running script is real, not aspirational.

**AC2 — ADO org name has no hardcoded literal outside the `ADO_ORG` variable.**
- **Given** `forge-sync.sh:81-108` (the ADO block),
- **When** the operator runs `grep -n 'saplyai' coder/templates/forge/forge-sync.sh`,
- **Then** the only match is the `ADO_ORG="${FORGE_ADO_ORG:-saplyai}"` default-value assignment on line 10 — no other line hardcodes `saplyai` inside the walk/clone logic itself.

**AC3 — Per-repo failure messages preserved verbatim.**
- **Given** the parameterised script,
- **When** the operator diffs `warn_private_clone_failed` and its two call sites (`agentic-ai`, `knowledge-base`) before and after this story,
- **Then** the function body and both call sites' repo-description arguments are byte-identical to the pre-story version — this story does not touch them.

**AC4 — Per-repo flags preserved.**
- **Given** the parameterised script,
- **When** the operator diffs the `gh repo clone` invocations for the org loop, `agentic-ai`, `knowledge-base`, and `company-overlay`,
- **Then** the `--recurse-submodules` flag remains present on the org loop, `agentic-ai`, and `company-overlay` clones and remains **absent** on the `knowledge-base` clone, exactly matching current behavior (`forge-sync.sh:52,58,66,74` — note `knowledge-base`'s clone at line 66 has no `-- --recurse-submodules`, unlike the other three).

**AC5 — Idempotent, no behavior change for the current Saply deployment.**
- **Given** all defaults are left as `Saply-ai`/`saplyai`/`agentic-ai knowledge-base company-overlay`,
- **When** the operator runs the parameterised script with no environment overrides at all,
- **Then** its behavior is observably identical to the pre-story script — this is a parameterisation story, not a behavior-change story, and the PoC's own workspace (which will *not* override these to a different company, since it is testing Forge with Saply's own agentic-ai repo per FR-KIT-001) must keep working exactly as before.

## Implementation Notes

Reference FR-WS-005, the task brief's explicit note "preserving the per-repo flags and the distinct failure messages," `forge-sync.sh:1-108` in full. Because most of this script is already parameterised, the bulk of the implementation work is **verification and closing any remaining gap in the ADO block**, not a rewrite.

```bash
# AC1 — confirm the wiring end to end
terraform plan -var 'github_org_override=test-org' coder/templates/forge/ 2>&1 | grep -A2 FORGE_GITHUB_ORG
# (adjust to however local.github_org is actually surfaced as a variable, if FE3-S01's pattern extends here)

# AC2 — no stray hardcoded org literal
grep -n 'saplyai' coder/templates/forge/forge-sync.sh

# AC3/AC4 — diff-based regression checks
git diff coder/templates/forge/forge-sync.sh   # review by eye against the "preserve exactly" requirement
```

If `local.github_org`/`local.ado_org` in `main.tf:114-115` are themselves still hardcoded `locals` rather than `variable`s, and the team wants organisation-level overridability (not just per-workspace env-var overridability, which already exists via `FORGE_GITHUB_ORG`/`FORGE_ADO_ORG`), promoting them to `variable`s is in scope for this story too — but note that doing so is a `main.tf` edit, not a `forge-sync.sh` edit, and should follow the same additive-variable pattern as FE3-S01 rather than duplicating it.

## Test Plan

**Pre-state:** `forge-sync.sh` already has `FORGE_SYNC_DENY`/`FORGE_GITHUB_ORG`/`FORGE_ADO_ORG` env-var overrides with Saply defaults; ADO org name confirmed (pending AC2) to appear only in the default assignment.

**Action sequence:**
1. Grep for any hardcoded `saplyai`/`Saply-ai` literal outside the three default-value assignments (AC2).
2. Diff `warn_private_clone_failed` and its call sites against the pre-story version (AC3).
3. Diff all `gh repo clone` invocations for flag consistency (AC4).
4. Confirm no-override behavior is unchanged by re-reading the full script end to end (AC5).
5. Defer AC1's live rendered-script check to FE3-S06/FE4-S01 if a scratch `terraform plan` isn't practical before the template is otherwise buildable — record whichever path was actually used.

**Post-state checks:**
- Zero stray `saplyai`/`Saply-ai` literals outside the three default assignments.
- Failure-message function and call sites byte-identical.
- Flag pattern (`--recurse-submodules` present/absent) matches original per repo.

**Rollback:** `git checkout` the pre-story `forge-sync.sh` on the PoC branch. No infrastructure state touched.

## Dependencies

- **Blocked by:** FE3-S02 (shares thematic ground — `repo_deny`/`FORGE_SYNC_DENY` — sequence to avoid confusion, though the two stories touch different files).
- **Blocks:** FE4-S01 (first workspace create exercises this script with the actual GitHub token).

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| "Parameterise" is read as "rewrite," and the rewrite accidentally collapses the two distinct failure messages into one generic template string | Medium — this is the single easiest way to violate the story's own requirement | High — undoes exactly what canon and the task brief both called out by name | AC3's byte-identical diff check is the explicit guard against this |
| The ADO walk logic (project enumeration via REST API) has a genuinely Saply-shaped assumption beyond just the org name (e.g., an assumed API version, a hardcoded resource GUID) mistaken for something to "fix" | Low | Medium — the ADO resource GUID `499b84ac-1321-427f-aa17-267ca6975798` is Azure DevOps's own fixed first-party resource ID, correct for **any** ADO tenant; changing it would break ADO auth for everyone | AC2 scopes the check specifically to the org **name**, not the resource GUID; document this distinction so a future reviewer doesn't "fix" the GUID by mistake |
| Confirming AC1's live wiring requires a template push this story can't yet do (FE3-S06 hasn't run) | Medium | Low — verification deferred, not skipped | Test Plan explicitly allows deferring AC1's live check and cross-referencing FE3-S06/FE4-S01 |

## Definition of Done

- [ ] AC2–AC5 all green and evidenced by direct inspection/diff.
- [ ] AC1 verified either via scratch plan or deferred-and-cross-referenced to FE3-S06/FE4-S01.
- [ ] No hardcoded Saply org literal outside the three default-value assignments.
- [ ] Per-repo failure messages and clone flags confirmed unchanged.
- [ ] Story status updated from `draft` to `done` in this file's frontmatter.
