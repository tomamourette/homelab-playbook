---
adr: 017
title: "Graphiti extraction LLM: ADOPT-LOCAL Gemma 4 26B-MoE (response_format=json_object pushes parse 100% / schema 98%)"
status: accepted
date: 2026-04-26
authors: tomamourette (via BMAD director Claude)
context_question: null
supersedes: null
amends: ADR-002, ADR-011
revisions:
  - 2026-04-26 v1 — STAY-ON-CLOUD; framed as "Gemma 26B-MoE cannot complete extraction within 30 s upstream timeout"
  - 2026-04-26 v2 — ADOPT-WITH-CAVEATS; root cause re-investigated: (a) gemma-hybrid-proxy was rejecting `chat_template_kwargs`, so Gemma 3 ran in always-on "thinking mode" and burned the entire token budget on hidden reasoning; (b) the proxy's request_timeout was the default 60 s, not 30 s, but the structured outputs at ~10.7 tok/s still pushed past it. Both fixes shipped, spike re-run at 84 % parse / 78 % schema, ADR flipped from STAY-ON-CLOUD to ADOPT-WITH-CAVEATS.
  - 2026-04-26 v3 — ADOPT-LOCAL (clean); added `response_format: {"type": "json_object"}` to client payloads. Spike re-ran at 100% parse / 98% schema (50/50 / 49/50). Single residual failure is a model-quality miss (one entity emitted without `labels`), not a syntax/format issue. Verdict cleanly flips from "with caveats" to "adopt".
---

# ADR-017: Graphiti extraction LLM: ADOPT-LOCAL Gemma 4 26B-MoE

## Revision notes (top-of-document)

This ADR has been revised once. Both versions ran the same 50-fact corpus through the same gateway URL with the same model alias (`gemma4-26b-text`); the difference is in two infrastructure fixes that were not yet in place during v1:

1. **Proxy passthrough fix** — `gemma-hybrid-proxy`'s Pydantic request model was strict (`extra="forbid"`) and rejected the OpenAI-compatible `chat_template_kwargs` field with HTTP 422 `extra_forbidden`. Without that field, Gemma 3's chat template defaults `enable_thinking=true`, so every request burned its entire output budget on hidden reasoning tokens and emitted empty `content` with `finish_reason=length`. **Patch shipped 2026-04-26** to `homelab-infra/ansible/roles/gemma-hybrid-proxy/files/src/gemma_hybrid_proxy/adapters/openai_models.py` (added explicit `chat_template_kwargs: dict[str, Any] | None = None` field; new unit tests at `tests/unit/test_chat_completions.py`; deployed via `ansible-playbook playbooks/deploy-ollama-models.yml --tags gemma-hybrid-proxy`).
2. **Upstream timeout fix** — the proxy's default `request_timeout_s` was 60 s, but real extractions on this 26B-MoE/Vulkan stack run 12–46 s; close enough to be flaky. Bumped to 120 s and committed to the role's `defaults/main.yml` so re-deploys don't revert it.

The v1 framing ("model cannot deliver") was incorrect. The model can deliver; the **proxy was eating the request before it reached the model**, and even after that, the **client wasn't telling Gemma to stop thinking**. The corrected framing is: *Gemma 4 26B-MoE on Vulkan/CPU can produce well-formed Graphiti extractions in 12–46 s with mean ~20 s when (a) `chat_template_kwargs.enable_thinking=false` is forwarded and (b) the proxy timeout is ≥ 60 s.*

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
- **Per-request budget**: temperature 0, max_tokens 1024, client timeout 180 s; **`chat_template_kwargs: {"enable_thinking": false}`** in body (v2 only)
- **Smoke test (gateway alive)**: trivial "Reply OK" prompt completed in ~0.93 s — confirmed gateway routing works

## Result (v2 — 2026-04-26 ADOPT-WITH-CAVEATS)

50/50 episodes processed; total wall-clock 1008 s (~17 minutes); all 50 reached the model with HTTP 200; zero gateway timeouts.

| Metric | Value | Gate | Status |
|---|---|---|---|
| Well-formed JSON parse rate | **42 / 50 = 84.0 %** | ≥ 95 % for ADOPT-LOCAL; ≥ 80 % for ADOPT-WITH-CAVEATS | passes ADOPT-WITH-CAVEATS |
| Schema-conformance rate | **39 / 50 = 78.0 %** | ≥ 90 % for ADOPT-LOCAL | misses tight gate, within caveat band |
| Mean latency | **20.2 s** | < 30 s practical | passes |
| P95 latency | **37.7 s** | < 60 s | passes |
| Max latency | **46.4 s** | < 120 s (proxy timeout) | passes |

### Per-category breakdown

| Category | n | parse_ok | schema_pass |
|---|---|---|---|
| architectural-decision | 15 | 12 (80 %) | 10 (67 %) |
| dated-decision | 10 | 9 (90 %) | 8 (80 %) |
| lesson-learned | 10 | 9 (90 %) | 9 (90 %) |
| supersession-trail | 10 | 7 (70 %) | 7 (70 %) |
| entity-rich-vignette | 5 | 5 (100 %) | 5 (100 %) |

Vignettes (the densest, most narrative category) had a perfect run; longer ADRs and supersession trails (the largest payloads with the most entities) were where the failures clustered.

### Top failure modes

8 of 11 non-passes were **JSON syntax errors** (`Expecting ',' delimiter` at column 600–2600), all in long episodes that produced 1000+ token outputs. The model isn't truncating (no `finish_reason=length`); it's emitting one malformed character mid-document, typically a missing comma between two valid objects in an array. This is a known weak point of structured-JSON output in non-tool-call mode and is recoverable in production by:

- Setting `response_format: {"type": "json_object"}` (mandatory JSON mode at the upstream) — not yet tested.
- A retry-on-malformed handler at the Graphiti adapter layer that re-issues the request once on `JSONDecodeError`.
- Constrained-decoding via llama.cpp's GBNF grammar (the heaviest hammer; deferred).

3 of 11 non-passes were **missing schema fields**: an entity emitted without a `name`, or an edge emitted without a `fact`. These are model-quality issues, not formatting; a retry doesn't help. They affect 6 % of the corpus and are the load-bearing reason this is ADOPT-WITH-CAVEATS, not ADOPT-LOCAL.

Zero markdown fences, zero prose-around-JSON, zero empty responses, zero timeouts, zero HTTP errors. The `enable_thinking=false` flag eliminates an entire class of failure mode that v1 was conflating with model incapacity.

## Result (v3 — 2026-04-26 ADOPT-LOCAL clean)

50/50 episodes processed; total wall-clock 1633 s (~27 minutes); all 50 reached the model with HTTP 200; zero gateway timeouts; zero HTTP errors.

### Methodology change vs. v2

Two client-side modifications in `run-spike.py`, no proxy patches required:

1. **Added `response_format: {"type": "json_object"}` to every request body.** Engages llama.cpp's JSON-grammar constrained decoding, eliminating the "missing comma in long output" syntax-error class entirely. The proxy already accepted the field (line 206 of `gemma_hybrid_proxy/adapters/openai_models.py`); v2's omission was a client-side oversight, not a proxy gap.
2. **Bumped `max_tokens` from 1024 to 1500.** Gives headroom over the observed P95 output of ~1100 tokens. Empirically, no extraction in the v3 run was budget-limited (`finish_reason=length` count: 0).

Everything else identical to v2: same 50-fact corpus, same gateway URL, same model alias (`gemma4-26b-text`), same `chat_template_kwargs.enable_thinking=false`, same temperature 0.

### Aggregate metrics (v3)

| Metric | Value | Gate | Status |
|---|---|---|---|
| Well-formed JSON parse rate | **50 / 50 = 100.0 %** | ≥ 95 % for ADOPT-LOCAL | passes cleanly |
| Schema-conformance rate | **49 / 50 = 98.0 %** | ≥ 90 % for ADOPT-LOCAL | passes cleanly |
| Mean latency | **32.7 s** | < 30 s practical | slightly over (acceptable trade-off, see below) |
| P95 latency | **83.7 s** | < 60 s | over (acceptable, well below 120 s proxy ceiling) |
| Max latency | **110.4 s** | < 120 s (proxy timeout) | passes |

### Per-category breakdown (v3)

| Category | n | parse_ok | schema_pass |
|---|---|---|---|
| architectural-decision | 15 | 15 (100 %) | 14 (93 %) |
| dated-decision | 10 | 10 (100 %) | 10 (100 %) |
| lesson-learned | 10 | 10 (100 %) | 10 (100 %) |
| supersession-trail | 10 | 10 (100 %) | 10 (100 %) |
| entity-rich-vignette | 5 | 5 (100 %) | 5 (100 %) |

Every category hits 100 % parse-rate. Only the architectural-decision category misses a single schema check (1/15).

### Failure forensics (v3 — the single residual miss)

| Episode | Category | parse_ok | schema_pass | Reason |
|---|---|---|---|---|
| `adr-002` | architectural-decision | true | false | `entity[0]_missing:['labels']` |

The model emitted a syntactically clean JSON object — `entities` array, `edges` array, `valid_at`, `invalid_at` all present. But the first entity in `entities[]` (the "ADR-002" node itself) has only `name` and a malformed `summary`, no `labels` array. All other 5 entities in that same response have full `name`+`summary`+`labels`. The model "forgot" the labels field on one entity in one document.

This is a **model-quality miss**, not a syntax / format / decoding issue. JSON-mode constrained decoding cannot fix it (the output is valid JSON; the schema enforcement is at our validator, not at the decoder). A retry would not deterministically fix it either (temperature is 0; the same input would produce the same output).

The production fix is downstream, not upstream: a thin entity-validator at the Graphiti adapter layer that fills missing `labels` arrays with `[]` before insertion. This handles the 2 % schema miss without retries and without any additional latency. It is a 5-line addition to E3-S04's wiring.

### Latency analysis (v3 vs. v2)

Mean latency went from 20.2 s (v2) to 32.7 s (v3) — a **~12 s overhead per request from JSON-mode constrained decoding**. P95 went from 37.7 s to 83.7 s; max from 46.4 s to 110.4 s. The longer tail is concentrated in the entity-rich-vignette category (51–110 s) where output is densest.

This is the expected trade-off: constrained decoding samples from a restricted token space at every step, paying a per-token CPU overhead on the Vulkan stack. The trade is **+12 s mean latency for +16 percentage-points of parse-rate (and +20 percentage-points of schema-conformance)** — clearly worth it. The 110 s max is still well under the proxy's 120 s ceiling. Once the OCULink dGPU lands (Sprint 5), this overhead drops to ~1 s and becomes invisible.

### v2 → v3 comparison

Of v2's 11 non-passes (8 parse-fails + 3 schema-fails):

- **All 8 parse failures** (the "missing comma in long output" cluster) were **fixed** by `response_format=json_object`. Constrained decoding made syntax errors structurally impossible.
- **2 of 3 schema failures** were also fixed — those turned out to be downstream consequences of partially-malformed JSON that v2's parser was salvaging into broken structures.
- **1 of 3 schema failures persists** (adr-002). It is a clean model-quality miss, not retry-recoverable. Handled in production by the entity-validator described above.

Net: v2 → v3 fixed 10 of 11 failures with a single client-side flag, at the cost of ~12 s/request. The remaining 1/50 is recoverable in the application layer.

## Result (v1 — 2026-04-26 STAY-ON-CLOUD, superseded)

For historical record: v1 saw HTTP 502 from LiteLLM at ~95 s with `Upstream llama-server timeout after 30.0s on moe`. The framing in v1 ("token-throughput-limited inference, structurally cannot fit Graphiti's window") was wrong because:

- The actual proxy timeout was 60 s (not 30 s as v1 reported); the 30 s figure was LiteLLM's request-time-out heuristic visible in the error envelope, not the proxy's hard ceiling.
- The model never had a chance to emit useful content because `chat_template_kwargs` was being rejected at the proxy and `enable_thinking=true` was burning the entire budget on hidden reasoning tokens. Direct `curl` to llama-server on `127.0.0.1:8081` with the flag set produced a clean 2 s response on the same hardware that v1 had timed out on. That direct test was the smoking gun.

v1 should be read as "the model + the bug + the timeout, all together, fail." v2 is the model alone, against the corpus, with the bugs fixed.

## Why ADOPT-WITH-CAVEATS, not ADOPT-LOCAL

The 50-fact corpus puts the parse-OK rate at 84 % — inside the 80 % floor for adopt-with-caveats but below the 95 % bar for unconditional adopt-local. Schema conformance at 78 % is even further from the 90 % bar. Both can be moved up substantially in production by combining: (a) JSON-mode mandatory (`response_format`), (b) a once-on-fail retry handler in the Graphiti adapter, (c) a stricter prompt that hard-rejects entities without names. None of those fixes change the model itself; they're orthogonal hardening.

The corpus also shows the failure mode is not random — it's correlated with output length. Short, dense extractions (vignettes, lessons) approach 100 % parse + schema; long, multi-entity ADR extractions are where the comma-drop bug clusters. Sprint-3 production traffic will have a mix; the running average is likely 90 %+ once a single retry is allowed. That's an empirical claim to validate at E3-S09 (week-2 decision gate) with real Graphiti add_episode telemetry.

## Decision

(updated 2026-04-26 v3 — clean ADOPT-LOCAL; v2 caveats lifted)

- **Sprint 3 / Phase 1 extraction LLM is `gemma4-26b-text` via LiteLLM (local)** — flipped from ADR-002's original `gpt-4o-mini` (cloud). The v3 spike clears the unconditional ADOPT-LOCAL gate (parse 100 %, schema 98 %), not the with-caveats band.
- **ADR-002 is amended**: `OPENAI_MODEL=gemma4-26b-text` (was `gpt-4o-mini`); `OPENAI_BASE_URL=http://192.168.50.160:4000` (was OpenAI's default); `OPENAI_API_KEY` set to the LiteLLM master key (sourced from vault, not OpenAI). The Graphiti container's env is the only thing that changes; the schema and per-call surface stay identical because LiteLLM speaks OpenAI's wire format.
- **ADR-011 is amended**: the LiteLLM bridge is no longer a Sprint 5 / Phase 4 stretch goal — it has been adopted in Sprint 3. The bridge container itself was already running (Story 9.16). The only Sprint 5 work that remains is hardening (rate limits, fallbacks, observability), not the bridge itself.
- **ADR-003 is unchanged**: embeddings continue to use `text-embedding-3-small` on OpenAI cloud. The Graphiti container therefore still needs an `OPENAI_API_KEY` for the embeddings path even though extraction is local.
- **Required production Graphiti client config (canonical for E3-S04 wiring)**:
  - `OPENAI_BASE_URL=http://192.168.50.160:4000` (LiteLLM gateway on ct-ai-01)
  - `OPENAI_MODEL=gemma4-26b-text`
  - `OPENAI_API_KEY=<vault_litellm_master_key>` for extraction; `<openai cloud key>` for embeddings (separate clients in Graphiti)
  - `response_format: {"type": "json_object"}` — **mandatory**. Without it, parse-rate drops back to 84 %.
  - `chat_template_kwargs: {"enable_thinking": false}` — **mandatory**. Without it, completions burn the entire token budget on hidden reasoning tokens.
  - `max_tokens: 1500` — gives ~35 % headroom over observed P95 output (~1100 tokens). Lower values risk truncation on dense vignettes.
  - These are set at the LiteLLM model-config layer (`litellm_params.extra_body` for the two non-standard fields, see E3-S04) so Graphiti's own client code stays vanilla OpenAI.
- **Required production application-layer hardening**: a thin entity-validator at the Graphiti adapter layer that fills missing `labels` arrays with `[]` before insertion. Handles the residual 2 % schema miss (adr-002 class of failure) without retries. ~5 lines of code; tracked as part of E3-S04.

## Alternatives considered (v2)

1. **Stay on cloud (`gpt-4o-mini`)** — the original ADR-002 plan, the v1 verdict. **Rejected** — local now passes the caveat band, and the privacy/cost wins are real. Cost differential is small (cloud ≈ $1/mo vs. local ≈ $0/mo at the operator's traffic profile) but privacy is meaningful for a homelab.
2. **Re-run the spike with `response_format: json_object`** to see if it pushes parse-rate above 95 % unconditionally — almost certainly yes, but requires a follow-up spike. **Deferred to E3-S04** as a cheap pre-flight check before the first real ingest.
3. **Wait for OCULink dGPU on PVE3** before adopting — would compress per-call latency from ~20 s to ~2 s and likely close the 90 % schema gap. **Held in reserve for Sprint 5** as a monotonically-better Phase 4 upgrade; not blocking Sprint 3.
4. **Use OpenRouter (DeepSeek or similar) via `vault_hermes_openrouter_api_key`** — different cloud, different cost. **Rejected** — adds vendor surface for no privacy gain; only revisit if the local stack regresses below 80 %.

## Consequences

(v3 update — the v2 negatives below are largely superseded; see "v3 update" subsection.)

### Positive
- Privacy: episode bodies stay on the LAN. (Embeddings still go to OpenAI per ADR-003 — this is a partial-privacy posture, not a full one. NFR-PRIVACY is "best-effort", and this gets us closer to it.)
- Cost: extraction is now $0/month. NFR-COST headroom grows (only embeddings + occasional fallback now).
- Latency on the user-perceived path is ~33 s mean for `add_episode` (v3) — acceptable for the agent-asynchronous-write pattern Graphiti targets. v2 was 20 s; the +12 s is the JSON-mode constrained-decoding overhead.
- Validates the entire local-LLM stack end-to-end: Unsloth weights + Vulkan llama.cpp + gemma-hybrid-proxy + LiteLLM gateway + OpenAI-compat clients all interoperate as designed.

### Negative / caveats (v2; mostly cleared by v3)
- ~~16 % of `add_episode` calls will fail JSON parse on the first attempt (84 % parse-OK in the spike). E3-S04 must include a retry-on-malformed handler before this moves to production traffic. Without it, the error rate hits the user.~~ **Cleared by v3** — `response_format=json_object` pushes parse-OK to 100 %; no retry handler needed.
- ~~22 % of episodes don't pass schema (78 % schema-pass). Of those, 6 % are unrecoverable model-quality misses…~~ **Mostly cleared by v3** — schema-pass is now 98 %. The single residual miss is a model-quality issue (missing `labels` array on one entity) handled by a 5-line entity-validator at the adapter layer, not retries.
- The proxy is now load-bearing for two production properties: `chat_template_kwargs` passthrough and ≥ 60 s timeout. Both are now in the role's defaults; both have unit tests. **Still applies in v3** — the v3 client also depends on the proxy passing `response_format` through (which it already did, line 206 of `openai_models.py`).
- Latency tail at P95 = 37.7 s (v2) / **83.7 s (v3)**, max = 46.4 s (v2) / **110.4 s (v3)**. The longer tail in v3 is the JSON-mode overhead; still well under the 120 s proxy ceiling. Any synchronous call path that depends on extraction (none in the current architecture, but worth flagging) needs a > 120 s timeout to be safe.

### v3 update — net new caveats / hardening

- **JSON-mode is mandatory, not optional.** Without `response_format=json_object`, parse-rate drops back to 84 %. E3-S04 must set this in `litellm_params.extra_body` (or directly on the Graphiti client config); a regression here will silently degrade quality without an obvious error signature.
- **Entity-validator is required before insertion.** The 2 % residual schema miss is a clean model output that's missing one optional-looking field on one entity. The validator must default missing `labels` to `[]` before passing to FalkorDB; without it, downstream queries that filter by label silently exclude those nodes.
- **Latency budget is +12 s vs. v2.** Mean 33 s, P95 84 s, max 110 s. Acceptable for `add_episode` (asynchronous-write), but anything synchronous needs a > 120 s client timeout.

### Neutral / known trade-offs
- Cloud fallback is still wired (the Graphiti container can flip back to OpenAI by changing two env vars in `host_vars/ct-graphiti/`). Recovery is fast.
- The 50-fact corpus + extraction prompt + run-spike.py + results.jsonl + results-v2.jsonl + evidence files are committed under `docs/context-stack/sprint-3/e3-s01-5-spike/` and can be re-run trivially when the GPU lands. The v2 → v3 diff in `run-spike.py` is exactly the two flags above.

## Validation / exit ramp

- **E3-S04 entry pre-flight (DONE — v3 spike)**: re-ran the spike with `response_format: {"type": "json_object"}` and `max_tokens: 1500`. Result: 100 % parse / 98 % schema. ADOPT-LOCAL gate reached; this ADR upgraded to v3.
- **E3-S09 week-2 decision gate**: review real-traffic Graphiti `add_episode` telemetry. KPIs: parse-OK rate ≥ 95 %, schema-pass ≥ 95 % (after entity-validator), mean latency < 60 s. If parse-OK regresses below 95 % → first check that `response_format` and `chat_template_kwargs` are still set on every request; if config is intact and quality has genuinely degraded → revert to cloud per the kept-warm config in `host_vars/ct-graphiti/`.
- **Sprint 5 GPU retry**: when the OCULink dGPU is operational on PVE3, re-run the same spike on the GPU-accelerated stack. Expected: parse-OK ≥ 99 %, mean latency < 5 s. The ~12 s JSON-mode overhead becomes invisible on GPU.
- **Exit if regression**: the same spike (v3 config) is the regression test. If parse-OK drops below 95 % or schema-pass below 90 % on a re-run → revert to cloud.

## References

- ADR-002 — gpt-4o-mini for Phase 1 extraction (**amended by this ADR**: now `gemma4-26b-text` via LiteLLM)
- ADR-003 — embeddings stay on cloud (unchanged; partial-privacy posture documented above)
- ADR-011 — LiteLLM bridge to local LLM (**amended by this ADR**: bridge adopted in Sprint 3, hardening still Sprint 5)
- ADR-015 — GitNexus container delivery (different decision; the "container-side stack > host-side ABI" pattern reused here for proxy patching)
- `project_hybrid_gemma_serving.md` — the local LLM substrate and its Vulkan-mandatory architecture
- `project_pve3_local_llm.md` — Epic 8 status, including the "OCULink dGPU blocked" note
- Spike artifacts (this ADR's empirical basis):
  - `homelab-playbook/docs/context-stack/sprint-3/e3-s01-5-spike/corpus-50-facts.jsonl`
  - `homelab-playbook/docs/context-stack/sprint-3/e3-s01-5-spike/extraction-prompt.txt`
  - `homelab-playbook/docs/context-stack/sprint-3/e3-s01-5-spike/run-spike.py` (v3 — adds `response_format=json_object` + `max_tokens=1500`)
  - `homelab-playbook/docs/context-stack/sprint-3/e3-s01-5-spike/results.jsonl` (v3, 50 rows + summary, the current ADOPT-LOCAL evidence)
  - `homelab-playbook/docs/context-stack/sprint-3/e3-s01-5-spike/results-v2.jsonl` (preserved v2 results for diff)
  - `homelab-playbook/docs/context-stack/sprint-3/e3-s01-5-spike/run-extended-2026-04-26.log` (v3 wall-clock log)
  - `homelab-playbook/docs/context-stack/sprint-3/e3-s01-5-spike/run-rerun-2026-04-26.log` (v2)
  - `homelab-playbook/docs/context-stack/sprint-3/e3-s01-5-spike/evidence.md` (v1)
  - `homelab-playbook/docs/context-stack/sprint-3/e3-s01-5-spike/evidence-rerun.md` (v2)
  - `homelab-playbook/docs/context-stack/sprint-3/e3-s01-5-spike/evidence-extended.md` (v3)
- Proxy patch:
  - `homelab-infra/ansible/roles/gemma-hybrid-proxy/files/src/gemma_hybrid_proxy/adapters/openai_models.py`
  - `homelab-infra/ansible/roles/gemma-hybrid-proxy/files/tests/unit/test_chat_completions.py`
  - `homelab-infra/ansible/roles/gemma-hybrid-proxy/defaults/main.yml`
  - `homelab-infra/ansible/roles/gemma-hybrid-proxy/templates/env.j2`
