# Story 6.5: Implement Query Hierarchy

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a homelab operator,
I want Hermes to implement a query hierarchy that checks the LLM Wiki first (fast, pre-synthesized), falls back to MemPalace (deep, raw verbatim), then OMEGA (cross-project memory),
So that knowledge queries are resolved at the cheapest tier first, reducing token usage on repeat queries while ensuring comprehensive recall for novel questions.

## Acceptance Criteria

1. **Given** Hermes has wiki-query, mempalace-search, and OMEGA MCP tools available
   **When** the `ai-dev-hermes` role deploys skills
   **Then** a `knowledge-query` Hermes skill exists at `~/.hermes/skills/bmad/knowledge-query/SKILL.md`
   **And** the skill follows the existing YAML frontmatter convention (name, description, version, author, metadata.hermes.tags, metadata.hermes.related_skills)

2. **Given** a question that has a high-confidence answer in the LLM Wiki
   **When** the `knowledge-query` skill is invoked
   **Then** the skill queries the wiki first via the wiki-query workflow (read `_index.md`, identify pages, synthesize)
   **And** if the wiki returns a confident answer (pages found with `confidence >= 0.7` and `provenance: extracted`), the answer is returned with wiki citations
   **And** MemPalace and OMEGA are NOT queried (short-circuit at Tier 1)

3. **Given** a question that the wiki cannot answer (zero relevant pages, or only low-confidence/inferred pages)
   **When** the `knowledge-query` skill falls through Tier 1
   **Then** the skill queries MemPalace via the `mempalace_search` MCP tool
   **And** if MemPalace returns relevant results (relevance score above threshold), the answer is synthesized from MemPalace results with source metadata
   **And** OMEGA is NOT queried (short-circuit at Tier 2)

4. **Given** a question that neither the wiki nor MemPalace can answer
   **When** the `knowledge-query` skill falls through Tiers 1 and 2
   **Then** the skill queries OMEGA via MCP tools (`omega_query` or `omega_search`)
   **And** the answer is synthesized from OMEGA results with namespace attribution
   **And** if OMEGA also returns no results, the skill reports "No knowledge found across any tier" with suggestions

5. **Given** the answer was found at any tier
   **When** the skill returns the answer
   **Then** the response includes a `[Source Tier]` label: `[Wiki]`, `[MemPalace]`, or `[OMEGA]`
   **And** the response includes citations appropriate to the tier (wikilinks for Wiki, drawer IDs for MemPalace, memory keys for OMEGA)

6. **Given** any tier's backing service is unavailable (wiki files missing, MemPalace MCP down, OMEGA MCP down)
   **When** the skill encounters the failure
   **Then** the skill logs a warning for that tier and proceeds to the next tier
   **And** the skill does NOT halt on a single tier failure — graceful degradation to available tiers

7. **Given** all implementation is complete
   **When** I check for BMAD update-safety
   **Then** no files in `.claude/skills/bmad-*/` have been modified

## Edge Cases & Error Scenarios

1. **Side effects:** Files created: 1 new `knowledge-query/SKILL.md` under `files/skills/`. Files modified: `tasks/verify.yml` (new VERIFY tasks). State advanced: sprint-status.yaml story status. External calls: Ansible deployment to ct-dev-test. This is a low-risk story — it creates one new skill file and adds verification, without modifying any existing skill files or templates.
2. **Dependency failure:** If wiki structure does not exist (`~/workspace/homelab/wiki/` missing): Tier 1 fails gracefully, falls through to Tier 2. If MemPalace MCP server is down: Tier 2 fails gracefully, falls through to Tier 3. If OMEGA MCP server is down: Tier 3 fails, skill reports no results available. If ALL three tiers are down: skill returns a clear error listing which services are unavailable. The skill must NEVER halt on a single service failure.
3. **Assumptions:** Wiki structure exists at `~/workspace/homelab/wiki/` with `SCHEMA.md`, `_index.md`, `_meta/taxonomy.md` (created by Story 5-1). MemPalace MCP server is running as `mempalace-mcp.service` (Story 6-1). OMEGA MCP server is running as `omega-mcp.service` (Story 2-1). All three memory systems have been populated with content. The existing `configure-skills.yml` recursive copy picks up new subdirectories automatically. The existing wiki-query, mempalace-search, and mempalace-kg-query skills remain unchanged — knowledge-query orchestrates them, it does NOT replace them.

## Eval Assertions

<!-- Binary test assertions derived from acceptance criteria. Used by /autoresearch:fix for post-code-review iteration loops. -->

| # | Assertion | Command/Check | Pass Criteria |
|---|-----------|---------------|---------------|
| AC-1 | knowledge-query skill deployed | `test -f ~/.hermes/skills/bmad/knowledge-query/SKILL.md` | Exits with code 0 |
| AC-1b | Skill has valid YAML frontmatter | `head -3 ~/.hermes/skills/bmad/knowledge-query/SKILL.md \| grep -q 'name:'` | Exits with code 0 |
| AC-2 | Tier 1 (Wiki) is checked first | Review SKILL.md confirms Step 1 is wiki query | Workflow starts with wiki |
| AC-3 | Tier 2 (MemPalace) fallback documented | Review SKILL.md confirms MemPalace is queried when wiki has no answer | MemPalace step follows wiki |
| AC-4 | Tier 3 (OMEGA) fallback documented | Review SKILL.md confirms OMEGA is queried when MemPalace has no answer | OMEGA step follows MemPalace |
| AC-5 | Source tier labels in output format | `grep -q 'Source Tier' ~/.hermes/skills/bmad/knowledge-query/SKILL.md` | Exits with code 0 |
| AC-6 | Graceful degradation documented | `grep -q 'graceful\|degrad\|proceed.*next.*tier\|skip.*tier' ~/.hermes/skills/bmad/knowledge-query/SKILL.md` | Exits with code 0 |
| AC-7 | No BMAD skill files modified | `git diff .claude/skills/bmad-*/` | Empty output (no changes) |

## Tasks / Subtasks

- [x] Task 0: Verify previous story's skill invocation (AC: prerequisite)
  - [x] Confirm the three MemPalace skills from Story 6-4 are deployed on ct-dev-test: `test -f ~/.hermes/skills/bmad/mempalace-search/SKILL.md && test -f ~/.hermes/skills/bmad/mempalace-diary/SKILL.md && test -f ~/.hermes/skills/bmad/mempalace-kg-query/SKILL.md`
  - [x] Confirm MemPalace MCP is wired in Hermes config: `grep -q 'mempalace' ~/.hermes/config.yaml`
  - [x] If either check fails, halt and raise a blocker — Story 6-4 prerequisites are not met

- [x] Task 1: Create `knowledge-query` Hermes skill (AC: 1, 2, 3, 4, 5, 6)
  - [x] Create `files/skills/knowledge-query/SKILL.md` in the `ai-dev-hermes` role at `homelab-infra/ansible/roles/ai-dev-hermes/files/skills/knowledge-query/SKILL.md`
  - [x] Use the same YAML frontmatter pattern as existing skills:
    ```yaml
    ---
    name: knowledge-query
    description: Unified query hierarchy across Wiki, MemPalace, and OMEGA — fast pre-synthesized answers first, deep raw memory second, cross-project memory third.
    version: 0.1.0
    author: homelab
    license: MIT
    metadata:
      hermes:
        tags: [knowledge, query, hierarchy, wiki, mempalace, omega, memory]
        related_skills: [wiki-query, mempalace-search, mempalace-kg-query]
    ---
    ```
  - [x] Skill body must implement the three-tier query hierarchy workflow:
    - **Tier 1 — Wiki (fast, pre-synthesized):** Follow the wiki-query workflow inline (read `_index.md`, identify relevant pages, read them, check confidence/provenance). If pages found with `confidence >= 0.7` and `provenance: extracted`, synthesize answer with `[[wikilink]]` citations and return. Label: `[Source Tier: Wiki]`.
    - **Tier 2 — MemPalace (deep, raw verbatim):** Use the `mempalace_search` MCP tool with the original query. If relevant results returned (check result count and relevance), synthesize answer from MemPalace excerpts with drawer ID citations. Label: `[Source Tier: MemPalace]`.
    - **Tier 3 — OMEGA (cross-project):** Use OMEGA MCP tools (`omega_query` or `omega_search`) with the original query. If results returned, synthesize answer with namespace and memory key citations. Label: `[Source Tier: OMEGA]`.
    - **No results:** If all three tiers return nothing, report: "No knowledge found across Wiki, MemPalace, or OMEGA. Consider ingesting relevant content via wiki-ingest, mempalace-diary, or omega_store."
  - [x] Include graceful degradation: each tier wrapped in error handling. If a tier's service is unavailable (files missing, MCP down), log a warning and proceed to the next tier. The skill must NEVER halt on a single tier failure.
  - [x] Include "When to Use" section: when the operator asks a general knowledge question and does not specify which memory system to search, or when another skill needs context and wants the best answer from the cheapest available source.
  - [x] Include "When NOT to Use" section: when the operator specifically wants to search a single tier (use wiki-query, mempalace-search, or omega directly), when writing content (use wiki-ingest or mempalace-diary), when querying the knowledge graph for entity relationships (use mempalace-kg-query).
  - [x] Skill file must be under 500 lines (project convention)

- [x] Task 2: Add VERIFY tasks to verify.yml (AC: 1)
  - [x] Add a VERIFY task to `homelab-infra/ansible/roles/ai-dev-hermes/tasks/verify.yml`:
    - `VERIFY: knowledge-query skill deployed` — `test -f ~/.hermes/skills/bmad/knowledge-query/SKILL.md`
  - [x] Follow the exact pattern of existing VERIFY tasks in verify.yml (use `ansible.builtin.command` with `changed_when: false`)

- [x] Task 3: Deploy to ct-dev-test and verify (AC: 1, 2, 3, 4, 5, 6)
  - [x] Run: `ansible-playbook playbooks/deploy-ai-dev-container.yml --limit ct-dev-test --tags ai-dev-hermes -i inventories/homelab/hosts.ini` — ok=115, changed=2 (Docker restart + new skill), failed=0
  - [x] Confirm skill deployed: `test -f ~/.hermes/skills/bmad/knowledge-query/SKILL.md` on ct-dev-test — rc=0
  - [x] Confirm idempotency: second run shows changed=1 (Docker restart only, skill files ok=no change)
  - [x] Run verify tags: `ansible-playbook playbooks/deploy-ai-dev-container.yml --limit ct-dev-test --tags verify -i inventories/homelab/hosts.ini` — ok=86, changed=0, failed=0

- [x] Task 4: Verify BMAD update-safety (AC: 7)
  - [x] Run `git diff .claude/skills/bmad-*/` and confirm empty output

### Review Findings

- [x] [Review][Defer] Hardcoded wiki path `~/workspace/homelab/wiki/` in knowledge-query SKILL.md — deferred, matches existing wiki-query pattern established in Story 5-3

### Senior Developer Review (AI)

**Review Date:** 2026-04-16
**Review Outcome:** Approve
**Layers:** Blind Hunter, Edge Case Hunter, Acceptance Auditor
**Summary:** 0 decision-needed, 0 patch, 1 defer, 2 dismissed. All 7 acceptance criteria satisfied. Skill follows established conventions (YAML frontmatter, section structure, error handling). Verify.yml changes are minimal and correct. BMAD update-safety confirmed.

## Dev Notes

### Architecture Context

This story implements **FR59** from the PRD: "Hermes implements a query hierarchy: check LLM Wiki first (fast, pre-synthesized), fall back to MemPalace (deep, raw), then OMEGA (cross-project)."

The architecture document specifies this as a **Cross-Cutting Concern**: "Query hierarchy: LLM Wiki, MemPalace, OMEGA — Wiki (fast, pre-synthesized) -> MemPalace (deep, raw verbatim) -> OMEGA (cross-project memory)."

The design rationale: Wiki pages are distilled, structured, and cheap to read (file I/O only). MemPalace has raw verbatim transcripts indexed by ChromaDB (MCP call + semantic search). OMEGA stores cross-project memories (MCP call + embedding search). Checking in this order minimizes cost while maximizing recall.

### Skill Design: Orchestrator Pattern

The `knowledge-query` skill is an **orchestrator** — it does NOT replace the existing individual skills. It delegates to them in sequence:

1. It inlines the wiki-query logic (file reads) rather than invoking wiki-query as a sub-skill, because Hermes skills are instruction documents, not callable functions.
2. It uses MemPalace MCP tools directly (same as mempalace-search would).
3. It uses OMEGA MCP tools directly.

The individual skills (wiki-query, mempalace-search, mempalace-kg-query) remain available for direct use when the operator wants to target a specific tier.

### Tier Decision Logic

**Tier 1 (Wiki) success criteria:**
- `_index.md` has page entries
- At least one page matches the query topic
- Matching pages have `confidence >= 0.7` AND `provenance: extracted`
- If only `inferred` or `stale` pages found, qualify the answer but still return at Tier 1 (do NOT fall through for merely low-confidence wiki content — the wiki is still the authoritative source)

**Tier 2 (MemPalace) success criteria:**
- `mempalace_search` MCP tool returns at least 1 result
- Results have meaningful content excerpts (not empty or irrelevant)
- If results exist but seem tangential, still return them with a caveat

**Tier 3 (OMEGA) success criteria:**
- OMEGA MCP `omega_query` or `omega_search` returns results
- Results are from the relevant namespace

### Graceful Degradation

Each tier must be wrapped in error handling. Failure modes:

| Tier | Failure Mode | Action |
|------|-------------|--------|
| Wiki | `wiki/` directory or `_index.md` missing | Log "Wiki unavailable — skipping Tier 1", proceed to Tier 2 |
| Wiki | Zero pages in wiki | Log "Wiki empty — skipping Tier 1", proceed to Tier 2 |
| MemPalace | MCP server unreachable | Log "MemPalace MCP unavailable — skipping Tier 2", proceed to Tier 3 |
| MemPalace | Search returns error | Log error details, proceed to Tier 3 |
| OMEGA | MCP server unreachable | Log "OMEGA MCP unavailable — skipping Tier 3", report no results |
| OMEGA | Search returns error | Log error details, report no results |
| All | All tiers fail | Report "All knowledge tiers unavailable" with diagnostic suggestions |

### Previous Story Intelligence (6-4)

Key learnings from Story 6-4:
- The existing `configure-skills.yml` recursive copy picks up new subdirectories without code changes — confirmed working for mempalace-search, mempalace-diary, and mempalace-kg-query
- The `config.yaml.j2` mcp_servers block was refactored in 6-4 to support both OMEGA and MemPalace conditionally — no template changes needed for this story
- Skill YAML frontmatter convention: `name`, `description`, `version` (0.1.0), `author` (homelab), `license` (MIT), `metadata.hermes.tags`, `metadata.hermes.related_skills`
- Skills are natural language instructions for Hermes, not executable code
- MemPalace venv path: `~/.mempalace/venv/`
- MemPalace MCP server module: `mempalace.mcp_server`
- Room auto-classification by mine may differ from manual taxonomy

### What This Story Does NOT Do

- Does NOT modify existing skills (wiki-query, mempalace-search, mempalace-kg-query, mempalace-diary)
- Does NOT modify Hermes config.yaml.j2 template (no new MCP wiring needed — all MCP connections already exist from 6-4)
- Does NOT modify defaults/main.yml (no new variables needed)
- Does NOT modify tasks/main.yml (no new task includes needed)
- Does NOT create the MemPalace Ansible role (Story 6-6)
- Does NOT modify any files in `.claude/skills/bmad-*/` (BMAD update-safety)

### File Modification Summary

| File | Action | Description |
|------|--------|-------------|
| `homelab-infra/ansible/roles/ai-dev-hermes/files/skills/knowledge-query/SKILL.md` | Create | Unified query hierarchy skill |
| `homelab-infra/ansible/roles/ai-dev-hermes/tasks/verify.yml` | Modify | Add VERIFY task for knowledge-query skill |

### Project Structure Notes

- New skill goes under `files/skills/knowledge-query/` following the established convention
- Deployment via existing `configure-skills.yml` recursive copy — no changes needed
- All changes are within the `homelab-infra/ansible/roles/ai-dev-hermes/` role

### References

- [Source: planning-artifacts/prd.md#FR59] — "Hermes implements a query hierarchy: check LLM Wiki first (fast, pre-synthesized), fall back to MemPalace (deep, raw), then OMEGA (cross-project)"
- [Source: planning-artifacts/architecture.md#Cross-Cutting Concerns] — "Query hierarchy: LLM Wiki, MemPalace, OMEGA — Wiki (fast, pre-synthesized) -> MemPalace (deep, raw verbatim) -> OMEGA (cross-project memory)"
- [Source: planning-artifacts/sprint-change-proposal-knowledge-mgmt-2026-04-11.md#Epic 6] — "6.5: Implement query hierarchy: wiki first -> MemPalace fallback"
- [Source: implementation-artifacts/6-4-wire-hermes-mempalace-skills.md] — Previous story: MCP wiring, skill conventions, configure-skills.yml behavior
- [Source: homelab-infra/ansible/roles/ai-dev-hermes/files/skills/wiki-query/SKILL.md] — Wiki query workflow (inlined by Tier 1)
- [Source: homelab-infra/ansible/roles/ai-dev-hermes/files/skills/mempalace-search/SKILL.md] — MemPalace search workflow (referenced by Tier 2)
- [Source: homelab-infra/ansible/roles/ai-dev-hermes/files/skills/mempalace-kg-query/SKILL.md] — KG query workflow (not used by hierarchy, but related)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Deployment Verification

Verified with command: `ansible-playbook playbooks/deploy-ai-dev-container.yml --limit ct-dev-test --tags ai-dev-hermes -i inventories/homelab/hosts.ini`
Result: 8/8 assertions passed (4 local + 4 remote).
All eval assertions verified on target ct-dev-test (192.168.50.152).

Remote assertion results:
- [AC-1] knowledge-query skill deployed: PASS (rc=0)
- [AC-1b] YAML frontmatter present: PASS (rc=0)
- [AC-5] Source Tier labels: PASS (rc=0)
- [AC-6] Graceful degradation documented: PASS (rc=0)
- Idempotency: PASS (second run changed=1, skill files unchanged)
- Verify tags: PASS (ok=86, changed=0, failed=0)

### Debug Log References

None required — straightforward skill creation with no debugging needed.

### Completion Notes List

- Created `knowledge-query` Hermes skill (270 lines, under 500 limit) implementing the three-tier query hierarchy: Wiki -> MemPalace -> OMEGA
- Skill includes full workflow with tier decision gates, graceful degradation for each tier, source tier labels, and per-tier citation formats
- Added VERIFY task to verify.yml for knowledge-query skill deployment check
- Updated skill count threshold in verify.yml from 9 to 10 to account for new skill
- All eval assertions pass locally (file exists, YAML frontmatter, Source Tier labels, graceful degradation docs, BMAD update-safety)
- Tasks 0, 1, 2, 4 complete. Task 3 (deployment) deferred to pipeline deployment step.

### File List

- `homelab-infra/ansible/roles/ai-dev-hermes/files/skills/knowledge-query/SKILL.md` (created)
- `homelab-infra/ansible/roles/ai-dev-hermes/tasks/verify.yml` (modified — added VERIFY task, updated skill count)
- `homelab-playbook/_bmad-output/implementation-artifacts/sprint-status.yaml` (modified — status updates)
- `homelab-playbook/_bmad-output/implementation-artifacts/6-5-implement-query-hierarchy.md` (created — story file)
