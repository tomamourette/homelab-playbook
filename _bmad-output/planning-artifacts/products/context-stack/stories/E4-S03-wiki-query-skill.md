---
type: story
epic: E4
id: E4-S03
title: "Author wiki-query skill (read-on-demand, ADR-009)"
size: 1d
priority: MUST
fr_refs: [FR-WIKI-001, FR-WIKI-003, FR-WIKI-005, FR-WIKI-009, FR-DEP-005]
adr_refs: [ADR-009, ADR-005, ADR-006]
status: draft
date: 2026-04-25
---

# E4-S03: Author wiki-query skill (read-on-demand, ADR-009)

## User Story

As **tomamourette** (homelab operator), I want **a thin Claude Code skill at `~/.claude/skills/wiki-query/SKILL.md` that triggers on documented prompts ("the wiki", "tailscale policy", "what did we decide about X", etc.), reads `homelab-playbook/wiki/index.md` first, identifies relevant slugs, and reads those pages directly via the `Read` tool — with NO LLM/embedding/MCP dependency**, so that **Tier-1 wiki retrieval costs zero retrieval tokens, completes in ≤ 200 ms wall-clock per page-read, and replaces the deleted `knowledge-query` orchestrator (which was decommissioned in E1-S05) with a simpler, narrower, ADR-009-compliant surface**.

## Background and Context

ADR-009 (closes Q7) ships the read-on-demand pattern: `index.md` is the structural entry point; the model picks slugs and calls `Read` directly. ADR-005 (MCP-first over skill-first) explicitly carves out `wiki-query` as the **single intentional skill bet** in this product — every other tier is MCP-native. Per FR-WIKI-009, the skill ships with no LLM dependency: retrieval is plain file-read.

This story replaces the `knowledge-query` orchestrator deleted in E1-S05 (FR-DEC-006). The new skill is structurally smaller: no LLM call to "decide which tier", no embedding lookup, no MCP roundtrip — just a description of the wiki shape and a call to `Read`.

## Acceptance Criteria

### AC1: Skill is installed at the canonical Claude Code skills location

- **Given** the operator's workstation
- **When** I run `ls ~/.claude/skills/wiki-query/`
- **Then** output shows at minimum `SKILL.md`; optional supplementary file `README.md` (operator-facing notes); no other files

### AC2: SKILL.md frontmatter conforms to the Claude Code skill spec

- **Given** `~/.claude/skills/wiki-query/SKILL.md` exists
- **When** I read its YAML frontmatter
- **Then** it contains `name: wiki-query`, a multi-line `description:` listing the trigger phrases (per ADR-009 §Decision: "the wiki", "wiki page on", "tailscale policy", "pve cluster", "runbook for", "what's our convention for X", "what did we decide about X" when X is non-session-specific), and `allowed-tools: Read` — and ONLY `Read` (no `Bash`, no `WebFetch`, no MCP tools — enforces FR-WIKI-009)

### AC3: SKILL.md body specifies the four-step retrieval procedure

- **Given** AC1 holds
- **When** I read the body of SKILL.md
- **Then** it instructs the model in this order: (1) Read `homelab-playbook/wiki/index.md` first; (2) From the user's question, identify 1-3 most-relevant slugs from the index; (3) Read those pages directly via `Read` (slugs map to filenames in the wiki tree, e.g., `pve-cluster-topology` → `architecture/pve-cluster-topology.md`); (4) Cite each consulted page by slug in the response

### AC4: SKILL.md includes the "wiki not initialised" fallback

- **Given** AC1 holds
- **When** I read SKILL.md
- **Then** it instructs the model: if `index.md` does not exist (e.g., wiki has been deleted/never-created), tell the user the wiki has not been initialised and stop — do NOT attempt embedding-based search, MCP fallback, or LLM synthesis

### AC5: Skill triggers on documented phrases — observed via dry-run

- **Given** the skill is installed and E4-S02's seeds are committed
- **When** I run a Claude Code session with prompt "what's our tailscale policy for phone-facing services?"
- **Then** Claude Code invokes the `wiki-query` skill (visible in transcript), reads `homelab-playbook/wiki/index.md` first, then reads `architecture/network-tailscale-policy.md`, and the response cites the slug `network-tailscale-policy`

### AC6: Skill triggers correctly across all 5 seed-coverage prompts

- **Given** AC5 mechanics work
- **When** I run 5 Claude Code sessions with prompts: (a) "what's our tailscale policy for phone-facing services?", (b) "describe the PVE cluster topology", (c) "how did we decommission MemPalace and OMEGA?", (d) "what's the hybrid-gemma-serving plan?", (e) "what is the context-stack project?"
- **Then** each session triggers `wiki-query`, reads `index.md` then the relevant seed, and cites the seed slug; transcripts saved to `/tmp/e4-s03-skill-smoke-{a..e}.log`

### AC7: Wiki page-read latency is ≤ 200 ms (FR-WIKI-005)

- **Given** the skill is installed and seeds are committed
- **When** I run `time cat homelab-playbook/wiki/architecture/network-tailscale-policy.md > /dev/null` and `time cat homelab-playbook/wiki/index.md > /dev/null` in 20 paired iterations (warm cache)
- **Then** every iteration's `real` time is ≤ 200 ms; p95 ≤ 100 ms (this measures the file-read; the skill's wall-clock includes the model's own latency, which is out-of-scope per FR-WIKI-005 wording: retrieval = file-read only)

### AC8: Skill consumes zero retrieval tokens (FR-WIKI-005)

- **Given** the skill is installed
- **When** I run a Claude Code session with one of the AC6 prompts and inspect the transcript
- **Then** no embedding API call is made; no MCP tool call is made (other than the model's own `Read` tool); no `WebFetch` is made; the only tokens spent are (a) the input prompt, (b) the model reading `index.md` + 1-3 wiki pages, (c) the synthesized response — these are LLM-completion tokens, NOT retrieval tokens. The retrieval surface itself costs zero embedding/search tokens

### AC9: Skill does not double-load on session start

- **Given** the skill is installed
- **When** I open a Claude Code session WITHOUT a triggering prompt (e.g., simple "ls" question)
- **Then** the skill does NOT auto-load `index.md` or any wiki page — it remains dormant until a triggering phrase fires (this distinguishes it from a SessionStart hook; ADR-009 §Mechanics is explicit)

### AC10: Skill survives wiki tree relocation gracefully

- **Given** the skill is installed
- **When** I temporarily rename `homelab-playbook/wiki/` to `wiki-temp-rename/` and run a triggering prompt
- **Then** the skill reports "wiki not initialised" per AC4 — does NOT crash, does NOT try filesystem search, does NOT try MCP fallback. (Restore the rename after the test.)

## Implementation Notes

### File: `~/.claude/skills/wiki-query/SKILL.md`

```yaml
---
name: wiki-query
description: |
  Use this skill to answer questions about the homelab's curated knowledge base
  ("the wiki"). The wiki holds architecture decisions, runbooks, decision archives,
  and a glossary at homelab-playbook/wiki/. Trigger phrases include: "the wiki",
  "wiki page on X", "tailscale policy", "pve cluster", "runbook for X", "what's
  our convention for X", "what did we decide about X" (when X is not
  session-specific — for session-specific decisions, prefer Graphiti's
  search_facts).
allowed-tools: Read
---
```

Body (verbatim from ADR-009 §Skill file structure, polished for production):

```markdown
# wiki-query

When invoked:

1. Read `homelab-playbook/wiki/index.md` first. It is a small markdown file
   (≤ 5 KB) listing every wiki page by category with a one-line summary and a
   slug.
2. From the user's question, identify 1-3 most-relevant slugs.
3. Read those pages directly via the `Read` tool. Slugs map to filenames in the
   wiki tree:
   - `pve-cluster-topology` → `homelab-playbook/wiki/architecture/pve-cluster-topology.md`
   - `decommission-context-stack-phase-1` → `homelab-playbook/wiki/runbooks/decommission-context-stack-phase-1.md`
   - etc. (the `category` frontmatter on each page maps to the directory)
4. Cite each consulted page by slug in your response so the user can navigate
   further. Use the form: "From the wiki: [page title](slug)."

Do not invoke any LLM, embedding, or external service. This is a plain
file-read skill. If `homelab-playbook/wiki/index.md` does not exist, tell the
user the wiki has not been initialised and recommend reviewing the Phase 3
wiki-init story (E4-S01 + E4-S02). Do not attempt to fall back to filesystem
search or any MCP tool.
```

### Optional `README.md` (operator-facing only)

```markdown
# wiki-query (operator notes)

This skill replaces the deleted `knowledge-query` orchestrator (FR-DEC-006).
Per ADR-009, retrieval is read-on-demand: `index.md` first, then 1-3 pages.

To extend coverage, add new pages under `homelab-playbook/wiki/` per the ADR-006
schema and re-run `scripts/wiki-lint.sh --regen` to rebuild `index.md`.

The skill auto-discovers new pages — no skill-edit needed when content grows.
```

### Trigger-phrase calibration (ADR-009 alignment)

The frontmatter `description` is what Claude Code uses to decide whether to invoke the skill. Trigger phrases must be specific enough to avoid stealing prompts from other tools (Graphiti's `search_facts` for dated decisions, GitNexus for code structure) but broad enough that natural homelab questions hit. The default list per ADR-009 is the starting point; if AC6 reveals false negatives, the operator iterates the description in a follow-up commit.

### Path safety (per architecture §5.3)

Slugs map to filenames inside `homelab-playbook/wiki/` only. The skill body does NOT permit user-controlled path traversal (no slug like `../../etc/passwd`). The constraint is enforced by-construction: the model resolves slug → category → filename via `index.md` lookup, and `Read` is bounded by Claude Code's tool surface to project files. If a malicious slug appears in `index.md` itself, that's a wiki-content problem caught by `wiki-lint.sh` (ADR-006 enforces unique well-formed slugs).

### NOT in scope for this story

- No embedding generation (FR-WIKI-009).
- No MCP server creation (ADR-005 — wiki-query is the only intentional skill).
- No "build a JSON index" preload optimization (ADR-009 §Alternatives — read-on-demand is decided).
- No CLAUDE.md auto-load of wiki content (ADR-009 §Alternatives explicitly rejects this).

## Test Plan

**Pre-flight:**
```bash
ls ~/.claude/skills/   # confirm skill not yet installed
ls homelab-playbook/wiki/index.md homelab-playbook/wiki/architecture/network-tailscale-policy.md   # E4-S01 + E4-S02 deliverables
```

**Install (Edit/Write):**
```bash
mkdir -p ~/.claude/skills/wiki-query
# Write SKILL.md per Implementation Notes
# Optionally write README.md
```

**AC verification:**
```bash
# AC1
ls ~/.claude/skills/wiki-query/
# AC2 (frontmatter inspection)
yq '.name, .description, ."allowed-tools"' ~/.claude/skills/wiki-query/SKILL.md
# Expect: name=wiki-query; description multi-line; allowed-tools=[Read]
# AC3 + AC4 (body inspection)
sed -n '/^---$/,/^---$/!p' ~/.claude/skills/wiki-query/SKILL.md | grep -E 'index.md|slug|Cite|not initialised'
# AC5 + AC6 (5 prompts; record transcripts)
for q in \
  "what's our tailscale policy for phone-facing services?" \
  "describe the PVE cluster topology" \
  "how did we decommission MemPalace and OMEGA?" \
  "what's the hybrid-gemma-serving plan?" \
  "what is the context-stack project?"; do
  echo "=== $q ===" >> /tmp/e4-s03-skill-smoke.log
  # Run as a non-interactive Claude Code invocation (or interactive; record terminal)
  script -q -c "claude -p '$q'" /tmp/e4-s03-skill-smoke-$(date +%s).log
done
# Inspect each transcript: confirm wiki-query triggered, index.md read, seed read, slug cited.
# AC7 (file-read latency)
for i in $(seq 1 20); do
  /usr/bin/time -f "%e" cat homelab-playbook/wiki/index.md > /dev/null 2>>/tmp/e4-s03-latency.log
  /usr/bin/time -f "%e" cat homelab-playbook/wiki/architecture/network-tailscale-policy.md > /dev/null 2>>/tmp/e4-s03-latency.log
done
awk 'NF{s+=$1; n++} END{print "avg:", s/n, "max:", m}' /tmp/e4-s03-latency.log   # all rows ≤ 0.200
# AC8 (manual transcript inspection: zero embedding calls, zero MCP calls)
grep -iE 'embedding|mcp|graphiti|gitnexus|webfetch' /tmp/e4-s03-skill-smoke-*.log
# Expect: zero matches in retrieval-call context (matches in cited content are OK)
# AC9 (no auto-load)
script -q -c "claude -p 'just say hello'" /tmp/e4-s03-no-trigger.log
grep -c 'wiki-query' /tmp/e4-s03-no-trigger.log   # expect 0 (skill should NOT have fired)
# AC10 (relocation drill)
mv homelab-playbook/wiki homelab-playbook/wiki-temp-rename
script -q -c "claude -p 'show me the tailscale policy from the wiki'" /tmp/e4-s03-norename.log
grep -i 'not initialised' /tmp/e4-s03-norename.log   # expect match
mv homelab-playbook/wiki-temp-rename homelab-playbook/wiki
```

**Rollback:**
```bash
rm -rf ~/.claude/skills/wiki-query/
# Skill is workstation-installed; no repo state to revert (the skill source SHOULD also be tracked under
# homelab-playbook/skills/wiki-query/ as a backup copy — see DoD).
```

## Dependencies

- **Blocks:** E4-S07 (Ansible role installs the skill on `ct-dev-homelab`); E4-S11 (FR-WIKI-005 latency check)
- **Blocked by:** E4-S01 (need index.md to read), E4-S02 (need at least one seed for AC5/AC6)

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Trigger phrases too narrow → skill misses obvious prompts | AC6 covers 5 representative prompts; if any miss, iterate `description` in follow-up commit (single-file edit, not a full story re-do) |
| Trigger phrases too broad → skill steals prompts that belong to Graphiti `search_facts` | ADR-013 tier-of-truth division is in `_schema.md` and the seeds; if observed, narrow `description` to add "for non-session-specific X" qualifier (already in default list) |
| Workstation-only install means it doesn't auto-deploy to `ct-dev-homelab` | E4-S07 Ansible role copies `~/.claude/skills/wiki-query/` to the target via the role; this story commits a backup copy under `homelab-playbook/skills/wiki-query/` for the role to source |
| `Read` tool may not have access to `homelab-playbook/wiki/` if cwd isn't the repo root | The skill body uses absolute path `homelab-playbook/wiki/index.md` relative to the working tree; Claude Code's `Read` resolves it under cwd. Document the "open Claude Code at the repo root" expectation in `_session-log.md` |

## Definition of Done

- [ ] All ACs pass (AC1–AC10)
- [ ] `~/.claude/skills/wiki-query/SKILL.md` installed
- [ ] Backup copy committed at `homelab-playbook/skills/wiki-query/SKILL.md` (for E4-S07 Ansible role)
- [ ] Optional README.md committed alongside (operator-facing notes)
- [ ] AC6 transcripts saved at `/tmp/e4-s03-skill-smoke-*.log` and referenced in PR description
- [ ] AC7 latency log saved at `/tmp/e4-s03-latency.log`
- [ ] No regression in `MEMORY.md` auto-memory loading
- [ ] Cross-reference task added: `AT-FR-WIKI-001a`, `AT-FR-WIKI-005a`, `AT-FR-WIKI-009a` (Phase 5a will populate)
