---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments: []
workflowType: 'research'
lastStep: 6
research_type: 'technical'
research_topic: 'Minisforum N5 Pro as PVE3 + OCULink GPU for Local LLM'
research_goals: 'Add N5 Pro as third Proxmox node; research OCULink + RX 9070 XT for local LLM inference'
user_name: 'tomamourette'
date: '2026-04-15'
web_research_enabled: true
source_verification: true
---

# Research Report: Minisforum N5 Pro as PVE3 + OCULink GPU for Local LLM

**Date:** 2026-04-15
**Author:** tomamourette
**Research Type:** Technical

---

## Executive Summary

This research covers adding a Minisforum N5 Pro (AMD Ryzen AI 9 HX PRO 370, 12C/24T, up to 96GB DDR5 ECC) as the third node (pve3) to the existing 2-node Proxmox home-cluster, and setting up an AMD Radeon RX 9070 XT 16GB via OCULink for local LLM inference.

**Key findings:**

1. **The N5 Pro is the most powerful node in the cluster** -- 12C/24T Zen 5, 10GbE networking, OCULink, 50 TOPS NPU, and 5x HDD bays. Confirmed Proxmox-compatible with active community validation.
2. **Going from 2 to 3 nodes transforms cluster reliability** -- quorum changes from "both nodes must be up" to "any 2 of 3", giving real high-availability for the first time.
3. **Vulkan beats ROCm on RDNA 4 today** -- 1.5-3.3x faster on the RX 9070 XT for LLM inference via llama.cpp. Zero driver dependencies (Mesa RADV ships with Linux).
4. **OCULink bandwidth is not a bottleneck for LLM inference** -- only 10-20% penalty during model loading; negligible during generation.
5. **Gemma 4 26B fits in 16GB** -- it's a MoE model (25.8B total, 3.8B active). Use IQ4_XS quantization (~14GB file, ~15GB VRAM) for optimal fit. Start testing with Gemma 4 E4B (4B dense).
6. **LXC > VM for GPU workloads** -- shared kernel, no exclusive GPU lock, multiple containers can share the same card.

**Recommended stack:** Proxmox LXC with Ollama (Vulkan, `OLLAMA_VULKAN=1`) + Open WebUI.

## Table of Contents

1. [Technical Research Scope Confirmation](#technical-research-scope-confirmation)
2. [Technology Stack Analysis](#technology-stack-analysis)
3. [Integration Patterns Analysis](#integration-patterns-analysis)
4. [Architectural Patterns and Design](#architectural-patterns-and-design)
5. [Implementation Roadmap](#implementation-roadmap)
6. [Risk Assessment and Mitigation](#risk-assessment-and-mitigation)
7. [Cost and Power Analysis](#cost-and-power-analysis)
8. [Future Outlook](#future-outlook)
9. [Sources](#sources)

---

## Technical Research Scope Confirmation

**Research Topic:** Minisforum N5 Pro as PVE3 + OCULink GPU for Local LLM
**Research Goals:** Add N5 Pro as third Proxmox node; research OCULink + RX 9070 XT for local LLM inference

**Technical Research Scope:**

- Architecture Analysis - hardware specs, cluster topology, GPU passthrough
- Implementation Approaches - Proxmox join procedure, BIOS configuration, driver setup
- Technology Stack - ROCm, llama.cpp, Ollama, Vulkan backends for AMD GPU
- Integration Patterns - Terraform/Ansible integration, monitoring, storage
- Performance Considerations - OCULink bandwidth impact, LLM inference benchmarks

**Research Methodology:**

- Current web data with rigorous source verification
- Live infrastructure inspection via SSH (pve1, pve2)
- Cross-referenced against existing documentation in homelab repo
- Confidence levels flagged for uncertain information

**Scope Confirmed:** 2026-04-15

---

## Technology Stack Analysis

### Track 1: Minisforum N5 Pro Hardware

> **Note:** The user initially referenced "M5 Pro" — web research confirms the product is the **Minisforum N5 Pro**, an AI NAS powered by the AMD Ryzen AI 9 HX PRO 370. This is a significantly more capable device than the older MS-05/M5 Pro line (Ryzen 7 5825U). The specs below reflect the N5 Pro.

#### Hardware Specifications

| Component | Specification |
|-----------|--------------|
| **CPU** | AMD Ryzen AI 9 HX PRO 370 — Zen 5 + Zen 5C, 12C/24T, up to 5.1 GHz boost |
| **NPU** | Integrated XDNA 2, 50 TOPS |
| **iGPU** | AMD Radeon 890M (RDNA 3.5), AV1/H.265 HW encode/decode |
| **RAM** | 2x SO-DIMM DDR5-5600 (ECC support), up to 96 GB |
| **Storage** | 5x 3.5" HDD bays + 3x M.2 slots (2230/2280/22110) + U.2 adapter option |
| **Network** | 1x 10GbE + 1x 5GbE RJ45 |
| **USB** | USB 4.0 ports (40 Gbps) |
| **OCULink** | Yes — PCIe 4.0 x4 |
| **Display** | HDMI output |
| **Power** | ~45W sustained, ~55W peak |
| **OS Support** | Proxmox, TrueNAS, Unraid, Linux, Windows |

_Source: [Minisforum N5 Pro Official](https://www.minisforum.com/products/n5-pro), [ServeTheHome Review](https://www.servethehome.com/minisforum-n5-pro-review-an-awesome-nas-platform/), [Notebookcheck Review](https://www.notebookcheck.net/Minisforum-N5-Pro-World-s-first-AI-NAS-with-AMD-Ryzen-AI-9-HX-PRO-370-IFA-2025-Award-winner-review.1142209.0.html)_

#### Comparison with Existing Nodes

| Attribute | pve1 | pve2 | pve3 (N5 Pro) |
|-----------|------|------|---------------|
| **CPU** | Intel i3-N305 (8C/8T) | Intel N200 (4C/4T) | AMD Ryzen AI 9 HX PRO 370 (12C/24T) |
| **RAM** | 46 GB DDR4 | 46 GB DDR4 | Up to 96 GB DDR5 ECC |
| **NVMe** | 466 GB | 932 GB | Up to 3x M.2 + 5x HDD |
| **Network** | 2.5 GbE (Realtek) | 2.5 GbE (Realtek) | 10 GbE + 5 GbE |
| **OCULink** | No | No | Yes (PCIe 4.0 x4) |
| **NPU** | No | No | 50 TOPS XDNA 2 |

The N5 Pro will be the most powerful node in the cluster by a significant margin.

#### Proxmox Compatibility

- **Confirmed compatible** — Minisforum officially lists Proxmox as a supported OS
- **BIOS settings required:**
  - Enable **SVM Mode** (AMD virtualization, equivalent to Intel VT-x)
  - Enable **IOMMU** (under AMD CBS > NBIO > NB Configuration)
  - Enable **ACS** if available (improves PCIe passthrough isolation)
  - Set boot to **UEFI only** (disable CSM/Legacy)
  - Disable **Secure Boot** for Proxmox installer
- **NIC drivers:** The 10GbE/5GbE NICs should have in-tree Linux kernel support — verify chipset after install with `lspci`
- **Power:** 45-55W makes this very efficient for a 24/7 hypervisor node

_Source: [Proxmox Forum - Mini PC discussion](https://forum.proxmox.com/threads/mini-pc-for-proxmox.117531/)_

---

### Track 2: OCULink + RX 9070 XT for Local LLM

#### OCULink Bandwidth Analysis

| Interface | Bandwidth | Lanes | Notes |
|-----------|-----------|-------|-------|
| **OCULink (N5 Pro / Deck 2)** | ~8 GB/s (64 Gbps) | PCIe 4.0 x4 | Best eGPU option |
| Thunderbolt 4 | ~5 GB/s (40 Gbps) | PCIe 3.0 x4 | Common but slower |
| Thunderbolt 5 | ~10 GB/s (80 Gbps) | PCIe 4.0 x4 | Newer, rare |
| Native PCIe x16 | ~32 GB/s (256 Gbps) | PCIe 4.0 x16 | Desktop standard |

**Impact on LLM inference:** The OCULink bandwidth penalty is **10-20% during model loading** but **negligible during inference**. Once a model is loaded into VRAM, only small token-sized data crosses the connection. The bottleneck is GPU memory bandwidth (640 GB/s on the 9070 XT), not the host-to-GPU link.

_Source: [egpu.io - eGPU LLM inference](https://egpu.io/forums/pro-applications/impact-of-egpu-connection-speed-on-local-llm-inference-in-multi-egpu-setups/), [LLM Speed Test](https://lilys.ai/notes/en/local-llm-20251213/external-gpu-pcie-llm-speed)_

#### AMD Radeon RX 9070 XT — AI/LLM Capabilities

| Attribute | Value |
|-----------|-------|
| **Architecture** | RDNA 4 (gfx1200/gfx1201) |
| **VRAM** | 16 GB GDDR6 |
| **Memory Bandwidth** | 640 GB/s |
| **TDP** | 304 W (requires adequate PSU in Deck 2 or external) |
| **PCIe** | 5.0 x16 native (runs at 4.0 x4 via OCULink) |
| **AI Throughput** | 2x per CU vs RDNA 3 |

#### ROCm Support Status (RDNA 4)

**Confirmed:** ROCm 7.x now supports RDNA 4 (gfx120X architecture) including the RX 9070 XT.

- Pre-built llama.cpp binaries with ROCm 7 are available — no separate ROCm installation required
- WMMA (Wave Matrix Multiply Accumulate) is implemented for RDNA 4 in ROCm 7, providing significant performance uplift over Vulkan for matrix operations
- Some performance optimization for matrix multiplication is still ongoing (active GitHub issues)
- The `HSA_OVERRIDE_GFX_VERSION=11.0.0` workaround is **no longer needed** with ROCm 7

_Source: [llama.cpp ROCm Discussion #15021](https://github.com/ggml-org/llama.cpp/discussions/15021), [llamacpp-rocm builds](https://github.com/lemonade-sdk/llamacpp-rocm), [ROCm LLMExt Compatibility](https://rocm.docs.amd.com/en/latest/compatibility/ml-compatibility/llama-cpp-compatibility.html)_

#### LLM Inference Benchmarks (RX 9070 XT)

| Model | Quantization | VRAM Usage | Tokens/sec (generation) | Fits in 16GB? |
|-------|-------------|------------|------------------------|---------------|
| Llama 3.2 1B | Q4_K_M | ~1.5 GB | ~163 tok/s | Yes |
| Llama 3.2 3B | Q3_K_L | ~2.5 GB | ~81 tok/s | Yes |
| Qwen 3 8B | Q4 | ~5 GB | 84-103 tok/s | Yes |
| Llama 3 8B | Q4_K_M | ~5 GB | ~80-95 tok/s (est.) | Yes |
| Mistral 7B | Q4_K_M | ~5 GB | ~80-95 tok/s (est.) | Yes |
| Qwen 2.5 14B | Q4_K_M | ~9 GB | ~40-55 tok/s (est.) | Yes |
| GPT-OSS 20B | MXFP4 | ~12 GB | 42-50 tok/s | Yes (tight) |
| Qwen 3 32B | Q4 (partial offload) | ~18 GB | 10-11 tok/s | No (needs CPU offload) |
| Llama 3 8B | FP16 | ~16 GB | ~50-60 tok/s (est.) | Borderline |

**Sweet spot:** 7B-14B parameter models at Q4 quantization. Comfortably runs dual 7B models or a single 14B model with headroom.

#### Target Model: Gemma 4 26B-A4B (MoE)

Gemma 4 26B is a **Mixture of Experts** model: 25.8B total parameters but only **3.8B active per token**. This means it delivers reasoning quality close to a dense 31B model while being much faster — but the full weights still need to sit in VRAM.

| Quantization | Model File Size | VRAM Needed | Fits RX 9070 XT (16GB)? | Quality |
|-------------|----------------|-------------|--------------------------|---------|
| **IQ4_XS** (Importance Matrix) | ~14 GB | ~15 GB | **Yes** — ~1GB headroom for KV cache | Very good |
| **Q3_K_M** | ~13-14 GB | ~14 GB | **Yes** — best balance for 16GB | Good (min viable for MoE routing) |
| **Q4_K_M** (Ollama default) | ~18 GB | ~16.5 GB | **Borderline** — may OOM with longer context | Best |
| **Q8_0** | ~28.5 GB | ~28.5 GB | No | Excellent |

**Chosen approach for 16GB VRAM: Q3_K_M**

Q3_K_M is the minimum viable quantization that preserves MoE routing integrity, fits comfortably in 16GB with ~2GB headroom for KV cache, and is available as a verified GGUF from Hugging Face.

```bash
# Primary: Q3_K_M via Hugging Face GGUF (recommended)
ollama run hf.co/DuoNeural/Gemma-4-26B-A4B-it-GGUF:Q3_K_M

# Alternative: IQ4_XS community model (slightly larger, slightly better quality)
ollama run VladimirGav/gemma4-26b-16GB-VRAM

# If Q4 is needed later: partial CPU offload via llama.cpp
# -ngl 999 -ot "exps=CPU" keeps expert layers on CPU while routing on GPU
```

**For testing with a smaller model first:**

| Model | Command | VRAM | Speed (est.) |
|-------|---------|------|-------------|
| **Gemma 4 E4B** (4B, dense) | `ollama run gemma4:e4b` | ~3 GB | Very fast (~100+ tok/s) |
| **Gemma 4 E2B** (2B, dense) | `ollama run gemma4:e2b` | ~2 GB | Fastest (~150+ tok/s) |
| **Qwen 3 8B** (Q4) | `ollama run qwen3:8b` | ~5 GB | ~84-103 tok/s |

Start with `gemma4:e4b` to validate the full pipeline (GPU detection, Vulkan, Ollama), then move to `gemma4:26b` with IQ4_XS.

_Source: [Ollama gemma4:26b](https://ollama.com/library/gemma4:26b), [VladimirGav/gemma4-26b-16GB-VRAM](https://ollama.com/VladimirGav/gemma4-26b-16GB-VRAM), [Gemma 4 VRAM Guide](https://www.gemma4.wiki/guide/gemma-4-model-sizes-vram-requirements), [AMD Day 0 Gemma 4 Support](https://www.amd.com/en/developer/resources/technical-articles/2026/day-0-support-for-gemma-4-on-amd-processors-and-gpus.html)_

_Source: [LocalScore RX 9070 XT](https://www.localscore.ai/accelerator/585), [TechReviewer RX 9070 XT for LLMs](https://www.techreviewer.com/tech-specs/amd-rx-9070-xt-gpu-for-llms/)_

#### Recommended Software Stack

| Tool | Backend | Why |
|------|---------|-----|
| **llama.cpp** (ROCm/HIP) | ROCm 7 | Best performance on RDNA 4 with WMMA support |
| **llama.cpp** (Vulkan) | Vulkan | Fallback if ROCm issues arise; no driver dependency |
| **Ollama** | Wraps llama.cpp | Easiest UX, model management, API server |
| **Open WebUI** | Web frontend | Chat interface for Ollama, self-hosted |
| **kobold.cpp** | Vulkan/ROCm | Alternative with good AMD support |

**Avoid for now:** vLLM and PyTorch directly — ROCm 7 RDNA 4 support is still maturing for these frameworks. Stick with llama.cpp-based tools.

#### ROCm vs Vulkan: Head-to-Head on RDNA 4

This is a critical decision. Both backends now work on RDNA 4, but they are **not equal**.

**Benchmark data: RX 9070 XT — Llama 2 7B Q4_0 (llama-bench)**

| Metric | Vulkan (RADV) | ROCm 7 (HIP) | Winner |
|--------|--------------|---------------|--------|
| **Prompt processing (pp512)** | ~5,036 t/s | ~1,520 t/s | **Vulkan (3.3x faster)** |
| **Text generation (tg128)** | ~137 t/s | ~92 t/s | **Vulkan (1.5x faster)** |

_Note: ROCm numbers are from Radeon AI PRO R9700 (same RDNA 4 arch, lower clocks). RX 9070 XT ROCm may be slightly higher but the ratio holds._

**Broader findings (RDNA 4 architecture):**

| Source | Finding |
|--------|---------|
| Phoronix (ROCm 7.1 vs Vulkan, R9700) | Vulkan matched or beat ROCm in most tests |
| llama.cpp Discussion #19890 | Vulkan ~183 t/s vs ROCm ~150 t/s decode (Qwen 35B MoE) |
| ROCm GitHub Issue #4883 | "llama.cpp Vulkan outperforms ROCm backend" on RDNA 4 |
| Community reports | "Vulkan is anywhere from at least as fast to 50% faster than ROCm" on RDNA 4 |

**Why Vulkan wins on RDNA 4:**
- Vulkan uses **KHR_cooperative_matrix** extension to access RDNA 4 matrix cores directly
- The RADV Mesa driver has excellent, well-tested RDNA 4 support
- ROCm 7 added WMMA for RDNA 4 but the compiler optimizations are still maturing
- ROCm has known performance issues with matrix multiplication on 9070 XT (GitHub ROCm/ROCm#5727)

**Verdict: Use Vulkan on RDNA 4 (RX 9070 XT)**

| Factor | Vulkan | ROCm 7 |
|--------|--------|--------|
| **Performance** | Faster (1.5-3x on RDNA 4) | Slower, still optimizing |
| **Setup complexity** | Zero — works with Mesa drivers | Requires ROCm 7 install (~2GB) |
| **Ollama support** | Experimental (`OLLAMA_VULKAN=1`) | Official (ROCm tarball) |
| **llama.cpp support** | Full, stable | Full, stable |
| **Driver requirement** | Mesa RADV (ships with Linux) | ROCm 7 (separate install) |
| **LXC passthrough** | `/dev/dri/*` only | `/dev/dri/*` + `/dev/kfd` |
| **Multi-container GPU sharing** | Works | Works |
| **Maturity on RDNA 4** | Mature (Mesa RADV) | Maturing (ROCm 7 is new) |

**Practical recommendation:**

1. **Start with Vulkan via llama.cpp directly** — fastest, simplest, no ROCm dependency
2. **For Ollama:** Set `OLLAMA_VULKAN=1` (experimental but working on RDNA 4)
3. **Fallback to ROCm** only if you hit a Vulkan-specific bug or need PyTorch later
4. **Re-evaluate in 6 months** — ROCm compiler optimizations for RDNA 4 are actively being developed

_Source: [llama.cpp Vulkan Discussion #10879](https://github.com/ggml-org/llama.cpp/discussions/10879), [Phoronix ROCm 7.1 vs Vulkan](https://www.phoronix.com/review/rocm-71-llama-cpp-vulkan), [ROCm Issue #4883](https://github.com/ROCm/ROCm/issues/4883), [llama.cpp Discussion #19890](https://github.com/ggml-org/llama.cpp/discussions/19890), [Ollama Vulkan](https://www.phoronix.com/news/ollama-Experimental-Vulkan)_

#### Power Considerations for Deck 2

The RX 9070 XT has a 304W TDP. The Minisforum Deck 2 eGPU dock needs to supply adequate power. Verify:
- Deck 2 PSU wattage (must exceed 304W + overhead)
- Adequate cooling in the dock enclosure
- Connect GPU before powering on (hot-plug is unreliable)

---

### Track 3: Adding PVE3 to the Proxmox Cluster

#### Quorum Improvement (Critical Benefit)

| Nodes | Expected Votes | Quorum | Fault Tolerance |
|-------|---------------|--------|-----------------|
| 2 (current) | 2 | 2 | **None** — both must be up |
| 3 (with pve3) | 3 | 2 | **1 node can fail** — real HA |

This is the single biggest operational improvement. With 3 nodes you get actual high availability — the cluster survives one node going down.

_Source: [Proxmox Cluster Manager Wiki](https://pve.proxmox.com/wiki/Cluster_Manager), [Proxmox 2-Node HA Wiki](https://pve.proxmox.com/wiki/Two-Node_High_Availability_Cluster)_

#### Current Cluster State (Live)

```
Cluster: home-cluster
Nodes: 2 (pve1: 192.168.50.201, pve2: 192.168.50.202)
Transport: knet, secauth: on
Quorum: Yes (2/2 votes)
Corosync config version: 4
```

#### Pre-requisites Checklist

- [ ] Fresh Proxmox VE 8.4 install on pve3 — **same version as pve1/pve2** (`pveversion` must match)
- [ ] Unique hostname: `pve3`
- [ ] Static IP: `192.168.50.203` (logical next in sequence)
- [ ] NTP synchronized (`timedatectl status`)
- [ ] **No VMs or containers created** on pve3 before joining
- [ ] `/etc/hosts` updated on **all three nodes**:
  ```
  192.168.50.201  pve1
  192.168.50.202  pve2
  192.168.50.203  pve3
  ```
- [ ] Root SSH access between nodes
- [ ] Firewall ports open between all nodes:

| Port | Protocol | Purpose |
|------|----------|---------|
| 22 | TCP | SSH |
| 8006 | TCP | Proxmox Web API |
| 5405-5412 | UDP | Corosync/knet |
| 60000-60050 | TCP | Live migration |

#### Step-by-Step Join Procedure

```bash
# 1. On pve3 — verify clean state
pvecm status          # Should show "not in a cluster"
pct list && qm list   # Must be empty

# 2. On pve3 — join the existing cluster
pvecm add 192.168.50.201
# Enter pve1 root password when prompted
# Accept SSH fingerprint: yes
# Corosync config + auth keys are copied automatically

# 3. On any node — verify cluster
pvecm status
# Expect: Nodes: 3, Quorate: Yes, Total votes: 3, Quorum: 2

# 4. Verify in Proxmox web UI
# Navigate to Datacenter > Cluster — all 3 nodes should appear

# 5. Test HA (optional, requires shared storage for online migration)
ha-manager status
```

#### Post-Join: Infrastructure Integration

**Ansible inventory** (`homelab-infra/ansible/inventories/homelab/hosts.ini`) — add pve3:
```ini
[proxmox_hosts]
pve1 ansible_host=192.168.50.201 ansible_user=root ansible_ssh_private_key_file=~/.ssh/homelab_ed25519
pve2 ansible_host=192.168.50.202 ansible_user=root ansible_ssh_private_key_file=~/.ssh/homelab_ed25519
pve3 ansible_host=192.168.50.203 ansible_user=root ansible_ssh_private_key_file=~/.ssh/homelab_ed25519
```

**Ansible host tuning** — apply existing `pve-host.yml` playbook to pve3:
```bash
ansible-playbook -i inventories/homelab/hosts.ini playbooks/pve-host.yml --limit pve3
```
This will auto-detect the physical NIC on pve3 and apply ring buffer tuning (RX/TX 4096).

**Terraform** — add pve3 as a target node for new containers in `terraform/envs/homelab/`

**Prometheus monitoring** — any containers on pve3 with `monitoring_enabled=true` will be auto-discovered via `file_sd_configs` after `terraform apply`

**Documentation** — update `docs/architecture-homelab-infra.md`:
- Add pve3 to the network diagram
- Add pve3 specs to the Infrastructure Resources section
- Update corosync config documentation

#### Common Pitfalls

1. **Hostname resolution** — if `/etc/hosts` is incomplete on any node, corosync fails silently
2. **Time drift** — >2s skew causes corosync token timeouts
3. **PVE version mismatch** — mixed versions cause API and replication issues; run `apt update && apt dist-upgrade` on pve1/pve2 first if needed
4. **Existing VMs on new node** — `pvecm add` will refuse or corrupt config if containers/VMs exist
5. **Storage** — pve3 has local storage only; live migration between nodes requires shared storage (NFS, Ceph, iSCSI). Offline migration (copies disk) works without shared storage.

#### Storage Considerations

The N5 Pro has 5x 3.5" HDD bays + M.2 slots. Options for shared storage:
- **NFS share** from pve3 (simplest — mount on pve1/pve2 as shared storage)
- **Ceph** (3 nodes is the minimum for Ceph — now viable with pve3)
- Keep local-only for now and use offline migration

---

## Summary of Key Findings

### Immediate Action: Add N5 Pro as PVE3
1. Install Proxmox VE 8.4 on the N5 Pro
2. Configure BIOS (SVM, IOMMU, UEFI-only)
3. Set static IP 192.168.50.203, hostname `pve3`
4. Update `/etc/hosts` on all 3 nodes
5. Run `pvecm add 192.168.50.201` from pve3
6. Update Ansible inventory and run `pve-host.yml`

### Future Action: OCULink + RX 9070 XT for LLM
1. The N5 Pro has OCULink — you can connect the GPU directly (no need for the Deck 2 if preferred)
2. ROCm 7 now supports RDNA 4; use llama.cpp with ROCm/HIP backend
3. Sweet spot: 7B-14B Q4 models at 80-100+ tok/s
4. GPU passthrough through Proxmox VFIO is viable; test IOMMU grouping
5. Consider Ollama + Open WebUI for a self-hosted ChatGPT-like interface

---

## Track 4: Proxmox Installation on the N5 Pro

### Important: The N5 Pro Ships with MinisCloud OS

The N5 Pro comes pre-installed with **MinisCloud OS** on a built-in 128 GB SSD. This is Minisforum's proprietary NAS operating system. To install Proxmox, you will **wipe this and install Proxmox on an M.2 NVMe drive**.

### What You Need

| Item | Detail |
|------|--------|
| **USB flash drive** | 8 GB+, for Proxmox installer |
| **M.2 NVMe SSD** | Install target — 256 GB minimum recommended (matches pve1/pve2 style) |
| **Keyboard + monitor** | HDMI for initial setup; not needed after |
| **Ethernet cable** | Connect to your 192.168.50.0/24 network |
| **Another PC** | To flash the Proxmox ISO to USB |

### Step 0: Prepare Installation Media

```bash
# Download Proxmox VE ISO (match your pve1/pve2 version)
# Check current version:
ssh pve1 'pveversion'
# Download matching ISO from https://www.proxmox.com/en/downloads

# Flash to USB (Linux/Mac):
dd bs=1M conv=fdatasync if=proxmox-ve_8.4-1.iso of=/dev/sdX status=progress
# Or use Ventoy / Rufus / balenaEtcher on Windows
```

**Known issue:** PVE 9 had a kernel panic (`Unable to mount root fs`) on the N5 Pro related to the boot method of the installation media. If you encounter this, use **Rufus in DD mode** (not ISO mode) or use `dd` directly. PVE 8.x installs cleanly.

_Source: [Proxmox Forum - N5 Pro can't boot with PVE9](https://forum.proxmox.com/threads/minisforums-nas-n5-pro-cant-boot-with-pve9.169753/)_

### Step 1: BIOS Configuration

Power on the N5 Pro and press **Delete** key to enter BIOS.

**Required settings:**

| Setting | Navigation Path | Value |
|---------|----------------|-------|
| **SVM Mode** | Advanced > CPU Configuration | **Enabled** |
| **IOMMU** | Advanced > AMD CBS > NBIO Common Options | **Enabled** |
| **ACS Enable** | Advanced > AMD CBS > NBIO Common Options (if present) | **Enabled** |
| **iGPU Configuration** | Advanced > AMD CBS > NBIO Common Options > GFX Configuration | `UMA_SPECIFIED` |
| **UMA Frame buffer** | Same submenu | `8G` (or `16G` if planning heavy transcoding) |
| **ReBAR** | Same submenu | **Enabled** |
| **Secure Boot** | Security / Boot | **Disabled** |
| **Boot Mode** | Boot | **UEFI only** (disable CSM/Legacy) |
| **Boot Order** | Boot | **USB first** (for installation) |

_Source: [naut.ca - N5 Pro iGPU Passthrough](https://www.naut.ca/blog/2025/11/20/minisforum-n5-pro-nas-igpu-passthrough/)_

### Step 2: Install Proxmox VE

1. Insert USB installer, boot from USB
2. If the graphical installer fails (black screen / hang), select **"Install Proxmox VE (Console Mode - nomodeset)"** from the advanced boot options
3. **Target disk:** Select the M.2 NVMe SSD (not the built-in 128 GB SSD unless you want to repurpose it)
4. **Filesystem:** Choose **ext4 (LVM)** to match pve1 and pve2 — this keeps your cluster consistent
5. **Options button** (on disk selection screen):
   - `hdsize`: Leave default (use full NVMe) or limit if you want to partition later
   - `swapsize`: 8 GB (matches pve1/pve2)
   - `maxroot`: 96 GB (matches pve1/pve2)
   - The rest becomes LVM thin pool for VM/CT storage
6. **Country/Timezone:** Your locale
7. **Root password:** Set a strong password
8. **Network configuration:**
   - **Management interface:** Select the 10GbE NIC if available (or whichever NIC is connected)
   - **Hostname:** `pve3.home-cluster`
   - **IP:** `192.168.50.203/24`
   - **Gateway:** `192.168.50.1`
   - **DNS:** `192.168.50.194` (your Pi-hole) or `192.168.50.1`
9. **Install** and wait for completion
10. Remove USB, reboot

### Step 3: Post-Install Verification

After reboot, the Proxmox web UI should be available at `https://192.168.50.203:8006`.

```bash
# SSH into pve3
ssh root@192.168.50.203

# Verify Proxmox version (must match pve1/pve2)
pveversion

# Verify CPU and RAM
lscpu | head -20
free -h

# Verify storage
lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT

# Verify networking
ip addr show
# Check which NICs are available:
lspci | grep -i ethernet

# Verify IOMMU is enabled
dmesg | grep -i iommu
# Should show: "AMD-Vi: IOMMU performance counters supported"

# Verify virtualization
dmesg | grep -i svm
# Should show SVM enabled
```

### Step 4: Kernel Parameters (for GPU passthrough readiness)

Even though the GPU isn't being connected yet, configure IOMMU and module blacklisting now so it's ready:

```bash
# Edit GRUB
nano /etc/default/grub

# Change GRUB_CMDLINE_LINUX_DEFAULT to:
GRUB_CMDLINE_LINUX_DEFAULT="quiet amd_iommu=on iommu=pt"

# Update GRUB
update-grub

# (Optional, for future GPU passthrough) Blacklist amdgpu to prevent host from claiming the dGPU
echo "blacklist amdgpu" > /etc/modprobe.d/blacklist-amdgpu.conf

# Load VFIO modules
echo "vfio" >> /etc/modules
echo "vfio_iommu_type1" >> /etc/modules
echo "vfio_pci" >> /etc/modules

# Update initramfs
update-initramfs -u -k all

# Reboot
reboot
```

### Step 5: Configure /etc/hosts (on ALL nodes)

```bash
# On pve3:
cat >> /etc/hosts << 'EOF'
192.168.50.201  pve1
192.168.50.202  pve2
192.168.50.203  pve3
EOF

# On pve1:
ssh pve1 'echo "192.168.50.203  pve3" >> /etc/hosts'

# On pve2:
ssh pve2 'echo "192.168.50.203  pve3" >> /etc/hosts'
```

### Step 6: NTP Synchronization

```bash
# On pve3 — verify time sync
timedatectl status
# If not synchronized:
systemctl enable --now systemd-timesyncd
timedatectl set-ntp true
```

### Step 7: Join the Cluster

```bash
# On pve3 — verify clean state
pvecm status        # Should show "not in a cluster"
pct list && qm list # Must be empty

# Join the cluster
pvecm add 192.168.50.201
# Enter pve1 root password when prompted
# Accept SSH fingerprint: yes
```

### Step 8: Verify Cluster

```bash
# On any node:
pvecm status
# Expect:
#   Nodes: 3
#   Quorate: Yes
#   Total votes: 3
#   Quorum: 2

# Check all nodes visible
pvesh get /nodes --output-format json-pretty
```

### Step 9: Post-Join Infrastructure Integration

See Track 3 section above for:
- Ansible inventory update (add pve3 to `[proxmox_hosts]`)
- Run `pve-host.yml` playbook for NIC tuning
- Terraform integration for new containers
- Prometheus monitoring auto-discovery

### Disk Layout: What Goes Where

The N5 Pro has multiple storage options. Recommended layout:

| Slot | Use | Purpose |
|------|-----|---------|
| **M.2 slot 1** | NVMe SSD (256GB+) | Proxmox boot + local-lvm (VM/CT storage) |
| **M.2 slot 2** (optional) | NVMe SSD | Fast VM storage or ZFS mirror with slot 1 |
| **M.2 slot 3** (optional) | NVMe SSD | Additional fast storage |
| **5x 3.5" HDD bays** | HDDs | Bulk storage, NFS shares, or future Ceph OSD |
| **Built-in 128GB SSD** | Repurpose or ignore | Could use for PBS (Proxmox Backup Server) |

### Consistency with Existing Nodes

Your pve1 and pve2 both use:
- **ext4 on LVM** (not ZFS)
- ~96 GB root partition
- 8 GB swap
- Remaining space as LVM thin pool (`pve-data`)

Keep pve3 the same for operational consistency.

---

## Integration Patterns Analysis

### Proxmox Cluster Integration Points

Adding pve3 touches multiple systems in your IaC pipeline. Here's every integration point:

| System | File/Config | Change Required |
|--------|-------------|-----------------|
| **Ansible inventory** | `ansible/inventories/homelab/hosts.ini` | Add `pve3` to `[proxmox_hosts]` |
| **Ansible hosts template** | `ansible/templates/hosts.ini.j2` | Add pve3 variable if templated |
| **Ansible pve-host playbook** | `ansible/playbooks/pve-host.yml` | Already targets `[proxmox_hosts]` — works automatically |
| **Terraform provider** | `terraform/envs/homelab/main.tf` | Add pve3 as available `target_node` for resources |
| **Terraform variables** | `terraform/envs/homelab/variables.tf` | Add pve3 node definition |
| **Corosync** | `/etc/pve/corosync.conf` | Auto-updated by `pvecm add` |
| **SSH config** | `~/.ssh/config` (control machine) | Add `pve3` alias |
| **DNS** | Pi-hole custom list (or `/etc/hosts`) | Add `pve3 192.168.50.203` |
| **Prometheus** | Auto-discovery via `file_sd_configs` | New containers auto-registered after `terraform apply` |
| **Grafana** | Storage Overview dashboard | Auto-picks up new node-exporter targets |
| **Documentation** | `docs/architecture-homelab-infra.md` | Update network diagram, node table |
| **NIC tuning** | `pve-host.yml` role | Auto-detects NIC and applies ring buffer tuning |

_Source: Live inspection of homelab-infra repo structure_

### GPU Passthrough Integration: VM vs LXC

For running Ollama/LLM workloads, there are two approaches. **LXC is strongly recommended** for this use case:

| Aspect | VM (VFIO passthrough) | LXC (device passthrough) |
|--------|----------------------|--------------------------|
| **GPU access** | Exclusive — entire card locked to one VM | Shared — multiple containers can use same GPU |
| **Performance** | Near-native | Near-native (no virtualization overhead) |
| **Memory overhead** | Full VM memory allocation | Shares host kernel, minimal overhead |
| **Setup complexity** | High (VFIO, ROM files, UEFI) | Low (3 device nodes + cgroup permissions) |
| **Hot-plug** | No (must boot with GPU) | Device can be added to running container |
| **Driver management** | Guest installs own drivers | Host driver shared via bind mounts |
| **Live migration** | Not possible with GPU attached | Not possible with GPU attached |
| **Best for** | Windows guests, dedicated GPU use | Linux services (Ollama, Plex transcoding) |

**Recommendation:** Run Ollama in a **privileged LXC container** with AMD GPU device passthrough. This matches your existing pattern (ct-media-01 is already privileged for GPU).

_Source: [XDA - Ollama Proxmox LXC AMD GPU](https://www.xda-developers.com/self-hosted-ollama-proxmox-lxc-uses-amd-gpu/), [XDA - GPU passthrough to LXCs](https://www.xda-developers.com/gpu-passthrough-to-lxcs-beats-vms/)_

### AMD GPU LXC Device Configuration

When the OCULink GPU is connected, pass these device nodes to the LXC container:

```bash
# In /etc/pve/lxc/<VMID>.conf:
lxc.cgroup2.devices.allow: c 226:* rwm    # DRI devices (required for Vulkan + ROCm)
lxc.mount.entry: /dev/dri dev/dri none bind,optional,create=dir

# Only needed if using ROCm backend (not needed for Vulkan):
lxc.cgroup2.devices.allow: c 234:* rwm    # KFD (ROCm compute)
lxc.mount.entry: /dev/kfd dev/kfd none bind,optional,create=file

# Or via Proxmox GUI: Resources → Device passthrough
# /dev/dri/card0 — mode 0666 (always needed)
# /dev/dri/renderD128 — mode 0666 (always needed)
# /dev/kfd — mode 0666 (only for ROCm)
```

Inside the container, install Ollama with Vulkan (recommended for RDNA 4):
```bash
# Standard Ollama install (Vulkan support included)
curl -fsSL https://ollama.com/install.sh | sh

# Enable Vulkan backend
echo 'OLLAMA_VULKAN=1' >> /etc/environment

# Alternative: ROCm-enabled Ollama (if you prefer ROCm)
# curl -L https://ollama.com/download/ollama-linux-amd64-rocm.tgz -o ollama-rocm.tgz
# sudo tar -C /usr -xzf ollama-rocm.tgz
```

_Source: [XDA - Self-hosted Ollama Proxmox LXC AMD GPU](https://www.xda-developers.com/self-hosted-ollama-proxmox-lxc-uses-amd-gpu/)_

### Shared Storage Options (3-Node Cluster)

With 3 nodes, new shared storage options become available:

| Option | Complexity | Performance | Redundancy | Best For |
|--------|-----------|-------------|------------|----------|
| **Local only** (current) | None | Best | None | Current setup — offline migration only |
| **NFS from pve3** | Low | Good | SPOF (pve3) | Quick shared storage for ISOs + backups |
| **ZFS replication** | Medium | Good | Per-schedule | HA without shared storage; replicate VMs to another node |
| **Ceph (3-node)** | High | Variable | 3x replication | Full HA with live migration; 1/3 usable capacity |

**Recommendation for now:** Start with **local storage only** (matches pve1/pve2). Use **NFS from pve3** for ISO sharing and Proxmox Backup Server if needed. The N5 Pro's 5x HDD bays make it a natural NFS host. Consider Ceph later if you need live migration between all nodes.

_Source: [Proxmox Forum - Best storage for 3-node cluster](https://forum.proxmox.com/threads/best-storage-solution-for-a-3-node-cluster-in-a-homelab.92203/), [SelfHostWise - Proxmox Storage Options](https://selfhostwise.com/posts/proxmox-ve-storage-options-zfs-lvm-thin-ceph-and-nfs-compared/)_

---

## Architectural Patterns and Design

### Target Architecture: 3-Node Cluster with AI Capability

```
Internet ─── Telenet CV8560E (bridge) ─── ASUS RT-AX88U (.1)
                                               │
                                     AiMesh (4x RT-AX92U)
                                               │
             ┌─────────────────────────────────┼────────────────────────────────┐
             │                                 │                                │
        pve1 (.201)                     pve2 (.202)                      pve3 (.203)
        i3-N305 / 46GB                 N200 / 46GB                   Ryzen AI 9 / 96GB
        466GB NVMe                     932GB NVMe                    NVMe + 5x HDD
        2.5GbE                         2.5GbE                        10GbE + 5GbE
             │                              │                              │
     ┌───────┴───────┐            ┌─────────┴────────┐           ┌────────┴────────┐
     │ ct-docker-01  │            │ ct-dev-homelab   │           │ ct-ai-01 (new)  │
     │ (.194)        │            │ (.150)           │           │ (.20x)          │
     │ Core infra    │            │ Development      │           │ Ollama + WebUI  │
     ├───────────────┤            ├──────────────────┤           │ GPU: RX 9070 XT │
     │ ct-media-01   │            │ ct-sparkle-cps   │           │ via OCULink     │
     │ (.161)        │            │ (.151)           │           └─────────────────┘
     │ Media + GPU   │            │ CPS-Fabric       │
     ├───────────────┤            ├──────────────────┤
     │ ct-zeroclaw   │            │ ct-dev-test      │
     │ (.104)        │            │ (.152)           │
     └───────────────┘            └──────────────────┘
```

### Node Role Assignment

| Node | Role | Rationale |
|------|------|-----------|
| **pve1** | Core infrastructure + Media | Existing workloads, stable, don't move |
| **pve2** | Development + CI/CD | Dev containers, test environments |
| **pve3** | AI/ML + Storage | Most powerful CPU, most RAM, GPU via OCULink, HDD bays for bulk storage |

### OCULink Architecture Decision: N5 Pro vs Deck 2

The N5 Pro **has its own OCULink port**. This means you have two options for connecting the RX 9070 XT:

| Option | Setup | Pros | Cons |
|--------|-------|------|------|
| **A: N5 Pro + OCULink directly** | GPU docked to N5 Pro | Single device, simpler, GPU available to Proxmox VMs/LXC directly | GPU tied to one node |
| **B: Deck 2 as separate device** | Deck 2 runs standalone (bare metal or its own Proxmox) | Deck 2 can be used independently, hot-swap between systems | Extra device to manage, networking overhead |

**Recommendation:** Option A — connect the RX 9070 XT directly to the N5 Pro's OCULink. This gives the GPU direct PCIe access through Proxmox, allowing clean passthrough to an LXC container running Ollama. The Deck 2 can be reserved for future use or as a portable AI workstation.

### LLM Service Architecture

```
┌─────────────── pve3 (N5 Pro) ──────────────────┐
│                                                  │
│  Host: Proxmox VE 8.4                           │
│  ├── IOMMU enabled (amd_iommu=on iommu=pt)     │
│  ├── /dev/dri/card0, /dev/dri/renderD128        │
│  └── /dev/kfd (ROCm compute)                    │
│                                                  │
│  ┌──── ct-ai-01 (LXC, privileged) ────────┐    │
│  │                                          │    │
│  │  Ollama (ROCm 7 / llama.cpp backend)    │    │
│  │  ├── API: http://192.168.50.20x:11434   │    │
│  │  ├── Models: /opt/appdata/ollama/models  │    │
│  │  └── GPU: RX 9070 XT via device pass    │    │
│  │                                          │    │
│  │  Open WebUI (Docker)                     │    │
│  │  ├── Web: http://192.168.50.20x:3000    │    │
│  │  └── Connects to Ollama API             │    │
│  │                                          │    │
│  └──────────────────────────────────────────┘    │
│                                                  │
│  ┌──── Other containers (future) ──────────┐    │
│  │  NFS server (5x HDD bays)              │    │
│  │  Proxmox Backup Server                  │    │
│  └──────────────────────────────────────────┘    │
└──────────────────────────────────────────────────┘
```

### Terraform Integration for PVE3

Your existing Terraform setup uses the `telmate/proxmox` provider. To deploy containers on pve3:

```hcl
# In terraform/envs/homelab/ — add pve3 as target node
module "ct-ai-01" {
  source       = "../../modules/ct-debian"
  hostname     = "ct-ai-01"
  target_node  = "pve3"
  vmid         = 160
  cores        = 8
  memory       = 32768
  disk_size    = "50G"
  ip_address   = "192.168.50.160"
  gateway      = "192.168.50.1"
  # ... standard ct-debian parameters
  monitoring_enabled = true
}
```

Note: GPU passthrough configuration (LXC device entries) is not managed by the Terraform `proxmox_lxc` resource — it needs to be applied via Ansible or manual config after container creation.

_Source: [VanMieghem - Automating Proxmox with Terraform and Ansible](https://vanmieghem.io/automating-proxmox-with-terraform-ansible/), [Virtualization Howto - OCULink eGPU Proxmox](https://www.virtualizationhowto.com/2026/03/i-added-an-egpu-to-my-proxmox-mini-pc-home-lab-using-oculink-heres-what-happened/)_

### Security Considerations

| Area | Recommendation |
|------|---------------|
| **Privileged LXC** | Required for GPU passthrough; isolate to AI workloads only |
| **Network** | Place AI container on same VLAN as other services; restrict Ollama API access |
| **Model storage** | Local to pve3 (NVMe for speed); no secrets in model files |
| **API exposure** | Ollama API (port 11434) should not be exposed to WAN; Traefik + Authelia if needed |
| **GPU device permissions** | Mode 0666 is broad; acceptable in homelab, but monitor for production |

---

## Implementation Roadmap

### Phase 1: Proxmox on N5 Pro (Day 1)

| Step | Action | Time Est. |
|------|--------|-----------|
| 1.1 | Flash Proxmox VE 8.4 ISO to USB (use `dd` or Rufus DD mode) | 10 min |
| 1.2 | Configure BIOS: SVM, IOMMU, ACS, UMA 8G, UEFI-only, Secure Boot off | 10 min |
| 1.3 | Install Proxmox on M.2 NVMe (ext4/LVM, 96GB root, 8GB swap) | 15 min |
| 1.4 | Set hostname `pve3`, IP `192.168.50.203`, gateway `.1`, DNS `.194` | During install |
| 1.5 | Post-install: verify with `pveversion`, `lscpu`, `dmesg \| grep iommu` | 5 min |
| 1.6 | Set kernel params: `amd_iommu=on iommu=pt` in GRUB, `update-grub`, reboot | 5 min |

### Phase 2: Join Cluster (Day 1)

| Step | Action | Time Est. |
|------|--------|-----------|
| 2.1 | Update `/etc/hosts` on pve1, pve2, and pve3 (all three) | 5 min |
| 2.2 | Verify NTP sync on pve3: `timedatectl status` | 2 min |
| 2.3 | From pve3: `pvecm add 192.168.50.201` | 2 min |
| 2.4 | Verify: `pvecm status` shows 3 nodes, quorum=2 | 2 min |
| 2.5 | Check Proxmox web UI: all 3 nodes visible in Datacenter > Cluster | 1 min |

### Phase 3: Infrastructure Integration (Day 1-2)

| Step | Action | Time Est. |
|------|--------|-----------|
| 3.1 | Add pve3 to Ansible `hosts.ini` under `[proxmox_hosts]` | 5 min |
| 3.2 | Add `pve3` SSH alias to control machine `~/.ssh/config` | 2 min |
| 3.3 | Run `ansible-playbook pve-host.yml --limit pve3` (NIC tuning) | 5 min |
| 3.4 | Add pve3 DNS entry to Pi-hole custom list | 2 min |
| 3.5 | Update `docs/architecture-homelab-infra.md` | 15 min |
| 3.6 | Update Terraform to support `target_node = "pve3"` | 10 min |

### Phase 4: AI Container Setup (Day 2-3, when ready for GPU)

| Step | Action | Time Est. |
|------|--------|-----------|
| 4.1 | Connect RX 9070 XT to N5 Pro OCULink port (GPU dock powered on before boot) | 10 min |
| 4.2 | Verify GPU detection: `lspci \| grep -i vga` on pve3 host | 2 min |
| 4.3 | Check IOMMU groups: `find /sys/kernel/iommu_groups/ -type l` | 5 min |
| 4.4 | Create privileged LXC container `ct-ai-01` (8 cores, 32GB RAM, 50GB disk) | 5 min |
| 4.5 | Add GPU device passthrough to LXC config (`/dev/dri/*`, optionally `/dev/kfd`) | 5 min |
| 4.6 | Inside container: install Ollama, set `OLLAMA_VULKAN=1` | 10 min |
| 4.7 | Install Open WebUI via Docker inside the LXC | 10 min |
| 4.8 | **Test model:** `ollama run gemma4:e4b` (small, validates full pipeline) | 5 min |
| 4.9 | Verify GPU is used: `ollama ps` should show GPU layers, not CPU-only | 2 min |
| 4.10 | **Target model:** `ollama run hf.co/DuoNeural/Gemma-4-26B-A4B-it-GGUF:Q3_K_M` (~14GB, fits in 16GB with headroom) | 10 min |
| 4.11 | Test Gemma 4 26B inference and verify VRAM usage stays under 16GB | 5 min |

**Total estimated time: ~3-4 hours across 2-3 sessions**

_Source: [Digital Spaceport - Ollama + OWUI Proxmox LXC Guide](https://digitalspaceport.com/how-to-setup-an-ai-server-homelab-beginners-guides-ollama-and-openwebui-on-proxmox-lxc/), [Scottymarch - Ollama Open WebUI Proxmox](https://scottymarch.com/complete-guide-setting-up-ollama-and-open-webui-with-gpu-passthrough-on-proxmox/)_

---

## Risk Assessment and Mitigation

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| **PVE9 boot issue on N5 Pro** | Medium | Known | Use PVE 8.4; flash USB with `dd` (DD mode), not ISO mode. Use console/nomodeset if graphical installer hangs. |
| **IOMMU grouping issues with OCULink** | Medium | Possible | Check groups after install. If GPU shares a group with other devices, apply ACS override patch. Connect GPU before boot. |
| **NIC driver instability** | Low | Possible | The N5 Pro uses 10GbE + 5GbE (not Realtek 2.5GbE). Verify chipset with `lspci` post-install; likely has in-tree support. |
| **PVE version mismatch** | High | Low | Run `pveversion` on all nodes before joining. Update pve1/pve2 if needed: `apt update && apt dist-upgrade`. |
| **Corosync split-brain** | High | Low | Ensure `/etc/hosts` is complete on all 3 nodes. Verify NTP. Open UDP 5405-5412. |
| **RX 9070 XT power in dock** | Medium | Low | Verify Deck 2 / eGPU dock PSU handles 304W TDP + overhead. If using N5 Pro OCULink directly, ensure adequate external PSU. |
| **Ollama Vulkan experimental** | Low | Medium | Vulkan works but is marked experimental. Fallback: install ROCm tarball. Both paths verified working on RDNA 4. |
| **GPU hot-plug failure** | Medium | Known | Always connect and power GPU before booting pve3. Hot-plug is unreliable for PCIe passthrough. |

---

## Cost and Power Analysis

### Power Budget

| Component | Idle | Load | 24/7 Annual (idle) |
|-----------|------|------|---------------------|
| pve1 (i3-N305) | ~10W | ~40W | ~88 kWh |
| pve2 (N200) | ~8W | ~30W | ~70 kWh |
| pve3 (N5 Pro) | ~15W | ~55W | ~131 kWh |
| RX 9070 XT (when connected) | ~30W | ~304W | Only during inference |
| **Total cluster (no GPU)** | **~33W** | **~125W** | **~289 kWh** |

At ~0.30 EUR/kWh (Belgium), the 3-node cluster costs approximately **~87 EUR/year** idle. The GPU adds significant power only during active inference; at 2 hours/day average usage it would add ~55 kWh/year (~16 EUR).

### Hardware Investment

| Item | Approx. Cost |
|------|-------------|
| Minisforum N5 Pro (barebone) | ~600-800 EUR |
| DDR5 RAM (64-96GB) | ~150-250 EUR |
| M.2 NVMe SSD (512GB-1TB) | ~50-80 EUR |
| RX 9070 XT 16GB | ~550-650 EUR |
| Minisforum Deck 2 (already bought) | ~150-200 EUR |
| **Total** | **~1,500-1,980 EUR** |

---

## Future Outlook

### Near-term (1-3 months)
- Complete Phase 1-3 (Proxmox + cluster join)
- Evaluate GPU performance with Vulkan backend
- Test Ollama + Open WebUI for daily use

### Medium-term (3-6 months)
- **ROCm RDNA 4 maturation**: Re-benchmark ROCm vs Vulkan as AMD ships compiler optimizations
- **Ceph evaluation**: With 3 nodes, evaluate Ceph for live migration capability
- **N5 Pro NPU**: Investigate XDNA 2 NPU (50 TOPS) for lightweight AI tasks without GPU
- **NFS from pve3**: Use HDD bays for shared storage (ISOs, backups, media overflow)
- **Proxmox Backup Server**: Run PBS on pve3 to back up VMs/CTs from pve1/pve2

### Long-term (6-12 months)
- **Deck 2 as second AI node**: Connect a second GPU or use the Deck 2 as a portable inference station
- **Larger models**: As ROCm/Vulkan matures, test 20B-32B models with partial CPU offloading
- **vLLM / PyTorch**: Once ROCm RDNA 4 support is fully stable, evaluate for more advanced AI workloads
- **Terraform state migration**: Move to MinIO S3 backend hosted on pve3 HDD storage

---

## Sources

- [Minisforum N5 Pro Official](https://www.minisforum.com/products/n5-pro)
- [ServeTheHome N5 Pro Review](https://www.servethehome.com/minisforum-n5-pro-review-an-awesome-nas-platform/)
- [Notebookcheck N5 Pro Review](https://www.notebookcheck.net/Minisforum-N5-Pro-World-s-first-AI-NAS-with-AMD-Ryzen-AI-9-HX-PRO-370-IFA-2025-Award-winner-review.1142209.0.html)
- [llama.cpp ROCm Performance Discussion](https://github.com/ggml-org/llama.cpp/discussions/15021)
- [llamacpp-rocm Pre-built Builds](https://github.com/lemonade-sdk/llamacpp-rocm)
- [ROCm LLMExt Compatibility Matrix](https://rocm.docs.amd.com/en/latest/compatibility/ml-compatibility/llama-cpp-compatibility.html)
- [LocalScore RX 9070 XT Benchmarks](https://www.localscore.ai/accelerator/585)
- [TechReviewer: RX 9070 XT for LLMs](https://www.techreviewer.com/tech-specs/amd-rx-9070-xt-gpu-for-llms/)
- [egpu.io: eGPU LLM Inference](https://egpu.io/forums/pro-applications/impact-of-egpu-connection-speed-on-local-llm-inference-in-multi-egpu-setups/)
- [External GPU vs PCIe: LLM Speed Test](https://lilys.ai/notes/en/local-llm-20251213/external-gpu-pcie-llm-speed)
- [Proxmox Cluster Manager Wiki](https://pve.proxmox.com/wiki/Cluster_Manager)
- [Proxmox Forum: Mini PC for Proxmox](https://forum.proxmox.com/threads/mini-pc-for-proxmox.117531/)
- [Proxmox Forum: N5 Pro Discussion](https://forum.proxmox.com/threads/minisforums-nas-n5-pro.166323/)
- [Proxmox Forum: N5 Pro PVE9 Boot Issue](https://forum.proxmox.com/threads/minisforums-nas-n5-pro-cant-boot-with-pve9.169753/)
- [N5 Pro iGPU Passthrough Guide](https://www.naut.ca/blog/2025/11/20/minisforum-n5-pro-nas-igpu-passthrough/)
- [N5/N5 Pro Quick Start Guide](https://store.minisforum.com/blogs/blog/n5-n5-pro-quick-start-guide)
- [Proxmox Forum: AMD Ryzen AI 9 HX 370 Drivers](https://forum.proxmox.com/threads/amd-ryzen-ai-9-hx-370-drivers.169525/)
- [XDA: Self-hosted Ollama Proxmox LXC with AMD GPU](https://www.xda-developers.com/self-hosted-ollama-proxmox-lxc-uses-amd-gpu/)
- [XDA: GPU Passthrough to LXCs beats VMs](https://www.xda-developers.com/gpu-passthrough-to-lxcs-beats-vms/)
- [Virtualization Howto: OCULink eGPU Proxmox](https://www.virtualizationhowto.com/2026/03/i-added-an-egpu-to-my-proxmox-mini-pc-home-lab-using-oculink-heres-what-happened/)
- [Proxmox Forum: Best Storage for 3-Node Cluster](https://forum.proxmox.com/threads/best-storage-solution-for-a-3-node-cluster-in-a-homelab.92203/)
- [SelfHostWise: Proxmox Storage Options Compared](https://selfhostwise.com/posts/proxmox-ve-storage-options-zfs-lvm-thin-ceph-and-nfs-compared/)
- [VanMieghem: Automating Proxmox with Terraform and Ansible](https://vanmieghem.io/automating-proxmox-with-terraform-ansible/)
- [Proxmox Forum: 3-Node Ceph Tutorial](https://forum.proxmox.com/threads/step-by-step-guide-3-node-proxmox-cluster-with-ceph-storage-full-video-tutorial.164565/)
- [Digital Spaceport: Ollama + OWUI Proxmox LXC Guide](https://digitalspaceport.com/how-to-setup-an-ai-server-homelab-beginners-guides-ollama-and-openwebui-on-proxmox-lxc/)
- [Scottymarch: Ollama Open WebUI GPU Proxmox](https://scottymarch.com/complete-guide-setting-up-ollama-and-open-webui-with-gpu-passthrough-on-proxmox/)
- [Ollama Hardware Support](https://docs.ollama.com/gpu)
- [Phoronix: Ollama Experimental Vulkan](https://www.phoronix.com/news/ollama-Experimental-Vulkan)
- [LLM Tracker: AMD GPUs](https://llm-tracker.info/howto/AMD-GPUs)

---

**Technical Research Completion Date:** 2026-04-15
**Research Methodology:** Live infrastructure inspection (SSH), web research with source verification, community benchmarks
**Confidence Level:** High -- based on multiple independent sources, verified hardware specs, and active community validation
**Document Status:** Complete
