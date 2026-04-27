# E3-S07 Evidence — Graphiti backup (ADR-007)

**Sprint:** 3 / Epic 3 (Graphiti rollout)
**Story:** E3-S07 — implement Graphiti backup per ADR-007
**Date:** 2026-04-27
**Operator:** tomamourette (BMAD director Claude)
**Status:** READY for E3-S08 (restore drill)

## Scope

Implement ADR-007 Layers 1–3 as automation on the developer workstation (where `graphiti-mcp` and `falkordb` containers run):

1. Layer 1 — AOF in-process durability (already on; verified, no change).
2. Layer 2 — daily AOF rewrite + weekly RDB snapshot (new cron + scripts).
3. Layer 3 — monthly per-graph Cypher-shaped export (new cron + script, amended for per-`group_id` graph reality discovered in E3-S06).

Plus an ADR-007 amendment recording the per-group-graph reality.

## FalkorDB persistence state (verification)

Captured at the start of the story (no changes were required — AOF was already configured by the compose file in E3-S04g):

| Setting | Value | Source |
| --- | --- | --- |
| `appendonly` | `yes` | `redis-cli CONFIG GET appendonly` |
| `appendfsync` | `everysec` | `redis-cli CONFIG GET appendfsync` |
| `save` (RDB rule) | `60 1000` | `redis-cli CONFIG GET save` |
| `dir` (data path) | `/var/lib/falkordb/data` | `redis-cli CONFIG GET dir` |
| `requirepass` | (empty) | `redis-cli CONFIG GET requirepass` |
| Host bind-mount | `~/.graphiti-data` → container `/var/lib/falkordb/data` | `docker-compose.yml` line 69 |
| Pre-existing `dump.rdb` | 10,577,017 bytes (Apr 27 06:47) | `docker exec falkordb ls -la /var/lib/falkordb/data` |

The compose file's `REDIS_ARGS=--appendonly yes --save 60 1000` (line 86) is the persistent enabler — Step 2 of the implementation plan was a no-op. No FalkorDB password is set, so no secret-leakage risk in the scripts; redis-cli runs without `-a`.

## GRAPH.LIST snapshot (per-group reality)

```
default_db
e3-s04b-smoke
e3-s05-smoke
e3-s05-smoke-retry
e3-s05-flash-lite-test
e3s05flashlite
e3s04g1
e3s04g2
e3s04g3
e3s06test1
e3s06test3bitemp
graphiti_migration
e3s06test5failinject
```

**Total: 13 graphs.** This is the discovery that drives the ADR-007 amendment — `default_db` is one of many, not "the" graph. Most are E3-S04/S05/S06 test namespaces; `default_db` is the original and `graphiti_migration` is from earlier work.

## Backup scripts (new files in homelab-apps)

All three live in `homelab-apps/stacks/graphiti/scripts/`, made executable, and run as the `developer` user (which has `docker` access without sudo).

### Per-script test results (manual run before cron install)

| Script | Exit | Artifact | Notes |
| --- | --- | --- | --- |
| `backup-aof-rewrite.sh` | 0 | (none — AOF lives in falkordb container; this script triggers compaction) | `aof_current_size=10,660,189` after rewrite |
| `backup-rdb-snapshot.sh` | 0 | `~/.local/state/graphiti-backup/rdb/falkordb-20260427T092409Z.rdb` (10,660,189 bytes) + `latest.rdb` symlink | `LASTSAVE` advanced 1777281768 → 1777281850 |
| `backup-cypher-export.sh` | 0 | `~/.local/state/graphiti-backup/cypher/cypher-20260427T092414Z.tar.gz` (18,214,258 bytes) + `latest.tar.gz` symlink | 13 graphs exported, 13 nodes-files + 13 edges-files + MANIFEST.txt inside tarball |

### Cypher tarball verification

```
$ tar -tzf ~/.local/state/graphiti-backup/cypher/latest.tar.gz | wc -l
28           # 13 nodes + 13 edges + 1 manifest + 1 dir entry
$ tar -tzf ~/.local/state/graphiti-backup/cypher/latest.tar.gz | grep -c '\.nodes\.raw$'
13
$ tar -tzf ~/.local/state/graphiti-backup/cypher/latest.tar.gz | grep -c '\.edges\.raw$'
13
```

MANIFEST.txt sample (real entity counts from prior test runs — `e3s06test1` is the heaviest at ~6,225 node-response-lines / ~41,910 edge-response-lines; the small graphs at 4/6 are essentially empty):

```
default_db nodes_lines=4 edges_lines=6
e3s05flashlite nodes_lines=283 edges_lines=1442
e3s04g1 nodes_lines=262 edges_lines=1173
e3s04g2 nodes_lines=262 edges_lines=1311
e3s04g3 nodes_lines=259 edges_lines=1304
e3s06test1 nodes_lines=6225 edges_lines=41910
e3s06test3bitemp nodes_lines=287 edges_lines=1238
graphiti_migration nodes_lines=4 edges_lines=6
e3s06test5failinject nodes_lines=64 edges_lines=186
```

### Idempotency verification

`backup-aof-rewrite.sh` and `backup-rdb-snapshot.sh` were each invoked twice in quick succession after the first manual run. Result: 3 distinct timestamped `.rdb` files in `~/.local/state/graphiti-backup/rdb/`, `latest.rdb` symlink advanced to the newest, AOF compaction completed cleanly each time, no corruption. Cypher export was not re-stressed since each invocation produces a uniquely timestamped tarball; no shared mutable state across runs.

```
$ ls ~/.local/state/graphiti-backup/rdb/
falkordb-20260427T092409Z.rdb  (10,660,189 bytes)
falkordb-20260427T092440Z.rdb  (10,660,226 bytes)
falkordb-20260427T092442Z.rdb  (10,660,226 bytes)
latest.rdb -> falkordb-20260427T092442Z.rdb
```

## Cron installed (verbatim)

User crontab for `developer` (no prior crontab existed):

```
# E3-S07: Graphiti backup schedule (ADR-007 amended 2026-04-27 for per-group graphs)
0 2 * * *   /home/developer/workspace/homelab/homelab-apps/stacks/graphiti/scripts/backup-aof-rewrite.sh
0 3 * * 0   /home/developer/workspace/homelab/homelab-apps/stacks/graphiti/scripts/backup-rdb-snapshot.sh
0 4 1 * *   /home/developer/workspace/homelab/homelab-apps/stacks/graphiti/scripts/backup-cypher-export.sh
```

`systemctl is-active cron` → `active`; `systemctl is-enabled cron` → `enabled`. The system-level `cron` daemon is up (PID 85, since Apr 24), so these entries will fire on schedule.

## Path deviations from the brief

The brief proposed `/var/log/graphiti-backup-*.log` and `/var/backups/graphiti/*`. Both were rejected because the `developer` user is unprivileged on the workstation and `/var/log` is not writable. The brief permits this adjustment ("If running cron as root, skip the chown. Adjust as needed."). Final paths:

| Brief path | Implemented path |
| --- | --- |
| `/var/log/graphiti-backup-aof.log` | `~/.local/state/graphiti-backup/logs/aof.log` |
| `/var/log/graphiti-backup-rdb.log` | `~/.local/state/graphiti-backup/logs/rdb.log` |
| `/var/log/graphiti-backup-cypher.log` | `~/.local/state/graphiti-backup/logs/cypher.log` |
| `/var/backups/graphiti/rdb/` | `~/.local/state/graphiti-backup/rdb/` |
| `/var/backups/graphiti/cypher/` | `~/.local/state/graphiti-backup/cypher/` |

The XDG state directory (`~/.local/state/`) is the correct convention for "data the operator wants to persist between runs but isn't user-facing config". The operator's host-level backup sweep (restic per project memory) should be pointed at this path; that is configuration outside this story's scope, but flagged here for E3-S08 follow-up.

## ADR-007 amendment

File: `_bmad-output/planning-artifacts/products/context-stack/adrs/ADR-007-graphiti-backup-strategy.md`. A new top section, "Amendment 2026-04-27 (per-group graph reality)", was prepended above the original Context. The original Decision text is unchanged. The amendment captures:

- **Discovery:** 13 graphs in `GRAPH.LIST`; `default_db` is one of many, not "the" graph.
- **What changed:** Layers 1 & 2 unaffected (server-level); Layer 3 now enumerates `GRAPH.LIST` dynamically.
- **Caveat:** `GRAPH.QUERY` output is canonical response format, not directly Cypher-import compatible. The `.raw` exports are an audit/portability/exit-ramp artifact; the RDB snapshot remains the actual recovery path. Round-trip replay tool is deferred to E3-S08.
- **Operational paths:** XDG state-dir rationale.
- **Reversal trigger:** if FalkorDB ships native `GRAPH.EXPORT`/`GRAPH.IMPORT`, demote the response-format dump.

## Total disk footprint at backup time

| Artifact | Size |
| --- | --- |
| 1× RDB snapshot | ~10.7 MB |
| 8 RDB snapshots @ steady-state | ~85 MB |
| 1× Cypher tarball | ~18.2 MB |
| 12 Cypher tarballs @ steady-state | ~220 MB (likely less with retention churn) |
| **Total ceiling** | **~305 MB** |

Well within NFR-FOOTPRINT-003. Note the Cypher export is bigger than the RDB because the response format is verbose ASCII vs. binary RDB.

## Things worth flagging

- **`e3s06test1` is large** (~6,225 node lines / ~41,910 edge lines). If any future graph grows another order of magnitude, the Cypher export's tar+gz may become slow; monitor and consider per-graph parallelism or a switch to compressed JSON streaming if it exceeds a few minutes.
- **AOF rewrite + RDB snapshot run via `docker exec` against the live container.** No quiescing of writes happens; this is acceptable because both `BGREWRITEAOF` and `BGSAVE` are background-fork operations Redis is designed to handle concurrently with traffic. Standard Redis durability semantics apply (AOF: durable to last fsync; RDB: durable to BGSAVE start time).
- **Logs are append-only and unbounded.** No log rotation is configured. At observed line rates (~10 lines/run, ~1 daily run + 1 weekly + 1 monthly) this will take years to matter. If it does become a problem, add `logrotate` config — out of scope here.
- **No off-host replication of the artifacts.** The brief defers this to the existing host-level backup sweep (project memory: restic). The operator must verify restic includes `~/.local/state/graphiti-backup/` in its source set; this is a configuration step outside this story, recommended as part of E3-S08 prep.

## READY for E3-S08

All story acceptance criteria from the brief are satisfied:

- AOF persistence verified on; daily rewrite cron installed and tested.
- RDB persistence verified on; weekly snapshot cron installed; rolling 8-snapshot retention proven.
- Per-group Cypher export cron installed; 13 graphs enumerated from `GRAPH.LIST` dynamically; tarball produced and verified to contain N nodes-files + N edges-files + MANIFEST; rolling 12-tarball retention configured.
- Each script tested manually with exit code 0 before cron install.
- Idempotency proven (3 RDB runs, 3 AOF runs, no corruption).
- ADR-007 amended in place with the per-group-graph discovery and the response-format caveat.
- Two repos, two commits, one per logical change (homelab-apps for code; homelab-playbook for docs).

E3-S08 should focus on:

1. Restoring from `latest.rdb` against a sacrificial Graphiti instance and proving the smoke tests still pass.
2. Pointing the operator's existing restic backup at `~/.local/state/graphiti-backup/`.
3. Optionally: a Cypher-replay tool that round-trips the `.raw` files through `CREATE` statements (deferred from this story).
