---
adr: 011
title: "Phase 4 LiteLLM bridge via OPENAI_BASE_URL env var (no Graphiti fork)"
status: accepted
date: 2026-04-25
authors: tomamourette (via BMAD director Claude)
context_question: Q4
---

# ADR-011: Phase 4 LiteLLM bridge via OPENAI_BASE_URL env var (no Graphiti fork)

## Context

PRD Q4 asks: does `mcp-v1.0.2` of Graphiti's MCP server expose `OpenAIGenericClient` via env var or CLI flag, allowing us to route Graphiti's LLM call through the operator's LiteLLM gateway (`hybrid_gemma_serving` epic) without forking the Graphiti source?

Two facts establish the answer:

1. **Direct source inspection (April 2026):** the `mcp_server/src/graphiti_mcp_server.py` file delegates client creation to `LLMClientFactory.create(self.config.llm)`. The CLI flag `--llm-provider` accepts `openai`, `azure_openai`, `anthropic`, `gemini`, `groq` — but **NOT** `openai_generic`. The `LLMClientFactory` source (in `services/factories/`) determines the actual class, which is the standard `OpenAIClient` (using `/v1/responses`) for `openai`. The `OpenAIGenericClient` (which uses `/v1/chat/completions`) is in `core/llm_client/` but is not selectable via the MCP server's surface.

2. **LiteLLM does support `/v1/responses` endpoints** — as of `litellm>=1.50` (Q1 2026), LiteLLM's proxy emulates the OpenAI Responses API for compatible upstream models. Graphiti's default `OpenAIClient` posting to LiteLLM's `/v1/responses` works *if the upstream model handles JSON Schema response format*, which most LiteLLM-fronted models do (Ollama via LiteLLM, vLLM, OpenAI passthrough).

3. **Failure mode:** if the upstream model behind LiteLLM does NOT speak Responses API correctly, Graphiti's extraction silently fails (malformed JSON → episode rejected). This is exactly the failure surface FR-LLM-005's 95%-well-formed-JSON validation gate is designed to catch.

The original install plan (§4) mentioned `OpenAIGenericClient` as a path to consider; verification confirms it requires forking the MCP server's factory, which violates the < 1 day reversibility constraint (NFR-MAINT-001).

## Decision

**For the Phase 4 LiteLLM bridge, use the standard `OpenAIClient` path with `OPENAI_BASE_URL` and `MODEL_NAME` env vars pointed at LiteLLM. Do NOT fork Graphiti's MCP server. Rely on LiteLLM's Responses API emulation.**

### Concrete config (Phase 4 only)

In `/srv/graphiti/.env`:
```env
# Phase 4 — point Graphiti's OpenAI SDK at LiteLLM
OPENAI_API_KEY=sk-litellm-anything       # required field, not validated by LiteLLM
OPENAI_BASE_URL=http://hybrid-gemma-litellm.tail-scale.ts.net:4000/v1
MODEL_NAME=gemma-reasoner                # whatever LiteLLM exposes
SMALL_MODEL_NAME=gemma-reasoner
EMBEDDER_MODEL_NAME=text-embedding-3-small  # stays on OpenAI per ADR-003 / FR-LLM-004
```

**Embeddings are NOT routed through LiteLLM** — `EMBEDDER_MODEL_NAME` keeps its default and Graphiti's embedder client uses the OpenAI default base URL because `OPENAI_BASE_URL` only affects the chat-completions/responses client *if* LiteLLM is fronting the embed model too — which it isn't. To enforce isolation, override `EMBEDDER_OPENAI_BASE_URL` if the upstream Graphiti version supports it; otherwise rely on the LiteLLM proxy's passthrough route for `text-embedding-3-small` directly to OpenAI (LiteLLM does this transparently for unmapped models).

### Validation gate (FR-LLM-005)

Before promoting Phase 4 off `ct-dev-homelab`, run a 50-fact validation set:
- 50 representative episode prompts (decisions, lessons, project facts) authored as a fixture file.
- Feed each through Graphiti via the LiteLLM-routed config.
- Measure: % of episodes that complete without `JSONDecodeError` or `Cypher error: invalid relation` in `docker compose logs graphiti-mcp`.
- **Pass:** ≥ 95% well-formed.
- **Fail:** auto-fallback (FR-LLM-006) to cloud `gpt-4o-mini` by reverting `OPENAI_BASE_URL` and `MODEL_NAME` (single env-var change, FR-LLM-008 reversibility).

### If LiteLLM's Responses API emulation is broken

Fallback path: deploy a **side-by-side LiteLLM proxy that *only* exposes `/v1/chat/completions`**, and front-end Graphiti to that proxy at a separate port. This still does not require forking Graphiti — it requires running LiteLLM with a config that strips the Responses API surface, forcing fallback. This is a 30-minute LiteLLM config change, captured as a runbook in the wiki at Phase 4 time.

## Consequences

**Positive.**
- Zero Graphiti fork — install-plan environment-variable path stays clean (FR-LLM-008 single-day reversibility).
- Validation gate is observable (`docker compose logs graphiti-mcp | grep JSONDecodeError`), not theoretical.
- Auto-fallback is a one-env-var revert; no rebuild.

**Negative.**
- Depends on LiteLLM Responses API emulation working correctly for the chosen upstream model. The 95% gate is exactly there to detect failure.
- Embeddings-bypass relies on LiteLLM's transparent passthrough; if LiteLLM is configured restrictively (deny-by-default model mapping), embeddings break silently. Document the model-mapping requirement in the Phase 4 runbook.

**Neutral.**
- If a future Graphiti MCP release exposes `--llm-provider openai_generic` (or env var equivalent), revisit and switch to that — likely cleaner long-term.

## Alternatives Considered

1. **Fork Graphiti MCP server to expose `OpenAIGenericClient`** — rejected. Violates < 1 day reversibility; introduces an upstream-tracking burden; defeats the install-plan §10 risk mitigation ("pin a specific tag").
2. **Wrap Graphiti behind a thin reverse-proxy that translates `/v1/responses` → `/v1/chat/completions`** — rejected. New layer, new failure mode; LiteLLM already does this when configured correctly. This becomes the *fallback if LiteLLM fails*, not the primary path.
3. **Skip Phase 4 entirely (cloud-only)** — Phase 4 is already stretch. If the validation gate fails repeatedly, this is the documented exit (Phase 1-3 ship without Phase 4 per FR-LLM-007).
4. **Run a separate LiteLLM proxy specifically for Graphiti, with a chat-completions-only config** — accepted as the *fallback* path if direct routing through `hybrid_gemma_serving`'s LiteLLM has Responses-API issues. Not the primary path.

## Validation / Exit Ramp

- **Validation:**
  - Phase 4 spike (Sprint 4): set up `OPENAI_BASE_URL` to LiteLLM in `ct-dev-homelab`'s Graphiti `.env`; run the 50-fact validation set; record pass/fail rate.
  - **Promote Phase 4 only if ≥ 95% pass** (FR-LLM-005).
  - **Cost-neutrality check** (NFR-COST-003): 7-day spend pre-bridge vs post-bridge at otherwise-equal usage.
- **Exit ramp:** revert `.env` (one env-var change, FR-LLM-008); Graphiti returns to cloud `gpt-4o-mini` instantly.
- **Reversal trigger:** if validation gate passes but K1-K6 KPIs regress in week 5 (post-bridge week 1), revert the bridge — local-LLM gain is not paying its cost.

## References

- PRD FR-LLM-001 through FR-LLM-008, NFR-AVAIL-003
- `graphiti-claude-code-install-plan-2026-04-25.md` §4 (LiteLLM hybrid path), §10 (open verification step #2)
- Brief §8.4, §10.1 R3
- Direct source inspection (April 2026): `getzep/graphiti` `mcp_server/src/graphiti_mcp_server.py` confirms `--llm-provider` choices do not include `openai_generic`
- Project memory `project_hybrid_gemma_serving.md`
