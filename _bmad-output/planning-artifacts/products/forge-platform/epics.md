---
type: epics
product: forge-platform
version: 1.0.0-draft
status: draft
date: 2026-09-09
authors: tomamourette (with BMad assist)
brief_ref: product-brief.md
prd_ref: prd.md
arch_ref: architecture.md
source_proposal: ../../sprint-change-proposal-2026-09-09.md
---

# Forge Platform — Epic Plan (PoC scope)

This artifact decomposes the Forge PoC into the five epics **FE0–FE4** defined in §4.2 of the
approved sprint change proposal. The epic and story IDs are **not invented here** — they are lifted
verbatim from §4.2 and must stay in lockstep with
`implementation-artifacts/sprint-status-forge-platform.yaml` (§6.1 of the proposal).

Sizes are **t-shirt estimates, not commitments**. **No story points are asserted.**

> **The whole of FE1–FE4 is blocked.** Per §5.4 of the proposal, nothing in FE1–FE4 starts before
> **both** operator prerequisites exist: a **GitHub OAuth App** (FE0-S01) and a **Cloudflare
> DNS-edit token** for `bi-services.be` (FE0-S02). Neither can be delivered by code. See §2.
>
> **FE1-S01 carries a second block:** the sizing decision (`prd.md` §11.1 / R4) is **unresolved**,
> and the operator's approval of the proposal explicitly did not settle it.

---

## 1. Epic Map

| Epic | Name | Goal (one sentence) | Size (est.) | Depends on | Exit gate summary | FR coverage |
|---|---|---|---|---|---|---|
| **FE0** | Prerequisites and truth | Land the two operator credentials that cannot be delegated, and correct the three pieces of repo state that would otherwise mislead or damage the work. | **S** — mostly operator, not code | None | Both credentials recorded; `FORGE_AGENTIC_AI_REF` pinned; sysbox comment drift corrected; the VMID 166 phantom neutralised | FR-PRE-001…006 = **6** |
| **FE1** | Substrate: CT 167 on the established pattern | Provision `ct-forge-01` on pve3 through the estate's standard project-CT runbook, with HA replication to both peers, and convert the CT 250 privilege inference into a measurement. | **S** | FE0 complete; **R4 resolved** | Gates (j) and (k) green; FE1-S05 result recorded whatever it is | FR-SUB-001…007 = **7** |
| **FE2** | Control plane: Coder + Postgres 16 + TLS | Stand up coderd, a local Postgres 16, the secrets seam and a browser-trusted certificate over DNS-01 — with no new public inbound ingress. | **M** | FE1 complete | Gate (a) green; `daemon.json` + Docker pin in place | FR-CTL-001…007 = **7** |
| **FE3** | Workspace: template de-Azured and building locally | Branch `forge-platform`, remove the Azure and Saply couplings from the workspace template, build the image locally and push the template. | **M** | FE2 complete | `coder templates push` succeeds; `intellij_gateway` decided (`terraform validate` fails while undecided) | FR-WS-001…009 = **9** |
| **FE4** | Toolkit and acceptance | Create the first workspace, run every acceptance gate from a tailnet client, and publish one explicit verdict. | **M** | FE3 complete | All eleven gates run and recorded; an explicit verdict published | FR-KIT-001…006 = **6** |

**Total FR coverage: 6 + 7 + 7 + 9 + 6 = 28 / 28.** Audited in §7.

**Total effort: M–L, two to four working sessions** — *if the operator prerequisites land first*
(proposal §3.2). Overall risk **MEDIUM**; nothing here threatens an existing production service.

---

## 2. The blocking prerequisites (§5.4) — read before anything else

> **1. A GitHub OAuth App** → `CODER_EXTERNAL_AUTH_0_ID/TYPE/CLIENT_ID/CLIENT_SECRET`.
> **The only non-optional external credential in the whole PoC.**
> `data "coder_external_auth" "github"` (`coder/templates/forge/main.tf:25-27`) lacks
> `optional = true` — unlike the azuredevops provider at `:32-35` — so the **workspace build
> fails** without it. And even if the build were made to pass, `forge-sync.sh` sources its token
> from `coder external-auth access-token github` and **silently skips its entire clone block** when
> the token is absent, so agentic-ai never reaches the workspace and gates (b)–(e) are untestable.
> **FE0-S01. Operator only; cannot be delegated.**
>
> **2. A Cloudflare API token**, DNS-edit scope, zone `bi-services.be`.
> Required for **any** browser-trusted certificate: the homelab has no inbound :80/:443, so
> HTTP-01 is **impossible**, not merely inconvenient. ~~The **wildcard scope is optional** —
> `coder_app "code_server"` sets `subdomain = false`, so code-server is path-proxied and exercises
> no wildcard.~~ **The token is not optional.**
>
> **REVERSED 2026-09-09 — a wildcard IS required.** Coder's preview URLs are subdomain-based and
> `CODER_WILDCARD_ACCESS_URL=*.forge.bi-services.be` is live on CT 167, so the certificate carries
> both `forge.bi-services.be` and `*.forge.bi-services.be`. The **token** clause is unaffected: one
> `Zone.DNS Edit` grant still covers it, no re-scoping. See
> [adrs/ADR-005](adrs/ADR-005-dns-01-wildcard-over-public-ingress.md).
> **FE0-S02. Operator only; cannot be delegated.**

Both are FE0 stories precisely so they are visible at the top of the plan rather than discovered at
first workspace build.

---

## 3. Sequencing

```
FE0 Prerequisites and truth
 │   (S — mostly operator)
 │   ├─ FE0-S01 GitHub OAuth App          [OPERATOR, BLOCKING]
 │   └─ FE0-S02 Cloudflare DNS token      [OPERATOR, BLOCKING]
 │
 ├──► GATE G0 ──── both credentials exist? AND the R4 sizing decision made?
 │                   └─ no  → STOP. FE1 does not start.
 │                   └─ yes → proceed
 ▼
FE1 Substrate (S)          ──► GATE G1 — gates (j) + (k) green; FE1-S05 recorded
 ▼
FE2 Control plane (M)      ──► GATE G2 — gate (a) green; daemon.json + pin in place
 ▼
FE3 Workspace (M)          ──► GATE G3 — templates push OK; intellij_gateway decided
 ▼
FE4 Toolkit + acceptance (M) ──► GATE G4 — eleven gates run and recorded
                                  │
                                  └──► FE4-S04 verdict: PORTS / PORTS-WITH-CAVEATS / DOES-NOT-PORT
                                       └──► FE4-S05 GATE G5 — the ONLY point at which
                                            productisation may be opened (R8)
```

The chain is strictly serial. FE1 cannot be parallelised against FE2 because FE2's Ansible role
targets a host that FE1 creates; FE3 builds an image on that host; FE4 exercises what FE3 pushed.
FE0's two non-operator stories (FE0-S03, FE0-S04) are repo edits that *could* be done at any time,
but doing them first is the point — FE0-S04 exists so nobody ports the wrong architecture.

---

## 4. Epic detail

### 4.1 FE0 — Prerequisites and truth (**S**, blocking, mostly operator)

**Goal.** Land the two credentials that cannot be delivered by code, and correct three pieces of
repo state that would otherwise mislead the implementation or damage the estate.

**Scope — in:** the GitHub OAuth App and its `optional = true` companion fix; the Cloudflare
DNS-edit token; pinning `FORGE_AGENTIC_AI_REF`; correcting the sysbox comment drift in
forge-platform's code and docs; neutralising the uncommitted VMID 166 phantom block.

**Scope — out:** any provisioning; any Coder or Postgres work; committing
`docs/forge-reuse-and-proxmox-findings.md` (that is an action on the proposal, §4.3, not a story
here); deciding the R4 sizing question (an operator decision recorded in `prd.md` §11.1, gated at
G0 rather than owned by a story).

**Dependencies.** None. FE0 runs against current repo state.

**Stories.**

| ID | Title | Size | Owner | FRs |
|---|---|---|---|---|
| FE0-S01 | Create the GitHub OAuth App; record `CODER_EXTERNAL_AUTH_0_*`; verify the grant covers `tomamourette/agentic-ai` | S | **operator, BLOCKING** | FR-PRE-001, FR-PRE-003 |
| FE0-S02 | Mint the Cloudflare DNS-edit token scoped to `bi-services.be` | S | **operator, BLOCKING** | FR-PRE-002 |
| FE0-S03 | Pin `FORGE_AGENTIC_AI_REF` to a tag in `coder_agent.main.env` (`main.tf:160-162`) | XS | dev | FR-PRE-004 |
| FE0-S04 | Fix the comment drift: `main.tf:399-404` and `:559-566`, `docs/coder/setup.md:149-156`, `docs/coder/orchestration-adr.md` sysbox mentions | S | dev | FR-PRE-005 |
| FE0-S05 | Stash or exclude the uncommitted `ct_sparkle_vlabel` (VMID 166) block; decide its fate | XS | dev + **operator decision** | FR-PRE-006 |

**Epic acceptance criteria.**

1. `CODER_EXTERNAL_AUTH_0_ID/TYPE/CLIENT_ID/CLIENT_SECRET` are recorded and the grant demonstrably
   covers `tomamourette/agentic-ai`.
2. A Cloudflare API token with DNS-edit scope on `bi-services.be` exists and is stored 0600
   root-owned (NFR-SEC-003).
3. `data "coder_external_auth" "github"` carries `optional = true`.
4. `FORGE_AGENTIC_AI_REF` names a tag, not a branch.
5. No file in `repos/forge-platform` claims the workspace runs under sysbox where it in fact runs
   `privileged = true`; `docs/coder/setup.md:141-146` is no longer the only truthful statement.
6. A `terraform plan` against the homelab root does **not** propose creating `ct_sparkle_vlabel`,
   and the operator has recorded a decision on the block's fate.

**Exit gate (G0 — proceed to FE1?).** All six above, **and** the R4 sizing decision in
`prd.md` §11.1 has been taken by the operator. **If either half is missing, FE1 does not start.**
This is the hard stop of the plan.

**Risks.** R1 (comment drift — this epic is its mitigation), R7 (the fabricated ADR-010 citation —
FE0-S02 is the first place the correct policy citation appears), R3 (the stale prior document —
handled at proposal level, but FE0 is when its divergences become load-bearing).

---

### 4.2 FE1 — Substrate: CT 167 on the established pattern (**S**)

**Goal.** Provision `ct-forge-01` — VMID 167, pve3, 4C/8GB/50GB, Debian 13,
`features=nesting=1,keyctl=1`, 192.168.50.167 — through the estate's standard project-CT runbook,
with HA replication to **both** peers, and convert the CT 250 privilege inference into a
measurement on the real container.

**Scope — in:** one `module "ct_forge_01"` block using `../../modules/ct-debian` mirroring
`ct_saply_ai`; two `outputs.tf` appends; an explicit `swap_mb`; a narrowly `-target`ed plan and
apply; replication jobs `167-0` and `167-1` plus `standard`-rule membership **via the Ansible roles
only**; inventory + `host_vars/ct-forge-01/main.yml` with `project_name`; `dev-host-setup.yml`; the
FE1-S05 privilege measurement.

**Scope — out:** anything Coder, Postgres or Caddy (FE2); Grafana dashboards (NFR-OBS-001 —
monitoring is auto-derived); any manual `ha-manager` or `pvesr` invocation (break-glass only).

**Dependencies.** FE0 complete **and** G0 passed, including the R4 sizing decision — because
FE1-S01 is where `swap_mb` and the CT's memory allocation are written down.

**Stories.**

| ID | Title | Size | FRs | Gates |
|---|---|---|---|---|
| FE1-S01 | Terraform module block + `outputs.tf` registration; **set `swap_mb` explicitly** | S | FR-SUB-001, 002, 003 | — |
| FE1-S02 | Narrow `-target`ed plan; verify only the expected resources; apply | S | FR-SUB-004 | j |
| FE1-S03 | HA: replication jobs `167-0`/`167-1` (both peers) + `standard` rule membership, **via the Ansible roles only** | S | FR-SUB-005 | k |
| FE1-S04 | Inventory + `host_vars/ct-forge-01/main.yml` with `project_name`; run `dev-host-setup.yml` | S | FR-SUB-006 | — |
| FE1-S05 | Re-run the E2 privilege measurement on CT 167 (Debian 13, `keyctl=1`) and record the result | XS | FR-SUB-007 | — |

**Epic acceptance criteria.**

1. `pct status 167` reports the container running on pve3 at 192.168.50.167.
2. `swap_mb` is set explicitly in the module block, not inherited from the 512 MB module default.
3. `ct-forge-01.bi-services.be` resolves via the auto-derived Cloudflare A record and Pi-hole
   `custom.list`; **no wildcard has entered `fqdn_dns_records`**.
4. CT 167 appears in `generated/prometheus-node-targets.json`.
5. **Gate (j):** `terraform plan` on the homelab root is clean apart from the intended CT, and the
   `ct_sparkle_vlabel` phantom has not been recreated.
6. **Gate (k):** `ha-manager status` shows `ct:167 (pve3, <state>)` **and**
   `/etc/pve/replication.cfg` contains **both** `167-0` and `167-1`.
7. `dev-host-setup.yml` completes without aborting at `dev-host/tasks/main.yml:205`.
8. The FE1-S05 measurement is recorded — including if it **differs** from CT 250's result. A
   differing result is a finding, not a failure.

**Exit gate (G1 — proceed to FE2?).** AC5, AC6 and AC7 green; AC8 recorded. If replication exists
on only one peer, **stop** — that is the ct:151 failure mode, in which data is safe but failover
lands in `error`.

**Risks.** R4 (the sizing conflict — resolved at G0, written down here), R6 (`ct:167` HA state
`started` vs `stopped` is an **operator call at FE1-S03**, taken against pve1's unresolved hard-hang
history and pve2's ~12 GB measured headroom as of 2026-07-30). R5 is not yet exercised here.

---

### 4.3 FE2 — Control plane: Coder + Postgres 16 + TLS (**M**)

**Goal.** Stand up the control plane on CT 167 — coderd, a local Postgres 16, the secrets seam, a
`coder.env` with the Azure identity blocks removed, and a browser-trusted certificate obtained over
DNS-01 — **adding no new public inbound ingress**.

**Scope — in:** a new `forge-coder-host` Ansible role covering coderd (pinned, checksum-verified
`.deb`), Postgres 16 (no extensions), `/opt/coder/secrets` (0700, six empty 0600 files), the
`coder.env`, a **static** Caddy site block with DNS-01 via `caddy-dns/cloudflare`, and
`/etc/docker/daemon.json` plus a Docker version pin.

**Scope — out:** OIDC / Entra sign-in (dropped — Coder's built-in password auth is already
permitted, `CODER_DISABLE_PASSWORD_AUTH=false`); Azure DevOps external auth (disabled cleanly via
the empty-file contract); `on_demand_tls` and the ask-server on `:9111` (they exist only because
Azure serves arbitrary per-SNI names); the mnemosyne secret pair (**explicitly not created**);
`pgvector` and every other extension.

**Dependencies.** FE1 complete. FE2-S04 additionally needs FE0-S01's credential and FE2-S05 needs
FE0-S02's token — the two blockers become concrete here.

**Stories.**

| ID | Title | Size | FRs | Gates |
|---|---|---|---|---|
| FE2-S01 | `forge-coder-host` Ansible role: coderd from a checksum-verified pinned `.deb` | S | FR-CTL-001 | — |
| FE2-S02 | Local Postgres 16 + role + database (no extensions) | S | FR-CTL-002 | — |
| FE2-S03 | `/opt/coder/secrets` 0700 with **six empty 0600 files**; **do not** create the mnemosyne pair | XS | FR-CTL-003 | f |
| FE2-S04 | `/etc/coder.d/coder.env` with the OIDC and ADO blocks dropped; password auth on | S | FR-CTL-004, FR-CTL-007 | — |
| FE2-S05 | Caddy with a **static** site block + DNS-01 via `caddy-dns/cloudflare`; token as a 0600 root `EnvironmentFile` | M | FR-CTL-005 | a |
| FE2-S06 | `daemon.json` with `{"features":{"time-namespaces":false}}` **and** a Docker version pin | XS | FR-CTL-006 | — |

**Epic acceptance criteria.**

1. `coder version` on CT 167 reports the pinned version, and the `.deb` checksum is recorded.
2. `psql` connects to the Forge database as the dedicated role; `\dx` lists no extensions.
3. `ls -la /opt/coder/secrets` shows a 0700 directory with exactly six 0600 zero-byte files and
   **no** mnemosyne pair.
4. `/etc/coder.d/coder.env` contains no OIDC or ADO block and sets
   `CODER_DISABLE_PASSWORD_AUTH=false`; `CODER_EXTERNAL_AUTH_0_*` are present.
5. **Gate (a):** Coder's web UI opens from a tailnet client **not on the LAN** over a
   browser-trusted certificate with no warning, on **both** SANs — the apex and a preview URL under
   `*.forge.bi-services.be`. ~~Wildcard SAN is **not** asserted.~~ **Amended 2026-09-09:** reversed —
   serving **only the apex** is a **FAIL**. **Second correction, same date:** do not read this as one
   certificate with two SANs — Caddy issues one certificate per name, and CT 167 serves two separate
   Let's Encrypt certificates, both verifying with no `-k`. The requirement is that both names present
   a browser-trusted certificate. Canonical wording and the measurement: `tests/acceptance.md` §2
   gate (a).
6. No new inbound port is exposed anywhere in the estate; the certificate was obtained by an
   **outbound** DNS API call (NFR-SEC-001).
7. `/etc/docker/daemon.json` contains `{"features":{"time-namespaces":false}}` and the Docker
   package is held at a pinned version.

**Exit gate (G2 — proceed to FE3?).** AC5 and AC7 green. AC7 in particular is non-negotiable: it is
the difference between a PoC that works on day one and one that breaks on an unrelated maintenance
day with a symptom that looks nothing like its cause.

**Risks.** R2 (the Docker 29.5.0 trap — FE2-S06 *is* its mitigation), R7 (the ingress citation —
FE2-S05 must cite `wiki/architecture/tailscale-policy.md:20-31` and
`wiki/architecture/remote-access-topology.md`, **never "ADR-010"**).

---

### 4.4 FE3 — Workspace: template de-Azured and building locally (**M**)

**Goal.** On a **branch** of `forge-platform` — never a fork — remove the Azure and Saply couplings
from the workspace template, build the image locally, and push the template to the new control
plane.

**Scope — in:** `local.image` → local `docker build` with `keep_locally = true`; four real
`variable`s over the four `coder_parameter` sizing knobs; replacing the two Saply heredocs; adding
`company-overlay` to `local.repo_deny`; parameterising `forge-sync.sh`; gating the Azure blocks in
`forge-onboard.sh`; deciding `intellij_gateway`; clone, build and `coder templates push`.

**Scope — out:** forking `main.tf` (FR-WS-009 forbids it); any tenancy or manifest work (R8);
removing `privileged = true` (ADR-002 accepts it and §3.3 of the proposal rejects the alternative);
solving sysbox (ADR-004).

**Dependencies.** FE2 complete. FE3-S01's *values* depend on the R4 decision taken at G0.

**Stories.**

| ID | Title | Size | FRs | Gates |
|---|---|---|---|---|
| FE3-S01 | forge-platform branch: `local.image` → local build; **four new `variable`s driving both the `coder_parameter` defaults and their validation maxima** | M | FR-WS-001, 002, 009 | — |
| FE3-S02 | Replace the two Saply heredocs (`main.tf:171-270`); add `company-overlay` to `local.repo_deny` | S | FR-WS-003, 004 | b |
| FE3-S03 | Parameterise `forge-sync.sh` (org, repos, ADO block) preserving the per-repo flags and the distinct failure messages | M | FR-WS-005 | — |
| FE3-S04 | Gate the Azure blocks in `forge-onboard.sh`, **including `:103` `az account show`** | S | FR-WS-006 | — |
| FE3-S05 | Decide `intellij_gateway`: keep it (registry.coder.com egress per build) or remove it | XS + **operator decision** | FR-WS-007 | — |
| FE3-S06 | Clone forge-platform onto CT 167; `docker build`; `coder templates push` | M | FR-WS-008 | — |

**Epic acceptance criteria.**

1. `coder/templates/forge/main.tf` is a branch of upstream, not a fork; the diff is additive
   variables plus targeted edits.
2. `docker images` on CT 167 lists the locally built workspace image; **no registry pull occurred**.
3. Four Terraform `variable`s drive both the `coder_parameter` defaults **and** their validation
   maxima for cpu shares, memory, swap and reservation.
4. `local.repo_deny` includes `company-overlay`.
5. Neither Saply heredoc remains at `main.tf:171-270`.
6. `forge-onboard.sh` completes on a host with no `az` binary — `:103` does not prompt.
7. `intellij_gateway` is **decided**, and `terraform validate` in that directory exits 0.
8. `coder templates push` succeeds.

**Exit gate (G3 — proceed to FE4?).** AC7 and AC8 green. AC7 is a hard gate rather than a
preference: `terraform validate` fails while the question is undecided, so FE3 cannot be closed
around it.

**Risks.** R4 (this epic carries one of the two candidate resolutions — but it does **not** get to
choose it; that is the operator's call at G0), R8 (FE3 is where "while we're in here" productisation
edits are most tempting — they are out of scope).

---

### 4.5 FE4 — Toolkit and acceptance (**M**)

**Goal.** Create the first workspace, prove the toolkit lands, run every acceptance gate from a
tailnet client that is not on the LAN, and **publish one explicit verdict**.

**Scope — in:** first workspace create; agentic-ai arriving via the GitHub external-auth token; all
eleven gates a–k with every result recorded including failures; a PBS backup of CT 167; the verdict;
the retrospective and the next-phase decision.

**Scope — out:** fixing anything the gates reveal beyond what the stories already cover — findings
are **recorded**, not chased (R8); opening productisation before FE4-S05.

**Dependencies.** FE3 complete.

**Stories.**

| ID | Title | Size | FRs | Gates |
|---|---|---|---|---|
| FE4-S01 | First workspace create; agentic-ai reaches the workspace via the GitHub token | S | FR-KIT-001 | b, c, d, e, i |
| FE4-S02 | Run the acceptance gates (§5.3); record every result including failures | M | FR-KIT-002, 003 | a–k |
| FE4-S03 | PBS backup of CT 167 to pve3-pbs | XS | FR-KIT-004 | — |
| FE4-S04 | PoC verdict: **PORTS / PORTS-WITH-CAVEATS / DOES-NOT-PORT**, with the caveats enumerated | S | FR-KIT-005 | — |
| FE4-S05 | Retrospective; decide whether to open a productisation phase or stop | S | FR-KIT-006 | — |

**Epic acceptance criteria.**

1. A workspace is created and `~/workspace/repos/github/` contains at least one repo cloned via
   `coder external-auth access-token github`, **and** `company-overlay` is not among them (gate b).
2. `~/.forge-toolchain` lists claude, codex, gh and terraform, and reports both API keys unset
   (gate c).
3. `ls ~/.claude/skills | wc -l` ≥ 200, `~/.claude/settings.json` has the **2** global
   registrations, and the resolved project root's `.claude/settings.json` has **18** (gate d).
4. `claude` starts under subscription OAuth and answers one prompt (gate e).
5. `~/.config/forge/openmemory.env` and `langfuse.env` are both zero-byte, the build log contains
   both "skipped" lines, and `sudo -n true` succeeds (gate f).
6. Gate (g) is **recorded** — pass or fail. It is **non-gating** per ADR-003, and a failure here is
   the expected shape of R5 materialising.
7. `free -g` on pve3 shows headroom with the workspace running and CT 167 is not swap-thrashing
   (gate h).
8. Wall-clock create → code-server-reachable is recorded (gate i).
9. CT 167 is backed up to pve3-pbs and the job is recorded.
10. **A single explicit verdict is published**, with caveats enumerated.
11. A retrospective is held and the next-phase decision recorded.

**Exit gate (G4 / G5 — product close).** All eleven gates **run and recorded** — note that "run and
recorded" is the gate, not "all passed"; a `DOES-NOT-PORT` verdict backed by evidence is a
**successful outcome of this PoC**. **FE4-S05 is the only point at which productisation may be
opened** (R8).

**Risks.** R5 (double-nested Docker on ZFS — surfaces at gate g, degrades rather than ends the PoC),
R4 (surfaces at gate h, and as an OOM at first workspace boot in FE4-S01), R8 (highest cost, highest
likelihood — FE4-S05 is the containment).

---

## 5. Cross-epic dependencies

| From | To | Nature |
|---|---|---|
| FE0-S01 | FE2-S04, FE3-S03, FE4-S01, gates b–e | The GitHub credential. Without it the workspace build fails and the clone block silently skips. |
| FE0-S02 | FE2-S05, gate a | The Cloudflare token. Without it no browser-trusted certificate is possible at all. |
| FE0-S03 | FE4-S01 | The pinned `FORGE_AGENTIC_AI_REF` is what makes the FE4 result reproducible. |
| FE0-S04 | FE3 (all) | Whoever edits the template reads the comment first. |
| FE0-S05 | FE1-S02, gate j | An un-stashed phantom block recreates a destroyed container on apply. |
| R4 decision (G0) | FE1-S01, FE3-S01 | The `swap_mb` value and the four `variable` values both derive from it. |
| FE1-S01/S02 | FE1-S03, FE1-S04 | The CT must exist before HA or `dev-host`. |
| FE1-S04 | FE2 (all) | `dev-host` provides Docker CE, Node 20 LTS, the Claude Code CLI wrapper, ruflo and pyenv — the base the `forge-coder-host` role builds on. |
| FE2-S03 | gate f | The six-empty-file seam is what gate (f) proves end to end. |
| FE2-S06 | R2 containment | Without it the PoC works on day one and breaks on a later maintenance day. |
| FE3-S02 | gate b | The `company-overlay` double-clone fix is half of gate (b). |
| FE3-S05 | FE3-S06 | `terraform validate` fails while `intellij_gateway` is undecided. |
| FE4-S02 | FE4-S04 | The verdict is only as good as the recorded evidence. |

---

## 6. Risk-to-epic map

| Risk | FE0 | FE1 | FE2 | FE3 | FE4 |
|---|:--:|:--:|:--:|:--:|:--:|
| **R1** comment drift | **mitigated** | | | exposed if unfixed | |
| **R2** Docker 29.5.0 trap | | | **mitigated** | | latent |
| **R3** stale prior document | exposed | | | | |
| **R4** sizing conflict **[OPEN]** | gated at G0 | **written down** | | **one candidate fix** | **measured (gate h)** |
| **R5** nested-nested Docker on ZFS **[UNTESTED]** | | | | | **exercised (gate g, non-gating)** |
| **R6** HA on a 3-node rule **[OPEN]** | | **operator call** | | | |
| **R7** the ADR-010 citation | corrected | | corrected | | corrected |
| **R8** scope creep | | | | most tempting here | **contained at FE4-S05** |

---

## 7. FR coverage audit

Every FR in `prd.md` §5 maps to at least one story. No orphans in either direction.

| FR | Story | FR | Story |
|---|---|---|---|
| FR-PRE-001 | FE0-S01 | FR-CTL-004 | FE2-S04 |
| FR-PRE-002 | FE0-S02 | FR-CTL-005 | FE2-S05 |
| FR-PRE-003 | FE0-S01 | FR-CTL-006 | FE2-S06 |
| FR-PRE-004 | FE0-S03 | FR-CTL-007 | FE2-S04 |
| FR-PRE-005 | FE0-S04 | FR-WS-001 | FE3-S01 |
| FR-PRE-006 | FE0-S05 | FR-WS-002 | FE3-S01 |
| FR-SUB-001 | FE1-S01 | FR-WS-003 | FE3-S02 |
| FR-SUB-002 | FE1-S01 | FR-WS-004 | FE3-S02 |
| FR-SUB-003 | FE1-S01 | FR-WS-005 | FE3-S03 |
| FR-SUB-004 | FE1-S02 | FR-WS-006 | FE3-S04 |
| FR-SUB-005 | FE1-S03 | FR-WS-007 | FE3-S05 |
| FR-SUB-006 | FE1-S04 | FR-WS-008 | FE3-S06 |
| FR-SUB-007 | FE1-S05 | FR-WS-009 | FE3-S01 |
| FR-CTL-001 | FE2-S01 | FR-KIT-001 | FE4-S01 |
| FR-CTL-002 | FE2-S02 | FR-KIT-002 | FE4-S02 |
| FR-CTL-003 | FE2-S03 | FR-KIT-003 | FE4-S02 |
| | | FR-KIT-004 | FE4-S03 |
| | | FR-KIT-005 | FE4-S04 |
| | | FR-KIT-006 | FE4-S05 |

**28 / 28 FRs covered across 27 stories** (FE0 ×5, FE1 ×5, FE2 ×6, FE3 ×6, FE4 ×5), matching §4.2
of the proposal exactly. No FR is uncovered and no story is orphaned. Four stories carry two FRs
each (FE0-S01, FE2-S04, FE3-S02, FE4-S02); FE1-S01 and FE3-S01 carry three each.

**NFR binding.** NFR-SEC-001 → FE2-S05 + gate (a); NFR-SEC-002 → FE1-S05 + ADR-002;
NFR-SEC-003 → FE0-S01, FE0-S02, FE2-S05; NFR-IAC-001 → FE1-S03; NFR-IAC-002 → FE1-S02 + gate (j);
NFR-DISP-001 → the FE4 rollback path; NFR-CAP-001 → gate (h); **NFR-CAP-002 → G0, open**;
NFR-OBS-001 → FE1-S01; NFR-PORT-001 → FE3-S01; NFR-PORT-002 → FE2-S03 + gate (f).

---

## 8. Open questions carried into execution

These are open **on purpose**. See `prd.md` §11 for the full statement of each.

1. **The sizing decision (R4).** `coder_parameter` defaults of 12288 MB RAM / 20480 MB swap against
   a 4C/8GB CT whose `swap_mb` defaults to 512 MB. Two candidate resolutions — four real
   `variable`s plus `swap_mb = 8192`, or resize the CT to 4C/12GB — **neither chosen**. An operator
   capacity call against pve3. **Blocks FE1-S01. Approval did not settle it.**
2. **Double-nested Docker on a ZFS-backed LXC rootfs (R5).** One nesting level is proven; two is
   **not tested in this estate**. Mitigated, not removed, by ADR-003.
3. **`intellij_gateway` (FE3-S05).** Keep and pay registry.coder.com egress per build, or remove.
   `terraform validate` fails while undecided.
4. **`ct:167` HA state (R6, FE1-S03).** `started` or `stopped` under the Project-CT HA Policy.
   Replication to both peers is **not** open — it is required.
5. **The fate of `ct_sparkle_vlabel` (FE0-S05).** Stashing is required; deletion versus retention
   is an operator decision.

---

## 9. References

- `../../sprint-change-proposal-2026-09-09.md` §4.2 (this decomposition), §5.3 (the gates), §5.4
  (the blockers), Risks R1–R8.
- [prd.md](prd.md) — FR/NFR definitions and §11 open decisions.
- [architecture.md](architecture.md) — topology, the secrets seam, the substitution table.
- [sprint-plan.md](sprint-plan.md) — session-by-session plan and the consolidated decision gates.
- [tests/acceptance.md](tests/acceptance.md) — gates a–k in full.
- [tests/e2e-deployment.md](tests/e2e-deployment.md) — the end-to-end runbook and rollback.
- `implementation-artifacts/sprint-status-forge-platform.yaml` — the tracking file; story keys there
  are the lowercase slugs of the IDs above.
- `homelab-playbook/wiki/runbooks/create-project-container.md` — the FE1 implementation vehicle.
