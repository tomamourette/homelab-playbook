---
type: architecture
product: forge-platform
version: 1.0.0
status: draft
date: 2026-09-09
prd_ref: prd.md
brief_ref: product-brief.md
---

# Forge Platform — Architecture

## 1. Executive Architecture Summary

This document describes the target topology for a single Proxmox LXC — **CT 167, `ct-forge-01`, pve3, 4C/8GB/50GB, Debian 13, `features=nesting=1,keyctl=1`, 192.168.50.167** — that hosts a self-hosted Coder control plane, a local Postgres 16 database, Caddy as a TLS-terminating reverse proxy, and a de-Azured Forge workspace template. It exists to answer one question with running infrastructure rather than opinion: **does Forge port off Azure at all?** It is not the architecture of a productised, multi-tenant Forge — that is a future, separate artifact set gated by FE4-S05.

The design principle throughout is **substitution, not redesign**. Every Azure dependency in the PoC path — Entra OIDC, Key Vault via IMDS, Azure Container Registry, Postgres Flexible Server, Caddy `on_demand_tls` — has a boring, already-idiomatic self-hosted replacement (§8), and none of the substitutions require forking `coder/templates/forge/main.tf` (§7). The seam that makes this cheap, `/opt/coder/secrets/*` → `/run/secrets/*` → `~/.config/forge/*.env` (§6), already implements an empty-file-means-disabled contract that every downstream consumer honours; the architecture's job is to feed that seam six empty files instead of Azure-sourced secrets, not to touch the consumers.

Two structural decisions carry the most weight. First, **CT 167 is an unprivileged LXC, not a VM** (ADR-001) — E2's in-session measurement showed a `privileged = true` container's blast radius ends at the LXC's own user namespace, and the workspace user already holds equivalent root *inside the container* via passwordless sudo, which the template depends on. Second, **HA follows the established project-CT pattern exactly** — replication to both peers, `standard` rule membership, via the `pve-ha-replication` / `pve-ha-rules` Ansible roles only — because the prior document's "no HA" recommendation was VM-specific reasoning (a 16 GB VM didn't fit on pve2) that does not carry over to an 8 GB LXC.

Two things are deliberately left unresolved by this document and must not be read as settled: the **workspace sizing conflict** (`coder_parameter` defaults of 12288 MB RAM / 20480 MB swap against an 8 GB CT — §11 AR1, blocks FE1-S01) and **double-nested Docker on a ZFS-backed LXC rootfs** (§11 AR2, R5 — untested, non-gating). Both are carried forward as open items, not quietly resolved in the writing of this architecture.

## 2. System Context (C4 Level 1)

```
                    +----------------------+
                    |      Operator        |
                    |    (tomamourette)     |
                    |  tailnet client, NOT  |
                    |     on the LAN        |
                    +-----------+----------+
                                |
                                | HTTPS (browser-trusted cert, DNS-01)
                                | over Tailscale tailnet
                                v
        +-------------------------------------------------------+
        |                    pve3 cluster node                   |
        |                                                         |
        |   +-------------------------------------------------+  |
        |   |     CT 167  ct-forge-01  (unprivileged LXC)      |  |
        |   |     Debian 13, nesting=1, keyctl=1               |  |
        |   |     192.168.50.167                               |  |
        |   |                                                  |  |
        |   |   coderd + Postgres 16 + Caddy + outer dockerd   |  |
        |   |   (see §3 for internals)                         |  |
        |   +-------------------------------------------------+  |
        |                                                         |
        |   Replicated (pve-ha-replication role):                 |
        |     167-0  pve3 -> pve1   (*/15)                        |
        |     167-1  pve3 -> pve2   (*/15)                        |
        +----------------------+----------------------------------+
                                |
                                | outbound only (DNS-01 API calls,
                                | GitHub OAuth token exchange)
                                v
        +----------------+          +------------------------+
        | Cloudflare DNS |          |   GitHub OAuth App     |
        |   API (zone    |          |  (external-auth token  |
        |  bi-services.be)|          |   for agentic-ai sync) |
        +----------------+          +------------------------+

  No inbound :80/:443 anywhere in this diagram. Every external call
  CT 167 makes is outbound-initiated (DNS-01 challenge, OAuth token
  exchange). This is what makes the design compatible with the
  homelab's Tailscale-first, no-public-ingress posture (§5.2).
```

**Actors and systems:** the operator, reaching CT 167 exclusively over the Tailscale tailnet from a client that is deliberately *not* on the LAN (so gates a–k measure the real remote-developer experience, not a LAN shortcut); the pve3 cluster node hosting CT 167 and replicating it to both peers; Cloudflare's DNS API, called outbound-only for DNS-01 certificate issuance; and the GitHub OAuth App, the PoC's one non-optional external credential. There is no inbound listener anywhere in this system — DNS-01 and OAuth token exchange are both outbound-initiated from inside CT 167.

## 3. Container Diagram (C4 Level 2)

```
  CT 167  ct-forge-01  (unprivileged LXC, Debian 13, 4C/8GB/50GB)
 +--------------------------------------------------------------------+
 |                                                                     |
 |   +-------------+      +----------------+      +----------------+  |
 |   |   Caddy      |----->|    coderd      |----->|  Postgres 16   |  |
 |   | static site  |      |  (pinned .deb, |      |  local role +  |  |
 |   | block, DNS-01|      |   checksum-    |      |  database, no  |  |
 |   | via caddy-dns|      |   verified)    |      |  extensions    |  |
 |   | /cloudflare  |      |                |      |                |  |
 |   +------+------+      +--------+-------+      +----------------+  |
 |          |                      |                                  |
 |    forge.bi-services.be   provisions workspace                     |
 |    (browser-trusted)      containers via outer dockerd             |
 |                                     |                               |
 |                                     v                               |
 |   +-------------------------------------------------------------+ |
 |   |                  outer dockerd (LXC-hosted)                  | |
 |   |    data root on the LXC's ZFS rootfs                         | |
 |   |    daemon.json: {"features":{"time-namespaces":false}}       | |
 |   |    version-pinned package (below the 29.5.0 behaviour flip)  | |
 |   |                                                               | |
 |   |   +-------------------------------------------------------+ | |
 |   |   |     workspace container (docker_image, keep_locally)   | | |
 |   |   |     privileged = true (ADR-002)                        | | |
 |   |   |                                                          | |
 |   |   |   +--------------------------------------------------+ | | |
 |   |   |   |   inner dockerd (double-nested — R5, untested)    | | | |
 |   |   |   |   writes to docker_volume.dockerd                  | | | |
 |   |   |   |   (housekeeping only — gate (g), non-gating)       | | | |
 |   |   |   +--------------------------------------------------+ | | |
 |   |   |                                                          | | |
 |   |   |   code-server (subdomain=false, path-proxied)           | | |
 |   |   |   ~/.forge-toolchain, ~/.claude/skills (agentic-ai)      | | |
 |   |   |   /opt/coder/secrets/* -> ~/.config/forge/*.env (§6)     | | |
 |   |   +----------------------------------------------------------+ |
 |   +-------------------------------------------------------------+ |
 |                                                                     |
 +--------------------------------------------------------------------+
```

Four layers of Docker-adjacent nesting exist in this box, and it is worth naming them precisely because §11 AR2's risk depends on which layer fails: (1) the LXC itself is unprivileged, held inside a Proxmox user namespace; (2) the outer dockerd runs inside the LXC, on the LXC's ZFS rootfs; (3) the workspace container it launches is `privileged = true`, but that privilege is still contained by the LXC's own user namespace (E2); (4) the workspace's inner dockerd, if it starts, writes to a Docker volume that lives on the outer dockerd's data root — i.e., two levels of Docker-on-Docker on top of one level of ZFS. Level 1→2 (Docker on ZFS inside an LXC) is proven — every project CT runs it via `dev-host`. Levels 3 and 4 stacked together are not (R5).

## 4. Component views

Each of §4.1–4.4 below corresponds to one epic. For traceability, the story-to-FR mapping in full:

| Epic | Stories | FR IDs | Covered in |
|---|---|---|---|
| FE1 (Substrate) | FE1-S01…S05 | FR-SUB-001…007 | §4.4 |
| FE2 (Control plane) | FE2-S01…S06 | FR-CTL-001…007 | §4.1, §6 |
| FE3 (Workspace) | FE3-S01…S06 | FR-WS-001…009 | §4.3, §7 |
| FE4 (Toolkit + acceptance) | FE4-S01…S05 | FR-KIT-001…006 | §4.5, product-brief §6 |

FE0 (Prerequisites and truth) has no component of its own — its five stories (FE0-S01…S05, FR-PRE-001…006) are preconditions that gate every component below rather than a layer in the topology, which is why they appear throughout §4.1–4.4 as blocking notes rather than as a §4.0.

### 4.1 Control plane

- **coderd** is installed by a new `forge-coder-host` Ansible role from a **checksum-verified, pinned `.deb`** — not a curl-pipe-shell install, not `:latest` (FE2-S01, FR-CTL-001).
- **Postgres 16** runs locally with a dedicated role and database, password auth, and deliberately **no extensions** — `pgvector` is an OpenMemory-only requirement, and OpenMemory is out of scope (FE2-S02, FR-CTL-002).
- **`/etc/coder.d/coder.env`** drops the OIDC block and the Azure DevOps external-auth block entirely; `CODER_DISABLE_PASSWORD_AUTH=false` turns password auth on as the sole sign-in path for a single operator (FE2-S04, FR-CTL-004).
- **`CODER_EXTERNAL_AUTH_0_*`** is configured from the operator-supplied GitHub OAuth App (FE2-S07/FR-CTL-007) — this is the control plane's one live external dependency, and it is intentionally left non-optional in the template surface even though `optional = true` is recommended alongside it (FR-PRE-003) so a missing grant degrades to a visible skip.
- **Caddy** serves `forge.bi-services.be` from a **static** site block, certificate via DNS-01 through `caddy-dns/cloudflare`, with the Cloudflare token supplied as a 0600 root-owned systemd `EnvironmentFile` (FE2-S05, FR-CTL-005). No `on_demand_tls`, no ask-server on `:9111` — see §8 and §9.
- **`/etc/docker/daemon.json`** on the outer dockerd carries `{"features":{"time-namespaces":false}}`, paired with a Docker version pin, closing the scheduled Docker 29.5.0 time-namespace trap before it can bite (FE2-S06, FR-CTL-006, R2, ADR-004).

### 4.2 The secrets seam

See §6 for the full contract. The component-level point: the control plane's only job with respect to secrets is to populate `/opt/coder/secrets/*` correctly — six files, 0600, inside a 0700 directory — and then get out of the way. Every downstream consumer (the workspace template's `sudo cat /run/secrets/*` calls, the empty-file-means-disabled branches) is unmodified by this PoC. The mnemosyne pair is explicitly **not** created (FE2-S03, FR-CTL-003) — there is no mnemosyne-consuming integration in PoC scope.

### 4.3 Workspace template

- **`local.image`** switches from an ACR pull to a local `docker build` with `docker_image "main" { keep_locally = true }` — no registry needed anywhere in the PoC (FE3-S01, FR-WS-001, E5 row 3).
- **Four new Terraform `variable`s** are added — not `coder_parameter` edits — driving both the sizing defaults and their validation maxima for `workspace_cpu_shares`, `workspace_memory_mb`, `workspace_memory_swap_mb`, `workspace_memory_reservation_mb` (FE3-S01, FR-WS-002). This is gated by the still-open R4/AR1 sizing decision (§11) — the variables can be added, but what value they carry is not decided by this architecture.
- **The two Saply-specific heredocs** at `main.tf:171-270` are replaced with generic equivalents; `company-overlay` is added to `local.repo_deny` so it stops being cloned twice (FE3-S02, FR-WS-003/004).
- **`forge-sync.sh`** is parameterised (org, repo list, ADO block) while preserving its per-repo flags and distinct failure messages (FE3-S03, FR-WS-005).
- **`forge-onboard.sh`** has every Azure block gated, including the `:103` `az account show` call, which today prompts for a login of a binary that will not exist on this substrate (FE3-S04, FR-WS-006).
- **`intellij_gateway`** is an explicitly undecided module (FE3-S05, FR-WS-007, §11 AR3) — keeping it means every workspace build needs `registry.coder.com` egress; removing it means none does. `terraform validate` in that directory fails while this is left undecided, which is a deliberate forcing function, not a bug to route around.
- **`FORGE_AGENTIC_AI_REF`** in `coder_agent.main.env` is pinned to a tag (FE0-S03, FR-PRE-004) so a merge to `agentic-ai` `main` cannot change the PoC's toolkit mid-flight.

### 4.4 Substrate, HA, DNS, and monitoring auto-derivation

- **Substrate:** `module "ct_forge_01"` in `homelab-infra/terraform/envs/homelab/main.tf`, built from `../../modules/ct-debian`, mirroring `ct_saply_ai` exactly — Debian 13, unprivileged, `features=nesting=1,keyctl=1`, 192.168.50.167 (FE1-S01, FR-SUB-001). `swap_mb` is set **explicitly** in this module block rather than inheriting the module's `swap_mb = 512` default (FR-SUB-002) — the value chosen depends on the still-open R4 decision.
- **DNS and monitoring are auto-derived, not hand-edited:** registering CT 167 in `outputs.tf` `locals.all_containers` feeds Prometheus `file_sd_configs` automatically, and registering it in `locals.project_container_host_map` generates both the Cloudflare A record and the Pi-hole `custom.list` entry (FE1-S01, FR-SUB-003). A wildcard must never enter `fqdn_dns_records` — that map renders hosts-format lines and dnsmasq rejects `*` entries; wildcards belong in the Cloudflare map only. ~~and the PoC does not need one (`coder_app "code_server"` is `subdomain = false`)~~ — **amended 2026-09-09: the PoC DOES need one.** `code_server` is `subdomain = false`, but Coder's preview URLs are subdomain-based and `CODER_WILDCARD_ACCESS_URL=*.forge.bi-services.be` is live on CT 167. The `fqdn_dns_records` rule itself is unchanged and still holds: the wildcard is served publicly from the Cloudflare map and internally from an additive Pi-hole dnsmasq `address=` drop-in, never from `fqdn_dns_records`. See [ADR-005](adrs/ADR-005-dns-01-wildcard-over-public-ingress.md).
- **Plan discipline:** `terraform plan` against the homelab root is narrowly `-target`ed at `module.ct_forge_01` and its generated/DNS resources — a bare plan drags in pre-existing DNS drift unrelated to this container (FE1-S02, FR-SUB-004, NFR-IAC-002).
- **HA:** two replication jobs, `167-0` (pve3→pve1) and `167-1` (pve3→pve2), at `*/15`, plus `ct:167` membership in the `standard` node-affinity rule — created via the `pve-ha-replication` and `pve-ha-rules` Ansible roles **only** (FE1-S03, FR-SUB-005, NFR-IAC-001). Replicating to only one peer is the ct:151 failure mode: data is safe, but failover lands in `error`.
- **`dev-host`:** an inventory entry plus `host_vars/ct-forge-01/main.yml` containing `project_name` must exist before `dev-host-setup.yml` runs, or the playbook aborts mid-run after creating the `developer` user but before seeding SSH keys (FE1-S04, FR-SUB-006). `dev-host` already installs Docker CE, Node 20 LTS, the Claude Code CLI wrapper, ruflo, and pyenv/Python 3.11.11 — most of the Forge host toolchain arrives for free.
- **Re-verification, not assumption:** the E2 privilege measurement (root-in-container, blast radius bounded by the LXC user namespace) is re-run on CT 167 itself — Debian 13, `keyctl=1` — rather than assumed to transfer unchanged from the CT 250 measurement (FE1-S05, FR-SUB-007). **[I]** marks the untested transfer assumption until this story runs.

### 4.5 Data flow: first workspace create (FE4-S01)

This is the sequence the eleven acceptance gates actually exercise, laid out once so each gate in §5.3 of the product brief can be read against a concrete flow rather than in isolation:

```
 1. Operator (tailnet client, NOT on LAN)
      -> HTTPS forge.bi-services.be                         [gate a: cert must be browser-trusted]
 2. Caddy terminates TLS (DNS-01 cert, static site block)
      -> proxies to coderd
 3. Operator authenticates (Coder password auth)
      -> creates workspace, accepting or overriding the
         four coder_parameter sizing knobs                  [gate h depends on what's chosen here — AR1]
 4. coderd -> outer dockerd: docker build (local image,
      keep_locally = true) -> docker run (privileged = true)
      -> wall-clock start of gate (i)'s timer
 5. Inside the workspace container, agent startup script runs:
      a. sudo cat /run/secrets/* (sudo -n true)              [gate f: empty-file contract]
      b. coder external-auth access-token github
           -> forge-sync.sh clones agentic-ai + repos        [gate b: company-overlay absent]
      c. forge-onboard.sh runs with Azure blocks gated        [az account show never fires]
      d. inner dockerd attempt (soft failure by construction) [gate g: non-gating]
      e. ~/.forge-toolchain populated, ~/.claude/skills seeded [gates c, d]
 6. code-server becomes reachable (subdomain = false, path-proxied)
      -> wall-clock end of gate (i)'s timer
 7. Operator runs `claude`, answers one prompt under
      subscription OAuth                                     [gate e: the actual product value]
 8. Operator checks pve3 `free -g` and `ha-manager status` /
      `/etc/pve/replication.cfg`                              [gates h, k]
```

Nothing in this flow requires an inbound connection at any step — step 1 arrives over the tailnet, step 5b/5c are outbound token exchanges, and the rest is local to CT 167.

## 5. Cross-cutting concerns

### 5.1 Security posture and the privileged-workspace blast radius

`privileged = true` is accepted for the Forge workspace container (ADR-002), and the reasoning is bounded, not casual. E2's in-session measurement on CT 250 (Debian 12, kernel 6.17.2-1-pve, Docker 29.3.1, cgroup v2) found: the privileged container gets full `CapEff`, but held inside the **LXC's own user namespace** — host uid 0 is unmapped, so "root" in the container is an unprivileged host uid; no host block devices are visible; `modprobe` fails. The realistic blast radius is **root inside the LXC** — a privilege the workspace user already holds via the passwordless sudo the template itself depends on (`main.tf:341,353,378` all read `/run/secrets/*` via `sudo cat`, and `sudo -n true` is acceptance gate (f)). For a single operator, `privileged = true` therefore adds close to zero incremental security delta.

This reasoning has an expiry condition, and it is written down rather than left implicit: **the moment a second, less-trusted developer needs a workspace on this host, the equivalence above stops holding** (NFR-SEC-002). That is the documented revisit trigger for ADR-002, and it is the same trigger that gates FE4-S05's productisation decision — not a target this architecture is designed toward.

### 5.2 Ingress posture

**No new public inbound ingress is added by this design.** DNS-01 issues certificates over an outbound API call to Cloudflare; there is no listener on :80 or :443 anywhere in this estate for Forge to bind to, so HTTP-01 was never an option. This is consistent with the homelab's standing network policy, documented at `homelab-playbook/wiki/architecture/tailscale-policy.md:20-31` — *"Public DNS / port-forward and SSH-key distribution both stay fallback-or-disabled unless Tailscale is genuinely insufficient"* — and `homelab-playbook/wiki/architecture/remote-access-topology.md`, which catalogues the estate's four legitimate off-LAN access mechanisms and where DNS-01-only services fit among them. **There is no "ADR-010 no-public-ingress" policy in this estate** — the only ADR-010 that exists is `products/context-stack/adrs/ADR-010-decommission-as-single-pr.md`, an unrelated document — and this architecture cites the two wiki pages above instead (R7, HARD RULE 1).

For orientation, the estate's four existing off-LAN access mechanisms and where Forge sits among them:

| Mechanism | Solves | Forge's relationship to it |
|---|---|---|
| Cloudflare Tunnel + Traefik | A third party or browser with no Tailscale reaching a specific public service | Not used — Forge has no third-party audience in this phase |
| Tailscale subnet router | The operator's own devices needing the whole LAN | This is how the operator's tailnet client reaches CT 167 in every gate |
| VS Code tunnels | Browser-only dev access to a specific container, no desktop VS Code | Not used — code-server itself is Forge's browser-based dev surface |
| Proxmox console / `pct enter` | Break-glass, always works | Available as the operator's fallback if Coder/Caddy misbehave during FE1–FE4 |

Forge adds a fifth pattern to this list only in the narrow sense that it terminates its own TLS via DNS-01 rather than riding an existing Cloudflare Tunnel — but the *posture* (outbound-only, Tailscale-reached) is identical to the other three self-service mechanisms, not a departure from them.

### 5.3 Secrets handling

Two secrets exist in this PoC, and both are handled the same way: 0600, root-owned, never committed. The **GitHub OAuth App's** `CODER_EXTERNAL_AUTH_0_CLIENT_SECRET` lives in `coder.env`. The **Cloudflare DNS-edit token** is supplied to Caddy as a systemd `EnvironmentFile` (NFR-SEC-003). Everything else the workspace needs follows the seam in §6 — six empty files, not six secrets.

### 5.4 Backup and recovery

CT 167 is backed up to **pve3-pbs** (FE4-S03, FR-KIT-004) — the standard PBS target for the pve3 project-CT fleet. Independently of the backup job, the container is **HA-replicated to both peers** (`167-0` pve3→pve1, `167-1` pve3→pve2, §4.4) — replication and backup are complementary, not redundant:

| Mechanism | Protects against | RPO | Owner |
|---|---|---|---|
| HA replication (`167-0`, `167-1`) | Node failure (pve3 goes down) | Near-zero (`*/15` schedule) | `pve-ha-replication` role |
| PBS backup (`pve3-pbs`) | Corruption, operator error, a bad `terraform apply` a live replica would faithfully copy | Per backup-job schedule | FE4-S03 |

The disposability principle (NFR-DISP-001) means recovery in the degenerate case is also just: destroy CT 167, re-run FE1–FE3 from the committed Terraform/Ansible/template state, and accept a re-run of FE4-S01. Nothing about this PoC's recovery path depends on the PBS restore succeeding on the first try — the whole substrate is reproducible from IaC, which is the point of building it this way rather than by hand.

### 5.5 Observability auto-derivation

No dashboard work is in PoC scope (NFR-OBS-001). Monitoring is a side effect of the same registration that produces DNS: CT 167's entry in `locals.all_containers` feeds the existing Prometheus `file_sd_configs` generation with zero Forge-specific configuration. Gate (h) — `free -g` on pve3 showing headroom with the workspace running, and CT 167 not swap-thrashing — is read directly off this auto-derived scrape target rather than a bespoke Forge dashboard.

## 6. The `/opt/coder/secrets` contract

This is the seam that makes the entire substitution table in §8 cheap, and it **must not be broken**.

```
   Ansible-populated                Read at workspace                Consumed by
   host-side files                  build time                       forge-sync.sh /
                                                                       forge-onboard.sh
  /opt/coder/secrets/               /run/secrets/                     ~/.config/forge/*.env
   (dir 0700, six                    (bind-mounted                     (written by main.tf's
    files 0600)                       into the workspace                heredoc logic,
                                       container)                       `: > file` on empty
        |                                  |                            input)
        |   sudo cat /run/secrets/*        |
        +---------------------------------->  main.tf:341,353,378
                                              (sudo -n true is load-
                                               bearing — gate (f))
```

Six empty 0600 files under `/opt/coder/secrets/` (FE2-S03, FR-CTL-003) is the entire Key-Vault-via-IMDS substitution (§8 row 1). The contract is **verified end to end**, not assumed: `main.tf:341-389` shows the exact empty-input branch — `: > "$HOME/.config/forge/openmemory.env"` on empty input, and the equivalent for `langfuse.env`. Gate (f) exercises this directly: both files land zero-byte in the workspace, the build log contains both "skipped" lines, and `sudo -n true` succeeds. **The mnemosyne pair is explicitly not created** (FE2-S03) — there is nothing in PoC scope that consumes it.

The reason this is a hard rule rather than a preference: every substitution in §8, and every deferral in §9, routes through this exact seam. Fork the seam — change what `/opt/coder/secrets/*` means, or short-circuit the `/run/secrets/*` bind-mount, or hand-edit `forge-sync.sh`'s empty-check logic — and every one of those independent decisions has to be re-verified together instead of independently.

## 7. Two-Terraform-roots principle

The Proxmox Terraform root (`homelab-infra/terraform/envs/homelab/`) is a **sibling** of the existing Azure Terraform root that provisions Saply AI's Forge deployment — not a relocation, not a merge, not a shared module tree. Each root owns its own state, its own provider block, and its own lifecycle. CT 167's `module "ct_forge_01"` block lives in the homelab root exactly like every other project CT (`ct_saply_ai`, `ct_quant_trading`, etc.); nothing in the Azure root is touched by this PoC, and nothing in the Proxmox root assumes the Azure root exists.

`coder/templates/forge/main.tf` — the Coder workspace template itself, as distinct from either infrastructure root — follows the same non-relocation principle at the template level: it is **not forked**. The prior document's own recommendation, adopted unchanged here, is edits on a branch, additive `variable`s only (§4.3), never a parallel copy of the file. A forked template immediately desyncs from every future upstream fix to the real Saply-facing template; an additive-variables branch can be rebased.

## 8. Azure → self-hosted substitution table

Reproduced from the sprint change proposal's E5 finding, verbatim in substance:

| Azure component | Self-hosted substitution | Evidence |
|---|---|---|
| Entra OIDC sign-in | Coder built-in password auth | `CODER_DISABLE_PASSWORD_AUTH=false` already permits it; drop the OIDC block from `coder.env` |
| Key Vault via IMDS → 8 host files | **Six empty files** under `/opt/coder/secrets/` (0600, dir 0700) | The template honours an explicit empty-file-means-disabled contract, verified at `coder/templates/forge/main.tf:341-389`: `: > "$HOME/.config/forge/openmemory.env"` on empty input, ditto langfuse and rollout |
| ACR image pull | Local `docker build` + `keep_locally = true` — **no registry needed** | `coder/templates/forge/main.tf:550` |
| Caddy `on_demand_tls` + an undocumented ask-server on `:9111` | A **static** Caddy site block | on-demand exists only because Azure serves arbitrary per-SNI names; a single fixed host does not need it |
| Postgres Flexible Server (Entra auth) | **Local Postgres 16**, password auth, no extensions | `pgvector` is an OpenMemory requirement only, and OpenMemory is out of scope |

Every row substitutes a managed-cloud-identity or managed-cloud-storage concept with a boring, already-present homelab equivalent. None of the five rows required a new service to be introduced to the estate — Coder's own auth, empty files, a local build, a static Caddy block, and a Postgres role are all things the homelab already knows how to run.

Two properties of this table are worth calling out explicitly, because they are the reason the PoC is scoped in weeks rather than months. First, **every substitution is a subtraction, not an addition** — nothing on the right-hand side is a new dependency the estate has to learn; Coder password auth, Postgres 16, Caddy, and a local `docker build` are all already-operated patterns. Second, **the five rows are independent of each other** — dropping OIDC does not require dropping Key Vault first, and the Postgres substitution does not depend on the Caddy substitution landing. This independence is what let FE2's stories (S01–S06) be sequenced without a strict dependency chain beyond "the CT exists."

## 9. What is deliberately absent and why

| Absent | Why |
|---|---|
| **Hermes** | Carries session pools + blob leases, the deepest Azure coupling in the estate; not needed to answer "does it port?" (out of PoC scope per §4.2 of the brief) |
| **OpenMemory** | Needs a 5-file provider/auth/dimension refactor and `pgvector`; cannot boot off Azure at all today |
| **Langfuse** | Pinned version unresolved; v3 drags in ClickHouse + Redis + MinIO onto an 8 GB host |
| **`pgvector`** | An OpenMemory-only extension; the PoC's Postgres 16 role is deliberately extension-free (FR-CTL-002) |
| **ACR (Azure Container Registry)** | `docker_image "main" { keep_locally = true }` means no registry is needed for any image in this PoC |
| **`on_demand_tls` + the `:9111` ask-server** | Exists only to serve certificates for arbitrary per-SNI Azure tenant subdomains; a single fixed hostname (`forge.bi-services.be`) needs a static Caddy block instead |
| **OIDC** | Entra-specific; Coder's built-in password auth is sufficient and simpler for one operator |
| **Sysbox** | Three independent blockers: nestybox/sysbox#1011 is open with no maintainer response; sysbox-in-LXC is unsupported per the maintainer (nestybox/sysbox#860); Debian 13 is absent from sysbox's distro-compatibility table. Not an option for CT 167 regardless of the Docker time-namespace flag. |
| **The VM path (`modules/vm-dev`)** | Never applied (`deploy_dev_vm = false`, zero `proxmox_vm_qemu` in state); legacy flat `disk {}` blocks for an old telmate version; `ci_password` required with no default; no qemu-guest-agent so no IP is ever returned; its base template lives on the wrong node (pve1) for a pve3 clone. The isolation premium a VM buys is priced for untrusted users, who do not exist in this phase (E4). |
| **CI wiring** | GitHub-hosted runners have no LAN route to Proxmox; this is a productisation-phase concern (NG5), not a porting question |

## 10. ADR index

| ADR | One-line summary |
|---|---|
| [ADR-001](adrs/ADR-001-lxc-over-vm-for-forge-poc.md) | Unprivileged LXC over a Proxmox VM for the PoC, on E2's blast-radius measurement and E4's assessment that `modules/vm-dev` is unusable as-is |
| [ADR-002](adrs/ADR-002-privileged-workspace-accepted-for-single-operator.md) | `privileged = true` accepted for the workspace container because, for a single operator, it adds close to zero incremental blast radius over the passwordless sudo the template already grants |
| [ADR-003](adrs/ADR-003-nested-docker-is-not-an-acceptance-gate.md) | Nested Docker inside the workspace has zero automated consumers in `agentic-ai`, fails soft by construction, and is therefore non-gating (gate (g)) |
| [ADR-004](adrs/ADR-004-sysbox-rejected-and-the-docker-29-5-0-trap.md) | Sysbox rejected on three independent grounds; the real sysbox-comment-drift cause is Docker 29.5.0's private-time-namespace default, fixed by a `daemon.json` flag plus a version pin |
| [ADR-005](adrs/ADR-005-dns-01-wildcard-over-public-ingress.md) | DNS-01 (outbound-only) chosen over any form of inbound HTTP-01 or public ingress, consistent with the tailscale-policy wiki page; the token is mandatory. ~~wildcard scope is optional~~ → **REVERSED 2026-09-09, wildcard required** (see the ADR's amendment) |
| [ADR-006](adrs/ADR-006-hermes-openmemory-langfuse-out-of-poc-scope.md) | Hermes, OpenMemory, and Langfuse deferred out of PoC scope, with the conditions under which each would re-enter a future phase |

## 11. Open architectural questions

| ID | Question | Status | Blocks |
|---|---|---|---|
| **AR1** | The sizing/swap conflict: `coder_parameter` defaults of 12288 MB RAM / 20480 MB swap against an 8 GB CT, with `swap_mb` defaulting to 512 MB inside an unprivileged LXC that cannot create its own swapfile. Two candidate resolutions — four real `variable`s plus `swap_mb = 8192`, or a 4C/12GB CT — neither chosen. | **UNRESOLVED — operator capacity call against pve3** | **FE1-S01** |
| AR2 | Double-nested Docker on a ZFS-backed LXC rootfs (§3, R5): one nesting level is proven across the project-CT fleet, two is not. | Untested | Non-gating (ADR-003); a failure degrades the PoC rather than ending it |
| AR3 | Whether to keep `intellij_gateway` (→ every workspace build needs `registry.coder.com` egress) or remove it (→ no such egress). | Undecided | `terraform validate` in `coder/templates/forge/` fails while undecided — **FE3-S05** |
| AR4 | Whether `ct:167`'s HA state should register `started` (matches an always-on host) or `stopped` (matches the Project-CT HA Policy default for a not-yet-running container) at rule-creation time. | Operator call | **FE1-S03** |
| AR5 | Which Docker version to pin the outer dockerd to — any version below the 29.5.0 time-namespace behaviour flip is a valid choice, but "which specific version" is not yet decided. | Undecided | FE2-S06 |

## 12. References

### 12.1 This product's planning artifacts

- [product-brief.md](product-brief.md) — vision, scope, and success criteria this architecture implements
- [../../sprint-change-proposal-2026-09-09.md](../../sprint-change-proposal-2026-09-09.md) — the approved spec; authoritative for E1–E7, R1–R8, and all FR/NFR IDs cited above
- `adrs/ADR-001` through `ADR-006` — see §10 for the full index

### 12.2 Prior art and homelab conventions

- `docs/forge-reuse-and-proxmox-findings.md` (2026-07-30, 352 lines, untracked) — prior art; reconciled per §3.4 of the sprint change proposal, not superseded
- `homelab-playbook/wiki/architecture/tailscale-policy.md:20-31` — the real no-public-ingress-by-default policy
- `homelab-playbook/wiki/architecture/remote-access-topology.md` — how DNS-01 fits the estate's remote-access mechanisms
- `homelab-playbook/wiki/runbooks/create-project-container.md` — the established project-CT pattern CT 167 follows
- `homelab-infra/terraform/modules/ct-debian` — the Terraform module `ct_forge_01` is built from, mirroring `ct_saply_ai`
- `homelab-infra/ansible/roles/pve-ha-replication/`, `pve-ha-rules/` — the only sanctioned path to HA configuration (NFR-IAC-001)

### 12.3 Source repositories (this pass's HEADs)

- `repos/forge-platform/coder/templates/forge/main.tf` @ `2b27a95` — the workspace template this architecture substitutes into; source of every `main.tf:NNN` citation above
- `repos/forge-platform/docs/coder/setup.md`, `docs/coder/orchestration-adr.md` — the sysbox comment drift corrected by FE0-S04
- `repos/agentic-ai` @ `87ec24a` — the toolkit (211 `SKILL.md` files, +14 `.skill` archives) the workspace must reach; `company-overlay` contributes 0

### 12.4 Structural precedent

- `products/context-stack/architecture.md` — structural precedent for this document's section shape and diagram style
- `products/doc-system/architecture.md` — cross-checked for heading and table-density conventions

---

**End of architecture — handoff to epics and stories.**
