# Story 0.2: Install Autoresearch Skill

Status: done

## Story

As a developer,
I want the autoresearch skill installed in my Claude Code environment,
so that I can run `/autoresearch:fix` after code review to automatically iterate on findings until eval assertions pass.

## Acceptance Criteria

1. **Given** the Claude Code environment with BMAD installed
   **When** the autoresearch skill is installed
   **Then** `/autoresearch:fix` is invocable and responds (AT-6.7)

2. **Given** the installed autoresearch skill
   **When** I check the skill directory
   **Then** it lives in its own directory (`.claude/skills/autoresearch/` or equivalent), separate from `bmad-*/` skills

3. **Given** the BMAD installation at `.claude/skills/bmad-*/`
   **When** the autoresearch skill is installed
   **Then** zero files in `.claude/skills/bmad-*/` are modified (NFR-INT-5, AT-6.8)

4. **Given** the autoresearch skill is installed
   **When** I list available commands
   **Then** `/autoresearch:fix`, `/autoresearch:plan`, and `/autoresearch:learn` are available

## Eval Assertions

<!-- Binary test assertions derived from acceptance criteria. Used by /autoresearch:fix for post-code-review iteration loops. -->

| # | Assertion | Command/Check | Pass Criteria |
|---|-----------|---------------|---------------|
| AC-1 | autoresearch:fix invocable | Run `/autoresearch:fix --help` or invoke skill | Skill responds without error |
| AC-2 | Separate from BMAD | `test -d .claude/skills/autoresearch/ && ! echo .claude/skills/bmad-autoresearch/` | Exists in own directory, not bmad-* |
| AC-3 | No BMAD files modified | `git diff .claude/skills/bmad-*/` | Empty output (no changes) |
| AC-4 | Key commands available | Check skill list for autoresearch:fix, autoresearch:plan, autoresearch:learn | All three appear in skill list |

## Tasks / Subtasks

- [x] Task 1: Install the autoresearch skill (AC: #1, #2)
  - [x] Option A (preferred): Used manual installation — cloned repo, copied skill files to `.claude/skills/autoresearch/`
  - [x] Also copied commands to `.claude/commands/autoresearch/` and `.claude/commands/autoresearch.md`
  - [x] Verified skill directory exists at `.claude/skills/autoresearch/`
  - [x] Session restart NOT needed — skill appeared immediately in skill list

- [x] Task 2: Verify autoresearch commands are available (AC: #1, #4)
  - [x] `/autoresearch:fix` listed in available skills
  - [x] `/autoresearch:plan` listed
  - [x] `/autoresearch:learn` listed
  - [x] All 10 commands visible: autoresearch, fix, plan, learn, debug, security, ship, predict, scenario, reason

- [x] Task 3: Verify BMAD update-safety (AC: #3)
  - [x] `git diff .claude/skills/bmad-*/` returns zero changes
  - [x] autoresearch is in `.claude/skills/autoresearch/`, separate from `bmad-*/`

## Dev Notes

### Installation Procedure

The uditgoenka/autoresearch skill has two installation methods:

**Manual Installation (preferred for control):**
```bash
git clone https://github.com/uditgoenka/autoresearch.git /tmp/autoresearch
cp -r /tmp/autoresearch/claude-plugin/skills/autoresearch ~/.claude/skills/autoresearch
cp -r /tmp/autoresearch/claude-plugin/commands/autoresearch ~/.claude/commands/autoresearch
cp /tmp/autoresearch/claude-plugin/commands/autoresearch.md ~/.claude/commands/autoresearch.md
rm -rf /tmp/autoresearch
```

**Plugin Marketplace:**
```
/plugin marketplace add uditgoenka/autoresearch
/plugin install autoresearch@autoresearch
```

**Important:** Start a new Claude Code session after installing. Reference files aren't resolvable in the same session where installation happened.

### What Autoresearch Provides

10 commands total:
- `/autoresearch` — Main unbounded improvement loop
- `/autoresearch:fix` — **Primary use case**: Iterative error crushing until tests pass
- `/autoresearch:plan` — Interactive wizard: Goal → Scope → Metric → Verify
- `/autoresearch:learn` — Documentation engine (init/update/check modes)
- `/autoresearch:ship` — 8-phase shipping workflow
- `/autoresearch:debug` — Scientific bug-hunting
- `/autoresearch:security` — Read-only STRIDE + OWASP audit
- `/autoresearch:scenario` — Edge-case explorer
- `/autoresearch:predict` — Multi-persona analysis
- `/autoresearch:reason` — Adversarial refinement

### How It Integrates with Our Workflow

```
/create-story-with-evals   ← Creates story + eval assertions
    ↓
/dev-story                 ← Uses eval assertions as TDD targets
    ↓
/code-review               ← Reviews code
    ↓
/autoresearch:fix          ← IF review found issues, iterate:
                              modify → run eval assertions → keep/revert → repeat
```

### Previous Story Learnings (Story 0.1)

- Wrapper skill pattern works: `.claude/skills/create-story-with-evals/` is standalone and visible immediately
- BMAD update-safety verified: `git diff .claude/skills/bmad-*/` shows zero changes
- Claude Code auto-detects new skills when files are placed in `.claude/skills/`

### Project Structure Notes

- Install target: `.claude/skills/autoresearch/` (skill files) + `.claude/commands/autoresearch/` (command registrations)
- No existing files modified
- No BMAD skill files touched

### References

- [Source: architecture.md — BMAD Workflow Enhancement Decisions / Autoresearch Skill Installation]
- [Source: prd.md — FR52, NFR-INT-5]
- [Source: research/technical-incremental-docs-autoresearch-2026-04-03.md — Enhancement Wrapper Pattern & Autoresearch Cadence]
- [Source: GitHub - uditgoenka/autoresearch](https://github.com/uditgoenka/autoresearch)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

None — clean installation.

### Completion Notes List

- Installed uditgoenka/autoresearch via manual git clone + file copy
- All 10 commands available immediately (no session restart needed)
- Skill at `.claude/skills/autoresearch/`, commands at `.claude/commands/autoresearch/`
- Zero BMAD files modified
- Cleaned up cloned repo from /tmp

### File List

- `.claude/skills/autoresearch/SKILL.md` (new — 35KB, comprehensive skill definition)
- `.claude/skills/autoresearch/references/` (new — 12 workflow reference files)
- `.claude/commands/autoresearch.md` (new — main command registration)
- `.claude/commands/autoresearch/` (new — 9 subcommand registrations)
