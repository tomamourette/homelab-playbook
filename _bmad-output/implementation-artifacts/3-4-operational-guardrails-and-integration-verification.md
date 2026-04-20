# Story 3.4: Operational Guardrails and Integration Verification

Status: done

## Story

As a developer,
I want operational guardrails enforced and end-to-end integration verified,
so that the Director operates safely within defined boundaries.

## Acceptance Criteria

1. **Given** the Director is functional (Story 3.3)
   **When** the guardrail configuration and integration tests run
   **Then** worker process count is limited to the configured maximum (FR33, AT-N2.1)

2. **Given** a worker completes a task and pushes
   **When** examining the git push behavior
   **Then** workers use regular git push, never force-push (FR36, AT-N3.3)

3. **Given** the Director completes a task pipeline
   **When** examining merge behavior
   **Then** the Director does not merge to main without human review (FR38, AT-N5.1)

4. **Given** the Director encounters a missing tool during a task
   **When** it decides how to handle the gap
   **Then** the Director does not install packages directly — package management stays in Ansible (FR39, AT-N5.3)

5. **Given** a worker is spawned
   **When** it performs git operations
   **Then** workers are restricted to feature branches (NFR-SEC-5)

6. **Given** the Director needs project context for a task
   **When** it queries OMEGA memory
   **Then** the Director retrieves and incorporates OMEGA context into task execution (FR23, AT-4.1)

7. **Given** the full stack is deployed (tmux + OMEGA + Hermes)
   **When** running the end-to-end integration test
   **Then** Director triggers a task that uses OMEGA context and produces a verifiable output (FR26, AT-4.2)

8. **Given** the ai-dev-hermes role runs
   **When** verify.yml executes
   **Then** all VERIFY-prefixed health checks pass (FR22)

9. **Given** the Director and workers operate under Anthropic Max Plan
   **When** examining usage patterns
   **Then** rate limits or usage constraints under Max Plan are documented (FR42)

## Edge Cases & Error Scenarios

1. **Side effects:** Modifies `templates/SOUL.md.j2` (strengthening existing guardrail sections, not adding new template structure). Modifies `tasks/verify.yml` (adding new VERIFY tasks). Modifies `defaults/main.yml` (adding Max Plan documentation comments). Creates `files/test-integration.sh` (new integration test script). Does NOT start Hermes or any long-running process. Does NOT modify OMEGA, tmux, or Claude Code configuration. Does NOT modify `.claude/skills/bmad-*/`.

2. **Dependency failure:** If OMEGA is not installed on the target, integration VERIFY tasks (AC-6, AC-7) are skipped via `when: ai_dev_hermes_omega_available` — the role succeeds but integration is not validated. If SOUL.md.j2 template rendering fails (e.g., missing variable), Ansible will fail on the template task — this is a hard failure, not degraded. If `grep -q` verify tasks match on unexpected text (false positive), the guardrail assertion passes incorrectly — use specific enough grep patterns to avoid false matches. If Hermes is not installed (Story 3.1 incomplete), all template tasks fail because `~/.hermes/` does not exist.

3. **Assumptions:** Stories 3.1, 3.2, and 3.3 are complete — `~/.hermes/config.yaml`, `.env`, `SOUL.md`, skill stubs, `start-hermes.sh`, and `spawn-worker.sh` all exist on target. SOUL.md.j2 already contains the autonomous execution, subagent delegation, git safety, and package management sections added by Story 3.3 — this story strengthens them, not creates them from scratch. The `ai_dev_hermes_omega_available` fact is set by `wire-omega.yml` (Story 3.2). The `claude` CLI is available on the target (dev-host role). Git is available and configured on the target.

## Eval Assertions

<!-- Binary test assertions derived from acceptance criteria. Used by /autoresearch:fix for post-code-review iteration loops. -->

| # | Assertion | Command/Check | Pass Criteria |
|---|-----------|---------------|---------------|
| AC-1 | SOUL.md contains worker limit guardrail | `ssh developer@TARGET grep -q 'max_workers\|maximum.*worker' ~/.hermes/SOUL.md` | Exit 0 — limit instruction present |
| AC-2 | SOUL.md contains no-force-push guardrail | `ssh developer@TARGET grep -q 'force.push\|--force' ~/.hermes/SOUL.md` | Exit 0 — prohibition text present |
| AC-3 | SOUL.md contains no-merge-to-main guardrail | `ssh developer@TARGET grep -q 'NEVER merge\|never merge.*main' ~/.hermes/SOUL.md` | Exit 0 — prohibition text present |
| AC-4 | SOUL.md contains no-package-install guardrail | `ssh developer@TARGET grep -q 'NEVER.*install\|never.*apt\|never.*pip' ~/.hermes/SOUL.md` | Exit 0 — prohibition text present |
| AC-5 | SOUL.md contains feature-branch restriction | `ssh developer@TARGET grep -q 'feature branch\|feature/' ~/.hermes/SOUL.md` | Exit 0 — restriction text present |
| AC-6 | OMEGA MCP connected in Hermes config | `ssh developer@TARGET grep -q 'omega' ~/.hermes/config.yaml` | Exit 0 when OMEGA is installed |
| AC-7 | End-to-end integration test | Review confirms: Director queries OMEGA memory, retrieves stored context, incorporates into task output | Manual — requires interactive Hermes session |
| AC-8 | All VERIFY tasks pass | `ansible-playbook deploy-hermes.yml --limit TARGET --tags ai-dev-hermes` | Exit 0, all VERIFY tasks report ok |
| AC-9 | Max Plan rate limits documented | `grep -q 'Max Plan' roles/ai-dev-hermes/defaults/main.yml` | Exit 0 — documentation comment present |
| IDMP | Idempotent second run | Run role twice, parse second run output | 0 changed tasks for ai-dev-hermes |
| BMAD | No BMAD files modified | `find .claude/skills/bmad-* -newer /tmp/bmad-marker -type f` | Empty output |

## Tasks / Subtasks

- [x] Task 1: Harden SOUL.md guardrails into verifiable rules (AC: #1-#5)
  - [x] Read current `templates/SOUL.md.j2` — confirm Story 3.3 added autonomous execution, subagent, git safety, package management sections
  - [x] Strengthen worker process limit section: add explicit instruction that Director MUST check running worker count before spawning, and refuse if `ai_dev_hermes_max_workers` is reached (FR33)
  - [x] Strengthen git safety section: add explicit `--no-force` instruction and "if push rejected, report conflict to user" language (FR36, AT-N3.3)
  - [x] Add merge guardrail section: "NEVER merge any branch to main. Create PR or mark worktree ready-for-review. Merging requires human approval." (FR38, AT-N5.1)
  - [x] Strengthen package management section: "NEVER run apt, pip, npm install directly. Report missing dependency and suggest Ansible role change." (FR39, AT-N5.3)
  - [x] Add feature branch restriction: "Workers MUST operate on feature branches only. Branch naming: `feature/<story-key>-<description>` or `fix/<description>`" (NFR-SEC-5)
  - [x] All tasks tagged `[ai-dev-hermes]`

- [x] Task 2: Add guardrail-specific VERIFY tasks to verify.yml (AC: #1, #8)
  - [x] `VERIFY | SOUL.md contains worker limit guardrail` — grep for `max_workers` or equivalent limit instruction in deployed SOUL.md
  - [x] `VERIFY | SOUL.md contains no-force-push guardrail` — grep for force-push prohibition text
  - [x] `VERIFY | SOUL.md contains no-merge-to-main guardrail` — grep for merge prohibition text
  - [x] `VERIFY | SOUL.md contains no-package-install guardrail` — grep for package install prohibition text
  - [x] `VERIFY | SOUL.md contains feature-branch-only guardrail` — grep for feature branch restriction text
  - [x] All verify tasks use `changed_when: false` and `VERIFY |` prefix
  - [x] Use `ansible.builtin.shell` with `grep -q` on deployed `~/.hermes/SOUL.md`

- [x] Task 3: Add OMEGA integration VERIFY tasks (AC: #6, #7)
  - [x] `VERIFY | OMEGA MCP is connected in Hermes config` — grep `omega` in `~/.hermes/config.yaml` (conditional on OMEGA installed)
  - [x] `VERIFY | OMEGA search responds` — run `omega search --query "test" --namespace {{ project_name }}` and check exit code (conditional on OMEGA installed)
  - [x] Guard both with `when: ai_dev_hermes_omega_available | default(false)` — if OMEGA not installed, skip gracefully
  - [x] All tasks tagged `[ai-dev-hermes]`

- [x] Task 4: Document Max Plan rate limits and usage constraints (AC: #9)
  - [x] Add a `# Max Plan Usage Notes` comment block in `defaults/main.yml` documenting:
    - Anthropic Max Plan allows programmatic `claude -p` usage
    - Concurrent worker sessions share the same subscription
    - Known rate limits or "no documented limits" if none found
    - Recommendation to monitor usage via Anthropic dashboard
  - [x] Add variable `ai_dev_hermes_max_plan_notes` (string, commented-out convention) for operator reference

- [x] Task 5: Create integration test script (AC: #6, #7)
  - [x] Create `roles/ai-dev-hermes/files/test-integration.sh` — a shell script that:
    - Checks OMEGA is reachable (`omega doctor`)
    - Stores a test memory in OMEGA (`omega store --key "integration-test-{{ timestamp }}" --value "Hermes integration test marker" --namespace {{ project_name }}`)
    - Starts a Hermes session with a one-shot task: "Query OMEGA for 'integration test marker' and report what you find"
    - Validates the output mentions the stored memory
  - [x] Mark as MANUAL assertion — script provides structure but requires interactive Hermes session for AT-4.1/AT-4.2
  - [x] Set permissions to 0755
  - [x] All tasks tagged `[ai-dev-hermes]`

- [x] Task 6: Deploy and verify on ct-dev-test (AC: all) — MANUAL DEPLOYMENT
  - [x] Run `ansible-playbook deploy-hermes.yml --limit ct-dev-test`
  - [x] Verify all new VERIFY tasks pass: `ansible-playbook deploy-hermes.yml --limit ct-dev-test --tags ai-dev-hermes -e ai_dev_hermes_verify_only=true` (or run verify.yml directly)
  - [x] SSH to ct-dev-test, confirm SOUL.md contains all 5 guardrail sections
  - [ ] Test OMEGA integration: store a test memory, start Hermes, ask it to query OMEGA (AT-4.1) — SKIPPED (OMEGA not installed on ct-dev-test)
  - [ ] Confirm worker spawning respects feature branch rule (AT-N3.3, NFR-SEC-5) — MANUAL
  - [x] Run all eval assertions

- [x] Task 7: Verify idempotency and BMAD-safety (AC: all) — MANUAL DEPLOYMENT
  - [x] Run the role a second time on ct-dev-test
  - [x] Confirm 0 changed tasks for ai-dev-hermes role
  - [x] Confirm zero files modified under `.claude/skills/bmad-*/`

- [ ] Task 8: Deploy to ct-dev-homelab (AC: all) — MANUAL DEPLOYMENT
  - [ ] Run `ansible-playbook deploy-hermes.yml --limit ct-dev-homelab`
  - [ ] Run all eval assertions on ct-dev-homelab
  - [ ] Run end-to-end integration test (AT-4.2) — MANUAL
  - [ ] Document any rate limits or Max Plan constraints observed (FR42)

## Dev Notes

### Architecture Patterns and Constraints

- **Guardrails are SOUL.md-enforced** — these are soft guardrails enforced by Director behavior via SOUL.md instructions, not system-level process controls. The architecture chose this approach because Hermes is an LLM agent, not a sandboxed process. Verify tasks confirm the instructions are present in the deployed SOUL.md.
- **Worker process limit** — `ai_dev_hermes_max_workers` (default 3) is a soft limit. SOUL.md instructs the Director to count running workers before spawning. There is no kernel-level cgroup or ulimit enforcement.
- **No force-push, no merge to main** — Enforced via SOUL.md instructions. AT-N3.3 and AT-N5.1 validate behavior, but the enforcement mechanism is instructional (LLM compliance), not technical (git hooks). If the user wants hard enforcement, git server-side hooks are a separate infrastructure concern outside this role.
- **Feature branch restriction** — Workers MUST operate on feature branches only. Branch naming convention: `feature/<story-key>-<description>` or `fix/<description>`.
- **Integration tests require OMEGA** — AT-4.1 and AT-4.2 only apply when OMEGA is installed. Use the `ai_dev_hermes_omega_available` fact (set by `wire-omega.yml` in Story 3.2) to guard integration verify tasks.
- **Hermes is NOT a daemon** — started on demand by the user in a tmux session. Integration tests that require an active Hermes session are MANUAL.

### Source Tree Components to Touch (homelab-infra repo)

| File | Action | Purpose |
|------|--------|---------|
| `roles/ai-dev-hermes/templates/SOUL.md.j2` | MODIFY | Strengthen guardrail sections with explicit verifiable language |
| `roles/ai-dev-hermes/tasks/verify.yml` | MODIFY | Add guardrail and OMEGA integration VERIFY tasks |
| `roles/ai-dev-hermes/defaults/main.yml` | MODIFY | Add Max Plan documentation comments and `ai_dev_hermes_max_plan_notes` |
| `roles/ai-dev-hermes/files/test-integration.sh` | NEW | Integration test script for AT-4.1/AT-4.2 |

### Ansible Task Patterns (from architecture.md)

- Task names: sentence case, action-first (`Verify SOUL.md contains guardrail`)
- Variable prefix: `ai_dev_hermes_*`
- Tags: `tags: [ai-dev-hermes]` on all tasks
- Use `ansible.builtin.shell` for grep checks (pipes needed)
- Use `failed_when:` not `ignore_errors: true`
- Verify tasks: `changed_when: false` and `VERIFY |` prefix
- Templates use `mode: '0644'` for SOUL.md, `mode: '0755'` for scripts

### Previous Story Learnings (from Story 3.3)

- **Template vs blockinfile:** Use Jinja2 conditionals inside templates instead of blockinfile when the file is template-managed. SOUL.md.j2 is a template — modify the template directly.
- **OMEGA binary path:** `~/.pyenv/shims/omega`, not `~/.local/bin/omega`. Use `ai_dev_hermes_omega_binary_path` variable (added in 3.2 review fix).
- **become_user with explicit paths:** Always set HOME, PATH, PYENV_ROOT environment on command tasks that need pyenv or cargo binaries.
- **Idempotency bar:** Story 3.3 achieved 0 changed on second run. Maintain this bar.
- **nvm version detection:** Use `sort -V` for locale-safe version sorting (fixed in 3.3 review).
- **SOUL.md already has sections:** Story 3.3 added autonomous execution guidance, subagent delegation, git safety, and package management sections. This story strengthens and extends those sections — do NOT duplicate them. Edit the existing sections in the template.
- **Cron is opt-in:** `ai_dev_hermes_cron_enabled` defaults to `false`. Do not change this.

### Testing Standards

- Deploy to ct-dev-test (192.168.50.152) first, then ct-dev-homelab (192.168.50.150) per test-then-deploy workflow
- Idempotency: second run must show 0 changed for ai-dev-hermes tasks
- BMAD-safety: zero modifications to `.claude/skills/bmad-*/`
- All verify tasks use `VERIFY |` prefix and `changed_when: false`
- Integration tests (AT-4.1, AT-4.2) are MANUAL — require interactive Hermes session

### Project Structure Notes

- All files are within `roles/ai-dev-hermes/` in the homelab-infra repo
- No files created outside the role directory
- No modifications to BMAD skills, OMEGA role, or tmux role
- SOUL.md.j2 is a Jinja2 template — all guardrail text is template content, not blockinfile

### References

- [Source: planning-artifacts/architecture.md#Operational Guardrails] — Config templates + verify tasks across roles
- [Source: planning-artifacts/architecture.md#Verify Task Patterns] — VERIFY prefix, changed_when: false, failed_when
- [Source: planning-artifacts/architecture.md#Role Independence & Conditional Integration] — ai-dev-hermes depends only on dev-host
- [Source: planning-artifacts/architecture.md#Secret Handling Patterns] — vault_ prefix, no_log, mode 0600
- [Source: planning-artifacts/architecture.md#File Path Conventions] — ~/.hermes/ owned by ai-dev-hermes
- [Source: planning-artifacts/epics.md#Story 3.4] — AC and FR mapping
- [Source: planning-artifacts/prd.md#AT-N2.1] — Worker process limits
- [Source: planning-artifacts/prd.md#AT-N3.3] — No force-push from workers
- [Source: planning-artifacts/prd.md#AT-N5.1] — No auto-merge to main
- [Source: planning-artifacts/prd.md#AT-N5.3] — No direct package install
- [Source: planning-artifacts/prd.md#AT-4.1] — Director uses OMEGA context
- [Source: planning-artifacts/prd.md#AT-4.2] — Worker captures to OMEGA
- [Source: planning-artifacts/prd.md#FR42] — Rate limit documentation
- [Source: implementation-artifacts/3-3-autonomous-task-execution-and-cron-scheduling.md] — Previous story learnings, SOUL.md sections, helper scripts
- [Source: implementation-artifacts/3-2-configure-omega-mcp-connection-and-bmad-skills.md] — OMEGA wiring, template vs blockinfile lesson

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

None — all YAML and bash syntax checks passed on first attempt.

### Completion Notes List

- Task 1: Hardened all 4 existing SOUL.md.j2 sections (Operational Guardrails, Subagent Delegation, Git Safety, Package Management) with explicit verifiable language. Added worker limit check-before-spawn instruction, --force prohibition with conflict reporting, NEVER merge to main language, NEVER install packages language, and feature branch naming convention (feature/<story-key> or fix/<desc>).
- Task 2: Added 5 guardrail VERIFY tasks to verify.yml using ansible.builtin.shell + grep -q on deployed SOUL.md. All use changed_when: false and VERIFY | prefix.
- Task 3: Added 2 OMEGA integration VERIFY tasks (MCP config check + search responds) guarded by `when: ai_dev_hermes_omega_available | default(false)`. Added integration test script existence check.
- Task 4: Added Max Plan Usage Notes comment block to defaults/main.yml with commented-out ai_dev_hermes_max_plan_notes variable documenting subscription sharing, fair-use policy, and monitoring recommendation.
- Task 5: Created files/test-integration.sh (shell script, 0755) with 4-step integration test: omega doctor, store test memory, retrieve verification, and manual Hermes session instructions. Added configure-integration-test.yml task file and wired into main.yml.
- Tasks 6-8: Deployment and manual verification tasks — require SSH to target hosts (ct-dev-test, ct-dev-homelab). Left unchecked for operator execution.

### Change Log

- 2026-04-16: Implemented Tasks 1-5 (code tasks). Hardened SOUL.md.j2 guardrails, added 8 VERIFY tasks to verify.yml, documented Max Plan in defaults/main.yml, created integration test script and deployment task.

### File List

- homelab-infra/ansible/roles/ai-dev-hermes/templates/SOUL.md.j2 (MODIFIED)
- homelab-infra/ansible/roles/ai-dev-hermes/tasks/verify.yml (MODIFIED)
- homelab-infra/ansible/roles/ai-dev-hermes/defaults/main.yml (MODIFIED)
- homelab-infra/ansible/roles/ai-dev-hermes/tasks/main.yml (MODIFIED)
- homelab-infra/ansible/roles/ai-dev-hermes/files/test-integration.sh (NEW)
- homelab-infra/ansible/roles/ai-dev-hermes/tasks/configure-integration-test.yml (NEW)
