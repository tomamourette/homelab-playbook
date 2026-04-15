# Story 8.4: Deploy Models and Open WebUI

Status: done

## Story

As a homelab operator,
I want a web chat interface (Open WebUI) connected to Ollama with a usable model deployed,
So that I have a self-hosted ChatGPT-like experience accessible from any device on my network.

## Context Note

The RX 9070 XT dGPU is not yet detected (OCULink issue). Gemma 4 26B (Q3_K_M, ~14GB) requires the dGPU's 16GB VRAM and **cannot run on the iGPU**. This story deploys Open WebUI and a model that works on the current hardware (iGPU with 8GB UMA). When the dGPU is resolved, pulling and running the 26B model is a single `ollama pull` command — no infrastructure changes needed.

**Current model:** Gemma 4 E4B (4B dense, ~3GB, already downloaded in Story 8.3)
**Alternative useful model:** Qwen 3 8B Q4 (~5GB, good for coding/chat)

## Acceptance Criteria

1. **Given** Ollama is running with Vulkan iGPU (Story 8.3)
   **When** I configure Ollama to listen on all interfaces
   **Then** the Ollama API is accessible from the network at `http://192.168.50.160:11434`

2. **Given** Ollama API is network-accessible
   **When** I deploy Open WebUI inside ct-ai-01
   **Then** Open WebUI is running and accessible at `http://192.168.50.160:3000`

3. **Given** Open WebUI is running
   **When** I open the web interface and select a model
   **Then** Open WebUI connects to Ollama and lists available models

4. **Given** Open WebUI is connected to Ollama
   **When** I send a chat message
   **Then** the model produces a coherent response in the web interface

5. **Given** the full stack is working
   **When** I access Open WebUI from another device on the network
   **Then** the web interface loads and is usable from any browser on the LAN

## Edge Cases & Error Scenarios

1. **Side effects:**
   - Ollama config changed to listen on 0.0.0.0 (exposes API to LAN — acceptable in homelab)
   - Docker installed inside ct-ai-01 (required for Open WebUI)
   - Open WebUI container stores user data in a Docker volume
   - Additional models can be pulled later from Open WebUI or CLI

2. **Dependency failure:**
   - If Open WebUI can't reach Ollama: verify OLLAMA_HOST is set to 0.0.0.0, port 11434 is open
   - If Docker install fails in LXC: ensure nesting=1 is set on the container
   - If Open WebUI shows no models: check Ollama API connectivity from within the Docker network

3. **Assumptions:**
   - ct-ai-01 (VMID 160) is running with Ollama active (Story 8.3 complete)
   - Container has internet access for Docker image pull and model downloads
   - 50GB root disk has enough space for Docker + models (~15GB needed)

## Eval Assertions

<!-- Binary test assertions derived from acceptance criteria. Used by /autoresearch:fix for post-code-review iteration loops. -->

| # | Assertion | Command/Check | Pass Criteria |
|---|-----------|---------------|---------------|
| AC-1 | Ollama API network accessible | `curl -s http://192.168.50.160:11434/api/tags` | Returns JSON with models list |
| AC-2 | Open WebUI running | `curl -s -o /dev/null -w '%{http_code}' http://192.168.50.160:3000` | Returns 200 or 301 |
| AC-3 | Models listed in API | `curl -s http://192.168.50.160:11434/api/tags \| grep -q gemma` | Exits with code 0 |
| AC-4 | Chat produces response | `curl -s http://192.168.50.160:11434/api/generate -d '{"model":"gemma4:e4b","prompt":"Hi","stream":false}' \| grep -q response` | Returns JSON with response field |
| AC-5 | WebUI accessible from LAN | `curl -s -o /dev/null -w '%{http_code}' http://192.168.50.160:3000` | Returns 200 or 301 from dev container |

## Tasks / Subtasks

- [x] Task 0: Verify Story 8.3 prerequisites
  - [x] Ollama active, gemma4:e4b available (9.6 GB)
- [x] Task 1: Configure Ollama for network access (AC: 1)
  - [x] Added `OLLAMA_HOST=0.0.0.0` to systemd override
  - [x] API accessible from network: `curl http://192.168.50.160:11434/api/tags` returns models
- [x] Task 2: Install Docker inside ct-ai-01 (AC: 2)
  - [x] Docker CE installed via get.docker.com script
  - [x] `docker ps` works
- [x] Task 3: Deploy Open WebUI (AC: 2, 3)
  - [x] Deployed `ghcr.io/open-webui/open-webui:main` on port 3000, connecting to host Ollama via host.docker.internal
  - [x] Web interface accessible at http://192.168.50.160:3000 (HTTP 200)
  - [x] Admin account creation available on first visit
- [x] Task 4: Test chat flow (AC: 4)
  - [x] API test: `curl /api/generate` with gemma4:e4b produces response
  - [x] Web UI ready for browser testing
- [x] Task 5: Verify LAN access (AC: 5)
  - [x] `curl http://192.168.50.160:3000` from ct-dev-homelab returns HTTP 200

## Dev Notes

### Previous Story Learnings (8.3)

- ct-ai-01 is VMID 160, Debian 13 Trixie, 8 cores, 16GB RAM, 50GB disk, IP 192.168.50.160
- Ollama 0.20.7 installed with Vulkan, running as systemd service
- Vulkan override at `/etc/systemd/system/ollama.service.d/vulkan.conf`
- GPU passthrough working: 68% CPU / 32% GPU split for gemma4:e4b
- renderD128 group fix applied with udev rule
- Container has nesting=1 (required for Docker-in-LXC)

### Open WebUI Deployment

Open WebUI runs as a Docker container. The standard command:
```bash
docker run -d -p 3000:8080 \
  --add-host=host.docker.internal:host-gateway \
  -v open-webui:/app/backend/data \
  --name open-webui \
  --restart always \
  ghcr.io/open-webui/open-webui:main
```

It connects to Ollama via `host.docker.internal:11434` by default.

### Ollama Network Access

By default Ollama listens on `127.0.0.1:11434`. To expose to the network:
```
Environment=OLLAMA_HOST=0.0.0.0
```

This is safe in a homelab LAN. For production, add Traefik + Authelia (future story).

### References

- [Source: planning-artifacts/research/technical-pve3-oculink-gpu-llm-research-2026-04-15.md#Recommended Software Stack]
- [Source: planning-artifacts/epics.md#Story 8.4]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6[1m])

### Debug Log References

- Ollama systemd override updated to include both OLLAMA_VULKAN=1 and OLLAMA_HOST=0.0.0.0
- Open WebUI uses `--add-host=host.docker.internal:host-gateway` to reach Ollama on the host
- Gemma 4 E4B responds but can be quirky with short prompts (small model behavior)

### Completion Notes List

- Ollama API exposed on 0.0.0.0:11434 (LAN accessible)
- Docker CE installed in ct-ai-01
- Open WebUI deployed at http://192.168.50.160:3000
- Full stack: Open WebUI → Ollama (Vulkan) → Gemma 4 E4B → iGPU (Radeon 890M)
- Ready for user to create admin account and chat via browser
- Additional models can be pulled from Open WebUI settings or `ollama pull`

### Deployment Verification

Result: 5/5 assertions passed.
All eval assertions verified on target.

| # | Assertion | Result |
|---|-----------|--------|
| AC-1 | Ollama API network accessible | PASS — returns JSON with gemma4:e4b |
| AC-2 | Open WebUI running | PASS — HTTP 200 |
| AC-3 | Models listed in API | PASS — gemma in response |
| AC-4 | Chat produces response | PASS — /api/generate returns response |
| AC-5 | WebUI accessible from LAN | PASS — HTTP 200 from ct-dev-homelab |

### Change Log

- 2026-04-15: Story implemented and verified — Open WebUI + Ollama + Gemma 4 E4B on iGPU

### File List

No repository files modified — all changes on ct-ai-01 container (VMID 160)
