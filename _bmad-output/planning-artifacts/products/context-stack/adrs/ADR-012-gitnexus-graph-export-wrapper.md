---
adr: 012
title: "GitNexus graph export via wrapper script (Cypher dump → portable JSON)"
status: accepted
date: 2026-04-25
authors: tomamourette (via BMAD director Claude)
context_question: Q8
---

# ADR-012: GitNexus graph export via wrapper script (Cypher dump → portable JSON)

## Context

PRD FR-CG-010 mandates that GitNexus exposes its graph as JSON exportable to disk for migration / backup / inspection. Brief §10.1 R1 documents the abandonment risk (single-maintainer project) and requires a documented exit ramp to CodeGraphContext or graphify at the Phase 2 retro.

Q8 asks the architecture phase to determine the GitNexus export format and stability.

**Source-verified facts (April 2026, GitNexus v1.6.3):**

- GitNexus uses **LadybugDB** as the underlying graph store (native CLI mode; LadybugDB WASM in browser mode).
- The README documents query tools (`cypher` — raw Cypher graph queries; `impact` — impact analysis; `context` — context retrieval) but **does not document an export format or `gitnexus export` command**.
- The graph schema (node labels, edge types, properties) is not formally documented; treat as private.

**Conclusion:** GitNexus does not ship a stable, portable export format. Therefore Context Stack must ship a **wrapper script** that constructs an exit-ramp-shaped JSON file via the documented Cypher query interface.

## Decision

Ship `homelab-playbook/scripts/gitnexus-export.sh` as a deliverable in Sprint 2 (E2 — GitNexus Pilot). The script:

1. Calls GitNexus's MCP `cypher` tool (or its CLI equivalent `npx gitnexus cypher`) to run a full-graph export query: `MATCH (n)-[r]->(m) RETURN n, labels(n), r, type(r), m, labels(m)`.
2. Streams the result through `jq` to produce a single newline-delimited JSON file with the schema below.
3. Outputs to `~/workspace/homelab/_export/gitnexus/$(date +%Y-%m-%d).ndjson`.

### Export JSON schema (Context-Stack-controlled, not GitNexus-controlled)

```jsonl
{"type":"node","id":"<ladybug-internal-id>","labels":["Function","Definition"],"props":{"name":"add_episode","file":"mcp_server/src/graphiti_mcp_server.py","line":234}}
{"type":"node","id":"...","labels":["File"],"props":{"path":"src/foo.py"}}
{"type":"edge","id":"<ladybug-internal-id>","src":"<node-id>","dst":"<node-id>","kind":"REFERENCES","props":{"line":56}}
```

This is a deliberately simple schema — three field shapes (`node`, `edge`, optional version-header line). Any successor tool (CodeGraphContext, graphify, a hand-rolled Neo4j replay) can ingest by reading line-by-line and building its own graph.

### Cadence

- **On-demand:** operator runs `scripts/gitnexus-export.sh` whenever they want a snapshot.
- **Phase 2 exit:** export run once, committed to `_export/gitnexus/` as an evidence artifact for FR-CG-010 / NFR-PORT-001 acceptance.
- **No automatic schedule** — the wiki+git workflow is the operator's primary capture mechanism; the export is the exit-ramp insurance, not a backup.

### Replay path (CodeGraphContext target)

A second script, `homelab-playbook/scripts/gitnexus-to-cgc.sh` (built only if/when the exit ramp is exercised), reads the NDJSON and re-creates nodes + edges via Cypher in CodeGraphContext's Neo4j backend:

```bash
# Sketch — only built on exit-ramp activation
cat $EXPORT \
  | jq -r 'select(.type=="node") | "MERGE (n:" + (.labels | join(":")) + " {id:\"" + .id + "\"}) SET n += " + (.props|tojson)' \
  | cypher-shell -u neo4j -p $NEO4J_PASS
```

The replay script is *not* shipped in Sprint 2 — only the export is. Building the replay is a Sprint 5+ event triggered by the exit-ramp event, captured in the wiki at `runbooks/gitnexus-to-codegraphcontext.md`.

## Consequences

**Positive.**
- FR-CG-010 satisfied with a script that uses GitNexus's documented query surface (Cypher) — no dependency on undocumented internal export.
- Schema is Context-Stack-controlled, so GitNexus version bumps that change LadybugDB internals don't break the export shape.
- NDJSON is the most portable format (line-delimited; resumable; jq-friendly).
- The export script is small (< 100 lines bash + jq) — ships fast in Sprint 2.

**Negative.**
- Cypher-based extraction can be slow on large graphs; for the operator's `~/workspace/homelab/` (~10k nodes ballpark) it should complete in seconds. Validate during Sprint 2.
- Replay logic is tool-specific (CodeGraphContext vs graphify needs different scripts); we ship export now, replay-on-demand later.
- If GitNexus changes its Cypher tool surface (e.g., renames `cypher` → `query`), the wrapper breaks. Mitigated by pinning GitNexus version (FR-DEP-010 spirit, ADR-004).

**Neutral.**
- Schema is Context-Stack's own; this is a feature (control), not a bug (lock-in).

## Alternatives Considered

1. **Wait for GitNexus to ship `gitnexus export`** — rejected. No upstream commitment; abandonment risk is the whole reason FR-CG-010 exists.
2. **Snapshot LadybugDB binary file** — rejected. LadybugDB binary format is not documented as portable; restore would require LadybugDB itself, which is the very dependency the exit ramp is escaping.
3. **Use SCIP (Sourcegraph's open code-graph protocol) as the export format** — rejected for now. SCIP is a strong target if cross-tool portability becomes a goal, but adopting SCIP is a larger story than NDJSON dump; revisit at Phase 4 retro.
4. **Skip the wrapper, accept the lock-in** — rejected. The operator's "< 1 day reversibility" constraint (NFR-MAINT-001) and the brief's R1 abandonment risk make the export non-optional.

## Validation / Exit Ramp

- **Validation:** in Sprint 2 acceptance, run `scripts/gitnexus-export.sh` on the operator's `~/workspace/homelab/` graph; output file exists, is < 50 MB, parses as valid NDJSON (`jq -c . < export.ndjson | wc -l` matches expected line count).
- **Exit ramp:** the script *is* the exit ramp. If GitNexus disappears, export script + a one-day replay-script-to-CodeGraphContext effort restores function.
- **Reversal trigger:** the export script's own "broken" trigger is GitNexus removing the `cypher` tool surface. If that happens, fork the export to use whatever query surface replaces it; the JSON schema is invariant.

## References

- PRD FR-CG-010, NFR-PORT-001
- Brief §10.1 R1 (abandonment risk)
- ADR-004 (GitNexus adoption + exit-ramp commitment)
- GitNexus README (LadybugDB native; `cypher` tool documented; no `export` documented as of April 2026): <https://github.com/abhigyanpatwari/GitNexus>
