# PBS Migration-Window Datastore — Operational Runbook

**Purpose:** Temporary Proxmox Backup Server datastore that holds backups of all cluster CTs/VMs during the pve3 storage migration (Epics 1-3 of the PVE3 storage migration plan). Exists for the migration window only — will be decommissioned once the permanent PBS datastore on pve3 (Epic 2, Story 2.8) is proven.

**Created:** 2026-04-20 (Story 1.2)
**Expected lifetime:** ~4 weeks
**Owner:** Tom (homelab operator)

---

## Quick Reference

| Item | Value |
|------|-------|
| PBS UI | `https://192.168.50.155:8007` |
| Host (LXC) | CT105 `ct-pbs-migration` on pve2 |
| Datastore | `migration-window` |
| PVE storage ID | `pbs-migration` (cluster-wide) |
| Token | `root@pam!pve-cluster` |
| Token ACL | `DatastoreBackup` on `/datastore/migration-window` |
| Fingerprint (SHA-256) | `d2:6e:ee:4f:1d:e8:e3:50:a1:ab:5b:3e:cb:5d:e4:e6:a7:cc:7c:c5:0c:b5:57:66:d4:d0:97:d5:72:f9:82:50` |
| Credentials file | `/root/.pbs-migration-credentials` on pve2 (chmod 600, NOT in git) |
| Prune policy | keep-last=2 (daily job `mw-prune`) |
| GC schedule | weekly, Sun 02:00 (`gc-schedule` on datastore) |
| Verify job | `verify-weekly`, Sun 03:00, `ignore-verified=1`, `outdated-after=7d` |
| Datastore capacity | 500 GB (491 GiB usable after fs overhead) |
| Thin pool (pve2) | `pve/data`, 794 GiB; monitor `data_percent` ≤ 85% |

---

## Reaching the PBS UI

From any machine on the `192.168.50.0/24` LAN:

```
https://192.168.50.155:8007
```

- Browser warning is expected (self-signed cert). The SHA-256 fingerprint is pinned in PVE's storage.cfg, which is what actually matters for the backup pipeline — the browser warning is only for humans clicking through.
- Login: `root@pam` with the CT105 root password. Retrieve the password from pve2:
  ```bash
  ssh pve2 'grep ^CT105_ROOT_PASSWORD /root/.pbs-migration-credentials'
  ```

## Console access to CT105

```bash
# From pve2 — interactive console
ssh pve2 'pct enter 105'

# From pve2 — run a one-shot command
ssh pve2 'pct exec 105 -- <command>'

# Start/stop
ssh pve2 'pct start 105'
ssh pve2 'pct stop 105'
```

---

## Using the datastore from PVE

The datastore is registered cluster-wide as `pbs-migration`. You can use it from any pve node (pve1, pve2, pve3) without further configuration.

### Ad-hoc backup of a CT/VM

```bash
ssh pve<N> 'vzdump <VMID> --storage pbs-migration --mode snapshot'
```

### Scheduled backups

Either add a backup job via the PVE web UI (Datacenter → Backup → Add, select `pbs-migration` as Storage) or drop into `/etc/pve/jobs.cfg`:

```
vzdump: backup-migration-window
    schedule mon..sun 22:00
    storage pbs-migration
    mode snapshot
    all 1
    notes-template "Migration-window nightly"
```

### List backups in the datastore

```bash
ssh pve2 'pvesm list pbs-migration'
```

### Restore a CT/VM

```bash
# From any pve node, restore CT152 snapshot into a test VMID (e.g. 199)
ssh pve2 'pct restore 199 pbs-migration:backup/ct/152/2026-04-20T19:19:00Z --storage local-lvm'
```

---

## Token rotation

Rotate if: (a) the secret is exposed, (b) the migration window extends past 14 days, or (c) when preparing for decommission.

```bash
# 1. Generate a new token inside CT105
ssh pve2 'pct exec 105 -- proxmox-backup-manager user generate-token root@pam pve-cluster-v2'

# 2. Grant the new token the DatastoreBackup role
ssh pve2 'pct exec 105 -- proxmox-backup-manager acl update /datastore/migration-window DatastoreBackup --auth-id "root@pam!pve-cluster-v2"'

# 3. Update PVE storage.cfg with the new secret
ssh pve2 'pvesm set pbs-migration --username "root@pam!pve-cluster-v2" --password "<new-secret>"'

# 4. Revoke the old token
ssh pve2 'pct exec 105 -- proxmox-backup-manager user delete-token root@pam pve-cluster'

# 5. Update /root/.pbs-migration-credentials on pve2 to reflect the new id + secret
```

---

## Prune policy

Kept deliberately tight to avoid the 491 GiB datastore filling during the migration window. The cluster has ~1.2 TB of running CT/VM storage; at typical PBS 2-3x compression that means two full cluster snapshots of all guests fit with margin.

- **Job:** `mw-prune`
- **Keep:** last 2 snapshots per VMID per backup-group
- **Schedule:** daily (runs at a default time chosen by PBS)

Adjust with:

```bash
ssh pve2 'pct exec 105 -- proxmox-backup-manager prune-job update mw-prune --keep-last <N>'
```

Garbage collection (reclaim disk after pruning) is a separate operation. Run manually after Story 1.3 full-cluster backup completes to force disk reclaim, or schedule a GC job:

```bash
ssh pve2 'pct exec 105 -- proxmox-backup-manager garbage-collection start migration-window'
```

---

## Monitoring during the migration window

Daily sanity check (anytime during the migration):

```bash
ssh pve2 'pvesm status | grep pbs-migration'
ssh pve2 'pct exec 105 -- df -h /var/lib/proxmox-backup'
ssh pve2 'pct exec 105 -- systemctl is-active proxmox-backup proxmox-backup-proxy'
```

Expected: active/active, datastore status `active`, and the mount has enough free space for the next planned backup. If used > 85%, trigger a GC run or tighten the prune policy.

## Thin-pool pressure monitoring (critical)

**Why this matters:** the datastore is a 500 GB ext4 fs *inside a thin-provisioned LV* on pve2's `pve/data` thin pool (794 GiB). `df` inside CT105 reports ext4 fill, which is meaningless for thin-pool pressure. When the thin pool hits 100%, ALL LVs on pve2 wedge — including CT151, CT152, CT153.

**Manual check:**
```bash
ssh pve2 'lvs -o lv_name,lv_size,data_percent,metadata_percent pve/data'
# data_percent should be < 85%; alert above 85%, critical above 95%
```

**Recommended alerting:** wire this into the existing Prometheus storage-monitoring project (see `project_storage_monitoring.md` memory). Add a textfile collector that writes `lvs --reportformat json` output periodically and scrape with node_exporter. Alert rules:
- Warning: `data_percent > 70`
- High: `data_percent > 85`
- Critical: `data_percent > 95` (at this point the migration is at risk; run emergency GC immediately)

## Fingerprint drift detection

If PBS's TLS cert ever regenerates (package update, manual rotation, container reinstall), the fingerprint in cluster storage.cfg no longer matches and all backups silently fail. Daily check:

```bash
# Run on pve1 or pve3 (any node except pve2 where PBS lives):
LIVE_FP=$(openssl s_client -connect 192.168.50.155:8007 </dev/null 2>/dev/null \
  | openssl x509 -fingerprint -sha256 -noout | cut -d= -f2)
STORED_FP=$(pvesm config pbs-migration | awk '/fingerprint/ {print $2}')
[ "$LIVE_FP" = "$STORED_FP" ] || echo "PBS fingerprint drift detected: live=$LIVE_FP stored=$STORED_FP"
```

If drift is detected, update stored fingerprint:
```bash
pvesm set pbs-migration --fingerprint "$LIVE_FP"
```

---

## Decommissioning (post-migration)

**⚠️ Timing gotcha — this datastore must OUTLIVE Epic 3 and must be handled specially for Epic 5:**

The naïve read is "decommission after Epic 3 (pve3 rebuild) because that's what we set this up for." That is **WRONG**. Epic 5 reinstalls pve2 — where this datastore physically lives. If we decommission after Epic 3 but before Epic 5, the backup safety net during pve2's own reinstall is gone. The migration-window PBS must survive until Epic 5 is complete OR be replaced by an equivalent before pve2 is touched.

**Two paths, choose based on schedule:**

### Path A — keep migration-window PBS alive until after Epic 5 (simpler)

**Trigger conditions** (ALL must be true):
1. Epic 2 Story 2.10 ("Permanent PBS datastore on hdd-pool/pbs") marked done
2. Epic 3 complete (pve3 reinstall + data restore)
3. Epic 5 complete (pve1 + pve2 both reinstalled to ZFS)
4. At least one full cluster backup + verified restore has run against the new permanent pve3 PBS datastore

Then proceed with the "Decommission procedure" below.

### Path B — evacuate before pve2 reinstall (required if Path A is infeasible)

**When to use:** if Epic 5 is scheduled before the permanent pve3 PBS is fully trusted, OR if you want to free pve2's 500 GB thin-pool allocation earlier.

**Pre-Epic 5-pve2-reinstall checklist:**
1. Ensure the permanent pve3 PBS datastore (`hdd-pool/pbs`) exists and has taken at least one verified full-cluster backup.
2. Sync migration-window chunks to the new permanent datastore:
   ```bash
   # On the new permanent PBS (pve3):
   proxmox-backup-manager sync-job create mw-evac \
     --store hdd-pool-pbs --remote pbs-migration@pve2 \
     --remote-store migration-window --schedule 'now'
   ```
3. Verify the sync copied everything: snapshot count and total size match on both sides.
4. Remove `pbs-migration` from cluster storage.cfg only AFTER sync verification passes.
5. Then proceed with CT105 destroy.

### Decommission procedure (both paths)

**Decommission procedure:**

```bash
# 1. Verify no backup jobs still reference pbs-migration
ssh pve2 'grep -l pbs-migration /etc/pve/jobs.cfg'
# (should return no matches — edit /etc/pve/jobs.cfg to remove any migration-window backup jobs first)

# 2. Remove the storage from the cluster
ssh pve2 'pvesm remove pbs-migration'

# 3. Shut down and destroy CT105
ssh pve2 'pct stop 105'
ssh pve2 'pct destroy 105 --purge'

# 4. Remove the credentials file on pve2
ssh pve2 'rm /root/.pbs-migration-credentials'

# 5. Mark Story 1.2 decommission done in _bmad-output/implementation-artifacts/
#    (no separate story required — add a note to 1-2-set-up-migration-window-pbs-datastore-off-pve3.md)
```

**Reclaimed:** ~500 GB on pve2 `local-lvm` thin pool, plus 8 GB for the CT rootfs. Returns pve2 to its pre-Story-1.2 storage state.

---

## Failure modes & recovery

### CT105 won't start after pve2 reboot

```bash
ssh pve2 'pct start 105'
# Check journal on failure
ssh pve2 'journalctl -u pve-container@105 --no-pager -n 50'
```

Most likely cause: `onboot 1` deferred start while pve2 was still coming up. Usually resolves on manual start. If the mountpoint volume is missing, pvesm may have failed to activate `local-lvm` — check `lvs pve | grep 105`.

### PBS proxy fails with EACCES on rrdb

Same as the install-time gotcha. Fix:

```bash
ssh pve2 'pct exec 105 -- chown backup:backup /var/lib/proxmox-backup'
ssh pve2 'pct exec 105 -- systemctl reset-failed proxmox-backup-proxy'
ssh pve2 'pct exec 105 -- systemctl start proxmox-backup-proxy'
```

### Fallback: operator workbench (CT150) unreachable during backup sweep

If CT150 ct-dev-homelab is down (pve1 rebooting, etc.) and Story 1.3's backup sweep needs to run, use the fallback script on pve2 itself:

```bash
ssh pve2 '/root/bin/backup-sweep.sh 2>&1 | tee /root/backup-sweep-$(date +%F).log'
```

The script contains the priority-ordered VMID list from Story 1.3 AC and runs `vzdump` sequentially against `pbs-migration`. It tolerates individual backup failures (logs and continues) rather than aborting the sweep.
```

### Datastore full

Immediate triage:

```bash
# Force prune
ssh pve2 'pct exec 105 -- proxmox-backup-manager prune-job list'
# Run GC to reclaim
ssh pve2 'pct exec 105 -- proxmox-backup-manager garbage-collection start migration-window'
# If still not enough, tighten retention
ssh pve2 'pct exec 105 -- proxmox-backup-manager prune-job update mw-prune --keep-last 1'
```

### Fingerprint rotation (CT regenerated cert)

If the PBS cert is regenerated (should never happen unless CT is rebuilt), update the pinned fingerprint:

```bash
# Grab new fingerprint
NEW_FP=$(ssh pve2 'pct exec 105 -- proxmox-backup-manager cert info | grep "Fingerprint (sha256)" | awk "{print \$3}"')
# Update storage.cfg
ssh pve2 "pvesm set pbs-migration --fingerprint $NEW_FP"
```

---

## Credentials reference

All secrets live in `/root/.pbs-migration-credentials` on pve2 (chmod 600). Retrieve with:

```bash
ssh pve2 'cat /root/.pbs-migration-credentials'
```

Never commit this file or any of its contents to git. The runbook references it by path only.
