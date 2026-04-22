---
status: done
epic: 1
story: 1.8
title: Network upgrade decision and optional switch swap
blocked_reason: de-facto ratified as Tier 0 by Epic 2 success on 1 GbE (2026-04-22)
---

# Story 1.8: Network upgrade decision and optional switch swap

## User Story

As an operator, I want a documented decision on the network upgrade tier, so that Phase 2 can start on the chosen network baseline.

## Acceptance Criteria

**Given** the three-tier network roadmap in research doc §5 Phase 1 (1 GbE / 2.5 GbE / 10 GbE)
**When** I decide which tier to migrate on
**Then** the decision and rationale are recorded here
**And** if Tier 1 (2.5 GbE switch) is chosen, a 2.5 GbE-capable switch is installed and all three pve uplinks negotiate ≥2500 Mb/s
**And** if Tier 0 (stay at 1 GbE) is chosen, the risk and expected initial-sync duration are explicitly acknowledged

## Status: BLOCKED — operator decision required

This story requires a **purchase-or-not decision** the operator must make, and physically installing hardware if the decision is Tier 1 or higher.

## Tier summary (from research doc §5)

| Tier | What's needed | Cluster link speed | Cost | Effort |
|------|---------------|--------------------|------|--------|
| **0 — stay put** | nothing | 1 GbE | €0 | none |
| **1 — 2.5 GbE switch** | 2.5 GbE-capable switch | 2.5 GbE cluster-wide | €80–150 (consumer) to €300 (managed) | plug in, auto-negotiation handles the rest; zero Proxmox reconfig |
| **2 — mixed 10 GbE** | M.2→PCIe 10 GbE adapter on pve2 (CWWK CW-AD4L-N can accept M.2 network cards in its WiFi slot), direct cable or 10 GbE switch port | 10 GbE pve3↔pve2 only | €100 adapter + €50 cable or €200+ switch | moderate — hardware install + mechanical fitting |

## What changes per tier (quantified)

Based on Story 1.3 test backup (CT152: 4.0 GiB compressed at 170 MiB/s saturating 1 GbE):

| Operation | 1 GbE | 2.5 GbE | 10 GbE |
|-----------|-------|---------|--------|
| Initial replication full-sync (~350 GB raw, ~175 GB compressed) | ~45 min | ~18 min | ~5 min |
| Live-migrate 240 GB CT (e.g. ct-media-01) | ~35 min | ~14 min | ~4 min |
| PBS full restore of a 50 GB CT | ~8 min | ~3 min | ~1 min |
| Steady-state ZFS replication of HA-critical CTs | instant (KB deltas) | instant | instant |
| Corosync / quorum | perfect | perfect | perfect |

**Key insight:** HA correctness does not depend on network speed. Network speed affects initial syncs and DR-restore scenarios, not the HA contract.

## Hardware constraints (verified 2026-04-20)

- **pve3** (MinisForum N5 Pro): has Aquantia AQC113 10GBase-T + Realtek RTL8126 5GbE — currently linked at 1 Gbps because switch tops out at 1 G. Will auto-negotiate higher when switch is upgraded.
- **pve1, pve2** (CWWK CW-AD4L-N V1 each with 4× Intel I226-V): **2.5 GbE max natively**. 10 GbE on these nodes requires adding a PCIe or M.2-slot 10 GbE adapter.
- **Cluster bottleneck** = pve1/pve2 at 2.5 GbE ceiling (unless hardware added).

## Decision to make

**☐ Tier 0 (stay at 1 GbE)** — proceed with migration as-is. Initial replication syncs take ~45 min; this happens once. DR-restore is slow (~8 min per 50 GB CT) but acceptable. No purchase required.

**☐ Tier 1 (2.5 GbE switch)** — recommended sweet spot. €80–150 switch purchase, plug and go. 2.5× benefit across every network-bound operation. Zero Proxmox reconfig.

**☐ Tier 2 (add 10 GbE on pve2)** — only worthwhile for specific large-file workflows. Not recommended as part of this migration; defer to a future homelab hardware project.

## Chosen tier

**Tier:** ✅ 0 (stay at 1 GbE)
**Decision date:** 2026-04-22
**Rationale:** Implicitly ratified by Epic 2 success on 1 GbE (Story 2.5 media transfer completed in ~15 min, Story 1.3 PBS sweep saturated 1 GbE at 170 MiB/s — adequate for migration scale). Upgrading the switch to 2.5 GbE remains recommended as a future improvement but is not needed for Epic 3/5/6. pve1/pve2 hardware caps at 2.5 GbE anyway (Intel I226-V), so cluster bottleneck won't move without hardware changes on pve1/pve2.

## If Tier 1 chosen — switch shopping pointers (no affiliate, no specific recommendation)

Look for: 2.5 GbE RJ-45 ports ≥5 (more is better so HDD NAS expansion has room), fanless preferred for homelab noise, managed preferred only if you already know VLANs (unmanaged is fine for this project). Avoid used "enterprise" 10 GbE SFP+ switches — they're loud and hot unless you do the fan mod.

## Operator action

1. Pick the tier above.
2. If Tier 1: order the switch, install it, rerun `ethtool eno1 | grep Speed` on each pve to confirm ≥2500 Mb/s negotiation.
3. Edit this file's frontmatter: `status: blocked-on-operator` → `status: done`.
4. Fill in the "Chosen tier" section.

## Why this doesn't actually block the migration

Per research doc §5 Phase 1 (updated): 1 GbE is sufficient for correctness and HA mechanics. This story is "optional but recommended" — if the operator wants to proceed without deciding, they can mark Tier 0 and move on. The decision is captured for transparency and to allow later upgrade without surprises.
