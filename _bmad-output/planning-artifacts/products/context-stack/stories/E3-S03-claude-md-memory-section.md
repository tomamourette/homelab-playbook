---
type: story
epic: E3
id: E3-S03
title: "Update CLAUDE.md with Memory (Graphiti) section"
size: 0.5d
priority: SHOULD
fr_refs: [FR-MEM-010]
adr_refs: [ADR-005, ADR-013, ADR-014]
status: draft
date: 2026-04-25
---

# E3-S03: Update CLAUDE.md with Memory (Graphiti) section

## User Story

As **tomamourette** (homelab operator), I want **a Memory (Graphiti) section in `~/.claude/CLAUDE.md` that tells Claude Code when to call `search_facts`/`search_nodes` (read) vs `add_episode` (write), with `group_id="tom-personal"` mandatory on every call**, so that **the model actually uses the Graphiti MCP server I just registered — closing OMEGA's actual failure mode (instructions weren't landing) and addressing AR8 (default group_id discipline)**.

## Background and Context

OMEGA's failure mode wasn't the MCP plumbing — it was that `omega_query` was never called because the session-start contract competed with `MEMORY.md` for the same model attention. Per ADR-005 and brief §8.1, the fix for Graphiti is *narrow nudge in CLAUDE.md*, not a session-start hook. Per architecture §11 AR8, `group_id` discipline is load-bearing — if the model omits it, writes go to Graphiti's literal `main` group instead of `tom-personal`, and recall hit-rate drops silently. Runbook §3 supplies the canonical CLAUDE.md block; this story adopts it verbatim with two additions: explicit AR8 note and tier-of-truth pointer (ADR-013).

This is a SHOULD per ADR-014 — the section won't ship rotting code, but its absence makes K5/K6 (recall + uplift KPIs) much harder to hit.

## Acceptance Criteria

### AC1: Memory (Graphiti) section exists in `~/.claude/CLAUDE.md`

- **Given** the deleted OMEGA section in `~/.claude/CLAUDE.md` (E1-S02 removed it; verify with `grep -i omega ~/.claude/CLAUDE.md` returning 0 matches)
- **When** I append a `## Memory (Graphiti)` section per the template in Implementation Notes
- **Then** `grep -c "^## Memory (Graphiti)" ~/.claude/CLAUDE.md` returns 1 and `grep -c "tom-personal" ~/.claude/CLAUDE.md` returns ≥ 2 (one in the read example, one in the write example).

### AC2: Section explicitly enumerates read triggers (`search_facts` / `search_nodes`)

- **Given** AC1
- **When** I run `awk '/^## Memory \(Graphiti\)/,/^## /' ~/.claude/CLAUDE.md` (extract the section)
- **Then** the extracted block contains the literal strings `search_facts`, `search_nodes`, "session start", "do you remember", and "before architecture decisions".

### AC3: Section explicitly enumerates write triggers (`add_episode`)

- **Given** AC1
- **When** the same extraction
- **Then** the block contains `add_episode`, "non-trivial decisions", "lessons learned", and "user says \"remember\"" (or equivalent — operator's preferred phrasing is acceptable).

### AC4: `group_id="tom-personal"` is called out as MANDATORY (closes AR8)

- **Given** AC1
- **When** the same extraction
- **Then** the block contains a line equivalent to: `Always pass group_id="tom-personal" so writes/reads stay in one namespace.` AND the word "mandatory" or "always" appears in connection with `group_id`.

### AC5: Tier-of-truth pointer present (ADR-013 cross-reference)

- **Given** AC1
- **When** the same extraction
- **Then** there is a line that explicitly disambiguates Graphiti from auto-memory (`MEMORY.md`) and from the wiki — phrasing similar to runbook §9: *"Use auto-memory for one-line preferences and pointers; use Graphiti for dated decisions and supersession trails; the wiki holds current-state runbooks."*

### AC6: Smoke-test — model invokes `search_facts` when prompted at session start

- **Given** ACs 1–5 land in CLAUDE.md and Graphiti MCP is registered (E3-S02)
- **When** I open a fresh Claude Code session in `~/workspace/homelab/homelab-playbook/` and prompt: *"What did we decide about pve2 storage?"* (a question where there's no Graphiti data yet — testing the call, not the result)
- **Then** the session transcript shows a tool call to `search_facts` (or `search_nodes`) with `group_id="tom-personal"` in the args; an empty-result response is acceptable for AC6 (E3-S05 covers the populated path).

### AC7: No conflict with auto-memory loader

- **Given** AC1
- **When** I run a fresh session and inspect the transcript
- **Then** `MEMORY.md` still loads at session start; the Memory (Graphiti) section does **not** instruct the model to skip or replace `MEMORY.md` (per brief NG6, auto-memory is augmented, not replaced).

## Implementation Notes

**Canonical block (lift from runbook §3, adapt for AR8 + ADR-013):**

```markdown
## Memory (Graphiti)

You have a Graphiti knowledge graph available via the `graphiti` MCP server.

When to write (use `add_episode`):
- After non-trivial decisions ("we chose X because Y")
- After lessons learned (failed approaches, gotchas)
- When the user says "remember X"

When to read (use `search_facts` and `search_nodes`):
- At session start, before any non-trivial task
- Whenever the user says "do you remember…", "what was that thing about…", or
  refers vaguely to past context
- Before architecture decisions, search for prior facts on the same topic

**Always pass `group_id="tom-personal"`** on every call. This is mandatory —
omitting it lands writes in Graphiti's default `main` group, where they will
not be found by reads against `tom-personal`.

Tier-of-truth division:
- `MEMORY.md` (auto-memory): one-line preferences and project pointers
- Graphiti: dated decisions, lessons, supersession trails
- `homelab-playbook/wiki/`: current-state runbooks and architecture (Phase 3)
- GitNexus: code structure (call `cypher`/`impact`/`context` tools)
```

- **Edit target:** `~/.claude/CLAUDE.md` (user-global), NOT the project CLAUDE.md at `homelab/CLAUDE.md` — the section is global so it applies across every Claude Code project (matches OMEGA's prior placement).
- **Pre-edit safety:** `cp ~/.claude/CLAUDE.md ~/.claude/CLAUDE.md.bak-pre-graphiti` so a one-line revert is `cp ~/.claude/CLAUDE.md.bak-pre-graphiti ~/.claude/CLAUDE.md`.
- **Section placement:** end of file, or replace the deleted OMEGA placeholder if E1-S02 left a hole. **Do NOT** put it ahead of the `## Memory (OMEGA)` if any zombie copy exists — verify with `grep -ni 'memory' ~/.claude/CLAUDE.md` first.
- **AR8 emphasis:** the **bold** marker around "Always pass `group_id`" is intentional — Markdown bold survives Claude Code's CLAUDE.md ingestion path.

## Test Plan

**Pre-flight:**
```bash
grep -ic "omega" ~/.claude/CLAUDE.md         # expect 0 (E1 cleaned)
grep -ic "graphiti" ~/.claude/CLAUDE.md      # expect 0 (about to add)
cp ~/.claude/CLAUDE.md ~/.claude/CLAUDE.md.bak-pre-graphiti
```

**Apply edit; then:**
```bash
# AC1
grep -c "^## Memory (Graphiti)" ~/.claude/CLAUDE.md         # 1
grep -c "tom-personal" ~/.claude/CLAUDE.md                  # >= 2

# AC2 + AC3 + AC4 + AC5 — extract section + greps
awk '/^## Memory \(Graphiti\)/,/^## [^M]/' ~/.claude/CLAUDE.md > /tmp/e3-s03-section.md
grep -c "search_facts\|search_nodes" /tmp/e3-s03-section.md   # >= 2
grep -c "add_episode" /tmp/e3-s03-section.md                  # >= 1
grep -ci "mandatory\|always" /tmp/e3-s03-section.md           # >= 1
grep -ci "MEMORY\.md\|wiki" /tmp/e3-s03-section.md            # >= 2

# AC6 — interactive
script -q /tmp/e3-s03-recall.log claude
# inside: "What did we decide about pve2 storage?"
grep -E "search_facts|search_nodes" /tmp/e3-s03-recall.log    # tool call observed
grep "tom-personal" /tmp/e3-s03-recall.log                    # group_id passed

# AC7 — verify MEMORY.md still loads
grep -i "MEMORY.md" /tmp/e3-s03-recall.log                    # auto-memory referenced
```

**Rollback:**
```bash
cp ~/.claude/CLAUDE.md.bak-pre-graphiti ~/.claude/CLAUDE.md
# Then re-run a session to verify the section is gone
```

## Dependencies

- **Blocks:** E3-S05 (smoke-tests assume the model knows when to call which tool); E3-S09 (K5 first-shot recall depends on the model actually firing `search_facts` — this is the prerequisite).
- **Blocked by:** E1-S02 (CLAUDE.md cleared of OMEGA), E3-S02 (Graphiti MCP registered — otherwise the instructions point at a nonexistent server).

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Operator forgets to also delete the OMEGA Memory section if any partial copy survives | Pre-flight `grep -ic "omega"` gate above (must be 0) |
| Section lands in wrong CLAUDE.md (project vs user-global) | Edit target explicit in Implementation Notes; verify with `realpath ~/.claude/CLAUDE.md` |
| Model still ignores the section (the OMEGA failure mode reprised) | E3-S09 K5 hit-rate gate is the binding observability — if K5 < 30% by week 2, escalate the section's emphasis (move to top, add explicit examples) |
| AR8 (default group_id) silently breaks recall | AC4 is the contractual statement; E3-S05 verifies behaviourally |
| CLAUDE.md edit conflicts with future updates from other tools | `~/.claude/CLAUDE.md.bak-pre-graphiti` preserved for ≤ 30 days |

## Definition of Done

- [ ] All ACs (AC1–AC7) pass
- [ ] `~/.claude/CLAUDE.md` updated with the canonical block
- [ ] Backup `~/.claude/CLAUDE.md.bak-pre-graphiti` exists for ≤ 30 day rollback window
- [ ] Section template also committed to `homelab-playbook/docs/runbooks/graphiti-claude-md-template.md` for the Ansible role to template (E4-S07 will pick this up)
- [ ] Acceptance test stub `AT-FR-MEM-010a` referenced in `tests/acceptance.md`
- [ ] One Claude Code session log captured at `/tmp/e3-s03-recall.log` showing the model invoked Graphiti tools with `group_id="tom-personal"`
