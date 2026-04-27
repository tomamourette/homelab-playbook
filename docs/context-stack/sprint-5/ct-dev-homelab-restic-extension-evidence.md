# ct-dev-homelab Restic Backup Extension — Evidence

- **Date**: 2026-04-27
- **Story**: Sprint-5 — extend `restic-backup` role to cover ct-dev-homelab (Graphiti + GitNexus production stacks)
- **Branch (homelab-infra)**: `feature/context-stack-e3-graphiti`
- **Branch (homelab-playbook)**: `decommission/context-stack-phase-1`

## Context

ct-dev-homelab.home.io (192.168.50.156, VMID 250 on pve3) hosts:

- The dev compose source for Graphiti at `/home/developer/workspace/homelab/homelab-apps/stacks/graphiti/` (already in git)
- The prod-style Ansible deploy of Graphiti at `/srv/graphiti/` (E4-S08 — docker-compose.yml, .env, patched Python, FalkorDB data dir)
- The prod-style Ansible deploy of GitNexus at `/srv/gitnexus/` (E4-S08)
- The E3-S07 backup cron output at `/home/developer/.local/state/graphiti-backup/` (rdb/cypher/logs)

Until this story, ct-dev-homelab was NOT in the `[backup_hosts]` inventory group, so none of the above was being versioned by the existing `restic-backup` role. This was the only host running Graphiti production state without restic coverage.

## Pre-flight outcomes

| Check | Outcome |
|---|---|
| SSH reachability via 192.168.50.156 | OK (`hostname → ct-dev-homelab`, uptime 2d 22h) |
| `/mnt/backups` directory state | NOT present pre-deploy. `/mnt` itself empty (root-owned, mode 0755). Created during deploy by the role's `Create backup repository parent directory` task (recursively, via Ansible `file: state: directory`). |
| `/mnt/backups` mount | Not a bind-mount. Lives on the LXC's local rpool/data volume (`rpool/data/subvol-250-disk-0`, 50G volume, 38G free at deploy). |
| restic binary pre-installed | NO (`bash: line 1: restic: command not found`). Installed by role's apt task to `/usr/bin/restic`, version `0.14.0 compiled with go1.19.8 on linux/amd64`. |
| Available disk for backups | 38G free on root pool. Initial backup ~36 MiB stored — generous headroom for retention policy (7d/4w/3m). |
| `/home/developer/.local/state/graphiti-backup` exists | YES — contains `rdb/`, `cypher/`, `logs/` subdirs (E3-S07 output). |
| `/srv/graphiti` exists | YES — owned by developer, contains compose files + .env + data/ |
| `/srv/gitnexus` exists | YES — owned by developer, contains docker-compose.yml + data/ |

## Inventory changes (homelab-infra)

### `ansible/inventories/homelab/hosts.ini` — diff

```
@@ -31,6 +31,7 @@
 [backup_hosts]
 ct-docker-01
 ct-media-01
 ct-sparkle-cps
+ct-dev-homelab
```

### `ansible/inventories/homelab/host_vars/ct-dev-homelab/restic.yml` — new file (verbatim)

```yaml
---
# Restic backup paths for ct-dev-homelab (added to backup_hosts in Sprint 5,
# Context-Stack epic — extends restic role coverage to the host running
# Graphiti + GitNexus production stacks).
#
# What gets versioned:
#   - /home/developer/.local/state/graphiti-backup
#       Output of the E3-S07 backup cron (rdb/cypher/logs artifacts) — the
#       canonical recovery artifact for the Graphiti knowledge graph.
#   - /srv/graphiti
#       Prod-style Ansible deploy of the Graphiti compose stack (E4-S08).
#       Captures docker-compose.yml, .env, patched factories.py, MCP config,
#       and the data/ subdir (with the AOF appendonly subdir excluded — see
#       restic_backup_exclude_patterns below).
#   - /srv/gitnexus
#       Prod-style deploy of the GitNexus compose stack (docker-compose.yml +
#       data/). Code-graph state is regenerable from git, but the compose
#       config and any local indexes are worth versioning.
#
# What is intentionally NOT covered here:
#   - /home/developer/workspace/homelab/homelab-apps/stacks/graphiti/
#     (the dev compose source) — already in git, no need to duplicate in restic.
#
# Storage path note:
#   The backup repo at /mnt/backups/restic/ct-dev-homelab/ lives on the LXC's
#   local rpool/data dataset (50G volume, ~38G free at deploy). This provides
#   versioning and ransomware/userspace-mistake protection, but NOT host-failure
#   protection — if the LXC's volume is lost, the restic repo is lost with it.
#   Operator follow-up: bind-mount /mnt/backups from a pve3-level shared pool
#   when convenient, then rerun the role to migrate the repo. The role is
#   backend-agnostic so the path swap is non-disruptive.
restic_backup_paths:
  - /home/developer/.local/state/graphiti-backup
  - /srv/graphiti
  - /srv/gitnexus

restic_backup_exclude_patterns:
  - "*.tmp"
  - ".cache"
  - "**/__pycache__/**"
  - "**/node_modules/**"
  # FalkorDB writes an append-only file (AOF) under data/appendonlydir/ that
  # mutates continuously while the container runs. Restic snapshots of an
  # actively-mutating AOF produce an inconsistent stream of fsync segments,
  # which would not be safely replayable on restore. The canonical recovery
  # artifact is the RDB snapshot — either /srv/graphiti/data/dump.rdb (live
  # FalkorDB) or the dated .rdb under /home/developer/.local/state/graphiti-backup/rdb/
  # (E3-S07 backup cron). Exclude the AOF dir to keep snapshots consistent.
  - "**/data/appendonlydir/**"

# Prometheus textfile collector dir — not yet provisioned on ct-dev-homelab,
# but the role creates it (mode 0755) so node-exporter can read backup metrics
# once observability lands on this host.
restic_backup_textfile_dir: "/var/lib/prometheus/node-exporter"
```

### Pre-existing `group_vars` bug — fixed as part of this commit

During pre-flight, the first `ansible-playbook` invocation failed at the
`Validate restic_backup_password is set` assertion. Investigation showed:

- `group_vars/all.yml` (file) defined `restic_backup_password: "{{ vault_restic_backup_password }}"`
- Commit `bbdb600` (E4-S08.1, 2026-04-27) added `group_vars/all/vault.yml` (file inside a same-named directory)
- Ansible's group_vars loader prefers the directory form when both `all.yml` and `all/` coexist at the same level, silently shadowing `all.yml`'s contents (`homelab_domain`, `notification_email`, `restic_backup_*`, `cloudflare_*`, `ai_dev_hermes_*`, ...).
- Verified by `ansible -m debug -a 'var=hostvars[inventory_hostname]'`: only the `vault_litellm_master_key` and `vault_gemini_api_key` (from `all/vault.yml`) were visible; nothing from `all.yml` (file) was loaded for any host.
- Existing backup_hosts (ct-docker-01, ct-media-01, ct-sparkle-cps) appeared "fine" only because their installed services were deployed pre-bbdb600 and continue to run; a re-deploy would have failed identically.

**Fix**: `git mv ansible/inventories/homelab/group_vars/all.yml ansible/inventories/homelab/group_vars/all/main.yml` so both files coexist inside `all/` and both auto-load. Zero content changes; just relocates the file.

This restores `restic_backup_password`, `notification_email`, `homelab_domain`, `appdata_path`, `cloudflare_api_token`, all `ai_dev_hermes_*`, and other globals to the same visibility the rest of the codebase assumed they had.

## Deploy outcome

```
$ cd ansible
$ ansible-playbook deploy-restic.yml --limit ct-dev-homelab \
    --vault-password-file /dev/shm/vp
...
PLAY RECAP *********************************************************************
ct-dev-homelab : ok=18 changed=11 unreachable=0 failed=0 skipped=0 rescued=0 ignored=0
```

Tasks that ran on ct-dev-homelab:

1. Install restic (apt, 0.14.0)
2. Create `/mnt/backups/restic` parent dir (mode 0700)
3. Render `/etc/restic-backup.env` (mode 0600, contains `RESTIC_REPOSITORY=/mnt/backups/restic` + password)
4. Initialize restic repository (first time)
5. Create `/var/lib/prometheus/node-exporter/` for textfile metrics
6. Render `/usr/local/bin/restic-backup.sh` (mode 0700)
7. Render `/usr/local/bin/restic-restore.sh` (mode 0700)
8. Render `/usr/local/bin/restic-notify-failure.sh` (mode 0700)
9. Render `/etc/systemd/system/restic-notify-failure@.service`
10. Render `/etc/systemd/system/restic-backup.service`
11. Render `/etc/systemd/system/restic-backup.timer`
12. Reload systemd, restart timer, enable timer

## First backup (manual trigger)

```
$ ssh root@192.168.50.156 'systemctl start restic-backup.service'
... wait 30s ...
$ journalctl -u restic-backup.service ...

[2026-04-27T15:40:22Z] [OK] restic-backup: /home/developer/.local/state/graphiti-backup backed up (1s)
[2026-04-27T15:40:22Z] [OK] restic-backup: /srv/graphiti backed up (0s)
[2026-04-27T15:40:23Z] [OK] restic-backup: /srv/gitnexus backed up (1s)
[2026-04-27T15:40:24Z] [OK] restic-backup: retention policy applied — keep 7d/4w/3m (1s)
[2026-04-27T15:40:25Z] [OK] restic-backup: prometheus textfile metrics written
[2026-04-27T15:40:25Z] [OK] restic-backup: all backups completed successfully on ct-dev-homelab
```

`restic snapshots`:

| Snapshot | Path | Files | New bytes (stored) | Source bytes |
|---|---|---:|---:|---:|
| `479d751a` | `/home/developer/.local/state/graphiti-backup` | 8 | 35.731 MiB | 58.039 MiB |
| `553a7637` | `/srv/graphiti` | 9 | 29.083 KiB | 71.757 KiB |
| `b3dbcd85` | `/srv/gitnexus` | 1 | 3.005 KiB | 3.620 KiB |

Total stored: ~36 MiB. Repo lives at `/mnt/backups/restic/`. All 3 snapshots tagged `ansible-managed`, host `ct-dev-homelab`.

Timer state: `restic-backup.timer` enabled and active; next trigger Tue 2026-04-28 02:03:12 UTC.

Prometheus textfile metrics emitted to `/var/lib/prometheus/node-exporter/restic_backup.prom`:

```
restic_backup_last_status{host="ct-dev-homelab"} 0
restic_backup_last_success_timestamp{host="ct-dev-homelab"} 1777304424
restic_backup_last_duration_seconds{host="ct-dev-homelab"} 3
restic_backup_last_size_bytes{host="ct-dev-homelab"} 3707
restic_backup_snapshots_total{host="ct-dev-homelab"} 1
```

(Note: the `snapshots_total` gauge per-host is the latest-snapshot retention count, not the absolute count of all paths' snapshots; that's role behaviour, not a regression.)

## Regression check on existing backup_hosts

```
$ ansible-playbook deploy-restic.yml --limit "ct-docker-01:ct-media-01:ct-sparkle-cps" \
    --check --diff --vault-password-file /dev/shm/vp
...
PLAY RECAP *********************************************************************
ct-docker-01   : ok=16 changed=8  unreachable=0 failed=0 skipped=2
ct-media-01    : ok=14 changed=0  unreachable=0 failed=0 skipped=2
ct-sparkle-cps : ok=14 changed=0  unreachable=0 failed=0 skipped=2
```

- ct-media-01, ct-sparkle-cps: fully idempotent (`changed=0`). No drift, no regressions.
- ct-docker-01: 8 changed-in-check-mode tasks. **This is pre-existing template drift, not introduced by this story** — the template files (env, scripts, systemd units) have evolved on disk vs. what was originally deployed there. Recommend a separate operator follow-up to re-apply the role on ct-docker-01 to flush drift; outside the scope of this story.

`failed=0 unreachable=0` across all three. No regressions introduced.

## Storage path decision

**Option A picked: local LXC storage at `/mnt/backups/restic/`** on `rpool/data/subvol-250-disk-0`.

Rationale:
- Consistent with how the role already targets ct-docker-01, ct-media-01, ct-sparkle-cps (local repos on each host's own storage).
- Setting up Option B (bind-mount from a pve3-level shared pool) requires a Proxmox-level LXC config edit (`pct set 250 -mp0 ...`) and mountpoint provisioning on pve3 — out of scope for an Ansible-only story.
- Option A still gives us versioning + ransomware/userspace-mistake protection; the gap is host-failure protection (if the LXC volume is lost, the repo is lost too).

**Operator follow-up (recommended)**: when convenient, bind-mount `/mnt/backups` on ct-dev-homelab from a pve3-level shared pool (or push to a remote SFTP/S3 backend). Once the bind-mount is live, re-run `ansible-playbook deploy-restic.yml --limit ct-dev-homelab` — the role is backend-agnostic and will switch transparently. Either bind-mount the existing on-LXC repo dir into the shared pool (preserving snapshots), or `restic copy` from the old repo to the new before swapping `RESTIC_REPOSITORY`.

## Anything unexpected

1. **Pre-existing `group_vars/all.yml` shadowing bug** (commit bbdb600): had to fix as part of this commit because the deploy could not succeed otherwise. See "Pre-existing group_vars bug" section above. This is a *fix*, not a regression — re-deploys to existing backup_hosts were already broken; users hadn't noticed because nobody had re-run the role since bbdb600.
2. **`unable to open cache: ... XDG_CACHE_HOME`** noise in journal — restic's cosmetic warning when run as a systemd unit with no `$HOME` for root. Doesn't affect correctness; the backup completes and the cache simply isn't reused. Could silence later with `Environment=HOME=/root` in the unit, but not blocking.
3. **`/mnt/backups` dir was created with mode 0700 root:root by the role** during deploy — that's the role's documented behavior (env file + repo are root-only).

## Other follow-ups flagged for separate stories

- **ct-ai-01 not in `backup_hosts`** despite running cost-cap state, LiteLLM gateway, Ollama models. Worth scoping a separate story to extend coverage there too.
- **ct-docker-01 template drift** (8 changed-in-check tasks): re-apply the role to flush.

## Status

READY for next operator action. Backups for ct-dev-homelab now run nightly at 02:00 UTC with the standard 7d/4w/3m retention policy. Manual restore via `/usr/local/bin/restic-restore.sh` is available.
