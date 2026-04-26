---
adr: 003
title: "Embeddings — gemini-embedding-2 via LiteLLM gateway (v2 amends v1's text-embedding-3-small)"
status: accepted-v2
date: 2026-04-25
last_amended: 2026-04-26
authors: tomamourette (via BMAD director Claude)
context_question: null
---

# ADR-003: Keep embeddings on OpenAI text-embedding-3-small in all phases

## Amendment 2026-04-26 (v2 — embedder switch to gemini-embedding-2)

**Decision change:** Replace OpenAI `text-embedding-3-small` (v1 of this ADR) with
**Google `gemini-embedding-2`** (3072 dimensions, routed through the homelab
LiteLLM gateway alias on ct-ai-01).

**Why:** Gemini Embedding 2 went GA 2026-04-22 and leads MTEB English-v2 (73.30),
MMTEB Multilingual (68.32, +5.09 over runner-up), and MTEB Code (74.66) — three
tracks #1 simultaneously per the e3-s04b research addendum. Cost is $0.20/M paid
(~$0.24/month at our 1.2M tokens/mo volume) or $0 on the Gemini API free tier.
Both within ADR-008's $1/day cap.

**Correction note:** The first revision of the e3-s04b research report
(`docs/context-stack/sprint-3/e3-s04b-embedder-research.md` main body, line 18)
misattributed v2's MTEB score (68.32) to v1 (`gemini-embedding-001`). The
Addendum at line 124 of that file corrects this. v1's standalone scores are not
separately reported in v2-era benchmark recaps. Picking v1 would have meant
paying for a worse model under a wrong benchmark.

**Voyage AI revisited:** ADR-003 v1 rejected Voyage on the false premise of "no
documented Graphiti integration path." `graphiti_core/embedder/voyage.py` is
first-class (the source file ships with graphiti-core 0.28.2). Voyage-3-large
remains a viable backup but loses to Gemini-2 today on benchmark lead, free-tier
economics, and post-MongoDB-acquisition uncertainty.

**Reversal trigger (revised):**
- Back to `gemini-embedding-001` if v2 develops stability issues during Sprint 3
  dogfood.
- Back to `text-embedding-3-small` only if both Gemini SKUs become unviable.

**Implementation:**
- Vault: `vault_gemini_api_key` added to
  `homelab-infra/ansible/inventories/homelab/host_vars/ct-ai-01/vault.yml`
  (host-scoped per existing pattern; mirrors `vault_litellm_master_key`).
- Gateway: new alias `gemini-embedding-2` in
  `homelab-infra/ansible/roles/litellm-gateway/templates/litellm-config.yaml.j2`
  with `model: gemini/gemini-embedding-2` and `litellm_settings.drop_params: true`
  (drops openai-SDK's `encoding_format=base64` which Gemini rejects).
- Stack: `homelab-apps/stacks/graphiti/docker-compose.yml` repoints
  `EMBEDDER_BASE_URL` to the gateway and `EMBEDDER_MODEL` to
  `gemini-embedding-2`; `OPENAI_API_KEY` env-var carries the LiteLLM master key
  (same gateway, openai-protocol). `config-graphiti-mcp.yaml` updates
  `embedder.dimensions` from 1536 to 3072.
- Verified end-to-end at the Graphiti-core embedder client layer
  (`graphiti_core.embedder.openai.OpenAIEmbedder.create()` returns 3072-dim
  vectors via the gateway → Google path).
- Evidence: `docs/context-stack/sprint-3/e3-s04b-evidence.md`.

The original v1 Decision text below is retained for audit history.

---

## Context

Graphiti uses an embedding model at write time (to embed entity/relation surface forms for semantic recall) and at query time (to embed search queries for similarity matching against stored embeddings). Phase 4 of Context Stack bridges Graphiti's *LLM* call through LiteLLM to a local reasoner; the obvious adjacent question is whether the *embedding* call should also be local.

Three constraints push back on local embeddings:
1. Maintainer caveat: small/local embedders produce drifted vectors that degrade recall quality on Graphiti's prompt-shape.
2. Embedding cost is already trivial: `text-embedding-3-small` at $0.02/1M tokens with ~50 tokens/query × ~30 queries/session × ~50 sessions/month ≈ < $0.01/month (per `graphiti-claude-code-install-plan-2026-04-25.md` §4).
3. Embedding payloads contain *fact text* (decision snippets, conversation prose) — privacy boundary is NFR-PRIV-002 (embeddings *may* go cloud; source code does not). Routing them locally for privacy gain saves nothing because source code is already off this path.

The brief's §10.1 R5 explicitly accepts the OpenAI embedding dependency as low-severity.

## Decision

Use **OpenAI `text-embedding-3-small`** (1536 dimensions) as the embedding model in **all phases** (1, 2, 3, and 4). The Phase 4 LiteLLM bridge routes only `MODEL_NAME` and `SMALL_MODEL_NAME`; `EMBEDDER_MODEL_NAME` stays on OpenAI. This is FR-LLM-004 hard-locked.

## Consequences

**Positive.**
- < $0.01/month embedding cost — invisibly cheap; immune to NFR-COST-001 pressure.
- 1536-dim is Graphiti's documented default; no ANN-index tuning, no recall-quality experiments needed.
- Decoupling embeddings from the Phase 4 LLM bridge halves the Phase 4 risk surface — only LLM extraction quality is on the validation gate (FR-LLM-005), not embedding similarity recall.

**Negative.**
- Cloud dependency persists. NFR-PRIV-002 documents this acceptance; embedding payloads are fact-text, not source code.
- One vendor (OpenAI) for one tier (embeddings) that we don't otherwise use heavily — slight account-overhead cost for the operator.

**Neutral.**
- 1536 dims is generous; could compress to 768 with `dimensions` parameter at small recall cost, but cost savings are negligible.

## Alternatives Considered

1. **Local embedder via Ollama / vLLM (e.g., `nomic-embed-text`, `bge-m3`)** — rejected. Saves < $0.01/month; introduces recall-quality risk that is not documented in Graphiti's tests; doubles the Phase 4 validation surface (would need a separate well-formed-recall gate). Reconsider only if `text-embedding-3-small` is repriced > 10× or deprecated.
2. **Voyage AI embeddings** — rejected. Marginally better recall in some benchmarks but introduces a third API key and no documented Graphiti integration path.
3. **OpenAI `text-embedding-3-large`** — rejected. 3072 dims, ~7× cost of small at no measurable recall benefit at this single-operator data scale (≤ ~5000 entities lifetime).
4. **Drop embeddings, use lexical-only `search_facts`** — rejected. Graphiti's bi-temporal value depends on semantic recall ("how did I solve a similar X?"); lexical-only collapses Graphiti to a thin wrapper around grep.

## Validation / Exit Ramp

- **Validation:** monthly OpenAI billing line for embeddings is < $0.10. K5 ≥ 50% first-shot recall hits by week 4 (FR-MEM-007) — if K5 falls short, embedding model is a candidate variable, but cheaper diagnoses are tried first (CLAUDE.md prompt, group_id discipline).
- **Exit ramp:** swap `EMBEDDER_MODEL_NAME` to `text-embedding-3-large` (one env var change) for a controlled recall-quality test if K5 underperforms.
- **Reversal trigger:** if OpenAI deprecates `text-embedding-3-small` or its cost rises above $1/month for the operator's profile, evaluate `bge-m3` via LiteLLM with a 100-query recall validation set.

## References

- `graphiti-claude-code-install-plan-2026-04-25.md` §4 (cost model; maintainer caveat on small-model embedder quality)
- PRD FR-MEM-004, FR-LLM-004, NFR-PRIV-002
- Brief §10.1 R5 (cloud-line acceptance)
