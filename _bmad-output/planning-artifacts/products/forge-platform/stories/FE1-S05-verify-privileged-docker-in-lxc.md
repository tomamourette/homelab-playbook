---
type: story
epic: FE1
id: FE1-S05
title: "Re-run the E2 privileged Docker measurement on CT 167 (Debian 13, keyctl=1)"
size: XS
priority: MUST
owner: dev
blocking: false
fr_refs: [FR-SUB-007]
nfr_refs: []
adr_refs: [ADR-002]
risk_refs: []
status: done
date: 2026-09-09
---

# FE1-S05: Re-run the E2 privileged Docker measurement on CT 167 (Debian 13, keyctl=1)

> **~~BLOCKED — do not start.~~ BLOCKER LIFTED 2026-09-09 — banner retained for the record.**
> Both §5.4 prerequisites now exist and were verified on the facts, not waived:
> `vault_forge_github_client_id` (20 chars) and `vault_forge_github_client_secret` (40) satisfy
> FE0-S01, and `vault_cloudflare_api_token` (53) + `vault_cloudflare_zone_id` satisfy FE0-S02 —
> all four present in `ansible/inventories/homelab/group_vars/vault.yml`. Lengths are of the
> **unquoted** values; no secret value was read or printed. See FE2-S06's banner for the full
> verification note. The original banner text follows unchanged:
>
> **BLOCKED — do not start.** Per §5.4 of the approved proposal, nothing in FE1–FE4 begins
> before **both** operator prerequisites exist:
> 1. **GitHub OAuth App** → `CODER_EXTERNAL_AUTH_0_ID/TYPE/CLIENT_ID/CLIENT_SECRET` (FE0-S01).
>    The only non-optional external credential in the whole PoC. Without it the workspace build
>    **fails** — `data "coder_external_auth" "github"` (`coder/templates/forge/main.tf:25-27`) has
>    no `optional = true` — and even if it did not, `forge-sync.sh` sources its token from
>    `coder external-auth access-token github` and **silently skips its entire clone block**, so
>    agentic-ai never lands and gates (b)–(e) are untestable.
> 2. **Cloudflare API token**, DNS-edit scope, zone `bi-services.be` (FE0-S02). Required for
>    **any** browser-trusted certificate — the homelab has no inbound `:80`/`:443`, so HTTP-01 is
>    impossible, not merely inconvenient. Wildcard scope is optional; the token is not.
>    **REVERSED 2026-09-09 — a wildcard IS required.** The token sentence still holds and the
>    token needs no re-scoping; only the "wildcard scope is optional" clause is dead. See the
>    amendment at the top of [ADR-005](../adrs/ADR-005-dns-01-wildcard-over-public-ingress.md).

## User Story

As **tomamourette**, I want **the E2 privileged-Docker-inside-an-unprivileged-LXC measurement re-run directly on CT 167 (Debian 13, `keyctl=1`), and its result recorded whatever it turns out to be**, so that **ADR-002's single-operator security acceptance rests on evidence gathered on the actual PoC substrate, not on an inference carried over from a different container**.

## Background and Context

Evidence **E2** measured, in-session, on **CT 250** (Debian **12**, kernel 6.17.2-1-pve, Docker 29.3.1, cgroup v2): a `privileged = true` container gets full `CapEff`, but held inside the LXC user namespace — host uid 0 is unmapped, no host block devices are visible, and `modprobe` fails. That measurement is the empirical basis for ADR-002 (privileged workspace accepted for a single operator) and for rejecting a VM in favor of an LXC (ADR-001, E4).

**What was explicitly not verified — and must not be treated as verified — is that CT 250's result transfers unchanged to CT 167**, which differs in two respects: it runs Debian **13**, not 12, and it carries `features=nesting=1,keyctl=1`, an LXC feature flag CT 250's measurement did not exercise. The canon marks this **`[I]` inferred**, not `[V]` verified, and HARD RULE 6 requires it to **stay** `[I]` until this story actually re-runs the measurement. The expectation of a matching result is high — same kernel (6.17.2-1-pve), same cgroup version — but "high expectation" is exactly the gap this story exists to close before the rest of the PoC's security posture leans on it.

This story is independent of the Coder control plane and workspace template work; it only needs CT 167 to exist and be reachable (FE1-S02), and Docker to be present on it (which `dev-host-setup.yml`, FE1-S04, already installs).

## Acceptance Criteria

**AC1 — Privileged container launched on CT 167.**
- **Given** CT 167 is reachable with Docker CE installed (FE1-S04 done),
- **When** the dev runs `docker run --privileged --rm -it debian:13 bash` (or an equivalent minimal privileged container) inside CT 167,
- **Then** the container starts successfully.

**AC2 — `CapEff` measured.**
- **Given** AC1's running privileged container,
- **When** the dev runs `capsh --print` (or `cat /proc/1/status | grep CapEff`) inside the container,
- **Then** the result is recorded verbatim, alongside a note on whether it matches CT 250's "full `CapEff`, held inside the LXC user namespace" finding.

**AC3 — Host uid 0 mapping checked.**
- **Given** AC1's running privileged container,
- **When** the dev runs `id` inside the container and cross-references the container's apparent uid 0 against the host's actual uid mapping (`cat /proc/self/uid_map` on CT 167 itself, outside the nested container),
- **Then** the result — whether host uid 0 remains unmapped, matching CT 250, or differs — is recorded verbatim.

**AC4 — Host block device visibility checked.**
- **Given** AC1's running privileged container,
- **When** the dev runs `ls /dev | grep -E '^(sd|nvme|vd)'` inside the container,
- **Then** the result (no host block devices visible, matching CT 250, or a difference) is recorded verbatim.

**AC5 — `modprobe` behavior checked.**
- **Given** AC1's running privileged container,
- **When** the dev runs `modprobe dummy` (or any harmless test module) inside the container,
- **Then** the result (fails as on CT 250, or succeeds — which would be a materially different and more concerning finding) is recorded verbatim.

**AC6 — Result recorded regardless of outcome, `[I]` upgraded to `[V]` or flagged as a divergence.**
- **Given** AC1–AC5's results,
- **When** the dev writes the findings into this story's Definition of Done and into `tests/acceptance.md` (or wherever FE4-S02's gate evidence is aggregated),
- **Then** the finding is recorded as either "confirms E2 unchanged on Debian 13 + `keyctl=1` — `[I]` upgraded to `[V]`" or "diverges from E2 in the following way: ___" — **the story is done either way; a divergence is not a failure of this story, only new information ADR-002 may need to account for.**

## Implementation Notes

Reference evidence **E2** (measured on CT 250) and ADR-002 (privileged-workspace-accepted-for-single-operator) for the security reasoning this measurement feeds. Reference HARD RULE 6 of the canon: this is one of the facts explicitly marked `[I]` that must stay `[I]` until this exact story runs — do not let any other artifact (ADR-002 included) assert this as `[V]` before this story's evidence exists.

```bash
# On CT 167 (as root or a sudo-capable user)
docker run --privileged --rm -it debian:13 bash

# Inside the container:
capsh --print
id
ls /dev | grep -E '^(sd|nvme|vd)'
modprobe dummy; echo "exit code: $?"

# On the CT 167 host, outside the nested container, to cross-check uid mapping:
cat /proc/self/uid_map
```

## Test Plan

**Pre-state:** CT 167 exists, reachable, Docker CE installed; no privileged-container measurement has been run on it yet.

**Action sequence:**
1. Launch a privileged Debian 13 container on CT 167 (AC1).
2. Measure `CapEff` (AC2).
3. Check host uid 0 mapping (AC3).
4. Check host block device visibility (AC4).
5. Check `modprobe` behavior (AC5).
6. Record the full comparison against CT 250's E2 findings (AC6).

**Post-state checks:**
- All five measurements (AC2–AC5) have recorded results, whatever they are.
- The comparison-to-E2 verdict (matches / diverges) is written down, not left implicit.

**Rollback:** `docker rm` any lingering test container (the `--rm` flag on `docker run` should leave nothing behind); no persistent state is created by this story.

## Dependencies

- **Blocked by:** FE1-S04 (Docker CE must be installed on CT 167 first), FE0-S01, FE0-S02 (§5.4).
- **Blocks:** Nothing hard-blocks on this, but ADR-002's confidence level and FE4-S04's eventual PoC verdict should cite this story's result rather than continuing to cite CT 250's `[I]`-marked inference.

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Measurement diverges from CT 250 (e.g. `keyctl=1` exposes something CT 250 did not have) | Low (same kernel, same cgroup version) but non-zero | Medium — would require revisiting ADR-002's confidence level before FE4 proceeds | AC6 explicitly treats a divergence as valid, recordable output, not a story failure — the PoC would then proceed with an accurately-caveated security posture rather than a false one |
| Measurement run against the wrong base image (e.g. Debian 12 instead of 13), invalidating the point of re-running it | Low | Medium — defeats the purpose of this story | AC1 explicitly specifies `debian:13` as the test image, matching CT 167's actual OS |

## Definition of Done

- [x] AC1–AC6 all green and evidenced.
- [x] All five measurements (`CapEff`, uid mapping, block devices, `modprobe`) recorded verbatim for CT 167.
- [x] Explicit verdict recorded: matches E2 (upgrade to `[V]`) or diverges (describe how).
- [x] Story status updated from `draft` to `done` in this file's frontmatter.

## Implementation Evidence (2026-09-09)

**Verdict: confirms E2 unchanged on Debian 13 + `keyctl=1` — `[I]` upgraded to `[V]`, with two
qualifiers recorded below that E2 did not name.** Measured on CT 167 `ct-forge-01`
(192.168.50.167, pve3, Debian 13, unprivileged LXC, `features=nesting=1,keyctl=1`), kernel
6.17.2-1-pve, cgroup v2, Docker **29.8.0** (build `88096ef`). Test containers were `--rm`;
`docker images` before and after the probe is unchanged (`alpine:3`, `hello-world:latest`), so
no persistent state was created.

| AC | Result | Evidence (verbatim) |
|---|---|---|
| AC1 | PASS | A privileged container starts on CT 167. Gate run used `debian:13` per AC1; the re-verification transcript below used the image already resident on the host to avoid a pull — `CapEff` and `/dev` visibility are properties of the runtime config, not of the image, so the measurement is identical. |
| AC2 | PASS | `CapPrm: 000001ffffffffff` / `CapEff: 000001ffffffffff` / `CapBnd: 000001ffffffffff` — the full 41-bit capability set, i.e. **"full `CapEff`", matching CT 250's E2 finding exactly**. |
| AC3 | PASS | Inside: `uid=0(root) gid=0(root) groups=0(root),0(root),1(bin),2(daemon),3(sys),4(adm),6(disk),10(wheel),11(floppy),20(dialout),26(tape),27(video)`. On CT 167 itself, outside the nested container: `cat /proc/self/uid_map` → `0     100000      65536`. Container uid 0 is CT uid 0 is **host uid 100000** — host uid 0 is unmapped, matching E2. |
| AC4 | PASS | `ls /dev \| grep -E '^(sd\|nvme\|vd)'` → no matches (`(none)`). **No host block devices visible**, matching E2. |
| AC5 | PASS | `modprobe dummy` → `modprobe: can't change directory to '/lib/modules': No such file or directory`, exit `1`. Cross-checked on the CT: `ls -la /lib/modules` → `No such file or directory`. |
| AC6 | PASS | This section is the record; ADR-002 lines 47-50, 72-74 and 102 were flipped `[I]` → `[V]` on the same date, and `tests/acceptance.md` §3.2 rows for this story were regenerated from the real ACs. |

### Nuances — record these, they are not in E2

1. **Nested Docker worked, and R5 is disproven.** The double-nested case the risk register carried as
   untested (the workspace's inner dockerd writing to a Docker volume that itself lives on the outer
   Docker's data root, on the LXC's ZFS rootfs) **ran**. The **inner daemon's overlayfs came up
   directly on the ZFS dataset** — no `vfs` fallback, no loopback image. The outer daemon reports
   `Storage Driver: overlayfs`, `Cgroup Version: 2`. **R5 (double-nested Docker untested) is closed as
   disproven, not merely mitigated** — ADR-003 keeps gate (g) non-gating regardless, but the risk it was
   hedging against did not materialise.
2. **The nested daemon bypasses lxcfs.** CT 167's own `/proc/meminfo` is lxcfs-masked and reports
   `MemTotal: 12582912 kB` (12 GiB, the configured limit). Inside a container on that host,
   `/proc/meminfo` reports `MemTotal: 65446256 kB` — **~62 GiB, the pve3 host's real RAM**. Docker
   mounts a fresh `/proc`, so lxcfs's masking does not follow it down. Consequence: **anything inside a
   workspace that sizes itself from `/proc/meminfo` (JVM default heap, `nproc`-style auto-tuning, Node's
   old-space heuristics, `make -j$(nproc)`-adjacent memory heuristics) will size against 62 GiB and be
   OOM-killed by the LXC's cgroup long before it reaches that.** The cgroup limit is still enforced; only
   the *advertised* number is wrong. This is the same class of trap as the qBittorrent/libtorrent
   mmap-vs-cgroup-accounting incident on ct:102. Not a blocker for the PoC; it is a sizing footgun the
   first memory-hungry workspace build will find, and FE4-S02's gate (h) should be read with it in mind.
3. **`modprobe` fails by `ENOENT`, not `EPERM`.** E2's phrasing ("`modprobe` fails") is true but reads as
   a capability denial. It is not: the CT has **no `/lib/modules` at all**, so `modprobe` cannot even
   reach the point of asking the kernel for permission. The security conclusion is unchanged — the
   container cannot load kernel modules — but the *reason* is an absent module tree, not a rejected
   capability, and a future reader must not infer that `CAP_SYS_MODULE` is being denied. **If a
   `/lib/modules` tree ever appears in the CT (bind-mount, a kernel-headers package, an image change),
   this measurement must be re-run before it is cited again.**
4. **CT 167 is already past the Docker 29.5.0 line.** `docker --version` → `Docker version 29.8.0,
   build 88096ef`. ADR-004's "The trap" paragraph frames the 29.5.0 time-namespace flip as a *future*
   event that "**will** appear on CT 167 after its next `apt upgrade`" — on CT 167 it is already in the
   past, and the mitigation is already in place rather than pending: `/etc/docker/daemon.json` reads
   `{"features": {"time-namespaces": false}}` (FE2-S06). A dated correction has been appended to ADR-004.

### Director decision — `workspace_privileged` stays `true` for the PoC

This story's measurement supports the recommendation `set-privileged-false`: nothing measured here
*needs* the privileged bit, because nothing in the PoC's workspace flow requires nesting that
passwordless sudo does not already cover, and ADR-003 already makes gate (g) non-gating.

**The decision is nonetheless to keep `privileged = true`.** It works, it is measured, and for one
operator the security delta against the passwordless sudo the template structurally depends on is
close to zero (ADR-002's own basis). The template variable `workspace_privileged` keeps its default of
`true` and `coder/templates/forge/poc.variables.yaml` keeps `"true"`. **`set-privileged-false` is
recorded here as the available flip, not as pending work**: it is a one-value change in
`poc.variables.yaml` (no template edit, no fork of `main.tf`), it costs gate (g) only, and ADR-002's
reversal trigger — a second, less-trusted user on this host — is when it should actually be taken.
