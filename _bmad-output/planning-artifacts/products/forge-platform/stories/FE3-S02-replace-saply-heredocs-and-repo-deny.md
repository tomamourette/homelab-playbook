---
type: story
epic: FE3
id: FE3-S02
title: "Replace the two Saply-specific heredocs and add company-overlay to local.repo_deny"
size: S
priority: MUST
owner: dev
blocking: false
fr_refs: [FR-WS-003, FR-WS-004]
nfr_refs: []
adr_refs: []
risk_refs: []
gate_refs: [b]
status: done
date: 2026-09-09
---

# FE3-S02: Replace the two Saply-specific heredocs and add company-overlay to local.repo_deny

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

As **tomamourette**, I want **the two Saply-specific heredocs in `coder/templates/forge/main.tf:171-270` replaced with generic equivalents, and `company-overlay` added to `local.repo_deny`**, so that **a workspace's onboarding documents don't hardcode Saply's product catalog (matching-frontend, matching-service, CV-engine, etc.) as if they were universal, and `company-overlay` — which is currently absent from the deny list — stops being cloned twice into two different paths**.

## Background and Context

`main.tf:171-270` writes two files at workspace boot via inline heredocs inside the `startup_script`: `$HOME/workspace/CLAUDE.md` (lines ~176-233, the "Saply Forge Workspace" orientation document) and `$HOME/workspace/repos/INDEX.md` (lines ~240-275, the "Saply Repos — Index"). Both are full of Saply-specific product knowledge that has no place in a generalized template: `matching-frontend`/`matching-service`/`matching-infrastructure` repo descriptions, the ADO project name `CV-engine`, the org name `Saply-ai` baked directly into prose, and links into `knowledge-base/docs/matching-frontend/` that assume that specific knowledge base's structure. None of this is wrong for Saply's own use of forge-platform — it is wrong as the **default** a de-Azured, company-agnostic template should ship. FR-WS-003 requires generic equivalents: an orientation document that explains the *mechanism* (repos/github, repos/ado, agentic-ai, knowledge-base, forge-onboard) without asserting specific product names as if they were structural.

The `company-overlay` bug is smaller in scope but concrete and independently verifiable: `local.repo_deny = ["agentic-ai", "knowledge-base"]` (`main.tf:110`) is meant to list every repo that `forge-sync.sh` clones by name into its own dedicated path (`~/workspace/agentic-ai`, `~/workspace/knowledge-base`) rather than into `~/workspace/repos/github/<name>`, so the generic per-org loop in `forge-sync.sh:46-54` should skip them. `forge-sync.sh:73-78` clones `company-overlay` into `~/workspace/company-overlay` exactly the same way — but `company-overlay` is **absent** from `repo_deny`, so the org-wide `gh repo list` loop at `forge-sync.sh:46-54` also clones it into `~/workspace/repos/github/company-overlay`, giving every workspace two independent clones of the same repo, out of sync with each other from the moment either one receives a commit. Acceptance gate (b) tests exactly this: `~/workspace/repos/github/company-overlay` must **not** exist after this fix, while the dedicated `~/workspace/company-overlay` clone (unaffected by this story) continues to work.

## Acceptance Criteria

**AC1 — CLAUDE.md heredoc genericized.**
- **Given** `main.tf`'s `startup_script` heredoc writing `$HOME/workspace/CLAUDE.md`,
- **When** the operator inspects the replaced content,
- **Then** it describes the structural layout (`repos/github/`, `repos/ado/`, `agentic-ai/`, `knowledge-base/`, `forge-onboard`) without naming any Saply-specific repo (`matching-frontend`, `matching-service`, `matching-infrastructure`) or company-specific term (`CV-engine`, `saply.ai` email domain example) as if it were part of the template's structure.

**AC2 — repos/INDEX.md heredoc genericized.**
- **Given** the second heredoc writing `$HOME/workspace/repos/INDEX.md`,
- **When** the operator inspects the replaced content,
- **Then** the "GitHub (repos/github/)" and "ADO (repos/ado/)" tables describe the mechanism (auto-cloned from `${local.github_org}`/`${local.ado_org}`, linked to `knowledge-base`) generically, with no hardcoded Saply repo names or CV-engine project references remaining as literal text in the template.

**AC3 — `company-overlay` added to the deny list.**
- **Given** `local.repo_deny` at `main.tf:110`,
- **When** the operator runs `grep -n 'repo_deny' coder/templates/forge/main.tf`,
- **Then** the list reads `["agentic-ai", "knowledge-base", "company-overlay"]` (order doesn't matter, presence does).

**AC4 — Double-clone eliminated (feeds gate b).**
- **Given** AC3 has passed and a workspace boots with a valid GitHub token,
- **When** `forge-sync.sh` completes its boot run,
- **Then** `~/workspace/repos/github/company-overlay` does **not** exist, while `~/workspace/company-overlay/.git` **does** exist (the dedicated clone at `forge-sync.sh:73-78` is unaffected — only the accidental second copy via the generic org loop is eliminated).

**AC5 — No behavior change to the sync mechanism itself.**
- **Given** AC3–AC4 have passed,
- **When** the operator diffs `forge-sync.sh` before and after this story,
- **Then** the diff is empty — this story's fix is entirely in `main.tf`'s `local.repo_deny` list (the value passed into `FORGE_SYNC_DENY`, `main.tf:302`), not in the script's own default (`forge-sync.sh:8`, which already includes `company-overlay` in its own fallback default and was simply never receiving it from the template's `FORGE_SYNC_DENY` override).

## Implementation Notes

Reference E1 (not directly, but establishes this file's general character), §4.2 FE3-S02, FR-WS-003, FR-WS-004. Exact lines to touch: `main.tf:110` (`repo_deny`), `main.tf:171-233` (CLAUDE.md heredoc), `main.tf:240-275` (repos/INDEX.md heredoc). Do not touch `forge-sync.sh` — its own default `DENY` fallback (`forge-sync.sh:8`) already lists `company-overlay`; the bug is purely that `main.tf` overrides that default via `FORGE_SYNC_DENY="${join(" ", local.repo_deny)}"` (`main.tf:302`) with a list that omits it.

```hcl
# main.tf:110 — before
repo_deny = ["agentic-ai", "knowledge-base"]

# after
repo_deny = ["agentic-ai", "knowledge-base", "company-overlay"]
```

```bash
# AC verification (post workspace boot, inside the workspace)
grep -n 'repo_deny' coder/templates/forge/main.tf
ls -d ~/workspace/repos/github/company-overlay 2>&1   # expect "No such file or directory"
ls -d ~/workspace/company-overlay/.git 2>&1            # expect it to exist
```

## Test Plan

**Pre-state:** `local.repo_deny = ["agentic-ai", "knowledge-base"]`; CLAUDE.md and repos/INDEX.md heredocs contain Saply-specific product/org content; a prior workspace (if any existed) would show `company-overlay` cloned into both paths.

**Action sequence:**
1. Rewrite the two heredocs to generic content (AC1, AC2).
2. Add `company-overlay` to `repo_deny` (AC3).
3. `terraform validate` in `coder/templates/forge/`.
4. Defer live verification of AC4/AC5 to FE3-S06/FE4-S01 (this story cannot test a real workspace boot until the template is pushed and a workspace is created) — record here that AC4/AC5 verification is deferred and cross-reference FE4-S01's evidence when it lands.

### Execution record — 2026-09-09

Executed source-only against the working tree of `repos/forge-platform` (nothing committed, nothing
pushed). Line numbers in this story are stale: FE3-S01 and a concurrent FE3-S03 run had already
landed uncommitted edits in the same file, so `repo_deny` is at `main.tf:164` (not 110), the
CLAUDE.md heredoc markers at `main.tf:264`/`326` (not 171/233) and the INDEX.md markers at
`main.tf:333`/`360` (not 240/275). `FORGE_SYNC_DENY` is built at TWO call sites, `main.tf:387`
(boot) and `main.tf:565` (hourly cron), not the single `main.tf:302` this story cites; both read
`join(" ", local.repo_deny)`, so the one-line change covers both.

**Interaction with FE3-S03 (important).** By the time this story ran, FE3-S03 had already lifted
the two Saply product catalogues out of the heredoc bodies into `var.forge_repo_catalogue`
(`variables.tf`), whose default reproduces the Saply documents byte-for-byte. That satisfied AC1's
"no company literal in the heredoc body" grep on its own, but left the bodies describing *nothing*
about the mechanism and left AC2's required `${local.github_org}` / `${local.ado_org}`
interpolation absent entirely. This story therefore did not undo that indirection; it added the
structural, company-agnostic mechanism prose around it — a new `## How repos get here` section in
CLAUDE.md and a new `## How the sync works` section in repos/INDEX.md — plus the `company-overlay/`
entry in the structure tree, and the AC2 org interpolation. Company-specific data stays data
(`var.forge_repo_catalogue`); the mechanism is now template text.

| AC | Result | Evidence |
|---|---|---|
| AC1 | **PASS on substance**, verify_command flawed | Heredoc body has 0 hits for the company-literal regex; marker count is exactly 2; the `AGENTS.md` symlink line is byte-for-byte unchanged. The command's own final sub-check cannot pass on this host — see the note below. |
| AC2 | **PASS** | `AC2 PASS (generic + both orgs interpolated)` |
| AC3 | **PASS** | `164:  repo_deny = ["agentic-ai", "knowledge-base", "company-overlay"]`, all three `present:` |
| AC4 | **deferred**; offline proxy PASS | `rendered FORGE_SYNC_DENY = 'agentic-ai knowledge-base company-overlay'` → company-overlay `skipped by org loop`, forge-platform still `cloned into repos/github/forge-platform`. `AC4-sim PASS ... live check deferred to FE4-S01`. Pre-change the same simulation printed `AC4-sim FAIL (company-overlay would be double-cloned)`. |
| AC5 | **PASS** | `git diff --exit-code -- coder/templates/forge/forge-sync.sh` exit 0, empty. |
| AC6 | **PASS** | `terraform fmt -check` exit 0; `terraform validate` exit 0, `Success! The configuration is valid`, only the three pre-existing `dir` deprecation warnings on `coder_agent.main`. |

The rendered value that actually reaches the script was confirmed with `terraform console`:
`join(" ", local.repo_deny)` → `"agentic-ai knowledge-base company-overlay"`, `local.github_org` →
`"Saply-ai"`, `local.ado_org` → `"saplyai"`. Both heredocs were rendered offline with the default
variable values and contain no unresolved `${...}`.

**AC1's verify_command is broken independently of this change.** Its last sub-check is
`grep -q 'ln -sf CLAUDE.md "$HOME/workspace/AGENTS.md"'`. `grep` on this host is **ugrep 7.8.4**,
which treats a mid-pattern `$` as an anchor, so that pattern matches nothing even against a
byte-identical line (`grep -Fc` → 1, `grep -c` → 0, proven on a one-line fixture). The command
therefore printed `AC1 FAIL (heredoc markers or AGENTS.md symlink damaged)` **before** any edit was
made, and prints it after. With the sub-check run as `grep -qF`, the unmodified command prints
`AC1 PASS (no company literals; markers + symlink intact)`. Fix the AC to use `grep -qF` (or
`\$HOME`); do not "repair" main.tf for it.

**Deferred to FE4-S01:** AC4's live checks — `ls -d ~/workspace/repos/github/company-overlay` must
report *No such file or directory*, and `ls -d ~/workspace/company-overlay/.git` must exist. The
offline `deny()` simulation above proves the deny list is correct; it does not prove a real boot
produced the right filesystem. Do not tick AC4 on the strength of the simulation.

**AC1's `saply.ai` clause — resolved, no action needed.** AC1 forbids "the `saply.ai` email domain
example". That string never existed in `main.tf`; its only occurrence in the template directory was
`coder/templates/forge/forge-onboard.sh:57` (`info "git config --global user.email
'you@saply.ai'"`), a file this story's Implementation Notes do not authorise touching. It has since
been removed by FE3-S01's forge-onboard.sh rewrite: `grep -rn 'saply\.ai' coder/templates/forge/`
now returns no matches at all. The clause is satisfied repo-wide, not merely vacuously for main.tf,
and nothing is carried forward.

### Verifier round 2 — findings and fixes, 2026-09-09

An adversarial verification pass scored AC1 and AC2 **fail** on substance (the mechanical greps
passed; the newly-authored prose was factually wrong) and scored four generalisation lenses fail.
All are fixed below. AC4 was scored *unverified* rather than fail — no defect, simply not provable
without a live boot; it stays deferred to FE4-S01.

| Finding | Fix | Where |
|---|---|---|
| **AC1 fail** — the new prose claimed ADO repos clone to `repos/ado/<project>/<name>`. The clone is FLAT: `forge-sync.sh:94` is `d="$HOME/workspace/repos/ado/$(basename "$url")"`; `$proj`/`$pe` (lines 90-91) only build the REST URL, never a path. A regression: HEAD never claimed a `<project>` level, and `docs/coder/workspaces.md:42` already documented the flat form. This document is rewritten into `~/workspace/CLAUDE.md` on every boot and symlinked to `AGENTS.md`, so it would have sent agents to a directory that never exists. | Corrected to `repos/ado/<name>` and made the flat layout explicit, including the genuine collision risk when two ADO projects share a repo name. | `main.tf:290-294` |
| **AC2 fail** — same false `repos/ado/<project>/<repo>` claim in the INDEX.md heredoc. Also overstated the GitHub half: `forge-sync.sh:47` is `gh repo list "$GITHUB_ORG" --limit 200`, not "every repository". | Corrected to `repos/ado/<repo>` with the same flat-layout note; the GitHub bullet now says "the first 200". | `main.tf:346-350` |
| **GEN-3 fail** — the generated documents are only neutral if a deployment overrides **all eight** `forge_*` knobs. Rendered against the repo's own documented example (`docs/coder/setup.md`), which omitted `forge_ado_org` and `forge_repo_catalogue`, `~/workspace/CLAUDE.md` still said `dev.azure.com/saplyai`, `matching-*`, `CV-engine`. AC1/AC2 passed only because the literals had moved into `var.forge_repo_catalogue`'s default, which those greps do not inspect. | (a) Added a real `coder/templates/forge/poc.tfvars` carrying all eight knobs for CT 167, so FE3-S06 has something to push with. (b) Completed the `setup.md` example with `forge_ado_org` + `forge_repo_catalogue` and stated that the eight knobs are one unit. (c) Added the render-level gate below so a future relocation cannot pass. | new `coder/templates/forge/poc.tfvars`; `docs/coder/setup.md` |
| **GEN-4 / GEN-5 fail** — with every `FORGE_*` var unset, `forge-onboard.sh` **blocked indefinitely** on `Log in to Azure CLI now?` (verifier's run died at its own 60s kill, exit 124), because the gate is `${FORGE_ENABLE_AZURE_CLI-true}` — unset means enabled — and `workspace/Dockerfile:22` installs the Azure CLI unconditionally, so `command -v az` succeeds with no tenant. The same run printed another company's npm-feed URL and told the developer to ask a "Saply-ai org owner" for access. | Two layers. Primary: `poc.tfvars` sets `forge_enable_azure_cli`/`forge_enable_azure_devops` false, `forge_npm_feed_host`/`forge_codex_extra_context` empty — the mechanism was already correct, only the PoC's default position was wrong. Backstop: `ask_login` now reads with `read -t "$ONBOARD_TIMEOUT"` (default 300s, `FORGE_ONBOARD_TIMEOUT=0` restores unbounded), so a missing credential can never hang onboarding regardless of gate state. Timing out is equivalent to pressing Enter, which every step already treats as a safe skip. Flipping the gate defaults to false was rejected: it would break the run's backwards-compatibility rule for the existing Azure deployment. **(The backstop's DEFAULT was superseded in round 3 — it is now 0/unbounded and opt-in, because a 300s default was itself a behaviour change to the existing Azure deployment. See *Verifier round 3* below.)** | `forge-onboard.sh:31-58`; `poc.tfvars` |
| **GEN-6 fail** — `forge-sync.sh:9-10` use `:-`, so `forge_ado_org = ""` (the natural way to write "no Azure DevOps") silently retargets `dev.azure.com/saplyai` rather than meaning "none". | The shell fix is out of scope — AC5 requires `forge-sync.sh` byte-identical — so the trap is closed at the **template boundary** instead: `variable "forge_ado_org"` and `variable "forge_github_org"` now carry `validation` blocks rejecting an empty/whitespace value, with an error message naming the `:-` fallback and pointing at the placeholder pattern. Backwards-compatible (both defaults are non-empty). **Follow-up still owed:** change `:-` to `-` on `forge-sync.sh:9-10` and guard the ADO block with `[ -n "$ADO_ORG" ]`. | `variables.tf:17-52`; `setup.md` warning |

**Re-run evidence (round 2).** All six ACs green: `AC1 PASS`, `AC2 PASS`, `AC3 PASS`, `AC4-sim PASS`
(live check still deferred), `AC5 PASS` (empty diff), `AC6 PASS` (`fmt -check` exit 0, `validate`
exit 0 with only the three pre-existing `dir` deprecations). `services/hermes` → `156 passed`.

Both generated documents were rendered offline (variables + locals + the extracted heredoc bodies
in a throwaway module, `terraform apply` + `terraform output -raw`):

- **With `poc.tfvars`:** 0 hits for `saply|cv-engine|matching-*|word-plugin|gdoc-plugin`, in
  **both** documents, and no unresolved `${...}`. Renders `# Homelab Forge Workspace`,
  `tomamourette GitHub repos`, `repos/ado/ — not used by this deployment`.
- **With defaults:** the Saply catalogue still renders (12 literal hits per document), i.e. the
  existing Azure deployment is unchanged apart from the two corrected ADO paths.
- `terraform plan -var 'forge_ado_org='` is now **rejected** with the explanatory error.

`forge-onboard.sh` under a pty with stdin held open and nobody answering:

- Defaults, `az` installed but not logged in → `Azure CLI: no answer in 3s, skipped`, onboarding
  **completes**, `EXIT=0`. Previously this hung until the harness killed it.
- `poc.tfvars` env → `Azure DevOps: not configured for this deployment, skipped`,
  `private npm feed: not configured, skipped`, `Azure CLI: disabled for this deployment, skipped`,
  **0 interactive prompts**, 0 company literals on the terminal or in the generated `~/.codex/`
  files, and `# Homelab Forge — Codex global context` / `repos/github/ — tomamourette GitHub repos`.
- Answer paths unregressed: `y` → attempts `az login --use-device-code`; `q` → `skipping all
  remaining steps`; Enter → `Azure CLI: skipped`; `FORGE_ONBOARD_TIMEOUT=0` → unbounded read.

**New AC — render-level neutrality gate (GEN-3's requested addition).** The existing AC1/AC2 greps
inspect the heredoc *body*, so relocating a company literal into a variable default passes them
while the rendered document still names the company. This checks the **output**:

```
# AC-RENDER: the generated documents must name no company on the PoC configuration.
# Renders both heredocs offline against coder/templates/forge/poc.tfvars.
cd /home/developer/workspace/homelab/repos/forge-platform/coder/templates/forge && \
R=$(mktemp -d) && cp variables.tf poc.tfvars "$R"/ && \
awk "/<<'WORKSPACE_CLAUDE_EOF'/{f=1;next} /^WORKSPACE_CLAUDE_EOF\$/{f=0} f" main.tf > "$R/c.txt" && \
awk "/<<'REPOS_INDEX_EOF'/{f=1;next} /^REPOS_INDEX_EOF\$/{f=0} f"   main.tf > "$R/i.txt" && \
{ printf 'locals {\n  github_org = var.forge_github_org\n  ado_org = var.forge_ado_org\n  a = <<A_EOT\n'; \
  cat "$R/c.txt"; printf 'A_EOT\n  b = <<B_EOT\n'; cat "$R/i.txt"; printf 'B_EOT\n}\n'; \
  printf 'output "a" { value = local.a }\noutput "b" { value = local.b }\n'; } > "$R/render.tf" && \
(cd "$R" && terraform init -no-color >/dev/null && \
 terraform apply -auto-approve -no-color -var-file=poc.tfvars >/dev/null && \
 terraform output -raw a > out_a && terraform output -raw b > out_b && \
 if /usr/bin/grep -Eiq 'saply|cv-engine|matching-(frontend|service|infrastructure)|word-plugin|gdoc-plugin' out_a out_b; \
 then echo 'AC-RENDER FAIL (company literal in a RENDERED document)'; \
 else echo 'AC-RENDER PASS (both rendered documents company-neutral)'; fi)
```

Result: `AC-RENDER PASS (both rendered documents company-neutral)`. Negative control — the same
command with `-var-file=poc.tfvars` removed prints `AC-RENDER FAIL`, which proves the grep has
teeth and is not a vacuous pass. That FAIL is *correct*: on the default (Azure) configuration the
documents are supposed to name Saply. This gate asserts neutrality **on the PoC configuration**,
which is the thing GEN-3 found broken.

> **Note on `grep` for anyone re-running these.** `grep` on this host is a shell function wrapping
> **ugrep 7.8.4**, which treats a mid-pattern `$` as an anchor. Every AC in this epic that greps for
> a literal `$` (AC1's `"$HOME/workspace/AGENTS.md"` sub-check) reports a false FAIL under it. Use
> `/usr/bin/grep` (GNU grep 3.8) or `grep -F`. With the real binary the unmodified AC1 command
> prints `AC1 PASS (no company literals; markers + symlink intact)` — confirmed this round.

### Verifier round 3 — findings and fixes, 2026-09-09

Round 3 scored **two fail** and **three unverified**. Both fails are fixed below. Of the three
unverified, two are the same AC4 deferral (no defect — the live check needs a workspace boot) and
one was a delivery question the verifier could not settle offline; that one is now closed by making
the answer not matter.

| Finding | Verdict | Fix | Where |
|---|---|---|---|
| **AC-COMPAT-ONBOARD-TIMEOUT** — round 2's `ONBOARD_TIMEOUT="${FORGE_ONBOARD_TIMEOUT-300}"` made the backstop the DEFAULT, so every `ask_login` prompt in the existing Azure deployment gained a 300s ceiling where HEAD (`read -r ans </dev/tty`) waited indefinitely, and a developer answering after it expired would have that keystroke land in their shell. A behaviour change to a shared file, outside the operator's decided sizing/image exceptions. The verifier was right and round 2 had identified the risk itself without acting on it. | **fail** | Default inverted so compat is the default: `ONBOARD_TIMEOUT="${FORGE_ONBOARD_TIMEOUT-0}"`, and 0 already selects the unbounded branch. The backstop is now **opt-in**: new `var.forge_onboard_timeout` (number, default **0**, validated non-negative integer) is published as `FORGE_ONBOARD_TIMEOUT` from both env mechanisms, and `poc.tfvars` sets **300** for the unattended PoC. The Azure deployment gets HEAD's behaviour; the PoC gets the backstop. | `forge-onboard.sh:38-47`; `variables.tf` (new `forge_onboard_timeout`); `main.tf` (both env blocks); `poc.tfvars`; `setup.md` |
| **AC-COMPAT-SCRIPT-FALLBACKS** — `FORGE_NPM_FEED_HOST` lost its in-script Saply fallback (`${FORGE_NPM_FEED_HOST-}`) and `FORGE_CODEX_EXTRA_CONTEXT` never had one, so those two steps' backwards-compatibility came to depend on a delivery path HEAD did not use: HEAD's agent env was only `{ CODER_WORKSPACE_ID }`, and `forge-onboard` is not run by the `startup_script` — it is auto-run from a managed `~/.bashrc` block. If the agent env did not reach that shell, the Azure deployment would silently lose its private npm feed auth and its Codex context appendix. | **unverified** | Closed on **both** axes so the delivery question no longer decides the outcome. (1) The in-script fallbacks are restored: `${FORGE_NPM_FEED_HOST-pkgs.dev.azure.com/saplyai/CV-engine/_packaging/WordUI}`, and an unset `FORGE_CODEX_EXTRA_CONTEXT` now falls back to the same eight Azure fact lines that `var.forge_codex_extra_context`'s default carries (verified byte-identical). Both use `-`/`+set`, never `:-`, so an explicit `""` still wins. (2) All seven `FORGE_*` names are additionally published on `docker_container.env` beside `FORGE_GIT_NAME`, i.e. on the container process, inherited unconditionally by every descendant. | `forge-onboard.sh:114-124, 337-366`; `main.tf` `docker_container.env` |
| **GEN-POC-TFVARS** — `docs/coder/setup.md:222` asserted "A working file for the homelab PoC is **checked in** at `coder/templates/forge/poc.tfvars`". It is not: `git ls-files --error-unmatch` fails, `git status` shows `?? coder/templates/forge/poc.tfvars`, and it is not ignored. Everything company-neutral about the PoC is conditional on that file being passed with `--variables-file`, so setup.md's own claim could lead FE3-S06 to omit the flag and Saply-brand the PoC. Same defect class as round 1: prose asserting something the repo does not do. | **fail** | The claim is corrected to what is true — present in the working tree, **not committed**, commit it with the FE3 series before FE3-S06, verify with `git ls-files` rather than assuming. (The run's hard rules forbid committing, so the file stays untracked and the doc now says so.) FE3-S06's AC4 is rewritten to carry `--variables-file` explicitly and to state that its omission does not fail, and a new **AC4b** post-push assertion greps the rendered documents and `printenv`s the `FORGE_*` values so an omitted flag fails loudly. | `docs/coder/setup.md:222-229`; `FE3-S06-build-image-and-template-push.md` (AC4, new AC4b, test plan step 6, DoD) |
| **AC4** (correctness lens and generalisation lens, same finding) | **unverified** | No fix owed — the verifier confirmed there is no defect, only that an offline simulation cannot prove a boot. Stays unticked. FE4-S01 owes the two checks verbatim: `ls -d ~/workspace/repos/github/company-overlay` must report "No such file or directory", and `ls -d ~/workspace/company-overlay/.git` must exist. | — |

**A defect found while fixing AC-COMPAT-SCRIPT-FALLBACKS, which changes why the container env
matters.** `terraform plan -var-file=poc.tfvars` renders `coder_agent.main.env` as
`"FORGE_NPM_FEED_HOST" = null` and `"FORGE_CODEX_EXTRA_CONTEXT" = null` for `forge_npm_feed_host =
""` — the Coder provider does not represent an empty string as an empty string in that map, so the
key may not be exported at all. A restored in-script fallback reads an unexported name as UNSET and
answers with the Saply value, which would have turned round 3's compat fix into a PoC regression:
the developer would be shown another company's feed URL despite `poc.tfvars` explicitly disabling
it. `docker_container.env` renders the same value as the string `FORGE_NPM_FEED_HOST=` — set but
empty — which the `-` form honours as "off". So the container-level publication is not
belt-and-braces here; for the explicit-empty case it is the only correct carrier. Evidence:

```
$ terraform console -var-file=poc.tfvars   # what docker_container.env renders
["FORGE_NPM_FEED_HOST=","FORGE_ONBOARD_TIMEOUT=300","FORGE_ENABLE_AZURE_CLI=false"]
$ terraform console                        # defaults, i.e. the Azure deployment
["FORGE_NPM_FEED_HOST=pkgs.dev.azure.com/saplyai/CV-engine/_packaging/WordUI","FORGE_ONBOARD_TIMEOUT=0"]
```

**Re-run evidence (round 3).**

*Timeout compat, from the real code.* The assignment and the whole `ask_login` body were extracted
out of the working-tree file (`grep -m1 '^ONBOARD_TIMEOUT='` and an `awk` range) and `eval`'d, so
the harness runs the shipped code rather than a paraphrase:

```
### FORGE_ONBOARD_TIMEOUT unset (existing Azure deployment):
resolved ONBOARD_TIMEOUT=[0]
BRANCH: unbounded -> read (blocks forever, = pre-change behaviour)
### FORGE_ONBOARD_TIMEOUT=300 (poc.tfvars):
resolved ONBOARD_TIMEOUT=[300]
BRANCH: bounded   -> read -t 300 (auto-skip)
```

HEAD, for comparison: `37:  read -r ans </dev/tty 2>/dev/null || ans=""` — no timeout. The unset
case now matches it.

*End-to-end under a pty, `az` stubbed as installed-but-not-logged-in (mirroring
`workspace/Dockerfile`, which installs the CLI unconditionally):*

- **Test A — every `FORGE_*` unset, nobody answers.** Blocks at `Log in to GitHub CLI now?` until
  the harness's own 20s kill: `EXIT=124 wall=22s`. This is the **desired** result — it is exactly
  HEAD's behaviour, and it is what round 2 had accidentally changed.
- **Test B — `poc.tfvars` env as `docker_container.env` delivers it** (`FORGE_NPM_FEED_HOST=` and
  `FORGE_CODEX_EXTRA_CONTEXT=` set-but-empty, both gates false, timeout shortened to 3s to make the
  branch observable): `EXIT=0`. Prints `Azure DevOps: not configured for this deployment, skipped`,
  `private npm feed: not configured, skipped`, `Azure CLI: disabled for this deployment, skipped`,
  and every unanswered prompt reports `no answer in 3s, skipped`. Zero company literals on the
  terminal and zero in the generated `~/.codex/` files; the generated `~/.codex/AGENTS.md` ends at
  "read them from the knowledge base" with **no** Azure appendix — i.e. explicit-empty is honoured.
- **Test C — the delivery gap itself: every `FORGE_*` unset, developer presses Enter.** `EXIT=0`,
  and the two things the verifier said could be silently lost are both back:
  `! pkgs.dev.azure.com/saplyai/CV-engine/_packaging/WordUI npm feed: skipped, no Azure DevOps
  token`, and `~/.codex/AGENTS.md` carries the full `## Deployment specifics` block. `diff` of those
  eight fact lines against `var.forge_codex_extra_context`'s default: **identical**.
- **Answer paths unregressed:** `q` → `skipping all remaining steps`, `EXIT=0`; Enter on GitHub then
  `y` on Azure CLI → `az stub: login login --use-device-code`, `EXIT=0`.

*Terraform.* `fmt -check` exit 0; `init -backend=false` ok; `validate` exit 0 (only the three
pre-existing `dir` deprecation warnings on `coder_agent.main`, main.tf:219). `plan -var-file=poc.tfvars`
succeeds. `plan -var 'forge_onboard_timeout=-5'` is rejected by the new validation;
`plan -var 'forge_ado_org='` still rejected by round 2's. Rendered env values:

```
DEFAULTS (Azure):  FORGE_ENABLE_AZURE_CLI="true"  FORGE_GITHUB_ORG="Saply-ai"
                   FORGE_NPM_FEED_HOST="pkgs.dev.azure.com/saplyai/CV-engine/_packaging/WordUI"
                   FORGE_ONBOARD_TIMEOUT="0"
poc.tfvars:        FORGE_ENABLE_AZURE_CLI="false" FORGE_GITHUB_ORG="tomamourette"
                   FORGE_NPM_FEED_HOST=null (agent map) / "FORGE_NPM_FEED_HOST=" (container env)
                   FORGE_ONBOARD_TIMEOUT="300"
```

*Full AC sweep, re-run with `/usr/bin/grep`:* `AC1 PASS`, `AC2 PASS`, `AC3 PASS`, `AC4-sim PASS`
(live check still deferred), `AC5 PASS` (empty diff), `AC6 PASS`. `AC-RENDER PASS`, with its
negative control (same command, `-var-file` removed) still printing `AC-RENDER FAIL` — the gate has
teeth. `services/hermes` → `156 passed in 0.56s`. `git log origin/main..HEAD` → `0`; `git diff
--stat -- coder/templates/forge/forge-sync.sh` → empty.


**Post-state checks (at FE4-S01):**
- `~/workspace/repos/github/company-overlay` absent.
- `~/workspace/company-overlay/.git` present.
- CLAUDE.md and repos/INDEX.md content contain no Saply product names.

**Rollback:** `git checkout` the pre-story heredoc content and `repo_deny` list on the PoC branch. No infrastructure state is touched — this is a template-source-only change until FE3-S06 builds/pushes it.

## Dependencies

- **Blocked by:** FE3-S01 (shares the same file; sequence to avoid merge conflicts — either story can go first, but both land on the same branch before FE3-S06).
- **Blocks:** FE4-S01 (first workspace create is where AC4/AC5 actually get exercised), gate (b) in FE4-S02.

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Generic heredoc rewrite accidentally breaks the `~/workspace/AGENTS.md` symlink logic (`main.tf:234-236`) that depends on `CLAUDE.md` existing at a specific path | Low | Medium — onboarding breaks silently | AC1 only changes heredoc *content*, not the file path or the symlink logic around it; keep the `WORKSPACE_CLAUDE_EOF` markers and surrounding shell untouched |
| A future contributor re-adds a hardcoded company name to "make it clearer for their team" | Medium over time | Low — reintroduces the same genericity problem for the next company | Document in a template comment that company-specific content belongs in `company-overlay`, not `main.tf` |
| AC4/AC5 cannot be verified until FE3-S06/FE4-S01 exist, creating a false sense of "done" at this story's close | Medium | Low — caught by the Test Plan explicitly deferring those checks | Definition of Done below marks AC4/AC5 verification as deferred-and-cross-referenced, not skipped |

## Definition of Done

- [x] AC1–AC3 green and evidenced by direct file inspection. (AC1 green on substance; its
  verify_command's symlink sub-check is itself broken under ugrep — see the Execution record.)
- [ ] AC4–AC5 deferred verification recorded, cross-referenced to FE4-S01 once that story runs.
  **Recorded, not yet cross-referenced** — AC5 is verified green here (empty diff); AC4's live
  check is deferred and stays unticked until FE4-S01 actually runs and its evidence lands.
- [x] `terraform validate` passes on the PoC branch. (exit 0; also `terraform fmt -check` exit 0.)
- [x] `forge-sync.sh` itself left untouched (diff empty).
- [x] Story status updated from `draft` to `done` in this file's frontmatter.
- [x] **Round-2 verifier findings closed** (AC1, AC2, GEN-3, GEN-4, GEN-5, GEN-6) — see
  *Verifier round 2* above. `AC-RENDER PASS`; `forge-onboard.sh` no longer hangs on any path;
  `terraform plan -var 'forge_ado_org='` now errors instead of silently retargeting another org.
- [x] **Scope widened beyond this story's original `files_to_touch`**, deliberately, to close
  findings the verifier raised against files this story's prose had generated or configured:
  `coder/templates/forge/variables.tf` (empty-org validations), `coder/templates/forge/poc.tfvars`
  (new; the eight-knob PoC configuration), `coder/templates/forge/forge-onboard.sh` (`ask_login`
  timeout backstop) and `docs/coder/setup.md` (completed tfvars example + empty-string warning).
  `forge-sync.sh` remains untouched, as AC5 requires.

- [x] **Round-3 verifier findings closed.** `AC-COMPAT-ONBOARD-TIMEOUT` (default inverted to 0 =
  HEAD's unbounded wait; the backstop is now opt-in via `var.forge_onboard_timeout`, 300 in
  `poc.tfvars`) and `GEN-POC-TFVARS` (setup.md no longer claims `poc.tfvars` is committed; FE3-S06
  carries `--variables-file` and a new AC4b post-push assertion). `AC-COMPAT-SCRIPT-FALLBACKS`
  closed on both axes — in-script Saply fallbacks restored **and** all seven `FORGE_*` names
  published on `docker_container.env` — so no outcome depends on which delivery path wins. AC4
  remains **unticked**: the verifier scored it *unverified*, not fail.
- [x] **A second file outside this repo was edited**, deliberately:
  `FE3-S06-build-image-and-template-push.md` (AC4 rewritten to require `--variables-file`, new AC4b
  post-push assertion, test-plan step 6, two DoD boxes). The verifier's fix hint asked for it, and
  leaving it would have meant fixing the doc that lies while leaving the story that acts on it
  unchanged.

> **Caveat on closing this story.** The BLOCKED banner at the top (FE0-S01 GitHub OAuth App,
> FE0-S02 Cloudflare token) is still unresolved. This change is source-only, touches no
> infrastructure and boots no workspace, and FE3-S01 was executed under the same gate, so the
> status was moved to `done` on that precedent. If the operator intended the gate to bind FE3
> source edits too, revert this frontmatter line — the code change itself is independent of it.
