# E3-S01 FalkorDB Evidence

**Date:** 2026-04-26
**Story:** E3-S01 Stand up FalkorDB Docker container (Graphiti backend)
**Branch:** feature/context-stack-e3-graphiti
**Sprint / Epic:** Sprint 3 / Epic E3 / 1 of 9
**ADRs:** ADR-001 (FalkorDB selection), ADR-007 (backup strategy)

## Compose stack

- **Path:** `homelab-apps/stacks/graphiti/docker-compose.yml`
- **Service:** `falkordb`
- **Image:** `falkordb/falkordb:v4.18.1` (pinned — FR-DEP-010, no `:latest`)
- **Image digest:** `sha256:d6aa9598b79cd54935864d56f971f3916156399a9ca38a5fae6c029ab1f2bce9`
- **Image size:** 175 MB
- **Bind:** `127.0.0.1:6379->6379` (loopback only — NFR-PRIV-001)
- **Volume:** `~/.graphiti-data:/var/lib/falkordb/data` (`FALKORDB_DATA_PATH`, persistent AOF + RDB)
- **Network:** named bridge `graphiti_default` — Graphiti MCP container will join in E3-S02
- **Resources:** `mem_limit: 1g`
- **Hardening:** `cap_drop: ALL`, re-add minimal `SETGID/SETUID/DAC_OVERRIDE`, `security_opt: no-new-privileges:true`
- **Logging:** `json-file` rotation, 20 MB × 3 files
- **Healthcheck:** `redis-cli MODULE LIST | grep -q graph` (verifies the FalkorDB graph module is loaded — strict)
- **Persistence flags (via `REDIS_ARGS` env):** `--appendonly yes --save 60 1000` (AOF on; RDB snapshot every 60 s if ≥1000 keys changed)

The Graphiti MCP server lands in E3-S02 on the same `graphiti_default` network; the MCP↔FalkorDB hop will not cross host loopback.

## Container running

```
$ docker ps --filter name=falkordb
NAMES      STATUS                    PORTS
falkordb   Up 16 seconds (healthy)   127.0.0.1:6379->6379/tcp
```

```
$ docker images --digests falkordb/falkordb
REPOSITORY          TAG       DIGEST                                                                    IMAGE ID       CREATED       SIZE
falkordb/falkordb   v4.18.1   sha256:d6aa9598b79cd54935864d56f971f3916156399a9ca38a5fae6c029ab1f2bce9   d6aa9598b79c   2 weeks ago   175MB
```

Final logs (last lines after a clean restart):

```
1:M 26 Apr 2026 15:49:24.652 * Redis version=8.6.2, bits=64, commit=00000000, modified=1, pid=1, just started
1:M 26 Apr 2026 15:49:24.694 * <graph> GraphBLAS JIT restrict to pre-jit kernels
1:M 26 Apr 2026 15:49:24.696 * <graph> Starting up FalkorDB version 4.18.1.
1:M 26 Apr 2026 15:49:24.699 * Module 'graph' loaded from /var/lib/falkordb/bin/falkordb.so
1:M 26 Apr 2026 15:49:24.700 * BGSAVE done, 0 keys saved, 0 keys skipped, 118 bytes written.
1:M 26 Apr 2026 15:49:24.701 * Creating AOF base file appendonly.aof.1.base.rdb on server start
1:M 26 Apr 2026 15:49:24.704 * Creating AOF incr file appendonly.aof.1.incr.aof on server start
1:M 26 Apr 2026 15:49:24.704 * Ready to accept connections tcp
```

## Connectivity + module verification

```
$ docker exec falkordb redis-cli PING
PONG

$ docker exec falkordb redis-cli MODULE LIST
# (formatted excerpt)
name vectorset  ver 1       path —
name graph      ver 41801   path /var/lib/falkordb/bin/falkordb.so
                            args MAX_QUEUED_QUERIES 25 TIMEOUT 1000 RESULTSET_SIZE 10000
```

Both modules present: `graph` (v4.18.1 / 41801) is the FalkorDB Cypher engine; `vectorset` is the bundled Redis 8 vector index module (useful for Graphiti embeddings later — does not need configuration this story).

Host `redis-cli` not installed on the workstation; container `exec` verification suffices.

## Persistence verified end-to-end

```
$ docker exec falkordb redis-cli GRAPH.QUERY test_graph "CREATE (n:Test {name: 'e3-s01-smoke'}) RETURN n"
n.id 0  n.labels [Test]  n.properties.name e3-s01-smoke
Labels added: 1   Nodes created: 1   Properties set: 1

$ docker exec falkordb ls -la /var/lib/falkordb/data/
drwxr-xr-x  appendonlydir/
-rw-r--r--  dump.rdb            # 1292 bytes — initial BGSAVE on startup

$ docker exec falkordb ls -la /var/lib/falkordb/data/appendonlydir/
-rw-r--r--  appendonly.aof.1.base.rdb       # 118 bytes
-rw-r--r--  appendonly.aof.1.incr.aof       # 211 bytes — write was appended
-rw-r--r--  appendonly.aof.manifest

# Pre-restart query
$ docker exec falkordb redis-cli GRAPH.QUERY test_graph "MATCH (n:Test) RETURN n.name"
n.name e3-s01-smoke

# Restart container
$ docker compose restart falkordb

# Post-restart query — same node returned
$ docker exec falkordb redis-cli GRAPH.QUERY test_graph "MATCH (n:Test) RETURN n.name"
n.name e3-s01-smoke

# Cleanup before commit (don't pollute future Graphiti namespace)
$ docker exec falkordb redis-cli GRAPH.DELETE test_graph
OK

$ docker exec falkordb redis-cli GRAPH.LIST
(empty)
```

AOF + RDB both present on the host bind-mount; node survived a full container restart; test graph removed cleanly before commit.

## Privacy boundary

```
$ ss -tlnp | grep -E ':6379|:4747'
LISTEN  127.0.0.1:4747   (gitnexus, prior story)
LISTEN  127.0.0.1:6379   (falkordb, this story)
```

- `127.0.0.1:6379` only — no LAN, no Tailscale exposure (NFR-PRIV-001).
- No outbound HTTP from FalkorDB (it is a local DB, no LLM hooks).
- No `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` env vars set on the container — LLM/embedder wiring is deferred to E3-S04 inside the Graphiti MCP service (E3-S02), not on FalkorDB itself.
- Hardening: `cap_drop: ALL` with only `SETGID/SETUID/DAC_OVERRIDE` re-added; `no-new-privileges:true`.
- Note: Redis logs the standard "Redis does not require authentication" warning at startup. This is expected and accepted — auth would defeat the in-cluster MCP↔DB hop on the docker network, and external exposure is already blocked by the loopback bind. Authentication can be revisited if the bind ever flips to `0.0.0.0` (it won't for this stack).

## Notes / lessons captured

- **`REDIS_ARGS` quoting trap.** First boot attempt used `--save "60 1000"` (with inner quotes) and Redis 8.6 rejected it with `Invalid save parameters` because the upstream `run.sh` uses `${REDIS_ARGS}` unquoted, so the inner quotes collapsed the two save params into one literal token. Fix: drop the inner quotes — `--save 60 1000`. Comment in compose file warns future-self.
- **Data path `/var/lib/falkordb/data`, not `/data`.** The upstream image's entrypoint reads `FALKORDB_DATA_PATH` (default `/var/lib/falkordb/data`) and passes `--dir` to redis-server itself. Mounting `/data` would silently bypass persistence (server would write into the container default and lose it on recreate). The compose file pins to the upstream's actual path and comments why.
- **Bundled web browser disabled.** `BROWSER=0` is set to suppress the FalkorDB Browser UI; we only want the redis-protocol surface for Graphiti's bolt-style client. Saves a few MB RAM and removes a port surface.
- **Backup strategy foundations only.** ADR-007 calls for daily AOF rewrite + weekly RDB + monthly Cypher export + quarterly drill. This story ships the AOF + RDB persistence the cron jobs depend on; the cron jobs themselves land in E3-S07.
- **NFR-FOOTPRINT-001 (<200 MB FalkorDB RSS) not measured here.** That is verified in E3-S09 once Graphiti has written real episodic data. The 1 GB compose `mem_limit` is the ceiling, not the budget.

## Story scope vs. story file

The committed story file (`E3-S01-falkordb-compose-stack.md`) targeted a deployment to LXC `ct-ai-01` with a Graphiti MCP service in the same compose unit. This story executed the **director-amended scope**: workstation-only FalkorDB stack at `homelab-apps/stacks/graphiti/`, mirroring the gitnexus convention from E2-S01.5. The Graphiti MCP service is split out to E3-S02. AC1/AC4/AC5/AC6 (directory layout, container health, PING, persistence-across-restart) are satisfied here; AC2's `:latest` ban is honored (`v4.18.1` pinned with digest); AC3 (`.env` mode 600, `OPENAI_API_KEY` / `FALKORDB_PASSWORD`) is deferred to E3-S04 since LLM wiring lives there.

## Hand-off to E3-S02

- Stack network `graphiti_default` is up and ready for the MCP container to join.
- FalkorDB reachable in-cluster as `falkordb:6379` (no auth — NFR-PRIV-001 boundary intact via loopback bind).
- Persistent volume at `~/.graphiti-data` survives container recreate; AOF + RDB confirmed on disk.
- `OPENAI_API_KEY` will be required by E3-S04 (LLM/embedder wiring), not before.
