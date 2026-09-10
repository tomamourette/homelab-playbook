---
adr: 006
title: "Hermes, OpenMemory, and Langfuse are out of PoC scope"
status: accepted
date: 2026-09-09
authors: tomamourette (with BMad assist)
evidence_ref: E5 (see also §3.3, R8)
---

# ADR-006: Hermes, OpenMemory, and Langfuse are out of PoC scope

## Context

Forge's Azure deployment bundles three services alongside the core Coder + Postgres + workspace stack:
**Hermes** (agent broker/sandbox), **OpenMemory** (vector-backed agent memory), and **Langfuse**
(LLM observability). The PoC's entire purpose is to answer one narrow question — does Forge run at all
on a substrate that is not Azure? — and the scope of what to include in that experiment is itself a
decision, not a default.

## Decision

**Hermes, OpenMemory, and Langfuse are explicitly out of scope for the PoC.** None is deployed to CT 167.
Each is deferred to a possible future productisation phase, and that phase may only be opened at
**FE4-S05**, not before.

### Basis

Each of the three is a design project in its own right, not a configuration change like the rest of the
Azure-substitution table (E5):

- **Hermes** needs a `sandbox.py` and a roughly 150-line broker that **do not exist today**. There is no
  partial version to stand up — it is greenfield work.
- **OpenMemory** needs a **5-file provider/auth/dimension refactor** before it can run against anything
  other than Azure-hosted infrastructure. It **cannot boot off Azure at all** in its current form.
- **Langfuse**'s pinned version is unresolved, and its v3 line would drag **ClickHouse, Redis, and
  MinIO** onto what is otherwise an 8 GB host — a footprint several times larger than everything else
  in the PoC combined.

**None of the three is needed to answer "does it port?"** Between them they carry nearly all of the
Azure coupling identified in this exercise — session pools, blob leases, Key Vault, App Configuration,
Entra-only Postgres, and the ClickHouse/Redis dependency above. Excluding them is what makes the
remaining Azure-substitution table (E5) as clean as it is: Entra OIDC → Coder password auth, Key Vault →
six empty files, ACR → local `docker build`, Caddy `on_demand_tls` → a static site block
([ADR-005](ADR-005-dns-01-wildcard-over-public-ingress.md)), and Postgres Flexible Server → local
Postgres 16 with no extensions.

## Consequences

**Postgres 16 needs no extensions.** `pgvector` is an OpenMemory requirement only; with OpenMemory out
of scope, the PoC's Postgres instance (FR-CTL-002) is a plain, unextended install.

**`/opt/coder/secrets` holds six empty files, and the mnemosyne pair is not created.** FE2-S03 creates
the directory (0700) with six empty (0600) placeholder files, honouring the empty-file-means-disabled
contract verified at `coder/templates/forge/main.tf:341-389`
(`: > "$HOME/.config/forge/openmemory.env"` and equivalents for langfuse and rollout). The
OpenMemory/Langfuse mnemosyne credential pair is deliberately **not** created, because there is no
service on the other end of it in this PoC.

**The empty-file contract is what makes this deferral cheap — and it is itself proven by gate (f).**
Gate (f) requires `~/.config/forge/openmemory.env` and `langfuse.env` to be zero-byte, the build log to
contain both "skipped" lines, and `sudo -n true` to succeed. Passing that gate is direct, end-to-end
evidence that deferring these three services does not silently break anything else in the template — the
seam (`/opt/coder/secrets/*` → `/run/secrets/*` → `~/.config/forge/*.env`) degrades gracefully exactly as
designed, rather than merely being assumed to.

### Positive

- Keeps the PoC's footprint small: an 8 GB CT, no ClickHouse/Redis/MinIO, no `pgvector`.
- Turns the empty-file contract into a genuinely tested architectural property (via gate (f)), not a
  placeholder nobody exercises.
- Avoids **R8** — scope creep from the PoC into productisation — which the risk register calls "the
  failure mode most likely to actually occur." The prior findings document independently lists 16
  decisions that belong to a platform owner, not an engineer, four of which block only the tenant
  manifest schema; none of them blocks this PoC, and this ADR keeps them from leaking in.

### Negative

- The PoC's eventual verdict (PORTS / PORTS-WITH-CAVEATS / DOES-NOT-PORT) says **nothing** about whether
  Hermes, OpenMemory, or Langfuse themselves port to a non-Azure substrate. A future productisation
  phase inherits that question in full, unreduced by any of this work.
- These three services "carry nearly all of the Azure coupling" per the PoC's own accounting — meaning
  the hardest portion of the real, eventual porting problem is deferred, not solved. The PoC answers a
  necessary question, not a sufficient one, for full productisation.

### Neutral

- This deferral is symmetric with the prior findings document's own Phase-0 scoping, which already
  excluded CI wiring and the Saply-specific leak deletions as productisation work rather than PoC work.
  This ADR extends the same scope boundary to these three services.

**Re-entry conditions: FE4-S05 is the only gate at which productisation — a tenancy cut, OpenMemory,
Hermes, or Langfuse — may be opened, and not before.** This is stated explicitly here because R8 is the
proposal's own assessment of the most likely failure mode: not a technical blocker, but scope creep from
an engineer or future session deciding mid-PoC that "while we're in here" is a good enough reason to
start one of these three. It is not.

## Alternatives Considered

1. **Include OpenMemory, dropping `pgvector` onto the local Postgres instance** — rejected. OpenMemory
   needs a 5-file provider/auth/dimension refactor before it can run off Azure at all; adding `pgvector`
   alone would not make it functional, and pursuing the refactor would turn a substrate PoC into an
   OpenMemory-porting project.
2. **Include Langfuse pinned to its current version** — rejected. The pinned version is itself
   unresolved, and the only clear path forward (v3) drags ClickHouse, Redis, and MinIO onto an 8 GB
   host — a footprint far outside anything else budgeted for the PoC.
3. **Include a stubbed form of Hermes** — rejected. There is no partial Hermes to stub; the `sandbox.py`
   and the ~150-line broker do not exist. Building a stub would itself be original design work, not a
   configuration change comparable to the rest of the E5 substitution table.
4. **Defer all three indefinitely, with no defined re-entry point** — rejected. The operator's stated
   intent (generalise Forge for companies other than Saply AI) will eventually require solving all
   three. Leaving the re-entry point undefined risks either premature creep into FE0–FE4 (R8) or the
   opposite failure — the question quietly never getting revisited at all. Naming FE4-S05 explicitly
   avoids both.

## Validation / Exit Ramp

- **Validation:** gate (f), run in FE4-S02, proves the empty-file contract holds for both
  `openmemory.env` and `langfuse.env` — zero-byte files, both "skipped" lines present in the build log,
  and `sudo -n true` succeeding. This is the cheapest available proof that deferring these three services
  does not silently break any other part of the template.
- **Exit ramp:** FE4-S05's retrospective explicitly decides whether to open a productisation phase. If
  yes, each of Hermes, OpenMemory, and Langfuse becomes its own epic-sized design effort — not a story —
  starting from the specific gaps enumerated in Basis above (Hermes's missing broker, OpenMemory's
  5-file refactor, Langfuse's version/footprint problem).
- **Reversal trigger:** FE4-S05 is reached **and** the operator explicitly decides to productise. At
  that point, and not before, this ADR is superseded by new ADRs scoping each of the three
  individually. Reaching FE4-S05 without that explicit decision does **not** reverse this ADR — per R8,
  the default outcome at FE4-S05 is to stop, unless productisation is affirmatively chosen.

## References

- Sprint change proposal, `sprint-change-proposal-2026-09-09.md` — E5, §3.3, R8, §4.2 (FE4-S05),
  §5.4.
- `coder/templates/forge/main.tf:341-389` (empty-file-means-disabled contract)
- PoC acceptance gate (f) — `sprint-change-proposal-2026-09-09.md` §5.3
- FE2-S03 (`/opt/coder/secrets` six empty files), FR-CTL-002 (Postgres 16, no extensions)
- [ADR-005](ADR-005-dns-01-wildcard-over-public-ingress.md)
