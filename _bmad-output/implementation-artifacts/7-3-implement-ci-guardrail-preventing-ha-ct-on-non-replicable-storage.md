---
status: review
epic: 7
story: 7.3
title: Implement CI guardrail preventing HA CT on non-replicable storage
---

# Story 7.3: Implement CI guardrail preventing HA CT on non-replicable storage

## User Story

As an operator, I want automated rejection of the original-incident
configuration, so that I cannot accidentally repeat it.

## Acceptance Criteria

**Given** the repo has a pre-commit / CI pipeline
**When** I add a check (Ansible playbook, shell script, or Terraform validation) that:
- Reads all CT/VM configs (via Proxmox API, SSH, or file-system fixtures)
- For each resource with `hastate` set (non-`disabled`) or a `ha` tag, verifies
  no disk/mount is on `fast-pool`, `fast-zfs`, `shared-nfs-bulk`, or
  `shared-nfs`
- Fails CI with a clear error if a violation is found
**Then** a deliberate test commit that puts an HA CT on `shared-nfs-bulk`
fails CI with the expected message
**And** a commit with the correct placement passes CI
**And** the check runs on every PR / pre-commit

## Tasks

- [x] Author core check script at
      `homelab-infra/scripts/ci/check-ha-storage-placement.py` — Python, no
      third-party deps, supports live-cluster mode (ssh to pveN) and
      `--test-mode --config-dir <dir>` for self-test.
- [x] Encode the BLOCKLIST (`fast-pool`, `fast-zfs`, `shared-nfs-bulk`,
      `shared-nfs`) with per-storage remediation hints.
- [x] Create three test fixtures in
      `homelab-infra/scripts/ci/test-cases/`: `good-ha-ct.conf`,
      `bad-ha-ct.conf`, `non-ha-ct.conf`.
- [x] Author Ansible playbook wrapper at
      `homelab-infra/ansible/playbooks/ci-checks.yml` with live/test modes,
      optional status-file write, fail-on-violation toggle.
- [x] Author GitHub Actions workflow at
      `homelab-infra/.github/workflows/ci-ha-storage-placement.yml` with a
      fixture self-test job (exercises each fixture in isolation) and a
      status-file gate job that reads `ci-status/ha-placement-status.txt`.
- [x] Document chosen delivery model (cron on pve2 + pre-commit hook + GHA
      defense-in-depth) in `homelab-infra/scripts/ci/README.md`.
- [x] Self-test: run the script against each fixture; verify
      good=PASS(rc=0), bad=FAIL(rc=1), non-ha=PASS(rc=0).
- [ ] **Operator action after review:** wire cron on pve2 and install
      pre-commit hook. DELIBERATELY NOT DONE in this story per spec.

## Dev Notes

### Why the `hastate` + `ha`-tag dual trigger

Proxmox's authoritative HA state lives in `/etc/pve/ha/resources.cfg`, not in
the per-resource `.conf`. A file-driven check that only parsed the per-VMID
config would miss HA resources whose flag is set entirely from the HA manager.
Two mitigations, both implemented:

1. The check reads a `hastate: <state>` line when present — some operators and
   tooling materialize it into the per-resource config for visibility, and it
   is a natural place to express HA intent in fixtures.
2. The `ha` token in `tags:` is treated as an equivalent intent signal. This
   is the durable, operator-controlled marker that survives HA-manager
   operations and is easy to grep for.

The long-term intent (documented in the README's "Maintaining the blocklist"
section) is that every HA-managed resource also carries the `ha` tag so the
grep path is sufficient even if `hastate` is never persisted in the per-VMID
file. A follow-up polish story can enforce "HA-managed → must have `ha` tag"
by cross-reading `ha-manager status` and failing if a resource has `hastate`
without the tag.

### Why Python, not Bash

The parse of disk lines (`rootfs`/`mp[0-9]+`/`scsi[0-9]+`/`virtio[0-9]+`/
`ide[0-9]+`/`sata[0-9]+`/`efidisk[0-9]+`/`tpmstate[0-9]+`) plus storage-id
extraction plus snapshot-section skipping is awkward in shell and very clear
in Python with re. Standard library only — no external deps, no venv. The
existing `scripts/audit-dns-consistency.py` set the pattern.

### Snapshot-section handling

Proxmox writes snapshot configs into the same file under `[<snapname>]`
headers. Those sections describe historical state, not what the live resource
runs today, so the parser stops at the first `[...]` header. A violation in a
snapshot section is not a violation of the current config (though if it were
restored, the check would fire on the restored live state).

### Why cron-on-pve2 rather than pure GitHub Actions

GitHub-hosted runners cannot SSH into the homelab (no inbound path through
the NAT). The options were:

| Option | Pros | Cons |
|--------|------|------|
| Self-hosted runner on pve2 | Real-time enforcement per push | Another moving part; runner updates to manage |
| Cron on pve2 → status file in repo | Simple; no runner; works offline | Up-to-1-cycle staleness (mitigable with tight cron) |
| Pre-commit-only | Fast, local | No remote visibility for PRs from third parties |

We picked **cron on pve2 writing a status file + pre-commit hook as primary +
GHA as defense-in-depth**. The pre-commit hook catches the common case
(operator editing Terraform / Ansible locally). The cron closes the loop for
asynchronous changes (e.g. GUI-driven Proxmox config edits that never touched
the repo). The GHA workflow guards against regressions in the check script
itself (via the fixture self-test) and surfaces any stale or failing status
file on PRs.

### Deliberately NOT done

Per story spec, this story ships the code only. None of these are wired to
live systems:

- No cron file written to pve2.
- No pre-commit hook installed in `.git/hooks/` or `.pre-commit-config.yaml`.
- No push of `ci-status/ha-placement-status.txt` seeded in the repo.
- No change to the existing `.github/workflows/infra-plan.yml`.

The operator will review adversarially before activation.

## Implementation Report

### Files created

| Path | Purpose |
|------|---------|
| `homelab-infra/scripts/ci/check-ha-storage-placement.py` | Core Python check; live + test modes |
| `homelab-infra/scripts/ci/README.md` | Rule definition, blocklist maintenance, delivery model |
| `homelab-infra/scripts/ci/test-cases/good-ha-ct.conf` | HA on local-zfs → PASS fixture |
| `homelab-infra/scripts/ci/test-cases/bad-ha-ct.conf` | HA on shared-nfs-bulk → FAIL fixture |
| `homelab-infra/scripts/ci/test-cases/non-ha-ct.conf` | non-HA on fast-pool → PASS fixture |
| `homelab-infra/ansible/playbooks/ci-checks.yml` | Playbook wrapper; live/test modes; status-file writer |
| `homelab-infra/.github/workflows/ci-ha-storage-placement.yml` | Self-test + status-file gate |

### Self-test results (captured 2026-04-20)

Script invoked in `--test-mode` against each fixture in isolation:

```
===== good-ha-ct (expect PASS, exit 0) =====
Resources inspected : 1
HA-flagged resources: 1
Blocked storage IDs : fast-pool, fast-zfs, shared-nfs, shared-nfs-bulk
RESULT: PASS — no HA resources on non-replicable storage.
EXIT=0

===== bad-ha-ct (expect FAIL, exit 1) =====
Resources inspected : 1
HA-flagged resources: 1
Blocked storage IDs : fast-pool, fast-zfs, shared-nfs, shared-nfs-bulk
RESULT: FAIL — 1 violation(s) found.
  X lxc:bad-ha-ct [tag: ha]
      source   : <test-dir>/bad-ha-ct.conf
      disk     : rootfs = shared-nfs-bulk:199/vm-199-disk-0.raw,size=20G
      storage  : shared-nfs-bulk  (BLOCKED)
      fix      : shared-nfs-bulk is NFS-exported from pve3's hdd-pool — single source.
                 Safe for non-HA bulk data (media, dumps). For HA workloads, move
                 disks to local-zfs on each node with replication.
EXIT=1

===== non-ha-ct (expect PASS, exit 0) =====
Resources inspected : 1
HA-flagged resources: 0
Blocked storage IDs : fast-pool, fast-zfs, shared-nfs, shared-nfs-bulk
RESULT: PASS — no HA resources on non-replicable storage.
EXIT=0
```

All three fixtures produced the expected result. Exit codes match the
contract documented in README / script docstring.

### Edge cases for reviewer scrutiny

1. **HA detection trigger symmetry.** The check treats `hastate: <anything
   except 'disabled'>` OR a `tags:` containing `ha`/`ha=1`/`ha-true` as
   HA-enabled. This is a UNION — a resource with either marker is flagged.
   Reviewer should confirm this matches operator expectation; alternative is
   AND (stricter) which would miss any resource where only one marker is set.
2. **Authoritative HA source is `/etc/pve/ha/resources.cfg`.** Neither
   per-VMID config file is the ground truth. The check compensates via the
   `ha` tag convention, but a resource added to HA via the GUI without the
   tag would evade detection. Mitigation: README notes a follow-up story to
   cross-read `ha-manager status` directly.
3. **`shared-nfs` vs `shared-nfs-bulk` both in blocklist.** Retained both so
   stale/rollback configs during migration can't silently re-introduce the
   original incident. After a clean post-migration state, `shared-nfs` can be
   removed from the list — but leaving it is belt-and-braces.
4. **Snapshot sections.** Parser skips lines after the first `[snapname]`
   header. If a snapshot's config were restored, the check would re-fire on
   the new live state; that is correct behavior.
5. **Disk values without a `:` separator.** e.g. pass-through like
   `/dev/disk/by-id/...`. `storage_id` is None and the line is ignored. That
   is correct — no Proxmox-managed storage to classify. Reviewer should
   confirm no production CT passes through whole-disk HDDs labelled with a
   blocklist string accidentally.
6. **Storage-ID regex strictness.** Accepts `[A-Za-z0-9][A-Za-z0-9_.\-]*`
   before the colon. Proxmox allows a slightly broader set (e.g. colon in
   CIFS volume paths? — no, those are escaped). Edge: a storage named
   `fast-pool-staging` would NOT match `fast-pool` — intentional (substring
   match would be dangerous) but worth calling out.
7. **GHA status-file gate is permissive when the file is missing.** This is
   deliberate: before the cron-on-pve2 is wired, there IS no status file,
   and failing PRs on that alone would brick development. The pre-commit
   hook is the real enforcement during that transition.
8. **Ansible `ha_check_status_file` default is empty string.** Writing is
   opt-in. When `-e ha_check_status_file=…` is not passed, no file is
   written — this keeps the playbook safe to run ad-hoc without touching
   shared paths.

### Not wired up (operator will review + activate)

- Cron on pve3 (no change under `/etc/cron.d/` on any node). **Host moved
  from pve2 → pve3** during adversarial fixes because pve2 is being
  reinstalled in Epic 5.
- Pre-commit hook in `.git/hooks/pre-commit` or `.pre-commit-config.yaml`.
- `ci-status/` directory in the repo.

## Post-adversarial fixes (2026-04-20)

An adversarial review of the story's review-state artifacts surfaced ten
gaps. All ten were fixed; self-test re-run shows each fixture produces the
documented outcome.

### Fix list

1. **Read `/etc/pve/ha/resources.cfg` in live SSH mode.** Previous detection
   relied on per-VMID `hastate:` or `ha` tag, both of which miss the GUI
   "HA → Add" path. The script now SSHes the first reachable node and
   parses `ct:<vmid>` / `vm:<vmid>` entries into a set that unions with
   tag/hastate detection. Test mode adds `--ha-resources-cfg <path>`.
   Applied: `scripts/ci/check-ha-storage-placement.py`
   (new `_fetch_ha_resources_from_cluster()`, `parse_ha_resources_cfg()`,
   `HA_RESOURCE_ENTRY_RE`; wired into `load_from_cluster()` and
   `load_from_directory()`).

2. **Blocklist regex + whitelist hybrid.** Replaced the 4-element exact-match
   frozenset with `BLOCKED_PATTERNS` (regex list: `^fast-.*$`,
   `^shared-nfs(-.*)?$`, `.*-shared-nfs.*`) + `EXPLICITLY_ALLOWED`
   (`local-zfs`, `local`). Unknown IDs trigger a non-fatal WARNING via the
   new `classify_storage()` helper.
   Applied: `scripts/ci/check-ha-storage-placement.py`, constants around
   line 95-120; new `find_violations_and_warnings()`.

3. **Added `unused\d+` to `DISK_LINE_RE`.** Proxmox parks detached volumes
   there that still consume storage and re-attach on restore.
   Applied: `scripts/ci/check-ha-storage-placement.py`, `DISK_LINE_RE`.

4. **Status-file gate flip-date.** GHA workflow now has
   `STRICT_AFTER_DATE="2026-05-15"`. Before that date a missing status
   file is a warning (exit 0); after, it's a hard failure (exit 1).
   Current mode is logged on every run.
   Applied: `.github/workflows/ci-ha-storage-placement.yml`,
   `live-status-gate` job.

5. **Cron host moved pve2 → pve3.** pve2 is being reinstalled in Epic 5;
   pve3 is the cluster-wide tail workload host and storage-dense, so a
   periodic check is cheap. README also notes the future-option of moving
   to ct-dev-homelab or a dedicated CI container.
   Applied: `ansible/playbooks/ci-checks.yml` (`hosts:
   {{ ha_check_run_host | default('pve3') }}`), `scripts/ci/README.md`
   (§ delivery model + future-consideration note).

6. **Redacted status file (no recon leak).** The committed
   `ci-status/ha-placement-status.txt` now contains ONLY `exit_code`,
   `timestamp`, `violation_hash` (sha256), `violations_count`. No VMIDs,
   hostnames, storage names, or paths. The full unredacted report stays
   in `/var/log/ha-placement-check.log` on the run host (pve3).
   Applied: `ansible/playbooks/ci-checks.yml` (two copy tasks — sanitized
   + full-log), `scripts/ci/README.md` (§ "Status file redaction policy"),
   GHA workflow updated to read the new keys (`exit_code:` without the
   leading `# `, plus `violations_count` and `violation_hash`).

7. **Atomic write on status file.** Ansible's `copy` module writes to a
   temp path and renames into place by default; pinned `unsafe_writes:
   false` explicitly on both copy tasks as belt-and-suspenders against
   future module-default changes.
   Applied: `ansible/playbooks/ci-checks.yml`, both copy tasks.

8. **Canonical tag `ha-managed` only.** Dropped `ha`, `ha=1`, `ha-true` —
   too easy to collide with SLA-intent tags. README now documents the
   operator rule: "for HA-managed workloads, add the `ha-managed` tag to
   the CT/VM config's tags line so CI can see it".
   Applied: `scripts/ci/check-ha-storage-placement.py` (`HA_TAG_TOKENS`),
   `scripts/ci/README.md`, and all three pre-existing fixtures updated to
   `ha-managed`.

9. **Fixed `hastate` semantics.** Only `{started, stopped, error, fence,
   freeze}` now count as HA-managed. `disabled` and `ignored` do NOT count
   (they are operator-signaled "pause HA" states).
   Applied: `scripts/ci/check-ha-storage-placement.py`
   (`HA_ACTIVE_STATES`, `HA_INACTIVE_STATES`, `parse_config()`).

10. **Added missing test fixtures.** Five new fixtures created, existing
    three updated:
    - `test-cases/ha-resources-cfg.conf` — mimics
      `/etc/pve/ha/resources.cfg` with both numeric VMIDs and fixture
      stems so `--ha-resources-cfg` can be exercised end-to-end.
    - `test-cases/gui-ha-ct.conf` — no tag, no hastate, **only** in
      resources.cfg, rootfs on shared-nfs-bulk → must FAIL (headline
      bypass case).
    - `test-cases/vm-with-bad-disk.conf` — qemu config with `scsi0:
      shared-nfs-bulk:…` + `ha-managed` tag + hastate → must FAIL.
    - `test-cases/multi-mount-partial-bad.conf` — rootfs good (local-zfs),
      mp0 bad (shared-nfs-bulk), HA-managed → must FAIL on mp0.
    - `test-cases/unknown-storage.conf` — HA-managed on `my-new-storage`
      → must PASS with WARNING.
    - Existing `good-ha-ct.conf` / `bad-ha-ct.conf` / `non-ha-ct.conf`
      updated to use `ha-managed` tag.

### Post-fix self-test results (2026-04-20)

All eight fixtures pass their contract (each run in isolation, matching
the GHA workflow's pattern):

```
good-ha-ct                  rc=0 warn=no    [PASS]
bad-ha-ct                   rc=1 warn=no    [PASS]
non-ha-ct                   rc=0 warn=no    [PASS]
gui-ha-ct (no resources.cfg)   rc=0 warn=no    [PASS — demonstrates bypass baseline]
gui-ha-ct (with resources.cfg) rc=1 warn=no    [PASS — now caught]
vm-with-bad-disk            rc=1 warn=no    [PASS]
multi-mount-partial-bad     rc=1 warn=no    [PASS — caught on mp0]
unknown-storage             rc=0 warn=yes   [PASS with warning]
```

The combined run (all fixtures + `--ha-resources-cfg`) reports 4
violations + 1 warning, matching the per-fixture contracts.

### Files modified (post-adversarial)

| Path | Change |
|------|--------|
| `homelab-infra/scripts/ci/check-ha-storage-placement.py` | Full rewrite of detection + classification + reporting |
| `homelab-infra/scripts/ci/README.md` | Delivery model (pve3), redaction policy, blocklist hybrid |
| `homelab-infra/scripts/ci/test-cases/ha-resources-cfg.conf` | **NEW** |
| `homelab-infra/scripts/ci/test-cases/gui-ha-ct.conf` | **NEW** |
| `homelab-infra/scripts/ci/test-cases/vm-with-bad-disk.conf` | **NEW** |
| `homelab-infra/scripts/ci/test-cases/multi-mount-partial-bad.conf` | **NEW** |
| `homelab-infra/scripts/ci/test-cases/unknown-storage.conf` | **NEW** |
| `homelab-infra/scripts/ci/test-cases/good-ha-ct.conf` | tag → `ha-managed` |
| `homelab-infra/scripts/ci/test-cases/bad-ha-ct.conf` | tag → `ha-managed` |
| `homelab-infra/scripts/ci/test-cases/non-ha-ct.conf` | doc comment updated |
| `homelab-infra/ansible/playbooks/ci-checks.yml` | host=pve3 default, sanitized+full-log writes, atomic copy |
| `homelab-infra/.github/workflows/ci-ha-storage-placement.yml` | STRICT_AFTER_DATE gate, new fixture self-tests, sanitized-key reads |
