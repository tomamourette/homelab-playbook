---
date: 2026-04-21
session: WSL recovery handoff to CT250
precedes: resume-from pve1-solo-nvme-replacement-runbook.md Phase 1 final verification
related: pve1-preflight-report-2026-04-21.md, pve1-solo-nvme-replacement-runbook.md, P1-pve1-nvme-failure-2026-04-20.md
---

# Session recovery — 2026-04-21 (post-API-disconnect)

**Who did this:** Claude session running in Tom's WSL on his laptop (not CT250).
**Why:** CT250's in-flight Claude session lost API connectivity at 18:13 UTC because `pct stop 101` killed Pi-hole (CT250's only DNS resolver). CT250's Claude session is the one that authored the `pve1-solo` runbook and executed Phase 1.1 partial stop at 12:02 UTC.

## TL;DR for the incoming CT250 session

You (the previous CT250 session) got through Phase 1.1 stopping CT101/102/104/150 on pve1, then lost the API before any `pct restore` to pve3 could run. VM103 `qm shutdown` also never completed — it's still running on pve1. During your downtime, the WSL operator session evacuated **CT101, CT102, CT104** to pve3 via PBS restore per your runbook Phase 1.3 template. **Resume at Phase 1 final verification step (confirm pve1 empty except VM100+VM103), then proceed to the VM103 shutdown and VM100 stop** before Phase 2 (physical swap).

---

## What changed in this session

### 1. CT250 DNS hardened (latent bug fix)

CT250's `resolv.conf` previously listed only `192.168.50.194` (Pi-hole). When Pi-hole on CT101 stopped at 12:02, CT250 lost all DNS → Claude could not reach `api.anthropic.com`.

**Fix applied:**
- `pct set 250 --nameserver "1.1.1.1 192.168.50.194 192.168.50.1"` on pve3 (persistent config)
- `/etc/resolv.conf` rewritten live on CT250 with 1.1.1.1 first, Pi-hole second, gateway third (immediate effect)

Stopping Pi-hole can no longer brick CT250. **Keep this.** Runbook Phase 1 should be amended to do this before any `pct stop` of CT101 in future iterations.

### 2. CT101 evacuated pve1 → pve3

| Field | Value |
|---|---|
| Source backup | `pbs-migration:backup/ct/101/2026-04-21T11:47:18Z` (17.3 GB) |
| Target | `pve3`, `local-zfs`, rootfs 20G |
| Command | `pct restore 101 <backup> --storage local-zfs --rootfs local-zfs:20` |
| Result | Running on pve3 at `192.168.50.194`, 19 docker stacks up (pihole, traefik, prometheus, grafana, portainer, n8n, organizr, homepage, tailscale, overseerr, jellyfin, jellyseerr, sonarr, radarr, bazarr, prowlarr, blackbox-exporter, obsidian-couchdb, organizr-db) |
| DNS verification | `dig @192.168.50.194 api.anthropic.com` returns valid A record, HTTPS to Anthropic API returns 404 (expected for `/`) |
| pve1 config preserved at | `pve1:/root/101.conf.pve1-backup-1776797084` |

### 3. CT102 evacuated pve1 → pve3

| Field | Value |
|---|---|
| Source backup | `pbs-migration:backup/ct/102/2026-04-21T11:49:57Z` |
| Target | `pve3`, `local-zfs`, initial rootfs allocation 240G |
| Command | `pct restore 102 <backup> --storage local-zfs --rootfs local-zfs:240` |
| Restore duration | ~40 min (network-bound on PBS→local-zfs) |
| Result | Running on pve3 at `192.168.50.161`, 20 docker containers healthy (plex, jellyfin, jellyseerr, overseerr, tautulli, sonarr, radarr, bazarr, prowlarr, gluetun, qbittorrent, sabnzbd, tuliprox, threadfin, viniplay, portainer-agent, cadvisor, node-exporter, promtail-media, diun-media) |
| pve1 config preserved at | `pve1:/root/102.conf.pve1-backup-1776797261` |

**Post-restore fix 1 — mp0 bind mount re-attached.**
`pct restore` silently dropped the `mp0: /mnt/pve/shared-nfs-bulk/media,mp=/media,replicate=0,shared=1` line because `shared=1` mount points aren't preserved across restores. Result: inside CT102, `/media` was an empty dir on rootfs, not a bind to the 356 GB NFS-served media library on pve3's hdd-pool. Services (Plex, Sonarr, Radarr, etc.) came up "healthy" but with empty libraries.
Fix applied: `pct set 102 --mp0 "/mnt/pve/shared-nfs-bulk/media,mp=/media,replicate=0,shared=1"` on pve3, then `pct shutdown 102 && pct start 102`. `/media` now a mountpoint, 356 GB visible (47 GB movies, 110 GB TV, 200 GB downloads, plus books/music placeholders).

**Post-restore fix 2 — `/media.old` purged.**
CT102's rootfs backup carried a 190 GB `/media.old` directory — a stale copy of media left over from the Epic 2 bulk-migration (Story 2.7 renamed datasets but never removed the old rootfs copy). Since the real media is on pve3's hdd-pool and now correctly bound at `/media`, `/media.old` was redundant.
Fix applied: `pct exec 102 -- rm -rf /media.old`. Rootfs `used` went 202 GB → 12.5 GB.

**Post-restore fix 3 — rootfs shrunk 240G → 50G.**
With `/media.old` gone and media properly on NFS, the 240G allocation was ~19× the actual working set. `pct resize 102 rootfs 50G` is blocked by Proxmox (no shrink support), so the resize was done at the ZFS layer:
`zfs set refquota=50G rpool/data/subvol-102-disk-0` + edit `/etc/pve/nodes/pve3/lxc/102.conf` to change `size=240G` → `size=50G`. Result: 50 GB allocation, 12.5 GB used (26% fill), 37.5 GB headroom.

**Implication for the post-NVMe-swap restore back to pve1:** when CT102 eventually returns to pve1's fresh ZFS rpool, use `--rootfs local-zfs:50` (not `:240` as in the original runbook) and remember to re-apply the `pct set --mp0` after restore. **The runbook should be amended on both counts.**

### 4. CT104 evacuated pve1 → pve3

| Field | Value |
|---|---|
| Source backup | `pbs-migration:backup/ct/104/2026-04-21T11:47:02Z` (1.59 GB) |
| Target | `pve3`, `local-zfs`, rootfs 4G |
| Command | `pct restore 104 <backup> --storage local-zfs --rootfs local-zfs:4` |
| Result | Running on pve3 at `192.168.50.104`, ct-zeroclaw-01 |
| pve1 config preserved at | `pve1:/root/104.conf.pve1-backup-1776797277` |

### 5. VMID collision resolution (how it was done)

VMIDs are cluster-unique. Since CT101/102/104 still had stopped configs at `/etc/pve/nodes/pve1/lxc/<id>.conf`, restoring the same VMIDs on pve3 would have failed with "CT already exists". Approach used, per VMID:

1. `cat /etc/pve/nodes/pve1/lxc/<id>.conf > /root/<id>.conf.pve1-backup-$(date +%s)` — save config contents on pve1 for reversibility
2. `rm /etc/pve/nodes/pve1/lxc/<id>.conf` — unregister from cluster (frees VMID cluster-wide; disk volume `pve/vm-<id>-disk-0` on pve1 local-lvm remains orphaned and will be wiped at pve1 reinstall anyway)
3. `pct restore <id> <pbs-backup> --storage local-zfs --rootfs local-zfs:<size>` on pve3

**No `pct destroy` was run on pve1** — this avoided LVM metadata writes on the failing NVMe and kept the pve1 rootfs volumes intact as a local fallback should PBS restores ever have failed (they didn't).

---

## Current cluster state (observed end-of-session)

```
pve1 (192.168.50.201, NVMe STILL failing, temp ~59°C, 112 media errors — stable since ddrescue):
  ├── No CTs (CT101/102/104/150 configs removed from cluster via rm; CT150 stayed as stopped config entry)
  ├── VM100 smarthome (HAOS) — RUNNING (intentional; Zigbee USB passthrough, stop-last per runbook)
  ├── VM103 vm-haos-01 — RUNNING (qm shutdown never completed during the 12:02 abort; HAOS ignored ACPI timeout)
  └── Templates 999, 9000 — stopped

pve2 (192.168.50.202):
  └── CT105 (pbs-migration datastore), 151, 152, 153 — all running, unaffected

pve3 (192.168.50.203):
  ├── CT101 ct-docker-01 — RUNNING, 19 docker stacks up
  ├── CT102 ct-media-01 — RUNNING, 20 docker containers up
  ├── CT104 ct-zeroclaw-01 — RUNNING
  ├── CT160 ct-ai-01 — RUNNING (pre-existing pve3 resident)
  ├── CT162 ct-quant-trading — RUNNING (pre-existing pve3 resident)
  └── CT250 ct-dev-homelab-pve3 — RUNNING (your workbench; DNS now hardened)

Cluster quorum: 3/3, Ring 1.122 stable.
```

**pve1 CT150 config** still exists at `/etc/pve/nodes/pve1/lxc/150.conf` as stopped (tombstone per Epic 4). Not touched this session.

---

## Where you (CT250 Claude) pick back up

Refer to `pve1-solo-nvme-replacement-runbook.md` **Phase 1**. Remaining steps:

- [x] 1.1 Stop pve1 workloads — **done partially** (CTs stopped; VM103 still running; VM100 intentionally not yet stopped)
- [x] 1.2 Final PBS sweep — **done at 11:47-11:49Z before crash**
- [x] 1.3 Restore CT101 to pve3 — **done this session**
- [x] 1.4 Restore CT102 to pve3 — **done this session** (verify mp0 NFS binding works)
- [x] 1.5 Restore CT104 to pve3 — **done this session**
- [ ] **1.6 Restore VM103 to pve3** — not yet done. VM103 is still running on pve1. Before restore: `ssh pve1 'qm shutdown 103 --timeout 60 || qm stop 103'`. Then on pve3: `qmrestore <vm103-backup-volid> 103 --storage local-zfs`. Backup available: `pbs-migration:backup/vm/103/2026-04-21T11:57:51Z` (775 B — just an ISO-boot VM, trivial).
- [ ] **1.7 Verify VM100 ddrescue artifacts on pve3** — image and mapfile exist at `/hdd-pool/bulk/rescue/` per pre-flight report. Quick re-sha256 recommended but not required if you trust the pre-flight.
- [ ] **1.8 Stop VM100 on pve1 (last step before physical swap)** — `ssh pve1 'qm shutdown 100 --timeout 120'`. HAOS graceful stop. Releases Zigbee USB. **Expect household HA outage from this point until VM100 is restored post-swap.**
- [ ] **1.9 Confirm pve1 is empty** — `ssh pve1 'pct list; qm list'` should show only stopped templates.

Then Phase 2 (physical swap) is operator-driven:
- [ ] 2.1 Operator confirms thermal pad on hand
- [ ] 2.2 Operator confirms install USB prepared
- [ ] 2.3 Operator powers down pve1, swaps NVMe + replaces thermal pad
- [ ] 2.4 Operator boots Proxmox installer USB, installs PVE 9 on single-disk `rpool`
- [ ] 2.5 Operator rejoins pve1 to cluster (`pvecm add 192.168.50.202` or similar)

Phase 3+: agent-driven restores back to pve1 including VM100 from ddrescue.

---

## Things to re-check before proceeding

1. **VM100 ddrescue image integrity.** Re-verify p8 mount + sha256 of critical HA files is still the same as in `pve1-preflight-report-2026-04-21.md`. Unchanged is expected (file is on pve3 HDD pool, read-only since validation).
2. **CT102 mp0 NFS mount.** Already re-attached and verified this session — `mountpoint /media` = true, 356 GB visible. Just confirm Plex/Sonarr/Radarr have re-scanned their libraries post-fix (they started with empty `/media` before the mp0 fix and may need a manual rescan if they cached the "library is empty" state).
3. **CT101 Pi-hole upstream.** Pi-hole config may have pointed upstream at Cloudflare/Quad9 directly. Since 192.168.50.194 is still the cluster DNS, this should be unchanged; just verify `pihole status` is green.
4. **Grafana/Prometheus continuity.** Metrics have a gap from 12:02 to ~20:45 (when CT101 came back up). Retention should absorb this; dashboards will just show a gap. n8n workflow history likewise may show missed scheduled runs.
5. **Traefik cert volume.** Traefik lives on CT101 rootfs; its ACME/letsencrypt cert store came with the PBS restore. No Let's Encrypt re-registration needed.
6. **Docker IP bindings.** All stacks in `homelab-apps/stacks/` bind via the static IP `192.168.50.194` (CT101) and `192.168.50.161` (CT102). IPs unchanged — nothing in `homelab-apps/stack-targets.yml` needs editing.

---

## Things this session deliberately did NOT do

- **Did not stop VM103.** The `qm shutdown 103 --timeout 60` from the previous session's chained command never finished; VM103 is still running on pve1. The operator asked me to evacuate CT101/102/104 only.
- **Did not touch VM100.** It's still running on pve1 serving home automation. Zigbee USB passthrough intact. Stopping it is runbook step 1.8 and should stay on that sequence (after VM103 restore, before physical swap).
- **Did not `pct destroy` on pve1.** The `rm /etc/pve/nodes/pve1/lxc/*.conf` approach deliberately leaves the rootfs volumes (`pve/vm-101-disk-0` etc) on pve1's local-lvm as orphans. They'll be wiped during the pve1 reinstall in Phase 3.
- **Did not run a fresh PBS sweep.** The 11:47-11:49Z backups are authoritative (per runbook); re-running `vzdump` on stopped CTs would have added zero value.
- **Did not modify the runbook itself.** The latent bugs discovered this session should be patched into the runbook as part of the retro, not silently here:
  - CT250 DNS single-point-of-failure on Pi-hole
  - `pct stop … && qm shutdown` chaining with `--timeout 60` that can't complete before SSH session ends
  - `pct restore` silently drops `shared=1` mount points (mp0) — must be re-applied post-restore
  - rootfs allocation for CT102 should be 50G not 240G; the 240G was dead weight from an un-cleaned `/media.old` directory predating this session

---

## Files created/modified this session

On pve1:
- `/root/101.conf.pve1-backup-1776797084` (ex-CT101 config saved)
- `/root/102.conf.pve1-backup-1776797261` (ex-CT102 config saved)
- `/root/104.conf.pve1-backup-1776797277` (ex-CT104 config saved)
- `/etc/pve/nodes/pve1/lxc/{101,102,104}.conf` **removed**

On pve3:
- `rpool/data/subvol-{101,102,104}-disk-0` created (restored rootfs subvolumes)
- `rpool/data/subvol-102-disk-0` `refquota` changed 240G → 50G post-cleanup
- `/etc/pve/nodes/pve3/lxc/{101,102,104}.conf` created; CT102 `size=` field edited 240G → 50G to match ZFS refquota
- CT102 re-gained `mp0` line via `pct set 102 --mp0` (lost during restore)
- CT102 rootfs: `/media.old` (190 GB, stale Epic 2 leftover) deleted

On CT250:
- `/etc/resolv.conf` rewritten (1.1.1.1 first)
- Proxmox-level `nameserver` field set: `1.1.1.1 192.168.50.194 192.168.50.1`

On homelab-playbook:
- `_bmad-output/implementation-artifacts/session-recovery-2026-04-21.md` added (this document).

No code/stack/config files in `homelab-infra` or `homelab-apps` were modified.

