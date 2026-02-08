# BMAD Help

**Core Utility** | **Model:** `/model instant` (Groq) | **Cost:** $0

## When to Use

User asks for help with BMAD commands, workflow, or methodology.

## Execution

Handle locally on the cheapest model. This is a reference lookup.

Provide a quick reference of available BMAD workflows:

**Phase 1 — Analysis:** product-brief, market-research, domain-research, technical-research, brainstorming
**Phase 2 — Planning:** create-prd, validate-prd, edit-prd, create-ux-design
**Phase 3 — Solutioning:** create-architecture*, create-epics-and-stories, check-implementation-readiness*
**Phase 4 — Implementation:** sprint-planning, create-story, validate-story, dev-story*, code-review*, qa-automate, correct-course, retrospective
**Quick Flow:** quick-spec, quick-dev*
**Context:** document-project, generate-project-context
**Utilities:** index-docs, shard-doc, editorial-review-prose, editorial-review-structure, adversarial-review, party-mode

`*` = Delegated to Claude CLI (Opus 4.6)

## Output

A help summary. Point the user to `openclaw/bmad-pipeline.md` for the full reference.
