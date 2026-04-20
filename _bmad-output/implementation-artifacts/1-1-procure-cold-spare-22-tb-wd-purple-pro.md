---
status: done
epic: 1
story: 1.1
title: Procure cold-spare 22 TB WD Purple Pro
---

# Story 1.1: Procure cold-spare 22 TB WD Purple Pro

## User Story

As an operator,
I want a 22 TB WD Purple Pro on the shelf,
So that a failed HDD during RAIDZ1 resilver can be replaced immediately without waiting on shipping.

## Acceptance Criteria

**Given** Phase 0 of the migration plan
**When** I place and receive the order
**Then** one sealed WD Purple Pro (matching part `WD221PURP`) is physically on the homelab shelf
**And** its serial number is documented in `homelab-playbook/_bmad-output/implementation-artifacts/cold-spare-inventory.md`
**And** the delivery date is recorded (for warranty tracking)

## Tasks

- Create tracking document at `cold-spare-inventory.md`
- Match drive model/part to the 5 existing HDDs on pve3
- Leave serial/delivery fields as placeholders for post-procurement fill-in

## Dev Notes

- Agent cannot physically place the order; the tracking doc is the actionable artifact for the human operator
- Existing HDDs on pve3 are `WDC WD221PURP-85CJRY0` (22 TB, 3.5", WD Purple Pro family) per pve3 `smartctl` inspection
- Target production serials captured live from pve3: 6LJ7HEUT (sda), 6LHYV64U (sdb), 69G94MNE (sdc), 6LJ59RET (sdd), 68G2NL9H (sde)
- Rationale for model-matching: keeping all 5+1 drives on the same firmware family minimizes surprise behaviour during resilver and avoids the occasional "mixed-vendor RAIDZ vibration resonance" anecdotes seen on home-lab NAS forums
- Warranty on WD Purple Pro is 5 yr — delivery date is the clock-start and must be captured

## Implementation Report

- Created `cold-spare-inventory.md` at `_bmad-output/implementation-artifacts/cold-spare-inventory.md`
- Status set to `to order`; Order date, Supplier, Serial, Delivery date, Physical location, Notes left as `TBD` placeholders for human fill-in post-procurement
- Captured the 5 live production serials from pve3 so the cold-spare record sits alongside an authoritative inventory
- No commits made (director handles that)
