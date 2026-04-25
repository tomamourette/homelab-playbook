---
adr: 001
title: "Use FalkorDB as the Graphiti backend"
status: accepted
date: 2026-04-25
authors: tomamourette (via BMAD director Claude)
context_question: null
---

# ADR-001: Use FalkorDB as the Graphiti backend

## Context

Graphiti supports four storage backends (Neo4j 5.26+, FalkorDB 1.1.2+, Kuzu 0.11.2+, Amazon Neptune). The Context Stack needs a graph store on `ct-ai-01` that fits the homelab's constraints:

- < 200 MB resident RAM at this data scale (NFR-FOOTPRINT-001).
- Sub-second startup (the operator stops/starts containers during dev).
- A vendor-supported docker-compose recipe (avoid bespoke wiring).
- One-graph-DB-only policy (brief NG8 — no Neo4j alongside FalkorDB).
- No multi-user, no RBAC, no shared tenancy.

The graphiti-claude-code install plan already recommends FalkorDB as the default; this ADR captures *why* and what alternatives were rejected.

## Decision

Adopt **FalkorDB** (Redis-module graph database, OpenCypher) as the sole graph backend for Graphiti on `ct-ai-01`. Run it as a sidecar container next to `graphiti-mcp` per the compose recipe in `graphiti-claude-code-install-plan-2026-04-25.md` §2.3. Bind to `127.0.0.1`, reach via Tailscale tailnet (matches existing `phone-notifications-tailscale` pattern).

## Consequences

**Positive.**
- ~200 MB resident RAM, ~1 ms startup — meets NFR-FOOTPRINT-001 with margin.
- Vendor-supported compose recipe lifted directly from FalkorDB docs; lowest install drift.
- OpenCypher query surface enables the Q2 backup `MATCH (n)-[r]->(m) RETURN n,r,m` JSON dump exit ramp (NFR-PORT-002).
- Redis-module foundation gives well-understood `BGSAVE` (RDB snapshot) and `BGREWRITEAOF` (AOF rewrite) ops surfaces for backup (ADR-007).
- FalkorDB Browser UI (port 3000) is a free side-effect for visual smoke-testing — used in the install runbook step 13.

**Negative.**
- Vendor benchmarks (FalkorDB-authored) showing it beats Neo4j are directional, not gospel.
- FalkorDB has a smaller ecosystem than Neo4j (fewer plugins, no APOC, no widely-known third-party tooling).
- LadybugDB's eventual emergence in agent-memory tooling could displace this choice in 2027.

**Neutral.**
- Single-process write lock (Redis-module property) does not matter at single-operator scale.
- No replication/HA — fine for this product (NFRs do not demand it).

## Alternatives Considered

1. **Neo4j 5.26+** — rejected. ~1 GB+ RAM minimum, ~3 GB recommended, ~90 ms startup. JVM tax is large for a daily-driver homelab process. Browser UI is nicer than FalkorDB Browser but the operator does not need a UI for a single-operator product (brief NG9). Heavier ops surface (auth, plugins).
2. **Kuzu 0.11.2+** — rejected. Embedded (no daemon) is appealing for portability (`tar` the dir, take it anywhere), but it cannot serve a remote MCP HTTP transport from `ct-ai-01` without re-architecting around a library-mode wrapper. Also the youngest of the four drivers in Graphiti (Feb 2026 addition); least battle-tested.
3. **Amazon Neptune** — rejected outright. Cloud-only, monthly cost > $20 (violates NFR-COST-001), no homelab fit.

## Validation / Exit Ramp

- **Validation:** at week 4, `docker stats graphiti-falkordb` resident < 200 MB; FalkorDB Browser at `http://ct-ai-01:3000` shows the populated graph.
- **Exit ramp:** Cypher dump (`MATCH (n)-[r]->(m) RETURN n,r,m` to JSON) replayable into Neo4j or Kuzu via a one-time import script. The MCP server log (FR-OBS-003) is the secondary insurance — replay `add_episode` calls into a fresh backend.
- **Reversal trigger:** if Phase 2 KPIs come in green but FalkorDB resident exceeds 500 MB, or the FalkorDB project loses upstream activity for ≥ 3 months (NFR-SUPP-001), re-evaluate Neo4j.

## References

- `graphiti-claude-code-install-plan-2026-04-25.md` §2 (FalkorDB recipe)
- `technical-memory-systems-evaluation-2026-04-25.md` (memory-systems landscape; FalkorDB ~500 MB low-cost line)
- FalkorDB benchmark blog: <https://www.falkordb.com/blog/graph-database-performance-benchmarks-falkordb-vs-neo4j/>
- PRD FR-MEM-001, FR-MEM-015, NFR-FOOTPRINT-001
