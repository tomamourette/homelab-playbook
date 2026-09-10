---
type: e2e-deployment-test-plan
product: forge-platform
version: 1.0.0-draft
status: draft
date: 2026-09-09
arch_ref: ../architecture.md
epics_ref: ../epics.md
prd_ref: ../prd.md
acceptance_ref: acceptance.md
proposal_ref: ../../../sprint-change-proposal-2026-09-09.md
runbook_ref: ../../../../wiki/runbooks/create-project-container.md
---

# Forge Platform PoC — End-to-End Deployment Test Plan

## 1. Overview and scope

### 1.1 What this plan tests

The full happy-path runbook for standing up the Forge Platform PoC on **CT 167 (`ct-forge-01`,
pve3, 192.168.50.167)**: CT create → targeted plan/apply → HA replication and rule membership →
inventory/host_vars/`dev-host-setup.yml` → the E2 privilege re-measurement → the `forge-coder-host`
Ansible role (coderd, Postgres 16, secrets directory, `coder.env`, Caddy DNS-01, `daemon.json` +
Docker pin) → the forge-platform branch edits → clone + `docker build` on CT 167 → `coder templates
push` → first workspace create → the eleven acceptance gates (a)–(k) — plus rollback.

### 1.2 What this plan does NOT test (delegated)

Per-story acceptance criteria live in `acceptance.md`; this plan does not re-litigate any single AC.
It covers the **sequencing and cross-layer** concerns that no single story states on its own: which
operator prerequisite gates which implementation step, what a partial failure at each step looks
like, and how to get back to a clean slate. It does not test productisation, CI, or anything from
the 16 platform-owner decisions in `docs/forge-reuse-and-proxmox-findings.md` §5 — those are
FE4-S05's territory, not this runbook's.

### 1.3 The FE0 prerequisite boundary

**Nothing in this runbook's §3 starts before every item in §2 is satisfied.** FE0 is entirely a
prerequisite epic: two operator-only blocking credentials (FE0-S01, FE0-S02) and three code/doc
hygiene stories (FE0-S03…S05) that carry no external dependency but must still land before FE1
touches Terraform state (`FE0-S05` resolves the `ct_sparkle_vlabel` phantom that a bare `apply`
would otherwise recreate). This plan treats "FE0 complete" as a single gate, checked once, at the
top of §3 — not re-checked per step.

---

## 2. Prerequisites

**All four of the following must be satisfied before step 1 of §3 runs. The first two are
operator-only, blocking, and cannot be delegated to code.**

### 2.1 Blocking operator credential #1 — GitHub OAuth App (FE0-S01)

`CODER_EXTERNAL_AUTH_0_ID/TYPE/CLIENT_ID/CLIENT_SECRET` must exist and the grant must cover
`tomamourette/agentic-ai`. Without it: `data "coder_external_auth" "github"`
(`coder/templates/forge/main.tf:25-27`) has no `optional = true`, so the workspace build **fails**
outright at step 11; and even if it built, `forge-sync.sh` sources its clone token from
`coder external-auth access-token github` and **silently skips its entire clone block**, so
agentic-ai never lands and gates (b)–(e) are untestable. This is the **only** non-optional external
credential anywhere in this runbook.

```bash
# Verification once FE0-S01 is recorded done:
grep -c 'CODER_EXTERNAL_AUTH_0_' <recorded-credential-location>   # expect 4
```

### 2.2 Blocking operator credential #2 — Cloudflare DNS-edit token (FE0-S02)

A Cloudflare API token, DNS-edit scope, zone `bi-services.be`, must exist. Without it: **no**
browser-trusted certificate is possible at step 9 — the homelab has no inbound :80/:443, so HTTP-01
cannot work at all, and DNS-01 needs this token to issue anything. ~~Wildcard scope is optional
(`coder_app "code_server"` is `subdomain = false`)~~; the token itself is not.

> **REVERSED 2026-09-09 — a wildcard IS required.** `code_server` really is `subdomain = false`, but
> Coder's preview URLs are subdomain-based and `CODER_WILDCARD_ACCESS_URL=*.forge.bi-services.be` is
> live in `/etc/coder.d/coder.env` on CT 167, so step 9 must issue a certificate carrying **both**
> `forge.bi-services.be` and `*.forge.bi-services.be`. The **token** clause is unaffected — one
> `Zone.DNS Edit` grant on the zone covers the `_acme-challenge` TXT records for both names, so no
> token re-scoping or re-issue is owed. See the amendment at the top of
> [ADR-005](../adrs/ADR-005-dns-01-wildcard-over-public-ingress.md).

```bash
# Verification once FE0-S02 is recorded done:
curl -s -X GET "https://api.cloudflare.com/client/v4/user/tokens/verify" \
  -H "Authorization: Bearer <token>" | grep -q '"status":"active"' && echo OK
```

### 2.3 pve3 capacity check

Before step 1's `terraform apply`, confirm pve3 has room for an additional 4C/8GB (or 4C/12GB if
the R4 sizing decision below chooses the larger CT) container plus headroom for a running workspace
container on top of it.

```bash
ssh pve3 'pvesh get /nodes/pve3/status | grep -E "memory|cpu"'
```

### 2.4 The `ct_sparkle_vlabel` (VMID 166) stash decision (FE0-S05)

`homelab-infra/terraform/envs/homelab/main.tf:280-304` carries an **uncommitted** `module
"ct_sparkle_vlabel"` block for a container destroyed on 2026-07-28. **This must be stashed or
excluded before step 1's plan runs**, or a bare apply recreates a container the operator deleted.
This runbook does **not** decide its fate — FE0-S05 is where that operator call is made and
recorded; this step only confirms it has been made.

```bash
git -C ~/workspace/homelab status --porcelain homelab-infra/terraform/envs/homelab/main.tf
# Expect either: no output (block resolved/committed per FE0-S05's decision), or a git-stash
# reference recorded in FE0-S05 if the decision was "stash, revisit later".
```

### 2.5 The R4 sizing decision

**This runbook does not resolve R4.** Before step 1, the operator must have chosen one of the two
candidates recorded in the FE1-S01 story banner: (a) four real `variable`s in the template plus
`swap_mb = 8192` on the CT, or (b) size CT 167 at 4C/12GB instead of 4C/8GB. Step 1 below is written
for **either** choice — the CT-size line in the `terraform apply` step is a variable, not a fixed
value, precisely because this decision is the operator's and stays open until FE1-S01 records it.

---

## 3. Happy-path runbook

Each step names its producing story, a copy-pasteable command block, and a verification. Steps are
sequential; do not skip a verification to save time — a failure two steps later is harder to
diagnose than a failure caught immediately.

### Step 1 — CT create (Terraform module block)

**Story:** FE1-S01. **Depends on:** §2.4 (phantom resolved), §2.5 (sizing decision made).

```bash
# Add module "ct_forge_01" to homelab-infra/terraform/envs/homelab/main.tf, mirroring
# module "ct_saply_ai": Debian 13, unprivileged, features=nesting=1,keyctl=1, .167,
# swap_mb set EXPLICITLY per the §2.5 decision (8192 if candidate (a), or leave module
# default if candidate (b) sizes the CT itself at 4C/12GB).
terraform -chdir=homelab-infra/terraform/envs/homelab fmt
terraform -chdir=homelab-infra/terraform/envs/homelab validate
```

**Verify:** `terraform validate` reports `Success!`; `git diff` shows only the new module block and
the two `outputs.tf` appends (no unrelated changes).

### Step 2 — Targeted plan / apply

**Story:** FE1-S02. **Depends on:** Step 1.

```bash
terraform -chdir=homelab-infra/terraform/envs/homelab plan \
  -target=module.ct_forge_01 \
  -target=<the two outputs.tf locals appends> \
  -out=ct167.plan
# Inspect ct167.plan — expect exactly: 1 LXC, its network/DNS registrations, nothing else.
terraform -chdir=homelab-infra/terraform/envs/homelab apply ct167.plan
```

**Verify:** `pct status 167` on pve3 reports `running`; `ping ct-forge-01.bi-services.be` (or the
tailnet-resolved name) responds.

### Step 3 — HA replication (both peers) and rule membership

**Story:** FE1-S03. **Depends on:** Step 2.

```bash
# Via the pve-ha-replication and pve-ha-rules Ansible roles ONLY — never direct ha-manager/pvesr
# for provisioning (that is break-glass-only per NFR-IAC-001).
ansible-playbook -i homelab-infra/ansible/inventory/hosts.yml \
  homelab-infra/ansible/playbooks/<ha-replication-playbook>.yml --limit pve3
ansible-playbook -i homelab-infra/ansible/inventory/hosts.yml \
  homelab-infra/ansible/playbooks/<ha-rules-playbook>.yml --limit pve3
```

**Verify:**
```bash
grep -A2 '^167-' /etc/pve/replication.cfg   # expect BOTH 167-0 and 167-1
ha-manager status | grep ct:167             # state matches the FE1-S03 operator decision
```

### Step 4 — Inventory, `host_vars/ct-forge-01/main.yml`, `dev-host-setup.yml`

**Story:** FE1-S04 `[not yet authored — see acceptance.md §1]`. **Depends on:** Step 2.

```bash
# host_vars MUST contain project_name, or dev-host aborts at dev-host/tasks/main.yml:205 —
# after creating the developer user, before seeding SSH keys at :511.
cat homelab-infra/ansible/inventories/homelab/host_vars/ct-forge-01/main.yml   # confirm project_name present
ansible-playbook -i homelab-infra/ansible/inventory/hosts.yml \
  homelab-infra/ansible/playbooks/dev-host-setup.yml --limit ct-forge-01
```

**Verify:** playbook completes with `failed=0 unreachable=0`; `ssh ct-forge-01 'which docker node npm claude pyenv'` all resolve.

### Step 5 — E2 privilege measurement, re-run on CT 167

**Story:** FE1-S05 `[not yet authored]`. **Depends on:** Step 4.

```bash
ssh ct-forge-01 'docker run --rm --privileged alpine sh -c "cat /proc/self/status | grep CapEff"'
ssh ct-forge-01 'docker run --rm --privileged alpine ls /dev | grep -c "^sd\|^nvme"'   # expect 0 — no host block devices
ssh ct-forge-01 'docker run --rm --privileged alpine modprobe dummy'                   # expect failure
```

**Verify:** result matches (or explicitly diverges from) the CT 250 baseline (E2, `[V, in-session]`
on CT 250; **`[I]`** — not verified — that it transfers unchanged to Debian 13 with `keyctl=1`).
Record whatever the actual result is; do not assume it matches CT 250.

### Step 6 — `forge-coder-host` role: coderd

**Story:** FE2-S01. **Depends on:** Step 4.

```bash
ansible-playbook -i homelab-infra/ansible/inventory/hosts.yml \
  homelab-infra/ansible/playbooks/deploy-forge-coder-host.yml --limit ct-forge-01 --tags coderd
```

**Verify:** `ssh ct-forge-01 'dpkg -l | grep coder'` shows the pinned version; the `.deb`'s installed
checksum matches the one recorded in the role.

### Step 7 — Postgres 16

**Story:** FE2-S02. **Depends on:** Step 6.

```bash
ansible-playbook ... --tags postgres
ssh ct-forge-01 'sudo -u postgres psql -c "\l" | grep coder'
```

**Verify:** dedicated database and role exist; `\dx` inside the coder database lists **no**
extensions (`pgvector` is an OpenMemory-only requirement, out of PoC scope).

### Step 8 — `/opt/coder/secrets` (six empty files)

**Story:** FE2-S03. **Depends on:** Step 6.

```bash
ssh ct-forge-01 'stat -c "%a %n" /opt/coder/secrets; ls -la /opt/coder/secrets'
```

**Verify:** directory mode `0700`; exactly six files, each `0` bytes, mode `0600`; the mnemosyne
pair is **not** among them.

### Step 9 — `coder.env` (password auth, GitHub external-auth) and Caddy DNS-01

**Stories:** FE2-S04, FE2-S05. **Depends on:** Steps 2.1/2.2 (credentials), Step 7 (Postgres), Step 8 (secrets).

```bash
ansible-playbook ... --tags coder_env,caddy
```

**Verify:**
```bash
ssh ct-forge-01 'sudo grep -c OIDC /etc/coder.d/coder.env'                 # expect 0
ssh ct-forge-01 'sudo grep CODER_DISABLE_PASSWORD_AUTH /etc/coder.d/coder.env'  # expect =false
curl -vI https://forge.bi-services.be 2>&1 | grep -iE 'issuer|SSL certificate'  # expect a real CA, no warning
```

### Step 10 — `daemon.json` (time-namespaces off) and Docker version pin

**Story:** FE2-S06 `[not yet authored]`. **Depends on:** Step 4 (Docker CE already installed by `dev-host`).

```bash
ssh ct-forge-01 'sudo cat /etc/docker/daemon.json | grep time-namespaces'
ssh ct-forge-01 'dpkg -l docker-ce | tail -1'
```

**Verify:** `{"features":{"time-namespaces":false}}` present; the installed Docker version is
recorded and held (`apt-mark hold` or equivalent) below the 29.5.0 flip until this is deliberately
revisited.

### Step 11 — forge-platform branch edits

**Stories:** FE0-S03, FE0-S04, FE3-S01…S05 `[FE3 stories not yet authored]`. **Depends on:** none of
the infrastructure steps — this can run in parallel with Steps 1–10 on a workstation clone of
`forge-platform`.

```bash
git -C repos/forge-platform checkout -b forge-poc-proxmox
# FE0-S03: pin FORGE_AGENTIC_AI_REF to a tag (main.tf:160-162)
# FE0-S04: fix sysbox comment drift (main.tf:399-404, :559-566; docs/coder/setup.md:149-156;
#          docs/coder/orchestration-adr.md)
# FE3-S01: local.image -> local docker build; four new variables for sizing defaults+maxima
# FE3-S02: replace the two Saply heredocs; add company-overlay to local.repo_deny
# FE3-S03: parameterise forge-sync.sh
# FE3-S04: gate every Azure block in forge-onboard.sh, including :103 az account show
# FE3-S05: decide intellij_gateway (keep or remove) — record the decision, do not leave it implicit
terraform -chdir=repos/forge-platform/coder/templates/forge validate
```

**Verify:** `terraform validate` passes (this is the concrete gate FE3-S05 must satisfy — an
undecided `intellij_gateway` fails validate); `git diff main.tf` shows additive variables and edits
only — `main.tf` is **not** forked (FR-WS-009).

### Step 12 — Clone forge-platform onto CT 167; `docker build`

**Story:** FE3-S06 `[not yet authored]`. **Depends on:** Steps 6–10 (control plane up), Step 11 (branch ready).

```bash
ssh ct-forge-01 'git clone --branch forge-poc-proxmox <forge-platform-url> ~/forge-platform'
ssh ct-forge-01 'cd ~/forge-platform/workspace && docker build -t forge-workspace:poc .'
```

**Verify:** `docker build` exits `0`; `docker images | grep forge-workspace` shows the tag;
Playwright's in-build smoke test (`workspace/Dockerfile:61-68`) passes without needing a registry.

### Step 13 — `coder templates push`

**Story:** FE3-S06. **Depends on:** Step 12.

```bash
ssh ct-forge-01 'cd ~/forge-platform/coder/templates/forge && coder templates push forge -y'
```

**Verify:** `coder templates list` shows `forge` with a new active version.

### Step 14 — First workspace create

**Story:** FE4-S01. **Depends on:** Step 13.

```bash
# From a tailnet client, NOT on the LAN:
coder create ct167-first-workspace --template forge -y
```

**Verify:** exit `0`; `coder external-auth access-token github` returns a token from inside the
workspace; `~/workspace/repos/github/agentic-ai` exists; `~/workspace/repos/github/company-overlay`
does not.

### Step 15 — Run acceptance gates (a)–(k)

**Story:** FE4-S02. **Depends on:** Step 14.

Run every gate command from `acceptance.md` §2, from the same tailnet client, recording every
result including gate (g)'s (non-gating per ADR-003, recorded either way).

---

## 4. Failure scenarios and what each means

### D1 — Workspace OOMs at first boot

**Realisation of:** R4, the sizing conflict, unmitigated. **Symptom:** the workspace container is
OOM-killed shortly after `coder create` reports success, or never reaches `ready`. **Diagnosis:**
`free -g` on pve3 during the attempt (gate h) shows near-zero headroom, or `dmesg | grep -i
oom-kill` on CT 167 shows the workspace's PID. **What it means:** the §2.5 R4 decision was either
not made, or was made and not actually applied at Step 11/Step 14 (e.g., the operator did not
override the create-form defaults). **Not a DOES-NOT-PORT signal by itself** — retry Step 14 with an
explicit smaller `workspace_memory_mb` override; if that succeeds, this becomes a PORTS-WITH-CAVEATS
input for FE4-S04, not a blocker.

### D2 — Inner dockerd fails on the ZFS-backed rootfs

**Realisation of:** R5, nested-nested Docker, untested. **Symptom:** gate (g)'s
`docker run --rm hello-world` fails inside the workspace, or the template's own dockerd-readiness
check (`main.tf:401-405`) emits `WARN: dockerd not ready`. **Diagnosis:**
`ssh ct-forge-01 'docker logs <workspace-container> 2>&1 | grep dockerd'`. **What it means:**
per ADR-003, this **degrades** the PoC — record it as a gate (g) failure and move on to gate (h);
it does not stop the run, and per E1, nothing in agentic-ai's automated surface actually calls
Docker.

### D3 — Workspace build fails with no GitHub grant

**Realisation of:** the FE0-S01 blocker, realised. **Symptom:** `coder create` fails outright with
a `data.coder_external_auth.github` error, or (worse) succeeds but `forge-sync.sh`'s clone block is
silently empty. **Diagnosis:** `coder ssh ... -- 'coder external-auth access-token github'` returns
an error or an empty string. **What it means:** stop immediately, return to §2.1 — this is not a
PoC finding, it is an unmet prerequisite. Do not proceed to gates (b)–(e) until this is fixed.

### D4 — Certificate never issues

**Realisation of:** the FE0-S02 blocker, realised. **Symptom:** Caddy logs show repeated DNS-01
challenge failures; `curl -vI https://forge.bi-services.be` times out or shows a self-signed
fallback certificate. **Diagnosis:**
`ssh ct-forge-01 'sudo journalctl -u caddy --since "10 min ago" | grep -i acme'`. **What it means:**
the Cloudflare token is missing, wrong-scoped, or the `EnvironmentFile` is not being read — return
to §2.2. This blocks gate (a) and, downstream, all of FE4 (no reachable Coder UI).

### D5 — `ha-manager` shows `ct:167` in `error` after a failover test

**Realisation of:** the single-replication-job trap — the ct:151 lesson. **Symptom:**
`ha-manager status` shows `ct:167 (pve1-or-pve2, error)` after a manual failover drill.
**Diagnosis:** `grep -A2 '^167-' /etc/pve/replication.cfg` shows only one of `167-0`/`167-1`, not
both. **What it means:** Step 3 was not completed correctly — one of the two replication jobs is
missing. Per PVE 9 HA error recovery: use `ha-manager set ct:167 --state disabled`, diagnose, then
re-`started`; do **not** attempt `ha-manager set --state stopped` directly on an error-state
resource — it is rejected.

---

## 5. Rollback

Per NFR-DISP-001: *"one destroyed CT, one stashed Terraform block, and a documented negative
result."*

```bash
# 1. Destroy CT 167 via a targeted Terraform destroy — never a bare `destroy` against the root.
terraform -chdir=homelab-infra/terraform/envs/homelab destroy \
  -target=module.ct_forge_01 \
  -target=<the two outputs.tf locals appends>

# 2. Remove the HA rule membership and both replication jobs via the SAME Ansible roles used to
#    create them (never hand-edit /etc/pve/replication.cfg or the rules CSV directly).
ansible-playbook -i homelab-infra/ansible/inventory/hosts.yml \
  homelab-infra/ansible/playbooks/<ha-replication-playbook>.yml --limit pve3 -e forge_ct_present=false
ansible-playbook -i homelab-infra/ansible/inventory/hosts.yml \
  homelab-infra/ansible/playbooks/<ha-rules-playbook>.yml --limit pve3 -e forge_ct_present=false

# 3. Restore the ct_sparkle_vlabel stash decision to whatever FE0-S05 recorded — this rollback does
#    not re-litigate that decision, it only confirms the stash/exclusion is still in the state
#    FE0-S05 left it in.
git -C ~/workspace/homelab status --porcelain homelab-infra/terraform/envs/homelab/main.tf

# 4. Record the negative result in FE4-S04 / FE4-S05 (whichever this rollback follows) — a rollback
#    is not a silent undo, it is itself part of the PoC's evidence.
```

**Verify:** `pct status 167` returns "does not exist"; `ha-manager status` no longer lists `ct:167`;
`/etc/pve/replication.cfg` has no `167-0`/`167-1` entries; `terraform plan` against the homelab root
(narrowly `-target`ed, per NFR-IAC-002) shows CT 167's absence as the only difference from the
pre-PoC state.

---

## 6. Wall-clock expectations

**T-shirt estimates only, never story points — these are ranges, not commitments**, from §3.2 of
the proposal:

| Phase | Size | Range |
|---|---|---|
| Artifact set authoring (this document and its siblings) | S | 1 session |
| CT 167 provisioning (Steps 1–5) | S | half a session; the runbook is stable and rehearsed 4× |
| `forge-coder-host` role (Steps 6–10) | M | Debian is native here |
| forge-platform branch edits (Step 11) | M | ~150 lines across ~6 files |
| Image build + template push + acceptance (Steps 12–15) | M | includes at least one failed workspace build — budget for it, do not treat it as a schedule miss |
| **Total** | **M–L** | Two to four working sessions, **if** the operator prerequisites in §2.1/§2.2 land first |

**At least one failed workspace build is budgeted into Steps 12–15**, per §3.2 of the proposal — a
first attempt that hits D1 or D2 is expected behaviour for this runbook, not a sign the plan is
wrong. Overall risk is **MEDIUM** per the proposal: contained to a new CT on the standard pattern,
with the genuine open risks being the sizing/swap conflict (R4), nested-nested Docker on ZFS (R5),
and the Docker 29.5.0 upgrade trap (R2) — none of which threatens existing production services.
