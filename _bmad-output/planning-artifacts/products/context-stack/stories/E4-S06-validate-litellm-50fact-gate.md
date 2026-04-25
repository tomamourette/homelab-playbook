---
type: story
epic: E4
id: E4-S06
title: "Validate Phase-4 LiteLLM extraction-JSON quality on 50-fact set (≥95% gate)"
size: 1.5d
priority: MUST
fr_refs: [FR-LLM-005, FR-LLM-006, FR-LLM-008]
adr_refs: [ADR-011]
status: draft
date: 2026-04-25
---

# E4-S06: Validate Phase-4 LiteLLM extraction-JSON quality on 50-fact set (≥95% gate)

## User Story

As **tomamourette** (homelab operator), I want **a 50-fact validation set fed through Graphiti's bridged LiteLLM path (E4-S05), with each fact's extraction inspected for well-formed JSON (no `JSONDecodeError`, no `Cypher error: invalid relation`); the bridge is promoted to Phase 4 acceptance ONLY if ≥ 95% of episodes extract cleanly (FR-LLM-005), and otherwise auto-falls back to cloud `gpt-4o-mini` by reverting `OPENAI_BASE_URL` (FR-LLM-006); the FR-LLM-008 single-day reversibility is independently re-exercised**, so that **the architectural safety net (ADR-011 §Validation gate) is enforced before ANY week-4 KPI scorecard depends on the bridge**.

## Background and Context

ADR-011 §Validation gate is explicit: 50 representative episode prompts, fed through Graphiti's bridged config, measure % well-formed extractions (the "well-formed" bar is "no `JSONDecodeError` AND no `Cypher error: invalid relation` in `docker compose logs graphiti-mcp`"). ≥ 95% pass = promote; otherwise revert. FR-LLM-005 is **MUST**; this gate is non-negotiable.

If the gate fails, FR-LLM-006 / NFR-AVAIL-003 mandate auto-fallback (ENV revert) — same single env-var change as E4-S05 AC8. Phase 4 then closes as **deferred** with documented reason; the rest of E4 ships unaffected (Phase 1-3 already proven in E2/E3).

This story is the **architectural safety net** — the entire LiteLLM bet rests on this gate working. AR2 + AR5 from architecture §11 both surface here. Per the special note in the brief, "the validation gate at S06 is critical — if it fails, Phase 4 falls back to cloud-only and S06 documents that. Don't skip the gate; it's the architectural safety net."

The 50-fact corpus source resolves EQ5 (epics.md §9): **handcrafted operator set distilled from existing project memory notes** — preserves coverage breadth, controls quality, and avoids leaking sensitive material that may exist in real Graphiti episodes.

## Acceptance Criteria

### AC1: 50-fact validation corpus is authored and committed

- **Given** the corpus is to be assembled from existing project memories (operator-handcrafted; closes EQ5)
- **When** I look at the repo
- **Then** `homelab-playbook/_bmad-output/planning-artifacts/products/context-stack/tests/litellm-50-fact-corpus.jsonl` exists with exactly 50 lines; each line is a JSON object with `id`, `name`, `episode_body`, `source` (always `"text"`), `source_description`, `group_id` (always `"phase-4-validation"` — distinct from `tom-personal` to keep validation writes isolated), and `expected_entity_count` (operator's expected number of entities Graphiti should extract — 1-3 typical); `git diff --stat` shows the file added; `wc -l` confirms 50 lines

### AC2: Corpus distribution covers the breadth of operator memory categories

- **Given** AC1 holds
- **When** I tally the corpus by category (column derivable from `source_description` prefix)
- **Then** distribution is approximately: 12 architectural decisions (e.g., "ADR-style: on date X we chose Y over Z"), 12 dated decisions (e.g., "On 2026-04-24 we did W"), 8 lessons-learned (e.g., "Lesson: do not run X before Y"), 8 supersession trails (e.g., "Decision A superseded by decision B on date C"), 6 project-state changes (e.g., "ct-foo moved from pve1 to pve3"), 4 bi-temporal stress-tests (facts with explicit `valid_at` differing from `created_at`); rationale documented as a comment block at the top of the JSONL is acceptable (or in a sibling `litellm-50-fact-corpus.README.md`)

### AC3: Validation harness exists and runs the corpus through bridged Graphiti

- **Given** E4-S05 has the bridge active
- **When** I run `bash homelab-playbook/scripts/run-litellm-validation.sh` (this story creates the script)
- **Then** the script: (a) confirms the bridge is active by checking `OPENAI_BASE_URL` in `/srv/graphiti/.env` over SSH; (b) iterates the 50-fact corpus, calling `add_episode` via the MCP HTTP transport for each (or via `mcp__graphiti__add_episode` round-trips through Claude Code if MCP-CLI access is preferred); (c) collects `docker compose logs graphiti-mcp --since <window>` after each call; (d) parses each fact's outcome as PASS/FAIL with the fail reason (regex `JSONDecodeError|Cypher error: invalid relation|Failed to extract`); (e) writes per-fact results to `homelab-playbook/_bmad-output/planning-artifacts/products/context-stack/tests/litellm-50-fact-results-<ISO-DATE>.jsonl`; (f) writes a summary line to stdout

### AC4: Pass rate is computed and gate decision is recorded

- **Given** AC3 ran
- **When** I read the results JSONL
- **Then** the script's stdout summary states: `passed=<N>`, `failed=<50-N>`, `pass_rate=<PCT>%`, `gate=PASS` if `PCT ≥ 95%` else `gate=FAIL`; an additional summary file at `tests/litellm-50-fact-summary-<ISO-DATE>.md` captures pass rate, top 3 failure modes (counted), per-category breakdown, and the gate decision

### AC5: If gate PASSES — bridge stays active and Phase 4 promotes

- **Given** AC4 reports `gate=PASS`
- **When** I record the result
- **Then** (a) `homelab-playbook/wiki/projects/hybrid-gemma-serving.md` is updated to `status: stable`, `last_reviewed=<today>`, and the body adds a "Phase 4 LiteLLM bridge validated 2026-04-XX, pass rate XX%" line; (b) the validation summary file is referenced from the wiki page; (c) the bridge config in `/srv/graphiti/.env` is left active for E4-S08 / E4-S09 to consume; (d) the validation `group_id="phase-4-validation"` writes are cleaned up via `mcp__graphiti__clear_graph(group_id="phase-4-validation")` so they don't pollute KPI K4 facts/week measurement

### AC6: If gate FAILS — auto-fallback fires (FR-LLM-006)

- **Given** AC4 reports `gate=FAIL`
- **When** the script reaches its terminal block
- **Then** the script automatically: (a) runs `sudo cp /srv/graphiti/.env.phase-3-backup /srv/graphiti/.env && cd /srv/graphiti && sudo docker compose up -d --no-deps graphiti-mcp` over SSH; (b) emits a log line `gate=FAIL → auto-fallback executed` to stdout AND to `journalctl -t graphiti-litellm-validation`; (c) fires an ntfy push to `http://ct101.tail-scale.ts.net/graphiti-alerts` with `Title: Graphiti LiteLLM gate FAILED` and `Priority: high`; (d) `homelab-playbook/wiki/projects/hybrid-gemma-serving.md` is updated to `status: superseded`, with body recording the failure date, pass rate, and revert action

### AC7: If gate FAILS — backlog item documents the recovery path

- **Given** AC6 fired
- **When** the operator authors the post-mortem entry
- **Then** `homelab-playbook/_bmad-output/planning-artifacts/products/context-stack/backlog/phase-4-litellm-gate-failure-<ISO-DATE>.md` exists with: pass rate, top 3 failure-mode regex patterns, sample failed `episode_body` examples, two candidate next-steps (option A: fallback to ADR-011 alt path — side-by-side LiteLLM proxy with chat-completions-only; option B: defer Phase 4 indefinitely per FR-LLM-007) — operator picks which to pursue at retro

### AC8: FR-LLM-008 reversibility re-exercised independently of validation flow

- **Given** the bridge is active (assume AC5 path) post-validation
- **When** I separately run `time bash homelab-playbook/scripts/run-litellm-revert.sh` (a thin wrapper that does `cp .env.phase-3-backup .env && docker compose up -d --no-deps graphiti-mcp`)
- **Then** wall-clock total is ≤ 60 s; post-revert: `add_episode` probe succeeds against cloud `gpt-4o-mini`; tcpdump confirms LLM traffic now hits `api.openai.com` only (NOT LiteLLM gateway). Re-apply the bridge after the drill so subsequent E4 stories run against the validated config

### AC9: Cost-neutrality check is started (NFR-COST-003 7-day window)

- **Given** AC5 path (bridge active)
- **When** the validation completes
- **Then** the day-of-validation OpenAI spend is recorded in `tests/litellm-50-fact-summary-<ISO-DATE>.md` as the **start of the 7-day pre/post comparison window**; E4-S09 weekly digest will pick up the post-validation 7-day spend and report cost-neutrality at E4-S11

### AC10: Validation harness is idempotent and can be re-run

- **Given** AC3 ran once
- **When** I re-run `bash homelab-playbook/scripts/run-litellm-validation.sh` an hour later
- **Then** it: (a) detects the prior run via timestamped output files and refuses unless `--force` is passed; (b) with `--force`, isolates the new run via `group_id="phase-4-validation-<ISO-TS>"` so prior validation writes are preserved; (c) the cleanup at AC5 step (d) targets the most recent run's group_id only; (d) repeated runs add results files (one per run) — they don't overwrite

### AC11: Deferred-from-S05 path: AC1-AC10 are NOT executed; story closes as deferred

- **Given** E4-S05 closed as `status: deferred` via its AC2 (gateway unreachable)
- **When** I look at this story
- **Then** I close it as `status: deferred` with frontmatter date, link to S05 deferral evidence, and a note in `backlog/phase-4-deferred.md` consolidating both stories under one ticket

## Implementation Notes

### Corpus authoring approach

50 facts handcrafted from these source memory notes (operator-distilled; tag each fact with the source for traceability):

- `project_pve3_storage_redesign.md`: 4-5 dated decisions + supersessions
- `project_hybrid_gemma_serving.md`: 3-4 architectural decisions
- `project_pve2_window_b_in_progress.md`: 3-4 dated decisions + lessons
- `project_pve9_ha_rules_migration.md`: 2-3 architectural decisions + 1 lesson
- `feedback_yaml_block_scalar_regex.md`: 1 lesson
- `feedback_pve9_ha_error_recovery.md`: 1 lesson
- `feedback_correct_fix.md`: 1 lesson
- `project_sparkle_cps.md`: 2-3 project-state facts
- `project_quant_trading.md`: 2 dated decisions
- `project_storage_monitoring.md`: 2-3 architectural decisions
- `project_phone_notifications_tailscale.md`: 1-2 architectural decisions
- `project_ai_dev_container.md`: 4-5 supersession-style facts (Epic-by-Epic transitions)
- `project_deployment_state.md`: 1-2 project-state facts
- 4 bi-temporal stress-tests fabricated for the test (e.g., `valid_at=2026-04-01`, `created_at=2026-04-25`, fact about a decision that was made earlier but recorded later)

Each fact's `episode_body` is 1-3 sentences, ~50-150 tokens. Avoid PII; redact specific IPs / API keys / hostnames if any leak in (use placeholders like `<host>`).

### `homelab-playbook/scripts/run-litellm-validation.sh` (sketch)

```bash
#!/usr/bin/env bash
set -euo pipefail
SSH_HOST="${SSH_HOST:-ct-ai-01.tail-scale.ts.net}"
CORPUS="${CORPUS:-_bmad-output/planning-artifacts/products/context-stack/tests/litellm-50-fact-corpus.jsonl}"
TS=$(date -u +%Y-%m-%dT%H%M%SZ)
RESULTS_DIR="_bmad-output/planning-artifacts/products/context-stack/tests"
RESULTS="$RESULTS_DIR/litellm-50-fact-results-$TS.jsonl"
SUMMARY="$RESULTS_DIR/litellm-50-fact-summary-$TS.md"
GROUP="phase-4-validation"
[ "${1:-}" = "--force" ] && GROUP="phase-4-validation-$TS"

# Pre-flight: bridge active?
ssh "$SSH_HOST" "grep -c '^OPENAI_BASE_URL=http://hybrid-gemma-litellm' /srv/graphiti/.env" | grep -q '^1$' || {
  echo "FAIL: bridge not active at $SSH_HOST"; exit 2
}

PASS=0; FAIL=0
while IFS= read -r line; do
  ID=$(echo "$line" | jq -r .id)
  # Snapshot logs window
  LOG_START=$(ssh "$SSH_HOST" 'date -u +%s')
  # Issue add_episode via MCP HTTP; group_id forced to validation
  PAYLOAD=$(echo "$line" | jq --arg g "$GROUP" '.group_id=$g | del(.expected_entity_count)')
  RESPONSE=$(curl -fsSL -m 30 -X POST \
    -H "Content-Type: application/json" \
    -d "{\"jsonrpc\":\"2.0\",\"id\":\"$ID\",\"method\":\"tools/call\",\"params\":{\"name\":\"add_episode\",\"arguments\":$PAYLOAD}}" \
    http://ct-ai-01.tail-scale.ts.net:8000/mcp/ || echo '{"error":"http_fail"}')
  sleep 2  # let logs flush
  LOG_END=$(ssh "$SSH_HOST" 'date -u +%s')
  LOGS=$(ssh "$SSH_HOST" "docker compose -f /srv/graphiti/docker-compose.yml logs --since ${LOG_START}s --until ${LOG_END}s graphiti-mcp 2>&1")

  if echo "$RESPONSE" | jq -e '.result.uuid // .result' >/dev/null 2>&1 \
     && ! echo "$LOGS" | grep -qE 'JSONDecodeError|Cypher error: invalid relation|Failed to extract'; then
    PASS=$((PASS+1))
    echo "{\"id\":\"$ID\",\"result\":\"PASS\"}" >> "$RESULTS"
  else
    FAIL=$((FAIL+1))
    REASON=$(echo "$LOGS" | grep -oE 'JSONDecodeError|Cypher error: invalid relation|Failed to extract' | head -1)
    echo "{\"id\":\"$ID\",\"result\":\"FAIL\",\"reason\":\"${REASON:-http_or_unknown}\"}" >> "$RESULTS"
  fi
done < "$CORPUS"

PCT=$(echo "scale=2; $PASS * 100 / 50" | bc)
GATE="FAIL"
[ "$PASS" -ge 48 ] && GATE="PASS"   # 48/50 = 96%; safer rounding than 95.0% strict

echo "passed=$PASS failed=$FAIL pass_rate=${PCT}% gate=$GATE" | tee -a "$SUMMARY"
{
  echo "# LiteLLM 50-fact validation — $TS"
  echo "- pass=$PASS / 50  (${PCT}%)"
  echo "- gate=$GATE  (threshold ≥ 95% / 48 of 50)"
  echo "- group_id=$GROUP"
  echo
  echo "## Top failure modes"
  jq -r 'select(.result=="FAIL")|.reason' "$RESULTS" | sort | uniq -c | sort -rn | head -3
} >> "$SUMMARY"

if [ "$GATE" = "FAIL" ]; then
  ssh "$SSH_HOST" 'sudo cp /srv/graphiti/.env.phase-3-backup /srv/graphiti/.env && cd /srv/graphiti && sudo docker compose up -d --no-deps graphiti-mcp'
  curl -fsSL -m 10 \
    -d "Phase-4 LiteLLM gate FAILED: pass_rate=${PCT}% (<95%). Auto-fallback executed; Graphiti reverted to gpt-4o-mini." \
    -H "Title: Graphiti LiteLLM gate FAILED" -H "Priority: high" \
    http://ct101.tail-scale.ts.net/graphiti-alerts || true
  logger -t graphiti-litellm-validation "gate=FAIL pct=$PCT auto-fallback executed"
  exit 6
fi

# Cleanup successful-validation writes from the validation group
curl -fsSL -m 30 -X POST -H "Content-Type: application/json" \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"tools/call\",\"params\":{\"name\":\"clear_graph\",\"arguments\":{\"group_id\":\"$GROUP\"}}}" \
  http://ct-ai-01.tail-scale.ts.net:8000/mcp/

echo "Validation complete. Results: $RESULTS, Summary: $SUMMARY"
```

### `homelab-playbook/scripts/run-litellm-revert.sh` (sketch — for AC8 drill)

```bash
#!/usr/bin/env bash
set -euo pipefail
SSH_HOST="${SSH_HOST:-ct-ai-01.tail-scale.ts.net}"
ssh "$SSH_HOST" 'test -f /srv/graphiti/.env.phase-3-backup' || { echo "FAIL: no backup"; exit 1; }
ssh "$SSH_HOST" 'sudo cp /srv/graphiti/.env.phase-3-backup /srv/graphiti/.env && cd /srv/graphiti && sudo docker compose up -d --no-deps graphiti-mcp'
echo "reverted at $(date -u +%FT%TZ)"
```

### Why 95%, why 50

Per ADR-011 §Decision: 50 episodes is large enough to surface systematic JSON-quality issues (one bad-prompt-template hits multiple facts; 50 catches that) and small enough to run end-to-end in ~30 minutes without burning meaningful spend (each episode is ~50-150 tokens × $local-or-cloud-model pricing; total spend on a 50-fact run is < $0.10). 95% threshold reflects the "5% malformed-tolerance" assumption in FR-LLM-006: above 5% bad output, the bridge is not safe for production use and Phase 1-3 cloud `gpt-4o-mini` is materially better.

### Why `group_id="phase-4-validation"` (not `tom-personal`)

Validation writes pollute the operator's `tom-personal` namespace if they go there. Isolating them via a dedicated group_id (a) keeps K4 facts/week measurement clean (E4-S11), (b) makes cleanup trivial (`clear_graph(group_id="phase-4-validation")`), (c) aligns with FR-MEM-005 namespace discipline (AR8 from arch §11).

### NOT in scope

- Doesn't modify the corpus mid-run.
- Doesn't measure end-to-end query quality (e.g., `search_facts` recall after extraction) — that's K5 / E4-S11.
- Doesn't compare local-vs-cloud quality side-by-side — only validates the local path against the absolute threshold.

## Test Plan

**Pre-flight (parallel; one Bash block):**
```bash
# Confirm E4-S05 left the bridge active
ssh ct-ai-01.tail-scale.ts.net 'grep -c "^OPENAI_BASE_URL=http://hybrid-gemma-litellm" /srv/graphiti/.env'   # 1
ssh ct-ai-01.tail-scale.ts.net 'docker compose -f /srv/graphiti/docker-compose.yml ps graphiti-mcp'        # Up
# Phase-3 backup exists
ssh ct-ai-01.tail-scale.ts.net 'ls -l /srv/graphiti/.env.phase-3-backup'
# Workstation MCP wiring
claude mcp list | grep graphiti
```

**Author corpus and harness:**
```bash
# Edit/Write the corpus JSONL (see distribution spec in AC2)
# Edit/Write the harness scripts run-litellm-validation.sh and run-litellm-revert.sh (chmod +x)
```

**Run validation:**
```bash
bash homelab-playbook/scripts/run-litellm-validation.sh
# Inspect results
cat _bmad-output/planning-artifacts/products/context-stack/tests/litellm-50-fact-summary-*.md
# Check ntfy if FAIL fired
journalctl -t graphiti-litellm-validation | tail -5
```

**AC verification (PASS path):**
```bash
# AC1
wc -l _bmad-output/planning-artifacts/products/context-stack/tests/litellm-50-fact-corpus.jsonl   # 50
# AC2 (manual category tally; document in summary)
jq -r .source_description tests/litellm-50-fact-corpus.jsonl | sort | uniq -c
# AC3 + AC4 (already ran; check files exist)
ls -la tests/litellm-50-fact-{results,summary}-*.{jsonl,md}
# AC5 (wiki update)
yq '.status, .last_reviewed' homelab-playbook/wiki/projects/hybrid-gemma-serving.md
bash homelab-playbook/scripts/wiki-lint.sh
# AC8 (revert drill)
time bash homelab-playbook/scripts/run-litellm-revert.sh   # ≤ 60s
ssh ct-ai-01.tail-scale.ts.net 'sudo timeout 30 tcpdump -nn -c 50 "host hybrid-gemma-litellm.tail-scale.ts.net"' &
script -q -c "claude -p 'add_episode: post-revert canary'" /tmp/e4-s06-revert-test.log
wait
# Re-apply bridge for downstream stories
ssh ct-ai-01.tail-scale.ts.net 'sudo install -o root -g root -m 600 /path/to/.env.phase-4 /srv/graphiti/.env && cd /srv/graphiti && sudo docker compose up -d --no-deps graphiti-mcp'
# AC10 (idempotency)
bash homelab-playbook/scripts/run-litellm-validation.sh && echo "should fail without --force"
bash homelab-playbook/scripts/run-litellm-validation.sh --force
```

**AC verification (FAIL path):**
```bash
# AC6 — script auto-fired the revert; verify
ssh ct-ai-01.tail-scale.ts.net 'grep -c "^OPENAI_BASE_URL=" /srv/graphiti/.env'   # 0 (reverted)
journalctl -t graphiti-litellm-validation | grep gate=FAIL
# AC7 — backlog written
ls _bmad-output/planning-artifacts/products/context-stack/backlog/phase-4-litellm-gate-failure-*.md
# AC4 reads gate=FAIL
cat tests/litellm-50-fact-summary-*.md | grep gate=
```

**Rollback (story-level):**
```bash
# If the validation run polluted Graphiti somehow
curl -X POST -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"clear_graph","arguments":{"group_id":"phase-4-validation"}}}' http://ct-ai-01.tail-scale.ts.net:8000/mcp/
# If the bridge state is wrong, run revert
bash homelab-playbook/scripts/run-litellm-revert.sh
```

## Dependencies

- **Blocks:** E4-S07 (Ansible role bakes in the validated config OR the deferral); E4-S09 (weekly digest tracks NFR-COST-003 7-day window); E4-S11 (KPI scorecard depends on knowing whether bridge is active or rolled back)
- **Blocked by:** E4-S05 (bridge plumbing must be in place; if S05 deferred, this story executes AC11 deferral)

## Risks and Mitigations

| Risk | Source | Mitigation |
|---|---|---|
| Local model produces malformed JSON above 5% threshold (AR2) | ADR-011 / brief R3 | The whole point of this story; AC6 auto-fallback fires; FR-LLM-007 makes Phase 4 stretch — Phase 1-3 ships unaffected |
| Validation corpus has too few stress-test edge cases → false PASS | Corpus design | AC2 distribution mandates breadth across categories including 4 bi-temporal stress tests; per-failure-mode breakdown in summary catches systematic gaps |
| LiteLLM gateway timeout during run (network blip) | Network | Script's `curl -m 30` per call; transient HTTP fail counts as FAIL (conservative); AC10 idempotency lets operator re-run after fixing the gateway |
| Validation writes leak into `tom-personal` namespace if `group_id` env not honored | Graphiti config | AC1 forces `group_id` in the corpus and AC3 harness re-injects it per call; AC5 cleanup targets `phase-4-validation` only — `tom-personal` is untouched |
| Cost spike during the 50-fact run if the local model is unexpectedly costly | Phase 4 economics | 50 episodes × ~150 tokens each is low-volume; even on cloud `gpt-4o-mini` that's < $0.10. Local-LLM run via `hybrid_gemma_serving` is essentially $0 |
| AC6 ntfy fails silently | ntfy config | `journalctl -t graphiti-litellm-validation` is the durable record; ntfy is best-effort; fallback log is the source-of-truth |
| Operator interprets a 94% pass as "close enough" and overrides the gate | Discipline | Threshold is hard-coded in script (`[ "$PASS" -ge 48 ]`); changing it requires editing the script — visible in PR review (reviewer-of-one acknowledges in commit body) |

## Definition of Done

- [ ] Either: AC1-AC10 all pass with `gate=PASS` (bridge active path); OR `gate=FAIL` with AC6+AC7 executed cleanly (auto-fallback + backlog item); OR AC11 deferred path closed cleanly
- [ ] `homelab-playbook/_bmad-output/planning-artifacts/products/context-stack/tests/litellm-50-fact-corpus.jsonl` committed (50 lines)
- [ ] `homelab-playbook/scripts/run-litellm-validation.sh` and `homelab-playbook/scripts/run-litellm-revert.sh` committed and executable
- [ ] Results + summary files for the validation run committed under `tests/`
- [ ] `homelab-playbook/wiki/projects/hybrid-gemma-serving.md` reflects the gate outcome (PASS → stable; FAIL → superseded; deferred → status=deferred)
- [ ] If FAIL: backlog item authored at `backlog/phase-4-litellm-gate-failure-<DATE>.md` AND ntfy push delivered
- [ ] AC8 revert-drill timed at ≤ 60 s (FR-LLM-008 reversibility evidence)
- [ ] AC9 cost-neutrality 7-day window started (start-of-window OpenAI spend recorded in summary)
- [ ] No regression in E1-E3 acceptance: existing Graphiti smoke tests still pass against current `.env` state
- [ ] Cross-reference task added: `AT-FR-LLM-005a`, `AT-FR-LLM-006a`, `AT-FR-LLM-008a` (Phase 5a will populate)
