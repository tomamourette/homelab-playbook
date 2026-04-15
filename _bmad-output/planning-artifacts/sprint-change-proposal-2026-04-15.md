# Sprint Change Proposal: Add PVE3 Node + Local LLM Epic

**Date:** 2026-04-15
**Author:** tomamourette
**Change Type:** New Epic (Additive)
**Scope Classification:** Moderate

---

## Section 1: Issue Summary

### Problem Statement

New hardware has been acquired (Minisforum N5 Pro + AMD Radeon RX 9070 XT 16GB via OCULink) that needs to be integrated into the homelab infrastructure. This is not a defect or failed approach — it's a strategic expansion that adds a third Proxmox node and local LLM inference capability to the homelab.

### Context

- The N5 Pro (AMD Ryzen AI 9 HX PRO 370, 12C/24T, up to 96GB DDR5 ECC, 10GbE, OCULink) is significantly more powerful than existing nodes (pve1: i3-N305, pve2: N200)
- The RX 9070 XT connects via OCULink for local LLM inference (Gemma 4 26B target model)
- Comprehensive technical research has been completed: `planning-artifacts/research/technical-pve3-oculink-gpu-llm-research-2026-04-15.md`
- This epic can start immediately in parallel with Epic 3 (currently in-progress) since it's infrastructure work with no dependencies on the AI Dev Container epics

### Evidence

- Hardware purchased and available
- Technical research validates: Proxmox compatibility confirmed, Vulkan > ROCm for RDNA 4, Gemma 4 26B fits in 16GB at Q3_K_M, 3-node cluster gives real HA
- Research document: 974 lines, 24 verified sources

---

## Section 2: Impact Analysis

### Checklist Results

| # | Check | Status | Finding |
|---|-------|--------|---------|
| 1.1 | Triggering story | N/A | No trigger story — new capability from hardware acquisition |
| 1.2 | Core problem | Done | Strategic expansion, not a problem. Category: New requirement |
| 1.3 | Evidence | Done | Technical research document complete with verified benchmarks |
| 2.1 | Current epic impact | Done | Epic 3 (in-progress) is NOT affected — continues as-is |
| 2.2 | Epic-level changes | Done | ADD new Epic 8. No existing epics modified. |
| 2.3 | Remaining epics | Done | Epics 4-7 unaffected. Future opportunity: Epic 4 playbook could include pve3 provisioning |
| 2.4 | Invalidated/new epics | Done | No epics invalidated. One new epic needed. |
| 2.5 | Priority/ordering | Done | New epic runs in parallel — no resequencing needed |
| 3.1 | PRD conflicts | Done | No conflict. Minor update: add pve3 as infrastructure context in Project Classification |
| 3.2 | Architecture conflicts | Done | Minor update: add pve3 node to infrastructure topology. No architectural pattern changes. |
| 3.3 | UI/UX conflicts | N/A | Infrastructure project — no UI/UX |
| 3.4 | Other artifacts | Done | `docs/architecture-homelab-infra.md` needs update (network diagram, node table). Ansible inventory needs pve3 entry. |

### Epic Impact: NONE on existing epics

All existing epics (0-7) continue unchanged. The new epic is fully independent.

### Artifact Conflicts: MINIMAL

| Artifact | Impact | Change Needed |
|----------|--------|---------------|
| PRD | Informational | Add 1 line to Project Classification: "3-node Proxmox homelab" |
| Architecture | Informational | Add pve3 to infrastructure topology description |
| Epics | Additive | Add Epic 8 with stories |
| Sprint Status | Additive | Add epic-8 entries |
| `docs/architecture-homelab-infra.md` | Update needed | Add pve3 to network diagram, node table, corosync config |
| Ansible `hosts.ini` | Update needed | Add pve3 to `[proxmox_hosts]` |
| SSH config | Update needed | Add pve3 alias |

### Technical Impact

- Cluster topology changes from 2-node to 3-node (quorum improvement)
- New Proxmox node requires BIOS configuration, OS install, cluster join
- GPU passthrough via OCULink requires IOMMU configuration
- Local LLM stack (Ollama + Vulkan + Gemma 4) runs in LXC container on pve3

---

## Section 3: Recommended Approach

### Selected Path: Direct Adjustment (Add New Epic)

**Rationale:**
- This is purely additive — no existing work needs to change
- The epic is independent and can start immediately
- It has zero dependencies on Epics 0-7 (and vice versa)
- Technical research is already complete, reducing story estimation risk
- The hardware is already purchased — no procurement blockers

**Effort Estimate:** Medium (3-4 hours hands-on across 2-3 sessions)
**Risk Level:** Low (well-researched, community-validated approach)
**Timeline Impact:** None on existing epics — runs in parallel

---

## Section 4: Detailed Change Proposals

### Change 1: Add Epic 8 to Epics Document

**File:** `homelab-playbook/_bmad-output/planning-artifacts/epics.md`
**Section:** After Epic 4 (before Phase 2 epics)

**NEW (append after Epic 4):**

```markdown
---

## Epic 8: PVE3 Node + Local LLM — AI Inference at Home

Developer has a third Proxmox node (pve3) running on the Minisforum N5 Pro with an AMD RX 9070 XT GPU connected via OCULink, serving local LLM inference (Gemma 4 26B) through Ollama in an LXC container with a web chat interface.

**Research:** planning-artifacts/research/technical-pve3-oculink-gpu-llm-research-2026-04-15.md

### Story 8.1: Install Proxmox VE on N5 Pro and Join Cluster

As a homelab operator,
I want Proxmox VE installed on the N5 Pro and joined to home-cluster as pve3,
So that I have a 3-node HA-capable cluster with my most powerful hardware available.

**Acceptance Criteria:**

**Given** the N5 Pro with an M.2 NVMe SSD installed
**When** I complete the Proxmox installation and cluster join
**Then** BIOS is configured (SVM, IOMMU, ACS, UMA 8G, UEFI-only, Secure Boot off)
**And** Proxmox VE 8.4 is installed on NVMe (ext4/LVM, 96GB root, 8GB swap — matching pve1/pve2)
**And** hostname is `pve3`, static IP is `192.168.50.203/24`
**And** kernel params include `amd_iommu=on iommu=pt`
**And** VFIO modules are loaded (vfio, vfio_iommu_type1, vfio_pci)
**And** `/etc/hosts` on pve1, pve2, and pve3 all contain all three nodes
**And** `pvecm add 192.168.50.201` succeeds from pve3
**And** `pvecm status` shows 3 nodes, quorum=2, quorate=Yes
**And** Proxmox web UI at https://192.168.50.203:8006 shows all 3 nodes

**Edge Cases:**
- If graphical installer hangs: use "Console Mode - nomodeset"
- If PVE version mismatch: run `apt update && apt dist-upgrade` on pve1/pve2 first
- If NTP is not synced: enable `systemd-timesyncd` before cluster join

### Story 8.2: Integrate PVE3 into Infrastructure Automation

As a homelab operator,
I want pve3 integrated into Ansible, SSH config, DNS, and documentation,
So that pve3 is managed consistently with pve1 and pve2.

**Acceptance Criteria:**

**Given** pve3 is joined to the cluster (Story 8.1)
**When** I update the infrastructure automation
**Then** `ansible/inventories/homelab/hosts.ini` has pve3 in `[proxmox_hosts]`
**And** `ansible-playbook pve-host.yml --limit pve3` succeeds (NIC ring buffer tuning applied)
**And** SSH config on the control machine has `pve3` alias (192.168.50.203)
**And** Pi-hole custom list includes `pve3` DNS entry
**And** `docs/architecture-homelab-infra.md` is updated with pve3 in the network diagram and node table
**And** `ansible all -m ping` succeeds for all hosts including pve3

### Story 8.3: Set Up GPU via OCULink and LXC Container with Ollama

As a homelab operator,
I want the RX 9070 XT connected via OCULink and Ollama running in a GPU-accelerated LXC container,
So that I can run local LLM inference on my homelab.

**Acceptance Criteria:**

**Given** pve3 is in the cluster with IOMMU configured (Story 8.1)
**When** I connect the GPU and set up the AI container
**Then** RX 9070 XT is connected via OCULink and detected by pve3 (`lspci | grep -i vga`)
**And** IOMMU groups are verified (`find /sys/kernel/iommu_groups/ -type l`)
**And** a privileged LXC container `ct-ai-01` exists on pve3 (8 cores, 32GB RAM, 50GB disk)
**And** GPU device nodes are passed through to the container (`/dev/dri/card0`, `/dev/dri/renderD128`)
**And** Ollama is installed inside the container with Vulkan backend (`OLLAMA_VULKAN=1`)
**And** `ollama run gemma4:e4b` succeeds as a pipeline validation test (small model, ~3GB VRAM)
**And** `ollama ps` confirms GPU layers are being used (not CPU fallback)

**Edge Cases:**
- If GPU not detected: ensure dock/PSU is powered on before pve3 boot; check BIOS OCULink settings
- If IOMMU groups are too broad: apply ACS override patch
- If Vulkan not detected in LXC: verify `/dev/dri/*` device passthrough with mode 0666

### Story 8.4: Deploy Gemma 4 26B and Open WebUI

As a homelab operator,
I want Gemma 4 26B running via Ollama with a web chat interface,
So that I have a self-hosted ChatGPT-like experience powered by my own hardware.

**Acceptance Criteria:**

**Given** Ollama is running with GPU acceleration (Story 8.3)
**When** I deploy the target model and web interface
**Then** `ollama run hf.co/DuoNeural/Gemma-4-26B-A4B-it-GGUF:Q3_K_M` downloads and runs successfully
**And** VRAM usage stays under 16GB during inference (`~14GB model + ~1-2GB KV cache`)
**And** inference produces coherent responses at reasonable speed
**And** Open WebUI is deployed via Docker inside the LXC container
**And** Open WebUI is accessible at `http://192.168.50.<ip>:3000` and connects to Ollama API
**And** multimodal capability works (text + image input via Gemma 4's vision)

**Edge Cases:**
- If OOM during long conversations: reduce `num_ctx` in Ollama modelfile or switch to Q3_K_S
- If model download fails: retry or use alternative GGUF from Hugging Face
- If Open WebUI can't reach Ollama: verify both are on same container network, Ollama API on 11434
```

### Change 2: Update Sprint Status

**File:** `homelab-playbook/_bmad-output/implementation-artifacts/sprint-status.yaml`
**Section:** After Epic 7 entries

**NEW (append):**

```yaml
  # --- Infrastructure Expansion (added 2026-04-15, SCP-pve3-local-llm) ---

  # Epic 8: PVE3 Node + Local LLM — AI Inference at Home
  epic-8: backlog
  8-1-install-proxmox-on-n5-pro-and-join-cluster: backlog
  8-2-integrate-pve3-into-infrastructure-automation: backlog
  8-3-setup-gpu-via-oculink-and-lxc-with-ollama: backlog
  8-4-deploy-gemma-4-26b-and-open-webui: backlog
  epic-8-retrospective: optional
```

### Change 3: PRD Minor Update

**File:** `homelab-playbook/_bmad-output/planning-artifacts/prd.md`
**Section:** Project Classification

**OLD:**
```
- **Project Context:** Brownfield — extending existing 2-node Proxmox homelab (4 containers, 19 Docker stacks, 40+ services) with new AI development capabilities
```

**NEW:**
```
- **Project Context:** Brownfield — extending existing 2-node Proxmox homelab (expanding to 3 nodes with N5 Pro as pve3; 4+ containers, 19 Docker stacks, 40+ services) with new AI development capabilities and local LLM inference
```

**Rationale:** Reflects the expanded infrastructure scope without changing any requirements or MVP definition.

### Change 4: Architecture Minor Update

**File:** `homelab-playbook/_bmad-output/planning-artifacts/architecture.md`
**Section:** Technical Constraints & Dependencies table

**NEW (append row):**

```
| N5 Pro as pve3 (Epic 8) | Hardware acquisition | Third cluster node (192.168.50.203), 12C/24T, up to 96GB DDR5 ECC, 10GbE, OCULink for RX 9070 XT GPU. Independent of AI Dev Container epics. |
```

**Rationale:** Acknowledges the new hardware without changing any architectural decisions for the AI Dev Container.

---

## Section 5: Implementation Handoff

### Change Scope: Moderate

This is a **Moderate** change — it adds a new epic to the backlog but requires no modifications to in-progress or completed work. The backlog needs a new epic entry and the sprint status file needs updating.

### Handoff Plan

| Recipient | Responsibility |
|-----------|---------------|
| **SM (Bob)** | Add Epic 8 to epics document, update sprint-status.yaml |
| **Dev (Amelia)** | Execute stories 8.1-8.4 (physical hardware setup + configuration) |
| **Architect (Winston)** | Review architecture implications if Ceph or shared storage is planned later |

### Execution Notes

- **Epic 8 can start immediately** — it has zero dependencies on Epics 3-7
- Stories 8.1 and 8.2 are manual/physical tasks (BIOS, install, cluster join, Ansible)
- Stories 8.3 and 8.4 are configuration tasks (GPU passthrough, Ollama, Open WebUI)
- The full implementation roadmap with commands is in the research document
- **Epic 8 does NOT block or affect Epic 3** (currently in-progress)

### Success Criteria

1. `pvecm status` shows 3 nodes, quorum=2
2. `ollama ps` shows Gemma 4 26B running on GPU
3. Open WebUI accessible and functional
4. Infrastructure automation (Ansible, docs) updated

---

**Sprint Change Proposal Status:** Ready for Review

Review complete proposal. **Continue [c]** or **Edit [e]**?
