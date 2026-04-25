---
type: product-index
product: context-stack
version: 1.0.0
status: ready-for-sprint-1
date: 2026-04-25
---

# Context Stack — Product Index

> A coherent, privacy-first AI-context stack for Claude Code that replaces the dormant memory tooling (MemPalace, OMEGA) with a smaller set of MCP-native components — code-graph (GitNexus), conversational memory (Graphiti+FalkorDB), and a file-tree wiki — plus a bridge to the operator's local-LLM substrate. Single user (tomamourette). Outcome: less re-derivation per session, durable cross-session memory, ≤$1/day cost cap, and clean exit ramps.

## Status

- **Phase complete:** BMAD Phases 1–6 (Brief → PRD → Architecture → Epics → Stories → Acceptance → E2E → Readiness → Sprint plan)
- **Ready for:** Sprint 1 kickoff
- **Total artifacts:** 9 top-level docs + 14 ADRs + 38 stories = 61 files, 4,593 lines (top-level only) + ADRs/stories
- **Readiness check:** PASS-WITH-NOTES (44 PASS / 2 PASS-WITH-NOTES / 0 FAIL → Sprint 1 GO)
- **Total estimated effort:** ~10 weeks (5 sprints × 2 weeks at ~3 effective hrs/day)

## At a Glance

| Layer | Tool | Epic | Sprint |
|---|---|---|---|
| Decommission | MemPalace + OMEGA removal (single PR, 8 commits, no-squash) | E1 | S1 |
| Code-graph | GitNexus v1.6.3 (npm, Node.js + LadybugDB), MCP, AST-first | E2 | S2 |
| Memory | Graphiti v1.0.2 + FalkorDB (bi-temporal), MCP | E3 | S3 |
| Wiki | File-based markdown under `homelab-playbook/wiki/` + wiki-query skill | E4 | S4 |
| Cost cap | $1/day hard-cap via cron + OpenAI Usage API + ntfy throttle (CT101) | E4 | S4 |
| LiteLLM bridge | `OPENAI_BASE_URL` → hybrid_gemma_serving (50-fact ≥95% gate) | E4 | S5 |
| Container deploy | Ansible role to ct-dev-homelab + rollback drill | E4 | S4 |

## Artifact Index

### Phase 1 — Discovery
- **[product-brief.md](product-brief.md)** (267 lines) — vision, problem (9 OMEGA memories in 18 days, MemPalace 0 tables), scope (8 in / 10 out), 6 KPIs, decommission/adoption targets, 3 research-artifact references.

### Phase 2 — Requirements
- **[prd.md](prd.md)** (485 lines) — 73 FRs (DEC×12, CG×12, MEM×15, WIKI×10, LLM×8, OBS×6, DEP×10) + 25 NFRs (PERF/COST/PRIV/FOOTPRINT/AVAIL/MAINT/SUPP/PORT) + 7 user journeys + MoSCoW recalibrated to 60/36/4.

### Phase 3 — Architecture
- **[architecture.md](architecture.md)** (518 lines) — C4 system + container + 5 component diagrams; 4-layer model (auto-memory / wiki / code-graph / memory); deployment topology (workstation + ct-ai-01 + ct-dev-homelab); cross-cutting privacy/observability/security/backup/cost.
- **[adrs/](adrs/)** (14 ADRs):
  - [ADR-001](adrs/ADR-001-falkordb-as-graphiti-backend.md) — FalkorDB as Graphiti backend
  - [ADR-002](adrs/ADR-002-gpt-4o-mini-for-graphiti-extraction-phase-1.md) — gpt-4o-mini for Graphiti extraction (Phase 1)
  - [ADR-003](adrs/ADR-003-embeddings-stay-on-openai.md) — Embeddings stay on OpenAI text-embedding-3-small
  - [ADR-004](adrs/ADR-004-gitnexus-over-graphify-and-codegraphcontext.md) — GitNexus over graphify and CodeGraphContext
  - [ADR-005](adrs/ADR-005-mcp-first-over-skill-first.md) — MCP-first over skill-first
  - [ADR-006](adrs/ADR-006-wiki-as-file-tree.md) — Wiki tier as a file-based markdown tree
  - [ADR-007](adrs/ADR-007-graphiti-backup-strategy.md) — Graphiti backup cadence (daily AOF + weekly RDB + monthly export)
  - [ADR-008](adrs/ADR-008-daily-1-dollar-cap-implementation.md) — Daily $1 hard-cap implementation
  - [ADR-009](adrs/ADR-009-wiki-query-skill-design.md) — wiki-query skill: read-on-demand
  - [ADR-010](adrs/ADR-010-decommission-as-single-pr.md) — Decommission as single PR with sequenced commits
  - [ADR-011](adrs/ADR-011-litellm-bridge-via-openai-base-url.md) — LiteLLM bridge via `OPENAI_BASE_URL`
  - [ADR-012](adrs/ADR-012-gitnexus-graph-export-wrapper.md) — GitNexus graph export wrapper (Cypher → JSON)
  - [ADR-013](adrs/ADR-013-tier-of-truth-division.md) — Tier-of-truth division (wiki vs Graphiti vs auto-memory)
  - [ADR-014](adrs/ADR-014-moscow-recalibration.md) — MoSCoW recalibration (60/36/4 MUST/SHOULD/COULD)

### Phase 4 — Epics and Stories
- **[epics.md](epics.md)** (580 lines) — 4 epics with goal/scope/deps/AC/exit-gate/FR-coverage/risks/decomposition; FR coverage audit (73/73, no orphans).
- **[stories/](stories/)** (38 INVEST stories, all ≤3d, frontmatter-tagged):
  - **E1 Decommission** (9 stories, ~7d ideal): E1-S01..S09 — disable hooks → remove entries → uninstall → MemPalace removal → Hermes Jinja → decommission doc → verify gates → forward-protection tag.
  - **E2 GitNexus Pilot** (8 stories, ~7d ideal): E2-S01..S08 — install + supply-chain → footprint <500 MB → MCP wiring → hooks → topology + privacy → 5 smoke tests → graph export → week-1 KPI gate.
  - **E3 Graphiti Pilot** (9 stories, ~9.5d ideal): E3-S01..S09 — FalkorDB compose → MCP HTTP/Tailscale → CLAUDE.md memory section → embedder + semaphore → smoke tests → backup cron → restore drill → week-2 KPI gate.
  - **E4 Production Hardening** (12 stories, ~13.5d ideal, split S4+S5): E4-S01..S12 — wiki schema/seeds → wiki-query skill → $1 cap → LiteLLM bridge → 50-fact gate → Ansible role → ct-dev-homelab deploy + rollback → observability digest → exit ramps → week-4 KPI scorecard → Phase 4 retro.

### Phase 5 — Test Strategy
- **[tests/acceptance.md](tests/acceptance.md)** (852 lines) — 325 ACs aggregated across 38 stories (E1=58, E2=61, E3=76, E4=130); 0 FR gaps; 6 vague ACs flagged (1.85%, well below 5% bar).
- **[tests/e2e-deployment.md](tests/e2e-deployment.md)** (1087 lines) — 26 test groups; 22-step happy-path runbook (4h25min wall-clock); 3 disaster scenarios (D1 FalkorDB AOF corruption + Cypher replay; D2 OpenAI 429 + cap engagement; D3 Tailscale/hotel-wifi outage).
- **[readiness-check.md](readiness-check.md)** (150 lines) — 44 PASS / 2 PASS-WITH-NOTES / 0 FAIL → **PASS-WITH-NOTES**; Sprint 1 **GO**; 2 mandatory fixes scheduled before Sprint 3 (`cypher-replay.sh` author-up; `docker compose down -v` "copy first" guard).

### Phase 6 — Sprint Plan
- **[sprint-plan.md](sprint-plan.md)** (654 lines) — 5 sprints / 10 weeks at ~3 hrs/day (~18 effective hrs/sprint, 1.7× ideal-to-wall-clock multiplier); per-sprint backlog with day-by-day plan + decision gates + slip risks; E4 split into S4 (wiki + cap + Ansible deploy) + S5 (LiteLLM bridge + observability + product-level KPI gate).

## Key Decisions (full rationale in ADRs)

1. **Decommission MemPalace + OMEGA in Sprint 1** — both proven dormant or empty; ADR-010 single-PR with 8 non-squash commits for revertability.
2. **GitNexus as code-graph layer** (ADR-004) — MCP-native, AST-first, npm v1.6.3, auto-reindex on commit; chosen over graphify/CodeGraphContext.
3. **Graphiti + FalkorDB as memory layer** (ADR-001) — bi-temporal validity intervals, MCP v1.0.2.
4. **Cloud Phase 1 LLMs** — gpt-4o-mini for extraction (ADR-002), text-embedding-3-small for embeddings (ADR-003); ~$1/month projected.
5. **Wiki as file-tree** (ADR-006) under `homelab-playbook/wiki/` + read-on-demand skill (ADR-009).
6. **Daily $1 hard-cap** (ADR-008) via cron + OpenAI Usage API + ntfy alert + auto-throttle on CT101 over Tailscale.
7. **LiteLLM bridge to local Gemma** (ADR-011) Sprint 5, gated by 50-fact ≥95% well-formed validation; defer to backlog if `hybrid_gemma_serving` not ready.
8. **MCP-first over skill-first** (ADR-005) — the lesson learned from MemPalace.

## Sprint 1 Kickoff Cheat-Sheet

Day 1 of Sprint 1 — every box must tick before writing any code (verbatim from `sprint-plan.md` §14):

1. Working tree clean: `git -C ~/workspace/homelab status` reports nothing to commit on each of the three sibling repos.
2. Branch created: `git -C ~/workspace/homelab/homelab-playbook checkout -b decommission/context-stack-phase-1` (or equivalent for each commit).
3. Pre-decommission baseline captured: `ansible-playbook` against `ct-dev-homelab` with current Hermes role and `verify.yml` exits 0. Save evidence to `homelab-playbook/docs/decommission/baseline-pre-decommission.txt`.
4. ct-dev-homelab reachable: `ansible -i inventory ct-dev-homelab -m ping` succeeds.
5. `~/.claude/settings.json` backed up to `~/.claude/settings.json.bak.<TS>` (rollback insurance).
6. `~/.mempalace/` listed for unexpected files (FR-DEC-012 evidence pre-deletion).
7. `pip list | grep omega-memory` confirms current install version (rollback target).
8. Hermes Jinja templates identified: `config.yaml.j2`, `defaults/main.yml`, `verify.yml` paths confirmed.
9. ADR-010 re-read: 8-commit sequence and **merge-commit-not-squash** rule fresh in mind.
10. Sprint backlog (sprint-plan.md §3.2) opened in task tracker; first task = E1-S01 (disable OMEGA hooks).
11. Operator life-context calibration: realistic estimate of how many of the next 10 working days will hit the 3-hr target — adjust expectations now, not at retro.

**Sprint 1 GO criterion:** all 11 above tick. First story to execute: **[E1-S01 disable OMEGA hooks](stories/E1-S01-disable-omega-hooks.md)**.

## Open Items Needing User Input

Genuinely minimal — most ambiguities are closed:

1. **Sprint 1 calendar start date (`S1-D1`)** — operator picks; all subsequent dates derive.
2. **Working title finalization** — "Context Stack" is a placeholder per brief §1; rename before or skip if happy with it.
3. **Sprint 5 LiteLLM go/no-go** — verify `hybrid_gemma_serving` Phase-1 readiness by S4 retro; if not ready, defer FR-LLM-007 to backlog (PRD §11 safety valve, sprint-plan §7).

## Maintenance Note

This product is BMAD-tracked. Future updates should:
- Update `sprint-plan.md` after each sprint retro (actuals vs estimates → next-sprint recalibration).
- Add ADRs (ADR-015+) for any architectural decision made during execution.
- Mark each completed story `status: completed` in its frontmatter and link the merge PR.
- Update `readiness-check.md` if scope changes mid-product.
- Re-run readiness check before any phase that descopes a MUST or extends timeline > 20%.

## Related Project Memories

- Auto-memory: `~/.claude/projects/-home-developer-workspace-homelab/memory/MEMORY.md`
- Prior research that motivated this product:
  - `homelab-playbook/_bmad-output/planning-artifacts/research/technical-graphify-evaluation-2026-04-25.md`
  - `homelab-playbook/_bmad-output/planning-artifacts/research/technical-memory-systems-evaluation-2026-04-25.md`
  - `homelab-playbook/_bmad-output/planning-artifacts/research/graphiti-claude-code-install-plan-2026-04-25.md`
- Related projects:
  - `project_hybrid_gemma_serving.md` — Sprint 5 LiteLLM bridge target (Unsloth UD-Q5_K_M + FastAPI proxy + LiteLLM gateway, Vulkan).
  - `project_phone_notifications_tailscale.md` — ntfy CT101 over Tailscale (cost-cap alert path).
  - `project_ai_dev_container.md` — Epic 6 supersession (this product replaces the MemPalace plan).
