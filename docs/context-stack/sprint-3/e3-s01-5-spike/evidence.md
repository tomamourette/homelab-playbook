# E3-S01.5 (spike) — Gemma 4 26B-MoE Graphiti extraction validation evidence

**Date:** 2026-04-26
**Story:** E3-S01.5 (unplanned spike, brought forward from E4-S06 per operator decision A)
**Branch:** `feature/context-stack-e3-graphiti`
**Verdict:** **STAY-ON-CLOUD**
**ADR:** ADR-017 (records the decision in full)

## What was tested

| Item | Value |
|---|---|
| Endpoint | `http://192.168.50.160:4000/v1/chat/completions` (LAN, ct-ai-01) |
| Auth | `Authorization: Bearer <vault_litellm_master_key>` |
| Model | `gemma4-26b-text` (Gemma 4 26B-MoE per `project_hybrid_gemma_serving.md`) |
| Backend | llama.cpp Vulkan build on PVE3 (no GPU; OCULink dGPU blocked) |
| LiteLLM upstream timeout | 30 s (gateway default) |
| Client timeout | 120 s |
| Sampling | temperature 0, max_tokens 800 |
| Corpus | 50 episodes × 5 categories at `corpus-50-facts.jsonl` |

## Results

**Smoke test (trivial prompt)** — gateway alive: HTTP 200 in ~0.93 s on a "Reply OK" payload.

**Real extraction (1 episode, ADR-001 paraphrase, ~150 word source)**:
- HTTP 502 after 95 s wall-clock
- Upstream LiteLLM error verbatim:
  ```
  litellm.BadGatewayError: BadGatewayError: OpenAIException -
  Upstream llama-server timeout after 30.0s on moe.
  Received Model Group=gemma4-26b-text
  Available Model Group Fallbacks=None
  ```
- Zero parseable model output.

**Remaining 49 episodes were not executed** — the failure mode is structural (token-throughput on the Vulkan stack, not prompt-quality or JSON-compliance). Running 49 more identical 30-second-upstream-timeouts would have produced ~75 minutes of confirmed-same-result data with no incremental decision value.

## Verdict gate evaluation

| Gate threshold | Outcome |
|---|---|
| ≥ 95 % well-formed JSON → ADOPT-LOCAL | Not measurable (no parseable output) |
| 80–94 % → ADOPT-WITH-CAVEATS | Not measurable |
| < 80 % → STAY-ON-CLOUD | **Triggered** (0 % well-formed JSON; 100 % upstream-timeout error) |

## Decision

**STAY-ON-CLOUD for Sprint 3.** ADR-002 + ADR-011 + ADR-003 all unchanged. ADR-017 records this verdict and the conditions under which it would change (GPU operational on PVE3, then re-run this same spike).

## Sprint-5 follow-up trigger

Re-run `run-spike.py` against the same gateway when:
1. PVE3 OCULink dGPU is online, AND
2. `gemma4-26b-text` (or its GPU-resident successor) is exposed via the LiteLLM gateway, AND
3. Token-throughput permits 800-token structured-JSON outputs in ≤ 10 s.

If the re-run hits the 95 % well-formed JSON gate, ADR-002 + ADR-011 will be amended at that time.

## Artifact inventory

- `corpus-50-facts.jsonl` — 50 episodes × 5 categories (kept for re-run)
- `extraction-prompt.txt` — Graphiti-shaped structured-JSON system prompt
- `run-spike.py` — runner (reads key from `~/.litellm-spike-key`, configurable via `LITELLM_BASE_URL` + `MODEL_NAME` env)
- `evidence.md` (this file)
- `ADR-017-graphiti-llm-local-vs-cloud-decision.md` — full decision record
- **Not retained**: `~/.litellm-spike-key` was shredded immediately after the test request (no key in repo, no key in chat history persisted in any file).

## Notes for the next retry

- The `run-spike.py` script supports `LITELLM_BASE_URL` + `MODEL_NAME` env-var overrides, so retrying against a different endpoint or model is a one-line invocation:
  ```bash
  LITELLM_BASE_URL=http://192.168.50.160:4000 \
  MODEL_NAME=gemma4-26b-text \
  python3 run-spike.py
  ```
- Single-episode testing (`--limit 1` was not implemented; consider adding for the Sprint-5 retry to fail-fast)
- The LiteLLM 30 s upstream timeout is a property of the gateway config, not Graphiti — increasing it would not change Graphiti's own request behavior, just shift the failure mode from gateway-side to Graphiti-side
