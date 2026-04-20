# Story 6.2: Initialize Palace Wings per Project

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a homelab operator,
I want MemPalace initialized with palace wings per project, a room taxonomy matching my knowledge domains, and a temporal knowledge graph with validity windows,
So that deep memory is organized by project with semantic structure that supports targeted recall, cross-domain traversal, and fact expiration.

## Acceptance Criteria

1. **Given** MemPalace 3.3.0 is installed and its MCP server is active on ct-dev-test (Story 6-1 done)
   **When** I run `mempalace init` for the `homelab` project
   **Then** a palace wing named `homelab` is created with rooms matching the project's knowledge domains (infra, apps, playbook, epics, decisions)
   **And** the palace data is stored under `~/.mempalace/palace/` (or the configured data directory)
   **And** `mempalace status` shows the new wing and its rooms

2. **Given** the `homelab` wing is initialized
   **When** I examine the room taxonomy
   **Then** each room maps to a bounded knowledge domain: `infra` (Terraform, Proxmox, networking), `apps` (Docker stacks, services), `playbook` (BMAD, sprints, stories), `epics` (epic retros, lessons learned), `decisions` (architecture decisions, ADRs)
   **And** each room contains halls for memory types: `facts`, `events`, `discoveries`, `preferences`, `advice`
   **And** the taxonomy is documented in a configuration file (YAML or JSON) that can be version-controlled

3. **Given** the palace wings are initialized
   **When** I add a fact to the knowledge graph with a validity window (e.g., "pve3 runs PVE 9.x" valid from 2026-04-16)
   **Then** `mempalace kg_add` stores the entity-relationship triple with a `valid_from` timestamp
   **And** `mempalace kg_query` returns the fact when queried within its validity window
   **And** facts with expired validity windows are excluded from default queries (or flagged as expired)

4. **Given** the `homelab` wing exists
   **When** I initialize a second wing for `sparkle-cps` (or any other project)
   **Then** the second wing is created independently without affecting the `homelab` wing
   **And** cross-wing queries do not leak results between projects (wing isolation)
   **And** `mempalace status` shows both wings

5. **Given** all palace initialization is complete
   **When** I create an Ansible task file `configure-palace.yml` in the `ai-dev-mempalace` role
   **Then** the task file initializes palace wings using variables from `defaults/main.yml` (wing names, room taxonomy)
   **And** the task is idempotent: re-running does not duplicate wings or rooms
   **And** the task is integrated into the role's `tasks/main.yml` execution order (after install, before verify)

6. **Given** all implementation is complete
   **When** I check for BMAD update-safety
   **Then** no files in `.claude/skills/bmad-*/` have been modified

## Edge Cases & Error Scenarios

1. **Side effects:**
   - Palace data directories created/expanded under `~/.mempalace/palace/` (ChromaDB collections, SQLite KG entries)
   - `defaults/main.yml` in `ai-dev-mempalace` role modified (new variables added)
   - New task file `configure-palace.yml` created in the role
   - `tasks/main.yml` modified to include the new task file
   - `verify.yml` modified with additional VERIFY checks for palace structure
   - Sprint status advanced: 6-2 to ready-for-dev

2. **Dependency failure:**
   - If MemPalace MCP service is not running (Story 6-1 prerequisite): `mempalace init` or `mempalace status` will fail; verify service is active before proceeding
   - If `mempalace init` does not support wing/room creation via CLI flags: may need to use MCP tools (`mempalace_palace_graph`) or direct ChromaDB/SQLite operations; Task 1 discovery is critical
   - If KG `valid_from`/`valid_until` fields are not supported natively: document the gap, propose metadata-based workaround (do not block the story)
   - If ChromaDB runs out of disk during wing creation: verify `~/.mempalace/palace/` has sufficient space (~500 MB headroom)
   - If Ansible task idempotency fails (duplicate wings on re-run): use `stat` or `mempalace status` output to gate wing creation

3. **Assumptions:**
   - Story 6-1 is done: MemPalace 3.3.0 installed, `mempalace-mcp.service` active, Claude Code MCP entry configured
   - `~/.mempalace/venv/bin/mempalace` binary is functional and in PATH for the Ansible role tasks
   - The `mempalace init` subcommand supports project/wing specification (to be verified in Task 1)
   - Room taxonomy is defined at Ansible variable level, not hard-coded in tasks
   - MemPalace KG supports temporal entity-relationship triples (from research; to be verified in Task 4)
   - `loginctl enable-linger` is already set (from Story 1-3)

## Eval Assertions

<!-- Binary test assertions derived from acceptance criteria. Used by /autoresearch:fix for post-code-review iteration loops. -->

| # | Assertion | Command/Check | Pass Criteria |
|---|-----------|---------------|---------------|
| AC-1 | Homelab wing initialized | `~/.mempalace/venv/bin/mempalace status 2>/dev/null \| grep -qi 'homelab'` | Exits with code 0, wing "homelab" appears in output |
| AC-2 | Room taxonomy matches design | `~/.mempalace/venv/bin/mempalace status 2>/dev/null \| grep -cEi 'infra\|apps\|playbook\|epics\|decisions'` | Count >= 5 (all five rooms present) |
| AC-3 | KG fact with validity window | `~/.mempalace/venv/bin/mempalace kg_query --entity pve3 2>/dev/null \| grep -qi 'valid'` | Exits with code 0, fact returned with temporal metadata |
| AC-4 | Wing isolation (no cross-leak) | Add fact to wing A, query wing B, confirm absence | Query to second wing returns no results from first wing |
| AC-5 | Ansible task idempotent | Run `ansible-playbook deploy-ai-dev-container.yml --tags mempalace` twice, compare changed count | Second run reports 0 changed for configure-palace tasks |
| AC-6 | BMAD update-safety | `git diff .claude/skills/bmad-*/` | Empty output (no changes) |

## Tasks / Subtasks

- [x] Task 1: Discover MemPalace CLI init/wing/room capabilities (AC: 1, 2)
  - [x] SSH to ct-dev-test and run `~/.mempalace/venv/bin/mempalace --help` and `~/.mempalace/venv/bin/mempalace init --help` to document available subcommands and options
  - [x] Determine how wings are created: CLI flags, config file, or API calls via MCP tools
  - [x] Determine how rooms and halls are defined: automatic from first write, or explicit creation needed
  - [x] Check if `mempalace status` shows wing/room structure
  - [x] Document findings in Dev Agent Record before proceeding

- [x] Task 2: Define room taxonomy for homelab project (AC: 2)
  - [x] Create a taxonomy configuration mapping project knowledge domains to rooms:
    - `infra`: Terraform modules, Proxmox nodes, networking, DNS, storage
    - `apps`: Docker Compose stacks, services, Traefik routes, Authelia SSO
    - `playbook`: BMAD workflow, sprint planning, story specs, code reviews
    - `epics`: Epic retrospectives, lessons learned, deployment patterns
    - `decisions`: Architecture decisions, ADRs, technology choices, trade-offs
  - [x] Each room gets standard hall types: `facts`, `events`, `discoveries`, `preferences`, `advice`
  - [x] Store taxonomy in a version-controllable format (YAML preferred, matching Ansible conventions)

- [x] Task 3: Initialize homelab palace wing with rooms (AC: 1, 2)
  - [x] Run `mempalace init` (or equivalent) on ct-dev-test to create the `homelab` wing
  - [x] Create rooms per the taxonomy from Task 2
  - [x] Verify wing and room structure via `mempalace status`
  - [x] Test a basic `mempalace search` query to confirm the wing is operational

- [x] Task 4: Validate temporal knowledge graph with validity windows (AC: 3)
  - [x] Add a test fact with `mempalace kg_add` (or equivalent MCP tool): entity-relationship triple with `valid_from` timestamp
  - [x] Query the fact with `mempalace kg_query` and confirm it returns within the validity window
  - [x] If MemPalace supports `valid_until`, add a fact with an expiration and confirm it is excluded from queries after expiry
  - [x] If MemPalace does not support validity windows natively, document the gap and propose a workaround (e.g., metadata tags, custom fields) in Dev Agent Record
  - [x] Record the actual KG CLI/MCP tool names and syntax discovered

- [x] Task 5: Validate wing isolation with a second project (AC: 4)
  - [x] Initialize a second wing (e.g., `sparkle-cps` or `test-project`) on ct-dev-test
  - [x] Add a fact to each wing
  - [x] Query each wing and confirm no cross-wing result leakage
  - [x] Run `mempalace status` to confirm both wings are listed independently

- [x] Task 6: Create `configure-palace.yml` Ansible task file (AC: 5)
  - [x] Add palace configuration variables to `roles/ai-dev-mempalace/defaults/main.yml`:
    - `ai_dev_mempalace_wings`: list of wing names (default: `["{{ project_name }}"]`)
    - `ai_dev_mempalace_room_taxonomy`: dict mapping room names to descriptions
    - `ai_dev_mempalace_hall_types`: list of hall types (default: `[facts, events, discoveries, preferences, advice]`)
  - [x] Create `roles/ai-dev-mempalace/tasks/configure-palace.yml` that:
    - Loops over `ai_dev_mempalace_wings` to initialize each wing
    - Creates rooms per the taxonomy for each wing
    - Uses `creates:` or `stat` checks for idempotency (skip if wing already exists)
  - [x] Add `include_tasks: configure-palace.yml` to `tasks/main.yml` (after install/systemd, before verify)
  - [x] Test idempotency: run the role twice, confirm no changed tasks on second run

- [x] Task 7: Deploy and verify on ct-dev-test (AC: 1-5)
  - [x] Run the full `ai-dev-mempalace` role on ct-dev-test
  - [x] Verify palace wing exists with correct room taxonomy
  - [x] Verify KG operations work (add fact, query fact)
  - [x] Run role a second time to confirm idempotency

- [x] Task 8: Verify BMAD update-safety (AC: 6)
  - [x] Run `git diff .claude/skills/bmad-*/` and confirm empty output

## Dev Notes

### Architecture Context

This story implements **FR58** from the PRD: "MemPalace knowledge graph stores temporal entity-relationship facts per project with validity windows." It also establishes the palace structure required by the architecture's planned decision: "MemPalace palace wing taxonomy (rooms, halls per project type)."

The architecture defines a **query hierarchy**: Wiki (fast, pre-synthesized) -> MemPalace (deep, raw verbatim) -> OMEGA (cross-project memory). This story sets up the MemPalace layer's organizational structure. The query hierarchy wiring itself is Story 6-5.

### MemPalace Architecture (from Research)

The palace metaphor maps to a physical memory palace:

```
Palace
  Wings (people/projects)
    Rooms (topics: auth, billing, deployment)
      Halls (memory types: facts, events, discoveries, preferences, advice)
        Closets (summaries -> point to originals)
        Drawers (verbatim original chunks)
    Tunnels (cross-wing connections)
  Knowledge Graph (temporal entity-relationship triples)
```

**Memory Layers:**

| Layer | Size | Loading | Purpose |
|-------|------|---------|---------|
| L0: Identity | ~50 tokens | Always | Who is the user |
| L1: Critical facts | ~120 tokens (AAAK) | Always | Key facts, compressed |
| L2: Room recall | Variable | On-demand | Topic-specific memory |
| L3: Deep search | Variable | On-demand | Full semantic search |

**Important:** Use **raw mode only** -- AAAK compression regresses recall from 96.6% to 84.2% (project's own disclosure).

### MemPalace CLI Reference

MemPalace 3.3.0 CLI subcommands (installed at `~/.mempalace/venv/bin/mempalace`):

`init`, `mine`, `search`, `compress`, `wake-up`, `split`, `hook`, `instructions`, `repair`, `mcp`, `migrate`, `status`

**Task 1 is critical:** The exact CLI syntax for wing/room creation, KG operations, and status queries must be discovered by running `--help` on ct-dev-test. Do NOT assume command syntax -- verify it.

### Ansible Role Extension Pattern

Story 6-1 created the `ai-dev-mempalace` role. This story extends it by:
1. Adding variables to `defaults/main.yml` (wing names, room taxonomy)
2. Creating a new task file `configure-palace.yml`
3. Including it in `tasks/main.yml`

Follow the existing role structure exactly. The role lives at: `homelab-infra/ansible/roles/ai-dev-mempalace/`

**Current role task files (from Story 6-1):**
- `tasks/main.yml` -- orchestrates all task files
- `tasks/install-mempalace.yml` -- pip install into venv
- `tasks/configure-systemd.yml` -- systemd user service
- `tasks/configure-claude-mcp.yml` -- Claude Code MCP wiring
- `tasks/configure-gitignore.yml` -- git exclusions
- `tasks/verify.yml` -- VERIFY-prefixed health checks

### Room Taxonomy Design

The room taxonomy is project-specific. For `homelab`:

| Room | Domain | Example Contents |
|------|--------|-----------------|
| `infra` | Terraform, Proxmox, networking, DNS, storage | Node specs, VLAN config, ZFS pools, NFS shares |
| `apps` | Docker stacks, services, routing | Traefik routes, Authelia SSO, media stack config |
| `playbook` | BMAD workflow, sprints, stories | Sprint status, story patterns, code review findings |
| `epics` | Retrospectives, lessons learned | Epic retros, deployment lessons, fix patterns |
| `decisions` | ADRs, architecture choices | Technology trade-offs, stack decisions, migration plans |

For `sparkle-cps` (future):

| Room | Domain | Example Contents |
|------|--------|-----------------|
| `cps-fabric` | CPS-Fabric repos, Azure DevOps | Pipeline config, deployment patterns |
| `architecture` | Solution design, integration | API contracts, service topology |
| `operations` | Monitoring, incidents | Alert rules, runbooks, post-mortems |

### Knowledge Graph Temporal Facts

MemPalace's KG stores entity-relationship triples with temporal validity. Example:

```
Entity: pve3
Relationship: runs
Target: Proxmox VE 9.x
Valid From: 2026-04-16
Valid Until: null (current)
```

This enables time-aware queries: "What was pve3 running in March 2026?" would return "Proxmox VE 8.4" if that fact existed with the appropriate validity window.

**Caveat:** The research notes that contradiction detection exists but is "not wired into knowledge graph operations." If temporal invalidation is not automatic, facts must be manually expired using `kg_invalidate` or equivalent.

### Previous Story Intelligence (6-1)

Key learnings from Story 6-1:
- MemPalace PyPI version was 3.3.0 (not 0.4.2 as initially assumed -- always verify on target)
- `mempalace serve` does not exist; MCP uses `python -m mempalace.mcp_server` with stdio transport
- Systemd service uses `Type=oneshot` + `RemainAfterExit` as a readiness gate (Claude Code spawns MCP itself)
- Surgical JSON merge for Claude Code settings uses a Python script
- All 12 VERIFY tasks pass on ct-dev-test
- The role uses the `ai-dev-omega-memory` pattern exactly
- Virtualenv at `~/.mempalace/venv/` isolates dependencies from OMEGA

**Critical pattern:** Story 6-1 discovered that MemPalace's actual CLI behavior differed from documentation assumptions. **Always verify commands on ct-dev-test before writing Ansible tasks.**

### What This Story Does NOT Do

- Does NOT mine existing conversation history (Story 6-3)
- Does NOT wire Hermes MemPalace skills (Story 6-4)
- Does NOT implement query hierarchy (Story 6-5)
- Does NOT create the full deployment composition test (Story 6-6)
- Does NOT enable AAAK compression (use raw mode only)
- Does NOT modify any files in `.claude/skills/bmad-*/` (BMAD update-safety)

### File Modification Summary

| File | Action | Description |
|------|--------|-------------|
| `homelab-infra/ansible/roles/ai-dev-mempalace/defaults/main.yml` | Modify | Add wing names, room taxonomy, hall types variables |
| `homelab-infra/ansible/roles/ai-dev-mempalace/tasks/configure-palace.yml` | Create | Palace wing/room initialization tasks |
| `homelab-infra/ansible/roles/ai-dev-mempalace/tasks/main.yml` | Modify | Add include for configure-palace.yml |
| `homelab-infra/ansible/roles/ai-dev-mempalace/tasks/verify.yml` | Modify | Add VERIFY tasks for palace structure |

### References

- [Source: planning-artifacts/prd.md#FR58] -- "MemPalace knowledge graph stores temporal entity-relationship facts per project with validity windows"
- [Source: planning-artifacts/architecture.md#Planned Decisions] -- "MemPalace palace wing taxonomy (rooms, halls per project type)"
- [Source: planning-artifacts/architecture.md#Cross-Cutting Concerns] -- "Query hierarchy: LLM Wiki, MemPalace, OMEGA"
- [Source: planning-artifacts/architecture.md#Technology Stack] -- "Deep Memory: MemPalace, Pinned, ChromaDB + SQLite KG, MCP server (19 tools)"
- [Source: planning-artifacts/research/technical-llm-knowledge-management-research-2026-04-11.md#Part 2: MemPalace] -- Palace metaphor architecture, memory layers, MCP tools, caveats
- [Source: planning-artifacts/research/technical-llm-knowledge-management-research-2026-04-11.md#Part 12: Epic Planning Guidance] -- "6.2: Initialize palace wings per project with room taxonomy"
- [Source: implementation-artifacts/6-1-install-mempalace-and-configure-mcp-server.md] -- Previous story: role structure, CLI findings, deployment lessons

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

- Task 1 Discovery: `mempalace init <dir> --yes` auto-detects rooms from folder structure, saves `mempalace.yaml` in project dir. Wings/rooms are NOT created via CLI flags -- they are created dynamically when drawers are added via ChromaDB collection `mempalace_drawers` (NOT `palace`).
- `mcp_server.py` cannot be imported directly in scripts -- it parses CLI args at module level and initializes KG at import time. Must use ChromaDB and KG modules directly for Ansible tasks.
- ChromaDB collection name is `mempalace_drawers` (from `MempalaceConfig().collection_name`), not `palace`.
- KG default path is `~/.mempalace/knowledge_graph.sqlite3` (NOT `palace/knowledge_graph.db`).
- `.mempalace/` directory ownership was root (from Story 6-1 Ansible install). Added ownership fix task to configure-palace.yml.
- ChromaDB downloaded ONNX embedding model (~79 MB) on first use -- `all-MiniLM-L6-v2`.
- KG natively supports `valid_from`, `valid_to`, `as_of` temporal queries, `invalidate()`, and `timeline()`. No workaround needed.

### Completion Notes List

- Task 1: Discovered MemPalace 3.3.0 CLI/API behavior. `mempalace init` is for folder-based room detection, not wing creation. Wings are created by adding drawers with wing/room metadata to the `mempalace_drawers` ChromaDB collection. MCP tools: `mempalace_kg_add`, `mempalace_kg_query`, `mempalace_kg_invalidate`, `mempalace_kg_timeline`, `mempalace_kg_stats`.
- Task 2: Room taxonomy defined in `defaults/main.yml` as `ai_dev_mempalace_wings` variable with 5 rooms (infra, apps, playbook, epics, decisions) and 5 hall types. Also rendered as `mempalace.yaml` per project via Jinja2 template.
- Task 3: Homelab wing initialized with 5 rooms seeded as ChromaDB drawers. `mempalace status` shows all 5 rooms. `mempalace search` returns semantically ranked results by wing/room.
- Task 4: KG temporal facts fully validated. `add_triple()` with `valid_from`/`valid_to`, `query_entity()` with `as_of`, `invalidate()`, and `timeline()` all work natively. Test fact: pve3 -> runs -> Proxmox VE 9.x (valid_from=2026-04-16).
- Task 5: Wing isolation confirmed. Created test-project wing, verified no cross-wing data leakage in either direction using ChromaDB `where={"wing": ...}` filtering. Cleaned up test wing after verification.
- Task 6: Created `configure-palace.yml` Ansible task file with 5 tasks: fix ownership, ensure palace dir, deploy mempalace.yaml templates, check/seed rooms, init KG. Added 4 VERIFY tasks to verify.yml. Idempotency verified: re-running seeding skips all existing drawers (5/5 skipped, 0 new).
- Task 7: All operations verified on ct-dev-test (192.168.50.152). Palace wing exists with correct taxonomy, KG operations work with temporal validity, search returns correct results, idempotency confirmed.
- Task 8: `git diff .claude/skills/bmad-*/` returns empty output. No BMAD files modified.

### File List

- `homelab-infra/ansible/roles/ai-dev-mempalace/defaults/main.yml` (modified) -- Added `ai_dev_mempalace_wings` and `ai_dev_mempalace_hall_types` variables
- `homelab-infra/ansible/roles/ai-dev-mempalace/tasks/configure-palace.yml` (created) -- Palace wing/room initialization tasks
- `homelab-infra/ansible/roles/ai-dev-mempalace/tasks/main.yml` (modified) -- Added include for configure-palace.yml
- `homelab-infra/ansible/roles/ai-dev-mempalace/tasks/verify.yml` (modified) -- Added 4 VERIFY tasks for palace structure
- `homelab-infra/ansible/roles/ai-dev-mempalace/templates/mempalace.yaml.j2` (created) -- Jinja2 template for per-project mempalace.yaml config
- `homelab-playbook/_bmad-output/implementation-artifacts/sprint-status.yaml` (modified) -- Story 6-2 status updated
- `homelab-playbook/_bmad-output/implementation-artifacts/6-2-initialize-palace-wings-per-project.md` (modified) -- Story file updated

### Change Log

- 2026-04-16: Story 6-2 implemented. Palace wings initialized for homelab project with 5 rooms (infra, apps, playbook, epics, decisions) and temporal KG validated on ct-dev-test. Ansible role extended with configure-palace.yml, 4 new VERIFY tasks, and mempalace.yaml template.
