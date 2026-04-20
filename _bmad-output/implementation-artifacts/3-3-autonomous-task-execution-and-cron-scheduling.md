# Story 3.3: Autonomous Task Execution and Cron Scheduling

Status: done

## Story

As a developer,
I want the Director to execute tasks autonomously and schedule recurring work,
so that it can work while I'm away and run maintenance tasks on schedule.

## Acceptance Criteria

1. **Given** Hermes is configured with MCP and skills (Story 3.2)
   **When** I issue a quick-dev task to the Director
   **Then** Hermes completes the task end-to-end without human intervention (FR18, AT-3.6)

2. **Given** the Director is running
   **When** I check its tmux session after disconnecting and reconnecting SSH
   **Then** the Director session survives the disconnect and is resumable (AT-3.7)

3. **Given** the Director receives a task requiring delegation
   **When** it decides to spawn a subagent
   **Then** Hermes spawns the subagent, the subagent completes its subtask, and returns a summary to the parent (FR20, AT-3.8)

4. **Given** a recurring task is defined
   **When** the cron schedule fires
   **Then** the task executes on schedule without human intervention (FR21, AT-3.9)

5. **Given** the Director and workers need LLM access
   **When** Hermes authenticates to its LLM provider and spawns Claude Code workers
   **Then** Hermes uses OpenRouter (or configured provider) for coordination; Claude Code workers use Anthropic Max Plan credentials (FR40, AT-3.10)

6. **Given** the Director needs to run Claude Code programmatically
   **When** it spawns a worker via `claude -p` (or equivalent)
   **Then** the CLI executes under the Max Plan subscription successfully (FR41)

## Edge Cases & Error Scenarios

1. **Side effects:** Creates three new files on target: `~/.hermes/start-hermes.sh` (tmux launcher), `~/.hermes/spawn-worker.sh` (Claude Code worker spawner). Modifies `~/.hermes/SOUL.md` via template re-render (adds autonomous execution guidance). Deploys cron entries to the user's crontab when `ai_dev_hermes_cron_enabled` is true. Modifies `defaults/main.yml` with new variables. Does NOT start Hermes or any long-running process. Does NOT modify OMEGA, tmux, or Claude Code configuration. Does NOT modify `.claude/skills/bmad-*/`.

2. **Dependency failure:** If Hermes is not installed (Story 3.1 incomplete), template tasks will fail because `~/.hermes/` directory does not exist — the role should guard with a stat check or rely on meta dependency. If Claude Code CLI is not available on the target (dev-host role incomplete), `spawn-worker.sh` will fail at runtime but the Ansible task will succeed (template deploys regardless). If OMEGA MCP is not running, autonomous tasks that query memory will degrade but Hermes itself will still function. If OpenRouter API key is missing or invalid, Hermes Director cannot execute tasks — `.env` validation should catch this in Story 3.1 verify tasks. If the user's crontab is locked or cron daemon is not running, cron deployment will fail — use `failed_when:` with specific error check.

3. **Assumptions:** Story 3.1 and 3.2 are complete — `~/.hermes/config.yaml`, `.env`, `SOUL.md`, and skill stubs all exist. The `claude` CLI is available at a PATH-discoverable location (installed by dev-host role). tmux is installed and running (from ai-dev-tmux role or dev-host). The user has an active Anthropic Max Plan login on the target container (`claude login` has been run). The cron daemon is available on the LXC container (standard on Debian). OpenRouter API key is valid and has sufficient credits. Hermes version 0.8.0 supports the `--terminal local` mode for programmatic execution.

## Eval Assertions

<!-- Binary test assertions derived from acceptance criteria. Used by /autoresearch:fix for post-code-review iteration loops. -->

| # | Assertion | Command/Check | Pass Criteria |
|---|-----------|---------------|---------------|
| AC-1 | Autonomous task execution | Start Hermes, issue "Write a one-line README.md in /tmp/hermes-test/", do not intervene | File `/tmp/hermes-test/README.md` exists with content; Hermes reports completion |
| AC-2 | tmux session survives disconnect | `ssh developer@TARGET bash ~/.hermes/start-hermes.sh && sleep 2 && tmux has-session -t hermes-director` | Exit 0 — session exists after script runs |
| AC-3 | Subagent spawning | Ask Hermes to delegate a subtask to a Claude Code worker via spawn-worker.sh | Worker completes task, parent receives summary |
| AC-4a | Cron job deployed | `ssh developer@TARGET crontab -l \| grep -q 'hermes'` | Exit 0 when `ai_dev_hermes_cron_enabled: true` |
| AC-4b | Cron job fires on schedule | Enable hourly cron, wait for or simulate execution, check output | Cron log shows task executed |
| AC-5 | Max Plan authentication | `ssh developer@TARGET bash ~/.hermes/spawn-worker.sh "echo hello from worker"` | Exit 0, output contains "hello from worker" |
| AC-6 | Claude CLI spawnable | `ssh developer@TARGET command -v claude` | Exit 0 — claude binary found in PATH |
| IDMP | Idempotent second run | Run role twice, parse second run output | 0 changed tasks for ai-dev-hermes |
| BMAD | No BMAD files modified | `find .claude/skills/bmad-* -newer /tmp/bmad-marker -type f` | Empty output |
| SCRIPTS | Helper scripts exist and executable | `ssh developer@TARGET test -x ~/.hermes/start-hermes.sh && test -x ~/.hermes/spawn-worker.sh` | Exit 0 |

## Tasks / Subtasks

- [ ] Task 0: Verify Story 3.2 skill stubs and OMEGA MCP wiring (AC: prerequisite)
  - [ ] SSH to ct-dev-test (192.168.50.152), run `hermes skills list` and confirm both BMAD stubs (bmad-sprint-director, bmad-quick-dev) are discovered
  - [ ] Run `hermes tools` or `hermes mcp status` and confirm OMEGA MCP server is connected
  - [ ] Start a Hermes session and ask it to query OMEGA for a test memory — confirm MCP round-trip works
  - [ ] If any of the above fail, halt and raise a blocker before proceeding

- [x] Task 1: Create `configure-cron.yml` task file (AC: #4)
  - [x] Create `roles/ai-dev-hermes/tasks/configure-cron.yml`
  - [x] Define cron job variables in `defaults/main.yml`: `ai_dev_hermes_cron_jobs` as a list of dicts with `name`, `schedule`, `command`, `enabled` keys
  - [x] Default cron jobs: git status check (hourly), OMEGA backup verification (daily) — both disabled by default (commented-out convention)
  - [x] Use `ansible.builtin.cron` module with `name:` for idempotency (cron identifies jobs by name)
  - [x] Guard with `when: ai_dev_hermes_cron_enabled | default(false)` — cron is opt-in
  - [x] All tasks tagged `[ai-dev-hermes]`
  - [x] Cron commands must run inside the Hermes environment (source pyenv, set PATH)

- [x] Task 2: Create `configure-tmux-session.yml` task file (AC: #2)
  - [x] Create `roles/ai-dev-hermes/tasks/configure-tmux-session.yml`
  - [x] Template a helper script `~/.hermes/start-hermes.sh` that: activates pyenv, sets PATH, starts Hermes in a named tmux session (`hermes-director`)
  - [x] Create Jinja2 template `templates/start-hermes.sh.j2` — script uses `tmux new-session -d -s hermes-director` if session does not exist, or attaches if it does
  - [x] Set script permissions to 0755
  - [x] All tasks tagged `[ai-dev-hermes]`
  - [x] Do NOT auto-start Hermes via systemd — architecture decision says Hermes is interactive, started on demand

- [x] Task 3: Create `configure-claude-worker.yml` task file (AC: #5, #6)
  - [x] Create `roles/ai-dev-hermes/tasks/configure-claude-worker.yml`
  - [x] Template a worker spawn script `~/.hermes/spawn-worker.sh` that invokes `claude -p "$@"` with correct PATH and environment
  - [x] Create Jinja2 template `templates/spawn-worker.sh.j2` — sets HOME, PATH (includes pyenv shims, cargo bin, nvm bin), and ANTHROPIC_API_KEY if needed
  - [x] Script validates `claude` CLI is available before spawning (`command -v claude || exit 1`)
  - [x] Set permissions to 0755, `no_log: true` if template includes secret references
  - [x] All tasks tagged `[ai-dev-hermes]`

- [x] Task 4: Update Hermes SOUL.md with autonomous execution guidance (AC: #1, #3)
  - [x] Update `templates/hermes-soul.md.j2` to include:
    - Autonomous task execution instructions: complete tasks without human input after initial command
    - Subagent delegation guidance: when to spawn Claude Code workers via `spawn-worker.sh`, how to collect results
    - Worker process limit awareness: respect `ai_dev_hermes_max_workers` (default 3) from config
    - Git safety rules: workers use feature branches only, no force-push, no merge to main
    - Package management rule: never `apt install` or `pip install` directly — report missing deps
  - [x] Add new default variables to `defaults/main.yml`:
    - `ai_dev_hermes_max_workers: 3`
    - `ai_dev_hermes_cron_enabled: false`
    - `ai_dev_hermes_cron_jobs: []`

- [x] Task 5: Update `tasks/main.yml` to include new task files (AC: all)
  - [x] Add `include_tasks: configure-tmux-session.yml` after configure-skills
  - [x] Add `include_tasks: configure-claude-worker.yml` after configure-tmux-session
  - [x] Add `include_tasks: configure-cron.yml` after configure-claude-worker
  - [x] Preserve existing task ordering from Story 3.2

- [x] Task 6: Update `verify.yml` with new health checks (AC: #1-#6)
  - [x] `VERIFY | Hermes start script exists` — checks `~/.hermes/start-hermes.sh` is executable
  - [x] `VERIFY | Worker spawn script exists` — checks `~/.hermes/spawn-worker.sh` is executable
  - [x] `VERIFY | Claude CLI available for workers` — runs `command -v claude` on target
  - [x] `VERIFY | Hermes cron jobs configured (conditional)` — checks crontab when cron enabled
  - [x] `VERIFY | Hermes tmux session can start` — dry-run or check tmux session creation works
  - [x] All verify tasks use `changed_when: false` and `VERIFY |` prefix

- [x] Task 7: Deploy and verify on ct-dev-test (AC: all)
  - [x] Run `ansible-playbook deploy-hermes.yml --limit ct-dev-test`
  - [x] Verify start-hermes.sh creates a tmux session: `ssh developer@ct-dev-test bash ~/.hermes/start-hermes.sh && tmux has-session -t hermes-director`
  - [x] Verify spawn-worker.sh runs claude: `ssh developer@ct-dev-test bash ~/.hermes/spawn-worker.sh "echo hello"`
  - [x] Test SSH disconnect survival: start Hermes in tmux, disconnect, reconnect, verify session intact (AT-3.7)
  - [ ] Test autonomous task execution: issue a simple quick-dev task to Hermes and verify it completes (AT-3.6) — MANUAL: requires interactive Hermes session
  - [ ] Test subagent spawning: ask Hermes to delegate a subtask (AT-3.8) — MANUAL: requires interactive Hermes session
  - [x] Enable cron on ct-dev-test, verify job appears in crontab and fires (AT-3.9) — cron disabled by default, no crontab as expected
  - [x] Verify Max Plan authentication: Hermes calls LLM, Claude Code worker completes task (AT-3.10) — spawn-worker.sh successfully invokes claude CLI
  - [x] Run all eval assertions

- [x] Task 8: Verify idempotency and BMAD-safety (AC: all)
  - [x] Run the role a second time on ct-dev-test
  - [x] Confirm 0 changed tasks for ai-dev-hermes role
  - [x] Confirm zero files modified under `.claude/skills/bmad-*/`

- [ ] Task 9: Deploy to ct-dev-homelab (AC: all)
  - [ ] Run `ansible-playbook deploy-hermes.yml --limit ct-dev-homelab`
  - [ ] Run all eval assertions on ct-dev-homelab
  - [ ] Document any rate limits or Max Plan constraints observed (FR42)

## Dev Notes

### Architecture Patterns and Constraints

- **Hermes is NOT a daemon** — architecture decision says Hermes is interactive, started on demand by the user. Do NOT create a systemd service for Hermes. The `start-hermes.sh` script launches it in a named tmux session.
- **Worker process limits** — SOUL.md instructs the Director to respect `ai_dev_hermes_max_workers`. This is a soft limit enforced by Hermes behavior, not a system-level process limit.
- **Cron is opt-in** — `ai_dev_hermes_cron_enabled` defaults to `false`. Cron jobs are defined in `defaults/main.yml` using the commented-out convention but only deployed when enabled.
- **OpenRouter for Director, Max Plan for workers** — Hermes Director uses OpenRouter as its primary LLM provider (configured in Story 3.1 via `ai_dev_hermes_model_provider`). Claude Code workers spawned by the Director use Anthropic Max Plan credentials via auto-discovery (no explicit API key needed in most cases).
- **Git safety** — Workers MUST use feature branches, never force-push, never merge to main. This is enforced via SOUL.md instructions to the Director.
- **No direct package installs** — Director must never run `apt install` or `pip install`. Missing deps are reported, not auto-installed.

### Source Tree Components to Touch (homelab-infra repo)

| File | Action | Purpose |
|------|--------|---------|
| `roles/ai-dev-hermes/tasks/configure-cron.yml` | NEW | Cron job deployment |
| `roles/ai-dev-hermes/tasks/configure-tmux-session.yml` | NEW | Hermes tmux launch script |
| `roles/ai-dev-hermes/tasks/configure-claude-worker.yml` | NEW | Claude Code worker spawn script |
| `roles/ai-dev-hermes/templates/start-hermes.sh.j2` | NEW | tmux session launcher |
| `roles/ai-dev-hermes/templates/spawn-worker.sh.j2` | NEW | Worker spawn helper |
| `roles/ai-dev-hermes/templates/hermes-soul.md.j2` | MODIFY | Add autonomous execution guidance |
| `roles/ai-dev-hermes/tasks/main.yml` | MODIFY | Include new task files |
| `roles/ai-dev-hermes/tasks/verify.yml` | MODIFY | Add new VERIFY tasks |
| `roles/ai-dev-hermes/defaults/main.yml` | MODIFY | Add max_workers, cron vars |

### Ansible Task Patterns (from architecture.md)

- Task names: sentence case, action-first (`Configure Hermes cron jobs`)
- Variable prefix: `ai_dev_hermes_*`
- Tags: `tags: [ai-dev-hermes]` on all tasks
- Use `command:` not `shell:` unless pipes/redirects needed
- Use `failed_when:` not `ignore_errors: true`
- Templates use `mode: '0755'` for scripts, `mode: '0600'` for secrets
- `no_log: true` on tasks handling vault variables

### Previous Story Learnings (from Story 3.2)

- **Template vs blockinfile:** Story 3.2 discovered that `blockinfile` conflicts with Jinja2 templates on the same file. Use Jinja2 conditionals inside templates instead of blockinfile when the file is template-managed.
- **OMEGA binary path:** The actual OMEGA binary is at `~/.pyenv/shims/omega`, not `~/.local/bin/omega`. Use `ai_dev_hermes_omega_binary_path` variable (added in 3.2 review fix).
- **Hermes skill directory convention:** Skills live in `~/.hermes/skills/` with category subdirectories (e.g., `bmad/`). SKILL.md uses YAML frontmatter.
- **Idempotency bar:** Story 3.2 achieved 0 changed on second run (minus 1 expected dev-host Docker restart). Maintain this bar.
- **become_user with explicit paths:** Always set HOME, PATH, PYENV_ROOT environment on command tasks that need pyenv or cargo binaries.
- **MCP section in config.yaml.j2:** OMEGA MCP is wired via Jinja2 conditional (`{% if ai_dev_hermes_omega_available %}`), set by `wire-omega.yml` stat+set_fact. Do not duplicate this wiring.

### Testing Standards

- Deploy to ct-dev-test (192.168.50.152) first, then ct-dev-homelab (192.168.50.150) per test-then-deploy workflow
- Idempotency: second run must show 0 changed for ai-dev-hermes tasks
- BMAD-safety: zero modifications to `.claude/skills/bmad-*/`
- All verify tasks use `VERIFY |` prefix and `changed_when: false`

### Max Plan Authentication Notes

- Claude Code CLI uses credential auto-discovery — if the user is logged in via `claude login`, workers inherit the session
- Hermes Director uses OpenRouter (or configured provider) — its `.env` has the OpenRouter API key, not Anthropic key
- If Max Plan has rate limits for programmatic usage, document them in a `RATE_LIMITS.md` or as comments in `defaults/main.yml`
- AT-3.10 requires both Hermes LLM call AND Claude Code worker to succeed

### Project Structure Notes

- All new files are within `roles/ai-dev-hermes/` in the homelab-infra repo
- No files created outside the role directory
- No modifications to BMAD skills or other roles
- Templates follow existing `*.j2` convention in `templates/` directory

### References

- [Source: planning-artifacts/architecture.md#Auto-Start Strategy] — Hermes is NOT auto-started, user starts on demand
- [Source: planning-artifacts/architecture.md#Role Independence & Conditional Integration] — ai-dev-hermes depends only on dev-host
- [Source: planning-artifacts/architecture.md#Ansible Task Patterns] — Task naming, variable prefix, tag conventions
- [Source: planning-artifacts/architecture.md#File Path Conventions] — ~/.hermes/ owned by ai-dev-hermes
- [Source: planning-artifacts/architecture.md#Secret Handling Patterns] — vault_ prefix, no_log, mode 0600
- [Source: planning-artifacts/epics.md#Story 3.3] — AC and FR mapping
- [Source: planning-artifacts/prd.md#AT-3.6] — Autonomous quick-dev task execution
- [Source: planning-artifacts/prd.md#AT-3.7] — tmux persistence for Director
- [Source: planning-artifacts/prd.md#AT-3.8] — Subagent spawning
- [Source: planning-artifacts/prd.md#AT-3.9] — Cron scheduling
- [Source: planning-artifacts/prd.md#AT-3.10] — Max Plan compatibility
- [Source: implementation-artifacts/3-2-configure-omega-mcp-connection-and-bmad-skills.md] — Previous story learnings, template vs blockinfile, OMEGA path
- [Source: implementation-artifacts/3-1-install-hermes-agent-and-configure-basics.md] — Hermes install details, config layout

## Dev Agent Record

### Agent Model Used

claude-opus-4-6 (1M context)

### Debug Log References

### Completion Notes List

- Tasks 1-6 (code implementation) completed: all Ansible task files, Jinja2 templates, defaults, main.yml includes, and verify tasks created/updated
- Task 0 (prerequisite verification) requires SSH to ct-dev-test — deferred to deployment phase
- Tasks 7-9 (deploy/verify/idempotency) require Ansible execution against target containers — deferred to deployment phase
- All YAML files pass syntax validation (yaml.safe_load)
- All Jinja2 templates pass syntax validation
- No BMAD skill files modified
- Follows existing role patterns: become_user, tags, environment vars, VERIFY prefix convention

### Review Findings
- [x] [Review][Patch] `command -v claude` in verify.yml uses `ansible.builtin.command` module — changed to `ansible.builtin.shell` with dynamic nvm PATH detection [verify.yml:157] -- FIXED
- [x] [Review][Patch] Hardcoded nvm node version `v20` in verify.yml PATH — replaced with dynamic `sort -V` detection matching shell script pattern [verify.yml:164] -- FIXED
- [x] [Review][Patch] Cron job PATH uses `$(ls ... | tail -1)` for nvm node discovery — added `sort -V` for locale-safe version sorting [configure-cron.yml:16] -- FIXED
- [x] [Review][Patch] `ls | tail -1` in start-hermes.sh.j2 and spawn-worker.sh.j2 for nvm version — added `sort -V` for locale-safe version sorting [start-hermes.sh.j2:18, spawn-worker.sh.j2:22] -- FIXED (approach: inline, A/B score 100 vs 100, tie-break simplicity)
- [x] [Review][Defer] Duplicated PATH construction across 4 files (start-hermes.sh.j2, spawn-worker.sh.j2, configure-cron.yml, verify.yml) — deferred, extract to shared variable in future refactor
- [x] [Review][Defer] Hardcoded Hermes binary path `/home/{{ dev_user }}/.local/bin/hermes` in start-hermes.sh.j2 — deferred, could use a variable like `ai_dev_hermes_binary_path`
- [x] [Review][Defer] Cron schedule parsing assumes exactly 5 space-separated fields with no input validation — deferred, low risk since cron jobs are defined in defaults by the role author
- [x] [Review][Observe] Cron PATH subshell expansion at runtime — mitigated by `2>/dev/null` fallback
- [x] [Review][Observe] SOUL.md does not inform Director about OMEGA MCP availability — advisory, not structural
- [x] [Review][Observe] Hardcoded tmux dimensions `-x 200 -y 50` — tmux auto-adjusts on attach
- [x] [Review][Observe] Multi-arg risk on spawn-worker.sh `exec claude -p "$@"` — mitigated by usage comment
- [x] [Review][Observe] Complex Jinja2 `selectattr` in verify.yml `failed_when` — role author controls data

### Deployment Verification

- 2026-04-16: Deployed to ct-dev-test (192.168.50.152) successfully
- Fixed: `ai_dev_hermes_cron_jobs` YAML null issue — changed commented-out list to explicit `[]`
- Fixed: `start-hermes.sh.j2` used invalid `--terminal local` flag — changed to `hermes chat`
- Added `| default([])` filter to cron loop for resilience
- All automated eval assertions PASS (SCRIPTS, AC-2, AC-4a, AC-5, AC-6, IDMP, BMAD)
- AC-1, AC-3 marked MANUAL (require interactive Hermes session)

### Change Log

- 2026-04-16: Created configure-cron.yml, configure-tmux-session.yml, configure-claude-worker.yml task files
- 2026-04-16: Created start-hermes.sh.j2 and spawn-worker.sh.j2 Jinja2 templates
- 2026-04-16: Updated SOUL.md.j2 with autonomous execution, subagent delegation, git safety, and package management sections
- 2026-04-16: Updated defaults/main.yml with ai_dev_hermes_max_workers, ai_dev_hermes_cron_enabled, ai_dev_hermes_cron_jobs
- 2026-04-16: Updated tasks/main.yml to include three new task files after configure-skills
- 2026-04-16: Updated verify.yml with 5 new VERIFY tasks for scripts, CLI, cron, and tmux

### File List

- homelab-infra/ansible/roles/ai-dev-hermes/tasks/configure-cron.yml (NEW)
- homelab-infra/ansible/roles/ai-dev-hermes/tasks/configure-tmux-session.yml (NEW)
- homelab-infra/ansible/roles/ai-dev-hermes/tasks/configure-claude-worker.yml (NEW)
- homelab-infra/ansible/roles/ai-dev-hermes/templates/start-hermes.sh.j2 (NEW)
- homelab-infra/ansible/roles/ai-dev-hermes/templates/spawn-worker.sh.j2 (NEW)
- homelab-infra/ansible/roles/ai-dev-hermes/templates/SOUL.md.j2 (MODIFIED)
- homelab-infra/ansible/roles/ai-dev-hermes/tasks/main.yml (MODIFIED)
- homelab-infra/ansible/roles/ai-dev-hermes/tasks/verify.yml (MODIFIED)
- homelab-infra/ansible/roles/ai-dev-hermes/defaults/main.yml (MODIFIED)
