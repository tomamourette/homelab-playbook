# Pre-Migration State Snapshot — 2026-04-20

## What this is

A read-only capture of the cluster's configuration and topology, taken on
**2026-04-20** at the start of Epic 1 (pre-migration safety), before any
destructive work on pve3 begins. It is the authoritative reference for
rollback diffing and verification that post-migration state either matches
expectation or deviates in a known, documented way.

## Scope

- Per-node: hostname, kernel, zpool/zfs layout, LVM layout, PVE version,
  storage status, container/VM lists, container/VM configs,
  link-level iface state (`ip -br link/addr`, `ethtool` per iface).
- Cluster-wide: `/etc/pve/storage.cfg`, `pvecm status/nodes`,
  `/etc/pve/corosync.conf`, `ha-manager status`.

## Not captured (by design)

- Live guest data (disks, rootfs contents) — that's covered by the
  Story 1.3 full-cluster PBS backup. This snapshot only preserves
  *configuration and topology* so a rebuilt pve3 can be compared
  against its pre-migration shape.
- Secrets (tokens, keys, `.pbs-migration-credentials`) — those stay on
  pve2 out of git per Story 1.2 policy.

## How to diff against a future state

```bash
# After migration (or any time), re-run the Story 1.4 collection script
# into a sibling dir, e.g. pre-migration-snapshot-2026-05-18/, then:
diff -r pre-migration-snapshot-2026-04-20/ pre-migration-snapshot-2026-05-18/
```

Expected post-Epic-3 differences: pve3 zpool layout (rpool unchanged,
new hdd-pool added), new `/etc/pve/storage.cfg` entries for hdd-pool
pools, CT160/CT162 configs unchanged.
