---
title: pve3 BIOS — Fixed VRAM allocation for Radeon 890M iGPU
date: 2026-04-24
updated: 2026-04-24 (post-Epic-3 execution — real BIOS options verified)
node: pve3 (MinisForum N5 Pro)
applies-to: Epic 3 Story 3.2 (pve3 reinstall), or any planned pve3 reboot maintenance window
relates-to: story-7-10 (this runbook is the Story 7-10 AC artifact), epic-3-complete-2026-04-24.md
---

# pve3 — Fixed VRAM BIOS configuration runbook

## BIOS options available on this MinisForum N5 Pro (verified 2026-04-24)

The UMA Frame Buffer Size menu offers exactly **three** fixed-size options:

| Option | Host RAM remaining (96 GB − UMA) | Typical LLM fit | Notes |
|---|---|---|---|
| **16 GB** | 80 GB | 13B Q4, 30B Q2 | Over-conservative on a 96 GB system |
| **32 GB** ✅ Epic 3 choice | 64 GB | **30B Q4, 70B Q2** | Best balance for this hardware; memory bandwidth bottlenecks before VRAM size does |
| **48 GB** | 48 GB | 70B Q3, larger context | Tight on host — 36 GB of CT allocations + ZFS ARC + kernel leaves <12 GB headroom |

**"24 GB" is NOT available** in this BIOS revision (the original spec assumed a continuous selector). Epic 3 used 32 GB.

## Purpose

The Radeon 890M iGPU in pve3's AMD Ryzen AI 9 HX PRO 370 uses UMA (Unified Memory Architecture) — system RAM carved out at BIOS level and exposed to the GPU as "VRAM". Setting it to a Fixed value (not Dynamic/Auto) enables:

1. **Reliable Ollama iGPU detection** — there is a known Ollama issue ([ollama/ollama#11451](https://github.com/ollama/ollama/issues/11451)) where gfx1150 (Radeon 890M) is not detected with Dynamic VRAM on AMD Ryzen AI 300 series. Fixed-mode allocation avoids this entirely.
2. **Larger LLM models on-device** — 32 GB VRAM comfortably runs 30B Q4 models or 70B Q2.
3. **Predictable host RAM accounting** — the UMA carveout is fixed, so `free -h` gives an honest number.

## Prerequisites

- pve3 must be powered off or about to reboot (BIOS settings are pre-boot)
- Physical monitor + USB keyboard connected to pve3 (BIOS is not accessible remotely — no BMC on this platform)
- Confirm no CT on pve3 has a memory reservation exceeding (96 − selected UMA) GB before making the change. Default pve3 CTs: CT160 16 GB + CT162 8 GB + CT250 8 GB = 32 GB committed. 32 GB UMA leaves 64 GB host → 32 GB headroom (safe).

## When to execute this runbook

Two good moments:
1. **During Epic 3 Story 3.2 reinstall** — reboot already happening, BIOS access cost is zero. Apply before the Proxmox installer USB boots.
2. **As a dedicated maintenance window** — schedule ~30 min downtime on pve3 (CT160, CT162, CT250 need to stop or migrate off). Cluster remains 2/3 quorate.

## Pre-reboot checklist

```bash
# 1. Evacuate or stop pve3's CTs
ssh pve3 "pct list"   # note what's running

# If Epic 3 execution:
#   CT160 is already stopped per Story 3.1
#   CT162 migrated to pve2 per Story 3.1
#   CT250 migrated to pve1 temporarily
# If standalone maintenance:
pct migrate 162 pve2 --restart --target-storage local-zfs
pct migrate 250 pve1 --restart --target-storage local-zfs
ssh pve3 "pct stop 160"   # CT160 can't migrate (iGPU passthrough)

# 2. Verify remaining cluster is healthy
ssh pve1 "pvecm status | grep -E 'Nodes|Quorate'"
# Expected: Nodes: 2 (or 3 if you haven't powered off yet), Quorate: Yes

# 3. Note current VRAM allocation (for rollback reference)
ssh pve3 "dmesg | grep -iE 'amdgpu|GTT|VRAM' | head -20"
# Record output — useful for rollback verification

# 4. Clean shutdown of pve3
ssh pve3 "shutdown -h now"
```

## BIOS settings change

### Step 1 — Enter BIOS

1. Power on pve3
2. Immediately press **Del** repeatedly (or **F2**, depending on BIOS — the MinisForum splash screen shows the key)
3. BIOS Setup Utility opens

### Step 2 — Navigate to UMA Frame Buffer Size

Exact menu path on MinisForum N5 Pro (AMI BIOS typical layout — may vary slightly by BIOS revision):

```
Advanced → AMD CBS → NBIO Common Options → GFX Configuration → UMA Frame Buffer Size
```

Alternative paths to try if the above doesn't exist in your BIOS revision:
- `Chipset → System Agent (SA) Configuration → Graphics Configuration → DVMT Pre-Allocated` (some revisions)
- `Advanced → AMD PBS → GFX UMA Size` (newer revisions)
- `Advanced → AMD Overclocking → GFX → UMA Buffer Size`

Look for a setting that lists GB values (512M, 1G, 2G, 4G, 8G, 16G, **24G**, possibly Dynamic/Auto).

### Step 3 — Set to 24G Fixed

1. Highlight the UMA Frame Buffer Size setting
2. Press **Enter**
3. Select **24G** (NOT Auto/Dynamic)
4. Press **Enter** to confirm

If you also see a separate "UMA Mode" or "GFX Memory Mode" setting:
- Set to **UMA_SPECIFIED** or **Fixed** (NOT **UMA_AUTO** or **Dynamic**)

### Step 4 — Save and exit

1. Press **F10** (Save & Exit) — or navigate to `Save & Exit → Save Changes and Reset`
2. Confirm **Yes**
3. System reboots

## Post-boot verification

After pve3 boots, SSH in and run:

```bash
# 1. Confirm host RAM is now ~72 GB (96 minus 24 reserved for iGPU)
free -h
# Expected: total ≈ 72Gi (if Fixed 24GB worked)
# If total still shows 86Gi-ish: Fixed allocation didn't take, fallback to dynamic. Re-enter BIOS.

# 2. Kernel iGPU allocation
dmesg | grep -iE "amdgpu.*vram|GTT|amdgpu.*memory" | head -10
# Expected: amdgpu lines showing 24576 MB VRAM or similar

# 3. AMD driver reports
cat /sys/class/drm/card0/device/mem_info_vram_total 2>/dev/null
# Expected: value near 25769803776 (= 24 GB in bytes)

# 4. If you have rocm-smi installed
rocm-smi --showmeminfo vram 2>/dev/null || echo "rocm-smi not installed (optional)"

# 5. CT160 iGPU passthrough check after starting CT160
pct start 160
pct exec 160 -- ls -la /dev/dri 2>&1 | head -5
# Expected: /dev/dri/card0 and /dev/dri/renderD128 present inside CT
pct exec 160 -- rocminfo 2>&1 | grep -E "Name|Marketing" | head -10
# Expected: Radeon 890M or gfx1150 listed

# 6. Ollama iGPU detection (the key success criterion)
pct exec 160 -- journalctl -u ollama --since "1 min ago" | grep -iE "gpu|rocm|vulkan" | head -10
# Expected: Ollama logs indicate iGPU detected (not "no GPU found, using CPU")

# 7. Test inference to confirm it hits iGPU (not CPU fallback)
pct exec 160 -- bash -c 'ollama run llama3.2:3b "hello" 2>&1 | head -20'
# While this runs, in another shell:
ssh pve3 "radeontop -d - -l 1" 2>&1 | head -5
# Expected: non-zero GPU utilization during inference
```

## Rollback procedure (if something is wrong)

If post-boot verification shows Ollama broken, host RAM miscounted, or BIOS setting corrupted the platform:

1. Shutdown pve3
2. Re-enter BIOS (Del at POST)
3. Navigate back to UMA Frame Buffer Size
4. Either:
   - Set back to previous value (likely 16G Fixed or Auto/Dynamic), OR
   - Reset BIOS to optimal defaults via `Save & Exit → Load Optimized Defaults` (will also reset any other BIOS tweaks; note them first)
5. Save & reboot
6. Verify host sees full 96 GB RAM again via `free -h`

## Troubleshooting

### BIOS doesn't offer a 24G option — caps at 16G

Older MinisForum BIOS revisions may not expose the 24 GB option. Check BIOS version on splash screen or via `dmidecode -s bios-version`. If older than 2025-Q3:
- Check MinisForum's support site for latest BIOS for N5 Pro
- Flash to latest per MinisForum's flashing procedure (requires USB, may be risky)
- Retry setting after flash

If unwilling to flash: **16G Fixed is still a meaningful improvement over Dynamic** and works with Ollama per the GitHub issue workaround.

### Post-boot `free -h` shows full 96 GB (allocation didn't apply)

BIOS may have silently ignored the Fixed-24G setting. Common causes:
- UMA Mode is set to "Auto" / "Dynamic" overriding Fixed value
- BIOS revision bug requiring a toggle of Power-Cycle-then-reboot to apply

Fix:
- Re-enter BIOS
- Verify the **Mode** is set to Fixed/UMA_SPECIFIED AND the **Size** is set to 24G
- If both correct, do a full power cycle (power off, unplug for 30 sec, power on)

### Ollama still falls back to CPU after setting fixed VRAM

Even with Fixed VRAM correctly allocated, Ollama may need explicit GPU selection:

```bash
pct exec 160 -- bash -c 'echo "HSA_OVERRIDE_GFX_VERSION=11.5.0" >> /etc/systemd/system/ollama.service.d/override.conf'
pct exec 160 -- systemctl daemon-reload && systemctl restart ollama
```

Reference: Ollama's [gfx1150 workaround documentation](https://github.com/ollama/ollama/issues/11451)

### CT160 fails to start after VRAM change

Likely cause: PCI device IDs for the iGPU shifted. Check:

```bash
pct config 160 | grep -i dev
lspci | grep -i vga
```

If device address changed (e.g., was `0000:c7:00.0`, now `0000:c6:00.0`), update CT config:

```bash
pct set 160 -dev0 /dev/dri/card0,gid=44
# Or via Proxmox UI: Resources → Device Passthrough → edit
```

## Notes for Epic 3 integration

When executing this as part of Story 3.2 (pve3 reinstall):

1. Do this BIOS change **FIRST**, before booting the Proxmox installer USB
2. After the Fixed-24G setting is applied and saved, insert install USB and boot from it
3. Auto-installer will see 72 GB host RAM (expected)
4. Post-install first-boot script and pve-node-bootstrap playbook run normally
5. After CT160 is restored (Story 3.8), run verification steps above to confirm iGPU is working

## References

- AMD Ryzen AI 300 series UMA documentation: [AMD developer docs on Unified Memory](https://www.amd.com/en/developer/resources/technical-articles.html)
- Ollama gfx1150 Dynamic VRAM issue: https://github.com/ollama/ollama/issues/11451
- Jeff Geerling's AMD APU VRAM allocation guide: https://www.jeffgeerling.com/blog/2025/increasing-vram-allocation-on-amd-ai-apus-under-linux/
- MinisForum N5 Pro support: https://minisforum.com/ (look up N5 Pro BIOS downloads)
