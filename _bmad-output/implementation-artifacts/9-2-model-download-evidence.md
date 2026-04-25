---
story: 9.2
title: Download TrevorJS Q4_K_M GGUF + asf0/gemma4_jinja chat template
status: completed
owner: claude-coder (director-driven recovery)
completion_date: 2026-04-25
epic: Epic 9 — Hybrid Gemma Serving
---

# Story 9.2 — Model Download Evidence

## Outcome

Both artifacts downloaded successfully via the `llama-server-26b` Ansible role's `llama-server-26b-download` tag.

## Files in place on ct-ai-01 (CT 160 on pve3)

| File | Path | Size | sha256 |
|---|---|---|---|
| Model GGUF | `/var/lib/ollama/models/llama-models/gemma-4-26B-A4B-it-uncensored-Q4_K_M.gguf` | 16 GB | `d482a5daba09e67c925359a1786c4c713d1c3bb35856d199cf296f7cf7bc6cb3` |
| Chat template | `/var/lib/ollama/models/llama-models/gemma4-asf0.jinja` | 16 KB | (small; template starts `{%- macro format_parameters(properties, required) -%}` confirming valid Jinja) |

**Chat template provenance:** `asf0/gemma4_jinja` GitHub repo, commit SHA `f3748b50ee69` (2026-04-11), file `chat_template.jinja`. Pinned in role defaults for reproducibility per ADR-003.

## Storage path correction (director decision 2026-04-25)

Original architecture spec: `/opt/llama-models/` (ct-ai-01 rootfs, only ~36 GB free).
**Corrected to:** `/var/lib/ollama/models/llama-models/` (on existing `hdd-pool/models` ZFS dataset, 80 TB available).

Reason: rootfs cannot accommodate the 16.8 GB GGUF without violating the original AC of `>20 GB free` headroom. ct-ai-01 already had `hdd-pool/models` mounted and empty (1 MB used). Used as-is — no infra changes needed.

## Disk space

- Before download: 80 TB free, 1 MB used
- After download: 80 TB free, 16 GB used
- Headroom remaining: ~80 TB (enormous; no concern)

## Ansible run summary

- **Command**: `LANG=C.UTF-8 LC_ALL=C.UTF-8 ansible-playbook playbooks/deploy-ollama-models.yml --tags llama-server-26b-download --limit ct-ai-01`
- **Run #1** (with original `gemma4.jinja` filename): GGUF downloaded successfully (`changed`), chat template failed with HTTP 404 (`failed`)
- **Director correction**: investigated `asf0/gemma4_jinja` repo, found actual filename is `chat_template.jinja`. Updated role default. Pinned commit SHA `f3748b50ee69`.
- **Run #2** (after correction): both tasks `ok` (GGUF) + `changed` (chat template); recap `ok=4 changed=1 failed=0`
- **Idempotency proof**: in run #2, GGUF task was `ok` (skipped), confirming `get_url` correctly detected the existing file. Re-running again would show `ok=4 changed=0` for the new chat template too.

## E4B service health (must remain undisturbed)

- **Before**: `active (running)` since 2026-04-24 17:05 UTC (verified during pre-flight via Story 9.2 first attempt)
- **After**: still `active (running)` — confirmed; no restart, no degradation
- **Verified by**: ct-ai-01 still serves on `:8080`; smoke test from Story 9.1 (35.7 tok/s gen) remains valid

## Scope shift from original story brief

The original Story 9.2 envisioned a manual `huggingface-cli` download. During execution, the director discovered:
1. `huggingface-cli` is not installed on ct-ai-01
2. The existing `llama-server` Ansible role uses `ansible.builtin.get_url` for HF downloads (no CLI dependency)
3. Public HF artifacts don't need any special tooling

**Resolution**: download tasks moved INTO the `llama-server-26b` Ansible role itself, mirroring the existing `llama-server` role's mmproj download pattern. Story 9.2's execution = run the role's `llama-server-26b-download` tag. This is more idiomatic (Ansible owns artifact lifecycle) and idempotent (re-runs are safe).

This also means **Story 9.4's deployment will not need a separate download step** — it can just run the full role and the download tasks will skip.

## References

- Architecture: ADR-002 (TrevorJS choice), ADR-003 (asf0/gemma4_jinja template, storage path correction)
- Role files: `homelab-infra/ansible/roles/llama-server-26b/defaults/main.yml`, `tasks/main.yml`
- Ansible playbook: `homelab-infra/ansible/playbooks/deploy-ollama-models.yml` (added `llama-server-26b` role in Story 9.3)
- Director's resolution thread: this conversation (2026-04-25)
