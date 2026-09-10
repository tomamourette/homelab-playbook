---
adr: 001
title: "Unprivileged LXC (CT 167) over a Proxmox VM for the Forge PoC"
status: accepted
date: 2026-09-09
authors: tomamourette (with BMad assist)
evidence_ref: E2, E4
---

# ADR-001: Unprivileged LXC (CT 167) over a Proxmox VM for the Forge PoC

## Context

The Forge PoC needs a Proxmox guest to host Coder, Postgres 16, the Forge workspace template, and the
agentic-ai toolkit, in order to answer one question: does Forge run at all on a substrate that is not
Azure? A prior analysis, `docs/forge-reuse-and-proxmox-findings.md` (2026-07-30, `forge-platform @
e025bc5`, `agentic-ai @ ff02e19`), recommended **a QEMU VM, not an LXC**, on four grounds: privileged
blast radius, overlay2-cannot-stack-on-overlay, guest-owned swap, and two prior LXC cgroup incidents.
That document is retained, not superseded (sprint-change-proposal-2026-09-09.md §3.4) — but on this one
point, new measurement changes the answer.

## Decision

Provision the PoC on an **unprivileged LXC, CT 167 (`ct-forge-01`)**, on **pve3**, **4C/8GB/50GB**,
**Debian 13**, `features=nesting=1,keyctl=1`, `192.168.50.167` — via the established `ct-debian`
Terraform module pattern (`module "ct_forge_01"`, mirroring `ct_saply_ai`), not a Proxmox VM.

### Basis

**E2 — measured, not assumed.** On CT 250 (Debian 12, kernel 6.17.2-1-pve, Docker 29.3.1, cgroup v2), a
privileged container was measured getting full `CapEff`, but **held inside the LXC user namespace**:
host uid 0 is unmapped, no host block devices are visible inside the container, and `modprobe` fails (no
`/lib/modules` in the CT). The realistic blast radius of `privileged = true` is root **inside the LXC**,
not root on the host.

**E4 — the VM path is not simply "safer," it is broken.** `homelab-infra/terraform/modules/vm-dev`:

- Has **never been applied** — `deploy_dev_vm = false`, zero `proxmox_vm_qemu` resources in state.
- Carries **legacy flat `disk {}` blocks** written for telmate 3.0.2-rc04; the nested `disks {}` form is
  current.
- `ci_password` is **required with no default**.
- Declares `agent = 1` and a `default_ipv4_address` output, but the image ships **no qemu-guest-agent**
  → no IP is ever returned.
- The base template (VM 9000) lives on **pve1**, and `local-zfs` is per-node, so a clone onto pve3 fails.

Proxmox's own guidance to prefer a VM over an LXC is conditioned on **untrusted users, maximum
isolation, or live migration**. None of these applies to a single-operator PoC. Combined with E2, the
case for a VM collapses for this scope.

**This overturns the prior findings document's "QEMU VM, not LXC" recommendation for the substrate
choice.** Of its four supporting arguments, **two are overturned** by E2's measurement — the privileged
blast-radius concern (it terminates at the LXC user-namespace boundary, not the host) and the two prior
LXC cgroup incidents (both were escalation-surface concerns that E2 now bounds directly). **Two survive
and are carried forward as risks, not blockers**, and are owned by other artifacts: guest-owned swap (the
sizing conflict, R4 — see the PRD's open sizing decision and FE1-S01) and the overlay/ZFS question (R5 —
see [ADR-003](ADR-003-nested-docker-is-not-an-acceptance-gate.md)).

## Consequences

### Positive

- Reuses a **rehearsed, stable pattern**: `homelab-playbook/wiki/runbooks/create-project-container.md`
  (`status: stable`, last reviewed 2026-07-28) has been exercised four times already for ct:162–165.
- `dev-host-setup.yml` already installs Docker CE, Node 20 LTS, the Claude Code CLI wrapper, ruflo, and
  pyenv/Python 3.11.11 — most of the Forge host toolchain arrives for free.
- An 8 GB LXC fits the established project-CT HA envelope. The prior document's VM path assumed a
  16 GB VM, which measured capacity (pve2 ~12 GB free, 2026-07-30) would not have comfortably absorbed.
- No new isolation technology, no new backup/snapshot tooling, no new monitoring integration — the CT
  is auto-derived into `locals.all_containers` and `locals.project_container_host_map` like every other
  project container.

### Negative

- **Guest-owned swap has no clean answer inside an unprivileged LXC.** A swapfile cannot be created
  inside the container; the CT gets whatever `swap_mb` Terraform sets on the host side, and
  `modules/ct-debian` defaults that to 512 MB. This is carried forward as the R4/sizing-conflict open
  decision, explicitly required to resolve before FE1-S01.
- **Double-nested Docker on a ZFS-backed LXC rootfs is untested** (R5): the workspace's inner dockerd
  writes to `docker_volume.dockerd`, which on CT 167 lives on the outer Docker's data root, itself on the
  LXC's ZFS rootfs. One nesting level is proven across every project CT; two is not. Mitigated, not
  removed, by [ADR-003](ADR-003-nested-docker-is-not-an-acceptance-gate.md) making that gate non-gating.

### Neutral

- This decision says nothing about whether `privileged = true` is the right posture for the workspace
  container running inside CT 167 — that is [ADR-002](ADR-002-privileged-workspace-accepted-for-single-operator.md).

**Consequence to state explicitly: this decision is revisited the moment a second, less-trusted user
exists on the host.** At that point the isolation premium a VM buys (Proxmox's own stated conditions —
untrusted users, maximum isolation, live migration) stops being hypothetical, and the LXC choice should
be re-litigated rather than assumed to still hold.

## Alternatives Considered

1. **A Proxmox VM instead of an LXC** — rejected per E4: the only VM-dev module in the estate has never
   been applied and is broken in four independent, documented ways (legacy disk syntax, a required
   password with no default, no working IP discovery, and a template on the wrong node for a pve3
   clone). Fixing all four would consume more of the PoC's budget than the isolation gain justifies for
   a single operator, per E2.
2. **Running the PoC on an existing project CT** (e.g., ct-saply-ai) — rejected. It would entangle a
   working project container with an experiment that provisions a control plane, a database, and a
   reverse proxy. A disposable, purpose-built CT is the point: if the PoC fails, the outcome is one
   destroyed CT and a documented negative result, not a partially-undone change to a container something
   else depends on.
3. **Solving the four `modules/vm-dev` defects and proceeding with a VM anyway** — rejected as
   disproportionate. None of the four defects is a quick fix (the guest-agent gap alone requires a new
   base template image), and E2 already shows the isolation argument for doing so does not hold for a
   single operator.

## Validation / Exit Ramp

- **Validation:** FE1-S05 re-runs the E2 privilege measurement directly on CT 167 (Debian 13,
  `keyctl=1`) rather than assuming the CT 250 result transfers unchanged. This is marked **[I]** until
  that story completes — same kernel, same cgroup version, high expectation, not yet verified.
- **Exit ramp:** the PoC is reversible at near-zero cost — destroy CT 167, keep the documented result.
  If a future phase needs the isolation a VM provides, the `modules/vm-dev` defects from E4 would need
  fixing first regardless of when the decision is revisited; nothing about running the PoC on an LXC
  first makes that harder later.
- **Reversal trigger:** a second, less-trusted user is introduced to the host, **or** FE1-S05's
  re-measurement on CT 167 surfaces something E2 did not (e.g., host block devices becoming visible, or
  uid 0 mapping unexpectedly). Either event reopens this ADR and the VM path from E4 should be
  re-evaluated (with its four defects fixed) rather than patched around.

## References

- Sprint change proposal, `sprint-change-proposal-2026-09-09.md` — E2, E4, §3.3, §3.4.
- `homelab-playbook/wiki/runbooks/create-project-container.md`
- `docs/forge-reuse-and-proxmox-findings.md` (2026-07-30, untracked; reconciled per §3.4)
- `homelab-infra/terraform/modules/vm-dev`
- [ADR-002](ADR-002-privileged-workspace-accepted-for-single-operator.md)
- [ADR-003](ADR-003-nested-docker-is-not-an-acceptance-gate.md)
