---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7]
lastStep: 7
inputDocuments:
  - homelab-playbook/_bmad-output/planning-artifacts/research/technical-hybrid-gemma-serving-research-2026-04-25.md
  - homelab-playbook/_bmad-output/planning-artifacts/architecture.md
  - homelab-playbook/_bmad-output/planning-artifacts/prd.md
  - homelab-playbook/_bmad-output/planning-artifacts/prd-production-readiness.md
  - homelab-infra/ansible/roles/llama-server/defaults/main.yml
  - homelab-infra/ansible/roles/llama-server/templates/llama-server.service.j2
  - docs/architecture-homelab-infra.md
  - docs/architecture-homelab-apps.md
workflowType: 'architecture'
project_name: 'homelab — hybrid-gemma-serving'
user_name: 'tomamourette'
date: '2026-04-25'
parent_initiative: 'PVE3 + Local LLM (Epic 8 follow-on)'
---

# Architecture Decision Document — Hybrid Gemma Serving

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

**Source of truth for technical decisions:** `homelab-playbook/_bmad-output/planning-artifacts/research/technical-hybrid-gemma-serving-research-2026-04-25.md`

**User decision recorded 2026-04-25:** TrevorJS Q4_K_M chosen as primary reasoner (uncensored output prioritized over chat-template stability + tool-call reliability). Unsloth UD-Q5_K_M defined as conditional fallback if Sprint 1 tool-call accuracy gate fails (<90% schema-valid on 50 prompts).

---

## Project Context Analysis

### Requirements Overview

**Functional Requirements** (sourced from research §Implementation Approaches → Acceptance Criteria + §Architectural Patterns):

| Domain | FRs | Architectural Impact |
|---|---|---|
| Inference backends (FR1-FR3) | 3 | New `llama-server-26b` systemd unit on `:8081`; existing E4B unit on `:8080` retained; both Vulkan-built, both `127.0.0.1` bind |
| Orchestration proxy (FR4-FR9) | 6 | New FastAPI app exposing `/v1/chat/completions`, `/v1/models`, `/health`; hexagonal layout (`domain/`, `adapters/`, `api/`); SSE streaming; bounded concurrency |
| Multimodal routing (FR10-FR12) | 3 | Content sniffer detects `image_url` / `input_audio` blocks; deterministic preprocessing through E4B; description injection into 26B reasoning context |
| Tool-call agent loop (FR13-FR15) | 3 | `analyze_image` and (deferred) `transcribe_audio` tool definitions; OpenAI streaming delta accumulation; intercept-execute-resume loop |
| API gateway (FR16-FR19) | 4 | LiteLLM proxy on `:4000`; virtual key auth; Prometheus metrics; rate limit; model-name aggregation |
| Client integration (FR20-FR22) | 3 | Open WebUI repointed at LiteLLM; Continue/Cursor/mobile/scripts use bearer token; three virtual model aliases visible across all clients |
| Operational guardrails (FR23-FR28) | 6 | systemd `Restart=on-failure`; structured JSON logs with request ID propagation; `/health` rollup; `NoNewPrivileges`; `ProtectSystem=strict` |
| Configuration management (FR29-FR31) | 3 | New Ansible roles `llama-server-26b`, `gemma-hybrid-proxy`, `litellm-gateway` matching existing role patterns; secrets in Ansible Vault |

**Non-Functional Requirements:**

| Category | Key Constraints |
|---|---|
| Reliability | 99% uptime over rolling 30 days; `Restart=on-failure` with `RestartSec=5s`; ~~`WatchdogSec=30s` for proxy~~ (CORRECTED 2026-04-25 Story 9.11: removed — uvicorn doesn't implement `sd_notify` so the watchdog killed the process every 30s; rely on `/health` external probe + `Restart=on-failure` instead); both backends always-warm |
| Security | Tailscale-only public exposure; LiteLLM bearer-token auth; **LiteLLM version+hash pinned** post-March-2026 advisory; loopback-only inter-service; vault-encrypted secrets; no PII/secrets in logs |
| Performance | Pure-text first-token ≤300ms; multimodal first-token ≤2.5s; 26B sustained decode ≥18 tok/s; tool-call iteration +1.5s budget; bounded `httpx` concurrency (max_connections=4 per upstream) |
| Capacity | 26B Q4_K_M (~16.8 GB) + E4B Q5_K_P+mmproj (~7 GB) = ~24 GB resident in 32 GB dedicated VRAM; 32 GB GTT as KV/headroom; 32K context default |
| Observability | LiteLLM Prometheus exporter; structured logs with request IDs; latency budgets per upstream documented |
| Compatibility | OpenAI `/v1/chat/completions` contract fidelity; SSE streaming with keep-alive comments; `image_url` (base64 + URL) + `input_audio` (deferred) content blocks; tool_calls streaming deltas |

**Scale & Complexity:**

- **3 new systemd units** (llama-server-26b, gemma-hybrid-proxy, litellm-gateway) on a single LXC
- **3 new Ansible roles** following the existing `llama-server` pattern
- **~300 LOC Python** in the FastAPI orchestration proxy (hexagonal layout, ≤150 LOC per module)
- **1 new model artifact** to download (TrevorJS Q4_K_M, ~16.8 GB) + chat template override
- **2 secondary artifacts** (Unsloth fallback model + mmproj if Sprint 1 gate fails)
- **No multi-tenancy**, no horizontal scaling, no cluster
- **Multi-client consumer surface** via single endpoint (Open WebUI, IDE plugins, mobile, CLI scripts)

### Project Scale Assessment

**Complexity Indicators:**

| Indicator | Status | Implication |
|---|---|---|
| Real-time features | ✅ (streaming SSE inference) | Streaming pass-through, no buffering, keep-alive comments needed |
| Multi-tenancy | ❌ (single user) | No per-tenant isolation; one bearer key tier |
| Regulatory compliance | ❌ (homelab) | No HIPAA/PCI/GDPR; standard secret hygiene only |
| Integration complexity | MEDIUM | LiteLLM ↔ FastAPI ↔ 2x llama-server; OpenAI contract fidelity is the key risk |
| User interaction complexity | LOW | Multi-app but consume same OpenAI-style API |
| Data complexity & volume | LOW | Stateless proxy; no DB beyond LiteLLM SQLite for logs |
| **Net complexity** | **MEDIUM** | Single-host orchestrator with deterministic routing + agent loop |

### Architectural Implications Summary

- **No frontend/UX work in scope** (Open WebUI is reused as-is, just repointed). Architecture workflow can skip UX-related decisions.
- **Pattern source already exists** in the homelab: the existing `llama-server` Ansible role is the direct template; the new orchestration proxy is the genuinely new build.
- **The "hard" decisions are protocol-level**: SSE streaming through an agent loop, OpenAI tool_call delta accumulation, content-block routing — these are where AI agents implementing this could make divergent choices (Step 5 territory).
- **No greenfield language/framework decision needed**: Python + FastAPI + httpx + sse-starlette + pydantic is locked by the proxy reference implementations and matches the homelab's existing Python tooling.
- **The architectural risk is concentrated in tool-call reliability on the abliterated TrevorJS variant** — explicit Sprint 1 measurement gate handles this.

---

## Starter Template Evaluation

This initiative spans four runtime components. Each gets evaluated against starter templates separately rather than picking one umbrella template, because the components have different maturity levels and different risk profiles.

### Inference Layer — Reuse `homelab-infra/ansible/roles/llama-server`

**Verdict: ADOPT EXISTING ROLE AS THE TEMPLATE; CLONE-AND-ADAPT FOR THE 26B VARIANT.**

The existing `llama-server` role (`homelab-infra/ansible/roles/llama-server/`) is the right starting point because:

- **Vulkan build path already validated.** `defaults/main.yml` sets `llama_cpp_vulkan: true` and ships the correct Debian build deps (`libvulkan-dev`, `glslc`, `spirv-headers`, `spirv-tools`). This sidesteps the ROCm bug (research §Tech Stack Gotcha #1).
- **Parameterized systemd template proven.** `templates/llama-server.service.j2` already handles model-file, mmproj, host/port, GPU layers, jinja, context size — exactly the variables we need to flex for the 26B variant (no mmproj, custom chat-template-file, different port/model).
- **Vault integration in place.** Surrounding playbook structure already wires Ansible Vault for HF tokens and other secrets.

The new `llama-server-26b` role is a structural clone with different defaults plus one additional parameter (`--chat-template-file`). Do NOT copy-paste the role; instead either (a) parameterize the existing role with `model_id` and instantiate it twice, OR (b) create a sibling role and accept the duplication. Recommendation: **(b) sibling role** — the configurations diverge in enough places (chat template, batch size, context, no mmproj) that parameterization risks coupling future E4B-only changes to 26B-only changes. Keep them independently shippable.

### Orchestration Proxy — Pattern-clone, do NOT fork

**Verdict: STUDY REFERENCE TEMPLATES, WRITE FRESH IN HEXAGONAL LAYOUT.**

The reference repos identified in research §Implementation are pattern teachers, not codebases to fork:

| Reference | What to learn from it | What NOT to take |
|---|---|---|
| `talesmousinho/fastapi-openai-sse-stream` | SSE forwarding pattern; `sse-starlette` usage; chunk loop shape | Project structure (flat, not hexagonal); error handling (minimal) |
| `AlirezaAzadbakht/minimal-fastapi-openai-proxy` | OpenAI request/response Pydantic models; `/v1/models` enumeration pattern; bearer token middleware | Multi-tenancy abstractions (we are single-tenant) |
| `ahmad2b/openai-agents-streaming-api` | Tool-call delta accumulation; intercept-execute-resume loop; status-event injection | OpenAI SDK coupling; agent framework wrappers |
| `Multimodal Reasoning Pipe V1` (Open WebUI) | Describe-then-reason flow logic | Pipe API surface (we expose OpenAI directly, not Pipe) |

Forking any of these creates ongoing drift cost and pulls in MIT-licensed code we then have to track. Cleaner: cherry-pick the specific patterns into a hexagonal layout (see §Project Structure & Boundaries) under our own license.

**Pinned versions (verified on PyPI, 2026-04-25):**

| Package | Pinned Version | Released | Why this version |
|---|---|---|---|
| `fastapi` | `==0.136.1` | 2026-04-23 | Latest stable; explicit SSE support added in 0.136 series |
| `httpx` | `==0.28.1` | 2024-12-06 | Last stable; no 2026 release yet — stable enough |
| `sse-starlette` | `==3.2.0` | 2026-03-29 | Latest stable; matches Starlette 0.4x |
| `pydantic` | `==2.13.3` | 2026-04-20 | Latest v2; required for strict mode + JSON Schema 2020-12 |
| `uvicorn` | `==0.46.0` | 2026-04-23 | Latest stable; required for FastAPI 0.136 compatibility |
| `structlog` | `==25.4.0` (or current) | — | Standard structured logging; not load-bearing, follow latest |
| `pytest` | `==8.x` | — | Test runner; use latest minor at lock time |
| `pytest-asyncio` | `==0.x` | — | Test runner; use latest minor at lock time |

All pins go into `requirements.txt` with `--hash=sha256:...` entries generated via `uv pip compile --generate-hashes`. The Ansible role MUST install with `uv pip install --require-hashes`. Renovate/Dependabot may file PRs to bump, but bumps require manual review.

### LiteLLM — Pin exact post-incident version + hash

**Verdict: PIN `litellm==1.83.13` (or latest stable in `1.83.x` series at install time), with SHA-256 hash verification.**

Per the [LiteLLM March 2026 security advisory](https://docs.litellm.ai/blog/security-update-march-2026) and [PyPI incident report](https://blog.pypi.org/posts/2026-04-02-incident-report-litellm-telnyx-supply-chain-attack/):

- Compromised versions: `1.82.7` and `1.82.8` (live ~40 minutes on PyPI 2026-03-24, downloaded 119k+ times).
- **Audited safe**: every release in the `1.78.0` through `1.82.6` range plus the new `1.83.x` series produced by the rebuilt CI/CD v2 pipeline.
- Latest as of 2026-04-25: `1.83.13`.

Pin choice: **`litellm==1.83.13`** with `--hash=sha256:...` constraint in `requirements.txt`. Re-evaluate quarterly; manual review before bumps. Document the chosen version + hash in the Ansible role defaults so it's audit-traceable.

### Open WebUI — No code change

**Verdict: REUSE EXISTING DOCKER STACK; CHANGE ONLY THE `OPENAI_API_BASE_URLS` ENV.**

Existing Open WebUI container is in `homelab-apps/stacks/` and already speaks OpenAI-compatible. Only operation: update its `OPENAI_API_BASE_URLS` to point at `http://ct-ai-01.tailnet:4000/v1` (LiteLLM) instead of the direct llama-server. No image change, no compose-file restructure beyond that env var.

---

## Core Architectural Decisions

The decisions below SUPERSEDE the implicit ADRs in research §Architectural Patterns and incorporate the user decision recorded 2026-04-25 (TrevorJS over Unsloth as primary).

Each ADR follows: **Status** | **Context** | **Decision** | **Consequences (positive + negative)** | **References**.

### ADR-001 — Vulkan/RADV backend mandatory

- **Status:** Accepted
- **Context:** ROCm has a confirmed endless-loop bug on `gemma-4-26B-A4B` for gfx1151 (Strix-class iGPU), producing garbage output (`<|channel><unused24>...`).
- **Decision:** Build llama.cpp with `-DGGML_VULKAN=ON` only; use Mesa RADV driver, not AMDVLK. Existing `llama-server` role default `llama_cpp_vulkan: true` is correct; the new `llama-server-26b` role inherits this.
- **Consequences:**
  - (+) Sidesteps the bug; matches benchmarked-good path on Radeon 880M class.
  - (+) Single backend across both `llama-server` instances simplifies ops.
  - (−) Vulkan is occasionally slower on certain ops than ROCm on other AMD GPUs; not relevant for Strix where ROCm is broken anyway.
- **References:** [llama.cpp #21416](https://github.com/ggml-org/llama.cpp/issues/21416), [llm-tracker Strix Halo notes](https://llm-tracker.info/_TOORG/Strix-Halo).

### ADR-002 — TrevorJS Q4_K_M as primary 26B reasoner; Unsloth UD-Q5_K_M as conditional fallback

- **Status:** Accepted (user decision 2026-04-25)
- **Context:** TrevorJS provides an abliterated (uncensored) Gemma 4 26B-A4B at Q4_K_M (16.8 GB) with no Q5+ ladder. Unsloth provides the official quant ladder (UD-Q4_K_M through UD-Q6_K) with chat-template stability and unverified — likely better — tool-call reliability. User prioritizes uncensored output.
- **Decision:** Run TrevorJS Q4_K_M as the canonical reasoner behind `gemma4-auto` and `gemma4-26b-text`. Define a Sprint 1 acceptance gate: tool-call accuracy ≥90% schema-valid on a 50-prompt evaluation set. **If gate fails, activate Unsloth UD-Q5_K_M as a parallel reasoner exposed as alias `gemma4-26b-text-strict`**, keeping TrevorJS for paths that genuinely need uncensored output.
- **Consequences:**
  - (+) Uncensored reasoning available across all client paths.
  - (−) Lower quant tier than memory budget allows (Q4 vs Q5).
  - (−) Requires chat-template override (ADR-003); unmeasured tool-call reliability risk.
  - (−) Sprint 1 gate adds measurement work and a contingency model download.
- **References:** [TrevorJS HF page](https://huggingface.co/TrevorJS/gemma-4-26B-A4B-it-uncensored-GGUF), [Unsloth gemma-4-26B-A4B-it-GGUF](https://huggingface.co/unsloth/gemma-4-26B-A4B-it-GGUF), research §Quantization Options for 26B-A4B.

**Addendum — Sprint 1 Gate Decision Tree (added 2026-04-25 per user feedback)**

The original ADR-002 specified a binary fallback (replace TrevorJS with Unsloth on tool-call test failure). Per user feedback, this is refined to a three-tier decision tree based on measured pass rate from the Story 9.5 test harness:

- **≥90% PASS** → no action; TrevorJS continues as sole reasoner
- **70-89% MARGINAL** → parallel deploy: TrevorJS for uncensored chat (`gemma4-26b-text`), Unsloth UD-Q5_K_M for strict tool-call paths (`gemma4-26b-text-strict` + `gemma4-auto` agent-loop traffic)
- **<70% FAIL** → replace: Unsloth becomes primary for tool-call paths; TrevorJS retained only as `gemma4-26b-uncensored` alias

The MARGINAL tier preserves the user's uncensored-chat choice while routing the more-demanding agent-loop traffic to the more-reliable model. Combined VRAM footprint of TrevorJS Q4_K_M (16.8 GB) + Unsloth UD-Q5_K_M (21 GB) + E4B (7 GB) = ~45 GB, exceeding 32 GB dedicated VRAM — relies on GTT spillover (32 GB available). Validate at deploy time; if perf degrades unacceptably, downgrade to FAIL action.

**Addendum — Sprint 1 Gate Outcome (recorded 2026-04-25)**

| Field | Value |
|---|---|
| Tier | **PASS** |
| Pass rate | **98.0%** (49/50 prompts) |
| Test harness | `homelab-infra/tests/sprint1_toolcall_gate.py` (979 LOC, stdlib-only) |
| Results report | `_bmad-output/implementation-artifacts/sprint1-toolcall-gate-results-2026-04-25.md` |
| Per-category | single-tool 20/20 · multi-tool 15/15 · parallel 5/5 · error-recovery 5/5 · negative 4/5 |
| Single failure | `negative-02` ("What is 2 plus 2?") — model emitted `calculate(2+2)` instead of answering directly. Negligible severity; clean schema, just over-eager intent. |
| Action | **None.** TrevorJS Q4_K_M continues as sole reasoner across all aliases. Unsloth UD-Q5_K_M is NOT deployed. |
| R1 status | **CLOSED** — chat-template fix (asf0/gemma4_jinja) is working end-to-end; zero `reasoning_content` leakage observed across all 50 prompts. |
| Discovered constraint | Model emits **sequential** tool calls, NOT parallel batches, on parallel-conceptual prompts. Sprint 2 orchestration loop (Story 9.13/9.14) must NOT assume parallel batching. |

**Addendum — Sprint 3 Story 9.15 surfaced a regression the Sprint 1 gate missed (recorded 2026-04-25)**

| Field | Value |
|---|---|
| Symptom | `gemma4-auto` requests with images + tool definitions: model emits tool calls as **plain text** in `delta.content` (e.g. `<\|tool_call\|>call:analyze_image{question:...}<tool_call\|>`) instead of structured `delta.tool_calls`. Agent loop never fires (0 `agent_loop.tool_iteration` log entries across 837s of production traffic). |
| Test that caught it | `homelab-infra/tests/sprint3_agentloop_smoke.py` — 25-prompt suite hitting the **production proxy** at `:8000` via `gemma4-auto` (with image preprocess + auto-injected `analyze_image` tool). Score: 12/25 (48%). Tool-triggering category 0/10. Multi-iteration 0/3. |
| Why Sprint 1 (Story 9.5) missed it | 9.5 hit `:8081` directly with raw test-defined tools and tiny prompt context. 9.15 hits the FULL proxy compose flow (image preprocess → augmented tools → larger context). The compose flow surfaces the regression; the bare flow doesn't. **Lesson: gate tests must exercise the production-shaped request path, not the raw upstream.** |
| Confirmed reproducibility | An exact prompt that succeeded in Story 9.14's live smoke 2h prior re-ran post-9.15 returns the same plain-text tool-call format. Not a harness bug; current production behavior. |
| Action taken | NONE in Sprint 3. Per user decision (Option B), MVP ships with text + passive-image modes working (5/5 + 5/5 = 100% in 9.15). Agent-loop gap is documented as Sprint 4 priority story 9.22 (NOT deferred — must complete before MVP feature-complete). |
| 4 hypotheses to test in 9.22 | (1) `gemma4-asf0.jinja` template doesn't structurally parse the model's tool-call output under proxy compose flow with augmented tools + image-description context. (2) `--jinja` flag interaction with augmented tool list. (3) System prompt for `gemma4-auto` not strong enough about structured tool use; tighten to explicitly require `tool_calls` field. (4) Switch agent-loop reasoner to **Unsloth UD-Q5_K_M** (the conditional fallback this addendum's "PASS" verdict said we wouldn't need). |
| Mitigation for users in the meantime | Use `gemma4-26b-text` or `gemma4-e4b-vision` aliases (both 100% reliable in 9.15). `gemma4-auto` still works for text + passive image; just avoid prompts that require deep-vision tool re-querying until 9.22 lands. |

- **Status:** Accepted
- **Context:** TrevorJS GGUFs ship with an outdated `gemma4` chat template; outputs land in `reasoning_content` while OpenAI `content` stays empty, plus tool calls get mangled. llama.cpp logs `"detected an outdated gemma4 chat template"` at startup.
- **Decision:** Override at server start via `--chat-template-file /var/lib/ollama/models/llama-models/gemma4-asf0.jinja`. The Ansible role downloads the template alongside the model (using `ansible.builtin.get_url`, matching the existing `llama-server` role's mmproj download pattern). Storage path corrected 2026-04-25 from `/opt/llama-models` to `/var/lib/ollama/models/llama-models` to use the existing `hdd-pool/models` ZFS dataset (80 TB) since rootfs (~36 GB free) cannot accommodate the 16.8 GB GGUF without violating the >20 GB headroom guardrail.
- **Consequences:**
  - (+) Fixes content/reasoning_content split; tool calls round-trip cleanly.
  - (−) HF discussion #2 reporter notes the fix is "incomplete" — verify in Sprint 1 against the tool-call gate (ADR-002).
  - (−) Ties us to a third-party Jinja file; pin commit SHA, monitor for upstream movement.
- **References:** [TrevorJS HF discussion #2](https://huggingface.co/TrevorJS/gemma-4-26B-A4B-it-uncensored-GGUF/discussions/2), [asf0/gemma4_jinja](https://github.com/asf0/gemma4_jinja).

### ADR-004 — Hybrid preprocessor + single-threaded master loop with modality cascade

- **Status:** Accepted
- **Context:** Routing options: pure preprocessor (deterministic fan-out), pure tool-call agent loop (LLM-judgment fan-out), LLM-as-router (third LLM for routing decisions). Anthropic explicitly advises against multi-agent orchestration for predictable workflows. 2026 cascade-routing research supports modality-driven (not confidence-driven) cascades.
- **Decision:** Modality detection in the proxy ALWAYS runs deterministically (no LLM). Image/audio content blocks ALWAYS preprocess through E4B → text. The 26B reasoner runs in a single-threaded master loop and may emit `analyze_image` tool calls to re-query E4B for specifics.
- **Consequences:**
  - (+) Deterministic routing; no LLM-judgment variance to debug.
  - (+) Pure-text requests have ~zero proxy overhead.
  - (+) Tool-call loop preserves cascade-routing benefit for follow-up queries.
  - (−) E4B preprocess adds ~1.5s to first multimodal token regardless of whether reasoner needed visual detail.
- **References:** [Building Effective AI Agents — Anthropic](https://resources.anthropic.com/building-effective-ai-agents), [Anthropic Claude Code single-threaded master loop](https://www.zenml.io/llmops-database/claude-code-agent-architecture-single-threaded-master-loop-for-autonomous-coding), [arXiv: Unified Routing and Cascading 2410](https://arxiv.org/html/2410.10347v1), research §Architectural Patterns and Design.

### ADR-005 — Two-layer proxy: LiteLLM outer gateway + custom FastAPI inner router

- **Status:** Accepted
- **Context:** LiteLLM provides auth, virtual keys, rate limiting, Prometheus, `/v1/models` aggregation out-of-box but cannot chain calls (await Model A → call Model B). Custom FastAPI is required for the orchestration logic. Putting auth in FastAPI duplicates LiteLLM's value; putting orchestration in LiteLLM is impossible.
- **Decision:** Build vs buy split: LiteLLM `:4000` for cross-cutting concerns; custom FastAPI `:8000` for orchestration. LiteLLM forwards to FastAPI as an `openai/<model>` upstream over loopback.
- **Consequences:**
  - (+) ~50 lines of custom code saved per cross-cutting feature.
  - (+) Each layer is independently testable.
  - (−) Two services to supervise instead of one.
  - (−) LiteLLM may buffer or rewrite tool-call deltas in transit (research-flagged risk); needs verification in integration tests; if confirmed, may need to bypass LiteLLM for the `gemma4-auto` path and have FastAPI handle auth itself for that route.
- **References:** Research §Orchestration / Proxy Stack, [dev.to LLM gateway comparison](https://dev.to/varshithvhegde/top-5-llm-gateways-in-2026-a-deep-dive-comparison-for-production-teams-34d2).

### ADR-006 — Stateless proxy, client-owned conversation history

- **Status:** Accepted
- **Context:** OpenAI contract requires the client to send the full message array on every request. Adding server-side session state breaks the contract and invents an invalidation problem.
- **Decision:** No session storage. No DB beyond LiteLLM's SQLite (logs/keys only). `gemma-hybrid-proxy` is fully stateless; restart causes zero data loss.
- **Consequences:**
  - (+) Trivial restarts; no migrations; no state corruption.
  - (+) Horizontal scaling (if ever needed) is free.
  - (−) Re-sending full history on every turn inflates request size; acceptable on loopback.
- **References:** Research §Data Architecture Patterns.

### ADR-007 — Hexagonal / ports-and-adapters layout for FastAPI codebase

- **Status:** Accepted
- **Context:** The proxy has three concerns that should not entangle: domain logic (orchestration, content inspection, delta accumulation), I/O (HTTP to upstream llama-servers), API surface (FastAPI routes). Mixing these makes mocking impossible and tests slow.
- **Decision:** `domain/` (pure, ≤150 LOC per module, no I/O) → `adapters/` (HTTP I/O via `httpx`) → `api/` (FastAPI routes). Domain depends on adapter interfaces, not concrete classes.
- **Consequences:**
  - (+) Unit tests run in milliseconds with mocked adapters.
  - (+) Adding a new modality = new domain branch + new adapter, no API surface change.
  - (−) Slightly more file ceremony than a single-file FastAPI app; worth it for testability.
- **References:** Research §Design Principles and Best Practices.

### ADR-008 — Defer audio support to v2

- **Status:** Accepted
- **Context:** llama.cpp `input_audio` content blocks are highly experimental on Gemma 4 E4B; some 400 errors reported in [llama.cpp #21334](https://github.com/ggml-org/llama.cpp/discussions/21334).
- **Decision:** v1 ships vision + text only. Audio content blocks return a 415 Unsupported Media Type with a clear "audio support is on the v2 roadmap" message. Re-evaluate once llama.cpp audio path stabilizes (track #21334).
- **Consequences:**
  - (+) Removes a high-risk integration from the v1 critical path.
  - (+) Lets v1 ship sooner.
  - (−) Audio-capable clients (mobile speech-to-text) are blocked on v2.
- **References:** [llama.cpp #21334](https://github.com/ggml-org/llama.cpp/discussions/21334), research §Data Formats & Content Blocks.

### ADR-009 — All inter-service traffic on `127.0.0.1`

- **Status:** Accepted
- **Context:** All four services (E4B llama-server, 26B llama-server, FastAPI, LiteLLM) live on the same LXC. External clients reach LiteLLM via Tailscale. Defense in depth dictates that even within the LXC, inter-service ports should not be reachable from the LXC's other interfaces.
- **Decision:** Every llama-server, FastAPI, and LiteLLM-internal binds to `127.0.0.1` only. The only externally-exposed port is LiteLLM `:4000`, exposed only on the Tailscale interface.
- **Consequences:**
  - (+) Even an LXC-local exploit can't directly hit a llama-server.
  - (+) Consistent with the existing homelab pattern of "publish only what must be public."
  - (−) Local debugging (`curl` against backends) requires being on the LXC; acceptable.
  - (−) Existing `llama-server` currently binds `0.0.0.0` per defaults — must be re-bound to `127.0.0.1` as part of cutover.
- **References:** Research §Integration Security Patterns.

### ADR-010 — Tailscale-only external exposure

- **Status:** Accepted
- **Context:** Existing homelab policy (`feedback project_phone_notifications_tailscale.md`) is Tailscale-only for all phone-facing and personal services. Public DNS exposure is the explicit non-goal.
- **Decision:** LiteLLM `:4000` listens on the Tailscale interface only; no port-forward, no public DNS record, no Cloudflare Tunnel. All clients (Open WebUI on the LAN, IDE plugins, mobile, scripts) connect via the tailnet.
- **Consequences:**
  - (+) Matches established homelab convention.
  - (+) Removes a large attack surface for free.
  - (−) Off-tailnet access requires installing Tailscale on the client; already standard in this homelab.
- **References:** `~/.claude/projects/-home-developer-workspace-homelab/memory/project_phone_notifications_tailscale.md`, research §Integration Security Patterns.

### ADR-011 — LiteLLM version + hash pinning mandatory

- **Status:** Accepted
- **Context:** LiteLLM PyPI was compromised in March 2026 (`v1.82.7`/`v1.82.8` shipped a credential stealer; 119k+ downloads during the ~40-minute window). Audited-safe versions exist; new CI/CD v2 pipeline produces post-incident `1.83.x` releases.
- **Decision:** Pin `litellm==1.83.13` (or latest stable `1.83.x` at install time) with `--hash=sha256:...` in `requirements.txt`. Install via `uv pip install --require-hashes`. Bumps require manual review and re-verification of the audit chain.
- **Consequences:**
  - (+) Reproducible install; supply-chain compromise detected at install time.
  - (+) Audit-traceable version recorded in Ansible defaults.
  - (−) Manual bump cadence; Renovate/Dependabot only files PRs, doesn't auto-merge.
- **References:** [LiteLLM Mar 2026 advisory](https://docs.litellm.ai/blog/security-update-march-2026), [PyPI incident report](https://blog.pypi.org/posts/2026-04-02-incident-report-litellm-telnyx-supply-chain-attack/), [Snyk analysis](https://snyk.io/blog/poisoned-security-scanner-backdooring-litellm/).

### ADR-012 — Stream-only through the agent loop; status events as italic delta.content chunks

- **Status:** Accepted
- **Context:** Buffering an agent-loop response until completion defeats SSE; clients see no progress for many seconds. OpenAI clients render `delta.content` markdown. Custom event channels (`event:` SSE fields outside `data:`) are ignored by most non-Vercel clients.
- **Decision:** Always stream. During the inner loop (E4B describe → 26B reason → tool call → re-issue), emit synthetic `chat.completion.chunk` frames with `delta.content` containing italic markdown status (e.g., `"\n_[describing image...]_\n"`). Final answer chunks come from the live 26B stream verbatim.
- **Consequences:**
  - (+) Universal client compatibility (renders as text in any OpenAI client).
  - (+) User sees real-time progress through the multi-step orchestration.
  - (−) Status text appears in transcript; clients that want to strip it must do so themselves (acceptable trade-off).
- **References:** [OpenAI streaming events](https://developers.openai.com/api/reference/resources/chat/subresources/completions/streaming-events), research §Tool-Call Orchestration Pattern.

### ADR coherence note

ADRs 001–012 are mutually reinforcing: 001 (Vulkan) enables 002 (TrevorJS) via 003 (template fix); 004 (hybrid loop) drives 007 (hexagonal layout); 005 (two-layer proxy) is enforced by 009 (loopback) and 010 (tailscale); 006 (stateless) and 012 (stream-only) preserve the OpenAI contract; 008 (defer audio) reduces v1 risk; 011 (LiteLLM pinning) hardens the supply chain. No two ADRs contradict; see §Architecture Validation for the explicit coherence check.

---

## Implementation Patterns & Consistency Rules

Patterns below close gaps where independent AI-agent implementations could legitimately diverge. Cite this section in story acceptance criteria.

### Naming conventions

| Surface | Convention | Examples |
|---|---|---|
| Virtual model aliases | kebab-case, family-suffix-detail | `gemma4-auto`, `gemma4-26b-text`, `gemma4-e4b-vision`, `gemma4-26b-text-strict` (fallback path) |
| Ansible role names | kebab-case, function-first | `llama-server-26b`, `gemma-hybrid-proxy`, `litellm-gateway` |
| systemd unit names | kebab-case, match Ansible role 1:1 | `llama-server-26b.service`, `gemma-hybrid-proxy.service`, `litellm-gateway.service` |
| Python module names | snake_case | `orchestrator.py`, `content_inspector.py`, `delta_accumulator.py`, `llama_server_client.py` |
| Python package | snake_case | `gemma_hybrid_proxy` |
| Tool function names (LLM-facing) | snake_case verbs | `analyze_image(image_id, question)` — and (deferred) `transcribe_audio(audio_id, language)` |
| Environment variables | UPPER_SNAKE_CASE, prefixed `GEMMA_HYBRID_` | `GEMMA_HYBRID_E4B_URL`, `GEMMA_HYBRID_MOE_URL`, `GEMMA_HYBRID_REQUEST_TIMEOUT_SECONDS`, `GEMMA_HYBRID_LOG_LEVEL` |
| LiteLLM env vars | UPPER_SNAKE_CASE, prefixed `LITELLM_` | `LITELLM_MASTER_KEY`, `LITELLM_DATABASE_URL` |
| HTTP request ID header | `X-Request-ID` | Mixed case per RFC convention; lowercase in code |

### API contract details

**SSE chunk format (mandatory shape):**

```
data: {"id":"chatcmpl-...","object":"chat.completion.chunk","created":...,"model":"gemma4-auto","choices":[{"index":0,"delta":{"content":"..."},"finish_reason":null}]}

data: [DONE]

```

- Each `data:` line followed by exactly one blank line.
- Stream terminator is literal `data: [DONE]` (no JSON wrapping).
- Keep-alive comment cadence: `: keepalive\n\n` every **15 seconds** while waiting on an upstream call (defeats nginx/Tailscale 60s default idle timeouts; reverse proxies in path must be configured for `proxy_read_timeout ≥600s`).
- Status event chunks (per ADR-012) use the same shape with `delta.content` containing markdown italic text.

**Error response shape (OpenAI envelope, mandatory):**

```json
{
  "error": {
    "message": "Upstream llama-server timeout after 30s",
    "type": "upstream_timeout",
    "param": null,
    "code": "gemma_hybrid.upstream.timeout"
  }
}
```

HTTP status mapping:

| Condition | Status | `error.type` | `error.code` |
|---|---|---|---|
| Upstream timeout | 502 | `upstream_timeout` | `gemma_hybrid.upstream.timeout` |
| Upstream 5xx | 502 | `upstream_error` | `gemma_hybrid.upstream.error` |
| Upstream 4xx (request shape) | 400 | `invalid_request_error` | `gemma_hybrid.request.invalid` |
| Audio content block | 415 | `unsupported_media_type` | `gemma_hybrid.modality.audio_unsupported` |
| Context window exceeded | 413 | `context_length_exceeded` | `gemma_hybrid.context.too_large` |
| Auth missing/invalid (LiteLLM) | 401 | `invalid_api_key` | `gemma_hybrid.auth.invalid_key` |
| Rate limit (LiteLLM) | 429 | `rate_limit_exceeded` | `gemma_hybrid.rate_limit.exceeded` |
| Internal | 500 | `internal_server_error` | `gemma_hybrid.internal` |

When streaming has begun and an upstream error occurs mid-stream, emit a final `data:` chunk with the OpenAI error envelope embedded in `choices[0].delta.content` as a clearly-marked block, then `data: [DONE]`. Do not silently truncate.

### Logging conventions

- Library: `structlog` configured for JSON output to stderr (journald captures).
- Mandatory fields on every log line: `timestamp` (ISO 8601 UTC), `level`, `event` (short snake_case), `request_id`, `service` (`gemma_hybrid_proxy` | `llama_server_e4b` | `llama_server_26b` | `litellm_gateway`).
- Per-upstream-call fields: `upstream` (`e4b` | `moe`), `duration_ms`, `status_code`, `model`, `content_block_types` (list), `tokens_in`, `tokens_out` (when known).
- Request ID: generated by LiteLLM if absent; propagated as `X-Request-ID` header on every loopback hop. FastAPI middleware reads/generates and binds to `structlog` contextvars at request start.
- **NEVER log:**
  - Raw image bytes or base64 data URLs (log only `content_block_types` summary)
  - Raw audio bytes (same)
  - Full prompt text from request bodies (log only first 64 chars + total length unless explicitly debug-flagged)
  - Bearer tokens, API keys, or any value sourced from Ansible Vault
  - Stack traces in production INFO+ logs (DEBUG only)

### Code structure rules

- All `domain/` modules ≤150 LOC.
- All `domain/` modules pure: no `httpx`, no file I/O, no env reads. Inputs in via function parameters; outputs out via return values or `AsyncIterator`.
- All adapter calls go through an interface defined in `domain/` and implemented in `adapters/`. Tests inject mock adapters.
- Pydantic v2 models with `model_config = ConfigDict(strict=True, extra="forbid")` for all public-API request models. Strict types prevent silent coercion.
- Async everywhere: `async def` at every layer; `httpx.AsyncClient` not `httpx.Client`. No sync I/O inside the event loop.
- Explicit timeouts on every upstream call: `httpx.Timeout(connect=2.0, read=30.0, write=10.0, pool=2.0)`. No defaults.
- `httpx.AsyncClient` configured per upstream with `limits=httpx.Limits(max_connections=4, max_keepalive_connections=4)`.

### Configuration rules

- All config via env vars; no hard-coded URLs/ports in code.
- Pydantic `BaseSettings` (`pydantic-settings` package) loads env at app start; rejects unknown env vars with `extra="forbid"`.
- Defaults sane for development (`http://127.0.0.1:8080` etc.); production overrides via systemd `EnvironmentFile=`.
- Env file path managed by Ansible role; rendered from `templates/env.j2` with vault-decrypted secrets.

### Tool-call schema rules

- JSON Schema dialect: `draft-07` (llama.cpp's grammar coercion is most stable here per its `--jinja` implementation).
- Required vs optional declared explicitly via `required: [...]`.
- Every parameter has a `description` written in plain English at sentence-level (not type-level) — these are read by the LLM, not by humans:

```json
{
  "name": "analyze_image",
  "description": "Ask a specific follow-up question about an image that was already shown. Use this when the initial description didn't cover the detail you need (e.g., specific text, axis labels, exact colors).",
  "parameters": {
    "type": "object",
    "properties": {
      "image_id": {
        "type": "string",
        "description": "The identifier of the image from the conversation, e.g. 'image-1'."
      },
      "question": {
        "type": "string",
        "description": "The specific question to ask about the image, in natural English."
      }
    },
    "required": ["image_id", "question"]
  }
}
```

### Error handling rules

- **Upstream timeout** → 502 with OpenAI-shaped error (see §API contract).
- **Tool execution failure** (E4B errored on `analyze_image`) → DO NOT fail the whole request. Inject a `tool` role message with `content: "Error: <short reason>"` and continue the master loop. The 26B reasoner gets a chance to respond conversationally.
- **Tool call max iterations** → cap at 5 iterations per request; on 6th, force `finish_reason=stop` with a status message. Prevents infinite loops on a misbehaving reasoner.
- **Content too large** (sum of message tokens > 26B context budget) → 413 with explicit message including the limit and the observed size; do NOT silently truncate.
- **Audio content block** (per ADR-008) → 415 immediately, before any upstream call.
- **Pydantic validation failure** on the request → 400 with the Pydantic error detail in OpenAI envelope.
- **Mid-stream upstream failure** → emit final error chunk + `[DONE]` (see §API contract).

---

## Project Structure & Boundaries

### Repository placement decision

**Question:** does the FastAPI proxy live under `homelab-infra/ansible/roles/gemma-hybrid-proxy/files/` (single-repo, Ansible-deployed) or as a sibling Python project under `homelab-apps/gemma-hybrid-proxy/` (separate project, Ansible references built artifact)?

**Survey of existing convention:**

- `homelab-apps/` is organized around **Docker Compose stacks** (`stacks/authelia`, `stacks/media-jellyfin`, etc.) plus utility scripts (`scripts/xtream-to-m3u.py`). It is NOT structured for first-party Python applications.
- `homelab-infra/ansible/roles/` includes both pure-config roles (`pve-host`, `apt-check`) and roles that deliver application code (e.g., `ai-dev-omega-memory` keeps Python under `files/`). The pattern of "Ansible role owns the Python source as `files/`" is established.
- No existing first-party Python service in the homelab is split across two repos.

**Decision:** **Python source lives under `homelab-infra/ansible/roles/gemma-hybrid-proxy/files/` (single-repo).** Rationale: matches `ai-dev-omega-memory` precedent, avoids creating an unprecedented `homelab-apps/<python-app>/` layout, keeps one PR-per-change instead of two, and removes the build-artifact-publishing problem (no need to publish a wheel to a registry). If the proxy outgrows ~1500 LOC or attracts non-homelab consumers, revisit and split into a sibling repo at that point.

### Concrete directory tree

```
homelab-infra/ansible/roles/
├── llama-server-26b/
│   ├── defaults/main.yml                # ports, model paths, batch size, context size, chat template path
│   ├── tasks/main.yml                   # download model + chat template, render unit, enable+start
│   ├── templates/llama-server-26b.service.j2
│   └── handlers/main.yml                # restart on unit/template change
│
├── gemma-hybrid-proxy/
│   ├── defaults/main.yml                # listen host/port, upstream URLs, log level, request timeout
│   ├── tasks/main.yml                   # create user, create venv with uv, install --require-hashes,
│   │                                    # render env, render unit, enable+start
│   ├── files/                           # Python source tree (see expanded layout below)
│   │   ├── pyproject.toml
│   │   ├── requirements.txt             # PINNED + hashes (uv pip compile --generate-hashes)
│   │   ├── src/gemma_hybrid_proxy/
│   │   │   ├── __init__.py
│   │   │   ├── main.py                  # FastAPI app factory + uvicorn entry
│   │   │   ├── config.py                # pydantic-settings BaseSettings
│   │   │   ├── domain/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── orchestrator.py      # master loop (≤150 LOC)
│   │   │   │   ├── content_inspector.py # detect image_url / input_audio blocks
│   │   │   │   ├── tool_definitions.py  # analyze_image (+ transcribe_audio v2) JSON schemas
│   │   │   │   └── delta_accumulator.py # streaming tool_calls reassembly
│   │   │   ├── adapters/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── llama_server_client.py  # httpx.AsyncClient wrapper
│   │   │   │   └── openai_models.py     # Pydantic v2 OpenAI request/response models
│   │   │   └── api/
│   │   │       ├── __init__.py
│   │   │       ├── chat_completions.py  # POST /v1/chat/completions
│   │   │       ├── models.py            # GET /v1/models
│   │   │       └── health.py            # GET /health
│   │   └── tests/
│   │       ├── unit/                    # mocked adapters; ms-fast
│   │       └── integration/             # httpx.MockTransport simulating llama-server
│   ├── templates/
│   │   ├── gemma-hybrid-proxy.service.j2
│   │   └── env.j2                       # rendered with vault-decrypted secrets
│   └── handlers/main.yml
│
└── litellm-gateway/
    ├── defaults/main.yml                # version PIN + hash, port, db path
    ├── tasks/main.yml                   # install pinned litellm, render config + env + unit, enable+start
    ├── templates/
    │   ├── litellm-gateway.service.j2
    │   ├── config.yaml.j2               # model_list with 3 virtual aliases + master_key from env
    │   └── env.j2                       # LITELLM_MASTER_KEY, DATABASE_URL from vault
    └── handlers/main.yml

homelab-infra/ansible/playbooks/
└── ct-ai-01.yml                         # UPDATE: add llama-server-26b, gemma-hybrid-proxy, litellm-gateway role invocations
```

### Integration boundaries (contracts)

**Boundary 1: LiteLLM `:4000` ↔ FastAPI `:8000`**

- Transport: HTTP/1.1 over loopback `127.0.0.1`.
- Format: OpenAI `/v1/chat/completions` and `/v1/models` shape, byte-for-byte.
- Auth: LiteLLM strips client bearer; FastAPI accepts unauthenticated loopback (defense in depth via ADR-009 binding).
- Streaming: SSE pass-through; LiteLLM must NOT buffer (verify in integration tests; if it buffers tool-call deltas, route `gemma4-auto` direct to FastAPI).
- Headers: `X-Request-ID` propagated; LiteLLM generates if missing.

**Boundary 2: FastAPI `:8000` ↔ llama-server `:8080` (E4B) and `:8081` (26B)**

- Transport: HTTP/1.1 over loopback `127.0.0.1`.
- Format: OpenAI `/v1/chat/completions` shape.
- Streaming: SSE; FastAPI consumes via `httpx.AsyncClient.stream()`; passes deltas through.
- Concurrency: bounded per-upstream pool (max_connections=4).
- Timeouts: explicit on every call (`connect=2s`, `read=30s`).
- Headers: `X-Request-ID` propagated downstream so journald correlates llama-server log lines.

**Boundary 3: External clients ↔ LiteLLM `:4000` over Tailscale**

- Transport: HTTP/1.1 over Tailscale tailnet (Wireguard underneath).
- Auth: Bearer token (LiteLLM virtual key per client class).
- Format: OpenAI surface only; clients see no internal model split.
- Rate limit: LiteLLM per-key budget (liberal defaults; tightened later per-key as needed).

### systemd ordering

```
multi-user.target
   ↑
   ├── llama-server.service                 (existing E4B; After=network.target)
   ├── llama-server-26b.service             (After=network.target llama-server.service)
   ├── gemma-hybrid-proxy.service           (After=network.target llama-server.service llama-server-26b.service;
   │                                         Requires=llama-server.service llama-server-26b.service)
   └── litellm-gateway.service              (After=network.target gemma-hybrid-proxy.service;
                                             Requires=gemma-hybrid-proxy.service)
```

`Requires=` (not just `After=`) on the proxy's deps so a backend failure stops the proxy too — clear failure mode rather than serving 502s. ~~`WatchdogSec=30s` on the proxy with `sd_notify` heartbeats from `main.py`.~~ (CORRECTED 2026-04-25 Story 9.11: WatchdogSec removed — uvicorn doesn't ship `sd_notify` heartbeats; spurious kills observed. `Restart=on-failure` + external `/health` probe (LiteLLM/Prometheus in Sprint 3) provides equivalent liveness signal.)

### Cutover sequencing (deployment order, distinct from systemd ordering)

Per research §Technology Adoption Strategies (incremental, additive, reversible):

1. Deploy `llama-server-26b` role to `ct-dev-test` → verify direct `:8081` access; smoke chat + tool-call.
2. Deploy `gemma-hybrid-proxy` role to `ct-dev-test` (passthrough mode first: `gemma4-26b-text`, `gemma4-e4b-vision` only) → verify SSE pass-through.
3. Enable `gemma4-auto` orchestration on `ct-dev-test` → verify image describe + tool-call loop.
4. Deploy `litellm-gateway` role to `ct-dev-test` → verify auth + virtual keys.
5. Rebind existing E4B `llama-server` to `127.0.0.1` (ADR-009 enforcement) on `ct-dev-test` → verify nothing else breaks.
6. Repeat steps 1–5 on `ct-ai-01`.
7. Repoint Open WebUI `OPENAI_API_BASE_URLS` from direct E4B to LiteLLM `:4000`.

---

## Architecture Validation

### Coherence check across ADRs

| ADR pair | Interaction | Coherent? |
|---|---|---|
| 001 (Vulkan) ↔ 002 (TrevorJS Q4) | Vulkan is the only viable backend for the chosen 26B variant | ✅ |
| 002 (TrevorJS) ↔ 003 (template fix) | Template fix is the precondition for 002 to function correctly | ✅ |
| 002 (TrevorJS) ↔ Sprint 1 gate | ADR codifies the gate; ADR-002 fallback path covered | ✅ |
| 004 (hybrid loop) ↔ 005 (two-layer proxy) | Orchestration logic lives in the inner FastAPI; LiteLLM remains contract-thin | ✅ |
| 004 (hybrid loop) ↔ 007 (hexagonal) | Domain isolation enables the loop logic to be tested without I/O | ✅ |
| 005 (LiteLLM) ↔ 011 (LiteLLM pinning) | Adoption of LiteLLM is conditional on pinning + hash discipline | ✅ |
| 006 (stateless) ↔ 012 (stream-only) | Both preserve the OpenAI client contract | ✅ |
| 008 (defer audio) ↔ 004 (modality cascade) | Cascade has fewer branches in v1; v2 expansion via §Implementation Patterns | ✅ |
| 009 (loopback) ↔ 010 (Tailscale-only) | Both reduce attack surface; layered, no contradiction | ✅ |
| 011 (pin LiteLLM) ↔ 005 (LiteLLM upstream) | Pinning is the safety mechanism that makes 005 acceptable | ✅ |
| 012 (status events) ↔ 006 (stateless) | Status events are per-request; no state crosses requests | ✅ |

**No contradictions detected.** The 12 ADRs form a coherent system: hardware constraints (001) drive model choice (002+003); orchestration shape (004) drives codebase structure (007); defense in depth (009+010) wraps the build/buy split (005+011); contract preservation (006+012) keeps the API surface clean; risk reduction (008) shrinks v1 scope.

### Functional requirements coverage

| FR group (from §Project Context Analysis) | Architectural component | ADR coverage |
|---|---|---|
| FR1–FR3 (inference backends) | `llama-server` (E4B, existing) + `llama-server-26b` (new role) | 001, 002, 003, 009 |
| FR4–FR9 (orchestration proxy) | `gemma-hybrid-proxy` FastAPI hexagonal app | 004, 005, 006, 007, 012 |
| FR10–FR12 (multimodal routing) | `domain/content_inspector.py` + `domain/orchestrator.py` | 004, 008 |
| FR13–FR15 (tool-call agent loop) | `domain/tool_definitions.py` + `domain/delta_accumulator.py` + `domain/orchestrator.py` | 004, 012, error handling rules in §Implementation Patterns |
| FR16–FR19 (API gateway) | `litellm-gateway` role + LiteLLM `:4000` | 005, 010, 011 |
| FR20–FR22 (client integration) | Open WebUI repointing + virtual model aliases | 005 (model aggregation), §Naming conventions |
| FR23–FR28 (operational guardrails) | systemd hardening + structured logs + `/health` | §systemd ordering, §Logging conventions |
| FR29–FR31 (configuration management) | Three new Ansible roles + Ansible Vault | §Project Structure |

Every FR group traces to a specific component; no orphan requirements.

### Non-functional requirements coverage

| NFR | Architectural mechanism |
|---|---|
| **Reliability** (99% uptime, 30-day rolling) | systemd `Restart=on-failure` (note: WatchdogSec removed per Story 9.11 — uvicorn doesn't sd_notify; rely on `/health` external probe instead); both backends always-warm; `Requires=` chain stops proxy if backend fails (clean failure vs degraded service) |
| **Security — public exposure** | ADR-010 (Tailscale-only), no public DNS |
| **Security — auth** | LiteLLM virtual keys; ADR-009 loopback for inter-service |
| **Security — supply chain** | ADR-011 (LiteLLM pin + hash); `uv pip install --require-hashes` for all Python deps |
| **Security — secrets** | Ansible Vault (existing pattern); `EnvironmentFile=` for systemd; never logged (§Logging conventions) |
| **Security — model output leakage** | ADR-003 (chat template fix prevents `reasoning_content` exposure via OpenAI surface) |
| **Performance — first-token latency** | Pure-text path bypasses E4B (≤300ms goal); multimodal path adds one E4B describe (~1.5s, total ≤2.5s) |
| **Performance — sustained decode** | ADR-001 (Vulkan path benchmarked at ~21 tok/s on 880M-class) |
| **Performance — concurrency** | `httpx.Limits(max_connections=4)` per upstream prevents single client from starving others |
| **Capacity — VRAM** | TrevorJS Q4_K_M (~16.8 GB) + E4B Q5_K_P (~7 GB) = ~24 GB / 32 GB dedicated VRAM; 8 GB headroom + 32 GB GTT for KV |
| **Observability — metrics** | LiteLLM Prometheus exporter; existing Prometheus scrape pattern |
| **Observability — logs** | `structlog` JSON → journald → existing aggregation; `X-Request-ID` end-to-end |
| **Compatibility — OpenAI** | API contract details enforced in §API contract; integration tests against OpenAI SDK |

Every NFR has at least one explicit mechanism.

### Implementation readiness assessment

**Ready to implement?** YES, with three caveats listed under "Open questions" below.

The combined research doc + this architecture doc give an AI agent or developer enough decisions to build without divergent choices:

- Model files, paths, and quants are named explicitly.
- All ports, hosts, and binding policies are specified.
- All Python package versions are pinned.
- API contracts (request shape, error envelope, streaming format) are defined byte-level.
- Naming conventions cover every surface (env vars, modules, aliases, units).
- Directory structure is a concrete tree, not a description.
- Service ordering and cutover sequence are explicit.
- ADR coherence is verified and traced.

### Open questions to surface to the user

1. **LiteLLM streaming-passthrough behavior for tool-call deltas.** Research flagged this as a "verify in integration tests" item. If LiteLLM buffers or rewrites streamed `tool_calls` deltas, we need the `gemma4-auto` route to bypass LiteLLM, with FastAPI handling auth itself for that path (a meaningful complication). **Action requested:** OK to handle this as a Sprint 1 verification task, with a documented contingency design rather than choosing now?

2. **Renovate vs Dependabot vs manual bump cadence.** ADR-011 says manual review for LiteLLM bumps; unspecified for everything else. Existing homelab convention not visible in `homelab-infra/`. **Action requested:** which bot (if any) should track Python deps, and what cadence (weekly digest? monthly?) for non-LiteLLM deps?

3. **Dedicated user account for the proxy service.** systemd unit template references `User={{ proxy_user }}` but no decision recorded on whether to create `gemma-hybrid` system user vs reuse an existing account (e.g., `llama` if one exists). **Action requested:** create dedicated `gemma-hybrid` system user, or piggyback on existing? Recommend dedicated for blast-radius reasons.

These are the only material gaps; everything else is decided.
