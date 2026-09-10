---
type: product-index
product: forge-platform
version: 1.0.0
status: planning-complete-implementation-blocked
date: 2026-09-09
source_proposal: ../../sprint-change-proposal-2026-09-09.md
---

# Forge Platform — Product Index

> A **proof of concept**, not a platform. Forge is today an Azure-only developer platform built for
> one company (Saply AI). Before any productisation is planned, one question has to be answered
> empirically: **does Forge run at all on a substrate that is not Azure?** This product stands up
> Coder + Postgres 16 + the Forge workspace template + the agentic-ai toolkit on a single Proxmox
> LXC (**CT 167, `ct-forge-01`, pve3, 4C/8GB/50GB, Debian 13, `features=nesting=1,keyctl=1`,
> 192.168.50.167**) and produces one dated, falsifiable verdict:
> **PORTS / PORTS-WITH-CAVEATS / DOES-NOT-PORT**.
>
> **Hermes, OpenMemory and Langfuse are explicitly out of scope.** They carry nearly all of the
> Azure coupling and none of them is needed to answer the question (ADR-006).

## Status

- **Source of authority:** `sprint-change-proposal-2026-09-09.md`, **approved as written 2026-09-09**.
- **Phase complete:** planning artifacts (Brief → PRD → Architecture → ADRs → Epics → Stories →
  Acceptance → E2E → Readiness → Sprint plan), authored per §4.1 and §4.2 of the proposal.
- **Readiness check:** **PASS-WITH-NOTES** (34 PASS / 1 PASS-WITH-NOTES / 0 FAIL).
- **Implementation gate:** **NO-GO.** FE0 may start now; **nothing in FE1–FE4 starts** until the
  three blockers below clear.
- **Artifacts:** 15 top-level and test documents + 6 ADRs + 27 stories = **41 files, ~7,560 lines**.
- **Total effort:** **M–L — two to four working sessions** (t-shirt **estimate, not a commitment**),
  *if the operator prerequisites land first*. **No story points are asserted anywhere.**
- **Tracking file:** `implementation-artifacts/sprint-status-forge-platform.yaml` — a **separate**
  file per §6.1. The existing `sprint-status.yaml` is deliberately untouched (§6.2 fallback not
  taken).

## ⛔ Three blockers before FE1 starts

| # | Blocker | Owner | Why it is hard-blocking |
|---|---|---|---|
| 1 | **GitHub OAuth App** → `CODER_EXTERNAL_AUTH_0_ID/TYPE/CLIENT_ID/CLIENT_SECRET` (FE0-S01) | **Operator only** | The **only non-optional external credential in the whole PoC.** `data "coder_external_auth" "github"` (`coder/templates/forge/main.tf:25-27`) lacks `optional = true`, so the **workspace build fails** without it — and even if it passed, `forge-sync.sh` sources its token from `coder external-auth access-token github` and **silently skips its entire clone block**, so agentic-ai never lands and gates (b)–(e) are untestable. |
| 2 | **Cloudflare API token**, DNS-edit scope, zone `bi-services.be` (FE0-S02) | **Operator only** | Required for **any** browser-trusted certificate. The homelab has no inbound :80/:443, so HTTP-01 is **impossible**, not merely inconvenient. ~~Wildcard scope is **optional** (`coder_app "code_server"` is `subdomain = false`)~~; the token is **not**. **Amended 2026-09-09 — the wildcard clause is REVERSED and a wildcard IS required**: `code_server` is `subdomain = false`, but Coder's preview URLs are subdomain-based and `CODER_WILDCARD_ACCESS_URL=*.forge.bi-services.be` is live on CT 167, so the certificate carries both `forge.bi-services.be` and `*.forge.bi-services.be`. The token clause is unaffected — one `Zone.DNS Edit` grant still covers both names, no re-scoping. See [ADR-005](adrs/ADR-005-dns-01-wildcard-over-public-ingress.md). |
| 3 | **The sizing decision (R4)** — **UNRESOLVED** | **Operator capacity call against pve3** | The template's `coder_parameter` defaults are **12288 MB RAM** (`main.tf:62`) and **20480 MB swap** (`main.tf:77`). They are `coder_parameter`, **not** `variable`, so a `--variables-file` **cannot** lower them; `min = 2048` and `mutable = true` mean an operator *can* choose smaller, but only by remembering to, every time. Swap has **no answer inside an unprivileged LXC** — the CT gets whatever `swap_mb` Terraform set, and `modules/ct-debian` defaults it to **512 MB**. Two candidate resolutions, **neither chosen**: (a) four real `variable`s driving both defaults and validation maxima **plus** `swap_mb = 8192`; or (b) size CT 167 at **4C/12GB**. **Approval of the proposal explicitly did not settle this.** It blocks **FE1-S01**. |

## At a Glance

| Layer | What it is | Epic | Size (est.) |
|---|---|---|---|
| Prerequisites | Two operator credentials + three repo-state corrections | **FE0** | S |
| Substrate | CT 167 on the standard project-CT runbook; HA to **both** peers; privilege measurement | **FE1** | S |
| Control plane | coderd (pinned `.deb`) + Postgres 16 (no extensions) + the six-empty-file secrets seam + static Caddy with DNS-01 + `daemon.json` and a Docker pin | **FE2** | M |
| Workspace | forge-platform **branch** (never a fork): local image build, four real `variable`s, Saply heredocs replaced, `forge-sync.sh` parameterised, Azure blocks gated | **FE3** | M |
| Toolkit + verdict | First workspace, eleven gates from a tailnet client, PBS backup, one explicit verdict, retrospective | **FE4** | M |

## Artifact Index

### Discovery
- **[product-brief.md](product-brief.md)** (244 lines) — vision, the Azure-only/Saply-coupled problem, PoC scope (in/out), success measures, and `docs/forge-reuse-and-proxmox-findings.md` as prior art.

### Requirements
- **[prd.md](prd.md)** (491 lines) — **28 FRs** (PRE ×6, SUB ×7, CTL ×7, WS ×9, KIT ×6) + **11 NFRs** (SEC/IAC/DISP/CAP/OBS/PORT); the eleven acceptance gates; §8 out-of-scope; §9.1 the blocking prerequisites; §10 risks R1–R8; **§11 the five open decisions**.

### Architecture
- **[architecture.md](architecture.md)** (345 lines) — CT 167 topology, the `/opt/coder/secrets` contract, the two-Terraform-roots principle, the Azure→self-hosted substitution table (E5), what is deliberately absent and why, and five open architectural questions.
- **[adrs/](adrs/)** (6 ADRs, 791 lines):
  - [ADR-001](adrs/ADR-001-lxc-over-vm-for-forge-poc.md) — Unprivileged LXC over a Proxmox VM. **Reversal trigger: a second untrusted user.** Records honestly that it overturns the prior document's VM recommendation, and which two of its four arguments survive as risks.
  - [ADR-002](adrs/ADR-002-privileged-workspace-accepted-for-single-operator.md) — `privileged = true` accepted for a single operator; the measured blast radius; the exact revisit trigger.
  - [ADR-003](adrs/ADR-003-nested-docker-is-not-an-acceptance-gate.md) — Nested Docker has zero automated consumers; gate (g) is **non-gating**, recorded either way.
  - [ADR-004](adrs/ADR-004-sysbox-rejected-and-the-docker-29-5-0-trap.md) — Sysbox rejected on three independent grounds; the real cause is the Docker 29.5.0 time-namespace flip, and the fix is a `daemon.json` flag **plus** a version pin.
  - [ADR-005](adrs/ADR-005-dns-01-wildcard-over-public-ingress.md) — DNS-01 over public ingress; token mandatory. ~~wildcard optional~~ → **wildcard REQUIRED, amended 2026-09-09** (Coder preview URLs are subdomain-based). **Records that "ADR-010" does not exist** and cites the wiki policy instead.
  - [ADR-006](adrs/ADR-006-hermes-openmemory-langfuse-out-of-poc-scope.md) — The deferral, **with re-entry conditions**: FE4-S05 only.

### Epics and Stories
- **[epics.md](epics.md)** (473 lines) — FE0–FE4 with goal / scope / dependencies / epic ACs / exit gate / FR coverage / risk map. **28/28 FR coverage, no orphans.**
- **[stories/](stories/)** (**27 INVEST stories**, 3,808 lines, frontmatter-tagged, t-shirt sized):
  - **FE0** ×5 — GitHub OAuth App **[BLOCKING]**, Cloudflare token **[BLOCKING]**, pin `FORGE_AGENTIC_AI_REF`, fix the sysbox comment drift, neutralise the VMID 166 phantom.
  - **FE1** ×5 — Terraform module + outputs (explicit `swap_mb`), targeted plan/apply, HA to both peers via the roles, inventory/host_vars/`dev-host`, re-run the privilege measurement.
  - **FE2** ×6 — `forge-coder-host` role, Postgres 16, six empty secrets files, `coder.env`, static Caddy + DNS-01, `daemon.json` + Docker pin.
  - **FE3** ×6 — local image + four `variable`s, Saply heredocs + `repo_deny`, `forge-sync.sh`, `forge-onboard.sh` gating, the `intellij_gateway` decision, build + template push.
  - **FE4** ×5 — first workspace, the eleven gates, PBS backup, **the verdict**, retrospective + next-phase decision.
  - **Every FE1–FE4 story carries the blocking-prerequisites banner.** FE1-S01 carries a second banner for the unresolved sizing decision.

### Test Strategy
- **[tests/acceptance.md](tests/acceptance.md)** (475 lines) — the eleven gates a–k in full with concrete commands and expected results, the per-epic AC index, cross-cutting categories, and the coverage audit.
- **[tests/e2e-deployment.md](tests/e2e-deployment.md)** (434 lines) — the end-to-end runbook (CT create → HA → dev-host → coder-host → image build → template push → first workspace → gates), five failure scenarios mapped to the named risks, and the rollback path.

### Readiness
- **[readiness-check.md](readiness-check.md)** (188 lines) — **PASS-WITH-NOTES**; 34 PASS / 1 PASS-WITH-NOTES / 0 FAIL; **implementation NO-GO** pending the three blockers.

### Sprint plan
- **[sprint-plan.md](sprint-plan.md)** (310 lines) — session-by-session (not calendar) plan with consolidated decision gates **G0–G5**. No dates are asserted, because the start depends on when the credentials land.

## Key Decisions (full rationale in the ADRs)

1. **Unprivileged LXC, not a VM** (ADR-001) — `modules/vm-dev` has never been applied and is broken in four documented ways; the isolation premium a VM buys is priced for untrusted users, who do not exist here. **Revisit on a second untrusted user.**
2. **`privileged = true` accepted for one operator** (ADR-002) — the blast radius ends at root *inside the LXC*, which the workspace user already holds via passwordless sudo. The cost is a **future** cost.
3. **Nested Docker is not an acceptance gate** (ADR-003) — zero automated consumers across 211 skills; dockerd failure is soft by construction; Playwright is native to the image.
4. **Sysbox rejected; the Docker 29.5.0 trap pinned** (ADR-004) — the failure **cannot reproduce today** on Docker 29.3.1 and **will** appear after the next `apt upgrade`. `daemon.json` **plus** a version pin, or it breaks on an unrelated maintenance day.
5. **DNS-01, no public ingress** (ADR-005) — an outbound API call, consistent with `homelab-playbook/wiki/architecture/tailscale-policy.md:20-31` and `wiki/architecture/remote-access-topology.md`. **There is no "ADR-010" in this estate.**
6. **Hermes / OpenMemory / Langfuse out** (ADR-006) — with explicit re-entry conditions at FE4-S05.
7. **A separate sprint-status file** (§6.1) — mixing a second product into `sprint-status.yaml` would repeat the `environments/`-means-tenant overloading identified as finding A7.
8. **The prior findings document is reconciled, not superseded** (§3.4) — most of it stands; it is overturned on one structural recommendation and one causal explanation.

## FE0 Kickoff Cheat-Sheet

Nothing here needs infrastructure. Every box must tick before FE1-S01.

1. **Create the GitHub OAuth App**; record `CODER_EXTERNAL_AUTH_0_ID/TYPE/CLIENT_ID/CLIENT_SECRET`; confirm the grant covers `tomamourette/agentic-ai`. (FE0-S01 — **operator, blocking**)
2. **Mint the Cloudflare API token**, DNS-edit scope, zone `bi-services.be`; store it 0600 root-owned. (FE0-S02 — **operator, blocking**)
3. **Take the sizing decision** — option (a) four `variable`s + `swap_mb = 8192`, or option (b) 4C/12GB. Record which and why. (§11.1 of the PRD; **blocks FE1-S01**)
4. Add `optional = true` to `data "coder_external_auth" "github"` (`main.tf:25-27`) so a missing grant degrades to a visible skip. (FE0-S01, recommended alongside)
5. Pin `FORGE_AGENTIC_AI_REF` to a **tag** in `coder_agent.main.env` (`main.tf:160-162`). (FE0-S03)
6. Fix the sysbox comment drift before anyone reads `main.tf:399-404` and ports the wrong architecture. (FE0-S04)
7. Stash or exclude the uncommitted `ct_sparkle_vlabel` (VMID 166) block and decide its fate — a bare apply would recreate a container destroyed on 2026-07-28. (FE0-S05)
8. Confirm **167** is still the next free VMID in the 162–169 project block.
9. Re-read `homelab-playbook/wiki/runbooks/create-project-container.md` — FE1 follows it verbatim, including the "narrowly `-target` the plan" and "replicate to **both** peers" pitfalls.
10. Commit `docs/forge-reuse-and-proxmox-findings.md` with a dated header pointing at the proposal (R3 — an untracked 352-line analysis is one `git clean` from gone). *This is a proposal §4.3 action, not a story.*

**G0 GO criterion:** items 1, 2 and 3 all done. **Nothing in FE1–FE4 starts otherwise.**

## Open Items Needing Operator Input

1. **The sizing decision (R4)** — 4C/8GB with template variables and `swap_mb = 8192`, or 4C/12GB. **Blocks FE1-S01. Approval did not settle it.**
2. **`ct:167` HA state** — `started` or `stopped` under the Project-CT HA Policy, decided against pve1's unresolved hard-hang history (R6). *Replication to both peers is not open — it is required.*
3. **`intellij_gateway`** — keep it (registry.coder.com egress on every workspace build) or remove it. `terraform validate` fails while undecided (FE3-S05).
4. **The fate of `ct_sparkle_vlabel`** — stashing is required; deletion vs retention is the operator's call (FE0-S05).
5. **Whether to open productisation after the verdict** — FE4-S05, and **only** FE4-S05 (R8).

## Known Unknowns

- **Double-nested Docker on a ZFS-backed LXC rootfs is untested in this estate (R5).** The workspace's inner dockerd writes to `docker_volume.dockerd`, which on CT 167 lives on the **outer** Docker's data root on the LXC's ZFS rootfs. Docker on ZFS works and **one** nesting level is proven; **two levels is not**. Mitigated but not removed by ADR-003 — gate (g) is non-gating, so a failure degrades the PoC rather than ending it. **No artifact in this set claims it will work.**
- **That CT 250's privilege measurement transfers to Debian 13 with `keyctl=1` is `[I]` inferred, not verified.** FE1-S05 exists to convert it.
- **The prior findings document's citations outside the seven files spot-checked this pass are `[I]`** and should be treated as approximately-correct rather than exact.

## Maintenance Note

This product is BMAD-tracked. Future updates should:
- Update `implementation-artifacts/sprint-status-forge-platform.yaml` as stories move; leave `sprint-status.yaml` alone.
- Add ADRs (ADR-007+) for any architectural decision taken during execution — in particular, the sizing decision deserves one once it is made.
- Mark each completed story `status: done` in its frontmatter.
- Record the verdict in `poc_verdict:` in the sprint-status file **and** in FE4-S04.
- Add a `ct-forge-01` project page to `homelab-playbook/wiki/` after the PoC concludes (proposal §4.3).

## Related

- **Source of authority:** [`../../sprint-change-proposal-2026-09-09.md`](../../sprint-change-proposal-2026-09-09.md) — approved 2026-09-09.
- **Prior art:** `docs/forge-reuse-and-proxmox-findings.md` (2026-07-30, 352 lines, untracked, written against `forge-platform @ e025bc5` / `agentic-ai @ ff02e19`). Reconciled, not superseded.
- **Estate policy:** `homelab-playbook/wiki/architecture/tailscale-policy.md`, `wiki/architecture/remote-access-topology.md`.
- **Implementation vehicle:** `homelab-playbook/wiki/runbooks/create-project-container.md`.
- **Structural precedent:** [`../context-stack/`](../context-stack/) and [`../doc-system/`](../doc-system/).
- **Repos read this pass:** `repos/forge-platform @ 2b27a95`, `repos/agentic-ai @ 87ec24a`.
