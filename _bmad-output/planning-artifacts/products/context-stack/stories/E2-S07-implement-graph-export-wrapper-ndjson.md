---
type: story
epic: E2
id: E2-S07
title: "Implement gitnexus-export.sh NDJSON wrapper for FR-CG-010 / ADR-012 exit ramp"
size: 1d
priority: MUST
fr_refs: [FR-CG-010]
nfr_refs: [NFR-PORT-001, NFR-SUPP-002]
adr_refs: [ADR-004, ADR-012]
status: draft
date: 2026-04-25
---

# E2-S07: Implement gitnexus-export.sh NDJSON wrapper for FR-CG-010 / ADR-012 exit ramp

## User Story

As **tomamourette**, I want **a small bash + jq wrapper script that exports the entire GitNexus graph to a portable, line-delimited JSON file using only GitNexus's documented `cypher` tool surface**, so that **GitNexus's abandonment risk (brief §10.1 R1) is bounded — at any time I can run one command, get a complete portable graph dump, and a one-day replay-script effort restores function on CodeGraphContext (per ADR-012)**.

## Background and Context

ADR-012 settles Q8 (export format). GitNexus does NOT ship a documented `gitnexus export` command, so Context Stack must provide the export by issuing a full-graph Cypher query and shaping the result through `jq` into NDJSON whose schema is owned by Context Stack (not GitNexus). FR-CG-010 (MUST), NFR-PORT-001, and NFR-SUPP-002 collectively make this the "exit ramp insurance" for the entire code-graph tier. ADR-012 specifies the schema (three line shapes: node, edge, optional version-header), the cadence (on-demand, no auto-schedule), and the replay path (separate `gitnexus-to-cgc.sh` built only if the exit ramp is exercised — out of scope here). This story ships only the export.

## Acceptance Criteria

**AC1 — Script exists, executable, well-formed.**
- **Given** E2-S05 done (parent-folder graph populated),
- **When** the operator commits `homelab-playbook/scripts/gitnexus-export.sh` mode 755 with shebang `#!/usr/bin/env bash` AND `set -euo pipefail`,
- **Then** `bash -n homelab-playbook/scripts/gitnexus-export.sh` exits 0 (syntax check) AND `shellcheck homelab-playbook/scripts/gitnexus-export.sh` returns ≤ 0 errors / warnings (warnings may exist but no errors).

**AC2 — Default output path matches ADR-012.**
- **Given** AC1 has passed,
- **When** the operator runs the script with no arguments,
- **Then** output is written to `~/workspace/homelab/_export/gitnexus/$(date +%Y-%m-%d).ndjson` (parent dir auto-created if missing) AND the script logs the output path on stdout.

**AC3 — Output is valid NDJSON conforming to the ADR-012 schema.**
- **Given** AC2 has run successfully,
- **When** the operator inspects the output file,
- **Then** all of:
  - `jq -c . < <file> | wc -l` matches the line count in the file (every line is valid JSON);
  - Every line has either `"type": "node"` (with required keys: `id`, `labels`, `props`) OR `"type": "edge"` (with required keys: `id`, `src`, `dst`, `kind`, `props`) OR an optional first-line `"type": "header"` (with `version`, `exported_at`, `gitnexus_version`);
  - Schema-validation script `jq -e 'if .type=="node" then has("id") and has("labels") and has("props") elif .type=="edge" then has("id") and has("src") and has("dst") and has("kind") and has("props") elif .type=="header" then has("version") else false end' < <file>` returns true for every line.

**AC4 — Export contains nodes from all three sub-repos.**
- **Given** AC3 has passed,
- **When** the operator runs `jq -c 'select(.type=="node" and (.props.path? // ""|tostring) | startswith("homelab"))' < <file> | jq -s 'group_by(.props.path | split("/")[0]) | map({(.[0].props.path|split("/")[0]):length}) | add'`,
- **Then** the resulting object has keys for `homelab`, `homelab-bootstrap`, AND `homelab-playbook` (proves the export reflects the parent-folder topology established in E2-S05).

**AC5 — Export contains at least one cross-repo edge.**
- **Given** AC3 has passed AND E2-S05 AC4 cross-repo query returned ≥ 1 row,
- **When** the operator runs `jq -c 'select(.type=="edge")' < <file>` and (via a small jq pipeline that joins edges to nodes by `id`) checks edge `src` and `dst` map to nodes from different sub-repos,
- **Then** at least one cross-repo edge is present in the export (proves graph completeness, not just node-count completeness).

**AC6 — Output size constraints (ADR-012 validation).**
- **Given** AC2 has run,
- **When** the operator runs `du -h <file>`,
- **Then** size is < 50 MB (ADR-012 sanity check for the operator's `~/workspace/homelab/` graph) AND `wc -l <file>` is between 100 and 100000 lines (sanity bounds for a real codebase; flag anything outside as suspicious).

**AC7 — Script handles GitNexus unavailable cleanly.**
- **Given** AC1 has passed,
- **When** the operator stops the gitnexus daemon (`pkill -f gitnexus`) AND runs the export script,
- **Then** the script exits non-zero with a clear error message ("GitNexus daemon not running" or "cypher tool unreachable") within 10 s AND no partial / corrupt output file is left behind (atomic write: write to `*.tmp` then `mv` only on success).

**AC8 — Replay-path documentation present (NFR-SUPP-002).**
- **Given** AC1 has passed,
- **When** the operator authors `homelab-playbook/docs/runbooks/gitnexus-exit-ramp.md`,
- **Then** the runbook includes: (a) when to invoke the exit ramp (per ADR-004 reversal trigger criteria), (b) the export command (this story's script), (c) a sketch / placeholder for `gitnexus-to-cgc.sh` (NOT shipped per ADR-012, but referenced), (d) link to ADR-012 schema spec, AND (e) the alternative tool to migrate to (CodeGraphContext, per ADR-004).

**AC9 — One snapshot committed as Phase 2 evidence (per ADR-012 cadence).**
- **Given** AC2 has run successfully,
- **When** the operator commits the resulting `*.ndjson` file (or a 100-line sample if size is large) to `homelab-playbook/_export/gitnexus/<date>.ndjson`,
- **Then** the file is in git AND referenced from the exit-ramp runbook as the FR-CG-010 / NFR-PORT-001 acceptance evidence.

## Implementation Notes

**Reference architecture sections:** §6.3 GitNexus graph export schema (the ADR-012 schema verbatim), §4.1 Code-graph layer ("Export: scripts/gitnexus-export.sh" line), §11 AR4 (abandonment risk this script bounds).

**Reference ADRs:** ADR-012 (the spec), ADR-004 (the adoption decision the exit ramp protects).

**Script skeleton** (AC1 reference):

```bash
#!/usr/bin/env bash
set -euo pipefail

OUT_DIR="${HOME}/workspace/homelab/_export/gitnexus"
OUT_FILE="${OUT_DIR}/$(date +%Y-%m-%d).ndjson"
TMP_FILE="${OUT_FILE}.tmp"
GITNEXUS_VERSION="$(npx gitnexus --version 2>/dev/null || echo unknown)"

mkdir -p "$OUT_DIR"

# AC7 — fail fast if daemon down
if ! npx gitnexus cypher 'RETURN 1' >/dev/null 2>&1; then
  echo "ERROR: GitNexus cypher tool unreachable; is the daemon running?" >&2
  exit 2
fi

# Header line
{
  jq -nc --arg ver "1" --arg ts "$(date -Iseconds)" --arg gv "$GITNEXUS_VERSION" \
     '{type:"header", version:$ver, exported_at:$ts, gitnexus_version:$gv}'

  # Nodes
  npx gitnexus cypher 'MATCH (n) RETURN id(n) AS id, labels(n) AS labels, properties(n) AS props' \
    | jq -c '{type:"node", id:.id, labels:.labels, props:.props}'

  # Edges
  npx gitnexus cypher 'MATCH (s)-[r]->(d) RETURN id(r) AS id, id(s) AS src, id(d) AS dst, type(r) AS kind, properties(r) AS props' \
    | jq -c '{type:"edge", id:.id, src:.src, dst:.dst, kind:.kind, props:.props}'
} > "$TMP_FILE"

mv "$TMP_FILE" "$OUT_FILE"
echo "Exported to: $OUT_FILE"
echo "Lines: $(wc -l < "$OUT_FILE")"
echo "Size: $(du -h "$OUT_FILE" | cut -f1)"
```

(Exact `cypher` invocation surface — stdin, args, JSON-line vs tabular output — must be verified against `npx gitnexus@1.6.3 cypher --help`; the skeleton above assumes JSON-line output, adjust the jq filters if it returns tabular.)

**Exit-ramp runbook path:** `homelab-playbook/docs/runbooks/gitnexus-exit-ramp.md`.

**Evidence file:** `homelab-playbook/_export/gitnexus/<YYYY-MM-DD>.ndjson` (the actual export — committed; or a 100-line sample if the full file is unwieldy).

## Test Plan

**Pre-state:**
- E2-S05 done; parent-folder graph populated.
- `jq` and `shellcheck` available on workstation.

**Action sequence:**
1. Author and commit script (AC1).
2. Run script with no args; confirm output path and stdout (AC2).
3. Validate NDJSON schema with the jq -e check (AC3).
4. Run sub-repo coverage check (AC4) and cross-repo edge check (AC5).
5. Check size + line-count bounds (AC6).
6. Stop daemon; rerun script; confirm fail-fast (AC7); restart daemon.
7. Author exit-ramp runbook (AC8).
8. Commit one snapshot as evidence (AC9).

**Post-state checks:**
- Script committed, mode 755, shellcheck-clean.
- Output file valid NDJSON with all three sub-repos represented.
- ≥ 1 cross-repo edge present.
- Exit-ramp runbook references this script.
- One snapshot committed under `_export/gitnexus/`.

**Rollback:**
- `git revert <commit>` removes the script + runbook + snapshot. Wall-time: < 1 minute.
- Removing the script does not affect GitNexus operation.

## Dependencies

- **Blocked by:** E2-S05 (parent-folder graph must exist before export has anything meaningful to export).
- **Blocks:** E2-S08 (week-1 gate verifies FR-CG-010 closure exists; references this story's evidence).

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| GitNexus's `cypher` tool returns tabular output rather than JSON-line, breaking the jq pipeline. | Med | Med — script needs reshape. | AC1 development includes a small spike: `npx gitnexus cypher 'RETURN 1, 2'` and inspect; adjust jq filters accordingly; document the actual output shape in script header comment. |
| Some `props` values contain types not JSON-serializable (e.g., binary blobs, custom types). | Low | Low — single-edge or single-node export failure. | Use `jq -c` with default null behaviour; log skipped lines to a sidecar `*.skipped.txt`; set acceptance threshold to "≥ 99% of nodes/edges export cleanly". |
| Cypher full-graph query times out on a large graph. | Low | Med — needs paginated extraction. | If timeout, refactor to paginated `MATCH (n) WHERE id(n) > $cursor RETURN n LIMIT 1000` loop; document in script header. |
| GitNexus version bump renames `cypher` → `query`. | Low | High — script breaks. | Pin GitNexus to v1.6.3 (already done in E2-S01); ADR-012 §Negative consequence acknowledges this; the schema is the invariant, not the cypher-call shape. |
| Snapshot file is large and bloats the repo. | Low | Low — annoying. | If > 5 MB, commit only a 100-line sample + git-ignore the full file; reference the gitignored path from the runbook. |

## Definition of Done

- [ ] AC1–AC9 all green.
- [ ] `homelab-playbook/scripts/gitnexus-export.sh` committed, mode 755, shellcheck-clean.
- [ ] `homelab-playbook/docs/runbooks/gitnexus-exit-ramp.md` committed.
- [ ] One NDJSON snapshot (or 100-line sample) committed under `_export/gitnexus/`.
- [ ] FR-CG-010 + NFR-PORT-001 + NFR-SUPP-002 marked closed in PRD coverage tracker.
- [ ] Story status updated to `done`; OMEGA `omega_store(...)` records "exit ramp ships in Sprint 2 = abandonment risk bounded".
