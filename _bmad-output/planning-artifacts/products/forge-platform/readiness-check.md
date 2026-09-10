---
type: readiness-check
product: forge-platform
version: 1.0.0
status: pass-with-notes
date: 2026-09-09
authors: tomamourette (with BMad assist)
verdict: PASS-WITH-NOTES
implementation_gate: NO-GO (blocked on §5.4 operator prerequisites and the R4 sizing decision)
source_proposal: ../../sprint-change-proposal-2026-09-09.md
---

# Forge Platform — Implementation Readiness Check

## Executive Verdict

**PASS-WITH-NOTES on the plan. NO-GO on starting implementation.**

The planning artifact set composes into a coherent, executable plan for a proof of concept whose
question is narrow and whose exit is cheap. Epic and story IDs are lifted verbatim from §4.2 of the
approved proposal rather than reinvented; FR coverage is 28/28 with no orphan FRs and no orphan
stories; every acceptance gate a–k traces to a story that produces it; the two blocking operator
prerequisites appear as first-class stories (FE0-S01, FE0-S02) with `blocking: true` in frontmatter
and a banner on every downstream story rather than as a footnote; the ingress posture cites the
policy that actually exists rather than the ADR that does not; and the rollback path is one
destroyed container, one stashed Terraform block and a documented negative result.

The verdict is **PASS-WITH-NOTES rather than PASS** because two things the plan depends on are
genuinely unresolved and cannot be closed by any amount of further authoring:

1. **The sizing decision (R4) has not been taken.** The workspace template's `coder_parameter`
   defaults are 12288 MB RAM and 20480 MB swap; they are `coder_parameter` and not `variable`, so a
   variables-file cannot lower them; and swap has no answer inside an unprivileged LXC whose
   `swap_mb` defaults to 512 MB. Two candidate resolutions exist and **neither has been chosen**.
   This is an operator capacity call against pve3. The proposal's approval note is explicit that
   approval did not settle it. It **blocks FE1-S01**.
2. **Double-nested Docker on a ZFS-backed LXC rootfs is untested in this estate (R5).** One nesting
   level is proven; two is not. The plan does not claim otherwise, and ADR-003 downgrades the
   consequence from fatal to degrading — but "we do not know" is the honest state, and no artifact
   in this set may be read as asserting that it will work.

Neither is a defect in the plan. Both are correctly *recorded as open* in `prd.md` §11, `epics.md`
§8, the sprint plan's G0 gate, and the sprint-status file's header comments. Recording them is the
requirement; resolving them silently would have been the defect.

**The implementation gate is NO-GO** for a third, simpler reason: neither of the two §5.4 operator
prerequisites exists yet. Nothing in FE1–FE4 starts before both do.

---

## Score Card

| # | Criterion | Result | Note |
|---|---|---|---|
| **A — Structure and provenance** | | | |
| A1 | Artifact set matches §4.1 of the approved proposal exactly | PASS | Every file in §4.1 exists and is non-empty |
| A2 | Structure mirrors the `products/context-stack` precedent | PASS | Same frontmatter conventions, heading style, table density |
| A3 | Epic and story IDs match §4.2 verbatim | PASS | FE0–FE4; 27 stories (FE0 ×5, FE1 ×5, FE2 ×6, FE3 ×6, FE4 ×5); no invented IDs |
| A4 | Story IDs match the sprint-status file keys | PASS | `implementation-artifacts/sprint-status-forge-platform.yaml`, 27 story keys + 5 epic keys + 1 retrospective key = 33 `development_status` entries |
| A5 | The existing `sprint-status.yaml` is untouched | PASS | §6.1 chose a separate file; §6.2 fallback was explicitly not taken |
| A6 | No edits to `planning-artifacts/prd.md`, `epics.md`, `architecture.md` | PASS | §4.3 requires none |
| **B — Requirements** | | | |
| B1 | Every FR traces to at least one story | PASS | 28/28, audited in `epics.md` §7 |
| B2 | Every story traces to at least one FR | PASS | No orphan stories |
| B3 | NFRs have acceptance binding | PASS-WITH-NOTES | 10 of 11 bind to a gate or story AC. **NFR-CAP-002 binds to a decision, not a test** — by design; it is the open sizing call |
| B4 | Out-of-scope is stated explicitly, not implied | PASS | `prd.md` §8: Hermes, OpenMemory, Langfuse named first, with ADR-006 giving re-entry conditions |
| **C — Architecture and decisions** | | | |
| C1 | Six ADRs authored per §4.1 | PASS | ADR-001…006, each with an explicit reversal trigger |
| C2 | The `/opt/coder/secrets` seam is documented and protected | PASS | `architecture.md` §6; FR-CTL-003, NFR-PORT-002, gate (f) |
| C3 | The two-Terraform-roots principle is stated | PASS | `architecture.md` §7; the Proxmox root is a sibling, not a relocation; `main.tf` is not forked (FR-WS-009) |
| C4 | The Azure→self-hosted substitution table (E5) is reproduced faithfully | PASS | `architecture.md` §8, with the evidence column intact |
| C5 | ADR-001 records the reversal trigger (a second untrusted user) | PASS | Also in ADR-002 |
| C6 | ADR-001 honestly records that it **overturns** the prior document's VM recommendation | PASS | Two of four arguments fall to E2; two survive as risks |
| **D — Decomposition and estimates** | | | |
| D1 | Stories are INVEST-shaped and ≤ one session each | PASS | Five are M (FE2-S05, FE3-S01, FE3-S03, FE3-S06, FE4-S02); the rest are S or XS |
| D2 | Estimates are t-shirt sizes or ranges, labelled as estimates | PASS | **No story points anywhere in the set** |
| D3 | Dependencies are explicit and the chain is serial where it must be | PASS | `epics.md` §3 and §5 |
| D4 | Effort total is consistent with §3.2 | PASS | M–L, two to four working sessions, *if the prerequisites land first* |
| **E — Test strategy** | | | |
| E1 | All eleven gates a–k are captured with concrete commands | PASS | `tests/acceptance.md` §2 |
| E2 | Gate (g) is correctly marked **non-gating** and still recorded | PASS | ADR-003; FR-KIT-003 |
| E3 | Gates are executed from a tailnet client **not on the LAN** | PASS | Stated in `tests/acceptance.md` and `tests/e2e-deployment.md` |
| E4 | Gate (d) uses the corrected C1 counts (2 global / 18 project-root) | PASS | "18 in `$HOME`" is explicitly called false |
| E5 | An end-to-end runbook plus rollback exists | PASS | `tests/e2e-deployment.md` |
| E6 | Failure scenarios map to the named risks | PASS | OOM→R4, inner dockerd→R5, no grant→FE0-S01, no certificate→FE0-S02, HA `error`→the ct:151 lesson |
| **F — Operational readiness** | | | |
| F1 | The two blocking operator prerequisites are prominent, not buried | PASS | FE0-S01/FE0-S02 with `blocking: true`; a banner on every FE1–FE4 story; a header block in the sprint-status file; `prd.md` §9.1; `epics.md` §2 |
| F2 | HA is specified via the Ansible roles only, to **both** peers | PASS | FR-SUB-005; direct `ha-manager`/`pvesr` marked break-glass; the ct:151 lesson cited |
| F3 | The Docker 29.5.0 trap is mitigated before it can fire | PASS | FE2-S06: `daemon.json` **and** a version pin |
| F4 | The VMID 166 phantom is neutralised before any plan | PASS | FE0-S05; gate (j) is the regression guard |
| F5 | The ingress posture cites a document that exists | PASS | `tailscale-policy.md:20-31` + `remote-access-topology.md`; **zero uncorrected "ADR-010" citations** in the set |
| F6 | Rollback is concrete and cheap | PASS | NFR-DISP-001; `tests/e2e-deployment.md` §5 |
| F7 | Backup of the new CT is in scope | PASS | FE4-S03, PBS to pve3-pbs |
| **G — Honesty** | | | |
| G1 | Verified `[V]` vs inferred `[I]` distinctions are preserved | PASS | CT 250→Debian 13 transfer, sysbox 0.7.1, and the prior document's unspot-checked citations all stay `[I]` |
| G2 | The sizing conflict is recorded as **open**, not resolved | PASS | `prd.md` §11.1, `epics.md` §8.1, sprint-plan G0, sprint-status header |
| G3 | R5 is recorded as **untested**, not assumed to work | PASS | `prd.md` §11.2, ADR-001, ADR-003 |
| G4 | The prior findings document is reconciled, not superseded | PASS | `prd.md` §3, ADR-001; its unspot-checked citations marked `[I]` |
| G5 | An explicit verdict is required and its criteria are defined in advance | PASS | FE4-S04 |
| G6 | Scope creep into productisation is contained at a named gate | PASS | FE4-S05 / G5; R8 |

**Totals: 34 PASS, 1 PASS-WITH-NOTES (B3), 0 FAIL.**

---

## Detailed findings (non-PASS items)

### B3 — NFR-CAP-002 binds to a decision rather than a test

`NFR-CAP-002` ("the sizing decision is resolved before FE1-S01") cannot be verified by running a
command. It is satisfied by an operator making a call and recording it. This is correct for what it
is, but it means the plan carries one requirement whose satisfaction is a human act rather than an
observable state, and that requirement gates the whole of FE1–FE4.

**Mitigation, already in the plan:** gate **G0** in `sprint-plan.md` makes the decision an explicit
go/no-go, and the sprint-status file records it in the header rather than in a comment on one line.
`NFR-CAP-001` and acceptance gate (h) then *measure* the consequence of whatever was decided. No
further fix is proposed.

---

## Blocking items before implementation starts

These are the plan's hard stops. All three must clear before FE1-S01.

1. **FE0-S01 — the GitHub OAuth App.** The only non-optional external credential in the PoC.
   Without it the workspace build fails, and even if it did not, `forge-sync.sh` silently skips its
   entire clone block, so agentic-ai never lands and gates (b)–(e) are untestable.
   **Operator only; cannot be delegated.**
2. **FE0-S02 — the Cloudflare DNS-edit token** for `bi-services.be`. Required for **any**
   browser-trusted certificate; HTTP-01 is impossible, not merely inconvenient. Wildcard scope is
   optional; the token is not. **Operator only; cannot be delegated.**
3. **The R4 sizing decision.** Option (a) four real `variable`s plus `swap_mb = 8192`, or option (b)
   size CT 167 at 4C/12GB. **Neither is chosen.** An operator capacity call against pve3.

---

## Recommended improvements (non-blocking)

1. **Land FE0-S04 (comment drift) before FE3 begins, not merely before FE3 ends.** An engineer
   reading `main.tf:399-404` sees a sysbox claim 62 lines above `privileged = true` and will port
   the wrong architecture. The plan sequences it correctly; the recommendation is to treat it as a
   hard precondition of touching the template rather than a tidy-up.
2. **Commit `docs/forge-reuse-and-proxmox-findings.md` with its dated header early.** It is an
   action of proposal §4.3 rather than a story here, so nothing in this plan forces it. An untracked
   352-line analysis is one `git clean` from gone (R3).
3. **Record the FE1-S05 measurement even if it exactly matches CT 250.** A confirming measurement is
   what converts an `[I]` into a `[V]`; skipping it because the result was expected would leave the
   inference standing.
4. **Decide `ct:167`'s HA state (R6) at FE1-S03 rather than deferring it.** Both replication jobs are
   required regardless; only the `started`/`stopped` choice is open, and deferring it leaves gate
   (k)'s expected output ambiguous.

---

## Outstanding questions carried into execution

Full statements in `prd.md` §11.

1. The sizing conflict (R4) — **blocks FE1-S01**.
2. Double-nested Docker on a ZFS-backed LXC rootfs (R5) — **untested**.
3. `intellij_gateway` (FE3-S05) — `terraform validate` fails while undecided.
4. `ct:167` HA state, `started` vs `stopped` (R6, FE1-S03).
5. The fate of `ct_sparkle_vlabel` (FE0-S05).

---

## Go / No-Go

| Question | Answer |
|---|---|
| Is the planning artifact set complete and internally consistent? | **Yes — PASS-WITH-NOTES.** |
| Is FE0 ready to start? | **Yes.** FE0-S01 and FE0-S02 are operator tasks that can begin immediately; FE0-S03/S04/S05 are small repo edits with no dependencies. |
| Is FE1 ready to start? | **No.** Blocked on FE0-S01, FE0-S02 and the R4 decision (gate G0). |
| Is the plan reversible if the PoC fails? | **Yes.** One destroyed CT, one stashed Terraform block, one documented negative result. A `DOES-NOT-PORT` verdict is a successful outcome of this PoC. |

**First action:** FE0-S01 and FE0-S02, in parallel, by the operator. **Second action:** take the R4
sizing decision. **Nothing else starts until all three are done.**

---

## Sign-off

| Role | Name | Status |
|---|---|---|
| Operator | tomamourette | Proposal approved as written, 2026-09-09; sizing decision explicitly **not** settled by that approval |
| Planning artifacts | BMad PM / Analyst / Architect / SM | Authored 2026-09-09 per proposal §4.1, §4.2, §6.1 |
| Implementation | BMad Dev | **Not started — NO-GO pending the three blocking items above** |
