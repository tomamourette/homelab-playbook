# ct-ai-01 Restic Backup Extension — Evidence

- **Date**: 2026-04-27
- **Story**: Sprint-5 — extend `restic-backup` role to cover ct-ai-01 (LiteLLM gateway, gemma-hybrid-proxy, cost-cap state)
- **Branch (homelab-infra)**: `feature/context-stack-e3-graphiti`
- **Branch (homelab-playbook)**: `feature/context-stack-e3-graphiti`
- **Precedent**: ct-dev-homelab restic extension (commit `9f5f95a` on homelab-infra, evidence at `docs/context-stack/sprint-5/ct-dev-homelab-restic-extension-evidence.md`). Same pattern, same Option-A storage decision, same role.

## Context

ct-ai-01.home.io (192.168.50.160, VMID 160 on pve3) hosts the local LLM serving stack:

- **LiteLLM gateway** (`/opt/litellm-gateway/`) — config.yaml + .env (LITELLM_MASTER_KEY + provider keys). systemd unit `litellm-gateway.service`.
- **Gemma hybrid proxy** (`/opt/gemma-hybrid-proxy/`) — Python proxy code + .env. systemd unit `gemma-hybrid-proxy.service`.
- **Cost-cap state** (`/var/lib/cost-cap/`) — daily-reset baseline `state.json` consumed by `/usr/local/bin/cost-cap.sh` to compute today's spend delta against the LiteLLM `/spend` endpoint.
- **Ollama** (`/var/lib/ollama/`) — local model runtime, ~16 GiB of model blobs.

Until this story, ct-ai-01 was NOT in the `[backup_hosts]` inventory group, so the LiteLLM master key, the gemma-hybrid `.env`, and the cost-cap baseline were unprotected. Combined with the ct-dev-homelab extension earlier today, both Sprint-5 hosts that hold unique-state are now covered.

## Pre-flight outcomes

| Check | Outcome |
|---|---|
| SSH reachability via 192.168.50.160 | OK (`hostname → ct-ai-01`, uptime 3d 34min) |
| Disk on root | `rpool/data/subvol-160-disk-0` 50G volume, 17G used, 33G free |
| `/opt/litellm-gateway/` | Present, owner `litellm`. Contains `config.yaml`, `config.yaml.cost-cap.bak`, `.env` (660), `.venv/` (361 MiB Python virtualenv) |
| `/opt/gemma-hybrid-proxy/` | Present, owner `gemma-hybrid`. Contains `src/`, `tests/`, `pyproject.toml`, `requirements*.txt`, `.env`, `.venv/` (32 MiB) |
| `/var/lib/cost-cap/` | Present, owner root, contains `state.json` (85 B baseline) |
| `/etc/cost-cap.env` | Present, root-owned, mode 0600 (vault-rendered by Ansible role) |
| `/etc/cron.d/cost-cap` | Present (Ansible-rendered) |
| `/usr/local/bin/cost-cap.sh` | Present, mode 0750 (Ansible-deployed) |
| `/var/log/cost-cap.log` | Present, 12.4 KiB |
| `/etc/systemd/system/litellm-gateway.service` | Present (Ansible-deployed) |
| `/etc/systemd/system/gemma-hybrid-proxy.service` | Present (Ansible-deployed) |
| `/var/lib/ollama/models/` | Present, **16 GiB** (regenerable from registry — confirmed exclusion decision) |
| `/mnt/backups` directory | NOT present pre-deploy. Created during deploy by the role's `Create backup repository parent directory` task. |
| `/mnt/backups` mount | Not a bind-mount. Lives on the LXC's local rpool dataset. Same Option-A storage as ct-dev-homelab. |
| restic binary pre-installed | NO (`bash: line 1: restic: command not found`). Installed by role's apt task. |
| `/root/.ssh/` keys to back up | None — only `authorized_keys`, no private keys present. |

## Path-selection note (role limitation)

The brief listed several loose files (`/etc/cost-cap.env`, `/etc/cron.d/cost-cap`, `/usr/local/bin/cost-cap.sh`, `/var/log/cost-cap.log`, `/etc/systemd/system/litellm-gateway.service`, `/etc/systemd/system/gemma-hybrid-proxy.service`). The `restic-backup` role's backup script (`templates/restic-backup.sh.j2`) gates each path with `if [ -d "$path" ]; then ... else log_fail` — files (not directories) get logged as failures and abort retention. Adding loose files would have broken the first-backup acceptance criterion.

Resolution chosen for this single-host extension: list only directories that contain unique runtime state. All loose files above are deployed by the `litellm-gateway` Ansible role from templates rendered against vault-encrypted secrets (verified at `ansible/roles/litellm-gateway/tasks/main.yml:160-225`), so they are fully regenerable by re-running the role. The systemd units are static templates in the same role. The cost-cap log is a forensic trail; journald/Loki holds a parallel record on the host.

The unique non-regenerable items — `LITELLM_MASTER_KEY` (in `/opt/litellm-gateway/.env`), the gemma-hybrid `.env`, the cost-cap `state.json` baseline — are all under directories listed below and ARE protected by this backup. Out-of-scope for this story: extending the role to `[ -e ]` and supporting files. That would benefit all backup_hosts and is a follow-up.

## Inventory changes (homelab-infra)

### `ansible/inventories/homelab/hosts.ini` — diff

```
@@ -32,6 +32,7 @@ ct-docker-01
 ct-media-01
 ct-sparkle-cps
 ct-dev-homelab
+ct-ai-01
```

### `ansible/inventories/homelab/host_vars/ct-ai-01/restic.yml` — new file (verbatim)

```yaml
---
# Restic backup paths for ct-ai-01 (added to backup_hosts in Sprint 5,
# Context-Stack epic — extends restic role coverage to the host running
# the LiteLLM gateway, gemma-hybrid-proxy, and cost-cap state).
#
# What gets versioned:
#   - /opt/litellm-gateway
#       LiteLLM gateway directory. Captures config.yaml (model/route/team
#       config, including the cost-cap START/END markers) and .env
#       (LITELLM_MASTER_KEY + provider keys). The .venv subtree is
#       excluded — Python virtualenvs are large (~360 MiB) and trivially
#       regenerable from upstream packages.
#   - /opt/gemma-hybrid-proxy
#       Gemma hybrid serving proxy. Captures src/, pyproject.toml,
#       requirements*.txt, and .env (proxy config). Tests are tiny and
#       worth keeping for forensics. The .venv subtree is excluded for
#       the same reason as above.
#   - /var/lib/cost-cap
#       Cost-cap runtime state directory. Contains state.json — the
#       daily-reset baseline used by /usr/local/bin/cost-cap.sh to
#       compute today's spend delta. Without this file the next cost-cap
#       cron tick re-baselines from the live /spend total, which would
#       silently disable the throttle until the next UTC midnight.
#
# What is intentionally NOT covered here:
#   - /var/lib/ollama/models/
#       ~16 GiB of Ollama model blobs at deploy time and growing.
#       Reproducible from the registry via `ollama pull <model>`. Backing
#       it up bloats the repo with no recovery value beyond saving a
#       download.
#   - /etc/cost-cap.env, /etc/cron.d/cost-cap, /usr/local/bin/cost-cap.sh,
#     /etc/systemd/system/litellm-gateway.service,
#     /etc/systemd/system/gemma-hybrid-proxy.service, /var/log/cost-cap.log
#       The restic-backup role's backup script gates each path with
#       `[ -d "$path" ]` — it only accepts directories, not loose files
#       (any file path would log_fail and abort retention). All of the
#       loose files above are deployed by the litellm-gateway Ansible
#       role from templates rendered against vault-encrypted secrets, so
#       they are fully regenerable by re-running the role. The systemd
#       units are static templates. /var/log/cost-cap.log is a forensic
#       trail; if it is ever needed for an incident, journald/Loki holds
#       a parallel record. Backing these up would require either staging
#       them under a single dir or extending the role to support files
#       — both out of scope for this single-host extension.
#
# Storage path note:
#   The backup repo at /mnt/backups/restic/ on ct-ai-01 lives on the
#   LXC's local rpool dataset (50 GiB volume, ~33 GiB free at deploy).
#   This provides versioning and ransomware/userspace-mistake protection,
#   but NOT host-failure protection — if the LXC volume is lost, the
#   restic repo is lost with it. Operator follow-up: bind-mount
#   /mnt/backups from a pve3-level shared pool when convenient, then
#   rerun the role to migrate the repo. The role is backend-agnostic so
#   the path swap is non-disruptive. Same Option-A decision as
#   ct-dev-homelab (commit 9f5f95a, Sprint 5).
restic_backup_paths:
  - /opt/litellm-gateway
  - /opt/gemma-hybrid-proxy
  - /var/lib/cost-cap

restic_backup_exclude_patterns:
  # Standard transient
  - "*.tmp"
  - ".cache"
  - "**/__pycache__/**"
  - "**/node_modules/**"
  - "*.pyc"
  # Python virtualenvs under /opt/* — large, trivially regenerable from
  # requirements.txt / pyproject.toml. Excluding ~390 MiB of venv content
  # on each backup run.
  - "**/.venv/**"

# Prometheus textfile collector dir — not yet provisioned on ct-ai-01,
# but the role creates it (mode 0755) so node-exporter can read backup
# metrics once observability lands on this host. Same default as
# ct-dev-homelab.
restic_backup_textfile_dir: "/var/lib/prometheus/node-exporter"
```

The pre-existing `host_vars/ct-ai-01/vault.yml` (cost-cap ntfy basic-auth) was not touched. `restic.yml` was added as a sibling.

## Deploy — PLAY RECAP

```
ansible-playbook -i ansible/inventories/homelab/hosts.ini \
  ansible/deploy-restic.yml --limit ct-ai-01 \
  --vault-password-file /dev/shm/vp

PLAY RECAP
ct-ai-01  : ok=18  changed=12  unreachable=0  failed=0  skipped=0  rescued=0  ignored=0
```

Tasks that changed:
- Install restic backup tool (apt → `/usr/bin/restic`)
- Create backup repository parent directory (`/mnt/backups/`)
- Deploy restic environment file (`/etc/restic-backup.env`, mode 0600)
- Initialize restic repository (created repo at `/mnt/backups/restic/`)
- Create Prometheus textfile collector directory (`/var/lib/prometheus/node-exporter/`, mode 0755)
- Deploy restic backup script (`/usr/local/bin/restic-backup.sh`, mode 0700)
- Deploy restic restore and verification script (`/usr/local/bin/restic-restore.sh`, mode 0700)
- Deploy restic failure notification script (`/usr/local/bin/restic-notify-failure.sh`, mode 0700)
- Deploy restic failure notification systemd service unit (`/etc/systemd/system/restic-notify-failure@.service`)
- Deploy restic-backup systemd service unit (`/etc/systemd/system/restic-backup.service`)
- Deploy restic-backup systemd timer unit (`/etc/systemd/system/restic-backup.timer`)
- Restart restic-backup timer handler

## First backup — output

Triggered manually via `systemctl start restic-backup.service`:

```
Apr 27 17:42:32 ct-ai-01 systemd[1]: Starting restic-backup.service - Restic backup of /opt/litellm-gateway, /opt/gemma-hybrid-proxy, /var/lib/cost-cap...

# Snapshot 1 — /opt/litellm-gateway
Files:           3 new,     0 changed,     0 unmodified
Dirs:            2 new,     0 changed,     0 unmodified
Added to the repository: 12.611 KiB (6.513 KiB stored)
processed 3 files, 10.850 KiB in 0:00
snapshot 4f98ce5c saved
[OK] /opt/litellm-gateway backed up (1s)

# Snapshot 2 — /opt/gemma-hybrid-proxy
Files:          45 new,     0 changed,     0 unmodified
Dirs:           13 new,     0 changed,     0 unmodified
Added to the repository: 282.305 KiB (89.364 KiB stored)
processed 45 files, 261.601 KiB in 0:00
snapshot 9bddfbbb saved
[OK] /opt/gemma-hybrid-proxy backed up (1s)

# Snapshot 3 — /var/lib/cost-cap
Files:           1 new,     0 changed,     0 unmodified
Dirs:            3 new,     0 changed,     0 unmodified
Added to the repository: 1.453 KiB (1.305 KiB stored)
processed 1 files, 85 B in 0:00
snapshot 2bab4a69 saved
[OK] /var/lib/cost-cap backed up (0s)

# Retention — keep 7d/4w/3m
Applying Policy: keep 7 daily, 4 weekly, 3 monthly snapshots
keep 1 snapshots: 9bddfbbb (gemma-hybrid-proxy)
keep 1 snapshots: 2bab4a69 (cost-cap)
keep 1 snapshots: 4f98ce5c (litellm-gateway)
[OK] retention policy applied — keep 7d/4w/3m (1s)
[OK] prometheus textfile metrics written
[OK] all backups completed successfully on ct-ai-01

restic-backup.service: Deactivated successfully. Consumed 3.048s CPU time, 52.3M memory peak.
```

`.venv` exclusion confirmed working: only 3 files for `/opt/litellm-gateway` (config.yaml + config.yaml.cost-cap.bak + .env), 45 files for `/opt/gemma-hybrid-proxy` (src/ + tests/ + pyproject.toml + requirements*.txt + .env). Without the exclusion these snapshots would have been ~390 MiB instead of ~273 KiB.

## Verification — restic snapshots / stats

```
$ source /etc/restic-backup.env && restic snapshots

ID        Time                 Host        Tags             Paths                    Size
------------------------------------------------------------------------------------------------
4f98ce5c  2026-04-27 17:42:32  ct-ai-01    ansible-managed  /opt/litellm-gateway     10.850 KiB
9bddfbbb  2026-04-27 17:42:33  ct-ai-01    ansible-managed  /opt/gemma-hybrid-proxy  261.601 KiB
2bab4a69  2026-04-27 17:42:34  ct-ai-01    ansible-managed  /var/lib/cost-cap        85 B
3 snapshots

$ restic stats --mode raw-data
Snapshots processed:  3
Total Blob Count:     66
Total Uncompressed:   298.432 KiB
Total Size:           94.539 KiB
Compression Ratio:    3.16x
```

Repo on disk: ~95 KiB after compression (3.16x).

Prometheus textfile metrics (`/var/lib/prometheus/node-exporter/restic_backup.prom`) written:

```
restic_backup_last_status{host="ct-ai-01"} 0
restic_backup_last_success_timestamp{host="ct-ai-01"} 1777311755
restic_backup_last_duration_seconds{host="ct-ai-01"} 3
restic_backup_last_size_bytes{host="ct-ai-01"} 85
restic_backup_snapshots_total{host="ct-ai-01"} 1
```

Note on `restic_backup_snapshots_total{host="ct-ai-01"} 1`: the role's metric-export code in `restic-backup.sh.j2:91` greps `"time"` occurrences in `restic snapshots --json`. With newer restic JSON formatting the count understates the per-host snapshot total. This is a pre-existing role quirk that affects every backup_host equally; not introduced by this change. Out of scope for this story; tracked as a future role-level cleanup.

## Storage path decision (Option A — local LXC repo)

Same trade-off accepted as ct-dev-homelab: `/mnt/backups/restic/` on the LXC's local rpool. Provides versioning + ransomware/userspace-mistake protection but NOT host-failure protection.

Operator follow-up (still open from ct-dev-homelab story; same item): bind-mount `/mnt/backups` from a pve3-level shared pool, then rerun the role on both ct-ai-01 and ct-dev-homelab to migrate the repos. The role is backend-agnostic.

## Regression check

Check-mode dry-run against the pre-existing four backup_hosts after the inventory + host_vars edits:

```
ansible-playbook -i ansible/inventories/homelab/hosts.ini \
  ansible/deploy-restic.yml \
  --limit "ct-docker-01:ct-media-01:ct-sparkle-cps:ct-dev-homelab" \
  --check --diff --vault-password-file /dev/shm/vp

PLAY RECAP
ct-dev-homelab  : ok=14  changed=0  unreachable=0  failed=0  skipped=2  rescued=0  ignored=0
ct-docker-01    : ok=14  changed=0  unreachable=0  failed=0  skipped=2  rescued=0  ignored=0
ct-media-01     : ok=14  changed=0  unreachable=0  failed=0  skipped=2  rescued=0  ignored=0
ct-sparkle-cps  : ok=14  changed=0  unreachable=0  failed=0  skipped=2  rescued=0  ignored=0
```

`changed=0 failed=0` across all four. No drift introduced by the ct-ai-01 inventory addition. The two skipped tasks per host are the `Initialize restic repository` block (gated on `restic_repo_check.rc != 0`, skipped because each repo is already initialized).

## Cross-reference to ct-dev-homelab extension precedent

Same role, same playbook, same vault password file pattern, same Option-A storage decision. ct-dev-homelab evidence at `docs/context-stack/sprint-5/ct-dev-homelab-restic-extension-evidence.md` (commit `9f5f95a` on `homelab-infra/main`). Combined, the two Sprint-5 hosts holding unique production state — ct-dev-homelab (Graphiti+GitNexus) and ct-ai-01 (LiteLLM+gemma-hybrid+cost-cap) — are now under the same nightly 02:00 restic schedule with 7d/4w/3m retention.

## Anything unexpected

- The `restic-backup` role's `[ -d "$path" ]` directory check (in `templates/restic-backup.sh.j2`) made it impossible to back up the loose files the brief listed (`/etc/cost-cap.env`, `/var/log/cost-cap.log`, etc.) without either staging them under a directory or extending the role. Decided to scope this story to directory-only paths and rely on the existing Ansible role to regenerate the loose files (they are vault-rendered templates). Worth queuing as a follow-up: extend the role's backup script to accept files via `[ -e ]`, with sensible per-host parent-dir handling.
- `.venv` directories under `/opt/litellm-gateway/` (361 MiB) and `/opt/gemma-hybrid-proxy/` (32 MiB) almost dwarfed the actual unique-state content. The `**/.venv/**` exclude pattern is essential and was confirmed working by the per-snapshot file counts.
- `/var/lib/ollama/models/` confirmed at 16 GiB on disk — exclusion decision validated. Ollama models are reproducible from the registry; backing them up would have multiplied repo size by ~150x for zero recovery benefit.

## Operator follow-ups (not in scope here)

1. Off-host bind-mount for `/mnt/backups` (still open from ct-dev-homelab; same fix migrates both LXCs)
2. Restic repo password rotation policy (cluster-wide; vault has a single `vault_restic_backup_password`)
3. Deploy keys / SSH keys backup if any are added to `/root/.ssh/` later
4. Role-level cleanup of the `restic_backup_snapshots_total` textfile metric (counts `"time"` strings; underreports with newer restic JSON)
5. Role enhancement: support file paths via `[ -e ]` in the backup script's per-path loop (would unblock backing up `/etc/cost-cap.env` etc. directly)
