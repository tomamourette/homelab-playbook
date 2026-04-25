---
adr: 013
title: "Tier-of-truth division — wiki vs Graphiti vs auto-memory"
status: accepted
date: 2026-04-25
authors: tomamourette (via BMAD director Claude)
context_question: null
---

# ADR-013: Tier-of-truth division — wiki vs Graphiti vs auto-memory

## Context

PRD FR-WIKI-007 mandates a "unified query hierarchy" document. The four tiers are defined in PRD glossary §14:

- **Tier 1** — LLM Wiki (file-based, zero-MCP, < 200 ms file-read).
- **Tier 2** — GitNexus code-graph (MCP, AST).
- **Tier 3** — Graphiti memory (MCP, bi-temporal).
- **Tier 4** — Claude Code auto-memory (`MEMORY.md`, deterministic markdown).

But "query hierarchy" answers half the question. The other half is **write hierarchy**: when the operator captures a fact, where does it go? Without a clean rule, the operator double-writes (the install-plan §9 explicit warning), facts drift between tiers, and "which tier is right?" becomes unanswerable.

The graphiti install plan §9 already gives the rule sketch:
- `MEMORY.md` for grep-able fast facts and pointers.
- Graphiti for "anything dated, anything that supersedes prior state."
- "Don't double-write."

This ADR formalises the rule and adds the wiki tier (which post-dates the install plan).

## Decision

### Single rule of thumb (operator decision card)

```
Is it a one-line stable fact / preference / pointer?
   → Tier 4 (auto-memory MEMORY.md)
   Examples: "ct-quant-trading is at 192.168.50.162", "user prefers TDD"

Is it a synthesised, durable artifact (architecture, runbook, policy)?
   → Tier 1 (wiki — homelab-playbook/wiki/)
   Examples: "Tailscale-only network policy", "PVE node rebuild runbook"

Is it a dated decision, lesson, or supersession (validity matters)?
   → Tier 3 (Graphiti add_episode, group_id=tom-personal)
   Examples: "On 2026-04-24, pve2 migrated LVM→ZFS", "lesson learned: ha-manager set --state stopped is rejected on error-state"

Is it source-code structure (definitions, references, calls)?
   → Tier 2 (GitNexus, automatic — no operator write action)
   Examples: "which roles call mempalace-search?" — answered by GitNexus query, never by manual write.
```

### Bidirectional rule (avoiding double-write)

- **Wiki → Graphiti supersession:** when a wiki page is superseded, set its frontmatter `superseded_by: <slug>` (ADR-006 schema) AND write a Graphiti episode capturing the date and reason. The wiki holds *current state*; Graphiti holds *the trail of how state evolved*.
- **Graphiti → Wiki promotion:** if a Graphiti episode crystallises into a stable pattern referenced in three+ sessions, promote a distilled summary into the wiki. The Graphiti episode stays (history); the wiki page is the new front door.
- **Auto-memory → Wiki promotion:** auto-memory entries that grow past one line (start having sub-bullets, code snippets) are wiki candidates. Migrate the entry, leave a one-line pointer in `MEMORY.md`.

### Read hierarchy (FR-WIKI-007's "query order")

For an operator question, Claude Code consults in order until satisfied:

1. **Wiki (Tier 1)** — `wiki-query` skill reads `index.md`, then relevant pages. Cheapest. < 200 ms wall, zero retrieval tokens.
2. **GitNexus (Tier 2)** — for "where is X defined?" / "what calls Y?" / "structural" questions. MCP tool calls. Sub-second.
3. **Graphiti (Tier 3)** — for "what did we decide about X?" / "when did Y change?" / "why did Z?" questions. MCP tool calls. ~100-500 ms.
4. **Auto-memory (Tier 4)** — passively loaded; not queried-on-demand. The session-start context.

## Consequences

**Positive.**
- A single decision card the operator can teach themselves in under a minute, write next to their keyboard, and follow without thinking.
- The bidirectional rules prevent the "I've written this fact in three places" drift. Doubles as a maintenance hint.
- Read order matches cost order — cheapest tier first; the model is structurally encouraged to consult the wiki before invoking MCP tools.
- Captures the install-plan §9 "Don't double-write" rule with concrete examples per tier.

**Negative.**
- Edge cases will occur ("is a deploy-runbook a wiki page or a Graphiti episode?"). The rule favours wiki for structural durability; Graphiti for temporal/dated/superseded. Operator judgement remains the final tiebreaker.
- The promotion rules (auto-memory → wiki, Graphiti → wiki) are operator chores; without enforcement, drift accumulates. Mitigated by `wiki-lint.sh` `last_reviewed: ≤ 6 months` warning.

**Neutral.**
- The query hierarchy doc itself (FR-WIKI-007) is a wiki page at `homelab-playbook/wiki/architecture/context-stack-query-hierarchy.md`, authored as one of the three Phase 3 seed entries (FR-WIKI-006).

## Alternatives Considered

1. **No formal rule (operator picks intuitively per fact)** — rejected. This is exactly how OMEGA + MemPalace + auto-memory drifted into incoherence.
2. **One-tier-rules-them-all (everything in Graphiti, or everything in wiki)** — rejected. Each tier has a real comparative advantage; collapsing them loses K1-K6 differentiation (e.g., wiki's < 200 ms, Graphiti's bi-temporal).
3. **Auto-routing via skill (the model picks the tier)** — rejected. Adds a layer of indirection and an LLM call to a tier system whose purpose is to *avoid* unnecessary LLM calls.

## Validation / Exit Ramp

- **Validation:** at Phase 3 exit, the query-hierarchy wiki page is one of the three seed entries (FR-WIKI-006); operator log shows ≥ 3 sessions where the model correctly chose the cheaper tier first.
- **Exit ramp:** if the rule causes confusion in practice, simplify to two tiers (wiki for state, Graphiti for trail) and demote auto-memory to "passive context only, not a write target". Single-day refactor.
- **Reversal trigger:** if K6 (subjective uplift) is low because the model is consulting tiers in the wrong order, audit `CLAUDE.md` to make the order explicit; revisit if `CLAUDE.md` instruction is insufficient.

## References

- PRD FR-WIKI-007, glossary §14 (Tier 1-4 definitions)
- `graphiti-claude-code-install-plan-2026-04-25.md` §9 (clean division of responsibility, "Don't double-write" rule)
- ADR-006 (wiki schema, supersession field)
- ADR-009 (wiki-query skill)
