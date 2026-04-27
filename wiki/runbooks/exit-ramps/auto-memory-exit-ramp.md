---
title: "Auto-memory tier — exit ramp"
slug: auto-memory-exit-ramp
category: runbooks
last_reviewed: 2026-04-27
owner: tomamourette
related_pages:
  - index
  - query-hierarchy
related_frs:
  - FR-MEM-003
  - NFR-PRIV-003
related_adrs:
  - ADR-013
status: stable
supersedes: []
superseded_by: null
---

# Auto-memory tier — exit ramp

## Summary

Auto-memory lives at
`~/.claude/projects/-home-developer-workspace-homelab/memory/` —
markdown files with frontmatter, indexed by `MEMORY.md`. The exit ramp
is `cp -a` of the directory; the only migration wrinkle is the
project-path encoding in the parent directory name (the
`-home-developer-workspace-homelab` segment encodes the project root
path) which must be updated when moving to a host with a different
filesystem layout.

## Context

Auto-memory is Tier 4 in the ADR-013 hierarchy: passive, session-bound
context loaded at session start. It holds **one-line stable facts /
preferences / pointers** that are too small to deserve a wiki page and
too durable to relegate to Graphiti episodes. Because it is loaded
passively (not queried-on-demand), keeping it small and grep-friendly
is the entire design discipline.

The directory is operator-private (per NFR-PRIV-003 — auto-memory never
syncs off the workstation without explicit operator action). It is *not*
checked into the repo; the exit ramp is therefore "copy the directory
out of `~/.claude/`", not "git clone".

## Procedure

### 1. Capture the data

```bash
SRC=~/.claude/projects/-home-developer-workspace-homelab/memory
DST=/path/to/destination/auto-memory-$(date +%Y-%m-%d)
cp -a "$SRC" "$DST"
ls "$DST"
# expect: MEMORY.md  feedback_*.md  project_*.md  user_*.md  reference_*.md
```

`cp -a` preserves timestamps, which matter for "last touched"
diagnostics; `cp -r` is acceptable but loses mtime fidelity.

### 2. Honour the file-naming convention

Per the prelude memory rules, each entry's filename encodes its kind:

| Prefix | Purpose | Example |
|---|---|---|
| `user_*.md` | Operator profile / identity | `user_profile.md` |
| `feedback_*.md` | Lesson learned, "use X next time" | `feedback_correct_fix.md` |
| `project_*.md` | Per-project pointers / state | `project_ct_media_pve3_migration.md` |
| `reference_*.md` | Look-up tables, conventions | (none currently) |

`MEMORY.md` is the index — one line per memory file with a hyperlink and
a one-sentence summary. The index is what Claude Code reads first; the
individual files are read on-demand when the index pointer is followed.

### 3. The project-path encoding (the only migration wrinkle)

The parent directory name encodes the project filesystem path:

```
~/.claude/projects/-home-developer-workspace-homelab/memory/
                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                   = `/home/developer/workspace/homelab/`
                   with `/` replaced by `-`
```

Claude Code resolves "which auto-memory belongs to this session" by
encoding the current project path the same way and looking up the
matching directory under `~/.claude/projects/`. Therefore:

- **Same operator, same path** (e.g. RDB-style host restore): copy the
  directory back; no rename needed.
- **Different host, same path** (e.g. workstation rebuild with the same
  `~/workspace/homelab/` layout): copy the directory; no rename needed.
- **Different host, different path** (e.g. moving from
  `/home/developer/workspace/homelab/` to `/srv/operator/homelab/`):
  copy and rename — the destination path encoding must match the new
  filesystem layout. Verify by running Claude Code and checking that
  the session prelude shows the expected `MEMORY.md` content.

### 4. When to migrate vs export

| Situation | Action |
|---|---|
| Workstation rebuild, same paths | Copy directory back into `~/.claude/projects/` |
| Move project root to new path | Copy + rename per §3 |
| Promote a memory to wiki (it grew sub-bullets) | Author the wiki page; replace the auto-memory file with a one-line pointer to the wiki slug |
| Memory now belongs in Graphiti (it's dated/conversational) | Write the Graphiti episode; delete the auto-memory file (don't double-write per ADR-013) |
| Operator wants a snapshot for off-workstation review | `cp -a` to a non-`~/.claude/` location — does not affect runtime |

The promotion path (auto-memory → wiki) is documented in ADR-013
§Bidirectional rule: "auto-memory entries that grow past one line
(start having sub-bullets, code snippets) are wiki candidates. Migrate
the entry, leave a one-line pointer in `MEMORY.md`."

### 5. Recovery from corruption / accidental delete

Auto-memory is operator-private and not under git. Recovery options:

1. **Workstation backup** — if the operator's home dir is in the
   workstation's existing backup pattern (zfs send / rsync), restore
   from there.
2. **OMEGA history** — if OMEGA was the prior memory tier (pre-Context-
   Stack), `omega_query()` may surface the same content as legacy
   episodes; re-author the auto-memory entries from those.
3. **From scratch** — auto-memory is the cheapest tier to rebuild;
   each entry is one line and the operator can re-author the dozen-or-
   so they actually use within an hour. Treat full loss as a
   tolerable, not-catastrophic event.

Catastrophic loss of auto-memory is recoverable from operator memory.
Catastrophic loss of the *wiki* requires git restore. This asymmetry
is intentional — auto-memory is a hot-cache, wiki is the durable store.

### 6. What goes here vs other tiers (decision card)

Per ADR-013, write to auto-memory when **all** of:

- The fact is one line.
- The fact is stable (not dated; not "last week's session").
- The fact is a pointer / preference / identity / convention shortcut.

Examples that belong:

- "ct-quant-trading is at 192.168.50.162"
- "Tom prefers TDD"
- "Use /skill-builder for new custom skills"

Examples that DON'T belong (route to wiki or Graphiti instead):

- "Tailscale-only access policy for phone-facing services" → wiki
  (synthesised, multi-paragraph rule).
- "On 2026-04-24, pve2 migrated LVM→ZFS" → Graphiti (dated).
- "Function `add_episode` lives at `mcp_server/src/...`" → GitNexus
  (structural, ephemeral against code changes).

## Cross-references

- [Query hierarchy](query-hierarchy) — when to consult Tier 4
  (auto-memory).
- ADR-013 — tier-of-truth division (write-side rules for auto-memory).
- `MEMORY.md` (in the auto-memory directory) — the live index.
