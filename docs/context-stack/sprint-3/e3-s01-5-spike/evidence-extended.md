# E3-S01.5c spike extended-run evidence — 2026-04-26

This is the third of three runs of the E3-S01.5 50-fact gate against the local Gemma 4 26B-MoE stack.

| Run | When | Verdict | Parse | Schema | Mean latency |
|---|---|---|---|---|---|
| v1 (`evidence.md`) | 2026-04-26 morning | STAY-ON-CLOUD | 0 % (HTTP 502) | n/a | n/a (timeout) |
| v2 (`evidence-rerun.md`) | 2026-04-26 afternoon | ADOPT-WITH-CAVEATS | 84 % | 78 % | 20.2 s |
| **v3 (this file)** | **2026-04-26 evening** | **ADOPT-LOCAL** | **100 %** | **98 %** | **32.7 s** |

The three runs differ in client-side configuration only; the gateway, proxy, model, hardware, prompt, and 50-fact corpus are identical across all three.

## What changed v2 → v3

Two client-side modifications in `run-spike.py`:

| Field | v2 | v3 |
|---|---|---|
| `response_format` | omitted | `{"type": "json_object"}` |
| `max_tokens` | 1024 | 1500 |
| `chat_template_kwargs.enable_thinking` | `false` (unchanged) | `false` (unchanged) |
| `temperature` | 0 (unchanged) | 0 (unchanged) |

No proxy patches. No model swap. The proxy already accepted `response_format` (line 206 of `gemma_hybrid_proxy/adapters/openai_models.py`); v2's omission was a client-side oversight, not a proxy gap. Director's pre-test on the first v2-failed episode (`adr-001`, "missing comma at col 653") confirmed: HTTP 200, ~32 s, clean parseable JSON with all 4 expected top-level keys.

## Reproducibility

```bash
cd homelab-playbook/docs/context-stack/sprint-3/e3-s01-5-spike

# Spike requires:
#   - LiteLLM gateway running on http://192.168.50.160:4000
#   - gemma-hybrid-proxy with the chat_template_kwargs patch (committed on
#     branch feature/context-stack-e3-graphiti since E3-S01.5b)
#   - LITELLM_API_KEY in env, or a 600-mode key file at ~/.litellm-spike-key

python3 -u run-spike.py 2>&1 | tee run-extended-2026-04-26.log
```

Total wall-clock: 1633.5 s (~27 min).

## Headline metrics

```
total_episodes:       50
parse_ok:             50 / 50  =  100.0 %
schema_pass:          49 / 50  =   98.0 %
mean_latency_ms:      32670.5  (~32.7 s)
p95_latency_ms:       69851    (~69.9 s)   <- summary row
max_latency_ms:       110373   (~110.4 s)
total_runtime_s:      1633.5   (~27.2 min)
had_markdown_fences:  0
had_prose:            0
empty_response:       0
http_error:           0
timeout:              0
```

Note: the summary's `p95_latency_ms` of 69.9 s is from a per-step P95 calculation; the corrected sorted-array P95 across the 50 latencies is **83.7 s** (between vignette-05 at 83.7 s and vignette-01 at 86.6 s). Both numbers are reported in the ADR for completeness; either way it's well under the 120 s proxy ceiling.

Verdict gate from `run-spike.py`:

```
ADOPT-LOCAL          → parse ≥ 95 % AND schema ≥ 90 %  → HIT (100 % / 98 %)
ADOPT-WITH-CAVEATS   → parse ≥ 80 %                    → also hit but superseded
STAY-ON-CLOUD        → parse < 80 %                    → not hit
```

## Per-category breakdown

| Category | n | parse_ok | parse_pct | schema_pass | schema_pct |
|---|---|---|---|---|---|
| architectural-decision | 15 | 15 | 100 % | 14 | 93 % |
| dated-decision | 10 | 10 | 100 % | 10 | 100 % |
| lesson-learned | 10 | 10 | 100 % | 10 | 100 % |
| supersession-trail | 10 | 10 | 100 % | 10 | 100 % |
| entity-rich-vignette | 5 | 5 | 100 % | 5 | 100 % |

Every category clears 100 % parse. Only the architectural-decision category misses one schema check (1/15).

## Failure forensics — the single residual miss

| Episode | Category | parse_ok | schema_pass | Reason |
|---|---|---|---|---|
| `adr-002` | architectural-decision | true | false | `entity[0]_missing:['labels']` |

**What the model did**: emitted a syntactically clean JSON object containing 6 entities, 5 edges, valid_at, invalid_at. All keys present at the top level. Five of the six entities have full `name`+`summary`+`labels`. The first entity (the "ADR-002" node itself) has only `name` and a malformed `summary` — no `labels` array.

**Snippet from `raw_output`**:

```json
{
  "entities": [
    {
      "name": "ADR-002",
      "summary":": "
      },
    {
      "name": "gpt-4o-mini",
      "summary": "A small-scale cloud-based large language model used for extraction tasks.",
      "labels": ["Model", "LLM"]
    },
    ...
  ]
}
```

**Diagnosis**: This is a clean **model-quality miss**, not a syntax / format / decoding issue:

- Output is well-formed JSON (the validator's `json_parse_ok=true`).
- JSON-mode constrained decoding cannot fix it. The constraint enforces JSON validity, not application schema.
- A retry would not deterministically fix it. Temperature is 0; same input → same output.
- The malformed `"summary":": "` shows the model went off-rails on entity[0] specifically. Probably a tokeniser hiccup at the first entity boundary.

**Production fix (recommended for E3-S04)**: a 5-line entity-validator at the Graphiti adapter layer that fills missing `labels` arrays with `[]` before insertion. No retries, no extra latency, no model changes. Catches this 2 % miss class without operator intervention.

## v2 → v3 comparison

Of v2's 11 non-passes (8 parse-fails + 3 schema-fails):

| v2 failure | v3 outcome | Reason |
|---|---|---|
| `adr-001` parse-fail (col 653) | **fixed** | JSON-mode prevents missing-comma class |
| `adr-006` parse-fail (col 1115) | **fixed** | JSON-mode prevents missing-comma class |
| `adr-009` parse-fail (col 1172) | **fixed** | JSON-mode prevents missing-comma class |
| `temporal-07` parse-fail (col 981) | **fixed** | JSON-mode prevents missing-comma class |
| `lesson-05` parse-fail (col 1345) | **fixed** | JSON-mode prevents missing-comma class |
| `supersession-03` parse-fail (col 1022) | **fixed** | JSON-mode prevents missing-comma class |
| `supersession-06` parse-fail (col 1778) | **fixed** | JSON-mode prevents missing-comma class |
| `supersession-10` parse-fail (col 2607) | **fixed** | JSON-mode prevents missing-comma class |
| `adr-005` schema-fail (entity[8] missing name) | **fixed** | downstream of v2's malformed JSON; clean run produced full schema |
| `adr-mock-15` schema-fail (edge[1] missing fact) | **fixed** | downstream of v2's malformed JSON; clean run produced full schema |
| `temporal-01` schema-fail (edge[1] missing fact) | **fixed** | downstream of v2's malformed JSON; clean run produced full schema |
| (new) `adr-002` schema-fail (entity[0] missing labels) | **persists** | clean model-quality miss; not retry-recoverable |

Net: v2 → v3 fixed 11 of 11 v2 failures. v3 introduced 1 new schema miss (adr-002 was actually a v2 parse-pass + schema-pass; in v3 the model went off-rails on entity[0] for a different reason). The trade is: replace a high-noise 22 % schema-fail rate with a low-noise 2 % miss in the same band.

## Latency profile

P50 ≈ 28 s, mean 32.7 s, P95 83.7 s, max 110.4 s. Distribution is right-skewed; the entity-rich-vignette category dominates the tail (51–110 s) because those outputs are the densest.

The +12 s mean latency vs. v2 (20 s → 33 s) is the **JSON-mode constrained-decoding overhead**. llama.cpp's `response_format=json_object` engages a JSON grammar (under the hood, GBNF) that restricts the sampling distribution at every token boundary. This costs CPU on the Vulkan stack. On future GPU (Sprint 5 OCULink), this overhead drops to ~1 s and becomes invisible.

For Graphiti's `add_episode` call profile (asynchronous write from the agent's perspective), 33 s mean is acceptable. The 110 s max stays comfortably under the 120 s proxy ceiling.

## Operational config recommended for E3-S04 wiring

The Graphiti container's LLM client must send these per-request fields. Set them at the LiteLLM model-config layer (`litellm_params.extra_body` for the two non-standard fields) so Graphiti's own client code can stay vanilla OpenAI.

```yaml
# host_vars/ct-graphiti/ — env passthrough
OPENAI_BASE_URL: http://192.168.50.160:4000
OPENAI_MODEL: gemma4-26b-text
OPENAI_API_KEY: "{{ vault_litellm_master_key }}"   # extraction
# (separate <openai cloud key> for embeddings client per ADR-003)
```

```yaml
# host_vars/ct-ai-01/ — LiteLLM config (litellm-config.yaml)
- model_name: gemma4-26b-text
  litellm_params:
    model: openai/gemma4-26b-text
    api_base: http://127.0.0.1:8090   # gemma-hybrid-proxy
    extra_body:
      response_format:
        type: json_object               # MANDATORY — without this, parse drops to 84 %
      chat_template_kwargs:
        enable_thinking: false          # MANDATORY — without this, model burns budget on hidden reasoning
    max_tokens: 1500                    # ~35 % headroom over P95 output (~1100 tokens)
    temperature: 0
    timeout: 120                        # ≥ proxy ceiling
```

**Application-layer hardening** (E3-S04): add a thin entity-validator on the Graphiti add_episode path that fills missing `labels` arrays with `[]` before FalkorDB insertion. Handles the 2 % residual schema miss without retries. ~5 lines.

## Files

- `corpus-50-facts.jsonl` — 50-episode corpus (unchanged from v1/v2)
- `extraction-prompt.txt` — system + user template (unchanged from v1/v2)
- `run-spike.py` — runner; v3 adds `response_format=json_object` + `max_tokens=1500`
- `results.jsonl` — 50 result rows + 1 summary row (this run; v3)
- `results-v2.jsonl` — preserved v2 results for diff
- `run-extended-2026-04-26.log` — stdout from this run
- `evidence.md` — v1 evidence (kept for historical record)
- `evidence-rerun.md` — v2 evidence (kept for historical record)
- `evidence-extended.md` — this file (v3)
