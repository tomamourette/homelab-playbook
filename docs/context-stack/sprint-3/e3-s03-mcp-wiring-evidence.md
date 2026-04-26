# E3-S03 — Wire Graphiti MCP into Claude Code (HTTP transport)

**Date:** 2026-04-26
**Story:** E3-S03 — Wire Graphiti MCP server into Claude Code config
**Branch:** `feature/context-stack-e3-graphiti`

## Wiring command

```bash
claude mcp add --transport http --scope user graphiti http://127.0.0.1:8000/mcp
```

Result: `Added HTTP MCP server graphiti with URL: http://127.0.0.1:8000/mcp to user config / File modified: /home/developer/.claude.json`

Path note: `/mcp` (no trailing slash). Per E3-S02 evidence §11, v1.0.2 of the Graphiti MCP server treats `/mcp/` as a 307 redirect to `/mcp`. The original story-file's hint of trailing-slash was wrong for this version.

## Connection verified

```
$ claude mcp list | grep graphiti
graphiti: http://127.0.0.1:8000/mcp (HTTP) - ✓ Connected
```

Both Sprint-2 and Sprint-3 MCP servers now coexist:
```
gitnexus: http://127.0.0.1:4747/api/mcp (HTTP) - ✓ Connected
graphiti: http://127.0.0.1:8000/mcp  (HTTP) - ✓ Connected
```

## JSON-RPC handshake

Initialize:
- HTTP 200 SSE stream
- `mcp-session-id: 7a7d34b733fc4090a85c73ed8ade3eff`
- `serverInfo: {name: "Graphiti Agent Memory", version: "1.26.0"}`
- Protocol: `2024-11-05`
- Capabilities: prompts (listChanged: false), resources (subscribe: false, listChanged: false), tools (listChanged: false)
- Server instructions sent verbatim — Graphiti documents its own usage in the handshake response (group_id namespacing, descriptive episode names, search-by-group_id guidance)

`notifications/initialized` accepted with HTTP 202.

## Tool surface (9 tools)

| Tool | Purpose |
|---|---|
| `add_memory` | Primary write — add episode (text/messages/JSON) |
| `search_nodes` | Natural-language entity search |
| `search_memory_facts` | Search relationships (edges) by query |
| `get_entity_edge` | Fetch specific edge by UUID |
| `get_episodes` | Retrieve episodes (group_id filter supported) |
| `delete_entity_edge` | Delete edge |
| `delete_episode` | Delete episode |
| (2 more truncated in initial probe) | likely `clear_graph`, `get_status` per upstream README |

This is the canonical Graphiti MCP tool surface per the install plan research. No surprises.

## Operator action items deferred to later stories

- **E3-S04**: real `OPENAI_API_KEY` for the embedder client (currently `PLACEHOLDER_FILL_IN_E3_S04` — `add_memory` will fail at first call until this is provided); LiteLLM gateway model-config update to inject `chat_template_kwargs.enable_thinking=false` + `response_format=json_object` per ADR-017 v3 (E3-S02 §11 finding: not first-class config knobs in the upstream Graphiti MCP server, must live at the gateway layer).
- **E3-S05**: smoke-test `add_memory` + `search_nodes` after the embedder key is in place.

## Files

- This evidence file (homelab-playbook)
- `/home/developer/.claude.json` (workstation-only, not in any repo) — modified to add the MCP server entry. Backup not made; reversal is `claude mcp remove graphiti --scope user`.
