# Story 8.3: Set Up GPU and LXC Container with Ollama

Status: done

## Story

As a homelab operator,
I want Ollama running in a GPU-accelerated LXC container on pve3,
So that I can run local LLM inference on my homelab.

## Context Note

The RX 9070 XT dGPU is physically connected via OCULink but not detected by pve3 (USB4 PCIe tunneling issue — under investigation). This story proceeds with the **integrated Radeon 890M (RDNA 3.5)** GPU which is working and detected. The LXC container, Ollama install, and Vulkan setup are identical — when the dGPU is resolved, it's just a matter of updating the device passthrough. A separate story will be added for OCULink troubleshooting.

## Acceptance Criteria

1. **Given** pve3 is in the cluster with IOMMU configured (Story 8.1) and upgraded to PVE 9 (kernel 6.17)
   **When** I check the GPU on the host
   **Then** the Radeon 890M iGPU is detected at `/dev/dri/card1` and `/dev/dri/renderD128`

2. **Given** the iGPU is available on the host
   **When** I create the AI container
   **Then** a privileged LXC container `ct-ai-01` exists on pve3 with 8 cores, 16GB RAM, 50GB disk, IP `192.168.50.160`

3. **Given** ct-ai-01 exists
   **When** I configure GPU passthrough
   **Then** `/dev/dri/card1` and `/dev/dri/renderD128` are accessible inside the container

4. **Given** GPU is passed through to the container
   **When** I install Ollama
   **Then** Ollama is installed with Vulkan backend enabled (`OLLAMA_VULKAN=1`)

5. **Given** Ollama is running with Vulkan
   **When** I run `ollama run gemma4:e4b` inside the container
   **Then** the model downloads, loads, and produces a coherent response

6. **Given** Ollama is serving a model
   **When** I check `ollama ps`
   **Then** GPU layers are being used (not CPU-only fallback)

## Edge Cases & Error Scenarios

1. **Side effects:**
   - New LXC container `ct-ai-01` (VMID 160) created on pve3
   - Container is privileged (required for GPU device passthrough)
   - `/dev/dri/*` devices shared between host and container (not exclusive)
   - Ollama downloads model files to container storage (~3GB for gemma4:e4b)

2. **Dependency failure:**
   - If Vulkan not detected inside LXC: verify `/dev/dri/*` passthrough with correct cgroup permissions and mode 0666
   - If Ollama falls back to CPU: check `OLLAMA_VULKAN=1` is set, verify `vulkaninfo` works inside container
   - If container can't access GPU: ensure container is privileged, check lxc.cgroup2 and lxc.mount.entry in config
   - If model download fails: check internet connectivity from container, retry

3. **Assumptions:**
   - pve3 is on PVE 9.1.7 with kernel 6.17 (upgraded in this session)
   - iGPU device nodes exist at `/dev/dri/card1` and `/dev/dri/renderD128` on host
   - Container will use DHCP or static IP on the 192.168.50.0/24 network
   - Mesa/Vulkan drivers are available in Debian Trixie repos (PVE 9 base)

## Eval Assertions

<!-- Binary test assertions derived from acceptance criteria. Used by /autoresearch:fix for post-code-review iteration loops. -->

| # | Assertion | Command/Check | Pass Criteria |
|---|-----------|---------------|---------------|
| AC-1 | iGPU detected on host | `ssh pve3 'ls -la /dev/dri/card1 /dev/dri/renderD128'` | Both device nodes exist |
| AC-2 | ct-ai-01 exists and running | `ssh pve3 'pct status 160'` | Shows "status: running" |
| AC-3 | GPU devices in container | `ssh pve3 'pct exec 160 -- ls -la /dev/dri/'` | Shows card and renderD128 |
| AC-4 | Ollama installed with Vulkan | `ssh pve3 'pct exec 160 -- ollama --version'` | Returns version string |
| AC-5 | Gemma 4 E4B runs | `ssh pve3 'pct exec 160 -- ollama run gemma4:e4b "Say hello in one word"'` | Returns a coherent response |
| AC-6 | GPU layers used | `ssh pve3 'pct exec 160 -- ollama ps'` | Shows GPU percentage > 0% |

## Tasks / Subtasks

- [x] Task 0: Verify Story 8.1/8.2 prerequisites
  - [x] iGPU device nodes confirmed: `/dev/dri/card1` + `/dev/dri/renderD128`
  - [x] IOMMU group 23 contains iGPU at `0000:c7:00.0`
- [x] Task 1: Create privileged LXC container ct-ai-01 (AC: 2)
  - [x] Created VMID 160, Debian 13 Trixie, 8 cores, 16GB RAM, 50GB disk on local-zfs
  - [x] Static IP 192.168.50.160/24, gateway .1, DNS .194
  - [x] Privileged container (unprivileged=0), nesting enabled, onboot=1
  - [x] Added local-zfs storage to Proxmox (`pvesm add zfspool local-zfs --pool rpool/data`)
  - [x] Container started and running
- [x] Task 2: Configure GPU device passthrough (AC: 3)
  - [x] Added `lxc.cgroup2.devices.allow: c 226:* rwm` and `lxc.mount.entry: /dev/dri` to container config
  - [x] Devices visible inside container: card1 + renderD128
  - [x] Fixed renderD128 group ownership (`postdrop` → `render`) — udev rule added for persistence
- [x] Task 3: Install Vulkan drivers inside container (AC: 4)
  - [x] Installed `mesa-vulkan-drivers vulkan-tools`
  - [x] `vulkaninfo --summary` shows AMD Radeon Graphics (RADV GFX1150), Vulkan 1.4.305
- [x] Task 4: Install Ollama with Vulkan backend (AC: 4)
  - [x] Installed curl + zstd (prerequisites), then Ollama 0.20.7
  - [x] Created systemd override `/etc/systemd/system/ollama.service.d/vulkan.conf` with `OLLAMA_VULKAN=1`
  - [x] Service active, Vulkan GPU detected: "AMD Radeon Graphics (RADV GFX1150)" 16.5 GiB
- [x] Task 5: Test with Gemma 4 E4B (AC: 5, 6)
  - [x] `ollama run gemma4:e4b` — model downloaded (~9.6GB), produces coherent responses
  - [x] `ollama ps` shows **68% CPU / 32% GPU** — GPU layers active
  - [x] Ollama API responds at `http://localhost:11434/api/tags`

## Dev Notes

### GPU Context

- **Active GPU:** Radeon 890M (iGPU, RDNA 3.5) — integrated, uses shared system RAM (8GB UMA allocated in BIOS)
- **Pending GPU:** RX 9070 XT (dGPU, RDNA 4, 16GB VRAM) — connected via OCULink but not detected (USB4 tunneling issue)
- **Device nodes on host:** `/dev/dri/card1` (display), `/dev/dri/renderD128` (compute)
- **No `/dev/kfd`** — KFD (ROCm compute) is not needed for Vulkan

### LXC GPU Passthrough Pattern

From the research doc and existing ct-media-01 pattern (which is also privileged for GPU):

```
# In /etc/pve/lxc/160.conf:
lxc.cgroup2.devices.allow: c 226:* rwm
lxc.mount.entry: /dev/dri dev/dri none bind,optional,create=dir
```

### Container Sizing

- **8 cores** — enough for Ollama + model inference
- **16GB RAM** — conservative; iGPU uses shared RAM, so container+GPU share from the same pool. 16GB leaves ~12GB for host/other containers from the 28GB total.
- **50GB disk** — models can be large (gemma4:e4b ~3GB, larger models 10-14GB)

### Previous Story Learnings

- pve3 upgraded to PVE 9.1.7 (kernel 6.17.13-2-pve) during OCULink investigation
- ZFS mirror root on NVMe 1+2, NVMe 3 untouched for Story 8.5
- pve-host role applied, NIC eno1 tuned
- 5GbE NIC (RTL8126) now detected on PVE 9

### References

- [Source: planning-artifacts/research/technical-pve3-oculink-gpu-llm-research-2026-04-15.md#AMD GPU LXC Device Configuration]
- [Source: planning-artifacts/research/technical-pve3-oculink-gpu-llm-research-2026-04-15.md#Recommended Software Stack]
- [Source: planning-artifacts/epics.md#Story 8.3]
- [Source: docs/architecture-homelab-infra.md#Infrastructure Resources]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6[1m])

### Debug Log References

- renderD128 had wrong group in container (`postdrop` instead of `render`) — fixed with `chgrp` + udev rule
- Ollama service didn't detect GPU until renderD128 permissions were fixed
- GPU offload is partial (68/32 CPU/GPU split) because gemma4:e4b (Q4_K_M, ~9.6GB) exceeds the 8GB UMA allocation
- pve3 upgraded to PVE 9.1.7 (kernel 6.17.13-2-pve) during this epic for OCULink investigation
- local-zfs storage pool had to be manually added to Proxmox (`pvesm add zfspool`)

### Completion Notes List

- ct-ai-01 (VMID 160) running on pve3 with Debian 13 Trixie
- GPU passthrough working: Radeon 890M iGPU via Vulkan (RADV GFX1150)
- Ollama 0.20.7 with Vulkan backend serving Gemma 4 E4B
- 68/32 CPU/GPU split — partial offload due to UMA memory constraints
- OCULink dGPU (RX 9070 XT) still not detected — separate troubleshooting needed
- API endpoint: http://192.168.50.160:11434 (from within container, needs OLLAMA_HOST=0.0.0.0 for external access)

### Change Log

- 2026-04-15: Story implemented — ct-ai-01 with Ollama + Vulkan iGPU
- 2026-04-15: Code review — approved, 0 findings, 6/6 eval assertions passed, marked done

### File List

No repository files modified — all changes on pve3 and ct-ai-01 container
