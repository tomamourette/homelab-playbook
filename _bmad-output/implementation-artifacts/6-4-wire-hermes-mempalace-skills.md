# Story 6.4: Wire Hermes MemPalace Skills

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a homelab operator,
I want Hermes to have dedicated skills for MemPalace search, diary write, and knowledge graph query, plus the MemPalace MCP server wired into Hermes config,
So that the Director agent can leverage deep verbatim memory and the temporal knowledge graph during autonomous task execution — enabling richer context than OMEGA alone.

## Acceptance Criteria

1. **Given** MemPalace 3.3.0 is installed with the MCP server running (Stories 6-1, 6-2, 6-3 done)
   **When** the `ai-dev-hermes` role runs on a host where MemPalace is detected
   **Then** the Hermes `config.yaml` includes a `mempalace` entry under `mcp_servers` pointing to the MemPalace MCP server command
   **And** the MCP entry uses the MemPalace venv Python path and `mempalace.mcp_server` module
   **And** if MemPalace is NOT installed, the entry is omitted (conditional wiring, no error)

2. **Given** the `ai-dev-hermes` role has deployed skills
   **When** the skill deployment tasks run
   **Then** a `mempalace-search` Hermes skill exists at `~/.hermes/skills/bmad/mempalace-search/SKILL.md`
   **And** the skill instructs Hermes to use the `mempalace_search` MCP tool for semantic search across wings and rooms
   **And** the skill follows the existing Hermes skill YAML frontmatter convention (name, description, version, author, metadata.hermes.tags)

3. **Given** the `ai-dev-hermes` role has deployed skills
   **When** the skill deployment tasks run
   **Then** a `mempalace-diary` Hermes skill exists at `~/.hermes/skills/bmad/mempalace-diary/SKILL.md`
   **And** the skill instructs Hermes to write diary entries (observations, decisions, lessons) to MemPalace drawers via MCP tools
   **And** entries target the correct wing based on the active project context

4. **Given** the `ai-dev-hermes` role has deployed skills
   **When** the skill deployment tasks run
   **Then** a `mempalace-kg-query` Hermes skill exists at `~/.hermes/skills/bmad/mempalace-kg-query/SKILL.md`
   **And** the skill instructs Hermes to query the MemPalace temporal knowledge graph for entity-relationship facts
   **And** the skill leverages KG temporal features (`valid_from`, `valid_to`, `as_of`) to retrieve current vs historical facts

5. **Given** Hermes has MemPalace MCP wired and all three skills deployed
   **When** Hermes is started and asked to list available skills
   **Then** `mempalace-search`, `mempalace-diary`, and `mempalace-kg-query` appear in the skill list
   **And** Hermes can invoke a MemPalace MCP tool (e.g., search) and receive results

6. **Given** all implementation is complete
   **When** I check for BMAD update-safety
   **Then** no files in `.claude/skills/bmad-*/` have been modified

## Edge Cases & Error Scenarios

1. **Side effects:** Files created: 3 new SKILL.md files under `files/skills/`, 1 new `wire-mempalace.yml` task file. Files modified: `defaults/main.yml` (new variables), `tasks/main.yml` (new include), `config.yaml.j2` (refactored mcp_servers block), `verify.yml` (new VERIFY tasks). State advanced: sprint-status.yaml story status. External calls: Ansible deployment to ct-dev-test. The config.yaml.j2 refactoring of the `mcp_servers` block is the highest-risk change — it touches OMEGA MCP wiring that is already working.
2. **Dependency failure:** If MemPalace is not installed on the target host, the `wire-mempalace.yml` stat check returns false and the MCP entry is omitted — Hermes works without error. If the MemPalace MCP server is down when Hermes tries to use a skill, the skill should report the error gracefully. If `configure-skills.yml` copy fails, no skills deploy — but it uses the same mechanism that already works for wiki-* and bmad-* skills.
3. **Assumptions:** MemPalace venv exists at `~/.mempalace/venv/` (created by Story 6-1). MemPalace MCP server module is `mempalace.mcp_server` (verified in Story 6-1 systemd template). The existing `configure-skills.yml` recursive copy picks up new subdirectories without code changes. Hermes config.yaml.j2 template renders without YAML syntax errors after the mcp_servers block refactoring. OMEGA MCP wiring continues to work after the template refactor (regression risk).

## Eval Assertions

<!-- Binary test assertions derived from acceptance criteria. Used by /autoresearch:fix for post-code-review iteration loops. -->

| # | Assertion | Command/Check | Pass Criteria |
|---|-----------|---------------|---------------|
| AC-1 | MemPalace MCP entry in Hermes config (when MemPalace installed) | `grep -q 'mempalace' ~/.hermes/config.yaml` | Exits with code 0 on host with MemPalace |
| AC-1b | OMEGA MCP entry still present (regression check) | `grep -q 'omega-memory' ~/.hermes/config.yaml` | Exits with code 0 on host with OMEGA |
| AC-1c | Conditional omission when MemPalace absent | Deploy to host without MemPalace; `grep -c 'mempalace' ~/.hermes/config.yaml` | Returns 0 (no match) |
| AC-2 | mempalace-search skill deployed | `test -f ~/.hermes/skills/bmad/mempalace-search/SKILL.md` | Exits with code 0 |
| AC-3 | mempalace-diary skill deployed | `test -f ~/.hermes/skills/bmad/mempalace-diary/SKILL.md` | Exits with code 0 |
| AC-4 | mempalace-kg-query skill deployed | `test -f ~/.hermes/skills/bmad/mempalace-kg-query/SKILL.md` | Exits with code 0 |
| AC-5 | Skills have valid YAML frontmatter | `head -3 ~/.hermes/skills/bmad/mempalace-search/SKILL.md \| grep -q 'name:'` | Exits with code 0 for all 3 skills |
| AC-6 | No BMAD skill files modified | `git diff .claude/skills/bmad-*/` | Empty output (no changes) |

## Tasks / Subtasks

- [ ] Task 1: Add MemPalace detection to Hermes role — conditional MCP wiring (AC: 1)
  - [ ] Create `tasks/wire-mempalace.yml` in the `ai-dev-hermes` role, following the exact pattern from `tasks/wire-omega.yml`:
    - Use `ansible.builtin.stat` to check for the MemPalace venv binary at `{{ ai_dev_hermes_mempalace_venv_path }}/bin/mempalace`
    - Register the result and set fact `ai_dev_hermes_mempalace_available`
  - [ ] Add MemPalace default variables to `defaults/main.yml`:
    - `ai_dev_hermes_mempalace_available: false`
    - `ai_dev_hermes_mempalace_venv_path: "/home/{{ dev_user }}/.mempalace/venv"`
  - [ ] Add `include_tasks: wire-mempalace.yml` to `tasks/main.yml` — place it right after the existing `wire-omega.yml` include (before `configure-hermes.yml` so the fact is available to the template)
  - [ ] Extend `templates/config.yaml.j2` to add a `mempalace` MCP server entry inside the `mcp_servers` block, conditional on `ai_dev_hermes_mempalace_available`:
    ```yaml
    {% if ai_dev_hermes_mempalace_available | default(false) | bool %}
      mempalace:
        command: {{ ai_dev_hermes_mempalace_venv_path }}/bin/python3
        args:
        - -m
        - mempalace.mcp_server
        enabled: true
    {% endif %}
    ```
  - [ ] Handle the `mcp_servers` block merge: currently the block only renders when OMEGA is available. Refactor so `mcp_servers:` renders when EITHER OMEGA or MemPalace is available, with each entry conditional independently. See Dev Notes for the exact template pattern.

- [ ] Task 2: Create `mempalace-search` Hermes skill (AC: 2)
  - [ ] Create `files/skills/mempalace-search/SKILL.md` in the `ai-dev-hermes` role
  - [ ] Use the same YAML frontmatter pattern as `wiki-query/SKILL.md`:
    ```yaml
    ---
    name: mempalace-search
    description: Search MemPalace deep memory for verbatim conversation context and project knowledge.
    version: 0.1.0
    author: homelab
    license: MIT
    metadata:
      hermes:
        tags: [mempalace, search, memory, knowledge-management]
        related_skills: [mempalace-diary, mempalace-kg-query, wiki-query]
    ---
    ```
  - [ ] Skill body should instruct Hermes to:
    - Use the `mempalace_search` MCP tool with a natural language query
    - Optionally filter by wing (e.g., `homelab`) and/or room (e.g., `infra`, `apps`, `planning`)
    - Return ranked results with source metadata (drawer ID, wing, room, timestamp)
    - Include a "When to Use" section: when the operator asks about prior conversations, project history, or detailed context not in the wiki
    - Include error handling: if MCP server is unreachable, report and suggest checking `systemctl --user status mempalace-mcp`

- [ ] Task 3: Create `mempalace-diary` Hermes skill (AC: 3)
  - [ ] Create `files/skills/mempalace-diary/SKILL.md` in the `ai-dev-hermes` role
  - [ ] Skill body should instruct Hermes to:
    - Write diary entries (observations, decisions, lessons learned) as new drawers in MemPalace
    - Target the correct wing based on the active project context (default: `homelab`)
    - Use MCP tools to create drawers with appropriate metadata (wing, room classification)
    - Include a "When to Use" section: after completing a task, making a decision, discovering a lesson, or when the operator explicitly asks to remember something
    - Include guidance on room selection based on content type (see room taxonomy in Dev Notes)

- [ ] Task 4: Create `mempalace-kg-query` Hermes skill (AC: 4)
  - [ ] Create `files/skills/mempalace-kg-query/SKILL.md` in the `ai-dev-hermes` role
  - [ ] Skill body should instruct Hermes to:
    - Query the MemPalace temporal knowledge graph for entity-relationship facts
    - Use KG MCP tools for: entity lookup, relationship traversal, temporal queries (`as_of` for point-in-time, `timeline()` for history)
    - Return structured results: entity, relationship, target, valid_from, valid_to
    - Include a "When to Use" section: when asking about relationships between entities (e.g., "which services run on pve2?"), temporal facts (e.g., "what was the Proxmox version before the upgrade?"), or navigating the project knowledge graph
    - Include guidance on temporal query patterns

- [ ] Task 5: Verify skill deployment via Ansible (AC: 2, 3, 4, 5)
  - [ ] The existing `configure-skills.yml` task already does a recursive copy of `files/skills/` to `~/.hermes/skills/bmad/`. Verify that adding subdirectories `mempalace-search/`, `mempalace-diary/`, `mempalace-kg-query/` under `files/skills/` is picked up automatically by the existing copy task — no changes to `configure-skills.yml` should be needed.
  - [ ] Add VERIFY tasks to `tasks/verify.yml`:
    - VERIFY: MemPalace skills deployed — `test -f ~/.hermes/skills/bmad/mempalace-search/SKILL.md`
    - VERIFY: MemPalace MCP wired (conditional) — if MemPalace detected, grep `config.yaml` for `mempalace` under `mcp_servers`
  - [ ] Deploy to ct-dev-test (192.168.50.152) and confirm:
    - Skills appear at expected paths
    - Hermes config includes MemPalace MCP entry (if MemPalace is installed)
    - Role remains idempotent (second run: changed=0 for skill files)

- [ ] Task 6: Verify BMAD update-safety (AC: 6)
  - [ ] Run `git diff .claude/skills/bmad-*/` and confirm empty output

## Dev Notes

### Architecture Context

This story implements **FR57** and **FR58** from the PRD by wiring MemPalace capabilities into the Hermes Director agent. The architecture specifies MemPalace as the "deep, raw verbatim" layer in the three-tier query hierarchy (Wiki -> MemPalace -> OMEGA). Story 6-5 will implement the query hierarchy itself; this story focuses on giving Hermes the skills and MCP connection to access MemPalace at all.

The research doc (`technical-llm-knowledge-management-research-2026-04-11.md`) confirms: "MemPalace already ships as an OpenClaw skill (v3.1.0). Hermes has native OpenClaw import." However, Story 6-1 installed MemPalace 3.3.0 and found that actual CLI/MCP behavior differs from documentation. **Verify all MCP tool names on ct-dev-test before writing skills.**

### MCP Server Wiring Pattern

The existing OMEGA MCP wiring in `config.yaml.j2` uses a conditional block:

```yaml
{% if ai_dev_hermes_omega_available | default(false) | bool %}
mcp_servers:
  omega-memory:
    command: {{ ai_dev_hermes_omega_binary_path }}
    args:
    - serve
    enabled: true
{% endif %}
```

With MemPalace added, the template must be refactored so `mcp_servers:` renders when EITHER service is available. The correct pattern:

```yaml
{% if (ai_dev_hermes_omega_available | default(false) | bool) or (ai_dev_hermes_mempalace_available | default(false) | bool) %}
mcp_servers:
{% if ai_dev_hermes_omega_available | default(false) | bool %}
  omega-memory:
    command: {{ ai_dev_hermes_omega_binary_path }}
    args:
    - serve
    enabled: true
{% endif %}
{% if ai_dev_hermes_mempalace_available | default(false) | bool %}
  mempalace:
    command: {{ ai_dev_hermes_mempalace_venv_path }}/bin/python3
    args:
    - -m
    - mempalace.mcp_server
    enabled: true
{% endif %}
{% endif %}
```

**Critical:** The MemPalace MCP server runs via the venv Python at `~/.mempalace/venv/bin/python3 -m mempalace.mcp_server`. This is the same command used in the systemd service (`mempalace-mcp.service`). Verify on ct-dev-test that Hermes can connect to it — the MCP server may need to be launched fresh per connection or use the existing systemd socket.

### Hermes Skill Convention

Existing Hermes skills in this project follow a consistent pattern. Use `wiki-query/SKILL.md` as the canonical reference:

- **YAML frontmatter:** `name`, `description`, `version` (0.1.0), `author` (homelab), `license` (MIT), `metadata.hermes.tags`, `metadata.hermes.related_skills`
- **Sections:** Overview, When to Use, Input, Output, Error Handling
- **Skill body:** Natural language instructions for Hermes (not code). Hermes interprets these instructions and uses its MCP tools to execute.
- **File location:** `homelab-infra/ansible/roles/ai-dev-hermes/files/skills/{skill-name}/SKILL.md`
- **Deployment path:** Skills are copied to `~/.hermes/skills/bmad/` by `configure-skills.yml`

### MemPalace MCP Tools (19 tools from research)

The research doc references 19 MCP tools. **Task 1 must verify actual tool names on ct-dev-test** by checking what the MCP server exposes. Expected categories:

- **Search:** semantic search across drawers, filtered by wing/room
- **Drawer operations:** create, read, list drawers (diary write uses this)
- **Knowledge Graph:** entity CRUD, relationship queries, temporal queries
- **Palace management:** status, wing/room listing

### Room Taxonomy (from Story 6-2)

The `homelab` wing has 5 rooms:

| Room | Domain |
|------|--------|
| `infra` | Terraform, Proxmox, networking, DNS, storage |
| `apps` | Docker stacks, services, Traefik, Authelia |
| `playbook` | BMAD workflow, sprints, stories, reviews |
| `epics` | Retrospectives, lessons learned |
| `decisions` | ADRs, architecture choices, trade-offs |

**Note from Story 6-3:** MemPalace mine auto-classifies rooms (e.g., `general`, `planning`) and does NOT necessarily use the wing taxonomy room names. The diary skill should guide Hermes to use the wing's room taxonomy for consistency, but be aware that auto-classified rooms may differ.

### Previous Story Intelligence (6-3)

Key learnings:
- MemPalace 3.3.0 CLI: `init`, `mine`, `search`, `compress`, `wake-up`, `split`, `hook`, `instructions`, `repair`, `mcp`, `migrate`, `status`
- Built-in dedup works reliably (re-run shows "Files skipped (already filed)")
- Room auto-classification by mine differs from manual taxonomy — `general` and `planning` rooms were created by mine
- ChromaDB collection: `mempalace_drawers`
- KG SQLite path: `~/.mempalace/knowledge_graph.sqlite3`
- KG supports temporal queries: `valid_from`, `valid_to`, `as_of`, `invalidate()`, `timeline()`
- MemPalace venv path: `~/.mempalace/venv/`
- **Critical pattern from 6-1, 6-2, 6-3:** Actual CLI/MCP behavior differs from documentation. Always verify on ct-dev-test before writing Ansible tasks or skill instructions.

### What This Story Does NOT Do

- Does NOT implement the query hierarchy (Story 6-5: wiki first -> MemPalace fallback)
- Does NOT create the MemPalace Ansible role from scratch (already done in Stories 6-1, 6-2, 6-3)
- Does NOT wire MemPalace MCP from the mempalace role side (that's cross-role wiring; this story wires from the Hermes role side)
- Does NOT modify `ai-dev-mempalace` role files — all changes are in `ai-dev-hermes` role
- Does NOT enable AAAK compression (raw mode only — AAAK regresses recall to 84.2%)
- Does NOT modify any files in `.claude/skills/bmad-*/` (BMAD update-safety)

### File Modification Summary

| File | Action | Description |
|------|--------|-------------|
| `homelab-infra/ansible/roles/ai-dev-hermes/defaults/main.yml` | Modify | Add MemPalace integration variables |
| `homelab-infra/ansible/roles/ai-dev-hermes/tasks/wire-mempalace.yml` | Create | MemPalace detection (stat + set_fact) |
| `homelab-infra/ansible/roles/ai-dev-hermes/tasks/main.yml` | Modify | Add include for wire-mempalace.yml |
| `homelab-infra/ansible/roles/ai-dev-hermes/templates/config.yaml.j2` | Modify | Add MemPalace MCP entry, refactor mcp_servers conditional |
| `homelab-infra/ansible/roles/ai-dev-hermes/files/skills/mempalace-search/SKILL.md` | Create | MemPalace search skill |
| `homelab-infra/ansible/roles/ai-dev-hermes/files/skills/mempalace-diary/SKILL.md` | Create | MemPalace diary write skill |
| `homelab-infra/ansible/roles/ai-dev-hermes/files/skills/mempalace-kg-query/SKILL.md` | Create | MemPalace KG query skill |
| `homelab-infra/ansible/roles/ai-dev-hermes/tasks/verify.yml` | Modify | Add VERIFY tasks for MemPalace skills and MCP |

### Project Structure Notes

- All changes are within the `homelab-infra/ansible/roles/ai-dev-hermes/` role — consistent with existing patterns
- New skills go under `files/skills/` and are auto-deployed by the existing `configure-skills.yml` task
- MCP wiring follows the established `wire-omega.yml` pattern (stat + set_fact + template conditional)
- No cross-role file modifications

### References

- [Source: planning-artifacts/prd.md#FR57] — "MemPalace is installed with its MCP server providing verbatim conversation storage and semantic search (96.6% recall, 19 MCP tools)"
- [Source: planning-artifacts/prd.md#FR58] — "MemPalace knowledge graph stores temporal entity-relationship facts per project with validity windows"
- [Source: planning-artifacts/architecture.md#Cross-Cutting Concerns] — "Query hierarchy: LLM Wiki, MemPalace, OMEGA"
- [Source: planning-artifacts/architecture.md#Technology Stack] — "Deep Memory: MemPalace, Pinned, ChromaDB + SQLite KG, MCP server (19 tools)"
- [Source: planning-artifacts/sprint-change-proposal-knowledge-mgmt-2026-04-11.md#Epic 6] — "6.4: Wire Hermes MemPalace skill (search, diary write, KG query)"
- [Source: planning-artifacts/research/technical-llm-knowledge-management-research-2026-04-11.md#Hermes + MemPalace] — OpenClaw skill integration path, MCP server config pattern
- [Source: implementation-artifacts/6-1-install-mempalace-and-configure-mcp-server.md] — MemPalace install, CLI, version 3.3.0
- [Source: implementation-artifacts/6-2-initialize-palace-wings-per-project.md] — Palace wing init, ChromaDB patterns, KG API, room taxonomy
- [Source: implementation-artifacts/6-3-mine-existing-conversation-history.md] — Mine CLI, auto-classification, dedup, Ansible task patterns
- [Source: homelab-infra/ansible/roles/ai-dev-hermes/tasks/wire-omega.yml] — Conditional MCP wiring pattern (stat + set_fact)
- [Source: homelab-infra/ansible/roles/ai-dev-hermes/templates/config.yaml.j2#L273-L281] — Current mcp_servers conditional block
- [Source: homelab-infra/ansible/roles/ai-dev-hermes/files/skills/wiki-query/SKILL.md] — Canonical Hermes skill format

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
