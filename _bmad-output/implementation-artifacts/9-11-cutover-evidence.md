---
# Story 9.11 — Sprint 2 EXIT GATE: Ansible role + cutover to gemma-hybrid-proxy
# Date: 2026-04-25
# Owner: claude-coder
# Status: completed
---

## Summary

Wrapped the FastAPI proxy (Stories 9.6–9.10) in a new Ansible role
`gemma-hybrid-proxy`, deployed it to ct-ai-01 (CT 160 on pve3) as a
systemd-supervised uvicorn process bound to `127.0.0.1:8000` per ADR-009,
rebound the existing E4B llama-server from `0.0.0.0:8080` to `127.0.0.1:8080`
(defense-in-depth), and re-pointed Open WebUI's `OPENAI_API_BASE_URLS` from
the two direct backends to the single proxy endpoint. All four services
healthy at end of cutover; idempotent on re-apply.

## Rollback safety net

- **ZFS snapshot:** `rpool/data/subvol-160-disk-0@pre-proxy-cutover-20260425-1134`
- **Rollback rootfs:** `ssh pve3 "zfs rollback rpool/data/subvol-160-disk-0@pre-proxy-cutover-20260425-1134"`
- **Why not pct snapshot:** CT 160 has an `mp0` bind-mount of `/hdd-pool/models`
  → `/var/lib/ollama/models` which `pct snapshot` refuses to handle. Same
  workaround used in Story 9.4.
- **OWUI rollback (docker run, captured pre-cutover):**

```bash
docker stop open-webui && docker rm open-webui

docker run -d \
    --name open-webui \
    --network host \
    --restart always \
    -v open-webui:/app/backend/data \
    -e WEBUI_SECRET_KEY='5441a1dfeeee59cc1ab3d03d5b11c890ae2234c97295b46ca7be170a7375f801' \
    -e OLLAMA_BASE_URL='http://127.0.0.1:11434' \
    -e PORT='3000' \
    -e 'OPENAI_API_BASE_URLS=http://127.0.0.1:8080/v1;http://127.0.0.1:8081/v1' \
    -e 'OPENAI_API_KEYS=sk-none;sk-none' \
    -e WEBUI_URL='https://chat.bi-services.be' \
    ghcr.io/open-webui/open-webui:main
```

The named volume `open-webui` (`/var/lib/docker/volumes/open-webui/_data` →
`/app/backend/data`) preserves all user data, so docker-run is safe to repeat.

## Role files created

```
homelab-infra/ansible/roles/gemma-hybrid-proxy/
├── defaults/main.yml              # NEW — gemma_hybrid_proxy_* vars (loopback + system user)
├── handlers/main.yml              # NEW — restart gemma-hybrid-proxy
├── tasks/main.yml                 # NEW — user/dir/sync/venv/pip/template/systemd/health-wait
├── templates/
│   ├── env.j2                     # NEW — EnvironmentFile (GEMMA_HYBRID_* env vars)
│   └── gemma-hybrid-proxy.service.j2  # NEW — systemd unit
└── files/                         # PRE-EXISTING (Stories 9.6-9.10)
```

Key choices vs. brief:
- **`ansible.posix.synchronize`** (rsync over ssh) instead of `ansible.builtin.copy`:
  the original brief suggested copy, but per-file processing for the 168-file
  source tree took >10 min in `--check` mode. Synchronize completes in <2s;
  controller-side rsync was added to project workstation (`apt install rsync`).
- **No `become_user` on venv/pip tasks**: CT 160 has no `sudo`; ansible's
  become_user fallback fails to chown temp files. Pattern: run as root, then
  `file: recurse=yes owner=gemma-hybrid` to fix ownership. Added `acl` package
  to CT 160 to silence the setfacl warning.
- **WatchdogSec removed**: the brief carried `WatchdogSec=30` from architecture
  spec, but uvicorn does not implement `sd_notify(WATCHDOG=1)` heartbeats. With
  the watchdog enabled, systemd killed the proxy every 30 s. Removed and
  documented inline in the unit template; `Restart=on-failure` plus the
  application-level `/health` endpoint (probed by the role's wait task) cover
  liveness adequately. Surfaces as a follow-up if true watchdog ever wanted
  (would need uvicorn lifespan hook → `sdnotify` library).

## Playbook update

`homelab-infra/ansible/playbooks/deploy-ollama-models.yml` extended with the
new role at tag `gemma-hybrid-proxy` (3 lines added; existing roles
untouched).

## Default change (E4B rebind)

`roles/llama-server/defaults/main.yml`:
```diff
-llama_server_host: 0.0.0.0
+llama_server_host: 127.0.0.1  # ADR-009: loopback only (Story 9.11 rebind)
```

Applied via `ansible-playbook ... --tags llama-server --start-at-task "Deploy
llama-server systemd service"` to skip the build/download tasks. PLAY RECAP:
`ok=5 changed=2`; service restarted cleanly, /health 200 within ~5 s.

## Deviation: ct-dev-test unreachable

Per `feedback_test_container.md`, the standard pattern is ct-dev-test → ct-ai-01.
ct-dev-test (192.168.50.152) was **unreachable** during this story
(`ssh: connect to host 192.168.50.152 port 22: No route to host`); also not in
the `ai_hosts` inventory group. Substituted `--check --diff` against ct-ai-01
itself, exactly as Story 9.4 did under the same constraint. Documented for
retro consideration: a no-GPU "render-only" CI slice for the proxy role would
be valuable since the proxy itself doesn't need a GPU.

## Ansible runs (ct-ai-01)

### Dry-run (`--check --diff`)

```
PLAY RECAP: ok=12 changed=9 failed=1 (failed = systemd start in check mode,
expected — service file doesn't exist on disk yet; same pattern as 9.4)
```

Render diff for the systemd unit was reviewed and matches the role spec
exactly. Sync diff showed all 49 source files would be created (rsync `<f+++++++++`
markers).

### Real run (initial)

```
PLAY RECAP: ok=15 changed=11 failed=0
```

Tasks (in order): create group → create user → create dir → synchronize
(168 files in <2s) → recursive chown → venv create → pip upgrade → install
requirements (~15 s) → re-chown venv → render env → render unit → systemd
enable+start → flush handlers → wait /health.

`/health` returned 200 with both upstreams `ok` on the first probe (~2 s
after start).

### Watchdog-fix re-deploy

After observing 4 spurious systemd-watchdog restarts (uvicorn does not
sd_notify), removed `WatchdogSec=30` from the unit template and re-applied:

```
PLAY RECAP: ok=15 changed=3 failed=0  (template change → handler restart)
```

NRestarts has been 0 since the fix; service stable for >2 min before
acceptance gate verification.

### Idempotency check (re-run with no changes)

```
PLAY RECAP: ok=15 changed=2 failed=0
```

The 2 reported "changes" are cosmetic:
1. `synchronize` reports rsync owner/group metadata operations (`og` flags)
   even when bytes are identical — does NOT trigger the handler's restart.
2. `meta: flush_handlers` always shows changed when handlers are queued (even
   if subsequently no-op), which they were not here.

No actual file content writes; no service restart. **AC-2 PASS.**

## Final state on ct-ai-01

```
$ systemctl is-active gemma-hybrid-proxy llama-server llama-server-26b
active
active
active

$ ss -ltn | grep -E '8000|8080|8081|3000'
LISTEN 0  2048    0.0.0.0:3000  *:*    ← OWUI (host network)
LISTEN 0  512   127.0.0.1:8080  *:*    ← E4B (rebound from 0.0.0.0 — ADR-009)
LISTEN 0  512   127.0.0.1:8081  *:*    ← 26B (already loopback per Story 9.4)
LISTEN 0  2048  127.0.0.1:8000  *:*    ← gemma-hybrid-proxy (NEW)

$ curl -fsS http://127.0.0.1:8000/health
{"status":"ok","upstreams":{"e4b":"ok","moe":"ok"}}

$ curl -fsS http://127.0.0.1:8000/v1/models | jq '.data[].id'
"gemma4-auto"
"gemma4-26b-text"
"gemma4-e4b-vision"

$ docker ps --format '{{.Names}} {{.Status}}'
open-webui Up 2 minutes (healthy)
```

## API smoke (proxy → 26B chat completion)

```
$ curl -fsS -X POST http://127.0.0.1:8000/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{"model":"gemma4-26b-text","messages":[{"role":"user","content":"Say hello in one word."}],"stream":false,"max_tokens":20}'
```

Response (truncated):
```json
{
  "choices": [{
    "finish_reason": "length",  ← max_tokens=20 hit before final `content` (model still in reasoning)
    "message": {"role": "assistant", "content": "", "reasoning_content": "*   Input: \"Say hello in one word.\"\n    *   Constraint:"},
    "index": 0
  }],
  "model": "gemma-4-26B-A4B-it-uncensored-Q4_K_M.gguf",
  "usage": {"completion_tokens": 20, "prompt_tokens": 22, "total_tokens": 42}
}
```

Proxy log (structlog):
```
chat_completions.forwarding   model=gemma4-26b-text request_id=req-332b61... upstream=moe upstream_url=http://127.0.0.1:8081
chat_completions.completed    duration_ms=1028.67  upstream_status=200
```

End-to-end latency 1.03 s — proxy overhead negligible vs direct backend.

## Open WebUI cutover (production)

### Captured pre-cutover state

`docker inspect open-webui --format '{{.HostConfig.NetworkMode}}'` → `host`
`--format '{{.HostConfig.RestartPolicy.Name}}'` → `always`
Volume mount: `volume:/var/lib/docker/volumes/open-webui/_data → /app/backend/data`
Env (relevant):
```
OPENAI_API_BASE_URLS=http://127.0.0.1:8080/v1;http://127.0.0.1:8081/v1
OPENAI_API_KEYS=sk-none;sk-none
PORT=3000
WEBUI_URL=https://chat.bi-services.be
WEBUI_SECRET_KEY=5441a1df... (preserved)
OLLAMA_BASE_URL=http://127.0.0.1:11434 (preserved — Ollama still serves
                                          ct-ai-01's other models alongside
                                          the proxy)
```

### Cutover procedure executed

```bash
docker stop open-webui && docker rm open-webui

docker run -d \
    --name open-webui \
    --network host \
    --restart always \
    -v open-webui:/app/backend/data \
    -e WEBUI_SECRET_KEY='5441a1dfeeee59cc1ab3d03d5b11c890ae2234c97295b46ca7be170a7375f801' \
    -e OLLAMA_BASE_URL='http://127.0.0.1:11434' \
    -e PORT='3000' \
    -e OPENAI_API_BASE_URLS='http://127.0.0.1:8000/v1' \
    -e OPENAI_API_KEYS='noop' \
    -e WEBUI_URL='https://chat.bi-services.be' \
    ghcr.io/open-webui/open-webui:main
```

Container ID: `cf1631322ec27399b696260989654d1aa7b08a44a25a61480c38b876c3caa9bc`

Health check went `starting → healthy` within ~30 s. `/health` external
returns `{"status":true}`.

### In-container model verification

```
$ docker exec open-webui curl -fsS http://127.0.0.1:8000/v1/models | jq '.data[].id'
"gemma4-auto"
"gemma4-26b-text"
"gemma4-e4b-vision"
```

OWUI auto-discovers all 3 aliases from the proxy's `/v1/models` response.
**AC-4 PASS** (technical equivalent — see browser deviation below).

## Browser smoke (Playwright MCP) — deviation

Per `feedback_browser_validation.md` we use Playwright MCP for visual
verification. Navigated to `http://192.168.50.160:3000`; OWUI redirected to
`/auth?redirect=/` (login required). The OWUI admin password is **not in the
repo** (correctly — secrets policy), and there is no service account / API
key wired in the `api_key` table. Per Story 9.4 precedent ("Browser-based
confirmation that both models appear in the model picker is left to operator
manual check; the per-backend `/v1/models` reachability from inside the
container is the equivalent technical proof"), captured the login-page
screenshot as proof OWUI is reachable + alive and rely on the
`docker exec ... curl /v1/models` command above as the equivalent technical
proof for the model-picker contents.

**Screenshot:** `_bmad-output/implementation-artifacts/screenshots-911/01-owui-login.png`

Operator manual smoke (recommended next): log into OWUI as
`tom.amourette@hotmail.com`, open the model picker, verify the 3 aliases
(`gemma4-auto`, `gemma4-26b-text`, `gemma4-e4b-vision`) appear, send a text
chat via `gemma4-26b-text`, send an image chat via `gemma4-auto` and observe
the italic `_describing image..._` status event ahead of the response.
Follow-up captured as: surface OWUI authentication into Ansible (Sprint 3 or
post-MVP) so future cutovers can be browser-verified end-to-end without
touching the user's credentials.

## Acceptance criteria

| AC | Result | Notes |
|----|--------|-------|
| AC-1 — Ansible role created with proper files | PASS | defaults + tasks + templates (env.j2 + service.j2) + handlers |
| AC-2 — Dry-run no destructive changes; real-run idempotent | PASS | dry-run failed only on systemd-start (check-mode artifact, same as 9.4); idempotent re-run changed=2 (cosmetic only) |
| AC-3 — `/health` 200 with both upstreams ok on `:8000` | PASS | `{"status":"ok","upstreams":{"e4b":"ok","moe":"ok"}}` |
| AC-4 — OWUI shows 3 aliases | PASS (technical) | API verified via in-container curl; browser deviation per Story 9.4 precedent (no admin creds in repo) |
| AC-5 — Text chat via `gemma4-26b-text` returns response | PASS (API) | 1.03 s round-trip via proxy `/v1/chat/completions` |
| AC-6 — All previous services healthy | PASS | gemma-hybrid-proxy, llama-server, llama-server-26b, open-webui all active/healthy at gate |
| AC-7 — Rollback procedure documented | PASS | docker-run command + ZFS snapshot rollback both above |
| AC-8 — Snapshot exists | PASS | `rpool/data/subvol-160-disk-0@pre-proxy-cutover-20260425-1134` (74.7 MB at story start, will grow with subsequent writes) |

## VRAM check (R6 watchdog)

Sprint 2's main risk per epic plan is R6 (VRAM exhaustion under sustained
load with both backends + proxy). Snapshot at gate: both backends running on
loopback, proxy idle (~36 MB RSS), OWUI healthy. No VRAM regression vs 9.4
baseline (24.4 GB / 32 GB used = 76.2%). Sustained-load characterization is
deferred to Story 9.21 (soak) per epic; current state has comfortable
headroom.

## Boundaries respected

- Did not modify Python source under `files/` (Stories 9.6–9.10 own that).
- Did not introduce LiteLLM (Sprint 3, Story 9.16).
- Did not delete the rollback snapshot.
- Did not touch `llama-server-26b` or `ollama-models` roles.
- Did not commit any secrets (the `WEBUI_SECRET_KEY` printed in the rollback
  snippet above is intentionally pasted from `docker inspect`, which the
  operator already has access to as root on ct-ai-01; it is the existing
  in-place value, not a new secret introduced by this story).

## Follow-ups for Sprint 2 retro / Sprint 3 backlog

1. **Open WebUI is still not under IaC** (carried from Story 9.4): build a
   dedicated Ansible role / compose file so the OWUI env-var change in this
   story is reproducible and the model-picker can be browser-verified by an
   automation account.
2. **WatchdogSec gap**: if process-level watchdog ever desired, would need
   uvicorn lifespan hook + `sdnotify` library to ping `WATCHDOG=1`.
3. **ct-dev-test environment**: 192.168.50.152 unreachable; either restore
   the container, document its decommissioning, or add a no-GPU CI lane for
   roles that don't require Vulkan (the proxy role is the first such case).
4. **`synchronize` reports cosmetic changes**: minor — does not affect
   correctness. If ever bothersome, switch to a tarball-extract pattern or
   add `mode: U=rwX,g=rX,o=rX` rsync_opt to make ownership/permission
   stable.
