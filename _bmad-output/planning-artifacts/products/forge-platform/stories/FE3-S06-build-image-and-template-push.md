---
type: story
epic: FE3
id: FE3-S06
title: "Clone forge-platform onto CT 167, docker build the workspace image, coder templates push"
size: M
priority: MUST
owner: dev
blocking: false
fr_refs: [FR-WS-008]
nfr_refs: []
adr_refs: []
risk_refs: [R5]
status: draft
date: 2026-09-09
---

# FE3-S06: Clone forge-platform onto CT 167, docker build the workspace image, coder templates push

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

As **tomamourette**, I want **the PoC branch of `forge-platform` cloned directly onto `ct-forge-01`, the workspace image built there with a local `docker build`, and `coder templates push` run against the running control plane**, so that **the last mile of "does Forge run at all on a substrate that is not Azure?" is actually exercised end-to-end, on the real host, rather than only validated in the abstract via `terraform validate`**.

## Background and Context

This is the closing story of FE3 and the direct prerequisite for FE4-S01 (first workspace create). Everything up to this point — FE3-S01 through FE3-S05 — has been branch edits authored and validated, but never actually built or pushed to a live coderd. This story is where those edits meet reality for the first time: `docker build` on the workspace `Dockerfile` (`repos/forge-platform/workspace/Dockerfile`, which already bakes Playwright + Chromium natively with an in-build smoke test at `:61-68`, per evidence **E1**) must actually complete on CT 167's hardware and Docker daemon (protected by FE2-S06's `daemon.json`/pin work), and `coder templates push` must successfully register the resulting template against the coderd instance FE2 stood up.

The task brief and the proposal's own effort estimate (§3.2: "Image build + template push + acceptance | M | includes at least one failed workspace build; assume it") are explicit that this is not expected to succeed cleanly on the first attempt, and that expectation should be treated as calibration, not as a lowered bar: **this story budgets for iteration**, but its Definition of Done is still an actual successful `coder templates push`, not merely an attempt. Likely first-pass failure classes, given everything gathered in FE0–FE3: a missed reference to the old ACR image name somewhere FE3-S01 didn't catch, a `terraform validate` pass that doesn't catch a runtime-only error (e.g., a `coder_parameter` value type mismatch only surfacing at `apply`), or a Docker build failure specific to CT 167's actual resource ceiling (4C/8GB per the current, still-open R4 sizing question) rather than a build-time image size problem.

Risk **R5** — nested-nested Docker on a ZFS-backed LXC rootfs is untested — is adjacent to this story but not resolved by it: this story's `docker build` runs on CT 167's **outer** Docker daemon (the one FE2-S06 configured), producing the workspace image. The **inner** dockerd-inside-a-privileged-workspace-container scenario that R5 actually concerns only exists once a workspace is *running* (FE4-S01), not during image build. This story's scope stops at a pushed template; ~~R5 remains open for FE4~~ **— R5 was CLOSED as DISPROVEN on 2026-09-09 by FE1-S05, which is earlier in the chain than this story expected.** Double-nested Docker was exercised on CT 167 and worked, with the inner daemon's overlayfs running **directly on the ZFS dataset** — no `vfs` fallback, no loopback image. This story's reasoning about *scope* is unaffected (an image build still runs on the outer daemon, and the inner-dockerd case still only exists once a workspace runs); only the "remains open" clause is stale. Gate (g) stays non-gating per ADR-003.

## Acceptance Criteria

**AC1 — forge-platform PoC branch present on CT 167.**
- **Given** CT 167 has network access to GitHub (via the developer's own credentials, not via the workspace-scoped Coder external-auth, since this is host-side setup, not a Forge workspace),
- **When** the operator runs `git clone` (or checks out an existing clone) of the forge-platform repo at the PoC branch containing FE3-S01 through FE3-S05's committed changes,
- **Then** `git log --oneline -5` on CT 167 shows those commits, and `git branch --show-current` confirms the PoC branch, not `main`.

**AC2 — Docker build completes.**
- **Given** AC1 has passed,
- **When** the operator runs `docker build -t forge-workspace:local repos/forge-platform/workspace/` on CT 167,
- **Then** the build completes with exit code 0, including the Playwright + Chromium smoke test baked into the Dockerfile (`workspace/Dockerfile:61-68`) passing as part of the build.

**AC3 — Local image matches what FE3-S01's `local.image` expects.**
- **Given** AC2 has passed,
- **When** the operator runs `docker images | grep forge-workspace`,
- **Then** the tag matches exactly what FE3-S01's `local.image` (or its replacement variable) references — a tag mismatch here is a common first-pass failure class per the proposal's own effort estimate.

**AC4 — `coder templates push` succeeds, WITH `--variables-file`.**
- **Given** AC1–AC3 have passed and the coderd control plane (FE2, all six stories) is running and reachable,
- **When** the operator runs `coder templates push forge -d coder/templates/forge --yes --variables-file coder/templates/forge/poc.tfvars` from CT 167, authenticated as the operator against the running coderd,
- **Then** the push succeeds, and `coder templates versions list forge` shows the newly pushed version as active.
- **The `--variables-file` flag is not optional and its omission does not fail.** Every `forge_*`
  variable defaults to the existing Azure/Saply deployment's value (that is the deliberate
  backwards-compatibility contract), so a push without it registers a template that boots fine and
  then writes `# Saply Forge Workspace` docs, names another company's repos and ADO projects, and
  offers an `az login` to a tenant this deployment has no relationship with. Confirm the file is
  actually present before pushing — `git ls-files coder/templates/forge/poc.tfvars` — because
  `coder templates push` uploads the directory as it is on disk and the file was authored
  uncommitted.
- **Then also**, if the Coder CLI rejects `forge_repo_catalogue` (an object-typed template
  variable, flagged Unverified in `docs/coder/setup.md`), record the exact error and fall back to
  the documented workaround (set its two markdown members to `""`) rather than dropping the whole
  variables file.

**AC4b — the pushed template is actually company-neutral (post-push assertion).**
- **Given** AC4 has passed,
- **When** the template's rendered output is inspected — at FE4-S01 from a workspace terminal, or
  immediately after the push via `terraform plan -var-file=coder/templates/forge/poc.tfvars` in the
  template directory,
- **Then** `grep -Eic 'saply|cv-engine|matching-(frontend|service|infrastructure)' ~/workspace/CLAUDE.md ~/workspace/repos/INDEX.md ~/.codex/AGENTS.md` returns `0` for every file, and
  `printenv FORGE_GITHUB_ORG FORGE_NPM_FEED_HOST FORGE_ONBOARD_TIMEOUT` shows `tomamourette`, an
  empty value, and `300`. A non-zero count or a Saply value means the push ran without
  `--variables-file`; re-push with it. The `printenv` half is not redundant: the scripts carry
  their own fallbacks to the Saply values, so it distinguishes "the override arrived" from "the
  fallback happened to look harmless".

**AC5 — At least one failure encountered and resolved, recorded honestly.**
- **Given** the proposal's own effort estimate budgets for "at least one failed workspace build,"
- **When** the operator works through AC1–AC4,
- **Then** whatever failures actually occurred (build errors, push errors, template validation errors caught only at this stage) are recorded in this story's evidence — including failures that were quickly fixed — rather than only reporting the final green state. A story that reports zero friction where the proposal explicitly predicted friction should be treated as suspicious, not as a good outcome.

## Implementation Notes

Reference FR-WS-008, §3.2 effort estimate ("includes at least one failed workspace build; assume it"), E1 (Playwright native image), R5 (scope boundary — this story does not exercise nested-nested Docker).

```bash
# AC1
cd ~/workspace  # on ct-forge-01
git clone <forge-platform-remote> repos/forge-platform
cd repos/forge-platform
git checkout <poc-branch-name>
git log --oneline -5
git branch --show-current

# AC2
docker build -t forge-workspace:local workspace/

# AC3
docker images | grep forge-workspace
grep -n 'local.image\|forge-workspace' coder/templates/forge/main.tf

# AC4 — the --variables-file flag is required; without it the PoC gets Saply-branded docs
git ls-files coder/templates/forge/poc.tfvars   # must print the path, not nothing
coder login https://forge.bi-services.be
coder templates push forge -d coder/templates/forge --yes \
  --variables-file coder/templates/forge/poc.tfvars
coder templates versions list forge

# AC4b — post-push assertion (run in the template dir, or from a workspace terminal at FE4-S01)
terraform plan -var-file=coder/templates/forge/poc.tfvars   # must not error on forge_repo_catalogue
# from a workspace terminal:
grep -Eic 'saply|cv-engine|matching-(frontend|service|infrastructure)' \
  ~/workspace/CLAUDE.md ~/workspace/repos/INDEX.md ~/.codex/AGENTS.md   # every count must be 0
printenv FORGE_GITHUB_ORG FORGE_NPM_FEED_HOST FORGE_ONBOARD_TIMEOUT
```

## Test Plan

**Pre-state:** FE0–FE2 complete (coderd + Postgres + Caddy/TLS running); FE3-S01 through FE3-S05 committed on the PoC branch but never built or pushed; nothing yet cloned onto CT 167 itself.

**Action sequence:**
1. Clone the PoC branch onto CT 167 (AC1).
2. `docker build` the workspace image (AC2); iterate on any build failures, recording each (AC5).
3. Confirm the built image's tag matches the template's `local.image` reference (AC3); fix any mismatch.
4. `coder templates push` **with `--variables-file coder/templates/forge/poc.tfvars`** (AC4); iterate on any push/validation failures, recording each (AC5).
5. Confirm the new template version is listed as active.
6. Run the AC4b post-push assertion so an omitted `--variables-file` fails loudly here rather than
   silently Saply-branding the PoC workspace at FE4-S01.

**Post-state checks:**
- `docker images` shows the built image with the expected tag.
- `coder templates versions list forge` shows the new version active.
- This story's evidence section (added at execution time, not in this authored draft) lists every failure encountered and its fix — even ones resolved in under a minute.

**Rollback:** `coder templates push forge -d <previous-known-good-dir> --yes` reverts the active template version if the new push causes problems for existing workspaces (none exist yet at this point in the sequence, so rollback risk is effectively zero for this specific story). `docker rmi forge-workspace:local` removes the built image if a clean re-build is needed.

## Dependencies

- **Blocked by:** FE2-S01 through FE2-S06 (running coderd + Postgres + Caddy/TLS + safe Docker daemon config), FE3-S01 through FE3-S05 (all template edits and the intellij_gateway decision must be committed on the PoC branch first — this story builds and pushes *that* branch, not an earlier state of it).
- **Blocks:** FE4-S01 (first workspace create needs an active, pushed template).

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Docker build fails on CT 167's actual resource ceiling (4C/8GB, R4 still open) rather than any code defect | Medium | Medium — could be mistaken for a template bug and debugged in the wrong place | AC5's honest-recording requirement should distinguish "build logic error" from "resource-starved build" failures explicitly |
| `coder templates push` succeeds but silently registers a broken template (e.g., a `coder_parameter` type error only surfaces at workspace *create* time, not push time) | Medium | Medium — false confidence carried into FE4-S01 | AC4 checks `templates versions list`, but this story does not create a workspace — FE4-S01 is where a push that "succeeded" but is actually broken gets caught; document that distinction so FE3-S06's green state isn't over-claimed |
| Nested-nested Docker (R5) gets conflated with this story's plain `docker build`, leading to a false belief that R5 was tested here | Low | Low if caught, Medium if not (an unverified risk gets marked resolved by mistake) | Background and Context section explicitly scopes R5 out of this story; FE4-S01/FE4-S02 gate (g) is where it's actually exercised |

## Definition of Done

- [ ] AC1–AC5 all green and evidenced, including an honest record of any failures encountered along the way.
- [ ] `forge-workspace:local` image built successfully on CT 167.
- [ ] `coder templates push` succeeded **with `--variables-file coder/templates/forge/poc.tfvars`**; new version active in `coder templates versions list forge`.
- [ ] AC4b post-push assertion green: no company literals in the rendered workspace docs, and `printenv` shows this deployment's `FORGE_*` values.
- [ ] R5 explicitly noted as still unverified by this story (deferred to FE4).
- [ ] Story status updated from `draft` to `done` in this file's frontmatter.
