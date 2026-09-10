---
type: prd
product: forge-platform
version: 1.0.0
status: approved-for-poc
date: 2026-09-09
authors: tomamourette (with BMad assist)
brief_ref: product-brief.md
arch_ref: architecture.md
epics_ref: epics.md
source_proposal: ../../sprint-change-proposal-2026-09-09.md
---

# Forge Platform — Product Requirements Document (PoC scope)

## 1. Document Control

| Field | Value |
|---|---|
| Product | Forge Platform — self-hosted PoC on Proxmox |
| Phase | Proof of concept. **Not** productisation. |
| Source of authority | `sprint-change-proposal-2026-09-09.md`, **approved as written 2026-09-09** |
| Scope classification | Moderate (§5.1 of the proposal) |
| Repos in play | `homelab-infra` (Terraform + Ansible), `homelab-playbook` (artifacts + wiki), `repos/forge-platform` @ `2b27a95`, `repos/agentic-ai` @ `87ec24a` |
| Target substrate | CT 167, `ct-forge-01`, pve3, 4C/8GB/50GB, Debian 13, `features=nesting=1,keyctl=1`, 192.168.50.167 |
| Implementation state | **BLOCKED.** Nothing in FE1–FE4 starts before the two §5.4 operator prerequisites exist (§9.1). |
| Relationship to `planning-artifacts/prd.md` | None. That PRD scopes the **AI Dev Container**, a personal always-on agent environment for one operator (`prd.md:49`). Forge is a **multi-user developer platform with a control plane**. They share a substrate and nothing else. No FR is added to that PRD and no Epic 9 is created (proposal §2.2). |

**Evidence notation.** This document preserves the proposal's distinction between claims
**[V]** verified against files or measurement and **[I]** inferred or unverified. Where a claim is
`[I]`, it stays `[I]` — a requirement may exist to *convert* it (FR-SUB-007 is exactly that), but
no artifact in this set may quietly promote an inference to a fact.

---

## 2. Executive Summary

The Forge developer platform is today an Azure-only system built for one company (Saply AI). The
operator intends to generalise it for other companies, and separating it from Saply AI is a
precondition for that. Before any productisation work is planned, one question has to be answered
empirically:

> **Does Forge run at all on a substrate that is not Azure?**

This PRD scopes the smallest system that can answer that question honestly: **Coder + Postgres 16
+ the Forge workspace template + the agentic-ai toolkit**, on a single Proxmox LXC, provisioned
through the estate's existing Terraform/Ansible pipeline, reachable over the tailnet with a
browser-trusted certificate and no new public inbound ingress.

The deliverable is not a platform. It is **a dated, falsifiable verdict**: `PORTS`,
`PORTS-WITH-CAVEATS`, or `DOES-NOT-PORT`, with the caveats enumerated. Anything less than an
explicit verdict means the PoC did not do its job.

Two things must be true before a single line of this is built, and neither can be delivered by
code — see §9.1. Two things are **not** settled by this document and must not be quietly settled
elsewhere — see §11 (the sizing conflict, and double-nested Docker on ZFS).

---

## 3. Background and Problem Recap

Forge's Azure coupling is not evenly distributed. The PoC path — control plane, database,
certificate, workspace image, toolkit — has a clean local substitution for every Azure component
(§5 of `architecture.md`, evidence E5). The parts that do **not** port cheaply are exactly the
parts this PoC excludes: Hermes, OpenMemory and Langfuse carry session pools, blob leases, Key
Vault, App Configuration, Entra-only Postgres and ClickHouse/Redis between them, and **none of
them is needed to prove that the architecture ports** (ADR-006).

A prior analysis of this same question exists: `docs/forge-reuse-and-proxmox-findings.md`
(2026-07-30, 352 lines, written against `forge-platform @ e025bc5` / `agentic-ai @ ff02e19`). It is
**untracked in git** and 40 days stale relative to this PRD. It is **reconciled, not superseded**
(proposal §3.4): most of it stands, it is overturned on exactly one structural recommendation
(VM → LXC, ADR-001) and one causal explanation (the sysbox failure, ADR-004), and its citations
outside the seven files spot-checked in this pass **have not been re-verified** and should be
treated as approximately-correct rather than exact **[I]**. Committing it with a dated header
pointing at the proposal is an action recorded in proposal §4.3; it is deliberately **not** an FR
here, because it is an artifact-hygiene action on the proposal, not a requirement of the product.

---

## 4. Personas and Journeys

### 4.1 Persona — tomamourette (single operator, today)

The only user of the PoC. Holds root on the Proxmox cluster, owns the DNS zone, and already has
passwordless sudo inside every Forge workspace by design (`main.tf:341,353,378`, and `sudo -n true`
is a load-bearing acceptance criterion). This persona is the entire security model of the PoC:
ADR-002's acceptance of `privileged = true` is valid **only** while this is the only persona.

### 4.2 Persona — a second, less-trusted developer (future, not present)

Does not exist yet. Their arrival is the **documented revisit trigger** for ADR-001 (LXC over VM)
and ADR-002 (privileged workspaces). Nothing in this PRD is written for them, and nothing in it
should be read as safe for them.

### 4.3 Journey A — Operator provisions the substrate

Operator lands the two credentials, resolves the sizing decision, targets a Terraform plan, applies
it, wires HA through the Ansible roles to **both** peers, runs `dev-host-setup.yml`, and re-runs the
privilege measurement on the real CT rather than assuming CT 250's result transfers. FE1.

### 4.4 Journey B — Operator stands up the control plane

`forge-coder-host` installs coderd from a pinned, checksum-verified `.deb`, a local Postgres 16
with no extensions, the six-empty-file secrets directory, a `coder.env` with the OIDC and ADO
blocks dropped, and a static Caddy site block that gets its certificate over DNS-01 — an
**outbound** API call, so no inbound ingress is added. FE2.

### 4.5 Journey C — Operator de-Azures the workspace template

On a branch of `forge-platform` (never a fork): local image build, four real `variable`s over the
four `coder_parameter` sizing knobs, the Saply heredocs replaced, `forge-sync.sh` parameterised,
the Azure blocks in `forge-onboard.sh` gated, and the `intellij_gateway` question actually decided.
FE3.

### 4.6 Journey D — Operator creates the first workspace and answers the question

Workspace creates; agentic-ai lands via the GitHub external-auth token; the operator runs the
eleven gates from a tailnet client that is **not on the LAN**, records every result including the
failures, backs the CT up to PBS, and publishes one explicit verdict. FE4.

### 4.7 Journey E — The PoC fails and is thrown away

A `DOES-NOT-PORT` verdict is a **successful outcome of this PoC**, not a failure of it. The exit is
one destroyed CT, one stashed Terraform block, and a documented negative result. No committed
homelab work depends on any of it (NFR-DISP-001).

---

## 5. Functional Requirements

FR IDs are frozen. Every other artifact in this product references them; `epics.md` §7 audits
coverage. Each FR names the story that covers it.

### 5.1 FR-PRE — Prerequisites and truth (FE0)

| ID | Requirement | Story |
|---|---|---|
| **FR-PRE-001** | A GitHub OAuth App exists and `CODER_EXTERNAL_AUTH_0_ID/TYPE/CLIENT_ID/CLIENT_SECRET` are recorded; the grant covers `tomamourette/agentic-ai`. **[operator, BLOCKING — see §9.1]** | FE0-S01 |
| **FR-PRE-002** | A Cloudflare API token with DNS-edit scope on zone `bi-services.be` exists. **[operator, BLOCKING — see §9.1]** | FE0-S02 |
| **FR-PRE-003** | `data "coder_external_auth" "github"` (`coder/templates/forge/main.tf:25-27`) gains `optional = true`, so a missing grant degrades to a visible skip rather than a build failure. Recommended alongside FR-PRE-001 per evidence E6.1; it is **not** a substitute for the credential. | FE0-S01 |
| **FR-PRE-004** | `FORGE_AGENTIC_AI_REF` is pinned to a tag in `coder_agent.main.env` (`main.tf:160-162`), so a merge to agentic-ai `main` cannot change the PoC mid-flight. | FE0-S03 |
| **FR-PRE-005** | The sysbox comment drift is corrected in code and docs before anyone builds on it: `main.tf:399-404` (claims sysbox/unprivileged DinD, **62 lines above `privileged = true` at :566**), `main.tf:559-566`, `docs/coder/setup.md:149-156`, and the ~9 sysbox mentions in `docs/coder/orchestration-adr.md`. `docs/coder/setup.md:141-146` is the only place that currently states the truth. | FE0-S04 |
| **FR-PRE-006** | The uncommitted `module "ct_sparkle_vlabel"` (VMID 166) block at `homelab-infra/terraform/envs/homelab/main.tf:280-304` is stashed or excluded and its fate decided, so no plan or apply recreates a container the operator destroyed on 2026-07-28. | FE0-S05 |

### 5.2 FR-SUB — Substrate (FE1)

| ID | Requirement | Story |
|---|---|---|
| **FR-SUB-001** | CT 167 `ct-forge-01` is provisioned on pve3 by a `module "ct_forge_01"` block using `../../modules/ct-debian` in `homelab-infra/terraform/envs/homelab/main.tf`, mirroring `ct_saply_ai`: Debian 13, unprivileged, `features=nesting=1,keyctl=1`, 192.168.50.167. | FE1-S01 |
| **FR-SUB-002** | `swap_mb` is set **explicitly** in the module block rather than inheriting the 512 MB default at `homelab-infra/terraform/modules/ct-debian/variables.tf:30-33`. The value depends on the unresolved decision in §11.1. | FE1-S01 |
| **FR-SUB-003** | The CT is registered in `outputs.tf` `locals.all_containers` (Prometheus `file_sd_configs`) and `locals.project_container_host_map` (Cloudflare A record + Pi-hole `custom.list`). **No wildcard enters `fqdn_dns_records`** — that map renders hosts-format lines and dnsmasq rejects `*` entries; wildcards go into the Cloudflare map only. | FE1-S01 |
| **FR-SUB-004** | `terraform plan` against the homelab root is narrowly `-target`ed and shows only the expected resources. A bare plan drags in pre-existing DNS drift unrelated to the container. | FE1-S02 |
| **FR-SUB-005** | HA: replication jobs `167-0` (pve3→pve1) **and** `167-1` (pve3→pve2) at `*/15`, plus `ct:167` membership in the `standard` node-affinity rule — created **via the `pve-ha-replication` and `pve-ha-rules` Ansible roles only**. A single replication job means "data is safe" but **failover lands in `error`**. | FE1-S03 |
| **FR-SUB-006** | An Ansible inventory entry and `ansible/inventories/homelab/host_vars/ct-forge-01/main.yml` containing `project_name` exist **before** `dev-host-setup.yml` runs, and that playbook completes. Without `project_name` the role aborts at `dev-host/tasks/main.yml:205` — after creating the `developer` user but before seeding SSH keys at :511. | FE1-S04 |
| **FR-SUB-007** | The evidence-E2 privilege measurement is re-run on CT 167 (Debian 13, `keyctl=1`) and the result recorded, whatever it is. E2 was measured on CT 250 (Debian 12, kernel 6.17.2-1-pve, Docker 29.3.1, cgroup v2); that the result transfers unchanged is **[I]**, and this requirement exists to stop it being assumed. | FE1-S05 |

### 5.3 FR-CTL — Control plane (FE2)

| ID | Requirement | Story |
|---|---|---|
| **FR-CTL-001** | A `forge-coder-host` Ansible role installs coderd from a **checksum-verified, pinned `.deb`**. | FE2-S01 |
| **FR-CTL-002** | Local Postgres 16 with a dedicated role and database, password auth, and **no extensions**. `pgvector` is an OpenMemory requirement only, and OpenMemory is out of scope (ADR-006). | FE2-S02 |
| **FR-CTL-003** | `/opt/coder/secrets` exists mode 0700 containing **six empty 0600 files**; the mnemosyne pair is **not** created. This is the head of the seam `/opt/coder/secrets/*` → `/run/secrets/*` → `~/.config/forge/*.env`, and the empty-file-means-disabled contract is honoured by every consumer (`main.tf:341-389`). **The seam must not be broken.** | FE2-S03 |
| **FR-CTL-004** | `/etc/coder.d/coder.env` exists with the OIDC and Azure DevOps blocks dropped and `CODER_DISABLE_PASSWORD_AUTH=false` (Coder's built-in password auth is already permitted). | FE2-S04 |
| **FR-CTL-005** | Caddy serves `forge.bi-services.be` from a **static** site block with a DNS-01 certificate via `caddy-dns/cloudflare`; the token is supplied as a 0600 root-owned systemd `EnvironmentFile`. No `on_demand_tls`, and no ask-server on `:9111` — those exist only because Azure serves arbitrary per-SNI names, which a single fixed host does not need. | FE2-S05 |
| **FR-CTL-006** | `/etc/docker/daemon.json` carries `{"features":{"time-namespaces":false}}` **and** the Docker package is version-pinned. | FE2-S06 |
| **FR-CTL-007** | `CODER_EXTERNAL_AUTH_0_*` is configured from the operator-supplied GitHub OAuth App. | FE2-S04 |

### 5.4 FR-WS — Workspace template (FE3)

| ID | Requirement | Story |
|---|---|---|
| **FR-WS-001** | `local.image` is sourced from a local `docker build` with `keep_locally = true` (`main.tf:549-550`); **no registry is used** — ACR is not replaced, it is removed. | FE3-S01 |
| **FR-WS-002** | Four real Terraform `variable`s drive **both** the `coder_parameter` defaults **and** their validation maxima for `workspace_cpu_shares` (`main.tf:42`), `workspace_memory_mb` (`:57`), `workspace_memory_swap_mb` (`:72`) and `workspace_memory_reservation_mb` (`:87`). **The values to set are gated on the unresolved decision in §11.1.** | FE3-S01 |
| **FR-WS-003** | The two Saply-specific heredocs at `main.tf:171-270` are replaced with generic equivalents. | FE3-S02 |
| **FR-WS-004** | `company-overlay` is added to `local.repo_deny` (currently `["agentic-ai", "knowledge-base"]` at `main.tf:110`), so it is no longer cloned twice. | FE3-S02 |
| **FR-WS-005** | `forge-sync.sh` is parameterised (org, repo list, ADO block) while preserving the per-repo flags and the distinct failure messages. | FE3-S03 |
| **FR-WS-006** | Every Azure block in `forge-onboard.sh` is gated, **including `:103` `az account show`**, which would otherwise prompt for a login of a binary that will not exist on CT 167. | FE3-S04 |
| **FR-WS-007** | The `module "intellij_gateway"` question (`main.tf:513-519`) is explicitly decided — keep it, and every workspace build then needs registry.coder.com egress; or remove it. `terraform validate` in that directory **fails while this is left undecided**. **Operator decision, open — see §11.3.** | FE3-S05 |
| **FR-WS-008** | forge-platform is cloned onto CT 167, the image builds locally, and `coder templates push` succeeds. | FE3-S06 |
| **FR-WS-009** | `coder/templates/forge/main.tf` is **not forked**. All changes are additive variables and edits on a branch of the upstream repo. | FE3-S01 |

### 5.5 FR-KIT — Toolkit, acceptance and verdict (FE4)

| ID | Requirement | Story |
|---|---|---|
| **FR-KIT-001** | A first workspace is created and agentic-ai reaches it via `coder external-auth access-token github`. | FE4-S01 |
| **FR-KIT-002** | All eleven acceptance gates (a–k, §7) are executed **from a tailnet client not on the LAN** and **every** result is recorded, including failures. | FE4-S02 |
| **FR-KIT-003** | Gate (g) — `docker run --rm hello-world` inside the workspace — is recorded either way but is **non-gating** per ADR-003. | FE4-S02 |
| **FR-KIT-004** | CT 167 is backed up to pve3-pbs and the job recorded. | FE4-S03 |
| **FR-KIT-005** | A **single explicit verdict** is published: `PORTS` / `PORTS-WITH-CAVEATS` / `DOES-NOT-PORT`, with the caveats enumerated. | FE4-S04 |
| **FR-KIT-006** | A retrospective is held and an explicit decision recorded on whether to open a productisation phase (tenancy cut, OpenMemory, Hermes) or stop. | FE4-S05 |

**Total: 28 FRs** — FR-PRE ×6, FR-SUB ×7, FR-CTL ×7, FR-WS ×9 (FR-WS-002 and FR-WS-009 both land in FE3-S01), FR-KIT ×6. Coverage is audited in `epics.md` §7.

---

## 6. Non-Functional Requirements

### 6.1 NFR-SEC — Security posture

| ID | Requirement |
|---|---|
| **NFR-SEC-001** | **No new public inbound ingress.** The certificate is issued over DNS-01, which is an **outbound** API call. This is consistent with — and is the reason the design works within — the estate's Tailscale-first posture at `homelab-playbook/wiki/architecture/tailscale-policy.md:20-31` ("Public DNS / port-forward and SSH-key distribution both stay fallback-or-disabled unless Tailscale is genuinely insufficient") and `wiki/architecture/remote-access-topology.md:15-40`. **There is no "ADR-010" in this estate** — the only ADR-010 is `products/context-stack/adrs/ADR-010-decommission-as-single-pr.md`, which is unrelated. Do not cite it. |
| **NFR-SEC-002** | `privileged = true` for workspace containers is accepted **for a single operator only**. The measured blast radius ends at root *inside the LXC* — a privilege the workspace user already holds. The **revisit trigger is a second, less-trusted user on the host** (ADR-002). |
| **NFR-SEC-003** | The Cloudflare API token and the GitHub OAuth client secret are stored 0600 root-owned and are never committed. |

### 6.2 NFR-IAC — Infrastructure-as-code discipline

| ID | Requirement |
|---|---|
| **NFR-IAC-001** | All infrastructure is created through Terraform and the existing Ansible roles. Direct `ha-manager` / `pvesr` invocation is **break-glass only** — bypassing the roles is how ct:163 and ct:164 drifted out of IaC until they were backfilled on 2026-05-14. |
| **NFR-IAC-002** | Every `terraform plan` against the homelab root is narrowly `-target`ed (gate j). |

### 6.3 NFR-DISP — Disposability

| ID | Requirement |
|---|---|
| **NFR-DISP-001** | The PoC is reversible at near-zero cost: one destroyed CT, one stashed Terraform block, and a documented negative result. No committed homelab work depends on it. |

### 6.4 NFR-CAP — Capacity

| ID | Requirement |
|---|---|
| **NFR-CAP-001** | With a workspace running, `free -g` on pve3 shows headroom and CT 167 is not swap-thrashing (gate h). |
| **NFR-CAP-002** | The sizing decision in §11.1 is resolved **before FE1-S01 starts**. **[OPEN — this is the one thing approval explicitly did not settle.]** |

### 6.5 NFR-OBS — Observability

| ID | Requirement |
|---|---|
| **NFR-OBS-001** | Monitoring is auto-derived: `locals.all_containers` → `generated/prometheus-node-targets.json`. **No dashboard work is in PoC scope.** |

### 6.6 NFR-PORT — Portability and the seam

| ID | Requirement |
|---|---|
| **NFR-PORT-001** | The Proxmox Terraform root is a **sibling** of the Azure root, not a relocation. The Azure root is not moved, rewritten, or deleted. |
| **NFR-PORT-002** | The secrets seam `/opt/coder/secrets/*` → `/run/secrets/*` → `~/.config/forge/*.env` is preserved intact. It is what makes the Azure→self-hosted substitution cheap, and gate (f) proves it end to end. |

---

## 7. Acceptance Gates (product-level, §5.3 of the proposal)

Executed **from a tailnet client not on the LAN**. Full detail lives in
[tests/acceptance.md](tests/acceptance.md).

| # | Gate | Gating? | Note |
|---|---|---|---|
| a | Coder's web UI and code-server open over a **browser-trusted certificate** with no warning, on **both** SANs — the apex `forge.bi-services.be` **and** a preview URL under `*.forge.bi-services.be` | Yes | **Amended 2026-09-09:** the original note read "Wildcard SAN **not** asserted — `coder_app "code_server"` is `subdomain = false`". That is reversed. `code_server` really is `subdomain = false`, but Coder's **preview URLs are subdomain-based** and `CODER_WILDCARD_ACCESS_URL=*.forge.bi-services.be` is set on CT 167, so serving **only the apex is a FAIL**. **Second correction 2026-09-09:** do **not** read this as "one certificate with two SANs". Caddy issues **one certificate per name**, and CT 167 now serves two separate genuine Let's Encrypt certificates (`CN=forge.bi-services.be` and `CN=*.forge.bi-services.be`), both verifying with no `-k`. The requirement is that **both names** present a browser-trusted certificate; counting SANs on the apex reads `1` on a correct deployment. Full measurement in `tests/acceptance.md` §2 gate (a). |
| b | `~/workspace/repos/github/` contains ≥1 repo cloned via `coder external-auth access-token github`, **and** `~/workspace/repos/github/company-overlay` does **not** exist | Yes | Proves FR-PRE-001 and the double-clone fix |
| c | `~/.forge-toolchain` lists claude, codex, gh, terraform, and reports both API keys unset | Yes | Subscription-auth path intact |
| d | `ls ~/.claude/skills \| wc -l` ≥ 200, **and** `~/.claude/settings.json` has the **2** global registrations, **and** the resolved project root's `.claude/settings.json` has **18** | Yes | Restated per the prior document's C1 — "18 in `$HOME`" is false |
| e | `claude` starts under subscription OAuth and answers one prompt | Yes | The actual product value |
| f | `~/.config/forge/openmemory.env` and `langfuse.env` are both **zero-byte**, the build log contains both "skipped" lines, and `sudo -n true` succeeds | Yes | Proves the empty-file contract end to end |
| g | `docker run --rm hello-world` succeeds inside the workspace | **No** | **Non-gating** per E1 / ADR-003. Record the result either way. |
| h | `free -g` on pve3 shows headroom with the workspace running; CT 167 is not swap-thrashing | Yes | The §11.1 sizing conflict, measured |
| i | Wall-clock create → code-server-reachable is recorded | Yes (recording, not a threshold) | Baseline for any future optimisation |
| j | `terraform plan` on the homelab root is clean apart from the intended CT; the `ct_sparkle_vlabel` phantom has not been recreated | Yes | Regression guard |
| k | `ha-manager status` shows `ct:167 (pve3, started)` **and** `/etc/pve/replication.cfg` has **both** `167-0` and `167-1` | Yes | The ct:151 lesson |

**The PoC verdict is a single explicit call in FE4-S04: `PORTS` / `PORTS-WITH-CAVEATS` /
`DOES-NOT-PORT`.** Anything less than an explicit verdict means the PoC did not do its job.

---

## 8. Out of Scope

**Explicitly out of scope for the PoC, and stated here so it cannot drift back in:**

1. **Hermes.** Needs a `sandbox.py` and a ~150-line broker that do not exist. (ADR-006)
2. **OpenMemory.** Needs a five-file provider/auth/dimension refactor and cannot boot off Azure at
   all. Its `pgvector` requirement is the only reason Postgres would need extensions; it does not,
   because OpenMemory is out. (ADR-006)
3. **Langfuse.** Pinned version unresolved; v3 would drag ClickHouse + Redis + MinIO onto an 8 GB
   host. (ADR-006)

Each of the three is a design project in its own right, each carries a large share of the Azure
coupling, and **none of them is needed to answer "does it port?"**.

Also out of scope:

4. **Productisation** — the tenancy cut, the tenant manifest schema, and the prior document's
   sixteen platform-owner decisions. **FE4-S05 is the only gate at which productisation may be
   opened** (R8 in §10 — the failure mode most likely to actually occur).
5. **CI wiring and the Saply leak deletions** (`saply-cv-workflow.skill`, `saplyCLI.jar`). These
   correctly gate a tenant cut, not a PoC; and CI cannot apply to Proxmox anyway, since
   GitHub-hosted runners have no LAN route.
6. **Sysbox.** Three independent blockers, none of which the PoC is asking about (ADR-004).
7. **A Proxmox VM.** `modules/vm-dev` has never been applied and is broken in four documented ways
   (ADR-001).
8. **Grafana dashboards** for CT 167. Monitoring is auto-derived; no dashboard work (NFR-OBS-001).
9. **Any change to `planning-artifacts/prd.md`, `epics.md`, `architecture.md`, or
   `implementation-artifacts/sprint-status.yaml`** (proposal §4.3, §6.1).

---

## 9. Dependencies and Assumptions

### 9.1 Blocking operator prerequisites — **nothing in FE1–FE4 starts before both exist**

> **1. A GitHub OAuth App** → `CODER_EXTERNAL_AUTH_0_ID/TYPE/CLIENT_ID/CLIENT_SECRET`.
> **The only non-optional external credential in the whole PoC.** `data "coder_external_auth"
> "github"` (`coder/templates/forge/main.tf:25-27`) lacks `optional = true` — unlike the
> azuredevops provider at `:32-35` — so the **workspace build fails** without it. And even if the
> build were made to pass, `forge-sync.sh` sources its token from
> `coder external-auth access-token github` and **silently skips its entire clone block** when the
> token is absent, so agentic-ai never reaches the workspace and gates (b)–(e) are untestable.
> Covered by FR-PRE-001 / FE0-S01. **Operator only; cannot be delegated.**
>
> **2. A Cloudflare API token**, DNS-edit scope, zone `bi-services.be`.
> Required for **any** browser-trusted certificate: the homelab has no inbound :80/:443, so
> HTTP-01 is **impossible**, not merely inconvenient. ~~The **wildcard scope is optional** —
> `coder_app "code_server"` sets `subdomain = false`, so code-server is path-proxied and exercises
> no wildcard; wildcard is only needed for `forge-preview-url`.~~ **The token is not optional.**
>
> **REVERSED 2026-09-09 — a wildcard IS required.** The struck clause was correct about
> `code_server` and wrong about the PoC: `forge-preview-url` is **not** out of scope — Coder's
> preview URLs are subdomain-based and `CODER_WILDCARD_ACCESS_URL=*.forge.bi-services.be` is live in
> `/etc/coder.d/coder.env` on CT 167, so the certificate must carry both SANs. **What did not
> change:** the token itself needs no re-scoping — one `Zone.DNS Edit` grant on `bi-services.be`
> already covers the `_acme-challenge` TXT records for both names. See the amendment at the top of
> [adrs/ADR-005](adrs/ADR-005-dns-01-wildcard-over-public-ingress.md).
> Covered by FR-PRE-002 / FE0-S02. **Operator only; cannot be delegated.**

### 9.2 Other dependencies

- **pve3 capacity.** The only resource shared with any existing epic. An 8 GB CT plus the Coder
  control plane plus Postgres 16 plus a running workspace container — see §11.1.
- **The established project-CT pattern.** `homelab-playbook/wiki/runbooks/create-project-container.md`
  (last reviewed 2026-07-28, `status: stable`, rehearsed four times) is the implementation vehicle.
- **`dev-host` already installs** Docker CE, Node 20 LTS, the Claude Code CLI wrapper, ruflo, and
  pyenv/Python 3.11.11 — most of the Forge host toolchain for free.
- **VMID 167 is the next free VMID** in the 162–169 project block; 162–165 are in state and 166 is
  the phantom addressed by FR-PRE-006.

### 9.3 Assumptions

- The operator remains the only user of CT 167 for the duration of the PoC (ADR-002).
- The Coder version installed by FE2-S01 accepts the template as branched by FE3 — untested until
  FE3-S06, and §3.2 of the proposal explicitly budgets for at least one failed workspace build.
- CT 250's privilege measurement is expected but **not assumed** to transfer to Debian 13 **[I]**;
  FR-SUB-007 converts the inference into a measurement.

---

## 10. Risks

Carried from the proposal's risk register. `epics.md` §6 maps them to epics.

| ID | Risk | Severity / Likelihood | Mitigation |
|---|---|---|---|
| **R1** | **Comment drift** — the docs describe sysbox, the code runs privileged. `main.tf:399-404` claims sysbox/unprivileged DinD **62 lines above `privileged = true` at :566**; the claim persists across `docs/coder/orchestration-adr.md` and `workspace/Dockerfile`. An engineer porting this reads the comment first and ports the wrong architecture. | Low severity / high likelihood of wasted time | FE0-S04 fixes it before anyone builds on it. ADR-004. |
| **R2** | **The Docker 29.5.0 upgrade trap is scheduled, not avoided.** CT 250 measured Docker 29.3.1, *below* the 29.5.0 time-namespace flip, so the failure **cannot reproduce today** and **will** appear after the next `apt upgrade` — with a symptom (`namespace {"time" ""} does not exist`) that looks nothing like its cause. | Medium severity / high likelihood if unmitigated | FE2-S06: `daemon.json` `{"features":{"time-namespaces":false}}` **plus** a version pin. ADR-004. |
| **R3** | `docs/forge-reuse-and-proxmox-findings.md` is untracked, 40 days stale, and its divergences from this plan (LXC vs VM, HA vs no-HA) are load-bearing. Two contradictory documents in the tree is worse than one stale one. | Medium | Reconcile, do not supersede (proposal §3.4); commit it with a dated header (proposal §4.3). Citations outside the seven spot-checked files stay **[I]**. |
| **R4** | **The sizing conflict.** See §11.1. Surfaces as an OOM at first workspace boot. | Medium severity / high likelihood | **Unresolved.** Blocks FE1-S01. NFR-CAP-002. |
| **R5** | **Nested-nested Docker on a ZFS-backed LXC rootfs is untested.** See §11.2. | Low severity given ADR-003 / medium likelihood | Gate (g) is non-gating, so a failure degrades the PoC rather than ending it. |
| **R6** | **HA on a 3-node rule while pve1's reliability is unresolved.** The `standard` rule spans pve1/pve2/pve3; pve2 measured ~12 GB free (2026-07-30); pve1 has a recorded hard-hang cycle. | Open question | Replication to **both** peers is correct and non-negotiable. Whether `ct:167` registers `started` or `stopped` per the Project-CT HA Policy is an **operator call at FE1-S03** — see §11.4. |
| **R7** | **The "ADR-010 no-public-ingress" citation does not resolve.** No such ADR exists in any tracked repo. A fabricated citation repeated into six ADRs is expensive to unpick. | Low, but it propagates | Every artifact in this set cites `wiki/architecture/tailscale-policy.md:20-31` and `wiki/architecture/remote-access-topology.md` instead. NFR-SEC-001, ADR-005. |
| **R8** | **Scope creep from the PoC into productisation.** The prior document lists 16 decisions that are the platform owner's, four of which block the tenant manifest schema. **None of them blocks the PoC, and none should be answered inside it.** | High likelihood / high cost — the failure mode most likely to actually occur | The PoC's only question is *"does it port?"*. **FE4-S05 is the gate where productisation may be opened — not before.** §8 item 4. |

> **A note on the proposal's own numbering.** The proposal's Approval section refers to the sizing
> conflict as "R1", while its risk register lists the sizing conflict as **R4** and comment drift
> as **R1**. This PRD uses the **risk-register** numbering. Where the operator's approval note says
> "R1 / workspace `coder_parameter` defaults", it means **R4 here**. The substance is unaffected:
> the sizing conflict is the headline open decision either way, and approval did not settle it.

---

## 11. Open Decisions

These are open **on purpose**. Recording them as open is a requirement of this PRD; resolving them
silently in a downstream artifact is a defect.

### 11.1 The sizing conflict — **UNRESOLVED, blocks FE1-S01** (R4, NFR-CAP-002)

The workspace template sizes workspaces with `coder_parameter` blocks, **not** `variable` blocks:

- `coder/templates/forge/main.tf:62` — `workspace_memory_mb` **default 12288 MB** (min 2048, max 15360)
- `coder/templates/forge/main.tf:77` — `workspace_memory_swap_mb` **default 20480 MB** (min 2048, max 32768)
- `coder/templates/forge/main.tf:87-99` — `workspace_memory_reservation_mb` default 2048 (min 512, max 8192)
- `coder/templates/forge/main.tf:42` — `workspace_cpu_shares`

A **4C/8GB** CT cannot host a workspace at those defaults. Three facts soften that, and one does not:

- They are `coder_parameter` with **`mutable = true`** and `min = 2048`, so an operator **can**
  pick 2048–8192 MB in the Coder create-workspace form. The prior findings document's flat claim
  *"First workspace OOMs"* is therefore **too strong** — it assumes the default is taken.
- But **`--variables-file` cannot lower a `coder_parameter` default**, so every workspace create is
  a manual act of remembering. A bad PoC ergonomic and a worse demo.
- **Swap has no answer inside an LXC.** You cannot create a swapfile in an unprivileged container;
  the CT gets whatever `swap_mb` Terraform set — **512 MB by default**
  (`homelab-infra/terraform/modules/ct-debian/variables.tf:30-33`). `memory_swap` at anything near
  its 20480 MB default is unbackable.

**Two candidate resolutions, neither chosen:**

| Option | What it means |
|---|---|
| **(a)** | Add four real `variable`s driving **both** the `coder_parameter` defaults **and** their validation maxima (FR-WS-002 / FE3-S01), **and** set `swap_mb = 8192` on the CT (FR-SUB-002 / FE1-S01). |
| **(b)** | Size CT 167 at **4C/12GB** instead of 4C/8GB. |

**This is an operator capacity call against pve3.** It must be resolved **before FE1-S01 starts**.
The proposal's approval note is explicit that approval does **not** settle it.

### 11.2 Double-nested Docker on a ZFS-backed LXC rootfs — **UNTESTED** (R5)

The workspace's inner dockerd writes to `docker_volume.dockerd`, which exists specifically because
*"overlay2 cannot stack on overlay"* (`main.tf:541-548, 585-588`). On CT 167 that volume lives on
the **outer** Docker's data root, on the LXC's **ZFS** rootfs. Docker on ZFS works — every project
CT runs it via `dev-host` — and **one nesting level is proven. Two levels is not.**

This is the strongest surviving argument from the prior document's VM recommendation (ADR-001
overturns two of that document's four arguments and carries this one forward as a risk, not a
blocker). It is **mitigated but not removed** by ADR-003: gate (g) is non-gating, so a failure here
degrades the PoC rather than ending it. **No claim is made in this artifact set that it will work.**

### 11.3 `intellij_gateway` — **UNDECIDED** (FR-WS-007, FE3-S05)

Keep `module "intellij_gateway"` (`main.tf:513-519`) and every workspace build needs
registry.coder.com egress; or remove it. `terraform validate` in that directory **fails while this
is left undecided**, so it cannot be deferred past FE3. **Operator decision.**

### 11.4 `ct:167` HA state — **UNDECIDED** (R6, FE1-S03)

Whether `ct:167` registers `started` or `stopped` under the Project-CT HA Policy is an operator
call, taken against pve1's unresolved hard-hang history and pve2's measured headroom. **Replication
to both peers is not open** — it is required (FR-SUB-005).

### 11.5 The fate of `ct_sparkle_vlabel` — **UNDECIDED** (FR-PRE-006, FE0-S05)

Stashing or excluding the block is required before any plan. Whether it is deleted, committed as
a destroyed-resource record, or kept stashed is an **operator decision**.

---

## 12. Effort and Risk (estimates, not commitments)

T-shirt sizes only. **No story points are asserted anywhere in this artifact set.**

| Phase | Size | Range |
|---|---|---|
| Artifact set authoring (brief → sprint plan) | S | 1 session |
| CT 167 provisioning via the established pattern | S | half a session; the runbook is stable and rehearsed 4× |
| `forge-coder-host` Ansible role (coderd, Postgres 16, Caddy, secrets dir, `daemon.json`) | M | Debian is native here |
| forge-platform branch edits | M | ~150 lines across ~6 files |
| Image build + template push + acceptance | M | includes at least one failed workspace build; assume it |
| **Total** | **M–L** | **Two to four working sessions — if the operator prerequisites land first** |

**Overall risk: MEDIUM.** Contained: a new CT on the standard pattern, an isolated Terraform
target, no shared service touched. The genuine risks are §11.1 (sizing), §11.2 (double-nested
Docker on ZFS) and R2 (the Docker 29.5.0 trap). **None of these threatens existing production
services.**

---

## 13. References

### 13.1 This product

- [product-brief.md](product-brief.md), [architecture.md](architecture.md), [epics.md](epics.md),
  [sprint-plan.md](sprint-plan.md), [readiness-check.md](readiness-check.md)
- [tests/acceptance.md](tests/acceptance.md), [tests/e2e-deployment.md](tests/e2e-deployment.md)
- ADRs: [ADR-001](adrs/ADR-001-lxc-over-vm-for-forge-poc.md),
  [ADR-002](adrs/ADR-002-privileged-workspace-accepted-for-single-operator.md),
  [ADR-003](adrs/ADR-003-nested-docker-is-not-an-acceptance-gate.md),
  [ADR-004](adrs/ADR-004-sysbox-rejected-and-the-docker-29-5-0-trap.md),
  [ADR-005](adrs/ADR-005-dns-01-wildcard-over-public-ingress.md),
  [ADR-006](adrs/ADR-006-hermes-openmemory-langfuse-out-of-poc-scope.md)

### 13.2 Source of authority

- `../../sprint-change-proposal-2026-09-09.md` — approved 2026-09-09 as written.
- `implementation-artifacts/sprint-status-forge-platform.yaml` — the tracking file (§6.1). The
  existing `sprint-status.yaml` is **not** touched.

### 13.3 Estate policy and precedent

- `homelab-playbook/wiki/architecture/tailscale-policy.md:20-31` — the ingress posture.
- `homelab-playbook/wiki/architecture/remote-access-topology.md:15-40` — how it fits alongside
  Cloudflare Tunnel, VS Code tunnels and the Proxmox console.
- `homelab-playbook/wiki/runbooks/create-project-container.md` — the implementation vehicle.
- `products/context-stack/` — the structural precedent for this artifact set.

### 13.4 Prior art

- `docs/forge-reuse-and-proxmox-findings.md` (2026-07-30, 352 lines, untracked, written against
  `forge-platform @ e025bc5` / `agentic-ai @ ff02e19`). **Reconciled, not superseded** — proposal
  §3.4. Citations outside the seven files spot-checked this pass are **[I]**.

### 13.5 Code read this pass

- `repos/forge-platform` @ `2b27a95` — `coder/templates/forge/main.tf`, `forge-sync.sh`,
  `forge-onboard.sh`, `forge-workspace-cleanup.sh`, `workspace/Dockerfile`, `docs/coder/setup.md`,
  `docs/coder/orchestration-adr.md`.
- `repos/agentic-ai` @ `87ec24a` — 211 `SKILL.md` + 14 `.skill` archives.
- `homelab-infra/terraform/modules/ct-debian/variables.tf`,
  `homelab-infra/terraform/envs/homelab/main.tf`, `homelab-infra/terraform/modules/vm-dev`.
