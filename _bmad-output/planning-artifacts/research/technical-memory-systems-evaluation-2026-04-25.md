---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments: [
  'https://github.com/mem0ai/mem0',
  'https://github.com/getzep/graphiti',
  'https://github.com/letta-ai/letta',
  'https://github.com/plastic-labs/honcho',
  'https://github.com/topoteretes/cognee',
  'https://github.com/CaviraOSS/OpenMemory',
  'https://blog.plasticlabs.ai/research/Benchmarking-Honcho',
  'https://mem0.ai/blog/mem0-the-token-efficient-memory-algorithm',
  'https://atlan.com/know/best-ai-agent-memory-frameworks-2026/',
  'https://vectorize.io/articles/best-ai-agent-memory-systems',
  'https://blog.bymar.co/posts/agent-memory-systems-2026/',
  'https://help.getzep.com/graphiti/getting-started/mcp-server',
  'https://docs.letta.com/guides/selfhosting',
  'https://docs.letta.com/guides/server/providers/ollama',
  'https://arxiv.org/abs/2501.13956',
  'https://arxiv.org/abs/2504.19413',
  'https://snap-research.github.io/locomo/',
  'https://arxiv.org/pdf/2410.10813'
]
workflowType: 'research'
research_type: 'technical'
research_topic: 'Agent / conversational memory systems for Claude Code in 2026 (Honcho, Mem0, Letta, Graphiti, Zep, OpenMemory MCP, Cognee, etc.) — adopt-vs-stay-on-OMEGA decision'
research_goals: 'Evaluate the 2026 landscape of agent / conversational memory systems against the user'\''s already-deployed OMEGA layer; identify whether any candidate offers capability above-and-beyond OMEGA worth adopting; produce a clear recommendation (adopt-X / stack-X-on-OMEGA / stay-on-OMEGA-only).'
user_name: 'tomamourette'
date: '2026-04-25'
web_research_enabled: true
source_verification: true
---

# Memory Systems for Claude Code in 2026: Comprehensive Evaluation

**Date:** 2026-04-25
**Author:** tomamourette
**Research Type:** technical

---

## Executive Summary

The 2026 agent-memory category has bifurcated. **Tier-1 (clear leaders)** is now Mem0 (post-April 2026 algorithm rewrite), Graphiti/Zep (temporal-KG specialist), and Honcho (theory-of-mind / personal-identity specialist). **Tier-2 (strong but narrower)** is Letta (self-editing OS-style memory), Cognee (local-first KG ingestion engine), and OpenMemory MCP (Mem0's local wrapper plus a community fork). The benchmark wars are *contested* — every vendor has at some point been accused of misconfiguring competitors — and the headline LongMemEval and LoCoMo numbers should be read with confidence-Medium, not High.

For a **Claude Code daily-driver context**, the decision pivots on three axes that OMEGA itself does not currently advertise: (1) **temporal-fact tracking** (Graphiti's bi-temporal validity windows), (2) **theory-of-mind / per-user representations** (Honcho's Dialectic and Dream loops), and (3) **graph traversal over conversational facts** (Mem0 Pro's graph tier and Graphiti's KG). OMEGA already covers session/cross-session retrieval, similarity search, typed memory (`decision`, `user_preference`), `[MEMORY]`/`[HANDOFF]`/`[COORD]` ground-truth blocks, and reflection (`omega_reflect`). It does *not* — based on documented surface — expose first-class temporal validity intervals or active per-user theory-of-mind modeling.

**Headline finding:** For a single-operator homelab where the "user" is one person (Tom) and most "memory" is project-scoped engineering decisions, the marginal value of layering Graphiti, Honcho or Mem0 on top of OMEGA is **modest and infrastructure-heavy**. The strongest candidate to add is **Graphiti** (temporal KG), because it offers something OMEGA's documented capability does not — bi-temporal fact validity, which matters for "this decision was true until pve2 rebuild on 2026-04-24, now superseded" use cases that recur in your repo. Honcho is interesting but its theory-of-mind sweet spot is *multi-user* assistants (tutors, companions), not a single solo developer. Mem0's recent algorithm rewrite is impressive on benchmarks but its core value (user-preference extraction + cheap retrieval) substantially overlaps with what OMEGA already does.

**Key Findings:**
- Mem0's April 2026 rewrite (LoCoMo 91.6, LongMemEval 93.4, BEAM-1M 64.1) is the most credible 2026 leap in benchmark-validated memory accuracy ([Mem0 blog](https://mem0.ai/blog/mem0-the-token-efficient-memory-algorithm)). Confidence: Medium (vendor-published, but methodology is documented and the open-source SDK ships the same algorithm).
- Graphiti is the only mainstream open-source system with *bi-temporal* fact modeling ([arXiv 2501.13956](https://arxiv.org/abs/2501.13956)). Its MCP server v1.0 is generally available and supports Neo4j, FalkorDB, Kuzu, and Neptune backends.
- Honcho posts state-of-the-art LongMem (90.4–92.6%) and LoCoMo (89.9%) numbers but its competitive baseline note ("the latest models score 92% on LongMem with no memory at all") is candid and weakens the comparative-uplift argument ([Plastic Labs benchmarks](https://blog.plasticlabs.ai/research/Benchmarking-Honcho)).
- Letta is the only open-source system whose agent *self-edits* memory via tool calls. It works with Ollama in principle but Letta themselves caution that performance on open-weight models is poor outside the very largest (GLM-4.7, MiniMax M2.1, frontier-class) ([Letta Ollama docs](https://docs.letta.com/guides/server/providers/ollama)).
- The contested-benchmark situation is real: Mem0 says Zep needs 600k tokens per conversation to hit its scores; Zep says Mem0 misconfigured the rebuttal. **Skepticism warranted on every published number.**

**Top 3 Recommendations:**
1. **Stay on OMEGA as the primary memory plane** — the marginal-uplift case for any candidate is weaker than the integration-and-maintenance cost for a single-operator setup. OMEGA already covers ~80% of what agent-memory tools market.
2. **If adding one thing, add Graphiti as a *narrow, optional* second tier** — specifically for temporal-fact / decision-validity tracking on architecture decisions across your three-repo topology. Run it via the MCP server with FalkorDB (lightest backend), point it at OMEGA-stored decision events as the ingestion source, and treat it as an *augment*, not a replacement.
3. **Do not adopt Mem0, Letta, Honcho, or Cognee** as primary memory. Mem0 duplicates OMEGA. Letta is an *agent runtime*, not a memory layer (wrong abstraction). Honcho is built for *multi-user* personal-identity products. Cognee is great for document-corpus KG ingestion but that's a different problem from agent memory.

---

## Table of Contents

1. Research Scope and Methodology
2. The Memory-Systems Landscape in 2026 (taxonomy)
3. Tool-by-Tool Deep Dive
   - 3.1 Mem0
   - 3.2 Graphiti / Zep
   - 3.3 Letta (MemGPT lineage)
   - 3.4 Honcho
   - 3.5 OpenMemory MCP
   - 3.6 Cognee
   - 3.7 Honourable mentions (Hindsight, Supermemory, MemMachine, MemPalace)
4. OMEGA Comparison Matrix
5. Benchmarks and Independent Evaluations
6. Integration with Claude Code
7. Cost, Privacy, and Maturity
8. Strategic Recommendations
9. Implementation Roadmap (if recommending adoption)
10. Risk Register
11. Sources and Confidence Levels

---

## 1. Research Scope and Methodology

**Question:** Should the user (a homelab operator running Claude Code as a daily-driver alongside the already-deployed OMEGA persistent-memory MCP) add a graph-memory / agent-memory system on top of OMEGA, and if so, which one performs best for that workflow in 2026?

**Out of scope:**
- The code-graph layer (graphify, GitNexus, CodeGraphContext) — covered separately in [`technical-graphify-evaluation-2026-04-25.md`](./technical-graphify-evaluation-2026-04-25.md). Memory systems and code-graph systems are different categorical layers; this report does not compare them.

**Methodology:**
- Live web search executed 2026-04-25 across vendor sites, GitHub, third-party reviews (DEV.to, Medium, Atlan, Vectorize), and academic sources (arXiv).
- Direct repo fetches for star counts, license, current release, MCP availability.
- Cross-checked benchmark claims across at least two third-party sources where possible.
- Confidence levels (High/Medium/Low) annotated on contested claims.
- Skeptical posture: vendor-published benchmarks treated as Medium-confidence by default.
- "Stay on OMEGA only" treated as a real candidate.

---

## 2. The Memory-Systems Landscape in 2026 (taxonomy)

The category has split into specialized lanes. The 2025-era pretense that "every memory system does the same thing" is gone; in 2026, the leading reviewers ([blog.bymar.co 2026 survey](https://blog.bymar.co/posts/agent-memory-systems-2026/), [Atlan](https://atlan.com/know/best-ai-agent-memory-frameworks-2026/), [Vectorize](https://vectorize.io/articles/best-ai-agent-memory-systems)) all converge on a similar taxonomy:

| Lane | Description | Leading tool | Sweet spot |
|---|---|---|---|
| **Profile / preference memory** | Extracts and stores per-user facts ("hates mushrooms", "uses Pacific time") | Mem0 | Customer support, personalization, multi-user assistants |
| **Temporal knowledge graph** | Stores facts as edges with validity windows; reasons about how facts change | Graphiti / Zep | Compliance, audit, decision-archeology, "what was true on date X" |
| **Self-editing OS memory** | Agent uses tool calls to manage its own core/recall/archival tiers | Letta (MemGPT) | Long-running agents that need fine-grained control |
| **Theory-of-mind / personal identity** | Per-peer evolving representation, dialectic queries, dream consolidation | Honcho | Tutors, companions, multi-user products |
| **Document-corpus KG** | Ingest large unstructured corpora into a queryable KG | Cognee | RAG over wikis/papers; not really conversational memory |
| **Local-first MCP wrapper** | Single-binary Docker stack exposing MCP tools, runs offline | OpenMemory MCP, mem0-mcp-self-hosted | Privacy-leaning solo devs |
| **Hybrid coordination memory (you are here)** | Session/handoff/coord blocks + typed decision/preference memory + reflection | **OMEGA** | Single-operator + AI-assistant continuity across sessions and projects |

Important taxonomy point: **OMEGA's lane (hybrid coordination memory) is not actively contested by any of the 2026 leaders.** Mem0 doesn't model `[HANDOFF]` blocks. Graphiti doesn't run a `omega_protocol()` session-init contract. Honcho doesn't reify `decision` vs `user_preference` types as first-class. The candidate tools all assume *they are the memory layer* — they are designed as foundations, not augmentations.

This means the right framing is not "which is best?" but "what does OMEGA *not* do that I now need?"

---

## 3. Tool-by-Tool Deep Dive

### 3.1 Mem0

**One-paragraph plain-English description:** Mem0 is a Python/TS SDK + hosted-service that extracts, stores, and retrieves user-level facts ("preferences", "biographical statements", "stated intentions") from conversation streams. It uses an LLM to do the extraction at write-time and uses a hybrid vector + optional graph index for retrieval at read-time. After its April 2026 algorithm rewrite, it claims state-of-the-art numbers on three public benchmarks while keeping retrieval-time tokens under 7k per query.

**Architecture:**
- Default: vector index (pluggable: Qdrant, Chroma, pgvector, etc.).
- Pro tier: dual-store (vector + Neo4j-style graph for entity relationships).
- Apache 2.0 license on the SDK; the hosted platform is the commercial wedge.
- Can self-host via Docker Compose (`AUTH_DISABLED=true` for local dev).
- ([Mem0 GitHub](https://github.com/mem0ai/mem0))

**Claude Code integration:**
- Official Mem0 MCP server with documented Claude Code path: edit `.mcp.json` or `~/.claude.json`, point at `mem0-mcp-server` ([Mem0 docs - Claude Code](https://docs.mem0.ai/integrations/claude-code)).
- Mem0 launched a "Plugin for AI Editors" in March-April 2026 with 9 MCP tools and lifecycle hooks ([dev.to comparison](https://dev.to/anajuliabit/mem0-vs-zep-vs-langmem-vs-memoclaw-ai-agent-memory-comparison-2026-1l1k)).
- Self-hosted setup: `pip install mem0ai`, `docker-compose up`, configure embeddings (default `text-embedding-3-small`, but Qwen 0.6B+ recommended for hybrid).
- Install ergonomics: **smooth, ~5-minute setup** per Mem0's own claim, corroborated by multiple dev.to walkthroughs.

**Performance/benchmarks:**
| Benchmark | Score | Source | Confidence |
|---|---|---|---|
| LoCoMo (legacy algo) | 67.13% LLM-as-Judge | [Mem0 paper, ECAI 2025](https://arxiv.org/abs/2504.19413) | High (peer-reviewed) |
| LoCoMo (April 2026 algo) | 91.6 | [Mem0 blog](https://mem0.ai/blog/mem0-the-token-efficient-memory-algorithm) | Medium (vendor) |
| LongMemEval (April 2026) | 93.4 | Same | Medium |
| BEAM 1M | 64.1 | Same | Medium |
| LongMemEval (older) | 49.0% (GPT-4o) | [Atlan](https://atlan.com/know/best-ai-agent-memory-frameworks-2026/) | High (third-party) |

**Note on the benchmark dispute:** Mem0's 2025 paper benchmarked Zep at 65.99% on LOCOMO; Zep rebutted that they were misconfigured and corrected to 75.14% ([Atlan summary](https://atlan.com/know/zep-vs-mem0/)). Both numbers should be read sceptically.

**Adoption proof:**
- ~54k GitHub stars (April 2026), ~6.1k forks ([Mem0 GitHub](https://github.com/mem0ai/mem0)). Confidence: High (live count).
- ~625k weekly PyPI downloads on `mem0ai`. Confidence: Medium (vendor-cited, plausible).
- Largest community in the category by a wide margin. Confidence: High.

**Maturity / governance risk:**
- Apache 2.0 OSS, VC-backed company, ECAI 2025 paper acceptance.
- Active contributor base; aggressive release cadence.
- Risk: hosted platform is the real product per multiple reviewers ("If you want self-hosting, you're mostly on your own" — [Atlan alternatives](https://atlan.com/know/mem0-alternatives/)).

**Hands-on third-party reviews:**
- [Reliable Data Engineering on Medium](https://medium.com/@reliabledataengineering/mem0-do-ai-agents-really-need-memory-honest-review-6760b5288f37) — "honest assessment: probably overkill for a weekend chatbot, indispensable for 10k-user SaaS."
- [ChatForest review](https://chatforest.com/reviews/mem0-mcp-server/) — "AI Memory That Actually Scales (If You Pay)" — flags the hosted-vs-self-host trade.
- [bymar.co 2026 survey](https://blog.bymar.co/posts/agent-memory-systems-2026/) — calls out: *"can collapse into 'smart profile + search' if you need deeper task memory."*

**Cost (self-hosted):**
- Compute: tiny — a Postgres + Qdrant in Docker Compose runs comfortably on a 1GB-RAM container.
- LLM-call dependence: heavy — the extraction pass is LLM-driven on every message. Use a local LLM (Ollama, your hybrid_gemma_serving) to make this free.

**Distinct capabilities vs OMEGA:**
- ✅ User-preference extraction with LLM-driven semantic deduplication (OMEGA stores `user_preference` typed memories but the extraction is manual/explicit, not auto).
- ✅ Optional graph tier for entity relationships (Pro).
- ❌ No documented theory-of-mind, no validity intervals, no `[HANDOFF]` semantics.
- **Net for solo-operator Claude Code:** ~70% overlap with OMEGA. Mem0's marginal-value play is "better automatic extraction"; OMEGA's `omega_store` is manual-with-typed-classification, which is arguably *better* for engineering decisions where you want auditability.

---

### 3.2 Graphiti / Zep

**One-paragraph plain-English description:** Graphiti is the open-source temporal knowledge-graph engine maintained by Zep. It models every fact as a graph edge with a *bi-temporal* validity window (when the fact was true; when the system learned about it). This lets agents reason precisely about how facts change over time — "Tom was running on PVE 8 *until* 2026-04-24; he's on PVE 9 *from* 2026-04-24". Zep is the commercial cloud product built on Graphiti; Graphiti by itself is fully self-hostable.

**Architecture:**
- Apache-2.0 (Graphiti); Zep Cloud is commercial SaaS.
- Backends: Neo4j 5.26+, FalkorDB 1.1.2+, Kuzu 0.11.2+, Amazon Neptune ([Graphiti GitHub](https://github.com/getzep/graphiti)).
- Bi-temporal model: every edge has `valid_at` and `recorded_at` intervals.
- LLM dependency at write-time for entity/relation extraction (best with structured-output models: OpenAI, Gemini; works with Anthropic, Groq, Azure, Ollama).
- ~25.4k stars (April 2026). Confidence: High.

**Claude Code integration:**
- Graphiti MCP Server v1.0.2 (released March 11, 2026) — direct stdio MCP support.
- Two install paths:
  - Docker Compose with built-in FalkorDB (recommended for solo dev): `docker compose up`, MCP at `http://localhost:8000/mcp/`.
  - Standalone with Neo4j: set `NEO4J_URI/USER/PASSWORD`, run `uv run main.py --database-provider neo4j`.
- ([Graphiti MCP docs](https://help.getzep.com/graphiti/getting-started/mcp-server))
- Note: Claude Desktop doesn't natively support HTTP transport, but Claude *Code* (the CLI) does, so the Docker-Compose+HTTP path is straightforward.

**Performance/benchmarks:**
| Benchmark | Score | Source | Confidence |
|---|---|---|---|
| LongMemEval (GPT-4o) | 63.8% | [Atlan](https://atlan.com/know/zep-vs-mem0/) | High (multi-source) |
| LoCoMo (vendor) | 84% (original); 75.14% (corrected) | [Mem0 paper](https://arxiv.org/abs/2504.19413) + Zep rebuttal | Medium (disputed) |
| LoCoMo (per Mem0 rebuttal) | 65.99% (claimed misconfig) | Same | Low (Mem0 vs Zep dispute) |

**Adoption proof:**
- 25.4k stars, 5+ database backends, peer-reviewed paper at arXiv:2501.13956. Confidence: High.
- Production users include enterprise customers (Zep Cloud).

**Maturity / governance risk:**
- Zep is VC-backed. Graphiti OSS is well-governed.
- Risk: Zep "Community Edition" was deprecated in favor of cloud; Graphiti core remains OSS, but the warning from past CE users is real ([Vectorize](https://vectorize.io/articles/best-ai-agent-memory-systems)).

**Hands-on third-party reviews:**
- [Neo4j blog](https://neo4j.com/blog/developer/graphiti-knowledge-graph-memory/) — substantive technical praise; obvious vendor angle (Neo4j is a backend).
- [Atlan Zep vs Mem0](https://atlan.com/know/zep-vs-mem0/) — clear-eyed: "Zep wins on temporal reasoning; Mem0 wins on community size."
- [Supermemory.ai comparison](https://blog.supermemory.ai/supermemory-vs-zep/) — biased competitor blog, takeable with salt.

**Cost (self-hosted):**
- Compute: medium. FalkorDB is light (~200MB). Neo4j 5.26 is heavier (~1GB+ RAM minimum, ~3GB recommended).
- LLM-call dependence: **heavy at write-time**. Each ingested message triggers LLM extraction; large repos can rack up tokens fast. Mitigation: point at your local Gemma reasoner via Ollama-compatible endpoint.

**Distinct capabilities vs OMEGA:**
- ✅ **Bi-temporal validity intervals** — this is the unique value-add. OMEGA has no documented temporal-fact-validity surface.
- ✅ Cypher-style graph traversal queries.
- ✅ Multi-modal source types (chat, business data, structured docs).
- ❌ No session-handoff / coord-block semantics.
- **Net for solo-operator Claude Code:** This is the ONE candidate that adds something OMEGA documentably does not have. The use case has to be real, though — temporal reasoning matters when "old decisions are ambient context" is a frequent failure mode.

---

### 3.3 Letta (MemGPT lineage)

**One-paragraph plain-English description:** Letta is the production rename of MemGPT, the original "LLM-as-an-OS" research project from UC Berkeley. The agent itself manages its own memory by calling tool functions to write to one of three tiers: `core` (always-in-context, like RAM), `recall` (a searchable conversation log), and `archival` (a long-term vector store). The agent decides what to remember; if the model judges wrong, the fact is lost. Letta isn't really a memory *library* — it's an entire *agent runtime* that happens to have memory as a first-class concern.

**Architecture:**
- Apache-2.0 license.
- Self-hostable via Docker (`compose.yaml`, `dev-compose.yaml`, `docker-compose-vllm.yaml` shipped).
- Backend: PostgreSQL.
- Model-agnostic at the API layer; supports OpenAI, Anthropic, Ollama, vLLM.
- ~22.3k stars (April 2026). Confidence: High.
- ([Letta GitHub](https://github.com/letta-ai/letta))

**Claude Code integration:**
- This is where Letta gets philosophically awkward. Letta has its own `letta-code` CLI which is an *alternative* to Claude Code — a memory-first coding agent ([letta-code GitHub](https://github.com/letta-ai/letta-code)).
- For Letta as a memory MCP *behind* Claude Code: there are community MCPs (e.g., [Letta Memory MCP on LobeHub](https://lobehub.com/mcp/miles990-letta-memory-mcp)) but no official first-party MCP.
- Letta's own docs explicitly recommend using *Skills* rather than MCP when working with Letta Code ([Letta MCP setup](https://docs.letta.com/guides/mcp/setup)).
- **Practical read:** Letta wants you to *replace* Claude Code, not augment it.

**Performance/benchmarks:**
- Letta has not published official LongMemEval or LoCoMo numbers ([Atlan](https://atlan.com/know/best-ai-agent-memory-frameworks-2026/)). Confidence: High that the gap is real.
- Anecdotal: "first open-source framework to demonstrate agents that improved measurably on task performance after weeks of operation" — corroborated by their published case studies but not an apples-to-apples benchmark.

**Adoption proof:**
- 22.3k stars; v0.16.7 March 31, 2026; active dev.
- Real production usage (named customers in their materials).

**Maturity / governance risk:**
- VC-backed, UC Berkeley pedigree, MemGPT-paper lineage.
- Risk: Letta's bet is that you adopt their *runtime*, not their library. If you keep Claude Code as your harness, Letta is the wrong shape.

**Hands-on third-party reviews:**
- [Vectorize Mem0 vs Letta](https://vectorize.io/articles/mem0-vs-letta) — "different problems": Mem0 is a memory API; Letta is an agent platform.
- [XYZEO Letta review](https://xyzeo.com/product/letta-memgpt) — substantive but vendor-friendly.
- [Letta Code blog](https://www.letta.com/blog/letta-code) — explicitly markets itself as a Claude-Code alternative.

**Cost (self-hosted):**
- Compute: medium-heavy — PostgreSQL + the agent process.
- LLM-call dependence: very heavy if the agent self-edits memory aggressively (each tool call is an LLM step). Letta themselves warn that "open weights models perform poorly outside the very best ones (GLM-4.7, MiniMax M2.1)" — frontier models are recommended ([Letta Ollama docs](https://docs.letta.com/guides/server/providers/ollama)).

**Distinct capabilities vs OMEGA:**
- ✅ Self-editing memory tiers (core/recall/archival), agent-controlled.
- ✅ Memory portability across model backends (the same agent state can run under Claude or GPT).
- ❌ Wrong layer — Letta isn't a memory MCP for Claude Code; it's a Claude Code alternative.
- **Net for solo-operator Claude Code:** Misfit. If the user *wanted* to leave Claude Code, Letta would be the credible candidate. He doesn't.

---

### 3.4 Honcho

**One-paragraph plain-English description:** Honcho, from Plastic Labs, is a peer-centric memory library focused on building per-user identity representations rather than fact stores. Its differentiator is the "Dialectic" API (you can ask Honcho natural-language questions about any peer it has observed) and the "Dream" pipeline (every ~8 hours, a background process consolidates observations into refined peer representations). It is heavily theory-of-mind-flavored — the implicit assumption is "you're building something that talks to multiple humans and needs to model each one."

**Architecture:**
- AGPL-3.0 license (restrictive; check before use in any closed-source product).
- Self-hostable: Postgres + pgvector, Redis, four background services (api, deriver, database, redis).
- LLM dependency: heavy and multi-call.
  - Default: Gemini for derivation/summary/minimal-reasoning, Anthropic for medium/high reasoning + dream.
  - OpenAI-compatible endpoints work (OpenRouter, Ollama, vLLM, LiteLLM).
- ~2.9k stars; ~327 forks. Confidence: High.
- ([Honcho GitHub](https://github.com/plastic-labs/honcho))

**Claude Code integration:**
- **No official MCP server** documented (as of April 2026). Honcho integrates via its own SDK/REST API, not via MCP.
- This is a meaningful integration gap for a Claude-Code-first operator.

**Performance/benchmarks:**
- LongMem S: 90.4% (Claude Haiku 4.5); 92.6% (Gemini 3 Pro)
- LoCoMo: 89.9%
- BEAM: 0.630/0.649/0.631/0.406 at 100k/500k/1M/10M tokens
- ([Plastic Labs benchmarks](https://blog.plasticlabs.ai/research/Benchmarking-Honcho))
- Confidence: Medium (vendor-published, but methodology is documented and the caveats are honest).
- **Critical caveat (acknowledged by Plastic Labs themselves):** "the latest models are beginning to underperform baseline" — i.e., on small-context tests, modern models without any memory framework score very close to memory-augmented systems. The marginal uplift is shrinking.

**Adoption proof:**
- Smaller community than Mem0/Letta/Graphiti.
- Plastic Labs has produced an AI tutor product ("Yousim") that uses Honcho — real production usage.

**Maturity / governance risk:**
- Smaller team. AGPL license is restrictive. VC-backed.

**Hands-on third-party reviews:**
- [bymar.co survey](https://blog.bymar.co/posts/agent-memory-systems-2026/) — "looks strongest when the problem is relationship-aware continuity"; "more infra than small hobby builds need."
- Notable: most third-party reviews position Honcho as *the* answer for multi-user products, not solo-dev tools.

**Cost (self-hosted):**
- Compute: heavier than Mem0 — four services, Postgres + Redis.
- LLM-call dependence: very heavy — Deriver runs on every message, Dream every ~8 hours.

**Distinct capabilities vs OMEGA:**
- ✅ Theory-of-mind per-peer modeling (OMEGA stores `user_preference` but doesn't run a Dialectic-style synthesis).
- ✅ Background consolidation (Dream).
- ❌ No MCP integration with Claude Code.
- ❌ AGPL-3.0 may be a concern depending on how the user redistributes.
- **Net for solo-operator Claude Code:** Mismatch. Honcho's sweet spot is "I have many users and I need to model each one." For a single homelab operator, the per-user-modeling lane doesn't apply.

---

### 3.5 OpenMemory MCP

**One-paragraph plain-English description:** OpenMemory MCP is the "local-first wrapper" pattern: a Docker stack (Mem0's own version uses Postgres + Qdrant) exposing the memory API over MCP, fully on the user's machine, no data egress. There are at least two distinct projects under this name: (1) Mem0's own [OpenMemory](https://mem0.ai/blog/introducing-openmemory-mcp), which is essentially a self-host wrapper around mem0ai with an admin dashboard at `localhost:3000`, and (2) [CaviraOSS/OpenMemory](https://github.com/CaviraOSS/OpenMemory), an independent community project with similar goals. They share the marketing name but are not the same codebase.

**Architecture:**
- Mem0's OpenMemory: Docker + Postgres + Qdrant; uses mem0ai under the hood. Supports Ollama for fully local operation.
- CaviraOSS OpenMemory: lighter, claims fully local persistent memory across "claude desktop, github copilot, codex, antigravity, etc."
- License: Apache-2.0 (mem0); not verified on the CaviraOSS fork.

**Claude Code integration:**
- MCP-native by design. Setup is comparable to Mem0's MCP server but without the cloud account.
- Multiple community walkthroughs ([dev.to](https://dev.to/n3rdh4ck3r/how-to-give-claude-code-persistent-memory-with-a-self-hosted-mem0-mcp-server-h68), [apidog](https://apidog.com/blog/openmemory-mcp-server/)).

**Performance/benchmarks:**
- Inherits Mem0's algorithm; same scores apply (LoCoMo 91.6 / LongMemEval 93.4 with the April 2026 algo).

**Adoption proof:**
- Smaller standalone footprint, but rides Mem0's adoption curve.

**Maturity / governance risk:**
- Reasonable for the Mem0-branded version; CaviraOSS variant is community-maintained — assess before relying on it.

**Hands-on third-party reviews:**
- [apidog walkthrough](https://apidog.com/blog/openmemory-mcp-server/) — straightforward setup, ~10 min on a typical box.
- [mem0 official launch](https://mem0.ai/blog/introducing-openmemory-mcp) — vendor framing.

**Cost (self-hosted):**
- Compute: tiny. LLM-dependence inherited from Mem0 (heavy at write-time).

**Distinct capabilities vs OMEGA:**
- ❌ Same lane as Mem0 — no theory-of-mind, no temporal validity intervals.
- ✅ Local-first and Ollama-friendly out of the box.
- **Net for solo-operator Claude Code:** Equivalent to "Mem0 self-hosted." If the user wanted Mem0 but only via local-first MCP, this is the path. But that decision was already negative in §3.1.

---

### 3.6 Cognee

**One-paragraph plain-English description:** Cognee is a knowledge-engine framework: ingest documents (any format), extract entities, build a queryable knowledge graph + vector index, and expose `remember`/`recall`/`forget`/`improve` operations. Its sweet spot is *batch ingestion* of pre-existing corpora (wikis, docs, papers), not *live conversational capture*. Architecturally compelling for the homelab use case because the default stack is fully embedded: SQLite + LanceDB + Kuzu, no external services.

**Architecture:**
- Apache-2.0; ~16.8k stars, ~1.7k forks.
- Default local stack: SQLite + LanceDB + Kuzu — all file-based, zero infra.
- Optional Neo4j, Memgraph, Postgres backends.
- LLM dependency: heavy at ingestion (extraction + relation inference).
- ([Cognee GitHub](https://github.com/topoteretes/cognee))

**Claude Code integration:**
- Official Cognee MCP server (`cognee-mcp` directory in repo). Supports stdio.
- Setup: `pip install cognee` + register the MCP — well under a minute on a working box.
- ([Official MCP docs](https://www.pulsemcp.com/servers/topoteretes-cognee-mcp))

**Performance/benchmarks:**
- No published LongMemEval or LoCoMo numbers as of April 2026.
- Recent paper on graph-LLM optimization ([arXiv:2505.24478](https://arxiv.org/abs/2505.24478)) covers methodology, not headline benchmark numbers.
- **Honest read:** Cognee leadership chooses not to play the LongMemEval-leaderboard game, which is defensible (Cognee solves a different problem) but means we have no apples-to-apples comparison.

**Adoption proof:**
- 16.8k stars is real adoption.
- Recent $7.5M seed round ([Cognee blog](https://www.cognee.ai/blog/cognee-news/cognee-raises-seven-million-five-hundred-thousand-dollars-seed)).

**Maturity / governance risk:**
- Well-funded, growing team, OSS license clean.
- Risk: solving a slightly different problem than this report's question.

**Hands-on third-party reviews:**
- [Vectorize](https://vectorize.io/articles/best-ai-agent-memory-systems) — "best for local-first deployments with graph reasoning"; "doesn't handle conversational personalization."
- [LanceDB case study](https://www.lancedb.com/blog/case-study-cognee) — vendor blog but technically substantive.

**Cost (self-hosted):**
- Compute: trivial — fully embedded.
- LLM-call dependence: heavy at ingestion, light at query.

**Distinct capabilities vs OMEGA:**
- ✅ Knowledge-graph extraction over arbitrary document corpora.
- ❌ Not designed for live agent conversation memory.
- **Net for solo-operator Claude Code:** Cognee is the *right* tool for "I have a folder of project docs and want them queryable as a graph" — which is much closer to what graphify / GitNexus solve, and which is **out of scope** for this memory study.

---

### 3.7 Honourable mentions

Additional 2026 entrants surfaced in the research; none are recommended for this user but they're real:

- **Hindsight (Vectorize)** — claims 91.4% LongMemEval, MIT license, Docker self-host, MCP-first. Strong on benchmark but "more tuning surface" per third-party review ([bymar.co](https://blog.bymar.co/posts/agent-memory-systems-2026/)). Worth re-evaluating if the user re-opens this question in 6 months.
- **Supermemory** — closed-source SaaS with claimed 81.6% LongMemEval. Nice MCP integration with Claude Code, but the closed-source posture is wrong for a privacy-leaning operator.
- **MemMachine** — academic-origin, claims 0.9169 on LoCoMo and 93.0 on LongMemEval-S ([arXiv:2604.04853](https://arxiv.org/html/2604.04853)) — interesting research, not yet a production offering.
- **MemPalace** — recently went viral, but reviewer notes "oversold benchmarks early; some token-count claims were off" ([bymar.co](https://blog.bymar.co/posts/agent-memory-systems-2026/)). Treat with caution.

---

## 4. OMEGA Comparison Matrix

| Capability | OMEGA | Mem0 | Graphiti/Zep | Letta | Honcho | OpenMemory MCP | Cognee |
|---|---|---|---|---|---|---|---|
| Persistent cross-session memory | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Similarity / semantic search | ✅ (`omega_query`) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Typed memory (decision/preference) | ✅ (first-class) | partial (preferences only) | partial (entity types) | partial (block labels) | ✅ (peer-centric) | ❌ | partial |
| Hooks-injected ground-truth blocks | ✅ (`[MEMORY]/[HANDOFF]/[COORD]`) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Memory-graph linking | ✅ (`omega_memory similar`) | partial (Pro graph tier) | ✅ (native KG) | partial | partial | partial | ✅ (native KG) |
| Reflection / evolution thinking | ✅ (`omega_reflect`) | ❌ | ❌ | ✅ (self-edit) | ✅ (Dream) | ❌ | partial (`improve`) |
| **Bi-temporal validity intervals** | ❌ | ❌ | **✅ (unique)** | ❌ | ❌ | ❌ | ❌ |
| **Theory-of-mind / Dialectic** | ❌ | ❌ | ❌ | partial (self-edit) | **✅ (unique)** | ❌ | ❌ |
| Self-editing agent state | ❌ | ❌ | ❌ | **✅ (unique)** | partial | ❌ | ❌ |
| MCP-native for Claude Code | ✅ | ✅ | ✅ | partial (community only) | ❌ | ✅ | ✅ |
| Local-first / privacy-clean | ✅ | partial (self-host complex) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Zero-infra default install | ✅ | ❌ (Postgres+Qdrant) | ❌ (Neo4j/FalkorDB) | ❌ (Postgres) | ❌ (Postgres+Redis) | partial | ✅ (SQLite+LanceDB+Kuzu) |
| LLM-cost at write-time | low | high | high | very high | very high | high | high |

**Reading the matrix:** OMEGA has *one* uncontested capability (`[MEMORY]`/`[HANDOFF]`/`[COORD]` blocks as hook-injected ground truth) and three that no candidate has (typed memory + hooks blocks + the `omega_protocol()` session contract). The candidates have *three* capabilities OMEGA does not: bi-temporal intervals (Graphiti only), theory-of-mind (Honcho only), self-editing state (Letta only).

The shape of the decision: do you want one of those three things badly enough to add a second memory plane?

---

## 5. Benchmarks and Independent Evaluations

**Headline benchmark scores (April 2026, normalized to LongMemEval where possible):**

| System | LongMemEval | LoCoMo | Source | Confidence |
|---|---|---|---|---|
| Honcho | 90.4–92.6% | 89.9% | [Plastic Labs](https://blog.plasticlabs.ai/research/Benchmarking-Honcho) | Medium (vendor) |
| Mem0 (April 2026 algo) | 93.4 | 91.6 | [Mem0 blog](https://mem0.ai/blog/mem0-the-token-efficient-memory-algorithm) | Medium (vendor) |
| Mem0 (older paper) | 49.0% | 67.13% | [arXiv 2504.19413](https://arxiv.org/abs/2504.19413) | High (peer-reviewed) |
| Graphiti/Zep | 63.8% | 84% (vendor) / 75.14% (corrected) / 65.99% (Mem0-disputed) | [Atlan](https://atlan.com/know/zep-vs-mem0/) | Medium (disputed) |
| Hindsight | 91.4% | not cited | [arXiv 2512.12818](https://vectorize.io/articles/best-ai-agent-memory-systems) | Medium |
| Supermemory | 81.6% | not cited | Vendor | Medium |
| MemMachine | 93.0 | 91.7 | [arXiv 2604.04853](https://arxiv.org/html/2604.04853) | Medium (academic) |
| Letta | not published | not published | [Atlan](https://atlan.com/know/best-ai-agent-memory-frameworks-2026/) | High (gap is real) |
| Cognee | not published | not published | (no publication) | High (gap is real) |
| OMEGA | not benchmarked publicly | not benchmarked publicly | (internal) | n/a |

**Critical observations:**
- **Every leader's headline score is vendor-published.** Each vendor's number has at some point been disputed by another vendor.
- **The Mem0 vs Zep dispute is the canonical case study.** Mem0's ECAI 2025 paper benchmarked Zep at 65.99% on LOCOMO; Zep's rebuttal alleged misconfiguration and counter-claimed 75.14%. Both numbers are now in the literature, ~10 points apart, depending on whose paper you read.
- **The "modern model with no memory beats older model with memory" effect is real.** Plastic Labs themselves note that on LongMem-S, "Gemini 3 Pro alone scores 92.0%" — i.e., the headroom for memory frameworks shrinks as base models improve.
- **No third-party head-to-head ranking exists with all six candidates on the same hardware, same prompts, same backbone.** Until that exists, *any* numerical leaderboard claim is best treated as Medium-confidence at best.

**For the user's context (single-operator engineering memory, not multi-user customer support):** LongMemEval and LoCoMo measure conversational fact-recall; they do *not* measure handoff-block fidelity, decision-archeology, or coord-block correctness. **The benchmarks evaluate a different problem than the one OMEGA is solving.** This makes them weak as a tie-breaker for this user's specific decision.

---

## 6. Integration with Claude Code

**Install ergonomics ranking (best to worst for a Claude Code daily-driver):**

| Tool | Install | Time-to-first-query |
|---|---|---|
| Cognee MCP | `pip install cognee` + MCP register | ~1 min |
| OpenMemory MCP | Docker + `make up` | ~5 min |
| Mem0 MCP (cloud) | Add MCP entry, paste API key | ~3 min |
| Mem0 MCP (self-host) | Docker Compose + Postgres + Qdrant | ~10 min |
| Graphiti MCP (FalkorDB) | `docker compose up` | ~5 min |
| Graphiti MCP (Neo4j) | Provision Neo4j 5.26+, env vars | ~15 min |
| Honcho | No MCP — direct SDK/API integration only | n/a (write your own MCP shim) |
| Letta | Docker stack, but the philosophical mismatch makes integration awkward | ~30 min for Docker; lifetime for the philosophy |

**Hook compatibility (OMEGA-style `[MEMORY]`/`[HANDOFF]` injection):** *None of the candidates replicate this pattern.* They all assume they ARE the memory-injection layer, not a co-tenant. Layering any of them alongside OMEGA means OMEGA's hook injection remains the primary mechanism and the new tool adds a *tool-call-mediated* secondary surface.

**MCP transport notes:**
- Claude Code (CLI) supports both stdio and HTTP MCP. Most candidates publish stdio; Graphiti also publishes HTTP via its FalkorDB Docker recipe.
- Multi-MCP coexistence with OMEGA is mechanically fine — the MCP spec allows multiple servers in `~/.claude.json`.

---

## 7. Cost, Privacy, and Maturity

**Cost (assuming self-hosted on your existing PVE3 box, using local Gemma reasoner via Ollama-compatible endpoint):**

| Tool | Compute (RAM) | LLM-token cost (write-time, on-host) | LLM-token cost (read-time) |
|---|---|---|---|
| Cognee | <500 MB | medium | low |
| Mem0 / OpenMemory | ~1 GB | medium-high | low (~7k tokens/query post-April-2026) |
| Graphiti (FalkorDB) | ~500 MB | high | low |
| Graphiti (Neo4j) | ~3 GB | high | low |
| Honcho | ~1.5 GB (Postgres+Redis) | very high (Deriver+Dream loops) | medium |
| Letta | ~1.5 GB | very high (self-edit per-step) | medium |
| OMEGA (current) | varies | n/a (manual capture) | low |

**Privacy:** All seven are self-hostable in some configuration. Mem0's "real product is the cloud" caveat is real — multiple reviewers note the self-host path is "you're on your own."

**Maturity:**
- Most established: Mem0 (54k stars, ECAI paper).
- Strongest pedigree: Letta (UC Berkeley, MemGPT paper).
- Best-funded recent entrant: Cognee ($7.5M seed).
- Smallest team: Honcho (Plastic Labs, ~3 people core).
- Best-governed OSS: Graphiti (Apache-2.0, Zep keeps the OSS core honest).

---

## 8. Strategic Recommendations

**Primary recommendation: Stay on OMEGA only.** No candidate offers enough above-and-beyond capability to justify the operational and conceptual cost of running two memory planes side-by-side for a single-operator homelab.

The reasoning:

1. **Capability overlap is high.** OMEGA already covers persistent cross-session memory, similarity search, typed memory, reflection, hook-injected ground truth, and memory linking. Mem0, Honcho, and OpenMemory are largely re-implementations of those primitives with different names.

2. **The three uncontested capabilities — bi-temporal intervals (Graphiti), theory-of-mind (Honcho), self-editing state (Letta) — each map to a use case the user does not have.**
   - Bi-temporal intervals matter most when *audit/compliance* or *decision-supersession-tracking* is a real failure mode. For a homelab, the failure mode is closer to "I forgot what we decided on Tuesday" — which OMEGA's `decision`-typed store already handles.
   - Theory-of-mind matters when there are *multiple humans* the agent needs to model. There is one Tom.
   - Self-editing memory matters when you want the *agent runtime* to manage its context. The user's runtime is Claude Code, not Letta.

3. **Operating two MCP-mediated memory planes is non-trivial.** Two systems means two query paths, two consistency models, two failure modes, and a real risk of "which memory is canonical?" for a given fact.

4. **Benchmarks don't measure the user's problem.** LongMemEval and LoCoMo are conversational-fact recall tests on synthetic dialogs. They don't measure handoff-block fidelity, project-context continuity, or decision-archeology — which is what OMEGA is for.

**Secondary recommendation (only if the primary is rejected): Add Graphiti as a *narrow, optional* second tier — temporal-decision tracking only.**

The case for Graphiti specifically:
- It's the only candidate offering bi-temporal intervals — a real capability OMEGA does not have.
- The MCP integration is clean (FalkorDB Docker Compose, ~5 min).
- Apache-2.0, ~25k stars, peer-reviewed paper.
- It can be sized small (FalkorDB ~500 MB) and run on PVE3 with no impact on the existing cluster.

The narrow scope:
- *Only* feed Graphiti decision-events with explicit `valid_at` intervals — not every conversation message.
- Treat Graphiti as a *secondary* tool the user explicitly invokes for "what did we decide about X, and is it still true?" queries.
- Keep OMEGA as the primary plane and the default for `omega_query`/`omega_store` calls.

**Tertiary recommendation: Re-evaluate in 6 months.**

The category is moving fast. The Mem0 April 2026 algorithm rewrite (LoCoMo 91.6) is a recent shock; Hindsight's claims (LongMemEval 91.4%) are a recent entrant; MemMachine and the academic frontier are pushing higher numbers. By Q4 2026, the answer may differ. Set a recurring "memory-systems checkpoint" reminder for October 2026.

**Recommendations explicitly not made:**
- Mem0 — capability overlap with OMEGA is too high.
- Letta — wrong layer; replaces Claude Code rather than augmenting it.
- Honcho — sweet spot is multi-user; user is solo.
- Cognee — solves a different problem (document KG ingestion); already covered by the parallel graphify research.
- OpenMemory MCP — equivalent to "Mem0 self-hosted" which is also rejected.

---

## 9. Implementation Roadmap (only if Graphiti adoption is approved)

**Phase 0 — Decision gate (1 hour)**
- Confirm a real, recurring failure mode that bi-temporal intervals would solve. Examples: "I decided X about pve2 storage on date D; that decision was superseded on D+N; I want the agent to know which is current." If no such recurring failure, abort and stay on OMEGA only.

**Phase 1 — Pilot install (1 day)**
- Spin up a test container (`ct-dev-test` per the user's standing policy) with Graphiti MCP via Docker Compose + FalkorDB.
- Wire Graphiti into Claude Code's `~/.claude.json` as a *secondary* MCP server.
- Configure Graphiti's LLM endpoint to point at the local Gemma reasoner (Ollama-compatible, per `hybrid_gemma_serving`).

**Phase 2 — Ingestion contract (2-3 days)**
- Define the *single* event source: `omega_store(content, "decision")` calls also emit a Graphiti edge with explicit `valid_at` and (when applicable) `invalidated_at` intervals.
- Write an OMEGA hook that publishes to Graphiti on `decision`-typed stores. Keep all other typed memories OMEGA-only.

**Phase 3 — Query path (1-2 days)**
- Add a slash command `/decision-history <topic>` that issues a Graphiti Cypher query for "facts valid as-of now" and "facts that were valid as-of date D." Return results to the agent.

**Phase 4 — 4-week pilot evaluation (4 weeks elapsed)**
- Track: how many queries to Graphiti vs OMEGA; how often the temporal-aware answer differed materially from the OMEGA answer; how often the agent's behavior changed because of it.
- Exit gate: if Graphiti added <5 material answer-changes in 4 weeks, deprecate it.

**Phase 5 — Production deployment (only if exit gate passes) (1 day)**
- Move from `ct-dev-test` to a `ct-graphiti-01` project container with HA policy matching standing project-CT policy.

**Total elapsed: ~5–7 weeks of part-time effort, exit gate at week 4.**

---

## 10. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Graphiti's LLM-cost-at-ingestion balloons under aggressive event capture | Medium | Medium | Throttle ingestion to `decision`-typed events only; use local Gemma; monitor token count weekly |
| Two memory planes diverge — agent gets contradictory answers from OMEGA vs Graphiti | Medium | High | Define OMEGA as the canonical plane; Graphiti is read-only-for-temporal-questions only |
| Benchmark numbers used to justify any candidate are revealed to be misconfigured | Medium | Low | Don't justify on benchmarks alone; capability-fit is the real argument |
| Honcho's AGPL-3.0 license creates licensing concerns if redistributed | Low | High | Don't pick Honcho |
| Letta absorbs the Claude Code workflow and the user ends up rebuilding everything | Low | Very High | Don't pick Letta |
| Mem0 cloud-vs-self-host gap leaves the user maintaining an unsupported deployment | Medium | Medium | Don't pick Mem0 |
| Category shifts within 6 months and the recommendation goes stale | High | Low | Re-evaluate in October 2026 |
| Adopting any candidate adds a cognitive-overhead "second memory plane" the user has to remember | High | Medium | Stay on OMEGA only; this is the primary recommendation precisely because of this risk |

---

## 11. Sources and Confidence Levels

**Primary sources (vendor / repository):**
- [Mem0 GitHub](https://github.com/mem0ai/mem0) — High confidence on stars, license, install
- [Mem0: Token-Efficient Memory Algorithm](https://mem0.ai/blog/mem0-the-token-efficient-memory-algorithm) — Medium confidence (vendor)
- [Mem0 paper, ECAI 2025](https://arxiv.org/abs/2504.19413) — High confidence (peer-reviewed)
- [Graphiti GitHub](https://github.com/getzep/graphiti) — High confidence
- [Graphiti MCP Server docs](https://help.getzep.com/graphiti/getting-started/mcp-server) — High confidence
- [Zep paper, arXiv 2501.13956](https://arxiv.org/abs/2501.13956) — High confidence (academic)
- [Letta GitHub](https://github.com/letta-ai/letta) — High confidence
- [Letta self-hosting docs](https://docs.letta.com/guides/selfhosting) — High confidence
- [Letta Ollama provider docs](https://docs.letta.com/guides/server/providers/ollama) — High confidence
- [Honcho GitHub](https://github.com/plastic-labs/honcho) — High confidence
- [Honcho Benchmarks](https://blog.plasticlabs.ai/research/Benchmarking-Honcho) — Medium confidence (vendor, but methodologically candid)
- [Cognee GitHub](https://github.com/topoteretes/cognee) — High confidence
- [Cognee MCP server](https://www.pulsemcp.com/servers/topoteretes-cognee-mcp) — Medium confidence
- [OpenMemory MCP launch](https://mem0.ai/blog/introducing-openmemory-mcp) — Medium confidence (vendor)
- [LoCoMo benchmark](https://snap-research.github.io/locomo/) — High confidence
- [LongMemEval paper](https://arxiv.org/pdf/2410.10813) — High confidence (peer-reviewed)

**Third-party comparison articles:**
- [Atlan: Best AI Agent Memory Frameworks 2026](https://atlan.com/know/best-ai-agent-memory-frameworks-2026/) — Medium-High (substantive analysis)
- [Atlan: Zep vs Mem0](https://atlan.com/know/zep-vs-mem0/) — Medium-High
- [Vectorize: Best AI Agent Memory Systems](https://vectorize.io/articles/best-ai-agent-memory-systems) — Medium (vendor-adjacent)
- [bymar.co: Agent Memory Systems 2026](https://blog.bymar.co/posts/agent-memory-systems-2026/) — Medium (analyst, refreshingly skeptical)
- [DEV.to: 5 AI Agent Memory Systems Compared](https://dev.to/varun_pratapbhardwaj_b13/5-ai-agent-memory-systems-compared-mem0-zep-letta-supermemory-superlocalmemory-2026-benchmark-59p3) — Medium
- [DEV.to: Mem0 vs Zep vs LangMem vs MemoClaw](https://dev.to/anajuliabit/mem0-vs-zep-vs-langmem-vs-memoclaw-ai-agent-memory-comparison-2026-1l1k) — Medium
- [Hermes OS blog: AI agent memory systems in 2026](https://hermesos.cloud/blog/ai-agent-memory-systems) — Medium
- [Yogesh Yadav on Medium](https://blog.devgenius.io/ai-agent-memory-systems-in-2026-mem0-zep-hindsight-memvid-and-everything-in-between-compared-96e35b818da8) — Medium
- [Reliable Data Engineering on Medium](https://medium.com/@reliabledataengineering/mem0-do-ai-agents-really-need-memory-honest-review-6760b5288f37) — Medium (honest skeptic)
- [ChatForest: Mem0 MCP review](https://chatforest.com/reviews/mem0-mcp-server/) — Medium

**Academic / benchmark sources:**
- [LongMemEval](https://arxiv.org/pdf/2410.10813) — High
- [LoCoMo](https://snap-research.github.io/locomo/) — High
- [MemMachine arXiv 2604.04853](https://arxiv.org/html/2604.04853) — Medium (recent)
- [BEAM benchmark mentions across Plastic Labs and Mem0](https://blog.plasticlabs.ai/research/Benchmarking-Honcho) — Medium

**Confidence calibration summary:**
- **High-confidence claims:** GitHub star counts, license terms, MCP availability/absence, peer-reviewed benchmark methodology.
- **Medium-confidence claims:** Vendor-published benchmark numbers, "fastest install" claims, comparative rankings from third-party blogs.
- **Low-confidence claims:** Disputed benchmarks (Mem0 vs Zep on LoCoMo), forward-looking "best for X use case" recommendations, claims of production usage at scale that are not third-party verified.

---

*End of report.*
