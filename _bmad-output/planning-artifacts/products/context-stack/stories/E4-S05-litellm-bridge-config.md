---
type: story
epic: E4
id: E4-S05
title: "Build LiteLLM bridge config (OPENAI_BASE_URL override to hybrid_gemma_serving)"
size: 1d
priority: SHOULD
fr_refs: [FR-LLM-001, FR-LLM-002, FR-LLM-003, FR-LLM-004, FR-LLM-007]
adr_refs: [ADR-011, ADR-003]
status: draft
date: 2026-04-25
---

# E4-S05: Build LiteLLM bridge config (OPENAI_BASE_URL override to hybrid_gemma_serving)

## User Story

As **tomamourette** (homelab operator), I want **Graphiti's LLM extraction call routed through my `hybrid_gemma_serving` LiteLLM gateway by setting `OPENAI_BASE_URL`, `MODEL_NAME`, and a placeholder `OPENAI_API_KEY` in `/srv/graphiti/.env` — without forking Graphiti — while embeddings continue going to OpenAI's `text-embedding-3-small` (FR-LLM-004 / ADR-003)**, so that **the architectural plumbing is in place to be exercised by the FR-LLM-005 95%-well-formed-JSON validation gate in E4-S06; if `hybrid_gemma_serving` is not yet available by Sprint 4 mid-week, this story executes the FR-LLM-007 deferral path cleanly without polluting Phase 1-3 work**.

## Background and Context

ADR-011 (closes Q4) is the architectural blueprint. Source-spike verification confirmed that Graphiti `mcp-v1.0.2` does NOT expose `--llm-provider openai_generic` via env or CLI flag — but the **default `OpenAIClient`** with `OPENAI_BASE_URL` pointing at LiteLLM works because LiteLLM (≥ 1.50) emulates OpenAI's `/v1/responses` endpoint. Ergo, no Graphiti fork required. Embeddings stay on OpenAI per ADR-003 / FR-LLM-004 — the bridge is for the LLM call only (FR-LLM-001 narrows to Graphiti's extraction call; FR-LLM-002 specifies the OpenAIGenericClient-equivalent path, which here is `OpenAIClient` against LiteLLM's chat-completions/responses surface).

Per FR-LLM-007, Phase 4 is **stretch**. If the upstream `hybrid_gemma_serving` LiteLLM gateway is not reachable by Sprint 4 mid-week, this story closes as **deferred** with a backlog ticket; E4-S06 (validation gate) closes likewise; the rest of E4 ships unaffected.

This story sets up the **plumbing**. E4-S06 *exercises* it via the 50-fact validation gate.

## Acceptance Criteria

### AC1: `hybrid_gemma_serving` LiteLLM endpoint is verified reachable from ct-ai-01

- **Given** I am SSH'd to ct-ai-01
- **When** I run `curl -fsS -m 5 http://hybrid-gemma-litellm.tail-scale.ts.net:4000/v1/models` (Tailscale-internal URL — actual hostname is operator-confirmed at story start)
- **Then** HTTP 200 returns; the JSON body lists at least one model name (e.g., `gemma-reasoner`); response time is < 2 s

### AC2: If AC1 fails, the FR-LLM-007 deferral path is executed cleanly

- **Given** AC1 fails (e.g., gateway HTTP error, DNS unreachable, 5 s timeout)
- **When** I record the failure in `/tmp/e4-s05-deferral.log` with timestamp + reason
- **Then** I (a) write a Phase-4-deferred backlog ticket at `homelab-playbook/_bmad-output/planning-artifacts/products/context-stack/backlog/phase-4-deferred.md`; (b) close THIS story as `status: deferred`; (c) close E4-S06 as `status: deferred`; (d) the rest of E4 (S01-04, S07-12) ships unaffected. PR description must explicitly cite the deferral and the rationale; `homelab-playbook/wiki/projects/hybrid-gemma-serving.md` is updated with `last_reviewed` and a "Phase 4 deferred until LiteLLM gateway lands" note. **AC3-AC10 are NOT applicable in deferral path.**

### AC3: A reversible env change is staged in `/srv/graphiti/.env` (NOT yet committed/applied)

- **Given** AC1 holds
- **When** I edit `/srv/graphiti/.env` to add the Phase-4 lines
- **Then** the file mode remains 600; the file contains: `OPENAI_API_KEY=sk-litellm-anything` (placeholder; LiteLLM ignores key validation), `OPENAI_BASE_URL=http://hybrid-gemma-litellm.tail-scale.ts.net:4000/v1`, `MODEL_NAME=<the model name from AC1>`, `SMALL_MODEL_NAME=<same model>`, `EMBEDDER_MODEL_NAME=text-embedding-3-small` (UNCHANGED — FR-LLM-004); a backup of the pre-change `.env` exists at `/srv/graphiti/.env.phase-3-backup` mode 600 for instant revert (FR-LLM-008)

### AC4: The PRE-change OpenAI API key is preserved out-of-band for embeddings passthrough

- **Given** AC3 staged the placeholder OPENAI_API_KEY
- **When** I inspect the `.env` and the LiteLLM gateway config
- **Then** the operator's real OpenAI key (the one that was at `OPENAI_API_KEY=sk-...` pre-change) is documented as still-needed for embeddings; either (a) the LiteLLM gateway is configured with the real OpenAI key in its own config so it transparently passes embedding calls through, OR (b) `.env` keeps `EMBEDDER_OPENAI_API_KEY=sk-real-...` if upstream Graphiti supports the env split — verified by reading `mcp_server/src/graphiti_mcp_server.py` at the pinned `v1.0.2` tag

### AC5: Apply the change and recreate graphiti-mcp container

- **Given** AC3 + AC4 hold
- **When** I run `cd /srv/graphiti && docker compose up -d --no-deps graphiti-mcp`
- **Then** the container restarts within 30 s; `docker compose logs graphiti-mcp --since 1m` shows the MCP server bound to `127.0.0.1:8000` with no `ImportError`, no auth error, no `OpenAI client could not be initialized` line; `claude mcp list` from workstation still shows `graphiti` as healthy

### AC6: Smoke probe — single `add_episode` round-trips through LiteLLM and back

- **Given** AC5 holds
- **When** I run a Claude Code session and issue `mcp__graphiti__add_episode` with a small probe (`name="phase-4-bridge-probe"`, `episode_body="The phase-4 LiteLLM bridge was activated on 2026-04-25T<ts>Z; this is the canary."`, `source="text"`, `source_description="phase-4 spike"`, `group_id="tom-personal"`)
- **Then** the call returns a UUID within 10 s; `docker compose logs graphiti-mcp --since 1m` shows the LLM request was sent to `hybrid-gemma-litellm.tail-scale.ts.net` (NOT `api.openai.com`) — confirmed via outbound HTTP host inspection; no `JSONDecodeError`, no `Cypher error`

### AC7: Embedding calls still target OpenAI (NOT LiteLLM)

- **Given** AC6 succeeded
- **When** I run `tcpdump -nn host api.openai.com or host hybrid-gemma-litellm.tail-scale.ts.net` on ct-ai-01 in a 60 s window during a second `add_episode` probe
- **Then** outbound traffic goes to BOTH endpoints: LLM call to `hybrid-gemma-litellm.tail-scale.ts.net:4000` AND embedding call to `api.openai.com:443` for `text-embedding-3-small` (FR-LLM-004 verified)

### AC8: Single-env-var revert restores Phase 1-3 baseline (FR-LLM-008)

- **Given** AC6 holds (bridge active)
- **When** I run `sudo cp /srv/graphiti/.env.phase-3-backup /srv/graphiti/.env && cd /srv/graphiti && docker compose up -d --no-deps graphiti-mcp`
- **Then** within 30 s: `docker compose logs graphiti-mcp` shows OpenAI client re-init; the same probe `add_episode` succeeds; outbound LLM traffic now goes to `api.openai.com` only (NOT to `hybrid-gemma-litellm.tail-scale.ts.net`); revert wall-time is ≤ 5 minutes operator-action-time

### AC9: Vaulted `.env` Phase-4 variant is committed for E4-S07 Ansible role

- **Given** AC3 staged the env change
- **When** I look at the homelab-playbook repo
- **Then** an ansible-vault-encrypted Phase-4 `.env` template exists at `homelab-playbook/roles/ai-dev-context-stack/templates/graphiti.env.phase-4.j2.vault` (or equivalent) following the existing Sparkle-style vault pattern; `git grep -l 'sk-' homelab-playbook/roles/` returns 0 — only encrypted blobs

### AC10: Bridge state is documented in the wiki for the next operator-self

- **Given** AC5 (or AC2 deferral) holds
- **When** I update `homelab-playbook/wiki/projects/hybrid-gemma-serving.md`
- **Then** the page records: bridge ACTIVE / DEFERRED status, the date, the gateway URL, the chosen `MODEL_NAME`, and a one-line revert recipe (AC8); page passes `wiki-lint.sh`; page is committed alongside the env-change

## Implementation Notes

### Pre-change `/srv/graphiti/.env` (Phase 1-3 state, post E3-S04)

```env
OPENAI_API_KEY=sk-real-openai-key                       # Graphiti's runtime
OPENAI_ADMIN_KEY=sk-admin-...                            # E4-S04
MODEL_NAME=gpt-4o-mini
EMBEDDER_MODEL_NAME=text-embedding-3-small
SEMAPHORE_LIMIT=5
GRAPHITI_TELEMETRY_ENABLED=false
```

### Post-change `/srv/graphiti/.env` (Phase 4 state)

```env
# Phase 4 — point Graphiti's OpenAI SDK at the hybrid_gemma_serving LiteLLM gateway
OPENAI_API_KEY=sk-litellm-anything                       # placeholder; LiteLLM doesn't validate
OPENAI_BASE_URL=http://hybrid-gemma-litellm.tail-scale.ts.net:4000/v1
OPENAI_ADMIN_KEY=sk-admin-...                            # unchanged — used by cost-cap.sh against api.openai.com
MODEL_NAME=gemma-reasoner                                # whatever LiteLLM exposes
SMALL_MODEL_NAME=gemma-reasoner
EMBEDDER_MODEL_NAME=text-embedding-3-small               # unchanged — embeddings still on OpenAI
EMBEDDER_OPENAI_BASE_URL=https://api.openai.com/v1       # only if upstream Graphiti supports it; otherwise rely on LiteLLM passthrough
EMBEDDER_OPENAI_API_KEY=sk-real-openai-key               # only if upstream Graphiti supports the env split; otherwise LiteLLM proxies it through
SEMAPHORE_LIMIT=5
GRAPHITI_TELEMETRY_ENABLED=false
```

**Verify the embedding-side env split** by reading the pinned tag's `mcp_server/src/graphiti_mcp_server.py` and `core/llm_client/embedder.py` — if `EMBEDDER_OPENAI_BASE_URL` / `EMBEDDER_OPENAI_API_KEY` are recognized, use the split (clean isolation). If not, use the LiteLLM-passthrough route per ADR-011 §Decision: LiteLLM gateway must have a passthrough rule for `text-embedding-3-small` → `api.openai.com` (the LiteLLM config in `hybrid_gemma_serving` includes this; verify via that gateway's docs at story start).

### LiteLLM gateway prerequisites (out of scope for this story; verified at AC1)

`hybrid_gemma_serving`'s LiteLLM gateway must:
- Expose `/v1/chat/completions` AND `/v1/responses` (LiteLLM ≥ 1.50 emulates Responses).
- Have a passthrough rule for the `text-embedding-3-small` model name (so embedding calls reach OpenAI directly with the operator's real key — not the LiteLLM placeholder).
- Be reachable from ct-ai-01 over Tailscale (`hybrid-gemma-litellm.tail-scale.ts.net` resolves and replies).

If any of these fail, AC2 deferral fires.

### Reversibility plumbing

The `.env.phase-3-backup` is the single revert pivot. AC8 verifies a one-file copy + one `docker compose up -d` restores Phase 1-3 in ≤ 5 minutes — well within the FR-LLM-008 "≤ 1 day" bound. The backup must be regenerated whenever a NON-Phase-4-bridge edit lands on `.env` (e.g., new `SEMAPHORE_LIMIT` value); E4-S07 Ansible role manages this lifecycle.

### What this story does NOT do

- Does NOT run the 50-fact validation gate (that's E4-S06; FR-LLM-005).
- Does NOT measure cost-neutrality (NFR-COST-003 — measured over Sprint 4 by E4-S09 weekly digest).
- Does NOT change embedding model/key (FR-LLM-004 explicit lock).
- Does NOT touch the workstation (the bridge is on ct-ai-01 only; workstation stays unchanged).
- Does NOT modify Graphiti's compose `image:` tag (still `zepai/graphiti-mcp:v1.0.2`).

## Test Plan

**Pre-flight (parallel; one Bash block):**
```bash
# AC1 reachability check
ssh ct-ai-01.tail-scale.ts.net 'curl -fsS -m 5 http://hybrid-gemma-litellm.tail-scale.ts.net:4000/v1/models'
# Existing Phase 1-3 health
ssh ct-ai-01.tail-scale.ts.net 'docker compose -f /srv/graphiti/docker-compose.yml ps; cat /srv/graphiti/.env | grep -v API_KEY'
# Confirm Graphiti pinned tag for source-spike verification
ssh ct-ai-01.tail-scale.ts.net 'grep image: /srv/graphiti/docker-compose.yml | grep graphiti-mcp'
# Workstation — current MCP wiring
claude mcp list | grep graphiti
```

**If AC1 fails → execute AC2 deferral:**
```bash
# Author backlog entry, close stories as deferred — see AC2 spec
echo "Phase 4 deferred — LiteLLM gateway not reachable at <date>" > homelab-playbook/_bmad-output/planning-artifacts/products/context-stack/backlog/phase-4-deferred.md
# Update status: deferred in this file's frontmatter and E4-S06's
```

**If AC1 holds → continue with AC3-AC10:**

```bash
# AC3 - stage .env change
ssh ct-ai-01.tail-scale.ts.net 'sudo cp /srv/graphiti/.env /srv/graphiti/.env.phase-3-backup && sudo chmod 600 /srv/graphiti/.env.phase-3-backup'
# scp the new .env (or edit in place via Edit tool)
scp .env.phase-4 ct-ai-01.tail-scale.ts.net:/tmp/.env.phase-4
ssh ct-ai-01.tail-scale.ts.net 'sudo install -o root -g root -m 600 /tmp/.env.phase-4 /srv/graphiti/.env && rm /tmp/.env.phase-4'

# AC4 - inspect upstream code for embedding env split
ssh ct-ai-01.tail-scale.ts.net 'docker run --rm zepai/graphiti-mcp:v1.0.2 cat mcp_server/src/graphiti_mcp_server.py | grep -E "EMBEDDER_OPENAI"'

# AC5 - apply
ssh ct-ai-01.tail-scale.ts.net 'cd /srv/graphiti && sudo docker compose up -d --no-deps graphiti-mcp'
sleep 30
ssh ct-ai-01.tail-scale.ts.net 'docker compose -f /srv/graphiti/docker-compose.yml logs graphiti-mcp --since 1m' | grep -iE 'error|fail|importerror' && echo FAIL || echo OK
claude mcp list | grep graphiti

# AC6 - smoke probe via Claude Code (manual; record transcript)
script -q -c "claude -p 'use mcp__graphiti__add_episode to capture: name=phase-4-bridge-probe, episode_body=The phase-4 LiteLLM bridge was activated on 2026-04-25T<ts>Z; this is the canary, source=text, source_description=phase-4 spike, group_id=tom-personal'" /tmp/e4-s05-probe.log

# AC7 - tcpdump from ct-ai-01 during a second probe
ssh ct-ai-01.tail-scale.ts.net 'sudo timeout 60 tcpdump -nn -i any "host api.openai.com or host hybrid-gemma-litellm.tail-scale.ts.net" -c 200' &
# Run another add_episode probe
sleep 5
script -q -c "claude -p 'add_episode: name=phase-4-bridge-probe-2, episode_body=Embedding split verification, source=text, group_id=tom-personal'" /tmp/e4-s05-probe2.log
wait
# Confirm output shows BOTH endpoints

# AC8 - revert
ssh ct-ai-01.tail-scale.ts.net 'sudo cp /srv/graphiti/.env.phase-3-backup /srv/graphiti/.env && cd /srv/graphiti && sudo docker compose up -d --no-deps graphiti-mcp'
sleep 30
# Verify revert: probe again, traffic should target api.openai.com only
ssh ct-ai-01.tail-scale.ts.net 'sudo timeout 30 tcpdump -nn -c 50 "host hybrid-gemma-litellm.tail-scale.ts.net"' &
script -q -c "claude -p 'add_episode: post-revert canary'" /tmp/e4-s05-revert.log
wait

# Re-apply Phase 4 for E4-S06 to consume:
ssh ct-ai-01.tail-scale.ts.net 'sudo install -o root -g root -m 600 /path/to/.env.phase-4 /srv/graphiti/.env && cd /srv/graphiti && sudo docker compose up -d --no-deps graphiti-mcp'

# AC9 - vault check
git grep -l 'sk-' homelab-playbook/roles/ai-dev-context-stack/   # 0 plaintext

# AC10 - wiki update
# Edit homelab-playbook/wiki/projects/hybrid-gemma-serving.md
bash homelab-playbook/scripts/wiki-lint.sh
```

**Rollback (story-level):** AC8 — single env-file copy + container recreate. < 5 minutes wall-clock.

## Dependencies

- **Blocks:** E4-S06 (validation gate runs against the bridged config); E4-S07 (Ansible role templates the Phase-4 `.env` variant)
- **Blocked by:** E3-S01 (Graphiti deployed), E3-S04 (`SEMAPHORE_LIMIT=5` baseline), E4-S04 (`OPENAI_ADMIN_KEY` already in `.env` so backup captures it)
- **External:** `hybrid_gemma_serving` LiteLLM gateway must be reachable (AC1) — if not, AC2 deferral fires; this story closes deferred and so does E4-S06

## Risks and Mitigations

| Risk | Source | Mitigation |
|---|---|---|
| LiteLLM Responses API emulation broken for chosen model (AR2 from arch §11) | ADR-011 | This story's plumbing is fine; E4-S06's 50-fact gate is what catches actual quality regression. ADR-011 §Fallback path = side-by-side LiteLLM proxy with chat-completions-only (30-min config change) |
| `OpenAIGenericClient` not selectable by env (AR5) | ADR-011 source spike | ADR-011 §Decision pivot: use default `OpenAIClient` against LiteLLM, not OpenAIGenericClient. Already factored in; this story doesn't fork |
| `hybrid_gemma_serving` not delivered by Sprint 4 mid-week | External epic timing | AC2 deferral path; FR-LLM-007 explicit non-blocking |
| Embedding traffic accidentally routed through LiteLLM (regression risk) | Env config | AC7 tcpdump verification; the `EMBEDDER_OPENAI_BASE_URL` split (if available) provides defense-in-depth; LiteLLM passthrough is the second line |
| Cost regression instead of cost-neutrality (NFR-COST-003) | Phase 4 surface | Story doesn't measure; E4-S09 weekly digest tracks 7-day pre/post; E4-S11 KPI scorecard catches at week-4 gate |
| Bridge introduces latency that fails NFR-PERF-006 (`add_episode` ≤ 5 s) | Local LLM may be slower | Measured at E4-S06; if local LLM consistently > 5 s, fallback to cloud per FR-LLM-006 |

## Definition of Done

- [ ] Either: AC1 holds AND AC3-AC10 all pass (Phase 4 active path); OR AC1 fails AND AC2 deferral path executed cleanly with backlog ticket
- [ ] `/srv/graphiti/.env.phase-3-backup` exists mode 600 (rollback pivot)
- [ ] Vaulted Phase-4 `.env` template committed (or marked deferred) under `homelab-playbook/roles/ai-dev-context-stack/templates/`
- [ ] `homelab-playbook/wiki/projects/hybrid-gemma-serving.md` reflects current bridge state (active/deferred), passes wiki-lint
- [ ] `homelab-playbook/scripts/cost-cap.sh` (E4-S04) is unchanged and still functional under either path
- [ ] No regression in Graphiti smoke tests from E3-S05 / E3-S06
- [ ] If active path: hand off to E4-S06 with the bridged config running
- [ ] Cross-reference task added: `AT-FR-LLM-001a`, `AT-FR-LLM-003a`, `AT-FR-LLM-004a` (Phase 5a will populate)
