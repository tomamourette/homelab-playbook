---
type: sprint-plan
product: forge-platform
version: 1.0.0
status: draft
date: 2026-09-09
brief_ref: product-brief.md
prd_ref: prd.md
arch_ref: architecture.md
epics_ref: epics.md
acceptance_ref: tests/acceptance.md
e2e_ref: tests/e2e-deployment.md
proposal_ref: ../../sprint-change-proposal-2026-09-09.md
---

# Forge Platform — Sprint Plan

## 1. Overview

This is not a calendar sprint plan. The proposal's unit of work (§4.1) is a **working session**, not a
two-week sprint, and its effort table (§3.2) sizes the whole PoC at **M–L, two to four working
sessions — if the operator prerequisites land first.** This document sequences the five frozen epics
(FE0–FE4) into a session map; each session gets a goal, a backlog, an ordered plan, risks, a
Definition of Done, a decision gate, and demo artifacts.

**No calendar dates are asserted beyond `2026-09-09`**, the date of the approved proposal. Session 1's
start depends entirely on when the two §5.4 operator prerequisites land — not knowable from inside
this document. All sizes are **t-shirt estimates (S/M/L) or session ranges, explicitly not
commitments**, per §3.2/§4.2 of the proposal. No story points or velocities appear anywhere here.

Session, not sprint, because: the PoC is single-operator side-project effort, not a team cadence; two
epics (FE0, FE1) are individually smaller than a session and may compress rather than forcing five
sessions where four suffice; and a session boundary is the natural checkpoint for a solo operator — it
ends with something demonstrable, and the next session waits on its gate.

## 2. Session map

| Session | Epic(s) | Size | Focus | Note |
|---|---|---|---|---|
| **Session 0** | FE0 | S | Prerequisites and truth — two blocking operator credentials, plus three small code/decision fixes | Mostly operator time. Gates everything downstream (G0). |
| **Session 1** | FE1 (+ possibly part of FE2) | S | Substrate — CT 167 on the established project-CT pattern | Estimated "half a session; the runbook is stable and rehearsed 4×" (§3.2). May absorb early FE2 stories (FE2-S01, FE2-S02) into the same sitting rather than force an artificial break. |
| **Session 2** | FE2 | M | Control plane — Coder + Postgres 16 + TLS | One of the two M-sized bodies most likely to overflow; DNS-01 + Caddy is the likely source. |
| **Session 3** | FE3 | M | Workspace — template de-Azured, building locally | The other M-sized body most likely to overflow; §3.2: image build + template push "includes at least one failed workspace build; assume it." |
| **Session 4** | FE4 | M | Toolkit and acceptance | Ends in a published verdict, not just a working system. |

Total: **M–L, two to four working sessions** (§3.2), contingent on FE0's prerequisites landing before
Session 1 and on how much FE1/FE2 and FE3/FE4 actually compress. Four sessions is the working
assumption; two is the best case. Neither compression is asserted as fact.

## 3. Session 0 — FE0: Prerequisites and truth

**Session Goal:** both blocking operator prerequisites exist and are recorded, and three
load-bearing-but-non-blocking fixes (agentic-ai ref pin, sysbox comment drift, the VMID 166 phantom)
are resolved before any Terraform plan touches the homelab root.

**Backlog** (epic size **S**, mostly operator not code):

| Story | Title | Notes |
|---|---|---|
| FE0-S01 | Create the GitHub OAuth App; record `CODER_EXTERNAL_AUTH_0_*`; verify the grant covers `tomamourette/agentic-ai` | **[operator, BLOCKING]** |
| FE0-S02 | Mint the Cloudflare DNS-edit token scoped to `bi-services.be` | **[operator, BLOCKING]** |
| FE0-S03 | Pin `FORGE_AGENTIC_AI_REF` to a tag in `coder_agent.main.env` (`main.tf:160-162`) | |
| FE0-S04 | Fix sysbox comment drift: `main.tf:399-404`/`:559-566`, `docs/coder/setup.md:149-156`, `docs/coder/orchestration-adr.md` | |
| FE0-S05 | Stash or exclude the uncommitted `ct_sparkle_vlabel` (VMID 166) block; decide its fate | Fate is an **open operator decision** |

**Ordered plan:** (1) FE0-S01/FE0-S02 first — pure operator actions, block everything else; (2)
FE0-S05 before any Terraform touch, so no later plan/apply risks recreating a destroyed container; (3)
FE0-S03/FE0-S04 any time, in either order or in parallel with the credentials — different repos, no
dependency.

**Risks:** R7 — do not cite "ADR-010"; the real citations are
`wiki/architecture/tailscale-policy.md:20-31` and `wiki/architecture/remote-access-topology.md`. R1 —
FE0-S04 is the direct mitigation for the comment-drift trap. The R4 sizing conflict is **not** an FE0
risk to resolve here, but it is a hard prerequisite to Session 1 (see G0).

**Session DoD:** credentials recorded and grant verified; ref pinned to a tag; comment drift corrected
in both code locations and both docs; `ct_sparkle_vlabel` fate decided and acted on.

**Decision Gate — G0 (before Session 1 opens):** GO only if both operator prerequisites exist **and**
the operator has made the R4/R1 sizing decision (four `variable`s + `swap_mb = 8192`, or a 4C/12GB
CT). This plan does not make that decision — it is a hard stop until the operator does. NO-GO
otherwise; nothing in FE1–FE4 starts.

**Demo artifacts:** recorded credentials (redacted) and grant scope; diff showing the comment-drift
fix and ref pin; a one-line record of the `ct_sparkle_vlabel` decision.

## 4. Session 1 — FE1: Substrate

**Session Goal:** CT 167 (`ct-forge-01`) exists on pve3 via the established pattern, is under HA
replication to both peers, has completed `dev-host-setup.yml`, and the E2 privilege measurement has
been re-run and recorded for this specific CT.

**Backlog** (epic size **S** — "half a session; the runbook is stable and rehearsed 4×"):

| Story | Title | Notes |
|---|---|---|
| FE1-S01 | Terraform module block + `outputs.tf` registration; **set `swap_mb` explicitly** | Blocked on the G0 sizing decision |
| FE1-S02 | Narrow `-target`ed plan; verify only the expected resources; apply | |
| FE1-S03 | HA: replication jobs `167-0`/`167-1` (both peers) + `standard` rule membership, **via the Ansible roles only** | `started`/`stopped` is an **operator call** |
| FE1-S04 | Inventory + `host_vars/ct-forge-01/main.yml` with `project_name`; run `dev-host-setup.yml` | Missing `project_name` aborts `dev-host` mid-run |
| FE1-S05 | Re-run the E2 privilege measurement on CT 167 (Debian 13, `keyctl=1`); record the result | CT 250's result is `[I]` for this CT until re-run |

**Ordered plan:** FE1-S01 (gated on G0's sizing decision) → FE1-S02 (targeted plan, then apply, never
bare) → FE1-S03 (HA, once the CT exists) → FE1-S04 (inventory/host_vars, then `dev-host-setup.yml`) →
FE1-S05 last, against the fully-provisioned CT. If time remains, low-risk early FE2 stories (FE2-S01,
FE2-S02) may be pulled forward, per §2 — only once FE1's own DoD is met.

**Risks:** R4/R1 — FE1-S01 executes the G0 decision; `swap_mb` must be set explicitly either way, since
the `ct-debian` module default (512 MB) is too small regardless. R6 — the 3-node `standard` rule while
pve1's reliability is unresolved; replication to both peers is non-negotiable, but `started`/`stopped`
is an explicit open call at FE1-S03. Runbook pitfalls carried forward: a bare `plan` drags in unrelated
DNS drift (mitigated by `-target`); a missing `project_name` aborts `dev-host` after the `developer`
user is created but before SSH keys are seeded (mitigated by ordering).

**Session DoD:** targeted `plan` clean; `ha-manager status` shows `ct:167` in the chosen state with
both replication jobs present; `dev-host-setup.yml` completes; E2 measurement re-run and recorded
(any result).

**Decision Gate — G1 (after FE1):** GO only if `terraform plan` is clean apart from the intended CT
and `ct_sparkle_vlabel` has not been recreated (gate j, run early); `ha-manager status` + both
replication jobs are present (gate k, run early); the FE1-S05 measurement is recorded — any result
passes, an unrecorded one does not.

**Demo artifacts:** targeted `plan`/`apply` output; `ha-manager status` and replication.cfg excerpt;
E2 re-measurement notes.

## 5. Session 2 — FE2: Control plane

**Session Goal:** Coder's control plane runs on CT 167 against local Postgres 16, behind Caddy on a
browser-trusted DNS-01 certificate, with the secrets contract in place and the Docker 29.5.0 trap
pre-empted.

**Backlog** (epic size **M**):

| Story | Title | Notes |
|---|---|---|
| FE2-S01 | `forge-coder-host` Ansible role: coderd from a checksum-verified pinned `.deb` | |
| FE2-S02 | Local Postgres 16 + role + database (no extensions) | `pgvector` is OpenMemory-only; out of scope |
| FE2-S03 | `/opt/coder/secrets` 0700 with **six empty 0600 files**; no mnemosyne pair | |
| FE2-S04 | `/etc/coder.d/coder.env`, OIDC/ADO blocks dropped; password auth on | |
| FE2-S05 | Caddy: **static** site block + DNS-01 via `caddy-dns/cloudflare`; token as a 0600 root `EnvironmentFile` | No `on_demand_tls`, no ask-server on `:9111` |
| FE2-S06 | `daemon.json` with `{"features":{"time-namespaces":false}}` **and** a Docker version pin | Pre-empts R2 |

**Ordered plan:** FE2-S01/FE2-S02 in either order or interleaved (independent packages) → FE2-S03
before FE2-S04 (coder.env expects the secrets contract to exist) → FE2-S04 before first coderd start →
FE2-S05 once coderd is reachable locally → FE2-S06 at any point, but land it before any `apt upgrade`
touches this host.

**Risks:** R2 — FE2-S06 is the direct mitigation for the Docker 29.5.0 trap; slipping it leaves the
host exposed to a future unrelated upgrade with a misleading symptom. NFR-SEC-003 — Cloudflare token
and OAuth secret stored 0600 root-owned, never committed. DNS-01 + Caddy is the most likely source of
session overflow (first-certificate issuance often needs a retry).

**Session DoD:** coderd running, backed by local Postgres 16; secrets dir exactly six empty 0600
files, no mnemosyne pair; `coder.env` has no OIDC/ADO, password auth works; Caddy serves
`forge.bi-services.be` via DNS-01; `daemon.json` + Docker pin in place.

**Decision Gate — G2 (after FE2):** GO only if a browser-trusted certificate is presented for
`forge.bi-services.be` with no warning from a tailnet client not on the LAN (gate a, partial — code-
server itself is exercised later); Coder accepts a password-auth login; `daemon.json` and the Docker
pin are both in place.

**Demo artifacts:** certificate chain evidence for `forge.bi-services.be`; `coder.env` (redacted) and
secrets-dir listing; `daemon.json` contents and the pinned package version.

## 6. Session 3 — FE3: Workspace

**Session Goal:** the forge-platform workspace template builds and pushes from CT 167 with no Azure
dependency and no registry pull, generalised past Saply AI, with the sizing knobs and the
`intellij_gateway` question both resolved in code (the sizing *values* remain the G0 operator call).

**Backlog** (epic size **M**):

| Story | Title | Notes |
|---|---|---|
| FE3-S01 | forge-platform branch: `local.image` → local build; four new `variable`s driving both the `coder_parameter` defaults and their validation maxima | Code side of the G0 sizing decision |
| FE3-S02 | Replace the two Saply heredocs (`main.tf:171-270`); add `company-overlay` to `local.repo_deny` | Fixes the double-clone |
| FE3-S03 | Parameterise `forge-sync.sh` (org, repos, ADO block), preserving per-repo flags and failure messages | |
| FE3-S04 | Gate the Azure blocks in `forge-onboard.sh`, including `:103` `az account show` | Otherwise prompts a login of a binary that will not exist |
| FE3-S05 | Decide `intellij_gateway`: keep (registry.coder.com egress per build) or remove | **Open operator decision** — `terraform validate` fails while undecided |
| FE3-S06 | Clone forge-platform onto CT 167; `docker build`; `coder templates push` | |

**Ordered plan:** FE3-S01 first (highest-risk edit, no dependents) → FE3-S02 + FE3-S03 together (same
generalisation pass, adjacent code) → FE3-S04 → FE3-S05 before FE3-S06 (`terraform validate` blocks on
it — cannot be deferred) → FE3-S06 last, once `validate` is clean.

**Risks:** R5 — nested-nested Docker on ZFS surfaces at first workspace boot in FE4, but FE3-S06's
`docker build` is the first touch of the image that will exercise it; carried forward, non-gating per
ADR-003. §3.2's own estimate assumes at least one failed workspace build. FE3-S05 left undecided is a
hard blocker, not a soft risk.

**Session DoD:** `terraform validate` clean (implies FE3-S05 decided); image builds locally, no
registry pull; no Saply heredoc content remains, `company-overlay` in `repo_deny`; `forge-onboard.sh`
no longer calls Azure CLI unconditionally; `coder templates push` succeeds.

**Decision Gate — G3 (after FE3):** GO only if `coder templates push` succeeds and `intellij_gateway`
has been explicitly decided (not merely passing validation by omission).

**Demo artifacts:** `terraform validate` output; `docker build` log (including the assumed first
failure and its resolution, if any); `coder templates push` output; the `intellij_gateway` decision
with rationale.

## 7. Session 4 — FE4: Toolkit and acceptance

**Session Goal:** a first real workspace exists, all eleven acceptance gates have been run and
recorded from a tailnet client not on the LAN, CT 167 is backed up, and a single explicit PoC verdict
is published.

**Backlog** (epic size **M**):

| Story | Title | Notes |
|---|---|---|
| FE4-S01 | First workspace create; agentic-ai reaches the workspace via the GitHub token | |
| FE4-S02 | Run the acceptance gates (§5.3, a–k); record every result including failures | |
| FE4-S03 | PBS backup of CT 167 to pve3-pbs | |
| FE4-S04 | PoC verdict: PORTS / PORTS-WITH-CAVEATS / DOES-NOT-PORT, caveats enumerated | |
| FE4-S05 | Retrospective; decide whether to open a productisation phase or stop | **The only point** productisation may be opened (R8) |

**Ordered plan:** FE4-S01 (precondition for every workspace-dependent gate) → FE4-S02 (all eleven
gates, including non-gating gate (g) and gate (h), the measured resolution of R4) → FE4-S03 (any time
after FE4-S01, before closing the PoC, to actually exercise NFR-DISP-001) → FE4-S04 only once FE4-S02
is fully complete → FE4-S05 last.

**Risks:** R8 — the single highest-likelihood, highest-cost risk in the whole plan (§9); FE4-S05 is a
hard gate against deciding tenancy/OpenMemory/Hermes early. Gate (h) is where R4 gets its real,
measured answer. Gate (g) failing (R5) is not a session failure — non-gating by design (ADR-003).

**Session DoD:** workspace created, agentic-ai present via the GitHub token; all eleven gates recorded
(pass/fail/caveat, none silently skipped); CT 167 backed up; verdict published; retrospective held with
an explicit go/stop call.

**Decision Gate — G4 (after FE4-S02, before the verdict):** GO to FE4-S04 only if all eleven gates
have a recorded result, whatever it is. A verdict written against a partial gate run does not satisfy
this plan.

**Decision Gate — G5 (at FE4-S05):** the **only** point in the entire plan where productisation
(tenancy cut, OpenMemory, Hermes) may be opened. Opening it earlier is exactly the R8 failure mode this
plan exists to prevent.

**Demo artifacts:** the completed gate table (a–k); the PBS backup record; the published verdict; the
retrospective notes and go/stop decision.

## 8. Decision gates, consolidated

| Gate | When | Criteria | If not met |
|---|---|---|---|
| **G0** | Before Session 1 | Both §5.4 prerequisites (GitHub OAuth App; Cloudflare DNS-edit token) exist **and** the operator has made the R4 sizing decision. The conflict: the template's `coder_parameter` defaults are **12288 MB RAM** (`coder/templates/forge/main.tf:62`) and **20480 MB swap** (`main.tf:77`); they are `coder_parameter` and **not** `variable`, so a `--variables-file` cannot lower them, and swap has no answer inside an unprivileged LXC whose `swap_mb` defaults to **512 MB** (`modules/ct-debian/variables.tf:30-33`). Resolutions: **(a)** four real `variable`s driving both defaults and validation maxima **plus** `swap_mb = 8192`, or **(b)** size CT 167 at **4C/12GB**. **Neither is chosen; approval did not settle it.** | **NO-GO.** The plan's only true hard stop. |
| **G1** | After FE1 | `plan` clean apart from the intended CT, `ct_sparkle_vlabel` not recreated (j); HA status + both replication jobs present (k); FE1-S05 measurement recorded | Do not open Session 2 |
| **G2** | After FE2 | Browser-trusted certificate over DNS-01 (a, partial); Coder reachable; `daemon.json` + Docker pin in place | Do not open Session 3 |
| **G3** | After FE3 | `coder templates push` succeeds; `intellij_gateway` decided (`validate` fails while undecided) | Do not open Session 4 |
| **G4** | After FE4-S02 | All eleven gates (a–k) run and recorded, whatever the results | Do not proceed to FE4-S04 |
| **G5** | At FE4-S05 | — | The only point productisation (tenancy cut, OpenMemory, Hermes) may be opened (R8) |

## 9. Slip risks and what they cost

- **The operator prerequisites (§5.4) do not land.** The whole plan stalls at G0. Nothing in FE1–FE4
  is otherwise code-blocked — the largest source of calendar uncertainty, entirely outside engineering
  control.
- **The R4 sizing conflict surfaces as an OOM at first workspace boot** instead of being decided
  cleanly at G0. A deferred decision lets FE1-S01 proceed with a default `swap_mb`, moving the cost
  from Session 1 (cheap) to Session 4/gate h (expensive, with a workspace already running).
- **Double-nested Docker on ZFS (R5) fails.** Per ADR-003 this degrades rather than ends the PoC —
  gate (g) is non-gating. The cost is a caveat in the FE4-S04 verdict, not a blocked session.
- **The Docker 29.5.0 trap (R2) arrives on a later, unrelated maintenance day** rather than during the
  PoC, if FE2-S06 slips. The symptom looks nothing like its cause, so the diagnostic cost lands on a
  disconnected future session — a reason not to defer FE2-S06 even though nothing mechanically
  enforces that.
- **Scope creep into productisation (R8).** The failure mode most likely to actually occur. Not a
  broken PoC, but one whose scope quietly grew past "does it port?" into decisions the prior findings
  document already assigned to a platform owner, not this PoC. G5 prices this risk at zero if
  respected.

## 10. Who does what

| Role | Responsibility |
|---|---|
| **Operator (tomamourette)** | FE0-S01, FE0-S02 — both blocking, non-delegable. Approve `terraform apply`. Decide the pve3 capacity call (G0's sizing decision). Decide `intellij_gateway` (FE3-S05). Decide the fate of `ct_sparkle_vlabel` (FE0-S05). Decide `ct:167`'s HA `started`/`stopped` state (FE1-S03). Judge the PoC verdict and the FE4-S05 go/stop call. |
| **BMad PM / Analyst** | Authored the `products/forge-platform/` artifact set after approval (this document included). |
| **BMad Architect** | ADR-001 through ADR-006. |
| **BMad SM** | Story files per §4.2 of the proposal; this sprint plan; the readiness check. |
| **BMad Dev** | FE1–FE4 implementation, against the existing runbook and Ansible roles. |

## 11. Rollback and exit

Per **NFR-DISP-001**: the PoC is reversible at near-zero cost. A rollback or early stop costs, at most,
one destroyed CT (167), one stashed Terraform block, and one documented negative result. No committed
homelab work depends on this PoC succeeding — nothing existing is invalidated whether it ports, ports
with caveats, or does not port.

**A DOES-NOT-PORT verdict at FE4-S04 is a successful PoC outcome, not a failure.** The PoC's only job
is to convert an opinion ("does Forge run self-hosted?") into evidence; any of the three verdicts does
that job. Treating DOES-NOT-PORT as a failed session would defeat the point of running the PoC.

Rollback mechanics, if invoked at any gate: destroy `module.ct_forge_01` via Terraform (removing the
CT, its HA replication jobs, and its DNS/Prometheus registrations together), leaving
`docs/forge-reuse-and-proxmox-findings.md` and this artifact set — including whatever partial gate
results were captured — as the documented record.

## 12. References

- Proposal: [../../sprint-change-proposal-2026-09-09.md](../../sprint-change-proposal-2026-09-09.md)
- Product brief: [product-brief.md](product-brief.md)
- PRD: [prd.md](prd.md)
- Architecture: [architecture.md](architecture.md)
- Epics: [epics.md](epics.md)
- ADRs: [adrs/ADR-001-lxc-over-vm-for-forge-poc.md](adrs/ADR-001-lxc-over-vm-for-forge-poc.md) through ADR-006
- Acceptance gates: [tests/acceptance.md](tests/acceptance.md)
- End-to-end runbook: [tests/e2e-deployment.md](tests/e2e-deployment.md)
- Tailscale / no-public-ingress policy (not "ADR-010"): `homelab-playbook/wiki/architecture/tailscale-policy.md:20-31` and `wiki/architecture/remote-access-topology.md`
- Prior art: `docs/forge-reuse-and-proxmox-findings.md` (2026-07-30)
