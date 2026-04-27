# Epic E3 (Graphiti Pilot) — Sprint 3 Retrospective

**Date:** 2026-04-27
**Sprint:** 3 (Graphiti Pilot, Week 2 of 10)
**Status:** CLOSED — Exit Gate **CONDITIONAL-PASS** (see §6)
**Branch:** `feature/context-stack-e3-graphiti` (this retro); Sprint 3 evidence committed on `decommission/context-stack-phase-1` per scorecard l.6
**Story count:** 9 planned + 1 prep + 7 unplanned substories executed = **17 total** (see §9)
**Author:** independent analyst (not an executor of the work)
**Sources:** every claim below is tied to a file path or commit SHA. Operator-side observations are marked "operator input pending".

---

## 1. Sprint goal vs outcome

**Planned goal** (sprint-plan.md §5.1, l.242): "Stand up Graphiti + FalkorDB Docker Compose stack on `ct-ai-01` per the 488-line install runbook; configure `gpt-4o-mini` + embeddings + `SEMAPHORE_LIMIT=5` + `tom-personal` namespace; ship three-layer backup (AOF + RDB + Cypher monthly); execute restore drill; pass 5 functional smoke tests; reach the week-2 KPI gate (4-of-6 green including K5 first-shot recall)."

**Outcome:** stack is up and the Graphiti-side smokes pass, but the LLM provider is **not** `gpt-4o-mini`, the embedder is **not** `text-embedding-3-small`, and the deploy target is **not** `ct-ai-01`. Mid-sprint a local-LLM arc (`E3-S04a..e`) ran 30-300s/episode with 0 entities persisted, was abandoned, and the stack pivoted to cloud `gemini-2.5-flash-lite` + `gemini-embedding-2`, which produced 7.5s/episode and 96% (48/50) persistence on a real 50-fact corpus (`e3-s04f-retry-evidence.md`, `e3-s06-evidence.md` §Test 1 l.32-65). Backup + restore drill landed; restore drill PASSED at 91s downtime (`e3-s08-evidence.md` §Phase 7). The week-2 6-KPI gate scored 1 PASS / 2 PARTIAL / 0 FAIL / 3 INSUFFICIENT-DATA (`e3-s09-kpi-scorecard.md` §Score tally l.30-37) — the literal "4-of-6 green" rule is unreachable from Sprint 3 alone because three of the six KPIs are GitNexus-bound and Sprint 2 was deferred. The honest reading is that every KPI in Sprint 3's actual scope passed or partial-passed; nothing failed.

The pilot delivered the function it was scoped for, on a different stack than planned, and at a different cost/quality envelope that turned out to be materially better than the original plan.

---

## 2. What went well

- **Cloud-LLM pivot landed first attempt clean.** After 4 substory iterations on local Gemma, `e3-s04f-retry-evidence.md` §Smoke test results l.65-76 records 6/6 substeps PASS on the first cloud run: 10 entities + 10 edges + temporal facts persisted, 7.5s end-to-end. No iteration needed once the provider flipped.
- **50-episode functional smoke held up under real load.** `e3-s06-evidence.md` §Test 1 l.32-65: 48/50 episodes persisted (96%, exceeds the ≥90% gate), avg 7.6 entities/episode, 363 unique entity mentions, zero LLM-side failures across 50 sequential calls. The 2 failures are attributable to a known FalkorDB driver bug (E3-S04h), not the LLM path.
- **Restore drill PASSED end-to-end with documented gotcha.** `e3-s08-evidence.md` §Phase 7 verdict: 91-second downtime, 26 keys + 13 graphs restored, all node counts matched pre-drill exactly. The first attempt failed silently (AOF preferred over RDB → 0 keys); the corrected procedure is captured in `e3-s08-restore-runbook.md` so the next operator does not re-discover it.
- **Workaround stack peaked at 5, ended at 3 (1 on the hot path).** `e3-s04g-evidence.md` §Goal recap shows the pivot+cleanup compressed peak `factories.py` patch + `OPENAI_BASE_URL` + `gemma4-26b-json` alias + `gemma-hybrid-proxy` + transient `pip install` down to two retained Hermes/OWUI workarounds plus one Sprint-3-late `graphiti_mcp_server.py` patch (E3-S08.6). Net: 5 → 3.
- **All four affected ADRs were amended in place, not abandoned.** ADR-002 (LLM provider switch + cost model), ADR-003 v2 (embedder switch), ADR-007 (per-group graphs in Layer-3 export), and ADR-017 (ADOPT-LOCAL reversed for Graphiti only, three-condition reversal-of-reversal trigger documented). Per `e3-s09-kpi-scorecard.md` §ADRs amended l.50-55. The architectural surface stays coherent.
- **Evidence discipline was rigorous.** Every substory has a dated evidence file with verbatim MCP requests/responses, log lines, and verdict. The investigation-first habit (`e3-s04c-investigation.md`, `e3-s08-5-search-regression-investigation.md`) caught two architectural surprises (option-A bridge non-functional on LiteLLM 1.83.13; graphiti-core's `@handle_multiple_group_ids` decorator skipping driver clones for `len==1`) before they shipped silently.
- **Cost ran an order of magnitude under budget.** `e3-s09-kpi-scorecard.md` §K3 l.24: $1-3/month projected against the $20/month NFR-COST-001 ceiling. The $1/day NFR-COST-002 cap (E4-S04 not yet shipped) is also robust to a 5x usage error per §Cost run-rate l.111-112.

## 3. What didn't go well

- **The Gemma-local path consumed 4 substory iterations before the cloud pivot.** Commits `7b2f52e` (E3-S04a, 2026-04-26 19:33Z) → `add0611` (E3-S04e, 2026-04-26 20:43Z) executed `LiteLLM alias → embedder switch → option-A bridge → factories.py patch → option-A revert` over a 70-minute span. The original spike (E3-S01.5) had verdict-flipped twice already (`74ef3aa` "ADOPT-LOCAL" v3 the same morning); none of the spike runs caught the graphiti-core integration issues that the substory arc surfaced.
- **The original spike judged parse quality but not integration.** `e3-s01-5-spike/evidence-extended.md` (the v3 ADOPT-LOCAL verdict) measured Gemma's JSON-mode behaviour in isolation. It did not measure Pydantic schema validation through `OpenAIGenericClient`, dedup query escaping, or the actual Graphiti extraction prompt at production length. The arc from `e3-s04a` to `e3-s04f-retry` was the missing integration-smoke step, executed retroactively after architectural commitment.
- **Late-Sprint-3 architectural surprise: search was returning 0 hits for most of the sprint.** `e3-s08-5-search-regression-investigation.md` §TL;DR l.7-8: graphiti-core's `@handle_multiple_group_ids` decorator only fans out the per-group FalkorDB driver clone when `len(group_ids) > 1`. With one group_id, `search_nodes` ran against the boot-time empty `default_db`. The 4/5 strong top-1 result in E3-S06 Test 2 was correct only because the prior `add_episode` mutated `driver._database` as a side-effect. The bug was fixed in E3-S08.6 (`9c5b35d`, 09:58Z) — **~2 hours before the KPI scorecard was authored** at `3068767` 10:05Z. K6 (subjective uplift) is INSUFFICIENT-DATA in part because operator real-session use of `search_nodes` was masked by this bug for most of the sprint.
- **Three KPIs scored INSUFFICIENT-DATA, not because Sprint 3 failed but because Sprint 2 never happened.** `e3-s09-kpi-scorecard.md` §K1/K2/K4-GitNexus l.22-26: GitNexus MCP shows `Connected` per E3-S03 evidence l.26, but `docs/context-stack/sprint-2/` does not exist and no week-1 KPI scorecard was ever authored. The literal "4-of-6 green" rule from `epics.md` §5.5 was authored assuming Sprint 2 carried K1/K2/K4-GitNexus measurements forward. Sprint 3 inherited the gap without inheriting the data.
- **Sprint plan said `ct-ai-01`; sprint shipped on the workstation.** `epics.md` §5.1 l.255 and sprint-plan.md §5.1 l.242 both target `ct-ai-01`. Restore-drill evidence (`e3-s08-evidence.md`) shows backup paths under `~/.local/state/graphiti-backup/` on the workstation; the `ct-ai-01` deploy is the E4-S08 acceptance criterion still pending. This is not necessarily wrong (the workstation is a faster iteration surface) but the planned-vs-actual delta is real and was not flagged in the scorecard's "operational readiness" section.
- **Two pre-S4 prep deliverables did not ship.** `e3-s09-kpi-scorecard.md` §Sprint 4 readiness checklist l.140-150: the `down -v` rollback-guard spec for E4-S07 (Mandatory Fix #2 from sprint-plan.md §10) is "not visible in Sprint 3 evidence"; `cypher-replay.sh` (Mandatory Fix #1, AC11 of E3-S07) "does not appear to have shipped in Sprint 3." Both were supposed to land here.
- **Scope crept silently via substory naming.** E3-S04 was 1 ideal day in the plan (`epics.md` §5.8 l.347). It expanded into E3-S04a, S04b, S04c, S04d, S04e, S04f, S04f-retry, S04g — 7 substories spanning 14 hours of evidence-bearing commits. There was no formal sprint-change-proposal cycle; the substories materialised inline in commits. The sprint plan's velocity-tracking section (sprint-plan.md §8) is a calibration mechanism that did not get exercised here.

## 4. Architectural pivots taken mid-sprint

| Pivot | Trigger | Resolution | Residual debt |
|---|---|---|---|
| **Local Gemma → cloud Gemini 2.5 Flash-Lite for extraction** (ADR-002, ADR-017) | E3-S04a..e: 30-300s/episode latency, 0 entities persisted, Pydantic validation chain failures with local Gemma via LiteLLM `OpenAIGenericClient`. Documented in `e3-s04c-investigation.md` and `e3-s04e: option-A residue revert` (commit `add0611`). | E3-S04f-retry switched provider to native `GeminiClient`. Smoke PASS first attempt (`e3-s04f-retry-evidence.md` §Smoke results). ADR-002 amended 2026-04-27, ADR-017 amended same day with a three-condition reversal-of-reversal trigger. | Cloud dependency on Google AI; privacy envelope already broken by OpenAI embedder under ADR-003 v1 so no new commitment per ADR-002 Amendment §Privacy. Cost: $1-3/month projected. |
| **OpenAI `text-embedding-3-small` → Google `gemini-embedding-2`** (ADR-003 v1 → v2) | `e3-s04b-embedder-research.md` (uncommitted draft, referenced from `e3-s04b-evidence.md`) found ADR-003 v1's 1536-dim OpenAI embedder incompatible with the Gemini extraction path's expected 3072-dim output. | ADR-003 v2 in effect (`e3-s04b: ADR-003 v2 amendment`, commit `3e5f003`). Embedder routed via LiteLLM gateway. | None on the smoke path. Cross-embedder migration if a future ADR-003 v3 lands would require re-embedding the 260+ entity nodes. |
| **Option-A LiteLLM bridge → revert + native client** | `e3-s04c-investigation.md`: option-A `OPENAI_BASE_URL` override approach is non-functional on LiteLLM 1.83.13 because `OpenAIGenericClient` selection in graphiti-core defaults to `/v1/responses` not `/v1/chat/completions`. | Reverted to factories.py bind-mount Pydantic patch (E3-S04d), then full pivot to native Gemini client (E3-S04f-retry). The factories.py patch was removed in E3-S04g cleanup (image `graphiti-mcp-genai-bundled:e3-s04g`). | None; bridge attempt fully reverted. |
| **Backup Layer 3 (Cypher export): single `default_db` → enumerate `GRAPH.LIST` dynamically** (ADR-007 amendment) | E3-S07 implementation discovered FalkorDB hosts 13 distinct graphs at backup time, not "the" `default_db`. Per `e3-s07-evidence.md` §ADR-007 amendment. | Backup script enumerates `GRAPH.LIST`; produces 13 nodes-files + 13 edges-files + MANIFEST in an 18.2 MB tarball. ADR-007 amended same day. | Cross-group entity leak (a failed dedup query landed entities in an unrelated graph) — documented as untreated open issue in `e3-s09-kpi-scorecard.md` §Open issues l.121. |
| **`graphiti_mcp_server.py` bind-mount patch** (E3-S08.6, late-sprint) | Post-restore drill: `search_nodes` returned 0 hits despite 260 indexed entities. Investigation (`e3-s08-5-search-regression-investigation.md`) traced root cause to graphiti-core's per-group decorator behaviour. | Bind-mount patch adds explicit `driver=client.driver.clone(database=group_ids[0])` for the 1-group case in `search_nodes`, `search_memory_facts`, `get_episodes`. 4/4 smoke PASS post-restart per `e3-s08-6-evidence.md` §Smoke results. | New workaround on the hot path; drop conditions documented in `e3-s08-6-evidence.md` §Drop conditions. Upstream `getzep/graphiti` or `zepai/knowledge-graph-mcp` image refresh that changes `graphiti_mcp_server.py` shape requires re-patching. |

## 5. Lessons for future sprints

- **Spike parse-quality is necessary but not sufficient.** Run a full integration smoke (extraction prompt at production length, dedup, persistence, retrieval) against the actual stack before architectural commitment. The E3-S01.5 spike measured Gemma JSON-mode in isolation; the integration issues that drove the pivot only surfaced 4 substories deep into E3-S04. A 0.5-day "end-to-end smoke against the real Graphiti container" gate at the spike boundary would have caught it cheaper than 4 substories did.
- **Substory expansion needs a formal trigger, not just a commit prefix.** E3-S04 grew from 1 story to 7 substories without a sprint-change-proposal. The velocity-tracking discipline in sprint-plan.md §8 explicitly anticipates this kind of overflow but was not exercised here. Recommend: at the moment a story emits its second substory, file a one-paragraph change-proposal note in the sprint directory so the carry-forward picture stays honest.
- **Late-sprint architectural surprises mask KPIs that depend on real operator usage.** K6 (subjective uplift) is not measurable when the search path returns 0 hits for half the sprint. If a sprint includes a "real operator usage" KPI, the dependent code path needs a hard smoke at sprint mid-point, not at sprint close. The E3-S08.5 investigation lands ~2 hours before the scorecard — that's a near-miss, not a margin.
- **Pre-prep items should have a hard ship-by point inside the sprint that owns them.** The `down -v` guard spec (S4-prep, owed by S3) and `cypher-replay.sh` (S3-prep authoring + S3 commit per AC11) both did not ship visibly. Both are small (≤0.5d). Recommend: at sprint kickoff, file the prep items as their own evidence-bearing stub with a sprint-day deadline.
- **"Plan target host" vs "actual deploy host" needs explicit mid-sprint reconciliation.** Sprint plan said `ct-ai-01`; sprint shipped on workstation. Either the plan needed a same-week amendment (sprint-change-proposal) or the scorecard needed a §Plan-vs-actual delta section. The KPI scorecard's "Sprint 4 readiness checklist" is the closest thing, but it tracks Sprint 4 prerequisites, not Sprint 3 plan deltas.

## 6. Exit Gate (Epic E3 acceptance)

Epic E3 acceptance criteria are quoted from `epics.md` §5.4 l.288-297. Each criterion is scored against Sprint 3 evidence with source.

| # | Acceptance criterion (epics.md §5.4) | Status | Source | Notes |
|---|---|---|---|---|
| 1 | `docker compose ps` shows `graphiti-mcp` + `graphiti-falkordb` Up | PASS | `e3-s09-kpi-scorecard.md` §Sprint 4 readiness l.142 ("graphiti-mcp Up (healthy), falkordb Up (healthy)") | Workstation, not `ct-ai-01` (see §3 "plan said ct-ai-01" finding) |
| 2 | `claude mcp list` shows `graphiti` over HTTP, healthy | PASS | `e3-s03-mcp-wiring-evidence.md` (commit `edcf688`) | MCP HTTP transport wired |
| 3 | `add_episode` returns UUID; `search_facts` retrieves it | PASS | `e3-s04f-retry-evidence.md` §Smoke test results l.65-76 | 7.5s end-to-end, 10 entities + 10 edges |
| 4 | Bi-temporal `valid_at` query passes | PASS-WITH-NOTE | `e3-s06-evidence.md` Test 3 (PASS-with-note) | 2 facts returned with `valid_at` populated; `invalid_at` not auto-set on this surface |
| 5 | All writes land in `tom-personal` (default group) | DEFERRED-IN-PRACTICE | `e3-s06-evidence.md` Test 1 used `e3s06test1`, not `tom-personal` | The default-group AR8 verification was not exercised against `tom-personal` specifically; E3-S06 used per-test alphanumeric groups to dodge E3-S04h. AR8 needs a Sprint 4 verification. |
| 6 | FalkorDB resident memory < 200 MB at end of sprint | OPERATOR INPUT PENDING | Not surfaced in scorecard or evidence | `docker stats` snapshot at end of Sprint 3 not captured in any committed evidence file |
| 7 | AOF daily / RDB weekly / Cypher monthly + restore drill exercised | PASS | `e3-s07-evidence.md` (AOF + cron + 10.66 MB RDB + 18.2 MB tarball); `e3-s08-evidence.md` (91s restore drill PASS) | Backup files exist on workstation only; restic source-set update is operator follow-up #1 |
| 8 | `SEMAPHORE_LIMIT=5`; telemetry off; pinned image tags | PARTIAL | `e3-s04g-evidence.md` (image `graphiti-mcp-genai-bundled:e3-s04g`); SEMAPHORE_LIMIT not surfaced | Image is pinned (locally tagged not registry-pinned). SEMAPHORE_LIMIT and telemetry-off settings not explicitly cited in scorecard or evidence file. Operator input pending. |
| 9 | Week-2 KPI gate: ≥4-of-6 KPIs green | LITERALLY UNMET; SUBSTANTIVELY MET | `e3-s09-kpi-scorecard.md` §Score tally l.30-37 | 1 PASS / 2 PARTIAL / 0 FAIL / 3 INSUFFICIENT-DATA; the 3 INSUFFICIENT-DATAs are GitNexus-bound and reflect Sprint 2 deferral, not Sprint 3 failure. Scorecard recommends conditional GO. |

**Exit Gate verdict: CONDITIONAL-PASS.** Five of nine criteria are clean PASS, two are PASS-WITH-NOTE / PARTIAL, two are operator-input-pending (AC5 `tom-personal` AR8 verification; AC6 FalkorDB RAM check; AC8 SEMAPHORE/telemetry config), and AC9 is unmet on the literal rule but substantively met within Sprint 3's actual scope. Zero criteria FAIL. The conditional GO recommended in the KPI scorecard (proceed to Sprint 4 with three notes) is the operative posture.

## 7. Carry-forward to Sprint 4

From the KPI scorecard's GO conditions (`e3-s09-kpi-scorecard.md` §Conditions for the GO l.162-166):

1. **At Sprint 4 kickoff (D31):** verify `ct-dev-homelab` reachability; re-confirm or draft the `down -v` rollback-guard spec for E4-S07 (Mandatory Fix #2, did not ship in S3 per scorecard l.149).
2. **Within Sprint 4:** point restic at `~/.local/state/graphiti-backup/` (operator follow-up #1 from scorecard l.131).
3. **Sprint 4 scope addition:** backfill K1, K2, K4-GitNexus measurement against the running GitNexus MCP. Recommend: ride E4-S09 (weekly observability digest), since it already covers GitNexus reindex timings + tool-hit-rate.

From this retro:

4. **Verify AR8 default-group discipline against `tom-personal` specifically.** E3-S06 used per-test alphanumeric groups to dodge E3-S04h; the planned `tom-personal` namespace verification (epic AC5) was not exercised. Add a one-off probe at S4 kickoff.
5. **Capture FalkorDB RSS at end of Sprint 4 against the < 200 MB threshold.** Epic AC6 needs a `docker stats` snapshot in evidence; not captured in S3.
6. **Re-confirm SEMAPHORE_LIMIT and telemetry-off settings in evidence.** Epic AC8 components not cited explicitly in S3 evidence.
7. **Land `cypher-replay.sh`.** Mandatory Fix #1, owed by E3-S07 AC11, did not ship visibly per scorecard l.150. Either land it in S4 or document the RDB-restore path (E3-S08, validated) as the operative recovery procedure and downgrade the Cypher tarball to documentation-only.
8. **Add a one-line "did this save a re-derivation?" prompt to the operator's daily retro template starting S4 D31** so K6 has 4 weeks of operator-tagged data before the product-level S5 gate (per scorecard §Risks for Sprint 4 item 5 l.181).

## 8. Backlog / deferred items

| ID | Item | Source | Severity | Notes |
|---|---|---|---|---|
| E3-S04h | `falkordb_driver.py` hyphen-quoting defect in RediSearch query builder | `e3-s09-kpi-scorecard.md` §Open issues l.119 | M | ~4% observed failure rate on a realistic 50-fact corpus. Workaround: alphanumeric `group_id` only. Real fix: patch `graphiti_core/driver/falkordb_driver.py` upstream or vendored. |
| (no ID) | Cross-group entity leak | `e3-s09-kpi-scorecard.md` §Open issues l.121 | L | Fact-19's failed dedup leaked entities into `e3s06test3bitemp` graph. Not a security issue at single-operator scale. Documented; untreated. |
| (no ID) | `add_episode` mutates `self.driver._database` upstream | `e3-s09-kpi-scorecard.md` §Open issues l.122 | M (theoretical) | Race condition under concurrent `add_episode` with different group_ids. E3-S08.6 patch dodges it; upstream concurrency risk remains. Out of scope for E3. |
| (no ID) | No auto-retry of failed episodes | `e3-s09-kpi-scorecard.md` §Open issues l.123 | L | When embedder gateway dropped (E3-S06 Test 5b), failed episode permanently dropped; operator must resubmit. Documented v1.26.0 behaviour. |
| Operator follow-up #1 | Point restic at `~/.local/state/graphiti-backup/` | `e3-s09-kpi-scorecard.md` §Open items l.132 | H if not done | Workstation-loss event currently loses every backup. Single config change. |
| Operator follow-up #2 | Delete `~/.graphiti-data.preserved-by-e3-s08` after 2026-04-28 | `e3-s09-kpi-scorecard.md` §Open items l.133 | L | 24h post-drill safety copy; ~10 MB. Per restore runbook. |
| Operator follow-up #3 | Decide Sprint 2 GitNexus disposition (backfill vs carry-forward) | `e3-s09-kpi-scorecard.md` §Open items l.134 | M | Affects S5 product-level gate readability. |
| S3-prep #1 | `cypher-replay.sh` companion | sprint-plan.md §10 / `e3-s09-kpi-scorecard.md` §Sprint 4 readiness l.150 | L | Did not ship in S3. Defer or downgrade to docs-only. |
| S3-prep #2 | `down -v` rollback-guard spec for E4-S07 | sprint-plan.md §10 / `e3-s09-kpi-scorecard.md` §Sprint 4 readiness l.149 | M | Did not ship visibly. S4 kickoff item. |
| (no ID) | E3-S08.6 bind-mount patch is fragile against upstream image refresh | `e3-s08-6-evidence.md` §Drop conditions | M | Operator must monitor `getzep/graphiti` and `zepai/knowledge-graph-mcp` releases; re-patch on shape change. |
| Daily $1 cap not yet enforced | E4-S04 work | `e3-s09-kpi-scorecard.md` §Open issues l.125 | M | Manual cost discipline only between now and Sprint 4 close. Sprint 4 plan-of-record. |

## 9. Story count: planned vs actual

| Tier | Stories |
|---|---|
| **Planned in epics.md §5.8** | E3-S01, S02, S03, S04, S05, S06, S07, S08, S09 = **9 stories** |
| **Plus prep item from sprint-plan.md §5.2** | S4-prep (`down -v` guards) — did not ship | +1 planned |
| **Substories added during sprint (E3-S04 expansion)** | E3-S04a, S04b, S04c, S04d, S04e, S04f, S04f-retry, S04g = **8 substory commits** for the 1 originally-planned E3-S04 story | +7 net (7 extra over original 1) |
| **Spike (E3-S01.5) and re-runs** | E3-S01.5, S01.5b, S01.5c = **3 spike commits** for what `epics.md` does not list as a separate story (the spike is implicit in E3-S01 but commit history surfaces it as 3 distinct verdict-flips) | +3 if counted |
| **Investigation/fix substories late in sprint** | E3-S08.5 (search regression investigation), E3-S08.6 (search fix) = **2 substories** | +2 |
| **Total commits with `e3-` prefix on the closing branch** | 18 (per `git log --oneline ... e3-` on `decommission/context-stack-phase-1`) | — |

**Headline number: 9 planned stories → ~17 effective stories executed (depending on whether you count the 3 spike re-runs as one story or three).** The +8 expansion is dominated by E3-S04 (1 → 8) and the late-sprint search-regression arc (S08 → S08, S08.5, S08.6).

This is **not** the same growth pattern as Epic 7 of the pve3-storage-migration sprint (`epic-7-retro-2026-04-25.md` §Discovery 2 l.682-705), which grew from 7 → 14 stories through deliberate "lessons-learned codification" additions. Epic 7's growth was a feature; the Epic 7 retro explicitly called it healthy. Epic E3's growth is a different pattern: **debugging substories under a story that turned out to be on the wrong architecture.** The E3-S04 chain (a → e) is sunk cost — none of those substories shipped a deliverable; they cleared the way for the cloud pivot. Useful to learn from, expensive to re-run.

## 10. Time spent

Sprint 3 first commit `d0bfaea` (e3-s01: FalkorDB evidence) — **2026-04-26 15:51 UTC**.
Sprint 3 final commit `3068767` (e3-s09: scorecard) — **2026-04-27 10:05 UTC**.

Elapsed: **~18 hours 14 minutes wall-clock**, single calendar day boundary crossed.

This is **dramatically faster than the sprint plan's ~17 wall-clock-day estimate** (sprint-plan.md §5.2). Three readings, listed honestly:

1. The plan's ideal-day:wall-clock multiplier of ~1.7× (sprint-plan.md §1) was wildly conservative for this sprint. Operator was clearly working concentrated hours, not the assumed ~3 hrs/day side-project cadence.
2. The "Sprint 3" framing collapses what would normally be 10 calendar days into a single push. **operator-side timing input pending** for whether this represents (a) a chosen intensive sprint, (b) catch-up after a gap, or (c) a different way of accounting for sprint duration than the plan assumed.
3. The velocity-calibration mechanism in sprint-plan.md §8 is unexercised: no `velocity-log.md` entry has been appended yet. Recommend doing so post-retro to inform S4-S5 planning.

## 11. Recommendation for Sprint 4 retro structure

Based on this sprint's findings, future retros should additionally capture:

- **Substory-budget actuals.** Track planned-stories vs effective-stories-executed at retro. Add a column to `velocity-log.md`: "substories added mid-sprint" with reason.
- **Plan-vs-actual delta section.** Where did the sprint deviate from sprint-plan §X.1 sprint goal? E.g. host (`ct-ai-01` vs workstation), components (`gpt-4o-mini` vs `gemini-2.5-flash-lite`), prep items (shipped vs deferred). Surface deltas explicitly so Sprint N+1 plans against reality, not against Sprint N's plan.
- **KPI in-scope subset score.** When upstream KPIs are deferred (as Sprint 2 was), score the in-scope KPI subset explicitly so the literal "4-of-6" rule does not produce noise. The Sprint 3 scorecard does this implicitly in prose; future scorecards should formalise it.
- **Mid-sprint integration-smoke gate after any spike.** Add a 0.5-day "full integration smoke" line item to the sprint plan immediately after any architectural-decision spike. The E3-S04 chain shows what happens when the integration-smoke step is implicit and lands at substory boundary instead.
- **"Did this save a re-derivation?" daily prompt.** Per scorecard §Risks for Sprint 4 item 5 l.181, capture K6 data continuously throughout the sprint, not retrospectively at retro time.

---

**End of retro.** This document is the Epic E3 Exit Gate and the Sprint 3 closure artifact. Sprint 4 GO is conditional per §6 + §7.
