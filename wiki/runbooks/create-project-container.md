---
title: "Create a new project container"
slug: create-project-container
category: runbooks
last_reviewed: 2026-07-28
owner: tomamourette
related_pages: [pve9-ha-migration, tailscale-policy, remote-access-recovery, remote-access-topology]
related_frs: []
related_adrs: []
status: stable
supersedes: []
superseded_by: null
tags: [proxmox, lxc, terraform, ansible, project-container, runbook]
---

# Create a new project container

## Summary

Spin up a fresh Debian 13 LXC project container on the cluster, end to end:
Terraform module → DNS auto-derivation → HA replication + rules → Ansible
`dev-host` provisioning → operator SSH verification. Project containers
follow the convention `ct-<name>` on `pve3` (active-cooled, AI/dev tier),
local-zfs storage, allocated from VMID/IP block `192.168.50.16x`. The
Terraform create produces only a bare LXC; the `developer` user, SSH
keys, Docker, Node, Claude Code, ruflo, and pyenv are all installed by
the `dev-host` Ansible role in a separate step. Skipping the Ansible
step is the single most common reason an operator's SSH login prompts
for a password.

## Context

The fleet's project containers (ct-sparkle-cps, ct-quant-trading,
ct-hermes-hub, ct-saply-ai, …) all share the same shape: 2-4 vCPU,
4-8 GB RAM, 20-50 GB disk, Debian 13 unprivileged, `nesting=1`, on
local-zfs. They get HA-eligible by replicating to both peer nodes at
`*/15` and joining the `standard` node-affinity rule. Sizing splits
into two tiers — light (2C/4GB/20GB, e.g. ct-hermes-hub) for always-on
director/agent work, heavier (4C/8GB/50GB, e.g. ct-quant-trading,
ct-saply-ai) for backtesting / AI workloads. DNS, Pi-hole entries,
Cloudflare records, and Prometheus targets are all auto-derived from
the Terraform `project_container_host_map` output — no per-CT manual
DNS edits are required.

This runbook is the canonical procedure. The `create-project-container`
Claude Code skill (in `~/.claude/skills/`) is the conversational
front-end to this runbook for operator sessions.

## Procedure

### 0. Pre-flight: pick VMID, IP, sizing, host node

| Convention | Source of truth |
|---|---|
| VMID | next free in `162-169` block (project containers); check `pct list` on each node |
| IP | matches VMID: `192.168.50.<vmid_last_two>` (e.g. 164 → 192.168.50.164) |
| Hostname | `ct-<name>` (kebab-case, must match Terraform module name without `ct_` prefix replaced by `_`) |
| Node | `pve3` is the default for AI/dev workloads (active-cooled, NVMe local-zfs); other nodes only with explicit reason |
| Storage | `local-zfs` (HA-eligible via replication; `local-lvm` is not supported on pve3 anyway) |
| OS template | `local:vztmpl/debian-13-standard_13.1-2_amd64.tar.zst` (Debian 12 template is NOT cached on pve3) |
| Sizing — light | 2C / 4GB / 20GB — always-on agent/director work |
| Sizing — heavy | 4C / 8GB / 50GB — backtesting, AI inference, larger context |
| HA tier | `standard` rule (failover across pve1/pve2/pve3, `--strict 0`) for normal project work; `critical` rule only with explicit reason |

If pve3 is missing the Debian 13 template (rare; check
`ls /var/lib/vz/template/cache/` on pve3 first):

```bash
ssh root@pve3 "pveam download local debian-13-standard_13.1-2_amd64.tar.zst"
```

### 1. Add the Terraform module

Edit `homelab-infra/terraform/envs/homelab/main.tf`. Append a new
`module "ct_<name>"` block after the most recent project container.
Mirror the `ct-saply-ai` template below — adjust `name`, `vmid`,
`network_ip`, sizing, and `tags` for the new container:

```hcl
# <Name> project container on pve3 — <one-line purpose>.
module "ct_<name>" {
  source = "../../modules/ct-debian"

  name         = "ct-<name>"
  vmid         = 164                       # next free in 162-169
  node         = "pve3"
  cores        = 4                         # 2 (light) or 4 (heavy)
  memory_mb    = 8192                      # 4096 or 8192
  disk_gb      = 50                        # 20 or 50
  storage_id   = "local-zfs"
  ostemplate   = "local:vztmpl/debian-13-standard_13.1-2_amd64.tar.zst"
  unprivileged = true
  features     = ["nesting=1"]

  network_bridge  = "vmbr0"
  network_ip      = "192.168.50.164/24"
  network_gateway = "192.168.50.1"
  nameserver      = "192.168.50.194"
  searchdomain    = var.domain

  ssh_keys = var.ssh_keys
  mounts   = []

  tags = ["<name>", "project", "ai-dev", "homelab"]
}
```

### 2. Wire into outputs.tf

Edit `homelab-infra/terraform/envs/homelab/outputs.tf`. Two appends —
one for Prometheus discovery, one for DNS auto-derivation:

```hcl
# locals.all_containers — append:
{
  name       = module.ct_<name>.name
  node       = module.ct_<name>.node
  vmid       = module.ct_<name>.ctid
  monitoring = module.ct_<name>.monitoring
},

# locals.project_container_host_map — append:
"ct-<name>" = module.ct_<name>.ip_address
```

This single edit propagates to:

- Cloudflare A record `ct-<name>.bi-services.be`
- Pi-hole `custom.list` (regenerated to `generated/pihole-custom.list`)
- Prometheus file_sd_configs (`generated/prometheus-node-targets.json`)
- The `dns_records` Terraform output

### 3. terraform init, plan (narrowly!), apply

```bash
cd homelab-infra/terraform/envs/homelab
terraform init -upgrade=false

# Narrow targets — see Pitfalls §1 for why this matters
terraform plan \
  -target=module.ct_<name> \
  -target=local_file.prometheus_targets \
  -target=local_file.pihole_custom_list \
  -target='cloudflare_record.homelab["ct-<name>"]' \
  -out=tfplan-<name>

terraform show -no-color tfplan-<name> | grep -E "(will be|^Plan:)"
# Expected: 4 creates + 2 replaces (the local_file regenerations).
# Plan: 6 to add, 0 to change, 2 to destroy.

terraform apply tfplan-<name>
```

### 4. Post-create on pve3 — replication + HA + node-affinity (via Ansible IaC)

The Proxmox API token does not always inject SSH keys / nameserver
correctly on create. Verify first:

```bash
ssh root@pve3 "pct config <vmid> | grep -E '^(nameserver|searchdomain|net0|features)'"
ssh root@pve3 "pct exec <vmid> -- ip -4 addr show eth0 | grep inet"
```

HA + replication are managed via the `pve-ha-rules` and
`pve-ha-replication` Ansible roles — **not** direct `ha-manager` /
`pvesr` commands. Both defaults files are the source of truth and
must stay reconciled (see role headers for the cross-reference
invariant).

Edit `homelab-infra/ansible/roles/pve-ha-replication/defaults/main.yml`,
append two replication jobs to `ha_replication_jobs`:

```yaml
- jobid: "<vmid>-0"
  source: pve3
  target: pve1
  schedule: "*/15"
  rate: 50
  comment: "ct-<name> HA replica to pve1"
- jobid: "<vmid>-1"
  source: pve3
  target: pve2
  schedule: "*/15"
  rate: 50
  comment: "ct-<name> HA replica to pve2"
```

Edit `homelab-infra/ansible/roles/pve-ha-rules/defaults/main.yml`, append
the resource to `ha_resources` and add the SID to the `standard` rule's
`resources` CSV (the role's reconcile pass will run `ha-manager rules
set --resources` to bring live state in line):

```yaml
# ha_resources: append
- type: ct
  vmid: <vmid>
  state: started   # or 'stopped' per the Project-CT HA Policy memory
  max_relocate: 1
  max_restart: 3
  failback: 1
  comment: "standard-tier; ct-<name>"

# ha_rules.standard.resources: include the new SID in the CSV
resources: "ct:101,ct:151,ct:163,ct:164,ct:<vmid>,ct:250"
```

Choose `state` per the [Project-CT HA Policy memory](git:%7E/.claude/projects/-home-developer-workspace-homelab/memory/project_project_container_ha_policy.md):

| Run-state at register | `state` |
|---|---|
| Always-on (immediately starts on cluster boot) | `started` |
| Stopped (replicates, but stays stopped on peer at failover) | `stopped` |

Then apply both playbooks (idempotent — existing entries skip):

```bash
cd homelab-infra/ansible
ansible-playbook playbooks/pve-ha-replication.yml
ansible-playbook playbooks/pve-ha-rules.yml
```

Verify HA pickup:

```bash
ssh root@pve3 "sleep 10 ; ha-manager status | grep ct:<vmid>"
# Expected: service ct:<vmid> (pve3, started)
```

**Direct `ssh root@pve3 ha-manager …` is reserved for break-glass
recovery only.** Adding a CT via CLI bypasses the role's defaults and
silently drifts live state away from IaC — exactly how ct:163 and
ct:164 ended up out of sync until backfilled on 2026-05-14.

### 5. SSH key gap — inject the operator's PC key (BEFORE Ansible)

`var.ssh_keys` in `terraform.tfvars` ships the `homelab-infra` ed25519
key with fingerprint `Nhm8fG…745q`. If the operator's workstation key
matches this fingerprint, skip this section. If it differs (or unsure):

```bash
# On operator workstation:
ssh-keygen -lf ~/.ssh/homelab_ed25519.pub

# If fingerprint != Nhm8fG…745q, inject the workstation key:
PUBKEY=$(cat ~/.ssh/homelab_ed25519.pub)
ssh root@pve3 "pct exec ${VMID} -- bash -c 'echo \"$PUBKEY\" >> /root/.ssh/authorized_keys'"
```

This unblocks `root@<ip>` access for the dev container so Ansible can
reach the host. The `developer` user's authorized_keys is seeded
separately by the `dev-host` role in step 7.

### 6. Wire Ansible inventory + host_vars

Edit `homelab-infra/ansible/inventories/homelab/hosts.ini`, append to
the `[dev_hosts]` group:

```ini
ct-<name> ansible_host=192.168.50.<ip> ansible_user=root \
  ansible_ssh_private_key_file=~/.ssh/homelab_ed25519
```

Create `homelab-infra/ansible/inventories/homelab/host_vars/ct-<name>/main.yml`:

```yaml
---
project_name: <name>

project_repos: []
```

The `project_name` var is **required** by `dev-host/tasks/main.yml:205`
(BMAD install task). Without it the playbook bails with
`'project_name' is undefined` after creating the user but before
seeding SSH keys (the SSH key task lives at line 511).

### 7. Run dev-host-setup

```bash
cd homelab-infra
ansible-playbook -i ansible/inventories/homelab/hosts.ini \
  ansible/dev-host-setup.yml --limit ct-<name>
```

This installs: developer user (uid 1000, sudo + docker groups), SSH
authorized_keys (the seeded `homelab-infra` pubkey from
`dev-host-setup.yml:18`), Docker CE, Node 20 LTS, Claude Code CLI
wrapper, ruflo, pyenv with Python 3.11.11, Microsoft ODBC, VS Code
tunnel service, en_US.UTF-8 locale.

Expected end state:
`ok=50 changed=24 unreachable=0 failed=0 skipped=5 rescued=0 ignored=1`

The single ignored task is `Register ruflo MCP server in Claude Code
(project scope)` — fails with `claude: not found` because the shell
PATH doesn't see the wrapper at `~/bin/claude` from a non-interactive
become. Run manually as `developer` later if needed:

```bash
ssh developer@<ip> "cd ~/workspace/<name> && claude mcp add ruflo -- ruflo mcp start"
```

### 8. Verify operator access

As of the 2026-07-28 keyless remote-access design, Tailscale is the
**primary** path and SSH keys are a **fallback only** — see
[Remote access recovery](remote-access-recovery) and
[Remote access topology](remote-access-topology) for the full picture.

**Primary — Tailscale SSH (keyless).** No keys, no hand-maintained
`~/.ssh/config`: the Tailscale VS Code extension shows a clickable list
of reachable machines, and that list is the source of truth for what's
reachable — do not maintain a parallel SSH config file. This only works
once the container is onboarded to the `remote-access` Ansible role
(new project containers are **not** onboarded by default — add
`ct-<name>` to `[remote_access_hosts]` in `hosts.ini` and to
`lxc_tun_ctids` in `playbooks/lxc-enable-tun.yml`, then run
`playbooks/lxc-enable-tun.yml` followed by `playbooks/remote-access.yml`
— see the recovery runbook for the full sequence):

```bash
ssh ct-<name>.taildf9e93.ts.net "hostname && id && docker --version"
```

**Fallback — SSH key (LAN-only, always available).** Project containers
get `developer`'s `authorized_keys` seeded by `dev-host-setup.yml`
(step 7) from the `homelab-infra` fleet key (`terraform.tfvars`
`var.ssh_keys`). Verify directly by IP, no config file needed:

```bash
ssh developer@192.168.50.<ip> "hostname && id && docker --version"
```

If this prompts for a password, the operator workstation's own key is
not yet authorized on this host. Add it to
`remote_access_authorized_keys` in
`homelab-infra/ansible/inventories/homelab/group_vars/all/remote-access.yml`
and run the fallback distribution playbook:

```bash
cd homelab-infra/ansible
ansible-playbook playbooks/ssh-authorized-keys.yml --limit ct-<name>
```

**Do NOT** copy the `homelab_ed25519` private key off `ct-dev-homelab`
to the workstation. A single private key living on one device with no
second path in is exactly the failure the 2026-07-28 keyless
remote-access design exists to eliminate (workstation `tom-notebook-1`
died taking the only copy with it). If the operator needs a new
workstation key trusted fleet-wide, add its **public** key to
`remote_access_authorized_keys` above — never move the private key.

### 9. Capture in auto-memory

Add a project memory file (template after `project_saply_ai.md` or
`project_hermes_hub.md`):

```bash
~/.claude/projects/-home-developer-workspace-homelab/memory/project_<name>.md
```

Register one line in `MEMORY.md`:

```markdown
- [<Name>](project_<name>.md) — ct-<name> (VMID <vmid>, pve3, .<ip>),
  <sizing> Debian 13 on local-zfs, project-tier HA <state>, created <date>
```

## Pitfalls

### 1. Untargeted `terraform plan` pulls in unrelated DNS drift

A bare `terraform plan` against this state often includes pre-existing
config drift (e.g. `gemma.bi-services.be → 192.168.50.194` from
`ai_service_ip_map`) that has nothing to do with the new container.
Always narrow with `-target=` (see step 3) and verify only the four
expected resources show "will be created".

### 2. SSH key fingerprint mismatch (terraform.tfvars vs operator key)

`var.ssh_keys` in `terraform.tfvars` does not match
`~/.ssh/homelab_ed25519` on every operator workstation. Symptom is a
password prompt despite `IdentityFile` being set. See step 5 + step 8.
This gap has hit ct-quant-trading (2026-04-18), ct-hermes-hub
(2026-05-06), and ct-saply-ai (2026-05-09).

### 3. Forgetting `host_vars/<name>/main.yml` aborts dev-host mid-run

The `dev-host` role requires `project_name`. If the host_vars file is
missing, the playbook fails at the BMAD install task **after** creating
the user but **before** seeding SSH keys. Symptom: `developer` exists
in `id`, no `~developer/.ssh/authorized_keys`. Re-run the playbook
after creating the host_vars file — it is idempotent.

### 4. `ha-manager rules set` REPLACES `--resources`, doesn't append

The CLI takes a complete CSV. Hidden behind the `pve-ha-rules` role
since 2026-05-14 (`tasks/rules.yml` reconcile pass) — the role reads
live `/etc/pve/ha/rules.cfg`, diffs against `ha_rules[*].resources`,
and runs `ha-manager rules set --resources <full-csv>` only when they
differ. If you bypass the role with direct CLI: always read the
current list first (`ha-manager rules config | grep standard`) before
writing back, or you will drop other CTs out of the rule.

### 5. Replication to only one peer = `error` state on failover

`standard` rule has `nodes pve1,pve2,pve3`, so a CT on pve3 must
replicate to BOTH pve1 AND pve2. A single replication job is enough
for "data is safe" but not enough for "HA failover succeeds". See
[PVE 9 HA migration](pve9-ha-migration) §3.

### 6. Debian 13 template caching is per-node

`pveam list local` is per-node. The template might be cached on pve1
but not pve3. Always check pve3 (the create target) explicitly. If
missing, the create fails with `volume does not exist` after the LXC
ID is allocated, leaving stale state. `pveam download` first.

## Cross-references

- [PVE 9 HA migration runbook](pve9-ha-migration) — rules-vs-groups,
  state policy, error recovery
- [Tailscale-only access policy](tailscale-policy) — phone-facing
  service exposure (project containers are NOT phone-facing by default)
- `homelab-infra/terraform/modules/ct-debian/` — the underlying
  Terraform module the per-CT blocks consume
- `homelab-infra/ansible/roles/dev-host/tasks/main.yml` — full task
  list of what step 7 actually installs
- `homelab-infra/ansible/dev-host-setup.yml` — playbook entrypoint;
  also where `ssh_authorized_keys` is hard-coded
- `~/.claude/.../memory/project_hermes_hub.md` — first project CT
  with HA + always-on (template for `--state started`)
- `~/.claude/.../memory/project_quant_trading.md` — first 4C/8GB/50GB
  project CT (template for heavier sizing)
- `~/.claude/.../memory/project_saply_ai.md` — most recent project
  CT (2026-05-09), this runbook's reference implementation
- `~/.claude/.../memory/project_project_container_ha_policy.md` —
  `--state` matches run-state policy
