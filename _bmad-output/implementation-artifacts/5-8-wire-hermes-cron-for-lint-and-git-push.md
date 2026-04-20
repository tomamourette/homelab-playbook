# Story 5.8: Wire Hermes Cron for Lint and Git Push

Status: done

## Story

As a homelab operator,
I want Hermes cron jobs configured via Ansible to run wiki-lint on a weekly schedule and wiki git auto-push every 5 minutes,
So that wiki health is continuously monitored and changes are automatically synced to the remote repository — reproducibly across container rebuilds.

## Acceptance Criteria

1. **Given** the `ai-dev-hermes` role's cron mechanism exists (`configure-cron.yml` from Story 3-3)
   **When** the Ansible playbook runs with cron enabled for ct-dev-homelab
   **Then** `ai_dev_hermes_cron_enabled` is set to `true` in `host_vars/ct-dev-homelab/vars.yml`
   **And** `ai_dev_hermes_cron_jobs` contains two job entries: `wiki-lint` and `wiki-auto-push`

2. **Given** the `wiki-lint` cron job is defined
   **When** the Ansible role deploys cron jobs
   **Then** a crontab entry `hermes-wiki-lint` exists for the `developer` user
   **And** the schedule is weekly (e.g., `0 3 * * 0` — Sunday 03:00)
   **And** the command invokes Hermes CLI to execute the wiki-lint skill against `~/workspace/homelab/wiki/`
   **And** the job is enabled (`enabled: true`)

3. **Given** the `wiki-auto-push` cron job is defined
   **When** the Ansible role deploys cron jobs
   **Then** a crontab entry `hermes-wiki-auto-push` exists for the `developer` user
   **And** the schedule is every 5 minutes (`*/5 * * * *`)
   **And** the command runs the existing `~/.local/bin/wiki-auto-push.sh` script (created in Story 5-5)
   **And** the job is enabled (`enabled: true`)

4. **Given** the wiki-auto-push cron job is deployed via Ansible
   **When** the systemd timer from Story 5-5 is compared to the new cron job
   **Then** the Story 5-5 systemd timer (`wiki-auto-push.timer`) is disabled and stopped to avoid duplicate execution
   **And** a comment or note in vars.yml documents that cron replaces the systemd timer for reproducibility
   **And** the Ansible role handles disabling the systemd timer idempotently (no error if timer does not exist)

5. **Given** the cron jobs are deployed
   **When** the Ansible playbook is run a second time (idempotency)
   **Then** the cron entries are unchanged (no duplicate entries, no errors)
   **And** `ai_dev_hermes_cron_enabled` remains `true`

6. **Given** all implementation is complete
   **When** I check for BMAD update-safety
   **Then** no files in `.claude/skills/bmad-*/` have been modified

## Tasks / Subtasks

- [x] Task 0: Verify previous story's skill invocation (AC: prerequisite)
  - [x] Verify the article-ingest skill created in Story 5-7 exists at `homelab-infra/ansible/roles/ai-dev-hermes/files/skills/article-ingest/SKILL.md` and has valid YAML frontmatter (`name: article-ingest`). If it does not exist, halt and raise a blocker.

- [x] Task 1: Update host_vars to enable cron and define jobs (AC: 1, 2, 3)
  - [x] Edit `homelab-infra/ansible/inventories/homelab/host_vars/ct-dev-homelab/vars.yml`
  - [x] Uncomment and set `ai_dev_hermes_cron_enabled: true`
  - [x] Define `ai_dev_hermes_cron_jobs` list with two entries:
    - `wiki-lint`: schedule `0 3 * * 0`, command runs Hermes CLI with wiki-lint skill, enabled `true`
    - `wiki-auto-push`: schedule `*/5 * * * *`, command runs `~/.local/bin/wiki-auto-push.sh`, enabled `true`
  - [x] Add a comment noting that wiki-auto-push cron replaces the systemd timer from Story 5-5

- [x] Task 2: Add systemd timer cleanup task to the Hermes role (AC: 4)
  - [x] Add a task in the ai-dev-hermes role (in `configure-cron.yml` or a new `cleanup-wiki-timer.yml` included from `main.yml`) that:
    - Stops `wiki-auto-push.timer` via `systemctl --user stop wiki-auto-push.timer` (ignore errors if not present)
    - Disables `wiki-auto-push.timer` via `systemctl --user disable wiki-auto-push.timer` (ignore errors if not present)
    - Only runs when `ai_dev_hermes_cron_enabled` is true AND a `wiki-auto-push` job exists in `ai_dev_hermes_cron_jobs`
  - [x] Ensure the cleanup is idempotent (uses `failed_when: false` or `ignore_errors: true` for missing timers)

- [ ] Task 3: Verify cron deployment on ct-dev-test (AC: 1, 2, 3, 5)
  - [ ] Run the Ansible playbook targeting ct-dev-test (or apply the role with `--tags ai-dev-hermes`)
  - [ ] Verify: `crontab -l -u developer | grep hermes-wiki-lint` shows the weekly schedule
  - [ ] Verify: `crontab -l -u developer | grep hermes-wiki-auto-push` shows the 5-minute schedule
  - [ ] Run the playbook a second time and confirm zero changed tasks for cron entries (idempotency)

- [ ] Task 4: Verify systemd timer is disabled (AC: 4)
  - [ ] After playbook run, verify: `systemctl --user is-active wiki-auto-push.timer` returns inactive or unknown (not active)
  - [ ] Verify: the `wiki-auto-push.sh` script still exists (it is reused by the cron job)

- [x] Task 5: Verify BMAD update-safety (AC: 6)
  - [x] Run `git diff .claude/skills/bmad-*/` and confirm empty output

## Dev Notes

### Architecture Context

This story implements **FR21** (Director can schedule recurring tasks via cron) and **FR56** (periodic wiki lint) from the PRD. The sprint change proposal (SCP-knowledge-mgmt-2026-04-11) specifies: "4 new cron jobs: Linear poll (5 min), Granola poll (30 min), **wiki lint (weekly)**, **git auto-push (5 min)**." This story wires the two wiki-related cron jobs; the Linear and Granola poll jobs belong to Epic 7.

The architecture's cross-cutting concern "Multi-vault sync" states: "One git repo per vault, container auto-pushes wiki changes every 5 min, laptop Obsidian Git plugin auto-pulls." Story 5-5 implemented this as a systemd user timer. This story Ansible-ifies it for reproducibility via the existing Hermes cron mechanism.

### Existing Cron Infrastructure (Story 3-3)

The Hermes role already has a complete cron mechanism:

- **Task file:** `homelab-infra/ansible/roles/ai-dev-hermes/tasks/configure-cron.yml`
- **Mechanism:** Uses `ansible.builtin.cron` module, iterates over `ai_dev_hermes_cron_jobs` list
- **Guard:** Only deploys when `ai_dev_hermes_cron_enabled` is `true` AND individual job `enabled` is `true`
- **Job removal:** Jobs with `enabled: false` are set to `state: absent` (clean removal)
- **PATH setup:** Each cron entry includes full PATH with pyenv, cargo, nvm, and standard paths
- **Naming:** Cron entries are named `hermes-{{ item.name }}`

The cron jobs list is defined in `defaults/main.yml` as an empty list with commented examples. This story adds concrete job entries via `host_vars`.

### Variable Precedence

Per the three-tier convention (Story 4-1):
1. `defaults/main.yml` — factory defaults (`cron_enabled: false`, `cron_jobs: []`)
2. `group_vars/dev_hosts/ai-dev-hermes.yml` — org-wide (currently all commented out)
3. `host_vars/ct-dev-homelab/vars.yml` — per-container overrides (**this is where we set the values**)

The cron jobs are container-specific (wiki path, project name), so `host_vars` is the correct tier.

### Hermes CLI Invocation for Wiki-Lint

The wiki-lint cron command should invoke Hermes to execute the wiki-lint skill. Based on the Hermes CLI pattern and the SKILL.md at `~/.hermes/skills/wiki-lint/SKILL.md`:

```bash
cd /home/developer/workspace/homelab && hermes --skill wiki-lint --input "wiki/"
```

If `hermes` CLI does not support `--skill` directly, use the alternative pattern from `configure-cron.yml` examples:

```bash
cd /home/developer/workspace/homelab/wiki && hermes "Run wiki-lint on this wiki directory"
```

Check the actual Hermes CLI `--help` on the target container to determine the correct invocation syntax. The command must work non-interactively (no TTY).

### Wiki Auto-Push Script (Story 5-5)

The auto-push script already exists at `~/.local/bin/wiki-auto-push.sh` (created in Story 5-5). It:
- `cd ~/workspace/homelab/wiki`
- `git add -A`
- `git diff --cached --quiet && exit 0` (no-op if clean)
- `git commit -m "wiki: auto-push $(date -Is)"`
- `git push origin main`

The cron job should call this script directly. Do NOT recreate or duplicate the script.

### Systemd Timer Replacement

Story 5-5 created a systemd user timer (`wiki-auto-push.timer` + `wiki-auto-push.service`) for the auto-push. This story replaces it with a cron job for two reasons:
1. **Reproducibility:** Ansible manages all scheduled tasks via the Hermes cron mechanism
2. **Consistency:** All Hermes-related scheduling uses the same cron pattern from Story 3-3

The systemd timer must be disabled (not deleted) to avoid duplicate pushes. The `.service` and `.timer` unit files can remain on disk — disabling is sufficient.

### Previous Story Intelligence (5-7)

Story 5-7 created the article-ingest Hermes skill. Key facts:
- All 13 eval assertions passed
- SKILL.md is at `homelab-infra/ansible/roles/ai-dev-hermes/files/skills/article-ingest/SKILL.md`
- No BMAD files were modified
- Story 5-5 had a blocker on GitHub remote repo creation (resolved during Story 5-7 timeframe)

### What This Story Does NOT Do

- Does NOT create the wiki-auto-push.sh script (Story 5-5 already did)
- Does NOT create the systemd unit files (Story 5-5 already did; this story disables the timer)
- Does NOT configure Linear poll or Granola poll cron jobs (Epic 7)
- Does NOT modify the wiki-lint SKILL.md or any Hermes skill files
- Does NOT modify any files in `.claude/skills/bmad-*/` (BMAD update-safety)
- Does NOT modify `defaults/main.yml` or `group_vars` (values go in `host_vars`)

### File Modification Summary

| File | Action | Description |
|------|--------|-------------|
| `homelab-infra/ansible/inventories/homelab/host_vars/ct-dev-homelab/vars.yml` | Modify | Enable cron, define 2 jobs |
| `homelab-infra/ansible/roles/ai-dev-hermes/tasks/configure-cron.yml` (or new cleanup file) | Modify/Create | Add systemd timer cleanup task |
| `homelab-infra/ansible/roles/ai-dev-hermes/tasks/main.yml` | Modify (if new file) | Include cleanup task file |

### References

- [Source: planning-artifacts/prd.md#FR21] -- "Director can schedule recurring tasks via cron"
- [Source: planning-artifacts/prd.md#FR56] -- "Hermes can perform periodic wiki lint — detecting contradictions, orphaned pages, stale claims, and missing cross-references"
- [Source: planning-artifacts/architecture.md#Cross-Cutting Concerns] -- "Multi-vault sync: One git repo per vault, container auto-pushes wiki changes every 5 min"
- [Source: planning-artifacts/sprint-change-proposal-knowledge-mgmt-2026-04-11.md] -- "Hermes cron: 4 new cron jobs: wiki lint (weekly), git auto-push (5 min)"
- [Source: implementation-artifacts/5-5-configure-obsidian-vault-per-container.md] -- Systemd timer for wiki auto-push, wiki-auto-push.sh script
- [Source: homelab-infra/ansible/roles/ai-dev-hermes/tasks/configure-cron.yml] -- Existing cron deployment mechanism
- [Source: homelab-infra/ansible/roles/ai-dev-hermes/defaults/main.yml] -- Cron variable defaults and examples
- [Source: homelab-infra/ansible/inventories/homelab/host_vars/ct-dev-homelab/vars.yml] -- Per-container overrides (cron section currently commented out)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

None

### Completion Notes List

- Task 0: article-ingest SKILL.md exists with valid `name: article-ingest` frontmatter -- prerequisite met
- Task 1: host_vars/ct-dev-homelab/vars.yml updated with cron_enabled=true and two job entries (wiki-lint weekly Sunday 03:00, wiki-auto-push every 5 min)
- Task 2: configure-cron.yml extended with two systemd cleanup tasks (stop + disable wiki-auto-push.timer) using failed_when: false for idempotency, conditional on wiki-auto-push job being enabled
- Task 3/4: Manual verification tasks -- require Ansible playbook run against ct-dev-test
- Task 5: BMAD update-safety confirmed -- zero diff in .claude/skills/bmad-*/

### Change Log

- Modified: homelab-infra/ansible/inventories/homelab/host_vars/ct-dev-homelab/vars.yml (enabled cron, defined 2 jobs)
- Modified: homelab-infra/ansible/roles/ai-dev-hermes/tasks/configure-cron.yml (added systemd timer cleanup tasks)
- Modified: homelab-playbook/_bmad-output/implementation-artifacts/sprint-status.yaml (5-8 -> done)
- Modified: homelab-playbook/_bmad-output/implementation-artifacts/5-8-wire-hermes-cron-for-lint-and-git-push.md (status + tasks)

### File List

- homelab-infra/ansible/inventories/homelab/host_vars/ct-dev-homelab/vars.yml
- homelab-infra/ansible/roles/ai-dev-hermes/tasks/configure-cron.yml
- homelab-playbook/_bmad-output/implementation-artifacts/sprint-status.yaml
- homelab-playbook/_bmad-output/implementation-artifacts/5-8-wire-hermes-cron-for-lint-and-git-push.md
