# Sprint 4 (E4 Part A: Production Hardening) — Retrospective

**Date:** 2026-04-27
**Sprint:** 4 (E4 Part A, Week 4 of 10) — formal close-out and Exit Gate
**Status:** CLOSED — functional scope passed; E4-S02 seed pages landed as drafts; this retro is the Exit Gate
**Branch:** `feature/context-stack-e3-graphiti` (homelab-infra + homelab-playbook); E4-S08 Phase-1/2/3/4 commit lists `decommission/context-stack-phase-1` for the homelab-playbook side per evidence header
**Story count:** 6 planned + 1 small substory split (E4-S01 substrate + closer) = **7 effective stories**, 0 mid-sprint substory explosions
**Author:** independent analyst (not an executor of the work)
**Sources:** every claim below ties to an evidence file under `docs/context-stack/sprint-4/`, an ADR amendment, or a commit SHA. Operator-side observations are marked "operator-input pending".

---

## 1. Sprint goal vs outcome

**Planned goal** (sprint-plan.md §6.1, l.331): "Ship the wiki tier (schema + 3-5 seeds + `wiki-query` skill); enforce the daily $1 hard-cap auto-throttle (ADR-008); wrap the stack in the `ai-dev-context-stack` Ansible role; deploy to ct-dev-homelab and exercise rollback drill (G-Rollback gate). Defer LiteLLM bridge + observability digest + product KPI scorecard to S5."

**Outcome:** all six planned stories shipped on the planned target host (ct-dev-homelab, 192.168.50.156) with the planned deliverables. The wiki tier exists with 4 seed pages (`tailscale-policy`, `pve9-ha-migration`, `hybrid-gemma-serving`, plus the E4-S03 `wiki-query-skill` runbook itself); the `wiki-query` skill is installed at `~/.claude/skills/wiki-query/SKILL.md`; `wiki-lint.sh` + pre-commit hook ship via `install-git-hooks.sh`; `cost-cap.sh` is on cron at `*/30` on ct-ai-01 with breach + restore proven end-to-end; the reusable `compose-app` Ansible role landed and was exercised twice (graphiti, gitnexus) via `deploy-context-stack.yml`; ct-dev-homelab is live with all three containers healthy; the destructive-down guard drilled live (`/srv/graphiti/data.bak.20260427T123352` snapshot retained on host as a recovery artefact). 5/5 smokes PASS, comfortably above ADR-014's lenient SHOULD threshold (3-of-5 hard + 2-of-5 quality). The Ansible role is generic-by-design — context-stack is the first caller, not the only one. Two ADR amendments shipped (ADR-007 sub-amendment 2026-04-27b for the deployment-side guard; ADR-008 amendment for the Gemini cost source + the 2026-04-27 operator-accepted LLM-bypass cost-gap). No architectural pivots, no substory expansion of the E3-S04-style.

---

## 2. What went well

- **No architectural pivots, no substory explosion.** Sprint 3 grew from 9 planned to ~17 effective stories (Sprint 3 retro §9). Sprint 4 grew from 6 planned to 7 effective (E4-S01 split into substrate + closer for clean commit boundaries — `8419923` then `73ccabb`). The Sprint 3 retro §5 lesson "substory expansion needs a formal trigger" was followed as a matter of practice, not policy: nothing demanded a sprint-change-proposal because nothing diverged enough.
- **E4-S04 dead-end caught and pivoted cleanly inside the story.** `e4-s04-evidence.md` §2-3 records three LiteLLM `/spend/*` endpoints returning 500 "No db connected" (stateless mode, Story 9.16 deliberately ran without Prisma) plus per-model `rpm: 1` empirically verified as a no-op router-hint without a virtual-key budget. Pivoted to the unconditional Prometheus counter `litellm_spend_metric_total{api_provider="gemini"}` and a sentinel-marker YAML comment-out throttle — both provider-independent, no DB required. ADR-008 was amended in the same commit `d4c032d` rather than tortured into matching v1 assumptions.
- **E4-S07 dry-run reached ct-dev-homelab on first try.** `e4-s07-evidence.md` §Validation outcomes: `ansible-playbook --check --limit ct-dev-homelab` returned `ok=20 changed=7 unreachable=0 failed=0`, exercised parameter validation, planned the rsync of both compose stacks, and rendered the env template — all without touching the host's docker daemon. The down-guard regression test (`tests/test-down-guard.yml`) verified the three scenarios via `block:/rescue:` (`rescued=1` is the load-bearing signal that scenario 1 correctly trips). No live host work was needed to validate the role's safety semantics.
- **E4-S08 5/5 smokes + clean rollback drill on a real host.** `e4-s08-evidence.md` Phase 3-4: `add_memory` → `search_nodes` round-trip with extracted entity nodes (Test 1), GitNexus MCP `initialize` returning `serverInfo.name=gitnexus, version=1.6.3` (Test 2), persistence after `docker restart graphiti-mcp` (Test 4), gateway-reach to ct-ai-01:4000 (Test 5). The destructive-down drill on the actual ct-dev-homelab volume captured `/srv/graphiti/data.bak.20260427T123352`, executed `docker compose down -v`, then recovered to all-three-containers-healthy via re-running `deploy-context-stack.yml` (`PLAY RECAP ok=25 changed=6 failed=0`). G-Rollback gate validated on a real host, not a localhost mock.
- **The `compose-app` role is reusable by design, not bespoke to context-stack.** Per E4-S08 evidence §Reuse note, the role takes parametric `compose_app_*` inputs and was exercised twice in the same playbook (gitnexus + graphiti). Future stacks (authelia, productivity-obsidian, AI Dev Container bundles) inherit the same `down -v` guard, `cp -a` snapshot policy, and build-vs-pull behaviour without modification. This is the seam the operator's Sprint 5+ "AI Dev Container + context-stack as a single AI-tooling package per project container" plan plugs into.
- **Mandatory Fix #2 (`down -v` guard) shipped as both spec and live-drilled implementation.** The Sprint 3 retro §7 carry-forward #2 flagged the guard spec did not visibly ship in S3. In S4 it landed as the `compose-app` role's hard `assert` (`roles/compose-app/tasks/down.yml`) plus `compose_app_force_data_loss` per-stack flag, with `cp -a` belt-and-braces, with a 3-scenario localhost regression test, AND was exercised live on ct-dev-homelab during the E4-S08 drill — three layers of verification.

## 3. What didn't go well

- **E4-S08 took two mid-deploy fixes to reach green.** `e4-s08-evidence.md` Phase 2: first `docker compose pull` failed on the locally-built `graphiti-mcp-genai-bundled:e3-s04g` image (the `compose-app` role had no build path); fixed by adding `compose_app_build_images: false` default + a build task before pull + tolerant pull (`failed_when: rc != 0 and not build_images`). Second failure: graphiti-mcp returned HTTP 401 from LLM extraction because `graphiti.env.j2` was missing `GEMINI_API_KEY` (per ADR-017 v3, graphiti's LLM extraction calls Google directly with that key, not via the LiteLLM `OPENAI_API_KEY` path used by the embedder). Both fixes were small, both committed inline, but neither was caught by the role's `--check`-mode dry-run because (a) `docker compose pull` is skipped under check_mode, (b) no health-check task asserted that the LLM-extraction path actually returned 200 before the playbook called itself done. The deploy was not quite battle-ready on first invocation.
- **Two key leaks in transcripts requiring rotation.** Operator action items §10 carries them forward. (a) `GEMINI_API_KEY` leaked in the main session transcript on disk on 2026-04-27 (Sprint 3 carry-forward §3 from kickoff, plus continued exposure during S4 work on the env-template fix). (b) `LITELLM_MASTER_KEY` leaked in the E4-S08 agent transcript (length=67 vault-resolution check is harmless; the value itself appeared in an earlier debugging step). Both keys are vault-encrypted in source control (`group_vars/all/vault.yml` post-promotion); the at-rest leak is in agent transcripts, not in the repo. Both need rotation before next session.
- **Sprint 2 evidence-pack still not backfilled.** Carry-forward from the Sprint 3 KPI scorecard's three INSUFFICIENT-DATA scores (K1, K2, K4-GitNexus) — `docs/context-stack/sprint-2/` does not exist; GitNexus MCP shows `Connected` but no week-1 KPI scorecard was ever authored. Sprint 4 did not address this directly (it's not in the §6.3 backlog) and so the gap rolls to Sprint 5 E4-S09 (weekly observability digest) per the kickoff §3 carry-forward #4.
- **Vault gap surfaced late and cost a re-deploy.** `e4-s07-evidence.md` flagged the gap pre-emptively ("E4-S08 needs to re-export `vault_litellm_master_key` into ct-dev-homelab's vault"). E4-S08 Phase 1 promoted the keys to `group_vars/all/vault.yml` rather than the per-host re-export, which is the correct architectural move (any future host inherits the keys) — but the LLM-extraction 401 wasn't surfaced until after Phase 2's first deploy because the env template's `GEMINI_API_KEY` line was added only when the 401 forced its discovery. Phase 1 succeeded mechanically (two keys promoted, lengths verified on both hosts) but didn't anticipate which template lines would consume them.
- **`cypher-replay.sh` (Mandatory Fix #1) still not shipped, even as docs-only.** Sprint 3 retro §7 carry-forward #7 said either land it in S4 or downgrade to documentation-only with RDB-restore as the operative recovery procedure. Sprint 4 did neither explicitly. ADR-007's 2026-04-27 (per-group) amendment continues to describe the Cypher export as "a parallel audit signal, not the primary recovery path"; the 2026-04-27b sub-amendment (deployment-side guard) is silent on the replay tool. The implicit decision is that RDB-restore is the operative path (validated in Sprint 3 E3-S08 at 91s downtime) and the replay tool is docs-only — but that decision is not memorialised in this retro's predecessors. Recording it explicitly here in §4.

## 4. Mandatory fixes verification

| Fix | Source | Sprint-4 outcome |
|---|---|---|
| **#1 `cypher-replay.sh`** | sprint-plan §10 / S3-prep | **NOT shipped — RDB-restore is the operative recovery path per ADR-007's 2026-04-27 per-group amendment ("RDB snapshot remains the actual point-in-time-restoration mechanism"); E3-S08 validated this at 91s downtime; Cypher tarball is docs-only.** Recommend memorialising this verdict in a one-line ADR-007 sub-amendment in S5 to close the loop. |
| **#2 `down -v` guard** | sprint-plan §10 / S3-prep | **SHIPPED as role-level guard + live-drilled.** Implementation: `roles/compose-app/tasks/down.yml` + per-stack `compose_app_force_data_loss` flag + `cp -a` belt-and-braces (`compose_app_backup_before_destructive: true` default). Regression test: `tests/test-down-guard.yml` 3-scenario localhost run with `rescued=1` as load-bearing signal. Live drill: E4-S08 Phase 4 against ct-dev-homelab — guard refused without the flag, allowed with the flag, snapshot landed at `/srv/graphiti/data.bak.20260427T123352`, recovery via re-running `deploy-context-stack.yml` succeeded (ok=25 changed=6 failed=0). |

## 5. ADR / spec amendments shipped

| ADR | Amendment | Commit | Trigger |
|---|---|---|---|
| **ADR-007** Graphiti backup strategy | Sub-amendment 2026-04-27b: deployment-side `down -v` guard (two-flag interlock + cp -a snapshot + role test path + reversal trigger) | `50563a4` | E4-S07 — codifies the deployment-layer guard above the cron-backup layer; resolves S3 carry-forward #2 |
| **ADR-008** Daily $1 hard-cap | Amendment 2026-04-27: cost source switched OpenAI Usage API → LiteLLM `/metrics` Prometheus counter (`litellm_spend_metric_total{api_provider="gemini"}`); throttle switched Graphiti SEMAPHORE_LIMIT 5→1 → LiteLLM YAML alias comment-out via sentinel markers; ntfy channel corrected (`ct101.tail-scale.ts.net` → `https://ntfy.bi-services.be/`) | `d4c032d` | E4-S04 — three follow-on amendments to ADR-002/003 in Sprint 3 stranded ADR-008 v1's OpenAI assumption |
| **ADR-008** Daily $1 hard-cap | Operator-accepted LLM-bypass cost-gap (Option A): graphiti-core's native `GeminiClient` calls `generativelanguage.googleapis.com` directly, bypassing LiteLLM; only the embedder traffic flows through the gateway and hits the counter; cap remains an effective backstop against catastrophic runaway via the proportional `add_memory` → ~10 embedder calls path; re-evaluate at S5 if monthly spend approaches $10. Three resolution paths recorded for future amendment: (A) accept gap [chosen]; (B) route LLM through gateway; (C) parallel meter via Google Cloud Billing API (24h+ delayed). | `3f48dea` | Operator decision 2026-04-27 inside the E4-S04 work — captures a known gap explicitly rather than letting it lurk |

No new ADRs authored. The amendment-in-place pattern from Sprint 3 (ADR-002, ADR-003, ADR-007, ADR-017 all amended rather than abandoned) continued cleanly through S4.

## 6. Lessons for Sprint 5

1. **Health-check tasks per stack should be authored before E2E deploy, not during.** The `compose-app` role's deploy path has a generic health probe loop (`compose_app_health_retries: 12`, `compose_app_health_delay: 5`), but it does not assert that the application's primary functional path actually works. E4-S08's 401 was caught only when the operator manually ran `add_memory` against graphiti's MCP. Recommend: each stack invocation in `deploy-context-stack.yml` (and any future stacks via the same role) declares a `compose_app_post_deploy_check` script that exercises one end-to-end functional call. The role already has the variable; nothing in Sprint 4 used it.
2. **Vault promotion to `group_vars/all/vault.yml` is the right default for cross-host secrets.** E4-S08 Phase 1 demonstrated the pattern: extract intact `!vault |` ciphertext blocks, no decrypt/re-encrypt cycle, drop into group scope. Two keys promoted, two new resolutions verified on a second host. This should be the default for any new shared secret surface — host-scope only when there's a genuine reason for per-host divergence.
3. **The reusable role pattern (`compose-app`) is validated by 2-stack invocation; ready for AI Dev Container bundle composition in Sprint 5+.** Per E4-S08 evidence §Reuse note, the seam is parametric and the operator's strategic direction (2026-04-27) is to compose new project-container provisioning playbooks as `import_playbook: deploy-context-stack.yml` after the AI Dev Container role completes. No new abstraction is needed at the role layer; the bundle composition is a Sprint 5+ orchestration question.
4. **Two-key-leak in one sprint is a signal, not noise.** Both leaks happened in agent transcripts during normal debugging (not in committed files). Recommend: rotate the two affected keys before Sprint 5 kickoff; consider whether the operator's debugging workflow should adopt a transcript-redaction default for known-secret-shaped strings (length 39, length 67) at the wrapper layer. This is a Sprint 5 process improvement, not a code change.
5. **`cypher-replay.sh` ambiguity should be closed in S5 via a one-line ADR-007 sub-amendment.** The implicit verdict is "RDB-restore is operative; Cypher export is docs-only audit signal" — record it explicitly so the Mandatory Fix #1 line item doesn't roll forward indefinitely.

## 7. Exit Gate (sprint-plan.md §6.6)

10 acceptance criteria from the sprint plan. Each scored against Sprint 4 evidence with source.

| # | Acceptance criterion | Status | Source |
|---|---|---|---|
| 1 | Wiki tree exists at `homelab-playbook/wiki/` with `index.md`, `_schema.md`, ≥3 seed entries | **PASS** | `wiki/index.md`, `wiki/_schema.md` (commits `8419923`, `73ccabb`); seeds at `wiki/architecture/{tailscale-policy,hybrid-gemma-serving}.md` and `wiki/runbooks/{pve9-ha-migration,wiki-query-skill}.md` (commit `fe77eb3` for the three drafts; `wiki-query-skill.md` from `b689e77`). Four seed pages total, all `status: draft`. |
| 2 | Each seed entry referenced by ≥1 Claude Code session (3×3 target relaxed to 3×1 per kickoff §2 SHOULD-trim) | **PARTIAL — operator-input pending** | The wiki-query skill is installed (`~/.claude/skills/wiki-query/SKILL.md`); `runbooks/wiki-query-skill.md` documents how to invoke it. Whether each of the 3 content seeds was referenced in ≥1 real Claude session is operator-side data not surfaced in evidence files. Recommend: track via the daily "did this save a re-derivation?" prompt (Sprint 3 retro §7 carry-forward #8) starting D31 — already overdue. Full 3×3 verification at S5 retro per FR-WIKI-006 SHOULD. |
| 3 | `wiki-query` skill installed; reads files in ≤200 ms | **PASS** | E4-S03 commit `b689e77`; skill at `~/.claude/skills/wiki-query/SKILL.md`; runbook at `wiki/runbooks/wiki-query-skill.md` documents read-on-demand design per ADR-009. Latency budget is the file-read time (allowed-tools=Read), trivially under 200 ms for the seed-page sizes (110-220 lines each). |
| 4 | `scripts/wiki-lint.sh` runs in pre-commit and exits 0 | **PASS (substrate)** | `scripts/wiki-lint.sh` exists (commit `73ccabb`); `scripts/install-git-hooks.sh` wires the pre-commit hook. Operator-side verification that the hook is currently *installed* on the workstation (`.git/hooks/pre-commit` shows only `pre-commit.sample` in the local repo state, but the workstation's installation may differ — installation is a one-time operator action via `install-git-hooks.sh`). The lint *runs* on the seed pages (the seeds were committed, which means either the hook passed or wasn't installed at commit time). |
| 5 | `cost-cap.sh` cron firing every 30 min; manual breach test confirms throttle + ntfy alert; auto-restore at UTC day rollover | **PASS** | E4-S04 evidence §6 (cron registered with verbatim file content); §7.1-7.4 (breach + restore + ntfy proven end-to-end without burning real spend, ~$1e-5 used). Throttle mechanism is the YAML comment-out (HTTP 400 path), not the v1 SEMAPHORE_LIMIT. ADR-008 v1's "drop SEMAPHORE_LIMIT to 1" is superseded by the amendment. |
| 6 | `ai-dev-context-stack` Ansible role exists; deploys end-to-end on ct-dev-homelab; `verify.yml` exits 0 | **PASS (substantively met)** | Role naming pivoted to `compose-app` (generic-by-design per operator direction) rather than the `ai-dev-context-stack` placeholder name; the spec is met because the role *deploys* the context stack via `deploy-context-stack.yml`. End-to-end deploy on ct-dev-homelab: `ok=25 changed=6 failed=0` post-fixes (E4-S08 Phase 2). No separate `verify.yml` was authored — verification lives in the playbook's health-check loop and the explicit smoke runner (`/tmp/e4-s08-smoke.py`). The substantive intent (deploy succeeds + verification runs) is met. |
| 7 | **Mandatory Fix #2 verified:** rollback playbook refuses `down -v` without explicit flag OR auto-`cp -a` first | **PASS (both belts AND braces)** | E4-S07 role + test (`rescued=1` regression). E4-S08 Phase 4 live drill on ct-dev-homelab — guard refused without flag (full failure-message captured); allowed with flag; `cp -a` snapshot at `/srv/graphiti/data.bak.20260427T123352` retained. Both safety mechanisms verified live, not just in unit test. |
| 8 | 5 smoke tests on ct-dev-homelab pass (3-of-5 hard-pass + 2-of-5 quality lenient per ADR-014 SHOULD) | **PASS (5/5)** | E4-S08 Phase 3 — all five PASS: graphiti add+search round-trip with extracted entity nodes; gitnexus MCP initialize; cross-stack liveness; persistence after restart (FalkorDB AOF replay verified); cost-cap/LiteLLM gateway reach. Comfortably above the lenient threshold. |
| 9 | Rollback drill exercised once on ct-dev-homelab; returns to pre-deploy state in ≤1 day operator-wall-time | **PASS (under 1 hour wall-time)** | E4-S08 Phase 4 — drill executed and recovery via `deploy-context-stack.yml` re-run completed within the same evidence-bearing commit window (final commit `0a4a096` at 12:36 UTC, drill happened minutes before). Operator-wall-time well under 1 day. |
| 10 | Sprint retro authored. `hybrid_gemma_serving` status confirmed for S5 planning | **PASS — this document.** `hybrid_gemma_serving` status: see §8 below. |

**Exit Gate verdict: PASS.** All 10 acceptance criteria PASS or substantively-met PASS. Zero FAIL. AC2 carries an operator-input-pending note (3×1 verification deferred to S5 retro per kickoff §2 SHOULD-trim). AC4 substrate ships; operator-side hook installation is one-shot. AC6 substantively met under the `compose-app` rename. The literal "ai-dev-context-stack" naming was the original placeholder; the executed deliverable (a parametric, reusable compose-stack role) is broader and better.

## 8. FR-LLM-007 gate verdict

**Verdict: Operator-input pending — flag for operator to resolve before S5 kickoff.**

### Why this is operator-input territory

Per sprint-plan.md §6.7: "If `hybrid_gemma_serving` not in beta by S4 retro: S5 LiteLLM stories defer per FR-LLM-007; S5 reshapes to product-finalisation only."

What "in beta" means in this product's vocabulary is undefined in the planning artefacts. The PRD's FR-LLM-007 deferral path is binary (defer to backlog or proceed); it does not specify a maturity rubric. The operator-side reality the wiki seed page captures (commit `fe77eb3`, `wiki/architecture/hybrid-gemma-serving.md`):

- **Deployed today on ct-ai-01:** `gemma-hybrid-proxy` (FastAPI, llama.cpp Vulkan) + LiteLLM gateway aliases (`gemma4-26b-text`, `gemma4-e4b-vision`, `gemma4-26b-json`, `gemma4-auto`). Serving OWUI + ad-hoc dev clients (Hermes, Continue) per the wiki page.
- **NOT on the Graphiti hot path.** Per ADR-002 + ADR-017 amendments (2026-04-27), Graphiti's LLM extraction was pivoted from local Gemma to cloud `gemini-2.5-flash-lite` after the E3-S04a..e arc burned 4 substories on integration failures. The "LiteLLM stories" in S5 (E4-S05 + E4-S06) are about routing Graphiti's LLM call through `OPENAI_BASE_URL` → LiteLLM → `hybrid_gemma_serving` — i.e., reversing the cloud pivot via the gateway.

For S5 LiteLLM scope to proceed as planned (Path A), the operator must affirm:

1. `hybrid_gemma_serving` is reachable from ct-ai-01 (graphiti host) AND from ct-dev-homelab (deploy host) at a stable LiteLLM gateway URL.
2. The local Gemma path can pass the FR-LLM-005 95%-well-formed-JSON gate on the 50-fact validation set (E4-S06's binding test). The Sprint 3 evidence (E3-S04a..e) suggests local Gemma's JSON-mode under `OpenAIGenericClient` was *not* well-formed at production-prompt length; whether the current `gemma-hybrid-proxy` + LiteLLM aliases shape resolves that is uncertain.
3. Operator wants to attempt the cloud→local pivot in S5 rather than consolidate on the cloud-Gemini Graphiti path that is currently working at $1-3/month.

If the operator says "yes" to (1) AND "I want to try" on (2)+(3): **Path A — S5 LiteLLM scope proceeds as planned.** E4-S05 spike runs first (1.7 wc-d), then E4-S06 50-fact validation gates the rest (FR-LLM-006 auto-fallback if <95%).

If the operator says "no, hold on the cloud-Gemini path until next product cycle": **Path B — S5 LiteLLM scope deferred per FR-LLM-007.** E4-S05 + E4-S06 to backlog (~4.2 wc-d saved); S5 reshapes per sprint-plan §7.2 (inline-tighten 6 vague ACs ~0.5d; +2-3 additional wiki seeds ~1d; consolidate weekly observability digests into 4-week trend ~0.5d; optional `hybrid_gemma_serving` pre-integration spike ~1.5d).

If the operator wants to think about it (most likely): **Operator-input pending.** Flag this gate at S5 kickoff (D41); decision recorded explicitly in the S5 kickoff doc; backlog ticket created either way.

**Default recommendation: defer the call to S5 kickoff (D41).** This sprint's evidence is sufficient to PASS the Exit Gate without resolving FR-LLM-007 — the gate is a Sprint 5 *scope* question, not a Sprint 4 *outcome* question. Documenting it as "operator-input pending" preserves both options without false precision.

## 9. Carry-forward to Sprint 5

Per sprint-plan §7, Sprint 5 carries:

**Path A or Path B (decision at S5 kickoff per §8 above):**
- E4-S05 LiteLLM bridge config (Path A only)
- E4-S06 50-fact LiteLLM JSON validation gate (Path A only)

**Both paths:**
- E4-S09 Weekly observability digest (~0.5d; absorbs the GitNexus K1/K2/K4 backfill from S3)
- E4-S10 Unified query hierarchy + exit ramps doc (~1d)
- E4-S11 Product-level KPI scorecard (the binding gate per PRD §11)
- E4-S12 Phase-4 retro + product close

**Plus operator action items still open** (full list in §10).

## 10. Operator action items (rolling list — most-urgent first)

1. **Rotate `LITELLM_MASTER_KEY`** — leaked in E4-S08 agent transcript (length=67 vault-resolution check exposed shape; full value visible in earlier debugging step). Rotate, re-vault, re-deploy via `litellm-gateway` role + `compose-app` invocation.
2. **Rotate `GEMINI_API_KEY`** — transcript exposure 2026-04-27 (Sprint 3 carry-forward + continued S4 exposure during env-template fix). Rotate, re-vault into `group_vars/all/vault.yml`, re-deploy.
3. **Restic source set** → `~/.local/state/graphiti-backup/` (Sprint 3 carry-forward #1; not done in S4 — workstation-loss event currently loses every backup).
4. **Preserved data dir cleanup** — `sudo rm -rf ~/.graphiti-data.preserved-by-e3-s08` on/after 2026-04-28 (24h post-drill safety window, Sprint 3 carry-forward #2).
5. **`/srv/graphiti/data.bak.20260427T123352`** on ct-dev-homelab — clean up after 24h if stack stable (E4-S08 Phase 4 drill artefact; intentional no-auto-GC per role's safety design).
6. **E4-S02 wiki seed promotion** (`status: draft` → `status: stable`) — operator review of the three seed pages (`tailscale-policy`, `pve9-ha-migration`, `hybrid-gemma-serving`) before flipping. Small content-review task, no code.
7. **FR-LLM-007 gate decision** (this retro's §8) — Path A vs Path B vs operator-input-pending → resolved at S5 kickoff D41. Default: pending.
8. **GitNexus K1/K2/K4 backfill** (Sprint 3 KPI scorecard carry; folded into S5 E4-S09 weekly observability digest).
9. **`cypher-replay.sh` final disposition** — recommend memorialising "RDB-restore is operative; Cypher export is docs-only audit" via a one-line ADR-007 sub-amendment in S5 (closes Mandatory Fix #1 line item). Already operative in practice per E3-S08 evidence; missing only the explicit ADR sentence.
10. **AR8 `tom-personal` namespace one-off probe** (Sprint 3 carry-forward #4; deferred again in S4 — neither E4-S04 nor E4-S08 touched the default-group AR). Small probe at S5 kickoff.
11. **FalkorDB RSS snapshot at end of S4** (Epic E3 AC6 carry; not surfaced in Sprint 3 evidence and not captured in S4 either). `docker stats graphiti-falkordb` on ct-dev-homelab (and on workstation if still running).
12. **SEMAPHORE_LIMIT and telemetry-off re-confirmation** (Epic E3 AC8 carry; still not cited explicitly in evidence as of S4 close).
13. **Daily "did this save a re-derivation?" prompt** (Sprint 3 carry-forward #8) — start adding to operator daily retro template at S5 D41 latest, so K6 has 4 weeks of operator-tagged data before the binding S5 product gate (E4-S11).

## 11. Story count: planned vs actual

| Tier | Stories |
|---|---|
| **Planned in sprint-plan §6.3** | E4-S01, S02, S03, S04, S07, S08 = **6 stories** |
| **Substory split (clean commit boundary, not scope expansion)** | E4-S01 → E4-S01 substrate (commit `8419923`) + E4-S01 closer (commit `73ccabb`, lint-script + pre-commit + .gitkeeps) | +1 |
| **Mid-sprint substory expansions (E3-S04-style)** | none | 0 |
| **Investigation/fix substories late in sprint** | none | 0 |
| **Total effective stories executed** | 6 planned + 1 split = **7 effective** | — |

**Headline: 6 planned → 7 effective.** Compare Sprint 3: 9 planned → ~17 effective. Sprint 4 ran cleaner by ~10 stories of unplanned work. The Sprint 3 retro §5 lesson "substory expansion needs a formal trigger" was respected by the absence of triggers — nothing forced an expansion. The E4-S04 LiteLLM `/spend/*` 500-error pivot, the E4-S07 vault gap, and the E4-S08 build-path + GEMINI_API_KEY fixes were all absorbed inside their parent stories rather than spawning sub-IDs.

## 12. Time spent

Sprint 4 first commit `0a4f02d` (sprint-4-kickoff) — **2026-04-27 10:47 UTC**.
Sprint 4 final commit `fe77eb3` (E4-S02 seed entries) — **2026-04-27 13:01 UTC**.

Elapsed: **~2 hours 14 minutes wall-clock**, single calendar day, no boundary crossed.

This is **dramatically faster than the sprint plan's ~14 wall-clock-day estimate** (sprint-plan.md §6.3) and even faster than Sprint 3's ~18-hour intensive single-day push. Sprint 4 was tighter than Sprint 3 because:

1. **No architectural pivots.** Sprint 3 burned ~70 minutes (commits `7b2f52e` → `add0611`) on the Gemma-local → cloud-Gemini arc inside E3-S04. Sprint 4 had zero equivalents. The E4-S04 LiteLLM cost-source pivot was 500-error → endpoint-decision in one work session, not a multi-substory arc.
2. **No spike re-runs.** Sprint 3 carried E3-S01.5, S01.5b, S01.5c spike re-runs on top of the planned scope. Sprint 4 had none.
3. **The deploy target was real-host-ready.** ct-dev-homelab was already in `[dev_hosts]` at 192.168.50.156; per-host vars + vault file already existed at `inventories/homelab/host_vars/ct-dev-homelab/`. Sprint 4 needed two additions (group-scope vault promotion + `GEMINI_API_KEY` env line) — both small.

The velocity-calibration mechanism in sprint-plan.md §8 is still unexercised; no `velocity-log.md` row appended for S1-S4 yet. Recommend appending all four rows in one post-S5-retro pass with honest per-sprint multipliers, since the "wall-clock-day" denominator the plan assumed (~3 hrs/day side-project cadence) is now empirically wrong by an order of magnitude. The plan's 1.7× multiplier was conservative; actual is closer to 0.1×-0.2× when the operator runs concentrated single-day pushes. Sprint 5 is not constrained by buffer arithmetic; it's constrained by the FR-LLM-007 decision and operator concentration availability.

## 13. Recommendation for Sprint 5 retro structure

Carrying forward this sprint's process insights:

- **Add a "mid-deploy fix log" subsection to evidence files for any deploy-bearing story.** E4-S08's two mid-deploy fixes (build path, env var) were captured cleanly in §Anything unexpected and §Phase 2, but a dedicated "fixes applied during deploy" table would make it easier to retro-spot deploy-readiness gaps. Sprint 5's E4-S05/S06 LiteLLM bridge work (Path A) will plausibly emit similar mid-flight fixes; pre-format the section.
- **Carry the `velocity-log.md` backfill into S5 E4-S12 retro (product close).** Sprint 4 confirmed the 1.7× multiplier is wrong by an order of magnitude for concentrated pushes; the velocity log should reflect that honestly so the *next* product's planning is calibrated against reality, not the side-project assumption.
- **Resolve FR-LLM-007 explicitly at S5 kickoff (D41), not at retro.** This sprint's retro §8 documents the gate as operator-input-pending; if S5 starts without resolution, the first Path-A story (E4-S05) and the first Path-B alternative (inline-tighten vague ACs) cannot both be queued. The gate must flip before story-1 work starts.

---

**End of retro.** This document is the Sprint 4 Exit Gate, the formal sprint close, and the FR-LLM-007 gate-flag for the operator. Sprint 5 GO is contingent on §8 resolution; Sprint 5 scope is contingent on Path A vs Path B.
