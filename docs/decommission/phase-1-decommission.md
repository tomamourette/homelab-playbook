# Context Stack — Phase 1 Decommission Runbook

> Operator-facing record of the OMEGA + MemPalace decommission executed 2026-04-25 as Sprint 1 / Epic E1 of the Context Stack BMAD product.

## What was decommissioned

- **OMEGA** (omega-memory v1.4.3) — local persistent-memory MCP system; daemon + workstation install + ai-dev-omega-memory Ansible role + ai-dev-hermes/wire-omega.yml + Hermes config.yaml.j2/defaults/verify/host_vars OMEGA conditionals
- **MemPalace** (v3.3.0) — local knowledge-graph MCP server; ~/.mempalace/ + ai-dev-mempalace Ansible role + 3 Hermes mempalace-* skills (kg-query/diary/search) + knowledge-query orchestrator skill + Hermes config.yaml.j2/defaults/verify mempalace conditionals + Hermes wiki/article-ingest skill prose references

## Why

Per ADR-010 + readiness-check.md (PASS-WITH-NOTES verdict, Sprint 1 GO):
- OMEGA was effectively dormant: 9 memories in 18 days, sqlite-vec broken, query hit-rate 1/8, MCP tools not surfaced, ct-dev-homelab verify failing for ~weeks (model.onnx missing)
- MemPalace was empty: 0 tables / 0 rows on workstation, never deployed live to ct-dev-homelab
- Both replaced architecturally per ADR-005 (MCP-first over skill-first lesson) by Graphiti (memory) + GitNexus (code-graph) — to be adopted in Sprints 2-5

## What replaced it (forward reference)

- **Sprint 2 (E2)**: GitNexus v1.6.3 (npm, Node.js) — code-graph layer
- **Sprint 3 (E3)**: Graphiti v1.0.2 + FalkorDB — memory layer with bi-temporal validity
- **Sprint 4 (E4 part A)**: LLM Wiki tier under homelab-playbook/wiki/ + wiki-query skill + daily $1 hard-cap
- **Sprint 5 (E4 part B)**: LiteLLM bridge to hybrid_gemma_serving + container deploy + observability

See: `homelab-playbook/_bmad-output/planning-artifacts/products/context-stack/README.md` for the full product index.

## Commit lineage

ADR-010 specifies 8-commit non-squash structure on `decommission/context-stack-phase-1` branch. Across 2 repos:

| # | Story | Commit (homelab-infra unless noted) | Description |
|---|-------|-------------------------------------|-------------|
| 1 | E1-S01 | (workstation only) | Disable OMEGA hooks in ~/.claude/settings.json |
| 2 | E1-S02 | (workstation only) | Remove disabled OMEGA hook entries |
| 3 | E1-S03 | 20a356b | Uninstall omega-memory + remove ai-dev-omega-memory role + Hermes OMEGA conditionals |
| 4 | E1-S04 | 1109a0f | Remove MemPalace store + ai-dev-mempalace role + Hermes mempalace skills |
| 5 | E1-S05 | 9a6fbbc | Remove Hermes wire-mempalace task + knowledge-query orchestrator |
| 6 | E1-S06 | 3020f48 | Remove MemPalace conditionals from Hermes Jinja + defaults + verify |
| 7a | E1-S07 part 1 | 1442225 | Clean prose references in Hermes wiki + article-ingest skills |
| 7b | E1-S07 part 2 | (homelab-playbook) <HEAD> | Author phase-1-decommission.md runbook |
| 8 | E1-S08 | <SHA> | Hermes verify + grep + process gates (Sprint 1 close) |
| 9 | E1-S09 | <SHA> | Forward-protection pre-push hook + decommission tag (post-merge) |

(Commits 1-2 are workstation-only and have no SHA in any repo; commits 3-7a SHAs are from homelab-infra; commit 7b appears as `<HEAD>` because this commit is itself the doc.)

## Rollback

Per ADR-010 §Decision: PR uses **merge-commit, not squash**, preserving per-commit revertability:
- Workstation: `cp ~/.claude/settings.json.bak.20260425-114500 ~/.claude/settings.json` + `pip install omega-memory==1.4.3` + `tar -xzf /tmp/omega-pre-decommission-2026-04-25.tar.gz -C ~/`
- Repo (per commit): `git -C <repo> revert <SHA>`

Backups:
- `~/.claude/settings.json.bak.20260425-114500` (1915 bytes, pre-Sprint-1 settings)
- `/tmp/omega-pre-decommission-2026-04-25.tar.gz` (132 KB, OMEGA data)
- `/tmp/mempalace-pre-decommission-2026-04-25.tar.gz` (928 bytes, MemPalace data)

## Validation

- ansible-playbook --syntax-check on deploy-ai-dev-container.yml limited to ct-dev-homelab: PASS (after each commit)
- Final repo-wide grep for `mempalace|omega-memory|wire-omega|wire-mempalace|ai-dev-omega-memory|ai-dev-mempalace|ai_dev_hermes_omega|ai_dev_hermes_mempalace`: zero results (excluding tooling state, BMAD output, historical fix-logs)
- Pre-push hook + tag installed in E1-S09 enforces forward protection

## References

- [Context Stack product](../../_bmad-output/planning-artifacts/products/context-stack/README.md)
- [ADR-010 — Decommission as single PR](../../_bmad-output/planning-artifacts/products/context-stack/adrs/ADR-010-decommission-as-single-pr.md)
- [ADR-005 — MCP-first over skill-first](../../_bmad-output/planning-artifacts/products/context-stack/adrs/ADR-005-mcp-first-over-skill-first.md)
- [Readiness check (PASS-WITH-NOTES, Sprint 1 GO)](../../_bmad-output/planning-artifacts/products/context-stack/readiness-check.md)
- [Pre-decommission baseline](baseline-pre-decommission.txt)
