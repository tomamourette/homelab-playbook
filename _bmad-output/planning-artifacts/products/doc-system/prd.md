---
stepsCompleted:
  - step-01-init
  - step-02-discovery
  - step-02b-vision
  - step-02c-executive-summary
  - step-03-success
  - step-04-journeys
  - step-05-domain
  - step-06-innovation
  - step-07-project-type
  - step-08-scoping
  - step-09-functional
  - step-10-nonfunctional
  - step-11-polish
  - step-12-complete
classification:
  projectType: developer-infrastructure
  domain: devops-ai-assisted-development
  complexity: medium
  projectContext: brownfield
inputDocuments:
  - homelab-playbook/_bmad-output/planning-artifacts/research/technical-codebase-docs-system-research-2026-04-27.md
  - homelab-playbook/_bmad-output/planning-artifacts/research/technical-claude-md-best-practices-2026-04-27.md
workflowType: 'prd'
project_name: 'Codebase Documentation System'
output_path: 'homelab-playbook/_bmad-output/planning-artifacts/products/doc-system/prd.md'
director_mode: true
---

# Product Requirements Document - Codebase Documentation System

**Author:** tomamourette
**Date:** 2026-04-27
**Status:** Complete (director-mode synthesis from two locked research artifacts)

---

## Executive Summary

The homelab has fully wired plumbing for documentation — GitNexus indexing on every commit, Graphiti capturing temporal decisions, BMAD generating `/docs/` baselines, Claude auto-memory accumulating operator learnings, an existing root `CLAUDE.md` instructing every Claude Code session — but no single layer that turns those streams into a wiki readers (PM, PO, devs, customers, AI agents) can rely on as current. The gap is not tooling, it is the **maintenance loop and the source-of-truth topology**: every fact-type has multiple homes today, and the wiki layer drifts because no one is responsible for keeping it synthesized.

This product is a self-maintaining, multi-audience documentation system for the homelab and any project derived from it. Markdown-in-git is the single source of truth; consumption fans out one-way to Obsidian (operator IDE), Azure DevOps Wiki (PM/PO/devs gated by existing AAD), an audience-tuned customer wiki (workspace `/wiki/` for non-AzDO projects), an MCP server (Cursor/Continue/future LLM clients), and an `llms.txt` manifest. Reference docs auto-generate from the GitNexus knowledge graph; narrative and decision docs are co-maintained by the operator and Claude Code agents on Karpathy's ingest/query/lint loop. A new skill, `wiki-publish-audience`, synthesizes the customer wiki from the operator wiki on demand — letting different audiences see different tones, depths, and redactions from one canonical body of markdown.

The project also delivers a refactor of the homelab's root `CLAUDE.md` from its current ~250+ line trajectory toward the 1,094-line ruflo anti-pattern down to Anthropic's published target of under 200 lines, using the Astral stub-redirect (`CLAUDE.md → AGENTS.md`) plus Cline-style topic split (`.claude/rules/<topic>.md`) — a pattern Anthropic explicitly endorses verbatim. The two refactors (doc system + schema) ship together because they share the same Claude Code hook lifecycle and the same operator workflow: every session that produces decisions also produces wiki updates, and every wiki edit is gated by the same instruction surface.

### What Makes This Special

Three things distinguish this from generic "docs as code" or hosted AI doc platforms:

1. **Audience-tuned synthesis from a single SoT.** The customer wiki is not a separate authored surface; it is a transform applied to the operator wiki via the `wiki-publish-audience` skill. Tom writes once at full operator depth; the skill produces customer-, PM-, and public-friendly variants on demand. AzDO-backed projects push to AzDO Wiki; non-AzDO projects write to the workspace `/wiki/`. The transform is configurable per audience without touching the source.
2. **Karpathy's LLM-Wiki maintenance loop wired to Claude Code's actual hook lifecycle.** Sessions feed ingest, edits trigger log appends, scheduled cron drives lint. Verified against Anthropic's hook spec, with the corrected understanding that `@`-imports are eager (so true lazy-load lives in Skills, slash commands, `UserPromptSubmit` hooks, or `paths:`-scoped rules — not in the topic split itself). The loop solves the "who maintains it" problem that abandons most wikis.
3. **GitNexus Code Wiki (OSS) for the Reference quadrant.** Auto-generated per-module documentation from the live knowledge graph, regen on PR/merge + weekly + on-demand, bounded to `/docs/reference/generated/`. Hallucination risk is lower than free-form synthesis because cross-references are graph-grounded. License-clean for the homelab (PolyForm-Noncommercial); the auto-update gap (enterprise-only feature) is recreated via a SessionEnd hook.

## Project Classification

- **Project Type:** developer-infrastructure (homelab-internal devops tooling and AI-agent instruction architecture)
- **Domain:** devops-ai-assisted-development (medium complexity — operator-scale, no regulated data, but with non-trivial cross-tool / cross-audience coordination concerns)
- **Complexity:** medium
- **Project Context:** brownfield — existing `/docs/` baseline (BMAD-generated 2026-04-02), GitNexus running, Claude Code with auto-memory active, Graphiti MCP available, ~250+ line root `CLAUDE.md` to refactor

## Success Criteria

### User Success

- **Operator (Tom)** can author once in Obsidian against `homelab-playbook/wiki/`, hit `/wiki publish customer`, and produce a clean audience-tuned wiki for non-tech audiences without re-writing content.
- **Operator** experiences ≤30 seconds of overhead per Claude Code session for wiki ingest (async runner, no in-session blocking).
- **Developer** onboarding to a homelab repo can answer "where do I start? what's the architecture? what was decided about X?" in ≤15 minutes by reading `index.md` and one referenced page, without asking another human.
- **PM/PO** can browse the AzDO Wiki for project status with AAD SSO and never see operator-only sections (e.g., Tailscale ACLs, internal hostnames, secrets references).
- **Customer** can read the customer-facing wiki via Tailscale (or AzDO Wiki for AzDO-backed projects) and find tutorials and how-tos written in plain language, with no operator jargon and no broken internal links.
- **AI agent (Claude Code, Cursor, Continue)** can consume the same `/docs/` and `homelab-playbook/wiki/` content via MCP server with zero per-tool re-authoring.

### Business Success

- **Documentation maintenance burden reduced by ≥50%** vs the current "humans write everything by hand" baseline, measured by operator-hours per month spent on doc updates.
- **Drift latency ≤24 hours** — between a code change landing on `main` and its dependent wiki page being flagged stale (scheduled lint + GitNexus PR/merge regen).
- **Zero customer-wiki leakage incidents** of operator-only content (secrets, internal hostnames, Tailscale ACLs) over the first 90 days.
- **LLM cost <€10/month** for the entire wiki maintenance loop (GitNexus regen + SessionEnd ingest + scheduled lint + audience-tuning passes).
- **Doc-system reach** = every audience listed has a native consumption surface (operator/Obsidian, PM-PO-dev/AzDO Wiki, customer/workspace-/wiki/-or-AzDO, AI agent/MCP server). Binary success metric.

### Technical Success

- **Single source of truth invariant holds** — every fact-type has exactly one authoritative home; no consumer is ever a writer (verified by CI mirror-direction check).
- **Frontmatter compliance = 100%** on `/docs/**/*.md` and `homelab-playbook/wiki/**/*.md` (pre-commit gate).
- **Hallucination escape rate** — synthesized claims contradicting sources flagged within 1 week (lint pass cross-checks `sources:` frontmatter against current source content).
- **Schema-file load size at session start** <5,000 tokens combined (CLAUDE.md stub + AGENTS.md + lazy-loaded `.claude/rules/<topic>.md` via `paths:` scoping or skill bodies).
- **Cross-tool schema works in Cursor and Codex** without per-tool re-authoring (manual verification post-migration).
- **Mirror-pipeline failures alert via existing crash-notifier pattern** (ntfy push) within 5 minutes.

### Measurable Outcomes

- AGENTS.md final length ≤120 lines (target headroom under Anthropic's 200-line published guidance).
- `.claude/rules/<topic>.md` total content ≤500 lines combined.
- Time-to-publish customer wiki from operator wiki: <2 minutes wall-clock for a small project, <10 minutes for the homelab.
- AzDO mirror latency from `main` push: <5 minutes.
- Scheduled weekly lint report posts to ntfy `docs-lint` topic with stale-pages count and contradictions count.

## Product Scope

### MVP - Minimum Viable Product

The MVP delivers a working operator-facing maintenance loop and the schema refactor — without yet adding the customer-wiki transform or all consumption surfaces. The MVP is independently useful: even without customer publish, the operator gets a self-maintaining wiki and a leaner `CLAUDE.md`/`AGENTS.md`.

**MVP includes:**

- Schema refactor Pass 1 + Pass 2: CLAUDE.md → AGENTS.md stub redirect + `.claude/rules/<topic>.md` topic split + audit cuts to ≤120 lines.
- Frontmatter spec applied to all `/docs/` and `homelab-playbook/wiki/` markdown files.
- `log.md` and `index.md` Karpathy primitives initialized in `homelab-playbook/wiki/`.
- SessionEnd ingest hook (async runner) wired into `~/.claude/hooks/docs/`.
- PostToolUse log.md hook (Edit/Write/MultiEdit on docs paths).
- Lint stack: markdownlint-cli2 + lychee + Vale + custom citation-checker + ajv frontmatter validator.
- Pre-commit hook gating frontmatter compliance.
- Scheduled weekly lint cron with ntfy report.
- GitNexus `wiki` test run on `homelab-playbook` with `--review` mode; output bounded to `/docs/reference/generated/`.

**MVP excludes** (deferred to Growth): customer-wiki skill, AzDO mirror, Quartz site, MCP doc server, llms.txt generator, GitNexus regen on PR/merge.

### Growth Features (Post-MVP)

- **Customer wiki publish skill** (`wiki-publish-audience`) — the load-bearing post-MVP feature. Reads operator wiki, applies audience filter via frontmatter + LLM tone-tuning, writes to workspace `/wiki/` (non-AzDO projects) or pushes to AzDO Wiki (AzDO projects).
- **AzDO Wiki one-way mirror** via Azure Pipelines for AzDO-backed projects (Sparkle-CPS first).
- **MCP doc server** (`arabold/docs-mcp-server`) registered in `~/.claude.json` so Cursor and Continue read the same source.
- **`llms.txt` generator** at workspace root + per-repo, walked by Diátaxis quadrant.
- **GitNexus regen on PR open + on merge to main** (extends existing post-commit hook with branch + path filter).
- **Quartz v4 build** for public-readable subset (only when a customer audience exists for a non-AzDO project).
- **Multi-skill split** of `wiki-publish-audience` into `wiki-filter-audience` + `wiki-tone-rewrite` + `wiki-mirror-azdo` + `wiki-mirror-workspace` if SKILL.md exceeds 500 lines.

### Vision (Future)

- **Cross-project skill portability**: the `wiki-publish-audience` skill works in any project derived from the homelab pattern (Sparkle-CPS, future projects) by reading project-context for AzDO vs non-AzDO targeting.
- **AGENTS.md as cross-tool universal**: Cursor and Codex parity for the homelab's instruction surface, verified by manual sessions in each.
- **Wiki search at scale**: integrate `qmd` (Karpathy-recommended local BM25 + vector search with MCP server) when `homelab-playbook/wiki/` exceeds ~100 pages.
- **Decision-graph integration**: the wiki's `sources:` frontmatter resolves `graphiti://` URIs at read time, surfacing decision lineage inline. Currently cited but not auto-resolved.
- **`autoresearch:fix` on the wiki itself**: the wiki becomes a target for the homelab's existing autoresearch loop — automated detection and PR for stale claims, broken citations, contradictions.
- **Customer-facing version pinning** — the audience-tuning skill emits versioned customer wikis tied to product release tags, not always reflecting `main`.

## User Journeys

### Journey Requirements Summary

These six journeys reveal the capability set documented in §Functional Requirements. Each maps cleanly to one or more capability areas (CA-1 Schema, CA-2 Wiki SoT, CA-3 Maintenance Loop, CA-4 Reference Auto-gen, CA-5 Audience Publish, CA-6 Multi-surface Consumption, CA-7 Drift & Quality, CA-8 Cross-tool Portability).

### Journey 1 — Operator captures a decision during a Claude Code session

**Persona:** Tom, homelab operator, mid-session debugging a PVE storage issue with Claude Code.

**Opening:** Tom is mid-session at his terminal, working through a tricky Proxmox HA failover bug. He and Claude have just figured out the root cause and decided to use a specific replication topology. The decision is non-obvious and matters for future sessions.

**Rising action:** Tom doesn't pause to write a doc — he keeps debugging. The session ends naturally (Claude finishes the task or Tom closes the terminal). The SessionEnd hook fires; the async ingest runner picks up the queue entry; over the next 15 minutes (cron tick), it reads the session transcript, identifies the decision-making turns, drafts an ADR-style entry as `docs/explanation/adr/adr-NNN-pve-replication-topology.md`, appends to `homelab-playbook/wiki/log.md`, and commits to a `wiki-bot/2026-04-27-session-XXXXX` branch.

**Climax:** Next morning, Tom checks `wiki-bot/*` branches, sees the auto-PR, reviews the ADR draft (frontmatter `owner: llm`), tweaks the wording, sets `owner: human`, and merges. The decision is now persistent, citable, and discoverable — without him having to remember to write it down.

**Resolution:** Future sessions reference the ADR via `sources: [bmad://docs/explanation/adr/adr-NNN-pve-replication-topology.md]` in dependent wiki pages. The operator's working memory is no longer the only place this decision lives.

**Capabilities revealed:** CA-3 (SessionEnd ingest, log.md append, async runner, wiki-bot branch + PR), CA-7 (frontmatter discipline, owner field).

### Journey 2 — New developer onboards to a homelab repo

**Persona:** A future Tom returning after a 3-month break, OR a new collaborator joining the homelab effort.

**Opening:** Open the `homelab-infra` repo. Question: "What does this do, what's the architecture, what's deployed where, what was decided?"

**Rising action:** Read `homelab-infra/README.md` (1 minute) → click `homelab-infra/docs/index.md` → land in Diátaxis-quadrant folders. The Reference quadrant has `docs/reference/generated/` with auto-generated GitNexus Code Wiki output (per-module pages with cross-references). The Explanation quadrant has ADRs. The How-to quadrant has runbooks promoted from operator memory. Tutorials get someone past the bootstrap problem.

**Climax:** ≤15 minutes in, the developer has a working mental model. They check `homelab-playbook/wiki/index.md` for cross-repo context (architecture overview, integration map, current project state). They read 2 ADRs, glance at one runbook, scan the GitNexus-generated module reference for the area they care about.

**Resolution:** They start working productively. Their questions land in the wiki via Journey 1's ingest, growing the corpus.

**Capabilities revealed:** CA-2 (Diátaxis IA, index.md, frontmatter, audience filtering for `dev`), CA-4 (GitNexus reference output), CA-6 (Obsidian or filesystem read; same git tree).

### Journey 3 — PM/PO checks project status via AzDO Wiki

**Persona:** PM working on a Sparkle-CPS-shaped project, AAD-authenticated to the AzDO tenant.

**Opening:** PM opens AzDO, navigates to the project's Wiki tab. Wants project status, current sprint, recent decisions — without operator jargon.

**Rising action:** PM browses pages mirrored from the project's `homelab-playbook-equivalent/wiki/` via the `wiki-publish-audience` skill targeting `audience: pm`. The skill stripped operator-only sections, soft-rewrote technical jargon, and injected a PM-friendly intro. Pages render with AzDO's native CommonMark + mermaid support; the TOC is auto-generated.

**Climax:** PM finds answers without asking the operator. Reads "PVE replication topology" as a 2-paragraph plain-English summary; the original ADR is linked but doesn't blast the PM with shell commands and Tailscale ACLs.

**Resolution:** PM closes the tab, has the right mental model for the next standup. No operator interrupt; no leak of internal hostnames.

**Capabilities revealed:** CA-5 (audience filter, tone rewrite, LLM transform pass), CA-6 (AzDO mirror to `wikiMaster` branch).

### Journey 4 — Customer reads the public-facing wiki

**Persona:** A customer (or future paying user) of a homelab-derived service.

**Opening:** Customer is told "see our docs at docs.example.tail-net.ts.net" (Tailscale-served Quartz site for the homelab) or the public AzDO Wiki URL for an AzDO project.

**Rising action:** Reads tutorials and how-tos written in plain language. No operator jargon, no internal hostnames, no Tailscale ACL references — those were stripped by `wiki-publish-audience` with `audience: customer` filter. Site has search (Quartz FlexSearch or AzDO native), graph view (Quartz only), and a clean Diátaxis IA.

**Climax:** Customer accomplishes their goal (signs up, integrates, troubleshoots) without contacting support.

**Resolution:** Customer doesn't see the operator wiki at all. Internal context stays internal; the public surface is exactly the public surface.

**Capabilities revealed:** CA-5 (audience tuning), CA-6 (Quartz build, Tailscale-served deploy or AzDO public wiki), CA-7 (redaction discipline via frontmatter).

### Journey 5 — AI agent (Cursor) consumes docs via MCP

**Persona:** Tom switches to Cursor for a frontend task in a homelab repo. Cursor needs project context.

**Opening:** Cursor session starts. AGENTS.md is the canonical schema (Anthropic-endorsed Astral pattern means `CLAUDE.md → @AGENTS.md`). Cursor reads `.cursor/rules/*.mdc` natively (manual symlinks for Tom) plus AGENTS.md.

**Rising action:** Tom asks Cursor about a feature. Cursor's `@docs` context provider hits the registered MCP doc server (`arabold/docs-mcp-server`), which serves `homelab-playbook/wiki/` and per-repo `/docs/`. Same markdown, same Diátaxis structure, same frontmatter.

**Climax:** Cursor's response cites pages via the `sources:` frontmatter. The `llms.txt` at site root helped the MCP server prioritize the right pages.

**Resolution:** Tom gets the same documentation quality from Cursor as from Claude Code. Zero re-authoring.

**Capabilities revealed:** CA-6 (MCP doc server, llms.txt), CA-8 (AGENTS.md cross-tool).

### Journey 6 — Operator runs scheduled weekly lint, finds drift

**Persona:** Tom on a quiet Sunday morning, ntfy pings.

**Opening:** Phone notifies: "Weekly doc lint: 3 stale pages, 1 contradiction, 7 orphans." Notification deep-links to the lint report on the homelab CT.

**Rising action:** Tom opens the report. Sees one page that was last_ingested 60 days ago but its `sources:` cite a code path GitNexus says no longer exists. One contradiction: ADR-007 says "Graphiti is authoritative" but a `runbooks/` page says "use auto-memory for decisions" (drift!). Seven orphans: pages no other page links to.

**Climax:** Tom fixes the contradiction in 5 minutes (updates the runbook to defer to ADR-007). For the stale page, runs `/wiki regen` which triggers a GitNexus wiki regen + LLM-Wiki ingest. Orphans get triaged: 4 are still relevant but need inbound links, 3 are obsolete and get archived.

**Resolution:** Wiki health restored. Total operator time: 30 minutes per week. Without the lint, this would have been silent drift accumulating for months.

**Capabilities revealed:** CA-7 (lint stack, citation checker, contradiction detection, orphan check, ntfy alert).

## Domain-Specific Requirements

The domain is **devops-ai-assisted-development** at medium complexity. There are no regulated-data concerns (no PHI, PII at scale, payments, or compliance frameworks like HIPAA/PCI-DSS apply to the homelab itself). However, the domain carries non-obvious constraints that shape the design.

### Compliance & Regulatory

- **Operator-secret leakage prevention**: the customer wiki must never expose secrets, credential paths, internal hostnames, Tailscale ACL details, or AAD tenant identifiers. The audience filter and `permissions.deny` enforcement (settings.json) are the layered defenses. *Why this matters: a leak of internal hostnames or tailscale identifiers is reconnaissance fuel; even though the homelab is non-commercial, Sparkle-CPS-derived projects are commercial and the same skill must work there.*
- **License hygiene**: GitNexus is PolyForm-Noncommercial-1.0.0. License-clean for the homelab. Sparkle-CPS use of GitNexus (commercial) requires either a commercial license or excluding GitNexus Code Wiki output from the Sparkle-CPS pipeline. The PRD's MVP keeps GitNexus on homelab only.

### Technical Constraints

- **Markdown-in-git is the single source of truth (ADR-002, locked)**. No DB-backed wiki engine. Mirrors are one-way only.
- **Cross-tool agent-instruction portability**: AGENTS.md must be readable by Codex (native), Claude Code (via `@AGENTS.md` import), Cursor (manual symlink), Continue (config opt-in), and Aider (manual `--read`). The Astral pattern is the cross-tool answer Anthropic endorses verbatim.
- **Hook discipline**: every Claude Code hook script must follow the existing `~/.claude/hooks/gitnexus/` pattern — `set +e`, fail-silent on errors, ≤3-second timeout, never propagate errors back to Claude. Anti-pattern lessons learned: a `bmad-update-project-docs` skill that hangs Claude breaks every session.
- **Async runners for LLM-cost work**: SessionEnd ingest must not block Claude Code shutdown. The hook queues; a separate cron-driven runner consumes.

### Integration Requirements

- **GitNexus MCP** at `127.0.0.1:4747/api/mcp` — runs in container `gitnexus`. CLI binary at `/app/gitnexus/dist/cli/index.js`. Existing `analyze --skip-agents-md` flag stays on (don't let GitNexus mutate the schema files).
- **Graphiti MCP** at `127.0.0.1:8000/mcp` — episodes/facts/entities. Cited via `graphiti://episode/<uuid>` URIs in wiki frontmatter.
- **AzDO REST + git push** for projects with AzDO tenants. The `wiki-publish-audience` skill uses existing AAD credentials from operator's environment.
- **Tailscale-served Quartz** for non-AzDO public surfaces — defaults to Tailscale-only per existing operator policy (phone-notifications-tailscale memory).
- **Existing crash-notifier ntfy** — reused for mirror-pipeline failures and weekly lint reports. Topic: `docs-lint`.

### Risk Mitigations

- **Hallucinated synthesis** (LLM-Wiki failure mode): citation-check lint pass, monthly review of `owner: llm` pages, frontmatter `contradictions:` populated by lint.
- **Drift across surfaces**: one-way mirrors only, enforced by CI; no consumer is ever a writer.
- **GitNexus single-maintainer abandonment**: pin Docker image SHA, archive image locally, OSS license keeps current version usable indefinitely.
- **LLM cost explosion on regen**: gate `gitnexus wiki` regen on graph-delta threshold (>N changed symbols); track $ in monthly review.
- **Schema split breaks Cursor/Codex**: test each tool post-migration; keep Pass 1 (stub redirect) reversible for rollback.

## Innovation & Novel Patterns

### Detected Innovation Areas

Three genuinely novel patterns combine in this product, none individually breakthrough but together unusual:

1. **Karpathy's LLM-Wiki applied to a multi-audience operator wiki.** Karpathy's gist is framed for personal knowledge bases — single curator, operator-as-reader, LLM-owns-wiki. This product extends the pattern to mixed audiences via the `wiki-publish-audience` synthesis skill. The operator wiki is Karpathy-shaped (LLM maintains, human curates); the customer wiki is a derived view, not an authored surface. **No published implementation does this combination today** (verified via the dedicated landscape research §C.6/§C.7 of `technical-codebase-docs-system-research-2026-04-27.md`).
2. **Graph-grounded reference docs + LLM-synthesized narrative docs in the same Diátaxis layout.** GitNexus Code Wiki produces the Reference quadrant from the live AST/community-detection graph; LLM-Wiki ingest produces Tutorials/How-to/Explanation. Cross-references between quadrants resolve through the `sources:` frontmatter (`graphiti://`, `file://<path>:<lo>-<hi>`, `bmad://`, `external://`). Each document type's failure mode is distinct and bounded; the lint pass cross-checks both.
3. **Cross-tool agent-schema delivery via Astral stub-redirect, with Cline-style topic split for organizational PR review-ability** — corrected for the actual Anthropic precedence model where `@`-imports are eager (so the topic split organizes content, doesn't lazy-load). True lazy-load lives in Skills + slash commands + UserPromptSubmit hooks. This combination is documented across multiple Anthropic doc pages but rarely combined this explicitly in published OSS exemplars.

### Market Context & Competitive Landscape

- **Hosted "AI doc" platforms** (Mintlify, GitBook AI) — focus on AI-augmented authoring, not LLM-native consumption. Vendor lock-in, hosted-only, expensive at scale. Unaligned with the homelab's MD-in-git constraint.
- **Karpathy LLM-Wiki implementations** in the wild (`Pratiyush/llm-wiki` 177★, `Astro-Han/karpathy-llm-wiki` 644★, `kfchou/wiki-skills` ~100★) — all single-curator personal-KB shape. None implement multi-audience synthesis.
- **GitNexus** — the only OSS code-graph → docs pipeline with both `wiki` subcommand and skill generation. Single-maintainer risk acknowledged.
- **`forrestchang/andrej-karpathy-skills`** at 94k stars is misleadingly named — it's a 67-line single-rule-file based on Karpathy's coding-pitfalls tweet, not his LLM-Wiki gist. Brand-amplified, do not use as model.

### Validation Approach

- **Week 1 acceptance test** — schema refactor: AGENTS.md ≤120 lines, all `/docs/` files have frontmatter, `obsidian-git` plugin syncs operator vault.
- **Week 2 acceptance test** — hooks: SessionEnd hook fires (queue entry written), PostToolUse logs landings, weekly lint cron emits ntfy.
- **Week 3 acceptance test** — GitNexus wiki output across all three repos (`homelab-infra`, `homelab-apps`, `homelab-playbook`) is human-readable and not embarrassing; manually compare to existing `architecture-*.md` baselines from BMAD's prior output. **If quality is poor on a repo, that repo's reference quadrant falls back to human-authored; GitNexus stays on for the others.**
- **Week 4 acceptance test** — `wiki-publish-audience` produces a customer wiki that passes a "would I show this to a paying customer?" review by Tom. Iterate filter rules in `references/<audience>-tone.md`.
- **30-day acceptance test** — count operator-hours spent on docs vs baseline; expect ≥50% reduction.
- **90-day acceptance test** — customer wiki has zero leakage incidents.

### Risk Mitigation

- **If LLM-Wiki produces too many false-positive ingests** (low-signal "decisions" promoted to ADRs): tighten the SessionEnd hook's filter rules, raise the LLM confidence threshold, or move ingest to human-confirmed only via slash command `/wiki ingest`.
- **If GitNexus output quality is poor**: keep the `analyze --skip-agents-md` flag (already on), skip `wiki` regen entirely, hand-author the Reference quadrant for now, revisit when GitNexus matures.
- **If `wiki-publish-audience` skill produces uneven tone**: split into multi-skill pack per `kfchou/wiki-skills` pattern (`wiki-filter-audience` + `wiki-tone-rewrite` + targeted skills per audience).
- **If schema split breaks cross-tool**: rollback to single-file AGENTS.md (Pass 2 reverse), keep stub redirect (Pass 1).

## Developer-Infrastructure Specific Requirements

### Project-Type Overview

This is operator-scale developer infrastructure: a documentation-and-instruction-architecture system intended for the homelab's three repos (homelab-infra, homelab-apps, homelab-playbook) and replicable to derived projects (Sparkle-CPS, Quant-Trading, AI Dev Container, future). It is not a SaaS product, not a customer-facing application, and not a published OSS package — but the schema portability requirement (cross-tool AGENTS.md) means design choices have to respect external standards even though the operator audience is one person.

### Technical Architecture Considerations

- **Shell-script-first hooks**, matching the existing `~/.claude/hooks/gitnexus/{pre,post}.sh` pattern. Bash + minimal jq + curl. No Python except where it pays for itself (citation-check, frontmatter validation, audience filter).
- **Container-resident services where they already exist** — GitNexus and Graphiti are already containerized; no new long-running services. The async ingest runner is a cron job, not a daemon.
- **Hook payloads via stdin JSON** — Claude Code passes structured payloads on hook stdin. Existing hooks read and ignore them safely; new hooks parse selectively.
- **CI as one-way mirror only** — Azure Pipelines (AzDO) and GitHub Actions (Quartz) read `main`, write to derived surfaces. No PR-from-CI back to source.
- **MCP server registration is per-tool config**, not a system-wide service. Each tool's config (Cursor `~/.cursor/...`, Continue `.continue/`) opts in to the same `docs-mcp-server` instance.

### Implementation Considerations

- **Migration must be reversible per pass.** Pass 1 of the schema refactor is `mv CLAUDE.md AGENTS.md && printf '@AGENTS.md\n' > CLAUDE.md` — one-line rollback.
- **No big-bang rewrites.** Existing `bmad-document-project` and `bmad-update-project-docs` skills continue to work during and after migration; the new system layers on, doesn't replace.
- **Frontmatter discipline must be enforced from Day 1.** Without it, the lint pass and the audience filter both lose ground truth. Pre-commit ajv hook is the gate.
- **Schema audit is the highest-risk single step** — cutting the existing 250+ line root CLAUDE.md to ≤120 lines while not breaking active sessions. Mitigation: do it in a feature branch, run a session against the new file, verify Claude Code behavior matches expectations before merging.
- **GitNexus wiki targets the entire workspace directly** (all three repos: `homelab-infra`, `homelab-apps`, `homelab-playbook`). The end goal is full-workspace coverage; per-repo opt-in adds incidental complexity without changing the operational shape.

## Project Scoping & Phased Development

### MVP Strategy & Philosophy

**MVP Approach: problem-solving MVP** — the maintenance loop is the binding problem. Solve "who maintains the docs" first; defer multi-audience publishing (Growth) and multi-tool consumption (Vision).

**Resource Requirements:** one operator (Tom) at evening cadence, ~30–40 hours over 4 weeks. No additional headcount.

### MVP Feature Set (Phase 1)

**Core User Journeys Supported:**
- Journey 1 (operator captures decision via SessionEnd ingest)
- Journey 2 (developer onboards via Diátaxis structure)
- Journey 6 (operator runs weekly lint)

**Must-Have Capabilities (mapped to FRs in next section):**
- CA-1 Schema Refactor (full)
- CA-2 Wiki SoT (full — frontmatter + log.md + index.md + Diátaxis quadrants)
- CA-3 Maintenance Loop (full — SessionEnd ingest, log append, async runner)
- CA-4 Reference Auto-gen (full — all three repos: `homelab-infra`, `homelab-apps`, `homelab-playbook`)
- CA-7 Drift & Quality (full — lint stack, citation check, ntfy report)
- CA-8 Cross-tool Portability (Pass 1 only — stub redirect; deeper validation in Growth)

### Post-MVP Features

**Phase 2 (Growth):**
- CA-5 Audience Publish (full — `wiki-publish-audience` skill, both AzDO and workspace `/wiki/` targets)
- CA-6 Multi-surface Consumption (full — AzDO mirror, MCP doc server, llms.txt, Quartz)
- CA-4 Reference Auto-gen extras (CI integration on PR/merge — base regen already in MVP)
- CA-7 GitNexus regen on PR/merge (extended hook)
- Journeys 3, 4, 5 fully supported.

**Phase 3 (Expansion):**
- Cross-project skill portability (Sparkle-CPS, Quant-Trading, AI Dev Container).
- `qmd` integration for at-scale wiki search.
- `graphiti://` URI auto-resolution in wiki rendering.
- `autoresearch:fix` loop applied to the wiki itself.
- Customer-facing version pinning to product release tags.

### Risk Mitigation Strategy

**Technical Risks:**
- Schema-refactor breaks Claude Code session behavior → feature-branch testing, Pass 1 reversibility, Pass 2 deferred until Pass 1 validated.
- GitNexus output quality unknown → start on smallest repo, manual quality review, off-ramp to "skip GitNexus, hand-author" if needed.
- LLM hallucination in synthesized pages → frontmatter `sources:` mandatory, lint cross-check, monthly `owner: llm` review.

**Market Risks:** N/A (operator-internal product).

**Resource Risks:**
- Operator overcommit at evening cadence → MVP is independently useful; Growth and Vision can land any time.
- LLM cost overrun → monthly $ tracking, hard ceiling at €15/month before alarming.

## Functional Requirements

This is the binding capability contract. Every feature in the implementation plan traces to one of these. 32 FRs across 8 capability areas.

### CA-1 Schema Refactor

- **FR1**: Operator can rename existing `CLAUDE.md` to `AGENTS.md` and create a new `CLAUDE.md` containing the single-line `@AGENTS.md` import without breaking any active Claude Code session (Astral stub-redirect pattern, Anthropic-endorsed).
- **FR2**: Operator can split AGENTS.md content into `.claude/rules/<topic>.md` files (general, file-organization, security, testing, docs, concurrency) such that AGENTS.md ends ≤120 lines and total instruction-file content loaded at session start is ≤5,000 tokens.
- **FR3**: Operator can add `paths:` frontmatter to a `.claude/rules/<topic>.md` file and have Claude Code load that rule only when matching files are touched (path-scoped lazy-load, the genuine token-saving mechanism).
- **FR4**: AI agent (Claude Code, Cursor via symlink, Codex native, Continue via config opt-in) can read AGENTS.md as the canonical schema with no per-tool re-authoring of rules content.
- **FR5**: Operator can encode safety-critical rules (e.g., "never read .env") in `settings.json:permissions.deny` for hard enforcement, with the same content optionally restated in AGENTS.md as advisory documentation.

### CA-2 Wiki Source-of-Truth

- **FR6**: Operator can place narrative content in `homelab-playbook/wiki/` organized by Diátaxis quadrants (`tutorials/`, `how-to/`, `reference/`, `explanation/`) with cross-cuts (`adr/`, `glossary/`, `projects/`, `runbooks/`).
- **FR7**: Operator can place per-repo content in `<repo>/docs/` mirroring the same Diátaxis structure for repo-internal concerns.
- **FR8**: Every markdown file in `homelab-playbook/wiki/**` and `<repo>/docs/**` carries the canonical frontmatter spec (title, diataxis, audience, owner, status, last_ingested, last_human_edit, sources, ingest_log, contradictions, tags), enforced by pre-commit ajv validation.
- **FR9**: The pre-commit hook rejects commits where any new or modified `.md` file under wiki/docs paths fails frontmatter schema validation.
- **FR10**: Operator can append entries to `log.md` (in each wiki root) using the prefix-formatted convention (`## [<ISO-date>] <op-type> | <subject>`) for grep-ability via standard unix tools.
- **FR11**: Operator (and AI agent) can read the wiki index via `index.md` at each wiki root, listing every page with one-line summary and category, updated on every ingest.

### CA-3 Maintenance Loop (Karpathy ingest/query/lint)

- **FR12**: When a Claude Code session ends, the SessionEnd hook queues an ingest job in `homelab-playbook/wiki/_meta/ingest-queue.jsonl` without blocking session shutdown (≤30 second budget, fail-silent on errors).
- **FR13**: An async runner (cron or systemd timer, every 15 min) drains the ingest queue, reads session transcripts, identifies decision-making turns, drafts wiki updates on `wiki-bot/<date>-session-<id>` branches, and opens auto-PRs.
- **FR14**: When an Edit/Write/MultiEdit tool call modifies a file under `<repo>/docs/**` or `homelab-playbook/wiki/**`, the PostToolUse hook appends a log.md entry with timestamp, file path, and session ID.
- **FR15**: Operator can invoke a manual ingest via `/wiki ingest <session-id>` slash command without waiting for SessionEnd.
- **FR16**: Operator can promote auto-memory entries (from `~/.claude/projects/<project>/memory/`) into the wiki when content shape matches a runbook (manual review + slash command, NOT automatic).

### CA-4 Reference-Layer Auto-Generation

- **FR17**: Operator can run `gitnexus wiki --review` against any indexed repo and produce per-module markdown documentation grouped by Leiden community detection.
- **FR18**: GitNexus wiki output writes only to `<repo>/docs/reference/generated/`; no other folder is touched (ADR-006 blast-radius bound; verified by pre-commit hook rejecting non-prefix writes by `gitnexus-bot`).
- **FR19**: GitNexus regen fires on weekly cron + on-demand operator invocation + on git PR open + on merge to main (extended `gitnexus/post.sh` with branch + path filter).
- **FR20**: GitNexus `analyze --skill-agents-md` flag remains permanently disabled in the post-commit hook; GitNexus must never mutate `AGENTS.md` or `CLAUDE.md`.

### CA-5 Audience-Tuned Customer Wiki Publish

- **FR21**: Operator can invoke the `wiki-publish-audience` skill with an audience parameter (`customer`, `pm`, `public`) and produce a synthesized wiki targeting the appropriate consumption surface.
- **FR22**: For projects with an Azure DevOps tenant, the skill pushes the synthesized wiki to the AzDO Wiki repo's `wikiMaster` branch via REST + git push using existing AAD credentials.
- **FR23**: For projects without an Azure DevOps tenant, the skill writes the synthesized wiki to `<workspace>/wiki/` at workspace root (NOT inside `homelab-playbook/`).
- **FR24**: The audience filter strips pages where frontmatter `audience:` does not include the target audience, redacts operator-only sections, and applies a configurable LLM tone-rewrite per audience.
- **FR25**: Audience configuration lives in `references/<audience>-tone.md` within the skill folder, allowing operator to fine-tune per audience without editing the skill workflow.
- **FR26**: The skill commits its synthesis output with a `wiki-publish: <audience> @ <SHA>` message and updates `_meta/last-sync.json` for provenance.

### CA-6 Multi-Surface Consumption

- **FR27**: An MCP doc server (`arabold/docs-mcp-server` or equivalent) serves `homelab-playbook/wiki/` and `<repo>/docs/` as MCP resources; it is registered in `~/.claude.json` and (manually) in Cursor and Continue configs so all three tools consume the same content.
- **FR28**: A workspace-root `llms.txt` file (AnswerDotAI spec) lists wiki pages organized by Diátaxis quadrant; regenerated on every push to `main`.
- **FR29** (Growth): Optionally, a Quartz v4 build pipeline produces a static site from `homelab-playbook/wiki/` + per-repo `<repo>/docs/`, deployed behind Tailscale on a homelab CT.

### CA-7 Drift Detection & Quality Gates

- **FR30**: A scheduled weekly cron runs the lint stack (markdownlint-cli2 + lychee + Vale + custom citation-checker + orphan-checker) and posts a report to ntfy topic `docs-lint`. Report includes counts of stale pages, broken links, prose violations, broken citations, contradictions, and orphans.
- **FR31**: The citation-checker resolves `file://<path>:<lo>-<hi>` (file exists, line range valid), `bmad://` (file exists in `_bmad-output/`), `external://` (lychee handles), and `graphiti://episode/<uuid>` (deferred MCP call) URIs in `sources:` frontmatter and reports broken references.
- **FR32**: The contradiction-checker compares synthesized pages (`owner: llm`) against their cited sources and flags claims where the synthesized text contradicts the current source content.

### CA-8 Cross-Tool Portability (validation, no new code)

(Covered by FR4 above; no additional FRs — the capability is the cross-tool reach itself, validated by manual sessions in each tool post-migration.)

## Non-Functional Requirements

Only NFR categories that actually matter for this product. Performance, security, and reliability apply; accessibility, scalability, and integration are either N/A or covered under FRs.

### Performance

- **Hook latency**: every Claude Code hook (PreToolUse, PostToolUse, SessionEnd) completes in ≤3 seconds wall-clock. Long-running work goes to an async runner consumed by cron.
- **Schema-file load size at session start**: ≤5,000 tokens combined (CLAUDE.md stub + AGENTS.md + lazy-loaded `.claude/rules/<topic>.md` via `paths:` scoping).
- **Session-end ingest** does not block Claude Code shutdown.
- **AzDO mirror latency**: < 5 minutes from `main` push to mirrored content visible in AzDO Wiki UI.
- **GitNexus wiki regen** for `homelab-playbook` (smallest repo, ~30 modules): < 5 minutes wall-clock at concurrency 3.
- **Customer wiki publish** for the homelab: < 10 minutes wall-clock end-to-end for full repo regen.

### Security

- **Customer wiki must not expose operator-only content**: the audience filter strips frontmatter `audience: [operator]` pages and `<!-- operator-only -->` HTML-comment-fenced blocks. Verified by spot-check on every publish.
- **Secrets must never reach any wiki surface**: pre-commit hook scans for credential patterns (existing tools or simple regex). Frontmatter `sources:` may reference filesystem paths but never inline credentials.
- **`permissions.deny` in `settings.json`** encodes hard fences (no read of `.env`, no write to `/etc`, no destructive git commands without explicit ack). Enforced by Claude Code regardless of CLAUDE.md content.
- **AzDO push credentials** are read from operator's environment (existing AAD setup), never committed.
- **GitNexus PolyForm-NC license**: scope GitNexus output to homelab projects only; do not generate GitNexus wiki output for Sparkle-CPS or any commercial project without separate licensing.

### Reliability

- **Mirror-pipeline failures alert via ntfy** within 5 minutes (reuses existing crash-notifier pattern).
- **Hook silent-fail discipline**: every hook script has `set +e` and exits 0 on any error to prevent breaking Claude Code sessions. Failures are logged to a hook log, not to stderr in the parent.
- **Async runner idempotency**: queue entries are reprocessable. If a runner crashes mid-ingest, the entry stays in `pending` state until next tick.
- **Schema-refactor reversibility**: every migration step is reversible via `git revert` of a single commit. Pass 1 in particular is one-line.
- **Lint cron silent-fail detection**: weekly health-check ntfy includes "lint last ran: <timestamp>". If timestamp is >2 weeks old, alert.

## Implementation Roadmap (carry into Architecture and Epic breakdown)

| Week | Critical Path | Reversibility | Cost |
|---|---|---|---|
| **W1** | Schema Pass 1 + frontmatter on existing 8 docs + log.md init + ajv pre-commit | All git revert | ~3 hrs |
| **W2** | Schema Pass 2 (.claude/rules split) + Diátaxis migration of 8 docs + lint stack install + SessionEnd hook + PostToolUse hook | All disable/revert | ~5–6 hrs |
| **W3** | GitNexus `wiki --review` across all three repos (`homelab-infra`, `homelab-apps`, `homelab-playbook`) + scheduled weekly lint cron + first ntfy report | Stop cron, delete output | ~5–7 hrs + LLM bill (3× single-repo cost) |
| **W4** | (Growth) `wiki-publish-audience` skill skeleton (Anthropic schema) + first customer-wiki publish for homelab + manual quality review | Stop skill, delete output | ~6–8 hrs |
| **W5+** | (Growth) AzDO mirror pipeline + MCP doc server registration + llms.txt generator + GitNexus regen on PR/merge + Quartz build (if customer audience for homelab) | All reversible | ~10–15 hrs |

Total to MVP (W1–W3): ~12–13 hours.
Total to Growth (W1–W5): ~30–40 hours.

## Open Decisions Resolved by Director Synthesis

(All previously open per `technical-codebase-docs-system-research-2026-04-27.md` §6 "Architecture Decisions Locked" + this PRD's director-mode commitments.)

1. **Architecture pick**: C (hybrid).
2. **Customer audience in scope**: yes.
3. **Operator wiki SoT location**: `homelab-playbook/wiki/`.
4. **Customer wiki location**: workspace `/wiki/` for non-AzDO projects; AzDO Wiki repo for AzDO projects.
5. **GitNexus regen cadence**: weekly + on-demand + on PR open + on merge.
6. **Obsidian sync**: `obsidian-git` plugin.
7. **Schema split pattern**: Astral stub-redirect + Cline topic split + path-scoped lazy-load via `paths:` frontmatter (the genuine token-saving mechanism, since `@`-imports are eager).
8. **CLAUDE.md target length**: ≤120 lines (Anthropic published target = 200; aim lower for headroom).
9. **GitNexus wiki coverage**: full workspace from MVP — all three repos (`homelab-infra`, `homelab-apps`, `homelab-playbook`). Per-repo opt-in adds incidental complexity without changing operational shape.
10. **Skill folder convention for `wiki-publish-audience`**: Anthropic canonical `SKILL.md + references/ + scripts/ + assets/`. NOT BMAD's `workflow.md + steps/` (community extension).
11. **Customer-wiki failure mode**: zero leakage of operator-only content over 90 days. Audit on every publish.
12. **LLM cost ceiling**: €10/month soft, €15/month hard; review monthly.

## References

- **Source-of-truth research**: `homelab-playbook/_bmad-output/planning-artifacts/research/technical-codebase-docs-system-research-2026-04-27.md` (2,031 lines, doc-system architecture).
- **Schema research**: `homelab-playbook/_bmad-output/planning-artifacts/research/technical-claude-md-best-practices-2026-04-27.md` (CLAUDE.md/AGENTS.md best practices, Karpathy skills landscape, instruction-precedence mesh).
- **Karpathy LLM-Wiki primary source**: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
- **Anthropic memory doc** (Astral pattern endorsement): https://docs.claude.com/en/docs/claude-code/memory
- **Anthropic skills doc**: https://docs.claude.com/en/docs/claude-code/skills
- **Anthropic best-practices**: https://code.claude.com/docs/en/best-practices
- **Diátaxis spec**: https://diataxis.fr
- **MADR 4.0 (ADR template)**: https://adr.github.io
- **AnswerDotAI llms-txt spec**: https://github.com/AnswerDotAI/llms-txt
- **GitNexus README**: https://github.com/abhigyanpatwari/GitNexus
- **`anthropics/skills` (canonical schema)**: https://github.com/anthropics/skills
- **`kfchou/wiki-skills` (multi-skill pack model)**: https://github.com/kfchou/wiki-skills

---

**PRD Status:** Complete. Director-mode synthesis from two locked research artifacts and six explicit operator decisions. All 11 substantive BMAD steps executed without menu pauses.

**Next Workflows:**
- `bmad-check-implementation-readiness` — validate PRD completeness before architecture work.
- `bmad-create-architecture` — formalize the Architecture C design from §C.5 of doc-system research into a per-product architecture doc at `products/doc-system/architecture.md`.
- `bmad-create-epics-and-stories` — break the FRs into epics (one per CA-N capability area) and stories.
- Or: skip architecture/epics and start executing W1 of §Implementation Roadmap directly (schema refactor Pass 1 + frontmatter is ~2 hrs, fully reversible).
