---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments: ['https://github.com/safishamsi/graphify']
workflowType: 'research'
lastStep: 6
research_type: 'technical'
research_topic: 'graphify (github.com/safishamsi/graphify) — multimodal AI-powered knowledge graph generator: technical merit and comparison with alternatives'
research_goals: 'Evaluate whether graphify offers better output and value than alternative knowledge-graph / code-RAG / GraphRAG implementations; gather available benchmarks and third-party reviews; produce a recommendation on adopt vs alternative.'
user_name: 'tomamourette'
date: '2026-04-25'
web_research_enabled: true
source_verification: true
---

# Research Report: technical

**Date:** 2026-04-25
**Author:** tomamourette
**Research Type:** technical

---

## Research Overview

This report evaluates **graphify** (https://github.com/safishamsi/graphify) — a multimodal AI-powered knowledge-graph generator released April 3, 2026 by @safishamsi — that turns folders of code, docs, papers, images, and video into a queryable graph for AI coding assistants. It compares graphify against the broader 2026 landscape of GraphRAG, code-RAG, and knowledge-graph-from-LLM tools (GitNexus, CodeGraphContext, code-review-graph, codegraph, FalkorDB CodeGraph, Microsoft GraphRAG, LightRAG, nano-graphrag, Sourcegraph Cody, Aider repo-map) to determine technical merit, output quality, and the right adoption posture for tomamourette's three-repo homelab + project-container topology.

**Headline finding**: graphify's *architectural choices are validated* by independent academic work (arxiv:2601.08773 confirms AST-derived KGs beat both LLM-extracted KGs and vector-only RAG for code multi-hop QA). However, its **headline 71.5× token-reduction claim is corpus-specific** — better-controlled third-party benchmarks (code-review-graph's 3-repo study) show the reduction factor *scales inversely with repo size*: 26.2× at ~125 files, 6.0× at ~28k files. **Expect ~5–10× on real medium-size repos, not 71.5×.** Graphify's strongest differentiators are the **multi-modal pass** (code + docs + papers + images + audio/video, none-of-which alternatives match end-to-end), **first-class edge confidence labels**, **git-committable artifacts**, and a unique **multi-repo merge** workflow that fits your polyrepo topology cleanly.

**Adoption verdict (preview — full reasoning in §8 and the Conclusion)**: **Adopt with caveats** for a 4-week pilot on `homelab-playbook`, with code-review-graph kept as a peer for code-review tasks and GitNexus's MCP-first trajectory monitored for the 8-week re-evaluation gate. The full executive summary, TOC, and recommendations live in the Research Synthesis section at the end of this document.

---

## Technical Research Scope Confirmation

**Research Topic:** graphify (github.com/safishamsi/graphify) — multimodal AI-powered knowledge graph generator: technical merit and comparison with alternatives

**Research Goals:** Evaluate whether graphify offers better output and value than alternative knowledge-graph / code-RAG / GraphRAG implementations; gather available benchmarks and third-party reviews; produce a recommendation on adopt vs alternative.

**Technical Research Scope:**

- Architecture Analysis - graph construction pipeline, AST→graph extraction, Leiden community detection, query model
- Implementation Approaches - install/run model, integration hooks (Claude Code, Cursor, Copilot CLI), determinism vs LLM dependence, cost
- Technology Stack - tree-sitter, NetworkX, graspologic/Leiden, faster-whisper, vis.js, OpenAI/Anthropic SDKs
- Integration Patterns - hook installation, git-committable artifacts, team/CI workflows, multi-repo merge (v0.5)
- Performance Considerations - the 71.5× token-reduction claim, indexing time/cost, scaling on large repos, query latency
- Comparative Landscape - GraphRAG family (MS GraphRAG, LightRAG, nano-graphrag), code-RAG (Cody, Aider repo-map, code2flow, Joern, Stack Graphs), KG-from-LLM (Neo4j llm-graph-builder, LlamaIndex KG), multimodal indexers
- Benchmarks & Reviews - methodology of the 71.5× claim, independent benchmarks, HN/Reddit/dev.to reception
- Adoption Verdict - clear recommendation tailored to homelab/dev-assistant use

**Research Methodology:**

- Live web search + direct fetches against the repo, releases, issues, third-party blogs
- Cross-check of comparative benchmarks where they exist (and explicit "no comparable benchmark" notes where they don't)
- Confidence levels on contested claims (e.g., 71.5×, star count)
- Skeptical posture toward self-reported benchmarks; preference for third-party reviews

**Scope Confirmed:** 2026-04-25

---

<!-- Content will be appended sequentially through research workflow steps -->

## Technology Stack Analysis

> Live web search executed 2026-04-25. Where claims could not be independently reproduced, confidence is annotated explicitly.

### Programming Languages

Graphify is a Python tool that **parses 25 source-code languages via tree-sitter ASTs** (Python, TypeScript, JavaScript, Go, Rust, Java, C#, C++, etc.), with a separate multimodal pass for non-code formats (Markdown, PDF, image, audio, video).

- _Popular Languages: Python is the dominant control-plane language across this category — Microsoft GraphRAG, LightRAG, nano-graphrag, LlamaIndex KG, neo4j-llm-graph-builder, CodeGraphContext, GitNexus's server side, and graphify itself are all Python-first. Rust is rising in the AST tier (tree-sitter core, ast-grep)._
- _Emerging Languages: .NET ports (`graphify-dotnet`) and TypeScript ports (GitNexus runs entirely in-browser) signal that the architecture is being re-implemented in language ecosystems whose teams want a native dependency-free experience._
- _Language Evolution: The "deterministic AST first, LLM second" model is now the de-facto blueprint for code-RAG; pure-LLM extraction has lost momentum after the arxiv:2601.08773 result (see Performance section)._
- _Performance Characteristics: Python is fine for orchestration; the actual hot path is tree-sitter (C with bindings), graspologic/Leiden (C++), and faster-whisper (CTranslate2/CUDA). The Python layer is glue, not a bottleneck._
- _Source: [GitHub - safishamsi/graphify](https://github.com/safishamsi/graphify), [Repository Intelligence in AI Coding Tools (2026)](https://www.buildmvpfast.com/blog/repository-intelligence-ai-coding-codebase-understanding-2026), [Graph Praxis: Graph RAG in 2026](https://medium.com/graph-praxis/graph-rag-in-2026-a-practitioners-guide-to-what-actually-works-dca4962e7517)._

### Development Frameworks and Libraries

**Graphify's core stack (verified):**

| Layer | Choice | Why it matters |
|---|---|---|
| Code parsing | **tree-sitter** (25 languages) | Deterministic, language-agnostic, no LLM cost. Same primitive used by GitHub Stack Graphs, Aider repo-map, Sourcegraph SCIP, code-review-graph, CodeGraphContext, codegraph, GitNexus. |
| Graph store | **NetworkX** (in-memory, on-disk JSON) | "No Neo4j required" is a differentiator from GraphRAG-in-Neo4j and FalkorDB CodeGraph. Trade-off: scaling ceiling (~10⁶ nodes) before query latency degrades. |
| Community detection | **Leiden via graspologic** | Topology-based clustering. **No embeddings used for clustering**, which is unusual — most GraphRAG variants cluster via embedding similarity or co-occurrence. |
| Speech-to-text | **faster-whisper** (local, CTranslate2) | Keeps audio/video on-disk; no third-party transcription bills. |
| Visualization | **vis.js** (interactive HTML) | Single-file output, git-committable, no server. |
| Semantic extraction | **Claude subagents** (parallel) | Drives the docs/papers/images pass. **Anthropic-only at present** — a real lock-in concern (see Limitations). |
| Edge confidence | Custom: `EXTRACTED` / `INFERRED` / `AMBIGUOUS` | Honest UX for non-deterministic edges; few competitors expose this. |

**Comparable framework choices in alternatives:**

- **Microsoft GraphRAG**: LangChain + custom indexing + Parquet artifacts; LLM-heavy entity/relation extraction; community summaries pre-computed.
- **LightRAG**: Lightweight in-memory with optional Neo4j; dual-level retrieval (low-level entities + high-level themes).
- **nano-graphrag**: Single-file ~1000-line GraphRAG re-implementation; popular as a hackable substrate.
- **GitNexus**: Tree-sitter + WebAssembly graph engine + MCP server + Claude Code hooks (PreToolUse / PostToolUse).
- **CodeGraphContext**: Tree-sitter + Neo4j + MCP server + CLI.
- **code-review-graph**: Tree-sitter + SQLite + Claude Code skill (claims 6.8× fewer tokens on reviews, 49× on daily coding).
- **codegraph (colbymchenry)**: Tree-sitter + JSON, 100% local, pre-indexed.
- **FalkorDB CodeGraph**: FalkorDB (Redis-graph fork) + AST + Cypher queries.
- **Aider repo-map**: PageRank over symbol graph, no LLM extraction, plain text repo-map injected into prompt.
- **Sourcegraph Cody**: SCIP indexes + remote search API + enterprise indexing pipeline.

_Source: [graphify ARCHITECTURE.md](https://github.com/safishamsi/graphify/blob/v3/ARCHITECTURE.md), [Memgraph: GraphRAG for Devs — Graph-Code](https://memgraph.com/blog/graphrag-for-devs-coding-assistant), [FalkorDB CodeGraph](https://www.falkordb.com/blog/code-graph/), [GitNexus on MarkTechPost](https://www.marktechpost.com/2026/04/24/meet-gitnexus-an-open-source-mcp-native-knowledge-graph-engine-that-gives-claude-code-and-cursor-full-codebase-structural-awareness/), [code-review-graph](https://github.com/tirth8205/code-review-graph), [codegraph by colbymchenry](https://github.com/colbymchenry/codegraph)._

### Database and Storage Technologies

- _Relational/SQL: Not used by graphify directly. code-review-graph uses SQLite as a persistence layer; that's a sensible upgrade path graphify could add._
- _NoSQL — Graph: **Graphify deliberately avoids a graph database**. Alternatives that adopt one: CodeGraphContext (Neo4j), FalkorDB CodeGraph (FalkorDB), Memgraph Graph-Code (Memgraph), Microsoft GraphRAG-in-Neo4j (community fork), Neo4j llm-graph-builder. Trade-off: graphify's NetworkX-on-disk approach gives zero-install and git-committable artifacts; graph-DB approaches give Cypher queries and scale to multi-million-node corpora._
- _In-Memory: NetworkX is purely in-memory at query time; the on-disk artifact is a JSON serialization. For very large corpora this is the principal scaling ceiling._
- _Embeddings/Vector: **Notably absent in graphify's clustering path** — Leiden is topology-based. This is both a feature (deterministic, cheap, reproducible) and a limitation (cannot do "semantically similar but never linked" retrieval, which LightRAG and Microsoft GraphRAG can)._
- _Cache: SHA256 file-content cache makes re-runs cheap — confirmed by reviewers._
- _Source: [graphify README v4](https://github.com/safishamsi/graphify/blob/v4/README.md), [Kevin Kinnett's hands-on review](https://www.kevinkinnett.com/posts/graphify-review-claude-code-knowledge-graph/), [paperclipped: Graph RAG in 2026 — Production](https://www.paperclipped.de/en/blog/graph-rag-production/)._

### Development Tools and Platforms

**Graphify ships as a "skill" / installable hook for AI coding assistants.** Documented integrations: **Claude Code, Codex, OpenCode, Cursor, Gemini CLI, GitHub Copilot CLI, VS Code Copilot Chat, Aider, OpenClaw, Factory Droid, Trae, Hermes, Kiro, Google Antigravity** — invoked as `/graphify`. PyPI package: `graphifyy` (note the double-y).

- _IDE/Editor integration: Graphify integrates by living *under* the AI assistant rather than as its own UI. Kevin Kinnett's review highlights that this works only as well as the assistant's ability to consume the resulting GRAPH_REPORT.md._
- _Version Control: Graph artifacts (HTML, JSON, report) are git-committable for team-wide use — explicit design choice, contrasted with Cody's remote-only indexing._
- _Build/install: Single `pip install graphifyy` plus a per-assistant skill registration. No daemon, no DB, no server. CodeGraphContext, FalkorDB, GitNexus, and Microsoft GraphRAG all require more infra._
- _Testing/QA: There is no published test harness or evaluation suite shipped with graphify; the published benchmark is a single mixed corpus (52 files, Karpathy repos + papers + images)._
- _Source: [graphify.net official site](https://graphify.net/), [graphifyy on PyPI](https://pypi.org/project/graphifyy/), [Releases page](https://github.com/safishamsi/graphify/releases)._

### Cloud Infrastructure and Deployment

Graphify is **strictly local-first**:

- Code never leaves the machine (deterministic AST pass).
- Audio/video transcribed locally via faster-whisper.
- Only **semantic descriptions** of docs/papers/images go to the configured LLM (Anthropic by default).
- Outputs sit in `graphify-out/`, can be checked into git, and queried offline.

This contrasts sharply with:
- **Sourcegraph Cody** — enterprise indexing service in the cloud, remote search API.
- **Microsoft GraphRAG** — designed around Azure OpenAI / OpenAI APIs and produces multi-GB Parquet artifacts; cost runs **$50–$200 per 10k-document indexing pass**, with four-figure bills on large corpora.
- **GitNexus** — runs entirely client-side in browser, zero-server, but loses the multi-modal pass.

For a homelab / privacy-leaning operator, graphify's threat model is favorable: it pairs cleanly with a local LLM (e.g., the `hybrid_gemma_serving` reasoner described in your project memory) for the AST/transcription passes, and only the multimodal-extract pass needs an external Anthropic call — and even that is replaceable in principle.

_Source: [Mustafa Genc — Build a Knowledge Graph From Your Entire Codebase Without Sending Your Code to Anyone](https://medium.com/@mustafa.gencc94/graphify-build-a-knowledge-graph-from-your-entire-codebase-without-sending-your-code-to-anyone-1b6924474b50), [paperclipped: Graph RAG in 2026 — Production cost analysis](https://www.paperclipped.de/en/blog/graph-rag-production/), [Sourcegraph Cody docs](https://sourcegraph.com/docs/cody)._

### Technology Adoption Trends

- _Migration Patterns: 2025-era pure-vector RAG → 2026-era **hybrid AST + LLM + graph traversal**. Aider's repo-map (PageRank over symbol graph) was an early signal; Microsoft GraphRAG validated the graph-summary approach; the arxiv:2601.08773 paper made AST-first the default for code._
- _Emerging Technologies: **MCP (Model Context Protocol) is now the de-facto integration bus** for code-graph tools (GitNexus, CodeGraphContext are MCP-first; graphify is "skill-first" per assistant — currently a different bet)._
- _Legacy Technology: Pure-vector codebase indexing (e.g., Continue's old @codebase, classic Cody embeddings) is being supplanted or augmented by graph approaches. Naive RAG remains fine for small homogeneous corpora._
- _Community Trends: As of April 2026, this category is **white-hot**: GitNexus hit #1 GitHub trending on April 10, 2026 with 1,195 stars in a single day; graphify reportedly crossed 22k stars in under 10 days after its April 3 release (one source cites 34.5k); code-review-graph, codegraph, CodeGraphContext, and FalkorDB CodeGraph are all 2026 entrants. Confidence on graphify's exact star count: **Medium** — figures from third-party blogs differ. Star count alone is also a weak quality signal in a hype cycle._
- _Source: [GitNexus #1 trending](https://blog.pebblous.ai/blog/gitnexus-code-knowledge-graph-2026/en/), [analyticsvidhya: From Karpathy's LLM Wiki to Graphify](https://www.analyticsvidhya.com/blog/2026/04/graphify-guide/), [arxiv:2601.08773 — Reliable Graph-RAG for Codebases](https://arxiv.org/abs/2601.08773)._

## Integration Patterns Analysis

> The "API surface" of a code-graph tool isn't HTTP — it's how it slots into AI coding assistants. Sections below adapt the template to that reality, while still covering protocols, formats, and interoperability per the workflow.

### API Design Patterns — Programmatic & Slash-Command Surfaces

Graphify exposes **four integration surfaces**, in increasing order of coupling:

1. **CLI** — `graphify <path>` (build), `graphify clone <repo>` (GitHub), `graphify merge-graphs` (cross-repo), `graphify query|path|explain` (graph traversal).
2. **Slash commands inside AI assistants** — `/graphify`, `/graphify query`, `/graphify path`, `/graphify explain`. These traverse `graph.json` hop-by-hop, returning relation type, confidence, source file, and source location.
3. **Library / programmatic** — `build_merge()` is the public entrypoint for safe incremental updates: loads existing graph, merges new chunks, optionally prunes deleted-file nodes, **never shrinks**. Idempotent, composable in CI.
4. **MCP stdio server (experimental)** — `graphify ./raw --mcp` exposes the graph over Model Context Protocol. **Open issue #146** is tracking native MCP integration with auto-refresh-on-file-change; until that ships, the MCP path is best treated as preview-quality.

- _RESTful APIs: Not provided by graphify. Equivalents (Sourcegraph Cody, GitNexus's hosted mode) do offer HTTP/GraphQL — useful at enterprise scale but unnecessary for a single-developer or single-team setup._
- _GraphQL APIs: Not used. Cody uses GraphQL for remote search; graphify's design rejects this in favor of local file traversal._
- _RPC/gRPC: Not used. MCP-stdio is the closest analog — a JSON-RPC-style protocol over stdio, designed for local agent processes._
- _Webhook/Event Patterns: Not native. Repo-change webhook → re-index would require external glue today; CodeGraphContext and GitNexus both have CI-side reindex hooks built in._
- _Source: [Graphify CLI Command Reference](https://graphify.net/graphify-cli-commands.html), [graphify README v4](https://github.com/safishamsi/graphify/blob/v4/README.md), [Issue #146 — native MCP integration](https://github.com/safishamsi/graphify), [Examples on how to use the Graphify Output (#69)](https://github.com/safishamsi/graphify/issues/69)._

### Communication Protocols

| Protocol | Graphify uses it? | Where? |
|---|---|---|
| **Local file I/O** | ✅ Primary | `graphify-out/` directory (graph.html / graph.json / GRAPH_REPORT.md) |
| **Anthropic API (HTTPS)** | ✅ For semantic-extraction pass on docs/papers/images | Subagents called in parallel |
| **MCP stdio** | ✅ Experimental | `--mcp` flag |
| **Claude Code hooks** | ✅ PreToolUse via settings.json | Fires before every Glob/Grep |
| **HTTP/REST** | ❌ | Not exposed |
| **WebSocket** | ❌ | Not used |
| **Message queues (AMQP/Kafka/MQTT)** | ❌ | Out of scope for indexer-style tool |

- _HTTP/HTTPS: Only outbound, only to the LLM provider. Inbound HTTP is intentionally absent — preserves the "no daemon" property._
- _WebSocket: Not used. Real-time UX is delegated to whichever AI assistant is hosting the slash command._
- _Message Queue Protocols: N/A for this category. Microsoft GraphRAG can be wired into pipelines (Azure Service Bus, etc.) at enterprise scale; graphify is intentionally simpler._
- _Hook protocol: Claude Code's PreToolUse/PostToolUse hooks are the de-facto "messaging" surface for AI-assistant tooling. Graphify uses PreToolUse only; GitNexus uses both (PreToolUse to enrich + PostToolUse to auto-reindex on commit) — that's a real product gap for graphify._
- _Source: [Hooks reference - Claude Code Docs](https://code.claude.com/docs/en/hooks), [Graphify + Claude Code Integration — Always-On Knowledge Graph](https://graphify.net/graphify-claude-code-integration.html), [GitNexus on MarkTechPost](https://www.marktechpost.com/2026/04/24/meet-gitnexus-an-open-source-mcp-native-knowledge-graph-engine-that-gives-claude-code-and-cursor-full-codebase-structural-awareness/)._

### Data Formats and Standards

Graphify's three output artifacts in `graphify-out/`:

| File | Format | Purpose | Consumed by |
|---|---|---|---|
| `graph.html` | Single-file HTML w/ vis.js | Interactive viz, share-by-email-friendly | Humans |
| `graph.json` | JSON (ad-hoc schema) | Source of truth, hop-by-hop traversable | LLM agents, CI, tools |
| `GRAPH_REPORT.md` | Markdown | "One-page architectural map": god nodes, communities, surprising connections, suggested questions | Claude/Cursor as `CLAUDE.md`-loaded prefix |

Edge attributes carried in `graph.json`: `relation_type`, `confidence` (`EXTRACTED`/`INFERRED`/`AMBIGUOUS`), `source_file`, `source_location`, plus `source_repo` after `merge-graphs`.

- _JSON: Primary. **Schema is ad-hoc and not formally documented** — a real interoperability concern; tools wanting to consume graph.json today should expect to read source. Compare to SCIP (Sourcegraph's open code-graph protocol, well-specified) and OpenAPI/AsyncAPI for general APIs._
- _Markdown: GRAPH_REPORT.md is the load-bearing artifact for Claude integration; **when it generates blank — as Kevin Kinnett's review reports — the whole workflow value drops off a cliff** (most-cited limitation in third-party reviews)._
- _HTML: Self-contained, git-committable, no JS bundler. Genuinely nice DX — mailing a `graph.html` to a colleague "just works"._
- _Binary serialization (Protobuf, MessagePack): Not used. The everything-is-JSON design fits the hackable / inspectable spirit but caps scaling. Microsoft GraphRAG ships Parquet-based artifacts for the same reason._
- _Source: [graphify.net — CLI Command Reference](https://graphify.net/graphify-cli-commands.html), [Kevin Kinnett's hands-on review](https://www.kevinkinnett.com/posts/graphify-review-claude-code-knowledge-graph/), [Graphify CLI Commands](https://graphify.net/graphify-cli-commands.html)._

### System Interoperability Approaches

**Two competing 2026 interoperability paradigms** for code-graph tools, and graphify currently bets primarily on the first:

#### A. "Skill / hook-per-assistant" (graphify's current default)

- One install command per assistant: `graphify claude install`, equivalents for Cursor / Codex / Copilot CLI / Aider / Hermes / etc. (15+ supported per README).
- Writes `CLAUDE.md` / equivalent + per-assistant hook config.
- **Pro**: Deep, opinionated integration with each tool's strengths (Claude Code skills are the deepest because the protocol exposes `PreToolUse`).
- **Con**: 15× the maintenance surface; each upstream tool change risks breaking integration; staleness is manual (no PostToolUse re-index today).

#### B. "MCP-first" (GitNexus, CodeGraphContext, hex-graph-mcp)

- Single MCP server; every MCP-capable assistant gets a uniform tool surface (`search_symbol`, `get_callers`, `find_path`, etc.).
- Graphify ships an MCP stdio server, but **issue #146 indicates the canonical/auto-refreshing version isn't done**.
- **Pro**: Write once, run on every MCP-capable client; future-proof as MCP becomes the standard.
- **Con**: Loses per-assistant niceties (hooks, slash-style ergonomics) unless the host wraps them.

The tide is moving toward MCP — DEV.to and morphllm's 2026 guides both flag this. Graphify's bet on per-assistant skills is currently paying off in mind-share (15+ integrations) but is the **single biggest medium-term architectural risk** I see.

- _Point-to-Point: Graphify-as-skill is point-to-point with each assistant; this works at small N (current state) but scales sublinearly._
- _API Gateway: The MCP server is effectively a "gateway" pattern: one process exposes many tools to many clients. This is the direction GitNexus and CodeGraphContext have committed to._
- _Service Mesh / ESB: Out of scope for an indexer; relevant only if you wire graphify into a CI/CD bus._
- _Source: [Claude Code Skills vs MCP Servers — DEV Community 2026](https://dev.to/williamwangai/claude-code-skills-vs-mcp-servers-what-to-use-how-to-install-and-the-best-ones-in-2026-548k), [Claude Code Memory vs MCP vs Skills — LaoZhang AI](https://blog.laozhang.ai/en/posts/claude-code-memory-vs-mcp-vs-skills), [Claude Code Skills vs MCP vs Plugins — morphllm](https://www.morphllm.com/claude-code-skills-mcp-plugins)._

### Microservices & Multi-Repo Integration Patterns

Graphify's multi-repo story is **the most differentiated piece of its 2026 roadmap**:

- `graphify clone <github_url>` — clones any public repo into `~/.graphify/repos/<owner>/<repo>` and runs the full pipeline.
- `graphify merge-graphs <a.json> <b.json> ... <out.json>` — merges N graphs into one, **tagging each node with its source repo**.
- Node-level `source_repo` lets queries like *"what does service-X call across our other repos?"* execute by graph traversal alone.

- _API Gateway pattern: N/A._
- _Service Discovery: Indirect — once you've merged graphs, cross-repo dependency edges are discoverable via traversal. This solves real polyrepo-pain that Cody/Aider only address via re-running search across multiple repos._
- _Circuit Breaker: N/A (offline tool)._
- _Saga / Distributed Transactions: N/A._
- _Comparison: Microsoft GraphRAG handles cross-source synthesis via "global community summaries" but is corpus-agnostic; graphify is the only tool I found with first-class **cross-repo merge** as a documented feature. **For your homelab + 3-repo `homelab/`/`homelab-bootstrap/`/`homelab-playbook/` topology, this is genuinely useful.**_
- _Source: [graphify README v4](https://github.com/safishamsi/graphify/blob/v4/README.md), [Releases page](https://github.com/safishamsi/graphify/releases), [Examples on how to use Graphify Output (#69)](https://github.com/safishamsi/graphify/issues/69)._

### Event-Driven Integration

Graphify is **fundamentally batch-oriented today**:

- _Publish-Subscribe: Not implemented. Graph staleness on file change is the most-cited operational complaint in user reviews; the workaround is `graphify <path>` re-runs (cheap due to SHA256 cache, but still manual)._
- _Event Sourcing: `build_merge()` provides "never-shrinks" semantics, which is event-sourcing-adjacent — good for incremental builds, but does not subscribe to a change stream._
- _Message Broker: Not used. GitNexus's PostToolUse-on-commit auto-reindex is a meaningful UX advantage today._
- _CQRS: Architecturally not a fit; queries and writes hit the same JSON file._
- _Where this matters: For a homelab with ~6 active repos, manual re-run is fine. For a 50-engineer team where the graph drifts within hours, this is a real gap; combine with a `pre-push` git hook or run nightly in CI._
- _Source: [Kevin Kinnett's review](https://www.kevinkinnett.com/posts/graphify-review-claude-code-knowledge-graph/), [GitNexus on MarkTechPost — auto-reindex on commit](https://www.marktechpost.com/2026/04/24/meet-gitnexus-an-open-source-mcp-native-knowledge-graph-engine-that-gives-claude-code-and-cursor-full-codebase-structural-awareness/)._

### Integration Security Patterns

- _OAuth 2.0 / JWT: Inherits from your AI provider's SDK (Anthropic key in env). No graphify-side auth surface to manage._
- _API Key Management: Graphify reads `ANTHROPIC_API_KEY` from environment. **Risk: a junior dev running `graphify` on a 1k-PDF research-paper folder can ring up a four-figure bill silently** — there is no documented spend cap or budget hook today._
- _Mutual TLS: N/A (no server)._
- _Data Encryption / Privacy boundary: This is graphify's strongest security story:_
  - Source code never leaves the machine (deterministic AST pass).
  - Audio/video transcribed locally via faster-whisper.
  - Only **semantic descriptions** of docs/papers/images go to the configured LLM.
  - This is materially better than Sourcegraph Cody's enterprise-indexer model, on par with GitNexus's all-local model, and far better than Microsoft GraphRAG's cloud-first design.
- _PyPI naming watch-out: The official package is **`graphifyy`** (double-y). There is also a `anytechie-graphify` package on PyPI; verify provenance before `pip install graphify` blindly. Supply-chain hygiene matters here — typosquatting is a known risk for fast-trending packages._
- _Source: [graphifyy on PyPI](https://pypi.org/project/graphifyy/), [anytechie-graphify (typosquat-watch)](https://pypi.org/project/anytechie-graphify/), [Mustafa Genc — privacy boundary article](https://medium.com/@mustafa.gencc94/graphify-build-a-knowledge-graph-from-your-entire-codebase-without-sending-your-code-to-anyone-1b6924474b50)._

## Architectural Patterns and Design

### System Architecture Patterns

Graphify is a **batch-oriented, three-pass pipeline** with a deliberately small dependency surface and no long-running services. Conceptually:

```
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│ Pass 1: AST      │ →  │ Pass 2: ASR      │ →  │ Pass 3: Semantic │
│ tree-sitter      │    │ faster-whisper   │    │ Claude subagents │
│ deterministic    │    │ local, cached    │    │ parallel, LLM    │
└──────────────────┘    └──────────────────┘    └──────────────────┘
              │                  │                       │
              ▼                  ▼                       ▼
        ┌──────────────────────────────────────────────────────┐
        │ NetworkX in-memory graph                              │
        │ + Leiden (graspologic) community detection            │
        │ + god-node detection (high-degree centrality)         │
        └──────────────────────────────────────────────────────┘
                                │
                                ▼
            ┌─────────────────────────────────────────┐
            │  graph.html  │  graph.json  │  REPORT.md │
            └─────────────────────────────────────────┘
```

**Pattern classification:**

- **Batch ETL pipeline** (Extract → Transform → Load), with the "load" target being on-disk JSON rather than a database. Closest precedent in the GraphRAG family: Microsoft GraphRAG, which is also a batch pipeline producing Parquet artifacts.
- **Layered processing with deterministic-first ordering** — codified separation of concerns: deterministic structural extraction precedes, and informs prompts for, the LLM-driven semantic pass. This is the same architectural insight validated by arxiv:2601.08773 (DKB > LLM-KB > vector-only on Java codebases).
- **No long-running services**: Stands in stark contrast to GitNexus (MCP server), CodeGraphContext (Neo4j daemon + MCP), Cody (remote indexer). Trade-off: zero-ops but no real-time updates.
- **Library + CLI hybrid** (`graphify <path>` + `from graphify import build_merge`). This dual-mode keeps it composable in CI while remaining one-shot-friendly.

**Architectural alternatives in the same problem-space:**

| Approach | Examples | When it wins |
|---|---|---|
| Batch pipeline → on-disk JSON | **Graphify**, codegraph (colbymchenry), code-review-graph | Solo dev / small team; privacy-first; git-committable artifacts |
| Long-running MCP server | GitNexus, CodeGraphContext, hex-graph-mcp | Live agentic workflows; auto-refresh on commit |
| Graph DB + query language | FalkorDB CodeGraph, Memgraph Graph-Code, Neo4j llm-graph-builder | Enterprise scale, Cypher queries, multi-million-node corpora |
| Hosted enterprise indexer | Sourcegraph Cody, Greptile | Multi-tenant, RBAC, large monorepos with code-search SLA |
| LLM-extracted KG (no AST) | Microsoft GraphRAG, LightRAG, nano-graphrag | Non-code corpora; global synthesis (community summaries) |
| Hybrid AST + LLM | **Graphify**, graphify-dotnet | Code + multi-modal docs; both deterministic and semantic edges |

_Source: [graphify ARCHITECTURE.md (v3)](https://github.com/safishamsi/graphify/blob/v3/ARCHITECTURE.md), [graphify.net — Tree-sitter AST Extraction](https://graphify.net/tree-sitter-ast-extraction.html), [arxiv:2601.08773](https://arxiv.org/abs/2601.08773), [paperclipped: Graph RAG in 2026 — Production](https://www.paperclipped.de/en/blog/graph-rag-production/)._

### Design Principles and Best Practices

Graphify embodies a set of design principles that match the 2026 GraphRAG-for-code consensus:

1. **Deterministic-first / LLM-second.** Code is parsed via tree-sitter; the LLM only handles non-code semantics. This is the load-bearing design choice — every third-party reviewer treats it as the right call. Validated by independent paper (arxiv:2601.08773): deterministic AST-derived graphs **outperformed** LLM-extracted KGs on multi-hop QA (15/15 vs 13/15 on Shopizer) at substantially lower indexing cost.
2. **Confidence as a first-class edge attribute.** `EXTRACTED` (deterministic) / `INFERRED` (LLM-suggested w/ score) / `AMBIGUOUS` (flagged for human review). Few competitors expose this; it is unusually honest UX for an LLM-augmented system.
3. **Local-first privacy boundary.** Source code never leaves the machine; only semantic descriptions of docs/papers/images do. Stronger than Cody, on par with GitNexus, far better than Microsoft GraphRAG.
4. **Composable artifacts.** HTML / JSON / Markdown — three forms, three consumers (humans / agents / LLM context window). Single-file outputs are git-committable and shareable, which the GraphRAG / Microsoft Parquet model is not.
5. **Progressive disclosure for the LLM.** GRAPH_REPORT.md is the "one-page architectural map" loaded into context; `graph.json` is the queryable substrate the agent traverses on demand. The agent shouldn't paste the whole graph into the prompt — it should hop. (Mirrors LightRAG's dual-level retrieval philosophy.)
6. **Domain-aware prompt construction.** Pass 2 (Whisper) uses a prompt derived from corpus god nodes, so transcription vocabulary fits the domain. This is a small but clever cross-pass feedback loop.

**Anti-patterns avoided (vs naive GraphRAG):**

- ❌ Embedding-similarity clustering on code (loses structural fidelity)
- ❌ LLM-only entity/relation extraction over source code (expensive, hallucination-prone — see arxiv:2601.08773 results)
- ❌ Requiring a graph DB for hello-world (graphify works zero-install)

**Anti-patterns present:**

- ⚠️ Schema-by-convention rather than spec (graph.json has no formal schema)
- ⚠️ Single-LLM-vendor concept extractor (Anthropic-shaped)
- ⚠️ Manual re-indexing (no PostToolUse refresh)

_Source: [graphify.net — Leiden Community Detection Without Embeddings](https://graphify.net/leiden-community-detection.html), [arxiv:2601.08773 — Reliable Graph-RAG for Codebases](https://arxiv.org/abs/2601.08773), [Memgraph — leiden_community_detection](https://memgraph.com/docs/advanced-algorithms/available-algorithms/leiden_community_detection), [Mustafa Genc on privacy](https://medium.com/@mustafa.gencc94/graphify-build-a-knowledge-graph-from-your-entire-codebase-without-sending-your-code-to-anyone-1b6924474b50)._

### Scalability and Performance Patterns

#### Indexing scalability (build time)

- **First run is the cost spike.** Reviewers report several minutes for a 200k-LOC codebase. Subsequent runs are fast thanks to **SHA256 file-content caching** + `build_merge()` semantics. Reasonable for solo / small-team scale.
- **API-cost ceiling.** A folder with hundreds of PDFs/images can drive Anthropic spend into the four-figure range. No documented spend cap, no `--max-cost` flag. This is the **biggest operational risk** today; for comparison, Microsoft GraphRAG bills similarly ($50–$200 per 10k-document indexing) per paperclipped.de. LightRAG runs at roughly **1/100th** of GraphRAG's cost for 70–90% of the quality on knowledge-corpora tasks.

#### Query scalability (run time)

- **NetworkX is the hard ceiling.** NetworkX stores graphs in Python dicts at ~100 B per edge. 30M edges ≈ 40 GB RAM. Above hundreds of thousands of nodes, common centrality / pathfinding algorithms slow dramatically — Neo4j GDS clocked harmonic centrality on a real graph in **14 s vs NetworkX's 1 h 6 min** in one published benchmark.
- **For homelab-scale (a few-thousand-LOC codebases + a few-hundred docs): NetworkX is fine and fast.**
- **For monorepo-scale (millions of LOC) or multi-million-node KGs: graphify's NetworkX choice becomes the bottleneck.** Alternatives: FalkorDB CodeGraph, Memgraph Graph-Code, or Neo4j-backed Microsoft GraphRAG forks.

#### Distributed / horizontal scaling

- Graphify is **single-process by design**. Pass 3 (Claude subagents) runs in parallel inside one machine but is not multi-host.
- Cross-repo work is achieved via **`graphify merge-graphs`** (one node-tag per repo), which scales linearly with #repos and does not require a distributed runtime.

#### Performance optimisations Graphify ships

- SHA256 content cache (skip unchanged files)
- Parallel Claude subagents (Pass 3)
- Topology-only Leiden (no embedding generation)
- Deterministic-first (skips LLM entirely for code)
- Domain-aware Whisper prompt (better transcripts → cheaper later passes)

_Source: [Memgraph — Biggest NetworkX Challenges](https://memgraph.com/blog/data-persistency-large-scale-data-analytics-and-visualizations-biggest-networkx-challenges), [Towards Data Science — Neo4j vs NetworkX centrality benchmark](https://towardsdatascience.com/fire-up-your-centrality-metric-engines-neo4j-vs-networkx-a-drag-race-of-sorts-18857f25be35/), [paperclipped.de — Production cost analysis](https://www.paperclipped.de/en/blog/graph-rag-production/), [Quasilinear Musings — Graph package benchmark](https://www.timlrx.com/blog/benchmark-of-popular-graph-network-packages/), [NVIDIA blog — GPU-accelerated Leiden](https://developer.nvidia.com/blog/how-to-accelerate-community-detection-in-python-using-gpu-powered-leiden/)._

### Integration and Communication Patterns

(Covered in depth in *Integration Patterns Analysis* above — short summary here for completeness.)

- **Slash-command hosted by AI assistant** — primary surface (`/graphify ...`)
- **PreToolUse hook** — intercepts every Glob/Grep, prepends graph context
- **CLAUDE.md / equivalent directive** — long-term memory injection so the assistant always knows about the graph
- **Library API** — `build_merge()` for incremental builds in CI
- **MCP stdio (preview)** — single tool surface for any MCP client (auto-refresh tracked in #146)

The **architectural bet**: skill-per-assistant ergonomics over MCP uniformity. This is the largest single architectural risk vs trend (MCP-first is winning per DEV.to / morphllm 2026 guides), and the largest current advantage (Claude Code PreToolUse hook is genuinely the best UX in this category).

_Source: [DEV.to — Claude Code Skills vs MCP Servers 2026](https://dev.to/williamwangai/claude-code-skills-vs-mcp-servers-what-to-use-how-to-install-and-the-best-ones-in-2026-548k), [morphllm — Claude Code Skills vs MCP vs Plugins](https://www.morphllm.com/claude-code-skills-mcp-plugins), [Hooks reference - Claude Code Docs](https://code.claude.com/docs/en/hooks)._

### Security Architecture Patterns

| Surface | Graphify pattern | Risk profile |
|---|---|---|
| Source code exposure | **Never sent off-machine** (deterministic AST) | ✅ Strong |
| Audio/video exposure | **Never sent off-machine** (faster-whisper local) | ✅ Strong |
| Document/image content | **Semantic descriptions only** to configured LLM | ⚠️ Depends on LLM provider's data policy |
| API key handling | Reads `ANTHROPIC_API_KEY` from env | ⚠️ Standard; risk of accidental check-in |
| Spend control | None documented | ❌ Missing — adopters should add budget guard |
| Supply-chain | PyPI namespace `graphifyy` (double-y); `anytechie-graphify` exists separately | ⚠️ Verify before installing |
| Output artifacts in git | HTML/JSON/MD git-committable; no secrets by design | ✅ Safe IF you don't run on a folder containing secrets |

**Comparison with alternatives:**

- **Sourcegraph Cody (enterprise)**: Source code is ingested into Sourcegraph's cloud index — strict opposite of graphify's threat model.
- **Microsoft GraphRAG**: Cloud-first by default; entity extraction sends content to OpenAI/Azure OpenAI.
- **GitNexus**: Browser-side parsing — never leaves the client. Comparable to graphify on privacy.
- **CodeGraphContext / FalkorDB**: Local indexing, but require a daemon/server and inherit its attack surface.

_Source: [Mustafa Genc — Without Sending Your Code to Anyone](https://medium.com/@mustafa.gencc94/graphify-build-a-knowledge-graph-from-your-entire-codebase-without-sending-your-code-to-anyone-1b6924474b50), [Sourcegraph Cody docs](https://sourcegraph.com/docs/cody), [paperclipped — Production cost](https://www.paperclipped.de/en/blog/graph-rag-production/), [graphifyy PyPI](https://pypi.org/project/graphifyy/)._

### Data Architecture Patterns

- **Single-source-of-truth on disk**: `graph.json` is canonical; `graph.html` and `GRAPH_REPORT.md` are derived views. Clean architecture: derived artifacts can be regenerated.
- **Append-only / never-shrinks build**: `build_merge()` is monotonic by default — additions and updates only, with optional pruning of deleted-file nodes. Event-sourcing-like, friendly to incremental CI runs.
- **Hop-by-hop traversal model**: The graph is *not* meant to be pasted into a prompt; agents walk it. This is structurally similar to LightRAG's dual-level retrieval and Microsoft GraphRAG's "local search" mode.
- **Topology-only clustering** (no embeddings): Leiden via graspologic. Reproducible and cheap, but cannot retrieve "semantically similar but never-linked" nodes — a real limitation when the user's query crosses corpus areas that the graph doesn't connect via explicit edges.
- **God-node detection**: High-centrality nodes surface as an attention prior — used to (a) seed the GRAPH_REPORT.md "important concepts" section and (b) bias the Pass-2 Whisper prompt. Cute architectural touch.

**Where this hurts:** if you ask a question whose answer depends on a "soft semantic" edge that no extractor created, graphify won't synthesize it the way a vector-RAG-or-LightRAG hybrid would. For the user's homelab/code use case this is rarely the dominant query type, but it's worth knowing.

_Source: [graphify.net — Leiden without embeddings](https://graphify.net/leiden-community-detection.html), [LightRAG paper / blog](https://learnopencv.com/lightrag/), [graphify Examples #69](https://github.com/safishamsi/graphify/issues/69)._

### Deployment and Operations Architecture

- **Zero-deploy.** `pip install graphifyy` (or `uv tool install graphifyy`); run `graphify <path>`. No daemon, no DB, no container.
- **CI integration.** Trivial: invoke `graphify` in a job, commit the artifacts, or upload them to artifact storage. Several reviewers describe this as the "killer feature" for team workflows.
- **Re-index trigger.** Manual today (or wrap with `git pre-push` / nightly cron). GitNexus's PostToolUse-on-commit auto-reindex is the operational benchmark to beat.
- **Cost/observability.** No built-in spend tracking, no metrics endpoint. Roll your own (e.g., wrap in a script that captures Anthropic usage from response headers; or use LiteLLM as a gateway and budget there — your `hybrid_gemma_serving` plan already has LiteLLM in scope, which would let you both budget *and* swap providers).
- **Disaster recovery.** Trivial — `graphify-out/` is regenerable from source. Lose it, re-run.

_Source: [Graphify CLI Command Reference](https://graphify.net/graphify-cli-commands.html), [Graphify + Claude Code Integration](https://graphify.net/graphify-claude-code-integration.html), [GitNexus on MarkTechPost — auto-reindex](https://www.marktechpost.com/2026/04/24/meet-gitnexus-an-open-source-mcp-native-knowledge-graph-engine-that-gives-claude-code-and-cursor-full-codebase-structural-awareness/), [paperclipped — operations cost analysis](https://www.paperclipped.de/en/blog/graph-rag-production/)._

## Implementation Approaches and Technology Adoption

### Technology Adoption Strategies

#### Where graphify sits in the 2026 adoption curve

- **April 3, 2026 release** → reportedly 22k+ stars in 10 days (one source 34.5k). Confidence on exact star count: **Medium** — third-party blogs disagree; treat directionally.
- Native integrations in 15+ AI assistants (Claude Code, Codex, Cursor, Gemini CLI, Copilot CLI, VS Code Copilot Chat, Aider, OpenClaw, Factory Droid, Trae, Hermes, Kiro, Google Antigravity, OpenCode).
- Karpathy's "LLM Wiki" idea is the cultural anchor — the maintainer explicitly framed graphify as that wiki materialized.
- Direct competitors **also** have meaningful share: GitNexus (28k+ stars), CodeGraphContext (2.2k stars / 100k+ downloads / MIT).
- This is **a hype-cycle peak** for code-graph tooling. Star counts are noisy; commit cadence, issue-resolution, and third-party reproductions matter more.

#### Rational adoption strategies for graphify (ranked)

1. **Pilot pattern (recommended)** — Pick *one* project (your `homelab-playbook` would be ideal: rich docs + code + the sprawl benefits most). Run `graphify clone` (or local `graphify <path>`), inspect `GRAPH_REPORT.md`. If it's blank or shallow, rerun (a known intermittent fault) before forming a verdict.
2. **Always-on pattern** — For your daily-driver repo, run `graphify claude install` to wire the PreToolUse hook. Schedule a nightly cron-driven `graphify <path>` to refresh.
3. **Multi-repo polyrepo pattern** — For your `homelab/` + `homelab-bootstrap/` + `homelab-playbook/` + project-CT containers, run `graphify clone` per repo, then `graphify merge-graphs` to surface cross-repo dependencies. **This is the use case where graphify's design is most differentiated**.
4. **Avoid the "ship it to the whole team on day one" pattern** — first-run cost on PDF/image-heavy folders can be four-figure spend; review-quality of `GRAPH_REPORT.md` is intermittent.

#### Migration patterns from / to alternatives

| If you're coming from … | Migration to graphify | Migration *away* if graphify disappoints |
|---|---|---|
| Plain Aider repo-map | **Easy** — graphify's GRAPH_REPORT.md is a strict superset of repo-map | → CodeGraphContext (similar zero-server model + Neo4j depth) |
| Sourcegraph Cody | **Hard if you want hosted RBAC**; **easy if you want privacy** | → Stay on Cody (enterprise UX still wins) |
| Microsoft GraphRAG / LightRAG | **Easy for the multimodal pass**; **hard if you need community summaries / global synthesis** | → LightRAG (1/100th cost, 70-90% quality) |
| Nothing (greenfield) | **Easy** — `pipx install graphifyy && graphify .` | → GitNexus (MCP-first, browser-side) |

_Source: [analyticsvidhya — From Karpathy's LLM Wiki to Graphify](https://www.analyticsvidhya.com/blog/2026/04/graphify-guide/), [GitNexus on MarkTechPost](https://www.marktechpost.com/2026/04/24/meet-gitnexus-an-open-source-mcp-native-knowledge-graph-engine-that-gives-claude-code-and-cursor-full-codebase-structural-awareness/), [Ry Walker Research — CodeGraphContext](https://rywalker.com/research/codegraphcontext), [Ry Walker — Code Intelligence Tools Compared](https://rywalker.com/research/code-intelligence-tools)._

### Development Workflows and Tooling

#### Day-1 install (Claude Code path — most relevant to your stack)

```bash
# install
uv tool install graphifyy
# or: pipx install graphifyy
# or: pip install graphifyy

# build the graph (one-shot)
cd ~/workspace/homelab
graphify .

# wire into Claude Code (writes CLAUDE.md + PreToolUse hook)
graphify claude install

# inspect outputs
ls graphify-out/
# graph.html  graph.json  GRAPH_REPORT.md
```

#### Cross-repo workflow

```bash
graphify clone https://github.com/yourorg/homelab           --out ./out/homelab.json
graphify clone https://github.com/yourorg/homelab-bootstrap --out ./out/bootstrap.json
graphify clone https://github.com/yourorg/homelab-playbook  --out ./out/playbook.json
graphify merge-graphs ./out/*.json --out ./out/merged.json
# query with source_repo node attribute
```

#### CI workflow (GitHub Actions example)

```yaml
- name: Refresh knowledge graph
  run: |
    pipx install graphifyy
    graphify .
- name: Commit graph artifacts
  run: |
    git add graphify-out/
    git commit -m "chore: refresh knowledge graph" || true
    git push
```

#### Daily developer ergonomics

- Treat `GRAPH_REPORT.md` as a "team architecture cheat-sheet". Read it on Monday. If it's drifted, re-run.
- Slash-commands inside Claude Code: `/graphify query`, `/graphify path X Y`, `/graphify explain N`. Treat these as you would `grep` / `git log` — short tactical operations.
- Re-run trigger: pre-push git hook OR nightly cron. **Manual re-run is the ergonomic gap.**

_Source: [Graphify CLI Command Reference](https://graphify.net/graphify-cli-commands.html), [Graphify + Claude Code Integration](https://graphify.net/graphify-claude-code-integration.html), [Mustafa Genc — Build a Knowledge Graph](https://medium.com/@mustafa.gencc94/graphify-build-a-knowledge-graph-from-your-entire-codebase-without-sending-your-code-to-anyone-1b6924474b50), [graphifyy on PyPI](https://pypi.org/project/graphifyy/)._

### Testing and Quality Assurance — Benchmarks Cross-Reference

#### Self-reported claims (graphify)

- **71.5× fewer tokens per query** vs reading raw files, on a 52-file mixed corpus: Karpathy's nanoGPT/minGPT/micrograd repos + "Attention is All You Need" / FlashAttention papers + images. The first run pays a one-time graph-build cost; every subsequent query reads the compact graph.
- **Confidence: Low–Medium.** The corpus is small, mixed (code + papers + images), and chosen by the maintainer. *No third-party reproduction has been published.*

#### Independent third-party benchmark — code-review-graph (Tirth Kanani, March 2026)

Methodology that *is* well-controlled, on **3 production OSS repos with real commits**:

| Repo | Files | Token reduction (review) |
|---|---|---|
| httpx | 125 | **26.2×** |
| FastAPI | 2,915 | **8.1×** |
| Next.js | 27,732 | **6.0×** |
| Avg (review) | — | **6.8×** |
| Daily coding (Next.js monorepo) | 27,732 | **up to 49×** |
| Review quality (10-pt) | — | 8.8 (with graph) vs 7.2 (without) |

**Implication for graphify**: Token-reduction factor scales **inversely with repo size** in code-review-graph's data. A 71.5× claim on a 52-file corpus is consistent with what you'd see at *that* scale — but expect graphify on a 27k-file repo to deliver something closer to 6–10× on real-world coding queries, not 71.5×. The order of magnitude advertised is plausible only on small, mixed corpora with high cross-doc structure.

#### Independent third-party benchmark — arxiv:2601.08773 (Jan 2026)

On Java / Shopizer multi-hop QA:
- AST-derived KG (DKB): **15/15** correct
- LLM-extracted KG: **13/15** correct (+ 2 partial)
- Vector-only RAG: **6/15** correct

**Implication for graphify**: Validates the *category* and graphify's deterministic-AST-first design choice, even though graphify itself isn't tested. AST-first is the right architecture; graphify implements it correctly.

#### Quality issues reported by reviewers

- **`GRAPH_REPORT.md` blank-output bug**: Kevin Kinnett reports the report came out blank on a real run, despite the graph itself being built. Workflow value collapses when this happens. (Most-cited concrete failure mode.)
- **Claude-only semantic pass**: If your assistant uses GPT-4 / Gemini / Llama, the most powerful pass is degraded or unusable.
- **No published test suite** shipped with graphify; benchmark is a single corpus.

_Source: [code-review-graph README — methodology table](https://github.com/tirth8205/code-review-graph), [Innovatrix — How code-review-graph cuts tokens 49×](https://www.innovatrixinfotech.com/blog/code-review-graph-claude-code-token-usage-reduction), [DEV.to — How code-review-graph Cuts Claude Code Token Usage 49×](https://dev.to/emperorakashi20/how-code-review-graph-cuts-claude-code-token-usage-by-49x-and-whether-its-actually-worth-it-4kn1), [Tirth Kanani's blog — I Built a Knowledge Graph that cuts 49×](https://tirthkanani18.medium.com/i-built-a-knowledge-graph-that-cuts-claude-codes-token-usage-by-49x-9260d3cd1069), [arxiv:2601.08773](https://arxiv.org/abs/2601.08773), [Kevin Kinnett's review](https://www.kevinkinnett.com/posts/graphify-review-claude-code-knowledge-graph/), [analyticsvidhya — From Karpathy's LLM Wiki to Graphify](https://www.analyticsvidhya.com/blog/2026/04/graphify-guide/)._

### Deployment and Operations Practices

- **Deploy unit**: a single Python tool. No daemon, no DB, no ports.
- **Operational footprint**: per-run RAM proportional to graph size; per-run cost proportional to non-code tokens × LLM rate.
- **Failure modes seen in the wild**: blank `GRAPH_REPORT.md`; long first-run on big repos; intermittent Anthropic rate-limit hits during Pass 3.
- **Observability**: none built-in. Use `litellm` proxy or Anthropic's Usage/Cost API as a wrapper.
- **Re-index**: the operational pain point. Recommend: nightly cron in CI for the always-current pattern; or `pre-push` hook for the eager pattern.

_Source: [Anthropic Usage and Cost API docs](https://platform.claude.com/docs/en/build-with-claude/usage-cost-api), [Kevin Kinnett's review](https://www.kevinkinnett.com/posts/graphify-review-claude-code-knowledge-graph/), [GitNexus auto-reindex on commit](https://www.marktechpost.com/2026/04/24/meet-gitnexus-an-open-source-mcp-native-knowledge-graph-engine-that-gives-claude-code-and-cursor-full-codebase-structural-awareness/)._

### Team Organization and Skills

- **Adoption skill curve**: Low. `pipx install graphifyy && graphify .` — anyone on the team can run it on day 1.
- **Power-user skill curve**: Medium. To debug a poor `GRAPH_REPORT.md` you need to read `graph.json` (undocumented schema). To extend it (e.g., add a new edge type) you need NetworkX + tree-sitter familiarity.
- **Roles**: For a homelab/solo-dev profile (your context), no team coordination needed. For a 5-person team, designate one "graph maintainer" who owns the nightly job and fields questions about the graph schema.
- **Learning resources**: graphify.net's docs are reasonable; `ARCHITECTURE.md` in the repo is the best architectural source. The Mustafa Genc / Pankaj / Kevin Kinnett / Aniket Sinare blog posts (April 2026) give realistic hands-on perspective.

_Source: [graphify ARCHITECTURE.md](https://github.com/safishamsi/graphify/blob/v3/ARCHITECTURE.md), [Mustafa Genc on GoPenAI](https://medium.com/@mustafa.gencc94/graphify-build-a-knowledge-graph-from-your-entire-codebase-without-sending-your-code-to-anyone-1b6924474b50), [Pankaj on Medium — Navigate by Structure, Not Similarity](https://medium.com/@pankaj_pandey/graphify-navigate-our-codebase-by-structure-not-similarity-eb773c4e9871), [Aniket Sinare — Stop Reading Code, Start Seeing It](https://medium.com/@aniketsinare/stop-reading-code-start-seeing-it-visualizing-your-codebase-with-graphify-vis-js-bdef82ad6050)._

### Cost Optimization and Resource Management

#### Per-run cost model (April 2026 Anthropic pricing)

- Sonnet 4.6: **$3/MTok input, $15/MTok output** (typical default for graphify subagents).
- Haiku 4.5: $1/$5 (cheaper but lower extraction quality for nuanced docs).
- Opus 4.6: $5/$25 (overkill for extraction).

#### Order-of-magnitude estimates (rough, build-time only)

| Corpus | Token estimate | Sonnet cost (build-only) |
|---|---|---|
| 50-file mixed (Karpathy-corpus-like) | ~200k input, ~50k output | **~$1.35** |
| 500 PDFs (research-paper folder) | ~50M input, ~5M output | **~$225** |
| 5k PDFs + images (lab archive) | ~500M input, ~50M output | **~$2,250** |

Code is **free** (deterministic AST), so a code-only repo of any size costs ~$0 in graphify build. The cost ceiling is entirely in the multi-modal pass.

#### Built-in cost optimisations

- **SHA256 cache** — only changed files re-extracted. After day 1, costs collapse.
- **Parallel subagents** — wall-clock optimisation, doesn't reduce token spend.
- **`build_merge()` semantics** — incremental, idempotent.

#### Optimisations you should add

- Wrap graphify in a script that reads Anthropic's **Usage & Cost API** (`/v1/organizations/usage_report/messages`) and aborts if a spend ceiling is hit. Trivial guardrail.
- Use **prompt caching** if you control subagent prompts — 90% off cached input.
- Use **Anthropic Message Batches API** for offline extraction passes — **50% off** at the cost of ≤24h latency.
- Use a **LiteLLM gateway** (already in scope per your `hybrid_gemma_serving` plan) — lets you swap to Haiku for the bulky doc pass and Sonnet for high-value rationale extraction, AND adds budget controls graphify lacks natively.

_Source: [Anthropic API Pricing 2026 — Finout](https://www.finout.io/blog/anthropic-api-pricing), [Anthropic API Docs — Pricing](https://platform.claude.com/docs/en/about-claude/pricing), [Anthropic API Docs — Usage and Cost API](https://platform.claude.com/docs/en/build-with-claude/usage-cost-api), [paperclipped — Production cost comparison MS GraphRAG vs LightRAG](https://www.paperclipped.de/en/blog/graph-rag-production/)._

### Risk Assessment and Mitigation

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Hype-cycle abandonment (one-developer project loses momentum mid-2026) | Medium | High | Treat outputs (graph.json) as portable. Keep an exit plan to GitNexus / CodeGraphContext. |
| `GRAPH_REPORT.md` blank-output bug | Medium | Medium | Re-run; verify report has content before relying on Claude's PreToolUse-injected guidance. |
| MCP-first ecosystem leaves skill-first behind | Medium | Medium | Watch issue #146; if MCP support stalls, lean toward GitNexus or hex-graph-mcp. |
| Anthropic-only semantic pass | High | Medium for non-Anthropic users | Use LiteLLM gateway to route to Anthropic for the semantic pass; AST/Whisper passes are vendor-neutral. |
| Cost runaway on large multi-modal corpora | Medium | High (financial) | Add spend cap wrapper (Anthropic Usage API). |
| Schema drift in graph.json across versions | Medium | Medium | Pin `graphifyy` version in CI; treat schema as private; test downstream consumers on upgrade. |
| PyPI typosquat (`anytechie-graphify` exists) | Low | High (supply-chain) | Always install `graphifyy` (double-y). Verify SHA in CI. |
| NetworkX scaling ceiling | Low for homelab; high for monorepo | High at scale | If your repos exceed ~hundreds of thousands of nodes, plan migration to FalkorDB / Memgraph / Neo4j. |
| 71.5× claim doesn't reproduce in your environment | High | Low (still useful) | Set realistic expectation: ~5–10× on real medium-size repos based on code-review-graph data. |

_Source: [GitNexus on MarkTechPost](https://www.marktechpost.com/2026/04/24/meet-gitnexus-an-open-source-mcp-native-knowledge-graph-engine-that-gives-claude-code-and-cursor-full-codebase-structural-awareness/), [code-review-graph methodology](https://github.com/tirth8205/code-review-graph), [Anthropic Cost API](https://platform.claude.com/docs/en/build-with-claude/usage-cost-api), [Memgraph NetworkX scaling article](https://memgraph.com/blog/data-persistency-large-scale-data-analytics-and-visualizations-biggest-networkx-challenges)._

---

## Technical Research Recommendations

### Implementation Roadmap

**Phase 0 — Sandbox evaluation (1 evening)**

1. `pipx install graphifyy` on your dev workstation (NOT in `ct-ai-01` yet).
2. Run `graphify ~/workspace/homelab` — wait ~5–10 min.
3. Open `graphify-out/graph.html` in a browser; read `GRAPH_REPORT.md`.
4. Verdict gate: does the report read like a useful architecture cheat-sheet, or is it shallow / blank? **If blank, re-run once before forming a verdict.**

**Phase 1 — Pilot integration (1–2 days)**

5. If Phase 0 is positive, run `graphify claude install` in the same repo.
6. Use Claude Code for one real task that benefits from architecture awareness (a refactor, an "explain how X talks to Y", or onboarding-style question).
7. Compare: did Claude pull the right context faster than without graphify? Did it cite GRAPH_REPORT.md?
8. Verdict gate: is the workflow value worth ~$1–5 / re-index?

**Phase 2 — Multi-repo merge (½ day)**

9. `graphify clone` for `homelab/`, `homelab-bootstrap/`, `homelab-playbook/`, and the project containers (`ct-ai-01`, `ct-sparkle-cps`, `ct-quant-trading`).
10. `graphify merge-graphs` to produce a single cross-repo graph.
11. Use this for an "ecosystem-wide" question: e.g., *"which playbook touches CT 162's storage path?"* — the answer should fall out of graph traversal.

**Phase 3 — Operationalisation (1 day)**

12. Wire a nightly cron (in `ct-ai-01` or a small playbook job) that runs `graphify` on each tracked repo and commits the artifacts.
13. Add a budget guardrail: a wrapper script that polls Anthropic's Usage & Cost API and aborts if spend exceeds your monthly cap.
14. Decide: stay on graphify, OR re-evaluate against GitNexus (MCP-first) / CodeGraphContext (Neo4j-first) / code-review-graph (review-focused).

**Phase 4 — Re-evaluation gate (8 weeks out — 2026-06-20)**

15. Has issue #146 (proper MCP support) shipped? If yes, the architectural risk drops sharply.
16. Has the `GRAPH_REPORT.md` blank-bug been fixed?
17. Are there independent benchmark reproductions of the 71.5× claim?
18. Is the maintainer still active (commit cadence, issue triage)?
19. Decision: keep / migrate / wrap with LiteLLM and continue.

### Technology Stack Recommendations

For your homelab + dev-assistant setup, the recommended stack:

- **Primary code-graph tool: graphify** (`graphifyy`) — *with* the caveats below.
- **Evaluation peer: code-review-graph** (`tirth8205/code-review-graph`) — better-validated benchmarks; useful as a sanity check, possibly as a daily-driver for *review* tasks if graphify's general-purpose graph doesn't pay off.
- **Strategic alternative to monitor: GitNexus** — MCP-first, similar privacy posture; the right next jump if graphify's per-assistant skills lag the ecosystem.
- **Enterprise/scale alternative: CodeGraphContext** — when (if) you outgrow NetworkX or want Cypher.
- **Multi-modal RAG complement: LightRAG** — for non-code corpora, where graphify's design is overkill and LightRAG's 1/100th-cost claim makes it the right fit.
- **LLM gateway: LiteLLM** (already in your `hybrid_gemma_serving` plan) — wrap graphify's subagent calls so you can swap providers, budget, and observe.
- **Local LLM substrate: your Unsloth UD-Q5_K_M Gemma reasoner** — useful for the AST/transcription passes; the Pass-3 semantic step probably still wants Claude unless you can swap to a stronger local model.

### Skill Development Requirements

- **Operational (essential)**: tree-sitter language detection, NetworkX basics, JSON schema reading.
- **Diagnostic (valuable)**: Leiden community detection intuition, cost-API integration with Anthropic.
- **Strategic (when relevant)**: MCP server development (for the day you might want to write a custom MCP wrapper around graphify's outputs).

### Success Metrics and KPIs

For your evaluation, measure (over 4 weeks):

| Metric | Target | Tool |
|---|---|---|
| Token reduction on real Claude Code tasks | ≥ 5× on small repos / ≥ 2× on big repos | Compare prompt size with vs without graphify hook |
| Re-index time after a typical commit | < 30 s | `time graphify .` |
| Anthropic spend per repo per month | < $20 (homelab cap) | Anthropic Usage API |
| `GRAPH_REPORT.md` non-blank rate | 100% | manual / `wc -l` check |
| Number of "good catches" (bugs / dependencies surfaced via graph) | ≥ 3 over 4 weeks | qualitative log |
| Claude Code agentic workflow success-rate uplift | qualitative ≥ "noticeable" | personal judgement |

If after 4 weeks you have ≥ 4 of 6 green, keep graphify; otherwise migrate to one of the alternatives above.

_Source: [Anthropic Usage & Cost API](https://platform.claude.com/docs/en/build-with-claude/usage-cost-api), [code-review-graph methodology](https://github.com/tirth8205/code-review-graph), [Ry Walker — Code Intelligence Tools Compared](https://rywalker.com/research/code-intelligence-tools), [Mustafa Genc on GoPenAI](https://medium.com/@mustafa.gencc94/graphify-build-a-knowledge-graph-from-your-entire-codebase-without-sending-your-code-to-anyone-1b6924474b50)._

---

# Graphify in 2026: A Multimodal Knowledge-Graph Generator at the Peak of Code-Graph Hype — Comprehensive Technical Research

## Executive Summary

In April 2026, the code-knowledge-graph category went from niche to white-hot. **Graphify**, released on April 3, 2026 by @safishamsi as the materialization of Andrej Karpathy's "LLM Wiki" idea, is one of the most visible entrants — reportedly crossing 22k+ stars in under ten days, with native integrations into 15+ AI coding assistants (Claude Code, Cursor, Codex, Gemini CLI, Copilot CLI, Aider, and more). It compresses any folder of code, docs, papers, images, or audio/video into a queryable knowledge graph stored as a single JSON file and rendered as an interactive HTML viz, with a one-page Markdown "architecture cheat-sheet" injected into your AI assistant's context via a Claude Code `PreToolUse` hook.

The architectural call graphify makes — **deterministic AST-first for code, LLM-second for docs/images, topology-only Leiden clustering, no graph database** — is independently validated by arxiv:2601.08773 (Jan 2026), which showed AST-derived KGs hit 15/15 on Java multi-hop QA versus LLM-extracted KGs at 13/15 and vector-only RAG at 6/15. Its multi-modal pipeline (tree-sitter + faster-whisper + Claude subagents) is genuinely differentiated — **no other tool in the 2026 landscape matches end-to-end on code + papers + audio + video + images** — and the multi-repo merge workflow (`graphify clone` + `graphify merge-graphs`) is uniquely well-aligned with polyrepo topologies like tomamourette's homelab.

The headline **71.5× fewer tokens per query** claim is real-but-narrow. It was measured on a 52-file mixed corpus (Karpathy's nanoGPT/minGPT/micrograd + "Attention is All You Need" + FlashAttention + a handful of images). Independent benchmarks from a methodologically tighter peer tool (code-review-graph, March 2026) measure token-reduction *across repository sizes* and find it **scales inversely with size**: 26.2× at 125 files (httpx) → 8.1× at 2,915 files (FastAPI) → 6.0× at 27,732 files (Next.js). On a mid-size real repo, plan for 5–10× reduction, not 71.5×. The order of magnitude is still useful — but treat the README number as marketing-grade, not specification-grade.

The biggest risks today are (1) **batch-only re-indexing** (no PostToolUse hook; GitNexus already has this), (2) the **MCP-vs-skill ecosystem fork** — graphify is currently skill-first across 15 assistants while GitNexus, CodeGraphContext, and hex-graph-mcp are MCP-first and tracking the 2026 standard better, (3) **single-vendor LLM** for the semantic pass (Anthropic), and (4) **no built-in spend cap** — a junior developer running graphify on a thousand-PDF research folder can ring up a four-figure Anthropic bill silently. None of these are fatal; all are addressable.

**Key Technical Findings:**

- **Architectural choices are validated**: Deterministic AST-first beats LLM-only KG extraction on Java code multi-hop QA in independent peer-reviewed work (15/15 vs 13/15 vs 6/15 on Shopizer per arxiv:2601.08773); graphify implements this pattern correctly.
- **Multi-modal is the genuine differentiator**: code + Markdown + PDF + image + audio + video in one graph is a category-of-one feature; nearest peers (GitNexus, CodeGraphContext, code-review-graph) are code-only.
- **The 71.5× claim doesn't generalise**: Independent peer benchmarks (code-review-graph, 3-repo study) show 26.2× → 8.1× → 6.0× as repo size grows. Plan for 5–10× on real medium-size repos.
- **Privacy posture is strong**: source code never leaves the machine; audio/video transcribed locally; only semantic descriptions of docs/papers/images go to the configured LLM. Materially better than Sourcegraph Cody / Microsoft GraphRAG.
- **Multi-repo merge is uniquely valuable** for polyrepo setups (per-node `source_repo` tag enables cross-repo queries). Directly relevant to your `homelab/` + `homelab-bootstrap/` + `homelab-playbook/` + project-container topology.
- **Operational gaps are concrete**: blank `GRAPH_REPORT.md` bug (Kevin Kinnett), no PostToolUse re-index, undocumented `graph.json` schema, no spend cap.

**Technical Recommendations:**

1. **Pilot on `homelab-playbook` first** — it has the right multi-modal mix (code + Ansible YAML + Markdown docs + diagrams) for graphify to shine. Use the 4-phase roadmap; gate at Phase 0 on `GRAPH_REPORT.md` quality.
2. **Pair with code-review-graph** for review-style tasks — its benchmarks are tighter and the focus is narrower; treat it as the "code-review specialist" sibling rather than a replacement.
3. **Wrap subagent calls in LiteLLM** (already in your `hybrid_gemma_serving` plan) — gives you provider portability AND the spend cap graphify lacks.
4. **Run the multi-repo merge** as the headline use case — `graphify clone` + `graphify merge-graphs` across your three homelab repos and project containers. This is where graphify is genuinely better than every alternative.
5. **Re-evaluate at 8 weeks (2026-06-20)** — gate decision on issue #146 (proper MCP support) shipping, blank-report bug fix, and maintainer commit cadence. If MCP support stalls, switch to GitNexus.

---

## Table of Contents

1. **Technical Research Introduction and Methodology** — significance, methodology, goals achieved
2. **Graphify Technical Landscape and Architecture Analysis** — what it is, how it's built, where it sits
3. **Implementation Approaches and Best Practices** — install, run, integrate, operate
4. **Technology Stack Evolution and Current Trends** — the 2026 code-graph category
5. **Integration and Interoperability Patterns** — slash, hook, library, MCP
6. **Performance and Scalability Analysis** — the 71.5× claim and what's real
7. **Security and Compliance Considerations** — privacy boundary, supply chain
8. **Strategic Technical Recommendations** — adopt-vs-alternative verdict
9. **Implementation Roadmap and Risk Assessment** — 4-phase plan + 9-risk register
10. **Future Technical Outlook and Innovation Opportunities** — MCP trajectory, embeddings hybrid
11. **Technical Research Methodology and Source Verification** — searches, sources, confidence
12. **Technical Appendices and Reference Materials** — tables, packages, links

---

## 1. Technical Research Introduction and Methodology

### Technical Research Significance

The "give the LLM the *structure* of your codebase, not just text similar to your query" thesis turned from a Karpathy tweet-stream into a working category in twelve weeks. Microsoft GraphRAG validated graph summaries; LightRAG showed the cost line could be cut 100×; arxiv:2601.08773 (Jan 2026) established that **deterministic AST-derived graphs beat LLM-extracted KGs and vector-only RAG** for code multi-hop reasoning. By April, GitNexus hit #1 GitHub trending in a single day, code-review-graph's 6.8× / 49× claim went viral, and graphify shipped as the most ambitious entrant by surface area: code + Markdown + PDF + image + audio + video, all in one batch-pipeline producing one queryable graph artifact.

Why it matters for tomamourette specifically: your homelab spans three Git repos (`homelab/`, `homelab-bootstrap/`, `homelab-playbook/`) plus six-plus project containers (Sparkle-CPS, quant-trading, ai-dev-container, etc.) with deep domain documentation, PVE/Terraform/Ansible code, and a maturing local-LLM substrate (`hybrid_gemma_serving`). A tool that turns this sprawl into a single queryable graph that an AI assistant can traverse — without sending your source to a vendor — is a load-bearing piece of context infrastructure if it actually works.

_Technical Importance: Code-graph is becoming the third leg of LLM context engineering (after vector RAG and prompt caching). Pick wrong now, retool later._
_Business Impact: Token-reduction at the 5–10× level is real money (and real latency) when an agent does dozens of tool calls per task; multi-repo dependency mapping is otherwise hours of manual archaeology._

_Source: [analyticsvidhya — From Karpathy's LLM Wiki to Graphify](https://www.analyticsvidhya.com/blog/2026/04/graphify-guide/), [arxiv:2601.08773](https://arxiv.org/abs/2601.08773), [Graph Praxis: Graph RAG in 2026](https://medium.com/graph-praxis/graph-rag-in-2026-a-practitioners-guide-to-what-actually-works-dca4962e7517)._

### Technical Research Methodology

- **Technical Scope**: graphify's architecture, integration model, performance, security, and competitive position. Twelve named alternatives evaluated (GitNexus, CodeGraphContext, code-review-graph, codegraph, FalkorDB CodeGraph, Memgraph Graph-Code, Microsoft GraphRAG, LightRAG, nano-graphrag, Sourcegraph Cody, Aider repo-map, Continue's @codebase).
- **Data Sources**: maintainer's repo / website / PyPI page / release notes; one peer-reviewed paper (arxiv:2601.08773); four hands-on third-party reviews (Mustafa Genc, Pankaj, Aniket Sinare, Kevin Kinnett); benchmark tooling for the closest sibling (code-review-graph); 2026 ecosystem analysts (Ry Walker, paperclipped.de, Graph Praxis); Anthropic's pricing and Usage & Cost API docs.
- **Analysis Framework**: 5-step technical-research workflow: scope → tech stack → integration → architecture → implementation, plus this synthesis. Confidence levels applied to each contested claim.
- **Time Period**: April 2026 (current); citing material from Jan 2026 (paper) through Apr 24, 2026 (GitNexus coverage).
- **Technical Depth**: Implementation-level — actual install commands, real benchmark numbers, real cost models — not surface description.

### Technical Research Goals and Objectives

**Original Technical Goals:** Evaluate whether graphify offers better output and value than alternative knowledge-graph / code-RAG / GraphRAG implementations; gather available benchmarks and third-party reviews; produce a recommendation on adopt vs alternative.

**Achieved Technical Objectives:**

- ✅ Mapped graphify's full stack (Python + tree-sitter + NetworkX + Leiden + faster-whisper + vis.js + Anthropic) and its 3-pass pipeline; classified architectural pattern.
- ✅ Identified 12 alternatives across 6 architectural shapes (batch-JSON, MCP server, graph DB, hosted enterprise, LLM-extracted KG, hybrid AST+LLM).
- ✅ Cross-referenced graphify's 71.5× claim against code-review-graph's 3-repo study and the arxiv:2601.08773 architecture validation.
- ✅ Surfaced concrete operational risks (blank-report bug, MCP-vs-skill fork, Anthropic-only semantic pass, no spend cap, NetworkX scaling ceiling).
- ✅ Produced a 4-phase pilot roadmap, 9-risk register, 6-metric KPI scorecard tailored to tomamourette's homelab topology.
- ✅ Bonus discovery: PyPI namespace (`graphifyy` vs `anytechie-graphify`) — supply-chain hygiene check.

---

## 2. Graphify Technical Landscape and Architecture Analysis

(Detailed coverage in **Architectural Patterns and Design** above; this section synthesises the strategic view.)

**Three-pass batch pipeline** → NetworkX graph → Leiden clustering → HTML/JSON/MD outputs.

The dominant architectural patterns in 2026 code-graph tooling and where graphify sits:

| Architectural pattern | Examples | Where graphify sits |
|---|---|---|
| Batch ETL → on-disk JSON | **Graphify**, codegraph, code-review-graph | ✅ Primary identity |
| MCP-first long-running server | GitNexus, CodeGraphContext, hex-graph-mcp | ⚠️ Experimental (`--mcp` flag, issue #146) |
| Graph DB + Cypher | FalkorDB CodeGraph, Memgraph Graph-Code, Neo4j llm-graph-builder | ❌ Deliberately not |
| Hosted enterprise indexer | Sourcegraph Cody, Greptile | ❌ Different threat model |
| LLM-extracted KG (no AST) | Microsoft GraphRAG, LightRAG | ❌ Inferior for code per arxiv:2601.08773 |
| Hybrid AST + LLM multi-modal | **Graphify**, graphify-dotnet | ✅ Category leader by surface area |

_Dominant Patterns: Hybrid AST + LLM with batch-to-disk artifacts is the 2026 sweet spot for solo-dev / small-team. MCP-first is the trend for live agentic workflows._
_Architectural Evolution: 2025 vector-only RAG → early-2026 LLM-extracted KGs (Microsoft GraphRAG) → mid-2026 deterministic-first hybrids (graphify, code-review-graph, GitNexus). The arxiv paper crystallised the consensus._
_Architectural Trade-offs: Graphify trades the operational simplicity of zero-deploy and git-committable artifacts against the live-update ergonomics of an MCP server and the query power of a real graph DB._

_Source: [arxiv:2601.08773](https://arxiv.org/abs/2601.08773), [Memgraph: GraphRAG for Devs](https://memgraph.com/blog/graphrag-for-devs-coding-assistant), [paperclipped — Graph RAG in 2026](https://www.paperclipped.de/en/blog/graph-rag-production/), [Ry Walker — Code Intelligence Tools Compared](https://rywalker.com/research/code-intelligence-tools)._

### System Design Principles and Best Practices

The six load-bearing principles graphify embodies (validated against current best practice):

1. **Deterministic-first, LLM-second** — confirmed best practice (arxiv:2601.08773).
2. **Confidence as a first-class edge attribute** — uncommon but unambiguously good UX.
3. **Local-first privacy boundary** — strongest in category alongside GitNexus.
4. **Composable artifacts** (HTML / JSON / MD) — different views for different consumers.
5. **Progressive disclosure for the LLM** — GRAPH_REPORT.md is the prefix, graph.json is the substrate.
6. **Domain-aware Whisper prompting** — small but clever cross-pass loop.

_Source: [graphify ARCHITECTURE.md](https://github.com/safishamsi/graphify/blob/v3/ARCHITECTURE.md), [graphify.net — Leiden without embeddings](https://graphify.net/leiden-community-detection.html), [arxiv:2601.08773](https://arxiv.org/abs/2601.08773)._

---

## 3. Implementation Approaches and Best Practices

(Detailed coverage in **Implementation Approaches and Technology Adoption** above. Synthesis below.)

- **Install**: `uv tool install graphifyy` (or `pipx install graphifyy`).
- **Build**: `graphify <path>`. Cache hits make re-runs cheap.
- **Integrate (Claude Code)**: `graphify claude install` writes `CLAUDE.md` directive + PreToolUse hook.
- **Cross-repo**: `graphify clone <url>` + `graphify merge-graphs`.
- **CI**: Trivial GitHub Actions job; commit `graphify-out/`.
- **Reindex trigger**: Manual today; wrap with `pre-push` git hook or nightly cron in CI. Operational gap vs GitNexus's PostToolUse-on-commit auto-reindex.

_Source: [Graphify CLI Command Reference](https://graphify.net/graphify-cli-commands.html), [Graphify + Claude Code Integration](https://graphify.net/graphify-claude-code-integration.html), [graphifyy on PyPI](https://pypi.org/project/graphifyy/)._

---

## 4. Technology Stack Evolution and Current Trends

(Detailed coverage in **Technology Stack Analysis** above. Synthesis below.)

- **Languages**: Python is the orchestration default; Rust rising in AST tooling; .NET / TS ports of the architecture (`graphify-dotnet`, GitNexus browser-side) signal cross-ecosystem demand.
- **Frameworks/Libraries**: Graphify's stack — tree-sitter / NetworkX / graspologic-Leiden / faster-whisper / vis.js / Anthropic SDK — is the de-facto reference set for "AST + LLM hybrid" tools.
- **Storage**: NetworkX-on-JSON is the simplicity bet. Real graph DBs (FalkorDB / Memgraph / Neo4j) win at scale. SQLite (code-review-graph's choice) is a sensible middle ground.
- **Trends**: MCP becoming the integration bus; multi-modal indexing as the new differentiator; enterprise tier consolidating on Cody / Greptile.

_Source: [Repository Intelligence in AI Coding Tools 2026](https://www.buildmvpfast.com/blog/repository-intelligence-ai-coding-codebase-understanding-2026), [Ry Walker — Code Intelligence Tools Compared](https://rywalker.com/research/code-intelligence-tools), [Graph Praxis — Graph RAG in 2026](https://medium.com/graph-praxis/graph-rag-in-2026-a-practitioners-guide-to-what-actually-works-dca4962e7517)._

---

## 5. Integration and Interoperability Patterns

(Detailed coverage in **Integration Patterns Analysis** above. Synthesis below.)

- **Skill-per-assistant** is graphify's primary bet (15+ supported); deepest in Claude Code via the PreToolUse hook + CLAUDE.md directive.
- **MCP support** is preview-quality (`--mcp` flag); proper auto-refreshing version tracked in issue #146.
- **Library API** (`build_merge()`) is idempotent and composable.
- **Outputs** are standard formats but `graph.json`'s schema is undocumented — the principal interoperability gap.

The **MCP-vs-skill fork** is the single most consequential architectural bet graphify has made. The 2026 trend is decisively MCP-ward (DEV.to / morphllm / LaoZhang AI all signal this in their April 2026 surveys).

_Source: [Hooks reference - Claude Code Docs](https://code.claude.com/docs/en/hooks), [DEV.to — Skills vs MCP 2026](https://dev.to/williamwangai/claude-code-skills-vs-mcp-servers-what-to-use-how-to-install-and-the-best-ones-in-2026-548k), [morphllm — Skills vs MCP vs Plugins](https://www.morphllm.com/claude-code-skills-mcp-plugins)._

---

## 6. Performance and Scalability Analysis

### The 71.5× claim, reconciled

Three benchmark anchors triangulate the real performance picture:

- **Graphify self-report**: 71.5× on 52 files (Karpathy + papers + images). Confidence: **Low** (single corpus, maintainer-chosen, never independently reproduced).
- **code-review-graph (independent peer)**: 26.2× → 8.1× → 6.0× across httpx → FastAPI → Next.js (125 → 2,915 → 27,732 files). Confidence: **High** (3 production repos, real commits, scaling test, quality scoring 8.8 vs 7.2).
- **arxiv:2601.08773**: AST-derived KGs achieve 15/15 on Java multi-hop QA vs LLM-KG 13/15 vs vector-only 6/15 on Shopizer. Confidence: **High** (peer-reviewed methodology). Validates *category and architecture*, not the specific token-reduction number.

**Synthesis**: Plan for **~5–10× token reduction** on a real medium-size repo. The order of magnitude is real; the 71.5× headline isn't representative. Quality uplift (review accuracy / completeness / actionability) is closer to **+1.6 points on a 10-pt scale** based on code-review-graph's controlled study.

### Scalability ceilings

- **NetworkX is the hard limit**: ~100 B/edge memory; 30M edges ≈ 40 GB RAM; harmonic-centrality benchmark Neo4j GDS 14 s vs NetworkX 1 h 6 min. Fine for homelab; problematic at monorepo scale.
- **Cost ceiling**: Multi-modal pass scales linearly with non-code tokens. ~$1.35 for a 50-file mixed corpus, ~$225 for 500 PDFs, ~$2,250 for 5k PDFs at Sonnet 4.6 prices.

_Source: [code-review-graph benchmark methodology](https://github.com/tirth8205/code-review-graph), [arxiv:2601.08773](https://arxiv.org/abs/2601.08773), [Memgraph: NetworkX scaling challenges](https://memgraph.com/blog/data-persistency-large-scale-data-analytics-and-visualizations-biggest-networkx-challenges), [Towards Data Science: Neo4j vs NetworkX](https://towardsdatascience.com/fire-up-your-centrality-metric-engines-neo4j-vs-networkx-a-drag-race-of-sorts-18857f25be35/), [Anthropic Pricing 2026 — Finout](https://www.finout.io/blog/anthropic-api-pricing)._

---

## 7. Security and Compliance Considerations

(Detailed coverage in **Integration Security Patterns** and **Security Architecture Patterns** above.)

- **Privacy posture**: source code never leaves machine; A/V transcribed locally; only semantic descriptions of docs/papers/images go to the LLM. Materially better than Cody (cloud indexer) and Microsoft GraphRAG (cloud-first).
- **Supply chain**: PyPI namespace is `graphifyy` (double-y). `anytechie-graphify` exists on PyPI — verify provenance.
- **API key handling**: standard env-var pattern; no graphify-side secrets to manage.
- **Spend cap**: NONE built-in — the operational risk most often missed. Wrap with Anthropic Usage & Cost API check.
- **Compliance**: For homelab use, no regulatory issue. For enterprise use with regulated data (PHI / PCI / GDPR-restricted), the multi-modal pass to a third-party LLM is the audit boundary; route via your enterprise LLM agreement.

_Source: [Anthropic Usage and Cost API](https://platform.claude.com/docs/en/build-with-claude/usage-cost-api), [Mustafa Genc — privacy article](https://medium.com/@mustafa.gencc94/graphify-build-a-knowledge-graph-from-your-entire-codebase-without-sending-your-code-to-anyone-1b6924474b50), [graphifyy PyPI](https://pypi.org/project/graphifyy/)._

---

## 8. Strategic Technical Recommendations

### The Verdict

**Adopt with caveats** — graphify earns a place in the toolchain on technical merit, but it does *not* unambiguously dominate alternatives, and the headline 71.5× claim doesn't generalise. The right posture is a **scoped 4-week pilot** with a clear re-evaluation gate at week 8.

### When graphify is the right pick (and where it isn't)

| Scenario | Pick | Why |
|---|---|---|
| Multi-modal mix (code + docs + papers + images + A/V), polyrepo | **Graphify** | Category-of-one for end-to-end multi-modal + multi-repo merge. |
| Code-review token-reduction focus only | **code-review-graph** | Tighter benchmarks, narrower scope, MIT-licensed, dedicated review skill. |
| MCP-first agentic workflow, browser/desktop convenience | **GitNexus** | MCP-native, PostToolUse auto-reindex, zero-server. Best UX in category today. |
| Enterprise, multi-million-LOC, Cypher queries needed | **CodeGraphContext** or **FalkorDB CodeGraph** | Real graph DB, scales past NetworkX ceiling. |
| Cloud-hosted, RBAC, multi-tenant | **Sourcegraph Cody** | Mature, but inverts graphify's threat model. |
| Non-code corpora needing global synthesis | **LightRAG** or **Microsoft GraphRAG** | Community summaries; LightRAG at ~1/100th GraphRAG cost. |
| Lightweight repo-map for solo CLI workflow | **Aider repo-map** | Already there if you use Aider; zero install. |

### Competitive Technical Advantages (the genuine ones)

- **End-to-end multi-modal** in one tool. No competitor matches.
- **Multi-repo merge with `source_repo`-tagged nodes**. Uniquely strong fit for polyrepo.
- **Privacy boundary equal-best in category**.
- **15+ assistant integrations day-1** (the moat that decays first as MCP standardises).
- **Confidence-labelled edges** (EXTRACTED / INFERRED / AMBIGUOUS) are uncommon-good UX.

### Innovation Opportunities

- **Hybrid clustering** (Leiden topology + optional embeddings for "semantically similar but not linked" recall).
- **PostToolUse auto-reindex** — close the operational gap vs GitNexus.
- **Native spend cap** — the easy security/cost win.
- **Schema for `graph.json`** — unlocks third-party tooling.

_Source: [Ry Walker — Code Intelligence Tools Compared](https://rywalker.com/research/code-intelligence-tools), [paperclipped — Graph RAG in 2026 — Production](https://www.paperclipped.de/en/blog/graph-rag-production/), [GitNexus on MarkTechPost](https://www.marktechpost.com/2026/04/24/meet-gitnexus-an-open-source-mcp-native-knowledge-graph-engine-that-gives-claude-code-and-cursor-full-codebase-structural-awareness/), [code-review-graph](https://github.com/tirth8205/code-review-graph)._

---

## 9. Implementation Roadmap and Risk Assessment

(Detailed coverage in **Implementation Approaches and Technology Adoption** above.)

**4-phase plan** (~3.5 days total wall-clock): Phase 0 sandbox eval (1 evening) → Phase 1 pilot integration (1–2 days) → Phase 2 multi-repo merge (½ day) → Phase 3 operationalisation as nightly cron (1 day) → Phase 4 re-evaluation gate at 8 weeks (2026-06-20).

**Risk register**: 9 risks tracked, 4 high-impact (hype-cycle abandonment, cost runaway, MCP ecosystem leaving skill-first behind, NetworkX scaling at high N). All have explicit mitigations.

**6-metric KPI scorecard** with 4-of-6-green decision rule at week 4.

---

## 10. Future Technical Outlook and Innovation Opportunities

### Near-term (1–6 months)

- MCP becomes the dominant integration substrate. Skill-first tools either ship MCP servers (graphify issue #146) or lose ground.
- PostToolUse auto-reindex becomes table stakes. Tools without it feel stale.
- Independent benchmark reproductions arrive. The 71.5× claim either holds up on a richer corpus or is quietly retired.
- Spend-cap and budget guardrails appear natively (not just wrapper scripts).

### Medium-term (6–18 months)

- Hybrid clustering (topology + embeddings) becomes standard — addresses the "semantically similar but not linked" recall gap.
- Code-graph + agentic-loop integration tightens. The graph isn't just consulted *before* tool calls; it's updated *during* them.
- Schema standardisation pressure for `graph.json` / cross-tool format. SCIP-style protocol for KG-of-code emerges.

### Long-term (18+ months)

- "Graph as the LLM context primitive" replaces the prompt-stuffing model. Agents traverse rather than retrieve-then-read.
- Local LLMs become competitive for the semantic-extraction pass. The Anthropic-only dependency dissolves.
- Real-time / event-driven KG maintenance becomes the norm. Batch indexing becomes a fallback, not the default.

_Source: [Graph Praxis — Graph RAG in 2026](https://medium.com/graph-praxis/graph-rag-in-2026-a-practitioners-guide-to-what-actually-works-dca4962e7517), [siliconangle — Scaling AI agents via contextual intelligence](https://siliconangle.com/2026/01/18/2026-data-predictions-scaling-ai-agents-via-contextual-intelligence/), [GitNexus on MarkTechPost](https://www.marktechpost.com/2026/04/24/meet-gitnexus-an-open-source-mcp-native-knowledge-graph-engine-that-gives-claude-code-and-cursor-full-codebase-structural-awareness/)._

---

## 11. Technical Research Methodology and Source Verification

### Primary Sources

- [GitHub — safishamsi/graphify](https://github.com/safishamsi/graphify) — repo, README v3 / v4, ARCHITECTURE.md, Releases page
- [graphify.net](https://graphify.net/) — official site, CLI reference, Leiden / Tree-sitter pages, Claude Code integration page
- [graphifyy on PyPI](https://pypi.org/project/graphifyy/) — official package; [anytechie-graphify](https://pypi.org/project/anytechie-graphify/) — namespace check

### Independent Benchmark Anchors

- [arxiv:2601.08773 — Reliable Graph-RAG for Codebases (Jan 2026)](https://arxiv.org/abs/2601.08773) — peer-reviewed AST-vs-LLM-vs-vector results
- [code-review-graph (Tirth Kanani, Mar 2026)](https://github.com/tirth8205/code-review-graph) — 3-repo controlled benchmark
- [Tirth Kanani — I Built a Knowledge Graph that Cuts Token Usage by 49×](https://tirthkanani18.medium.com/i-built-a-knowledge-graph-that-cuts-claude-codes-token-usage-by-49x-9260d3cd1069)
- [DEV.to — How code-review-graph cuts tokens 49× (and is it worth it)](https://dev.to/emperorakashi20/how-code-review-graph-cuts-claude-code-token-usage-by-49x-and-whether-its-actually-worth-it-4kn1)

### Hands-on Reviews (third-party)

- [Kevin Kinnett — Graphify Review with Claude Code](https://www.kevinkinnett.com/posts/graphify-review-claude-code-knowledge-graph/) — surfaces blank-report bug, Claude-only dependency, big-repo first-run cost
- [Mustafa Genc on GoPenAI — Without Sending Your Code to Anyone](https://medium.com/@mustafa.gencc94/graphify-build-a-knowledge-graph-from-your-entire-codebase-without-sending-your-code-to-anyone-1b6924474b50)
- [Pankaj — Navigate Our Codebase by Structure, Not Similarity](https://medium.com/@pankaj_pandey/graphify-navigate-our-codebase-by-structure-not-similarity-eb773c4e9871)
- [Aniket Sinare — Stop Reading Code, Start Seeing It](https://medium.com/@aniketsinare/stop-reading-code-start-seeing-it-visualizing-your-codebase-with-graphify-vis-js-bdef82ad6050)
- [Soumil Shah — Graphify vs Caveman](https://medium.com/@shahsoumil519/graphify-vs-caveman-two-clever-tools-that-make-your-ai-coding-assistant-way-smarter-c6cd91378c59)
- [analyticsvidhya — From Karpathy's LLM Wiki to Graphify](https://www.analyticsvidhya.com/blog/2026/04/graphify-guide/)

### Comparative Analyses

- [Ry Walker Research — Code Intelligence Tools Compared](https://rywalker.com/research/code-intelligence-tools)
- [Ry Walker Research — CodeGraphContext](https://rywalker.com/research/codegraphcontext)
- [paperclipped — Graph RAG in 2026: Production cost & architecture](https://www.paperclipped.de/en/blog/graph-rag-production/)
- [Graph Praxis — Graph RAG in 2026: A Practitioner's Guide](https://medium.com/graph-praxis/graph-rag-in-2026-a-practitioners-guide-to-what-actually-works-dca4962e7517)
- [Repository Intelligence in AI Coding Tools 2026](https://www.buildmvpfast.com/blog/repository-intelligence-ai-coding-codebase-understanding-2026)
- [DEV.to — Claude Code Skills vs MCP Servers 2026](https://dev.to/williamwangai/claude-code-skills-vs-mcp-servers-what-to-use-how-to-install-and-the-best-ones-in-2026-548k)
- [morphllm — Claude Code Skills vs MCP vs Plugins](https://www.morphllm.com/claude-code-skills-mcp-plugins)
- [LaoZhang AI — Memory vs MCP vs Skills](https://blog.laozhang.ai/en/posts/claude-code-memory-vs-mcp-vs-skills)

### Direct Alternatives

- [GitHub — abhigyanpatwari/GitNexus](https://github.com/abhigyanpatwari/GitNexus) | [GitNexus on MarkTechPost](https://www.marktechpost.com/2026/04/24/meet-gitnexus-an-open-source-mcp-native-knowledge-graph-engine-that-gives-claude-code-and-cursor-full-codebase-structural-awareness/) | [Pebblous — GitNexus #1 Trending](https://blog.pebblous.ai/blog/gitnexus-code-knowledge-graph-2026/en/)
- [GitHub — CodeGraphContext](https://github.com/CodeGraphContext/CodeGraphContext)
- [GitHub — colbymchenry/codegraph](https://github.com/colbymchenry/codegraph)
- [Memgraph: GraphRAG for Devs — Graph-Code](https://memgraph.com/blog/graphrag-for-devs-coding-assistant)
- [FalkorDB CodeGraph](https://www.falkordb.com/blog/code-graph/)
- [Sourcegraph Cody docs](https://sourcegraph.com/docs/cody)

### Background / Pricing / Algorithms

- [Anthropic API — Pricing](https://platform.claude.com/docs/en/about-claude/pricing) | [Anthropic API — Usage and Cost API](https://platform.claude.com/docs/en/build-with-claude/usage-cost-api) | [Anthropic Pricing 2026 — Finout](https://www.finout.io/blog/anthropic-api-pricing)
- [Hooks reference — Claude Code Docs](https://code.claude.com/docs/en/hooks)
- [From Louvain to Leiden — Nature](https://www.nature.com/articles/s41598-019-41695-z) | [Leiden algorithm — Wikipedia](https://en.wikipedia.org/wiki/Leiden_algorithm)
- [Memgraph: NetworkX scaling challenges](https://memgraph.com/blog/data-persistency-large-scale-data-analytics-and-visualizations-biggest-networkx-challenges) | [Towards Data Science — Neo4j vs NetworkX benchmark](https://towardsdatascience.com/fire-up-your-centrality-metric-engines-neo4j-vs-networkx-a-drag-race-of-sorts-18857f25be35/) | [NVIDIA — GPU-accelerated Leiden](https://developer.nvidia.com/blog/how-to-accelerate-community-detection-in-python-using-gpu-powered-leiden/)

### Web Search Queries Executed

- `graphify safishamsi knowledge graph generator review`
- `graphify github safishamsi tree-sitter networkx leiden benchmark`
- `"graphify" hacker news codebase knowledge graph 2026`
- `Microsoft GraphRAG vs LightRAG vs nano-graphrag benchmark comparison 2026`
- `code knowledge graph tool tree-sitter AST RAG 2026 alternatives`
- `codebase indexing AI assistant Aider repo-map vs Sourcegraph Cody Continue 2026`
- `graphify "71.5x" token reduction methodology benchmark Karpathy`
- `graphify reddit critique honest review limitations code knowledge graph`
- `"AST-derived" knowledge graph vs LLM-extracted code RAG accuracy 2026 paper`
- `GitNexus CodeGraphContext code-review-graph knowledge graph claude code 2026`
- `graphify install Claude Code skill hook PreToolUse PostToolUse MCP integration`
- `graphify multi-repo cross-repo merge v0.5 GitHub clone JSON output`
- `MCP server vs Claude Code skill integration pattern code knowledge graph 2026`
- `graphify slash command output GRAPH_REPORT.md JSON schema query`
- `graphify three-pass pipeline architecture deterministic AST god nodes Leiden`
- `Leiden community detection vs Louvain knowledge graph code clustering`
- `NetworkX scale ceiling million nodes performance graph database alternatives 2026`
- `code knowledge graph scaling million LOC indexing time benchmark 2026`
- `graphify hands-on review case study large codebase python javascript real world`
- `"code-review-graph" "6.8x" "49x" tirth8205 benchmark Claude Code methodology`
- `graphify vs GitNexus vs CodeGraphContext comparison developer review 2026`
- `graphify cost API spend Anthropic Claude budget large repository indexing`

### Confidence Level Summary

| Claim | Confidence | Why |
|---|---|---|
| 71.5× token reduction (graphify) | **Low** | Single small mixed corpus; not independently reproduced |
| 5–10× on real medium-size repos | **Medium-High** | Triangulated via code-review-graph's controlled 3-repo study |
| AST-first architecture is correct | **High** | Peer-reviewed (arxiv:2601.08773); 15/15 vs 13/15 vs 6/15 on Shopizer |
| GitHub stars (22k+ vs 34.5k) | **Medium** | Sources disagree; figure is rapidly changing |
| Maintainer is solo / single-developer-risk | **Medium** | Inferred from repo activity pattern; not explicitly verified |
| Multi-modal end-to-end is unique | **High** | Surveyed 12 alternatives; none match end-to-end |
| Privacy boundary as described | **High** | Multiple independent reviewers confirm |
| Anthropic-only semantic pass | **High** | Confirmed by README + reviewers |
| `GRAPH_REPORT.md` blank-output bug | **Medium** | Single hands-on report (Kevin Kinnett) |
| `anytechie-graphify` is a typosquat | **Low** | Exists on PyPI; provenance not verified |

### Research Limitations

- No direct hands-on testing was performed in this report; all conclusions are derived from documentation, third-party reviews, and ecosystem analysis. A Phase-0 sandbox run on `homelab-playbook` is the right next action and is recommended in §9.
- Star counts and adoption metrics in a hype cycle are noisy. Discount accordingly; commit cadence and issue-triage activity are stronger long-term signals.
- The 71.5× number has not been independently reproduced; expectations in this report are calibrated against the closest peer's better-controlled study (code-review-graph), not graphify's own measurement.

---

## 12. Technical Appendices and Reference Materials

### Appendix A — Architectural Pattern Comparison Table

| Tool | Architecture | DB | Multi-modal | Multi-repo | MCP | License | Stars (Apr 2026) |
|---|---|---|---|---|---|---|---|
| **Graphify** | Batch ETL → JSON | NetworkX (in-mem) | ✅ All | ✅ Native merge | ⚠️ Preview | Apache-2.0 | 22k–34k |
| GitNexus | MCP server | Custom engine | ❌ Code only | ⚠️ Manual | ✅ Native | (unspecified) | ~28k |
| CodeGraphContext | MCP + CLI | Neo4j | ❌ Code only | ⚠️ Manual | ✅ Native | MIT | ~2.2k (100k+ DLs) |
| code-review-graph | Batch + skill | SQLite | ❌ Code only | ❌ Single repo | ❌ | MIT | (small) |
| codegraph (colbymchenry) | Pre-indexed local | JSON | ❌ Code only | ❌ | ❌ | (open) | (small) |
| FalkorDB CodeGraph | Graph-DB native | FalkorDB | ❌ Code only | ⚠️ Possible | ❌ | (commercial) | n/a |
| Microsoft GraphRAG | Cloud pipeline | Parquet | ⚠️ Text-mostly | ⚠️ Possible | ❌ | MIT | (large) |
| LightRAG | Lightweight pipeline | NetworkX/Neo4j | ⚠️ Text-mostly | ⚠️ Manual | ❌ | (open) | (large) |
| nano-graphrag | Single-file impl | LightRAG-like | ⚠️ Text | ❌ | ❌ | MIT | (small) |
| Sourcegraph Cody | Hosted indexer | SCIP/cloud | ❌ Code only | ✅ Native | ⚠️ | EE/SaaS | (enterprise) |
| Aider repo-map | In-prompt | (none) | ❌ Code only | ❌ | ❌ | Apache-2.0 | (large) |

### Appendix B — Token-Reduction Benchmarks (cross-tool)

| Source | Tool | Corpus | Reduction |
|---|---|---|---|
| graphify README | Graphify | 52 files (Karpathy + papers + images) | 71.5× |
| code-review-graph (Mar 2026) | code-review-graph | httpx (125 files) | 26.2× |
| code-review-graph (Mar 2026) | code-review-graph | FastAPI (2,915 files) | 8.1× |
| code-review-graph (Mar 2026) | code-review-graph | Next.js (27,732 files) | 6.0× |
| code-review-graph (Mar 2026) | code-review-graph | Next.js (daily coding) | up to 49× |
| code-review-graph quality study | code-review-graph | 10-pt scale | +1.6 (8.8 vs 7.2) |
| arxiv:2601.08773 (Jan 2026) | DKB (AST-derived) | Java Shopizer multi-hop | 15/15 |
| arxiv:2601.08773 | LLM-KB | Java Shopizer | 13/15 |
| arxiv:2601.08773 | Vector-only | Java Shopizer | 6/15 |

### Appendix C — Cost Model (Anthropic Sonnet 4.6, April 2026)

| Corpus | Approx tokens | Build cost (one-time) | Re-run cost (cache hit) |
|---|---|---|---|
| Code-only repo (any size) | 0 (deterministic) | ~$0 | ~$0 |
| 50 mixed files (Karpathy-like) | 200k in / 50k out | ~$1.35 | ~$0.10 |
| 500 PDFs (lab archive) | 50M in / 5M out | ~$225 | ~$15 |
| 5,000 PDFs + images | 500M in / 50M out | ~$2,250 | ~$150 |

Apply 50% discount via Batch API or 90% via prompt caching where applicable.

### Appendix D — Quick-Reference Commands

```bash
# install
uv tool install graphifyy             # or: pipx install graphifyy

# build
graphify .                             # current dir
graphify clone https://github.com/X/Y  # GitHub repo

# integrate (Claude Code)
graphify claude install                # CLAUDE.md + PreToolUse hook

# multi-repo
graphify merge-graphs a.json b.json --out merged.json

# MCP (preview)
graphify ./raw --mcp

# query (within Claude Code / etc)
/graphify query <text>
/graphify path <node-a> <node-b>
/graphify explain <node-id>
```

### Appendix E — Open Source Projects & Communities Referenced

- safishamsi/graphify (and forks: graphify-dotnet)
- abhigyanpatwari/GitNexus (and nxpatterns/gitnexus mirror)
- CodeGraphContext/CodeGraphContext
- tirth8205/code-review-graph
- colbymchenry/codegraph
- microsoft/graphrag (and DEEP-PolyU/Awesome-GraphRAG curated list)
- HKUDS/LightRAG, gusye1234/nano-graphrag
- sourcegraph/cody, Aider-AI/aider
- shaneholloman/mcp-knowledge-graph, levnikolaevich/claude-code-skills (hex-graph)
- Anthropic/claude-code

---

## Technical Research Conclusion

### Summary of Key Technical Findings

Graphify is a **technically sound, architecturally ambitious entrant** in the white-hot 2026 code-knowledge-graph category. Its design — deterministic AST-first, LLM-second, topology-only Leiden clustering, no graph DB, multi-modal end-to-end — is **independently validated as the right pattern** for code by arxiv:2601.08773. Its **multi-modal scope and multi-repo merge are genuinely differentiated** versus all named alternatives. Its **privacy posture is best-in-class** alongside GitNexus.

The headline 71.5× token-reduction claim is **real-but-narrow** — corpus-specific to a small mixed Karpathy-and-papers folder; better-controlled peer benchmarks (code-review-graph) put real-world reduction in the **5–10× range** on medium-size repos and up to 49× only in highly favorable monorepo scenarios. Quality uplift in controlled tests is meaningful (+1.6 points on a 10-pt scale).

The **operational gaps are real but addressable**: blank-report bug, batch-only re-indexing (no PostToolUse), undocumented `graph.json` schema, single-vendor LLM dependency for the semantic pass, no spend cap. The **strategic risk is the MCP-vs-skill ecosystem fork** — graphify's 15-assistant skill-first bet is currently paying off in mind-share but is the architecture most exposed to MCP standardisation.

### Strategic Technical Impact Assessment

For tomamourette's homelab:

- **Phase 0–2 of the pilot (sandbox + Claude integration + multi-repo merge) is the highest-EV move** in this category right now. ~3 hours of work, ~$0–5 of API cost, exposes whether the multi-modal + multi-repo story holds in your environment.
- The **8-week re-evaluation gate (2026-06-20)** is the right horizon — long enough for issue #146 (proper MCP) to ship or stall, the blank-report bug to be triaged, and the 71.5× figure to be independently reproduced or quietly retired.
- **Don't put graphify on the critical path of any deploy/CI workflow** at the pilot stage. Treat its outputs as advisory; treat the assistant integration as a productivity boost, not a guarantee.

### Next Steps Technical Recommendations

1. **Run Phase 0 (sandbox eval) on `homelab-playbook`** today/this week. ~1 evening.
2. **If Phase 0 is positive, run Phase 1 (Claude install + one real task) within the next week.**
3. **Phase 2 (multi-repo merge across `homelab/` + `homelab-bootstrap/` + `homelab-playbook/` + project containers) is the killer use case for your topology** — schedule it after Phase 1 confirmation.
4. **Wrap subagent calls in LiteLLM** to plug the spend-cap gap, gain provider portability, and align with your `hybrid_gemma_serving` plan.
5. **Treat code-review-graph as a peer**, not a substitute. Different tools, different sweet spots; both are MIT/open and cheap to keep installed.
6. **Re-evaluate at week 8 (2026-06-20)** against the 6-metric scorecard. Decision rule: 4-of-6 green → keep graphify; otherwise migrate to GitNexus (if MCP-first becomes the dominant model) or CodeGraphContext (if you outgrow NetworkX).

---

**Technical Research Completion Date:** 2026-04-25
**Research Period:** April 2026 — current comprehensive technical analysis
**Document Length:** Full coverage spanning 6 workflow steps (scope → tech stack → integration → architecture → implementation → synthesis)
**Source Verification:** 60+ unique sources cited; all contested claims annotated with confidence levels
**Technical Confidence Level:** High overall; specific contested claims (71.5×, exact star count, single-developer risk) flagged in §11

_This comprehensive technical research document serves as an authoritative reference for evaluating graphify's adoption in tomamourette's homelab + dev-assistant context, and provides cross-tool benchmarks and architectural framing applicable to the broader 2026 code-knowledge-graph category._





