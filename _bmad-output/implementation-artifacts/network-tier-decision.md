# Network Tier Decision — Ratification

**Decision date:** 2026-04-22
**Chosen tier:** Tier 0 — stay at 1 GbE
**Status:** Ratified (de-facto, via Epic 2 completion on 1 GbE)

## Summary

The homelab cluster remains on 1 GbE. Epic 2 completed successfully at this speed (Story 2.5 media transfer ~15 min; Story 1.3 PBS sweep saturated 1 GbE at 170 MiB/s), confirming that 1 GbE is adequate for the migration workload. No switch upgrade is required for Epic 3 / 5 / 6.

A future 2.5 GbE switch upgrade remains recommended as a quality-of-life improvement but is not blocking. Note: pve1/pve2 hardware caps at 2.5 GbE (Intel I226-V), so cluster uplink won't move beyond that without additional PCIe/M.2 adapters on those nodes.

## Details

See `1-8-network-upgrade-decision-and-optional-switch-swap.md` for the full tier comparison, rationale, and hardware constraints.
