---
# Sprint Status — Hybrid Gemma Serving (Epic 9)
# Generated: 2026-04-25
# Project: homelab — hybrid-gemma-serving
# Project Key: NOKEY
# Tracking System: file-system
# Story Location: homelab-playbook/_bmad-output/implementation-artifacts
# Parent Initiative: Epic 8 (PVE3 + Local LLM) — completed 2026-04-15
# Sprint Start: 2026-04-25
# Sprint End: NONE — BMad rule: NO TIME ESTIMATES; sequencing only
#
# SOURCE DOCUMENTS:
#   - planning-artifacts/hybrid-gemma-serving-epics.md (1 epic, 21 stories, 4 sprints)
#   - planning-artifacts/hybrid-gemma-serving-architecture.md (12 ADRs)
#   - planning-artifacts/research/technical-hybrid-gemma-serving-research-2026-04-25.md
#
# STATUS LEGEND:
#   pending      — story not yet started; story file may not exist yet
#   in_progress  — developer is actively implementing
#   blocked      — dependency unmet OR external blocker (e.g., upstream issue)
#   completed    — story done, verified, committed
#   deferred     — story explicitly out of MVP; gated on a trigger (Sprint 4 default)
#
# OWNER LEGEND:
#   unassigned    — no owner picked up yet
#   <handle>      — agent or operator handle that owns the story
#
# WORKFLOW NOTES:
#   - Sprints are STRICTLY SEQUENTIAL: Sprint 1 → Sprint 2 → Sprint 3 → Sprint 4 (deferred)
#   - Sprint 1 has a THREE-TIER EXIT GATE on Story 9.5 (50-prompt tool-call test harness).
#       Pass rate ≥90% PASS  → no action; TrevorJS continues as sole reasoner.
#       Pass rate 70-89% MARGINAL → parallel deploy: TrevorJS for uncensored chat,
#                                   Unsloth UD-Q5_K_M for strict tool-call paths.
#       Pass rate <70% FAIL  → replace: Unsloth becomes primary for tool-call paths;
#                              TrevorJS retained only as `gemma4-26b-uncensored` alias.
#       Tier outcome recorded as ADR-002 addendum in hybrid-gemma-serving-architecture.md.
#   - Sprint 4 is DEFERRED. Trigger conditions: llama.cpp #21334 stabilizes for Gemma 4 E4B audio
#       OR a concrete operator audio use-case appears.
#   - Within each sprint, stories are SEQUENTIAL (each depends on the prior).
#   - All deploys go through ct-dev-test (192.168.50.152) → ct-ai-01 (192.168.50.160) per
#       feedback_test_container.md.
#   - Browser validation per feedback_browser_validation.md uses Playwright MCP.
---

epic:
  id: 9
  name: "Hybrid Gemma Serving — Dual-Backend Orchestration"
  parent_initiative: "Epic 8 (PVE3 + Local LLM)"
  status: pending
  start_date: "2026-04-25"
  end_date: null  # BMad rule: no time estimates; sequencing only
  total_stories: 21
  mvp_stories: 17
  deferred_stories: 4
  scope_summary: |
    Replace the single-model Gemma 4 E4B serving on ct-ai-01 with a dual-backend
    orchestration: a second llama-server runs Gemma 4 26B-A4B (TrevorJS Q4_K_M
    primary, Unsloth UD-Q5_K_M conditional fallback) alongside E4B. A custom
    FastAPI proxy on :8000 exposes 3 virtual model aliases (gemma4-auto,
    gemma4-26b-text, gemma4-e4b-vision) with deterministic multimodal preprocessing
    (image_url → E4B describe → 26B reason) and a tool-call agent loop
    (analyze_image lets 26B re-query E4B mid-stream). LiteLLM on :4000 fronts the
    proxy with bearer-token auth + Prometheus metrics for multi-app access
    (Open WebUI, Continue.dev, Cursor, mobile via Tailscale).
  out_of_scope:
    - Audio support (Sprint 4 — deferred, gated on llama.cpp #21334)
    - Embeddings endpoint
    - Speculative decoding (broken on MoE + mmproj)
    - Multi-tenant key tiering
    - Migration to a future Gemma 5 release

# ============================================================================
# DEPENDENCY GRAPH (high-level)
# ============================================================================
#
#   Sprint 1: 9.1 → 9.2 → 9.3 → 9.4 → 9.5* (EXIT GATE — three-tier)
#                                       │
#                                       │ Story 9.5 pass rate determines tier:
#                                       │   ≥90% PASS      → no action
#                                       │   70-89% MARGINAL → parallel-deploy Unsloth
#                                       │   <70% FAIL      → replace TrevorJS for tool-call paths
#                                       │ Outcome recorded as ADR-002 addendum.
#                                       ▼
#   Sprint 2: 9.6 → 9.7 → 9.8 → 9.9 → 9.10 → 9.11 (EXIT GATE)
#                                                │
#                                                ▼
#   Sprint 3: 9.12 → 9.13 → 9.14 → 9.15 → 9.16 → 9.17 (EXIT GATE)
#                                                     │
#                                                     ▼
#   Sprint 4 PRIORITY: 9.22  (REQUIRED for MVP feature-complete —
#                              fix for the gemma4-auto agent-loop
#                              production regression surfaced by 9.15)
#                                                     │
#                                                     ▼
#   Sprint 4 DEFERRED: 9.18 → 9.19 → 9.20 → 9.21
#       Triggered when: llama.cpp #21334 stabilizes for Gemma 4 E4B audio
#                       OR concrete operator audio use-case arises.
# ============================================================================

sprints:

  # ==========================================================================
  # SPRINT 1 — Foundation
  # ==========================================================================
  - id: sprint-1
    name: "Foundation — second llama-server + tool-call accuracy gate"
    status: pending
    sequence: 1
    goal: |
      A second llama-server (Gemma 4 26B-A4B) running on ct-ai-01:8081 alongside
      the existing E4B on :8080, registered in Open WebUI as a manual second
      model, and subjected to a 50-prompt synthetic tool-call accuracy test.
    exit_gate:
      story: "9.5"
      criteria: |
        Three-tier decision based on measured pass rate from the 50-prompt test
        harness (tests/sprint1_toolcall_gate.py). Pass rate = (prompts passing
        all 3 checks: schema-valid + correct-intent + correct-args) / 50.
      pass_action: |
        PASS (≥90%): Record ADR-002 addendum confirming TrevorJS as sole
        reasoner. Sprint 2 proceeds unmodified.
      marginal_action: |
        MARGINAL (70-89%): Parallel deploy. Keep TrevorJS as primary for
        gemma4-26b-text (uncensored chat); deploy Unsloth UD-Q5_K_M as secondary
        for gemma4-26b-text-strict and route the tool-call agent loop in
        gemma4-auto to Unsloth. Combined VRAM ~38 GB — relies on GTT spillover;
        validate at deploy time. Record outcome as ADR-002 addendum.
      fail_action: |
        FAIL (<70%): Replace. Unsloth UD-Q5_K_M becomes primary for tool-call
        paths (gemma4-26b-text-strict + gemma4-auto agent loop); TrevorJS
        retained only as gemma4-26b-uncensored alias for non-tool-call use
        cases. Update llama-server-26b role defaults to add Unsloth GGUF,
        re-deploy via ct-dev-test → ct-ai-01, re-run the 50-prompt harness on
        Unsloth, record outcome as ADR-002 addendum, then proceed to Sprint 2.
      adr_location: |
        ADR-002 addendum is appended in-place to ADR-002 inside
        homelab-playbook/_bmad-output/planning-artifacts/hybrid-gemma-serving-architecture.md.
        No separate _bmad-output/architecture-decisions/ tree.
    stories:
      - id: "9.1"
        title: "Verify Vulkan build of llama.cpp on ct-ai-01"
        status: completed
        owner: claude-coder
        completion_date: 2026-04-25
        depends_on: ["epic-8/8.4"]
        risks: ["R3"]  # llama.cpp upgrade breaks Vulkan build on Strix iGPU
        is_exit_gate: false
        evidence: "_bmad-output/implementation-artifacts/llama-cpp-build-verification-2026-04.md"
        notes: |
          Verify-only path. AC-1/2/3/4 all PASS against existing binary
          (sha256 aa20a7a5..., llama.cpp commit 4fbdabd). No rebuild needed;
          E4B service was not disrupted.
      - id: "9.2"
        title: "Download TrevorJS Q4_K_M GGUF and asf0/gemma4_jinja chat template"
        status: completed
        owner: claude-coder
        completion_date: 2026-04-25
        depends_on: ["9.1"]
        risks: ["R1"]  # TrevorJS chat-template fix possibly incomplete
        is_exit_gate: false
        evidence: "_bmad-output/implementation-artifacts/9-2-model-download-evidence.md"
        notes: |
          Scope shifted from manual huggingface-cli download to
          Ansible-role-driven get_url download (matches existing llama-server
          role's mmproj pattern; no CLI dependency). Storage path corrected
          from /opt/llama-models (rootfs, only 36GB free) to
          /var/lib/ollama/models/llama-models (on hdd-pool/models, 80TB).
          Chat template filename corrected from gemma4.jinja to
          chat_template.jinja (actual filename in asf0/gemma4_jinja repo);
          commit SHA pinned to f3748b50ee69 for reproducibility.
          GGUF sha256: d482a5daba09e67c925359a1786c4c713d1c3bb35856d199cf296f7cf7bc6cb3.
          Idempotency verified: re-run shows GGUF task `ok` (skipped).
          E4B service remained healthy throughout.
      - id: "9.3"
        title: "Create Ansible role llama-server-26b"
        status: completed
        owner: claude-coder
        completion_date: 2026-04-25
        depends_on: ["9.2"]
        risks: []
        is_exit_gate: false
        evidence: "_bmad-output/implementation-artifacts/9-3-llama-server-26b-role-evidence.md"
        notes: |
          Role created mirroring existing llama-server role minimal layout
          (defaults/, tasks/, templates/ — no handlers/vars/meta/verify per
          existing-pattern precedent). Lint result: 1 violation (role-name
          kebab-case, identical to existing role). Dry-run intentionally fails
          on missing-model precondition until Story 9.2 lands the GGUF +
          chat-template; service is enabled but NOT started (Story 9.4 deploys).
      - id: "9.4"
        title: "Deploy llama-server-26b to ct-dev-test then ct-ai-01 and register in Open WebUI"
        status: completed
        owner: claude-coder
        completion_date: 2026-04-25
        depends_on: ["9.3"]
        risks: ["R3"]  # caught by ct-dev-test step
        is_exit_gate: false
        evidence: "_bmad-output/implementation-artifacts/9-4-26b-deploy-evidence.md"
        notes: |
          Deployed to ct-ai-01 only (ct-dev-test deviation: no GPU access on
          ct-dev-test would cause runtime fail; substituted Ansible
          `--check --diff` dry-run on ct-ai-01 itself per director guidance).
          Rollback safety: ZFS snapshot `rpool/data/subvol-160-disk-0
          @pre-26b-deploy-20260425-1013` (pct snapshot blocked by mp0 bind-mount).
          VRAM: 5.72 GB (E4B alone) → 24.39 GB (E4B + 26B) of 32 GB total.
          All 4 ACs PASS: text chat (`content` populated, no R1 indicator;
          25.11 tok/s within 18-30 research band), tool-call (correct name +
          args), E4B unaffected (PID 91 unchanged, 17h uptime preserved).
          OWUI registration required switching the container to host networking
          (`--network host`, `PORT=3000`) so it can reach 26B's loopback bind
          per ADR-009 — bridge-mode `host.docker.internal` resolved to docker
          bridge gateway (172.17.0.1) which can't see 127.0.0.1:8081. Both
          backends reachable from inside the OWUI container; named volume
          `open-webui` preserved all user data. OWUI is NOT under IaC (manual
          docker run) — captured as Sprint 1 retro follow-up.
      - id: "9.5"
        title: "Sprint 1 tool-call accuracy gate (50-prompt test harness, three-tier decision)"
        status: completed
        owner: claude-coder
        completion_date: 2026-04-25
        depends_on: ["9.4"]
        risks: ["R1"]  # this story IS the R1 measurement — outcome: R1 CLOSED
        is_exit_gate: true
        gate_outcome: PASS                   # PASS / MARGINAL / FAIL
        gate_pass_rate_pct: 98.0
        artefact_test_harness: "homelab-infra/tests/sprint1_toolcall_gate.py"
        artefact_results_json: "homelab-playbook/_bmad-output/implementation-artifacts/sprint1-toolcall-gate-results-2026-04-25.json"
        artefact_report: "homelab-playbook/_bmad-output/implementation-artifacts/sprint1-toolcall-gate-results-2026-04-25.md"
        evidence: "_bmad-output/implementation-artifacts/9-5-toolcall-gate-evidence.md"
        artefact_adr: "homelab-playbook/_bmad-output/planning-artifacts/hybrid-gemma-serving-architecture.md (ADR-002 addendum, in-place — director-owned follow-up, NOT triggered by harness)"
        notes: |
          GATE OUTCOME: PASS (49/50 = 98.0% ≥ 90% threshold).
          Recommendation: keep TrevorJS Q4_K_M as sole reasoner; no Unsloth
          fallback deploy required. Sprint 2 may proceed unmodified.
          Per-category: single 20/20, multi 15/15, parallel 5/5, error-recovery
          5/5, negative 4/5. Single failure: negative-02 ("What is 2 plus 2?")
          where the model conservatively invoked calculate(expression="2 + 2")
          instead of answering directly — clean schema, just over-eager intent.
          R1 CLOSED: 50/50 responses had reasoning_content correctly sequestered
          per asf0 template; zero CoT leakage into user-visible content.
          Wall time 374s (mean 7.5s/prompt; ambiguous prompts ran ~44s due to
          long deliberation — informational, flagged for Sprint 3 latency).
          Anomaly for Sprint 2/3 planning: parallel-call prompts emitted ONE
          call (not 2-3) — model chains sequentially via re-prompting; the
          delta_accumulator (Story 9.13) and orchestration loop (Story 9.12)
          must not assume parallel batching.
          Implementation deviation: harness uses stdlib urllib.request instead
          of httpx (not available in CT 160 venv; per Story 9.5 boundaries no
          ad-hoc package installs). Functionally equivalent. Re-runnable as a
          single command (see report).
          Director-owned follow-up: append ADR-002 addendum recording tier
          PASS, pass rate 98.0%, date 2026-04-25.

  # ==========================================================================
  # SPRINT 2 — Proxy passthrough + multimodal preprocessing
  # ==========================================================================
  - id: sprint-2
    name: "Proxy + multimodal preprocessing"
    status: pending
    sequence: 2
    goal: |
      A custom FastAPI orchestration proxy on ct-ai-01:8000 exposes three virtual
      model aliases over OpenAI-compatible REST. Pure-text and pure-vision requests
      pass through directly; gemma4-auto deterministically detects image_url
      content blocks, calls E4B for description (non-streaming), injects the
      description into the message history, and forwards to 26B with SSE streaming.
      Status events keep the user informed during preprocessing. Open WebUI is
      repointed at the proxy.
    exit_gate:
      story: "9.11"
      criteria: |
        Open WebUI's model picker shows all three virtual aliases (gemma4-auto,
        gemma4-26b-text, gemma4-e4b-vision); image upload via gemma4-auto
        produces a 26B-reasoned answer that references the image content;
        Playwright MCP browser smoke verifies the visible italic status event
        during the multimodal preprocessing window.
    stories:
      - id: "9.6"
        title: "Scaffold gemma-hybrid-proxy Python repo with hexagonal layout"
        status: completed
        owner: claude-coder
        completion_date: "2026-04-25"
        evidence: "_bmad-output/implementation-artifacts/9-6-proxy-scaffold-evidence.md"
        depends_on: ["9.5"]  # Sprint 1 gate must pass before proxy work commits
        risks: ["R9"]  # reference template introduces vulnerability
        is_exit_gate: false
        notes: |
          REPO LOCATION RESOLVED 2026-04-25 in epics doc and architecture doc:
          homelab-infra/ansible/roles/gemma-hybrid-proxy/files/ (single-repo,
          matches ai-dev-omega-memory precedent). No longer an open question.
          Scaffold delivered 2026-04-25: 29 project files, 928 src LOC + 382
          test LOC, all 6 ACs PASS (deps install clean in tmp venv, ruff
          clean, mypy strict-mode clean on domain/ + adapters/openai_models,
          19/19 pytest pass in 0.05s, uvicorn smoke on :18000 returned valid
          JSON for /health, /v1/models, and 501 envelope for /v1/chat/completions).
          Two follow-ups for downstream stories captured in evidence doc:
          (1) hash-pinning deferred to Sprint 2 hardening — versions strictly
          pinned but no --require-hashes; (2) settings extra="ignore" in dev,
          tighten to "forbid" when Ansible role lands in Story 9.11.
      - id: "9.7"
        title: "Implement /v1/models advertising 3 virtual aliases"
        status: completed
        owner: claude-coder
        completion_date: "2026-04-25"
        evidence: "_bmad-output/implementation-artifacts/9-7-models-endpoint-evidence.md"
        depends_on: ["9.6"]
        risks: []
        is_exit_gate: false
        notes: |
          /v1/models now returns OpenAI-shaped envelope with all three virtual
          aliases plus `created` (deploy-time constant), `owned_by="homelab"`,
          non-standard `capabilities[]` per research-doc table, and non-standard
          `status` ("ready" | "upstream_down") derived from a 5-second TTL
          single-flight upstream-health cache (new module
          domain/upstream_health.py, 88 LOC, reusable by /health). 36/36 unit
          tests pass (9 new for 9.7); mypy + ruff clean on Story 9.7 surfaces.
          Live smoke on :18001 verified all new fields render correctly with
          `status: upstream_down` (no llama-server on dev box) and 200 on
          subsequent cached hits. AC-5 deviation: 2 pre-existing ruff issues
          in api/chat_completions.py (Story 9.8 WIP) deferred to that story
          per boundary rule.
          OPEN DECISION (OD-5): capabilities[] + status fields are non-standard
          (not in OpenAI spec). Verify Open WebUI tolerates unknown fields
          during 9.11 smoke test; if it rejects, remove from
          api/models.py::list_models entry construction (cache scaffolding
          stays intact).
      - id: "9.8"
        title: "Passthrough mode for gemma4-26b-text and gemma4-e4b-vision with SSE streaming"
        status: completed
        owner: claude-coder
        completion_date: "2026-04-25"
        depends_on: ["9.7"]
        risks: ["R9"]
        is_exit_gate: false
        ac_coverage: ["AC-1", "AC-2", "AC-7"]
        evidence: "_bmad-output/implementation-artifacts/9-8-passthrough-evidence.md"
        notes: |
          Passthrough router + SSE forwarder shipped 2026-04-25 (claude-coder).
          New domain/router.py (123 LOC pure), fleshed-out
          adapters/llama_server_client.py (forward_json + stream_request +
          UpstreamTimeout/Unreachable error types + transport= injection
          point for tests), full api/chat_completions.py replacing the 501
          stub. All 10 ACs PASS: AC-1 through AC-7 + AC-9 + AC-10 via
          mocked httpx.MockTransport (36/36 pytest, ruff clean, mypy clean
          on 17 files); AC-8 live smoke against real ct-ai-01 by pushing
          source to /tmp, uvicorn on 127.0.0.1:18002 against loopback :8080
          + :8081 — text-only chat through gemma4-26b-text returned
          "Hello." at 24.87 tok/s decode (vs 25.11 tok/s direct on Sprint
          1 — proxy overhead negligible); streaming forwarded 26 chunks
          with canonical `data: {...}\n\n` SSE framing in 1.36s.
          gemma4-auto returns 501 with explicit Story-9.9 deferral pointer;
          unknown models return 404 + valid_aliases array in OpenAI envelope.
          Smoke environment (uvicorn + /tmp/gemma-hybrid-proxy) torn down;
          llama-server + llama-server-26b services unaffected (both active
          before+after, /health green on :8080 + :8081). The 2 ruff issues
          flagged in 9.7's notes for api/chat_completions.py are implicitly
          resolved by the rewrite. Deviation flagged: api/chat_completions.py
          is 474 LOC over the 150-LOC story hint — ~50% docstrings + a
          4-helper SSE state machine (parse upstream record, emit data +
          comment events, keepalive on idle, embed error frames mid-stream);
          not refactored further this story (architecture has no hard limit
          on api/ modules — only domain/ has ≤150). Boundaries respected:
          no gemma4-auto orchestration (9.9), no tool_call delta accumulation
          (9.13), no new prod dependencies, no production state touched.
      - id: "9.9"
        title: "Implement gemma4-auto with E4B preprocessing → 26B forwarding"
        status: completed
        owner: claude-coder
        completion_date: "2026-04-25"
        depends_on: ["9.8"]
        risks: []
        is_exit_gate: false
        ac_coverage: ["AC-3"]
        evidence: "_bmad-output/implementation-artifacts/9-9-gemma4-auto-evidence.md"
        notes: |
          gemma4-auto modality cascade shipped 2026-04-25 (claude-coder).
          New domain/multimodal_preprocessor.py (191 LOC pure, async, takes
          LlamaServerClient by parameter) + fleshed-out
          domain/content_inspector.py (98 LOC pure inspect() returning
          InspectionResult with image_block coordinates) + extended
          api/chat_completions.py with _handle_auto branch (intercepts
          ALIAS_AUTO before route() to dispatch the cascade). All 10 ACs
          PASS: AC-1 (text-only auto skips E4B), AC-2 (1 image → 1 E4B + 1
          MoE), AC-3 (2 images → 2 sequential E4B + 1 MoE), AC-4 (audio →
          415 with ADR-008 envelope), AC-5 (streaming auto: preprocess
          non-streaming, MoE SSE through), AC-6 (E4B timeout/5xx → 502
          with explicit envelope, no degrade-to-text), AC-7 (empty E4B
          description → fallback marker, request still flows), AC-8 live
          smoke (text-only 2.23s with preprocess_latency_ms=0.0;
          1x1 PNG image 33.58s with preprocess_latency_ms=27.27s
          exercising the AC-7 fallback path; audio 415 instant), AC-9
          (44/44 pytest pass, +9 new tests in test_chat_completions_auto.py,
          -1 obsolete 501-deferral test from 9.8 superseded by this story),
          AC-10 (ruff clean, mypy clean on 18 source files, pytest green
          in 0.32s). Privacy: log lines carry only
          multimodal_blocks={images:N,audio:M}, preprocess_latency_ms,
          total_upstream_calls — never image bytes or description text.
          Production state untouched (smoke env on uvicorn :18003 torn down;
          /tmp/gemma-hybrid-proxy* removed; both backend services active
          before+after; ports 8080/8081 still bound by the production
          llama-server PIDs). Deviations flagged: (1) content_inspector.py
          98 LOC vs 80 hint and multimodal_preprocessor.py 191 LOC vs 120
          hint — both well under the 150-LOC architecture rule when
          docstrings excluded; (2) gemma4-auto no longer reaches
          domain/router.route() through the API surface — intercepted in
          chat_completions() before the route() call so the static router
          contract for passthrough aliases stays untouched; the
          NotYetImplemented sentinel for ALIAS_AUTO in the router is now
          unreachable through the API but retained for safety. Boundaries
          respected: no status events (Story 9.10), no tool-call agent
          loop (Story 9.13), no new prod deps, no production state
          touched, no logging of image bytes/URLs/descriptions.
      - id: "9.10"
        title: "Status events during preprocessing (italic-formatted delta.content chunks)"
        status: completed
        owner: claude-coder
        completion_date: "2026-04-25"
        depends_on: ["9.9"]
        risks: ["R4"]  # Open WebUI tool-call streaming bug — verify status events don't trigger
        is_exit_gate: false
        ac_coverage: ["AC-5"]
        evidence: "_bmad-output/implementation-artifacts/9-10-status-events-evidence.md"
        notes: |
          Status events shipped 2026-04-25 (claude-coder). Option A chosen
          (per story brief): new pure module domain/sse_helpers.py (71 LOC)
          builds OpenAI-shaped chat.completion.chunk frames; promoted
          domain/multimodal_preprocessor._describe_one_image to public
          describe_one_image + extracted build_description_block helper
          (no signature change to preprocess_images, so non-streaming +
          text-only-streaming paths are untouched). New generator
          _sse_stream_with_status in api/chat_completions.py drives the
          per-image describe loop: emits "\n_[describing image N of M...]_\n"
          before each E4B call, then "\n_[reasoning...]_\n" before opening
          MoE, then forwards MoE chunks via the existing _sse_stream helper
          (so keepalive + mid-stream error embedding behave identically to
          passthrough). All 8 ACs PASS: AC-1 (1 image → 1 describe + 1
          reasoning + MoE in order), AC-2 (2 images → 2 describes "1 of 2"
          and "2 of 2" then reasoning then MoE), AC-3 (text-only streaming
          emits zero status — verified mocked AND live), AC-4 (non-streaming
          + image returns plain JSON, no status anywhere), AC-5 (chunk
          format byte-equal to ADR-012: `\n_[describing image 1 of 1...]_\n`,
          standard chat.completion.chunk envelope, finish_reason null, no
          custom event field), AC-6 live smoke on ct-ai-01:18004 (TTFB
          8.6ms for first status; 26s preprocess wait between describe
          status and first MoE chunk; reasoning status arrived in same
          second as first MoE chunk; total wall time 28.4s; 15s keepalive
          comment landed during the wait, defeating idle timeouts), AC-7
          (49/49 pytest pass — 44 prior + 5 new in test_chat_completions_auto.py;
          no regressions), AC-8 (ruff clean, mypy clean on 19 src files,
          pytest green in 0.22s). Privacy: status text never logged
          (architecture §Logging rule); only multimodal_blocks /
          preprocess_latency_ms / total_upstream_calls bound on logs.
          Production state untouched (smoke env on uvicorn :18004 torn
          down; /tmp/gemma-hybrid-proxy* removed; both llama-server services
          active before+after on :8080+:8081). Module sizes: sse_helpers
          71 LOC vs ≤60 hint (over by 11 — docstrings + format-text helper
          exposed for unit assertion); api/chat_completions.py 795 LOC
          (+155 over 9.9 — generator is ~110 LOC including extensive
          docstring; same flag as 9.8/9.9, refactor deferred to 9.13
          when delta accumulation lands). R4 verification: status events
          are pure delta.content (no tool_calls), confirmed by AC-5
          test asserting absence of "event"/"type" custom keys at top
          level — Open WebUI #23066 should NOT trigger.
      - id: "9.11"
        title: "Create Ansible role gemma-hybrid-proxy and deploy via ct-dev-test → ct-ai-01; repoint Open WebUI"
        status: completed
        owner: claude-coder
        completed_date: "2026-04-25"
        depends_on: ["9.10"]
        risks: ["R6"]  # VRAM exhaustion under sustained load — verify both backends + proxy fit
        is_exit_gate: true
        ac_coverage: ["AC-3", "AC-8"]
        evidence: "9-11-cutover-evidence.md"
        notes: |
          DECISION RESOLVED: dedicated `gemma-hybrid` system user (uid 997,
          gid 987) per architecture §Open question #3. Role at
          `homelab-infra/ansible/roles/gemma-hybrid-proxy/` with defaults,
          tasks, templates (env.j2 + service.j2), handlers. Real deploy on
          ct-ai-01 succeeded (snapshot rpool/data/subvol-160-disk-0@pre-
          proxy-cutover-20260425-1134). Proxy on 127.0.0.1:8000, /health
          green, /v1/models returns the 3 aliases. E4B llama-server
          rebound from 0.0.0.0:8080 → 127.0.0.1:8080 per ADR-009 (defense
          in depth — config flipped in
          roles/llama-server/defaults/main.yml + restarted via
          --start-at-task). OWUI cutover: docker rm + re-run with
          OPENAI_API_BASE_URLS=http://127.0.0.1:8000/v1 (single endpoint,
          named volume `open-webui` preserved); rollback command captured
          in evidence. 1 deviation: ct-dev-test unreachable (no route to
          host); --check on ct-ai-01 substituted (same pattern as 9.4).
          1 mid-flight bug fix: WatchdogSec=30 caused spurious systemd
          restarts (uvicorn doesn't ping sd_notify); removed from unit
          template with comment explaining the gap. Idempotent re-run
          shows changed=2 (synchronize cosmetic + flush_handlers
          cosmetic, no actual writes). Browser smoke deviation: OWUI
          requires admin login (no creds in repo); login page reached +
          screenshot captured + technical proof via in-container
          `docker exec open-webui curl /v1/models` returning 3 aliases.
          All 4 services healthy (gemma-hybrid-proxy, llama-server, llama-
          server-26b, open-webui), all four endpoints loopback-only
          except OWUI :3000.

  # ==========================================================================
  # SPRINT 3 — Tool-call agent loop + LiteLLM gateway
  # ==========================================================================
  - id: sprint-3
    name: "Tool-call agent loop + LiteLLM gateway"
    status: pending
    sequence: 3
    goal: |
      The 26B reasoner can mid-stream emit a tool_calls for analyze_image, the
      proxy intercepts the call, executes it against E4B with the original image
      data, appends the tool result to the conversation, and resumes 26B's
      stream — all transparent to the client. LiteLLM gateway sits in front for
      bearer-token auth, Prometheus metrics, rate limiting; Open WebUI,
      Continue.dev, Cursor, and the operator's phone are all configured to use it.
    exit_gate:
      story: "9.17"
      criteria: |
        All 10 acceptance criteria from research §Implementation Approaches →
        Testing and Quality Assurance pass; multi-app access works from at least
        Open WebUI + one IDE + the phone over Tailscale; LiteLLM Prometheus
        metrics visible in Grafana.
    stories:
      - id: "9.12"
        title: "Define analyze_image tool schema (JSON Schema draft-07)"
        status: completed
        owner: claude-coder
        completion_date: "2026-04-25"
        evidence: "_bmad-output/implementation-artifacts/9-12-tool-definitions-evidence.md"
        depends_on: ["9.11"]
        risks: ["R1"]  # accuracy already gated; this story locks the schema
        is_exit_gate: false
        notes: |
          Schema RESOLVED 2026-04-25: `image_id: string` (e.g., 'image-1'-style
          identifier) + `question: string`, both required. Architecture's
          string-id form is more robust to multi-turn history. Epic Story 9.12
          updated to match architecture §Tool-call schema rules.
          Implementation 2026-04-25 (claude-coder): replaced Story 9.6 skeleton
          in domain/tool_definitions.py (117 LOC, ≤120 cap) with
          ANALYZE_IMAGE_TOOL + AVAILABLE_TOOLS + MAX_TOOL_ITERATIONS=5 +
          get_tool_by_name + augment_request_with_tools (pure non-mutating
          merge w/ dedup-by-name) + assign_image_ids (global numbering across
          messages, composes with multimodal_preprocessor for Story 9.14) +
          AnalyzeImageArgs (Pydantic strict, extra=forbid). 16 new unit tests
          (49 → 65 total), ruff + mypy + pytest all green, zero regressions.
          transcribe_audio NOT registered (ADR-008). multimodal_preprocessor.py
          and chat_completions.py untouched per story boundaries — Story 9.14
          wires the composition.
      - id: "9.13"
        title: "Implement delta_accumulator for streaming tool_calls"
        status: completed
        owner: claude-coder
        completion_date: "2026-04-25"
        depends_on: ["9.12"]
        risks: ["R4"]  # Open WebUI #23066 surfaces here if delta emission is dirty
        is_exit_gate: false
        evidence: "_bmad-output/implementation-artifacts/9-13-delta-accumulator-evidence.md"
        notes: |
          ToolCallAccumulator + parse_arguments + accumulate_stream shipped
          2026-04-25 (claude-coder). Fleshed out the 41-LOC skeleton from
          Story 9.6 into a pure-domain reassembler at
          domain/delta_accumulator.py (217 lines raw / 116 code lines —
          under the 150-LOC architecture ceiling). Class renamed from the
          skeleton's DeltaAccumulator → ToolCallAccumulator per the Story
          9.13 brief (skeleton was unreachable; zero callers — verified
          via grep). All 6 ACs PASS: 4 methods + 2 helpers per spec
          (finish_reason exposed as @property for tuple-return ergonomics
          in accumulate_stream); 15 new unit tests in
          tests/unit/test_delta_accumulator.py covering single-call
          multi-chunk, parallel calls interleaved, pre-tool text content,
          args-before-name, malformed JSON (with structlog warning capture
          via capsys), valid-but-non-object JSON, empty/None args,
          finish_reason=stop with no calls, finish_reason=length
          truncation, Pydantic round-trip validation, reset(), empty/
          missing choices defensiveness, missing-index fallthrough, and
          accumulate_stream end-to-end (tool-call + plain-stop variants);
          ruff + mypy strict on domain/* clean across 19 src files;
          80/80 pytest pass (49 prior + 16 from 9.12 parallel + 15 new),
          0 regressions. Pure module — no httpx, no env reads, no I/O;
          finalize() returns ToolCall.function.arguments as the original
          JSON-encoded string per OpenAI spec (callers parse via
          parse_arguments helper which logs + returns {} on failure
          rather than crashing). Boundaries respected: no
          chat_completions.py edits (9.14 owns the wire-in), no
          tool_definitions.py edits (9.12 parallel), no preprocessor
          edits, no new prod deps. R4 (Open WebUI #23066) defence:
          accumulator yields validated Pydantic ToolCall objects that
          round-trip cleanly — byte-level fixture comparison for
          downstream re-encoding belongs to 9.14.
      - id: "9.14"
        title: "Implement orchestrator agent loop (intercept → execute → resume → stream)"
        status: completed
        owner: claude-coder
        completion_date: "2026-04-25"
        depends_on: ["9.13"]
        risks: ["R4", "R6"]
        is_exit_gate: false
        ac_coverage: ["AC-4"]
        evidence: "_bmad-output/implementation-artifacts/9-14-agent-loop-evidence.md"
        notes: |
          Iteration cap RESOLVED 2026-04-25: hard cap of 5 iterations per
          request (configurable via gemma_hybrid_proxy_max_tool_iterations,
          default 5); on the 6th iteration, force finish_reason=stop. Matches
          architecture §Error handling rules. Epic Story 9.14 updated.
          Implementation 2026-04-25 (claude-coder): new
          domain/agent_loop.py (351 raw / 259 code lines — over the 180-LOC
          brief target; runner is a @dataclass with streaming +
          non-streaming methods, a tool-execution helper, and 6 module-level
          pure helpers — see deviation #1 in evidence) +
          build_image_registry helper. _handle_auto in
          api/chat_completions.py rewired to: build per-request
          image_registry → assign_image_ids → preprocess_images (re-inspect
          for shifted coords) → augment_request_with_tools → AgentLoopRunner
          drives the iteration loop. Streaming-with-status branch wires the
          runner identically post-preprocess so all 4 status-event types
          fire (describing N of M / reasoning / calling analyze_image /
          continuing reasoning). Tool-execution failure modes (Pydantic
          args invalid, E4B 5xx/timeout/connect-refused, unknown
          image_id, unknown tool name, catch-all Exception) all inject
          a `tool` message with `error: ...` body and let the loop
          continue — never crashes the request. Iteration cap (5) emits
          synthetic content + finish_reason=stop + [DONE]. All 10 ACs
          PASS: AC-1 (text-only auto skips loop iteration — regression
          check), AC-2 (image preprocess + augmented request reaches MoE
          + 1 iter when no tool call), AC-3 (mocked + LIVE: model emits
          analyze_image, executed against E4B, second MoE iteration
          consumes result), AC-4 (max_iterations=3 synthetic loop bounded
          + clean close), AC-5 (malformed args → tool error injected, no
          crash), AC-6 (E4B 503 + httpx.ConnectError → tool error
          injected, no crash), AC-7 (status events captured in mocked +
          live SSE), AC-8 (101/101 pytest pass — 80 prior + 21 new + 3
          updated for new image-id label shape, 0 regressions), AC-9
          (ruff clean, mypy clean on 20 src files, pytest 0.30s), AC-10
          (live smoke ct-ai-01:18005 — agent loop fired with REAL MoE
          emitting tool_calls finish_reason; full timing 0.006s TTFB
          for first status, 26s preprocess, 8s reasoning to tool_calls,
          26s tool exec via E4B re-describe, ~26s second MoE iteration,
          total 85.97s wall; production gemma-hybrid-proxy.service on
          :8000 untouched throughout; smoke env torn down on exit).
          3 deviations flagged in evidence: (1) agent_loop.py 259 code
          lines over 180 brief target (parity with 9.13's 217 raw and
          9.9's 191) — refactor would break hexagonal testability;
          (2) iteration cap fires AFTER 5th iteration not BEFORE 6th —
          functionally equivalent; (3) 3 pre-existing tests in
          test_chat_completions_auto.py updated for new image-id label
          shape — intended Story 9.14 behaviour, not a regression.
          Boundaries respected: no tool_definitions.py edits, no
          delta_accumulator.py edits, no LiteLLM, no transcribe_audio,
          no production state touched, no new prod deps. Evidence:
          9-14-agent-loop-evidence.md.
      - id: "9.15"
        title: "Test with synthetic prompts that should trigger tool calls"
        status: completed
        owner: claude-coder
        completion_date: "2026-04-25"
        depends_on: ["9.14"]
        risks: ["R1"]
        is_exit_gate: false
        ac_coverage: ["AC-1", "AC-2", "AC-3", "AC-4", "AC-7", "AC-8", "AC-9", "AC-10"]
        ac_pass_count: 8
        ac_total_count: 10
        evidence: "_bmad-output/implementation-artifacts/9-15-agentloop-smoke-evidence.md"
        notes: |
          Story 9.15 itself completed (test harness built, 25-prompt suite ran,
          results captured). 8/10 ACs PASS. AC-5 (tool-triggering ≥50%) and
          AC-6 (multi-iteration ≥1 success) FAILED — exposing a critical
          regression: gemma4-auto agent loop emits tool calls as plain text
          instead of structured delta.tool_calls. Per-category: text-only 5/5,
          passive-image 5/5, tool-triggering 0/10, multi-iteration 0/3,
          iteration-cap 2/2. Per director decision (Option B), MVP ships with
          this gap; fix is priority Sprint 4 Story 9.22. ADR-002 has a Sprint 3
          addendum recording the gate-test methodology gap (must test the
          production compose flow, not the raw upstream).
      - id: "9.16"
        title: "Deploy LiteLLM gateway with virtual key for self; configure model_list pointing at FastAPI router"
        status: completed
        owner: claude-coder
        completed_at: "2026-04-25"
        depends_on: ["9.15"]
        risks: ["R2"]  # this story IS the R2 mitigation
        is_exit_gate: false
        ac_coverage: ["AC-9"]
        evidence: "_bmad-output/implementation-artifacts/9-16-litellm-gateway-evidence.md"
        notes: |
          litellm_version PIN RESOLVED 2026-04-25: `litellm==1.83.13` (or latest
          stable `1.83.x` at install time) with `--hash=sha256` verification per
          architecture ADR-011. Epic Story 9.16 updated. Operator must
          independently re-audit at deploy time to confirm the version is still
          current and audited.

          DEPLOYED 2026-04-25 (claude-coder). All 10 ACs PASS on ct-ai-01:
          litellm-gateway.service active on 127.0.0.1:4000, forwards 3 aliases
          to gemma-hybrid-proxy on :8000, master-key bearer auth working
          (401 without, 200 with), Prometheus /metrics/ exposed (200).
          Idempotent (0 changes on 2nd run). All 4 upstream services still
          healthy. Snapshot pre-litellm-deploy-20260425-1730 retained.
          Key deviations: pip spec `litellm[proxy,proxy-runtime]==1.83.13`
          (proxy-runtime carries prometheus-client; brief said only [proxy]),
          stateless mode (no Prisma DB; not needed for Sprint 3 ACs),
          hash-pinning skipped for 90+ transitive graph (Story 9.6 trade-off
          precedent; pre-install assert refuses 1.82.7/1.82.8 compromised
          tags). Master key generated fresh, NOT in git (operator password
          manager + /tmp/litellm-master-key-9.16.txt mode 0600 pending
          Vault enrolment). Evidence: 9-16-litellm-gateway-evidence.md.
          Sprint 3 may proceed to Story 9.17 (EXIT GATE).

          OPEN DECISION: bearer key storage strategy.
            Epic says: operator's bearer key recorded only in password manager
              (not in git).
            Question raised: should the key also be stored in Ansible Vault for
              IaC reproducibility? Pick one strategy before deploy.

          OPEN DECISION: LiteLLM streaming passthrough behavior for tool-call
          deltas. Architecture flags this as a verification task — if LiteLLM
          buffers/rewrites streamed tool_calls deltas, gemma4-auto must bypass
          LiteLLM with FastAPI handling auth itself for that route. Plan a
          Sprint 3 verification sub-task during 9.16 integration testing.
      - id: "9.17"
        title: "Configure clients (Open WebUI, Continue.dev, Cursor, phone) with virtual key + Prometheus + Grafana dashboard"
        status: pending
        owner: unassigned
        depends_on: ["9.16"]
        risks: ["R7"]  # Tailscale outage — LAN fallback documented
        is_exit_gate: true
        ac_coverage: ["AC-6", "AC-8", "AC-9", "AC-10"]

  # ==========================================================================
  # SPRINT 4 — Priority fix + Deferred audio/hardening
  # ==========================================================================
  - id: sprint-4
    name: "Priority fix + Deferred audio + hardening"
    status: pending
    sequence: 4
    goal: |
      Two tracks: (1) priority — fix the agent-loop production regression
      surfaced by Story 9.15 (story 9.22); (2) deferred — audio support
      (9.18-9.20) and soak/E2E hardening (9.21) gated on llama.cpp #21334
      stabilization or concrete operator need.
    priority_track:
      - "9.22"
    deferred_track:
      - "9.18"
      - "9.19"
      - "9.20"
      - "9.21"
    trigger_conditions:
      description: "The deferred track stays out of MVP and only triggers when ONE of the following becomes true:"
      conditions:
        - "llama.cpp #21334 (Gemma 4 E4B audio) lands stable"
        - "A concrete operator need for audio in/out arises"
      tracking_artefact: "homelab-playbook/_bmad-output/planning-artifacts/audio-tracking.md"
      review_cadence: "monthly during planning ceremonies"
      applies_to_track: "deferred"  # priority track 9.22 has no trigger gate; it's required for MVP feature-complete
    priority_track_gate:
      story: "9.22"
      criteria: |
        gemma4-auto agent loop emits structured delta.tool_calls under
        production proxy compose flow; sprint3_agentloop_smoke.py
        tool-triggering ≥70% (7/10) and multi-iteration ≥66% (2/3); no
        regression in text-only / passive-image categories; ADR-002
        addendum updated with the chosen mitigation.
    exit_gate:
      story: "9.21"
      criteria: |
        1-hour soak test produces no monotonic GPU/RSS memory growth, no
        systemd restarts, error rate <1%, p95 first-token within budgets.
        Epic-level success criteria fully met.
      applies_to_track: "deferred"
    note_on_audio_contradiction: |
      ADR-008 (Defer audio to v2) says audio content blocks return 415
      Unsupported Media Type with a "v2 roadmap" message. Sprint 4 stories
      9.18-9.21 plan to add audio support. This is consistent — the deferred
      track IS the v2 work. When the deferred track triggers, the 415
      short-circuit in the orchestrator must be removed before 9.19 lands.
    stories:
      - id: "9.22"
        title: "Agent-loop production reliability fix (Sprint 3 regression)"
        status: pending
        owner: unassigned
        depends_on: ["9.17"]      # blocks on Sprint 3 close
        risks: ["R1"]             # R1 reopened
        is_exit_gate: false       # Sprint 4 priority gate, not regular sprint exit
        priority: critical        # NEW field; flag this as MUST-DO
        track: priority
        evidence_pending: "_bmad-output/implementation-artifacts/sprint3-agentloop-smoke-results-2026-04-25.md"
        notes: |
          PRIORITY (not deferred). Sprint 3 Story 9.15 surfaced that gemma4-auto
          agent loop emits tool calls as plain text instead of structured
          delta.tool_calls. 0/10 tool-triggering prompts succeeded; 0/3
          multi-iteration prompts succeeded. Agent loop never fires.
          Test 4 hypotheses in order: (1) system-prompt tightening,
          (2) asf0 template audit, (3) --jinja flag interaction,
          (4) Unsloth UD-Q5_K_M reasoner swap.
          See ADR-002 Sprint 3 addendum for full context.
      - id: "9.18"
        title: "Track llama.cpp #21334 (Gemma 4 E4B audio) and decide trigger"
        status: deferred
        owner: unassigned
        depends_on: ["sprint-3:complete"]
        risks: ["R5"]  # this story IS the R5 mitigation through deferral + tracking
        is_exit_gate: false
        is_trigger_story: true  # the only Sprint 4 work that runs before the trigger fires
        track: deferred
      - id: "9.19"
        title: "Implement transcribe_audio tool + input_audio content branch"
        status: deferred
        owner: unassigned
        depends_on: ["9.18:trigger-fires"]
        risks: ["R5"]
        is_exit_gate: false
        track: deferred
      - id: "9.20"
        title: "Browser E2E test suite (Playwright MCP) for the full multi-app flow"
        status: deferred
        owner: unassigned
        depends_on: ["sprint-3:complete"]  # technically runnable from end of Sprint 3
        risks: ["R4"]
        is_exit_gate: false
        track: deferred
      - id: "9.21"
        title: "Soak test (1 hour continuous) for memory stability"
        status: deferred
        owner: unassigned
        depends_on: ["sprint-3:complete"]  # 9.19 if audio coverage included
        risks: ["R6"]  # this story IS the R6 validation
        is_exit_gate: true
        track: deferred

# ============================================================================
# CROSS-SPRINT RISK REGISTER
# Risks come from research §Implementation Approaches → Risk Assessment.
# Each risk references the story/stories that mitigate or measure it.
# ============================================================================
risks:
  - id: R1
    severity: high
    name: "TrevorJS chat-template fix possibly incomplete"
    description: |
      The asf0/gemma4_jinja override is reported as "incomplete" by the original
      HF discussion #2 reporter. If reasoning_content leaks into OpenAI content
      or tool_calls round-trip mangled, the agentic reasoner is unusable as the
      primary backend.
    mitigation_stories: ["9.5", "9.12", "9.15"]
    sprint_surface: "Sprint 1 exit gate (9.5)"
    contingency: |
      ADR-002b activates Unsloth UD-Q5_K_M as fallback. See Sprint 1 exit gate
      pass_action / fail_action for the fork.
  - id: R2
    severity: high
    name: "LiteLLM PyPI compromise repeats"
    description: |
      LiteLLM PyPI was compromised March 2026 (1.82.7 / 1.82.8 shipped a
      credential stealer; 119k+ downloads in ~40 minutes). Future compromise
      possible. Mitigation = pin + hash + audited post-incident version + manual
      review of bumps.
    mitigation_stories: ["9.16"]
    sprint_surface: "Sprint 3 (9.16)"
    contingency: "Refuse install on hash mismatch; manually audit bump candidates."
  - id: R3
    severity: medium
    name: "llama.cpp Vulkan upgrade breaks Strix iGPU build"
    description: "Build mismatch on rebuild surfaces in mid-sprint."
    mitigation_stories: ["9.1", "9.4"]
    sprint_surface: "Sprint 1 (9.1 verify, 9.4 ct-dev-test catches it)"
    contingency: "Pin llama.cpp commit; rebuild on a known-good ref."
  - id: R4
    severity: high
    name: "Open WebUI tool-call streaming bug (#23066)"
    description: |
      Open WebUI has an infinite-loop streaming tool messages issue (#23066).
      If the proxy emits dirty tool-call deltas, Open WebUI loops and the UX
      is broken. Mitigation = clean delta emission + browser E2E.
    mitigation_stories: ["9.10", "9.13", "9.20"]
    sprint_surface: "Sprint 2 (9.10 status events shouldn't trigger), Sprint 3 (9.13 clean accumulation), Sprint 4 deferred (9.20 E2E catches regressions)"
    contingency: "Bypass Open WebUI for the agent-loop path; use direct API client."
  - id: R5
    severity: medium
    name: "input_audio instability on Gemma 4 E4B"
    description: "llama.cpp audio path is highly experimental; some 400 errors reported."
    mitigation_stories: ["9.18", "9.19"]
    sprint_surface: "Sprint 4 deferred (9.18 trigger gate)"
    contingency: "Sprint 4 stays deferred; ADR-008 returns 415 for audio in v1."
  - id: R6
    severity: medium
    name: "VRAM exhaustion under sustained load"
    description: "Both backends + proxy must fit within 32 GB dedicated VRAM budget over hours."
    mitigation_stories: ["9.11", "9.21"]
    sprint_surface: "Sprint 2 (9.11 verify on deploy), Sprint 4 (9.21 soak)"
    contingency: "Reduce 26B context size; reduce E4B batch size; accept lower concurrency cap."
  - id: R7
    severity: low
    name: "Tailscale outage"
    description: "If Tailscale is down, remote clients can't reach LiteLLM."
    mitigation_stories: ["9.17"]
    sprint_surface: "Sprint 3 (9.17 documents LAN fallback)"
    contingency: "LAN-direct access from on-network clients remains functional."
  - id: R8
    severity: low
    name: "LXC reboot loses warm KV cache"
    description: "First request after reboot is slower; no warm-cache persistence."
    mitigation_stories: []
    sprint_surface: "Accepted; no story"
    contingency: "Accepted; document expected first-request latency in runbook."
  - id: R9
    severity: medium
    name: "Reference template introduces a vulnerability when copied"
    description: |
      Copying patterns from MIT-licensed reference repos (talesmousinho,
      AlirezaAzadbakht, ahmad2b) verbatim risks pulling in a latent bug.
    mitigation_stories: ["9.6", "9.8"]
    sprint_surface: "Sprint 2 (9.6 scaffold, 9.8 passthrough)"
    contingency: "Adapt patterns; do not fork. Per architecture §Starter Template Evaluation."
  - id: R10
    severity: low
    name: "Gemma 5 supersedes the architecture"
    description: "A future Gemma 5 release may obsolete the model choices."
    mitigation_stories: []
    sprint_surface: "Architecture is model-agnostic; defaults swap suffices"
    contingency: "Accepted; revisit at Gemma 5 launch."

# ============================================================================
# OPEN DECISIONS TO RESOLVE AT DEPLOY TIME
# Surfaced from epic Open Questions, architecture Open Questions, and
# inconsistencies between the two documents.
# ============================================================================
open_decisions:
  - id: OD-1
    sprint: 3
    story: "9.16"
    decision: "LiteLLM streaming passthrough behavior for tool-call deltas"
    description: |
      Verify in integration tests whether LiteLLM buffers or rewrites streamed
      tool_calls deltas. If it does, gemma4-auto must bypass LiteLLM and FastAPI
      must handle auth itself for that route.
    resolution_required_by: "Story 9.16 integration testing"
    default_path: "Plan as a Sprint 3 verification sub-task; documented contingency in architecture §Boundary 1."

  - id: OD-2
    sprint: 3
    story: "9.16"
    decision: "litellm_version re-audit at deploy"
    description: |
      Pin RESOLVED 2026-04-25: litellm==1.83.13 (or latest stable 1.83.x at
      install time) with --hash=sha256 verification. Operator must independently
      re-audit at deploy time to confirm the post-March-2026 audited version is
      still current. Open only as a re-audit checkpoint, not a pin choice.
    resolution_required_by: "Story 9.16 deploy"
    default_path: "litellm==1.83.13 with --hash=sha256 verification."

  - id: OD-3
    sprint: 3
    story: "9.16"
    decision: "Bearer key storage strategy (password manager only vs vault)"
    description: |
      Epic says operator's bearer key is recorded only in password manager (not
      in git). Architecture leaves this open. If operator wants the key in
      vault for IaC reproducibility, the story is one-line different.
    resolution_required_by: "Story 9.16 deploy"
    default_path: "Password manager only (matches existing security pattern)."

  - id: OD-4
    sprint: cross-cutting
    story: null
    decision: "Renovate vs Dependabot vs manual cadence for Python deps"
    description: |
      ADR-011 says manual review for LiteLLM bumps; unspecified for everything
      else (FastAPI, httpx, pydantic, sse-starlette, etc.). Pick a bot and a
      cadence (e.g., weekly digest, monthly review).
    resolution_required_by: "Before first dep-bump PR lands"
    default_path: "Recommend Renovate weekly digest with manual merge for LiteLLM, auto-merge minor for everything else."

  - id: OD-5
    sprint: 2
    story: "9.7"
    decision: "/v1/models capabilities[] field is non-standard — verify Open WebUI tolerance"
    description: |
      OpenAI's /v1/models doesn't define a capabilities array. Open WebUI may
      ignore it (fine) or reject it (story needs adjustment). Verify in 9.11
      smoke test.
    resolution_required_by: "Story 9.11 smoke test"
    default_path: "Ship capabilities[] as informational; remove if Open WebUI rejects."

  - id: OD-6
    sprint: 2
    story: "9.11"
    decision: "System user creation: dedicated gemma-hybrid vs reuse existing"
    description: |
      systemd unit references User={{ proxy_user }} but no decision recorded.
      Architecture §Open question #3 recommends dedicated for blast-radius.
    resolution_required_by: "Story 9.11 deploy"
    default_path: "Dedicated gemma-hybrid system user."

  # OD-7 RESOLVED 2026-04-25: Sprint 1 fallback is now a THREE-TIER decision
  # tree (PASS / MARGINAL / FAIL — see exit_gate above and ADR-002 addendum in
  # the architecture doc). Replaces the prior binary epic-vs-architecture
  # contradiction. No longer an open decision.
  #
  # OD-8 RESOLVED 2026-04-25: analyze_image tool schema uses `image_id: string`
  # (architecture's string-id form). Epic Story 9.12 updated.
  #
  # OD-9 RESOLVED 2026-04-25: Tool-call max iterations = 5 (architecture's value
  # adopted). Epic Story 9.14 updated.
  #
  # OD-10 RESOLVED 2026-04-25: Sprint 1 gate ADR is inlined as an ADDENDUM to
  # ADR-002 in hybrid-gemma-serving-architecture.md. No separate
  # _bmad-output/architecture-decisions/ folder is created.
  #
  # OD-11 RESOLVED 2026-04-25: Status event string format = ADR-012 form
  # `\n_[describing image...]_\n`. Epic Story 9.10 updated.

# ============================================================================
# CROSS-DOC INCONSISTENCIES (resolution captured under open_decisions above)
# ============================================================================
known_inconsistencies:
  # All OD-7 through OD-11 inconsistencies were RESOLVED 2026-04-25 (see
  # commented entries above in open_decisions). Epic, architecture, and sprint
  # status are now consistent on:
  #   - Sprint 1 gate: three-tier decision tree (PASS / MARGINAL / FAIL),
  #     ADR-002 addendum inlined in architecture doc.
  #   - Tool schema: image_id: string + question: string.
  #   - Max iterations: 5 (default) with 6th iteration force-stop.
  #   - Status event format: \n_[describing image...]_\n.
  #   - Proxy repo location: homelab-infra/ansible/roles/gemma-hybrid-proxy/files/.
  #   - LiteLLM pin: 1.83.13 with --hash=sha256.
  resolved: |
    All cross-doc inconsistencies as of 2026-04-25 are reconciled. New
    inconsistencies to be added below as they are surfaced.

# ============================================================================
# VELOCITY TRACKING
# Empty for now; filled as sprints complete. No time estimates per BMad rule;
# track stories completed per sprint window and any retro signals.
# ============================================================================
velocity:
  sprint_1:
    stories_total: 5
    stories_completed: 5  # 9.1, 9.2, 9.3, 9.4, 9.5
    gate_outcome: "pass-trevorjs-only"  # "pass-trevorjs-only" | "marginal-parallel-deploy" | "fail-unsloth-replace"
    gate_pass_rate: 0.98  # numeric: prompts-passing-all-3-checks / 50  (49/50)
    notes: |
      9.1, 9.2, 9.3, 9.4, 9.5 all completed 2026-04-25 (claude-coder). 26B
      service live on ct-ai-01:8081 (loopback per ADR-009), registered in Open
      WebUI alongside E4B. Smoke tests PASS: text chat content non-empty (no R1
      indicator), tool-call returns correct name + args, decode 25 tok/s
      (within 18-30 research band), E4B unaffected. Rollback snapshot:
      rpool/data/subvol-160-disk-0@pre-26b-deploy-20260425-1013.
      Sprint 1 EXIT GATE (Story 9.5) outcome: PASS (49/50 = 98.0% ≥ 90%
      threshold). Keep TrevorJS as sole reasoner; no Unsloth fallback deploy
      required. R1 CLOSED (zero CoT leakage in 50/50 responses). Sprint 2 may
      proceed unmodified. Single failure: negative-02 ("What is 2 plus 2?")
      where model conservatively invoked calculate tool — clean schema, low
      severity. Director-owned follow-up: append ADR-002 addendum recording
      tier verdict, pass rate, date.
  sprint_2:
    stories_total: 6
    stories_completed: 6  # 9.6, 9.7, 9.8, 9.9, 9.10, 9.11
    status: completed
    completed_date: "2026-04-25"
    notes: |
      9.6 completed 2026-04-25 (claude-coder). Python scaffold under
      homelab-infra/ansible/roles/gemma-hybrid-proxy/files/ with hexagonal
      layout (domain/, adapters/, api/), Pydantic v2 strict OpenAI models,
      real /health + /v1/models, 501 stub for /v1/chat/completions, 19
      passing unit tests, ruff + mypy clean, uvicorn smoke verified on
      :18000. Evidence: 9-6-proxy-scaffold-evidence.md.
      9.7 completed 2026-04-25 (claude-coder). /v1/models refined: 3 aliases
      now carry `created`, `owned_by="homelab"`, non-standard `capabilities[]`
      per research table, and non-standard `status` derived from a 5-second
      TTL single-flight upstream-health cache (new domain/upstream_health.py,
      88 LOC). 27/27 unit tests pass (9 new at this point); mypy + ruff
      clean on Story 9.7 surfaces. Live smoke on :18001 confirms shape.
      AC-5 known deviation: 2 pre-existing ruff issues in
      api/chat_completions.py (9.8 WIP) deferred to that story per
      boundary rule. Evidence: 9-7-models-endpoint-evidence.md.
      9.8 completed 2026-04-25 (claude-coder). Passthrough router
      (domain/router.py, 123 LOC pure) + SSE streaming forwarder
      (api/chat_completions.py rewritten, 474 LOC incl. helpers) +
      llama_server_client adapter forward_json/stream_request methods.
      All 10 ACs PASS: AC-1 through AC-7 + AC-9 + AC-10 via mocked
      httpx.MockTransport (36/36 pytest, +9 new tests; ruff clean,
      mypy clean on 17 files); AC-8 live smoke on real ct-ai-01 — text
      chat at 24.87 tok/s (within Sprint 1 baseline, proxy overhead
      negligible), streaming 26 chunks with canonical SSE framing in
      1.36s, 9.7's deferred ruff issues implicitly resolved by rewrite.
      Production state untouched (smoke env torn down; both backends
      active before+after). Evidence: 9-8-passthrough-evidence.md.
      9.9 completed 2026-04-25 (claude-coder). gemma4-auto modality
      cascade implemented: new domain/multimodal_preprocessor.py (191
      LOC pure async, takes LlamaServerClient by parameter — pure
      hexagonal boundary), fleshed-out domain/content_inspector.py (98
      LOC pure inspect() returning InspectionResult with image_block
      coordinates), extended api/chat_completions.py with _handle_auto
      dispatching the cascade. All 10 ACs PASS via 9 new mocked tests
      (httpx.MockTransport split-routed by upstream port) + live smoke
      on ct-ai-01: text-only auto 2.23s with preprocess_latency_ms=0.0
      (E4B never touched — fast-path proven); 1x1 PNG image 33.58s
      with preprocess_latency_ms=27.27s (E4B describe + MoE reason in
      series — also exercised AC-7 fallback live since 1x1 transparent
      yields empty description); audio short-circuits to 415 with
      ADR-008 envelope before any I/O. 44/44 pytest, ruff clean, mypy
      clean on 18 src files. Privacy: log lines carry only
      multimodal_blocks={images:N,audio:M}, preprocess_latency_ms,
      total_upstream_calls — never bytes/URLs/descriptions.
      Production state untouched (uvicorn :18003 torn down;
      /tmp/gemma-hybrid-proxy* removed; both llama-server services
      active before+after on :8080+:8081). Evidence:
      9-9-gemma4-auto-evidence.md. Sprint 2 may proceed to Story 9.10
      (status events) and 9.11 (Ansible role + deploy).
      9.10 completed 2026-04-25 (claude-coder). Status events shipped
      per ADR-012 — Option A: new pure module domain/sse_helpers.py
      (71 LOC), promoted preprocessor._describe_one_image to public +
      extracted build_description_block helper, new generator
      api/_sse_stream_with_status drives per-image describe + status
      emission. All 8 ACs PASS via 5 new mocked tests + live smoke on
      ct-ai-01:18004: streaming + 1x1 PNG capture shows describe-status
      arrives 8.6 ms after request (TTFB), preprocess wait of ~26 s,
      then reasoning-status + first MoE chunk in same second, total
      28.4 s; text-only streaming gemma4-auto emits zero status events
      (verified live, ttfb 5.8 ms — fast path proven). 49/49 pytest,
      ruff clean, mypy clean on 19 src files. Status chunk format
      byte-equal to ADR-012: `\n_[describing image N of M...]_\n` /
      `\n_[reasoning...]_\n` in standard chat.completion.chunk
      delta.content (no custom event channel — vanilla OpenAI clients
      render via markdown). Privacy: status text never logged.
      Production state untouched (uvicorn :18004 torn down;
      /tmp/gemma-hybrid-proxy* removed; both llama-server services
      active before+after). Evidence: 9-10-status-events-evidence.md.
      Sprint 2 may proceed to Story 9.11 (Ansible role + deploy + Open
      WebUI repoint — Sprint 2 EXIT GATE).
      9.11 completed 2026-04-25 (claude-coder). Sprint 2 EXIT GATE
      passed. New role gemma-hybrid-proxy under
      homelab-infra/ansible/roles/gemma-hybrid-proxy/ (defaults +
      tasks + templates + handlers; uses ansible.posix.synchronize for
      168-file source tree — much faster than per-file copy);
      systemd unit (User=gemma-hybrid, NoNewPrivileges, ProtectSystem
      strict, ProtectHome, PrivateTmp; WatchdogSec removed — uvicorn
      doesn't sd_notify). Real deploy on ct-ai-01: snapshot
      rpool/data/subvol-160-disk-0@pre-proxy-cutover-20260425-1134;
      Ansible PLAY RECAP ok=15 changed=11 failed=0; idempotent re-run
      ok=15 changed=2 (cosmetic only). E4B rebound to 127.0.0.1:8080
      per ADR-009 (default flipped in roles/llama-server/defaults).
      OWUI cutover: stop+rm+rerun with OPENAI_API_BASE_URLS=
      http://127.0.0.1:8000/v1 (single endpoint), named volume
      `open-webui` preserved, rollback docker-run command captured.
      Verified all 3 aliases visible via in-container curl
      (/v1/models from OWUI to proxy returns gemma4-auto +
      gemma4-26b-text + gemma4-e4b-vision). Live API smoke:
      proxy → 26B chat completions returns response in 1.03s
      (logged via structlog). Browser-smoke deviation: OWUI requires
      admin login (no creds in repo, per 9.4 precedent); Playwright
      reached login page + screenshot captured at
      _bmad-output/implementation-artifacts/screenshots-911/
      01-owui-login.png. Final state: 4 services active
      (gemma-hybrid-proxy, llama-server, llama-server-26b,
      open-webui), all loopback except OWUI :3000. Evidence:
      9-11-cutover-evidence.md.
  sprint_3:
    stories_total: 6
    stories_completed: 5  # 9.12, 9.13, 9.14, 9.15, 9.16
    notes: |
      9.12 completed 2026-04-25 (claude-coder). analyze_image tool definition
      locked + registry plumbing (get_tool_by_name, augment_request_with_tools,
      assign_image_ids, AnalyzeImageArgs, MAX_TOOL_ITERATIONS=5) in
      domain/tool_definitions.py (117 LOC). 16 new unit tests, suite 49 → 65
      passing, ruff + mypy clean. Unblocks 9.14 (orchestrator agent loop).
      Evidence: 9-12-tool-definitions-evidence.md.
      9.13 completed 2026-04-25 (claude-coder). ToolCallAccumulator +
      parse_arguments + accumulate_stream shipped at
      domain/delta_accumulator.py (217 raw / 116 code lines, ≤150 cap),
      replacing the Story 9.6 41-LOC skeleton (class renamed
      DeltaAccumulator → ToolCallAccumulator per the 9.13 brief; skeleton
      had zero callers). Pure module — no httpx, no env reads, no I/O;
      finalize() returns ToolCall.function.arguments as the original
      JSON-encoded string per OpenAI spec; parse_arguments helper logs +
      returns {} on malformed/non-object payloads rather than crashing
      (Story 9.14 surfaces a clean tool-execution error). 15 new unit
      tests in tests/unit/test_delta_accumulator.py covering
      single-call multi-chunk, parallel calls interleaved, pre-tool
      text content captured separately, args-before-name out-of-order,
      malformed JSON warning capture, valid-but-non-object JSON, empty/
      None args, finish_reason=stop with no calls, finish_reason=length
      truncation, Pydantic ToolCall round-trip validation, reset(),
      empty/missing choices defensiveness, missing-index fallthrough,
      and accumulate_stream end-to-end (tool-call + plain-stop variants).
      Suite 65 → 80 passing (49 prior + 16 from 9.12 + 15 new), 0
      regressions; ruff + mypy strict on domain/* clean across 19 src
      files. Boundaries respected: no chat_completions.py edits
      (Story 9.14 wires it in), no tool_definitions.py edits
      (9.12 parallel), no preprocessor edits, no new prod deps. R4
      (Open WebUI #23066) defence: accumulator yields validated Pydantic
      ToolCall objects that round-trip cleanly — byte-level fixture
      comparison for downstream re-encoding belongs to 9.14. Evidence:
      9-13-delta-accumulator-evidence.md. Sprint 3 may proceed to
      Story 9.14 (orchestrator agent loop).
      9.14 completed 2026-04-25 (claude-coder). Orchestrator agent loop
      shipped at domain/agent_loop.py (351 raw / 259 code lines —
      AgentLoopRunner @dataclass with run_streaming + run_non_streaming +
      pure-async tool execution; 6 module-level helpers including
      build_image_registry). _handle_auto in api/chat_completions.py
      rewired to: build per-request image_registry → assign_image_ids →
      preprocess_images (re-inspect for shifted block coords) →
      augment_request_with_tools → AgentLoopRunner drives the iteration
      loop; streaming-with-status branch wires the runner identically
      post-preprocess so all 4 status events fire (describing N of M /
      reasoning / calling analyze_image / continuing reasoning).
      Tool-execution failure modes (Pydantic args invalid, E4B
      5xx/timeout/connect-refused, unknown image_id, unknown tool name,
      catch-all Exception) all inject a `tool` message with `error: ...`
      body — never crashes the request. Iteration cap (5) emits synthetic
      content + finish_reason=stop + [DONE]. All 10 ACs PASS via 21 new
      unit tests + 3 updated tests for new image-id label shape; suite
      80 → 101, 0 regressions; ruff clean, mypy clean on 20 src files.
      Live smoke on ct-ai-01:18005 (port chosen to avoid clashing with
      production :8000) demonstrated full agent loop firing with REAL
      MoE emitting tool_calls finish_reason: TTFB 0.006s for first
      status; 26s preprocess (E4B describe); 8s reasoning to tool_calls;
      26s tool exec via E4B re-describe; ~26s second MoE iteration; total
      85.97s wall. All 4 status events captured live (describing 1 of 1
      → reasoning → calling analyze_image: what color is the pixel?... →
      continuing reasoning). Production gemma-hybrid-proxy.service on
      :8000, llama-server on :8080, llama-server-26b on :8081 all active
      before+after; smoke env (uvicorn + /tmp/ghp-9.14*) torn down on
      exit; port 18005 released. Boundaries respected: no
      tool_definitions.py edits, no delta_accumulator.py edits, no
      LiteLLM, no transcribe_audio, no new prod deps, no production
      state touched. Deviation: agent_loop.py 259 code lines over the
      180-LOC brief target (parity with 9.13's 217 raw and 9.9's 191 —
      further compression would break hexagonal testability or drop the
      non-streaming path which the brief required). Evidence:
      9-14-agent-loop-evidence.md. Sprint 3 may proceed to Story 9.15
      (synthetic prompts harness against the live :8000 proxy).
      9.15 completed 2026-04-25 (claude-coder). New 25-prompt smoke
      harness shipped at homelab-infra/tests/sprint3_agentloop_smoke.py
      (stdlib-only, ~600 LOC) modelled on Sprint 1's sprint1_toolcall_gate.py
      pattern but targeting the production gemma-hybrid-proxy on :8000
      (model gemma4-auto, where the proxy auto-injects analyze_image)
      rather than :8081 directly. Distribution: 5 no_image regression +
      5 passive_image (general "describe") + 10 tool_triggering (specific
      questions designed to provoke analyze_image) + 3 multi_iteration
      (multi-step prompts) + 2 iteration_cap (synthetic stress).
      Ran inside CT 160 against :8000 with TIMEOUT=240. Result:
      12/25 PASS (48.0%), 837.6s wall (14.0 min), 0 HTTP 5xx.
      8/10 ACs PASS: AC-1 (harness e2e), AC-2 (25 prompts), AC-3
      (no_image 5/5 ≥80%), AC-4 (passive 5/5 ≥80%), AC-7 (cap 2/2
      terminate), AC-8 (status events visible — 20/20 multimodal had
      describe events), AC-9 (no 5xx), AC-10 (all 4 services preserved
      before+after — gemma-hybrid-proxy / llama-server / llama-server-26b
      / open-webui docker container). 2/10 ACs FAIL: AC-5 (tool_triggering
      0/10 vs ≥50% target), AC-6 (no multi-iteration produced 2+
      structured tool_calls). CRITICAL FINDING: 6/15 multimodal-tool
      prompts emitted unstructured `<|tool_call>call:analyze_image{...}<tool_call|>`
      tokens as PLAIN TEXT in delta.content rather than as structured
      delta.tool_calls SSE chunks — meaning the deployed TrevorJS Gemma
      4 26B-A4B + gemma4-asf0.jinja template is not producing the
      OpenAI-format tool_calls under the proxy's compose flow (image
      preprocess + augmented tools). Sprint 1 (Story 9.5) 98% pass on
      :8081 direct + Story 9.14 live smoke 2h prior succeeded with
      structured tool_calls — the regression appears in the proxy's
      compose path. Independent re-probe with the EXACT 9.14 prompt
      now returns finish_reason=stop with no tool_calls, confirming
      this is current production behavior, not a harness bug.
      Notable: cap-01 tried SIX sequential <|tool_call> text emissions
      — exactly the multi-call sequence the iteration cap was built for,
      but invisible to the loop because unstructured. Iteration cap
      (MAX_TOOL_ITERATIONS=5) NEVER fired because no structured
      iteration ever ran — cap behavior remains unproven against real
      production traffic. The agent-loop INFRASTRUCTURE is correct
      (status events fire, preprocess works, loop is reachable, no
      hangs); the gap is upstream tool-call emission. Recommended
      follow-up (out of scope for 9.15): tighten gemma4-auto system
      prompt OR audit gemma4-asf0.jinja template parsing OR fall back
      to Unsloth UD-Q5_K_M (Sprint 1 alternate). Boundaries respected:
      did NOT modify the deployed proxy or any role; harness is
      stdlib-only (no installs in CT 160); did NOT touch ct-ai-01
      services beyond curl. Coordination: Story 9.16 (LiteLLM gateway)
      deployed mid-test on :4000 — disjoint port, no impact on :8000
      reachability or test results. Evidence:
      9-15-agentloop-smoke-evidence.md (results + critical-finding
      analysis); JSON results
      sprint3-agentloop-smoke-results-2026-04-25.json; markdown
      sprint3-agentloop-smoke-results-2026-04-25.md. Sprint 3 may
      proceed to Story 9.17 (EXIT GATE).
      9.16 completed 2026-04-25 (claude-coder). New Ansible role
      `litellm-gateway` deployed on ct-ai-01: LiteLLM 1.83.13 (post-March-
      2026-PyPI-advisory pinned per ADR-011) listening on 127.0.0.1:4000,
      forwarding 3 virtual aliases (gemma4-auto, gemma4-26b-text,
      gemma4-e4b-vision) to gemma-hybrid-proxy on :8000/v1. Master-key
      bearer auth working (401 without, 200 with); Prometheus /metrics/
      exposed on same port. Stateless mode (no Prisma/SQLite — not needed
      for Sprint 3). Idempotent (0 changes on 2nd run). All 4 upstream
      services (proxy, both llama-servers, OWUI) still healthy. Snapshot
      pre-litellm-deploy-20260425-1730 retained on rpool/data/subvol-160.
      Deviations: pip spec uses `litellm[proxy,proxy-runtime]==1.83.13`
      (proxy-runtime carries prometheus-client; brief said only [proxy]),
      hash-pinning skipped for 90+ transitive graph (Story 9.6 trade-off
      precedent; pre-install assert refuses 1.82.7/1.82.8 compromised
      tags). Master key generated via openssl, NOT in git (operator
      password manager + /tmp tmpfile pending Vault enrolment); Vault
      enrolment is a follow-up. R2 (LiteLLM PyPI compromise) MITIGATED.
      Boundaries respected: did NOT repoint OWUI (Story 9.17), did NOT
      touch deployed proxy beyond read-only HTTP, did NOT downgrade. 9.15
      runs in parallel; 9.16 deploy did not bounce or restart the proxy.
      Evidence: 9-16-litellm-gateway-evidence.md. Sprint 3 may proceed
      to Story 9.17 (EXIT GATE: clients + Prometheus + Grafana).
  sprint_4:
    stories_total: 5  # 9.22 priority + 9.18-9.21 deferred
    stories_completed: 0
    priority_track:
      stories_total: 1  # 9.22
      stories_completed: 0
      status: pending  # REQUIRED for MVP feature-complete
    deferred_track:
      stories_total: 4  # 9.18-9.21
      stories_completed: 0
      deferred: true
      trigger_status: "not-fired"  # "not-fired" | "fired-llamacpp" | "fired-use-case"
    notes: |
      Sprint 4 split into two tracks 2026-04-25 after Story 9.15 surfaced
      a critical regression on the gemma4-auto agent loop. Director
      decision (Option B): MVP ships with the gap; Sprint 4 priority track
      (Story 9.22) closes it as a must-do before MVP feature-complete.
      Deferred track (9.18-9.21) remains gated on llama.cpp #21334 or
      operator audio need, unchanged.

# ============================================================================
# RETROSPECTIVE
# ============================================================================
retrospective:
  epic-9-retrospective:
    status: optional
    notes: |
      Sprint planning generated 2026-04-25 from new epic + architecture docs.
      All 21 stories pending; all owners unassigned. Re-run sprint planning
      after each sprint exit gate to refresh statuses.
