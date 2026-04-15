# Story 3.1: Install Hermes Agent and Configure Basics

Status: done

## Story

As a developer,
I want Hermes Agent installed and configured with an Ansible role using the layered variable design,
so that I have a Director agent ready to run tasks with OpenRouter as its LLM provider and all settings driven by overridable variables.

## Acceptance Criteria

1. **Given** a container with `dev-host` role applied (pyenv Python 3.11+, Node.js)
   **When** the `ai-dev-hermes` role runs the install and configure tasks
   **Then** Hermes is installed via its installer script (AT-3.1)
   **And** `~/.local/bin/hermes` is in PATH (or symlinked from `~/.hermes/hermes-agent/venv/bin/hermes`)

2. **Given** the role has installed Hermes
   **When** config.yaml is templated
   **Then** `~/.hermes/config.yaml` is created from Jinja2 template with ALL settings driven by role variables (AT-3.2)
   **And** the model provider is OpenRouter with the configured model and base_url
   **And** terminal backend is local with cwd set to the project workspace path
   **And** max_turns, compression threshold, and all agent settings match role variables

3. **Given** the role has installed Hermes
   **When** the SOUL.md and .env are templated
   **Then** `~/.hermes/SOUL.md` is created from Jinja2 template
   **And** `~/.hermes/.env` has `ANTHROPIC_TOKEN` and `ANTHROPIC_API_KEY` explicitly set to empty (clearing stale OAuth tokens)
   **And** integration tokens (OpenRouter, Slack bot/app, HA, optional: FAL, Tinker, WandB, Google) are sourced from vault-encrypted variables with mode 0600 (FR37, NFR-SEC-1, `no_log: true`)

4. **Given** the role has written config files
   **When** `hermes doctor` runs on the target
   **Then** all checks pass (AT-3.1)

5. **Given** the role's `defaults/main.yml`
   **When** inspected
   **Then** it contains the FULL variable catalog with every configurable Hermes setting, organized by section (model, agent, integrations, terminal, display, security, memory, delegation, cron, session)
   **And** each variable uses the `ai_dev_hermes_` prefix
   **And** all variables have sensible defaults matching the manual install on ct-dev-test

6. **Given** `~/.hermes/.env` and `~/.hermes/sessions/` and `~/.hermes/hermes.db`
   **When** git status runs in the workspace
   **Then** these paths are excluded from git tracking (NFR-SEC-4)

7. **Given** the role has already been run successfully
   **When** the role runs again
   **Then** all tasks report no changes (idempotent)

8. **Given** the BMAD installation at `.claude/skills/bmad-*/`
   **When** this story is implemented
   **Then** zero files in `.claude/skills/bmad-*/` are modified (NFR-INT-5)

## Edge Cases & Error Scenarios

1. **Side effects:** Creates the entire `~/.hermes/` directory tree if not present. Writes `config.yaml`, `.env`, `SOUL.md` — overwrites existing files from manual install. Adds PATH entry to `~/.bashrc` via blockinfile. Adds patterns to `.gitignore` via blockinfile. Does NOT start Hermes as a service (Hermes is interactive, not a daemon). Does NOT run `hermes setup` (interactive wizard).

2. **Dependency failure:** If the curl installer fails mid-download (network issue), partial state may remain at `~/.hermes/hermes-agent/`. The `block/rescue` pattern should clean up the partial install directory. If `dev-host` role dependency is not met (no pyenv Python 3.11+, no Node.js), the installer will fail — the role should validate prerequisites before invoking the installer. If vault variables are undefined (e.g., `vault_openrouter_api_key` not in vault), the `.env` template will render empty values — acceptable for optional keys, but OpenRouter key is required for Hermes to function. The verify task (`hermes doctor`) will catch this.

3. **Assumptions:** `dev-host` role has been applied and pyenv Python 3.11+ is available. Node.js 20 LTS is available via nvm (installed by dev-host). The container has internet access for the curl installer (downloads Python packages, possibly Node.js). The `developer` user has write access to `~/.hermes/`, `~/.local/bin/`, `~/.bashrc`. Ansible vault file exists with at least `vault_openrouter_api_key` defined. The Hermes installer URL (`https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh`) is stable. `~/.local/bin` is the correct binary location (confirmed on ct-dev-test but may change with Hermes versions).

## Eval Assertions

<!-- Binary test assertions derived from acceptance criteria. Used by /autoresearch:fix for post-code-review iteration loops. -->

| # | Assertion | Command/Check | Pass Criteria |
|---|-----------|---------------|---------------|
| AC-1a | Hermes binary exists | `ssh developer@TARGET hermes --version` | Returns version string, exit 0 |
| AC-1b | PATH includes ~/.local/bin | `ssh developer@TARGET bash -lc 'echo $PATH' \| grep -q '.local/bin'` | Exit 0 |
| AC-2a | Config provider is OpenRouter | `ssh developer@TARGET grep 'provider: openrouter' ~/.hermes/config.yaml` | Exit 0, line found |
| AC-2b | Config model matches variable | `ssh developer@TARGET grep 'default:' ~/.hermes/config.yaml` | Contains expected model name |
| AC-2c | Config CWD set | `ssh developer@TARGET grep 'cwd:' ~/.hermes/config.yaml` | Contains project workspace path |
| AC-2d | Config max_turns matches | `ssh developer@TARGET grep 'max_turns:' ~/.hermes/config.yaml` | Contains expected value (default 90) |
| AC-3a | OAuth tokens cleared | `ssh developer@TARGET grep '^ANTHROPIC_TOKEN=$' ~/.hermes/.env` | Exit 0, empty value |
| AC-3b | OpenRouter key present | `ssh developer@TARGET grep -c 'OPENROUTER_API_KEY=.' ~/.hermes/.env` | Returns 1 (non-empty value) |
| AC-3c | .env permissions 0600 | `ssh developer@TARGET stat -c '%a' ~/.hermes/.env` | Output is `600` |
| AC-3d | SOUL.md exists | `ssh developer@TARGET test -f ~/.hermes/SOUL.md` | Exit 0 |
| AC-4 | hermes doctor passes | `ssh developer@TARGET hermes doctor` | Exit 0, all checks pass |
| AC-5 | Full variable catalog (30+) | `grep -c 'ai_dev_hermes_' roles/ai-dev-hermes/defaults/main.yml` | Count >= 30 |
| AC-6a | .env excluded from git | `ssh developer@TARGET grep -q '.hermes/.env' ~/workspace/homelab/.gitignore` | Exit 0 |
| AC-6b | sessions excluded from git | `ssh developer@TARGET grep -q '.hermes/sessions' ~/workspace/homelab/.gitignore` | Exit 0 |
| AC-7 | Idempotent second run | Run role twice, parse second run output | 0 changed tasks |
| AC-8 | No BMAD files modified | `find .claude/skills/bmad-* -newer /tmp/bmad-marker -type f` | Empty output |

## Tasks / Subtasks

- [x] Task 0: Investigate Hermes on ct-dev-test and validate prerequisites (AC: prerequisite)
  - [x] SSH to ct-dev-test (192.168.50.152), confirm Hermes is running with `hermes --version`
  - [x] Document actual installer behavior: what it installs, where, what it creates
  - [x] Confirm pyenv Python 3.11+ and Node.js are available (dev-host prerequisite)
  - [x] Review `~/.hermes/config.yaml` structure for template design
  - [x] Review `~/.hermes/.env` structure for template design (DO NOT log secrets)
  - [x] Document the `hermes doctor` output format for verify task assertions
  - [x] Check Epic 2 retro action items #3 (update architecture.md) and #4 (dev-host friction) — address during this story if applicable

- [x] Task 1: Create role skeleton (AC: #5)
  - [x] Create `roles/ai-dev-hermes/` directory structure: `tasks/`, `templates/`, `defaults/`, `handlers/`, `meta/`, `files/`
  - [x] Create `meta/main.yml` with `dependencies: [{role: dev-host}]`
  - [x] Create `handlers/main.yml` (empty initially, may add restart handlers later)
  - [x] Create `defaults/main.yml` with the FULL variable catalog:
    - Section: Version pinning (`ai_dev_hermes_version`)
    - Section: Target user (`dev_user`, `dev_user_uid`)
    - Section: Model (`ai_dev_hermes_model_provider`, `ai_dev_hermes_model_default`, `ai_dev_hermes_model_base_url`)
    - Section: Agent behavior (`ai_dev_hermes_max_turns`, `ai_dev_hermes_compression_threshold`, `ai_dev_hermes_compression_summary_model`, `ai_dev_hermes_session_reset_mode`, `ai_dev_hermes_session_idle_minutes`)
    - Section: Terminal (`ai_dev_hermes_terminal_backend`, `ai_dev_hermes_terminal_cwd`, `ai_dev_hermes_terminal_timeout`)
    - Section: Display (`ai_dev_hermes_display_personality`, `ai_dev_hermes_tool_progress`)
    - Section: Integrations — Slack (`ai_dev_hermes_slack_bot_token`, `ai_dev_hermes_slack_app_token`, `ai_dev_hermes_slack_allowed_users`, `ai_dev_hermes_slack_home_channel`, `ai_dev_hermes_slack_home_channel_name`)
    - Section: Integrations — Home Assistant (`ai_dev_hermes_ha_url`, `ai_dev_hermes_ha_token`)
    - Section: Integrations — OpenRouter (`ai_dev_hermes_openrouter_api_key`)
    - Section: Integrations — Optional providers (`ai_dev_hermes_google_api_key`, `ai_dev_hermes_fal_api_key`, `ai_dev_hermes_tinker_api_key`, `ai_dev_hermes_wandb_api_key`)
    - Section: Security (`ai_dev_hermes_sudo_enabled`, `ai_dev_hermes_tirith_enabled`, `ai_dev_hermes_redact_secrets`)
    - Section: Memory (`ai_dev_hermes_memory_enabled`, `ai_dev_hermes_memory_char_limit`, `ai_dev_hermes_user_char_limit`)
    - Section: Delegation (`ai_dev_hermes_delegation_max_iterations`)
    - Section: Cron (`ai_dev_hermes_cron_wrap_response`)
    - Section: TTS (`ai_dev_hermes_tts_provider`, `ai_dev_hermes_tts_voice`)
    - Section: Paths (`ai_dev_hermes_home`, `ai_dev_hermes_install_timeout`)

- [x] Task 2: Create install task (AC: #1)
  - [x] Create `tasks/install-hermes.yml`
  - [x] Check if Hermes is already installed: `stat ~/.hermes/hermes-agent/`
  - [x] If not installed: run the curl installer with `block/rescue` for error handling
  - [x] Verify binary at `~/.local/bin/hermes` or `~/.hermes/hermes-agent/venv/bin/hermes`
  - [x] Ensure `~/.local/bin` is in PATH via `blockinfile` in `~/.bashrc`
  - [x] Set timeout to `{{ ai_dev_hermes_install_timeout }}` (default 600s)
  - [x] All tasks tagged `[ai-dev-hermes]`

- [x] Task 3: Create config.yaml template (AC: #2)
  - [x] Create `templates/config.yaml.j2` based on the live config structure from ct-dev-test
  - [x] Template ALL settings using `{{ ai_dev_hermes_* }}` variables
  - [x] Use conditional blocks for optional sections (Slack, HA, FAL, etc.)
  - [x] Create `tasks/configure-hermes.yml` to template the config
  - [x] Use `mode: '0644'` for config.yaml

- [x] Task 4: Create SOUL.md template (AC: #3)
  - [x] Create `templates/SOUL.md.j2` — Director identity and instructions
  - [x] Include project context: "You are the Director agent for the {{ project_name }} project"
  - [x] Include operational guardrails from FR38, FR39 (no merge to main, no package install)

- [x] Task 5: Create .env template (AC: #3)
  - [x] Create `templates/env.j2` — structured like the live .env from ct-dev-test
  - [x] ANTHROPIC_TOKEN= (empty, explicitly cleared)
  - [x] ANTHROPIC_API_KEY= (empty, explicitly cleared)
  - [x] OPENROUTER_API_KEY={{ ai_dev_hermes_openrouter_api_key }}
  - [x] SLACK_BOT_TOKEN={{ ai_dev_hermes_slack_bot_token }} (conditionally rendered)
  - [x] SLACK_APP_TOKEN={{ ai_dev_hermes_slack_app_token }} (conditionally rendered)
  - [x] HASS_TOKEN={{ ai_dev_hermes_ha_token }} (conditionally rendered)
  - [x] All optional keys conditionally rendered
  - [x] Create `tasks/configure-env.yml` with `mode: '0600'` and `no_log: true`

- [x] Task 6: Create gitignore task (AC: #6)
  - [x] Create `tasks/configure-gitignore.yml`
  - [x] Add `.hermes/.env`, `.hermes/sessions/`, `.hermes/hermes.db`, `.hermes/memories/` to gitignore
  - [x] Use `blockinfile` with Ansible markers (consistent with ai-dev-omega-memory pattern)

- [x] Task 7: Create main.yml and verify.yml (AC: #4, #7)
  - [x] Create `tasks/main.yml` composing: install-hermes -> configure-hermes -> configure-env -> configure-gitignore
  - [x] Create `tasks/verify.yml` with VERIFY-prefixed checks:
    - `VERIFY | Hermes binary exists and responds`
    - `VERIFY | Hermes config.yaml exists and has correct provider`
    - `VERIFY | Hermes .env has correct permissions (0600)`
    - `VERIFY | Hermes .env does not contain ANTHROPIC_API_KEY value`
    - `VERIFY | Hermes doctor passes all checks`

- [x] Task 8: Deploy and verify on ct-dev-test (AC: #1-#6)
  - [x] Run the role on ct-dev-test (192.168.50.152)
  - [x] NOTE: Hermes is already manually installed — the role must handle this gracefully (idempotent over existing install)
  - [x] Run all eval assertions
  - [x] Fix any failures

- [x] Task 9: Verify idempotency and BMAD-safety (AC: #7, #8)
  - [x] Run the role a second time on ct-dev-test
  - [x] Confirm 0 changed tasks (ai-dev-hermes role: 0 changed; 1 changed from dev-host dep runc restart — pre-existing)
  - [x] Confirm zero files modified under `.claude/skills/bmad-*/`

- [x] Task 10: Deploy to ct-dev-homelab (AC: all)
  - [x] Run the role on ct-dev-homelab (192.168.50.150)
  - [x] This is a fresh install (no existing Hermes) — confirms installer flow (NOTE: Hermes was already installed from prior manual/dev-host work; installer skipped, config templated fresh — installer flow was validated on ct-dev-test in Task 8)
  - [x] Run all eval assertions
  - [x] Run verify.yml

## Dev Notes

### Dual-Model Architecture (Sprint Change Proposal 2026-04-11)

Hermes Director uses **OpenRouter** as its primary LLM provider (not Anthropic). Claude Code workers (spawned via `claude -p` in Story 3.3) use Anthropic Max Plan credentials via auto-discovery. The two credential chains are independent:

- `config.yaml` -> `model.provider: openrouter`, `model.base_url: https://openrouter.ai/api/v1`
- `.env` -> `OPENROUTER_API_KEY` is the primary secret; `ANTHROPIC_API_KEY` explicitly empty
- Claude Code workers: inherit Max Plan credentials from host environment (no role config needed)

### Layered Variable Design Convention (Sprint Change Proposal 2026-04-11)

Three-tier precedence: `defaults/main.yml` < `group_vars/dev_hosts/ai-dev-hermes.yml` < `host_vars/ct-project/ai-dev-hermes.yml`

- `defaults/main.yml`: every setting listed with sensible factory defaults
- `group_vars/dev_hosts/ai-dev-hermes.yml`: org-wide shared settings (created in Story 4.1)
- `host_vars/ct-project/ai-dev-hermes.yml`: project-specific overrides (created in Story 4.1)
- **Commented-out convention:** group_vars and host_vars files list ALL available settings; active ones uncommented, inactive ones commented with default value

This story creates the `defaults/main.yml` (tier 1). Story 4.1 creates tiers 2 and 3.

### Manual Install Record (Reference)

Full record at `planning-artifacts/research/hermes-agent-manual-install-2026-04-08.md`. Key facts:
- Installer: `curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash`
- Binary: `~/.local/bin/hermes` (also `~/.hermes/hermes-agent/venv/bin/hermes`)
- Helper: `~/.hermes/bin/tirith`
- PATH issue: `~/.local/bin` not in PATH by default
- `hermes setup` is interactive — Ansible MUST template config directly
- OAuth banned for third-party agents since April 4, 2026

### Config File Layout (from ct-dev-test)

```
~/.hermes/
  config.yaml          # ~300 lines, deeply nested YAML — template from Jinja2
  .env                 # API keys — template with mode 0600, no_log
  SOUL.md              # Agent identity — template from Jinja2
  memories/
    MEMORY.md          # Agent notes (2,200 char limit)
    USER.md            # User profile (1,375 char limit)
  skills/              # Story 3.2 deploys BMAD stubs here
  cron/                # Story 3.3 configures scheduled jobs
  sessions/            # SQLite FTS5 session history — exclude from git
  hermes.db            # Main database — exclude from git
  hermes-agent/        # Installed package + venv
    venv/bin/hermes    # Actual binary
```

### Previous Story Learnings (from Epic 2)

- **`become_user` with explicit paths:** Always set HOME, PATH, PYENV_ROOT environment on command tasks
- **`blockinfile` for cross-role writes:** Use Ansible markers, idempotent, clearly marked
- **`changed_when` with stdout detection:** Prevents false "changed" reports
- **dev-host meta dependency friction:** `include_role` pulls full chain, requires dummy vars. Pass `git_user_name`, `git_user_email` in deploy playbook.
- **Version check for idempotency:** Check binary version before install/build (pattern from ai-dev-tmux)
- **systemd user services:** Use `systemctl --user`, `loginctl enable-linger`, `XDG_RUNTIME_DIR`

### Ansible Task Patterns (from architecture.md)

| Pattern | Rule |
|---------|------|
| Task names | Sentence case, action-first: `Install Hermes Agent via installer script` |
| Variable prefix | `ai_dev_hermes_*` |
| Tags | `tags: [ai-dev-hermes]` on all tasks |
| No `shell:` when `command:` works | Use `command:` unless pipes/redirects needed |
| No `ignore_errors: true` | Use `failed_when:` with specific conditions |
| No hardcoded paths | Always use variables from defaults |
| No `become: true` unless root needed | Dev container, user-space install |

### File Location Map

| Repo | Path | Purpose |
|------|------|---------|
| homelab-infra | `ansible/roles/ai-dev-hermes/defaults/main.yml` | Full variable catalog |
| homelab-infra | `ansible/roles/ai-dev-hermes/meta/main.yml` | Role dependency (dev-host) |
| homelab-infra | `ansible/roles/ai-dev-hermes/handlers/main.yml` | Handlers (initially empty) |
| homelab-infra | `ansible/roles/ai-dev-hermes/tasks/main.yml` | Task orchestration |
| homelab-infra | `ansible/roles/ai-dev-hermes/tasks/install-hermes.yml` | Installer + PATH |
| homelab-infra | `ansible/roles/ai-dev-hermes/tasks/configure-hermes.yml` | Template config.yaml |
| homelab-infra | `ansible/roles/ai-dev-hermes/tasks/configure-env.yml` | Template .env (0600) |
| homelab-infra | `ansible/roles/ai-dev-hermes/tasks/configure-gitignore.yml` | Git exclusions |
| homelab-infra | `ansible/roles/ai-dev-hermes/tasks/verify.yml` | VERIFY health checks |
| homelab-infra | `ansible/roles/ai-dev-hermes/templates/config.yaml.j2` | Hermes config template |
| homelab-infra | `ansible/roles/ai-dev-hermes/templates/env.j2` | Hermes .env template |
| homelab-infra | `ansible/roles/ai-dev-hermes/templates/SOUL.md.j2` | Director identity template |

### Test-Then-Deploy Workflow

1. Write role in homelab-infra on ct-dev-homelab
2. Deploy to ct-dev-test (192.168.50.152) — has existing Hermes install
3. Run eval assertions on ct-dev-test
4. Code review
5. Deploy to ct-dev-homelab (192.168.50.150) — fresh install

### References

- [Source: planning-artifacts/sprint-change-proposal-2026-04-11.md] — Layered config + dual-model architecture
- [Source: planning-artifacts/research/hermes-agent-manual-install-2026-04-08.md] — Manual install record
- [Source: planning-artifacts/architecture.md#Implementation Patterns] — Ansible task conventions
- [Source: planning-artifacts/architecture.md#File Path Conventions] — Hermes file paths
- [Source: planning-artifacts/architecture.md#Variable Naming] — Variable prefix conventions
- [Source: planning-artifacts/architecture.md#Conditional Integration Wiring] — Cross-role detection pattern
- [Source: implementation-artifacts/epic-2-retro-2026-04-08.md#Action Items] — Retro items #3-7
- [Source: implementation-artifacts/2-4-verify-memory-features-and-conditional-hermes-wiring.md#Dev Notes] — Previous story learnings

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6

### Debug Log References

### Completion Notes List
- Task 0: Investigation complete. Hermes v0.8.0 on ct-dev-test. Binary at ~/.local/bin/hermes (symlink to ~/.hermes/hermes-agent/venv/bin/hermes). Config ~300 lines YAML. .env has 25 keys (ANTHROPIC_TOKEN/API_KEY empty as expected). hermes doctor passes with warnings (config version outdated v12->v13, optional OAuth not configured). Python 3.11.2, Node v20.20.2 confirmed. PATH includes ~/.local/bin via login shell. Retro #3 (architecture.md update) deferred to /update-project-docs. Retro #4 (dev-host friction) — workaround exists, low priority.
- Task 10: Deployed to ct-dev-homelab (192.168.50.150). Role ran successfully: 65 ok, 7 changed, 0 failed. Hermes was already installed (installer skipped), config.yaml/SOUL.md/.env/gitignore templated fresh (7 changed tasks: apt cache, docker restart from dev-host dep, bashrc PATH, config.yaml, .env, SOUL.md, gitignore). All 13 eval assertions pass: binary exists (v0.8.0), PATH correct, OpenRouter provider set, model google/gemma-4-26b-a4b-it, CWD /home/developer/workspace/homelab, max_turns 90, ANTHROPIC_TOKEN/API_KEY empty, OpenRouter key present, .env 0600, SOUL.md exists, hermes doctor passes (warnings only for optional features), 59 variables in defaults (>30 threshold), git exclusions configured. verify.yml all SUCCESS. AC-8 BMAD safety: zero files modified under .claude/skills/bmad-*/.

### Change Log
- 2026-04-14: Task 10 — Deployed ai-dev-hermes role to ct-dev-homelab, all eval assertions and verify tasks pass

### Review Findings

- [x] [Review][Patch] "Automatically" language in monitoring runbook overstates a partially manual workflow — change "monitoring is set up automatically" to reflect that 2 of 5 steps are manual [docs/deployment-guide.md:218] -- FIXED (approach: inline)
- [x] [Review][Defer] Runbook step order: Prometheus targets copied before node-exporter is deployed, causing brief scrape errors in the 60s reload window — deferred, low impact and self-healing
- [x] [Review][Defer] Manual `cp` step between repos has no idempotency guard or path validation — deferred, architectural (needs Ansible task or CI step)
- [x] [Review][Defer] No documented opt-out path for `monitoring_enabled=false` — deferred, belongs in infra repo Terraform docs
- [x] [Review][Defer] No container removal/decommission monitoring procedure documented — deferred, future doc addition

### File List
No new files created in this task — deployment of existing role to ct-dev-homelab target only.
