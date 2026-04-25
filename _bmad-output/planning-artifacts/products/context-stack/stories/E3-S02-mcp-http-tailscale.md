---
type: story
epic: E3
id: E3-S02
title: "Configure Graphiti MCP HTTP transport + Tailscale reach + Claude Code registration"
size: 1d
priority: MUST
fr_refs: [FR-MEM-002, FR-MEM-003, FR-MEM-009]
adr_refs: [ADR-001, ADR-005]
status: draft
date: 2026-04-25
---

# E3-S02: Configure Graphiti MCP HTTP transport + Tailscale reach + Claude Code registration

## User Story

As **tomamourette** (homelab operator), I want **the `graphiti-mcp` HTTP endpoint reachable from my workstation over the Tailscale tailnet and registered with Claude Code as the `graphiti` MCP server**, so that **Claude Code's tool surface advertises `add_episode` / `search_facts` / `search_nodes` etc. and I can drive Graphiti from any session (FR-MEM-002, FR-MEM-003 covered)**.

## Background and Context

Per architecture §3 and §8.2, the workstation reaches `ct-ai-01` over Tailscale (matches the `phone-notifications-tailscale` pattern from project memory). Graphiti's MCP server exposes streamable HTTP at `/mcp/`; runbook §3 documents the registration form (`claude mcp add --transport http graphiti http://ct-ai-01.<tailnet>.ts.net:8000/mcp/`). The story flips the compose port bind from `127.0.0.1:8000` to `0.0.0.0:8000` (Tailscale ACLs are the authentication boundary), runs the runbook §6 Steps 8–10 verifications, and lands the `claude mcp add` registration. This closes the runbook open-verification step #3 ("Claude Code's HTTP MCP transport reaches the server through Tailscale without auth").

## Acceptance Criteria

### AC1: Compose port bind flipped to `0.0.0.0:8000` on graphiti-mcp

- **Given** E3-S01 stack is up with `127.0.0.1:8000:8000`
- **When** I edit the rendered `/srv/graphiti/docker-compose.yml` to change `127.0.0.1:8000:8000` → `0.0.0.0:8000:8000` on `graphiti-mcp` and run `docker compose up -d` (runbook §6 Step 9)
- **Then** `docker compose port graphiti-mcp 8000` returns `0.0.0.0:8000` and `ss -tlnp | grep :8000` on `ct-ai-01` shows the port listening on `0.0.0.0`.
- **And** FalkorDB ports stay at `127.0.0.1:6379` and `127.0.0.1:3000` (only the MCP port changes; FalkorDB is loopback-only inside the container network).

### AC2: MCP `/health` returns OK from localhost on ct-ai-01

- **Given** AC1
- **When** I run `curl -s http://127.0.0.1:8000/health` on ct-ai-01 (runbook §6 Step 7)
- **Then** the response is HTTP 200 and the body parses as JSON containing `"status": "ok"` (or equivalent shape per `mcp-v1.0.2`).

### AC3: MCP `tools/list` advertises the standard Graphiti tool surface

- **Given** AC2
- **When** I run on ct-ai-01:
  ```bash
  curl -s -X POST http://127.0.0.1:8000/mcp/ \
    -H 'Content-Type: application/json' \
    -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
  ```
- **Then** the response is HTTP 200 and the JSON `result.tools[].name` list includes **at minimum**: `add_episode`, `search_facts`, `search_nodes`, `get_episodes`, `delete_entity_edge`, `delete_episode`, `clear_graph`, `get_status` (FR-MEM-009).

### AC4: Endpoint reachable from workstation over Tailscale

- **Given** AC3 and Tailscale up on workstation + ct-ai-01
- **When** I run from workstation: `curl -s http://ct-ai-01.<tailnet>.ts.net:8000/health` (substitute the actual Tailscale hostname)
- **Then** the response matches AC2 (HTTP 200, JSON status ok); round-trip latency from `time curl` is < 100 ms (informational; not a gate).

### AC5: Claude Code MCP registration succeeds

- **Given** AC4
- **When** I run on workstation: `claude mcp add --transport http graphiti http://ct-ai-01.<tailnet>.ts.net:8000/mcp/ --scope user`
- **Then** `claude mcp list` shows a row containing `graphiti  http  http://ct-ai-01...:8000/mcp/  ✓ connected` (or equivalent "connected" status indicator).

### AC6: Tool surface visible inside a Claude Code session

- **Given** AC5
- **When** I open a fresh Claude Code session in `~/workspace/homelab/homelab-playbook/` and ask: *"List the tools provided by the graphiti MCP server."*
- **Then** the model lists at least the eight tools enumerated in AC3 (the model may paraphrase names; verify by tool-call logs in the session, not the prose response).

### AC7: No outbound 8000 from non-tailnet hosts

- **Given** AC1 (port now bound to `0.0.0.0`)
- **When** I run from a non-tailnet host (e.g. `curl --connect-timeout 3 http://<ct-ai-01-public-ip-if-any>:8000/health`)
- **Then** the connection fails (timeout or connection refused) — the LXC is **not** publicly reachable; only the tailnet path works. (NFR-PRIV-003 forward-compliance — phone-facing surfaces are out of scope but the same tailnet posture applies to MCP.)

## Implementation Notes

- **Why `0.0.0.0` is safe here:** the LXC has no public IPv4/IPv6 routing; the tailnet ACL is the auth boundary. This matches the operator's existing CT101/ntfy pattern (`project_phone_notifications_tailscale.md`).
- **Tailscale hostname:** use `tailscale status` on the workstation to discover the canonical name (e.g. `ct-ai-01.<tailnet>.ts.net`). Do **not** hardcode an IP — Tailscale magic-DNS handles the rotation.
- **Scope choice for `claude mcp add`:** `--scope user` (per runbook §3) — the operator wants Graphiti available across every Claude Code project, not just one. Re-evaluate if multi-project namespacing becomes desirable (out of scope for this product per brief NG7).
- **HTTP MCP path is `/mcp/` (with trailing slash):** runbook §3. Omitting the slash sometimes 404s depending on the FastAPI router; pass it.
- **No in-protocol auth:** Graphiti MCP does not implement Bearer/API-key auth. Tailscale tailnet membership is the authentication. Document this in the install runbook (security §5.3 of architecture).
- **`get_status()` is a useful smoke probe** — once registered, calling it from Claude Code should return DB connectivity info; saves one round-trip during E3-S05 smoke-tests.

## Test Plan

**Pre-flight:**
```bash
# Workstation
tailscale status | head    # expect ct-ai-01 listed
claude mcp list            # snapshot pre-state (no graphiti yet)

# ct-ai-01
docker compose ps          # both containers running per E3-S01
```

**Steps:**
```bash
# AC1 — flip the bind
ssh ct-ai-01 'cd /srv/graphiti && sed -i "s|127.0.0.1:8000:8000|0.0.0.0:8000:8000|" docker-compose.yml && docker compose --env-file .env up -d'
ssh ct-ai-01 'docker compose port graphiti-mcp 8000'

# AC2 + AC3 (on ct-ai-01)
ssh ct-ai-01 'curl -fsS http://127.0.0.1:8000/health && echo'
ssh ct-ai-01 'curl -fsS -X POST http://127.0.0.1:8000/mcp/ -H "Content-Type: application/json" -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/list\",\"params\":{}}" | jq -r ".result.tools[].name" | sort'

# AC4 (from workstation)
TS_HOST=$(tailscale status --json | jq -r '.Peer[] | select(.HostName=="ct-ai-01") | .DNSName' | sed 's/\.$//')
curl -fsS "http://${TS_HOST}:8000/health"

# AC5
claude mcp add --transport http graphiti "http://${TS_HOST}:8000/mcp/" --scope user
claude mcp list | grep graphiti

# AC6 — interactive; record session transcript
script -q /tmp/e3-s02-mcp-tools-list.log claude
# inside: "list graphiti tools"
grep -E "(add_episode|search_facts|search_nodes)" /tmp/e3-s02-mcp-tools-list.log
```

**Rollback if AC4–AC6 fail:**
```bash
# Workstation
claude mcp remove graphiti

# ct-ai-01: revert bind to 127.0.0.1 if exposing was the problem
ssh ct-ai-01 'cd /srv/graphiti && sed -i "s|0.0.0.0:8000:8000|127.0.0.1:8000:8000|" docker-compose.yml && docker compose up -d'
```

## Dependencies

- **Blocks:** E3-S03 (CLAUDE.md update needs the registered MCP name); E3-S04 (env config edits live in `.env` — independent — but the verification path uses MCP); E3-S05, S06 (smoke tests need the registered MCP); E3-S08 (restore drill verifies via MCP); E3-S09 (decision gate uses tool-hit-rate logged via MCP).
- **Blocked by:** E3-S01 (compose stack up), E1-S02 (settings.json clean of OMEGA before new MCP entries land).

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| `mcp-v1.0.2` HTTP route is not exactly `/mcp/` (regression vs runbook) | AC2 + AC3 are independent probes; if AC3 fails, inspect `docker compose logs graphiti-mcp | tail -50` for the actual route path |
| Tailscale ACL accidentally blocks the workstation→ct-ai-01 path | `tailscale ping ct-ai-01` from workstation; review ACLs in the Tailscale admin console |
| `claude mcp add` registration ID-clash with a stale leftover from a previous experiment | `claude mcp remove graphiti` before AC5; AC5 then becomes idempotent |
| Public exposure of 8000 (operator's ct-ai-01 has unexpected public route) | AC7 is the negative-test gate; if it fails, flip back to `127.0.0.1` and use `tailscale serve` instead of host-bind |
| Bind change requires container recreate, not just `restart` | The runbook uses `docker compose up -d` which recreates only the changed service — verified pattern |

## Definition of Done

- [ ] All ACs (AC1–AC7) pass
- [ ] `claude mcp list` on workstation shows `graphiti` connected
- [ ] Compose template change committed (port `0.0.0.0:8000:8000`) to `homelab-playbook/roles/ai-dev-graphiti/templates/`
- [ ] Tailscale hostname recorded in install runbook (do **not** commit secrets, but the hostname is fine — it's tailnet-internal)
- [ ] Acceptance test stub `AT-FR-MEM-002a` + `AT-FR-MEM-003a` referenced in `tests/acceptance.md`
- [ ] Runbook open-verification step #3 closed — confirmed reachability over tailnet without in-protocol auth
- [ ] No regression in E3-S01 ACs (FalkorDB still PINGs, both containers still healthy)
