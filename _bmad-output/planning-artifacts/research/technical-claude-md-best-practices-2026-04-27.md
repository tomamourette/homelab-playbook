---
stepsCompleted: []
inputDocuments:
  - homelab-playbook/_bmad-output/planning-artifacts/research/technical-codebase-docs-system-research-2026-04-27.md
workflowType: 'research'
lastStep: 1
research_type: 'technical'
research_topic: 'CLAUDE.md / AGENTS.md / .claude/rules — best practices for agent-instruction files, with deep-dive on Karpathy-style skills (forrestchang/andrej-karpathy-skills) and alternatives'
research_goals: 'Inform a refactor of the homelab root CLAUDE.md (currently risking the 1,094-line claude-flow/ruflo anti-pattern) into a best-practice cross-tool schema. Output: structural patterns, content taxonomy, length/tone guidance, instruction-precedence rules, anti-patterns, and a recommended target shape that combines with the doc-system research to give a single integrated design for /home/developer/workspace/homelab/.'
user_name: 'tomamourette'
date: '2026-04-27'
web_research_enabled: true
source_verification: true
---

# Research Report: CLAUDE.md / AGENTS.md best practices + Karpathy skills

**Date:** 2026-04-27
**Author:** tomamourette
**Research Type:** technical
**Companion:** `technical-codebase-docs-system-research-2026-04-27.md` (will be combined in synthesis)

---

## Research Overview

The homelab's root `CLAUDE.md` is substantial and trending toward the 1,094-line `ruvnet/claude-flow` (rebranded ruflo) anti-pattern surfaced in the doc-system research §C.8. Before refactoring it, this research establishes:

1. **Karpathy-style skill packs** — what `forrestchang/andrej-karpathy-skills` and similar implementations actually look like, what they lift from Karpathy, and what's worth lifting into the homelab.
2. **CLAUDE.md / AGENTS.md content best practices** — what belongs in these files vs what should live elsewhere; optimal length, tone, structure; hierarchy; forbid-list vs how-to vs context-provider style; anti-patterns beyond what §C.8 already surfaced.
3. **Instruction precedence and the Skills / Rules / Slash-Commands / Memory mesh** — how Claude Code's `CLAUDE.md`, `AGENTS.md`, `.claude/rules/`, `settings.json`, `.claude/commands/`, `.claude/skills/`, and the memory system interact; when to use each; lazy-loading via `InstructionsLoaded`.

The output combines with the doc-system research (Architecture C with two-layer wiki) to produce a single integrated design for the homelab.

---

## 1. Karpathy-style skill packs — forrestchang deep-dive + alternatives

*Returned 2026-04-27 / 28. Star counts and last-push dates verified via `api.github.com`.*

### 1.1 `forrestchang/andrej-karpathy-skills` — full inventory

**Repo metadata:** 94,917 stars / 9,186 forks / last push 2026-04-20 / created 2026-01-27 / MIT [verified]. Active but low commit volume (last 5 commits = README/marketplace polish).

**Critical framing correction:** the repo's own description is *"A single CLAUDE.md file to improve Claude Code behavior, derived from Andrej Karpathy's observations on LLM coding pitfalls."* Despite the name **`andrej-karpathy-skills`**, this is **one rule file packaged as one skill**, not a Karpathy-style skill *pack*. The 94k stars overwhelmingly reflect the brand of the topic, not the depth of the artifact.

**Top-level structure** [verified]:

| Path | Type | Size | Purpose |
|---|---|---|---|
| `.claude-plugin/` | dir | — | Claude Code plugin manifests (`plugin.json`, `marketplace.json`) |
| `.cursor/` | dir | — | Cursor IDE rule mirror (`rules/karpathy-guidelines.mdc`) |
| `CLAUDE.md` | file | 2,357 B | Canonical 4-principle rules — the actual product |
| `CURSOR.md` | file | 1,955 B | Same content, Cursor-flavoured |
| `EXAMPLES.md` | file | 14,838 B | Long-form before/after code examples |
| `README.md` | file | 6,198 B | Marketing + install instructions |
| `skills/karpathy-guidelines/SKILL.md` | file | 2,518 B (67 lines) | The skill body — **95% byte-identical to root `CLAUDE.md`** |

**Source attribution:** the only Karpathy citation is `https://x.com/karpathy/status/2015883857489522876` — his **coding-pitfalls tweet thread**. **No reference to Karpathy's LLM-Wiki gist or `karpathy/autoresearch`.** This repo addresses Karpathy's *coding-pitfalls* observations, not his *skills* or *wiki* mechanisms.

**Distinctiveness:** adds optional `license:` frontmatter; does NOT use `references/`, `scripts/`, `assets/`, `workflow.md`, or `steps/`. **Essentially a CLAUDE.md masquerading as a skill** — duplicates the same content into root and `skills/karpathy-guidelines/` so it works in both project-CLAUDE.md mode and plugin-skill mode.

### 1.2 Direct alternatives — actually-implementing Karpathy patterns

| Repo | Stars | Last push | Karpathy idea | Schema |
|---|---|---|---|---|
| `uditgoenka/autoresearch` | **4,130** | 2026-04-15 | Autoresearch loop | Multi-platform tri-skill: `claude-plugin/`, `.opencode/`, `.agents/`. Slash commands `/autoresearch:plan|debug|fix|security|ship|...`. References + scripts. |
| `Astro-Han/karpathy-llm-wiki` | **644** | 2026-04-28 | LLM-Wiki gist | Single `SKILL.md` + `references/`. 187 lines. |
| `kfchou/wiki-skills` | ~100 | 2026-04-26 | LLM-Wiki gist | **True multi-skill pack: `wiki-init`, `wiki-ingest`, `wiki-query`, `wiki-lint`, `wiki-update`** — five separate skills, each <300 lines, sharing a `SCHEMA.md` for cross-skill state. |
| `harshilmathur/autodecision` | 71 | 2026-04-26 | Autoresearch + LLM-council for decisions | Slash-command + skill hybrid; cites Karpathy explicitly. |
| `toolboxmd/karpathy-wiki` | 69 | 2026-04-28 | LLM-Wiki gist | Single skill + `hooks/session-start` + `hooks/stop`; auto-capture via `.wiki-pending/`. |
| `VoidLight00/autoimprove-cc` | 63 | 2026-04-21 | Autoresearch on SKILL.md itself | Auto-improves any SKILL.md against `eval.json` binary assertions. |
| `NulightJens/ai-second-brain-skills` | 55 | 2026-04-26 | LLM-Wiki + autoresearch hybrid | Two-skill pack: `llm-wiki-setup` + `wiki-self-heal`. |
| `grandamenium/autoresearch-anything` | 18 | 2026-04-17 | Autoresearch generalised | Single skill pack. |

**Verification on prior-known repos:** `Pratiyush/llm-wiki` (180 stars) is **NOT a skill pack** — it's a Python application that ingests Claude Code session JSONL into a wiki. `MehmetGoekce/llm-wiki` and `lucasastorian/llmwiki` are similarly small Python apps, not skill packs. Treat as `[unverified for skill-pack status]` — do not lift skill patterns from them.

### 1.3 `anthropics/skills` — file-level deep dive

**Metadata:** 125,011 stars / 14,643 forks / last push 2026-04-23 / created 2025-09-22 [verified].

**Top-level:**

| Path | Notes |
|---|---|
| `.claude-plugin/` | Marketplace manifest |
| `README.md` | 5,460 B |
| `THIRD_PARTY_NOTICES.md` | 46,162 B (license attributions) |
| `skills/` | **17 example skills** (algorithmic-art, brand-guidelines, canvas-design, claude-api, doc-coauthoring, docx, frontend-design, internal-comms, mcp-builder, **pdf**, pptx, **skill-creator**, slack-gif-creator, theme-factory, web-artifacts-builder, webapp-testing, xlsx) |
| `spec/agent-skills-spec.md` | 87 B redirect to https://agentskills.io/specification |
| `template/` | Single 140 B `SKILL.md` template (frontmatter + `# Insert instructions below`) |

**Three skills inspected at file level:**

**(a) `pdf/`** — files: `LICENSE.txt`, `SKILL.md` (8,072 B), `forms.md` (11,854 B), `reference.md` (16,692 B), `scripts/`. SKILL.md opens with *"## Quick Start"* + code, then explicit progressive-disclosure pointers: *"For advanced features... see REFERENCE.md. If you need to fill out a PDF form, read FORMS.md."*

**(b) `docx/`** — `LICENSE.txt`, `SKILL.md` (20,084 B), `scripts/`. Frontmatter `description` is **376 words** of trigger phrases including *"Triggers include: any mention of 'Word doc', 'word document', '.docx'... **Do NOT use for** PDFs, spreadsheets, Google Docs, or general coding tasks unrelated to document generation."* — **heavy negative triggers**.

**(c) `skill-creator/`** — `LICENSE.txt`, `SKILL.md` (33,168 B), `agents/`, `assets/`, `eval-viewer/`, `references/`, `scripts/`. The largest skill in the repo. Body codifies the **canonical "anatomy"** verbatim:

```
skill-name/
├── SKILL.md (required)
│   ├── YAML frontmatter (name, description required)
│   └── Markdown instructions
└── Bundled Resources (optional)
    ├── scripts/    - Executable code for deterministic/repetitive tasks
    ├── references/ - Docs loaded into context as needed
    └── assets/     - Files used in output (templates, icons, fonts)
```

And the **three-level progressive disclosure**: (1) metadata always in context (~100 words), (2) SKILL.md body when triggered (<500 lines ideal), (3) bundled resources loaded on demand. Plus an explicit anti-undertriggering note: *"please make the skill descriptions a little bit 'pushy'... 'Make sure to use this skill whenever the user mentions dashboards... even if they don't explicitly ask for a "dashboard."'"*.

**Required vs optional frontmatter:** required = `name`, `description`. Optional = `license`, `compatibility`, per-skill custom keys.

**Folder convention is fixed:** `scripts/`, `references/`, `assets/`. **No canonical `workflow.md` or `steps/`** — those are BMAD/superpowers-style community extensions.

**Cross-skill calling:** Anthropic's skills do **not** declare explicit "depends on skill X" wiring. Skills point to each other in prose. `kfchou/wiki-skills` invents a shared `SCHEMA.md` informally.

### 1.4 Patterns worth lifting

1. **Trigger-phrase-first descriptions with negative triggers.** *"Triggers include: ... Do NOT use for: ..."*. Best demo: `anthropics/skills/skills/docx/SKILL.md`.
2. **Three-tier progressive disclosure** (metadata → SKILL.md body <500 lines → bundled `references/`+`scripts/`+`assets/`). Codified in `skill-creator/SKILL.md`.
3. **Multi-skill pack with shared `SCHEMA.md` for inter-skill state.** Best demo: `kfchou/wiki-skills` — 5 separate skills (`wiki-init`/`wiki-ingest`/`wiki-query`/`wiki-lint`/`wiki-update`) sharing schema.
4. **Imperative numbered-step bodies, not narrative.** *"### 1. Gather configuration … ### 2. Create directory structure"* — `kfchou/wiki-skills/wiki-init/SKILL.md`.
5. **Repo-level hooks paired with skill folder.** `toolboxmd/karpathy-wiki` ships `hooks/session-start` and `hooks/stop` alongside `skills/karpathy-wiki/SKILL.md` — clean way to make a skill ambient without polluting `settings.json`.
6. **Multi-platform skill mirroring** (Claude Code + Cursor + Codex/OpenCode). Both `uditgoenka/autoresearch` and `forrestchang/andrej-karpathy-skills` ship parallel trees from one canonical source.
7. **Negative-rationalisation guard in description.** *"Do NOT skip based on tone or shape — 'this looks like casual chat'... are forbidden rationalizations."* (`toolboxmd/karpathy-wiki`) — pre-empts skill-undertriggering failure mode.
8. **SKILL.md as autoresearch loop target.** `VoidLight00/autoimprove-cc` — meta-pattern: SKILL.md + `eval.json` binary assertions + autoresearch loop over the SKILL.md itself.

### 1.5 Anti-patterns observed

- **Skill description as marketing copy.** `forrestchang/andrej-karpathy-skills` (94k★ / 1 file / 67 lines) is the canonical case of brand amplification beyond content depth. Star-farmed but not abandoned.
- **"Skill" that's a CLAUDE.md rebadge.** Same repo: 95% byte-identical between root CLAUDE.md and `skills/karpathy-guidelines/SKILL.md`. Skill folder exists mostly to satisfy plugin packaging.
- **SKILL.md as README.** Smaller wiki repos (e.g., `Pratiyush/llm-wiki`) carry product-marketing copy and badges in the header.
- **Step files >200 lines and unsearchable.** Anthropic's own `skill-creator/SKILL.md` is 33 KB / ~700+ lines, exceeding its own "<500 lines ideal" rule. Treat the structure as canonical, the length as cautionary.
- **Hardcoded paths breaking portability.** `toolboxmd/karpathy-wiki` requires editing absolute paths in `settings.json` — bad pattern.
- **"Karpathy by name only."** `forrestchang` references the coding-pitfalls tweet but does not implement Karpathy's actual *autoresearch* or *LLM-Wiki* mechanisms.
- **Wiki repos that aren't skills.** `Pratiyush/llm-wiki` (180★) and `Lum1104/Understand-Anything` (9k★) appear in "karpathy claude" searches but are Python applications, not skill packs.

### 1.6 Sources (verified 2026-04-27/28)

- https://github.com/forrestchang/andrej-karpathy-skills · https://github.com/anthropics/skills · https://github.com/uditgoenka/autoresearch · https://github.com/Astro-Han/karpathy-llm-wiki · https://github.com/kfchou/wiki-skills · https://github.com/toolboxmd/karpathy-wiki · https://github.com/VoidLight00/autoimprove-cc · https://github.com/harshilmathur/autodecision · https://github.com/grandamenium/autoresearch-anything
- https://x.com/karpathy/status/2015883857489522876 (coding-pitfalls tweet)
- https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f (LLM-Wiki gist)
- https://github.com/karpathy/autoresearch
- https://agentskills.io/specification

---

## 2. CLAUDE.md / AGENTS.md content best practices

*Returned 2026-04-27. All URLs verified. Anthropic primary-source quotes are exact.*

### 2.1 Anthropic's official guidance — verbatim

**On purpose and mental model:**

> *"CLAUDE.md files are markdown files that give Claude persistent instructions for a project, your personal workflow, or your entire organization. You write these files in plain text; Claude reads them at the start of every session."* [verified — memory]

> *"CLAUDE.md content is delivered as a user message after the system prompt, not as part of the system prompt itself. Claude reads it and tries to follow it, but **there's no guarantee of strict compliance**, especially for vague or conflicting instructions."* [verified — memory]

This is the single most important fact: **CLAUDE.md is advisory context, not enforced configuration.** For enforcement: *"Settings rules are enforced by the client regardless of what Claude decides to do. CLAUDE.md instructions shape Claude's behavior but are not a hard enforcement layer."* [verified]

**On when to add to CLAUDE.md:**

> *"Treat CLAUDE.md as the place you write down what you'd otherwise re-explain. Add to it when:*
> *• Claude makes the same mistake a second time*
> *• A code review catches something Claude should have known about this codebase*
> *• You type the same correction or clarification into chat that you typed last session*
> *• A new teammate would need the same context to be productive*
> 
> *Keep it to facts Claude should hold in every session: build commands, conventions, project layout, 'always do X' rules. **If an entry is a multi-step procedure or only matters for one part of the codebase, move it to a skill or a path-scoped rule instead.**"* [verified — memory]

**On size:**

> *"**Size**: target under 200 lines per CLAUDE.md file. Longer files consume more context and reduce adherence."* [verified — memory]

> *"Keep it concise. For each line, ask: 'Would removing this cause Claude to make mistakes?' If not, cut it. **Bloated CLAUDE.md files cause Claude to ignore your actual instructions!**"* [verified — best-practices]

**On specificity:**

> *"**Specificity**: write instructions that are concrete enough to verify. For example:*
> *• 'Use 2-space indentation' instead of 'Format code properly'*
> *• 'Run `npm test` before committing' instead of 'Test your changes'*
> *• 'API handlers live in `src/api/handlers/`' instead of 'Keep files organized'"* [verified]

**On emphasis:**

> *"You can tune instructions by adding emphasis (e.g., 'IMPORTANT' or 'YOU MUST') to improve adherence."* [verified — best-practices]

Surrounding paragraph: *"If Claude keeps doing something you don't want despite having a rule against it, the file is probably too long and the rule is getting lost."* [verified]

**Anthropic's published include/exclude table:** [verified — best-practices]

| ✅ Include | ❌ Exclude |
|---|---|
| Bash commands Claude can't guess | Anything Claude can figure out by reading code |
| Code style rules that differ from defaults | Standard language conventions Claude already knows |
| Testing instructions and preferred test runners | Detailed API documentation (link to docs instead) |
| Repository etiquette (branch naming, PR conventions) | Information that changes frequently |
| Architectural decisions specific to your project | Long explanations or tutorials |
| Developer environment quirks (required env vars) | File-by-file descriptions of the codebase |
| Common gotchas or non-obvious behaviors | Self-evident practices like "write clean code" |

**For Skills:** *"Create a skill when you keep pasting the same playbook, checklist, or multi-step procedure into chat, or when a section of CLAUDE.md has grown into a procedure rather than a fact."* [verified — skills]

**For hooks:** *"Use hooks for actions that must happen every time with zero exceptions. ... Unlike CLAUDE.md instructions which are advisory, hooks are deterministic and guarantee the action happens."* [verified — best-practices]

**On AGENTS.md (the Astral pattern, officially endorsed):**

> *"Claude Code reads `CLAUDE.md`, not `AGENTS.md`. **If your repository already uses `AGENTS.md` for other coding agents, create a `CLAUDE.md` that imports it so both tools read the same instructions without duplicating them.** You can also add Claude-specific instructions below the import."* [verified — memory]

### 2.2 Content taxonomy — what belongs

| Category | Phrasing | Length budget | Exemplar |
|---|---|---|---|
| **Behavioral invariants** | Imperative ("ALWAYS X", "NEVER Y"); reserve emphasis for 2–3 rules | 5–15 lines | Temporal's `time.Sleep` ban |
| **Project shape / file map** | Declarative ("Source in `/src`, tests in `/tests`") | 5–10 lines | Dagger's directory pointer |
| **Build/test/lint commands** | Imperative + literal command (`` `npm test` ``) | 5–10 lines | Anthropic's `/init` output |
| **Coding conventions** | Concrete + counter-example ("ES modules, not CommonJS") | 5–15 lines | Anthropic best-practices |
| **Domain forbidden patterns** | Imperative + literal pattern + lint-gate ref | 5–20 lines | Temporal's forbid-list |
| **Security boundaries** | Imperative + concrete artifact ("never commit `.env`") | 3–10 lines | Most production CLAUDE.md |
| **Pointers** | `@path` import or `see X.md for Y` | 1 line each | Anthropic's `@AGENTS.md` |
| **Project context** | Declarative one-liner ("This is a Rust CLI for Python packaging") | 1–3 lines | Astral's `uv` |

### 2.3 What does NOT belong

| Anti-content | Where it actually belongs |
|---|---|
| Marketing copy / project intro narrative | `README.md` for humans |
| Full CLI reference | Tool's `--help`, or skills |
| Long descriptive prose Claude can derive from code | Nowhere — delete |
| Architecture diagrams | `docs/architecture/` |
| Onboarding tutorials | `docs/tutorials/` |
| Multi-step procedures (deploy, release) | `.claude/skills/<name>/SKILL.md` |
| Path-specific rules (e.g., "in `src/api/` always X") | `.claude/rules/<topic>.md` with `paths:` frontmatter |
| Per-developer preferences | `CLAUDE.local.md` (gitignored) |
| Dynamic state (current sprint, todo) | Auto-memory `MEMORY.md` |
| Code-style enforcement | Linter + pre-commit hook |
| Hard-enforced bans (no `.env` writes) | `permissions.deny` in `settings.json` |

### 2.4 Length and density

| Source | Target | Type |
|---|---|---|
| Anthropic memory doc | **"under 200 lines"** | [verified] |
| Anthropic skills doc | **"Keep `SKILL.md` under 500 lines"** | [verified] |
| HumanLayer (engineering org) | **"less than 300 lines"**; their root file is **"less than sixty lines"** | [anecdotal] |
| Community measurement | 300–600 tokens typical; >2,000 tokens = wrong content; >5,000 tokens = compounding tax across compaction | [anecdotal] |

**Real measurements:**
- `ruvnet/claude-flow` (1,094 lines) = canonical worst-in-class.
- Anthropic's own `claude-code` repo ships **zero CLAUDE.md** — for shipped product code where the product *is* the agent, the file is unnecessary.
- Astral's `uv`: stub-redirect.
- Temporal/Dagger: 38–104 lines, tied to lint gates.
- **Pattern is bimodal:** minimal (<100 lines, tied to enforcement) or absent. Files between 200 and 1,000 lines = universally reported failure zone.

### 2.5 Tone and voice

No published Anthropic A/B data. What's verified:
- Imperative emphasis explicitly endorsed: *"add emphasis (e.g., 'IMPORTANT' or 'YOU MUST') to improve adherence."* [verified]
- Specificity examples uniformly imperative: "Use 2-space indentation", "Run `npm test`". [verified]
- Vague descriptive content rejected: "Self-evident practices like 'write clean code'." [verified]

**Community consensus** [anecdotal]:
- Imperative + concrete > descriptive + abstract.
- **Reserve `IMPORTANT` / `YOU MUST` for 2–3 truly load-bearing rules.** Universal usage destroys the signal: *"If every rule is marked important, the emphasis becomes invisible."*
- Pair imperatives with rationale only when reason is non-obvious.
- Avoid "should" / "prefer" / "consider" — Claude treats as suggestions.

**Nuance:** file structure and project shape are better stated *declaratively*. "API handlers live in `src/api/handlers/`" reads as fact, not order. Mixing is fine: declarative for shape, imperative for behavior.

### 2.6 Hierarchy and structure patterns

Anthropic's only published structure guidance:

> *"**Structure**: use markdown headers and bullets to group related instructions. Claude scans structure the same way readers do: organized sections are easier to follow than dense paragraphs."* [verified]

**Common section order** (synthesis from Astral/Temporal/Dagger and Anthropic's `/init` output):

1. **One-line project context** ("This is a Rust CLI for Python packaging.")
2. **Build/test/lint commands** — highest-ROI section
3. **Project shape** (one-line directory pointers, NOT ASCII trees)
4. **Behavioral invariants** (5–15 imperative rules)
5. **Forbidden patterns / security** (often tied to lint gates)
6. **Pointers** (`@AGENTS.md`, `@docs/...`, `.claude/rules/`)

**Markdown features Anthropic supports:**
- `@path/to/file` imports, max 5 hops, relative-path-aware. **Imported files load at launch, not on demand** — they consume context the same as inline content. Confirms §3.1 finding.
- HTML block comments (`<!-- ... -->`) **stripped before injection** — leave human-only notes without paying tokens. Comments in code blocks preserved.
- Standard markdown headers, lists, tables, code blocks. No special extensions.
- **No YAML frontmatter on CLAUDE.md itself** — reserved for `.claude/rules/<topic>.md` and `SKILL.md`.

**`@file` imports vs single-file**: imports help organization but **do not save context**. To actually slim context: path-scoped rules (load only on file match) or skills (load only on invocation).

### 2.7 Memory hierarchy — full precedence map

| Layer | Path | Loaded | Best at |
|---|---|---|---|
| **Managed policy CLAUDE.md** | `/etc/claude-code/CLAUDE.md` (Linux), `/Library/Application Support/ClaudeCode/CLAUDE.md` (mac) | Every session, unconditionally; cannot be excluded by users | Org-wide compliance, security, brand voice |
| **Project `./CLAUDE.md`** | Repo root | Every session, full file | Team-shared conventions, build commands |
| **`./CLAUDE.local.md`** | Repo root, gitignored | Every session; appended after CLAUDE.md → wins on conflict at same level | Sandbox URLs, personal test data |
| **User `~/.claude/CLAUDE.md`** | Home | Every session | Personal preferences across all projects |
| **`.claude/rules/<topic>.md`** | Project | At launch if no `paths:`; on-demand when matching files read | Topic-split rules |
| **`.claude/commands/<name>.md`** | Project or user | Lazy — only when invoked as `/<name>` | Reusable prompts (legacy; merging into skills) |
| **`.claude/skills/<name>/SKILL.md`** | Project, user, plugin, managed | Description always in context (≤1,536 chars); body only when invoked | Procedures, playbooks, on-demand reference |
| **`.claude/agents/<name>.md`** | Project or user | Only when delegated | Specialised side-tasks with independent context |
| **`settings.json`** (managed/project/user/local) | Various | Always in effect; lower scopes can't override managed; deny beats allow | Permissions, hooks, env, sandbox |
| **Auto-memory `MEMORY.md`** | Per-repo, machine-local | First 200 lines or 25KB at session start | Things Claude learns from corrections |

**Settings vs CLAUDE.md** — most commonly missed distinction. Anthropic's clean decision table [verified — memory]:

| Concern | Configure in |
|---|---|
| Block specific tools, commands, file paths | Managed settings: `permissions.deny` |
| Enforce sandbox isolation | Managed settings: `sandbox.enabled` |
| Environment variables, API routing | Managed settings: `env` |
| Code style and quality guidelines | CLAUDE.md |
| Behavioral instructions | CLAUDE.md |

**The trap:** writing "NEVER commit secrets" in CLAUDE.md is **advisory**. Adding `"deny": ["Read(./.env)", "Read(./.env.*)"]` to `settings.json` is **enforced**. Use both.

### 2.8 Cross-tool portability

**Anthropic's officially endorsed dual-write strategy** [verified]:

```markdown
# CLAUDE.md
@AGENTS.md

## Claude Code

Use plan mode for changes under `src/billing/`.
```

This is **exactly the Astral pattern**. AGENTS.md = cross-tool source of truth; CLAUDE.md imports + appends Claude-specific tail.

**Reality check April 2026** [anecdotal community]:
- AGENTS.md natively read by: Codex CLI, Copilot, Cursor (partial), Windsurf, Amp, Devin.
- **Claude Code does NOT natively read AGENTS.md as of April 2026** — open issue #6235 with thousands of upvotes; the `@AGENTS.md` import in a thin CLAUDE.md is the recommended path.
- Symlink approach (`ln -s AGENTS.md CLAUDE.md`) works but loses the Claude-specific tail.

### 2.9 Anti-patterns beyond §C.8

1. **Stale rules drift.** Rules referencing renamed files or deprecated commands. *"Review your CLAUDE.md files periodically to remove outdated or conflicting instructions."* [verified]
2. **Cross-file contradiction.** `CLAUDE.md` says "use pnpm" while `.cursorrules` says "use npm". *"If two rules contradict each other, Claude may pick one arbitrarily."* [verified]
3. **Over-prescription.** "Always use TypeScript strict mode" is fine; "Always wrap every function in try/catch" is wrong. Test: would a senior engineer push back?
4. **Under-specification.** "Be careful with the database layer" without defining careful = worse than no rule.
5. **Per-developer preferences leaking into committed CLAUDE.md.** Sandbox URLs, "I prefer pytest verbose mode" — belong in `CLAUDE.local.md`.
6. **Storing dynamic state.** Sprint status, todo lists — belongs in auto-memory or issue tracker.
7. **Auto-generated CLAUDE.md from `/init` left untouched.** Aggressive pruning is the difference between a 60-line working file and a 400-line ignored one.
8. **Treating CLAUDE.md as enforcement.** "NEVER write to /etc" is advice. If it matters, encode in `permissions.deny` or `PreToolUse` hook.
9. **Mistaking emphasis density for adherence.** Files with `IMPORTANT:` on every line consistently produce *worse* compliance.
10. **Inflated CLAUDE.md as documentation substitute.** README is for humans; CLAUDE.md is for Claude.

### 2.10 Sources (verified 2026-04-27)

**Anthropic primary [verified]:**
- https://code.claude.com/docs/en/memory · https://code.claude.com/docs/en/best-practices · https://code.claude.com/docs/en/skills · https://code.claude.com/docs/en/sub-agents · https://code.claude.com/docs/en/settings

**Cross-tool standard [verified]:** https://agents.md

**Community evidence [anecdotal]:** humanlayer.dev/blog/writing-a-good-claude-md · buildtolaunch.substack.com (token-tax estimates) · datacamp/claudelog/builder.io (emphasis-sparingly principle) · hivetrail.com/blog/agents-md-vs-claude-md-cross-tool-standard (AGENTS.md adoption status April 2026)

---

## 3. Instruction-Precedence and Lazy-Loading Mesh

*Returned 2026-04-27. All URLs verified that day. Claims tagged `[verified]` (Anthropic docs), `[doc-implied]` (inferred from doc wording), `[anecdotal]` (community-derived, no Anthropic source).*

### 3.1 Load order at session start — what's eager vs lazy

| Source | When loaded | Mechanism | Token cost at start |
|---|---|---|---|
| `~/.claude/CLAUDE.md` (user-global) | **Eager** every session | Concatenated under "User memory" section | Full file |
| `<project>/CLAUDE.md` | **Eager** every session in cwd | Concatenated under "Project memory" | Full file |
| `<project>/CLAUDE.local.md` | **Eager** if present | Same channel, marked "local"; gitignored by convention | Full file |
| `<project>/AGENTS.md` | **Not auto-loaded by Claude Code** in 2026 | Loaded only via `@AGENTS.md` import inside CLAUDE.md | Full file *if* imported |
| `.claude/rules/<topic>.md` | **Eager IF `@`-imported in CLAUDE.md; otherwise NOT LOADED** | Standard import resolver | Full file if imported |
| `.claude/commands/<name>.md` | Discovery only — names + frontmatter scanned | Body loaded only when slash-command invoked | Names only (~tens of tokens each) |
| `.claude/skills/<name>/SKILL.md` | **Frontmatter only** scanned at start | Body + sibling files loaded when model routes to skill | ~100–300 tokens per skill (frontmatter) |
| `~/.claude/projects/<project>/memory/MEMORY.md` | Eager when memory enabled | Per-fact files via `@` follow standard import semantics | MEMORY.md full + transitive imports |
| `~/.claude/hooks/*` + `settings.json:hooks` | **Never in context** | Subprocess execution on event match | 0 |
| `settings.json` (non-hooks) | Config only — model, permissions, env | Not exposed as instructions | 0 |

**Critical correction to companion doc-system research**: §3.5 of `technical-codebase-docs-system-research-2026-04-27.md` claimed `.claude/rules/<topic>.md` lazy-loads via `InstructionsLoaded`. **This is wrong.** `@`-imports resolve eagerly at session start (Anthropic memory doc, max 5 levels of recursion). A Cline-style split into `.claude/rules/general.md`, `security.md`, `testing.md`, etc. **does NOT save session-start tokens** — it only reorganizes them on disk. To get true lazy load, use Skills, Slash commands, or `UserPromptSubmit` hooks that conditionally inject context.

### 3.2 Precedence rules — what wins when sources conflict

Anthropic's memory doc states: *"If memory files conflict, more specific or recent instructions generally take precedence, but Claude uses judgment"* `[verified, but soft]`.

Practical precedence, most-specific to most-general:

1. **Active user prompt** — always trumps any persisted rule.
2. **Slash-command body** when invoked — overrides ambient guidance for the turn.
3. **Skill body** when invoked — overrides general rules within scope.
4. **`CLAUDE.local.md`** — local overrides committed `[doc-implied]`.
5. **Project `CLAUDE.md`** — overrides user-global for project-specific concerns `[verified]`.
6. **User `~/.claude/CLAUDE.md`** — baseline.
7. **Imported files** (`@.claude/rules/x.md`) — inherit precedence of importer.
8. **Auto-memory `MEMORY.md`** — facts not rules; conflicts resolve toward CLAUDE.md `[anecdotal]`.

**Honest verdict:** Claude Code's instruction surface is layered but **not strictly ordered**. Anthropic publishes load-timing guarantees and rough precedence but stops short of a deterministic resolver. Design for *non-conflict by construction* — keep CLAUDE.md terse and authoritative; push topical depth into Skills (genuinely lazy) and rules files (eager but organized); reserve slash commands for user-typed shortcuts; treat auto-memory as model-curated notes that periodically promote into CLAUDE.md after review.

Sub-cases worth knowing:
- **CLAUDE.md vs AGENTS.md when both present**: AGENTS.md only loaded if CLAUDE.md imports it; later content in the assembled prompt overrides earlier.
- **Multiple `.claude/rules/*.md` contradicting**: no documented arbitration; resolve by deliberate ordering or topic-naming convention so only one matches a task.
- **Skill description vs CLAUDE.md**: description is for *routing* (does this skill apply?), not behavior. Once routed, skill body has scoped precedence.

### 3.3 Decision tree — Skill vs Rule vs Slash Command vs CLAUDE.md content

**Decision rule: frequency × specificity × user-intent-trigger.**

- *Always-applies, project-wide, terse* → **CLAUDE.md**
- *Always-applies but bulky/topical* → **`.claude/rules/<topic>.md` imported from CLAUDE.md** (organizes; doesn't lazy-load)
- *Multi-step procedure invoked by description-match* → **Skill** (genuinely lazy)
- *User-typed shortcut for a recurring action* → **Slash command** (lazy on invoke)
- *Per-machine or per-developer secret/preference* → **CLAUDE.local.md**
- *Persistent fact accumulating over time* → **Auto-memory**

| Content | Best home | Reasoning |
|---|---|---|
| "Always use POSIX disk_io for libtorrent" | `.claude/rules/qbittorrent.md` imported | Topical, narrow scope, bulky enough for own file |
| "Run tests with `npm test`" | Project `CLAUDE.md` (Build & Test) | Universal, tiny, eager-load worth it |
| "When user says 'create story', do X" | **Skill** with description "Create a BMAD story spec" | Description-routed by user intent |
| "Workflow for upgrading PVE: detach → migrate → upgrade → reattach" | **Skill** (multi-step procedure) | Procedural, ordered, benefits from progressive disclosure |
| "Project uses 3-repo split: infra/apps/playbook" | Project `CLAUDE.md` (Architecture) | Foundational context every agent needs |
| "Forbidden: `time.Sleep` in tests" | `.claude/rules/testing.md` or CLAUDE.md if short | Tipping point: one ban → CLAUDE.md inline; twelve → rules file |
| "User prefers concise responses, no closing summaries" | User-global `~/.claude/CLAUDE.md` | Cross-project, persona-level |
| "Database schema lives at `db/schema.sql`" | Project `CLAUDE.md` (one-liner) | Pointer fact, eager-load cheap |
| "Run `/loop` to start a recurring task" | **Slash command** `.claude/commands/loop.md` | User-typed shortcut |

### 3.4 Lazy-loading paths that actually work

Since `@`-imports are eager, real lazy-load requires:

1. **Skills** — frontmatter scanned at start, body loaded on routing match. Best for procedural content.
2. **Slash commands** — body loaded on `/name` invocation. Best for user-typed shortcuts.
3. **Hook-injected context** — a `UserPromptSubmit` hook can read a topic file conditional on prompt content, then emit it as additional context. **This is the closest analog to Cline's per-topic load** `[doc-implied via hook event semantics]`.
4. **Tool-driven Read** — the model invokes `Read` on a rules file when it decides relevance.

Implication for the homelab refactor: the Cline-style split (ADR-003 in the doc-system research) is still useful for *organization and review-ability*, but should not be sold as a token-savings mechanism. The genuine token savings come from moving procedural content into **Skills** and rule-conditional content into **`UserPromptSubmit` hooks**.

### 3.5 Skills system — discovery and routing in practice

From https://docs.claude.com/en/docs/claude-code/skills and `anthropics/skills`:

- **Discovery**: at session start, Claude Code walks `.claude/skills/*/SKILL.md` and `~/.claude/skills/*/SKILL.md`, parses YAML frontmatter (`name`, `description`, optional `allowed-tools`), and registers each as a candidate. Body is **not** read.
- **Routing**: the model uses the `description` field "to determine when this skill applies to the user's request." Phrased as **semantic match by the model itself**, not deterministic keyword index. No documented embedding-similarity layer.
- **Folder structure**: SKILL.md alone, or SKILL.md + workflow.md + steps/`*.md`. Body Reads sibling files progressively as needed.
- **Cost at scale**: 100-skill install = ~100 frontmatter blobs at start. At ~50 tokens each = ~5000 tokens — non-trivial but bounded. Anthropic schema caps `description` at 1024 chars.

**Pulling in other context**: skill body can Read sibling files, invoke MCP tools, reference rules files. Skills do **not** automatically inherit `.claude/rules/*` — they must Read explicitly.

### 3.6 Memory hierarchy — auto-memory vs CLAUDE.md

- Auto-memory at `~/.claude/projects/<project>/memory/MEMORY.md` is a **distinct feature** from CLAUDE.md (Anthropic memory doc).
- **Loaded eagerly** when memory feature is on; per-fact `@`-imports follow standard semantics.
- **200-line truncation**: not in Anthropic's public docs as of 2026-04-27. Treat as folklore until verified `[anecdotal]`.
- **`/memory` command**: edits MEMORY.md interactively. Use for transient/accumulating facts.
- **`omega_*` commands**: not Anthropic-native. User-installed MCP tool family, project-specific to this homelab — note for context but not a portable pattern.

**Rule of thumb:** CLAUDE.md = *committed, reviewable* contract. MEMORY.md = *accumulating, model-curated* notes. When they disagree, CLAUDE.md is the source of truth; treat memory drift as a signal to refactor CLAUDE.md.

### 3.7 Cross-tool implications — AGENTS.md reach in 2026

For the Astral `CLAUDE.md = @AGENTS.md` pattern to deliver value, peer tools must read AGENTS.md. Reality:

| Tool | AGENTS.md support | Notes |
|---|---|---|
| **Claude Code** | Via `@AGENTS.md` import in CLAUDE.md | Indirection, not native parsing |
| **OpenAI Codex CLI** | **Native primary** | Anchor of the convention |
| **Cursor** | **No native support**; reads `.cursor/rules/*.mdc` first, `.cursorrules` legacy fallback | Manual symlink/import needed |
| **Continue.dev** | **Opt-in via config** — list AGENTS.md in `rules` config | Not automatic |
| **Aider** | **Manual inclusion** via `--read AGENTS.md` or `.aider.conf.yml` | Repo-map + git history is its primary |

**Net:** AGENTS.md is a *convention with partial uptake*. Cross-tool reach in 2026-04-27 = Codex (native), Claude Code (via import), Continue (via config), Cursor + Aider (manual). The Astral pattern is sound but requires per-tool verification — for the homelab where Claude Code is primary, the indirection works; if the operator adds Cursor, manual symlinks needed.

### 3.8 Failure modes specific to instruction precedence

| Symptom | Cause | Detection | Recovery |
|---|---|---|---|
| Two committers add conflicting CLAUDE.md rules | Last-write-wins in git | PR review; agent behavior diverges | Refactor into single section with explicit precedence wording |
| `.local` rule contradicts committed | `.local` silently wins, invisible | Behavior diverges per machine | Move to committed CLAUDE.md or document local override |
| Skill description matches unintended prompt | `description` too generic | Skill activates on wrong inputs | Tighten description to specific intents and example phrases |
| Hook fails silently | Returns non-zero or times out | Stale/missing context; agent ignores rules | Tail hook logs (Claude Code emits hook stderr); add `set -e`; verify matchers |
| Memory and CLAUDE.md disagree | Auto-memory captured stale fact | Agent quotes obsolete info | `/memory` to edit; promote durable facts to CLAUDE.md, prune memory |
| `@`-import path broken after refactor | Imports relative to importer | Silent — content absent; agent under-informed | CI lint walking imports, fail on missing files |
| Skill folder loads body twice | Two SKILL.md with same `name` | Confused routing | Skill names must be globally unique; namespace with project prefix |

**Detection rule:** when an agent "forgets" something written down, the first check is *which file did you write it in, and is that file actually in the load path for this session*.

### 3.9 Sources (verified 2026-04-27)

- https://docs.claude.com/en/docs/claude-code/memory — load order, `@`-imports, 5-level recursion, `.local` deprecation, project>user precedence.
- https://docs.claude.com/en/docs/claude-code/skills — frontmatter-only startup scan, body lazy-load, description-based routing.
- https://github.com/anthropics/skills — SKILL.md folder layouts and progressive-disclosure examples.
- https://code.claude.com/docs/en/hooks — 13 hook events, subprocess model, hooks-not-in-context.
- https://docs.claude.com/en/docs/claude-code/slash-commands — discovery and on-invoke body load.
- https://docs.claude.com/en/docs/claude-code/settings — `settings.json` schema and hook matchers.
- https://github.com/openai/codex — AGENTS.md primacy.
- https://docs.cursor.com/context/rules — `.cursor/rules/*.mdc` precedence.
- https://docs.continue.dev — `.continue/rules` and AGENTS.md opt-in.
- https://aider.chat/docs — repo-map model and manual AGENTS.md inclusion.

---

## 4. Synthesis — recommended homelab CLAUDE.md / AGENTS.md / Skills design

### 4.1 Headline conclusions

1. **Anthropic explicitly endorses the Astral `@AGENTS.md` pattern** [verbatim, §2.1]. ADR-003 in the doc-system research is correct on the choice; the migration path can cite Anthropic's own doc as authority.
2. **CLAUDE.md is advisory, not enforced** — for hard fences (`.env` writes, destructive commands), use `permissions.deny` in `settings.json` or `PreToolUse` hooks. Companion research §3 already wires hooks; this clarifies the *enforcement boundary*.
3. **Anthropic published target: under 200 lines per CLAUDE.md.** Verbatim. The homelab's current root CLAUDE.md exceeds this and should be cut, not just split.
4. **Cline-style topic split organizes content but does NOT lazy-load** — `@`-imports are eager. To genuinely save tokens, move procedural content into **Skills** (lazy by design), user-typed shortcuts into **Slash commands**, and prompt-conditional rules into **`UserPromptSubmit` hooks**. *(Corrects §3.5 / §4.4 / ADR-003 of the doc-system research.)*
5. **The `forrestchang/andrej-karpathy-skills` repo is a brand-amplified single-rule-file**, NOT a Karpathy *skill pack*. The 94k stars are misleading. **Do not lift its structure.** It addresses Karpathy's coding-pitfalls tweet, not his LLM-Wiki gist.
6. **Real Anthropic skill folder convention** is `SKILL.md + scripts/ + references/ + assets/` — NOT `workflow.md + steps/`. The latter are BMAD/superpowers community extensions; both are valid but distinct.
7. **`kfchou/wiki-skills`** is the cleanest multi-skill pack pattern in the wild (5 skills sharing a `SCHEMA.md`). **This is the model the homelab's `wiki-publish-audience` skill should emulate** — break it into multiple cooperating skills if it grows beyond a single SKILL.md.

### 4.2 Recommended target shape for the homelab

Combining all findings and the doc-system research's ADR-003 / ADR-004:

```
/home/developer/workspace/homelab/
├── CLAUDE.md                     # Astral stub (Anthropic-endorsed)
│                                 #   Line 1: @AGENTS.md
│                                 #   Lines 2-N: Claude-specific tail (optional, <30 lines)
│
├── AGENTS.md                     # CANONICAL schema, cross-tool
│                                 # Target: ≤200 lines (Anthropic verbatim)
│                                 # Current: ~250+ lines → must be cut
│                                 # Sections in order:
│                                 #   1. Project context (1-line)
│                                 #   2. Build/test/lint commands
│                                 #   3. Project shape (one-line dir pointers)
│                                 #   4. Behavioral invariants (5-15 imperative rules)
│                                 #   5. Forbidden patterns / security
│                                 #   6. Pointers (@.claude/rules/<topic>.md)
│
├── CLAUDE.local.md               # gitignored — operator-only preferences
│                                 # (sandbox URLs, "verbose pytest", etc.)
│
├── .claude/
│   ├── rules/                    # Topic-split rules — eager-loaded if @-imported
│   │   ├── docs.md               # wiki schema, frontmatter, ingest/query/lint
│   │   ├── security.md           # OWASP, secrets, validation
│   │   ├── testing.md            # TDD, mocks vs integration
│   │   ├── concurrency.md        # batching, parallelism
│   │   └── path-scoped/          # path-scoped rules (load-on-file-match)
│   │       ├── homelab-infra-terraform.md   # paths: ['homelab-infra/**']
│   │       └── homelab-apps-docker.md
│   │
│   ├── commands/                 # Slash commands — lazy-loaded on /name
│   │   └── (existing slash commands)
│   │
│   └── skills/                   # Skills — frontmatter scanned, body lazy
│       └── wiki-publish-audience/  # NEW (per Architecture C, D4)
│           ├── SKILL.md          # ≤500 lines (Anthropic target)
│           ├── references/       # audience-tone guidance, redaction rules
│           │   ├── customer-tone.md
│           │   ├── pm-tone.md
│           │   └── public-tone.md
│           ├── scripts/          # deterministic transforms
│           │   ├── filter-by-audience.py
│           │   └── push-to-azdo.sh
│           └── assets/           # templates (intro pages, TOCs)
│
└── settings.json                 # ENFORCED rules (hooks, permissions)
                                  # NOT advisory like CLAUDE.md
```

### 4.3 What changes vs prior research

The doc-system research (§4.4 ADR-003) called for a Cline-style split into `.claude/rules/<topic>.md`. **That stays**, but with three corrections:

| Correction | Why |
|---|---|
| Don't sell the split as a token-savings mechanism. It organizes for review-ability and PR diffs. Token savings come from **moving procedural content into Skills** (genuinely lazy). | §3.4 finding — `@`-imports are eager. |
| Use `paths:` frontmatter on rules files where applicable — they then load only when matching files are touched. | Anthropic-supported, genuine lazy-load for path-scoped rules. |
| **Use `permissions.deny` in `settings.json` for any rule that's actually load-bearing for safety** (e.g., "never read `.env`"). | CLAUDE.md is advisory; settings is enforced. Anthropic explicit. |

### 4.4 The audit / refactor plan for the existing root `CLAUDE.md`

The current homelab root `CLAUDE.md` is ~250+ lines. Concrete cuts following Anthropic's exclude list:

| Section | Action | Why |
|---|---|---|
| Project intro narrative | **CUT** — move to `README.md` if needed | "Marketing copy / project intro narrative" anti-pattern |
| Build & Test commands | **KEEP** — top of AGENTS.md, ~10 lines | Anthropic include-list highest-ROI section |
| File Organization | **KEEP** but compress to 5–8 one-line pointers | "ASCII trees → one-line pointers" pattern |
| Concurrency / batching rules | **MOVE** to `.claude/rules/concurrency.md` if >15 lines, otherwise keep in AGENTS.md | If standalone bulky topic |
| Swarm Orchestration / V3 CLI / 60+ agent types / Memory commands ref | **CUT entirely from AGENTS.md** — these are tool-specific to ruflo, not project-wide invariants | "Detailed API documentation (link to docs instead)" |
| Security Rules | **SPLIT** — invariants stay in AGENTS.md (3–5 lines); enforcement moves to `settings.json:permissions.deny` | Advisory vs enforced distinction |
| Behavioral Rules (top of file) | **KEEP** — these are the load-bearing imperatives; trim to 8–12 with selective `IMPORTANT` emphasis | Anthropic specifically endorses imperative + emphasis (sparingly) |
| Available Agents (60+ list), 3-Tier Model Routing, Quick Setup, Support | **CUT** — these are ruflo product reference, not project rules | Anti-pattern: "Tool-specific reference belongs in tool's own docs" |

**Expected result:** 250+ → ~80–120 lines AGENTS.md + ~3 line CLAUDE.md stub + 4–6 topic files in `.claude/rules/` (each <100 lines). Total context cost at session start ≈ 60–70% of current.

### 4.5 The `wiki-publish-audience` skill — refined design (post-Karpathy research)

Per §1.4 patterns lifted, the new skill should:

- Use **trigger-phrase-first description with negative triggers** — *"Use when user says 'publish customer wiki', 'sync customer wiki', 'update customer-facing docs'. Triggers include: requests to mirror playbook content to AzDO Wiki or workspace /wiki/. **Do NOT use for** editing the operator wiki directly, or for /docs/ per-repo pages — those are not the customer surface."*
- Use **three-tier progressive disclosure** — SKILL.md keeps orchestration ≤500 lines; per-audience tone guidance lives in `references/customer-tone.md`, `pm-tone.md`, `public-tone.md`; transforms in `scripts/filter-by-audience.py`; templates in `assets/`.
- **Imperative numbered-step body**, not narrative. Pattern from `kfchou/wiki-skills`.
- Consider splitting into **multi-skill pack** if the skill grows past 500 lines:
  - `wiki-publish-audience` — orchestrator
  - `wiki-filter-audience` — applies frontmatter-based filtering
  - `wiki-tone-rewrite` — per-audience LLM transforms
  - `wiki-mirror-azdo` — pushes to AzDO Wiki
  - `wiki-mirror-workspace` — writes to workspace `/wiki/`
  - Shared `SCHEMA.md` for inter-skill state — Karpathy LLM-Wiki primitive.

### 4.6 What to NOT lift

Explicit anti-recommendations:
- **Do NOT structure the homelab CLAUDE.md after `forrestchang/andrej-karpathy-skills`.** It's a single-rule-file with brand inflation; not a model.
- **Do NOT use BMAD's `workflow.md + steps/` as the canonical skill structure.** It's a community extension, not Anthropic-canonical. Reserve it for skills genuinely needing multi-step workflows; default to flat `SKILL.md` + `references/` + `scripts/` per Anthropic.
- **Do NOT load `.claude/rules/*.md` eagerly via `@`-imports for every rule** — that defeats the token-saving purpose. Use `paths:` frontmatter for path-scoped lazy-load, or move the content into a Skill.
- **Do NOT mark every rule `IMPORTANT` / `YOU MUST`.** Reserve emphasis for 2–3 truly load-bearing rules per file.

### 4.7 Combined synthesis with doc-system research

The two research projects produce a **single integrated design** for the homelab:

| Layer | Source-of-truth | Consumed by | Driven by |
|---|---|---|---|
| **Schema** (agent rules) | `AGENTS.md` (≤200 lines) + `.claude/rules/<topic>.md` + `settings.json` (for enforced rules) | Claude Code, Cursor (manual), Codex (native), Continue (config) | This research §4.4 audit + ADR-003 |
| **Operator wiki SoT** | `homelab-playbook/wiki/` (Diátaxis-aligned) | Operator (Obsidian via `obsidian-git`); Claude Code via filesystem | Doc-system research §4 + Architecture C |
| **Repo-local /docs/** | Per-repo `/docs/` (Diátaxis-aligned) | Same | Doc-system research §4.3.1 |
| **Reference layer** | `gitnexus wiki` → `docs/reference/generated/` | Auto-generated, regen on PR/merge + weekly + on-demand | Doc-system research ADR-006 + D5 cadence |
| **Customer wiki** | Synthesized via `wiki-publish-audience` skill | AzDO Wiki (AzDO projects) or workspace `/wiki/` (homelab) | Doc-system research D4 + this research §4.5 |
| **Skills** | `.claude/skills/<name>/` with Anthropic canonical schema | Claude Code (frontmatter routing) | This research §1.3 + §4.5 |
| **Hooks** | `~/.claude/hooks/` + `settings.json:hooks` | Event-driven, never in context | Doc-system research §3.5 + this research §3.4 |
| **Memory** | Auto-memory `MEMORY.md` + `/memory` slash command | Eager at session start | This research §3.6 |

The two research files together give:
1. **Doc-system research** — what gets documented, where it lives, how it stays current.
2. **CLAUDE.md research** — how the agent that maintains all this gets instructed, in a way that scales.

Implementation order is unchanged from doc-system §5.9 with one insertion: **Pass 1 of the schema split** (CLAUDE.md → AGENTS.md stub) should happen Week 1 alongside the audit cuts identified in §4.4 above. **Pass 2** (split into `.claude/rules/<topic>.md`) becomes Week 2.

### 4.8 Verifiable success metrics for the schema refactor

Beyond the doc-system research's NFRs:

- **Final AGENTS.md length: ≤120 lines** (Anthropic target = 200; aim lower for headroom).
- **Total `.claude/rules/<topic>.md` content: ≤500 lines combined**, with `paths:` frontmatter where applicable.
- **`@`-import count from AGENTS.md: ≤4 topic files** (avoid spider-web import graphs).
- **Session-start token cost from agent-instruction files: <5,000 tokens** (measurable via Claude Code's `/cost` or similar).
- **Settings.json: encode every safety-critical rule via `permissions.deny`**, not just CLAUDE.md.
- **Compliance verification:** check Cursor session reads AGENTS.md correctly (manual test post-migration).

### 4.9 Sources

This research synthesizes:
- §1: Karpathy + forrestchang deep-dive (researcher subagent return 2026-04-27)
- §2: CLAUDE.md content best practices (researcher subagent return 2026-04-27)
- §3: Instruction-precedence and lazy-loading mesh (researcher subagent return 2026-04-27)

Plus Anthropic's primary docs (https://code.claude.com/docs/en/{memory,best-practices,skills,sub-agents,settings,hooks,slash-commands}), the cross-tool spec (https://agents.md), and the companion doc-system research (`technical-codebase-docs-system-research-2026-04-27.md`).
