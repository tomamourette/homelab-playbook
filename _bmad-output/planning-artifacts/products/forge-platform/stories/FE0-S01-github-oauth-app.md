---
type: story
epic: FE0
id: FE0-S01
title: "Create the GitHub OAuth App and record CODER_EXTERNAL_AUTH_0_* credentials"
size: S
priority: MUST
owner: operator
blocking: true
fr_refs: [FR-PRE-001, FR-PRE-003]
nfr_refs: [NFR-SEC-003]
adr_refs: []
risk_refs: []
gate_refs: [b]
status: done
date: 2026-09-09
---

# FE0-S01: Create the GitHub OAuth App and record CODER_EXTERNAL_AUTH_0_* credentials

> **OPERATOR TASK — BLOCKING. Cannot be delegated.**

## User Story

As **tomamourette**, I want **a GitHub OAuth App created and its `CODER_EXTERNAL_AUTH_0_ID/TYPE/CLIENT_ID/CLIENT_SECRET` values recorded**, so that **the Coder control plane can authenticate to GitHub on the workspace's behalf, `forge-sync.sh` can clone `agentic-ai` into the workspace, and gates (b)–(e) become testable instead of silently degrading**.

## Background and Context

This is the first story of FE0 (Prerequisites and truth) and one of the two hard blockers named in §5.4 of the approved sprint-change-proposal-2026-09-09.md: nothing in FE1–FE4 begins before this exists. Evidence item **E6.1** established why this credential is different from every other external dependency in the PoC: `data "coder_external_auth" "github"` (`coder/templates/forge/main.tf:25-27`) carries no `optional = true` — unlike the `azuredevops` provider at `:32-35` — so the workspace build **fails outright** without a working GitHub external-auth grant. Even supposing the build were patched to tolerate its absence, `forge-sync.sh` sources its token from `coder external-auth access-token github` and **silently skips its entire clone block** when that call returns nothing, meaning `agentic-ai` never reaches the workspace and the PoC's toolkit gates (b)–(e) have nothing to test. Every other external credential in this PoC (ADO, OpenMemory, Langfuse) degrades cleanly via the empty-file-means-disabled contract (E5); this one does not. It is, per HARD RULE 4(i) of the canon, the **only non-optional external credential in the whole PoC**.

The grant must specifically cover `tomamourette/agentic-ai` — the repo `forge-sync.sh` needs to clone (FR-KIT-001). A GitHub OAuth App scoped to the wrong account, org, or with an unaccepted authorization will produce the same silent-skip failure as having no App at all, so verifying the grant is a first-class acceptance criterion here, not an afterthought.

Per the canon's HARD RULE 4, this secondary requirement travels with this story: FR-PRE-003 recommends adding `optional = true` to the same `data` block anyway, so a *future* missing or revoked grant degrades to a visible skip in the build log rather than a hard failure. This is **recommended alongside** FR-PRE-001, explicitly **not a substitute** for actually creating the App — the clone step still silently no-ops without the credential either way.

## Acceptance Criteria

**AC1 — OAuth App created.**
- **Given** the operator is signed in to the GitHub account that owns `tomamourette/agentic-ai`,
- **When** the operator creates a new OAuth App under GitHub Developer Settings, with its Authorization callback URL set to the Coder external-auth callback for the eventual `forge.bi-services.be` control plane (`https://forge.bi-services.be/external-auth/0/callback`, per Coder's external-auth convention),
- **Then** the App exists with a generated Client ID and Client Secret, and the App's homepage URL is set to `https://forge.bi-services.be` (placeholder acceptable pre-FE2, correctable later without re-creating the App).

**AC2 — All four credential values recorded.**
- **Given** AC1 has passed,
- **When** the operator records the four values `CODER_EXTERNAL_AUTH_0_ID` (a stable id such as `github`), `CODER_EXTERNAL_AUTH_0_TYPE=github`, `CODER_EXTERNAL_AUTH_0_CLIENT_ID`, and `CODER_EXTERNAL_AUTH_0_CLIENT_SECRET` in the operator's secure credential store (password manager or equivalent — **not** a file inside either git repo),
- **Then** all four values are retrievable and none appear in `git status` or `git diff` in `forge-platform`, `agentic-ai`, or `homelab-infra`.

**AC3 — Grant covers `tomamourette/agentic-ai`.**
- **Given** AC1 has passed,
- **When** the operator authorizes the OAuth App against the account holding `tomamourette/agentic-ai` (organization or personal, whichever is authoritative) and confirms via the GitHub UI (Settings → Applications → Authorized OAuth Apps) that the grant is active,
- **Then** the authorized scope includes read access to `tomamourette/agentic-ai`, verified by the App's authorization screen listing the repository or organization.

**AC4 — Values staged for FE2-S04, not yet deployed.**
- **Given** AC2 has passed,
- **When** the operator reviews `/etc/coder.d/coder.env` on the (not-yet-existing) `ct-forge-01` host,
- **Then** nothing is written there by this story — FR-CTL-007 wires these four values into `coder.env` at FE2-S04, once CT 167 exists. This story's Definition of Done is the credential existing and being recorded, not deployed.

**AC5 — Secondary AC, FR-PRE-003 (recommended alongside, not a substitute).**
- **Given** AC1–AC3 have passed,
- **When** a dev (not necessarily the operator, and not blocked on the operator's remaining FE0 work) adds `optional = true` to `data "coder_external_auth" "github"` at `coder/templates/forge/main.tf:25-27` on the forge-platform PoC branch,
- **Then** `terraform validate` in `coder/templates/forge/` still passes, and the change is committed as a small, separately-reviewable diff — this does **not** replace AC1–AC3; the workspace build and the `forge-sync.sh` clone step still require the actual credential to do anything useful.

## Implementation Notes

Reference proposal §5.4(1), §6.1 (sprint-status key `fe0-s01-github-oauth-app`), evidence **E6.1**. Reference `docs/coder/setup.md` for any existing GitHub OAuth App creation notes in forge-platform (check before assuming none exists — the Azure-era template may already document the callback URL convention). The `CODER_EXTERNAL_AUTH_0_ID` naming and the numeric-suffix pattern (`_0_`) are Coder's own multi-provider external-auth convention — a second provider would use `CODER_EXTERNAL_AUTH_1_*`.

```text
# GitHub → Settings → Developer settings → OAuth Apps → New OAuth App
Application name:            Forge PoC (ct-forge-01)
Homepage URL:                https://forge.bi-services.be
Authorization callback URL:  https://forge.bi-services.be/external-auth/0/callback

# Record (password manager, not a repo):
CODER_EXTERNAL_AUTH_0_ID=github
CODER_EXTERNAL_AUTH_0_TYPE=github
CODER_EXTERNAL_AUTH_0_CLIENT_ID=<from GitHub>
CODER_EXTERNAL_AUTH_0_CLIENT_SECRET=<from GitHub>
```

AC5's Terraform edit is a one-line addition inside the existing `data` block; do not fork `coder/templates/forge/main.tf` (FR-WS-009) to make it — edit on the PoC branch.

## Test Plan

**Pre-state:** No GitHub OAuth App exists for this purpose; `CODER_EXTERNAL_AUTH_0_*` values are unset anywhere.

**Action sequence:**
1. Create the OAuth App (AC1).
2. Record all four values in the credential store (AC2).
3. Authorize the grant against the account holding `tomamourette/agentic-ai` and confirm in the GitHub UI (AC3).
4. (Optionally, in parallel, not blocking) a dev adds `optional = true` at `main.tf:25-27` and runs `terraform validate` (AC5).

**Post-state checks:**
- GitHub UI shows the App under Authorized OAuth Apps for the target account.
- Credential store has all four values retrievable by the operator.
- No credential value appears in any tracked or untracked file under `~/workspace/homelab/`.

**Rollback:** Revoke the OAuth App from GitHub Settings; delete the four recorded values from the credential store. No infrastructure state is touched by this story, so rollback is unconditional and immediate.

## Dependencies

- **Blocked by:** Nothing — this is the first story in the artifact set.
- **Blocks:** FE1-S01 through FE4-S02 per §5.4 (all of FE1–FE4 require both FE0-S01 and FE0-S02 to exist first). Directly consumed by FE2-S04 (`coder.env` wiring) and exercised by FE4-S01/FE4-S02 (gate b).

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| OAuth App created under the wrong GitHub account/org, grant does not cover `tomamourette/agentic-ai` | Low | High — silent clone skip, gates (b)–(e) untestable, hard to diagnose | AC3 makes grant verification an explicit, separate acceptance criterion with a UI check |
| Client secret recorded insecurely (e.g., pasted into a chat log or a repo file) | Low | High — credential leak | AC2 explicitly requires a credential store and a negative `git status`/`git diff` check |
| Callback URL set before `forge.bi-services.be` DNS/TLS exist (FE2 not done yet) | Medium | Low — cosmetic only; GitHub does not validate reachability at App-creation time | AC1 accepts the placeholder URL; correctable later via GitHub's App settings without re-creating the App or losing the Client ID |

## Definition of Done

- [ ] AC1–AC5 all green and evidenced.
- [ ] GitHub OAuth App exists and is authorized against the account holding `tomamourette/agentic-ai`.
- [ ] All four `CODER_EXTERNAL_AUTH_0_*` values recorded in the operator's credential store, confirmed absent from all git working trees.
- [ ] `optional = true` added to `data "coder_external_auth" "github"` on the forge-platform PoC branch (secondary AC5), `terraform validate` passing.
- [ ] Story status updated from `draft` to `done` in this file's frontmatter.
