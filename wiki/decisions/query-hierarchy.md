---
title: "Context Stack query hierarchy — which tier to consult first"
slug: query-hierarchy
category: decisions
last_reviewed: 2026-04-27
owner: tomamourette
related_pages:
  - _schema
  - index
  - wiki-query-skill
  - wiki-exit-ramp
  - gitnexus-exit-ramp
  - graphiti-exit-ramp
  - auto-memory-exit-ramp
related_frs:
  - FR-WIKI-001
  - FR-WIKI-007
  - FR-MEM-003
  - FR-CG-001
related_adrs:
  - ADR-006
  - ADR-009
  - ADR-013
status: stable
supersedes: []
superseded_by: null
---

# Context Stack query hierarchy

## Summary

Four tiers of truth, each with a distinct purpose: **wiki** (pre-synthesized
current state), **GitNexus** (structural code-graph), **Graphiti** (dated
conversational/temporal trail), **auto-memory** (session-bound one-line
pointers). Pick the cheapest tier that *owns* the question's shape; fall
back outward only on miss. This page is the canonical routing table per
ADR-013 (FR-WIKI-007).

## Context

ADR-013 divides authoritative knowledge across four tiers because no single
substrate covers all the question shapes the operator asks Claude Code in a
homelab session. Each tier has a real comparative advantage:

- **Tier 1 — Wiki** (`homelab-playbook/wiki/`): markdown + YAML, zero MCP,
  < 200 ms file-read. Holds **current state** — architecture, runbooks,
  policies. Updated by hand, lives in git.
- **Tier 2 — GitNexus** (MCP at port 4747, LadybugDB-backed): structural
  AST graph over `~/workspace/homelab/`. Holds **code structure** — what
  is defined, what calls what, what imports what.
- **Tier 3 — Graphiti** (MCP at port 8000, FalkorDB-backed): bi-temporal
  graph keyed on `group_id=tom_personal`. Holds **dated decisions** — when
  did X happen, what superseded what, what was the lesson learned.
  Note: underscore not hyphen — FalkorDB's RediSearch backend treats `-`
  as the NOT operator and silently fails ingestion of group_ids
  containing hyphens (confirmed 2026-04-28 during seed batch).
- **Tier 4 — Auto-memory** (`~/.claude/projects/-home-developer-workspace-homelab/memory/`):
  markdown files with a `MEMORY.md` index. Holds **one-line stable facts /
  preferences / pointers**. Loaded passively at session start.

Without an explicit routing table the model double-queries (waste), wrong-
queries (drift), or misses (silence). This page binds the routing rule
explicit so skills, agents, and the operator can teach themselves the
order in under a minute.

## Procedure / Decision

### Question-shape routing table

| Question shape | First tier | Fallback (in order) | Pitfall |
|---|---|---|---|
| "What did we decide about X?" (architecture / policy) | Wiki — `wiki-query` skill | Graphiti `search_facts` (if conversational/dated) → fail-open | Don't ask Graphiti for crystallised architecture; it may have the seed episode but not the synthesised page |
| "What's our convention for X?" | Wiki — `wiki-query` skill | grep over `homelab-playbook/` → fail-open | Don't grep `_bmad-output/` for conventions; conventions live in `wiki/architecture/` |
| "What's the runbook for X?" | Wiki (`runbooks/`) — `wiki-query` skill | Graphiti for dated lessons → operator memory | Conflating a runbook (durable procedure) with a story spec (one-off plan) |
| "What functions call X?" / "Where is Y defined?" | GitNexus — `mcp__gitnexus__query` / `cypher` / `impact` | grep `~/workspace/homelab/` (manual) → fail-open | Don't ask the wiki for code structure; it goes stale instantly |
| "What changed in repo Z this week?" | GitNexus `detect_changes` | git log → fail-open | Don't rely on auto-memory for repo state |
| "When did Tom set up X?" / "When did X migrate?" | Graphiti `search_facts` (filtered by date) | git log → operator journal | Don't ask the wiki "when" — wiki holds *current* state, not the trail |
| "Why did we supersede X with Y?" | Graphiti `search_facts` (supersession edges) | Wiki frontmatter `superseded_by` field → ADR file | Don't infer supersession from wiki diff; the *reason* lives in Graphiti, the *fact* lives in wiki frontmatter |
| "What was discussed in last session?" | Auto-memory (passive context) | Graphiti recent episodes (`group_id=tom_personal`) | Don't ask the wiki for session content — wiki is durable, sessions are not |
| "What's Tom's preference for X?" | Auto-memory (`feedback_*.md`, `user_*.md`) | Graphiti episodes tagged `user_preference` | Don't bury preferences in Graphiti when they fit a one-liner |
| "What's the IP / VMID / path of CT-X?" | Auto-memory (`project_*.md` pointers) | Wiki `projects/` if the page exists → terraform inventory | Don't promote a one-liner to wiki; promote only when sub-bullets emerge |
| "What does function F do?" (semantic) | Read source (via Claude Code Read tool, often via GitNexus locating it first) | Wiki if a runbook documents it | LLM-only summarisation without grounding is hallucination-prone |

### Tier-of-truth violations (anti-patterns)

These are the failure modes the routing table is designed to prevent. Each
maps to a real pitfall observed in the OMEGA / MemPalace incoherence the
Context Stack replaces (ADR-013 §Alternatives Considered, item 1).

- **Asking Graphiti for an architecture decision** → you may get a dated
  episode without the synthesised current-state. Use the wiki first.
- **Asking the wiki for last-week's session content** → wiki is durable
  by definition; session content goes to auto-memory or Graphiti.
- **Asking auto-memory for "why did we choose X"** → auto-memory holds
  the *what* (one-liner pointer); the *why* lives in Graphiti episodes
  or in an ADR cross-referenced from the wiki.
- **Asking the wiki "what calls function F"** → wiki goes stale at the
  speed of code. Use GitNexus.
- **Writing the same fact in three tiers** → the bidirectional rules in
  ADR-013 §Decision (wiki↔Graphiti supersession, auto-memory→wiki
  promotion) prevent this; respect them at write time.

### Routing rules for skills and agents

Claude Code skills, sub-agents, and any future automation MUST sequence
queries in cost order — cheapest tier first, MCP tiers only when the
file-tier misses. The current implementation surfaces:

1. **`wiki-query` skill** (Tier 1, ADR-009): reads `wiki/index.md` first,
   then 1-3 relevant pages on-demand. Zero MCP, zero LLM, zero embedding.
   See [wiki-query skill](wiki-query-skill) for trigger phrases.
2. **GitNexus MCP tools** (Tier 2): invoke `mcp__gitnexus__list_repos` to
   confirm the registry, then `query` / `context` / `impact` / `cypher` for
   structural questions. Cache by query shape; tool calls are sub-second
   but not free.
3. **Graphiti MCP tools** (Tier 3): invoke `search_facts` with a
   `group_id=tom_personal` filter for dated/conversational questions.
   Graphiti is the only tier that answers "when" cleanly.
4. **Auto-memory** (Tier 4): loaded passively at session start; not
   queried-on-demand. The session prelude includes `MEMORY.md` content;
   if a one-liner pointer is missing, write it (auto-memory is the write
   target for new pointers, per ADR-013).

Do not invert the order — invoking GitNexus or Graphiti before the wiki
spends MCP round-trip cost on a question the wiki could have answered for
free. The 4-week pilot's K6 (subjective uplift) is partially gated on the
operator observing this order in transcripts.

### When the question doesn't fit any tier

Three legitimate fail-open paths:

- **Read the source directly** (Claude Code `Read` tool) — for code-level
  semantics no graph captures (intent, naming rationale, inline TODOs).
- **Run the actual command** (Claude Code `Bash` tool) — for live system
  state (`docker ps`, `pvesh get`, `ip a`). No tier of truth replaces a
  fresh `docker stats`.
- **Ask the operator** — for product judgement / preferences not yet
  captured. Then *write the answer back* into the appropriate tier per
  ADR-013's write-side rules.

### Exit ramps for each tier

Every tier has a documented exit ramp (FR-WIKI-007 + each tier's PRD
portability requirement). When in doubt about how to migrate / export /
recover from a tier, consult its exit-ramp runbook:

- [Wiki exit ramp](wiki-exit-ramp) — clone the repo, you have the data.
- [GitNexus exit ramp](gitnexus-exit-ramp) — NDJSON dump via ADR-012
  wrapper script; includes the **container `${HOME}` path-resolution
  divergence** operator note from E4-S09.
- [Graphiti exit ramp](graphiti-exit-ramp) — RDB restore (recovery) +
  per-graph Cypher export (audit-only) per ADR-007 amended.
- [Auto-memory exit ramp](auto-memory-exit-ramp) — directory copy with
  project-path encoding update.

## Cross-references

- [Wiki page schema](_schema) — frontmatter spec consumed by Tier 1.
- [wiki-query skill](wiki-query-skill) — Tier 1 retrieval mechanism.
- ADR-006 — wiki-as-file-tree decision.
- ADR-009 — wiki-query skill design (read-on-demand).
- ADR-013 — tier-of-truth division (the source rule this page implements).
- PRD FR-WIKI-007 — "unified query hierarchy" requirement.

## Pitfalls

- **Tier-of-truth violations** (see anti-patterns above): asking the wrong
  tier returns wrong-shaped or empty answers. The routing table is the
  fix; the bidirectional write rules in ADR-013 prevent regression.
- **Skipping the wiki to "save time"**: the wiki is the cheapest tier
  (file read, < 200 ms). Skipping it to "go straight to the source" is
  almost always slower because the wiki holds the synthesis and source
  reading without that synthesis is unbounded.
- **Treating the routing table as exhaustive**: it isn't. The fail-open
  paths (read source, run command, ask operator) are first-class. The
  table covers the *common* shapes; uncommon shapes fall back to
  judgement.
- **Stale wiki masquerading as current**: every wiki page has a
  `last_reviewed` field; the lint warns at > 6 months. If a page reads
  as authoritative but its `last_reviewed` is stale, treat it as a hint
  and verify against the live system before acting.
