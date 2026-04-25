---
adr: 004
title: "Adopt GitNexus as the code-graph layer (over graphify and CodeGraphContext)"
status: accepted
date: 2026-04-25
authors: tomamourette (via BMAD director Claude)
context_question: null
---

# ADR-004: Adopt GitNexus as the code-graph layer (over graphify and CodeGraphContext)

## Context

The Context Stack needs a code-graph tier that gives Claude Code structural awareness of `~/workspace/homelab/` (parent folder + three sibling repos + per-project containers). The 2026 landscape (per `technical-graphify-evaluation-2026-04-25.md`) offers three serious candidates:

| Candidate | Architecture | Integration | Reindex |
|---|---|---|---|
| graphify | Batch ETL → JSON | Skill-first, 15+ assistants | Manual (PreToolUse only) |
| GitNexus | MCP-native server (LadybugDB) | MCP-first, stdio | Auto-reindex on commit (PostToolUse) |
| CodeGraphContext | MCP server + Neo4j | MCP-first | CI-side hooks |

The director's resolved decision is GitNexus on these grounds: MCP-native, AST-first, parent-folder-with-sub-repos topology fit, PreToolUse + PostToolUse hooks, auto-reindex on every commit, < 500 MB resident, local-only privacy posture (no source code over the wire).

This ADR captures the rationale and exit ramp.

## Decision

Adopt **GitNexus** (`abhigyanpatwari/GitNexus`, npm-distributed, currently latest **v1.6.3** as of April 2026) on the workstation as the Tier-2 code-graph MCP server. Install via `npm install -g gitnexus@1.6.3` (pinned, not `@latest` per FR-DEP-010 spirit). Wire stdio transport, register PreToolUse + PostToolUse hooks. Auto-reindex on every commit, no path/branch filter (FR-CG-005). Underlying graph store is LadybugDB (native CLI mode), queryable via Cypher.

## Consequences

**Positive.**
- MCP-first matches the architectural bet of the wider Context Stack (Graphiti is MCP, Wiki is intentionally not). Skill-first tools age fast as MCP standardises (brief §10.1 R4).
- PostToolUse-on-commit auto-reindex closes graphify's biggest operational gap: no stale graph after every change.
- Local-only — `npm install -g gitnexus` runs entirely on the workstation; tree-sitter parsing happens in-process; no source code over the wire (FR-CG-002, NFR-PRIV-001).
- Native parent-folder-with-sub-repos handling, designed for exactly the `homelab/` topology.
- Cypher query interface available — same query mental model as FalkorDB (ADR-001), reduces operator cognitive load.

**Negative.**
- **Young, single-maintainer project.** Brief §10.1 R1 flags this as the highest risk in the product. Mitigation lives in NFR-SUPP-001 (≥ 3 months upstream activity gate at adoption) and the export wrapper of ADR-012 (Q8).
- npm distribution means a Node.js runtime on the workstation (already present for Claude Code; not a new dependency).
- Earlier brief draft assumed Python ("daemon < 500 MB" implied a Python process). Actual implementation is Node.js + tree-sitter + LadybugDB. Footprint ceiling stays 500 MB; verify in week 1.
- LadybugDB is a less-well-known graph store than Neo4j — exit-ramp tooling is bespoke (ADR-012).

**Neutral.**
- The `graphify` (NetworkX-on-JSON, batch) approach is genuinely interesting for *content* graphs (papers, audio, video) — but Context Stack's scope is code only.

## Alternatives Considered

1. **graphify (`pip install graphifyy`, double-y)** — rejected. Skill-first per assistant; PreToolUse only (no PostToolUse-on-commit auto-reindex); MCP support is preview-quality (issue #146 still open). Strong batch-pipeline tool for content graphs but wrong shape for live code-graph.
2. **CodeGraphContext** — rejected for *primary* code-graph; **kept as exit ramp**. Requires a Neo4j daemon (heavier — ~1 GB JVM RAM; violates the one-graph-DB-only spirit of brief NG8). Useful target if GitNexus abandonment happens.
3. **code-review-graph** — rejected. Optimized for PR review, not always-on code-graph. The 6.8× / 6.0× third-party benchmark anchor for K1 came from this tool, but for daily-driver use GitNexus is a better fit.
4. **codegraph (colbymchenry)** — rejected. Tree-sitter + JSON pre-indexed, no MCP server, no live updates; closer to graphify than GitNexus in architecture.
5. **Sourcegraph Cody** — rejected. Enterprise indexer model, remote-first, multi-tenant; wrong shape for a single-operator local-only product.
6. **Aider repo-map** — rejected. Bound to Aider; doesn't compose with Claude Code's tool surface.

## Validation / Exit Ramp

- **Validation:**
  - Week 0: confirm ≥ 3 months commit activity on `abhigyanpatwari/GitNexus` (NFR-SUPP-001).
  - Week 1: install completes; `npx gitnexus@1.6.3 setup` registers MCP; full reindex of `~/workspace/homelab/` ≤ 60 s (FR-CG-007); incremental commit reindex ≤ 30 s (FR-CG-006).
  - Week 4: K1 (token reduction) ≥ 5× on three representative cross-repo questions; K2 timings green; tool-hit-rate logged (FR-OBS-006).
- **Exit ramp (per FR-CG-010, ADR-012):** export GitNexus's LadybugDB to JSON via a wrapper script; replay into CodeGraphContext (Neo4j-backed, MCP) using a Cypher-replay script. Wrapper is part of Sprint 2 deliverable so the exit ramp is a one-day exercise, not a forking research task.
- **Reversal trigger:** GitNexus upstream activity drops below one commit/month for three consecutive months, OR a critical bug breaks reindex on the operator's repo with no maintainer response in two weeks. In either case, run the export wrapper and adopt CodeGraphContext.

## References

- `technical-graphify-evaluation-2026-04-25.md` (full landscape; GitNexus #1 GitHub trending Apr 10 2026; PostToolUse auto-reindex differentiator; MCP-first trajectory)
- GitNexus repo: <https://github.com/abhigyanpatwari/GitNexus>
- npm: <https://www.npmjs.com/package/gitnexus>
- PRD FR-CG-001 through FR-CG-012, NFR-SUPP-001, NFR-FOOTPRINT-002
- Brief §10.1 R1 (abandonment risk), §8.2 (adoption target)
