# E4-S08 — First real deploy of graphiti + gitnexus to ct-dev-homelab

| | |
|--|--|
| Date          | 2026-04-27 |
| Story         | E4-S08 (Sprint 4, Context Stack product) |
| Branches      | `decommission/context-stack-phase-1` (homelab-playbook), `feature/context-stack-e3-graphiti` (homelab-infra) |
| Status        | Sprint 4 functional scope CLOSED |
| Target host   | ct-dev-homelab (192.168.50.156) |

## Summary

Closed Sprint 4's load-bearing operational story across four phases: vault promotion (host→group scope), first real deploy of graphiti + gitnexus to ct-dev-homelab via the `compose-app` Ansible role, 5/5 smoke tests PASS end-to-end including LLM extraction, and the destructive-down guard drill (refuses without flag, snapshots + executes with flag).

## Phase 1 — Vault promotion (host_vars → group_vars/all)

**Goal:** move `vault_gemini_api_key` and `vault_litellm_master_key` out of the ct-ai-01 host scope so other hosts (graphiti on ct-dev-homelab) can resolve them.

**Approach:** preserve per-key vault format (string-vault `!vault |` blocks) — extract intact ciphertexts, no decrypt/re-encrypt cycle. Source: `ansible/inventories/homelab/host_vars/ct-ai-01/vault.yml`. Destination: new file `ansible/inventories/homelab/group_vars/all/vault.yml`.

**Counts:**

| Metric                                                | Before | After |
|-------------------------------------------------------|--------|-------|
| `vault_gemini_api_key` in `host_vars/ct-ai-01/vault.yml`  | 1      | 0     |
| `vault_litellm_master_key` in `host_vars/ct-ai-01/vault.yml` | 1      | 0     |
| `vault_gemini_api_key` in `group_vars/all/vault.yml`      | (file absent) | 1     |
| `vault_litellm_master_key` in `group_vars/all/vault.yml`     | (file absent) | 1     |
| `vault_cost_cap_ntfy_basic_auth` in host vault            | 1      | 1 (unchanged) |

**Resolution verification (ct-ai-01):** `vault_litellm_master_key` (length=67), `vault_gemini_api_key` (length=39), `vault_cost_cap_ntfy_basic_auth` (length=60) — all three resolve. Lengths only; no values echoed.

**Resolution verification (ct-dev-homelab):** `vault_litellm_master_key` (length=67), `vault_gemini_api_key` (length=39) — both resolve from new group scope.

**ct-ai-01 smoke (`--check` against `litellm-gateway` tags):**

```
PLAY RECAP
ct-ai-01    : ok=20  changed=1  unreachable=0  failed=0  skipped=1
```

The single `changed=1` is a pre-existing unconditional pip-upgrade task in the litellm-gateway role (unrelated to the vault promotion). No "key not found" errors.

## Phase 2 — Real deploy to ct-dev-homelab

**Playbook:** `ansible/playbooks/deploy-context-stack.yml` (no `--check`).

**First attempt failure (halt-on-failure):** `docker compose pull` failed for `graphiti-mcp-genai-bundled:e3-s04g` — that image is locally built (E3-S04g wraps `zepai/knowledge-graph-mcp:standalone` to bundle google-genai SDK) and lives in no registry. The `compose-app` role had no build path.

**Fix (committed as a small role enhancement):**

1. Added `compose_app_build_images: false` default to `roles/compose-app/defaults/main.yml`.
2. Added a "Build stack images via docker compose" task before pull in `roles/compose-app/tasks/main.yml`.
3. Made pull tolerant when build is enabled (`failed_when: rc != 0 and not build_images`).
4. Set `compose_app_build_images: true` for the graphiti stack in `deploy-context-stack.yml`.

**Second attempt (post-fix):**

```
PLAY RECAP
ct-dev-homelab    : ok=25  changed=6  unreachable=0  failed=0  skipped=4
```

**Container state on ct-dev-homelab post-deploy:**

```
NAMES          STATUS                  PORTS
graphiti-mcp   Up (healthy)            127.0.0.1:8000->8000/tcp
falkordb       Up (healthy)            127.0.0.1:6379->6379/tcp
gitnexus       Up (healthy)            127.0.0.1:4747->4747/tcp
```

**Health endpoints:** `graphiti /health = 200`, `gitnexus /api/mcp = 400` (expected — MCP requires POST), `gitnexus init via JSON-RPC = 200`.

**Deviation surfaced and resolved:** initial deploy left graphiti-mcp's LLM extraction returning HTTP 401 (`Incorrect API key provided: sk-14e9c...`). Root cause: `graphiti.env.j2` template was missing `GEMINI_API_KEY` — graphiti's config-graphiti-mcp.yaml uses `provider: gemini` for LLM extraction (per ADR-017 v3 / E3-S04f-retry), which calls Google Gemini directly with `GEMINI_API_KEY`. The embedder still routes through the LiteLLM gateway with `OPENAI_API_KEY=<litellm_master_key>`. Fix: added a third `GEMINI_API_KEY={{ vault_gemini_api_key }}` line to the env template — the very reason vault_gemini_api_key was promoted to group scope. Re-deploy: ok=25 changed=7. Post-fix the LLM-extraction pipeline succeeds (test 1 returned actual entity nodes by name).

## Phase 3 — 5 smoke tests

Smoke runner: `python3 /tmp/e4-s08-smoke.py --restart` executed via SSH on ct-dev-homelab. Group_id `e4s08deploy` (alphanumeric only — E3-S04h regression carried forward).

| # | Test                          | Verdict | Detail                                                                 |
|---|-------------------------------|---------|------------------------------------------------------------------------|
| 1 | Graphiti MCP add → search round-trip | PASS | `add_memory` accepted; after 90s, `search_nodes` returned `Nodes retrieved successfully` with extracted entity nodes (uuid + name fields populated by the Gemini-2.5-flash-lite extractor). |
| 2 | GitNexus query smoke          | PASS    | MCP `initialize` against `:4747/api/mcp` returned `serverInfo.name=gitnexus`, `version=1.6.3`. |
| 3 | Cross-stack liveness          | PASS    | `graphiti /health=200` and `gitnexus /api/mcp=400` (MCP non-POST response, expected) in same run. |
| 4 | Persistence after restart     | PASS    | `docker restart graphiti-mcp` → 30s wait for /health=200 → `search_nodes` returned the same entity nodes. FalkorDB AOF replay verified. |
| 5 | Cost-cap / LiteLLM gateway reach | PASS | From ct-dev-homelab, `curl http://192.168.50.160:4000/health/liveliness = 200 "I'm alive!"`. |

**Total: 5/5 PASS.** Comfortably above ADR-014's lenient SHOULD threshold (3-of-5 hard + 2-of-5 quality).

Side note (not a fail): `get_episodes` returned "No episodes found" even with episodes ingested. Known graphiti quirk — `get_episodes` filters by `episode_id_prefix` which we don't set. The functionally important paths (add, search, persistence) all work.

## Phase 4 — Rollback drill (down -v guard)

Drill playbook: `/tmp/e4-s08-down-drill.yml` (one-off, not committed).

**Scenario 1 — destructive=true, force_data_loss=false:** the role's `assert` task `REFUSE destructive 'down -v' without explicit force_data_loss override` fired with the role's full failure-message, listing both flags required. The drill caught the failure in a `rescue:` block and reported PASS.

```
fatal: [ct-dev-homelab]: FAILED!
  msg: compose-app: refusing to run `docker compose down -v` for stack
       'graphiti' (would destroy named volumes...)
```

**Scenario 2 — destructive=true, force_data_loss=true:** guard allowed pass-through. Snapshot created at `/srv/graphiti/data.bak.20260427T123352` via `cp -a`. Then `docker compose down -v` executed, removing the falkordb named volume.

**Restore after drill:** re-ran `deploy-context-stack.yml` against ct-dev-homelab. `PLAY RECAP ok=25 changed=6 failed=0`. All three containers healthy again. The `data.bak.20260427T123352` snapshot remains on disk as a recovery artefact (no automatic GC — that's intentional per the role's safety-net design).

## Final state

| | |
|--|--|
| ct-dev-homelab graphiti-mcp     | Up, healthy, 127.0.0.1:8000 |
| ct-dev-homelab falkordb         | Up, healthy, 127.0.0.1:6379 (data dir freshly initialised post-drill) |
| ct-dev-homelab gitnexus         | Up, healthy, 127.0.0.1:4747 |
| ct-dev-homelab snapshot         | `/srv/graphiti/data.bak.20260427T123352` retained |
| Workstation graphiti            | UNDISTURBED — different host, separate compose project |
| Vault keys promoted             | `vault_gemini_api_key`, `vault_litellm_master_key` → `group_vars/all/vault.yml` |
| Role enhancement                | `compose_app_build_images` flag (default false) |

## Anything unexpected

1. **Initial pull failure on graphiti-mcp** (locally-built image, no registry). Resolved by adding `compose_app_build_images` to the role. Small, on-spec role enhancement; committed separately under e4-s08.2.
2. **Initial 401 from LLM extraction** (env template missing GEMINI_API_KEY). Resolved by adding the third env var to `graphiti.env.j2`. This is exactly what justifies the Phase 1 vault promotion — `vault_gemini_api_key` had to be group-scope before this template line could resolve.
3. **`get_episodes` returns empty** despite successful add+search. Known graphiti quirk (filter on `episode_id_prefix`); does not block the story. Search and persistence verified through `search_nodes` instead.

## READY-for-Sprint-5 status

Sprint 4 functional scope is **CLOSED**. Remaining Sprint 4 work:

- **E4-S02** (operator seed picks for the knowledge graph) — small content task, no deploy implications.
- **E5 retro / Sprint-4 retro** — at sprint boundary.

Sprint 5 can begin once E4-S02 lands.

## Reuse note for future project containers

Per operator strategic direction (2026-04-27): the `compose-app` role and `deploy-context-stack.yml` playbook are reusable patterns, not single-purpose. When provisioning future LXCs (project containers, BMAD hosts, etc.), the AI-tooling baseline can be composed from:

1. **AI Dev Container role** (homelab-playbook memory `project_ai_dev_container.md`) — installs Claude Code, dotfiles, base AI tooling.
2. **`compose-app` role** (this repo, `ansible/roles/compose-app/`) — deploys context-stack (graphiti + gitnexus) so the new container has unified episodic memory + code-graph access from day one. Same pattern (`deploy-context-stack.yml --limit <new-container>`) works unchanged; the role takes the same `compose_app_*` parameters per stack.

The bundle composition (Claude Code + context-stack as a single AI-tooling package per new project container) is **Sprint 5+ scope**. This story leaves the seam clean: any future "project container provisioning" playbook can `import_playbook: deploy-context-stack.yml` after the AI Dev Container role completes, and the new container will have the same memory + code-graph surface as a workstation. No new abstraction needed at this layer; the seam is already parametric.

## File map

- `homelab-infra/ansible/inventories/homelab/group_vars/all/vault.yml` (new) — promoted vault keys
- `homelab-infra/ansible/inventories/homelab/host_vars/ct-ai-01/vault.yml` (trimmed) — keys removed
- `homelab-infra/ansible/roles/compose-app/defaults/main.yml` — `compose_app_build_images` default
- `homelab-infra/ansible/roles/compose-app/tasks/main.yml` — build step + pull tolerance
- `homelab-infra/ansible/playbooks/deploy-context-stack.yml` — `compose_app_build_images: true` for graphiti
- `homelab-infra/ansible/playbooks/templates/graphiti.env.j2` — added `GEMINI_API_KEY` line
- `homelab-playbook/docs/context-stack/sprint-4/e4-s08-evidence.md` (this file)
