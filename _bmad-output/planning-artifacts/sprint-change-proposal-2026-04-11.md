# Sprint Change Proposal — Layered Configuration & Dual-Model Architecture for AI Dev Roles

**Date:** 2026-04-11
**Trigger:** Manual Hermes installation on ct-dev-test revealed need for hierarchical variable design and dual-model architecture
**Scope:** Moderate — affects Epic 3 stories, Epic 4 stories, architecture doc, PRD, inventory structure
**Recommended Path:** Direct Adjustment (no scope change, no rollback)

---

## 1. Issue Summary

During the manual Hermes installation on ct-dev-test (April 8), two significant findings emerged:

**Finding 1: Hierarchical configuration needed.** Multiple settings are shared across all AI dev containers (Slack tokens, Home Assistant URL, OpenRouter key, default model, TTS provider) vs project-specific (working directory, repos, namespace). The current architecture assumes per-project parameterization via `host_vars` (FR31) but does not define a layered defaults mechanism. Without it, each new container would require duplicating all Hermes/OMEGA/tmux settings.

**Finding 2: Dual-model architecture.** Hermes Agent uses **OpenRouter** as its LLM provider (currently `google/gemma-4-26b-a4b-it`, configurable to any model) for its own thinking, planning, and coordination. For actual **implementation work** (code writing, BMAD skill execution, file analysis), Hermes delegates to **Claude Code** workers via `claude -p`, which use Anthropic Max Plan credentials. This is a deliberate separation:
- Hermes (Director) = OpenRouter → any model → thinking, planning, Slack/HA interaction
- Claude Code (Worker) = Anthropic Max Plan → Claude → code implementation, BMAD execution, git operations

This changes the auth story:
- **OAuth banned for third-party agents** (April 4, 2026) — but irrelevant since Hermes uses OpenRouter, not Anthropic directly
- **`ANTHROPIC_API_KEY` not needed in Hermes `.env`** — cleared, auto-discovery available as fallback only
- **`OPENROUTER_API_KEY` is the primary secret** for Hermes's own LLM calls
- **Ansible vault needed for:** OpenRouter key, Slack tokens, HA token, and optional provider keys (Google, FAL, Tinker, WandB)

### Evidence

- `host_vars/ct-dev-homelab.yml` and `host_vars/ct-dev-test.yml` are identical 3-line files — no tool config at all
- Manual install record (`hermes-agent-manual-install-2026-04-08.md`) documents 20+ configurable settings, most shared across containers
- `group_vars/all.yml` already demonstrates the layered pattern for notifications (smtp_host used by 5 roles)
- No `group_vars/dev_hosts/` exists — there's no layer between global and per-host

---

## 2. Impact Analysis

### Epic Impact

| Epic | Impact | Details |
|------|--------|---------|
| Epic 3 | **Modified** | Story 3.1 must design the full variable catalog in `defaults/main.yml` with the commented-out convention. Story 3.2 MCP/skills config variables also need the layered treatment. |
| Epic 4 | **Modified** | Story 4.1 must create `group_vars/dev_hosts/` with per-tool files and migrate `host_vars` to directory-based layout. |
| Epic 0-2 | No impact | Already complete. Existing roles (`ai-dev-tmux`, `ai-dev-omega-memory`) already use flat prefixed variables — compatible with this pattern. |

### Artifact Impact

| Artifact | Impact | Sections |
|----------|--------|----------|
| **Architecture** | Update needed | "Deferred Decisions" (Slack/HA not Phase 2 for Hermes-native), "Cross-Component Dependencies" (auth approach), "Variable Naming & Defaults" (add commented-out convention), "Shared variables" table (expand) |
| **PRD** | Minor update | FR31 expansion to mention layered defaults; FR37 clarification on auth auto-discovery |
| **Epics** | Story AC updates | Story 3.1 and Story 4.1 acceptance criteria |
| **Inventory** | New structure | `group_vars/dev_hosts/` directory, `host_vars` migration to directories |

---

## 3. Recommended Approach: Direct Adjustment

**Rationale:** Ansible's variable precedence system is purpose-built for this pattern. No new tooling, no architectural change — just designing the variable structure to use what Ansible already provides.

**Effort:** Low — variable design is part of Story 3.1 anyway; this formalizes the approach.
**Risk:** Low — the precedence chain (`role defaults < group_vars < host_vars`) is a core Ansible feature.
**Timeline Impact:** None — fits within existing story scope.

---

## 4. Detailed Change Proposals

### Change 1: Architecture Doc — Variable Design Convention

**File:** `planning-artifacts/architecture.md`
**Section:** Variable Naming & Defaults

**ADD** after the existing "Variable Naming & Defaults" conventions:

```markdown
### Layered Variable Design Convention

All AI dev roles use a three-tier variable precedence model:

| Tier | Location | Purpose | Example |
|------|----------|---------|---------|
| 1. Role defaults | `roles/ai-dev-*/defaults/main.yml` | Factory defaults — every configurable setting listed | `ai_dev_hermes_model: "anthropic/claude-sonnet-4-6"` |
| 2. Group vars | `group_vars/dev_hosts/ai-dev-*.yml` | Org-wide shared settings — what Tom uses across all containers | `ai_dev_hermes_ha_url: "https://ha.bi-services.be"` |
| 3. Host vars | `host_vars/ct-<project>/ai-dev-*.yml` | Project-specific overrides — only what differs | `ai_dev_hermes_model: "anthropic/claude-opus-4-6"` |

**Commented-out catalog convention:** Every tier 2 (group_vars) and tier 3 (host_vars) file
lists ALL available settings from the role defaults. Active settings are uncommented; inactive
settings are commented with their default value. This provides a scannable overview of what
*could* be configured without reading the role source.

**File-per-tool split:** Both `group_vars/dev_hosts/` and `host_vars/ct-<project>/` use
separate YAML files per tool (e.g., `ai-dev-hermes.yml`, `ai-dev-omega.yml`). Ansible
merges all files in a directory at the same precedence level.
```

**Rationale:** Formalizes the design pattern so all stories and future roles follow it consistently.

---

### Change 2: Architecture Doc — Dual-Model Architecture & Auth

**File:** `planning-artifacts/architecture.md`
**Section:** Core Architectural Decisions (new subsection) + Cross-Component Dependencies

**ADD** new architectural decision:

```markdown
### Dual-Model Architecture (Director vs Worker)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Hermes LLM provider | OpenRouter (any model) | Flexibility to use best model for coordination tasks; not locked to Anthropic. Currently google/gemma-4-26b-a4b-it |
| Claude Code workers | Anthropic Max Plan (Claude) | Best model for code implementation, BMAD skill execution. Spawned via `claude -p` |
| Auth separation | Hermes uses OPENROUTER_API_KEY; Claude Code uses Max Plan auto-discovery | No coupling between Director and Worker credentials |
| Model configurability | Per-container via layered variables | Different projects may need different Director models (e.g., Opus for complex planning) |

**Cascading:** Hermes config.yaml `model.provider` is set to `openrouter` with `model.base_url`
pointing to OpenRouter's API. Claude Code workers inherit Max Plan credentials from the host
environment. The two credential chains are independent — Hermes can function even if Claude Code
auth changes, and vice versa.
```

**UPDATE** Cross-Component Dependencies:

**OLD:**
```
Ansible vault    ←── Hermes .env (ANTHROPIC_API_KEY)
                 ←── OMEGA config (if API key needed)
```

**NEW:**
```
OpenRouter API   ←── Hermes Director (LLM calls for thinking/planning/coordination)
Claude Code creds ←── Claude Code workers (spawned via `claude -p`, Max Plan auto-discovery)
Ansible vault    ←── Hermes .env (OPENROUTER_API_KEY, Slack tokens, HA token, optional provider keys)
                 ←── OMEGA config (if API key needed)
```

**Rationale:** Hermes uses OpenRouter as its primary LLM provider. Claude Code workers use Max Plan credentials via auto-discovery. The two are independent.

---

### Change 3: Architecture Doc — Deferred Decisions Update

**File:** `planning-artifacts/architecture.md`
**Section:** Decision Priority Analysis > Deferred Decisions

**OLD:**
```
- Information source integrations — Slack, email, Granola MCPs (Phase 2)
```

**NEW:**
```
- Information source integrations — Slack MCP, email MCP, Granola MCP as Claude Code tools (Phase 2)
- Note: Hermes has built-in Slack and Home Assistant integrations configured via role variables (Epic 3, not deferred)
```

**Rationale:** Hermes-native integrations (Slack, HA) are configured during install, not deferred. The Phase 2 item is specifically about Claude Code MCP integrations.

---

### Change 4: Story 3.1 — Acceptance Criteria Update

**File:** `planning-artifacts/epics.md`
**Section:** Story 3.1: Install Hermes Agent and Configure Basics

**OLD:**
```
**Given** a container with `dev-host` role applied (pyenv Python 3.11+, Node.js)
**When** the `ai-dev-hermes` role runs the install and configure tasks
**Then** Hermes is installed via its installer script (AT-3.1)
**And** `~/.hermes/config.yaml` is created with terminal backend=local, cwd to project root (AT-3.2)
**And** `~/.hermes/SOUL.md` is templated from Jinja2
**And** `~/.hermes/.env` is created from vault-encrypted variables with mode 0600 (FR37, NFR-SEC-1, `no_log: true`)
**And** `hermes doctor` reports all checks passing
**And** `.env` and database files are excluded from git (NFR-SEC-4)
```

**NEW:**
```
**Given** a container with `dev-host` role applied (pyenv Python 3.11+, Node.js)
**When** the `ai-dev-hermes` role runs the install and configure tasks
**Then** Hermes is installed via its installer script (AT-3.1)
**And** `~/.hermes/config.yaml` is templated from Jinja2 with all settings driven by role variables (AT-3.2)
**And** `~/.hermes/SOUL.md` is templated from Jinja2
**And** `~/.hermes/.env` has stale OAuth tokens cleared; auth uses Claude Code credential auto-discovery
**And** integration tokens (Slack, HA, Tinker) in `.env` are sourced from vault-encrypted variables with mode 0600 (FR37, NFR-SEC-1, `no_log: true`)
**And** `defaults/main.yml` contains the full variable catalog with every configurable Hermes setting (model, iterations, compression, Slack, HA, TTS, terminal, tools, sudo, session reset)
**And** `hermes doctor` reports all checks passing
**And** `.env` and database files are excluded from git (NFR-SEC-4)
```

**Rationale:** Reflects auth discovery, adds the full variable catalog requirement.

---

### Change 5: Story 4.1 — Acceptance Criteria Update

**File:** `planning-artifacts/epics.md`
**Section:** Story 4.1: Create Deployment Playbook and Group Vars

**OLD:**
```
**And** `inventory/group_vars/ai_dev.yml` parameterizes project_name, vault refs (FR31)
```

**NEW:**
```
**And** `inventory/group_vars/dev_hosts/` contains per-tool YAML files (`ai-dev.yml`, `ai-dev-hermes.yml`, `ai-dev-omega.yml`, `ai-dev-tmux.yml`) with the commented-out full catalog convention (FR31)
**And** `host_vars/` for each AI dev container uses directory layout with `vars.yml`, `vault.yml`, and optional per-tool override files
**And** variables follow the three-tier precedence: role defaults < group_vars/dev_hosts < host_vars/ct-<project>
```

**Rationale:** Formalizes the layered config structure and file-per-tool convention.

---

### Change 6: Architecture Doc — Shared Variables Table Expansion

**File:** `planning-artifacts/architecture.md`
**Section:** Variable Naming & Defaults > Shared variables

**OLD:**
```
| Variable | Purpose | Used By |
|----------|---------|---------|
| `project_name` | Drives OMEGA namespace, container hostname | ai-dev-omega-memory, ai-dev-hermes |
| `vault_anthropic_api_key` | Anthropic API key (vault-encrypted) | ai-dev-hermes |
```

**NEW:**
```
| Variable | Purpose | Used By | Tier |
|----------|---------|---------|------|
| `project_name` | Drives OMEGA namespace, Hermes working dir | ai-dev-omega-memory, ai-dev-hermes | host_vars |
| `project_repos` | Git repositories to clone | dev-host | host_vars |
| `dev_user` | Target user for all AI dev roles | all ai-dev-* roles | group_vars |
| `ai_dev_hermes_model_provider` | LLM provider for Hermes Director | ai-dev-hermes | group_vars (overridable) |
| `ai_dev_hermes_model_default` | Default model name | ai-dev-hermes | group_vars (overridable) |
| `ai_dev_hermes_model_base_url` | Provider API endpoint | ai-dev-hermes | group_vars |
| `ai_dev_hermes_slack_bot_token` | Slack bot token | ai-dev-hermes | group_vars (vault ref) |
| `ai_dev_hermes_slack_app_token` | Slack app token (Socket Mode) | ai-dev-hermes | group_vars (vault ref) |
| `ai_dev_hermes_slack_allowed_users` | Allowed Slack user IDs | ai-dev-hermes | group_vars |
| `ai_dev_hermes_slack_home_channel` | Default Slack channel ID | ai-dev-hermes | group_vars (overridable) |
| `ai_dev_hermes_ha_url` | Home Assistant URL | ai-dev-hermes | group_vars |
| `vault_openrouter_api_key` | Encrypted OpenRouter API key | ai-dev-hermes | group_vars/vault |
| `vault_slack_bot_token` | Encrypted Slack bot token | ai-dev-hermes | group_vars/vault |
| `vault_slack_app_token` | Encrypted Slack app token | ai-dev-hermes | group_vars/vault |
| `vault_ha_token` | Encrypted HA long-lived token | ai-dev-hermes | group_vars/vault |
| `vault_google_api_key` | Encrypted Google AI key (optional) | ai-dev-hermes | group_vars/vault |

Note: `vault_anthropic_api_key` removed — Hermes uses OpenRouter; Claude Code workers use Max Plan auto-discovery.
```

**Rationale:** Reflects the dual-model architecture, layered variable design, and real config from ct-dev-test.

---

### Change 7a: PRD — FR40 Update (Dual-Model Auth)

**File:** `planning-artifacts/prd.md`
**Section:** Functional Requirements

**OLD:**
```
FR40: Director can authenticate and make API calls using the user's Anthropic Max Plan credentials
```

**NEW:**
```
FR40: Director authenticates to its configured LLM provider (OpenRouter by default) for coordination tasks, and spawns Claude Code workers that use Anthropic Max Plan credentials for implementation work
```

**Rationale:** The Director uses OpenRouter, not Anthropic directly. Claude Code workers (spawned via `claude -p`) use Max Plan. The two credential chains are independent.

---

### Change 7b: PRD — FR37 Clarification

**File:** `planning-artifacts/prd.md`
**Section:** Functional Requirements

**OLD:**
```
FR37: All secrets are managed via Ansible vault — no plaintext credentials in roles or configuration files
```

**NEW:**
```
FR37: All secrets are managed via Ansible vault — no plaintext credentials in roles or configuration files. Vault-managed secrets include: OpenRouter API key, Slack bot/app tokens, Home Assistant token, and optional provider keys (Google, FAL, Tinker, WandB). Anthropic API key is not vault-managed — Claude Code workers use Max Plan credential auto-discovery.
```

**Rationale:** Clarifies which secrets are vault-managed now that the auth model is understood.

---

### Change 7: Inventory Structure Migration

**Action:** During Epic 4 Story 4.1 implementation, migrate existing flat `host_vars` files to directory layout:

```
BEFORE:
  host_vars/ct-dev-homelab.yml
  host_vars/ct-dev-test.yml

AFTER:
  host_vars/ct-dev-homelab/
    vars.yml              # project_name, project_repos (moved from flat file)
    # vault.yml           # when project-specific secrets needed
    # ai-dev-hermes.yml   # when project-specific Hermes overrides needed
  host_vars/ct-dev-test/
    vars.yml
```

**Rationale:** Consistent directory-based layout across all hosts. ct-sparkle-cps already uses this pattern.

---

## 5. Implementation Handoff

**Scope classification: Moderate**

Changes span story acceptance criteria, architecture doc, PRD, and inventory design — but no scope increase, no new epics, no timeline impact.

| Recipient | Responsibility |
|-----------|---------------|
| **Dev (Amelia)** | Update architecture.md: layered variable convention (Change 1), dual-model architecture + auth (Change 2), deferred decisions (Change 3), shared variables (Change 6). Implement the variable catalog in Story 3.1 `defaults/main.yml`. |
| **SM (Bob)** | Update epics.md: Story 3.1 ACs (Change 4), Story 4.1 ACs (Change 5). Update prd.md: FR40 (Change 7a), FR37 (Change 7b). |
| **Dev (Amelia)** | Implement inventory migration during Story 4.1 (Change 7). |

**Success criteria:**
- Architecture doc reflects dual-model architecture (Hermes→OpenRouter, Workers→Max Plan), layered variable design, and expanded shared variables table
- PRD FR40 reflects dual-model auth; FR37 clarifies vault-managed secrets
- Story 3.1 `defaults/main.yml` contains commented full catalog of all Hermes settings, organized by section (model, agent, integrations, terminal, display, security, memory, delegation, cron, session)
- Story 4.1 creates `group_vars/dev_hosts/` with per-tool files using the commented-out convention
- `host_vars` migrated to directory layout for all AI dev containers
- A setting defined in `group_vars/dev_hosts/ai-dev-hermes.yml` is correctly overridden by the same variable in `host_vars/ct-<project>/ai-dev-hermes.yml`
- Hermes authenticates to OpenRouter for its own LLM calls; Claude Code workers use Max Plan auto-discovery independently
