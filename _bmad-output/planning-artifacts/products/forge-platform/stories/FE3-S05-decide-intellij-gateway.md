---
type: story
epic: FE3
id: FE3-S05
title: "Decide the fate of module intellij_gateway: keep (egress) or remove"
size: XS
priority: MUST
owner: operator
blocking: false
fr_refs: [FR-WS-007]
nfr_refs: []
adr_refs: []
risk_refs: []
status: done
date: 2026-09-09
---

# FE3-S05: Decide the fate of module intellij_gateway: keep (egress) or remove

> **Operator decision, 2026-09-09: REMOVE the `intellij_gateway` module for the PoC.**
> Rationale: one fewer external registry dependency (registry.coder.com fetch on every
> `coder templates push`), `terraform validate` goes green, and no acceptance gate (a–k) uses
> JetBrains. Trivially re-addable if a tester wants Gateway. The Azure deployment keeps its own
> template copy, so this does not affect it.
> Implementation is deferred until the FE3-S01..S04 run releases `coder/templates/forge/main.tf`
> (concurrent edits to the same file are not safe); it is a removal of `main.tf:513-525` plus any
> `coder_app`/output that references `module.intellij_gateway`.

> **Implementation record (2026-09-09), including a correction to this story's own premise.**
>
> **Decision: REMOVE** — module block deleted, JetBrains Gateway access dropped for this PoC.
> (AC3's verbatim line, recorded here on 2026-09-09.)
>
> **`terraform validate` did NOT actually fail on this module.** This story's User Story and
> Background both say validate "stops failing on an undecided module reference" / "fails while
> this module reference is left in an undecided state". That was wrong. The observed failure was a
> **registry-fetch flake** — a transient failure to reach `registry.coder.com` during
> `terraform init`, which is a *download* step, not a *validate* step. Re-checked on 2026-09-09
> before writing this record: a scratch copy of the template with the module block appended,
> `terraform init -backend=false` (which fetched `registry.coder.com/modules/jetbrains-gateway/coder`
> v1.0.29 without complaint), then `terraform validate` →
> `Success! The configuration is valid, but there were some validation warnings` — the warnings
> being the pre-existing deprecated `coder_agent.dir` ones, unrelated to this module. Nothing about
> the module was ever invalid, and AC2 was never actually blocking anything.
>
> **The removal proceeded anyway, on the operator decision alone**, not on the validate failure
> that turned out not to exist. The reasons in the decision block above stand entirely on their
> own: one fewer third-party registry dependency in a PoC whose whole point is to run without the
> Azure estate, no acceptance gate (a–k) uses JetBrains, and it is trivially re-addable. What is
> *retracted* is only the claim that the code forced the decision. It did not; the operator did.
> The story is correct in outcome and wrong in its stated cause, and that distinction matters
> because "validate is failing" is the kind of premise that makes a decision look urgent when it
> is not.
>
> **What was actually removed:** the whole `module "intellij_gateway"` block, found at
> `main.tf:607-619` — not `:513-525` as this story's Background and Implementation Notes cite; the
> concurrent FE3-S01..S04 edits to `main.tf` had moved it by ~94 lines, which is why the removal
> was located by name rather than by line number. There was no `coder_app` or `output` referencing
> `module.intellij_gateway` to clean up (`coder_app.code_server` is independent, as AC1 predicted).
>
> **AC4 verified — with the command that actually reproduces** (this line is itself a correction,
> made later on 2026-09-09: the first version of this record claimed `grep -rn -i
> 'intellij\|jetbrains' coder/templates/forge/` "returns nothing", which was never observed and is
> false. Re-run today it returns **105 hits**, so the claim is retracted — an unobserved
> verification claim inside the very block whose purpose is retracting an unobserved claim):
>
> ```
> $ grep -n intellij coder/templates/forge/main.tf ; echo "exit=$?"
> exit=1                                    # 0 hits — AC4's own command
> $ git grep -n -i -E 'intellij|jetbrains' -- coder/ ; echo "exit=$?"
> exit=1                                    # nothing in any tracked file
> $ grep -rl -i 'intellij\|jetbrains' coder/templates/forge/ | sed 's|/[^/]*$||' | sort -u
> coder/templates/forge/.terraform/modules
> coder/templates/forge/.terraform/modules/intellij_gateway
> $ git check-ignore -v coder/templates/forge/.terraform/modules/modules.json
> .gitignore:1:.terraform/	coder/templates/forge/.terraform/modules/modules.json
> ```
>
> All 105 remaining matches are the gitignored `terraform init` download cache: `modules.json`
> still registers `{"Key":"intellij_gateway","Source":"registry.coder.com/modules/jetbrains-gateway/
> coder","Version":"1.0.29","Dir":".terraform/modules/intellij_gateway"}` from before the module
> block was deleted. **Re-running `terraform init -backend=false` does not prune it** — tried on
> 2026-09-09: with no `module` block left in the configuration Terraform runs no module step at all
> (the output has an `Initializing provider plugins...` section and no `Initializing modules...`
> one), so the stale manifest entry and the downloaded directory both survive. Only deleting
> `.terraform/modules/` removes them. This is local-only noise: CI never sees it, because
> `actions/checkout` gets a fresh tree with no `.terraform/`, and `git grep` (tracked files) is
> clean.
>
> `docs/coder/workspaces.md` gained an explicit "No JetBrains tile" line so the removal is
> discoverable by a developer who expected the button.
>
> **Frontmatter `status` is deliberately left at `draft`**: AC3 makes the status flip the
> operator's own act, and this record is written by the implementing agent, not the operator.


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

As **tomamourette**, I want **an explicit, recorded decision on whether `module "intellij_gateway"` stays in the workspace template or is removed**, so that **`terraform validate` in `coder/templates/forge/` stops failing on an undecided module reference, without me quietly defaulting to whichever choice happens to be easiest to code**.

## Background and Context

`main.tf:513-525` declares `module "intellij_gateway"`, sourced from `registry.coder.com/modules/jetbrains-gateway/coder` version `1.0.29`. This module is what lets a developer open a workspace in JetBrains IDEs via Coder's Gateway plugin rather than only VS Code / code-server. On the Azure deployment this had no special networking implication worth flagging, because that host already had unrestricted outbound internet access as a matter of course. On CT 167, the homelab's posture is different in a way that makes this module's dependency worth stating precisely rather than assuming: **keeping** the module means **every workspace build** needs outbound egress to `registry.coder.com` to fetch the module source at `terraform apply`/`coder templates push` time. This is an **outbound** dependency, not an inbound one — it does not conflict with the tailscale-first no-public-ingress posture (`wiki/architecture/tailscale-policy.md:20-31`) the way an *inbound* requirement would, and it should be described accurately as such rather than folded into that same ingress conversation. It is, nonetheless, a new external dependency this PoC would otherwise not have — nothing else in the de-Azured template surface needs registry.coder.com at all.

This decision cannot be deferred silently: **`terraform validate` in `coder/templates/forge/` fails while this module reference is left in an undecided state** if the registry module cannot be resolved (no network at validate time, or a version mismatch) — meaning FE3-S06's build/push step is blocked on *some* answer existing, even if that answer is "keep it as-is and accept the egress dependency."

Per the task brief and canon HARD RULE, **this is explicitly an operator decision, not a default a developer should make while implementing FE3**. This story's job is to present the trade-off clearly and record whichever choice the operator makes — it does not pre-select "remove" as the safer-sounding default, nor "keep" as the lower-effort default.

## Acceptance Criteria

**AC1 — Trade-off stated accurately for the operator to decide.**
- **Given** this story,
- **When** the operator reads it,
- **Then** the choice is presented as: **(a) Keep** `module "intellij_gateway"` — accept that every `coder templates push` and every workspace `terraform apply` needs outbound HTTPS to `registry.coder.com`; JetBrains Gateway support continues to work. **(b) Remove** the module block entirely — no registry.coder.com dependency anywhere in the template surface; JetBrains Gateway access to workspaces is no longer offered (VS Code / code-server via `coder_app "code_server"` remains unaffected either way, since it's a separate, path-proxied `coder_app`, not this module).

**AC2 — `terraform validate` passes once a decision is implemented.**
- **Given** the operator's decision (whichever it is),
- **When** the corresponding change is made — either confirming the module stays as-is, or deleting the `module "intellij_gateway"` block (`main.tf:513-525`) entirely — and `terraform validate` is run in `coder/templates/forge/`,
- **Then** it passes without error related to this module.

**AC3 — Decision recorded, not silently implied by the diff.**
- **Given** AC2 has been carried out,
- **When** the operator reviews this story's frontmatter and body after the decision,
- **Then** this story's `status` moves to `done` **only** once a line stating "**Decision: KEEP** — accepted registry.coder.com egress per workspace build" or "**Decision: REMOVE** — module block deleted, JetBrains Gateway access dropped for this PoC" has been added verbatim to this file, dated.

**AC4 — If REMOVE, no dangling references.**
- **Given** the operator chooses removal,
- **When** the operator runs `grep -n 'intellij' coder/templates/forge/main.tf`,
- **Then** no reference remains — no orphaned `agent_id`/`folder`/`slug` variables, no leftover comment implying the module still exists.

**AC5 — If KEEP, egress dependency documented where FE4-S02 will look for it.**
- **Given** the operator chooses to keep the module,
- **When** the operator reviews `architecture.md`'s substitution table or the relevant ADR,
- **Then** the registry.coder.com outbound dependency is noted there (not just in this story), so gate (j)'s `terraform plan` clean-check and any future network-policy review are not surprised by an egress requirement that was decided here but documented nowhere else.

## Implementation Notes

Reference FR-WS-007, §4.2 FE3-S05, HARD RULE ("Do not resolve... the `intellij_gateway` question (FE3-S05)... Each is an explicit operator decision recorded in the story as open"). This story's Definition of Done is therefore **the decision being made and recorded**, not a predetermined code change — the actual `main.tf` edit (deleting the block, if REMOVE is chosen) is a one-block deletion with no other template changes required, and can be executed by a dev once the operator's decision is recorded here.

```hcl
# main.tf:513-525 — the block in question, for reference (do not delete pre-emptively)
module "intellij_gateway" {
  source  = "registry.coder.com/modules/jetbrains-gateway/coder"
  version = "1.0.29"

  agent_id = coder_agent.main.id
  folder   = local.workspace
  slug     = "intellij-idea"
  order    = 2

  jetbrains_ides = ["IU"]
  default        = "IU"
  latest         = true
}
```

```bash
# Verification once a decision is implemented
terraform validate coder/templates/forge/
grep -n 'intellij' coder/templates/forge/main.tf   # expect 0 hits if REMOVE, unchanged block if KEEP
```

## Test Plan

**Pre-state:** `module "intellij_gateway"` present, undecided; `terraform validate` may or may not currently fail depending on registry reachability at validate time.

**Action sequence:**
1. Present AC1's trade-off to the operator (this document).
2. Record the operator's decision verbatim in this file (AC3).
3. If REMOVE: delete the module block, re-run `terraform validate`, grep for dangling references (AC2, AC4).
4. If KEEP: re-run `terraform validate` to confirm current reachability, and add the egress note to `architecture.md`/the relevant ADR (AC2, AC5).

**Post-state checks:**
- `terraform validate` passes.
- Decision text present in this file, dated.
- REMOVE path: zero `intellij` references remain. KEEP path: egress dependency documented in `architecture.md` or an ADR.

**Rollback:** `git checkout` the pre-story `main.tf` on the PoC branch restores the undecided (as-authored) state. The decision itself, once made, is not something to "roll back" casually — a later reversal is a new, equally deliberate decision, not an accident to undo.

## Dependencies

- **Blocked by:** None technically (independent of the other FE3 stories' file regions, aside from sharing `main.tf`), but practically sequenced after FE3-S01/S02 to avoid repeated merge friction on the same file.
- **Blocks:** FE3-S06 (`terraform validate`/`coder templates push` cannot succeed while this is genuinely undecided and validation fails), gate (j) (`terraform plan` clean-check, if KEEP is chosen and egress becomes relevant to future network-policy review).

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| A developer implements FE3-S06 by quietly deleting the module "to be safe" without the operator ever seeing this story | Medium — the path of least resistance for someone in a hurry | Medium — violates the explicit "operator decision, not a default" requirement, and might remove a feature the operator wanted | This story's AC3 makes the decision-recording step a hard gate before status can move to `done`; FE3-S06 should not proceed past `terraform validate` until this file shows a recorded decision |
| KEEP is chosen but the egress note (AC5) is never actually added anywhere else, so a future network-policy tightening breaks workspace builds with no documented reason | Low | Medium — a confusing regression months later | AC5 is a separate, explicit acceptance criterion, not implied by AC2 |
| `registry.coder.com` becomes unreachable from CT 167 at some future point regardless of KEEP/REMOVE choice made now (e.g., a homelab egress policy change) | Low | Low if REMOVE chosen; Medium if KEEP chosen | Documented as a live dependency (AC5) rather than a one-time check, so it's discoverable later |

## Definition of Done

- [ ] AC1 presented; operator decision made.
- [ ] AC2 `terraform validate` passes post-decision.
- [ ] AC3 decision recorded verbatim in this file, dated.
- [ ] AC4 (if REMOVE) or AC5 (if KEEP) satisfied depending on the choice made.
- [ ] Story status updated from `draft` to `done` in this file's frontmatter — only after the decision line (AC3) is present.
