---
type: story
epic: FE4
id: FE4-S05
title: "Retrospective; explicit decision on whether to open a productisation phase or stop"
size: S
priority: MUST
owner: operator
blocking: false
fr_refs: [FR-KIT-006]
nfr_refs: []
adr_refs: [ADR-006]
risk_refs: [R8, R3]
status: draft
date: 2026-09-09
---

# FE4-S05: Retrospective; explicit decision on whether to open a productisation phase or stop

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

As **tomamourette**, I want **a retrospective across all five Forge PoC epics and one explicit
decision on whether to open a productisation phase (tenancy cut, OpenMemory, Hermes) or stop here**,
so that **the single highest-likelihood failure mode identified in the risk register — scope creep
from the PoC into productisation — cannot happen by drift, only by deliberate, recorded choice**.

## Background and Context

R8 names this precisely: *"Scope creep from the PoC into productisation... None of them blocks the
PoC and none should be answered inside it. FE4-S05 is the gate where productisation may be opened —
not before. High likelihood, high cost — the failure mode most likely to actually occur."* This
story is that gate, and only this story. `docs/forge-reuse-and-proxmox-findings.md` §5 lists 16
decisions that belong to the platform owner, four of which block the tenant manifest schema; none
of the 16 has been answered anywhere in FE0–FE4, by design (§3.4's "minimal Phase 0" reasoning), and
this story is where they get triaged — not resolved, triaged. ADR-006 records what is out of PoC
scope (Hermes, OpenMemory, Langfuse) and, per §4.1, the re-entry conditions under which any of them
could come back; those conditions are the test this story applies if the decision is to open a next
phase. This story restates FE4-S04's verdict verbatim rather than re-deriving it — verdict and
next-phase decision are deliberately two different stories precisely so one cannot leak into the
other.

## Acceptance Criteria

**AC1 — Retrospective covers all five epics.**
- **Given** FE0 through FE4 have each reached a terminal state (`done`, explicitly `deferred`, or
  explicitly abandoned, per whatever the sprint-status file shows at retrospective time),
- **When** the operator authors the per-epic retrospective section,
- **Then** each of FE0, FE1, FE2, FE3, FE4 has its own paragraph naming what worked, what didn't,
  and linking the relevant story files by ID.

**AC2 — FE4-S04's verdict is restated, not re-litigated.**
- **Given** FE4-S04 recorded a single explicit verdict,
- **When** this retrospective opens its findings section,
- **Then** it quotes that verdict verbatim (copy-pasted, not paraphrased) and does not introduce a
  second, different, or softened verdict anywhere in this story.

**AC3 — The 16 platform-owner decisions are triaged, not silently answered.**
- **Given** `docs/forge-reuse-and-proxmox-findings.md` §5 lists 16 decisions belonging to the
  platform owner, four of which block the tenant manifest schema,
- **When** the operator addresses productisation in this story,
- **Then** each of the 16 is explicitly marked **"in scope if productisation opens"** or **"still
  out of scope"** — none is answered in the prose of this retrospective; a mark is not an answer.

**AC4 — Explicit open/stop decision.**
- **Given** AC1–AC3,
- **When** the operator makes the call,
- **Then** exactly one of **OPEN a productisation phase** (naming which of the 16 decisions are
  picked up first, and which of ADR-006's re-entry conditions for Hermes/OpenMemory/Langfuse are
  now satisfied, if any) or **STOP** (the Forge PoC closes; no further Forge work is scheduled) is
  recorded in bold, with the reasoning explicitly tied back to the FE4-S04 verdict quoted in AC2.

**AC5 — If OPEN, next-phase scope is bounded, not a blank check.**
- **Given** the AC4 decision is **OPEN**,
- **When** the operator records next steps,
- **Then** the retrospective lists only which of the 16 decisions are picked up first, states
  explicitly that a **new** BMAD artifact set (new brief/PRD/epics under a new or extended product
  folder) is required before any implementation begins, and confirms this story itself performs
  **no** such implementation.

**AC6 — Closure state proposed, not applied.**
- **Given** HARD RULE 7 forbids touching `implementation-artifacts/sprint-status.yaml` from any
  artifact in this set,
- **When** the retrospective concludes,
- **Then** it states, as a proposal for the operator to apply by hand, what
  `epic-fe4-retrospective` and the overall Forge PoC status should read in the sprint-status file —
  this story does not edit that file itself.

## Implementation Notes

Cite ADR-006 for the out-of-scope services and their re-entry conditions, R8 for the scope-creep
risk this story exists to close safely, and R3 for the standing decision to reconcile (not
supersede) `docs/forge-reuse-and-proxmox-findings.md` — if OPEN is chosen, that document's remaining
15 non-blocking decisions are the natural backlog seed for the next artifact set, not something to
re-litigate here.

```text
Per-epic retrospective skeleton (AC1):
  FE0 — Prerequisites and truth:   what worked / what didn't / story links
  FE1 — Substrate (CT 167):        what worked / what didn't / story links
  FE2 — Control plane:             what worked / what didn't / story links
  FE3 — Workspace template:        what worked / what didn't / story links
  FE4 — Toolkit and acceptance:    what worked / what didn't / story links

16-decision triage table (AC3):
  # | Decision (from findings doc §5) | in scope if OPEN | still out of scope
  1..16 | ... | ... | ...
```

## Test Plan

**Pre-state:** FE4-S04 (verdict) is `done`; every other FE0–FE4 story is in a terminal state.

**Action sequence:**
1. Pull the FE4-S04 verdict verbatim into this story (AC2).
2. Write the five per-epic retrospective paragraphs (AC1).
3. Enumerate and triage the 16 platform-owner decisions (AC3).
4. Make and record the OPEN/STOP call (AC4).
5. If OPEN, bound the next-phase scope per AC5; if STOP, state that explicitly and record what, if
   anything, remains as a documented backlog item.
6. Propose the sprint-status closure state without editing the file (AC6).

**Post-state checks:**
- Exactly one of **OPEN** / **STOP** appears in bold, once.
- The FE4-S04 verdict quote in this story matches FE4-S04's verdict line character-for-character.
- All 16 decisions from the findings document appear in the triage table with a mark.
- `implementation-artifacts/sprint-status.yaml` is unmodified by this story
  (`git status --porcelain implementation-artifacts/sprint-status.yaml` is empty).

**Rollback:** None — this is a document. A later correction is a dated addendum, not a silent edit.

## Dependencies

- **Blocked by:** FE4-S04.
- **Blocks:** Nothing within this artifact set — this is the last story. If the decision is
  **OPEN**, it blocks (conceptually, not in this tracker) the authoring of a new BMAD artifact set
  for the next phase, which is explicitly out of this story's own scope to perform.

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| R8 — productisation gets answered piecemeal across FE0–FE4 instead of at this single gate | High | High | Every other FE0–FE4 story in this set carries the same restriction in its Background section; this story is the only one with authority to open it (HARD RULE) |
| R3 — the reconciled findings document's remaining decisions get silently re-litigated instead of triaged | Medium | Medium | AC3 requires a mark, not an answer, for every one of the 16 decisions |
| Retrospective drifts into re-deriving a different verdict than FE4-S04's | Low | High — two conflicting verdicts in the artifact set | AC2 requires a verbatim quote, checkable by diff |

## Definition of Done

- [ ] AC1–AC6 all satisfied.
- [ ] OPEN/STOP decision recorded in bold, exactly once, tied to the FE4-S04 verdict.
- [ ] All 16 platform-owner decisions triaged with an explicit mark.
- [ ] `sprint-status.yaml` confirmed unmodified.
- [ ] Story status updated from `draft` to `done` in this file's frontmatter.
