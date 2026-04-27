---
title: "Hybrid Gemma serving stack on ct-ai-01"
slug: hybrid-gemma-serving
category: architecture
last_reviewed: 2026-04-27
owner: tomamourette
related_pages: [tailscale-policy]
related_frs: []
related_adrs: [ADR-002, ADR-011, ADR-017]
status: draft
supersedes: []
superseded_by: null
tags: [llm, gemma, litellm, vulkan]
---

# Hybrid Gemma serving stack on ct-ai-01

## Summary

Local Gemma 4 26B-MoE runs on `ct-ai-01` via llama.cpp Vulkan
(`llama-server-26b` on `:8081`), fronted by `gemma-hybrid-proxy`
(FastAPI on `:8000`) and exposed through a LiteLLM gateway (`:4000`)
with virtual aliases `gemma4-auto`, `gemma4-26b-text`, `gemma4-26b-json`,
`gemma4-e4b-vision`, plus the `gemini-embedding-2` Gemini-routed embedder
alias. **Graphiti exception (post-2026-04-27, ADR-002 + ADR-017
amendments): Graphiti's LLM extraction now uses cloud
`gemini-2.5-flash-lite` directly, NOT this local stack.** Other
consumers (OWUI, ad-hoc developer queries) continue on the local
aliases.

## Context

### Why Vulkan

ct-ai-01 has no NVIDIA CUDA path; Vulkan is the available GPU compute
backend on the iGPU (and, when the OCULink dGPU lands, will remain the
unified backend). llama.cpp's Vulkan build is mature and runs the 26B-MoE
checkpoint at usable token rates (12–46 s extraction wall-clock, mean
~20 s, per ADR-017 v3 spike).

### Why a hybrid proxy in front of llama-server

llama.cpp's bare HTTP API drifts from OpenAI semantics in places that
matter for downstream clients (modality routing, JSON-mode injection,
chat-template knobs). `gemma-hybrid-proxy` is a thin FastAPI hexagonal
adapter that:

- Routes by modality across the bare 26B-text and E4B-vision upstreams.
- Forwards `chat_template_kwargs` so callers can disable Gemma 3's
  always-on thinking mode (see Pitfalls).
- Owns three virtual model aliases in the proxy layer; LiteLLM exposes
  them outward as named models.

### Why LiteLLM in front of the proxy

LiteLLM gives us bearer-token auth, Prometheus metrics on `/metrics`,
request logging, `/v1/models` aggregation, and a single OpenAI-compatible
surface for *all* homelab LLM aliases (local + Gemini embedder). It is
the only network-facing layer of the stack — the inner FastAPI proxy and
both llama-servers bind loopback-only.

## Procedure / Decision

### Component layout

| Layer | Process | Bind | Role |
|---|---|---|---|
| Outer gateway | `litellm` 1.83.13 | `0.0.0.0:4000` | OpenAI-compatible front door, bearer auth, Prometheus, alias routing |
| Inner proxy | `gemma-hybrid-proxy` (FastAPI, hexagonal) | `127.0.0.1:8000` | Modality cascade, JSON-mode injection, `chat_template_kwargs` passthrough |
| Text upstream | `llama-server-26b` (TrevorJS Q4_K_M, asf0 chat template) | `127.0.0.1:8081` | Gemma 4 26B-MoE text reasoning |
| Vision/audio upstream | `llama-server` (E4B Q5_K_P + mmproj) | `127.0.0.1:8080` | Gemma 4 E4B vision passthrough |
| App on box | Open WebUI | `:3000` | Routes through LiteLLM with bearer auth |

Models live on `/var/lib/ollama/models/llama-models/` (hdd-pool, ~80 TB
available). The original research path of `/opt/llama-models` was a
rootfs-too-small dead end; the corrected path is in role defaults.

### Virtual aliases (LiteLLM `model_list`)

Defined in
[`homelab-infra/ansible/roles/litellm-gateway/templates/litellm-config.yaml.j2`](git:homelab-infra/ansible/roles/litellm-gateway/templates/litellm-config.yaml.j2):

| Alias | Routes to | Intended use |
|---|---|---|
| `gemma4-auto` | proxy modality cascade | text + passive image; **agent-loop tool-calls NOT production-reliable** (Sprint 4 priority 9.22) |
| `gemma4-26b-text` | proxy → 26B upstream | text reasoning, 100% reliable |
| `gemma4-e4b-vision` | proxy → E4B upstream | vision/audio passthrough, 100% reliable |
| `gemma4-26b-json` | proxy → 26B with forced JSON-mode + thinking disabled | structured-output workloads (ADR-017 v3) |
| `gemini-embedding-2` | LiteLLM → Google Gemini API | embeddings only (per ADR-003 v2) |

A `gemini-2.5-flash-lite` alias is reserved as a forward-compat sentinel
in the LiteLLM config but is **not yet deployed at this layer** —
Graphiti currently calls Google directly (see "Graphiti exception" below).

### Consumer routing

| Consumer | Path | Notes |
|---|---|---|
| Graphiti (post-2026-04-27) | **Direct to Google** via `gemini-2.5-flash-lite` | Bypasses the local stack per ADR-002 + ADR-017 amendments |
| Open WebUI on ct-ai-01 | LiteLLM `:4000` → local aliases | Bearer auth |
| Ad-hoc dev queries (Continue.dev, Cursor, phone via Tailscale) | LiteLLM `:4000` over tailnet | Bearer auth — see [Tailscale policy](tailscale-policy) |
| Ai-Dev Hermes container | **OpenRouter directly** (`google/gemma-4-26b-a4b-it`) | Discrepancy with prior memory — see "Discrepancies surfaced" below |

### Graphiti exception (post-2026-04-27)

ADR-017 v3's ADOPT-LOCAL verdict for Graphiti was reversed by the v3
amendment dated 2026-04-27. Graphiti now uses cloud
`gemini-2.5-flash-lite` directly via the standard OpenAIClient + Google
Gemini OpenAI-compat endpoint. The amendment in
[`_bmad-output/planning-artifacts/products/context-stack/adrs/ADR-017-graphiti-llm-local-vs-cloud-decision.md`](git:homelab-playbook/_bmad-output/planning-artifacts/products/context-stack/adrs/ADR-017-graphiti-llm-local-vs-cloud-decision.md)
records why: the local stack passed parse-quality (50/50 / 49/50 in v3
spike) but failed integration-layer Graphiti chain testing across ≥6
stacked impedance issues (Pydantic strict-mode in factories.py,
`responses.parse()` vs `chat.completions`, schema-mismatch, etc.).
**The reversal is narrow to Graphiti.** Local Gemma is retained for
Hermes-class / OWUI / dev-ad-hoc consumers.

Reversal-of-reversal trigger (per ADR-017 amendment):
1. graphiti-core ships an `openai_generic` provider arm in factories.py
   (PR #1437 or successor).
2. local llama.cpp grows reliable JSON-schema enforcement.
3. A parse-then-Pydantic-validate smoke test of the full chain produces
   clean results equivalent to the cloud path.

## Pitfalls

### Pydantic strict-mode rejecting `chat_template_kwargs`

`gemma-hybrid-proxy`'s request model previously had `extra="forbid"`
and rejected the OpenAI-compatible `chat_template_kwargs` field with
HTTP 422 `extra_forbidden`. Without that field, Gemma 3's chat
template defaulted `enable_thinking=true` and every request burned
its entire output budget on hidden reasoning, returning empty
`content` with `finish_reason=length`. **Patch shipped 2026-04-26**
to
[`homelab-infra/ansible/roles/gemma-hybrid-proxy/files/src/gemma_hybrid_proxy/adapters/openai_models.py`](git:homelab-infra/ansible/roles/gemma-hybrid-proxy/files/src/gemma_hybrid_proxy/adapters/openai_models.py)
(explicit `chat_template_kwargs: dict[str, Any] | None = None` field;
unit tests at `tests/unit/test_chat_completions.py`).

### Upstream timeout

Default `request_timeout_s=60` is too tight: real extractions on the
26B-MoE/Vulkan stack run 12–46 s with mean ~20 s. Bumped to 120 s in
[`homelab-infra/ansible/roles/gemma-hybrid-proxy/defaults/main.yml`](git:homelab-infra/ansible/roles/gemma-hybrid-proxy/defaults/main.yml)
to keep deploys from regressing.

### Chat-template filename

The asf0/gemma4_jinja chat template ships as `chat_template.jinja`,
not `gemma4.jinja`. Hard-coding `gemma4.jinja` in role defaults breaks
the upstream load.

### systemd `WatchdogSec=30` killed uvicorn

uvicorn does not call `sd_notify`; the watchdog spuriously kills the
proxy. Removed from the unit template; the systemd unit ships without
`WatchdogSec`.

### LiteLLM listen-host = `0.0.0.0` is intentional

Sprint 3 default of `127.0.0.1` was widened in Story 9.17 to
`0.0.0.0:4000` so:

1. Prometheus on ct-docker-01 can scrape `/metrics` over the LAN.
2. Tailscale clients (Continue.dev, Cursor, phone) can reach the
   gateway from off-host.

The bearer token (`LITELLM_MASTER_KEY`) is the security boundary; no
path through this listener is reachable without the master / virtual
key. Public DNS / port-forward stays disabled per the
[Tailscale policy](tailscale-policy).

### LiteLLM PyPI compromise (March 2026)

`litellm` 1.82.7 / 1.82.8 shipped a credential stealer. The role pins a
post-incident audited release: `litellm[proxy,proxy-runtime]==1.83.13`
in
[`homelab-infra/ansible/roles/litellm-gateway/defaults/main.yml`](git:homelab-infra/ansible/roles/litellm-gateway/defaults/main.yml).
Do not bump without re-auditing.

### Agent-loop tool-call regression on `gemma4-auto`

Sprint 3 25-prompt smoke (12/25 pass) showed `gemma4-auto`'s agent loop
emits tool calls as plain text
(`<|tool_call|>call:analyze_image{...}<tool_call|>`) instead of
structured `delta.tool_calls` — the orchestrator never observes
`finish_reason=tool_calls`. **Sprint 4 priority Story 9.22.** Until
fixed, prefer `gemma4-26b-text` or `gemma4-e4b-vision` for
tool-calling workflows.

## Discrepancies surfaced (memory vs repo state, 2026-04-27)

- **Hermes consumer claim:** the source memory states local Gemma serves
  "Hermes/OWUI/dev-ad-hoc". Verified against
  [`homelab-infra/ansible/roles/ai-dev-hermes/defaults/main.yml`](git:homelab-infra/ansible/roles/ai-dev-hermes/defaults/main.yml):
  `ai_dev_hermes_model_provider: openrouter`, base URL
  `https://openrouter.ai/api/v1`, model
  `google/gemma-4-26b-a4b-it`. Hermes currently calls **OpenRouter
  directly**, not the local LiteLLM stack. Confirmed consumers of the
  local stack are OWUI on ct-ai-01 and ad-hoc dev clients reaching
  `:4000` over the tailnet.
- **`gemini-2.5-flash-lite` LiteLLM alias:** the LiteLLM config carries a
  forward-compat sentinel block but no live alias entry. Graphiti's
  cloud-Gemini path goes around LiteLLM today, not through it. If a
  future story reroutes Graphiti through LiteLLM (for cost-cap
  observability), the sentinel block is the correct splice point.

## Cross-references

- [ADR-002 amendment (2026-04-27)](git:homelab-playbook/_bmad-output/planning-artifacts/products/context-stack/adrs/ADR-002-gpt-4o-mini-for-graphiti-extraction-phase-1.md)
  — Graphiti LLM switch to `gemini-2.5-flash-lite`
- [ADR-011](git:homelab-playbook/_bmad-output/planning-artifacts/products/context-stack/adrs/ADR-011-litellm-bridge-via-openai-base-url.md)
  — LiteLLM bridge via `OPENAI_BASE_URL` env var
- [ADR-017 v3 + 2026-04-27 amendment](git:homelab-playbook/_bmad-output/planning-artifacts/products/context-stack/adrs/ADR-017-graphiti-llm-local-vs-cloud-decision.md)
  — ADOPT-LOCAL verdict and Graphiti-only reversal
- [`homelab-infra/ansible/roles/gemma-hybrid-proxy/`](git:homelab-infra/ansible/roles/gemma-hybrid-proxy/)
- [`homelab-infra/ansible/roles/litellm-gateway/`](git:homelab-infra/ansible/roles/litellm-gateway/)
- [`homelab-infra/ansible/roles/llama-server-26b/`](git:homelab-infra/ansible/roles/llama-server-26b/)
- [Hybrid Gemma research](git:homelab-playbook/_bmad-output/planning-artifacts/research/technical-hybrid-gemma-serving-research-2026-04-25.md)
- [Hybrid Gemma architecture](git:homelab-playbook/_bmad-output/planning-artifacts/hybrid-gemma-serving-architecture.md)
- [Hybrid Gemma client runbook](git:homelab-playbook/docs/runbooks/hybrid-gemma-clients.md)
- [Tailscale policy](tailscale-policy) — for off-LAN reachability of `:4000`
