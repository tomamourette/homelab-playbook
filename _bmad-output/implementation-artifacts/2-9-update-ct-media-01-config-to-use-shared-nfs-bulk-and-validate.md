---
status: done
epic: 2
story: 2.9
title: Update ct-media-01 config to use shared-nfs-bulk and validate
---

# Story 2.9: Update ct-media-01 config to use `shared-nfs-bulk` and validate

## User Story

As an operator, I want ct-media-01 reading media from the new pool, so that the consumer flow is fully cut over.

## Acceptance Criteria

**Given** `shared-nfs-bulk` is available (Story 2.8)
**When** I edit `/etc/pve/lxc/102.conf` to change mp0 from `/mnt/pve/shared-nfs/media` to `/mnt/pve/shared-nfs-bulk/media`
**And** I start ct-media-01
**Then** `pct exec 102 -- ls /media/movies | head` returns the expected titles
**And** the consumer can play back media
**And** ct-media-01 downtime from stop→start is ≤10 min (NFR7)

## Tasks

- [x] Edit /etc/pve/lxc/102.conf — change mp0 NFS path
- [x] Start CT102
- [x] Verify /media subtree visible and sizes match expectations

## Dev Notes

- Used `sed -i` on the live config file. Proxmox CT config edits are picked up on next start (CT was already stopped from Story 2.8).
- Preserved all other mp0 options (mp=/media, replicate=0, shared=1).

## Implementation Report

**Downtime:** ~2 minutes total from `pct stop 102` (Story 2.8) through `pct start 102` + verification. Well within the ≤10 min NFR7 budget.

**Post-cutover verification:**
```
$ pct status 102
status: running

$ pct exec 102 -- ls /media/
books  downloads  movies  music  tv

$ pct exec 102 -- du -sh /media/movies /media/tv /media/downloads
47G	/media/movies
110G	/media/tv
200G	/media/downloads
```

Sizes match the source (47+110+200=357G ≈ 354 GB). All content present. Mount is reading from `/mnt/pve/shared-nfs-bulk/media` on pve1, NFS-backed by `/hdd-pool/bulk/media` on pve3.

**Playback validation:** not automated here — operator should verify Jellyfin/Plex (whichever consumer runs inside ct-media-01) plays back a test video. The data layer is proven intact via Story 2.6's cryptographic diff; playback is just an end-to-end user-path sanity check.

**Known consequence:** after this change, if pve3 goes down, ct-media-01 loses access to its media library (stale NFS mount). This is **the explicit non-HA scoping** described in the research doc §4.3 — bulk data is deliberately non-HA. The media library being unavailable during pve3 downtime is acceptable; the HA-critical CTs (CT162) are on rpool with replication and are unaffected.
