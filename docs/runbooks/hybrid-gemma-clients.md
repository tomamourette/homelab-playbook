# Hybrid Gemma Serving — Client Configuration Runbook

**Story 9.17 (Sprint 3 EXIT GATE) — MVP** · last verified 2026-04-25

This runbook documents how each consumer (Open WebUI, Continue.dev, Cursor,
mobile, scripts) connects to the LiteLLM gateway in front of the
hybrid-gemma stack on `ct-ai-01` (192.168.50.160).

## Stack overview

```
Client ──► LiteLLM :4000 ──► gemma-hybrid-proxy :8000 ──► llama-server E4B  :8080
                                                       └► llama-server 26B :8081
```

- LiteLLM listens on `192.168.50.160:4000` (LAN-private).
- Bearer-token auth — every `/v1/*` path requires `Authorization: Bearer $LITELLM_MASTER_KEY`.
- Master key stored in Ansible Vault at
  `homelab-infra/ansible/inventories/homelab/host_vars/ct-ai-01/vault.yml`
  under `vault_litellm_master_key`. Operators retrieve via
  `ansible-vault view`. Real value also kept in the operator's password
  manager.
- Three model aliases visible to clients:
  - `gemma4-26b-text` — text-only, the 26B reasoner. **Production-reliable.**
  - `gemma4-e4b-vision` — image-attached, the E4B vision model. **Production-reliable.**
  - `gemma4-auto` — server-side router (E4B preprocesses, 26B reasons).
    Reliable for text + passive-image (the 80% case).
    See "Known limitation" below for the agent-loop gap.

## Known limitation — Sprint 4 Story 9.22 priority gap

The `gemma4-auto` agent loop emits tool calls as **plain-text tokens** in
`delta.content` instead of structured `delta.tool_calls`. This was
surfaced by Story 9.15's 25-prompt smoke (0/10 tool-triggering, 0/3
multi-iteration). Sprint 4 priority Story 9.22 closes this gap.

**Production guidance until 9.22 lands:**

| Use case | Recommended alias |
|----------|-------------------|
| Plain text chat | `gemma4-26b-text` |
| Image attached, no tool calls expected | `gemma4-auto` (preprocessing path) |
| Image attached, deep-vision tool calls expected | `gemma4-e4b-vision` (direct) |
| Tool-call workflows (e.g. Continue.dev agent mode) | `gemma4-26b-text` |

Reference: `_bmad-output/implementation-artifacts/sprint3-agentloop-smoke-results-2026-04-25.md`,
ADR-002 Sprint 3 addendum, Sprint 4 Story 9.22 in
`hybrid-gemma-serving-epics.md`.

## Open WebUI (chat.bi-services.be)

Already configured by Story 9.17 cutover. Verify with:

```bash
ssh root@192.168.50.160 "docker inspect open-webui --format '{{range .Config.Env}}{{println .}}{{end}}'" \
  | grep -E 'OPENAI_API_BASE_URLS|OPENAI_API_KEYS' | sed 's/sk-[a-f0-9]*/sk-REDACTED/g'

# Expected:
# OPENAI_API_BASE_URLS=http://127.0.0.1:4000/v1
# OPENAI_API_KEYS=sk-REDACTED
```

OWUI runs in `--network host` on `ct-ai-01`, so it reaches LiteLLM via
loopback `127.0.0.1:4000` (no LAN/Tailscale dependency).

## Continue.dev (IDE)

Add to `~/.continue/config.yaml` on the operator's workstation:

```yaml
models:
  - name: Gemma 4 26B (text)
    provider: openai
    model: gemma4-26b-text
    apiBase: http://192.168.50.160:4000/v1
    apiKey: <paste-litellm-master-key-here>
    contextLength: 32000

  - name: Gemma 4 E4B (vision)
    provider: openai
    model: gemma4-e4b-vision
    apiBase: http://192.168.50.160:4000/v1
    apiKey: <paste-litellm-master-key-here>
    contextLength: 8000

  - name: Gemma 4 auto-route
    provider: openai
    model: gemma4-auto
    apiBase: http://192.168.50.160:4000/v1
    apiKey: <paste-litellm-master-key-here>
    contextLength: 32000
```

Retrieve the key once with:

```bash
cd ~/workspace/homelab/homelab-infra/ansible
ansible -i inventories/homelab/hosts.ini ct-ai-01 -m debug \
  -a 'msg={{ vault_litellm_master_key }}'
```

If the workstation is off the LAN, replace the IP with the ct-ai-01
Tailscale hostname (Tailscale not yet installed on ct-ai-01 at MVP gate;
pending follow-up — see "Off-LAN access" below).

## Cursor (IDE)

Cursor → Settings → Models → Add custom OpenAI-compatible model:

| Field | Value |
|-------|-------|
| Model name | `gemma4-26b-text` (or `gemma4-auto`, `gemma4-e4b-vision`) |
| API endpoint | `http://192.168.50.160:4000/v1` |
| API key | (vault-stored master key) |

Same off-LAN caveat as Continue.dev.

## Mobile / phone

The operator's Android phone is on the homelab tailnet
(`project_phone_notifications_tailscale.md`). Two paths:

### Path 1 — via Open WebUI (default, no extra config)

Open https://chat.bi-services.be from the phone browser; sign in with
the existing OWUI account; chat. Open WebUI handles the LiteLLM call
internally on `ct-ai-01`. **Tom's typical mobile path.**

### Path 2 — direct LiteLLM (any OpenAI-compatible mobile app)

Useful for Mac/iOS apps like *Pal* or *ChatBox*:

| Setting | Value |
|---------|-------|
| Endpoint | `http://192.168.50.160:4000/v1` |
| API key | (vault-stored master key) |
| Model | `gemma4-26b-text` |

Requires the phone to be on home wifi (LAN reach) OR on the tailnet AND
ct-ai-01 to be on the tailnet (ct-ai-01 not yet enrolled in Tailscale —
follow-up). Until ct-ai-01 is on Tailscale, Path 1 (OWUI) is the only
off-LAN-reachable mobile path.

## Off-LAN access — follow-up

ADR-010 says the long-term remote-access pattern is Tailscale on
ct-ai-01. As of Story 9.17 close, ct-ai-01 is **not** in the tailnet.
This is acceptable for the MVP exit gate because:

1. Open WebUI at `chat.bi-services.be` (Cloudflare-tunneled via
   ct-docker-01 on the tailnet) covers operator chat from any network.
2. Continue.dev / Cursor are LAN-only at the moment, which matches the
   operator's typical work pattern (laptop on home wifi).

**Follow-up (Sprint 4 nice-to-have):** install Tailscale in CT 160
following the same pattern as ct-docker-01 / pve3 / phone, then update
this runbook with `apiBase: http://<tailnet-ip>:4000/v1` for the IDE
clients. No LiteLLM-side change needed (already binds `0.0.0.0`).

## Prometheus + Grafana

- Prometheus scrape job: `litellm-gateway` on
  `192.168.50.160:4000/metrics/` (note trailing slash — avoids 307 hop).
- Grafana dashboard: **LiteLLM — Hybrid Gemma Gateway**
  (`uid: hybrid-gemma-litellm`, folder *Homelab*).
- Open from `https://grafana.bi-services.be` after Authelia SSO.

Provisioned from
`homelab-apps/stacks/observability/dashboards/litellm-gemma.json` and
auto-loaded by Grafana's file provisioner (10s update interval).

## Smoke test (post-deploy)

```bash
KEY=$(ansible -i ~/workspace/homelab/homelab-infra/ansible/inventories/homelab/hosts.ini \
       ct-ai-01 -m debug -a 'msg={{ vault_litellm_master_key }}' \
       | grep -oP '(?<="msg": ")[^"]+')

# Models
curl -s -H "Authorization: Bearer $KEY" \
  http://192.168.50.160:4000/v1/models | jq '.data[].id'
# → "gemma4-auto" "gemma4-26b-text" "gemma4-e4b-vision"

# Text chat
curl -fsS -X POST http://192.168.50.160:4000/v1/chat/completions \
  -H "Authorization: Bearer $KEY" -H 'Content-Type: application/json' \
  -d '{"model":"gemma4-26b-text","messages":[{"role":"user","content":"Reply: ok"}],"max_tokens":256,"temperature":0}' \
  | jq -r '.choices[0].message.content'
```

## Rollback (if needed)

Reverting OWUI to the proxy (Story 9.11 state):

```bash
ssh root@192.168.50.160 << 'EOF'
docker stop open-webui && docker rm open-webui
docker run -d \
    --name open-webui --network host --restart always \
    -v open-webui:/app/backend/data \
    -e WEBUI_SECRET_KEY='5441a1dfeeee59cc1ab3d03d5b11c890ae2234c97295b46ca7be170a7375f801' \
    -e OLLAMA_BASE_URL='http://127.0.0.1:11434' \
    -e PORT='3000' \
    -e OPENAI_API_BASE_URLS='http://127.0.0.1:8000/v1' \
    -e OPENAI_API_KEYS='noop' \
    -e WEBUI_URL='https://chat.bi-services.be' \
    ghcr.io/open-webui/open-webui:main
EOF
```

Reverting LiteLLM bind to loopback-only (defaults change):

```bash
cd ~/workspace/homelab/homelab-infra/ansible
git checkout HEAD -- roles/litellm-gateway/defaults/main.yml  # if not yet committed
# or edit defaults/main.yml: litellm_listen_host: 127.0.0.1
ansible-playbook -i inventories/homelab/hosts.ini playbooks/deploy-ollama-models.yml \
  --limit ct-ai-01 --tags litellm-gateway
```

Removing the Prometheus scrape (rolls back observability surface):

```bash
git checkout HEAD -- ~/workspace/homelab/homelab-apps/stacks/observability/config/prometheus.yml
scp ~/workspace/homelab/homelab-apps/stacks/observability/config/prometheus.yml \
    root@192.168.50.194:/opt/homelab-apps/stacks/observability/config/prometheus.yml
ssh root@192.168.50.194 "docker exec prometheus wget -qO- --post-data='' http://localhost:9090/-/reload"
```

ZFS rootfs rollback (last resort, full container revert):

```bash
ssh pve3 "zfs rollback rpool/data/subvol-160-disk-0@pre-9-17-mvp-cutover-20260425-2030"
```
