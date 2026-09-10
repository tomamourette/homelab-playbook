---
type: story
epic: FE4
id: FE4-S03
title: "PBS backup of CT 167 to pve3-pbs; record the job"
size: XS
priority: MUST
owner: dev
blocking: false
fr_refs: [FR-KIT-004]
nfr_refs: [NFR-DISP-001]
adr_refs: []
risk_refs: []
status: draft
date: 2026-09-09
---

# FE4-S03: PBS backup of CT 167 to pve3-pbs; record the job

> **BLOCKED — do not start.** Per §5.4 of the approved proposal, nothing in FE1–FE4 begins
> before **both** operator prerequisites exist:
> 1. **GitHub OAuth App** → `CODER_EXTERNAL_AUTH_0_ID/TYPE/CLIENT_ID/CLIENT_SECRET` (FE0-S01).
>    The only non-optional external credential in the whole PoC. Without it the workspace build
>    **fails** — `data "coder_external_auth" "github"` (`coder/templates/forge/main.tf:25-27`) has
>    no `optional = true` — and even if it did not, `forge-sync.sh` sources its token from
>    `coder external-auth access-token github` and **silently skips its entire clone block**, so
>    agentic-ai never lands and gates (b)–(e) are untestable.
> 2. **Cloudflare API token**, DNS-edit scope, zone `bi-services.be` (FE0-S02). Required for
>    **any** browser-trusted certificate — the homelab has no inbound :80/:443, so HTTP-01 is
>    impossible, not merely inconvenient. Wildcard scope is optional; the token is not.
>    **REVERSED 2026-09-09 — a wildcard IS required.** The token sentence still holds and the
>    token needs no re-scoping; only the "wildcard scope is optional" clause is dead. See the
>    amendment at the top of [ADR-005](../adrs/ADR-005-dns-01-wildcard-over-public-ingress.md).

## User Story

As **tomamourette**, I want **CT 167 backed up to pve3-pbs, with the backup job recorded**, so that
**the PoC's disposability promise (NFR-DISP-001) is actually backed by a recovery point, not just
asserted in prose**.

## Background and Context

NFR-DISP-001 states the PoC is "reversible at near-zero cost: destroy one CT, stash one Terraform
block, keep a documented negative result." A PBS backup is the piece that makes "destroy one CT"
genuinely low-risk rather than merely cheap — without it, a bad `terraform destroy` or an in-place
mistake during FE4-S02's acceptance run has no recovery path short of re-running FE1–FE3 in full.
This story is deliberately minimal and manual: per §3.4's reconciliation table, CI wiring and any
form of automation beyond the existing homelab pattern is explicitly **out of Phase-0 scope** for
this PoC (heavy Phase 0 items were rejected in favour of a minimal one). A single, recorded,
verified backup is sufficient evidence for FR-KIT-004; a recurring schedule is productisation-shaped
and belongs to the FE4-S05 gate if a next phase opens, not to this story.

pve3-pbs is the same Proxmox Backup Server target already used for the other project CTs on pve3;
no new storage or infrastructure is introduced here.

## Acceptance Criteria

**AC1 — Backup job runs to completion.**
- **Given** CT 167 exists (post-FE1) and, ideally, has already been exercised by FE4-S01/FE4-S02 so
  the backup captures a representative state rather than an empty shell,
- **When** the operator runs `vzdump 167 --storage pve3-pbs --mode snapshot --node pve3`,
- **Then** the command exits `0` and prints a completed-backup summary with no errors.

**AC2 — Backup is visible and dated in PBS.**
- **Given** AC1 has passed,
- **When** the operator runs `proxmox-backup-client snapshot list --repository <pve3-pbs-repo> ct/167`,
- **Then** at least one snapshot for `ct/167` is listed, dated 2026-09-09 or later.

**AC3 — Backup integrity verified.**
- **Given** AC2 has passed,
- **When** the operator runs the PBS verify job for the `ct/167` group (CLI `proxmox-backup-client
  verify` or the equivalent GUI "Verify" action against the pve3-pbs storage),
- **Then** the verification reports **OK**, with no corruption flagged.

**AC4 — Job details recorded in this story.**
- **Given** AC1–AC3 have passed,
- **When** the operator records the snapshot ID, size, and duration from the `vzdump` output,
- **Then** that record is written verbatim into this story's Test Plan — this is the "job recorded"
  half of FR-KIT-004, distinct from the backup existing.

## Implementation Notes

No Terraform or Ansible role change is introduced — `vzdump` / `proxmox-backup-client` are
operator-run Proxmox tooling, consistent with NFR-IAC-001's break-glass allowance for operational
commands that are not infrastructure state changes. pve3-pbs is the existing PBS storage target
already backing other project CTs; no new datastore is created.

```bash
# Run the backup
vzdump 167 --storage pve3-pbs --mode snapshot --node pve3

# Confirm it landed
proxmox-backup-client snapshot list --repository <pve3-pbs-repo> ct/167

# Verify integrity
proxmox-backup-client verify ct/167 --repository <pve3-pbs-repo>
```

## Test Plan

**Pre-state:** CT 167 exists and is running; FE4-S01/S02 have ideally already exercised it so the
snapshot is representative rather than empty.

**Action sequence:**
1. Run the `vzdump` command; capture full output.
2. List snapshots in PBS; confirm the new one is present.
3. Run the verify step; confirm OK.
4. Record snapshot ID, size, and duration in the checks below.

**Post-state checks:**
- `vzdump` exit code `0`.
- Snapshot ID: `__` / Size: `__` / Duration: `__` (fill in at execution time).
- Verify result: `OK`.

**Rollback:**
- None needed — the backup is additive and does not modify CT 167. If the snapshot is later judged
  unrepresentative (e.g., taken before FE4-S02 ran), re-run `vzdump` after the acceptance gates and
  keep both snapshots; PBS's deduplicated storage makes this inexpensive.

## Dependencies

- **Blocked by:** FE1-S02 (CT 167 must exist). Best sequenced after FE4-S02 for a representative
  snapshot, though not strictly required.
- **Blocks:** FE4-S04 (the verdict can cite this backup as evidence for NFR-DISP-001), FE4-S05.

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Single manual backup, no recurring schedule | High (by design) | Low for a PoC | Acceptable for PoC scope per §3.4's "minimal Phase 0" reasoning; a recurring PBS job is a productisation follow-up to be triaged at FE4-S05 (R8), not added here |
| pve3-pbs storage runs low on capacity | Low | Medium | `vzdump` fails loudly on a full datastore; AC1's exit-code check catches this immediately rather than silently |

## Definition of Done

- [ ] AC1–AC4 all green and evidenced.
- [ ] Snapshot ID, size, and duration recorded in this story.
- [ ] Verify result recorded as `OK`.
- [ ] Story status updated from `draft` to `done` in this file's frontmatter.
