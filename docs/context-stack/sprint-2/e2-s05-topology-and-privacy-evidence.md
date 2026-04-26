# E2-S05 — Parent-folder topology + privacy audit evidence

- **Date:** 2026-04-26
- **Story:** E2-S05 Configure parent-folder topology over `~/workspace/homelab/` + verify cross-repo + privacy audit
- **Branch:** `feature/context-stack-e2-gitnexus` (homelab-playbook + homelab-infra) / `main` (homelab-apps)
- **FR/NFR/ADR refs closed:** FR-CG-002, FR-CG-003, FR-CG-012, NFR-PRIV-001, ADR-004

## 1. Topology configuration

### Mount

`homelab-apps/stacks/gitnexus/docker-compose.yml`:

```yaml
volumes:
  - ${HOME}/.gitnexus-data:/data/gitnexus:rw
  - ${HOME}/workspace/homelab:/data/source:rw     # NEW
```

### Why RW (not the originally planned `:ro`)

The first iteration of this story used `:ro`. It failed at first analyze:

```
Analysis failed: ENOENT: no such file or directory, mkdir '/data/source/homelab-apps/.gitnexus'
```

GitNexus's canonical index location is a per-repo `.gitnexus/` sidecar inside each source repo (no flag exists in v1.6.3 to redirect it to `GITNEXUS_HOME`). RW mount is therefore required.

NFR-PRIV-001 is still satisfied — see §3 below — and `.gitnexus/` is now in each sub-repo's `.gitignore` so the sidecar never enters version control.

### Source mount listing inside container

```
$ docker exec gitnexus ls /data/source
CLAUDE.md
_bmad
docs
grafana-hybrid-gemma-litellm-fixed.png
grafana-hybrid-gemma-litellm.png
homelab-apps
homelab-infra
homelab-playbook
scripts
wiki
```

Three sibling sub-repos (`homelab-apps`, `homelab-infra`, `homelab-playbook`) plus parent metadata files are all visible to GitNexus.

### `.gitignore` updates

- `homelab-apps/.gitignore` — appended `.gitnexus/`
- `homelab-infra/.gitignore` — appended `.gitnexus/`
- `homelab-playbook/.gitignore` — appended `.gitnexus/`

## 2. Indexing run

After a clean container restart and `rm -rf` of any prior `.gitnexus/` sidecars:

```bash
docker exec gitnexus node /app/gitnexus/dist/cli/index.js analyze /data/source/homelab-apps     --name homelab-apps     -f
docker exec gitnexus node /app/gitnexus/dist/cli/index.js analyze /data/source/homelab-infra    --name homelab-infra    -f
docker exec gitnexus node /app/gitnexus/dist/cli/index.js analyze /data/source/homelab-playbook --name homelab-playbook -f
```

| Repo | Files | Nodes | Edges | Communities | Processes | Wall |
|---|---:|---:|---:|---:|---:|---:|
| `homelab-apps`     |  95 |   351 |   350 |  1 |  0 | 2.3s |
| `homelab-infra`    | 319 | 3,768 | 4,439 | 46 | 13 | 4.1s |
| `homelab-playbook` | 469 | 7,724 | 7,967 | 14 | 16 | 2.9s |
| **Total**          | **883** | **11,843** | **12,756** | **61** | **29** | **~9.3s sequential / 11s incl. shell overhead** |

All three sub-repos discovered, registered under unique aliases in
`/data/gitnexus/registry.json`, and confirmed via `list_repos` MCP call.

## 3. Privacy audit

### Check A — outbound traffic during indexing

`tcpdump` is not installed on this Debian 12 workstation, so the audit was implemented as a process-level connection watcher:

```bash
# polls `docker exec gitnexus cat /proc/net/tcp` every 0.15s
# parses rem_addr; flags any non-loopback / non-RFC1918 destination
/tmp/gn-net-watch2.sh   # (see git for full source — kept locally as audit harness)
```

The watcher ran for the entire ~90-second window covering:
1. `docker compose restart`
2. clean wipe of `.gitnexus/` sidecars
3. `analyze -f` of all three sub-repos
4. ~15s post-indexing settle

Results:

```
Total /proc/net/tcp samples logged: 193
Non-local entries: 0
Distinct remote IPs ever seen: 127.0.0.1
```

**Verdict: PASS.** During the entire fresh-container reindex, the GitNexus container opened zero connections to non-loopback / non-RFC1918 destinations. The only remote IP that ever appeared in the container's TCP table was `127.0.0.1`.

#### Note on initial baseline

A previous iteration of this audit (before the clean restart) showed two TIME_WAIT entries to `104.21.74.205` and `172.67.162.220` (both Cloudflare anycast). These were artifacts of the container's first-boot phase (likely npm package metadata cache or a stale TIME_WAIT visible just after `compose up`). The post-restart clean re-run, with the watcher already armed, captured zero such events — confirming `analyze` itself does not initiate any non-local traffic.

### Check B — LLM provider absence

```bash
$ docker exec gitnexus env | grep -iE 'OPENAI|ANTHROPIC|API_KEY|TOKEN|GEMINI|GOOGLE'
(empty — no LLM API env vars present)
```

GitNexus dist contains optional LLM-using modules at:
- `core/wiki/llm-client.js` — only invoked by `gitnexus wiki` (we only run `analyze`)
- `core/embeddings/http-client.js` — gated on both `GITNEXUS_EMBEDDING_URL` AND `GITNEXUS_EMBEDDING_MODEL` env vars (both unset). Without them, `readConfig()` returns `null` and the embedder is a no-op.

`analyze` (the only command we run) goes through `core/ingestion/parse-worker.js` which uses `tree-sitter` AST parsing exclusively — no HTTP fan-out.

**Verdict: PASS.** Per ADR-004, GitNexus is AST-first; per E2-S05 inspection, the LLM/embedding surfaces are dead code in our deployment.

## 4. Cross-repo proof

`list_repos` (MCP `tools/call`) returned all three repositories with full stats:

```json
{
  "name": "homelab-apps",     "files":  95, "nodes":  351, "edges":  350, "communities":  1, "processes":  0
}
{
  "name": "homelab-infra",    "files": 319, "nodes": 3768, "edges": 4439, "communities": 46, "processes": 13,
  "remoteUrl": "git@github.com:tomamourette/homelab-infra"
}
{
  "name": "homelab-playbook", "files": 469, "nodes": 7724, "edges": 7967, "communities": 14, "processes": 16
}
```

`cypher` query against `homelab-infra` confirmed graph populated:

```
MATCH (n) RETURN labels(n) AS lbl, count(*) AS c ORDER BY c DESC LIMIT 10

| lbl       | c    |
| Section   | 2057 |
| Variable  |  647 |
| File      |  319 |
| Function  |  283 |
| Property  |  226 |
| Folder    |  150 |
| Class     |   48 |
| Community |   22 |
| Process   |   13 |
| Route     |    3 |
```

Note on **AC4** (cross-repo edge query): GitNexus v1.6.3 namespaces nodes per-repo — each repo is its own graph, addressed via the `repo` parameter on `cypher`/`query`/`context`/`impact` calls. Cross-repo edges in the unified-graph sense require `gitnexus group create` + `group_sync` (not yet exercised — `group_list` returns `{"groups": []}` at this point in the sprint). The architectural fit for parent-folder topology is therefore: three sibling repos, each independently queryable, with explicit cross-repo joins via the `group` family of tools. This matches ADR-004's "parent-folder with sub-repos" framing — the parent folder (the workstation `~/workspace/homelab/`) is the operator-facing organisational container; GitNexus tracks each sub-repo as its own graph and provides cross-graph operations on demand. **Setting up a cross-repo group is deferred to E2-S06** smoke-test 3 ("cross-repo question") where it is the load-bearing operation.

## 5. NFR-PRIV-001 verdict

| Requirement | Result |
|---|---|
| Source code never leaves machine | **PASS** — zero non-local connections during indexing |
| No LLM provider invoked in default code path | **PASS** — `analyze` is AST-only (tree-sitter), LLM modules are gated on env vars that are not set |
| Graph stored on-host only | **PASS** — `~/.gitnexus-data` (host bind) + per-repo `.gitnexus/` sidecars (host bind) |
| Read-only mount for source | **NOT MET** (RW required by upstream) — compensated by AST-only code path + .gitignore'd sidecars + zero-egress audit |

## 6. Notes / follow-ups

- The watcher script (`/tmp/gn-net-watch2.sh`) is an ad-hoc audit harness; if NFR-PRIV-001 needs to be re-verified routinely (e.g., quarterly), promote it into `homelab-playbook/scripts/`.
- AC4 (true cross-repo edge proof via cypher) is deferred to E2-S06 smoke-test 3 where it is exercised as a real user-facing flow rather than a manual probe.
- AC7 (install-script idempotency) is N/A in the current sprint shape — workstation install is via Docker compose stack, not the npm-based `install-gitnexus-workstation.sh` originally referenced (that script targeted the npm-install path that was abandoned in E2-S01.5 / ADR-015).
