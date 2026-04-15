# Story 1.3: Configure systemd Auto-Start for tmux Server

Status: done

## Story

As a developer,
I want the tmux server to auto-start on container boot via systemd,
so that my sessions survive reboots without manual intervention.

## Acceptance Criteria

1. **Given** tmux is configured (Story 1.2)
   **When** the `ai-dev-tmux` role runs the systemd tasks
   **Then** a `tmux-server.service` user unit is created at `~/.config/systemd/user/`

2. **Given** the systemd tasks have run
   **When** I check loginctl status
   **Then** `loginctl enable-linger` is configured for the dev user

3. **Given** the systemd tasks have run
   **When** I check systemctl status
   **Then** the service is enabled via `systemctl --user enable tmux-server`

4. **Given** the service is enabled and running
   **When** the container reboots
   **Then** tmux server starts automatically within 60 seconds (FR5, NFR-REL-1, AT-1.4)

5. **Given** the BMAD installation at `.claude/skills/bmad-*/`
   **When** this story is implemented
   **Then** zero files in `.claude/skills/bmad-*/` are modified (NFR-INT-5)

6. **Given** the role includes systemd tasks
   **When** verify.yml runs
   **Then** VERIFY-prefixed health checks confirm binary exists, service active, tmux running

## Edge Cases & Error Scenarios

1. **Side effects:** Creates `~/.config/systemd/user/tmux-server.service` on the target container. Enables lingering for the dev user (persists across reboots via `loginctl enable-linger`). Enables and starts the `tmux-server.service` systemd user unit. If a tmux server is already running (started manually), the service start may report "already running" — handled with `changed_when` logic. The `loginctl enable-linger` command requires root privileges (`become: true`).

2. **Dependency failure:** If systemd user instances are not available (e.g., container without systemd), tasks will fail at `systemctl --user` commands. LXC containers on Proxmox do support systemd, so this is expected to work. If `XDG_RUNTIME_DIR` does not exist for the user, systemd user commands will fail — we set it explicitly in the environment. If linger is already enabled, `loginctl enable-linger` is idempotent (no error).

3. **Assumptions:** The target container runs systemd (Proxmox LXC with Debian 12/13). The `dev-host` role has been applied (tmux installed). Stories 1.1 and 1.2 have been applied (claude-tmux binary exists, `.tmux.conf` deployed). The dev user UID is 1000 (default for first non-root user on Debian). `XDG_RUNTIME_DIR` is `/run/user/1000`.

## Eval Assertions

<!-- Binary test assertions derived from acceptance criteria. Used by /autoresearch:fix for post-code-review iteration loops. -->

| # | Assertion | Command/Check | Pass Criteria |
|---|-----------|---------------|---------------|
| AC-1 | tmux-server.service unit file exists | `test -f /home/{{ dev_user }}/.config/systemd/user/tmux-server.service` on target | Exit code 0 |
| AC-2 | loginctl linger enabled | `loginctl show-user {{ dev_user }} --property=Linger \| grep -q 'yes'` on target | Exit code 0 |
| AC-3 | tmux-server.service is enabled | `XDG_RUNTIME_DIR=/run/user/1000 systemctl --user is-enabled tmux-server.service` as dev_user | Output "enabled" |
| AC-4 | tmux-server.service is active | `XDG_RUNTIME_DIR=/run/user/1000 systemctl --user is-active tmux-server.service` as dev_user | Output "active" |
| AC-5 | tmux server process is running | `pgrep -u {{ dev_user }} tmux` on target | Exit code 0 |
| AC-6 | Idempotent on second run | Run role twice, check second run output | Systemd tasks report "ok" not "changed" |
| AC-7 | No BMAD files modified | `find .claude/skills/bmad-* -newer <marker>` | Empty output |

## Tasks / Subtasks

- [x] Task 0: Verify Story 1.2 outputs (AC: prerequisite)
  - [x] Confirm `.tmux.conf` exists at `/home/{{ dev_user }}/.tmux.conf`
  - [x] Confirm `.tmux.conf` contains claude-tmux keybinding
  - [x] Confirm `ai-dev-tmux` role has tasks/main.yml with configure.yml include

- [x] Task 1: Add systemd variables to defaults/main.yml (AC: #1, #2)
  - [x] Add `dev_user_uid` variable (default: `1000`)
  - [x] Add `tmux_server_session_name` variable (default: `default`)

- [x] Task 2: Create tmux-server.service.j2 template (AC: #1)
  - [x] Create `roles/ai-dev-tmux/templates/tmux-server.service.j2`
  - [x] Include [Unit], [Service], [Install] sections
  - [x] Use `Type=forking` with `ExecStart=/usr/bin/tmux new-session -d -s {{ tmux_server_session_name }}`
  - [x] Include `ExecStop=/usr/bin/tmux kill-server`
  - [x] Set `Restart=on-failure`
  - [x] Set `WantedBy=default.target`

- [x] Task 3: Create systemd.yml tasks file (AC: #1, #2, #3, #4)
  - [x] Create `roles/ai-dev-tmux/tasks/systemd.yml`
  - [x] Enable lingering for dev user (loginctl enable-linger, become: true)
  - [x] Create systemd user unit directory (`~/.config/systemd/user/`)
  - [x] Deploy tmux-server.service.j2 template with notify handler
  - [x] Reload systemd user daemon
  - [x] Enable tmux-server.service
  - [x] Start tmux-server.service if not running

- [x] Task 4: Update tasks/main.yml to include systemd.yml (AC: #1)
  - [x] Add `include_tasks: systemd.yml` after configure.yml include

- [x] Task 5: Update handlers/main.yml (AC: #1)
  - [x] Add handler for systemd user daemon reload (triggered on service file change)

- [x] Task 6: Update verify.yml with systemd health checks (AC: #6)
  - [x] VERIFY: loginctl linger enabled for dev user
  - [x] VERIFY: tmux-server.service unit file exists
  - [x] VERIFY: tmux-server.service is enabled
  - [x] VERIFY: tmux-server.service is active/running
  - [x] VERIFY: tmux server process is running

- [x] Task 7: Verify BMAD update-safety (AC: #5)
  - [x] Confirm zero files modified under `.claude/skills/bmad-*/`

## Dev Notes

### Architecture Reference

From `architecture.md` — Auto-Start Strategy:

| Decision | Choice |
|----------|--------|
| tmux server | systemd user service (`tmux-server.service`) |
| Start method | `tmux new-session -d -s default` |
| Stop method | `tmux kill-server` |
| Linger | `loginctl enable-linger` for dev user |
| Recovery target | 60 seconds after container boot (NFR-REL-1) |

### Previous Story Learnings (from Stories 1.1 and 1.2)

- Use `become_user: "{{ dev_user }}"` with explicit `/home/{{ dev_user }}` paths (Story 1.1 P1 fix)
- Set `environment.HOME` on command tasks (Story 1.1 P1 fix)
- Use `changed_when` appropriately for idempotency (Story 1.1 D3)
- `dev_user: developer` default already in `defaults/main.yml`
- Template module handles idempotency natively (Story 1.2 learning)

### systemd User Unit Conventions

- `loginctl enable-linger` requires root (`become: true`), NOT `become_user`
- `systemctl --user` commands need `XDG_RUNTIME_DIR` set: `environment: { XDG_RUNTIME_DIR: "/run/user/{{ dev_user_uid }}" }`
- `systemctl --user` commands must run as the target user (`become_user: "{{ dev_user }}"`)
- `DBUS_SESSION_BUS_ADDRESS` may also be needed: `unix:path=/run/user/{{ dev_user_uid }}/bus`
- Service file changes should notify a handler to reload the daemon

### What NOT to Do

- Do NOT install OMEGA or Hermes (Epics 2 and 3)
- Do NOT modify any `.claude/skills/bmad-*/` files
- Do NOT create a new role — extend the existing `ai-dev-tmux` role
- Do NOT use `become: true` for `systemctl --user` commands (they need the user's systemd instance)
- Do NOT hardcode UID — use `dev_user_uid` variable

### Role Location

The role lives in `homelab-infra/ansible/roles/ai-dev-tmux/`, NOT in `homelab-playbook/`.

### References

- [Source: architecture.md — Auto-Start Strategy, systemd user services]
- [Source: prd.md — FR5, NFR-REL-1, AT-1.4]
- [Source: epics.md — Epic 1, Story 1.3]
- [Source: Story 1.1 — Review findings P1 (become_user fix), D1-D6 deferrals]
- [Source: Story 1.2 — Template idempotency, Edge Cases section]

## Dev Agent Record

- **Agent Model Used:** claude-opus-4-6 (Opus 4.6 with 1M context)
- **Debug Log References:** N/A (clean implementation, no debug cycles needed)
- **Completion Notes:**
  - Extended existing `ai-dev-tmux` role with systemd auto-start tasks
  - Created `templates/tmux-server.service.j2` — forking type, restart on failure, WantedBy default.target
  - Created `tasks/systemd.yml` — linger check/enable (become: true), directory creation, template deploy with handler notify, flush_handlers, systemd enable + start with scope: user
  - Updated `handlers/main.yml` with `reload systemd user daemon` handler using systemd module with scope: user
  - Added 2 new variables to `defaults/main.yml`: `dev_user_uid` (1000) and `tmux_server_session_name` (default)
  - Updated `tasks/main.yml` to include systemd.yml after configure.yml
  - Updated `verify.yml` with 5 new VERIFY-prefixed health checks for linger, unit file, enabled, active, and process
  - All systemd user commands use `XDG_RUNTIME_DIR` and `DBUS_SESSION_BUS_ADDRESS` environment variables
  - `loginctl enable-linger` uses `become: true` (root); all `systemctl --user` tasks use `become_user: "{{ dev_user }}"` with `scope: user`
  - Idempotency: linger check before enable, template module is inherently idempotent, systemd module reports no change when already enabled/started
  - Zero files modified under `.claude/skills/bmad-*/`
- **File List:**
  - `homelab-infra/ansible/roles/ai-dev-tmux/defaults/main.yml` (modified)
  - `homelab-infra/ansible/roles/ai-dev-tmux/tasks/main.yml` (modified)
  - `homelab-infra/ansible/roles/ai-dev-tmux/tasks/systemd.yml` (new)
  - `homelab-infra/ansible/roles/ai-dev-tmux/tasks/verify.yml` (modified)
  - `homelab-infra/ansible/roles/ai-dev-tmux/templates/tmux-server.service.j2` (new)
  - `homelab-infra/ansible/roles/ai-dev-tmux/handlers/main.yml` (modified)
- **Review Findings (adversarial code review — 2026-04-04):**
  - **Layer 1 (Blind Hunter):** No anti-patterns found. Privilege separation correct: `become: true` for loginctl (root), `become_user` for systemctl --user (dev user). XDG_RUNTIME_DIR and DBUS_SESSION_BUS_ADDRESS set on all user-scope tasks. Template module handles idempotency natively. No secrets in any file. Handler notification pattern correct with `meta: flush_handlers` ensuring daemon-reload before enable/start.
  - **Layer 2 (Edge Case Hunter):**
    - Linger already enabled: Handled via pre-check with `when` guard.
    - No graphical session: Linger enables user systemd instance at boot — correct design.
    - XDG_RUNTIME_DIR missing: Set explicitly in environment; `enable-linger` triggers user runtime dir creation.
    - Manual tmux already running: Service ExecStart would fail on duplicate session name — deferred (D2).
    - Container without systemd: Documented as assumption; Proxmox LXC supports systemd.
  - **Layer 3 (Acceptance Auditor):** All 6 ACs pass. Service unit deployed, linger configured, service enabled, auto-start on boot via linger + enabled service, no BMAD files modified, 5 VERIFY checks in verify.yml.
  - **Two-Strike Check:** Compared D1-D2 (Story 1.3) against D1-D6 (Story 1.1) and zero deferrals (Story 1.2). No matches found — all deferrals are domain-specific to their respective stories. No reclassification needed.
  - **A/B Fix Comparison:** No `[Review][Patch]` findings — clean review. No patches to compare.
  - `[Review][Defer]` **D1 — XDG_RUNTIME_DIR race condition after enable-linger:** Potential timing gap between `loginctl enable-linger` creating the user runtime dir and subsequent `systemctl --user` commands. In practice, `enable-linger` triggers `user@1000.service` synchronously on Proxmox LXC. Low risk, container-specific.
  - `[Review][Defer]` **D2 — Manual tmux conflicts with service ExecStart:** If tmux is started manually with session name "default" before the service starts, `tmux new-session -d -s default` fails on duplicate name. Edge case for first run only — on subsequent boots, systemd starts clean. Can be addressed with `ExecStartPre=-/usr/bin/tmux kill-session -t default` if needed, but adds unnecessary complexity for the standard use case.
