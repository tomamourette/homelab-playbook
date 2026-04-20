# Story 6.6: Create MemPalace Ansible Role

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a homelab operator,
I want the ai-dev-mempalace Ansible role completed to full convention (matching ai-dev-omega-memory's structure: meta, handlers, verify, conditional Hermes wiring, group_vars),
So that MemPalace is deployable via the existing one-command playbook with the same quality bar as every other ai-dev-* role.

## Acceptance Criteria

1. **Given** the existing `ai-dev-mempalace` role at `homelab-infra/ansible/roles/ai-dev-mempalace/`
   **When** I compare it against the `ai-dev-omega-memory` reference convention
   **Then** the role has all required subdirectories: `defaults/`, `handlers/`, `meta/`, `tasks/`, `templates/`
   **And** the empty `files/` directory is removed (role has no static files to ship)

2. **Given** Hermes is installed on the target container (`~/.hermes/config.yaml` exists)
   **When** the `ai-dev-mempalace` role runs
   **Then** a `wire-hermes.yml` task file conditionally adds the MemPalace MCP server entry to Hermes config using `blockinfile` with Ansible markers
   **And** the marker follows the convention: `# {mark} MEMPALACE MCP CONNECTION - MANAGED BY ANSIBLE`
   **And** the block adds a `mempalace` entry under `mcp_servers` in `~/.hermes/config.yaml`
   **And** if Hermes is NOT installed, the role completes without error (graceful skip)

3. **Given** the `main.yml` task file orchestrates all subtasks
   **When** I review `tasks/main.yml`
   **Then** it includes `wire-hermes.yml` after `configure-mining.yml` and before the verify block
   **And** the include follows the naming convention: `"Wire MemPalace MCP into Hermes (if installed)"`

4. **Given** a `group_vars/dev_hosts/ai-dev-mempalace.yml` file does not yet exist
   **When** the story is complete
   **Then** an `ai-dev-mempalace.yml` group_vars file exists at `inventories/homelab/group_vars/dev_hosts/ai-dev-mempalace.yml`
   **And** it follows the commented-out full catalog convention (matching `ai-dev-omega.yml` style)
   **And** it documents all overridable defaults from `roles/ai-dev-mempalace/defaults/main.yml`

5. **Given** the `verify.yml` already has comprehensive health checks
   **When** I run `ansible-playbook ... --tags verify --limit ct-dev-test`
   **Then** verify.yml includes a conditional Hermes wiring check (matching omega-memory's pattern)
   **And** the check verifies `mempalace` appears in `~/.hermes/config.yaml` when Hermes is installed
   **And** the check is skipped when Hermes is NOT installed

6. **Given** the playbook at `playbooks/deploy-ai-dev-container.yml` already includes `ai-dev-mempalace`
   **When** I run `ansible-playbook playbooks/deploy-ai-dev-container.yml --limit ct-dev-test -i inventories/homelab/hosts.ini`
   **Then** the full playbook succeeds with zero errors
   **And** a second run is idempotent (zero changed tasks or only expected service restarts)

7. **Given** all implementation is complete
   **When** I check for BMAD update-safety
   **Then** no files in `.claude/skills/bmad-*/` have been modified

## Edge Cases & Error Scenarios

1. **Side effects:** Files created: `tasks/wire-hermes.yml`, `inventories/homelab/group_vars/dev_hosts/ai-dev-mempalace.yml`. Files modified: `tasks/main.yml` (new include), `tasks/verify.yml` (new conditional verify tasks). Directory removed: `files/` (empty). State advanced: sprint-status.yaml story status. External calls: Ansible deployment to ct-dev-test. This is a low-risk polish story -- it adds missing convention files without changing existing functionality.
2. **Dependency failure:** If Hermes is not installed on target: `wire-hermes.yml` must skip gracefully (check `stat` of `~/.hermes/config.yaml`). If `blockinfile` fails due to malformed YAML in Hermes config: Ansible reports the error but other tasks are not affected. If the mempalace-mcp service is not running: verify tasks catch this independently of Hermes wiring.
3. **Assumptions:** Stories 6-1 through 6-5 are complete and deployed. The role already has working install, systemd, MCP, gitignore, palace config, and mining tasks. Hermes is deployed via `ai-dev-hermes` role and has a valid `config.yaml`. The `ai-dev-omega-memory` role's `wire-hermes.yml` and `verify.yml` patterns are the canonical reference. The `deploy-ai-dev-container.yml` playbook already lists `ai-dev-mempalace` in its roles.

## Eval Assertions

<!-- Binary test assertions derived from acceptance criteria. Used by /autoresearch:fix for post-code-review iteration loops. -->

| # | Assertion | Command/Check | Pass Criteria |
|---|-----------|---------------|---------------|
| AC-1 | Role has no empty files/ dir | `test ! -d homelab-infra/ansible/roles/ai-dev-mempalace/files` | Exits with code 0 (dir removed) |
| AC-2 | wire-hermes.yml exists | `test -f homelab-infra/ansible/roles/ai-dev-mempalace/tasks/wire-hermes.yml` | Exits with code 0 |
| AC-2b | wire-hermes uses blockinfile | `grep -q 'blockinfile' homelab-infra/ansible/roles/ai-dev-mempalace/tasks/wire-hermes.yml` | Exits with code 0 |
| AC-2c | wire-hermes has correct marker | `grep -q 'MEMPALACE MCP CONNECTION' homelab-infra/ansible/roles/ai-dev-mempalace/tasks/wire-hermes.yml` | Exits with code 0 |
| AC-3 | main.yml includes wire-hermes | `grep -q 'wire-hermes' homelab-infra/ansible/roles/ai-dev-mempalace/tasks/main.yml` | Exits with code 0 |
| AC-4 | group_vars file exists | `test -f homelab-infra/ansible/inventories/homelab/group_vars/dev_hosts/ai-dev-mempalace.yml` | Exits with code 0 |
| AC-5 | verify.yml checks Hermes wiring | `grep -q 'Hermes.*wiring\|hermes.*mempalace' homelab-infra/ansible/roles/ai-dev-mempalace/tasks/verify.yml` | Exits with code 0 |
| AC-6 | Full playbook succeeds | `ansible-playbook playbooks/deploy-ai-dev-container.yml --limit ct-dev-test -i inventories/homelab/hosts.ini` | Exits with code 0 |
| AC-7 | No BMAD skill files modified | `git diff .claude/skills/bmad-*/` | Empty output (no changes) |

## Tasks / Subtasks

- [x] Task 0: Verify previous story's deployment (AC: prerequisite)
  - [x] Confirm Story 6-5's knowledge-query skill is deployed on ct-dev-test: `ssh ct-dev-test 'test -f ~/.hermes/skills/bmad/knowledge-query/SKILL.md'`
  - [x] Confirm MemPalace MCP service is active: `ssh ct-dev-test 'su - developer -c "XDG_RUNTIME_DIR=/run/user/1000 systemctl --user is-active mempalace-mcp"'`
  - [x] If either check fails, halt and raise a blocker

- [x] Task 1: Create `wire-hermes.yml` task file (AC: 2, 3)
  - [x] Create `homelab-infra/ansible/roles/ai-dev-mempalace/tasks/wire-hermes.yml`
  - [x] Follow `ai-dev-omega-memory/tasks/wire-hermes.yml` pattern exactly: stat check for `~/.hermes/config.yaml`, then `blockinfile` with `when: hermes_config_stat.stat.exists`
  - [x] Use marker: `# {mark} MEMPALACE MCP CONNECTION - MANAGED BY ANSIBLE`
  - [x] Block content: add `mempalace` MCP server entry pointing to `{{ ai_dev_mempalace_venv }}/bin/python -m mempalace.mcp_server --palace {{ ai_dev_mempalace_palace_dir }}`
  - [x] Add include to `tasks/main.yml` after `configure-mining.yml` and before verify block

- [x] Task 2: Create `group_vars/dev_hosts/ai-dev-mempalace.yml` (AC: 4)
  - [x] Create `inventories/homelab/group_vars/dev_hosts/ai-dev-mempalace.yml`
  - [x] Follow the commented-out full catalog convention (see `ai-dev-omega.yml` for style reference)
  - [x] Document all defaults from `roles/ai-dev-mempalace/defaults/main.yml` as commented-out entries
  - [x] Include three-tier precedence header comment

- [x] Task 3: Add conditional Hermes verify tasks (AC: 5)
  - [x] Add to `tasks/verify.yml`: check if Hermes config exists (stat), then grep for 'mempalace' in config
  - [x] Follow `ai-dev-omega-memory/tasks/verify.yml` lines 196-209 pattern exactly
  - [x] Use `when: hermes_config_check.stat.exists` for conditional execution

- [x] Task 4: Remove empty `files/` directory (AC: 1)
  - [x] Remove `homelab-infra/ansible/roles/ai-dev-mempalace/files/` (empty, unused)

- [x] Task 5: Deploy and verify on ct-dev-test (AC: 6)
  - [x] Run full playbook: `ansible-playbook playbooks/deploy-ai-dev-container.yml --limit ct-dev-test -i inventories/homelab/hosts.ini`
  - [x] Confirm zero errors
  - [x] Run verify: `ansible-playbook playbooks/deploy-ai-dev-container.yml --limit ct-dev-test -i inventories/homelab/hosts.ini --tags verify`
  - [x] Confirm all VERIFY checks pass including new Hermes wiring check
  - [x] Run idempotency check: re-run full playbook, confirm zero changed or only expected changes

## Dev Notes

- **Reference role**: `homelab-infra/ansible/roles/ai-dev-omega-memory/` -- this is the canonical convention to match
- **Key pattern**: `wire-hermes.yml` uses `ansible.builtin.stat` + `ansible.builtin.blockinfile` with `when:` conditional -- never fail if Hermes is absent
- **Blockinfile markers**: Use `# {mark}` convention so Ansible manages the block idempotently. The OMEGA role uses `# {mark} OMEGA MCP CONNECTION - MANAGED BY ANSIBLE` -- follow the same pattern with `MEMPALACE`
- **MCP server command**: MemPalace uses `python -m mempalace.mcp_server --palace <path>` (stdio transport), NOT a long-running daemon. The MCP entry in Hermes config should use `command` + `args` format
- **group_vars convention**: All `ai-dev-*.yml` files in `group_vars/dev_hosts/` use commented-out entries with descriptive comments. They document the full variable catalog for operator reference without overriding role defaults
- **Existing files/ directory**: The `files/` subdirectory is empty -- it was created during initial role scaffolding but the role uses only templates (Jinja2). Remove it to match the omega-memory convention (no empty dirs)

### Project Structure Notes

- Role path: `homelab-infra/ansible/roles/ai-dev-mempalace/`
- Playbook: `homelab-infra/ansible/playbooks/deploy-ai-dev-container.yml` (already includes role)
- group_vars: `homelab-infra/ansible/inventories/homelab/group_vars/dev_hosts/`
- host_vars: `homelab-infra/ansible/inventories/homelab/host_vars/ct-dev-test/vars.yml`
- Inventory: `homelab-infra/ansible/inventories/homelab/hosts.ini`

### References

- [Source: homelab-infra/ansible/roles/ai-dev-omega-memory/tasks/wire-hermes.yml] -- canonical wire-hermes pattern
- [Source: homelab-infra/ansible/roles/ai-dev-omega-memory/tasks/verify.yml#L196-L209] -- conditional Hermes verify pattern
- [Source: homelab-infra/ansible/roles/ai-dev-omega-memory/tasks/main.yml] -- main.yml include ordering
- [Source: homelab-infra/ansible/inventories/homelab/group_vars/dev_hosts/ai-dev-omega.yml] -- group_vars convention (if exists)
- [Source: homelab-playbook/_bmad-output/planning-artifacts/sprint-change-proposal-knowledge-mgmt-2026-04-11.md] -- Story 6.6 definition

## Dev Agent Record

### Agent Model Used

claude-opus-4-6

### Debug Log References

### Completion Notes List

- Task 0: Verified Story 6-5 prerequisites via SSH to 192.168.50.152 -- knowledge-query skill deployed, mempalace-mcp active
- Task 1: Created wire-hermes.yml following ai-dev-omega-memory pattern exactly (stat + blockinfile + when conditional). Added include to main.yml after configure-mining.yml
- Task 2: Created ai-dev-mempalace.yml group_vars with full commented-out variable catalog matching ai-dev-omega.yml convention
- Task 3: Added two new VERIFY tasks to verify.yml -- Hermes config stat check and conditional mempalace grep
- Task 4: Removed empty files/ directory (rmdir)
- Task 5: Deployed to ct-dev-test -- first run: ok=113 changed=4 (wire-hermes blockinfile was the key change). Second run: ok=113 changed=2 (only dev-host expected changes). Verify tags: ok=88 changed=0 failed=0 -- all 88 checks pass including new Hermes wiring verify

### File List

- homelab-infra/ansible/roles/ai-dev-mempalace/tasks/wire-hermes.yml (NEW)
- homelab-infra/ansible/roles/ai-dev-mempalace/tasks/main.yml (MODIFIED - added wire-hermes include)
- homelab-infra/ansible/roles/ai-dev-mempalace/tasks/verify.yml (MODIFIED - added Hermes wiring verify tasks)
- homelab-infra/ansible/inventories/homelab/group_vars/dev_hosts/ai-dev-mempalace.yml (NEW)
- homelab-infra/ansible/roles/ai-dev-mempalace/files/ (DELETED - empty directory removed)

### Senior Developer Review (AI)

**Review Date:** 2026-04-16
**Review Outcome:** Approve
**Findings:** 0 decision-needed, 0 patch, 0 defer, 0 dismissed
**Notes:** Clean review -- all three review layers (Blind Hunter, Edge Case Hunter, Acceptance Auditor) passed. Implementation precisely matches the ai-dev-omega-memory reference convention. All 7 ACs verified.

### Deployment Verification

Verified with command: `ansible-playbook playbooks/deploy-ai-dev-container.yml --limit ct-dev-test -i inventories/homelab/hosts.ini`
Result: 9/9 assertions passed.
All eval assertions verified on target.

Verify tags: `ansible-playbook ... --tags verify` -- 88/88 checks passed (0 failed, 0 skipped relevant).
Idempotency: Second run showed 0 changed tasks in the mempalace role.
