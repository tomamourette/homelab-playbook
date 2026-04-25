---
# Story 9.16 — Deploy LiteLLM gateway in front of gemma-hybrid-proxy
# Date: 2026-04-25
# Owner: claude-coder
# Status: completed
---

## Summary

Stood up a new Ansible role `litellm-gateway` deploying LiteLLM 1.83.13
(post-March-2026-PyPI-advisory pinned per ADR-011) on ct-ai-01 (CT 160 on
pve3). LiteLLM listens on `127.0.0.1:4000`, forwards three virtual aliases
(`gemma4-auto`, `gemma4-26b-text`, `gemma4-e4b-vision`) to the
gemma-hybrid-proxy from Story 9.11 at `127.0.0.1:8000/v1`, enforces
master-key bearer-token auth, and exposes Prometheus metrics at `/metrics/`
on the same port. Stateless mode (no Prisma/SQLite) for Sprint 3.
Idempotent on second run (0 changes). All 4 upstream services
(`gemma-hybrid-proxy`, `llama-server`, `llama-server-26b`, `open-webui`)
remain healthy.

## Rollback safety net (AC-10)

- **ZFS snapshot:** `rpool/data/subvol-160-disk-0@pre-litellm-deploy-20260425-1730`
- **Rollback rootfs:** `ssh pve3 "zfs rollback rpool/data/subvol-160-disk-0@pre-litellm-deploy-20260425-1730"`
- **Why ZFS snapshot, not pct snapshot:** CT 160 has the `mp0` bind-mount of
  `/hdd-pool/models` → `/var/lib/ollama/models` which `pct snapshot` refuses
  to handle. Same workaround as Stories 9.4 and 9.11.
- **Soft rollback (no rebuild needed):**
  `systemctl disable --now litellm-gateway && rm /etc/systemd/system/litellm-gateway.service`
  removes the new surface without touching the proxy or llama-servers. The
  `litellm` user, `/opt/litellm-gateway/`, and `/var/lib/litellm/` remain
  inert until the next role apply.

## Role files created (AC-1)

```
homelab-infra/ansible/roles/litellm-gateway/
├── defaults/main.yml                     # NEW — litellm_* vars (loopback, system user, version pin, vault ref)
├── handlers/main.yml                     # NEW — restart litellm-gateway
├── tasks/main.yml                        # NEW — assert version safe, user/dir/venv/pip/templates/systemd/health-wait
├── templates/
│   ├── env.j2                            # NEW — LITELLM_MASTER_KEY (no_log on render)
│   ├── litellm-config.yaml.j2            # NEW — model_list (3 aliases) + general_settings + prometheus callback
│   └── litellm-gateway.service.j2        # NEW — systemd unit (After/Requires gemma-hybrid-proxy)
```

Playbook update: `homelab-infra/ansible/playbooks/deploy-ollama-models.yml`
appended `litellm-gateway` role with tag `litellm-gateway` (4 lines added,
existing roles untouched).

## Key decisions vs. brief

- **`litellm[proxy,proxy-runtime]==1.83.13` extras** instead of bare `litellm`.
  The bare wheel ships only the SDK; the proxy server CLI requires `[proxy]`
  (uvicorn/fastapi/prisma machinery) AND `[proxy-runtime]` (which contains
  `prometheus-client==0.20.0`, OTel/sentry stack, and several runtime
  integrations). Verified empirically: deploy with bare `[proxy]` crashes at
  startup with `ModuleNotFoundError: No module named 'prometheus_client'`
  the moment `callbacks: ["prometheus"]` is parsed. PyPI metadata for
  `litellm 1.83.13` confirms `prometheus-client` lives in the
  `proxy-runtime` extra (NOT `proxy` or `extra-proxy`).
- **Stateless mode, no `database_url`.** LiteLLM 1.83.x triggers a Prisma
  client init the moment `database_url` is set; Prisma needs `prisma
  generate` to build native binaries against its bundled schema, which is a
  separate build step. Story 9.16 needs only master-key bearer auth +
  Prometheus + virtual aliases, none of which require persistence.
  Request logs go to stderr (systemd journal). Documented inline in
  `litellm-config.yaml.j2`; future virtual-key DB persistence is a clean
  re-enable + add `prisma generate` task.
- **Hash-pinning skipped for transitive graph.** Per the Story 9.6 trade-off
  precedent: `[proxy,proxy-runtime]` pulls 90+ transitive dependencies;
  `--require-hashes` would force resolving + maintaining a hash for every
  one. Pinned the top-level (`litellm==1.83.13`) and added a pre-install
  `assert` that REFUSES to deploy if the requested version is `1.82.7` or
  `1.82.8` (the compromised PyPI tags). Documented gap; revisit when
  upstream ships a slimmer official set or a SBOM/lockfile.
- **`/usr/bin/python3` not `/usr/bin/python3.11`.** Brief suggested 3.11;
  CT 160 ships Python 3.13.5 (Trixie default). litellm 1.83.13 is
  `py3-none-any` so portable. Mirror gemma-hybrid-proxy convention.
- **WatchdogSec omitted** — same correction as Story 9.11. uvicorn (which
  the LiteLLM CLI runs under the hood) does not implement
  `sd_notify(WATCHDOG=1)` heartbeats. `Restart=on-failure` plus the
  `/health/liveliness` endpoint cover liveness adequately.
- **Master key NOT committed to git.** Generated fresh on the deploy host
  (`openssl rand -hex 32`), passed via `--extra-vars vault_litellm_master_key=$KEY`,
  full key recorded only in the operator's password manager and at
  `/tmp/litellm-master-key-9.16.txt` (mode 0600) on the operator
  workstation pending vault enrolment. Defaults render
  `vault_litellm_master_key | default('REPLACE_ME_VIA_VAULT')` so a
  forgotten vault entry surfaces fast (LiteLLM rejects all requests).
  Render task uses `no_log: true` to keep the key out of Ansible logs.
- **Listener on port 4000 only** (no separate `:4001` for Prometheus).
  Brief had a `litellm_prometheus_port: 4001` placeholder; LiteLLM 1.83.x
  exposes `/metrics` on the SAME port as the API (mounted as a sub-app
  via `make_asgi_app()`). Kept the variable for forward compatibility but
  defaulted it to `litellm_listen_port` and updated the comment.

## Ansible run outputs

### Dry-run (--check --diff)

`ok=13 changed=10 unreachable=0 failed=1`. The single failure is the
expected check-mode systemd lookup: the service unit is rendered to a
diff-display tempfile but never written to disk in check mode, so
`systemctl enable` cannot find it. Identical pattern to the
gemma-hybrid-proxy role check-run.

### Real run #1 (initial)

Diagnosed two missing-extras issues before reaching green:
1. `[proxy]` only → `ModuleNotFoundError: prometheus_client` (added `[extra-proxy]` first, wrong extra)
2. `[proxy,extra-proxy]` → still `ModuleNotFoundError: prometheus_client` (correct extra is `proxy-runtime`)
3. `[proxy,proxy-runtime]` → `Exception: Unable to find Prisma binaries. Please run 'prisma generate' first.`
4. Removed `database_url` from config → CLEAN STARTUP.

### Real run #2 (after fixes)

```
PLAY RECAP *********************************************************************
ct-ai-01 : ok=16 changed=3 unreachable=0 failed=0 skipped=0 rescued=0 ignored=0
```

### Real run #3 (idempotency check, AC-2)

```
PLAY RECAP *********************************************************************
ct-ai-01 : ok=15 changed=0 unreachable=0 failed=0 skipped=0 rescued=0 ignored=0
```

Zero changes on second run — role is idempotent.

## Smoke-test results

### AC-3 — service running, listening on `:4000`

```
$ systemctl is-active litellm-gateway gemma-hybrid-proxy llama-server llama-server-26b
active active active active

$ ss -tlnp | grep ':4000'
LISTEN 0 2048 127.0.0.1:4000 0.0.0.0:* users:(("litellm",pid=119061,fd=13))
```

### AC-4 — `/v1/models` returns 3 aliases (forwarded from proxy)

```
$ curl -s -H "Authorization: Bearer $MASTER_KEY" http://127.0.0.1:4000/v1/models | jq -r '.data[].id'
gemma4-auto
gemma4-26b-text
gemma4-e4b-vision
```

### AC-5 — text-only chat completion with bearer (LiteLLM → proxy → MoE)

```
$ curl -s -X POST http://127.0.0.1:4000/v1/chat/completions \
    -H "Authorization: Bearer $MASTER_KEY" \
    -H 'Content-Type: application/json' \
    -d '{"model":"gemma4-26b-text","messages":[{"role":"user","content":"Reply with exactly the word HELLO and nothing else."}],"max_tokens":256,"temperature":0}'

FINISH: stop
CONTENT: 'HELLO'
USAGE: {'completion_tokens': 102, 'prompt_tokens': 27, 'total_tokens': 129, 'prompt_tokens_details': {'cached_tokens': 0}}
MODEL: gemma4-26b-text
```

(`completion_tokens=102` reflects the 26B reasoner's reasoning_content
budget before the final `HELLO` content; `max_tokens=12` was too tight in
an earlier probe and produced `finish_reason=length` with empty content.
Bumping to 256 produced the expected clean stop. This is intrinsic to the
26B reasoner, not a LiteLLM/proxy issue.)

### AC-6 — request without bearer returns 401

```
$ curl -s -o /dev/null -w 'HTTP %{http_code}\n' \
    -X POST http://127.0.0.1:4000/v1/chat/completions \
    -H 'Content-Type: application/json' \
    -d '{"model":"gemma4-26b-text","messages":[{"role":"user","content":"hi"}],"max_tokens":4}'
HTTP 401
```

### AC-7 — Prometheus exporter responds

```
$ curl -sL -o /dev/null -w 'HTTP %{http_code} URL %{url_effective}\n' \
    http://127.0.0.1:4000/metrics
HTTP 200 URL http://127.0.0.1:4000/metrics/

$ curl -sL http://127.0.0.1:4000/metrics | head -10
# HELP python_gc_objects_collected_total Objects collected during gc
# HELP python_gc_objects_uncollectable_total Uncollectable objects found during GC
# HELP python_gc_collections_total Number of times this generation was collected
# HELP python_info Python platform information
# HELP process_virtual_memory_bytes Virtual memory size in bytes.
...
```

(LiteLLM 307-redirects `/metrics` → `/metrics/` (mounted ASGI sub-app);
follow-redirects yields the standard Prometheus text format. Story 9.17
Prometheus scrape config should set `metrics_path: /metrics/` to skip the
redirect hop.)

### AC-8 — version verification (NOT compromised)

```
$ /opt/litellm-gateway/.venv/bin/pip show litellm | head -3
Name: litellm
Version: 1.83.13
Summary: Library to easily interface with LLM API providers
```

`1.83.13` confirmed; `1.82.7`/`1.82.8` (the compromised tags) are
explicitly rejected by the role's pre-install assert.

### AC-9 — all previous services still healthy

```
gemma-hybrid-proxy /health → {"status":"ok","upstreams":{"e4b":"ok","moe":"ok"}}
gemma-hybrid-proxy /v1/models → ['gemma4-auto', 'gemma4-26b-text', 'gemma4-e4b-vision']
OWUI :3000 -> HTTP 200
llama-server E4B :8080 -> HTTP 200
llama-server 26B :8081 -> HTTP 200
systemctl is-active: active active active active
```

## Acceptance criteria

| AC | Status | Evidence |
|----|--------|----------|
| AC-1: role created with proper layout | PASS | files listed above |
| AC-2: dry-run + idempotent real-run | PASS | 30/0 changes on 2nd run |
| AC-3: service running on :4000, healthy | PASS | systemctl + ss output |
| AC-4: /v1/models returns 3 aliases | PASS | curl output |
| AC-5: text bearer-auth chat completion | PASS | "HELLO" returned, finish=stop |
| AC-6: no-bearer request returns 401 | PASS | HTTP 401 |
| AC-7: Prometheus /metrics responds | PASS | HTTP 200 with python_/process_ metrics |
| AC-8: pip show confirms 1.83.13 | PASS | bare wheel + extras both 1.83.13 |
| AC-9: all upstreams still healthy | PASS | 4× active, 3× HTTP 200 |
| AC-10: snapshot for rollback | PASS | pre-litellm-deploy-20260425-1730 |

## Boundary check

- Did NOT repoint Open WebUI (Story 9.17 does that). OWUI still points at
  the gemma-hybrid-proxy on `:8000` per Story 9.11 cutover.
- Did NOT touch the deployed gemma-hybrid-proxy beyond reading
  `/v1/models` and `/health` (read-only HTTP).
- Did NOT downgrade to a compromised version (pre-install assert blocks).
- LiteLLM master key is not in git: vault placeholder in defaults, real
  value injected via `--extra-vars` and recorded only in operator
  password manager (and `/tmp/litellm-master-key-9.16.txt` mode 0600 on
  operator workstation pending Ansible Vault enrolment).
- Did NOT touch ct-dev-test (not viable for this story per the brief's
  same-pattern-as-9.4/9.11 deviation; --check on ct-ai-01 covered).

## Outstanding follow-ups (not blocking 9.16)

1. **Vault enrolment** of `vault_litellm_master_key` into
   `inventories/homelab/host_vars/ct-ai-01/vault.yml` (currently the key is
   in the operator's password manager + a tmpfile; vault enrolment moves
   the IaC contract into version control without leaking the key).
2. **Story 9.17 Prometheus scrape** must use `metrics_path: /metrics/`
   (trailing slash) to avoid the 307 hop.
3. **LiteLLM streaming-passthrough verification for tool-call deltas**
   (architecture open question + sprint-status open decision). Did not
   exercise streaming-with-tool-calls through LiteLLM in 9.16 — that's
   Story 9.17's e2e Open WebUI test against `gemma4-auto` with an image.
   If LiteLLM buffers tool-call deltas, the architecture contingency is
   to bypass LiteLLM for `gemma4-auto` and have the proxy auth itself.
4. **DB-backed virtual keys** deferred. If/when the operator wants
   per-client keys (Continue.dev, Cursor, mobile, scripts), re-enable
   `database_url` and add a `prisma generate` task in `tasks/main.yml`.

## Sprint status update

`hybrid-gemma-serving-sprint-status.md`:
- 9.16 `status: pending` → `completed`
- 9.16 `owner: unassigned` → `claude-coder`
- 9.16 add `completed_at: 2026-04-25`
- 9.16 add `evidence: "_bmad-output/implementation-artifacts/9-16-litellm-gateway-evidence.md"`
- `sprint_3.stories_completed: 3 → 4`

Sprint 3 progresses to Story 9.17 (clients + observability + Open WebUI
repoint) which is the Sprint 3 EXIT GATE.
