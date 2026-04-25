# Graphiti on Claude Code — Install & Integration Plan

**Author:** Research agent (for tomamourette)
**Date:** 2026-04-25
**Scope:** Shovel-ready runbook to install [Graphiti](https://github.com/getzep/graphiti) (Zep's open-source temporal knowledge graph) and wire it into Claude Code as a deliberate replacement for the dormant OMEGA install.
**Companion doc (read first if you haven't):** `technical-memory-systems-evaluation-2026-04-25.md`. This file does **not** repeat that comparison; it assumes Graphiti has been chosen and the question is "how do I install it cleanly?"

---

## 1. Versions & components — April 2026 snapshot

| Component | Latest | Released | Notes |
|---|---|---|---|
| `graphiti-core` (Python lib) | **0.28.2** | 2026-03-11 | Apache-2.0. Hardens Cypher injection in search filters. Min Python 3.10. ([releases](https://github.com/getzep/graphiti/releases), [PyPI](https://pypi.org/project/graphiti-core/)) |
| `graphiti-mcp` server | **mcp-v1.0.2** | 2026-03-11 | Lives in `mcp_server/` of the same repo. Requires `graphiti-core>=0.28.2`. ([README](https://github.com/getzep/graphiti/blob/main/mcp_server/README.md)) |
| Repo | `getzep/graphiti` | — | Apache-2.0, ~823 commits on `main` as of mid-March 2026. |

**Release cadence:** roughly every 2–4 weeks for `graphiti-core` (0.26.3 Jan 22 → 0.27.0 Feb 11 → 0.28.0 Feb 17 → 0.28.2 Mar 11). MCP releases are slower, semver-tagged, and follow security/feature waves in core.

**Confidence: High** — read directly from GitHub releases.

---

## 2. Backend choice: FalkorDB (recommended for this homelab)

### Decision

**Use FalkorDB.** It is the *default* the Graphiti team ships, it's the focus of the FalkorDB-authored MCP integration docs, the docker-compose recipe is the most polished, and resource use on a homelab is trivial (Redis module — typically <200 MB RAM at this data scale). ([FalkorDB Graphiti MCP docs](https://docs.falkordb.com/agentic-memory/graphiti-mcp-server.html))

Performance: in vendor-published OpenCypher benchmarks FalkorDB is materially faster than Neo4j on most queries (sub-140 ms p99 vs Neo4j seconds-tier p99 in their workload), and crucially boots in ~1 ms vs Neo4j's ~90 ms — meaningful for a process you may stop/start during dev. ([FalkorDB benchmark blog](https://www.falkordb.com/blog/graph-database-performance-benchmarks-falkordb-vs-neo4j/)). **Confidence: Medium** — the benchmark is FalkorDB-authored; treat as directional, not gospel.

### When to pick the others

- **Neo4j** — pick if you already have a Neo4j on the homelab, want the Browser UI for visual exploration, or expect to onboard non-technical users. Heavier (JVM, ~1 GB RAM at idle), more ops surface (auth, plugins, APOC), but the most mature tooling. ([Neo4j MCP docs](https://neo4j.com/developer/genai-ecosystem/model-context-protocol-mcp/))
- **Kuzu** — embedded, no daemon, ~zero ops, single directory of files. Pick if you want maximum portability (`tar` the dir, take it anywhere) or are running Graphiti as a library inside another process. Trade-off: only one process can write at a time, no remote access, and as of Graphiti 0.28 the Kuzu driver was added recently (Feb 2026) so call it less battle-tested than Neo4j/FalkorDB. ([Kuzu config](https://help.getzep.com/graphiti/configuration/kuzu-db-configuration), [Kuzu intro](https://thedataquarry.com/blog/embedded-db-2/)). **Confidence: Medium** on maturity claim — based on release-history dates only.
- **Amazon Neptune** — not relevant for a Proxmox homelab.

### FalkorDB deployment recipe (homelab-sized)

`/srv/graphiti/docker-compose.yml`:

```yaml
services:
  falkordb:
    image: falkordb/falkordb:latest
    container_name: graphiti-falkordb
    restart: unless-stopped
    ports:
      - "127.0.0.1:6379:6379"   # bind to localhost only
      - "127.0.0.1:3000:3000"   # FalkorDB Browser UI
    volumes:
      - /srv/graphiti/data:/data
    environment:
      # Optional: set a password by setting REDIS_ARGS
      - REDIS_ARGS=--requirepass ${FALKORDB_PASSWORD}
    mem_limit: 1g
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  graphiti-mcp:
    image: zepai/graphiti-mcp:latest
    container_name: graphiti-mcp
    restart: unless-stopped
    depends_on:
      falkordb:
        condition: service_healthy
    ports:
      - "127.0.0.1:8000:8000"   # MCP HTTP endpoint
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - MODEL_NAME=${MODEL_NAME:-gpt-4o-mini}
      - SMALL_MODEL_NAME=${SMALL_MODEL_NAME:-gpt-4o-mini}
      - EMBEDDER_MODEL_NAME=${EMBEDDER_MODEL_NAME:-text-embedding-3-small}
      - DATABASE_PROVIDER=falkordb
      - FALKORDB_URI=redis://falkordb:6379
      - FALKORDB_PASSWORD=${FALKORDB_PASSWORD}
      - FALKORDB_DATABASE=default_db
      - GRAPHITI_GROUP_ID=tom-personal
      - GRAPHITI_TELEMETRY_ENABLED=false
      - SEMAPHORE_LIMIT=5
    mem_limit: 512m
```

**Resource budget:** 1.5 GB RAM, ~100–200 MB disk in week 1, both containers ride on `ct-ai-01`. Bind to `127.0.0.1` and reach via Tailscale (matches your existing phone-notifications-tailscale pattern — see your MEMORY note `project_phone_notifications_tailscale.md`).

**Confidence: High** for the structure (lifted from official compose); **Medium** for `zepai/graphiti-mcp:latest` image tag — verify in Step 3 of runbook (it may need to be built locally if no public image exists yet).

### Volume layout

```
/srv/graphiti/
├── docker-compose.yml
├── .env                  # OPENAI_API_KEY, FALKORDB_PASSWORD — chmod 600
└── data/                 # FalkorDB AOF/RDB snapshots, owned by container UID 999
```

Add `/srv/graphiti/data` to whatever you back up (your standard zfs send pattern or rsnapshot).

---

## 3. Claude Code MCP integration — concrete config

Claude Code (CLI) **does not** support stdio across a remote container; for an MCP server running as a service on `ct-ai-01`, use **HTTP transport**. (SSE is deprecated as of early 2026 — most Graphiti clients use streamable HTTP on the same URL.) ([Claude Code MCP docs](https://code.claude.com/docs/en/mcp))

### From your laptop / dev workstation (recommended for daily-driver use)

```bash
# Tailscale name of ct-ai-01 — replace with your actual hostname
claude mcp add --transport http graphiti http://ct-ai-01.tail-scale.ts.net:8000/mcp/ --scope user
```

Verify:
```bash
claude mcp list
# Expected: graphiti  http  http://ct-ai-01...:8000/mcp/  ✓ connected
```

### If you want it for one project only

```bash
claude mcp add --transport http graphiti http://ct-ai-01...:8000/mcp/ --scope project
```

### If you want stdio (e.g., running Graphiti directly on the same host as Claude Code)

```bash
claude mcp add graphiti -- uv run --directory /srv/graphiti/src/mcp_server \
  graphiti_mcp_server.py --transport stdio
```

Less recommended — you lose the centralised server, and every Claude Code session boots its own process.

### Required env vars (passed to the **server**, not Claude Code)

| Variable | Required | Default | Notes |
|---|---|---|---|
| `OPENAI_API_KEY` | Yes (or local equivalent) | — | LLM + embeddings |
| `MODEL_NAME` | No | `gpt-4o-mini` | Main LLM for fact extraction |
| `SMALL_MODEL_NAME` | No | `gpt-4o-mini` | Used for cheaper sub-steps |
| `EMBEDDER_MODEL_NAME` | No | `text-embedding-3-small` (1536 dims) | |
| `DATABASE_PROVIDER` | No | `falkordb` | `falkordb`/`neo4j`/`kuzu` |
| `FALKORDB_URI` | If FalkorDB | `redis://falkordb:6379` | |
| `GRAPHITI_GROUP_ID` | No | `main` | **Use this as a namespace** (e.g., `tom-personal`, `tom-work`) |
| `SEMAPHORE_LIMIT` | No | `10` | Throttle for LLM rate limits — drop to 3–5 if using local LLM |
| `GRAPHITI_TELEMETRY_ENABLED` | No | `true` | **Set to `false`** |

([MCP server README](https://github.com/getzep/graphiti/blob/main/mcp_server/README.md))

### Slash commands & skills

Graphiti **does not ship Claude Code slash commands or hooks**. The MCP server simply exposes tools that the model can call:

- `add_episode(name, episode_body, source, source_description, group_id?)`
- `search_facts(query, group_id?, max_facts?, ...)`
- `search_nodes(query, group_id?, max_nodes?, ...)`
- `get_episodes(group_id?, last_n?)`
- `get_entity_edge(uuid)`
- `delete_entity_edge(uuid)`, `delete_episode(uuid)`, `clear_graph()`, `get_status()`

Whether the model *uses* those tools is a function of (a) tool descriptions in the MCP manifest and (b) what's in `CLAUDE.md`. Concretely: you will need to nudge it explicitly. Add to `~/.claude/CLAUDE.md`:

```markdown
## Memory (Graphiti)

You have a Graphiti knowledge graph available via the `graphiti` MCP server.

When to write (use `add_episode`):
- After non-trivial decisions ("we chose X because Y")
- After lessons learned (failed approaches, gotchas)
- When the user says "remember X"

When to read (use `search_facts` and `search_nodes`):
- At session start, before any non-trivial task
- Whenever the user says "do you remember…", "what was that thing about…", or
  refers vaguely to past context
- Before architecture decisions, search for prior facts on the same topic

Always pass `group_id="tom-personal"` so writes/reads stay in one namespace.
```

This mirrors the OMEGA protocol structure but routes through Graphiti's tools.

### Hooks — Graphiti does not install them

Graphiti has **no Pre/PostToolUse hooks**. If you want auto-capture of conversation turns into the graph (the OMEGA-style ambition), the recommended pattern is:

1. A Claude Code **stop hook** in `~/.claude/settings.json` that runs a small script
2. The script `POST`s the just-finished turn's transcript to `http://ct-ai-01:8000/mcp/` invoking `add_episode` with `source="message"`

This is non-trivial wiring and explicitly **out of scope for Day 1** — get the model-driven write path working first, add capture later if it earns its keep.

**Confidence: High** for the negative claim (no hooks shipped); **Medium** that a stop-hook is the right pattern — verify against your existing `update-config` skill conventions.

---

## 4. LLM & embedding choices

### Default (cloud, easiest)

- LLM: `gpt-4o-mini` (Graphiti's documented default)
- Embedder: `text-embedding-3-small` at 1536 dims (Graphiti default, plenty for memory recall)

This is what the docs are written against. **Pick this for Week 1.** ([LLM config](https://help.getzep.com/graphiti/configuration/llm-configuration))

### Pointing Graphiti at your LiteLLM gateway (your `hybrid_gemma_serving` plan)

**Yes, this works** — Graphiti supports OpenAI-compatible endpoints via `OpenAIGenericClient`. Important nuance: the **default `OpenAIClient`** uses `/v1/responses` which Ollama and most OpenAI-compatible proxies do not implement. Graphiti's `OpenAIGenericClient` falls back to `/v1/chat/completions` with `response_format`, which LiteLLM and Ollama both support.

For the MCP server (which currently doesn't expose a CLI flag for `OpenAIGenericClient` directly — verify in runbook), the cleanest path is environment variables that the underlying OpenAI Python SDK respects:

```env
OPENAI_API_KEY=sk-litellm-anything   # LiteLLM doesn't care, but must be set
OPENAI_BASE_URL=http://ct-ai-01.tail-scale.ts.net:4000/v1
MODEL_NAME=gemma-reasoner            # whatever you named it in LiteLLM
EMBEDDER_MODEL_NAME=text-embedding-3-small
```

**Important caveat from the docs:** Graphiti's prompts are demanding — small/local models often produce malformed JSON and the graph fails to ingest. The recommendation is "use larger, more capable models." Your Unsloth UD-Q5_K_M Gemma reasoner is probably borderline-OK for `MODEL_NAME` if it's the 27B+ tier; **it's almost certainly not OK as the embedder.** Consider keeping embeddings on OpenAI (cheap, see §4 cost) and only routing the LLM through LiteLLM.

**Open verification step:** confirm whether `mcp-v1.0.2` exposes `--llm-provider openai_generic` or whether you need to fork the entrypoint. If forking is needed, this hybrid path is a Week-2 task, not Day-1. **Confidence: Medium.**

### Cost order-of-magnitude (cloud path, your usage profile)

Profile: ~50 sessions/month × ~10 stored facts × ~30 queries.

- **Ingest:** each `add_episode` runs entity-extraction + relation-extraction prompts. Conservatively ~2k input tokens + ~500 output tokens at `gpt-4o-mini` ($0.15/$0.60 per 1M) → ~$0.0006/episode → 50 × 10 × $0.0006 = **$0.30/month**
- **Query:** each search is dominated by the embedding call (`text-embedding-3-small` = $0.02/1M tokens). 50 × 30 × ~50 tokens × $0.02/1M = **<$0.01/month**
- **Total: well under $1/month.** A single forgotten Postgres backup test on the cluster will cost more in electricity.

**Confidence: Medium** — depends on episode size; double the estimate if you start dumping full files in.

---

## 5. OMEGA migration — honest take

**Don't migrate. Re-enter by hand.**

You have 9 entries (6 lessons_learned, 3 decisions). At 1–3 minutes each to re-state in your own words to Claude Code (which then calls `add_episode`), you're done in 30 minutes. The benefits of doing so by hand:

- You re-read each entry and decide whether it's *still* true (some of those lessons are 18 days old, but homelab state has moved — pve2 storage redesign, PVE 9 HA migration, etc.)
- Graphiti's entity/relation extraction sees coherent prose, not a SQLite row dump
- No script to write, debug, and throw away

**Search result:** no public OMEGA→Graphiti migration script exists (verified — searches for "omega memory graphiti migrate" and "omega.db graphiti import" return nothing). Writing one for 9 rows is over-engineered.

**Practical method for the 30-minute port:**
```bash
sqlite3 ~/.omega/omega.db "SELECT category, content, created_at FROM memories ORDER BY created_at" \
  > /tmp/omega-export.txt
# then in Claude Code:
# "Read /tmp/omega-export.txt and for each entry, call graphiti add_episode with
#  group_id='tom-personal', name='omega-import-N', source='text', and the content
#  as episode_body. Use the original created_at as reference_time if the tool supports it."
```

**Confidence: High** on the recommendation; this is a values judgment, not a fact.

---

## 6. Day-1 install runbook

**Pre-flight (do once, on your workstation):**
- You have an `OPENAI_API_KEY` available (it's the cheap cloud path; swap later)
- `ct-ai-01` is reachable via Tailscale and has Docker + docker-compose installed
- You know the Tailscale hostname for `ct-ai-01`

```
Step 1. SSH to ct-ai-01.
   $ ssh ct-ai-01
   Expect: shell prompt on the LXC.

Step 2. Create the working directory and grab the official compose file.
   $ sudo mkdir -p /srv/graphiti/data
   $ sudo chown $USER:$USER /srv/graphiti
   $ cd /srv/graphiti
   $ curl -fsSLO https://raw.githubusercontent.com/getzep/graphiti/main/mcp_server/docker/docker-compose.yml
   Expect: docker-compose.yml in the directory.

Step 3. Verify the upstream image actually exists; if not, plan to build locally.
   $ grep -E "^\s+image:" docker-compose.yml
   $ docker pull $(grep -A1 "graphiti" docker-compose.yml | grep image | head -1 | awk '{print $2}')
   Expect: pull succeeds. If "manifest unknown", note this — you'll build locally
   in step 4a instead.

Step 4. Create .env. Use a strong password for FalkorDB even though it's local-only.
   $ cat > .env <<EOF
   OPENAI_API_KEY=sk-...your-real-key...
   FALKORDB_PASSWORD=$(openssl rand -hex 24)
   MODEL_NAME=gpt-4o-mini
   EMBEDDER_MODEL_NAME=text-embedding-3-small
   GRAPHITI_GROUP_ID=tom-personal
   GRAPHITI_TELEMETRY_ENABLED=false
   SEMAPHORE_LIMIT=5
   EOF
   $ chmod 600 .env
   Expect: .env exists, mode 600.

Step 4a (only if Step 3 failed). Build MCP server locally.
   $ git clone --depth=1 https://github.com/getzep/graphiti.git /tmp/graphiti
   $ cd /tmp/graphiti/mcp_server && docker build -t graphiti-mcp:local .
   $ cd /srv/graphiti && sed -i 's|image: zepai/graphiti-mcp:.*|image: graphiti-mcp:local|' docker-compose.yml
   Expect: image graphiti-mcp:local exists.

Step 5. Start the stack.
   $ docker compose --env-file .env up -d
   Expect: Two containers Up, no exit code in `docker compose ps`.

Step 6. Health check FalkorDB.
   $ docker compose exec falkordb redis-cli -a "$FALKORDB_PASSWORD" PING
   Expect: PONG.

Step 7. Health check the MCP server.
   $ curl -s http://127.0.0.1:8000/health
   Expect: {"status": "ok"} or HTTP 200 (response shape may vary by version).

Step 8. Hit the MCP endpoint to confirm tools are advertised.
   $ curl -s -X POST http://127.0.0.1:8000/mcp/ \
       -H 'Content-Type: application/json' \
       -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
   Expect: JSON listing tools including add_episode, search_facts, search_nodes.
   If 4xx, inspect: `docker compose logs graphiti-mcp | tail -50`.

Step 9. Open the MCP port to your tailnet (skip if you're staying local-only on ct-ai-01).
   In docker-compose.yml, change "127.0.0.1:8000:8000" to "0.0.0.0:8000:8000",
   then: `docker compose up -d` to recreate. Tailscale ACLs handle the rest.

Step 10. From your workstation, register the server with Claude Code.
   $ claude mcp add --transport http graphiti \
       http://ct-ai-01.<your-tailnet>.ts.net:8000/mcp/ --scope user
   $ claude mcp list
   Expect: graphiti listed as connected.

Step 11. First write — open Claude Code, ask it to remember something.
   Prompt: "Use the graphiti MCP. Call add_episode with name='install-test',
   episode_body='Graphiti installed on ct-ai-01 on 2026-04-25 using FalkorDB
   backend, group_id=tom-personal.', source='text', group_id='tom-personal'."
   Expect: tool call succeeds, returns an episode UUID.

Step 12. First read — verify the write took.
   Prompt: "Use graphiti search_facts for 'graphiti install', group_id='tom-personal'."
   Expect: at least one fact mentioning the install.

Step 13. Browse the graph visually (sanity).
   Open http://ct-ai-01.<tailnet>.ts.net:3000 in a browser.
   Expect: FalkorDB Browser UI; pick the database, run `MATCH (n) RETURN n LIMIT 25`,
   see entity nodes (e.g., "Graphiti", "ct-ai-01", "FalkorDB").

Step 14. Update CLAUDE.md (see §3 above) so the model uses Graphiti by default.
   $ vim ~/.claude/CLAUDE.md
   Expect: Memory (Graphiti) section added.

Step 15. Disable OMEGA cleanly so the two systems don't fight.
   $ mv ~/.omega ~/.omega.archived-2026-04-25
   $ vim ~/.claude/CLAUDE.md  # remove or comment-out the OMEGA section
   Expect: omega_query / omega_store no longer referenced.
```

**Total wall-clock estimate: 45–75 minutes** (60 if Step 4a is needed; 90 if you fight a 429 from OpenAI on first ingest and have to drop SEMAPHORE_LIMIT).

### Roll-back path

```bash
# On ct-ai-01:
cd /srv/graphiti
docker compose down
docker volume rm graphiti_data 2>/dev/null   # if you used a named volume
sudo rm -rf /srv/graphiti/data               # OR keep this directory for forensics
# On workstation:
claude mcp remove graphiti
mv ~/.omega.archived-2026-04-25 ~/.omega     # un-archive OMEGA
# Restore the OMEGA section in ~/.claude/CLAUDE.md from git history.
```

---

## 7. Smoke-test plan (run all five immediately after Step 13)

| # | What it tests | Action | Pass criterion |
|---|---|---|---|
| 1 | Memory write | Claude Code: *"Remember: pve2 was migrated to ZFS mirror on 2026-04-24, CT151 was returned to it. Store via graphiti."* | Tool returns episode UUID; FalkorDB Browser shows new nodes for `pve2`, `ZFS mirror`, `CT151` and edges connecting them. |
| 2 | Memory read | New session, prompt: *"Use graphiti to recall: when was pve2 migrated to ZFS?"* | Response includes `2026-04-24`. |
| 3 | Temporal validity | Add: *"On 2026-04-25, ct-ai-01 was moved from pve2 to pve3."* Then ask: *"Where is ct-ai-01 hosted as of 2026-04-23?"* and *"…as of today?"* | First answer: `pve2` (or "no info"). Second answer: `pve3`. The earlier fact about pve2 hosting must remain queryable. |
| 4 | Embedding similarity | Add a fact about *"Tailscale ACLs control which devices can reach the homelab tailnet"*. Then query: *"How is access to the homelab restricted from the public internet?"* | Tailscale fact is returned even though no exact phrase overlap. |
| 5 | Auto entity extraction | Add freeform prose: *"During the pve9 HA rules migration on 2026-04-22, I learned `ha-manager set --state stopped` is rejected on error-state resources — you have to disable, diagnose, then start."* No structured hints. | `search_nodes` for `ha-manager` returns the entity. `search_facts` for `error state` returns the lesson. The relation between `pve9` and `ha-manager` is in the graph. |

If any of 1–3 fail, the install is not actually working — go to logs before continuing. 4 and 5 are quality signals, not pass/fail.

---

## 8. Week-1 monitoring & thresholds

| Signal | Healthy | Investigate |
|---|---|---|
| FalkorDB data dir size (`du -sh /srv/graphiti/data`) | <500 MB after week 1 | Growing >100 MB/day with light use |
| Episode count (`get_episodes` count, or count nodes in browser) | 30–80 episodes after a week of normal use | <5 (auto-write isn't firing) or >300 (capture loop is too eager) |
| OpenAI spend (platform.openai.com → usage) | <$2 in week 1 | >$10 — almost always means a runaway ingest of a large file |
| Search latency (eyeball from Claude Code; Graphiti docs target <100 ms) | <500 ms perceived | >2 s — likely hitting OpenAI embedding latency, not Graphiti |
| `docker compose logs graphiti-mcp \| grep -i error` | Zero or rare 429s only | Repeated 5xx, JSONDecodeError on extraction (model too small), or `Cypher` errors |
| MCP tool hit-rate (manual log of how often the model actually calls graphiti) | At least 1 read/session, 1 write every 2–3 sessions | Zero calls all week — CLAUDE.md instructions aren't landing |

Track these in a short journal entry at end of week 1. The hit-rate metric is the most important — that was OMEGA's actual failure mode.

---

## 9. Coexistence with Claude Code's auto-memory (`MEMORY.md`)

Claude Code auto-memory is a **markdown-file index** at `~/.claude/projects/<project>/memory/MEMORY.md`. It's lossless plaintext, hand-readable, version-controllable, and synced across the local file system only. Graphiti is a **structured queryable graph** with temporal validity and entity extraction.

**These are complementary, not competing. Keep both.**

### Clean division of responsibility

| Use auto-memory (`MEMORY.md`) for… | Use Graphiti for… |
|---|---|
| User profile / preferences (one-line each) | Project decisions and lessons learned |
| Active project pointers ("CT151 lives at .151") | Anything dated, anything that supersedes prior state |
| Things you want to be able to `grep` | Anything you want to search semantically ("how did I solve a similar X?") |
| Tiny, stable facts | Larger episodes, prose, conversational context |
| Things you want in the prompt context for free, every session | Things that are too many/too noisy to always include |

### Practical rules

- `MEMORY.md` files stay where they are; Claude Code already loads them. You already use them well.
- Graphiti's `group_id` becomes your namespace separator (`tom-personal`, per-project ids if you want, etc.).
- **Don't double-write.** When you store something in Graphiti, don't also paste it into MEMORY.md. The pointers in MEMORY.md you currently have ("[PVE3 Storage Redesign](project_pve3_storage_redesign.md) — …") stay where they are; new project state goes to Graphiti.

Graphiti does **not** make `MEMORY.md` redundant. The opposite — `MEMORY.md` is your fast, cheap, deterministic context layer; Graphiti is your slower, richer, queryable layer.

---

## 10. Risks and exit ramps

### Week-1 risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| MCP tools not getting invoked (OMEGA's failure mode again) | Medium | Strong wording in CLAUDE.md (§3); week-1 hit-rate monitoring |
| LLM cost surprise from a runaway ingest | Low–Medium | `SEMAPHORE_LIMIT=5`, watch the OpenAI usage page once a day in week 1 |
| FalkorDB data dir corruption on hard reboot | Low | RDB+AOF defaults are durable; back up `/srv/graphiti/data` nightly |
| MCP server image not on Docker Hub | Medium | Step 4a in runbook (build locally) |
| Graphiti's prompts mis-extract (wrong entities, missing relations) | Medium | Default model `gpt-4o-mini` is known-good; if you swap to local LLM expect quality drop |
| `mcp-v1.0.2` regression bug | Low | Pin a specific tag (`zepai/graphiti-mcp:v1.0.2`) rather than `latest` for reproducibility |

### Month-1 risks

- **Drift between graph and reality.** Facts get stale. Graphiti's temporal model handles this if you write *new* facts that supersede old ones; it does *not* magically know when something becomes wrong. Plan a monthly review.
- **Graph bloat.** If hooks-driven auto-capture lands later, episode counts can balloon. Set a soft alarm at 1,000 episodes and audit.
- **Vendor capture.** Graphiti is Apache-2.0 and OSS, but the docs+blog ecosystem is Zep-owned. If Zep pivots commercially, the OSS branch may stagnate. **Confidence: Low** that this happens in the next 6 months.

### Exit ramp (migrating away from Graphiti)

Graphiti has no first-class `export` command, but the data is queryable Cypher. The two viable exit paths:

1. **Cypher dump.** Connect to FalkorDB and run `MATCH (n)-[r]->(m) RETURN n,r,m` to extract the full graph as JSON; rebuild in another graph-backed memory tool (Zep cloud, Neo4j-direct, MemoryGraph) by replaying.
2. **Episode replay.** All `add_episode` calls were durable inputs; if you logged them (recommended — pipe MCP server logs to a file), you can replay against any other agent-memory system that accepts episode-style ingest.

Concretely, set up the MCP server to log requests at INFO level and rotate the log monthly — that file is your insurance policy.

**Confidence: Medium** on the exit story — the Cypher dump path is well-trodden but tool-specific re-import is bespoke.

---

## Open verification steps (things this plan asserts that you should sanity-check during install)

1. The `zepai/graphiti-mcp:latest` image exists on Docker Hub. **(Step 3 of runbook covers this.)**
2. `mcp-v1.0.2` exposes a way to use `OpenAIGenericClient` for the LiteLLM/Ollama path without forking — verify by running `docker compose run graphiti-mcp --help` and looking for an `openai_generic` provider option, or read the `mcp_server/main.py` source.
3. Claude Code's HTTP MCP transport reaches the server through Tailscale without auth — should "just work" since Tailscale is the auth boundary, but confirm Step 10 succeeds.
4. The default group-id behaviour: when the model omits `group_id`, does Graphiti use `GRAPHITI_GROUP_ID` from the env, or the literal string `"main"`? If the latter, your CLAUDE.md instruction to always pass `group_id="tom-personal"` is load-bearing.

---

## Sources

- [getzep/graphiti GitHub](https://github.com/getzep/graphiti)
- [Graphiti releases](https://github.com/getzep/graphiti/releases)
- [graphiti-core on PyPI](https://pypi.org/project/graphiti-core/)
- [MCP server README (canonical install)](https://github.com/getzep/graphiti/blob/main/mcp_server/README.md)
- [Knowledge Graph MCP Server — Zep docs](https://help.getzep.com/graphiti/getting-started/mcp-server)
- [LLM Configuration — Zep docs](https://help.getzep.com/graphiti/configuration/llm-configuration)
- [Kuzu DB Configuration — Zep docs](https://help.getzep.com/graphiti/configuration/kuzu-db-configuration)
- [Graphiti MCP Server with FalkorDB — FalkorDB docs](https://docs.falkordb.com/agentic-memory/graphiti-mcp-server.html)
- [FalkorDB vs Neo4j benchmarks (vendor)](https://www.falkordb.com/blog/graph-database-performance-benchmarks-falkordb-vs-neo4j/)
- [Connect Claude Code to tools via MCP](https://code.claude.com/docs/en/mcp)
- [LiteLLM OpenAI-compatible endpoints](https://docs.litellm.ai/docs/providers/openai_compatible)
- [Kuzu embedded DB intro — Data Quarry](https://thedataquarry.com/blog/embedded-db-2/)
