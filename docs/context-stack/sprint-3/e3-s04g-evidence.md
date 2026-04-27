# E3-S04g — Cleanup evidence

**Date:** 2026-04-27
**Story:** E3-S04g (post-pivot cleanup, ADR amendments)
**Branch:** `feature/context-stack-e3-graphiti`
**Repos touched:** homelab-apps (Steps 1-3), homelab-playbook (Steps 4-5, this doc)

## Goal recap

After E3-S04f-retry's pivot from local Gemma to cloud `gemini-2.5-flash-lite`
(commit `d77c64f`), four workarounds in the Graphiti stack became dead weight:

1. `factories.py.patched` bind-mount (E3-S04d) — gemini provider doesn't use the openai factory arm
2. `OPENAI_BASE_URL` env (E3-S04b) — same reason; openai SDK env fallback is off the hot path
3. Transient `pip install google-genai` — survives only the current container; lost on `--force-recreate`
4. (informational) `gemma4-26b-json` LiteLLM alias and `gemma-hybrid-proxy` — kept for non-Graphiti consumers

E3-S04g cleans up #1, #2, and #3, with smoke verification between each step,
and amends ADR-002 + ADR-017 to reflect the new architecture.

## Step results

| Step | Action | Smoke result | Status |
|---|---|---|---|
| 1 | Persistent google-genai SDK via custom Dockerfile | 10 nodes / ~10s / `e3s04g1` | PASS |
| 2 | Drop `factories.py` bind-mount; delete patched file | 10 nodes / ~10s / `e3s04g2` | PASS |
| 3 | Drop `OPENAI_BASE_URL` env | 10 nodes / ~10s / `e3s04g3` | PASS |
| 4 | ADR-002 + ADR-017 amendments | (no smoke; doc-only) | PASS |

All four steps passed. No rollbacks. Each step committed independently
(no squash, no amend) so any single step can be reverted in isolation.

## Container build (Step 1)

**Image tag:** `graphiti-mcp-genai-bundled:e3-s04g`
**Image ID:** `ce41bd511e04` (manifest list digest of the multi-arch build)
**Base image (FROM):** `zepai/knowledge-graph-mcp@sha256:460bafb39439...` (digest-pinned per FR-DEP-010)
**Size:** 196 MB (3 MB increase from the 193 MB base — google-genai + 4 transitive deps)
**Bundled SDK:** `google-genai 1.73.1` (plus `google-auth 2.49.2`, `pyasn1 0.6.3`, `pyasn1-modules 0.4.2`, `websockets 16.0`)

The Dockerfile uses the bundled `uv` (at `/root/.local/bin/uv`) rather than
`pip` because the upstream venv at `/app/mcp/.venv` ships without a pip
script — uv-managed venvs install packages directly. Initial Dockerfile
draft used `/app/mcp/.venv/bin/pip` and failed at `[2/2] RUN ... did not
complete successfully: exit code: 127`; corrected to
`uv pip install --python /app/mcp/.venv/bin/python --no-cache 'google-genai>=1.62.0'`.

**Persistence test:** `docker compose up -d --force-recreate graphiti-mcp`
followed by `docker exec graphiti-mcp /app/mcp/.venv/bin/python -c "import
google.genai; print(google.genai.__version__)"` returned `1.73.1` (not the
expected `FAIL_SDK_MISSING`). The Dockerfile-baked install survives recreate.

## Final compose diff (since `d77c64f`)

Three logical changes in `homelab-apps/stacks/graphiti/docker-compose.yml`,
all in the `graphiti-mcp` service:

1. `image: zepai/knowledge-graph-mcp@sha256:460bafb39439...` replaced by
   `build: { context: ., dockerfile: Dockerfile }` + a stable local
   `image: graphiti-mcp-genai-bundled:e3-s04g` tag. (Step 1)
2. `environment:` block — `OPENAI_BASE_URL=http://192.168.50.160:4000/v1`
   line removed; replaced with a NOTE comment pointing at this evidence
   doc and the ADR amendments. `LITELLM_BASE_URL` and `EMBEDDER_BASE_URL`
   retained. (Step 3)
3. `volumes:` block — the `./factories.py.patched:/app/mcp/src/services/factories.py:ro`
   line removed; replaced with a NOTE comment. `config-graphiti-mcp.yaml`
   mount retained. (Step 2)

New file: `homelab-apps/stacks/graphiti/Dockerfile` (12 lines including
header comment).

Deleted file: `homelab-apps/stacks/graphiti/factories.py.patched`
(442 lines; recoverable from git via `git show 451ea91:stacks/graphiti/factories.py.patched`).

## Mini-smoke protocol (used between Steps 1, 2, 3)

Each smoke ran a fresh MCP session against `http://127.0.0.1:8000/mcp`
(no trailing slash — server returns 307 redirect to the no-slash form,
which urllib doesn't follow on POST), using the same episode body and
search query against three different `group_id` values so the runs don't
interfere with each other.

- `initialize` → `notifications/initialized` → `tools/call:add_memory` →
  poll `tools/call:search_nodes` every 5s until ≥1 node returns or 60s elapses
- Episode body: 5-sentence description of homelab + Graphiti + E3-S04g
  (intentionally entity-rich: Tom Amourette, pve1, pve2, pve3, Proxmox VE,
  Graphiti, gemini-2.5-flash-lite, E3-S04g, factories.py, OPENAI_BASE_URL)
- Acceptance: ≥1 node returned

All three smokes returned 10 nodes within ~10s of polling onset (Flash-Lite
extraction wall-clock ~5-8s + queue dispatch overhead). Full quality story
remains the property of `e3-s04f-retry-evidence.md` (10 entities + 10 edges
+ temporal facts at 7.5s); E3-S04g smokes are integration sanity, not
quality re-validation.

Smoke script lived at `/tmp/e3-s04g-smoke.py` for the duration of the story
and was cleaned up afterwards.

## ADR amendments (Step 4)

Both ADRs got a new top-level section inserted after the H1 title and
before the existing `## Context` / `## Revision notes` blocks. The original
v1 / v2 / v3 text is preserved verbatim — amendments add, never overwrite.

- [`ADR-002`](../../../_bmad-output/planning-artifacts/products/context-stack/adrs/ADR-002-gpt-4o-mini-for-graphiti-extraction-phase-1.md)
  — `Amendment 2026-04-27 (LLM provider switch — gpt-4o-mini → gemini-2.5-flash-lite)`.
  Records the cloud pivot, $1-3/month cost, unchanged privacy envelope,
  reversal trigger.
- [`ADR-017`](../../../_bmad-output/planning-artifacts/products/context-stack/adrs/ADR-017-graphiti-llm-local-vs-cloud-decision.md)
  — `Amendment 2026-04-27 (ADOPT-LOCAL reversed for Graphiti, retained for other workloads)`.
  Records the narrow reversal of v3's verdict (Graphiti only); local Gemma
  retained for Hermes/OWUI/dev queries. Three-condition reversal-of-reversal
  trigger documented.

## Deviations / surprises

- **Smoke script needed two fixes before first run:**
  1. MCP endpoint is `/mcp` (no trailing slash); upstream returns 307 to
     the no-slash form, which Python's `urllib` does not follow on POST.
     Adjusted `BASE` constant from `/mcp/` to `/mcp`.
  2. The upstream venv is uv-managed and ships without `pip`. Initial
     Dockerfile draft `RUN /app/mcp/.venv/bin/pip install ...` failed with
     `pip: not found`. Corrected to use the bundled `uv` (`/root/.local/bin/uv`)
     with `--python /app/mcp/.venv/bin/python` to target the right venv.
- **Container runs as root** — `docker exec graphiti-mcp id` returned
  `uid=0(root) gid=0(root)`. The brief's optional `USER` directives are
  not required and were dropped. Documented in the Dockerfile comment.
- **No HA / multi-step rollback needed** — every step's smoke passed first
  try after the smoke-script fixes above.

## Commit list

```
1483545 e3-s04g.3: drop OPENAI_BASE_URL env from graphiti compose — irrelevant for gemini provider
db61c3a e3-s04g.2b: remove factories.py.patched (no longer mounted)
7b6fc83 e3-s04g.2: drop factories.py bind-mount — redundant since gemini provider doesn't use openai factory arm
6b03b08 e3-s04g.1: persistent google-genai SDK via custom Dockerfile — survives --force-recreate
```

(homelab-apps repo, branch `feature/context-stack-e3-graphiti`)

```
7ebe1c5 e3-s04g.4: ADR-002 + ADR-017 amendments — Graphiti-LLM cloud pivot rationale
```

(homelab-playbook repo, same branch)

A 6th commit covering this evidence doc (`e3-s04g.5`) lands separately on
homelab-playbook.

## Status

**READY for E3-S06 — full functional smoke-test suite (extraction quality
at scale, similarity, bi-temporal, multi-hop, failure-injection).**

The Graphiti stack is now in a clean, persistent, documented state with no
known dead-weight workarounds for the cloud-Gemini extraction path. The
upstream `factories.py` is unmodified, no orphan env-vars remain, and the
google-genai SDK is baked into a stable local image tag that survives any
compose recreate cycle.
