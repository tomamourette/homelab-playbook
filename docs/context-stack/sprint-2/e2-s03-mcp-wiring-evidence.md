# E2-S03 MCP Wiring Evidence

**Date:** 2026-04-26
**Story:** E2-S03 Wire GitNexus MCP server into Claude Code
**Predecessors:** E2-S01.5 (Docker pivot, ADR-015), E2-S02-retry (footprint PASS)
**Branch:** feature/context-stack-e2-gitnexus

## Stale stdio entry removal

Pre-state `claude mcp list` showed the orphan stdio entry left over from E2-S01.5
(when the npm-installed `gitnexus` binary was removed in favour of the
Docker-delivered daemon per ADR-015):

```
gitnexus: /home/developer/.npm-global/bin/gitnexus mcp - ✗ Failed to connect
```

Removed via the Claude Code CLI (no manual file edit needed):

```
$ claude mcp remove gitnexus
Removed MCP server "gitnexus" from user config
File modified: /home/developer/.claude.json
```

Post-removal grep confirmed clean state:

```
$ claude mcp list 2>&1 | grep -i gitnexus
(no gitnexus entry — clean)
```

## HTTP MCP entry registration

First attempted with default scope (`local`, project-scoped). Re-added at user
scope to match the original (and to make GitNexus available across every
project Claude Code session, not just under `/home/developer/workspace/homelab`).

- **Command used:** `claude mcp add --transport http --scope user gitnexus http://127.0.0.1:4747/api/mcp`
- **Endpoint:** http://127.0.0.1:4747/api/mcp (loopback only — privacy boundary preserved)
- **Transport:** HTTP (per ADR-015)
- **Scope:** user (`/home/developer/.claude.json`)

Output:

```
Added HTTP MCP server gitnexus with URL: http://127.0.0.1:4747/api/mcp to user config
File modified: /home/developer/.claude.json
```

## Connection verification

```
$ claude mcp list 2>&1 | grep -i gitnexus
gitnexus: http://127.0.0.1:4747/api/mcp (HTTP) - ✓ Connected
```

**Verdict:** Connected. Container also confirmed healthy:

```
$ docker ps --filter name=gitnexus --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
NAMES      STATUS                    PORTS
gitnexus   Up 13 minutes (healthy)   127.0.0.1:4747->4747/tcp
```

## JSON-RPC initialize handshake

Direct curl probe to confirm MCP protocol works end-to-end:

```
$ curl -sS -i -X POST http://127.0.0.1:4747/api/mcp \
    -H 'Content-Type: application/json' \
    -H 'Accept: application/json, text/event-stream' \
    -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"e2-s03-test","version":"1.0"}}}'

HTTP/1.1 200 OK
content-type: text/event-stream
mcp-session-id: 3128cb69-61bf-4070-847d-da5ba17eef91

event: message
data: {"result":{"protocolVersion":"2024-11-05","capabilities":{"tools":{},"resources":{},"prompts":{}},"serverInfo":{"name":"gitnexus","version":"1.6.3"}},"jsonrpc":"2.0","id":1}
```

- Status: HTTP 200
- Server: gitnexus 1.6.3
- Protocol: 2024-11-05
- Capabilities advertised: tools, resources, prompts
- Stateful HTTP transport confirmed via `mcp-session-id` response header.

## Tools discovered

After sending `initialize` + `notifications/initialized`, `tools/list` returned
**13 MCP tools**:

1. `list_repos` — list indexed repositories
2. `query` — query the code knowledge graph for execution flows (BM25 + semantic, RRF-ranked)
3. `cypher` — raw Cypher queries against the knowledge graph
4. `context` — 360-degree view of a single symbol (callers, callees, references, processes)
5. `detect_changes` — analyse uncommitted git diff and find affected execution flows
6. `rename` — multi-file coordinated rename via graph + text search
7. `impact` — blast-radius analysis (LOW/MEDIUM/HIGH/CRITICAL risk)
8. `route_map` — API route → handler/middleware/consumer mapping
9. `tool_map` — MCP/RPC tool → handler mapping
10. `shape_check` — response-shape mismatch detection between routes and consumers
11. `api_impact` — pre-change impact report for API route handlers
12. `group_list` — list cross-repo groups
13. `group_sync` — rebuild the cross-repo Contract Registry

This **exceeds** the architecture §7.1 minimum surface (`cypher`, `impact`,
`context`, `reindex`-equivalent via `detect_changes` / `group_sync`). The
expanded inventory reflects gitnexus@1.6.3 (the version pinned in E2-S01.5).

## Notes

- **Transport:** HTTP per ADR-015 (Docker delivery model). The original stdio
  registration written by `gitnexus setup` in E2-S01.5 is structurally obsolete
  for our deployment topology.
- **Privacy boundary:** endpoint binds to 127.0.0.1 only (verified via
  `docker ps` PORTS column showing `127.0.0.1:4747->4747/tcp`). No 0.0.0.0
  binding.
- **Session restart:** Claude Code's MCP daemon picks up the new entry on next
  invocation; `claude mcp list` already shows ✓ Connected without restarting
  the host process. Existing in-flight Claude Code sessions may need
  reload-MCP-tools or a session restart to expose the GitNexus tools to the
  model — this is already the standard MCP add-server flow.
- **Hooks scope:** PreToolUse and PostToolUse hook wiring (which the legacy
  `gitnexus setup` would have written) is intentionally **out of scope** for
  this story. Hook configuration is E2-S04, and `~/.claude/settings.json`
  remains in its post-Sprint-1 clean state (`hooks: {}`).

## Next action

Proceed to **E2-S04** to wire PreToolUse + PostToolUse hooks against the now
visible MCP tool surface.
