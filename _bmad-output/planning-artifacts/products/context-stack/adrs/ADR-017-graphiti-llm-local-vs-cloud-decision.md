---
adr: 017
title: "Graphiti extraction LLM: STAY ON cloud (gpt-4o-mini) — Gemma 4 26B-MoE local stack times out at upstream"
status: accepted
date: 2026-04-26
authors: tomamourette (via BMAD director Claude)
context_question: null
supersedes: null
amends: null
---

# ADR-017: Graphiti extraction LLM stays on cloud (gpt-4o-mini) — Gemma 4 26B-MoE upstream times out at 30 s

## Context

ADR-002 selected `gpt-4o-mini` (cloud) as the Graphiti extraction LLM for Sprint 3 / Phase 1. ADR-011 deferred the local-LLM-via-LiteLLM bridge to Sprint 5 / Phase 4, gated by E4-S06's 50-fact validation that ≥ 95 % of extraction outputs parse as well-formed JSON.

The operator (E3-S01.5 unplanned spike, decision Option A) asked whether the validation gate could be brought forward to Sprint 3 to use the existing local Gemma 4 26B-MoE stack (per `project_hybrid_gemma_serving.md`: Unsloth UD-Q5_K_M, llama.cpp Vulkan build on PVE3, fronted by a LiteLLM gateway on `ct-ai-01`). If Gemma passed the gate, ADR-002 + ADR-011 would be amended to adopt local immediately.

This ADR records the spike result and the consequent decision.

## Spike methodology

- **Endpoint**: `http://192.168.50.160:4000/v1/chat/completions` (LiteLLM gateway on ct-ai-01, LAN reachable)
- **Model**: `gemma4-26b-text` (per ADR-002 candidate; specifically the 26B MoE, not the auto-router)
- **Auth**: master key sourced from `host_vars/ct-ai-01/vault.yml:vault_litellm_master_key` via SSH, written to a 600-mode file on the workstation, shredded after the spike
- **Corpus**: 50 episodes spanning 5 categories (architectural decisions, dated decisions with temporal markers, lessons-learned, supersession trails, entity-rich vignettes) at `homelab-playbook/docs/context-stack/sprint-3/e3-s01-5-spike/corpus-50-facts.jsonl`
- **Extraction prompt**: structured-JSON request mirroring Graphiti's documented entity+edge+temporal schema (entities array, edges array, valid_at, invalid_at)
- **Per-request budget**: temperature 0, max_tokens 800, client timeout 120 s (LiteLLM upstream timeout 30 s — built-in to gateway config)
- **Smoke test (gateway alive)**: trivial "Reply OK" prompt completed in ~0.93 s — confirmed gateway routing works

## Result

**The first real extraction request returned HTTP 502 from LiteLLM after 95 s wall-clock with the explicit upstream error**:

```
litellm.BadGatewayError: BadGatewayError: OpenAIException -
Upstream llama-server timeout after 30.0s on moe.
Received Model Group=gemma4-26b-text
Available Model Group Fallbacks=None
```

The Gemma 4 26B-MoE backend cannot complete a Graphiti-shaped extraction within the LiteLLM 30 s upstream timeout. The remaining 49 episodes were not run — the failure mode is structural (token-throughput-limited inference, not prompt-quality or schema-compliance), and re-running would simply confirm the same timeout.

Aggregate metrics by category: N/A — zero successful extractions.

**Schema-conformance rate**: N/A (no parseable output).
**JSON-parse rate**: 0% (the response payload was the LiteLLM error envelope, not a model completion).
**Verdict against the gate**: ≥ 95 % well-formed → not measurable; **STAY-ON-CLOUD** branch is taken.

## Why the timeout

`gemma4-26b-text` is a 26 B-parameter Mixture-of-Experts model running on llama.cpp's Vulkan compute path on PVE3 (per `project_hybrid_gemma_serving.md`). MoE on Vulkan/CPU is fundamentally token-throughput-limited compared to dense GPU inference. Graphiti's extraction prompt requests a structured-JSON output with multiple entity entries + edge entries + temporal markers; the 800-token output budget is well within Graphiti's normal operating envelope but exceeds what 26B-MoE-on-Vulkan can produce in 30 s.

The "OCULink dGPU" project (per `project_pve3_local_llm.md`) — which would provide GPU-accelerated inference and likely move this comfortably under 30 s — is documented as "blocked" pending hardware arrival.

## Decision

- **Sprint 3 / Phase 1 extraction LLM remains `gpt-4o-mini` (cloud)** as originally specified by ADR-002.
- **ADR-002 is unchanged** (model selection holds).
- **ADR-011 is unchanged** (LiteLLM bridge to local LLM remains a Sprint 5 / Phase 4 stretch goal).
- **ADR-003 is unchanged** (embeddings always stay on `text-embedding-3-small` cloud regardless of LLM-side decisions).

## Alternatives considered

1. **Adopt local Gemma 4 26B-MoE now** — the operator's preferred outcome. **Rejected**: timeout proves the stack cannot deliver extraction within Graphiti's normal request window; Sprint 3 would stall or run with multi-minute MCP-call latencies.
2. **Tune `gemma4-26b-text` temperature/sampling/parallelism** to fit under 30 s — speculative; the 26B-MoE-on-Vulkan token-throughput floor is ~tens of tokens/s, structured-JSON output is at minimum ~150–300 tokens for a real episode, and the gateway-side 30 s ceiling is also a Graphiti-side guard. Token-arithmetic doesn't close the gap. **Rejected**.
3. **Try `gemma4-auto`** (the LiteLLM router that decides between 26B-text and e4b-vision) — `e4b` is much smaller but is the vision variant, not the right tool. The auto-router would still send text-extraction to 26B-text. **Rejected** — same backend.
4. **Use a smaller/quantised local model** (e.g. gemma2-9b, qwen3-0.5b) to fit the 30 s budget — would meet latency but is below the ADR-003 maintainer caveat threshold for clean extraction JSON; defeats the purpose of the spike and re-introduces the original risk. **Rejected** for Sprint 3.
5. **Switch to OpenRouter (DeepSeek or similar) using the existing `vault_hermes_openrouter_api_key`** — cheaper than OpenAI direct; routes to a different cloud. Adds OpenRouter as a dependency for the memory layer. **Held in reserve** — operator-policy decision; not an ADR-017 item.

## Consequences

### Positive
- Sprint 3 unblocked. E3-S04 will wire `gpt-4o-mini` per the original ADR-002 plan as soon as `OPENAI_API_KEY` is provided.
- Honest empirical baseline: we know exactly why local doesn't work today (upstream timeout), and what would change the answer (GPU acceleration on PVE3).
- The 50-fact corpus + extraction prompt + run-spike.py are kept under `docs/context-stack/sprint-3/e3-s01-5-spike/` and can be re-run trivially when the GPU is operational — no new authoring needed for the Sprint-5 retry.

### Negative
- Memory layer now has a cloud LLM dependency for extraction (~$1/month at the user's projected usage; well within the < $20/month NFR-COST budget but ≠ $0).
- Extraction failures will surface as MCP errors and possibly partial graph state until E3-S04 + verifications are complete.
- ADR-011's Sprint-5 LLM-bridge story now has a hard precondition: GPU must be online before re-running the spike. This becomes a Sprint-5 entry-gate item.

### Neutral / known trade-offs
- Privacy: episode bodies leave the workstation for OpenAI extraction. Per ADR-003 this was already true for embeddings (and per Graphiti's documented architecture); this ADR doesn't change the privacy posture.
- Cost: well under budget; effectively negligible.

## Validation / exit ramp

- **Sprint 5 retry**: when the OCULink dGPU is operational on PVE3 and `gemma4-26b-text` (or whatever GPU-resident successor model is exposed by the LiteLLM gateway) can complete an 800-token structured-JSON output in ≤ 10 s, re-run `docs/context-stack/sprint-3/e3-s01-5-spike/run-spike.py` (already authored) for a fresh 50-fact gate. If ≥ 95 % well-formed JSON, ADR-002 + ADR-011 will be amended at that time.
- **Earlier retry**: if the operator switches `vault_hermes_openrouter_api_key` to point at a fast local-equivalent model (e.g. DeepSeek-via-OpenRouter), the same spike can be re-run against that endpoint without changing this ADR.
- **Exit if cost grows**: the `< $20/month` NFR-COST gate is the budget envelope. If `gpt-4o-mini` extraction crosses ~$10/month, evaluate the OpenRouter alternative (Option 5 above) at the next retro.

## References

- ADR-002 — gpt-4o-mini for Phase 1 extraction (unchanged by this ADR)
- ADR-003 — embeddings stay on cloud (unchanged)
- ADR-011 — LiteLLM bridge to local LLM (unchanged; Sprint 5 / Phase 4 still the target)
- ADR-015 — GitNexus container delivery (different decision, but established the "container-side stack > host-side ABI" pattern)
- `project_hybrid_gemma_serving.md` — the user's local LLM substrate and its Vulkan-mandatory architecture
- `project_pve3_local_llm.md` — Epic 8 status, including the "OCULink dGPU blocked" note
- Spike artifacts (this ADR's empirical basis):
  - `homelab-playbook/docs/context-stack/sprint-3/e3-s01-5-spike/corpus-50-facts.jsonl`
  - `homelab-playbook/docs/context-stack/sprint-3/e3-s01-5-spike/extraction-prompt.txt`
  - `homelab-playbook/docs/context-stack/sprint-3/e3-s01-5-spike/run-spike.py`
  - `homelab-playbook/docs/context-stack/sprint-3/e3-s01-5-spike/evidence.md`
