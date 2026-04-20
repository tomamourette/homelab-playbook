# Story 5.6: Set Up Laptop Meta-Vault with Dataview

Status: review

## Story

As a homelab operator,
I want my laptop's Obsidian configured with an Obsidian Git plugin for auto-pull, a Dataview plugin for dashboards, and URI links to per-project vaults,
So that I can browse all project wikis from my laptop with live-updating dashboards and seamless navigation between projects.

## Acceptance Criteria

1. **Given** the wiki remote repository exists on GitHub (created in Story 5-5)
   **When** I clone the wiki repo to the laptop and open it in Obsidian
   **Then** a local clone of the wiki exists at a known path on the laptop (e.g., `~/Obsidian/homelab-wiki/`)
   **And** Obsidian recognizes the directory as a vault (`.obsidian/` directory present from Story 5-5)
   **And** all `[[wikilinks]]` between entity, concept, decision, and meeting pages are navigable
   **And** the Obsidian graph view shows entity relationships based on cross-references

2. **Given** the cloned wiki vault is open in Obsidian on the laptop
   **When** I install and configure the Obsidian Git community plugin
   **Then** the Obsidian Git plugin is installed and enabled in the vault
   **And** auto-pull is configured to run on a schedule (e.g., every 5 minutes) so that container-side changes from Hermes auto-push (Story 5-5) appear on the laptop without manual intervention
   **And** the plugin settings are committed to the vault's `.obsidian/` directory so they persist across clones
   **And** conflict resolution is set to a safe default (e.g., pull before push, or pull-only mode since the laptop is read-mostly)

3. **Given** the Obsidian Git plugin is pulling changes automatically
   **When** Hermes pushes a wiki change on the container (via the wiki-auto-push timer from Story 5-5)
   **Then** the change appears on the laptop Obsidian instance within 10 minutes (5-min server push + 5-min laptop pull)
   **And** no manual `git pull` is required

4. **Given** the cloned wiki vault is open in Obsidian on the laptop
   **When** I install and configure the Dataview community plugin
   **Then** the Dataview plugin is installed and enabled in the vault
   **And** at least two Dataview dashboard pages exist in the wiki:
     - **Entity Index dashboard** (`wiki/dashboards/entity-index.md`): a Dataview query that lists all entity pages from `wiki/entities/` with their `type`, `status`, and `last_updated` frontmatter fields, sorted by last updated
     - **Recent Activity dashboard** (`wiki/dashboards/recent-activity.md`): a Dataview query that lists the 20 most recently modified pages across all wiki subdirectories, showing path, title, and modification date
   **And** the dashboards render correctly in Obsidian's reading view (Dataview blocks produce tables, not raw code)

5. **Given** the laptop may eventually have multiple project wiki vaults (one per container)
   **When** I set up the meta-vault navigation structure
   **Then** a meta-vault index page exists (e.g., `~/Obsidian/meta-vault/index.md` or a dedicated page in the homelab wiki) that contains Obsidian URI links (`obsidian://open?vault=...&file=...`) to each per-project vault's `_index.md`
   **And** clicking a URI link opens the target vault in Obsidian (or prompts to open it if not already open)
   **And** the meta-vault structure is documented so future projects can add their vault links following the same pattern

6. **Given** all laptop-side configuration is complete
   **When** the setup is verified end-to-end
   **Then** Obsidian Git auto-pull is active (check plugin status)
   **And** Dataview dashboards render correctly with live data from the wiki
   **And** URI links to per-project vaults are functional
   **And** no files in `.claude/skills/bmad-*/` have been modified (BMAD update-safety)

## Edge Cases & Error Scenarios

1. **Side effects:** This story creates files on the laptop (not the container): Obsidian Git plugin config in `.obsidian/plugins/obsidian-git/`, Dataview plugin config in `.obsidian/plugins/dataview/`, dashboard markdown pages in `wiki/dashboards/`, and a meta-vault index page. The `community-plugins.json` file (initialized as `[]` in Story 5-5) will be updated to list `["obsidian-git", "dataview"]`. Dashboard files committed to the wiki repo will propagate back to the container via git push/pull cycle.
2. **Dependency failure:** If the GitHub remote wiki repo does not exist yet (Story 5-5 Task 2 was BLOCKED), the clone step fails -- the remote repo must be created first. If Obsidian is not installed on the laptop, all steps fail -- prerequisite is Obsidian desktop app installed. If the Obsidian Git plugin cannot authenticate to the remote (SSH key not configured on laptop for GitHub), auto-pull will fail silently -- verify `git pull` works manually first. If Dataview queries return empty results, it likely means wiki pages lack frontmatter -- verify pages from Story 5-1/5-2 have the expected YAML frontmatter fields.
3. **Assumptions:** Obsidian desktop app is already installed on the laptop. The laptop has git installed and SSH keys configured for GitHub access. The wiki remote repo on GitHub exists and is accessible (Story 5-5 dependency). The wiki pages created by Stories 5-1 through 5-4 have YAML frontmatter with fields like `type`, `status`, `last_updated` that Dataview can query. The laptop user has permission to install Obsidian community plugins (not restricted by enterprise policy). Only one project wiki exists initially (homelab); multi-vault URI linking is forward-looking.

## Eval Assertions

<!-- Binary test assertions derived from acceptance criteria. Used by /autoresearch:fix for post-code-review iteration loops. -->

| # | Assertion | Command/Check | Pass Criteria |
|---|-----------|---------------|---------------|
| AC-1 | Wiki cloned and recognized as vault | `test -d ~/Obsidian/homelab-wiki/.obsidian` | Exits with code 0 |
| AC-1b | Wikilinks navigable | Review confirms: opening a page with `[[wikilinks]]` in Obsidian allows clicking through to the linked page |
| AC-2 | Obsidian Git plugin installed | `test -f ~/Obsidian/homelab-wiki/.obsidian/plugins/obsidian-git/main.js` | Exits with code 0 |
| AC-2b | Auto-pull configured | `cat ~/Obsidian/homelab-wiki/.obsidian/plugins/obsidian-git/data.json \| grep -q '"autoPull"'` | Exits with code 0, autoPull interval is set |
| AC-3 | End-to-end sync within 10 min | Review confirms: create a test file on container, wait 10 min, file appears in laptop Obsidian |
| AC-4 | Dataview plugin installed | `test -f ~/Obsidian/homelab-wiki/.obsidian/plugins/dataview/main.js` | Exits with code 0 |
| AC-4b | Entity Index dashboard renders | Review confirms: `wiki/dashboards/entity-index.md` shows a Dataview table listing entities with type, status, last_updated columns |
| AC-4c | Recent Activity dashboard renders | Review confirms: `wiki/dashboards/recent-activity.md` shows a Dataview table listing 20 most recent pages |
| AC-5 | Meta-vault index with URI links | `grep -q 'obsidian://open' ~/Obsidian/homelab-wiki/wiki/dashboards/meta-vault.md` or equivalent meta-vault index file | Exits with code 0 |
| AC-6 | No BMAD files modified | `cd ~/workspace/homelab && git diff .claude/skills/bmad-*/` | Empty output (no changes) |

## Tasks / Subtasks

- [x] Task 1: Clone wiki repo to laptop and verify vault recognition (AC: 1)
  - [x] Ensure the GitHub remote repo `homelab-wiki` exists (prerequisite from Story 5-5 Task 2 -- if not created yet, create it now via GitHub web UI or `gh repo create`)
  - [x] Push existing wiki commits from container to the remote: `cd ~/workspace/homelab/wiki && git push -u origin main`
  - [ ] Clone on laptop: `git clone git@github.com:tomamourette/homelab-wiki.git ~/Obsidian/homelab-wiki/` *(manual laptop step -- see setup guide)*
  - [ ] Open the cloned directory as a vault in Obsidian *(manual laptop step)*
  - [x] Verify `.obsidian/app.json` has `useMarkdownLinks: false` (from Story 5-5)
  - [ ] Verify `[[wikilinks]]` between pages are clickable and graph view shows relationships *(manual laptop step)*

- [x] Task 2: Install and configure Obsidian Git plugin (AC: 2, 3)
  - [ ] In Obsidian: Settings > Community plugins > Turn on community plugins (if not already enabled) *(manual laptop step)*
  - [ ] Browse and install "Obsidian Git" plugin by Vinzent03 *(manual laptop step)*
  - [ ] Enable the plugin *(manual laptop step)*
  - [x] Configure plugin settings:
    - Auto pull interval: 5 minutes
    - Pull on startup: enabled
    - Auto commit and push: disabled (laptop is read-mostly; edits should be rare)
    - Conflict resolution: pull-rebase preferred
  - [ ] Verify: check Obsidian Git status bar shows "ready" or last pull timestamp *(manual laptop step)*
  - [ ] Test: make a change on the container, wait for auto-push (5 min) + auto-pull (5 min), verify change appears on laptop *(manual laptop step)*

- [x] Task 3: Install and configure Dataview plugin (AC: 4)
  - [ ] In Obsidian: Settings > Community plugins > Browse > Install "Dataview" by Michael Brenan *(manual laptop step)*
  - [ ] Enable the plugin *(manual laptop step)*
  - [x] Enable JavaScript queries in Dataview settings (for flexibility, optional)
  - [x] Enable inline queries (for flexibility, optional)

- [x] Task 4: Create Dataview dashboard pages (AC: 4)
  - [x] Create `wiki/dashboards/` directory in the wiki repo
  - [x] Create `wiki/dashboards/entity-index.md` -- adapted Dataview queries to match actual SCHEMA.md frontmatter fields (confidence, stale, last_ingested, provenance instead of type/status/last_updated)
  - [x] Create `wiki/dashboards/recent-activity.md` -- lists 20 most recently modified pages across all wiki subdirectories
  - [ ] Open each dashboard in Obsidian reading view and verify tables render with data *(manual laptop step)*
  - [ ] If tables are empty, check that wiki pages have YAML frontmatter with the expected fields *(manual laptop step)*

- [x] Task 5: Create meta-vault navigation with URI links (AC: 5)
  - [x] Create `wiki/dashboards/meta-vault.md` with Obsidian URI links and homelab vault entry
  - [ ] Verify clicking the URI link opens the target vault/file in Obsidian *(manual laptop step)*
  - [x] Document the pattern for adding future project vaults (instructions and URI reference included in meta-vault.md)

- [x] Task 6: Commit configuration and verify end-to-end (AC: 6)
  - [x] Update `community-plugins.json` to list enabled plugins: `["obsidian-git", "dataview"]`
  - [x] Commit all new files (dashboards, plugin configs) to the wiki repo -- committed from container side
  - [x] Push changes from container to remote (initial push resolved Story 5-5 blocker)
  - [ ] Verify changes appear on the container (via auto-pull or manual pull) *(manual laptop step)*
  - [ ] Verify Obsidian Git auto-pull is active on laptop *(manual laptop step)*
  - [ ] Verify Dataview dashboards render correctly *(manual laptop step)*
  - [ ] Verify URI links work *(manual laptop step)*
  - [x] Verify no files in `.claude/skills/bmad-*/` have been modified

## Dev Notes

### Architecture Context

This story implements **FR54** from the PRD: "User can browse project knowledge via an Obsidian vault per container, synced to a laptop meta-vault via git with auto-pull."

The architecture defines the multi-vault sync concern as: "One git repo per vault, container auto-pushes wiki changes every 5 min, laptop Obsidian Git plugin auto-pulls." Story 5-5 handled the **container side** (Obsidian vault config, git remote, auto-push timer). This story handles the **laptop side** (clone, plugins, dashboards, meta-vault URI links).

This is a **CLIENT-SIDE story** -- all work happens on the laptop, not the container. The dev agent should produce documentation and file content that the operator follows manually on the laptop. There are no Ansible roles or container-side changes.

### Key Design Decisions

- **Read-mostly laptop model:** The laptop Obsidian instance is primarily for reading/browsing wiki content pushed by Hermes on the container. Auto-commit/push from the laptop is disabled by default to avoid merge conflicts. If the operator edits wiki pages on the laptop, they should commit and push manually.
- **Dataview for dashboards:** Dataview is the standard Obsidian plugin for dynamic queries. Dashboard pages use Dataview query blocks that render as tables in reading view. The queries depend on YAML frontmatter in wiki pages (established by SCHEMA.md from Story 5-1).
- **Meta-vault via URI links (not vault-of-vaults):** Rather than nesting vaults, which Obsidian does not support, the meta-vault approach uses Obsidian URI protocol links (`obsidian://open?vault=...&file=...`) to jump between vaults. This keeps each project vault independent and clean.
- **Dashboard pages live inside the wiki:** Placing dashboards in `wiki/dashboards/` means they are synced bidirectionally via git. Container-side Hermes operations won't interfere because Hermes operates on `wiki/entities/`, `wiki/concepts/`, etc. -- not `wiki/dashboards/`.

### Obsidian Git Plugin Configuration

Key settings for the Obsidian Git plugin (stored in `.obsidian/plugins/obsidian-git/data.json`):

| Setting | Value | Rationale |
|---------|-------|-----------|
| `autoPullInterval` | 5 | Pull every 5 minutes to match container's 5-min auto-push |
| `pullOnStartup` | true | Get latest changes when opening vault |
| `autoCommitMessage` | (default) | Not critical since auto-commit is disabled |
| `autoPush` | false | Laptop is read-mostly; manual push for edits |
| `autoCommit` | false | Laptop is read-mostly; manual commit for edits |

### Dataview Query Design

Dataview queries depend on YAML frontmatter fields in wiki pages. The SCHEMA.md from Story 5-1 defines the frontmatter contract:

- **Entity pages** (`wiki/entities/`): `title`, `type`, `status`, `aliases`, `tags`, `related`, `last_updated`, `content_hash`
- **Concept pages** (`wiki/concepts/`): `title`, `type`, `domain`, `tags`, `related`, `last_updated`, `content_hash`
- **Decision pages** (`wiki/decisions/`): `title`, `type`, `status`, `date`, `tags`, `related`, `last_updated`, `content_hash`

If pages lack these frontmatter fields, Dataview queries will return empty results. The dev agent should verify that at least a few pages have proper frontmatter before testing dashboards.

### Story 5-5 Completion State (Previous Story Intelligence)

Story 5-5 is in `review` status. Key state:
- Obsidian vault config complete: `wiki/.obsidian/app.json` has `useMarkdownLinks: false`, `community-plugins.json` exists as `[]`
- Git remote added: `origin` points to `git@github.com:tomamourette/homelab-wiki.git`
- **BLOCKED**: GitHub repo `homelab-wiki` has NOT been created yet -- `git push` fails with "Repository not found"
- Auto-push systemd timer is active and working locally (commits succeed, push fails due to missing remote)
- This story **must resolve the blocked remote repo creation** before cloning on the laptop

### What This Story Does NOT Do

- Does NOT modify container-side Obsidian config (Story 5-5 handled that)
- Does NOT build the article-ingest skill (Story 5-7)
- Does NOT wire Hermes cron for lint scheduling (Story 5-8)
- Does NOT create an Ansible role -- this is manual laptop configuration
- Does NOT modify any files in `.claude/skills/bmad-*/` (BMAD update-safety constraint)
- Does NOT set up MemPalace or query hierarchy (Epic 6)

### References

- [Source: planning-artifacts/prd.md#FR54] -- "User can browse project knowledge via an Obsidian vault per container, synced to a laptop meta-vault via git with auto-pull"
- [Source: planning-artifacts/architecture.md#Cross-Cutting Concerns] -- "Multi-vault sync: One git repo per vault, container auto-pushes wiki changes every 5 min, laptop Obsidian Git plugin auto-pulls"
- [Source: planning-artifacts/architecture.md#Stack] -- "Knowledge Viewer: Obsidian, Latest, Per-project vault on laptop, Obsidian Git plugin auto-pull"
- [Source: planning-artifacts/architecture.md#Planned Decisions] -- "Obsidian multi-vault strategy: separate vaults + laptop meta-vault with URI links"
- [Source: planning-artifacts/sprint-change-proposal-knowledge-mgmt-2026-04-11.md] -- Story 5.6 definition: "Set up laptop meta-vault with Obsidian Git, Dataview dashboards"
- [Source: implementation-artifacts/5-5-configure-obsidian-vault-per-container.md] -- Previous story: vault config, git remote (blocked), auto-push timer
- [Source: wiki/SCHEMA.md] -- Frontmatter contract for wiki pages (fields used by Dataview queries)
- [Source: implementation-artifacts/5-1-create-llm-wiki-structure-and-schema.md] -- Wiki directory structure and SCHEMA.md creation

## Dev Agent Record

### Agent Model Used

claude-opus-4-6 (1M context)

### Debug Log References

- Story 5-5 blocker (GitHub remote repo not created) was resolved: `git push -u origin main` succeeded, branch now tracking remote

### Completion Notes List

- This is a CLIENT-SIDE story. All container-side artifacts (dashboards, plugin configs, setup docs) have been created and committed. Manual laptop steps remain for the operator to complete using the setup guide at `wiki/outputs/laptop-meta-vault-setup.md`.
- Resolved Story 5-5 blocker: pushed all existing wiki commits to GitHub remote `git@github.com:tomamourette/homelab-wiki.git`
- Adapted Dataview queries to match actual SCHEMA.md frontmatter fields (`confidence`, `stale`, `last_ingested`, `provenance`) instead of the story template's assumed fields (`type`, `status`, `last_updated`)
- Updated `.gitignore` to track plugin `data.json` configs while ignoring `main.js`/`manifest.json` (installed per-device)
- Pre-committed Obsidian Git plugin config with read-mostly settings: auto-pull every 5 min, push disabled, rebase sync
- Pre-committed Dataview plugin config with JS and inline queries enabled
- Created 3 dashboard pages: entity-index, recent-activity, meta-vault navigation
- Created comprehensive laptop setup guide with step-by-step instructions and troubleshooting table

### Change Log

- 2026-04-16: Initial implementation -- created all server-side artifacts, resolved GitHub remote blocker, adapted Dataview queries to actual schema

### File List

- wiki/.gitignore (modified -- track plugin data.json, ignore main.js/manifest.json/styles.css)
- wiki/.obsidian/community-plugins.json (modified -- added obsidian-git and dataview)
- wiki/.obsidian/plugins/obsidian-git/data.json (new -- auto-pull config, read-mostly mode)
- wiki/.obsidian/plugins/dataview/data.json (new -- JS queries enabled, inline queries enabled)
- wiki/wiki/dashboards/entity-index.md (new -- Dataview table of all entities)
- wiki/wiki/dashboards/recent-activity.md (new -- Dataview table of 20 most recent pages)
- wiki/wiki/dashboards/meta-vault.md (new -- URI links to project vaults with add-vault guide)
- wiki/outputs/laptop-meta-vault-setup.md (new -- comprehensive laptop setup instructions)
