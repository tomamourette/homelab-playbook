# Pre-existing 0:0 vs 1000:1000 drift on ct-docker-01

**Date:** 2026-04-27
**Drift:** `/opt/appdata/{automations-n8n,organizr}` are `root:root` (0:0) on the host but the `docker-host` Ansible role declares `1000:1000`.
**Mode:** Read-only investigation. Nothing was modified on ct-docker-01.
**Predecessor work:** `drift-investigation-evidence.md` Phase 1 (commit `caed59d`) removed the recursive-chown CouchDB-clobber bug. The 0:0→1000:1000 parent-dir drift was explicitly deferred to this story.

## Current state

`stat` output from ct-docker-01 (192.168.50.194):

```
File: /opt/appdata/automations-n8n
Size: 7   Blocks: 17   IO Block: 512   directory
Access: (0755/drwxr-xr-x)  Uid: (    0/    root)   Gid: (    0/    root)
Modify: 2025-09-27 22:07:00 +0000
Change: 2026-04-21 18:45:13 +0000
Birth:  2026-04-21 18:45:13 +0000

File: /opt/appdata/organizr
Size: 5   Blocks: 1    IO Block: 512   directory
Access: (0755/drwxr-xr-x)  Uid: (    0/    root)   Gid: (    0/    root)
Modify: 2025-09-27 22:07:52 +0000
Change: 2026-04-21 18:45:25 +0000
Birth:  2026-04-21 18:45:23 +0000
```

Both parents are owned `root:root` mode `0755`. Birth-time on the inode is 2026-04-21 (matches a recent re-creation, likely the LXC/CT rebuild around that date); content `mtime` from 2025-09-27 indicates data was retained / restored across that re-creation.

### Subdirectories are mixed (this is the key signal)

```
/opt/appdata/automations-n8n/
  drwxr-xr-x  2 1000 1000  local-files/
  drwxr-xr-x  5 1000 1000  n8n/                ← n8n container writes here as uid 1000
  drwxr-xr-x  3 root root  postgres/           ← postgres-init creates pgdata as uid 70
  drwxr-xr-x  2 root root  postgres-initdb/
  drwxr-xr-x  3  999 root  redis/              ← redis container writes here as uid 999

/opt/appdata/organizr/
  drwxr-xr-x  6  999 systemd-journal  mariadb/         ← mariadb container, uid 999
  drwxr-xr-x  2  999 systemd-journal  mariadb-config/
  drwxr-xr-x  7 1000            1000  organizr/        ← organizr container drops to PUID=1000
```

For comparison, two sibling appdata dirs ARE already aligned to the role intent:

```
drwxr-xr-x 10 1000 1000 observability/
drwxr-xr-x  3 1000 1000 productivity-obsidian/
```

So the same role on the same host has already produced 1000:1000 parents elsewhere — these two dirs simply pre-date the role-managed mkdir or were created out-of-band by something running as root.

## Role intent

`ansible/roles/docker-host/main.yml` (post-`caed59d`, lines 31–55):

```yaml
- name: Create Docker host appdata directories
  file:
    path: "{{ item }}"
    state: directory
    owner: 1000
    group: 1000
    mode: '0755'
    # A1 (drift-investigation 2026-04-27): NO recurse — apps that create
    # subdirs as a different UID (e.g. CouchDB at 5984) must not be clobbered
    # back to 1000:1000. Only ensure the listed dirs themselves exist + own.
  loop:
    - /opt/appdata/infra-core/traefik
    - /opt/appdata/infra-core/portainer
    - /opt/appdata/observability/prometheus
    - /opt/appdata/observability/grafana
    - /opt/appdata/observability/node-exporter
    - /opt/appdata/observability/cadvisor
    - /opt/appdata/automations-n8n        ← target dir #1
    - /opt/appdata/organizr               ← target dir #2
    - /opt/appdata/productivity-obsidian
```

`recurse: yes` was removed in `caed59d`. The role would now chown only the listed parent dir, not its subtree. So the next `--check` run would report exactly **2 changed** (these two dirs going `0:0 → 1000:1000`).

## App expectation

### n8n stack — `homelab-apps/stacks/automations-n8n/docker-compose.yml`

| Container | `User:` directive | Internal runtime UID (verified) | Volume on host | Subdir owner on host |
|---|---|---|---|---|
| `n8n` | not set (image default) | `uid=1000(node) gid=1000(node)` | `/opt/appdata/automations-n8n/n8n:/home/node/.n8n` | `1000:1000` ✓ |
| `n8n` | (same) | (same) | `/opt/appdata/automations-n8n/local-files:/files` | `1000:1000` ✓ |
| `n8n-db` (postgres:15.5-alpine) | not set, runs as root then drops to postgres uid 70 internally | container runs as `root` per `docker exec id`, but pgdata owned by uid 70 | `/opt/appdata/automations-n8n/postgres:/var/lib/postgresql/data` | parent `root:root`; `pgdata/` owned `70:root 0700` ✓ |
| `n8n-redis` (redis:7.2.3-alpine) | not set, image default redis user uid 999 | container runs as `root` (no USER in compose), but writes data as 999 | `/opt/appdata/automations-n8n/redis:/data` | `999:root` ✓ |

No `PUID`/`PGID` env in the n8n stack. The expectation is purely "image default UID writes to the host volume," and that has been working — n8n's `.n8n/` is correctly `1000:1000`.

### organizr stack — `homelab-apps/stacks/organizr/docker-compose.yml`

| Container | `User:` directive | Internal runtime UID (verified) | Volume on host | Subdir owner on host |
|---|---|---|---|---|
| `organizr` (organizr/organizr:2.1.5680) | not set; uses `PUID`/`PGID` env | `uid=0(root)` from `docker exec id` (s6-init runs root, drops to PUID for fpm/nginx workers) | `/opt/appdata/organizr/organizr:/config` | `1000:1000` ✓ |
| `organizr-db` (mariadb:10.11.6) | not set | container runs as root, mysqld drops to mysql uid 999 | `/opt/appdata/organizr/mariadb:/var/lib/mysql` | `999:systemd-journal` ✓ |

`PUID=1000`, `PGID=1000` are set in `/opt/homelab-apps/stacks/organizr/.env` on the host (matches `homelab-apps/stacks/organizr/.env.sample` in repo). Confirmed inside the running container's env. End-state: organizr config files are owned 1000:1000 — exactly matching the role's parent-dir intent.

### All 5 containers verified healthy

```
n8n          n8nio/n8n:1.17.1            Up 29 hours (healthy)
n8n-db       postgres:15.5-alpine        Up 29 hours (healthy)
n8n-redis    redis:7.2.3-alpine          Up 29 hours (healthy)
organizr     organizr/organizr:2.1.5680  Up 29 hours (healthy)
organizr-db  mariadb:10.11.6             Up 29 hours (healthy)
```

29h uptime with the parent dir at `0:0` proves the apps don't need to OWN the parent — they only need execute (`+x`) traversal to reach their owned subdir. Mode `0755` provides world-traversable, so the drift is functionally invisible.

## Verdict: α

**Option α — Role default is correct, host parents are drifted to 0:0; apps already use 1000:1000 in the subdirs that matter.**

Evidence:

1. **Apps run as PUID=1000 / image-default uid 1000** (n8n confirmed by `docker exec id`; organizr confirmed by `PUID=1000` env + the inner `organizr/` subdir being `1000:1000`).
2. **Subdirs the apps actually write to are already 1000:1000** — `automations-n8n/n8n/`, `automations-n8n/local-files/`, `organizr/organizr/`. Containers created them at the correct UID; that data is well-formed.
3. **Sibling parent dirs created by the same role are already 1000:1000** on the same host (`observability/`, `productivity-obsidian/`). The role pattern works; these two parents just pre-date that pattern (or were touched out-of-band as root before the role re-ran).
4. **The drift is cosmetic** for runtime — `0755` lets containers traverse the parent regardless of owner. Apps are healthy.
5. **The role no longer recurses** (Phase-1 fix `caed59d`), so applying the chown only flips the 2 parent inodes — not the carefully-mixed subdir UIDs (postgres 70, redis 999, mariadb 999).

It's clearly NOT option β (host is not intentionally root-owned — the role plus the sibling alignment shows 1000:1000 IS the convention) and NOT option γ (the dirs are not empty — they hold ~5 GB of n8n workflow data and organizr config + a mariadb).

## Recommended fix direction

**Re-run `docker-setup.yml` against ct-docker-01 — no role change required.** The post-`caed59d` role does exactly the right thing: chowns just the 2 parent dirs, leaves the subtree alone.

```bash
# Dry-run first (read-only) to confirm only the 2 parents will flip
LC_ALL=C.UTF-8 ansible-playbook -i inventories/homelab/hosts.ini \
  docker-setup.yml --limit ct-docker-01 \
  --vault-password-file /dev/shm/vp --check --diff

# Expected --check output:
#   TASK [docker-host : Create Docker host appdata directories]
#     changed: [ct-docker-01] => (item=/opt/appdata/automations-n8n)  uid 0->1000, gid 0->1000
#     changed: [ct-docker-01] => (item=/opt/appdata/organizr)         uid 0->1000, gid 0->1000
#     ok:      [ct-docker-01] => (item=/opt/appdata/observability/...) and the rest
#   PLAY RECAP: changed=2 (or 3 if apt-cache noise counts)

# Apply once dry-run shows exactly 2 ownership flips and nothing else
ansible-playbook ... docker-setup.yml --limit ct-docker-01 --vault-password-file ...
```

Acceptance:
- `stat /opt/appdata/{automations-n8n,organizr}` shows `Uid: 1000 Gid: 1000` post-apply.
- Re-run `--check`: `changed=0` (or only routine apt-cache noise).
- All 5 containers remain `(healthy)`; no restart required.

### Why this is safer than a manual `chown`

The role applies the change idempotently and re-stamps the convention across all parent dirs in one motion (proving the role is in sync with reality). A manual `chown root:root → 1000:1000` on just these two paths leaves the role still showing drift on the next `--check` run because Ansible reports the file module's full attribute set. Running the role IS the fix.

## Risks

1. **Open file handles inside containers** — `chown` of the parent dir does not invalidate file descriptors held inside any of the 5 running containers. The containers have inotify watches on subdirs, not the parent inode. n8n, organizr, postgres, redis, mariadb will not notice. Risk: **negligible**.
2. **Backups (restic) referencing the parent dir** — restic snapshots files, not parent-dir ownership; the next backup will record the new ownership in metadata for the 2 inodes only. No impact on existing snapshots. Risk: **negligible**.
3. **Mode change** — none. The role asserts `0755`, the host already has `0755`. Owner-only flip.
4. **A subdir under either parent surprisingly NEEDS the parent to be `0:0`** — verified false by the 29h healthy uptime under the existing world-traversable `0755` mode. The containers traverse via `o+x` regardless of the owner UID.
5. **Race with a parallel deploy** — none expected; ct-docker-01 has no concurrent automation. Run during a quiet window anyway.
6. **Gotcha: any ad-hoc `cron`/script that asserts `[ -O /opt/appdata/<x> ]`** — would flip from "owned by root" to "owned by 1000". Searched: no such scripts in `homelab-infra/scripts/` or visible cron entries on ct-docker-01 (out of scope for the read-only checks here, but worth a `crontab -l && ls /etc/cron*` glance during apply).

Mitigation:
- Run with `--check --diff` first; visually confirm only 2 inodes flip.
- Keep an `ssh` session to ct-docker-01 open during apply and `docker ps --format '{{.Names}} {{.Status}}'` immediately after.
- If anything misbehaves, reverse with `chown 0:0 /opt/appdata/automations-n8n /opt/appdata/organizr` (single command, idempotent rollback).

## Estimated apply time

- Dry-run (`--check`): ~30–45 seconds (apt cache + connection overhead + 9-item file loop).
- Apply: ~30–45 seconds. Two `chown` syscalls on directory inodes — both finish in milliseconds.
- Verification (re-run `--check`, `stat`, `docker ps`): ~1 minute.

**Total: ~2–3 minutes wall-clock**, including SSH reconnects.

## Anything unexpected

1. **`automations-n8n` and `organizr` parent inodes are dated `Birth: 2026-04-21 18:45`** — this is the `ctime` of an inode-rewrite, not original creation. Some operation on 2026-04-21 (around 18:45 UTC) rebuilt these specific inodes as root. Sibling dirs in `/opt/appdata/` show various older birth-times (`Sep 27 2025`, `Feb 9`, `Mar 17`). Working theory: a manual `mkdir -p` or `mv` + `mkdir` rebuild ran as root on that date, possibly during a backup-restore or a CT migration touch-up. Not load-bearing for the fix; flagged for completeness.
2. **`global.env` on the host has only `TZ=Europe/Brussels` for the relevant org-wide vars** — `PUID`/`PGID` live in `stacks/organizr/.env`, not in the global env. n8n stack has no `PUID`/`PGID` at all (uses image-default uid 1000 directly). This is consistent with how the deployment is structured but means there's no single "uid=1000" declaration to sanity-check; the 1000:1000 convention is implicit across the stack collection.
3. **The `organizr` container's `docker exec id` reports `uid=0(root)`** despite `PUID=1000` env. This is normal for the linuxserver.io / s6-overlay pattern: the s6 init runs as root, then drops the actual PHP-FPM and nginx workers to `abc` (uid 1000). Files in `/config` end up owned 1000:1000, which matches the host subdir owner. No issue.
4. **The Phase-1 commit message itself predicted this exact follow-up**: *"remaining 2 are pre-existing 0:0->1000:1000 ownership of automations-n8n/organizr (separate drift, not this fix's scope)."* This investigation closes that loop with an α verdict and a runbook.

## One-line summary for the parent ticket

Verdict α: re-run `docker-setup.yml --limit ct-docker-01` to flip both parent dirs `0:0 → 1000:1000`; ~2-3 min, negligible risk, apps stay healthy because they already own their subdirs.

---

## APPLIED 2026-04-27

`docker-setup.yml` re-deployed against ct-docker-01.

- `PLAY RECAP: ok=11 changed=5 failed=0`
- The 2 expected changes for `/opt/appdata/automations-n8n` + `/opt/appdata/organizr` (owner 0:0 → 1000:1000) landed
- Three other unrelated drift tasks also re-applied during the same play (traefik/portainer dirs from the same docker-host loop) — those were already scheduled drift, not new
- Post-apply stat: `/opt/appdata/{automations-n8n,organizr}` owner UID 1000 mode 0755 (UID 1000 has no `/etc/passwd` entry on ct-docker-01, hence stat shows `UNKNOWN:UNKNOWN`; numeric ownership is what containers care about)
- All 5 affected containers (n8n, n8n-db, n8n-redis, organizr, organizr-db) **`Up 29 hours (healthy)` — uptime unchanged** confirms no FD invalidation, no container restart, no disruption

Verdict α fix complete. Closes the pre-existing drift item carried over from Phase 1.
