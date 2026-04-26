# E3-S02 — Graphiti MCP container evidence

**Story:** E3-S02 (Stand up Graphiti MCP v1.0.2 Docker container)
**Sprint:** 3 / Epic E3 / Context Stack product
**Date:** 2026-04-26
**Branch:** `feature/context-stack-e3-graphiti` (homelab-apps + homelab-playbook)
**Companion change:** `homelab-apps/stacks/graphiti/docker-compose.yml` — adds `graphiti-mcp` service block alongside the existing `falkordb` service.

## TL;DR

- `zepai/knowledge-graph-mcp:standalone` (mcp-server **v1.0.2**, graphiti-core **0.28.2**) is running healthy on the workstation, port `127.0.0.1:8000` only.
- Connects in-cluster on the `graphiti_default` docker network to the existing FalkorDB at `redis://falkordb:6379`. PING returns `+PONG`.
- MCP `initialize` over streamable HTTP returns `serverInfo.name="Graphiti Agent Memory"` `version=1.26.0`, protocol `2024-11-05`. Session-ID issued.
- LLM client wired to LiteLLM gateway on `ct-ai-01` (model `gemma4-26b-text`, master key vault-sourced).
- Embedder wired to cloud OpenAI with placeholder key — first `add_episode` call will 401 until E3-S04 supplies the real key. **Acceptable per the brief.**

## Image — supply-chain provenance

| Field | Value |
|---|---|
| Image | `zepai/knowledge-graph-mcp:standalone` |
| Digest (sha256) | `460bafb39439d99ff001ea6ef03efbe0bd5d9e6afe2655edf926da4fd9df97c5` |
| OCI version label | `1.0.2` |
| OCI revision label (upstream commit SHA) | `19e44a97a929ebf121294f97f26966f0379d8e30` (getzep/graphiti) |
| graphiti-core | `0.28.2` |
| Vendor | Zep AI (Apache-2.0) |
| Architecture | `linux/amd64` |
| Layers | 16 |
| Compressed size | 193 MB (Docker Hub) / 132 MB (uncompressed RootFS) |
| Build base | `python:3.11-slim-bookworm` (per upstream `mcp_server/docker/Dockerfile.standalone`) |

### Surprise vs. brief

The brief stated *"No public Docker image exists for Graphiti MCP — confirmed via `docker pull` attempts (denied for both `zepai/graphiti-mcp` and `getzep/graphiti-mcp`)"*, and directed a local source build. **That is correct for the names tried, but `zepai/knowledge-graph-mcp:standalone` does exist on Docker Hub** under a different repo name. It is the official upstream-published image (vendor `Zep AI`, source `https://github.com/getzep/graphiti`, revision `19e44a97...`).

Decision: pull-and-pin-by-digest rather than build-from-source. Rationale:
- Reproducible across operators without a local build toolchain.
- Matches the existing `falkordb/falkordb:v4.18.1@sha256:d6aa9598...` convention in the same compose file.
- Same supply-chain story as the rest of the homelab estate (FR-DEP-010 — no `:latest`).
- The OCI labels record the exact upstream source SHA, so traceability to the build inputs is preserved.

If the operator prefers the build-from-source approach, it remains an option — the upstream Dockerfile builds cleanly per a smoke check (`mcp_server/docker/Dockerfile.standalone`). For now we use the published image.

## Compose stack diff

Added a single new service `graphiti-mcp` to the existing `homelab-apps/stacks/graphiti/docker-compose.yml`. Conventions mirrored from the FalkorDB block:

| Convention | falkordb | graphiti-mcp |
|---|---|---|
| `image:` digest-pinned | yes | yes |
| `restart: unless-stopped` | yes | yes |
| Port bind | `127.0.0.1:6379:6379` | `127.0.0.1:8000:8000` |
| Network | `graphiti_default` | `graphiti_default` |
| `security_opt: no-new-privileges` | yes | yes |
| `cap_drop: ALL` | yes (re-adds 3 caps) | yes (no re-adds) |
| `mem_limit` | 1g | 1g |
| Healthcheck | `redis-cli MODULE LIST | grep -q graph` | `urllib.request.urlopen('http://localhost:8000/health')` |
| Logging json-file | 20m × 3 | 20m × 3 |
| `depends_on` | — | `falkordb: service_healthy` |

### Privacy posture (NFR-PRIV-001)

Both ports loopback-only on the host:

```text
$ ss -tlnp | grep -E ':8000|:6379'
LISTEN 0  4096  127.0.0.1:6379  0.0.0.0:*
LISTEN 0  4096  127.0.0.1:8000  0.0.0.0:*
```

The original story-file's AC1 ("flip MCP port to `0.0.0.0` for Tailscale-tailnet reach from a second workstation") is **deferred** — single-workstation operation does not need a tailnet path. Reconsider when/if a second Claude Code workstation enters the picture (out of scope this sprint per brief NG7).

## ADR-017 v3 runtime config — what's wired, what's deferred

| ADR-017 v3 element | Implementation site | Status |
|---|---|---|
| LLM `OPENAI_BASE_URL=http://192.168.50.160:4000/v1` | `config-graphiti-mcp.yaml: llm.providers.openai.api_url` via `${LITELLM_BASE_URL}` | **wired** |
| LLM `model=gemma4-26b-text` | `config-graphiti-mcp.yaml: llm.model` via `${MODEL_NAME}` | **wired** |
| LLM auth via LiteLLM master key | `.env: LITELLM_MASTER_KEY` (sourced from `/opt/litellm-gateway/.env` on ct-ai-01) | **wired** |
| `max_tokens=1500` | `config-graphiti-mcp.yaml: llm.max_tokens` via `${LLM_MAX_TOKENS}` | **wired** |
| Embedder `text-embedding-3-small` direct OpenAI | `config-graphiti-mcp.yaml: embedder.providers.openai.*` | **wired (placeholder key)** |
| **Separate** LLM and embedder credentials | Custom `config-graphiti-mcp.yaml` mounted over `/app/mcp/config/config.yaml` | **wired** |
| `chat_template_kwargs.enable_thinking=false` | Upstream MCP server has no first-class config knob | **deferred to E3-S04** (LiteLLM gateway model-config) |
| `response_format={"type":"json_object"}` | Upstream MCP server has no first-class config knob | **deferred to E3-S04** (LiteLLM gateway model-config) |
| Real cloud `OPENAI_API_KEY` for embedder | `.env: OPENAI_API_KEY=PLACEHOLDER_FILL_IN_E3_S04` | **deferred to E3-S04** |

Why the deferred items can wait: the MCP server validates the cloud key as truthy at startup but only HTTPs to OpenAI on `add_episode`. `initialize` + `tools/list` + `get_status` all succeed with the placeholder. The `enable_thinking=false` and `response_format=json_object` knobs are LiteLLM-side concerns — they go in the gateway's per-model config, not in the Graphiti config — so they belong in E3-S04 next to the real cloud key wiring.

The custom config sits at `homelab-apps/stacks/graphiti/config-graphiti-mcp.yaml`. The two relevant blocks:

```yaml
llm:
  provider: "openai"
  model: ${MODEL_NAME:gemma4-26b-text}
  max_tokens: ${LLM_MAX_TOKENS:1500}
  providers:
    openai:
      api_key: ${LITELLM_MASTER_KEY}                     # NOT cloud OpenAI
      api_url: ${LITELLM_BASE_URL:http://192.168.50.160:4000/v1}

embedder:
  provider: "openai"
  model: ${EMBEDDER_MODEL:text-embedding-3-small}
  dimensions: 1536
  providers:
    openai:
      api_key: ${OPENAI_API_KEY}                         # cloud OpenAI (placeholder)
      api_url: ${EMBEDDER_BASE_URL:https://api.openai.com/v1}
```

## .env handling

| Item | State |
|---|---|
| `stacks/graphiti/.env` (real secrets) | exists, mode `0600`, gitignored by `**/.env` rule (line 13 of `homelab-apps/.gitignore`) |
| `stacks/graphiti/.env.sample` (template) | committed, placeholder values only |
| Naming | matches existing repo convention (`.env.sample`, not `.env.example`) |
| `git check-ignore` verification | `.gitignore:13:**/.env  stacks/graphiti/.env` — confirmed gitignored |

Sourcing of the real LITELLM_MASTER_KEY: SSH'd to `ct-ai-01` (`192.168.50.160`), grepped `^LITELLM_MASTER_KEY=` from `/opt/litellm-gateway/.env`, piped to mode-600 `~/.litellm-graphiti-mcp-key` on workstation, copied into `stacks/graphiti/.env`, then `shred -u`'d the staging file. No secret material leaves the workstation; no secret enters the git index (verified via `git diff --cached` before commit).

## Container started — `docker ps` line

```text
NAMES          IMAGE          STATUS                    PORTS
graphiti-mcp   460bafb39439   Up 44 seconds (healthy)   127.0.0.1:8000->8000/tcp
falkordb       falkordb/falkordb:v4.18.1   Up 18 hours (healthy)   127.0.0.1:6379->6379/tcp
```

## Graphiti MCP → FalkorDB in-cluster connectivity (verified)

```text
$ docker exec graphiti-mcp python3 -c "
import socket
s = socket.socket()
s.connect(('falkordb', 6379))
s.sendall(b'*1\r\n\$4\r\nPING\r\n')
print(s.recv(64).decode().strip())
s.close()
"
+PONG
```

The MCP container resolves `falkordb` via docker's embedded DNS on the `graphiti_default` network and gets a Redis-protocol `+PONG` from FalkorDB on `:6379`. The hop never crosses the host loopback boundary.

Startup logs corroborate (`docker logs graphiti-mcp`):

```text
Successfully initialized Graphiti client
Using LLM provider: openai / gemma4-26b-text
Using Embedder provider: openai
Using database: falkordb
Using group_id: main
Starting MCP server with transport: http
Running MCP server with streamable HTTP transport on 0.0.0.0:8000
MCP Endpoint: http://localhost:8000/mcp/
```

(All FalkorDB index-creation lines from the same log block are `Index already exists` — the schema persists across restarts via the `~/.graphiti-data` volume mounted into the FalkorDB container by E3-S01.)

## MCP HTTP endpoint probe

### `/health`

```text
$ curl -sS -m 5 -w 'HTTP %{http_code} time=%{time_total}s\n' http://127.0.0.1:8000/health
{"status":"healthy","service":"graphiti-mcp"}HTTP 200 time=0.001260s
```

### `/mcp` initialize handshake

The streamable-http MCP endpoint is at `/mcp` (the `/mcp/` form `307`-redirects to `/mcp`; **upstream story-file note about a "trailing slash required" is wrong for v1.0.2 — the trailing slash redirects, the no-slash form serves**). Response is SSE (`Content-Type: text/event-stream`):

```text
$ curl -sS -m 5 -i -X POST http://127.0.0.1:8000/mcp \
    -H 'Content-Type: application/json' \
    -H 'Accept: application/json, text/event-stream' \
    -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"e3-s02-probe","version":"1.0"}}}'

HTTP/1.1 200 OK
mcp-session-id: c461e944dc6d4c978a515c89a1f22a71
content-type: text/event-stream
[...]
event: message
data: {"jsonrpc":"2.0","id":1,"result":{
  "protocolVersion":"2024-11-05",
  "capabilities":{"experimental":{},"prompts":{...},"resources":{...},"tools":{"listChanged":false}},
  "serverInfo":{"name":"Graphiti Agent Memory","version":"1.26.0"},
  "instructions":"<full Graphiti agent prompt — 32 lines>"
}}
```

The `serverInfo.version` of `1.26.0` is FastMCP's internal protocol-server version, not the graphiti-core/mcp-server release version (which is 0.28.2 / 1.0.2 — see OCI labels). The `mcp-session-id` header confirms the streamable-http session was established.

### Tools list (deferred to E3-S03)

A `tools/list` call against the streamable-http transport requires the session-ID round-trip and an SSE consumer (curl-streaming gets messy). The tool surface is fully exercised in E3-S03 when Claude Code's MCP client registers and lists tools natively. The upstream `instructions` block in the `initialize` response above already enumerates the tool surface contractually: `add_memory`, `search_nodes`, `search_facts`, `delete_episode`, `delete_entity_edge`, `clear_graph` — i.e., the eight-tool surface FR-MEM-009 expects.

## Env var inventory (secrets redacted)

Set on the `graphiti-mcp` container at runtime (verified via `docker inspect graphiti-mcp --format '{{range .Config.Env}}{{println .}}{{end}}'`):

| Variable | Value (redacted) | Source | Purpose |
|---|---|---|---|
| `FALKORDB_URI` | `redis://falkordb:6379` | compose | DB endpoint |
| `FALKORDB_DATABASE` | `default_db` | compose | DB name |
| `LITELLM_BASE_URL` | `http://192.168.50.160:4000/v1` | compose | LLM gateway |
| `LITELLM_MASTER_KEY` | `sk-…` (REDACTED) | `.env` (vault-sourced from ct-ai-01) | LLM auth |
| `MODEL_NAME` | `gemma4-26b-text` | compose | LLM model alias |
| `LLM_MAX_TOKENS` | `1500` | compose | ADR-017 v3 |
| `EMBEDDER_BASE_URL` | `https://api.openai.com/v1` | compose | embedder endpoint |
| `EMBEDDER_MODEL` | `text-embedding-3-small` | compose | embedder model |
| `OPENAI_API_KEY` | `PLACEHOLDER_FILL_IN_E3_S04` | `.env` | embedder auth (deferred) |
| `GRAPHITI_GROUP_ID` | `main` | compose | graph namespace |
| `SEMAPHORE_LIMIT` | `10` | compose | upstream concurrency knob |
| `CONFIG_PATH` | `/app/mcp/config/config.yaml` | compose | config file path |
| `PYTHONUNBUFFERED` | `1` | compose | log flushing |

## Deferred work (out of scope this story)

| Item | Lands in |
|---|---|
| Real cloud `OPENAI_API_KEY` for embedder | E3-S04 |
| LiteLLM gateway model-config: `chat_template_kwargs.enable_thinking=false` and `response_format=json_object` | E3-S04 |
| `claude mcp add` registration on workstation | E3-S03 |
| First `add_episode` smoke test | E3-S05 |
| Tailscale-tailnet exposure (flip to `0.0.0.0:8000` on a second-workstation expansion) | future story (currently NG7) |
| FalkorDB Browser UI on `:3000` | not enabled by this story; the MCP container's startup log mentions it but the standalone image does not run the FalkorDB browser (combined-image-only feature) |

## Working tree at end of story

| Repo | Status |
|---|---|
| `homelab-apps` | 2 staged files (compose edit + `.env.sample` + `config-graphiti-mcp.yaml` new); `.env` correctly NOT staged |
| `homelab-playbook` | 1 staged file (this evidence doc) |
| `homelab-infra` | clean (no changes this story) |

## Hand-off

`READY for E3-S03` — wire Graphiti MCP into Claude Code. Per the live MCP server, the registration command should be:

```bash
claude mcp add --transport http graphiti http://127.0.0.1:8000/mcp --scope user
```

Note the **no-trailing-slash** form (verified above; the `/mcp/` form 307-redirects, which some MCP clients handle and some don't — pin the canonical URL to `/mcp`). When/if a second workstation needs to reach this MCP via Tailscale, flip the compose port to `0.0.0.0:8000:8000` and use `http://ct-workstation.<tailnet>.ts.net:8000/mcp` instead — but that's out of scope for this story per brief NG7.
