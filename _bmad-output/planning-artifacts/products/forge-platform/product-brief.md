---
type: product-brief
product: forge-platform
version: 1.0.0
date: 2026-09-09
author: tomamourette (with BMad assist)
status: planning artifacts authored; implementation BLOCKED on §5.4 operator prerequisites
inputs:
  - homelab-playbook/_bmad-output/planning-artifacts/sprint-change-proposal-2026-09-09.md
  - docs/forge-reuse-and-proxmox-findings.md (2026-07-30, 352 lines, untracked)
  - repos/forge-platform @ 2b27a95
  - repos/agentic-ai @ 87ec24a
---

# Forge Platform — Product Brief

## 1. Vision

Forge is today an Azure-only developer platform — Coder control plane, a workspace template, and the `agentic-ai` skill/hook toolkit — built for one company (Saply AI). The operator's stated intent is to **productise Forge for companies other than Saply AI**, and separating it from Saply AI's Azure estate is a precondition for that.

This brief does not scope productisation. It scopes the single question that has to be answered first, empirically, before any productisation work is planned: **does Forge run at all on a substrate that is not Azure?** The vehicle is a proof of concept — Coder + Postgres 16 + the Forge workspace template + the `agentic-ai` toolkit, stood up on a single Proxmox LXC on the operator's own homelab cluster. The output is not a working platform; it is a dated, falsifiable verdict.

Forge-as-a-productisable-platform is the eventual destination. This PoC is the first, narrowest step toward it, structured so a negative result costs almost nothing and a positive result becomes the evidence base for the phase that follows.

## 2. Problem Statement

`repos/forge-platform` + `repos/agentic-ai` currently assume Azure end to end:

| Azure dependency | Where it shows up |
|---|---|
| Entra OIDC sign-in | `coder.env` OIDC block |
| Key Vault via IMDS (8 host files) | Secrets seam feeding `~/.config/forge/*.env` |
| Azure Container Registry image pulls | `local.image` sourcing in `main.tf` |
| Postgres Flexible Server, Entra auth | The control-plane database |
| Caddy `on_demand_tls` + an undocumented ask-server on `:9111` | TLS issuance for arbitrary per-SNI Azure tenant subdomains |
| Two Saply-specific onboarding heredocs | `main.tf:171-270` |
| An `az account show` call | `forge-onboard.sh:103` |

Every one of these couplings is Saply-AI-specific or Azure-specific, and none of them has been tested against any other substrate. The architecture companion document (§8 of `architecture.md`) works through a substitution for each row; this brief's job is only to establish that the substitution is worth attempting and to bound what "worth attempting" means.

Nothing in the existing homelab BMAD artifact set covers this work. The homelab PRD is scoped to the **AI Dev Container** — a personal, always-on agent environment for a solo consultant (`prd.md:49`). Forge is a **multi-user developer platform with a control plane** (Coder), a workspace lifecycle, external-auth integration, and per-developer isolation. They share a Proxmox substrate and nothing else. There is no epic, no FR, and no product folder that Forge's PoC belongs to — inventing one by amending the AI Dev Container PRD would make that PRD describe two products and destroy its FR coverage map (`sprint-change-proposal-2026-09-09.md` §2.2).

A prior analysis of exactly this question already exists — `docs/forge-reuse-and-proxmox-findings.md` (2026-07-30, 352 lines, written against `forge-platform @ e025bc5` / `agentic-ai @ ff02e19`) — and is **currently untracked in git**. Both repos have since moved (`2b27a95` / `87ec24a`). That document is prior art for this PoC, not a substitute for it: it is reconciled, not superseded (§3.4 of the sprint change proposal), and one of its structural recommendations (a Proxmox VM rather than an LXC) is overturned here on newly measured evidence.

## 3. Target Users and Personas

**Single user, today: tomamourette.**

| Attribute | Value |
|---|---|
| Role | Solo homelab operator; owns both the Forge platform and the Proxmox estate it runs on |
| Stack expertise | Deep Proxmox, Terraform, Ansible; the established project-CT pattern (VMID block 162–169) |
| Relationship to Forge | Builds and maintains `forge-platform` + `agentic-ai`; currently the only Coder user and the only workspace occupant |
| Security posture accepted | `privileged = true` workspaces, in-container passwordless sudo, and blast radius bounded by the LXC user namespace — acceptable *because* there is exactly one trust domain (ADR-002) |

**Future persona (explicitly out of scope for this PoC): a second, less-trusted developer.** The moment a second person needs a Coder workspace on this host, the single-operator security reasoning in ADR-001 and ADR-002 stops holding — `privileged = true` and the passwordless-sudo equivalence are accepted *for a single operator only*. That persona's arrival is the documented revisit trigger for both ADRs, not a design target this PoC optimises for. Standing this persona up (tenancy cut, per-user isolation, RBAC) is productisation work and is explicitly deferred to FE4-S05.

**Non-personas (explicit).** No customer-facing users. No Saply AI product team access. No CI runners (GitHub-hosted runners have no LAN route to Proxmox). No shared-tenant concerns of any kind in this phase.

| | Today (in scope) | Future (out of scope, revisit trigger) |
|---|---|---|
| Trust domains | One | Two or more |
| Sign-in | Coder password auth | Likely OIDC / per-user SSO (undesigned) |
| Workspace privilege | `privileged = true` accepted (ADR-002) | Requires re-litigation the moment a second developer exists |
| Secrets scope | Single operator's GitHub + Cloudflare credentials | Per-tenant secret isolation (undesigned) |
| Governing artifact | This product folder | A future, separate productisation artifact set, gated by FE4-S05 |

## 4. Goals and Non-Goals

### 4.1 In scope (PoC)

| # | In-scope item | Epic |
|---|---|---|
| G1 | CT 167 `ct-forge-01` provisioned on pve3 via the established project-CT Terraform/Ansible pattern, HA-replicated to both peers | FE1 |
| G2 | Coder control plane + Postgres 16 + Caddy with a browser-trusted certificate, self-hosted, no Azure services | FE2 |
| G3 | The Forge workspace template de-Azured: local image build, no registry, Saply-specific heredocs replaced, Azure onboarding blocks gated | FE3 |
| G4 | The `agentic-ai` toolkit (211 skills) reaches a real workspace via GitHub external-auth and is exercised by a live `claude` session under subscription OAuth | FE4 |
| G5 | Eleven acceptance gates (a–k, §6) executed from a tailnet client not on the LAN, every result recorded including failures | FE4 |
| G6 | A single explicit verdict — PORTS / PORTS-WITH-CAVEATS / DOES-NOT-PORT — with caveats enumerated | FE4 |
| G7 | `docs/forge-reuse-and-proxmox-findings.md` committed with a dated header, reconciling it with this PoC's findings rather than discarding it | FE0 |

### 4.2 Out of scope (PoC)

| # | Out-of-scope item | Why |
|---|---|---|
| NG1 | **Hermes** | Session pools + blob leases are Azure-coupled; not needed to prove the architecture ports |
| NG2 | **OpenMemory** | Needs a 5-file provider/auth/dimension refactor and `pgvector`; cannot boot off Azure at all today; not needed for the PoC's question |
| NG3 | **Langfuse** | Pinned version unresolved; v3 drags in ClickHouse + Redis + MinIO on an 8 GB host; not needed for the PoC's question |
| NG4 | Tenancy cut / productisation (per-tenant manifest schema, RBAC, a second user) | The prior document's 16 platform-owner decisions include four that block a tenant manifest schema; **none blocks the PoC and none should be answered inside it** |
| NG5 | CI wiring | GitHub-hosted runners have no LAN route to Proxmox; productisation-phase concern |
| NG6 | The Saply AI leak deletions (`saply-cv-workflow.skill`, `saplyCLI.jar`) | Productisation cleanup, not a porting question |
| NG7 | Sysbox as the container runtime | Three independent blockers (open upstream issue, unsupported in LXC, Debian 13 absent from the compat table) — see §8 |
| NG8 | A Proxmox VM as the deployment vehicle | `modules/vm-dev` has never been applied and is broken in four documented ways; the isolation premium it buys is priced for untrusted users, who do not exist in this phase |

Hermes, OpenMemory, and Langfuse together carry nearly all of Forge's remaining Azure coupling (session pools, blob leases, Key Vault, App Configuration, Entra-only Postgres, ClickHouse/Redis). Excluding all three is what makes the PoC answerable in weeks rather than months.

### 4.3 Phasing summary

| Phase | Epic | Outcome | Gate to next phase |
|---|---|---|---|
| 0 | FE0 | Prerequisites and truth: both blocking operator credentials exist; comment drift and phantom VMID resolved | Both credentials recorded; `FORGE_AGENTIC_AI_REF` pinned |
| 1 | FE1 | CT 167 exists on pve3, HA-replicated to both peers, `dev-host` provisioned | E2 privilege measurement re-run and recorded on CT 167 |
| 2 | FE2 | Coder + Postgres 16 + Caddy running self-hosted with a browser-trusted cert | `coder.env` password-auth reachable over Tailscale |
| 3 | FE3 | Workspace template builds locally with no Azure dependency | `coder templates push` succeeds |
| 4 | FE4 | First workspace created, all gates run, verdict published, retrospective held | FE4-S05 decision: open productisation, or stop |

This PoC is Phase 0–4 only. A productisation phase, if opened, is a separate, future artifact set gated by FE4-S05 — not pre-committed here.

### 4.4 Two blocking operator prerequisites

Nothing in FE1–FE4 should start before both of these exist — neither can be delivered by code, and both are load-bearing for the acceptance gates that follow them:

| # | Prerequisite | Why it blocks | Consequence if skipped |
|---|---|---|---|
| 1 | **GitHub OAuth App** → `CODER_EXTERNAL_AUTH_0_ID/TYPE/CLIENT_ID/CLIENT_SECRET`, grant covering `tomamourette/agentic-ai` | `data "coder_external_auth" "github"` (`main.tf:25-27`) has no `optional = true` | Workspace build fails outright; even if it built, `forge-sync.sh` silently skips its whole clone block without a token, so `agentic-ai` never lands and gates (b)–(e) are untestable |
| 2 | **Cloudflare API token**, DNS-edit scope, zone `bi-services.be` | The homelab has no inbound :80/:443, so HTTP-01 cannot work at all — DNS-01 is the only option and it needs this token | No browser-trusted certificate is possible for `forge.bi-services.be`; gate (a) cannot pass |

~~Wildcard scope on the Cloudflare token is optional — `coder_app "code_server"` is `subdomain = false`, so code-server is path-proxied and exercises no wildcard.~~ The token itself is not optional.

> **REVERSED 2026-09-09 — a wildcard IS required.** Coder's preview URLs are subdomain-based
> (`CODER_WILDCARD_ACCESS_URL=*.forge.bi-services.be`, live on CT 167), so the certificate carries
> both `forge.bi-services.be` and `*.forge.bi-services.be`. The **token** half of the struck sentence
> still holds — one `Zone.DNS Edit` grant on the zone covers both names, no re-scoping. See
> [adrs/ADR-005](adrs/ADR-005-dns-01-wildcard-over-public-ingress.md).

## 5. Key Constraints

| Constraint | Target |
|---|---|
| Substrate | CT 167, `ct-forge-01`, pve3, 4C/8GB/50GB, Debian 13, `features=nesting=1,keyctl=1`, 192.168.50.167 |
| Public ingress | None added. DNS-01 issues certificates over an outbound API call only — consistent with `wiki/architecture/tailscale-policy.md:20-31` and `wiki/architecture/remote-access-topology.md` |
| IaC-only provisioning | All infrastructure via Terraform + the existing `pve-ha-replication` / `pve-ha-rules` Ansible roles; direct `ha-manager` / `pvesr` is break-glass only |
| Single-operator security posture | `privileged = true` workspaces accepted for one operator only (ADR-002); revisit trigger is a second, less-trusted user |
| Disposability | Reversible at near-zero cost: destroy one CT, stash one Terraform block, keep a documented negative result |
| No fork | `coder/templates/forge/main.tf` is not forked; changes are additive variables on a branch |
| Two Terraform roots | The Proxmox root is a sibling of the existing Azure root, not a relocation — each owns its own state and lifecycle |
| Plan discipline | `terraform plan` against the homelab root is always narrowly `-target`ed; a bare plan drags in pre-existing DNS drift unrelated to this container |
| Estimates | T-shirt sizes (S/M/L) or ranges only, always labelled "estimate, not a commitment" — no story points |

## 6. Success Criteria

The PoC's acceptance gates (§5.3 of the sprint change proposal), executed from a tailnet client **not on the LAN**:

| # | Gate (summary) | Note |
|---|---|---|
| a | Coder UI + code-server open over a browser-trusted certificate, no warning, on **both** SANs (apex **and** a preview URL under `*.forge.bi-services.be`) | **Amended 2026-09-09:** was "No wildcard SAN asserted" — reversed. Serving **only the apex is a FAIL**. **Second correction 2026-09-09:** do **not** read this as "one certificate with two SANs". Caddy issues **one certificate per name**, and CT 167 now serves two separate genuine Let's Encrypt certificates (`CN=forge.bi-services.be` and `CN=*.forge.bi-services.be`), both verifying with no `-k`. The requirement is that **both names** present a browser-trusted certificate; counting SANs on the apex reads `1` on a correct deployment. Full measurement in `tests/acceptance.md` §2 gate (a). |
| b | ≥1 repo cloned via GitHub external-auth; `company-overlay` does not exist under it | Proves FR-PRE-001 and the double-clone fix |
| c | `~/.forge-toolchain` lists claude, codex, gh, terraform; both API keys unset | Subscription-auth path intact |
| d | ≥200 skills present; 2 global + 18 project `.claude/settings.json` registrations | Restated per prior-doc correction C1 |
| e | `claude` starts under subscription OAuth and answers one prompt | The actual product value |
| f | `openmemory.env` / `langfuse.env` zero-byte; both "skipped" in build log; `sudo -n true` succeeds | Proves the empty-file contract end to end |
| g | `docker run --rm hello-world` inside the workspace | **Non-gating** (ADR-003); recorded either way |
| h | `free -g` on pve3 shows headroom; CT 167 not swap-thrashing | The sizing conflict, measured (§8) |
| i | Wall-clock create → code-server-reachable recorded | Baseline for future optimisation |
| j | `terraform plan` clean apart from the intended CT; no `ct_sparkle_vlabel` phantom | Regression guard |
| k | `ha-manager status` shows `ct:167 (pve3, started)`; both `167-0`/`167-1` in `replication.cfg` | The ct:151 lesson |

**The verdict itself is the top-level success criterion:** FE4-S04 must publish one of **PORTS / PORTS-WITH-CAVEATS / DOES-NOT-PORT**, with every caveat enumerated. Anything short of an explicit verdict means the PoC did not do its job — a pile of green checkmarks with no stated conclusion is a failed PoC by this brief's own definition.

**Hard gate — non-negotiable regardless of the eleven above:** gate (k), HA correctness. `ha-manager status` must show `ct:167 (pve3, started)` **and** `/etc/pve/replication.cfg` must carry **both** `167-0` and `167-1`. A single replication job passing while the other is silently absent is exactly the ct:151 failure mode — data looks safe right up until a failover lands the container in `error`. This gate is checked independently of the PORTS verdict; a verdict of PORTS with gate (k) unmet is not a valid outcome.

**Effort estimate (t-shirt, wall-clock, *estimate — not a commitment*):**

| Phase | Size | Range |
|---|---|---|
| Artifact set authoring (this brief → sprint plan) | S | 1 session |
| CT 167 provisioning via the established pattern | S | half a session; runbook is stable and rehearsed 4× |
| `forge-coder-host` Ansible role | M | Debian is native here |
| forge-platform branch edits | M | ~150 lines across ~6 files |
| Image build + template push + acceptance | M | includes at least one failed workspace build; assume it |
| **Total** | **M–L** | Two to four working sessions **if the operator prerequisites (§4.4) land first** |

## 7. Strategic Alignment

Adding a Forge product folder does **not** conflict with the homelab PRD's goals — the reason matters and is worth stating explicitly, since Forge and the AI Dev Container look adjacent on the surface.

`prd.md:49` scopes the AI Dev Container as *"a reusable Proxmox LXC container template that provides an always-on AI development environment — a personal 'Jarvis' for software projects,"* built for a solo consultant. Forge is a **multi-user developer platform with a control plane** (Coder), a workspace lifecycle, and per-developer isolation. These are different products that happen to share a substrate.

Three PRD themes are **reinforced**, not contradicted:

- *"Self-hosted and sovereign"* (`prd.md:61`) — the PoC's entire purpose is moving Forge off a cloud.
- *"Infrastructure-as-code for the agent layer"* (`prd.md:64`) — the PoC uses the existing Terraform/Ansible pipeline rather than a bespoke one.
- Brownfield expansion of the Proxmox estate (`prd.md:71`) — the same pattern already used for Epic 8 (PVE3 + local LLM).

Because the two products are genuinely separate, this brief makes no edit to `prd.md`, `epics.md`, or `architecture.md`. Forge gets its own product folder, structured exactly like `products/context-stack/`, `products/doc-system/`, and `products/remote-access/` — an established, working precedent that ran to a clean close on the Context Stack product (2026-04-27, verdict CONTINUE).

| Existing artifact set | Relationship to this PoC | Reference |
|---|---|---|
| AI Dev Container (`epics.md` Epics 0–4) | **None.** Different product; all epics `done`; untouched by this proposal | `prd.md:49` |
| Knowledge Management (Epic 7, `backlog`) | **None.** Epic 7 is Hermes-facing ingestion; Hermes is explicitly out of PoC scope | `sprint-change-proposal-2026-09-09.md` §2.1 |
| PVE3 + local LLM (Epic 8) | **Pattern precedent only.** Same brownfield-Proxmox-expansion theme; no shared resource beyond pve3 capacity | `prd.md:71` |
| Context Stack (`products/context-stack/`) | **Structural precedent.** This product folder mirrors its Brief → PRD → Architecture → Epics → Stories → Acceptance → Readiness → Sprint-plan shape | `products/context-stack/` |
| `sprint-status.yaml` (homelab main) | **Unedited.** Forge tracks in its own `sprint-status-forge-platform.yaml`, per the estate's existing per-product-status-file convention | §6.1 of the sprint change proposal |

## 8. Risks and Open Questions

### 8.1 Risk register

| ID | Risk / question | Severity / likelihood | Status |
|---|---|---|---|
| **R4 (headline — the sizing conflict)** | Template `coder_parameter` defaults are 12288 MB RAM / 20480 MB swap against an 8 GB CT; these are `coder_parameter`, not `variable`, so a `--variables-file` cannot lower the default, and swap has no answer inside an unprivileged LXC (`swap_mb` defaults to 512 MB). | High likelihood, medium severity — surfaces as OOM at first workspace boot | **OPEN. Must be resolved before FE1-S01.** Two candidate resolutions, neither chosen: (a) four real `variable`s driving both the defaults and their validation maxima, plus `swap_mb = 8192`; or (b) size CT 167 at 4C/12GB. This is an operator capacity call against pve3. |
| R1 | Comment drift: forge-platform's docs describe sysbox; the code runs `privileged = true` 62 lines below | Low severity, high likelihood of wasted time | Fixed by FE0-S04 |
| R2 | The Docker 29.5.0 upgrade trap is scheduled, not avoided — CT 250 measured 29.3.1, below the time-namespace behaviour flip | Medium severity, high likelihood if unmitigated | Mitigated by FE2-S06 (`daemon.json` flag + version pin) |
| R3 | `docs/forge-reuse-and-proxmox-findings.md` is untracked and 40 days stale; its citations outside seven spot-checked files have not been re-verified | Medium | Reconcile, do not supersede; commit with a dated header (G7) |
| R5 | Double-nested Docker on a ZFS-backed LXC rootfs is untested — one nesting level is proven (every project CT runs it via `dev-host`), two is not | Medium likelihood, low severity given ADR-003 | Carried forward; mitigated by gate (g) being non-gating |
| R6 | HA on a 3-node `standard` rule while pve1's reliability is unresolved (recorded hard-hang cycle); pve2 measured ~12 GB free (2026-07-30) | Open question, not a risk to close here | Replication to both peers is non-negotiable; whether `ct:167` registers `started` or `stopped` is an operator call at FE1-S03 |
| R7 | A prior request framed the ingress policy as "ADR-010's no-public-ingress rule" — **no such ADR exists.** The real policy is `wiki/architecture/tailscale-policy.md:20-31` and `wiki/architecture/remote-access-topology.md`. | Low severity, but propagates if uncorrected | Every downstream artifact in this product cites the wiki pages, never "ADR-010" |
| R8 | Scope creep from the PoC into productisation — the most likely failure mode to actually occur | High likelihood, high cost | FE4-S05 is the only gate where productisation may be opened; not before |

**Overall risk: MEDIUM.** The PoC is contained — a new CT on the standard pattern, an isolated Terraform target, no shared service touched, and none of the eight risks above threatens an existing production service. The genuine risks are the sizing/swap conflict, double-nested Docker on ZFS, and the Docker 29.5.0 upgrade trap; all three are named, tracked, and either mitigated or explicitly left open rather than assumed away.

### 8.2 The headline open decision, restated

The sizing conflict (labelled R4 in the risk register, but referred to as "R1" in the proposal's own Approval section — the proposal's numbering is internally inconsistent; this brief treats it as the headline item regardless of number) is the one thing this brief cannot resolve on the operator's behalf. It requires a pve3 capacity judgement — is 4C/8GB with a hand-sized workspace acceptable, or does CT 167 need to grow to 4C/12GB — and that judgement belongs to the operator, not to this document. **It must be resolved before FE1-S01 starts.**

## 9. Glossary

| Term | Definition |
|---|---|
| **Forge** | The Coder-based multi-user developer platform (`repos/forge-platform`), today Azure-only and Saply-AI-coupled |
| **agentic-ai** | The companion skills/hooks toolkit (`repos/agentic-ai`, 211 `SKILL.md` files at `87ec24a`) that reaches a Forge workspace via `forge-sync.sh` |
| **PoC** | This proof of concept: does Forge run on a non-Azure substrate at all? Nothing more. |
| **CT 167 / `ct-forge-01`** | The disposable Proxmox LXC this PoC provisions on pve3 to host the Coder control plane |
| **`coder_parameter`** | A Coder Terraform resource exposing a mutable, per-workspace-create value with a default and min/max — distinct from a Terraform `variable`, which is fixed at template-push time |
| **DNS-01** | The ACME certificate-issuance challenge type that proves domain control via a DNS record rather than an inbound HTTP request — the only viable path here, since the homelab has no inbound :80/:443 |
| **Empty-file-means-disabled contract** | The seam `/opt/coder/secrets/*` → `/run/secrets/*` → `~/.config/forge/*.env`: a zero-byte file at any stage means "this integration is disabled," verified end to end by gate (f) |
| **PORTS / PORTS-WITH-CAVEATS / DOES-NOT-PORT** | The three permitted verdict values for FE4-S04; no other framing satisfies the PoC's purpose |
| **FE0–FE4** | The five frozen epic IDs for this PoC (Prerequisites and truth; Substrate; Control plane; Workspace; Toolkit and acceptance) — see `epics.md` for goal/scope/AC detail per epic |
| **FR / NFR** | Functional / non-functional requirement IDs, defined once in this product's `prd.md` and referenced, never redefined, by every other artifact in the folder |
| **VMID** | Proxmox's numeric container/VM identifier; this PoC claims **167**, the next free slot in the 162–169 project block after the **166** phantom (an uncommitted, already-destroyed `ct_sparkle_vlabel` block) is resolved |
| **T-shirt sizing** | S / M / L effort labels used throughout this product in place of story points, always paired with "estimate, not a commitment" |
| **PBS** | Proxmox Backup Server — the existing `pve3-pbs` target CT 167 backs up to (FE4-S03), independent of and complementary to HA replication |
| **Tailnet** | The operator's Tailscale mesh network; acceptance gates a–k are run from a tailnet client deliberately *not* on the LAN, to measure the real remote-developer path |

## 10. References

- `docs/forge-reuse-and-proxmox-findings.md` (2026-07-30, 352 lines, currently untracked) — prior art for this PoC; reconciled, not superseded, per §3.4 of the sprint change proposal
- [sprint-change-proposal-2026-09-09.md](../../sprint-change-proposal-2026-09-09.md) — the approved spec this brief is derived from; authoritative for all epic/story IDs, FR/NFR IDs, and the acceptance gates
- `homelab-playbook/wiki/architecture/tailscale-policy.md:20-31` — the real no-public-ingress-by-default policy (not "ADR-010")
- `homelab-playbook/wiki/architecture/remote-access-topology.md` — how DNS-01 outbound-only certificate issuance fits the estate's remote-access posture
- `homelab-playbook/wiki/runbooks/create-project-container.md` — the established CT provisioning pattern this PoC follows for CT 167
- [prd.md](../../prd.md) — the AI Dev Container PRD; unedited by this proposal, cited in §7 for strategic alignment only
- `products/context-stack/` — the structural precedent this product folder mirrors
- `repos/forge-platform/coder/templates/forge/main.tf` @ `2b27a95` — the workspace template this PoC de-Azures; source of the sizing-conflict facts in §8
- `repos/agentic-ai` @ `87ec24a` — the toolkit (211 `SKILL.md` files) exercised by gates (c)–(e)
- [architecture.md](architecture.md) — companion document; target topology, the `/opt/coder/secrets` contract, and the Azure→self-hosted substitution table this brief's §4 scope implies

---

**End of brief — handoff to architecture and epics.**
