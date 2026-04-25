---
type: story
epic: E3
id: E3-S06
title: "Implement 5 functional smoke-test scenarios (bi-temporal, similarity, extraction, supersession, graceful degradation)"
size: 1.5d
priority: MUST
fr_refs: [FR-MEM-009, FR-MEM-013]
adr_refs: [ADR-005]
status: draft
date: 2026-04-25
---

# E3-S06: Implement 5 functional smoke-test scenarios (bi-temporal, similarity, extraction, supersession, graceful degradation)

## User Story

As **tomamourette** (homelab operator), I want **the five functional smoke-test scenarios from the install runbook §7 executed against the live Graphiti pilot — bi-temporal validity, embedding similarity, auto entity-extraction, multi-episode supersession, and graceful-degradation-when-FalkorDB-stopped — captured as repeatable test scripts**, so that **I can prove Graphiti's bi-temporal differentiator actually works (the genuine reason to adopt it), prove similarity recall is sensible, prove extraction doesn't malform JSON at this LLM tier, and prove the stack degrades gracefully under failure (FR-MEM-009, FR-MEM-013, NFR-AVAIL-002 covered; runbook §7 tests 3+4+5 + degradation drill)**.

## Background and Context

The runbook §7 smoke-test plan has five scenarios. E3-S05 covered tests 1 (write) and 2 (read) plus AR8 closure. This story executes the remaining three runbook scenarios (3, 4, 5) **and** adds the graceful-degradation drill mandated by FR-MEM-013 / NFR-AVAIL-002 (3-second hang ceiling). Bi-temporal validity is Graphiti's genuine differentiator over Mem0/Letta/Cognee (per memory-systems-eval) — the entire reason it was selected. If test 3 fails, the architectural premise is in question and the week-2 decision gate (E3-S09) should consider migrate-or-revert.

Per epics §9 EQ3 (Phase 4b open question), this story specifies the exact failure injection for the degradation drill: `docker compose stop graphiti-falkordb` (NOT killing the network — that's a different test surface; the question is "Graphiti container hung", which is FalkorDB-stopped).

## Acceptance Criteria

### AC1: Test 3 (bi-temporal validity) passes — superseded fact retains both validity intervals

- **Given** the graph contains the install marker from E3-S05 AC1
- **When** I drive these two writes from Claude Code (runbook §7 test 3, lifted verbatim with date adjustments):
  1. *"Use graphiti add_episode: name='pve-state-1', episode_body='On 2026-04-24, ct-ai-01 was hosted on pve2. CT151 was migrated back to pve2.', source='text', group_id='tom-personal'."*
  2. *"Use graphiti add_episode: name='pve-state-2', episode_body='On 2026-04-25, ct-ai-01 was moved from pve2 to pve3.', source='text', group_id='tom-personal'."*
- **Then** after 30 s ingest delay, query: *"Use graphiti search_facts for 'where is ct-ai-01 hosted', group_id='tom-personal'."*
- **And** the response includes at least one fact about `ct-ai-01` and `pve3` with a `valid_at` aligned to 2026-04-25; the earlier `pve2` fact is still queryable (e.g. via `search_facts(query='ct-ai-01 historic location')` returns BOTH facts ordered).
- **Smoke acceptance:** the model can answer "as of 2026-04-23, where was ct-ai-01?" with `pve2` (or "no info"), and "as of today" with `pve3` (runbook §7 test 3 pass criterion).

### AC2: Test 4 (embedding similarity) passes — semantic recall without exact-phrase overlap

- **Given** the graph state from AC1
- **When** I drive: *"Use graphiti add_episode: name='tailscale-policy', episode_body='Tailscale ACLs control which devices can reach the homelab tailnet. Phone-facing services bind to 127.0.0.1 and Tailscale Serve handles ingress.', source='text', group_id='tom-personal'."*
- **And** after 30 s ingest, query: *"Use graphiti search_facts for 'how is access to the homelab restricted from the public internet', group_id='tom-personal'."*
- **Then** the Tailscale fact is returned in the top results despite zero exact-phrase overlap (`ACLs`, `tailnet`, `127.0.0.1`, `Serve` vs `access`, `restricted`, `public internet`).
- **Smoke acceptance:** runbook §7 test 4 pass criterion — semantic match without literal substring match.

### AC3: Test 5 (auto entity-extraction) passes — freeform prose extracts entities + relations cleanly

- **Given** ACs 1–2
- **When** I drive: *"Use graphiti add_episode: name='ha-rules-lesson', episode_body='During the pve9 HA rules migration on 2026-04-22, I learned that ha-manager set --state stopped is rejected on error-state resources — you have to disable, diagnose, then start.', source='text', group_id='tom-personal'."* (lifted from runbook §7 test 5; matches a real OMEGA entry I'm hand-porting)
- **And** after 60 s ingest (extraction may take longer), query both:
  - `search_nodes(query='ha-manager', group_id='tom-personal')`
  - `search_facts(query='error state', group_id='tom-personal')`
- **Then** `search_nodes` returns an entity for `ha-manager` (or equivalent normalized form); `search_facts` returns the lesson with reference to error state; FalkorDB Browser shows a relation between `pve9` (or `PVE 9`) and `ha-manager`.
- **Smoke acceptance:** extraction JSON did not malform (no error in `docker compose logs graphiti-mcp 2>&1 | grep -i JSONDecodeError`).

### AC4: Multi-episode supersession check (extends test 3)

- **Given** AC1 (two pve-state episodes ingested)
- **When** I run a Cypher query directly: `MATCH (n)-[r]->(m) WHERE n.name CONTAINS 'ct-ai-01' RETURN n, r.name, r.valid_at, r.invalid_at, m`
- **Then** at least one edge has both `valid_at` populated and (where applicable) `invalid_at` populated — Graphiti has detected the supersession from `pve2` → `pve3` and recorded the temporal interval. (If `invalid_at` is null on the older fact, that's acceptable — Graphiti's docs note explicit invalidation requires explicit signal; the operator records that as a finding in story evidence.)

### AC5: Graceful degradation — FalkorDB stopped, Claude Code session continues, no > 3 s hang

- **Given** ACs 1–4 establish a populated graph
- **When** I:
  1. On ct-ai-01: `docker compose -f /srv/graphiti/docker-compose.yml stop falkordb` (the failure injection — closes EQ3)
  2. From workstation: open a fresh Claude Code session, prompt: *"Use graphiti search_facts for 'pve3', group_id='tom-personal'."* and start a `time` measurement on the session-side
- **Then** within 3 s wall-clock the tool call returns an error (or empty result) and the session continues — Claude Code does NOT hang waiting for a response. The auto-memory + wiki + GitNexus paths continue to function in the same session.

### AC6: Recovery from degraded state — FalkorDB restarted, recall works again

- **Given** AC5
- **When** I run on ct-ai-01: `docker compose -f /srv/graphiti/docker-compose.yml start falkordb && sleep 10`
- **And** from workstation: `time curl -fsS http://127.0.0.1:8000/health` (via Tailscale)
- **And** drive a fresh `search_facts(query='pve3', group_id='tom-personal')` from Claude Code
- **Then** health is OK; the search returns the same fact as in AC1 (no data loss — AOF replay on restart); round-trip latency back to baseline (< 500 ms p95 per NFR-PERF-002).

### AC7: All five smoke tests captured as a single runnable script

- **Given** ACs 1–6 pass once interactively
- **When** I write `homelab-playbook/scripts/graphiti-smoke.sh` that executes the test scenarios via `claude --print` (one-shot mode) or `curl` against the MCP endpoint
- **Then** running `./scripts/graphiti-smoke.sh` exits 0 on a healthy stack, prints a per-test PASS/FAIL summary, and exits non-zero on any failure. The script is committed to the repo and referenced from the install runbook.

### AC8: docker compose logs show zero `JSONDecodeError` across the entire suite

- **Given** ACs 1–6 ran end-to-end
- **When** I run `docker compose -f /srv/graphiti/docker-compose.yml logs graphiti-mcp 2>&1 | grep -iE "JSONDecodeError|extraction.*failed|malformed" | wc -l`
- **Then** the count is 0 — `gpt-4o-mini` is producing well-formed extraction JSON at this LLM tier (informs the FR-LLM-005 95% gate baseline for E4-S06).

## Implementation Notes

- **Test ordering:** AC1 → AC2 → AC3 → AC4 → AC5 → AC6 in sequence. ACs 1–4 populate the graph; AC5 takes it down; AC6 brings it back. AC7 captures the whole thing as a script.
- **30 s ingest wait between writes and reads:** Graphiti's extraction pipeline runs async; reads before extraction completes return zero results (false negative). Use 30 s for short bodies, 60 s for longer prose (AC3).
- **AC2 query phrasing is intentionally divergent:** "how is access to the homelab restricted from the public internet" shares zero substrings with the ingested fact's surface form. If recall returns the fact, embedding similarity is working. If it doesn't, similarity is broken — this is the AR for ADR-003 (embedder choice).
- **AC3 extraction quality is the FR-LLM-005 baseline.** Track this manually in story evidence: how many entities extracted, how many relations, any nonsense (e.g. `ha-manager` parsed as a person's name). This corpus informs the 50-fact validation set for E4-S06.
- **AC4 Cypher direct path:** `docker compose exec falkordb redis-cli -a "$FALKORDB_PASSWORD" GRAPH.QUERY default_db "MATCH (n)-[r]->(m) WHERE n.name CONTAINS 'ct-ai-01' RETURN n, r.name, r.valid_at, r.invalid_at, m"`. Bi-temporal correctness is observable here, not via the MCP tools (which abstract it).
- **AC5 failure injection (closes EQ3):** `docker compose stop falkordb` is the chosen mode — it kills the DB but keeps the MCP server alive, so the failure cascade is "MCP server can't reach DB" → tool returns error within 3 s. Alternative ("stop graphiti-mcp") would test a different code path (Claude Code's MCP transport timeout) — useful but not what FR-MEM-013 specifies.
- **AC5 timeout assertion:** Claude Code's MCP HTTP transport has a default request timeout (typically ~30 s). The 3 s assertion is at the operator-perceived level — the model may retry, but the session must not feel hung. Measure with stopwatch on first run; encode in `graphiti-smoke.sh` as `timeout 5s claude --print '...'`.
- **Smoke script template (`graphiti-smoke.sh`):**
  ```bash
  #!/usr/bin/env bash
  set -uo pipefail
  PASS=0; FAIL=0
  run() { echo "=== $1 ==="; if eval "$2"; then echo "PASS: $1"; PASS=$((PASS+1)); else echo "FAIL: $1"; FAIL=$((FAIL+1)); fi; }
  run "test1-write" 'claude --print "..." | grep -E "[0-9a-f-]{36}"'
  run "test2-read" '...'
  # ... etc for tests 3, 4, 5, degradation, recovery
  echo "Result: $PASS passed, $FAIL failed"
  exit $FAIL
  ```

## Test Plan

```bash
# AC1 — drive the two pve writes via Claude Code
# (Two separate prompts; capture both UUIDs)

sleep 30

# AC1 verification
script -q /tmp/e3-s06-pve.log claude
# inside: "Use graphiti search_facts for 'where is ct-ai-01 hosted', group_id='tom-personal'."
grep -iE "pve3.*2026-04-25|2026-04-25.*pve3" /tmp/e3-s06-pve.log

# AC2 — Tailscale similarity
sleep 30
script -q /tmp/e3-s06-similarity.log claude
# inside: "Use graphiti search_facts for 'how is access to the homelab restricted from the public internet', group_id='tom-personal'."
grep -i "tailscale\|tailnet" /tmp/e3-s06-similarity.log

# AC3 — extraction
sleep 60
script -q /tmp/e3-s06-extraction.log claude
# inside two prompts: search_nodes for 'ha-manager' and search_facts for 'error state'
grep -i "ha-manager" /tmp/e3-s06-extraction.log
ssh ct-ai-01 'docker compose -f /srv/graphiti/docker-compose.yml logs graphiti-mcp 2>&1 | grep -ic JSONDecodeError'    # expect 0

# AC4 — direct Cypher for bi-temporal
ssh ct-ai-01 'docker compose -f /srv/graphiti/docker-compose.yml exec -T falkordb redis-cli -a "$(grep ^FALKORDB_PASSWORD= /srv/graphiti/.env | cut -d= -f2)" GRAPH.QUERY default_db "MATCH (n)-[r]->(m) WHERE n.name CONTAINS '\''ct-ai-01'\'' RETURN n.name, r.name, r.valid_at, r.invalid_at, m.name"'
# Capture output to evidence; verify valid_at populated

# AC5 — degradation drill
ssh ct-ai-01 'docker compose -f /srv/graphiti/docker-compose.yml stop falkordb'
START=$(date +%s%N)
timeout 5s claude --print "Use graphiti search_facts for 'pve3', group_id='tom-personal'."
END=$(date +%s%N)
ELAPSED_MS=$(( (END - START) / 1000000 ))
echo "Elapsed: ${ELAPSED_MS}ms"
[ $ELAPSED_MS -lt 3000 ] || { echo "FAIL: hung > 3 s"; exit 1; }

# AC6 — recovery
ssh ct-ai-01 'docker compose -f /srv/graphiti/docker-compose.yml start falkordb'
sleep 10
curl -fsS http://ct-ai-01.<tailnet>.ts.net:8000/health
script -q /tmp/e3-s06-recovery.log claude
# inside: "Use graphiti search_facts for 'pve3', group_id='tom-personal'."
grep -i "pve3" /tmp/e3-s06-recovery.log

# AC7 — script
chmod +x homelab-playbook/scripts/graphiti-smoke.sh
./homelab-playbook/scripts/graphiti-smoke.sh
echo "Exit code: $?"   # expect 0

# AC8
ssh ct-ai-01 'docker compose -f /srv/graphiti/docker-compose.yml logs graphiti-mcp 2>&1 | grep -iE "JSONDecodeError|extraction.*failed|malformed" | wc -l'    # expect 0
```

## Dependencies

- **Blocks:** E3-S07 (backup story uses the now-populated graph as restore target); E3-S08 (restore drill verifies probe data persists); E3-S09 (decision-gate K5 measurement uses these tagged retro entries).
- **Blocked by:** E3-S05 (basic write/read + AR8 closure must pass first).

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Bi-temporal extraction is weaker than the docs claim — AC1/AC4 fail | This is the architectural premise check; if it fails, file as week-2 KPI gate input — E3-S09 may decide migrate-or-revert |
| Embedding similarity weak (AC2 fails) — recall poor on paraphrased queries | Per ADR-003 reversal trigger: swap to `text-embedding-3-large` for one-week controlled experiment |
| Extraction JSON malforms on AC3 prose (AC8 fails) | At `gpt-4o-mini` tier this should not happen; if it does, file an upstream issue and re-run with stronger prompt; informs FR-LLM-005 gate baseline |
| AC5 hangs > 3 s (NFR-AVAIL-002 violation) | Document as MCP transport regression; tighten the Claude Code MCP timeout config in `~/.claude/settings.json` (if exposed); escalate to FR-MEM-013 SHOULD downgrade if irreducible |
| AC6 reveals data loss after restart (AOF replay broken) | Hard FalkorDB issue; document, escalate to ADR-007 backup story (E3-S07) — the AOF cadence may need to be tightened or `fsync=always` set |
| `graphiti-smoke.sh` flaky under load (false fails on slow OpenAI) | Build in retry-once logic; document p95 per test in script comments |

## Definition of Done

- [ ] All ACs (AC1–AC8) pass at least once interactively
- [ ] `homelab-playbook/scripts/graphiti-smoke.sh` committed and runs to exit 0 on a healthy stack
- [ ] Story evidence directory `_bmad-output/evidence/E3-S06/` populated with: bi-temporal Cypher result, similarity transcript, extraction transcript, degradation timing log, recovery transcript
- [ ] Acceptance test stubs `AT-FR-MEM-009b/c/d`, `AT-FR-MEM-013a`, `AT-NFR-AVAIL-002a` referenced in `tests/acceptance.md`
- [ ] FR-LLM-005 baseline note added to story evidence: "gpt-4o-mini extraction JSON: 0 malformed across N episodes" — feeds E4-S06 50-fact validation set
- [ ] EQ3 closed: failure injection mode = `docker compose stop falkordb`; documented in epics §9
- [ ] All test prompts archived in `homelab-playbook/scripts/graphiti-smoke-prompts.md` as the canonical script source
