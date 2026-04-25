---
type: architecture
product: context-stack
version: 1.0.0-draft
status: draft
date: 2026-04-25
prd_ref: prd.md
brief_ref: product-brief.md
---

# Context Stack — Architecture

## 1. Executive Architecture Summary

Context Stack is a four-tier context substrate for Claude Code, deliberately small in surface area and sequenced to ship in four sprints. The four layers, in cost-order from cheapest to most expensive: a **file-based wiki** at `homelab-playbook/wiki/` (Tier 1, < 200 ms file-read, zero retrieval tokens); the **GitNexus code-graph** MCP server on the workstation (Tier 2, npm-distributed, AST-first via tree-sitter, LadybugDB-backed, auto-reindex on every commit); the **Graphiti memory layer** running on `ct-ai-01` (Tier 3, FalkorDB backend, MCP HTTP transport, `gpt-4o-mini` extraction LLM, `text-embedding-3-small` embeddings, single `tom-personal` group_id); and Claude Code's pre-existing **auto-memory** (Tier 4, `MEMORY.md` markdown, deterministic, unaffected). The four tiers compose: the wiki holds *current state*, GitNexus answers *structural code* questions, Graphiti tracks *dated decisions and supersession trails*, auto-memory is the *passive session-start ground truth*.

The deployment model is hybrid by design. Tier 1 (wiki) and Tier 2 (GitNexus) run entirely on the operator's workstation — source code never leaves the machine for code-parsing passes (NFR-PRIV-001). Tier 3 (Graphiti + FalkorDB) runs in two Docker containers on `ct-ai-01`, bound to `127.0.0.1` and reached via Tailscale tailnet — the same network posture as the operator's existing `phone-notifications-tailscale` pattern. Tier 4 is filesystem-local. Embeddings cross to OpenAI; nothing else does. Phase 4 stretch routes Graphiti's LLM call through the operator's `hybrid_gemma_serving` LiteLLM gateway via `OPENAI_BASE_URL` env var override (no Graphiti fork required) behind a 95%-well-formed-JSON validation gate.

The product is a consolidation play: it decommissions MemPalace + OMEGA in Phase 1 (single PR, 8 sequenced commits, tagged `phase-1-decommission-complete`) before introducing GitNexus + Graphiti in Phase 2, the wiki tier in Phase 3, and the LiteLLM bridge in Phase 4 (stretch). The architectural priority is reversibility: every component is unwireable in ≤ 1 day (NFR-MAINT-001), every adopted external component has a documented exit ramp (NFR-SUPP-002), and the decommission rollback (re-install OMEGA + MemPalace from the prior commit) is a documented runbook validated on `ct-dev-homelab` before any production-class promotion.

The architecture's biggest bet is on **MCP-first integration** for the two heavyweight tiers and **file-first integration** for the lightweight tier — codified in ADR-005. The OMEGA + MemPalace failure pattern was bespoke skill scaffolding; the fix is to live on the standard MCP manifest surface for code-graph and memory, and to keep the wiki ergonomically free of any such surface. The single skill bet is `wiki-query` — intentionally thin, plain file-read, zero LLM dependency (FR-WIKI-009).

## 2. System Context (C4 Level 1)

```
                                                                                                             
                +--------------------+        +-----------------+        +----------------+                 
                |     Operator       |        |  Claude Code    |        |  Anthropic API |                 
                |   (tomamourette)   |  CLI   |   (workstation) | --HTTPS--> |  (Sonnet 4.7)  |             
                +---------+----------+        +--------+--------+        +----------------+                 
                          |                            |                                                    
                          | reads/writes               | tool calls (MCP) + reads (wiki)                    
                          v                            v                                                    
                                                                                                             
              +---------------------------- Context Stack -----------------------------+                    
              |                                                                        |                    
              |  +-----------+   +-------------+   +----------------------+   +-----+  |                    
              |  |  Wiki     |   |  GitNexus   |   |  Graphiti stack      |   | LLM |  |                    
              |  |  (md      |   |  MCP server |   |  (FalkorDB +         |   | Wiki|  |                    
              |  |   tree)   |   |  + LadybugDB|   |   graphiti-mcp)      |   |Bridge| |                    
              |  |  Tier 1   |   |  Tier 2     |   |  Tier 3              |   |Phase4| |                    
              |  +-----------+   +-------------+   +----------+-----------+   +--+--+  |                    
              |   workstation     workstation      ct-ai-01 LXC                |       |                    
              +-------------------------------------------------+--------------+-------+                    
                                                                |                      |                    
                              embeddings + extraction           |   stretch:           |                    
                                          v                     |   route LLM calls    |                    
                                  +---------------+             |   via LiteLLM        |                    
                                  |  OpenAI API   | <----------+'                      |                    
                                  | (gpt-4o-mini, |                                     |                    
                                  |  embed-3-sm.) |              hybrid_gemma_serving <+                    
                                  +---------------+              (separate epic)                            
                                                                                                             
              Auto-memory MEMORY.md (Tier 4) lives at ~/.claude/projects/.../memory/ — workstation-local.    
```

External actors: the operator (single user), Claude Code (the daily-driver CLI), Anthropic API (Claude Code's underlying model), OpenAI API (Graphiti's extraction + embeddings), and the future `hybrid_gemma_serving` LiteLLM gateway. System boundary: everything inside the dashed box is Context Stack; OpenAI/Anthropic are external dependencies; `hybrid_gemma_serving` is a peer epic, not part of Context Stack.

## 3. Container Diagram (C4 Level 2)

```
 Workstation                                                  ct-ai-01 (LXC, Tailscale-reachable)
+-----------------------------------------+                  +-------------------------------------+
|                                         |                  |                                     |
|  Claude Code (CLI process)              |                  |   Docker Compose stack              |
|     |                                   |                  |   (/srv/graphiti/docker-compose.yml)|
|     |--reads MEMORY.md (Tier 4)         |                  |                                     |
|     |                                   |                  |   +---------------------------+     |
|     |--reads wiki/index.md + entries    |                  |   |  graphiti-mcp container   |     |
|     |       (Tier 1 via wiki-query)     |                  |   |  127.0.0.1:8000 → 0.0.0.0 |     |
|     |                                   |                  |   |  HTTP MCP transport       |     |
|     |--MCP stdio: GitNexus               |                  |   +-------------+-------------+     |
|     |       (Tier 2)                    |                  |                 | redis://     |     |
|     |       npx gitnexus@v1.6.3 mcp     |                  |                 v              |     |
|     |                                   |                  |   +---------------------------+     |
|     |--MCP HTTP: Graphiti               |                  |   |  graphiti-falkordb        |     |
|     |       http://ct-ai-01:8000/mcp/   |    Tailscale     |   |  127.0.0.1:6379           |     |
|     +-----------------------------------+ <--------------> |   |  /srv/graphiti/data       |     |
|                                         |   tailnet (auth) |   |  (AOF + RDB persist)      |     |
|     ~/.claude/                          |                  |   +---------------------------+     |
|       settings.json (PreToolUse,        |                  |                                     |
|         PostToolUse hooks)              |                  |   /srv/graphiti/                    |
|       skills/wiki-query/SKILL.md        |                  |     .env (mode 600)                 |
|                                         |                  |     scripts/cost-cap.sh             |
|     ~/workspace/homelab/                |                  |     scripts/cypher-export.sh        |
|       homelab-playbook/wiki/            |                  |     cron.d/graphiti-backup          |
|       (homelab/, homelab-bootstrap/,    |                  |                                     |
|        homelab-playbook/)               |                  |                                     |
|     ~/.gitnexus/ (LadybugDB index)      |                  |   CT101 (separate)                  |
|                                         |                  |     ntfy (alert sink)               |
+-----------------------------------------+                  +-------------------------------------+
```

Key boundaries:
- **MCP transports:** GitNexus = stdio (in-process, no network); Graphiti = HTTP over Tailscale.
- **Privacy boundary:** workstation-bounded code (no source code leaves machine); fact-text + embeddings cross to OpenAI; LLM extraction prompts cross to OpenAI in Phase 1-3, to LiteLLM in Phase 4.
- **Auth boundary:** Tailscale tailnet authenticates `ct-ai-01` ↔ workstation; FalkorDB password protects the Redis surface inside the container; OpenAI API key in `/srv/graphiti/.env` mode 600.

## 4. Component Diagrams (C4 Level 3) — per layer

### 4.1 Code-graph layer (GitNexus)

```
                +---------------------------------------------------+
                |  GitNexus MCP server (Node.js, npm gitnexus@1.6.3)|
                |                                                   |
                |  +-----------+  +----------+  +-----------------+ |
                |  | tree-sitter |  | LadybugDB |  | MCP tool surface| |
                |  | parsers   |->| graph    |->| - cypher        | |
                |  | (25 langs)|  | engine   |  | - impact        | |
                |  +-----------+  +----------+  | - context       | |
                |                                | - reindex       | |
                |                                +-----------------+ |
                +-----------------------+---------------------------+
                                        ^                ^
                                        | stdio          | hooks
                                        |                |
                  PreToolUse: enrich    |                |  PostToolUse-on-commit: reindex
                                        v                v
                              +-----------------------------+
                              | Claude Code (workstation)   |
                              +-----------------------------+
```

- **Install:** `npm install -g gitnexus@1.6.3` (pinned per FR-DEP-010 spirit) + `npx gitnexus setup` to register MCP across Claude Code (and any other supported clients). FR-CG-001.
- **Topology:** parent-folder mode over `~/workspace/homelab/` (covers all three sibling repos). FR-CG-003.
- **Hooks:** PreToolUse + PostToolUse, registered in `~/.claude/settings.json`. FR-CG-004.
- **Reindex:** auto on every commit via PostToolUse-on-Bash hook (no path/branch filter — FR-CG-005 / ADR-014 downgraded to COULD; default no-filter).
- **Privacy:** entirely local; no LLM calls; tree-sitter parses → LadybugDB. FR-CG-002, FR-CG-012.
- **Export:** `scripts/gitnexus-export.sh` (ADR-012) calls the `cypher` tool and writes NDJSON. FR-CG-010.

### 4.2 Memory layer (Graphiti + FalkorDB)

```
                +-----------------------------------------------------+
                |  graphiti-mcp container (zepai/graphiti-mcp:v1.0.2) |
                |                                                     |
                |  +-------------------+   +----------------------+   |
                |  | OpenAI client     |   | MCP tool surface     |   |
                |  | gpt-4o-mini ext.  |   | - add_episode        |   |
                |  | text-embed-3-sm.  |   | - search_facts       |   |
                |  | SEMAPHORE_LIMIT=5 |   | - search_nodes       |   |
                |  +-------------------+   | - get_episodes       |   |
                |                          | - delete_*           |   |
                |                          | - clear_graph        |   |
                |                          | - get_status         |   |
                |                          +----------+-----------+   |
                +-----------------------------+-------+---------------+
                                              | redis://falkordb:6379
                                              v
                +-----------------------------------------------------+
                |  graphiti-falkordb container (falkordb/falkordb)    |
                |  - OpenCypher engine                                |
                |  - AOF + RDB persistence                            |
                |  - /data on volume → /srv/graphiti/data on host     |
                |  - 127.0.0.1:6379 + 127.0.0.1:3000 (Browser UI)     |
                +-----------------------------------------------------+
```

- **Backend:** FalkorDB (ADR-001). FR-MEM-001.
- **Transport:** MCP HTTP, `127.0.0.1:8000` bind, reach via Tailscale (FR-MEM-002, FR-MEM-003).
- **Models:** `gpt-4o-mini` LLM (ADR-002), `text-embedding-3-small` embeddings (ADR-003). FR-MEM-004.
- **Namespace:** all writes use `group_id="tom-personal"` (FR-MEM-005).
- **Throttle:** `SEMAPHORE_LIMIT=5` baseline; ADR-008 cron drops to 1 if daily cap hit (FR-MEM-006, FR-OBS-002).
- **Persistence:** AOF (default-on) + RDB; backup cadence per ADR-007.
- **Telemetry:** disabled (`GRAPHITI_TELEMETRY_ENABLED=false`). FR-MEM-011.

### 4.3 Wiki layer (file-tree + wiki-query skill)

```
                +-----------------------------------------------------+
                |  ~/.claude/skills/wiki-query/                       |
                |   SKILL.md (frontmatter + instructions)             |
                |   description: triggers on "wiki", "tailscale       |
                |   policy", "runbook for", etc.                      |
                |   allowed-tools: Read                               |
                +-------------------+---------------------------------+
                                    | Read
                                    v
                +-----------------------------------------------------+
                |  homelab-playbook/wiki/                             |
                |    index.md          ← entry point (auto-rebuilt)   |
                |    _schema.md        ← frontmatter spec             |
                |    architecture/     ← cross-product decisions      |
                |    runbooks/         ← step-by-step procedures      |
                |    decisions/        ← distilled prior decisions    |
                |    glossary/         ← term definitions             |
                |    projects/         ← cross-link pointers          |
                |                                                     |
                |  Each page: YAML frontmatter (title, slug,          |
                |  category, last_reviewed, owner, related_pages,     |
                |  related_frs, related_adrs, status, supersedes,     |
                |  superseded_by) + body sections.                    |
                |                                                     |
                |  scripts/wiki-lint.sh  ← link checker, last_reviewed|
                |                          warn, index.md regen       |
                +-----------------------------------------------------+
```

- **Schema:** ADR-006 (frontmatter, directory structure, slugs, link rules).
- **Skill design:** ADR-009 (read-on-demand via `index.md`, no preload).
- **Tier-of-truth division:** ADR-013 (wiki = current state; Graphiti = trail/supersession; auto-memory = pointers; GitNexus = code structure).

### 4.4 LiteLLM bridge (Phase 4 — stretch)

```
                Phase 1-3 path (default):
                graphiti-mcp ──HTTPS──► api.openai.com (gpt-4o-mini, text-embedding-3-small)

                Phase 4 path (post-validation gate):
                graphiti-mcp ──HTTP──► hybrid-gemma-litellm.tail-scale.ts.net:4000/v1
                              (OPENAI_BASE_URL override; LLM only)
                                          │
                                          ├──► local Gemma 27B reasoner (via LiteLLM)  [LLM]
                                          │
                                          └──► api.openai.com  [embeddings: text-embedding-3-small]
                                               (LiteLLM transparent passthrough)
```

- **Implementation:** ADR-011 — `OPENAI_BASE_URL` + `MODEL_NAME` env var override; no Graphiti fork.
- **Validation gate:** 50-fact validation set; ≥ 95% well-formed JSON to promote (FR-LLM-005).
- **Fallback:** auto-revert env vars to OpenAI defaults on validation failure (FR-LLM-006, FR-LLM-008).
- **Embeddings:** stay on OpenAI in all phases (ADR-003 / FR-LLM-004).

### 4.5 Decommission flow (E1)

```
Pre-Sprint-1 state:                Sprint 1 (8 commits, single PR):
+-------------------+              1. disable OMEGA hooks (settings.json)
| ~/.claude/        |              2. remove OMEGA hooks
|  settings.json    |              3. uninstall omega-memory + role + group_vars
|   omega entries x4|              4. remove MemPalace store + role + skills
| ~/.omega/         |              5. remove wire-mempalace.yml + knowledge-query
| ~/.mempalace/     |              6. remove mempalace conditionals (Hermes Jinja x3)
| ai-dev-omega-     |              7. write decommission doc
|   memory role     |              8. run Hermes verify on ct-dev-homelab
| ai-dev-mempalace  |
|   role            |              Post-Sprint-1 state (tagged):
| Hermes:           |              +-------------------+
|   mempalace-kg-   |              | (clean)           |
|     query skill   |              | grep -i 'mempalace|omega'
|   mempalace-diary |              |   homelab/ → 0    |
|   mempalace-search|              | pgrep mempalace|  |
|   wire-mempalace.yml|            |   omega → 0       |
|   config.yaml.j2  |              | Hermes verify → 0 |
|     conditionals  |              | tag: phase-1-     |
|   defaults/main.yml|             |   decommission-   |
|     conditionals  |              |   complete        |
|   verify.yml      |              +-------------------+
|     conditionals  |
| knowledge-query   |
|   orchestrator    |
+-------------------+
```

ADR-010 captures the single-PR-with-sequenced-commits strategy.

## 5. Cross-cutting concerns

### 5.1 Privacy boundary

| Crosses the wire | Stays local |
|---|---|
| Graphiti episode prompts (text descriptions of decisions/lessons) → OpenAI for extraction | Source code (parsed by GitNexus tree-sitter on workstation) |
| Embedding payloads (~50 tokens/query, ~2 KB/episode) → OpenAI | Wiki content (read directly by Claude Code; never leaves workstation) |
| Phase 4: LLM extraction prompts → LiteLLM gateway → local Gemma reasoner | Auto-memory `MEMORY.md` (filesystem) |
| Claude Code's own conversation tokens → Anthropic API (existing, not Context Stack's surface) | GitNexus LadybugDB graph |
| Graphiti MCP HTTP traffic → Tailscale tailnet (encrypted, authenticated) | FalkorDB Redis traffic (loopback only inside Docker network) |

NFR-PRIV-001 enforced by ADR-004 (GitNexus local-only, no LLM calls); NFR-PRIV-002 documents the embedding cloud-line as accepted; NFR-PRIV-003 (Tailscale-only for phone-facing surfaces) is reserved for forward use — none in Phase 1-4 scope.

### 5.2 Observability

| Signal | Source | Cadence | Target |
|---|---|---|---|
| GitNexus reindex duration | PostToolUse hook log | Per-commit | ≤ 30 s incremental, ≤ 60 s full (NFR-PERF-004/005) |
| GitNexus tool-hit-rate | Hook log + manual journal | Weekly | ≥ 1 read/session (FR-OBS-006) |
| Graphiti search latency | `docker compose logs graphiti-mcp` | Spot-check | p95 < 500 ms (NFR-PERF-002) |
| Graphiti episode count | `get_episodes` tool / FalkorDB Browser | Weekly | ≥ 25/week after week 2 (K4) |
| Graphiti good-catch tally | Operator-tagged retro entries | Weekly | ≥ 3 over 4-week pilot (FR-OBS-005) |
| Daily OpenAI spend | `cost-cap.sh` cron poll | Every 30 min | < $1/day (NFR-COST-002, ADR-008) |
| Monthly all-in spend | OpenAI billing + Anthropic usage export | Weekly summed | < $20/month (NFR-COST-001, K3) |
| Container health | `docker compose ps` + `redis-cli PING` | On-demand | both Up, PONG |
| FalkorDB resident memory | `docker stats` | 24 h sample @ week 4 | < 200 MB (NFR-FOOTPRINT-001) |
| Wiki link integrity | `scripts/wiki-lint.sh` | Pre-commit | exit 0 |

A weekly retro template (referenced from FR-OBS-004) collects K1-K6 measurements and a one-paragraph subjective note.

### 5.3 Security

- **API-key handling:** all secrets in `/srv/graphiti/.env` mode 600; never committed (FR-DEP-008). The operator's existing Sparkle-style ansible-vault pattern is available if vault-rotation discipline is needed.
- **MCP auth:** Graphiti HTTP MCP relies on Tailscale tailnet authentication; no in-protocol auth (consistent with the operator's `phone-notifications-tailscale` pattern). FalkorDB password protects the Redis surface inside the container network.
- **Supply-chain (the graphify vs graphifyy lesson):**
  - GitNexus: `npm install -g gitnexus@1.6.3` — explicit version pin, single canonical name (no known typosquat as of April 2026).
  - Graphiti: pin `zepai/graphiti-mcp:v1.0.2` and `falkordb/falkordb:<pinned>` — never `:latest` (FR-DEP-010 spirit).
  - graphifyy double-y was the exemplar lesson; we're not adopting graphify but the lesson generalises: **always verify package name + maintainer + checksum on first install**.
- **Path safety:** `wiki-query` skill uses slug-based addressing constrained to `homelab-playbook/wiki/` — no user-controlled path traversal surface.
- **No telemetry:** Graphiti telemetry off (FR-MEM-011); GitNexus has no documented telemetry; check at install (week 0).

### 5.4 Backup and recovery

- **Graphiti:** ADR-007 — three-layer backup (in-process AOF + daily AOF rewrite cron + weekly RDB cron + monthly Cypher JSON export). Restore drill quarterly. Captured under FR-MEM-014.
- **Wiki:** inherent (markdown in git; NFR-PORT-003). Backed up by whatever backs up the homelab-playbook repo.
- **GitNexus index:** rebuildable from source code via full reindex (≤ 60 s); not separately backed up.
- **Auto-memory:** filesystem-local; whatever backs up the workstation `~/.claude/` covers it.
- **Decommission rollback:** FR-DEP-007 — re-install OMEGA + MemPalace from prior commit on tagged release (`phase-1-decommission-complete`).

### 5.5 Cost controls

- **NFR-COST-001 < $20/month:** weekly spend check (FR-OBS-001 / ADR-014: now SHOULD); operator-journaled.
- **NFR-COST-002 < $1/day:** ADR-008 cron-driven OpenAI Usage API poll on `ct-ai-01` (every 30 min); auto-throttle `SEMAPHORE_LIMIT=5 → 1` when threshold hit; ntfy alert via CT101; auto-restore at UTC day rollover.
- **Per-episode cost ceiling:** `gpt-4o-mini` at ~$0.0006/episode → ~500 episodes consumes ~$0.30. Operator's profile (~50 sessions × ~10 episodes/month = 500/month) stays well under the cap.
- **Phase 4 cost-neutrality:** NFR-COST-003 — LiteLLM bridge must not increase spend; embeddings stay on OpenAI per ADR-003 so the only delta is the LLM-extraction line.

## 6. Data Models

### 6.1 Graphiti episode/entity/edge model

Graphiti stores three primary shapes:

- **Episode:** a `(name, episode_body, source, source_description, group_id, reference_time?)` record. The body is freeform text; Graphiti's LLM extracts entities + relations and writes them as nodes/edges. UUID returned. Captured by `add_episode`.
- **Entity (node):** `(uuid, name, summary, group_id, created_at, valid_at?, invalid_at?)`. Multiple labels possible.
- **Edge (fact):** `(uuid, source_node, target_node, name, fact, group_id, valid_at, invalid_at?, expired_at?, created_at)`. Bi-temporal — `valid_at` is when the fact became true in the world; `created_at` is when the system learned it.

What it stores: dated decisions, lessons, project state changes, supersession chains. What it does not store (per ADR-013): static structural facts (in wiki), code definitions/references (in GitNexus), one-line preferences (in `MEMORY.md`).

Query surface: `search_facts(query, group_id, max_facts)` (text similarity over edges) and `search_nodes(query, group_id, max_nodes)` (text similarity over entities). Bi-temporal queries (e.g., "as of date X") are constructable via Cypher but the MCP tool surface exposes the common patterns.

### 6.2 Wiki page schema

ADR-006 normative schema (frontmatter + body conventions). Every page MUST carry:
- `title`, `slug`, `category` (one of: architecture / runbooks / decisions / glossary / projects)
- `last_reviewed` (ISO date), `owner`
- `related_pages` (slug list), `related_frs` (FR-ID list), `related_adrs` (ADR-NNN list)
- `status` (draft / stable / superseded), `supersedes`, `superseded_by`

Body sections (where applicable, in order): `## Summary`, `## Context`, `## Procedure / Decision / Definition`, `## Cross-references`. Cross-refs use `[text](slug)` form (slug-based). Link checker = `scripts/wiki-lint.sh`.

### 6.3 GitNexus graph export schema

ADR-012 normative schema — Context-Stack-controlled NDJSON:

```jsonl
{"type":"node","id":"...","labels":["Function"],"props":{"name":"add_episode","file":"...","line":234}}
{"type":"edge","id":"...","src":"...","dst":"...","kind":"REFERENCES","props":{"line":56}}
```

This is *Context Stack's* export shape, not GitNexus's internal one. The wrapper script `scripts/gitnexus-export.sh` is the single source of truth for the export format; LadybugDB internals are private. FR-CG-010 acceptance is satisfied by running the wrapper, not by GitNexus's documented export format.

## 7. Integration Surfaces

### 7.1 MCP servers — tool inventory

**GitNexus** (stdio):
- `cypher(query)` — raw Cypher query
- `impact(symbol)` — impact analysis from a symbol
- `context(file_or_symbol)` — context retrieval for a file/symbol
- `reindex(scope?)` — manual reindex trigger
- (additional tools per upstream README; check `npx gitnexus@1.6.3 mcp --help`)

**Graphiti** (HTTP):
- `add_episode(name, episode_body, source, source_description, group_id?, reference_time?)`
- `search_facts(query, group_id?, max_facts?, ...)`
- `search_nodes(query, group_id?, max_nodes?, ...)`
- `get_episodes(group_id?, last_n?)`
- `get_entity_edge(uuid)`
- `delete_entity_edge(uuid)`, `delete_episode(uuid)`, `clear_graph()`
- `get_status()`

### 7.2 Claude Code skills

**`wiki-query`** (the only skill in this stack):
- Path: `~/.claude/skills/wiki-query/SKILL.md`
- Triggers: "the wiki", "wiki page on", "tailscale policy", "pve cluster", "runbook for", "what's our convention for X", "what did we decide about X" (when X is not session-specific)
- Allowed tools: `Read`
- Behaviour: read `index.md`, identify slugs, read pages directly. ADR-009.

### 7.3 Hooks — what fires when

| Hook | Trigger | Action | FR |
|---|---|---|---|
| GitNexus PreToolUse | Before any Claude Code tool call | Inject relevant code-graph context | FR-CG-004 |
| GitNexus PostToolUse | After Bash containing `git commit` | Auto-reindex changed paths | FR-CG-005 (default no-filter) |
| (No hooks for Graphiti or Wiki — model-driven via tool/skill calls) | | | ADR-005 |

Hook entries live in `~/.claude/settings.json`; registered by `npx gitnexus setup`.

### 7.4 LiteLLM proxy config (Phase 4)

Captured in ADR-011:
- `OPENAI_BASE_URL=http://hybrid-gemma-litellm.tail-scale.ts.net:4000/v1`
- `MODEL_NAME=gemma-reasoner` (or whatever the gateway exposes)
- `EMBEDDER_MODEL_NAME=text-embedding-3-small` (unchanged; embeddings stay on OpenAI)
- LiteLLM must implement Responses API emulation OR a side-by-side chat-completions-only proxy per ADR-011's fallback path.

## 8. Deployment Architecture

### 8.1 Workstation install (Phase 1, default)

The workstation is the primary surface for Tier 1 (wiki) and Tier 2 (GitNexus). Install commands:

```bash
# Tier 2 — GitNexus
npm install -g gitnexus@1.6.3
npx gitnexus setup    # registers MCP across Claude Code (and Cursor/Codex/etc. if installed)

# Tier 1 — wiki seed (Sprint 3)
mkdir -p ~/workspace/homelab/homelab-playbook/wiki/{architecture,runbooks,decisions,glossary,projects}
cp ~/.claude/skills/wiki-query/SKILL.md ~/.claude/skills/wiki-query/SKILL.md  # placeholder; written in Sprint 3
```

The `wiki-query` skill is committed under `~/.claude/skills/wiki-query/` per Phase 3 deliverable (FR-WIKI-001). The wiki tree itself is committed inside `homelab-playbook/`.

### 8.2 ct-ai-01 container (Phase 2)

Tier 3 (Graphiti + FalkorDB) deploys via Docker Compose on `ct-ai-01`. Full runbook is **`graphiti-claude-code-install-plan-2026-04-25.md` §6 (steps 1-15)** — 488-line shovel-ready procedure; this document does NOT duplicate it. Architecture-level deltas from that runbook:

| Delta | What it changes | Why |
|---|---|---|
| `MODEL_NAME=gpt-4o-mini` (pinned) | Run-book §4 already documents this; ADR-002 elevates to architectural decision | Cost, JSON-quality |
| `image: zepai/graphiti-mcp:v1.0.2` | Run-book §5 says `latest`; we pin per FR-DEP-010 | Reproducibility |
| `image: falkordb/falkordb:<pinned>` | Run-book uses `latest`; pin by SHA or version | Reproducibility |
| Add `cron.d/graphiti-backup` | New file, ADR-007 | Backup cadence |
| Add `scripts/cost-cap.sh` + `*/30 * * * *` cron | New file, ADR-008 | NFR-COST-002 enforcement |
| Add `scripts/cypher-export.sh` | New file, ADR-007 monthly export layer | NFR-PORT-002 |

`ct-dev-homelab` is the test target before any production-class container, per FR-DEP-004 and the operator's standing per-story policy (`feedback_test_container.md`).

### 8.3 Compose / systemd / Ansible role topology

- **Docker Compose** owns the `graphiti-mcp` + `graphiti-falkordb` pair on `ct-ai-01`. Compose unit lives at `/srv/graphiti/docker-compose.yml`.
- **systemd** owns `cron` (already present on the LXC) which runs `cost-cap.sh`, `BGREWRITEAOF`, `BGSAVE`, and `cypher-export.sh`. No new systemd units; cron entries only.
- **Ansible role** `ai-dev-graphiti` (new in Phase 2) idempotently sets up the directory, drops the compose unit, drops the env file from a vaulted source, installs cron entries, and registers MCP with Claude Code. Role lives in `homelab-playbook/roles/ai-dev-graphiti/`. Replaces the deleted `ai-dev-mempalace` and `ai-dev-omega-memory` roles in the playbook structure.
- **Hermes config edits** (Phase 1 decommission): three Jinja templates lose mempalace conditionals; no Graphiti adoption inside Hermes (out of scope per brief NG3).

### 8.4 Graphiti install plan reference

**The 488-line runbook at `homelab-playbook/_bmad-output/planning-artifacts/research/graphiti-claude-code-install-plan-2026-04-25.md` is the operative install procedure.** This architecture document references it; it is not duplicated. Architecture-level deltas captured in §8.2 above.

## 9. ADR Index

| ADR | Title | Status | Closes |
|---|---|---|---|
| [ADR-001](adrs/ADR-001-falkordb-as-graphiti-backend.md) | Use FalkorDB as the Graphiti backend | accepted | — |
| [ADR-002](adrs/ADR-002-gpt-4o-mini-for-graphiti-extraction-phase-1.md) | Use gpt-4o-mini for Graphiti extraction in Phase 1 | accepted | — |
| [ADR-003](adrs/ADR-003-embeddings-stay-on-openai.md) | Keep embeddings on OpenAI text-embedding-3-small in all phases | accepted | — |
| [ADR-004](adrs/ADR-004-gitnexus-over-graphify-and-codegraphcontext.md) | Adopt GitNexus as the code-graph layer | accepted | — |
| [ADR-005](adrs/ADR-005-mcp-first-over-skill-first.md) | MCP-first integration over skill-first | accepted | — |
| [ADR-006](adrs/ADR-006-wiki-as-file-tree.md) | Wiki tier as a file-based markdown tree under homelab-playbook/wiki/ | accepted | Q3 |
| [ADR-007](adrs/ADR-007-graphiti-backup-strategy.md) | Graphiti backup cadence — daily AOF + weekly RDB + monthly export | accepted | Q2 |
| [ADR-008](adrs/ADR-008-daily-1-dollar-cap-implementation.md) | Daily $1 hard-cap via OpenAI Usage API + ct-ai-01 cron throttle | accepted | Q6 |
| [ADR-009](adrs/ADR-009-wiki-query-skill-design.md) | wiki-query skill — read-on-demand with index.md as the entry point | accepted | Q7 |
| [ADR-010](adrs/ADR-010-decommission-as-single-pr.md) | Decommission MemPalace + OMEGA in a single PR with sequenced commits | accepted | — |
| [ADR-011](adrs/ADR-011-litellm-bridge-via-openai-base-url.md) | Phase 4 LiteLLM bridge via OPENAI_BASE_URL (no Graphiti fork) | accepted | Q4 |
| [ADR-012](adrs/ADR-012-gitnexus-graph-export-wrapper.md) | GitNexus graph export via wrapper script | accepted | Q8 |
| [ADR-013](adrs/ADR-013-tier-of-truth-division.md) | Tier-of-truth division — wiki vs Graphiti vs auto-memory | accepted | — |
| [ADR-014](adrs/ADR-014-moscow-recalibration.md) | MoSCoW recalibration — downgrade 16 MUSTs to SHOULD/COULD | accepted | Q1 |

## 10. PRD Calibration (Q1)

Per ADR-014, the PRD's 63/10/0 MoSCoW distribution is recalibrated to **44 MUST / 26 SHOULD / 3 COULD (60% / 36% / 4%)** by downgrading 19 items.

### Summary by category

| Category | Pre | Post | Change |
|---|---|---|---|
| FR-DEC (decommission) | 12 MUST | 12 MUST | unchanged (rock-solid) |
| FR-CG (code-graph) | 11 MUST + 1 SHOULD | 7 MUST + 4 SHOULD + 1 COULD | -3 MUST → SHOULD, -1 MUST → COULD (FR-CG-005) |
| FR-MEM (memory) | 12 MUST + 3 SHOULD | 8 MUST + 7 SHOULD | -4 MUST → SHOULD |
| FR-WIKI (wiki) | 10 MUST | 7 MUST + 3 SHOULD | -3 MUST → SHOULD |
| FR-LLM (LiteLLM) | 6 MUST + 2 SHOULD | 6 MUST + 2 SHOULD | unchanged (Phase 4 hard rules) |
| FR-OBS (observability) | 4 MUST + 2 SHOULD | 1 MUST + 4 SHOULD + 1 COULD | -3 MUST → SHOULD, FR-OBS-002 → COULD |
| FR-DEP (deploy) | 8 MUST + 2 SHOULD | 7 MUST + 3 SHOULD | -1 MUST → SHOULD (FR-DEP-006 wording) |
| **Total** | **63 / 10 / 0** | **44 / 26 / 3** | **60% / 36% / 4%** |

ADR-014 enumerates each downgrade with rationale. The PRD itself is updated via a Sprint-1 PRD-validation-pass addendum referencing ADR-014.

## 11. Open Architectural Risks

| ID | Risk | Validation phase | Mitigation if it bites |
|---|---|---|---|
| AR1 | GitNexus's npm-distribution + Node.js runtime contradicts the brief's implicit Python assumption (< 500 MB daemon footprint). Actual footprint TBD on workstation. | Sprint 2 install | Verify `ps aux | grep gitnexus` RSS at week 1; if > 500 MB, consider browser-side mode or revisit ADR-004 |
| AR2 | LiteLLM Responses API emulation may not work cleanly with all upstream models. Phase 4 validation gate exists for this; if 95% gate is unattainable, fallback to side-by-side LiteLLM proxy (ADR-011 alt) or remain on cloud. | Sprint 4 | Phase 4 is stretch; Phase 1-3 ship without it (FR-LLM-007) |
| AR3 | OpenAI Usage API has eventual consistency (~5-15 min); the $1/day cap can overshoot by a few cents during chatty bursts. | Sprint 2 (post-install) | Tighten cron cadence to 15 min OR accept overshoot; documented in ADR-008 |
| AR4 | GitNexus abandonment (single-maintainer; brief R1). | Continuous | NFR-SUPP-001 (≥ 3 mo upstream activity at adoption); ADR-012 export wrapper; ADR-004 exit ramp to CodeGraphContext |
| AR5 | Graphiti's MCP server v1.0.2 may have undiscovered config bugs around `OpenAIClient` vs `OpenAIGenericClient` selection that defeat ADR-011's no-fork path. | Sprint 4 spike | Validation gate catches it; fallback to side-by-side proxy |
| AR6 | Wiki content drift (last_reviewed > 6 months across multiple pages). | Continuous | `wiki-lint.sh` warn level; quarterly wiki-review story in backlog |
| AR7 | The single-PR decommission (ADR-010) creates a wide-surface review. A missed reference could ship dead code. | Sprint 1 | FR-DEC-009 grep gate is the hard check; FR-DEC-011 Hermes verify run is the secondary gate |
| AR8 | `tom-personal` group_id discipline — if writes occasionally land in the default `main` group (per install-plan §10 verification step #4), recall hit-rate drops silently. | Sprint 2 (post-install) | Verify default-group behaviour during Step 12 of runbook; codify in `CLAUDE.md` |

## 12. References

### 12.1 BMAD planning artifacts (this product)
- `homelab-playbook/_bmad-output/planning-artifacts/products/context-stack/product-brief.md`
- `homelab-playbook/_bmad-output/planning-artifacts/products/context-stack/prd.md`
- `homelab-playbook/_bmad-output/planning-artifacts/products/context-stack/adrs/` — 14 ADRs

### 12.2 Source research artifacts
- `homelab-playbook/_bmad-output/planning-artifacts/research/technical-graphify-evaluation-2026-04-25.md` — graphify and code-graph landscape
- `homelab-playbook/_bmad-output/planning-artifacts/research/technical-memory-systems-evaluation-2026-04-25.md` — agent-memory landscape
- `homelab-playbook/_bmad-output/planning-artifacts/research/graphiti-claude-code-install-plan-2026-04-25.md` — operative install runbook (488 lines, NOT duplicated here)

### 12.3 Project memory
- `project_ai_dev_container.md` — Epic 6 superseded
- `project_hybrid_gemma_serving.md` — Phase 4 LiteLLM target
- `project_phone_notifications_tailscale.md` — network defaults; CT101 ntfy
- `feedback_test_container.md` — `ct-dev-homelab` per-story validation policy

### 12.4 External
- GitNexus: <https://github.com/abhigyanpatwari/GitNexus>, <https://www.npmjs.com/package/gitnexus>
- Graphiti: <https://github.com/getzep/graphiti>, <https://help.getzep.com/graphiti/>
- FalkorDB: <https://docs.falkordb.com/>
- Claude Code MCP: <https://code.claude.com/docs/en/mcp>
- LiteLLM OpenAI-compatible: <https://docs.litellm.ai/docs/providers/openai_compatible>

---

**End of architecture — handoff to Epics phase.**
