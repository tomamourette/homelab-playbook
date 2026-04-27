---
name: wiki-query
description: |
  Look up authoritative pre-synthesized knowledge from the homelab wiki at
  `~/workspace/homelab/homelab-playbook/wiki/`. Trigger on: "the wiki",
  "wiki page on X", "tailscale policy", "pve cluster", "runbook for X",
  "what's our convention for X", "what did we decide about X" (when X is
  not session-specific). Reads `index.md` first, then 1-3 relevant pages
  on-demand. Does NOT preload the wiki tree, does NOT call any LLM /
  embedding / MCP service. For session-specific dated decisions prefer
  Graphiti's `search_facts`; for live code structure prefer GitNexus.
allowed-tools: Read
---

# wiki-query

Use this skill to answer questions about Tom's homelab from the curated
markdown wiki at `~/workspace/homelab/homelab-playbook/wiki/`. The wiki holds
*current-state* authoritative knowledge: architecture decisions, runbooks,
distilled prior decisions, glossary terms, and per-project pointers.

## When to use

- Question is about homelab infrastructure topology, runbooks, conventions,
  decisions, or glossary terms (e.g., "tailscale policy for phone-facing
  services", "describe the PVE cluster topology", "how do we rotate auth
  keys").
- The answer should be reproducible and citable from a single source of
  truth, not freshly inferred.
- NOT for live state or session-specific facts — those go to Graphiti
  (`search_facts`), GitNexus (code structure), or the auto-memory pointer
  index. See ADR-013 for the tier-of-truth division.

## How to use (four steps, in order)

1. **Read `~/workspace/homelab/homelab-playbook/wiki/index.md` first.** It is
   a small markdown file (< 5 KB at bootstrap) that lists every wiki page by
   category with a one-line summary and a slug.
2. **Identify 1-3 most-relevant slugs** from the index, based on the user's
   question. Be specific: pick slugs whose titles or summaries match the
   user's noun phrase, not just any topic-adjacent page.
3. **Read those pages directly via the `Read` tool.** Slugs map to filenames
   in the same tree, with the `category` frontmatter selecting the directory:
   - slug `pve-cluster-topology` (category `architecture`) →
     `~/workspace/homelab/homelab-playbook/wiki/architecture/pve-cluster-topology.md`
   - slug `decommission-context-stack-phase-1` (category `runbooks`) →
     `~/workspace/homelab/homelab-playbook/wiki/runbooks/decommission-context-stack-phase-1.md`
   - slugs `_schema` and `index` are root-level meta pages.
4. **Cite each consulted page by slug** in your response so the user can
   navigate further. Use the form: `From the wiki: [<page title>](<slug>)`.

## Fallback: wiki not initialised

If `~/workspace/homelab/homelab-playbook/wiki/index.md` does not exist (e.g.,
the wiki has been deleted, or the operator is on a fresh checkout that
pre-dates E4-S01), tell the user the wiki has not been initialised and
recommend reviewing the Phase 3 wiki-init stories (E4-S01, E4-S02). **Do
NOT** attempt:

- Filesystem search outside the wiki tree.
- Embedding-based search.
- Any MCP tool fallback (Graphiti, GitNexus, etc.).
- LLM-only synthesis dressed up as wiki content.

Just say the wiki is absent and stop.

## Constraints

- This is a plain file-read skill. No LLM, embedding, or external service
  call is permitted at retrieval time (FR-WIKI-009).
- Do NOT batch-read the entire wiki tree at invocation. Read `index.md` and
  then only the 1-3 pages your slug picks identified.
- Cross-references between wiki pages (slug-based) are valid — follow them
  if the first page redirects you.
- If a page's `last_reviewed` frontmatter is older than ~6 months, add a
  one-line note in your response: `Wiki page <slug> was last reviewed
  <date> — verify currency before acting.` (The lint script warns on this
  too; the skill surfaces it to the user.)
- The slug-to-filename mapping is deterministic — do not invent slugs that
  aren't listed in `index.md`.
