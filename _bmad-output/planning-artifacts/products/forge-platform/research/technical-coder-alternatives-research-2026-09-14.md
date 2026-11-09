---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments: []
workflowType: 'research'
lastStep: 6
research_type: 'technical'
research_topic: 'Alternatives to Coder for the Forge developer platform'
research_goals: 'Scored comparison of workspace/dev-environment platforms for Forge (self-hosted Proxmox LXC, Tailscale-only, IaC, agentic-ai toolkit per user) with a recommendation for (a) the homelab single-operator case and (b) the multi-company/team case'
user_name: 'tomamourette'
date: '2026-09-14'
web_research_enabled: true
source_verification: true
---

# Research Report: technical

**Date:** 2026-09-14
**Author:** tomamourette
**Research Type:** technical

---

## Research Overview

This report answers one question for the Forge developer platform: **is Coder the right foundation, and if not, what is?** It was produced 2026-09-14 → 2026-09-21 with the BMad technical-research workflow: five research steps, fourteen parallel research agents plus lead verification of every single-sourced or load-bearing claim at its primary source, ~120 cited sources, each fact carrying a confidence grade.

**Finding in one line:** of everything evaluated, only two things still offer a self-hosted, Kubernetes-free path on Proxmox in September 2026 — Coder, and the Dev Containers standard running on your own hosts with Tailscale as the access and identity layer. Everything else is dead (CodeCanvas), Kubernetes-only (Okteto, Che), cloud/SaaS-only (Gitpod/Ona — now being acquired by OpenAI —, E2B, Daytona, Modal, Vercel, Cloudflare), or effectively unmaintained (DevPod). Coder itself is in a live pivot toward a hosted, metered agent layer that Forge does not use.

**Recommendation:** make the workspace the product — a portable `devcontainer.json` + signed prebuilt image + Ansible roles + Claude Code managed policy + Terraform for Proxmox and Tailscale — and treat Coder as an optional per-customer profile (one instance per company) rather than the platform. For the homelab, steady state is without Coder; for customer teams that need self-service and brokered identity, add it. Weighted scores: homelab A 3.57 / B 4.19 / **C 4.29**; teams A 3.58 / B 3.92 / **C 4.25**. The full executive summary is in the *Research Synthesis* section below; step-by-step evidence is in the sections between.

---

<!-- Content will be appended sequentially through research workflow steps -->

## Technical Research Scope Confirmation

**Research Topic:** Alternatives to Coder for the Forge developer platform
**Research Goals:** Scored comparison of workspace/dev-environment platforms for Forge (self-hosted Proxmox LXC, Tailscale-only, IaC, agentic-ai toolkit per user) with a recommendation for (a) the homelab single-operator case and (b) the multi-company/team case

**Technical Research Scope:**

- Candidates — Coder v2.36 (incl. Coder Tasks / AI-agent features, OSS-vs-Premium boundary), Gitpod/Ona Flex self-hosted runners, DevPod (Loft), Eclipse Che, Daytona post-pivot, JetBrains CodeCanvas, Okteto, devcontainer CLI + VS Code Remote-SSH/Tunnels on per-user LXC/Incus (status quo scaled by Ansible), Nix/Devbox reproducibility, agent-execution sandboxes (E2B, Daytona, Modal, Claude Code sandboxing), plus anything found that fits better
- Architecture Analysis — control-plane components, Proxmox/LXC fit without Kubernetes, workspace isolation model, remote-access model and Tailscale composition
- Integration Patterns — per-user identity and GitHub/secret brokering, authenticated web-app exposure, IaC surface, later Hermes/OpenMemory/Langfuse hooks
- Implementation & Operations — install footprint, DB/upgrade burden, licensing/cost of the features Forge uses, maturity/maintenance trajectory (Sept 2026), migration cost from the current Coder template
- Synthesis — weighted scoring on the operator's criteria; two recommendations (homelab single-operator; multi-company/team) with consequences for the PoC and the FE4 verdict

**Boundaries:** no scoring on features neither case needs (e.g. Kubernetes autoscaling); the status-quo pattern is a real candidate.

**Research Methodology:**

- Current web data with rigorous source verification
- Multi-source validation for critical technical claims
- Confidence level framework for uncertain information
- Comprehensive technical coverage with architecture-specific insights

**Scope Confirmed:** 2026-09-14

## Technology Stack Analysis

_Step 2 — the candidate landscape as it stands on 2026-09-14. Facts were gathered by five parallel researchers (Coder; vendor CDEs; client-only/status-quo tooling; agent sandboxes and isolation runtimes; identity/Tailscale/cost cross-cuts) and spot-checked by the lead where a claim rested on one source. Confidence: **H**igh (primary source, dated), **M**edium (secondary or single primary), **L**ow (unverified this pass)._

### Method and source quality

- Primary sources preferred: vendor docs, changelogs, GitHub release pages, pricing pages fetched live; press only for corporate events; forums only for pain-point evidence.
- Two claims that arrived single-sourced were re-verified by the lead: the OpenAI–Ona acquisition (now H — [Forbes, 13 Jun 2026](https://www.forbes.com/sites/janakirammsv/2026/06/13/openai-buys-ona-to-run-codex-agents-inside-enterprise-clouds/), [TechTimes](https://www.techtimes.com/articles/318338/20260613/openai-acquires-ona-run-codex-agents-hours-without-your-computer.htm), [Dealroom](https://app.dealroom.co/news/note/openai-acquires-cloud-platform-ona-to-power-its-ai-agents); announced 11 Jun 2026, pending regulatory approval) and Ona's unsupported local/Linux runner (M-H — the [support article](https://support.gitpod.io/articles/3732428451-local-environment-support-and-desktop-applications) 404s on direct fetch but is quoted identically by two independent search indexes, and the only runner Terraform modules are [AWS](https://github.com/gitpod-io/terraform-aws-ona-runner) and [GCP](https://github.com/gitpod-io/terraform-google-ona-runner)).
- GitHub Team pricing fetched live by the lead from [github.com/pricing](https://github.com/pricing): $4/user/month; Codespaces included with separate compute from $0.18/hr (H).

### Category map

The "Coder alternative" space is not one category. Five distinct kinds of thing were in scope:

| # | Category | What it is | Members evaluated |
|---|---|---|---|
| 1 | **CDE control planes** | A server that owns workspace lifecycle, identity, brokered access | Coder (incumbent), Gitpod/Ona, JetBrains CodeCanvas, Okteto, Eclipse Che / OpenShift Dev Spaces |
| 2 | **Client-only environment tooling** | No server; the developer's machine drives a remote/local container | `devcontainer` CLI + VS Code Remote-SSH/Tunnels, DevPod, JetBrains dev-container support, `code serve-web` |
| 3 | **Status quo, scaled** | One LXC per project/user via Terraform + Ansible + Tailscale | Proxmox LXC (incl. PVE 9.1 OCI import), Incus, Nix/Devbox/Flox/devenv as reproducibility layer |
| 4 | **Agent execution sandboxes** | Ephemeral compute for AI-agent code execution, API-driven, not IDE-first | E2B, Daytona, Modal, Vercel Sandbox, Cloudflare Sandboxes, Northflank, Runloop, Blaxel, Morph; Anthropic sandbox-runtime / Claude Code `/sandbox`; Claude Managed Agents |
| 5 | **Isolation runtimes on our hardware** | How strongly a workspace/agent is contained | Docker namespaces (current), gVisor, Sysbox, Kata/Firecracker/libkrun microVMs |

The access/identity layer (Tailscale, GitHub tokens, secrets injection, auth proxies) cuts across all five and is treated in its own subsection.

### Candidate status board (September 2026)

| Candidate | Status | Hosting model | K8s required | Runs on a Proxmox LXC/Docker host | Licence / price signal | Trajectory | Conf. |
|---|---|---|---|---|---|---|---|
| **Coder** | v2.36.5 stable (10 Sep), v2.37.1 mainline (8 Sep); monthly cadence, ESR line | Self-hosted control plane (coderd + Postgres 13+ + provisioner) | No — Docker provider first-class | **Yes (current)** | AGPL core; Premium/AI Premium unpublished, sales-gated | $90M Series C (KKR, Apr 2026); product emphasis shifting to hosted "Coder Agents", AI Gateway, Agent Firewall | H |
| **Gitpod → Ona** | Rebranded Sep 2025; Classic sunset Oct 2025; **acquisition by OpenAI announced 11 Jun 2026** | SaaS control plane; runners in *your* AWS/GCP (Enterprise) | Cloud-runner stack, not K8s per se | **No** — local/Linux runner explicitly unsupported | Core from $20/mo pooled; Enterprise custom | Folding into OpenAI Codex | H (status) / M-H (runner) |
| **JetBrains CodeCanvas** | **Discontinued — stopped working 31 Mar 2026** | — | Yes (was) | No | — | JetBrains: CDE model "too niche and obsolete" in an agent-first market | H |
| **Okteto** | Live | Helm-only self-hosted | **Yes** (3-node minimum recommended) | No | Free 5 seats w/ licence key; beyond that quote-only | K8s dev-platform focus | M-H |
| **Eclipse Che / Dev Spaces** | Live, maintained (Dev Spaces 3.29, Jul 2026) | K8s/OpenShift operator | **Yes** — Docker mode removed years ago | No | EPL / OpenShift subscription | Adding agent-sandbox + MCP integrations | H |
| **DevPod (Loft/vCluster Labs)** | Not archived, but no default-branch commit since 14 Nov 2025, alpha tags only, "still maintained?" issue unanswered ~1 yr; community fork active | Client-only CLI; Pro = Helm chart | No (OSS) | Yes technically (SSH/Proxmox providers) | MPL-2.0; Pro pricing not public | Vendor pivoted to K8s tenancy (vCluster); **treat as unmaintained** | H |
| **Daytona** | OSS dev-env manager **dead** (repo banner: development private as of Jun 2026) | Managed sandbox API | n/a | No | Closed; $0.0504/vCPU-h | Agent-sandbox vendor | H |
| **devcontainer CLI + VS Code Remote-SSH / Tunnels** | CLI 0.89.0 (31 Aug 2026), GA Features ecosystem, prebuild guidance | None (client + container) | No | **Yes** | MIT / Microsoft EULA for VS Code | Standard is the lingua franca all CDEs consume | H |
| **JetBrains dev-container support** | Real, improving through 2026, lags VS Code | Client (Gateway) | No | Yes | Commercial IDEs | — | M |
| **Proxmox LXC + Ansible (status quo)** | PVE 9.1 adds **OCI-image LXC creation (tech preview)** | Hypervisor-native | No | **Yes (is the host)** | AGPL / optional subscription | Absorbing container use-cases natively | H |
| **Incus** | Healthy (Apache-2.0, Debian-packaged); Terraform `lxc/incus` 1.1.0 (May 2026) with OCI images | Alternative to Proxmox, **not** a co-resident | No | No — competing manager on the same node | Apache-2.0 | Healthy | M-H |
| **Nix: Devbox / Flox / devenv** | Active; Devbox Cloud hosted layer **sunset Aug 2026**; Flox Team $40/seat; devenv Cloud private beta | Reproducibility layer under a devcontainer | No | Yes | Apache-2.0 / GPLv2 / mixed | Team layers immature or pricey | M-H |
| **E2B** | Live | Firecracker + Nomad; self-host on **GCP (24 CPU, 2.5 TB SSD) or AWS bare-metal beta only** | No (Nomad) | **No** | Apache-2.0 infra; ~$0.166/h per 2 vCPU sandbox | Agent-sandbox leader | H |
| **Northflank** | Live | BYOC/BYOK on your own **Kubernetes** (≥1 node 12 vCPU/24 GB) | **Yes** | No | Commercial, SOC 2 | Best self-host story among sandbox vendors | M-H |
| **Modal / Vercel / Cloudflare Sandboxes / Runloop / Blaxel / Morph** | Live | Managed only (Runloop: BYOC into AWS/GCP/Azure) | n/a | No | Usage-priced | — | M |
| **Anthropic sandbox-runtime (`srt`) & Claude Code `/sandbox`** | Beta research preview, Apache-2.0 | OS-level (bubblewrap / seatbelt), **no container or VM needed** | No | **Yes** (already usable inside a Forge workspace) | Apache-2.0 | Anthropic's documented tiering: srt → Docker → gVisor → microVM | H |
| **Claude Managed Agents** | GA Apr 2026; "self-hosted sandboxes" beta May 2026 (Lambda, Cloudflare, Daytona, E2B, Fly, GKE, Modal, Vercel, "generic") | Anthropic control plane, your execution backend | n/a | Partly (backend), control plane never | Per-ms billing | Direct competitor to "workspace-resident agent" model | M |

### Coder in depth — the incumbent's own trajectory

- **Release line.** v2.36.4 (ours) is one patch behind stable v2.36.5 and supported; four-tier channel Mainline → Stable → Security → ESR, cut monthly. [releases](https://github.com/coder/coder/releases), [release policy](https://coder.com/docs/install/releases) (H).
- **v2.37.0 breaking changes (1 Sep 2026):** Chats API moved to `/api/v2`; OAuth rejects `openid` scope by default; dynamic client registration off by default; **Coder Tasks disabled** — the server refuses to start with `--hide-ai-tasks` set; `login_type=none` deprecated. (H, release notes.)
- **Tasks → Agents.** "Coder Agents" arrived ~v2.32 as the replacement for Tasks; Tasks deprecated in v2.34, removed in v2.37, surviving only on the ESR line. Migration doc: [tasks-to-chats-migration](https://coder.com/docs/ai-coder/agents/tasks-to-chats-migration). MCP-server and model configuration moved to organisation scope; native chat spend limits replaced by AI Gateway budgets (Premium). (M-H — consistent across three doc pages; explicit GA/beta label for "Agents" not found.)
  **Correction to the researcher's inference:** Forge does *not* use Coder Tasks. Claude Code runs as an ordinary process inside the workspace (`forge-onboard.sh`/`forge-sync.sh`), which v2.37 does not touch. The finding is a **direction-of-travel signal** — Coder is moving the agent layer into coderd and monetising it — not a breakage of the current template.
- **OSS vs Premium boundary** ([pricing](https://coder.com/pricing), H): Community = unlimited workspaces/templates, single org, OIDC SSO (one platform), **one external-auth integration**, **5 concurrent Coder Agents**, community support. Premium-only = external provisioners, workspace proxies, HA, multi-org RBAC/custom roles/groups, OIDC group sync, **audit logging**, quotas, **template permissions**, enforce-updates, disable-SSH, command logging, branding, quiet hours, notifications, SLA. AI Premium removes the agent cap and adds Agents API, MCP Server, AI Gateway, Agent Firewall. Prices unpublished. For Forge the two Community limits that bite first are the single external-auth integration (GitHub only) and — only if Coder Agents were adopted — the 5-agent cap.
- **Provisioning.** Docker on a single host is a first-class documented target ([creating templates](https://coder.com/docs/admin/templates/creating-templates), H). No official Proxmox/Incus/LXD provisioner; a community [proxmox-vm template](https://registry.coder.com/templates/umair/proxmox-vm) exists; a registry issue requesting an official one is open (M).
- **External auth.** Generic OAuth2 + first-class GitHub/GitLab/Bitbucket ([docs](https://coder.com/docs/admin/external-auth), H). Open issues: no API to retrieve refresh tokens (#12787), intermittent GitHub token-refresh failures (#17069), docs clarity (#13208, #15968) (M). Community report that headless agents inside workspaces do not receive the external-auth token automatically — explicit env plumbing needed (M, single issue). Postgres 13+ required; docs recommend an externally managed Postgres with daily backups ([architecture](https://coder.com/docs/admin/infrastructure/architecture.md), H).
- **Health.** 100k+ stars across Coder repos (Jun 2025); Series C $90M led by KKR, early Apr 2026, ~$175M raised, ~300% YoY bookings growth reported; no layoffs/pivot-away found (M-H, press). Small-self-hoster sentiment is **under-verified** — only issue-tracker evidence found.

### Eliminated on hard facts

Not by preference: **CodeCanvas** no longer exists; **Okteto** and **Che/Dev Spaces** are Kubernetes-only with no non-K8s mode; **Gitpod/Ona** has no self-hostable path below Enterprise, keeps a SaaS control plane, and is being absorbed into OpenAI's Codex — a poor bet for a Claude-Code-centred platform; **Daytona**'s open dev-environment product is dead and its sandbox product is closed and managed; **E2B** self-hosts only on GCP or AWS bare metal; **Northflank** needs your own Kubernetes; the remaining sandbox vendors are managed-only.

### Client-only and status-quo building blocks (all viable on our hardware)

- **Dev Containers** is now the substrate every surviving product consumes (Coder, Ona, DevPod, Codespaces, JetBrains all read `devcontainer.json`). The CLI is current (0.89.0), Features are GA, and prebuilt images remove any control-plane dependency ([prebuild guide](https://containers.dev/guide/prebuild), H).
- **VS Code Remote-SSH** is fully viable without Tunnels; Tunnels need a GitHub/Microsoft account per device and can simply be left unused when SSH-over-Tailscale exists ([tunnels docs](https://code.visualstudio.com/docs/remote/tunnels), H). `code serve-web` is Microsoft's own browser VS Code server ([docs](https://code.visualstudio.com/docs/remote/vscode-server), H). No multi-user story in any of this — that is exactly the layer a control plane provides.
- **DevPod** fits architecturally (client-only, SSH/Proxmox providers, devcontainer-native, MPL-2.0) but is effectively unmaintained by its vendor; adopting it means adopting the community fork (H).
- **Proxmox 9.1 OCI → LXC** (tech preview) lets Proxmox create containers directly from OCI images — the hypervisor itself is absorbing part of the Docker-in-LXC use case ([4sysops](https://4sysops.com/archives/proxmox-ve-91-create-lxc-containers-from-oci-images-granular-nested-virt-cpu-control-and-more/), H). **Incus** is healthy but is a competing manager, not a co-resident on a Proxmox node (M-H).
- **Nix layer** (Devbox/Flox/devenv) composes under a devcontainer via `postCreateCommand` and does not conflict with Claude Code hooks/skills; none has a mature self-hostable team layer today (Devbox Cloud sunset Aug 2026, devenv Cloud private beta, Flox Team $40/seat) (M-H).

### Access, identity and secrets layer

- **Tailscale Services — GA Feb 2026** ([blog](https://tailscale.com/blog/services-ga), H): a MagicDNS name + virtual IP per logical service, independent of device, on all plans; since Mar 2026 clients accept Service VIPs regardless of `--accept-routes`. This is the 2026-native way to give each workspace/project a stable hostname without subnet routes — directly relevant to the incident that preceded this research.
- **Tailscale SSH** replaces key management with identity + ACLs; `check` mode (re-auth) is unavailable for tagged devices and automation ([docs](https://tailscale.com/docs/features/tailscale-ssh), H). **ACL tags + groups** scale per-user access to per-project machines ([ACL syntax](https://tailscale.com/kb/1337/acl-syntax), H). **tsnet / WhoIs** gives identity-aware app auth without a separate IdP; `tsidp` builds an OIDC IdP on it ([tsnet](https://tailscale.com/docs/features/tsnet), H). Funnel is the only Tailscale feature that would break the Tailscale-only policy.
- **Tailscale pricing (live, Sep 2026):** Personal free (≤6 users, SSH ≤5 hosts, 3 ACL groups) · Standard $8/user/mo (SCIM, device posture, 10 groups, config audit) · Premium $18/user/mo · Enterprise custom. Aggregator pages still quoting "Personal Plus/Starter" are stale (H). Multiple tailnets under one IdP is **alpha** (M) — do not design on it. **Headscale** 0.23+ is production-usable but lacks SAML, posture, GUI-native RBAC and audit (H).
- **Git identity:** GitHub App installation tokens (new stateless `ghs_<APPID>_<JWT>` format rolling out from 27 Apr 2026) are the short-lived, non-personal best practice; OAuth-App user tokens (Coder external auth today) act as the user; Codespaces' repo-scoped `GITHUB_TOKEN` is the cleanest default but GitHub-tied (H/M).
- **Secrets injection without Kubernetes:** Infisical (self-hosted, Docker sidecar/CLI agent, no plaintext at rest) is the small-team consensus over Vault's K8s-centric agent; 1Password for SaaS-first teams (M-H).
- **Auth proxies:** oauth2-proxy / Pomerium / Authelia comparisons are vendor-skewed; given Tailscale is already the perimeter, **Tailscale identity headers** are the lowest-complexity option for internal tools; Caddy/Traefik DNS-01 wildcard practice unchanged in 2026 (H).

### Isolation on our hardware

- Anthropic's own tiering for running Claude Code ([secure deployment doc](https://code.claude.com), H): sandbox-runtime (good, very low overhead) → Docker (setup-dependent) → gVisor (excellent, medium/high overhead) → microVMs (excellent, high overhead); recommended production pattern at any tier: `--network none` container + Unix-socket proxy on the host for credential injection and domain allow-listing.
- Everything with kernel-level isolation needs `/dev/kvm`: **Kata, Firecracker, libkrun/Microsandbox cannot run inside an LXC** — only inside a Proxmox VM with nested virtualisation (H). **gVisor in LXC** is reported broken on the Proxmox forum — experimental at best (M). **Sysbox** remains unsupported in unprivileged LXC per our prior finding (not re-verified; it is what powers Docker Desktop ECI, which is Desktop-only) (M).
- Practical choices: (a) keep namespace-only Docker in the existing LXC (current, ADR-002); (b) add `srt`/Claude Code `/sandbox` **inside** workspaces for cheap agent containment (available today, no architecture change); (c) a nested-virt VM for microVM sandboxes — an architecture change, not a package.

### Market signals

- The category is being relabelled: Gartner's 2026 *Market Guide for Cloud Development Environments* market page now reads "Transitioning to **Agentic** Cloud Development Environments" (title H; figures paywalled, M). JetBrains exited CDEs calling the model "too niche and obsolete" in an agent-first market; Gitpod pivoted to agents and was bought by OpenAI; Daytona pivoted to agent sandboxes; Coder raised on an agent-governance thesis. Independent commentary: "agents need somewhere to live, and that somewhere looks like a CDE" (M-H).
- Two survivors with a self-hosted, non-Kubernetes path remain: **Coder** and **the Dev-Containers-on-your-own-hosts pattern** (with or without a thin orchestration layer). Everything else in scope is dead, K8s-only, cloud-only, or a different product category.

### Cost inputs (per user per month unless noted, Sep 2026)

| Item | Price | Confidence |
|---|---|---|
| Coder Community | $0 | H |
| Coder Premium / AI Premium | unpublished, annual per-user, sales-gated | H (that it is unpublished) |
| Ona Core / Enterprise | from $20/mo pooled / custom — moot | H |
| CodeCanvas | discontinued — excluded | H |
| Tailscale Personal / Standard / Premium | $0 (≤6 users) / $8 / $18 | H |
| GitHub Team | $4 (Codespaces compute extra, from $0.18/h) | H |
| Flox Team (if Nix layer with hosted sharing) | $40/seat | M |
| Infisical self-hosted | $0 (OSS) | M |

### Cross-candidate analysis and quality assessment

- **Pattern 1 — convergence on Dev Containers.** Every surviving product consumes `devcontainer.json`; investing Forge's workspace definition there is portable across Coder, plain SSH hosts, and any future product. Forge's template today is Terraform + a Dockerfile — not a devcontainer.
- **Pattern 2 — the control plane is the only thing Coder uniquely provides on our hardware.** Identity, brokered access, lifecycle, per-user tokens, authenticated app URLs. Tailscale (Services, SSH, ACL tags, identity headers) now covers a large share of that for a small trusted group without a control plane.
- **Pattern 3 — the agent layer is where vendors are moving and monetising.** Coder Agents (capped on Community), Claude Managed Agents, Codex-via-Ona. A workspace-resident Claude Code with our own skills/hooks is orthogonal to all of them and keeps working; it also means Forge is not dependent on any vendor's agent orchestration.
- **Pattern 4 — isolation is an architecture decision, not a product pick.** Nothing evaluated hardens an LXC-hosted Docker workspace beyond namespaces without a VM; `srt`/`/sandbox` is the cheap, immediate mitigation.
- **Confidence overall:** High on eliminations and on Coder's release/licence facts; Medium on Coder Agents' GA status, DevPod Pro, and forum-level sentiment. **Gaps carried forward:** Coder Agents GA/beta label; whether v2.37 template-schema changes touch our template; DevPod Pro pricing; Sysbox-in-LXC re-verification; Anthropic "generic infrastructure" self-hosted-sandbox option on a first-party page; Fly/Morph/Blaxel self-hosting.

## Integration Patterns Analysis

_Step 3 — how each surviving option integrates identity, access, web apps, secrets, the agent toolkit and the planned Hermes/OpenMemory/Langfuse pieces. Three researchers (Coder surface; devcontainers-on-hosts + Tailscale; Claude Code/observability/MCP) plus lead verification of the Tailscale Serve identity-header claim and of Coder's default-provider flags on our own v2.36.4 binary._

### Integration surface A — the Coder control plane

**Terraform provider `coder/coder` v2.19.0 (28 Jul 2026)** — the contract a template programs against (M–H; registry pages resisted direct fetch, field names corroborated from snippets — verify against the provider docs before relying on exact names):

| Resource / data | Purpose | Notes relevant to Forge |
|---|---|---|
| `coder_agent` | agent binary + init inside the compute resource | base of everything |
| `coder_app` | UI tile / URL for something listening in the workspace | `subdomain=true` needs `CODER_WILDCARD_ACCESS_URL`; `share` = owner/authenticated/public (restricting allowed levels is Premium); health checks |
| `coder_script` | start/stop/cron scripts on the agent | used today for periodic sync + keepalive |
| `coder_env`, `coder_metadata` | env injection; UI metadata | — |
| `coder_parameter` | build-time inputs with validation, `ephemeral`, `mutable` | the `--variables-file` scalar limitation we hit is separate |
| `coder_external_auth` (data) | per-user OAuth token from a configured provider; `optional` | used today for github + azuredevops |
| `coder_workspace_owner` (data) | id, name, email, groups, `oidc_access_token`, `session_token`, per-user `ssh_public_key`/`ssh_private_key`, rbac roles | per-user git config and SSH identity come from here |
| **`coder_devcontainer`** (≥2.21) | declares a `devcontainer.json` sub-environment run by the agent via `@devcontainers/cli` + Docker | **Dev Containers integration GA, default-on since 2.24** ([docs](https://coder.com/docs/admin/integrations/devcontainers/integration), H); envbuilder in maintenance mode ([docs](https://coder.com/docs/admin/integrations/devcontainers/envbuilder), H) |

**Git credentials.** `GIT_ASKPASS` → `coder gitaskpass` → control plane → external-auth token per HTTPS git call (~0.6–1 s round trip, doubled because git asks user and password separately) ([external auth](https://coder.com/docs/admin/external-auth), H/M). Headless processes use `coder external-auth access-token <id>` ([CLI](https://coder.com/docs/reference/cli/external-auth_access-token), H) — agents inside workspaces do **not** get the token automatically; explicit plumbing is required (M). Open issues: no refresh-token retrieval API (#12787), intermittent GitHub refresh failures (#17069). Community tier allows **one** external-auth integration; our template already declares two (`github`, `azuredevops`) — the ADO one is dormant but is a licence seam to catalogue.

**Login/identity.** Generic OIDC login works with any compliant IdP; Tailscale's `tsidp` is standards-compliant but not named by Coder — untested (L). `CODER_DISABLE_PASSWORD_AUTH=true` exists. **Verified on ct-forge-01 (`coder server --help`, v2.36.4):** `CODER_OAUTH2_GITHUB_DEFAULT_PROVIDER_ENABLE` (default true — the login button that misled the operator on 2026-09-11) and `CODER_EXTERNAL_AUTH_GITHUB_DEFAULT_PROVIDER_ENABLE` (default true — a Coder-managed external-auth provider our explicit block supersedes). OIDC group/role sync and Coder Groups are Premium ([idp-sync](https://coder.com/docs/admin/users/idp-sync), H).

**Automation & observability.** Full REST API + CLI (service accounts recommended for headless automation); notifications by email or webhook (delivery-preference config Premium); Prometheus on :2112 with optional agent stats ([prometheus](https://coder.com/docs/admin/integrations/prometheus), H); **audit log Premium-only** (H).

**Networking.** Client↔workspace: WireGuard peer-to-peer via STUN, fallback to coderd's embedded DERP (or Tailscale's/custom DERP) ([networking](https://coder.com/docs/admin/networking), H). `CODER_WILDCARD_ACCESS_URL` + matching wildcard cert required for subdomain apps and port-forwarding; docs recommend disabling path-based apps once wildcard is on ([wildcard](https://coder.com/docs/admin/networking/wildcard-access-url), H). Browser-only mode is Premium. Air-gapped/private-network deployment is a documented pattern; no Tailscale-only-specific caveats found (M).

**MCP / agents.** Built-in MCP server (`io.github.coder/coder`; remote `/api/experimental/mcp/http`; local `coder exp mcp server`) exposes workspace/template/agent operations to AI tools ([mcp-server](https://coder.com/docs/ai-coder/mcp-server), H); tier not stated (L). **None of it is required to run Claude Code inside a workspace** — our template already does so with plain startup scripts (M, confirmed by absence of any such prerequisite in docs).

### Integration surface B — Dev Containers on your own hosts (no control plane)

**Spec and CLI** ([spec](https://containers.dev/implementors/spec), H): lifecycle `onCreate → updateContent → postCreate → postStart → postAttach`; `containerEnv` (baked) vs `remoteEnv` (per connection, no rebuild); `hostRequirements`; `customizations.vscode`; **`secrets` is implemented as metadata only** — values come from an external store (`devcontainer --secrets-file`, keychain, vault) and surface like `remoteEnv` (M). Features (`github-cli`, `docker-outside-of-docker`, `common-utils`, …) are current in `devcontainers/features` (H). Headless: `devcontainer up` / `devcontainer exec` (M). **VS Code Remote-SSH → "Reopen in Container" on a remote Docker host is fully supported, no local Docker** ([docs](https://code.visualstudio.com/remote/advancedcontainers/develop-remote-host), H).

**Git identity.** `gh auth login --web` device flow works headless (H); SSH agent forwarding (`ForwardAgent`/`AllowAgentForwarding`) is auto-handled by VS Code's Dev Containers extension, GCM is not forwardable (M). No first-party multi-user broker exists for a *shared* host — the one-CT-per-user model sidesteps it; a GitHub-App-token bridge is the bespoke alternative (M).

**Tailscale mechanics** (all H unless noted):
- Tags via `tagOwners`; **tagged nodes have key expiry disabled by default** ([blog](https://tailscale.com/blog/tagged-key-expiry)) — the 90-day trap we hit on the gateway does not apply to tagged per-workspace nodes; OAuth clients scoped to tags mint short-lived keys (`tailscale_tailnet_key`, `ephemeral`/`preauthorized`/`reusable`) ([oauth clients](https://tailscale.com/docs/features/oauth-clients)).
- Official Docker image runs userspace by default; `TS_SERVE_CONFIG` for declarative serve; sidecar shares the app's netns ([guide](https://tailscale.com/blog/docker-tailscale-guide)).
- **Serve injects identity headers** `Tailscale-User-Login/Name/Profile-Pic` on tailnet traffic, strips them from inbound requests, **does not populate them for tagged source devices**, never on Funnel — verified by the lead on [kb/1312](https://tailscale.com/kb/1312/serve). Requires HTTPS certs enabled. `caddy-tailscale` (community) does the same via `WhoIs()` inside Caddy.
- **Tailscale Services (GA 19 Feb 2026)**: declared in admin console/API, tsnet apps can self-register; stable MagicDNS name; **several hosts can back one Service with health-based routing**; ~10 services/user on paid tiers (M, single blog); Terraform `tailscale_service` resource since provider v0.29.0 (15 May 2026), latest v0.29.2 (H, registry).
- Tailscale SSH rules: `src`/`dst` (`autogroup:self`)/`users` (`autogroup:nonroot`); widening `dst` to a tag without revisiting `users` over-grants; **TS-2026-009** root escalation via `getent` argument injection fixed in **1.98.9** — our fleet must be ≥1.98.9 (H, [advisory](https://db.gcve.eu/vuln/ts-2026-009)). Serve/Funnel: Funnel is the only public path.

**Terraform providers.** `tailscale/tailscale` v0.29.2 (acl, tailnet_key, split-DNS nameservers, search paths, **service**, OIDC/WIF credentials — no static provider secret needed) (H). Proxmox: `bpg/proxmox` is the 2026 recommendation for PVE 9 (30+ releases/yr, full LXC/VM/SDN/ACL scope, OpenTofu-compatible); `telmate/proxmox` — the one `homelab-infra` uses — is slower-moving with breaking major bumps (M, community). **PVE 9.1 `pct create <id> oci://…`** builds a native LXC from an OCI image (Tech Preview); nested Docker inside an OCI-sourced LXC is undocumented (H/gap).

**Browser tools.** `code serve-web` or code-server behind `tailscale serve` is a first-party documented pattern — auth is tailnet membership, no separate login ([kb/1164](https://tailscale.com/kb/1164/codeserver), H). JetBrains Gateway over SSH to a MagicDNS name works but is not a Tailscale integration (M). Stable per-user URLs: Serve per node (URL tied to the node) vs a **Service** (survives CT rebuild/migration, can front several hosts) vs `caddy-tailscale` wildcard (community) (M).

### Cross-cutting — the agent toolkit layer (identical under A or B)

- **Claude Code settings precedence** (H, [docs](https://code.claude.com/docs)): `managed-settings.json` (OS-deployed, unoverridable) > CLI `--settings` > `.claude/settings.local.json` > `.claude/settings.json` > `~/.claude/settings.json`. Skills/hooks/agents/MCP live in `.claude/` or `~/.claude/`; **plugins GA 2026** (marketplace May 2026); a team pins its catalogue by committing `extraKnownMarketplaces` in `.claude/settings.json` — the same works for a private marketplace repo synced by `forge-sync.sh` ([discover plugins](https://code.claude.com/docs/en/discover-plugins), H).
- **Sandbox/network policy** ([sandboxing](https://code.claude.com/docs/en/sandboxing), H): `sandbox.network.allowedDomains`, `strictAllowlist`, **`allowManagedDomainsOnly` (managed settings only)**, `deniedDomains`, HTTP/SOCKS proxy ports, `tlsTerminate` + `credentials.{envVars,files}` with `injectHosts` — secrets injected only into requests to named hosts; filesystem allow-lists with managed-only lock; `enableWeakerNestedSandbox` for Docker without privileged namespaces (explicitly weaker). Headless auth: `ANTHROPIC_API_KEY`, `CLAUDE_CODE_OAUTH_TOKEN`, `apiKeyHelper` (refreshing), Bedrock/Vertex flags ([env vars](https://code.claude.com/docs/en/env-vars), H).
- **Agent SDK hosting** ([hosting](https://platform.claude.com/docs/en/agent-sdk/hosting), H): ephemeral vs persistent container patterns; egress via a proxy enforcing domain allow-list + credential injection + logging — the same mechanism as above; never mount the real home dir; pin the CLI version; bound `maxTurns`.
- **MCP**: stdio vs Streamable HTTP; OAuth 2.1 + PKCE mandatory for HTTP; `claude mcp add --scope local|project|user` — **project scope writes `.mcp.json` into the repo**, the natural sync mechanism for Forge's shared servers ([quickstart](https://code.claude.com/docs/en/mcp-quickstart), H); the 2026-07-28 spec **release candidate** makes requests stateless (plain load-balancing of shared MCP servers behind Tailscale) (M — RC, check client support).

### Cross-cutting — observability and memory

- **Claude Code OTel** (beta): metrics/logs/traces via OTLP (`CLAUDE_CODE_ENABLE_TELEMETRY=1`, `OTEL_*`); prompt/response/tool content **redacted by default**, opt-in per field; exports carry `user.email`/`organization.id` ([monitoring](https://code.claude.com/docs/en/monitoring-usage), H). **Langfuse ingests OTLP natively** at `/api/public/otel` (HTTP protobuf/JSON, Basic Auth with project keys); legacy ingestion API sunsets on Cloud 16 Nov 2026 ([langfuse otel](https://langfuse.com/integrations/native/opentelemetry), H). Interoperability inferred from both sides' OTLP support, not vendor-certified.
- **Langfuse v3 self-hosted = six services** — web, worker, Postgres 17, ClickHouse ≥24.3, Redis/Valkey, S3/MinIO; realistic floor ~4 cores/16 GB/100 GB; core MIT with no usage limits, EE add-ons (SCIM, audit, project RBAC) key-gated ([self-hosting](https://langfuse.com/self-hosting), H). Heavier than "tracing" implies; Tailscale-only policy argues for self-hosting on a dedicated CT rather than Cloud.
- **OpenMemory / mem0**: Apache-2.0, active; self-hosted MCP server = API + Postgres + Qdrant + UI, SSE transport; **open issue mem0ai/mem0 #6080 (checked 2026-06-01): API routers ship without authentication — any caller can read/write any `user_id`; a global pause endpoint can DoS all users** (H, live issue). Not multi-user-safe without a fronting auth layer; fix status as of Sept 2026 unconfirmed (gap). This should be cited in ADR-006's re-entry conditions.

### Cross-cutting — webhook-triggered agents (the Hermes pattern)

Tailscale Serve cannot receive SaaS webhooks (GitHub/Linear are not on the tailnet); the choices are Funnel (public, `*.ts.net` certs only) or **Cloudflare Tunnel** (custom domain, permanent endpoint) — the homelab's existing, documented exception; smee-style relays are dev-only; HMAC verification (`X-Hub-Signature-256`) must terminate at the agent, which makes relays self-checking (H/M).

### Integration security patterns — what to carry into the architecture step

1. **Identity headers are only as good as their source**: Serve/WhoIs identity is absent for tagged devices — per-user machines must be user-owned; shared/tagged hosts need a real IdP (Coder login, tsidp, Authelia).
2. **Tokens**: Coder external auth = OAuth-App user token, acts as the user, refresh path has open bugs; GitHub App installation tokens (new stateless format rolling out since 27 Apr 2026) are the short-lived, non-personal best practice for any bespoke broker; Codespaces-style repo-scoped tokens are the reference bar.
3. **Secret injection**: Claude Code's `injectHosts` + a host-side proxy, or Infisical's agent/CLI, keep secrets off the workspace disk under both A and B; `devcontainer.json` `secrets` is metadata only.
4. **Fleet hygiene**: Tailscale ≥1.98.9 everywhere (TS-2026-009); Coder default-provider flags set explicitly.

### Integration need × option matrix

| Need | A — Coder | B — Dev Containers on hosts + Tailscale |
|---|---|---|
| Per-user login to the platform | Coder users / OIDC (groups Premium) | tailnet membership; Tailscale SSH identity; optional tsidp/Authelia |
| Per-user git identity in the environment | external auth (`gitaskpass`), one integration on Community; per-user SSH key from `coder_workspace_owner` | `gh auth login` device flow, forwarded SSH agent, or a GitHub-App broker; one CT per user avoids collision |
| Stable authenticated URL per workspace app | `coder_app` subdomain behind wildcard cert, `share=authenticated` | `tailscale serve` (per node) or **Tailscale Service** (stable, multi-host), identity headers; or `caddy-tailscale` wildcard |
| Lifecycle / self-service | dashboard, API, schedules, TTLs | Terraform + Ansible; PVE 9.1 OCI LXC (preview); no self-service UI |
| Portable workspace definition | `coder_devcontainer` (GA) — devcontainer.json under Coder | devcontainer.json natively |
| Agent toolkit distribution & policy | forge-sync + `.claude/` + managed settings | identical |
| Telemetry → Langfuse | identical (OTLP from Claude Code) | identical |
| Shared MCP servers | identical (`.mcp.json` project scope, HTTP + OAuth) | identical |
| Audit trail | Premium | Tailscale config audit (Standard tier), Proxmox/PVE logs, git |
| External webhooks (Hermes) | Cloudflare Tunnel (both) | Cloudflare Tunnel (both) |

### Quality assessment

High confidence on Coder's GA devcontainer path, Tailscale Serve/Services/SSH facts (primary docs, lead-verified), Claude Code settings/sandbox/OTel docs, Langfuse footprint and the OpenMemory issue. Medium on exact `coder/coder` field names (registry SPA), Tailscale Services plan limits, `tsidp`-as-Coder-IdP (inferred), MCP RC adoption. **Gaps carried forward:** nested Docker inside OCI-sourced LXC; OpenMemory auth fix status; Terraform-native Service creation in practice; Coder MCP server tier; a worked devcontainer + Tailscale Service recipe (none published).

## Architectural Patterns and Design

_Step 4 (written 2026-09-21) — three concrete target architectures for Forge on the homelab's actual substrate (Proxmox VE 9 cluster, ZFS, unprivileged LXC + Docker, PBS, HA by node-affinity + replication, Tailscale-only access, Terraform + Ansible), with the isolation, identity, data and operations trade-offs each carries. Sources: two researchers (Coder validated architectures + Tailscale multi-tenancy/Services + prebuild pipelines; Proxmox isolation/backup/ops) plus lead verification of the `tailscale_service` Terraform schema and a read-only fleet check._

### System Architecture Patterns — the three candidates

**Architecture A — Coder control plane, portable workspaces.** Keep coderd + Postgres + Caddy on CT 167 as today, but move the workspace *definition* from a Coder-specific Dockerfile/Terraform image to `devcontainer.json` run by Coder's GA Dev Containers integration (`coder_devcontainer`, agent + `@devcontainers/cli` + Docker). Coder keeps login, per-user external-auth tokens, subdomain apps behind the wildcard cert, self-service lifecycle, dashboard, API.

```
tailnet ──► Caddy (*.forge, LE DNS-01) ──► coderd ──► Postgres 16
                                            │  provisioner (Terraform: docker provider)
                                            ▼
                     CT 167 (unpriv LXC, nesting+keyctl) ── Docker ── workspace container
                                                                    └─ devcontainer (sub-agent)
                                                                       Claude Code + managed settings
```

- Multi-company: **one Coder instance + DB per company** (Community is hard-capped to a single organisation; Organizations are Premium — [pricing](https://coder.com/pricing), [blog](https://coder.com/blog/coder-community-open-source), H). One CT per company is the natural unit.
- Fit note: Coder's smallest *validated* architecture is the 1,000-user Kubernetes tier (coderd 2 vCPU/8 GB ×3, Postgres 8 vCPU/30 GB) ([validated architectures](https://coder.com/docs/admin/infrastructure/validated-architectures), H). A single-node Docker deployment is supported but outside the validated set; rule of thumb ~1 vCPU + 2 GB per 250 users, minimum coderd 1 CPU/2 GB (M). CT 167's 6C/12 GB is generous for 1–10 users.

**Architecture B — no control plane: one environment per user/project on Proxmox, Tailscale as the platform.** Each user (or project) gets an unprivileged LXC created by Terraform from a template CT (ZFS clone, near-instant), provisioned by Ansible (Docker, `devcontainer` CLI, Claude Code, toolkit sync, Tailscale as a **tagged** node with an OAuth-client key — no expiry). The workspace itself is a devcontainer on that CT. Access: Tailscale SSH (identity from the tailnet), VS Code Remote-SSH → Reopen in Container, or `code serve-web`/code-server behind `tailscale serve` (tailnet-only HTTPS, identity headers). Stable URLs via **Tailscale Services** (`svc:<project>`, Terraform `tailscale_service`, multi-host capable). Policy: Claude Code `managed-settings.json` pushed by Ansible.

```
tailnet (ACL: group:<team> → tag:ws-<project>; svc:<project>) 
   │ Tailscale SSH / Remote-SSH / https://<svc>.<tailnet>.ts.net
   ▼
CT per user/project (unpriv LXC, tagged tailscale node) ── Docker ── devcontainer
   Terraform (bpg/proxmox or telmate) ── Ansible (dev-host + forge roles) ── managed-settings.json
```

- Multi-company: **one tailnet per company** (no MSP console; multi-tailnet-under-one-org is alpha and sales-provisioned — [docs](https://tailscale.com/docs/features/multiple-tailnets), H) and one Proxmox tenant per company via SDN zone/VNet + IPAM + VNet firewall ([SDN wiki](https://pve.proxmox.com/wiki/Software-Defined_Network), H).
- What it lacks by construction: a per-user *login* to anything but the tailnet; a self-service UI; per-user git tokens brokered centrally (device-flow `gh auth` or a GitHub-App broker instead).

**Architecture C — portable core, optional control plane.** Make B's artefacts the product: the devcontainer definition, the prebuilt image (`devcontainers/ci` → GHCR, Cosign keyless-signed by digest), the Ansible `forge-*` roles, the managed-settings policy, the toolkit sync, the Tailscale ACL/Service definitions in Terraform. Run them **without** Coder for the homelab and any single-operator customer; put **Coder in front** (Architecture A) only for a customer that needs self-service, a login page, dashboards or brokered tokens for a team. Because Coder now consumes `devcontainer.json` natively, the same image and policy run under both.

### Design Principles and Best Practices

1. **The workspace definition must not depend on the control plane.** Dev Containers is the only format every survivor consumes; Coder's Dockerfile-in-Terraform template is the lock-in point today.
2. **Tailscale is the perimeter and the identity substrate.** Membership, tags, SSH identity, Serve identity headers, Services. Anything public goes through the one documented exception (Cloudflare Tunnel).
3. **Policy lives in Claude Code's managed layer, not in the platform.** `managed-settings.json` + `allowManagedDomainsOnly` + `injectHosts` give the same agent guardrails under A, B or C.
4. **One instance / one tailnet / one Proxmox tenant per company.** Both Coder Community and Tailscale push this way; SDN zones make it cheap on Proxmox.
5. **Secrets never land on the workspace disk.** Coder external auth, Claude Code credential injection at the proxy, Infisical agent, `devcontainer.json` `secrets` as metadata only.
6. **Treat isolation as a separate axis from the product choice** (see Security).

### Scalability and Performance Patterns

- **A:** vertical on CT 167 for 1–10 users; provisioner concurrency is the practical limit; Postgres and coderd are single instances (HA replicas Premium). Coder does not support downgrades — back up before every monthly upgrade ([upgrade best practices](https://coder.com/docs/install/upgrade-best-practices), H).
- **B:** horizontal by CT; ZFS clones are copy-on-write and near-instant (5 clones with unique IP/hostname ≈30 s reported), but bulk Terraform clones slow when over-parallelised — throttle `terraform apply` for batch creation (M). Sizing must be coherent across the **two cgroup layers** (LXC memory+swap ceiling → Docker `--memory`) or the outer OOM-killer fires without throttling (M). PVE 9 SDN IPAM can replace Pi-hole-side IP allocation for per-project VNets (H).
- **Both:** the agent workload, not the IDE, sets the ceiling — Anthropic's baseline is ~1 GiB/1 CPU per headless agent; token cost dominates infra cost.

### Integration and Communication Patterns

Covered in step 3; the architecture-level consequence is the matrix there: identity/URL/lifecycle differ between A and B, while the toolkit, MCP, telemetry and webhook layers are identical. Under C the differing part is the pluggable part.

### Security Architecture Patterns

**Isolation ladder on this hardware** (Anthropic's tiering + Proxmox's own guidance):

| Tier | Mechanism | Available under | Notes |
|---|---|---|---|
| 0 | Claude Code `/sandbox` / `srt` inside the workspace | A, B, C — today | OS-level (bubblewrap), no architecture change; weaker nested mode inside Docker |
| 1 | Docker namespaces inside an **unprivileged** LXC | A, B, C — today | UID-shifted root; AppArmor + seccomp + cgroup v2 (v1 removed in PVE 9.0). Proxmox: "safe by design" for trusted workloads; **"for maximum isolation… nesting containers inside a Proxmox QEMU VM remains a recommended practice"** ([unprivileged LXC wiki](https://pve.proxmox.com/wiki/Unprivileged_LXC_containers), H) |
| 2 | gVisor inside LXC | experimental | forum reports of breakage (M) |
| 3 | microVMs (Kata/Firecracker/libkrun) in a **nested-virt VM** | requires a VM, not LXC | `kvm-*` `nested=1` + `--cpu host` or PVE 9.1's granular nested-virt CPU flag ([nested virt wiki](https://pve.proxmox.com/wiki/Nested_Virtualization), H); **cannot be live-migrated** → HA becomes cold restart; qualitative "quietly slow" overhead, no benchmark |

Consequences: ADR-002 (privileged workspaces accepted for one operator) stands for the homelab; for a *multi-user* customer the honest options are Tier 1 with per-user CTs (B/C) — one CT per user is itself a stronger boundary than shared Docker on one CT — or a dedicated nested-virt sandbox VM per company for untrusted agent runs (Tier 3), accepting no live migration.

**Identity edges:** Serve/WhoIs identity is absent for **tagged** source devices — user endpoints must be user-owned; workspace CTs are tagged (that is the right way round). Tailscale SSH rules: keep `dst: autogroup:self` semantics unless `users` is tightened; fleet ≥1.98.9 (TS-2026-009; gateway at 1.96.5 has `RunSSH:false` — not exposed, image bump owed). Coder default-provider flags set explicitly. One external-auth integration on Community — the dormant `azuredevops` block is a licence seam.

### Data Architecture Patterns

- **A:** Postgres is the single source of truth (users, templates, workspaces, external-auth tokens). No Coder-native backup: `pg_dump` via a vzdump/PBS **pre-backup hook** so the CT snapshot carries an application-consistent dump, not just a crash-consistent volume (H for the hook mechanism, M for the pattern). Template versions live in Postgres too — the git repo is the recovery path.
- **B/C:** state is in git (Terraform, Ansible, ACL, Services), in the registry (prebuilt images, signed by digest), and on per-CT volumes (home dirs). Nothing central to lose but the tailnet config — which is why the ACL/DNS/Services export into `homelab-infra/tailscale/` (D5) matters.
- **PBS for all:** snapshot mode on ZFS (silently downgrades to suspend if unsupported — check logs); per-mountpoint exclude for Docker overlay/cache dirs; `pct restore` to a new CTID for restore tests; **prune only drops metadata — schedule garbage collection or space is never reclaimed** ([PBS maintenance](https://pbs.proxmox.com/docs/maintenance.html), H).
- **Observability data:** Langfuse v3's ClickHouse/Redis/MinIO make it the heaviest stateful component in the whole design (~4C/16 GB) — its own CT, its own backup policy.

### Deployment and Operations Architecture

| Concern | A — Coder | B — hosts | C — portable core |
|---|---|---|---|
| Components to run | coderd, Postgres, Caddy, provisioner, Docker (per company) | Docker + devcontainer CLI + tailscaled per CT; Terraform/Ansible on the workbench | B, plus A where a customer wants it |
| Upgrades | monthly Coder line, migrations, **no downgrade**, Postgres major bumps | apt + Ansible; devcontainer CLI/VS Code server self-update; Tailscale auto-update | both, but Coder failures never take the workspaces' definition with them |
| HA | CT 167 as today (restart-on-failover); nested-virt VMs excluded | per-CT node-affinity + replication as project CTs today | same |
| Networking | wildcard DNS + cert per instance; Coder DERP embedded | Tailscale Services + ACL tags; SDN VNet per company | both |
| Audit | Premium | Tailscale config audit (Standard), PVE task log, git history | git is the audit trail for the core |
| Operator surface | dashboard + CLI + API | Terraform/Ansible + tailnet admin | — |

### Architecture trade-off summary (qualitative; scored in step 5)

| Criterion | A | B | C |
|---|---|---|---|
| Self-service for a team | ●●● | ○ | ●●● when A is added |
| Per-user identity & token brokering | ●●● (1 integration on Community) | ●● (tailnet identity; git via device flow/broker) | ●●/●●● |
| Portability / lock-in | ●● (devcontainer under Coder) | ●●● | ●●● |
| Operational weight per company | ●○○ (5 components + monthly upgrades) | ●●● (nothing central) | ●● |
| Isolation ceiling on LXC | Tier 1, shared host | Tier 1, **per-user CT** | same as B; VM tier optional |
| Multi-company | one instance per company | one tailnet + SDN tenant per company | same |
| Cost of features actually needed | free tier fits; audit/groups Premium | Tailscale Standard $8/user if SCIM/posture wanted | same |
| Migration from today | small (template → devcontainer) | medium (roles exist; Services/ACL/Terraform new) | medium, incremental |

### Quality assessment

High confidence on Coder's single-org cap, validated-architecture floor and no-downgrade rule; on Tailscale Services mechanics and Terraform schema (lead-verified); on Proxmox's isolation guidance, cgroup v2, nested-virt live-migration block and the PBS prune/GC gotcha. Medium on Terraform clone throughput, cgroup double-limit behaviour, nested-virt overhead (qualitative only) and the tailnet-per-customer inference. **Gaps carried forward:** HA semantics for nested-virt VMs (undocumented); Docker inside an OCI-sourced LXC (unexplored); Services count limits per plan; a controlled clone benchmark.

## Implementation Approaches and Technology Adoption

_Step 5 (2026-09-21) — what each architecture costs to reach from today's Forge, how it is operated, what it depends on, and a weighted score against the operator's criteria. Inputs: two researchers (migration mechanics; adoption lessons and operational risk), lead verification of the Tailscale postmortem and the Coder CVE at their primary sources, and a read-only inventory of the current repos and CT 167._

### Where Forge stands today (measured)

- Template: `main.tf` 740 lines + `variables.tf` 335 + `poc.variables.yaml` 110; providers `coder/coder`, `kreuzwerker/docker`; `forge-onboard.sh` and `forge-sync.sh` are **base64-embedded into Terraform** and driven by agent env — this, not the image, is the Coder-specific coupling.
- Image: `workspace/Dockerfile` (134 lines) **already builds on `mcr.microsoft.com/devcontainers/javascript-node:1-20-bookworm`**, and a minimal `workspace/devcontainer.json` exists (build + `remoteUser` + 3 extensions). `@anthropic-ai/claude-code@latest` and `@openai/codex@latest` are **unpinned**; image 4.33 GB.
- Ansible already in hand: `dev-host` (551 lines), `remote-access` (715), `forge-coder-host` (7,290), `forge-dns` (1,371), `forge-workspace-image` (1,068). Toolkit: `agentic-ai` (608 md/py/sh/json files). CT 167: 6 cores, 12 GB, coder/postgresql/caddy active.

### Technology adoption strategies

**Common first step under every architecture — make the workspace definition portable (est. 1 session).** Move the onboarding and sync logic out of `main.tf` into `workspace/devcontainer.json` lifecycle hooks (`onCreateCommand` → toolkit install, `postStartCommand` → `forge-sync`), pass identity via `remoteEnv`, pin Claude Code and Codex versions in the Dockerfile, and prebuild the image with `devcontainers/ci` to GHCR, signed by digest with Cosign keyless ([prebuild guide](https://containers.dev/guide/prebuild), [devcontainers/ci](https://github.com/devcontainers/ci), H). Three independent 2025–26 write-ups converge on the same principle — *"treat `devcontainer.json` as the durable contract and keep the runtime swappable"* ([stribog](https://stribog.com/blog/devpod-coder-self-hosted-developer-environments-codespaces-exit), [Big Iron](https://bigiron.cc/guides/self-hosted-cloud-dev-environments-with-devcontainers), M). Precedent for the pitfalls of SSH-into-container designs: one author replaced DevPod's SSH layer with plain `docker exec` attach ([fabiorehm](https://fabiorehm.com/blog/2025/11/11/devpod-ssh-devcontainers), M).

**Architecture A — Coder with devcontainer workspaces (est. 1–2 sessions after the common step).**
- Flags: `CODER_AGENT_DEVCONTAINERS_ENABLE` (default true ≥2.24), `…_PROJECT_DISCOVERY_ENABLE` (≥2.25), `…_DISCOVERY_AUTOSTART_ENABLE` (default false) ([integration](https://coder.com/docs/admin/integrations/devcontainers/integration), H). Declare `coder_devcontainer` explicitly rather than rely on discovery (issue #19345: every devcontainer in a repo is treated as Coder-managed).
- The devcontainer is a **sub-agent** (`coder ssh <ws>.<agent>`, own port-forward, `coder open vscode`); `coder_app` is not derived from `devcontainer.json` — point an explicit `coder_app` at the sub-agent or use `appPort` through the parent ([working with dev containers](https://coder.com/docs/user-guides/devcontainers/working-with-dev-containers), H).
- Open bugs to plan around (checked 2026-09-21, H): #24626 `customizations.vscode` not applied on first connect (needs Rebuild Container); #21109 `CODER_*` env not propagated into the devcontainer via VS Code; #18764 prebuilt workspaces + devcontainers not reliably combinable. Startup-script vs lifecycle-hook ordering is **undocumented** — keep all workspace logic in the hooks and leave the startup script to agent bootstrapping only.
- Template hygiene: existing workspaces do not auto-rebuild on template push; keep the home volume block untouched or `lifecycle { ignore_changes = all }` ([resource persistence](https://coder.com/docs/admin/templates/extending-templates/resource-persistence), H). Remove the dormant `azuredevops` external auth (Community = one integration). Set `CODER_OAUTH2_GITHUB_DEFAULT_PROVIDER_ENABLE` / `CODER_EXTERNAL_AUTH_GITHUB_DEFAULT_PROVIDER_ENABLE` explicitly. Add a PBS pre-backup `pg_dump` hook. Track the monthly release line (no downgrade).

**Architecture B — control-plane-less CT per user/project (est. 2–3 sessions; most building blocks exist).**
- New Ansible role `forge-workspace` on top of `dev-host` + `remote-access`: Docker, `@devcontainers/cli`, `devcontainer up` as a systemd unit (or compose restart policy), `code serve-web --host 0.0.0.0 --port <p> --without-connection-token --accept-server-license-terms` as a systemd **user** service, `tailscale set --operator=<user>`, `tailscale serve --bg` / `serve set-config` **re-applied idempotently at boot** — open issue #19298 (set-config state not preserved across reboots) and #17769 (Tailscale Services have no built-in re-advertise-on-boot) both require an `ExecStartPost` after `tailscaled.service` (M-H, [#19298](https://github.com/tailscale/tailscale/issues/19298), [#17769](https://github.com/tailscale/tailscale/issues/17769)).
- Terraform: CT from a template (ZFS clone) via the existing provider (`bpg/proxmox` recommended for new work), `tailscale_tailnet_key` from a tag-scoped OAuth client (`tag:ws-<project>`, no expiry), `tailscale_service` (`svc:<project>`, `tcp:443`, tags), ACL grants `group:<team> → tag:ws-<project>` and Tailscale SSH rules. Provider v0.29.2 supports OIDC/WIF credentials — no static API key in state.
- Git identity: `gh auth login` (device flow) + `gh auth setup-git` is the simplest maintained path (token in `~/.config/gh/hosts.yml`, H); for short-lived non-personal tokens, `git-credential-github-app` (Go) or `git-credential-github-app-auth` (Rust) with `useHttpPath = true` and a cache helper ≥7200 s (M-H). VS Code: Remote-SSH → *Reopen in Container* on the CT (remote Docker, key auth) (H). JetBrains Gateway needs only SSH+SFTP; ≥2 cores/4 GB per backend (M).
- Per-company isolation: tailnet per company; PVE SDN zone/VNet + IPAM + VNet firewall when a second company lands.

**Architecture C — do the common step, run B on the homelab, keep A as the "with control plane" profile.** Adoption is incremental: nothing in B invalidates A because both consume the same `devcontainer.json` and prebuilt image; Coder is added per customer, one instance per company.

### Development workflows and tooling

- Image pipeline: `devcontainers/ci` on a self-hosted runner (multi-arch on GitHub-hosted runners is ~1 h via QEMU — irrelevant unless arm64 targets appear), push to GHCR, Cosign keyless by digest, SBOM attestation; the devcontainer references the image by digest.
- Toolkit distribution: `forge-sync` (git) + `extraKnownMarketplaces` for plugins + project-scope `.mcp.json`; policy in `managed-settings.json` pushed by Ansible (both A and B), `sandbox.network.allowManagedDomainsOnly` + `injectHosts` for secrets.
- Version discipline: pin `@anthropic-ai/claude-code@X.Y.Z`, set `DISABLE_AUTOUPDATER=1` in the image and `autoUpdatesChannel: stable` in managed settings (H, Anthropic docs via researcher; Anthropic does remove features — `TaskOutput` removed Sep 2026, M). Pin the devcontainer CLI; the spec evolves incrementally (lockfile graduation proposal Apr 2026), no breaking incidents found (M).

### Testing and quality assurance

- Definition tests: `devcontainer up && devcontainer exec -- forge-selftest` in CI for every image build (toolkit present, hooks fire, `claude --version` pinned, MCP servers reachable).
- Platform tests: the audit's acceptance gates (a–k) already exist for A; for B the equivalents are: Tailscale SSH login as a user (identity headers present via Serve), Service resolves and routes, `code serve-web` reachable tailnet-only and **not** from LAN, private clone works with the per-user token, managed-settings lock cannot be overridden from `.claude/settings.json`.
- Regression pack: the `forge-dns` role's A+AAAA assertion pattern generalises — every name a role lands must be asserted for rcode, not just answer.

### Deployment and operations practices

| Concern | A | B / C-core |
|---|---|---|
| Monthly upgrade | coderd + migrations, back up first, no downgrade; monitor GHSA (CVE-2026-55431 fixed 2.34.2 — our 2.36.4 unaffected, [advisory](https://github.com/coder/coder/security/advisories/GHSA-v54h-cp2w-9x4g), H) | apt + Ansible; Tailscale auto-update; devcontainer CLI/VS Code server pinned |
| Backup | PBS snapshot + `pg_dump` hook; template git as recovery | PBS per CT; git + registry hold the definition; ACL/Services in Terraform |
| HA | CT 167 restart-on-failover | per-CT node-affinity; no nested-virt VMs unless sandbox tier 3 is chosen |
| Observability | Coder Prometheus + agent stats; Claude Code OTel → Langfuse | node exporter per CT; Claude Code OTel → Langfuse; Tailscale config audit (Standard) |
| Time to first workspace | minutes (image pull), seconds warm; prebuilds are extra infra ([Coder blog](https://coder.com), H) | ZFS clone + Ansible run: minutes; warm devcontainer seconds (not benchmarked — gap) |
| Estimated ongoing effort | generic self-hosting guidance: ~2–4 h/month for a team-critical platform (M, not Coder-specific) | lower central effort; effort moves to per-CT hygiene, which Ansible already automates |

### Team organisation and skills

Single operator today. **A** adds Postgres administration, Coder release/CVE cadence, template-version discipline and the Tasks→Agents narrative on top of Terraform/Ansible/TLS. **B** stays inside skills already exercised in this homelab — Terraform, Ansible, Tailscale ACLs, systemd — plus devcontainer-spec literacy; it removes a database and a second web application from the operator's patch surface. For a customer team, A's dashboard reduces the operator-in-the-loop for lifecycle; B shifts that to Terraform/Ansible runs unless a thin self-service layer is added later.

### Cost optimisation and resource management

Per company, per month (Sept 2026 prices, H unless noted): Coder Community $0 (Premium unpublished); Tailscale Personal $0 up to 6 users (Tailscale SSH capped at 5 hosts), Standard $8/user (SCIM, posture, config audit) — **Pricing v4 (8 Apr 2026) bills per assigned seat, existing customers grandfathered ≥12 months** ([pricing v4](https://tailscale.com/blog/pricing-v4), H); GitHub Team $4/user; Infisical $0; Langfuse $0 + ~4C/16 GB of compute; Claude API/seat costs dominate everything above. Hardware: A needs one 6C/12 GB CT per company plus workspaces; B needs one CT per user/project (2–4 GB each at idle, sized coherently across the two cgroup layers).

### Risk assessment and mitigation

| Risk | Evidence | Mitigation |
|---|---|---|
| Coder product churn (Tasks removed v2.37; agent layer monetised; monthly line; no downgrade) | release notes, pricing, H | Forge never depends on Coder Tasks/Agents; devcontainer-portable definition; back up before upgrades |
| Coder Community limits (single org; one external auth; audit/groups Premium) | pricing/blog, H | one instance per company; drop ADO auth; git as audit trail |
| Tailscale control-plane dependency | Tailscale's own postmortem (21 Jan 2026): **nine periods of partial downtime/slowness in ~1 month**; data plane and existing connections kept working; blocked: admin console, device approvals, ACL changes ([post](https://tailscale.com/blog/hypergrowth-isnt-always-easy), H). *A secondary blog's "19 SQLite corruption incidents" claim did not match the primary and is not used.* | onboarding/ACL changes are the exposure, not daily work; Headscale is a client-config fallback (loses SCIM/posture/audit) |
| Tailscale pricing shift to per-seat | pricing v4, H | ≤6 users free; budget Standard for customers |
| Claude Code fast cadence / removals | v2.1.270 (12 Sep 2026); `TaskOutput` removal | pin + `DISABLE_AUTOUPDATER=1` + stable channel; toolkit self-test in CI |
| Devcontainer-under-Coder bugs | #24626, #21109, #18764 | keep logic in hooks; explicit `coder_devcontainer`; no prebuilt-workspace pooling |
| Tailscale Serve/Services state not persisted across reboot | #19298, #17769 | systemd `ExecStartPost` after `tailscaled` |
| OpenMemory without auth | mem0 #6080 | gate behind Tailscale ACL / auth proxy; single-user only until fixed |
| Isolation on shared LXC Docker | Proxmox wiki steer to VMs for max isolation | per-user CT (B/C); nested-virt VM tier only where required (no live migration) |
| Unpinned `@latest` in the image | Dockerfile:40 | pin now (common step) |

## Technical Research Recommendations

### Weighted scoring

Scores 1–5 per criterion; weights differ by case. (a) = homelab, single operator; (b) = multi-company/team reuse.

| Criterion | w(a) | w(b) | A Coder+devcontainers | B hosts | C portable core (+A where needed) |
|---|---|---|---|---|---|
| Self-service & team fit (1–10 users) | 1 | 3 | 5 | 2 | 4 |
| Proxmox/LXC friendliness, no K8s | 3 | 2 | 4 | 5 | 5 |
| Per-user identity & secret brokering | 1 | 3 | 4 | 3 | 4 |
| Reproducibility / IaC / portability | 3 | 3 | 4 | 5 | 5 |
| Tailscale-only access fit | 3 | 2 | 4 | 5 | 5 |
| Operational weight | 3 | 2 | 2 | 4 | 3 |
| Cost of features actually needed | 2 | 2 | 4 | 5 | 5 |
| Maturity & trajectory (Sept 2026) | 2 | 3 | 3 | 4 | 4 |
| Migration cost from today | 2 | 1 | 4 | 2 | 3 |
| Isolation ceiling for multi-user | 1 | 3 | 2 | 4 | 4 |
| **Weighted mean (a) homelab** | | | **3.57** | **4.19** | **4.29** |
| **Weighted mean (b) teams** | | | **3.58** | **3.92** | **4.25** |

The gap between A and B/C is driven by operational weight, cost, isolation and trajectory; A's advantages (self-service, login, brokered tokens) are real but only weigh heavily in case (b) — and C recovers them where a customer needs them.

### Recommendation (a) — homelab, single operator

**C without Coder in steady state.** Do the common step; then run the homelab's own Forge as B (one CT per project — which is what the homelab already does with `ct-dev-homelab` and the project CTs), with Tailscale SSH/Remote-SSH, `code serve-web` behind Serve, Services for stable names, managed settings for policy. Keep CT 167's Coder instance **only as the reference/demo deployment for customers** and to finish the FE4 gates already planned; retire it if no customer needs A within a defined window. Expected verdict framing for FE4-S04: **DOES-NOT-PORT as a homelab necessity, PORTS-WITH-CAVEATS as a customer profile.**

### Recommendation (b) — multi-company / team reuse

**C: portable core first, Coder per customer on demand.** Ship the devcontainer + signed image + `forge-*` roles + managed policy + Terraform (Proxmox, Tailscale ACL/keys/Services) as the product. For a customer with a team that needs self-service, a login page, brokered git tokens and dashboards, add Coder Community (one instance and DB per company; devcontainer workspaces; explicit `coder_devcontainer`; external auth GitHub only) — accept audit-log/groups being Premium or substitute git + Tailscale config audit. For a customer that is one or two people, B alone. Isolation: per-user CT by default; a nested-virt sandbox VM (no live migration) only if untrusted agent execution is a stated requirement.

### Implementation roadmap

| Phase | Scope | Size | Depends on |
|---|---|---|---|
| 0 — Hygiene (now) | pin Claude Code/Codex; `DISABLE_AUTOUPDATER`; managed-settings skeleton; Tailscale ≥1.98.9 fleet-wide (gateway image bump); Coder default-provider flags; drop ADO auth; PBS `pg_dump` hook; ACL/Services export to `homelab-infra/tailscale/` | S | — |
| 1 — Portable definition | hooks in `workspace/devcontainer.json`; scripts out of `main.tf`; `devcontainers/ci` → GHCR, Cosign by digest; `coder_devcontainer` in the template; toolkit self-test | M | Phase 0 |
| 2 — FE4 on Coder as planned | gates a–k with the devcontainer-based workspace; verdict per framing above | M | Phase 1, consent click |
| 3 — B on the homelab | `forge-workspace` role; Terraform `tailscale_*`; convert one CT (`ct-dev-homelab`) from VS Code Tunnels to Remote-SSH + Serve + Service; Tailscale SSH | M | Phase 1 |
| 4 — Customer profile | per-company Terraform module (CT/tailnet/SDN); optional Coder instance module; runbooks | M–L | Phase 2 + 3 |
| Deferred | Langfuse CT (~4C/16 GB), OpenMemory behind auth, sandbox VM tier | — | ADR-006 re-entry |

### Technology stack recommendations

Dev Containers (spec + CLI, pinned) · prebuilt image on the official devcontainer base, GHCR, Cosign · Claude Code pinned + managed settings · Tailscale (tags, OAuth-client keys, SSH, Serve, Services; provider v0.29.x) · Proxmox LXC via Terraform (`bpg/proxmox` for new modules) + Ansible roles · Coder Community as an optional per-company profile · Infisical for secrets when a second company arrives · Langfuse self-hosted, OTLP.

### Skill development requirements

Devcontainer spec and CLI internals; Tailscale ACL grammar (ssh rules, tags, Services); Cosign/Sigstore keyless signing; Coder devcontainer sub-agent model (for the A profile); PVE SDN zones/VNets/IPAM (for the second company).

### Success metrics and KPIs

Time-to-first-workspace for a new user (target: < 15 min end-to-end, < 2 min warm); onboarding steps requiring the operator (target: create user/CT + ACL only); image drift (all workspaces on the same digest); toolkit self-test pass rate per build (100 %); managed-policy coverage (every workspace has `allowManagedDomainsOnly`); secrets-on-disk audit (zero tokens in home dirs); upgrade MTTR (Coder profile) and unplanned control-plane downtime; cost per user per month excluding LLM tokens.

---

# Research Synthesis — Forge Beyond Coder: Workspace-as-Product on Proxmox and Tailscale

## Executive Summary

Forge set out to give every developer an identical, agent-ready workspace — Claude Code with a curated skills/hooks/wiki toolkit, private repos cloned with the user's own GitHub identity, web tools behind authentication, reachable only over Tailscale, all managed as code on a Proxmox homelab and reusable for other small companies. The proof of concept implemented this on Coder v2.36, and its first audit surfaced roughly twenty findings, most of them in the control plane rather than in the workspace. That prompted the question this report answers: *is the control plane the right investment?*

The market moved while the PoC was being built. In the twelve months to September 2026 the "cloud development environment" category was reclassified by its own vendors and by Gartner into *agentic* environments: JetBrains shut CodeCanvas down calling the model "too niche and obsolete", Gitpod became Ona and is being acquired by OpenAI to run Codex agents, Daytona pivoted to closed agent sandboxes, DevPod's vendor walked away, and Coder raised $90 M on an agent-governance thesis, removed "Coder Tasks" in v2.37 and now meters hosted "Coder Agents" behind an AI-Premium tier. Gartner's market guide is literally retitled *"Transitioning to Agentic Development Sandbox Platforms"* and it forecasts that by 2027 most agentic engineering teams will treat the IDE as optional ([Gartner press release, 20 May 2026](https://www.gartner.com/en/newsroom/press-releases/2026-05-20-gartner-says-the-market-for-enterprise-ai-coding-agents-is-entering-a-new-phase-of-expansion-and-competitive-realignment), [Peer Insights market page](https://www.gartner.com/reviews/market/cloud-development-environments); M — press-level). Forge's actual value — the toolkit, the policy, the identity model — lives in the workspace, which is precisely the layer every vendor is now commoditising onto the Dev Containers standard.

**Key technical findings**

- **Exactly two options survive the hard constraints** (self-hosted, no Kubernetes, Proxmox LXC/Docker, Tailscale-only): Coder, and Dev Containers on your own hosts. All others are eliminated on facts, not preference (§ Technology Stack Analysis).
- **Coder's unique contribution is the login + per-user token + subdomain-app + self-service loop**; its Community tier is single-organisation, one external-auth integration, no audit log — and its smallest *validated* architecture is a 1,000-user Kubernetes tier. It now runs `devcontainer.json` natively (GA since 2.24), which makes the workspace definition portable *while staying on Coder* (§ Integration Patterns).
- **Tailscale closed the gaps that used to force a control plane**: Serve injects identity headers (verified), Services (GA Feb 2026, Terraform since May) give stable multi-host URLs, tagged nodes no longer expire, Tailscale SSH replaces key management. Its control plane had nine partial outages in one month over 2025/26 — existing connections kept working; onboarding and ACL changes did not (§ Architectural Patterns, § Implementation).
- **Agent guardrails are platform-independent**: Claude Code's `managed-settings.json` with `allowManagedDomainsOnly` and host-scoped credential injection, plugins pinned via a git marketplace, project-scope `.mcp.json`, OTLP telemetry into self-hosted Langfuse. None of it depends on who manages the workspace.
- **Isolation is an architecture decision, not a product pick**: Proxmox's own guidance is that unprivileged LXC is "safe by design" for *trusted* workloads and that maximum isolation means a VM; microVM sandboxes need nested virtualisation, which blocks live migration. A CT per user is a stronger boundary than shared Docker on one CT without going to VMs.
- **Two integrations need budget regardless**: Langfuse v3 is six stateful services (~4 C/16 GB); OpenMemory's API currently ships without authentication.

**Technical recommendations**

1. **Adopt Architecture C — portable core, optional control plane.** The devcontainer definition, signed prebuilt image, `forge-*` Ansible roles, managed Claude Code policy and Terraform for Proxmox/Tailscale are the product. Coder Community is a per-company add-on (one instance and database each) for teams that need self-service, a login page and brokered git tokens.
2. **Homelab: run without Coder in steady state**; keep CT 167 as the customer reference deployment, finish the FE4 gates already planned, frame the PoC verdict as *does-not-port as a homelab necessity, ports-with-caveats as a customer profile*.
3. **Do the common first step now**: move `forge-onboard.sh`/`forge-sync.sh` from base64-in-Terraform into devcontainer lifecycle hooks; pin Claude Code/Codex and disable the auto-updater; prebuild and sign the image; put `managed-settings.json` under Ansible.
4. **Land the hygiene items independent of the decision**: Tailscale ≥1.98.9 fleet-wide, Coder default-provider flags explicit, drop the dormant Azure DevOps external auth, PBS `pg_dump` pre-backup hook, export the tailnet ACL/DNS/Services into `homelab-infra/tailscale/`.
5. **Defer with conditions**: Langfuse on its own CT when tracing is actually needed; OpenMemory only behind an auth layer; a nested-virt sandbox VM only if untrusted agent execution becomes a stated requirement.

## Table of Contents

1. Introduction and Methodology
2. Landscape and Architecture Analysis → *Technology Stack Analysis* (step 2) and *Architectural Patterns and Design* (step 4)
3. Implementation Approaches → *Implementation Approaches and Technology Adoption* (step 5)
4. Technology Stack Evolution and Trends → step 2, *Market signals*
5. Integration and Interoperability → *Integration Patterns Analysis* (step 3)
6. Performance and Scalability → step 4, *Scalability and Performance Patterns*
7. Security and Compliance → step 4, *Security Architecture Patterns*; step 3, *Integration security patterns*
8. Strategic Recommendations → step 5, *Technical Research Recommendations*; this synthesis
9. Roadmap and Risk → step 5, *Implementation roadmap*, *Risk assessment and mitigation*
10. Future Outlook (below)
11. Methodology and Source Verification (below)
12. Appendices (below)

## 1. Introduction and Methodology

**Significance.** Forge is meant to be reused across companies; a foundation chosen in 2026 has to survive the category's realignment around agents and the vendor pivots that came with it. The cost of choosing wrong is not the PoC — it is re-platforming every customer.

**Method.** BMad technical-research workflow, steps 1–6, 2026-09-14 → 2026-09-21. Fourteen research agents ran in parallel per step (five for the landscape, three for integration, two for architecture, two for implementation, plus two spot-checks), each instructed to verify against live primary sources and to grade confidence. The lead re-verified every single-sourced or decision-bearing claim: the OpenAI–Ona acquisition (three independent outlets), Ona's unsupported Linux runner, GitHub Team pricing, Tailscale Serve identity headers, the `tailscale_service` Terraform schema, the Coder default-provider flags on our own binary, Coder CVE-2026-55431, and Tailscale's January 2026 postmortem — where a researcher's "19 SQLite corruption incidents" was found not to match the primary and was replaced by the accurate "nine partial outages in one month". Local facts (repo sizes, Dockerfile base, existing roles, CT 167 state, fleet Tailscale versions) were measured read-only.

**Goals achieved.** (a) A scored comparison on the operator's nine criteria plus isolation; (b) recommendations for the homelab and for multi-company reuse, each with consequences for the current PoC and the FE4 verdict; (c) a concrete, sized roadmap; (d) a risk register with mitigations; (e) a list of hygiene items that are correct under any decision.

## 2–9. Detailed analysis

The step sections above are the body of this report and are not repeated here:

- *Technology Stack Analysis* — category map, candidate status board, Coder in depth, eliminations on hard facts, client-only/status-quo building blocks, access/identity layer, isolation on our hardware, market signals, cost inputs.
- *Integration Patterns Analysis* — Coder's Terraform/API/auth/networking surface; devcontainers + Tailscale mechanics (tags, OAuth-client keys, Serve identity headers, Services, SSH, providers, PVE 9.1 OCI, browser tools); the platform-independent agent toolkit layer; observability and memory; webhook ingress; the need × option matrix.
- *Architectural Patterns and Design* — Architectures A, B, C with diagrams; design principles; scalability; the isolation ladder with Proxmox's own guidance; data and operations architecture; qualitative trade-offs.
- *Implementation Approaches and Technology Adoption* — measured starting point; adoption path per architecture with the exact flags, open bugs and boot-persistence hooks; workflows, testing, operations, skills, cost; risk register; weighted scoring; recommendations (a) and (b); roadmap; KPIs.

## 10. Future Outlook

- **Near term (≤12 months):** Coder's Agents/AI-Gateway line hardens and the Community tier's agent cap becomes the pressure point for anyone who adopted Coder Tasks — Forge is unexposed. Tailscale ships network-map caching (offline resilience) and expands Services; multi-tailnet-under-one-org may reach GA, which would simplify the one-tailnet-per-company model. The Dev Containers lockfile graduates. Claude Code's managed-settings and sandbox surface keeps widening — the policy layer Forge should standardise on.
- **Medium term (1–3 years):** the IDE becomes optional for agentic teams (Gartner); the durable artefacts are the environment definition, the policy, and the identity model — all of which Architecture C already externalises. Expect microVM-class isolation to become table stakes for *untrusted* agent execution; on Proxmox that is a VM tier, and the design leaves room for it without touching the core.
- **Watch items:** Gartner's own forecast that a large share of agentic projects will be cancelled on cost/complexity — an argument for the lightest platform that meets the need; OpenAI's integration of Ona into Codex (a possible future "Codex cloud" competitor to workspace-resident agents); Proxmox OCI-LXC maturing out of tech preview.

## 11. Methodology and Source Verification

**Primary sources used** (representative; full URLs are inline in each section): coder.com/docs and pricing, github.com/coder/coder releases/issues/advisories, registry.terraform.io (coder, tailscale, proxmox), tailscale.com/kb + docs + blog (Serve, Services GA, multiple tailnets, pricing v4, tagged-key expiry, January 2026 postmortem), containers.dev spec and guides, code.visualstudio.com remote docs, code.claude.com / platform.claude.com docs (settings, sandboxing, env vars, monitoring, Agent SDK hosting), langfuse.com self-hosting and OTLP docs, github.com/mem0ai/mem0, pve.proxmox.com wiki (unprivileged LXC, nested virtualization, SDN, backup), pbs.proxmox.com maintenance docs, ona.com / support.gitpod.io, blog.jetbrains.com/codecanvas, okteto.com docs, eclipse.dev/che, e2b.dev / deepwiki infra docs, northflank.com docs, github.com/loft-sh/devpod, github.com/daytonaio/daytona, github.com/devcontainers/cli|features|ci, docs.sigstore.dev, github.com/pricing, Forbes/TechTimes/Dealroom (Ona acquisition), Gartner press release and market pages.

**Confidence framework.** H = primary source, dated, or measured locally; M = secondary or single primary, or inferred from documented behaviour; L = unverified this pass. Where sources conflicted (Daytona pivot date; Tailscale incident count; "sub-second" vs measured figures elsewhere in this programme) the primary or the measurement won and the conflict is noted in place.

**Limitations.** Coder Agents' GA label and MCP-server tier not explicitly stated; Coder devcontainer startup-script/hook ordering undocumented; no controlled benchmarks for nested-virt overhead, Terraform clone throughput, or B's time-to-first-workspace; OpenMemory auth-fix status unconfirmed; Tailscale Services per-plan limits single-sourced; small-self-hoster sentiment thin (issue trackers rather than forums); Gartner content paywalled beyond press level.

## 12. Appendices

**A. Decision table for a new customer**

| Customer shape | Profile | Components per company |
|---|---|---|
| 1–2 people, trusted | B | CT(s) + tailnet + roles; no Coder |
| Team wanting self-service/login/brokered tokens | A over the same core | + Coder Community instance + Postgres + Caddy (one per company) |
| Untrusted agent execution required | B/A + sandbox VM tier | + nested-virt VM (no live migration), microVM runtime |
| Compliance audit trail required | A + Premium, or B + git/Tailscale Standard audit | licence or process decision |

**B. Hygiene items valid under any decision** — Tailscale ≥1.98.9 fleet-wide (gateway image 1.96.5 → bump; `RunSSH:false` today); pin `@anthropic-ai/claude-code`/`@openai/codex`, `DISABLE_AUTOUPDATER=1`, stable channel; `CODER_OAUTH2_GITHUB_DEFAULT_PROVIDER_ENABLE` and `CODER_EXTERNAL_AUTH_GITHUB_DEFAULT_PROVIDER_ENABLE` explicit; remove `azuredevops` external auth; PBS `pg_dump` pre-backup hook + garbage-collection schedule; export tailnet ACL/split-DNS/Services to `homelab-infra/tailscale/`; move onboarding scripts into devcontainer hooks.

**C. Related artefacts in this programme** — `sprint-change-proposal-2026-09-09.md` (PoC scope), `adrs/ADR-001…006`, `_bmad-output/audit/forge-2026-09-10/` (audit plan, network review §1–13, G plan, fix-F evidence), `tests/acceptance.md` gates a–k.

---

## Technical Research Conclusion

**Summary.** The evaluation eliminated every hosted, Kubernetes-bound or abandoned alternative on facts and left two viable foundations. Between them, the decisive observation is that Forge's value sits in the workspace, that the workspace is now portable across both foundations via Dev Containers, and that Tailscale plus Claude Code's managed policy layer already supply most of what a control plane used to justify for a small trusted group.

**Strategic impact.** Choosing the portable core protects every future customer from vendor pivots of the kind seen this year, keeps the homelab's operating burden flat, and still lets a customer team have Coder's self-service where it earns its keep — without two divergent products.

**Next steps.** Phase 0 hygiene now; Phase 1 portable definition (one session) so FE4 runs on the devcontainer-based workspace; FE4 verdict with the framing above; Phase 3 converts one homelab CT to the control-plane-less pattern as the reference for customers who don't need Coder.

**Technical Research Completion Date:** 2026-09-21
**Research Period:** 2026-09-14 → 2026-09-21, live sources
**Source Verification:** every decision-bearing claim cited; single-sourced claims re-verified or marked
**Overall Confidence:** High on eliminations, licence boundaries, Tailscale/Proxmox/Claude Code mechanics; Medium on effort estimates and vendor trajectory beyond twelve months
