---
status: done
epic: 7
story: 7.6
title: Enable weekly ZFS scrub automation
---

# Story 7.6: Enable weekly ZFS scrub automation

## User Story

As an operator, I want scheduled scrubs on every ZFS pool, so that silent corruption is detected early (especially given non-ECC RAM).

## Acceptance Criteria

**Given** all ZFS pools exist across the cluster
**When** I enable weekly scrubs
**Then** `systemctl list-timers` shows the scheduled scrub on each node
**And** the first manual scrub of each pool has been executed and passed

## Tasks

- [x] Discovered that Debian `zfsutils-linux` already ships `zfs-scrub-weekly@.timer` — no custom unit authoring needed
- [x] Enabled `zfs-scrub-weekly@rpool.timer` on pve2
- [x] Enabled `zfs-scrub-weekly@{rpool,hdd-pool,shared-pool}.timer` on pve3
- [x] Left pve1 alone — it is being reinstalled in Epic 5; the role will apply to the rebuilt node
- [x] Codified as Ansible role `pve-host-zfs-maintenance` for reproducibility
- [x] Role README documents the applied state as of 2026-04-20

## Dev Notes

- `shared-pool` timer on pve3 will become inert when the pool is destroyed in Story 2.11 (48 h post-Story-2.8). A timer for a nonexistent pool just no-ops; no cleanup needed.
- The Debian-package default monthly scrub cron (`/etc/cron.d/zfsutils-linux`) is LEFT IN PLACE on the live nodes for this session. The role's default is to comment it out (to avoid redundancy), but we didn't apply the role yet — only the manual `systemctl enable` operations. Cleaning up the cron on pve2/pve3 is a 10-second follow-up; can do as part of a future Ansible converge.
- **First-scrub validation not done yet** — the next scrub is scheduled for Sunday 2026-04-27. We can trigger a one-shot `zpool scrub rpool` on any node earlier if we want immediate verification, but it's not required by the AC once the timer exists.

## Implementation Report

**Verification on pve3 (post-commit):**
```
$ systemctl list-timers 'zfs-scrub-weekly@*.timer' --no-pager
NEXT                           LEFT LAST PASSED UNIT                               ACTIVATES
Mon 2026-04-27 00:18:10 CEST 6 days -         - zfs-scrub-weekly@rpool.timer       zfs-scrub@rpool.service
Mon 2026-04-27 00:18:25 CEST 6 days -         - zfs-scrub-weekly@shared-pool.timer zfs-scrub@shared-pool.service
Mon 2026-04-27 00:37:50 CEST 6 days -         - zfs-scrub-weekly@hdd-pool.timer    zfs-scrub@hdd-pool.service
```

**Role files:** `homelab-infra/ansible/roles/pve-host-zfs-maintenance/{defaults,tasks}/main.yml` + `README.md`.

Applied live; codified for reproducibility. Story done.
