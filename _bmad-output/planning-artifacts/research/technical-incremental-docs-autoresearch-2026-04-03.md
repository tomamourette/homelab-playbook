---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments: []
workflowType: 'research'
lastStep: 6
status: 'complete'
completedAt: '2026-04-03'
research_type: 'technical'
research_topic: 'Incremental Project Documentation & Autoresearch for BMAD Skills'
research_goals: 'Design a targeted BMAD skill for incremental docs/ folder updates after each epic, explore Karpathy autoresearch for skill improvement, and research best practices for AI-assisted documentation maintenance.'
user_name: 'tomamourette'
date: '2026-04-03'
web_research_enabled: true
source_verification: true
---

# Technical Research Report: Incremental Project Documentation & Autoresearch for BMAD Skills

**Date:** 2026-04-03
**Author:** tomamourette
**Research Type:** Technical

---

## Technical Research Scope Confirmation

**Research Topic:** Incremental Project Documentation & Autoresearch for BMAD Skills
**Research Goals:** Design a targeted BMAD skill for incremental docs/ folder updates after each epic, explore Karpathy autoresearch for skill improvement, and research best practices for AI-assisted documentation maintenance.

**Technical Research Scope:**

- Architecture Analysis — bmad-document-project internals, autoresearch pipeline, incremental update patterns
- Implementation Approaches — diff-based vs full regen, git-aware change detection, section-level updates
- Technology Stack — Karpathy's autoresearch, AI documentation tools, BMAD skill system
- Integration Patterns — autoresearch patterns for Claude skills, BMAD epic completion workflow hooks
- Performance Considerations — token efficiency, context window management for large docs

**Research Methodology:**

- Current web data with rigorous source verification
- Multi-source validation for critical technical claims
- Confidence level framework for uncertain information
- Comprehensive technical coverage with architecture-specific insights

**Scope Confirmed:** 2026-04-03

---

## Technology Stack Analysis

### Karpathy's Autoresearch — Core Architecture

Autoresearch (released March 2026, 21,000+ GitHub stars) is a framework for autonomous AI experimentation built on **deliberate minimalism** — three files, one editable, one metric, time-boxed cycles.

**Three-File Design:**
- `prepare.py` — Immutable. Data prep, tokenizer, evaluation metric. Never modified.
- `train.py` — The single editable file (~630 lines). Agent modifies this file only.
- `program.md` — Human-written Markdown instructions that define research objectives, constraints, and strategy. The "research org code."

**Core Primitives:**
1. **Editable asset** — Single file the agent can modify (keeps search space interpretable)
2. **Scalar metric** — Single number determining improvement (val_bpb — lower is better)
3. **Time-boxed cycle** — Fixed 5-minute experiments (~12/hour, ~100 overnight)

**The Loop:** Read instructions → Form hypothesis → Modify code → Run experiment → Measure → Keep if improved, discard if not → Repeat.

_Source: [GitHub - karpathy/autoresearch](https://github.com/karpathy/autoresearch), [DataCamp Guide](https://www.datacamp.com/tutorial/guide-to-autoresearch), [VentureBeat](https://venturebeat.com/technology/andrej-karpathys-new-open-source-autoresearch-lets-you-run-hundreds-of-ai)_

### Autoresearch Applied to Claude Code Skills

The autoresearch pattern has already been adapted for Claude Code skill optimization. Key implementations:

**uditgoenka/autoresearch (Claude Code Plugin):**
An 8-phase autonomous loop protocol:
1. Review current state + git history + results log
2. Pick next change (based on what worked/failed/untried)
3. Make ONE focused change
4. Git commit (before verification)
5. Run mechanical verification (tests, benchmarks, scores)
6. Keep if improved → revert if worse → fix or skip if crashed
7. Log result
8. Repeat forever (or N iterations)

**Key Commands:** `/autoresearch` (main loop), `/autoresearch:plan` (interactive wizard), `/autoresearch:learn` (documentation engine with init/update/check modes), `/autoresearch:scenario` (edge-case explorer), `/autoresearch:reason` (adversarial refinement via blind judge panel).

**Three Foundational Constraints:**
- One change per iteration (atomic, traceable)
- Mechanical verification only (no subjective "looks good")
- Automatic rollback on failure (git preserves history)

_Source: [GitHub - uditgoenka/autoresearch](https://github.com/uditgoenka/autoresearch), [MindStudio - AutoResearch Pattern for Claude Code Skills](https://www.mindstudio.ai/blog/karpathy-autoresearch-pattern-claude-code-skills)_

### Existing BMAD Document-Project Skill — Architecture

The installed `bmad-document-project` skill uses a **full-scan architecture** with these key characteristics:

**Workflow Modes:**
- `initial_scan` — First-time documentation generation
- `full_rescan` — Re-scan entire project, regenerate all docs
- `deep_dive` — Targeted documentation for a specific area

**Scan Levels:** Quick (pattern-based, 2-5 min), Deep (10-30 min), Exhaustive (30+ min)

**Project Type Detection:** Uses `documentation-requirements.csv` (12 project types, 24-column schema) to determine what to scan and document. Columns include key_file_patterns for detection and requirement flags (requires_api_scan, requires_data_models, etc.).

**Output Structure:**
- `docs/index.md` — Master index referencing all generated docs
- `docs/project-overview.md` — Executive summary, tech stack, roadmap
- `docs/architecture-{part}.md` — Per-repo architecture documentation
- `docs/source-tree-analysis.md` — Full annotated directory trees
- `docs/development-guide.md`, `deployment-guide.md`, `integration-architecture.md`

**State Tracking:** `project-scan-report.json` tracks progress, enables resume capability.

**Key Limitation:** No incremental mode. Only full_rescan or deep_dive. No awareness of what changed since last scan — it regenerates everything.

_Source: Local codebase analysis of `/.claude/skills/bmad-document-project/`_

### AI Documentation Tools — 2026 Landscape

**Mintlify Workflows (Git Diff-Aware):**
- Reads code diffs when PRs merge, drafts corresponding documentation updates
- Bi-directional Git sync — changes flow between repos and web editor
- AI coding agents (Claude Code, Cursor) can update docs via pull requests
- **Key insight:** Mintlify's approach validates that diff-aware incremental doc updates are a proven pattern

**Documentation.AI:**
- Supports MCP servers for agent-driven updates and automation
- Modular documentation with tagged snippets linked to code blocks

**Industry Best Practices for Incremental Docs:**
- Real-time synchronization via MCP connections between AI and source code
- Periodic sweeps comparing doc metadata against active code changes
- Modular documentation: reusable snippets tagged to code blocks, auto-reflected on change
- Incremental modernization 2.5x more likely to achieve objectives than "big bang" replacement

_Source: [Mintlify](https://www.mintlify.com/blog/auto-generate-docs-from-repos), [Document360 Trends](https://document360.com/blog/ai-documentation-trends/), [Docsie](https://www.docsie.io/blog/articles/automated-documentation-research-2026/)_

### Technology Adoption Trends

**The Autoresearch Pattern Beyond ML:**
- Already adapted for code quality, content, marketing, DevOps — "anything with a number you can measure"
- Multiple Claude Code skill implementations exist (uditgoenka/autoresearch, various Medium/Substack guides)
- The pattern has been called "the meta-skill that improves all other skills"

**Documentation-as-Code:**
- Trend toward treating docs like source code: versioned, tested, CI/CD integrated
- Git-aware documentation tools outperforming manual maintenance approaches
- AI agents as documentation contributors alongside human engineers

_Source: [MindStudio - Self-Improving Skills](https://www.mindstudio.ai/blog/claude-code-autoresearch-self-improving-skills), [AI Maker - Skill That Improves All Skills](https://aimaker.substack.com/p/how-i-built-skill-improves-all-skills-karpathy-autoresearch-loop)_

## Integration Patterns Analysis

### How the Autoresearch Pattern Maps to Incremental Documentation

The autoresearch `/autoresearch:learn` command already implements documentation modes that directly map to our use case:

| Autoresearch Mode | BMAD Doc Equivalent | Purpose |
|---|---|---|
| `init` | `initial_scan` (bmad-document-project) | Generate docs from scratch by scanning the codebase |
| `update` | **Missing — this is what we need** | Refresh existing docs based on what changed |
| `check` | No equivalent | Read-only health report — validate docs are current |
| `summarize` | No equivalent | Quick overview of documentation state |

**Key insight:** The `update` and `check` modes are exactly what the current `bmad-document-project` lacks. The autoresearch pattern provides the architectural blueprint for adding these modes.

_Source: [GitHub - uditgoenka/autoresearch](https://github.com/uditgoenka/autoresearch)_

### Git-Diff-Aware Change Detection Pattern

The incremental documentation skill needs to detect what changed since docs were last generated. The approach combines git primitives:

**Change Detection Pipeline:**
```
1. git log --since="<last_docs_date>" --name-only --pretty=format:""
   → Lists all files changed since docs were last generated

2. Classify changed files by impact:
   - Ansible roles (tasks/, templates/, defaults/) → Update architecture docs
   - Docker Compose (stacks/) → Update architecture-homelab-apps.md
   - Terraform (modules/) → Update architecture-homelab-infra.md
   - Scripts/tools → Update development-guide.md
   - New directories/services → Update source-tree-analysis.md + index.md

3. For each impacted doc section:
   - Read current doc section
   - Read changed source files
   - Generate updated section content
   - Replace only that section (preserve unchanged sections)
```

**Mintlify's Proven Pattern:** Mintlify Workflows reads code diffs when PRs merge and drafts corresponding doc updates. This validates that diff-aware incremental updates are production-ready — we're applying the same concept but at epic-completion granularity rather than per-PR.

_Source: [Mintlify](https://www.mintlify.com/blog/auto-generate-docs-from-repos), [Git documentation](https://git-scm.com/docs/git-diff)_

### BMAD Skill Integration Points

**Where the new skill fits in the BMAD workflow:**

```
Epic completion workflow:
  /create-story → /dev-story → /code-review → /qa-automate
                    ↓ (repeat for all stories in epic)
  /retrospective
                    ↓
  /update-project-docs    ← NEW SKILL (runs here)
                    ↓
  Next epic / sprint planning
```

**Claude Code Hooks Integration:**
The skill could also be triggered automatically via a Claude Code hook. Skills are invoked when the user calls them; hooks fire automatically at lifecycle events. Options:

| Trigger | Mechanism | When |
|---------|-----------|------|
| Manual invocation | `/update-project-docs` slash command | User runs after epic completion |
| Post-task hook | Claude Code `PostToolUse` hook | After specific git merge/PR operations |
| Scheduled | Hermes Agent cron job (Phase 2) | Weekly automated doc sync |

**Recommended for MVP:** Manual invocation after epic completion. Automated hooks add complexity and risk of unwanted doc changes.

_Source: [Claude Code Hooks Guide](https://code.claude.com/docs/en/hooks-guide), [Claude Code Skills](https://www.everettquebral.com/blog/artificial-intelligence/skills-hooks-and-plugins-in-claude-code)_

### Integration with Existing bmad-document-project

The new skill should **extend, not replace** the existing `bmad-document-project` skill. Integration strategy:

**Shared Resources:**
- Same `docs/` output folder (`{project_knowledge}`)
- Same document templates and naming conventions
- Same `project-scan-report.json` state file (extended with last-update timestamps per section)
- Same `documentation-requirements.csv` for project type detection

**Distinct Responsibilities:**
| Skill | When to Use | What It Does |
|-------|-------------|-------------|
| `bmad-document-project` | Initial setup, major restructures | Full codebase scan → generate all docs from scratch |
| `bmad-update-project-docs` (new) | After each epic completes | Git-diff detection → update only affected doc sections |

**State File Extension:**
The existing `project-scan-report.json` gains new fields:
```json
{
  "last_full_scan": "2026-04-02",
  "last_incremental_update": "2026-04-03",
  "section_timestamps": {
    "project-overview.md": "2026-04-02",
    "architecture-homelab-infra.md": "2026-04-03",
    "architecture-homelab-apps.md": "2026-04-02"
  },
  "git_ref_at_last_update": "abc123f"
}
```

### Autoresearch-Inspired Skill Improvement Loop

Beyond the documentation skill itself, the autoresearch pattern can improve the skill's quality over time:

**The Self-Improvement Pattern:**
```
1. Define metric: doc_coverage_score = (sections_current / total_sections) × 100
2. Define eval: After update, check that:
   - All changed files are reflected in docs
   - No doc sections reference deleted/renamed resources
   - Index.md links are all valid
   - Updated sections pass a coherence check
3. Run the loop:
   - Modify skill instructions (program.md equivalent)
   - Run update on a test repo
   - Measure doc_coverage_score
   - Keep if improved, revert if worse
4. Result: Skill prompts improve over time through measured iteration
```

**Practical application for BMAD:** The `bmad-update-project-docs` skill's workflow.md becomes the equivalent of autoresearch's `program.md` — the editable instruction file that gets refined through measured iteration. The `check` mode (doc health report) provides the scalar metric.

_Source: [MindStudio - AutoResearch Pattern](https://www.mindstudio.ai/blog/karpathy-autoresearch-pattern-claude-code-skills), [Medium - Self-Improving Skills](https://medium.com/@shubhjain191/how-to-make-your-claude-code-skills-self-improving-using-auto-research-803ff97d5483)_

### MCP-Based Doc Sync vs Git-Diff Approach

**What "MCP-based real-time sync" actually means in practice:**

Two distinct patterns exist under this umbrella:

1. **MCP as a query/read layer** — An MCP server exposes documentation for AI agent consumption. Google's Developer Knowledge API does this — AI tools query docs via MCP and get structured, version-aware responses. This makes docs *consumable* by AI, not *maintainable*.

2. **MCP as a write/sync layer** — Platforms like Docsie claim MCP enables AI to "automatically create, update, and manage guides in real time." In practice, this is event-triggered or on-demand (AI agents calling MCP tools to generate/update docs), not continuous background sync.

**Comparison for our use case:**

| Aspect | MCP-Based Sync | Git-Diff-Based Skill (our approach) |
|--------|---------------|--------------------------------------|
| Change detection | Compares live API/code state vs docs | `git log --since` detects file changes |
| Trigger | On-demand or scheduled MCP tool calls | Manual after epic completion |
| Scope | Per-endpoint or per-resource | Per-epic (batch of related changes) |
| Infrastructure | Requires running MCP server | Zero infrastructure — uses git + Claude Code |
| Best for | API docs, SaaS platforms with live endpoints | IaC/infra projects with git-tracked code |
| Complexity | High (server setup, connection management) | Low (git commands + BMAD skill) |

**Verdict: Git-diff is the right choice for this project.**

- The project is fully git-tracked — git diffs give perfect change detection for free
- No live APIs to compare against — this is infrastructure code, not a REST API
- Docs are local markdown files — Claude Code reads/edits them directly, no MCP intermediary needed
- MCP adds unnecessary infrastructure for syncing local docs with local code on the same container

**Future MCP opportunity (Phase 2+):** If OMEGA Memory stores documentation metadata, OMEGA's MCP server could expose doc freshness data to Hermes Director. The Director could then trigger doc updates as part of its autonomous workflow. But that's orchestration, not sync — and it uses MCP for *triggering*, not for the actual doc update mechanism.

_Source: [Docsie - MCP Server Documentation Integration](https://www.docsie.io/blog/articles/mcp-server-documentation-integration-2026/), [Google Developer Knowledge API](https://www.infoq.com/news/2026/02/google-documentation-ai-agents/)_

## Architectural Design: bmad-update-project-docs Skill

### Proposed Skill Architecture

The skill follows the BMAD skill convention (SKILL.md + workflow.md + supporting files) and the autoresearch-inspired `init/update/check` mode pattern.

**Skill Directory Structure:**

```
.claude/skills/bmad-update-project-docs/
├── SKILL.md                          # Frontmatter + invocation rules
├── workflow.md                       # Mode router (update/check/full)
├── instructions.md                   # Core update logic
├── templates/
│   └── section-update-prompt.md      # Prompt template for section regeneration
└── references/
    └── doc-section-mapping.md        # Maps file patterns → doc sections
```

### Three Operating Modes

| Mode | Command | What It Does |
|------|---------|-------------|
| **update** (default) | `/update-project-docs` | Git-diff detection → update affected doc sections |
| **check** | `/update-project-docs check` | Read-only health report — which docs are stale, what changed |
| **full** | `/update-project-docs full` | Delegates to `bmad-document-project` for full rescan |

### Update Mode — Core Algorithm

```
Phase 1: DETECT CHANGES
  1. Read project-scan-report.json → extract git_ref_at_last_update
  2. Run: git log --name-only --pretty=format:"" <last_ref>..HEAD
  3. Deduplicate and classify changed files

Phase 2: MAP CHANGES TO DOC SECTIONS
  4. For each changed file, determine which doc(s) it affects:
     - homelab-infra/ansible/roles/*     → architecture-homelab-infra.md
     - homelab-infra/terraform/*         → architecture-homelab-infra.md
     - homelab-apps/stacks/*             → architecture-homelab-apps.md
     - homelab-playbook/*                → architecture-homelab-playbook.md
     - Any repo structural change        → source-tree-analysis.md
     - New services/stacks/roles         → project-overview.md, index.md
     - Deployment changes                → deployment-guide.md
     - Dev workflow changes              → development-guide.md
     - Cross-repo integration changes    → integration-architecture.md
  5. Build update_plan: list of (doc_file, sections_to_update, changed_source_files)

Phase 3: PRESENT PLAN TO USER
  6. Show: "I detected N files changed since last doc update. Here's what I'd update:"
     - List each doc file and the sections affected
     - Show which source files drove each change
  7. User confirms or adjusts the plan

Phase 4: EXECUTE UPDATES
  8. For each doc in update_plan:
     a. Read current doc file
     b. Read changed source files that affect this doc
     c. Regenerate ONLY the affected sections using section-update-prompt.md
     d. Preserve all unchanged sections exactly as-is
     e. Write updated doc file
  9. Update index.md if any new docs or sections were added

Phase 5: UPDATE STATE
  10. Update project-scan-report.json:
      - git_ref_at_last_update = current HEAD
      - last_incremental_update = current date
      - section_timestamps = updated for each modified section
```

### Check Mode — Doc Health Report

```
1. Read project-scan-report.json → extract timestamps
2. Run: git log --name-only --pretty=format:"" <last_ref>..HEAD
3. For each changed file, determine affected docs
4. Report:
   "Documentation Health Report:
    ✅ project-overview.md — current (last updated 2026-04-02)
    ⚠️ architecture-homelab-infra.md — STALE (3 files changed since last update)
       Changed: ansible/roles/ai-dev-tmux/*, ansible/roles/ai-dev-omega-memory/*
    ✅ architecture-homelab-apps.md — current
    ⚠️ source-tree-analysis.md — STALE (new directories detected)

    Recommendation: Run /update-project-docs to update 2 stale documents."
5. No changes made — read-only
```

### File-to-Doc Mapping Strategy

The mapping is configurable via `references/doc-section-mapping.md`, making it adaptable across projects:

```yaml
# doc-section-mapping.md (loaded as context by the skill)
mappings:
  - pattern: "homelab-infra/ansible/roles/**"
    docs: ["architecture-homelab-infra.md"]
    sections: ["Roles", "Deployment Sequence"]
  - pattern: "homelab-infra/terraform/**"
    docs: ["architecture-homelab-infra.md"]
    sections: ["Terraform Module Architecture", "Infrastructure Resources"]
  - pattern: "homelab-apps/stacks/**"
    docs: ["architecture-homelab-apps.md"]
    sections: ["Application Services"]
  - pattern: "*/docker-compose.yml"
    docs: ["project-overview.md"]
    sections: ["Application Services"]
  - pattern: "**"
    docs: ["source-tree-analysis.md"]
    sections: ["_full_regenerate"]  # Always regenerate tree on any change
```

### Section-Level Update vs Full Regeneration

**Section-level update (default):** Read the current doc, identify the H2/H3 section that needs updating, regenerate only that section from the changed source files, replace in-place. This preserves any manual edits in other sections.

**Full regeneration (fallback):** For docs like `source-tree-analysis.md` where the entire content is derived from directory scanning, full regeneration is simpler and more accurate. Marked as `_full_regenerate` in the mapping.

### Autoresearch Self-Improvement Integration

The skill's `workflow.md` serves as the autoresearch `program.md` equivalent — the editable instruction file:

```
Autoresearch improvement loop for this skill:

1. METRIC: doc_accuracy_score
   - After update, count sections that correctly reflect current code state
   - Score = correct_sections / total_updated_sections

2. EVAL: Run /update-project-docs check after /update-project-docs
   - All previously-stale docs should now show ✅ current
   - No section should reference deleted/renamed files
   - All index.md links should resolve

3. ITERATE: Modify workflow.md instructions
   - Improve section detection heuristics
   - Refine prompt templates for better section regeneration
   - Adjust file-to-doc mappings based on missed updates

4. KEEP/REVERT: Based on doc_accuracy_score
```

This means the skill can improve itself over time through the autoresearch loop — the `check` mode provides the scalar metric, and the `workflow.md` is the editable asset.

### Relationship to Existing bmad-document-project

```
bmad-document-project          bmad-update-project-docs
├── initial_scan          ←──── /update-project-docs full (delegates)
├── full_rescan           ←──── /update-project-docs full (delegates)
├── deep_dive                   (independent feature, kept in original)
│
│   SHARED:
├── docs/ output folder
├── project-scan-report.json (extended with incremental fields)
├── documentation-requirements.csv (project type detection)
├── templates/ (doc format conventions)
│
│   NEW (only in update skill):
│                                ├── update mode (git-diff → section update)
│                                ├── check mode (health report)
│                                └── doc-section-mapping.md
```

_Source: Architectural design based on research findings from [autoresearch patterns](https://github.com/uditgoenka/autoresearch), [BMAD skill conventions](https://aj-geddes.github.io/claude-code-bmad-skills/skills/), [Claude Code skills best practices](https://code.claude.com/docs/en/skills)_

## Implementation Approach & Recommendations

### Implementation Roadmap

**Phase 1: Build the Core Skill (MVP)**

| Step | What | How |
|------|------|-----|
| 1 | Create skill directory structure | `SKILL.md`, `workflow.md`, `instructions.md`, `templates/`, `references/` |
| 2 | Implement `check` mode first | Simplest mode — read-only, no file mutations. Validates the git-diff detection and file-to-doc mapping logic |
| 3 | Implement `update` mode | Core algorithm: detect → map → present plan → user confirms → update sections → update state |
| 4 | Implement `full` mode | Thin wrapper that delegates to existing `bmad-document-project` |
| 5 | Test on homelab project | Run after a known epic completion, verify docs are correctly updated |
| 6 | Iterate using Claude A/B pattern | Claude A refines the skill, Claude B tests it on fresh context |

**Phase 2: Self-Improvement Loop**

| Step | What |
|------|------|
| 7 | Define eval cases — known epics with expected doc changes |
| 8 | Add autoresearch-style `doc_accuracy_score` metric |
| 9 | Run improvement loop: modify workflow.md → test → measure → keep/revert |
| 10 | Refine `doc-section-mapping.md` based on missed/incorrect updates |

**Phase 3: Integration into BMAD Workflow**

| Step | What |
|------|------|
| 11 | Add `/update-project-docs` to post-epic checklist in BMAD workflow |
| 12 | Document in sprint-planning/retrospective templates as a standard step |
| 13 | (Future) Hermes Director triggers doc update as part of autonomous epic completion |

### Development Workflow for Building the Skill

Following Claude Code skill best practices:

1. **Define use cases first** — "After completing an epic that adds 3 Ansible roles, run `/update-project-docs` and it updates `architecture-homelab-infra.md` and `source-tree-analysis.md` without touching other docs"
2. **Start simple** — Begin with `check` mode (read-only, no risk), validate change detection works
3. **Include examples** — Put sample inputs/outputs in SKILL.md so Claude understands what success looks like
4. **Test after each change** — Don't build all three modes before testing any
5. **Use the Claude A/B pattern** — Claude A develops the skill, Claude B tests it on real tasks with fresh context

_Source: [Claude Code Skills Docs](https://code.claude.com/docs/en/skills), [How to Build a Production-Ready Skill](https://towardsdatascience.com/how-to-build-a-production-ready-claude-code-skill/), [Eval and Iterate on Skills](https://www.mager.co/blog/2026-03-08-claude-code-eval-loop/)_

### Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Section detection misses a change | Doc stays stale for one section | `check` mode catches it; user can add mapping to `doc-section-mapping.md` |
| Section update overwrites manual edits | Loss of human-curated content | Present plan to user before writing; use diff preview |
| `project-scan-report.json` gets corrupted | State tracking breaks | Fallback: treat as first run, use `git log` from last doc modification date |
| Large epics produce too many changes | Overwhelming update plan | Group by doc file, let user select which docs to update |
| Git history not available (shallow clone) | Can't detect changes | Warn user; offer `full` mode as fallback |

### What This Skill Does NOT Replace

| Scenario | Use This | Not This |
|----------|----------|----------|
| First-time project documentation | `bmad-document-project` (full scan) | update-project-docs |
| Major project restructure (new repos, rearchitecture) | `bmad-document-project` (full rescan) | update-project-docs |
| Post-epic incremental update | `update-project-docs` (update mode) | bmad-document-project |
| "Are my docs current?" health check | `update-project-docs` (check mode) | manual inspection |
| Deep-dive into a specific module | `bmad-document-project` (deep_dive mode) | update-project-docs |

### Success Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Doc accuracy after update | 100% of changed files reflected in docs | `check` mode reports 0 stale docs after `update` |
| Sections preserved | Unchanged sections identical before/after | Diff of doc file shows only expected sections changed |
| Time to update | <5 minutes for a typical epic | Wall-clock time from invocation to completion |
| False positives | <10% of proposed updates are unnecessary | User rejects fewer than 1 in 10 proposed changes |
| Mapping coverage | All file patterns in project have a doc mapping | `check` mode reports "unmapped files: 0" |

### Rejected Alternatives

| Alternative | Why Rejected |
|-------------|-------------|
| MCP-based real-time sync | Over-engineered for local git-tracked IaC project; adds unnecessary infrastructure |
| Full regeneration after every epic | Wastes tokens, risks losing manual edits, takes 10-30 min vs <5 min |
| Git hooks (auto-trigger on commit) | Too granular — docs should update per epic, not per commit |
| Separate documentation repo | Adds cross-repo sync complexity; docs/ in the same workspace is simpler |
| Custom Python tool instead of BMAD skill | Loses Claude Code integration, context awareness, and BMAD ecosystem benefits |
| Modifying BMAD built-in skills | BMAD updates overwrite `.claude/skills/bmad-*/` — all custom changes lost |

## Autoresearch in the BMAD Story Workflow

### The Opportunity

The autoresearch pattern can be embedded within BMAD story execution — not just for skill improvement, but for improving code output quality per story.

### Two Application Points

**1. During `/create-story` — Define Eval Assertions**

Add an "Eval Assertions" section to the story template that derives binary test assertions from acceptance criteria:

```markdown
## Eval Assertions (for autoresearch verification)

- [ ] `omega --version` exits with code 0 → OMEGA installed
- [ ] `systemctl --user is-active omega-mcp` returns "active" → MCP running
- [ ] `omega search --query "test"` completes in <2s → search performance
- [ ] `omega doctor` reports all checks passing → health check
- [ ] `.env` file has mode 0600 → secret permissions
```

This is TDD where tests come from the story spec. No BMAD skill modification needed — the template is user-controlled.

**2. After `/code-review` — Run Autoresearch Fix Loop**

If code review identifies failures, use `/autoresearch:fix` to iterate:
- Modify code → run eval assertions → keep if more pass → revert if fewer → repeat until all green

### BMAD Update-Safety: Critical Design Constraint

**Problem:** BMAD skills live in `.claude/skills/bmad-*/`. BMAD updates overwrite these files. Any modifications to built-in skills are lost on update.

**Solution: Wrapper skills + user-controlled templates, not modifications.**

| Component | Who Owns It | BMAD-Update-Safe? |
|-----------|------------|-------------------|
| `.claude/skills/bmad-create-story/` | BMAD upstream | NO — don't modify |
| `.claude/skills/bmad-dev-story/` | BMAD upstream | NO — don't modify |
| Story template in `_bmad-output/` | User (you) | YES — add eval assertions here |
| `/autoresearch:fix` skill | Separate install (uditgoenka or custom) | YES — independent of BMAD |
| `/update-project-docs` skill | New standalone skill | YES — independent of BMAD |

**The eval assertions live in the story OUTPUT file (which you control), not in the BMAD skill code (which BMAD controls).** BMAD's `/create-story` reads the template and fills it in. If the template has an "Eval Assertions" section, BMAD populates it.

### Enhanced BMAD Workflow (Update-Safe)

```
BMAD skills (upstream, untouched):
  /bmad-create-story    → Uses YOUR story template (with eval assertions section)
  /bmad-dev-story       → Implements the story
  /bmad-code-review     → Reviews the code
  /bmad-retrospective   → Reviews the epic

Your additions (standalone, update-safe):
  Story template         → Add "Eval Assertions" section (yours, not BMAD's)
  /autoresearch:fix      → Install separately, run after code-review if needed
  /update-project-docs   → New skill, runs after epic completion
```

### What Already Exists vs What's Needed

| Existing | What It Does | Gap |
|----------|-------------|-----|
| `/autoresearch:fix` (uditgoenka) | Iterative error crushing (tests, lint, types) | Doesn't know story requirements — only mechanical quality |
| `/autoresearch:plan` | Wizard defining goal → scope → metric → verify | Could generate eval criteria, but manual per-story |
| BMAD `/code-review` | 3-layer adversarial review | Produces findings but doesn't auto-fix |
| BMAD `/qa-automate` | Generates automated tests | After implementation, not before |
| TDD with Claude Code | Red-green-refactor loop | Tests written by developer, not derived from story |

**The gap:** Nobody connects story acceptance criteria to autoresearch eval assertions automatically. The solution is the story template section — simple, update-safe, no skill modification required.

---

## Research Synthesis & Conclusions

### Executive Summary

This research investigated three interconnected questions: (1) how to maintain project documentation incrementally after each BMAD epic, (2) whether Karpathy's autoresearch pattern can improve BMAD skill quality, and (3) how autoresearch can be integrated into the BMAD story execution workflow.

**Key Findings:**

1. **Incremental documentation is the right approach** — industry data shows incremental modernization is 2.5x more likely to succeed than full regeneration. Mintlify validates the git-diff-aware update pattern in production. MCP-based real-time sync is over-engineered for a local git-tracked IaC project.

2. **The autoresearch pattern maps directly to BMAD skills** — the `program.md` concept (editable instruction file optimized through measured iteration) maps to BMAD's `workflow.md`. The `/autoresearch:learn` modes (`init/update/check`) fill the exact gap missing from `bmad-document-project`.

3. **BMAD update-safety is a critical constraint** — never modify BMAD's built-in skills. Use wrapper skills, user-controlled templates, and separately-installed tools instead.

4. **Autoresearch in the story workflow works through templates, not skill modifications** — eval assertions derived from acceptance criteria live in the story output file, which the user controls. `/autoresearch:fix` is a separately-installed skill run after code review.

### Deliverables Recommended

| Deliverable | Type | Priority | Effort |
|-------------|------|----------|--------|
| `bmad-update-project-docs` skill | New standalone BMAD skill | High | Medium — 5-file skill with 3 modes |
| Story template with eval assertions | Template modification | High | Low — add one section to existing template |
| `autoresearch` skill installation | Install existing skill | Medium | Low — install uditgoenka/autoresearch |
| Doc-section-mapping configuration | Reference file | High | Low — YAML mapping of file patterns → docs |
| Self-improvement eval suite | Eval definitions | Low | Medium — define binary tests for doc accuracy |

### Enhancement Wrapper Pattern & Autoresearch Cadence

**Enhancement wrapper pattern:** Each BMAD skill gets a standalone wrapper that calls the original and adds enhancements. Wrappers are autoresearch-improvable; BMAD skills are never modified.

```
BMAD skills (upstream, never modified):
  /bmad-create-story
  /bmad-dev-story
  /bmad-code-review

Enhancement wrappers (autoresearch-improvable):
  /create-story-with-evals     → wraps /bmad-create-story + adds eval assertions
  /dev-story-verified          → wraps /bmad-dev-story + runs eval assertions after (Phase 2)
  /code-review-with-fix        → wraps /bmad-code-review + runs /autoresearch:fix (Phase 2)
```

**Autoresearch skill improvement cadence:**

```
Phase 1 (MVP — manual, per-epic):
  After each epic completion:
    1. Manually review: "Did the wrappers help? What did they miss?"
    2. Capture learnings as eval cases (add to skill's eval suite)
    3. Run /autoresearch on each wrapper skill once (~30 min)
    4. Keep improvements, commit
    → Lightweight, manual, builds the eval dataset from real usage

Phase 2 (Director operational — automated, overnight):
  Hermes Director schedules overnight:
    1. Load accumulated eval cases (growing with each epic)
    2. Run autoresearch loop on each wrapper skill (30-50 iterations)
    3. Morning: review proposed improvements, accept/reject
    → Compound learning: each epic makes wrappers better

Key principle: Autoresearch needs eval cases from real usage.
You can't optimize a skill that hasn't been used.
  Use → Capture evals → Autoresearch → Improved skill → Use again → ...
```

**Epic completion checklist (updated):**
```
1. /retrospective              ← Review the epic
2. /update-project-docs        ← Update docs
3. Capture eval cases          ← What worked/failed in wrapper skills
4. Run autoresearch on wrappers ← Optional Phase 1, automated Phase 2
```

### Implementation Priority

```
Phase 1 (Immediate — with AI Dev Container MVP):
  1. Build /create-story-with-evals wrapper skill
  2. Install autoresearch skill (uditgoenka/autoresearch)
  3. Build bmad-update-project-docs skill (check mode first, then update)

Phase 2 (After first epic completion):
  4. Build /dev-story-verified wrapper
  5. Build /code-review-with-fix wrapper
  6. Run /update-project-docs on real epic output — validate the approach
  7. Begin autoresearch improvement loop on wrapper skills
  8. Refine doc-section-mapping based on actual project changes

Phase 3 (With Hermes Director — AI Dev Container Phase 2):
  9. Director triggers /update-project-docs after autonomous epic completion
  10. Director triggers /autoresearch:fix after code review failures
  11. Director schedules overnight autoresearch on wrapper skills
  12. OMEGA Memory captures eval cases for cross-project learning
```

### Sources

- [GitHub - karpathy/autoresearch](https://github.com/karpathy/autoresearch) — Original autoresearch framework
- [GitHub - uditgoenka/autoresearch](https://github.com/uditgoenka/autoresearch) — Claude Code autoresearch skill
- [MindStudio - AutoResearch Pattern for Claude Code Skills](https://www.mindstudio.ai/blog/karpathy-autoresearch-pattern-claude-code-skills)
- [MindStudio - Self-Improving AI Skills](https://www.mindstudio.ai/blog/claude-code-autoresearch-self-improving-skills)
- [MindStudio - AutoResearch Eval Loop](https://www.mindstudio.ai/blog/autoresearch-eval-loop-binary-tests-claude-code-skills)
- [DataCamp - Guide to AutoResearch](https://www.datacamp.com/tutorial/guide-to-autoresearch)
- [VentureBeat - Karpathy's AutoResearch](https://venturebeat.com/technology/andrej-karpathys-new-open-source-autoresearch-lets-you-run-hundreds-of-ai)
- [Mintlify - Auto-Generate Docs from Repos](https://www.mintlify.com/blog/auto-generate-docs-from-repos)
- [Document360 - AI Documentation Trends 2026](https://document360.com/blog/ai-documentation-trends/)
- [Docsie - MCP Server Documentation Integration](https://www.docsie.io/blog/articles/mcp-server-documentation-integration-2026/)
- [Claude Code Skills Documentation](https://code.claude.com/docs/en/skills)
- [Claude Code Hooks Guide](https://code.claude.com/docs/en/hooks-guide)
- [BMAD Method Skills](https://aj-geddes.github.io/claude-code-bmad-skills/skills/)
- [Zerocopy - Autoresearch for Agentic Coding Skills](https://zerocopy.blog/2026/03/25/karpathys-autoresearch-improving-agentic-coding-skills/)
- [AI Maker - Skill That Improves All Skills](https://aimaker.substack.com/p/how-i-built-skill-improves-all-skills-karpathy-autoresearch-loop)
- [Medium - Self-Improving Skills with AutoResearch](https://medium.com/@shubhjain191/how-to-make-your-claude-code-skills-self-improving-using-auto-research-803ff97d5483)
- [Google Developer Knowledge API via MCP](https://www.infoq.com/news/2026/02/google-documentation-ai-agents/)

---

**Technical Research Completion Date:** 2026-04-03
**Source Verification:** All technical claims cited with current sources
**Confidence Level:** High — based on multiple authoritative sources and validated patterns
