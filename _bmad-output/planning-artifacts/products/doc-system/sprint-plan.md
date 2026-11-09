---
type: sprint-plan
product: doc-system
version: 1.0.0-draft
status: active
date: 2026-04-27
prd_ref: prd.md
arch_ref: architecture.md
epics_ref: epics.md
director_mode: true
---

# Codebase Documentation System — Sprint Plan

## 1. Sprint Overview

| Sprint | Weeks | Goal (1 sentence) | Stories | Effort | Epic coverage |
|---|---|---|---|---|---|
| **Sprint 1** | W1–W2 | Foundation: schema refactor + wiki SoT structure + lint stack + cross-tool baseline. **MVP-critical.** | 19 | ~10–12 hrs | E1 (6) + E2 (7) + E7 partial (4) + E8 partial (2) |
| **Sprint 2** | W3 | Maintenance loop wired + GitNexus reference auto-gen across all 3 repos + citation/orphan checkers. **Completes MVP.** | 17 | ~10–12 hrs | E3 (6) + E4 (7) + E7 ext (3) + E8 (1) |
| **Sprint 3** | W4 | Audience-tuned customer-wiki publish skill + contradiction checker + health alarm. **First Growth value.** | 10 | ~8–10 hrs | E5 (8) + E7 (2) |
| **Sprint 4** | W5+ | Multi-surface consumption: MCP doc server, llms.txt, AzDO mirror, Quartz site. **Full audience reach.** | 9 | ~10–15 hrs | E6 (7) + E8 (2) |

**Total: 55 stories, ~38–49 hrs of operator effort.** MVP exit at Sprint 2 = 36 stories, ~20–24 hrs.

## 2. Sprint 1 — Foundation (W1–W2)

### Sprint Goal

The homelab root agent-instruction surface is refactored to Anthropic-endorsed Astral + Cline patterns (≤120-line AGENTS.md), the wiki source-of-truth structure is in place with frontmatter compliance and Karpathy primitives (`log.md`, `index.md`), and the lint stack is installed and configured. By end of Sprint 1, the operator has a leaner, cross-tool-portable agent schema and a wiki structure ready to receive content.

### Sprint 1 Story Backlog (in execution order)

| # | Story ID | Title | FR | Hours | Status |
|---|---|---|---|---|---|
| 1 | **E1.S1** | Pass 1: stub redirect (CLAUDE.md → @AGENTS.md) | FR1 | 0.5 | pending |
| 2 | **E1.S2** | Audit cuts on AGENTS.md (≤120 lines target) | FR2 | 1.5 | pending |
| 3 | **E1.S3** | Pass 2: split into `.claude/rules/<topic>.md` | FR2 | 2.0 | pending |
| 4 | **E1.S4** | Path-scoped rules with `paths:` frontmatter | FR3 | 1.0 | pending |
| 5 | **E1.S5** | settings.json hard fences via `permissions.deny` | FR5 | 0.5 | pending |
| 6 | **E1.S6** | Cross-tool validation (Cursor + Codex symlink) | FR4 | 1.0 | pending |
| 7 | **E2.S1** | Wiki structure (Diátaxis layout) | FR6 | 0.5 | pending |
| 8 | **E2.S2** | Per-repo `/docs/` Diátaxis migration | FR7 | 1.0 | pending |
| 9 | **E2.S3** | Frontmatter spec (JSON Schema) | FR8 | 0.5 | pending |
| 10 | **E2.S4** | Apply frontmatter to 8 existing BMAD docs | FR8 | 1.0 | pending |
| 11 | **E2.S5** | ajv pre-commit hook | FR9 | 0.5 | pending |
| 12 | **E2.S6** | Initialize log.md + prefix convention | FR10 | 0.25 | pending |
| 13 | **E2.S7** | Initialize index.md + content catalog | FR11 | 0.5 | pending |
| 14 | **E7.S1** | Install lint binaries (markdownlint, lychee, Vale) | FR30 | 0.5 | pending |
| 15 | **E7.S2** | markdownlint config | FR30 | 0.25 | pending |
| 16 | **E7.S3** | lychee config | FR30 | 0.25 | pending |
| 17 | **E7.S4** | Vale config | FR30 | 0.5 | pending |
| 18 | **E8.S1** | Cursor session test (read AGENTS.md) | FR4 | 0.5 | pending |
| 19 | **E8.S2** | Codex CLI session test (AGENTS.md native) | FR4 | 0.5 | pending |

**Sprint 1 effort total: ~12.75 hrs.**

### Sprint 1 Exit Criteria

- AGENTS.md final length ≤120 lines.
- Total `.claude/rules/<topic>.md` content ≤500 lines.
- 100% frontmatter compliance on `homelab-playbook/wiki/**/*.md` and `<repo>/docs/**/*.md`.
- ajv pre-commit hook rejects invalid frontmatter (warning mode for first month).
- `log.md` and `index.md` initialized with seed content.
- Lint binaries installed and configured.
- Cursor + Codex sessions confirmed reading AGENTS.md.

### Sprint 1 Risks

- **Schema-refactor breaks active sessions** (mitigation: feature branch, manual probe before merge, Pass 1 reversible in one git commit).
- **Pre-commit hook is too aggressive** (mitigation: warning mode for first month before hard-fail).
- **Cursor/Codex behavior diverges from Claude Code** (mitigation: E8.S1–S2 explicitly verify; per-tool fallbacks in E8 epic).

## 3. Sprint 2 — Maintenance Loop + Reference (W3)

### Sprint Goal

The Karpathy ingest/log loop is wired to Claude Code's hook lifecycle (SessionEnd ingest, PostToolUse log append, async runner producing wiki-bot PRs). GitNexus Code Wiki produces auto-generated reference docs across all three workspace repos with cadence weekly + on-demand + on PR/merge. Citation and orphan checkers join the lint stack. By end of Sprint 2, the operator's wiki is genuinely self-maintaining.

### Sprint 2 Story Backlog

| # | Story ID | Title | FR | Hours |
|---|---|---|---|---|
| 1 | **E3.S1** | SessionEnd hook | FR12 | 1.0 |
| 2 | **E3.S2** | PostToolUse log hook | FR14 | 1.0 |
| 3 | **E3.S3** | Settings.json hook wiring | FR12, FR14 | 0.5 |
| 4 | **E3.S4** | Async ingest runner (cron 15min) | FR13 | 2.0 |
| 5 | **E3.S5** | Manual ingest slash command | FR15 | 0.5 |
| 6 | **E3.S6** | Auto-memory promotion slash command | FR16 | 0.5 |
| 7 | **E4.S1** | GitNexus wiki provider config | (FR17 prep) | 0.25 |
| 8 | **E4.S2** | First regen `--review` across 3 repos | FR17 | 1.5 |
| 9 | **E4.S3** | Output destination + blast-radius bound | FR18 | 1.0 |
| 10 | **E4.S4** | Weekly regen cron | FR19 | 0.5 |
| 11 | **E4.S5** | On PR + on merge regen hook extension | FR19 | 1.0 |
| 12 | **E4.S6** | Verify --skip-agents-md permanently on | FR20 | 0.25 |
| 13 | **E4.S7** | Workspace-wide quality review | (E4 acceptance) | 1.0 |
| 14 | **E7.S5** | check-citations.py | FR31 | 1.0 |
| 15 | **E7.S6** | check-orphans.py | FR30 | 0.5 |
| 16 | **E7.S7** | Weekly lint cron + ntfy integration | FR30 | 0.5 |
| 17 | **E8.S3** | Continue session test | FR4 | 0.5 |

**Sprint 2 effort total: ~12.5 hrs.**

### Sprint 2 Exit Criteria

- A test session produces an ingest queue entry within 30s of session end.
- The async runner drains queue, opens at least one wiki-bot PR with proper frontmatter.
- GitNexus output exists in all three repos at `/docs/reference/generated/` and nowhere else.
- Pre-commit hook rejects out-of-prefix writes by `gitnexus-bot`.
- Weekly regen cron is enabled.
- Weekly lint produces a `lint-<date>.md` report and a ntfy push.
- Continue session reads AGENTS.md.

### Sprint 2 Risks

- **GitNexus output quality is poor** for one or more repos (mitigation: per-repo off-ramp documented in E4.S7).
- **LLM ingest cost runs hot** on first month (mitigation: monitor billing, gate on confidence threshold, add `/wiki ingest` manual override).
- **Async runner crashes mid-ingest** (mitigation: idempotent queue states, lint detects gaps).

## 4. Sprint 3 — Audience-Tuned Customer Wiki Publish (W4)

### Sprint Goal

The `wiki-publish-audience` skill is installed using Anthropic's canonical schema (`SKILL.md + references/ + scripts/ + assets/`). Operator can run `/wiki publish customer` and produce a synthesized customer-tuned wiki at workspace `/wiki/` (homelab) with zero leakage of operator-only content. AzDO push capability is dry-run tested. Contradiction checker joins the lint stack. By end of Sprint 3, the homelab has a working customer-facing wiki surface.

### Sprint 3 Story Backlog

| # | Story ID | Title | FR | Hours |
|---|---|---|---|---|
| 1 | **E5.S1** | Skill folder scaffold | FR21 | 0.5 |
| 2 | **E5.S2** | Audience filter (`filter-by-audience.py`) | FR24 | 1.5 |
| 3 | **E5.S3** | Per-audience tone configs | FR25 | 1.0 |
| 4 | **E5.S4** | Tone-rewrite LLM pass (`tone-rewrite.py`) | FR21, FR24 | 1.5 |
| 5 | **E5.S5** | Workspace `/wiki/` target | FR23, FR26 | 0.5 |
| 6 | **E5.S6** | AzDO Wiki target | FR22, FR26 | 1.5 |
| 7 | **E5.S7** | Auto-detect target (AzDO vs workspace) | FR22, FR23 | 0.5 |
| 8 | **E5.S8** | First customer-wiki publish for homelab | (E5 acceptance) | 1.5 |
| 9 | **E7.S8** | check-contradictions.py | FR32 | 1.5 |
| 10 | **E7.S9** | Health-check ntfy (lint last ran) | (E7 reliability) | 0.25 |

**Sprint 3 effort total: ~10.25 hrs.**

### Sprint 3 Exit Criteria

- Skill installed and discoverable via Claude Code.
- Audience filter strips operator-only pages and HTML-comment-fenced blocks.
- Workspace `/wiki/` populated with customer-tuned content for the homelab.
- Manual zero-leakage audit passes (no secrets, internal hostnames, Tailscale ACLs in published content).
- Contradiction checker catches at least one synthetic test case.
- Health-check ntfy alarms on stale lint timestamp.

### Sprint 3 Risks

- **Audience tone is uneven across pages** (mitigation: split skill into multi-skill pack per `kfchou/wiki-skills` model).
- **Operator-content leakage** via misclassified `audience:` frontmatter (mitigation: pre-publish scan for credential patterns, manual audit of every customer-publish output for first 90 days).
- **AzDO push auth fails** in dry-run (mitigation: defer AzDO target until Sparkle-CPS-shaped project is in scope; homelab uses workspace `/wiki/` only).

## 5. Sprint 4 — Multi-Surface Consumption (W5+, Growth)

### Sprint Goal

The wiki becomes consumable from every audience's native surface: MCP doc server feeds Cursor + Continue + Claude Code, `llms.txt` exposes the wiki to external LLM crawlers, AzDO mirror pipeline serves PM/PO/devs from `wikiMaster` branch, and (optional) Quartz v4 produces a Tailscale-served public site for customers. By end of Sprint 4, every audience has a native consumption path from a single MD source-of-truth.

### Sprint 4 Story Backlog

| # | Story ID | Title | FR | Hours |
|---|---|---|---|---|
| 1 | **E6.S1** | MCP doc server registration | FR27 | 1.0 |
| 2 | **E6.S2** | Cross-tool MCP registration (Cursor, Continue) | FR27 | 1.0 |
| 3 | **E6.S3** | llms.txt generator | FR28 | 1.5 |
| 4 | **E6.S4** | llms.txt regen on push | FR28 | 0.5 |
| 5 | **E6.S5** | AzDO Wiki mirror pipeline | FR22-mirror | 2.5 |
| 6 | **E6.S6** | Quartz build (optional) | FR29 | 3.0 |
| 7 | **E6.S7** | Tailscale-served deploy (homelab CT) | FR29 | 2.0 |
| 8 | **E8.S4** | Aider session test (optional) | FR4 | 0.5 |
| 9 | **E8.S5** | Multi-tool MCP doc-server test | FR27 | 0.5 |

**Sprint 4 effort total: ~12.5 hrs.**

### Sprint 4 Exit Criteria

- Cursor + Continue + Claude Code all read the same wiki via MCP.
- `llms.txt` validates against AnswerDotAI spec.
- AzDO Wiki UI shows mirrored content within 5 min of `main` push.
- (Optional) Quartz site reachable via Tailscale.

### Sprint 4 Risks

- **MCP server abandoned** before Sprint 4 (mitigation: trivial to fork or replace with 100-line custom server).
- **Quartz build complexity** for first-time setup (mitigation: optional epic; can land any time, even Sprint 5).

## 6. Per-Story Pipeline (executed by Director)

Two pipeline variants based on story size:

### 6.1 Standard pipeline (>0.5 hr stories — 4 stages, 4 agents, **Stage 3 ∥ Stage 4 parallel**)

| Stage | Agent type | Output | Parallel? |
|---|---|---|---|
| **1. Create Story** | planner / specification | `stories/sprint-N/<EPIC>.<STORY>.md` with INVEST AC | sequential |
| **2. Dev Story** | sparc-coder / coder | Implementation (code, config, file changes) | sequential, depends on 1 |
| **3. Code Review** | reviewer / code-analyzer | Code-correctness review report | **parallel with 4** |
| **4. Adversarial Review** | reviewer (cynical mode) | Cynical findings; semantic-correctness, hidden risks | **parallel with 3** |

**Why parallel:** confirmed in E1.S2 retrospective — Stage 3 (code-correctness) and Stage 4 (semantic-correctness/cynical) are orthogonal concerns. Running them sequentially anchors the cynical pass on the code-review verdict; running them in parallel keeps Stage 4 blind and earns more value. Wall-clock per standard story drops from 4× to ~3× (Create → Dev → [Review ∥ Adversarial]).

### 6.2 Trivial pipeline (≤0.5 hr stories — 3 stages, 3 agents)

| Stage | Agent type | Output |
|---|---|---|
| **1. Create Story** | planner / specification | `stories/sprint-N/<EPIC>.<STORY>.md` with INVEST AC |
| **2. Dev Story** | sparc-coder / coder | Implementation |
| **3. Combined Review** | reviewer (code-review + cynical mode in one) | Combined review report with both code-quality findings and adversarial concerns |

The trivial pipeline applies to stories with `estimated_hours: ≤0.5`. Saves ~25% agent runs across the program.

### 6.3 Stories assigned to trivial vs standard pipeline

**Trivial pipeline (≤0.5 hr):** E1.S1, E1.S5, E2.S1, E2.S3, E2.S5, E2.S6, E2.S7, E7.S1, E7.S2, E7.S3, E7.S6, E7.S7, E7.S9, E8.S1, E8.S2, E8.S3, E8.S4, E8.S5, E3.S3, E3.S5, E3.S6, E4.S1, E4.S4, E4.S6, E5.S1, E5.S5, E5.S7, E6.S4 → 28 stories × 3 = **84 runs**

**Standard pipeline (>0.5 hr):** E1.S2, E1.S3, E1.S4, E1.S6, E2.S2, E2.S4, E7.S4, E3.S1, E3.S2, E3.S4, E4.S2, E4.S3, E4.S5, E4.S7, E7.S5, E7.S8, E5.S2, E5.S3, E5.S4, E5.S6, E5.S8, E6.S1, E6.S2, E6.S3, E6.S5, E6.S6, E6.S7 → 27 stories × 4 = **108 runs**

**Total agent runs: 192 (down from 220).**

Each story passes through its pipeline before the next story begins (within an epic where stories share files) or in parallel where independent (e.g., E7 lint binary install is independent of E1 schema work).

## 7. Status Tracking

Story status updates live in this file. Per-story details land in `stories/sprint-N/<EPIC>.<STORY>.md`. Sprint exit triggers the next sprint or a retrospective.

## 8. References

- PRD: `prd.md`
- Architecture: `architecture.md`
- Epics: `epics.md`
- Doc-system research: `../../research/technical-codebase-docs-system-research-2026-04-27.md`
- Schema research: `../../research/technical-claude-md-best-practices-2026-04-27.md`
