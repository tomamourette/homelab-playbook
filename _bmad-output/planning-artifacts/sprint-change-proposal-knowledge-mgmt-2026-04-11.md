---
status: approved
created: 2026-04-11
trigger: Technical research on LLM Wiki, MemPalace, Obsidian, and knowledge ingestion pipelines
scope_classification: moderate
mode: batch
---

# Sprint Change Proposal — Knowledge Management Expansion

**Date:** 2026-04-11
**Author:** tomamourette
**Trigger:** Technical research completed on LLM knowledge management systems (LLM Wiki, MemPalace, Hermes Agent extensions, Obsidian, Linear/Granola/Azure DevOps MCP ingestion pipelines)

---

## Checklist Section 1: Trigger and Context

### 1.1 Triggering Story
[x] Done

No specific story triggered this change. The trigger is a **technical research session** (2026-04-11) that explored three knowledge management systems and three MCP-based ingestion sources. The research revealed concrete capabilities that extend the project's vision of "compound learning" beyond what the original PRD scoped.

### 1.2 Core Problem
[x] Done

**Category:** New requirements emerged from technical research

**Problem Statement:** The current PRD envisions a persistent memory system (OMEGA) and an always-on Director (Hermes), but lacks:
1. A **synthesized knowledge layer** — OMEGA stores raw memories but nothing distills them into structured, interlinked understanding (LLM Wiki pattern)
2. A **deep verbatim memory** with semantic search beyond OMEGA's session-oriented capture (MemPalace)
3. A **human-readable knowledge viewer** — no way for Tom to browse, navigate, and review what the AI knows (Obsidian)
4. **Automated knowledge ingestion** from external sources — the Product Brief's Phase 2 mentions "Slack, email, Granola MCPs" but with no concrete design for how tickets (Linear), meetings (Granola), or web articles flow into the knowledge system

### 1.3 Supporting Evidence
[x] Done

- **Research report:** `planning-artifacts/research/technical-llm-knowledge-management-research-2026-04-11.md` (12 sections, 14 verified sources)
- **LLM Wiki** (Karpathy, April 2026): Proven pattern with 5+ community Obsidian implementations, zero infrastructure cost
- **MemPalace**: 96.6% recall on LongMemEval, ships as OpenClaw skill for Hermes, MCP-native (19 tools)
- **Linear MCP**: Official, 21 tools, GA
- **Granola MCP**: Already connected in our environment (5 tools)
- **Azure DevOps MCP**: Microsoft official, GA
- **Hermes memory providers**: Honcho supports cross-instance shared user modeling

---

## Checklist Section 2: Epic Impact Assessment

### 2.1 Current Epic (Epic 3)
[x] Done

**Epic 3 (Always-On Director) can proceed as planned.** No modifications needed. The new epics are additive and depend on Epic 3 completing first (Hermes must be installed before it can run wiki/ingestion skills).

### 2.2 Required Epic-Level Changes
[x] Done — Action-needed

**Add three new epics:**

| New Epic | Title | Dependency |
|----------|-------|-----------|
| **Epic 5** | LLM Wiki + Obsidian Integration | Epic 3 (Hermes skills) |
| **Epic 6** | MemPalace — Deep Memory | Epic 3 (Hermes MCP), enhanced by Epic 5 |
| **Epic 7** | Knowledge Ingestion Pipelines | Epic 5 (wiki-ingest skill) |

### 2.3 Remaining Planned Epics
[x] Done

| Epic | Impact |
|------|--------|
| **Epic 3** (Hermes Director) | No change. Proceeds as planned. Becomes prerequisite for Epics 5-7. |
| **Epic 4** (One-Command Deployment) | **Minor update needed.** The Ansible playbook should be parameterized to optionally include new roles (`ai-dev-obsidian-wiki`, `ai-dev-mempalace`). But Epic 4 can still be implemented as-is with just the original 3 roles, and extended later. |

### 2.4 New Epics Required
[x] Done

Yes — three new epics are needed. See detailed breakdown in Section 3 and Summary.

### 2.5 Epic Order / Priority
[x] Done

**No reordering of existing epics.** The new epics append after Epic 4:

```
Epic 0: BMAD Workflow Enhancements     done
Epic 1: Persistent Sessions            done
Epic 2: Persistent Memory (OMEGA)      done
Epic 3: Always-On Director (Hermes)    next
Epic 4: One-Command Deployment         backlog
Epic 5: LLM Wiki + Obsidian            new
Epic 6: MemPalace — Deep Memory        new
Epic 7: Knowledge Ingestion Pipelines  new
```

---

## Checklist Section 3: Artifact Conflict and Impact Analysis

### 3.1 PRD Conflicts
[!] Action-needed

The PRD needs updates in three areas:

**A. Scope section**

Move from "Out of scope" to Phase 2 "In Scope":
- ~~Information source integrations (Slack, email, Granola MCPs)~~ → Knowledge ingestion pipelines: Linear MCP (ticket triage), Granola MCP (meeting notes), Azure DevOps MCP (work items)
- ~~Memory curation beyond OMEGA's built-in dedup/TTL~~ → Query hierarchy: LLM Wiki (fast) → MemPalace (deep) → OMEGA (cross-project)
- ~~Obsidian integration~~ → Per-container Obsidian vault, laptop meta-vault, git sync, Dataview dashboards

Add to Phase 2 scope:
- LLM Wiki pattern for synthesized knowledge (Obsidian-native wiki maintained by Hermes)
- MemPalace for deep verbatim memory with semantic search (19 MCP tools)

**B. Functional Requirements — Add FR53-FR62:**

| FR | Description | Epic |
|----|-------------|------|
| FR53 | Hermes can maintain a structured LLM Wiki (markdown pages, index, cross-references) per project | Epic 5 |
| FR54 | User can browse project knowledge via Obsidian vault synced from container | Epic 5 |
| FR55 | Hermes can ingest web articles into LLM Wiki via BMAD research skill | Epic 5 |
| FR56 | Hermes can perform periodic wiki lint (contradictions, orphans, stale claims) | Epic 5 |
| FR57 | MemPalace installed with MCP server providing verbatim conversation storage and semantic search | Epic 6 |
| FR58 | MemPalace knowledge graph stores temporal entity-relationship facts per project | Epic 6 |
| FR59 | Hermes queries wiki first, falls back to MemPalace for deep search (query hierarchy) | Epic 6 |
| FR60 | Hermes polls Linear MCP for new tickets, classifies type, and routes to appropriate BMAD skill | Epic 7 |
| FR61 | Hermes polls Granola MCP for new meetings and ingests notes into LLM Wiki | Epic 7 |
| FR62 | Hermes connects to Azure DevOps MCP for work item and PR context (conditional, per project) | Epic 7 |

**C. Success Criteria — Add Phase 2 metrics:**

- LLM Wiki contains 50+ pages after 1 month of usage, with working cross-references
- MemPalace recall rate >90% on project-specific queries
- Linear ticket triage runs autonomously with <5 min latency
- Granola meeting notes ingested within 30 min of meeting end
- Obsidian vault on laptop shows updated wiki pages within 5 min of container change

### 3.2 Architecture Conflicts
[!] Action-needed

**A. Technical Stack table — Add:**

| Layer | Technology | Version | Convention |
|-------|-----------|---------|------------|
| Knowledge Wiki | LLM Wiki (markdown) | N/A (pattern) | Per-container Obsidian vault, git-synced |
| Deep Memory | MemPalace | Pinned | ChromaDB + SQLite KG, MCP server |
| Knowledge Viewer | Obsidian | Latest | Per-project vault on laptop, Obsidian Git plugin |
| Ticket Management | Linear MCP | Official | Hermes MCP client, cron polling |
| Meeting Notes | Granola MCP | Native | Hermes MCP client, cron polling |
| Work Items | Azure DevOps MCP | Microsoft official | Conditional per project |

**B. Cross-Cutting Concerns — Add:**

| Concern | Affected Components | Approach |
|---------|-------------------|----------|
| Multi-vault sync | Obsidian, git, Hermes cron | One repo per vault, container auto-push, laptop auto-pull |
| Query hierarchy | LLM Wiki, MemPalace, OMEGA | Wiki (fast) → MemPalace (deep) → OMEGA (cross-project) |
| Shared user model | Hermes instances across containers | Honcho memory provider (cloud) or OMEGA profile (self-hosted) |
| MCP client fan-out | Hermes connecting to 4+ MCP servers | Per-container config.yaml, conditional wiring per project |

**C. Deferred Decisions — Move to Planned:**
- ~~Cross-project OMEGA instance (Phase 2)~~ → Shared Omega MCP endpoint across containers
- New deferred: "MemPalace federation across containers" (if needed later)

### 3.3 UI/UX Specifications
[N/A] Skip — Infrastructure project.

### 3.4 Other Artifacts
[!] Action-needed

| Artifact | Impact |
|----------|--------|
| **Ansible roles** | 2 new roles: `ai-dev-wiki` (wiki structure, git config, Hermes skills), `ai-dev-mempalace` (MemPalace install, MCP server, palace init) |
| **Epic 4 playbook** | Must be extensible to include new roles (parameterized, not hardcoded) |
| **Hermes skills** | 6+ new skills: wiki-ingest, wiki-query, wiki-lint, article-ingest, ticket-triage, meeting-ingest |
| **Hermes cron** | 4 new cron jobs: Linear poll (5 min), Granola poll (30 min), wiki lint (weekly), git auto-push (5 min) |
| **Container resources** | MemPalace adds ChromaDB (~200MB RAM). Total stack must stay <2GB. Needs validation. |

---

## Checklist Section 4: Path Forward Evaluation

### 4.1 Option 1: Direct Adjustment
[x] Viable — **Recommended**

Add Epics 5-7 to the existing plan. No modification to Epics 0-4. The existing epics are foundational — the new epics build on top.

- **Effort:** Medium — 3 new epics with ~22 stories total
- **Risk:** Low — no existing work is affected; new epics are additive
- **Timeline:** Extends project by 3 epics (estimated 3-6 weeks depending on pace)

### 4.2 Option 2: Potential Rollback
[x] Not viable — No completed work needs rollback. This is scope expansion, not correction.

### 4.3 Option 3: PRD MVP Review
[x] Not viable (not needed) — MVP (Phase 1, Epics 0-4) remains unchanged. New epics are Phase 2.

### 4.4 Selected Approach: Direct Adjustment

**Rationale:**
- Existing Epics 0-4 are unaffected — zero disruption to current sprint
- The PRD already envisioned Phase 2 with "information source integrations" and "memory curation" — this makes those vague references concrete
- New epics have clear dependencies (3 → 5 → 6 → 7) and sequence naturally
- LLM Wiki (Epic 5) has zero infrastructure cost — it's a pattern using existing tools
- MemPalace (Epic 6) is a single pip install with an Ansible role
- Ingestion pipelines (Epic 7) leverage MCP servers already available (Granola already connected)

---

## Checklist Section 5: Sprint Change Proposal

### 5.1 Issue Summary

Technical research on LLM knowledge management systems revealed three complementary tools (LLM Wiki, MemPalace, Obsidian) and three MCP-based ingestion sources (Linear, Granola, Azure DevOps) that concretize the project's Phase 2 vision. The change adds 3 new epics (5-7) with ~22 stories, extending project scope without modifying any existing epics.

### 5.2 Impact Analysis

- **Epic Impact:** Epics 0-4 unchanged. Three new epics (5-7) added as Phase 2.
- **Story Impact:** No current or future stories modified. ~22 new stories created.
- **Artifact Conflicts:** PRD (scope + 10 new FRs + success criteria), Architecture (6 stack entries + 4 cross-cutting concerns), Product Brief (move Obsidian from out-of-scope), epics.md (3 new epics), sprint-status.yaml (3 new epic entries).
- **Technical Impact:** 2 new Ansible roles, 6+ Hermes skills, 4 cron jobs, ~200MB additional RAM from MemPalace ChromaDB.

### 5.3 Recommended Approach

**Direct Adjustment** — Add Epics 5-7 as Phase 2 scope. No changes to Phase 1 (Epics 0-4).

### 5.4 Detailed Change Proposals

**See Section 3 above** for specific old → new changes to each artifact.

### 5.5 Implementation Handoff

**Scope classification: Moderate** — Backlog reorganization needed.

| Role | Responsibility |
|------|---------------|
| **Product Manager (John)** | Update PRD: move items from out-of-scope to Phase 2, add FR53-FR62, add Phase 2 success criteria |
| **Architect (Winston)** | Update architecture: add stack entries, cross-cutting concerns, planned decisions |
| **Scrum Master (Bob)** | Update epics.md with Epic 5-7 story breakdowns. Update sprint-status.yaml. |
| **Bob (SM)** | Proceed with Epic 3 sprint planning as next — no delay from this change. |

---

## Checklist Section 6: Final Review

### 6.1 Checklist Completion
[x] Done — All applicable sections addressed.

### 6.2 Proposal Accuracy
[x] Done — All recommendations supported by research report (14 verified sources).

### 6.3 User Approval
[x] Done — Approved by tomamourette on 2026-04-11.

### 6.4 Sprint Status Update
[x] Done — Added epic-5, epic-6, epic-7 to sprint-status.yaml as backlog (2026-04-11).

### 6.5 Handoff Confirmation
[x] Done — Handoff plan confirmed. Next steps:
- PM (John): Update PRD with FR53-62 and Phase 2 scope changes
- Architect (Winston): Update architecture with new stack entries and cross-cutting concerns
- SM (Bob): Proceed with Epic 3 sprint planning as next epic. Create Epic 5-7 story breakdowns when those epics become active.

---

## What Does NOT Change

- Epic 0 (done), Epic 1 (done), Epic 2 (done) — no modifications
- Epic 3 (next) — proceeds exactly as planned
- Epic 4 (backlog) — proceeds as planned, may be extended later to include new roles
- MVP definition — unchanged, Phase 1 remains Epics 0-4
- Current sprint cadence — no interruption

---

## New Epics Summary

### Epic 5: LLM Wiki + Obsidian Integration (8 stories)

Developer has a structured, LLM-maintained knowledge wiki per project that compounds understanding over time, browsable via Obsidian on the laptop with live git sync.

| Story | Description | FRs |
|-------|-------------|-----|
| 5.1 | Create LLM Wiki directory structure and SCHEMA.md per project | FR53 |
| 5.2 | Build wiki-ingest Hermes skill (create pages, update index, cross-link) | FR53 |
| 5.3 | Build wiki-query Hermes skill (search pages, synthesize answers) | FR53 |
| 5.4 | Build wiki-lint Hermes skill (contradictions, orphans, stale claims) | FR56 |
| 5.5 | Configure Obsidian vault per container with git auto-push | FR54 |
| 5.6 | Set up laptop meta-vault with Obsidian Git, Dataview dashboards | FR54 |
| 5.7 | Build article-ingest skill (URL → BMAD research → wiki) | FR55 |
| 5.8 | Wire Hermes cron for wiki lint and git push | FR56 |

### Epic 6: MemPalace — Deep Memory (6 stories)

Developer has deep verbatim memory with semantic search and a temporal knowledge graph per project, with a query hierarchy that checks the wiki first and falls back to MemPalace for raw context.

| Story | Description | FRs |
|-------|-------------|-----|
| 6.1 | Install MemPalace and configure MCP server per container | FR57 |
| 6.2 | Initialize palace wings per project with room taxonomy | FR58 |
| 6.3 | Mine existing conversation history (Claude, Slack exports) | FR57 |
| 6.4 | Wire Hermes MemPalace skill (search, diary write, KG query) | FR57, FR58 |
| 6.5 | Implement query hierarchy: wiki first → MemPalace fallback | FR59 |
| 6.6 | Create MemPalace Ansible role for one-command deployment | FR57 |

### Epic 7: Knowledge Ingestion Pipelines (8 stories)

Developer has automated ingestion pipelines that pull tickets from Linear, meeting notes from Granola, and work items from Azure DevOps into the knowledge system, with intelligent classification and routing to appropriate BMAD skills.

| Story | Description | FRs |
|-------|-------------|-----|
| 7.1 | Connect Hermes to Linear MCP, build ticket-triage skill | FR60 |
| 7.2 | Connect Hermes to Granola MCP, build meeting-ingest skill | FR61 |
| 7.3 | Connect Hermes to Azure DevOps MCP (conditional, per project) | FR62 |
| 7.4 | Build classification router (bug/feature/idea/suggestion) | FR60 |
| 7.5 | Wire BMAD skill delegation per ticket type | FR60 |
| 7.6 | Set up Hermes cron polling for Linear (5 min) and Granola (30 min) | FR60, FR61 |
| 7.7 | Configure Slack gateway for manual URL ingestion | FR55 |
| 7.8 | End-to-end integration test: ticket → triage → action → wiki → Obsidian | FR60, FR61, FR54 |
