---
adr: 015
title: "GitNexus container delivery (Docker) over npm — libstdc++ ABI floor blocks native install on Debian 12"
status: accepted
date: 2026-04-26
authors: tomamourette (via BMAD director Claude)
context_question: null
supersedes: null
amends: ADR-004, ADR-005
---

# ADR-015: GitNexus container delivery (Docker) over npm — libstdc++ ABI floor blocks native install on Debian 12

## Context

ADR-004 selected GitNexus as the Tier-2 code-graph MCP server, with the install channel pinned to `npm install -g gitnexus@1.6.3`. ADR-005 implied stdio MCP transport (the npm package's default). Sprint 2 / E2-S01 successfully completed the npm install and supply-chain verification. **E2-S02 then failed at runtime**, before any RSS sample could be taken.

The failure mode was not the architecture risk anticipated by AR1 (footprint > 500 MB). It was a **libstdc++ ABI floor incompatibility** in the LadybugDB native binding shipped with `gitnexus@1.6.3`:

- The npm package bundles `@ladybugdb/core` whose native module `lbugjs.node` is dynamically linked against **`GLIBCXX_3.4.32`** (and `_3.4.31`).
- The Claude Code workstation runs **Debian 12 bookworm**, which ships **`libstdc++` topping out at `GLIBCXX_3.4.30`**.
- Result: `Error: ERR_DLOPEN_FAILED — /lib/x86_64-linux-gnu/libstdc++.so.6: version 'GLIBCXX_3.4.32' not found`. The `gitnexus` daemon cannot start. ADR-004's npm channel is non-viable on this OS.

ADR-004 did not specify a libstdc++ baseline; the decision treated "Node.js + npm" as a sufficient runtime contract. That gap is now closed by this ADR. The director's spike confirmed the upstream Docker image (Debian 13 trixie base) ships a recent-enough `libstdc++` and the daemon starts cleanly inside the container.

This ADR captures the workstation-install-channel pivot. The architectural decision (GitNexus over graphify / CodeGraphContext) from ADR-004 is **unchanged** — only the delivery model changes.

## Decision

**Use the official `ghcr.io/abhigyanpatwari/gitnexus:1.6.3` Docker image as the canonical workstation install of the GitNexus MCP server.**

- Image: `ghcr.io/abhigyanpatwari/gitnexus:1.6.3` — digest `sha256:006ea303f1dc...` (also tagged `latest`; mirror at `akonlabs/gitnexus:1.6.3` resolves to the same digest).
- Image size: 944 MB on pull / ~504 MB on disk.
- Base: Debian 13 trixie (libstdc++ floor satisfied; no `GLIBCXX_3.4.32` issue).
- Default entrypoint: `docker-entrypoint.sh` → `gitnexus serve --host 0.0.0.0 --port 4747` inside the container.
- Internal binary: `gitnexus` resolves to `/app/gitnexus/dist/cli/index.js`.
- Daemon serves HTTP on **port 4747**; MCP endpoints mounted at **`/api/mcp`**.
- Persistence: container volume `/data/gitnexus` (= `GITNEXUS_HOME`) → host bind mount `~/.gitnexus-data`.
- Workstation persistence model: **`docker-compose`** under `homelab-apps/stacks/gitnexus/docker-compose.yml` — mirrors the existing stacks convention (observability, infra-core, et al.), single-file lifecycle, no systemd-unit ownership concerns.
- **Port binding is `127.0.0.1:4747:4747` only**. NFR-PRIV-001 still applies — the daemon stays local-only on the workstation; no LAN/tailnet exposure.

The npm package `gitnexus@1.6.3` is **uninstalled** as part of E2-S01.5 to remove dead weight (`/home/developer/.npm-global/bin/gitnexus`).

## Consequences

**Positive.**
- Avoids workstation system-library upgrades (Option A had high blast radius — `apt install -t bookworm-backports libstdc++6` could destabilise other tools).
- Aligns with **Sprint 4 / E4-S07** which already plans a container-deploy for ct-dev-homelab — same image, same compose pattern, fewer surprises.
- ADR-004 explicitly mentions Docker images as a supported channel ("npm distribution means a Node.js runtime on the workstation"; the Docker channel sidesteps the runtime dependency entirely).
- Container isolation tightens supply-chain blast-radius: a compromised LadybugDB binding cannot reach host system libraries.
- Same image runs identically on the workstation today and on a homelab container tomorrow — promotes deploy-environment parity.

**Negative.**
- **MCP transport changes from stdio to HTTP**. ADR-005's "MCP-first integration" decision implied stdio (the npm package's default); the containerised daemon serves HTTP at `http://127.0.0.1:4747/api/mcp`. ADR-005 is amended to clarify that transport is delivery-model dependent and either is acceptable. E2-S03 (MCP wiring to Claude Code) must register the server with `claude mcp add --transport http gitnexus http://127.0.0.1:4747/api/mcp` rather than the originally-planned stdio command.
- Small additional ops surface: Docker daemon dependency on the workstation (already present for other workflows). Workstation `docker info` is a new pre-flight check.
- 944 MB image footprint shifts E2-S02's footprint NFR from "RSS only" to "RSS + image storage". The < 500 MB RSS target (NFR-FOOTPRINT-002, AR1) still applies to the running daemon's resident memory; the 944 MB image is a one-time disk cost, not a runtime cost. E2-S02 retry must measure container RSS (`docker stats gitnexus`), not just process RSS.
- Container lifecycle adds restart-policy ownership: `restart: unless-stopped` (per stacks convention). A workstation reboot brings the daemon back automatically, no systemd unit required.

**Neutral.**
- Container delivery aligns with the broader Context Stack architectural pattern — Graphiti (Tier 3) is already container-based on ct-ai-01. Tier 2 was the outlier; this pivot brings it in line.
- LadybugDB itself is unchanged. The graph-store choice and Cypher query interface (ADR-004 §Decision) are untouched.

## Alternatives Considered

1. **Workstation libstdc++ upgrade (apt-pin to bookworm-backports or trixie repos)** — *rejected*. High blast radius; risks breaking other tools that depend on the bookworm-stable C++ ABI. Single-purpose system-library mutation for a single tool is poor hygiene.
2. **Containerise via official Docker image** — *chosen* (this ADR). Lowest-blast-radius fix, aligns with Sprint 4 plan, ADR-004 already lists Docker as supported.
3. **Find an older GitNexus version that pre-dates the GLIBCXX_3.4.32 dependency** — *rejected*. Research-heavy with uncertain outcome; might need to roll back several minor versions, losing features (parent-folder support was added in 1.5+). Pinning to an older release defeats NFR-SUPP-001 (≥3mo upstream activity gate at adoption — older releases drift further from current upstream).
4. **Reverse ADR-004 → adopt CodeGraphContext as the primary code-graph** — *rejected for now, retained as fallback* (ADR-004 §Validation/Exit Ramp). Bigger architectural pivot (Neo4j daemon, +1 GB JVM RAM, MCP-first via different server). Container delivery is the proportionate fix; CodeGraphContext remains the documented exit ramp if Docker delivery also fails for some reason.

## Validation / Exit Ramp

- **Validation (this story, E2-S01.5):**
  - `docker pull ghcr.io/abhigyanpatwari/gitnexus:1.6.3` — image present (digest `006ea303...`).
  - `docker compose -f stacks/gitnexus/docker-compose.yml up -d` succeeds; `docker ps` shows `gitnexus` healthy.
  - `curl -sS http://127.0.0.1:4747/` returns HTTP 200/404 (process is up); `/api/mcp` log line "MCP HTTP endpoints mounted at /api/mcp" present in `docker logs gitnexus`.
  - `which gitnexus` returns "(not found)" after `npm uninstall -g gitnexus` (no leftover npm binary).
- **Validation (E2-S02 retry):** sample container RSS over 24h (`docker stats --no-stream gitnexus`); confirm < 500 MB sustained per NFR-FOOTPRINT-002.
- **Validation (E2-S03):** `claude mcp add --transport http gitnexus http://127.0.0.1:4747/api/mcp` succeeds; `claude mcp list` shows `gitnexus` healthy.
- **Exit ramp:** if Docker delivery also fails (LadybugDB issue surfaces in some other way — e.g., the container itself crashes on workstation kernel features), Option D (CodeGraphContext) remains the documented architectural fallback per ADR-004. The export wrapper of ADR-012 is the bridge.
- **Reversal trigger:** if `gitnexus@1.6.3` (or a successor) ships a static-linked LadybugDB binding or an Alpine/musl variant that runs natively on Debian 12 bookworm, revisit npm delivery and revert this ADR. Workstation libstdc++ baseline tracking (re-check at every minor OS upgrade) is added to NFR-SUPP-001 in spirit (operational, not contractual).

## References

- ADR-004 (GitNexus over graphify and CodeGraphContext) — original tool-selection; this ADR amends only the delivery channel.
- ADR-005 (MCP-first integration) — amended in this story to clarify transport is delivery-dependent (stdio for npm, HTTP for container).
- ADR-012 (GitNexus graph export wrapper) — the documented exit ramp to CodeGraphContext if both npm and Docker delivery fail.
- E2-S01 evidence: `docs/context-stack/sprint-2/e2-s01-evidence.md` (npm install succeeded; supply-chain verified).
- E2-S01.5 evidence: `docs/context-stack/sprint-2/e2-s01-5-pivot-evidence.md` (this pivot's verification log).
- LadybugDB upstream (libstdc++ floor source): `@ladybugdb/core` native binding `lbugjs.node`.
- GitHub: <https://github.com/abhigyanpatwari/GitNexus>; container registry: `ghcr.io/abhigyanpatwari/gitnexus`.
