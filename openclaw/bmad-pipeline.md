# BMAD Pipeline — Workflow Map & Model Routing

**Last Updated:** 2026-02-06
**Status:** Active Reference

## Purpose

Map every BMAD workflow command to its phase, agent, and recommended model for cost-optimized execution in this homelab OpenClaw setup.

---

## Claude CLI Delegation — Opus 4.6 (Max Subscription)

All Claude CLI delegated tasks run on **Opus 4.6** via the Claude Max subscription. No model-tier decisions needed — Max provides Opus for everything at a fixed monthly cost. Per-token pricing is irrelevant for these tasks.

| Model | Subscription | Used For |
|---|---|---|
| **Opus 4.6** | Claude Max ($100-200/mo) | All Claude CLI delegated work (architecture, dev stories, code review, quick dev) |

See [claude-cli-delegation.md](./claude-cli-delegation.md) for invocation patterns and auth setup.

---

## Pipeline Overview

```
Phase 1: Analysis (optional)     -> Gemini Pro (free via OAuth)
Phase 2: Planning                -> Gemini Pro (free) / Groq (cheap for validation)
Phase 3: Solutioning             -> Claude CLI Opus 4.6 for architecture, Gemini Pro for stories
Phase 4: Implementation          -> Claude CLI Opus 4.6 for dev, Gemini Pro for sprint mgmt, Groq for QA
Quick Flow (parallel track)      -> Gemini Pro / Claude CLI Opus 4.6 depending on complexity
Context & Documentation          -> Gemini Pro (free via OAuth)
```

**Why Gemini Pro for BMAD instead of Flash?** BMAD workflows produce structured planning artifacts (PRDs, stories, architecture docs) where reasoning quality directly impacts downstream code generation. Pro's stronger reasoning is worth it — and it's still free via OAuth (same 60 RPM / 1,000 req/day quota). Flash remains the default primary for non-BMAD tasks (Telegram supervision, heartbeats, general chat).

---

## Phase 1: Analysis (Optional)

Explore the problem space and validate ideas before committing to planning.

| Command | Code | Workflow | Agent | Recommended Model | Est. Cost |
|---|---|---|---|---|---|
| `/bmad-bmm-create-product-brief` | CB | Create Product Brief | Analyst (Mary) | Gemini Pro | $0 |
| `/bmad-bmm-market-research` | MR | Market Research | Analyst (Mary) | Gemini Pro | $0 |
| `/bmad-bmm-domain-research` | DR | Domain Research | Analyst (Mary) | Gemini Pro | $0 |
| `/bmad-bmm-technical-research` | TR | Technical Research | Analyst (Mary) | Gemini Pro or `reason` | $0-0.05 |
| `/bmad-brainstorming` | BP | Brainstorming | Analyst (Mary) | Gemini Pro | $0 |

**Notes:**
- All analysis workflows use Gemini Pro for better reasoning quality on planning artifacts
- Technical research can escalate to `reason` (DeepSeek R1) if evaluating complex architecture trade-offs
- Market/domain research use web search tools — Pro's reasoning helps synthesize findings

---

## Phase 2: Planning

Define what to build and for whom.

| Command | Code | Workflow | Variant | Agent | Recommended Model | Est. Cost |
|---|---|---|---|---|---|---|
| `/bmad-bmm-create-prd` | CP | Create PRD | Create | PM (John) | Gemini Pro | $0 |
| `/bmad-bmm-validate-prd` | VP | Validate PRD | Validate | PM (John) | Gemini Pro or `quality` | $0-0.03 |
| `/bmad-bmm-edit-prd` | EP | Edit PRD | Edit | PM (John) | Gemini Pro | $0 |
| `/bmad-bmm-create-ux-design` | CU | Create UX Design | Create | UX (Sally) | Gemini Pro | $0 |

**Notes:**
- PRD creation uses Pro for better structured output quality — still free via OAuth
- PRD validation can use Pro (free) or `quality` (Groq) for a second-opinion perspective
- Edit is iterative refinement — Pro handles this well

---

## Phase 3: Solutioning

Decide how to build it and break work into stories.

| Command | Code | Workflow | Variant | Agent | Recommended Model | Est. Cost |
|---|---|---|---|---|---|---|
| `/bmad-bmm-create-architecture` | CA | Create Architecture | Create | Architect (Winston) | **Claude CLI Opus 4.6** | Subscription |
| `/bmad-bmm-create-epics-and-stories` | CE | Create Epics & Stories | Create | PM (John) | Gemini Pro | $0 |
| `/bmad-bmm-check-implementation-readiness` | IR | Implementation Readiness | Validate | Architect (Winston) | **Claude CLI Opus 4.6** | Subscription |

**Notes:**
- Architecture and implementation readiness are delegated to Claude CLI (Opus 4.6 via Max subscription). No cost-per-token concern — use the best model for these high-stakes artifacts
- Epics & stories are structured extraction from PRD — Pro handles this well and is still free

---

## Phase 4: Implementation

Build it, one story at a time.

| Command | Code | Workflow | Variant | Agent | Recommended Model | Est. Cost |
|---|---|---|---|---|---|---|
| `/bmad-bmm-sprint-planning` | SP | Sprint Planning | Create | Scrum Master (Bob) | Gemini Pro | $0 |
| `/bmad-bmm-sprint-status` | SS | Sprint Status | Monitor | Scrum Master (Bob) | Gemini Pro | $0 |
| `/bmad-bmm-create-story` | CS | Create Story | Create | Scrum Master (Bob) | Gemini Pro | $0 |
| (validate-story) | VS | Validate Story | Validate | Scrum Master (Bob) | `quality` | ~$0.01 |
| `/bmad-bmm-dev-story` | DS | Dev Story | Create | Developer (Amelia) | **Claude CLI Opus 4.6** | Subscription |
| `/bmad-bmm-code-review` | CR | Code Review | Review | Developer (Amelia) | **Claude CLI Opus 4.6** | Subscription |
| `/bmad-bmm-qa-automate` | QA | QA Automation | Create | QA (Quinn) | `quality` | ~$0.01-0.03 |
| `/bmad-bmm-correct-course` | CC | Correct Course | Change Mgmt | Scrum Master (Bob) | `reason` | ~$0.02-0.05 |
| `/bmad-bmm-retrospective` | ER | Retrospective | Review | Scrum Master (Bob) | Gemini Pro | $0 |

**Scope & Frequency:**
- **Per epic:** Sprint planning, sprint status, retrospective — run once per epic/sprint
- **Per user story:** Create story, dev story, code review, QA automate — run once per story (multiply by number of stories in the epic)
- **Exception-only:** Correct course — only triggered when implementation reveals an issue, limitation, or improvement that would alter the architecture. Almost always preceded by research (Phase 1 `/bmad-bmm-technical-research` or `/bmad-bmm-domain-research`) before course-correcting

**Notes:**
- Dev story is IaC code generation (Terraform, Ansible, Compose). Delegated to Claude CLI (Opus 4.6) — best code quality, uses CLAUDE.md for project conventions, runs tests automatically
- Code review is delegated to Claude CLI (Opus 4.6) — can read the full codebase, run linters, check git history for context
- QA automation is pattern-based test generation — `quality` (Groq) is sufficient
- Sprint planning/status are structured YAML operations — Pro handles this well
- Correct course needs reasoning about impact analysis — `reason` is a good budget pick. Trigger flow: discover issue during dev → research (Phase 1) → correct course → update architecture/stories as needed
- Retrospective is reflective prose — Pro captures nuance better for lessons learned

---

## Quick Flow (Parallel Track)

Skip phases 1-3 for small, well-understood work.

| Command | Code | Workflow | Agent | Recommended Model | Est. Cost |
|---|---|---|---|---|---|
| `/bmad-bmm-quick-spec` | QS | Quick Spec | Solo Dev (Barry) | Gemini Pro or `quality` | $0-0.02 |
| `/bmad-bmm-quick-dev` | QD | Quick Dev | Solo Dev (Barry) | **Claude CLI Opus 4.6** | Subscription |

**Notes:**
- Quick spec is conversational discovery — start on free, escalate to `quality` if complex
- Quick dev is delegated to Claude CLI (Opus 4.6) — even small tasks get the best model, no cost tradeoff with Max subscription

---

## Context Management

Manage project context and documentation for brownfield projects.

| Command | Code | Workflow | Agent | Recommended Model | Est. Cost |
|---|---|---|---|---|---|
| `/bmad-bmm-document-project` | DP | Document Project | Analyst (Mary) | Gemini Pro | $0 |
| `/bmad-bmm-generate-project-context` | GPC | Generate Project Context | Analyst (Mary) | Gemini Pro | $0 |

---

## Documentation & Technical Writing

| Command | Code | Workflow | Agent | Recommended Model | Est. Cost |
|---|---|---|---|---|---|
| Write Document | WD | Write Document | Tech Writer (Paige) | Gemini Pro | $0 |
| Update Standards | US | Update Standards | Tech Writer (Paige) | Gemini Pro | $0 |
| Mermaid Generate | MG | Mermaid Diagrams | Tech Writer (Paige) | Gemini Pro | $0 |
| Validate Document | VD | Validate Document | Tech Writer (Paige) | Gemini Pro or `quality` | $0-0.01 |
| Explain Concept | EC | Explain Concept | Tech Writer (Paige) | Gemini Pro | $0 |

**Notes:**
- These are accessed via agent menus (Paige), not direct `/bmad-bmm-*` commands
- Document validation can use Pro (free) or `quality` (Groq) for a different perspective

---

## Core Utilities

| Command | Code | Workflow | Recommended Model | Est. Cost |
|---|---|---|---|---|
| `/bmad-help` | BH | BMAD Help | `instant` | $0 |
| `/bmad-party-mode` | PM | Multi-Agent Discussion | Gemini Pro | $0 |
| `/bmad-index-docs` | ID | Index Docs | `instant` | $0 |
| `/bmad-shard-doc` | SD | Shard Large Document | `instant` | $0 |
| `/bmad-editorial-review-prose` | EP | Editorial Review (Prose) | Gemini Pro | $0 |
| `/bmad-editorial-review-structure` | ES | Editorial Review (Structure) | `quality` | ~$0.01 |
| `/bmad-review-adversarial-general` | AR | Adversarial Review | `reason` | ~$0.02-0.05 |

**Notes:**
- Help, indexing, and sharding are mechanical — use cheapest model
- Adversarial review needs reasoning depth — `reason` is the budget-friendly pick

---

## Cost Per Full BMAD Cycle

A complete feature cycle through all phases:

| Phase | Claude CLI Delegated | Free/Cheap (OpenClaw) | Cost |
|---|---|---|---|
| 1. Analysis | 0 | 5 | $0 (Gemini Pro) |
| 2. Planning | 0 | 4 | $0 (Gemini Pro + Groq) |
| 3. Solutioning | 2 (architecture, readiness) | 1 | Subscription (Opus 4.6) |
| 4. Implementation | 2 (dev-story, code review) | 6 | Subscription (Opus 4.6) |
| **Total** | **4 delegated sessions** | **16 free/cheap** | **$0 variable** |

**With Max subscription, there is no per-token cost for Claude CLI delegated work.** All 4 delegated sessions (architecture, impl. readiness, dev story, code review) run on Opus 4.6 within the fixed monthly subscription. The remaining 16 workflows run on free (Gemini Pro) or cheap (Groq) models.

---

## Model Switching Workflow

When working through a BMAD cycle, switch models at these transition points:

```
Start BMAD session: switch to Gemini Pro (/model pro)
  │
  ├─ Phase 1: Stay on Pro ───────────────────────── /product-brief, /research
  ├─ Phase 2: Stay on Pro ───────────────────────── /create-prd, /edit-prd, /validate-prd
  │
  ├─ Phase 3: → Claude CLI (Opus 4.6) ─────────── /create-architecture
  │            /model pro ──────── /create-epics-and-stories
  │            → Claude CLI (Opus 4.6) ─────────── /check-implementation-readiness
  │
  ├─ Phase 4: Stay on Pro ───────────────────────── /sprint-planning, /create-story
  │            → Claude CLI (Opus 4.6) ─────────── /dev-story
  │            → Claude CLI (Opus 4.6) ─────────── /code-review
  │            /model quality ────────────────────── /qa-automate
  │            /model pro ──────── /retrospective
  │
  └─ Back to Gemini Flash (default) when BMAD session ends
```

**Rule of thumb:** Switch to Gemini Pro at the start of any BMAD session. For architecture, impl. readiness, dev story, and code review — OpenClaw delegates to Claude CLI (Opus 4.6 via Max subscription). No model switching needed for these; OpenClaw handles the delegation via `exec`. Switch back to Flash (default) when BMAD work is done.

---

## Summary Statistics

- **Total workflows:** 31
- **Claude CLI delegated (Opus 4.6 via Max):** 5 (architecture, impl. readiness, dev-story, code-review, quick-dev)
- **Work well on Groq (cheap):** 7 (validations, QA, adversarial reviews, course corrections)
- **Gemini Pro (free via OAuth):** 19 (planning, research, documentation, sprint mgmt)

---

## Related Documents

- [model-routing-strategy.md](./model-routing-strategy.md) — Model inventory, aliases, and fallback chain
- [cost-optimization.md](./cost-optimization.md) — Cost optimization techniques and budget scenarios
- [openclaw-config-reference.md](./openclaw-config-reference.md) — Full openclaw.json configuration reference
- [claude-cli-delegation.md](./claude-cli-delegation.md) — Delegating dev work to Claude CLI via OpenClaw exec
