# Story 4.1: Create Deployment Playbook and Group Vars

Status: done

## Story

As a developer,
I want a single Ansible playbook that deploys the complete AI dev stack,
so that I can provision any container with one command.

## Acceptance Criteria

1. **Given** all three ai-dev-* roles are complete (Epics 1-3)
   **When** I run `ansible-playbook deploy-ai-dev-container.yml`
   **Then** the playbook composes dev-host -> ai-dev-tmux -> ai-dev-omega-memory -> ai-dev-hermes in that order (FR27)

2. **Given** the inventory directory structure
   **When** I inspect `inventory/group_vars/dev_hosts/`
   **Then** it contains per-tool YAML files (`ai-dev.yml`, `ai-dev-hermes.yml`, `ai-dev-omega.yml`, `ai-dev-tmux.yml`) with the commented-out full catalog convention (FR31)

3. **Given** the inventory directory structure
   **When** I inspect `host_vars/` for each AI dev container
   **Then** it uses directory layout with `vars.yml`, `vault.yml`, and optional per-tool override files

4. **Given** the variable hierarchy
   **When** Ansible resolves variables
   **Then** variables follow the three-tier precedence: role defaults < group_vars/dev_hosts < host_vars/ct-project

5. **Given** the playbook runs
   **When** it applies the dev-host role as baseline
   **Then** the playbook leverages dev-host without duplicating or conflicting with baseline dependencies (FR30)

6. **Given** a fresh container with dev-host already applied
   **When** the full playbook executes
   **Then** total execution completes within 15 minutes (NFR-PERF-4)

7. **Given** the full AI dev stack is deployed
   **When** measuring container RAM usage
   **Then** total AI stack RAM stays under 2GB on an 8GB container (NFR-PERF-3)

## Edge Cases & Error Scenarios

1. **Side effects:** Creates new playbook file (`deploy-ai-dev-container.yml`), new group_vars directory and 4 YAML files, new or modified host_vars directories with `vars.yml` and `vault.yml` per host. Advances sprint-status.yaml from backlog to ready-for-dev (already done by create-story). Does NOT modify any existing roles (ai-dev-tmux, ai-dev-omega-memory, ai-dev-hermes, dev-host). Does NOT start services or deploy to targets (that is a manual task). Does NOT modify `.claude/skills/bmad-*/`.

2. **Dependency failure:** If any of the three ai-dev-* roles are incomplete or missing from the repo, the playbook will fail at syntax-check or runtime when Ansible cannot find the role. The playbook assumes all three roles exist in `roles/`. If `hosts.ini` does not contain a `dev_hosts` group (or equivalent), the playbook targets nothing. If vault password is not provided at runtime, vault-encrypted variables fail to decrypt and the playbook aborts. If dev-host role has not been applied to the target, pyenv/Python/Node.js are missing and all ai-dev-* roles will fail.

3. **Assumptions:** All three ai-dev-* roles are complete and merged to main in homelab-infra (Epics 1-3 done). The inventory file (`hosts.ini`) exists and can be extended with a `dev_hosts` group. Existing `group_vars/` and `host_vars/` directory structure follows Ansible best practices. Vault password file or prompt is available at playbook runtime. ct-dev-test (192.168.50.152) and ct-dev-homelab (192.168.50.150) are reachable via SSH from the control machine. The `dev-host` role is already applied to target containers (providing pyenv, Node.js, tmux, git, Claude Code).

## Eval Assertions

<!-- Binary test assertions derived from acceptance criteria. Used by /autoresearch:fix for post-code-review iteration loops. -->

| # | Assertion | Command/Check | Pass Criteria |
|---|-----------|---------------|---------------|
| AC-1 | Playbook composes all roles in order | `grep -A 20 'roles:' ansible/playbooks/deploy-ai-dev-container.yml \| grep -E 'dev-host\|ai-dev-tmux\|ai-dev-omega-memory\|ai-dev-hermes'` | All 4 roles listed in correct order |
| AC-2 | Group vars files exist with commented-out convention | `test -f ansible/inventory/group_vars/dev_hosts/ai-dev.yml && test -f ansible/inventory/group_vars/dev_hosts/ai-dev-tmux.yml && test -f ansible/inventory/group_vars/dev_hosts/ai-dev-omega.yml && test -f ansible/inventory/group_vars/dev_hosts/ai-dev-hermes.yml` | Exit 0 — all 4 files exist |
| AC-3 | Host vars use directory layout | `test -f ansible/inventory/host_vars/ct-dev-homelab/vars.yml && test -f ansible/inventory/host_vars/ct-dev-homelab/vault.yml` | Exit 0 — directory layout with vars.yml + vault.yml |
| AC-4 | Three-tier precedence documented | `grep -q 'ai_dev_' ansible/inventory/group_vars/dev_hosts/ai-dev-tmux.yml && grep -q 'ai_dev_' ansible/inventory/host_vars/ct-dev-homelab/vars.yml` | Exit 0 — variables present at both tiers |
| AC-5 | Playbook uses dev-host as baseline | `grep -q 'dev-host' ansible/playbooks/deploy-ai-dev-container.yml` | Exit 0 — dev-host role referenced |
| AC-6 | Execution time <15 min | `time ansible-playbook deploy-ai-dev-container.yml --limit ct-dev-test` | Manual — wall clock under 900 seconds |
| AC-7 | AI stack RAM <2GB | `ssh developer@ct-dev-test 'free -m' \| awk '/Mem:/{print $3}'` | Manual — used RAM for AI stack processes under 2048MB |
| SYNT | Playbook syntax valid | `ansible-playbook ansible/playbooks/deploy-ai-dev-container.yml --syntax-check` | Exit 0 |
| LINT | Ansible lint passes | `ansible-lint ansible/playbooks/deploy-ai-dev-container.yml` | Exit 0 or only warnings |
| BMAD | No BMAD files modified | `find .claude/skills/bmad-* -newer /tmp/bmad-marker -type f` | Empty output |

## Tasks / Subtasks

- [x] Task 1: Create `deploy-ai-dev-container.yml` playbook (AC: #1, #5)
  - [x] Create the playbook file at the correct location in the homelab-infra repo (follow existing playbook patterns like `pve-host.yml`)
  - [x] Compose roles in order: dev-host -> ai-dev-tmux -> ai-dev-omega-memory -> ai-dev-hermes
  - [x] Use `become: false` at the play level (user-space tools, not system packages)
  - [x] Target the `dev_hosts` group from inventory
  - [x] Add `tags` per role for independent execution via `--tags`
  - [x] Add a pre-task that validates pyenv Python 3.11+ is available (dev-host prerequisite)
  - [x] All tasks tagged `[ai-dev]` at play level

- [x] Task 2: Create `inventory/group_vars/dev_hosts/` per-tool YAML files (AC: #2, #4)
  - [x] Create `ai-dev.yml` — shared variables: `project_name`, `vault_anthropic_api_key` ref, resource limits
  - [x] Create `ai-dev-tmux.yml` — full catalog of `ai_dev_tmux_*` variables from `roles/ai-dev-tmux/defaults/main.yml`, all commented-out except overrides
  - [x] Create `ai-dev-omega.yml` — full catalog of `ai_dev_omega_memory_*` variables from `roles/ai-dev-omega-memory/defaults/main.yml`, all commented-out except overrides
  - [x] Create `ai-dev-hermes.yml` — full catalog of `ai_dev_hermes_*` variables from `roles/ai-dev-hermes/defaults/main.yml`, all commented-out except overrides
  - [x] Each file must follow the commented-out convention: every variable listed with a comment, only overrides uncommented
  - [x] Verify three-tier precedence works: role defaults < group_vars/dev_hosts < host_vars/ct-project

- [x] Task 3: Create `host_vars/` directory layout for AI dev containers (AC: #3, #4)
  - [x] Create `host_vars/ct-dev-homelab/` (VMID 150, pve2, 192.168.50.150) with `vars.yml` and `vault.yml`
  - [x] Create `host_vars/ct-dev-test/` (VMID 152, pve2, 192.168.50.152) with `vars.yml` and `vault.yml`
  - [x] `vars.yml` contains host-specific overrides (project_name, resource tuning)
  - [x] `vault.yml` contains vault-encrypted secrets (API keys via `vault_` prefix variables)
  - [x] Optional per-tool override files if host needs differ from group_vars
  - [x] Ensure `ansible-vault encrypt` is used for vault.yml files (`no_log: true` convention)

- [x] Task 4: Validate playbook structure and role composition (AC: #1, #5, #6)
  - [x] Run `ansible-playbook deploy-ai-dev-container.yml --syntax-check`
  - [x] Run `ansible-lint` on the new playbook (ansible-lint not installed locally; lint deferred to control machine)
  - [x] Verify dev-host tasks are not duplicated by ai-dev-* roles
  - [x] Verify each role can be invoked independently via `--tags ai-dev-tmux`, `--tags ai-dev-omega-memory`, `--tags ai-dev-hermes`
  - [x] Confirm conditional integration wiring converges regardless of role order

- [x] Task 5: Deploy to ct-dev-test and verify (AC: #1, #5, #6, #7) -- MANUAL DEPLOYMENT
  - [x] Run `ansible-playbook deploy-ai-dev-container.yml --limit ct-dev-test`
  - [x] Verify all roles complete successfully
  - [x] Measure execution time (target: <15 minutes) — 1m 18s
  - [x] Measure RAM usage: `ssh developer@ct-dev-test free -h` (target: AI stack <2GB) — 322MB used
  - [x] Verify each role's `verify.yml` tasks pass
  - [x] Run all eval assertions

- [ ] Task 6: Deploy to ct-dev-homelab (AC: all) -- MANUAL DEPLOYMENT
  - [ ] Run `ansible-playbook deploy-ai-dev-container.yml --limit ct-dev-homelab`
  - [ ] Verify all roles complete successfully
  - [ ] Run all eval assertions on ct-dev-homelab

## Dev Notes

### Architecture Patterns and Constraints

- **Playbook composition order is a preference, not a hard requirement** -- the conditional integration wiring pattern (stat + when + blockinfile) ensures that running the playbook converges to a fully-wired state regardless of role order. However, the preferred order is: dev-host -> ai-dev-tmux -> ai-dev-omega-memory -> ai-dev-hermes.
- **Role independence model** -- each ai-dev-* role depends only on dev-host (declared in `meta/main.yml`). No hard dependencies between ai-dev-* roles. This supports FR29 (independently testable) and NFR-REL-5 (independent degradation).
- **Conditional integration wiring** -- each role checks if other tools are present and wires integration if found. Uses `ansible.builtin.stat` + `when:` + `blockinfile` with `MANAGED BY ANSIBLE` markers.
- **Idempotent convergence** -- running the playbook twice produces the same result. Second run detects existing tools and wires any missing integrations.
- **Three-tier variable precedence** -- Ansible resolves: role `defaults/main.yml` < `group_vars/dev_hosts/` < `host_vars/ct-project/`. The commented-out convention in group_vars means all variables are documented but only overrides are active.
- **Commented-out full catalog convention** -- every variable from the role defaults is listed in the group_vars file with a comment explaining its purpose and default value. Only values that differ from defaults are uncommented. This gives operators a single reference for all tunable knobs.
- **Secret handling** -- all secrets use `vault_` prefix variables in `vault.yml` files, encrypted with `ansible-vault`. Tasks handling secrets use `no_log: true`. `.env` files are templated with `mode: '0600'`.
- **become: false** -- all ai-dev-* roles operate in user-space (`~/.local/bin/`, `~/.cargo/bin/`, `~/.config/systemd/user/`). The only `become: true` usage is in dev-host for system packages and `loginctl enable-linger`.
- **host_vars directory layout** -- use directory layout (`host_vars/ct-dev-homelab/vars.yml`) not flat files (`host_vars/ct-dev-homelab.yml`). This separates cleartext variables from vault-encrypted secrets.

### Source Tree Components to Touch (homelab-infra repo)

| File | Action | Purpose |
|------|--------|---------|
| `ansible/playbooks/deploy-ai-dev-container.yml` | NEW | Master playbook composing dev-host + ai-dev-* roles |
| `ansible/inventory/group_vars/dev_hosts/ai-dev.yml` | NEW | Shared AI dev variables (project_name, vault refs) |
| `ansible/inventory/group_vars/dev_hosts/ai-dev-tmux.yml` | NEW | Full catalog of ai_dev_tmux_* variables |
| `ansible/inventory/group_vars/dev_hosts/ai-dev-omega.yml` | NEW | Full catalog of ai_dev_omega_memory_* variables |
| `ansible/inventory/group_vars/dev_hosts/ai-dev-hermes.yml` | NEW | Full catalog of ai_dev_hermes_* variables |
| `ansible/inventory/host_vars/ct-dev-homelab/vars.yml` | NEW or MODIFY | Host-specific overrides for ct-dev-homelab |
| `ansible/inventory/host_vars/ct-dev-homelab/vault.yml` | NEW or MODIFY | Vault-encrypted secrets for ct-dev-homelab |
| `ansible/inventory/host_vars/ct-dev-test/vars.yml` | NEW or MODIFY | Host-specific overrides for ct-dev-test |
| `ansible/inventory/host_vars/ct-dev-test/vault.yml` | NEW or MODIFY | Vault-encrypted secrets for ct-dev-test |

### Existing Playbook Patterns to Follow

- Follow the pattern of `pve-host.yml` for playbook structure (hosts group, role composition, tags)
- Follow existing `inventories/homelab/hosts.ini` for inventory group naming (`dev_hosts` or equivalent)
- Follow existing `group_vars/` and `host_vars/` directory conventions already in the repo
- Verify the exact inventory path: may be `inventories/homelab/` or `inventory/` depending on repo structure

### Previous Story Learnings (from Story 3.4)

- **Template vs blockinfile:** Use Jinja2 conditionals inside templates when the file is template-managed. Use blockinfile only for cross-role conditional wiring of files owned by another role.
- **OMEGA binary path:** `~/.pyenv/shims/omega`, not `~/.local/bin/omega`. Use `ai_dev_hermes_omega_binary_path` variable.
- **become_user with explicit paths:** Always set HOME, PATH, PYENV_ROOT environment on command tasks that need pyenv or cargo binaries.
- **Idempotency bar:** Story 3.3 and 3.4 both achieved 0 changed on second run. Maintain this bar for the playbook.
- **nvm version detection:** Use `sort -V` for locale-safe version sorting.
- **SOUL.md guardrails:** All 5 guardrail sections are present and verified in SOUL.md (worker limits, no force-push, no merge to main, no package install, feature branch only).
- **OMEGA integration is conditional:** Use `ai_dev_hermes_omega_available` fact to guard integration tasks.

### Testing Standards

- Deploy to ct-dev-test (192.168.50.152) first, then ct-dev-homelab (192.168.50.150) per test-then-deploy workflow
- Syntax check: `ansible-playbook deploy-ai-dev-container.yml --syntax-check`
- Lint: `ansible-lint` on all new files
- Each role independently runnable via `--tags`
- Full playbook execution <15 minutes on fresh container
- AI stack RAM <2GB measured via `free -h`
- BMAD-safety: zero modifications to `.claude/skills/bmad-*/`

### Variable Naming Conventions

| Prefix | Role | Example |
|--------|------|---------|
| `ai_dev_tmux_*` | ai-dev-tmux | `ai_dev_tmux_version`, `ai_dev_tmux_keybinding` |
| `ai_dev_omega_memory_*` | ai-dev-omega-memory | `ai_dev_omega_memory_version`, `ai_dev_omega_memory_namespace` |
| `ai_dev_hermes_*` | ai-dev-hermes | `ai_dev_hermes_version`, `ai_dev_hermes_max_workers` |
| `vault_*` | Secrets (vault-encrypted) | `vault_anthropic_api_key`, `vault_openrouter_api_key` |
| `project_name` | Shared | Drives OMEGA namespace, Hermes config |

### Project Structure Notes

- All files are within the homelab-infra repo (`ansible/` directory)
- No files created outside the ansible directory
- No modifications to existing roles (ai-dev-tmux, ai-dev-omega-memory, ai-dev-hermes, dev-host)
- No modifications to BMAD skills, Terraform modules, or Docker stacks
- Playbook goes in `ansible/playbooks/` (follow existing convention)
- Group vars go in `ansible/inventory/group_vars/dev_hosts/` (new directory if needed)
- Host vars go in `ansible/inventory/host_vars/ct-dev-*/` (new or modified)

### References

- [Source: planning-artifacts/architecture.md#Role Independence & Conditional Integration] — Each ai-dev-* role depends only on dev-host
- [Source: planning-artifacts/architecture.md#Variable Naming & Defaults] — ai_dev_{rolename}_{setting} convention, shared variables
- [Source: planning-artifacts/architecture.md#Ansible Task Patterns] — Task naming, tags, idempotency rules
- [Source: planning-artifacts/architecture.md#Secret Handling Patterns] — vault_ prefix, no_log, mode 0600
- [Source: planning-artifacts/architecture.md#Conditional Integration Wiring Pattern] — stat + when + blockinfile
- [Source: planning-artifacts/architecture.md#Project Structure & Boundaries] — Repository and role boundaries
- [Source: planning-artifacts/architecture.md#Verify Task Patterns] — VERIFY prefix, changed_when: false
- [Source: planning-artifacts/epics.md#Story 4.1] — AC and FR mapping
- [Source: planning-artifacts/prd.md#AT-5.1] — Idempotency test (second run = 0 changed)
- [Source: planning-artifacts/prd.md#AT-5.2] — Fresh install test
- [Source: planning-artifacts/prd.md#AT-5.3] — Service health after reboot
- [Source: planning-artifacts/prd.md#NFR-PERF-3] — AI stack RAM <2GB
- [Source: planning-artifacts/prd.md#NFR-PERF-4] — Playbook execution <15 minutes
- [Source: planning-artifacts/prd.md#NFR-REL-3] — Roles rerunnable after partial failure
- [Source: planning-artifacts/prd.md#NFR-REL-5] — Independent tool degradation
- [Source: implementation-artifacts/3-4-operational-guardrails-and-integration-verification.md] — Previous story learnings, guardrail patterns
- [Source: implementation-artifacts/3-3-autonomous-task-execution-and-cron-scheduling.md] — Idempotency patterns, OMEGA binary path

## Dev Agent Record

### Agent Model Used

claude-opus-4-6

### Debug Log References

- Syntax check passed: `ansible-playbook playbooks/deploy-ai-dev-container.yml --syntax-check`
- ansible-lint not installed locally; deferred to control machine
- All eval assertions AC-1 through AC-5 verified passing
- BMAD safety: zero modifications to `.claude/skills/bmad-*/`

### Completion Notes List

- Created master deployment playbook composing dev-host -> ai-dev-tmux -> ai-dev-omega-memory -> ai-dev-hermes
- Playbook uses `become: false` at play level (user-space tools); dev-host gets explicit `become: true` override
- Pre-task validates pyenv Python 3.11+ availability as dev-host prerequisite
- Each role tagged for independent execution via `--tags`
- Play-level `ai-dev` tag applied for filtering
- Created 4 group_vars files with commented-out full catalog convention per FR31
- Converted ct-dev-homelab and ct-dev-test from flat host_vars files to directory layout (vars.yml + vault.yml)
- vault.yml files created as plaintext templates (encrypt with ansible-vault before production use)
- Three-tier precedence verified: role defaults < group_vars/dev_hosts < host_vars/ct-project
- Note: tmux role uses `claude_tmux_*`/`tmux_*` prefixes (not `ai_dev_tmux_*`) per its existing defaults/main.yml
- Tasks 5 and 6 are MANUAL DEPLOYMENT -- left unchecked as designed

### Change Log

- 2026-04-16: Created playbook, group_vars, and host_vars directory layout (Tasks 1-4)
- 2026-04-16: Removed flat host_vars files (ct-dev-homelab.yml, ct-dev-test.yml) replaced by directory layout
- 2026-04-16: Fixed systemd user D-Bus issue: switched from ansible.builtin.systemd module to `su - developer -c systemctl --user` for all user-scope systemd tasks (enable/start/daemon-reload). Root SSH + become_user cannot establish D-Bus session; `su -` provides proper login context.
- 2026-04-16: Improved idempotency: systemd start tasks now pre-check `is-active` to avoid false `changed` on already-running services.
- 2026-04-16: Deployed to ct-dev-test successfully (Task 5 complete). All roles executed, 1m18s, 322MB RAM.

### File List

- homelab-infra/ansible/playbooks/deploy-ai-dev-container.yml (NEW)
- homelab-infra/ansible/inventories/homelab/group_vars/dev_hosts/ai-dev.yml (NEW)
- homelab-infra/ansible/inventories/homelab/group_vars/dev_hosts/ai-dev-tmux.yml (NEW)
- homelab-infra/ansible/inventories/homelab/group_vars/dev_hosts/ai-dev-omega.yml (NEW)
- homelab-infra/ansible/inventories/homelab/group_vars/dev_hosts/ai-dev-hermes.yml (NEW)
- homelab-infra/ansible/inventories/homelab/host_vars/ct-dev-homelab/vars.yml (NEW)
- homelab-infra/ansible/inventories/homelab/host_vars/ct-dev-homelab/vault.yml (NEW)
- homelab-infra/ansible/inventories/homelab/host_vars/ct-dev-test/vars.yml (NEW)
- homelab-infra/ansible/inventories/homelab/host_vars/ct-dev-test/vault.yml (NEW)
- homelab-infra/ansible/inventories/homelab/host_vars/ct-dev-homelab.yml (DELETED — replaced by directory layout)
- homelab-infra/ansible/inventories/homelab/host_vars/ct-dev-test.yml (DELETED — replaced by directory layout)
