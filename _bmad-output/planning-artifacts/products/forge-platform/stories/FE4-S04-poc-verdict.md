---
type: story
epic: FE4
id: FE4-S04
title: "PoC verdict: PORTS / PORTS-WITH-CAVEATS / DOES-NOT-PORT, with caveats enumerated"
size: S
priority: MUST
owner: operator
blocking: false
fr_refs: [FR-KIT-005]
nfr_refs: []
adr_refs: [ADR-003]
risk_refs: [R4, R5, R6, R8]
status: draft
date: 2026-09-09
---

# FE4-S04: PoC verdict: PORTS / PORTS-WITH-CAVEATS / DOES-NOT-PORT, with caveats enumerated

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

As **tomamourette**, I want **a single, explicit, dated verdict on whether Forge ports to a
non-Azure substrate**, so that **"does it port?" stops being an opinion and becomes recorded
evidence the next decision (FE4-S05) can be built on**.

## Background and Context

Per §5.3 of the proposal: *"PoC verdict is a single explicit call in FE4-S04:
PORTS / PORTS-WITH-CAVEATS / DOES-NOT-PORT. Anything less than an explicit verdict means the PoC
did not do its job."* This story exists solely to make that call — it is not a retrospective (that
is FE4-S05) and it does not decide whether to productise (also FE4-S05, per R8 and HARD RULE: "FE4-S05
is the ONLY gate where productisation may be opened — not before"). The evidence this story judges
is FE4-S02's eleven recorded gate results and FE4-S03's backup confirmation. ADR-003 (gate (g) is
non-gating) is load-bearing here: a nested-Docker failure alone cannot force a DOES-NOT-PORT call.
R4 (sizing) and R6 (HA ambiguity) are the two most likely sources of a caveat rather than an outright
failure, since both have documented workarounds (manual sizing override; either HA state is a valid
operator choice under the Project-CT HA Policy).

## Acceptance Criteria

**AC1 — Verdict decision framework defined before the results are read.**
- **Given** FE4-S02 has recorded results for all eleven gates and FE4-S03 has confirmed a backup,
- **When** the operator authors this story's "Verdict Decision Framework" section **before**
  transcribing the FE4-S02 results into it,
- **Then** the framework states explicitly:
  - **PORTS** requires gates (a)–(f) and (h)–(k) all passing; gate (g)'s result is recorded but
    irrelevant to this tier per ADR-003.
  - **PORTS-WITH-CAVEATS** applies when one or more of gates (a)–(f), (h)–(k) fails or is degraded
    in a narrowly scoped, workaround-compatible way — e.g., gate (h) shows swap-thrashing at
    default sizing but a smaller manual override (R4) resolves it, or gate (k) shows `ct:167` in a
    valid-but-non-default HA state — **and** gate (g) fails outright (non-gating, per ADR-003, does
    not on its own force a worse tier).
  - **DOES-NOT-PORT** applies if gate (e) fails (the actual product value — `claude` cannot start
    under subscription OAuth) **or** gate (b) fails (agentic-ai never reaches the workspace at all,
    meaning the GitHub-token chain is fundamentally broken) **or** two or more of gates
    (a), (c), (d), (f) fail simultaneously with no workaround identified.

**AC2 — Framework applied against FE4-S02's actual results.**
- **Given** AC1's framework and FE4-S02's results table,
- **When** the operator walks gates (a) through (k) in order and classifies each against the
  framework,
- **Then** a running tally is recorded in this story (e.g., "10 of 11 gating-relevant gates pass;
  gate (g) failed and is excluded from the tally per ADR-003").

**AC3 — Single explicit verdict recorded.**
- **Given** AC2's tally,
- **When** the operator states the verdict,
- **Then** exactly one of **PORTS** / **PORTS-WITH-CAVEATS** / **DOES-NOT-PORT** appears in bold in
  this story's "Verdict" section, with every caveat (if any) listed as a bullet, each bullet citing
  the specific gate and the specific risk (R4/R5/R6/etc.) it corresponds to.

**AC4 — Open operator decisions are carried forward, not silently closed by the verdict.**
- **Given** R4 (sizing), R6 (HA started/stopped), FE3-S05 (`intellij_gateway`), and FE0-S05
  (`ct_sparkle_vlabel` fate) may still be unresolved at verdict time,
- **When** the verdict is written,
- **Then** it explicitly lists which of these remain open **regardless of** the verdict reached —
  the verdict does not imply any of them were resolved.

**AC5 — Verdict does not open productisation.**
- **Given** R8 and the canon's HARD RULE reserve the productisation decision for FE4-S05 alone,
- **When** the verdict is recorded,
- **Then** this story makes **no** mention of a tenancy cut, OpenMemory, or Hermes re-scoping as a
  decision — it states only the PORTS/CAVEATS/DOES-NOT-PORT call and defers "what happens next" to
  FE4-S05 in full.

## Implementation Notes

This is a judgment story, not an implementation story — no code, Terraform, or Ansible changes.
Reference §5.3 (the verdict requirement, verbatim), ADR-003 (gate (g) non-gating), and the HARD
RULE distinguishing this story from FE4-S05. The framework in AC1 must be written **before** the
results are transcribed, specifically so the tiering logic cannot be reverse-engineered to fit a
preferred outcome — that ordering is itself part of the acceptance criterion, not just good practice.

```text
Verdict Decision Framework (fill in per AC1, before reading FE4-S02's results):
  PORTS               = gates a,b,c,d,e,f,h,i,j,k all PASS (g recorded, excluded from tally)
  PORTS-WITH-CAVEATS  = >=1 of {a,b,c,d,e,f,h,i,j,k} FAILs narrowly + workaround identified,
                        AND e,b are not among the failures
  DOES-NOT-PORT       = e FAILs, OR b FAILs, OR >=2 of {a,c,d,f} FAIL simultaneously
```

## Test Plan

**Pre-state:** FE4-S02 (all eleven gate results recorded) and FE4-S03 (backup confirmed) are both
`done`.

**Action sequence:**
1. Author the Verdict Decision Framework (AC1) without looking at FE4-S02's results table yet.
2. Open FE4-S02's results table; classify each gate against the framework (AC2).
3. Compute the tally; determine which tier the tally lands in.
4. Write the verdict in bold with enumerated caveats (AC3).
5. List open operator decisions untouched by this verdict (AC4).
6. Confirm no productisation language appears anywhere in this story (AC5) — grep this file for
   `tenancy`, `OpenMemory`, `Hermes` and confirm zero matches outside citations of what is explicitly
   deferred.

**Post-state checks:**
- Exactly one of the three verdict strings appears in bold, once.
- Every caveat bullet cites a specific gate letter and a specific risk ID.
- `grep -icE 'open a productisation|tenancy cut' <this file>` returns `0` real decisions (citations
  of the deferral itself are fine; a decision is not).

**Rollback:** None — this is a document. If new evidence later contradicts the verdict, it is
corrected via a dated addendum appended to this story, never a silent edit of the original verdict
line.

## Dependencies

- **Blocked by:** FE4-S02, FE4-S03.
- **Blocks:** FE4-S05 (the retrospective restates this verdict verbatim rather than re-deriving it).

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| R8 — verdict story quietly drifts into a productisation discussion | High (the single most likely failure mode, per canon) | High | AC5 is a hard, checkable gate (grep-verifiable) specifically to catch this before the story is marked done |
| Framework written to fit a pre-decided outcome | Low | High — undermines the whole PoC's credibility | AC1 requires the framework to be authored before the results are transcribed, and the Test Plan sequence enforces that order |
| R4/R6 ambiguity makes the tier boundary unclear | Medium | Medium | AC1's framework explicitly names the caveat-vs-failure boundary in advance so this story cannot stall on an undefined edge case |

## Definition of Done

- [ ] AC1–AC5 all satisfied.
- [ ] Verdict recorded in bold, exactly once, with caveats enumerated.
- [ ] Open operator decisions listed explicitly.
- [ ] No productisation decision appears in this story (grep-verified).
- [ ] Story status updated from `draft` to `done` in this file's frontmatter.
