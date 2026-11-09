---
type: epics
product: doc-system
version: 1.0.0-draft
status: draft
date: 2026-04-27
brief_ref: ../doc-system/prd.md
prd_ref: prd.md
arch_ref: architecture.md
director_mode: true
---

# Codebase Documentation System — Epic Plan

This artifact decomposes delivery into **8 epics aligned to the 8 capability areas** (CA-1 through CA-8) defined in the PRD. Story-level INVEST acceptance criteria are derived from PRD FRs and architecture component contracts. The epic map respects the PRD's 4-week MVP + Growth phasing.

## 1. Epic Map (one-page overview)

| Epic ID | Capability Area | Name | Sprint | Dependencies | Exit Criteria summary | FR coverage |
|---|---|---|---|---|---|---|
| **E1** | CA-1 | Schema Refactor | S1 | None (first epic) | AGENTS.md ≤120 lines + `.claude/rules/<topic>.md` split + verified Claude Code session reads correctly | 5 (FR1–5) |
| **E2** | CA-2 | Wiki Source-of-Truth Foundation | S1 | E1 (rules reference docs.md) | Frontmatter on all 8 existing `/docs/` files + `homelab-playbook/wiki/` structure with `index.md` + `log.md` + Diátaxis quadrants + ajv pre-commit gate live | 6 (FR6–11) |
| **E3** | CA-3 | Maintenance Loop (Karpathy ingest/log) | S2 | E1, E2 (frontmatter is hard dep) | SessionEnd hook + PostToolUse log hook + async ingest runner producing wiki-bot PRs | 5 (FR12–16) |
| **E4** | CA-4 | Reference Auto-Generation (GitNexus) | S2 | E2 (frontmatter spec) | `gitnexus wiki` regen across all 3 repos with output bounded to `/docs/reference/generated/`; weekly + on-demand + on PR/merge cadence | 4 (FR17–20) |
| **E5** | CA-5 | Audience-Tuned Customer Wiki Publish | S3 | E2 (frontmatter audience field), E1 (skill registration) | `wiki-publish-audience` skill installed using Anthropic canonical schema; produces customer wiki for homelab (workspace `/wiki/`) and AzDO Wiki for AzDO projects | 6 (FR21–26) |
| **E6** | CA-6 | Multi-Surface Consumption | S4 | E2 (sources), E5 (audience publish) | MCP doc server + llms.txt + AzDO mirror pipeline + (optional) Quartz site | 3 (FR27–29) |
| **E7** | CA-7 | Drift Detection & Quality Gates | S1 (lint) + S2 (citation) | E2 (frontmatter); CA-7 spans sprints | Weekly lint cron live + ntfy reports + citation-checker + orphan-checker + contradiction-checker | 3 (FR30–32) |
| **E8** | CA-8 | Cross-tool Portability Validation | All sprints | E1 | Manual sessions in Cursor + Codex + Continue verify AGENTS.md is read; no per-tool re-authoring needed | (FR4 cross-cuts; validation only — no separate FRs) |

**Total FR coverage:** 5+6+5+4+6+3+3 = **32 / 32** PRD FRs (full coverage; CA-8 is validation-only and shares FR4 with E1).

**Sprint cadence (per PRD §Implementation Roadmap):**
- **Sprint 1 (W1–W2)**: Foundation. E1 + E2 + E7-partial (lint stack only). MVP-critical path.
- **Sprint 2 (W3)**: Loop + Reference. E3 + E4 + E7-extension (citation checker, GitNexus regen on PR/merge).
- **Sprint 3 (W4)**: Audience Publish. E5 + E7-final (contradiction checker).
- **Sprint 4 (W5+, Growth)**: Multi-surface. E6 + E8 final validation.

---

## 2. Epic 1 — Schema Refactor (CA-1)

**Goal:** Refactor the homelab root agent-instruction surface from the current ~250+ line root `CLAUDE.md` (trending toward the 1,094-line ruflo anti-pattern) to the Anthropic-endorsed Astral stub-redirect + Cline-style topic split + path-scoped lazy-load. Final state: `CLAUDE.md` (1 line `@AGENTS.md`) + `AGENTS.md` (≤120 lines, canonical) + `.claude/rules/<topic>.md` (organized topic files) + `settings.json:permissions.deny` (enforced safety rules).

**Sprint:** 1 (W1–W2)

**Story breakdown:**

| Story | Title | One-line | FR |
|---|---|---|---|
| **E1.S1** | Pass 1: stub redirect | `mv CLAUDE.md AGENTS.md && printf '@AGENTS.md\n' > CLAUDE.md`; commit; verify Claude Code session reads correctly | FR1 |
| **E1.S2** | Audit cuts on AGENTS.md | Strip ruflo product reference, 60+ agent type list, 3-tier model routing, V3 CLI subcommand reference, swarm orchestration intro; target ≤120 lines | FR2 |
| **E1.S3** | Pass 2: topic split + content corrections | Move sections into `.claude/rules/{general,file-organization,security,testing,docs,concurrency}.md`; replace each moved section in AGENTS.md with a 1-line pointer; **also fix 2 findings promoted from E1.S2 adversarial review: (a) cut/replace `npm run build/test/lint` Build & Test block (no package.json at workspace root — homelab is Terraform/Ansible/Docker), (b) cut/replace JS/TS-product Project Architecture bullets (TDD London / event sourcing / DDD bounded contexts) with homelab-specific idioms (per-repo IaC discipline, idempotent runbooks, frontmatter-mandatory docs)**; and (c) replace "swarm" terminology on Behavioral Rules line 10 with "subagents" (residual ruflo terminology) | FR2 |
| **E1.S4** | Path-scoped rules | Add `paths: ['homelab-infra/**']` and `paths: ['homelab-apps/**']` frontmatter to topic-specific rules to enable genuine lazy-load | FR3 |
| **E1.S5** | settings.json hard fences | Move safety-critical rules into `settings.json:permissions.deny` (e.g., `Read(./.env)`, `Read(./.env.*)`, `Bash(rm -rf /*)`) | FR5 |
| **E1.S6** | Cross-tool validation | Manual session in Cursor (with symlink) + Codex CLI; verify AGENTS.md is consumed | FR4 |

**Acceptance criteria for epic:**
- AGENTS.md final length ≤120 lines (verified via `wc -l`).
- Total `.claude/rules/<topic>.md` content ≤500 lines combined.
- A Claude Code session in the homelab root produces correct behavior matching pre-refactor expectations on at least 3 manual probes.
- Cursor and Codex sessions read AGENTS.md without errors.
- Pre-commit hook runs and validates AGENTS.md does not exceed 200 lines.

---

## 3. Epic 2 — Wiki Source-of-Truth Foundation (CA-2)

**Goal:** Establish `homelab-playbook/wiki/` as the operator/internal SoT and per-repo `<repo>/docs/` as the repo-local SoT, both organized by Diátaxis. Apply the canonical frontmatter spec to all existing 8 BMAD-generated docs. Initialize Karpathy primitives (`log.md`, `index.md`). Wire pre-commit ajv frontmatter validation.

**Sprint:** 1 (W1–W2)

**Story breakdown:**

| Story | Title | One-line | FR |
|---|---|---|---|
| **E2.S1** | Wiki structure | Create `homelab-playbook/wiki/` Diátaxis layout: `tutorials/`, `how-to/`, `reference/`, `explanation/adr/`, `explanation/architecture/`, `glossary/`, `projects/`, `runbooks/`, `raw/`, `_meta/` | FR6 |
| **E2.S2** | Per-repo `/docs/` Diátaxis migration | Move existing 8 BMAD-generated docs into Diátaxis quadrant folders inside their owning repos | FR7 |
| **E2.S3** | Frontmatter spec | Define `_meta/frontmatter.schema.json` (JSON Schema draft 2020-12) with required `title`, `diataxis`, `audience`, `owner`, `status`, `last_ingested` and optional `last_human_edit`, `sources`, `ingest_log`, `contradictions`, `tags` | FR8 |
| **E2.S4** | Apply frontmatter to existing docs | Add frontmatter to all 8 existing BMAD-generated docs + any handwritten files; tag operator-only sections with `audience: [operator]` | FR8 |
| **E2.S5** | ajv pre-commit gate | Wire `ajv validate` against the schema as a pre-commit hook; soft-fail (warning) for first month, hard-fail thereafter | FR9 |
| **E2.S6** | log.md primitive | Initialize `homelab-playbook/wiki/log.md` with seed entry; document the `## [<ISO-date>] <op-type> | <subject>` prefix convention | FR10 |
| **E2.S7** | index.md primitive | Initialize `homelab-playbook/wiki/index.md` as content-oriented catalog; one line per page with link + summary; update on every ingest | FR11 |

**Acceptance criteria for epic:**
- 100% frontmatter compliance on `homelab-playbook/wiki/**/*.md` and `<repo>/docs/**/*.md` (pre-commit gate).
- `index.md` lists every wiki/docs page with one-line summary.
- `log.md` accepts entries in canonical format and is grep-able (`grep "^## \[" log.md` returns chronological list).
- ajv pre-commit hook rejects frontmatter-invalid commits.
- Diátaxis quadrant folders exist and are populated with at least the 8 existing baseline docs.

---

## 4. Epic 3 — Maintenance Loop (CA-3)

**Goal:** Wire the Karpathy ingest/log loop into Claude Code's hook lifecycle. SessionEnd hook queues ingests; PostToolUse hook appends log.md entries; async runner consumes the queue and produces wiki-bot PRs.

**Sprint:** 2 (W3)

**Story breakdown:**

| Story | Title | One-line | FR |
|---|---|---|---|
| **E3.S1** | SessionEnd hook | `~/.claude/hooks/docs/session-end.sh`: read stdin payload, append queue entry to `homelab-playbook/wiki/_meta/ingest-queue.jsonl`. ≤3s budget, fail-silent | FR12 |
| **E3.S2** | PostToolUse log hook | `~/.claude/hooks/docs/post-tooluse-edit.sh`: matcher `Edit|Write|MultiEdit` on `/docs/**` and `/wiki/**`; append entry to nearest ancestor `log.md` | FR14 |
| **E3.S3** | Settings.json hook wiring | Add hook entries to `~/.claude/settings.json` with proper matchers and timeouts | FR12, FR14 |
| **E3.S4** | Async ingest runner | `~/.claude/hooks/docs/ingest-runner.sh` (cron every 15 min): drain queue, load session transcript, LLM identifies decisions, draft on `wiki-bot/<date>-session-<id>` branch, open auto-PR | FR13 |
| **E3.S5** | Manual ingest slash command | `.claude/commands/wiki-ingest.md`: invoke ingest for a specific session-id without waiting for SessionEnd | FR15 |
| **E3.S6** | Auto-memory promotion slash command | `.claude/commands/wiki-promote-memory.md`: surface auto-memory entries that look like runbooks, prompt operator to promote into wiki | FR16 |

**Acceptance criteria for epic:**
- A test Claude Code session ending produces exactly one `ingest-queue.jsonl` entry.
- An Edit on a `/docs/` file produces exactly one `log.md` entry within 3 seconds.
- The async runner drains queue entries within 15 minutes; produces a draft PR for at least one decision-bearing test session.
- Wiki-bot branches are created with `wiki-bot/` prefix; PRs are auto-opened.
- Hook logs show no propagated errors back to Claude Code (sessions never break).

---

## 5. Epic 4 — Reference Auto-Generation (CA-4)

**Goal:** Use GitNexus's `wiki` subcommand to auto-generate per-module reference documentation for all three workspace repos (`homelab-infra`, `homelab-apps`, `homelab-playbook`). Output bounded strictly to `/docs/reference/generated/`. Cadence: weekly + on-demand + on PR open + on merge to main.

**Sprint:** 2 (W3)

**Story breakdown:**

| Story | Title | One-line | FR |
|---|---|---|---|
| **E4.S1** | Configure GitNexus wiki provider | Set OpenAI API key in `~/.gitnexus/config.json`; pick model (Haiku 4.5 for cost, or default `minimax/minimax-m2.5`); set concurrency 3 | (FR17 prep) |
| **E4.S2** | Workspace-wide first regen with `--review` | Run `gitnexus wiki --review` on each of the three repos; review proposed module structure; iterate before letting full regen complete | FR17 |
| **E4.S3** | Output destination + blast-radius bound | Wrap `gitnexus wiki` output: rsync from `<repo>/.gitnexus/wiki/` into `<repo>/docs/reference/generated/`; pre-commit hook rejects writes outside this prefix when commit author == `gitnexus-bot` | FR18, ADR-006 |
| **E4.S4** | Weekly cron | `0 4 * * 0` UTC: `gitnexus wiki` for each of three repos; commit changes to `gitnexus-bot/<date>` branch; auto-PR | FR19 |
| **E4.S5** | On PR open + on merge regen | Extend `~/.claude/hooks/gitnexus/post.sh` with branch + path filter: if commit lands on `main` AND files in `<repo>/src/**` or `<repo>/terraform/**` changed, queue regen via async runner | FR19 |
| **E4.S6** | Verify `--skip-agents-md` permanently on | Confirm existing `gitnexus/post.sh` already uses `--skip-agents-md`; assert in CI that it never disappears | FR20 |
| **E4.S7** | Workspace-wide quality review | Compare GitNexus output for each repo against its existing BMAD-generated `architecture-*.md`; if quality is poor on a repo, document fallback (skip for that repo, hand-author) | (E4 acceptance) |

**Acceptance criteria for epic:**
- `gitnexus wiki` runs successfully for all three repos.
- Output is committed to `<repo>/docs/reference/generated/` and nowhere else.
- Pre-commit hook rejects out-of-prefix writes by `gitnexus-bot`.
- Weekly cron is enabled and produces a regen at scheduled time.
- On a real merge to `main` with code changes, post-commit hook triggers regen via async runner.
- Manual quality review of all three repos completed; off-ramp documented for any repo whose output is poor.

---

## 6. Epic 5 — Audience-Tuned Customer Wiki Publish (CA-5)

**Goal:** Build the `wiki-publish-audience` skill using Anthropic's canonical schema. Reads operator wiki, applies frontmatter `audience:` filter + LLM tone-rewrite, writes to workspace `/wiki/` (non-AzDO projects) or pushes to AzDO Wiki repo (AzDO projects). Configurable per audience via `references/<audience>-tone.md`.

**Sprint:** 3 (W4)

**Story breakdown:**

| Story | Title | One-line | FR |
|---|---|---|---|
| **E5.S1** | Skill folder scaffold | Create `.claude/skills/wiki-publish-audience/` with Anthropic canonical layout: `SKILL.md` + `references/` + `scripts/` + `assets/`. Frontmatter with trigger-phrase-first description + negative triggers | FR21 |
| **E5.S2** | Audience filter | `scripts/filter-by-audience.py`: read operator wiki; for each page, check frontmatter `audience:`; emit pages where target audience is included; redact `<!-- operator-only -->` blocks | FR24 |
| **E5.S3** | Per-audience tone configs | Create `references/customer-tone.md`, `references/pm-tone.md`, `references/public-tone.md` with redaction rules, jargon translations, intro templates | FR25 |
| **E5.S4** | Tone-rewrite LLM pass | `scripts/tone-rewrite.py`: for each filtered page, call LLM (Haiku for cost) with the audience-tone config and produce rewritten markdown | FR21, FR24 |
| **E5.S5** | Workspace `/wiki/` target | `scripts/write-workspace-wiki.sh`: write synthesized wiki to `<workspace>/wiki/` for non-AzDO projects; create `_meta/last-sync.json` provenance | FR23, FR26 |
| **E5.S6** | AzDO Wiki target | `scripts/push-to-azdo.sh`: clone `wikiMaster` branch of project's AzDO Wiki repo; rsync synthesized wiki; commit with `wiki-publish: <audience> @ <SHA>`; push using AAD-authenticated git | FR22, FR26 |
| **E5.S7** | Auto-detect target | `SKILL.md` workflow: detect whether project has AzDO tenant (heuristic: `.azure-pipelines.yml` exists, or `_bmad/azdo-config.yaml`) and route to S5 or S6 | FR22, FR23 |
| **E5.S8** | First customer-wiki publish for homelab | Manual run: `/wiki publish customer`; review output at workspace `/wiki/`; iterate `references/customer-tone.md` until quality acceptable | (E5 acceptance) |

**Acceptance criteria for epic:**
- Skill installed and discoverable via Claude Code (frontmatter scanned at startup).
- Trigger-phrase-first description with negative triggers prevents accidental routing.
- Audience filter strips operator-only pages and HTML-comment-fenced blocks correctly (verified by zero leakage of test-tagged operator content).
- Workspace `/wiki/` populated with audience-tuned content for the homelab.
- AzDO push capability tested in dry-run mode against a Sparkle-CPS-shaped project.
- Operator-content-leakage test: review every published page for secrets, internal hostnames, Tailscale ACLs — all zero.

---

## 7. Epic 6 — Multi-Surface Consumption (CA-6)

**Goal:** Make the operator wiki consumable from every audience's native surface: AI agents via MCP, external LLM crawlers via `llms.txt`, PM/PO/devs via AzDO Wiki, customers via Quartz (optional Growth feature).

**Sprint:** 4 (W5+, Growth)

**Story breakdown:**

| Story | Title | One-line | FR |
|---|---|---|---|
| **E6.S1** | MCP doc server registration | Add `docs` server to `~/.claude.json` running `arabold/docs-mcp-server` with roots `homelab-playbook/wiki/` + each `<repo>/docs/`; test via Claude Code session | FR27 |
| **E6.S2** | Cross-tool MCP registration | Register the same MCP server URL in Cursor's `~/.cursor/...` and Continue's `.continue/config.yaml`; test that all three tools see the same wiki | FR27 |
| **E6.S3** | llms.txt generator | Python script that walks `homelab-playbook/wiki/` + per-repo `<repo>/docs/`, emits AnswerDotAI-spec `llms.txt` at workspace root organized by Diátaxis quadrant; commit to git | FR28 |
| **E6.S4** | llms.txt regen on push | GitHub Action or pre-push hook: re-run llms.txt generator on every push to `main` | FR28 |
| **E6.S5** | AzDO Wiki mirror pipeline | `azure-pipelines-wiki-mirror.yml`: trigger on push to `main` with paths filter; clone `wikiMaster` worktree, rsync MD/PNG/SVG, commit + push | (FR22 — mirrors operator wiki, distinct from FR21 audience-publish flow) |
| **E6.S6** | Quartz build (optional) | GitHub Action that clones Quartz v4, symlinks wiki + per-repo docs as `content/`, runs `quartz build`, deploys to homelab CT behind Tailscale via nginx | FR29 |
| **E6.S7** | Tailscale-served deploy | Configure homelab CT (existing or new) with nginx serving Quartz output; expose only on Tailscale tailnet (operator default per phone-notifications-tailscale memory) | FR29 |

**Acceptance criteria for epic:**
- Cursor and Continue sessions read the same `homelab-playbook/wiki/` content via MCP without per-tool re-authoring.
- `llms.txt` exists at workspace root, parses against the AnswerDotAI spec validator, and lists pages grouped by Diátaxis quadrant.
- AzDO Wiki UI shows mirrored content within 5 minutes of a `main` push.
- (Optional) Quartz site is reachable via Tailscale from operator's phone and renders correctly.

---

## 8. Epic 7 — Drift Detection & Quality Gates (CA-7)

**Goal:** Continuous detection of doc drift via a layered lint stack: markdown syntax (markdownlint), broken links (lychee), prose quality (Vale), citation integrity (custom check-citations.py), orphan detection, and contradiction detection. Reports via existing ntfy crash-notifier pattern. Spans Sprint 1 (lint stack) + Sprint 2 (citation/orphan/contradiction). Crosscutting epic.

**Sprint:** 1 (S7.S1–S7.S4) + 2 (S7.S5–S7.S7) + 3 (S7.S8 contradiction-checker)

**Story breakdown:**

| Story | Title | One-line | FR |
|---|---|---|---|
| **E7.S1** | Install lint binaries | `npm install -g markdownlint-cli2`; install `lychee` (cargo or GitHub release); install Vale (apt or release) | FR30 |
| **E7.S2** | markdownlint config | `.markdownlint-cli2.yaml` at repo root with sensible defaults (MD013 line-length disabled, MD041 first-line-h1 disabled for frontmatter compatibility) | FR30 |
| **E7.S3** | lychee config | `.lychee.toml` excluding `graphiti://`, `bmad://`, `file://` URI schemes (custom checker handles), respecting cache | FR30 |
| **E7.S4** | Vale config | `.vale.ini` with Microsoft + write-good styles; relaxed rules for ADR pages | FR30 |
| **E7.S5** | check-citations.py | Resolve `file://`, `bmad://`, `external://` (delegate to lychee), `graphiti://` (deferred MCP call placeholder for v1, real call v2). Report broken citations | FR31 |
| **E7.S6** | check-orphans.py | Build wiki link graph from inbound link analysis; report pages with zero inbound links | FR30 |
| **E7.S7** | Weekly lint cron | `~/.claude/hooks/docs/weekly-lint.sh`: orchestrate all checks; produce `homelab-playbook/wiki/_meta/lint-<date>.md`; ntfy push to `docs-lint` | FR30 |
| **E7.S8** | check-contradictions.py | For pages with `owner: llm`, cross-reference `sources:` against current source content; flag claims that no longer match. Rule-based v1, LLM-diff v2 | FR32 |
| **E7.S9** | Health-check ntfy | Weekly health-check ntfy includes "lint last ran: <timestamp>"; alarm if >2 weeks old | (E7 reliability) |

**Acceptance criteria for epic:**
- Weekly lint produces a `lint-<date>.md` report and a ntfy push.
- Report contains counts: stale pages, broken links, prose violations, broken citations, orphans, contradictions.
- Broken citations are caught when a `sources:` URI no longer resolves.
- Operator runs at least one full cycle (lint → fix → re-lint) on the existing baseline.
- Contradiction-checker catches at least one synthetic test case (intentionally introduced contradiction).

---

## 9. Epic 8 — Cross-tool Portability Validation (CA-8)

**Goal:** Validate that the AGENTS.md schema works across Cursor, Codex CLI, Continue, and (manually) Aider, with no per-tool re-authoring. Validation-only epic, no new code paths beyond config tweaks. Spans all sprints as ongoing verification.

**Sprint:** All sprints (validation milestones at end of each)

**Story breakdown:**

| Story | Title | One-line | FR |
|---|---|---|---|
| **E8.S1** | Cursor session test | After E1.S6, a Cursor session in homelab root reads AGENTS.md via symlink; verify behavior matches Claude Code on 3 manual probes | FR4 |
| **E8.S2** | Codex CLI session test | A Codex CLI session reads AGENTS.md natively; verify same behavior | FR4 |
| **E8.S3** | Continue session test | A Continue session reads AGENTS.md via `.continue/config.yaml` `rules` opt-in; verify same behavior | FR4 |
| **E8.S4** | Aider session test (optional) | An Aider session with `--read AGENTS.md` consumes the schema; verify it doesn't conflict with repo-map model | FR4 |
| **E8.S5** | Multi-tool MCP doc-server test | After E6.S2, all three tools (Claude Code, Cursor, Continue) read the same `homelab-playbook/wiki/` via MCP; verify content parity | FR27 |

**Acceptance criteria for epic:**
- Cursor + Codex sessions in the homelab read AGENTS.md and produce expected behavior on the 3 manual probes used in E1.S6.
- No per-tool rule duplication exists (the rules live once, in AGENTS.md and `.claude/rules/`).
- (Stretch) all four tools (Claude Code, Cursor, Codex, Continue) consume the same wiki via MCP.

---

## 10. FR-to-Epic Audit (full-coverage check)

| FR # | Capability Area | Epic | Story |
|---|---|---|---|
| FR1 | CA-1 | E1 | E1.S1 |
| FR2 | CA-1 | E1 | E1.S2, E1.S3 |
| FR3 | CA-1 | E1 | E1.S4 |
| FR4 | CA-1 (cross-cuts CA-8) | E1 + E8 | E1.S6, E8.S1, E8.S2, E8.S3, E8.S4 |
| FR5 | CA-1 | E1 | E1.S5 |
| FR6 | CA-2 | E2 | E2.S1 |
| FR7 | CA-2 | E2 | E2.S2 |
| FR8 | CA-2 | E2 | E2.S3, E2.S4 |
| FR9 | CA-2 | E2 | E2.S5 |
| FR10 | CA-2 | E2 | E2.S6 |
| FR11 | CA-2 | E2 | E2.S7 |
| FR12 | CA-3 | E3 | E3.S1, E3.S3 |
| FR13 | CA-3 | E3 | E3.S4 |
| FR14 | CA-3 | E3 | E3.S2, E3.S3 |
| FR15 | CA-3 | E3 | E3.S5 |
| FR16 | CA-3 | E3 | E3.S6 |
| FR17 | CA-4 | E4 | E4.S2 |
| FR18 | CA-4 | E4 | E4.S3 |
| FR19 | CA-4 | E4 | E4.S4, E4.S5 |
| FR20 | CA-4 | E4 | E4.S6 |
| FR21 | CA-5 | E5 | E5.S1, E5.S4 |
| FR22 | CA-5 | E5 | E5.S6, E5.S7 |
| FR23 | CA-5 | E5 | E5.S5, E5.S7 |
| FR24 | CA-5 | E5 | E5.S2, E5.S4 |
| FR25 | CA-5 | E5 | E5.S3 |
| FR26 | CA-5 | E5 | E5.S5, E5.S6 |
| FR27 | CA-6 | E6 (+ E8) | E6.S1, E6.S2, E8.S5 |
| FR28 | CA-6 | E6 | E6.S3, E6.S4 |
| FR29 | CA-6 | E6 | E6.S6, E6.S7 |
| FR30 | CA-7 | E7 | E7.S1–S4, E7.S6, E7.S7 |
| FR31 | CA-7 | E7 | E7.S5 |
| FR32 | CA-7 | E7 | E7.S8 |

**Total:** 32 / 32 PRD FRs covered. No FR uncovered.

---

## 11. Sprint Plan Summary

| Sprint | Weeks | Epics | Story Count | Hours (est) |
|---|---|---|---|---|
| **Sprint 1** | W1–W2 | E1 (Schema) + E2 (Wiki SoT) + E7-partial (lint stack S1–S4) + E8.S1–S2 | 6 + 7 + 4 + 2 = **19 stories** | ~10–12 hrs |
| **Sprint 2** | W3 | E3 (Maintenance Loop) + E4 (Reference Auto-gen) + E7-extension (S5, S6, S7) + E8.S3 | 6 + 7 + 3 + 1 = **17 stories** | ~10–12 hrs |
| **Sprint 3** | W4 | E5 (Audience Publish) + E7.S8 (contradiction check) + E7.S9 (health check) | 8 + 2 = **10 stories** | ~8–10 hrs |
| **Sprint 4** | W5+ (Growth) | E6 (Multi-surface) + E8.S4–S5 (final cross-tool validation) | 7 + 2 = **9 stories** | ~10–15 hrs |

**Total: 55 stories across 4 sprints, ~38–49 hours of operator effort.**

(MVP = Sprints 1–2: ~36 stories, ~20–24 hours.)

## 12. Epic Dependencies (Gantt-style)

```
Sprint 1: ████████████████████ E1 (Schema)
          ▒▒▒▒▒▒▒▒▒▒██████████ E2 (Wiki SoT) ──┐
                    ▒▒▒▒██████ E7-lint        │
                          ░░░░ E8.S1-S2       │
Sprint 2:                          ████████████ E3 (Loop) ──┐
                                   ████████████ E4 (Reference)
                                         ░░░░░░ E7-extension
                                              ░ E8.S3
Sprint 3:                                          ████████ E5 (Audience) ──┐
                                                       ░░░ E7.S8
                                                       ░░░ E7.S9
Sprint 4:                                                       ████████████ E6 (Multi-surface)
                                                                       ░░░░ E8.S4-S5
```

Legend: ████ active development · ▒▒▒▒ blocking dependency · ░░░░ light / cross-cutting

## 13. References

- PRD: `products/doc-system/prd.md`
- Architecture: `products/doc-system/architecture.md`
- Doc-system research: `_bmad-output/planning-artifacts/research/technical-codebase-docs-system-research-2026-04-27.md`
- Schema research: `_bmad-output/planning-artifacts/research/technical-claude-md-best-practices-2026-04-27.md`
