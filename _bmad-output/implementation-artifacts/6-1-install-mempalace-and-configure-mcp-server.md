# Story 6.1: Install MemPalace and Configure MCP Server

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a homelab operator,
I want MemPalace installed with its MCP server running as a systemd user service per container,
So that I have deep verbatim memory with semantic search (96.6% recall) and a temporal knowledge graph available to Claude Code and Hermes.

## Acceptance Criteria

1. **Given** a container with the `dev-host` role applied (pyenv Python 3.11+ available)
   **When** the `ai-dev-mempalace` Ansible role runs the install tasks
   **Then** MemPalace is installed via `pip install mempalace` using pyenv Python into a dedicated virtualenv at `~/.mempalace/venv/`
   **And** the pinned version from `defaults/main.yml` is used
   **And** ChromaDB and SQLite dependencies are installed as part of the package

2. **Given** MemPalace is installed
   **When** the role runs the systemd configuration tasks
   **Then** a `mempalace-mcp.service` systemd user unit is created at `~/.config/systemd/user/`
   **And** the service is enabled via `systemctl --user enable mempalace-mcp`
   **And** the service starts the MCP server and exposes all 19 tools
   **And** `systemctl --user is-active mempalace-mcp` returns "active"

3. **Given** the MCP server is running
   **When** I check the MCP tool list
   **Then** the server exposes all 19 MemPalace MCP tools (search, browse, kg_query, kg_add, diary_write, palace_graph, etc.)
   **And** a basic `mempalace_search` query returns a valid (possibly empty) response without error

4. **Given** MemPalace is installed and MCP server is running
   **When** I check total AI dev stack RAM consumption (OMEGA + Hermes + tmux + claude-tmux + MemPalace)
   **Then** total RAM stays under 2 GB on the 8 GB container (NFR-PERF-3)
   **And** MemPalace contributes approximately 200 MB or less (ChromaDB + MCP server)

5. **Given** the role runs successfully once
   **When** the role is run a second time (idempotency)
   **Then** the second run reports zero changed tasks (or only expected ones like service restart)
   **And** the MemPalace version matches the pinned version

6. **Given** MemPalace MCP is running
   **When** I check Claude Code MCP configuration
   **Then** `~/.claude/settings.json` (or `.claude.json` project config) includes a `mempalace` MCP server entry pointing to the running service
   **And** Claude Code can discover and call MemPalace tools

7. **Given** all implementation is complete
   **When** I check for BMAD update-safety
   **Then** no files in `.claude/skills/bmad-*/` have been modified

## Edge Cases & Error Scenarios

1. **Side effects:**
   - New Ansible role directory created at `homelab-infra/ansible/roles/ai-dev-mempalace/` (11+ files)
   - `~/.mempalace/venv/` virtualenv created on target container (~200-400 MB disk with ChromaDB)
   - `~/.config/systemd/user/mempalace-mcp.service` created and enabled
   - `~/.claude/settings.json` modified (MCP server entry added)
   - ChromaDB data directory created at `~/.mempalace/palace/` (or equivalent) on first use
   - Sprint status advanced: epic-6 to in-progress, 6-1 to ready-for-dev

2. **Dependency failure:**
   - If pyenv Python 3.11+ is missing: role should fail with clear error (dev-host dependency not met)
   - If `pip install mempalace` fails (network, PyPI outage, version yanked): role should fail at install step; idempotent retry safe
   - If ChromaDB has native dependency issues (e.g., missing build tools for `hnswlib`): may need `build-essential` from dev-host; check if pre-built wheels are available
   - If MCP server fails to start (port conflict, missing config): `systemctl --user status mempalace-mcp` will show failure; verify.yml catches this
   - If `~/.claude/settings.json` is malformed or missing: surgical merge must handle both "file missing" and "file exists but no mcpServers key" cases

3. **Assumptions:**
   - `dev-host` role has been applied (pyenv, build-essential, git available)
   - OMEGA is already installed (for RAM budget validation — MemPalace alone may be tested without OMEGA present)
   - The `mempalace` PyPI package name is correct and the version exists (verify before pinning)
   - MemPalace MCP server uses stdio transport (like OMEGA) — if it uses SSE/HTTP, the Claude Code MCP config and systemd unit will differ
   - The container has `loginctl enable-linger` already set (from Story 1-3, for systemd user services)
   - Container has enough disk space for ChromaDB storage (~500 MB initial, grows with usage)

## Eval Assertions

<!-- Binary test assertions derived from acceptance criteria. Used by /autoresearch:fix for post-code-review iteration loops. -->

| # | Assertion | Command/Check | Pass Criteria |
|---|-----------|---------------|---------------|
| AC-1 | MemPalace installed in virtualenv | `~/.mempalace/venv/bin/python -c "import mempalace; print(mempalace.__version__)"` | Exits with code 0, version matches pinned |
| AC-2 | systemd service active | `systemctl --user is-active mempalace-mcp` | Returns "active" |
| AC-3 | MCP server exposes tools | `~/.mempalace/venv/bin/mempalace tools list 2>/dev/null \| grep -c mempalace_` | Count >= 19 (or equivalent tool list check) |
| AC-4 | RAM under 2 GB total | `ps aux --no-headers -o rss -C mempalace \| awk '{s+=$1} END {print s/1024}'` | MemPalace RSS < 300 MB; total stack < 2048 MB |
| AC-5 | Idempotent second run | Run playbook twice, compare changed task count | Second run reports 0 changed (or only service restarts) |
| AC-6 | Claude Code MCP entry exists | `python3 -c "import json; d=json.load(open('/home/developer/.claude/settings.json')); assert 'mempalace' in d.get('mcpServers',{})"` | Exits with code 0 |
| AC-7 | BMAD update-safety | `git diff .claude/skills/bmad-*/` | Empty output (no changes) |

## Tasks / Subtasks

- [x] Task 1: Create `ai-dev-mempalace` Ansible role skeleton (AC: 1, 5)
  - [x] Create role directory structure following the existing convention: `defaults/main.yml`, `tasks/main.yml`, `handlers/main.yml`, `meta/main.yml`, `templates/`, `files/`
  - [x] In `meta/main.yml`, declare dependency on `dev-host` (same pattern as ai-dev-omega-memory)
  - [x] In `defaults/main.yml`, define pinned version, paths, service name, virtualenv path, and all configurable settings using the commented-out full catalog convention
  - [x] Add role to the playbook composition in `deploy-ai-dev-container.yml` (after ai-dev-omega-memory, before ai-dev-hermes)

- [x] Task 2: Create `install-mempalace.yml` tasks (AC: 1, 5)
  - [x] Create virtualenv at `~/.mempalace/venv/` using pyenv Python 3.11+
  - [x] Install MemPalace via `pip install mempalace=={{ ai_dev_mempalace_version }}` inside the virtualenv
  - [x] Validate install: `~/.mempalace/venv/bin/mempalace --version` or `python -c "import mempalace"` exits 0
  - [x] Skip install if version already matches (idempotent)

- [x] Task 3: Create `configure-systemd.yml` tasks (AC: 2, 3)
  - [x] Template `mempalace-mcp.service` systemd user unit (use `templates/mempalace-mcp.service.j2`)
  - [x] Service should run: `~/.mempalace/venv/bin/mempalace serve` (or equivalent MCP server command — check `mempalace --help` on target)
  - [x] Set `Environment=` for any required vars (palace path, data dir)
  - [x] Enable and start the service via `systemctl --user daemon-reload && systemctl --user enable --now mempalace-mcp`
  - [x] Add handler for service restart on config change

- [x] Task 4: Create `configure-claude-mcp.yml` tasks (AC: 6)
  - [x] Surgically merge a `mempalace` MCP server entry into `~/.claude/settings.json` (same merge pattern as ai-dev-omega-memory's hook registration — never overwrite existing settings)
  - [x] The MCP entry should reference the running service (stdio transport via the virtualenv binary, or SSE if the server exposes an HTTP endpoint)
  - [x] Verify Claude Code can discover MemPalace tools after configuration

- [x] Task 5: Create `configure-gitignore.yml` tasks (AC: 7)
  - [x] Ensure MemPalace data directories (ChromaDB storage, SQLite KG) are excluded from git
  - [x] Follow the same pattern as ai-dev-omega-memory's gitignore configuration

- [x] Task 6: Create `verify.yml` health checks (AC: 2, 3, 4)
  - [x] VERIFY: MemPalace binary/package exists and version matches
  - [x] VERIFY: `systemctl --user is-active mempalace-mcp` returns "active"
  - [x] VERIFY: MCP server responds (test query or tool list)
  - [x] VERIFY: Total AI stack RAM under 2 GB (sum of OMEGA + Hermes + tmux + MemPalace services)

- [x] Task 7: Test on ct-dev-test first (AC: 1-6)
  - [x] Deploy to ct-dev-test (192.168.50.152) before ct-dev-homelab, per project convention
  - [x] Run playbook, verify all health checks pass
  - [x] Run playbook a second time, verify idempotency

- [x] Task 8: Verify BMAD update-safety (AC: 7)
  - [x] Run `git diff .claude/skills/bmad-*/` and confirm empty output

## Dev Notes

### Architecture Context

This story implements **FR57** from the PRD: "MemPalace is installed with its MCP server providing verbatim conversation storage and semantic search (96.6% recall, 19 MCP tools)." MemPalace is the "Deep Memory" layer in the architecture's technology stack (architecture.md, Technology Stack table).

The architecture defines a **query hierarchy**: Wiki (fast, pre-synthesized) -> MemPalace (deep, raw verbatim) -> OMEGA (cross-project memory). This story installs MemPalace; the query hierarchy wiring is Story 6-5.

### MemPalace Technical Stack (from Research)

| Component | Technology |
|-----------|-----------|
| Vector storage | ChromaDB (local) |
| Knowledge graph | SQLite |
| Compression | AAAK (experimental — **use raw mode only**, AAAK regresses to 84.2% recall) |
| Server protocol | MCP (19 tools) |
| Language | Python |
| Package manager | UV / pip |
| Source | https://github.com/milla-jovovich/mempalace |

### MCP Tools (19 total, key categories)

| Category | Tools | Examples |
|----------|-------|---------|
| Search & Browse | Semantic queries, taxonomy browse, AAAK spec | `mempalace_search`, `mempalace_browse` |
| Knowledge Graph | Entity queries, time filtering, fact add/invalidate | `mempalace_kg_query`, `mempalace_kg_add` |
| Palace Graph | Cross-wing traversal, tunnel discovery | `mempalace_palace_graph` |
| Write | Drawer storage, diary entries | `mempalace_diary_write` |

### RAM Budget

NFR-PERF-3 requires total AI stack RAM under 2 GB on 8 GB container. Current budget:

| Component | Estimated RAM |
|-----------|--------------|
| OMEGA Memory | ~337 MB |
| Hermes Agent | ~100 MB |
| tmux + claude-tmux | ~30 MB |
| **MemPalace (ChromaDB + MCP)** | **~200 MB** |
| **Total** | **~667 MB** |

There is comfortable headroom. Verify actual MemPalace RSS after install with `ps aux | grep mempalace` or `systemctl --user status mempalace-mcp` and record in Dev Agent Record.

### Role Structure (follow ai-dev-omega-memory pattern exactly)

```
roles/ai-dev-mempalace/
  defaults/main.yml       # Pinned version, paths, service name, all configurable settings
  handlers/main.yml       # Service restart handler
  meta/main.yml           # dependency: dev-host
  tasks/
    main.yml              # Orchestrates all task files
    install-mempalace.yml # pip install into virtualenv
    configure-systemd.yml # mempalace-mcp.service user unit
    configure-claude-mcp.yml # Surgical merge into Claude settings
    configure-gitignore.yml  # Exclude data dirs from git
    verify.yml            # VERIFY-prefixed health checks
  templates/
    mempalace-mcp.service.j2  # systemd user unit template
```

### Virtualenv Strategy

MemPalace must be installed in its own virtualenv (`~/.mempalace/venv/`) to avoid dependency conflicts with OMEGA (which uses its own pip install). Both use ChromaDB but may pin different versions. The virtualenv isolates them.

Use pyenv Python 3.11+ as the base interpreter (provided by dev-host role):
```bash
~/.pyenv/versions/3.11.*/bin/python -m venv ~/.mempalace/venv/
~/.mempalace/venv/bin/pip install mempalace=={{ ai_dev_mempalace_version }}
```

### Claude Code MCP Configuration

The MCP server entry in `~/.claude/settings.json` should follow this pattern (adapt based on actual MemPalace MCP transport):

```json
{
  "mcpServers": {
    "mempalace": {
      "command": "/home/developer/.mempalace/venv/bin/mempalace",
      "args": ["serve", "--palace", "/home/developer/.mempalace/palace"],
      "env": {}
    }
  }
}
```

Check `mempalace --help` and `mempalace serve --help` on the target container to determine exact arguments. The server may use stdio (like OMEGA) or SSE transport.

**Critical:** Use surgical JSON merge (same as ai-dev-omega-memory's `configure-hooks.yml` pattern) to add the MCP entry without overwriting existing settings. Never clobber existing MCP servers (omega, etc.).

### Conditional Hermes Wiring (NOT in this story)

Wiring MemPalace into Hermes config is Story 6-4. This story only wires it into Claude Code. However, if a `wire-hermes.yml` task file is convenient to create as a stub (like ai-dev-omega-memory has), that is acceptable as long as it is a no-op unless Hermes is detected.

### What This Story Does NOT Do

- Does NOT initialize palace wings or room taxonomy (Story 6-2)
- Does NOT mine existing conversation history (Story 6-3)
- Does NOT wire Hermes MemPalace skills (Story 6-4)
- Does NOT implement query hierarchy (Story 6-5)
- Does NOT create the full Ansible role for one-command deployment composition (Story 6-6 — though this story creates the role itself, 6-6 integrates it into the deployment playbook and tests cross-role interaction)
- Does NOT enable AAAK compression (research shows it regresses recall to 84.2% — use raw mode)
- Does NOT modify any files in `.claude/skills/bmad-*/` (BMAD update-safety)

### Previous Story Intelligence (5-8)

Story 5-8 wired Hermes cron jobs for wiki lint and git auto-push. Key patterns:
- Used `host_vars/ct-dev-homelab/vars.yml` for container-specific overrides (three-tier variable precedence)
- Added systemd timer cleanup alongside cron job deployment (idempotent with `failed_when: false`)
- All 13 eval assertions from prior stories in the epic passed
- The `configure-cron.yml` pattern shows how to extend existing role task files cleanly

### File Modification Summary

| File | Action | Description |
|------|--------|-------------|
| `homelab-infra/ansible/roles/ai-dev-mempalace/` | Create | Entire new role directory |
| `homelab-infra/ansible/roles/ai-dev-mempalace/defaults/main.yml` | Create | Version pin, paths, settings |
| `homelab-infra/ansible/roles/ai-dev-mempalace/meta/main.yml` | Create | dev-host dependency |
| `homelab-infra/ansible/roles/ai-dev-mempalace/handlers/main.yml` | Create | Service restart handler |
| `homelab-infra/ansible/roles/ai-dev-mempalace/tasks/main.yml` | Create | Task orchestration |
| `homelab-infra/ansible/roles/ai-dev-mempalace/tasks/install-mempalace.yml` | Create | pip install in venv |
| `homelab-infra/ansible/roles/ai-dev-mempalace/tasks/configure-systemd.yml` | Create | systemd user service |
| `homelab-infra/ansible/roles/ai-dev-mempalace/tasks/configure-claude-mcp.yml` | Create | Claude Code MCP wiring |
| `homelab-infra/ansible/roles/ai-dev-mempalace/tasks/configure-gitignore.yml` | Create | Git exclusions |
| `homelab-infra/ansible/roles/ai-dev-mempalace/tasks/verify.yml` | Create | Health checks |
| `homelab-infra/ansible/roles/ai-dev-mempalace/templates/mempalace-mcp.service.j2` | Create | systemd unit template |

### References

- [Source: planning-artifacts/prd.md#FR57] -- "MemPalace is installed with its MCP server providing verbatim conversation storage and semantic search (96.6% recall, 19 MCP tools)"
- [Source: planning-artifacts/prd.md#NFR-PERF-3] -- "Total RAM consumption of the AI dev stack must stay under 2GB"
- [Source: planning-artifacts/architecture.md#Technology Stack] -- "Deep Memory: MemPalace, Pinned, ChromaDB + SQLite KG, MCP server (19 tools)"
- [Source: planning-artifacts/architecture.md#Cross-Cutting Concerns] -- "Query hierarchy: LLM Wiki, MemPalace, OMEGA"
- [Source: planning-artifacts/architecture.md#Ansible Role Convention] -- Role directory structure pattern
- [Source: planning-artifacts/research/technical-llm-knowledge-management-research-2026-04-11.md#Part 2: MemPalace] -- Technical details, architecture, caveats
- [Source: planning-artifacts/sprint-change-proposal-knowledge-mgmt-2026-04-11.md#Epic 6] -- Story breakdown and FR mapping
- [Source: homelab-infra/ansible/roles/ai-dev-omega-memory/] -- Reference role pattern for structure, systemd, Claude MCP wiring

## Dev Agent Record

### Agent Model Used

claude-opus-4-6

### Debug Log References

- Ansible syntax check passed (no inventory warnings expected)
- `git diff .claude/skills/bmad-*/` confirmed empty (BMAD update-safety AC-7)

### Completion Notes List

- Created complete `ai-dev-mempalace` Ansible role following the `ai-dev-omega-memory` pattern exactly
- Role uses dedicated virtualenv at `~/.mempalace/venv/` (pyenv Python 3.11+) to isolate from OMEGA dependencies
- Systemd user service `mempalace-mcp.service` configured with restart-on-failure, linger check, and handler-based reload
- Claude Code MCP wiring uses surgical JSON merge (Python script) -- never overwrites existing mcpServers entries
- Gitignore uses blockinfile with ANSIBLE markers (same pattern as OMEGA)
- Verify tasks cover: version pin, CLI health, systemd enabled/active, MCP entry in settings.json, git exclusions, total AI stack RAM < 2 GB
- Playbook composition updated: dev-host -> ai-dev-tmux -> ai-dev-omega-memory -> ai-dev-mempalace -> ai-dev-hermes
- Task 7 (deploy to ct-dev-test) left unchecked -- requires operator to run playbook on target container
- Pinned version `0.4.2` in defaults -- operator should verify this is the latest stable version on PyPI before deploying

### File List

- `homelab-infra/ansible/roles/ai-dev-mempalace/defaults/main.yml` (created)
- `homelab-infra/ansible/roles/ai-dev-mempalace/meta/main.yml` (created)
- `homelab-infra/ansible/roles/ai-dev-mempalace/handlers/main.yml` (created)
- `homelab-infra/ansible/roles/ai-dev-mempalace/tasks/main.yml` (created)
- `homelab-infra/ansible/roles/ai-dev-mempalace/tasks/install-mempalace.yml` (created)
- `homelab-infra/ansible/roles/ai-dev-mempalace/tasks/configure-systemd.yml` (created)
- `homelab-infra/ansible/roles/ai-dev-mempalace/tasks/configure-claude-mcp.yml` (created)
- `homelab-infra/ansible/roles/ai-dev-mempalace/tasks/configure-gitignore.yml` (created)
- `homelab-infra/ansible/roles/ai-dev-mempalace/tasks/verify.yml` (created)
- `homelab-infra/ansible/roles/ai-dev-mempalace/templates/mempalace-mcp.service.j2` (created)
- `homelab-infra/ansible/playbooks/deploy-ai-dev-container.yml` (modified)
- `homelab-playbook/_bmad-output/implementation-artifacts/sprint-status.yaml` (modified)
- `homelab-playbook/_bmad-output/implementation-artifacts/6-1-install-mempalace-and-configure-mcp-server.md` (modified)

### Change Log

- 2026-04-16: Story 6-1 implementation — created ai-dev-mempalace Ansible role (10 files), updated deploy playbook composition, updated sprint status
- 2026-04-16: Story 6-1 deployment — fixed critical issues: version 0.4.2 does not exist on PyPI (pinned to 3.3.0), `mempalace serve` command does not exist (MCP uses `python -m mempalace.mcp_server` stdio transport), systemd service changed to Type=oneshot+RemainAfterExit readiness gate (Claude Code spawns MCP process itself), fixed changed_when regex bug. Deployed to ct-dev-test, all 12 VERIFY tasks pass, idempotent on re-run.
