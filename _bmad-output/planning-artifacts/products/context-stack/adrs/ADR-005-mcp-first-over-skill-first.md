---
adr: 005
title: "MCP-first integration over skill-first (the GitNexus + Graphiti vs MemPalace lesson)"
status: accepted
date: 2026-04-25
authors: tomamourette (via BMAD director Claude)
context_question: null
---

# ADR-005: MCP-first integration over skill-first (the GitNexus + Graphiti vs MemPalace lesson)

## Context

MemPalace's failure mode was not algorithmic. The SQLite was empty (zero tables, zero rows) because no skill ever wrote to it; the three Hermes skills that wrapped it (`mempalace-kg-query`, `mempalace-diary`, `mempalace-search`) were not invoked by Claude Code in the operator's daily-driver flow. OMEGA's failure mode was adjacent: technically running, vector search broken, MCP tools not surfaced, query hit rate 1-of-8 on real sessions.

Both failures share a root cause: **the integration layer was bespoke, per-assistant, and handcrafted**. MemPalace shipped Hermes skills that Hermes (a different bot product) was supposed to call; OMEGA shipped a "protocol" that required hand-rolling `omega_welcome` / `omega_protocol` calls into every session. Neither shape is what Claude Code's underlying model is *trained to call*.

MCP changes that. MCP-native servers advertise tools through the standard manifest; the model is trained on "use tools when available." The trajectory in the 2026 GraphRAG / agent-memory category is unambiguous: MCP is winning (per `technical-graphify-evaluation-2026-04-25.md` §3 emerging-technologies and §3.2 architectural-shapes table; per `technical-memory-systems-evaluation-2026-04-25.md` recommendation table).

## Decision

**All Tier-2 and Tier-3 components in the Context Stack are MCP-native.** Specifically:
- **GitNexus** (Tier 2, code-graph) — MCP server, transport varies by delivery model (see ADR-015): **HTTP transport** when delivered via the official Docker image (current canonical install — `claude mcp add --transport http gitnexus http://127.0.0.1:4747/api/mcp`); stdio transport when delivered via npm (originally implied by ADR-004, no longer the workstation install channel after E2-S01.5 pivot).
- **Graphiti** (Tier 3, memory) — MCP server, HTTP transport, registered via `claude mcp add --transport http graphiti ...` (ADR-001 + ADR-006).

**Note on transport variance (added 2026-04-26 per ADR-015):** the MCP-native architectural commitment is independent of stdio-vs-HTTP. Both are first-class MCP transports. The choice for any given tool follows its delivery model: containerised tools naturally serve HTTP on a loopback port; npm/binary tools default to stdio. Either is acceptable so long as the server is registered through `claude mcp add` and discovered by Claude Code's standard MCP manifest mechanism.

The **only** skill-tier integration in this stack is **`wiki-query`** (Tier 1) — and that is intentionally a thin file-read skill with no daemon, no DB, no MCP wiring (ADR-006). Brief §10.1 R4 explicitly flags `wiki-query` as the only skill bet; ADR-009 designs it to be reversibly replaceable with a Wiki MCP server if MCP-side ergonomics improve.

## Consequences

**Positive.**
- Tools advertised through MCP manifests are reliably discovered and called by Claude Code's model — this is the structural fix to OMEGA's "tools not surfaced" failure mode.
- Adding a tool means writing an MCP server (well-documented standard), not bespoke skill scaffolding per assistant — applies the lesson from graphify's 15-assistant skill-fork pain.
- The ecosystem trajectory (MCP-first) means upstream tooling improvements arrive as MCP-server upgrades, not skill rewrites.

**Negative.**
- MCP servers are heavier than plain skill scripts (they're long-running processes with health concerns, not invocations).
- HTTP MCP transport (Graphiti's) means a network surface, however local; we mitigate via `127.0.0.1` bind + Tailscale boundary (FR-MEM-003).
- Dependence on Anthropic's MCP standard remaining stable — but this is a strong-trajectory bet, not a fragile experiment.

**Neutral.**
- `wiki-query` as a skill is a deliberate exception — Tier 1's value is sub-200 ms file-read with zero process overhead (NFR-PERF-003), which an MCP server would defeat. ADR-009 captures this.

## Alternatives Considered

1. **All-skill integration (a la graphify, MemPalace)** — rejected. Two failure proofs in this exact homelab.
2. **All-MCP including Wiki** — rejected. Wiki is a markdown tree; an MCP server in front of a markdown tree adds latency and process surface for no benefit. ADR-009 recommends file-read.
3. **Hybrid skill+MCP per tool** — rejected as architectural drift. We chose MCP for code-graph and memory because both tiers benefit from a long-running process (parser state for GitNexus, FalkorDB connection for Graphiti). Wiki does not.

## Validation / Exit Ramp

- **Validation:** at week 4, K6 (subjective uplift "yes" on ≥ 60% of sessions) implies the model is actually invoking GitNexus + Graphiti tools — the OMEGA failure mode would surface as low K6 + zero tool-hit logs.
- **Operational signal:** FR-OBS-006 (GitNexus tool-hit-rate logged; zero calls for one week → CLAUDE.md review).
- **Exit ramp:** if the MCP standard fragments or Anthropic deprecates current transport semantics, rebind to whatever Claude Code's then-current discovery mechanism is. The architectural decisions (FalkorDB backend, AST-first code-graph, file-based wiki) survive a transport change.

## References

- `technical-memory-systems-evaluation-2026-04-25.md` §6.1 (Graphiti MCP integration cleanliness)
- `technical-graphify-evaluation-2026-04-25.md` §3.2 (architectural shapes; MCP-first trajectory)
- Brief §10.1 R4 (MCP-vs-skill ecosystem trajectory)
- PRD FR-CG-001 (MCP-native), FR-MEM-002 (HTTP transport), FR-WIKI-003 (skill-tier exception)
