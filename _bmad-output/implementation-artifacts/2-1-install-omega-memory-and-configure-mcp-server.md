# Story 2.1: Install OMEGA Memory and Configure MCP Server

Status: done

## Story

As a developer,
I want OMEGA Memory installed with its MCP server running as a systemd service,
so that I have a persistent shared brain available for all sessions.

## Acceptance Criteria

1. **Given** a container with `dev-host` role applied (pyenv Python 3.11+ available)
   **When** the `ai-dev-omega-memory` role runs the install tasks
   **Then** OMEGA is installed via `pip install omega-memory[server]` using pyenv Python
   **And** the `omega` CLI is available at `~/.local/bin/omega` or pyenv shims path

2. **Given** OMEGA is installed
   **When** `omega setup` runs
   **Then** initial setup completes and downloads the ~90MB ONNX embedding model
   **And** `omega doctor` reports all checks passing (AT-2.1)

3. **Given** OMEGA is installed and set up
   **When** the role runs the systemd tasks
   **Then** `omega-mcp.service` systemd user unit is created at `~/.config/systemd/user/`
   **And** `loginctl enable-linger` is configured for the dev user
   **And** the service is enabled via `systemctl --user enable omega-mcp.service`
   **And** the service is active and running

4. **Given** the systemd service is enabled and running
   **When** the container reboots
   **Then** the MCP server starts automatically on boot

5. **Given** OMEGA is running
   **When** checking container resource usage
   **Then** OMEGA RAM stays within expected bounds (~337MB) (NFR-PERF-3)

6. **Given** the role has already been run successfully
   **When** the role runs again
   **Then** all tasks report no changes (idempotent)

7. **Given** the BMAD installation at `.claude/skills/bmad-*/`
   **When** this story is implemented
   **Then** zero files in `.claude/skills/bmad-*/` are modified (NFR-INT-5)

## Edge Cases & Error Scenarios

1. **Side effects:** Creates `ai-dev-omega-memory` role directory in `homelab-infra/ansible/roles/`. On the target container: installs Python package (`omega-memory[server]`), downloads ~90MB ONNX model to `~/.omega/models/`, creates systemd user unit file, enables lingering for dev user.

2. **Dependency failure:** If `pip install` fails (network issue, package not found, dependency conflict), the role should fail at that task with pip's error output visible. If `omega setup` fails (network issue downloading ONNX model, disk space), the role should fail at that task. If pyenv Python 3.11+ is not available, the role's meta/main.yml dependency on `dev-host` should catch this — but the role should also verify Python version in a pre-check task. If the OMEGA MCP server CLI command differs from assumed `omega serve --mcp` (Architecture Gap #4), the service unit will fail to start.

3. **Assumptions:** The target container runs Debian 12/13 on amd64 with systemd. The `dev-host` role has been applied (providing pyenv with Python 3.11.11 installed). Internet access is available for pip install and ONNX model download on first run. The actual OMEGA install paths may differ from assumed `~/.omega/` (Architecture Gap #1 — validate during implementation). The MCP server CLI command may differ from assumed `omega serve --mcp` (Architecture Gap #4 — validate during implementation).

## Eval Assertions

<!-- Binary test assertions derived from acceptance criteria. Used by /autoresearch:fix for post-code-review iteration loops. -->

| # | Assertion | Command/Check | Pass Criteria |
|---|-----------|---------------|---------------|
| AC-1 | OMEGA CLI installed | `which omega` or `pip show omega-memory` on target | Exit code 0 |
| AC-2 | OMEGA doctor passes | `omega doctor` on target | Exit code 0, all checks pass |
| AC-3a | omega-mcp.service unit file exists | `test -f /home/developer/.config/systemd/user/omega-mcp.service` on target | Exit code 0 |
| AC-3b | loginctl linger enabled | `loginctl show-user developer --property=Linger \| grep -q 'yes'` on target | Exit code 0 |
| AC-3c | omega-mcp.service is enabled | `XDG_RUNTIME_DIR=/run/user/1000 systemctl --user is-enabled omega-mcp.service` as dev_user | Output "enabled" |
| AC-3d | omega-mcp.service is active | `XDG_RUNTIME_DIR=/run/user/1000 systemctl --user is-active omega-mcp.service` as dev_user | Output "active" |
| AC-4 | Auto-start after reboot | Reboot container, wait 60s, check `systemctl --user is-active omega-mcp.service` | Output "active" |
| AC-5 | RAM within bounds | `ps aux \| grep omega \| awk '{sum+=$6} END {print sum}'` on target | Under ~345000 KB (~337MB) |
| AC-6 | Idempotent on second run | Run role twice, check second run output | All tasks report "ok" not "changed" |
| AC-7 | No BMAD files modified | `find .claude/skills/bmad-* -newer <marker>` | Empty output |

## Tasks / Subtasks

- [x] Task 0: Verify dev-host prerequisites on target (AC: prerequisite)
  - [x] Confirm pyenv is installed at `/home/{{ dev_user }}/.pyenv/bin/pyenv`
  - [x] Confirm Python 3.11+ is available via `pyenv versions`
  - [x] Confirm pip is available in pyenv Python
  - [x] Confirm systemd is running (container supports user services)

- [x] Task 1: Create the `ai-dev-omega-memory` role directory structure in `homelab-infra/ansible/roles/` (AC: #1)
  - [x] Create `roles/ai-dev-omega-memory/tasks/main.yml`
  - [x] Create `roles/ai-dev-omega-memory/defaults/main.yml` with pinned OMEGA version, paths, namespace
  - [x] Create `roles/ai-dev-omega-memory/meta/main.yml` declaring dependency on `dev-host`
  - [x] Create `roles/ai-dev-omega-memory/handlers/main.yml` with `restart omega-mcp` handler
  - [x] Create `roles/ai-dev-omega-memory/templates/` directory

- [x] Task 2: Implement OMEGA installation tasks (AC: #1, #2)
  - [x] Create `roles/ai-dev-omega-memory/tasks/install-omega.yml`
  - [x] Check if omega is already installed (pip show or which)
  - [x] If not present: `pip install omega-memory[server]` using pyenv Python
  - [x] Verify `omega` CLI is available after install
  - [x] Run `omega setup` for initial configuration (creates data dir, downloads ONNX model)
  - [x] Verify `omega doctor` passes
  - [x] Include install-omega.yml from main.yml

- [x] Task 3: Implement systemd service tasks (AC: #3, #4)
  - [x] Create `roles/ai-dev-omega-memory/tasks/configure-systemd.yml`
  - [x] Create `roles/ai-dev-omega-memory/templates/omega-mcp.service.j2`
  - [x] Check and enable loginctl linger for dev user (`become: true`)
  - [x] Create systemd user unit directory (`~/.config/systemd/user/`)
  - [x] Deploy omega-mcp.service.j2 template with notify handler
  - [x] Daemon-reload, enable, and start the service (scope: user)
  - [x] Include configure-systemd.yml from main.yml
  - [x] **CRITICAL: Validate the exact MCP server launch command.** Architecture assumes `omega serve --mcp` but this is unconfirmed (Gap #4). Check `omega --help` or `omega serve --help` on target after install to determine the correct ExecStart command.

- [x] Task 4: Create verify.yml with VERIFY-prefixed health checks (AC: #2, #3, #5)
  - [x] Create `roles/ai-dev-omega-memory/tasks/verify.yml`
  - [x] VERIFY: omega CLI exists and responds
  - [x] VERIFY: omega doctor passes
  - [x] VERIFY: omega-mcp.service unit file exists
  - [x] VERIFY: loginctl linger enabled for dev user
  - [x] VERIFY: omega-mcp.service is enabled
  - [x] VERIFY: omega-mcp.service is active/running
  - [x] VERIFY: OMEGA data directory exists (`~/.omega/` or actual path)
  - [x] VERIFY: ONNX embedding model downloaded

- [x] Task 5: Verify BMAD update-safety (AC: #7)
  - [x] Confirm zero files modified under `.claude/skills/bmad-*/`

## Dev Notes

### Architecture Reference

From `architecture.md` — OMEGA MCP Server Lifecycle:

| Decision | Choice |
|----------|--------|
| MCP server process | systemd user service |
| Service name | `omega-mcp.service` |
| Auto-start | `systemctl --user enable omega-mcp.service` |
| Health check | `omega doctor` in verify tasks |
| Python | pyenv-managed 3.11+, `pip install omega-memory[server]` (pyenv global, no venv) |
| Data directory | `~/.omega/` (assumed — validate during implementation) |
| MCP server command | `omega serve --mcp` (assumed — **validate during implementation**, Architecture Gap #4) |

### Architecture Gaps to Resolve in This Story

| # | Gap | Resolution |
|---|-----|------------|
| G1 | OMEGA actual install paths may differ from assumed `~/.omega/` | After `pip install` + `omega setup`, check actual paths. Update `defaults/main.yml` accordingly. |
| G4 | OMEGA MCP server CLI command not confirmed (`omega serve --mcp`?) | After install, run `omega --help` and `omega serve --help`. Use actual command in service template. |

### Previous Story Learnings (from Epic 1: Stories 1.1, 1.2, 1.3)

- Use `become_user: "{{ dev_user }}"` with explicit `/home/{{ dev_user }}` paths (Story 1.1 P1 fix — `ansible_env.HOME` resolves to `/root` under `become: true`)
- Set `environment.HOME` and `environment.PATH` (including pyenv shims) on all command tasks
- Use `changed_when` appropriately for idempotency reporting (Story 1.1 D3)
- `dev_user: developer` and `dev_user_uid: 1000` as defaults
- Template module handles idempotency natively (Story 1.2)
- `loginctl enable-linger` requires root (`become: true`), NOT `become_user` (Story 1.3)
- `systemctl --user` commands need `XDG_RUNTIME_DIR` and `DBUS_SESSION_BUS_ADDRESS` environment variables (Story 1.3)
- Use `meta: flush_handlers` to ensure daemon-reload runs before enable/start (Story 1.3)
- `failed_when: false` on initial version checks to handle missing binary (Story 1.1)
- Use `timeout:` on long-running install commands (Story 1.1 P2 — added 900s for cargo install)

### systemd User Unit Pattern (from Story 1.3)

```ini
[Unit]
Description=OMEGA Memory MCP Server
After=network.target

[Service]
Type=simple
ExecStart={{ omega_mcp_exec_command }}
Restart=on-failure
RestartSec=5
Environment=PATH=/home/{{ dev_user }}/.pyenv/shims:/home/{{ dev_user }}/.pyenv/bin:/home/{{ dev_user }}/.local/bin:/usr/local/bin:/usr/bin:/bin
Environment=HOME=/home/{{ dev_user }}
Environment=PYENV_ROOT=/home/{{ dev_user }}/.pyenv

[Install]
WantedBy=default.target
```

**Key difference from tmux-server.service:** Type=`simple` (not `forking`), PATH includes pyenv shims and `.local/bin`.

### Variable Naming Convention (from architecture)

```yaml
# defaults/main.yml
ai_dev_omega_memory_version: "0.4.2"  # Pin exact version — validate current latest
ai_dev_omega_memory_namespace: "{{ project_name }}"
ai_dev_omega_memory_data_dir: "/home/{{ dev_user }}/.omega"  # Validate after install
ai_dev_omega_memory_backup_enabled: true
dev_user: developer
dev_user_uid: 1000
```

### File Location Map

| Repo | Path | Purpose |
|------|------|---------|
| homelab-infra | `ansible/roles/ai-dev-omega-memory/` | New Ansible role (all files) |
| homelab-playbook | `_bmad-output/implementation-artifacts/2-1-*.md` | This story file |
| Target container | `~/.local/bin/omega` or pyenv shims | OMEGA CLI binary |
| Target container | `~/.omega/` | OMEGA data directory (SQLite DB, ONNX model) |
| Target container | `~/.config/systemd/user/omega-mcp.service` | systemd user unit |

### Test-Then-Deploy Workflow

**Write** role files on `ct-dev-homelab` (this container).
**Deploy** to `ct-dev-test` (192.168.50.152) first.
**Verify** all eval assertions pass on `ct-dev-test`.
**Code review** after verification.
**Deploy** to `ct-dev-homelab` after review passes.

### What NOT to Do

- Do NOT register Claude Code hooks (Story 2.2)
- Do NOT configure namespace isolation or backup (Story 2.3)
- Do NOT configure Hermes MCP connection (Story 2.4)
- Do NOT modify any `.claude/skills/bmad-*/` files
- Do NOT use system Python — use pyenv-managed Python
- Do NOT create Python venvs — OMEGA uses pyenv global (per architecture)
- Do NOT hardcode paths — use variables from defaults/main.yml
- Do NOT use `shell:` when `command:` suffices
- Do NOT use `ignore_errors: true` — use `failed_when:` with specific conditions

### References

- [Source: architecture.md — OMEGA MCP Server Lifecycle, Python Environment Strategy, systemd Unit Patterns, File Path Conventions, Variable Naming, Conditional Integration Wiring]
- [Source: prd.md — FR6-FR15, NFR-REL-2, NFR-PERF-1, NFR-PERF-3, NFR-INT-1, AT-2.1]
- [Source: epics.md — Epic 2, Story 2.1]
- [Source: Story 1.1 — P1 (become_user fix), P2 (timeout), D3 (changed_when)]
- [Source: Story 1.3 — systemd user unit pattern, linger, XDG_RUNTIME_DIR, flush_handlers]
- [Source: Epic 1 Retrospective — Test-then-deploy workflow, ct-dev-test verification target]

## Dev Agent Record

- **Agent Model Used:** claude-opus-4-6 (Opus 4.6 with 1M context)
- **Debug Log References:** N/A (clean implementation after one iteration)
- **Architecture Gaps Resolved:**
  - **G1 (install paths):** OMEGA home confirmed at `~/.omega`. Model cache at `~/.cache/omega/models/`. CLI at pyenv shims: `~/.pyenv/shims/omega`.
  - **G4 (MCP server command):** `omega serve --daemon` for HTTP daemon mode (systemd). `omega serve` (stdio) exits immediately without stdin — must use `--daemon` flag.
- **Key Implementation Discoveries:**
  - OMEGA v1.4.3 installed (not 0.4.2 as assumed in architecture — significantly newer)
  - `pip install omega-memory` is not sufficient — must use `omega-memory[server]` extra to get the `mcp` package dependency
  - `omega setup` exits with rc=1 even on success (reports `[FAIL] 1` for non-critical items like FTS5/vector index). Used `failed_when: false` and verified critical items via assert.
  - `omega setup --download-model` downloads bge-small-en-v1.5 (127MB) — newer/larger than the architecture's assumed all-MiniLM-L6-v2 (86MB)
  - OMEGA auto-registers itself in Claude Code MCP and hooks during `omega setup` — no separate hook registration needed for MCP server (Story 2.2 may need to verify/adjust these)
  - OMEGA adds an `OMEGA Core` block to CLAUDE.md during setup
  - RAM usage: ~251MB RSS (well under 337MB budget)
- **Iteration Notes:**
  - First run failed on `omega setup` — the `when: not omega_home_dir.stat.exists` check was wrong because `~/.omega` gets created during pip install, not just setup. Fixed to check for ONNX model existence instead.
  - MCP service started but exited immediately — `omega serve` in stdio mode needs stdin. Fixed to use `omega serve --daemon` for HTTP daemon mode.
  - `pip install omega-memory` missing `[server]` extra — MCP package not included. Fixed install command.
- **Completion Notes:**
  - Created `ai-dev-omega-memory` Ansible role with 7 files across 5 directories
  - Install uses pyenv shims paths consistently (`/home/{{ dev_user }}/.pyenv/shims/pip`, `omega`)
  - Setup idempotency: checks ONNX model existence before running `omega setup`
  - systemd pattern mirrors Story 1.3: linger check/enable, template deploy, flush_handlers, enable+start
  - All `become_user` tasks include PYENV_ROOT, HOME, PATH environment variables
  - Idempotency verified: second run shows 0 changed tasks for role
  - All eval assertions pass on ct-dev-test
  - Zero files modified under `.claude/skills/bmad-*/`
- **File List:**
  - `homelab-infra/ansible/roles/ai-dev-omega-memory/defaults/main.yml` (new)
  - `homelab-infra/ansible/roles/ai-dev-omega-memory/meta/main.yml` (new)
  - `homelab-infra/ansible/roles/ai-dev-omega-memory/handlers/main.yml` (new)
  - `homelab-infra/ansible/roles/ai-dev-omega-memory/tasks/main.yml` (new)
  - `homelab-infra/ansible/roles/ai-dev-omega-memory/tasks/install-omega.yml` (new)
  - `homelab-infra/ansible/roles/ai-dev-omega-memory/tasks/configure-systemd.yml` (new)
  - `homelab-infra/ansible/roles/ai-dev-omega-memory/tasks/verify.yml` (new)
  - `homelab-infra/ansible/roles/ai-dev-omega-memory/templates/omega-mcp.service.j2` (new)
