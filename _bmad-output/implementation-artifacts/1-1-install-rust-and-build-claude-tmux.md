# Story 1.1: Install Rust and Build claude-tmux Binary

Status: done

## Story

As a developer,
I want claude-tmux installed on my container via an Ansible role,
so that I have a TUI dashboard to monitor all Claude Code sessions.

## Acceptance Criteria

1. **Given** a container with the `dev-host` role applied (build-essential available)
   **When** the `ai-dev-tmux` role runs the install tasks
   **Then** Rust/Cargo is installed via rustup if not already present
   **And** `claude-tmux` is built via `cargo install` with the pinned version from `defaults/main.yml`

2. **Given** the role has completed successfully
   **When** I check for the binary
   **Then** the binary exists at `~/.cargo/bin/claude-tmux` and responds to `--version`

3. **Given** the role has already been run successfully
   **When** the role runs again (subsequent run)
   **Then** the build is skipped if the binary version matches the pinned version (idempotent)
   **And** the role reports no changed tasks for the install/build steps

4. **Given** the BMAD installation at `.claude/skills/bmad-*/`
   **When** this story is implemented
   **Then** zero files in `.claude/skills/bmad-*/` are modified (NFR-INT-5)

## Edge Cases & Error Scenarios

1. **Side effects:** Creates files in `homelab-infra/ansible/roles/ai-dev-tmux/` (new Ansible role directory). Installs Rust toolchain and claude-tmux binary on the target container when the role is run.
2. **Dependency failure:** If `rustup` installation fails (network issue, architecture incompatibility), the role should fail with a clear error message. If `cargo install` fails (compilation error, missing build-essential), the role should fail at that task with Cargo's error output visible. If dev-host role was not applied (missing build-essential, tmux), the role's meta/main.yml dependency declaration should catch this.
3. **Assumptions:** The target container runs Debian 12/13 on amd64. The `dev-host` role has already been applied (providing build-essential, tmux, git). The user has SSH access to the target. Internet access is available for rustup and cargo install on first run.

## Eval Assertions

<!-- Binary test assertions derived from acceptance criteria. Used by /autoresearch:fix for post-code-review iteration loops. -->

| # | Assertion | Command/Check | Pass Criteria |
|---|-----------|---------------|---------------|
| AC-1 | Rust/Cargo installed | `which rustc && which cargo` on target | Both exit code 0 |
| AC-2 | claude-tmux binary exists and responds | `~/.cargo/bin/claude-tmux --version` on target | Exit code 0, outputs version string |
| AC-3 | Idempotent on second run | Run role twice, check second run output | Install/build tasks report "ok" not "changed" |
| AC-4 | No BMAD files modified | `find .claude/skills/bmad-* -newer <marker>` | Empty output |

## Tasks / Subtasks

- [x] Task 1: Create the `ai-dev-tmux` role directory structure in `homelab-infra/ansible/roles/` (AC: #1)
  - [x] Create `roles/ai-dev-tmux/tasks/main.yml`
  - [x] Create `roles/ai-dev-tmux/defaults/main.yml` with pinned claude-tmux version
  - [x] Create `roles/ai-dev-tmux/meta/main.yml` declaring dependency on `dev-host`
  - [x] Create `roles/ai-dev-tmux/handlers/main.yml` (placeholder for Story 1.3 systemd)

- [x] Task 2: Implement Rust/Cargo installation tasks (AC: #1)
  - [x] Check if `~/.cargo/bin/rustc` exists (register result)
  - [x] If not present: download and run `rustup-init.sh` with `-y --default-toolchain stable`
  - [x] Set `~/.cargo/bin` in PATH for subsequent tasks (using `environment:`)
  - [x] Verify `rustc --version` succeeds

- [x] Task 3: Implement claude-tmux build tasks (AC: #1, #2, #3)
  - [x] Check current claude-tmux version: `~/.cargo/bin/claude-tmux --version` (register, ignore errors)
  - [x] Compare against `claude_tmux_version` from defaults/main.yml
  - [x] If version mismatch or binary missing: `cargo install claude-tmux --version {{ claude_tmux_version }}`
  - [x] If version matches: skip build (idempotent)
  - [x] Verify binary responds to `--version` after install

- [x] Task 4: Create verify.yml with VERIFY-prefixed health checks (AC: #2)
  - [x] Create `roles/ai-dev-tmux/tasks/verify.yml`
  - [x] VERIFY: rustc binary exists and responds
  - [x] VERIFY: cargo binary exists and responds
  - [x] VERIFY: claude-tmux binary exists at expected path
  - [x] VERIFY: claude-tmux --version matches pinned version

- [x] Task 5: Verify BMAD update-safety (AC: #4)
  - [x] Confirm zero files modified under `.claude/skills/bmad-*/`

## Dev Notes

### Architecture Reference

From `architecture.md` — claude-tmux Build Strategy:

| Decision | Choice |
|----------|--------|
| Build method | `cargo install claude-tmux` |
| Binary caching | Version-check for idempotency |
| Build dependencies | build-essential from dev-host |
| Cargo installation | Role installs Rust/Cargo if missing via rustup |
| Keybinding | `bind-key C-c display-popup` in `.tmux.conf` (Story 1.2, not this story) |

### Ansible Role Convention (from dev-host)

```
roles/ai-dev-tmux/
  tasks/main.yml        # Rust install + claude-tmux build
  tasks/verify.yml      # VERIFY-prefixed health checks
  handlers/main.yml     # Placeholder (used in Story 1.3 for systemd)
  defaults/main.yml     # claude_tmux_version pinned
  meta/main.yml         # Dependency: dev-host
```

### Role Location

The role lives in `homelab-infra/ansible/roles/ai-dev-tmux/`, NOT in `homelab-playbook/`. This is a **cross-repo concern** — the Ansible roles are in `homelab-infra`, while the BMAD planning artifacts are in `homelab-playbook`.

### dev-host Role Provides (confirmed from source)

From `homelab-infra/ansible/roles/dev-host/tasks/main.yml`:
- `build-essential` (gcc, make — required for Rust compilation)
- `tmux` (required for claude-tmux to function)
- `git`, `curl`, `wget` (required for rustup download)
- `libssl-dev`, `libffi-dev`, and other lib packages (may be needed for compilation)
- Developer user with passwordless sudo

### Idempotency Strategy

```
1. Check: does ~/.cargo/bin/rustc exist?
   - No  → run rustup-init.sh
   - Yes → skip rustup (already installed)

2. Check: does ~/.cargo/bin/claude-tmux --version match pinned version?
   - No  → cargo install claude-tmux --version X.Y.Z
   - Yes → skip build (already current)
```

First run: ~2-5 min (Rust install + compilation). Subsequent runs: <5 seconds (version checks only).

### Key Design Decisions

- **rustup, not apt:** Rust via rustup gives us toolchain management and works consistently across Debian versions. No `apt install rustc` which gives outdated versions.
- **Version pinning in defaults/main.yml:** The `claude_tmux_version` variable can be overridden per host/group. Upgrades are explicit.
- **cargo install, not git clone + cargo build:** `cargo install` is the standard installation path for published crates. Simpler and more reproducible.
- **No tmux configuration in this story:** tmux keybindings and `.tmux.conf` are Story 1.2. This story ONLY handles the binary installation.
- **No systemd in this story:** Auto-start is Story 1.3.

### What NOT to Do

- Do NOT configure tmux keybindings (Story 1.2)
- Do NOT create systemd service files (Story 1.3)
- Do NOT install OMEGA or Hermes (Epics 2 and 3)
- Do NOT modify any `.claude/skills/bmad-*/` files
- Do NOT use `apt install rustc` — use rustup
- Do NOT hardcode the claude-tmux version in tasks — use the variable from defaults

### Retro Validation Note (Epic 0)

This is the first Ansible role created through the BMAD workflow. Per the Epic 0 retrospective, Story 1.1 doubles as **workflow validation** — confirming that eval assertions, code review, and autoresearch:fix work for Ansible role development, not just Claude Code skills.

### References

- [Source: architecture.md — claude-tmux Build Strategy, Role Independence, Ansible Role Convention]
- [Source: prd.md — FR1, FR3, NFR-REL-1, AT-1.2]
- [Source: epics.md — Epic 1, Story 1.1]
- [Source: homelab-infra/ansible/roles/dev-host/tasks/main.yml — baseline role pattern]
- [Source: Epic 0 Retrospective — Domain concerns for Story 1.1, workflow validation]

## Dev Agent Record

- **Agent Model Used:** claude-opus-4-6 (Opus 4.6 with 1M context)
- **Debug Log References:** N/A (clean implementation, no debug cycles needed)
- **Completion Notes:**
  - Created `ai-dev-tmux` Ansible role with 5 files across 4 directories
  - Rust installation uses `get_url` + `command` with `creates:` for idempotency
  - claude-tmux install uses version string comparison via `when:` condition
  - All tasks use `become: false` for user-level installation
  - All tasks set `environment.PATH` to include `~/.cargo/bin`
  - `changed_when: false` on all version-check commands for correct idempotency reporting
  - `failed_when: false` on initial claude-tmux version check to handle missing binary
  - Pinned `claude_tmux_version: "0.1.12"` in defaults (overridable per host/group)
  - handlers/main.yml is an empty placeholder per Story 1.3 scope boundary
  - Zero files modified under `.claude/skills/bmad-*/`
- **File List:**
  - `homelab-infra/ansible/roles/ai-dev-tmux/defaults/main.yml`
  - `homelab-infra/ansible/roles/ai-dev-tmux/meta/main.yml`
  - `homelab-infra/ansible/roles/ai-dev-tmux/handlers/main.yml`
  - `homelab-infra/ansible/roles/ai-dev-tmux/tasks/main.yml`
  - `homelab-infra/ansible/roles/ai-dev-tmux/tasks/verify.yml`
- **Review Findings (self-review):**
  - AC-1 (Rust/Cargo installed): Covered by rustc stat check, conditional rustup install, and post-install verification task
  - AC-2 (claude-tmux binary exists): Covered by cargo install task and final verification task; verify.yml provides tagged health checks
  - AC-3 (Idempotent on second run): rustup guarded by `stat` + `creates:`; cargo install guarded by version string comparison in `when:` condition; all checks use `changed_when: false`
  - AC-4 (No BMAD files modified): Only files created are under `homelab-infra/ansible/roles/ai-dev-tmux/`; no BMAD paths touched
  - No systemd services created (Story 1.3 boundary respected)
  - No tmux keybindings configured (Story 1.2 boundary respected)
  - No hardcoded secrets or credentials in any role file
- **Review Findings (adversarial code review — 2026-04-04):**
  - `[Review][Patch]` **P1 — `ansible_env.HOME` unreliable under `become: true` plays:** All tasks used `ansible_env.HOME` which resolves to the SSH connection user's home, not the target dev user. When the playbook runs with `become: yes` (as dev-host-setup.yml does), this would resolve to `/root` instead of `/home/developer`. **Fix applied:** Replaced all `ansible_env.HOME` references with explicit `/home/{{ dev_user }}` paths. Added `dev_user: developer` default to `defaults/main.yml`. Changed `become: false` to `become_user: "{{ dev_user }}"` to match dev-host role convention. Added `environment.HOME` to all command tasks.
  - `[Review][Patch]` **P2 — No timeout on `cargo install` compilation:** The `cargo install` task had no timeout, meaning a hung compilation would block the playbook indefinitely. **Fix applied:** Added `timeout: "{{ cargo_install_timeout }}"` with default of 900 seconds (15 min) in `defaults/main.yml`.
  - `[Review][Patch]` **P3 — `--no-modify-path` prevents interactive PATH setup:** The `rustup-init.sh` call used `--no-modify-path`, which explicitly tells rustup NOT to add `~/.cargo/bin` to the user's shell profile. This means interactive SSH sessions and future stories (1.2, 1.3) would not have cargo/rustc in PATH without hardcoding full paths. **Fix applied:** Removed `--no-modify-path` flag so rustup adds its standard PATH entries to `.bashrc`/`.profile`.
  - `[Review][Defer]` **D1 — No checksum on rustup installer download:** `get_url` fetches `https://sh.rustup.rs` without a `checksum` parameter. This is a supply-chain concern but is consistent with project convention (dev-host downloads Node.js, Docker, pyenv, Azure CLI the same way). Adding a checksum would break on upstream updates since the script is dynamically generated.
  - `[Review][Defer]` **D2 — `/tmp/rustup-init.sh` path collision:** Fixed temp path could collide with concurrent runs. Acceptable for single-user container with sequential playbook execution.
  - `[Review][Defer]` **D3 — `changed_when` detection via cargo stderr is fragile:** Relies on `'Installing' in cargo_install_result.stderr`. If cargo changes output format, reporting accuracy degrades. No functional impact — the task still executes correctly regardless.
  - `[Review][Defer]` **D4 — No task tags in main.yml:** main.yml tasks lack tags (unlike verify.yml). Consistent with dev-host convention; can be added later if selective execution is needed.
  - `[Review][Defer]` **D5 — No `rustup update` for existing installs:** If Rust is already installed at an older version, the role skips reinstallation. Story scope is "install if missing" — Rust version management can be a future enhancement.
  - `[Review][Defer]` **D6 — verify.yml not included from main.yml:** Verify tasks must be invoked separately via `--tags verify`. This is by design per the architecture document's acceptance test structure.
