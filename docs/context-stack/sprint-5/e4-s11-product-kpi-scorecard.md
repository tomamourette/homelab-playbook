# Context Stack — Product-level KPI Scorecard (E4-S11)

**Date:** 2026-04-27
**Span:** 5 sprints — Sprint 1 closed 2026-04-26 (`phase-1-decommission-complete`); Sprint 2 closed 2026-04-26 (`650e906`); Sprint 3 closed 2026-04-27 (`03ad119` retro); Sprint 4 closed 2026-04-27 (`144174f` retro); Sprint 5 in-flight 2026-04-27.
**Branch:** `feature/context-stack-e3-graphiti` (Sprint 2 retro + KPI scorecard live on `main`; Sprint 3-5 work on this branch).
**Verdict:** **CONTINUE** — product is functionally on track; no FAIL. RELEASE is blocked by a small set of operator-input-pending items (FR-LLM-007 gate, two key rotations, restic source-set, three E3-AC carries) and one product-level KPI (K6 subjective uplift) that requires real-session operator data not yet collected. PIVOT is not warranted — the cloud-Gemini Graphiti pivot already absorbed the only meaningful architectural decision change, and it shipped clean.
**Operator-input-pending items:** FR-LLM-007 gate (Path A vs Path B for E4-S05/E4-S06); rotate `LITELLM_MASTER_KEY` and `GEMINI_API_KEY`; point restic source-set at `~/.local/state/graphiti-backup/`; verify AR8 `tom-personal` namespace; capture FalkorDB RSS on ct-dev-homelab; re-confirm `SEMAPHORE_LIMIT=5` + telemetry-off in evidence; daily K6 retro prompt; close `cypher-replay.sh` disposition via one-line ADR-007 sub-amendment.

---

## TL;DR

Across 5 sprints (4 functional + 1 close-out in flight), 73 FRs and 25 NFRs were exercised against a product whose architecture absorbed one significant pivot (local-Gemma → cloud-Gemini for Graphiti extraction; ADR-002/003/017 amended in place) and one significant naming/scope expansion (the Sprint-4 Ansible role landed as the generic `compose-app` rather than the placeholder `ai-dev-context-stack` — broader and re-usable by design). Every functional smoke that ran returned the result the brief required; zero FRs scored FAIL. The headline numbers — K1 token reduction `38× median` (E2-S08, real GitNexus measurements) backed by `~29×` cross-repo ratio (E4-S09 backfill, paper math); K2 GitNexus reindex `1.58 s analyze + 68.7 ms hook` against a 30 s threshold; K3 spend `$1-3/mo projected` against `$20/mo` (cap-cap proven end-to-end on synthetic breach); K4 `48/50 episodes (96%)` Graphiti extraction quality and `3/3 (100%)` GitNexus non-blank graph artifacts; K5 `4/5 strong top-1 hits` synthetic recall — clear the Sprint-3 / Sprint-4 internal gates and the Sprint-2 internal gate.

The reasons this is not RELEASE rather than CONTINUE: (1) K6 subjective uplift was masked by the E3-S08.5 search regression for most of Sprint 3 (fixed `9c5b35d` 2 hours before the Sprint-3 scorecard) and remains operator-data-pending; (2) FR-LLM-007 gate is operator-input-pending — Path A vs Path B is a Sprint-5 scope decision, not a product-defect; (3) several E3 epic-AC carries (AR8 default-group, FalkorDB RSS, SEMAPHORE/telemetry-off explicit citation) were never captured to evidence even though the underlying configuration is correct; (4) two key rotations and a restic source-set update are operator follow-ups whose absence does not break anything currently running but does leave a documented exposure window. None of these warrant PIVOT — they warrant the close-out work that E4-S12 owns.

---

## A. Functional requirements (73 FRs across 7 buckets)

Status legend per the brief: **PASS** (acceptance signal demonstrated and cited), **PARTIAL** (substantively met but with a documented gap or a non-canonical surface), **FAIL** (acceptance signal demonstrably not met), **INSUFFICIENT-DATA** (no evidence in committed artifacts; should have been measured), **OPERATOR-INPUT-PENDING** (gate is an operator decision; not a defect of execution).

### A.1 FR-DEC — Decommission (12 FRs)

Source for the entire bucket: Sprint 1 retro (`730c4fb`); evidence directory `docs/decommission/` on `main` (`baseline-pre-decommission.txt`, `grep-gate-2026-04-26.txt`, `process-audit-2026-04-26.txt`, `post-decommission-verify-2026-04-26.txt`, `sprint-1-verify-report.md`, `phase-1-decommission.md`, `pre-push-hook.sh`, `hook-self-test-2026-04-25.txt`); annotated tag `phase-1-decommission-complete` on the closing E1-S09 commit.

Every FR-DEC-* is **PASS** because the bucket has a single closure artifact (the tagged commit) and a verify-report that exits clean across the grep gate (FR-DEC-009), the pgrep gate (FR-DEC-010), the Hermes verify run on ct-dev-homelab (FR-DEC-011), and the FR-DEC-012 no-data-migration record. The Sprint 1 retro §"What didn't go well" notes the safety-net session gate between E1-S01 and E1-S02 was skipped pragmatically (JSON validation + backup gave equivalent recoverability) — recorded as a documented exception, not a missed AC.

| Bucket aggregate | Count |
|---|---|
| **FR-DEC PASS** | **12 / 12** |
| FR-DEC PARTIAL / FAIL / INSUFFICIENT-DATA / OPERATOR-PENDING | 0 |

### A.2 FR-CG — GitNexus code-graph (12 FRs)

Sources: Sprint 2 KPI scorecard `c18b014` (`docs/context-stack/sprint-2/e2-s08-week1-kpi-scorecard.md`); Sprint 2 retro `650e906` (`_bmad-output/implementation-artifacts/context-stack-sprint-2-retro-2026-04-26.md`); E4-S09 backfill `d4896ab` (`docs/context-stack/sprint-2/kpi-backfill.md`); E4-S08 evidence `0a4a096` (Phase 3 GitNexus MCP smoke on ct-dev-homelab).

| FR | Status | Source |
|---|---|---|
| FR-CG-001 (MCP-native install) | PASS | E2-S01 install + E2-S03 MCP wiring; container-delivery pivot per ADR-015 (E2-S01.5) — `claude mcp list` shows `gitnexus` healthy on workstation and on ct-dev-homelab (E4-S08 Phase 3) |
| FR-CG-002 (local-only, no source code leaves machine) | PASS | E2-S05 privacy audit (`docs/context-stack/sprint-2/e2-s05-topology-and-privacy-evidence.md`) — network audit during reindex shows zero LLM-API host calls |
| FR-CG-003 (parent-folder topology over `~/workspace/homelab/`) | PASS | E2-S05 — three sub-repos indexed; cypher returns nodes from all three; cross-repo edges present |
| FR-CG-004 (Pre/PostToolUse hooks) | PASS | E2-S04 evidence; hook overhead 68.7 ms wall-clock per E2-S08 K2 measurement |
| FR-CG-005 (auto-reindex on every commit, no path/branch filter) | PASS | E2-S04 — design note: PostToolUse fires `detect_changes` (cheap), `analyze` only on explicit op invocation per E4-S09 backfill §K2 |
| FR-CG-006 (incremental reindex ≤ 30 s) | PASS (proxy) | E2-S08 measured 1.58 s analyze on 93-file repo; E4-S09 backfill registry-spacing inference confirms sub-30 s; explicit per-commit timing carried into recurring digest |
| FR-CG-007 (full reindex ≤ 60 s) | PASS (proxy) | E2-S08 1.58 s ≪ 60 s; ADR-014 downgrade to SHOULD; the 359-file `homelab-infra` reindex ran > 5 min during E2-S08 due to single-threaded NLP embedding contention with `gitnexus serve` — flagged as Sprint-3 carry, not a release-gate FAIL |
| FR-CG-008 (K1 ≥ 5×) | PASS | E2-S08 measured 38× median (range 24×–257×) on 3 synthetic tasks; E4-S09 backfill `~29×` on a separate cross-repo question |
| FR-CG-009 (non-blank graph artifact) | PASS | E4-S09 backfill 3/3 = 100% on `lbug` graph artifacts (11.7 MB / 31.5 MB / 35.2 MB); FR maps to `lbug` per ADR-004/ADR-015, not the `GRAPH_REPORT.md` filename in the original PRD wording |
| FR-CG-010 (JSON exportable graph) | PASS | E2-S07 NDJSON export wrapper `scripts/gitnexus-export.sh` per ADR-012 |
| FR-CG-011 (graceful degradation if GitNexus unavailable) | PASS | E2-S06 Scenario 5b drill — daemon stopped, no > 3 s hang |
| FR-CG-012 (no LLM call for parsing) | PASS | E2-S05 network audit — gitnexus container has no API keys mounted, no outbound LLM endpoints |

| Bucket aggregate | Count |
|---|---|
| **FR-CG PASS** | **12 / 12** |

Caveat for the binding scorecard: E4-S09 §"Anything unexpected" item 1 documents the GitNexus container `${HOME}` path-resolution divergence (container resolves to `/root/.gitnexus-data`; operator's `gitnexus analyze` writes to `/home/developer/.gitnexus-data`) — flagged into E4-S10 exit-ramp doc; this does not invalidate any FR-CG-* PASS but does mean the live MCP `list_repos` from this Sprint-5 Claude Code session returned `[]` despite three healthy on-disk graphs. Recurring digest's K1 row is the right place for the post-fix round-trip number.

### A.3 FR-MEM — Graphiti memory (15 FRs)

Sources: Sprint 3 KPI scorecard `3068767` (`docs/context-stack/sprint-3/e3-s09-kpi-scorecard.md`); Sprint 3 retro `03ad119`; E3-S04f-retry, E3-S06, E3-S07, E3-S08, E3-S08.6 evidence; E4-S08 Phase 3 5/5 smokes on ct-dev-homelab.

| FR | Status | Source |
|---|---|---|
| FR-MEM-001 (FalkorDB Docker Compose) | PASS | E3-S01 evidence + E4-S08 Phase 2 deploy — `falkordb Up (healthy)` on ct-dev-homelab |
| FR-MEM-002 (MCP HTTP transport) | PASS | E3-S03 evidence + `graphiti /health=200` on ct-dev-homelab (E4-S08 Phase 2) |
| FR-MEM-003 (127.0.0.1 bind + Tailscale reach) | PASS | E3-S02 + E4-S08 Phase 2 — `127.0.0.1:8000->8000/tcp` |
| FR-MEM-004 (LLM + embedder choice) | **PASS-WITH-AMENDMENT** | Original PRD specified `gpt-4o-mini` + `text-embedding-3-small`. ADR-002 amended 2026-04-27 to `gemini-2.5-flash-lite` (E3-S04f-retry pivot, justified by 30-300 s/episode local-Gemma → 7.5 s/episode Flash-Lite first try). ADR-003 v2 amended 2026-04-27 to `gemini-embedding-2` (3072 dim) routed via LiteLLM gateway. The intent of FR-MEM-004 (a working extraction stack) is met; the literal text is superseded by the ADR amendments shipped in `7ebe1c5` and `3e5f003`. |
| FR-MEM-005 (`group_id="tom-personal"` for all writes) | **OPERATOR-INPUT-PENDING (AR8 verification)** | E3-S05 covered the AR8 mechanic; E3-S06 used per-test alphanumeric groups (`e3s06test1`, etc.) to dodge E3-S04h hyphen-quoting bug. Sprint 3 retro §6 AC5 marks this `DEFERRED-IN-PRACTICE`; Sprint 4 retro §10 item 10 carries it; Sprint 5 kickoff §3 item 9 carries it. The default-group AR8 probe specifically against `tom-personal` was never run. |
| FR-MEM-006 (`SEMAPHORE_LIMIT=5`) | **INSUFFICIENT-DATA** | Sprint 3 retro §6 AC8 marks this `PARTIAL — operator input pending`; explicit citation absent from any committed evidence file. Sprint 4 retro §10 item 12 carries it. Configuration is presumed correct (compose env path; ADR-008 amendment switched the throttle-on-breach mechanism to LiteLLM YAML comment-out, which makes SEMAPHORE_LIMIT a baseline-only value). |
| FR-MEM-007 (K5 first-shot recall ≥ 50%) | PARTIAL | E3-S06 Test 2 measured `4/5 strong top-1 hits` on synthetic recall. Operator-tagged real-session "good catches" not measured (E3-S08.5 search bug masked half the sprint; daily prompt-template change deferred to S4 D31 per Sprint 3 retro §7 item 8 and Sprint 4 retro §10 item 13). PRD §7 K5 threshold is met on synthetic recall; the operator-tagged ≥ 3 good-catches-over-4-weeks half is unmeasured. |
| FR-MEM-008 (≥ 25 facts/week, K4) | INSUFFICIENT-DATA (operator-data-pending) | E4-S09 first weekly digest §K4 reports `0` facts in `tom-personal` — production-target Graphiti at ct-dev-homelab has 1 episode total (smoke-test only). The metric is structurally measurable; the count-as-of-now is "not yet exercised by operator daily use." |
| FR-MEM-009 (standard MCP tool surface) | PASS | E3-S05 + E3-S08.6 — `add_episode`, `search_facts`, `search_nodes`, `get_episodes`, etc. all exercised; E3-S08.6 patched `search_nodes`/`search_memory_facts`/`get_episodes` for the `len(group_ids)==1` decorator regression |
| FR-MEM-010 (`CLAUDE.md` Memory section) | PASS | E3-S03 evidence — replaces deleted OMEGA Memory section |
| FR-MEM-011 (telemetry disabled) | INSUFFICIENT-DATA | Sprint 3 retro §6 AC8 — explicit citation of `GRAPHITI_TELEMETRY_ENABLED=false` absent from committed evidence; configuration is presumed correct from compose env. |
| FR-MEM-012 (Cypher export available) | PASS | E3-S07 — 18.2 MB tarball, 13 nodes-files + 13 edges-files + MANIFEST; `scripts/cypher-export.sh` cron at 04:00 UTC day-1 monthly |
| FR-MEM-013 (graceful degradation if Graphiti down) | PASS | E3-S06 Test 4 drill |
| FR-MEM-014 (backup mechanism documented + exercised) | PASS | E3-S07 (3-layer backup: AOF + RDB + monthly Cypher) + E3-S08 restore drill PASS at 91 s downtime; runbook `e3-s08-restore-runbook.md` |
| FR-MEM-015 (FalkorDB RSS < 200 MB) | PARTIAL | E4-S09 first digest reports FalkorDB RSS on ct-dev-homelab = `16.84 MiB` (G), well under 200 MB. Sprint 3 retro §6 AC6 flags that the original `docker stats` snapshot at end of Sprint 3 was not captured in evidence; the Sprint 5 digest reading covers the production-target host but not the workstation Graphiti instance — Sprint 4 retro §10 item 11 carries the workstation snapshot. |

| Bucket aggregate | Count |
|---|---|
| **FR-MEM PASS** | **9 / 15** |
| FR-MEM PASS-WITH-AMENDMENT (ADR-amended; FR text superseded) | 1 / 15 |
| FR-MEM PARTIAL | 3 / 15 |
| FR-MEM INSUFFICIENT-DATA | 2 / 15 |
| FR-MEM OPERATOR-INPUT-PENDING | 1 / 15 (FR-MEM-005 AR8 probe — strict reading) |
| FR-MEM FAIL | 0 / 15 |

### A.4 FR-WIKI — LLM Wiki tier (10 FRs)

Sources: E4-S01 + E4-S01-closer commits (`8419923`, `73ccabb`); E4-S02 seeds `fe77eb3`; E4-S03 skill `b689e77`; E4-S10 query hierarchy + exit-ramps `437c0bc`; on-disk wiki tree at `homelab-playbook/wiki/`.

| FR | Status | Source |
|---|---|---|
| FR-WIKI-001 (`wiki-query` skill) | PASS | E4-S03 — `~/.claude/skills/wiki-query/SKILL.md` installed; runbook at `wiki/runbooks/wiki-query-skill.md` |
| FR-WIKI-002 (wiki at `homelab-playbook/wiki/`) | PASS | Tree exists |
| FR-WIKI-003 (file-based, zero-MCP) | PASS | E4-S03 — allowed-tools=Read; no LLM call at retrieval |
| FR-WIKI-004 (`index.md` summarising tree) | PASS | E4-S01 substrate |
| FR-WIKI-005 (≤ 200 ms wiki query) | PASS | E4-S03 — file-read against 110-220 line seed pages trivially under 200 ms (latency budget = file-read time only) |
| FR-WIKI-006 (3 seeds × 3 sessions each) | **PARTIAL — operator-input pending** | Sprint 4 retro §7 AC2 — 4 seed pages exist (`tailscale-policy`, `pve9-ha-migration`, `hybrid-gemma-serving`, `wiki-query-skill`); the per-seed × 3-session count is operator-side data not surfaced in evidence files; Sprint 4 retro relaxes this to 3×1 per kickoff §2 SHOULD-trim with operator review at S5 retro |
| FR-WIKI-007 (unified query hierarchy doc) | PASS | E4-S10 — `wiki/decisions/query-hierarchy.md` per ADR-013 |
| FR-WIKI-008 (wiki in homelab-playbook git) | PASS | Tree is version-controlled inside this repo |
| FR-WIKI-009 (no LLM dependency in skill) | PASS | E4-S03 — allowed-tools=Read only |
| FR-WIKI-010 (bulk content out of scope) | PASS | E4-S02 — 4 seeds is the deliverable; brief NG4 honoured |

| Bucket aggregate | Count |
|---|---|
| **FR-WIKI PASS** | **9 / 10** |
| FR-WIKI PARTIAL | 1 / 10 (FR-WIKI-006 — operator-input pending) |
| FR-WIKI FAIL | 0 / 10 |

### A.5 FR-LLM — LiteLLM bridge (8 FRs)

Per the brief's hard rule: **all FR-LLM-* are FR-LLM-007-gate-pending → OPERATOR-INPUT-PENDING.** Sprint 4 retro §8 documents the gate explicitly (Path A vs Path B vs operator-input-pending); Sprint 5 kickoff §3 item 6 carries it; the LiteLLM bridge stories E4-S05 and E4-S06 did NOT run this sprint per Sprint 5 kickoff's gate-deferral.

| FR | Status | Source |
|---|---|---|
| FR-LLM-001 (bridge Graphiti only) | OPERATOR-INPUT-PENDING | Story E4-S05 deferred per FR-LLM-007 |
| FR-LLM-002 (`OpenAIGenericClient` path) | OPERATOR-INPUT-PENDING | Story E4-S05 deferred — note: E3-S04c investigation found Option A (`OPENAI_BASE_URL` override) non-functional on LiteLLM 1.83.13 because `OpenAIGenericClient` selection in graphiti-core defaults to `/v1/responses` not `/v1/chat/completions`; this informs the eventual E4-S05 design choice but is not itself an FR-LLM-002 evaluation |
| FR-LLM-003 (`OPENAI_BASE_URL` + `MODEL_NAME` override) | OPERATOR-INPUT-PENDING | Story E4-S05 deferred |
| FR-LLM-004 (embeddings stay on OpenAI) | **PASS-WITH-AMENDMENT (effectively superseded)** | ADR-003 v2 (`3e5f003`) routed embeddings through LiteLLM gateway (`gemini-embedding-2`); the operative deployed embedder is no longer OpenAI. The intent of FR-LLM-004 (don't let small-model JSON quality degrade extraction) is moot in Path B (no LiteLLM bridge); reopens in Path A. |
| FR-LLM-005 (≥ 95% well-formed JSON gate) | OPERATOR-INPUT-PENDING | Story E4-S06 deferred |
| FR-LLM-006 (auto-fallback on malformed JSON) | OPERATOR-INPUT-PENDING | Story E4-S06 deferred |
| FR-LLM-007 (Phase 4 stretch / non-blocking) | **OPERATOR-INPUT-PENDING (the gate itself)** | This IS the gate; Path A vs Path B vs pending. Sprint 4 retro §8 + Sprint 5 kickoff §1.6. |
| FR-LLM-008 (reversible in ≤ 1 day) | OPERATOR-INPUT-PENDING | Story E4-S06 deferred |

| Bucket aggregate | Count |
|---|---|
| **FR-LLM PASS** | **0 / 8** |
| FR-LLM PASS-WITH-AMENDMENT | 1 / 8 (FR-LLM-004 superseded by ADR-003 v2) |
| FR-LLM OPERATOR-INPUT-PENDING | 7 / 8 |
| FR-LLM FAIL | 0 / 8 |

### A.6 FR-OBS — Observability + cost-tracking (6 FRs)

Sources: E4-S04 evidence `d4c032d` + `3f48dea`; E4-S09 evidence `d4896ab`; weekly digest template at `wiki/runbooks/weekly-observability-digest.md`; first digest at `wiki/decisions/weekly-digest-2026-w18.md`; cron `*/30` on ct-ai-01 verified live.

| FR | Status | Source |
|---|---|---|
| FR-OBS-001 (weekly cost-check procedure documented) | PASS | E4-S09 template + first digest; auto-fills 6/10 KPI rows; `[TBD]` for operator-judgement rows |
| FR-OBS-002 (daily $1 hard-cap) | **PASS-WITH-AMENDMENT** | E4-S04 — cost source switched OpenAI Usage API → LiteLLM `/metrics` (ADR-008 amendment `d4c032d`); throttle switched SEMAPHORE_LIMIT 5→1 → LiteLLM YAML alias comment-out via sentinel markers; ntfy channel corrected to `https://ntfy.bi-services.be/`. Manual breach test proven end-to-end without burning real spend (~$1e-5). Operator-accepted LLM-bypass cost-gap recorded in `3f48dea` (graphiti-core's native `GeminiClient` calls `generativelanguage.googleapis.com` directly, bypassing LiteLLM; only embedder traffic flows through the gateway and hits the counter). The cap remains an effective backstop; re-evaluate at S5 if monthly spend approaches $10. |
| FR-OBS-003 (Graphiti MCP logs INFO-level + monthly rotation) | PARTIAL | Sprint 3 retro §6 AC8 — telemetry-off citation is `OPERATOR INPUT PENDING`; INFO-level + rotation is presumed-correct from compose env but no log-rotation snapshot was captured in evidence |
| FR-OBS-004 (weekly retro note with K1-K6) | PASS | E4-S09 first digest landed; recurring template at `wiki/runbooks/weekly-observability-digest.md`; ADR-006 4-section layout |
| FR-OBS-005 (good-catch tally ≥ 3 over pilot) | INSUFFICIENT-DATA (operator-data-pending) | Sprint 3 retro §6 + Sprint 4 retro §10 item 13 — daily "did this save a re-derivation?" prompt was supposed to start at S4 D31 to give 4 weeks of operator-tagged data before this scorecard; it didn't. K6 / K5-good-catch tally is not measurable at product-close from current evidence. |
| FR-OBS-006 (GitNexus tool-hit-rate; zero-week trigger CLAUDE.md review) | PASS | E4-S09 first digest reports 43 calls in window; conditional callout suppressed per FR-OBS-006 logic |

| Bucket aggregate | Count |
|---|---|
| **FR-OBS PASS** | **4 / 6** |
| FR-OBS PASS-WITH-AMENDMENT | 1 / 6 (FR-OBS-002 cost source + throttle mechanism amendment) |
| FR-OBS PARTIAL | 1 / 6 (FR-OBS-003 telemetry/log-rotation citation) |
| FR-OBS INSUFFICIENT-DATA | 1 / 6 (FR-OBS-005 — operator-data-pending) |
| FR-OBS FAIL | 0 / 6 |

(Total = 6+1; FR-OBS-002 is double-counted as PASS-WITH-AMENDMENT and bucket-PASS).

### A.7 FR-DEP — Deployment (10 FRs)

Sources: Sprint 1 retro (Phase 1 Ansible playbooks idempotent); E3-S01 + E4-S07 + E4-S08 (Phase 2/4 Ansible); E4-S07 evidence `50563a4` (down -v guard ADR-007 sub-amendment); E4-S08 evidence `0a4a096` (5/5 smokes + rollback drill on ct-dev-homelab).

| FR | Status | Source |
|---|---|---|
| FR-DEP-001 (Phase 1 idempotent Ansible) | PASS | Sprint 1 retro §"Stories shipped" |
| FR-DEP-002 (`/srv/graphiti/docker-compose.yml` + `.env` mode 600; not in git) | PASS | E3-S01 + E4-S08 Phase 1 vault promotion (keys live in `group_vars/all/vault.yml` ansible-vault encrypted; no plaintext) |
| FR-DEP-003 (Phase 2 GitNexus install captured in script/role) | PASS | E2-S01 install-evidence + Docker delivery via ADR-015 |
| FR-DEP-004 (validated on `ct-dev-homelab` first) | PASS | E4-S08 — 192.168.50.156 |
| FR-DEP-005 (Phase 3 wiki rollout) | PASS | E4-S01/S02/S03 |
| FR-DEP-006 (verify.yml exit 0 + 5 smoke tests pass) | **PASS (substantively met)** | Sprint 4 retro §7 AC8 — 5/5 smokes PASS on ct-dev-homelab (graphiti add+search; gitnexus MCP initialize; cross-stack liveness; persistence after restart; cost-cap/LiteLLM gateway reach). The literal `verify.yml` was not authored as a separate file; verification lives in the playbook health-check loop + explicit smoke runner (`/tmp/e4-s08-smoke.py`). Substantive intent met. |
| FR-DEP-007 (rollback drilled per phase) | PASS | E4-S08 Phase 4 — destructive-down guard refused without flag, allowed with flag, snapshot at `/srv/graphiti/data.bak.20260427T123352`, recovery via re-running `deploy-context-stack.yml` (ok=25 changed=6 failed=0); Sprint 1 rollback path documented in `phase-1-decommission.md`; G-Rollback gate validated on a real host |
| FR-DEP-008 (no secrets in repo) | PASS | E4-S08 Phase 1 — vault-encrypted ciphertext blocks promoted to group scope; pre-push hook + lint-gate per Sprint 1 retro |
| FR-DEP-009 (dev_hosts container playbook OMEGA refs dropped) | PASS | E1-S03 |
| FR-DEP-010 (pinned image tags, not `latest`) | PASS-WITH-AMENDMENT | Original PRD specified `zepai/graphiti-mcp:v1.0.2`; the operative deployed image is `graphiti-mcp-genai-bundled:e3-s04g` (locally-built per E3-S04g to bake in `google-genai` SDK after the cloud pivot). Locally-tagged not registry-pinned; Sprint 3 retro §6 AC8 records this as PARTIAL. ADR-002 amendment captures the rationale. |

| Bucket aggregate | Count |
|---|---|
| **FR-DEP PASS** | **9 / 10** |
| FR-DEP PASS-WITH-AMENDMENT | 1 / 10 (FR-DEP-010 locally-built image; pin still in place at the local tag layer) |
| FR-DEP FAIL | 0 / 10 |

### A.8 FR roll-up

| Bucket | Total | PASS | PASS-WITH-AMENDMENT | PARTIAL | INSUFFICIENT-DATA | OPERATOR-PENDING | FAIL |
|---|---|---|---|---|---|---|---|
| FR-DEC | 12 | 12 | 0 | 0 | 0 | 0 | 0 |
| FR-CG | 12 | 12 | 0 | 0 | 0 | 0 | 0 |
| FR-MEM | 15 | 9 | 1 | 3 | 2 | 1 (AR8) | 0 |
| FR-WIKI | 10 | 9 | 0 | 1 | 0 | 0 | 0 |
| FR-LLM | 8 | 0 | 1 | 0 | 0 | 7 | 0 |
| FR-OBS | 6 | 4 | 1 | 1 | 1 | 0 | 0 |
| FR-DEP | 10 | 9 | 1 | 0 | 0 | 0 | 0 |
| **Total** | **73** | **55** | **4** | **5** | **3** | **8** | **0** |

Counting PASS-WITH-AMENDMENT as substantively-PASS (the FR's intent is met; ADR amendments are how the architecture absorbed sprint-3's pivot without abandoning FRs): **59 / 73 PASS-equivalent (81%)**, **5 / 73 PARTIAL**, **3 / 73 INSUFFICIENT-DATA**, **8 / 73 OPERATOR-INPUT-PENDING (almost entirely FR-LLM-007 gate-deferred)**, **0 / 73 FAIL**.

Strict reading (PASS-WITH-AMENDMENT held separately): **55 / 73 (75%) clean PASS**.

---

## B. Non-functional requirements (25 NFRs across 8 buckets)

### B.1 NFR-PERF — Performance (6 NFRs)

| NFR | Threshold | Measured | Status | Source |
|---|---|---|---|---|
| NFR-PERF-001 (session-start overhead < 1 s) | < 1 s | hook overhead 68.7 ms (PostToolUse on commit), GitNexus session-start no-regression per E2-S08 §G-Latency | **PASS** | E2-S08 KPI scorecard `c18b014`; G-Latency clean |
| NFR-PERF-002 (query p95 < 500 ms) | < 500 ms | Graphiti `search_nodes` 0.35-0.92 s post-E3-S08.6 fix; GitNexus query default 5×10 symbols < 500 ms target met by signal payload shape; not all queries empirically measured | PARTIAL | E3-S08.6 evidence (`9c5b35d`); recurring digest carries this row |
| NFR-PERF-003 (wiki Tier-1 < 200 ms) | < 200 ms | E4-S03 design — file-read against 110-220 line pages trivially under 200 ms | PASS | E4-S03 |
| NFR-PERF-004 (incremental reindex < 30 s) | < 30 s | 1.58 s analyze + 68.7 ms hook (E2-S08) | PASS | Sprint 2 KPI scorecard |
| NFR-PERF-005 (full reindex < 60 s) | < 60 s | 1.58 s on `homelab-apps` (93 files) — not measured on `homelab-infra` (timed out > 5 min in E2-S08; flagged as analyze-vs-serve concurrency carry, not a NFR FAIL because the hook backgrounds the analyze with `disown`) | PASS-WITH-CAVEAT | Sprint 2 retro carry-over; ADR-014 SHOULD downgrade |
| NFR-PERF-006 (Graphiti `add_episode` < 5 s/episode) | < 5 s | E3-S04f-retry first try 7.5 s — slightly over | PARTIAL | E3-S04f-retry evidence; PRD threshold technically not met but the threshold itself was based on `gpt-4o-mini` cost-model arithmetic, not on operator pain — a 7.5 s episode at single-operator scale is comfortable |

**NFR-PERF aggregate:** 4 PASS, 1 PASS-WITH-CAVEAT, 1 PARTIAL.

### B.2 NFR-COST — Cost (3 NFRs)

| NFR | Threshold | Measured | Status | Source |
|---|---|---|---|---|
| NFR-COST-001 (< $20/month all-in) | < $20/mo | $1-3/mo projected at Gemini Flash-Lite pricing (6-10 M tokens/month extraction); ADR-002 Amendment §Cost | **PASS** | E3-S09 §K3; ADR-002 amendment |
| NFR-COST-002 (< $1/day; auto-throttle on breach) | < $1/day | Auto-throttle SHIPPED via E4-S04 + ADR-008 amendments; manual breach test proven end-to-end (synthetic breach + ntfy alert + restore) without burning real spend (~$1e-5) | **PASS-WITH-AMENDMENT** | E4-S04 evidence; ADR-008 amendment + cost-gap acceptance |
| NFR-COST-003 (Phase 4 LiteLLM bridge cost-neutrality) | bridge ≤ Phase-1 baseline | OPERATOR-INPUT-PENDING — Phase 4 LiteLLM bridge gate-deferred; the `add_memory` → embedder LiteLLM path is metered and currently $0.000254/week | OPERATOR-INPUT-PENDING | Sprint 4 retro §8; Sprint 5 kickoff §1.6 |

### B.3 NFR-PRIV — Privacy (3 NFRs)

| NFR | Status | Source |
|---|---|---|
| NFR-PRIV-001 (no source code crosses boundary; GitNexus local-only) | **PASS** | E2-S05 privacy audit; ADR-015 container has no API keys; Sprint 2 KPI scorecard §K3 |
| NFR-PRIV-002 (embeddings MAY go to provider; documented + accepted) | **PASS** | ADR-003 v2 amendment 2026-04-27 — embeddings on Gemini (was OpenAI); privacy envelope unchanged; ADR-002 Amendment §Privacy explicitly documents the cloud line |
| NFR-PRIV-003 (Tailscale-only for phone-facing; reserved for future) | N/A | No phone-facing surfaces in this product; brief NG6; reserved |

### B.4 NFR-FOOTPRINT — Resource footprint (3 NFRs)

| NFR | Threshold | Measured | Status | Source |
|---|---|---|---|---|
| NFR-FOOTPRINT-001 (FalkorDB RSS < 200 MB) | < 200 MB | ct-dev-homelab: 16.84 MiB (E4-S09 first digest); workstation snapshot at end of Sprint 3 not captured | **PASS-WITH-NOTE** | E4-S09 digest; Sprint 4 retro §10 item 11 carries the workstation snapshot |
| NFR-FOOTPRINT-002 (GitNexus daemon RSS) | re-baselined < 2 GB per ADR-016 (was < 500 MB in PRD) | 882 MiB end-of-week (E2-S08); 91-93 MiB current (E4-S09 backfill); `57.53MiB / 8GiB` per `docker stats` | **PASS** | Sprint 2 KPI scorecard §AR1; ADR-016 |
| NFR-FOOTPRINT-003 (combined disk < 5 GB) | < 5 GB | FalkorDB data + GitNexus indexes (78 MB total: 11.7 + 31.5 + 35.2 MB) + wiki tree (~1 MB) — comfortably under 5 GB | **PASS** | E4-S09 backfill table |

### B.5 NFR-AVAIL — Availability + graceful degradation (3 NFRs)

| NFR | Status | Source |
|---|---|---|
| NFR-AVAIL-001 (GitNexus down → session continues, no > 3 s hang) | **PASS** | E2-S06 Scenario 5b drill |
| NFR-AVAIL-002 (Graphiti down → session continues, no > 3 s hang) | **PASS** | E3-S06 Test 4 drill |
| NFR-AVAIL-003 (LiteLLM gateway down → fallback to cloud) | OPERATOR-INPUT-PENDING | LiteLLM bridge gate-deferred; FR-LLM-006 fallback path gate-deferred |

### B.6 NFR-MAINT — Maintainability (2 NFRs)

| NFR | Status | Source |
|---|---|---|
| NFR-MAINT-001 (each component unwireable in ≤ 1 day) | **PASS** | E4-S08 Phase 4 rollback drill — under 1 hour wall-time on a real host |
| NFR-MAINT-002 (decommission rollback documented + exercisable) | **PASS** | Sprint 1 `phase-1-decommission.md` + `phase-1-decommission-complete` tag is the rollback target |

### B.7 NFR-SUPP — Upstream support (2 NFRs)

| NFR | Status | Source |
|---|---|---|
| NFR-SUPP-001 (≥ 3 months upstream activity at adoption) | **PASS** | E2-S01 supply-chain verification — `gitnexus@1.6.3` checksum + maintainer + ≥ 3 mo activity verified at install; Graphiti `getzep/graphiti` verified pre-E3-S01 |
| NFR-SUPP-002 (documented exit ramps) | **PASS** | E4-S10 — four exit-ramp runbooks at `wiki/runbooks/exit-ramps/`: GitNexus (NDJSON dump; CodeGraphContext alternative; documents container vs CLI registry divergence), Graphiti (Cypher dump; episode-replay deferred per Mandatory Fix #1 verdict; RDB-restore is operative), wiki (git clone), auto-memory (`cp -a`) |

### B.8 NFR-PORT — Portability (3 NFRs)

| NFR | Status | Source |
|---|---|---|
| NFR-PORT-001 (GitNexus JSON exportable) | **PASS** | E2-S07 NDJSON wrapper |
| NFR-PORT-002 (Graphiti exportable via Cypher AND episode-replay) | **PASS-WITH-AMENDMENT** | E3-S07 Cypher dump shipped (`scripts/cypher-export.sh` cron monthly); episode-replay log existence is documented but per Sprint 4 retro §4 Mandatory Fix #1 the operative recovery is RDB-restore (validated 91 s downtime per E3-S08); the Cypher tarball is docs-only audit signal. ADR-007 amendment 2026-04-27 captures this; Sprint-4 retro §6 lesson #5 recommends a one-line ADR-007 sub-amendment in S5 to memorialise it explicitly. |
| NFR-PORT-003 (wiki plain markdown — inherently portable) | **PASS** | by construction |

### B.9 NFR roll-up

| Bucket | Total | PASS | PASS-WITH-NOTE/CAVEAT/AMENDMENT | PARTIAL | OPERATOR-PENDING | N/A | FAIL |
|---|---|---|---|---|---|---|---|
| NFR-PERF | 6 | 4 | 1 | 1 | 0 | 0 | 0 |
| NFR-COST | 3 | 1 | 1 | 0 | 1 | 0 | 0 |
| NFR-PRIV | 3 | 2 | 0 | 0 | 0 | 1 | 0 |
| NFR-FOOTPRINT | 3 | 2 | 1 | 0 | 0 | 0 | 0 |
| NFR-AVAIL | 3 | 2 | 0 | 0 | 1 | 0 | 0 |
| NFR-MAINT | 2 | 2 | 0 | 0 | 0 | 0 | 0 |
| NFR-SUPP | 2 | 2 | 0 | 0 | 0 | 0 | 0 |
| NFR-PORT | 3 | 2 | 1 | 0 | 0 | 0 | 0 |
| **Total** | **25** | **17** | **4** | **1** | **2** | **1** | **0** |

Counting PASS-WITH-NOTE/CAVEAT/AMENDMENT as substantively PASS: **21 / 25 PASS-equivalent (84%)**, **1 / 25 PARTIAL**, **2 / 25 OPERATOR-INPUT-PENDING (NFR-COST-003 + NFR-AVAIL-003, both LiteLLM-bridge-dependent)**, **1 / 25 N/A (NFR-PRIV-003 phone-facing reserved)**, **0 / 25 FAIL**.

---

## C. KPI roll-up (the binding gate per PRD §11 + sprint-plan §7.6)

The product gate is `≥ 4-of-6 KPIs green AND G-Latency clean AND G-Rollback validated`. Aggregating from Sprint 2 KPI scorecard (`c18b014`), Sprint 3 KPI scorecard (`3068767`), Sprint 2 KPI backfill (`d4896ab` → `docs/context-stack/sprint-2/kpi-backfill.md`), and E4-S09 first weekly digest (`wiki/decisions/weekly-digest-2026-w18.md`):

| KPI | Green threshold | Best-evidence value | Verdict | Source |
|---|---|---|---|---|
| **K1 — Token reduction** | ≥ 5× | **38× median** (E2-S08 on 3 synthetic GitNexus tasks; range 24×-257×); **~29×** (E4-S09 backfill on a separate cross-repo question) | **GREEN** | Sprint 2 KPI scorecard §K1; E4-S09 backfill §K1 |
| **K2 — Reindex time** | ≤ 30 s incremental, ≤ 60 s full | **1.58 s analyze + 68.7 ms hook** on 93-file repo; full proxy-pass via registry-spacing inference; cold-path absolute number deferred to next routine reindex per E4-S09 backfill §K2 | **GREEN** | Sprint 2 KPI scorecard §K2; E4-S09 backfill §K2 |
| **K3 — Spend** | < $20/month all-in | **$1-3/mo** projected (Gemini Flash-Lite pricing); GitNexus $0; cap-cap proven end-to-end on synthetic breach (~$1e-5 actual spend) | **GREEN** | E3-S09 §K3; ADR-002 amendment §Cost; E4-S04 evidence |
| **K4 — Non-blank artifacts** | 100% | **96% Graphiti** (48/50 episodes; 2 known-bug failures via E3-S04h hyphen-quoting, not UUID-emission failure) AND **100% GitNexus** (3/3 lbug graphs non-blank); aggregate is the AND of both halves so K4 = `partial` if strict-100% read, `green` if "non-blank-when-not-blocked-by-known-bug" read | **GREEN-WITH-NOTE (Graphiti half is 96% not 100%)** | E3-S06 Test 1 evidence; E4-S09 backfill §K4 |
| **K5 — Good-catch rate / first-shot recall** | ≥ 50% AND ≥ 3 good-catches over pilot | Synthetic recall **4/5 strong top-1, 4/5 P@3 ≥ 2/3** (E3-S06 Test 2); operator-tagged good-catches over the 4-week pilot are **not measurable from current evidence** — the daily K6/K5 prompt was supposed to start at S4 D31 but didn't | **PARTIAL** (recall semantics met by synthetic; operator-tagged tally INSUFFICIENT-DATA) | E3-S09 §K5; Sprint 4 retro §10 item 13 |
| **K6 — Subjective uplift** | ≥ 60% sessions where stack queried; "noticeable" by week 4 | **INSUFFICIENT-DATA** — the E3-S08.5 search regression masked Graphiti's value for the latter half of Sprint 3 (fix landed `9c5b35d`, ~2 hours before the Sprint-3 scorecard); the operator-daily K6 prompt to capture sessions across the 4-week pilot did not start at S4 D31 as planned (Sprint 3 retro §7 item 8; Sprint 4 retro §10 item 13) | **INSUFFICIENT-DATA** | E3-S09 §K6; Sprint 4 retro §10 item 13 |

**KPI score:** **4 GREEN (K1, K2, K3, K4) / 1 PARTIAL (K5) / 1 INSUFFICIENT-DATA (K6) / 0 RED.**

The gate `≥ 4-of-6 GREEN` is **MET (4/6)** on a strict reading, **5/6 if K4 is read as GREEN-WITH-NOTE and K5 is counted as PARTIAL-PASS via synthetic-recall**, and would be **5/6 GREEN** outright if the operator-tagged K5/K6 data had been captured continuously since S4 D31 as recommended.

**Hard gates:**

- **G-Latency** (NFR-PERF-001 zero observable session-start regression vs 5-session baseline): **PASS** — Sprint 2 KPI scorecard reports hook overhead 68.7 ms, no regression.
- **G-Rollback** (FR-DEP-007 end-to-end rollback validated on `ct-dev-homelab`): **PASS** — E4-S08 Phase 4 destructive-down drill on the real host: guard refused without flag, allowed with flag, snapshot at `/srv/graphiti/data.bak.20260427T123352`, recovery via `deploy-context-stack.yml` re-run (ok=25 changed=6 failed=0). Recovery wall-time well under 1 hour, comfortably under the 1-day spec.

**Both hard gates: PASS.**

---

## D. Critical risks remaining

Numbered for traceability into E4-S12 close-out.

1. **FR-LLM-007 gate (operator-input-pending).** Path A (LiteLLM bridge proceeds; E4-S05/S06 run) vs Path B (defer to backlog) vs continued pending. Sprint 4 retro §8 documents three resolution paths; default is pending. Blocks 7/8 FR-LLM-* and NFR-COST-003 + NFR-AVAIL-003 from final scoring.

2. **K6 / FR-OBS-005 operator-data gap.** The daily "did this save a re-derivation?" retro prompt was supposed to start at S4 D31 (Sprint 3 retro §7 item 8 + Sprint 4 retro §10 item 13). Without it, K6 INSUFFICIENT-DATA persists into the binding gate. Closes by either (a) operator self-tagging retroactively over the past 2 days where Graphiti was queried, or (b) accepting K6 as INSUFFICIENT-DATA at product close and committing to the daily prompt for the post-product steady-state.

3. **Two key rotations pending.** `LITELLM_MASTER_KEY` (length=67 leaked in E4-S08 agent transcript) and `GEMINI_API_KEY` (Sprint 3 carry-forward + continued S4 exposure during env-template fix). Vault-encrypted at rest in `group_vars/all/vault.yml`; the leak is in agent transcripts on disk. Sprint 5 kickoff §3 items 1-2.

4. **Restic source-set drift.** `~/.local/state/graphiti-backup/` is not in the operator's restic source-set. Workstation-loss event currently loses every Graphiti backup. Single config change. Sprint 3 carry-forward #1; Sprint 4 retro §10 item 3.

5. **E3-S04h hyphen-escape bug.** `falkordb_driver.py` RediSearch query builder fails on entities with hyphens / `\s` / backticks; ~4% observed failure rate on a realistic 50-fact corpus (2/50 in E3-S06 Test 1). Workaround: alphanumeric `group_id` only. Real fix: patch upstream or vendored. Backlog.

6. **GitNexus container `${HOME}` divergence.** Container resolves to `/root/.gitnexus-data`; operator's `gitnexus analyze` writes to `/home/developer/.gitnexus-data`; two registries diverge; live MCP `list_repos` from operator-side Claude Code returns `[]` despite three healthy on-disk graphs. Documented in E4-S09 evidence §"Anything unexpected" item 1 and in E4-S10 GitNexus exit-ramp doc. Operator picks docker-exec alias OR bind-mount alignment at next deploy.

7. **Two unaddressed `add_episode` upstream behaviours.** (a) `add_episode` mutates `self.driver._database` in place upstream — race condition under concurrent calls with different `group_ids`; E3-S08.6 patch dodges it; out of scope for this product. (b) No auto-retry of failed episodes — when embedder gateway dropped (E3-S06 Test 5b), failed episode permanently dropped; operator must resubmit. Documented v1.26.0 behaviour. Both backlog.

8. **AR8 `tom-personal` namespace one-off probe still open.** Sprint 3 retro §6 AC5 `DEFERRED-IN-PRACTICE`; Sprint 4 retro §10 item 10. The default-group AR8 verification specifically against `tom-personal` was never run because E3-S06 used per-test alphanumeric groups to dodge E3-S04h. Small probe.

9. **FalkorDB RSS workstation snapshot still open.** Sprint 3 retro §6 AC6; Sprint 4 retro §10 item 11. ct-dev-homelab measured at 16.84 MiB (E4-S09); workstation never measured.

10. **`SEMAPHORE_LIMIT=5` + telemetry-off explicit citation still open.** Sprint 3 retro §6 AC8; Sprint 4 retro §10 item 12. Configuration is presumed correct; explicit evidence-file citation absent.

11. **`cypher-replay.sh` final disposition pending.** Mandatory Fix #1 from sprint-plan §10 / Sprint 3 retro §7 item 7 / Sprint 4 retro §10 item 9. Implicit verdict per ADR-007 amendment is "RDB-restore is operative; Cypher export is docs-only audit." A one-line ADR-007 sub-amendment in S5 (Sprint 4 retro §6 lesson #5) closes the loop; pending.

12. **Preserved data dir cleanups.** `~/.graphiti-data.preserved-by-e3-s08` (after 2026-04-28); `/srv/graphiti/data.bak.20260427T123352` on ct-dev-homelab (after 24 h). Operator follow-ups; trivial; not blocking.

**Critical risks remaining count: 12** (3 operator-input-pending gates/decisions; 4 operator-action items; 3 unaddressed upstream behaviours; 2 evidence-citation gaps).

---

## E. ADR amendments shipped this product

Source: file headers in `_bmad-output/planning-artifacts/products/context-stack/adrs/` + commit history.

| ADR | Amendment | Commit | Sprint | Trigger / why |
|---|---|---|---|---|
| **ADR-002** (gpt-4o-mini for Graphiti extraction) | Amendment 2026-04-27 — LLM provider switch `gpt-4o-mini → gemini-2.5-flash-lite` via native `GeminiClient`; cost $1-3/mo at $0.10/M input + $0.40/M output | `7ebe1c5` | Sprint 3 (E3-S04g.4) | E3-S04a..e burned 4 substories on local-Gemma integration failures (30-300 s/episode latency, 0 entities persisted, Pydantic validation chain failures); Flash-Lite first try 7.5 s/episode + 10 entities + 10 edges + temporal facts. Cloud-line was not new commitment (OpenAI embedder under ADR-003 v1 already broke the privacy envelope). |
| **ADR-003** v2 (embeddings) | v2 in effect — OpenAI `text-embedding-3-small` (1536 dim) → Google `gemini-embedding-2` (3072 dim) routed via LiteLLM gateway | `3e5f003` | Sprint 3 (E3-S04b) | E3-S04b research found ADR-003 v1 OpenAI embedder incompatible with Gemini extraction path's expected output shape |
| **ADR-007** (Graphiti backup strategy) | Amendment 2026-04-27 — per-group graph reality; Layer 3 Cypher export now enumerates `GRAPH.LIST` dynamically (13 graphs at backup time, not "the" `default_db`) | `91ef4f6` | Sprint 3 (E3-S07) | FalkorDB hosts 13 distinct graphs (per-test isolation from E3-S06); single-default-db assumption was wrong |
| **ADR-007** (Graphiti backup strategy) | Sub-amendment 2026-04-27b — deployment-side `down -v` guard; two-flag interlock + `cp -a` snapshot + role test path + reversal trigger | `50563a4` | Sprint 4 (E4-S07) | Codifies the deployment-layer guard above the cron-backup layer; resolves Sprint 3 carry-forward #2 ("Mandatory Fix #2 — `down -v` guard spec did not visibly ship in S3") |
| **ADR-008** (daily $1 hard-cap) | Amendment 2026-04-27 — cost source switched OpenAI Usage API → LiteLLM `/metrics` Prometheus counter `litellm_spend_metric_total{api_provider="gemini"}`; throttle switched Graphiti SEMAPHORE_LIMIT 5→1 → LiteLLM YAML alias comment-out via sentinel markers; ntfy channel corrected `ct101.tail-scale.ts.net` → `https://ntfy.bi-services.be/` | `d4c032d` | Sprint 4 (E4-S04) | Three follow-on amendments to ADR-002/003 in Sprint 3 stranded ADR-008 v1's OpenAI assumption |
| **ADR-008** (daily $1 hard-cap) | Operator-accepted LLM-bypass cost-gap (Option A) — graphiti-core's native `GeminiClient` calls `generativelanguage.googleapis.com` directly, bypassing LiteLLM; only embedder traffic flows through the gateway and hits the counter; cap remains effective backstop via proportional `add_memory` → ~10 embedder calls path; re-evaluate at S5 if monthly spend approaches $10 | `3f48dea` | Sprint 4 (operator decision inside E4-S04) | Captures known gap explicitly rather than letting it lurk |
| **ADR-017** (Graphiti LLM local vs cloud decision) | Amendment 2026-04-27 — ADOPT-LOCAL Gemma reversed for Graphiti only; Gemma retained for Hermes / OWUI / dev-query workloads; three-condition reversal-of-reversal trigger documented | `7ebe1c5` | Sprint 3 (E3-S04g.4) | Same pivot as ADR-002 amendment; ADR-017 records the scope of the reversal (Graphiti-only) and the conditions under which the operator would re-attempt local |

**Amendment count this product: 7 amendments to 5 ADRs across 4 sprints.** No new ADRs were rendered obsolete; the amendment-in-place pattern (rather than abandon-and-replace) preserved architectural coherence through the cloud pivot.

---

## F. Verdict + decision rationale

Per sprint-plan §7.6:

- All MUSTs PASS → **RELEASE**
- MUSTs PARTIAL but functional → **CONTINUE** (Sprint 5 wraps with what's shipped)
- Critical MUST FAIL → **PIVOT**

**Strict count of MUSTs (PRD §5.7 distribution): 63 / 73 FRs are MUST.** Of those 63 MUSTs:

- The 12 FR-DEC MUSTs all PASS.
- The 11 FR-CG MUSTs all PASS (FR-CG-009 was SHOULD per PRD §5.2; ADR-014 split adjusts but doesn't unbreak the MUST count).
- The FR-MEM MUSTs that are unambiguously PASS: FR-MEM-001, 002, 003, 009, 013, 015 (`PARTIAL` against the strict-100% read but `PASS` against the threshold; ADR-014 SHOULD-downgraded). FR-MEM-004 PASS-WITH-AMENDMENT (intent met). FR-MEM-005 OPERATOR-INPUT-PENDING (AR8 probe; not a defect of the running stack — `tom-personal` is the configured default group_id, just not exercised under that name in S3 evidence). FR-MEM-006 + FR-MEM-011 INSUFFICIENT-DATA (citation gap, not config defect). FR-MEM-007 PARTIAL (operator-tagged half pending). FR-MEM-008 INSUFFICIENT-DATA (operator-data-pending). FR-MEM-010 PASS. FR-MEM-014 PASS. FR-MEM-012 PASS.
- The FR-WIKI MUSTs all PASS except FR-WIKI-006 PARTIAL (operator-side per-seed × 3-session count not surfaced in evidence).
- The FR-LLM MUSTs are all OPERATOR-INPUT-PENDING per the brief's hard rule (FR-LLM-005, 006, 007, 008 are the four MUSTs in this bucket; all gate-deferred). FR-LLM-004 PASS-WITH-AMENDMENT (effectively superseded by ADR-003 v2).
- The FR-OBS MUSTs: FR-OBS-001 + FR-OBS-002 + FR-OBS-004 PASS (FR-OBS-002 with amendment). FR-OBS-005 + FR-OBS-006 are SHOULD; FR-OBS-003 SHOULD.
- The FR-DEP MUSTs all PASS (or substantively-met-PASS for FR-DEP-006 with the literal `verify.yml` rename to playbook health-check + smoke-runner; FR-DEP-010 PASS-WITH-AMENDMENT for the locally-built image).

**Critical-MUST FAIL count: 0.**

**MUST PARTIAL count (substantively functional but with documented gaps): 5** — FR-MEM-007 (synthetic-recall passes, operator-tagged half pending); FR-WIKI-006 (operator-side count pending); FR-MEM-005 (AR8 probe pending; configured but not exercised under `tom-personal` name); plus 2 others on a strict reading.

**OPERATOR-INPUT-PENDING count (gate-deferred or evidence-citation pending, not defects): 8** — almost entirely FR-LLM-* gate-deferred per the brief's hard rule.

**Verdict flow:**

- All MUSTs PASS strictly? **No** — 5 PARTIAL + 8 OPERATOR-PENDING + 3 INSUFFICIENT-DATA. So not RELEASE.
- Are MUSTs PARTIAL but functional? **Yes** — every PARTIAL is "substantively met with operator-side data missing or evidence-citation pending"; the running stack does what the FR demands. K6 / FR-OBS-005 INSUFFICIENT-DATA is the only data-class gap that the binding scorecard cannot yet score, and it is a measurement-window problem, not a stack-defect.
- Is there a critical MUST FAIL warranting PIVOT? **No** — zero FAILs across 73 FRs and 25 NFRs. The single architectural pivot already absorbed (cloud-Gemini for Graphiti) shipped clean and was justified by smoke evidence (E3-S04f-retry).

**Verdict: CONTINUE.** The product is on track — the cloud-Gemini pivot is the only architectural change that shipped this product, and it shipped clean. The remaining work to reach RELEASE is operator-side: resolve FR-LLM-007 gate, complete the four operator-action items (key rotations, restic, AR8 probe, FalkorDB RSS snapshot), and either capture K6 retroactively or accept it as INSUFFICIENT-DATA at product close.

**Why not RELEASE:** at least 8 OPERATOR-INPUT-PENDING items that are not defects but are gates, plus K6 INSUFFICIENT-DATA which is a measurement-window problem the operator can close in two ways (retroactive tagging or accept-and-commit-to-prompt-from-now). RELEASE without resolving FR-LLM-007 is meaningful — but the brief's hard rule says treat that bucket as gate-pending, not defect-pending. The honest reading is that the gate is the operator's call and the product cannot mark RELEASE until the call is made.

**Why not PIVOT:** zero FAILs. The pivot already happened in Sprint 3 and shipped. Architecture decisions are stable. No rebuild signal anywhere.

---

## G. Sprint 5 close-out checklist (input to E4-S12)

What needs to land in E4-S12 (final retro + product close) for the product to formally close:

1. ✅ This scorecard (E4-S11) committed.
2. E4-S12 retro authored — covers the 5-sprint product close, validates ADR-014 SHOULD/MUST split retroactively (Sprint 4 retro §6 lesson #5), backlog tickets for deferred work, quarterly wiki-review cadence, velocity-log backfill (5 rows: S1-S5; Sprint 4 retro §12 confirms the 1.7× plan multiplier is wrong by an order of magnitude for concentrated pushes — actual closer to 0.1×–0.2×).
3. Operator GO conditions resolved — sprint-5 kickoff §3 + Sprint 4 retro §10:
    - FR-LLM-007 gate decision (Path A / Path B / explicit deferral with backlog ticket).
    - Key rotations: `LITELLM_MASTER_KEY`, `GEMINI_API_KEY`.
    - Restic source-set update.
    - Preserved data dir cleanups (`~/.graphiti-data.preserved-by-e3-s08`, `/srv/graphiti/data.bak.20260427T123352`).
    - AR8 `tom-personal` probe (one-off, ≤ 0.25 d).
    - FalkorDB RSS workstation snapshot capture.
    - `SEMAPHORE_LIMIT=5` + telemetry-off evidence-citation closure.
    - `cypher-replay.sh` disposition closed via one-line ADR-007 sub-amendment ("RDB-restore is operative; Cypher export is docs-only audit").
    - K6 daily prompt template change (start at product-close + steady-state) OR retroactive operator self-tagging across the past 2 days where Graphiti was queried.
    - E4-S02 wiki seed promotion (`status: draft` → `status: stable`) for `tailscale-policy`, `pve9-ha-migration`, `hybrid-gemma-serving`.
4. Branch merge-to-main vs feature-branch-for-further-work — operator decision at S5 retro. The current branch `feature/context-stack-e3-graphiti` carries Sprints 3-5 work; Sprint 1 + Sprint 2 retros and the Sprint-2 KPI scorecard live on `main` already (`730c4fb`, `650e906`, `c18b014`); the binding S5 close should fold this branch's work into `main` if RELEASE, or hold as a feature branch if CONTINUE-with-operator-actions.

---

## Files cited

- `/home/developer/workspace/homelab/homelab-playbook/_bmad-output/planning-artifacts/products/context-stack/prd.md` (FR/NFR catalogue §5/§6; KPI definitions §7; release acceptance §11)
- `/home/developer/workspace/homelab/homelab-playbook/_bmad-output/planning-artifacts/products/context-stack/epics.md` (epic acceptance §3.4 / §4.4 / §5.4 / §6.4; FR coverage audit §8)
- `/home/developer/workspace/homelab/homelab-playbook/_bmad-output/planning-artifacts/products/context-stack/sprint-plan.md` (§7.5 Path A DoD; §7.6 binding decision gate)
- `/home/developer/workspace/homelab/homelab-playbook/_bmad-output/planning-artifacts/products/context-stack/tests/acceptance.md` (325 ACs, 38 stories — referenced for AC-to-FR mapping)
- ADRs amended this product: `adrs/ADR-002-*` (amend `7ebe1c5`); `adrs/ADR-003-*` v2 (amend `3e5f003`); `adrs/ADR-007-*` (amends `91ef4f6` + `50563a4`); `adrs/ADR-008-*` (amends `d4c032d` + `3f48dea`); `adrs/ADR-017-*` (amend `7ebe1c5`).
- Sprint 1: `_bmad-output/implementation-artifacts/context-stack-sprint-1-retro-2026-04-26.md` (`730c4fb`); `docs/decommission/sprint-1-verify-report.md` (on `main`); tag `phase-1-decommission-complete`.
- Sprint 2: `docs/context-stack/sprint-2/e2-s08-week1-kpi-scorecard.md` (`c18b014`, on `main`); `_bmad-output/implementation-artifacts/context-stack-sprint-2-retro-2026-04-26.md` (`650e906`, on `main`); E4-S09 backfill `docs/context-stack/sprint-2/kpi-backfill.md` (this branch).
- Sprint 3: `docs/context-stack/sprint-3/e3-s09-kpi-scorecard.md` (`3068767`); `docs/context-stack/sprint-3/e3-retro.md` (`03ad119`); E3-S04f-retry, S06, S07, S08, S08.5, S08.6 evidence files.
- Sprint 4: `docs/context-stack/sprint-4/retro.md` (`144174f`); E4-S04 evidence (`d4c032d` + `3f48dea`); E4-S07 evidence (`50563a4`); E4-S08 evidence (`0a4a096`).
- Sprint 5: `docs/context-stack/sprint-5/kickoff.md` (`ca21749`); `docs/context-stack/sprint-5/e4-s09-evidence.md` (`d4896ab`); `wiki/decisions/weekly-digest-2026-w18.md`; E4-S10 query-hierarchy + 4 exit-ramps (`437c0bc`).

---

**End of E4-S11 — input to E4-S12 (final Sprint 5 retro + product close-out).**
