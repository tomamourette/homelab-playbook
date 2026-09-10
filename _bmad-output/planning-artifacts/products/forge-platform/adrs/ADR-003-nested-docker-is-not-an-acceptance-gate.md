---
adr: 003
title: "Nested Docker inside the workspace is not an acceptance gate"
status: accepted
date: 2026-09-09
authors: tomamourette (with BMad assist)
evidence_ref: E1
---

# ADR-003: Nested Docker inside the workspace is not an acceptance gate

## Context

The Forge workspace container runs `privileged = true`
([ADR-002](ADR-002-privileged-workspace-accepted-for-single-operator.md)) specifically to support an
inner dockerd — docker-in-docker inside the workspace, inside CT 167's unprivileged LXC
([ADR-001](ADR-001-lxc-over-vm-for-forge-poc.md)). Whether that inner dockerd actually works, and
whether it *needs* to work for the PoC to succeed, are two different questions. This ADR answers the
second: is `docker run --rm hello-world` inside a workspace a condition of the PoC's verdict, or merely
something worth recording?

## Decision

**Nested Docker inside the workspace is not an acceptance gate.** Gate (g) — `docker run --rm
hello-world` succeeding inside the workspace — is recorded in FE4-S02 either way, but its result does
**not** determine the PoC's PORTS / PORTS-WITH-CAVEATS / DOES-NOT-PORT verdict (FE4-S04).

### Basis

**E1 — zero automated consumers.** A grep across `repos/agentic-ai @ 87ec24a`, scoped to `skills/
hooks/ workflows/ scripts/ tests/ tools/`, for executable docker/compose/testcontainers invocations
returns exactly **three** files, and all three are **prose in BMAD templates**, not calls:
`skills/bmad-create-architecture/steps/step-06-structure.md`,
`skills/bmad-document-project/documentation-requirements.csv`, and
`skills/bmad-document-project/workflows/full-scan-instructions.md`.

The **only** docker invocation anywhere in the Coder template surface is housekeeping:
`coder/templates/forge/forge-workspace-cleanup.sh:14-26` — `docker info`, four `prune` calls, and
`docker system df`. That script tidies up after Docker; it does not depend on Docker being used for
anything.

dockerd's failure to start is **soft by construction**: `coder/templates/forge/main.tf:401-405` is
written to survive `set -e` and emits only `WARN: dockerd not ready (see /tmp/dockerd.log; needs the
sysbox runtime on the host)`. The template itself does not treat a failed dockerd as fatal.

Browser testing is not a driver for nested Docker either: Playwright and Chromium are baked **natively**
into the workspace image (`repos/forge-platform/workspace/Dockerfile:61-68`), with an in-build smoke
test. There is no containerized-browser pattern that would require dockerd to be functional.

The one documented justification for nested Docker,
`repos/forge-platform/docs/coder/orchestration-adr.md:32-33` — *"Devs need `docker compose up` for local
stacks (Postgres/Redis/Java services — 8 repos ship compose/Dockerfiles)"* — points at the **Saply AI
product repos**, which are explicitly out of scope for this PoC
([ADR-006](ADR-006-hermes-openmemory-langfuse-out-of-poc-scope.md) covers the adjacent Hermes/OpenMemory/
Langfuse deferral; the Saply product repos are a separate, likewise out-of-scope, exclusion per the
proposal's scope statement).

*Count correction, for the record:* the working figure of "231 skills" in earlier discussion does not
reproduce. `find repos/agentic-ai -name SKILL.md` returns **211**, plus **14** `.skill` archives under
`skills/`; `company-overlay` contributes **0**. This does not change E1's substance — 211 or 231, none
of them shell out to Docker.

This decision is also what keeps **R5** (double-nested Docker on a ZFS-backed LXC rootfs, untested in
this estate — see [ADR-001](ADR-001-lxc-over-vm-for-forge-poc.md)) at **low severity**: because gate (g)
is non-gating, a failure there degrades the PoC to PORTS-WITH-CAVEATS at worst, rather than ending it.

## Consequences

### Positive

- Decouples the PoC's schedule and its verdict from an untested nesting depth (R5) for a capability
  the in-scope toolkit does not actually use.
- Matches the real usage pattern measured by E1: zero automated consumers today.
- Removes any pressure to solve sysbox "properly" before FE4 in order to protect the acceptance run —
  see [ADR-004](ADR-004-sysbox-rejected-and-the-docker-29-5-0-trap.md) for why that would be
  disproportionate anyway.

### Negative

- The PoC could report PORTS or PORTS-WITH-CAVEATS while a genuinely broken capability (Docker inside
  the workspace) ships silently, if the operator later brings in-scope work that starts using nested
  Docker. Nothing in this ADR prevents that risk from resurfacing outside the PoC's frame.
- Downstream readers of the eventual verdict must understand gate (g)'s non-gating status explicitly, or
  a PASS-flavoured verdict could be misread as "Docker-in-Docker is proven" when it is not.

### Neutral

- Gate (g)'s result is still recorded per FR-KIT-003 — this ADR changes what the result *means* to the
  verdict, not whether it is measured at all.

## Alternatives Considered

1. **Make gate (g) gating (require it to pass for a PORTS verdict)** — rejected. This would tie the
   PoC's headline verdict to an untested nesting depth (R5) for a capability that E1 shows has zero
   in-scope consumers. It would also make the verdict hostage to solving sysbox
   ([ADR-004](ADR-004-sysbox-rejected-and-the-docker-29-5-0-trap.md)) or a ZFS storage-driver question
   neither of which the PoC needs to answer.
2. **Remove nested Docker from the template entirely for the PoC** — rejected. This would fork
   `coder/templates/forge/main.tf`, violating the prior findings document's "do not fork" agreement
   (sprint-change-proposal §3.4), and would remove `docker_volume.dockerd`, which exists for a real,
   documented reason (`main.tf:541-548, 585-588` — "overlay2 cannot stack on overlay"). A larger change
   than a non-gating capability warrants.
3. **Solve sysbox so nested Docker is "properly" unprivileged, then gate on it** — rejected in
   [ADR-004](ADR-004-sysbox-rejected-and-the-docker-29-5-0-trap.md) on three independent grounds. Pursuing
   it here would consume the PoC's entire risk budget answering a question the PoC does not need to ask.

## Validation / Exit Ramp

- **Validation:** FE4-S02 executes gate (g) and records the boolean result — pass or fail — alongside
  every other gate in §5.3. FE4-S04's verdict is drafted without conditioning on that result.
- **Exit ramp:** if a future in-scope repo begins shelling to Docker in its actual execution path (not
  prose, per the E1 grep), re-open this ADR and reclassify gate (g) as gating. At that point R5 would
  need to be genuinely resolved — likely requiring either a working sysbox path or a return to
  [ADR-001](ADR-001-lxc-over-vm-for-forge-poc.md)'s VM alternative for that specific workload.
- **Reversal trigger:** an automated consumer of nested Docker appears in the agentic-ai toolkit's
  actual execution path. Re-run the E1 grep (`skills/ hooks/ workflows/ scripts/ tests/ tools/` for
  executable docker/compose/testcontainers invocations) as part of the re-entry check at the start of
  any productisation phase (FE4-S05), since that is the point at which Saply-repo-adjacent, docker-using
  work would first become in-scope again.

## References

- Sprint change proposal, `sprint-change-proposal-2026-09-09.md` — E1, §3.3.
- `coder/templates/forge/main.tf:401-405, 541-548, 585-588`
- `coder/templates/forge/forge-workspace-cleanup.sh:14-26`
- `docs/coder/orchestration-adr.md:32-33`
- `workspace/Dockerfile:61-68`
- [ADR-001](ADR-001-lxc-over-vm-for-forge-poc.md) — R5
- [ADR-002](ADR-002-privileged-workspace-accepted-for-single-operator.md)
- [ADR-004](ADR-004-sysbox-rejected-and-the-docker-29-5-0-trap.md)
- PoC acceptance gate (g) — `sprint-change-proposal-2026-09-09.md` §5.3
