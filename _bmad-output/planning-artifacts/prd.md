---
stepsCompleted: ['step-01-init', 'step-02-discovery', 'step-03-success', 'step-04-journeys', 'step-05-domain', 'step-06-innovation', 'step-07-project-type']
inputDocuments:
  - "homelab-playbook/_bmad-output/planning-artifacts/product-brief-homelab-playbook-2026-02-05.md"
  - "homelab-playbook/management/README.md"
workflowType: 'prd'
briefCount: 1
researchCount: 0
brainstormingCount: 0
projectDocsCount: 1
classification:
  projectType: 'developer_tool'
  domain: 'process_control'
  complexity: 'medium-high'
  projectContext: 'brownfield'
---

# Product Requirements Document - homelab-playbook

**Author:** Larry
**Date:** 2026-02-05

## Success Criteria

### User Success

The primary user success moment is **the first `git revert` after a bad deploy** — the realization that infrastructure is recoverable and experimentation is safe.

**Measurable User Success Outcomes:**

- **First Recovery Victory:** Successfully execute `git revert` to recover from a bad configuration within 30 days of MVP deployment
- **End-to-End Workflow Velocity:** Deploy a new service from idea to production (Product Brief → PRD → Architecture → PR → Deploy) in less than 4 hours of focused work
- **Operational Confidence:** Zero "SSH panic fixes" after 60 days — all configuration changes flow through git-based workflows
- **Topology Awareness:** Operator can answer "What's running where?" in under 30 seconds using the playbook as single source of truth
- **Safe Evening Maintenance:** Execute routine maintenance or quick fixes at 10 PM without triggering 3 AM debugging sessions

### Business Success

homelab-playbook transforms weekend "tinkering" into productive infrastructure development with measurable ROI.

**Measurable Business Outcomes:**

- **Deployment Velocity:** Ship at least 1 new fully-integrated service per month during weekend planning sessions
- **Upgrade Confidence:** Complete infrastructure upgrades (Proxmox version bumps, core service updates) without data loss or more than 2 hours of downtime
- **Family Uptime SLA:** Maintain >99% monthly uptime for family-facing services (Plex, Home Assistant) — measured, not guessed
- **Knowledge Persistence:** Infrastructure state is fully documented in git repositories, eliminating "configuration archaeology" and upgrade paralysis

### Technical Success

Every service achieves production-grade integration with consistent Day 2 operational capabilities.

**Measurable Technical Outcomes:**

- **100% Day 2 Integration:** All deployed services include Traefik ingress routing, Authentik authentication, Prometheus monitoring, and Restic backup configuration
- **Zero Configuration Drift:** Live infrastructure state matches git repository state — no undocumented SSH fixes or zombie containers
- **PR-Based Changes:** 100% of infrastructure-as-code changes submitted as Pull Requests with agent-generated code and human review gates
- **Documented Architecture:** Every service deployment includes architecture decisions, integration requirements, and operational runbooks in version control

### Measurable Outcomes

**Success is achieved when:**

1. The operator experiences the "aha!" moment of recovering from failure via `git revert`
2. The homelab transitions from anxiety-inducing to confidence-building
3. "Doing it right" becomes easier than "doing it quick" due to AI-agent process automation
4. Upgrades and maintenance become routine operations instead of weekend-consuming projects
5. The playbook serves as the authoritative system topology and operational guide

## Product Scope

### MVP - Minimum Viable Product

**Core Workflow:** Prove the "Factory" methodology works end-to-end for a single service deployment.

**MVP Requirements:**

- **BMAD Planning Workflows:** Product Brief, PRD, and Architecture workflows functional from VS Code terminal
- **Agent-Generated IaC:** AI coder agent generates Ansible roles, Docker Compose files, and Traefik configurations as Pull Requests
- **Reviewer Mode:** Larry reviews agent-generated PRs in VS Code or web UI with ability to request changes
- **Full Day 2 Integration:** One reference deployment (ad-blocking service: Pi-hole or AdGuard Home) with complete Traefik ingress, Authentik SSO, Prometheus monitoring, and Restic backups
- **Topology Awareness:** Agent knows node inventory, service registry, and can answer "where is X running?"
- **Version Control Recovery:** Demonstrate successful `git revert` of a bad configuration

**MVP Success Gate:** Larry deploys one new service from scratch using BMAD workflows with full Day 2 integration, then successfully reverts a bad config change.

### Growth Features (Post-MVP)

**Enhanced Capabilities (3-6 months post-MVP):**

- **Operator Mode Enhancements:** Quick maintenance commands ("Check Paperless logs", "Restart Plex") without remembering IP addresses or paths
- **Multi-Service Orchestration:** Deploy complex stacks (e.g., full *arr media suite) as coordinated deployments
- **Automated Health Checks:** Proactive monitoring and alerting for configuration drift detection
- **Documentation Generation:** Auto-generated system diagrams, service dependency maps, and operational runbooks
- **Migration Tooling:** Migrate existing ad-hoc services into BMAD-managed state with minimal disruption

### Vision (Future)

**Long-Term Product Evolution:**

- **Community Playbooks:** Open-source repository of BMAD-validated service deployments shareable across homelabs
- **Homelab Marketplace:** Vetted, production-grade service blueprints with guaranteed Day 2 integration
- **Cross-Homelab Patterns:** Generalized BMAD workflows for common homelab infrastructure patterns (media server, automation hub, network security)
- **AI-Driven Optimization:** Agent analyzes resource utilization and recommends infrastructure optimizations
- **Disaster Recovery Automation:** Full infrastructure rebuild from git repositories with zero manual intervention

## User Journeys

### Journey 1: Larry the Planner - "Weekend Deep Dive"

**Opening Scene:**
It's Saturday morning. Larry's scrolling r/selfhosted and sees yet another post about network-wide ad blocking. He's been meaning to deploy Pi-hole for months, but the thought of configuring DNS, setting up Traefik ingress, wiring in Authentik SSO, adding Prometheus metrics, and configuring backups... it's a weekend project that could easily spiral into "why isn't my network working" on Monday morning.

**Rising Action:**
Larry opens VS Code terminal in the `homelab-playbook` repo and types: `bmad plan "Block ads network-wide"`

The agent interviews him inline:
- "Pi-hole or AdGuard Home?"
- "Which VLAN should it serve?"
- "SSO required or local auth acceptable?"
- "Backup frequency for blocklists?"

15 minutes of focused Q&A. The agent generates a Product Brief, then a PRD, then an Architecture document - all sitting in `_bmad-output/planning-artifacts/`. Larry reviews the architecture: Ansible role for VM provisioning, Docker Compose for Pi-hole, Traefik labels for ingress, Authentik provider config, Prometheus exporter enabled, Restic backup job.

**Climax:**
The agent generates the full IaC stack and opens a Pull Request. Larry reviews the YAML diffs in VS Code - clean, well-structured, follows his existing patterns. He leaves one comment: "Use DNS-over-HTTPS upstream instead of plain DNS." The agent updates the PR. Larry approves and merges.

**Resolution:**
90 minutes later, Pi-hole is live at `https://pihole.home.lab` with SSO login, metrics flowing to Grafana, and nightly backups configured. Larry updates his router's DNS settings. Ads vanish. Family doesn't notice (which is the point - uptime maintained). Larry commits a note to `memory/2026-02-05.md`: "Deployed Pi-hole using BMAD - first full Day 2 integration from scratch. This actually works."

**Journey Requirements:**
- Terminal-based BMAD workflow invocation
- Interactive inline Q&A for requirements gathering
- Artifact generation (Brief, PRD, Architecture) in planning-artifacts folder
- IaC code generation (Ansible, Docker Compose, Traefik, Authentik, Prometheus, Restic)
- PR-based review with iterative refinement
- Integration with existing homelab patterns and conventions

---

### Journey 2: Larry the Reviewer - "Code Review Flow"

**Opening Scene:**
Larry gets a Telegram notification: "Pull Request #47: Deploy Paperless-NGX - Ready for review." It's Tuesday evening. He's got 30 minutes before dinner.

**Rising Action:**
He opens the PR in VS Code. The agent has generated:
- Ansible playbook for VM creation on `node-02`
- Docker Compose stack with Paperless, Redis, PostgreSQL
- Traefik ingress config with SSL
- Authentik provider for SSO
- Prometheus metrics scraper
- Restic backup job for document storage

Larry scans the diffs. The Postgres credentials are hardcoded in the compose file. Not acceptable.

**Climax:**
Larry comments on the PR: "Move Postgres creds to Ansible vault. Also - what's the backup retention policy for documents?"

The agent responds inline: "Updated to use vault variables. Retention policy: 7 daily, 4 weekly, 12 monthly snapshots via Restic. Acceptable?"

Larry: "Perfect. Approved."

**Resolution:**
Merge. Deploy. 10 minutes later, Paperless is live at `https://paperless.home.lab`. Larry tests the SSO flow - works. Checks Grafana - metrics flowing. Scans a test document on his phone via the mobile upload URL. The system actually works as documented. He closes his laptop and heads to dinner, confident he didn't just create a 3 AM debugging session.

**Journey Requirements:**
- PR-based code review workflow (GitHub/Gitea compatible)
- Inline agent Q&A within PR comments
- Best practices validation (secrets management, backup policies)
- Iterative refinement based on review feedback
- Deployment confidence through documented integration

---

### Journey 3: Larry the Operator - "Evening Maintenance"

**Opening Scene:**
It's 10 PM. Larry's wife reports: "Plex isn't loading." Larry sighs. In the old days, this meant SSH into three different VMs, grep logs, check Docker status, restart containers, hope nothing else breaks.

**Rising Action:**
Larry opens a terminal: `bmad check plex`

The agent responds:
```
Plex Media Server
- Node: node-03
- Status: Container running, but healthcheck failing
- Logs: Database connection timeout to postgres-plex
- Related: postgres-plex container restarted 14m ago (OOM killed)
```

Larry: `bmad fix plex db memory`

**Climax:**
Agent: "Postgres container OOM - current limit 512MB. Recommend 2GB for media libraries >500 movies. Shall I generate PR to update compose memory limits?"

Larry: "Yes."

PR created. Larry reviews the single-line change: `mem_limit: 2g`. Approves. Deploys.

**Resolution:**
Plex is back online in 3 minutes. Wife texts: "Working now, thanks!" Larry updates the homelab topology notes with the memory lesson learned. No SSH sessions, no manual log grepping, no guessing which node hosts what. Back to his book by 10:15 PM.

**Journey Requirements:**
- CLI-based operational commands for troubleshooting
- Topology awareness (agent knows service locations, dependencies)
- Log aggregation and intelligent diagnostics
- Quick-fix PR generation for common issues
- Knowledge capture and documentation updates

---

### Journey 4: Family Member - "Just Works" Experience

**Opening Scene:**
Emma (Larry's daughter) wants to watch a movie. She opens Plex on her iPad.

**Rising Action:**
The app loads. Her profile auto-logs in (thanks to Authentik SSO shared session). The movie she was watching yesterday picks up right where she left off.

**Climax:**
The movie plays. Subtitles work. No buffering. The "just works" magic.

**Resolution:**
Emma watches her movie. She has no idea that behind the scenes, Plex is running with 99.8% uptime this month, automatic backups every night, and Larry can redeploy it from scratch in minutes if needed. She doesn't need to know. That's the point.

**Journey Requirements:**
- Transparent reliability - users don't notice infrastructure
- SSO integration for seamless auth across services
- High availability and uptime
- No user-facing maintenance windows

---

### Journey Requirements Summary

**From Planner Mode:**
- Terminal-invoked BMAD workflows (Brief, PRD, Architecture generation)
- Interactive requirements elicitation
- IaC artifact generation (Ansible, Docker, Traefik, Authentik, Prometheus, Restic)
- PR-based deployment

**From Reviewer Mode:**
- PR review UI integration (VS Code, web)
- Inline agent dialogue within PRs
- Best practices validation
- Iterative refinement workflows

**From Operator Mode:**
- Topology-aware CLI commands
- Service status and log aggregation
- Intelligent diagnostics and fix recommendations
- Quick-fix PR generation

**From Family Member Experience:**
- Transparent uptime and reliability
- SSO integration
- Zero user-facing maintenance impact

## Innovation & Novel Patterns

### Detected Innovation Areas

**"Factory vs App Store" Paradigm Shift**

homelab-playbook introduces a fundamentally different approach to homelab infrastructure management. Where existing tools (DockSTARTer, HomelabOS, Ansible-NAS) function as pre-packaged application catalogs - solving "what to deploy" - homelab-playbook is a structured *methodology* that solves "how to manage it." This reframes homelab operations from ad-hoc service deployment to a full product development lifecycle with requirements, architecture planning, code review, and version control.

**AI as Process Multiplier**

The core innovation is making enterprise-grade process discipline viable for single-operator homelabs by having AI agents absorb the "process tax." Traditional software engineering rigor (Product Briefs, PRDs, Architecture documents, PR-based reviews, documentation as first-class deliverables) is typically cost-prohibitive for personal infrastructure. By delegating the heavy lifting to AI agents - requirements elicitation, code generation, documentation writing - the structured path becomes *easier* than SSH-and-hack shortcuts. This inverts the usual tradeoff where "doing it right" requires more effort than "doing it quick."

**Three Operating Modes**

The product recognizes that infrastructure operators shift between three distinct mindsets:
- **Planner Mode:** Creative, exploratory sessions for new service ideation
- **Reviewer Mode:** Critical evaluation of agent-generated changes against best practices
- **Operator Mode:** Reactive troubleshooting with topology awareness acting as an intelligent system index

Each mode has tailored UX patterns (terminal-based workflows, PR reviews, CLI diagnostics) rather than forcing all operations through a single interface paradigm.

### Market Context & Competitive Landscape

**Existing Solutions:**
- **App Store Tools** (DockSTARTer, HomelabOS): Pre-packaged deployments, no process discipline
- **IaC Tools** (Terraform, Ansible, Docker Compose): Powerful execution layers, process-agnostic
- **Configuration Management** (Puppet, Chef, SaltStack): State management, not lifecycle management
- **AI Coding Assistants** (GitHub Copilot, Cursor): Code generation, not workflow orchestration

**homelab-playbook Differentiation:**
- Only solution treating homelab infrastructure as a *product with a lifecycle*
- Only tool combining AI agents + product management methodology + IaC tooling
- Only approach making "best practices" the default path through AI automation

**Unproven Market Assumption:**
The core bet is that single-operator homelabs will adopt enterprise-grade process discipline *if* AI removes the friction. This is untested - the homelab community may prefer flexible, ad-hoc approaches even when tooling improves.

### Validation Approach

**MVP Success Validation:**

The "aha!" moment - the first successful `git revert` of a bad configuration - is the validation gate. Success is proven when:

1. **Process Adoption:** Larry completes one full BMAD workflow (Brief → PRD → Architecture → PR → Deploy) in under 4 hours
2. **Code Quality:** Agent-generated IaC passes Larry's review standards (secrets in vault, backup policies defined, Day 2 integration complete)
3. **Recovery Confidence:** A bad configuration is successfully reverted via git, demonstrating that version control actually prevents permanent breakage
4. **Friction Test:** The structured workflow is subjectively *easier* than the old SSH-and-hack approach

**Validation Metrics:**
- Time to first deployment: <4 hours focused work
- Agent-generated code quality: PR approval rate >80% on first submission
- Configuration drift: Zero SSH fixes after 60 days
- Operator confidence: Subjective assessment - does infrastructure feel less fragile?

### Risk Mitigation

**Innovation Risk 1: AI Agent Code Quality**

*Risk:* Agent-generated IaC is low-quality, buggy, or insecure, requiring extensive human rework and defeating the "easier than ad-hoc" promise.

*Mitigation:*
- PR-based review gate ensures human validation before deployment
- Start with reference implementations (Pi-hole, Paperless) to establish quality baseline
- Agent learns from feedback - iterative refinement within PR workflow
- Fallback: Larry writes IaC manually if agent quality doesn't meet standards

**Innovation Risk 2: Process Adoption Failure**

*Risk:* The BMAD workflow feels like bureaucratic overhead despite AI assistance - Larry reverts to SSH fixes because "it's faster."

*Mitigation:*
- Optimize for terminal-first workflow - no web UI context switching
- Keep agent interactions conversational and inline (no form-filling)
- Measure time-to-deploy and compare against old ad-hoc approach
- Allow "escape hatches" for true emergencies while tracking SSH fix frequency

**Innovation Risk 3: Homelab Community Rejects Process Discipline**

*Risk:* The homelab ethos values experimentation and flexibility - structured process feels antithetical to the "tinker and learn" culture.

*Mitigation:*
- Optimize for Larry's single-player workflow first, not community adoption
- Document the "why" - show concrete benefits (confidence, recovery, uptime) not just process
- Future community adoption is post-MVP - prove it works for one person before scaling
- Open-source the methodology for others to adapt, not prescribe

## Developer Tool Technical Requirements

### Architecture Overview

homelab-playbook is an **orchestration layer** that coordinates BMAD methodology with AI agents to generate infrastructure-as-code for existing homelab repositories. It does NOT replace existing infrastructure - it enhances the development workflow.

**Component Roles:**

1. **OpenClaw (Supervisor)** - Coordinates BMAD planning workflows (Product Brief, PRD, Architecture, Stories)
2. **Claude Code CLI (Coder)** - Executes implementation stories, generates IaC following BMAD context
3. **homelab-infra** - Existing Terraform + Ansible for VM/CT provisioning (target repo)
4. **homelab-apps** - Existing Docker Compose stacks via Portainer GitOps (target repo)
5. **homelab-playbook** - Coordination hub (planning artifacts, pattern library, topology registry)

**Development Workflow Transformation:**

**Before:**
- Larry manually writes Terraform/Ansible/Docker Compose in VS Code
- Manual commits → GitOps (Portainer webhooks, Ansible playbooks)

**After:**
- OpenClaw runs BMAD planning → generates Brief, PRD, Architecture, Stories in `homelab-playbook/_bmad-output/`
- OpenClaw spawns Claude Code CLI with story context
- Claude Code CLI generates IaC in target repo (`homelab-infra` or `homelab-apps`)
- Claude Code CLI creates branch + commits → opens Pull Request
- Larry reviews PR in VS Code or web UI
- Merge → existing GitOps unchanged (Portainer webhooks, Ansible playbooks)

### Technical Architecture Requirements

#### 1. BMAD Workflow Orchestration

**Requirements:**
- OpenClaw must execute BMAD workflows from terminal invocation (terminal-first UX)
- Planning artifacts stored in `homelab-playbook/_bmad-output/planning-artifacts/`
- Stories stored in `homelab-playbook/_bmad-output/implementation-artifacts/`
- Workflow state tracked in artifact frontmatter (`stepsCompleted` arrays)
- Agent maintains session continuity across multi-step workflows

**Outputs:**
- Product Brief (markdown, validates problem/solution fit)
- PRD (markdown, defines requirements/personas/success criteria)
- Architecture (markdown, technical decisions and integration patterns)
- Stories (markdown, actionable implementation specs for Claude Code CLI)

#### 2. Claude Code CLI Integration

**Context Passing:**
Claude Code CLI must receive sufficient context to generate code that matches existing patterns:

- **Story Specification** - Implementation requirements from BMAD story file
- **Architecture Decisions** - Technical patterns from Architecture document
- **Existing Code Examples** - Reference stacks from `homelab-apps/stacks/` or Ansible roles from `homelab-infra/ansible/roles/`
- **Pattern Library** - Conventions document (Traefik labels, network setup, volume mounts, `.env` structure)
- **Topology Registry** - Node inventory (which VMs/CTs exist, IPs, capabilities)

**Spawn Mechanism:**
- OpenClaw spawns Claude Code CLI as background session via `sessions_spawn`
- Pass story file path + architecture context + example code
- Claude Code CLI runs in target repo directory (`homelab-infra/` or `homelab-apps/`)
- Session runs until story complete or human intervention needed

**Output:**
- Git branch with IaC changes (Terraform modules, Ansible playbooks, or Docker Compose stacks)
- Commit messages following conventional commit format
- Pull Request with description linking back to BMAD story

#### 3. Pattern Library & Convention Documentation

Claude Code CLI must generate code matching existing homelab patterns. Document conventions:

**homelab-apps Stack Conventions:**
- **Compose v2 syntax** with pinned image tags (no `latest`)
- **Traefik v3 labels** for HTTP routing:
  - `traefik.enable=true`
  - HTTP→HTTPS redirect router + secure HTTPS router
  - Service port definition
  - `traefik.docker.network=proxy`
- **External `proxy` network** - no host port publishing unless required (DNS, VPN)
- **Bind mounts** to `/opt/appdata/<stack>/<service>` for persistent data
- **Environment variables** via `.env` files (`.env.sample` committed to git)
- **Healthchecks** for all long-running services
- **Standard env vars:** `TZ=Europe/Brussels`, `PUID=1000`, `PGID=1000`

**homelab-infra Ansible Conventions:**
- Roles in `ansible/roles/<role-name>/main.yml`
- Playbooks in `ansible/<purpose>.yml`
- Inventory in `ansible/inventory.yml`
- Variables in playbook or role defaults

**homelab-infra Terraform Conventions:**
- Modules in `terraform/modules/<resource-type>/`
- Environment-specific configs in `terraform/envs/homelab/`
- Proxmox provider for VM/CT creation

**Day 2 Integration Requirements (all new services):**
- Traefik ingress with Let's Encrypt TLS
- Authentik SSO integration (when applicable)
- Prometheus metrics scraping (when exporter available)
- Restic backup configuration (for data directories)

#### 4. Repository Coordination

**Repository Routing Logic:**

Determine target repository based on deployment type:

- **homelab-infra** changes:
  - New VM or LXC container provisioning (Terraform module)
  - Host-level configuration (Ansible role/playbook)
  - Network or storage infrastructure
  
- **homelab-apps** changes:
  - New Docker Compose stack in `stacks/<stack-name>/`
  - Modifications to existing stack
  - Stack deployment target mapping in `stack-targets.yml`

**Multi-Repo Coordination:**

Some deployments span both repos (e.g., provision VM in infra + deploy app stack):
- Generate changes in both repos as separate PRs
- PRs cross-reference each other
- Deployment order documented (infra first, then apps)

#### 5. Pull Request Validation Rules

Larry's PR review checklist (can be partially automated):

**Code Quality:**
- No hardcoded secrets (must use `.env` or Ansible vault)
- Pinned image tags (no `latest` tags)
- Healthchecks defined
- Traefik labels follow conventions
- External networks declared properly

**Day 2 Integration:**
- Traefik ingress configured
- Backup policy defined (Restic config or manual backup strategy)
- Monitoring configured (Prometheus scraper or healthcheck)
- SSO integration (Authentik provider if user-facing service)

**Documentation:**
- README or inline comments explain non-obvious config
- `.env.sample` created with all required variables
- Stack deployment target documented in `stack-targets.yml`

**Testing Strategy:**
- Claude Code CLI validates Docker Compose syntax before PR
- Ansible playbook syntax check via `ansible-playbook --syntax-check`
- Terraform plan output included in PR description

#### 6. GitOps Integration (Unchanged)

homelab-playbook does NOT modify existing deployment automation:

**homelab-apps GitOps (Portainer):**
- Merge to `main` triggers Portainer webhooks
- Changed stacks redeploy automatically
- Portainer GUI shows deployment status

**homelab-infra Execution:**
- Terraform apply runs from dev-vm (manual or GitHub Actions)
- Ansible playbooks run from dev-vm via `ansible-playbook`
- VM/CT creation visible in Proxmox GUI

**homelab-playbook role:** Generate correct code, submit PR, let existing automation handle deployment.

### Topology Registry

Agent must know infrastructure state to make intelligent decisions:

**Node Inventory:**
```yaml
nodes:
  - id: ct-docker-01
    type: lxc
    ip: 192.168.50.101
    purpose: Docker host (general apps)
    capabilities: [docker, traefik, portainer]
  
  - id: ct-media-01
    type: lxc
    ip: 192.168.50.102
    purpose: Media server
    capabilities: [docker, igpu-passthrough, plex]
  
  - id: dev-vm
    type: vm
    ip: 192.168.50.115
    purpose: Development workstation
    capabilities: [terraform, ansible, vscode-remote]
```

**Service Registry:**
```yaml
services:
  - name: traefik
    node: ct-docker-01
    stack: infra-core
    ingress: traefik.homelab.local
  
  - name: plex
    node: ct-media-01
    stack: media-plex
    ingress: plex.homelab.local
```

**Usage:**
- Operator Mode: "Check Plex logs" → knows to SSH to ct-media-01
- Planner Mode: "Deploy Pi-hole" → suggests ct-docker-01 as target
- Reviewer Mode: Validates deployment target matches service type

### Installation & Setup

**Prerequisites:**
- Git repositories cloned: `homelab-infra`, `homelab-apps`, `homelab-playbook`
- OpenClaw installed and configured
- Claude Code CLI installed and API key configured
- SSH access to dev-vm (192.168.50.115)
- VS Code with Remote SSH extension

**Initial Setup:**
1. Clone `homelab-playbook` repository
2. Initialize BMAD submodule (if using submodule, or workflows already embedded in `_bmad/`)
3. Configure topology registry (`topology/nodes.yml`, `topology/services.yml`)
4. Configure pattern library (`patterns/docker-compose-conventions.md`, `patterns/ansible-conventions.md`)
5. Test OpenClaw coordination: run `/product-brief` workflow
6. Test Claude Code CLI spawn: implement sample story

**Configuration Files:**
- `homelab-playbook/config.yml` - Agent settings, API keys, repository paths
- `homelab-playbook/topology/` - Node and service registry
- `homelab-playbook/patterns/` - Convention documentation for Claude Code CLI

### Documentation Requirements

**User-Facing Documentation:**
- **Quickstart Guide** - Deploy first service using BMAD workflow (Pi-hole walkthrough)
- **Workflow Guide** - How to invoke BMAD commands, interpret output, review PRs
- **Troubleshooting Guide** - Common failures (agent generates bad code, PR conflicts, GitOps issues)

**Developer Documentation:**
- **Pattern Library** - Traefik conventions, Ansible best practices, Docker Compose structure
- **Architecture Decision Records** - Why certain patterns were chosen
- **Story Templates** - Examples of well-formed stories for Claude Code CLI

**Reference Documentation:**
- **Topology Registry** - Current infrastructure state, node capabilities
- **Service Catalog** - Deployed services, ingress URLs, backup policies
- **Example Deployments** - Pi-hole, Paperless, full media stack walkthroughs
