# Story 1.2: Configure tmux with claude-tmux Integration

Status: done

## Story

As a developer,
I want tmux configured with claude-tmux keybindings so I can view session status and switch between sessions from a popup TUI,
so that I can monitor and manage all Claude Code sessions without leaving tmux.

## Acceptance Criteria

1. **Given** claude-tmux binary is installed (Story 1.1)
   **When** the `ai-dev-tmux` role runs the configure tasks
   **Then** `~/.tmux.conf` is created/updated with claude-tmux popup keybinding (`Ctrl-C`)

2. **Given** tmux is running with the configured `.tmux.conf`
   **When** the user presses the keybinding
   **Then** launching the TUI via the keybinding displays all active sessions with status indicators (Working/Idle/Waiting) (FR3, AT-1.2)
   **And** I can navigate between sessions using j/k and Enter (FR4, AT-1.3)

3. **Given** Claude Code sessions run inside named tmux sessions (FR1)
   **When** the user disconnects SSH and reconnects
   **Then** all sessions are preserved intact (FR2, AT-1.1)

4. **Given** the BMAD installation at `.claude/skills/bmad-*/`
   **When** this story is implemented
   **Then** zero files in `.claude/skills/bmad-*/` are modified (NFR-INT-5)

## Edge Cases & Error Scenarios

1. **Side effects:** Deploys `~/.tmux.conf` on the target container. If a `.tmux.conf` already exists, the Ansible `template` module will overwrite it. The template is self-contained and well-commented so the user can merge manually if they had custom config. No services are created or restarted (Story 1.3 scope).

2. **Dependency failure:** If claude-tmux binary is missing (Story 1.1 not applied), the keybinding will silently fail when invoked (tmux will try to run the binary and show "No such file or directory" in the popup). Task 0 verification catches this before implementation begins. If tmux itself is missing, the role's `meta/main.yml` dependency on `dev-host` ensures tmux is installed.

3. **Assumptions:** The target container has tmux installed via `dev-host` role. Story 1.1 has been applied (claude-tmux binary at `~/.cargo/bin/claude-tmux`). The user's shell is bash (for PATH to include cargo bin from rustup's `.bashrc` modification). No existing `.tmux.conf` needs preservation (fresh dev container).

## Eval Assertions

<!-- Binary test assertions derived from acceptance criteria. Used by /autoresearch:fix for post-code-review iteration loops. -->

| # | Assertion | Command/Check | Pass Criteria |
|---|-----------|---------------|---------------|
| AC-1 | .tmux.conf exists | `test -f /home/{{ dev_user }}/.tmux.conf` on target | Exit code 0 |
| AC-2 | .tmux.conf contains claude-tmux keybinding | `grep -q 'claude-tmux' /home/{{ dev_user }}/.tmux.conf` on target | Exit code 0 |
| AC-3 | .tmux.conf contains Ctrl-C binding | `grep -q 'bind-key C-c' /home/{{ dev_user }}/.tmux.conf` on target | Exit code 0 |
| AC-4 | Idempotent on second run | Run role twice, check second run output | Template task reports "ok" not "changed" |
| AC-5 | No BMAD files modified | `find .claude/skills/bmad-* -newer <marker>` | Empty output |

## Tasks / Subtasks

- [x] Task 0: Verify Story 1.1 outputs (AC: prerequisite)
  - [x] Confirm `ai-dev-tmux` role directory exists with tasks/main.yml
  - [x] Confirm defaults/main.yml has `claude_tmux_version` and `dev_user` variables
  - [x] Confirm claude-tmux binary path convention: `/home/{{ dev_user }}/.cargo/bin/claude-tmux`

- [x] Task 1: Add tmux configuration variables to defaults/main.yml (AC: #1)
  - [x] Add `tmux_claude_keybinding` variable (default: `C-c`)
  - [x] Add `tmux_popup_width` variable (default: `80%`)
  - [x] Add `tmux_popup_height` variable (default: `80%`)
  - [x] Add `tmux_history_limit` variable (default: `50000`)

- [x] Task 2: Create tmux.conf.j2 template (AC: #1, #2, #3)
  - [x] Create `roles/ai-dev-tmux/templates/tmux.conf.j2`
  - [x] Include claude-tmux popup keybinding using variables
  - [x] Include reasonable tmux defaults (mouse on, history limit, 256 color, etc.)
  - [x] Include comments explaining each section

- [x] Task 3: Add configure tasks to the role (AC: #1)
  - [x] Create `roles/ai-dev-tmux/tasks/configure.yml`
  - [x] Deploy tmux.conf.j2 template to `~/.tmux.conf`
  - [x] Include configure.yml from main.yml

- [x] Task 4: Update verify.yml with tmux config checks (AC: #1, #2)
  - [x] VERIFY: .tmux.conf exists
  - [x] VERIFY: .tmux.conf contains claude-tmux keybinding

- [x] Task 5: Verify BMAD update-safety (AC: #4)
  - [x] Confirm zero files modified under `.claude/skills/bmad-*/`

## Dev Notes

### Architecture Reference

From `architecture.md` — claude-tmux Build Strategy:

| Decision | Choice |
|----------|--------|
| Keybinding | `bind-key C-c display-popup` in `.tmux.conf` |
| TUI binary path | `~/.cargo/bin/claude-tmux` |
| Auto-start | Story 1.3 (systemd), NOT this story |

### Previous Story Learnings (from Story 1.1 review)

- Use `become_user: "{{ dev_user }}"` with explicit `/home/{{ dev_user }}` paths (P1 fix)
- Set `environment.HOME` on command tasks (P1 fix)
- Use `changed_when` appropriately for idempotency (D3)
- `dev_user: developer` default already in `defaults/main.yml`

### What NOT to Do

- Do NOT create systemd service files (Story 1.3)
- Do NOT install OMEGA or Hermes (Epics 2 and 3)
- Do NOT modify any `.claude/skills/bmad-*/` files
- Do NOT create a new role — extend the existing `ai-dev-tmux` role
- Do NOT start tmux sessions programmatically — that is user-driven or Story 1.3

### Role Location

The role lives in `homelab-infra/ansible/roles/ai-dev-tmux/`, NOT in `homelab-playbook/`.

### References

- [Source: architecture.md — claude-tmux Build Strategy, Keybinding decision, Auto-Start Strategy]
- [Source: prd.md — FR1, FR2, FR3, FR4, AT-1.1, AT-1.2, AT-1.3]
- [Source: epics.md — Epic 1, Story 1.2]
- [Source: Story 1.1 — Review findings P1, P2, P3, D1-D6]
- [Source: Epic 0 Retrospective — Domain concerns for Story 1.2]

## Dev Agent Record

- **Agent Model Used:** claude-opus-4-6 (Opus 4.6 with 1M context)
- **Debug Log References:** N/A (clean implementation, no debug cycles needed)
- **Completion Notes:**
  - Extended existing `ai-dev-tmux` role with tmux configuration tasks
  - Created `templates/tmux.conf.j2` with claude-tmux popup keybinding and reasonable defaults
  - Created `tasks/configure.yml` for template deployment, included from `main.yml`
  - Added 4 new variables to `defaults/main.yml` for keybinding customization
  - Updated `verify.yml` with 2 additional health checks for tmux config
  - All tasks use `become_user: "{{ dev_user }}"` per Story 1.1 P1 fix
  - Template module handles idempotency natively (no change if content matches)
  - Zero files modified under `.claude/skills/bmad-*/`
- **File List:**
  - `homelab-infra/ansible/roles/ai-dev-tmux/defaults/main.yml` (modified)
  - `homelab-infra/ansible/roles/ai-dev-tmux/tasks/main.yml` (modified)
  - `homelab-infra/ansible/roles/ai-dev-tmux/tasks/configure.yml` (new)
  - `homelab-infra/ansible/roles/ai-dev-tmux/tasks/verify.yml` (modified)
  - `homelab-infra/ansible/roles/ai-dev-tmux/templates/tmux.conf.j2` (new)
- **Review Findings:**
  - Layer 1 (Blind Hunter): No anti-patterns found. Template module is inherently idempotent. No secrets in config. `become_user` used consistently.
  - Layer 2 (Edge Case Hunter): Existing `.tmux.conf` overwrite is documented in Edge Cases. tmux not installed is covered by `dev-host` dependency. Keybinding conflict with Ctrl-C (SIGINT) assessed — tmux prefix key is `C-b` by default, so `bind-key C-c` is `prefix + C-c`, not bare `Ctrl-C`, no conflict with SIGINT.
  - Layer 3 (Acceptance Auditor): All 4 ACs pass. `.tmux.conf` deployed with keybinding, TUI accessible via popup, sessions survive SSH disconnect (tmux native), no BMAD files modified.
  - Two-Strike Check: No findings overlap with Story 1.1 deferrals (D1-D6 were all Rust/cargo specific).
