---
type: story
epic: FE2
id: FE2-S06
title: "docker daemon.json disables time-namespaces and the Docker package is version-pinned"
size: XS
priority: MUST
owner: dev
blocking: false
fr_refs: [FR-CTL-006]
nfr_refs: []
adr_refs: [ADR-004]
risk_refs: [R2]
status: done
date: 2026-09-09
---

# FE2-S06: docker daemon.json disables time-namespaces and the Docker package is version-pinned

> **BLOCKER LIFTED 2026-09-09 — banner retained for the record.** The §5.4 gate below is
> **satisfied**, verified on the facts rather than waived: `vault_forge_github_client_id` (**20**
> chars), `vault_forge_github_client_secret` (**40**), `vault_cloudflare_api_token` (53) and
> `vault_cloudflare_zone_id` are all present in `inventories/homelab/group_vars/vault.yml`, so
> FE0-S01 and FE0-S02 both exist. No secret value was read or printed.
>
> **Correction 2026-09-09 — the convention for these lengths.** The figures first written here
> (`22` / `42`) were the lengths of the **quoted YAML literals**, i.e. they counted the two
> surrounding `"` characters as part of the value. They have been corrected to the lengths of the
> **secret values themselves, unquoted**: `vault_forge_github_client_id` is **20** characters and
> `vault_forge_github_client_secret` is **40** — which is also the shape a GitHub OAuth App
> credential pair is expected to have, so the corrected figures are a sanity check on the credential,
> where the old ones quietly were not. `vault_cloudflare_api_token` is unaffected at **53** (that
> figure was already the unquoted value). **Convention, for anything that cites a secret length in
> this artifact set: lengths are of the unquoted value. Never count YAML quoting.** Length is the only
> property of these credentials that any artifact here may state; the values themselves are never
> read, printed, or echoed into a document.
>
> **Note on the retained text below — the wildcard clause is REVERSED (2026-09-09).** The quoted
> banner ends "Wildcard scope is optional; the token is not." The **token** half stands. The
> **wildcard** half does not: Coder's preview URLs are subdomain-based and
> `CODER_WILDCARD_ACCESS_URL=*.forge.bi-services.be` is live on CT 167, so the certificate must
> carry both `forge.bi-services.be` and `*.forge.bi-services.be`. See the amendment at the top of
> [ADR-005](../adrs/ADR-005-dns-01-wildcard-over-public-ingress.md). The quote itself is left
> byte-for-byte intact because it is the record of what the banner said, not a live instruction —
> which is why the sweep that annotated the other 20 story banners in place skipped this one.
>
> The original text:
>
> > **BLOCKED — do not start.** Per §5.4 of the approved proposal, nothing in FE1–FE4 begins
> > before **both** operator prerequisites exist:
> > 1. **GitHub OAuth App** → `CODER_EXTERNAL_AUTH_0_ID/TYPE/CLIENT_ID/CLIENT_SECRET` (FE0-S01).
> >    The only non-optional external credential in the whole PoC. Without it the workspace build
> >    **fails** — `data "coder_external_auth" "github"` (`coder/templates/forge/main.tf:25-27`) has
> >    no `optional = true` — and even if it did not, `forge-sync.sh` sources its token from
> >    `coder external-auth access-token github` and **silently skips its entire clone block**, so
> >    agentic-ai never lands and gates (b)–(e) are untestable.
> > 2. **Cloudflare API token**, DNS-edit scope, zone `bi-services.be` (FE0-S02). Required for
> >    **any** browser-trusted certificate — the homelab has no inbound :80/:443, so HTTP-01 is
> >    impossible, not merely inconvenient. Wildcard scope is optional; the token is not.

## User Story

As **tomamourette**, I want **`/etc/docker/daemon.json` on `ct-forge-01` carrying `{"features":{"time-namespaces":false}}` and the Docker package version-pinned rather than left to float on `apt upgrade`**, so that **the privileged docker-in-docker the Forge workspace template depends on keeps working after routine host maintenance, instead of breaking on the first unrelated `apt upgrade` that crosses the Docker 29.5.0 line**.

## Background and Context

Evidence item **E3** is the reason this story exists, and it is worth restating precisely because the failure mode is scheduled, not present. `coder/templates/forge/main.tf:559-566` and `docs/coder/setup.md:149-156` both blame sysbox's incompatibility on "the host's Docker 29.6" in general terms, but the actual mechanism is narrower and dated: **Docker 29.5.0 enabled private time namespaces by default** (moby/moby#52326), which is what produces the `OCI runtime create failed: namespace {"time" ""} does not exist` error referenced by `nestybox/sysbox#1011`. **The same 29.5.0 release shipped the fix as an off-switch**: `{"features":{"time-namespaces":false}}` in `daemon.json`. Three independent reporters on that upstream issue confirm the flag resolves it.

The trap, and the reason this is its own story rather than a footnote, is captured in **R2**: `ct-forge-01`'s eventual Docker version is unknown at story-authoring time, but the reference measurement (**CT 250**, canon E2) ran **Docker 29.3.1** — *below* the 29.5.0 behaviour flip. That means **the failure cannot reproduce today**, on a freshly provisioned host, and **will** appear the first time an unrelated `apt upgrade` on `ct-forge-01` crosses 29.5.0. The resulting symptom — a namespace error deep in an OCI runtime create call — looks nothing like its cause (a routine package upgrade), and would very plausibly be mis-diagnosed as a sysbox problem re-appearing, sending someone down the sysbox-fix rabbit hole that ADR-004 already rejected (nestybox/sysbox#1011 open with no maintainer response; sysbox-in-LXC unsupported per nestybox/sysbox#860; Debian 13 absent from sysbox's distro-compat table).

> **CORRECTION — measured on CT 167, 2026-09-09, before any change (supersedes the two
> paragraphs above).** Three of their factual claims do not hold for this host:
>
> 1. **The premise "the failure cannot reproduce today" is false here.** CT 167 does not run
>    CT 250's Docker 29.3.1. It runs **Docker 29.8.0** (`5:29.8.0-1~debian.13~trixie`), which is
>    *above* the 29.5.0 flip, and private time namespaces were **empirically active**: a throwaway
>    container reported `time:[4026536813]` against the host's `time:[4026531834]`. The trap is
>    **present, not scheduled**. Nothing was actually broken, because ADR-004 chose `privileged`
>    over sysbox and `docker run --rm hello-world` exits 0 — so the flag is a *hedge* on this
>    architecture, not a live repair. The accurate one-line statement is: **private time namespaces
>    are confirmed active on CT 167, and `daemon.json` now switches them off.**
> 2. **R2 needs restating, not just this story.** `prd.md:347` and `product-brief.md:197` both
>    describe the trap as "scheduled, not avoided" on the strength of the CT 250 measurement.
>    That wording is stale for CT 167. **Operator decision still open** (see Evidence below):
>    correct R2 in `prd.md` / `product-brief.md`, or leave the divergence recorded here only.
> 3. **The citations are wrong on both location and content.** The sysbox rationale comment in
>    `coder/templates/forge/main.tf` is at **lines 567-580**, not 559-566 (559-566 is the tail of
>    `resource "docker_image" "main"` and the head of `resource "docker_container" "workspace"`);
>    the same wrong range is repeated in `tests/acceptance.md` §3.1 (FE0-S04-AC2) and `prd.md:346`.
>    More importantly, neither file "blames sysbox on Docker 29.6 in general terms" any more:
>    `main.tf:567-577` already reads *"The actual break (found 2026-09): Docker 29.5.0 turned on
>    private time namespaces by default (moby/moby#52326)"* and `docs/coder/setup.md:150-152`
>    already reads *"it is not a broad Docker-29.6 incompatibility"*. FE0-S04's corrections appear
>    applied but uncommitted in the `repos/forge-platform` working tree. This Background describes
>    a pre-FE0-S04 state that no longer exists on disk.
>
> Separately, `coder/templates/forge/main.tf:25-27` in the banner above is off by one: the
> `data "coder_external_auth" "github"` block is **lines 26-28** (25 is a comment). Its substance
> holds — the `github` block has no `optional = true` while `azuredevops` at 32-35 does.

Two independent controls are both required, not either/or: the `daemon.json` flag makes the *current* Docker version safe regardless of when it was installed, and the version pin prevents `apt upgrade` from silently crossing behavioural lines like this one again in the future (a second-order version, whatever it turns out to be, could introduce its own new default). Per ADR-004, treat the daemon flag as the reliable, verified fix; sysbox 0.7.1 remains **unverified [I]** and is not an alternative pursued here.

## Acceptance Criteria

**AC1 — daemon.json carries the flag.**
- **Given** `ct-forge-01`'s Docker installation,
- **When** the operator runs `cat /etc/docker/daemon.json`,
- **Then** the JSON contains `"features": {"time-namespaces": false}` (merged with, not replacing, any other keys `dev-host-setup.yml` may already have set there).

**AC2 — Docker package is version-pinned.**
- **Given** `/etc/apt/preferences.d/` on `ct-forge-01`,
- **When** the operator runs `apt-cache policy docker-ce` (or the equivalent for whichever Docker package `dev-host` installs),
- **Then** a pin file exists holding the package at its currently-installed version, and `apt-get upgrade -s` (simulate) shows `docker-ce` (and `docker-ce-cli`, `containerd.io` as applicable) held, not scheduled for upgrade.

**AC3 — Daemon restarts cleanly with the new config *and the flag demonstrably takes effect*.**
- **Given** AC1 has passed,
- **When** the operator restarts dockerd and then compares a container's time-namespace inode
  against the host's,
- **Then** the daemon comes back up with no `-p err` journal entries, and the container's
  `/proc/self/ns/time` inode **equals** the host's `/proc/1/ns/time` inode.

> **AC3 was rewritten on 2026-09-09; the original wording is unusable and would have produced a
> false pass.** It asked for `docker info --format '{{json .}}' | grep -o time-namespaces`. Docker
> 29.8.0 does not surface daemon feature flags through `docker info` **at all**: verified on CT 167
> that `docker info 2>&1 | grep -ic features` returns `0` and the 57-key `docker info --format
> '{{json .}}'` payload contains no `Features` member. The grep therefore returns nothing whether
> the flag is set or not — measured *after* the fix landed, with the flag provably in effect, it
> still returned nothing. The AC's parenthetical fallback ("inspecting the daemon's reported
> feature flags via the Docker API") is equally unavailable: `/info` returns the same struct. Only
> the kernel can answer, so the check is behavioural:
>
> ```bash
> systemctl restart docker && sleep 3 && systemctl is-active --quiet docker \
>   && journalctl -u docker --since "-2 min" --no-pager -p err | tail -5
> docker run --rm alpine:3 readlink /proc/self/ns/time   # container
> readlink /proc/1/ns/time                               # host — must be the SAME inode
> ```
>
> The role asserts exactly this on **every** run (`docker-daemon: assert the container shares the
> host time namespace`), so a later daemon.json edit or an un-restarted daemon fails the play
> instead of drifting silently.

**AC4 — Verified against the actual installed version, not assumed.**
- **Given** `dev-host-setup.yml` has already installed Docker CE as part of FE1-S04,
- **When** the operator runs `docker --version` on `ct-forge-01`,
- **Then** the reported version is recorded in this story's evidence (whatever it turns out to be — do not assume it matches CT 250's 29.3.1), and if it is already ≥ 29.5.0, AC1's flag is confirmed load-bearing right now rather than merely precautionary.

**AC5 — Existing privileged workspace containers unaffected.**
- **Given** the flag change is host-daemon-wide,
- **When** any `docker run` or `docker_container` resource is created on this host after AC3 (including, later, `docker_container.workspace` from the Forge template),
- **Then** container creation is unaffected for images/workloads that do not rely on private time namespaces — this story does not change container behaviour observably, only removes a scheduled failure mode.

## Implementation Notes

**Delivered in `roles/forge-coder-host`, not `dev-host`.** The story's own notes lean toward
`dev-host` ("whichever role already owns `docker-ce` installation … is the natural place"), and
`dev-host` does own it (`roles/dev-host/tasks/main.yml:107-142`). It was rejected on blast radius
and on FE2-S01:73, which quotes proposal §2.3: *"A new `forge-coder-host` role covers coderd,
Postgres 16, Caddy, `/opt/coder/secrets`, `daemon.json`"*. Concretely:

- `dev-host-setup.yml` targets `[dev_hosts]`, which has **10** members
  (`inventories/homelab/hosts.ini:21-31`): ct-dev-homelab, ct-sparkle-cps, ct-dev-test,
  ct-isabelle, ct-quant-trading, ct-hermes-hub, ct-saply-ai, ct-crypto-quant, ct-sparkle-vlabel
  (which no longer exists) and ct-forge-01. An ungated pin there would freeze Docker on **nine
  unrelated containers**.
- `roles/dev-host/tasks/main.yml:468-471` already restarts dockerd **unconditionally on every
  run**. `forge-platform/docs/superpowers/specs/2026-06-25-forge-workspace-dev-readiness-design.md:62`
  warns that this bounces running workspaces. Putting the change in `forge-coder-host` keeps the
  restart behind a handler that fires only when `daemon.json` actually changed.

| File | Role |
|---|---|
| `roles/forge-coder-host/tasks/docker-daemon.yml` | the two controls + the standing AC3/AC5 assertion |
| `roles/forge-coder-host/templates/docker-forge.pref.j2` | the apt pin, one stanza per package |
| `roles/forge-coder-host/handlers/main.yml` | **new** `restart docker` handler |
| `roles/forge-coder-host/defaults/main.yml` | file paths, package list, pin priority, probe image |
| `roles/forge-coder-host/tasks/main.yml` | `import_tasks`, tag `forge-docker-daemon` |

```bash
cd homelab-infra/ansible
ansible-playbook playbooks/forge-coder-host.yml --limit ct-forge-01 --tags forge-docker-daemon
```

**Four defects in the story's original snippet, all of which would have failed or misfired:**

1. `docker_daemon_json_existing` **is defined nowhere in this repo** (`grep -rn 'daemon.json'
   ansible/` had zero hits before this story). The snippet would have templated `{}` and, on a host
   that *did* have a `daemon.json`, silently truncated it — the exact failure the comment warns
   against. Shipped instead: `stat` → `slurp` → `b64decode | trim | from_json` (defaulting to `{}`
   when absent **or blank**) → `combine(..., recursive=True)` → `to_nice_json`. `to_nice_json` sorts
   keys, so the bytes are stable and the second apply is `changed=0`.
2. `ansible_facts.packages['docker-ce'][0].version` is **undefined without a preceding
   `package_facts` task** — `gather_facts` does not populate it. Shipped: an explicit
   `ansible.builtin.package_facts: manager=apt` (python3-apt 3.0.0 is present on CT 167), plus an
   `assert` that every package to be pinned is actually installed.
3. The single stanza `Package: docker-ce docker-ce-cli containerd.io` / `Pin: version <docker-ce's
   version>` would have **pinned `containerd.io` to a version that does not exist**. The five
   packages `dev-host` installs do not share a version — docker-ce and docker-ce-cli are
   `5:29.8.0-1~debian.13~trixie`, containerd.io `2.3.5-1~debian.13~trixie`, docker-buildx-plugin
   `0.37.0-1~debian.13~trixie`, docker-compose-plugin `5.5.1-1~debian.13~trixie`. Shipped: **one
   stanza per package**, version read off the host at run time.
4. `notify: restart docker` had **no handler to notify**: `roles/dev-host/` has no `handlers/`
   directory and `grep -rn "restart docker" ansible/ --include=*.yml` returned nothing anywhere in
   the tree. Shipped: a `restart docker` handler in `forge-coder-host/handlers/main.yml`, plus a
   `meta: flush_handlers` **before** the verification tasks — without it the first (changing) run
   would assert against the *old* daemon, because handlers otherwise run at end of play.

**Pin mechanism.** Authored AC2 asks for `/etc/apt/preferences.d/` at `Pin-Priority: 1001`;
`tests/acceptance.md`'s derived AC3 said `apt-mark hold` "or equivalent". The `preferences.d` form
shipped, because AC2's own verify command tests for it. This is a **new pattern in the estate** —
`/etc/apt/preferences.d/` previously held only NodeSource's `nodejs`/`nsolid` (origin pins,
priority 600) and FE2-S02's `pgdg-forge.pref`, and `apt-mark showhold` is empty.

> **CORRECTED 2026-09-09 after security review — the paragraph that stood here was wrong.**
> It said ">1000 ... **outranks the security archive** ... (`forge_docker_pin_priority: 1000`
> restores that)". Both halves are false, and the same false escape hatch was written into
> `defaults/main.yml`, `README.md` and two other places in this story. The truth:
>
> * **There is no Pin-Priority that both holds the version and admits security upgrades.**
>   `man 5 apt_preferences` (read on CT 167): *"Install the highest priority version."* Every
>   archive on this host is at **500** — `500 http://security.debian.org trixie-security/main`
>   **and** `500 https://download.docker.com/linux/debian trixie/stable` — so **any** priority
>   above 500 (501, 990, 1000, 1001 alike) makes the pinned version the candidate and blocks every
>   later one, security fixes included.
> * **`>= 1000` buys downgrades, not security precedence.** The man page's only statement about
>   that band is *"P >= 1000 causes a version to be installed even if this constitutes a downgrade
>   of the package"*.
> * **The security-archive framing was wrong twice over.** `docker-ce` ships only from
>   `download.docker.com` at 500; Debian's security archive does not carry it at all, so a
>   docker-ce CVE fix was never going to arrive from there in the first place.
>
> Measured, not argued — see *Evidence → The corrected claim, verified on the host*: the role was
> applied with `-e forge_docker_pin_priority=1000` and `apt-cache policy docker-ce` still reported
> the pinned version as `Candidate`.
>
> **The reversals that actually work**, and are now what the role and the rendered pin file offer:
>
> | How | Effect |
> |---|---|
> | `forge_docker_pin_enabled: false` + re-apply the role | Removes the pin file and refreshes the apt cache. New in this fix — the role can now perform its own documented reversal |
> | `rm /etc/apt/preferences.d/docker-forge.pref && apt-get update` | Same, by hand (this was already the correct "Lift with" line in the template) |
> | `apt-mark hold docker-ce docker-ce-cli docker-ce-rootless-extras containerd.io docker-buildx-plugin docker-compose-plugin` | Blocks upgrades **just as absolutely**, but is **visible** in `apt-mark showhold`, which a `preferences.d` file is not |
>
> **The pin now has an expiry nag — no stronger claim than that.** `unattended-upgrades` is **not
> installed** on CT 167 (so the "routine `apt upgrade`" trigger is operator-driven, not automatic)
> and a `preferences.d` file never appears in `apt-mark showhold` — meaning nothing on the host
> would ever surface the staleness. The role does: `forge_docker_pin_review_date` (**2026-12-09**,
> 90 days) is asserted on every apply and the play **fails** past it, naming the two real options.
>
> Corrected 2026-09-09 (second security review), which flagged the earlier phrasing "the pin is
> bounded" as overstating the mechanism. Precisely what the assert does:
>
> * It **fails the next apply**. It does **not** remove the pin file — and because the assert runs
>   *before* the pin task, past the date the file simply stays in place while the play aborts.
> * It **only fires if someone runs the role.** An untouched host is nagged by nothing.
>
> That is a loud nag on the IaC path, not an expiry on the host. Lifting the pin remains a
> deliberate act (`forge_docker_pin_enabled: false` and re-apply).
> `forge_docker_pin_signoff` is rendered into the pin file and currently reads
> `NOT RECORDED - FE2-S06 operator_items #2 still open`, because **that sign-off has not been
> given** — see *Still open for the operator*.

## Test Plan

**Pre-state:** Docker CE already installed via `dev-host-setup.yml` (FE1-S04); `daemon.json` either absent or without the `time-namespaces` key; no apt pin on the Docker packages.

**Action sequence:**
1. Record the currently-installed Docker version (AC4).
2. Merge the `time-namespaces: false` flag into `daemon.json` (AC1).
3. Add the apt pin (AC2).
4. Restart Docker; confirm clean startup and the flag's effect (AC3).
5. Run a plain `docker run --rm hello-world` as a smoke test that ordinary container creation still works (AC5).

**Post-state checks:**
- `daemon.json` contains the flag.
- `apt-get upgrade -s` shows Docker packages held.
- `docker info` clean, no daemon errors.
- `hello-world` container runs successfully.

**Rollback:** Remove the `time-namespaces` key from `daemon.json`, remove the apt pin file, `systemctl restart docker`. Reversible with no data loss since this changes only daemon configuration, not any volume or image state.

## Dependencies

- **Blocked by:** FE1-S04 (Docker CE installed via `dev-host-setup.yml`). **Satisfied:** Docker
  29.8.0 active on CT 167; `ct-forge-01` is in `[dev_hosts]` at `inventories/homelab/hosts.ini:31`
  and `host_vars/ct-forge-01/main.yml` exists.
- **Blocked by (undeclared in the original text, but real given the chosen placement):** FE2-S01,
  which creates the `forge-coder-host` role. **Satisfied:** the role skeleton already existed when
  this story ran — FE2-S02 landed `tasks/postgres.yml` and FE2-S03 landed `tasks/secrets.yml`, so
  FE2-S06 extended it rather than creating a role ad hoc.
- **Blocks:** FE3-S06 (image build uses this same Docker daemon), FE4-S01 (first workspace create
  depends on `docker_container.workspace`'s privileged container creation succeeding on this
  daemon).
- **Ordering constraint the story does not state but needs:** FE2-S06 must land **before** FE4-S01.
  The `restart docker` handler bounces every running container, so after the first workspace exists
  this change is disruptive rather than free. The sprint order already gives this.

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| CT 167's Docker version at provisioning time is already ≥ 29.5.0, meaning the failure is live from day one rather than scheduled | **RESOLVED — this branch is the one that happened.** 29.8.0, private time namespaces measured active | Lower than feared: `privileged` (ADR-004), not sysbox, so nothing was actually broken — `hello-world` ran fine before the change | AC4 read the real version; the flag is applied and its effect measured behaviourally, not inferred |
| `daemon.json` merge overwrites keys `dev-host-setup.yml` already sets (e.g., log driver, storage driver config) | **Nil today** — the file did not exist and nothing in `ansible/` writes it | Medium if it ever does | Shipped as a real `stat` + `slurp` + `from_json` + `combine(recursive=True)`, **not** the story snippet's blind write (whose undefined `docker_daemon_json_existing` would have truncated an existing file). AC3 confirms clean restart |
| Apt pin blocks a *security* update to Docker indefinitely | **Certain while the pin exists** — not "low". Any Pin-Priority above 500 blocks every later docker-ce version, and the fixes ship from `download.docker.com` at 500. Mitigating only the *trigger*: `unattended-upgrades` is not installed on CT 167, so an upgrade is operator-driven, not automatic | Medium-high — this is the host that will run coderd, Postgres and `/opt/coder/secrets` and be published at `forge.bi-services.be` | **Bounded, not just accepted.** ~~`forge_docker_pin_priority: 1000` reverses it~~ — corrected 2026-09-09: no priority admits security upgrades. Real reversals: `forge_docker_pin_enabled: false` + re-apply, `rm` the file + `apt-get update`, or the operator-visible `apt-mark hold`. `forge_docker_pin_review_date: 2026-12-09` is asserted every apply and **fails the play** past that date, because nothing on the host would surface the staleness on its own. Operator sign-off is **still outstanding** (operator_items #2) and is rendered into the pin file as not recorded |

## Evidence (measured 2026-09-09 on CT 167 / ct-forge-01, 192.168.50.167)

### AC4 — the actual installed version, read not assumed

```
$ docker --version
Docker version 29.8.0, build 88096ef

$ apt-cache policy docker-ce
docker-ce:
  Installed: 5:29.8.0-1~debian.13~trixie
  Candidate: 5:29.8.0-1~debian.13~trixie
```

All **six** installed Docker-archive packages, read off the host with
`dpkg-query -W` before any change:

| Package | Installed version | Installed by |
|---|---|---|
| `docker-ce` | `5:29.8.0-1~debian.13~trixie` | `dev-host` |
| `docker-ce-cli` | `5:29.8.0-1~debian.13~trixie` | `dev-host` |
| `docker-ce-rootless-extras` | `5:29.8.0-1~debian.13~trixie` | **apt, as an unversioned `Recommends:` of `docker-ce`** |
| `containerd.io` | `2.3.5-1~debian.13~trixie` | `dev-host` |
| `docker-buildx-plugin` | `0.37.0-1~debian.13~trixie` | `dev-host` |
| `docker-compose-plugin` | `5.5.1-1~debian.13~trixie` | `dev-host` |

> **Six, corrected 2026-09-09 (second security review).** This table listed the
> **five** packages `dev-host` names, and so did `forge_docker_pin_packages`.
> `docker-ce-rootless-extras` was installed all along and **left unpinned at
> priority 500** — see *Evidence → The coverage gap, closed and falsified*.

**29.8.0 is above the 29.5.0 flip.** CT 250's 29.3.1 was not carried forward. What that does and
does not mean is stated in the Background correction above: private time namespaces were confirmed
**active**, but nothing was broken, because ADR-004 chose `privileged` over sysbox. Record the flag
as a hedge that is now provably in effect — **not** as a live repair — when this feeds FE4-S04's
verdict inputs.

### Pre-change baseline (the falsifiable starting point)

```
/etc/docker/daemon.json           -> ls: cannot access ...: No such file or directory
/etc/apt/preferences.d/           -> nodejs, nsolid, pgdg-forge.pref   (no docker pin)
apt-mark showhold                 -> (empty)
apt-get upgrade -s | grep -i docker -> (empty; Installed == Candidate, so "nothing scheduled"
                                       was ALREADY true and proves nothing about the pin)
container /proc/self/ns/time      -> time:[4026536813]
host      /proc/1/ns/time         -> time:[4026531834]      DIFFERENT => private time-ns ACTIVE
```

### Apply — two consecutive runs

```
$ cd homelab-infra/ansible
$ ansible-playbook playbooks/forge-coder-host.yml --limit ct-forge-01     # run 1
...
TASK [forge-coder-host : docker-daemon: merge features.time-namespaces=false into daemon.json (AC1)] ***
changed: [ct-forge-01]
TASK [forge-coder-host : docker-daemon: pin the Docker packages at their installed versions (AC2)] ***
changed: [ct-forge-01]
RUNNING HANDLER [forge-coder-host : restart docker] ****************************
changed: [ct-forge-01]
TASK [forge-coder-host : docker-daemon: assert the container shares the host time namespace (AC3)] ***
ok: [ct-forge-01] => {
    "changed": false,
    "msg": "Container and host share time namespace time:[4026531834] - the daemon.json flag is in effect, and ordinary container creation still works (AC5)."
}

PLAY RECAP *********************************************************************
ct-forge-01                : ok=32   changed=3    unreachable=0    failed=0    skipped=2    rescued=0    ignored=0

$ ansible-playbook playbooks/forge-coder-host.yml --limit ct-forge-01     # run 2
PLAY RECAP *********************************************************************
ct-forge-01                : ok=32   changed=0    unreachable=0    failed=0    skipped=1    rescued=0    ignored=0

$ ansible-playbook playbooks/forge-coder-host.yml --limit ct-forge-01 --check --diff
PLAY RECAP *********************************************************************
ct-forge-01                : ok=30   changed=0    unreachable=0    failed=0    skipped=3    rescued=0    ignored=0
```

`changed=3` on run 1 is exactly the two files plus the handler-driven daemon restart. Run 2 is
`changed=0` and the restart handler does **not** fire, which is the property that matters once
FE4-S01 has live workspaces. The skip count differs by one between the runs for a benign reason:
on run 1 `docker-daemon: read the existing daemon.json` skipped because the file did not exist yet;
on run 2 it ran. (The other skip in both runs is FE2-S02's PGDG cache refresh, which is conditional
on the source or pin having changed.) `--check --diff` reports no diff on any of the three
FE2-S06 tasks.

**Re-applied after the 2026-09-09 security fix** (corrected pin-file wording, plus the new
`forge_docker_pin_enabled` lift, review-date assert and sign-off field). Only the rendered pin file
changed; `daemon.json` did not, so the restart handler did **not** fire and no container was
bounced:

```
$ ansible-playbook playbooks/forge-coder-host.yml --limit ct-forge-01     # run 1
TASK [forge-coder-host : docker-daemon: fail once the Docker apt pin is past its review date] ***
ok: [ct-forge-01] => {
    "msg": "Docker apt pin is inside its review window (review by 2026-12-09; operator sign-off:
            NOT RECORDED - FE2-S06 operator_items #2 still open)."
}
TASK [forge-coder-host : docker-daemon: pin the Docker packages at their installed versions (AC2)] ***
changed: [ct-forge-01]
TASK [forge-coder-host : docker-daemon: assert the container shares the host time namespace (AC3)] ***
ok: [ct-forge-01] => {
    "msg": "Container and host share time namespace time:[4026531834] - the daemon.json flag is in
            effect, and ordinary container creation still works (AC5)."
}
PLAY RECAP *********************************************************************
ct-forge-01                : ok=33   changed=1    unreachable=0    failed=0    skipped=3

$ ansible-playbook playbooks/forge-coder-host.yml --limit ct-forge-01     # run 2
ct-forge-01                : ok=33   changed=0    unreachable=0    failed=0    skipped=3

$ ansible-playbook playbooks/forge-coder-host.yml --limit ct-forge-01 --check --diff
ct-forge-01                : ok=31   changed=0    unreachable=0    failed=0    skipped=5

$ ansible-playbook playbooks/forge-coder-host.yml --limit ct-forge-01 --tags forge-docker-daemon
ct-forge-01                : ok=13   changed=0    unreachable=0    failed=0    skipped=2
```

### AC1 — daemon.json carries the flag

```
$ jq -e '.features["time-namespaces"] == false' /etc/docker/daemon.json >/dev/null \
    && echo "flag OK mode=$(stat -c %a /etc/docker/daemon.json) keys=$(jq -r 'keys|join(",")' /etc/docker/daemon.json)"
flag OK mode=644 keys=features

$ cat /etc/docker/daemon.json
{
    "features": {
        "time-namespaces": false
    }
}
```

The merge-preservation half of AC1 is **not falsifiable on this host today** — the file did not
exist, so there was nothing to merge with, and the role created it. The merge semantics were kept
anyway for FE2-S01/S02/S05, which may add keys to the same file. The AC1 verify command as authored
also has a **shell quoting defect** (`keys=$(jq -r \"keys|join(\\\",\\\")\" ...)` fails with
`syntax error near unexpected token`); the form above is the same command with the quoting repaired
and identical semantics.

### AC2 — the packages are pinned at their installed versions

```
$ ls /etc/apt/preferences.d/ | grep -q docker && apt-cache policy docker-ce docker-ce-cli containerd.io \
    docker-buildx-plugin docker-compose-plugin | grep -E "^(docker|containerd)|1001|Installed:" \
  && [ "$(apt-get upgrade -s 2>/dev/null | grep -cE '^Inst (docker-ce|docker-ce-cli|containerd\.io|docker-buildx-plugin|docker-compose-plugin) ')" = 0 ] && echo PIN_OK
docker-ce:
  Installed: 5:29.8.0-1~debian.13~trixie
 *** 5:29.8.0-1~debian.13~trixie 1001
docker-ce-cli:
  Installed: 5:29.8.0-1~debian.13~trixie
 *** 5:29.8.0-1~debian.13~trixie 1001
containerd.io:
  Installed: 2.3.5-1~debian.13~trixie
 *** 2.3.5-1~debian.13~trixie 1001
docker-buildx-plugin:
  Installed: 0.37.0-1~debian.13~trixie
 *** 0.37.0-1~debian.13~trixie 1001
docker-compose-plugin:
  Installed: 5.5.1-1~debian.13~trixie
 *** 5.5.1-1~debian.13~trixie 1001
PIN_OK
```

Each package carries **its own** version at priority 1001. Note the AC's "nothing scheduled" half is
**vacuous on this host**: `apt-get upgrade -s | grep -i docker` was already empty before the pin
existed, because Installed == Candidate. The pin is proved by the 1001 priority lines, not by the
absence of an `Inst` line — a verifier running only `apt-get upgrade -s` would have passed AC2 with
no pin file at all.

**A second defect in the AC's own command, found 2026-09-09 and left as-authored.** The verify
command names **five** packages, so it went green while `docker-ce-rootless-extras` sat unpinned at
500 — it could not have caught the coverage gap. Run verbatim above (`PIN_OK`, exit 0) and again
extended to all six installed Docker-archive packages:

```
$ ssh root@192.168.50.167 'apt-cache policy docker-ce docker-ce-cli docker-ce-rootless-extras \
    containerd.io docker-buildx-plugin docker-compose-plugin | grep -E "^(docker|containerd)|1001|Installed:"'
docker-ce:                  Installed 5:29.8.0-1~debian.13~trixie   *** 1001
docker-ce-cli:              Installed 5:29.8.0-1~debian.13~trixie   *** 1001
docker-ce-rootless-extras:  Installed 5:29.8.0-1~debian.13~trixie   *** 1001   <- was 500
containerd.io:              Installed 2.3.5-1~debian.13~trixie      *** 1001
docker-buildx-plugin:       Installed 0.37.0-1~debian.13~trixie     *** 1001
docker-compose-plugin:      Installed 5.5.1-1~debian.13~trixie      *** 1001

$ ssh root@192.168.50.167 'grep -c "^Package:" /etc/apt/preferences.d/docker-forge.pref'
6

# every Docker-archive package that is installed, and the priority of its installed version:
containerd.io             installed_priority=1001
docker-buildx-plugin      installed_priority=1001
docker-ce                 installed_priority=1001
docker-ce-cli             installed_priority=1001
docker-ce-rootless-extras installed_priority=1001
docker-compose-plugin     installed_priority=1001
```

**Zero installed Docker-archive packages remain at 500.** The AC text itself is not silently
rewritten — amending it to name six packages is a story change for the operator, the same treatment
AC1's shell-quoting defect got. The role does not depend on the AC command being right: its own
coverage assert derives the list from apt.

### The corrected claim, verified on the host (security-review fix, 2026-09-09)

An independent security review found that the pin **works** but that the *reversal path* this story
documented in four places — "`forge_docker_pin_priority: 1000` lets security upgrades win" — is
**false**. Corrected in `defaults/main.yml`, `README.md`, the rendered pin file and this story, and
then falsified on the host rather than merely re-argued.

**1. The rule, from the host's own man page.** `man 5 apt_preferences` on CT 167:

```
       •   Install the highest priority version.

       P >= 1000
           causes a version to be installed even if this constitutes a downgrade of the package
```

`>= 1000` buys **downgrades**. The man page says nothing about security archives in any band.

**2. Every archive on this host is at 500** (`apt-cache policy`, CT 167):

```
 500 https://download.docker.com/linux/debian trixie/stable amd64 Packages
     release o=Docker,a=trixie,l=Docker CE,c=stable,b=amd64
 500 http://security.debian.org trixie-security/main amd64 Packages
     release v=13,o=Debian,a=stable-security,n=trixie-security,l=Debian-Security,c=main,b=amd64
```

So the story's phrase "outranks the security archive" was wrong twice over: a pin at 1000 outranks
500 exactly as hard as 1001 does, **and** `docker-ce` never comes from Debian's security archive in
the first place — every docker-ce CVE fix ships from `download.docker.com` at 500.

**3. Applied at 1000 through the role, to prove it.**

```
$ ansible-playbook playbooks/forge-coder-host.yml --limit ct-forge-01 \
    --tags forge-docker-daemon -e forge_docker_pin_priority=1000
ct-forge-01                : ok=13   changed=1    unreachable=0    failed=0    skipped=2

$ ssh root@192.168.50.167 'grep -c "Pin-Priority: 1000" /etc/apt/preferences.d/docker-forge.pref'
5
$ ssh root@192.168.50.167 'apt-cache policy docker-ce containerd.io'
docker-ce:
  Installed: 5:29.8.0-1~debian.13~trixie
  Candidate: 5:29.8.0-1~debian.13~trixie      <- STILL the pinned version
 *** 5:29.8.0-1~debian.13~trixie 1000
containerd.io:
  Installed: 2.3.5-1~debian.13~trixie
  Candidate: 2.3.5-1~debian.13~trixie
 *** 2.3.5-1~debian.13~trixie 1000
$ ssh root@192.168.50.167 'apt-cache policy docker-ce | grep -E "^ +5:" | head -3'
     5:29.7.2-1~debian.13~trixie 500
     5:29.7.1-1~debian.13~trixie 500
     5:29.7.0-1~debian.13~trixie 500
```

At 1000 the pinned version is still the candidate and all 40+ other versions are still at 500. A
future docker-ce CVE fix lands in that same archive at 500 and loses to the pin, at 1000 exactly as
at 1001. **The escape hatch offered to the operator did not exist.**

**"Other", never "newer" — measured, because two repo files had drifted to "newer".** The story text
said *other*; `defaults/main.yml` and `README.md:280` said *newer*, which is false. Counted on the
host 2026-09-09:

```
$ apt-cache madison docker-ce | wc -l
44
$ n=0; for v in $(apt-cache madison docker-ce | awk '{print $3}'); do \
    dpkg --compare-versions "$v" gt 5:29.8.0-1~debian.13~trixie && n=$((n+1)); done; echo $n
count_strictly_newer=0
```

29.8.0 is the newest Docker has published, so **every one of the other 43 is older**. The
consequence for the report: the 1000-priority run demonstrates the **mechanism** (any priority above
the 500 that every archive sits at wins), it does **not** exhibit an observed blocked security
upgrade. The future-CVE case is the same `dpkg --compare-versions` arithmetic against a version that
does not exist yet. Both repo files now say "other ... all older today". This mattered enough to fix
because it is the same documentation-integrity failure class as the finding the paragraph was
written to correct.

**4. The escape hatch that does exist, and was tested.** `forge_docker_pin_enabled: false` is new in
this fix; the role removes the pin file and refreshes the apt cache:

```
$ ansible-playbook playbooks/forge-coder-host.yml --limit ct-forge-01 \
    --tags forge-docker-daemon -e forge_docker_pin_enabled=false
TASK [docker-daemon: pin the Docker packages at their installed versions (AC2)] *** skipping
TASK [docker-daemon: lift the pin when forge_docker_pin_enabled is false]      *** changed
TASK [docker-daemon: refresh the apt cache after lifting the pin]              *** ok
ct-forge-01                : ok=13   changed=1    unreachable=0    failed=0    skipped=2

$ ssh root@192.168.50.167 'ls /etc/apt/preferences.d/'
nodejs  nsolid  pgdg-forge.pref            <- docker-forge.pref gone
$ ssh root@192.168.50.167 'apt-cache policy docker-ce containerd.io'
docker-ce:
  Installed: 5:29.8.0-1~debian.13~trixie
  Candidate: 5:29.8.0-1~debian.13~trixie
 *** 5:29.8.0-1~debian.13~trixie 500       <- back to ordinary archive priority
        100 /var/lib/dpkg/status
containerd.io:
 *** 2.3.5-1~debian.13~trixie 500
```

The drop from `1001` to `500` on the `***` line is the contrast that proves the pin was doing the
blocking. The pin was then restored to the defined state and re-applied twice (`changed=1`, then
`changed=0`).

**5. The pin now carries an expiry nag — stated at its real strength.** Nothing on CT 167 would
ever surface its staleness — `unattended-upgrades` is not installed, and a `preferences.d` file does
not appear in `apt-mark showhold` (which is empty here). So the role asserts the expiry on **every**
apply, and the success message keeps the missing sign-off visible:

```
TASK [forge-coder-host : docker-daemon: fail once the Docker apt pin is past its review date] ***
ok: [ct-forge-01] => {
    "msg": "Docker apt pin is inside its review window (review by 2026-12-09; operator sign-off:
            NOT RECORDED - FE2-S06 operator_items #2 still open)."
}
```

Proved it actually bites, in check mode so nothing changed:

```
$ ansible-playbook ... --check -e forge_docker_pin_review_date=2026-08-01
fatal: [ct-forge-01]: FAILED! => {
    "assertion": "(forge_docker_pin_review_date | string) >= (ansible_facts.date_time.date | string)",
    "evaluated_to": false,
    "msg": "The Docker apt pin on this host is past its review date (2026-08-01; today is
            2026-09-09). Since it was written it has blocked ALL docker-ce / containerd.io
            upgrades including security fixes — lowering Pin-Priority would not have changed
            that. Decide explicitly: lift it (set forge_docker_pin_enabled: false and re-apply),
            or re-review the pinned versions against Docker's security advisories and bump
            forge_docker_pin_review_date. ..."
}
ct-forge-01                : ok=7    changed=0    unreachable=0    failed=1
```

**Not fixed, because it is not mine to fix:** the operator sign-off `operator_items` #2 demands is
still not recorded. The role states that on the host rather than assuming it — see *Still open for
the operator* #4.

### The coverage gap, closed and falsified (second security review, 2026-09-09)

**The hole.** The pin held **five** packages. A **sixth Docker package was installed and unpinned**:

```
$ ssh root@192.168.50.167 'dpkg-query -W -f="${Package} ${Version} ${Status}\n" "docker*" "containerd*"'
containerd.io             2.3.5-1~debian.13~trixie    install ok installed
docker-buildx-plugin      0.37.0-1~debian.13~trixie   install ok installed
docker-ce                 5:29.8.0-1~debian.13~trixie install ok installed
docker-ce-cli             5:29.8.0-1~debian.13~trixie install ok installed
docker-ce-rootless-extras 5:29.8.0-1~debian.13~trixie install ok installed   <- NOT PINNED
docker-compose-plugin     5.5.1-1~debian.13~trixie    install ok installed

$ ssh root@192.168.50.167 'apt-cache policy docker-ce-rootless-extras | head -4'
docker-ce-rootless-extras:
  Installed: 5:29.8.0-1~debian.13~trixie
  Candidate: 5:29.8.0-1~debian.13~trixie
 *** 5:29.8.0-1~debian.13~trixie 500      <- ordinary archive priority, no 1001 line
```

Nothing version-locked it to the frozen `docker-ce`: it is an **unversioned `Recommends:`**
(`apt-cache show docker-ce` -> `Recommends: apparmor, ca-certificates, docker-ce-rootless-extras,
...`) and its own `Depends:` are only `dbus-user-session, libc6 (>= 2.34)`. When 29.9.x lands, a
routine `apt upgrade` moves rootless-extras across the release boundary while `docker-ce` stays at
29.8.0 — **precisely the silent crossing this control exists to prevent** — while the role's own
assert reassured the operator with *"All 5 Docker packages are installed"*.

**Why an explicit list was the wrong shape.** Adding a sixth entry fixes today and leaves the same
trap armed for tomorrow: `dev-host` never named rootless-extras, apt pulled it in, and the list
mirrored `dev-host`. So the role no longer trusts the list. `forge_docker_pin_coverage_check`
derives, from apt's own index, every package the Docker archive offers, intersects it with what dpkg
reports installed, and fails if any is unpinned.

**Proved the assert bites, using the exact pre-fix list** (check mode — no state change):

```
$ ansible-playbook playbooks/forge-coder-host.yml --limit ct-forge-01 --tags forge-docker-daemon --check \
    -e '{"forge_docker_pin_packages":["docker-ce","docker-ce-cli","containerd.io","docker-buildx-plugin","docker-compose-plugin"]}'
TASK [forge-coder-host : docker-daemon: assert the pin covers every installed Docker-archive package] ***
fatal: [ct-forge-01]: FAILED! => {
    "assertion": "forge_docker_pin_gap | length == 0",
    "evaluated_to": false,
    "msg": "PIN COVERAGE GAP. These packages are installed from the Docker apt archive but are NOT in
            forge_docker_pin_packages, so they sit at ordinary priority 500 while the pinned ones sit
            at 1001: docker-ce-rootless-extras. ..."
}
ct-forge-01                : ok=9    changed=0    unreachable=0    failed=1
exit=2
```

Had this assert existed, the gap could not have shipped.

**And proved it cannot pass vacuously.** An empty derivation (cleaned `/var/lib/apt/lists`) would
make the coverage comparison trivially true — the same failure class — so a separate assert requires
the derivation to have produced something first:

```
$ ansible-playbook ... --tags forge-docker-daemon --check \
    -e forge_docker_archive_lists_glob=/var/lib/apt/lists/no-such-archive_*_Packages
TASK [forge-coder-host : docker-daemon: assert the Docker archive index was actually readable] ***
fatal: [ct-forge-01]: FAILED! => {
    "assertion": "(forge_docker_archive_pkgs.stdout_lines | default([])) | length > 0",
    "evaluated_to": false,
    "msg": "Cannot check pin coverage: ... matched no readable apt index, so the set of
            Docker-archive packages could not be derived and an empty comparison would pass
            vacuously. Run `apt-get update` ..., or set forge_docker_pin_coverage_check: false to
            accept an explicitly UNCHECKED pin list."
}
ct-forge-01                : ok=8    changed=0    unreachable=0    failed=1
exit=2
```

**Passing state on the real list:**

```
TASK [forge-coder-host : docker-daemon: assert every package to be pinned is actually installed] ***
    "msg": "All 6 packages NAMED IN forge_docker_pin_packages are installed; their versions will be
            read from the host, not assumed. This checks the list, NOT its completeness — whether the
            list covers every Docker package actually installed here is a separate assert,
            immediately below."
TASK [forge-coder-host : docker-daemon: assert the Docker archive index was actually readable] ***
    "msg": "Docker apt archive offers 11 packages on this host; comparing them against what is installed."
TASK [forge-coder-host : docker-daemon: assert the pin covers every installed Docker-archive package] ***
    "msg": "Pin covers all 6 Docker-archive packages installed here (containerd.io,
            docker-buildx-plugin, docker-ce, docker-ce-cli, docker-ce-rootless-extras,
            docker-compose-plugin) — derived from apt's index, not assumed from the list."
```

The success message of the older assert was also reworded: it now says what it checked (the list)
and names what it did not (completeness), instead of implying both.

### What the expiry assert actually does — corrected downward

The README claimed **"The pin is bounded."** That overstates the mechanism, and the correction is
worth recording because the overstatement is what a future operator would rely on:

* The assert **fails the next apply**; it does **not** remove the pin file. It also runs **before**
  the pin task, so past the review date the file stays exactly as it is while the play aborts.
* It **only fires if someone runs the role.** An untouched host is nagged by nothing.

It is a loud nag on the IaC path, not an expiry on the host. `README.md` and this story now say that;
the rendered pin-file header already said only "The Ansible role FAILS after this date", which was
accurate.

### AC3 — clean restart, and the flag demonstrably in effect

```
$ systemctl restart docker && sleep 3 && systemctl is-active --quiet docker \
    && journalctl -u docker --since "-2 min" --no-pager -p err | tail -5
-- No entries --
$ ... readlink /proc/<container pid>/ns/time  vs  readlink /proc/1/ns/time
container=time:[4026531834] host=time:[4026531834]
FLAG_IN_EFFECT
```

Pre-change the same probe returned `container=time:[4026536813] host=time:[4026531834]`. The
inode moved to the host's, which is the whole change.

**Proof that the story's original AC3 command would have been a false green** — run *after* the fix
landed, with the flag provably in effect:

```
$ docker info 2>&1 | grep -ic features
0
$ docker info --format '{{json .}}' | grep -o time-namespaces
(no output)
$ systemctl is-active docker
active
```

Identical output to the pre-change state. Anyone closing AC3 on that command would have marked it
green with the flag never applied.

### AC5 — ordinary container creation unaffected

```
$ docker run --rm hello-world >/dev/null 2>&1; echo "hello-world exit=$?"; docker ps -a --format '{{.Names}} {{.Status}}'
hello-world exit=0
(no containers)
```

The second half of AC5 — *"including, later, `docker_container.workspace` from the Forge
template"* — is **forward-looking and not mechanically verifiable here**: that resource does not
exist until FE3-S06 builds the image and FE4-S01 creates the first workspace. **Carry it as a check
on FE4-S01 / gate (g), not as closed by FE2-S06.**

### Still open for the operator

1. **R2 restatement.** `prd.md:347` and `product-brief.md:197` still describe the trap as
   "scheduled, not avoided" on CT 250's 29.3.1. Divergence is recorded here; correcting those two
   files was **not** done (needs sign-off).
2. **`tests/acceptance.md` regeneration.** Stale on three counts now that this story is real:
   §5.3 still lists "FE2-S06 does not yet exist" as a known gap; §3.3 rows 299-302 carry 4
   `[derived]` ACs against the 5 authored, and derived AC2 ("pinned below/at a known-good release")
   **contradicts** authored AC2 (pinned *at* the installed version, which here is 29.8.0 — above the
   flip, not below a known-good release); §1.1 counts (FE2 = 29, total = 130) become 30 / 131. Not
   regenerated — batch it with FE1-S04/S05 and FE3-S01..S06, or do it now.
3. **ADR reference mismatch.** Frontmatter says `adr_refs: [ADR-004]`; `acceptance.md` gate (g)
   binds FR-CTL-006 to "ADR-003 (non-gating)". Both are defensible, but the story never says its FR
   feeds an explicitly **non-gating** gate, which changes how a failure here is triaged in
   FE2-S04 / FE4-S04.
4. **Pin priority — and the sign-off this story has not got.** 1001 shipped because AC2's verify
   command tests for it, and it works. What was written here before was wrong: *"it outranks the
   security archive. `forge_docker_pin_priority: 1000` ... is a one-line change if CVE currency
   should win instead."* **No priority admits security upgrades** — every archive on CT 167 is at
   500 and apt installs the highest-priority version, so 1000 blocks docker-ce CVE fixes exactly as
   hard as 1001 (verified on the host; see Evidence). `>= 1000` only additionally permits
   downgrades. **What is actually needed from you:**
   - **Sign off, or lift.** `operator_items` #2 asked you to accept that Docker misses CVE patches
     on CT 167 for the PoC's lifetime. That acceptance is **not recorded anywhere**, so the role
     renders `NOT RECORDED - FE2-S06 operator_items #2 still open` into the pin file. Set
     `forge_docker_pin_signoff: "<name>, <date>"` to accept, or `forge_docker_pin_enabled: false`
     to lift the pin (the role then removes the file and refreshes apt).
   - **Confirm the expiry.** `forge_docker_pin_review_date` defaults to **2026-12-09** (90 days).
     The role fails the play past it. Shorten, lengthen or disable
     (`forge_docker_pin_review_enforce: false`) deliberately — but note that disabling it leaves
     nothing at all watching the pin.
   - **Consider `apt-mark hold` instead.** Equally blocking, but visible in `apt-mark showhold`,
     which a `preferences.d` file is not. It would fail AC2's authored verify command as written,
     so it is a story-text change, not a silent swap.

## Definition of Done

- [x] AC1–AC5 all green and evidenced. **Caveat, stated rather than glossed:** AC1's
      merge-preservation half and AC5's `docker_container.workspace` half are not mechanically
      verifiable at this story's close — see Evidence. Everything else was measured.
- [x] `daemon.json` merge and apt pin **authored as Ansible tasks** in
      `roles/forge-coder-host/tasks/docker-daemon.yml` + `templates/docker-forge.pref.j2`, applied
      twice to CT 167 (`changed=3` then `changed=0`; and again after the 2026-09-09 security fix,
      `changed=1` then `changed=0`). *Read "committed" as "authored in the working
      tree": the operating rule for this work is working-tree changes only, never commit or push.*
- [x] Actual installed Docker version recorded: **29.8.0**, `5:29.8.0-1~debian.13~trixie`, plus the
      other four packages. CT 250's 29.3.1 was **not** carried forward.
- [x] `docker run --rm hello-world` confirmed working post-change (`exit=0`), and the role re-runs
      an equivalent container on every apply as a standing AC3/AC5 assertion.
- [x] Story status updated from `draft` to `done` in this file's frontmatter.
- [x] AC3's unusable verification command replaced with the behavioural namespace probe, with proof
      that the original returns nothing in **both** the fixed and unfixed states.
- [x] **Security-review fix, 2026-09-09.** The false reversal path
      ("`forge_docker_pin_priority: 1000` lets security upgrades win") corrected in all four places
      it was stated — `defaults/main.yml`, `README.md`, this story's Implementation Notes and its
      risk table — and replaced with the two reversals that work (`forge_docker_pin_enabled: false`
      through the role; `apt-mark hold` as the operator-visible alternative). Falsified on the host
      rather than re-argued: applied at 1000, the pinned version was still `Candidate`. The pin is
      now nagged by `forge_docker_pin_review_date` (2026-12-09), asserted on every apply and
      proved to fail the play once past. Re-applied twice: `changed=1` then `changed=0`.
- [x] **Second security-review fix, 2026-09-09.** Three defects closed.
      **(i) Coverage gap:** `docker-ce-rootless-extras` was installed and unpinned at priority 500
      (an unversioned `Recommends:` of `docker-ce`, so nothing held it to the frozen version). It is
      now pinned, and — because an explicit list goes stale silently — `forge_docker_pin_coverage_check`
      derives the installed Docker-archive package set from apt's own index on every apply and fails
      on any gap. Falsified in check mode with the exact pre-fix five-package list: the assert names
      `docker-ce-rootless-extras` and exits 2. A second assert stops an empty derivation passing
      vacuously. The older assert's success message no longer implies completeness it did not check.
      **(ii) "40+ newer versions"** in `defaults/main.yml` and `README.md:280` corrected to "40+
      other versions ... all older today"; measured `apt-cache madison docker-ce | wc -l` = 44 and
      0 strictly newer, so the 1000-priority run proves the mechanism, not an observed blocked
      upgrade. **(iii)** README's "The pin is bounded." softened to what the assert does: fails the
      next apply, leaves the file in place, and only fires if the role is run.
- [ ] **Operator:** sign off on (or lift) the Docker CVE-currency trade-off. `operator_items` #2
      asked for this and it is **not recorded**, so the role renders
      `NOT RECORDED - FE2-S06 operator_items #2 still open` into the pin file on the host and
      repeats it in every apply's task output. This is the one item the fix could not close itself.
- [ ] **Operator:** R2 restatement in `prd.md` / `product-brief.md`, and `tests/acceptance.md`
      regeneration — see "Still open for the operator" above. Not done here.
