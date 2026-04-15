---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
inputDocuments:
  - https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
  - https://github.com/milla-jovovich/mempalace
  - https://github.com/NousResearch/hermes-agent
  - https://linear.app/docs/mcp
  - https://www.granola.ai/blog/granola-mcp
  - https://github.com/microsoft/azure-devops-mcp
workflowType: 'research'
lastStep: 8
research_type: 'technical'
research_topic: 'LLM Knowledge Management — LLM Wiki, MemPalace, Hermes Agent, Obsidian, Ingestion Pipelines'
research_goals: 'Deep analysis of each system, Obsidian integration, multi-vault architecture, knowledge ingestion workflows (Linear, Granola, Azure DevOps), epic planning'
user_name: 'tomamourette'
date: '2026-04-11'
web_research_enabled: true
source_verification: true
---

# Technical Research Report: LLM Knowledge Management Systems

**Date:** 2026-04-11
**Author:** tomamourette
**Research Type:** Technical — Deep Comparative Analysis

---

## Research Overview

This report examines three systems for LLM-native knowledge management — **LLM Wiki** (Karpathy), **MemPalace** (milla-jovovich), and **Hermes Agent** (NousResearch) — evaluating each independently, then analysing how they combine and fit into our Proxmox/Ansible homelab infrastructure.

**Methodology:** Primary source analysis (GitHub repos, gist content, AGENTS.md, SKILL.md, integration docs) supplemented with web research on the Hermes agent ecosystem. All claims verified against source material with caveats noted where marketing overstates reality.

---

## Part 1: LLM Wiki (Karpathy)

### What It Is

LLM Wiki is a **pattern** (not a software product) for building personal knowledge bases where an LLM incrementally maintains a structured, interlinked collection of markdown files — rather than performing RAG on raw sources every time.

**Source:** https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f

### Core Insight

> "Maintaining a knowledge base is work whose burden grows faster than its value, causing abandonment. LLMs don't tire or forget cross-reference updates."

The pattern shifts the labour distribution: humans curate sources and think strategically; the LLM handles bookkeeping, cross-referencing, and synthesis.

### Three-Layer Architecture

| Layer | Owner | Purpose |
|-------|-------|---------|
| **Raw Sources** | Human (immutable) | Articles, papers, docs, images — the LLM reads but never modifies |
| **The Wiki** | LLM (generated) | Markdown pages: summaries, entity pages, concept pages, cross-references |
| **The Schema** | Human (config) | CLAUDE.md or equivalent telling the LLM how the wiki is structured, naming conventions, workflows |

### Operations

| Operation | What Happens |
|-----------|-------------|
| **Ingest** | LLM reads new source → writes summary pages → updates index → refreshes entity/concept pages. A single source may touch 10-15 wiki pages. |
| **Query** | Question against the wiki → LLM searches relevant pages → synthesizes answer with citations. Good answers filed back as new pages. |
| **Lint** | Periodic health check: contradictions, stale claims, orphan pages, missing cross-references, data gaps. |

### Navigation Files

- **index.md** — Content catalogue listing every page with one-line summaries, organized by category. Updated on each ingest.
- **log.md** — Append-only chronological record of ingests, queries, and lint passes. Parseable with standard Unix tools.

### Key Strengths

- **Zero dependencies** — Pure markdown, works with any LLM, any editor
- **Compounds over time** — Each new source strengthens the entire knowledge base, connections are pre-built
- **Obsidian-native** — Users commonly maintain the wiki in Obsidian, getting graph views and bidirectional links for free
- **Searchable** — At small scale, index.md suffices; at scale, hybrid BM25/vector search via tools like `qmd`
- **Intentionally abstract** — Directory structure, page formats, and tooling are domain-dependent; users collaborate with their LLM to instantiate a version matching their needs

### Limitations

- **Not a tool** — No installable software, no API, no automation. It's a workflow pattern that requires discipline.
- **Token-hungry on ingest** — Ingesting a single source that touches 15 wiki pages means the LLM needs to read/write extensively.
- **No built-in memory persistence** — Relies entirely on the LLM having file access (Claude Code, Cursor, etc.) to read/write the wiki.
- **No semantic search by default** — At scale, you need to bolt on vector search.
- **Single-user pattern** — No multi-agent or collaboration built in.

### Assessment

LLM Wiki is a **philosophy and workflow**, not a product. Its power is simplicity — markdown files that any tool can read, that compound over time, and that the LLM maintains. It's the "plain text" of LLM knowledge management.

---

## Part 2: MemPalace

### What It Is

MemPalace is an **open-source Python tool** that stores AI conversation history and project knowledge verbatim in ChromaDB, organized using a physical memory palace metaphor. It provides an MCP server with 19 tools for semantic search and knowledge graph queries.

**Source:** https://github.com/milla-jovovich/mempalace

### Architecture: The Palace Metaphor

```
Palace
├── Wings (people/projects)
│   ├── Rooms (topics: auth, billing, deployment)
│   │   ├── Halls (memory types: facts, events, discoveries, preferences, advice)
│   │   │   ├── Closets (summaries → point to originals)
│   │   │   └── Drawers (verbatim original chunks)
│   │   └── ...
│   └── Tunnels (cross-wing connections)
└── Knowledge Graph (temporal entity-relationship triples)
```

### Memory Layers

| Layer | Size | Loading | Purpose |
|-------|------|---------|---------|
| **L0: Identity** | ~50 tokens | Always | Who is the user |
| **L1: Critical facts** | ~120 tokens (AAAK) | Always | Key facts, compressed |
| **L2: Room recall** | Variable | On-demand | Topic-specific memory |
| **L3: Deep search** | Variable | On-demand | Full semantic search |

### Technical Stack

| Component | Technology |
|-----------|-----------|
| Vector storage | ChromaDB (local) |
| Knowledge graph | SQLite |
| Compression | AAAK (experimental lossy abbreviation) |
| Server protocol | MCP (19 tools) |
| Language | Python |
| Package manager | UV / pip |

### Mining Modes

- **Projects** — Ingests code and documentation
- **Conversations** — Ingests Claude, ChatGPT, Slack exports
- **General** — Auto-classifies into decisions, milestones, problems

### MCP Tools (Key Categories)

| Category | Tools | Examples |
|----------|-------|---------|
| Search & Browse | Semantic queries, taxonomy browse, AAAK spec | `mempalace_search`, `mempalace_browse` |
| Knowledge Graph | Entity queries, time filtering, fact add/invalidate | `mempalace_kg_query`, `mempalace_kg_add` |
| Palace Graph | Cross-wing traversal, tunnel discovery | `mempalace_palace_graph` |
| Write | Drawer storage, diary entries | `mempalace_diary_write` |

### Important Caveats (April 2026 Disclosure)

The project made honest corrections to earlier claims:

| Claim | Reality |
|-------|---------|
| 96.6% R@5 on LongMemEval | **True — but raw mode only**, not AAAK-compressed |
| AAAK saves tokens at scale | **Overstated** — regresses performance to 84.2% R@5 |
| Palace metadata boosts retrieval 34% | **Standard ChromaDB filtering**, not architecturally novel |
| Contradiction detection | Exists but **not wired into knowledge graph operations** |

### Key Strengths

- **Local-first, zero-cloud** — Everything on your machine, no API keys, no subscriptions
- **96.6% recall** on raw verbatim storage — genuinely strong
- **MCP-native** — 19 tools, works with Claude, ChatGPT, Cursor, Gemini
- **Knowledge graph** with temporal validity windows — facts can expire
- **OpenClaw/Hermes skill** — Direct integration path to Hermes agent
- **Conversation mining** — Ingest past chat history from multiple platforms

### Limitations

- **ChromaDB dependency** — Heavier than plain files; needs Python runtime
- **AAAK compression unreliable** — The project itself admits performance regression
- **Single-palace design** — Not inherently multi-agent or distributed
- **Python-only** — No TypeScript/Node alternative

### Assessment

MemPalace is a **solid verbatim memory store with semantic search** wrapped in a creative metaphor. The core value is real: local ChromaDB with 96.6% recall and an MCP server that any AI assistant can use. Ignore the AAAK marketing; use raw mode.

---

## Part 3: Hermes Agent (NousResearch)

### What It Is

Hermes Agent is a **self-improving AI agent platform** from Nous Research that provides a persistent, learning-capable system with cross-platform messaging, flexible deployment, and an autonomous skill-creation loop.

**Source:** https://github.com/NousResearch/hermes-agent

### Architecture

```
Hermes Agent
├── TUI (Terminal UI with streaming, slash commands)
├── Messaging Gateway (Telegram, Discord, Slack, WhatsApp, Signal, Email)
├── Terminal Backends (local, Docker, SSH, Daytona, Singularity, Modal)
├── 40+ Built-in Tools
├── MCP Server Integration
├── Skills Hub (persistent procedures)
├── Memory System (FTS5 search, LLM summarization, cross-session)
├── Honcho Dialectic User Modeling
├── Cron Scheduler (unattended tasks)
└── Subagent Delegation (parallel workstreams)
```

### Self-Learning Loop

1. Agent completes a complex task
2. Autonomously creates a reusable **skill** from the experience
3. Skills self-improve during subsequent use
4. Agent-curated memory with periodic nudges
5. Compatible with **agentskills.io** open standard

### Memory & Knowledge

**Built-in memory** is stored in `~/.hermes/memories/` (MEMORY.md, USER.md), injected into the system prompt at session start. Session history uses FTS5-indexed SQLite for cross-session recall with LLM summarization.

**8 External Memory Providers** (plugins, never replacing built-in):

| Provider | Capability |
|----------|-----------|
| Honcho | Dialectic user modeling |
| Mem0 | Managed memory layer |
| Hindsight | Automatic fact extraction |
| Holographic | Knowledge graphs |
| RetainDB | Structured retention |
| ByteRover | Semantic search |
| Supermemory | Cross-app memory |
| OpenViking | Open-source memory |

This plugin architecture means MemPalace could be added as a 9th memory provider, or connected via MCP tools.

### MCP Integration (Dual Mode)

Hermes has **first-class MCP support** operating in two modes:

- **As MCP client**: Connects to external MCP servers at startup, discovers tools, registers them alongside native tools. Dynamic tool discovery — servers can notify of changes at runtime.
- **As MCP server**: Claude Code, Cursor, or Codex can use Hermes's messaging and agent capabilities as tools.
- **Transports**: stdio and HTTP with automatic reconnection and security filtering (allow/block lists)
- **Config**: `~/.hermes/config.yaml` under `mcp_servers:`

### Hermes Model Family

- **Hermes 3** (2024): Fine-tuned Llama 3.1 (3B, 8B, 70B, 405B). ChatML format with `<tool_call>` XML tags.
- **Hermes 4** (2025): Hybrid reasoning on Llama 3.1 (70B, 405B). Features `<think>...</think>` segments for self-reflective reasoning.

The agent framework is model-agnostic but optimized for Hermes models.

### Deployment Flexibility

| Backend | Use Case |
|---------|----------|
| Local | Development, personal use |
| Docker | Containerized, reproducible |
| SSH | Remote servers |
| Daytona | Serverless with hibernation |
| Singularity | HPC / research clusters |
| Modal | Cloud GPU workloads |

Runs on a **$5 VPS** up to GPU clusters. Hibernates when idle on serverless backends.

### Model Support

Provider-agnostic: Nous Portal, OpenRouter (200+ models), OpenAI, Anthropic, z.ai/GLM, Kimi/Moonshot, MiniMax, and custom endpoints. Switch models with `hermes model` — no code changes.

### Key Strengths

- **Self-improving** — Skills created from experience, refined on use
- **Multi-platform messaging** — Reach the agent from anywhere
- **MCP-native** — Integrates external tool servers
- **Lightweight deployment** — Docker container on a $5 VPS
- **OpenClaw migration** — Direct import of MemPalace skills, personas, memories
- **Cron scheduling** — Unattended daily reports, backups, audits
- **MIT licensed**

### Limitations

- **Relatively new** — Ecosystem still maturing
- **Memory system is simpler** than dedicated solutions (FTS5 vs vector search)
- **No built-in knowledge graph** — Relies on external tools for structured knowledge
- **Multi-model routing not built-in** — Manual model selection

### Assessment

Hermes is an **excellent agent runtime** — persistent, self-improving, deployable anywhere, and MCP-compatible. Its memory system is functional but basic. It's designed to be extended with specialized knowledge tools rather than being a knowledge store itself.

---

## Part 4: How They Fit Together

### Complementary Architecture

These three systems occupy distinct layers of a knowledge-augmented agent stack:

```
┌─────────────────────────────────────────────┐
│            HERMES AGENT (Runtime)            │
│  Self-improving agent with messaging,       │
│  scheduling, skills, and tool execution     │
├─────────────────────────────────────────────┤
│          MEMPALACE (Memory Store)            │
│  Verbatim conversation storage, semantic    │
│  search, knowledge graph, MCP tools         │
├─────────────────────────────────────────────┤
│          LLM WIKI (Knowledge Base)          │
│  Structured markdown wiki maintained by     │
│  the LLM, with index, cross-references,    │
│  and compounding synthesis                  │
├─────────────────────────────────────────────┤
│          RAW SOURCES (Ground Truth)         │
│  Documents, repos, conversation exports,    │
│  articles, papers                           │
└─────────────────────────────────────────────┘
```

### Integration Model

| System | Role | What It Stores | How It's Queried |
|--------|------|---------------|-----------------|
| **LLM Wiki** | Synthesized knowledge | Distilled understanding, entity pages, concept pages, cross-references | File reads via LLM, index.md navigation |
| **MemPalace** | Raw memory | Verbatim conversations, temporal facts, entity relationships | MCP semantic search (19 tools) |
| **Hermes** | Agent runtime | Skills, user profiles, session context | Built-in memory + external MCP tools |

### Data Flow

```
Raw Source → MemPalace (mine & store verbatim)
                ↓
         Hermes Agent (queries MemPalace via MCP)
                ↓
         LLM Wiki (Hermes writes synthesized pages)
                ↓
         Index + Cross-references compound
                ↓
         Future queries hit wiki first (fast), fall back to MemPalace (deep)
```

### The Key Synergy

- **MemPalace** captures *everything* — high recall, low synthesis
- **LLM Wiki** captures *understanding* — high synthesis, curated knowledge
- **Hermes** is the *agent* that queries both and acts on the results

Together: MemPalace is the raw memory, LLM Wiki is the refined knowledge base, and Hermes is the brain that uses both and learns from the process.

### Hermes + MemPalace (Direct Integration)

MemPalace already ships as an **OpenClaw skill** (v3.1.0). Hermes has native OpenClaw import. The integration path is:

1. Install MemPalace: `pip install mempalace`
2. Add MCP server to Hermes config:
   ```json
   {
     "mcpServers": {
       "mempalace": {
         "command": "python3",
         "args": ["-m", "mempalace.mcp_server"]
       }
     }
   }
   ```
3. Hermes gains 19 memory tools — search, knowledge graph, diary, palace graph
4. Hermes's self-improving skills can learn to use MemPalace patterns effectively

### Hermes + LLM Wiki (Workflow Integration)

LLM Wiki isn't a tool — it's a pattern. Integration means:

1. Create a wiki directory structure (e.g., `~/wiki/` or a git repo)
2. Write a schema file (CLAUDE.md equivalent) defining the wiki structure
3. Hermes uses its file tools to read/write wiki pages during ingest/query/lint operations
4. Create Hermes skills for the three LLM Wiki operations (ingest, query, lint)
5. Schedule periodic lint passes via Hermes cron

### Three-System Combined Protocol

```
Session Start:
  1. Hermes loads context files + user profile
  2. MemPalace status check (L0 identity, L1 critical facts)
  3. Wiki index.md loaded for topic awareness

On New Information:
  1. MemPalace stores verbatim (mine/drawer write)
  2. Hermes triggers wiki ingest skill
  3. Wiki pages updated, index refreshed

On Query:
  1. Check wiki first (fast, pre-synthesized)
  2. If insufficient → MemPalace semantic search (deep, raw)
  3. If valuable answer → file back into wiki

Periodic Maintenance:
  1. Hermes cron triggers wiki lint
  2. MemPalace KG invalidation for stale facts
  3. Skills self-improve from patterns
```

---

## Part 5: Homelab Integration Strategy

### Current Infrastructure Context

- **Proxmox cluster** with LXC containers managed by Terraform/Ansible
- **ct-dev-homelab** (VMID 150) — primary dev container
- **ct-dev-test** (VMID 152) — test container
- **ct-sparkle-cps** (VMID 151) — CPS-Fabric repos with vault-encrypted Azure DevOps creds
- **Three repos**: homelab-infra, homelab-apps, homelab-playbook
- **Python 3.11.11** available via pyenv
- **Epic 2 (Persistent Memory)** upcoming — directly relevant

### Proposed Deployment Architecture

```
ct-dev-homelab (192.168.50.150)
├── Hermes Agent (Docker or local)
│   ├── MCP: MemPalace server
│   ├── MCP: Other tools (git, file, etc.)
│   ├── Skills: wiki-ingest, wiki-query, wiki-lint
│   └── Cron: nightly lint, weekly summary
├── MemPalace
│   ├── ChromaDB (local storage)
│   ├── SQLite knowledge graph
│   └── Palace: wings per project (homelab-infra, homelab-apps, sparkle-cps)
└── LLM Wiki
    ├── ~/workspace/homelab/wiki/ (or dedicated repo)
    ├── index.md, log.md
    ├── Entity pages (proxmox, traefik, pihole, etc.)
    ├── Concept pages (networking, storage, CI/CD, etc.)
    └── Schema in CLAUDE.md or dedicated config
```

### Alignment with Epic 2 (Persistent Memory)

The upcoming Epic 2 is about persistent memory for the AI dev container. These three systems directly address that goal:

| Epic 2 Need | Solution |
|-------------|----------|
| Cross-session memory | MemPalace (verbatim storage + semantic search) |
| Structured knowledge | LLM Wiki (synthesized, interlinked pages) |
| Autonomous maintenance | Hermes cron (lint, summarize, invalidate stale facts) |
| Self-improvement | Hermes skills (learn from usage patterns) |

### Phased Rollout

**Phase 1 — LLM Wiki (Lowest friction, immediate value)**
- Create wiki directory in homelab-playbook or dedicated repo
- Write schema defining structure for homelab knowledge
- Start ingesting existing docs, architecture decisions, retro notes
- Use from Claude Code sessions directly (no new infrastructure)

**Phase 2 — MemPalace (Add semantic memory)**
- `pip install mempalace` on ct-dev-homelab
- Initialize palace with wings per project
- Mine existing conversation exports
- Add MCP server to Claude Code config
- Test on ct-dev-test first per established workflow

**Phase 3 — Hermes Agent (Add autonomous capabilities)**
- Deploy Hermes in Docker on ct-dev-homelab (or dedicated container)
- Connect MemPalace as MCP tool
- Create skills for LLM Wiki operations
- Set up cron jobs for maintenance
- Enable messaging gateway (Telegram/Discord) for remote interaction

### Ansible Role Considerations

Each phase should have a corresponding Ansible role update in homelab-infra:

- `dev-host` role: add MemPalace pip package, wiki directory structure
- New `hermes-agent` role: Docker container, MCP config, cron setup
- Config managed via vault-encrypted variables for any API keys

---

## Part 6: Risks and Considerations

### Technical Risks

| Risk | Mitigation |
|------|-----------|
| ChromaDB resource usage on LXC | Monitor memory; ChromaDB is lightweight for small palaces |
| AAAK compression unreliable | Use raw mode only (project's own recommendation) |
| Hermes agent maturity | Start with MemPalace + Wiki first; add Hermes when stable |
| Token costs for wiki ingest | Batch ingests; use Haiku for routine operations |
| Knowledge drift between systems | Lint pass catches contradictions; wiki is source of truth for synthesis |

### Operational Risks

| Risk | Mitigation |
|------|-----------|
| Maintaining two knowledge systems | Clear separation: MemPalace = raw memory, Wiki = refined knowledge |
| Over-engineering for a homelab | Phase 1 (wiki only) is zero-infrastructure; scale only if valuable |
| Bootstrap problem (this container manages itself) | Wiki and palace data stored in git; reproducible via Ansible |

---

## Part 7: Recommendations

1. **Start with LLM Wiki** — It's free, zero-infrastructure, and directly useful in current Claude Code sessions. Create the schema, start ingesting your existing BMAD docs and architecture decisions.

2. **Add MemPalace for Epic 2** — It directly solves the persistent memory goal. Use raw mode, ignore AAAK. Set up palace wings per project.

3. **Evaluate Hermes for Epic 3 or later** — It's the agent runtime that ties everything together, but it's the most complex to deploy and the least critical for immediate needs.

4. **Keep LLM Wiki as the "source of refined truth"** — MemPalace stores everything; wiki stores understanding. When they conflict, investigate and update.

5. **Use the established test-then-deploy workflow** — Deploy each phase to ct-dev-test first, validate, then promote to ct-dev-homelab.

---

## Part 8: Obsidian + LLM Wiki Best Practices

### Canonical Directory Structure

The LLM Wiki pattern maps cleanly to an Obsidian vault:

```
project-wiki/                    ← Obsidian vault root
├── .obsidian/                   ← Obsidian config (gitignored selectively)
├── raw/                         ← Immutable source documents (human drops in)
├── wiki/                        ← LLM-owned pages (entities, concepts, summaries)
│   ├── entities/                ← Person, tool, service pages
│   ├── concepts/                ← Architectural patterns, methodologies
│   ├── decisions/               ← ADRs, retro learnings
│   └── meetings/                ← Meeting note summaries
├── outputs/                     ← Query results, generated reports
├── .drafts/                     ← Staging area for human review before promotion
├── _index.md                    ← Self-maintained page catalogue
├── _meta/
│   └── taxonomy.md              ← Controlled tag vocabulary
├── log.md                       ← Append-only operation log
└── SCHEMA.md                    ← LLM instructions (wiki conventions, workflows)
```

**Naming:** Kebab-case filenames (`quantum-computing.md`). No vector DB needed up to ~100 articles / 400K words — the LLM navigates via `_index.md`.

### YAML Frontmatter for Obsidian Compatibility

Every wiki page should include:

```yaml
---
title: Proxmox Clustering
confidence: 0.85
last_ingested: 2026-04-11
sources:
  - proxmox-docs-ha.pdf
  - meeting-2026-04-10.md
content_hash: abc123
stale: false
provenance: extracted    # extracted | inferred | ambiguous
tags:
  - infrastructure
  - proxmox
  - high-availability
---
```

Use Obsidian-native `[[wikilinks]]` for internal cross-references. After each ingest, a cross-linker pass scans for unlinked mentions and weaves them into wikilinks — this directly powers Obsidian's graph view and backlinks panel.

### Essential Obsidian Plugins

| Plugin | Purpose |
|--------|---------|
| **Dataview** | Query frontmatter: "all pages where confidence < 0.7 or stale = true" |
| **Templater** | Templates for new wiki pages so LLM output matches consistent structure |
| **Graph Analysis** | Visualize entity relationships, spot orphan pages |
| **Obsidian Git** | Auto-pull from container repos (1-5 min interval) |
| **Kanban** | Visualize sprint-status as kanban board |
| **Folder Notes** | Auto-create index notes per folder |

### LLM-Writes / Human-Reads Workflow

Key design principle: **separation of ownership**.

| Mechanism | Purpose |
|-----------|---------|
| **Separate vault** | Keep LLM wiki separate from hand-written notes to prevent hallucination contamination |
| **Draft staging** | New articles land in `.drafts/` for human review before promotion to `wiki/` |
| **Manual edit detection** | LLM skips pages a human has edited, preventing overwrites |
| **Lint health checks** | Detect contradictions, orphaned pages, stale claims. Run after every 10 ingests or monthly |
| **Filesystem watching** | Obsidian watches the filesystem natively — LLM-written files appear immediately |

### Community Implementations

Several open-source projects exist since Karpathy's post:

| Project | Approach |
|---------|----------|
| **Ar9av/obsidian-wiki** | Full framework for AI agents to build/maintain an Obsidian wiki |
| **kytmanov/obsidian-llm-wiki-local** | 100% local with Ollama — no cloud |
| **ekadetov/llm-wiki** | Claude Code plugin for persistent, compounding wikis in Obsidian |
| **AgriciDaniel/claude-obsidian** | Claude + Obsidian companion with /wiki, /save, /autoresearch commands |

---

## Part 9: Obsidian Multi-Vault Architecture

### The Setup

Each container has its own Obsidian vault (one per project). The user accesses all vaults from a laptop via git sync.

### Multi-Vault Capabilities in Obsidian

- Obsidian natively supports multiple vaults with a vault switcher (bottom-left icon)
- Multiple vaults can be open simultaneously in separate windows
- **No native cross-vault linking** — `[[wikilinks]]` only resolve within the current vault
- Each vault has its own `.obsidian/` with independent settings, plugins, and themes

### Cross-Vault Strategies

| Strategy | How It Works | Pros | Cons |
|----------|-------------|------|------|
| **Meta-vault with URI links** | Separate "hub" vault using `obsidian://open?vault=Name&file=Note` links | Clean isolation, per-project repos | No inline preview, requires all vaults registered |
| **Symlinks** | Symlink project folders into a mega-vault | Native wikilinks work across projects | Fragile with git, indexing overhead |
| **Single mega-vault** | One vault, folder-per-project | Full cross-linking, single search | Git conflicts, one plugin config for all |

### Recommended Approach: Separate Vaults + Meta-Vault

```
Laptop (Obsidian)
├── meta-vault/                    ← Hub with MOCs and URI links
│   ├── projects/
│   │   ├── homelab.md             ← MOC with obsidian:// links to homelab vault
│   │   └── sparkle-cps.md        ← MOC with obsidian:// links to sparkle vault
│   ├── shared/
│   │   ├── people.md             ← Cross-project entity (Tom, team members)
│   │   └── glossary.md           ← Shared terminology
│   └── dashboard.md              ← Dataview queries across local vault
│
├── homelab-wiki/                  ← Cloned from ct-dev-homelab git
│   └── (LLM Wiki structure)
│
└── sparkle-cps-wiki/              ← Cloned from ct-sparkle-cps git
    └── (LLM Wiki structure)
```

### Git Sync Pattern

**One repo per vault** is strongly recommended:
- Each container owns its own repo — clean push/pull boundaries
- Monorepo with multiple vault roots breaks Obsidian Git plugin expectations
- On the laptop, each vault is cloned independently

**Critical .gitignore entries:**
```
.obsidian/workspace.json
.obsidian/workspace-mobile.json
.obsidian/plugins/*/data.json   # Plugin state (optional — may want to sync)
```

### Container-Side Auto-Push

Each container's Hermes cron pushes wiki changes:
```bash
# In Hermes cron (every 5 min or post-ingest)
cd /home/developer/workspace/<project>/wiki
git add -A
git diff --cached --quiet || git commit -m "wiki: auto-update $(date +%Y-%m-%d-%H%M)"
git push
```

Laptop's Obsidian Git plugin auto-pulls every 1-5 minutes.

---

## Part 10: Knowledge Ingestion Pipelines

### MCP Tool Landscape

| Service | MCP Server | Key Tools | Auth | Push/Pull |
|---------|-----------|-----------|------|-----------|
| **Linear** | Official (remote, hosted) | 21 tools: find/create/update issues, projects, comments | OAuth via Linear app | Pull-only (query). No MCP webhooks. |
| **Granola AI** | Native (already connected) | 5 tools: `list_meetings`, `get_meetings`, `get_meeting_transcript`, `query_granola_meetings`, `list_meeting_folders` | OAuth | Pull-only |
| **Azure DevOps** | Microsoft official (GA, remote hosted) | Work items, PRs, builds, test plans, docs | Azure AD | Pull-only |
| **Slack** | Hermes gateway (native) | Send/receive messages via Hermes messaging | Bot token | Push (receives messages) |

### Workflow 1: Web Article → LLM Wiki

**Trigger:** User sends URL to Hermes via Slack/Telegram/CLI

```
User sends URL + optional notes to Hermes
    ↓
Hermes fetches article content (browser/fetch tool)
    ↓
Hermes triggers BMAD technical-research skill via Claude Code
    (passes article content + user notes as context)
    ↓
Claude Code produces research output
    ↓
Hermes runs wiki-ingest skill:
    1. Creates summary page in wiki/
    2. Creates/updates entity pages for mentioned technologies
    3. Updates _index.md
    4. Appends to log.md
    ↓
New pages land in .drafts/ if configured (or directly in wiki/)
    ↓
Git auto-push → Obsidian auto-pull on laptop
```

**Hermes skill definition:**
```
Name: article-ingest
Trigger: User sends URL
Steps: fetch → research → wiki-ingest → git-push
```

### Workflow 2: Linear Ticket → Automated Triage + Action

**Trigger:** Hermes cron polls Linear MCP every 5 minutes for new issues in "Inbox" state

```
Hermes cron (every 5 min):
    linear_search_issues(status: "Inbox", created_after: last_check)
    ↓
For each new issue:
    ↓
Hermes classifies type (from title + description):
    ├── Bug → Claude Code: root cause analysis, fix identification
    │         BMAD: /bmad-code-review if code referenced
    │         Output: Linear comment with findings, move to "Triaged"
    │
    ├── Feature → Claude Code: /bmad-technical-research
    │             BMAD: /bmad-brainstorming for approach options
    │             Output: Linear comment with research, create sub-issues
    │
    ├── Idea → BMAD: /bmad-brainstorming
    │          Output: Linear comment with evaluation, wiki page
    │
    └── Suggestion → Hermes evaluates, drafts response
                     Output: Linear comment with assessment
    ↓
Wiki-ingest: decision/finding page created
    ↓
Linear ticket updated (label, status, comment with findings)
    ↓
Slack notification: "Triaged [TICKET-123]: Bug — root cause identified"
```

**Parallel MCP usage:** When a Linear ticket references an Azure DevOps repo, Hermes can pull PR/build context from Azure DevOps MCP simultaneously.

**Alternative trigger:** Instead of cron polling, Linear webhook → Slack channel notification → Hermes Slack gateway receives message → acts immediately. More real-time but requires webhook setup.

### Workflow 3: Granola Meeting → LLM Wiki

**Trigger:** Hermes cron polls Granola MCP for new meetings since last check

```
Hermes cron (every 30 min or post-meeting):
    list_meetings(since: last_check)
    ↓
For each new meeting:
    get_meeting_transcript(meeting_id)
    get_meetings(meeting_id)  ← structured notes
    ↓
Hermes extracts:
    - Key decisions
    - Action items (with owners)
    - Entity mentions (people, projects, tools)
    - Topics discussed
    ↓
Wiki-ingest skill:
    1. Creates meeting page in wiki/meetings/
    2. Updates entity pages for mentioned people/projects
    3. Creates/updates action items page
    4. Cross-links to relevant concept/decision pages
    5. Updates _index.md
    ↓
If action items map to Linear: create Linear issues
If action items map to Azure DevOps: create work items
    ↓
Git auto-push → Obsidian auto-pull
```

**Granola plan note:** Basic plan limits to 30 days and no transcripts. Business/Enterprise needed for full history and transcript access.

### Combined Ingestion Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    INGESTION SOURCES                          │
│                                                              │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌──────────────┐  │
│  │ Web URL  │  │ Linear  │  │ Granola │  │ Azure DevOps │  │
│  │ (manual) │  │  (MCP)  │  │  (MCP)  │  │    (MCP)     │  │
│  └────┬─────┘  └────┬────┘  └────┬────┘  └──────┬───────┘  │
│       │              │            │               │          │
│  User sends     Cron poll     Cron poll      On-demand      │
│  via Slack      5 min         30 min         (referenced)   │
└───────┼──────────────┼────────────┼───────────────┼──────────┘
        │              │            │               │
        ▼              ▼            ▼               ▼
┌──────────────────────────────────────────────────────────────┐
│                    HERMES AGENT                               │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Classification & Routing                             │   │
│  │  - Article → research + wiki ingest                   │   │
│  │  - Bug ticket → fix analysis + code review            │   │
│  │  - Feature ticket → research + brainstorm             │   │
│  │  - Meeting → extract decisions + action items         │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         │                                    │
│  ┌──────────────────────▼───────────────────────────────┐   │
│  │  Processing (via Claude Code + BMAD skills)           │   │
│  │  - /bmad-technical-research                           │   │
│  │  - /bmad-brainstorming                                │   │
│  │  - /bmad-code-review                                  │   │
│  │  - wiki-ingest skill                                  │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         │                                    │
└─────────────────────────┼────────────────────────────────────┘
                          │
            ┌─────────────┼─────────────┐
            ▼             ▼             ▼
      ┌──────────┐  ┌──────────┐  ┌──────────┐
      │ LLM Wiki │  │ MemPalace│  │ Linear/  │
      │ (synth)  │  │  (raw)   │  │ ADO/Slack│
      │          │  │          │  │ (output) │
      └──────────┘  └──────────┘  └──────────┘
            │
            ▼
      Git push → Obsidian (laptop)
```

---

## Part 11: Per-Container Architecture (Option B — Revised)

### Complete Stack Per Container

```
ct-dev-homelab (150)
├── Hermes Agent
│   ├── Built-in: MEMORY.md (project-specific agent notes)
│   ├── Provider: Honcho (shared user model across containers)
│   ├── MCP clients:
│   │   ├── OMEGA (shared cross-project memory)
│   │   ├── MemPalace (local project memory)
│   │   ├── Linear (ticket management)
│   │   ├── Granola (meeting notes)
│   │   └── Azure DevOps (CPS repos, conditional)
│   ├── Skills:
│   │   ├── article-ingest (URL → research → wiki)
│   │   ├── ticket-triage (Linear → classify → act)
│   │   ├── meeting-ingest (Granola → wiki)
│   │   ├── wiki-ingest (core wiki write operations)
│   │   ├── wiki-query (search wiki pages)
│   │   └── wiki-lint (health check + fix)
│   ├── Cron:
│   │   ├── Linear poll (every 5 min)
│   │   ├── Granola poll (every 30 min)
│   │   ├── Wiki lint (weekly)
│   │   └── Git auto-push (every 5 min)
│   └── Gateway: Slack (receive URLs, notifications)
│
├── MemPalace
│   ├── ChromaDB (local)
│   ├── SQLite knowledge graph
│   └── Wing: "homelab" (rooms: infra, apps, playbook, epics)
│
├── LLM Wiki (Obsidian vault)
│   ├── raw/
│   ├── wiki/ (entities, concepts, decisions, meetings)
│   ├── .drafts/
│   ├── _index.md, log.md, SCHEMA.md
│   └── .obsidian/ (vault config)
│
└── OMEGA MCP (shared, networked)
    └── Cross-project decisions, user profile, checkpoints
```

### Shared vs Local Summary

| Layer | Scope | System | Where |
|-------|-------|--------|-------|
| User identity | All containers | Honcho (cloud) | honcho.dev |
| Cross-project knowledge | All containers | OMEGA MCP | Networked service |
| Project knowledge (synthesized) | Per-container | LLM Wiki / Obsidian vault | Local git repo |
| Project memory (raw) | Per-container | MemPalace | Local ChromaDB |
| Agent self-improvement | Per-container | Hermes MEMORY.md + Skills | Local ~/.hermes/ |
| Ticket/meeting ingestion | Per-container (filtered) | Hermes + MCP clients | Linear/Granola/ADO |

---

## Part 12: Epic Planning Guidance

### Proposed Epics

**Epic 5: LLM Wiki + Obsidian Integration**

| Story | Description |
|-------|-------------|
| 5.1 | Create LLM Wiki directory structure and SCHEMA.md per project |
| 5.2 | Build wiki-ingest Hermes skill (create pages, update index, cross-link) |
| 5.3 | Build wiki-query Hermes skill (search pages, synthesize answers) |
| 5.4 | Build wiki-lint Hermes skill (contradictions, orphans, stale claims) |
| 5.5 | Configure Obsidian vault per container with git auto-push |
| 5.6 | Set up laptop meta-vault with Obsidian Git, Dataview dashboards |
| 5.7 | Build article-ingest skill (URL → BMAD research → wiki) |
| 5.8 | Wire Hermes cron for wiki lint and git push |

**Epic 6: MemPalace — Deep Memory**

| Story | Description |
|-------|-------------|
| 6.1 | Install MemPalace and configure MCP server per container |
| 6.2 | Initialize palace wings per project with room taxonomy |
| 6.3 | Mine existing conversation history (Claude, Slack exports) |
| 6.4 | Wire Hermes MemPalace skill (search, diary write, KG query) |
| 6.5 | Implement query hierarchy: wiki first → MemPalace fallback |
| 6.6 | Configure MemPalace Ansible role for one-command deployment |

**Epic 7: Knowledge Ingestion Pipelines**

| Story | Description |
|-------|-------------|
| 7.1 | Connect Hermes to Linear MCP, build ticket-triage skill |
| 7.2 | Connect Hermes to Granola MCP, build meeting-ingest skill |
| 7.3 | Connect Hermes to Azure DevOps MCP (conditional, CPS containers) |
| 7.4 | Build classification router (bug/feature/idea/suggestion) |
| 7.5 | Wire BMAD skill delegation per ticket type |
| 7.6 | Set up Hermes cron polling for Linear (5 min) and Granola (30 min) |
| 7.7 | Configure Slack gateway for manual URL ingestion |
| 7.8 | End-to-end integration test: ticket → triage → action → wiki → Obsidian |

### Dependencies

```
Epic 3 (Hermes Director) — prerequisite for all
    ↓
Epic 5 (LLM Wiki + Obsidian) — no dependency on 6 or 7
Epic 6 (MemPalace) — enhanced by 5 (query hierarchy uses both)
    ↓
Epic 7 (Ingestion Pipelines) — depends on 5 (wiki-ingest) and optionally 6
```

---

## Sources

| Source | URL | Accessed |
|--------|-----|----------|
| LLM Wiki (Karpathy gist) | https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f | 2026-04-11 |
| MemPalace repository | https://github.com/milla-jovovich/mempalace | 2026-04-11 |
| MemPalace SKILL.md (OpenClaw) | https://github.com/milla-jovovich/mempalace/blob/main/integrations/openclaw/SKILL.md | 2026-04-11 |
| Hermes Agent repository | https://github.com/NousResearch/hermes-agent | 2026-04-11 |
| Hermes Agent docs — Memory | https://hermes-agent.nousresearch.com/docs/user-guide/features/memory | 2026-04-11 |
| Hermes Agent docs — Memory Providers | https://hermes-agent.nousresearch.com/docs/user-guide/features/memory-providers | 2026-04-11 |
| Hermes Agent docs — MCP | https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp | 2026-04-11 |
| Linear MCP docs | https://linear.app/docs/mcp | 2026-04-11 |
| Granola AI MCP | https://www.granola.ai/blog/granola-mcp | 2026-04-11 |
| Azure DevOps MCP | https://github.com/microsoft/azure-devops-mcp | 2026-04-11 |
| Ar9av/obsidian-wiki | https://github.com/Ar9av/obsidian-wiki | 2026-04-11 |
| kytmanov/obsidian-llm-wiki-local | https://github.com/kytmanov/obsidian-llm-wiki-local | 2026-04-11 |
| ekadetov/llm-wiki (Claude Code plugin) | https://github.com/ekadetov/llm-wiki | 2026-04-11 |
| AgriciDaniel/claude-obsidian | https://github.com/AgriciDaniel/claude-obsidian | 2026-04-11 |
