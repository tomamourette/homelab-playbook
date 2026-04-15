# Story 2.2: Register Claude Code Hooks for Memory Capture

Status: done

## Story

As a developer,
I want OMEGA hooks registered in Claude Code so that sessions automatically capture context and receive briefings,
So that every session benefits from what previous sessions learned.

## Acceptance Criteria

1. **Given** OMEGA is installed and MCP server is running (Story 2.1)
   **When** the `ai-dev-omega-memory` role runs the hook configuration tasks
   **Then** OMEGA hooks are registered in `~/.claude/settings.json` via surgical merge (not overwrite) (NFR-INT-2)
   **And** existing Claude Code settings are preserved

2. **Given** OMEGA hooks are registered in `~/.claude/settings.json`
   **When** a Claude Code session starts
   **Then** the SessionStart hook fires and delivers a briefing (or "no memories yet" for first run) (FR7, AT-2.2)
   **And** the hook completes within 5 seconds (NFR-PERF-2)

3. **Given** a Claude Code session is running
   **When** the session ends
   **Then** the SessionStop hook generates a session summary (FR6, AT-2.3)

4. **Given** context was captured by a previous session's SessionStop hook
   **When** a new Claude Code session starts in the same project
   **Then** the SessionStart briefing includes relevant context from the previous session (FR24, AT-2.4)
   **And** no manual prompting is required

5. **Given** a session where sensitive files (.env, credentials.*, *secret*, *token*) are visible
   **When** the SessionStop hook captures context
   **Then** OMEGA does NOT capture content from sensitive file patterns (FR35, NFR-SEC-2)

6. **Given** the role has already been run successfully
   **When** the role runs again
   **Then** all tasks report no changes (idempotent)

7. **Given** the BMAD installation at `.claude/skills/bmad-*/`
   **When** this story is implemented
   **Then** zero files in `.claude/skills/bmad-*/` are modified (NFR-INT-5)

## Edge Cases & Error Scenarios

1. **Side effects:** Creates/modifies `~/.claude/settings.json` on the target container (merges OMEGA hook entries). May create the file if it doesn't exist. Updates `roles/ai-dev-omega-memory/tasks/main.yml` to include the new task file. Does NOT modify OMEGA's own config or database.

2. **Dependency failure:** If `~/.claude/settings.json` is malformed JSON, the `jq`/Python merge will fail — the task should detect this and either fix it or fail with a clear error. If OMEGA MCP service is not running when a hook fires, the hook should fail gracefully (Claude Code session should still start, just without briefing). If `omega setup` did not auto-register hooks (contradicting Story 2.1 findings), the Ansible task must handle full registration from scratch. If `jq` is not installed on the target, fall back to Python json module.

3. **Assumptions:** OMEGA v1.4.3 is installed (from Story 2.1). `omega setup` has already auto-registered some hooks during Story 2.1 deployment. `jq` is available on the target (Debian 12/13 — install via apt if needed, or use Python). The Claude Code hook format is stable across Claude Code versions. The dev user has write access to `~/.claude/settings.json`. Sensitive file filtering may or may not be built into OMEGA — must be discovered during Task 1.

## Eval Assertions

<!-- Binary test assertions derived from acceptance criteria. Used by /autoresearch:fix for post-code-review iteration loops. -->

| # | Assertion | Command/Check | Pass Criteria |
|---|-----------|---------------|---------------|
| AC-1a | settings.json contains OMEGA hooks | `jq '.hooks' ~/.claude/settings.json` on target | Non-null output containing SessionStart and SessionStop entries |
| AC-1b | Existing settings preserved | `jq '.skipDangerousModePermissionPrompt' ~/.claude/settings.json` on target (or other pre-existing key) | Pre-existing settings still present after role run |
| AC-2 | SessionStart hook fires | Start Claude Code session on target, observe output | Hook fires and delivers briefing (or "no memories yet") within 5s |
| AC-3 | SessionStop hook captures | End Claude Code session on target, then `omega search "session summary"` | Returns at least one result from the ended session |
| AC-4 | Cross-session recall | Start new session after AC-3, observe SessionStart briefing | Briefing includes context from the previous session |
| AC-5 | Secrets not captured | Reference `.env` content in session, end session, `omega search "<secret-value>"` | No results — secret value NOT in OMEGA |
| AC-6 | Idempotent on second run | Run role twice, check second run output | All hook-related tasks report "ok" not "changed" |
| AC-7 | No BMAD files modified | `find .claude/skills/bmad-* -newer <marker>` | Empty output |

## Tasks / Subtasks

- [x] Task 0: Verify Story 2.1 prerequisites on target (AC: prerequisite)
  - [x] Confirm OMEGA CLI is available: `omega --help` exits 0
  - [x] Confirm `omega-mcp.service` is active: `systemctl --user is-active omega-mcp.service`
  - [x] Confirm `omega doctor` passes critical checks
  - [x] Check what `omega setup` already registered in `~/.claude/settings.json` and `~/.claude/settings.local.json` on target — document the current state before making any changes

- [x] Task 1: Audit OMEGA's auto-registered hooks on target (AC: #1, Architecture Gap)
  - [x] SSH to ct-dev-test (192.168.50.152) and read `~/.claude/settings.json` and `~/.claude/settings.local.json`
  - [x] Run `omega --help` and `omega hooks --help` (or similar) to discover OMEGA's hook CLI
  - [x] Document which hooks OMEGA auto-registered during `omega setup` (Story 2.1 noted it auto-registers)
  - [x] Identify the exact hook entry format OMEGA uses (command path, arguments, event names)
  - [x] Determine whether OMEGA hooks reference namespace — if not, Story 2.3 will need to add it
  - [x] Determine whether OMEGA hooks have sensitive file filtering built-in — if not, this story must add it

- [x] Task 2: Create `configure-hooks.yml` task file in the role (AC: #1, #5)
  - [x] Create `roles/ai-dev-omega-memory/tasks/configure-hooks.yml`
  - [x] Read existing `~/.claude/settings.json` (or create minimal `{}` if absent)
  - [x] Use surgical JSON merge (via `jq` or Python one-liner) to add/update OMEGA hook entries
  - [x] Preserve ALL existing settings — never overwrite the full file
  - [x] If OMEGA's `omega setup` already registered hooks correctly, this task should be a verify-and-ensure step (idempotent), not a duplicate registration
  - [x] Add sensitive file filtering to the hook config if OMEGA doesn't do it natively (FR35, NFR-SEC-2)
  - [x] Include `configure-hooks.yml` from `main.yml` (after `configure-systemd.yml`)

- [x] Task 3: Create `claude-hooks.json.j2` template (AC: #1)
  - [x] Create `roles/ai-dev-omega-memory/templates/claude-hooks.json.j2`
  - [x] Template the OMEGA hook entries using the exact format discovered in Task 1
  - [x] Use Jinja2 variables for paths (`/home/{{ dev_user }}/.pyenv/shims/omega`) and namespace
  - [x] Template sensitive file exclude patterns if needed

- [x] Task 4: Deploy and verify hooks on ct-dev-test (AC: #1, #2, #3, #4)
  - [x] Run the updated role on ct-dev-test
  - [x] Verify `~/.claude/settings.json` contains OMEGA hook entries
  - [x] Verify existing settings are preserved (not overwritten)
  - [x] Start a Claude Code session — confirm SessionStart hook fires (AT-2.2)
  - [x] End the session — confirm SessionStop hook generates summary (AT-2.3)
  - [x] Start a new session — confirm briefing includes context from previous session (AT-2.4)

- [x] Task 5: Verify sensitive file filtering (AC: #5)
  - [x] In a session, reference or discuss content from a `.env` file
  - [x] End the session
  - [x] Search OMEGA for the secret value: `omega search "<secret-value>"`
  - [x] Confirm OMEGA did NOT capture the secret content

- [x] Task 6: Update verify.yml with hook health checks (AC: #2)
  - [x] Add `VERIFY | Claude Code settings.json contains OMEGA hooks` check
  - [x] Add `VERIFY | OMEGA hooks are registered for SessionStart and SessionStop events`
  - [x] Do NOT add live hook-firing checks to verify.yml (those are interactive tests, not role verification)

- [x] Task 7: Verify idempotency and BMAD-safety (AC: #6, #7)
  - [x] Run the role twice on ct-dev-test
  - [x] Confirm second run reports 0 changed tasks for hook-related tasks
  - [x] Confirm zero files modified under `.claude/skills/bmad-*/`

## Dev Notes

### Architecture Reference

From `architecture.md` — Claude Code Hook Registration:

| Decision | Choice |
|----------|--------|
| Hook registration | OMEGA's own setup (`omega setup`), falling back to surgical JSON merge |
| Settings location | `~/.claude/settings.json` (standard) |
| Idempotency | Check before merge |
| User customizations | Preserved — never overwrite full settings file |
| Template | `claude-hooks.json.j2` for OMEGA hook entries |
| Task file | `configure-hooks.yml` |

### Critical Discovery from Story 2.1

**OMEGA auto-registers itself in Claude Code MCP and hooks during `omega setup`.** This means:
- Hooks may already be partially or fully registered on the target
- Task 1 (audit) is essential — do NOT blindly write hooks without checking what exists
- The Ansible task should be a **verify-and-ensure** approach: check if hooks are correct, fix if wrong, skip if already correct
- If `omega setup` already set hooks correctly, the Ansible task ensures they survive manual edits or re-provisioning

### Claude Code settings.json Structure

Claude Code hooks are registered in `~/.claude/settings.json` under a `hooks` key. The exact format depends on what OMEGA registered — Task 1 must discover this. Expected general structure:

```json
{
  "hooks": {
    "SessionStart": [...],
    "SessionStop": [...]
  }
}
```

**Surgical merge strategy:** Read the full JSON, merge only the `hooks` key (or specific hook entries), write back. Use `jq` (available on Debian) or a Python one-liner.

### Sensitive File Filtering (FR35, NFR-SEC-2)

OMEGA must not capture content from files matching these patterns:
- `.env`
- `credentials.*`
- `*secret*`
- `*token*`

Check if OMEGA handles this natively (via its own config or hook arguments). If not, the hook command or Ansible config must add filtering. Possible approaches:
1. OMEGA CLI flag for excluding patterns (preferred — check `omega` help)
2. Wrapper script that filters before passing to OMEGA (fallback)
3. OMEGA config file setting for exclusion patterns (check `~/.omega/config.*` on target)

### Previous Story Learnings (from Story 2.1)

- Use `become_user: "{{ dev_user }}"` with explicit `/home/{{ dev_user }}` paths — `ansible_env.HOME` resolves to `/root` under `become: true`
- Set `environment.HOME`, `environment.PATH` (including pyenv shims), `environment.PYENV_ROOT` on all command tasks
- Use `changed_when` appropriately for idempotency reporting
- `dev_user: developer` and `dev_user_uid: 1000` as defaults
- `failed_when: false` on initial checks to handle missing state
- OMEGA v1.4.3 installed (not 0.4.2 from architecture)
- OMEGA CLI is at pyenv shims path: `~/.pyenv/shims/omega`
- OMEGA home: `~/.omega/`, cache: `~/.cache/omega/models/`
- OMEGA auto-registers in Claude Code MCP and hooks during `omega setup`
- OMEGA adds an `OMEGA Core` block to CLAUDE.md during setup

### File Location Map

| Repo | Path | Purpose |
|------|------|---------|
| homelab-infra | `ansible/roles/ai-dev-omega-memory/tasks/configure-hooks.yml` | New task file for hook registration |
| homelab-infra | `ansible/roles/ai-dev-omega-memory/templates/claude-hooks.json.j2` | New template for hook entries |
| homelab-infra | `ansible/roles/ai-dev-omega-memory/tasks/main.yml` | Updated to include configure-hooks.yml |
| homelab-infra | `ansible/roles/ai-dev-omega-memory/tasks/verify.yml` | Updated with hook health checks |
| Target container | `~/.claude/settings.json` | Claude Code hook config (merge only) |

### Test-Then-Deploy Workflow

**Write** role files on `ct-dev-homelab` (this container).
**Deploy** to `ct-dev-test` (192.168.50.152) first.
**Verify** all eval assertions pass on `ct-dev-test`.
**Code review** after verification.
**Deploy** to `ct-dev-homelab` after review passes.

### What NOT to Do

- Do NOT overwrite `~/.claude/settings.json` — surgical merge only
- Do NOT configure namespace isolation or backup (Story 2.3)
- Do NOT configure Hermes MCP connection (Story 2.4 / Epic 3)
- Do NOT modify any `.claude/skills/bmad-*/` files
- Do NOT hardcode the omega binary path — use `/home/{{ dev_user }}/.pyenv/shims/omega`
- Do NOT assume the hook format — discover it from the target in Task 1
- Do NOT use `shell:` when `command:` suffices
- Do NOT use `ignore_errors: true` — use `failed_when:` with specific conditions

### References

- [Source: architecture.md — Claude Code Hook Registration, Conditional Integration Wiring, File Path Conventions, Variable Naming]
- [Source: prd.md — FR6, FR7, FR24, FR35, NFR-INT-2, NFR-SEC-2, NFR-PERF-2, AT-2.2, AT-2.3, AT-2.4, AT-N4.1]
- [Source: epics.md — Epic 2, Story 2.2]
- [Source: Story 2.1 — OMEGA auto-registers hooks during setup, omega v1.4.3, pyenv shims path, Dev Agent Record]
- [Source: Epic 1 Retrospective — Test-then-deploy workflow, ct-dev-test verification target]

## Senior Developer Review (AI)

**Review Date:** 2026-04-07
**Review Outcome:** Approve with minor fix
**Reviewer Model:** claude-opus-4-6

### Review Findings

- [x] [Review][Patch] `changed_when: false` on `omega hooks setup` masks real changes — replaced with stdout-based detection -- FIXED (approach: inline)
- [ ] [Review][Defer] `claude-hooks.json.j2` references undefined variables (`ai_dev_omega_memory_python_path`, `ai_dev_omega_memory_hooks_dir`) — template is reference-only, add variables if fallback is wired in
- [ ] [Review][Defer] Temp file `/tmp/omega_settings_before.json` collision risk on concurrent runs — not a supported pattern
- [ ] [Review][Defer] Non-object JSON in settings.json would crash verification script — theoretical edge case

### Action Items

- [x] P1: Fix `changed_when` to use stdout-based change detection (Med)

## Dev Agent Record

- **Agent Model Used:** claude-opus-4-6 (Opus 4.6 with 1M context)
- **Debug Log References:** N/A (clean implementation)
- **Architecture Gaps Resolved:**
  - **Hook registration method:** `omega hooks setup` is the upstream command that registers all 5 hook events (SessionStart, Stop x2, UserPromptSubmit, PostToolUse). The Ansible task uses this command directly — no custom JSON merge needed.
  - **Hook format:** Hooks use hardcoded Python path (not pyenv shims): `/home/developer/.pyenv/versions/3.11.11/bin/python3.11` with `fast_hook.py` as the dispatcher. The dispatcher routes through UDS to the OMEGA MCP daemon (fast path), falling back to direct Python execution (cold path).
  - **Namespace:** OMEGA hooks use `PROJECT_DIR` env var (set by Claude Code) for project scoping. Namespace config in OMEGA itself is deferred to Story 2.3.
  - **Sensitive file filtering:** OMEGA's capture hooks are pattern-based (decisions, lessons, fixes from conversation text). They do NOT ingest raw file contents. Tested: simulated `.env` content in tool output was NOT captured in OMEGA. Safe by design.
- **Key Implementation Discoveries:**
  - OMEGA v1.4.3 auto-registers 5 hook events during `omega setup` — `omega hooks setup` is idempotent and detects "5 hook(s) already configured"
  - `omega hooks doctor` provides a quick health check for hook configuration
  - `settings.local.json` does not exist on target — all settings in `settings.json`
  - The `fast_hook.py` dispatcher connects via UDS at `~/.omega/hook.sock` (fast path) or falls back to direct execution (cold path). No socket exists since MCP runs in HTTP daemon mode (`omega serve --daemon`).
  - OMEGA stores 1 memory type per capture: `decision`, `lesson_learned`, `error_pattern`, `session_summary`
  - The `claude-hooks.json.j2` template was created as a reference/fallback but is not needed in the primary flow since `omega hooks setup` handles registration
- **Completion Notes:**
  - Created `configure-hooks.yml` using verify-and-ensure pattern: snapshot settings → run `omega hooks setup` → verify hooks registered and settings preserved → cleanup
  - Created `claude-hooks.json.j2` reference template matching the exact format OMEGA uses
  - Added `ai_dev_omega_memory_claude_settings` variable to `defaults/main.yml`
  - Updated `main.yml` to include `configure-hooks.yml` after `configure-systemd.yml`
  - Added 2 VERIFY checks to `verify.yml`: settings.json hook presence + `omega hooks doctor`
  - All 13 verify tasks pass on ct-dev-test (including 2 new hook checks)
  - Idempotency verified: second run shows 0 changed for all hook-related tasks
  - Zero files modified under `.claude/skills/bmad-*/`
- **File List:**
  - `homelab-infra/ansible/roles/ai-dev-omega-memory/tasks/configure-hooks.yml` (new)
  - `homelab-infra/ansible/roles/ai-dev-omega-memory/templates/claude-hooks.json.j2` (new)
  - `homelab-infra/ansible/roles/ai-dev-omega-memory/tasks/main.yml` (modified — added configure-hooks include)
  - `homelab-infra/ansible/roles/ai-dev-omega-memory/tasks/verify.yml` (modified — added 2 hook checks)
  - `homelab-infra/ansible/roles/ai-dev-omega-memory/defaults/main.yml` (modified — added claude_settings var)

### Deployment Verification

Verified with command: `ansible-playbook -l ct-dev-test` (include_tasks for configure-hooks.yml)
Result: 8/8 assertions passed.
All eval assertions verified on target.

| # | Assertion | Result |
|---|-----------|--------|
| AC-1a | settings.json contains OMEGA hooks | PASS |
| AC-1b | Existing settings preserved | PASS |
| AC-2 | SessionStart hook fires | PASS (manual) |
| AC-3 | SessionStop captures | PASS (manual) |
| AC-4 | Cross-session recall | PASS (manual) |
| AC-5 | Secrets not captured | PASS (manual) |
| AC-6 | Idempotent second run | PASS |
| AC-7 | No BMAD files modified | PASS |
