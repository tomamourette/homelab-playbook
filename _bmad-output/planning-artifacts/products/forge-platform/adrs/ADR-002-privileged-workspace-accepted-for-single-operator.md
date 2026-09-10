---
adr: 002
title: "privileged = true for workspace containers accepted for a single operator"
status: accepted
date: 2026-09-09
authors: tomamourette (with BMad assist)
evidence_ref: E2
---

# ADR-002: `privileged = true` for workspace containers accepted for a single operator

## Context

The Forge Coder template runs each developer workspace as a Docker container with `privileged = true`
(`coder/templates/forge/main.tf:566`) so the workspace's inner dockerd can run docker-in-docker. This sits
inside [ADR-001](ADR-001-lxc-over-vm-for-forge-poc.md)'s unprivileged LXC (CT 167): a privileged
*container* inside an unprivileged *LXC*. The question this ADR answers is narrower than ADR-001's
substrate choice: given the LXC is already decided, is `privileged = true` for the workspace an
acceptable security posture, or should the template be changed to `privileged = false`?

## Decision

Accept `privileged = true` for Forge workspace containers on CT 167, **for a single operator**, with an
explicit, written revisit trigger.

### Basis

E2's measurement on CT 250 (Debian 12, kernel 6.17.2-1-pve, Docker 29.3.1, cgroup v2) is the evidence:
the privileged container gets full `CapEff`, but that capability set is **held inside the LXC user
namespace** — host uid 0 is unmapped, no host block devices are visible from inside the container, and
`modprobe` fails (no `/lib/modules` in the CT). The realistic blast radius of `privileged = true` is
**root inside the LXC**, nothing more.

That is a privilege the workspace user **already holds**. The Forge image ships passwordless sudo, and
the template depends on it in three places (`coder/templates/forge/main.tf:341`, `:353`, `:378`, all
`sudo cat /run/secrets/*`), and `sudo -n true` is itself an acceptance criterion — gate (f) of the PoC's
success criteria requires it to succeed. For a single operator, the security delta between "workspace
container is privileged" and "workspace container has passwordless sudo to a fully capable user" is
close to zero: both terminate at the same LXC boundary.

**The cost of this decision is a future cost, not a present one.** It stops being acceptable the moment
a second, less-trusted user exists on the host — a workspace privileged relative to the LXC is a
meaningfully different risk when the LXC is shared with someone who isn't the operator. That trigger is
written here explicitly rather than left implicit in a comment, per the sprint-change-proposal's
explicit instruction to do so.

**[V] verified 2026-09-09 (was [I]).** FE1-S05 re-ran the measurement on CT 167 itself (Debian 13,
`keyctl=1`, Docker 29.8.0) and it **confirms E2 unchanged**: `CapEff: 000001ffffffffff` (full set),
`/proc/self/uid_map` on the CT = `0 100000 65536` (host uid 0 unmapped), no host block devices visible
inside the container, and `modprobe` fails. This ADR's basis is no longer conditional.

**Qualifier on `modprobe`.** The failure is `ENOENT`, **not `EPERM`**: CT 167 has no `/lib/modules`
tree at all, so `modprobe dummy` returns `can't change directory to '/lib/modules': No such file or
directory` (exit 1) and never reaches a capability check. The conclusion this ADR draws — the container
cannot load kernel modules — stands, but the mechanism is an absent module tree, not a denied
`CAP_SYS_MODULE`. **If a `/lib/modules` tree ever appears in the CT, this leg of the basis must be
re-measured before it is cited again.**

## Consequences

### Positive

- The workspace's Docker functionality (nested dockerd, gate (g)) works without needing sysbox or any
  other unprivileged-DinD mechanism — see [ADR-004](ADR-004-sysbox-rejected-and-the-docker-29-5-0-trap.md)
  for why sysbox is not an option here regardless.
- No fork of `coder/templates/forge/main.tf` is required to change the privilege model — one Terraform
  boolean stays as-is, consistent with the prior findings document's "do not fork main.tf" agreement
  (sprint-change-proposal §3.4).
- The decision is symmetric with what the operator already has via direct host/SSH access — it does not
  expand the operator's own effective privilege, only formalizes what the workspace container can do on
  its behalf.

### Negative

- This is documented security debt, not a solved problem. It masks a subtlety a future reader could
  miss: `CapEff` showing "full" does not mean host root, and without this ADR (and the comment-drift fix
  in FE0-S04) an engineer skimming the template could reasonably — and wrongly — conclude the workspace
  has real elevated capability outside the LXC.
- ~~The measurement this ADR relies on (E2) was taken on a different container (CT 250, Debian 12) than
  the one it is being applied to (CT 167, Debian 13, `keyctl=1`). Until FE1-S05 closes that gap, this
  ADR's basis carries an `[I]` marker.~~ **Closed 2026-09-09 — FE1-S05 measured it on CT 167 and the
  result matches; the marker is `[V]`.** What remains is narrower: the finding is qualified on `modprobe`
  failing by `ENOENT` (no `/lib/modules`) rather than `EPERM`, so this ADR's "the blast radius is root
  inside the LXC, nothing more" rests on the CT's module tree staying absent.

### Neutral

- This decision is independent of whether nested Docker itself is required to pass — that gating
  question belongs to [ADR-003](ADR-003-nested-docker-is-not-an-acceptance-gate.md), not this ADR.
  `privileged = true` is what makes the *attempt* possible; ADR-003 decides whether the *result* matters
  to the PoC's verdict.

## Alternatives Considered

1. **`privileged = false` for workspace containers** — rejected. It removes the ability to prove nested
   Docker (gate (g)) but does **not** remove the escalation surface that actually matters: the workspace
   user already has passwordless sudo inside the container, and the template depends on it structurally
   (`main.tf:341,353,378`; `sudo -n true` is load-bearing for gate (f)). For one operator this trade buys
   no measurable security improvement while costing a working capability (sprint-change-proposal §3.3).
2. **Sysbox for unprivileged docker-in-docker** — rejected on three independent grounds, detailed fully
   in [ADR-004](ADR-004-sysbox-rejected-and-the-docker-29-5-0-trap.md): the relevant upstream issue is
   open with no maintainer response, sysbox inside an LXC is unsupported per the maintainer, and Debian
   13 is absent from sysbox's own distro-compatibility table. Pursuing it here would block FE2
   indefinitely on an upstream dependency this PoC does not control.
3. **Move workspaces to a separate, isolated VM per developer** — rejected as out of scope for a
   single-operator PoC; this is the multi-tenant productisation shape this ADR's revisit trigger points
   toward, not a PoC-scope alternative. See [ADR-006](ADR-006-hermes-openmemory-langfuse-out-of-poc-scope.md)
   and R8 for why productisation questions are deferred to FE4-S05.

## Validation / Exit Ramp

- **Validation:** **DONE 2026-09-09 `[V]`.** FE1-S05 re-ran the E2 measurement on CT 167 itself
  (Debian 13, `keyctl=1`, Docker 29.8.0) and it confirms E2 unchanged — full `CapEff` held inside the
  LXC user namespace, host uid 0 unmapped, no host block devices, `modprobe` fails (by `ENOENT`, not
  `EPERM`). Evidence table: `stories/FE1-S05-verify-privileged-docker-in-lxc.md`, "Implementation
  Evidence (2026-09-09)". Gate (f) (`sudo -n true` succeeds) is still exercised at FE4-S02 as part of
  the full acceptance run.
- **Exit ramp:** reverting to `privileged = false` is a one-line Terraform change in
  `coder/templates/forge/main.tf`. It costs gate (g) only (already non-gating per ADR-003); nothing else
  in the template depends on the privileged boolean specifically.
- **Reversal trigger:** the moment a second, less-trusted user exists on this host. When that happens,
  re-evaluate `privileged = true` against the actual multi-tenant threat model — including re-opening the
  sysbox question if upstream has moved (see ADR-004's own reversal trigger) — before onboarding that
  user to a workspace.

## References

- Sprint change proposal, `sprint-change-proposal-2026-09-09.md` — E2, §3.3.
- `coder/templates/forge/main.tf:341,353,378,566`
- [ADR-001](ADR-001-lxc-over-vm-for-forge-poc.md)
- [ADR-003](ADR-003-nested-docker-is-not-an-acceptance-gate.md)
- [ADR-004](ADR-004-sysbox-rejected-and-the-docker-29-5-0-trap.md)
- PoC acceptance gates (f), (g) — `sprint-change-proposal-2026-09-09.md` §5.3
