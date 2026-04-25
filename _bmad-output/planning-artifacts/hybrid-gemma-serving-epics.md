---
stepsCompleted: ['step-01-validate-prerequisites', 'step-02-design-epics', 'step-03-create-stories', 'step-04-final-validation']
inputDocuments:
  - 'homelab-playbook/_bmad-output/planning-artifacts/research/technical-hybrid-gemma-serving-research-2026-04-25.md'
  - 'homelab-playbook/_bmad-output/planning-artifacts/hybrid-gemma-serving-architecture.md'
project_name: 'homelab — hybrid-gemma-serving'
parent_initiative: 'Epic 8 PVE3 + Local LLM (follow-on)'
date: '2026-04-25'
user_name: 'tomamourette'
---

# Hybrid Gemma Serving - Epic Breakdown

## Overview

This document decomposes the **Hybrid Gemma Serving** initiative into one new epic with 21 stories across 4 sprints. The epic is a direct follow-on to **Epic 8 (PVE3 Node + Local LLM)** — Epic 8 delivered the LXC + GPU + Ollama + Open WebUI baseline; this epic replaces the single-model serving with a dual-backend orchestration that pairs **Gemma 4 E4B** (multimodal: vision + audio) with **Gemma 4 26B-A4B** (MoE text reasoner) behind a **custom OpenAI-compatible orchestration proxy** and a **LiteLLM gateway** for multi-app access.

**Source of truth:** `homelab-playbook/_bmad-output/planning-artifacts/research/technical-hybrid-gemma-serving-research-2026-04-25.md`. The 4-sprint roadmap in §Implementation Approaches → Implementation Roadmap is the input for these stories. The 10-item acceptance criteria list in §Implementation Approaches → Testing and Quality Assurance maps directly to story-level acceptance criteria. The 10-item risk register in §Implementation Approaches → Risk Assessment and Mitigation is referenced by `Risks:` flags on the stories where each risk applies.

**Architecture doc (in-progress):** `homelab-playbook/_bmad-output/planning-artifacts/hybrid-gemma-serving-architecture.md`.

**Critical user decision recorded 2026-04-25:** TrevorJS Q4_K_M is the chosen primary reasoner (uncensored output prioritized over chat-template stability and tool-call reliability). Unsloth UD-Q5_K_M is defined as a conditional fallback if the **Sprint 1 tool-call accuracy gate** fails (see Story 9.5). This deviates from the research's text-recommendation (which favored Unsloth) but is an informed product trade-off; the gate exists explicitly to surface the consequence early so that the fallback can be activated before the proxy / agent-loop work in Sprints 2 and 3 commits to a broken reasoner.

---

## Problem Statement

Open WebUI on `ct-ai-01` currently talks to a single `llama-server` instance running Gemma 4 E4B. E4B is a strong multimodal model but a weak reasoner; the operator wants 26B-class reasoning quality on text and code while preserving E4B's vision/audio capability. Running two `llama-server` processes on the iGPU is straightforward, but exposing them as a single endpoint that auto-routes by content type (text → 26B, image → E4B-describe → 26B-reason), supports a tool-call agent loop (so 26B can re-query E4B with specific follow-up questions), and serves all clients (Open WebUI, Continue.dev, Cursor, mobile, scripts) under one bearer-token gateway requires deliberate orchestration that doesn't exist out of the box.

## Scope

**In scope:**

- Second `llama-server` systemd unit for Gemma 4 26B-A4B (TrevorJS Q4_K_M primary; Unsloth UD-Q5_K_M conditional fallback), `127.0.0.1:8081`, Vulkan-built, `--jinja` enabled, `asf0/gemma4_jinja` chat template
- Custom FastAPI orchestration proxy (`gemma-hybrid-proxy`) on `127.0.0.1:8000`, hexagonal layout, exposing 3 virtual model aliases (`gemma4-auto`, `gemma4-26b-text`, `gemma4-e4b-vision`)
- Tool-call agent loop with `analyze_image` tool (allows 26B to re-query E4B mid-stream)
- LiteLLM gateway on `127.0.0.1:4000` with virtual-key auth, Prometheus metrics, version-pinned post-March-2026 advisory
- Three new Ansible roles (`llama-server-26b`, `gemma-hybrid-proxy`, `litellm-gateway`) following the existing `llama-server` role pattern
- Open WebUI repointed at LiteLLM as the canonical endpoint; secondary clients (Continue.dev, Cursor, mobile) configured with virtual key
- Tailscale-only public exposure (matches existing phone-notifications policy)

**Out of scope (deferred to Sprint 4 or later):**

- Audio support (`input_audio` content blocks + `transcribe_audio` tool) — gated on llama.cpp [#21334](https://github.com/ggml-org/llama.cpp/discussions/21334) stabilizing
- Embeddings endpoint (`/v1/embeddings`) — defer until a concrete consumer needs it
- Speculative decoding — explicitly broken on MoE + mmproj per [llama.cpp #21826](https://github.com/ggml-org/llama.cpp/discussions/21826)
- Multi-tenant key tiering, rate-limit-by-app — single-user homelab, not needed
- Migration to a future Gemma 5 release

## Success Criteria

The epic is complete when **all 10 acceptance criteria from research §Implementation Approaches → Testing and Quality Assurance** pass on `ct-ai-01`, plus:

- Open WebUI's model picker shows three virtual aliases (`gemma4-auto`, `gemma4-26b-text`, `gemma4-e4b-vision`) and routes correctly through LiteLLM
- A 1-hour soak test produces no memory leaks, no streaming hangs, no stream-corruption events
- Browser-level E2E suite (Playwright MCP) passes against Open WebUI for text, image, and tool-call flows
- All artifacts (FastAPI app, Ansible roles, systemd units, LiteLLM config) deployed via the standard `ct-dev-test → ct-ai-01` Ansible flow with `verify.yml` checks passing
- Sprint 1 tool-call accuracy gate documented in an ADR (either confirms TrevorJS as primary reasoner or activates the Unsloth fallback)

## Parent Initiative & Cross-References

- **Parent initiative:** Epic 8 (PVE3 Node + Local LLM) in `epics.md` — completed 2026-04-15. The `ct-ai-01` LXC, GPU passthrough, Vulkan-built `llama-server`, and Open WebUI baseline that this epic builds on were all delivered there.
- **Research doc:** `homelab-playbook/_bmad-output/planning-artifacts/research/technical-hybrid-gemma-serving-research-2026-04-25.md`
- **Architecture doc (in-progress):** `homelab-playbook/_bmad-output/planning-artifacts/hybrid-gemma-serving-architecture.md`
- **Existing role pattern:** `homelab-infra/ansible/roles/llama-server/` (existing E4B serving) — direct template for the new `llama-server-26b` role.

## Epic List

### Epic 9: Hybrid Gemma Serving — Dual-Backend Orchestration

The operator has a single OpenAI-compatible endpoint on `ct-ai-01` that auto-routes prompts to the right Gemma 4 backend (E4B for vision, 26B-A4B for reasoning), supports a tool-call agent loop that lets the reasoner re-query the multimodal model mid-stream, and is consumable from Open WebUI, IDE plugins, mobile, and scripts via a LiteLLM gateway with bearer-token auth and Prometheus metrics. Sprint 4 (audio) is in-epic but explicitly marked deferred / out of MVP.

**Sprint structure:**

| Sprint | Theme | Stories | Status |
|---|---|---|---|
| Sprint 1 | Foundation — second `llama-server` + tool-call gate | 9.1 → 9.5 | MVP |
| Sprint 2 | Proxy passthrough + multimodal preprocessing | 9.6 → 9.11 | MVP |
| Sprint 3 | Tool-call agent loop + LiteLLM gateway | 9.12 → 9.17 | MVP |
| Sprint 4 (priority) | Agent-loop production reliability fix | 9.22 | **MVP feature-complete** |
| Sprint 4 (deferred) | Audio support + hardening | 9.18 → 9.21 | **Deferred / out of MVP** |

**Total: 1 epic, 22 stories (17 Sprint 1-3 MVP + 1 Sprint 4 priority + 4 deferred).**

### Dependency Chain

```
Sprint 1 (9.1 → 9.2 → 9.3 → 9.4 → 9.5*)
        ↓
        ↓ (* if 9.5 fails the ≥90% schema-valid gate, branch to ADR-2b
        ↓   Unsloth-fallback flow before Sprint 2 begins)
        ↓
Sprint 2 (9.6 → 9.7 → 9.8 → 9.9 → 9.10 → 9.11)
        ↓
Sprint 3 (9.12 → 9.13 → 9.14 → 9.15 → 9.16 → 9.17)
        ↓
Sprint 4 priority track (REQUIRED for MVP feature-complete)
        ↓
       9.22 (agent-loop production reliability fix)
        ↓
Sprint 4 deferred track (gated on llama.cpp #21334 stabilizing OR operator audio need)
        ↓
       9.18 → 9.19 → 9.20 → 9.21
```

Stories within a sprint are mostly sequential (later stories depend on earlier ones); the dependencies are called out per-story under `Depends on:`.

---

## Sprint 1 — Foundation

**Goal:** A second `llama-server` (Gemma 4 26B-A4B) running on `ct-ai-01:8081` alongside the existing E4B on `:8080`, registered in Open WebUI as a manual second model, and subjected to a 50-prompt synthetic tool-call accuracy test. The exit gate is the tool-call accuracy measurement that decides whether TrevorJS Q4_K_M (operator's primary choice) is viable as the agentic reasoner or whether Unsloth UD-Q5_K_M is activated as the fallback before any proxy work begins.

**Maps to research §Implementation Approaches → Implementation Roadmap → Sprint 1 (T1.1 through T1.7) plus the new T1.5-gate explicitly added per user direction 2026-04-25.**

### Story 9.1: Verify Vulkan build of llama.cpp on ct-ai-01

As a homelab operator,
I want the existing `llama-server` Ansible role's Vulkan build verified (and idempotently re-run if not),
So that the new 26B-A4B unit launches on the same proven Vulkan/RADV backend rather than discovering a build mismatch mid-Sprint.

**Sprint:** 1
**Depends on:** Epic 8 Story 8.4 (existing E4B `llama-server` on `ct-ai-01`)
**Source:** Research §Implementation Approaches → Build & Deployment Specifics → step 1 ("Build llama.cpp — already done; verify Vulkan-enabled")
**Risks:** R3 (llama.cpp upgrade breaks Vulkan build on Strix iGPU)

**Acceptance Criteria:**

**Given** `ct-ai-01` (192.168.50.160) has the existing `llama-server` Ansible role applied and the E4B `llama-server.service` running
**When** I run `pct exec 160 -- /opt/llama.cpp/build/bin/llama-server --version 2>&1 | head -10` from `pve3`
**Then** the output lists Vulkan among the active ggml backends (no ROCm references)
**And** if Vulkan is missing, re-running `ansible-playbook -i inventory ct-ai-01.yml --tags llama-server` rebuilds with `llama_cpp_vulkan: true` and the second invocation reports zero changed tasks (idempotent)
**And** the existing E4B `llama-server.service` remains `active (running)` after any rebuild
**And** the verified build tag is captured in `homelab-playbook/_bmad-output/implementation-artifacts/llama-cpp-build-verification-2026-04.md`

### Story 9.2: Download TrevorJS Q4_K_M GGUF and asf0/gemma4_jinja chat template

As a homelab operator,
I want the TrevorJS abliterated Gemma 4 26B-A4B Q4_K_M GGUF and the asf0/gemma4_jinja chat template downloaded to `/opt/llama-models/` on `ct-ai-01`,
So that Story 9.3's role has the model artifacts in place and the broken built-in chat template is overridden from day one.

**Sprint:** 1
**Depends on:** 9.1
**Source:** Research §Implementation Approaches → Build & Deployment Specifics → step 2 (model + template download); §Top 7 Gotchas item 2 (TrevorJS chat-template breakage); §Quantization Options for 26B-A4B
**Risks:** R1 (TrevorJS chat-template fix possibly incomplete — surfaced in Story 9.5)

**Acceptance Criteria:**

**Given** `ct-ai-01` has Hugging Face CLI available (or `huggingface-cli` installed inline) and `/opt/llama-models/` exists with sufficient free space (>20 GB)
**When** I run `huggingface-cli download TrevorJS/gemma-4-26B-A4B-it-uncensored-GGUF gemma-4-26B-A4B-it-uncensored-Q4_K_M.gguf --local-dir /opt/llama-models/ --local-dir-use-symlinks False`
**Then** the GGUF file (≈16.8 GB) lives at `/opt/llama-models/gemma-4-26B-A4B-it-uncensored-Q4_K_M.gguf` with mode `0644`
**And** `sha256sum` of the file matches the value published on the HF model page (recorded in `homelab-playbook/_bmad-output/implementation-artifacts/llm-model-manifest.md`)
**When** I run `curl -fsSL https://raw.githubusercontent.com/asf0/gemma4_jinja/<pinned-sha>/gemma4.jinja -o /opt/llama-models/gemma4-asf0.jinja`
**Then** the template file exists at `/opt/llama-models/gemma4-asf0.jinja`
**And** the git SHA used is recorded alongside the model checksum in the manifest
**And** the download steps are codified into the Story 9.3 Ansible role rather than left as one-shot manual commands

### Story 9.3: Create Ansible role `llama-server-26b`

As a homelab operator,
I want a new Ansible role that deploys the 26B-A4B `llama-server` as a systemd unit on `127.0.0.1:8081`,
So that the second backend is reproducible, vault-friendly, and matches the existing `llama-server` role's pattern.

**Sprint:** 1
**Depends on:** 9.2
**Source:** Research §Implementation Approaches → Development Workflows and Tooling (repo layout); §Build & Deployment Specifics → step 3 (systemd unit template + role defaults)
**Risks:** none unique to this story

**Acceptance Criteria:**

**Given** `homelab-infra/ansible/roles/llama-server/` exists as the template
**When** I create `homelab-infra/ansible/roles/llama-server-26b/` by copying the structure (`tasks/`, `handlers/`, `templates/`, `defaults/`, `vars/`, `meta/`, `verify.yml`)
**Then** the role includes a `templates/llama-server-26b.service.j2` matching the spec in research §Build & Deployment Specifics step 3 (Vulkan, `--jinja`, `--chat-template-file`, `-b 256`, `-c 32768`, sampling `--temp 1.0 --top-p 0.95 --top-k 64`)
**And** `defaults/main.yml` exposes the full variable catalog from research § (host=127.0.0.1, port=8081, gpu_layers=99, batch_size=256, context_size=32768, models_dir=/opt/llama-models, model_file=`gemma-4-26B-A4B-it-uncensored-Q4_K_M.gguf`, hf_repo=`TrevorJS/gemma-4-26B-A4B-it-uncensored-GGUF`, chat_template_file=`gemma4-asf0.jinja`)
**And** the role downloads the GGUF + chat template idempotently via Ansible (uses `community.general.huggingface_hub` or shells to `huggingface-cli` with `creates:`) so that Story 9.2's manual steps become role-managed
**And** all variables are prefixed `llama_server_26b_`
**And** all tasks are tagged `llama-server-26b`
**And** `verify.yml` checks: GGUF + chat template present, systemd unit `enabled` and `active`, port `8081` listening on `127.0.0.1`, `curl 127.0.0.1:8081/v1/models` returns the loaded model, `--version` output includes Vulkan
**And** running the role twice produces zero changed tasks on the second run (idempotent — NFR-INT pattern)

### Story 9.4: Deploy `llama-server-26b` to ct-dev-test then ct-ai-01 and register in Open WebUI

As a homelab operator,
I want the role deployed first to `ct-dev-test` (192.168.50.152) for smoke-testing, then to `ct-ai-01`, and registered in Open WebUI as a manual second model alongside the existing E4B,
So that the 26B backend is usable end-to-end through the existing UI before any proxy work begins.

**Sprint:** 1
**Depends on:** 9.3
**Source:** Research §Implementation Approaches → Implementation Roadmap → T1.5, T1.6, T1.7; existing user feedback `feedback_test_container.md` (deploy to ct-dev-test before ct-ai-01)
**Risks:** R3 (llama.cpp upgrade breaks Vulkan build) — caught by ct-dev-test step

**Acceptance Criteria:**

**Given** the `llama-server-26b` role passes `ansible-lint`
**When** I run `ansible-playbook -i inventory ct-dev-test.yml --tags llama-server-26b`
**Then** the role completes without error on `ct-dev-test` and `verify.yml` passes
**And** `curl 192.168.50.152:8081/v1/models` returns the TrevorJS 26B model name (loopback bind on dev container is acceptable for the smoke test; bind via SSH tunnel if needed)
**And** a manual chat round-trip against `ct-dev-test:8081` returns a coherent text response within reasonable latency
**When** I run `ansible-playbook -i inventory ct-ai-01.yml --tags llama-server-26b`
**Then** the role completes on `ct-ai-01` and `verify.yml` passes
**And** the existing E4B `llama-server.service` on `:8080` is unaffected (`active (running)`, no restart)
**And** Open WebUI's admin → connections has the 26B endpoint added as a second OpenAI-compatible endpoint pointing at `http://127.0.0.1:8081`
**And** Open WebUI's model picker now shows both the E4B and the 26B model
**And** a manual prompt against the 26B model in Open WebUI returns a coherent response
**And** measured tok/s falls within the 18–30 tok/s research band (recorded in `homelab-playbook/_bmad-output/implementation-artifacts/26b-baseline-perf.md`); if it falls outside, the deviation is documented but does not block the sprint

### Story 9.5: Sprint 1 tool-call accuracy gate (50-prompt synthetic test, three-tier decision)

As a homelab operator,
I want a 50-prompt synthetic tool-call test harness run against the TrevorJS 26B-A4B backend with the asf0 chat template, scoring schema-validity, correct-intent, and correct-args,
So that I know **before** Sprint 2's proxy work commits whether to keep TrevorJS as sole reasoner (≥90% PASS), parallel-deploy Unsloth UD-Q5_K_M alongside it (70-89% MARGINAL), or replace TrevorJS with Unsloth for tool-call paths (<70% FAIL) — the test harness is re-runnable so it can be re-measured after llama.cpp upgrades or template changes.

**Sprint:** 1 (exit gate)
**Depends on:** 9.4
**Source:** Research §Implementation Approaches → Risk Assessment → R1 (PRIMARY RISK after user choice); §Implementation Approaches → Success Metrics and KPIs (≥90% schema-valid baseline, refined to a three-tier decision tree per user feedback 2026-04-25); architecture ADR-002 addendum (in `hybrid-gemma-serving-architecture.md`)
**Risks:** R1 (TrevorJS chat-template fix possibly incomplete — this story exists explicitly to measure R1)

**Test prompt set (50 prompts in `tests/sprint1_toolcall_gate/prompts.jsonl`):**

- **20 single-tool-call prompts** (e.g., "analyze this image and tell me what's in the top-left corner" → expects `analyze_image` call with specific question)
- **15 multi-tool-call prompts** (multi-step reasoning that needs 2-3 tool calls)
- **5 parallel-call prompts** (single response with multiple tools at once)
- **5 error-recovery prompts** (tool returns error; model should retry or recover)
- **5 negative prompts** (no tool call needed; model should respond directly without inventing one)

**Scoring per prompt (binary, summed):**

- **Schema-valid:** the emitted `tool_call` JSON parses AND matches the registered tool schema (draft-07)
- **Correct-intent:** chose the right tool (or correctly chose none for negative prompts)
- **Correct-args:** arguments are sensible for the prompt — automated for structural correctness; manual graded on a 5-point spot-check sample for semantic sensibility

**Pass rate** = (prompts passing all 3 checks) / 50

**Acceptance Criteria:**

**Given** the TrevorJS 26B-A4B backend is running on `ct-ai-01:8081` with `--jinja` and `--chat-template-file gemma4-asf0.jinja` (Story 9.4)
**When** I author the 50-prompt test set above in `tests/sprint1_toolcall_gate/prompts.jsonl` (one JSON object per line, with `prompt`, `category`, `expected_tool` (or null), `expected_args_shape` fields)
**And** I author the test harness `tests/sprint1_toolcall_gate.py` (Python, pytest-organized, `httpx` for calls — executable standalone, doesn't require the full proxy; talks directly to `llama-server :8081`)
**Then** the harness POSTs each prompt to `http://127.0.0.1:8081/v1/chat/completions` with the registered tool schema, parses the response, and records per prompt: schema-valid (bool), correct-intent (bool), correct-args (bool, automated structural + manual spot-check sample)
**And** the harness emits an aggregate report `homelab-playbook/_bmad-output/implementation-artifacts/sprint1-toolcall-gate-results-YYYY-MM-DD.md` with per-prompt scores, summary pass rate, count of `reasoning_content` leakage cases (per Top-7 Gotcha #2), and the recommended tier per the decision tree below
**And** the harness is re-runnable as a single command (`pytest tests/sprint1_toolcall_gate.py`) — re-running after a llama.cpp upgrade or template change just re-executes and re-emits the report
**And** the report is committed to the homelab repo

**Gate decision tree (three-tier, replaces the prior binary gate):**

| Tier | Pass rate | Action | Resulting model layout |
|---|---|---|---|
| **PASS** | ≥90% | Keep TrevorJS as primary; **no action** | TrevorJS Q4_K_M only — `gemma4-26b-text` and `gemma4-auto` both route to it |
| **MARGINAL** | 70–89% | **Parallel deploy**: keep TrevorJS as primary for `gemma4-26b-text` (uncensored chat); deploy Unsloth UD-Q5_K_M as secondary for `gemma4-26b-text-strict` and route the tool-call agent loop in `gemma4-auto` to Unsloth | TrevorJS Q4_K_M + Unsloth UD-Q5_K_M coexist (~38 GB combined; fits 32 GB VRAM + GTT spillover; validate at deploy) |
| **FAIL** | <70% | **Replace**: Unsloth UD-Q5_K_M becomes primary for tool-call paths; TrevorJS retained only as `gemma4-26b-uncensored` alias for non-tool-call use cases | Unsloth UD-Q5_K_M is the agentic reasoner; TrevorJS reserved for explicit uncensored-chat invocation |

**Exit criteria:** The decision tier is recorded as an addendum to ADR-002 in `homelab-playbook/_bmad-output/planning-artifacts/hybrid-gemma-serving-architecture.md` (no separate ADR file); the 50-prompt report is committed; if MARGINAL or FAIL, the Unsloth GGUF (~21 GB) is downloaded and the relevant role/proxy alias wiring is updated and re-deployed via the standard ct-dev-test → ct-ai-01 flow before Sprint 2 begins.

---

## Sprint 2 — Proxy passthrough + multimodal preprocessing

**Goal:** A custom FastAPI orchestration proxy on `ct-ai-01:8000` exposes three virtual model aliases (`gemma4-auto`, `gemma4-26b-text`, `gemma4-e4b-vision`) over OpenAI-compatible REST. Pure-text and pure-vision requests pass through directly; `gemma4-auto` deterministically detects `image_url` content blocks, calls E4B for description (non-streaming), injects the description into the message history, and forwards to 26B with SSE streaming. Status events keep the user informed during the multimodal preprocessing step. Open WebUI is repointed at the proxy.

**Maps to research §Implementation Approaches → Implementation Roadmap → Sprint 2 (T2.1 through T2.9).**

### Story 9.6: Scaffold `gemma-hybrid-proxy` Python repo with hexagonal layout

As a homelab operator,
I want a new `gemma-hybrid-proxy` Python repo scaffolded with the hexagonal layout from the research doc,
So that the FastAPI app is structured for testability and future evolution before any orchestration logic is written.

**Sprint:** 2
**Depends on:** 9.5 (gate must pass before proxy work commits)
**Source:** Research §Implementation Approaches → Development Workflows and Tooling (repo layout); §Architectural Patterns → System Architecture Patterns (hexagonal)
**Risks:** R9 (reference template introduces a vulnerability when copied — mitigation: adapt patterns, do not copy verbatim)

**Repo location (RESOLVED):** Python source lives under `homelab-infra/ansible/roles/gemma-hybrid-proxy/files/` per architecture doc §Project Structure & Boundaries (matches the `ai-dev-omega-memory` precedent — Ansible role owns the Python source as `files/`). This is not an open question.

**Acceptance Criteria:**

**Given** `homelab-infra/ansible/roles/gemma-hybrid-proxy/files/` is the target (per architecture §Project Structure & Boundaries)
**When** I scaffold the proxy under `homelab-infra/ansible/roles/gemma-hybrid-proxy/files/` with the layout in architecture §Project Structure & Boundaries
**Then** the directory structure is `src/gemma_hybrid_proxy/{domain,adapters,api,config.py,main.py}`, `tests/{unit,integration}`, `pyproject.toml`, `requirements.txt`, `.env.sample`, `Dockerfile` (optional, systemd-direct via venv is the primary deploy path)
**And** `pyproject.toml` declares Python ≥ 3.11
**And** dependencies are pinned with hashes via `uv pip compile --generate-hashes`: `fastapi`, `uvicorn[standard]`, `httpx`, `sse-starlette`, `pydantic>=2.0`, `structlog`, `pytest`, `pytest-asyncio`
**And** `pre-commit` runs `ruff` + `mypy --strict src/gemma_hybrid_proxy/domain`
**And** an empty FastAPI app boots via `uvicorn gemma_hybrid_proxy.main:app --host 127.0.0.1 --port 8000` and responds 200 to `GET /health`
**And** `tests/unit/test_smoke.py` passes (just imports the app and checks `/health`)
**And** the repo is committed and pushed; CI (GitHub Actions or matching homelab convention) runs `ruff` + `mypy` + `pytest` on push and is green

### Story 9.7: Implement `/v1/models` advertising 3 virtual aliases

As a homelab operator,
I want the proxy to expose `GET /v1/models` returning the three virtual aliases,
So that Open WebUI and other OpenAI-compatible clients can discover the routing-aware models from the single endpoint.

**Sprint:** 2
**Depends on:** 9.6
**Source:** Research §Integration Patterns → API Design Patterns ("Pattern: Virtual model multiplexing"); §Integration Patterns → Data Formats & Content Blocks → "Capability advertisement" subsection
**Risks:** none

**Acceptance Criteria:**

**Given** the FastAPI app from Story 9.6
**When** I implement `GET /v1/models` in `api/models_router.py`
**Then** the response shape matches OpenAI's `{"object": "list", "data": [...]}` with three entries: `gemma4-auto`, `gemma4-26b-text`, `gemma4-e4b-vision`
**And** each entry includes `id`, `object: "model"`, `created`, `owned_by: "homelab"`, and a custom `capabilities` array per the research-doc table:
- `gemma4-e4b-vision` → `["text", "vision", "audio"]`
- `gemma4-26b-text` → `["text", "tools"]`
- `gemma4-auto` → `["text", "vision", "audio", "tools"]`
**And** unit tests in `tests/unit/test_models_router.py` assert the response shape and content
**And** the Open WebUI UI (if pointed at the proxy temporarily for testing) shows all three model names in its picker

### Story 9.8: Passthrough mode for `gemma4-26b-text` and `gemma4-e4b-vision` with SSE streaming

As a homelab operator,
I want `POST /v1/chat/completions` with `model="gemma4-26b-text"` or `model="gemma4-e4b-vision"` to forward transparently to the matching `llama-server` backend with SSE streaming intact,
So that the proxy is usable in pure-passthrough mode before any orchestration logic is added.

**Sprint:** 2
**Depends on:** 9.7
**Source:** Research §Integration Patterns → Communication Protocols (SSE format details); §Implementation Approaches → Implementation Roadmap T2.3, T2.4; reference template [`talesmousinho/fastapi-openai-sse-stream`](https://github.com/talesmousinho/fastapi-openai-sse-stream)
**Risks:** R9 (reference template — adapt, don't copy)

**Acceptance Criteria:**

**Given** Stories 9.7 and Sprint 1 backends
**When** I implement `POST /v1/chat/completions` in `api/chat_router.py` with adapter `adapters/llama_upstream.py` using `httpx.AsyncClient` (`max_connections=4` per upstream, configurable)
**Then** requests with `model="gemma4-26b-text"` route to `http://127.0.0.1:8081/v1/chat/completions` and the response (streaming or non-streaming) is forwarded byte-for-byte preserving headers like `Content-Type: text/event-stream`
**And** requests with `model="gemma4-e4b-vision"` route the same way to `http://127.0.0.1:8080`
**And** SSE streaming preserves OpenAI delta format: `data: {json}\n\n` blocks, terminator `data: [DONE]\n\n`, plus a `: keepalive\n\n` comment every 15s during long generations
**And** integration tests in `tests/integration/test_passthrough.py` use `httpx.MockTransport` to assert: streaming chunks pass through unchanged, non-streaming responses pass through unchanged, request headers (Authorization stripped at proxy entry, since LiteLLM handles that layer) and body shape are forwarded correctly
**And** acceptance criterion 1 from the research-doc test list passes: "POST `/v1/chat/completions` with `model='gemma4-26b-text'` and a text-only message returns a streamed response within 300ms first-token" (measured against the live ct-dev-test backend during integration testing)

### Story 9.9: Implement `gemma4-auto` with E4B preprocessing → 26B forwarding

As a homelab operator,
I want `model="gemma4-auto"` to deterministically detect `image_url` content blocks, call E4B (non-streaming) for a description, replace the image block with the textual description, and forward the rewritten request to 26B with SSE streaming,
So that the operator gets 26B-class reasoning over E4B-perceived images without any client-side orchestration.

**Sprint:** 2
**Depends on:** 9.8
**Source:** Research §Architectural Patterns → System Architecture Patterns (Hybrid Preprocessor + Single-Threaded Master Loop with Modality Cascade); §Integration Patterns → System Interoperability — Inter-Service Handoffs (the FastAPI router pseudocode); §Implementation Approaches → Implementation Roadmap T2.5
**Risks:** none unique

**Acceptance Criteria:**

**Given** Story 9.8 (passthrough working)
**When** I implement `domain/content_inspector.py` (pure function: takes the OpenAI message list, returns a list of `(message_index, block_index, block_type)` tuples for non-text blocks) and `domain/orchestrator.py` (the master loop)
**And** I add the `gemma4-auto` branch to `api/chat_router.py`
**Then** for a `gemma4-auto` request with no image/audio content, the proxy forwards directly to 26B (same path as `gemma4-26b-text`)
**And** for a `gemma4-auto` request with one or more `image_url` blocks, the proxy: (1) issues a non-streaming `POST /v1/chat/completions` to the E4B backend (`:8080`) per image with a fixed `describe this image in detail` system prompt, (2) replaces each `image_url` content block with a `text` block formatted as `[Image: <description>]`, (3) forwards the rewritten request to 26B (`:8081`) with `stream=True` and pipes the SSE response through to the client
**And** the rewritten message history is logged at DEBUG level for traceability (with image data redacted)
**And** unit tests for `content_inspector` cover: text-only messages, single image, multiple images, mixed text+image, empty content, malformed content blocks
**And** integration tests for `orchestrator` use `httpx.MockTransport` to assert the two-call sequence (E4B non-streaming describe, 26B streaming reason) and the message-rewriting logic
**And** acceptance criteria 2 and 3 from the research-doc test list pass: image-only request via `gemma4-e4b-vision` returns a streamed description; `gemma4-auto` with `image_url` triggers E4B-describe → 26B-reason in series with the final answer referencing image content

### Story 9.10: Status events during preprocessing (italic-formatted delta.content chunks)

As a homelab operator,
I want the proxy to emit visible status events during the multimodal preprocessing window (before 26B's first real token),
So that Open WebUI users see "_describing image..._" rather than a stalled spinner during the E4B call.

**Sprint:** 2
**Depends on:** 9.9
**Source:** Research §Implementation Approaches → Testing and Quality Assurance → acceptance criterion 5 ("Status events visible during the multimodal loop"); reference [Multimodal Reasoning Pipe V1](https://openwebui.com/f/snicky666/multimodal_reasoning_pipe_v1) (italic-formatted `delta.content` chunks pattern)
**Risks:** R4 (Open WebUI tool-call streaming bug — verify status events don't trigger it; status is plain `delta.content`, not `tool_calls`, so the bug should not apply)

**Acceptance Criteria:**

**Given** Story 9.9 (orchestrator working)
**When** I extend `domain/orchestrator.py` to emit SSE chunks with `delta.content` set to italic-formatted status messages during the preprocessing window
**Then** for `gemma4-auto` with image content, the client first receives one or more SSE chunks containing `delta.content: "\n_[describing image...]_\n"` (bracketed italic markdown with leading/trailing newlines, per ADR-012 in the architecture doc), followed by the actual 26B streaming response
**And** for multi-image requests, separate status events are emitted per image (e.g., `"\n_[describing image 1 of 3...]_\n"`)
**And** the status events are valid OpenAI SSE chunks (correct shape, `finish_reason: null`, included in the same stream as the final response)
**And** integration tests assert: status events arrive before first 26B token; status events do NOT appear for pure-text requests; status events do NOT appear when routing through `gemma4-26b-text` directly
**And** smoke-tested in Open WebUI: a vision prompt visibly shows the italic status during the ~1-2s E4B describe window before 26B output starts streaming

### Story 9.11: Create Ansible role `gemma-hybrid-proxy` and deploy via ct-dev-test → ct-ai-01; repoint Open WebUI

As a homelab operator,
I want an Ansible role that deploys the FastAPI proxy as a systemd unit, deployed first to `ct-dev-test` then to `ct-ai-01`, with Open WebUI repointed at the proxy as the canonical OpenAI endpoint,
So that the proxy is reproducible, supervised, and serving real Open WebUI traffic by end of Sprint 2.

**Sprint:** 2 (exit gate)
**Depends on:** 9.10
**Source:** Research §Implementation Approaches → Build & Deployment Specifics → step 4 (`gemma-hybrid-proxy.service.j2`); §Deployment and Operations Practices → Deployment flow
**Risks:** R3 (Vulkan build) — N/A here; R6 (VRAM exhaustion under sustained load — verify both backends + proxy fit within budget)

**Acceptance Criteria:**

**Given** the `gemma-hybrid-proxy` Python package is installable via `pip` from a tarball or git ref
**When** I create `homelab-infra/ansible/roles/gemma-hybrid-proxy/` with `tasks/`, `handlers/`, `templates/gemma-hybrid-proxy.service.j2` (matching the spec in research §Build & Deployment step 4), `defaults/main.yml`, `verify.yml`, `meta/main.yml`
**Then** the role creates a dedicated user (`proxy_user`), provisions a venv at `{{ proxy_dir }}/.venv`, installs the proxy package with hash-pinned requirements, templates `.env`, and installs+enables `gemma-hybrid-proxy.service`
**And** the systemd unit includes `Requires=llama-server.service llama-server-26b.service`, `WatchdogSec=30`, `NoNewPrivileges=true`, `ProtectSystem=strict`, `Restart=on-failure`, `RestartSec=5`
**And** all variables are prefixed `gemma_hybrid_proxy_`; all tasks tagged `gemma-hybrid-proxy`
**And** `verify.yml` checks: service active, port 8000 listening on 127.0.0.1, `/health` responds 200, `/v1/models` returns the three aliases
**When** I run `ansible-playbook -i inventory ct-dev-test.yml --tags gemma-hybrid-proxy`
**Then** the role completes and `verify.yml` passes on `ct-dev-test`
**And** integration tests from Stories 9.8–9.10 pass against the live ct-dev-test deployment
**When** I run `ansible-playbook -i inventory ct-ai-01.yml --tags gemma-hybrid-proxy`
**Then** the role completes on `ct-ai-01` and `verify.yml` passes
**And** Open WebUI's admin → connections is updated to point at `http://127.0.0.1:8000/v1` as the canonical OpenAI endpoint (the direct-to-`8080` and direct-to-`8081` connections from Story 9.4 are removed)
**And** the existing `llama-server.service` (E4B) is rebound to `127.0.0.1` (defense-in-depth note from research §Build step 4)
**And** Open WebUI's model picker now shows `gemma4-auto`, `gemma4-26b-text`, `gemma4-e4b-vision`
**And** end-to-end test: uploading an image to Open WebUI via `gemma4-auto` produces a 26B-reasoned answer that references the image content (Sprint 2 exit gate from research)
**And** Playwright MCP browser smoke test verifies the visible italic status event during the multimodal preprocessing step (per `feedback_browser_validation.md`)

---

## Sprint 3 — Tool-call agent loop + LiteLLM gateway

**Goal:** The 26B reasoner can mid-stream emit a `tool_calls` for `analyze_image`, the proxy intercepts the call, executes it against E4B with the original image data, appends the tool result to the conversation, and resumes 26B's stream — all transparent to the client. A LiteLLM gateway sits in front for bearer-token auth, Prometheus metrics, and rate limiting; Open WebUI, Continue.dev, Cursor, and the operator's phone are all configured to use it.

**Maps to research §Implementation Approaches → Implementation Roadmap → Sprint 3 (T3.1 through T3.9).**

### Story 9.12: Define `analyze_image` tool schema (JSON Schema draft-07)

As a homelab operator,
I want the `analyze_image` tool defined as an OpenAI-compatible function-calling schema,
So that the orchestrator can register it on `gemma4-auto` requests and the 26B reasoner has a stable contract to call against.

**Sprint:** 3
**Depends on:** 9.11
**Source:** Research §Integration Patterns → Tool-Call Orchestration Pattern; §Implementation Approaches → Implementation Roadmap T3.1
**Risks:** R1 (tool-call accuracy — already gated in Story 9.5; this story locks the schema)

**Acceptance Criteria:**

**Given** the OpenAI function-calling schema standard (JSON Schema draft-07 inside the `parameters` field of a `tool` definition)
**When** I author `domain/tools/analyze_image.py` with the tool definition
**Then** the schema includes `name: "analyze_image"`, `description` field clearly stating "use this when you need to ask a specific question about an image already provided in the conversation", and `parameters` with required `image_id: string` (e.g., `'image-1'`-style identifier of an image already in the conversation, per architecture §Tool-call schema rules) and required `question: string` (the specific follow-up question)
**And** the schema validates against the OpenAI function-calling spec
**And** unit tests cover: schema loads, schema validates a synthetic well-formed call, schema rejects missing-required-field calls, schema rejects extra-field calls (`additionalProperties: false`)
**And** the tool definition is registered in `domain/tools/__init__.py` so the orchestrator can include it in 26B requests when `gemma4-auto` is the selected model AND image content is present

### Story 9.13: Implement `delta_accumulator` for streaming tool_calls

As a homelab operator,
I want a `delta_accumulator` module that reassembles partial `tool_calls` deltas (per-index reassembly) from the SSE stream into complete tool-call objects,
So that the orchestrator can detect a finished tool call in the streaming response and decide whether to intercept it.

**Sprint:** 3
**Depends on:** 9.12
**Source:** Research §Integration Patterns → Tool-Call Orchestration Pattern (delta-accumulation pattern); §Implementation Approaches → Implementation Roadmap T3.2; §Open WebUI Integration Surface → "Open WebUI has [an infinite-loop streaming tool messages issue (#23066)] — Proxy must emit clean tool-call deltas"
**Risks:** R4 (Open WebUI tool-call streaming bug — surfaces here if delta emission is dirty)

**Acceptance Criteria:**

**Given** the OpenAI streaming tool_calls delta protocol (per-index, partial JSON arguments accumulated chunk-by-chunk)
**When** I implement `domain/delta_accumulator.py` with class `DeltaAccumulator` that consumes chunks and exposes a method to emit completed tool_calls when a chunk's `finish_reason` is `tool_calls` (or equivalent terminal signal)
**Then** the accumulator handles: single tool call across multiple chunks, multiple parallel tool_calls (different `index` values), interleaved text + tool_call deltas, edge case where the call completes in a single chunk
**And** the accumulator validates the accumulated arguments JSON before declaring a call complete (rejects calls with malformed JSON arguments and surfaces the error to the orchestrator)
**And** unit tests in `tests/unit/test_delta_accumulator.py` cover all branches above with synthetic SSE chunk sequences captured from llama-server
**And** the accumulator emits clean tool-call deltas when re-encoded for downstream forwarding (defends against Open WebUI bug #23066 — verified by inspecting emitted SSE bytes against a known-good fixture)

### Story 9.14: Implement orchestrator agent loop (intercept → execute → resume → stream)

As a homelab operator,
I want the orchestrator master loop to detect an `analyze_image` tool call from 26B mid-stream, execute it against E4B with the original image data, append the result as a `tool` message, re-issue the 26B call, and continue streaming the resumed response to the client,
So that the 26B reasoner can ask the multimodal model specific follow-up questions without the client knowing.

**Sprint:** 3
**Depends on:** 9.13
**Source:** Research §Architectural Patterns → System Architecture Patterns (single-threaded master loop per Anthropic's published agent guidance); §Integration Patterns → Tool-Call Orchestration Pattern; §Implementation Approaches → Implementation Roadmap T3.3
**Risks:** R4 (Open WebUI #23066), R6 (VRAM under sustained load — both backends active during agent loop)

**Acceptance Criteria:**

**Given** Stories 9.12 + 9.13
**When** I extend `domain/orchestrator.py` with the agent-loop branch
**Then** for `gemma4-auto` requests where (a) image content is present AND (b) the rewritten 26B call includes the `analyze_image` tool registration, the orchestrator: (1) streams the 26B response through the delta_accumulator, (2) on detecting a complete `analyze_image` tool_call, pauses forwarding to the client, executes the call against E4B with the indexed image data + the supplied question, (3) appends the E4B response as an OpenAI `tool` message to the conversation, (4) re-issues the chat-completions call to 26B with the appended history, (5) resumes streaming the new response to the client
**And** the loop has a hard cap of 5 tool-call iterations per request (configurable via `gemma_hybrid_proxy_max_tool_iterations`, default 5 per architecture §Error handling rules); on the 6th iteration, the loop stops and the partial response plus a `[max_iterations_reached]` status are emitted (force `finish_reason=stop`)
**And** an italic status event (`_consulting vision model..._`) is emitted to the client during each E4B execution window
**And** integration tests (against live ct-dev-test) cover: tool call triggered + executed + resumed (happy path), tool call with malformed arguments → fall back to plain stream, tool-call iteration cap reached, no tool call emitted (plain stream proceeds normally)
**And** acceptance criterion 4 from the research-doc test list passes: image + tool definitions trigger 26B emitting tool_calls, proxy executes against E4B, resumes 26B, final answer answers the specific question

### Story 9.15: Test with synthetic prompts that should trigger tool calls

As a homelab operator,
I want a small end-to-end test suite of synthetic prompts designed to provoke `analyze_image` tool calls,
So that I can demonstrate the agent loop works on real (not mocked) traffic before LiteLLM is layered on top.

**Sprint:** 3
**Depends on:** 9.14
**Source:** Research §Implementation Approaches → Implementation Roadmap T3.4
**Risks:** R1 (tool-call accuracy)

**Acceptance Criteria:**

**Given** the agent loop from Story 9.14 is deployed on `ct-dev-test`
**When** I author `tests/integration/sprint3_agent_loop/prompts.jsonl` with at least 10 prompts designed to provoke `analyze_image` calls (e.g., "I've shown you a screenshot. List every error message you can see, then explain what the most likely root cause is.")
**And** I run the runner script against `ct-dev-test:8000`
**Then** at least 70% of the prompts produce at least one `analyze_image` invocation in the trace log (target is loose because LLM behavior is non-deterministic; the assertion is "the loop fires when expected, not zero", not strict accuracy)
**And** every fired tool call: passes the schema validation, executes against E4B without error, has its result appended to the conversation, resumes 26B output
**And** the trace log for each prompt is captured in `tests/integration/sprint3_agent_loop/traces/` (one file per prompt) for manual review and as a regression baseline
**And** any prompt that triggers >3 iterations (the hard cap) is documented as a possible loop-detection or prompt-engineering concern

### Story 9.16: Deploy LiteLLM gateway with virtual key for self; configure model_list pointing at FastAPI router

As a homelab operator,
I want LiteLLM running on `ct-ai-01:4000` as the outer gateway, with a hash-pinned post-March-2026 audited version, configured to forward all three virtual aliases to the FastAPI router on `:8000`, with a single bearer key minted for myself,
So that all clients have one authenticated, observable, rate-limited entrypoint.

**Sprint:** 3
**Depends on:** 9.15
**Source:** Research §Implementation Approaches → Build & Deployment Specifics → step 5 (`litellm-gateway.service.j2` + LiteLLM `config.yaml`); §Implementation Approaches → Implementation Roadmap T3.5; §Risk Assessment R2 (PyPI compromise — pin + hash + advisory subscription)
**Risks:** R2 (LiteLLM PyPI compromise repeats — mitigation: this story IS the mitigation)

**Acceptance Criteria:**

**Given** the LiteLLM advisory and a verified-audited post-2026-03 version (`litellm==1.83.13` per architecture ADR-011, or the latest stable `1.83.x` the operator re-audits at deploy time)
**When** I create `homelab-infra/ansible/roles/litellm-gateway/` matching the existing role pattern (`tasks/`, `templates/litellm-gateway.service.j2`, `templates/config.yaml.j2`, `defaults/main.yml`, `verify.yml`)
**Then** `defaults/main.yml` exposes: `litellm_version` (PINNED), `litellm_master_key` (vault-encrypted reference), `litellm_db_url` (`sqlite:///var/lib/litellm/logs.db`), `litellm_port` (4000), `litellm_log_level` (INFO)
**And** `requirements.txt` for the LiteLLM venv pins the version with a `--hash=sha256:...` line; the role refuses to install if the hash mismatch occurs
**And** the `vault.yml` entry for `litellm_master_key` is committed (encrypted) to the homelab repo; the operator's bearer key is generated fresh and recorded only in the operator's password manager (not in git)
**And** `templates/config.yaml.j2` matches the research §step 5 spec: three model entries (`gemma4-auto`, `gemma4-26b-text`, `gemma4-e4b-vision`) all forwarding to `http://127.0.0.1:8000/v1` with `api_key: "noop"` (since LiteLLM auths the client side, the FastAPI side is loopback-only and trusts loopback)
**And** the systemd unit includes `Requires=gemma-hybrid-proxy.service`, `Restart=on-failure`, `NoNewPrivileges=true`
**And** `verify.yml` checks: service active, port 4000 listening on `127.0.0.1` (or Tailscale IP if configured), `/health` returns 200, `/v1/models` returns the three aliases (with master key auth), an unauthenticated request returns 401
**When** I deploy via `ansible-playbook -i inventory ct-dev-test.yml --tags litellm-gateway` then `ct-ai-01.yml`
**Then** both deploys complete without error and `verify.yml` passes
**And** acceptance criterion 9 from the research-doc test list passes: LiteLLM rejects requests with invalid bearer tokens; valid-token request reaches the FastAPI router

### Story 9.17: Configure clients (Open WebUI, Continue.dev, Cursor, phone) with virtual key + Prometheus + Grafana dashboard

As a homelab operator,
I want all client apps configured to use the LiteLLM gateway with the operator's bearer key, plus a Prometheus scrape config and a Grafana dashboard for LiteLLM metrics,
So that the multi-app consumer surface and the observability surface are both live by Sprint 3 exit.

**Sprint:** 3 (exit gate)
**Depends on:** 9.16
**Source:** Research §Implementation Approaches → Implementation Roadmap T3.6, T3.7, T3.8; §Open WebUI Integration Surface; §Deployment and Operations Practices → Observability
**Risks:** R7 (Tailscale outage — local LAN access remains; Tailscale is the secure remote layer, not the only path)

**Acceptance Criteria:**

**Given** Story 9.16 (LiteLLM live on `ct-ai-01:4000`)
**When** I update Open WebUI's admin → connections to point at `http://127.0.0.1:4000/v1` (Open WebUI runs in-LXC) with the bearer key stored in Open WebUI's secret store
**Then** Open WebUI's model picker shows the three virtual aliases sourced from LiteLLM
**And** an end-to-end Open WebUI prompt against `gemma4-auto` with an image attachment exercises the full path (LiteLLM → FastAPI → E4B describe → 26B reason → tool call → E4B re-query → 26B resume → SSE back to client)
**When** I configure Continue.dev's `config.yaml` (in the AI dev container or operator's IDE) with the LiteLLM URL (Tailscale IP for remote access) and bearer key
**Then** Continue.dev can send a chat-completions request and receive a streamed response
**When** I configure Cursor (if present) similarly
**Then** Cursor can send a chat-completions request and receive a streamed response
**When** I configure the operator's phone client (any OpenAI-compatible mobile app) with the Tailscale URL + bearer key
**Then** the phone can send a prompt over the tailnet and receive a streamed response
**And** all four clients are documented in `homelab-playbook/docs/runbooks/hybrid-gemma-clients.md` with config snippets (key redacted)
**When** I add LiteLLM to the existing Prometheus scrape config (homelab-apps observability stack) with target `<ct-ai-01-tailscale-ip>:4000/metrics` and bearer-key auth
**Then** Prometheus's `/targets` page shows the LiteLLM target as `UP`
**And** a new Grafana dashboard `dashboards/litellm-gemma.json` provisioned in the existing observability dashboard provisioning directory shows: requests per minute, p50/p95/p99 first-token latency, error rate, tokens-per-second per model, tool-call invocations per minute
**And** the dashboard loads within 3 seconds (matches existing NFR-PERF-1 from production-readiness epics)
**And** acceptance criterion 10 from the research-doc test list passes: `systemctl restart gemma-hybrid-proxy` causes <5s downtime; in-flight requests complete or fail cleanly

**Sprint 3 exit gate:** All 10 acceptance criteria from the research doc pass; multi-app access works from at least Open WebUI + one IDE + the phone over Tailscale; LiteLLM Prometheus metrics visible in Grafana.

---

## Sprint 4 — Priority fix + Deferred audio/hardening

**Sprint 4 has TWO tracks:**

- **Priority track (must complete before MVP feature-complete):**
  - Story 9.22 — Agent-loop production reliability fix (regression surfaced by Sprint 3 Story 9.15)

- **Deferred track (gated on llama.cpp #21334 stabilization OR concrete operator audio need):**
  - Story 9.18 — Track llama.cpp #21334 and decide trigger
  - Story 9.19 — Implement `transcribe_audio` tool + `input_audio` content branch
  - Story 9.20 — Browser E2E test suite (Playwright MCP)
  - Story 9.21 — Soak test (1 hour continuous) for memory stability

**Goal (priority track):** Restore the `gemma4-auto` agent loop in production. Sprint 1 Story 9.5 passed the tool-call gate at 98% against `:8081` direct, and Sprint 3 Story 9.14 succeeded in live smoke; but Story 9.15's 25-prompt suite against the production proxy compose flow showed 0/10 tool-triggering and 0/3 multi-iteration prompts produce structured `delta.tool_calls`. The 26B reasoner emits tool calls as plain-text tokens. MVP ships with this gap (per Option B director decision); Sprint 4 priority track closes it.

**Goal (deferred track):** Add Gemma 4 E4B audio capability through `transcribe_audio` tool + `input_audio` content blocks, harden the deployment with browser E2E tests and a 1-hour soak test.

**Status of deferred track: DEFERRED.** Held out of the MVP and only triggered when:

1. llama.cpp [#21334](https://github.com/ggml-org/llama.cpp/discussions/21334) (Gemma 4 E4B audio) lands stable, OR
2. A concrete operator need for audio in/out arises.

The deferred-track stories are scoped here so the work is recoverable without a fresh planning pass. Sprint 4 stays in this epic (rather than spawning a new one) because the work is small, contiguous, and uses the same artifacts (FastAPI app, Ansible roles, LiteLLM); no separate epic-level ceremony is justified.

**Maps to research §Implementation Approaches → Implementation Roadmap → Sprint 4 (deferred).** The priority Story 9.22 is a Sprint 3 regression fix and was not in the original research roadmap; it was added 2026-04-25 in response to Story 9.15's findings.

### Story 9.22 — Agent-loop production reliability (PRIORITY — not deferred)

**Status:** pending — REQUIRED for MVP feature-complete
**Sprint:** 4 (priority track — distinct from the deferred audio track 9.18-9.21)
**Trigger:** Sprint 3 Story 9.15 surfaced a critical regression on the `gemma4-auto` agent loop
**Evidence:** `_bmad-output/implementation-artifacts/sprint3-agentloop-smoke-results-2026-04-25.md` (12/25 PASS, 0/10 tool-triggering, 0/3 multi-iteration)
**Risks:** R1 reopened (chat-template effectiveness in proxy compose flow)

**Problem statement:**
The `gemma4-auto` agent loop (Story 9.14) does not fire under production traffic. The 26B reasoner emits tool calls as **plain-text tokens** in `delta.content` (e.g. `<|tool_call|>call:analyze_image{question:...}<tool_call|>`) instead of structured `delta.tool_calls` SSE chunks. The orchestrator (`domain/agent_loop.py`) never observes a `finish_reason=tool_calls` event, so `analyze_image` invocations never execute and the deep-vision agent loop is non-functional. Sprint 1 Story 9.5 missed this (98% PASS) because it tested the raw upstream (`:8081` with bare tool definitions), not the proxy compose flow (image preprocessing + augmented tools + larger context).

**Acceptance criteria:**

- AC-1: Re-run `homelab-infra/tests/sprint3_agentloop_smoke.py` against the same production proxy after fix; tool-triggering category passes ≥70% (7/10), multi-iteration category passes ≥66% (2/3).
- AC-2: At least one structured `tool_calls` event observed in production proxy logs after fix (`agent_loop.tool_iteration` log line present).
- AC-3: No regression: text-only and passive-image categories still 100% (10/10 combined).
- AC-4: ADR-002 addendum updated with the chosen mitigation + final pass rate.

**Investigation hypotheses (ordered by cost):**

1. **System prompt tightening** (cheapest): inject a `system` message in the `gemma4-auto` request that explicitly instructs the model to use the structured `tool_calls` field, not inline tokens. Test impact in isolation. If pass rate ≥70%, no further action.
2. **`gemma4-asf0.jinja` template audit** (medium cost): trace how the template renders the augmented tool list under proxy compose flow. Compare bare-prompt rendering (Story 9.5's path) vs compose-flow rendering (Story 9.15's path) to identify the divergence. Possible fixes: tweak template, add a tool-call-format directive.
3. **`--jinja` flag interaction** (medium cost): test whether disabling `--jinja` and using llama.cpp's built-in chat template (without the asf0 override) gives different tool-call structure. May break content/reasoning_content split (R1) — accept the trade or fork.
4. **Reasoner swap to Unsloth UD-Q5_K_M** (highest cost — model-weight change): activate ADR-002's conditional fallback. Deploy Unsloth as `gemma4-26b-text-strict`, route only the `gemma4-auto` agent-loop traffic through it. Lose uncensored output for the agent loop; keep TrevorJS for `gemma4-26b-text` and `gemma4-auto` non-tool-call paths. ~38 GB combined VRAM (relies on GTT spillover; validate empirically).

**Suggested approach:** test hypotheses in order; stop at first acceptable pass rate.

**Mitigation in production until 9.22 lands:** users should prefer `gemma4-26b-text` or `gemma4-e4b-vision` aliases for tool-call workflows. `gemma4-auto` remains functional for text + passive-image (the 80% case).

**Depends on:** Sprint 3 complete (proxy + LiteLLM live)
**Blocks:** Sprint 4 audio track (9.18-9.21) — fix the priority gap first

### Story 9.18: Track llama.cpp #21334 (Gemma 4 E4B audio) and decide trigger

As a homelab operator,
I want a recurring check on llama.cpp issue [#21334](https://github.com/ggml-org/llama.cpp/discussions/21334) and a documented trigger condition that activates Sprint 4,
So that audio support work begins exactly when (and only when) the upstream landscape is ready.

**Sprint:** 4 (deferred)
**Depends on:** Sprint 3 complete
**Source:** Research §Implementation Approaches → Implementation Roadmap → Sprint 4; §Risk Assessment R5 (`input_audio` instability)
**Risks:** R5 (audio instability — this story IS the mitigation through deferral + tracking)

**Acceptance Criteria:**

**Given** the llama.cpp #21334 discussion thread
**When** the operator periodically (e.g., monthly during planning ceremonies) checks the issue status
**Then** a one-line status update is appended to `homelab-playbook/_bmad-output/planning-artifacts/audio-tracking.md`
**And** if the discussion resolves with a stable, merged implementation for Gemma 4 E4B audio (or if a concrete audio use-case emerges), the operator opens Sprint 4 and proceeds with stories 9.19 → 9.21
**And** the trigger conditions are documented explicitly in `audio-tracking.md` (not implicit "I'll know it when I see it")

### Story 9.19: Implement `transcribe_audio` tool + `input_audio` content branch

As a homelab operator,
I want the proxy to handle `input_audio` content blocks deterministically (transcribe via E4B) AND a `transcribe_audio` tool the 26B reasoner can call to re-query specific portions of audio,
So that audio support has the same dual-path (preprocessing + agent loop) as vision.

**Sprint:** 4 (deferred — depends on Story 9.18 trigger)
**Depends on:** 9.18 trigger fires
**Source:** Research §Integration Patterns → Data Formats & Content Blocks (input_audio); §Implementation Approaches → Implementation Roadmap → Sprint 4
**Risks:** R5 (audio instability — verify on ct-dev-test before ct-ai-01)

**Acceptance Criteria:**

**Given** llama.cpp audio support for Gemma 4 E4B is stable (Story 9.18 trigger fired)
**When** I extend `domain/content_inspector.py` to detect `input_audio` blocks
**And** I extend `domain/orchestrator.py` to: (a) deterministically transcribe `input_audio` blocks via E4B and inject the text into the 26B request (mirroring the image-describe path), (b) handle `transcribe_audio` tool calls in the agent loop (mirroring `analyze_image`)
**And** I author the `transcribe_audio` tool schema following the same pattern as `analyze_image` (required: `audio_index: integer`, optional: `start_seconds: number`, `end_seconds: number`, `question: string`)
**Then** unit tests cover the new content_inspector branch and the new tool schema
**And** integration tests against ct-dev-test exercise an audio-only request (preprocessing path) and an audio + tool-definition request (agent-loop path)
**And** the deployment goes through the standard ct-dev-test → ct-ai-01 flow with `verify.yml` passing
**And** the deferred-from-Sprint-2 acceptance criterion for audio is added to the proxy test suite

### Story 9.20: Browser E2E test suite (Playwright MCP) for the full multi-app flow

As a homelab operator,
I want a Playwright MCP browser test suite covering the Open WebUI experience for text, image, audio, and tool-call flows,
So that the system is regression-tested at the UI level (per `feedback_browser_validation.md`) and not only at the API level.

**Sprint:** 4 (deferred — value increases once audio lands, but technically runnable from end of Sprint 3)
**Depends on:** Sprint 3 complete (and 9.19 if audio coverage included)
**Source:** Research §Implementation Approaches → Testing and Quality Assurance (Browser E2E row); existing user feedback `feedback_browser_validation.md`
**Risks:** R4 (Open WebUI tool-call streaming bug — surfaces here if not already)

**Acceptance Criteria:**

**Given** the full hybrid-gemma stack is live on `ct-ai-01`
**When** I author Playwright MCP scenarios in `tests/e2e/playwright/hybrid-gemma/` covering: (a) text-only chat against `gemma4-26b-text`, (b) image-attached chat against `gemma4-auto` with visible italic status events, (c) image + question that should provoke an `analyze_image` tool call, (d) audio-attached chat (if Story 9.19 done), (e) model-picker contains all three aliases, (f) streaming visibility (tokens appear progressively, not all at once at end)
**Then** the suite runs from the AI dev container against `ct-ai-01` via Tailscale and all scenarios pass
**And** screenshots / DOM snapshots are captured at key checkpoints for visual diff regression
**And** the suite is documented in `homelab-playbook/docs/runbooks/hybrid-gemma-e2e-tests.md` with run instructions

### Story 9.21: Soak test (1 hour continuous) for memory stability

As a homelab operator,
I want a 1-hour soak test continuously hitting the `gemma4-auto` endpoint with mixed text/image/tool-call prompts,
So that I can verify no memory leaks, no streaming hangs, no GPU-memory growth over time before declaring the epic done.

**Sprint:** 4 (deferred — but explicitly part of the epic-level success criteria)
**Depends on:** Sprint 3 complete (audio coverage added if 9.19 done)
**Source:** Research §Implementation Approaches → Testing and Quality Assurance (Soak row); §Success Metrics and KPIs (Reliability)
**Risks:** R6 (VRAM exhaustion under sustained load — this story IS the validation)

**Acceptance Criteria:**

**Given** the full hybrid-gemma stack is live and the LiteLLM Grafana dashboard from Story 9.17 is exporting metrics
**When** I run a `k6` (or `locust`) script against `ct-ai-01:4000` with: 60 minutes total duration, mixed prompt set (40% pure text, 40% image+text, 20% image+tool-definition), bounded concurrency at 4 (matches the proxy's `httpx max_connections`)
**Then** the script captures: requests completed, requests failed (with error categorization), p50/p95/p99 latency, total tokens generated, peak GPU memory observed (via `radeontop` or equivalent during the run)
**And** at the end of the run: GPU memory has not grown monotonically (within ~200 MB of baseline), proxy process RSS has not grown monotonically (within ~100 MB of baseline), no `systemd` restarts of any of the three services occurred, error rate < 1%, p95 first-token latency held within the success-metric budgets (≤300ms text, ≤2.5s multimodal)
**And** the report is committed to `homelab-playbook/_bmad-output/implementation-artifacts/sprint4-soak-2026-MM.md`
**And** if any threshold is breached, the deviation is investigated and either fixed or accepted with a written justification before declaring Sprint 4 (and therefore the epic) complete

---

## Final Validation

### Acceptance-Criteria Coverage Verification

The 10 research-doc acceptance criteria (research §Implementation Approaches → Testing and Quality Assurance) all map to at least one story:

| AC # | Story | Notes |
|---|---|---|
| AC-1 (text first-token ≤300ms) | 9.8, 9.21 | Validated in passthrough integration; soak-tested |
| AC-2 (E4B vision streaming) | 9.8 | Passthrough |
| AC-3 (auto image → describe → reason) | 9.9, 9.11 | Implemented in 9.9, end-to-end gate in 9.11 |
| AC-4 (tool-call agent loop) | 9.14, 9.15, 9.22 | Implementation + synthetic tests + Sprint 4 priority fix (Story 9.15 surfaced production regression) |
| AC-5 (status events visible) | 9.10, 9.20 | Implementation + browser E2E |
| AC-6 (concurrent requests) | 9.21 | Soak test |
| AC-7 (upstream timeout → OAI error) | 9.8 | Adapter error handling (implicit in passthrough story; should be made explicit if a separate sub-story is needed) |
| AC-8 (Open WebUI model picker) | 9.11, 9.17 | After proxy + after LiteLLM |
| AC-9 (LiteLLM auth + Prometheus) | 9.16, 9.17 | Auth in 16, Prometheus in 17 |
| AC-10 (proxy restart <5s downtime) | 9.17 | Validated post-LiteLLM deploy |

### Dependency Verification

- **Strict sequential dependency Sprint 1 → 2 → 3:** Sprint 2 cannot begin until Sprint 1's tool-call gate (Story 9.5) decides which reasoner is canonical, because the proxy and agent-loop work commit to that backend's behavior.
- **No forward dependencies within a sprint:** Stories within each sprint are sequential by depend-on.
- **Sprint 4 entirely gated on Story 9.18 trigger:** No work begins until either upstream stabilizes or a use case appears.

### Risk-Coverage Verification

Each risk in the research-doc risk register has at least one story that mitigates or measures it:

| Risk | Mitigated by |
|---|---|
| R1 (TrevorJS chat-template) | 9.5 (gate), 9.12 (locked schema), 9.15 (synthetic tests — surfaced regression), 9.22 (Sprint 4 priority fix) |
| R2 (LiteLLM PyPI compromise) | 9.16 (hash-pinned audited version) |
| R3 (llama.cpp Vulkan upgrade breaks) | 9.1 (verify), 9.4 (ct-dev-test first) |
| R4 (Open WebUI tool-call streaming bug #23066) | 9.13 (clean delta emission), 9.20 (browser E2E) |
| R5 (`input_audio` instability) | Sprint 4 deferral, 9.18 (tracking) |
| R6 (VRAM exhaustion) | 9.11 (verify on deploy), 9.21 (soak) |
| R7 (Tailscale outage) | 9.17 (LAN fallback documented) |
| R8 (LXC reboot loses warm KV cache) | Accepted; no story needed |
| R9 (reference template vulnerability) | 9.6 (adapt, don't copy verbatim) |
| R10 (Gemma 5 supersedes) | Architecture is model-agnostic; defaults swap suffices — accepted |

### Open Questions / Decisions Surfaced for Operator

1. ~~**Story 9.6 — repo location.**~~ **RESOLVED 2026-04-25:** Python source lives under `homelab-infra/ansible/roles/gemma-hybrid-proxy/files/` per architecture doc §Project Structure & Boundaries (matches the `ai-dev-omega-memory` precedent — Ansible role owns the Python source as `files/`).
2. **Story 9.7 — `capabilities` field is non-standard.** OpenAI's `/v1/models` doesn't define a `capabilities` array. Open WebUI may or may not honor it. If clients ignore it, that's fine (informational only); if Open WebUI uses it for client-side validation and rejects unknown capabilities, the story may need adjustment. Verify in Story 9.11 smoke test.
3. **Story 9.16 — `litellm_version` PIN.** Architecture ADR-011 pins `litellm==1.83.13` (or latest stable `1.83.x` at install time) with `--hash=sha256` verification. The operator must independently re-audit and confirm the post-March-2026 audited version is still current at deploy time.
4. **Story 9.17 — bearer key storage.** The story specifies the operator's bearer key is recorded only in the operator's password manager (not in git). This matches the existing security pattern but should be re-confirmed; if the operator wants the key stored in vault for IaC reproducibility, the story is one-line different.

### Deviations from Research Roadmap (and Why)

1. **New story 9.5 added to Sprint 1.** Research §Implementation Approaches → Implementation Roadmap → Sprint 1 lists T1.1–T1.7 ending at "Manual quality / tok/s tests on real prompts." The 50-prompt synthetic tool-call accuracy test is mentioned only in §Success Metrics and KPIs and §Risk Assessment (R1) but not as a Sprint 1 task. Per the user direction recorded 2026-04-25 (TrevorJS as primary reasoner, Unsloth as conditional fallback, gate must run early), the gate is elevated to a first-class Sprint 1 exit story. This is the most material deviation in this document.
2. **Sprint 2 split into 6 stories vs research's 9 tasks.** Research T2.1–T2.9 is condensed because several tasks naturally pair (e.g., scaffold + `/v1/models` are both ~half-day, but separating them was useful to make the dependency graph clearer; SSE streaming is folded into the passthrough story since they're the same code change; ct-dev-test deploy + ct-ai-01 deploy are folded into the role-creation story to keep the deploy gate together). Net effect: same scope, slightly fewer story boundaries.
3. **Sprint 3 tightened from 9 tasks to 6 stories.** Research's T3.5/T3.6/T3.7/T3.8 (LiteLLM deploy + Open WebUI config + Continue/Cursor/phone config + Prometheus/Grafana) are grouped into Stories 9.16 (LiteLLM gateway) + 9.17 (clients + observability) because they form one logical unit and splitting them would create awkward cross-story coupling. Soak test moved to Sprint 4 (Story 9.21) because it's a hardening task that fits more naturally there and isn't a Sprint 3 exit blocker.
4. **Sprint 4 explicitly marked deferred / out of MVP within the same epic.** The user prompt asked "does Sprint 4 belong as a separate epic?" — recommendation: keep in same epic, marked deferred. Rationale: (a) the work is small and contiguous, using the same artifacts; (b) no separate epic-level ceremony (planning, retro) is justified for 4 stories; (c) keeping it in this epic keeps the audit trail intact (Sprint 4 was in the original research roadmap, not a follow-up afterthought).

### Architecture Compliance Verification

- All new Ansible roles follow the existing `llama-server` role pattern (defaults, tasks, templates, handlers, verify.yml, meta) — Stories 9.3, 9.11, 9.16
- All systemd units use `Restart=on-failure` + `RestartSec=5` + `NoNewPrivileges=true` — Stories 9.3, 9.11, 9.16
- All secrets managed via Ansible Vault — Story 9.16 (master key)
- Loopback-only inter-service binding (`127.0.0.1`) — Stories 9.3, 9.11, 9.16
- Tailscale-only public exposure — Story 9.17 (matches existing phone-notifications policy)
- ct-dev-test → ct-ai-01 deployment flow — Stories 9.4, 9.11, 9.16 (matches `feedback_test_container.md`)
- Browser validation via Playwright MCP — Stories 9.11, 9.20 (matches `feedback_browser_validation.md`)
- Hash-pinned dependencies for supply-chain safety — Stories 9.6 (proxy), 9.16 (LiteLLM)
