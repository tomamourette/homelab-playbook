# E2-S02 Footprint Evidence (Container Retry)

**Date:** 2026-04-26
**Story:** E2-S02 Verify GitNexus footprint < 500MB RSS — retry against containerised daemon
**Predecessor:** E2-S01.5 (Docker pivot per ADR-015)
**Closes:** architecture AR1
**Branch:** feature/context-stack-e2-gitnexus

## Container under test

- Image: `ghcr.io/abhigyanpatwari/gitnexus:1.6.3`
- Container name: `gitnexus`
- Container ID: `4d3e7b21072c`
- Host PID (PID-1 inside container, host-namespace view): `711040`
- Process: `node gitnexus/dist/cli/index.js serve --host 0.0.0.0 --port 4747`
- Port binding: `127.0.0.1:4747->4747/tcp` (loopback-only, privacy-bounded)
- Health: `Up 2 minutes (healthy)` at start of test

### docker stats snapshot at test start

```
CONTAINER ID   NAME       CPU %   MEM USAGE / LIMIT   MEM %   NET I/O         BLOCK I/O   PIDS
4d3e7b21072c   gitnexus   0.02%   50.82MiB / 8GiB     0.62%   1.66kB / 870B   0B / 0B     11
```

### host ps snapshot at test start

```
    PID    RSS      VSZ  CMD
 711040  81956 11662056  node gitnexus/dist/cli/index.js serve --host 0.0.0.0 --port 4747
```

## Methodology

- Sustained sampling over a 60-second window: 12 samples × 5-second cadence.
- Two metrics captured per sample:
  - `docker stats --no-stream` MEM USAGE (cgroup-aware, sum of all container processes; 11 PIDs).
  - Host-process RSS for PID 711040 via `ps -o rss=` (host-namespace view of container PID-1).
- Idle workload — daemon serving the MCP HTTP endpoint, no parent-folder indexing yet (that is E2-S05). Sustained-load testing is E2-S06 scenario 5.

## RSS samples (12 × 5s = 60s)

| timestamp (UTC) | docker MEM USAGE | host RSS (KB) |
|---|---|---|
| 11:34:19 | 50.82 MiB / 8 GiB | 81956 |
| 11:34:25 | 50.82 MiB / 8 GiB | 81960 |
| 11:34:31 | 51.15 MiB / 8 GiB | 82056 |
| 11:34:37 | 51.15 MiB / 8 GiB | 82056 |
| 11:34:43 | 50.92 MiB / 8 GiB | 82060 |
| 11:34:49 | 50.92 MiB / 8 GiB | 82060 |
| 11:34:55 | 51.17 MiB / 8 GiB | 82064 |
| 11:35:01 | 50.99 MiB / 8 GiB | 82128 |
| 11:35:07 | 50.99 MiB / 8 GiB | 82128 |
| 11:35:13 | 50.99 MiB / 8 GiB | 82132 |
| 11:35:19 | 51.24 MiB / 8 GiB | 82136 |
| 11:35:25 | 51.24 MiB / 8 GiB | 82136 |

Raw samples: `/tmp/e2-s02-rss-samples-2026-04-26.txt`

## Statistics (host-process RSS)

- **PEAK:** 82136 KB / **80.21 MB**
- **MEAN:** 82073 KB / **80.15 MB**
- **P95:**  82136 KB / **80.21 MB**

(Spread across the window: ~180 KB total — the daemon is essentially flat-line at idle.)

## Statistics (docker stats MEM USAGE — cgroup view)

- **PEAK:** 51.24 MiB / **53.73 MB**
- **MIN:**  50.82 MiB / **53.29 MB**

The host-process RSS (~80 MB) is higher than docker stats MEM USAGE (~51 MB) because:
- `docker stats` reports cgroup `memory.current` minus inactive page cache (working-set–style metric).
- `ps -o rss` reports the full resident set of the host process, including shared library pages that may be discounted by cgroup accounting.

The conservative metric (host RSS, **80.21 MB peak**) is the one used for the threshold decision.

## Representative docker stats row (post-sample)

```
CONTAINER ID   NAME       CPU %   MEM USAGE / LIMIT   MEM %   NET I/O         BLOCK I/O   PIDS
4d3e7b21072c   gitnexus   0.02%   51.23MiB / 8GiB     0.63%   1.66kB / 870B   0B / 0B     11
```

CPU stayed at 0.02% (idle daemon), 11 worker PIDs, no block I/O during the window.

## NFR-FOOTPRINT verdict

- **Threshold:** < 500 MB RSS sustained
- **PEAK measured:** 80.21 MB (host-process view) / 53.73 MB (cgroup view)
- **Verdict:** **PASS** — peak is **6.2× under** the 500 MB threshold on the more conservative host-process metric, and 9.3× under on the cgroup metric.

## AR1 closure

**AR1 closed.** GitNexus footprint is well within budget when delivered as a Docker container per ADR-015. The npm-install ABI risk from the original AR1 is fully retired by switching to the official upstream image (`ghcr.io/abhigyanpatwari/gitnexus:1.6.3`), which ships with a compatible glibc/libstdc++ baked in. Container delivery removes both the install-time risk (E2-S01.5 evidence) and the runtime-footprint risk (this story).

## Notes

- This baseline is for an **idle daemon with no graph loaded**. Parent-folder indexing (E2-S05) and active hook traffic (E2-S04, E2-S06) will increase the footprint. The 500 MB budget gives ~420 MB of headroom — ample for a typical homelab parent-folder graph.
- Sustained-load testing (1-hour active session, scenario 5) is part of **E2-S06**; if RSS climbs above 500 MB under load, this NFR will need to be re-opened then.
- The image is 944 MB on registry / 504 MB on disk — those are storage costs, separate from RSS at runtime.
- `127.0.0.1:4747` loopback binding confirmed in the port mapping: external attack surface is zero. Privacy-bounded as required by the architecture.

## Cross-references

- ADR-015 (Docker delivery for GitNexus)
- E2-S01.5 pivot evidence: `e2-s01-5-pivot-evidence.md`
- Original (failed) E2-S02 evidence: `e2-s02-footprint-evidence.md`
- Compose stack: `homelab-apps/stacks/gitnexus/docker-compose.yml`
