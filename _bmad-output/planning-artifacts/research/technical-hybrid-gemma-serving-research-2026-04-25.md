---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments: []
workflowType: 'research'
lastStep: 6
research_type: 'technical'
research_topic: 'Hybrid local-LLM serving on AMD Strix iGPU: dual llama-server (Gemma 4 E4B multimodal + Gemma 4 26B-A4B MoE text reasoner) fronted by a custom OpenAI-compatible orchestration proxy with auto multimodal routing and tool-call agent loop'
research_goals: |
  1. Validate the architecture (two backends + proxy) against current 2026 community practice and llama.cpp constraints (Vulkan vs ROCm, MoE quirks, mmproj/draft incompatibilities).
  2. Compare orchestration approaches: custom FastAPI proxy vs LiteLLM proxy vs Open WebUI Pipes — for cross-app (non-WebUI) usage.
  3. Decide auto-preprocess vs tool-call vs hybrid routing for multimodal traffic.
  4. Risk assessment: tool-call reliability on abliterated 26B-A4B (TrevorJS) + reasoner alternatives if it degrades.
  5. Produce a concrete, citable spec the implementation can follow (build flags, systemd structure, Ansible touch-points, ports, model aliases, latency budget).
user_name: 'tomamourette'
date: '2026-04-25'
web_research_enabled: true
source_verification: true
---

# Research Report: Technical

**Date:** 2026-04-25
**Author:** tomamourette
**Research Type:** Technical

---

## Research Overview

This document captures comprehensive technical research on building a **hybrid local-LLM serving architecture** for `ct-ai-01` (Proxmox LXC on `pve3`, AMD Radeon 880M iGPU, 32 GB dedicated VRAM + 32 GB GTT), pairing **Gemma 4 E4B** (multimodal: vision + audio) with **Gemma 4 26B-A4B** (MoE text reasoner) behind a **custom OpenAI-compatible orchestration proxy**. The proxy auto-routes image/audio content through E4B for description, hands the resulting text to 26B-A4B for reasoning, and exposes a tool-call agent loop so 26B can re-query E4B with specific follow-up questions. A LiteLLM gateway sits in front for authentication, observability, and rate limiting, providing a single endpoint for multi-app consumption (Open WebUI, Continue.dev, Cursor, mobile, scripts).

The research validates the architecture against current 2026 community practice and llama.cpp constraints (Vulkan vs ROCm, MoE quirks, mmproj/draft incompatibilities), compares orchestration approaches (custom FastAPI vs LiteLLM vs Open WebUI Pipes), recommends auto-preprocessing for multimodal traffic with a tool-call layer for deeper queries, and produces a concrete implementation roadmap with build flags, systemd unit templates, Ansible role structure, and 10 explicit acceptance criteria. The final architectural recommendation is a **hybrid preprocessor + single-threaded master loop** (per Anthropic's published agent guidance), explicitly choosing **Unsloth UD-Q5_K_M** for the reasoner over the abliterated TrevorJS variant due to chat-template stability and tool-call reliability concerns.

For the executive summary, key findings, and strategic recommendations, see **§Research Synthesis and Strategic Recommendations** at the end of the document.

---

<!-- Content will be appended sequentially through research workflow steps -->

## Technical Research Scope Confirmation

**Research Topic:** Hybrid local-LLM serving on AMD Strix iGPU: dual `llama-server` (Gemma 4 E4B multimodal + Gemma 4 26B-A4B MoE text reasoner) fronted by a custom OpenAI-compatible orchestration proxy with auto multimodal routing and tool-call agent loop.

**Research Goals:**

1. Validate the architecture (two backends + proxy) against current 2026 community practice and llama.cpp constraints (Vulkan vs ROCm, MoE quirks, mmproj/draft incompatibilities).
2. Compare orchestration approaches: custom FastAPI proxy vs LiteLLM proxy vs Open WebUI Pipes — for cross-app (non-WebUI) usage.
3. Decide auto-preprocess vs tool-call vs hybrid routing for multimodal traffic.
4. Risk assessment: tool-call reliability on abliterated 26B-A4B (TrevorJS) + reasoner alternatives if it degrades.
5. Produce a concrete, citable spec the implementation can follow (build flags, systemd structure, Ansible touch-points, ports, model aliases, latency budget).

**Technical Research Scope:**

- Architecture Analysis — dual-backend topology, agent-loop pattern, streaming through proxies, Vulkan vs ROCm on Strix-class iGPUs, MoE expert-loading under speculation
- Implementation Approaches — FastAPI vs LiteLLM proxy, Open WebUI Pipes/Functions, systemd + Ansible deployment patterns
- Technology Stack — llama.cpp build flags, mmproj/multimodal handling, OpenAI-compatible API surface, Python async stack, Gemma 4 quant trade-offs
- Integration Patterns — `/v1/chat/completions` inspection, tool-call schemas for `analyze_image`/`transcribe_audio`, model-alias multiplexing, SSE pass-through, Open WebUI multi-endpoint registration
- Performance Considerations — KV/VRAM budget, prefill/gen tok/s on Radeon 880M class, latency budget for multimodal preprocessing, abliteration impact on tool-calls

**Research Methodology:**

- Current web data with rigorous source verification
- Multi-source validation for critical technical claims
- Confidence level framework for uncertain information
- Comprehensive technical coverage with architecture-specific insights

**Scope Confirmed:** 2026-04-25

---

## Technology Stack Analysis

### Top 7 Gotchas (Executive Summary)

1. **Use Vulkan/RADV, not ROCm.** Confirmed open ROCm endless-loop bug on `gemma-4-26B-A4B` for gfx1151 (Strix-class) — outputs garbage like `<|channel><unused24>...`. Other Gemma 4 SKUs work on ROCm, but 26B-A4B does not. _Source: [llama.cpp #21416](https://github.com/ggml-org/llama.cpp/issues/21416)._
2. **TrevorJS abliterated GGUFs ship with a broken chat template.** Outputs land in `reasoning_content` while `content` stays empty in `/v1/chat/completions`. llama.cpp logs `"detected an outdated gemma4 chat template"`. Fix: override with `--chat-template-file` pointing at [asf0/gemma4_jinja](https://github.com/asf0/gemma4_jinja), which also preserves tool calls. _Source: [TrevorJS HF discussion #2](https://huggingface.co/TrevorJS/gemma-4-26B-A4B-it-uncensored-GGUF/discussions/2)._
3. **Tool-use requires `--jinja`.** Without the flag, `tool_calls` endpoints are disabled in `llama-server`. Abliteration impact on tool-call accuracy is **not formally benchmarked** — flag as risk.
4. **mmproj is one-per-process and incompatible with `--model-draft`.** Speculative decoding cannot coexist with multimodal in the same `llama-server`. _Source: [llama.cpp discussion #21826](https://github.com/ggml-org/llama.cpp/discussions/21826)._
5. **A single `llama-server` with `--mmproj` already handles BOTH text and vision requests.** Clients pass `image_url` blocks in OpenAI-format messages; same `/v1/chat/completions` endpoint serves both. So splitting purely by modality on the *server* side is unnecessary; the split is needed for the *quality* reason (E4B can't reason as well as 26B).
6. **LiteLLM was compromised on PyPI in March 2026.** Supply-chain attack — pin versions, verify hashes if used. _Source: [dev.to LLM proxy landscape 2026](https://dev.to/stockyarddev/the-llm-proxy-landscape-in-2026-helicone-acquired-litellm-compromised-and-whats-next-3oon)._
7. **Helicone is in maintenance mode** after Mintlify acquisition — avoid for new builds.

### Programming Languages

- **Python 3.11+** for the orchestration proxy. FastAPI/httpx/sse-starlette ecosystem is mature and matches the 2026 OpenAI-compatible proxy reference templates.
- **C++** at the inference layer — already chosen via `llama.cpp`. No language decision needed there.
- _Confidence: HIGH._ Python is the de-facto choice for OpenAI-compatible proxies in 2026 ([dev.to gateway comparison](https://dev.to/varshithvhegde/top-5-llm-gateways-in-2026-a-deep-dive-comparison-for-production-teams-34d2)).

### Inference Runtime Stack (`llama.cpp`)

| Component | Choice | Rationale |
|---|---|---|
| Backend | **Vulkan / RADV** (`-DGGML_VULKAN=ON`) | Decisively beats ROCm on Strix-class iGPUs; sidesteps the [#21416](https://github.com/ggml-org/llama.cpp/issues/21416) bug. |
| Driver | **Mesa RADV**, not AMDVLK | Fewer regressions on RDNA 3.5 per [llm-tracker Strix Halo notes](https://llm-tracker.info/_TOORG/Strix-Halo). |
| Server | `llama-server` (built-in) | OpenAI-compatible `/v1/chat/completions` + `/v1/models`. |
| Tool-use flag | `--jinja` (mandatory) | Otherwise function-calling endpoints are disabled. |
| Chat template | `--chat-template-file ./gemma4-asf0.jinja` | Avoids `reasoning_content` leakage on TrevorJS GGUF. |
| Batch tip | `-b 256` on Vulkan | Avoids hangs on large models per llm-tracker. |

### Gemma 4 Model SKUs

| SKU | Effective / Total | Vision | Audio | Tool-use | Context |
|---|---|---|---|---|---|
| E2B | 2.3B eff / 5.1B (PLE) | ✅ | ✅ (≤30s) | ✅ | 128K |
| **E4B** (current) | 4.5B eff / 8B (PLE) | ✅ | ✅ (≤30s) | ✅ | 128K |
| **26B-A4B** (target add) | 3.8B active / 25.2B total (MoE 8/128) | ✅ | ❌ | ✅ | 256K |
| 31B | 30.7B dense | ✅ | ❌ | ✅ | 256K |

_Source: [Google Gemma 4 model card](https://ai.google.dev/gemma/docs/core/model_card_4), [HF Gemma 4 blog](https://huggingface.co/blog/gemma4)._

### Quantization Options for 26B-A4B

- **TrevorJS (abliterated, uncensored)**: only Q4_K_M (16.8 GB) and Q8_0 (26.9 GB). No Q4_K_XL. No mmproj.
- **Unsloth (official base)**: full ladder — IQ2_XXS (9.9 GB) → UD-Q4_K_M (16.9 GB) → UD-Q4_K_XL (17.1 GB) → UD-Q5_K_M (21.2 GB) → UD-Q5_K_XL (21.2 GB) → UD-Q6_K (23.2 GB) → Q8_0 (26.9 GB) → BF16 (50.5 GB) + MXFP4_MOE (16.6 GB). Unsloth also publishes an mmproj file (`mmproj-BF16.gguf`).
- **Sweet spot for 32 GB VRAM**: **UD-Q5_K_M ≈ 21 GB weights** + small KV cache (small because only 3.8B active) → ~24-25 GB total at 32K context. Comfortable in dedicated VRAM, leaves GTT for E4B + headroom.
- **Trade-off**: TrevorJS gives uncensored text but only Q4 (lower quality + chat-template fix needed). Unsloth gives Q5/Q6 sweet-spot quants but no abliteration. Hybrid approach worth considering: Unsloth for text reasoning, TrevorJS only if uncensored required.
- _Sources: [TrevorJS HF page](https://huggingface.co/TrevorJS/gemma-4-26B-A4B-it-uncensored-GGUF), [Unsloth gemma-4-26B-A4B-it-GGUF](https://huggingface.co/unsloth/gemma-4-26B-A4B-it-GGUF), [Unsloth Gemma 4 docs](https://unsloth.ai/docs/models/gemma-4)._

### Orchestration / Proxy Stack

| Component | Choice | Why |
|---|---|---|
| Outer gateway | **LiteLLM proxy** (`:4000`) | Auth/virtual keys, Prometheus metrics, request logging, OpenTelemetry, `/v1/models` aggregation — all built-in. ~50 lines saved per feature. **PIN VERSION** (March 2026 PyPI compromise). |
| Inner router | **Custom FastAPI** (`:8000`) | LiteLLM cannot chain calls (await Model A → call Model B); content sniffing for `image_url` + agent-loop must live here. ~300 lines. |
| Stream protocol | **SSE via `sse-starlette`** | OpenAI-compatible. Set proxy `proxy_read_timeout` ≥ 600s to avoid stream kills. |
| Upstream client | **`httpx.AsyncClient`** | Async, supports streaming responses. |
| Models | **`pydantic`** | OpenAI request/response schemas. |

**Reference templates** worth cloning over writing from scratch:
- [`talesmousinho/fastapi-openai-sse-stream`](https://github.com/talesmousinho/fastapi-openai-sse-stream) — SSE forwarding pattern
- [`AlirezaAzadbakht/minimal-fastapi-openai-proxy`](https://github.com/AlirezaAzadbakht/minimal-fastapi-openai-proxy) — multi-tenancy + OpenAI SDK compat
- [`fangwentong/openai-proxy`](https://github.com/fangwentong/openai-proxy) — transparent forwarding + logging
- [`ahmad2b/openai-agents-streaming-api`](https://github.com/ahmad2b/openai-agents-streaming-api) — streaming through an agent loop
- [`Multimodal Reasoning Pipe V1`](https://openwebui.com/f/snicky666/multimodal_reasoning_pipe_v1) — Open WebUI Pipe doing exactly the describe-then-reason flow (read its source as logic reference)

### Open WebUI Integration Surface

- **Single endpoint registration**: point Open WebUI at the LiteLLM `:4000` URL via `OPENAI_API_BASE_URLS`; auto-discovers virtual model names (`gemma4-auto`, `gemma4-26b-text`, `gemma4-e4b-vision`) from `/v1/models`. _Source: [Open WebUI OpenAI-compatible quick start](https://docs.openwebui.com/getting-started/quick-start/connect-a-provider/starting-with-openai-compatible/)._
- **Pipes appear as virtual models** with "External" badge ([Pipes docs](https://docs.openwebui.com/features/extensibility/pipelines/pipes/)) — but it's **unclear if Open WebUI re-exposes Pipes via OpenAI-compatible endpoints to external clients**. Treat this as a confirmed gap → canonical endpoint must be the FastAPI router, not a Pipe.
- **Known bug**: Open WebUI has [an infinite-loop streaming tool messages issue (#23066)](https://github.com/open-webui/open-webui/issues/23066). Proxy must emit clean tool-call deltas.

### Deployment Stack

| Component | Choice |
|---|---|
| Host | Proxmox LXC `ct-ai-01` (VMID 160 on `pve3`) — already provisioned |
| iGPU access | LXC GPU passthrough (already working for current `llama-server`) |
| Process supervision | **systemd** units — matches existing `llama-server.service` and `ollama.service` patterns |
| Service ordering | New units: `llama-server-26b.service`, `gemma-hybrid-proxy.service`, `litellm-gateway.service`. Add `Requires=`/`After=` chain. |
| Configuration management | **Ansible role** in homelab-playbook — matches existing pattern |
| Secrets | Vault-encrypted (matches existing pattern for Sparkle-CPS Azure DevOps creds) |
| Network exposure | **Tailscale-only** (matches phone-notifications policy) |
| Open WebUI | Existing Docker container on `:3000`, repointed at LiteLLM `:4000` |

### Realistic Performance Numbers (Radeon 880M / 8060S Class)

| Model | Backend | Quant | Prefill | Decode |
|---|---|---|---|---|
| Gemma 4 26B-A4B | Vulkan/RADV | Q4_K_M | ~239 tok/s | ~21 tok/s |
| Gemma 4 26B-A4B | Vulkan/RADV (optimized batched) | Q4 | — | up to 52 tok/s |
| Gemma 4 E4B + mmproj | Vulkan/RADV | Q5_K_P | ~400 tok/s (estimate) | ~30-60 tok/s (estimate) |

- 880M is one tier above the 760M (which hit ~21 tok/s on 26B-A4B Q4_K_M); expect roughly the same band since memory bandwidth is the bottleneck.
- _Sources: [dev.to ~21 tok/s Gemma 4 Ryzen mini PC](https://dev.to/hrodrig/21-toks-gemma-4-on-a-ryzen-mini-pc-llamacpp-vulkan-and-the-messy-truth-about-local-chat-m82), [Level1Techs Strix Halo benchmarks](https://forum.level1techs.com/t/strix-halo-ryzen-ai-max-395-llm-benchmark-results/233796), [knightli GPU benchmark scoreboard](https://www.knightli.com/en/2026/04/23/llama-cpp-gpu-benchmark-cuda-rocm-vulkan-scoreboard/)._

### Adoption Trends & Alternatives Considered

- **OpenRouter self-hosted**: no first-party offering; community proxies are not general-purpose routers.
- **Helicone**: maintenance mode post-Mintlify — skip.
- **Portkey, TrueFoundry, Kong AI Gateway**: enterprise-grade, overkill for single-user homelab.
- **llama-swap**: lighter than a router but only swaps models on one llama-server — no chaining.
- **Olla**: newer self-hosted gateway worth glancing at; unconfirmed whether it does content-based fan-out.

### Recommended Target Architecture

```
Clients (Open WebUI, Continue, Cursor, mobile)
    │  bearer token
    ▼
LiteLLM proxy :4000   [auth, virtual keys, rate limit, logs, /v1/models aggregator]
    │  internal forward
    ▼
FastAPI router :8000  [content sniff → E4B describe → 26B reason → tool loop → SSE]
    │                                       │
    ▼                                       ▼
llama-server :8080                   llama-server :8081
(Gemma 4 E4B Uncensored Q5_K_P       (Gemma 4 26B-A4B UD-Q5_K_M
 + mmproj, Vulkan)                    text-only, Vulkan, --jinja
                                      + asf0/gemma4_jinja template)
```

### Confidence & Gaps

- **HIGH confidence**: Vulkan choice, model SKU map, Unsloth quant ladder, FastAPI stack, LiteLLM as outer gateway, Open WebUI registration mechanism.
- **MEDIUM confidence**: 880M-specific perf numbers (extrapolated from 760M and 8060S), TrevorJS chat-template fix coverage by asf0 template (HF discussion #2 reporter says incomplete fix).
- **LOW confidence / gaps**: Abliterated 26B-A4B tool-call reliability (not benchmarked publicly), whether `litellm.async_pre_call_hook` cleanly supports awaiting an upstream call mid-hook (suspected: not idiomatic), whether Open WebUI re-exposes Pipes via OpenAI-compatible endpoints to external clients (docs silent — assume no).

---

## Integration Patterns Analysis

The integration surface for this system is single-host, intra-LXC, HTTP-only. The classical microservices patterns (Kafka, AMQP, gRPC, service mesh) don't apply — this is a tight Python-process orchestrator coordinating two local subprocess inference servers. The relevant integration concerns are: **OpenAI API contract fidelity**, **SSE streaming correctness**, **tool-call delta orchestration**, **multimodal content-block handling**, and **service-to-service handoff**.

### API Design Patterns

**OpenAI-compatible REST is the universal contract.** Every client in scope (Open WebUI, Continue.dev, Cursor, mobile, scripts) speaks `/v1/chat/completions` and `/v1/models`. There is no need to design a custom API — fidelity to the OpenAI surface IS the design goal.

| Endpoint | Method | Purpose | Implementation Notes |
|---|---|---|---|
| `/v1/chat/completions` | POST | Primary inference (text + multimodal + tools, streaming or not) | Accept full OpenAI spec; sniff content for routing |
| `/v1/models` | GET | Model discovery | Aggregate from both backends + advertise virtual aliases (`gemma4-auto`, `gemma4-26b-text`, `gemma4-e4b-vision`) |
| `/v1/embeddings` | POST | (Optional) Embeddings passthrough to E4B if needed | Defer until needed |
| `/health` | GET | Liveness for systemd / monitoring | Simple OK + upstream health roll-up |

_Source: [llama.cpp server README](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md), [Open WebUI OpenAI-compatible quick start](https://docs.openwebui.com/getting-started/quick-start/connect-a-provider/starting-with-openai-compatible/)._

**Pattern: Virtual model multiplexing.** A single endpoint exposes multiple model names; behavior differs based on the `model` field in the request body. This lets clients that only know "set the base URL and pick a model" get the routing behavior implicitly.

### Communication Protocols

| Protocol | Where | Transport | Notes |
|---|---|---|---|
| **HTTP/1.1** | All inter-service hops | TCP loopback (127.0.0.1) | All on `ct-ai-01`; no TLS needed internally |
| **HTTPS** | Tailscale exposure to external clients | Tailscale-encrypted tunnel | Matches existing phone-notifications policy; no public DNS |
| **Server-Sent Events (SSE)** | Streaming responses to client | `text/event-stream` over HTTP | Standard OpenAI delta protocol |
| **JSON** | All request/response bodies | UTF-8 | Pydantic models for validation |

**SSE format details to honor for OpenAI compatibility:**
- Each chunk: `data: {json}\n\n` followed by an empty line
- Stream terminator: `data: [DONE]\n\n`
- **Keep-alive comments** (`: keepalive\n\n`) every ~15s during long agent loops to defeat nginx/Tailscale idle timeouts (default 60s — push to ≥600s if any reverse proxy is in path)
- **No buffering**: nginx/Caddy must have `proxy_buffering off` for streaming endpoints

_Source: [sse-starlette docs](https://pypi.org/project/sse-starlette/), [OpenAI streaming guide](https://developers.openai.com/api/docs/guides/streaming-responses)._

### Data Formats & Content Blocks

The OpenAI message schema has structured content blocks. The proxy must inspect these to decide routing.

```json
{
  "messages": [
    {
      "role": "user",
      "content": [
        {"type": "text", "text": "What's in this image?"},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}},
        {"type": "input_audio", "input_audio": {"data": "...", "format": "wav"}}
      ]
    }
  ]
}
```

| Content type | Format | llama.cpp support | Routing decision |
|---|---|---|---|
| `text` | UTF-8 string | ✅ Always | Plain → 26B-A4B |
| `image_url` | base64 data URL OR remote HTTP URL | ✅ Stable (added [#12898](https://github.com/ggml-org/llama.cpp/pull/12898), still marked experimental) | Detected → describe via E4B → inject text → continue |
| `input_audio` | base64 data + format field | ⚠️ Highly experimental on llama.cpp; some 400 errors reported. Gemma 4 E4B audio specifically tracked in [llama.cpp #21334](https://github.com/ggml-org/llama.cpp/discussions/21334) | Detected → transcribe via E4B (mmproj-audio) → inject text → continue. **High-risk; needs end-to-end smoke test.** |
| `tool_calls` (assistant→user) | Streaming function calls | ✅ With `--jinja` | Intercepted in proxy, executed, response fed back |
| `tool` (user→assistant) | Tool result message | ✅ With `--jinja` | Standard role |

_Sources: [llama.cpp multimodal docs](https://github.com/ggml-org/llama.cpp/blob/master/docs/multimodal.md), [audio support discussion #13759](https://github.com/ggml-org/llama.cpp/discussions/13759), [Gemma 4 E4B audio question #21334](https://github.com/ggml-org/llama.cpp/discussions/21334)._

**Capability advertisement**: `/v1/models` should expose the multimodal capability per model so clients know what they can send. Per llama.cpp docs: "clients should check /models or /v1/models for the multimodal capability before making a multimodal request." For our virtual aliases, the proxy advertises:
- `gemma4-e4b-vision` → vision + audio
- `gemma4-26b-text` → text + tools
- `gemma4-auto` → vision + audio + tools (the orchestrated path)

### System Interoperability — Inter-Service Handoffs

```
┌──────────────────────────────────────────────────────────────────┐
│ Client (Open WebUI, Continue, Cursor, mobile, script)            │
│   POST https://ct-ai-01.tailnet/v1/chat/completions              │
│   Authorization: Bearer <virtual-key>                            │
└────────────────┬─────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ LiteLLM gateway :4000  (PINNED VERSION post-Mar-2026 CVE)       │
│   - Validate virtual key, enforce rate limit                    │
│   - Log request to local SQLite                                 │
│   - Forward to FastAPI router as a custom OpenAI upstream       │
└────────────────┬────────────────────────────────────────────────┘
                 │  same /v1/chat/completions shape
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ FastAPI router :8000                                            │
│   1. Parse messages, extract content blocks                     │
│   2. If model="gemma4-auto":                                    │
│      a. If image_url/input_audio present:                       │
│         - Call llama-server :8080 (E4B+mmproj) NON-streaming    │
│           with prompt: "describe this in detail"                │
│         - Replace block with text: "[Image: <description>]"     │
│      b. Forward rewritten request to llama-server :8081 (26B)   │
│         WITH stream=True; pipe SSE through to client            │
│      c. If 26B emits tool_calls (analyze_image / transcribe):   │
│         - Accumulate deltas (per index), execute against E4B,   │
│           append tool message, re-issue 26B call, resume stream │
│   3. If model="gemma4-26b-text" or "gemma4-e4b-vision":         │
│      - Direct passthrough to corresponding backend              │
└────────┬───────────────────────────────────────────┬────────────┘
         │                                           │
         ▼                                           ▼
  llama-server :8080                          llama-server :8081
  (E4B uncensored Q5_K_P + mmproj)            (26B-A4B UD-Q5_K_M
   text+image+audio capable)                   text-only, --jinja,
                                               asf0/gemma4_jinja template)
```

### Tool-Call Orchestration Pattern

Streaming tool calls is the trickiest part. OpenAI's contract delivers tool calls as **incremental deltas** in the streamed chunks; the proxy must reassemble before executing.

**Accumulation pattern** ([OpenAI cookbook](https://cookbook.openai.com/examples/how_to_stream_completions)):

1. For each `chat.completion.chunk`, look at `choices[0].delta.tool_calls[*]`.
2. Each delta has an `index` identifying *which* tool call it belongs to (a single response can contain multiple parallel calls).
3. Accumulate `tool_calls[index].function.name` (sent once) and `function.arguments` (sent in pieces, concatenate as a string).
4. When `finish_reason == "tool_calls"`, parse each accumulated `arguments` as JSON, execute against the appropriate upstream (`analyze_image` → E4B, `transcribe_audio` → E4B), then construct `tool` role messages with the results.
5. Re-issue the chat completion call to 26B with the original messages + assistant tool_calls + tool results, again streaming.
6. Pipe the new stream's deltas straight to the client.

**Status events for visibility during the inner loop**: emit synthetic `chat.completion.chunk` frames with `delta.content` containing user-visible status (e.g., `"\n_[describing image...]_\n"`). Vanilla OpenAI clients will render them as italic text. Cleaner than custom event channels that non-Vercel clients ignore.

_Sources: [OpenAI Chat Completions streaming events](https://developers.openai.com/api/reference/resources/chat/subresources/completions/streaming-events), [OpenAI function-calling guide](https://platform.openai.com/docs/guides/function-calling), [ahmad2b/openai-agents-streaming-api](https://github.com/ahmad2b/openai-agents-streaming-api)._

### Microservices Integration Patterns (Adapted)

These don't strictly apply — single-host, single-process orchestration — but the principles do:

| Pattern | Adapted Application |
|---|---|
| **API Gateway** | LiteLLM `:4000` is the gateway: virtual keys, rate limit, observability, model aggregation. |
| **Service Discovery** | Static via systemd `After=` ordering and config; backends always at known ports. No dynamic discovery needed. |
| **Circuit Breaker** | Lightweight: `httpx` timeouts (10s upstream), 3 retries on 5xx with exponential backoff. Open WebUI's own retry behavior makes server-side circuit breakers low-priority. |
| **Bulkhead** | One `httpx.AsyncClient` per upstream, with bounded concurrency (e.g., `limits=httpx.Limits(max_connections=4)`) so a runaway client can't starve the orchestrator. |

### Event-Driven Integration

Not applicable — this is request/response. No publish/subscribe, no event sourcing, no CQRS. Mentioned for completeness; explicitly out of scope.

### Integration Security Patterns

| Concern | Pattern | Implementation |
|---|---|---|
| **Network exposure** | Tailscale-only, no public DNS | Matches existing homelab policy from `project_phone_notifications_tailscale.md` |
| **Authentication** | Bearer tokens (LiteLLM virtual keys) | Per-client key issued from LiteLLM admin; rotate annually |
| **Authorization** | Implicit (single-tenant) | All keys have full access; no per-key model restrictions needed yet |
| **Inter-service** | None (loopback only) | LiteLLM ↔ FastAPI ↔ llama-server all on 127.0.0.1; LXC isolation is the boundary |
| **Secrets** | Vault-encrypted in Ansible | Matches Sparkle-CPS pattern; LiteLLM master key, virtual keys, any HF tokens |
| **Supply chain** | **Pin LiteLLM version + verify hash** | Critical due to March 2026 PyPI compromise — track [advisory](https://dev.to/stockyarddev/the-llm-proxy-landscape-in-2026-helicone-acquired-litellm-compromised-and-whats-next-3oon) for clean-version cutoff |
| **Input validation** | Pydantic models on every endpoint | Standard FastAPI; rejects malformed requests at the gateway |
| **Rate limiting** | LiteLLM's per-key budget | Default to liberal for self-use, tighter if a third-party app is added later |

### Confidence & Gaps for Integration Layer

- **HIGH confidence**: OpenAI API contract, SSE pattern, tool-call accumulation, image_url handling, LiteLLM gateway role.
- **MEDIUM confidence**: Status-event injection during agent loop (works but client UX varies), `/v1/models` capability advertisement format (llama.cpp's exact field names not fully verified — to verify in implementation).
- **LOW confidence / gaps**:
  - **Audio support is fragile.** Gemma 4 E4B audio via llama.cpp's `input_audio` content block is very new and reports 400 errors in some cases. Plan to ship without audio in v1, add as a follow-up after smoke-testing E4B audio in isolation.
  - **TrevorJS chat-template fix coverage** for tool calls specifically — to validate during implementation.
  - **LiteLLM ↔ FastAPI handoff for streaming tool calls** — verify LiteLLM doesn't buffer or rewrite tool_call deltas; if it does, may need to bypass LiteLLM for the `gemma4-auto` model and have FastAPI handle auth itself for that path.

---

## Architectural Patterns and Design

The system is best characterized as a **single-host, multi-process inference orchestrator** implementing a **hybrid preprocessor-plus-agent-loop pattern** in front of two specialized model backends. The architectural posture is deliberately conservative: match Anthropic's published guidance to "start with the simplest architecture that could plausibly work" rather than reaching for multi-agent frameworks. _Source: [Building Effective AI Agents — Anthropic](https://resources.anthropic.com/building-effective-ai-agents)._

### System Architecture Patterns

**Chosen pattern: Hybrid Preprocessor + Single-Threaded Master Loop (Cascade Routing variant).**

| Pattern | Used? | Rationale |
|---|---|---|
| **Preprocessor (deterministic fan-out)** | ✅ | When `image_url` or `input_audio` is present, the proxy *always* dispatches to E4B first to convert the modality to text. This is deterministic, predictable, and gives 80% of the value with zero LLM-routing variance. |
| **Single-threaded master loop (Anthropic style)** | ✅ | Within a single `chat/completions` request, the proxy runs ONE flat conversation history. No threaded conversations, no competing agent personas. Loop terminates when 26B emits a `finish_reason != "tool_calls"`. _Source: [Anthropic Claude Code architecture](https://www.zenml.io/llmops-database/claude-code-agent-architecture-single-threaded-master-loop-for-autonomous-coding)._ |
| **Cascade routing (small → large)** | ✅ (modality cascade only) | E4B handles vision/audio "perception" → 26B handles "cognition". Not a quality cascade (not "try E4B first, escalate to 26B if low confidence") — modality-driven, not confidence-driven, which avoids the calibration problem. |
| **LLM-as-router** | ❌ | Rejected: introduces a third LLM call just to pick a model. Deterministic content sniffing (fast, free, predictable) is sufficient since the routing rules are simple. _Counter-cited: [LLMRouter](https://github.com/ulab-uiuc/LLMRouter), [RouteLLM](https://github.com/lm-sys/RouteLLM) — relevant for cost-driven cloud routing, not local single-user homelab._ |
| **Multi-agent orchestration** | ❌ | Anthropic explicitly advises against this for predictable workflows. _Source: [Anthropic agent patterns](https://aimultiple.com/building-ai-agents)._ Saves complexity, debuggability cost, and latency. |
| **Speculative decoding** | ❌ | Broken on MoE targets in current llama.cpp; mmproj/draft incompatibility (see Tech Stack section). |
| **Ensemble / mixture-of-agents** | ❌ | Doubles inference cost for marginal local-single-user benefit. |

**Why this pattern beats pure LLM-as-router for this use case:**
- **Determinism**: Routing rule is "is there a non-text content block? → preprocess via E4B." No LLM-judgment variance to debug.
- **Latency**: One round-trip overhead added only for multimodal requests (~1-2s). Pure-text requests go straight to 26B with zero proxy overhead beyond JSON parse + forward.
- **Cost**: Zero added inference for pure-text requests — they ARE the majority for most workflows.
- **Tool-call agency layered on top**: 26B can re-query E4B with specific questions (`analyze_image(image_id, "what's the y-axis label?")`) when the initial generic description isn't enough — this preserves the "cascade routing" research benefit without the calibration headache.

_Sources: [arXiv: Dynamic Model Routing and Cascading Survey 2026](https://arxiv.org/html/2603.04445v1), [arXiv: Unified Routing and Cascading 2410](https://arxiv.org/html/2410.10347v1)._

### Design Principles and Best Practices

**Hexagonal / Ports-and-Adapters layout for the FastAPI router.**

```
gemma_hybrid_proxy/
├── domain/                    # Pure orchestration logic, no I/O
│   ├── orchestrator.py        # The master loop (frame: messages → frame → next action)
│   ├── content_inspector.py   # Detect image_url / input_audio in OAI messages
│   ├── tool_definitions.py    # analyze_image, transcribe_audio JSON schemas
│   └── delta_accumulator.py   # OpenAI tool_call streaming reassembly
├── adapters/                  # I/O boundary
│   ├── llama_server_client.py # httpx wrapper for upstream calls
│   └── openai_models.py       # Pydantic request/response models
├── api/                       # FastAPI surface
│   ├── chat_completions.py    # POST /v1/chat/completions handler
│   ├── models.py              # GET /v1/models virtual alias enumeration
│   └── health.py              # GET /health upstream rollup
├── config.py                  # Env-driven settings (E4B_URL, MOE_URL, etc.)
└── main.py                    # FastAPI app wiring + uvicorn entry
```

**SOLID applied (concretely, not as buzzwords):**
- **Single Responsibility**: `orchestrator.py` knows how to drive the loop; `content_inspector.py` knows how to read messages; `delta_accumulator.py` knows how to reassemble tool_calls. Each ≤150 lines.
- **Open/Closed**: New modalities (e.g., video when llama.cpp adds it) require a new content-inspector branch + a new tool definition — orchestrator doesn't change.
- **Dependency Inversion**: `orchestrator.py` depends on an interface, not concrete `httpx`. Adapters can be mocked in tests without touching the network.

**Behaviors enforced as code, not docs:**
- Pydantic-validated request/response (no untyped dicts crossing boundaries).
- Async everywhere (`async def` + `httpx.AsyncClient`) — no sync blocking inside the event loop.
- All upstream calls have explicit timeouts; no defaults.
- Structured logging with request ID propagated end-to-end.

_Source: [Anthropic engineering: managed agents](https://www.anthropic.com/engineering/managed-agents)._

### Scalability and Performance Patterns

**Vertical-only scaling.** Single LXC, single iGPU, single user → no horizontal scaling concerns. The patterns that DO matter:

| Concern | Pattern | Implementation |
|---|---|---|
| **Cold start** | Keep both `llama-server` instances always-warm | systemd `Restart=always`; models stay loaded in VRAM |
| **VRAM contention** | Static allocation, no swapping | E4B + 26B both resident; total ~29 GB of 32 GB VRAM. Validated in Tech Stack section. |
| **Concurrent requests** | Bounded queue at proxy | `httpx.Limits(max_connections=4)` per upstream; reject with 429 when overloaded (single-user → unlikely to hit) |
| **Latency budget** | Documented per stage | Pure text: ≤300ms first token. Multimodal: ≤2.5s first token (E4B descr ~1.5s + 26B prefill). Tool-call iteration: +1.5s per loop. |
| **Streaming** | Pass-through, no buffering | sse-starlette; never await full upstream response before forwarding |
| **Token counting / context windows** | Honor limits at proxy | If summed messages exceed 26B's 256K, fail-fast with clear error rather than silently truncate |

**Caching:** explicitly out of scope for v1. Local single-user, prompts vary, KV-cache reuse already happens inside `llama-server`. Adding a proxy-layer prompt cache adds invalidation complexity for marginal gain.

### Integration and Communication Patterns (Architecture-Level)

Already detailed in §Integration Patterns. At the architectural layer:

- **Stateless proxy**: No session state, no DB. Client owns full conversation history (per OpenAI contract). Restarting `gemma-hybrid-proxy.service` causes zero data loss.
- **Service composition order** (systemd `After=` chain):
  ```
  llama-server-e4b.service       (existing)
       ↓ After=
  llama-server-26b.service       (new)
       ↓ After=
  gemma-hybrid-proxy.service     (new)
       ↓ After=
  litellm-gateway.service        (new)
  ```
- **Backwards compatibility**: Existing `llama-server` on `:8080` keeps its current API surface and Open WebUI registration during cutover. Open WebUI gets re-pointed to LiteLLM `:4000` last.

### Security Architecture Patterns

- **Network boundary**: LXC firewall + Tailscale tailnet. No public DNS exposure. Matches existing phone-notifications policy in `project_phone_notifications_tailscale.md`.
- **Defense in depth**: LiteLLM virtual key (auth) → FastAPI Pydantic validation (input contract) → llama-server only listens on `127.0.0.1` (network isolation) → systemd `User=`/`NoNewPrivileges=` (process isolation).
- **Supply-chain hygiene**: All Python deps pinned in `requirements.txt` with hashes. **LiteLLM specifically pinned** to a known-clean post-March-2026 version with hash verification. Renovate/Dependabot for tracking, manual review before bumps.
- **Secret management**: All secrets in Ansible Vault (matches Sparkle-CPS pattern). No secrets in env files on disk.
- **Reasoning_content leakage** (model-level security concern): TrevorJS chat-template fix prevents internal CoT from leaking via OpenAI surface — important if external clients ever consume the API.

_Source: [Hybrid Cloud-Local LLM Architecture Guide 2026](https://www.sitepoint.com/hybrid-cloudlocal-llm-the-complete-architecture-guide-2026/)._

### Data Architecture Patterns

**Stateless. No persistence beyond logs.**

| Data class | Lifetime | Store |
|---|---|---|
| Chat history | Per-request, owned by client | In OpenAI message array; not persisted by proxy |
| Model weights | Permanent | `/opt/ollama-models/` (existing) and `/opt/llama-models/` (new) on bulk storage |
| KV cache | Per-process, in VRAM | Managed by `llama-server` |
| Request logs | Configurable retention (e.g., 30 days) | LiteLLM SQLite at `/var/lib/litellm/logs.db` |
| Metrics | Real-time + 90 days | Prometheus + Grafana (existing storage-monitoring pattern) |
| Secrets | Permanent | Ansible Vault |

### Deployment and Operations Architecture

**Operational model: declarative-first, immutable-bias, observable.**

| Aspect | Choice |
|---|---|
| **Provisioning** | Terraform (existing pattern for `ct-ai-01` LXC) |
| **Configuration** | Ansible role `gemma_hybrid` (new), composed with existing `llama_cpp` and `open_webui` roles |
| **Service supervision** | systemd, with `Restart=always`, `RestartSec=5s`, `WatchdogSec=30s` for the proxy |
| **Health checks** | `/health` endpoint; systemd health checks; LiteLLM exposes its own |
| **Metrics** | LiteLLM Prometheus exporter scraped by existing Prometheus on monitoring stack |
| **Logs** | journald → forwarded to existing log aggregation |
| **Rollback** | Git-tracked Ansible role; `ansible-playbook --tags gemma_hybrid` re-runs idempotent |
| **Backup** | Model weights are immutable artifacts — no backup needed beyond having the HF source. LiteLLM SQLite included in existing snapshot policy |

**HA posture**: not applicable for v1. Single-node, single-iGPU, single-user. Per `project_project_container_ha_policy.md`, ct-ai-01 should have `--state` matching current run-state (running → fails over, stopped → stays stopped). The hybrid proxy adds no new HA requirements.

### Architectural Decision Records (ADRs) — Implicit, To Be Captured

For traceability when implemented, the following decisions warrant ADRs:

1. **ADR: Use Vulkan, not ROCm, for Gemma 4 26B-A4B on Strix iGPU.** Driver bug [#21416](https://github.com/ggml-org/llama.cpp/issues/21416).
2. **ADR (UPDATED 2026-04-25): Use TrevorJS Q4_K_M for 26B-A4B (uncensored).** User decision overrides initial Unsloth recommendation. Trade-off accepted: lower quant tier + chat-template fix required + tool-call reliability risk in exchange for uncensored text reasoning. Sprint 1 must include early tool-call accuracy measurement; if <90% schema-valid, fallback ADR-2b activates: run Unsloth UD-Q5_K_M as a secondary reasoner on alias `gemma4-26b-text-strict`, reserve TrevorJS for `gemma4-26b-text` and the agentic `gemma4-auto` only when uncensored output is needed.
3. **ADR: Hybrid preprocessor + tool-call agent loop.** Not pure preprocessor, not pure agent loop, not LLM-router.
4. **ADR: LiteLLM as outer gateway, custom FastAPI as inner router.** Build vs buy split.
5. **ADR: Defer audio support to v2.** llama.cpp `input_audio` too unstable for production v1.
6. **ADR: Stateless proxy, client-owned conversation history.** OpenAI contract preservation.

### Confidence & Gaps for Architectural Layer

- **HIGH confidence**: Hybrid preprocessor + master loop pattern (matches Anthropic's published guidance + 2026 cascade-routing research); hexagonal layout for FastAPI codebase; vertical-only scaling posture; stateless proxy.
- **MEDIUM confidence**: Latency budget numbers (estimated, not measured on actual hardware); tool-call iteration bounds (no published data on how many iterations a Gemma 4 26B-A4B agent loop typically needs).
- **LOW confidence / gaps**: Whether the abliterated TrevorJS variant degrades tool-call adherence enough to make the agent loop unreliable (unknown until measured); long-term LiteLLM project health post-March-2026 incident (monitor advisory).

---

## Implementation Approaches and Technology Adoption

This section converts the architectural decisions into a concrete, executable plan tailored to the existing homelab patterns (Terraform/Ansible/Vault/systemd) and the live state of `ct-ai-01` (existing `llama-server` Ansible role at `homelab-infra/ansible/roles/llama-server`, Vulkan-built, E4B+mmproj running on `:8080`, Open WebUI on `:3000`).

### Technology Adoption Strategies

**Strategy: Incremental, additive, reversible.** No big-bang rewrites; each phase is independently shippable and rollback-friendly.

| Phase | Action | Rollback | Independent value? |
|---|---|---|---|
| **0 — Baseline** | Current state: E4B+mmproj on `:8080`, Open WebUI on `:3000`, Ollama removed | (already done) | Active |
| **1 — Add 26B backend** | New systemd unit `llama-server-26b.service` on `:8081`, register in Open WebUI as second model | Disable+remove unit; remove from Open WebUI | ✅ Manual model picker UX immediately usable |
| **2 — Smoke-test 26B** | Manual chat tests (text, code, tool-call), measure tok/s, validate chat template fix | (no state change) | ✅ Validates assumptions before building proxy |
| **3 — Build proxy (passthrough mode)** | FastAPI app exposing `gemma4-26b-text` and `gemma4-e4b-vision` as virtual models; pure forwarding | Repoint Open WebUI back to direct backends | ✅ Single endpoint working |
| **4 — Add multimodal preprocessing** | Implement content-sniff → E4B-describe → 26B-reason flow as `gemma4-auto` model | Unregister `gemma4-auto`; passthrough still works | ✅ Hybrid behavior available |
| **5 — Add tool-call agent loop** | Register `analyze_image` tool; implement delta accumulation + execute-resume | Disable tool registration; falls back to plain preprocessing | ✅ Deeper vision queries possible |
| **6 — Add LiteLLM gateway** | Outer layer: virtual keys, rate limit, observability, Prometheus | Bypass LiteLLM, expose proxy directly | ✅ Multi-app auth + metrics |
| **7 (deferred) — Audio support** | Add `transcribe_audio` tool + `input_audio` content handling | Strip audio handling, fail-fast on audio messages | Earned after llama.cpp audio stabilizes |

_Each phase is one PR/commit, each is reversible, none are blocked by future phases._

### Development Workflows and Tooling

**Repo layout** (within existing `homelab-infra/`):

```
homelab-infra/
├── ansible/
│   ├── roles/
│   │   ├── llama-server/                  # EXISTING — keep as-is for E4B
│   │   ├── llama-server-26b/              # NEW — copies pattern from llama-server
│   │   ├── gemma-hybrid-proxy/            # NEW — deploys FastAPI app
│   │   └── litellm-gateway/               # NEW — deploys LiteLLM proxy
│   └── playbooks/
│       └── ct-ai-01.yml                   # UPDATE — add new role invocations
└── ...

homelab-apps/                              # NEW or existing — code repo
└── gemma-hybrid-proxy/
    ├── src/gemma_hybrid_proxy/            # Hexagonal layout per Step 4
    │   ├── domain/
    │   ├── adapters/
    │   ├── api/
    │   ├── config.py
    │   └── main.py
    ├── tests/
    │   ├── unit/                          # No I/O; mock adapters
    │   └── integration/                   # Hits live llama-server in dev
    ├── pyproject.toml                     # uv / pip-tools
    ├── requirements.txt                   # PINNED + hashes
    └── Dockerfile                         # OR systemd-direct via venv
```

**Tooling stack:**

| Concern | Tool | Why |
|---|---|---|
| Python deps | **`uv`** + `requirements.txt` with hashes | Fast, reproducible, supply-chain-safe |
| Testing | `pytest` + `pytest-asyncio` + `httpx.MockTransport` | Standard for FastAPI |
| Type checking | `mypy` (strict on `domain/`) | Catches contract drift in tool-call schemas |
| Linting/formatting | `ruff` | One tool, fast, replaces `black + flake8 + isort` |
| Pre-commit | `pre-commit` hooks running `ruff` + `mypy` | Existing homelab pattern |
| Local dev | `uvicorn --reload` against `ct-dev-test` (192.168.50.152) | Per `feedback_test_container.md` — test on ct-dev-test before ct-ai-01 |
| CI | (TBD — match existing homelab convention if present; otherwise GitHub Actions) | Run `ruff`+`mypy`+`pytest` on every push |
| Docs | Inline docstrings + a single `docs/architecture.md` referencing this research doc | Avoid doc rot |

### Build & Deployment Specifics

**1. Build llama.cpp (already done; verify Vulkan-enabled):**

```bash
ssh pve3 "pct exec 160 -- bash -c '/opt/llama.cpp/build/bin/llama-server --version 2>&1 | head -5'"
# Expect: ggml backends include Vulkan
```

If not Vulkan: rebuild the existing `llama-server` Ansible role (already has `llama_cpp_vulkan: true` in defaults).

**2. Download Unsloth UD-Q5_K_M GGUF for 26B-A4B:**

```bash
# Inside ct-ai-01:
huggingface-cli download \
  unsloth/gemma-4-26B-A4B-it-GGUF \
  gemma-4-26B-A4B-it-UD-Q5_K_M.gguf \
  --local-dir /opt/llama-models/ \
  --local-dir-use-symlinks False

# Custom chat template (asf0 fix):
curl -fsSL https://raw.githubusercontent.com/asf0/gemma4_jinja/main/gemma4.jinja \
  -o /opt/llama-models/gemma4-asf0.jinja
```

_Action: store HF token in Ansible Vault if model is gated; Unsloth's GGUFs are typically public._

**3. New systemd unit (`llama-server-26b.service.j2`) — adapted from existing template:**

```ini
[Unit]
Description=llama.cpp Server (Gemma 4 26B-A4B Unsloth UD-Q5_K_M, text-only)
After=network.target llama-server.service

[Service]
Type=simple
ExecStart={{ llama_cpp_dir }}/build/bin/llama-server \
    -m {{ llama_server_26b_models_dir }}/{{ llama_server_26b_model_file }} \
    --chat-template-file {{ llama_server_26b_models_dir }}/gemma4-asf0.jinja \
    --host {{ llama_server_26b_host }} \
    --port {{ llama_server_26b_port }} \
    -ngl {{ llama_server_26b_gpu_layers }} \
    -b {{ llama_server_26b_batch_size }} \
    --jinja \
    -c {{ llama_server_26b_context_size }} \
    --temp 1.0 --top-p 0.95 --top-k 64
Environment=LD_LIBRARY_PATH={{ llama_cpp_dir }}/build/bin
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**Defaults** (`roles/llama-server-26b/defaults/main.yml`):

```yaml
llama_server_26b_host: 127.0.0.1                    # internal-only; proxy accesses via loopback
llama_server_26b_port: 8081
llama_server_26b_gpu_layers: 99
llama_server_26b_batch_size: 256                    # Vulkan stability tip per llm-tracker
llama_server_26b_context_size: 32768                # Unsloth recommendation
llama_server_26b_models_dir: /opt/llama-models
llama_server_26b_model_file: gemma-4-26B-A4B-it-UD-Q5_K_M.gguf
llama_server_26b_hf_repo: unsloth/gemma-4-26B-A4B-it-GGUF
```

**Action: re-bind existing `llama-server` to `127.0.0.1` too** (currently `0.0.0.0`) once the proxy is in place — defense in depth.

**4. `gemma-hybrid-proxy.service.j2`:**

```ini
[Unit]
Description=Gemma Hybrid Proxy (FastAPI orchestrator: E4B vision + 26B reasoning)
After=network.target llama-server.service llama-server-26b.service
Requires=llama-server.service llama-server-26b.service

[Service]
Type=simple
User={{ proxy_user }}
WorkingDirectory={{ proxy_dir }}
EnvironmentFile={{ proxy_dir }}/.env
ExecStart={{ proxy_dir }}/.venv/bin/uvicorn \
    gemma_hybrid_proxy.main:app \
    --host 127.0.0.1 \
    --port 8000 \
    --workers 1 \
    --no-access-log
Restart=on-failure
RestartSec=5
WatchdogSec=30
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths={{ proxy_dir }}/logs

[Install]
WantedBy=multi-user.target
```

**5. `litellm-gateway.service.j2`** (similar pattern; LiteLLM ships as a Python package; pin version):

```yaml
litellm_version: "1.57.0"                # PIN — verify clean post-March-2026 advisory
litellm_master_key: "{{ vault_litellm_master_key }}"      # Ansible Vault
litellm_db_url: "sqlite:///var/lib/litellm/logs.db"
litellm_port: 4000
```

LiteLLM `config.yaml` defines the upstream as our FastAPI proxy:

```yaml
model_list:
  - model_name: gemma4-auto
    litellm_params:
      model: openai/gemma4-auto
      api_base: http://127.0.0.1:8000/v1
      api_key: "noop"
  - model_name: gemma4-26b-text
    litellm_params:
      model: openai/gemma4-26b-text
      api_base: http://127.0.0.1:8000/v1
      api_key: "noop"
  - model_name: gemma4-e4b-vision
    litellm_params:
      model: openai/gemma4-e4b-vision
      api_base: http://127.0.0.1:8000/v1
      api_key: "noop"
general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY
  database_url: os.environ/DATABASE_URL
  store_model_in_db: false
```

### Testing and Quality Assurance

**Test pyramid for the proxy:**

| Layer | Tool | Examples | Run when |
|---|---|---|---|
| **Unit** | `pytest` w/ mocked adapters | `content_inspector` extracts image_urls; `delta_accumulator` reassembles streamed tool_calls; `orchestrator` master loop terminates correctly | Every commit, pre-commit |
| **Integration (local)** | `pytest` against `httpx.MockTransport` simulating llama-server | Full `chat/completions` flow with mocked upstream responses | Every commit, CI |
| **Integration (live, ct-dev-test)** | `pytest` against real llama-server in `ct-dev-test` | Streaming, tool-call iteration, malformed input rejection | Pre-deploy to ct-ai-01 |
| **Smoke (ct-ai-01)** | Manual `curl` + Open WebUI | Text round-trip, image round-trip, tool-call round-trip | Post-deploy |
| **Soak** | `k6` or `locust` for 1h continuous | Memory stability, no leaks, no streaming hangs | Weekly via cron / ScheduleWakeup |
| **Browser E2E** | Playwright MCP | Open WebUI vision chat, model picker, streaming visibility | Per `feedback_browser_validation.md` — required before claiming feature done |

**Critical test cases (acceptance criteria):**

1. ✅ POST `/v1/chat/completions` with `model="gemma4-26b-text"` and a text-only message returns a streamed response within 300ms first-token.
2. ✅ POST with `model="gemma4-e4b-vision"` and an `image_url` content block returns a streamed description.
3. ✅ POST with `model="gemma4-auto"` and an `image_url` triggers E4B-describe → 26B-reason in series; final answer references the image content.
4. ✅ POST with `model="gemma4-auto"`, `image_url`, AND tool definitions including `analyze_image`: 26B emits tool_calls, proxy executes against E4B, resumes 26B, final answer answers the specific question.
5. ✅ Status events visible during the multimodal loop ("_describing image..._").
6. ✅ Concurrent requests don't corrupt streams (run 5 parallel `curl`s).
7. ✅ Upstream timeout returns OAI-shaped error to client (not raw stack trace).
8. ✅ Open WebUI's model picker shows `gemma4-auto`, `gemma4-26b-text`, `gemma4-e4b-vision` after restart.
9. ✅ LiteLLM rejects requests with invalid bearer tokens; Prometheus scrape returns metrics.
10. ✅ `systemctl restart gemma-hybrid-proxy` causes <5s downtime; in-flight requests complete or fail cleanly.

### Deployment and Operations Practices

**Deployment flow** (matches existing homelab pattern):

```
1. PR merged → Ansible-Lint passes
2. Run on ct-dev-test first:
   ansible-playbook -i inventory ct-dev-test.yml --tags gemma_hybrid
3. Smoke + integration tests against ct-dev-test
4. Run on ct-ai-01:
   ansible-playbook -i inventory ct-ai-01.yml --tags gemma_hybrid
5. Validate via Open WebUI + Playwright
6. Mark deploy successful in ops log
```

**Observability:**

| Signal | Where | Alerting |
|---|---|---|
| Service health | `systemd` + `/health` endpoint | `Restart=on-failure`; alert if restart count >3 in 1h |
| Latency | LiteLLM Prometheus exporter | Alert if p95 first-token > 5s on text |
| Error rate | LiteLLM logs + Prometheus | Alert if 5xx rate > 5% over 5m |
| GPU usage | Existing storage-monitoring + `radeontop` exporter | Dashboard, no alerts (shared resource) |
| Disk usage | Existing storage-monitoring | Alert if `/opt/llama-models` >80% |
| Token throughput | LiteLLM logs aggregated | Weekly report, no alerts |

**Logging:**

- Structured JSON logs from FastAPI (`structlog`).
- Request ID generated at LiteLLM, propagated via `X-Request-ID` header through all hops.
- One log line per upstream call with: timing, model, content-block-types, status.
- 30-day retention via journald → existing log aggregation.

**Disaster recovery:**

- Model weights are immutable artifacts. If lost: re-download from HF (≈30 min for 21 GB Q5_K_M on a typical home connection).
- LiteLLM SQLite snapshotted by existing backup policy.
- Code in git; Ansible idempotent; full rebuild from clean LXC: ~1 hour incl. model download.

### Team Organization and Skills (Adapted)

Single-operator project. Skills checklist:

| Area | Currently strong | Gap to fill |
|---|---|---|
| Proxmox / LXC ops | ✅ | — |
| Terraform / Ansible | ✅ | — |
| llama.cpp build | ✅ (existing role) | Verify Vulkan-only build still passes after llama.cpp upgrade |
| systemd | ✅ | — |
| Python / FastAPI | Likely yes | If new: ~2 hours to ramp on async + sse-starlette (use reference templates) |
| OpenAI streaming protocol nuances | Maybe | Worth a 1-hour read of the OpenAI Cookbook + a tool-call cookbook example before coding |
| LiteLLM operation | New | ~1 hour from docs |

**Estimated effort:** 12–18 hours of focused work end-to-end (excluding the audio v2 phase). Phases 1–2 (~2h), Phase 3 (~3h), Phase 4 (~3h), Phase 5 (~4h), Phase 6 (~2h), buffer 2-4h.

### Cost Optimization and Resource Management

For a homelab, "cost" is electricity + hardware utilization. The architecture is already cost-optimal in this dimension:

- **No cloud spend.**
- **iGPU at full utilization only during active inference**; idle cost negligible.
- **Both models resident in VRAM** — no swap-in cost. Trade-off: ~29 GB VRAM permanently allocated; acceptable since this is a dedicated AI host.
- **Power**: ct-ai-01 idle ≈ ~25W; under inference ≈ ~80-100W (ballpark for Strix iGPU). Not a budget concern.

### Risk Assessment and Mitigation

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | TrevorJS abliterated chat-template fix incomplete (per HF discussion #2) — **PRIMARY RISK after user choice** | High | High (tool calls broken) | **Sprint 1 measurement gate**: 50-prompt tool-call accuracy test using asf0/gemma4_jinja template; if <90% schema-valid, deploy Unsloth UD-Q5_K_M as secondary reasoner per ADR-2b and route tool-loop traffic away from TrevorJS. Document outcome in ADR. |
| R2 | LiteLLM PyPI compromise repeats | Medium | High (supply chain) | Pin version + hash; subscribe to security advisories; review release notes before bumps. |
| R3 | llama.cpp upgrade breaks Vulkan build on Strix iGPU | Medium | Medium | Pin `llama_cpp_version` to a known-good tag; test upgrades on `ct-dev-test` first. |
| R4 | Open WebUI tool-call streaming bug ([#23066](https://github.com/open-webui/open-webui/issues/23066)) hits us | Medium | Medium | Smoke-test in OWUI specifically; if bug present, route OWUI through `gemma4-26b-text` only and reserve `gemma4-auto` for non-OWUI clients until fixed. |
| R5 | mmproj `input_audio` causes 400s | High (already known) | Low (audio deferred) | Audio explicitly deferred to v2; document fail-fast behavior on audio inputs in v1. |
| R6 | VRAM exhaustion under sustained load | Low | High (model crash) | Validated math leaves ~3 GB headroom + 32 GB GTT; bounded concurrency at proxy; alert on GPU memory %. |
| R7 | Tailscale outage breaks remote access | Low | Medium (locally still works) | Local LAN access remains functional; Tailscale is the secure remote layer, not the only path. |
| R8 | LXC reboot loses warm KV cache | Certain (every restart) | Low | Inherent; first request after restart has higher latency. Acceptable. |
| R9 | Reference FastAPI template introduces a vulnerability when copied | Medium | Medium | Don't copy verbatim — read the template, adapt patterns into our hexagonal layout, audit for security (no `eval`, no shell-out, no untrusted deserialization). |
| R10 | Future Gemma 5 release supersedes Gemma 4 quickly | Medium | Low | Architecture is model-agnostic; swapping the model file in defaults + re-deploying the Ansible role handles it. |

### Implementation Roadmap (Concrete)

**Sprint 1 (week 1) — Foundation**
- [ ] T1.1: Verify llama.cpp on ct-ai-01 is Vulkan-built (re-run existing role if needed)
- [ ] T1.2: Download Unsloth UD-Q5_K_M to `/opt/llama-models/` (~21 GB)
- [ ] T1.3: Download asf0/gemma4_jinja chat template
- [ ] T1.4: Create Ansible role `llama-server-26b` (copy + adapt existing role)
- [ ] T1.5: Deploy to ct-dev-test (192.168.50.152), smoke-test
- [ ] T1.6: Deploy to ct-ai-01, register in Open WebUI as a manual second model
- [ ] T1.7: Manual quality / tok/s tests on real prompts
- [ ] **Exit gate**: 26B-A4B usable in Open WebUI alongside E4B; tok/s within 18-30 range; no chat-template leakage

**Sprint 2 (week 2) — Proxy passthrough + multimodal preprocessing**
- [ ] T2.1: Scaffold `gemma-hybrid-proxy` repo with hexagonal layout
- [ ] T2.2: Implement `/v1/models` advertising 3 virtual aliases
- [ ] T2.3: Implement `gemma4-26b-text` and `gemma4-e4b-vision` passthrough
- [ ] T2.4: Implement SSE streaming forwarding
- [ ] T2.5: Implement `gemma4-auto` with E4B preprocessing → 26B forwarding
- [ ] T2.6: Status events during preprocessing
- [ ] T2.7: Ansible role `gemma-hybrid-proxy`
- [ ] T2.8: Deploy to ct-dev-test, run integration tests
- [ ] T2.9: Deploy to ct-ai-01; repoint Open WebUI to new endpoint
- [ ] **Exit gate**: Open WebUI shows 3 models; image upload via `gemma4-auto` produces 26B-reasoned answer with E4B-derived description

**Sprint 3 (week 3) — Tool-call agent loop + LiteLLM gateway**
- [ ] T3.1: Define `analyze_image` tool schema
- [ ] T3.2: Implement `delta_accumulator` for streaming tool_calls
- [ ] T3.3: Implement orchestrator loop (intercept → execute → resume → stream)
- [ ] T3.4: Test with synthetic prompts that should trigger tool calls
- [ ] T3.5: Deploy LiteLLM gateway with virtual key for self
- [ ] T3.6: Configure Open WebUI to use LiteLLM URL
- [ ] T3.7: Configure Continue.dev / Cursor / phone with virtual key
- [ ] T3.8: Prometheus scrape config + Grafana dashboard for LiteLLM metrics
- [ ] T3.9: Soak test 1 hour
- [ ] **Exit gate**: All 10 acceptance criteria pass; multi-app access works; metrics visible

**Sprint 4 (deferred) — Audio support + hardening**
- Triggered when: llama.cpp `input_audio` lands stable for Gemma 4 E4B (track [#21334](https://github.com/ggml-org/llama.cpp/discussions/21334)) OR a concrete need arises.
- Add `transcribe_audio` tool, content-inspector branch, smoke tests.

### Technology Stack Recommendations (Final)

| Layer | Choice | Version Pin |
|---|---|---|
| Inference engine | llama.cpp (existing) | tag `b5XXX` (current good) |
| Inference backend | Vulkan/RADV | n/a |
| Multimodal model | Gemma 4 E4B Uncensored (HauhauCS) Q5_K_P + mmproj | (existing) |
| Reasoner model | **TrevorJS gemma-4-26B-A4B-it-uncensored Q4_K_M** (16.8 GB) — user choice for uncensored output | latest revision |
| Fallback reasoner (conditional) | Unsloth gemma-4-26B-A4B-it UD-Q5_K_M | latest revision; deployed if Sprint 1 tool-call test fails |
| Chat template | asf0/gemma4_jinja (mandatory for TrevorJS) | git SHA pinned |
| Proxy framework | FastAPI + uvicorn + sse-starlette + httpx + pydantic v2 | All pinned with hashes |
| Gateway | LiteLLM | **post-2026-03 audited version, pinned + hash** |
| Process supervisor | systemd | host default |
| Configuration mgmt | Ansible (existing) | (existing) |
| Secrets | Ansible Vault (existing) | (existing) |
| Observability | Prometheus + Grafana (existing) | (existing) |
| UI | Open WebUI Docker (existing) | (existing) |

### Skill Development Requirements

- **Pre-build**: spend ~1 hour reading [OpenAI Cookbook on streaming completions](https://cookbook.openai.com/examples/how_to_stream_completions) and one of the FastAPI proxy reference templates ([talesmousinho/fastapi-openai-sse-stream](https://github.com/talesmousinho/fastapi-openai-sse-stream) is shortest).
- **Pre-build**: read the [Multimodal Reasoning Pipe V1](https://openwebui.com/f/snicky666/multimodal_reasoning_pipe_v1) source as a logic reference for the describe-then-reason flow.
- **During build**: keep [llama.cpp server README](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md) and [Unsloth Gemma 4 docs](https://unsloth.ai/docs/models/gemma-4) open for flag reference.

### Success Metrics and KPIs

**Functional:**
- All 10 acceptance criteria pass (binary)
- `gemma4-auto` correctly handles 95%+ of image-bearing prompts without manual fallback to direct backends (sample: 20 representative prompts, manually graded)

**Performance:**
- Pure-text first-token latency: ≤300ms (measured)
- Multimodal first-token latency: ≤2.5s (measured)
- 26B-A4B sustained decode: ≥18 tok/s (measured)
- E4B describe + 26B answer end-to-end: ≤30s for "describe and reason about this image" prompts

**Reliability:**
- Service uptime: ≥99% over rolling 30 days (excluding planned maintenance)
- Tool-call accuracy on Unsloth 26B-A4B: ≥90% schema-valid tool calls (measured on 50 synthetic prompts)
- Zero stream-corruption events under concurrent load

**Operational:**
- Mean time to detect failed deploy: ≤2 minutes (via systemd + alert)
- Mean time to rollback: ≤5 minutes (via Ansible re-deploy of prior tag)
- Zero secret leaks in logs (verify via PII detection scan)

### Confidence & Gaps for Implementation Layer

- **HIGH confidence**: Phasing approach, Ansible role pattern (matches existing), systemd unit shape, test plan, risk register.
- **MEDIUM confidence**: Effort estimate (12-18h is plausible but personal velocity varies); LiteLLM exact integration shape (config syntax verified, runtime behavior under streaming tool_calls TBD).
- **LOW confidence / gaps**: Specific tok/s numbers on actual 880M hardware (extrapolated; will measure in Sprint 1 T1.7); whether 32K context fits cleanly in budget under heavy multi-tool agent loops (may need to drop to 16K if KV cache pressure shows up).

---

# Research Synthesis and Strategic Recommendations

## Hybrid Gemma 4 Serving on AMD Strix iGPU: An Authoritative Technical Reference

## Executive Summary

The most credible 2026 community pattern for "running Gemma 4 4B alongside Gemma 4 26B" is **not** speculative decoding (which is broken on MoE targets in current llama.cpp and incompatible with `mmproj`), but a **modality-driven cascade**: small multimodal model handles perception (vision/audio), MoE text model handles cognition. Implemented well, this delivers near-frontier local capability — 26B-class reasoning quality at ~21-45 tok/s decode on a 32 GB iGPU, full multimodal support, single OpenAI-compatible endpoint for any client.

The recommended architecture is a **two-layer proxy in front of two specialized `llama-server` backends**: LiteLLM as outer gateway (auth, virtual keys, Prometheus metrics, rate limiting) and a custom FastAPI router as inner orchestrator (content sniffing, multimodal preprocessing, tool-call agent loop). This composition exists because LiteLLM's routing is name-based and cannot chain calls, while writing virtual-key/observability infrastructure from scratch wastes effort. The agent loop follows Anthropic's "single-threaded master loop" guidance — deliberately the simplest pattern that could work, optimizing for debuggability over orchestration cleverness.

Three early-2026 facts materially shape the build: (1) **ROCm has an open endless-loop bug specifically on `gemma-4-26B-A4B` on Strix-class iGPUs** — mandates Vulkan/RADV; (2) **TrevorJS abliterated GGUFs ship with a broken chat template** that leaks output into `reasoning_content` and likely impairs tool-call reliability — pushes the recommendation to the official Unsloth UD-Q5_K_M instead; (3) **LiteLLM was compromised on PyPI in March 2026** — version pinning with hash verification is mandatory, not optional.

**Key Technical Findings:**

- **Vulkan/RADV is the only viable backend** for Gemma 4 26B-A4B on this hardware class today; ROCm is broken specifically on this SKU.
- **Unsloth UD-Q5_K_M (~21 GB) is the sweet-spot quantization** — fits comfortably in 32 GB VRAM with 32K context, avoids the chat-template and tool-call risks of the abliterated variant.
- **A single `llama-server --mmproj` instance already serves both text and multimodal requests on the same OpenAI endpoint** — the E4B/26B split is for *quality* (better reasoner), not for separating modalities.
- **Modality cascade beats LLM-as-router** for this use case because the routing rule is deterministic ("non-text content present?") — no LLM-judgment variance to debug, zero added inference cost on pure-text requests.
- **Tool-call agent loop layered on top of the deterministic preprocessor** preserves the cascade-routing research benefit (26B can ask E4B specific follow-up questions) without the calibration headache of confidence-based escalation.
- **All other "best setup" interpretations** found online (speculative decoding, ensemble/MoA, multi-agent orchestration) are either broken on this hardware or violate Anthropic's published "start simple" guidance for predictable workflows.

**Top 5 Strategic Recommendations:**

1. **Build the dual-`llama-server` + FastAPI proxy + LiteLLM gateway architecture** as specified, in 4 sprints, ~12-18 hours of focused work.
2. **Use Unsloth UD-Q5_K_M for the reasoner**, not TrevorJS Q4_K_M — the chat-template and tool-call risks outweigh the uncensoring benefit unless an explicit uncensored-text need emerges.
3. **Pin and hash-verify LiteLLM** to a post-March-2026 audited version; subscribe to the security advisory.
4. **Defer audio support to v2** (after llama.cpp `input_audio` for Gemma 4 stabilizes); ship vision-only in v1 to derisk the launch.
5. **Validate every stage on `ct-dev-test` before `ct-ai-01`** per the existing homelab pattern; use Playwright MCP for browser-level acceptance testing per existing convention.

## Table of Contents (Full Document)

1. **Technical Research Scope Confirmation** — research topic, goals, and methodology
2. **Technology Stack Analysis** — runtime stack, model SKU map, quantization options, orchestration stack, deployment stack, performance numbers, gotchas
3. **Integration Patterns Analysis** — OpenAI API contract, SSE streaming, content blocks, tool-call orchestration, inter-service handoffs, security
4. **Architectural Patterns and Design** — chosen pattern, design principles, scalability, security architecture, data architecture, deployment architecture, ADRs
5. **Implementation Approaches and Technology Adoption** — adoption strategy, repo layout, build commands, systemd unit templates, test plan, deployment flow, observability, risk register, 4-sprint roadmap, success metrics
6. **Research Synthesis and Strategic Recommendations** *(this section)* — executive summary, TOC, strategic recommendations, future outlook, methodology and source verification, conclusion

## Strategic Technical Recommendations (Detailed)

### Architecture Recommendation

Adopt the **Hybrid Preprocessor + Single-Threaded Master Loop with Modality Cascade** pattern documented in §Architectural Patterns and Design. Concretely:

```
Clients (Open WebUI, Continue, Cursor, mobile)
    │
    ▼
LiteLLM gateway :4000   [auth, observability, rate limit, /v1/models aggregator]
    │
    ▼
FastAPI router :8000  [content sniff → E4B describe → 26B reason → tool loop → SSE]
    │                                       │
    ▼                                       ▼
llama-server :8080                   llama-server :8081
(E4B Q5_K_P + mmproj, Vulkan)        (Unsloth 26B-A4B UD-Q5_K_M, Vulkan,
                                      --jinja + asf0/gemma4_jinja template)
```

### Technology Selection

| Layer | Final choice | Pin |
|---|---|---|
| Inference engine | llama.cpp | Tag `b5XXX` (current good) |
| Backend | Vulkan/RADV | n/a |
| Multimodal model | Gemma 4 E4B Uncensored (HauhauCS) Q5_K_P + mmproj | Existing |
| Reasoner model | **TrevorJS gemma-4-26B-A4B-it-uncensored Q4_K_M** (user choice 2026-04-25) | Latest revision |
| Fallback reasoner (conditional) | Unsloth gemma-4-26B-A4B-it UD-Q5_K_M | Activated if Sprint 1 tool-call accuracy <90% |
| Chat template | asf0/gemma4_jinja (mandatory) | git SHA |
| Proxy framework | FastAPI + uvicorn + sse-starlette + httpx + pydantic v2 | Hash-pinned |
| Gateway | LiteLLM | **Audited post-2026-03 version, hash-pinned** |
| Process supervision | systemd | Host default |
| Configuration mgmt | Ansible (existing pattern) | n/a |

### Implementation Strategy

Phased and reversible per §Implementation Approaches: Sprint 1 (26B backend + Open WebUI manual picker) → Sprint 2 (proxy passthrough + multimodal preprocessing) → Sprint 3 (tool-call agent loop + LiteLLM gateway) → Sprint 4 deferred (audio when llama.cpp stabilizes). Each sprint exits on validated acceptance criteria; each is independently shippable and rollback-friendly.

### Competitive Technical Advantage (vs Cloud Alternatives)

For the homelab single-user use case, this architecture gives:

- **Sovereignty**: zero cloud spend, zero data egress, full control over the model and its behavior.
- **Capability ceiling**: 26B-class reasoning + multimodal vision matches mid-tier cloud offerings (e.g., GPT-4o-mini, Claude Haiku 4.5) for many tasks, at ~$0 marginal cost per query.
- **Latency floor**: local first-token in <1s for text, ~2.5s for multimodal — competitive with cloud API median.
- **Privacy**: every byte stays inside the LXC + Tailscale tailnet.

The deliberate trade-off vs cloud: no frontier-model capability (no GPT-5, no Claude Opus 4.7), no automatic upgrades, all ops responsibility on the operator.

## Implementation Roadmap and Risk Assessment (Cross-Reference)

The full 4-sprint roadmap with task-level breakdown lives in §Implementation Approaches → Implementation Roadmap. The 10-item risk register with likelihood/impact/mitigation is in §Implementation Approaches → Risk Assessment and Mitigation. Top three risks to internalize:

1. **R1 — TrevorJS chat-template breakage**: mitigated by choosing Unsloth UD-Q5_K_M as the reasoner. If uncensored text is later required, run TrevorJS as a *third* backend on a dedicated alias (`gemma4-26b-uncensored`) separate from the agentic `gemma4-auto` path.
2. **R2 — LiteLLM PyPI compromise recurrence**: mitigated by version + hash pinning, advisory subscription, manual review before bumps.
3. **R5 — `input_audio` instability in llama.cpp**: mitigated by deferring audio entirely from v1; explicitly reject audio content with a clear error.

## Future Technical Outlook

**Near-term (next 3-6 months) developments to watch:**

- **MoE-aware speculative decoding** in llama.cpp ([discussion #21975](https://github.com/ggml-org/llama.cpp/discussions/21975)): if landed, revisit speculative decoding for 26B-A4B (would meaningfully improve decode tok/s on this hardware).
- **`input_audio` stabilization** for Gemma 4 E4B in llama.cpp ([discussion #21334](https://github.com/ggml-org/llama.cpp/discussions/21334)): unblocks Sprint 4 audio support.
- **ROCm fix for 26B-A4B endless-loop** ([issue #21416](https://github.com/ggml-org/llama.cpp/issues/21416)): would enable ROCm as a Vulkan alternative, unlocking 10-20% additional decode throughput on RDNA 3.5.
- **Gemma 5** likely release (Google has a roughly annual cadence): the architecture is model-agnostic; swapping requires only the GGUF file + chat template update in Ansible defaults.

**Medium-term (6-18 months):**

- **Strix Halo successor / RDNA 4 mobile** would shift the compute envelope; the architecture remains valid.
- **OpenAI Responses API** convergence: more clients may move from `/v1/chat/completions` to the newer Responses API surface — proxy may need to expose both.
- **Open WebUI tool-streaming bug fix** ([#23066](https://github.com/open-webui/open-webui/issues/23066)) — would let `gemma4-auto` be used safely from OWUI without workarounds.

**Long-term (18+ months):**

- **Sub-7B models reaching 26B-class capability** would obsolete the dual-backend pattern in favor of a single high-quality multimodal model. Architecture should be ready to collapse the proxy into a passthrough when this transition happens.
- **Specialized inference hardware in homelab tier** (e.g., Strix Halo successors with 64+ GB unified memory) would enable larger MoE targets; architecture scales linearly to a third backend.

## Innovation and Research Opportunities (Local-Specific)

Beyond the immediate build, opportunities surfaced during research that warrant separate investigation:

- **Caching layer in the proxy**: prompt-prefix caching for repeated agent tool calls (e.g., system prompts) could cut latency by 30-50% on tool-loop iterations. Out of scope for v1 but a strong v3 candidate.
- **Local fine-tuning of E4B for description quality**: a small LoRA tuned on "describe images for downstream LLM reasoning" prompts could measurably improve `gemma4-auto` quality. Aligns with the existing Ollama model curation pattern.
- **Cross-model prompt rewriting**: a tiny LLM (or rule-based system) that detects ambiguous queries and rewrites them for 26B clarity. Out of scope but interesting.
- **Skill-builder integration**: per `feedback_skill_builder.md`, expose this architecture to other Claude-Code-style agents in the homelab as a tool — could become a self-improving infrastructure component.

## Technical Research Methodology and Source Verification

### Methodology Summary

- **Web-first verification** for every claim using current 2026 sources; no reliance on training-data assumptions for facts about Gemma 4, llama.cpp 2026 state, LiteLLM, or current bug landscape.
- **Multi-source corroboration** for critical decisions (e.g., Vulkan vs ROCm validated against llama.cpp issue #21416, llm-tracker Strix Halo notes, dev.to Vulkan benchmark, knightli benchmark scoreboard — four independent sources).
- **Confidence levels** explicitly attached to each section (HIGH / MEDIUM / LOW) with gaps surfaced.
- **Pattern matching against existing homelab conventions** (Ansible role layout, vault-encrypted secrets, Tailscale-only exposure, ct-dev-test → ct-ai-01 promotion path, Playwright browser validation).
- **Adversarial framing**: actively sought out community reports of breakage (HF discussions, GitHub issues) rather than only reading marketing/docs.
- **Dispatched parallel research subagents** in Step 2 to cover the inference and orchestration stacks concurrently, reducing both wall-clock time and context bloat.

### Primary Source Categories

- **llama.cpp GitHub** (issues, discussions, README): authoritative on bugs, capabilities, flag semantics
- **Hugging Face** (model cards, discussions, file listings): authoritative on model artifacts and quantization options
- **Unsloth, Modular, AMD developer blogs**: quasi-authoritative on Gemma 4 deployment patterns
- **r/LocalLLaMA, dev.to, Level1Techs forums**: community benchmarks, real-world tok/s on RDNA 3.5
- **arXiv** (cascade-routing survey, unified routing paper): academic grounding for architectural pattern choice
- **Anthropic engineering** (Building Effective AI Agents, Claude Code architecture): authoritative on agent-loop design
- **Open WebUI docs and community**: Pipes/Functions surface, multi-endpoint registration
- **OpenAI cookbook + API reference**: streaming protocol, tool-call delta accumulation
- **dev.to LLM proxy landscape 2026**: LiteLLM compromise, Helicone status, gateway comparison

### Complete Source Inventory

All URL citations are inline in their respective sections; the canonical inventory:

**llama.cpp & Gemma 4:**
- [llama.cpp #21416 — ROCm endless-loop on 26B-A4B](https://github.com/ggml-org/llama.cpp/issues/21416)
- [llama.cpp #21826 — mmproj/draft incompatibility](https://github.com/ggml-org/llama.cpp/discussions/21826)
- [llama.cpp #21975 — Spec decode + MoE verification](https://github.com/ggml-org/llama.cpp/discussions/21975)
- [llama.cpp #21334 — Gemma 4 E4B audio input](https://github.com/ggml-org/llama.cpp/discussions/21334)
- [llama.cpp #13759 — Audio input support](https://github.com/ggml-org/llama.cpp/discussions/13759)
- [llama.cpp server README](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
- [llama.cpp multimodal docs](https://github.com/ggml-org/llama.cpp/blob/master/docs/multimodal.md)
- [Google Gemma 4 model card](https://ai.google.dev/gemma/docs/core/model_card_4)
- [HF Gemma 4 blog](https://huggingface.co/blog/gemma4)
- [Unsloth Gemma 4 docs](https://unsloth.ai/docs/models/gemma-4)
- [unsloth/gemma-4-26B-A4B-it-GGUF](https://huggingface.co/unsloth/gemma-4-26B-A4B-it-GGUF)
- [TrevorJS gemma-4-26B-A4B-it-uncensored-GGUF](https://huggingface.co/TrevorJS/gemma-4-26B-A4B-it-uncensored-GGUF)
- [TrevorJS HF discussion #2 — chat template error](https://huggingface.co/TrevorJS/gemma-4-26B-A4B-it-uncensored-GGUF/discussions/2)
- [TrevorS/gemma-4-abliteration repo](https://github.com/TrevorS/gemma-4-abliteration)
- [HauhauCS Gemma-4-E4B-Uncensored-HauhauCS-Aggressive](https://huggingface.co/HauhauCS/Gemma-4-E4B-Uncensored-HauhauCS-Aggressive)
- [HauhauCS profile](https://huggingface.co/HauhauCS)
- [Jiunsong/supergemma4-26b-uncensored-gguf-v2](https://huggingface.co/Jiunsong/supergemma4-26b-uncensored-gguf-v2)
- [asf0/gemma4_jinja custom template](https://github.com/asf0/gemma4_jinja)
- [llm-tracker Strix Halo notes](https://llm-tracker.info/_TOORG/Strix-Halo)
- [Level1Techs Strix Halo benchmarks](https://forum.level1techs.com/t/strix-halo-ryzen-ai-max-395-llm-benchmark-results/233796)
- [knightli GPU benchmark scoreboard](https://www.knightli.com/en/2026/04/23/llama-cpp-gpu-benchmark-cuda-rocm-vulkan-scoreboard/)
- [dev.to ~21 tok/s Gemma 4 Ryzen mini PC](https://dev.to/hrodrig/21-toks-gemma-4-on-a-ryzen-mini-pc-llamacpp-vulkan-and-the-messy-truth-about-local-chat-m82)
- [datapnt: Deploying Gemma 4 26B-A4B on RTX 5090](https://datapnt.com/blog/deploying-gemma-4-26b-a4b-on-rtx-5090)
- [AMD: Day 0 support for Gemma 4 on AMD GPUs](https://www.amd.com/en/developer/resources/technical-articles/2026/day-0-support-for-gemma-4-on-amd-processors-and-gpus.html)
- [HN: Gemma 4 Uncensored autoresearch results](https://news.ycombinator.com/item?id=47651216)

**Orchestration & Proxy:**
- [LiteLLM call hooks](https://docs.litellm.ai/docs/proxy/call_hooks)
- [LiteLLM routing](https://docs.litellm.ai/docs/routing)
- [LiteLLM auto routing](https://docs.litellm.ai/docs/proxy/auto_routing)
- [Open WebUI Pipes docs](https://docs.openwebui.com/features/extensibility/pipelines/pipes/)
- [Open WebUI OpenAI-compatible quick start](https://docs.openwebui.com/getting-started/quick-start/connect-a-provider/starting-with-openai-compatible/)
- [Open WebUI tool-message infinite loop bug #23066](https://github.com/open-webui/open-webui/issues/23066)
- [Multimodal Reasoning Pipe V1](https://openwebui.com/f/snicky666/multimodal_reasoning_pipe_v1)
- [sse-starlette](https://pypi.org/project/sse-starlette/)
- [talesmousinho/fastapi-openai-sse-stream](https://github.com/talesmousinho/fastapi-openai-sse-stream)
- [AlirezaAzadbakht/minimal-fastapi-openai-proxy](https://github.com/AlirezaAzadbakht/minimal-fastapi-openai-proxy)
- [fangwentong/openai-proxy](https://github.com/fangwentong/openai-proxy)
- [Building an OpenAI-Compatible Streaming Interface (Medium)](https://medium.com/@moustafa.abdelbaky/building-an-openai-compatible-streaming-interface-using-server-sent-events-with-fastapi-and-8f014420bca7)
- [ahmad2b/openai-agents-streaming-api](https://github.com/ahmad2b/openai-agents-streaming-api)
- [OpenAI Chat Completions streaming events](https://developers.openai.com/api/reference/resources/chat/subresources/completions/streaming-events)
- [OpenAI cookbook: how to stream completions](https://cookbook.openai.com/examples/how_to_stream_completions)
- [OpenAI function-calling guide](https://platform.openai.com/docs/guides/function-calling)
- [LLM proxy landscape 2026](https://dev.to/stockyarddev/the-llm-proxy-landscape-in-2026-helicone-acquired-litellm-compromised-and-whats-next-3oon)
- [Top 5 LLM Gateways 2026](https://dev.to/varshithvhegde/top-5-llm-gateways-in-2026-a-deep-dive-comparison-for-production-teams-34d2)
- [TrueFoundry LiteLLM alternatives](https://www.truefoundry.com/blog/litellm-alternatives)
- [Olla + Open WebUI integration](https://thushan.github.io/olla/integrations/frontend/openwebui-openai/)

**Architectural Patterns:**
- [Anthropic: Building Effective AI Agents](https://resources.anthropic.com/building-effective-ai-agents)
- [Anthropic: managed agents](https://www.anthropic.com/engineering/managed-agents)
- [Anthropic Claude Code architecture](https://www.zenml.io/llmops-database/claude-code-agent-architecture-single-threaded-master-loop-for-autonomous-coding)
- [Anthropic 6 composable patterns](https://aimultiple.com/building-ai-agents)
- [arXiv: Dynamic Model Routing and Cascading Survey 2026](https://arxiv.org/html/2603.04445v1)
- [arXiv: Unified Routing and Cascading 2410](https://arxiv.org/html/2410.10347v1)
- [LLMRouter](https://github.com/ulab-uiuc/LLMRouter)
- [RouteLLM](https://github.com/lm-sys/RouteLLM)
- [NVIDIA llm-router](https://github.com/NVIDIA-AI-Blueprints/llm-router)
- [Hybrid Cloud-Local LLM Architecture Guide 2026](https://www.sitepoint.com/hybrid-cloudlocal-llm-the-complete-architecture-guide-2026/)

### Confidence Profile

| Area | Confidence | Notes |
|---|---|---|
| llama.cpp Vulkan vs ROCm decision | HIGH | Multiple independent confirmations |
| Model SKU + capability map | HIGH | Google + HF + Unsloth corroborate |
| Quantization sweet spot | HIGH | Unsloth's UD-Q5_K_M is well-documented |
| Hybrid preprocessor + agent loop pattern | HIGH | Anthropic + 2026 cascade-routing research |
| FastAPI hexagonal layout | HIGH | Standard pattern, multiple reference templates |
| LiteLLM as outer gateway | HIGH | Documented call-hooks, virtual keys, observability |
| OpenAI streaming protocol details | HIGH | Official cookbook + API reference |
| 880M-specific tok/s numbers | MEDIUM | Extrapolated from 760M and 8060S |
| TrevorJS chat-template fix coverage | MEDIUM | HF discussion #2 reporter says incomplete |
| Tool-call accuracy on abliterated 26B | LOW | Not benchmarked publicly — must measure |
| LiteLLM streaming tool-call passthrough | LOW | Verify in implementation |
| Audio support feasibility | LOW | Explicitly deferred; high known instability |

### Methodology Limitations

- **No on-target measurement yet**: All performance numbers are extrapolations from similar (but not identical) hardware. Sprint 1 task T1.7 will produce ground-truth.
- **Web sources have a freshness ceiling**: 2026 is moving fast on llama.cpp; some bugs cited may be fixed by the time implementation begins (a feature, not a flaw — re-check during build).
- **No formal evaluation of reasoning quality** between Unsloth and TrevorJS variants: chose conservatively (Unsloth) based on chat-template stability rather than measured reasoning benchmarks.
- **Single-operator perspective**: no code-review by a second human; mitigation is the explicit phasing and reversibility of the rollout.

## Technical Appendices and Reference Materials

### Hardware and System Reference

- **Host**: `pve3` (Proxmox VE 9.x), AMD Strix-class APU, Radeon 880M iGPU (RDNA 3.5)
- **Container**: `ct-ai-01` (VMID 160), Linux LXC, GPU passthrough enabled
- **VRAM allocation**: 32 GB dedicated (BIOS-fixed) + 32 GB GTT (shared system memory)
- **Storage**: model weights on bulk storage; container rootfs on fast pool
- **Network**: internal LAN + Tailscale tailnet exposure
- **Cluster role**: pve3 has active cooling (~20°C NVMe delta vs pve1/pve2) per `project_pve_node_cooling.md`

### Existing Homelab Conventions Referenced

- **Ansible role pattern**: `homelab-infra/ansible/roles/llama-server/` — Vulkan-built llama.cpp + parameterized systemd template
- **Vault-encrypted secrets**: per `project_sparkle_cps.md` Azure DevOps creds pattern
- **Tailscale-only network exposure**: per `project_phone_notifications_tailscale.md`
- **Test container path**: deploy to ct-dev-test (192.168.50.152) before ct-ai-01, per `feedback_test_container.md`
- **Browser validation**: Playwright MCP for visual E2E, not just API checks, per `feedback_browser_validation.md`
- **Storage monitoring**: Terraform auto-discovery + Prometheus file_sd_configs per `project_storage_monitoring.md`
- **HA policy**: `--state matching current run-state` per `project_project_container_ha_policy.md`

### Glossary

- **A4B**: "Active 4B" — Gemma 4 26B MoE configuration with ~3.8B active params per token (8-of-128 expert routing)
- **mmproj**: Multimodal projector — separate GGUF file pairing with text weights to enable vision/audio
- **PLE**: Per-Layer Embedding — Gemma 4 E2B/E4B's parameter-sharing scheme that gives "effective" param count smaller than total
- **Abliteration**: Norm-preserving directional intervention removing refusal behavior from a model's residual stream; preserves capabilities better than full fine-tuning
- **EGA**: Expert-Granular Abliteration — applying abliteration per-expert in MoE models
- **LXC**: Linux Container — lightweight virtualization Proxmox uses
- **GTT**: Graphics Translation Table — system memory accessible to the GPU as overflow VRAM
- **RADV**: Mesa's open-source AMD Vulkan driver
- **mmproj-audio**: Audio projector variant for E2B/E4B (≤30s clips)

---

## Research Conclusion

### Summary of Key Findings

The research validates that the user's intuition about a "hybrid 4B + 26B" setup is correct in spirit, but identifies the *specific* pattern that's actually viable on this hardware in 2026: a **modality-driven cascade** with deterministic preprocessing and an optional tool-call agent loop, NOT speculative decoding (broken on MoE) and NOT LLM-as-router (overcomplicated for predictable workflows). The architecture is **two `llama-server` backends + custom FastAPI router + LiteLLM gateway**, with **Unsloth UD-Q5_K_M as the chosen 26B reasoner** (favoring chat-template stability over abliteration). The implementation is decomposable into 4 reversible sprints totaling 12-18 focused hours, with concrete artifacts (systemd unit templates, Ansible role structure, FastAPI hexagonal layout, 10 acceptance criteria) ready for the build phase.

### Strategic Impact Assessment

This architecture upgrades `ct-ai-01` from a single-model multimodal endpoint to a **production-grade local AI serving platform** capable of replacing a substantial fraction of cloud LLM consumption (vision + reasoning + tool-use) for the homelab's owner. The capability ceiling rises from ~8B-class quality to 26B-MoE quality on text reasoning, while preserving full multimodal support. The marginal cost is ~$0 per query, latency is competitive with cloud APIs at the median, and data sovereignty is absolute. The trade-offs are explicit: no frontier-model capability, all ops responsibility on the operator, and a one-time engineering investment of ~12-18 hours.

### Next Steps

1. **Confirm the model choice** (Unsloth UD-Q5_K_M vs TrevorJS Q4_K_M) — the research recommends Unsloth; verify there's no concrete uncensored-text need before committing.
2. **Begin Sprint 1** (foundation): verify Vulkan build, download Unsloth model + asf0 chat template, create `llama-server-26b` Ansible role, deploy to ct-dev-test, smoke-test, deploy to ct-ai-01, register in Open WebUI.
3. **Capture the 6 ADRs** identified in §Architectural Patterns and Design as actual ADR documents in the repo (matches existing `adr-architect` agent pattern).
4. **Open a tracking issue** in the homelab repo summarizing this research with a link to this document and the 4-sprint roadmap.
5. **Schedule a v2 review** for ~3 months out to assess llama.cpp audio stabilization and decide on Sprint 4 (audio support).

---

**Technical Research Completion Date:** 2026-04-25
**Research Period:** Comprehensive analysis of 2026 community practice, llama.cpp state, Gemma 4 ecosystem, and proxy/orchestration patterns
**Document Length:** ~9,000 words across 6 sections
**Source Verification:** All technical facts cited with current sources; multi-source corroboration on critical decisions
**Technical Confidence Level:** HIGH on architectural decisions, MEDIUM on hardware-specific perf numbers, LOW on items explicitly deferred (audio, tool-call accuracy on abliterated variant)

_This document serves as the authoritative technical reference for the hybrid Gemma serving build on `ct-ai-01`. It informs the implementation roadmap, ADRs, and acceptance criteria for the upcoming sprints._
