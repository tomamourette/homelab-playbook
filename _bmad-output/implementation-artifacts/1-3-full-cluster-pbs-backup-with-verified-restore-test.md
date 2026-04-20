---
status: done
epic: 1
story: 1.3
title: Full cluster PBS backup with verified restore test
---

# Story 1.3: Full cluster PBS backup with verified restore test

## User Story

As an operator preparing to rebuild pve3's storage,
I want every CT/VM in the cluster backed up to `pbs-migration` and a restore path proven on a representative guest,
So that any rollback or accidental destruction during the migration window is recoverable.

## Acceptance Criteria

**Given** the `pbs-migration` datastore is healthy (established in Story 1.2)
**When** I run a full cluster backup sweep in the priority order and perform a test restore of CT152 to a temporary VMID
**Then** each backup either appears OK in the PBS UI or is logged with a clear failure cause
**And** sizes/timestamps are captured in `pre-migration-backup-manifest.md`
**And** the test restore CT starts, boots Debian, and is cleanly destroyed after verification

## Priority Order (from AC)

Priority list: CT162, CT160, CT102, VM100, VM103, CT101, CT151, CT153, CT104, CT150, CT152.
Dispatched per-node (vzdump must run on the node hosting the guest):

| Node | Guests (in list priority) |
|------|---------------------------|
| pve1 | 102, 100, 103, 101, 104, 150 |
| pve2 | 151, 153, 152 |
| pve3 | 162, 160 |

The three per-node sweeps ran concurrently (separate ssh sessions) to compress wall-clock time while respecting the per-node serial constraint.

## Tasks

- [x] Verify VMID 199 free on all three nodes
- [x] Verify `pbs-migration` storage active on all three nodes (`pvesm status | grep pbs-migration`)
- [x] Launch three parallel per-node vzdump sweeps in priority order with `--mode snapshot`
- [x] Monitor and capture vzdump output to per-node log files under `/tmp/backup-sweep-1.3/`
- [x] Handle VM100 failure gracefully (retry once in `--mode stop`, log cause, continue)
- [x] Diagnose VM100 failure root cause (pve1 NVMe critical medium errors via dmesg)
- [x] Confirm 10 of 11 backups present in PBS via `pvesm list pbs-migration`
- [x] Perform test restore of CT152 → VMID 199 on pve2 using `--storage local-lvm --rootfs local-lvm:15`
- [x] Start CT 199, verify `pct status` running, `uptime` shows fresh boot, Debian 12 confirmed
- [x] Destroy CT 199 with `pct stop` then `pct destroy --purge`; verify VMID released
- [x] Write manifest to `pre-migration-backup-manifest.md` with table, totals, failures, restore details, reproducibility commands

## Dev Notes

- **Datastore:** `pbs-migration` (CT105 ct-pbs-migration on pve2 @ 192.168.50.155, datastore `migration-window`).
- **Approach chosen:** Dispatching vzdump via ssh-per-node rather than invoking the pve2 fallback `/root/bin/backup-sweep.sh`. The fallback script runs vzdump from pve2 and therefore can only target guests on pve2 — the other nodes would silently fail. Per-node dispatch respects Proxmox's guest-locality constraint and also lets the three nodes' backups run concurrently.
- **Priority within node:** preserved the canonical priority. Across nodes, AC priority is partially interleaved (since all three nodes run in parallel), which matches the intent (all critical guests backed up in the first few minutes).
- **VM100 root cause — hardware failure on pve1:** `dmesg` shows `nvme0n1 critical medium error` at sector ~224,110,720 during the second backup attempt. This is unrelated to the USB passthrough (`usb0: host=10c4:ea60`) originally suspected. The bad-sector region intersects VM100's scsi0 LV at the 16.8–17 GiB mark, which is why both snapshot-mode and stop-mode attempts fail at the same percentage. **This is a separate P1 that must be escalated**: pve1's NVMe is developing physical bad sectors. Mitigation options are listed in the manifest's Failures section.
- **CT152 reused backup:** the manifest references the fresh 2026-04-20T19:34:02Z snapshot (from this sweep), not the Story 1.2 test (2026-04-20T19:19:00Z). Both remain in PBS — retention policy (Story 1.2) will handle pruning.
- **VM103 diskless backup:** expected. `vm-haos-01` is a Home Assistant OS VM with no persistent disk attachments in its qemu config — the resulting 778-byte backup is config-only, sufficient for config rebuild but not data restore.
- **Thin-pool warnings on pve1:** several `Sum of all thin volume sizes ... exceeds the size of thin pool pve/data` warnings surfaced during CT101, 104, 150 snapshots. These did not cause failures (thin LVM snapshots are metadata-only until COW activity), but reinforce the general pve1 storage-pressure picture seen alongside the NVMe errors.

## Implementation Report

### Sweep outcome

- **Wall clock:** 2026-04-20T19:32:45Z → 2026-04-20T20:12:17Z, ~40 minutes (pve2 finished at 19:35, pve3 at 19:40, pve1 at 20:12 — driven by CT102 at 31 min).
- **Successful backups:** 10 of 11 guests. All show OK in PBS UI (`pvesm list pbs-migration` confirms the presence and size of each snapshot).
- **Failed backup:** 1 (VM100 smarthome). Logged, retried once in stop mode, identified as pve1 NVMe medium error (not a snapshot-mode or USB-passthrough quirk).
- **Compressed wire volume:** ~249 GiB across successes (CT102 dominates with ~211 GiB; everything else totals ~38 GiB).
- **PBS deduped on-disk:** 182.3 GiB used of 491 GiB (37.11%), leaving 283.8 GiB free — plenty of headroom for incremental sweeps across the migration window.

### Restore test outcome

- Restore of CT152 to VMID 199 on pve2 completed in **1 min 6 s** (66 s). CT started cleanly, Debian 12 bookworm booted, uptime 0 min confirmed fresh start, destroyed in 7 s with no residual storage. End-to-end PBS → pct restore → boot → destroy verified.

### Artifacts

- **Manifest:** `_bmad-output/implementation-artifacts/pre-migration-backup-manifest.md` (sizes, timestamps, failures, reproducibility commands, PBS utilization).
- **Sweep logs:** `/tmp/backup-sweep-1.3/{pve1,pve2,pve3}.log` per-node vzdump output; `/tmp/backup-sweep-1.3/vm100-retry.log` retry with dmesg correlation; `/tmp/backup-sweep-1.3/restore.log` pct restore transcript.
- **Per-node sweep driver scripts:** `/tmp/backup-sweep-1.3/pve{1,2,3}-sweep.sh` (priority ordering + resilience to single-guest failure).

### Risks / Escalations

1. **P1 — pve1 NVMe medium errors (new finding).** `nvme0n1` is reporting critical medium errors at sectors ~224,110,720+ with clustered read failures. VM100 cannot be backed up from its current location. This is **independent of Story 1.3's scope** but surfaced by it. Must be flagged to director before the pve3 migration proceeds — ideally addressed in parallel (VM100 live-migrate to pve2, pve1 NVMe health investigation).
2. **VM100 pre-migration backup absent.** If pve1 is also destabilised during the pve3 migration window, VM100 has no recovery path via PBS. Director should decide whether to (a) proceed with migration leaving VM100 unbacked, (b) live-migrate VM100 to pve2 first and re-sweep, or (c) accept the risk and pause VM100 to attempt a cold `dd conv=noerror,sync` capture.
3. **VM103 diskless backup** is benign but should be noted in migration runbook: restoring this VM requires separate data restoration from whatever external store holds HAOS's disk image.

### Definition of Done

- [x] 10 of 11 guests backed up to pbs-migration successfully (plus VM100 failure logged with root cause)
- [x] Sizes and timestamps captured in manifest
- [x] CT152 test restore executed end-to-end (restore → start → verify Debian boot → destroy)
- [x] Test CT (VMID 199) purged, VMID released
- [x] Failures logged and root-caused
- [x] Reproducibility commands documented
- [x] Story spec file written
