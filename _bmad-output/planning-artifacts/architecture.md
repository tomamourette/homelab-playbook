---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
lastStep: 8
status: 'complete'
completedAt: '2026-04-03'
lastEdited: '2026-04-11'
editHistory:
  - date: '2026-04-11'
    changes: 'Phase 2b Knowledge Management: added 6 stack entries (LLM Wiki, MemPalace, Obsidian, Linear/Granola/Azure DevOps MCP), 4 cross-cutting concerns (multi-vault sync, query hierarchy, shared user model, MCP fan-out), moved information source integrations from deferred to planned, added Phase 2b planned decisions. Per SCP-knowledge-mgmt-2026-04-11.'
  - date: '2026-04-03'
    changes: 'Added BMAD Workflow Enhancements scope: doc update skill architecture, eval assertions, autoresearch integration, Claude Code skill patterns'
inputDocuments:
  - homelab-playbook/_bmad-output/planning-artifacts/prd.md
  - homelab-playbook/_bmad-output/planning-artifacts/product-brief-ai-dev-container.md
  - homelab-playbook/_bmad-output/planning-artifacts/product-brief-ai-dev-container-distillate.md
  - homelab-playbook/_bmad-output/planning-artifacts/research/technical-ephemeral-cloud-containers-research-2026-03-31.md
  - docs/index.md
  - docs/project-overview.md
  - docs/architecture-homelab-infra.md
  - docs/architecture-homelab-playbook.md
  - docs/integration-architecture.md
workflowType: 'architecture'
project_name: 'homelab'
user_name: 'tomamourette'
date: '2026-04-02'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**

42 functional requirements across 7 capability domains:

| Domain | FRs | Architectural Impact |
|--------|-----|---------------------|
| Session Persistence (FR1-FR5) | 5 | claude-tmux Rust binary build + tmux config, auto-start on boot, keybinding registration |
| Persistent Memory (FR6-FR15) | 10 | OMEGA Memory pip install, MCP server lifecycle, Claude Code hook registration, SQLite backup cron, namespace isolation enforcement |
| Agent Orchestration (FR16-FR22) | 7 | Hermes Agent installer, config.yaml + SOUL.md + .env, MCP connection to OMEGA, BMAD skill stubs, cron scheduling |
| Integration (FR23-FR26) | 4 | MCP bridge between Hermes and OMEGA, Claude Code hook pipeline for worker capture, multi-session memory sharing |
| Provisioning & Reproducibility (FR27-FR32) | 6 | Single playbook composing dev-host + 3 new ai-dev-* roles, parameterized per project, each role independently testable |
| Operational Guardrails (FR33-FR39) | 7 | Worker process limits, namespace query isolation, secret filtering in hooks, git push safety, Ansible-only package management |
| Anthropic Subscription (FR40-FR42) | 3 | Max Plan authentication validation, programmatic Claude Code spawning, rate limit documentation |
| BMAD Workflow Enhancements (FR43-FR52) | 10 | New Claude Code skill `bmad-update-project-docs` (3 modes), configurable file-to-doc mapping, state tracking, eval assertions in story templates, autoresearch skill installation |

**Non-Functional Requirements:**

| Category | Key Constraints |
|----------|----------------|
| Reliability | tmux survives reboots (60s recovery), SQLite WAL mode, roles recover from partial failure, <=24h backup RPO, independent tool degradation |
| Security | Ansible vault for all secrets, OMEGA filters sensitive file content, namespace isolation at query layer, .env/DB excluded from git, workers restricted to feature branches |
| Performance | OMEGA search <2s for 5K memories, SessionStart hook <5s, full stack RAM <2GB on 8GB container, playbook execution <15min |
| Integration | Stable MCP interface (no version coupling), standard Claude Code hook location, pinned tool versions with compatibility matrix, Max Plan compatibility, BMAD update-safety (no modifications to bmad-* skills), skill independence (doc update works on any BMAD project) |

**Scale & Complexity:**

- Primary domain: Developer infrastructure — IaC provisioning + AI agent orchestration
- Complexity level: Medium — 5 independent upstream tools with MCP integration, multiple runtimes, single-user, single-container
- Estimated architectural components: 3 new Ansible roles (`ai-dev-tmux`, `ai-dev-omega-memory`, `ai-dev-hermes`), 1 new playbook, Claude Code hook configs, MCP server configs, systemd units for auto-start and backup, 1 new Claude Code skill (`bmad-update-project-docs`), story template modification, autoresearch skill installation

### Technical Constraints & Dependencies

| Constraint | Source | Impact |
|-----------|--------|--------|
| Existing `dev-host` role as baseline | homelab-infra conventions | All ai-dev-* roles declare dependency on dev-host; Python 3.11+ via pyenv, Node.js, tmux, git, Claude Code already available |
| Python 3.11+ required by Hermes | Hermes Agent upstream | pyenv (from dev-host) must provide 3.11+; ai-dev-hermes role validates version before install |
| Rust/Cargo required for claude-tmux | claude-tmux upstream | Build from source (~2-5 min); role should cache compiled binary for idempotency |
| OMEGA Memory ~337MB RAM at runtime | OMEGA sizing | Combined with Hermes (~100MB) + system, must stay under 2GB total for AI stack on 8GB container |
| 90MB ONNX embedding model download | OMEGA setup | One-time download; role must handle offline/retry scenarios |
| Hermes 90 max turns per session | Hermes hard limit | Architectural constraint on autonomous task length; subagent spawning + /compress as workarounds |
| Hermes 2,200 char MEMORY.md limit | Hermes hard limit | Director memory is constrained; OMEGA serves as the real persistent memory layer |
| No new Terraform module (MVP) | PRD scoping | Uses existing ct-dev-homelab (VMID 150, pve2, 2C/8GB); dedicated ct-ai-dev module deferred to Phase 2 |
| Anthropic Max Plan subscription | User constraint | Must validate programmatic API usage, Claude Code CLI spawning, rate limits — blocking validation |
| N5 Pro as pve3 (Epic 8) | Hardware acquisition | Third cluster node (192.168.50.203), 12C/24T, up to 96GB DDR5 ECC, 10GbE, OCULink for RX 9070 XT GPU. Independent of AI Dev Container epics. |
| `.env` + vault pattern | homelab-infra conventions | ANTHROPIC_API_KEY and OMEGA config via Ansible vault, never plaintext |

### Cross-Cutting Concerns Identified

| Concern | Affected Components | Architectural Approach Needed |
|---------|-------------------|-------------------------------|
| Python version management | OMEGA (3.9+), Hermes (3.11+) | pyenv from dev-host provides 3.11+; all ai-dev-* roles use pyenv-managed Python, not system Python |
| Secret management | Hermes .env (API key), OMEGA config, Claude Code hooks | Ansible vault for all secrets; roles template .env files from vault vars; .gitignore enforced |
| MCP server lifecycle | OMEGA MCP server, Hermes MCP client connection | OMEGA MCP must auto-start (systemd or tmux); Hermes config references OMEGA MCP endpoint; health check validates connection |
| Tool version pinning | OMEGA, Hermes, claude-tmux, ONNX model | Pin exact versions in Ansible role defaults; compatibility matrix documented; upgrades require explicit testing |
| Resource budgeting | OMEGA (337MB), Hermes (100MB), tmux, claude-tmux | Total AI stack must stay <2GB RAM; Prometheus monitoring of container resources recommended |
| Namespace isolation | OMEGA namespaces, Claude Code hooks, Hermes config | Single variable (project name) drives namespace across all tools; Ansible parameterizes consistently |
| Upstream dependency risk | Hermes, OMEGA, claude-tmux are community projects | Version pin, design for component swappability, cache build artifacts |
| Auto-start on boot | tmux server, OMEGA MCP server | systemd units for automatic recovery after container reboot |
| BMAD update-safety | Doc update skill, eval assertions, autoresearch | All enhancements must be standalone skills or user-controlled templates — zero modifications to `.claude/skills/bmad-*/` files |
| Multi-vault sync | Obsidian, git, Hermes cron | One git repo per vault, container auto-pushes wiki changes every 5 min, laptop Obsidian Git plugin auto-pulls |
| Query hierarchy | LLM Wiki, MemPalace, OMEGA | Wiki (fast, pre-synthesized) → MemPalace (deep, raw verbatim) → OMEGA (cross-project memory) |
| Shared user model | Hermes instances across containers | Honcho memory provider (cloud, shared workspace) or OMEGA profile (self-hosted alternative) |
| MCP client fan-out | Hermes connecting to 4+ MCP servers | Per-container config.yaml with conditional wiring — only enable MCPs relevant to the project |

## Starter Template Evaluation

### Primary Technology Domain

Infrastructure/DevOps — IaC provisioning + AI agent orchestration. This is a brownfield project extending an operational platform, not a greenfield application.

### Starter Template Decision: Not Applicable

**Rationale:** This project adds capabilities to an existing, fully operational infrastructure stack. The "starter" is the existing codebase across three repositories:

- **homelab-infra** — Terraform modules, Ansible roles (including `dev-host` as the baseline), deployment scripts
- **homelab-apps** — Docker Compose stacks (not directly modified by this project)
- **homelab-playbook** — BMAD orchestration and planning artifacts

New capabilities (claude-tmux, OMEGA Memory, Hermes Agent) will be implemented as new Ansible roles following existing `dev-host` role patterns, not generated from any starter template.

### Established Technical Stack

| Layer | Technology | Version | Convention |
|-------|-----------|---------|------------|
| Provisioning | Terraform | >= 1.6 | Module-based, telmate/proxmox provider |
| Config Management | Ansible | >= 2.15 | Role-based, Jinja2 templates, vault-encrypted secrets |
| Container Host | Proxmox LXC | Debian 12/13 | ct-debian module, 2C/8GB for dev containers |
| Python | pyenv-managed | 3.11+ | Installed by dev-host role, used by OMEGA + Hermes |
| Node.js | nvm-managed | 20 LTS | Installed by dev-host role, used by Hermes |
| Rust | Cargo | Latest | Required for claude-tmux build from source |
| AI Agent | Claude Code CLI | Latest | Installed by dev-host role |
| Memory | OMEGA Memory | Pinned | SQLite + MCP server |
| Orchestrator | Hermes Agent | Pinned | Python-based, MCP client |
| Monitoring TUI | claude-tmux | Pinned | Rust binary |
| Secrets | Ansible vault | N/A | All credentials encrypted, `.env` templated |
| Knowledge Wiki | LLM Wiki (markdown) | N/A (pattern) | Per-container Obsidian vault, git-synced, Hermes-maintained |
| Deep Memory | MemPalace | Pinned | ChromaDB + SQLite KG, MCP server (19 tools) |
| Knowledge Viewer | Obsidian | Latest | Per-project vault on laptop, Obsidian Git plugin auto-pull |
| Ticket Management | Linear MCP | Official (remote) | Hermes MCP client, cron polling every 5 min |
| Meeting Notes | Granola MCP | Native | Hermes MCP client, cron polling every 30 min |
| Work Items | Azure DevOps MCP | Microsoft official | Conditional per project, Hermes MCP client |

### Ansible Role Convention (from existing dev-host)

New roles follow the established pattern:

```
roles/
  {role-name}/
    tasks/main.yml        # Required: task definitions
    handlers/main.yml     # Required if services need restart triggers
    templates/*.j2        # Jinja2 templates for dynamic config
    defaults/main.yml     # Default variables (overridable)
    files/                # Static files (scripts, configs)
    meta/main.yml         # Role dependencies (declares dev-host)
```

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
- Role independence model — each ai-dev-* role works standalone with conditional integration wiring
- OMEGA MCP server lifecycle — must be always-available for both Hermes and Claude Code
- Python environment strategy — how upstream tools manage their own runtimes

**Important Decisions (Shape Architecture):**
- Auto-start strategy for boot recovery
- Claude Code hook registration method
- claude-tmux build caching
- Acceptance test structure

**Planned Decisions (Phase 2b — Knowledge Management):**
- LLM Wiki directory structure and SCHEMA.md convention per project
- MemPalace palace wing taxonomy (rooms, halls per project type)
- Obsidian multi-vault strategy: separate vaults + laptop meta-vault with URI links
- Cross-project OMEGA instance as shared MCP endpoint across containers
- Linear/Granola/Azure DevOps MCP polling intervals and classification routing
- Query hierarchy implementation: wiki → MemPalace → OMEGA fallback chain

**Deferred Decisions (Post-MVP):**
- Dedicated `ct-ai-dev` Terraform module (Phase 2a)
- DBOS crash recovery integration (Phase 2a)
- GEPA skill optimization scheduling (Phase 2a)
- MemPalace federation across containers (if needed beyond per-container instances)

### Python Environment Strategy

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Python management | Let each tool manage its own | Hermes has its own installer that handles Python 3.11 + Node.js; OMEGA uses pip install with pyenv Python. Forcing shared/separate venvs adds complexity the upstream tools don't expect |
| pyenv as foundation | pyenv from dev-host provides 3.11+ | Both tools use pyenv-managed Python, not system Python. dev-host already installs pyenv |
| Dependency isolation | Upstream tools handle it | Hermes installer creates its own environment; OMEGA pip install uses pyenv global. No Ansible-managed venvs |

**Cascading:** Ansible roles don't create or manage Python virtual environments. They ensure pyenv has 3.11+ available, then invoke upstream install commands.

### OMEGA MCP Server Lifecycle

| Decision | Choice | Rationale |
|----------|--------|-----------|
| MCP server process | systemd user service | Auto-starts on boot, standard lifecycle management, journald logging. Always-available for both Hermes and Claude Code |
| Service name | `omega-mcp.service` | Consistent with systemd naming conventions |
| Auto-start | `systemctl --user enable omega-mcp.service` | Survives reboots without cron or tmux dependency |
| Health check | `omega doctor` in verify tasks | Validates MCP server is running and responsive |

**Cascading:** Hermes and Claude Code both expect OMEGA MCP to be reachable. systemd ensures it's running before either consumer starts. If OMEGA is not installed, consumers degrade gracefully — Hermes runs without memory, Claude Code sessions skip hooks.

### Auto-Start Strategy (Boot Recovery)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| tmux server | systemd user service | `tmux-server.service` — starts tmux server on boot, all named sessions recoverable |
| OMEGA MCP | systemd user service | `omega-mcp.service` — After tmux-server (ordering, not hard dependency) |
| Hermes Agent | Not auto-started | User starts Director sessions on demand in tmux. Hermes is interactive, not a daemon |
| claude-tmux | Not auto-started | TUI launched on demand via tmux keybinding (Ctrl-C) |
| Dependency ordering | `omega-mcp.service` After `network.target` | MCP server needs network; no hard dependency on tmux |

**Cascading:** Two systemd user units total. Both managed by `ai-dev-tmux` (tmux-server) and `ai-dev-omega-memory` (omega-mcp) roles respectively.

### Claude Code Hook Registration

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Hook registration | OMEGA's own setup command (`omega setup`), falling back to surgical JSON merge | Prefer upstream tooling; if `omega setup` handles hook registration, let it. If not, Ansible uses jq/Python to merge hook entries into existing settings |
| Settings location | `~/.claude/settings.json` (standard) | NFR-INT-2: standard Claude Code settings location, no custom hook loaders |
| Idempotency | Check before merge | Role verifies hooks are already registered before modifying settings file |
| User customizations | Preserved | Never overwrite the full settings file — only add/update OMEGA-specific hook entries |

**Cascading:** The `ai-dev-omega-memory` role handles this. If Claude Code settings don't exist yet, the role creates a minimal settings file with just the hooks.

### claude-tmux Build Strategy

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Build method | `cargo install claude-tmux` | Standard Rust package installation |
| Binary caching | Version-check for idempotency | Role checks if `~/.cargo/bin/claude-tmux` exists and matches pinned version. Skips build if current |
| Build dependencies | build-essential from dev-host | Rust compilation needs gcc/make, already provided by baseline role |
| Cargo installation | Role installs Rust/Cargo if missing | `rustup` installer, cached in `~/.cargo/` |
| Keybinding | `bind-key C-c display-popup` in `.tmux.conf` | tmux keybinding for TUI launch, configured by ai-dev-tmux role |

**Cascading:** First run takes ~2-5 min for Rust compilation. Subsequent role runs skip if binary version matches. Cargo itself is a one-time install.

### Role Independence & Conditional Integration

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Role dependencies | All ai-dev-* roles depend only on dev-host | No hard dependencies between ai-dev-* roles. Supports FR29 (independently testable) and NFR-REL-5 (independent degradation) |
| Integration wiring | Conditional — detect and configure | Each role checks if other tools are present and wires integration if found |
| Playbook order | Preference, not requirement | `dev-host → ai-dev-tmux → ai-dev-omega-memory → ai-dev-hermes` for logical flow, but any order converges to same state |
| Idempotent convergence | Running playbook twice = same result | Second run detects existing tools and wires any missing integrations |

**Conditional Integration Logic:**

| Role | Checks For | If Found | If Not Found |
|------|-----------|----------|--------------|
| ai-dev-hermes | OMEGA MCP (`omega` binary or systemd unit) | Adds OMEGA MCP server entry to Hermes `config.yaml` | Skips MCP config — Hermes works standalone |
| ai-dev-omega-memory | Hermes config (`~/.hermes/config.yaml`) | Adds/updates OMEGA MCP entry in Hermes config | Skips — Hermes not installed yet |
| ai-dev-omega-memory | Claude Code settings (`~/.claude/settings.json`) | Merges hook entries | Creates minimal settings file with hooks |

**Cascading:** Any install order works. The last role to install wires the integration. Running the full playbook always converges to fully-wired state.

### Acceptance Test Structure

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Test approach | Both: Ansible verify.yml + comprehensive test script | Quick verify tasks in each role for CI; full test script for acceptance validation |
| Ansible verify | `verify.yml` per role, run via `--tags verify` | Tests service health during/after provisioning: binary exists, service running, config valid |
| Test script | `tests/test-ai-dev-stack.sh` in homelab-infra | Comprehensive script covering AT-1 through AT-N5 (43 tests). Run manually or in CI |
| Test independence | Each role's verify.yml is self-contained | Can verify one role without the others being installed |
| Integration tests | Only in the comprehensive test script | AT-4 (integration smoke tests) require multiple services — not suitable for per-role verify |

**Cascading:** Ansible verify tasks run as part of the playbook (fast, basic health). The comprehensive test script is a separate manual step for full acceptance validation.

### Decision Impact Analysis

**Implementation Sequence:**
```
1. ai-dev-tmux          → tmux server + claude-tmux TUI (immediate value: session persistence)
2. ai-dev-omega-memory  → OMEGA + MCP server + Claude Code hooks (core: persistent memory)
   └── IF Hermes detected → wire MCP connection
3. ai-dev-hermes        → Hermes Agent + BMAD skills + cron
   └── IF OMEGA detected → wire MCP connection
4. Playbook             → Composes all three, converges integrations
5. Verification         → Per-role verify + comprehensive test script
```

**Cross-Component Dependencies:**
```
OMEGA MCP Server ←── Claude Code hooks (SessionStart briefing, SessionStop capture)
                 ←── Hermes Director (MCP client, queries/stores memory)

pyenv (dev-host) ←── OMEGA pip install (Python 3.9+)
                 ←── Hermes installer (Python 3.11+)

tmux (dev-host)  ←── claude-tmux TUI (keybinding)
                 ←── Hermes Director sessions (runs in tmux)
                 ←── Claude Code worker sessions (run in tmux)

systemd          ←── tmux-server.service (boot recovery)
                 ←── omega-mcp.service (always-on MCP)

Ansible vault    ←── Hermes .env (ANTHROPIC_API_KEY)
                 ←── OMEGA config (if API key needed)
```

### BMAD Workflow Enhancement Decisions

#### Incremental Documentation Skill

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Skill type | Standalone Claude Code skill | BMAD-update-safe — no modifications to built-in bmad-* skills |
| Skill name | `bmad-update-project-docs` | Follows bmad- prefix convention but lives in its own directory |
| Operating modes | update (default), check (read-only), full (delegates) | update for incremental changes, check for health reports, full delegates to existing bmad-document-project |
| Change detection | Git-diff based (`git log --since`) | Zero infrastructure — uses git primitives, no MCP server needed |
| Update granularity | Section-level within doc files | Preserves unchanged sections, only regenerates affected H2/H3 sections |
| File-to-doc mapping | Configurable YAML in `references/doc-section-mapping.md` | Adaptable across projects, not hardcoded |
| State tracking | Extends existing `project-scan-report.json` | Adds `git_ref_at_last_update`, `last_incremental_update`, per-section timestamps |
| User confirmation | Required before writing | Presents change plan, user confirms before any doc modifications |

**Cascading:** The doc update skill shares the `docs/` output folder and state file with `bmad-document-project`. The `full` mode delegates to the existing skill, not duplicates it.

#### Eval Assertions in Story Templates

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Implementation | Section in user-controlled story template | BMAD-update-safe — template is in `_bmad-output/`, not in skill code |
| Format | Binary test assertions derived from acceptance criteria | Autoresearch pattern requires scalar metrics; binary pass/fail is the clearest signal |
| Scope | Per-story, not per-epic | Each story gets its own eval assertions matching its acceptance criteria |
| Integration | No BMAD skill modification needed | `bmad-create-story` reads the template and fills in sections including eval assertions |

**Cascading:** Eval assertions become the metric for `/autoresearch:fix` loops. They also serve as verification criteria for `/bmad-code-review`.

#### Autoresearch Skill Installation

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Skill source | uditgoenka/autoresearch (or equivalent) | Proven Claude Code autoresearch implementation with 8-phase loop |
| Installation | Separately installed Claude Code skill | Independent of BMAD — no coupling or dependency |
| Primary command | `/autoresearch:fix` | Post-code-review iteration loop: modify → verify → keep/revert → repeat |
| Metric source | Eval assertions from story template | Binary test criteria provide the scalar metric for the autoresearch loop |
| Scope | Per-story, triggered manually after code review | Not automated — user decides when to run the fix loop |

**Cascading:** Autoresearch needs eval assertions to function. Story template change must happen before autoresearch is useful.

#### BMAD Update-Safety Constraint

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Constraint | Zero modifications to `.claude/skills/bmad-*/` | BMAD updates overwrite these files — any custom changes are lost |
| New skills | Standalone directories in `.claude/skills/` | `bmad-update-project-docs/` is separate from `bmad-document-project/` |
| Template changes | User-controlled files in `_bmad-output/` | Story templates are project artifacts, not BMAD skill code |
| Third-party skills | Separately installed | Autoresearch skill has no dependency on BMAD installation |

## Implementation Patterns & Consistency Rules

### Critical Conflict Points Identified

8 areas where AI agents implementing different roles could make different choices, resolved below.

### Ansible Task Patterns

**All AI agents MUST follow these conventions for new roles:**

| Pattern | Rule | Example |
|---------|------|---------|
| Task names | Sentence case, action-first, descriptive | `Install OMEGA Memory via pip`, `Configure systemd unit for OMEGA MCP` |
| Role naming | kebab-case, `ai-dev-` prefix | `ai-dev-tmux`, `ai-dev-omega-memory`, `ai-dev-hermes` |
| Variable prefix | Role name with underscores | `ai_dev_tmux_version`, `ai_dev_omega_memory_namespace` |
| Tags | Role name as tag on all tasks | `tags: [ai-dev-tmux]` |
| Handlers | Use handlers for service restarts, not inline `command` | `notify: restart omega-mcp` |
| Idempotency | All tasks must be idempotent | Use `creates:`, `when:`, `stat` checks |
| Block/rescue | Use for tasks that might fail on first run | `block:` for install, `rescue:` for cleanup |

**Anti-patterns:**
- Never use `shell:` when `command:` suffices
- Never use `ignore_errors: true` — use `failed_when:` with specific conditions
- Never hardcode paths — use variables from `defaults/main.yml`
- Never use `become: true` unless the task genuinely requires root (most don't on a dev container)

### File Path Conventions

| Path | Purpose | Managed By |
|------|---------|------------|
| `~/.cargo/bin/claude-tmux` | claude-tmux binary | ai-dev-tmux |
| `~/.tmux.conf` | tmux configuration (keybindings) | ai-dev-tmux |
| `~/.config/systemd/user/tmux-server.service` | tmux auto-start | ai-dev-tmux |
| `~/.local/bin/omega` | OMEGA Memory CLI | ai-dev-omega-memory (via pip) |
| `~/.omega/` | OMEGA data directory (SQLite DB, ONNX model) | ai-dev-omega-memory |
| `~/.config/systemd/user/omega-mcp.service` | OMEGA MCP auto-start | ai-dev-omega-memory |
| `~/.claude/settings.json` | Claude Code hooks | ai-dev-omega-memory (merge only) |
| `~/.hermes/` | Hermes Agent config directory | ai-dev-hermes |
| `~/.hermes/config.yaml` | Hermes main config | ai-dev-hermes |
| `~/.hermes/.env` | Hermes secrets (vault-templated) | ai-dev-hermes |
| `~/.hermes/SOUL.md` | Hermes personality/instructions | ai-dev-hermes |
| `~/.hermes/skills/` | BMAD skill stubs | ai-dev-hermes |

**Rule:** Each role owns specific paths. No role writes to another role's paths except through the conditional integration wiring pattern (documented in Core Architectural Decisions).

**Anti-patterns:**
- Never install tools to `/usr/local/bin/` — use user-space paths (`~/.local/bin/`, `~/.cargo/bin/`)
- Never write configs to `/etc/` — user-space `~/.config/` or tool-specific dirs
- Never create paths outside the user's home directory without explicit `become: true` justification

### Variable Naming & Defaults

**`defaults/main.yml` conventions:**

| Pattern | Rule | Example |
|---------|------|---------|
| Naming | `ai_dev_{rolename}_{setting}` | `ai_dev_omega_memory_version: "0.4.2"` |
| Version pinning | Exact version in defaults, overridable | `ai_dev_hermes_version: "1.2.0"` |
| Feature flags | Boolean, default to enabled | `ai_dev_omega_memory_backup_enabled: true` |
| Paths | Use `~` or `{{ ansible_user_dir }}` | `ai_dev_omega_memory_data_dir: "{{ ansible_user_dir }}/.omega"` |
| Namespace | Project-driven variable | `ai_dev_omega_memory_namespace: "{{ project_name }}"` |
| Secrets | Reference vault variables, never inline | `ai_dev_hermes_api_key: "{{ vault_anthropic_api_key }}"` |

**Shared variables** (defined in playbook `group_vars/` or passed as extra-vars):

| Variable | Purpose | Used By |
|----------|---------|---------|
| `project_name` | Drives OMEGA namespace, container hostname | ai-dev-omega-memory, ai-dev-hermes |
| `vault_anthropic_api_key` | Anthropic API key (vault-encrypted) | ai-dev-hermes |

### systemd Unit Patterns

**All systemd user services follow this template:**

```ini
[Unit]
Description={{ service_description }}
After=network.target

[Service]
Type=simple
ExecStart={{ exec_command }}
Restart=on-failure
RestartSec=5
Environment=PATH={{ ansible_user_dir }}/.local/bin:{{ ansible_user_dir }}/.cargo/bin:/usr/local/bin:/usr/bin:/bin

[Install]
WantedBy=default.target
```

| Pattern | Rule |
|---------|------|
| Unit naming | `{tool-name}.service` — `tmux-server.service`, `omega-mcp.service` |
| Type | `simple` for long-running processes |
| Restart | `on-failure` with `RestartSec=5` |
| PATH | Include pyenv, cargo, and local bin paths |
| User scope | `systemctl --user` — never system-level for dev tools |
| Enable | `systemctl --user enable {service}` for boot persistence |
| Lingering | `loginctl enable-linger {{ ansible_user }}` for user services to start at boot |

### Conditional Integration Wiring Pattern

**Standard pattern for cross-role detection and configuration:**

```yaml
- name: Check if OMEGA Memory is installed
  ansible.builtin.stat:
    path: "{{ ansible_user_dir }}/.local/bin/omega"
  register: omega_installed

- name: Configure Hermes MCP connection to OMEGA
  ansible.builtin.blockinfile:
    path: "{{ ansible_user_dir }}/.hermes/config.yaml"
    marker: "# {mark} OMEGA MCP CONNECTION - MANAGED BY ANSIBLE"
    block: |
      mcp_servers:
        omega-memory:
          command: omega
          args: ["serve", "--mcp"]
  when: omega_installed.stat.exists
```

| Pattern | Rule |
|---------|------|
| Detection | Use `stat` module to check for binary or config file existence |
| Marker | Use `blockinfile` with `# {mark} ... MANAGED BY ANSIBLE` markers |
| Conditional | Always use `when:` — never fail if the other tool isn't present |
| Idempotent | `blockinfile` is inherently idempotent with markers |

### Verify Task Patterns

**Each role includes `verify.yml` with this structure:**

```yaml
- name: "VERIFY | Check {{ tool_name }} binary exists"
  ansible.builtin.command: "{{ binary_path }} --version"
  register: version_check
  changed_when: false
  failed_when: version_check.rc != 0

- name: "VERIFY | Check {{ tool_name }} service is running"
  ansible.builtin.systemd:
    name: "{{ service_name }}"
    scope: user
  register: service_status
  failed_when: service_status.status.ActiveState != "active"
  when: service_has_systemd_unit | default(false)

- name: "VERIFY | Run {{ tool_name }} health check"
  ansible.builtin.command: "{{ health_check_command }}"
  register: health_check
  changed_when: false
  failed_when: health_check.rc != 0
  when: health_check_command is defined
```

| Pattern | Rule |
|---------|------|
| Task prefix | `VERIFY |` in all verify task names |
| Changed when | `changed_when: false` — verify tasks never report changes |
| Failure mode | Explicit `failed_when:` — never `ignore_errors` |
| Optional checks | `when:` guard for checks that only apply if a feature is installed |

### Secret Handling Patterns

| Pattern | Rule |
|---------|------|
| Vault variable prefix | `vault_` prefix for all encrypted variables |
| .env templating | Jinja2 template with vault vars: `ANTHROPIC_API_KEY={{ vault_anthropic_api_key }}` |
| File permissions | `mode: '0600'` on all .env files |
| .gitignore | Role ensures `.gitignore` includes `.env`, `*.db` in tool directories |
| No secrets in output | `no_log: true` on tasks that handle secrets |

### Claude Code Skill Patterns

**All AI agents MUST follow these conventions for new Claude Code skills:**

| Pattern | Rule | Example |
|---------|------|---------|
| Skill directory | `.claude/skills/{skill-name}/` | `.claude/skills/bmad-update-project-docs/` |
| Required files | `SKILL.md` (frontmatter + instructions) | YAML frontmatter with name, description |
| Workflow file | `workflow.md` for multi-step skills | Mode router: update/check/full |
| Instructions | `instructions.md` for core logic | Step-by-step algorithm |
| Templates | `templates/` for reusable prompts | `section-update-prompt.md` |
| References | `references/` for configuration data | `doc-section-mapping.md` |
| SKILL.md size | Under 500 lines | Move details to separate files |
| Independence | Each skill works standalone | No tight coupling to other skills |

**bmad-update-project-docs skill structure:**

```
.claude/skills/bmad-update-project-docs/
├── SKILL.md                          # Frontmatter + invocation rules
├── workflow.md                       # Mode router (update/check/full)
├── instructions.md                   # Core update algorithm
├── templates/
│   └── section-update-prompt.md      # Prompt template for section regeneration
└── references/
    └── doc-section-mapping.md        # Maps file patterns → doc sections
```

**Anti-patterns:**
- Never modify files in `.claude/skills/bmad-*/` — these are BMAD upstream
- Never create skills that depend on other skills being installed (design for independence)
- Never hardcode project-specific paths — use config or references files

### Enforcement Guidelines

**All AI agents MUST:**
1. Use the variable naming convention: `ai_dev_{rolename}_{setting}`
2. Pin exact tool versions in `defaults/main.yml`
3. Use `stat` + `when:` for conditional integration — never fail if optional tool is absent
4. Use `blockinfile` with `MANAGED BY ANSIBLE` markers for any config file shared between roles
5. Include `verify.yml` with VERIFY-prefixed tasks for every role
6. Use `no_log: true` on any task handling vault variables or .env content
7. Use user-space paths (`~/.config/`, `~/.local/bin/`) — never system paths for dev tools

**Pattern Verification:**
- `ansible-lint` validates role structure and task conventions
- `yamllint` validates YAML formatting
- `detect-secrets scan` validates no hardcoded secrets
- Verify tasks run as part of playbook to confirm tool health

## Project Structure & Boundaries

### Requirements to Repository Mapping

| FR Category | Target Repo | New Files/Directories |
|------------|-------------|----------------------|
| Session Persistence (FR1-5) | homelab-infra | New role `ai-dev-tmux` |
| Persistent Memory (FR6-15) | homelab-infra | New role `ai-dev-omega-memory` |
| Agent Orchestration (FR16-22) | homelab-infra | New role `ai-dev-hermes` |
| Integration (FR23-26) | homelab-infra | Conditional wiring tasks in each role |
| Provisioning (FR27-32) | homelab-infra | New playbook `deploy-ai-dev-container.yml` |
| Operational Guardrails (FR33-39) | homelab-infra | Config templates + verify tasks across roles |
| Anthropic Subscription (FR40-42) | homelab-infra | Verify tasks in `ai-dev-hermes` |

### homelab-infra — New Ansible Roles & Playbook

```
homelab-infra/
├── ansible/
│   ├── roles/
│   │   ├── ai-dev-tmux/                              # NEW ROLE (FR1-FR5)
│   │   │   ├── tasks/
│   │   │   │   ├── main.yml                          # Orchestrates all task files
│   │   │   │   ├── install-rustup.yml                # Install Rust/Cargo if missing
│   │   │   │   ├── install-claude-tmux.yml           # cargo install with version check
│   │   │   │   ├── configure-tmux.yml                # .tmux.conf keybindings, claude-tmux popup
│   │   │   │   ├── configure-systemd.yml             # tmux-server.service user unit
│   │   │   │   └── verify.yml                        # AT-1.1 through AT-1.4 health checks
│   │   │   ├── handlers/main.yml                     # restart tmux-server
│   │   │   ├── templates/
│   │   │   │   ├── tmux.conf.j2                      # tmux config with claude-tmux keybinding
│   │   │   │   └── tmux-server.service.j2            # systemd user unit
│   │   │   ├── defaults/main.yml                     # ai_dev_tmux_version, paths
│   │   │   └── meta/main.yml                         # depends: dev-host
│   │   │
│   │   ├── ai-dev-omega-memory/                      # NEW ROLE (FR6-FR15)
│   │   │   ├── tasks/
│   │   │   │   ├── main.yml                          # Orchestrates all task files
│   │   │   │   ├── install-omega.yml                 # pip install omega-memory[server]
│   │   │   │   ├── configure-omega.yml               # omega setup, ONNX model download
│   │   │   │   ├── configure-hooks.yml               # Claude Code hook registration (merge)
│   │   │   │   ├── configure-systemd.yml             # omega-mcp.service user unit
│   │   │   │   ├── configure-backup.yml              # SQLite backup systemd timer
│   │   │   │   ├── configure-namespace.yml           # Project namespace setup
│   │   │   │   ├── wire-hermes.yml                   # Conditional: if Hermes found, wire MCP
│   │   │   │   └── verify.yml                        # AT-2.1 through AT-2.9 health checks
│   │   │   ├── handlers/main.yml                     # restart omega-mcp
│   │   │   ├── templates/
│   │   │   │   ├── omega-mcp.service.j2              # systemd user unit for MCP server
│   │   │   │   ├── omega-backup.service.j2           # backup service unit
│   │   │   │   ├── omega-backup.timer.j2             # backup timer (daily)
│   │   │   │   └── claude-hooks.json.j2              # OMEGA hook entries for merge
│   │   │   ├── defaults/main.yml                     # ai_dev_omega_memory_version, namespace, backup
│   │   │   └── meta/main.yml                         # depends: dev-host
│   │   │
│   │   ├── ai-dev-hermes/                            # NEW ROLE (FR16-FR22)
│   │   │   ├── tasks/
│   │   │   │   ├── main.yml                          # Orchestrates all task files
│   │   │   │   ├── install-hermes.yml                # Run Hermes installer script
│   │   │   │   ├── configure-hermes.yml              # config.yaml, SOUL.md
│   │   │   │   ├── configure-env.yml                 # .env from vault (no_log: true)
│   │   │   │   ├── configure-skills.yml              # BMAD skill stubs
│   │   │   │   ├── configure-cron.yml                # Hermes cron jobs
│   │   │   │   ├── wire-omega.yml                    # Conditional: if OMEGA found, wire MCP
│   │   │   │   └── verify.yml                        # AT-3.1 through AT-3.10 health checks
│   │   │   ├── handlers/main.yml                     # (no services to restart — Hermes is interactive)
│   │   │   ├── templates/
│   │   │   │   ├── hermes-config.yaml.j2             # Hermes config with conditional MCP
│   │   │   │   ├── hermes-env.j2                     # .env with vault_anthropic_api_key
│   │   │   │   └── hermes-soul.md.j2                 # SOUL.md personality
│   │   │   ├── files/
│   │   │   │   └── skills/                           # BMAD skill stub files
│   │   │   │       ├── bmad-sprint-director/
│   │   │   │       │   └── SKILL.md
│   │   │   │       └── bmad-quick-dev/
│   │   │   │           └── SKILL.md
│   │   │   ├── defaults/main.yml                     # ai_dev_hermes_version, model, paths
│   │   │   └── meta/main.yml                         # depends: dev-host
│   │   │
│   │   └── [existing roles unchanged]
│   │
│   ├── playbooks/
│   │   ├── deploy-ai-dev-container.yml               # NEW — composes dev-host + ai-dev-* roles
│   │   └── [existing playbooks unchanged]
│   │
│   ├── inventory/
│   │   └── group_vars/
│   │       └── ai_dev.yml                            # NEW — shared vars: project_name, vault refs
│   │
│   └── tests/
│       └── test-ai-dev-stack.sh                      # NEW — comprehensive AT-1 through AT-N5
│
└── terraform/                                        # NO CHANGES (MVP)
```

### Claude Code Skills — New & Modified

```
.claude/skills/
├── bmad-update-project-docs/                         # NEW SKILL (FR43-FR52)
│   ├── SKILL.md                                      # Frontmatter + invocation
│   ├── workflow.md                                   # Mode router: update/check/full
│   ├── instructions.md                               # Core update algorithm
│   ├── templates/
│   │   └── section-update-prompt.md                  # Prompt for section regeneration
│   └── references/
│       └── doc-section-mapping.md                    # File patterns → doc sections
│
├── autoresearch/                                     # INSTALLED (3rd-party)
│   └── [uditgoenka/autoresearch skill files]         # /autoresearch:fix command
│
└── bmad-*/                                           # UNCHANGED — BMAD upstream skills
    └── [do not modify these]
```

### homelab-playbook — Planning Artifacts & Templates

```
homelab-playbook/
├── _bmad-output/
│   ├── planning-artifacts/
│   │   ├── prd.md                                    # AI Dev Container PRD (updated)
│   │   ├── architecture.md                           # THIS DOCUMENT (updated)
│   │   ├── production-readiness-architecture.md      # Previous architecture (renamed)
│   │   ├── product-brief-ai-dev-container.md         # Product brief (existing)
│   │   ├── product-brief-ai-dev-container-distillate.md
│   │   ├── validation-report-prd-2026-04-03.md       # PRD validation report
│   │   └── research/
│   │       ├── technical-ephemeral-cloud-containers-research-2026-03-31.md
│   │       └── technical-incremental-docs-autoresearch-2026-04-03.md
│   │
│   └── [story templates]                             # MODIFY: add "Eval Assertions" section
│
└── [rest of homelab-playbook unchanged]
```

### homelab-apps — No Changes

This project does not modify any Docker Compose stacks. All changes are host-level Ansible roles in homelab-infra and Claude Code skills.

### Architectural Boundaries

**Repository Boundaries:**

| Boundary | Rule | Violation Example |
|----------|------|-------------------|
| homelab-infra owns all host config | Ansible roles, systemd units, tool installations | Never manually pip install on a container |
| homelab-apps owns Docker stacks | Not touched by this project | Never add AI dev tools as Docker containers |
| homelab-playbook owns planning | PRDs, architecture, stories | Never put Ansible code here |

**Role Boundaries:**

| Boundary | Rule |
|----------|------|
| Each role owns its paths | ai-dev-tmux owns `~/.tmux.conf`, ai-dev-omega-memory owns `~/.omega/`, etc. |
| Cross-role writes use blockinfile | Only through conditional integration wiring with `MANAGED BY ANSIBLE` markers |
| No role assumes another is installed | All cross-role checks use `stat` + `when:` |

**Data Boundaries:**

| Data Type | Location | Backup Scope |
|-----------|----------|-------------|
| OMEGA SQLite database | `~/.omega/memory.db` | YES — omega-backup.timer (daily) |
| OMEGA ONNX model | `~/.omega/models/` | NO — re-downloadable |
| Hermes config | `~/.hermes/` | YES — included if container-level Restic runs |
| Hermes sessions | `~/.hermes/sessions/` | NO — ephemeral session data |
| Hermes skills | `~/.hermes/skills/` | YES — custom skills are valuable |
| claude-tmux binary | `~/.cargo/bin/claude-tmux` | NO — re-buildable |
| Claude Code settings | `~/.claude/settings.json` | YES — contains hook config |

### Integration Points

**Internal (within container):**

```
Claude Code sessions ──(hooks)──→ OMEGA MCP Server ←──(MCP)── Hermes Director
       │                              │
       └── tmux sessions              └── SQLite DB (~/.omega/memory.db)
              │
              └── claude-tmux TUI (reads tmux session state)
```

**External (container to outside):**
- Hermes → Anthropic API (HTTPS, API key auth, Max Plan)
- Claude Code → Anthropic API (HTTPS, Max Plan)
- OMEGA → None (fully local, no external calls)
- claude-tmux → None (reads local tmux state only)

**Cross-repo (homelab-infra to target container):**
- Ansible SSH → ct-dev-homelab (VMID 150, pve2) for role execution
- Ansible vault → decrypts secrets at deploy time, templates to .env files

## Architecture Validation Results

### Coherence Validation

**Decision Compatibility:**
- All technology choices are compatible: pyenv-managed Python 3.11+ serves both OMEGA (3.9+) and Hermes (3.11+). Rust/Cargo for claude-tmux is independent. No version conflicts.
- systemd user services for tmux-server and omega-mcp are compatible — both use `WantedBy=default.target` with `loginctl enable-linger`.
- Conditional integration wiring via `stat` + `when:` + `blockinfile` is compatible with all three roles' install-then-configure pattern.

**Pattern Consistency:**
- All roles follow identical conventions: `ai_dev_{role}_{setting}` variables, kebab-case role names, VERIFY-prefixed health checks, `MANAGED BY ANSIBLE` markers for cross-role writes.
- All systemd units follow the same template (Type=simple, Restart=on-failure, user scope).
- Secret handling is consistent: vault variables with `vault_` prefix, `no_log: true`, `mode: '0600'` on .env files.

**Structure Alignment:**
- Every FR maps to a specific role and task file. No orphaned requirements.
- Role boundaries are clean — each role owns specific paths, cross-role writes use the documented wiring pattern.
- The playbook composition order is a preference, not a hard requirement, which the conditional wiring pattern supports.

### Requirements Coverage

**Functional Requirements: 52/52 covered**

| Category | FRs | Architectural Support |
|----------|-----|----------------------|
| Session Persistence | FR1-FR5 | ai-dev-tmux: claude-tmux binary, tmux config, systemd auto-start, keybinding |
| Persistent Memory | FR6-FR15 | ai-dev-omega-memory: OMEGA pip install, MCP server, hooks, backup timer, namespace config |
| Agent Orchestration | FR16-FR22 | ai-dev-hermes: Hermes installer, config, skills, cron, MCP connection |
| Integration | FR23-FR26 | Conditional wiring in omega + hermes roles, Claude Code hooks pipeline |
| Provisioning | FR27-FR32 | deploy-ai-dev-container.yml playbook, group_vars, role independence |
| Operational Guardrails | FR33-FR39 | Config templates (process limits, namespace isolation, secret filtering, git safety) |
| Anthropic Subscription | FR40-FR42 | ai-dev-hermes verify tasks (AT-3.10), documented in defaults |
| BMAD Workflow Enhancements | FR43-FR52 | Standalone skill `bmad-update-project-docs` (3 modes), story template eval assertions section, autoresearch skill install |

**Non-Functional Requirements: All addressed**

| NFR | Architectural Support |
|-----|----------------------|
| NFR-REL-1: tmux survives reboots | tmux-server.service systemd user unit with lingering |
| NFR-REL-2: SQLite survives crashes | OMEGA uses WAL mode by default |
| NFR-REL-3: Roles recover from partial failure | Idempotent tasks with `creates:`, `when:`, `stat` checks |
| NFR-REL-4: <=24h backup RPO | omega-backup.timer (daily systemd timer) |
| NFR-REL-5: Independent degradation | Role independence model — no hard cross-role dependencies |
| NFR-SEC-1: Encrypted secrets | Ansible vault, `no_log: true`, `mode: '0600'` |
| NFR-SEC-2: No secret capture | OMEGA hook configuration excludes sensitive file patterns |
| NFR-SEC-3: Namespace isolation | Single `project_name` variable drives namespace everywhere |
| NFR-SEC-4: .env/DB not in git | Roles ensure .gitignore entries |
| NFR-SEC-5: Workers on feature branches | Operational guardrail in config templates |
| NFR-PERF-1: Search <2s | OMEGA's native SQLite + vector search (validated in AT-2.5) |
| NFR-PERF-2: Hook <5s | OMEGA SessionStart briefing (validated in AT-2.2) |
| NFR-PERF-3: Stack <2GB RAM | Resource budget: OMEGA ~337MB + Hermes ~100MB + system overhead |
| NFR-PERF-4: Playbook <15min | Role independence allows incremental runs; claude-tmux build cached after first |
| NFR-INT-1: Stable MCP interface | Version pinning in defaults, no version-specific coupling |
| NFR-INT-2: Standard hook location | `~/.claude/settings.json` — surgical merge, not overwrite |
| NFR-INT-3: Pinned versions | All tool versions in `defaults/main.yml` |
| NFR-INT-4: Max Plan compatible | AT-3.10 verify task validates programmatic usage |
| NFR-INT-5: BMAD update-safe | All enhancements in standalone skills/templates — zero bmad-* modifications |
| NFR-INT-6: Skill independence | Doc update skill works on any BMAD project with docs/ folder |

### Gap Analysis Results

| # | Gap | Priority | Resolution |
|---|-----|----------|------------|
| 1 | OMEGA's actual install paths may differ from assumed `~/.omega/` | Important | First story should validate actual OMEGA paths during installation and update role defaults accordingly |
| 2 | Hermes installer may create its own Python venv — exact post-install layout unknown | Important | First story should run installer interactively, document actual output, then codify in Ansible tasks |
| 3 | claude-tmux `cargo install` package name may differ from assumed | Minor | Verify exact crate name via `cargo search claude-tmux` during first story |
| 4 | OMEGA MCP server CLI command (`omega serve --mcp`?) not confirmed | Important | Validate exact MCP server launch command from OMEGA docs during implementation |
| 5 | Hermes config.yaml MCP server registration format not confirmed | Important | Validate exact config format from Hermes docs during implementation |

**Assessment:** All gaps are implementation-time verifications, not architectural gaps. The architecture is correct in its approach; specific CLI commands and paths need validation against upstream tool documentation during the first implementation stories.

### Architecture Completeness Checklist

**Requirements Analysis**
- [x] Project context thoroughly analyzed (42 FRs, 7 domains)
- [x] Scale and complexity assessed (medium, single-user, single-container)
- [x] Technical constraints identified (10 constraints)
- [x] Cross-cutting concerns mapped (8 concerns)

**Architectural Decisions**
- [x] Critical decisions documented (7 decisions with rationale)
- [x] Technology stack fully specified with versions
- [x] Integration patterns defined (conditional wiring, MCP, hooks)
- [x] Deployment sequence documented (flexible order with convergence)

**Implementation Patterns**
- [x] Ansible task conventions (7 rules + anti-patterns)
- [x] File path ownership defined per role
- [x] Variable naming conventions with examples
- [x] systemd unit patterns with template
- [x] Conditional integration wiring pattern with code example
- [x] Verify task pattern with code example
- [x] Secret handling pattern (5 rules)
- [x] Enforcement guidelines (7 mandatory rules)

**Project Structure**
- [x] Complete directory structure for homelab-infra changes
- [x] Repository boundaries defined
- [x] Role boundaries defined with ownership rules
- [x] Data boundaries with backup scope
- [x] All integration points documented (internal, external, cross-repo)

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION

**Confidence Level:** High — brownfield project extending established Ansible patterns, clear role boundaries, well-understood upstream tools with known installation paths.

**Key Strengths:**
- Builds on proven, operational infrastructure with established Ansible conventions
- Role independence model allows incremental deployment and testing
- Conditional wiring pattern eliminates hard ordering dependencies
- Every FR has a specific home in a specific role and task file
- Architecture accommodates upstream tool installation quirks gracefully

**Areas for Future Enhancement:**
- Dedicated `ct-ai-dev` Terraform module for fresh project containers (Phase 2)
- DBOS crash recovery wrapping Director workflows (Phase 2)
- GEPA skill optimization with cron scheduling (Phase 2)
- Cross-project OMEGA instance for methodology insights (Phase 2)
- Unified health-check script aggregating all tool diagnostics (Phase 2)

### Implementation Handoff

**AI Agent Guidelines:**
- Follow all architectural decisions exactly as documented
- Use implementation patterns consistently across all roles and skills
- Respect role boundaries — each role owns specific paths
- Use conditional integration wiring for any cross-role configuration
- Never modify files in `.claude/skills/bmad-*/` — BMAD update-safety is a hard constraint
- Use Claude Code skill patterns for any new skills
- Refer to this document for all architectural questions
- Validate upstream tool CLI commands against current docs during implementation

**Implementation Sequence:**
```
Epic 0: BMAD Workflow Enhancements (prerequisite)
  0.1  Story template + eval assertions section
  0.2  Install autoresearch skill
  0.3  Build bmad-update-project-docs skill (check + update + full modes)

Epic 1: ai-dev-tmux         ← uses eval assertions, autoresearch:fix
Epic 2: ai-dev-omega-memory  ← uses eval assertions, autoresearch:fix
Epic 3: ai-dev-hermes        ← uses eval assertions, autoresearch:fix
Epic 4: Playbook & Integration
  └── followed by /update-project-docs to sync docs
```

**First Implementation Priority:**
Build BMAD Workflow Enhancements (Epic 0) — prerequisite tooling that improves the quality of all subsequent epics. Start with eval assertions in the story template (simplest), then autoresearch install, then the doc update skill.
