---
story: E2-S01.5
title: "Pivot to Docker delivery — libstdc++ floor incompatibility evidence"
date: 2026-04-26
sprint: 2
epic: E2
status: complete
adr_ref: ADR-015
---

# E2-S01.5 — Pivot Evidence

Unplanned pivot story between E2-S01 (npm install — passed install, failed at runtime) and E2-S02 (footprint test — re-targeted at the containerised daemon).

Architecture risk AR1 realized differently than anticipated: not an RSS overshoot, but a **libstdc++ ABI floor incompatibility** in the LadybugDB native binding. Operator selected **Option B: containerise via the official Docker image**.

## 1. libstdc++ ABI floor delta (root cause)

**Workstation (Debian 12 bookworm):**

```
$ strings /usr/lib/x86_64-linux-gnu/libstdc++.so.6 | grep -E "GLIBCXX_3\.4\.(28|29|30|31|32)" | sort -u
GLIBCXX_3.4.28
GLIBCXX_3.4.29
GLIBCXX_3.4.30
```

Maximum available symbol: **`GLIBCXX_3.4.30`**.

**LadybugDB requirement (npm `gitnexus@1.6.3` → `@ladybugdb/core` → `lbugjs.node`):**

`Error: ERR_DLOPEN_FAILED — /lib/x86_64-linux-gnu/libstdc++.so.6: version 'GLIBCXX_3.4.32' not found (required by .../node_modules/@ladybugdb/core/build/Release/lbugjs.node)`

Required: **`GLIBCXX_3.4.32`** (and `_3.4.31`).

**Delta:** Debian 12 ships libstdc++ topping out at 3.4.30; LadybugDB needs 3.4.32. The npm channel cannot start the daemon on this OS. ADR-004 did not specify a libstdc++ baseline; that gap is now closed by ADR-015.

## 2. Docker spike findings (verified by director, re-verified in this story)

| Property | Value |
|---|---|
| Image | `ghcr.io/abhigyanpatwari/gitnexus:1.6.3` |
| Digest (image ID) | `006ea303f1dc` |
| Tags | `1.6.3`, `latest` (also at `akonlabs/gitnexus:1.6.3` — same digest) |
| Size (pull / disk) | 944 MB / 504 MB |
| Base OS | Debian 13 trixie (libstdc++ floor satisfied) |
| Default entrypoint | `docker-entrypoint.sh` → `gitnexus serve --host 0.0.0.0 --port 4747` |
| Internal binary | `gitnexus` → `/app/gitnexus/dist/cli/index.js` |
| HTTP port | **4747** |
| MCP path | **`/api/mcp`** |
| Persistence env | `GITNEXUS_HOME=/data/gitnexus` |

```
$ docker images | grep gitnexus
akonlabs/gitnexus:1.6.3                   006ea303f1dc        944MB          504MB
akonlabs/gitnexus:latest                  006ea303f1dc        944MB          504MB
ghcr.io/abhigyanpatwari/gitnexus:1.6.3    006ea303f1dc        944MB          504MB
ghcr.io/abhigyanpatwari/gitnexus:latest   006ea303f1dc        944MB          504MB
```

## 3. Persistence model chosen — `docker-compose` (Option B1)

**Decision:** docker-compose under `homelab-apps/stacks/gitnexus/docker-compose.yml`.

**Rationale:**
- Mirrors the existing convention. Every other stack in this estate (`stacks/observability/`, `stacks/infra-core/`, `stacks/automations-n8n/`, et al.) uses docker-compose with the same shape: `services:` block, healthcheck, restart policy, security-hardening (`no-new-privileges`, `cap_drop: ALL`), 20–50 MB log rotation.
- Single-file lifecycle (`docker compose up -d` / `down`) is cleaner than systemd-unit ownership for a workstation-local service. No PID file, no service-name conflict surface.
- Reusable verbatim on ct-dev-homelab in Sprint 4 / E4-S07 (the same image, the same compose stanza, just a different host) — promotes deploy-environment parity. A systemd unit would not transplant.
- The stacks/ directory is intentionally a manifest catalog (not exclusively a cluster-deploy target); placing the workstation manifest here keeps a single source of truth.

**Privacy:** port `4747` is bound to `127.0.0.1` only (not `0.0.0.0`). NFR-PRIV-001 enforced; no LAN/tailnet exposure.

**Not chosen (Option B2, systemd unit):** would require sudo, would not transplant to ct-dev-homelab, would introduce a second lifecycle pattern in the estate.

## 4. Daemon-running verification (live)

**Stack started:**

```
$ docker compose -f homelab-apps/stacks/gitnexus/docker-compose.yml up -d
 Network gitnexus_default Creating
 Network gitnexus_default Created
 Container gitnexus Creating
 Container gitnexus Created
 Container gitnexus Starting
 Container gitnexus Started
```

**Container running:**

```
$ docker ps --filter name=gitnexus --format "{{.ID}}  {{.Image}}  {{.Status}}  {{.Ports}}"
65bdbb12de07  ghcr.io/abhigyanpatwari/gitnexus:1.6.3  Up 13 seconds (health: starting)  127.0.0.1:4747->4747/tcp
```

**Daemon logs (success signal — exactly what the brief flagged):**

```
$ docker logs gitnexus
MCP HTTP endpoints mounted at /api/mcp
GitNexus server running on http://localhost:4747
```

**HTTP live checks:**

```
$ curl -sS -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:4747/
HTTP 404            # process is up; root has no route — expected

$ curl -sS -o /dev/null -w "HTTP %{http_code}\n" http://127.0.0.1:4747/api/mcp
HTTP 400            # MCP endpoint is mounted; bare GET returns 400 — expected (MCP requires JSON-RPC POST)
```

Both responses are **process-is-up** signals. A "connection refused" or `7` would have been the failure case. (Full MCP protocol negotiation will be exercised in E2-S03 when Claude Code registers the server via `claude mcp add --transport http`.)

**Live RSS sample (initial):**

```
$ docker stats --no-stream --format "{{.Name}}  {{.MemUsage}}  {{.CPUPerc}}" gitnexus
gitnexus  51.4MiB / 8GiB  0.07%
```

51.4 MiB resident at idle. The full 24-hour sustained-RSS measurement under load is E2-S02's job; the early reading is well under the 500 MB target (NFR-FOOTPRINT-002 / AR1).

**Persistent data dir:**

```
$ ls -la ~/.gitnexus-data
total 9
drwxr-xr-x  2 developer developer 2 Apr 26 11:27 .
drwxr-xr-x 26 developer developer ... ..
```

Empty bind-mount target ready for graph data.

## 5. npm uninstall confirmation

```
$ npm uninstall -g gitnexus
removed 254 packages in 834ms

$ which gitnexus
                          # (empty — exit code 1, "not found")

$ ls /home/developer/.npm-global/lib/node_modules/gitnexus
ls: cannot access '/home/developer/.npm-global/lib/node_modules/gitnexus': No such file or directory

$ ls /home/developer/.npm-global/bin/gitnexus
ls: cannot access '/home/developer/.npm-global/bin/gitnexus': No such file or directory
```

The npm install artifact (E2-S01 deliverable) is fully removed. Container delivery is now the sole `gitnexus` binary on the workstation.

## 6. ADR-015 cross-reference

This pivot is captured in:

- **ADR-015** — `_bmad-output/planning-artifacts/products/context-stack/adrs/ADR-015-gitnexus-container-delivery-libstdc-floor.md` — the architectural decision (npm → Docker).
- **ADR-005** — amended in-place with a "transport variance" note clarifying that MCP transport (stdio vs HTTP) is delivery-dependent. Both remain first-class MCP transports.
- **ADR-004** — *not* amended. Tool-selection (GitNexus over graphify / CodeGraphContext) is unchanged. ADR-015 only changes the delivery channel.
- **Sprint plan** — `sprint-plan.md` updated with a Sprint 2 Pivot Note. ½-day slip absorbed by the existing buffer (Sprint 2 had ~3.3 wall-clock days of slack — see sprint-plan §4.2 "Sprint total").

## 7. Forward implications

- **E2-S02 (next):** retry footprint test against the containerised daemon. Measure with `docker stats --no-stream gitnexus` over 24h, not host-process RSS. Target unchanged: < 500 MB sustained.
- **E2-S03:** MCP wiring command changes from the original (npm-implied) `npx gitnexus setup` stdio approach to: `claude mcp add --transport http gitnexus http://127.0.0.1:4747/api/mcp`. This is the canonical HTTP-transport registration form (matches the Graphiti pattern from ADR-001 + ADR-006).
- **E2-S05 / privacy audit:** still required. The 127.0.0.1 bind already enforces local-only at the network layer; tcpdump audit during full reindex remains mandatory to confirm tree-sitter parsing makes no outbound calls.
- **Sprint 4 / E4-S07:** the workstation `docker-compose.yml` is the seed for the ct-dev-homelab deploy. Same image, same stanza.

## 8. Anything unexpected?

- The container was healthier and lighter than feared. 51.4 MiB at idle is comfortably below the 500 MB ceiling; the 944 MB image footprint is a one-time disk cost, not a runtime cost.
- The `MCP HTTP endpoints mounted at /api/mcp` log line is exactly the success signal the director's brief flagged — no surprises.
- The pivot consumed ~½ day, well within Sprint 2's slack budget. Critical-path stories (E2-S03 onwards) are unblocked.
