---
stepsCompleted: [1, 2, 3, 4]
status: 'complete'
completedAt: '2026-04-03'
inputDocuments:
  - homelab-playbook/_bmad-output/planning-artifacts/prd.md
  - homelab-playbook/_bmad-output/planning-artifacts/architecture.md
workflowType: 'epics-and-stories'
project_name: 'homelab'
user_name: 'tomamourette'
date: '2026-04-03'
---

# AI Dev Container - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for AI Dev Container, decomposing 52 functional requirements from the PRD and architectural decisions into implementable stories. Epic 0 (BMAD Workflow Enhancements) is a prerequisite that improves the development workflow used for all subsequent epics.

## Requirements Inventory

### Functional Requirements

FR1: User can run Claude Code sessions inside named tmux sessions on the server
FR2: User can disconnect from SSH and reconnect to find all tmux sessions intact with no context loss
FR3: User can view all active sessions and their status (Working/Idle/Waiting) via a TUI dashboard
FR4: User can switch between active sessions from the TUI dashboard
FR5: tmux server and key sessions can auto-start on container boot
FR6: Claude Code sessions can automatically capture lessons, decisions, and context to persistent storage via lifecycle hooks
FR7: Claude Code sessions can receive an automatic briefing of relevant prior context at session start
FR8: User can search stored memories using natural language queries with semantic relevance ranking
FR9: System can detect and deduplicate semantically similar memories automatically
FR10: System can evolve existing memories when related content is captured (append, not duplicate)
FR11: System can expire transient memories (session summaries) via TTL while preserving persistent memories (lessons) indefinitely
FR12: User can organize memories into project-scoped namespaces
FR13: System can enforce namespace isolation — queries in one namespace never return results from another
FR14: System can back up the memory database on a configurable schedule
FR15: User can restore the memory database from a backup
FR16: User can install and configure an always-on Director agent that runs in a tmux session
FR17: Director can connect to the persistent memory system via MCP to query and store context
FR18: Director can execute a quick-dev task end-to-end without human intervention after initial command
FR19: Director can load and execute BMAD methodology skills
FR20: Director can spawn subagents to delegate subtasks
FR21: Director can schedule recurring tasks via cron
FR22: User can verify Director health and configuration via a built-in diagnostic command
FR23: Director can query persistent memory and incorporate retrieved context into task execution
FR24: Claude Code worker sessions can capture outputs to persistent memory via hooks, making them available to other sessions
FR25: Multiple simultaneous tmux sessions can share memory — what one session stores, another can retrieve without restart
FR26: User can verify end-to-end integration: Director triggers a task that uses memory context and produces a verifiable output
FR27: User can provision the complete AI dev stack on a container by running a single Ansible playbook
FR28: Ansible playbook can be re-run on the same container without side effects (idempotent)
FR29: Each tool's Ansible role can be run and tested independently
FR30: Ansible AI dev roles can leverage the existing dev-host role's runtime dependencies without duplicating or conflicting with the baseline
FR31: Ansible playbook can be parameterized per project (project name, OMEGA namespace, API keys via vault)
FR32: Each Ansible role can run verification tasks that confirm the installed service is functional
FR33: System can limit the maximum number of concurrent worker processes
FR34: System can prevent memory queries from returning results across namespace boundaries
FR35: System can prevent secrets (API keys, passwords) from being captured into persistent memory
FR36: Workers can only use regular git push, never force-push
FR37: All secrets are managed via Ansible vault — no plaintext credentials in roles or configuration files
FR38: Director does not merge code to main branches without human review
FR39: Director does not install system packages directly — package management stays in Ansible roles
FR40: Director can authenticate and make API calls using the user's Anthropic Max Plan credentials
FR41: Claude Code CLI can be spawned programmatically by the Director under the Max Plan subscription
FR42: System can document any rate limits or usage constraints that apply under Max Plan for automated usage
FR43: User can run an incremental documentation update skill that detects changed files and updates only affected doc sections
FR44: The doc update skill can detect which files changed using git history and classify changes by impact
FR45: The doc update skill can present a change plan requiring user confirmation before writing
FR46: The doc update skill can update individual sections while preserving unchanged sections exactly as-is
FR47: The doc update skill can run in read-only check mode producing a health report
FR48: The doc update skill can delegate to bmad-document-project for full regeneration
FR49: The doc update skill can maintain a configurable file-to-doc mapping
FR50: The doc update skill can track state in project-scan-report.json
FR51: User can add Eval Assertions section to story templates without modifying BMAD built-in skill files
FR52: User can install and use autoresearch skill separately from BMAD for post-code-review fix loops

### NonFunctional Requirements

NFR-REL-1: tmux sessions survive container reboots (60s recovery)
NFR-REL-2: OMEGA database survives unexpected termination (SQLite WAL mode)
NFR-REL-3: Ansible roles rerunnable after partial failure
NFR-REL-4: OMEGA backups run on schedule (<=24h data loss)
NFR-REL-5: Independent tool degradation — no single failure renders stack unusable
NFR-SEC-1: All credentials encrypted via Ansible vault — zero plaintext secrets
NFR-SEC-2: OMEGA does not capture sensitive file content
NFR-SEC-3: Namespace isolation enforced at query layer — no bypass
NFR-SEC-4: Hermes .env and OMEGA DB excluded from git
NFR-SEC-5: Workers restricted to feature branches
NFR-PERF-1: OMEGA search <2s for 5K memories
NFR-PERF-2: OMEGA SessionStart hook <5s
NFR-PERF-3: AI dev stack RAM <2GB on 8GB container
NFR-PERF-4: Full playbook execution <15 minutes
NFR-INT-1: OMEGA stable MCP interface (no version coupling)
NFR-INT-2: Claude Code hooks in standard settings location
NFR-INT-3: All tool versions pinned with compatibility matrix
NFR-INT-4: Anthropic Max Plan compatible
NFR-INT-5: BMAD-update-safe — zero modifications to bmad-* skills
NFR-INT-6: Doc update skill independent — works on any BMAD project

### Additional Requirements

From Architecture:
- Brownfield project — extends existing codebase, no starter template
- All ai-dev-* roles depend only on dev-host (no cross-role hard dependencies)
- Conditional integration wiring: roles detect other tools, configure if present
- systemd user services for tmux-server and omega-mcp
- pyenv Python 3.11+ as foundation
- Rust/Cargo for claude-tmux (cached binary)
- Claude Code skill conventions: SKILL.md <500 lines, references/, templates/
- BMAD update-safety: zero modifications to .claude/skills/bmad-*/

### UX Design Requirements

Not applicable — infrastructure project.

### FR Coverage Map

| FR | Epic | Description |
|----|------|-------------|
| FR1 | Epic 1 | Named tmux sessions |
| FR2 | Epic 1 | Disconnect/reconnect survival |
| FR3 | Epic 1 | TUI dashboard (claude-tmux) |
| FR4 | Epic 1 | Session switching from TUI |
| FR5 | Epic 1 | Auto-start on boot |
| FR6 | Epic 2 | Auto-capture to persistent storage |
| FR7 | Epic 2 | Auto-briefing at session start |
| FR8 | Epic 2 | Semantic search of memories |
| FR9 | Epic 2 | Auto-deduplication |
| FR10 | Epic 2 | Memory evolution (append) |
| FR11 | Epic 2 | TTL expiry for transient memories |
| FR12 | Epic 2 | Project-scoped namespaces |
| FR13 | Epic 2 | Namespace isolation enforcement |
| FR14 | Epic 2 | Backup on schedule |
| FR15 | Epic 2 | Restore from backup |
| FR16 | Epic 3 | Director agent in tmux |
| FR17 | Epic 3 | Director MCP connection to OMEGA |
| FR18 | Epic 3 | Quick-dev task execution |
| FR19 | Epic 3 | BMAD skill loading |
| FR20 | Epic 3 | Subagent spawning |
| FR21 | Epic 3 | Cron scheduling |
| FR22 | Epic 3 | Director health check |
| FR23 | Epic 3 | Director queries memory |
| FR24 | Epic 2 | Worker sessions capture to memory |
| FR25 | Epic 2 | Multi-session memory sharing |
| FR26 | Epic 3 | End-to-end integration verification |
| FR27 | Epic 4 | Single playbook deployment |
| FR28 | Epic 4 | Idempotent playbook |
| FR29 | Epic 4 | Independent role testing |
| FR30 | Epic 4 | Baseline role compatibility |
| FR31 | Epic 4 | Parameterized per project |
| FR32 | Epic 4 | Role verification tasks |
| FR33 | Epic 3 | Worker process limits |
| FR34 | Epic 2 | Namespace query isolation |
| FR35 | Epic 2 | Secret capture prevention |
| FR36 | Epic 3 | No force-push from workers |
| FR37 | Epic 3 | Ansible vault for all secrets |
| FR38 | Epic 3 | No auto-merge to main |
| FR39 | Epic 3 | No direct package install |
| FR40 | Epic 3 | Max Plan authentication |
| FR41 | Epic 3 | Programmatic Claude Code spawn |
| FR42 | Epic 3 | Rate limit documentation |
| FR43 | Epic 0 | Incremental doc update skill |
| FR44 | Epic 0 | Git-diff change detection |
| FR45 | Epic 0 | Change plan with user confirmation |
| FR46 | Epic 0 | Section-level updates |
| FR47 | Epic 0 | Read-only check mode |
| FR48 | Epic 0 | Full mode delegation |
| FR49 | Epic 0 | Configurable file-to-doc mapping |
| FR50 | Epic 0 | State tracking |
| FR51 | Epic 0 | Eval assertions in story template |
| FR52 | Epic 0 | Autoresearch skill installation |

## Epic List

### Epic 0: BMAD Workflow Enhancements (Prerequisite Tooling)

Developer has an enhanced BMAD workflow with binary eval assertions in stories, automated post-code-review fix loops, and incremental documentation updates — used during all subsequent epics.

**FRs covered:** FR43, FR44, FR45, FR46, FR47, FR48, FR49, FR50, FR51, FR52
**NFRs addressed:** NFR-INT-5, NFR-INT-6

### Epic 1: Persistent Sessions — Never Lose Context Again

Developer can run Claude Code in tmux sessions that survive SSH disconnects, laptop restarts, and container reboots. A TUI dashboard shows all session status at a glance.

**FRs covered:** FR1, FR2, FR3, FR4, FR5
**NFRs addressed:** NFR-REL-1, NFR-PERF-3 (partial)

### Epic 2: Persistent Memory — Sessions That Remember

Developer's Claude Code sessions automatically capture lessons and receive context briefings from previous sessions. Memories are searchable, deduplicated, and organized by project namespace with backup and restore.

**FRs covered:** FR6, FR7, FR8, FR9, FR10, FR11, FR12, FR13, FR14, FR15, FR24, FR25, FR34, FR35
**NFRs addressed:** NFR-REL-2, NFR-REL-4, NFR-SEC-2, NFR-SEC-3, NFR-SEC-4, NFR-PERF-1, NFR-PERF-2, NFR-INT-1, NFR-INT-2

### Epic 3: Always-On Director — AI That Works While You Sleep

Developer has an always-on Hermes Agent Director that executes tasks autonomously, connects to OMEGA memory for context, loads BMAD skills, spawns subagents, and schedules recurring work. Works with Anthropic Max Plan.

**FRs covered:** FR16, FR17, FR18, FR19, FR20, FR21, FR22, FR23, FR26, FR33, FR36, FR37, FR38, FR39, FR40, FR41, FR42
**NFRs addressed:** NFR-SEC-1, NFR-SEC-5, NFR-INT-3, NFR-INT-4

### Epic 4: One-Command Deployment — Reproducible AI Dev Stack

Developer can deploy the complete AI dev stack on any container with a single Ansible playbook command. Roles are independently testable, idempotent, parameterized per project, and pass comprehensive acceptance tests.

**FRs covered:** FR27, FR28, FR29, FR30, FR31, FR32
**NFRs addressed:** NFR-REL-3, NFR-REL-5, NFR-PERF-3, NFR-PERF-4

---

## Epic 0: BMAD Workflow Enhancements

Developer has an enhanced BMAD workflow with binary eval assertions in stories, automated post-code-review fix loops, and incremental documentation updates — used during all subsequent epics.

### Story 0.1: Add Eval Assertions Section to Story Template

As a developer,
I want an "Eval Assertions" section in my BMAD story template that derives binary test criteria from acceptance criteria,
So that every story has measurable pass/fail verification points for autoresearch and code review.

**Acceptance Criteria:**

**Given** the story template in `_bmad-output/`
**When** I run `/bmad-create-story` for any story
**Then** the generated story file contains an "Eval Assertions" section with binary test assertions
**And** each assertion maps to a specific acceptance criterion
**And** zero files in `.claude/skills/bmad-*/` are modified (AT-6.8)

### Story 0.2: Install Autoresearch Skill

As a developer,
I want the autoresearch skill installed in my Claude Code environment,
So that I can run `/autoresearch:fix` after code review to automatically iterate on findings until eval assertions pass.

**Acceptance Criteria:**

**Given** the Claude Code environment with BMAD installed
**When** I install the autoresearch skill to `.claude/skills/autoresearch/`
**Then** `/autoresearch:fix` is invocable and responds (AT-6.7)
**And** the skill is in its own directory, separate from `bmad-*/` skills
**And** zero files in `.claude/skills/bmad-*/` are modified (AT-6.8)

### Story 0.3: Build Doc Update Skill — Check Mode

As a developer,
I want to run `/update-project-docs check` to see which documentation is stale,
So that I know which docs need updating after code changes without modifying any files.

**Acceptance Criteria:**

**Given** a project with a `docs/` folder and recent code changes since the last doc update
**When** I run `/update-project-docs check`
**Then** the skill detects changed files using `git log --since` (FR44)
**And** classifies changes by impact to specific documentation files using the file-to-doc mapping (FR49)
**And** displays a health report showing stale docs and what changed (FR47, AT-6.2)
**And** no documentation files are modified (read-only mode)
**And** state is tracked in `project-scan-report.json` (FR50, AT-6.5)

### Story 0.4: Build Doc Update Skill — Update Mode

As a developer,
I want to run `/update-project-docs` to incrementally update only the affected documentation sections after an epic,
So that my project docs stay current without full regeneration.

**Acceptance Criteria:**

**Given** a project with stale docs (as identified by check mode)
**When** I run `/update-project-docs`
**Then** the skill presents a change plan showing which docs and sections will be updated (FR45, AT-6.3)
**And** waits for user confirmation before writing
**And** updates only affected sections while preserving unchanged sections exactly (FR46)
**And** updates `project-scan-report.json` with new git ref and section timestamps (FR50, AT-6.5)

### Story 0.5: Build Doc Update Skill — Full Mode and Mapping Config

As a developer,
I want `/update-project-docs full` to delegate to the existing `bmad-document-project` skill for complete regeneration,
So that I have a single entry point for both incremental and full documentation workflows.

**Acceptance Criteria:**

**Given** the doc update skill is installed
**When** I run `/update-project-docs full`
**Then** the skill delegates to `bmad-document-project` for a full rescan (FR48, AT-6.4)
**And** the `references/doc-section-mapping.md` file is configurable per project (FR49)
**And** the skill works on any BMAD project with a `docs/` folder, not just this one (NFR-INT-6)

---

## Epic 1: Persistent Sessions — Never Lose Context Again

Developer can run Claude Code in tmux sessions that survive SSH disconnects, laptop restarts, and container reboots. A TUI dashboard shows all session status at a glance.

### Story 1.1: Install Rust and Build claude-tmux Binary

As a developer,
I want claude-tmux installed on my container via an Ansible role,
So that I have a TUI dashboard to monitor all Claude Code sessions.

**Acceptance Criteria:**

**Given** a container with the `dev-host` role applied (build-essential available)
**When** the `ai-dev-tmux` role runs the install tasks
**Then** Rust/Cargo is installed via rustup if not already present
**And** `claude-tmux` is built via `cargo install` with the pinned version from `defaults/main.yml`
**And** the binary exists at `~/.cargo/bin/claude-tmux` and responds to `--version`
**And** subsequent role runs skip the build if the binary version matches (idempotent)

### Story 1.2: Configure tmux with claude-tmux Integration

As a developer,
I want tmux configured with claude-tmux keybindings so I can view session status and switch between sessions from a popup TUI,
So that I can monitor and manage all Claude Code sessions without leaving tmux.

**Acceptance Criteria:**

**Given** claude-tmux binary is installed (Story 1.1)
**When** the `ai-dev-tmux` role runs the configure tasks
**Then** `~/.tmux.conf` is created/updated with claude-tmux popup keybinding (`Ctrl-C`)
**And** launching the TUI via the keybinding displays all active sessions with status indicators (Working/Idle/Waiting) (FR3, AT-1.2)
**And** I can navigate between sessions using j/k and Enter (FR4, AT-1.3)
**And** Claude Code sessions run inside named tmux sessions (FR1)
**And** disconnecting SSH and reconnecting preserves all sessions intact (FR2, AT-1.1)

### Story 1.3: Configure systemd Auto-Start for tmux Server

As a developer,
I want the tmux server to auto-start on container boot via systemd,
So that my sessions survive reboots without manual intervention.

**Acceptance Criteria:**

**Given** tmux is configured (Story 1.2)
**When** the `ai-dev-tmux` role runs the systemd tasks
**Then** a `tmux-server.service` user unit is created at `~/.config/systemd/user/`
**And** `loginctl enable-linger` is configured for the user
**And** the service is enabled via `systemctl --user enable tmux-server`
**And** after a container reboot, tmux server starts automatically within 60 seconds (FR5, NFR-REL-1, AT-1.4)
**And** the role includes `verify.yml` with VERIFY-prefixed health checks (binary exists, service active, tmux running)

---

## Epic 2: Persistent Memory — Sessions That Remember

Developer's Claude Code sessions automatically capture lessons and receive context briefings from previous sessions. Memories are searchable, deduplicated, and organized by project namespace with backup and restore.

### Story 2.1: Install OMEGA Memory and Configure MCP Server

As a developer,
I want OMEGA Memory installed with its MCP server running as a systemd service,
So that I have a persistent shared brain available for all sessions.

**Acceptance Criteria:**

**Given** a container with `dev-host` role applied (pyenv Python 3.11+ available)
**When** the `ai-dev-omega-memory` role runs the install and systemd tasks
**Then** OMEGA is installed via `pip install omega-memory[server]` using pyenv Python
**And** `omega setup` completes and downloads the 90MB ONNX embedding model
**And** `omega doctor` reports all checks passing (AT-2.1)
**And** `omega-mcp.service` systemd user unit is created, enabled, and running
**And** the MCP server starts automatically on boot
**And** OMEGA RAM stays within expected bounds (~337MB) (NFR-PERF-3)

### Story 2.2: Register Claude Code Hooks for Memory Capture

As a developer,
I want OMEGA hooks registered in Claude Code so that sessions automatically capture context and receive briefings,
So that every session benefits from what previous sessions learned.

**Acceptance Criteria:**

**Given** OMEGA is installed and MCP server is running (Story 2.1)
**When** the `ai-dev-omega-memory` role runs the hook configuration tasks
**Then** OMEGA hooks are registered in `~/.claude/settings.json` via surgical merge (not overwrite) (NFR-INT-2)
**And** existing Claude Code settings are preserved
**And** SessionStart hook fires and delivers a briefing (or "no memories yet") (FR7, AT-2.2)
**And** SessionStop hook generates a session summary (FR6, AT-2.3)
**And** a new session receives context from previous sessions (FR24, AT-2.4)
**And** OMEGA does not capture content from sensitive file patterns (.env, credentials, secrets) (FR35, NFR-SEC-2)

### Story 2.3: Configure Namespace Isolation and Backup

As a developer,
I want memories organized by project namespace with isolation and automated backups,
So that client data stays separated and my memory database is protected.

**Acceptance Criteria:**

**Given** OMEGA is installed with hooks registered (Story 2.2)
**When** the `ai-dev-omega-memory` role runs namespace and backup tasks
**Then** project namespace is configured from the `project_name` variable (FR12)
**And** queries in one namespace never return results from another (FR13, FR34, NFR-SEC-3, AT-N1.1)
**And** an `omega-backup.timer` systemd unit runs daily SQLite backups (FR14, NFR-REL-4)
**And** backups are restorable — copy backup over DB, restart, verify memories intact (FR15, AT-2.8)
**And** OMEGA database and .env files are excluded from git tracking (NFR-SEC-4)

### Story 2.4: Verify Memory Features and Conditional Hermes Wiring

As a developer,
I want OMEGA's advanced memory features working and Hermes integration wired if present,
So that the memory system is fully functional and ready for Director integration.

**Acceptance Criteria:**

**Given** OMEGA is installed with namespace and backup configured (Story 2.3)
**When** the verify and conditional wiring tasks run
**Then** semantic search returns relevant results ranked by relevance (FR8, AT-2.5)
**And** duplicate memories are detected and evolved, not duplicated (FR9, FR10, AT-2.6)
**And** session summaries expire per TTL policy while lessons persist (FR11, AT-2.7)
**And** multiple simultaneous sessions share memory without restart (FR25, AT-4.3)
**And** if Hermes config exists at `~/.hermes/config.yaml`, OMEGA MCP entry is added via `blockinfile` (conditional wiring)
**And** if Hermes is not installed, the role completes without error
**And** `verify.yml` passes all VERIFY-prefixed health checks

---

## Epic 3: Always-On Director — AI That Works While You Sleep

Developer has an always-on Hermes Agent Director that executes tasks autonomously, connects to OMEGA memory for context, loads BMAD skills, spawns subagents, and schedules recurring work. Works with Anthropic Max Plan.

### Story 3.1: Install Hermes Agent and Configure Basics

As a developer,
I want Hermes Agent installed and configured with API credentials,
So that I have a Director agent ready to run tasks.

**Acceptance Criteria:**

**Given** a container with `dev-host` role applied (pyenv Python 3.11+, Node.js)
**When** the `ai-dev-hermes` role runs the install and configure tasks
**Then** Hermes is installed via its installer script (AT-3.1)
**And** `~/.hermes/config.yaml` is templated from Jinja2 with all settings driven by role variables (AT-3.2)
**And** `~/.hermes/SOUL.md` is templated from Jinja2
**And** `~/.hermes/.env` has stale OAuth tokens cleared; auth uses Claude Code credential auto-discovery as fallback
**And** Hermes Director uses OpenRouter as its primary LLM provider; Claude Code workers use Anthropic Max Plan for implementation (FR40)
**And** integration tokens (Slack, HA, OpenRouter, optional providers) in `.env` are sourced from vault-encrypted variables with mode 0600 (FR37, NFR-SEC-1, `no_log: true`)
**And** `defaults/main.yml` contains the full variable catalog with every configurable Hermes setting (model, iterations, compression, Slack, HA, TTS, terminal, tools, sudo, session reset) using the commented-out convention
**And** `hermes doctor` reports all checks passing
**And** `.env` and database files are excluded from git (NFR-SEC-4)

### Story 3.2: Configure OMEGA MCP Connection and BMAD Skills

As a developer,
I want the Director connected to OMEGA memory and loaded with BMAD skill stubs,
So that it can use project context and execute BMAD methodology tasks.

**Acceptance Criteria:**

**Given** Hermes is installed (Story 3.1)
**When** the `ai-dev-hermes` role runs MCP wiring and skills tasks
**Then** if OMEGA is installed, Hermes config includes OMEGA MCP server entry (FR17, AT-3.3, conditional wiring)
**And** if OMEGA is not installed, Hermes works standalone without error
**And** BMAD skill stubs are deployed to `~/.hermes/skills/` (FR19)
**And** Hermes can load and list available skills (AT-3.5)
**And** all tool versions are pinned in `defaults/main.yml` with a documented compatibility matrix (NFR-INT-3)

### Story 3.3: Autonomous Task Execution and Cron Scheduling

As a developer,
I want the Director to execute tasks autonomously and schedule recurring work,
So that it can work while I'm away and run maintenance tasks on schedule.

**Acceptance Criteria:**

**Given** Hermes is configured with MCP and skills (Story 3.2)
**When** I issue a quick-dev task to the Director
**Then** Hermes completes the task end-to-end without human intervention (FR18, AT-3.6)
**And** the Director runs in a tmux session that survives SSH disconnect (AT-3.7)
**And** Hermes can spawn subagents for delegated subtasks (FR20, AT-3.8)
**And** recurring tasks can be scheduled via cron (FR21, AT-3.9)
**And** Hermes authenticates using Anthropic Max Plan credentials (FR40, AT-3.10)
**And** Claude Code CLI can be spawned programmatically under Max Plan (FR41)

### Story 3.4: Operational Guardrails and Integration Verification

As a developer,
I want operational guardrails enforced and end-to-end integration verified,
So that the Director operates safely within defined boundaries.

**Acceptance Criteria:**

**Given** the Director is functional (Story 3.3)
**When** the guardrail configuration and integration tests run
**Then** worker process count is limited to the configured maximum (FR33, AT-N2.1)
**And** workers use regular git push, never force-push (FR36, AT-N3.3)
**And** the Director does not merge to main without human review (FR38, AT-N5.1)
**And** the Director does not install packages directly — package management stays in Ansible (FR39, AT-N5.3)
**And** workers are restricted to feature branches (NFR-SEC-5)
**And** Director can query OMEGA memory and incorporate context into tasks (FR23, AT-4.1)
**And** end-to-end integration passes: Director triggers task using OMEGA context (FR26, AT-4.2)
**And** `verify.yml` passes all VERIFY-prefixed health checks (FR22)
**And** rate limits or usage constraints under Max Plan are documented (FR42)

---

## Epic 4: One-Command Deployment — Reproducible AI Dev Stack

Developer can deploy the complete AI dev stack on any container with a single Ansible playbook command. Roles are independently testable, idempotent, parameterized per project, and pass comprehensive acceptance tests.

### Story 4.1: Create Deployment Playbook and Group Vars

As a developer,
I want a single Ansible playbook that deploys the complete AI dev stack,
So that I can provision any container with one command.

**Acceptance Criteria:**

**Given** all three ai-dev-* roles are complete (Epics 1-3)
**When** I run `ansible-playbook deploy-ai-dev-container.yml`
**Then** the playbook composes dev-host → ai-dev-tmux → ai-dev-omega-memory → ai-dev-hermes (FR27)
**And** `inventory/group_vars/dev_hosts/` contains per-tool YAML files (`ai-dev.yml`, `ai-dev-hermes.yml`, `ai-dev-omega.yml`, `ai-dev-tmux.yml`) with the commented-out full catalog convention (FR31)
**And** `host_vars/` for each AI dev container uses directory layout with `vars.yml`, `vault.yml`, and optional per-tool override files
**And** variables follow the three-tier precedence: role defaults < group_vars/dev_hosts < host_vars/ct-project
**And** the playbook leverages dev-host without duplicating or conflicting (FR30)
**And** total execution completes within 15 minutes (NFR-PERF-4)
**And** total AI stack RAM stays under 2GB (NFR-PERF-3)

### Story 4.2: Idempotency, Independence, and Acceptance Tests

As a developer,
I want the playbook to be idempotent, roles independently testable, and a comprehensive test script validating the full stack,
So that I can confidently re-run provisioning and verify everything works.

**Acceptance Criteria:**

**Given** the playbook runs successfully (Story 4.1)
**When** I run the playbook a second time
**Then** the second run reports zero changed tasks (or only expected ones like service restarts) (FR28, AT-5.1)
**And** each role can be run independently via `--tags` (FR29)
**And** each role's `verify.yml` confirms the installed service is functional (FR32)
**And** no single tool failure renders the stack unusable — each degrades independently (NFR-REL-5)
**And** roles recover correctly when rerun after partial failure (NFR-REL-3)
**And** `tests/test-ai-dev-stack.sh` comprehensive test script passes AT-1 through AT-6 and AT-N1 through AT-N5 (51 tests total)
**And** services start correctly after a container reboot (AT-5.3)

---

## Epic 8: PVE3 Node + Local LLM — AI Inference at Home

Developer has a third Proxmox node (pve3) running on the Minisforum N5 Pro with an AMD RX 9070 XT GPU connected via OCULink, serving local LLM inference (Gemma 4 26B) through Ollama in an LXC container with a web chat interface.

**Research:** planning-artifacts/research/technical-pve3-oculink-gpu-llm-research-2026-04-15.md

### Story 8.1: Install Proxmox VE on N5 Pro and Join Cluster

As a homelab operator,
I want Proxmox VE installed on the N5 Pro and joined to home-cluster as pve3,
So that I have a 3-node HA-capable cluster with my most powerful hardware available.

**Acceptance Criteria:**

**Given** the N5 Pro with an M.2 NVMe SSD installed
**When** I complete the Proxmox installation and cluster join
**Then** BIOS is configured (SVM, IOMMU, ACS, UMA 8G, UEFI-only, Secure Boot off)
**And** Proxmox VE 8.4 is installed on ZFS mirror (RAID1) across NVMe 1 + NVMe 2, with 8GB swap. NVMe 3 is left untouched for Story 8.5.
**And** hostname is `pve3`, static IP is `192.168.50.203/24`
**And** kernel params include `amd_iommu=on iommu=pt`
**And** VFIO modules are loaded (vfio, vfio_iommu_type1, vfio_pci)
**And** `/etc/hosts` on pve1, pve2, and pve3 all contain all three nodes
**And** `pvecm add 192.168.50.201` succeeds from pve3
**And** `pvecm status` shows 3 nodes, quorum=2, quorate=Yes
**And** Proxmox web UI at https://192.168.50.203:8006 shows all 3 nodes

**Edge Cases:**
- If graphical installer hangs: use "Console Mode - nomodeset"
- If PVE version mismatch: run `apt update && apt dist-upgrade` on pve1/pve2 first
- If NTP is not synced: enable `systemd-timesyncd` before cluster join

### Story 8.2: Integrate PVE3 into Infrastructure Automation

As a homelab operator,
I want pve3 integrated into Ansible, SSH config, DNS, and documentation,
So that pve3 is managed consistently with pve1 and pve2.

**Acceptance Criteria:**

**Given** pve3 is joined to the cluster (Story 8.1)
**When** I update the infrastructure automation
**Then** `ansible/inventories/homelab/hosts.ini` has pve3 in `[proxmox_hosts]`
**And** `ansible-playbook pve-host.yml --limit pve3` succeeds (NIC ring buffer tuning applied)
**And** SSH config on the control machine has `pve3` alias (192.168.50.203)
**And** Pi-hole custom list includes `pve3` DNS entry
**And** `docs/architecture-homelab-infra.md` is updated with pve3 in the network diagram and node table
**And** `ansible all -m ping` succeeds for all hosts including pve3

### Story 8.3: Set Up GPU via OCULink and LXC Container with Ollama

As a homelab operator,
I want the RX 9070 XT connected via OCULink and Ollama running in a GPU-accelerated LXC container,
So that I can run local LLM inference on my homelab.

**Acceptance Criteria:**

**Given** pve3 is in the cluster with IOMMU configured (Story 8.1)
**When** I connect the GPU and set up the AI container
**Then** RX 9070 XT is connected via OCULink and detected by pve3 (`lspci | grep -i vga`)
**And** IOMMU groups are verified (`find /sys/kernel/iommu_groups/ -type l`)
**And** a privileged LXC container `ct-ai-01` exists on pve3 (8 cores, 32GB RAM, 50GB disk)
**And** GPU device nodes are passed through to the container (`/dev/dri/card0`, `/dev/dri/renderD128`)
**And** Ollama is installed inside the container with Vulkan backend (`OLLAMA_VULKAN=1`)
**And** `ollama run gemma4:e4b` succeeds as a pipeline validation test (small model, ~3GB VRAM)
**And** `ollama ps` confirms GPU layers are being used (not CPU fallback)

**Edge Cases:**
- If GPU not detected: ensure dock/PSU is powered on before pve3 boot; check BIOS OCULink settings
- If IOMMU groups are too broad: apply ACS override patch
- If Vulkan not detected in LXC: verify `/dev/dri/*` device passthrough with mode 0666

### Story 8.4: Deploy Gemma 4 26B and Open WebUI

As a homelab operator,
I want Gemma 4 26B running via Ollama with a web chat interface,
So that I have a self-hosted ChatGPT-like experience powered by my own hardware.

**Acceptance Criteria:**

**Given** Ollama is running with GPU acceleration (Story 8.3)
**When** I deploy the target model and web interface
**Then** `ollama run hf.co/DuoNeural/Gemma-4-26B-A4B-it-GGUF:Q3_K_M` downloads and runs successfully
**And** VRAM usage stays under 16GB during inference (~14GB model + ~1-2GB KV cache)
**And** inference produces coherent responses at reasonable speed
**And** Open WebUI is deployed via Docker inside the LXC container
**And** Open WebUI is accessible at `http://192.168.50.<ip>:3000` and connects to Ollama API
**And** multimodal capability works (text + image input via Gemma 4's vision)

**Edge Cases:**
- If OOM during long conversations: reduce `num_ctx` in Ollama modelfile or switch to Q3_K_S
- If model download fails: retry or use alternative GGUF from Hugging Face
- If Open WebUI can't reach Ollama: verify both are on same container network, Ollama API on 11434

### Story 8.5: Configure Shared Storage and Bulk Storage Pools

As a homelab operator,
I want NVMe 3 configured as a ZFS pool with NFS export for cluster shared storage, and the 5x HDD bays configured as a RAIDZ2 pool for bulk media/file storage,
So that I can live-migrate VMs/CTs between cluster nodes and have redundant bulk storage that survives 2 drive failures.

**Acceptance Criteria:**

**Given** pve3 is in the cluster with ZFS mirror root on NVMe 1+2 (Story 8.1)
**When** I configure the additional storage pools
**Then** NVMe 3 has a ZFS pool (`shared-pool`) with a dataset exported via NFS
**And** pve1 and pve2 mount the NFS share as a Proxmox storage target
**And** a test container can be live-migrated between nodes using the NFS shared storage
**And** 5x HDDs are configured as a ZFS RAIDZ2 pool (`bulk-pool`) with ~60% usable capacity
**And** `bulk-pool` survives 2 simultaneous drive failures (RAIDZ2)
**And** ZFS ARC max is explicitly set (`zfs_arc_max`) to leave headroom for Ollama/GPU workloads
**And** both pools are visible in Proxmox web UI under pve3 storage

**Edge Cases:**
- If NFS mount is slow: verify 10GbE link is active (pve3) vs 2.5GbE (pve1/pve2) — NFS performance bounded by slowest link
- If ZFS ARC consumes too much RAM: tune `zfs_arc_max` in `/etc/modprobe.d/zfs.conf` (recommend 4-8GB for 96GB system)
- If HDDs are not yet installed: this story can be partially completed (NVMe 3 pool + NFS first, HDD pool later)

### Story 8.6: Upgrade Cluster to Proxmox VE 9

(pve3 already upgraded — only pve1 and pve2 remain)


As a homelab operator,
I want all three cluster nodes upgraded from Proxmox VE 8.4 to PVE 9,
So that I get kernel 6.14 (5GbE NIC support on N5 Pro), OpenZFS 2.3.3 (live RAIDZ expansion), OCI container support, and continued upstream security updates.

**Acceptance Criteria:**

**Given** a healthy 3-node cluster running PVE 8.4 (Stories 8.1, 8.2 complete)
**When** I upgrade each node using the official in-place upgrade procedure
**Then** pve3 is upgraded first (fewest containers, easiest to test)
**And** pve2 is upgraded second (migrate ct-dev-homelab to pve3 first, then upgrade, then migrate back)
**And** pve1 is upgraded last (migrate containers to pve2/pve3, upgrade, migrate back)
**And** `pveversion` on all 3 nodes shows PVE 9.x
**And** `pvecm status` shows 3 nodes, quorate=Yes after each node upgrade
**And** all containers and VMs are running and healthy after the full upgrade
**And** both NICs on pve3 (10GbE + 5GbE) are detected and operational
**And** ZFS pools on all nodes are healthy (`zpool status` shows ONLINE)

**Edge Cases:**
- If upgrade fails mid-way on a node: reboot into previous kernel (GRUB menu), troubleshoot before retrying
- If cluster loses quorum during upgrade: only upgrade one node at a time, verify quorum after each
- If containers won't start after upgrade: check LXC config compatibility (PVE 9 uses newer LXC)
- Keep mixed-version window as short as possible — HA is broken in mixed 8+9 clusters
- Follow the official upgrade checklist: `pve8to9 --full` before each node upgrade

### Story 8.7: Integrate AI Services into DNS and Reverse Proxy

As a homelab operator,
I want Open WebUI and Ollama accessible via proper DNS names with HTTPS and SSO protection,
So that the AI services are consistent with the rest of my homelab infrastructure.

**Acceptance Criteria:**

**Given** Open WebUI is running on ct-ai-01 at 192.168.50.160:3000 (Story 8.4)
**When** I integrate the AI services into the existing DNS and routing infrastructure
**Then** `chat.bi-services.be` resolves to the correct IP via Pi-hole custom DNS
**And** Traefik routes `chat.bi-services.be` to Open WebUI with TLS termination
**And** Authelia SSO middleware protects the Open WebUI route
**And** `ollama.bi-services.be` resolves via Pi-hole for direct API access (optional, for programmatic use)
**And** the Pi-hole custom list template (`pihole-custom.list.j2`) includes the AI service entries
**And** Terraform ct-ai-01 module exists (or variables are added) so the IP is available as a Terraform output

**Edge Cases:**
- If Traefik is on ct-docker-01 and Open WebUI is on ct-ai-01: need cross-host routing (like media-indexers.yml pattern)
- If Authelia blocks API calls: add a bypass rule for the Ollama API endpoint or use a separate route without SSO
