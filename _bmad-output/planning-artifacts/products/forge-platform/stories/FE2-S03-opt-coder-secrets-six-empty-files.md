---
type: story
epic: FE2
id: FE2-S03
title: "/opt/coder/secrets 0700 with six empty 0600 files — do not create the mnemosyne pair"
size: XS
priority: MUST
owner: dev
blocking: false
fr_refs: [FR-CTL-003]
nfr_refs: [NFR-SEC-003, NFR-PORT-001]
adr_refs: [ADR-006]
risk_refs: []
gate_refs: [f]
status: done
date: 2026-09-09
---

# FE2-S03: /opt/coder/secrets 0700 with six empty 0600 files — do not create the mnemosyne pair

> **§5.4 gate CLEARED — implemented and applied 2026-09-09.** The blanket rule is that nothing in
> FE1–FE4 begins before both operator prerequisites exist. Both now do, checked without printing any
> value (`ansible-vault view inventories/homelab/group_vars/vault.yml`):
> 1. **GitHub OAuth App** (FE0-S01) — `vault_forge_github_client_id` (22 chars) and
>    `vault_forge_github_client_secret` (42 chars) are present in
>    `homelab-infra/ansible/inventories/homelab/group_vars/vault.yml`.
> 2. **Cloudflare API token** (FE0-S02) — `vault_cloudflare_api_token` (53 chars) and
>    `vault_cloudflare_zone_id` are present, DNS-edit scoped on zone `bi-services.be`.
>
> This story consumes neither credential — it creates six empty files — so it was never a technical
> dependency. Recorded here because §5.4 is a policy gate, and the gate is now satisfied on the facts.

## User Story

As **tomamourette**, I want **`/opt/coder/secrets` created mode 0700 on `ct-forge-01`, containing exactly six empty mode-0600 files (and explicitly not the two mnemosyne files)**, so that **the workspace template's existing empty-file-means-disabled contract degrades OpenMemory, Langfuse, and the App Configuration rollout flag cleanly, without me having to touch a single line of `coder/templates/forge/main.tf`**.

## Background and Context

Evidence item **E5** identifies this as the cheapest of all the Azure substitutions: the Key-Vault-via-IMDS mechanism that populates eight host files on the Azure coderd VM (`repos/forge-platform/modules/coder/cloud-init.yaml:117-165`) becomes, on a homelab host with no Key Vault, simply **not populating them** — because the workspace template already honours an explicit empty-file-means-disabled contract, verified in `coder/templates/forge/main.tf`. Concretely: the OpenMemory block reads `/run/secrets/openmemory-token` and `/run/secrets/openmemory-mcp-url` via `sudo cat`, and if both are empty, writes `: > "$HOME/.config/forge/openmemory.env"` (a genuinely empty file) rather than failing; the Langfuse block does the identical thing for the three Langfuse secrets (`langfuse-host`, `langfuse-public-key`, `langfuse-secret-key`); the rollout block does it again for `appconfig-endpoint`.

> **Anchor by grep, not by line number.** Every line number this story originally cited for `main.tf`
> was already wrong or stale, and `main.tf` has kept moving. As of 2026-09-09 the six `sudo cat`
> calls are at **341, 342, 358, 359, 360, 383** at git HEAD (`2b27a95`) but at **382, 383, 399, 400,
> 401, 424** in the working tree, which carries uncommitted FE0-S03/FE0-S04 changes. The three
> `: > "$HOME/.config/forge/<x>.env"` else-branches are at working-tree 389, 411, 428. The
> substantive contract is stable; only the anchors drift. Use:
> ```bash
> grep -n 'sudo cat /run/secrets' coder/templates/forge/main.tf
> ```

The Azure cloud-init creates **eight** files under `/opt/coder/secrets/`: `mnemosyne-pat`, `mnemosyne-pat-write`, `openmemory-token`, `openmemory-mcp-url`, `langfuse-host`, `langfuse-public-key`, `langfuse-secret-key`, and `appconfig-endpoint` (`modules/coder/cloud-init.yaml:117-164`, the mnemosyne pair specifically at 128-136). Of these, the workspace template's `sudo cat /run/secrets/*` calls only ever reference the **six** that feed OpenMemory, Langfuse, and the rollout flag. `mnemosyne-pat` and `mnemosyne-pat-write` are **not consumed anywhere in the repository** — this story originally claimed the coderd host's own ACR-pull logic reads them, which is wrong: that pull uses `ARMTOK`, an ARM IMDS token, not the mnemosyne PAT. A repo-wide grep shows the pair is only ever *created and populated*, never read. Their only ever-documented consumer is the abandoned `docs/superpowers/plans/2026-07-02-workspace-topology-v2.md`. The rationale was wrong; the conclusion is right and independently confirmed — `main.tf` mounts exactly six `host_path` volumes out of `/opt/coder/secrets` and none is a mnemosyne file. **Creating the mnemosyne pair here would be pure scope creep with no consumer in this PoC** — hence the hard rule: six files, not eight.

This is one of the two seams the canon calls out as must-not-break: `/opt/coder/secrets/*` → `/run/secrets/*` → `~/.config/forge/*.env`. The must-not-break-the-seam language is **FR-CTL-003** (`prd.md:164`), not NFR-PORT-001 — NFR-PORT-001 is "the Proxmox Terraform root is a sibling of the Azure root, not a relocation" (`prd.md:239`) and says nothing about seams. The `nfr_refs` frontmatter is left as-is pending an operator ruling; the correct reference for this sentence is FR-CTL-003. The middle hop, `/opt/coder/secrets/*` being bind-mounted or copied to `/run/secrets/*` inside the `docker_container.workspace` resource, is **not** re-verified by this story — it is a fact about the existing template that this story's file layout must satisfy on the input side.

## Acceptance Criteria

**AC1 — Directory exists at 0700.**
- **Given** `ct-forge-01` after this story's Ansible task runs,
- **When** the operator runs `stat -c '%a %U' /opt/coder/secrets`,
- **Then** the output is `700 root`.

  **Owner decision, recorded (was circular across FE2-S01/S03/S04):** `root`. CT 167 has no `coder`
  UNIX user — `id coder` returns *no such user*, and the `coder` created by FE2-S02 is a PostgreSQL
  role, a different namespace — and coderd is not installed yet, so root was the only satisfiable
  answer. It is set as `forge_secrets_owner`/`forge_secrets_group` in
  `roles/forge-coder-host/defaults/main.yml`. **FE2-S04 must give `/etc/coder.d/coder.env` the same
  owner.** If a `coderd` service account is later introduced, change the two defaults and re-apply —
  the role reconciles ownership on every run.

**AC2 — Exactly six files, each empty and mode 0600.**
- **Given** AC1 has passed,
- **When** the operator runs `find /opt/coder/secrets -maxdepth 1 -type f -exec stat -c '%n %a %s' {} \;`,
- **Then** exactly six files are listed — `openmemory-token`, `openmemory-mcp-url`, `langfuse-host`, `langfuse-public-key`, `langfuse-secret-key`, `appconfig-endpoint` — each mode `600` and size `0`.

**AC3 — Mnemosyne pair explicitly absent.**
- **Given** AC2 has passed,
- **When** the operator runs `ls /opt/coder/secrets/mnemosyne-pat /opt/coder/secrets/mnemosyne-pat-write 2>&1`,
- **Then** both invocations report "No such file or directory" — the role must not create them, even as empty placeholders.

**AC4 — Idempotent and non-destructive.**
- **Given** the six files already exist (possibly with content, if an operator later decides to populate one for a future phase),
- **When** the role is re-run,
- **Then** it does not truncate or overwrite existing file content — it only creates files that are missing.

  **Correction:** the parenthetical originally said "`state: touch` guarded by a `creates`-style
  check". `ansible.builtin.file` has no `creates` parameter. The mechanism that actually makes
  `state: touch` non-truncating *and* idempotent-reporting is `modification_time: preserve` plus
  `access_time: preserve`, which is what the Implementation Notes YAML below already used and what
  the role implements. In `ansible/modules/file.py`, `execute_touch()` only opens (and thereby
  empties) the file when its previous state is `absent`, and `update_timestamp_for_file()` returns
  `False` immediately when both timestamps are `preserve` — so on an existing file the module
  reconciles nothing but mode/owner.

**AC5 — Feeds gate (f) end to end (verification only, not this story's job to run).**
- **Given** this story's file layout,
- **When** FE4-S02 later runs gate (f) (`~/.config/forge/openmemory.env` and `langfuse.env` both zero-byte, build log contains both "skipped" lines, `sudo -n true` succeeds),
- **Then** this story's Definition of Done includes confirming, by the grep-anchored cross-check in the Implementation Notes (not by line number — `main.tf`'s anchors have already drifted twice), that the six filenames created here exactly match the six filenames that script reads — a name mismatch here would silently defeat the whole contract without erroring anywhere.

## Implementation Notes

Reference E5, ADR-006, HARD RULE (the seam must not be broken). This task set belongs in the same `forge-coder-host` role family as FE2-S01/S02/S05/S06.

```yaml
- name: Ensure /opt/coder/secrets exists, mode 0700
  ansible.builtin.file:
    path: /opt/coder/secrets
    state: directory
    mode: "0700"
    owner: root
    group: root

- name: Ensure the six empty secret files exist (never truncate if already populated)
  ansible.builtin.file:
    path: "/opt/coder/secrets/{{ item }}"
    state: touch
    mode: "0600"
    owner: root
    group: root
    modification_time: preserve
    access_time: preserve
  loop:
    - openmemory-token
    - openmemory-mcp-url
    - langfuse-host
    - langfuse-public-key
    - langfuse-secret-key
    - appconfig-endpoint

- name: Confirm the mnemosyne pair is absent (fail loudly if a prior run created it)
  ansible.builtin.stat:
    path: "/opt/coder/secrets/{{ item }}"
  loop: [mnemosyne-pat, mnemosyne-pat-write]
  register: mnemosyne_check
  failed_when: mnemosyne_check.stat.exists
```

Cross-check for AC5. This was framed as a manual eyeball check ("run once by hand", "by inspection");
it is fully mechanisable, and the story's own risk table makes it the only thing standing between a
filename typo and a false-green gate (f), so it is scripted rather than read:

```bash
diff -u \
  <(grep -o '/run/secrets/[a-z-]*' \
      ~/workspace/homelab/repos/forge-platform/coder/templates/forge/main.tf \
      | sed 's|.*/||' | sort -u) \
  <(grep -oE '^\s+- (openmemory|langfuse|appconfig)[a-z-]+' \
      ~/workspace/homelab/homelab-infra/ansible/roles/forge-coder-host/defaults/main.yml \
      | awk '{print $2}' | sort -u) \
  && [ "$(grep -c 'host_path      = \"/opt/coder/secrets/' \
        ~/workspace/homelab/repos/forge-platform/coder/templates/forge/main.tf)" = 6 ] \
  && echo AC5-PASS
```

Keeping the six names in `defaults/main.yml` rather than inlined in the task is what makes this a
one-line diff instead of a manual read.

## Test Plan

**Pre-state:** CT 167 exists; `/opt/coder/secrets` does not exist.

**Action sequence:**
1. Apply the role (AC1, AC2).
2. Confirm mnemosyne pair absent (AC3).
3. Re-run the role; confirm no file content changes (AC4).
4. Run the scripted filename cross-check against `main.tf` (AC5) — grep-anchored, not line-anchored.

**Post-state checks:**
- `stat -c '%a' /opt/coder/secrets` = `700`.
- Six files present, each `600`/size 0.
- Two mnemosyne files absent.

**Rollback:** `rm -rf /opt/coder/secrets` — no downstream state depends on this directory until FE3/FE4 workspace creation reads it via the (not-yet-built) `/run/secrets` mount.

## Dependencies

- **Blocked by:** FE1-S04 (CT 167 provisioned). Satisfied: `ct-forge-01` is in `[dev_hosts]` in
  `inventories/homelab/hosts.ini:31`, `host_vars/ct-forge-01/main.yml` exists with
  `project_name: forge`, and SSH to 192.168.50.167 works.
- **Blocked by (was unstated — gap now closed):** the `forge-coder-host` role must exist. It does:
  **FE2-S02 landed the skeleton** (`defaults/`, `tasks/main.yml`, `tasks/postgres.yml`,
  `handlers/main.yml`, `README.md`) plus `playbooks/forge-coder-host.yml`. This story added
  `tasks/secrets.yml` to it rather than creating a role ad hoc, so FE2-S01's AC1 "standard shape"
  is not pre-empted.
- **Blocks:** FE4-S01 (first workspace create — the empty-file contract must exist for the build to reach the "skipped" branches cleanly), gate (f) in FE4-S02.

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Filename typo (e.g. `langfuse-publickey` vs `langfuse-public-key`) silently breaks the contract with no error anywhere | Low | Medium — gate (f) fails much later with a confusing symptom | AC5's cross-check against `main.tf`, scripted rather than eyeballed, before marking done |
| A future role re-run truncates a populated file when a later phase actually wires a real secret | Low (not exercised in this PoC — all six stay empty) | Low for the PoC, higher for a later productisation phase | AC4's idempotency check uses `state: touch` with preserved timestamps, not an unconditional overwrite |
| Someone creates the mnemosyne pair "for completeness" without checking scope | Low | Low — dead files, no functional harm, but drifts from ADR-006's explicit exclusion | AC3 is a hard failure condition in the role itself, not just documentation |

## Definition of Done

- [x] AC1–AC5 all green and evidenced (see Implementation Record).
- [x] `/opt/coder/secrets` (0700) with exactly the six named empty files (0600) delivered as Ansible
      tasks in `roles/forge-coder-host/tasks/secrets.yml`.
- [x] Mnemosyne pair confirmed absent — and the role's assert proven to fire when it is not.
- [x] Filenames cross-checked mechanically against `coder/templates/forge/main.tf` (grep-anchored,
      not line-anchored): `AC5-PASS`, no diff.
- [x] Story status updated from `draft` to `done` in this file's frontmatter.
- [x] `tests/acceptance.md` §3.3 FE2-S03 rows AC1–AC5 flipped `pending` → `pass`.

## Implementation Record (2026-09-09)

Delivered as Ansible IaC in the existing `forge-coder-host` role family. Nothing was hand-typed on
CT 167; every state change went through `ansible-playbook`, and every host check below is read-only.

### Files

| File | Change |
|---|---|
| `homelab-infra/ansible/roles/forge-coder-host/defaults/main.yml` | Added the FE2-S03 block: `forge_secrets_dir`, `forge_secrets_dir_mode`, `forge_secrets_file_mode`, `forge_secrets_owner`/`_group`, `forge_coder_secret_files` (the six), `forge_forbidden_secret_files` (the mnemosyne pair) |
| `homelab-infra/ansible/roles/forge-coder-host/tasks/secrets.yml` | New. Four tasks: directory 0700, six files `state: touch` with both timestamps `preserve`, `stat` the forbidden pair, `assert` it is absent |
| `homelab-infra/ansible/roles/forge-coder-host/tasks/main.yml` | Wired `secrets.yml` in, tagged `forge-secrets` (plus a `secrets` alias so this story's AC4 command runs verbatim) |
| `homelab-infra/ansible/roles/forge-coder-host/README.md` | Added the `/opt/coder/secrets` section: six-not-eight, the owner decision, why `state: touch`, the AC5 cross-check, rollback |
| `homelab-infra/ansible/playbooks/forge-coder-host.yml` | Usage header only — added the `--tags forge-secrets` line |

**Playbook naming deviation:** this story's AC4 command names
`playbooks/deploy-forge-coder-host.yml`. The real playbook, created by FE2-S02, is
`playbooks/forge-coder-host.yml`. The existing one was reused rather than creating a near-duplicate;
every command below is the AC's command with that one substitution.

### The mnemosyne guard was rewritten

The Implementation Notes snippet used `loop:` + `register:` + `failed_when: <reg>.stat.exists` on a
single task. A looped `register` produces `.results` (a list), so a bare `.stat` reference is not the
shape a reader expects and the failure message says nothing useful. It is split into
`ansible.builtin.stat` (`failed_when: false`, `changed_when: false`) followed by an
`ansible.builtin.assert` over
`forge_mnemosyne_check.results | selectattr('stat.exists') | list | length == 0`, with a `fail_msg`
that names the offending file and cites ADR-006. **Proven to fire** — see the AC3 guard test below.

### Evidence

**Pre-state (read-only over ssh, before any apply):**
```
--- /opt/coder ---
ls: cannot access '/opt/coder': No such file or directory
--- id coder ---
id: 'coder': no such user
```

**Static checks (controller):**
```
$ ansible-playbook playbooks/forge-coder-host.yml --syntax-check
playbook: playbooks/forge-coder-host.yml
$ ansible-lint roles/forge-coder-host/tasks/secrets.yml
Failed: 4 failure(s), 0 warning(s) in 1 files processed of 1 encountered.
  name[casing]  x4  (all "All names should start with an uppercase letter.")
```
The four are `name[casing]` only, matching the role's established `"<story>: lowercase description"`
prefix convention — `tasks/postgres.yml` carries 25 of the identical violation. No other rule fires
(no `risky-file-permissions`, no `no-changed-when`). The repo has no `.ansible-lint` config and no
lint gate in CI.

**Apply, run 1 — verbatim recap:**
```
TASK [forge-coder-host : secrets: ensure the mode-0700 secrets directory exists at /opt/coder/secrets] ***
changed: [ct-forge-01]

TASK [forge-coder-host : secrets: ensure the six empty secret files exist (never truncating an existing one)] ***
changed: [ct-forge-01] => (item=openmemory-token)
changed: [ct-forge-01] => (item=openmemory-mcp-url)
changed: [ct-forge-01] => (item=langfuse-host)
changed: [ct-forge-01] => (item=langfuse-public-key)
changed: [ct-forge-01] => (item=langfuse-secret-key)
changed: [ct-forge-01] => (item=appconfig-endpoint)

TASK [forge-coder-host : secrets: assert the mnemosyne pair is absent (ADR-006)] ***
ok: [ct-forge-01] => {
    "msg": "mnemosyne-pat and mnemosyne-pat-write are absent from /opt/coder/secrets, as ADR-006 requires."
}

PLAY RECAP *********************************************************************
ct-forge-01                : ok=5    changed=2    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
```

**Apply, run 2 — verbatim recap:**
```
PLAY RECAP *********************************************************************
ct-forge-01                : ok=5    changed=0    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
```

**AC1:**
```
$ ssh -i ~/.ssh/homelab_ed25519 root@192.168.50.167 "stat -c '%a %U' /opt/coder/secrets"
700 root
```

**AC2:** the `find`/`diff` command returned no diff → `AC2-PASS`. Directory listing:
```
drwx------ 2 root root 8 Sep  9 12:38 .
-rw------- 1 root root 0 Sep  9 12:36 appconfig-endpoint
-rw------- 1 root root 0 Sep  9 12:37 langfuse-host
-rw------- 1 root root 0 Sep  9 12:36 langfuse-public-key
-rw------- 1 root root 0 Sep  9 12:36 langfuse-secret-key
-rw------- 1 root root 0 Sep  9 12:36 openmemory-mcp-url
-rw------- 1 root root 0 Sep  9 12:36 openmemory-token
```

**AC3:**
```
ls: cannot access '/opt/coder/secrets/mnemosyne-pat': No such file or directory
ls: cannot access '/opt/coder/secrets/mnemosyne-pat-write': No such file or directory
AC3-PASS
```

**AC3 guard test — the assert actually fires.** `mnemosyne-pat` was created *through a throwaway
Ansible play* (never a hand command) and the role re-run failed with `rc=2`:
```
fatal: [ct-forge-01]: FAILED! => {
    "assertion": "forge_mnemosyne_check.results | selectattr('stat.exists') | list | length == 0",
    "evaluated_to": false,
    "msg": "ADR-006 excludes the mnemosyne credential pair from this PoC, but mnemosyne-pat
exists under /opt/coder/secrets. Nothing in coder/templates/forge/main.tf mounts or reads these
files — it mounts exactly 6 host_path volumes and none of them is a mnemosyne file. Remove them on
the host rather than relaxing this assertion."
}
ct-forge-01                : ok=4    changed=0    unreachable=0    failed=1    ...
```
The injected file was then removed through Ansible and AC3 re-verified clean.

**AC4:** the command's static half passes (`modification_time: preserve` ×1, `access_time: preserve`
×1, no content-writing module in the file) and the second apply reports `changed=0` → `AC4-PASS`.

**AC4, empirically — the story's risk list notes that `changed=0` plus task shape proves
idempotency and proves non-truncation *by construction*, but never exercises a populated file. It
was exercised.** Through throwaway Ansible plays (no hand commands), `langfuse-host` was populated
with 54 bytes of sentinel content, the role was re-run over it, and the file was read back:
```
BEFORE size=54 mode=0600 sha256=cb0cfc8451bf7d75da6180a127cd9406a1f895cb012d9e4b3ba5645c04803f2e mtime=1788957454.7182167
   (role re-run: ct-forge-01 : ok=5  changed=0  failed=0)
AFTER  size=54 mode=0600 sha256=cb0cfc8451bf7d75da6180a127cd9406a1f895cb012d9e4b3ba5645c04803f2e mtime=1788957454.7182167
```
Content, mode **and mtime** survived byte-for-byte, and the task did not even report `changed`. The
file was then restored to size 0 / mode 0600 and the role re-run twice more, both `changed=0`.

**AC5:**
```
$ diff -u <(grep -o '/run/secrets/[a-z-]*' .../main.tf | sed 's|.*/||' | sort -u) \
          <(grep -oE '^\s+- (openmemory|langfuse|appconfig)[a-z-]+' .../defaults/main.yml \
            | awk '{print $2}' | sort -u) \
  && [ "$(grep -c 'host_path      = "/opt/coder/secrets/' .../main.tf)" = 6 ] && echo AC5-PASS
AC5-PASS
```
No diff. Both sides are exactly: `appconfig-endpoint`, `langfuse-host`, `langfuse-public-key`,
`langfuse-secret-key`, `openmemory-mcp-url`, `openmemory-token`. `main.tf` mounts exactly 6
`host_path` volumes from `/opt/coder/secrets` (working-tree lines 645, 650, 655, 660, 665, 670).

### Side effect worth recording

`/opt/coder` itself was created by the same `file` task as its parent and inherited mode `0700`,
owner `root` (`drwx------ 3 root root`). The story only specified `/opt/coder/secrets`. This is
harmless and arguably desirable, but **FE2-S04 should be aware** that `/opt/coder` is already
root-only if it wants to place anything else beneath it.

### Not done

Nothing was committed or pushed — working-tree changes only.
