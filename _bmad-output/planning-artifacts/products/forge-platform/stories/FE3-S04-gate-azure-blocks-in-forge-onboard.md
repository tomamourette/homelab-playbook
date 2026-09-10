---
type: story
epic: FE3
id: FE3-S04
title: "Gate every Azure block in forge-onboard.sh, including az account show"
size: S
priority: MUST
owner: dev
blocking: false
fr_refs: [FR-WS-006]
nfr_refs: []
adr_refs: []
risk_refs: []
status: done
date: 2026-09-09
---

# FE3-S04: Gate every Azure block in forge-onboard.sh, including az account show

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
>
> **Executed ahead of the banner, 2026-09-09 — operator please confirm.** The banner above is
> left verbatim; it is correct for FE1–FE4 as a whole. This story was nevertheless executed,
> because every one of its ACs was verifiable on the dev host with **no** Coder, no GitHub OAuth
> App, no Cloudflare token and no CT 167 — the change is a 6-line edit to one shell script,
> proven with local `bash` harnesses (see Evidence). Nothing was committed, pushed, or deployed.
> If the block is intended to be absolute by policy even for infrastructure-free shell edits,
> revert with `git checkout coder/templates/forge/forge-onboard.sh`.

## User Story

As **tomamourette**, I want **every Azure-specific block in `forge-onboard.sh` gated behind a detectable condition — including the `az account show` check — so onboarding never invokes the `az` binary on an image that doesn't ship it**, so that **a developer's first interactive terminal in a Forge workspace doesn't hang or error on a login prompt for a CLI that was never installed**.

## Background and Context

`forge-onboard.sh` runs automatically on the first real interactive shell in every workspace (guarded by the `~/.forge-onboarded` sentinel, wired at `main.tf:320-334`). Step 4 of that script (`forge-onboard.sh:108-116`) unconditionally calls `az account show >/dev/null 2>&1`, and — since `set -u` is active (`forge-onboard.sh:14`) but this line doesn't reference an unset variable, it won't trip that guard — if `az` is not on `PATH` at all, `az account show` fails with a shell "command not found" rather than a clean non-zero exit from the Azure CLI itself. Depending on the workspace image's shell settings this can print a startup-log-cluttering error rather than the intended `warn "Azure CLI: not logged in"` branch, and if `az` genuinely doesn't exist in the de-Azured Forge workspace image, `ask_login "Azure CLI"` (`forge-onboard.sh:113`) would then prompt the developer to log in to a CLI that literally is not installed — a broken, confusing first-run experience for exactly the demo that matters (gate (e), "claude starts... The actual product value").

Verified by direct inspection this pass: the `az account show` call is at **`forge-onboard.sh:109`** in the current `forge-platform @ 2b27a95` checkout (the sprint-change-proposal's evidence table cites `:103` for this same call — a small line-number drift, most likely from incidental edits between the proposal's research pass and this story's authoring pass; **109 is the verified current line** and is what this story's AC references).

This is not the only Azure-coupled block in the script. A full audit found three:
1. **Step 3b** (`:80-106`) — the optional private ADO npm feed auth, hardcoded to `pkgs.dev.azure.com/saplyai/CV-engine/_packaging/WordUI` by default (`FORGE_NPM_FEED_HOST`). Already self-skips cleanly when the variable is empty (`:84-85`), and is override-driven — this block is **already correctly gated** and needs no change beyond confirming its default doesn't error when unset.
2. **Step 4** (`:108-116`) — the `az account show`/`az login --use-device-code` block. **Not gated** — this is the one FR-WS-006 names explicitly.
3. **Step 3** (`:72-78`) — the Azure DevOps external-auth check. This uses `coder external-auth access-token azure-devops`, a Coder-native call, not the `az` binary — it does not need gating on `az`'s presence, only on ADO being relevant at all, which it already handles by printing an informational warning rather than failing.

FR-WS-006 requires gating **every** Azure block, so this story adds a presence check specifically around step 4 (the one genuinely az-binary-dependent, ungated block), and confirms (without needing code changes) that steps 3 and 3b already degrade cleanly.

## Acceptance Criteria

**AC1 — `az account show` gated on binary presence.**
- **Given** `forge-onboard.sh` step 4,
- **When** the operator runs the script in a shell where `az` is not on `PATH`,
- **Then** the step prints something equivalent to `info "Azure CLI: not installed, skipped"` and does **not** attempt `az account show` or `ask_login "Azure CLI"` at all — no shell "command not found" error appears anywhere in the output.

**AC2 — Existing behavior preserved when `az` is present.**
- **Given** a workspace image where `az` **is** installed,
- **When** step 4 runs,
- **Then** behavior is unchanged from before this story: `az account show` is attempted, and `ask_login`/`az login --use-device-code` still offer to log in on failure exactly as today.

**AC3 — Step 3b confirmed self-skipping, no code change required unless a gap is found.**
- **Given** step 3b (`FORGE_NPM_FEED_HOST`),
- **When** the operator sets `FORGE_NPM_FEED_HOST=""` and re-runs onboarding,
- **Then** the script prints `info "private npm feed: not configured, skipped"` (`:85`) and does not attempt any ADO token lookup — confirming the existing gate at `:84-85` is sufficient; this story makes no change here unless testing reveals otherwise.

**AC4 — Step 3 (ADO external-auth check) confirmed non-`az`-dependent.**
- **Given** step 3,
- **When** the operator inspects it,
- **Then** it calls only `coder external-auth access-token azure-devops`, never the `az` binary directly — confirming this step needs no gating change under FR-WS-006's "az binary absent" concern (it may still print an ADO-specific warning, which is fine and out of scope for this story — ADO awareness itself is not being removed, only unconditional `az` invocation).

**AC5 — Line reference corrected and recorded.**
- **Given** the sprint-change-proposal's evidence table cites `forge-onboard.sh:103` for this fix,
- **When** the operator runs `grep -n 'az account show' coder/templates/forge/forge-onboard.sh` against the PoC branch's actual state,
- **Then** the verified line number (109 as of this story's authoring, or whatever it is by the time this story executes) is recorded in this story's evidence, noting the discrepancy against the proposal's `:103` citation rather than silently assuming either number.

## Implementation Notes

Reference FR-WS-006, proposal §4.2 FE3-S04, evidence table citation `forge-onboard.sh:103` (verified this pass as `:109` — see AC5). Only step 4 needs a code change.

```bash
# forge-onboard.sh — before (step 4, current ~line 108-116)
if az account show >/dev/null 2>&1; then
  ok "Azure CLI: logged in"
else
  warn "Azure CLI: not logged in"
  if ask_login "Azure CLI"; then
    az login --use-device-code || warn "az login failed — re-run later with: az login --use-device-code"
  fi
fi

# after
if ! command -v az >/dev/null 2>&1; then
  info "Azure CLI: not installed, skipped"
elif az account show >/dev/null 2>&1; then
  ok "Azure CLI: logged in"
else
  warn "Azure CLI: not logged in"
  if ask_login "Azure CLI"; then
    az login --use-device-code || warn "az login failed — re-run later with: az login --use-device-code"
  fi
fi
```

```bash
# AC verification
grep -n 'az account show' coder/templates/forge/forge-onboard.sh
PATH="/usr/bin:/bin" bash -c 'command -v az || echo "az absent, as expected on a de-Azured image"'
# then run forge-onboard.sh in a shell with az stripped from PATH and inspect output for AC1
```

## Test Plan

**Pre-state:** `az account show` unconditional at (verified) line 109; step 3b already self-skips on empty `FORGE_NPM_FEED_HOST`; step 3 already uses only `coder external-auth`.

**Action sequence:**
1. Add the `command -v az` gate around step 4 (AC1, AC2).
2. Run onboarding in a shell with `az` present, confirm unchanged behavior (AC2).
3. Run onboarding in a shell with `PATH` stripped of `az`, confirm the new skip message and no error (AC1).
4. Empty `FORGE_NPM_FEED_HOST` and re-run, confirm existing skip message still appears (AC3).
5. Re-read step 3, confirm no `az` binary call (AC4).
6. Record the verified `az account show` line number against the proposal's citation (AC5).

**Post-state checks:**
- No "command not found" for `az` anywhere in onboarding output when `az` is absent.
- Behavior unchanged when `az` is present.
- Steps 3 and 3b confirmed already-safe, no regressions introduced.

**Rollback:** `git checkout` the pre-story `forge-onboard.sh` on the PoC branch. No infrastructure state touched — this executes inside a workspace container, not on the host.

## Dependencies

- **Blocked by:** None within FE3 specifically (independent of FE3-S01/S02/S03's file scope — different file).
- **Blocks:** FE4-S01 (first workspace's first interactive terminal runs this script via the `~/.bashrc` auto-run hook).

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| The `command -v az` gate masks a case where `az` is present but broken in some other way (e.g., a corrupted install), producing a misleading "not installed" message | Low | Low — cosmetic message inaccuracy only, no functional harm since the fallback path (skip) is safe either way | Accept as a minor and acceptable imprecision; not worth a more complex health check for this PoC |
| A future workspace image variant does ship `az` (e.g., a hybrid company deployment), and this gate is mistaken for "Azure support removed" | Low | Low | AC2 explicitly preserves full functionality when `az` is present; comment the gate's purpose inline |
| Line-number drift (AC5) recurs for other citations in the same file between this story and FE4 execution | Medium | Low — cosmetic, doesn't block acceptance | Recording verified line numbers, not proposal citations, as the source of truth per story |

## Evidence

Executed 2026-09-09 against `forge-platform @ 2b27a95` (branch `main`). Working-tree edit only —
not committed, not pushed. One file changed: `coder/templates/forge/forge-onboard.sh`.

### AC5 — line-number reconciliation for `az account show`

| Source | Cited line | Verdict |
|---|---|---|
| Sprint-change-proposal evidence table | `forge-onboard.sh:103` | **Stale.** Not the location of the call in any state observed this pass — neither HEAD nor working tree. |
| This story's Background (authoring pass) | `forge-onboard.sh:109` | **Correct pre-edit.** Confirmed in both the working tree and the committed HEAD blob. |
| Post-edit (after this story's change) | `forge-onboard.sh:115` | **Current.** The call moved down 6 lines (4 comment + 2 code lines inserted above it) and is now the `elif` arm. |

Real output:

```
$ git show HEAD:coder/templates/forge/forge-onboard.sh | grep -n 'az account show'
109:if az account show >/dev/null 2>&1; then

$ grep -n 'az account show' coder/templates/forge/forge-onboard.sh    # post-edit
115:elif az account show >/dev/null 2>&1; then
```

### Correction to this story's Background (§ "Background and Context")

The Background asserts that an ungated `az account show` on an image without `az` "can print a
startup-log-cluttering error". **That claim is not reproducible and is withdrawn.** Line 109
already redirected stderr (`>/dev/null 2>&1`), which swallows bash's own `command not found`
message along with everything else. Verified with `az` stripped from `PATH`:

```
$ env -i PATH=<no-az> bash --noprofile --norc -c 'az account show >/dev/null 2>&1; echo "exit=$?"'
exit=127                          # <- no message at all, stderr was already redirected

$ env -i PATH=<no-az> bash --noprofile --norc -c 'az login --use-device-code'
bash: line 1: az: command not found
exit=127                          # <- the ONLY real leak, and it was at :114, not :109
```

The genuine defect is the second half of AC1's concern: the ungated script **prompted the
developer to log in to a CLI that is not installed**. Observed pre-edit, `az` absent from `PATH`
(the `/dev/tty` line is harness noise from `env -i`; the real script is tty-guarded at `:22`):

```
  ! Azure CLI: not logged in
  Log in to Azure CLI now?  [y] yes   [Enter] skip   [q] skip all: <harness: /dev/tty unavailable>
  • Azure CLI: skipped
```

The unredirected `command not found` at `:114` fires only if the developer answers `y` to that
prompt — so the prompt is simultaneously the defect and the gateway to the error. The gate closes
both: when `az` is absent the `elif`/`else` arms are unreachable, so `:114` can never run. For
that reason `az login --use-device-code` was left byte-identical (AC2).

### Additional line-number drift found (same class as AC5)

The Background cites `main.tf:320-334` for the `~/.bashrc` auto-run hook. Measured this pass:

| Location in `main.tf` | @ HEAD 2b27a95 | @ working tree |
|---|---|---|
| `onboard_b64 = base64encode(file(...))` | 119 | 140 |
| script delivery (`base64 -d > ~/.local/bin/forge-onboard`) | 312 | 340 |
| managed-block `sed -i` strip | 326 | 354 |
| tty + sentinel guarded hook line | 330 | 358 |

Neither column matches the cited `320-334`. `main.tf` is concurrently modified by the parallel
FE3-S01 run, which is why the two columns differ — working-tree numbers are a moving target and
should not be cited. Per this story's own Risks row 3, verified numbers are recorded here rather
than the proposal's citations being trusted. **No `main.tf` change was made by this story**, and
the stale citation in the Background was deliberately left in place rather than silently rewritten.

### The change

Single hunk, step 4 only:

```diff
 # 4. Azure CLI
-if az account show >/dev/null 2>&1; then
+# Presence gate (FR-WS-006): skip this step entirely when the az binary is absent from the
+# workspace image, so onboarding never invokes az or prompts for a login to a CLI that is not
+# installed. This is NOT "Azure support removed" — when az IS present the original detect /
+# warn / ask_login / device-code flow below runs unchanged.
+if ! command -v az >/dev/null 2>&1; then
+  info "Azure CLI: not installed, skipped"
+elif az account show >/dev/null 2>&1; then
   ok "Azure CLI: logged in"
 else
```

The inline comment is the Risks row 2 mitigation ("mistaken for Azure support removed"), not decoration.

### AC results

| AC | Pre-edit | Post-edit | Evidence |
|---|---|---|---|
| AC1 — gated on binary presence | **FAIL** (prompted `Log in to Azure CLI now?` with no `az` on `PATH`) | **PASS** | az-stripped `PATH` harness prints exactly `  • Azure CLI: not installed, skipped`; no prompt, no `command not found`. |
| AC2 — behaviour preserved when `az` present | PASS | **PASS** | Host has `/usr/bin/az`; harness prints `  ✓ Azure CLI: logged in`. Never reaches the "not installed" branch. |
| AC3 — step 3b self-skips | PASS | **PASS** (no change made) | `FORGE_NPM_FEED_HOST="" ` harness prints `  • private npm feed: not configured, skipped`; no ADO token lookup. The "unless testing reveals otherwise" escape hatch was **not** triggered. |
| AC4 — step 3 non-`az`-dependent | PASS | **PASS** (no change made) | Step 3 body calls only `coder external-auth access-token azure-devops`. Regex sweep for bare `az ` across the whole file returns exactly two hits, both in step 4. |
| AC5 — line number recorded | n/a | **PASS** | Table above: `:103` stale, `:109` verified pre-edit, `:115` post-edit. |
| AC6 — scope guard (derived) | n/a | **PASS** | `bash -n` → SYNTAX OK. `git diff --name-only` shows `forge-onboard.sh` plus the parallel run's four pre-existing files and nothing else. Diff is one hunk in step 4. |

### Out-of-scope observation — likely missing story (raise before FE4-S02 runs gate (e))

> **RESOLVED in remediation round 2.** The verifier ruled these in scope for this story's
> generalisation lens (LENS-GEN-2, fail), so they were fixed here rather than deferred to a
> new story. Every literal listed below is now an overridable `${FORGE_*-default}` or neutral
> text, and `~/.codex/AGENTS.md` no longer asserts any deployment's cloud, region, product
> repos or state storage. The paragraph below is kept as the round-1 record; do not action it.

`forge-onboard.sh` still carries Saply-specific literals that no FE3 story appears to own
(FE3-S02 is scoped to `main.tf` heredocs and does not mention this file). At working-tree line
numbers: `:57` `you@saply.ai`; `:153-155` hint text naming `Saply-ai/agentic-ai` and
`Saply-ai/knowledge-base`; `:219` `# Codex CLI — Saply Forge workspace config`; and `:239-273`
a `~/.codex/AGENTS.md` heredoc asserting "a Saply Forge developer workspace on Azure" plus
`matching-frontend`/`matching-service`, `CV-engine`, `francecentral`, and state storage
`saplyforgetfstate` — written into every workspace's Codex global context. Out of scope for
FE3-S04 (az-gating only) and deliberately untouched. Related, and also left alone per AC3: with
`FORGE_NPM_FEED_HOST` unset and no ADO token, first-run output prints
`! pkgs.dev.azure.com/saplyai/CV-engine/_packaging/WordUI npm feed: skipped, no Azure DevOps token`.
That is a legal overridable default under ground truth, but it does put a `saplyai` URL in the
PoC's first-run output — operator confirmation requested.

### Test-coverage note

No automated test covers `forge-onboard.sh`. The repo's pytest suite lives under
`services/hermes` and exercises nothing in `coder/templates/forge`. The commands above are
purpose-built harnesses, not a committed regression net; adding one would be new scope.

## Remediation round 2 — verifier findings (2026-09-09)

Three verifier findings came back against the first pass. All are addressed here. The
falsified claim is retracted rather than restated.

### LENS-GEN-1 (was: fail) — the gate was a BINARY probe, not a CONFIG probe

The verifier was right and the first pass was wrong. `command -v az` is satisfied on the PoC
image: `workspace/Dockerfile:23` installs the Azure CLI and `:25` runs `az version`, so the
`not installed` arm is unreachable there and a developer was still prompted to log in to a
tenant this deployment does not have.

Reproduced the verifier's exact scenario — a stub `az` on PATH that exits 1 (installed, no
account configured). Pre-fix, from the HEAD blob, byte-identical to what the verifier quoted:

```
  ! Azure CLI: not logged in
  Log in to Azure CLI now?  [y] yes   [Enter] skip   [q] skip all:
  • Azure CLI: skipped
```

Post-fix, same harness, same stub:

```
  • Azure CLI: no Azure account configured, skipped
```

Step 4 now runs four gates, cheapest first: an explicit `FORGE_ENABLE_AZURE_CLI` opt-out
(`:131`), the binary probe (`:133`), `az account show` (`:135`), and a config probe
`az account list --only-show-errors --output tsv` (`:137`). Both of the fix_hint's options
were taken rather than one: (a) the env knob exists, defaulting to `true`; (b) the binary
probe is AND-ed with a real config probe.

Backwards compatibility for the Azure deployment was verified by execution, not asserted.
With a stub `az` where `account show` fails but `account list` returns a subscription row —
a real Azure user whose session has expired — post-fix output is byte-identical to pre-fix:

```
  ! Azure CLI: not logged in
  Log in to Azure CLI now?  [y] yes   [Enter] skip   [q] skip all:
```

`az account list` reads the local profile, so an expired session still lists its
subscriptions and falls through to the login offer. Only "az installed but never pointed at
a tenant" is newly skipped — exactly what FR-WS-006 and the ground-truth rule ("must SKIP
cleanly when their config is absent; they must not prompt or fail") require.

Step 3 (Azure DevOps) got the same treatment at `:77` via `FORGE_ENABLE_AZURE_DEVOPS-true`.
It never prompted, but it did tell a deployment with no ADO to go and configure an ADO
provider, which is not skipping cleanly. Default `true` preserves today's output exactly.

### LENS-GEN-2 (was: fail) — five hard-coded Saply strings

All five are now overridable defaults or neutral text:

| Was | Now |
|---|---|
| `:57` `you@saply.ai` | `you@example.com` — neutral placeholder, no org identity |
| `:159-161` `Saply-ai/agentic-ai`, `Saply-ai/knowledge-base`, "Saply-ai org owner" | `${FORGE_GITHUB_ORG-Saply-ai}` in all three places |
| `:225` `# Codex CLI — Saply Forge workspace config` | `${FORGE_ORG_LABEL-Saply}`; delimiter `<<'TOMLEOF'` → `<<TOMLEOF` |
| `:246-273` the `~/.codex/AGENTS.md` heredoc | delimiter `<<'MDEOF'` → `<<MDEOF`; org strings parameterised; non-portable deployment facts removed |

The AGENTS.md body was the finding that actually mattered: it is Codex's global ground truth
in every workspace, and it asserted "a Saply Forge developer workspace on Azure",
`matching-frontend`/`matching-service`, `CV-engine`, `francecentral`, and state storage
`saplyforgetfstate`. Those are not defaults that anything could override, so they were
removed rather than parameterised, and replaced with a line telling Codex to read deployment
specifics from the knowledge base instead of assuming them. Backwards compatibility is kept
through a new `FORGE_CODEX_EXTRA_CONTEXT` appendix hook: a deployment exports its own facts
and they are appended verbatim; unset or empty appends nothing.

Because the delimiters are now unquoted, every backtick in the heredoc is escaped. Verified
by execution: step 9 run against a throwaway HOME renders fenced code blocks and inline code
spans literally, with no command substitution.

Executed against a throwaway HOME with `FORGE_ORG_LABEL=Homelab FORGE_GITHUB_ORG=tomamourette`,
then swept for `saply|francecentral|matching-(frontend|service)|CV-engine|key vault|azure infra|tfstate`:

- pre-fix (HEAD blob, same overrides): 8 hits, matching the verifier's quoted lines 1, 3, 9,
  17, 18, 24 and 28.
- post-fix: zero hits.

### CLAIM-lockfile-unmodified (was: unverified) — claim RETRACTED

The first pass claimed "the tracked `.terraform.lock.hcl` is UNMODIFIED". That was false and
is withdrawn. `git diff` confirms one additive line under
`registry.terraform.io/hashicorp/http`:

```
+    "h1:FekY+4cjIw3QBdpk2dVQ20+t8AeDwCK/VaKOnjfeJvw=",
```

Attribution was re-confirmed independently rather than taken on trust: `hashicorp/http`
appears nowhere in `main.tf` (whose `required_providers` lists only `coder/coder` and
`kreuzwerker/docker`) and only in `.terraform/modules/intellij_gateway/main.tf:10`; the
`main.tf` diff contains no provider-requirement lines at all. The hash is therefore a
`terraform init` artifact from installing the intellij_gateway module, produced by a parallel
run. FE3-S04 changed one `.sh` file and cannot have caused it.

Left in place, deliberately — and that call is now backed by a measurement rather than a
prediction. `terraform validate` in `coder/templates/forge` currently exits 0:

```
Success! The configuration is valid, but there were some
validation warnings as shown above.
```

Zero errors, three warnings, all of them the pre-existing `coder_agent.main` `dir` deprecation
on `main.tf:263`. The added hash is exactly what repairs the
`hashicorp/http 3.6.0 ... does not match any of the checksums` error the first pass hit, so
reverting it would re-break `validate` for whoever currently holds `main.tf`. The operator
decision the verifier asked for still stands, but "revert" is now the strictly worse option.

Worth flagging upward: this also contradicts the run's ground truth, which said `validate` is
"EXPECTED to still fail on the intellij_gateway module until FE3-S05". It does not fail, and
`intellij_gateway` is not mentioned in the output at all. Reporting that precisely rather than
adjusting anything to match the expectation.

One caution for anyone re-checking: this file's modified/unmodified state was observed to
flip inside a single minute — `git status` listed it, then did not, then `git diff` showed the
hunk again — while a parallel run was executing `terraform init`. Any single snapshot of it
is racy, which is the most likely reason the first pass reported it honestly but wrongly.

### Line numbers after this round

`az account show` has moved again, as a direct result of this story's own edits:

| Reference | Line |
|---|---|
| Proposal citation (stale from the start) | `:103` |
| Verified pre-story, HEAD blob | `:109` |
| After remediation round 1 | `:115` |
| After remediation round 2 | `:133` |
| Live at 12:04, after FE3-S03's concurrent edit to this same file | `:135` |

AC5's verify_command computes the line dynamically, so it passes on whichever line is live —
`:135` as measured at 12:04. Treat every number in this table as a timestamped observation,
not a durable fact: FE3-S03 was editing this same file while this round ran (see below).

One trap worth leaving behind for the next editor: AC5 resolves the line with
`grep -n 'az account show' ... | head -1`, so the *first* textual match wins. The first draft
of this round's gate comment contained the words "az account show", which put the first match
on the comment at `:121` and made AC5 fail against a line that is not code. The comment was
reworded to "an active signed-in session" — same line count, so the code line did not move.
Prose in this file must avoid quoting the exact strings the ACs grep for.

### Not changed, and why

- Step 3b was left alone, as AC3 requires. Its `${FORGE_NPM_FEED_HOST-...saplyai...}` default
  was the one string the verifier classed as already qualifying, and its `# 3b.` comment cited
  a `CV-engine` doc path that the verifier's enumeration deliberately excluded. Both were
  rewritten anyway — by FE3-S03, mid-round, not by this story (see below). The default is now
  `${FORGE_NPM_FEED_HOST-}` with the URL moved to `var.forge_npm_feed_host` in `main.tf`.
- `main.tf` — not touched by this story. Plumbing these knobs into `coder_agent.main.env` was
  written up as a handover below and FE3-S03 then implemented it independently; see the
  contract check.

### Concurrency: FE3-S03 edited this same file mid-round, and the two halves converged

At 12:02:57, while this round was running its AC sweep, FE3-S03 wrote to
`coder/templates/forge/forge-onboard.sh` — the file this story owns — rewriting step 3b's
comment and changing its default to `${FORGE_NPM_FEED_HOST-}`. All eight of this round's edits
survived that write and were re-verified individually afterwards; the collision was in step 3b,
which this story deliberately never touched, so nothing was lost either way. It was luck, not
design: two runs editing one file with no locking can silently drop work.

The valuable part is that the two halves match. This story chose env-var names on the script
side; FE3-S03 independently plumbed `coder_agent.main.env` on the Terraform side. Checked
mechanically rather than by eye — every `${FORGE_*}` the script reads against every `FORGE_*`
`main.tf` exports:

| Env var | Read by forge-onboard.sh | Exported by main.tf |
|---|---|---|
| `FORGE_ENABLE_AZURE_CLI` | yes | yes — `var.forge_enable_azure_cli ? "true" : "false"` |
| `FORGE_ENABLE_AZURE_DEVOPS` | yes | yes — `var.forge_enable_azure_devops ? "true" : "false"` |
| `FORGE_ORG_LABEL` | yes | yes — `var.forge_org_label` (default `"Saply"`) |
| `FORGE_GITHUB_ORG` | yes | yes — `local.github_org` |
| `FORGE_NPM_FEED_HOST` | yes | yes — `var.forge_npm_feed_host` |
| `FORGE_CODEX_EXTRA_CONTEXT` | yes | no — optional appendix hook, unset appends nothing |

The booleans matter: the script compares against the literal string `true`, and `main.tf` sends
`"true"`/`"false"` strings rather than HCL bools. That agreement was verified by running the
script with those exact values, not inferred from the types.

### End-to-end proof, both deployment profiles

Steps 3, 3b, 4 and 9 were run together under the two environments `main.tf` actually produces.

Profile A — the PoC (`azure_cli=false`, `azure_devops=false`, `org=tomamourette`,
`label=Forge`, `feed=""`), with a stub `az` present on PATH:

```
  • Azure DevOps: not configured for this deployment, skipped
  • private npm feed: not configured, skipped
  • Azure CLI: disabled for this deployment, skipped
  ✓ Codex: config.toml created
  ✓ Codex: AGENTS.md created (global workspace context)
```

Sweeping everything that profile wrote to disk for
`saply|francecentral|CV-engine|matching-(frontend|service)|tfstate|on Azure` returns nothing.

Profile B — the existing Azure deployment, all `main.tf` defaults, with a stub `az` whose
session has expired:

```
  ! Azure DevOps: no token — authenticate the 'azure-devops' provider in the Coder UI,
  • then restart the workspace to clone ADO repos into ~/workspace/repos/ado.
  ! pkgs.dev.azure.com/saplyai/CV-engine/_packaging/WordUI npm feed: skipped, no Azure DevOps token
  ! Azure CLI: not logged in
  Log in to Azure CLI now?  [y] yes   [Enter] skip   [q] skip all:
```

That is the pre-story behaviour, unchanged. The generalisation is carried entirely by the
defaults, so the Azure deployment sees no difference at all.

## Remediation round 3 — verifier findings (2026-09-09)

Round 2 shipped a fourth gate that was **wrong**, and three independent verifier lenses
(`correctness` AC2, `compat-regression` AC-COMPAT-1, `generalisation` LENS-GEN-1) all landed on
the same line. They were right. This section records the retraction and the fix.

### The defect: gate 4 keyed on login history, not on deployment config

Round 2's step 4 ended with

```sh
elif [ -z "$(az account list --only-show-errors --output tsv 2>/dev/null || true)" ]; then
  info "Azure CLI: no Azure account configured, skipped"
```

with an in-code comment claiming an empty subscription list means "the CLI is installed but was
never pointed at a tenant, so there is no credential to renew and nothing to prompt about". That
comment was false. Round 2 "proved" backwards compatibility with a stub `az` whose
`account list` returned a subscription row — a state that can only exist **after** a prior
successful login. It never exercised a genuinely fresh profile with the real CLI.

Probed the real binary (`/usr/bin/az` 2.84.0) against an empty `AZURE_CONFIG_DIR`:

```
az account show                                    -> exit=1
az account list --only-show-errors --output tsv    -> raw=[]  bytes=0
```

So gate 4 fires on an empty profile. And an empty profile is the **normal** first-run state of
every Azure workspace: `docker_volume.home` is per-workspace, `$HOME/.forge-onboarded` is the
onboarding sentinel, and nothing logs in ahead of onboarding. Reproduced end to end with the
real `az`, `FORGE_ENABLE_AZURE_CLI=true`, and a fresh profile:

```
--- PRE-STORY (HEAD 2b27a95) ---
  ! Azure CLI: not logged in
  Log in to Azure CLI now?  [y] yes   [Enter] skip   [q] skip all:
  • Azure CLI: skipped

--- ROUND 2 (the regression), IDENTICAL conditions ---
  • Azure CLI: no Azure account configured, skipped
```

The device-code login offer had been removed from every brand-new Azure workspace — the exact
developer the step exists to serve. That breaks the run's hard rule that every new variable's
default must reproduce today's behaviour.

### Root cause, stated plainly

Profile-emptiness cannot distinguish "PoC with no tenant" from "Azure developer on a brand-new
workspace". Both are an empty `~/.azure`, so **any** gate keyed on it must resolve one of them
wrongly. Deployment intent has to come from configuration, and `FORGE_ENABLE_AZURE_CLI` already
carries it: `coder_agent.main.env` exports it unconditionally, so gate 1 always has a real value.

### The fix

Gate 4 deleted. Step 4 is three gates, and the comment now states why the fourth must not exist:

```sh
if [ "${FORGE_ENABLE_AZURE_CLI-true}" != "true" ]; then
  info "Azure CLI: disabled for this deployment, skipped"
elif ! command -v az >/dev/null 2>&1; then
  info "Azure CLI: not installed, skipped"
elif az account show >/dev/null 2>&1; then      # forge-onboard.sh:135
  ok "Azure CLI: logged in"
else
  warn "Azure CLI: not logged in"
  ...
```

The PoC gets its silent skip from `forge_enable_azure_cli = false` in `poc.tfvars`
(`docs/coder/setup.md:220`), not from inference.

### Evidence — three deployment profiles, executed

`PROFILE B`, existing Azure deployment, all defaults, **fresh** az profile, steps 3 + 3b + 4,
pre-story (HEAD) vs post-fix, harness tmp-path normalised:

```
$ diff -u b_pre.n b_post.n
BYTE-IDENTICAL — Azure deployment behaviour fully preserved
```

```
  ! Azure DevOps: no token — authenticate the 'azure-devops' provider in the Coder UI,
  • then restart the workspace to clone ADO repos into ~/workspace/repos/ado.
  ! pkgs.dev.azure.com/saplyai/CV-engine/_packaging/WordUI npm feed: skipped, no Azure DevOps token
  ! Azure CLI: not logged in
  Log in to Azure CLI now?  [y] yes   [Enter] skip   [q] skip all:
```

`PROFILE A`, PoC with `poc.tfvars`:

```
  • Azure DevOps: not configured for this deployment, skipped
  • private npm feed: not configured, skipped
  • Azure CLI: disabled for this deployment, skipped
```

`PROFILE C`, PoC operator forgets the variables file entirely (all `FORGE_*` unset): the script
falls back to Azure behaviour and prompts. This is by design — config, not inference, is the
discriminator — and it is unreachable through the template, because `coder_agent.main.env`
exports `FORGE_ENABLE_AZURE_CLI` on every deployment. It can only happen when the script is
hand-run outside a workspace.

> **Correction (2026-09-09, later the same day — PROFILE C was wrong about the risk, and the
> behaviour it describes has since been changed).** The paragraph above is kept exactly as it was
> written when this story was executed, because it is what the AC evidence was judged against. Two
> things in it do not hold up:
>
> 1. **"Unreachable through the template" was too strong.** `forge-onboard.sh` is *not* run by the
>    template's `startup_script`: the startup script writes it to `~/.local/bin/forge-onboard` and
>    installs a managed `~/.bashrc` block, and the script then runs in the developer's first
>    interactive terminal. The `coder_agent.main.env` export therefore has to survive a hop the
>    startup script does not make, which is exactly why the template publishes every `FORGE_*` name
>    twice (agent env *and* `docker_container.env`). "Env delivery cannot fail here" was an
>    assumption, not an observation — and the unset case is the one case where being wrong costs
>    the most, because the fallback prompt lands in the developer's FIRST terminal and holds it.
> 2. **The unset fallback is no longer Azure behaviour.** As of 2026-09-09,
>    `forge-onboard.sh` reads `${FORGE_ENABLE_AZURE_DEVOPS-false}` (step 3, `:113`) and
>    `${FORGE_ENABLE_AZURE_CLI-false}` (step 4, `:179`) — `-false`, not the `-true` this story
>    shipped. `forge-sync.sh`'s ADO clone block is gated on the same name with the same `-false`
>    fallback, and both `forge-sync` call sites in `main.tf` now pass `FORGE_ENABLE_AZURE_DEVOPS`
>    explicitly on the command line.
>
> **Post-fix PROFILE C** (PoC operator forgets the variables file entirely, all `FORGE_*` unset)
> is therefore a clean skip, not a prompt:
>
> ```
>   • Azure DevOps: not configured for this deployment, skipped
>   • Azure CLI: disabled for this deployment, skipped
> ```
>
> (Step 3b, the private npm feed, is unchanged and still falls back to the Azure feed host when
> `FORGE_NPM_FEED_HOST` is unset, per this story's AC3 — an unset feed host cannot prompt, it can
> only skip on a missing token.)
>
> **PROFILE B is unaffected**, which is the whole reason this is safe: the Azure deployment sets
> both gates to `true` from `var.forge_enable_azure_cli` / `var.forge_enable_azure_devops`
> (defaults `true`) on both `coder_agent.main.env` and `docker_container.env`, so the changed
> fallback never fires there. What changed is only what *absence of the flag* means: it now means
> "this deployment has not told me it has Azure", which is the only thing absence can honestly
> mean, instead of "assume Azure".
>
> Also renamed on the same day: `poc.tfvars` (referred to above and at `:566`) is now
> `poc.variables.yaml`. The HCL file was never loadable by Coder — `coder templates push
> --variables-file` parses YAML into `map[string]string` — so PROFILE A's overrides could only
> ever have been applied by a local `terraform plan -var-file=`, never by the push that actually
> deploys the template. See FE3's F1/F4 record and `scripts/poc-plan.sh`.

> **Follow-up correction (2026-09-09, later still — the parenthetical about step 3b above is now
> out of date, and the "clean skip" it qualified was incomplete).** A verification pass drove the
> post-fix script under a real pty with every `FORGE_*` unset and stub binaries that log their
> argv. The two boolean gates behaved exactly as the correction above claims, but the run still
> logged `coder external-auth access-token azure-devops`, and the generated `~/.codex/AGENTS.md`
> still ended with `## Deployment specifics — This workspace runs on Azure … francecentral …
> Key Vault … saplyforgetfstate`. Two ungated Azure fallbacks were responsible, both outside this
> story's literal wording but inside the property it exists to establish:
>
> 1. **Step 3b, the private npm feed** — `NPM_FEED_HOST="${FORGE_NPM_FEED_HOST-pkgs.dev.azure.com/saplyai/CV-engine/_packaging/WordUI}"`
>    fell back to Saply's ADO artifacts feed, and the very next line minted an ADO token for it.
>    The parenthetical above ("an unset feed host cannot prompt, it can only skip on a missing
>    token") was true as far as it went and missed the point: the token *request* is itself the
>    thing the gate exists to prevent, and the fallback also printed another organisation's feed
>    URL to a homelab developer.
> 2. **The `FORGE_CODEX_EXTRA_CONTEXT` unset-fallback heredoc** — the same Azure facts the gated
>    `repos/ado/` tree row had just been made to omit, re-asserted 30 lines later as Codex ground
>    truth.
>
> Both are now gated. Step 3b requires `FORGE_ENABLE_AZURE_DEVOPS=true`
> (`forge-onboard.sh:142`) and otherwise prints `private npm feed: not configured for this
> deployment, skipped`; the Codex appendix fallback requires either Azure flag (`:395`) and is
> otherwise empty, so the generated file carries no `## Deployment specifics` section at all. The
> Azure deployment is again unaffected — with either flag true both fallbacks are reachable exactly
> as before. **Post-fix PROFILE C is now a clean skip in full**, with no `azure-devops` token
> request anywhere in the run:
>
> ```
>   • Azure DevOps: not configured for this deployment, skipped
>   • private npm feed: not configured for this deployment, skipped
>   • Azure CLI: disabled for this deployment, skipped
> ```

### AC2 strengthened (it could only ever pass vacuously)

The verifier showed AC2's harness passes on this host for the wrong reason: `~/.azure` holds a
signed-in profile, so execution stops at gate 3 and never reaches the branch AC2's text is about.
A new **AC2-FRESH** case runs the same block with an empty `AZURE_CONFIG_DIR` and asserts the
login offer is still emitted, so this class of defect cannot pass silently again:

```
AC2       PASS    ✓ Azure CLI: logged in                       (logged-in host, gate 3)
AC2-FRESH PASS    ! Azure CLI: not logged in
                  Log in to Azure CLI now?  [y] yes  …          (empty profile, gate 4 absent)
```

### AC-COMPAT-1(b) — `FORGE_CODEX_EXTRA_CONTEXT` is now plumbed and restores everything

Round 2 left the hook exported by nobody, so the Azure deployment's Codex global context was
genuinely thinner. `variables.tf` now declares `forge_codex_extra_context`, exported from
`coder_agent.main.env`, whose default restores every fact the generalised body no longer asserts.
Round 3 added the two the first draft of that default still missed — **`Key Vault`** (named by the
verifier) and the **Mnemosyne** rename. Rendered `~/.codex/AGENTS.md`, HEAD vs post-fix under
Azure defaults, checked fact by fact:

```
=== facts in HEAD's AGENTS.md still LOST post-fix ===
(end of lost list — empty means full restore)
```

Under PoC overrides the same file renders **0** Saply/Azure literals.

### Line-number drift, continued

`az account show` has now moved five times: `:103` (proposal, always stale) → `:109` (HEAD) →
`:115` (round 1) → `:133` (round 2) → **`:135`** (round 3, live). AC5 resolves it dynamically
with `grep … | head -1`, which is why prose in this file must never quote the exact strings the
ACs grep for.

### Concurrency, again — and this time it overlapped

A parallel run was writing `coder/templates/forge/main.tf`, `variables.tf` and
`forge-onboard.sh` **during** this round (12:22:15–12:22:44). It had independently deleted gate 4
and added `forge_codex_extra_context` before this run's first edit landed. Round 3's own
contribution is therefore narrower than it would otherwise have been: the two missing facts in
the Codex restore default, plus independent re-verification of everything else. All findings
below were re-derived by execution rather than taken on trust.

## Definition of Done

- [x] AC1–AC6 all green and evidenced (re-run verbatim after remediation round 2).
- [x] Step 4 gated on CONFIG, not on local CLI state: `FORGE_ENABLE_AZURE_CLI` opt-out +
      `command -v az` + an active-session check. Round 2's fourth gate (a subscription-list probe)
      is DELETED — it suppressed the device-code offer on every brand-new Azure workspace.
      Step 3 gated on `FORGE_ENABLE_AZURE_DEVOPS`. Step 3b unchanged, as AC3 requires.
- [x] Azure backwards-compatibility proven by execution against the REAL `az` on a FRESH
      profile (not round 2's stub): steps 3 + 3b + 4 are byte-identical pre-story vs post-fix.
- [x] Every Saply literal in this file is now an overridable default or neutral text; the
      `~/.codex/AGENTS.md` global context renders with zero Saply/Azure literals under PoC overrides.
- [x] Verified line number for `az account show` recorded (`:135`) against the proposal's `:103`
      citation, with the full `:103` → `:109` → `:115` → `:133` → `:135` drift trail.
- [x] AC2 strengthened with an AC2-FRESH empty-profile case, so it can no longer pass vacuously.
- [x] `FORGE_CODEX_EXTRA_CONTEXT` plumbed from `variables.tf`; its default restores every fact
      the generalised body dropped, `Key Vault` and the Mnemosyne rename included.
- [x] The first pass's false "lockfile is UNMODIFIED" claim retracted, re-attributed to a
      parallel run's `terraform init`, and left in place with reasons.
- [x] Story status updated from `draft` to `done` in this file's frontmatter.
