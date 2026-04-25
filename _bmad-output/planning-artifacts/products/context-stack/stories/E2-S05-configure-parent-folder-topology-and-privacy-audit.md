---
type: story
epic: E2
id: E2-S05
title: "Configure parent-folder topology over ~/workspace/homelab/ + verify cross-repo + privacy audit"
size: 1d
priority: MUST
fr_refs: [FR-CG-002, FR-CG-003, FR-CG-012]
nfr_refs: [NFR-PRIV-001]
adr_refs: [ADR-004]
status: draft
date: 2026-04-25
---

# E2-S05: Configure parent-folder topology over ~/workspace/homelab/ + verify cross-repo + privacy audit

## User Story

As **tomamourette**, I want **GitNexus configured to index `~/workspace/homelab/` as a single parent-folder graph spanning all three sibling repos (`homelab/`, `homelab-bootstrap/`, `homelab-playbook/`)**, so that **cross-repo questions like "which Ansible roles in homelab-playbook reference services defined in homelab/" return correctly typed edges instead of missing the link entirely (the killer feature called out in brief §8.2 and architecture §4.1) — and so I can confirm in a single hard test that no source code or AST data ever leaves the workstation (FR-CG-002, FR-CG-012, NFR-PRIV-001)**.

## Background and Context

GitNexus's parent-folder-with-sub-repos topology is the architectural fit that drove ADR-004 over graphify and CodeGraphContext: the operator's `~/workspace/homelab/` directory contains exactly that shape — three sibling repos under one parent. FR-CG-003 mandates this topology. FR-CG-002 + FR-CG-012 + NFR-PRIV-001 collectively require that parsing is local-only with zero outbound LLM-API traffic; this story does the definitive `tcpdump`-based audit during a full reindex (E2-S02 seeded the technique). Architecture §4.1 + §5.1 (Privacy boundary) define the exact contract: "Source code (parsed by GitNexus tree-sitter on workstation) — stays on workstation".

## Acceptance Criteria

**AC1 — Parent-folder topology configured.**
- **Given** E2-S04 done (hooks live and pointing at v1.6.3),
- **When** the operator runs `npx gitnexus init --root ~/workspace/homelab/` (or whatever the upstream-documented topology-config command is — discoverable via `npx gitnexus --help`) AND inspects the resulting GitNexus config,
- **Then** the configured root is `/home/developer/workspace/homelab/` AND GitNexus discovers exactly three sub-repos: `homelab/`, `homelab-bootstrap/`, `homelab-playbook/` (verified via `npx gitnexus list-repos` or equivalent CLI introspection, OR via a Cypher query — see AC3).

**AC2 — Full reindex completes successfully.**
- **Given** AC1 has passed,
- **When** the operator runs `npx gitnexus reindex --full` (cold start) AND captures wall-clock time,
- **Then** the reindex exits 0 AND wall-clock time is recorded (the < 60 s NFR-PERF-005 hard check is in E2-S06 smoke test 5; here we just need a successful completion AND a recorded timing for E2-S08's KPI scorecard).

**AC3 — Cypher query returns nodes from all three sub-repos.**
- **Given** AC2 has passed,
- **When** the operator (via Claude Code MCP `cypher` tool OR `npx gitnexus cypher`) runs `MATCH (f:File) RETURN DISTINCT split(f.path, "/")[0..2] AS repo_root LIMIT 50` (or an equivalent query that segments file-path by sub-repo),
- **Then** the result set contains File nodes from at minimum 3 distinct top-level paths corresponding to `homelab`, `homelab-bootstrap`, and `homelab-playbook` (proves cross-repo coverage).

**AC4 — Cross-repo edge exists end-to-end (the killer-feature proof).**
- **Given** AC3 has passed,
- **When** the operator runs a Cypher query that walks an edge crossing repo boundaries — e.g., `MATCH (n)-[r]->(m) WHERE split(n.path,"/")[0..2] <> split(m.path,"/")[0..2] RETURN n.path, type(r), m.path LIMIT 10` (find any reference / import / definition that spans two sub-repos),
- **Then** at least one row is returned (i.e., GitNexus found at least one cross-repo edge in the operator's actual codebase) AND the row's `n.path` and `m.path` are confirmed to be in two different sub-repos.

**AC5 — Network audit during reindex (FR-CG-002, FR-CG-012, NFR-PRIV-001).**
- **Given** AC2 has passed (full reindex profile is known),
- **When** the operator captures `sudo tcpdump -i any -n -w /tmp/gitnexus-reindex.pcap 'tcp and not (host 127.0.0.1 or host ::1)' &` for the entirety of a fresh `npx gitnexus reindex --full`,
- **Then** post-capture inspection (`sudo tcpdump -r /tmp/gitnexus-reindex.pcap | grep -vE '127\.0\.0\.1|::1'`) shows ZERO TCP connections to `api.openai.com`, `api.anthropic.com`, or any `*.openai.com` / `*.anthropic.com` / `*.google.com` / `*.deepmind.com` LLM-API endpoint AND zero connections to GitNexus's own telemetry endpoint (if any — none is documented per architecture §5.3); evidence committed to `homelab-playbook/docs/decisions/gitnexus-privacy-audit.md`.

**AC6 — Hook-driven incremental reindex respects topology.**
- **Given** AC1 has passed AND E2-S04 hooks are live,
- **When** the operator makes a one-line edit in `homelab-playbook/`, commits via Bash tool (so PostToolUse fires), AND runs the AC4 cross-repo query immediately afterward,
- **Then** the changed file appears in the graph within 30 s of commit (per NFR-PERF-004) AND the cross-repo edge from AC4 still resolves (incremental reindex did not corrupt the cross-repo merge).

**AC7 — Topology config captured for repeatability.**
- **Given** AC1 has passed,
- **When** the operator extends `homelab-playbook/scripts/install-gitnexus-workstation.sh` with the exact topology-init command AND any per-machine config files written by GitNexus (e.g., `~/.gitnexus/config.json` if upstream uses that pattern) are referenced as either committed templates or generated-on-first-run,
- **Then** a fresh-rebuild walkthrough (scratch `$HOME` simulation) reaches "parent-folder topology over `~/workspace/homelab/`" with no manual prompts; idempotent on re-run.

## Implementation Notes

**Reference architecture sections:** §4.1 Code-graph layer (parent-folder topology row), §5.1 Privacy boundary (the "Source code (parsed by GitNexus tree-sitter on workstation) — stays on workstation" line), §11 No AR — this story closes both privacy ARs into evidence.

**Reference ADRs:** ADR-004 (parent-folder fit is the adoption rationale).

**Concrete commands:**

```bash
# AC1 — topology config
npx gitnexus init --root ~/workspace/homelab/    # or: gitnexus config set root ~/workspace/homelab/
npx gitnexus list-repos    # if available; otherwise inspect ~/.gitnexus/config.json

# AC2 — full reindex with timing
time npx gitnexus reindex --full 2>&1 | tee /tmp/gitnexus-full-reindex.log

# AC3 — Cypher: nodes from all 3 sub-repos
# via npx CLI:
npx gitnexus cypher 'MATCH (f:File) RETURN DISTINCT substring(f.path, 0, indexof(f.path,"/")) AS repo LIMIT 50'
# or via Claude Code MCP cypher tool inside a session

# AC4 — cross-repo edge
npx gitnexus cypher 'MATCH (n)-[r]->(m)
                     WHERE n.path STARTS WITH "homelab-playbook/"
                       AND m.path STARTS WITH "homelab/"
                     RETURN n.path, type(r), m.path LIMIT 10'

# AC5 — privacy audit
sudo tcpdump -i any -n -w /tmp/gitnexus-reindex.pcap 'tcp and not (host 127.0.0.1 or host ::1)' &
TCPDUMP_PID=$!
sleep 2
npx gitnexus reindex --full
sleep 5
sudo kill -INT $TCPDUMP_PID
sudo tcpdump -r /tmp/gitnexus-reindex.pcap | grep -E 'openai|anthropic|google|deepmind' && echo "FAIL" || echo "PASS"
sudo tcpdump -r /tmp/gitnexus-reindex.pcap | wc -l   # baseline noise count

# AC6 — incremental reindex test
echo "# topology test $(date)" >> homelab-playbook/_bmad-output/.touch
cd ~/workspace/homelab/homelab-playbook && git add . && git commit -m "test: E2-S05 incremental"
sleep 30
npx gitnexus cypher 'MATCH (f:File) WHERE f.path CONTAINS ".touch" RETURN f.path'
# rerun AC4 query; expect same / superset

# AC7 — install-script extension
# append to install-gitnexus-workstation.sh:
# if ! npx gitnexus list-repos 2>/dev/null | grep -q homelab-playbook; then
#   npx gitnexus init --root ~/workspace/homelab/
# fi
```

**Privacy-audit evidence note path:** `homelab-playbook/docs/decisions/gitnexus-privacy-audit.md`. Contents: the exact tcpdump command, full reindex wall-clock time, packet count summary, grep results for LLM hosts, AC4 cross-repo query result row count, ADR-004 + FR-CG-002 + FR-CG-012 + NFR-PRIV-001 closure verdict.

## Test Plan

**Pre-state:**
- E2-S04 done; hooks live.
- All three sibling repos exist at `~/workspace/homelab/{,homelab-bootstrap,homelab-playbook}/` with at least 1 commit each.
- Workstation has `tcpdump` and `sudo` available.

**Action sequence:**
1. Configure parent-folder topology (AC1).
2. Run full reindex with timing capture (AC2).
3. Run Cypher cross-repo coverage query (AC3).
4. Run Cypher cross-repo edge query (AC4); record row count.
5. Capture tcpdump during a fresh full reindex; inspect for LLM endpoints (AC5).
6. Make a commit in `homelab-playbook/`; wait 30 s; verify incremental reindex caught the change AND cross-repo edge still resolves (AC6).
7. Extend install script with topology-init guard (AC7).
8. Update privacy-audit evidence note.

**Post-state checks:**
- `npx gitnexus list-repos` (or config introspection) shows all three sibling repos.
- AC4 cross-repo edge query returns ≥ 1 row.
- AC5 evidence shows zero LLM-API outbound traffic during full reindex.
- AC6 incremental reindex < 30 s.
- Install script idempotent.

**Rollback:**
- `npx gitnexus reset` (or delete `~/.gitnexus/config.json` and re-run `setup`) reverts topology config.
- Combined with E2-S03 + E2-S04 rollback: full disable in < 5 minutes.

## Dependencies

- **Blocked by:** E2-S04 (hooks must be live for AC6 incremental test).
- **Blocks:** E2-S06 (smoke tests 1, 2, 3 all require parent-folder topology + cross-repo edges to be queryable), E2-S08 (KPI K1 token-reduction sample relies on cross-repo questions answering correctly).

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| GitNexus doesn't auto-discover all three sub-repos (e.g., requires explicit per-repo registration). | Med | Med — AC1 fails. | Fallback to `npx gitnexus add-repo` (or equivalent) for each sibling; document the multi-step procedure in install script. |
| Cypher query syntax differs slightly from openCypher (LadybugDB dialect). | Med | Low — query rewrite needed. | Operator iterates the AC3 / AC4 queries against `npx gitnexus cypher --help` examples; document final working queries in evidence note for E2-S06 reuse. |
| `tcpdump` captures unrelated workstation traffic, drowning AC5 signal. | Med | Low — needs filtering. | Filter by destination hosts in `grep -E` (LLM endpoints); supplement with `iptables --owner gitnexus-uid` rule if available. |
| AC4 query returns zero rows because the operator's codebase legitimately has no cross-repo references. | Low | High — would invalidate the killer-feature proof. | If zero rows, manually plant a known cross-repo reference (e.g., a script in `homelab-playbook/scripts/` that calls a path under `homelab/`) and rerun. |
| Privacy audit reveals an outbound connection to an unexpected GitNexus host (e.g., update-check). | Low | High — would violate FR-CG-012. | Document; investigate (could be tree-sitter language-pack download — one-time, not parsing-time); if persistent + parsing-related, escalate to ADR-004 amendment / re-evaluate. |

## Definition of Done

- [ ] AC1–AC7 all green and evidenced.
- [ ] `homelab-playbook/docs/decisions/gitnexus-privacy-audit.md` committed; AC5 closure verdict explicit.
- [ ] Cross-repo cypher query (AC4) saved in evidence note for reuse in E2-S06.
- [ ] `homelab-playbook/scripts/install-gitnexus-workstation.sh` extended with idempotent topology-init.
- [ ] FR-CG-002, FR-CG-003, FR-CG-012, NFR-PRIV-001 marked closed in PRD coverage tracker.
- [ ] Story status updated to `done`; OMEGA `omega_store(...)` records the privacy verdict + cross-repo proof.
