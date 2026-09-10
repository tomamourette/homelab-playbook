---
type: story
epic: FE4
id: FE4-S01
title: "First workspace create; agentic-ai reaches the workspace via coder external-auth access-token github"
size: S
priority: MUST
owner: dev
blocking: false
fr_refs: [FR-KIT-001]
nfr_refs: [NFR-CAP-002]
adr_refs: [ADR-002]
risk_refs: [R4]
gate_refs: [b, c, d, e, i]
status: draft
date: 2026-09-09
---

# FE4-S01: First workspace create; agentic-ai reaches the workspace via coder external-auth access-token github

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

As **tomamourette**, I want **the first Coder workspace on CT 167 created from the pushed forge
template, with agentic-ai reaching it over `coder external-auth access-token github`**, so that
**the toolkit gates (b)–(e) have something to run against and the "does it port?" question moves
from configuration to evidence**.

## Background and Context

This is the first story of FE4 (Toolkit and acceptance) and depends on the entire chain FE0→FE3
having landed: the GitHub OAuth App (FE0-S01), the Cloudflare token (FE0-S02), CT 167 provisioned
and HA'd (FE1), the Coder control plane with TLS (FE2), and the de-Azured template pushed
(FE3-S06). Per E6.1 of the proposal, `data "coder_external_auth" "github"`
(`coder/templates/forge/main.tf:25-27`) has no `optional = true`, so a workspace build without a
working GitHub grant fails outright. Even assuming the build succeeds, `forge-sync.sh` sources its
clone token from `coder external-auth access-token github` and **silently skips its entire clone
block** when that call returns nothing — meaning agentic-ai never reaches the workspace and
gates (b)–(e) in §5.3 are untestable no matter how clean the rest of the stack is. This story is
therefore the pivot: it is the first point at which the whole preceding chain either produces a
running workspace with a populated `~/workspace/repos/github/` tree, or it does not.

The four `coder_parameter` sizing knobs (`workspace_cpu_shares`, `workspace_memory_mb`,
`workspace_memory_swap_mb`, `workspace_memory_reservation_mb`) are presented on the create-workspace
form at whatever defaults FE3-S01 shipped (12288 MB RAM / 20480 MB swap unless the R4 decision
changed them). **R4 remains open** — this story does not resolve it, it only records whatever
values the operator actually chose at create time, because that record is the input gate (h)
measures in FE4-S02. ADR-002 (privileged workspace accepted for a single operator) is the security
posture this workspace runs under; no revisit is triggered by this story.

## Acceptance Criteria

**AC1 — Workspace build succeeds and the GitHub grant is live.**
- **Given** FE0-S01 through FE3-S06 have all landed and the operator has a `coder` CLI session
  authenticated against `https://forge.bi-services.be` from a tailnet client,
- **When** the operator runs `coder create ct167-first-workspace --template forge -y` and, once the
  workspace is running, `coder ssh ct167-first-workspace -- coder external-auth access-token github`,
- **Then** the `coder create` command exits 0 with no `data.coder_external_auth.github` error, and
  the `access-token` call returns a non-empty token string (not an error, not an empty string).

**AC2 — agentic-ai lands via the token, company-overlay is not double-cloned.**
- **Given** AC1 has passed,
- **When** the operator runs `coder ssh ct167-first-workspace -- 'ls ~/workspace/repos/github/'` and
  `coder ssh ct167-first-workspace -- 'test -d ~/workspace/repos/github/company-overlay; echo $?'`,
- **Then** the first command lists at least the `agentic-ai` directory, and the second prints `1`
  (does not exist) — proving both FR-KIT-001 and the FE3-S02 `local.repo_deny` fix in the same pass.
- **This is where FE3-S02's AC4 is finally verified.** That story could only run an offline
  simulation of `forge-sync.sh`'s `deny()` and left AC4 deliberately unticked. Run the two checks
  **verbatim** and paste their real output back into FE3-S02's Execution record:
  `ls -d ~/workspace/repos/github/company-overlay` must report "No such file or directory", and
  `ls -d ~/workspace/company-overlay/.git` must exist (the dedicated clone, `forge-sync.sh:72-78`).
  Do not tick FE3-S02's AC4 on anything less.

**AC2b — the template's `FORGE_*` configuration actually reached the workspace.**
- **Given** AC1 has passed,
- **When** the operator opens a **Coder web terminal** (not `coder ssh` — the value has to survive
  the same hop `forge-onboard` does, and that script is auto-run from a managed `~/.bashrc` block,
  not from the `startup_script`) and runs
  `printenv FORGE_GITHUB_ORG FORGE_ADO_ORG FORGE_NPM_FEED_HOST FORGE_ONBOARD_TIMEOUT`,
- **Then** it prints `tomamourette`, `none`, an **empty line**, and `300`.
- **Why this is not redundant with a grep of the generated docs:** `forge-onboard.sh` carries
  in-script fallbacks to the previous Azure/Saply deployment's values for exactly these names, so
  the workspace can look plausible while the override never arrived. A missing or Saply value here
  means `coder templates push` ran without `--variables-file coder/templates/forge/poc.tfvars`
  (FE3-S06 AC4) — re-push with it. An empty `FORGE_NPM_FEED_HOST` is the *correct* result and is
  distinguishable from an absent one: `printenv` exits non-zero and prints nothing for a name that
  is unset, but prints a blank line for one that is set-and-empty.
- **Then also** `grep -Eic 'saply|cv-engine|matching-(frontend|service|infrastructure)'
  ~/workspace/CLAUDE.md ~/workspace/repos/INDEX.md ~/.codex/AGENTS.md` returns `0` for all three.

**AC3 — Sizing knobs actually chosen are recorded verbatim (R4 evidence, not resolution).**
- **Given** the create-workspace form presented the four `coder_parameter` fields at `coder create`
  time,
- **When** the operator notes the values actually submitted (default or manually overridden),
- **Then** all four values are written into this story's Test Plan §Post-state checks exactly as
  chosen — this AC does not decide R4, it only produces the input gate (h) will measure in FE4-S02.

**AC4 — code-server is reachable over the browser-trusted certificate.**
- **Given** the workspace agent reports `ready`,
- **When** the operator, from a tailnet client not on the LAN, opens the `coder_app "code_server"`
  URL in a browser,
- **Then** the page loads with no certificate warning (full gate-(a) verification happens in
  FE4-S02; this AC only confirms the URL resolves and serves before that run).

**AC5 — Wall-clock create-to-reachable baseline recorded (gate i).**
- **Given** the operator notes the timestamp `T0` at `coder create` invocation and `T1` at the
  moment code-server first responds to a browser request,
- **When** the operator computes `T1 − T0`,
- **Then** that duration is written into this story's Test Plan as the gate-(i) baseline, whatever
  the number is — no target time is asserted.

**AC6 — Toolkit basics present before the full gate run.**
- **Given** the workspace is running,
- **When** the operator runs `coder ssh ct167-first-workspace -- 'cat ~/.forge-toolchain'` and
  `coder ssh ct167-first-workspace -- 'claude --version'`,
- **Then** `~/.forge-toolchain` exists and lists at least `claude`, `codex`, `gh`, `terraform`, and
  `claude --version` returns a version string — confirming the toolkit surface is present ahead of
  the exhaustive FE4-S02 run.

## Implementation Notes

Reference `architecture.md`'s `/opt/coder/secrets` → `/run/secrets` → `~/.config/forge/*.env` seam
(must not be broken by this story — it is read-only here), ADR-002 (privileged workspace, single
operator), and E6.1 of the proposal for the GitHub grant chain. The runbook
`homelab-playbook/wiki/runbooks/create-project-container.md` does not cover workspace create — this
is Coder-native, not Terraform/Ansible — so no runbook step applies beyond CT 167 already existing.

```bash
# From a tailnet client, authenticated coder CLI session:
coder create ct167-first-workspace --template forge -y

# Confirm GitHub grant is live inside the workspace:
coder ssh ct167-first-workspace -- 'coder external-auth access-token github'

# Confirm agentic-ai landed, company-overlay did not double-clone:
coder ssh ct167-first-workspace -- 'ls ~/workspace/repos/github/'
coder ssh ct167-first-workspace -- 'test -d ~/workspace/repos/github/company-overlay; echo $?'

# FE3-S02 AC4, verbatim — paste the real output back into that story before ticking its AC4:
coder ssh ct167-first-workspace -- 'ls -d ~/workspace/repos/github/company-overlay'  # must fail
coder ssh ct167-first-workspace -- 'ls -d ~/workspace/company-overlay/.git'          # must exist

# AC2b — in a Coder WEB TERMINAL (not coder ssh), confirm the template's config reached the shell
# that auto-runs forge-onboard:
printenv FORGE_GITHUB_ORG FORGE_ADO_ORG FORGE_NPM_FEED_HOST FORGE_ONBOARD_TIMEOUT
grep -Eic 'saply|cv-engine|matching-(frontend|service|infrastructure)' \
  ~/workspace/CLAUDE.md ~/workspace/repos/INDEX.md ~/.codex/AGENTS.md

# Confirm toolkit basics:
coder ssh ct167-first-workspace -- 'cat ~/.forge-toolchain'
coder ssh ct167-first-workspace -- 'claude --version'
```

## Test Plan

**Pre-state:**
- FE0-S01, FE0-S02 (operator prerequisites) exist and are recorded.
- FE1 (CT 167 provisioned, HA'd, dev-host applied) is complete.
- FE2 (Coder + Postgres + Caddy TLS) is complete; `https://forge.bi-services.be` is reachable.
- FE3-S06 (template built and pushed) is complete; `coder templates list` shows `forge`.

**Action sequence:**
1. From a tailnet client not on the LAN, run `coder create ct167-first-workspace --template forge -y`; note `T0`.
2. Record the four sizing values presented/chosen on the create form.
3. Wait for the workspace agent to report `ready`; note `T1` when code-server first responds.
4. Run the AC1–AC2 and AC6 verification commands via `coder ssh`.
5. Open the code-server URL in a browser from the tailnet client; confirm no cert warning (AC4).
6. Record `T1 − T0` as the gate-(i) baseline (AC5).

**Post-state checks:**
- `coder external-auth access-token github` returns a token.
- `~/workspace/repos/github/agentic-ai` exists; `~/workspace/repos/github/company-overlay` does not,
  and `~/workspace/company-overlay/.git` does — the two halves of FE3-S02's deferred AC4.
- In a Coder web terminal, `printenv FORGE_GITHUB_ORG FORGE_ADO_ORG FORGE_NPM_FEED_HOST
  FORGE_ONBOARD_TIMEOUT` prints `tomamourette` / `none` / blank / `300` (AC2b).
- Sizing values recorded: `workspace_cpu_shares=__`, `workspace_memory_mb=__`,
  `workspace_memory_swap_mb=__`, `workspace_memory_reservation_mb=__` (fill in at execution time).
- Gate-(i) baseline recorded: `T1 − T0 = __`.

**Rollback:**
- `coder delete ct167-first-workspace -y` removes the workspace; CT 167 itself, the control plane,
  and the template are untouched. Re-running `coder create` recovers this story's state in full.

## Dependencies

- **Blocked by:** FE0-S01, FE0-S02 (operator prerequisites), FE1-S01..S05, FE2-S01..S06,
  FE3-S01..S06 (the entire preceding chain must be `done`).
- **Blocks:** FE4-S02 (the exhaustive gate run needs a running workspace to test against).

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| R4 — default sizing (12288 MB RAM / 20480 MB swap) OOMs the workspace on an 8 GB CT | High | Medium | Operator manually overrides the `coder_parameter` values on the create form per the FE1-S01 banner; AC3 records whatever was chosen so the OOM (or its absence) is explainable in FE4-S02 gate (h) |
| GitHub grant technically present but scoped to the wrong org/user | Low | High — gates (b)–(e) untestable | AC1's `access-token` call is a live check, not a config read; a scope mismatch surfaces immediately as an empty/error response |
| `forge-sync.sh` clone block silently skips without an obvious error | Medium | High — false-positive "workspace is fine" | AC2 explicitly checks for the `agentic-ai` directory's presence, not just the absence of an error |

## Definition of Done

- [ ] AC1–AC6 all green and evidenced with command output pasted into this story.
- [ ] Sizing values actually used are recorded (AC3).
- [ ] Gate-(i) baseline recorded (AC5).
- [ ] Story status updated from `draft` to `done` in this file's frontmatter.
