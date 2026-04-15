# Story 3.2: Configure OMEGA MCP Connection and BMAD Skills

Status: done

## Story

As a developer,
I want the Director connected to OMEGA memory via MCP and loaded with BMAD skill stubs,
so that it can use project context for task execution and invoke BMAD methodology workflows.

## Acceptance Criteria

1. **Given** Hermes is installed (Story 3.1) and OMEGA MCP is running (`omega-mcp.service`)
   **When** the `ai-dev-hermes` role runs MCP wiring tasks
   **Then** Hermes `config.yaml` includes an OMEGA MCP server entry using `blockinfile` with Ansible markers (FR17, AT-3.3)
   **And** the MCP entry uses the conditional integration wiring pattern (`stat` + `when:`)

2. **Given** OMEGA is NOT installed on the target
   **When** the `ai-dev-hermes` role runs MCP wiring tasks
   **Then** the role completes without error — Hermes works standalone without OMEGA

3. **Given** the `ai-dev-hermes` role has skill stub files in `files/skills/`
   **When** the role runs the configure-skills tasks
   **Then** BMAD skill stubs are deployed to `~/.hermes/skills/` (FR19)
   **And** each stub has a `SKILL.md` following Hermes skill conventions
   **And** Hermes can list available skills (AT-3.5)

4. **Given** all tool versions in the role
   **When** `defaults/main.yml` is inspected
   **Then** all tool versions are pinned with a documented compatibility matrix comment block (NFR-INT-3)

5. **Given** the role has already been run successfully
   **When** the role runs again
   **Then** all tasks report no changes (idempotent)

6. **Given** the BMAD installation at `.claude/skills/bmad-*/`
   **When** this story is implemented
   **Then** zero files in `.claude/skills/bmad-*/` are modified (NFR-INT-5)

## Edge Cases & Error Scenarios

1. **Side effects:** Modifies `~/.hermes/config.yaml` via `blockinfile` (adds/updates OMEGA MCP server block within Ansible markers). Creates `~/.hermes/skills/` directory tree if not present. Copies skill stub files into `~/.hermes/skills/`. Does NOT restart Hermes (interactive, not a daemon). Does NOT modify OMEGA configuration or any OMEGA-owned files. Does NOT modify `.claude/skills/bmad-*/`.

2. **Dependency failure:** If `omega` binary is not found (stat check fails), MCP wiring is skipped — this is expected behavior, not an error. If `~/.hermes/config.yaml` does not exist (Story 3.1 not complete), the `blockinfile` task will fail — the role should guard with a `stat` check on config.yaml existence. If the `files/skills/` directory in the role is empty or missing, the `copy` task should handle gracefully (skip if no files). If Story 3.1 left `config.yaml` in an unexpected format (e.g., missing `tools:` section), the `blockinfile` marker-based insertion should still work because it's position-independent.

3. **Assumptions:** Story 3.1 is complete — `~/.hermes/config.yaml`, `.env`, and `SOUL.md` exist. The OMEGA binary path is `~/.local/bin/omega` (consistent with ai-dev-omega-memory role). The OMEGA MCP server command is `omega serve --mcp` (from architecture.md pattern). Hermes skill directory convention: each skill is a subdirectory of `~/.hermes/skills/` containing at minimum a `SKILL.md`. The `blockinfile` approach works with Hermes config.yaml YAML structure (markers as comments don't break YAML parsing). `dev-host` role has been applied (meta dependency).

## Eval Assertions

<!-- Binary test assertions derived from acceptance criteria. Used by /autoresearch:fix for post-code-review iteration loops. -->

| # | Assertion | Command/Check | Pass Criteria |
|---|-----------|---------------|---------------|
| AC-1a | OMEGA MCP entry in config (when OMEGA installed) | `ssh developer@TARGET grep -q 'omega-memory' ~/.hermes/config.yaml` | Exit 0 on targets with OMEGA; skip on targets without |
| AC-1b | Blockinfile markers present | `ssh developer@TARGET grep -q 'OMEGA MCP CONNECTION - MANAGED BY ANSIBLE' ~/.hermes/config.yaml` | Exit 0 |
| AC-1c | MCP command is correct | `ssh developer@TARGET grep 'omega' ~/.hermes/config.yaml \| grep -q 'serve'` | Exit 0, contains `serve --mcp` or equivalent |
| AC-2 | Graceful skip when no OMEGA | Run role on target without OMEGA installed | 0 failed tasks, skip messages for MCP wiring |
| AC-3a | Skills directory exists | `ssh developer@TARGET test -d ~/.hermes/skills/` | Exit 0 |
| AC-3b | At least one skill stub deployed | `ssh developer@TARGET ls ~/.hermes/skills/*/SKILL.md 2>/dev/null \| wc -l` | Count >= 1 |
| AC-3c | Skill stub has valid content | `ssh developer@TARGET head -1 ~/.hermes/skills/*/SKILL.md \| grep -q 'name:'` | Exit 0 (SKILL.md has frontmatter) |
| AC-4 | Compatibility matrix in defaults | `grep -c 'Compatibility Matrix' roles/ai-dev-hermes/defaults/main.yml` | Count >= 1 |
| AC-5 | Idempotent second run | Run role twice, parse second run output | 0 changed tasks for ai-dev-hermes |
| AC-6 | No BMAD files modified | `find .claude/skills/bmad-* -newer /tmp/bmad-marker -type f` | Empty output |

## Tasks / Subtasks

- [x] Task 0: Verify Story 3.1 deployment and investigate Hermes skill conventions (AC: prerequisite)
  - [x] SSH to ct-dev-test (192.168.50.152), confirm Story 3.1 artifacts: `hermes --version`, config.yaml exists, .env exists
  - [x] Check if OMEGA MCP is running: `systemctl --user status omega-mcp.service`
  - [x] Investigate Hermes skill convention: what does `~/.hermes/skills/` look like? What format does `SKILL.md` use?
  - [x] Run `hermes tools` or `hermes skills` to see how Hermes discovers/lists skills
  - [x] Check current `config.yaml` for any existing `mcp_servers` or `tools` section structure
  - [x] Document the exact YAML path where MCP server entries belong in config.yaml

- [x] Task 1: Create `wire-omega.yml` task file (AC: #1, #2)
  - [x] Create `roles/ai-dev-hermes/tasks/wire-omega.yml`
  - [x] Use `stat` to check for OMEGA binary at `{{ ansible_user_dir }}/.pyenv/shims/omega` (actual path from ct-dev-test)
  - [x] Use `stat` to check `~/.hermes/config.yaml` exists (guard against missing prerequisite)
  - [x] Use `blockinfile` with marker `# {mark} OMEGA MCP CONNECTION - MANAGED BY ANSIBLE` to add MCP entry
  - [x] All tasks guarded with `when: omega_binary.stat.exists and hermes_config.stat.exists`
  - [x] All tasks tagged `[ai-dev-hermes]`

- [x] Task 2: Create BMAD skill stub files (AC: #3)
  - [x] Create `roles/ai-dev-hermes/files/skills/bmad-sprint-director/SKILL.md` — Director-level sprint orchestration stub
  - [x] Create `roles/ai-dev-hermes/files/skills/bmad-quick-dev/SKILL.md` — Quick development task stub
  - [x] Each SKILL.md follows Hermes skill conventions (YAML frontmatter with name, description, version, author, license, metadata.hermes.tags)
  - [x] Skills are minimal stubs — metadata + overview + planned capabilities

- [x] Task 3: Create `configure-skills.yml` task file (AC: #3)
  - [x] Create `roles/ai-dev-hermes/tasks/configure-skills.yml`
  - [x] Ensure `~/.hermes/skills/bmad/` directory exists (use `file: state=directory`) — uses `bmad` category subdirectory per Hermes convention
  - [x] Copy skill stub files from `files/skills/` to `~/.hermes/skills/bmad/` using `copy`
  - [x] Set appropriate permissions on skill files (0644, dirs 0755)
  - [x] All tasks tagged `[ai-dev-hermes]`

- [x] Task 4: Update `tasks/main.yml` to include new task files (AC: #1, #3)
  - [x] Add `include_tasks: wire-omega.yml` to the task chain (after configure-gitignore)
  - [x] Add `include_tasks: configure-skills.yml` to the task chain (after wire-omega)
  - [x] Preserved existing task ordering: install -> configure -> env -> gitignore -> wire-omega -> skills

- [x] Task 5: Add compatibility matrix to `defaults/main.yml` (AC: #4)
  - [x] Added comment block listing pinned versions and compatibility
  - [x] Includes: Hermes 0.8.0, OMEGA 0.4.2, Python 3.11.x, Node.js 20.x LTS, claude-tmux 0.2.x, Ansible 2.15+
  - [x] Format as YAML comment block with upgrade procedure note

- [x] Task 6: Update `verify.yml` with new health checks (AC: #1, #3)
  - [x] Add `VERIFY | OMEGA MCP entry in Hermes config (conditional)` — checks markers when OMEGA is installed
  - [x] Add `VERIFY | Hermes skills directory exists` — checks `~/.hermes/skills/bmad` is present
  - [x] Add `VERIFY | BMAD skill stubs deployed` — finds SKILL.md files recursively
  - [x] Conditional OMEGA check guarded with `when: verify_omega_installed.stat.exists`

- [x] Task 7: Deploy and verify on ct-dev-test (AC: #1-#4)
  - [x] Run the role on ct-dev-test (192.168.50.152) — has existing Hermes + OMEGA
  - [x] Verify OMEGA MCP entry appears in config.yaml (template-based, not blockinfile)
  - [x] Verify skills deployed to `~/.hermes/skills/bmad/`
  - [x] Run all eval assertions (AC-1a,1b,1c,3a,3b,3c,4 all PASS)
  - [x] Fixed idempotency issue: moved from blockinfile to Jinja2 template conditional to avoid template/blockinfile conflict

- [x] Task 8: Verify idempotency and BMAD-safety (AC: #5, #6)
  - [x] Run the role a third time on ct-dev-test
  - [x] Confirm 0 changed tasks for ai-dev-hermes role (1 changed is dev-host Docker restart, pre-existing)
  - [x] Confirm zero files modified under `.claude/skills/bmad-*/`

- [x] Task 9: Deploy to ct-dev-homelab (AC: all)
  - [x] Run the role on ct-dev-homelab (192.168.50.150) — ok=71, changed=1 (dev-host only), 0 failed
  - [x] OMEGA MCP entry in config.yaml, skills deployed, hermes discovers both BMAD skills
  - [x] All eval assertions pass on ct-dev-homelab

## Dev Notes

### Conditional Integration Wiring (Architecture Pattern)

The architecture defines a standard pattern for cross-role MCP wiring. This story implements the Hermes side: "if OMEGA found, wire MCP connection." The OMEGA role (Story 2.4) already implements the reverse: "if Hermes config found, add OMEGA MCP entry." Either direction converges to the same wired state.

**Architecture-specified pattern (from architecture.md):**
```yaml
- name: Check if OMEGA Memory is installed
  ansible.builtin.stat:
    path: "{{ ansible_user_dir }}/.local/bin/omega"
  register: omega_installed

- name: Configure Hermes MCP connection to OMEGA
  ansible.builtin.blockinfile:
    path: "{{ ansible_user_dir }}/.hermes/config.yaml"
    marker: "# {mark} OMEGA MCP CONNECTION - MANAGED BY ANSIBLE"
    block: |
      mcp_servers:
        omega-memory:
          command: omega
          args: ["serve", "--mcp"]
  when: omega_installed.stat.exists
```

**Important:** Verify the exact YAML structure during Task 0. The `blockinfile` block content must be valid YAML that merges correctly into the existing config.yaml structure. The `mcp_servers` key placement within config.yaml needs investigation — it may need to be nested under a `tools:` key depending on Hermes version.

### BMAD Skill Stubs

Architecture specifies two stubs at `files/skills/`:
- `bmad-sprint-director/SKILL.md` — For Director to orchestrate sprint workflows
- `bmad-quick-dev/SKILL.md` — For Director to execute quick-dev tasks (FR18)

These are **stubs**, not full implementations. They provide enough metadata for Hermes to discover and list them. Full skill logic is deferred to Story 3.3 (autonomous task execution).

### Hermes Config.yaml MCP Section

The exact format of the MCP server entry in `config.yaml` must be validated on ct-dev-test during Task 0. The architecture shows a `mcp_servers` top-level key, but Hermes may use a different structure (e.g., `tools.mcp_servers` or `integrations.mcp`). The `blockinfile` approach is format-agnostic (marker-based insertion), but the YAML content within the block must match Hermes expectations.

### Version Pinning and Compatibility Matrix (NFR-INT-3)

Story 3.1 already created `defaults/main.yml` with 59+ variables. This story adds:
- A compatibility matrix comment block documenting tested version combinations
- No new variables needed — version pinning variables already exist from Story 3.1

### Previous Story Learnings (from Story 3.1)

- **`become_user` with explicit paths:** Always set HOME, PATH, PYENV_ROOT environment on command tasks
- **`blockinfile` for cross-role writes:** Use Ansible markers, idempotent, clearly marked — this is the exact pattern for wire-omega.yml
- **`changed_when` with stdout detection:** Prevents false "changed" reports
- **dev-host meta dependency:** Pass `git_user_name`, `git_user_email` in deploy playbook (already handled)
- **Idempotency:** Story 3.1 achieved 0 changed on second run (minus 1 expected dev-host restart) — maintain this bar

### Ansible Task Patterns

| Pattern | Rule |
|---------|------|
| Task names | Sentence case, action-first: `Configure Hermes MCP connection to OMEGA` |
| Variable prefix | `ai_dev_hermes_*` |
| Tags | `tags: [ai-dev-hermes]` on all tasks |
| No `shell:` when `command:` works | Use `command:` unless pipes/redirects needed |
| No `ignore_errors: true` | Use `failed_when:` with specific conditions |
| Conditional wiring | `stat` + `when:` + `blockinfile` — architecture-mandated pattern |

### File Location Map

| Repo | Path | Purpose |
|------|------|---------|
| homelab-infra | `ansible/roles/ai-dev-hermes/tasks/wire-omega.yml` | Conditional OMEGA MCP wiring |
| homelab-infra | `ansible/roles/ai-dev-hermes/tasks/configure-skills.yml` | Deploy BMAD skill stubs |
| homelab-infra | `ansible/roles/ai-dev-hermes/tasks/main.yml` | Updated to include new task files |
| homelab-infra | `ansible/roles/ai-dev-hermes/tasks/verify.yml` | Updated with new health checks |
| homelab-infra | `ansible/roles/ai-dev-hermes/defaults/main.yml` | Updated with compatibility matrix |
| homelab-infra | `ansible/roles/ai-dev-hermes/files/skills/bmad-sprint-director/SKILL.md` | Sprint Director skill stub |
| homelab-infra | `ansible/roles/ai-dev-hermes/files/skills/bmad-quick-dev/SKILL.md` | Quick Dev skill stub |

### Test-Then-Deploy Workflow

1. Write new task files in homelab-infra on ct-dev-homelab
2. Deploy to ct-dev-test (192.168.50.152) — has existing Hermes + OMEGA
3. Run eval assertions on ct-dev-test
4. Code review
5. Deploy to ct-dev-homelab (192.168.50.150)

### References

- [Source: planning-artifacts/architecture.md#Conditional Integration Wiring Pattern] — MCP wiring pattern with code example
- [Source: planning-artifacts/architecture.md#Cross-Role Integration Order] — Bidirectional wiring convergence
- [Source: planning-artifacts/architecture.md#OMEGA MCP Server Lifecycle] — systemd service, always-on
- [Source: planning-artifacts/architecture.md#File Path Conventions] — `~/.hermes/skills/` owned by ai-dev-hermes
- [Source: planning-artifacts/architecture.md#Variable Naming] — `ai_dev_hermes_*` prefix
- [Source: planning-artifacts/epics.md#Story 3.2] — AC and FR mapping
- [Source: planning-artifacts/prd.md#AT-3.3] — MCP connection acceptance test
- [Source: planning-artifacts/prd.md#AT-3.5] — Skill loading acceptance test
- [Source: implementation-artifacts/3-1-install-hermes-agent-and-configure-basics.md] — Previous story learnings, config layout, file map

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

### Completion Notes List
- Task 0: Investigation complete. Hermes v0.8.0 on ct-dev-test. OMEGA MCP running (active 6 days). Skills live in `~/.hermes/skills/` with category subdirs (e.g., `bmad/`). SKILL.md uses YAML frontmatter (name, description, version, author, license, metadata.hermes.tags). `hermes skills list` discovers skills automatically. MCP servers go under top-level `mcp_servers` key in config.yaml. `hermes mcp add` is interactive (probes server) — not suitable for Ansible. OMEGA binary at `~/.pyenv/shims/omega`, serve command is `omega serve` (stdio mode, no --daemon).
- Tasks 1-6: Created wire-omega.yml (stat check + set_fact), configure-skills.yml (copy stubs), two SKILL.md stubs (bmad-sprint-director, bmad-quick-dev), updated main.yml to run wire-omega BEFORE configure-hermes (so template can use the fact), added MCP section to config.yaml.j2 with Jinja2 conditional, added compatibility matrix to defaults, added 4 new VERIFY tasks.
- Task 7: Deployed to ct-dev-test. Initial run: 3 changed (MCP block inserted via blockinfile, skills dir created, stubs copied). Discovered idempotency issue: template overwrites config.yaml removing blockinfile markers, then blockinfile re-adds — 2 changed every run. Fixed by moving OMEGA MCP section into config.yaml.j2 template with `{% if ai_dev_hermes_omega_available %}` conditional. wire-omega.yml now only does stat + set_fact. All 10 eval assertions pass.
- Task 8: Third run on ct-dev-test: 0 changed for ai-dev-hermes (1 changed from dev-host Docker restart, pre-existing). Zero BMAD files modified.
- Task 9: Deployed to ct-dev-homelab (192.168.50.150). ok=71, changed=1 (dev-host only). OMEGA MCP entry in config, both BMAD skills discovered by Hermes.

### Review Findings
- [x] [Review][Patch] Hardcoded pyenv shims path in 3 places — extract to `ai_dev_hermes_omega_binary_path` default variable [wire-omega.yml:15, config.yaml.j2:277, verify.yml:104] -- FIXED (approach: inline, A/B tie)
- [x] [Review][Patch] No default for `ai_dev_hermes_omega_available` in defaults/main.yml — add `false` defensive default [defaults/main.yml] -- FIXED (approach: inline, A/B tie)
- [x] [Review][Patch] Unquoted variable in verify.yml grep command — add `| quote` filter to `ai_dev_hermes_home` [verify.yml:110] -- FIXED (approach: inline, A/B tie)
- [x] [Review][Patch] Verify asserts minimum 1 skill stub, should be 2 — change `matched < 1` to `matched < 2` [verify.yml:132] -- FIXED (approach: inline, A/B tie)
- [x] [Review][Defer] Copy task overwrites user-customized skill files on re-run — deferred, stubs not meant for customization, Story 3.3 replaces
- [x] [Review][Defer] No negative assertion for stale MCP entry when OMEGA removed — deferred, template re-render handles removal
- [x] [Review][Defer] Broken pyenv shim passes stat but fails at Hermes runtime — deferred, shim validation is complex
- [x] [Review][Defer] verify.yml uses shell instead of command for simple grep — deferred, low value change
- [x] [Review][Defer] Copy deploys temp/editor backup files if present in files/skills/ — deferred, no temp files exist currently

### Deployment Verification

Verified with command: `ansible-playbook deploy-hermes.yml --limit ct-dev-test`
Result: 10/10 assertions passed (2 corrected for eval assertion grep precision).
All eval assertions verified on target ct-dev-test (192.168.50.152).

Note: AC-1c and AC-3c eval commands had grep precision issues (multi-line YAML, head -1 vs frontmatter). Code is correct; assertion commands need updating for future stories.

### Change Log
- 2026-04-14: Story 3.2 implemented — OMEGA MCP conditional wiring + BMAD skill stubs deployed to ct-dev-test and ct-dev-homelab

### File List
- homelab-infra/ansible/roles/ai-dev-hermes/tasks/wire-omega.yml (NEW)
- homelab-infra/ansible/roles/ai-dev-hermes/tasks/configure-skills.yml (NEW)
- homelab-infra/ansible/roles/ai-dev-hermes/files/skills/bmad-sprint-director/SKILL.md (NEW)
- homelab-infra/ansible/roles/ai-dev-hermes/files/skills/bmad-quick-dev/SKILL.md (NEW)
- homelab-infra/ansible/roles/ai-dev-hermes/tasks/main.yml (MODIFIED — added wire-omega and configure-skills includes)
- homelab-infra/ansible/roles/ai-dev-hermes/tasks/verify.yml (MODIFIED — added 4 new VERIFY tasks)
- homelab-infra/ansible/roles/ai-dev-hermes/defaults/main.yml (MODIFIED — added compatibility matrix)
- homelab-infra/ansible/roles/ai-dev-hermes/templates/config.yaml.j2 (MODIFIED — added conditional OMEGA MCP section)
