# Sprint Change Proposal: Forge developer platform — self-hosted PoC on Proxmox

**Date:** 2026-09-09
**Author:** tomamourette (with BMad analyst assist)
**Workflow:** `bmad-correct-course`, Batch mode
**Change Type:** New product line (additive) — strategic pivot, not a failure remediation
**Scope Classification:** Moderate
**Status:** APPROVED 2026-09-09 (as written). Product artifacts and a dedicated sprint-status file authored per §4.1/§6.1. Implementation (FE1+) blocked on §5.4 operator prerequisites.

---

## Section 1: Issue Summary

### Problem Statement

The **Forge developer platform** (`repos/forge-platform` + `repos/agentic-ai`) is today an Azure-only
system built for one company (Saply AI). The operator intends to **generalise it for other companies**,
and separating it from Saply AI is a precondition for that. Before any productisation work is planned,
one question has to be answered empirically: **does Forge run at all on a substrate that is not Azure?**

Nothing in the current BMAD artifact set covers this. The homelab PRD is scoped to the *AI Dev Container*
(a personal always-on agent environment); Forge is a *multi-user developer platform*. They share a
substrate and nothing else. There is no epic, no FR, and no product folder that this work belongs to.

The proposed correction is to stand up a **proof of concept** — Coder + Postgres 16 + the Forge workspace
template + the agentic-ai toolkit on a single Proxmox LXC (**CT 167, `ct-forge-01`, pve3, 4C/8GB/50GB,
Debian 13, `features=nesting=1,keyctl=1`, 192.168.50.167**) — and to track it as a **new product**
under `planning-artifacts/products/forge-platform/`, mirroring the `context-stack` precedent.

**Explicitly out of scope for the PoC:** Hermes, OpenMemory, Langfuse. These carry nearly all of the
Azure coupling (session pools, blob leases, Key Vault, App Configuration, Entra-only Postgres,
ClickHouse/Redis) and **none of them is needed to prove that the architecture ports**.

### Context

This is a **strategic pivot**, categorised honestly:

- **Not a failure.** No story failed, no epic is blocked, no acceptance criterion was missed. Every
  homelab epic in `sprint-status.yaml` is `done` except Epic 7 (Knowledge Ingestion Pipelines), which
  is `backlog` and untouched by this.
- **Not a course correction against a plan.** There is no existing plan to correct. The trigger is a
  new business intent: productise Forge for companies other than Saply AI.
- **It is a course correction against the artifact set**, because the artifact set has no place to put
  this work, and putting it in the wrong place (as an Epic 9 of the AI Dev Container) would corrupt a
  product line whose PRD says something else.

A prior analysis of exactly this question already exists: **`docs/forge-reuse-and-proxmox-findings.md`**
(2026-07-30, 352 lines, `forge-platform @ e025bc5`, `agentic-ai @ ff02e19`). It is **untracked in git**
(`git status` reports `?? docs/forge-reuse-and-proxmox-findings.md`). Both repos have moved since:
`forge-platform` is now at `2b27a95`, `agentic-ai` at `87ec24a`. Reconciliation with that document is
handled in §1.3 and §3.4; it is not superseded wholesale — most of it stands.

### Evidence

Findings 1–7 below are the basis for the recommendation. Each is marked **[V]** verified against files
or measurement, or **[I]** inferred/unverified. File paths are relative to `~/workspace/homelab/`.

---

**E1 — Nested Docker inside the workspace has zero automated consumers. [V]**

- Across `repos/agentic-ai` @ `87ec24a`, a grep for executable docker/compose/testcontainers invocations
  across `skills/ hooks/ workflows/ scripts/ tests/ tools/` returns **three** files, and all three are
  prose in BMAD templates, not calls:
  `skills/bmad-create-architecture/steps/step-06-structure.md`,
  `skills/bmad-document-project/documentation-requirements.csv`,
  `skills/bmad-document-project/workflows/full-scan-instructions.md`.
- The **only** docker invocation in the entire Coder template surface is
  `repos/forge-platform/coder/templates/forge/forge-workspace-cleanup.sh:14-26` — `docker info`,
  then four `prune` calls and a `docker system df`. Housekeeping, not workload.
- Failure to start dockerd is **soft by construction**:
  `coder/templates/forge/main.tf:401-405` is written to survive `set -e` and emits only
  `WARN: dockerd not ready (see /tmp/dockerd.log; needs the sysbox runtime on the host)`.
- Browser testing is **not** a driver: Playwright + Chromium are baked natively into the image at
  `repos/forge-platform/workspace/Dockerfile:61-68`, with an in-build smoke test.
- The documented justification for nested Docker is
  `repos/forge-platform/docs/coder/orchestration-adr.md:32-33` — *"Devs need `docker compose up` for
  local stacks (Postgres/Redis/Java services — 8 repos ship compose/Dockerfiles)"*. Those are the
  **Saply AI product repos**, which are out of scope for this PoC.

*Count correction:* the working figure of "231 skills" does not reproduce. `find repos/agentic-ai -name
SKILL.md` returns **211**, plus **14** `.skill` archives under `skills/`. `company-overlay` contributes
**0** `SKILL.md`. The substance of E1 is unaffected — 211 or 231, none of them shells out to Docker.

**Consequence:** nested Docker is a *nice-to-have* for the PoC, not an acceptance gate. It can be
proven with a single `docker run --rm hello-world` and, if it fails, the PoC still answers its question.

---

**E2 — Privileged Docker inside an unprivileged LXC was measured working. [V, in-session]**

Measured on **CT 250** (Debian 12, kernel 6.17.2-1-pve, Docker 29.3.1, cgroup v2):

- The privileged container gets full `CapEff`, but **held inside the LXC user namespace** — host uid 0
  is unmapped, so "root" in the container is an unprivileged host uid.
- No host block devices are visible inside the container.
- `modprobe` fails (no `/lib/modules` in the CT).

**Realistic blast radius: root *inside the LXC*.** That is a privilege the workspace user **already
holds** — the Forge image ships passwordless sudo, and the template depends on it
(`coder/templates/forge/main.tf:341,353,378` all read `/run/secrets/*` via `sudo cat`, and the
acceptance criterion `sudo -n true` is load-bearing). For a **single operator**, the security delta of
`privileged = true` is therefore close to zero.

The cost is a **future** cost: this reasoning stops being acceptable the moment a second, less-trusted
user exists on the host. That is the documented trigger to revisit, and it should be written into the
PoC's ADR rather than left implicit.

*Not verified:* that CT 250's result transfers unchanged to a Debian **13** CT with `keyctl=1`. It is
the same kernel and the same cgroup version, so the expectation is high, but the PoC's first
acceptance step should re-run the measurement on CT 167 rather than assume it. **[I]**

---

**E3 — forge-platform's stated sysbox rationale is factually wrong, and the correct fix is a flag. [V]**

The code and the docs both blame the Docker **version**:

- `coder/templates/forge/main.tf:559-566` — *"sysbox 0.7.0 is incompatible with the host's Docker 29.6
  (OCI `time` namespace error, nestybox/sysbox#1011) … the alternative (pinning host Docker+containerd
  back) risks the host runtime."*
- `docs/coder/setup.md:149-156` — *"downgrading host Docker+containerd to a sysbox-supported ~27.x
  risks the host runtime and freezes Docker security updates."*

The real cause is narrower: **Docker 29.5.0 enabled private time namespaces by default**
(moby/moby#52326). **The same release shipped the off-switch**:
`{"features":{"time-namespaces":false}}` in `/etc/docker/daemon.json`. Three reporters on
nestybox/sysbox#1011 confirm the flag resolves it.

Two qualifications that must not be dropped:

- nestybox/sysbox#1011 is **still open with no maintainer response**. Treat the daemon flag as the
  reliable fix and **sysbox 0.7.1 as unverified**. **[I]**
- Separately, **sysbox inside an LXC is unsupported per the maintainer** (nestybox/sysbox#860), and
  **Debian 13 is absent from sysbox's distro-compatibility table**. Sysbox is therefore not an option
  for CT 167 regardless of the flag.

**The trap:** CT 250 runs **Docker 29.3.1**, which is *below* the 29.5.0 behaviour flip. The bug
**cannot reproduce today** — and **will** appear after the next `apt upgrade`. This is a latent
scheduled failure, not a resolved one. It needs a pin or a pre-emptive `daemon.json` entry in the
PoC's Ansible role.

---

**E4 — A Proxmox VM is not the simpler path. [V]**

`homelab-infra/terraform/modules/vm-dev`:

- **Has never been applied.** `deploy_dev_vm = false`; state contains zero `proxmox_vm_qemu` resources.
- Carries **legacy flat `disk {}` blocks** for telmate 3.0.2-rc04 (the nested `disks {}` form is current).
- `ci_password` is **required with no default**.
- Declares `agent = 1` and a `default_ipv4_address` output with **no qemu-guest-agent** in the image →
  **no IP is ever returned**.
- The base template (VM 9000) lives on **pve1**, and `local-zfs` is per-node, so a pve3 clone fails.

Proxmox's own guidance to prefer a VM over an LXC is conditioned on **untrusted users / maximum
isolation / live migration**. None applies to a single-operator PoC. Combined with E2, the case for
a VM collapses for *this* scope.

**The trigger to revisit is a second untrusted user, not the PoC.** State it as an ADR consequence.

---

**E5 — Every Azure dependency in the PoC path has a clean local substitution. [V]**

| Azure component | Self-hosted substitution | Evidence |
|---|---|---|
| Entra OIDC sign-in | Coder built-in password auth | `CODER_DISABLE_PASSWORD_AUTH=false` already permits it; drop the OIDC block from `coder.env` |
| Key Vault via IMDS → 8 host files | **Six empty files** under `/opt/coder/secrets/` (0600, dir 0700) | The template honours an explicit empty-file-means-disabled contract, verified at `coder/templates/forge/main.tf:341-389`: `: > "$HOME/.config/forge/openmemory.env"` on empty input, ditto langfuse and rollout |
| ACR image pull | Local `docker build` + `keep_locally = true` — **no registry needed** | `coder/templates/forge/main.tf:550` |
| Caddy `on_demand_tls` + an undocumented ask-server on `:9111` | A **static** Caddy site block | on-demand exists only because Azure serves arbitrary per-SNI names; a single fixed host does not need it |
| Postgres Flexible Server (Entra auth) | **Local Postgres 16**, password auth, no extensions | `pgvector` is an OpenMemory requirement only, and OpenMemory is out of scope |

The seam that makes this cheap is `/opt/coder/secrets/*` → `/run/secrets/*` → `~/.config/forge/*.env`.
It must not be broken.

---

**E6 — Two operator prerequisites are blocking and cannot be delivered by code. [V]**

1. **A GitHub OAuth App** for `CODER_EXTERNAL_AUTH_0_*`. **MANDATORY.**
   `data "coder_external_auth" "github"` (`coder/templates/forge/main.tf:25-27`) lacks
   `optional = true` (unlike the azuredevops provider at `:32-35`), so the **workspace build fails**
   without it. Worse, even if the build were made to pass, `forge-sync.sh` sources its token from
   `coder external-auth access-token github` and **silently skips its entire clone block** when the
   token is absent — meaning `agentic-ai` never reaches the workspace and the PoC proves nothing.
   This is the **one non-optional external credential**: ADO, OpenMemory and Langfuse all disable
   cleanly via the empty-file contract.
   *Recommended alongside:* add `optional = true` to the github block anyway, so a missing grant
   degrades to a visible skip rather than a build failure.

2. **A Cloudflare API token** scoped to **DNS-edit on `bi-services.be`** for a DNS-01 certificate on
   `forge.bi-services.be` (and optionally `*.forge.bi-services.be`).
   DNS-01 needs **no inbound connection**, which is what makes it compatible with the homelab's
   Tailscale-first, no-public-ingress posture. The **token is mandatory even for a single-name
   certificate** — the homelab has no inbound :80/:443, so HTTP-01 cannot work at all. The
   **wildcard scope is optional**: `coder_app "code_server"` sets `subdomain = false`, so code-server
   is path-proxied and exercises no wildcard. Wildcard is only needed for `forge-preview-url`.

*Correction to the framing:* the requested justification cited **"ADR-010's no-public-ingress rule."**
**No such ADR exists in any tracked repo.** `grep -rn "ADR-010"` across the estate returns exactly one
hit — `products/context-stack/adrs/ADR-010-decommission-as-single-pr.md`, an unrelated document. The
policy being invoked is real but lives elsewhere: `homelab-playbook/wiki/architecture/tailscale-policy.md:20-31`
("Public DNS / port-forward and SSH-key distribution both stay fallback-or-disabled unless Tailscale is
genuinely insufficient") and `wiki/architecture/remote-access-topology.md:15-40`. **Cite those, not ADR-010.**

---

**E7 — The established homelab CT pattern is the correct implementation vehicle. [V]**

From `homelab-playbook/wiki/runbooks/create-project-container.md` (last reviewed 2026-07-28, `status: stable`):

- **Terraform:** a `module "ct_forge_01"` block using `../../modules/ct-debian` in
  `homelab-infra/terraform/envs/homelab/main.tf`, mirroring `ct_saply_ai`.
- **DNS is auto-derived**, not hand-edited: register the CT in `outputs.tf` `locals.all_containers`
  (Prometheus `file_sd_configs`) and `locals.project_container_host_map` (→ Cloudflare A record +
  Pi-hole `custom.list`).
- **`terraform plan` MUST be narrowly `-target`ed.** A bare plan against this state drags in
  pre-existing DNS drift unrelated to the container (runbook §Pitfalls 1).
- **HA via the Ansible roles only** — `pve-ha-replication` and `pve-ha-rules`. Direct `ha-manager` /
  `pvesr` is break-glass only; bypassing the roles is exactly how ct:163 and ct:164 drifted out of IaC
  until backfilled on 2026-05-14 (runbook §4, §Pitfalls 4).
- **Replicate to BOTH peers** (pve3→pve1 *and* pve3→pve2). The `standard` rule spans all three nodes;
  a single replication job means "data is safe" but **failover lands in `error`** (runbook §Pitfalls 5).
- **`project_name` MUST exist** in `ansible/inventories/homelab/host_vars/ct-forge-01/main.yml`, or
  `dev-host` aborts at the BMAD install task (`dev-host/tasks/main.yml:205`) — **after** creating the
  `developer` user but **before** seeding SSH keys at line 511 (runbook §6, §Pitfalls 3).
- **`dev-host` already installs** Docker CE, Node 20 LTS, the Claude Code CLI wrapper, ruflo, and
  pyenv/Python 3.11.11. That is most of the Forge host toolchain for free.

**VMID:** the 162–169 project block is currently 162, 163, 164, 165 in state; **166 is a phantom** —
`homelab-infra/terraform/envs/homelab/main.tf:280-304` is an **uncommitted working-tree** `module
"ct_sparkle_vlabel"` block (verified: `git diff` shows it as +27 unstaged lines) for a container that
was destroyed on 2026-07-28. **167 is the correct next free VMID**, and the phantom block must be
stashed or excluded before planning, or a bare apply recreates a container the operator deleted.

---

## Section 2: Impact Analysis

### 2.1 Epic impact — **none of the existing epics are affected**

| Artifact set | Epics | State (`sprint-status.yaml` and siblings) | Impact |
|---|---|---|---|
| AI Dev Container (`epics.md`) | 0, 1, 2, 3, 4 | all `done` | **None** |
| Knowledge Management (SCP-knowledge-mgmt-2026-04-11) | 5, 6 `done`; **7 `backlog`** | Epic 7 = Linear/Granola/ADO ingestion for Hermes | **None** |
| PVE3 node + local LLM (`epics.md` §Epic 8) | 8 | `done` | **None** |
| pve3 storage migration (`sprint-status-pve3-storage-migration.yaml`) | 1–7 | all `done` / `done-with-*` | **None** |
| Hybrid Gemma serving | separate status file | separate track | **None** |
| Context Stack (`products/context-stack/`) | E1–E4 | CLOSED 2026-04-27, verdict CONTINUE | **None** |

**This is the answer, and it is justified rather than convenient:**

- Epic 7 (Knowledge Ingestion) is Hermes-facing. **Hermes is explicitly out of PoC scope.** Zero overlap.
- Epics 0–6 and 8 are `done`. Adding a product does not reopen a completed epic.
- The **only** shared resource is **pve3 capacity**, which is a technical constraint (§2.3), not an
  epic dependency.

**Therefore no existing epic is modified, split, added to, or resequenced by this proposal.**

### 2.2 Artifact conflicts

**Does adding a Forge product conflict with the homelab PRD's goals?** No — and the reason matters.

`prd.md:49` scopes the product as *"a reusable Proxmox LXC container template that provides an always-on
AI development environment — a personal 'Jarvis' for software projects,"* built *"for a solo consultant
running multiple client projects."* Forge is a **multi-user developer platform with a control plane**
(Coder), a workspace lifecycle, OIDC, and per-developer isolation. These are **different products that
share a substrate.**

Three PRD themes are *reinforced*, not contradicted:

- *"Self-hosted and sovereign"* (`prd.md:61`) — the PoC's entire purpose is moving Forge off a cloud.
- *"Infrastructure-as-code for the agent layer"* (`prd.md:64`) — the PoC uses the existing
  Terraform/Ansible pipeline rather than a bespoke one.
- Brownfield expansion of the Proxmox estate (`prd.md:71`) — same pattern as Epic 8.

**Conclusion: do not add FRs to `prd.md`, and do not add an Epic 9 to `epics.md`.** Forge gets its own
product folder, exactly as `context-stack`, `doc-system` and `remote-access` already do. Adding it to
the AI Dev Container line would make that PRD describe two products and destroy its FR coverage map.

`architecture.md` (914 lines, AI Dev Container solution design) similarly needs **no edit**: it makes no
claim about the estate that a new project CT invalidates.

### 2.3 Technical impact

| Area | Impact | Detail |
|---|---|---|
| **IaC — Terraform** | Additive, one module block + two `outputs.tf` appends | Must be planned with `-target=module.ct_forge_01` + the three generated/DNS resources. **Blocked by** the uncommitted `ct_sparkle_vlabel` (VMID 166) phantom block. |
| **IaC — swap** | **`swap_mb` must be set explicitly** | `modules/ct-debian/variables.tf:30-33` defaults `swap_mb = 512`, and the runbook's template block does not set it. The Forge workspace's `memory_swap` default is **20480 MB** (`coder/templates/forge/main.tf:71-84`). See the sizing conflict below. |
| **DNS** | Auto-derived, zero manual edits | `ct-forge-01.bi-services.be` via `project_container_host_map`. **A wildcard must never enter `fqdn_dns_records`** — that map renders hosts-format lines for Pi-hole and dnsmasq rejects `*` entries. Wildcards go into the Cloudflare map only. |
| **Monitoring** | Auto-derived | `locals.all_containers` → `generated/prometheus-node-targets.json`. No dashboard work required for a PoC. |
| **HA** | Two replication jobs + one rule membership | `167-0` (pve3→pve1) and `167-1` (pve3→pve2), `*/15`; append `ct:167` to the `standard` rule CSV. `state:` per the Project-CT HA Policy — `started` if always-on. **Open question:** pve1's crash-loop history makes a 3-node `standard` rule less reassuring than it reads (§Open Questions). |
| **Capacity (pve3)** | The real constraint | An 8 GB CT plus the Coder control plane plus Postgres 16 plus a running workspace container. **See the sizing conflict.** |
| **Ansible** | One new host entry + host_vars + one new role | `dev-host` covers Docker/Node/Claude/pyenv. A new `forge-coder-host` role covers coderd, Postgres 16, Caddy, `/opt/coder/secrets`, `daemon.json`. |
| **forge-platform repo** | Branch edits, no fork | Variables for the image ref and the four sizing ceilings, replace two Saply heredocs, parameterise `forge-sync.sh`, gate `forge-onboard.sh:103` (`az account show`, which otherwise prompts for a login of a binary that will not exist). |
| **Security posture** | Unchanged for one operator; documented debt for two | E2. Needs an ADR, not a footnote. |
| **Public ingress** | **None added.** | DNS-01 issues certificates over an outbound API call. Consistent with `wiki/architecture/tailscale-policy.md:20-31`. |

**⚠ Sizing conflict found during this analysis — this changes the picture and is not in the brief.**

`coder/templates/forge/main.tf` sizes workspaces with `coder_parameter` blocks, not `variable` blocks:

- `:56-69` `workspace_memory_mb` — **default 12288 MB**, min 2048, max 15360
- `:71-84` `workspace_memory_swap_mb` — **default 20480 MB**, min 2048, max 32768
- `:86-99` `workspace_memory_reservation_mb` — default 2048

A **4C/8GB** CT cannot host a workspace at those defaults. Three facts soften it, and one does not:

- These are `coder_parameter`, **`mutable = true`**, with `min = 2048` — so an operator **can** pick
  2048–8192 MB in the Coder create-workspace form. The prior findings document's flat claim *"First
  workspace OOMs"* (§Appendix A) is **too strong**: it assumes the default is taken.
- But **`--variables-file` cannot lower a `coder_parameter` default**, so every workspace create is a
  manual act of remembering. That is a bad PoC ergonomic and a worse demo.
- **Swap has no answer inside an LXC.** You cannot create a swapfile in an unprivileged container; the
  CT gets whatever `swap_mb` Terraform set — **512 MB by default**. `memory_swap` at anything near its
  default is unbackable.

**Recommendation:** do the small forge-platform change the prior document already prescribed — add four
real `variable`s driving **both** the parameter default **and** its validation max — and set
`swap_mb = 8192` on the CT. Budget this into the PoC rather than discovering it at first workspace boot.
Alternatively size CT 167 at **4C/12GB**; that is an operator capacity call against pve3.

---

## Section 3: Recommended Approach

### 3.1 The three checklist options

| Option | Assessment |
|---|---|
| **1. Direct Adjustment** — extend the plan additively, keep all completed work | **RECOMMENDED.** Nothing existing is invalidated. Forge becomes a fourth entry under `products/`, alongside `context-stack`, `doc-system` and `remote-access` — an established, working precedent. No epic reopens, no FR changes, no rollback. |
| **2. Rollback** — revert completed work to clear the path | **Rejected — nothing to roll back.** No committed work conflicts with Forge. The only reversal in sight is the *uncommitted* `ct_sparkle_vlabel` block, which is a stash, not a rollback. Invoking this option would be theatre. |
| **3. MVP Review / Re-scope** — reduce or replan the MVP | **Rejected — the MVP is complete.** The AI Dev Container MVP shipped; 6/6 epics, 24 stories, 31 FRs deployed. Forge does not compete for its scope. Re-opening it to accommodate an unrelated product would be a category error. |

### 3.2 Recommendation

**Option 1 — Direct Adjustment.** Create `planning-artifacts/products/forge-platform/` as a new
BMAD-tracked product, structured exactly like `context-stack`. Scope its first phase to the PoC
defined here. Make no change to `prd.md`, `epics.md`, or `architecture.md`.

**Rationale:**

1. **The precedent already exists and worked.** `products/context-stack/` ran a full
   Brief → PRD → Architecture → Epics → Stories → Acceptance → Readiness → Sprint-plan cycle to a clean
   close (2026-04-27, verdict CONTINUE, zero FAIL). Reusing that shape costs no design effort.
2. **It isolates a genuinely separate product** without polluting a PRD whose FR coverage map is
   currently complete and audited.
3. **It is reversible at near-zero cost.** If the PoC fails, the outcome is one destroyed CT, one
   stashed Terraform block, and a documented negative result. No committed homelab work depends on it.
4. **It converts an unresolved strategic question into a dated, falsifiable answer.** "Does Forge run
   self-hosted?" is currently opinion. After the PoC it is evidence.

**Effort estimate (t-shirt, wall-clock, *estimates not commitments*):**

| Phase | Size | Range |
|---|---|---|
| Artifact set authoring (brief → sprint plan) | **S** | 1 session |
| CT 167 provisioning via the established pattern | **S** | half a session; the runbook is stable and rehearsed 4× |
| `forge-coder-host` Ansible role (coderd, Postgres 16, Caddy, secrets dir, `daemon.json`) | **M** | Debian is native here — unlike the prior doc's VM path, which carried a Debian→Ubuntu delta |
| forge-platform branch edits (variables, heredocs, `forge-sync.sh`, `forge-onboard.sh` gating) | **M** | ~150 lines across ~6 files |
| Image build + template push + acceptance | **M** | includes at least one failed workspace build; assume it |
| **Total** | **M–L** | Two to four working sessions if the operator prerequisites land first |

**Risk: MEDIUM.**
- Contained: a new CT on the standard pattern, an isolated Terraform target, no shared service touched.
- The genuine risks are (a) the sizing/swap conflict in §2.3, (b) nested-nested Docker on a ZFS-backed
  LXC rootfs (untested — see §Open Questions), and (c) the Docker 29.5.0 upgrade trap (E3).
- None of these threatens existing production services.

### 3.3 Rejected alternatives

| Alternative | Why rejected |
|---|---|
| **A Proxmox VM instead of an LXC** | E4: `modules/vm-dev` has never been applied, carries legacy telmate disk blocks, a required-with-no-default `ci_password`, no guest agent (so no IP), and a template on the wrong node. The isolation premium it buys is priced for untrusted users, which do not exist here (E2). **Revisit when a second untrusted user appears — not before.** |
| **`privileged = false` for workspaces** | Removes nested Docker without removing the escalation surface that matters: the workspace user already has passwordless sudo *inside the container*, and the template depends on it (`main.tf:341,353,378`; `sudo -n true` is an acceptance criterion). Costs the `docker run hello-world` proof; buys nothing measurable for one operator. |
| **Solving sysbox** | Three independent blockers: the upstream issue (nestybox/sysbox#1011) is **open with no maintainer response**; **sysbox inside LXC is unsupported per the maintainer** (nestybox/sysbox#860); **Debian 13 is absent from sysbox's distro-compat table**. Would consume the PoC's entire budget to answer a question the PoC is not asking. |
| **Including Hermes / OpenMemory / Langfuse** | Each is a design project in its own right — Hermes needs a `sandbox.py` and a ~150-line broker that do not exist; OpenMemory needs a 5-file provider/auth/dimension refactor and cannot boot off Azure at all; Langfuse's pinned version is unresolved and v3 would drag in ClickHouse + Redis + MinIO on an 8 GB host. None is needed to answer "does it port?" |
| **Running the PoC on an existing CT** | Would entangle a working project container with an experiment that provisions a control plane, a database and a reverse proxy. A disposable CT is the point. |

### 3.4 Reconciliation with `docs/forge-reuse-and-proxmox-findings.md` (2026-07-30)

The prior document remains **substantially correct** and should be **retained, not superseded**. This
proposal narrows its scope to a PoC and overturns exactly one of its structural recommendations.

**Agreements (adopted unchanged):**

- The `/opt/coder/secrets` → `/run/secrets` → `~/.config/forge/*.env` contract is the seam, and
  empty-means-disabled is honoured by every consumer (§1.2, §3 "What NOT to change" items 1–2).
- Do **not** fork `coder/templates/forge/main.tf`. Add variables.
- Do **not** move the Azure Terraform root; a Proxmox root is a **sibling**, not a relocation.
- `docker_image "main" { keep_locally = true }` means **no registry is needed** (B10, `main.tf:550`).
- The GitHub OAuth App is blocking, and `data "coder_external_auth" "github"` should gain
  `optional = true` regardless (§4 Phase 1 step 9). Independently re-derived here as E6.
- Wildcard TLS is **optional** for phase 1; the reason DNS-01 is needed is **no inbound**, not
  wildcards (Appendix A). Adopted verbatim.
- Keep wildcards out of `fqdn_dns_records` (Appendix A). Adopted verbatim.
- VMID 166 is a phantom uncommitted block that must be stashed before planning (Appendix A). **Re-verified
  in this pass** via `git diff`.
- Pin `FORGE_AGENTIC_AI_REF` in `coder_agent.main.env` (`main.tf:160-162`) so a merge to agentic-ai
  `main` cannot change the PoC mid-flight. **Kept.**

**Differences (this proposal diverges, with reasons):**

| Prior document | This proposal | Why |
|---|---|---|
| **"QEMU VM, not LXC"** (§4 Phase 1) — four arguments: privileged blast radius; overlay2-on-overlay; guest-owned swap; two prior LXC cgroup incidents | **Unprivileged LXC, CT 167** | Two of the four arguments are overturned by E2's measurement (blast radius ends at the LXC's user namespace; the workspace user already holds in-container root). **Two survive and are carried forward as risks, not as blockers:** guest-owned swap (§2.3) and the overlay/ZFS question (§Open Questions). The deciding factor is E4: the VM path's own module has never been applied and is broken in four documented ways. |
| **"No HA, no replication"** for the Coder host | **Standard project-CT HA** — both peers, `standard` rule | The prior reasoning was VM-specific: a 16 GB VM did not fit on pve2 (measured ~12 GB free, 2026-07-30) so a strict-0 rule would relocate to a node that could not run it. An **8 GB LXC** fits the established project-CT envelope. The prior document's underlying rule — *never HA without a matching `/etc/pve/replication.cfg` entry* (the ct:151 failure) — is **preserved and strengthened**: both peers, via the Ansible roles. |
| **Heavy Phase 0** (CI wiring, leak deletion, `modules/vm-dev` validation, C1 hook-scope fix) | **Minimal Phase 0** (operator credentials, `FORGE_AGENTIC_AI_REF` pin, comment-drift fix) | CI wiring and the Saply leak deletions (`saply-cv-workflow.skill`, `saplyCLI.jar`) are **productisation** work, correctly gating a *tenant cut* — not a PoC. CI cannot apply to Proxmox anyway (GitHub-hosted runners have no LAN route; prior §5 decision 14). `modules/vm-dev` validation is **moot** once the VM path is rejected. C1 is kept only as an **acceptance restatement** ("2 global registrations in `$HOME` **and** 18 in the resolved project root"), not as a fix. |
| Sysbox blamed on **Docker version incompatibility** | Sysbox blamed on the **time-namespace default flip** (E3), fixable by a daemon flag | Correction, with the caveat that the upstream issue is still open. The prior document repeated forge-platform's own framing without challenging it. |
| Skill count "**211 SKILL.md**" | **211 confirmed** at `87ec24a` | The prior document was right; the "231" figure in circulation does not reproduce. |
| Repos read at `e025bc5` / `ff02e19` | Now `2b27a95` / `87ec24a` | Line references were spot-checked this session and held for `coder/templates/forge/main.tf` (`:559-566`, `:401-405`, `:56-99`, `:550`), `docs/coder/setup.md:149-156`, `docs/coder/orchestration-adr.md:32-33`, `forge-workspace-cleanup.sh:14-26`, `workspace/Dockerfile:61-68`. **Citations outside those files have not been re-verified against the newer commits.** |

---

## Section 4: Detailed Change Proposals

### 4.1 New product artifact set — `planning-artifacts/products/forge-platform/`

Mirrors `products/context-stack/`. **None of these exist yet; none is created by this proposal.**

| File | Purpose |
|---|---|
| `README.md` | Product index: status, at-a-glance layer table, artifact index, key decisions, kickoff cheat-sheet, open items. The `context-stack` README is the template. |
| `product-brief.md` | Vision (Forge as a productisable developer platform), the problem (Azure-only, Saply-coupled), PoC scope (in/out — **Hermes/OpenMemory/Langfuse explicitly out**), success measures, and the link to `docs/forge-reuse-and-proxmox-findings.md` as prior art. |
| `prd.md` | FRs for the PoC only — substrate, control plane, workspace, toolkit, acceptance. NFRs: no public ingress, IaC-only provisioning, single-operator security posture, disposability. |
| `architecture.md` | Target topology for CT 167; the `/opt/coder/secrets` contract; the two-Terraform-roots principle; the Azure→self-hosted substitution table (E5); what is deliberately absent and why. |
| `adrs/ADR-001-lxc-over-vm-for-forge-poc.md` | E2 + E4. **Consequence to state explicitly: revisit on a second untrusted user.** |
| `adrs/ADR-002-privileged-workspace-accepted-for-single-operator.md` | The blast-radius measurement, the passwordless-sudo equivalence, and the exact revisit trigger. |
| `adrs/ADR-003-nested-docker-is-not-an-acceptance-gate.md` | E1 — zero automated consumers; soft failure; Playwright is native. |
| `adrs/ADR-004-sysbox-rejected-and-the-docker-29-5-0-trap.md` | E3, including the required `daemon.json` / pin. |
| `adrs/ADR-005-dns-01-wildcard-over-public-ingress.md` | E6.2 + the tailscale-policy citation (**not** "ADR-010"). |
| `adrs/ADR-006-hermes-openmemory-langfuse-out-of-poc-scope.md` | The deferral, with the re-entry conditions. |
| `epics.md` | The five epics in §4.2, with goal / scope / dependencies / AC / exit gate / FR coverage / risks. |
| `sprint-plan.md` | Session-by-session plan with decision gates. |
| `stories/` | INVEST stories per epic, ≤1 session each, frontmatter-tagged. |
| `tests/acceptance.md` | The PoC acceptance gates (§5.3), aggregated from story ACs. |
| `tests/e2e-deployment.md` | The end-to-end runbook: CT create → HA → dev-host → coder-host → image build → template push → first workspace, plus rollback. |
| `readiness-check.md` | PASS / PASS-WITH-NOTES / FAIL gate before the first story runs. |

### 4.2 Proposed epic and story breakdown (PoC scope)

Sizes are **t-shirt estimates**, not story points. No point values are asserted.

**FE0 — Prerequisites and truth (S)** — *blocking; mostly operator, not code*
- FE0-S01 Create the GitHub OAuth App; record `CODER_EXTERNAL_AUTH_0_*`; verify the grant covers
  `tomamourette/agentic-ai` **[operator, BLOCKING]**
- FE0-S02 Mint the Cloudflare DNS-edit token scoped to `bi-services.be` **[operator, BLOCKING]**
- FE0-S03 Pin `FORGE_AGENTIC_AI_REF` to a tag in `coder_agent.main.env` (`main.tf:160-162`)
- FE0-S04 Fix the comment drift: `main.tf:399-404` and `:559-566`, `docs/coder/setup.md:149-156`,
  `docs/coder/orchestration-adr.md` sysbox mentions — the docs describe sysbox, the code runs privileged
- FE0-S05 Stash or exclude the uncommitted `ct_sparkle_vlabel` (VMID 166) block; decide its fate

**FE1 — Substrate: CT 167 on the established pattern (S)**
- FE1-S01 Terraform module block + `outputs.tf` registration; **set `swap_mb` explicitly**
- FE1-S02 Narrow `-target`ed plan; verify only the expected resources; apply
- FE1-S03 HA: replication jobs `167-0`/`167-1` (both peers) + `standard` rule membership, **via the
  Ansible roles only**
- FE1-S04 Inventory + `host_vars/ct-forge-01/main.yml` with `project_name` (or `dev-host` aborts
  mid-run); run `dev-host-setup.yml`
- FE1-S05 Re-run the E2 privilege measurement on CT 167 (Debian 13, `keyctl=1`) and record the result

**FE2 — Control plane: Coder + Postgres 16 + TLS (M)**
- FE2-S01 `forge-coder-host` Ansible role: coderd from a checksum-verified pinned `.deb`
- FE2-S02 Local Postgres 16 + role + database (no extensions)
- FE2-S03 `/opt/coder/secrets` 0700 with **six empty 0600 files**; **do not** create the mnemosyne pair
- FE2-S04 `/etc/coder.d/coder.env` with the OIDC and ADO blocks dropped; password auth on
- FE2-S05 Caddy with a **static** site block + DNS-01 via `caddy-dns/cloudflare`; token as a 0600 root
  `EnvironmentFile`
- FE2-S06 `daemon.json` with `{"features":{"time-namespaces":false}}` **and** a Docker version pin (E3)

**FE3 — Workspace: template de-Azured and building locally (M)**
- FE3-S01 forge-platform branch: `local.image` → local build; **four new `variable`s driving both the
  `coder_parameter` defaults and their validation maxima** (§2.3)
- FE3-S02 Replace the two Saply heredocs (`main.tf:171-270`); add `company-overlay` to
  `local.repo_deny` (it is currently cloned twice)
- FE3-S03 Parameterise `forge-sync.sh` (org, repos, ADO block) preserving the per-repo flags and the
  distinct failure messages
- FE3-S04 Gate the Azure blocks in `forge-onboard.sh`, **including `:103` `az account show`** — it will
  otherwise prompt for a login of a binary that no longer exists
- FE3-S05 Decide `intellij_gateway`: keep it (every workspace build then needs registry.coder.com
  egress) or remove it. **`terraform validate` in that directory fails if this is left undecided.**
- FE3-S06 Clone forge-platform onto CT 167; `docker build`; `coder templates push`

**FE4 — Toolkit and acceptance (M)**
- FE4-S01 First workspace create; agentic-ai reaches the workspace via the GitHub token
- FE4-S02 Run the acceptance gates (§5.3); record every result including failures
- FE4-S03 PBS backup of CT 167 to pve3-pbs
- FE4-S04 PoC verdict: **PORTS / PORTS-WITH-CAVEATS / DOES-NOT-PORT**, with the caveats enumerated
- FE4-S05 Retrospective; decide whether to open a productisation phase (tenancy cut, OpenMemory,
  Hermes) or stop

### 4.3 Edits to existing artifacts

| Artifact | Edit | Rationale |
|---|---|---|
| `planning-artifacts/prd.md` | **None** | §2.2 — different product. |
| `planning-artifacts/epics.md` | **None** | §2.1 — no epic affected. |
| `planning-artifacts/architecture.md` | **None** | No claim invalidated. |
| `implementation-artifacts/sprint-status.yaml` | **None** | Forge gets its own status file — see §6. |
| `docs/forge-reuse-and-proxmox-findings.md` | **Commit it** (currently untracked) and add a dated header pointing to this proposal and to §3.4 | An untracked 352-line analysis is one `git clean` from gone. |
| `homelab-infra/terraform/envs/homelab/main.tf` | Stash/resolve `ct_sparkle_vlabel`; add `module "ct_forge_01"` | FE0-S05, FE1-S01 |
| `homelab-infra/terraform/envs/homelab/outputs.tf` | Two appends | FE1-S01 |
| `homelab-infra/ansible/roles/pve-ha-replication/defaults/main.yml` | Two jobs | FE1-S03 |
| `homelab-infra/ansible/roles/pve-ha-rules/defaults/main.yml` | One resource + rule CSV | FE1-S03 |
| `homelab-playbook/wiki/` | A `ct-forge-01` project page after the PoC concludes | Wiki is operator SoT |
| Auto-memory `MEMORY.md` | One line after FE1 | Runbook §9 |

---

## Section 5: Implementation Handoff

### 5.1 Scope classification: **MODERATE**

**Why not Minor:** it creates a new product artifact set (~15 files plus stories), provisions new
production infrastructure, and spans **four** repositories — `homelab-infra` (Terraform + Ansible),
`homelab-playbook` (artifacts + wiki), `homelab-apps` (only if a LAN wildcard is pursued), and the
external `forge-platform`. That is more than a story-level scope revision.

**Why not Major:** nothing existing is invalidated, replanned, or rolled back. Zero epics change, zero
FRs change, the PRD and architecture are untouched, and the MVP is not reopened. The change is
**purely additive** and reversible by destroying one CT.

**Comparison to house precedent:** `sprint-change-proposal-2026-04-24.md` classified *"scope revision
on two existing stories plus three new stories"* as **Minor**. This is materially larger — a whole
product line — but it touches nothing that already shipped. **Moderate** is the honest middle.

### 5.2 Who does what

| Role | Responsibility |
|---|---|
| **Operator (tomamourette)** | FE0-S01, FE0-S02 (**both blocking, cannot be delegated**). Approve this proposal. Approve `terraform apply`. Decide the pve3 capacity question (8 GB vs 12 GB, §2.3). Decide `intellij_gateway` (FE3-S05). Decide the fate of `ct_sparkle_vlabel`. Judge the PoC verdict. |
| **BMad PM / Analyst** | Author the `products/forge-platform/` artifact set after approval. |
| **BMad Architect** | ADR-001 … ADR-006. |
| **BMad SM** | Story files from §4.2; sprint plan; readiness check. |
| **BMad Dev** | FE1–FE4 implementation, against the existing runbook and roles. |
| **This proposal** | Documents the change. Creates **no** product artifacts, edits **no** `sprint-status.yaml`, commits **nothing**. |

### 5.3 Success criteria (PoC acceptance gates)

Adapted from the prior document's phase-1 gates, with its own corrections applied. **From a tailnet
client not on the LAN:**

| # | Gate | Note |
|---|---|---|
| a | Coder's web UI and code-server open over a **browser-trusted certificate** with no warning | Wildcard SAN **not** asserted — `coder_app "code_server"` is `subdomain = false` |
| b | `~/workspace/repos/github/` contains ≥1 repo cloned via `coder external-auth access-token github`, **and** `~/workspace/repos/github/company-overlay` does **not** exist | Proves E6.1 and the double-clone fix |
| c | `~/.forge-toolchain` lists claude, codex, gh, terraform, and reports both API keys unset | Subscription-auth path intact |
| d | `ls ~/.claude/skills \| wc -l` ≥ 200, **and** `~/.claude/settings.json` has the **2** global registrations, **and** the resolved project root's `.claude/settings.json` has **18** | Restated per C1 — 18-in-HOME is false |
| e | `claude` starts under subscription OAuth and answers one prompt | The actual product value |
| f | `~/.config/forge/openmemory.env` and `langfuse.env` are both **zero-byte**, the build log contains both "skipped" lines, and `sudo -n true` succeeds | Proves the empty-file contract end to end |
| g | `docker run --rm hello-world` succeeds inside the workspace | **Non-gating** per E1/ADR-003. Record the result either way. |
| h | `free -g` on pve3 shows headroom with the workspace running; CT 167 is not swap-thrashing | The §2.3 sizing conflict, measured |
| i | Wall-clock create → code-server-reachable is recorded | Baseline for any future optimisation |
| j | `terraform plan` on the homelab root is clean apart from the intended CT; the `ct_sparkle_vlabel` phantom has not been recreated | Regression guard |
| k | HA: `ha-manager status` shows `ct:167 (pve3, started)` **and** `/etc/pve/replication.cfg` has **both** `167-0` and `167-1` | The ct:151 lesson |

**PoC verdict is a single explicit call in FE4-S04: PORTS / PORTS-WITH-CAVEATS / DOES-NOT-PORT.**
Anything less than an explicit verdict means the PoC did not do its job.

### 5.4 Blocking operator prerequisites

> **Nothing in FE1–FE4 should start before both of these exist.**

1. **GitHub OAuth App** → `CODER_EXTERNAL_AUTH_0_ID/TYPE/CLIENT_ID/CLIENT_SECRET`.
   Without it the workspace build **fails** (`data "coder_external_auth" "github"` at
   `coder/templates/forge/main.tf:25-27` has no `optional = true`), and even if it did not, the
   `forge-sync.sh` clone block **silently skips**, so agentic-ai never lands and gates (b)–(e) are
   untestable. **The only non-optional external credential in the whole PoC.**
2. **Cloudflare API token**, DNS-edit scope, zone `bi-services.be`.
   Required for **any** browser-trusted certificate — the homelab has no inbound :80/:443, so HTTP-01
   is impossible, not merely inconvenient. Wildcard scope is optional; the token is not.

---

## Section 6: Proposed `sprint-status.yaml` changes

**NOT APPLIED.** Two changes are proposed, in preference order.

### 6.1 Preferred: a **new** status file — `implementation-artifacts/sprint-status-forge-platform.yaml`

Forge is a separate product, and the estate already keeps per-product status files
(`sprint-status-production-readiness.yaml`, `sprint-status-pve3-storage-migration.yaml`,
`hybrid-gemma-serving-sprint-status.md`). Proposed initial content:

```yaml
generated: 2026-09-09
last_updated: 2026-09-09
project: forge-platform - self-hosted PoC on Proxmox
project_key: NOKEY
tracking_system: file-system
story_location: homelab-playbook/_bmad-output/implementation-artifacts
source_proposal: planning-artifacts/sprint-change-proposal-2026-09-09.md

development_status:
  # FE0: Prerequisites and truth (BLOCKING — two operator credentials)
  epic-fe0: backlog
  fe0-s01-github-oauth-app: backlog            # OPERATOR, BLOCKING
  fe0-s02-cloudflare-dns-token: backlog        # OPERATOR, BLOCKING
  fe0-s03-pin-forge-agentic-ai-ref: backlog
  fe0-s04-fix-sysbox-comment-drift: backlog
  fe0-s05-resolve-ct-sparkle-vlabel-phantom: backlog

  # FE1: Substrate — CT 167 ct-forge-01 on pve3
  epic-fe1: backlog
  fe1-s01-terraform-module-and-outputs: backlog
  fe1-s02-targeted-plan-and-apply: backlog
  fe1-s03-ha-replication-both-peers-and-rule: backlog
  fe1-s04-inventory-host-vars-and-dev-host: backlog
  fe1-s05-verify-privileged-docker-in-lxc: backlog

  # FE2: Control plane — Coder + Postgres 16 + TLS
  epic-fe2: backlog
  fe2-s01-forge-coder-host-role-coderd: backlog
  fe2-s02-postgres-16-local: backlog
  fe2-s03-opt-coder-secrets-six-empty-files: backlog
  fe2-s04-coder-env-password-auth: backlog
  fe2-s05-caddy-static-block-dns01: backlog
  fe2-s06-docker-daemon-time-namespaces-off-and-pin: backlog

  # FE3: Workspace — template de-Azured
  epic-fe3: backlog
  fe3-s01-template-variables-image-and-sizing: backlog
  fe3-s02-replace-saply-heredocs-and-repo-deny: backlog
  fe3-s03-parameterise-forge-sync: backlog
  fe3-s04-gate-azure-blocks-in-forge-onboard: backlog
  fe3-s05-decide-intellij-gateway: backlog
  fe3-s06-build-image-and-template-push: backlog

  # FE4: Toolkit and acceptance
  epic-fe4: backlog
  fe4-s01-first-workspace-create: backlog
  fe4-s02-run-acceptance-gates-a-to-k: backlog
  fe4-s03-pbs-backup-ct167: backlog
  fe4-s04-poc-verdict: backlog
  fe4-s05-retrospective-and-next-phase-decision: backlog
  epic-fe4-retrospective: optional
```

### 6.2 Fallback: append to the existing `implementation-artifacts/sprint-status.yaml`

Only if the operator prefers a single tracking file. The exact diff would be the `development_status`
block above, appended verbatim after `epic-8-retrospective`, plus a `last_updated: 2026-09-09` bump and
a `# --- Forge Platform PoC (added 2026-09-09, SCP-forge-poc) ---` separator comment matching the
existing house style.

**Not recommended** — that file's header declares `project: homelab - AI Dev Container`, and mixing a
second product into it repeats the `environments/`-means-tenant overloading that the prior findings
document identifies as finding A7.

**Neither change is applied by this document.**

---

## Open Questions / Risks

**R1 — Comment drift in forge-platform: the docs describe sysbox, the code runs privileged.**
`coder/templates/forge/main.tf:399-404` still says *"the workspace runs under the sysbox runtime →
unprivileged docker-in-docker"* — **62 lines above `privileged = true` at `:566`**. The same claim
persists in `docs/coder/orchestration-adr.md` (~9 sysbox mentions, including the "Current architecture
(pilot)" section) and in `workspace/Dockerfile`. `docs/coder/setup.md:141-146` is the only place that
states the truth. An engineer porting this reads the comment first and ports the wrong architecture.
**FE0-S04 fixes this before anyone builds on it.** *Risk: low severity, high likelihood of wasted time.*

**R2 — The Docker 29.5.0 upgrade trap is scheduled, not avoided.**
CT 250 measured Docker **29.3.1**, below the 29.5.0 time-namespace flip, so the failure mode **cannot
reproduce today**. The next `apt upgrade` on CT 167 crosses that line. Without FE2-S06 (`daemon.json`
`{"features":{"time-namespaces":false}}` **plus** a version pin), the PoC works on day one and breaks
on an unrelated maintenance day, with a symptom (`namespace {"time" ""} does not exist`) that looks
nothing like its cause. *Risk: medium severity, high likelihood if unmitigated.*

**R3 — `docs/forge-reuse-and-proxmox-findings.md` already exists, is untracked, and is 40 days stale.**
It is a 352-line analysis of this exact question, sitting **untracked** in the working tree, written
against `forge-platform @ e025bc5` / `agentic-ai @ ff02e19`; both repos have since moved to `2b27a95` /
`87ec24a`. **Resolution: reconcile, do not supersede.** §3.4 records the agreements and the four
divergences. **Action: commit the file** with a dated header pointing at this proposal. Its file:line
citations outside the seven files spot-checked in this pass **have not been re-verified** and should be
treated as approximately-correct rather than exact. *Risk: medium — the divergences (LXC vs VM, HA vs
no-HA) are load-bearing, and two contradictory documents in the tree is worse than one stale one.*

**R4 — Workspace sizing vs an 8 GB CT (see §2.3).**
Template defaults are 12288 MB RAM / 20480 MB swap. The `coder_parameter` minimum is 2048, so a
workspace *can* be created small — but only by remembering to, every time, and swap has no answer
inside an unprivileged LXC (`swap_mb` defaults to 512 in `modules/ct-debian`). **Decision needed before
FE1-S01:** four real `variable`s in the template (FE3-S01) *and* an explicit `swap_mb`, or size CT 167
at 4C/12GB. *Risk: high likelihood, medium severity — it surfaces as an OOM at first workspace boot.*

**R5 — Nested-nested Docker on a ZFS-backed LXC rootfs is untested.**
The workspace's inner dockerd writes to `docker_volume.dockerd`, which exists specifically because
*"overlay2 cannot stack on overlay"* (`coder/templates/forge/main.tf:541-548, 585-588`). On CT 167 that
volume lives on the **outer** Docker's data root, on the LXC's **ZFS** rootfs. Docker on ZFS works
(every project CT runs it via `dev-host`), and one nesting level is proven — **two levels is not.**
This is the strongest surviving argument from the prior document's VM recommendation. Mitigation: E1
says gate (g) is non-gating, so a failure here degrades the PoC rather than ending it. *Risk: medium
likelihood, low severity given ADR-003.*

**R6 — HA on a 3-node rule while pve1's reliability is unresolved.**
The `standard` rule spans pve1/pve2/pve3, and the runbook requires replication to **both** peers. Prior
capacity measurement (2026-07-30) put pve2 at ~12 GB free, and pve1 has a recorded hard-hang cycle.
Replication to both peers is correct and non-negotiable; whether `ct:167` should register `started` or
`stopped` per the Project-CT HA Policy is an **operator call at FE1-S03**. *Open question, not a risk
to close in this document.*

**R7 — The "ADR-010 no-public-ingress" citation does not resolve (see E6).**
No such ADR exists in any tracked repo. The policy is real and lives in
`wiki/architecture/tailscale-policy.md:20-31` and `wiki/architecture/remote-access-topology.md`.
Every downstream artifact must cite those. *Risk: low, but it propagates — a fabricated citation
repeated into six ADRs is expensive to unpick.*

**R8 — Scope creep from the PoC into productisation.**
The prior document's §5 lists **16 decisions that are the platform owner's, not the engineer's**, four
of which block the tenant manifest schema. **None of them blocks the PoC**, and none should be answered
inside it. The PoC's only question is *"does it port?"*. **FE4-S05 is the gate where productisation may
be opened — not before.** *Risk: high likelihood, high cost. This is the failure mode most likely to
actually occur.*

---

## Approval

Operator: tomamourette — **approved**
Date: 2026-09-09
Decision: ☑ Approved as written ☐ Approved with modifications ☐ Rejected

Approved without modification. The open sizing decision (**R4** in the risk register / workspace `coder_parameter`
defaults of 12288 MB RAM + 20480 MB swap vs. the CT's allocation) remains an open item to be
resolved before FE1-S01, as recorded in the risk register — approval does not settle it.

**On approval, the next action is authoring `planning-artifacts/products/forge-platform/` per §4.1.
Implementation (FE1+) does not start until §5.4's two operator prerequisites exist.**
