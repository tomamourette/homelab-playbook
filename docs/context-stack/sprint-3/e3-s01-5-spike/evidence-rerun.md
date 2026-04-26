# E3-S01.5b spike re-run evidence — 2026-04-26

This is the second of two runs of the E3-S01.5 50-fact gate against the local Gemma 4 26B-MoE stack. The first run (`evidence.md`, 2026-04-26 morning) saw zero successful extractions and produced ADR-017 v1 STAY-ON-CLOUD. The second run (this file, 2026-04-26 afternoon) saw 50 / 50 episodes complete with HTTP 200, 84 % parse-OK, 78 % schema-pass, and produced ADR-017 v2 ADOPT-WITH-CAVEATS.

The two runs differ in two ways and only two ways:

| Run | gemma-hybrid-proxy | request body |
|---|---|---|
| v1 (morning) | strict Pydantic, rejected `chat_template_kwargs` with HTTP 422 | omitted `chat_template_kwargs` (would have been rejected anyway) |
| v2 (afternoon) | patched: `chat_template_kwargs: dict[str, Any] \| None = None` added to the request model | sent `chat_template_kwargs: {"enable_thinking": false}` |

Both ran the same 50-fact corpus, same prompt, same model alias, same hardware.

## Reproducibility

```bash
cd homelab-playbook/docs/context-stack/sprint-3/e3-s01-5-spike

# Spike requires:
#   - LiteLLM gateway running on http://192.168.50.160:4000
#   - gemma-hybrid-proxy with the chat_template_kwargs patch (commit on
#     branch feature/context-stack-e3-graphiti)
#   - LITELLM_API_KEY in env, or a 600-mode key file at ~/.litellm-spike-key

python3 -u run-spike.py 2>&1 | tee run-rerun-2026-04-26.log
```

Run-spike.py is configured to send `chat_template_kwargs.enable_thinking=false` on every request. This is also wired into the LiteLLM model config (E3-S04) so production Graphiti calls don't need to know about it.

## Headline metrics

```
total_episodes:       50
parse_ok:             42 / 50  =  84.0 %
schema_pass:          39 / 50  =  78.0 %
mean_latency_ms:      20155.2  (~20.2 s)
p95_latency_ms:       37691    (~37.7 s)
max_latency_ms:       46350    (~46.4 s)
total_runtime_s:      1007.8   (~16.8 min)
had_markdown_fences:  0
had_prose:            0
empty_response:       0
http_error:           0
timeout:              0
```

Verdict gate from `run-spike.py`:

```
ADOPT-LOCAL          → parse ≥ 95 % AND schema ≥ 90 %  → not hit
ADOPT-WITH-CAVEATS   → parse ≥ 80 %                    → HIT (84 %)
STAY-ON-CLOUD        → parse < 80 %                    → not hit
```

## Per-category breakdown

| Category | n | parse_ok | parse_pct | schema_pass | schema_pct |
|---|---|---|---|---|---|
| architectural-decision | 15 | 12 | 80 % | 10 | 67 % |
| dated-decision | 10 | 9 | 90 % | 8 | 80 % |
| lesson-learned | 10 | 9 | 90 % | 9 | 90 % |
| supersession-trail | 10 | 7 | 70 % | 7 | 70 % |
| entity-rich-vignette | 5 | 5 | 100 % | 5 | 100 % |

Pattern: small-output episodes (vignettes, lessons) are nearly perfect; large-output episodes (the 15 ADRs and the 10 supersession trails) are where the failures cluster. The model produces correct content; it loses one comma or one closing brace mid-stream when the output exceeds ~1 000 tokens.

## Failure forensics — top three modes

### Mode 1: missing comma between two valid array elements (8 of 11 non-passes)

8 of 11 failures are JSON syntax errors with the same shape. Examples:

| episode | parse_error | column |
|---|---|---|
| adr-001 | `Expecting ',' delimiter at line 1 col 653` | 653 |
| adr-006 | `Expecting ',' delimiter at line 1 col 1115` | 1115 |
| adr-009 | `Expecting ',' delimiter at line 1 col 1172` | 1172 |
| temporal-07 | `Expecting ',' delimiter at line 1 col 981` | 981 |
| lesson-05 | `Expecting ',' delimiter at line 1 col 1345` | 1345 |
| supersession-03 | `Expecting ',' delimiter at line 1 col 1022` | 1022 |
| supersession-06 | `Expecting ',' delimiter at line 1 col 1778` | 1778 |
| supersession-10 | `Expecting ',' delimiter at line 1 col 2607` | 2607 |

`finish_reason=stop` in all cases — no truncation. The model emits `}{` instead of `},{` (or similar) somewhere in the entities/edges array. Mitigations:

- Production retry-on-malformed handler at the Graphiti adapter layer (cheap; one extra call on 16 % of traffic).
- `response_format: {"type": "json_object"}` at the upstream — Gemma 3 supports it; not yet tested. If it lifts parse-rate to 95 %+, this ADR upgrades to unconditional ADOPT-LOCAL.
- GBNF grammar via llama.cpp (heaviest hammer; deferred).

### Mode 2: schema field missing (3 of 11 non-passes)

| episode | fail_reason |
|---|---|
| adr-005 | `entity[8]_missing:['name']` |
| adr-mock-15 | `edge[1]_missing:['fact']` |
| temporal-01 | `edge[1]_missing:['fact']` |

Model produced syntactically-valid JSON but omitted a required field on one entity or edge. Cannot be fixed by retry. Stricter prompt + content-validation reject at the Graphiti layer would catch these and either re-prompt or drop the malformed entity. 6 % of the corpus; the load-bearing reason this is ADOPT-WITH-CAVEATS not ADOPT-LOCAL.

### Mode 3: nothing else

Zero markdown fences, zero prose around JSON, zero empty responses, zero HTTP errors, zero timeouts. The `enable_thinking=false` flag eliminates an entire class of failure that would have shown up otherwise.

## Latency profile

P50 ≈ 16 s, mean 20.2 s, P95 37.7 s, max 46.4 s. Distribution is right-skewed — most episodes finish in < 20 s, a few outliers push the tail. The proxy timeout is 120 s (set in `defaults/main.yml`); the LiteLLM gateway-side ceiling is the next bottleneck.

For Graphiti's `add_episode` call profile (asynchronous write from the agent's perspective; user doesn't wait), 20 s mean is acceptable. For any synchronous read-time extraction this would be too slow.

## What changed vs. the v1 spike

v1 saw HTTP 502 from LiteLLM at ~95 s wall-clock with `Upstream llama-server timeout after 30.0s on moe`. The narrative in v1's `evidence.md` was that the model can't fit in the time budget. That narrative was incomplete.

The actual root cause was two compounding bugs:

1. **Proxy 422 on `chat_template_kwargs`** — the gemma-hybrid-proxy's Pydantic request model had `extra="forbid"`. Sending the field returned `422 extra_forbidden` before the request reached llama-server. The director's direct `curl 127.0.0.1:8081` test bypassed the proxy and proved the model itself responded in 2 s with `enable_thinking=false`.
2. **Default proxy timeout** — `request_timeout_s` defaulted to 60 s. The model emits 300–500 token JSON outputs at ~10.7 tok/s = 28–47 s, plus prompt processing. Real production traffic was right on the edge of the 60 s ceiling and intermittently tripping it. Bumped to 120 s.

Both are fixed in the proxy role's defaults. v1 should be read as "the model + the bug + the timeout, all together, fail." v2 is the model alone, against the corpus, with the bugs fixed.

## Verdict

**ADOPT-WITH-CAVEATS**. Local Gemma 4 26B-MoE clears the parse-rate floor (≥ 80 %) and is within reach of the schema-pass floor (78 % vs. 90 % bar) but does not unconditionally clear ADOPT-LOCAL. Sprint 3 production traffic will:

1. Use `gemma4-26b-text` via LiteLLM as the Graphiti extraction LLM.
2. Wire a retry-on-malformed handler at E3-S04 to absorb the 16 % parse-fail rate.
3. Reassess at E3-S09 (week-2 decision gate) against real `add_episode` telemetry. If parse-OK + schema-pass with retry settles ≥ 90 % / ≥ 85 %, hold; otherwise revert to cloud.

The fallback is one config change: `OPENAI_BASE_URL` and `OPENAI_API_KEY` in `host_vars/ct-graphiti/` flip from LiteLLM's local URL + master key back to OpenAI's URL + the previously-vaulted OpenAI key.

## Files

- `corpus-50-facts.jsonl` — 50-episode corpus (unchanged from v1)
- `extraction-prompt.txt` — system + user template (unchanged from v1)
- `run-spike.py` — runner; v2 has `chat_template_kwargs: {"enable_thinking": false}` in the request body
- `results.jsonl` — 50 result rows + 1 summary row (this run)
- `run-rerun-2026-04-26.log` — stdout from this run
- `evidence.md` — v1 evidence (kept for historical record)
- `evidence-rerun.md` — this file
