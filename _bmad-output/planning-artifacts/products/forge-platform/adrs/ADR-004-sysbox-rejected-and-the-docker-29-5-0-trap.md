---
adr: 004
title: "Sysbox rejected; the real Docker 29.5.0 time-namespace trap"
status: accepted
date: 2026-09-09
authors: tomamourette (with BMad assist)
evidence_ref: E3
---

# ADR-004: Sysbox rejected; the real Docker 29.5.0 time-namespace trap

## Context

`coder/templates/forge/main.tf:559-566` gives a stated rationale for why the workspace runs privileged
instead of under sysbox (the mechanism that would allow unprivileged docker-in-docker): *"sysbox 0.7.0 is
incompatible with the host's Docker 29.6 (OCI `time` namespace error, nestybox/sysbox#1011) … the
alternative (pinning host Docker+containerd back) risks the host runtime."* `docs/coder/setup.md:149-156`
repeats the same framing. This ADR examines whether that framing is correct and whether sysbox should be
pursued for CT 167.

## Decision

**Reject sysbox for CT 167** on three independent grounds, none of which is the version conflict the
existing comments describe. Require a `daemon.json` flag **and** a Docker version pin in the
`forge-coder-host` Ansible role (FE2-S06) instead.

### Basis

**E3 — sysbox is rejected on three independent grounds, any one of which is sufficient:**

1. **nestybox/sysbox#1011 is still open, with no maintainer response.** There is no fix to adopt, only
   an unresolved upstream report.
2. **Sysbox inside an LXC is unsupported per the maintainer** (nestybox/sysbox#860). CT 167 is an LXC
   regardless of what runs inside it — this alone rules sysbox out independent of the Docker version.
3. **Debian 13 is absent from sysbox's distro-compatibility table.** CT 167 runs Debian 13.

**Correcting the record.** forge-platform's own code and docs blame the Docker *version*
(`main.tf:559-566`; `docs/coder/setup.md:149-156`). The real, narrower cause is that **Docker 29.5.0
enabled private time namespaces by default** (moby/moby#52326) — and the **same release** shipped the
off-switch: `{"features":{"time-namespaces":false}}` in `/etc/docker/daemon.json`. Three reporters on
nestybox/sysbox#1011 confirm the flag resolves the symptom. **Treat the daemon flag as the reliable fix.
Treat "sysbox 0.7.1 resolves it" as unverified — marked [I]** — the flag is confirmed by reporters; the
newer sysbox point release is not independently confirmed here, and grounds 1–3 above make it moot for
CT 167 regardless.

**The trap.** CT 250 — the container E2 measured privileged-Docker behavior on
([ADR-002](ADR-002-privileged-workspace-accepted-for-single-operator.md)) — runs **Docker 29.3.1**, which
is *below* the 29.5.0 behavior flip. The time-namespace bug **cannot reproduce today** on that reference
point, and **will** appear on CT 167 after its next `apt upgrade` crosses 29.5.0 — a latent, scheduled
failure, not a resolved one. Its symptom (`namespace {"time" ""} does not exist`) looks nothing like its
cause, which makes it expensive to diagnose blind on a random future maintenance day.

> **CORRECTION — 2026-09-09 (dated, appended; the paragraph above is left intact as the record of
> what was believed at authoring time).** The clause "**will** appear on CT 167 after its next
> `apt upgrade` crosses 29.5.0 — a latent, scheduled failure" is **no longer true of CT 167**, and the
> reader should not go looking for a future event that has already happened.
>
> Measured on CT 167 (`ct-forge-01`, 192.168.50.167) on 2026-09-09: `docker --version` →
> `Docker version 29.8.0, build 88096ef`. CT 167 is **already past the 29.5.0 behaviour flip**, by
> three minor versions, from the day it was provisioned — FE1-S04's `dev-host-setup.yml` installed
> Docker CE from upstream, not from a pre-29.5.0 line. The 29.5.0 crossing on this host is **history,
> not schedule**.
>
> What this changes and what it does not:
> - **The requirement is unchanged and is now load-bearing rather than precautionary.** The
>   `daemon.json` flag is not a hedge against a future upgrade on CT 167; it is the thing keeping the
>   *current* daemon usable for nested workloads. FE2-S06 landed it:
>   `/etc/docker/daemon.json` on CT 167 reads `{"features": {"time-namespaces": false}}` (verified
>   2026-09-09), and the Docker packages are pinned at 29.8.0 by the `forge-coder-host` role.
> - **The version pin's job has shifted.** It was described above as preventing "an unplanned crossing
>   of the 29.5.0 line." That crossing cannot be prevented on CT 167 because it is behind us; the pin's
>   actual job here is to stop an unattended `apt upgrade` from moving *off* a version whose behaviour
>   under the flag has been measured. The negative consequence recorded below (missed Docker security
>   updates until deliberately revisited) is unaffected.
> - **CT 250 (the E2 reference point, Docker 29.3.1) is still below the flip.** The sentence about CT
>   250 remains correct as written; only the CT 167 half of the paragraph is superseded.
> - **Nested Docker was exercised on CT 167 with the flag in place** and worked, with the inner
>   daemon's overlayfs running directly on the ZFS dataset — see FE1-S05's Implementation Evidence.
>   No `namespace {"time" ""} does not exist` error occurred.

**Required:** a `daemon.json` entry setting `{"features":{"time-namespaces":false}}`, **and** a Docker
package version pin, both delivered by the `forge-coder-host` Ansible role (FE2-S06). Neither alone is
sufficient — the flag prevents the symptom on any Docker version; the pin prevents an unplanned crossing
of the 29.5.0 line before the flag is confirmed to still be the right mitigation for whatever version
ships next.

**Consequence recorded here: the comment drift.** `main.tf:399-404` and `:559-566`,
`docs/coder/setup.md:149-156`, and roughly nine sysbox mentions across `docs/coder/orchestration-adr.md`
(including its "Current architecture (pilot)" section) all describe sysbox / unprivileged
docker-in-docker as the running architecture, when the code has run `privileged = true` since
`main.tf:566`. `docs/coder/setup.md:141-146` is the only place in the repo that states the truth. An
engineer porting this system reads the comment first and would port the wrong architecture. **FE0-S04
fixes this drift before anyone builds on it** (R1 in the risk register — low severity, high likelihood
of wasted time if left unfixed).

## Consequences

### Positive

- Closes **R2** (the Docker 29.5.0 upgrade trap) at negligible cost: one `daemon.json` key and one
  version pin, both delivered by a single Ansible role task.
- Corrects **R1** (the comment drift) so a future engineer — including whoever eventually attempts
  productisation per [ADR-006](ADR-006-hermes-openmemory-langfuse-out-of-poc-scope.md) — reads an
  accurate architecture description rather than a stale sysbox narrative.
- Keeps CT 167 off a dependency on an open, unresolved upstream issue (nestybox/sysbox#1011) with no
  committed timeline.

### Negative

- The Docker version pin means CT 167 will miss a class of Docker security updates until this decision
  is deliberately revisited — a narrower version of the very risk forge-platform's own (incorrect)
  rationale warned about for pinning to ~27.x, now scoped to "pin the current line" rather than
  "downgrade two major versions."
- Introduces one more piece of state that must be tracked deliberately (the pin itself), or it ages
  silently the same way the sysbox comments did (R1).

### Neutral

- If nestybox later confirms 0.7.1 resolves #1011 **and** adds Debian 13 to its compatibility table,
  this decision can be revisited without urgency, since the daemon-flag-plus-pin mitigation already
  works and is not blocking anything in the interim.

## Alternatives Considered

1. **Pin host Docker and containerd back to a sysbox-supported ~27.x line** — rejected. This is
   forge-platform's own prior recommendation (`docs/coder/setup.md:149-156`), and its own stated
   downside stands independent of the version-vs-flag correction: it "risks the host runtime and
   freezes Docker security updates" for a two-major-version downgrade, a materially larger cost than a
   forward pin plus a feature flag.
2. **Wait for nestybox/sysbox#1011 to be resolved upstream** — rejected. It is open with no maintainer
   response and no ETA; blocking FE2 on it would stall the entire control-plane epic indefinitely.
3. **Accept `privileged = true` instead of pursuing sysbox** — this is the path this ADR reinforces; see
   [ADR-002](ADR-002-privileged-workspace-accepted-for-single-operator.md) for the full acceptance
   rationale and revisit trigger. It is not a rejected alternative of this ADR so much as the decision
   this ADR's rejection of sysbox leaves standing.
4. **Do nothing about the Docker 29.5.0 trap and hope it doesn't surface** — rejected. The trap fires on
   an unrelated maintenance day with a confusing symptom; the fix (one `daemon.json` key, one pin) is
   cheap now and expensive to diagnose blind later.

## Validation / Exit Ramp

- **Validation:** **PARTIALLY DONE 2026-09-09.** FE2-S06 set the `daemon.json` flag and the version
  pin as part of the `forge-coder-host` role — verified on CT 167: `/etc/docker/daemon.json` =
  `{"features": {"time-namespaces": false}}`, Docker pinned at 29.8.0. FE1-S05 then exercised Docker
  functionally, including the nested case, with **no** `namespace {"time" ""}` error
  (`stories/FE1-S05-verify-privileged-docker-in-lxc.md`). FE4-S02's gate (g) is still outstanding
  (non-gating per [ADR-003](ADR-003-nested-docker-is-not-an-acceptance-gate.md), but still informative).
  See the dated correction under "The trap" above: on CT 167 the 29.5.0 flip is already in the past.
- **Exit ramp:** if sysbox becomes viable for CT 167 later (see reversal trigger below), the mitigation
  in this ADR does not need to be undone first — a future switch to sysbox for a multi-tenant host would
  simply stop relying on the `privileged = true` posture from
  [ADR-002](ADR-002-privileged-workspace-accepted-for-single-operator.md); the `daemon.json` flag and
  version pin remain independently correct regardless.
- **Reversal trigger:** (a) nestybox/sysbox#1011 closes with a maintainer-confirmed fix **and** Debian
  13 is added to sysbox's distro-compatibility table — re-evaluate sysbox for a future multi-user host;
  or (b) the pinned Docker version falls far enough behind to accumulate unpatched CVEs — revisit the
  pin-versus-security-update tradeoff on its own schedule, independent of the sysbox question.

## References

- Sprint change proposal, `sprint-change-proposal-2026-09-09.md` — E3, R1, R2.
- `coder/templates/forge/main.tf:399-404, 559-566`
- `docs/coder/setup.md:141-146, 149-156`
- `docs/coder/orchestration-adr.md`
- moby/moby#52326 (Docker 29.5.0 private time namespaces by default)
- nestybox/sysbox#1011 (open, no maintainer response); nestybox/sysbox#860 (sysbox-in-LXC unsupported)
- [ADR-002](ADR-002-privileged-workspace-accepted-for-single-operator.md)
- [ADR-003](ADR-003-nested-docker-is-not-an-acceptance-gate.md)
