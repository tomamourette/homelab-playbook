---
type: prd
product: context-stack
version: 1.0.0-draft
status: draft
date: 2026-04-25
brief_ref: product-brief.md
---

# Context Stack — Product Requirements Document

## 1. Document Control

| Field | Value |
|---|---|
| Product | Context Stack |
| Version | 1.0.0-draft |
| Status | Draft (Phase 2 — PRD) |
| Author | tomamourette (via BMAD director Claude) |
| Date | 2026-04-25 |
| Source brief | `homelab-playbook/_bmad-output/planning-artifacts/products/context-stack/product-brief.md` |
| Director-resolved decisions | Product name "Context Stack"; LLM Wiki under `homelab-playbook/wiki/`; GitNexus reindex on every commit; LiteLLM bridge Graphiti-only; full decommission of MemPalace + OMEGA; Graphiti adoption with FalkorDB + `gpt-4o-mini` + `text-embedding-3-small`; GitNexus adoption (workstation MCP-native, AST-first, auto-reindex on commit); LLM Wiki tier (file-based, zero-MCP); LiteLLM bridge to `hybrid_gemma_serving` (Phase 4 stretch). |

**Traceability summary.** Every FR and NFR in this PRD traces back to a brief section, a director-resolved decision, or one of the three research artifacts: `technical-graphify-evaluation-2026-04-25.md`, `technical-memory-systems-evaluation-2026-04-25.md`, `graphiti-claude-code-install-plan-2026-04-25.md`. Citations appear inline on each requirement.

---

## 2. Executive Summary

Context Stack is a single-operator product that consolidates the Claude Code context substrate into a coherent, privacy-first stack of three context tiers and a decommission of two dormant tools. The objective is not new capability for its own sake — it is to stop paying maintenance rent on tools that do not work (OMEGA's broken vector search, MemPalace's empty SQLite) and to add narrowly justified capability where the operator has a real, recurring failure mode (decision-archaeology across a long-running homelab).

The product ships in four sprints, each with a single epic. Phase 1 is decommission: end-to-end removal of MemPalace and OMEGA from workstation, dev_hosts container, and Hermes config, leaving Claude Code's auto-memory (`MEMORY.md`) as the only memory tier. Phase 2 introduces GitNexus as the workstation code-graph (MCP-native, AST-first, auto-reindex on commit) and Graphiti as the conversational/temporal memory layer (FalkorDB backend on `ct-ai-01`, MCP HTTP transport, `gpt-4o-mini` LLM, `text-embedding-3-small` embeddings). Phase 3 establishes the LLM Wiki tier under `homelab-playbook/wiki/` as Tier-1 zero-MCP pre-synthesised knowledge with a `wiki-query` skill. Phase 4 (stretch) bridges Graphiti's LLM call through LiteLLM to the operator's `hybrid_gemma_serving` gateway behind a 95%-well-formed-JSON validation gate.

Acceptance is measured against a 6-metric KPI scorecard requiring 4-of-6 green at week 4. Hard gates outside the scorecard: zero observable Claude Code session-start latency regression, and end-to-end rollback validated on `ct-dev-homelab` before promotion. This PRD enumerates 73 functional requirements and 25 non-functional requirements, each individually testable and traceable to brief, decision, or research source.

---

## 3. Background and Problem Recap

This section summarises §2 of the brief; full statement and quantitative dimensions lives there.

**Three context tools have accumulated and decayed.** OMEGA is technically running but materially dormant: 9 memories captured in 18 days, vector search broken (sqlite-vec not loaded), MCP tools not surfaced to Claude Code, query hit rate 1-of-8 on real sessions, and the `omega_welcome → omega_protocol` session-start contract imposes a cost it does not pay back. MemPalace is empty: zero tables and zero rows in the local SQLite; its only deployment target (`ct-dev-test`) has been retired; the Hermes WhatsApp auto-responder briefly wired three skills against it (`mempalace-kg-query`, `mempalace-diary`, `mempalace-search`); none are used. Hermes wiring is partial — `wire-mempalace.yml`, the degenerated `knowledge-query` orchestrator, plus conditional blocks in Hermes' `config.yaml.j2`, `defaults/main.yml`, and `verify.yml` — all reference dead infrastructure.

**Quantitative dimensions.** The operator's auto-memory file at `/home/developer/.claude/projects/-home-developer-workspace-homelab/memory/MEMORY.md` is the only memory tier currently working. The brief calibrates the K1 token-reduction target at ≥ 5× (against code-review-graph's third-party 6.8× / 6.0× anchors), explicitly NOT graphify's 71.5× corpus-specific claim (per `technical-graphify-evaluation-2026-04-25.md` §Headline finding). Steady-state spend target is < $20/month all-in (Anthropic + OpenAI). FalkorDB's resident footprint at this data scale is < 200 MB; GitNexus daemon < 500 MB.

**Cost of inaction.** Every Claude Code session re-reads the same files, re-derives the same architecture decisions, and burns tokens it should not need to. The "compound learning" promise of AI Dev Container Epic 6 has not materialised. Continuing to maintain dormant tools competes with the maintenance budget for tools that would.

---

## 4. User Personas and Journeys

### 4.1 Persona: tomamourette (single homelab operator power-user)

| Attribute | Value |
|---|---|
| Role | Solo homelab operator + consulting developer |
| Primary AI workflow | Claude Code as daily driver; BMAD-style story-driven development |
| Stack expertise | Deep Proxmox 9.x / Terraform / Ansible; 3-node PVE cluster (pve1/pve2/pve3) |
| Repo topology | Parent folder `homelab/` with three sibling repos (`homelab/`, `homelab-bootstrap/`, `homelab-playbook/`) plus per-project containers (Sparkle-CPS, quant-trading, ai-dev-container, Hermes) |
| Constraint posture | Privacy-first; cost-conscious (< $20/month); maintenance-budget sensitive; Tailscale-only for phone-facing services |
| Team size | One. No multi-user, no RBAC, no shared-tenant assumptions. |

**Non-personas (explicit).** No customer-facing users. No team collaborators. No cross-tenant clients. Design choices that primarily benefit multi-tenant scenarios are out of scope.

### 4.2 Journey A — Daily Claude Code coding session (workstation)

1. Operator opens Claude Code in a sub-repo (e.g., `homelab-playbook`).
2. Session-start hook fires; auto-memory is loaded; GitNexus MCP advertises tool surface; Graphiti MCP advertises tool surface; LLM Wiki table-of-contents (a single `index.md`) is read by the model from the wiki tree.
3. Operator asks a code question ("which roles call `mempalace-search`?").
4. Claude Code consults — in order — wiki (Tier 1, zero-cost), GitNexus (Tier 2, AST traversal), Graphiti (Tier 3, conversational/temporal facts), auto-memory (Tier 4, deterministic markdown).
5. Operator commits; PostToolUse hook auto-reindexes GitNexus.

**Acceptance signal:** session-start overhead from this stack is < 1 s wall-clock vs. baseline (NFR-PERF-001).

### 4.3 Journey B — Multi-day decision lookup (Graphiti memory)

1. Operator made a non-trivial decision yesterday ("on 2026-04-24 we migrated pve2 from LVM to ZFS mirror"). Claude Code wrote it to Graphiti via `add_episode` with `group_id=tom-personal`.
2. Today, the operator asks "what did we decide about pve2 storage?"
3. Claude Code calls `search_facts` against Graphiti; Graphiti returns the fact with `valid_at` reflecting the actual decision date.
4. If a superseding decision exists ("on 2026-04-25 ct-ai-01 moved pve2 → pve3"), Graphiti's bi-temporal model returns both, ordered by validity.

**Acceptance signal:** K5 — ≥ 50% of first-shot recall queries return a useful prior decision by week 4 (FR-MEM-007).

### 4.4 Journey C — Cross-repo code question (GitNexus + parent-folder topology)

1. Operator asks "which Ansible roles in any of the three sibling repos still reference `mempalace`?"
2. Claude Code calls GitNexus across the parent folder graph (designed for this exact polyrepo layout per `technical-graphify-evaluation-2026-04-25.md`).
3. GitNexus returns a structured list with file paths, line numbers, and relation types (definition, reference, import).
4. Operator iterates without re-reading any file by hand; token budget on the answer is < 1/5 of the equivalent grep-and-read approach (K1 target).

**Acceptance signal:** K1 — token reduction ≥ 5× on a real medium-size repo task vs. baseline (FR-CG-008, NFR-PERF-002).

### 4.5 Journey D — Architecture-question fast path (LLM Wiki Tier-1)

1. Operator asks "what's the Tailscale-only network policy for phone-facing services?"
2. Claude Code's `wiki-query` skill (the replacement for the deleted `knowledge-query` orchestrator) reads `homelab-playbook/wiki/network/tailscale-policy.md` directly. No MCP roundtrip, no LLM extraction, no graph traversal.
3. Answer is returned in ≤ 200 ms file-read time.

**Acceptance signal:** Tier-1 query path takes < 200 ms wall-clock and consumes zero Anthropic/OpenAI tokens for retrieval (FR-WIKI-005, NFR-PERF-003).

### 4.6 Journey E — Container deploy of context-stack to ct-dev-homelab

1. Operator runs the Phase 2 deploy playbook against `ct-dev-homelab`.
2. Playbook ensures FalkorDB + Graphiti MCP server are up on `ct-ai-01` (or the dev-homelab equivalent), bound to `127.0.0.1`, reachable via Tailscale.
3. Playbook registers Graphiti with Claude Code (`claude mcp add --transport http graphiti http://...:8000/mcp/`).
4. Smoke tests run: write episode, read it back, verify FalkorDB Browser shows nodes.
5. Rollback path is exercised once (per G-Rollback gate) before promotion.

**Acceptance signal:** end-to-end deploy on `ct-dev-homelab` succeeds with `verify.yml` exit code 0; rollback path returns the container to pre-deploy state in ≤ 1 day operator-wall-time (FR-DEP-006, FR-DEP-007).

### 4.7 Journey F — Decommission migration (OMEGA + MemPalace removal day)

1. Operator runs the Phase 1 decommission playbook.
2. The four OMEGA hook entries are first disabled in `~/.claude/settings.json`, verified silent for one full Claude Code session, then removed entirely.
3. The `ai-dev-omega-memory` Ansible role and its group_vars are removed; `omega-memory` Python package uninstalled.
4. MemPalace: `~/.mempalace/` deleted; `ai-dev-mempalace` role deleted; three Hermes mempalace skills deleted; `wire-mempalace.yml` deleted; `knowledge-query` orchestrator deleted; conditional blocks removed from `config.yaml.j2`, `defaults/main.yml`, `verify.yml`.
5. Hermes verify run is executed end-to-end on `ct-dev-homelab` (or its successor); zero references to `mempalace` or `omega` survive.
6. Auto-memory is unaffected — `MEMORY.md` continues to be loaded.

**Acceptance signal:** zero matches for `grep -r -i 'mempalace\|omega' homelab/` (excluding decommission doc itself and git history) AND zero MemPalace/OMEGA processes running on `ct-dev-homelab` after the run (FR-DEC-009, FR-DEC-010).

---

## 5. Functional Requirements (FRs)

Each FR carries a unique ID, statement, rationale, observable acceptance signal, MoSCoW priority (MUST / SHOULD / COULD), and traceability to brief section and/or research file.

### 5.1 FR-DEC — Decommission requirements (MemPalace + OMEGA cleanup)

| ID | Statement | Priority | Trace |
|---|---|---|---|
| **FR-DEC-001** | Delete the workstation MemPalace store at `~/.mempalace/` (entire directory). | MUST | Brief §7.1 |
| **FR-DEC-002** | Delete the Ansible role `ai-dev-mempalace` (entire role tree). | MUST | Brief §7.1 |
| **FR-DEC-003** | Delete the three Hermes skills `mempalace-kg-query`, `mempalace-diary`, `mempalace-search`. | MUST | Brief §7.1 |
| **FR-DEC-004** | Delete the wiring playbook `wire-mempalace.yml`. | MUST | Brief §7.1 |
| **FR-DEC-005** | Edit Hermes `config.yaml.j2`, `defaults/main.yml`, `verify.yml` to remove every conditional that references `mempalace`. | MUST | Brief §7.1, §10.1 R7 |
| **FR-DEC-006** | Delete the degenerated orchestrator skill `knowledge-query` from the workstation. The skill is reborn as `wiki-query` in Phase 3 (FR-WIKI-001). | MUST | Brief §7.1, §8.3 |
| **FR-DEC-007** | First disable the four OMEGA entries in `~/.claude/settings.json` (verified silent for one full Claude Code session), then remove them entirely. | MUST | Brief §7.2 |
| **FR-DEC-008** | Remove the Ansible role `ai-dev-omega-memory` and its group_vars from the dev_hosts container playbook; uninstall the Python package `omega-memory`. | MUST | Brief §7.2 |
| **FR-DEC-009** | After Phase 1 completes, `grep -r -i 'mempalace\|omega' homelab/` (excluding the decommission doc itself, git history, and `_bmad-output/`) returns zero matches. | MUST | Journey F acceptance |
| **FR-DEC-010** | After Phase 1 completes, no MemPalace or OMEGA processes are running on `ct-dev-homelab`; `pgrep -f 'mempalace\|omega' = 0`. | MUST | Journey F acceptance |
| **FR-DEC-011** | Phase 1 includes a Hermes `verify.yml` run on `ct-dev-homelab` (or successor); the run exits 0. | MUST | Brief §10.1 R7 |
| **FR-DEC-012** | No data migration is performed from MemPalace or OMEGA stores; both are empty/near-empty. The decision is recorded in the decommission doc. | MUST | Brief §7.3, NG10 |

**Acceptance bundle (FR-DEC-*).** A successful Phase 1 produces (a) a clean `grep` baseline, (b) a green Hermes verify run, (c) auto-memory continuity confirmed by reading `MEMORY.md` end-to-end, (d) a tagged git commit recording the decommission state.

### 5.2 FR-CG — Code-graph (GitNexus) requirements

| ID | Statement | Priority | Trace |
|---|---|---|---|
| **FR-CG-001** | GitNexus is installed on the workstation as an MCP-native server (stdio transport), not in a remote container. | MUST | Brief §8.2; graphify-eval §Integration Patterns |
| **FR-CG-002** | GitNexus runs entirely local-only; no source code leaves the machine for code-parsing passes. | MUST | Brief §5 (Privacy), §8.2 |
| **FR-CG-003** | GitNexus is configured for the parent-folder-with-sub-repos topology over `~/workspace/homelab/` (covering `homelab/`, `homelab-bootstrap/`, `homelab-playbook/`). | MUST | Brief §8.2; graphify-eval §Multi-repo merge |
| **FR-CG-004** | GitNexus registers PreToolUse and PostToolUse hooks on Claude Code via `~/.claude/settings.json`. | MUST | Brief §8.2; graphify-eval §Communication Protocols (PreToolUse/PostToolUse) |
| **FR-CG-005** | GitNexus auto-reindexes on every commit (PostToolUse-on-commit); no branch or path filter is applied. | MUST | Director decision §0; closes brief Q3 |
| **FR-CG-006** | Incremental reindex after a typical commit completes in ≤ 30 s wall-clock on the operator's workstation. | MUST | NFR-PERF-004; brief K2 |
| **FR-CG-007** | Full reindex of `~/workspace/homelab/` (parent folder, all three sub-repos) completes in ≤ 60 s. | MUST | Brief K2 |
| **FR-CG-008** | On a representative cross-repo code question, the GitNexus-mediated answer consumes ≤ 1/5 the input tokens of an equivalent grep-and-read baseline (K1 ≥ 5×). | MUST | Brief §6 K1; graphify-eval §Headline finding |
| **FR-CG-009** | GitNexus produces a `GRAPH_REPORT.md`-style summary artifact (or equivalent) that is non-blank for every commit. | SHOULD | Brief §6 (non-blank-artifacts KPI) |
| **FR-CG-010** | GitNexus exposes its graph as JSON exportable to disk for migration / backup / inspection. | MUST | NFR-PORT-001; brief §10.1 R1 (exit ramp) |
| **FR-CG-011** | If GitNexus is unavailable, Claude Code degrades gracefully — the auto-memory + wiki paths continue to function. | MUST | NFR-AVAIL-001 |
| **FR-CG-012** | GitNexus does NOT make any LLM API call for code-parsing (AST-first, deterministic). | MUST | Director decision: GitNexus is local-AST, no LLM extraction |

### 5.3 FR-MEM — Memory (Graphiti) requirements

| ID | Statement | Priority | Trace |
|---|---|---|---|
| **FR-MEM-001** | Graphiti is deployed on `ct-ai-01` via Docker Compose with FalkorDB as the backend. | MUST | Brief §8.1; install-plan §2 |
| **FR-MEM-002** | Graphiti's MCP server uses HTTP transport (stdio not viable for remote container access). | MUST | Brief §8.1; install-plan §3 |
| **FR-MEM-003** | The Graphiti container binds to `127.0.0.1` and is reached via Tailscale tailnet (matches phone-notifications-tailscale pattern). | MUST | Brief §8.1; install-plan §6 Step 9 |
| **FR-MEM-004** | Phase 1 LLM is `gpt-4o-mini` (cloud); embeddings are `text-embedding-3-small` (1536 dims). | MUST | Brief §8.1; install-plan §4 |
| **FR-MEM-005** | All writes use `group_id="tom-personal"` for namespacing. | MUST | Brief §8.1; install-plan §3 |
| **FR-MEM-006** | `SEMAPHORE_LIMIT=5` is set on the Graphiti container to cap concurrent LLM calls. | MUST | Brief §10.1 R6; install-plan §3 |
| **FR-MEM-007** | Graphiti returns a useful prior decision on ≥ 50% of first-shot recall queries by week 4 (K5). | MUST | Brief §6 K5 |
| **FR-MEM-008** | Graphiti captures ≥ 25 distinct facts per week after week 2 (K4). | MUST | Brief §6 K4 |
| **FR-MEM-009** | Graphiti exposes the standard MCP tool surface at minimum: `add_episode`, `search_facts`, `search_nodes`, `get_episodes`, `delete_entity_edge`, `delete_episode`, `clear_graph`, `get_status`. | MUST | Install-plan §3 |
| **FR-MEM-010** | `~/.claude/CLAUDE.md` is updated with a "Memory (Graphiti)" section instructing the model when to read (`search_facts` / `search_nodes`) and when to write (`add_episode`). | MUST | Install-plan §3 (Slash commands & skills); brief §10.1 R4 |
| **FR-MEM-011** | Graphiti telemetry is disabled (`GRAPHITI_TELEMETRY_ENABLED=false`). | MUST | Install-plan §3 |
| **FR-MEM-012** | Graphiti's data directory `/srv/graphiti/data` is exportable via `MATCH (n)-[r]->(m) RETURN n,r,m` to JSON for backup/migration; an export script exists in the repo. | SHOULD | Install-plan §10 (exit ramp); NFR-PORT-002 |
| **FR-MEM-013** | If Graphiti is unavailable, Claude Code degrades gracefully — wiki + auto-memory continue to function; no blocking tool call hangs > 3 s before timeout. | MUST | NFR-AVAIL-002 |
| **FR-MEM-014** | Graphiti backup cadence is defined in the Architecture phase (deferred per director decision); the PRD requires that *some* backup mechanism is documented and exercised once before Phase 2 promotion. | SHOULD | Brief Q5 (deferred to Architecture); director decision |
| **FR-MEM-015** | Graphiti FalkorDB resident memory remains < 200 MB at the operator's data scale through week 4. | MUST | NFR-FOOTPRINT-001; brief §5 |

### 5.4 FR-WIKI — LLM Wiki tier requirements

| ID | Statement | Priority | Trace |
|---|---|---|---|
| **FR-WIKI-001** | A new skill `wiki-query` is introduced under `~/.claude/skills/` (or equivalent) replacing the deleted `knowledge-query`. | MUST | Brief §8.3; closes brief Q2 (location decided) |
| **FR-WIKI-002** | The wiki content tree lives at `homelab-playbook/wiki/` (per director decision). | MUST | Director decision |
| **FR-WIKI-003** | The wiki is file-based, markdown-only, zero-MCP at the retrieval surface (no daemon, no DB, no LLM extraction at read time). | MUST | Brief §8.3 |
| **FR-WIKI-004** | The wiki tree contains an `index.md` summarising what each subtree covers; Claude Code reads `index.md` at session start as part of project context. | MUST | Brief §7 (query hierarchy doc) |
| **FR-WIKI-005** | A wiki-tier query (file read of one wiki entry) completes in ≤ 200 ms wall-clock and consumes zero Anthropic/OpenAI tokens for retrieval (LLM tokens are only spent if the model summarises content into the response). | MUST | Journey D acceptance; NFR-PERF-003 |
| **FR-WIKI-006** | At least three wiki entries are authored before Phase 3 exit, each consumed by ≥ 3 distinct Claude Code sessions (tracked via operator log). | MUST | Brief §4.3 (Phase 3 gate) |
| **FR-WIKI-007** | A "unified query hierarchy" document is published describing tier order: Tier 1 wiki → Tier 2 GitNexus → Tier 3 Graphiti → Tier 4 auto-memory. | MUST | Brief §4.1 G7 |
| **FR-WIKI-008** | The wiki tree is version-controlled inside `homelab-playbook` and changes ride the existing git workflow. | MUST | Brief §8.3 (curated content) |
| **FR-WIKI-009** | The `wiki-query` skill ships with no LLM dependency — its retrieval is plain file-read; semantic interpretation is whatever Claude Code does with the returned content. | MUST | Brief §8.3 |
| **FR-WIKI-010** | Wiki content authorship at scale is explicitly out of scope; the deliverable is the *tier mechanism*, not bulk content (operator curates over time). | MUST | Brief §4.2 NG4 |

### 5.5 FR-LLM — LiteLLM bridge requirements (Phase 4 stretch)

| ID | Statement | Priority | Trace |
|---|---|---|---|
| **FR-LLM-001** | The LiteLLM bridge routes Graphiti's LLM calls (only) to `hybrid_gemma_serving`. GitNexus is excluded from the bridge per director decision (GitNexus is local-AST, no LLM extraction). | SHOULD | Director decision; brief §8.4 |
| **FR-LLM-002** | The bridge uses Graphiti's `OpenAIGenericClient` path (`/v1/chat/completions`, NOT the default `/v1/responses`) for LiteLLM/Ollama compatibility. | SHOULD | Install-plan §4 |
| **FR-LLM-003** | The bridge sets `OPENAI_BASE_URL` to the LiteLLM gateway and `MODEL_NAME` to the local reasoner model name; `OPENAI_API_KEY` is set to a non-empty placeholder (LiteLLM does not validate it). | SHOULD | Install-plan §4 |
| **FR-LLM-004** | Embeddings remain on OpenAI `text-embedding-3-small` in Phase 4 (per maintainer caveat about small-model JSON quality on extraction); Phase 4 does NOT route embeddings through LiteLLM. | MUST | Brief §8.1; install-plan §4 |
| **FR-LLM-005** | The bridge passes a 50-fact validation set with ≥ 95% well-formed extraction JSON before promotion. | MUST | Brief §4.3 (Phase 4 gate); brief §10.1 R3 |
| **FR-LLM-006** | If the local model produces malformed JSON above the 5% threshold, the bridge auto-falls back to cloud `gpt-4o-mini` and emits a log line. | MUST | Brief §8.4 (failure mode) |
| **FR-LLM-007** | Phase 4 is explicitly stretch — Phase 1–3 ship without the bridge and without dependency on `hybrid_gemma_serving` delivery. | MUST | Brief §9 (relationship); §4.3 |
| **FR-LLM-008** | The bridge is reversible in ≤ 1 day — flipping `OPENAI_BASE_URL` and `MODEL_NAME` back to OpenAI defaults restores Phase-1-LLM behaviour. | MUST | NFR-MAINT-001; brief §5 (reversibility) |

### 5.6 FR-OBS — Observability and cost-tracking requirements

| ID | Statement | Priority | Trace |
|---|---|---|---|
| **FR-OBS-001** | A weekly cost-check procedure exists and is documented: read OpenAI usage page + Anthropic usage export; record total in a journal entry. | MUST | Brief §6 K3; install-plan §8 |
| **FR-OBS-002** | A daily $1 hard-cap rule is encoded: if any single day's combined Graphiti-induced spend exceeds $1, ingestion is auto-throttled (e.g., temporarily drop `SEMAPHORE_LIMIT` to 1) and the operator is alerted. | MUST | NFR-COST-002 |
| **FR-OBS-003** | Graphiti MCP server logs are captured at INFO level and rotated monthly; the log file is the insurance policy for the exit ramp (replay episodes). | SHOULD | Install-plan §10 (exit ramp) |
| **FR-OBS-004** | A weekly retro note records: K1 token-reduction sample, K2 reindex timings, K3 spend, K4 facts/week, K5 first-shot-recall hit rate, K6 subjective uplift. | MUST | Brief §6 |
| **FR-OBS-005** | A "good-catch" tally is maintained — operator-tagged moments where Graphiti returned a useful prior decision; target ≥ 3 over the 4-week pilot. | SHOULD | Brief §6 K5; success-metric scorecard |
| **FR-OBS-006** | GitNexus tool-hit-rate is logged (how often Claude Code actually calls GitNexus tools); zero calls for one full week triggers a `CLAUDE.md` review. | SHOULD | Install-plan §8 (analogous Graphiti hit-rate signal) |

### 5.7 FR-DEP — Deployment and install requirements

| ID | Statement | Priority | Trace |
|---|---|---|---|
| **FR-DEP-001** | Phase 1 (decommission) is deployed via Ansible playbook(s) targeting workstation, dev_hosts container, and Hermes config; the playbook is idempotent. | MUST | Brief §4.3; FR-DEC-* |
| **FR-DEP-002** | Phase 2 Graphiti deploy on `ct-ai-01` is captured in `/srv/graphiti/docker-compose.yml` + `.env` (mode 600); `.env` is NOT committed to git. | MUST | Install-plan §2; project rule (no secrets in repo) |
| **FR-DEP-003** | Phase 2 GitNexus install is captured in a workstation-side script or Ansible role; install includes Claude Code MCP registration. | MUST | Brief §8.2 |
| **FR-DEP-004** | Phase 2 deploy is first validated end-to-end on `ct-dev-homelab` before any production-class container; this matches the operator's standing per-story test-container policy. | MUST | Brief §4.1 G8; project rule (per `feedback_test_container.md`) |
| **FR-DEP-005** | Phase 3 wiki rollout consists of (a) creating `homelab-playbook/wiki/` tree with `index.md`, (b) authoring three seed entries, (c) installing the `wiki-query` skill. | MUST | Brief §4.3 |
| **FR-DEP-006** | An end-to-end deploy run on `ct-dev-homelab` exits with `verify.yml` returning 0 and all five smoke tests (install-plan §7) passing. | MUST | Journey E acceptance |
| **FR-DEP-007** | A documented rollback path exists for each phase (Phase 1: re-install OMEGA + MemPalace from prior commit; Phase 2: `docker compose down` + `claude mcp remove graphiti` + GitNexus uninstall; Phase 3: skill removal; Phase 4: env var revert per FR-LLM-008). Rollback is exercised once on `ct-dev-homelab` before promotion. | MUST | Brief §6 G-Rollback |
| **FR-DEP-008** | The deploy never commits secrets or `.env` files; secret material lives in `.env` (chmod 600) on target host or in the existing vault pattern (Sparkle-style ansible-vault). | MUST | Project rule (CLAUDE.md security rules) |
| **FR-DEP-009** | The dev_hosts container playbook references in `homelab-playbook` are updated to drop OMEGA group_vars and any MemPalace references. | MUST | FR-DEC-008 |
| **FR-DEP-010** | A pinned image tag is used for `graphiti-mcp` (e.g., `zepai/graphiti-mcp:v1.0.2`), not `latest`, for reproducibility. | SHOULD | Install-plan §10 (week-1 risk) |

**FR distribution summary.**
- **Total FRs: 73** across seven groups (DEC ×12, CG ×12, MEM ×15, WIKI ×10, LLM ×8, OBS ×6, DEP ×10).
- **MoSCoW: 63 MUST / 10 SHOULD / 0 COULD.** (No COULD-tagged items at this scope; the WIKI bulk-content out-of-scope item could be reframed as COULD if the operator changes their mind, but is currently a NG.)
- **Adjustment: priority distribution skews MUST-heavy (~86%) because every decommission step is hard-required for cleanup and most MEM/CG items are baseline functionality.** This is acknowledged as a deviation from the 60/30/10 hint; the rationale is that the product is a consolidation play with little optional surface — a single missed decommission step leaves dead code in the homelab. The architecture phase may downgrade specific items to SHOULD if costs justify; flagged as an architectural question (§13 Q1).

---

## 6. Non-Functional Requirements (NFRs)

Each NFR carries an ID, measurable threshold, measurement method, and traceability.

### 6.1 NFR-PERF — Performance

| ID | Threshold | Measurement | Trace |
|---|---|---|---|
| **NFR-PERF-001** | Claude Code session-start overhead introduced by the stack: < 1 s wall-clock. | Time from `claude` invocation to first prompt-ready over 5 sessions, averaged. Compare against pre-deploy baseline. | Brief §5; G-Latency |
| **NFR-PERF-002** | Claude Code query (Graphiti `search_facts`, GitNexus AST query) p95 latency: < 500 ms. | Time from tool-call dispatch to tool-result-received over 50 representative queries. | Brief §6; install-plan §8 |
| **NFR-PERF-003** | Wiki Tier-1 file-read query: < 200 ms wall-clock. | Single `read_file` call against a wiki entry, measured over 20 calls. | Journey D; FR-WIKI-005 |
| **NFR-PERF-004** | GitNexus incremental reindex after typical commit: < 30 s. | PostToolUse hook duration, captured from hook-run logs over 10 typical commits. | Brief K2; FR-CG-006 |
| **NFR-PERF-005** | GitNexus full reindex of parent folder: < 60 s. | Cold-start full reindex on `~/workspace/homelab/`. | Brief K2; FR-CG-007 |
| **NFR-PERF-006** | Graphiti `add_episode` ingestion: < 5 s per typical episode (~2k input tokens). | Tool-call duration measured over 30 episodes. | Install-plan §4 (cost model implies sub-5 s) |

### 6.2 NFR-COST — Cost

| ID | Threshold | Measurement | Trace |
|---|---|---|---|
| **NFR-COST-001** | All-in monthly Anthropic + OpenAI spend attributable to the stack: < $20/month at steady state. | Monthly OpenAI billing + Anthropic usage export, manually summed and journaled. | Brief §5; §6 K3 |
| **NFR-COST-002** | Daily hard cap: < $1/day. If exceeded, auto-throttle ingestion (drop `SEMAPHORE_LIMIT` to 1) and alert operator. | Daily OpenAI billing dashboard; FR-OBS-002 implementation. | FR-OBS-002 |
| **NFR-COST-003** | Phase 4 LiteLLM bridge MUST not increase spend beyond Phase 1 baseline (local-LLM substitution is cost-neutral or cheaper). | Compare 7-day pre-bridge vs post-bridge spend at otherwise-equal usage. | Brief §8.4 |

### 6.3 NFR-PRIV — Privacy

| ID | Threshold | Measurement | Trace |
|---|---|---|---|
| **NFR-PRIV-001** | Source code never leaves the workstation for code-parsing passes. GitNexus is local-only. | Inspect GitNexus binary network behaviour (e.g., `tcpdump` snapshot during reindex shows no outbound LLM-API host calls). | Brief §5; FR-CG-002, FR-CG-012 |
| **NFR-PRIV-002** | Embeddings of conversational fact semantics MAY go to OpenAI (`text-embedding-3-small`); this is documented and accepted. Source code does NOT cross the boundary. | Document review; embedding-call payload audit on a sample episode. | Brief §10.1 R5 |
| **NFR-PRIV-003** | Phone-facing surfaces (none in scope today) MUST be Tailscale-only. Reserved for future option. | N/A in Phase 1–4; documented for forward compliance. | Brief §5; project rule |

### 6.4 NFR-FOOTPRINT — Resource footprint

| ID | Threshold | Measurement | Trace |
|---|---|---|---|
| **NFR-FOOTPRINT-001** | FalkorDB resident memory: < 200 MB. | `docker stats graphiti-falkordb` over 24 h after week 4. | Brief §5; FR-MEM-015 |
| **NFR-FOOTPRINT-002** | GitNexus daemon resident memory: < 500 MB. | Process RSS sample over 24 h on workstation. | Brief §5 |
| **NFR-FOOTPRINT-003** | Combined disk footprint of stack data (FalkorDB data + GitNexus indexes + wiki tree): < 5 GB. | `du -sh /srv/graphiti/data` + GitNexus index dir + `homelab-playbook/wiki/`. | Aggregate of brief constraints; install-plan §2 (~100–200 MB Graphiti week 1) |

### 6.5 NFR-AVAIL — Availability and graceful degradation

| ID | Threshold | Measurement | Trace |
|---|---|---|---|
| **NFR-AVAIL-001** | If GitNexus is unavailable, Claude Code session continues; auto-memory + wiki paths function. No tool-call hang > 3 s. | Stop GitNexus daemon; run a representative session; verify completion + < 3 s timeout. | FR-CG-011 |
| **NFR-AVAIL-002** | If Graphiti is unavailable, Claude Code session continues; auto-memory + wiki + GitNexus continue. No tool-call hang > 3 s. | Stop FalkorDB or graphiti-mcp containers; run a representative session; verify. | FR-MEM-013 |
| **NFR-AVAIL-003** | If LiteLLM gateway is unavailable in Phase 4, the bridge auto-falls back to cloud `gpt-4o-mini` (FR-LLM-006). | Stop LiteLLM; verify Graphiti still ingests an episode via cloud path. | FR-LLM-006 |

### 6.6 NFR-MAINT — Maintainability

| ID | Threshold | Measurement | Trace |
|---|---|---|---|
| **NFR-MAINT-001** | Each stack component is unwireable in ≤ 1 day operator-wall-time. | Measured on FR-DEP-007 rollback exercise. | Brief §5 |
| **NFR-MAINT-002** | Decommission rollback (re-install OMEGA + MemPalace from prior git commit) is documented and exercisable. | Document review + dry-run on `ct-dev-homelab`. | FR-DEP-007 |

### 6.7 NFR-SUPP — Upstream support / project liveness

| ID | Threshold | Measurement | Trace |
|---|---|---|---|
| **NFR-SUPP-001** | Every adopted external component must show ≥ 3 months of upstream commit activity at adoption time. | Inspect GitHub commit graph for `getzep/graphiti`, GitNexus repo at adoption point. | Brief §10.1 R1 (abandonment risk) |
| **NFR-SUPP-002** | Documented exit ramp exists for each adopted component (Graphiti → episode-replay/Cypher dump; GitNexus → JSON graph export to alternative tool such as CodeGraphContext). | Document review at end of Phase 2. | Brief §10.1 R1; install-plan §10 |

### 6.8 NFR-PORT — Portability / data export

| ID | Threshold | Measurement | Trace |
|---|---|---|---|
| **NFR-PORT-001** | GitNexus graph artifacts are exportable to JSON for migration / backup. | Run export command; inspect output. | FR-CG-010 |
| **NFR-PORT-002** | Graphiti graph is exportable via Cypher dump (`MATCH (n)-[r]->(m) RETURN n,r,m`) AND via episode-replay log. Both methods are documented. | Document + run on a populated Graphiti at Phase 2 exit. | FR-MEM-012; install-plan §10 |
| **NFR-PORT-003** | Wiki content is plain markdown in version control — inherently portable; no export needed. | N/A — file-based by construction. | FR-WIKI-003 |

**NFR distribution summary.** Total NFRs: 25 across eight categories (PERF ×6, COST ×3, PRIV ×3, FOOTPRINT ×3, AVAIL ×3, MAINT ×2, SUPP ×2, PORT ×3). Every NFR has a measurable threshold and a defined measurement method.

---

## 7. Success Metrics and KPIs

The 6-metric KPI scorecard is the steady-state success measure, evaluated at week 4 of usage. **Decision rule: 4-of-6 green at week 4 → keep the stack; otherwise migrate (per brief §6 Phase 2 gate).**

| # | KPI | Green threshold | Measurement source | Owner |
|---|---|---|---|---|
| **K1** | Token reduction on real Claude Code tasks | ≥ 5× input-token reduction vs grep-and-read baseline | Operator-tagged before/after comparison on three representative cross-repo questions per week | Operator |
| **K2** | Re-index time after typical commit | ≤ 30 s incremental, ≤ 60 s full reindex | PostToolUse hook duration logs | Auto-captured |
| **K3** | Anthropic + OpenAI spend per month | < $20/month all-in at steady state | OpenAI billing + Anthropic usage export, summed weekly | Operator |
| **K4** | Non-blank artifacts | 100% of GitNexus reindexes produce non-blank GRAPH_REPORT.md (or equivalent) AND Graphiti `add_episode` returns a UUID for every captured fact | Hook log inspection + Graphiti tool-result inspection | Auto-captured |
| **K5** | Good-catch rate | ≥ 50% of first-shot recall queries return a useful prior decision by week 4; ≥ 3 "good catches" tagged over the 4-week pilot | Operator-tagged retro entries | Operator |
| **K6** | Subjective agentic-workflow uplift | "Yes" on ≥ 60% of sessions where the stack was queried; subjective rating at minimum "noticeable" by week 4 retro | Weekly retro note | Operator |

**Hard gates (separate from K1–K6):**

- **G-Latency.** Zero observable Claude Code latency regression at session start (NFR-PERF-001). Measured against a 5-session pre-deploy baseline. Regression here fails Phase 2 outright.
- **G-Rollback.** End-to-end rollback to pre-Context-Stack state validated on `ct-dev-homelab` by end of Sprint 4. If rollback is not validated, the stack does not promote off `ct-dev-homelab`.

---

## 8. Out of Scope (MoSCoW WONT)

The following are explicitly **WONT** for this product, reaffirming and extending brief §4.2:

- **Hermes memory layer.** Hermes' memory needs are separate; `ct-dev-test` is retired (brief NG3).
- **Customer-facing or production multi-tenant deployments.** Single-operator product (brief NG1).
- **Multi-tenant / RBAC / per-namespace isolation** (brief NG7). The single `group_id="tom-personal"` in Graphiti is the only namespace.
- **LLM Wiki content authorship at scale.** The product delivers the *tier mechanism*, not bulk content (brief NG4; FR-WIKI-010).
- **Code-graph for binary / non-text artifacts** (e.g., images, audio, video). GitNexus is text-source-only; graphify's multimodal pass is not adopted.
- **Mobile / phone-facing surfaces** for this product. Tailscale-ntfy is a separate project per memory note `project_phone_notifications_tailscale.md`.
- **Replacing Claude Code auto-memory (`MEMORY.md`).** Auto-memory is the only memory tier currently working; Context Stack augments, not replaces (brief NG6).
- **A new graph database deployment beyond FalkorDB** (brief NG8). No Neo4j, no Kuzu, no Neptune.
- **Visual UI / dashboard for the stack** (brief NG9). CLI + MCP only. The FalkorDB Browser UI shipped with the FalkorDB image is a side-effect, not a product surface.
- **Migrating data from MemPalace or OMEGA stores** (brief NG10; FR-DEC-012). Both are empty/near-empty.
- **Adopting Mem0 / Letta / Honcho / Cognee / OpenMemory MCP** (per memory-systems-eval §8). Decision is to adopt only Graphiti from the memory category.
- **Adopting graphify** (per graphify-eval). Decision is to adopt GitNexus over graphify on MCP-native, AST-first, parent-folder-fit, and PostToolUse-on-commit grounds.

---

## 9. Dependencies and Assumptions

### 9.1 External dependencies

- **Anthropic API access** (Claude Code's underlying model substrate). Pricing per 2026-04 Anthropic tier table.
- **OpenAI API access** for `gpt-4o-mini` (Graphiti LLM, Phase 1) and `text-embedding-3-small` (embeddings, Phase 1–4). Account-level spend tracking enabled.
- **Docker on `ct-ai-01`** with docker-compose, working internet egress for image pulls (or local-build fallback per install-plan §6 Step 4a).
- **Tailscale tailnet** reachable from the operator's workstation to `ct-ai-01` (existing — phone-notifications pattern).
- **Existing `hybrid_gemma_serving` plan** is referenced as the Phase 4 target; this product does NOT block on its delivery (brief §9 — "Phase 1–3 ship without it").
- **Existing Claude Code auto-memory** continues to work; this product does not replace it (brief NG6).

### 9.2 Assumptions

- The operator's daily Claude Code workflow is on the workstation, not on a remote container.
- `ct-ai-01` is reachable over Tailscale for the duration of Phase 2+.
- `ct-dev-homelab` exists or can be provisioned for Phase 2 validation.
- The operator's existing Ansible vault pattern (Sparkle-style) is available for any secret material; no new vault infrastructure is required.
- `gpt-4o-mini` and `text-embedding-3-small` remain available at quoted price points through 4-week pilot; if either is deprecated, a re-evaluation note is filed (per brief §10.1 R5).

---

## 10. Risks (carry from brief §10)

Risks below extend the brief register with quantitative dimensions where possible.

| ID | Risk | Severity | Quant. dimension | Mitigation |
|---|---|---|---|---|
| **R1** | GitNexus is a young, single-maintainer project; abandonment risk. | High | NFR-SUPP-001: ≥ 3 months upstream activity at adoption | Documented exit ramp to CodeGraphContext (Neo4j, MCP) or graphify per brief §10.1 R1; FR-CG-010 export |
| **R2** | Graphiti's bi-temporal value depends on ≥ 1 month of sustained use before payoff; operator may judge prematurely. | Medium | KPI scorecard locked to week 4 (FR-OBS-004) | No promote/demote before week 4 |
| **R3** | LiteLLM bridge unproven for Graphiti's extraction-JSON quality. | Medium | FR-LLM-005: 95% well-formed-JSON gate on 50-fact set | Phase 4 stretch + gated; Phase 1–3 use cloud `gpt-4o-mini`; auto-fallback (FR-LLM-006) |
| **R4** | MCP-vs-skill ecosystem trajectory — skill-first bets age fast. | Medium | Both Graphiti and GitNexus are MCP-native; `wiki-query` is the only skill bet, intentionally thin | Continuous monitoring; re-evaluate skill scope at Phase 3 retro |
| **R5** | OpenAI dependency for Graphiti embeddings keeps a cloud line. | Low | NFR-PRIV-002: documented and accepted; no source code crosses boundary | Embedding-only; flagged for Phase 4 re-review (FR-LLM-004) |
| **R6** | Spend creep if Graphiti ingestion becomes chatty. | Medium | NFR-COST-001 < $20/mo; NFR-COST-002 daily $1 cap; FR-MEM-006 SEMAPHORE_LIMIT=5 | FR-OBS-001 weekly cost-check; FR-OBS-002 auto-throttle |
| **R7** | Decommission breakage — Hermes config edits are wide-surface. | Medium | FR-DEC-011 mandatory verify run on `ct-dev-homelab` | Phase 1 includes a Hermes verify run before Phase 2 begins |
| **R8** | MoSCoW MUST-heavy distribution may make Phase 1 over-rigid; missed items block progress. | Low | 63/73 FRs are MUST | Architecture phase may downgrade specific items to SHOULD; flagged as Q1 in §13 |
| **R9** | Operator subjective uplift (K6) is hard to measure rigorously. | Low | Weekly retro note (FR-OBS-004); ≥ 60% session threshold | Accept subjective scoring; document operator-defined "noticeable" baseline at week 1 |

---

## 11. Acceptance Criteria for Product Release ("done")

The product is considered "done" (Phase 2 promotion plus Phase 3 delivery, with Phase 4 as stretch) when **ALL** of the following hold:

1. **All FR-MUST items pass.** Every MUST-tagged FR (63 total) has its acceptance signal demonstrated on `ct-dev-homelab` and on the operator's workstation as applicable.
2. **All NFR thresholds met.** All 25 NFRs have measured values within threshold over the 4-week pilot window.
3. **KPI scorecard: ≥ 4-of-6 green at week 4.** K1, K2, K3, K4, K5, K6 measured per §7; ≥ 4 are green.
4. **Decommission complete.** FR-DEC-009 and FR-DEC-010 hold: zero MemPalace/OMEGA references in homelab repo (excluding decommission docs and git history); zero MemPalace/OMEGA processes running on `ct-dev-homelab`.
5. **End-to-end deploy validated on `ct-dev-homelab`.** FR-DEP-006: `verify.yml` exits 0; all five smoke tests (install-plan §7) pass.
6. **Rollback validated on `ct-dev-homelab`.** G-Rollback gate satisfied per FR-DEP-007.
7. **G-Latency satisfied.** NFR-PERF-001: zero observable session-start regression vs 5-session baseline.
8. **Phase 3 wiki seeded.** ≥ 3 wiki entries authored AND consumed by ≥ 3 distinct Claude Code sessions each (FR-WIKI-006).
9. **Documentation complete.** Unified query hierarchy doc published (FR-WIKI-007); install + rollback runbook in `homelab-playbook/`; weekly retro template established (FR-OBS-004).

If criterion 3 (4-of-6 KPI green) fails, the product enters the migrate-or-revert decision path per brief §4.3 Phase 2 gate, and the rollback paths in FR-DEP-007 are exercised.

---

## 12. Validation and Test Strategy

This PRD is one of three Phase 2/5 deliverables. Detailed validation artifacts are produced in subsequent phases:

- **`acceptance.md`** (Phase 5) — Acceptance test cases. One scenario per FR-MUST minimum, mapping each test to the FR ID + KPI/NFR. Includes the install-plan §7 five smoke tests as the canonical Phase 2 acceptance suite.
- **`e2e-deployment.md`** (Phase 5) — End-to-end deploy procedure for `ct-dev-homelab`: prerequisites, step-by-step playbook execution, smoke-test run, rollback exercise, sign-off checklist. Captures the full G-Rollback gate run.
- **`adrs/`** — Architecture Decision Records, populated in the Architecture phase. Expected ADR slots (non-exhaustive): backup cadence for Graphiti (closes brief Q5); GitNexus exact distribution channel; LiteLLM bridge implementation surface; wiki-query skill structural design.

**Testability principle.** Every FR has at least one observable signal in this PRD. Phase 5 expands those signals into runnable test cases or operator-verifiable procedures. No test in Phase 5 should require a new requirement to be invented; if Phase 5 finds an untested observable signal, that is a PRD bug to be fixed by addendum.

---

## 13. Open Questions (live)

These are the genuine architectural questions remaining after the brief's director-resolved decisions. Each is owned by the architecture phase. **No item in this list re-litigates a director-resolved decision.**

| ID | Question | Owner | Resolved by |
|---|---|---|---|
| **Q1** | MoSCoW MUST-heavy distribution (~79%) may be over-rigid. Should specific FRs be downgraded to SHOULD, and if so, which? | Architecture phase | Architecture review of FR-MEM-014 (backup), FR-OBS-003 (log retention), FR-DEP-010 (image pinning), FR-CG-009 (GRAPH_REPORT format) |
| **Q2** | Graphiti backup cadence — `zfs send` of `/srv/graphiti/data` schedule and retention window. | Architecture phase | Phase 2 architecture (deferred per director decision) |
| **Q3** | Wiki content schema — does the wiki tree enforce a frontmatter standard (YAML), section-heading conventions, or freeform markdown? | Architecture phase | Phase 3 architecture |
| **Q4** | LiteLLM bridge implementation surface — does Graphiti's `mcp-v1.0.2` expose `OpenAIGenericClient` selection without forking, or is a wrapper required? (Open verification step from install-plan §10 #2.) | Phase 4 spike | Pre-Phase-4 verification |
| **Q5** | GitNexus exact install distribution channel and pinned version — is it pip-installable, source-built, or distributed otherwise? Sub-question: which version pins to use. | Architecture phase | Phase 2 architecture |
| **Q6** | Daily $1 hard-cap auto-throttle implementation surface — where does the hook live (cron, OpenAI usage poll, MCP-server middleware)? | Architecture phase | Phase 2 architecture (FR-OBS-002) |
| **Q7** | Wiki-query skill structural design — read-on-demand vs preload-index-at-session-start; concrete FR-WIKI-001 surface. | Architecture phase | Phase 3 architecture |
| **Q8** | Concrete FR-CG export format for the GitNexus graph (FR-CG-010) — JSON schema + tooling for replay into a successor (CodeGraphContext). | Architecture phase | Phase 2 architecture |

---

## 14. Glossary (extends brief §11)

In addition to brief §11 terms (MCP, AST, Leiden, bi-temporal, GraphRAG, FalkorDB, LiteLLM, Wing/Room/Hall):

| Term | Definition |
|---|---|
| **Tier-1 / Tier-2 / Tier-3 / Tier-4** | The query hierarchy specified in FR-WIKI-007. Tier 1 = LLM Wiki (file-based, zero-MCP). Tier 2 = GitNexus code-graph (MCP, AST). Tier 3 = Graphiti memory (MCP, bi-temporal). Tier 4 = Claude Code auto-memory (`MEMORY.md`, deterministic markdown). Order is fastest/cheapest first. |
| **G-Latency / G-Rollback** | Hard gates separate from the K1–K6 KPI scorecard. G-Latency: NFR-PERF-001. G-Rollback: FR-DEP-007 + the brief's §6 hard gate. |
| **K1–K6** | The 6 KPIs of the success scorecard (§7). K1=token reduction, K2=reindex time, K3=spend, K4=non-blank artifacts, K5=good-catch rate, K6=subjective uplift. |
| **Decommission doc** | A markdown deliverable in `homelab-playbook/` produced as part of Phase 1, recording every action taken and the FR-DEC-012 "no-data-migration" record. |
| **`ct-ai-01`** | The LXC container hosting Graphiti + FalkorDB. Existing in the operator's environment (per project memory). |
| **`ct-dev-homelab`** | The dedicated test container used for end-to-end deploy validation per the operator's standing policy (`feedback_test_container.md`). |
| **`tom-personal`** | The single Graphiti `group_id` namespace used by this single-operator product. |

---

## 15. References

### 15.1 BMAD planning artifacts (this product)

- `homelab-playbook/_bmad-output/planning-artifacts/products/context-stack/product-brief.md` — Phase 1 brief; primary input.

### 15.2 Source research artifacts

- `homelab-playbook/_bmad-output/planning-artifacts/research/technical-graphify-evaluation-2026-04-25.md` — graphify and code-graph landscape; source of K1 calibration anchor (~5–10× on real medium-size repos; NOT 71.5×); confirms GitNexus's MCP-native + PreToolUse/PostToolUse hooks + parent-folder topology fit.
- `homelab-playbook/_bmad-output/planning-artifacts/research/technical-memory-systems-evaluation-2026-04-25.md` — memory-systems landscape; source of Graphiti adoption decision (only candidate offering bi-temporal validity); explicit do-not-adopt list (Mem0, Letta, Honcho, Cognee, OpenMemory MCP).
- `homelab-playbook/_bmad-output/planning-artifacts/research/graphiti-claude-code-install-plan-2026-04-25.md` — shovel-ready Graphiti install runbook; source of all §5.3 (FR-MEM) deployment specifics: FalkorDB recipe, MCP HTTP transport, `127.0.0.1`-bind + Tailscale-reach, `gpt-4o-mini` + `text-embedding-3-small` defaults, `SEMAPHORE_LIMIT=5`, `tom-personal` group_id, smoke-test plan, exit-ramp pattern.

### 15.3 Project memory (cited by reference)

- `project_ai_dev_container.md` — Epic 6 superseded by this product.
- `project_hybrid_gemma_serving.md` — Phase 4 LiteLLM bridge target.
- `project_phone_notifications_tailscale.md` — Tailscale-only network defaults; phone-facing surfaces are out of scope but the network policy is inherited.
- `feedback_test_container.md` — `ct-dev-homelab` per-story validation policy.
- `/home/developer/.claude/projects/-home-developer-workspace-homelab/memory/MEMORY.md` — auto-memory; Tier 4 of the query hierarchy; unaffected by decommission.

### 15.4 Companion product brief (predecessor)

- `homelab-playbook/_bmad-output/planning-artifacts/product-brief-ai-dev-container.md` — original brief that introduced OMEGA + MemPalace as Phase 2b knowledge management. Context Stack supersedes that Phase 2b plan.

---

**End of PRD — handoff to Architecture phase.**
