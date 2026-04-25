---
type: story
epic: E3
id: E3-S05
title: "Smoke-test add_episode + search_facts + verify tom-personal namespacing (closes AR8)"
size: 1d
priority: MUST
fr_refs: [FR-MEM-005, FR-MEM-009]
adr_refs: [ADR-005]
status: draft
date: 2026-04-25
---

# E3-S05: Smoke-test add_episode + search_facts + verify tom-personal namespacing (closes AR8)

## User Story

As **tomamourette** (homelab operator), I want **a probe `add_episode` to return a UUID, the matching `search_facts` to return the fact, AND a controlled experiment that proves writes default to `tom-personal` (not the literal string `main`)**, so that **basic write/read works end-to-end and architecture risk AR8 (default group_id discipline) is closed before any K5 first-shot-recall measurement (FR-MEM-005, FR-MEM-009 covered; runbook §7 tests 1+2 + open-verification step #4)**.

## Background and Context

This is the **first functional smoke test** of the Graphiti pilot — runbook §7 tests 1 and 2 (write + read). Architecture §11 AR8 flags that if the model omits `group_id`, Graphiti uses its compiled-in default (literal string `"main"`), **not** the env-set `GRAPHITI_GROUP_ID`. This silently fragments the graph: writes land in `main`, reads against `tom-personal` find nothing, K5 recall hit-rate collapses without an obvious symptom. Runbook §10 open-verification step #4 calls this out as the exact thing to test on day one. This story does both — proving basic plumbing AND closing AR8 with an experiment that distinguishes the two failure modes.

The five-scenario suite (E3-S06) is broader and includes bi-temporal validity / similarity / failure-injection; this story is the narrower "did I install it right at all" gate that must pass before E3-S06 starts.

## Acceptance Criteria

### AC1: Probe write via Claude Code returns a UUID

- **Given** Graphiti MCP is registered (E3-S02), CLAUDE.md instructs the model (E3-S03), and LLM/embedder are configured (E3-S04)
- **When** I open a Claude Code session and prompt: *"Use the graphiti MCP. Call `add_episode` with `name='install-test-e3-s05'`, `episode_body='Graphiti pilot smoke-test on ct-ai-01 on 2026-04-25; FalkorDB backend; group_id tom-personal.'`, `source='text'`, `group_id='tom-personal'`."* (lift verbatim from runbook §6 Step 11)
- **Then** the tool call succeeds and returns a UUID matching the regex `^[0-9a-f-]{36}$`; the UUID is captured in the session log at `/tmp/e3-s05-write.log`.

### AC2: FalkorDB Browser confirms node creation

- **Given** AC1
- **When** I open `http://ct-ai-01.<tailnet>.ts.net:3000` in a browser, select the `default_db` graph, and run `MATCH (n) WHERE n.group_id = 'tom-personal' RETURN n LIMIT 25` (runbook §6 Step 13)
- **Then** at least one node returns; node properties include `group_id="tom-personal"` and content related to the probe (e.g. `Graphiti`, `ct-ai-01`, or `FalkorDB` entities).

### AC3: search_facts in a fresh session returns the fact

- **Given** AC1 + AC2 (and waiting ~30 s for ingestion to complete)
- **When** I open a **fresh** Claude Code session (not the one that did the write — proves no in-session caching) and prompt: *"Use graphiti `search_facts` for 'graphiti install', `group_id='tom-personal'`."* (runbook §6 Step 12)
- **Then** the response includes at least one fact whose text references the install probe; `valid_at` is populated (any value — bi-temporal correctness is E3-S06).

### AC4: Default-group experiment — explicit `group_id` write lands in tom-personal

- **Given** AC1 establishes the explicit-`group_id` happy path
- **When** I drive `add_episode(name='ar8-explicit', episode_body='AR8 probe: explicit group_id=tom-personal', source='text', group_id='tom-personal')` from Claude Code
- **Then** `MATCH (n) WHERE n.group_id = 'tom-personal' AND n.name CONTAINS 'ar8-explicit' RETURN n` in FalkorDB Browser returns the node; `MATCH (n) WHERE n.group_id = 'main' AND n.name CONTAINS 'ar8-explicit' RETURN n` returns **zero**.

### AC5: Default-group experiment — `group_id` omitted lands in `main` (the AR8 trap)

- **Given** AC4
- **When** I drive `add_episode(name='ar8-default', episode_body='AR8 probe: group_id deliberately omitted from this call', source='text')` from Claude Code (no `group_id` kwarg)
- **Then** at least one of the following is true (the test passes the AR8 closure either way, but the path matters):
  - **Path A (graph fragmentation confirmed):** `MATCH (n) WHERE n.group_id = 'main' AND n.name CONTAINS 'ar8-default' RETURN n` returns the node, AND `MATCH (n) WHERE n.group_id = 'tom-personal' AND n.name CONTAINS 'ar8-default' RETURN n` returns **zero**. → **AR8 is real, mitigation is the CLAUDE.md mandate (E3-S03 AC4).**
  - **Path B (env default honoured):** the node lands in `tom-personal` despite the omission. → **AR8 is mitigated by `GRAPHITI_GROUP_ID=tom-personal` at the env level; CLAUDE.md mandate is belt-and-braces.**
- **And** the path observed is recorded in story evidence at `_bmad-output/evidence/E3-S05-ar8-finding.md` with the exact Cypher results.

### AC6: search across both groups isolates writes

- **Given** AC4 + AC5
- **When** I drive `search_facts(query='AR8 probe', group_id='tom-personal')` and separately `search_facts(query='AR8 probe', group_id='main')`
- **Then** the `tom-personal` search returns the AC4 fact (and possibly more), the `main` search returns the AC5 fact only IF Path A in AC5 holds. Group isolation is provable.

### AC7: get_status reports healthy DB connectivity

- **Given** AC1
- **When** I drive `get_status()` from Claude Code
- **Then** the response contains a healthy/connected-equivalent status field; `database_provider` (or equivalent) reports `falkordb`.

### AC8: AR8 conclusion encoded in CLAUDE.md emphasis

- **Given** AC5 evidence
- **When** I read back the Memory (Graphiti) section in `~/.claude/CLAUDE.md` from E3-S03
- **Then**:
  - If Path A: the **bold** `Always pass group_id="tom-personal"` instruction is verified-load-bearing — no edit needed (E3-S03 already covers it).
  - If Path B: append a one-line note to the section: `(Note: GRAPHITI_GROUP_ID env default is also set to tom-personal as belt-and-braces; the explicit pass is still the contract.)` — minor edit, takes 30 seconds.

## Implementation Notes

- **Run AC4 + AC5 BEFORE the broader E3-S06 suite.** This story's job is to know which AR8 path is in effect — the rest of the smoke-tests assume that knowledge.
- **FalkorDB Browser query examples:**
  - All nodes in `tom-personal`: `MATCH (n) WHERE n.group_id = 'tom-personal' RETURN n`
  - All nodes in `main`: `MATCH (n) WHERE n.group_id = 'main' RETURN n`
  - Count by group: `MATCH (n) RETURN n.group_id AS g, count(n) AS c`
- **30-second wait between AC1 and AC3:** Graphiti's ingest pipeline runs LLM extraction asynchronously after `add_episode` returns the UUID; allow time. If 30 s is insufficient, allow up to 2 min and document.
- **Two separate sessions (write vs read in AC3):** prevents in-session cache from masking a real persistence failure. The `script -q` capture of both sessions is the test artefact.
- **Story evidence directory:** `_bmad-output/evidence/E3-S05-*` — `ar8-finding.md` for the Path A/B determination, plus session logs and Cypher screenshots.
- **The `episode_body` text in AC1 is intentionally factual** so the smoke test populates the graph with a real anchor for E3-S06 supersession tests — no temporary "test123" — that fact stays in the graph as the install marker.

## Test Plan

```bash
# AC1 — interactive
script -q /tmp/e3-s05-write.log claude
# inside: prompt verbatim from AC1
grep -E "^[0-9a-f-]{36}$" /tmp/e3-s05-write.log    # expect at least one match

# AC2
# Open browser http://ct-ai-01.<tailnet>.ts.net:3000
# Run: MATCH (n) WHERE n.group_id = 'tom-personal' RETURN n LIMIT 25
# Capture screenshot to _bmad-output/evidence/E3-S05-falkordb-tom-personal.png

# AC3 — fresh session (after 30 s wait)
sleep 30
script -q /tmp/e3-s05-read.log claude --new-session
# inside: "Use graphiti search_facts for 'graphiti install', group_id='tom-personal'."
grep -i "install" /tmp/e3-s05-read.log

# AC4 — explicit group_id write
script -q /tmp/e3-s05-ar8-explicit.log claude
# inside: "Use graphiti add_episode with name='ar8-explicit', episode_body='AR8 probe: explicit', source='text', group_id='tom-personal'."

# AC5 — omitted group_id write (THE AR8 PROBE)
script -q /tmp/e3-s05-ar8-default.log claude
# inside: "Use graphiti add_episode with name='ar8-default', episode_body='AR8 probe: omitted', source='text'. DO NOT pass group_id."

# AC6 — verify isolation in FalkorDB Browser:
# Query 1: MATCH (n) WHERE n.group_id='tom-personal' AND n.name CONTAINS 'ar8' RETURN n.name, n.group_id
# Query 2: MATCH (n) WHERE n.group_id='main' AND n.name CONTAINS 'ar8' RETURN n.name, n.group_id
# Capture both result sets to _bmad-output/evidence/E3-S05-ar8-finding.md

# AC7
script -q /tmp/e3-s05-status.log claude
# inside: "Call graphiti get_status."
grep -iE "(falkor|connected|healthy)" /tmp/e3-s05-status.log
```

**Acceptance evidence template (`_bmad-output/evidence/E3-S05-ar8-finding.md`):**

```markdown
# AR8 finding — Graphiti default group_id behaviour

Date: 2026-04-25
Tested by: tomamourette
Graphiti MCP: zepai/graphiti-mcp:v1.0.2
GRAPHITI_GROUP_ID env: tom-personal

## AC4 — explicit group_id="tom-personal"
tom-personal results: <paste>
main results: <paste>

## AC5 — group_id omitted
tom-personal results: <paste>
main results: <paste>

## Conclusion
[Path A: AR8 real — CLAUDE.md mandate is load-bearing]
OR
[Path B: env default honoured — mandate is belt-and-braces]

## Action
[None / appended one-line note to CLAUDE.md per E3-S05 AC8]
```

## Dependencies

- **Blocks:** E3-S06 (broader smoke suite assumes basic write/read works AND knows AR8 path); E3-S07 (backup story tests against real data — this story populates the install marker); E3-S09 (K5 first-shot recall depends on namespacing being correct).
- **Blocked by:** E3-S04 (LLM/embedder configured), E3-S03 (CLAUDE.md instructs the model).

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Async ingest takes longer than 30 s, AC3 returns empty (false negative) | Re-run AC3 after 2 min; document; if persistent, drop `SEMAPHORE_LIMIT` further |
| FalkorDB Browser unavailable (port 3000 not exposed) | Use `redis-cli ... GRAPH.QUERY default_db "MATCH (n) ..."` from `docker compose exec falkordb` instead — same result, less ergonomic |
| Model refuses to call `add_episode` with `group_id` omitted (AC5) | Drop to direct MCP call via `curl -X POST http://127.0.0.1:8000/mcp/ -d '{"method":"tools/call","params":{"name":"add_episode","arguments":{"name":"ar8-default","episode_body":"...","source":"text"}}}'` — proves the server-side default behaviour |
| Path A confirmed but operator takes no action (AR8 risk recurs) | E3-S03 AC4 already mandates the explicit pass in CLAUDE.md; Path A confirmation is itself the mitigation reinforcement |
| FalkorDB returns no results due to graph-name mismatch (`default_db` vs whatever `FALKORDB_DATABASE` resolved to) | Pre-flight: `docker compose exec falkordb redis-cli -a "$FALKORDB_PASSWORD" GRAPH.LIST` to enumerate graph names |

## Definition of Done

- [ ] All ACs (AC1–AC8) pass
- [ ] `_bmad-output/evidence/E3-S05-ar8-finding.md` written and committed
- [ ] FalkorDB Browser screenshot captured for AC2
- [ ] Session logs at `/tmp/e3-s05-{write,read,ar8-explicit,ar8-default,status}.log` archived to story evidence
- [ ] CLAUDE.md updated per AC8 (Path A: no edit; Path B: one-line note)
- [ ] Acceptance test stubs `AT-FR-MEM-005a`, `AT-FR-MEM-009a` referenced in `tests/acceptance.md`
- [ ] AR8 status flipped from "open" to "mitigated" in architecture §11 risk register (or addendum)
- [ ] Install marker (the AC1 episode) survives in the graph as the canonical install timestamp — referenced by E3-S08 restore drill
