# Gemma 4 stack upgrade on ct-ai-01 — plan (2026-11-09)

**Decision (operator, 2026-11-09):** switch both servers to **official Google QAT weights**. 26B-A4B (:8081) gets an MTP drafter; **12B Unified** (vision + audio) replaces E4B on :8080. Uncensored GGUFs stay on disk for rollback. Go/no-go per phase via a fixed acceptance eval.

**Ground rules:** always `ansible-playbook playbooks/deploy-ollama-models.yml --limit ct-ai-01 --tags <role>` (never the full playbook — it also runs `ollama-models`). `--check --diff` first. Restarts deliberate/manual. Commit + push to `main` at C1–C5.

## Live state at start
- CT 160 ct-ai-01 (pve3, .160), 8C / 32 GB / swap 0; Radeon 890M (RADV GFX1150), UMA 32 GiB, 24.8 GB used.
- :8080 `llama-server` — E4B Uncensored Q5_K_P + mmproj, `-c 32768` (role says 8192).
- :8081 `llama-server-26b` — TrevorJS 26B-A4B uncensored Q4_K_M, asf0 chat template; ~24 tok/s decode / ~90 tok/s prefill.
- llama.cpp live `b9159-2-g91e84fed6`, role pins `b8948` (role would DOWNGRADE + rebuild + restart).
- `gemma-hybrid-proxy` :8000 has hand patches on host (`api/chat_completions.py:483,537`, `adapters/openai_models.py` LENIENT_INBOUND) and timeout 300; binds 0.0.0.0. Unit has `Requires=` on both llama units.
- LiteLLM live has `extra_body.chat_template_kwargs.enable_thinking:false` on `gemma4-26b-text` + `gemma4-e4b-vision` (not in IaC).

## Phase 0a — reconcile drift into IaC (no behaviour change) · downtime 0
1. Copy live proxy source patches into `roles/gemma-hybrid-proxy/files/src/...`; run pytest, adjust tests expecting `extra="forbid"`.
2. `litellm-config.yaml.j2:14-23` add the `extra_body` block on the two aliases.
3. `roles/llama-server/defaults/main.yml:30` → `llama_server_context_size: 32768`.
4. `roles/gemma-hybrid-proxy/defaults/main.yml:53` → `request_timeout_s: 300`.
5. `roles/llama-server/defaults/main.yml:12` → record live build `b9159`.
6. Proxy bind: codify current `0.0.0.0` for now; re-bind to loopback (ADR-009) only after `ss -tn sport = :8000` shows no remote clients over a day.
- Verify: `--check --diff` on the four role tags shows no change. **C1** `fix(ai): reconcile ct-ai-01 LLM stack drift into IaC`.

## Phase 0b — side-by-side llama.cpp build + hardening · downtime ~5 s (proxy)
- `llama_cpp_version` → target release; `llama_cpp_build_dir: /opt/llama.cpp-{{ version }}`; `llama_cpp_active_dir` (units use it; changes only in 0c) in new `host_vars/ct-ai-01/llm-stack.yml`.
- Build targets `llama-server llama-bench`; restart only when the unit file changes (not on rebuild).
- Unit templates: `-np {{ parallel }}` (4) and `--cache-ram 2048`.
- Remove duplicate `llama_cpp_dir` in `roles/llama-server-26b/defaults/main.yml:15`.
- Proxy unit `Requires=` → `Wants=` (stopping one llama unit no longer kills every alias).
- Verify: new binary `--version`, `--help | grep -e draft-mtp`. **C2**.

## Eval — fixed acceptance set (write before 0c; baseline on current stack)
`homelab-infra/ansible/scripts/gemma-acceptance-eval.sh` + `prompts/`: speed (3×512 tok, `timings`, MTP acceptance), Dutch (8 prompts, operator review vs baseline), tool calling (5 → structured `tool_calls` on `gemma4-26b-text`; record `gemma4-auto`), JSON (10 Graphiti-style on `gemma4-26b-json`, all `json.loads`, no thought leakage), vision (3 images), audio (12B only, direct :8080).

## Phase 0c — switch binary, keep current weights · ~30 s per unit
- `llama_cpp_active_dir` → new build; apply `--tags llama-server,llama-server-26b`; `systemctl restart llama-server-26b`.
- Accept: health 200; 26B ≥ 22 tok/s decode, ≥ 85 tok/s prefill; 20-min soak 4 parallel streams without `GGML_ASSERT` (llama.cpp #29221 → fall back to `-np 3`); eval passes.
- Rollback: `llama_cpp_active_dir: /opt/llama.cpp`, apply, restart (~2 min).

## Phase 1 — 26B-A4B official QAT + MTP · window ~45 min (26B aliases down)
- Weights `google/gemma-4-26B-A4B-it-qat-q4_0-gguf` → `gemma-4-26B_q4_0-it.gguf` (14.4 GB). Drafter candidates: `ggml-org/gemma-4-26B-A4B-it-GGUF` → `mtp-gemma-4-26B-A4B-it-Q8_0.gguf`; `unsloth/gemma-4-26B-A4B-it-qat-GGUF` → `mtp-gemma-4-26B-A4B-it.gguf`.
- Test on temporary unit :8091 (stop prod 26B first): no-MTP vs drafter a vs b, `--spec-type draft-mtp -md … --spec-draft-n-max 3 -ngld 99`.
- Memory ≈ 16.5 GB (vs ~18.3 today).
- **Gate G1 (operator):** MTP decode ≥ 30 tok/s, acceptance ≥ 0.6, prefill ≥ 85, tools 5/5, JSON 10/10, Dutch ≥ baseline, soak clean (#29419 → `-fa off` on drafter).
- IaC: new repo/file/draft vars; template file empty (official GGUF embeds template); unit `{% if %}` blocks; rollback values as comments in `llm-stack.yml`. **C3**.

## Phase 2 — 12B Unified QAT on :8080 (vision + audio) · window ~30 min (vision down)
- `google/gemma-4-12B-it-qat-q4_0-gguf` → `gemma-4-12b-it-qat-q4_0.gguf` (7.0 GB) + `mmproj-gemma-4-12b-it-qat-q4_0.gguf` (audio encoder confirmed in header). Optional drafter `ggml-org/gemma-4-12B-it-GGUF` → `mtp-gemma-4-12B-it-Q4_0.gguf`.
- Test on :8090 after stopping E4B. Memory ≈ 9.5–10 GB → total ≈ 26.5 / 32 GiB.
- **Gate G2:** vision 3/3, audio transcribes, decode ≥ 10 tok/s, `gemma4-auto` image latency ≤ 2× baseline.
- IaC: models dir → hdd-pool `llama-models`; add main-GGUF download task; keep `gemma4-e4b-vision` alias as compat, add `gemma4-12b`. Audio stays behind proxy 415 (ADR-008) → follow-up story. **C4**.
- Rollback: restore E4B vars (files still in `/opt/ollama-models`).

## Phase 3 — docs (C5, homelab-playbook)
Architecture doc: amend ADR-002 (official QAT), ADR-008 (audio capable at model layer), new ADR for MTP + versioned llama.cpp dirs; memory budget. Runbook `hybrid-gemma-clients.md`: diagram, aliases, known-issue re-check, rollback + eval sections.

## Risks
- 12B dense decode likely ~10–12 tok/s on Strix Point → slower vision/auto preprocessing; measure at G2.
- Vulkan: #29221 (`-np 4`), #29419 (MTP + FA), #25618 (MTP divergence on quantized targets).
- No official MTP GGUF from Google; drafter provenance unconfirmed → acceptance rate decides.
- Official weights may behave differently for Graphiti JSON / OWUI prompts tuned on uncensored → JSON 10/10 guard.
- Swap 0 + mmap page cache → watch cgroup `memory.peak` during every window.
