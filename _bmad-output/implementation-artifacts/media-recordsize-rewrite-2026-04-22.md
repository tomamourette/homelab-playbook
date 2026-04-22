---
date: 2026-04-22
session: Story 2.3 recordsize drift remediation — full media rewrite
outcome: successful
---

# Media rewrite: hdd-pool/bulk 128K → 1M recordsize

## Why

Audit finding (Epic 2 audit agent): `hdd-pool/bulk` had `recordsize=128K` when research §4.2 required `recordsize=1M` for bulk dataset with large media files (1M → better sequential throughput, fewer metadata ops). The property setting was missed during Story 2.3, so all 366 GB of media was written with 128K records. Setting recordsize on an existing dataset only affects future writes, so a full rewrite was needed to realize the performance characteristic.

## Approach

1. Set `recordsize=1M` on `hdd-pool` + `hdd-pool/bulk` (affects future writes only)
2. Created new dataset `hdd-pool/bulk-new` with `recordsize=1M`
3. Background rsync `/hdd-pool/bulk/ → /hdd-pool/bulk-new/` (preserves all permissions/xattrs; writes new blocks at 1M record boundary)
4. ZFS rename swap: `bulk → bulk-old`, `bulk-new → bulk`
5. Stop ct-media-01, re-export NFS, remount on pve1, start ct-media-01
6. Verified file count + SHA-256 match + CT102 reads cleanly

## Timeline

- Rsync duration: ~18 min (459 files, 366 GB, on a single-node RAIDZ1 copy — ~340 MB/s sustained)
- CT102 downtime: ~3 min (shutdown → rename → NFS remount → start)

## Gotcha: stale NFS file handle after server-side rename

After `zfs rename hdd-pool/bulk hdd-pool/bulk-old && zfs rename hdd-pool/bulk-new hdd-pool/bulk` on pve3, the NFS client on pve1 had a stale file handle (CT102 pre-start hook refused with "directory '/mnt/pve/shared-nfs-bulk/media' does not exist").

**Fix:** `umount -l /mnt/pve/shared-nfs-bulk` on pve1; PVE's storage layer automatically remounted on next `pvesm status` query. CT102 then started cleanly.

**Lesson:** server-side ZFS dataset rename invalidates client NFS handles even when the mount path on the server is unchanged. Client must explicitly drop + re-establish the mount. Add this to the pve2 reinstall runbook if a similar pattern is used.

## Results

| Metric | Before | After |
|---|---|---|
| hdd-pool/bulk recordsize | 128K (default) | 1M (local) |
| hdd-pool/bulk USED | 366 GB | 366 GB |
| Files | 459 | 459 |
| SHA-256 spot check on large file | — | match |
| ct-media-01 health | running | running (20 docker containers starting) |

## Retained for soak: hdd-pool/bulk-old

The old 128K-recordsize dataset is kept as a rollback option for ~48 h. After that window, assuming no Plex/Jellyfin issues surface, destroy with `zfs destroy -r hdd-pool/bulk-old`. This reclaims 366 GB on `hdd-pool` but doesn't affect anything else.

Stored state to monitor before destroy:
- Plex library scan completes without errors
- Jellyfin library scan completes without errors
- No file-missing alerts from Sonarr/Radarr/Prowlarr

## Sprint status update

Story 2.3 remains `done` in sprint YAML. The audit-identified drift has been fully remediated. Adding a Dev Notes update to `2-3-create-hdd-pool-datasets-and-tune-properties.md` to reflect the remediation.
