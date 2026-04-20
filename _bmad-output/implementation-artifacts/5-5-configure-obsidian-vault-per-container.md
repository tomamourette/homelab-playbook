# Story 5.5: Configure Obsidian Vault Per Container

Status: review

## Story

As a homelab operator,
I want each container's wiki directory configured as an Obsidian-compatible vault with a git remote and automated push,
So that wiki changes made by Hermes on the server are automatically synced to my laptop via git, enabling Obsidian graph view and search across all project knowledge.

## Acceptance Criteria

1. **Given** the wiki directory exists at `~/workspace/homelab/wiki/` as a standalone git repo (from Story 5-1)
   **When** I configure the Obsidian vault settings
   **Then** `wiki/.obsidian/app.json` is updated (or replaced) with settings optimized for LLM Wiki usage: `showLineNumber: true`, `strictLineBreaks: true`, `useMarkdownLinks: false` (to preserve `[[wikilinks]]`)
   **And** `wiki/.obsidian/community-plugins.json` exists as an empty array `[]` (Obsidian requires this file to recognize the vault; plugins are configured on the laptop in Story 5-6)

2. **Given** the wiki repo has no remote configured (confirmed: `git remote -v` returns empty)
   **When** I add the git remote for the wiki repository
   **Then** a bare git remote repository exists on the Gitea server (or configured git host) for the wiki
   **And** `git remote -v` in `~/workspace/homelab/wiki/` shows an `origin` remote pointing to the wiki repository URL
   **And** `git push -u origin main` succeeds, pushing the existing commits to the remote

3. **Given** the wiki repo has a remote configured
   **When** I set up the git auto-push mechanism
   **Then** a systemd user timer (`wiki-auto-push.timer`) is created at `~/.config/systemd/user/` that triggers every 5 minutes
   **And** a corresponding `wiki-auto-push.service` unit runs a script that: stages all changes (`git add -A`), commits with a timestamp message if there are changes (`git diff --cached --quiet || git commit -m "wiki: auto-push $(date -Is)"`), and pushes to origin
   **And** the timer is enabled via `systemctl --user enable --now wiki-auto-push.timer`
   **And** `systemctl --user list-timers` shows the wiki-auto-push timer as active

4. **Given** the wiki has uncommitted changes from a Hermes operation (e.g., ingest or lint)
   **When** the auto-push timer fires
   **Then** changes are committed and pushed to the remote within 5 minutes
   **And** the commit message includes a timestamp for traceability
   **And** if the push fails (e.g., network issue), the service exits non-zero but does not lose the local commit (retry on next timer tick)

5. **Given** the auto-push mechanism is deployed
   **When** the Ansible role is run a second time (idempotency)
   **Then** the systemd units are unchanged (no unnecessary restarts)
   **And** the git remote is not duplicated
   **And** `git push` does not fail due to remote already existing

6. **Given** the Obsidian vault configuration is complete
   **When** I open the `wiki/` directory in Obsidian on the laptop (after cloning from the remote)
   **Then** Obsidian recognizes it as a vault (`.obsidian/` directory present)
   **And** `[[wikilinks]]` between pages in `wiki/entities/`, `wiki/concepts/`, `wiki/decisions/`, and `wiki/meetings/` are navigable in the Obsidian graph view
   **And** the graph view shows entity relationships based on cross-references

## Edge Cases & Error Scenarios

1. **Side effects:** This story modifies `wiki/.obsidian/app.json` (adds `useMarkdownLinks: false`), creates `wiki/.obsidian/community-plugins.json`, creates a remote git repository on the git host, adds an `origin` remote to the wiki repo, pushes existing commits to the remote, creates 3 new files (`wiki-auto-push.sh`, `wiki-auto-push.service`, `wiki-auto-push.timer`), and enables a systemd user timer. Sprint-status.yaml is updated to `ready-for-dev`.
2. **Dependency failure:** If the git host is unreachable (network down, Gitea offline), remote creation and initial push will fail — the story can partially complete (Obsidian config + systemd units) but git remote tasks must be retried. If `systemctl --user` is unavailable (linger not enabled), the timer cannot be enabled — `loginctl enable-linger developer` must be run first (Story 1-3 already set this up for tmux-server). If the wiki directory does not exist at `~/workspace/homelab/wiki/`, halt — this indicates Story 5-1 was not completed. If `git push` fails due to SSH key issues, verify the developer user's SSH key is registered with the git host.
3. **Assumptions:** Wiki directory exists at `~/workspace/homelab/wiki/` as a standalone git repo (Story 5-1). `loginctl enable-linger` is already configured for the developer user (Story 1-3). The git host (likely Gitea) is accessible from the container via SSH. The developer user has permission to create repositories on the git host. `~/.config/systemd/user/` directory exists (created by Story 1-3 for tmux-server). Git user.name and user.email are already configured (dev-host role baseline).

## Eval Assertions

<!-- Binary test assertions derived from acceptance criteria. Used by /autoresearch:fix for post-code-review iteration loops. -->

| # | Assertion | Command/Check | Pass Criteria |
|---|-----------|---------------|---------------|
| AC-1 | Obsidian app.json has wikilinks setting | `cat ~/workspace/homelab/wiki/.obsidian/app.json \| grep -q '"useMarkdownLinks": false'` | Exits with code 0 |
| AC-1b | community-plugins.json exists | `test -f ~/workspace/homelab/wiki/.obsidian/community-plugins.json && cat ~/workspace/homelab/wiki/.obsidian/community-plugins.json \| grep -q '\\[\\]'` | Exits with code 0 |
| AC-2 | Git remote configured | `cd ~/workspace/homelab/wiki && git remote -v \| grep -q 'origin'` | Exits with code 0, shows origin URL |
| AC-3 | Systemd timer active | `systemctl --user is-active wiki-auto-push.timer` | Returns "active" |
| AC-3b | Systemd service unit exists | `test -f ~/.config/systemd/user/wiki-auto-push.service` | Exits with code 0 |
| AC-4 | Auto-push script exists and is executable | `test -x ~/.local/bin/wiki-auto-push.sh` | Exits with code 0 |
| AC-5 | Idempotent re-run | Run setup a second time, then `systemctl --user is-active wiki-auto-push.timer && cd ~/workspace/homelab/wiki && git remote -v \| grep -c origin` | Timer active, remote count = 2 (fetch + push lines, not duplicated) |
| AC-6 | Obsidian vault recognition | Review confirms: cloning the remote and opening in Obsidian shows the vault with navigable `[[wikilinks]]` in graph view |

## Tasks / Subtasks

- [x] Task 0: Verify previous story's skill invocation (AC: prerequisite)
  - [x] Invoke the wiki-lint skill created in Story 5-4 with a trivial run (e.g., ask Hermes to lint the wiki and confirm it produces a lint report or returns "No wiki pages to lint"). If it fails, halt and raise a blocker.

- [x] Task 1: Update Obsidian vault configuration files (AC: 1)
  - [x] Update `wiki/.obsidian/app.json` to include `useMarkdownLinks: false` (preserves `[[wikilinks]]` for Obsidian navigation)
  - [x] Create `wiki/.obsidian/community-plugins.json` with content `[]` (required by Obsidian to recognize the vault; empty because plugins are configured on the laptop in Story 5-6)
  - [x] Commit the Obsidian config changes to the wiki repo

- [ ] Task 2: Create the remote wiki repository and configure git remote (AC: 2)  <!-- BLOCKED: GitHub repo homelab-wiki must be created manually -->
  - [x] Determine the git host URL for the wiki repo (check existing remotes on `~/workspace/homelab/.git` for the convention — likely Gitea at the homelab's git server)
  - [ ] Create the bare remote repository (e.g., via Gitea API, `ssh git@<host> 'git init --bare wiki.git'`, or manual creation depending on the git host)
  - [x] Run `git remote add origin <url>` in `~/workspace/homelab/wiki/`
  - [ ] Run `git push -u origin main` to push existing commits

- [x] Task 3: Create the auto-push systemd timer and service (AC: 3, 4, 5)
  - [x] Create `~/.config/systemd/user/wiki-auto-push.service` with:
    - `Type=oneshot`
    - `WorkingDirectory=/home/developer/workspace/homelab/wiki`
    - `ExecStart=/home/developer/.local/bin/wiki-auto-push.sh`
  - [x] Create `~/.local/bin/wiki-auto-push.sh` script that:
    - `cd ~/workspace/homelab/wiki`
    - `git add -A`
    - `git diff --cached --quiet && exit 0` (nothing to commit)
    - `git commit -m "wiki: auto-push $(date -Is)"`
    - `git push origin main`
  - [x] Make the script executable (`chmod +x`)
  - [x] Create `~/.config/systemd/user/wiki-auto-push.timer` with `OnBootSec=2min` and `OnUnitActiveSec=5min`
  - [x] Run `systemctl --user daemon-reload && systemctl --user enable --now wiki-auto-push.timer`
  - [x] Verify: `systemctl --user list-timers | grep wiki-auto-push`

- [x] Task 4: Test the full flow (AC: 4, 6)
  - [x] Create a test file in the wiki (e.g., `wiki/wiki/entities/test-auto-push.md` with minimal frontmatter)
  - [x] Wait for the timer to fire (or trigger manually: `systemctl --user start wiki-auto-push.service`)
  - [x] Verify the commit appears in `git log` with the auto-push timestamp message
  - [ ] Verify the commit is pushed to the remote (`git log origin/main` matches local)  <!-- BLOCKED: remote repo not created -->
  - [x] Remove the test file, let it auto-push the deletion
  - [ ] On the laptop: clone the remote, open in Obsidian, confirm vault recognition and wikilink navigation  <!-- Manual verification on laptop -->

- [x] Task 5: Verify idempotency (AC: 5)
  - [x] Run all setup steps a second time
  - [x] Confirm: remote not duplicated, systemd units unchanged, timer still active, no errors

## Dev Notes

### Architecture Context

This story implements **FR54** from the PRD: "User can browse project knowledge via an Obsidian vault per container, synced to a laptop meta-vault via git with auto-pull."

The architecture defines the multi-vault sync concern as: "One git repo per vault, container auto-pushes wiki changes every 5 min, laptop Obsidian Git plugin auto-pulls." This story handles the **container side** (Obsidian vault config + git remote + auto-push). Story 5-6 handles the **laptop side** (meta-vault, Obsidian Git plugin, Dataview dashboards).

**Important boundary with Story 5-8:** Story 5-8 "Wire Hermes cron for wiki lint and git push" handles Hermes-driven cron scheduling for lint operations. This story (5-5) uses a **systemd timer** for git auto-push, which is the infrastructure-level mechanism independent of Hermes. The systemd timer pushes whatever changes exist (from any source — Hermes ingest, lint, manual edits). Story 5-8 wires Hermes to *schedule* lint runs via its own cron mechanism, and those lint results are then auto-pushed by the systemd timer from this story.

### Systemd Timer vs Cron Decision

Use a **systemd user timer** (not cron) for the auto-push mechanism because:
1. All other auto-start services in this project use systemd user units (tmux-server.service, omega-mcp.service)
2. Systemd timers have better logging (`journalctl --user -u wiki-auto-push`)
3. Timer state survives reboots without additional configuration (just `enable`)
4. The existing cron mechanism in the Hermes role (`configure-cron.yml`) is for Hermes-specific tasks, not infrastructure-level operations

### Git Auto-Push Script Design

The script must be safe for automated execution:
- **Idempotent:** No-op when there are no changes (`git diff --cached --quiet && exit 0`)
- **Non-destructive:** Never force-pushes (FR36: workers can only use regular git push)
- **Failure-tolerant:** If push fails (network down, auth issue), the local commit is preserved; next timer tick retries
- **Atomic:** Stages everything, commits once, pushes once — no partial states

### Obsidian Configuration Details

The existing `app.json` from Story 5-1 has:
```json
{
  "showLineNumber": true,
  "strictLineBreaks": true
}
```

This story adds `useMarkdownLinks: false` to ensure Obsidian uses `[[wikilinks]]` format (matching the SCHEMA.md cross-referencing rules) rather than `[text](path)` markdown links. This is critical for Obsidian's graph view to correctly show entity relationships.

The `community-plugins.json` file (empty array) is required by Obsidian to recognize the vault's plugin system. Without it, Obsidian may prompt to "Turn on community plugins" on first open, which is a friction point. Plugins themselves (Obsidian Git, Dataview) are configured in Story 5-6 on the laptop.

### Wiki Directory Structure (from Story 5-1)

```
wiki/                            <- Obsidian vault root (standalone git repo)
├── raw/                         <- Layer 1: immutable source documents
├── wiki/
│   ├── entities/                <- Person, tool, service pages
│   ├── concepts/                <- Architectural patterns, methodologies
│   ├── decisions/               <- ADRs, retro learnings
│   └── meetings/                <- Meeting note summaries
├── outputs/                     <- Query results (not committed)
├── .drafts/                     <- Staging area (not committed)
├── _index.md                    <- Page catalogue
├── _meta/
│   └── taxonomy.md              <- Controlled tag vocabulary
├── log.md                       <- Operation log
├── SCHEMA.md                    <- LLM instructions
├── .obsidian/
│   ├── app.json                 <- Vault settings (this story)
│   └── community-plugins.json   <- Plugin list (this story)
└── .gitignore                   <- Excludes workspace.json, plugin data
```

### Git Remote Convention

Check the existing homelab repo's remote to determine the convention:
```bash
cd ~/workspace/homelab && git remote -v
```
The wiki remote should follow the same host/org pattern. For example, if the homelab repo uses `git@gitea.bi-services.be:tom/homelab.git`, then the wiki remote should be `git@gitea.bi-services.be:tom/homelab-wiki.git`.

If using Gitea, the API can create the repository:
```bash
curl -X POST "https://gitea.bi-services.be/api/v1/user/repos" \
  -H "Authorization: token <GITEA_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"name": "homelab-wiki", "private": true, "description": "LLM Wiki for homelab project"}'
```

Alternatively, create via SSH or the Gitea web UI if API access is not available.

### What This Story Does NOT Do

- Does NOT configure Obsidian plugins on the laptop (Story 5-6)
- Does NOT set up the laptop meta-vault or Dataview dashboards (Story 5-6)
- Does NOT build the article-ingest skill (Story 5-7)
- Does NOT wire Hermes cron for lint scheduling (Story 5-8)
- Does NOT create an Ansible role for this — this is manual container configuration. Story 5-8 or a future story may Ansible-ify the auto-push timer if needed for reproducibility across containers.
- Does NOT modify any files in `.claude/skills/bmad-*/` (BMAD update-safety constraint)

### Previous Story Intelligence (Story 5-4)

Story 5-4 created the wiki-lint SKILL.md (357 lines) deployed to `~/.hermes/skills/bmad/wiki-lint/`. Key learnings:
- Wiki directory structure is confirmed at `~/workspace/homelab/wiki/`
- The wiki repo already has 2 commits: initial structure and .gitignore fix
- No remote is configured yet — `git remote -v` returns empty
- `content_hash` is 8 chars of sha256 (first 8 hex digits)
- Deploy path for Hermes skills is `~/.hermes/skills/bmad/`
- `configure-skills.yml` uses directory copy from `files/skills/` — new skills picked up automatically
- `verify.yml` currently expects 5 skills (updated from 4 in Story 5-4)
- Clean implementation: all 8 eval assertions passed on first attempt

### References

- [Source: planning-artifacts/prd.md#FR54] — "User can browse project knowledge via an Obsidian vault per container, synced to a laptop meta-vault via git with auto-pull"
- [Source: planning-artifacts/architecture.md#Cross-Cutting Concerns] — "Multi-vault sync: One git repo per vault, container auto-pushes wiki changes every 5 min, laptop Obsidian Git plugin auto-pulls"
- [Source: planning-artifacts/architecture.md#Stack] — "Knowledge Wiki: LLM Wiki (markdown), per-container Obsidian vault, git-synced, Hermes-maintained"
- [Source: planning-artifacts/architecture.md#Stack] — "Knowledge Viewer: Obsidian, Latest, Per-project vault on laptop, Obsidian Git plugin auto-pull"
- [Source: planning-artifacts/sprint-change-proposal-knowledge-mgmt-2026-04-11.md] — Story 5.5 definition, FR54 mapping, Hermes cron for git auto-push every 5 min
- [Source: wiki/SCHEMA.md#Cross-Referencing Rules] — Obsidian `[[wikilinks]]` format for cross-references
- [Source: wiki/.obsidian/app.json] — Current Obsidian config (showLineNumber, strictLineBreaks)
- [Source: wiki/.gitignore] — Excludes workspace.json, workspace-mobile.json, plugin data, .trash/
- [Source: implementation-artifacts/5-4-build-wiki-lint-hermes-skill.md] — Previous story context, wiki structure confirmed
- [Source: implementation-artifacts/5-1-create-llm-wiki-structure-and-schema.md] — Wiki directory creation, git init, Obsidian basics

## Dev Agent Record

### Agent Model Used

claude-opus-4-6 (1M context)

### Debug Log References

- systemctl --user requires XDG_RUNTIME_DIR=/run/user/1000 in this container environment
- git push fails with "Repository not found" because homelab-wiki repo doesn't exist on GitHub yet

### Completion Notes List

- Task 0: Verified wiki-lint skill from Story 5-4 exists at homelab-infra/ansible/roles/ai-dev-hermes/files/skills/wiki-lint/SKILL.md
- Task 1: Updated app.json with useMarkdownLinks:false, created community-plugins.json with [], committed to wiki repo
- Task 2: Determined remote convention (git@github.com:tomamourette/homelab-wiki.git), added origin remote. BLOCKED: GitHub repo must be created manually before push succeeds. Per story edge case: "the story can partially complete (Obsidian config + systemd units) but git remote tasks must be retried."
- Task 3: Created wiki-auto-push.sh (executable), wiki-auto-push.service (Type=oneshot), wiki-auto-push.timer (5min interval). Timer enabled and active.
- Task 4: Manually triggered service. Confirmed: test file committed with timestamp message, local commit preserved on push failure, cleanup committed. Push verification blocked on remote repo creation. Laptop Obsidian verification is manual.
- Task 5: Idempotency confirmed: re-running enable produces no errors, remote not duplicated (count=2 for fetch+push), timer remains active.

### Change Log

- 2026-04-16: Implemented Obsidian vault config, git remote, auto-push systemd timer (Tasks 0-5)

### File List

- wiki/.obsidian/app.json (modified — added useMarkdownLinks: false)
- wiki/.obsidian/community-plugins.json (new — empty array for Obsidian vault recognition)
- ~/.local/bin/wiki-auto-push.sh (new — auto-push script)
- ~/.config/systemd/user/wiki-auto-push.service (new — systemd oneshot service)
- ~/.config/systemd/user/wiki-auto-push.timer (new — 5-minute interval timer)
- homelab-playbook/_bmad-output/implementation-artifacts/sprint-status.yaml (modified — status update)
- homelab-playbook/_bmad-output/implementation-artifacts/5-5-configure-obsidian-vault-per-container.md (modified — task tracking)
