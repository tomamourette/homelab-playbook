---
type: story
epic: FE2
id: FE2-S01
title: "forge-coder-host Ansible role: install coderd from a checksum-verified, pinned .deb"
size: S
priority: MUST
owner: dev
blocking: false
fr_refs: [FR-CTL-001]
nfr_refs: [NFR-IAC-001]
adr_refs: []
risk_refs: []
status: done
date: 2026-09-09
---

# FE2-S01: forge-coder-host Ansible role: install coderd from a checksum-verified, pinned .deb

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
>    **any** browser-trusted certificate — the homelab has no inbound :80/:443, so HTTP-01 is
>    impossible, not merely inconvenient. Wildcard scope is optional; the token is not.
>    **REVERSED 2026-09-09 — a wildcard IS required.** The token sentence still holds and the
>    token needs no re-scoping; only the "wildcard scope is optional" clause is dead. See the
>    amendment at the top of [ADR-005](../adrs/ADR-005-dns-01-wildcard-over-public-ingress.md).

## User Story

As **tomamourette**, I want **coderd installed on `ct-forge-01` through a new `forge-coder-host` Ansible role that pins an exact `.deb` version and verifies its checksum before installing**, so that **the control plane exists in a reproducible, version-controlled form rather than as a manual `curl | sh` on a one-off host, and a rebuild of CT 167 reproduces the same coderd version**.

## Background and Context

This is the first story of FE2 (Control plane: Coder + Postgres 16 + TLS). It assumes FE1 is complete: CT 167 (`ct-forge-01`, pve3, 4C/8GB/50GB, Debian 13) exists, is registered in Terraform outputs, has HA replication to both peers, and `dev-host-setup.yml` has already run against it — meaning Docker CE, Node 20 LTS, the Claude Code CLI wrapper, ruflo, and pyenv/Python 3.11.11 are already present per the runbook (`homelab-playbook/wiki/runbooks/create-project-container.md`).

The Azure-era deployment installed coderd via `cloud-init.yaml` (`repos/forge-platform/modules/coder/cloud-init.yaml`) as a one-shot VM bootstrap — not reproducible outside that VM image, and not something this PoC should copy. Per NFR-IAC-001, all infrastructure on the homelab side is created through Terraform and Ansible roles; a hand-run install script would put coderd outside that discipline from day one. Per the sizing note in `docs/coder/setup.md` (Azure deployment installed coderd "behind Caddy (auto-TLS); Docker installed for workspaces" via cloud-init systemd units), the homelab equivalent is a proper Ansible role, `forge-coder-host`, following the pattern already established by `pve-ha-replication` and `pve-ha-rules` (canon E7).

Coder does not ship in the Debian apt repositories, so the install method is a downloaded `.deb`. Given the estate's history with unpinned upstream installs (E3's Docker 29.5.0 trap is exactly this class of failure — a "latest" install silently crossing a behavioural line), this role must pin an exact coderd version and verify its published checksum before `dpkg -i`, never `curl https://coder.dev/install.sh | sh`.

## Acceptance Criteria

> **Read the Implementation Record at the foot of this file before verifying.**
> Four statements in the ACs below are factually wrong about the shipped
> package and will produce false failures if run literally: there is no
> `coderd` binary (AC2/AC4/DoD/Test Plan — the binary is `coder`), the asset
> filename carries a `_linux` infix (AC2/Implementation Notes), `coder.service`
> is package payload rather than postinst output (AC5), and
> `/etc/coder.d/coder.env` already exists as a dpkg conffile (AC5). The
> original wording is left intact for audit; every correction is evidenced
> below.


**AC1 — Role exists with the standard shape.**
- **Given** `homelab-infra/ansible/roles/` follows the existing role layout (`defaults/main.yml`, `tasks/main.yml`, handlers as needed),
- **When** the operator runs `ansible-playbook --syntax-check` against a play that includes `forge-coder-host`,
- **Then** the syntax check passes and the role's `defaults/main.yml` exposes at minimum `coder_version`, `coder_deb_url`, and `coder_deb_sha256` as overridable variables.

**AC2 — Pinned version, no `latest`.**
- **Given** the role's `tasks/main.yml`,
- **When** the operator greps the role for the download URL,
- **Then** the URL contains an exact version string (e.g. `coder_2.x.y_amd64.deb`), never `latest`, and `coder_version` is not left at a default of `latest` in `defaults/main.yml`.

**AC3 — Checksum verified before install.**
- **Given** the role downloads the `.deb` to a temp path,
- **When** the role runs,
- **Then** it computes the file's SHA-256 and compares it against `coder_deb_sha256` using Ansible's `get_url` `checksum` parameter (or an explicit `stat` + `assert` task pair), and the play **fails** (does not proceed to `dpkg -i`) if the checksum does not match.

**AC4 — Idempotent apply.**
- **Given** coderd is already installed at the pinned version,
- **When** the operator re-runs the play against `ct-forge-01`,
- **Then** the role reports no changes (skips the download/install tasks) and `coderd --version` still reports the pinned version.

**AC5 — Service present but not yet configured to run standalone.**
- **Given** AC1–AC4 have passed,
- **When** the operator runs `systemctl status coder` on `ct-forge-01`,
- **Then** the `coder.service` unit exists (installed by the `.deb`'s postinst) — it may be inactive or failing at this point, since `/etc/coder.d/coder.env` (FE2-S04) and the database (FE2-S02) do not exist yet. This story's Definition of Done is the binary and unit installed, not the service healthy.

## Implementation Notes

Reference proposal §4.2 FE2, §2.3 (Ansible impact row: "A new `forge-coder-host` role covers coderd, Postgres 16, Caddy, `/opt/coder/secrets`, `daemon.json`" — this story covers only the coderd slice; FE2-S02, S03, S05, S06 cover the rest of that same role or sibling roles). Follow the existing role conventions used by `pve-ha-replication` / `pve-ha-rules` (canon E7) rather than inventing a new layout.

```yaml
# roles/forge-coder-host/defaults/main.yml (illustrative shape)
coder_version: "2.18.4"              # pin exactly; bump deliberately, never "latest"
coder_deb_url: "https://github.com/coder/coder/releases/download/v{{ coder_version }}/coder_{{ coder_version }}_amd64.deb"
coder_deb_sha256: "<record the published sha256 for this exact release asset>"

# roles/forge-coder-host/tasks/main.yml (illustrative shape)
- name: Download pinned coderd .deb with checksum verification
  ansible.builtin.get_url:
    url: "{{ coder_deb_url }}"
    dest: "/tmp/coder_{{ coder_version }}_amd64.deb"
    checksum: "sha256:{{ coder_deb_sha256 }}"
    mode: "0644"

- name: Install coderd
  ansible.builtin.apt:
    deb: "/tmp/coder_{{ coder_version }}_amd64.deb"
    state: present
```

Do not use `bin/coder-cli.sh` or the upstream install script — the checksum-verified `.deb` path is the requirement (FR-CTL-001), specifically because it is the pattern that survives an unattended re-provision.

## Test Plan

**Pre-state:** CT 167 exists (FE1 complete); no `coder` package installed; `coderd --version` returns "command not found".

**Action sequence:**
1. Author `roles/forge-coder-host/{defaults,tasks}/main.yml` (AC1–AC3).
2. `ansible-playbook --syntax-check` (AC1).
3. Apply the role against `ct-forge-01` in check mode first (`--check --diff`), then for real.
4. Confirm `coderd --version` matches the pin (AC2).
5. Deliberately corrupt `coder_deb_sha256` by one character and re-run; confirm the play fails before `dpkg -i` (AC3).
6. Restore the correct checksum, re-run, confirm idempotent no-op (AC4).
7. `systemctl status coder` — unit present (AC5).

**Post-state checks:**
- `dpkg -l | grep coder` shows the pinned version.
- `systemctl list-unit-files | grep coder.service` shows the unit installed.
- Re-running the play twice in a row produces zero changed tasks on the second run.

**Rollback:** `apt-get remove --purge coder` on `ct-forge-01`; no Terraform or HA state is touched by this story.

## Dependencies

- **Blocked by:** FE1-S04 (CT 167 provisioned and `dev-host-setup.yml` complete — this role assumes Debian 13 base packages and Docker are already present).
- **Blocks:** FE2-S04 (coder.env needs the `coder.service` unit this role installs), FE2-S05 (Caddy fronts this service).

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Upstream coderd release yanked or checksum unpublished for the chosen version | Low | Medium — role author must re-pin | AC2/AC3 make the pin and checksum explicit variables, easy to bump in one place |
| Role installs cleanly but `coder.service` immediately crash-loops because config is absent | Expected, not a defect | None for this story | AC5 explicitly scopes this story to "binary and unit installed," not "service healthy" — that is FE2-S02/S04's job |
| Operator later runs the upstream `install.sh` by habit, drifting the host out of the role's control | Low | Medium — reproducibility lost | Document in the role's README/comments that `install.sh` is explicitly rejected in favor of the pinned `.deb`, per FR-CTL-001 |

## Definition of Done

- [ ] AC1–AC5 all green and evidenced.
- [ ] `roles/forge-coder-host/{defaults,tasks}/main.yml` committed under `homelab-infra/ansible/`.
- [ ] `coderd --version` on `ct-forge-01` matches the pinned `coder_version`.
- [ ] Re-running the play is idempotent (zero changes on second run).
- [ ] Story status updated from `draft` to `done` in this file's frontmatter.

---

## Implementation Record — 2026-09-09

Implemented as Ansible IaC and applied to `ct-forge-01` (CT 167). Nothing was
hand-typed on the host; the only hand commands run against it were read-only
verification, and the one state change the ACs call for by hand (removing the
package for AC3's negative test) was driven through a throwaway Ansible play.
Nothing was committed or pushed.

### What landed

| Path | Change |
|---|---|
| `homelab-infra/ansible/roles/forge-coder-host/defaults/main.yml` | New `coderd package (FE2-S01)` block: `coder_version`, `coder_deb_url`, `coder_deb_sha256`, plus `forge_coder_*` cache/unit/service variables |
| `homelab-infra/ansible/roles/forge-coder-host/tasks/main.yml` | New inline FE2-S01 block (assert arch → read installed state → cache dir → `get_url` with `checksum:` → stat → `apt: deb:` → conditional `daemon_reload` → hold `coder.service` down), ahead of the existing FE2-S02/S03/S06 includes |
| `homelab-infra/ansible/roles/forge-coder-host/README.md` | New `## coderd (FE2-S01)` section — the `install.sh` rejection, the pin rationale, the cache-path decision, the idempotency guard, the no-postinst findings, and the knock-ons for FE2-S03/S04 |
| `homelab-infra/ansible/playbooks/forge-coder-host.yml` | `--tags forge-coderd` added to the usage header (the play itself already existed and already targets `ct-forge-01` only) |

The role and its playbook already existed — FE2-S02 created them — so FE2-S01
extended them rather than inventing a second role.

### The version pin: 2.36.4, and why not 2.18.4

`coder_version: "2.36.4"`, SHA-256
`dd342deb35be5ba117d86e25bfe520f0e17e72bf499882779c60f90f11554c5c`, taken from
upstream's published `coder_2.36.4_checksums.txt` and independently confirmed
by `sha256sum` over the 190,645,930-byte asset.

2.36.4 is Coder's current **stable** channel release (published 2026-09-01).
GitHub's release pointer for the repository redirects to `v2.36.4`, and its
release body opens `> ## Stable (since September 1, 2026)`. `v2.37.0` and
`v2.37.1` are newer by date but are *mainline*: their notes carry the "this is
a mainline Coder release, enterprise customers without a staging environment
should install the stable release" banner. A control plane takes stable.

The story's illustrative `2.18.4` was not taken. It is a 2024-vintage release
roughly eighteen minor versions back, while `coder/templates/forge/main.tf` —
the template FE4 must push — was authored against a mid-2026 Azure server and
uses `data.coder_workspace_owner`, `coder_script`, `coder_metadata`, ordered
`coder_parameter`s and `registry.coder.com/modules/jetbrains-gateway/coder`
v1.0.29. There is no 2.18.4 precedent anywhere in the estate to inherit: the
Azure host ran the unpinned install script, and `.github/workflows/coder-template-push.yml:23`
derives its CLI version from whatever the running server reports. Pinning
2.18.4 would ship a control plane about two years older than the template it
has to run, and the mismatch would surface at FE4, not here.

> **Operator confirmation outstanding.** No planning document names a version;
> `architecture.md:130` requires only "checksum-verified, pinned `.deb`".
> 2.36.4 is a reasoned default, not an approved one. Changing it is two lines
> in `defaults/main.yml` plus one re-apply.

### Corrections to this story's text (all measured, not inferred)

1. **There is no `coderd` binary.** `dpkg-deb --contents` on the real asset
   lists exactly four installed paths: `/etc/coder.d/coder.env`,
   `/usr/bin/coder`, `/usr/lib/systemd/system/coder.service`,
   `/usr/lib/systemd/system/coder-workspace-proxy.service`. On the installed
   host, `coderd --version` → `bash: line 1: coderd: command not found`, while
   `coder --version` → `Coder v2.36.4+10fd510`. AC2, AC4, DoD bullet 3 and Test
   Plan steps 4 and "Pre-state" must all read `coder --version`.
2. **The download URL in the Implementation Notes 404s.** The real asset name
   carries a `_linux` infix. Probed:
   `.../v2.18.4/coder_2.18.4_amd64.deb` → HTTP 404;
   `.../v2.18.4/coder_2.18.4_linux_amd64.deb` → HTTP 200. Copying the snippet
   verbatim fails on the first run.
3. **AC5 attributes `coder.service` to the wrong mechanism.** The package has
   **no postinst at all** — its control archive holds only `control`,
   `md5sums`, `conffiles` and `preinst`. Both unit files are ordinary payload.
   Consequences the role now handles: nothing runs `systemctl daemon-reload`
   (the role does, but only when the install changed), and nothing enables or
   starts the service.
4. **AC5 is wrong that `/etc/coder.d/coder.env` "does not exist yet".** The
   `.deb` ships it, non-empty (291 bytes), and declares it its *sole dpkg
   conffile*. On the host after install:
   `-rw-r--r-- 1 root root 291 Sep  1 04:53 /etc/coder.d/coder.env`. The AC's
   conclusion still holds, for a different reason: the unit is inactive because
   nothing enabled it, not because its `EnvironmentFile` is missing. In fact
   `coder.service` carries `ConditionFileNotEmpty=/etc/coder.d/coder.env`,
   which the shipped file already satisfies.
5. **A second unit ships:** `coder-workspace-proxy.service`. Anything grepping
   `systemctl list-unit-files | grep coder` and expecting one line misreads it.
6. **`bin/coder-cli.sh` (Implementation Notes) does not exist** in
   `repos/forge-platform` and never has. The pattern actually being rejected is
   real and is cited in the role README instead:
   `modules/coder/cloud-init.yaml:46` = `curl -fsSL https://coder.com/install.sh | sh`.
   The Background's `coder.dev` is also the wrong host; upstream is `coder.com`.
7. **CT 167 sizing.** Background says 4C/8GB/50GB. Measured: 6 cores, 12 GB RAM,
   4 GB swap, 80 GB root. Harmless here; stale for any FE1/FE3 sizing story that
   inherits it.

### Two defects found and fixed during implementation

**(a) `/tmp` is not a safe download destination.** The story's snippet uses
`/tmp`. On CT 167, `/usr/lib/tmpfiles.d/tmp.conf` line 11 is
`q /tmp 1777 root root 10d` and `systemd-tmpfiles-clean.timer` is active, so a
`.deb` parked there is deleted after ten days; the eleventh-day apply would
re-download 190 MB and report `changed`. AC4's back-to-back double run
structurally cannot see that, because both runs fall inside the same ten-day
window. The role caches to `/var/cache/forge-coder-host/` instead.

**(b) A version-only idempotency guard silently breaks a removed host.**
Measured on CT 167 right after `apt remove coder`:

```
dpkg -l coder                                 ->  rc  coder  2.36.4-1  amd64 ...
dpkg-query -W -f='${Version}' coder           ->  2.36.4-1     (exit status 0)
dpkg-query -W -f='${db:Status-Status}' coder  ->  config-files
command -v coder                              ->  (nothing)
test -f /usr/lib/systemd/system/coder.service ->  absent
```

A removed-but-not-purged package keeps its version and still exits 0 while the
binary and both units are gone. The first guard written for this role compared
the version alone and would have declared that host converged — silently, at
`changed=0`. It now requires `${db:Status-Status} == installed` as well.
Proven by recovery: from that `rc` state a plain re-apply reported `changed=1`
(install only; the cached `.deb` was still present and its checksum still
matched) and `coder --version` came back.

The same trap invalidates **AC3's own final assertion as written** —
`dpkg-query -W coder 2>/dev/null || echo NOT-INSTALLED | grep -q NOT-INSTALLED`
prints `coder 2.36.4-1` for a package in `rc` state, so it reports a false
failure against a correctly-aborted install. Both forms were run; the corrected
check (`dpkg -l` state column plus `command -v coder`) is the one that means
anything.

### Decision recorded: `coder.service` is held stopped and disabled

`forge_coder_service_manage: true`, `forge_coder_service_enabled: false`,
`forge_coder_service_state: "stopped"`. The package leaves it down by itself
(no postinst), but the role asserts it rather than inheriting it, because the
unit is closer to starting than the story assumes — `ConditionFileNotEmpty` is
already satisfied by the shipped conffile, and `coder server` with an empty
`CODER_PG_CONNECTION_URL` falls back to provisioning its own built-in Postgres,
which would leave real state for FE2-S04 to trip over. Disable + stop rather
than mask, so FE2-S04 flips two variables with no unmask step.

### Flags for the neighbouring stories

- **FE2-S04:** `/etc/coder.d/coder.env` is a dpkg conffile. This role's install
  task passes `dpkg_options: "force-confdef,force-confold"` (Debian's default,
  restated because it is now load-bearing) so an Ansible-managed file survives
  a future coder version bump instead of prompting or being clobbered. FE2-S04
  should template it knowing that.
- **FE2-S03:** the package's `preinst` creates a `coder` **UNIX** user
  (`uid=999`, `--system --shell /bin/false`) and appends it to `docker`
  (`groups=988(coder),991(docker)`). FE2-S03 chose `root:root 0700` for
  `/opt/coder/secrets` explicitly because no such user existed; it exists now.
  Not a defect — `coder.service` runs as `User=coder`, but the secret files are
  consumed as Docker `host_path` bind mounts performed by dockerd (root), so
  coderd never reads them itself. Worth re-checking at FE4 if that changes.
- **Traceability:** `tests/acceptance.md` §3.3 lines 273-277 map AC1-AC5 to
  FR-CTL-001 with gate `—`; no lettered gate (a)-(k) covers this story, so
  these ACs are the entire safety net. That is why the wrong-binary-name and
  wrong-URL defects above were worth writing down rather than quietly fixing.

### Evidence

```
$ ansible-playbook -i inventories/homelab/hosts.ini playbooks/forge-coder-host.yml --syntax-check
playbook: playbooks/forge-coder-host.yml                                    # rc=0  (AC1)

AC1-PASS
AC2-PASS pin=2.36.4      dpkg-query -W -f='${Version}' coder  ->  2.36.4-1
CHECKSUM-MATCHES-UPSTREAM
AC4-PASS
DoD2-PASS pin=2.36.4

# apply, run 1 (fresh host)
ct-forge-01 : ok=45  changed=3  unreachable=0  failed=0  skipped=3  rescued=0  ignored=0
    changed: cache directory, .deb download, .deb install
# apply, run 2 (back to back)
ct-forge-01 : ok=41  changed=0  unreachable=0  failed=0  skipped=7  rescued=0  ignored=0

# AC3 negative test, coder_deb_sha256 overridden to 64 zeros
TASK [forge-coder-host : Download the pinned coderd .deb and verify its published SHA-256]
fatal: [ct-forge-01]: FAILED! => "The checksum for /root/.ansible/tmp/.../tmpmdqk6p8u did not
  match 0000000000000000000000000000000000000000000000000000000000000000; it was
  dd342deb35be5ba117d86e25bfe520f0e17e72bf499882779c60f90f11554c5c."
ct-forge-01 : ok=4  changed=0  unreachable=0  failed=1  skipped=0  rescued=0  ignored=0
  -> the install task was never reached; the cached .deb was not overwritten
     (sha256 still dd342deb...); the host stayed without /usr/bin/coder.

# AC5, final state
UNIT-FILE-PRESENT
UNIT FILE     STATE    PRESET
coder.service disabled enabled
/usr/bin/coder
ii  coder  2.36.4-1  amd64  Provision development environments with infrastructure with code
inactive
   Loaded: loaded (/usr/lib/systemd/system/coder.service; disabled; preset: enabled)
   Active: inactive (dead)
-rw-r--r-- 1 root root 291 Sep  1 04:53 /etc/coder.d/coder.env

$ coder --version
Coder v2.36.4+10fd510 Tue Sep  1 01:37:18 UTC 2026
$ coderd --version
bash: line 1: coderd: command not found          # story text; not a real binary

# no Terraform or HA state touched (AC-ROLLBACK)
$ ssh root@192.168.50.203 'ha-manager status | grep -E "ct:167|quorum"'
quorum OK
service ct:167 (pve3, started)
```
