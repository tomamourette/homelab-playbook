---
type: architecture
product: doc-system
version: 1.0.0-draft
status: draft
date: 2026-04-27
prd_ref: prd.md
research_refs:
  - homelab-playbook/_bmad-output/planning-artifacts/research/technical-codebase-docs-system-research-2026-04-27.md
  - homelab-playbook/_bmad-output/planning-artifacts/research/technical-claude-md-best-practices-2026-04-27.md
director_mode: true
---

# Codebase Documentation System — Architecture

## 1. Executive Architecture Summary

The documentation system is a **layered, single-source-of-truth architecture with audience-tuned fan-out**. Markdown-in-git is the only authoritative narrative store; every consumption surface (Obsidian, AzDO Wiki, workspace `/wiki/`, Quartz site, MCP doc server, `llms.txt`) is a one-way read-only mirror of that source. The architecture has **two wiki tiers** (operator/internal SoT in `homelab-playbook/wiki/`, customer-tuned synthesis in workspace `/wiki/` for non-AzDO projects or AzDO Wiki for AzDO projects) and **four content layers** (raw immutable sources / derived narrative wiki / auto-generated reference docs / agent-instruction schema), bridged by a Karpathy-style ingest/query/lint maintenance loop wired to Claude Code's hook lifecycle.

The architectural priority is **reversibility per capability area**: each of the 8 capability areas (CA-1 through CA-8 in the PRD) can be independently disabled or rolled back without breaking the others. The schema refactor (CA-1) is reversible in one git commit per pass; the maintenance loop (CA-3) can be disabled by removing two hooks; the reference auto-generation (CA-4) can be skipped by stopping a cron and emptying `/docs/reference/generated/`; the customer-wiki publish (CA-5) is a skill that can be uninstalled. This decomposition mirrors the PRD's MVP-then-Growth phasing: build cheap, validate, layer on value, never trap the operator.

The architecture's biggest bet is on **graph-grounded reference + LLM-synthesized narrative + audience-filtered publish** as a coherent triad. GitNexus Code Wiki produces the Reference quadrant from the live AST/community-detection graph (low hallucination because cross-refs are graph-grounded). Karpathy's LLM-Wiki ingest produces the Tutorials/How-to/Explanation quadrants from session transcripts and external sources (higher hallucination risk, mitigated by `sources:` frontmatter and lint cross-check). The `wiki-publish-audience` skill applies an audience filter + LLM tone-rewrite to produce customer-, PM-, public-tuned wikis from the same source. The triad is novel — no published OSS implementation combines all three at this exact configuration as of 2026-04-27.

The entire system runs on **operator-scale infrastructure**: existing Docker container for GitNexus, existing Graphiti container, existing Claude Code hook directory, existing AzDO tenant via Sparkle-CPS, existing Tailscale tailnet for non-public surfaces, existing crash-notifier ntfy for alerts. No new long-running services. No SaaS dependencies. Total LLM cost target: <€10/month.

## 2. System Context (C4 Level 1)

```
                     ┌──────────────────────┐                       
                     │      Operator        │                       
                     │  (tomamourette)      │                       
                     └─────────┬────────────┘                       
                               │ writes (Obsidian, terminal)        
                               │ reviews (AzDO web UI)              
                               ▼                                    
       ┌───────────── Codebase Documentation System ─────────────┐  
       │                                                          │  
       │  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐ │  
       │  │ Operator SoT │  │  Auto-gen    │  │ Audience-tuned │ │  
       │  │   wiki       │  │  Reference   │  │ Customer wiki  │ │  
       │  │ (Diátaxis)   │  │  (GitNexus)  │  │  (synthesis)   │ │  
       │  └──────┬───────┘  └──────┬───────┘  └───────┬────────┘ │  
       │         │                 │                   │          │  
       │         └────── single MD source-of-truth ────┘          │  
       │                          │                                │  
       │  ┌───────── Maintenance Loop (Karpathy) ─────────┐       │  
       │  │  Ingest (SessionEnd) → Query → Lint (cron)    │       │  
       │  └───────────────────┬───────────────────────────┘       │  
       └──────────────────────┼───────────────────────────────────┘  
                              │                                      
        ┌─────────────────────┼─────────────────────────────┐        
        ▼                     ▼                             ▼        
  ┌──────────┐         ┌──────────┐                  ┌─────────────┐
  │ Claude   │         │ Cursor / │                  │ AzDO Wiki / │
  │ Code     │         │ Continue │                  │ Quartz site │
  │ (primary)│         │ (via MCP)│                  │ (audiences) │
  └────┬─────┘         └─────┬────┘                  └─────┬───────┘
       │                     │                             │        
       ▼                     ▼                             ▼        
  Anthropic API          OpenAI/local                   PM, PO,     
                                                       customers,  
                                                       public      
```

**External actors:**
- **Operator** — primary author, reviewer, lint-report consumer.
- **PM, PO, devs** — read AzDO Wiki via existing AAD SSO (Sparkle-CPS tenant).
- **Customers / public** — read workspace `/wiki/` (non-AzDO projects) or AzDO public wiki, via Tailscale or AAD-public.
- **AI agents** — Claude Code (native), Cursor (manual symlinks + MCP), Continue (config + MCP), Codex (AGENTS.md native), Aider (manual `--read`).

**External systems:**
- Anthropic API (Claude Sonnet 4.6 / Opus 4.7 default).
- OpenAI API (Graphiti embeddings, GitNexus wiki-gen LLM, optional `wiki-publish-audience` LLM).
- Azure DevOps (existing tenant via Sparkle-CPS — AzDO Wiki target for AzDO-backed projects).
- Tailscale tailnet (default network posture for non-public services).
- ntfy (existing crash-notifier topic infra).

## 3. Container Diagram (C4 Level 2)

```
┌──────────────────────────── Workstation / Homelab ────────────────────────────────────┐
│                                                                                       │
│  ┌─────────────────────────── Source-of-Truth Layer ──────────────────────────────┐ │
│  │                                                                                 │ │
│  │  Workspace git repo (homelab/)                                                  │ │
│  │  ├── homelab-infra/docs/      ┐                                                 │ │
│  │  ├── homelab-apps/docs/       ├─ per-repo Diátaxis docs (FR6, FR7)             │ │
│  │  ├── homelab-playbook/docs/   ┘                                                 │ │
│  │  ├── homelab-playbook/wiki/   ── operator/internal wiki SoT (FR6, FR8)         │ │
│  │  ├── CLAUDE.md (stub)         ┐                                                 │ │
│  │  ├── AGENTS.md (canonical)    ├─ schema layer (CA-1: FR1-5)                    │ │
│  │  ├── .claude/rules/           ┘                                                 │ │
│  │  └── settings.json (enforced) ── permissions.deny etc. (FR5)                    │ │
│  │                                                                                 │ │
│  └─────────────────────────────────────┬───────────────────────────────────────────┘ │
│                                        │                                             │
│  ┌─────────────────────── Processing Layer (Maintenance Loop) ──────────────────────┐│
│  │                                                                                  ││
│  │  Claude Code hooks → ~/.claude/hooks/docs/                                       ││
│  │   ├── session-end.sh (FR12)              queues to ingest-queue.jsonl            ││
│  │   ├── post-tooluse-edit.sh (FR14)        log.md append                           ││
│  │   └── pre-commit/frontmatter-validate.sh (FR9)                                   ││
│  │                                                                                  ││
│  │  Async runner (cron, every 15 min) → docs-ingest                                 ││
│  │   └── reads queue, calls LLM, drafts wiki updates → wiki-bot/<date> branches     ││
│  │       (FR13)                                                                     ││
│  │                                                                                  ││
│  │  Weekly lint cron (Mon 06:00 UTC) → docs/weekly-lint.sh (FR30, FR31, FR32)       ││
│  │   └── markdownlint + lychee + Vale + check-citations.py + check-orphans.py       ││
│  │       reports to ntfy `docs-lint`                                                ││
│  │                                                                                  ││
│  │  GitNexus container (existing, 127.0.0.1:4747)                                   ││
│  │   ├── analyze on every commit (existing post.sh, --skip-agents-md kept)          ││
│  │   ├── wiki regen: weekly + on-demand + on PR/merge → /docs/reference/generated/  ││
│  │   │   (FR17, FR18, FR19, all 3 repos per workspace decision)                     ││
│  │   └── --skill-agents-md flag PERMANENTLY DISABLED (FR20, ADR-006)                ││
│  │                                                                                  ││
│  │  Graphiti container (existing, 127.0.0.1:8000)                                   ││
│  │   └── episodes/facts/entities cited via graphiti:// URIs (read-only from wiki)   ││
│  │                                                                                  ││
│  └─────────────────────────────────────┬────────────────────────────────────────────┘│
│                                        │                                             │
│  ┌──────────────────── Synthesis & Publish Layer (CA-5) ──────────────────────────┐ │
│  │                                                                                  │ │
│  │  .claude/skills/wiki-publish-audience/ (Anthropic canonical schema)              │ │
│  │   ├── SKILL.md                  orchestrator (≤500 lines)                        │ │
│  │   ├── references/<audience>.md  per-audience tone & redaction config (FR25)      │ │
│  │   ├── scripts/                  filter-by-audience.py, push-to-azdo.sh           │ │
│  │   └── assets/                   intro-page templates, TOC templates              │ │
│  │                                                                                  │ │
│  │  Trigger: operator slash-command or `/wiki publish customer|pm|public`            │ │
│  │  Reads:   homelab-playbook/wiki/  (operator SoT)                                 │ │
│  │  Writes:  - workspace /wiki/ for non-AzDO projects (FR23)                        │ │
│  │           - AzDO Wiki repo wikiMaster branch via REST+git (FR22)                 │ │
│  │  Auth:    AAD credentials from operator env (FR22)                               │ │
│  │  Provenance: _meta/last-sync.json, commit message wiki-publish: <audience> @ SHA │ │
│  │                                                                                  │ │
│  └─────────────────────────────────────┬────────────────────────────────────────────┘ │
│                                        │                                             │
└────────────────────────────────────────┼─────────────────────────────────────────────┘
                                         │                                             
       ┌─────────────────────────────────┼─────────────────────────────────────────┐   
       ▼                                 ▼                                         ▼   
┌─────────────┐                  ┌────────────────┐                       ┌──────────────┐
│  Obsidian   │                  │ AzDO Wiki      │                       │ MCP doc      │
│  (operator) │                  │ wikiMaster     │                       │ server       │
│  vault =    │                  │ branch         │                       │ (arabold)    │
│  git tree   │                  │ (mirror)       │                       │ + llms.txt   │
│ obsidian-git│                  │ AAD SSO        │                       │ Cursor/Cont. │
└─────────────┘                  └────────────────┘                       └──────────────┘
                                                                                     
                  Optional Growth: Quartz v4 site behind Tailscale on a homelab CT  
                                                                                     
```

## 4. Source-of-Truth Topology

Each fact-type has exactly one authoritative home. Architectural rule (ADR-002): derived views never become writers.

| Fact type | Authoritative store | Read by | Written by |
|---|---|---|---|
| Code & config | git repo (3 sub-repos) | everyone | operator |
| Live code structure | GitNexus knowledge graph (Docker) | wiki references via graph queries; never duplicated into MD | GitNexus `analyze` on every commit (auto) |
| Temporal decisions / episodes | Graphiti (FalkorDB-backed MCP) | wiki cites via `graphiti://episode/<uuid>` URIs | Operator and Claude Code agents (Graphiti MCP `add_memory`) |
| Operator working notes | Claude auto-memory `~/.claude/projects/<project>/memory/` | Claude sessions (eager at start) | Auto-memory tool + `/memory` slash command |
| Formal artifacts | BMAD outputs in `_bmad-output/` | wiki cites via `bmad://` URIs | BMAD skills |
| External sources | `<wiki>/raw/` folder (per-wiki) | wiki cites via `external://` URIs | Operator (Obsidian Web Clipper, drag-into) |
| Operator/internal wiki | `homelab-playbook/wiki/` (Diátaxis) | Obsidian (operator), MCP server (agents), AzDO mirror (read-only), audience-publish skill (read-only) | Operator + Claude Code agents via wiki-bot branches |
| Per-repo docs | `<repo>/docs/` (Diátaxis) | same as above | same as above |
| Reference auto-gen | `/docs/reference/generated/` per repo | humans, AI agents | **GitNexus only** (FR18, ADR-006 blast-radius bound) |
| Customer-tuned wiki | workspace `/wiki/` or AzDO Wiki repo | PM, PO, customer, public | **`wiki-publish-audience` skill only** (FR23) |
| Schema (agent rules) | `AGENTS.md` + `.claude/rules/<topic>.md` + `settings.json` | Claude Code (via `@AGENTS.md`), Cursor (manual symlink), Codex (native), Continue (config) | Operator (PR review) |

## 5. Component Contracts

### 5.1 SessionEnd Ingest Hook (FR12)

- **Path:** `~/.claude/hooks/docs/session-end.sh`
- **Trigger:** Claude Code `SessionEnd` hook event (verified per https://code.claude.com/docs/en/hooks).
- **Input:** stdin JSON payload with `session_id`, `termination_reason`.
- **Output:** appends one entry to `homelab-playbook/wiki/_meta/ingest-queue.jsonl`.
- **Constraints:** ≤3 second budget, `set +e`, fail-silent. Never blocks Claude Code shutdown.
- **Failure mode:** queue write fails → entry lost. Mitigation: scheduled lint detects gap (compares git log vs queue history).

### 5.2 PostToolUse Log Hook (FR14)

- **Path:** `~/.claude/hooks/docs/post-tooluse-edit.sh`
- **Trigger:** `PostToolUse` matcher `Edit|Write|MultiEdit`.
- **Filter:** only fires when `tool_input.file_path` contains `/docs/` or `/wiki/`.
- **Output:** appends `## [<ISO-date>] edit | <relative-path> | session=<session_id>` to nearest ancestor `log.md`.
- **Constraints:** ≤3 second budget, fail-silent.

### 5.3 Async Ingest Runner (FR13)

- **Path:** `~/.claude/hooks/docs/ingest-runner.sh` (cron, every 15 min) OR systemd timer.
- **Workflow:** drains `ingest-queue.jsonl` → for each entry: read session transcript via Claude API or local cache → identify decision-making turns → draft ADR or runbook update on `wiki-bot/<date>-session-<id>` branch → commit with provenance frontmatter (`owner: llm`, `sources:`, `last_ingested:`) → open auto-PR.
- **LLM:** Anthropic Sonnet for ingest (cheaper than Opus, sufficient for synthesis). Cost target: ~$0.10–0.30 per session.
- **Idempotency:** queue entries marked `pending|processing|done|failed`. Crashes safe.

### 5.4 Weekly Lint Cron (FR30, FR31, FR32)

- **Path:** `~/.claude/hooks/docs/weekly-lint.sh`
- **Schedule:** `0 6 * * 1` UTC.
- **Pipeline:**
  1. `markdownlint-cli2` against all wiki/docs paths.
  2. `lychee` link check (excludes `graphiti://`, `bmad://`, `file://` — citation-checker handles).
  3. `Vale` prose lint with Microsoft + write-good styles.
  4. `check-citations.py` resolving `file://`, `bmad://`, `external://` (lychee), `graphiti://` (deferred MCP call).
  5. `check-orphans.py` finding wiki pages with zero inbound links.
  6. `check-contradictions.py` cross-referencing `owner: llm` pages against current `sources:` content (lightweight LLM diff or rule-based for v1).
- **Output:** report to `homelab-playbook/wiki/_meta/lint-<date>.md` + ntfy push to `docs-lint` topic.
- **Fail-detection:** if last `lint-*.md` file is >2 weeks old, weekly health-check ntfy alerts.

### 5.5 GitNexus Wiki Regen (FR17, FR18, FR19)

- **Trigger:** weekly cron (Sun 04:00 UTC) + on-demand (`/wiki regen`) + on PR open + on merge to `main` (extended `~/.claude/hooks/gitnexus/post.sh` with branch + path filter).
- **Command:** `docker exec gitnexus node /app/gitnexus/dist/cli/index.js wiki <repo-path> --concurrency 3 --no-stats`.
- **Output:** writes to `<repo>/.gitnexus/wiki/`, then rsync into `<repo>/docs/reference/generated/`.
- **Blast-radius bound (FR18, ADR-006):** pre-commit hook rejects writes outside `/docs/reference/generated/` when commit author == `gitnexus-bot`.
- **`--skip-agents-md` (FR20, ADR-006):** permanently on; existing `gitnexus/post.sh` already has this.
- **Workspace coverage:** all three repos (homelab-infra, homelab-apps, homelab-playbook) — full coverage from MVP per operator decision 2026-04-27.

### 5.6 `wiki-publish-audience` Skill (FR21–FR26)

- **Path:** `.claude/skills/wiki-publish-audience/`
- **Schema:** Anthropic canonical (`SKILL.md` + `references/` + `scripts/` + `assets/`). NOT BMAD's `workflow.md + steps/` (community extension).
- **Frontmatter:** `name: wiki-publish-audience` / `description: Use when user says 'publish customer wiki', 'sync customer wiki', 'update customer-facing docs'. Triggers: requests to mirror playbook content to AzDO Wiki or workspace /wiki/. Do NOT use for editing the operator wiki directly.`
- **Workflow:** read operator wiki → filter pages by frontmatter `audience:` containing target → for each page: LLM tone-rewrite per `references/<audience>-tone.md` config → strip operator-only sections + `<!-- operator-only -->` blocks → assemble target tree → write/push.
- **Targets:**
  - **Non-AzDO projects** (homelab itself): write to `<workspace>/wiki/` at workspace root.
  - **AzDO projects** (Sparkle-CPS-shaped): git push to `wikiMaster` branch of AzDO Wiki repo via REST + AAD-authenticated git.
- **Failure modes:** uneven tone → split into multi-skill pack (`wiki-filter-audience` + `wiki-tone-rewrite` + `wiki-mirror-azdo` + `wiki-mirror-workspace`) per `kfchou/wiki-skills` model. Audience config drift → keep `references/<audience>-tone.md` under operator review, lint the skill against its own `eval.json` per `VoidLight00/autoimprove-cc` pattern (Vision feature).

### 5.7 MCP Doc Server (FR27)

- **Path:** registered in `~/.claude.json` as `docs` MCP server.
- **Implementation:** `arabold/docs-mcp-server` initial; replaceable with a 100-line custom server if needed.
- **Roots:** `homelab-playbook/wiki/` + each `<repo>/docs/`.
- **Cross-tool:** same MCP server URL registered in Cursor `~/.cursor/...` and Continue `.continue/config.yaml`.

### 5.8 AzDO Mirror Pipeline (FR22)

- **Type:** Azure Pipelines YAML (`azure-pipelines-wiki-mirror.yml`).
- **Trigger:** push to `main`, paths filter on `**/docs/**` and `homelab-playbook/wiki/**`.
- **Action:** clone `wikiMaster` branch as worktree, rsync MD/PNG/SVG into worktree, commit + push.
- **Direction:** **strictly one-way** (repo → AzDO). AzDO Wiki UI configured as Code-Wiki-mode pointing at `wikiMaster` (read-only by design); communicated to PMs.

### 5.9 Quartz Build (Growth, FR29)

- **Type:** GitHub Action.
- **Trigger:** push to `main`, paths filter on `homelab-playbook/wiki/**` + `<repo>/docs/**`.
- **Pipeline:** clone Quartz v4 → symlink wiki + per-repo docs as `content/` → `npx quartz build` → upload `public/` artifact → deploy to homelab CT behind Tailscale via nginx (matches `phone-notifications-tailscale` default).

## 6. Schema Architecture (CA-1)

**Pattern combo:** Astral stub-redirect (Anthropic-endorsed verbatim) + Cline manifest+topic-split + path-scoped lazy-load via `paths:` frontmatter.

```
CLAUDE.md             # 1 line: @AGENTS.md
AGENTS.md             # canonical schema, ≤120 lines
                      # Section order:
                      #  1. Project context (1-line)
                      #  2. Build/test/lint commands
                      #  3. Project shape (one-line dir pointers)
                      #  4. Behavioral invariants (5–15 imperative rules)
                      #  5. Forbidden patterns / security
                      #  6. Pointers (@.claude/rules/<topic>.md)
.claude/rules/
├── general.md                 # behavioral invariants — ≤80 lines
├── file-organization.md       # where things live — ≤30 lines
├── security.md                # OWASP, secrets, validation — ≤50 lines
├── testing.md                 # TDD, integration tests — ≤40 lines
├── docs.md                    # wiki schema, ingest/query/lint workflow — ≤100 lines
├── concurrency.md             # batching, parallelism — ≤30 lines
└── path-scoped/
    ├── homelab-infra-terraform.md   # paths: ['homelab-infra/**'] — lazy
    └── homelab-apps-docker.md       # paths: ['homelab-apps/**']  — lazy
CLAUDE.local.md       # gitignored — operator-only preferences
settings.json         # ENFORCED rules (permissions.deny, hooks)
```

**Critical correction from research:** `@`-imports are eager, not lazy. The Cline-style topic split organizes for review-ability and PR diffs but does NOT save session-start tokens. To genuinely lazy-load: (a) `paths:` frontmatter on rules files, (b) Skills (frontmatter scanned, body lazy on routing match), (c) Slash commands (body on invocation), (d) `UserPromptSubmit` hooks that conditionally inject context.

**Migration in two reversible passes:**
1. **Pass 1** (~30 min): `mv CLAUDE.md AGENTS.md && printf '@AGENTS.md\n' > CLAUDE.md && git commit`. One-line revert.
2. **Pass 2** (~2–3 hrs): split AGENTS.md into `.claude/rules/<topic>.md` files + apply audit cuts (drop ruflo product reference, 60+ agent list, 3-tier model routing — content that's tool-specific reference, not project rules). Target: ≤120 line AGENTS.md.

## 7. Data Flow — Maintenance Loop (Karpathy)

```
                        ┌─────────────────────────────┐
                        │  Operator's Claude Code     │
                        │  session                    │
                        └──────────────┬──────────────┘
                                       │ (decision made, edits land)
                                       ▼
              ┌──────────────────────────────────────────────────┐
              │ PostToolUse hook (Edit|Write|MultiEdit on        │
              │ /docs/** or /wiki/**) → log.md append            │
              └──────────────────────────────────────────────────┘
                                       │
                                       ▼
                    ┌──────────────────────────────────┐
                    │ SessionEnd hook                  │
                    │ → ingest-queue.jsonl entry       │
                    │   (pending)                      │
                    └──────────────┬───────────────────┘
                                   │ (cron 15 min later)
                                   ▼
            ┌──────────────────────────────────────────────────┐
            │ Async ingest runner                              │
            │  • reads queue                                   │
            │  • loads session transcript                      │
            │  • LLM identifies decisions / runbook material   │
            │  • drafts wiki update on wiki-bot/<branch>       │
            │  • opens auto-PR with frontmatter (owner: llm,   │
            │    sources:, last_ingested:)                     │
            └──────────────┬───────────────────────────────────┘
                           │
                           ▼
              ┌────────────────────────────────────────┐
              │ Operator review (next morning)         │
              │  • merges PR (sets owner: human if     │
              │    keeping)                            │
              │  • or rejects + tweaks ingest config   │
              └────────────────────────────────────────┘

           ─────────────────── (weekly lint pass) ──────────────────

                     ┌───────────────────────────────┐
                     │ Mon 06:00 UTC cron            │
                     └──────────────┬────────────────┘
                                    ▼
   ┌──────────────────────────────────────────────────────────┐
   │ Lint pipeline (markdownlint + lychee + Vale + cite check │
   │  + orphan check + contradiction check)                   │
   └──────────────────────────┬───────────────────────────────┘
                              │
                              ▼
                ┌─────────────────────────────────┐
                │ ntfy `docs-lint` push           │
                │ + lint-<date>.md in _meta/      │
                └─────────────────────────────────┘
```

## 8. Cross-cutting Concerns

### 8.1 Provenance / Citations (FR31)

Frontmatter `sources:` is the load-bearing primitive. Resolves four URI schemes:
- `file://<path>:<lo>-<hi>` — file exists, line range valid (via GitNexus `route_map` for canonical anchors).
- `bmad://<path>` — file exists in `_bmad-output/`.
- `external://<url>` — lychee handles.
- `graphiti://episode/<uuid>` — deferred MCP call to `mcp__graphiti__get_entity_edge`.

`ingest_log:` cross-links into `log.md` for audit trail. `contradictions:` populated by lint pass.

### 8.2 Security & Redaction (NFR Security)

Three layers of defense against operator-secret leakage to customer surface:
1. **Frontmatter `audience:` array** filters out operator-only pages.
2. **`<!-- operator-only -->` HTML-comment-fenced blocks** are stripped (HTML comments survive markdown rendering but are detectable).
3. **`permissions.deny` in `settings.json`** enforces hard fences (no `.env` reads, no destructive commands) regardless of CLAUDE.md/AGENTS.md content.

Pre-commit hook scans for credential patterns. AzDO push uses operator's existing AAD env vars; never committed.

### 8.3 Failure Modes & Fallbacks (per §3.8 of doc-system research)

| Failure | Fallback |
|---|---|
| GitNexus down | git diff for ingest path detection; existing 3-second hook timeout protects |
| Graphiti down | provenance citations remain stable strings; ingest skips Graphiti enrichment, queues retry |
| Hook misfire/timeout | log.md gaps detected by scheduled lint, back-filled |
| Mirror to AzDO fails | crash-notifier ntfy alert (existing pattern) |
| Confidently-wrong synthesis | lint cross-checks `sources:`; flags contradictions |
| Schema drift (CLAUDE.md vs AGENTS.md) | pre-commit diff; Astral pattern keeps single SoT |
| Operator edits in Obsidian outside session | `FileChanged` hook + `last_ingested` frontmatter catch on next SessionStart |
| Session compaction loses pending edits | `PreCompact` hook flushes pending to `log.md` |

### 8.4 Observability

- **Ntfy topics**: `docs-lint` (weekly report), `docs-mirror` (mirror failure alerts).
- **Lint reports**: persisted in `homelab-playbook/wiki/_meta/lint-<date>.md`.
- **Sync provenance**: `_meta/last-sync.json` per published wiki target.
- **Hook logs**: stderr captured by Claude Code's hook log path.
- **Ingest queue**: `homelab-playbook/wiki/_meta/ingest-queue.jsonl` is human-readable for triage.

## 9. Decision Register (ADRs)

ADRs live at `<repo>/docs/explanation/adr/` (per-repo) and `homelab-playbook/wiki/decisions/` (workspace-level). Initial set drafted in research §5.2 / §4.6:

| ADR | Title | Status | Source |
|---|---|---|---|
| **ADR-001** | Adopt Diátaxis IA | proposed | doc-system research §4.6 |
| **ADR-002** | Markdown-in-git is single SoT; consumers are read-only | drafted | doc-system research §5.2.1 |
| **ADR-003** | CLAUDE.md = `@AGENTS.md`; AGENTS.md canonical; topic split | drafted | doc-system research §5.2.2 + claude-md research §4.4 |
| **ADR-004** | Adopt Architecture C (hybrid) with two-layer wiki split | drafted | doc-system research §6 + this PRD |
| **ADR-005** | Frontmatter spec mandatory on all wiki/docs MD files | drafted | doc-system research §5.2.3 |
| **ADR-006** | GitNexus Code Wiki bounded to `/docs/reference/generated/` | proposed | doc-system research §4.6 |
| **ADR-007** | Graphiti is authoritative for temporal decisions; wiki cites by URI | proposed | doc-system research §4.6 |
| **ADR-008** | Workspace `homelab-playbook/wiki/` for cross-repo, per-repo `/docs/` for repo-internal | proposed | doc-system research §4.6 |
| **ADR-009** | `log.md` append-only, prefix-formatted, rotated annually | proposed | doc-system research §4.6 |
| **ADR-010** | Mirrors are one-way only (repo → AzDO/Quartz; never write back) | proposed | doc-system research §4.6 |
| **ADR-011** | `@`-imports are eager; topic split organizes, doesn't lazy-load. True lazy-load = Skills / slash / hooks / `paths:` | proposed | claude-md research §3 |
| **ADR-012** | GitNexus workspace coverage from MVP (all 3 repos), not per-repo opt-in | proposed | operator decision 2026-04-27 |
| **ADR-013** | `wiki-publish-audience` skill uses Anthropic canonical schema (SKILL.md + references/ + scripts/ + assets/), not BMAD's workflow.md + steps/ | proposed | claude-md research §1.4 |

ADR-001 through ADR-013 are drafted in research artifacts; final per-product copies land at `products/doc-system/adrs/` during implementation.

## 10. Operational View

### 10.1 Deployment

- **No new long-running services.** Existing GitNexus container, Graphiti container, Claude Code hooks, AzDO tenant, Tailscale tailnet, ntfy infra.
- **Cron jobs** added to operator's user crontab (or systemd user timers): ingest-runner (every 15 min), GitNexus weekly regen (Sun 04:00 UTC), weekly lint (Mon 06:00 UTC).
- **CI pipelines** added: AzDO Pipelines for AzDO Wiki mirror; GitHub Action for Quartz build (Growth).

### 10.2 Sequencing constraints

- Schema refactor Pass 1 must precede Pass 2.
- Frontmatter spec must land before SessionEnd hook (ingest produces frontmatter-bearing files).
- Lint stack must land before scheduled cron.
- GitNexus regen on PR/merge requires the existing `gitnexus/post.sh` extension, not a parallel hook.
- `wiki-publish-audience` must read frontmatter `audience:` field, so frontmatter spec is its hard dependency.

### 10.3 Cost ceilings (per PRD NFR)

- LLM cost: <€10/month soft, €15/month hard. Tracked via OpenAI/Anthropic billing dashboards.
- GitNexus regen full-workspace: ~$1.50–6 per regen depending on changed-symbol count, gated on graph-delta threshold.
- SessionEnd ingest: ~$0.10–0.30/session × ~20 sessions/month ≈ $2–6/month.
- Audience-publish pass: ~$0.50/run × ~4/month ≈ $2/month.
- Weekly lint: ~$0.50/run × 4 ≈ $2/month.
- Total target: ~$8–16/month projected; alarm at €15.

## 11. Architecture Quality Attributes (mapped to NFRs)

| NFR | Architectural mechanism |
|---|---|
| Hook latency ≤3s | All hooks `set +e`, fail-silent; LLM work goes to async runner |
| Schema-file load ≤5k tokens | Astral stub + ≤120-line AGENTS.md + path-scoped `.claude/rules/` (only matching paths load) |
| AzDO mirror <5 min | Single AzDO Pipelines YAML, rsync-based, runs in parallel |
| Reliability — silent failures detectable | Weekly lint alerts on stale `lint-*.md`, hook logs reviewable |
| Security — operator content never leaks | Three-layer redaction: audience filter + HTML comments + `permissions.deny` |
| Reversibility per CA | Each capability area can be disabled independently (see §1) |
| Cost ceiling | Async runners + delta-gated regen; monthly billing review |

## 12. Open Architecture Items for Build Time

- **Choice of MCP doc server**: `arabold/docs-mcp-server` initial, replaceable.
- **Audience-tuning LLM model**: default Haiku 4.5 (cheap, fast); upgrade to Sonnet for higher-quality customer wiki passes if cost permits.
- **Lint contradiction-checker**: rule-based v1 (regex-style cross-references); LLM-diff v2 if v1 has too many false negatives.
- **GitNexus regen graph-delta threshold**: pick after first month of operation; baseline target = "regen if >10% of symbols changed since last full pass".
- **Wiki bot git author identity**: dedicated SSH key + git-config `wiki-bot <wiki-bot@homelab.local>` so commits are clearly attributable.

## 13. References

- PRD: `products/doc-system/prd.md`
- Research (architecture & topology): `_bmad-output/planning-artifacts/research/technical-codebase-docs-system-research-2026-04-27.md`
- Research (schema & instruction precedence): `_bmad-output/planning-artifacts/research/technical-claude-md-best-practices-2026-04-27.md`
- Anthropic memory doc: https://docs.claude.com/en/docs/claude-code/memory
- Anthropic skills doc: https://docs.claude.com/en/docs/claude-code/skills
- Claude Code hooks: https://code.claude.com/docs/en/hooks
- Diátaxis: https://diataxis.fr
- MADR 4.0: https://adr.github.io
- Karpathy LLM-Wiki: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
- GitNexus: https://github.com/abhigyanpatwari/GitNexus
- AnswerDotAI llms-txt: https://github.com/AnswerDotAI/llms-txt
- `kfchou/wiki-skills`: https://github.com/kfchou/wiki-skills
- `arabold/docs-mcp-server`: https://github.com/arabold/docs-mcp-server
