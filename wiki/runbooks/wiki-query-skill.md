---
title: "wiki-query skill: design, install, and test"
slug: wiki-query-skill
category: runbooks
last_reviewed: 2026-04-27
owner: tomamourette
related_pages:
  - _schema
  - index
related_frs:
  - FR-WIKI-001
  - FR-WIKI-003
  - FR-WIKI-005
  - FR-WIKI-009
related_adrs:
  - ADR-005
  - ADR-006
  - ADR-009
  - ADR-013
status: stable
supersedes: []
superseded_by: null
---

# wiki-query skill

## Summary

`wiki-query` is the read-on-demand Claude Code skill that answers homelab
questions from this wiki. It lives on the operator's workstation at
`~/.claude/skills/wiki-query/SKILL.md` (NOT in the repo), but the canonical
SKILL.md source-of-truth IS version-controlled at
`homelab-playbook/skills/wiki-query/SKILL.md`. This page captures the design
rationale, install procedure, and test recipe so the skill is reproducible
from the repo even though its runtime location is in `$HOME`.

## Context

Per ADR-009, the wiki tier serves Claude Code via a **read-on-demand** skill
rather than a pre-built JSON index, MCP server, or embedding store. ADR-005
explicitly carves out `wiki-query` as the single intentional skill bet in
the Context Stack — every other tier is MCP-native. The skill replaces the
deleted `knowledge-query` orchestrator removed in E1-S05 (FR-DEC-006).

The skill is workstation-installed because Claude Code resolves
`~/.claude/skills/<name>/SKILL.md` from the user's home directory regardless
of which repo the session is opened in. Committing it to a repo would not
make Claude Code pick it up automatically. The version-controlled
`homelab-playbook/skills/wiki-query/SKILL.md` is the **source of truth** —
the workstation copy is a deployment of it. The E4-S07 Ansible role
(`ai-dev-context-stack`) will use the repo copy as the source for any
container-side deploy (e.g., `ct-dev-homelab`).

## Procedure / Decision / Definition

### What the skill does

When triggered, the skill instructs Claude Code to:

1. Read `~/workspace/homelab/homelab-playbook/wiki/index.md` first.
2. Pick 1-3 slugs from the index that match the user's question.
3. Read those pages directly via the `Read` tool — no LLM / embedding / MCP.
4. Cite each consulted page by slug in the response.

If `index.md` is absent the skill reports "wiki not initialised" and stops —
no filesystem fallback, no MCP fallback, no LLM-only synthesis. See
[Wiki page schema](_schema) for the page format the skill consumes.

### Where it lives on the workstation

```
~/.claude/skills/
└── wiki-query/
    └── SKILL.md      # frontmatter + body; the only file Claude Code reads
```

The repo backup copy lives at:

```
homelab-playbook/skills/wiki-query/SKILL.md
```

The two files MUST stay byte-identical — bring them into sync via the
install procedure below whenever the repo copy changes.

### Install procedure (workstation)

```bash
# 1. From the homelab-playbook repo root:
mkdir -p ~/.claude/skills/wiki-query
cp skills/wiki-query/SKILL.md ~/.claude/skills/wiki-query/SKILL.md

# 2. Verify the install:
ls -la ~/.claude/skills/wiki-query/
head -1 ~/.claude/skills/wiki-query/SKILL.md   # expect: ---

# 3. Restart any open Claude Code session for it to pick up the new skill.
```

If `~/.claude/skills/wiki-query/SKILL.md` already exists, `cp` overwrites
it with the latest repo version — that is the intended sync pattern.

### Test procedure

Smoke (workstation, after install):

```bash
ls ~/.claude/skills/wiki-query/                                   # SKILL.md present
head -10 ~/.claude/skills/wiki-query/SKILL.md                     # frontmatter valid
diff -u skills/wiki-query/SKILL.md ~/.claude/skills/wiki-query/SKILL.md   # byte-identical
```

Functional (per E4-S03 ACs, requires E4-S02 seeds to fully test):

1. Open a Claude Code session at the homelab repo root.
2. Ask a triggering prompt, e.g. *"what's our tailscale policy for
   phone-facing services?"*.
3. Expect transcript to show: `wiki-query` invoked → `index.md` read →
   matched seed read → response cites the slug.

The detailed five-prompt smoke matrix is captured in the E4-S03 story
spec under AC6 (`/tmp/e4-s03-skill-smoke-{a..e}.log`). Run it once seeds
land in E4-S02.

### Trigger phrases (calibrated in ADR-009)

The skill's frontmatter `description:` is what Claude Code uses to decide
whether to invoke it. The current phrases:

- "the wiki" / "wiki page on X"
- "tailscale policy"
- "pve cluster"
- "runbook for X"
- "what's our convention for X"
- "what did we decide about X" (when X is **not** session-specific)

If after E4-S02 seeds land the skill is observed missing obvious prompts,
iterate the `description:` in a follow-up commit on
`homelab-playbook/skills/wiki-query/SKILL.md` and re-sync the workstation
copy via the install procedure. Single-file edits, no story re-do per the
E4-S03 risk register.

### What the skill does NOT do (per ADR-009)

- No embedding generation (FR-WIKI-009).
- No MCP server, no daemon (ADR-005 — wiki-query is the only intentional
  skill).
- No precomputed JSON index (`wiki/_index.json` was rejected in ADR-009
  alternatives). Reversal trigger: wiki > 100 entries AND `index.md` > 20
  KB AND missed-page rate observable.
- No `CLAUDE.md` auto-load of wiki content (rejected in ADR-009
  alternatives). The skill is dormant unless triggered.

## Cross-references

- [Wiki page schema](_schema) — page format the skill consumes.
- ADR-005 — skill-tier exception for wiki-query.
- ADR-006 — wiki-as-file-tree decision and schema.
- ADR-009 — wiki-query skill design (read-on-demand vs preload-index).
- ADR-013 — tier-of-truth division (when to use wiki vs Graphiti vs
  auto-memory vs GitNexus).
- E4-S01 story spec — schema + bootstrap (ACs 5/6/9 closed in commit
  `73ccabb`).
- E4-S03 story spec — this skill's authoring story.
- E4-S07 — Ansible role that will deploy the skill onto `ct-dev-homelab`
  by sourcing `homelab-playbook/skills/wiki-query/SKILL.md`.
