---
type: product-brief
product: context-stack
date: 2026-04-25
author: tomamourette (via BMAD director Claude)
status: draft-v1
working_title: true
inputs:
  - homelab-playbook/_bmad-output/planning-artifacts/research/technical-graphify-evaluation-2026-04-25.md
  - homelab-playbook/_bmad-output/planning-artifacts/research/technical-memory-systems-evaluation-2026-04-25.md
  - homelab-playbook/_bmad-output/planning-artifacts/research/graphiti-claude-code-install-plan-2026-04-25.md
  - /home/developer/.claude/projects/-home-developer-workspace-homelab/memory/MEMORY.md (auto-memory)
  - project_ai_dev_container.md (Epic 6 supersession)
  - project_hybrid_gemma_serving.md (Phase 4 LiteLLM bridge)
  - project_phone_notifications_tailscale.md (network defaults)
---

# Context Stack — Product Brief

> **Working title.** "Context Stack" is the placeholder name used through this brief and may be revised before PRD. Naming finalisation is an explicit open question in §10.

## 1. Vision

A coherent, privacy-first AI-context stack for Claude Code that replaces the dormant memory tooling currently installed (MemPalace, OMEGA) with a smaller set of better-supported, MCP-native components — code-graph, conversational memory, pre-synthesised knowledge — plus a bridge to the operator's local-LLM substrate.

The stack is not a new platform. It is a deliberate consolidation of three context tiers behind Claude Code, each chosen because it survives a 12-month maintenance test and because it composes cleanly with the others rather than competing for the same role.

## 2. Problem Statement

Claude Code is the operator's daily AI assistant, and the only memory layer currently doing useful work is Claude Code's built-in auto-memory. Around it, three context tools have accumulated and decayed:

- **OMEGA** is technically running but materially dormant: nine memories captured in eighteen days, vector search broken (sqlite-vec not loaded), MCP tools not surfaced to Claude Code, and a query hit rate of 1-of-8 on real sessions. The protocol contract (`omega_welcome` → `omega_protocol`) imposes session-start cost without paying it back.
- **MemPalace** is empty. The local SQLite has zero tables and zero rows. The only deployment target was `ct-dev-test`, which has been retired. The Hermes WhatsApp auto-responder briefly wired three skills against it; those skills are unused.
- **Hermes wiring** is partial — `wire-mempalace.yml`, `mempalace-kg-query`, `mempalace-diary`, `mempalace-search`, `knowledge-query` (degenerated orchestrator), `wire-mempalace.yml`, plus conditional blocks across Hermes' `config.yaml.j2`, `defaults/main.yml`, and `verify.yml` — all reference dead infrastructure.

The cost of doing nothing is concrete: every Claude Code session re-reads the same files, re-derives the same architecture decisions, and burns tokens it should not need to. Lessons captured during one session do not surface in the next. The "compound learning" promise of the AI Dev Container Epic 6 (MemPalace) has not materialised, and continuing to maintain dormant tools competes with the maintenance budget for tools that would.

## 3. Target Users and Personas

**Single user: tomamourette.**

| Attribute | Value |
|---|---|
| Role | Solo homelab operator + consulting developer |
| Stack expertise | Deep Proxmox, Terraform, Ansible; PVE 9.x cluster of three nodes (pve1/pve2/pve3) |
| AI workflow | Claude Code as daily driver; BMAD-style story-driven development |
| Repo topology | Parent folder `homelab/` containing three sibling repos (`homelab/`, `homelab-bootstrap/`, `homelab-playbook/`) plus several project containers (Sparkle-CPS, quant-trading, ai-dev-container, Hermes) |
| Deployment posture | Privacy- and cost-conscious; prefers local-first; Tailscale-only for phone-facing services |
| Team size | One. No multi-user, no RBAC, no shared-tenant concerns. |
| Constraint sensitivity | High on maintenance budget, moderate on dollar cost, low on hardware footprint |

**Non-personas (explicit).** No customer-facing users. No team collaborators. No cross-tenant clients. The product solves a single-operator problem and design choices that benefit multi-tenant scenarios are out of scope.

## 4. Goals and Non-Goals

This is the most consequential section of the brief. Anything not listed here is not in scope for the Context Stack product.

### 4.1 In scope

| # | In-scope item | Phase |
|---|---|---|
| G1 | Decommission MemPalace end-to-end (workstation files, Ansible role, Hermes skills, wiring playbook, config conditionals, degenerated orchestrator skill) | Phase 1 |
| G2 | Decommission OMEGA end-to-end (Claude Code hooks, settings.json entries, Ansible role, group_vars, Python package) | Phase 1 |
| G3 | Introduce Graphiti as the conversational/temporal memory layer via MCP, FalkorDB backend, on `ct-ai-01` | Phase 2 |
| G4 | Introduce GitNexus as the code-graph layer (MCP-native, AST-first, PreToolUse/PostToolUse hooks, auto-reindex on commit) on the workstation | Phase 2 |
| G5 | Establish the LLM Wiki tier — file-based pre-synthesised structured knowledge — and a `wiki-query` skill replacing the deleted `knowledge-query` orchestrator | Phase 3 |
| G6 | Bridge Graphiti's LLM and (where useful) GitNexus's LLM calls to the operator's `hybrid_gemma_serving` LiteLLM gateway, with a validation gate on extraction-JSON quality | Phase 4 (stretch) |
| G7 | Document a unified query hierarchy (Wiki → Graphiti → code-graph → auto-memory) so Claude Code knows which tier to consult first | Phase 2/3 |
| G8 | Validate end-to-end deploy on `ct-dev-homelab` with a documented rollback path | Phase 2 |

### 4.2 Out of scope

| # | Out-of-scope item | Why |
|---|---|---|
| NG1 | Any customer-facing or production multi-tenant deployment | Single-operator product |
| NG2 | Any rewrite of Claude Code itself | Wrong layer |
| NG3 | Memory layers for the Hermes WhatsApp auto-responder | Hermes' memory needs are separate; `ct-dev-test` is retired |
| NG4 | LLM Wiki content authorship at scale | We deliver the *tier mechanism*; content is curated by the operator over time |
| NG5 | Graphiti-on-local-LLM as a Phase 1 default | Maintainer caveat: small local models produce malformed extraction JSON; Phase 4 only, behind validation gate |
| NG6 | Replacing Claude Code auto-memory | Auto-memory is the only memory tier currently working; Context Stack augments, does not replace |
| NG7 | Multi-user / RBAC / per-namespace isolation | Single-operator |
| NG8 | A new graph database deployment beyond FalkorDB | One graph DB only; no Neo4j/Kuzu/Neptune |
| NG9 | Visual UI / dashboard for the stack | Out of scope for Phase 1–4; CLI + MCP only |
| NG10 | Migrating any data from the dormant MemPalace or OMEGA stores | Both are empty/near-empty; not worth a migration story |

### 4.3 Phasing summary

| Phase | Outcome | Gate to next phase |
|---|---|---|
| 1. Decommission | MemPalace + OMEGA fully removed, baseline measured | Confirmed-clean state on workstation, dev_hosts container, Hermes config |
| 2. Adopt Graphiti + GitNexus | Both running, MCP-wired, hooks active, dev_homelab validated | KPI scorecard ≥ 4-of-6 green at week 4 |
| 3. LLM Wiki tier | `wiki-query` skill live, query-hierarchy doc published | First three wiki entries authored and consumed by ≥ 3 Claude Code sessions |
| 4. LiteLLM bridge (stretch) | Graphiti's LLM call routed via `hybrid_gemma_serving` for at least the small-model path | Extraction-JSON quality ≥ 95% well-formed on a 50-fact validation set |

## 5. Key Constraints

| Constraint | Target |
|---|---|
| Privacy | Source code never leaves the machine for code-parsing passes (GitNexus is local-only by design) |
| Spend | < $20 / month total Anthropic + OpenAI spend on the stack at steady state |
| Latency | Claude Code session-start overhead < 1 s introduced by the stack |
| Footprint | FalkorDB < 200 MB resident; GitNexus daemon < 500 MB resident |
| Single-operator | No multi-user, no RBAC, no shared tenancy assumed |
| Reversibility | Each component must be unwireable in < 1 day if it disappoints |
| Network | Phone-facing surfaces (if any) reachable only via Tailscale, per existing pattern |

## 6. Success Criteria

The KPI scorecard below is the steady-state measure. Phase 2 exit requires **≥ 4 of 6 green** at week 4 of usage.

| # | KPI | Green threshold | Calibration source |
|---|---|---|---|
| K1 | Token reduction on real medium-size repos | ≥ 5× | Calibrated against code-review-graph's 6.8× and Next.js 6.0× benchmarks; explicitly NOT graphify's 71.5× claim (corpus-specific, see §12) |
| K2 | Re-index time on `homelab/` parent | ≤ 60 s on full reindex, ≤ 5 s on incremental | GitNexus benchmarks |
| K3 | Steady-state monthly spend | < $20 | OpenAI billing + Anthropic usage export |
| K4 | Non-blank artifacts (Graphiti facts captured / week) | ≥ 25 distinct facts/week after week 2 | Graphiti `group_id` query |
| K5 | Good-catch rate (Graphiti hits useful prior decision in conversation) | ≥ 50% on first-shot recall queries by week 4 | Operator-tagged queries in `tom-personal` group |
| K6 | Agentic uplift (subjective: "did the stack save me a re-read?") | Yes on ≥ 60% of sessions where the stack was queried | Weekly retro note |

**Hard gates (separate from KPI scorecard):**

- **G-Latency.** Zero observable Claude Code latency regression at session start. Measured against a 5-session pre-deploy baseline. A regression here fails Phase 2 outright.
- **G-Rollback.** End-to-end rollback to pre-Context-Stack state validated on `ct-dev-homelab` by end of Sprint 4. If rollback is not validated, the stack does not promote off `ct-dev-homelab`.

## 7. Decommission Targets

This section is intentionally explicit so the Phase 1 epic has unambiguous deliverables. The decommission policy below is **confirmed**, not under debate.

### 7.1 MemPalace — REMOVE

| Target | Action |
|---|---|
| Workstation store | Delete `~/.mempalace/` |
| Ansible role | Delete `ai-dev-mempalace` role |
| Hermes skills | Delete `mempalace-kg-query`, `mempalace-diary`, `mempalace-search` |
| Wiring playbook | Delete `wire-mempalace.yml` |
| Hermes config | Edit `config.yaml.j2`, `defaults/main.yml`, `verify.yml` to remove all mempalace conditionals |
| Orchestrator skill | Delete `knowledge-query` (degenerated; will be re-introduced as `wiki-query` in Phase 3) |

### 7.2 OMEGA — REMOVE

| Target | Action |
|---|---|
| Claude Code hooks | Disable the four omega entries in `~/.claude/settings.json` |
| Settings cleanup | Remove the four omega entries entirely once disablement is verified |
| Ansible role | Remove `ai-dev-omega-memory` |
| Group vars | Remove omega-memory group_vars from the dev_hosts container playbook |
| Python package | Uninstall `omega-memory` |

### 7.3 Migration

No data migration. Both stores are empty or near-empty (MemPalace: 0 rows; OMEGA: 9 memories with broken vector search). The auto-memory file at `/home/developer/.claude/projects/.../memory/MEMORY.md` continues to be the ground-truth thread of project state across sessions and is unaffected by decommission.

## 8. Adoption Targets

### 8.1 Graphiti

| Property | Value |
|---|---|
| Backend | FalkorDB (default; ~200 MB RAM at this data scale; ~1 ms startup) |
| Phase 1 LLM | `gpt-4o-mini` (cloud) |
| Phase 4 LLM | LiteLLM-bridged local model via `hybrid_gemma_serving` |
| Embeddings | OpenAI `text-embedding-3-small` (kept on cloud per maintainer caveat about small-model JSON quality) |
| Transport | MCP HTTP (stdio not viable for remote container) |
| Group ID | `tom-personal` |
| Network | Bind `127.0.0.1`, reach via Tailscale tailnet (matches existing phone-notifications pattern) |
| Reference plan | `graphiti-claude-code-install-plan-2026-04-25.md` |

### 8.2 GitNexus

| Property | Value |
|---|---|
| Install location | Workstation (local-only — source code does not leave machine) |
| Transport | MCP server, stdio |
| Hooks | PreToolUse + PostToolUse on Claude Code |
| Trigger | Auto-reindex on commit |
| Topology | Designed for a parent-folder-with-sub-repos layout (matches `homelab/` exactly) |
| Footprint | < 500 MB daemon |

### 8.3 LLM Wiki

| Property | Value |
|---|---|
| Storage | Files (markdown), in a designated tree under the homelab repo |
| Skill | New `wiki-query` skill, designed in the Architecture phase |
| Tier in query hierarchy | Tier 1 (fastest, zero-MCP) |
| Authorship | Human-curated; tooling provides the *mechanism*, not bulk content |
| Replaces | The deleted `knowledge-query` orchestrator |

### 8.4 LiteLLM bridge (Phase 4 stretch)

| Property | Value |
|---|---|
| Target gateway | `hybrid_gemma_serving` (separate epic) |
| Scope | Graphiti LLM and small-model paths; potentially GitNexus calls if it benefits |
| Validation gate | Extraction-JSON well-formedness ≥ 95% on a 50-fact validation set |
| Failure mode | Auto-fallback to cloud `gpt-4o-mini` if local model produces malformed JSON above threshold |

## 9. Strategic Alignment

| Project | Relationship | Reference |
|---|---|---|
| Auto-memory (`MEMORY.md`) | Augmented, not replaced. Auto-memory remains the canonical project-state log. | `/home/developer/.claude/projects/-home-developer-workspace-homelab/memory/MEMORY.md` |
| AI Dev Container Epic 6 (MemPalace) | **Superseded.** Context Stack consumes that epic's intent (a memory layer that compounds learning) and decommissions its tooling. Epic 6 is closed-by-supersession. | `project_ai_dev_container.md` |
| Hybrid Gemma Serving | **Future integration target.** Phase 4 LiteLLM bridge depends on this epic's gateway being available. Context Stack does not block on Hybrid Gemma; Phase 1–3 ship without it. | `project_hybrid_gemma_serving.md` |
| Phone Notifications via Tailscale | **Network default.** Any phone-facing component (none in scope today, but option preserved) inherits the Tailscale-only posture. | `project_phone_notifications_tailscale.md` |
| Hermes WhatsApp auto-responder | **Decoupled.** Hermes' memory needs are out of scope; this product only removes its dead mempalace wiring. | (covered in §7) |

## 10. Risks and Open Questions

### 10.1 Risks

| ID | Risk | Severity | Mitigation |
|---|---|---|---|
| R1 | **GitNexus is a young, single-maintainer project; abandonment risk is real.** | High | Graph artifacts are portable; documented exit ramp to CodeGraphContext (Neo4j-backed, also MCP) or graphify (different licence assumptions) at Phase 2 retro |
| R2 | **Graphiti's bi-temporal value depends on sustained use (≥ 1 month) before it pays off.** Operator may judge it on early-week signal and discard prematurely. | Medium | KPI scorecard locked to week 4 measurement; do not promote/demote before |
| R3 | **LiteLLM bridge to local LLM is unproven for Graphiti's extraction-JSON quality.** Maintainer flagged that small local models produce malformed JSON. | Medium | Phase 4 is stretch + gated; Phase 1–3 use cloud `gpt-4o-mini`; validation gate is hard requirement before promotion |
| R4 | **MCP-vs-skill ecosystem trajectory** — graphify's lesson is that skill-first bets age fast as MCP standardises. | Medium | Both adoption targets (Graphiti, GitNexus) are MCP-native; LLM Wiki skill is the only skill-tier bet, and it's intentionally thin |
| R5 | **OpenAI dependency** for Graphiti embeddings keeps a cloud line in a privacy-first product. | Low | Embedding-only call; no source code crosses the boundary; flagged for Phase 4 review when local-embedding quality improves |
| R6 | **Spend creep** if Graphiti ingestion becomes chatty (LLM-extraction per fact). | Medium | $20/month KPI + per-week spend check; `SEMAPHORE_LIMIT=5` on Graphiti container caps concurrent LLM calls |
| R7 | **Decommission breakage** — the Hermes config edits are wide-surface and could break unrelated paths. | Medium | Phase 1 includes a Hermes verify run before Phase 2 begins |

### 10.2 Open questions

| ID | Question | Owner | Resolved by |
|---|---|---|---|
| Q1 | Final product name. "Context Stack" is a working title. | Operator | Before PRD |
| Q2 | LLM Wiki directory location and file layout — is it inside `homelab-playbook/` or its own tree? | Architecture phase | Phase 3 architecture |
| Q3 | Does GitNexus auto-reindex run on every commit, or only on commits to specific branches/paths? | Architecture phase | Phase 2 architecture |
| Q4 | Should the LiteLLM bridge include GitNexus calls or only Graphiti? GitNexus's local-only stance may make this redundant. | Phase 4 spike | Pre-Phase-4 |
| Q5 | Graphiti backup policy — `zfs send` of `/srv/graphiti/data` cadence and retention. | Architecture phase | Phase 2 architecture |

## 11. Glossary

| Term | Definition |
|---|---|
| **MCP** | Model Context Protocol. Anthropic-led open protocol for exposing tools/resources/prompts to LLM clients (Claude Code, Cursor, etc.). MCP-native components are first-class citizens for Claude Code; skill-tier components are bespoke wrappers. |
| **AST** | Abstract Syntax Tree. Deterministic parse tree of source code, used here as the primary input for code-graph construction. AST-first means the graph structure is derived from code parsing, not LLM extraction. |
| **Leiden** | Graph community-detection algorithm (Traag et al., 2019), successor to Louvain. Used by Microsoft GraphRAG and graphify to cluster nodes into communities; topology-based, embedding-free. |
| **bi-temporal** | A fact-modelling pattern where each fact carries two time dimensions: when it was *true* in the world (valid time) and when it was *recorded* in the system (transaction time). Graphiti's headline differentiator. Enables queries like "what did the system believe was true on date X?" |
| **GraphRAG** | Family of retrieval-augmented-generation systems that index a corpus into a knowledge graph and retrieve via graph traversal + community summaries instead of, or in addition to, vector similarity. Microsoft GraphRAG (Feb 2024) was the canonical reference; the family now spans LightRAG, nano-graphrag, FalkorDB CodeGraph, code-review-graph, GitNexus, graphify. |
| **FalkorDB** | Redis-module graph database (fork of RedisGraph). The default Graphiti backend. ~200 MB RAM at this data scale, ~1 ms startup, OpenCypher query language. |
| **LiteLLM** | Open-source LLM-gateway proxy that exposes a uniform OpenAI-compatible API in front of arbitrary providers (Ollama, vLLM, OpenAI, Anthropic, Bedrock, etc.). Used here as the substrate for the Hybrid Gemma Serving epic and the Phase 4 routing target. |
| **Wing / Room / Hall** | Legacy MemPalace structural metaphor (a memory store organised into "wings" and "rooms"). Acknowledged here for completeness because it appears in soon-to-be-deleted Hermes skill names; not adopted in the new stack. |

## 12. References

### 12.1 Source research artifacts (authoritative for this brief)

- `homelab-playbook/_bmad-output/planning-artifacts/research/technical-graphify-evaluation-2026-04-25.md` — landscape evaluation of graphify and the broader code-graph / GraphRAG family. **Source of the K1 calibration:** "graphify's headline 71.5× claim is corpus-specific; expect ~5–10× on real medium-size repos, with code-review-graph's 6.8× / 6.0× third-party numbers as the calibration anchor." Headline finding: AST-first code-graph is validated by independent academic work (arxiv:2601.08773); MCP-first trajectory matters.
- `homelab-playbook/_bmad-output/planning-artifacts/research/technical-memory-systems-evaluation-2026-04-25.md` — landscape evaluation of agent / conversational memory systems (Mem0, Graphiti, Letta, Honcho, OpenMemory MCP, Cognee, Letta). **Source of the Graphiti adoption choice:** "Graphiti is the strongest narrow-augmentation candidate because it offers bi-temporal validity, which OMEGA does not." Tier-1/Tier-2 split; explicit "do not adopt Mem0/Letta/Honcho/Cognee" recommendation.
- `homelab-playbook/_bmad-output/planning-artifacts/research/graphiti-claude-code-install-plan-2026-04-25.md` — shovel-ready Graphiti install plan. **Source of all §8.1 deployment specifics:** FalkorDB recipe, MCP HTTP transport choice, `127.0.0.1`-bind + Tailscale-reach pattern, `gpt-4o-mini` + `text-embedding-3-small` defaults, `SEMAPHORE_LIMIT=5`, `tom-personal` group_id.

### 12.2 Memory / project context (cited by reference, not duplicated)

- `/home/developer/.claude/projects/-home-developer-workspace-homelab/memory/MEMORY.md` — auto-memory; canonical project-state log
- `project_ai_dev_container.md` — AI Dev Container epic plan (Epic 6 superseded by this product)
- `project_hybrid_gemma_serving.md` — Phase 4 LiteLLM bridge target
- `project_phone_notifications_tailscale.md` — Tailscale-only network defaults

### 12.3 Companion product brief (predecessor)

- `homelab-playbook/_bmad-output/planning-artifacts/product-brief-ai-dev-container.md` — original brief that introduced OMEGA + MemPalace as Phase 2b knowledge management. Context Stack supersedes that Phase 2b plan.

---

**End of brief — handoff to PRD phase.**
