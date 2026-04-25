---
adr: 002
title: "Use gpt-4o-mini for Graphiti extraction in Phase 1"
status: accepted
date: 2026-04-25
authors: tomamourette (via BMAD director Claude)
context_question: null
---

# ADR-002: Use gpt-4o-mini for Graphiti extraction in Phase 1

## Context

Graphiti runs an LLM at ingest time to extract entities and relations from each episode. The brief's $20/month NFR-COST-001 leaves little room for an expensive primary model, and Graphiti's prompts are demanding — small/local models are documented as producing malformed JSON that breaks ingestion.

We need a model for Phase 1 that:
- Is cheap enough to keep monthly spend < $20 with normal use (~50 sessions × ~10 episodes).
- Is the documented Graphiti default (lowest divergence from upstream tests/docs).
- Is reliably available on the OpenAI API (no preview-tier risk).
- Can be swapped to a local LLM in Phase 4 without re-architecting (FR-LLM-001).

Phase 4 stretch is to bridge through LiteLLM to the operator's `hybrid_gemma_serving` 27B reasoner; that swap is gated on a 95% well-formed-JSON validation set (FR-LLM-005), so the Phase 1 model must still be reachable as the auto-fallback (FR-LLM-006).

## Decision

Adopt **OpenAI `gpt-4o-mini`** as the Phase 1 extraction LLM and small-model path (`MODEL_NAME=gpt-4o-mini`, `SMALL_MODEL_NAME=gpt-4o-mini`). Hold this choice through Phase 1–3; reconsider in Phase 4 only behind the validation gate. Embeddings stay on OpenAI `text-embedding-3-small` per ADR-003.

## Consequences

**Positive.**
- Documented Graphiti default → install-plan Step 4 lifts straight from upstream docs with no patching.
- ~$0.0006/episode at 2k input + 500 output tokens (per `graphiti-claude-code-install-plan-2026-04-25.md` §4 cost model). At ~500 episodes/month (well above the K4 25-facts/week target), that's ~$0.30/month — well under the NFR-COST-001 < $20 ceiling and the NFR-COST-002 daily $1 cap.
- "Small enough to be cheap, large enough to extract clean JSON" — matches the maintainer caveat that smaller local models break.
- Auto-fallback for Phase 4 (FR-LLM-006) is still this same model — no new code required.

**Negative.**
- Cloud dependency keeps a privacy line (NFR-PRIV-002 — embeddings + extraction prompts cross to OpenAI). Source code does not cross; conversation snippets and decisions do.
- OpenAI pricing changes are an external risk; documented in the assumptions section of the PRD (§9.2).
- Single-vendor LLM dependency — same risk graphify carries with Anthropic; mitigated by the architectural goal of swappable LLM in Phase 4.

**Neutral.**
- Sonnet/Opus would extract higher-quality relations but cost an order of magnitude more; not worth the delta for a single-operator decision archive.

## Alternatives Considered

1. **Anthropic Sonnet 4.7** — rejected for Phase 1. ~50× more expensive than gpt-4o-mini at the same input/output ratio. Would blow NFR-COST-001 with normal use unless heavily throttled, and Graphiti's docs are not written against Sonnet's tool/JSON conventions.
2. **Anthropic Haiku** — rejected. Cheaper than Sonnet but more expensive than gpt-4o-mini, and not Graphiti's documented default — adoption risk on prompt-template drift.
3. **Local LLM via LiteLLM (Phase 1 default)** — rejected per maintainer caveat (small local models produce malformed extraction JSON). This is exactly the failure mode Phase 4's validation gate exists to test for; using it as Phase 1 default would miss the validation step and risk a non-ingesting graph from day one.
4. **gpt-4o (full)** — rejected. ~10× the cost of gpt-4o-mini for marginal extraction-quality gain at this corpus size; extraction-quality K4 ≥ 25 facts/week is achievable with the mini.

## Validation / Exit Ramp

- **Validation:** weekly OpenAI usage check (FR-OBS-001); week-4 spend < $20 for combined ingest + embed (NFR-COST-001).
- **Exit ramp:** if extraction quality is poor (operator-perceived noise in `search_facts` results), pin `MODEL_NAME=gpt-4o` for one week as a controlled experiment — single env var change, no architectural shift.
- **Reversal trigger:** if `gpt-4o-mini` is deprecated or repriced > 3× by OpenAI, switch to current cheap-tier OpenAI default (assessed at the time) or accelerate Phase 4 LiteLLM bridge.

## References

- `graphiti-claude-code-install-plan-2026-04-25.md` §4 (LLM choice, cost model)
- PRD FR-MEM-004, NFR-COST-001, NFR-COST-002
- ADR-003 (embeddings), ADR-008 (cost cap), ADR-011 (LiteLLM bridge)
