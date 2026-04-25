---
# Story 9.4 — Deploy llama-server-26b + register in Open WebUI
# Date: 2026-04-25
# Owner: claude-coder
# Status: completed (pending Story 9.5 50-prompt gate)
---

## Summary

Deployed the `llama-server-26b` Ansible role to ct-ai-01 (CT 160 on pve3),
started the systemd unit (TrevorJS Gemma 4 26B-A4B Uncensored Q4_K_M on
loopback `127.0.0.1:8081`), passed all 4 acceptance smoke tests, and registered
the new endpoint in Open WebUI alongside the existing E4B endpoint. The
existing E4B service was untouched (same PID, 17h uptime preserved).

## Rollback snapshot

Proxmox `pct snapshot` is **not available** for CT 160 because its `mp0`
bind-mount (`/hdd-pool/models` → `/var/lib/ollama/models`) is not snapshottable.
Took a ZFS snapshot of the rootfs subvol directly instead:

- `rpool/data/subvol-160-disk-0@pre-26b-deploy-20260425-1013`
- Rollback: `ssh pve3 "zfs rollback rpool/data/subvol-160-disk-0@pre-26b-deploy-20260425-1013"`
- The `mp0` bind-mount holds only model files (16 GB GGUF + chat template)
  that did NOT change during this story; rolling back rootfs alone restores
  the systemd config and Docker container state to the pre-deploy moment.

## Deviation from test-container-first policy

Per `feedback_test_container.md`, deploys normally go to ct-dev-test
(192.168.50.152) before ct-ai-01. **Skipped here** because ct-dev-test has no
GPU access; the role would render the systemd unit but the service would fail
at runtime (no Vulkan device → llama-server exits). Per director guidance,
substituted an Ansible `--check --diff` dry-run against ct-ai-01 itself; that
validated idempotency, template rendering, and absence of side effects on the
existing E4B unit. Recorded for retro/feedback consideration.

## VRAM delta

- Before (E4B alone): **5,723,750,400 B = 5.72 GB used / 32 GB total (17.9%)**
- After (E4B + 26B): **24,389,316,608 B = 24.39 GB used / 32 GB total (76.2%)**
- Delta from 26B (model weights + ~20 KV pages of 32k ctx): **18.67 GB**
- Headroom remaining on dedicated VRAM: **7.6 GB** (plus 32 GB GTT spillover)

Roughly matches the ~24 GB combined estimate in the brief.

## Ansible dry-run (--check --diff) summary

```
TASK [Verify llama-server binary exists]                    ok
TASK [Ensure 26B models directory exists]                   ok
TASK [Download 26B model GGUF]                              changed (check-mode noop, file present pre-flight)
TASK [Download asf0/gemma4_jinja chat template]             changed (check-mode noop, file present pre-flight)
TASK [Verify 26B model is present after download]           ok
TASK [Verify chat template is present after download]       ok
TASK [Deploy llama-server-26b systemd service]              changed (24-line unit content matches role spec exactly; diff captured)
TASK [Reload systemd and enable llama-server-26b]           failed (expected — unit doesn't exist yet in check mode)

PLAY RECAP: ok=8 changed=3 failed=1 (failure benign in check mode)
```

No unexpected changes; **no touches to the existing `llama-server.service`**.
Proceeded to real deploy.

## Ansible real-run summary

Deployed cleanly (exit 0). After completion:

```
$ ls -lah /etc/systemd/system/ | grep llama
-rw-r--r-- 1 root root 637 Apr 25 10:20 llama-server-26b.service   ← new
-rw-r--r-- 1 root root 528 Apr 16 20:17 llama-server.service       ← unchanged

$ systemctl is-enabled llama-server-26b
enabled
```

## Service start + health

Started manually after role completion (role enables but does not start, by
design — `state` not set in the systemd task per Story 9.3 contract):

```
$ systemctl start llama-server-26b.service
$ systemctl status llama-server-26b.service --no-pager | head
● llama-server-26b.service - llama.cpp Server (Gemma 4 26B-A4B Uncensored Q4_K_M, text-only)
     Loaded: loaded (/etc/systemd/system/llama-server-26b.service; enabled)
     Active: active (running) since Sat 2026-04-25 10:20:29 UTC
   Main PID: 43567 (llama-server)
```

Health check passed within ~20 seconds (4th poll attempt at 5 s intervals):

```
$ curl -fsS http://127.0.0.1:8081/health
{"status":"ok"}
```

Bound to `127.0.0.1:8081` per ADR-009 (loopback only):

```
$ ss -ltn | grep -E '8080|8081'
LISTEN 0 512    0.0.0.0:8080  *:*    ← E4B (existing, unchanged)
LISTEN 0 512  127.0.0.1:8081  *:*    ← 26B (new, loopback per ADR-009)
```

## AC-1 — text chat smoke test

Prompt: `Say hello in one word.`

Response (truncated):
```
{
  "choices": [{
    "finish_reason": "stop",
    "message": {
      "role": "assistant",
      "content": "Hello.",                    ← non-empty
      "reasoning_content": "*   Input: \"Say hello in one word.\"\n..."
    }
  }],
  "model": "gemma-4-26B-A4B-it-uncensored-Q4_K_M.gguf",
  "usage": {"completion_tokens": 107, "prompt_tokens": 22, "total_tokens": 129},
  "timings": {"predicted_per_second": 25.11}
}
```

**Result: PASS.** `content` is correctly populated with the user-visible reply
("Hello."); chain-of-thought is sequestered in `reasoning_content` per the
asf0/gemma4_jinja template's design. **No R1 indicator** — the chat-template
fix from ADR-003 is working end-to-end. Note that the model emitted 107 CoT
tokens before the 1-word answer (typical for reasoner-style templates).

## AC-2 — tool-call smoke test

Prompt: `What is the weather in Paris? Use the get_weather tool.`
Tool: `get_weather(city: string)`

Response (truncated):
```
{
  "choices": [{
    "finish_reason": "tool_calls",
    "message": {
      "role": "assistant",
      "content": "",
      "reasoning_content": "...The user provided the city as \"Paris\"...",
      "tool_calls": [{
        "type": "function",
        "function": {
          "name": "get_weather",
          "arguments": "{\"city\":\"Paris\"}"
        },
        "id": "ve5JnLr3U37mmthvjLof2t3ZF5ZU31Nu"
      }]
    }
  }]
}
```

**Result: PASS.** `tool_calls[0].function.name == "get_weather"`,
`arguments == {"city":"Paris"}`, `finish_reason == "tool_calls"`. Single
synthetic prompt; the actual Sprint 1 exit gate is the Story 9.5 50-prompt
test harness.

## AC-3 — decode tok/s

From AC-1 timings: **25.11 tok/s** (107 predicted tokens / 4.26 s).
Confirmed by AC-2 timings: **24.87 tok/s** (83 tokens / 3.34 s).

| Backend | Decode tok/s | Reference |
|---|---|---|
| E4B (Q5_K_P, ~7 GB) on :8080 | 35.7 | epic story 9.1 baseline |
| 26B-A4B (Q4_K_M, ~17 GB) on :8081 | **25.0** | this story |

Within the research band of 18-30 tok/s for the 26B model. ~30% slower than
E4B as expected for the larger active-parameter footprint. Recorded for the
`26b-baseline-perf.md` artefact noted in Story 9.4 AC.

## AC-4 — E4B unaffected

```
$ systemctl status llama-server.service --no-pager | head
● llama-server.service - llama.cpp Server (Gemma 4 Uncensored + Multimodal)
     Active: active (running) since Fri 2026-04-24 17:05:21 UTC; 17h ago
   Main PID: 91 (llama-server)              ← same PID as pre-deploy
   Memory: 152.4M

$ curl -fsS http://127.0.0.1:8080/health
{"status":"ok"}
```

E4B PID and uptime unchanged. No restart triggered by the role or by 26B's
service unit (`After=` directive is non-coupling; E4B was already up).

## Open WebUI registration

### Discovered state

Existing `open-webui` Docker container was started ad-hoc with `docker run`
(no compose file, no systemd unit — confirmed via `find` and `systemctl` greps;
no IaC entry in the homelab repo). Container env had a single endpoint:

```
OPENAI_API_BASE_URL=http://host.docker.internal:8080/v1
OPENAI_API_KEY=sk-none
```

### Approach taken

Recreated the container with multi-endpoint env vars per Open WebUI docs
(`OPENAI_API_BASE_URLS` plural, semicolon-separated, with matching
`OPENAI_API_KEYS`). The named volume `open-webui` (mounted at
`/app/backend/data`) preserves all user data, accounts, chat history, and
settings — recreation is non-destructive.

### Networking decision (architectural note)

Initial recreation kept the bridge network and used `host.docker.internal`,
but **the 26B endpoint binds to `127.0.0.1:8081` per ADR-009 (loopback-only)**
which is unreachable from the docker bridge gateway (172.17.0.1). Two options:

1. Relax 26B bind to `0.0.0.0:8081` — **violates ADR-009** (loopback boundary
   is the security mechanism for the unauthenticated llama-server endpoint).
2. Switch OWUI to host networking (`--network host`) so its container shares
   the LXC's network namespace and can reach `127.0.0.1:8081` directly.

Chose option 2 — preserves ADR-009. Set `PORT=3000` env var (OWUI's internal
listen port, default 8080 collides with E4B in host-net mode), pointed both
endpoints at `127.0.0.1`, and removed the `-p` mapping (irrelevant under host
networking). External port 3000 still works because OWUI now binds directly
on `0.0.0.0:3000` in the LXC.

Final container env:
```
OPENAI_API_BASE_URLS=http://127.0.0.1:8080/v1;http://127.0.0.1:8081/v1
OPENAI_API_KEYS=sk-none;sk-none
OLLAMA_BASE_URL=http://127.0.0.1:11434
PORT=3000
WEBUI_URL=https://chat.bi-services.be   (preserved)
WEBUI_SECRET_KEY=...                    (preserved — same as before)
```

### Verification

Both backends reachable from inside the OWUI container:
```
$ docker exec open-webui curl -fsS http://127.0.0.1:8081/v1/models | head
{"models":[{"name":"gemma-4-26B-A4B-it-uncensored-Q4_K_M.gguf",...
$ docker exec open-webui curl -fsS http://127.0.0.1:8080/v1/models | head
{"models":[{"name":"Gemma-4-E4B-Uncensored-HauhauCS-Aggressive-Q5_K_P.gguf",...
```

OWUI HTTP externally reachable on `http://192.168.50.160:3000/health` → 200.
Browser-based confirmation that both models appear in the model picker is
left to operator manual check (the `/openai/models` proxied endpoint requires
a logged-in session); the per-backend `/v1/models` reachability from inside
the container is the equivalent technical proof.

## R1 status

**No R1 indicator from this story's smoke tests.** AC-1 returned a non-empty
`content` field with the user-visible answer; `reasoning_content` is the
correct sink for chain-of-thought per the asf0 template. R1 (chat-template fix
incomplete) will be measured at scale by Story 9.5's 50-prompt gate.

## Follow-ups for Sprint 1 retro

1. **Open WebUI is not under IaC** — manual `docker run` setup. Recommend a
   dedicated Ansible role (or compose file) so future env-var changes are
   reproducible. Captured for retro / Sprint 3 backlog (Story 9.13/9.14
   territory: Open WebUI reconfiguration).
2. **ZFS snapshot vs `pct snapshot`** — the `mp0` bind-mount blocks `pct
   snapshot`. Workable for now (rootfs ZFS snapshot handles the relevant
   mutable state) but worth documenting in the runbook so operators don't
   assume `pct snapshot 160` will work.
3. **ct-dev-test deviation** — per memory `feedback_test_container.md` we
   normally deploy there first. Documented above; consider whether a no-GPU
   "render-only" check is worth wiring into a future iteration of the role.
