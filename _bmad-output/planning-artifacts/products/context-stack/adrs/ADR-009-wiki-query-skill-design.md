---
adr: 009
title: "wiki-query skill: read-on-demand with index.md as the entry point"
status: accepted
date: 2026-04-25
authors: tomamourette (via BMAD director Claude)
context_question: Q7
---

# ADR-009: wiki-query skill — read-on-demand with index.md as the entry point

## Context

PRD FR-WIKI-001 introduces a new `wiki-query` skill replacing the deleted `knowledge-query` orchestrator. Q7 asks which design pattern to use:

- **Read-on-demand:** the skill description tells the model how the wiki is shaped; the model picks files to read using `Read`. No precomputation.
- **Preload-index:** at session start, build a small searchable index (e.g., `wiki/_index.json` with title + slug + first 200 chars of each page); the skill loads that index into context and returns slugs to read.

The right answer depends on (a) wiki size, (b) read-cost model, and (c) what the model is structurally good at.

Constraints from the PRD:
- FR-WIKI-005: a Tier-1 query must complete in ≤ 200 ms wall-clock and consume zero Anthropic/OpenAI tokens for retrieval.
- FR-WIKI-009: the skill ships with no LLM dependency — retrieval is plain file-read.
- FR-WIKI-010: scaling to bulk content is explicitly out of scope.

Wiki size projection: at the operator's curation rate (3 entries seeded for Phase 3 exit; ~1-2 per week thereafter), the wiki reaches ~20 entries by the year mark and asymptotes well below 100. At ~2 KB/entry that's < 200 KB total — small enough to fit in any prompt context if needed, but not zero.

## Decision

**Use read-on-demand with `index.md` as the structural entry point**, not a pre-built JSON index.

### Mechanics

1. The `wiki-query` skill is registered in `~/.claude/skills/wiki-query/SKILL.md` with frontmatter directing Claude Code to use it for "homelab wiki", "tailscale policy", "pve cluster", "runbook", etc.
2. The skill body says (paraphrased):
   > "Read `homelab-playbook/wiki/index.md`. It is a small markdown file (< 5 KB) listing all wiki pages by category with one-line summaries. Identify the slug(s) most relevant to the user's question. Read those files with the `Read` tool (slugs are filenames). Cite the wiki pages by slug in your response."
3. `index.md` is auto-rebuildable by `scripts/wiki-lint.sh` (which already walks the tree per ADR-006); it is a markdown listing, not a JSON dump, so `cat index.md` is human-readable.
4. No precomputed JSON index. No embedding. No daemon.

### Why this beats preload-index at Context Stack scale

- The `index.md` is < 5 KB even at 100 entries (just title + slug + one-line summary per page). That fits comfortably in a system-prompt or session-start read; the gain from a separate JSON is zero.
- A precomputed JSON index would need to be regenerated on every wiki commit — adds a `wiki-lint.sh` step that competes with FR-WIKI-005's "200 ms file-read" promise (writes are slower than reads when no DB is involved).
- Read-on-demand is what Claude Code's model is *trained to do* — read files, identify by name, retrieve. Preload-index is fighting the grain.
- Preload-index would create a parallel data structure that drifts from the source markdown — every drift bug is a wrong-answer bug.

### Skill file structure (under `~/.claude/skills/wiki-query/`)

```
SKILL.md           # Frontmatter + body; the only file the model reads to know the skill
README.md          # Operator-facing notes (optional)
```

`SKILL.md` (sketch — final wording polished in Sprint 3):

```yaml
---
name: wiki-query
description: |
  Use this skill to answer questions about the homelab's curated knowledge base
  ("the wiki"). The wiki holds architecture decisions, runbooks, decision archives,
  and a glossary at homelab-playbook/wiki/. Triggers: "the wiki", "wiki page on",
  "tailscale policy", "pve cluster", "runbook for", "what's our convention for X",
  "what did we decide about X" (when X is not session-specific).
allowed-tools: Read
---
```

Body:
```markdown
# wiki-query

When invoked:
1. Read `homelab-playbook/wiki/index.md` first — it lists every wiki page by
   category with a one-line summary and a slug.
2. From the user's question, identify 1-3 most-relevant slugs.
3. Read those pages directly via the `Read` tool. Slugs map to filenames in
   the same tree (e.g., slug `pve-cluster-topology` → `architecture/pve-cluster-topology.md`).
4. Cite each page by slug in your response so the user can navigate further.

If `index.md` does not exist, tell the user the wiki has not been initialised
and recommend running the Sprint 3 wiki-init story.

Do not invoke any LLM, embedding, or external service. This is a plain file-read
skill.
```

## Consequences

**Positive.**
- Sub-200 ms file-read for the entry point (`index.md`) and for the relevant page reads — meets FR-WIKI-005.
- Zero retrieval tokens — meets the FR-WIKI-005 promise (LLM tokens are only spent if the model summarises content into the response, which is expected and out of the retrieval budget).
- No drift surface — the markdown tree is the single source of truth.
- Operator can rename, reorder, and reorganise pages by editing `index.md` + filenames; the skill works the same.
- The index is human-grep-able (`grep tailscale homelab-playbook/wiki/index.md`) — useful even without the skill.

**Negative.**
- The model must read `index.md` first; that's a one-extra-Read-call session-start cost. < 5 KB is < 100 ms wall-clock, well within the FR-WIKI-005 budget.
- Cold-cache cases (first session of the day on a slow disk) might exceed 200 ms on a very large index; observed risk only if the wiki grows past expectations.
- The model can only find what `index.md` advertises — if a page exists but isn't in the index, it's invisible. Mitigated by `wiki-lint.sh` checking all files are indexed.

**Neutral.**
- Slug-based routing (vs path-based) is a design choice from ADR-006 that this skill inherits.

## Alternatives Considered

1. **Preload JSON index at session start** — rejected. Adds a precomputation step, drift surface, and parallel data format for a corpus that fits comfortably in a `cat index.md`.
2. **Wiki-as-MCP-server (e.g., a tiny `read_wiki(slug)` MCP tool)** — rejected. Adds daemon overhead and a process surface for what is a markdown-tree read. ADR-005 reserves `wiki-query` as the only intentional skill-tier integration. If MCP becomes ergonomically cheap (e.g., zero-config local-stdio with no daemon), revisit.
3. **Embedding-based wiki search (a Tier-1 lite version of Graphiti)** — rejected. Defeats the "zero-MCP, zero-LLM" tier goal (FR-WIKI-009); duplicates Graphiti's job poorly.
4. **Auto-loaded `index.md` content in `CLAUDE.md`** — rejected. Couples wiki state to `CLAUDE.md`; loads even when not needed. Skill-on-demand is leaner.

## Validation / Exit Ramp

- **Validation:** at Phase 3 exit (FR-WIKI-006), each of the three seed entries is read by ≥ 3 distinct Claude Code sessions; operator log captures the trigger ("user asked for X → wiki-query → page Y returned").
- **Exit ramp:** if read-on-demand underperforms (e.g., model misses relevant pages because `index.md` summaries are too terse), the cheapest fix is to expand summaries in `index.md` (still markdown, no architecture change). If that fails, build a `wiki/_index.json` regenerator and switch the skill to preload — single file, no other change.
- **Reversal trigger:** wiki grows past 100 entries AND `index.md` exceeds 20 KB AND model demonstrably misses pages → switch to preload-index.

## References

- PRD FR-WIKI-001 through FR-WIKI-010, NFR-PERF-003
- ADR-005 (skill-tier exception), ADR-006 (wiki schema)
- Brief Q2 closed (location), Q3 closed (architecture phase resolution)
- Q7 explicit close
